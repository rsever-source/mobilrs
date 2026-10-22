import asyncio
import importlib
import os
import re
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import JSONResponse

import admin_dashboard

TEST_PASSWORD = "test-only-password"


class FakeState:
    csp_nonce = "test-nonce"


class FakeRequest:
    """admin_page/_require_session için gereken en küçük istek nesnesi."""

    def __init__(self, token=None, headers=None):
        self.cookies = {"eng_admin_session": token} if token else {}
        self.headers = headers or {}
        self.state = FakeState()


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


class AdminSessionCookieTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"ADMIN_PASSWORD": TEST_PASSWORD})
        patcher.start()
        self.addCleanup(patcher.stop)
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

    def test_cookie_lifetime_is_seven_days(self):
        header = session_cookie_header()
        self.assertIn("max-age=%d" % admin_dashboard.SESSION_TTL, header.lower())
        self.assertEqual(admin_dashboard.SESSION_TTL, 7 * 24 * 60 * 60)

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


if __name__ == "__main__":
    unittest.main()
