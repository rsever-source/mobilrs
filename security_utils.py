"""Engelli.me güvenlik yardımcıları.

Bu modül bilinçli olarak yalnızca standart kütüphaneyi kullanır. Böylece
güvenlik davranışı (istemci IP çözümleme, hız sınırlama, oturum iptali,
CSP hash üretimi, URL doğrulama) FastAPI, pandas ve pdfplumber gibi ağır
bağımlılıklar kurulmadan da test edilebilir.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html as html_lib
import ipaddress
import os
import re
import threading
import time
from urllib.parse import urlsplit

SESSION_COOKIE_NAME = "eng_admin_session"

# ---------------------------------------------------------------------------
# İstemci IP çözümleme
# ---------------------------------------------------------------------------


def normalize_ip(value):
    """Metni geçerliyse normalleştirilmiş IP adresine çevirir, değilse '' döner."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("["):
        # [2001:db8::1]:443 gibi köşeli parantezli IPv6
        end = text.find("]")
        if end > 0:
            text = text[1:end]
    elif text.count(":") == 1:
        # 203.0.113.7:53124 gibi IPv4:port
        host, _, port = text.partition(":")
        if port.isdigit():
            text = host
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return ""


def resolve_client_ip(forwarded, peer, trust_forwarded=None):
    """İstemci IP'sini, proxy güvenine göre çözer.

    Cloud Run, istemcinin gönderdiği ``X-Forwarded-For`` değerini **silmez**;
    gerçek istemci IP'sini listenin sonuna ekler. Bu yüzden listedeki ilk
    değer saldırgan tarafından seçilebilir; güvenilir kabul edilen tek değer
    en sağdaki geçerli IP'dir.

    ``trust_forwarded`` verilmezse Cloud Run ortam değişkenlerine bakılır:
    başlık yalnızca bilinen bir platform proxy'si arkasında okunur. Aksi
    hâlde istek sahibi başlığı serbestçe uydurabileceği için yok sayılır.
    """
    if trust_forwarded is None:
        trust_forwarded = bool(os.environ.get("K_SERVICE") or os.environ.get("K_REVISION"))
    if trust_forwarded and forwarded:
        parts = [part.strip() for part in str(forwarded).split(",") if part.strip()]
        for candidate in reversed(parts):
            ip = normalize_ip(candidate)
            if ip:
                return ip
        return normalize_ip(peer) or "unknown"
    return normalize_ip(peer) or "unknown"


# ---------------------------------------------------------------------------
# Hız sınırlama
# ---------------------------------------------------------------------------


class SlidingWindowLimiter:
    """Anahtar başına kayan pencere sayacı.

    ``check`` ya ``(True, 0)`` ya da ``(False, beklenecek_saniye)`` döner.
    Sayaçlar süreç içindedir; çok örnekli kurulumda her örnek kendi
    sayacını tutar (bilinen sınırlama, rapor notlarında belirtilmiştir).
    """

    def __init__(self, max_keys=4096, clock=time.monotonic):
        self._hits = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys
        self._clock = clock

    def check(self, key, limit, window):
        now = self._clock()
        cutoff = now - window
        with self._lock:
            hits = [stamp for stamp in self._hits.get(key, ()) if stamp > cutoff]
            if len(hits) >= limit:
                retry_after = max(1, int(window - (now - hits[0])) + 1)
                self._hits[key] = hits
                return False, retry_after
            hits.append(now)
            self._hits[key] = hits
            self._evict(now, window)
            return True, 0

    def count(self, key, window):
        """Pencere içindeki kayıt sayısını döndürür (kayıt eklemez)."""
        now = self._clock()
        cutoff = now - window
        with self._lock:
            hits = [stamp for stamp in self._hits.get(key, ()) if stamp > cutoff]
            if hits:
                self._hits[key] = hits
            else:
                self._hits.pop(key, None)
            return len(hits)

    def reset(self, key):
        with self._lock:
            self._hits.pop(key, None)

    def clear(self):
        """Tüm sayaçları siler (testler ve bakım için)."""
        with self._lock:
            self._hits.clear()

    def _evict(self, now, window):
        if len(self._hits) <= self._max_keys:
            return
        cutoff = now - window
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            self._hits.pop(key, None)
        while len(self._hits) > self._max_keys:
            oldest = min(self._hits, key=lambda k: self._hits[k][-1])
            self._hits.pop(oldest, None)


# ---------------------------------------------------------------------------
# CSP hash üretimi
# ---------------------------------------------------------------------------

# HTML'de kullanılan satır içi olay öznitelikleri. Liste dışı bir olay
# (ör. onmouseenter) CSP tarafından engellenir; bu yüzden kapsam geniş
# tutulur ve hash yalnızca ilgili öznitelik varsa üretilir.
CSP_EVENT_ATTRIBUTES = (
    "click",
    "dblclick",
    "submit",
    "change",
    "input",
    "load",
    "keydown",
    "keyup",
    "keypress",
    "focus",
    "blur",
    "pointerdown",
    "pointerup",
    "mouseenter",
)

_SCRIPT_ATTR_RE = re.compile(
    r'\bon(?:' + "|".join(CSP_EVENT_ATTRIBUTES) + r')\s*=\s*"([^"]*)"',
    re.IGNORECASE,
)
_STYLE_ATTR_RE = re.compile(r'\bstyle\s*=\s*"([^"]*)"', re.IGNORECASE)


def attribute_hash(value):
    digest = hashlib.sha256(html_lib.unescape(value).encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def csp_attr_hashes(sources):
    """Statik HTML için ``script-src-attr`` / ``style-src-attr`` hash'lerini üretir.

    Girdi statiktir; sonuç istek başına yeniden hesaplanmak yerine bir kez
    hesaplanıp sabitlenmelidir.
    """
    script_hashes = sorted({attribute_hash(v) for v in _SCRIPT_ATTR_RE.findall(sources)})
    style_hashes = sorted({attribute_hash(v) for v in _STYLE_ATTR_RE.findall(sources)})
    return script_hashes, style_hashes


# ---------------------------------------------------------------------------
# Oturum imzası ve iptali
# ---------------------------------------------------------------------------


def session_signature(secret, expiry, nonce):
    """Oturum çerezi imzası. ``secret`` boşsa imza üretilmez."""
    if not secret:
        return ""
    payload = str(expiry) + "." + str(nonce)
    return hmac.new(str(secret).encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def parse_session_token(token, max_nonce=128):
    """``expiry.nonce.signature`` biçimini çözer; bozuksa ``None`` döner."""
    try:
        expiry, nonce, signature = str(token or "").split(".", 2)
        expires_at = int(expiry)
    except (ValueError, TypeError):
        return None
    if len(nonce) > max_nonce:
        return None
    return expires_at, nonce, signature


class SessionRevocationStore:
    """Çıkış yapılan oturumların nonce listesini tutar.

    Varsayılan backend süreç içi sözlüktür ve ek altyapı gerektirmez. Bu
    durumda iptal yalnızca isteği karşılayan örnekte geçerlidir; Cloud Run'da
    birden çok örnek varsa diğer örnekler çerezi süresi dolana kadar kabul
    eder. ``REDIS_URL`` tanımlıysa nonce'lar Redis'e de yazılır ve tüm
    örnekler aynı listeyi görür.
    """

    REDIS_PREFIX = "engelli:admin:revoked:"

    def __init__(self, clock=time.time, redis_client=None, redis_url=None):
        self._items = {}
        self._lock = threading.Lock()
        self._clock = clock
        self._redis = redis_client
        self._redis_url = redis_url
        self._redis_ready = redis_client is not None

    def _client(self):
        if self._redis_ready:
            return self._redis
        self._redis_ready = True
        url = (self._redis_url if self._redis_url is not None else os.environ.get("REDIS_URL", "")).strip()
        if not url:
            self._redis = None
            return None
        try:
            import redis  # isteğe bağlı; REDIS_URL yoksa hiç yüklenmez

            client = redis.from_url(
                url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
            )
            client.ping()
            self._redis = client
        except Exception:
            self._redis = None
        return self._redis

    def revoke(self, nonce, expires_at):
        if not nonce:
            return
        remaining = int(expires_at - self._clock())
        if remaining <= 0:
            return
        with self._lock:
            self._items[nonce] = expires_at
        client = self._client()
        if client is not None:
            try:
                client.setex(self.REDIS_PREFIX + nonce, remaining, "1")
            except Exception:
                pass

    def is_revoked(self, nonce):
        if not nonce:
            return False
        now = self._clock()
        with self._lock:
            expires_at = self._items.get(nonce)
            if expires_at is not None and expires_at <= now:
                self._items.pop(nonce, None)
                expires_at = None
            alive = expires_at is not None
        if alive:
            return True
        client = self._client()
        if client is None:
            return False
        try:
            return bool(client.exists(self.REDIS_PREFIX + nonce))
        except Exception:
            # Redis erişilemezse iptal listesi devre dışı kalır; oturum
            # imzası ve süre kontrolü çalışmaya devam eder.
            return False

    def clear(self):
        """Testler ve bakım için bellek içi listeyi temizler."""
        with self._lock:
            self._items.clear()


# ---------------------------------------------------------------------------
# URL ve istek boyutu doğrulama
# ---------------------------------------------------------------------------


def safe_https_url(value):
    """Yalnızca geçerli ``https://`` adreslerini döndürür, diğerlerinde ''."""
    text = str(value or "").strip()
    if not text or any(ch in text for ch in ("\n", "\r", "\t", "\x00")):
        return ""
    try:
        parsed = urlsplit(text)
    except ValueError:
        return ""
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return ""
    return text


def parse_content_length(value):
    """Content-Length başlığını negatif olmayan tamsayıya çevirir."""
    try:
        size = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return size if size >= 0 else None
