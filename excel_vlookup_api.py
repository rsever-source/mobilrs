import asyncio, base64, hashlib, html as html_lib, io, json, os, re, secrets, time, uuid, zipfile
from datetime import date
from urllib.parse import urlparse

import pandas as pd, pdfplumber, uvicorn
from fastapi import BackgroundTasks, FastAPI, UploadFile, File, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from starlette.background import BackgroundTask

from tufe_service import get_current_tufe, save_cache
from otv_service import get_otv_data, refresh_otv_data, _load as load_otv_cache

app = FastAPI(title="Rdv Asistan", docs_url=None, redoc_url=None, openapi_url=None)

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
    response = await call_next(request)
    def csp_hash(value):
        digest = hashlib.sha256(html_lib.unescape(value).encode("utf-8")).digest()
        return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"
    csp_sources = "\n".join((HOME_HTML, CHAT_HTML, KVKK_HTML))
    script_attr_hashes = sorted({csp_hash(value) for value in re.findall(r'\bon(?:click|submit|change|input|load)\s*=\s*"([^"]*)"', csp_sources, re.IGNORECASE)})
    style_attr_hashes = sorted({csp_hash(value) for value in re.findall(r'\bstyle\s*=\s*"([^"]*)"', csp_sources, re.IGNORECASE)})
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"script-src-attr 'unsafe-hashes' {' '.join(script_attr_hashes)}; "
        f"style-src 'self' 'nonce-{nonce}'; "
        f"style-src-attr 'unsafe-hashes' {' '.join(style_attr_hashes)}; "
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
    elif path == "/kvkk":
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        response.headers["Cache-Control"] = "no-store"
    return response



OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 2000
MAX_ARCHIVE_UNCOMPRESSED = 100 * 1024 * 1024
MAX_EXCEL_ROWS = 200_000
MAX_PDF_PAGES = 50
MAX_PDF_ROWS = 100_000
FILE_PROCESS_TIMEOUT = 90
RATE_LIMIT_WINDOW = 60
UPLOAD_RATE_LIMIT = 6
REFRESH_RATE_LIMIT_WINDOW = 300
REFRESH_RATE_LIMIT = 1
_RATE_LIMITS = {}
_RATE_LIMIT_LOCK = asyncio.Lock()
_REFRESH_LOCK = asyncio.Lock()
MONTH_NAMES = {1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}


async def enforce_rate_limit(request: Request, bucket: str, limit: int, window: int):
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client_ip}"
    now = time.monotonic()
    async with _RATE_LIMIT_LOCK:
        cutoff = now - window
        for k in list(_RATE_LIMITS):
            if not _RATE_LIMITS[k] or _RATE_LIMITS[k][-1] <= cutoff:
                _RATE_LIMITS.pop(k, None)
        hits = [t for t in _RATE_LIMITS.get(key, []) if t > cutoff]
        if len(hits) >= limit:
            retry_after = max(1, int(window - (now - hits[0])) + 1)
            raise HTTPException(429, "Çok fazla istek. Lütfen biraz sonra tekrar deneyin.", headers={"Retry-After": str(retry_after)})
        hits.append(now)
        _RATE_LIMITS[key] = hits
        if len(_RATE_LIMITS) > 4096:
            oldest = min(_RATE_LIMITS, key=lambda k: _RATE_LIMITS[k][-1])
            _RATE_LIMITS.pop(oldest, None)


def unique_output_path(ext):
    return os.path.join(OUTPUT_DIR, f"rdv_{uuid.uuid4().hex}.{ext}")


def delete_file(path):
    try:
        if os.path.exists(path): os.remove(path)
    except Exception: pass


async def read_upload_limited(upload, max_size=MAX_FILE_SIZE):
    data = await upload.read()
    if len(data) > max_size:
        raise HTTPException(413, f"{upload.filename or 'Dosya'} çok büyük. Maksimum {max_size//(1024*1024)} MB.")
    return data


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

@app.get("/api/news")
async def api_news():
    try:
        with open("news.json", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"updated_at": None, "items": []}
    items = []
    for item in data.get("items", [])[:10]:
        url = str(item.get("url", "")).strip()
        if not url.startswith(("https://", "http://")):
            continue
        items.append({
            "id": str(item.get("id", "")),
            "title": str(item.get("title", ""))[:180],
            "summary": str(item.get("summary", ""))[:900],
            "category": str(item.get("category", "Gündem"))[:50],
            "source": str(item.get("source", ""))[:100],
            "url": url,
            "published_at": item.get("published_at"),
        })
    return JSONResponse({"updated_at": data.get("updated_at"), "items": items})

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if request.headers.get("host", "").split(":")[0].lower() == "chat.engelli.me":
        return HTMLResponse(CHAT_HTML.replace("<style>", f'<style nonce="{request.state.csp_nonce}">'))
    initial = load_otv_cache() or {}
    initial_json = __import__("json").dumps(initial, ensure_ascii=False).replace("</", "<\\/")
    try:
        with open("news.json", encoding="utf-8") as f:
            initial_news = json.load(f)
    except Exception:
        initial_news = {"updated_at": None, "items": []}
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
    app.add_api_route("/" + _n, _icon_route(_n), methods=["GET"], include_in_schema=False)


@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    return HTMLResponse("User-agent: *\nAllow: /\nSitemap: https://engelli.me/sitemap.xml\n", media_type="text/plain")


@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml():
    return HTMLResponse("<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>https://engelli.me/</loc></url></urlset>", media_type="application/xml")


@app.get("/.well-known/security.txt", response_class=Response)
async def security_txt():
    return Response("Contact: https://engelli.me/\nExpires: 2027-10-01T00:00:00.000Z\nPreferred-Languages: tr, en\nCanonical: https://engelli.me/.well-known/security.txt\n", media_type="text/plain")


@app.get("/kvkk", response_class=HTMLResponse)
async def kvkk_page(request: Request):
    return HTMLResponse(KVKK_HTML.replace("<style>", f'<style nonce="{request.state.csp_nonce}">'))




@app.post("/excel-islem")
async def excel_motor(request: Request, komut:str=Form(...), file1:UploadFile=File(...), file2:UploadFile=File(...)):
    await enforce_rate_limit(request, "upload", UPLOAD_RATE_LIMIT, RATE_LIMIT_WINDOW)
    out=None
    try:
        if not check_extension(file1.filename,(".xlsx",".xls")) or not check_extension(file2.filename,(".xlsx",".xls")): raise HTTPException(400,"Geçerli Excel dosyaları seç.")
        d1=await read_upload_limited(file1); d2=await read_upload_limited(file2); validate_file_signature(d1,file1.filename,file1.content_type); validate_file_signature(d2,file2.filename,file2.content_type)
        out=await asyncio.wait_for(asyncio.to_thread(build_excel_result,d1,d2,komut), timeout=FILE_PROCESS_TIMEOUT)
        return FileResponse(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="excel_sonuc.xlsx",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except asyncio.TimeoutError:
        if out: delete_file(out)
        raise HTTPException(504,"Excel işlemi zaman sınırını aştı.")
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,"Excel işlemi sırasında beklenmeyen bir hata oluştu.")


@app.post("/pdf-excel-islem")
async def pdf_excel_motor(request: Request, pdf_file:UploadFile=File(...)):
    await enforce_rate_limit(request, "upload", UPLOAD_RATE_LIMIT, RATE_LIMIT_WINDOW)
    out=None
    try:
        if not check_extension(pdf_file.filename,(".pdf",)): raise HTTPException(400,"Geçerli bir PDF dosyası seç.")
        pdf_data=await read_upload_limited(pdf_file); validate_file_signature(pdf_data,pdf_file.filename,pdf_file.content_type)
        out=await asyncio.wait_for(asyncio.to_thread(build_pdf_result,pdf_data), timeout=FILE_PROCESS_TIMEOUT)
        return FileResponse(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="pdf_to_excel_sonuc.xlsx",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except asyncio.TimeoutError:
        if out: delete_file(out)
        raise HTTPException(504,"PDF işlemi zaman sınırını aştı.")
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,"PDF → Excel işlemi sırasında beklenmeyen bir hata oluştu.")


KVKK_HTML = r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KVKK Aydınlatma Metni | Engelli.me</title><style>body{margin:0;background:#f4f6f9;color:#182234;font-family:Inter,Aptos,"Segoe UI",system-ui,-apple-system,sans-serif}.card{max-width:820px;margin:32px auto;padding:28px;background:#fff;border:1px solid #e4e8ef;border-radius:18px;box-shadow:0 10px 30px rgba(20,32,55,.06)}h1{font-size:25px;margin:0 0 18px}h2{font-size:17px;margin:22px 0 8px}p,li{font-size:14px;line-height:1.65}.muted{color:#697386;font-size:12px}@media(max-width:640px){body{background:#fff}.card{margin:0;padding:20px;border:0;border-radius:0;box-shadow:none}h1{font-size:22px}}</style></head><body><main class="card"><h1>KVKK Aydınlatma Metni</h1><p class="muted">Son güncelleme: 28 Eylül 2026</p><h2>1. Veri Sorumlusu</h2><p>Bu hizmet kapsamında işlenen kişisel veriler bakımından veri sorumlusu, Engelli.me hizmetinin işletmecisidir.</p><h2>2. Kapsam</h2><p>Bu Aydınlatma Metni, Engelli.me üzerinde sunulan Excel işlemleri, PDF → Excel hizmeti ve kullanıcı sohbetine ilişkin kişisel veri işleme faaliyetleri hakkında bilgilendirme amacıyla hazırlanmıştır.</p><h2>3. Excel ve PDF → Excel Hizmetleri</h2><p>Excel ve PDF → Excel araçlarına yüklediğiniz dosyalar, yalnızca talep ettiğiniz dosya işlemini gerçekleştirmek ve sonucu size sunmak amacıyla teknik olarak işlenir. Dosya içeriğinde kişisel veri bulunması halinde bu veriler de işlem sırasında teknik olarak işlenebilir.</p><h2>4. Dosyaların Saklanması</h2><p>Yüklediğiniz Excel ve PDF dosyaları kalıcı olarak saklanmak üzere tasarlanmamıştır. Dosya içeriği işlem sırasında işlenir. Oluşturulan sonuç dosyası geçici olarak oluşturulur ve işlem sonrasında silinir.</p><h2>5. Kullanıcı Sohbeti</h2><p>Engelli.me kullanıcı sohbeti, Klaklak altyapısı kullanılarak sunulmaktadır. Sohbet alanında kullanıcıların seçtiği takma ad (nickname), IP adresi ve mesaj içeriği gibi veriler Klaklak'ın hizmetini sunması ve kötüye kullanımın önlenmesi amacıyla işlenebilir. Engelli.me uygulaması sohbet mesajlarını kendi sunucularında ayrıca arşivlemek veya kalıcı olarak saklamak üzere tasarlanmamıştır.</p><p>Klaklak'ın geçici sohbet yapısında aktif odada son 50 mesaja kadar içerik gösterilebilir; oda, kimsenin bulunmadığı sürenin ardından temizlenir ve sohbet geçmişi arşivlenmez. Kötüye kullanımın önlenmesine yönelik zaman, IP adresi ve takma ad bilgilerini içeren kayıtlar Klaklak'ın kendi hizmet koşulları ve gizlilik uygulamaları kapsamında daha farklı sürelerde tutulabilir.</p><p>Sohbet hizmeti uçtan uca şifreli değildir. Bu nedenle sohbet alanına telefon numarası, adres, kimlik bilgisi, sağlık bilgisi veya başka kişisel ya da özel nitelikli kişisel verileri yazmamanız önemle tavsiye edilir.</p><h2>6. Kişisel Verilerin İşlenme Amaçları ve Hukuki Sebepler</h2><p>Kişisel veriler; sunulan hizmetlerin çalıştırılması, kullanıcı tarafından talep edilen işlemlerin gerçekleştirilmesi, teknik güvenliğin sağlanması, kötüye kullanımın ve güvenlik olaylarının önlenmesi ve ilgili mevzuattan doğan yükümlülüklerin yerine getirilmesi amaçlarıyla, 6698 sayılı Kişisel Verilerin Korunması Kanunu'nun 5 ve 6. maddelerinde düzenlenen ilgili veri işleme şartları çerçevesinde işlenebilir.</p><h2>7. Veri Aktarımı ve Üçüncü Taraf Hizmet Sağlayıcılar</h2><p>Hizmetlerin sunulabilmesi için kişisel veriler, kullanılan teknik altyapı ve hizmet sağlayıcılarına, yalnızca ilgili hizmetin gerektirdiği ölçüde aktarılabilir veya bu sağlayıcılar tarafından işlenebilir. Kullanıcı sohbetinde Klaklak üçüncü taraf hizmet sağlayıcısı olarak görev yapmaktadır. Klaklak tarafından işlenen veriler ayrıca Klaklak'ın kendi gizlilik ve hizmet koşullarına tabidir.</p><h2>8. Kullanıcıların Dikkatine</h2><p>Hizmetleri kullanırken mümkün olduğunca kişisel veri içermeyen dosyalar yüklemeniz ve sohbet alanında kişisel veri paylaşmamanız önerilir. Özellikle özel nitelikli kişisel verileri içeren belgeleri yalnızca gerekli olduğunda yükleyiniz.</p><h2>9. Güvenlik</h2><p>Kişisel verilerin hukuka aykırı işlenmesini veya erişilmesini önlemek ve güvenliğini sağlamak amacıyla hizmetin teknik yapısına uygun teknik ve idari tedbirler uygulanır.</p><h2>10. Saklama Süreleri</h2><p>Kişisel veriler, işlendikleri amaç için gerekli olan süre boyunca ve ilgili mevzuatta öngörülen saklama süreleri kadar muhafaza edilir. Dosya işleme sonuçları geçici olarak oluşturulur ve işlem sonrasında silinir. Sohbet içerikleri ve Klaklak tarafından tutulan teknik/kötüye kullanım kayıtları bakımından Klaklak'ın kendi saklama politikaları geçerlidir.</p><h2>11. İlgili Kişinin Hakları</h2><p>KVKK'nın 11. maddesi kapsamında kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse buna ilişkin bilgi talep etme, işlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme, yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme, eksik veya yanlış işlenmişse düzeltilmesini isteme, kanunda öngörülen şartlar çerçevesinde silinmesini veya yok edilmesini isteme ve diğer kanuni haklarınızı kullanma hakkınız bulunmaktadır.</p><h2>12. İletişim ve Başvurular</h2><p>KVKK kapsamındaki taleplerinizi hizmet işletmecisine iletebilirsiniz. Başvurular ilgili mevzuatta öngörülen usul ve esaslara göre değerlendirilir. Veri sorumlusu iletişim bilgilerinin güncellenmesi halinde bu metin de güncellenecektir.</p><p class="muted">Bu metin, Engelli.me üzerinde sunulan hizmetlerin kapsamındaki kişisel veri işleme faaliyetleri hakkında bilgilendirme amacı taşır. Klaklak'ın kendi hizmeti kapsamında gerçekleştirdiği veri işleme faaliyetleri bakımından Klaklak'ın güncel gizlilik politikası ayrıca dikkate alınmalıdır.</p></main></body></html>'''

HOME_HTML = r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Engelli.me ÖTV Muaf Araçlar ve Engelli Haberleri</title><meta name="description" content="Güncel ÖTV muaf araç liste fiyatları ve hesaplanmış fiyatlar. TÜFE ile kira hesaplama, Excel ve PDF → Excel araçları."><meta name="robots" content="index,follow"><link rel="canonical" href="https://engelli.me/"><meta property="og:title" content="ÖTV Muaf Araçlar ve Kira Hesaplama | Engelli.me"><meta property="og:description" content="Güncel ÖTV muaf araç liste fiyatları ve hesaplanmış fiyatlar."><meta property="og:url" content="https://engelli.me/"><meta property="og:type" content="website"><link rel="icon" type="image/png" href="/favicon.png?v=1"><link rel="apple-touch-icon" href="/apple-touch-icon.png?v=1">
<style>
:root{--ink:#182234;--muted:#596579;--blue:#0b57e3;--blue-dark:#0844b5;--line:#d6dde8;--soft:#f5f7fa;--soft-blue:#edf4ff;--white:#fff;--green:#0b6b3a;--shadow:0 16px 45px rgba(20,32,55,.08);--base-scale:1}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{touch-action:pan-y;margin:0;background:#f4f6f9;color:var(--ink);font-family:Inter,Aptos,"Segoe UI",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased;font-size:calc(16px * var(--base-scale))}
button,input,select,textarea{font:inherit}.app{width:min(1180px,calc(100% - 48px));margin:28px auto 48px;background:var(--white);border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow);overflow:hidden}
.header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:22px 30px;border-bottom:1px solid var(--line);background:var(--white)}.brand{font-size:24px;font-weight:850;letter-spacing:-.6px}.brand span{color:var(--blue)}.header-note{font-size:12px;color:var(--muted)}.chat-nav{color:var(--blue);text-decoration:none;font-size:13px;font-weight:850;border:1px solid #b8cbed;border-radius:999px;padding:8px 12px;background:var(--soft-blue)}.chat-nav:hover{background:#dce9ff}
.skip-link{position:absolute;left:-9999px;top:8px;z-index:100;padding:10px 14px;background:var(--ink);color:#fff;border-radius:8px}.skip-link:focus{left:8px}.accessibility-tools{display:flex;align-items:center;justify-content:flex-end}.accessibility-toggle{display:none;border:1px solid #b8cbed;border-radius:8px;padding:7px 11px;background:var(--soft-blue);color:var(--blue);font-size:12px;font-weight:800;cursor:pointer}.accessibility-panel{display:flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:flex-end}.accessibility-panel-head{display:flex;align-items:center;gap:7px}.accessibility-options{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.accessibility-panel button{border:1px solid #b8cbed;border-radius:8px;padding:6px 9px;background:var(--soft-blue);color:var(--blue);font-size:12px;font-weight:800;cursor:pointer}.accessibility-panel button[aria-pressed="true"]{background:var(--blue);color:#fff}.accessibility-panel .tool-label{font-size:11px;font-weight:800;color:var(--muted)}.accessibility-reset{font-size:11px!important;padding:5px 8px!important;background:transparent!important;color:var(--muted)!important}.accessibility-reset:hover{text-decoration:underline}
.high-contrast{--ink:#000;--muted:#000;--blue:#0000ee;--blue-dark:#000080;--line:#000;--soft:#fff;--soft-blue:#fff;--white:#fff;background:#fff!important}.high-contrast .app,.high-contrast .panel,.high-contrast .news-card,.high-contrast .vehicle-card,.high-contrast .tool,.high-contrast .stat,.high-contrast .hero,.high-contrast .news-section{border:2px solid #000;background:#fff;color:#000}.high-contrast .news-summary,.high-contrast .news-source,.high-contrast .news-date,.high-contrast .hero p,.high-contrast .section-head p,.high-contrast .tool small,.high-contrast .stat small,.high-contrast .header-note,.high-contrast .kvkk-note,.high-contrast .note{color:#000}.high-contrast a,.high-contrast .news-link{color:#0000ee!important;text-decoration:underline}.high-contrast button{border:2px solid #000;background:#000;color:#fff}.high-contrast .accessibility-tools button{background:#fff;color:#000}.high-contrast .accessibility-tools button[aria-pressed="true"]{background:#000;color:#fff}.high-contrast .primary,.high-contrast .btn{background:#000;color:#fff}.high-contrast.dark-mode{--ink:#000;--muted:#000;--blue:#0000ee;--white:#fff;background:#fff!important}.dark-mode{--ink:#f2f5fa;--muted:#c1ccda;--blue:#79a9ff;--blue-dark:#a7c5ff;--line:#526174;--soft:#1b2430;--soft-blue:#1c355d;--white:#111923;--shadow:0 16px 45px rgba(0,0,0,.35);background:#0b1118!important}.dark-mode .header,.dark-mode .panel,.dark-mode .news-card,.dark-mode .vehicle-card,.dark-mode .tool,.dark-mode .stat,.dark-mode .input,.dark-mode select,.dark-mode textarea{background:var(--white);color:var(--ink)}.dark-mode .hero,.dark-mode .news-section{background:#172231}.dark-mode .news-card h3 a{color:var(--ink)}
body.font-large .app{zoom:1.12}body.font-xlarge .app{zoom:1.25}body.font-large .accessibility-tools,body.font-xlarge .accessibility-tools{zoom:.9}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,[tabindex]:focus-visible{outline:3px solid #ffbf47;outline-offset:3px}
.page{display:none}.page.on{display:block}.home{padding:30px}.hero{padding:20px 22px;border:1px solid #dce6f6;border-radius:20px;background:linear-gradient(135deg,#f8fbff,#edf4ff);box-shadow:inset 4px 0 0 var(--blue),0 8px 22px rgba(11,87,227,.10)}.eyebrow{font-size:12px;font-weight:800;color:var(--blue);letter-spacing:.08em;text-transform:uppercase;margin-bottom:9px}.hero h1{margin:0;font-size:28px;line-height:1.1;letter-spacing:-.9px}.hero p{margin:7px 0 0;max-width:680px;color:var(--muted);font-size:13px;line-height:1.45}.hero-stats{display:flex;gap:8px;margin-top:15px}.stat{background:#fff;border:1px solid #dfe7f3;border-radius:14px;padding:9px 13px;min-width:125px}.stat small{display:block;color:var(--muted);font-size:11px}.stat b{display:block;margin-top:2px;font-size:18px;letter-spacing:-.3px}.section{margin-top:18px}.section-head{display:flex;align-items:end;justify-content:space-between;gap:15px;margin-bottom:12px}.section-head h2{margin:0;font-size:21px;letter-spacing:-.4px}.section-head p{margin:0;color:var(--muted);font-size:12px}
.news-section{margin-top:26px;padding:20px;border:1px solid #e1e7f0;border-radius:22px;background:linear-gradient(145deg,#fbfcff,#f5f8fc)}
.news-section .section-head{margin-bottom:14px}.news-kicker{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.news-kicker-dot{width:8px;height:8px;border-radius:50%;background:#e04b59;box-shadow:0 0 0 5px #fdecef}
.news-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.news-card{display:flex;flex-direction:column;min-width:0;border:1px solid #e0e6ef;border-radius:17px;background:#fff;padding:16px;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}
.news-card:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(20,32,55,.07);border-color:#d2dbe9}
.news-card .news-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}
.news-tag{display:inline-flex;align-items:center;border-radius:999px;padding:5px 9px;background:#edf4ff;color:var(--blue);font-size:10px;font-weight:850;white-space:nowrap}
.news-date{font-size:10px;color:var(--muted);white-space:nowrap}
.news-card h3{margin:0;font-size:16px;line-height:1.3;letter-spacing:-.2px}
.news-card h3 a{color:var(--ink);text-decoration:none}.news-card h3 a:hover{text-decoration:underline}.news-summary-link{display:block;color:#596579;text-decoration:none}.news-summary-link:hover{text-decoration:underline}
.news-summary{margin:9px 0 13px;color:#596579;font-size:12px;line-height:1.55;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}
 .news-card.clickable{cursor:pointer}.news-card.clickable:active{transform:scale(.99)}
 .news-detail-title{margin:0 0 10px;font-size:25px;line-height:1.25}
 .news-detail-summary{margin:0;color:#4f5d72;font-size:15px;line-height:1.75}
 .news-detail-source{margin-top:18px;padding-top:14px;border-top:1px solid #edf0f4;font-size:12px;color:var(--muted)}
 .news-detail-source a{color:var(--blue);font-weight:800;text-decoration:none}
.news-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:auto;padding-top:11px;border-top:1px solid #edf0f4}
.news-source{min-width:0;color:var(--muted);font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.news-source b{color:#465268}.news-link{flex:0 0 auto;color:var(--blue);font-size:11px;font-weight:850;text-decoration:none}.news-link:hover{text-decoration:underline}.news-share{display:block;box-sizing:border-box;margin:10px 0 0;width:100%;min-height:34px;border:1px solid #b8cbed;border-radius:10px;padding:7px 10px;background:var(--soft-blue);color:var(--blue);font-size:11px;font-weight:800;line-height:18px;text-align:center;cursor:pointer;appearance:none}.news-share:hover{background:#dce9ff}.news-share{margin-top:10px;width:100%;border:1px solid #b8cbed;border-radius:10px;padding:7px 10px;background:var(--soft-blue);color:var(--blue);font-size:11px;font-weight:800;cursor:pointer}.news-share:hover{background:#dce9ff}
.news-empty{grid-column:1/-1;border:1px dashed #d7dee9;border-radius:15px;padding:18px;text-align:center;color:var(--muted);font-size:12px;background:#fff}
.news-archive-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;min-height:22px}.news-refresh{font-size:10px;color:var(--muted)}
.news-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media(max-width:640px){.news-section{padding:15px;border-radius:19px}.news-grid,.news-list{grid-template-columns:1fr}.news-card{padding:15px}.news-card h3{font-size:15px}.news-summary{font-size:12px}.news-date{display:none}}

.vehicle-grid{display:grid;grid-template-columns:repeat(2,minmax(0,500px));justify-content:center;gap:16px}.vehicle-card{border:1px solid var(--line);border-radius:14px;background:#fff;padding:18px 20px;display:flex;align-items:center;justify-content:space-between;gap:10px;min-width:0}.vehicle-card .vehicle-info{min-width:0}.vehicle-card .brandline{font-size:10px;color:var(--muted);font-weight:750;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vehicle-card h3{margin:4px 0 3px;font-size:18px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vehicle-card .trim{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vehicle-card .price-line{flex:0 0 auto;text-align:right}.vehicle-card .price-label{font-size:10px;color:var(--muted);white-space:nowrap}.vehicle-card .price{font-size:18px;font-weight:850;white-space:nowrap}.vehicle-card .arrow{display:none}
.more{display:flex;justify-content:center;margin-top:22px}.primary,.secondary{border:0;border-radius:12px;padding:12px 17px;font-weight:800;cursor:pointer}.primary{background:var(--blue);color:#fff}.primary:hover{background:var(--blue-dark)}.secondary{background:var(--soft-blue);color:var(--blue)}
.tools{margin-top:30px}.tool-grid{display:none;grid-template-columns:repeat(3,1fr);gap:12px}.tools.open .tool-grid{display:grid}.tool{display:flex;align-items:center;gap:13px;border:1px solid var(--line);border-radius:16px;padding:17px;background:#fff;cursor:pointer}.tool-icon{width:42px;height:42px;flex:0 0 42px;border-radius:12px;background:var(--soft-blue);display:grid;place-items:center;color:var(--blue);font-weight:900}.tool b{font-size:14px}.tool small{display:block;margin-top:3px;color:var(--muted);font-size:11px}
.footer{padding:20px 30px;border-top:1px solid var(--line);color:var(--muted);font-size:11px;text-align:center}.kvkk-note{margin-top:10px;font-size:11px;line-height:1.5;color:var(--muted)}.kvkk-note a{color:var(--blue);font-weight:700;text-decoration:none}.kvkk-note a:hover{text-decoration:underline}
.page-wrap{padding:30px}.page-head{display:flex;align-items:center;gap:10px;margin-bottom:18px}.back{border:1px solid var(--line);background:#fff;border-radius:11px;width:40px;height:40px;cursor:pointer;font-size:24px}.page-head h1,.page-head h2{margin:0;font-size:28px;letter-spacing:-.7px}.panel{border:1px solid var(--line);border-radius:18px;background:#fff;padding:20px;margin-bottom:14px}.summary{background:var(--soft-blue);border-color:#d9e6fb}.chips{display:flex;gap:8px;overflow:auto;padding:2px 1px 8px}.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 14px;white-space:nowrap;font-size:12px;font-weight:750;cursor:pointer}.chip.on{background:var(--blue);border-color:var(--blue);color:#fff}.list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.row{border:1px solid var(--line);border-radius:17px;padding:17px;background:#fff}.rowtop{display:flex;justify-content:space-between;gap:15px}.row .tag{background:#e8f7ef;color:var(--green);border-radius:999px;padding:5px 9px;height:max-content;font-size:10px;font-weight:800}.name{font-size:17px;font-weight:850}.meta{font-size:12px;color:var(--muted);margin-top:4px}.price{margin-top:14px;font-size:11px;color:var(--muted)}.price b{display:block;color:var(--ink);font-size:18px;margin-top:2px}.note{font-size:11px;color:var(--muted);line-height:1.5;margin-top:9px}.field{display:block;margin:12px 0 6px;font-size:12px;font-weight:800}.input,select,textarea{width:100%;border:1px solid #d9dee8;border-radius:12px;padding:12px 13px;background:#fff}.btn{width:100%;border:0;border-radius:12px;padding:13px;background:var(--blue);color:#fff;font-weight:800;cursor:pointer;margin-top:12px}.green{background:var(--green)}.result{display:none;margin-top:12px;border-radius:15px;background:var(--soft-blue);padding:16px}.result .big{font-size:27px;font-weight:900;color:var(--blue);text-align:center;margin:7px 0}.filebox{position:relative;border:2px dashed #d5dbe5;border-radius:14px;padding:18px;text-align:center;margin:10px 0;color:var(--muted);font-size:12px}.filebox input{position:absolute;inset:0;opacity:0;width:100%;height:100%}.bottom-home{display:none!important}
@media(min-width:901px){.app{width:min(1380px,calc(100% - 64px));margin-top:32px}.home,.page-wrap{padding:38px}.hero{padding:26px 28px}.hero h1{font-size:32px}.hero p{font-size:14px;max-width:820px}.section{margin-top:28px}.section-head h2{font-size:23px}.news-section{padding:24px;margin-top:30px}.news-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.news-card{padding:19px}.news-card h3{font-size:18px}.news-summary{font-size:13px;line-height:1.6;-webkit-line-clamp:3}.news-source{font-size:11px}.news-link{font-size:12px}.vehicle-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;justify-content:stretch}.vehicle-card{padding:20px 22px}.vehicle-card h3{font-size:19px}.vehicle-card .trim{font-size:13px}.vehicle-card .price{font-size:19px}.tool-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.tool{padding:19px}.tool b{font-size:15px}.tool small{font-size:12px}.page-head h1,.page-head h2{font-size:30px}.list{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.row{padding:19px}.name{font-size:18px}.panel{padding:24px}}
@media(max-width:900px){.vehicle-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.tool-grid{grid-template-columns:1fr 1fr}}
@media(max-width:640px){body{background:#fff}.app{width:100%;margin:0;border:0;border-radius:0;box-shadow:none;min-height:100vh}.header{padding:17px 16px}.brand{font-size:22px}.header-note{font-size:10px}.home,.page-wrap{padding:18px 16px 80px}.hero{padding:17px;border-radius:18px}.hero h1{font-size:23px}.hero p{font-size:12px}.hero-stats{grid-template-columns:1fr 1fr;gap:8px}.stat:last-child{grid-column:1/-1;position:static;width:auto;min-width:0;padding:15px 17px}.stat:last-child small{font-size:11px}.stat:last-child b{font-size:20px;margin-top:4px}.stat b{font-size:20px}.section{margin-top:24px}.section-head h2{font-size:19px}.vehicle-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.vehicle-card{padding:15px 13px}.vehicle-card h3{font-size:15px}.vehicle-card .price-label{font-size:9px}.vehicle-card .price{font-size:14px}.tool-grid{grid-template-columns:1fr}.tool{padding:15px}.page-head h1,.page-head h2{font-size:23px}.list{grid-template-columns:1fr}.row{padding:15px}.accessibility-tools{width:auto;flex-direction:column;align-items:flex-end}.accessibility-toggle{display:block;width:auto;text-align:center;padding:6px 10px;border-radius:999px;font-size:11px}.accessibility-panel{display:none;width:min(320px,100%);margin-top:6px;padding:8px;border:1px solid var(--line);border-radius:12px;background:var(--soft);box-shadow:0 6px 16px rgba(20,32,55,.07)}.accessibility-panel.open{display:block}.accessibility-panel-head{justify-content:space-between;margin-bottom:6px}.accessibility-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.accessibility-options button{min-height:36px;padding:5px 6px}.accessibility-options button[data-font]{min-width:0}.bottom-home{display:block;position:fixed;left:50%;bottom:10px;transform:translateX(-50%);border:1px solid var(--line);background:#fff;color:var(--blue);border-radius:999px;padding:7px 12px;font-size:11px;font-weight:850;opacity:.82;box-shadow:0 5px 16px rgba(0,0,0,.10);z-index:20;transition:transform .2s ease,opacity .2s ease,padding .2s ease,font-size .2s ease}.bottom-home.compact{transform:translateX(-50%) scale(.86);opacity:.62;padding:5px 9px;font-size:10px}}
.brand{display:flex;align-items:center}.brand-logo{width:48px;height:48px;margin-left:10px;flex:0 0 auto}@media(max-width:640px){.brand-logo{width:42px;height:42px;margin-left:8px}}</style></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a><main class="app">
<header class="header"><div class="brand">Engelli<span>.me</span><img class="brand-logo" src="/logo.png?v=1" alt="" width="38" height="38" decoding="async"></div><div class="accessibility-tools"><button type="button" id="accessibilityToggle" class="accessibility-toggle" aria-expanded="false" aria-controls="accessibilityPanel">Erişilebilirlik</button><div id="accessibilityPanel" class="accessibility-panel" role="group" aria-label="Erişilebilirlik seçenekleri" tabindex="-1"><div class="accessibility-panel-head"><span class="tool-label">Erişilebilirlik seçenekleri</span><button type="button" id="accessibilityReset" class="accessibility-reset">Sıfırla</button></div><div class="accessibility-options"><button type="button" data-font="1" aria-label="Standart yazı boyutu">A</button><button type="button" data-font="1.12" aria-label="Büyük yazı boyutu">A+</button><button type="button" data-font="1.25" aria-label="Daha büyük yazı boyutu">A++</button><button type="button" id="contrastToggle" aria-pressed="false">Yüksek kontrast</button><button type="button" id="darkToggle" aria-pressed="false">Koyu mod</button></div></div></div></header><!-- Homepage UI build -->
<div id="main-content" tabindex="-1">
<section id="home" class="page on"><div class="home">
<section class="news-section" aria-labelledby="news-heading">
  <div class="section-head">
    <div><div class="news-kicker"><span class="news-kicker-dot" aria-hidden="true"></span><h2 id="news-heading">Güncel engelli haberleri</h2></div><p>Haklar, ÖTV, sosyal destek ve günlük yaşamdan seçilmiş gelişmeler</p></div>
    <button type="button" class="secondary" onclick="openPage('news')">Tüm haberleri görüntüle</button>
  </div>
  <div id="homeNews" class="news-grid"><div class="news-empty">Haberler yükleniyor…</div></div>
</section>
<div class="hero"><h1>Güncel ÖTV muaf araçlar</h1><p>Liste fiyatları ve hesaplanmış fiyatlar tek yerde. Uygun araçları marka ve paket bazında inceleyebilirsiniz.</p><div class="hero-stats"><div class="stat"><small>Uygun paket</small><b id="heroCount">—</b></div><div class="stat"><small>Marka</small><b id="heroBrands">—</b></div></div></div>
<div class="section" aria-labelledby="vehicles-heading"><div class="section-head"><div><h2 id="vehicles-heading">ÖTV muaf araçlar</h2></div><div id="heroTime" style="font-size:10px;color:var(--muted);text-align:right;white-space:nowrap">Son araştırma saati: —</div></div><div id="homeVehicles" class="vehicle-grid" aria-live="polite"></div><div class="more"><button type="button" class="primary" onclick="openPage(&quot;otv&quot;)">Tüm araçları görüntüle</button></div></div>
<div class="section" style="margin-top:24px"><div class="tool" onclick="window.location.href='https://chat.engelli.me'" style="cursor:pointer"><div class="tool-icon">💬</div><div><b>Kullanıcılar Sohbet</b><small>Topluluk sohbetine katıl</small></div></div><div style="margin-top:7px;padding:0 4px;font-size:10px;line-height:1.45;color:var(--muted)">Bu sohbet Klaklak altyapısı kullanılarak sunulmaktadır. Kişisel bilgilerinizi paylaşmayınız. <a href="/kvkk" style="color:var(--blue);font-weight:700;text-decoration:none">KVKK Aydınlatma Metni →</a></div></div><div class="tools" id="helpers"><div class="section-head" onclick="toggleHelpers()" style="cursor:pointer"><div><h2>Yardımcılar</h2><p>Tek dokunuşla açabilirsiniz</p></div><div style="color:var(--blue);font-size:20px;font-weight:900">＋</div></div><div class="tool-grid"><div class="tool" onclick="openPage('kira')"><div class="tool-icon">₺</div><div><b>Kira Hesaplama</b><small>TÜFE ile kira artışını hesapla</small></div></div><div class="tool" onclick="openPage('excel')"><div class="tool-icon">X</div><div><b>Excel İşlemleri</b><small>Düşeyara, birleştirme ve pivot</small></div></div><div class="tool" onclick="openPage('pdfexcel')"><div class="tool-icon">PDF</div><div><b>PDF → Excel</b><small>PDF içeriğini Excel'e aktar</small></div></div></div></div>
</div></section>
<section id="news" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h2>Güncel engelli haberleri</h1></div>
<div class="panel summary"><div class="news-archive-head"><b>Son 10 haber</b><span id="newsUpdated" class="news-refresh">Güncelleniyor…</span></div></div>
<div id="newsList" class="news-list"><div class="news-empty">Haberler yükleniyor…</div></div></div></section>
<section id="newsDetail" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('news')">‹</button><h2>Haber detayı</h2></div><div class="panel"><h2 id="newsDetailTitle" class="news-detail-title"></h2><div id="newsDetailSummary" class="news-detail-summary"></div><button type="button" id="newsDetailShare" class="news-share" aria-label="Bu haberi paylaş">Paylaş ↗</button><div id="newsDetailSource" class="news-detail-source"></div></div></div></section>
<section id="otv" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h2>ÖTV muaf araçlar</h2></div><div class="panel summary"><b id="otvSummary">Yükleniyor…</b><div class="note">2026 üst limit: <b id="otvLimit">—</b> · Yerli katkı oranı en az %40.</div></div><div id="otvChips" class="chips"></div><div id="otvList" class="list"></div></div></section>
<section id="kira" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h2>Kira Hesaplama</h2></div><div class="panel"><form onsubmit="kiraHesapla(event)"><label class="field">Mevcut kira</label><input id="mevcut-kira" class="input" type="number" min="1" step=".01" placeholder="Örn: 12000" required><label class="field">Kira yenileme ayı</label><select id="yenileme-ayi" required><option value="">Ay seç</option><option value="1">Ocak</option><option value="2">Şubat</option><option value="3">Mart</option><option value="4">Nisan</option><option value="5">Mayıs</option><option value="6">Haziran</option><option value="7">Temmuz</option><option value="8">Ağustos</option><option value="9">Eylül</option><option value="10">Ekim</option><option value="11">Kasım</option><option value="12">Aralık</option></select><button id="kira-btn" class="btn">Hesapla</button></form><div id="kira-result" class="result"></div></div></div></section>
<section id="excel" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h2>Excel İşlemleri</h2></div><div class="panel"><form action="/excel-islem" method="post" enctype="multipart/form-data"><div class="filebox">＋ 1. Excel (Ana Dosya)<input type="file" name="file1" accept=".xlsx,.xls" required></div><div class="filebox">＋ 2. Excel (Referans Dosyası)<input type="file" name="file2" accept=".xlsx,.xls" required></div><label class="field">İşlem</label><textarea name="komut" placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap." required></textarea><button class="btn">Excel işlemini başlat</button></form><div class="kvkk-note">Yüklediğiniz dosyalar yalnızca işlem amacıyla kullanılır ve kalıcı olarak saklanmaz. <a href="/kvkk" target="_blank" rel="noopener noreferrer">KVKK Aydınlatma Metni</a></div></div></div></section>
<section id="pdfexcel" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h2>PDF → Excel</h2></div><div class="panel"><form action="/pdf-excel-islem" method="post" enctype="multipart/form-data"><div class="filebox"><span id="pdfFileName">PDF seçilmedi — PDF dosyasını seç</span><input type="file" name="pdf_file" accept=".pdf" required onchange="pdfSecildi(this)"></div><button class="btn green">PDF'i Excel'e çevir</button></form><div class="kvkk-note">Yüklediğiniz dosyalar yalnızca işlem amacıyla kullanılır ve kalıcı olarak saklanmaz. <a href="/kvkk" target="_blank" rel="noopener noreferrer">KVKK Aydınlatma Metni</a></div></div></div></section>
<footer class="footer">Engelli.me · Güncel veriler resmi kaynaklardan kontrol edilir.</footer><button id="bottomHome" class="bottom-home" onclick="openPage('home')">⌂ Ana Sayfa</button></div></main>
<script>
let otvData=/*INITIAL_OTV_DATA*/{},activeBrand=null;if(!otvData.vehicles)otvData={vehicles:[],limit:2873900};
let newsData=/*INITIAL_NEWS_DATA*/{items:[],updated_at:null},pageStack=['home'],forwardStack=[];
function applyAccessibility(){let font='1',contrast=false,dark=false;try{font=localStorage.getItem('engellime-font-size')||'1';contrast=localStorage.getItem('engellime-high-contrast')==='1';dark=localStorage.getItem('engellime-dark-mode')==='1'}catch(e){}document.documentElement.style.setProperty('--base-scale',font);document.body.classList.toggle('font-large',font==='1.12');document.body.classList.toggle('font-xlarge',font==='1.25');document.body.classList.toggle('high-contrast',contrast);document.body.classList.toggle('dark-mode',dark);document.querySelectorAll('[data-font]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.font===font?'true':'false'));document.getElementById('contrastToggle').setAttribute('aria-pressed',contrast?'true':'false');document.getElementById('darkToggle').setAttribute('aria-pressed',dark?'true':'false')}
const accessibilityToggle=document.getElementById('accessibilityToggle'),accessibilityPanel=document.getElementById('accessibilityPanel');
function setAccessibilityPanel(open,moveFocus=false){if(!accessibilityToggle||!accessibilityPanel)return;accessibilityPanel.classList.toggle('open',open);accessibilityToggle.setAttribute('aria-expanded',open?'true':'false');if(open&&moveFocus)accessibilityPanel.focus();else if(!open&&moveFocus)accessibilityToggle.focus()}
accessibilityToggle?.addEventListener('click',()=>setAccessibilityPanel(!accessibilityPanel.classList.contains('open'),true));
accessibilityPanel?.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();setAccessibilityPanel(false,true)}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&accessibilityPanel?.classList.contains('open')){e.preventDefault();setAccessibilityPanel(false,true)}});
document.querySelectorAll('[data-font]').forEach(b=>b.addEventListener('click',()=>{try{localStorage.setItem('engellime-font-size',b.dataset.font)}catch(e){}applyAccessibility()}));document.getElementById('contrastToggle').addEventListener('click',()=>{let on=!document.body.classList.contains('high-contrast');try{localStorage.setItem('engellime-high-contrast',on?'1':'0')}catch(e){}applyAccessibility()});document.getElementById('darkToggle').addEventListener('click',()=>{let on=!document.body.classList.contains('dark-mode');try{localStorage.setItem('engellime-dark-mode',on?'1':'0')}catch(e){}applyAccessibility()});document.getElementById('accessibilityReset').addEventListener('click',()=>{try{localStorage.removeItem('engellime-font-size');localStorage.removeItem('engellime-high-contrast');localStorage.removeItem('engellime-dark-mode')}catch(e){}applyAccessibility()});applyAccessibility();
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function safeUrl(v){let u=String(v||'').trim();return /^https?:\/\//i.test(u)?u:''}
function newsDate(v){if(!v)return '';try{return new Date(v).toLocaleDateString('tr-TR',{day:'2-digit',month:'short',year:'numeric'})}catch(e){return ''}}
function shortNewsSummary(v){let s=String(v||'').trim(),parts=s.match(/[^.!?]+[.!?]+/g);return parts?parts.slice(0,2).join(' ').trim():s}
function newsCard(item){let u=safeUrl(item.url),title=esc(item.title),summary=esc(shortNewsSummary(item.summary)),source=esc((item.source||'Kaynak belirtilmemiş').replace(/\s*\(yedek\)\s*/gi,'')),dt=esc(newsDate(item.published_at)),idx=newsData.items.indexOf(item),titleId='news-title-'+idx;return '<article class="news-card clickable" data-news-index="'+idx+'" tabindex="0" role="button" aria-labelledby="'+titleId+'"><div class="news-meta"><span class="news-date">'+dt+'</span></div><h3 id="'+titleId+'">'+title+'</h3><a class="news-summary news-summary-link" href="#newsDetail" data-news-index="'+idx+'" aria-label="'+title+'">'+summary+'</a><div class="news-bottom"><span class="news-source">Kaynak: <b>'+source+'</b></span>'+(u?'<a class="news-link" href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">Habere git ↗</a>':'')+'</div></article>'}
async function shareNews(index){let item=newsData.items[index];if(!item)return;let url=location.origin+location.pathname+'?haber='+encodeURIComponent(item.title||'');let data={title:item.title||'Engelli.me',text:item.title||'Engelli.me',url};try{if(navigator.share){await navigator.share(data);return}if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(url);alert('Engelli.me haber bağlantısı kopyalandı.')}else{window.prompt('Engelli.me haber bağlantısını kopyalayın:',url)}}catch(e){if(e&&e.name!=='AbortError')console.error(e)}}
function bindNewsCards(){document.querySelectorAll('.news-card[data-news-index]').forEach(card=>{let index=Number(card.dataset.newsIndex),open=()=>openNewsDetail(index);card.addEventListener('click',e=>{if(e.target.closest('.news-summary-link,.news-link'))return;open()});card.addEventListener('keydown',e=>{if(e.target.closest('.news-summary-link,.news-link'))return;if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}});card.querySelector('.news-summary-link')?.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();open()});card.querySelector('.news-link')?.addEventListener('click',e=>{e.stopPropagation()})})}
function openNewsDetail(index){let item=newsData.items[index];if(!item)return;document.getElementById('newsDetailTitle').textContent=item.title||'';document.getElementById('newsDetailSummary').textContent=item.summary||'';let u=safeUrl(item.url),source=esc((item.source||'Kaynak belirtilmemiş').replace(/\s*\(yedek\)\s*/gi,'')),share=document.getElementById('newsDetailShare');share.onclick=()=>shareNews(index);share.style.display='block';document.getElementById('newsDetailSource').innerHTML=u?('Kaynak: <a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+source+' ↗</a>'):('Kaynak: '+source);openPage('newsDetail')}
function renderNews(){let items=newsData.items||[],home=document.getElementById('homeNews');if(home){let homeItems=items.slice(0,window.innerWidth>900?6:4);home.innerHTML=homeItems.length?homeItems.map(newsCard).join(''):'<div class="news-empty">Şu anda yayınlanacak güncel engelli haberi bulunamadı.</div>'}let list=document.getElementById('newsList');if(list){list.innerHTML=items.slice(0,10).map(newsCard).join('')||'<div class="news-empty">Şu anda yayınlanacak güncel engelli haberi bulunamadı.</div>'}bindNewsCards();let updated=document.getElementById('newsUpdated');if(updated)updated.textContent=newsData.updated_at?'Son güncelleme: '+newsDate(newsData.updated_at):'Henüz güncelleme yok'}
async function loadNews(){try{let r=await fetch('/api/news?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('news');newsData=await r.json();renderNews();let sharedTitle=new URLSearchParams(location.search).get('haber');if(sharedTitle){let sharedIndex=newsData.items.findIndex(x=>String(x.title||'')===sharedTitle);if(sharedIndex>=0)openNewsDetail(sharedIndex)}}catch(e){let home=document.getElementById('homeNews'),list=document.getElementById('newsList');if(home)home.innerHTML='<div class="news-empty">Haberler şu anda alınamadı.</div>';if(list)list.innerHTML='<div class="news-empty">Haberler şu anda alınamadı.</div>'}}
function openPage(id,push=true){document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));let target=document.getElementById(id);if(!target)return;target.classList.add('on');let bh=document.getElementById('bottomHome');if(bh)bh.style.setProperty('display',id==='home'?'none':'block','important');if(push&&pageStack[pageStack.length-1]!==id){pageStack.push(id);forwardStack=[]}scrollTo(0,0);if(id==='otv')renderOTV()}
function goPreviousPage(){if(pageStack.length>1){forwardStack.push(pageStack.pop());openPage(pageStack[pageStack.length-1],false)}else{openPage('home',false)}}
function goNextPage(){if(forwardStack.length){let id=forwardStack.pop();pageStack.push(id);openPage(id,false)}}

function tl(v){return Number(v||0).toLocaleString('tr-TR')+' ₺'}
function otvRateFor(v){let p=Number(v.price||0),b=(v.brand||'').toUpperCase(),m=(v.model||'').toUpperCase();if(!p)return null;let solve=(rules)=>{for(let [r,min,max] of rules){let base=p/1.20/(1+r);if(base>min&&(max==null||base<=max))return r}return null};if(b==='TOGG')return solve([[.25,0,1650000],[.55,1650000,null]]);if(b==='TOYOTA'&&m.includes('C-HR'))return solve([[.70,0,1250000],[.80,1250000,null]]);if(b==='TOYOTA'&&m.includes('COROLLA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]]);if(b==='FIAT'&&m.includes('ULYSSE'))return solve([[1.50,0,1650000],[1.70,1650000,null]]);if(b==='FIAT'&&m.includes('EGEA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]])||solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]]);return solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]])}
function exemptPrice(v){let r=otvRateFor(v);return r==null?null:Math.round(Number(v.price)/(1+r))}
function verifiedRow(v){let ep=exemptPrice(v);return '<div class="row"><div class="rowtop"><div><div class="name">'+(v.brand||'')+' '+(v.model||'')+'</div><div class="meta">'+(v.trim||'')+'</div></div><span class="tag">Uygun</span></div><div class="price">Liste Fiyatı<b>'+tl(v.price)+'</b></div>'+(ep?'<div class="price">Hesaplanmış ÖTV Muaf Fiyat<b>'+tl(ep)+'</b></div>':'')+'<div class="note">Yerlilik: %'+(v.locality||'—')+' · Kaynak: '+(v.source_name||v.brand)+' · Son kontrol: '+(v.checked_at||'—')+'</div></div>'}
function allBrands(){return [...new Set((otvData.vehicles||[]).map(v=>v.brand).filter(Boolean))]}
function buttons(){let bs=allBrands();if(activeBrand&&!bs.includes(activeBrand))activeBrand=null;let el=document.getElementById('otvChips');el.innerHTML=bs.map(b=>'<button class="chip '+(b===activeBrand?'on':'')+'" data-brand="'+String(b).replace(/"/g,'&quot;')+'">'+b+'</button>').join('');el.querySelectorAll('.chip').forEach(btn=>btn.addEventListener('click',()=>setBrand(btn.dataset.brand)))}
function setBrand(b){activeBrand=activeBrand===b?null:b;renderOTV()}
function renderHomeVehicles(){let el=document.getElementById("homeVehicles"),all=(otvData.vehicles||[]).filter(v=>Number(v.price)>0),byModel={};all.forEach(v=>{let key=((v.brand||"")+" "+(v.model||"")).trim().toUpperCase();if(!byModel[key]||Number(v.price)<Number(byModel[key].price))byModel[key]=v});let vs=Object.values(byModel).sort((a,b)=>Number(a.price)-Number(b.price)).slice(0,6);el.innerHTML=vs.length?vs.map(v=>'<div class="vehicle-card"><div class="vehicle-info"><div class="brandline">'+(v.brand||'')+'</div><h3>'+(v.model||'')+'</h3><div class="trim">'+(v.trim||'')+'</div></div><div class="price-line"><div class="price-label">ÖTV muaf fiyatı</div><div class="price">'+tl(exemptPrice(v)||v.price)+'</div></div></div>').join(''):'<div class="panel">Araç listesi yükleniyor…</div>'}
function toggleHelpers(){document.getElementById("helpers").classList.toggle("open")}
function renderHome(){renderHomeVehicles();let c=document.getElementById('heroCount'),b=document.getElementById('heroBrands'),t=document.getElementById('heroTime');c.textContent=(otvData.vehicles||[]).length+' paket';b.textContent=allBrands().length+' marka';t.textContent=otvData.updated_time?'Son araştırma saati: '+otvData.updated_time:'Son araştırma saati: —'}
function pdfSecildi(input){let el=document.getElementById('pdfFileName');el.textContent=input.files&&input.files.length?'✓ PDF seçildi: '+input.files[0].name:'PDF seçilmedi — PDF dosyasını seç'}
function renderOTV(){document.getElementById('otvLimit').textContent=tl(otvData.limit);buttons();let rows=(otvData.vehicles||[]).filter(v=>!activeBrand||v.brand===activeBrand);document.getElementById('otvSummary').textContent=rows.length+' uygun paket · Son fiyat kontrolü '+(otvData.updated_at||'—');document.getElementById('otvList').innerHTML=rows.length?rows.map(verifiedRow).join(''):'<div class="panel">Bu markada uygun ve fiyatı doğrulanmış paket bulunamadı.</div>'}
async function loadOTV(){try{let r=await fetch('/api/otv',{cache:'no-store'});otvData=await r.json();renderHome()}catch(e){}}
function otvNeedsRefresh(){try{let s=String(otvData.updated_at||'').trim();let m=s.match(/^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2})$/);if(!m)return true;let dt=new Date(Number(m[3]),Number(m[2])-1,Number(m[1]),Number(m[4]),Number(m[5]));return Date.now()-dt.getTime()>=43200000}catch(e){return true}}
async function triggerOTVBackgroundRefresh(){if(!otvNeedsRefresh())return;try{await fetch('/api/otv/yenile',{method:'POST',keepalive:true});let r=await fetch('/api/otv?ts='+Date.now(),{cache:'no-store'});if(r.ok){otvData=await r.json();renderHome()}}catch(e){}}
async function kiraHesapla(e){e.preventDefault();let b=document.getElementById('kira-btn'),res=document.getElementById('kira-result');b.disabled=true;b.textContent='Hesaplanıyor...';res.style.display='block';res.innerHTML='Güncel TÜFE kontrol ediliyor...';try{let body=new URLSearchParams();body.append('mevcut_kira',document.getElementById('mevcut-kira').value);body.append('yenileme_ayi',document.getElementById('yenileme-ayi').value);let r=await fetch('/kira-hesapla',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});let d=await r.json();if(!r.ok)throw Error(d.detail||'Hesaplama yapılamadı.');res.innerHTML='<div class="note" style="text-align:center">12 aylık ortalama TÜFE</div><div class="big">%'+d.oran+'</div><div class="note" style="text-align:center">Yeni kira</div><div class="big">'+d.yeni_kira+'</div><div class="note">'+d.durum+'</div>'}catch(x){res.innerHTML='<div class="note">'+x.message+'</div>'}finally{b.disabled=false;b.textContent='Hesapla'}}
let swipeStartX=0,swipeStartY=0,swipeActive=false;
document.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'){swipeStartX=e.clientX;swipeStartY=e.clientY;swipeActive=true}},{passive:true});
document.addEventListener('pointerup',e=>{if(!swipeActive||e.pointerType!=='touch')return;swipeActive=false;let dx=e.clientX-swipeStartX,dy=e.clientY-swipeStartY;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)*1.1){if(dx<0)goNextPage();else goPreviousPage()}},{passive:true});
window.addEventListener('scroll',()=>{let b=document.getElementById('bottomHome');if(b)b.classList.toggle('compact',window.scrollY>120)},{passive:true});
document.addEventListener('pointercancel',()=>{swipeActive=false},{passive:true});
renderHome();renderNews();loadOTV();loadNews();setTimeout(triggerOTVBackgroundRefresh,800);
</script></body></html>'''


if __name__ == "__main__":
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=int(os.environ.get("PORT",8000)), reload=False)
