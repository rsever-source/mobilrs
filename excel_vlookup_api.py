import io, os, uuid
from datetime import date
from urllib.parse import urlparse

import pandas as pd, pdfplumber, uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from starlette.background import BackgroundTask

from tufe_service import get_current_tufe, save_cache
from otv_service import get_otv_data, refresh_otv_data, _load as load_otv_cache
from vehicle_images import get_vehicle_image

app = FastAPI(title="Rdv Asistan")

@app.get("/vehicle-image")
async def vehicle_image(key: str):
    data = get_vehicle_image(key)
    if not data:
        return Response(status_code=404)
    content, media_type = data
    return Response(content=content, media_type=media_type)

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
MAX_FILE_SIZE = 25 * 1024 * 1024
MONTH_NAMES = {1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}


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


def next_renewal_year(m):
    t=date.today(); return t.year if m >= t.month else t.year+1


def previous_month(y,m): return (y-1,12) if m==1 else (y,m-1)


@app.get("/tufe-guncelle")
async def spark_tufe_guncelle(key:str=Query(...), source:str=Query(...), rate:float=Query(...), year:int=Query(...), month:int=Query(...)):
    expected=os.environ.get("SPARK_TUFE_KEY","").strip()
    if not expected: raise HTTPException(500,"SPARK_TUFE_KEY ayarlanmamış.")
    if key != expected: raise HTTPException(403,"Yetkisiz erişim.")
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
    except Exception as e: raise HTTPException(503,f"Güncel TÜFE verisi alınamadı. {e}")
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
async def api_otv_yenile(): return JSONResponse(refresh_otv_data(force=True))

@app.get("/", response_class=HTMLResponse)
async def index():
    initial = load_otv_cache() or {}
    initial_json = __import__("json").dumps(initial, ensure_ascii=False).replace("</", "<\\/")
    return HTMLResponse(HOME_HTML.replace("/*INITIAL_OTV_DATA*/{}", initial_json))

@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    return HTMLResponse("User-agent: *\nAllow: /\nSitemap: https://engelli.me/sitemap.xml\n", media_type="text/plain")


@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml():
    return HTMLResponse("<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>https://engelli.me/</loc></url></urlset>", media_type="application/xml")




@app.post("/excel-islem")
async def excel_motor(komut:str=Form(...), file1:UploadFile=File(...), file2:UploadFile=File(...)):
    out=None
    try:
        if not check_extension(file1.filename,(".xlsx",".xls")) or not check_extension(file2.filename,(".xlsx",".xls")): raise HTTPException(400,"Geçerli Excel dosyaları seç.")
        a=pd.read_excel(io.BytesIO(await read_upload_limited(file1))); b=pd.read_excel(io.BytesIO(await read_upload_limited(file2)))
        if a.empty or b.empty: raise HTTPException(400,"Excel dosyalarında veri bulunamadı.")
        a.columns=[normalize_column_name(c) for c in a.columns]; b.columns=[normalize_column_name(c) for c in b.columns]; k=komut.lower().strip()
        if any(w in k for w in ["düşeyara","duseyara","vlookup","birleştir","birlestir","merge","eşleştir","eslestir"]):
            c=select_join_column(a,b,komut); result=pd.merge(a,b,on=c,how="left",suffixes=("","_referans"))
        elif any(w in k for w in ["pivot","özet","ozet","grupla","toplam"]):
            cc=find_command_columns(a,komut); nums=a.select_dtypes(include="number").columns.tolist()
            if not nums: raise HTTPException(400,"Pivot/özet için sayısal sütun bulunamadı.")
            val=next((c for c in cc if c in nums),nums[0]); idx=next((c for c in cc if c!=val),None) or next((c for c in a.columns if c!=val),None)
            if idx is None: raise HTTPException(400,"Pivot için grup sütunu bulunamadı.")
            result=pd.pivot_table(a,values=val,index=idx,aggfunc="sum",fill_value=0).reset_index()
        else: result=a.copy()
        out=unique_output_path("xlsx"); result.to_excel(out,index=False)
        return FileResponse(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="excel_sonuc.xlsx",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,f"Excel Hatası: {e}")


@app.post("/pdf-excel-islem")
async def pdf_excel_motor(pdf_file:UploadFile=File(...)):
    out=None
    try:
        if not check_extension(pdf_file.filename,(".pdf",)): raise HTTPException(400,"Geçerli bir PDF dosyası seç.")
        rows=[]
        with pdfplumber.open(io.BytesIO(await read_upload_limited(pdf_file))) as pdf:
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
        if not rows: raise HTTPException(400,"PDF içinde Excel'e aktarılacak metin veya tablo bulunamadı. Taranmış/resim PDF ise OCR gerekir.")
        mc=max(map(len,rows)); df=pd.DataFrame([r+[""]*(mc-len(r)) for r in rows]); out=unique_output_path("xlsx"); df.to_excel(out,index=False,header=False)
        return FileResponse(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="pdf_to_excel_sonuc.xlsx",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,f"PDF → Excel Hatası: {e}")


HOME_HTML = r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>ÖTV Muaf Araçlar ve Kira Hesaplama | Engelli.me</title><meta name="description" content="ÖTV muaf araçlar, güncel liste fiyatları ve tahmini ÖTV muaf fiyatları. TÜFE ile kira hesaplama, Excel ve PDF → Excel araçları."><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="https://engelli.me/"><meta property="og:title" content="ÖTV Muaf Araçlar ve Kira Hesaplama | Engelli.me"><meta property="og:description" content="ÖTV muaf araç fiyatları ve pratik hesaplama araçları."><meta property="og:url" content="https://engelli.me/"><meta property="og:type" content="website">
<style>:root{--blue:#1769e0;--ink:#172033;--muted:#6b7485;--line:#e5e9f1;--bg:#eef2f7;--card:#fff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Aptos,"Segoe UI",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}.app{width:min(1280px,calc(100% - 48px));margin:24px auto;min-height:calc(100vh - 48px);background:var(--card);border:1px solid #e4e8ef;border-radius:28px;padding:30px 34px 48px;box-shadow:0 18px 55px #17203312}.top{display:flex;align-items:center;gap:12px;margin:0 2px 24px}.brandmark{width:46px;height:46px;border-radius:14px;background:linear-gradient(145deg,#173d78,#0d2c5d);color:#fff;display:grid;place-items:center;font-size:21px;font-weight:850}.brandname{font-size:29px;font-weight:850;letter-spacing:-.7px}.hero{background:linear-gradient(135deg,#f8fbff,#edf4ff);color:var(--ink);border:1px solid #dce6f6;border-radius:24px;padding:24px;box-shadow:0 12px 30px #1769e312}.herotop{display:flex;justify-content:space-between;align-items:flex-start;gap:24px}.carbadge{font-size:24px;margin-bottom:4px}.hero h2{margin:0;font-size:30px;line-height:1.1;font-weight:800;letter-spacing:-.7px}.sub{font-size:14px;color:var(--muted);margin-top:7px}.check{text-align:right}.check small,.herofoot small{display:block;color:var(--muted);font-size:11px}.check b{display:block;margin-top:4px;font-size:16px}.herofoot{display:flex;gap:72px;margin-top:22px}.herofoot b{display:block;font-size:25px;margin-top:3px}.hero button{margin-top:22px;border:0;border-radius:13px;background:var(--blue);color:#fff;padding:12px 18px;font-weight:750;font-size:13px;cursor:pointer}.sec{display:flex;justify-content:space-between;align-items:center;margin:28px 2px 12px}.sec h3{margin:0;font-size:20px;font-weight:800}.homevehicles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.homecar{border:1px solid var(--line);border-radius:19px;padding:13px;background:linear-gradient(145deg,#fff,#f7f9fc);cursor:pointer;min-width:0;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}.homecar:hover{transform:translateY(-3px);box-shadow:0 12px 28px #17203316;border-color:#bfd0ec}.homecar .carpic{height:116px;border-radius:14px;background:linear-gradient(135deg,#edf3ff,#f8fafc);display:grid;place-items:center;overflow:hidden;margin-bottom:11px}.homecar .carpic img{width:100%;height:100%;object-fit:contain;object-position:center;padding:2px;display:block}.homecar .carbrand{font-size:11px;color:var(--muted);font-weight:700}.homecar .carmodel{font-size:15px;font-weight:800;line-height:1.25;margin-top:3px;overflow-wrap:anywhere}.homecar .carprice{font-size:12px;color:var(--blue);font-weight:800;margin-top:7px}.utilitytab{display:flex;justify-content:space-between;align-items:center;margin:26px 0 11px;padding:16px 18px;border:1px solid #dfe6f2;border-radius:18px;background:linear-gradient(135deg,#f8fbff,#eef4ff);cursor:pointer}.utilitytab span{display:flex;align-items:center;gap:9px}.utilitytab small{display:block;color:var(--muted);font-size:11px;margin-top:2px}.projects{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.projects.collapsed{display:none}.p{border:1px solid var(--line);border-radius:17px;padding:18px;display:flex;gap:11px;align-items:center;background:#fff;cursor:pointer;transition:transform .15s ease,box-shadow .15s ease}.p:hover{transform:translateY(-2px);box-shadow:0 9px 24px #17203312;border-color:#bfd0ec}.ico{width:40px;height:40px;border-radius:12px;background:#eef4ff;display:grid;place-items:center;font-size:20px}.p b{font-size:15px;font-weight:750}.p small{display:block;color:var(--muted);font-size:11px;margin-top:3px}.page{display:none}.page.on{display:block}.pagehead{display:flex;align-items:center;gap:8px;margin-bottom:18px}.back{border:0;background:none;font-size:28px;padding:4px 10px 4px 0;cursor:pointer}.pagehead h2{margin:0;font-size:27px;font-weight:800}.panel{border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px;background:#fff}.chips{display:flex;gap:8px;overflow:auto;padding-bottom:5px}.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 14px;white-space:nowrap;font-weight:700;font-size:12px;cursor:pointer}.chip.on{background:var(--blue);color:#fff;border-color:var(--blue)}.list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.row{border:1px solid var(--line);border-radius:17px;padding:15px;background:#fff;min-width:0}.rowtop{display:flex;justify-content:space-between;gap:10px}.vehicle-main{display:flex;align-items:center;gap:12px;min-width:0}.vehicle-mini{width:150px;height:96px;flex:0 0 150px;border-radius:13px;overflow:hidden;background:linear-gradient(135deg,#edf3ff,#f7f9fc);display:grid;place-items:center;font-size:27px}.vehicle-mini img{width:100%;height:100%;object-fit:contain;object-position:center;padding:3px;display:block}.row .tag{background:#e8f8ee;color:#168143;padding:5px 9px;border-radius:999px;font-size:10px;height:max-content}.row .name{font-size:16px;font-weight:800;overflow-wrap:anywhere}.row .meta{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.4;overflow-wrap:anywhere}.price{margin-top:10px;font-size:11px;color:var(--muted)}.price b{display:block;color:#111;font-size:18px;margin-top:2px;overflow-wrap:anywhere}.note{font-size:11px;color:var(--muted);line-height:1.5;margin-top:8px}.field{display:block;margin:12px 0 6px;font-size:12px;font-weight:800}.input,select,textarea{width:100%;border:1px solid #d9dee8;border-radius:13px;padding:13px;font-size:16px;background:#fff}.btn{width:100%;border:0;border-radius:13px;padding:14px;background:var(--blue);color:#fff;font-size:15px;font-weight:750;margin-top:12px;cursor:pointer}.green{background:#168f50}.result{display:none;margin-top:12px;border-radius:16px;background:#f3f7ff;padding:16px}.result .big{font-size:28px;font-weight:900;color:var(--blue);text-align:center;margin:8px 0}.filebox{position:relative;border:2px dashed #d6dbe5;border-radius:14px;padding:18px;text-align:center;margin:10px 0;color:var(--muted);font-size:12px}.filebox input{position:absolute;inset:0;opacity:0;width:100%;height:100%}.homebtn{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);border:1px solid var(--line);background:#fff;color:var(--blue);border-radius:999px;padding:10px 18px;font-weight:800;box-shadow:0 7px 25px #0001;z-index:9;cursor:pointer}@media(max-width:1000px){.homevehicles{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:767px){body{background:#fff}.app{width:100%;max-width:520px;margin:0 auto;min-height:100vh;border:0;border-radius:0;padding:18px 16px 88px;box-shadow:none}.brandname{font-size:25px}.hero{padding:16px;border-radius:22px}.hero h2{font-size:25px}.check{display:none}.herofoot{gap:38px}.herofoot b{font-size:22px}.homevehicles{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:12px;padding:2px 2px 10px;margin-right:-16px;padding-right:16px;scrollbar-width:none}.homevehicles::-webkit-scrollbar{display:none}.homecar{flex:0 0 82%;scroll-snap-align:start}.homecar .carpic{height:132px}.projects{grid-template-columns:1fr 1fr}.list{grid-template-columns:1fr}.vehicle-mini{width:110px;height:72px;flex-basis:110px}.pagehead h2{font-size:22px}.sec h3{font-size:18px}}</style></head><body><main class="app">
<section id="home" class="page on"><div class="hero"><div class="herotop"><div><div class="carbadge">🚗</div><h2>ÖTV Muaf Araçlar</h2><div class="sub">Güncel liste fiyatları ve tahmini ÖTV muaf fiyatlar</div></div><div class="check"><small>Son fiyat kontrolü</small><b id="heroTime" class="loading">—</b></div></div><div class="herofoot"><div><small>Uygun paket</small><b id="heroCount" class="loading">—</b></div><div><small>Marka</small><b id="heroBrands" class="loading">—</b></div></div><button onclick="openPage('otv')">Tümünü Gör ›</button></div><div class="sec"><h3>Öne Çıkan Araçlar</h3></div><div id="homeVehicles" class="homevehicles"></div><div class="utilitytab" onclick="toggleUtilities()"><span>🛠️ <b>Yararlı İşlemler</b><small>Günlük işlemler ve araçlar</small></span><b id="utilityArrow">⌄</b></div><div id="utilities" class="projects collapsed"><div class="p" onclick="openPage('kira')"><div class="ico">🏠</div><div><b>Kira Hesaplama</b><small>TÜFE ile kira artışı</small></div></div><div class="p" onclick="openPage('excel')"><div class="ico">📊</div><div><b>Excel</b><small>Düşeyara, birleştirme, pivot</small></div></div><div class="p" onclick="openPage('pdfexcel')"><div class="ico">🟢</div><div><b>PDF → Excel</b><small>Tablo ve metni Excel'e aktar</small></div></div></div></section>
<section id="otv" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>ÖTV Muaf Araçlar</h2></div><div class="panel"><b id="otvSummary">Yükleniyor…</b><div class="note">2026 üst limit: <b id="otvLimit">—</b> · Yerli katkı oranı en az %40.</div></div><div id="otvChips" class="chips"></div><div id="otvList" class="list"></div></section>
<section id="kira" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>Kira Hesaplama</h2></div><div class="panel"><form onsubmit="kiraHesapla(event)"><label class="field">Mevcut kira</label><input id="mevcut-kira" class="input" type="number" min="1" step=".01" placeholder="Örn: 12000" required><label class="field">Kira yenileme ayı</label><select id="yenileme-ayi" required><option value="">Ay seç</option><option value="1">Ocak</option><option value="2">Şubat</option><option value="3">Mart</option><option value="4">Nisan</option><option value="5">Mayıs</option><option value="6">Haziran</option><option value="7">Temmuz</option><option value="8">Ağustos</option><option value="9">Eylül</option><option value="10">Ekim</option><option value="11">Kasım</option><option value="12">Aralık</option></select><button id="kira-btn" class="btn">Hesapla</button></form><div id="kira-result" class="result"></div></div></section>
<section id="excel" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>Excel</h2></div><div class="panel"><form action="/excel-islem" method="post" enctype="multipart/form-data"><div class="filebox">＋ 1. Excel (Ana Dosya)<input type="file" name="file1" accept=".xlsx,.xls" required></div><div class="filebox">＋ 2. Excel (Referans Dosyası)<input type="file" name="file2" accept=".xlsx,.xls" required></div><label class="field">İşlem</label><textarea name="komut" placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap." required></textarea><button class="btn">Excel İşlemini Başlat</button></form></div></section>

<section id="pdfexcel" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>PDF → Excel</h2></div><div class="panel"><form action="/pdf-excel-islem" method="post" enctype="multipart/form-data"><div class="filebox" id="pdfFileBox">📄 <span id="pdfFileName">PDF seçilmedi — PDF Dosyasını Seç</span><input type="file" name="pdf_file" accept=".pdf" required onchange="pdfSecildi(this)"></div><button class="btn green">PDF'i Excel'e Çevir</button></form></div></section>
<button class="homebtn" onclick="openPage('home')">⌂ &nbsp;Ana Sayfa</button></main>
<script>
let otvData=/*INITIAL_OTV_DATA*/{},activeBrand=null; if(!otvData.vehicles)otvData={vehicles:[],limit:2873900};
function openPage(id){document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));document.getElementById(id).classList.add('on');scrollTo(0,0);if(id==='otv')renderOTV()}
function tl(v){return Number(v||0).toLocaleString('tr-TR')+' ₺'}
function otvRateFor(v){let p=Number(v.price||0),b=(v.brand||'').toUpperCase(),m=(v.model||'').toUpperCase();if(!p)return null;let solve=(rules)=>{for(let [r,min,max] of rules){let base=p/1.20/(1+r);if(base>min&&(max==null||base<=max))return r}return null};if(b==='TOGG')return solve([[.25,0,1650000],[.55,1650000,null]]);if(b==='TOYOTA'&&m.includes('C-HR'))return solve([[.70,0,1250000],[.80,1250000,null]]);if(b==='TOYOTA'&&m.includes('COROLLA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]]);if(b==='FIAT'&&m.includes('ULYSSE'))return solve([[1.50,0,1650000],[1.70,1650000,null]]);if(b==='FIAT'&&m.includes('EGEA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]])||solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]]);return solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]])}function exemptPrice(v){let r=otvRateFor(v);return r==null?null:Math.round(Number(v.price)/(1+r))}function vehicleImage(v){return v&&v.image_url?v.image_url:''}function verifiedRow(v){let ep=exemptPrice(v),img=vehicleImage(v);return `<div class="row"><div class="rowtop"><div class="vehicle-main"><div class="vehicle-mini">${img?`<img src="${img}" loading="lazy" alt="${v.brand} ${v.model}" onerror="this.parentElement.textContent='🚗';">`:'🚗'}</div><div><div class="name">${v.brand} ${v.model}</div><div class="meta">${v.trim||''}</div></div></div><span class="tag">Uygun</span></div><div class="price">Liste Fiyatı<b>${tl(v.price)}</b></div>${ep?`<div class="price">Tahmini ÖTV Muaf Fiyat<b>${tl(ep)}</b></div>`:''}<div class="note">Yerlilik: %${v.locality||'—'} · Kaynak: ${v.source_name||v.brand} · Son kontrol: ${v.checked_at||'—'}</div></div>`}
function allBrands(){return [...new Set((otvData.vehicles||[]).map(v=>v.brand).filter(Boolean))]}
function buttons(){let bs=allBrands();if(activeBrand&&!bs.includes(activeBrand))activeBrand=null;document.getElementById('otvChips').innerHTML=bs.map(b=>`<button class="chip ${b===activeBrand?'on':''}" onclick="setBrand('${b.replace(/'/g,"\\'")}')">${b}</button>`).join('')}
function setBrand(b){activeBrand=activeBrand===b?null:b;renderOTV()}
function toggleUtilities(){let x=document.getElementById("utilities"),a=document.getElementById("utilityArrow");x.classList.toggle("collapsed");a.textContent=x.classList.contains("collapsed")?"⌄":"⌃"}function renderHomeVehicles(){let el=document.getElementById("homeVehicles"),all=(otvData.vehicles||[]).filter(v=>Number(v.price)>0),byModel={};all.forEach(v=>{let key=((v.brand||"")+" "+(v.model||"")).trim().toUpperCase();if(!byModel[key]||Number(v.price)<Number(byModel[key].price))byModel[key]=v});let vs=Object.values(byModel).sort((a,b)=>Number(a.price)-Number(b.price)).slice(0,6);el.innerHTML=vs.length?vs.map(function(v){let img=vehicleImage(v);return "<div class=\"homecar\" onclick=\"openPage('otv')\" title=\"Araç detaylarını gör\"><div class=\"carpic\">"+(img?"<img src=\""+img+"\" loading=\"lazy\" alt=\""+(v.brand||"")+" "+(v.model||"")+"\" onerror=\"this.parentElement.textContent='🚗';\">":"🚗")+"</div><div class=\"carbrand\">"+(v.brand||"")+"</div><div class=\"carmodel\">"+(v.model||"")+"</div><div class=\"carprice\">"+tl(v.price)+"</div></div>"}).join(""):"<div class=\"panel\">Araç listesi yükleniyor…</div>"}function renderHome(){renderHomeVehicles();let c=document.getElementById('heroCount'),b=document.getElementById('heroBrands'),t=document.getElementById('heroTime');c.textContent=(otvData.vehicles||[]).length+' paket';b.textContent=allBrands().length+' marka';t.textContent=otvData.updated_time||'—';c.classList.remove('loading');b.classList.remove('loading');t.classList.remove('loading')}
function pdfSecildi(input){let el=document.getElementById('pdfFileName');if(input.files&&input.files.length){el.textContent='✓ PDF seçildi: '+input.files[0].name;}else{el.textContent='PDF seçilmedi — PDF Dosyasını Seç';}}function renderOTV(){document.getElementById('otvLimit').textContent=tl(otvData.limit);buttons();let rows=(otvData.vehicles||[]).filter(v=>!activeBrand||v.brand===activeBrand);document.getElementById('otvSummary').textContent=`${rows.length} uygun paket · Son fiyat kontrolü ${otvData.updated_at||'—'}`;document.getElementById('otvList').innerHTML=rows.length?rows.map(verifiedRow).join(''):'<div class="panel">Bu markada uygun ve fiyatı doğrulanmış paket bulunamadı.</div>'}
async function loadOTV(){try{let r=await fetch('/api/otv');otvData=await r.json();renderHome()}catch(e){}}
async function kiraHesapla(e){e.preventDefault();let b=document.getElementById('kira-btn'),res=document.getElementById('kira-result');b.disabled=true;b.textContent='Hesaplanıyor...';res.style.display='block';res.innerHTML='Güncel TÜFE kontrol ediliyor...';try{let body=new URLSearchParams();body.append('mevcut_kira',document.getElementById('mevcut-kira').value);body.append('yenileme_ayi',document.getElementById('yenileme-ayi').value);let r=await fetch('/kira-hesapla',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});let d=await r.json();if(!r.ok)throw Error(d.detail||'Hesaplama yapılamadı.');res.innerHTML=`<div class="note" style="text-align:center">12 aylık ortalama TÜFE</div><div class="big">%${d.oran}</div><div class="note" style="text-align:center">Yeni kira</div><div class="big">${d.yeni_kira}</div><div class="note">${d.durum}</div>`}catch(x){res.innerHTML='<div class="note">'+x.message+'</div>'}finally{b.disabled=false;b.textContent='Hesapla'}}
renderHome(); loadOTV();
</script></body></html>'''


if __name__ == "__main__":
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=int(os.environ.get("PORT",8000)), reload=False)
