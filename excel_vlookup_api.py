import io, os, uuid
from datetime import date
from urllib.parse import urlparse

import pandas as pd, pdfplumber, uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from starlette.background import BackgroundTask

from tufe_service import get_current_tufe, save_cache
from otv_service import get_otv_data, refresh_otv_data, _load as load_otv_cache

app = FastAPI(title="Rdv Asistan")


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


HOME_HTML = r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>ÖTV Muaf Araçlar ve Kira Hesaplama | Engelli.me</title><meta name="description" content="Güncel ÖTV muaf araç liste fiyatları ve hesaplanmış fiyatlar. TÜFE ile kira hesaplama, Excel ve PDF → Excel araçları."><meta name="robots" content="index,follow"><link rel="canonical" href="https://engelli.me/"><meta property="og:title" content="ÖTV Muaf Araçlar ve Kira Hesaplama | Engelli.me"><meta property="og:description" content="Güncel ÖTV muaf araç liste fiyatları ve hesaplanmış fiyatlar."><meta property="og:url" content="https://engelli.me/"><meta property="og:type" content="website">
<style>
:root{--ink:#182234;--muted:#697386;--blue:#1769e0;--blue-dark:#0e4faf;--line:#e4e8ef;--soft:#f5f7fa;--soft-blue:#edf4ff;--white:#fff;--green:#14804a;--shadow:0 16px 45px rgba(20,32,55,.08)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f4f6f9;color:var(--ink);font-family:Inter,Aptos,"Segoe UI",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
button,input,select,textarea{font:inherit}.app{width:min(1180px,calc(100% - 48px));margin:28px auto 48px;background:var(--white);border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow);overflow:hidden}
.header{display:flex;align-items:center;justify-content:space-between;padding:22px 30px;border-bottom:1px solid var(--line);background:#fff}.brand{font-size:24px;font-weight:850;letter-spacing:-.6px}.brand span{color:var(--blue)}.header-note{font-size:12px;color:var(--muted)}
.page{display:none}.page.on{display:block}.home{padding:30px}.hero{padding:30px;border:1px solid #dce6f6;border-radius:24px;background:linear-gradient(135deg,#f8fbff,#edf4ff)}.eyebrow{font-size:12px;font-weight:800;color:var(--blue);letter-spacing:.08em;text-transform:uppercase;margin-bottom:9px}.hero h1{margin:0;font-size:36px;line-height:1.08;letter-spacing:-1.2px}.hero p{margin:10px 0 0;max-width:680px;color:var(--muted);font-size:15px;line-height:1.55}.hero-stats{display:flex;gap:10px;margin-top:24px}.stat{background:#fff;border:1px solid #dfe7f3;border-radius:16px;padding:13px 17px;min-width:150px}.stat small{display:block;color:var(--muted);font-size:11px}.stat b{display:block;margin-top:4px;font-size:22px;letter-spacing:-.3px}.section{margin-top:28px}.section-head{display:flex;align-items:end;justify-content:space-between;gap:15px;margin-bottom:12px}.section-head h2{margin:0;font-size:21px;letter-spacing:-.4px}.section-head p{margin:0;color:var(--muted);font-size:12px}
.vehicle-grid{display:grid;grid-template-columns:repeat(2,minmax(0,360px));justify-content:center;gap:8px}.vehicle-card{border:1px solid var(--line);border-radius:12px;background:#fff;padding:11px 13px}.vehicle-card .brandline{font-size:10px;color:var(--muted);font-weight:750}.vehicle-card h3{margin:3px 0 1px;font-size:14px;line-height:1.2}.vehicle-card .trim{font-size:11px;color:var(--muted);min-height:15px}.vehicle-card .price-line{display:flex;justify-content:space-between;align-items:end;gap:10px;margin-top:9px;padding-top:8px;border-top:1px solid var(--line)}.vehicle-card .price-label{font-size:9px;color:var(--muted)}.vehicle-card .price{font-size:14px;font-weight:850}.vehicle-card .arrow{display:none}
.more{display:flex;justify-content:center;margin-top:14px}.primary,.secondary{border:0;border-radius:12px;padding:12px 17px;font-weight:800;cursor:pointer}.primary{background:var(--blue);color:#fff}.primary:hover{background:var(--blue-dark)}.secondary{background:var(--soft-blue);color:var(--blue)}
.tools{margin-top:30px}.tool-grid{display:none;grid-template-columns:repeat(3,1fr);gap:12px}.tools.open .tool-grid{display:grid}.tool{display:flex;align-items:center;gap:13px;border:1px solid var(--line);border-radius:16px;padding:17px;background:#fff;cursor:pointer}.tool-icon{width:42px;height:42px;flex:0 0 42px;border-radius:12px;background:var(--soft-blue);display:grid;place-items:center;color:var(--blue);font-weight:900}.tool b{font-size:14px}.tool small{display:block;margin-top:3px;color:var(--muted);font-size:11px}
.footer{padding:20px 30px;border-top:1px solid var(--line);color:var(--muted);font-size:11px;text-align:center}
.page-wrap{padding:30px}.page-head{display:flex;align-items:center;gap:10px;margin-bottom:18px}.back{border:1px solid var(--line);background:#fff;border-radius:11px;width:40px;height:40px;cursor:pointer;font-size:24px}.page-head h1{margin:0;font-size:28px;letter-spacing:-.7px}.panel{border:1px solid var(--line);border-radius:18px;background:#fff;padding:20px;margin-bottom:14px}.summary{background:var(--soft-blue);border-color:#d9e6fb}.chips{display:flex;gap:8px;overflow:auto;padding:2px 1px 8px}.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 14px;white-space:nowrap;font-size:12px;font-weight:750;cursor:pointer}.chip.on{background:var(--blue);border-color:var(--blue);color:#fff}.list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.row{border:1px solid var(--line);border-radius:17px;padding:17px;background:#fff}.rowtop{display:flex;justify-content:space-between;gap:15px}.row .tag{background:#e8f7ef;color:var(--green);border-radius:999px;padding:5px 9px;height:max-content;font-size:10px;font-weight:800}.name{font-size:17px;font-weight:850}.meta{font-size:12px;color:var(--muted);margin-top:4px}.price{margin-top:14px;font-size:11px;color:var(--muted)}.price b{display:block;color:var(--ink);font-size:18px;margin-top:2px}.note{font-size:11px;color:var(--muted);line-height:1.5;margin-top:9px}.field{display:block;margin:12px 0 6px;font-size:12px;font-weight:800}.input,select,textarea{width:100%;border:1px solid #d9dee8;border-radius:12px;padding:12px 13px;background:#fff}.btn{width:100%;border:0;border-radius:12px;padding:13px;background:var(--blue);color:#fff;font-weight:800;cursor:pointer;margin-top:12px}.green{background:var(--green)}.result{display:none;margin-top:12px;border-radius:15px;background:var(--soft-blue);padding:16px}.result .big{font-size:27px;font-weight:900;color:var(--blue);text-align:center;margin:7px 0}.filebox{position:relative;border:2px dashed #d5dbe5;border-radius:14px;padding:18px;text-align:center;margin:10px 0;color:var(--muted);font-size:12px}.filebox input{position:absolute;inset:0;opacity:0;width:100%;height:100%}.bottom-home{display:none}
@media(max-width:900px){.vehicle-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.tool-grid{grid-template-columns:1fr 1fr}}
@media(max-width:640px){body{background:#fff}.app{width:100%;margin:0;border:0;border-radius:0;box-shadow:none;min-height:100vh}.header{padding:17px 16px}.brand{font-size:22px}.header-note{font-size:10px}.home,.page-wrap{padding:18px 16px 80px}.hero{padding:20px;border-radius:20px}.hero h1{font-size:28px}.hero p{font-size:13px}.hero-stats{grid-template-columns:1fr 1fr;gap:8px}.stat:last-child{grid-column:1/-1;position:static;width:auto;min-width:0;padding:15px 17px}.stat:last-child small{font-size:11px}.stat:last-child b{font-size:20px;margin-top:4px}.stat b{font-size:20px}.section{margin-top:24px}.section-head h2{font-size:19px}.vehicle-grid{grid-template-columns:1fr;gap:9px}.vehicle-card{padding:15px}.vehicle-card .price-line{margin-top:13px;padding-top:11px}.tool-grid{grid-template-columns:1fr}.tool{padding:15px}.page-head h1{font-size:23px}.list{grid-template-columns:1fr}.row{padding:15px}.bottom-home{display:block;position:fixed;left:50%;bottom:12px;transform:translateX(-50%);border:1px solid var(--line);background:#fff;color:var(--blue);border-radius:999px;padding:10px 17px;font-weight:850;box-shadow:0 8px 25px rgba(0,0,0,.12);z-index:20}}
</style></head><body><main class="app">
<header class="header"><div class="brand">Engelli<span>.me</span></div></header>
<section id="home" class="page on"><div class="home">
<div class="hero"><h1>Güncel ÖTV muaf araçlar</h1><p>Liste fiyatları ve hesaplanmış fiyatlar tek yerde. Uygun araçları marka ve paket bazında inceleyebilirsiniz.</p><div class="hero-stats"><div class="stat"><small>Uygun paket</small><b id="heroCount">—</b></div><div class="stat"><small>Marka</small><b id="heroBrands">—</b></div></div></div>
<div class="section"><div class="section-head"><div><h2>Güncel ÖTV muaf araçlar</h2></div><div id="heroTime" style="font-size:10px;color:var(--muted);text-align:right;white-space:nowrap">Son araştırma saati: —</div></div><div id="homeVehicles" class="vehicle-grid"></div><div class="more"><button class="primary" onclick="openPage(&quot;otv&quot;)">Tüm araçları gör →</button></div></div>
<div class="tools" id="helpers"><div class="section-head" onclick="toggleHelpers()" style="cursor:pointer"><div><h2>Yardımcılar</h2><p>Tek dokunuşla açabilirsiniz</p></div><div style="color:var(--blue);font-size:20px;font-weight:900">＋</div></div><div class="tool-grid"><div class="tool" onclick="openPage('kira')"><div class="tool-icon">₺</div><div><b>Kira Hesaplama</b><small>TÜFE ile kira artışını hesapla</small></div></div><div class="tool" onclick="openPage('excel')"><div class="tool-icon">X</div><div><b>Excel İşlemleri</b><small>Düşeyara, birleştirme ve pivot</small></div></div><div class="tool" onclick="openPage('pdfexcel')"><div class="tool-icon">PDF</div><div><b>PDF → Excel</b><small>PDF içeriğini Excel'e aktar</small></div></div></div></div>
</div></section>
<section id="otv" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h1>ÖTV muaf araçlar</h1></div><div class="panel summary"><b id="otvSummary">Yükleniyor…</b><div class="note">2026 üst limit: <b id="otvLimit">—</b> · Yerli katkı oranı en az %40.</div></div><div id="otvChips" class="chips"></div><div id="otvList" class="list"></div></div></section>
<section id="kira" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h1>Kira Hesaplama</h1></div><div class="panel"><form onsubmit="kiraHesapla(event)"><label class="field">Mevcut kira</label><input id="mevcut-kira" class="input" type="number" min="1" step=".01" placeholder="Örn: 12000" required><label class="field">Kira yenileme ayı</label><select id="yenileme-ayi" required><option value="">Ay seç</option><option value="1">Ocak</option><option value="2">Şubat</option><option value="3">Mart</option><option value="4">Nisan</option><option value="5">Mayıs</option><option value="6">Haziran</option><option value="7">Temmuz</option><option value="8">Ağustos</option><option value="9">Eylül</option><option value="10">Ekim</option><option value="11">Kasım</option><option value="12">Aralık</option></select><button id="kira-btn" class="btn">Hesapla</button></form><div id="kira-result" class="result"></div></div></div></section>
<section id="excel" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h1>Excel İşlemleri</h1></div><div class="panel"><form action="/excel-islem" method="post" enctype="multipart/form-data"><div class="filebox">＋ 1. Excel (Ana Dosya)<input type="file" name="file1" accept=".xlsx,.xls" required></div><div class="filebox">＋ 2. Excel (Referans Dosyası)<input type="file" name="file2" accept=".xlsx,.xls" required></div><label class="field">İşlem</label><textarea name="komut" placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap." required></textarea><button class="btn">Excel işlemini başlat</button></form></div></div></section>
<section id="pdfexcel" class="page"><div class="page-wrap"><div class="page-head"><button class="back" onclick="openPage('home')">‹</button><h1>PDF → Excel</h1></div><div class="panel"><form action="/pdf-excel-islem" method="post" enctype="multipart/form-data"><div class="filebox"><span id="pdfFileName">PDF seçilmedi — PDF dosyasını seç</span><input type="file" name="pdf_file" accept=".pdf" required onchange="pdfSecildi(this)"></div><button class="btn green">PDF'i Excel'e çevir</button></form></div></div></section>
<footer class="footer">Engelli.me · Güncel veriler resmi kaynaklardan kontrol edilir.</footer><button class="bottom-home" onclick="openPage('home')">⌂ Ana Sayfa</button></main>
<script>
let otvData=/*INITIAL_OTV_DATA*/{},activeBrand=null;if(!otvData.vehicles)otvData={vehicles:[],limit:2873900};
function openPage(id){document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));document.getElementById(id).classList.add('on');scrollTo(0,0);if(id==='otv')renderOTV()}
function tl(v){return Number(v||0).toLocaleString('tr-TR')+' ₺'}
function otvRateFor(v){let p=Number(v.price||0),b=(v.brand||'').toUpperCase(),m=(v.model||'').toUpperCase();if(!p)return null;let solve=(rules)=>{for(let [r,min,max] of rules){let base=p/1.20/(1+r);if(base>min&&(max==null||base<=max))return r}return null};if(b==='TOGG')return solve([[.25,0,1650000],[.55,1650000,null]]);if(b==='TOYOTA'&&m.includes('C-HR'))return solve([[.70,0,1250000],[.80,1250000,null]]);if(b==='TOYOTA'&&m.includes('COROLLA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]]);if(b==='FIAT'&&m.includes('ULYSSE'))return solve([[1.50,0,1650000],[1.70,1650000,null]]);if(b==='FIAT'&&m.includes('EGEA'))return solve([[.75,0,850000],[.80,850000,1100000],[.90,1100000,1650000],[1.00,1650000,null]])||solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]]);return solve([[.70,0,650000],[.75,650000,900000],[.80,900000,1100000],[.90,1100000,null]])}
function exemptPrice(v){let r=otvRateFor(v);return r==null?null:Math.round(Number(v.price)/(1+r))}
function verifiedRow(v){let ep=exemptPrice(v);return '<div class="row"><div class="rowtop"><div><div class="name">'+(v.brand||'')+' '+(v.model||'')+'</div><div class="meta">'+(v.trim||'')+'</div></div><span class="tag">Uygun</span></div><div class="price">Liste Fiyatı<b>'+tl(v.price)+'</b></div>'+(ep?'<div class="price">Hesaplanmış ÖTV Muaf Fiyat<b>'+tl(ep)+'</b></div>':'')+'<div class="note">Yerlilik: %'+(v.locality||'—')+' · Kaynak: '+(v.source_name||v.brand)+' · Son kontrol: '+(v.checked_at||'—')+'</div></div>'}
function allBrands(){return [...new Set((otvData.vehicles||[]).map(v=>v.brand).filter(Boolean))]}
function buttons(){let bs=allBrands();if(activeBrand&&!bs.includes(activeBrand))activeBrand=null;let el=document.getElementById('otvChips');el.innerHTML=bs.map(b=>'<button class="chip '+(b===activeBrand?'on':'')+'" data-brand="'+String(b).replace(/"/g,'&quot;')+'">'+b+'</button>').join('');el.querySelectorAll('.chip').forEach(btn=>btn.addEventListener('click',()=>setBrand(btn.dataset.brand)))}
function setBrand(b){activeBrand=activeBrand===b?null:b;renderOTV()}
function renderHomeVehicles(){let el=document.getElementById("homeVehicles"),all=(otvData.vehicles||[]).filter(v=>Number(v.price)>0),byModel={};all.forEach(v=>{let key=((v.brand||"")+" "+(v.model||"")).trim().toUpperCase();if(!byModel[key]||Number(v.price)<Number(byModel[key].price))byModel[key]=v});let vs=Object.values(byModel).sort((a,b)=>Number(a.price)-Number(b.price)).slice(0,6);el.innerHTML=vs.length?vs.map(v=>'<div class="vehicle-card"><div class="brandline">'+(v.brand||'')+'</div><h3>'+(v.model||'')+'</h3><div class="trim">'+(v.trim||'')+'</div><div class="price-line"><div><div class="price-label">ÖTV muaf fiyatı</div><div class="price">'+tl(v.price)+'</div></div></div></div>').join(''):'<div class="panel">Araç listesi yükleniyor…</div>'}
function toggleHelpers(){document.getElementById("helpers").classList.toggle("open")}
function renderHome(){renderHomeVehicles();let c=document.getElementById('heroCount'),b=document.getElementById('heroBrands'),t=document.getElementById('heroTime');c.textContent=(otvData.vehicles||[]).length+' paket';b.textContent=allBrands().length+' marka';t.textContent=otvData.updated_time?'Son araştırma saati: '+otvData.updated_time:'Son araştırma saati: —'}
function pdfSecildi(input){let el=document.getElementById('pdfFileName');el.textContent=input.files&&input.files.length?'✓ PDF seçildi: '+input.files[0].name:'PDF seçilmedi — PDF dosyasını seç'}
function renderOTV(){document.getElementById('otvLimit').textContent=tl(otvData.limit);buttons();let rows=(otvData.vehicles||[]).filter(v=>!activeBrand||v.brand===activeBrand);document.getElementById('otvSummary').textContent=rows.length+' uygun paket · Son fiyat kontrolü '+(otvData.updated_at||'—');document.getElementById('otvList').innerHTML=rows.length?rows.map(verifiedRow).join(''):'<div class="panel">Bu markada uygun ve fiyatı doğrulanmış paket bulunamadı.</div>'}
async function loadOTV(){try{let r=await fetch('/api/otv');otvData=await r.json();renderHome()}catch(e){}}
async function kiraHesapla(e){e.preventDefault();let b=document.getElementById('kira-btn'),res=document.getElementById('kira-result');b.disabled=true;b.textContent='Hesaplanıyor...';res.style.display='block';res.innerHTML='Güncel TÜFE kontrol ediliyor...';try{let body=new URLSearchParams();body.append('mevcut_kira',document.getElementById('mevcut-kira').value);body.append('yenileme_ayi',document.getElementById('yenileme-ayi').value);let r=await fetch('/kira-hesapla',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});let d=await r.json();if(!r.ok)throw Error(d.detail||'Hesaplama yapılamadı.');res.innerHTML='<div class="note" style="text-align:center">12 aylık ortalama TÜFE</div><div class="big">%'+d.oran+'</div><div class="note" style="text-align:center">Yeni kira</div><div class="big">'+d.yeni_kira+'</div><div class="note">'+d.durum+'</div>'}catch(x){res.innerHTML='<div class="note">'+x.message+'</div>'}finally{b.disabled=false;b.textContent='Hesapla'}}
renderHome();loadOTV();
</script></body></html>'''


if __name__ == "__main__":
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=int(os.environ.get("PORT",8000)), reload=False)
