import asyncio, io, json, os, re, secrets, sys, time, uuid, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd, pdfplumber, uvicorn
import requests
from fastapi import BackgroundTasks, FastAPI, UploadFile, File, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from starlette.background import BackgroundTask
from security_utils import (
    SlidingWindowLimiter,
    csp_attr_hashes,
    parse_content_length,
    resolve_client_ip,
)

from tufe_service import get_current_tufe, save_cache
from otv_service import get_otv_data, refresh_otv_data, _load as load_otv_cache
from admin_dashboard import router as admin_dashboard_router

EK2_ROOT = Path(__file__).resolve().parent / "ek2-balthazard"
sys.path.insert(0, str(EK2_ROOT))
sys.path.insert(0, str(EK2_ROOT / "arac1"))
sys.path.insert(0, str(EK2_ROOT / "arac2"))
import arac1_sunucu as ek2_arac1  # noqa: E402
import arac2_sunucu as ek2_arac2  # noqa: E402


def _ek2_html(ad: str) -> str:
    return (EK2_ROOT / ad / f"{ad}.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Araç sayfalarının ortak portal görünümü
# ---------------------------------------------------------------------------
# Ek-2 araç sayfaları (arac1/arac2/arac3) kendi hesaplama motorlarını ve
# arayüz betiklerini korur. Burada yalnızca sayfa iskeleti — üst başlık, ana
# menü, erişilebilirlik düğmesi ve alt bilgi — ana sayfayla aynı görsel dile
# bağlanır. HTML dosyalarına dokunulmaz; ekleme istek sırasında yapılır.

_PORTAL_NAV_HTML = (
    '<nav class="portal-nav" aria-label="Ana menü"><ul>'
    '<li><a href="/">Ana Sayfa</a></li>'
    '<li><a href="/#news">Haberler</a></li>'
    '<li><a href="/#hesaplamalar" aria-current="true">Yardımcılar</a></li>'
    '<li><a href="/#otv-araclar">ÖTV Muafiyetli Araçlar</a></li>'
    '</ul></nav>'
)

_PORTAL_FOOTER_HTML = (
    '<footer class="portal-footer" aria-label="Site alt bilgisi">'
    '<div class="portal-footer-inner">'
    '<div class="portal-footer-top">'
    '<section class="portal-footer-brand" aria-label="Engelli.me">'
    '<a class="portal-footer-link" href="/" aria-label="Engelli.me ana sayfa">'
    '<img src="/logo.png?v=1" alt="" width="40" height="40" loading="lazy" decoding="async">'
    '<span>Engelli<span class="portal-footer-dot">.me</span></span></a>'
    '<p>Engelli hakları, mevzuat ve günlük yaşam için güncel haberler ve pratik araçlar.</p>'
    '</section>'
    '<nav class="portal-footer-nav" aria-label="Hızlı bağlantılar">'
    '<h2>Keşfet</h2>'
    '<a href="/#news">Güncel haberler</a>'
    '<a href="/#hesaplamalar">Yardımcılar</a>'
    '<a href="/#otv-araclar">ÖTV muafiyetli araçlar</a>'
    '</nav>'
    '<section class="portal-footer-contact" aria-label="İletişim ve bilgiler">'
    '<h2>İletişim ve bilgiler</h2>'
    '<a class="portal-footer-mail" href="mailto:info@engelli.me">info@engelli.me</a>'
    '<a class="portal-footer-legal" href="/kvkk">KVKK aydınlatma metni <span aria-hidden="true">→</span></a>'
    '</section>'
    '</div>'
    '<div class="portal-footer-bottom">'
    '<p>© 2026 Engelli.me</p>'
    '<p>Engelli hakları, güncel gelişmeler ve erişilebilir dijital araçlar.</p>'
    '</div>'
    '</div>'
    '</footer>'
)

_PORTAL_CHROME_CSS = """
:root{--paper:#fbfaf7;--paper-deep:#f3f1ea;--surface:#ffffff;--ink:#16211f;--ink-soft:#2b3733;
--muted:#5e6b66;--line:#e2ded5;--line-strong:#cfc9bd;--accent:#0f766e;--accent-ink:#0b5d56;
--accent-soft:#e7f2ef;--bg:#fbfaf7;--card:#ffffff;--blue:#0f766e;--soft:#e7f2ef;--radius:4px;
--font-serif:Georgia,"Iowan Old Style","Palatino Linotype","Book Antiqua",serif;
--font-sans:"Segoe UI",Inter,system-ui,-apple-system,sans-serif}
html{font-size:calc(16px * var(--font-scale,1));background:var(--paper)!important}
body{background:var(--paper)!important;color:var(--ink)!important;font-family:var(--font-sans)!important;
padding-top:0!important;padding-bottom:0!important;margin:0}
body>.app{max-width:1180px;margin:0 auto;padding-top:0!important;min-height:0;
background:var(--paper)!important}
body>.sayfa{max-width:1180px;margin:0 auto}
.site-header{position:static!important;z-index:60;min-height:0;background:var(--paper)!important;
color:var(--ink);border-bottom:1px solid var(--line);box-shadow:none;backdrop-filter:none}
.site-header-inner{width:min(1180px,calc(100% - 32px));min-height:0;margin:0 auto;padding:12px 0;
display:flex;align-items:center;gap:14px;justify-content:flex-start;flex-wrap:wrap}
.site-brand{order:1;flex-direction:row-reverse;color:var(--ink);font-family:var(--font-serif);
font-size:1.5rem;font-weight:700;letter-spacing:-.02em;gap:10px}
.site-brand-accent{color:var(--accent)}
.site-brand-logo{width:40px;height:40px;flex:0 0 40px;padding:0;border:1px solid var(--line);
border-radius:50%;background:#ffffff;box-shadow:none}
.portal-nav{order:2;margin-left:auto;min-width:0}
.portal-nav ul{display:flex;align-items:center;gap:1.15rem;list-style:none;margin:0;padding:0}
.portal-nav a{display:inline-block;padding:.35rem 0;color:var(--muted);font-size:.82rem;font-weight:600;
text-decoration:none;border-bottom:2px solid transparent;white-space:nowrap}
.portal-nav a:hover{color:var(--ink);text-decoration:none}
.portal-nav a[aria-current]{color:var(--ink);border-bottom-color:var(--accent)}
.site-accessibility-tools{order:3;margin-left:.2rem;position:relative}
.site-mobile-home,.site-scroll-home{display:none!important}
.site-accessibility-toggle{display:inline-flex!important;align-items:center;justify-content:center;
min-height:2.5rem;padding:.45rem .85rem;border:1px solid var(--line-strong);border-radius:3px;
background:var(--surface);color:var(--ink);font-size:.78rem;font-weight:700;cursor:pointer}
.site-accessibility-toggle:hover{border-color:var(--accent);color:var(--accent-ink)}
.site-accessibility-panel{display:none;position:absolute;right:0;top:calc(100% + .5rem);z-index:60;
width:min(21rem,calc(100vw - 2rem));padding:.85rem;background:var(--surface);color:var(--ink);
border:1px solid var(--line-strong);border-radius:4px;box-shadow:0 14px 34px rgba(0,0,0,.16);
flex-direction:column;gap:.6rem;align-items:stretch}
.site-accessibility-panel.open{display:flex}
.site-accessibility-panel-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem}
.site-accessibility-panel .site-tool-label{font-size:.7rem;font-weight:700;letter-spacing:.08em;
text-transform:uppercase;color:var(--muted);white-space:normal}
.site-accessibility-panel .site-accessibility-reset{font-size:.72rem;padding:.25rem .4rem;
background:transparent;border:1px solid transparent;color:var(--accent-ink);text-decoration:underline}
.site-accessibility-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.4rem}
.site-accessibility-options button:nth-child(n+4){grid-column:1/-1}
.site-accessibility-panel button{border:1px solid var(--line-strong);border-radius:3px;
background:var(--surface);color:var(--ink);font-size:.78rem;font-weight:700;padding:.5rem .3rem;cursor:pointer}
.site-accessibility-panel button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.sayfa{max-width:1180px!important;margin:0 auto;padding:0 0 36px}
body>.app .sayfa,body>.app .arac-duzeni{max-width:1180px}
body h1{font-family:var(--font-serif);font-weight:700;letter-spacing:-.02em;
font-size:clamp(1.65rem,3.1vw,2.25rem);line-height:1.16;color:var(--ink)}
body h2,body h3{font-family:var(--font-serif);letter-spacing:-.01em;color:var(--ink)}
.giris{color:var(--muted)}
.sekmeler{display:flex;gap:.35rem;padding:14px 0 0;margin:0 0 18px;
border-bottom:1px solid var(--line);border-top:0;flex-wrap:wrap}
.sekme{border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;
color:var(--muted);padding:.55rem .8rem;font-size:.82rem;font-weight:700;text-decoration:none;box-shadow:none}
.sekme:hover{color:var(--ink);background:transparent;text-decoration:none}
.sekme[aria-current]{color:var(--ink);border-bottom-color:var(--accent);background:transparent;box-shadow:none}
.kart{background:var(--card);border:1px solid var(--line);border-radius:4px;box-shadow:none}
.alt-bilgi{border-top:1px solid var(--line);margin-top:24px;padding-top:12px;
color:var(--muted);font-size:.78rem;line-height:1.6;background:transparent}
.alt-bilgi p{margin:0 0 .4rem}
.portal-footer{background:var(--paper-deep);border-top:1px solid var(--line);margin-top:34px;
padding:26px 16px 30px;color:var(--ink);font-size:.82rem;line-height:1.6}
.portal-footer p{margin:0 0 .5rem}
.portal-footer-inner{width:min(1180px,100%);margin:0 auto}
.portal-footer-top{display:grid;grid-template-columns:1.5fr 1fr 1.1fr;gap:26px;
padding-bottom:18px;margin-bottom:14px;border-bottom:1px solid var(--line-strong);text-align:left}
.portal-footer h2{font-family:var(--font-sans);font-size:.7rem;font-weight:800;letter-spacing:.12em;
text-transform:uppercase;color:var(--muted);margin:0 0 .55rem}
.portal-footer-brand p{color:var(--muted);font-size:.78rem;margin:.6rem 0 0;max-width:34ch}
.portal-footer-link{display:inline-flex;align-items:center;gap:10px;color:var(--ink);
font-family:var(--font-serif);font-size:1.3rem;font-weight:700;text-decoration:none;text-align:left}
.portal-footer-link img{width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:#fff}
.portal-footer-dot{color:var(--accent)}
.portal-footer-nav,.portal-footer-contact{display:flex;flex-direction:column;align-items:flex-start;gap:.3rem}
.portal-footer-nav a,.portal-footer-contact a{color:var(--ink-soft);font-size:.8rem;text-decoration:none}
.portal-footer-nav a:hover,.portal-footer-contact a:hover{color:var(--accent-ink);text-decoration:underline}
.portal-footer-mail{font-weight:700;color:var(--accent-ink)!important}
.portal-footer-bottom{display:flex;flex-wrap:wrap;gap:.3rem 1.4rem;color:var(--muted);font-size:.74rem}
.portal-footer-bottom p{margin:0}
body.high-contrast .site-header,body.high-contrast .site-accessibility-panel{background:#fff;
border-color:#000;border-width:2px}
body.high-contrast .site-accessibility-toggle,body.high-contrast .site-accessibility-panel button{
background:#fff;color:#000;border:2px solid #000}
body.high-contrast .site-accessibility-panel button[aria-pressed="true"]{background:#000;color:#fff}
body.high-contrast .portal-nav a,body.high-contrast .site-brand,body.high-contrast .portal-footer a,
body.high-contrast .portal-footer p,body.high-contrast .portal-footer h2{color:#000}
body.high-contrast .portal-nav a[aria-current]{border-bottom:3px solid #0000ee}
body.high-contrast .portal-footer-top,body.high-contrast .alt-bilgi{border-color:#000}
body.dark-mode .site-header{background:#101a18;border-bottom-color:#2c3a36}
body.dark-mode .site-brand,body.dark-mode .portal-nav a,body.dark-mode .portal-footer a,
body.dark-mode .portal-footer-brand p,body.dark-mode .portal-footer h2,body.dark-mode .portal-footer p{color:#e6efe9}
body.dark-mode .site-accessibility-toggle,body.dark-mode .site-accessibility-panel{background:#16211f;
color:#e6efe9;border-color:#3a4a45}
body.dark-mode .site-accessibility-panel button{background:#101a18;color:#e6efe9;border-color:#3a4a45}
body.dark-mode .site-accessibility-panel button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#04120f}
body.dark-mode .portal-footer{background:#0e1715;border-top-color:#2c3a36}
body.dark-mode .portal-footer-top{border-bottom-color:#2c3a36}
@media(max-width:900px){
.portal-footer-top{grid-template-columns:1fr 1fr}
}
@media(max-width:760px){
.site-header{display:block!important;min-height:0}
.site-header-inner{width:calc(100% - 24px);padding:10px 0;gap:8px 10px}
.site-brand{font-size:1.25rem;gap:8px}
.site-brand-logo{width:34px;height:34px;flex-basis:34px}
.portal-nav{order:4;margin-left:0;width:100%;overflow-x:auto;border-top:1px solid var(--line);padding-top:6px}
.portal-nav ul{gap:.9rem}
.portal-nav a{font-size:.78rem;padding:.3rem 0}
.site-accessibility-tools{order:3;margin-left:auto}
.site-accessibility-toggle{min-height:2.2rem;padding:.35rem .6rem;font-size:.72rem}
.portal-footer-top{grid-template-columns:1fr;gap:18px}
}
@media(max-width:420px){
.portal-nav ul{gap:.7rem}
.portal-nav a{font-size:.72rem}
}
"""


def _ek2_sayfa(ad: str, yer_tutucu: str, adres: str, nonce: str) -> str:
    govde = _ek2_html(ad).replace(yer_tutucu, adres)
    # Ortak portal üst başlığı: ana menü ve erişilebilirlik düğmesi.
    if '<div class="site-accessibility-tools">' in govde:
        govde = govde.replace('<div class="site-accessibility-tools">',
                              _PORTAL_NAV_HTML + '<div class="site-accessibility-tools">', 1)
    # Ortak alt bilgi sayfa sonuna eklenir; aracın kendi bilgilendirme notu korunur.
    son = govde.rfind("</body>")
    if son != -1:
        govde = govde[:son] + _PORTAL_FOOTER_HTML + govde[son:]
    govde = govde.replace("</head>", f'<style nonce="{nonce}">{_PORTAL_CHROME_CSS}</style></head>', 1)
    return (govde.replace("<style>", f'<style nonce="{nonce}">')
                 .replace("<script", f'<script nonce="{nonce}"'))


app = FastAPI(title="Rdv Asistan", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(admin_dashboard_router)

CHAT_HTML = r'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Engelli.me Sohbet</title>
<meta name="description" content="Engelli.me canlı sohbet odası.">
<style>
:root{--ink:#182234;--muted:#697386;--blue:#1769e0;--line:#e4e8ef;--white:#fff}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:#f4f6f9;color:var(--ink);font-family:Inter,Aptos,"Segoe UI",system-ui,-apple-system,sans-serif}
.shell{height:100%;min-height:100%;display:flex;flex-direction:column;max-width:1100px;margin:0 auto;background:#fff}
.head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--line)}
.brand{font-size:21px;font-weight:850;letter-spacing:-.5px}.brand span{color:var(--blue)}
.back{color:var(--blue);text-decoration:none;font-size:13px;font-weight:800}
.chat{flex:1;min-height:0;padding:12px}
.chat iframe{display:block;width:100%;height:calc(100vh - 82px);min-height:520px;border:1px solid var(--line);border-radius:16px;background:#fff}
@media(max-width:640px){.head{padding:14px 16px}.chat{padding:8px}.chat iframe{height:calc(100vh - 68px);min-height:480px;border-radius:12px}}
</style>
</head>
<body>
<main class="shell">
<header class="head"><div class="brand">Engelli<span>.me</span> Sohbet</div><a class="back" href="https://engelli.me/">← Ana Sayfa</a></header>
<div class="chat"><iframe src="https://klaklak.com/embed/engellime" title="Engelli.me canlı sohbet" loading="eager" allow="clipboard-write"></iframe></div>
</main>
</body>
</html>'''


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(24)
    request.state.csp_nonce = nonce
    if request.method == "POST" and request.url.path in UPLOAD_PATHS:
        declared = parse_content_length(request.headers.get("content-length"))
        if declared is not None and declared > MAX_REQUEST_BODY:
            # Gövde ayrıştırılmadan reddedilir; çok büyük istek diske/ belleğe alınmaz.
            response = JSONResponse(
                {"detail": "İstek gövdesi çok büyük. Maksimum " + str(MAX_REQUEST_BODY // (1024 * 1024)) + " MB."},
                status_code=413,
            )
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"script-src-attr 'unsafe-hashes' {' '.join(_CSP_SCRIPT_ATTR_HASHES)}; "
        f"style-src 'self' 'nonce-{nonce}'; "
        f"style-src-attr 'unsafe-hashes' {' '.join(_CSP_STYLE_ATTR_HASHES)}; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-src https://klaklak.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    path = request.url.path
    if request.method != "GET" or path in {"/tufe-guncelle", "/kira-hesapla", "/excel-islem", "/pdf-excel-islem", "/api/otv/yenile"}:
        response.headers["Cache-Control"] = "no-store"
    elif path in {"/", "/api/news", "/api/otv", "/robots.txt", "/sitemap.xml"}:
        response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
    elif path in {"/logo.png", "/favicon.png", "/apple-touch-icon.png"}:
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif path.startswith("/brand-logos/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif path == "/kvkk":
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        response.headers["Cache-Control"] = "no-store"
    return response



OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 2000
MAX_ARCHIVE_UNCOMPRESSED = 64 * 1024 * 1024
MAX_EXCEL_ROWS = 200_000
MAX_PDF_PAGES = 50
MAX_PDF_ROWS = 100_000
FILE_PROCESS_TIMEOUT = 90
RATE_LIMIT_WINDOW = 60
UPLOAD_RATE_LIMIT = 6
REFRESH_RATE_LIMIT_WINDOW = 300
REFRESH_RATE_LIMIT = 1
_RATE_LIMITS = SlidingWindowLimiter()
_REFRESH_LOCK = asyncio.Lock()

# Ağır dosya işlemleri (pandas/pdfplumber) aynı anda en fazla bu kadar
# çalışır. Sınır, 512 MiB'lik Cloud Run örneğinde bellek taşmasını ve
# zaman aşımına uğrayan işlerin birikmesini engeller.
HEAVY_WORK_CONCURRENCY = 2
HEAVY_WORK_QUEUE_TIMEOUT = 30
_HEAVY_WORK_POOL = ThreadPoolExecutor(max_workers=HEAVY_WORK_CONCURRENCY, thread_name_prefix="heavy")
_HEAVY_WORK_SLOTS = asyncio.Semaphore(HEAVY_WORK_CONCURRENCY)
MAX_REQUEST_BODY = 2 * MAX_FILE_SIZE + 8 * 1024 * 1024
UPLOAD_PATHS = frozenset({"/excel-islem", "/pdf-excel-islem"})
UPLOAD_CHUNK_SIZE = 1024 * 1024
MONTH_NAMES = {1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}


def client_ip_from_request(request: Request) -> str:
    """İstemci IP'sini platformun eklediği güvenilir değerden çözer.

    Cloud Run, istemcinin gönderdiği X-Forwarded-For değerini koruyup gerçek
    istemci IP'sini sona eklediği için yalnızca en sağdaki değer güvenilirdir.
    """
    return resolve_client_ip(
        request.headers.get("x-forwarded-for", ""),
        request.client.host if request.client else None,
    )


async def enforce_rate_limit(request: Request, bucket: str, limit: int, window: int):
    client_ip = client_ip_from_request(request)
    allowed, retry_after = _RATE_LIMITS.check(f"{bucket}:{client_ip}", limit, window)
    if not allowed:
        raise HTTPException(429, "Çok fazla istek. Lütfen biraz sonra tekrar deneyin.", headers={"Retry-After": str(retry_after)})


def unique_output_path(ext):
    return os.path.join(OUTPUT_DIR, f"rdv_{uuid.uuid4().hex}.{ext}")


def delete_file(path):
    try:
        if os.path.exists(path): os.remove(path)
    except Exception: pass


async def run_heavy_job(func, *args, timeout):
    """Ağır işlemi sınırlı havuzda çalıştırır.

    Zaman aşımında iş parçacığı durdurulamaz (Python bunu desteklemez) ama
    yeni işler sıraya girer ve eşzamanlılık sabit kalır; böylece yavaş
    istekler birikerek bellek/CPU tüketmez.
    """
    try:
        await asyncio.wait_for(_HEAVY_WORK_SLOTS.acquire(), timeout=HEAVY_WORK_QUEUE_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(503, "Sunucu şu anda yoğun. Lütfen biraz sonra tekrar deneyin.", headers={"Retry-After": "15"})
    future = asyncio.get_running_loop().run_in_executor(_HEAVY_WORK_POOL, func, *args)
    future.add_done_callback(lambda _future: _HEAVY_WORK_SLOTS.release())
    try:
        return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(504, "İşlem zaman sınırını aştı.")


def guard_request_body(request, max_size=MAX_REQUEST_BODY):
    """Content-Length sınırı aşıyorsa gövdeyi okumadan isteği reddeder."""
    declared = parse_content_length(request.headers.get("content-length"))
    if declared is not None and declared > max_size:
        raise HTTPException(413, f"İstek gövdesi çok büyük. Maksimum {max_size//(1024*1024)} MB.")
    return declared


async def read_upload_limited(upload, max_size=MAX_FILE_SIZE):
    """Yüklenen dosyayı parça parça okur ve sınır aşımında erken durur."""
    declared = getattr(upload, "size", None)
    if isinstance(declared, int) and declared > max_size:
        raise HTTPException(413, f"{upload.filename or 'Dosya'} çok büyük. Maksimum {max_size//(1024*1024)} MB.")
    chunks = []
    total = 0
    while True:
        chunk = await upload.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(413, f"{upload.filename or 'Dosya'} çok büyük. Maksimum {max_size//(1024*1024)} MB.")
        chunks.append(chunk)
    return b"".join(chunks)


def check_extension(filename, allowed): return (filename or "").lower().endswith(allowed)

def validate_file_signature(data, filename, content_type=""):
    name=(filename or "").lower()
    if name.endswith(".pdf"):
        if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(400,"PDF MIME türü geçersiz.")
        ok=data.startswith(b"%PDF")
    elif name.endswith(".xlsx"):
        if content_type and content_type not in {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip", "application/octet-stream"}:
            raise HTTPException(400,"XLSX MIME türü geçersiz.")
        ok=data.startswith(b"PK\x03\x04")
    elif name.endswith(".xls"):
        if content_type and content_type not in {"application/vnd.ms-excel", "application/octet-stream"}:
            raise HTTPException(400,"XLS MIME türü geçersiz.")
        ok=data.startswith(b"\xD0\xCF\x11\xE0")
    else:
        ok=True
    if not ok:
        raise HTTPException(400,"Dosya türü içeriğiyle uyuşmuyor.")
    if name.endswith(".xlsx"):
        validate_xlsx_zip(data)


def validate_xlsx_zip(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise HTTPException(413,"XLSX arşivi çok fazla dosya içeriyor.")
            total = 0
            for info in infos:
                if info.flag_bits & 0x1 or len(info.filename) > 255:
                    raise HTTPException(400,"XLSX arşivi güvenli değil.")
                total += info.file_size
                if info.compress_size and info.file_size / info.compress_size > 1000:
                    raise HTTPException(413,"XLSX sıkıştırma oranı güvenli sınırı aşıyor.")
            if total > MAX_ARCHIVE_UNCOMPRESSED:
                raise HTTPException(413,"XLSX açılmış boyut sınırını aşıyor.")
    except HTTPException:
        raise
    except (zipfile.BadZipFile, OSError):
        raise HTTPException(400,"Geçerli bir XLSX arşivi yükleyin.")

def normalize_column_name(v): return str(v).strip()


def select_join_column(a, b, command):
    common = [c for c in a.columns if c in b.columns]
    if not common: raise HTTPException(400, "İki Excel dosyasında ortak sütun bulunamadı.")
    cl = command.lower()
    for c in common:
        if str(c).lower() in cl: return c
    for p in ["id","kod","code","no","numara","musteri","müşteri","container","konteyner","referans","ref","sicil"]:
        for c in common:
            if p in str(c).lower(): return c
    return common[0]


def find_command_columns(df, command): return [c for c in df.columns if str(c).lower() in command.lower()]
def money_tr(v): return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " TL"


def build_excel_result(d1, d2, command):
    a=pd.read_excel(io.BytesIO(d1), nrows=MAX_EXCEL_ROWS + 1); b=pd.read_excel(io.BytesIO(d2), nrows=MAX_EXCEL_ROWS + 1)
    if a.shape[0] > MAX_EXCEL_ROWS or b.shape[0] > MAX_EXCEL_ROWS:
        raise HTTPException(413,"Excel satır sınırı aşıldı.")
    if a.empty or b.empty: raise HTTPException(400,"Excel dosyalarında veri bulunamadı.")
    a.columns=[normalize_column_name(c) for c in a.columns]; b.columns=[normalize_column_name(c) for c in b.columns]; k=command.lower().strip()
    if any(w in k for w in ["düşeyara","duseyara","vlookup","birleştir","birlestir","merge","eşleştir","eslestir"]):
        c=select_join_column(a,b,command); result=pd.merge(a,b,on=c,how="left",suffixes=("","_referans"))
    elif any(w in k for w in ["pivot","özet","ozet","grupla","toplam"]):
        cc=find_command_columns(a,command); nums=a.select_dtypes(include="number").columns.tolist()
        if not nums: raise HTTPException(400,"Pivot/özet için sayısal sütun bulunamadı.")
        val=next((c for c in cc if c in nums),nums[0]); idx=next((c for c in cc if c!=val),None) or next((c for c in a.columns if c!=val),None)
        if idx is None: raise HTTPException(400,"Pivot için grup sütunu bulunamadı.")
        result=pd.pivot_table(a,values=val,index=idx,aggfunc="sum",fill_value=0).reset_index()
    else: result=a.copy()
    if result.shape[0] > MAX_EXCEL_ROWS: raise HTTPException(413,"İşlem sonucu satır sınırını aşıyor.")
    out=unique_output_path("xlsx"); result.to_excel(out,index=False); return out


def build_pdf_result(pdf_data):
    rows=[]
    with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES: raise HTTPException(413,"PDF sayfa sınırını aşıyor.")
        for page in pdf.pages:
            tables=page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if row:
                            rr=[str(c).replace("\n"," ").strip() if c is not None else "" for c in row]
                            if any(rr): rows.append(rr)
            else:
                txt=page.extract_text()
                if txt: rows.extend([[ln.strip()] for ln in txt.split("\n") if ln.strip()])
            if len(rows) > MAX_PDF_ROWS: raise HTTPException(413,"PDF satır sınırını aşıyor.")
    if not rows: raise HTTPException(400,"PDF içinde Excel'e aktarılacak metin veya tablo bulunamadı. Taranmış/resim PDF ise OCR gerekir.")
    mc=max(map(len,rows)); df=pd.DataFrame([r+[""]*(mc-len(r)) for r in rows]); out=unique_output_path("xlsx"); df.to_excel(out,index=False,header=False); return out


def next_renewal_year(m):
    t=date.today(); return t.year if m >= t.month else t.year+1


def previous_month(y,m): return (y-1,12) if m==1 else (y,m-1)


@app.post("/tufe-guncelle")
async def spark_tufe_guncelle(request: Request, authorization: str|None=Header(default=None), source:str=Query(...), rate:float=Query(...), year:int=Query(...), month:int=Query(...)):
    await enforce_rate_limit(request, "tufe-update", 5, 300)
    expected=os.environ.get("SPARK_TUFE_KEY","").strip()
    if not expected: raise HTTPException(500,"SPARK_TUFE_KEY ayarlanmamış.")
    if authorization != f"Bearer {expected}": raise HTTPException(401,"Yetkisiz erişim.", headers={"WWW-Authenticate":"Bearer"})
    p=urlparse(source)
    if (p.hostname or "").lower() != "veriportali.tuik.gov.tr" or not p.path.startswith("/tr/press/"):
        raise HTTPException(400,"Sadece resmi TÜİK haber bülteni kabul edilir.")
    if not 1 <= month <= 12 or not 2020 <= year <= 2100 or not 0 < rate < 200:
        raise HTTPException(400,"Geçersiz parametre.")
    data={"rate":round(float(rate),2),"year":year,"month":month,"period":f"{MONTH_NAMES[month]} {year}","source":source,"data_mode":"spark"}
    if not save_cache(data): raise HTTPException(500,"Veri Redis'e kaydedilemedi.")
    return JSONResponse({"ok":True,"message":"TÜFE başarıyla kaydedildi.","oran":f"{rate:.2f}".replace(".",","),"donem":data["period"],"source":source})


@app.post("/kira-hesapla")
async def kira_hesapla(mevcut_kira:float=Form(...), yenileme_ayi:int=Form(...)):
    if mevcut_kira <= 0 or not 1 <= yenileme_ayi <= 12: raise HTTPException(400,"Geçerli kira ve yenileme ayı gir.")
    try: tufe=get_current_tufe()
    except Exception: raise HTTPException(503,"Güncel TÜFE verisi şu anda alınamadı.")
    rate=float(tufe["rate"]); ty=int(tufe["year"]); tm=int(tufe["month"]); period=str(tufe["period"]); source=str(tufe["source"])
    artis=mevcut_kira*rate/100; yeni=mevcut_kira+artis; ry=next_renewal_year(yenileme_ayi); target=previous_month(ry,yenileme_ayi); current=(ty,tm)
    if current == target:
        durum=f"{MONTH_NAMES[yenileme_ayi]} {ry} kira yenilemesi için gerekli {period} TÜFE verisi yayımlanmış. Hesap güncel resmi TÜİK oranıyla yapıldı."
    elif current < target:
        durum=f"Son resmi TÜFE verisi {period} dönemine ait. {MONTH_NAMES[yenileme_ayi]} {ry} yenilemesi için gerekli veri henüz yayımlanmadı. Şimdilik son resmi oranla hesaplandı."
    else:
        durum=f"Hesap, TÜİK'in yayımladığı son resmi {period} verisiyle yapıldı."
    return JSONResponse({"oran":f"{rate:.2f}".replace(".",","),"mevcut_kira":money_tr(mevcut_kira),"artis":money_tr(artis),"yeni_kira":money_tr(yeni),"donem":period,"durum":durum,"source":source,"data_mode":tufe.get("data_mode","cache")})


@app.get("/api/otv")
async def api_otv(): return JSONResponse(get_otv_data())

@app.post("/api/otv/yenile")
async def api_otv_yenile(request: Request):
    await enforce_rate_limit(request, "otv-refresh", REFRESH_RATE_LIMIT, REFRESH_RATE_LIMIT_WINDOW)
    async with _REFRESH_LOCK:
        data = await asyncio.to_thread(refresh_otv_data, True)
    return JSONResponse(data)

# Haberleri çalışma anında GitHub'daki güncel dosyadan oku; ağ hatasında yerel yedeği kullan.
_NEWS_SOURCE_URL = "https://raw.githubusercontent.com/rsever-source/mobilrs/cloud-run-migration/news.json"
_NEWS_CACHE = {"expires_at": 0.0, "data": None}


def _read_local_news_data():
    try:
        with open("news.json", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except Exception:
        pass
    return {"updated_at": None, "items": []}


def _load_news_data():
    now = time.monotonic()
    cached = _NEWS_CACHE.get("data")
    if cached is not None and now < _NEWS_CACHE.get("expires_at", 0.0):
        return cached
    try:
        url = _NEWS_SOURCE_URL + "?v=" + str(int(time.time() // 60))
        response = requests.get(url, timeout=(3, 5), headers={"Cache-Control": "no-cache"})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError("Invalid news JSON")
        _NEWS_CACHE.update({"expires_at": now + 60.0, "data": data})
        return data
    except Exception:
        data = _read_local_news_data()
        _NEWS_CACHE.update({"expires_at": now + 15.0, "data": data})
        return data


@app.get("/api/news")
async def api_news():
    data = await asyncio.to_thread(_load_news_data)
    items = []
    for item in data.get("items", [])[:12]:
        url = str(item.get("url", "")).strip()
        if not url.startswith(("https://", "http://")):
            continue
        items.append({
            "id": str(item.get("id", "")),
            "title": str(item.get("title", ""))[:180],
            "summary": str(item.get("summary", ""))[:900],
            "detail_summary": str(item.get("detail_summary", ""))[:1400],
            "category": str(item.get("category", "Gündem"))[:50],
            "source": str(item.get("source", ""))[:100],
            "url": url,
            "published_at": item.get("published_at"),
        })
    return JSONResponse({"updated_at": data.get("updated_at"), "items": items})


@app.get("/arac1", response_class=HTMLResponse)
@app.get("/arac1/", response_class=HTMLResponse)
async def ek2_arac1_sayfa(request: Request):
    return HTMLResponse(_ek2_sayfa("arac1", "__ARAC2_ADRESI__", "/arac2", request.state.csp_nonce))


@app.get("/arac2", response_class=HTMLResponse)
@app.get("/arac2/", response_class=HTMLResponse)
async def ek2_arac2_sayfa(request: Request):
    return HTMLResponse(_ek2_sayfa("arac2", "__ARAC1_ADRESI__", "/arac1", request.state.csp_nonce))


@app.get("/arac3", response_class=HTMLResponse)
@app.get("/arac3/", response_class=HTMLResponse)
async def ek2_arac3_sayfa(request: Request):
    return HTMLResponse(_ek2_sayfa("arac3", "__ARAC1_ADRESI__", "/arac1", request.state.csp_nonce))


@app.get("/api/arac3/eslestirme")
async def arac3_eslestirme():
    dosya = EK2_ROOT / "arac3" / "arac3_182_ek1_eslestirme.json"
    if not dosya.is_file():
        raise HTTPException(503, "Araç 3 Ek-1 eşleştirme verisi henüz kullanıma hazır değil.")
    return FileResponse(dosya, media_type="application/json; charset=utf-8")


@app.get("/api/bolumler")
async def ek2_bolumler():
    return JSONResponse(ek2_arac1.gezinme_yuku(None))


@app.get("/api/gezinme")
async def ek2_gezinme(bolum: str = Query(...)):
    sonuc = ek2_arac1.gezinme_yuku(bolum)
    if not sonuc.get("ok"):
        raise HTTPException(404, sonuc.get("mesaj", "Bölüm bulunamadı."))
    return JSONResponse(sonuc)


@app.get("/api/ara")
async def ek2_ara(metin: str = Query(""), bolum: str | None = Query(default=None)):
    sonuc = ek2_arac1.arama_yuku(metin, bolum)
    if not sonuc.get("ok"):
        raise HTTPException(404, sonuc.get("mesaj", "Bölüm bulunamadı."))
    return JSONResponse(sonuc)


@app.get("/api/ozel-hesaplamalar")
async def ek2_ozel_hesaplamalar():
    return JSONResponse({"ok": True, **ek2_arac1.ozel_hesaplamalar()})


@app.get("/api/kurallar")
async def ek2_kurallar():
    return JSONResponse({"ok": True, **ek2_arac1.kurallar()})


@app.get("/api/kayit/{kimlik}")
async def ek2_kayit(kimlik: str):
    if kimlik.startswith(("KV-", "KH-", "UG-", "SS-", "EM-", "GH-", "ON-", "SN-")):
        for bolum in ek2_arac1.ek_katalog().get("bolumler", []):
            for satir in bolum.get("kayitlar", []):
                if satir.get("id") != kimlik:
                    continue
                return JSONResponse(ek2_arac1.ek_kayit_sonuc_yuku(bolum, satir))
        raise HTTPException(404, "Ek katalog kaydı bulunamadı.")
    kayit = ek2_arac1.katalog().kayit(kimlik)
    if kayit is None:
        raise HTTPException(404, "Kayıt bulunamadı.")
    return JSONResponse(ek2_arac1.sonuc_yuku(kayit))


@app.get("/api/belirsiz/{kimlik}")
async def ek2_belirsiz(kimlik: str):
    kayit = ek2_arac1.katalog().belirsiz_kayit(kimlik)
    if kayit is None:
        raise HTTPException(404, "Kayıt bulunamadı.")
    return JSONResponse(ek2_arac1.belirsiz_yuku(kayit))


@app.post("/api/hesapla")
async def ek2_hesapla(request: Request):
    try:
        uzunluk = int(request.headers.get("content-length") or "0")
    except ValueError:
        uzunluk = -1
    if uzunluk <= 0 or uzunluk > 64 * 1024:
        raise HTTPException(400, "İstek okunamadı.")
    try:
        girdi = json.loads((await request.body()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(400, "İstek okunamadı.")
    sonuc = ek2_arac2.balthazard(girdi)
    if sonuc.get("ok"):
        sonuc["gosterim"] = ek2_arac2.gosterim_ekle(sonuc)
    return JSONResponse(sonuc)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if request.headers.get("host", "").split(":")[0].lower() == "chat.engelli.me":
        return HTMLResponse(CHAT_HTML.replace("<style>", f'<style nonce="{request.state.csp_nonce}">'))
    initial = load_otv_cache() or {}
    initial_json = __import__("json").dumps(initial, ensure_ascii=False).replace("</", "<\\/")
    initial_news = await asyncio.to_thread(_load_news_data)
    initial_news_json = json.dumps(initial_news, ensure_ascii=False).replace("</", "<\\/")
    html = (
        HOME_HTML
        .replace("/*INITIAL_OTV_DATA*/{}", initial_json)
        .replace("/*INITIAL_NEWS_DATA*/{}", initial_news_json)
        .replace("<script>", f'<script nonce="{request.state.csp_nonce}">')
        .replace("<style>", f'<style nonce="{request.state.csp_nonce}">')
    )
    return HTMLResponse(html)


def _icon_route(name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    async def handler():
        if not os.path.isfile(path):
            raise HTTPException(404, "Dosya bulunamadı.")
        return FileResponse(path, media_type="image/png")
    return handler

for _n in ("logo.png", "favicon.png", "apple-touch-icon.png"):
    app.add_api_route("/" + _n, _icon_route(_n), methods=["GET", "HEAD"], include_in_schema=False)
for _alias, _n in (("favicon.ico", "favicon.png"), ("apple-touch-icon-precomposed.png", "apple-touch-icon.png")):
    app.add_api_route("/" + _alias, _icon_route(_n), methods=["GET", "HEAD"], include_in_schema=False)

BRAND_LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand-logos")
BRAND_LOGO_FILES = {"fiat.svg", "renault.svg", "togg.svg", "toyota.svg", "hyundai.svg"}


@app.get("/brand-logos/{filename}", include_in_schema=False)
async def brand_logo_asset(filename: str):
    path = os.path.join(BRAND_LOGO_DIR, filename)
    if filename not in BRAND_LOGO_FILES or not os.path.isfile(path):
        raise HTTPException(404, "Dosya bulunamadı.")
    return FileResponse(path, media_type="image/svg+xml")


@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    return HTMLResponse("User-agent: *\nAllow: /\nSitemap: https://engelli.me/sitemap.xml\n", media_type="text/plain")


@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml():
    urls = ("https://engelli.me/", "https://engelli.me/arac1", "https://engelli.me/arac2", "https://engelli.me/arac3")
    entries = "".join("<url><loc>" + url + "</loc></url>" for url in urls)
    xml = '<?xml version="1.0" encoding="UTF-8"?>' + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + entries + "</urlset>"
    return HTMLResponse(xml, media_type="application/xml")


@app.get("/.well-known/security.txt", response_class=Response)
async def security_txt():
    return Response("Contact: https://engelli.me/\nExpires: 2027-10-01T00:00:00.000Z\nPreferred-Languages: tr, en\nCanonical: https://engelli.me/.well-known/security.txt\n", media_type="text/plain")


@app.get("/kvkk", response_class=HTMLResponse)
async def kvkk_page(request: Request):
    return HTMLResponse(KVKK_HTML.replace("<style>", f'<style nonce="{request.state.csp_nonce}">'))




@app.post("/excel-islem")
async def excel_motor(request: Request, komut:str=Form(...), file1:UploadFile=File(...), file2:UploadFile=File(...)):
    await enforce_rate_limit(request, "upload", UPLOAD_RATE_LIMIT, RATE_LIMIT_WINDOW)
    guard_request_body(request)
    out=None
    try:
        if not check_extension(file1.filename,(".xlsx",".xls")) or not check_extension(file2.filename,(".xlsx",".xls")): raise HTTPException(400,"Geçerli Excel dosyaları seç.")
        d1=await read_upload_limited(file1); d2=await read_upload_limited(file2); validate_file_signature(d1,file1.filename,file1.content_type); validate_file_signature(d2,file2.filename,file2.content_type)
        out=await run_heavy_job(build_excel_result, d1, d2, komut, timeout=FILE_PROCESS_TIMEOUT)
        return FileResponse(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="excel_sonuc.xlsx",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,"Excel işlemi sırasında beklenmeyen bir hata oluştu.")


@app.post("/pdf-excel-islem")
async def pdf_excel_motor(request: Request, pdf_file:UploadFile=File(...)):
    await enforce_rate_limit(request, "upload", UPLOAD_RATE_LIMIT, RATE_LIMIT_WINDOW)
    guard_request_body(request)
    out=None
    try:
        if not check_extension(pdf_file.filename,(".pdf",)): raise HTTPException(400,"Geçerli bir PDF dosyası seç.")
        pdf_data=await read_upload_limited(pdf_file); validate_file_signature(pdf_data,pdf_file.filename,pdf_file.content_type)
        out=await run_heavy_job(build_pdf_result, pdf_data, timeout=FILE_PROCESS_TIMEOUT)
        return FileResponse(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="pdf_to_excel_sonuc.xlsx",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,"PDF → Excel işlemi sırasında beklenmeyen bir hata oluştu.")


KVKK_HTML = r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KVKK Aydınlatma Metni | Engelli.me</title><style>body{margin:0;background:#f4f6f9;color:#182234;font-family:Inter,Aptos,"Segoe UI",system-ui,-apple-system,sans-serif}.card{max-width:820px;margin:32px auto;padding:28px;background:#fff;border:1px solid #e4e8ef;border-radius:18px;box-shadow:0 10px 30px rgba(20,32,55,.06)}h1{font-size:25px;margin:0 0 18px}h2{font-size:17px;margin:22px 0 8px}p,li{font-size:14px;line-height:1.65}.muted{color:#697386;font-size:12px}@media(max-width:640px){body{background:#fff}.card{margin:0;padding:20px;border:0;border-radius:0;box-shadow:none}h1{font-size:22px}}</style></head><body><main class="card"><h1>KVKK Aydınlatma Metni</h1><p class="muted">Son güncelleme: 28 Eylül 2026</p><h2>1. Veri Sorumlusu</h2><p>Bu hizmet kapsamında işlenen kişisel veriler bakımından veri sorumlusu, Engelli.me hizmetinin işletmecisidir.</p><h2>2. Kapsam</h2><p>Bu Aydınlatma Metni, Engelli.me üzerinde sunulan Excel işlemleri, PDF → Excel hizmeti ve kullanıcı sohbetine ilişkin kişisel veri işleme faaliyetleri hakkında bilgilendirme amacıyla hazırlanmıştır.</p><h2>3. Excel ve PDF → Excel Hizmetleri</h2><p>Excel ve PDF → Excel araçlarına yüklediğiniz dosyalar, yalnızca talep ettiğiniz dosya işlemini gerçekleştirmek ve sonucu size sunmak amacıyla teknik olarak işlenir. Dosya içeriğinde kişisel veri bulunması halinde bu veriler de işlem sırasında teknik olarak işlenebilir.</p><h2>4. Dosyaların Saklanması</h2><p>Yüklediğiniz Excel ve PDF dosyaları kalıcı olarak saklanmak üzere tasarlanmamıştır. Dosya içeriği işlem sırasında işlenir. Oluşturulan sonuç dosyası geçici olarak oluşturulur ve işlem sonrasında silinir.</p><h2>5. Kullanıcı Sohbeti</h2><p>Engelli.me kullanıcı sohbeti, Klaklak altyapısı kullanılarak sunulmaktadır. Sohbet alanında kullanıcıların seçtiği takma ad (nickname), IP adresi ve mesaj içeriği gibi veriler Klaklak'ın hizmetini sunması ve kötüye kullanımın önlenmesi amacıyla işlenebilir. Engelli.me uygulaması sohbet mesajlarını kendi sunucularında ayrıca arşivlemek veya kalıcı olarak saklamak üzere tasarlanmamıştır.</p><p>Klaklak'ın geçici sohbet yapısında aktif odada son 50 mesaja kadar içerik gösterilebilir; oda, kimsenin bulunmadığı sürenin ardından temizlenir ve sohbet geçmişi arşivlenmez. Kötüye kullanımın önlenmesine yönelik zaman, IP adresi ve takma ad bilgilerini içeren kayıtlar Klaklak'ın kendi hizmet koşulları ve gizlilik uygulamaları kapsamında daha farklı sürelerde tutulabilir.</p><p>Sohbet hizmeti uçtan uca şifreli değildir. Bu nedenle sohbet alanına telefon numarası, adres, kimlik bilgisi, sağlık bilgisi veya başka kişisel ya da özel nitelikli kişisel verileri yazmamanız önemle tavsiye edilir.</p><h2>6. Kişisel Verilerin İşlenme Amaçları ve Hukuki Sebepler</h2><p>Kişisel veriler; sunulan hizmetlerin çalıştırılması, kullanıcı tarafından talep edilen işlemlerin gerçekleştirilmesi, teknik güvenliğin sağlanması, kötüye kullanımın ve güvenlik olaylarının önlenmesi ve ilgili mevzuattan doğan yükümlülüklerin yerine getirilmesi amaçlarıyla, 6698 sayılı Kişisel Verilerin Korunması Kanunu'nun 5 ve 6. maddelerinde düzenlenen ilgili veri işleme şartları çerçevesinde işlenebilir.</p><h2>7. Veri Aktarımı ve Üçüncü Taraf Hizmet Sağlayıcılar</h2><p>Hizmetlerin sunulabilmesi için kişisel veriler, kullanılan teknik altyapı ve hizmet sağlayıcılarına, yalnızca ilgili hizmetin gerektirdiği ölçüde aktarılabilir veya bu sağlayıcılar tarafından işlenebilir. Kullanıcı sohbetinde Klaklak üçüncü taraf hizmet sağlayıcısı olarak görev yapmaktadır. Klaklak tarafından işlenen veriler ayrıca Klaklak'ın kendi gizlilik ve hizmet koşullarına tabidir.</p><h2>8. Kullanıcıların Dikkatine</h2><p>Hizmetleri kullanırken mümkün olduğunca kişisel veri içermeyen dosyalar yüklemeniz ve sohbet alanında kişisel veri paylaşmamanız önerilir. Özellikle özel nitelikli kişisel verileri içeren belgeleri yalnızca gerekli olduğunda yükleyiniz.</p><h2>9. Güvenlik</h2><p>Kişisel verilerin hukuka aykırı işlenmesini veya erişilmesini önlemek ve güvenliğini sağlamak amacıyla hizmetin teknik yapısına uygun teknik ve idari tedbirler uygulanır.</p><h2>10. Saklama Süreleri</h2><p>Kişisel veriler, işlendikleri amaç için gerekli olan süre boyunca ve ilgili mevzuatta öngörülen saklama süreleri kadar muhafaza edilir. Dosya işleme sonuçları geçici olarak oluşturulur ve işlem sonrasında silinir. Sohbet içerikleri ve Klaklak tarafından tutulan teknik/kötüye kullanım kayıtları bakımından Klaklak'ın kendi saklama politikaları geçerlidir.</p><h2>11. İlgili Kişinin Hakları</h2><p>KVKK'nın 11. maddesi kapsamında kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse buna ilişkin bilgi talep etme, işlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme, yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme, eksik veya yanlış işlenmişse düzeltilmesini isteme, kanunda öngörülen şartlar çerçevesinde silinmesini veya yok edilmesini isteme ve diğer kanuni haklarınızı kullanma hakkınız bulunmaktadır.</p><h2>12. İletişim ve Başvurular</h2><p>KVKK kapsamındaki taleplerinizi hizmet işletmecisine iletebilirsiniz. Başvurular ilgili mevzuatta öngörülen usul ve esaslara göre değerlendirilir. Veri sorumlusu iletişim bilgilerinin güncellenmesi halinde bu metin de güncellenecektir.</p><p class="muted">Bu metin, Engelli.me üzerinde sunulan hizmetlerin kapsamındaki kişisel veri işleme faaliyetleri hakkında bilgilendirme amacı taşır. Klaklak'ın kendi hizmeti kapsamında gerçekleştirdiği veri işleme faaliyetleri bakımından Klaklak'ın güncel gizlilik politikası ayrıca dikkate alınmalıdır.</p></main></body></html>'''

HOME_HTML = r'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Engelli.me | Engelli Haberleri, Yardımcılar ve ÖTV Muafiyetli Araçlar</title>
<meta name="description" content="Güncel engelli haberleri, ÖTV muafiyetli araç fiyatları, EK-2 hastalık oranı bulma, Balthazard engellilik oranı hesaplama, kira hesaplama, Excel ve PDF → Excel araçları.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="https://engelli.me/">
<meta property="og:title" content="Engelli.me | Haberler, Yardımcılar ve ÖTV Muafiyetli Araçlar">
<meta property="og:description" content="Güncel engelli haberleri, ÖTV muafiyetli araç fiyatları ve pratik hesaplama araçları.">
<meta property="og:url" content="https://engelli.me/">
<meta property="og:type" content="website">
<meta name="theme-color" content="#16211f">
<link rel="icon" type="image/png" href="/favicon.png?v=2" sizes="64x64">
<link rel="shortcut icon" type="image/png" href="/favicon.png?v=2">
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=2">
<style>
/* ==========================================================================
   Engelli.me — Haber Portalı Tasarım Taslağı v2
   Fotoğrafsız, tipografi odaklı haber akışı + ÖTV Muafiyetli Araçlar +
   Engelli.me'nin mevcut erişilebilirlik kontrolleri.
   Referans: Colorlib Sparkling (sade düzen, içerik + yan sütun)
   ========================================================================== */

:root {
  --paper: #fbfaf7;
  --paper-deep: #f3f1ea;
  --surface: #ffffff;
  --ink: #16211f;
  --ink-soft: #2b3733;
  --muted: #5e6b66;
  --line: #e2ded5;
  --line-strong: #cfc9bd;
  --accent: #0f766e;
  --accent-ink: #0b5d56;
  --accent-soft: #e7f2ef;
  --alert: #b5432a;
  --demo-bg: #fdf5e7;
  --demo-ink: #7a4a12;
  --demo-line: #efe0c8;
  --logo-bg: #ffffff;
  --breaking-bg: #16211f;
  --breaking-ink: #f4f2ec;
  --breaking-muted: #a8b8b2;
  --btn-primary-bg: #16211f;
  --btn-primary-ink: #fbfaf7;

  --font-serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  --font-sans: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;

  --wrap: 1180px;
  --gap: 48px;
  --font-scale: 1;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  font-size: calc(16px * var(--font-scale));
  -webkit-text-size-adjust: 100%;
  scroll-behavior: smooth;
  scroll-padding-top: 6rem;
}

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 1rem;
  line-height: 1.5;
}

img {
  max-width: 100%;
  height: auto;
}

[hidden] {
  display: none !important;
}

a {
  color: inherit;
  text-decoration: none;
}

a:hover {
  color: var(--accent-ink);
}

button,
input,
select,
textarea {
  font-family: inherit;
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  border: 0;
  white-space: nowrap;
}

.wrap {
  width: min(var(--wrap), 100% - 48px);
  margin-inline: auto;
}

.skip-link {
  position: absolute;
  left: 16px;
  top: -60px;
  z-index: 60;
  padding: 10px 16px;
  background: var(--ink);
  color: var(--paper);
  font-size: 0.8125rem;
  font-weight: 600;
}

.skip-link:focus {
  top: 12px;
  color: var(--paper);
}

/* Demo bilgi şeridi ------------------------------------------------------- */

.demo-bar {
  margin: 0;
  padding: 7px 20px;
  background: var(--demo-bg);
  border-bottom: 1px solid var(--demo-line);
  color: var(--demo-ink);
  font-size: 0.75rem;
  line-height: 1.4;
  text-align: center;
}

/* Üst bölüm --------------------------------------------------------------- */

.site-header {
  position: sticky;
  top: 0;
  z-index: 30;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}

.header-inner {
  position: relative;
  display: flex;
  align-items: center;
  gap: 1.1rem;
  min-height: 4.75rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 0 0 auto;
}

.brand-logo {
  display: block;
  width: 46px;
  height: 46px;
}

.brand-name {
  font-family: var(--font-serif);
  font-size: 1.4375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
}

.brand-dot {
  color: var(--accent);
}

.site-nav {
  margin-left: auto;
  min-width: 0;
}

.site-nav ul {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.15rem 1.05rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.site-nav a {
  display: inline-block;
  padding: 6px 0;
  border-bottom: 2px solid transparent;
  color: var(--ink-soft);
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.site-nav a:hover {
  border-bottom-color: var(--line-strong);
  color: var(--ink);
}

.site-nav a.is-active {
  border-bottom-color: var(--accent);
  color: var(--ink);
}

.nav-toggle {
  display: none;
  align-items: center;
  gap: 0.5rem;
  flex: 0 0 auto;
  margin-left: 0;
  padding: 9px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: transparent;
  color: var(--ink);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.nav-toggle-bars,
.nav-toggle-bars::before,
.nav-toggle-bars::after {
  display: block;
  width: 15px;
  height: 2px;
  background: currentColor;
}

.nav-toggle-bars {
  position: relative;
}

.nav-toggle-bars::before,
.nav-toggle-bars::after {
  content: "";
  position: absolute;
  left: 0;
}

.nav-toggle-bars::before {
  top: -5px;
}

.nav-toggle-bars::after {
  top: 5px;
}

/* Erişilebilirlik menüsü -------------------------------------------------- */

.a11y {
  flex: 0 0 auto;
}

.a11y-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: transparent;
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
}

.a11y-toggle:hover {
  background: var(--accent-soft);
  color: var(--ink);
}

.a11y-icon {
  display: block;
  flex: 0 0 auto;
}

.a11y-panel {
  display: none;
  position: absolute;
  top: calc(100% + 0.6rem);
  right: 0;
  z-index: 40;
  width: min(20rem, calc(100vw - 2rem));
  max-height: calc(100vh - 8rem);
  overflow-y: auto;
  padding: 1rem;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-top: 3px solid var(--accent);
  border-radius: 4px;
}

.a11y-panel.open {
  display: block;
}

.a11y-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.65rem;
}

.a11y-title {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.a11y-reset {
  padding: 0;
  border: 0;
  border-bottom: 1px solid currentColor;
  background: transparent;
  color: var(--accent-ink);
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}

.a11y-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.4rem;
}

.a11y-options button {
  min-height: 2.6rem;
  padding: 0.4rem 0.3rem;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  background: var(--surface);
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}

.a11y-options button:hover {
  border-color: var(--accent);
}

.a11y-options button[aria-pressed="true"] {
  border-color: var(--accent);
  background: var(--accent);
  color: #ffffff;
}

.a11y-options .a11y-wide {
  grid-column: 1 / -1;
  min-height: 2.4rem;
  font-size: 0.73rem;
}

.a11y-note {
  margin: 0.6rem 0 0;
  color: var(--muted);
  font-size: 0.68rem;
  line-height: 1.5;
}

/* Son dakika -------------------------------------------------------------- */

.breaking {
  background: var(--breaking-bg);
  color: var(--breaking-ink);
}

.breaking-inner {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-height: 46px;
  padding-block: 8px;
}

.breaking-label {
  flex: 0 0 auto;
  padding: 4px 9px;
  border-radius: 3px;
  background: var(--alert);
  color: #ffffff;
  font-size: 0.656rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.breaking-text {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  font-size: 0.875rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breaking-text a {
  color: var(--breaking-ink);
}

.breaking-text a:hover {
  color: #ffffff;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.breaking-time {
  flex: 0 0 auto;
  color: var(--breaking-muted);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}

.breaking-all {
  flex: 0 0 auto;
  border-bottom: 1px solid var(--breaking-muted);
  color: var(--breaking-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.breaking-all:hover {
  border-bottom-color: var(--breaking-ink);
  color: var(--breaking-ink);
}

/* Manşet ------------------------------------------------------------------ */

main {
  padding-bottom: 8px;
}

.lead {
  padding: 30px 0 40px;
  border-top: 3px solid var(--ink);
  border-bottom: 1px solid var(--line);
  margin-top: 28px;
}

.kicker {
  margin: 0 0 14px;
  color: var(--accent-ink);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.lead h1 {
  max-width: 24ch;
  margin: 0 0 18px;
  font-family: var(--font-serif);
  font-size: clamp(2rem, 4.4vw, 3.5rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.1;
}

.lead h1 a:hover {
  color: var(--accent-ink);
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 6px;
}

.lead-summary {
  max-width: 62ch;
  margin: 0 0 16px;
  color: var(--ink-soft);
  font-family: var(--font-serif);
  font-size: 1.12rem;
  line-height: 1.55;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 8px;
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
}

.meta-sep {
  color: var(--line-strong);
}

.demo-flag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--demo-bg);
  color: var(--demo-ink);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* İçerik ve yan sütun ----------------------------------------------------- */

.layout {
  display: contents;
}

/* Ana sayfa ızgarası: araçlar masaüstünde sağ sütunda, mobilde sayfa sonunda. */

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 8fr) minmax(0, 4fr);
  grid-template-areas:
    "lead lead"
    "news sidebar"
    "news tools"
    "otv otv"
    "chat chat";
  column-gap: var(--gap);
  row-gap: 0;
  align-items: start;
}

.lead { grid-area: lead; }
.news { grid-area: news; min-width: 0; padding-top: 40px; }
.sidebar { grid-area: sidebar; min-width: 0; padding-top: 40px; }
.tools-section { grid-area: tools; min-width: 0; }
.otv { grid-area: otv; }
.chat-invite { grid-area: chat; }

.section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px 20px;
  padding-top: 14px;
  border-top: 2px solid var(--ink);
}

.section-head h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 1.45rem;
  font-weight: 700;
  letter-spacing: -0.015em;
}

.section-link {
  flex: 0 0 auto;
  color: var(--accent-ink);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.section-link:hover {
  text-decoration: underline;
  text-underline-offset: 4px;
}

.feed-note {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.5;
}

/* Son haberler ------------------------------------------------------------ */

.news-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.news-item {
  padding: 24px 0;
  border-bottom: 1px solid var(--line);
}

.news-item:first-child {
  border-top: 1px solid var(--line);
  margin-top: 20px;
}

.news-item h3 {
  margin: 0 0 8px;
  font-family: var(--font-serif);
  font-size: clamp(1.18rem, 1.9vw, 1.4rem);
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.24;
}

.news-item h3 a:hover {
  color: var(--accent-ink);
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 4px;
}

.summary {
  max-width: 62ch;
  margin: 0 0 10px;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.62;
}

.news-item .meta {
  font-size: 0.75rem;
}

/* Yan sütun --------------------------------------------------------------- */

.sidebar {
  display: grid;
  gap: 36px;
  position: static;
}

.sidebar h2 {
  margin: 0 0 4px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--ink);
  font-family: var(--font-sans);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.most-read ol {
  margin: 0;
  padding: 0;
  list-style: none;
}

.most-read li {
  border-bottom: 1px solid var(--line);
}

.most-read a {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  align-items: baseline;
  padding: 14px 0;
}

.most-read-num {
  color: var(--accent);
  font-family: var(--font-serif);
  font-size: 1.0625rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.most-read-text {
  font-family: var(--font-serif);
  font-size: 1.02rem;
  font-weight: 700;
  letter-spacing: -0.005em;
  line-height: 1.32;
}

.most-read a:hover .most-read-text {
  color: var(--accent-ink);
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
}

.sources ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.sources li {
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
  color: var(--ink-soft);
  font-size: 0.84rem;
}

.sources .note {
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.5;
}

/* ÖTV Muafiyetli Araçlar -------------------------------------------------- */

.otv {
  margin-top: 4.5rem;
  scroll-margin-top: 6.5rem;
}

.otv-head {
  align-items: flex-start;
  padding-top: 1.1rem;
  border-top: 3px solid var(--ink);
}

.otv-head .kicker {
  margin-bottom: 0.5rem;
}

.otv-head h2 {
  font-size: clamp(1.7rem, 2.6vw, 2.2rem);
  letter-spacing: -0.02em;
}

.otv-update {
  flex: 0 0 auto;
  margin: 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.5;
  text-align: right;
  white-space: nowrap;
}

.otv-update strong {
  color: var(--ink);
  font-weight: 700;
}

.otv-intro {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  gap: 2.5rem;
  padding: 1.1rem 0 1.4rem;
  border-bottom: 1px solid var(--line);
}

.otv-intro p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 0.92rem;
  line-height: 1.65;
}

.otv-intro-note {
  color: var(--muted) !important;
  font-size: 0.78rem !important;
  border-left: 2px solid var(--accent);
  padding-left: 0.9rem;
}

.otv-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 1.1rem 0;
  border-bottom: 1px solid var(--line);
}

.otv-summary p {
  margin: 0;
  padding: 0 1.1rem;
  border-left: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.4;
}

.otv-summary p:first-child {
  padding-left: 0;
  border-left: 0;
}

.otv-summary strong {
  display: block;
  margin-bottom: 0.15rem;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 1.24rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}

.brand-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem 0.9rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--line);
}

.filter-label {
  margin: 0;
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.filter-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.brand-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2rem;
  padding: 0.3rem 0.62rem;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  background: transparent;
  color: var(--ink-soft);
  font-size: 0.74rem;
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
}

.brand-chip:hover {
  border-color: var(--accent);
  color: var(--ink);
}

.brand-chip[aria-pressed="true"] {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
}

.chip-count {
  font-size: 0.66rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.72;
}

.brand-list {
  margin-top: 0.4rem;
}

.brand-group {
  display: grid;
  grid-template-columns: 10.5rem minmax(0, 1fr);
  gap: 2rem;
  padding: 1.5rem 0 1.7rem;
  border-bottom: 1px solid var(--line);
}

.brand-head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  min-width: 0;
}

.brand-mark {
  flex: 0 0 2.6rem;
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  padding: 0.35rem;
  background: var(--logo-bg);
  border: 1px solid var(--line);
  border-radius: 3px;
}

.brand-mark img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.brand-title {
  min-width: 0;
}

.brand-title h3 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: -0.015em;
  line-height: 1.1;
}

.brand-title p {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.7rem;
  line-height: 1.5;
}

.vehicle-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 2.5rem;
  margin: 0;
  padding: 0 0 0 2rem;
  border-left: 1px solid var(--line);
  list-style: none;
}

.vehicle-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: start;
  padding: 0.8rem 0;
  border-top: 1px solid var(--line);
}

.vehicle-row:nth-child(-n + 2) {
  border-top: 0;
}

.vehicle-main {
  min-width: 0;
}

.vehicle-name {
  display: block;
  font-family: var(--font-serif);
  font-size: 1.02rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.25;
}

.vehicle-trim {
  display: block;
  margin-top: 0.1rem;
  color: var(--muted);
  font-size: 0.76rem;
  line-height: 1.4;
}

.vehicle-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.55rem;
  margin-top: 0.35rem;
  color: var(--muted);
  font-size: 0.7rem;
  line-height: 1.4;
}

.vehicle-ok {
  display: inline-block;
  padding: 0 0.35rem;
  border: 1px solid var(--accent-ink);
  border-radius: 2px;
  color: var(--accent-ink);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  line-height: 1.5;
  text-transform: uppercase;
}

.vehicle-price {
  text-align: right;
  white-space: nowrap;
}

.price-label {
  display: block;
  color: var(--muted);
  font-size: 0.63rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.price-value {
  display: block;
  color: var(--ink);
  font-size: 1.02rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}

.price-list {
  display: block;
  margin-top: 0.1rem;
  color: var(--muted);
  font-size: 0.7rem;
  font-variant-numeric: tabular-nums;
}

.vehicle-source {
  grid-column: 1 / -1;
  margin: 0.15rem 0 0;
  color: var(--muted);
  font-size: 0.68rem;
  line-height: 1.5;
}

.vehicle-source a {
  color: var(--accent-ink);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.otv-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  margin-top: 1.5rem;
}

.otv-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.7rem 1rem;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  background: transparent;
  color: var(--ink);
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1.3;
}

.otv-btn:hover {
  border-color: var(--ink);
  background: var(--accent-soft);
  color: var(--ink);
}

.otv-btn-primary {
  border-color: var(--btn-primary-bg);
  background: var(--btn-primary-bg);
  color: var(--btn-primary-ink);
}

.otv-btn-primary:hover {
  border-color: var(--accent-ink);
  background: var(--accent-ink);
  color: #ffffff;
}

.otv-calc {
  max-width: 70ch;
  margin-top: 1.6rem;
  padding-top: 1.2rem;
  border-top: 1px solid var(--line);
  scroll-margin-top: 6.5rem;
}

.otv-calc:target {
  background: var(--accent-soft);
}

.otv-calc h3 {
  margin: 0 0 0.4rem;
  font-family: var(--font-serif);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.otv-calc p {
  margin: 0 0 0.5rem;
  color: var(--ink-soft);
  font-size: 0.85rem;
  line-height: 1.65;
}

.otv-calc-link {
  margin-top: 0.4rem !important;
}

.otv-calc-link a {
  color: var(--accent-ink);
  font-size: 0.8rem;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.otv-note {
  margin: 1.4rem 0 0;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.6;
}

/* Alt bilgi — mevcut içerik yapısından esinlenen, yeni haber portalına uyarlanmış footer */
.site-footer {
  margin-top: 68px;
  padding: 38px 24px 18px;
  background: var(--paper-deep);
  border-top: 1px solid var(--line-strong);
  color: var(--ink-soft);
  font-size: 0.8rem;
  line-height: 1.65;
}

.footer-inner {
  width: min(var(--wrap), 100%);
  margin-inline: auto;
}

.footer-top {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(180px, 0.85fr) minmax(190px, 0.9fr);
  gap: clamp(28px, 5vw, 72px);
  padding-bottom: 30px;
}

.footer-brand-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1;
}

.footer-brand-link img {
  display: block;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #fff;
}

.footer-brand-dot {
  color: var(--accent);
}

.footer-brand > p {
  max-width: 38ch;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.7;
}

.footer-brand > .footer-note {
  margin-top: 7px;
  font-size: 0.72rem;
}

.footer-nav,
.footer-contact {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 9px;
}

.footer-nav h2,
.footer-contact h2 {
  margin: 4px 0 6px;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.footer-nav a,
.footer-contact a {
  color: var(--ink-soft);
  font-size: 0.8rem;
  text-decoration: none;
  text-underline-offset: 3px;
}

.footer-nav a:hover,
.footer-contact a:hover {
  color: var(--accent-ink);
  text-decoration: underline;
}

.footer-contact .footer-email {
  color: var(--accent-ink);
  font-weight: 700;
}

.footer-contact .footer-legal {
  margin-top: 2px;
  color: var(--muted);
  font-size: 0.74rem;
}

.footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px 24px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.69rem;
}

.footer-bottom p { margin: 0; }

body.dark-mode .site-footer {
  background: var(--paper-deep);
  border-top-color: var(--line);
  color: var(--ink-soft);
}
body.dark-mode .footer-brand-link,
body.dark-mode .footer-nav h2,
body.dark-mode .footer-contact h2 { color: var(--ink); }
body.dark-mode .footer-nav a,
body.dark-mode .footer-contact a { color: var(--ink-soft); }
body.dark-mode .footer-contact .footer-email { color: var(--accent); }

/* Koyu mod --------------------------------------------------------------- */

body.dark-mode {
  --paper: #101715;
  --paper-deep: #0b1210;
  --surface: #16201d;
  --ink: #eef3f0;
  --ink-soft: #d7e0dc;
  --muted: #a7b5af;
  --line: #2c3a35;
  --line-strong: #42544d;
  --accent: #4fd1c5;
  --accent-ink: #6ee7db;
  --accent-soft: #13312d;
  --alert: #d4674c;
  --demo-bg: #2a2418;
  --demo-ink: #f0d9a8;
  --demo-line: #463b26;
  --logo-bg: #f4f7f5;
  --breaking-bg: #08100d;
  --breaking-ink: #eef3f0;
  --breaking-muted: #a7b5af;
  --btn-primary-bg: #4fd1c5;
  --btn-primary-ink: #07110f;
  background: var(--paper);
  color: var(--ink);
}

body.dark-mode .site-header,
body.dark-mode .site-nav,
body.dark-mode .a11y-panel {
  background: var(--paper);
}

body.dark-mode .a11y-panel {
  background: var(--surface);
}

body.dark-mode .vehicle-price .price-value {
  color: var(--ink);
}

/* Yüksek kontrast --------------------------------------------------------- */

body.high-contrast {
  --paper: #ffffff;
  --paper-deep: #ffffff;
  --surface: #ffffff;
  --ink: #000000;
  --ink-soft: #000000;
  --muted: #000000;
  --line: #000000;
  --line-strong: #000000;
  --accent: #0000ee;
  --accent-ink: #0000ee;
  --accent-soft: #ffffff;
  --alert: #000000;
  --demo-bg: #ffffff;
  --demo-ink: #000000;
  --demo-line: #000000;
  --logo-bg: #ffffff;
  --breaking-bg: #000000;
  --breaking-ink: #ffffff;
  --breaking-muted: #ffffff;
  --btn-primary-bg: #000000;
  --btn-primary-ink: #ffffff;
  background: #ffffff;
  color: #000000;
}

body.high-contrast a {
  color: #0000ee;
  text-decoration: underline;
}

body.high-contrast .brand,
body.high-contrast .skip-link,
body.high-contrast .otv-btn {
  text-decoration: none;
}

body.high-contrast .brand {
  color: #000000;
}

body.high-contrast .site-header {
  background: #ffffff;
  border-bottom: 2px solid #000000;
}

body.high-contrast .site-nav a.is-active {
  border-bottom-color: #000000;
  color: #000000;
}

body.high-contrast .a11y-toggle {
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
}

body.high-contrast .a11y-panel {
  background: #ffffff;
  border: 2px solid #000000;
  border-top: 3px solid #000000;
}

body.high-contrast .a11y-options button {
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
}

body.high-contrast .a11y-options button[aria-pressed="true"] {
  background: #000000;
  color: #ffffff;
}

body.high-contrast .a11y-reset {
  color: #000000;
}

body.high-contrast .demo-bar {
  background: #ffffff;
  color: #000000;
  border-bottom: 2px solid #000000;
}

body.high-contrast .breaking {
  background: #000000;
  color: #ffffff;
  border-bottom: 2px solid #000000;
}

body.high-contrast .breaking-label {
  background: #ffffff;
  color: #000000;
}

body.high-contrast .breaking-text a,
body.high-contrast .breaking-all {
  color: #ffffff;
}

body.high-contrast .breaking-all {
  border-bottom-color: #ffffff;
}

body.high-contrast .lead {
  border-top: 3px solid #000000;
  border-bottom: 2px solid #000000;
}

body.high-contrast .section-head {
  border-top: 2px solid #000000;
}

body.high-contrast .sidebar h2,
body.high-contrast .most-read li,
body.high-contrast .sources li,
body.high-contrast .news-item,
body.high-contrast .brand-group,
body.high-contrast .otv-intro,
body.high-contrast .vehicle-row,
body.high-contrast .otv-note,
body.high-contrast .otv-calc,
body.high-contrast .site-footer {
  border-color: #000000;
}

body.high-contrast .vehicle-list {
  border-left: 2px solid #000000;
}

body.high-contrast .brand-mark {
  border: 2px solid #000000;
  background: #ffffff;
}

body.high-contrast .vehicle-ok {
  border: 1px solid #000000;
  color: #000000;
}

body.high-contrast .brand-chip {
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
}

body.high-contrast .brand-chip[aria-pressed="true"] {
  background: #000000;
  color: #ffffff;
}

body.high-contrast .demo-flag {
  border: 1px solid #000000;
  background: #ffffff;
  color: #000000;
}

body.high-contrast .otv-btn {
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
}

body.high-contrast .otv-btn-primary {
  background: #000000;
  color: #ffffff;
}

body.high-contrast .site-footer {
  background: #ffffff;
  border-top: 2px solid #000000;
  box-shadow: none;
  color: #000000;
}
body.high-contrast .footer-brand-link,
body.high-contrast .footer-nav h2,
body.high-contrast .footer-contact h2,
body.high-contrast .footer-nav a,
body.high-contrast .footer-contact a,
body.high-contrast .footer-brand > p,
body.high-contrast .footer-bottom {
  color: #000000;
}
body.high-contrast .footer-nav a,
body.high-contrast .footer-contact a { text-decoration: underline; }

body.high-contrast .otv-calc:target {
  background: #ffffff;
}

body.high-contrast :focus-visible {
  outline: 3px solid #0000ee;
  outline-offset: 2px;
}

/* Duyarlı yerleşim -------------------------------------------------------- */

@media (max-width: 1100px) {
  :root {
    --gap: 36px;
  }

  .site-nav ul {
    gap: 0.15rem 0.85rem;
  }
}

@media (max-width: 1240px) {
  .nav-toggle {
    display: inline-flex;
  }

  .a11y {
    margin-left: auto;
  }

  .a11y-toggle-text {
    display: none;
  }

  .a11y-toggle {
    padding: 0.5rem;
  }

  .site-nav {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin: 0;
    padding: 0.5rem 1.5rem 1rem;
    background: var(--paper);
    border-bottom: 1px solid var(--line-strong);
    max-height: calc(100vh - 5rem);
    overflow-y: auto;
  }

  .site-nav.is-open {
    display: block;
  }

  .site-nav ul {
    flex-direction: column;
    align-items: stretch;
    gap: 0;
  }

  .site-nav li {
    border-bottom: 1px solid var(--line);
  }

  .site-nav a {
    display: block;
    padding: 12px 2px;
    border-bottom: 0;
    font-size: 0.875rem;
  }

  .site-nav a.is-active {
    color: var(--accent-ink);
  }
}

@media (max-width: 900px) {
  .home-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "lead"
      "news"
      "sidebar"
      "otv"
      "tools"
      "chat";
    column-gap: 0;
  }

  .news {
    padding-top: 32px;
  }

  .sidebar {
    padding-top: 0;
    margin-top: 48px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 40px;
  }

  .lead h1 {
    max-width: none;
  }

  .otv-intro {
    grid-template-columns: minmax(0, 1fr);
    gap: 1rem;
  }

  .brand-group {
    grid-template-columns: minmax(0, 1fr);
    gap: 1rem;
  }

  .vehicle-list {
    padding-left: 0;
    border-left: 0;
  }
}

@media (max-width: 700px) {
  .wrap {
    width: min(var(--wrap), 100% - 32px);
  }

  .site-nav {
    padding-inline: 1rem;
  }

  .breaking-inner {
    flex-wrap: wrap;
    gap: 6px 10px;
    padding-block: 10px;
  }

  .breaking-text {
    order: 3;
    flex-basis: 100%;
    overflow: visible;
    font-size: 0.84rem;
    text-overflow: clip;
    white-space: normal;
  }

  .breaking-all {
    margin-left: auto;
  }

  .lead {
    padding: 24px 0 32px;
    margin-top: 20px;
  }

  .lead-summary {
    font-size: 1.04rem;
  }

  .otv {
    margin-top: 3.5rem;
  }

}

@media (max-width: 600px) {
  .vehicle-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .vehicle-row,
  .vehicle-row:nth-child(-n + 2) {
    border-top: 1px solid var(--line);
  }

  .vehicle-row:first-child {
    border-top: 0;
  }

  .otv-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .otv-update {
    text-align: left;
    white-space: normal;
  }

  .otv-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem 0;
  }

  .otv-summary p:nth-child(odd) {
    padding-left: 0;
    border-left: 0;
  }

  .otv-summary p:nth-child(even) {
    padding-left: 1rem;
  }

  .filter-label {
    flex-basis: 100%;
  }
}

@media (max-width: 560px) {
  .sidebar {
    grid-template-columns: minmax(0, 1fr);
  }

  .section-head {
    align-items: flex-end;
  }

  .otv-head {
    align-items: flex-start;
  }

  .section-head h2 {
    font-size: 1.32rem;
  }

.vehicle-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.35rem;
  }

  .vehicle-price {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0 0.5rem;
    text-align: left;
  }

  .price-label {
    flex-basis: 100%;
  }

  .price-list {
    margin-top: 0;
  }
}

@media (max-width: 400px) {
  .header-inner {
    gap: 0.5rem;
  }

  .brand {
    gap: 0.5rem;
  }

  .brand-logo {
    width: 40px;
    height: 40px;
  }

  .brand-name {
    font-size: 1.05rem;
  }

  .a11y-toggle {
    padding: 0.4rem;
  }

  .nav-toggle {
    width: 2.4rem;
    justify-content: center;
    padding: 0.4rem;
  }

  .nav-toggle-text {
    display: none;
  }

}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
}


/* İşlevsel araçlar — sağ sütunda editoryal liste, mobilde sayfa sonunda */
.tools-section {
  margin-top: 2.25rem;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
  scroll-margin-top: 6.5rem;
}

.tools-section-head {
  display: block;
  margin: 0 0 0.2rem;
  padding: 0.85rem 0 0;
  border-top: 2px solid var(--ink);
}

.tools-section-head h2 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.tools-section-head > div > p {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.45;
}

.tools-section .tool-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
  margin-top: 0.45rem;
}

.tool-card {
  display: grid;
  grid-template-columns: 1.7rem minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.65rem;
  min-width: 0;
  min-height: 0;
  padding: 0.82rem 0;
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  color: var(--ink);
  text-decoration: none;
  transition: color 140ms ease;
}

.tool-card:first-child { border-top: 1px solid var(--line); }
.tool-card:hover {
  background: transparent;
  border-color: var(--line-strong);
  color: var(--accent-ink);
}
.tool-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

.tool-icon {
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  width: 1.7rem;
  height: auto;
  padding-top: 0.08rem;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--accent);
  font-size: 1.05rem;
  font-weight: 800;
  line-height: 1.2;
}
.tool-icon-guide { font-size: 1.05rem; }
.tool-icon-pdf { font-size: 0.66rem; letter-spacing: -0.03em; }

.tool-copy {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}
.tool-copy strong {
  color: var(--ink);
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.35;
}
.tool-copy > span {
  color: var(--muted);
  font-size: 0.7rem;
  line-height: 1.45;
}
.tool-copy .tool-route-note {
  color: var(--muted);
  font-size: 0.64rem;
  line-height: 1.35;
}
.tool-arrow {
  align-self: center;
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 600;
  transition: color 140ms ease, transform 140ms ease;
}
.tool-card:hover .tool-copy strong,
.tool-card:hover .tool-arrow { color: var(--accent-ink); }
.tool-card:hover .tool-arrow { transform: translate(2px, -2px); }

.tools-footnote {
  margin: 0.75rem 0 0;
  color: var(--muted);
  font-size: 0.64rem;
  line-height: 1.5;
}

body.dark-mode .tool-card { background: transparent; border-color: var(--line); }
body.dark-mode .tool-icon,
body.dark-mode .tool-arrow { color: var(--accent); }
body.high-contrast .tool-card {
  background: #ffffff;
  border: 0;
  border-bottom: 2px solid #000000;
  color: #000000;
}
body.high-contrast .tool-card:first-child { border-top: 2px solid #000000; }
body.high-contrast .tool-copy strong,
body.high-contrast .tool-copy > span,
body.high-contrast .tools-footnote,
body.high-contrast .tool-icon,
body.high-contrast .tool-arrow { color: #000000; }

@media (max-width: 900px) {
  .tools-section { margin-top: 3.5rem; }
  .tools-section .tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 1.5rem;
  }
}
@media (max-width: 560px) {
  .tools-section { margin-top: 3rem; padding-top: 0; }
  .tools-section .tool-grid { grid-template-columns: minmax(0, 1fr); }
  .tool-card { padding: 0.78rem 0; }
}
@media (prefers-reduced-motion: reduce) {
  .tool-card, .tool-arrow { transition: none; }
}


/* Ana sayfa sohbet daveti — footer öncesinde tam genişlikli topluluk bağlantısı */
.chat-invite {
  grid-area: chat;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  min-width: 0;
  margin-top: 3rem;
  padding: clamp(20px, 3vw, 32px);
  border: 1px solid var(--line-strong);
  border-left: 4px solid var(--accent);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: 0 8px 24px rgba(22, 33, 31, 0.045);
}
.chat-invite-copy {
  min-width: 0;
  max-width: 64ch;
}
.chat-invite .kicker {
  margin: 0 0 0.45rem;
  color: var(--accent);
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}
.chat-invite h2 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(1.3rem, 2.2vw, 1.8rem);
  line-height: 1.2;
}
.chat-invite-copy > p:not(.kicker) {
  margin: 0.55rem 0 0;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.6;
}
.chat-invite-copy .chat-invite-note {
  font-size: 0.72rem;
}
.chat-invite-link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 14px;
  min-height: 48px;
  padding: 12px 18px;
  border: 1px solid var(--btn-primary-bg);
  border-radius: 999px;
  background: var(--btn-primary-bg);
  color: var(--btn-primary-ink);
  font-size: 0.82rem;
  font-weight: 750;
  white-space: nowrap;
  transition: transform 140ms ease, background 140ms ease;
}
.chat-invite-link:hover {
  color: var(--btn-primary-ink);
  background: var(--accent-ink);
  border-color: var(--accent-ink);
  transform: translateY(-1px);
}
.chat-invite-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
body.high-contrast .chat-invite {
  background: #ffffff;
  border: 2px solid #000000;
  border-left-width: 6px;
  box-shadow: none;
}
body.high-contrast .chat-invite .kicker,
body.high-contrast .chat-invite h2,
body.high-contrast .chat-invite-copy > p,
body.high-contrast .chat-invite-link {
  color: #000000;
}
body.high-contrast .chat-invite-link {
  background: #ffffff;
  border: 2px solid #000000;
  text-decoration: underline;
}
@media (max-width: 560px) {
  .chat-invite {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
    margin-top: 2.25rem;
    padding: 20px;
  }
  .chat-invite-link {
    width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .chat-invite-link { transition: none; }
}


/* Haber arşiv düğmesi ve mobil sadeleştirme */
.news-archive-toggle {
  appearance: none;
  border: 0;
  padding: 0;
  margin: 0;
  background: transparent;
  color: var(--accent-ink);
  font: inherit;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  text-align: right;
}
.news-archive-toggle:hover {
  text-decoration: underline;
  text-underline-offset: 4px;
}
.news-archive-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}


/* V4.3/V4.4 — mobil sadeleştirme ve uyarlanmış footer */
@media (max-width: 700px) {
  .sidebar { display: none !important; }
  .site-footer {
    margin-top: 44px;
    padding: 28px 18px 16px;
  }
  .footer-inner { width: 100%; }
  .footer-top {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 24px 18px;
    padding-bottom: 22px;
  }
  .footer-brand { grid-column: 1 / -1; }
  .footer-brand > p { max-width: 48ch; }
  .footer-bottom {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
}
@media (max-width: 420px) {
  .footer-top { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .footer-brand { grid-column: auto; }
  .footer-brand > p { max-width: 36ch; }
  .footer-nav, .footer-contact { gap: 7px; }
}
/* ==========================================================================
   Engelli.me — portal entegrasyon katmanı
   V4.4 görsel dili korunarak canlı FastAPI uygulamasına bağlanan ekranlar:
   haber arşivi, haber detayı, kira/Excel/PDF araçları, ayrıntılı ÖTV listesi.
   ========================================================================== */

/* Sayfa yönlendirme (SPA) -------------------------------------------------- */
.page { display: none; }
.page.on { display: block; }
.page.on.home-grid { display: grid; }

.page-inner {
  width: 100%;
  max-width: 60rem;
  margin: 0 auto;
  padding: 30px 0 76px;
}

.page-head {
  padding-top: 16px;
  border-top: 3px solid var(--ink);
  margin-bottom: 22px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.9rem;
  color: var(--accent-ink);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.back-link:hover { text-decoration: underline; text-underline-offset: 4px; }

.page-head h1,
.page-head h2 {
  margin: 0 0 0.55rem;
  font-family: var(--font-serif);
  font-size: clamp(1.7rem, 3.2vw, 2.4rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.14;
}

.page-note {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.76rem;
  line-height: 1.5;
}

/* Haber listesi ve arşiv --------------------------------------------------- */
#homeNews .news-item:first-child { border-top: 0; margin-top: 8px; }
.archive-list .news-item:first-child { border-top: 0; margin-top: 0; }

.news-item .meta time { font-variant-numeric: tabular-nums; }

.news-item h3 a[data-news-index] { cursor: pointer; }

.news-empty {
  padding: 20px 0;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.6;
}

/* Haber detayı ------------------------------------------------------------- */
.detail-title {
  margin: 0 0 0.7rem;
  font-family: var(--font-serif);
  font-size: clamp(1.7rem, 3.6vw, 2.6rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.16;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2rem 0.55rem;
  margin: 0 0 1.1rem;
  color: var(--muted);
  font-size: 0.78rem;
}

.detail-source {
  color: var(--accent-ink);
  font-weight: 700;
}

.article-body {
  padding-top: 1.1rem;
  border-top: 1px solid var(--line);
}

.article-body p {
  max-width: 68ch;
  margin: 0 0 1rem;
  color: var(--ink-soft);
  font-family: var(--font-serif);
  font-size: 1.06rem;
  line-height: 1.78;
}

.article-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  margin-top: 1.4rem;
  padding-top: 1.2rem;
  border-top: 1px solid var(--line);
}

.article-note {
  margin: 1.1rem 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.6;
}

/* Formlar ve araç ekranları ------------------------------------------------ */
.form-card {
  margin-top: 1.2rem;
  padding: 1.4rem 1.5rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 4px;
}

.field {
  display: block;
  margin: 0 0 0.4rem;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.input,
.form-card select,
.form-card textarea {
  width: 100%;
  margin-bottom: 1.05rem;
  padding: 0.66rem 0.75rem;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  background: var(--surface);
  color: var(--ink);
  font-size: 0.95rem;
  line-height: 1.4;
}

.form-card textarea { min-height: 6.5rem; resize: vertical; }

.input:focus-visible,
.form-card select:focus-visible,
.form-card textarea:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.filebox {
  position: relative;
  margin-bottom: 1rem;
  padding: 1rem;
  border: 1px dashed var(--line-strong);
  border-radius: 3px;
  background: var(--paper);
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.5;
}

.filebox input[type="file"] {
  display: block;
  width: 100%;
  margin-top: 0.5rem;
  color: var(--ink);
  font-size: 0.8rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-height: 2.7rem;
  padding: 0.7rem 1.2rem;
  border: 1px solid var(--btn-primary-bg);
  border-radius: 3px;
  background: var(--btn-primary-bg);
  color: var(--btn-primary-ink);
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.3;
  cursor: pointer;
}
.btn:hover { background: var(--accent-ink); border-color: var(--accent-ink); color: #ffffff; }
.btn:disabled { opacity: 0.7; cursor: progress; }

.result {
  display: none;
  margin-top: 1.2rem;
  padding: 1.1rem 1.2rem;
  border-left: 3px solid var(--accent);
  background: var(--accent-soft);
  color: var(--ink);
  font-size: 0.9rem;
  line-height: 1.65;
}
.result .big {
  margin: 0.1rem 0 0.7rem;
  font-family: var(--font-serif);
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.2;
}
.result .note { color: var(--muted); font-size: 0.76rem; }

.form-note {
  margin: 1rem 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.6;
}
.form-note a { color: var(--accent-ink); font-weight: 700; text-decoration: underline; text-underline-offset: 2px; }

/* Ayrıntılı ÖTV listesi ---------------------------------------------------- */
.flat-list { display: grid; gap: 0; margin-top: 1rem; }

.flat-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  padding: 1rem 0;
  border-top: 1px solid var(--line);
}
.flat-row:last-child { border-bottom: 1px solid var(--line); }

.flat-row .vehicle-name { font-size: 1.05rem; }

.flat-row .vehicle-source { grid-column: 1 / -1; margin-top: 0.35rem; }

.flat-price { text-align: right; white-space: nowrap; }

.flat-price .price-value { font-size: 1.05rem; }

.summary-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 1.4rem;
  margin: 0 0 0.4rem;
  padding: 0.9rem 0;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.78rem;
}
.summary-strip strong { color: var(--ink); font-size: 0.95rem; }

.brand-title .locality { color: var(--muted); }

/* Alt bilgi ve mobil gezinme ---------------------------------------------- */
.footer-links { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; }

.bottom-home {
  display: none;
  align-items: center;
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 45;
  padding: 0.6rem 0.9rem;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  background: var(--surface);
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 700;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.14);
  cursor: pointer;
}

/* Kaydırma hedefleri ------------------------------------------------------- */
#hesaplamalar,
#otv-araclar,
#helpers { scroll-margin-top: 6.5rem; }

/* Duyarlı ekler ----------------------------------------------------------- */
@media (max-width: 900px) {
  .page-inner { padding: 22px 0 64px; }

  .flat-row { grid-template-columns: minmax(0, 1fr); }
  .flat-price { text-align: left; }

  .bottom-home.show { display: inline-flex; }
}

@media (max-width: 600px) {
  .form-card { padding: 1.1rem; }
  .article-body p { font-size: 1rem; }
}

@media (max-width: 700px) {
  .bottom-home { display: none; }
}

/* Yüksek kontrast düzeltmeleri -------------------------------------------- */
body.high-contrast .form-card,
body.high-contrast .filebox,
body.high-contrast .flat-row,
body.high-contrast .result {
  border-color: #000000;
}
body.high-contrast .filebox { border-style: solid; }
body.high-contrast .input,
body.high-contrast .form-card select,
body.high-contrast .form-card textarea,
body.high-contrast .btn,
body.high-contrast .bottom-home {
  border: 2px solid #000000;
  background: #ffffff;
  color: #000000;
}
body.high-contrast .btn,
body.high-contrast .bottom-home { background: #000000; color: #ffffff; }
body.high-contrast .result { background: #ffffff; }
body.high-contrast .back-link,
body.high-contrast .detail-source { color: #0000ee; }

/* Koyu mod düzeltmeleri --------------------------------------------------- */
body.dark-mode .filebox { background: var(--paper); }
body.dark-mode .result { background: var(--accent-soft); }
</style>
</head>
<body>
<a class="skip-link" href="#icerik">İçeriğe geç</a>

<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/" aria-label="Engelli.me ana sayfa">
      <img class="brand-logo" src="/logo.png?v=1" alt="" width="46" height="46" decoding="async">
      <span class="brand-name">Engelli<span class="brand-dot">.me</span></span>
    </a>

    <nav id="site-nav" class="site-nav" aria-label="Ana menü">
      <ul>
        <li><a href="#home" id="navHome" class="is-active" aria-current="page" onclick="return goPage('home')">Ana Sayfa</a></li>
        <li><a href="#news" id="navNews" onclick="return goPage('news')">Haberler</a></li>
        <li><a href="#hesaplamalar" onclick="return goSection('hesaplamalar')">Yardımcılar</a></li>
        <li><a href="#otv-araclar" onclick="return goSection('otv-araclar')">ÖTV Muafiyetli Araçlar</a></li>
      </ul>
    </nav>

    <div class="a11y">
      <button type="button" id="accessibilityToggle" class="a11y-toggle"
              aria-expanded="false" aria-controls="accessibilityPanel" aria-label="Erişilebilirlik seçeneklerini aç">
        <svg class="a11y-icon" viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" focusable="false">
          <circle cx="12" cy="4.3" r="2.1" fill="currentColor"></circle>
          <path d="M4.2 8.1c0-.7.6-1.3 1.3-1.3h13c.7 0 1.3.6 1.3 1.3s-.6 1.3-1.3 1.3h-4.1l1.4 5.1 2.2 5.9c.3.7-.1 1.4-.8 1.7-.7.3-1.4-.1-1.7-.8l-2-5.4h-1.1l-2 5.4c-.3.7-1 1.1-1.7.8-.7-.3-1.1-1-.8-1.7l2.2-5.9 1.4-5.1H5.5c-.7 0-1.3-.6-1.3-1.3Z" fill="currentColor"></path>
        </svg>
        <span class="a11y-toggle-text">Erişilebilirlik</span>
      </button>

      <div id="accessibilityPanel" class="a11y-panel" role="group" aria-label="Erişilebilirlik seçenekleri" tabindex="-1">
        <div class="a11y-head">
          <span class="a11y-title">Erişilebilirlik seçenekleri</span>
          <button type="button" id="accessibilityReset" class="a11y-reset">Sıfırla</button>
        </div>
        <div class="a11y-options">
          <button type="button" data-font="1" aria-label="Standart yazı boyutu" aria-pressed="true">A</button>
          <button type="button" data-font="1.12" aria-label="Büyük yazı boyutu" aria-pressed="false">A+</button>
          <button type="button" data-font="1.25" aria-label="Daha büyük yazı boyutu" aria-pressed="false">A++</button>
          <button type="button" id="contrastToggle" class="a11y-wide" aria-pressed="false">Yüksek kontrast</button>
          <button type="button" id="darkToggle" class="a11y-wide" aria-pressed="false">Koyu mod</button>
        </div>
        <p class="a11y-note">Ayarlar bu tarayıcıda saklanır. Escape ile kapatılır.</p>
        <p class="sr-only" id="a11yStatus" role="status" aria-live="polite"></p>
      </div>
    </div>

    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Menüyü aç">
      <span class="nav-toggle-bars" aria-hidden="true"></span>
      <span class="nav-toggle-text">Menü</span>
    </button>
  </div>
</header>

<section class="breaking" aria-label="Son dakika haberleri">
  <div class="wrap breaking-inner">
    <span class="breaking-label">Son dakika</span>
    <p class="breaking-text">
      <a href="#news" id="breakingLink">Güncel engelli haberleri yükleniyor…</a>
    </p>
    <time class="breaking-time" id="breakingTime"></time>
    <a class="breaking-all" href="#news" onclick="return goPage('news')">Tümü</a>
  </div>
</section>

<main id="icerik" class="wrap">
<section id="home" class="page on home-grid" aria-label="Ana sayfa">

  <section class="lead" id="manset" aria-labelledby="manset-baslik">
    <p class="kicker">Manşet</p>
    <h1 id="manset-baslik"><a href="#newsDetail" id="leadLink">Güncel engelli haberleri yükleniyor…</a></h1>
    <p class="lead-summary" id="leadSummary"></p>
    <p class="meta">
      <time id="leadDate"></time>
      <span class="meta-sep" aria-hidden="true">·</span>
      <span id="leadSource"></span>
    </p>
  </section>

  <section class="news" id="son-haberler" aria-labelledby="son-haberler-baslik">
    <div class="section-head">
      <h2 id="son-haberler-baslik">Son haberler</h2>
      <a class="section-link" href="#news" onclick="return goPage('news')">Tüm haberler</a>
    </div>
    <p class="feed-note">Ana sayfada en yeni 7 haber (manşet dahil) gösterilir; tüm arşivi Haberler sayfasında bulabilirsiniz.</p>
    <ol class="news-list" id="homeNews">
      <li class="news-empty">Haberler yükleniyor…</li>
    </ol>
  </section>

  <aside class="sidebar" aria-label="Yan sütun">
    <section class="most-read" aria-labelledby="cok-okunanlar-baslik">
      <h2 id="cok-okunanlar-baslik">Çok okunanlar</h2>
      <ol id="mostRead">
        <li><span class="most-read-text">Yükleniyor…</span></li>
      </ol>
    </section>

    <section class="sources" aria-labelledby="kaynaklar-baslik">
      <h2 id="kaynaklar-baslik">Haber kaynakları</h2>
      <ul>
        <li>Anadolu Ajansı</li>
        <li>TRT Haber</li>
        <li>Aile ve Sosyal Hizmetler Bakanlığı</li>
        <li>SGK Duyuruları</li>
        <li>GİB Güncel Duyurular</li>
        <li>Türkiye Belediyeler Birliği</li>
      </ul>
      <p class="note">Haberler yalnızca bu resmî kaynaklardan, otomatik akışla derlenir.</p>
    </section>
  </aside>

  <section class="tools-section" id="hesaplamalar" aria-labelledby="hesaplamalar-baslik">
    <span id="helpers" aria-hidden="true"></span>
    <div class="tools-section-head">
      <div>
        <h2 id="hesaplamalar-baslik">Yardımcılar</h2>
        <p>İhtiyacınız olan işlemlere tek yerden ulaşın</p>
      </div>
    </div>
    <div class="tool-grid">
      <a class="tool-card" href="/arac1">
        <span class="tool-icon" aria-hidden="true">%</span>
        <span class="tool-copy">
          <strong>Hastalık Oranı Bulma</strong>
          <span>Hastalık ve değerlendirme basamağına göre kaynak oranını incele</span>
        </span>
        <span class="tool-arrow" aria-hidden="true">→</span>
      </a>
      <a class="tool-card" href="/arac2">
        <span class="tool-icon" aria-hidden="true">＋</span>
        <span class="tool-copy">
          <strong>Balthazard Oranı Hesaplama</strong>
          <span>Bilinen engellilik oranlarını Balthazard formülüyle birleştir</span>
        </span>
        <span class="tool-arrow" aria-hidden="true">→</span>
      </a>
      <a class="tool-card" href="/arac3">
        <span class="tool-icon tool-icon-guide" aria-hidden="true">§</span>
        <span class="tool-copy">
          <strong>Çalışma Gücü Kaybı Rehberi</strong>
          <span>Ek-1 hastalık listesi, FAS ve rehber açıklamalar</span>
        </span>
        <span class="tool-arrow" aria-hidden="true">→</span>
      </a>
      <a class="tool-card" href="#kira" onclick="return goPage('kira')">
        <span class="tool-icon" aria-hidden="true">₺</span>
        <span class="tool-copy">
          <strong>Kira Hesaplama</strong>
          <span>TÜFE ile kira artışını hesapla</span>
        </span>
        <span class="tool-arrow" aria-hidden="true">→</span>
      </a>
      <a class="tool-card" href="#excel" onclick="return goPage('excel')">
        <span class="tool-icon" aria-hidden="true">X</span>
        <span class="tool-copy">
          <strong>Excel İşlemleri</strong>
          <span>Düşeyara, birleştirme ve pivot</span>
        </span>
        <span class="tool-arrow" aria-hidden="true">→</span>
      </a>
      <a class="tool-card" href="#pdfexcel" onclick="return goPage('pdfexcel')">
        <span class="tool-icon tool-icon-pdf" aria-hidden="true">PDF</span>
        <span class="tool-copy">
          <strong>PDF → Excel</strong>
          <span>PDF içeriğini Excel'e aktar</span>
        </span>
        <span class="tool-arrow" aria-hidden="true">→</span>
      </a>
    </div>
    <p class="tools-footnote">Hastalık oranı, Balthazard ve çalışma gücü rehberi ayrı sayfalarda açılır. Kira, Excel ve PDF → Excel işlemleri bu portal içinde çalışır.</p>
  </section>

  <section class="otv" id="otv-araclar" aria-labelledby="otv-baslik">
    <div class="section-head otv-head">
      <div>
        <p class="kicker">Araç rehberi</p>
        <h2 id="otv-baslik">ÖTV Muafiyetli Araçlar</h2>
      </div>
      <p class="otv-update">
        Son fiyat kontrolü<br>
        <strong id="homeOtvUpdate">—</strong>
      </p>
    </div>

    <div class="otv-intro">
      <p>
        2026 ÖTV muafiyeti üst limiti <strong id="otvLimit">—</strong>. Listede yerli katkı oranı
        en az <strong>%40</strong> olan M1 araçlar ve güncel uygun paketleri yer alıyor.
        Her paket için liste fiyatı ile mevcut sistemdeki yöntemle hesaplanan ÖTV muaf fiyatı
        birlikte gösterilir.
      </p>
      <p class="otv-intro-note">
        Fiyatlar ve uygunluk bilgileri Engelli.me canlı ÖTV verisinden alınır; sayfa her açılışta
        güncel veriyi kontrol eder.
      </p>
    </div>

    <div class="otv-summary">
      <p><strong id="homeOtvCount">—</strong> uygun paket</p>
      <p><strong id="homeOtvBrands">—</strong> marka</p>
      <p><strong>%40</strong> asgari yerlilik</p>
      <p><strong id="homeOtvLimit">—</strong> 2026 üst limiti</p>
    </div>

    <div class="brand-filter">
      <p class="filter-label" id="brandFilterLabel">Markaya göre filtrele</p>
      <div class="filter-buttons" id="homeBrandChips" role="group" aria-labelledby="brandFilterLabel"></div>
      <p class="sr-only" id="vehicleFilterStatus" role="status" aria-live="polite"></p>
    </div>

    <div class="brand-list" id="homeBrandList">
      <p class="news-empty">Araç listesi yükleniyor…</p>
    </div>

    <div class="otv-actions">
      <a class="otv-btn otv-btn-primary" href="#otv" onclick="return goPage('otv')">
        Ayrıntılı araç listesi <span aria-hidden="true">→</span>
      </a>
      <a class="otv-btn" href="#otv-hesaplama">
        ÖTV muaf fiyat hesaplaması
      </a>
    </div>

    <div class="otv-calc" id="otv-hesaplama">
      <h3>ÖTV muaf fiyatı nasıl hesaplanıyor?</h3>
      <p>
        Muaf fiyat, ayrıntılı araç listesinde her paket için
        <strong>“Hesaplanmış ÖTV Muaf Fiyat”</strong> satırı olarak otomatik hesaplanır.
        Yukarıdaki “Muaf fiyat” değerleri de aynı yöntemle türetilmiştir; resmî ÖTV tutarı yerine
        bilgilendirme amaçlıdır.
      </p>
      <p class="otv-calc-link">
        <a href="#otv" onclick="return goPage('otv')">Ayrıntılı listede hesaplanmış fiyatları gör <span aria-hidden="true">→</span></a>
      </p>
    </div>

    <p class="otv-note">
      Kaynak: T.C. Sanayi ve Teknoloji Bakanlığı 2026 yerli katkı oranı beyanları ve marka
      fiyat listeleri. Yerlilik verisi bulunmayan markalarda “—” gösterilir. Fiyatı
      doğrulanamayan veya 2026 limitini aşan adaylar listeye alınmaz. Bu bölümde araç fotoğrafı
      kullanılmaz; yalnızca marka logoları yer alır.
    </p>
  </section>

  <section class="chat-invite" aria-labelledby="chat-invite-title">
    <div class="chat-invite-copy">
      <p class="kicker">Topluluğa katıl</p>
      <h2 id="chat-invite-title">Engelli.me Sohbet</h2>
      <p>Engelli hakları ve günlük yaşam üzerine diğer ziyaretçilerle sohbet edin, deneyimlerinizi paylaşın.</p>
      <p class="chat-invite-note">Gizliliğiniz için sohbette kimlik, iletişim veya sağlık bilgilerinizi paylaşmayın.</p>
    </div>
    <a class="chat-invite-link" href="https://chat.engelli.me/" target="_blank" rel="noopener noreferrer" aria-label="Engelli.me canlı sohbeti yeni sekmede aç">
      <span>Canlı sohbete katıl</span>
      <span aria-hidden="true">↗</span>
    </a>
  </section>

</section>
<section id="news" class="page" aria-labelledby="arsiv-baslik">
  <div class="page-inner">
    <div class="page-head">
      <a class="back-link" href="#home" onclick="return goPage('home')">‹ Ana sayfa</a>
      <h1 id="arsiv-baslik">Güncel engelli haberleri</h1>
      <p class="page-note" id="newsUpdated">Güncelleniyor…</p>
    </div>
    <ol class="news-list archive-list" id="newsList">
      <li class="news-empty">Haberler yükleniyor…</li>
    </ol>
  </div>
</section>

<section id="newsDetail" class="page" aria-labelledby="newsDetailTitle">
  <div class="page-inner">
    <div class="page-head">
      <a class="back-link" href="#news" onclick="return goPage('news')">‹ Haberler</a>
      <p class="kicker" id="newsDetailKicker">Haber</p>
      <h1 class="detail-title" id="newsDetailTitle"></h1>
      <p class="detail-meta">
        <time id="newsDetailDate"></time>
        <span class="meta-sep" aria-hidden="true">·</span>
        <span class="detail-source" id="newsDetailSource"></span>
      </p>
    </div>
    <div class="article-body" id="newsDetailSummary"></div>
    <div class="article-actions">
      <a class="otv-btn otv-btn-primary" id="newsDetailLink" href="#" target="_blank" rel="noopener noreferrer" hidden>Haberi kaynağında aç <span aria-hidden="true">↗</span></a>
      <button type="button" class="otv-btn" id="newsDetailShare" aria-label="Bu haberi paylaş">Haberi paylaş</button>
    </div>
    <p class="article-note" id="newsDetailNote">Haber içeriği yayımlayan kurumun resmî kaynağından alınmıştır. Ayrıntı ve güncellemeler için kaynak bağlantısını kullanın.</p>
  </div>
</section>

<section id="otv" class="page" aria-labelledby="otv-page-baslik">
  <div class="page-inner">
    <div class="page-head">
      <a class="back-link" href="#home" onclick="return goPage('home')">‹ Ana sayfa</a>
      <p class="kicker">Araç rehberi</p>
      <h1 id="otv-page-baslik">ÖTV Muafiyetli Araçlar · Ayrıntılı liste</h1>
      <p class="page-note" id="otvSummaryText">Yükleniyor…</p>
    </div>
    <div class="summary-strip">
      <span>2026 üst limiti: <strong id="otvPageLimit">—</strong></span>
      <span>Asgari yerlilik: <strong>%40</strong></span>
    </div>
    <div class="brand-filter">
      <p class="filter-label" id="otvFilterLabel">Markaya göre filtrele</p>
      <div class="filter-buttons" id="otvChips" role="group" aria-labelledby="otvFilterLabel"></div>
    </div>
    <div class="flat-list" id="otvList">
      <p class="news-empty">Araç listesi yükleniyor…</p>
    </div>
    <p class="otv-note">
      Liste fiyatları marka fiyat listelerinden, yerlilik oranları T.C. Sanayi ve Teknoloji
      Bakanlığı beyanlarından alınır. “Hesaplanmış ÖTV Muaf Fiyat” bilgilendirme amaçlıdır;
      resmî ÖTV tutarı yerine geçmez.
    </p>
  </div>
</section>

<section id="kira" class="page" aria-labelledby="kira-baslik">
  <div class="page-inner">
    <div class="page-head">
      <a class="back-link" href="#home" onclick="return goPage('home')">‹ Ana sayfa</a>
      <p class="kicker">Yardımcılar</p>
      <h1 id="kira-baslik">Kira Hesaplama</h1>
      <p class="page-note">Mevcut kiranızı ve yenileme ayını girin; 12 aylık ortalama TÜFE ile yeni kirayı hesaplayalım.</p>
    </div>
    <div class="form-card">
      <form onsubmit="kiraHesapla(event)">
        <label class="field" for="mevcut-kira">Mevcut kira (TL)</label>
        <input id="mevcut-kira" class="input" type="number" min="1" step="0.01" placeholder="Örn: 12000" required>
        <label class="field" for="yenileme-ayi">Kira yenileme ayı</label>
        <select id="yenileme-ayi" required>
          <option value="">Ay seçin</option>
          <option value="1">Ocak</option>
          <option value="2">Şubat</option>
          <option value="3">Mart</option>
          <option value="4">Nisan</option>
          <option value="5">Mayıs</option>
          <option value="6">Haziran</option>
          <option value="7">Temmuz</option>
          <option value="8">Ağustos</option>
          <option value="9">Eylül</option>
          <option value="10">Ekim</option>
          <option value="11">Kasım</option>
          <option value="12">Aralık</option>
        </select>
        <button id="kira-btn" class="btn" type="submit">Hesapla</button>
      </form>
      <div id="kira-result" class="result" role="status" aria-live="polite"></div>
      <div class="article-actions">
        <button type="button" id="kiraShare" class="otv-btn" aria-label="Kira hesaplama sayfasını paylaş">Sayfayı paylaş</button>
      </div>
      <p class="form-note">Hesaplama, TÜİK tarafından açıklanan 12 aylık ortalama TÜFE oranını kullanır. Sonuç bilgilendirme amaçlıdır.</p>
    </div>
  </div>
</section>

<section id="excel" class="page" aria-labelledby="excel-baslik">
  <div class="page-inner">
    <div class="page-head">
      <a class="back-link" href="#home" onclick="return goPage('home')">‹ Ana sayfa</a>
      <p class="kicker">Yardımcılar</p>
      <h1 id="excel-baslik">Excel İşlemleri</h1>
      <p class="page-note">İki Excel dosyası yükleyin ve yapmak istediğiniz işlemi yazın. Sonuç dosyası işlem bitince indirilir.</p>
    </div>
    <div class="form-card">
      <form action="/excel-islem" method="post" enctype="multipart/form-data">
        <div class="filebox">1. Excel (Ana Dosya)<input type="file" name="file1" accept=".xlsx,.xls" required></div>
        <div class="filebox">2. Excel (Referans Dosyası)<input type="file" name="file2" accept=".xlsx,.xls" required></div>
        <label class="field" for="excel-komut">İşlem</label>
        <textarea id="excel-komut" name="komut" placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap." required></textarea>
        <button class="btn" type="submit">Excel işlemini başlat</button>
      </form>
      <p class="form-note">Yüklediğiniz dosyalar yalnızca işlem amacıyla kullanılır ve kalıcı olarak saklanmaz. <a href="/kvkk" target="_blank" rel="noopener noreferrer">KVKK Aydınlatma Metni</a></p>
    </div>
  </div>
</section>

<section id="pdfexcel" class="page" aria-labelledby="pdf-baslik">
  <div class="page-inner">
    <div class="page-head">
      <a class="back-link" href="#home" onclick="return goPage('home')">‹ Ana sayfa</a>
      <p class="kicker">Yardımcılar</p>
      <h1 id="pdf-baslik">PDF → Excel</h1>
      <p class="page-note">Bir PDF dosyası seçin; içeriği tabloya dönüştürülerek Excel dosyası olarak indirilir.</p>
    </div>
    <div class="form-card">
      <form action="/pdf-excel-islem" method="post" enctype="multipart/form-data">
        <div class="filebox"><span id="pdfFileName">PDF seçilmedi — PDF dosyasını seç</span><input type="file" name="pdf_file" accept=".pdf" required onchange="pdfSecildi(this)"></div>
        <button class="btn" type="submit">PDF'i Excel'e çevir</button>
      </form>
      <p class="form-note">Yüklediğiniz dosyalar yalnızca işlem amacıyla kullanılır ve kalıcı olarak saklanmaz. <a href="/kvkk" target="_blank" rel="noopener noreferrer">KVKK Aydınlatma Metni</a></p>
    </div>
  </div>
</section>
</main>
<footer class="site-footer" aria-label="Site alt bilgisi">
  <div class="footer-inner">
    <div class="footer-top">
      <section class="footer-brand" aria-labelledby="footer-brand-title">
        <a class="footer-brand-link" href="#home" onclick="return goPage('home')" aria-label="Engelli.me ana sayfaya dön">
          <img src="/logo.png?v=1" alt="" width="42" height="42" loading="lazy" decoding="async">
          <span id="footer-brand-title">Engelli<span class="footer-brand-dot">.me</span></span>
        </a>
        <p>Engelli hakları, mevzuat ve günlük yaşam için güncel haberler ve pratik araçlar.</p>
        <p class="footer-note">Bilgilendirici içerikler ve kullanışlı hesaplama araçları tek yerde.</p>
      </section>

      <nav class="footer-nav" aria-label="Hızlı bağlantılar">
        <h2>Keşfet</h2>
        <a href="#news" onclick="return goPage('news')">Güncel haberler</a>
        <a href="#hesaplamalar" onclick="return goSection('hesaplamalar')">Yardımcılar</a>
        <a href="#otv-araclar" onclick="return goSection('otv-araclar')">ÖTV muafiyetli araçlar</a>
      </nav>

      <section class="footer-contact" aria-labelledby="footer-contact-title">
        <h2 id="footer-contact-title">İletişim ve bilgiler</h2>
        <a class="footer-email" href="mailto:info@engelli.me">info@engelli.me</a>
        <a class="footer-legal" href="/kvkk">KVKK aydınlatma metni <span aria-hidden="true">→</span></a>
      </section>
    </div>

    <div class="footer-bottom">
      <p>© 2026 Engelli.me</p>
      <p>Engelli hakları, güncel gelişmeler ve erişilebilir dijital araçlar.</p>
    </div>
  </div>
</footer>

<button id="bottomHome" class="bottom-home" type="button" onclick="goPage('home')">⌂ Ana Sayfa</button>

<script>
let otvData=/*INITIAL_OTV_DATA*/{},activeBrand=null;
if(!otvData||!otvData.vehicles)otvData={vehicles:[],limit:2873900};
let newsData=/*INITIAL_NEWS_DATA*/{};if(!newsData||!newsData.items)newsData={items:[],updated_at:null};

/* ---- Erişilebilirlik ---------------------------------------------------- */
const FONT_KEY='engellime-font-size',CONTRAST_KEY='engellime-high-contrast',DARK_KEY='engellime-dark-mode',FONT_VALUES=['1','1.12','1.25'];
function storeGet(k){try{return window.localStorage.getItem(k)}catch(e){return null}}
function storeSet(k,v){try{window.localStorage.setItem(k,v)}catch(e){}}
function storeRemove(k){try{window.localStorage.removeItem(k)}catch(e){}}
const accessibilityToggle=document.getElementById('accessibilityToggle'),accessibilityPanel=document.getElementById('accessibilityPanel');
const a11yStatus=document.getElementById('a11yStatus');
function announce(message){if(a11yStatus)a11yStatus.textContent=message}
function currentFont(){let v=storeGet(FONT_KEY)||'1';return FONT_VALUES.indexOf(v)>=0?v:'1'}
function applyAccessibility(){let font=currentFont(),contrast=storeGet(CONTRAST_KEY)==='1',dark=storeGet(DARK_KEY)==='1';document.documentElement.style.setProperty('--font-scale',font);document.body.classList.toggle('font-large',font==='1.12');document.body.classList.toggle('font-xlarge',font==='1.25');document.body.classList.toggle('high-contrast',contrast);document.body.classList.toggle('dark-mode',dark);document.querySelectorAll('[data-font]').forEach(b=>{b.setAttribute('aria-pressed',b.dataset.font===font?'true':'false')});let c=document.getElementById('contrastToggle'),d=document.getElementById('darkToggle');if(c)c.setAttribute('aria-pressed',contrast?'true':'false');if(d)d.setAttribute('aria-pressed',dark?'true':'false')}
function setAccessibilityPanel(open,moveFocus=false){if(!accessibilityToggle||!accessibilityPanel)return;accessibilityPanel.classList.toggle('open',open);accessibilityToggle.setAttribute('aria-expanded',open?'true':'false');accessibilityToggle.setAttribute('aria-label',open?'Erişilebilirlik seçeneklerini kapat':'Erişilebilirlik seçeneklerini aç');if(moveFocus){if(open)accessibilityPanel.focus({preventScroll:true});else accessibilityToggle.focus({preventScroll:true})}}
if(accessibilityToggle&&accessibilityPanel){
  accessibilityToggle.addEventListener('click',()=>{let willOpen=accessibilityToggle.getAttribute('aria-expanded')!=='true';if(willOpen&&document.getElementById('site-nav')?.classList.contains('is-open'))setNav(false,false);setAccessibilityPanel(willOpen,true)});
  accessibilityPanel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();setAccessibilityPanel(false,true)}});
  const a11yBox=document.querySelector('.a11y');
  if(a11yBox)a11yBox.addEventListener('focusout',e=>{if(!accessibilityPanel.classList.contains('open')||!e.relatedTarget)return;if(!a11yBox.contains(e.relatedTarget))setAccessibilityPanel(false,false)});
}
document.querySelectorAll('[data-font]').forEach(b=>b.addEventListener('click',()=>{storeSet(FONT_KEY,b.dataset.font);applyAccessibility();announce('Yazı boyutu güncellendi.')}));
document.getElementById('contrastToggle')?.addEventListener('click',()=>{let on=!document.body.classList.contains('high-contrast');storeSet(CONTRAST_KEY,on?'1':'0');applyAccessibility();announce(on?'Yüksek kontrast açık.':'Yüksek kontrast kapalı.')});
document.getElementById('darkToggle')?.addEventListener('click',()=>{let on=!document.body.classList.contains('dark-mode');storeSet(DARK_KEY,on?'1':'0');applyAccessibility();announce(on?'Koyu mod açık.':'Koyu mod kapalı.')});
document.getElementById('accessibilityReset')?.addEventListener('click',()=>{storeRemove(FONT_KEY);storeRemove(CONTRAST_KEY);storeRemove(DARK_KEY);applyAccessibility();announce('Erişilebilirlik ayarları sıfırlandı.')});
document.addEventListener('click',e=>{if(!accessibilityPanel||!accessibilityPanel.classList.contains('open'))return;let box=document.querySelector('.a11y');if(box&&!box.contains(e.target))setAccessibilityPanel(false,false)});

/* ---- Mobil menü --------------------------------------------------------- */
const navToggle=document.querySelector('.nav-toggle'),navToggleText=document.querySelector('.nav-toggle-text'),siteNav=document.getElementById('site-nav');
function setNav(open,moveFocus){if(!navToggle||!siteNav)return;navToggle.setAttribute('aria-expanded',open?'true':'false');navToggle.setAttribute('aria-label',open?'Menüyü kapat':'Menüyü aç');siteNav.classList.toggle('is-open',open);if(navToggleText)navToggleText.textContent=open?'Kapat':'Menü';if(open)setAccessibilityPanel(false,false);if(moveFocus)navToggle.focus({preventScroll:true})}
if(navToggle&&siteNav){
  navToggle.addEventListener('click',()=>setNav(navToggle.getAttribute('aria-expanded')!=='true',false));
  siteNav.addEventListener('click',e=>{if(e.target.closest('a'))setNav(false,false)});
  window.addEventListener('resize',()=>{if(window.innerWidth>1240)setNav(false,false)});
}
document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;if(accessibilityPanel&&accessibilityPanel.classList.contains('open')){e.preventDefault();setAccessibilityPanel(false,true);return}if(siteNav&&siteNav.classList.contains('is-open')){e.preventDefault();setNav(false,true)}});

/* ---- Ortak yardımcılar -------------------------------------------------- */
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function safeUrl(v){let u=String(v||'').trim();return /^https?:\/\//i.test(u)?u:''}
function newsDate(v){if(!v)return '';try{return new Date(v).toLocaleDateString('tr-TR',{day:'2-digit',month:'short',year:'numeric'})}catch(e){return ''}}
function newsTime(v){if(!v)return '';try{return new Date(v).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})}catch(e){return ''}}
function shortNewsSummary(v){let s=String(v||'').trim(),parts=s.match(/[^.!?]+[.!?]+/g);return parts?parts.slice(0,2).join(' ').trim():s}
function cleanSource(v){return String(v||'Kaynak belirtilmemiş').replace(/\s*\(yedek\)\s*/gi,'').trim()}

/* ---- Haberler ----------------------------------------------------------- */
function newsItemHTML(item,index){let title=esc(item.title),summary=esc(shortNewsSummary(item.summary)),source=esc(cleanSource(item.source)),dt=esc(newsDate(item.published_at));return '<li class="news-item"><h3><a href="#newsDetail" data-news-index="'+index+'">'+title+'</a></h3><p class="summary">'+summary+'</p><p class="meta"><time>'+dt+'</time><span class="meta-sep" aria-hidden="true">·</span><span>'+source+'</span></p></li>'}
function splitParagraphs(text){let s=String(text||'').trim();if(!s)return [];if(s.indexOf('\n')>=0)return s.split(/\n+/).map(x=>x.trim()).filter(Boolean);return [s]}
function buildDetailParagraphs(item){let out=[],lead=String(item.summary||'').trim(),detail=String(item.detail_summary||'').trim();if(lead)out=out.concat(splitParagraphs(lead));if(detail&&detail!==lead)out=out.concat(splitParagraphs(detail));if(!out.length)out=['Bu haber için ayrıntı metni bulunamadı.'];return out}
function renderLead(items){let item=items[0],link=document.getElementById('leadLink'),summary=document.getElementById('leadSummary'),date=document.getElementById('leadDate'),source=document.getElementById('leadSource');if(!link)return;if(!item){link.textContent='Yayınlanmış haber bulunamadı.';link.removeAttribute('href');if(summary)summary.textContent='Haber akışı şu anda boş görünüyor.';return}link.textContent=item.title||'';link.onclick=e=>{e.preventDefault();openNewsDetail(0)};if(summary)summary.textContent=shortNewsSummary(item.summary);if(date)date.textContent=newsDate(item.published_at);if(source)source.textContent=cleanSource(item.source);let breaking=document.getElementById('breakingLink'),bt=document.getElementById('breakingTime');if(breaking){breaking.textContent=item.title||'Güncel engelli haberleri';breaking.onclick=e=>{e.preventDefault();openNewsDetail(0)}}if(bt)bt.textContent=newsTime(item.published_at)}
function renderMostRead(items){let el=document.getElementById('mostRead');if(!el)return;if(!items.length){el.innerHTML='<li><span class="most-read-text">Haberler yükleniyor…</span></li>';return}el.innerHTML=items.slice(0,5).map((item,i)=>'<li><a href="#newsDetail" data-news-index="'+i+'"><span class="most-read-num" aria-hidden="true">'+String(i+1).padStart(2,'0')+'</span><span class="most-read-text">'+esc(item.title)+'</span></a></li>').join('')}
function bindNewsLinks(){document.querySelectorAll('a[data-news-index]').forEach(a=>{a.onclick=e=>{e.preventDefault();openNewsDetail(Number(a.dataset.newsIndex))}})}
function renderNews(){let items=(newsData&&newsData.items)||[],home=document.getElementById('homeNews');if(home){let homeItems=items.slice(1,7);home.innerHTML=homeItems.length?homeItems.map((it,i)=>newsItemHTML(it,i+1)).join(''):'<li class="news-empty">Şu anda yayınlanacak güncel engelli haberi bulunamadı.</li>'}renderLead(items);renderMostRead(items);let list=document.getElementById('newsList');if(list){list.innerHTML=items.slice(0,12).map((it,i)=>newsItemHTML(it,i)).join('')||'<li class="news-empty">Şu anda yayınlanacak güncel engelli haberi bulunamadı.</li>'}let updated=document.getElementById('newsUpdated');if(updated)updated.textContent=newsData.updated_at?'Son güncelleme: '+newsDate(newsData.updated_at):'Henüz güncelleme yok';bindNewsLinks()}
function openNewsDetail(index){let item=(newsData.items||[])[index];if(!item)return;let title=document.getElementById('newsDetailTitle'),date=document.getElementById('newsDetailDate'),source=document.getElementById('newsDetailSource'),body=document.getElementById('newsDetailSummary');if(title)title.textContent=item.title||'';if(date)date.textContent=newsDate(item.published_at);if(source)source.textContent=cleanSource(item.source);if(body){body.innerHTML='';buildDetailParagraphs(item).forEach(text=>{let p=document.createElement('p');p.textContent=text;body.appendChild(p)})}let u=safeUrl(item.url),link=document.getElementById('newsDetailLink');if(link){if(u){link.href=u;link.hidden=false}else{link.hidden=true;link.removeAttribute('href')}}let share=document.getElementById('newsDetailShare');if(share)share.onclick=()=>shareNews(index);openPage('newsDetail')}
async function shareNews(index){let item=(newsData.items||[])[index];if(!item)return;let url=location.origin+location.pathname+'?haber='+encodeURIComponent(item.title||'');let data={title:item.title||'Engelli.me',text:item.title||'Engelli.me',url};try{if(navigator.share){await navigator.share(data);return}if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(url);alert('Engelli.me haber bağlantısı kopyalandı.')}else{window.prompt('Engelli.me haber bağlantısını kopyalayın:',url)}}catch(e){if(e&&e.name!=='AbortError')console.error(e)}}
async function loadNews(){try{let r=await fetch('/api/news?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('news');newsData=await r.json();renderNews();let params=new URLSearchParams(location.search),sharedTitle=params.get('haber');if(sharedTitle){let sharedIndex=(newsData.items||[]).findIndex(x=>String(x.title||'')===sharedTitle);if(sharedIndex>=0){openPage('news');openNewsDetail(sharedIndex)}}}catch(e){let home=document.getElementById('homeNews'),list=document.getElementById('newsList');if(home)home.innerHTML='<li class="news-empty">Haberler şu anda alınamadı.</li>';if(list)list.innerHTML='<li class="news-empty">Haberler şu anda alınamadı.</li>'}}
/* ---- ÖTV muafiyetli araçlar -------------------------------------------- */
function tl(v){return Number(v||0).toLocaleString('tr-TR')+' ₺'}
function otvRateFor(v){let p=Number(v.price||0),b=(v.brand||'').toUpperCase(),m=(v.model||'').toUpperCase();if(!p)return null;let solve=(rules)=>{for(let [r,min,max] of rules){let base=p/1.20/(1+r);if(base>min&&(max==null||base<=max))return r}return null};if(b==='TOGG')return solve([[.25,0,1650000],[.55,1650000,null]]);if(b==='TOYOTA'&&m.includes('C-HR'))return solve([[.70,0,1250000],[.80,1250000,null]]);if(b==='TOYOTA'&&m.includes('COROLLA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]]);if(b==='FIAT'&&m.includes('ULYSSE'))return solve([[1.50,0,1650000],[1.70,1650000,null]]);if(b==='FIAT'&&m.includes('EGEA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]])||solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]]);return solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]])}
function exemptPrice(v){let r=otvRateFor(v);return r==null?null:Math.round(Number(v.price)/(1+r))}
const BRAND_LOGOS={fiat:'fiat.svg',renault:'renault.svg',togg:'togg.svg',toyota:'toyota.svg',hyundai:'hyundai.svg'};
function eligibleVehicles(){return (otvData.vehicles||[]).filter(v=>Number(v.price)>0)}
function filteredVehicles(){return eligibleVehicles().filter(v=>!activeBrand||v.brand===activeBrand)}
function allBrands(){return [...new Set(eligibleVehicles().map(v=>v.brand).filter(Boolean))]}
function brandLogo(brand,cls){let file=BRAND_LOGOS[String(brand||'').trim().toLowerCase()];return file?'<span class="'+(cls||'vehicle-logo')+'"><img src="/brand-logos/'+file+'" alt="" width="34" height="34" loading="lazy" decoding="async"></span>':''}
function brandGroups(rows){let order=[],map={};rows.forEach(v=>{let b=String(v.brand||'').trim()||'Diğer';if(!map[b]){map[b]={brand:b,rows:[]};order.push(b)}map[b].rows.push(v)});return order.map(b=>map[b])}
function localityText(rows){let nums=rows.map(v=>parseFloat(String(v.locality||'').replace(',','.'))).filter(n=>!isNaN(n));if(!nums.length)return 'Yerlilik verisi yok';let min=Math.min.apply(null,nums),max=Math.max.apply(null,nums),f=n=>String(n).replace('.',',');return 'Yerlilik %'+(min===max?f(min):f(min)+'–%'+f(max))}
function vehicleRowHTML(v){let ep=exemptPrice(v),u=safeUrl(v.source_url),source=esc(v.source_name||v.brand||''),checked=esc(v.checked_at||'—');return '<li class="vehicle-row"><div class="vehicle-main"><span class="vehicle-name">'+esc(v.model)+'</span><span class="vehicle-trim">'+esc(v.trim||'')+'</span><span class="vehicle-meta"><span class="vehicle-ok">Uygun</span> Yerlilik %'+esc(v.locality||'—')+'</span></div><div class="vehicle-price"><span class="price-label">Muaf fiyat</span><span class="price-value">'+(ep?tl(ep):'—')+'</span><span class="price-list">Liste '+tl(v.price)+'</span></div><p class="vehicle-source">'+(u?'Kaynak: <a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+source+' ↗</a>':'Kaynak: '+source)+' · Son kontrol: '+checked+'</p></li>'}
function brandGroupHTML(g){return '<section class="brand-group"><div class="brand-head">'+brandLogo(g.brand,'brand-mark')+'<div class="brand-title"><h3>'+esc(g.brand)+'</h3><p>'+g.rows.length+' paket · '+esc(localityText(g.rows))+'</p></div></div><ul class="vehicle-list">'+g.rows.map(vehicleRowHTML).join('')+'</ul></section>'}
function flatRowHTML(v){let ep=exemptPrice(v),u=safeUrl(v.source_url),source=esc(v.source_name||v.brand||'');return '<div class="flat-row"><div class="vehicle-main"><span class="vehicle-name">'+esc(v.brand||'')+' '+esc(v.model)+'</span><span class="vehicle-trim">'+esc(v.trim||'')+'</span><span class="vehicle-meta"><span class="vehicle-ok">Uygun</span> Yerlilik %'+esc(v.locality||'—')+'</span></div><div class="flat-price"><span class="price-label">Hesaplanmış ÖTV muaf fiyat</span><span class="price-value">'+(ep?tl(ep):'—')+'</span><span class="price-list">Liste '+tl(v.price)+'</span></div><p class="vehicle-source">'+(u?'Kaynak: <a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+source+' ↗</a>':'Kaynak: '+source)+' · Son kontrol: '+esc(v.checked_at||'—')+'</p></div>'}
function chipsHTML(){let rows=eligibleVehicles(),brands=allBrands(),out=('<button type="button" class="brand-chip" aria-pressed="'+(activeBrand?'false':'true')+'" data-brand="__all">Tümü <span class="chip-count">'+rows.length+'</span></button>');out+=brands.map(b=>'<button type="button" class="brand-chip" aria-pressed="'+(b===activeBrand?'true':'false')+'" data-brand="'+esc(b)+'">'+esc(b)+' <span class="chip-count">'+rows.filter(v=>v.brand===b).length+'</span></button>').join('');return out}
function bindChips(){document.querySelectorAll('#homeBrandChips .brand-chip, #otvChips .brand-chip').forEach(btn=>{btn.onclick=()=>setBrand(btn.dataset.brand)})}
function setBrand(b){activeBrand=(b==='__all'||activeBrand===b)?null:b;renderOTV()}
function renderOTV(){let all=eligibleVehicles(),limit=document.getElementById('otvLimit'),homeLimit=document.getElementById('homeOtvLimit'),pageLimit=document.getElementById('otvPageLimit');if(limit)limit.textContent=tl(otvData.limit);if(homeLimit)homeLimit.textContent=tl(otvData.limit);if(pageLimit)pageLimit.textContent=tl(otvData.limit);let count=document.getElementById('homeOtvCount');if(count)count.textContent=all.length;let brands=document.getElementById('homeOtvBrands');if(brands)brands.textContent=allBrands().length;let updated=document.getElementById('homeOtvUpdate');if(updated)updated.textContent=otvData.updated_at||'—';['homeBrandChips','otvChips'].forEach(id=>{let el=document.getElementById(id);if(el)el.innerHTML=chipsHTML()});let rows=filteredVehicles(),list=document.getElementById('homeBrandList');if(list){let groups=brandGroups(rows);list.innerHTML=groups.length?groups.map(brandGroupHTML).join(''):'<p class="news-empty">Bu markada uygun ve fiyatı doğrulanmış paket bulunamadı.</p>'}let flat=document.getElementById('otvList');if(flat)flat.innerHTML=rows.length?rows.map(flatRowHTML).join(''):'<p class="news-empty">Bu markada uygun ve fiyatı doğrulanmış paket bulunamadı.</p>';let summary=document.getElementById('otvSummaryText');if(summary)summary.textContent=rows.length+' uygun paket · Son fiyat kontrolü '+(otvData.updated_at||'—');let status=document.getElementById('vehicleFilterStatus');if(status)status.textContent=activeBrand?(activeBrand+' araçları gösteriliyor. '+rows.length+' paket.'):('Tüm markalar gösteriliyor. '+rows.length+' paket.');bindChips()}
function renderHome(){renderOTV()}
async function loadOTV(){try{let r=await fetch('/api/otv',{cache:'no-store'});if(!r.ok)throw Error('otv');otvData=await r.json();renderOTV()}catch(e){}}
function otvNeedsRefresh(){try{let s=String(otvData.updated_at||'').trim(),m=s.match(/^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2})$/);if(!m)return true;let dt=new Date(Number(m[3]),Number(m[2])-1,Number(m[1]),Number(m[4]),Number(m[5]));return Date.now()-dt.getTime()>=43200000}catch(e){return true}}
async function triggerOTVBackgroundRefresh(){if(!otvNeedsRefresh())return;try{await fetch('/api/otv/yenile',{method:'POST',keepalive:true});let r=await fetch('/api/otv?ts='+Date.now(),{cache:'no-store'});if(r.ok){otvData=await r.json();renderOTV()}}catch(e){}}
document.addEventListener('error',e=>{let img=e.target;if(img&&img.tagName==='IMG'&&img.closest('.brand-mark'))img.style.visibility='hidden'},true);
/* ---- Kira, Excel, PDF işlemleri ---------------------------------------- */
async function shareKira(){let url=location.origin+location.pathname+'?sayfa=kira';let data={title:'Engelli.me Kira Hesaplama',text:'Engelli.me Kira Hesaplama',url};try{if(navigator.share){await navigator.share(data);return}if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(url);alert('Kira hesaplama bağlantısı kopyalandı.')}else{window.prompt('Kira hesaplama bağlantısını kopyalayın:',url)}}catch(e){if(e&&e.name!=='AbortError')console.error(e)}}
document.getElementById('kiraShare')?.addEventListener('click',shareKira);
async function kiraHesapla(e){e.preventDefault();let b=document.getElementById('kira-btn'),res=document.getElementById('kira-result');if(!b||!res)return;b.disabled=true;b.textContent='Hesaplanıyor...';res.style.display='block';res.innerHTML='Güncel TÜFE kontrol ediliyor...';try{let body=new URLSearchParams();body.append('mevcut_kira',document.getElementById('mevcut-kira').value);body.append('yenileme_ayi',document.getElementById('yenileme-ayi').value);let r=await fetch('/kira-hesapla',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});let d=await r.json();if(!r.ok)throw Error(d.detail||'Hesaplama yapılamadı.');res.innerHTML='<div class="note">12 aylık ortalama TÜFE</div><div class="big">%'+d.oran+'</div><div class="note">Yeni kira</div><div class="big">'+d.yeni_kira+'</div><div class="note">'+d.durum+'</div>'}catch(x){res.innerHTML='<div class="note">'+x.message+'</div>'}finally{b.disabled=false;b.textContent='Hesapla'}}
function pdfSecildi(input){let el=document.getElementById('pdfFileName');if(!el)return;el.textContent=input.files&&input.files.length?'✓ PDF seçildi: '+input.files[0].name:'PDF seçilmedi — PDF dosyasını seç'}

/* ---- Sayfa yönlendirme -------------------------------------------------- */
let startPage=(function(){let h=(location.hash||'').replace('#',''),el=h?document.getElementById(h):null;if(el&&el.classList.contains('page'))return h;let p=new URLSearchParams(location.search);if(p.get('sayfa')==='kira')return 'kira';return 'home'})();
let pageStack=[startPage],forwardStack=[];
function updateNav(id){let h=document.getElementById('navHome'),n=document.getElementById('navNews');if(h){h.classList.toggle('is-active',id==='home');if(id==='home')h.setAttribute('aria-current','page');else h.removeAttribute('aria-current')}if(n){n.classList.toggle('is-active',id==='news');if(id==='news')n.setAttribute('aria-current','page');else n.removeAttribute('aria-current')}}
function syncBottomHome(id=document.querySelector('.page.on')?.id||'home'){let bh=document.getElementById('bottomHome');if(bh)bh.classList.toggle('show',id!=='home')}
function openPage(id,push=true){
  let target=document.getElementById(id);
  if(!target||!target.classList.contains('page'))return;
  if(push&&pageStack[pageStack.length-1]!==id){
    if(pageStack.length>1&&pageStack[pageStack.length-2]===id){history.back();return}
    history.pushState({...history.state,engellimePage:id},'',location.pathname+location.search+(id==='home'?'':'#'+id));
    pageStack.push(id);forwardStack=[];
  }
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));
  target.classList.add('on');syncBottomHome(id);updateNav(id);scrollTo(0,0);
  if(id==='otv')renderOTV();
}
window.addEventListener('popstate',e=>{
  let id=e.state&&typeof e.state.engellimePage==='string'&&document.getElementById(e.state.engellimePage)?e.state.engellimePage:'home';
  let prior=pageStack.lastIndexOf(id);
  if(prior>=0)pageStack=pageStack.slice(0,prior+1);else pageStack.push(id);
  forwardStack=[];
  openPage(id,false);
});
window.addEventListener('hashchange',()=>{let id=(location.hash||'').replace('#',''),el=document.getElementById(id),on=document.querySelector('.page.on');if(el&&el.classList.contains('page')&&(!on||on.id!==id))openPage(id,false)});
function goPreviousPage(){if(pageStack.length>1)history.back();else openPage('home',false)}
function goNextPage(){history.forward()}
function goPage(id){openPage(id);return false}
function goSection(id){let on=document.querySelector('.page.on');if(!on||on.id!=='home')openPage('home');let el=document.getElementById(id);if(el)el.scrollIntoView({behavior:'smooth',block:'start'});return false}

/* ---- Dokunmatik gezinme ------------------------------------------------- */
let touchStartX=0,touchStartY=0;
document.addEventListener('touchstart',e=>{
  if(e.touches.length!==1)return;
  touchStartX=e.touches[0].clientX;
  touchStartY=e.touches[0].clientY;
},{passive:true});
document.addEventListener('touchend',e=>{
  if(!e.changedTouches.length)return;
  let dx=e.changedTouches[0].clientX-touchStartX;
  let dy=e.changedTouches[0].clientY-touchStartY;
  // Safari's left-edge gesture belongs to browser history, not the in-page swipe handler.
  if(touchStartX<=24||touchStartX>=window.innerWidth-24)return;
  if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)*1.1){
    if(dx<0)goNextPage();else goPreviousPage();
  }
},{passive:true});

/* ---- Başlangıç ---------------------------------------------------------- */
if(!history.state||!Object.prototype.hasOwnProperty.call(history.state,'engellimePage'))history.replaceState({...history.state,engellimePage:startPage},'',location.href);
applyAccessibility();
renderNews();
renderOTV();
openPage(startPage,false);
/* Doğrudan bağlantıyla açılan iç sayfalarda tarayıcının parça (hash) kaydırması
   üst bölümü sticky başlığın altına kaydırabiliyor; sayfa açılışında başa dön. */
if(startPage&&startPage!=='home'){window.addEventListener('load',()=>scrollTo(0,0));scrollTo(0,0);}
loadOTV();
loadNews();
setTimeout(triggerOTVBackgroundRefresh,800);
</script>
</body>
</html>'''


# CSP satır içi olay öznitelikleri statiktir; hash'ler istek başına değil,
# modül yüklenirken bir kez hesaplanır (her istekte ~540 KB taramayı önler).
_CSP_SCRIPT_ATTR_HASHES, _CSP_STYLE_ATTR_HASHES = csp_attr_hashes(
    "\n".join((HOME_HTML, CHAT_HTML, KVKK_HTML, _ek2_html("arac1"), _ek2_html("arac2"), _ek2_html("arac3")))
)


if __name__ == "__main__":
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=int(os.environ.get("PORT",8000)), reload=False)
