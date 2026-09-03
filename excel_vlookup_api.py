import io, os, uuid
from datetime import date
from typing import List
from urllib.parse import urlparse
import pandas as pd, pdfplumber, uvicorn
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from starlette.background import BackgroundTask
from tufe_service import get_current_tufe, save_cache
from otv_service import get_otv_data, refresh_otv_data

app=FastAPI(title="Rdv Asistan")
OUTPUT_DIR="outputs"; os.makedirs(OUTPUT_DIR,exist_ok=True)
MAX_FILE_SIZE=25*1024*1024; MAX_IMAGES_TOTAL_SIZE=100*1024*1024
MONTH_NAMES={1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}

def unique_output_path(ext): return os.path.join(OUTPUT_DIR,f"rdv_{uuid.uuid4().hex}.{ext}")
def delete_file(path):
    try:
        if os.path.exists(path): os.remove(path)
    except Exception: pass
async def read_upload_limited(upload,max_size=MAX_FILE_SIZE):
    data=await upload.read()
    if len(data)>max_size: raise HTTPException(413,f"{upload.filename or 'Dosya'} çok büyük. Maksimum {max_size//(1024*1024)} MB.")
    return data
def check_extension(filename,allowed): return (filename or "").lower().endswith(allowed)
def normalize_column_name(v): return str(v).strip()
def select_join_column(a,b,command):
    common=[c for c in a.columns if c in b.columns]
    if not common: raise HTTPException(400,"İki Excel dosyasında ortak sütun bulunamadı.")
    cl=command.lower()
    for c in common:
        if str(c).lower() in cl: return c
    for p in ["id","kod","code","no","numara","musteri","müşteri","container","konteyner","referans","ref","sicil"]:
        for c in common:
            if p in str(c).lower(): return c
    return common[0]
def find_command_columns(df,command):
    cl=command.lower(); return [c for c in df.columns if str(c).lower() in cl]
def money_tr(v): return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".")+" TL"
def next_renewal_year(m):
    t=date.today(); return t.year if m>=t.month else t.year+1
def previous_month(y,m): return (y-1,12) if m==1 else (y,m-1)

@app.get("/tufe-guncelle")
async def spark_tufe_guncelle(key:str=Query(...),source:str=Query(...),rate:float=Query(...),year:int=Query(...),month:int=Query(...)):
    expected=os.environ.get("SPARK_TUFE_KEY","").strip()
    if not expected: raise HTTPException(500,"SPARK_TUFE_KEY ayarlanmamış.")
    if key!=expected: raise HTTPException(403,"Yetkisiz erişim.")
    p=urlparse(source)
    if (p.hostname or "").lower()!="veriportali.tuik.gov.tr" or not p.path.startswith("/tr/press/"):
        raise HTTPException(400,"Sadece resmi TÜİK haber bülteni kabul edilir.")
    if not 1<=month<=12 or not 2020<=year<=2100 or not 0<rate<200: raise HTTPException(400,"Geçersiz parametre.")
    data={"rate":round(float(rate),2),"year":year,"month":month,"period":f"{MONTH_NAMES[month]} {year}","source":source,"data_mode":"spark"}
    if not save_cache(data): raise HTTPException(500,"Veri Redis'e kaydedilemedi.")
    return JSONResponse({"ok":True,"message":"TÜFE başarıyla kaydedildi.","oran":f"{rate:.2f}".replace(".",","),"donem":data["period"],"source":source})

@app.post("/kira-hesapla")
async def kira_hesapla(mevcut_kira:float=Form(...),yenileme_ayi:int=Form(...)):
    if mevcut_kira<=0 or not 1<=yenileme_ayi<=12: raise HTTPException(400,"Geçerli kira ve yenileme ayı gir.")
    try: tufe=get_current_tufe()
    except Exception as e: raise HTTPException(503,f"Güncel TÜFE verisi alınamadı. {e}")
    rate=float(tufe["rate"]); ty=int(tufe["year"]); tm=int(tufe["month"]); period=str(tufe["period"]); source=str(tufe["source"])
    artis=mevcut_kira*rate/100; yeni=mevcut_kira+artis
    ry=next_renewal_year(yenileme_ayi); target=previous_month(ry,yenileme_ayi); current=(ty,tm)
    if current==target: durum=f"{MONTH_NAMES[yenileme_ayi]} {ry} kira yenilemesi için gerekli {period} TÜFE verisi yayımlanmış. Hesap güncel resmi TÜİK oranıyla yapıldı."
    elif current<target: durum=f"Son resmi TÜFE verisi {period} dönemine ait. {MONTH_NAMES[yenileme_ayi]} {ry} yenilemesi için gerekli veri henüz yayımlanmadı. Şimdilik son resmi oranla hesaplandı."
    else: durum=f"Hesap, TÜİK'in yayımladığı son resmi {period} verisiyle yapıldı."
    return JSONResponse({"oran":f"{rate:.2f}".replace(".",","),"mevcut_kira":money_tr(mevcut_kira),"artis":money_tr(artis),"yeni_kira":money_tr(yeni),"donem":period,"durum":durum,"source":source,"data_mode":tufe.get("data_mode","cache")})

@app.get("/api/otv")
async def api_otv(): return JSONResponse(get_otv_data())
@app.post("/api/otv/yenile")
async def api_otv_yenile(): return JSONResponse(refresh_otv_data(force=True))

@app.get("/",response_class=HTMLResponse)
async def index(): return HTMLResponse(HOME_HTML)

@app.post("/excel-islem")
async def excel_motor(komut:str=Form(...),file1:UploadFile=File(...),file2:UploadFile=File(...)):
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
    except HTTPException: raise
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,f"Excel Hatası: {e}")

@app.post("/resim-pdf-islem")
async def resim_pdf_motor(images:List[UploadFile]=File(...)):
    out=None; pil=[]; total=0
    try:
        for f in images:
            if not f.filename or not check_extension(f.filename,(".jpg",".jpeg",".png")): continue
            d=await read_upload_limited(f); total+=len(d)
            if total>MAX_IMAGES_TOTAL_SIZE: raise HTTPException(413,"Seçilen fotoğrafların toplam boyutu çok büyük. Maksimum 100 MB.")
            im=ImageOps.exif_transpose(Image.open(io.BytesIO(d)))
            if im.mode!="RGB": im=im.convert("RGB")
            pil.append(im.copy()); im.close()
        if not pil: raise HTTPException(400,"Geçerli fotoğraf bulunamadı.")
        out=unique_output_path("pdf"); pil[0].save(out,"PDF",save_all=True,append_images=pil[1:],resolution=150.0)
        return FileResponse(out,media_type="application/pdf",filename="rdv_pdf_sonuc.pdf",background=BackgroundTask(delete_file,out))
    except HTTPException:
        if out: delete_file(out)
        raise
    except Exception as e:
        if out: delete_file(out)
        raise HTTPException(500,f"PDF Hatası: {e}")
    finally:
        for im in pil:
            try: im.close()
            except Exception: pass

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

HOME_HTML=r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>RDV Asistan</title>
<style>
:root{--blue:#0b57e3;--blue2:#1d6cff;--green:#18a957;--ink:#111827;--muted:#6b7280;--line:#e6e9ef;--bg:#f5f7fb}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink)}.app{max-width:520px;margin:auto;min-height:100vh;background:#fff;padding:18px 16px 88px}.top{font-size:28px;font-weight:850;margin:10px 2px 18px}.hero{background:linear-gradient(145deg,var(--blue2),#0745cb);color:#fff;border-radius:22px;padding:18px;box-shadow:0 14px 35px #0b57e32b}.hero h2{margin:0 0 5px;font-size:21px}.sub{font-size:13px;opacity:.9}.herofoot{display:flex;justify-content:space-between;align-items:end;margin:18px 0 14px}.herofoot small{display:block;opacity:.82}.herofoot b{display:block;font-size:24px;margin-top:3px}.hero button{width:100%;border:0;border-radius:12px;padding:12px;background:#fff;color:var(--blue);font-weight:800}.chips{display:flex;gap:8px;overflow:auto;padding:14px 0 8px;scrollbar-width:none}.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:8px 13px;white-space:nowrap;font-weight:700;font-size:12px}.chip.on{background:var(--blue);color:#fff;border-color:var(--blue)}.sec{display:flex;justify-content:space-between;align-items:center;margin:18px 2px 10px}.sec h3{margin:0;font-size:17px}.projects{display:grid;grid-template-columns:1fr 1fr;gap:10px}.p{border:1px solid var(--line);border-radius:17px;padding:14px;display:flex;gap:10px;align-items:center;background:#fff}.ico{width:38px;height:38px;border-radius:11px;background:#eef4ff;display:grid;place-items:center;font-size:20px}.p b{font-size:13px}.p small{display:block;color:var(--muted);font-size:10px;margin-top:3px}.homebtn{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);border:1px solid var(--line);background:#fff;color:var(--blue);border-radius:999px;padding:10px 18px;font-weight:800;box-shadow:0 7px 25px #0001;z-index:9}.page{display:none}.page.on{display:block}.back{border:0;background:none;font-size:25px;padding:4px 8px 4px 0}.pagehead{display:flex;align-items:center;gap:8px;margin-bottom:16px}.pagehead h2{margin:0;font-size:21px}.panel{border:1px solid var(--line);border-radius:18px;padding:15px;margin-bottom:12px}.field{display:block;margin:12px 0 6px;font-size:12px;font-weight:800}.input,select,textarea{width:100%;border:1px solid #d9dee8;border-radius:13px;padding:13px;font-size:16px;background:#fff}textarea{height:88px}.btn{width:100%;border:0;border-radius:13px;padding:14px;background:var(--blue);color:#fff;font-size:15px;font-weight:800;margin-top:12px}.green{background:#168f50}.purple{background:#6857df}.result{display:none;margin-top:12px;border-radius:16px;background:#f3f7ff;padding:16px}.result .big{font-size:28px;font-weight:900;color:var(--blue);text-align:center;margin:8px 0}.list{display:grid;gap:10px}.row{border:1px solid var(--line);border-radius:16px;padding:13px}.rowtop{display:flex;justify-content:space-between;gap:10px}.row .tag{background:#e8f8ee;color:#168143;padding:4px 8px;border-radius:999px;font-size:10px;height:max-content}.row .name{font-weight:850}.row .meta{font-size:11px;color:var(--muted);margin-top:4px;line-height:1.45}.rowprices{display:grid;grid-template-columns:1fr 1fr;margin-top:10px;font-size:10px;color:var(--muted)}.rowprices b{display:block;color:#111;font-size:14px;margin-top:2px}.rowprices .m b{color:var(--green)}.filebox{position:relative;border:2px dashed #d6dbe5;border-radius:14px;padding:18px;text-align:center;margin:10px 0;color:var(--muted);font-size:12px}.filebox input{position:absolute;inset:0;opacity:0;width:100%;height:100%}.note{font-size:11px;color:var(--muted);line-height:1.5;margin-top:8px}
</style></head><body><main class="app">
<section id="home" class="page on"><div class="top">RDV Asistan</div><div class="hero"><h2>🚗 ÖTV Muaf Araçlar</h2><div class="sub">Bakanlık yerlilik verisi + resmî marka fiyatları</div><div class="herofoot"><div><small>Uygun paket</small><b id="heroCount">—</b></div><div style="text-align:right"><small>Son güncelleme</small><b id="heroTime">—</b></div></div><button onclick="openPage('otv')">Tümünü Gör ›</button></div><div class="sec"><h3>Projeler</h3></div><div class="projects"><div class="p" onclick="openPage('kira')"><div class="ico">🏠</div><div><b>Kira Hesaplama</b><small>TÜFE ile kira artışı</small></div></div><div class="p" onclick="openPage('excel')"><div class="ico">📊</div><div><b>Excel</b><small>Düşeyara, birleştirme, pivot</small></div></div><div class="p" onclick="openPage('imgpdf')"><div class="ico">📄</div><div><b>Resim → PDF</b><small>Fotoğrafları tek PDF yap</small></div></div><div class="p" onclick="openPage('pdfexcel')"><div class="ico">🟢</div><div><b>PDF → Excel</b><small>Tablo ve metni Excel'e aktar</small></div></div></div></section>
<section id="otv" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>ÖTV Muaf Araçlar</h2></div><div class="panel"><b id="otvSummary">Yükleniyor…</b><div class="note">2026 üst limit: <b id="otvLimit">—</b> · Yerli katkı oranı en az %40. Paket, motor ve şanzıman ayrı değerlendirilir.</div></div><div id="otvChips" class="chips"></div><div id="otvList" class="list"></div></section>
<section id="kira" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>Kira Hesaplama</h2></div><div class="panel"><form onsubmit="kiraHesapla(event)"><label class="field">Mevcut kira</label><input id="mevcut-kira" class="input" type="number" min="1" step=".01" placeholder="Örn: 12000" required><label class="field">Kira yenileme ayı</label><select id="yenileme-ayi" required><option value="">Ay seç</option><option value="1">Ocak</option><option value="2">Şubat</option><option value="3">Mart</option><option value="4">Nisan</option><option value="5">Mayıs</option><option value="6">Haziran</option><option value="7">Temmuz</option><option value="8">Ağustos</option><option value="9">Eylül</option><option value="10">Ekim</option><option value="11">Kasım</option><option value="12">Aralık</option></select><button id="kira-btn" class="btn">Hesapla</button></form><div id="kira-result" class="result"></div></div></section>
<section id="excel" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>Excel</h2></div><div class="panel"><form action="/excel-islem" method="post" enctype="multipart/form-data"><div class="filebox">＋ 1. Excel (Ana Dosya)<input type="file" name="file1" accept=".xlsx,.xls" required></div><div class="filebox">＋ 2. Excel (Referans Dosyası)<input type="file" name="file2" accept=".xlsx,.xls" required></div><label class="field">İşlem</label><textarea name="komut" placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap." required></textarea><button class="btn">Excel İşlemini Başlat</button></form></div></section>
<section id="imgpdf" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>Resim → PDF</h2></div><div class="panel"><form action="/resim-pdf-islem" method="post" enctype="multipart/form-data"><div class="filebox">＋ Fotoğrafları Seç<input type="file" name="images" accept=".png,.jpg,.jpeg" multiple required></div><button class="btn purple">PDF Yap</button></form></div></section>
<section id="pdfexcel" class="page"><div class="pagehead"><button class="back" onclick="openPage('home')">‹</button><h2>PDF → Excel</h2></div><div class="panel"><form action="/pdf-excel-islem" method="post" enctype="multipart/form-data"><div class="filebox">＋ PDF Dosyasını Seç<input type="file" name="pdf_file" accept=".pdf" required></div><button class="btn green">PDF'i Excel'e Çevir</button></form></div></section><button class="homebtn" onclick="openPage('home')">⌂ &nbsp;Ana Sayfa</button></main>
<script>
let otvData={vehicles:[],limit:2873900},activeBrand=null;
function openPage(id){document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));document.getElementById(id).classList.add('on');scrollTo(0,0);if(id==='otv'){activeBrand=null;renderOTV()}}
function tl(v){return v==null?'—':Number(v).toLocaleString('tr-TR')+' ₺'}
function muaf(v){return v==null?'Hesaplanmıyor':tl(v)}
function row(v){let meta=[v.trim,v.engine,v.transmission,v.fuel].filter(Boolean).join(' · ');return `<div class="row"><div class="rowtop"><div><div class="name">${v.brand} ${v.model}</div><div class="meta">${meta}</div></div><span class="tag">%${Number(v.locality||0).toLocaleString('tr-TR')} yerli</span></div><div class="rowprices"><div>Liste Fiyatı<b>${tl(v.price)}</b></div><div class="m">Hesaplanan Muaf Fiyat<b>${muaf(v.exempt_price)}</b></div></div><div class="note">Kaynak: ${v.source_name||v.brand} · Son kontrol: ${v.checked_at||'—'}</div></div>`}
function buttons(){const bs=[...new Set(otvData.vehicles.map(v=>v.brand))];document.getElementById('otvChips').innerHTML=bs.map(b=>`<button class="chip ${b===activeBrand?'on':''}" onclick="setBrand('${b}')">${b}</button>`).join('')}
function setBrand(b){activeBrand=(activeBrand===b?null:b);renderOTV()}
function renderHome(){document.getElementById('heroCount').textContent=otvData.vehicles.length+' paket';document.getElementById('heroTime').textContent=otvData.updated_time||'—'}
function renderOTV(){document.getElementById('otvLimit').textContent=tl(otvData.limit);document.getElementById('otvSummary').textContent=otvData.vehicles.length+' uygun paket · Son güncelleme '+(otvData.updated_at||'—');buttons();let a=otvData.vehicles.filter(v=>!activeBrand||v.brand===activeBrand);document.getElementById('otvList').innerHTML=a.map(row).join('')||'<div class="panel">Uygun paket bulunamadı.</div>'}
async function loadOTV(){try{let r=await fetch('/api/otv');otvData=await r.json();renderHome()}catch(e){document.getElementById('heroCount').textContent='—'}}
async function kiraHesapla(e){e.preventDefault();let b=document.getElementById('kira-btn'),res=document.getElementById('kira-result');b.disabled=true;b.textContent='Hesaplanıyor...';res.style.display='block';res.innerHTML='Güncel TÜFE kontrol ediliyor...';try{let body=new URLSearchParams();body.append('mevcut_kira',document.getElementById('mevcut-kira').value);body.append('yenileme_ayi',document.getElementById('yenileme-ayi').value);let r=await fetch('/kira-hesapla',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});let d=await r.json();if(!r.ok)throw Error(d.detail||'Hesaplama yapılamadı.');res.innerHTML=`<div class="note" style="text-align:center">12 aylık ortalama TÜFE</div><div class="big">%${d.oran}</div><div class="note" style="text-align:center">Yeni kira</div><div class="big">${d.yeni_kira}</div><div class="note">${d.durum}</div>`}catch(x){res.innerHTML='<div class="note">'+x.message+'</div>'}finally{b.disabled=false;b.textContent='Hesapla'}}
loadOTV();
</script></body></html>'''

if __name__=="__main__":
    uvicorn.run("excel_vlookup_api:app",host="0.0.0.0",port=int(os.environ.get("PORT",8000)),reload=False)
