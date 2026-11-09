import asyncio
import importlib
import os
import re
import time
import types
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.responses import JSONResponse

import admin_dashboard

TEST_PASSWORD = "test-only-password"


class FakeState:
    csp_nonce = "test-nonce"


class FakeClient:
    def __init__(self, host="10.0.0.1"):
        self.host = host


class FakeRequest:
    """admin_page/_require_session için gereken en küçük istek nesnesi."""

    def __init__(self, token=None, headers=None, client=None):
        self.cookies = {admin_dashboard.SESSION_COOKIE_NAME: token} if token else {}
        self.headers = headers or {}
        self.state = FakeState()
        self.client = client or FakeClient()


def make_token(ttl=admin_dashboard.SESSION_TTL, nonce="nonce-value"):
    expiry = str(int(time.time()) + ttl)
    signature = admin_dashboard._session_signature(expiry, nonce)
    return expiry + "." + nonce + "." + signature


def session_cookie_header():
    response = JSONResponse({"ok": True})
    admin_dashboard._set_session(response)
    return response.headers["set-cookie"]


def cookie_value(header):
    match = re.search(r"eng_admin_session=([^;]+)", header)
    if not match:
        raise AssertionError("Oturum çerezi Set-Cookie başlığında bulunamadı.")
    return match.group(1)


def render_page(token=None):
    response = asyncio.run(admin_dashboard.admin_page(FakeRequest(token)))
    return response.body.decode("utf-8")


def login_request(token=None, forwarded="203.0.113.7", peer="10.0.0.1"):
    return FakeRequest(
        token,
        headers={"host": "engelli.me", "origin": "https://engelli.me", "x-forwarded-for": forwarded},
        client=FakeClient(peer),
    )


def run_login(password, request=None):
    body = types.SimpleNamespace(password=password)
    return asyncio.run(admin_dashboard.admin_password_login(request or login_request(), body))


class AdminSessionCookieTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"ADMIN_PASSWORD": TEST_PASSWORD})
        patcher.start()
        self.addCleanup(patcher.stop)
        # Modül düzeyindeki sayaçlar testler arasında taşınmasın.
        admin_dashboard._login_failures.clear()
        admin_dashboard.SESSION_REVOCATIONS.clear()
        # Tanı satırları üretimde Cloud Run loglarına gider; test çıktısını kirletmesin.
        admin_dashboard.logger.setLevel("CRITICAL")

    def test_session_cookie_is_lax_so_cross_site_navigation_keeps_it(self):
        # iOS Safari, SameSite=Strict çerezini başka siteden gelen üst düzey
        # gezinmede göndermiyor; bu yüzden giriş sayfası gereksiz açılıyordu.
        header = session_cookie_header()
        lowered = header.lower()
        self.assertIn("samesite=lax", lowered)
        self.assertNotIn("samesite=strict", lowered)
        self.assertIn("httponly", lowered)
        self.assertIn("secure", lowered)
        self.assertIn("path=/admin", lowered)
        self.assertNotIn("domain=", lowered)

    def test_cookie_lifetime_is_twelve_hours(self):
        header = session_cookie_header()
        self.assertIn("max-age=%d" % admin_dashboard.SESSION_TTL, header.lower())
        self.assertEqual(admin_dashboard.SESSION_TTL, 12 * 60 * 60)

    def test_issued_cookie_is_accepted_on_next_request(self):
        token = cookie_value(session_cookie_header())
        request = FakeRequest(token)
        self.assertEqual(admin_dashboard._session_state(request), admin_dashboard.SESSION_VALID)
        self.assertTrue(admin_dashboard._require_session(request))
        self.assertIn("Haber sistemi durum raporu", render_page(token))

    def test_session_survives_application_restart(self):
        token = cookie_value(session_cookie_header())
        # Yeni revision/instance aynı ADMIN_PASSWORD ile başlar; modülü yeniden
        # yüklemek süreç yeniden başlamasını taklit eder.
        importlib.reload(admin_dashboard)
        request = FakeRequest(token)
        self.assertEqual(admin_dashboard._session_state(request), admin_dashboard.SESSION_VALID)
        self.assertTrue(admin_dashboard._require_session(request))

    def test_expired_session_is_rejected(self):
        token = make_token(ttl=-60)
        request = FakeRequest(token)
        self.assertEqual(admin_dashboard._session_state(request), admin_dashboard.SESSION_EXPIRED)
        with self.assertRaises(HTTPException) as raised:
            admin_dashboard._require_session(request)
        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("Yönetici parolası", render_page(token))

    def test_tampered_session_is_rejected(self):
        expiry, nonce, _ = make_token().split(".", 2)
        token = expiry + "." + nonce + "." + "0" * 64
        request = FakeRequest(token)
        self.assertEqual(admin_dashboard._session_state(request), admin_dashboard.SESSION_BAD_SIGNATURE)
        with self.assertRaises(HTTPException) as raised:
            admin_dashboard._require_session(request)
        self.assertEqual(raised.exception.status_code, 401)

    def test_session_signed_with_other_secret_is_rejected(self):
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "another-password"}):
            token = make_token()
        self.assertEqual(
            admin_dashboard._session_state(FakeRequest(token)),
            admin_dashboard.SESSION_BAD_SIGNATURE,
        )

    def test_malformed_session_is_rejected(self):
        for token in ("not-a-token", "123.abc", "abc.def.ghi"):
            self.assertEqual(
                admin_dashboard._session_state(FakeRequest(token)),
                admin_dashboard.SESSION_MALFORMED,
            )

    def test_missing_cookie_and_missing_secret_are_distinguished(self):
        self.assertEqual(
            admin_dashboard._session_state(FakeRequest(None)),
            admin_dashboard.SESSION_MISSING,
        )
        with patch.dict(os.environ, {"ADMIN_PASSWORD": ""}):
            self.assertEqual(
                admin_dashboard._session_state(FakeRequest(make_token())),
                admin_dashboard.SESSION_NO_SECRET,
            )


class AdminLogoutTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"ADMIN_PASSWORD": TEST_PASSWORD})
        patcher.start()
        self.addCleanup(patcher.stop)
        admin_dashboard._login_failures.clear()
        admin_dashboard.SESSION_REVOCATIONS.clear()
        admin_dashboard.logger.setLevel("CRITICAL")

    def test_logout_revokes_the_session_server_side(self):
        token = make_token(nonce="logout-nonce")
        request = login_request(token)
        self.assertEqual(admin_dashboard._session_state(request), admin_dashboard.SESSION_VALID)
        response = asyncio.run(admin_dashboard.admin_logout(request))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(admin_dashboard._session_state(request), admin_dashboard.SESSION_REVOKED)
        with self.assertRaises(HTTPException) as raised:
            admin_dashboard._require_session(request)
        self.assertEqual(raised.exception.status_code, 401)

    def test_logout_without_cookie_still_succeeds(self):
        response = asyncio.run(admin_dashboard.admin_logout(login_request(None)))
        self.assertEqual(response.status_code, 200)


class AdminLoginThrottleTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"ADMIN_PASSWORD": TEST_PASSWORD})
        patcher.start()
        self.addCleanup(patcher.stop)
        admin_dashboard._login_failures.clear()
        admin_dashboard.SESSION_REVOCATIONS.clear()
        admin_dashboard.logger.setLevel("CRITICAL")
        sleep_patcher = patch.object(admin_dashboard.asyncio, "sleep", AsyncMock())
        sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)

    def test_failed_logins_add_delay(self):
        with self.assertRaises(HTTPException) as raised:
            run_login("wrong-password")
        self.assertEqual(raised.exception.status_code, 401)
        admin_dashboard.asyncio.sleep.assert_awaited()
        delay = admin_dashboard.asyncio.sleep.await_args.args[0]
        self.assertGreater(delay, 0)
        self.assertLessEqual(delay, admin_dashboard.LOGIN_MAX_DELAY_SECONDS)

    def test_brute_force_is_blocked_after_five_failures(self):
        for _ in range(admin_dashboard.LOGIN_ATTEMPT_LIMIT):
            with self.assertRaises(HTTPException) as raised:
                run_login("wrong-password")
            self.assertEqual(raised.exception.status_code, 401)
        with self.assertRaises(HTTPException) as raised:
            run_login("wrong-password")
        self.assertEqual(raised.exception.status_code, 429)
        headers = {key.lower(): value for key, value in (raised.exception.headers or {}).items()}
        self.assertIn("retry-after", headers)
        self.assertGreaterEqual(int(headers["retry-after"]), 1)

    def test_successful_login_resets_the_counter(self):
        for _ in range(3):
            with self.assertRaises(HTTPException):
                run_login("wrong-password")
        response = run_login(TEST_PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertIn("set-cookie", {key.lower() for key in response.headers.keys()})
        self.assertEqual(
            admin_dashboard._login_failures.count("login:203.0.113.7", admin_dashboard.LOGIN_ATTEMPT_WINDOW),
            0,
        )
        for _ in range(admin_dashboard.LOGIN_ATTEMPT_LIMIT):
            with self.assertRaises(HTTPException) as raised:
                run_login("wrong-password")
            self.assertEqual(raised.exception.status_code, 401)

    def test_throttle_key_uses_trusted_proxy_value(self):
        with patch.dict(os.environ, {"K_SERVICE": "mobilrs-test"}, clear=False):
            spoofed = login_request(forwarded="1.1.1.1, 203.0.113.7")
            self.assertEqual(admin_dashboard._client_ip(spoofed), "203.0.113.7")
            other_spoof = login_request(forwarded="9.9.9.9, 203.0.113.7")
            self.assertEqual(admin_dashboard._client_ip(other_spoof), "203.0.113.7")


if __name__ == "__main__":
    unittest.main()
