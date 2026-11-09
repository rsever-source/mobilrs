"""Güvenlik düzeltmelerinin kalıcılığını doğrulayan testler.

İki tür test vardır:

* ``security_utils`` davranış testleri: yalnızca standart kütüphane gerekir.
* Kaynak denetimleri: ``excel_vlookup_api.py`` ve ``admin_dashboard.py`` içinde
  güvenlik açığını geri getiren kalıpların (kaçışsız HTML, güvenilmeyen XFF,
  her istekte CSP hash hesabı vb.) yeniden oluşmadığını doğrular. Ağır
  bağımlılıklar (pandas, pdfplumber) kurulmadan çalışır.
"""

import base64
import hashlib
import os
import pathlib
import time
import unittest
from unittest.mock import patch

import security_utils
from security_utils import (
    SessionRevocationStore,
    SlidingWindowLimiter,
    attribute_hash,
    csp_attr_hashes,
    normalize_ip,
    parse_content_length,
    parse_session_token,
    resolve_client_ip,
    safe_https_url,
    session_signature,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def source(name):
    return (REPO_ROOT / name).read_text(encoding="utf-8")


class ClientIpTests(unittest.TestCase):
    def test_rightmost_forwarded_value_is_trusted(self):
        # Cloud Run istemcinin gönderdiği değeri silmez, gerçek IP'yi sona ekler.
        self.assertEqual(
            resolve_client_ip("1.1.1.1, 203.0.113.7", "10.0.0.1", trust_forwarded=True),
            "203.0.113.7",
        )

    def test_spoofed_left_value_does_not_change_key(self):
        first = resolve_client_ip("1.1.1.1, 203.0.113.7", None, trust_forwarded=True)
        second = resolve_client_ip("9.9.9.9, 203.0.113.7", None, trust_forwarded=True)
        self.assertEqual(first, second)

    def test_forwarded_header_is_ignored_without_trusted_proxy(self):
        self.assertEqual(
            resolve_client_ip("1.1.1.1", "10.0.0.1", trust_forwarded=False),
            "10.0.0.1",
        )

    def test_trust_is_detected_from_cloud_run_environment(self):
        with patch.dict(os.environ, {"K_SERVICE": "mobilrs-test"}, clear=False):
            self.assertEqual(
                resolve_client_ip("1.1.1.1, 198.51.100.4", "10.0.0.1"),
                "198.51.100.4",
            )
        with patch.dict(os.environ, {"K_SERVICE": "", "K_REVISION": ""}, clear=False):
            self.assertEqual(resolve_client_ip("1.1.1.1", "10.0.0.1"), "10.0.0.1")

    def test_invalid_values_fall_back_to_peer_or_unknown(self):
        self.assertEqual(
            resolve_client_ip("not-an-ip, also-bad", "10.0.0.1", trust_forwarded=True),
            "10.0.0.1",
        )
        self.assertEqual(resolve_client_ip("", None, trust_forwarded=True), "unknown")

    def test_ipv6_and_port_forms(self):
        self.assertEqual(normalize_ip("[2001:db8::1]:443"), "2001:db8::1")
        self.assertEqual(normalize_ip("203.0.113.7:53124"), "203.0.113.7")
        self.assertEqual(normalize_ip("2001:db8::1"), "2001:db8::1")


class SlidingWindowLimiterTests(unittest.TestCase):
    def test_limit_is_enforced_and_reported(self):
        limiter = SlidingWindowLimiter()
        for _ in range(5):
            self.assertEqual(limiter.check("k", 5, 60), (True, 0))
        allowed, retry_after = limiter.check("k", 5, 60)
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)

    def test_keys_are_independent(self):
        limiter = SlidingWindowLimiter()
        for _ in range(5):
            limiter.check("a", 5, 60)
        self.assertEqual(limiter.check("b", 5, 60), (True, 0))

    def test_window_expiry_releases_slots(self):
        now = [1000.0]
        limiter = SlidingWindowLimiter(clock=lambda: now[0])
        for _ in range(2):
            limiter.check("k", 2, 10)
        self.assertFalse(limiter.check("k", 2, 10)[0])
        now[0] += 11
        self.assertEqual(limiter.check("k", 2, 10), (True, 0))

    def test_count_reset_and_clear(self):
        limiter = SlidingWindowLimiter()
        limiter.check("k", 10, 60)
        limiter.check("k", 10, 60)
        self.assertEqual(limiter.count("k", 60), 2)
        limiter.reset("k")
        self.assertEqual(limiter.count("k", 60), 0)
        limiter.check("k", 10, 60)
        limiter.clear()
        self.assertEqual(limiter.count("k", 60), 0)


class CspHashTests(unittest.TestCase):
    def test_attribute_hash_matches_csp_spec(self):
        value = "loadOTV()"
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        self.assertEqual(attribute_hash(value), "'sha256-" + base64.b64encode(digest).decode() + "'")

    def test_entity_encoded_attribute_is_normalized(self):
        self.assertEqual(attribute_hash("a(&quot;b&quot;)"), attribute_hash('a("b")'))

    def test_script_and_style_hashes_are_collected_and_deduplicated(self):
        html = (
            '<button onclick="goNext()">1</button>'
            '<button onclick="goNext()">2</button>'
            '<div onkeydown="if(event.key)goNext()"></div>'
            '<div style="color:red"></div>'
        )
        script_hashes, style_hashes = csp_attr_hashes(html)
        self.assertEqual(len(script_hashes), 2)
        self.assertIn(attribute_hash("if(event.key)goNext()"), script_hashes)
        self.assertEqual(style_hashes, [attribute_hash("color:red")])

    def test_keyboard_and_focus_events_are_covered(self):
        # onkeydown CSP listesinde yoksa klavye ile gezinme engelleniyordu.
        for event in ("keydown", "keyup", "focus", "blur"):
            self.assertIn(event, security_utils.CSP_EVENT_ATTRIBUTES)

    def test_hashes_are_precomputed_once_at_import(self):
        text = source("excel_vlookup_api.py")
        self.assertNotIn("script_attr_hashes = sorted(", text)
        self.assertIn("_CSP_SCRIPT_ATTR_HASHES, _CSP_STYLE_ATTR_HASHES = csp_attr_hashes(", text)
        # Hesap yalnızca modül yüklenirken bir kez yapılmalı.
        self.assertEqual(text.count("csp_attr_hashes("), 1)
        start = text.index("async def add_security_headers")
        body = text[start:text.index("    path = request.url.path", start)]
        self.assertNotIn("csp_attr_hashes(", body)
        self.assertIn("_CSP_SCRIPT_ATTR_HASHES", body)


class SessionTests(unittest.TestCase):
    def test_signature_is_stable_and_depends_on_secret(self):
        first = session_signature("secret", "123", "n")
        self.assertEqual(first, session_signature("secret", "123", "n"))
        self.assertNotEqual(first, session_signature("other", "123", "n"))
        self.assertEqual(session_signature("", "123", "n"), "")

    def test_token_parsing(self):
        self.assertEqual(parse_session_token("123.abc.sig"), (123, "abc", "sig"))
        for bad in ("", "abc", "1.2", "x.abc.sig", "123." + "n" * 200 + ".sig"):
            self.assertIsNone(parse_session_token(bad))

    def test_revocation_store_blocks_until_expiry(self):
        now = [1000.0]
        store = SessionRevocationStore(clock=lambda: now[0], redis_url="")
        store.revoke("nonce", 1060)
        self.assertTrue(store.is_revoked("nonce"))
        self.assertFalse(store.is_revoked("other"))
        self.assertFalse(store.is_revoked(""))
        now[0] = 1061
        self.assertFalse(store.is_revoked("nonce"))

    def test_revoking_expired_session_is_a_noop(self):
        now = [1000.0]
        store = SessionRevocationStore(clock=lambda: now[0], redis_url="")
        store.revoke("nonce", 900)
        self.assertFalse(store.is_revoked("nonce"))

    def test_store_without_redis_url_uses_memory_only(self):
        # Canlıda REDIS_URL tanımlı değil; ek altyapı varsayılmıyor.
        store = SessionRevocationStore(redis_url="")
        self.assertIsNone(store._client())


class UrlAndBodyTests(unittest.TestCase):
    def test_only_https_urls_survive(self):
        self.assertEqual(safe_https_url("https://engelli.me/x"), "https://engelli.me/x")
        for bad in (
            "javascript:alert(1)",
            "http://engelli.me/x",
            "data:text/html,<script>",
            "//engelli.me/x",
            "/admin",
            "https://",
            "https://engelli.me/\nSet-Cookie: x",
            "",
            None,
        ):
            self.assertEqual(safe_https_url(bad), "", f"reddedilmeliydi: {bad!r}")

    def test_content_length_parsing(self):
        self.assertEqual(parse_content_length("123"), 123)
        self.assertEqual(parse_content_length(" 42 "), 42)
        for bad in ("", "-1", "abc", None):
            self.assertIsNone(parse_content_length(bad))


class ApiSourceTests(unittest.TestCase):
    """Kaynakta güvenlik açığını geri getiren kalıplar bulunmamalı."""

    @classmethod
    def setUpClass(cls):
        cls.text = source("excel_vlookup_api.py")

    def test_rate_limit_does_not_use_spoofable_first_ip(self):
        self.assertNotIn('forwarded.split(",")[0]', self.text)
        self.assertIn("resolve_client_ip(", self.text)

    def test_upload_limit_checks_declared_size_and_streams(self):
        self.assertIn("guard_request_body(request)", self.text)
        self.assertIn("chunk = await upload.read(UPLOAD_CHUNK_SIZE)", self.text)
        self.assertNotIn("data = await upload.read()\n", self.text)

    def test_concurrent_heavy_work_is_bounded(self):
        self.assertIn("HEAVY_WORK_CONCURRENCY = 2", self.text)
        self.assertIn("run_heavy_job(build_excel_result", self.text)
        self.assertIn("run_heavy_job(build_pdf_result", self.text)

    def test_archive_expansion_limit_is_lowered(self):
        self.assertIn("MAX_ARCHIVE_UNCOMPRESSED = 64 * 1024 * 1024", self.text)

    def test_otv_fields_are_html_escaped(self):
        for field in ("brand", "model", "trim", "locality", "source_name", "checked_at"):
            self.assertNotIn("'+(v." + field + "||", self.text, f"kaçışsız alan: {field}")
        self.assertIn("esc(v.trim||'')", self.text)
        self.assertIn("esc(v.checked_at||'—')", self.text)
        self.assertNotIn('data-brand="\'+String(b).replace(', self.text)
        self.assertIn('data-brand="\'+esc(b)+\'">\'+esc(b)', self.text)


class AdminSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = source("admin_dashboard.py")

    def test_session_lifetime_is_shortened(self):
        self.assertIn("SESSION_TTL = 12 * 60 * 60", self.text)
        self.assertNotIn("SESSION_TTL = 7 * 24 * 60 * 60", self.text)

    def test_logout_revokes_session(self):
        self.assertIn("SESSION_REVOCATIONS.revoke(", self.text)
        self.assertIn("if SESSION_REVOCATIONS.is_revoked(nonce):", self.text)

    def test_login_is_throttled_and_delayed(self):
        self.assertIn("LOGIN_ATTEMPT_LIMIT = 5", self.text)
        self.assertIn("_login_failures.check(", self.text)
        self.assertIn("await asyncio.sleep(", self.text)

    def test_panel_links_are_sanitized_in_js_and_python(self):
        self.assertNotIn("a.href=item.url", self.text)
        self.assertNotIn("a.href=detail.url", self.text)
        self.assertIn("safeHref(item.url)", self.text)
        self.assertIn("safeHref(detail.url)", self.text)
        self.assertIn("JSONResponse(_sanitize_urls(result)", self.text)
        self.assertIn('"url", "html_url", "final_url", "source_url", "locality_source_url"', self.text)


if __name__ == "__main__":
    unittest.main()
