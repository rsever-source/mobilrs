import io
import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

app = FastAPI(title="RdvAsistan - Akıllı Mobil Platform")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# GELECEKTEKİ DİĞER PROJELERİN İÇİN BURAYA YENİ SAYFALAR/HİZMETLER EKLEYEBİLİRSİN
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RdvAsistan - Akıllı Excel Hub</title>
        <style>
            :root {
                --bg-color: #f1f5f9;
                --card-bg: #ffffff;
                --primary: #0f172a;
                --accent: #3b82f6;
                --text: #1e293b;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
            body { background: var(--bg-color); color: var(--text); padding: 15px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
            .container { width: 100%; max-width: 500px; background: var(--card-bg); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden; }
            .header { background: var(--primary); color: white; padding: 30px 20px; text-align: center; }
            .header h1 { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
            .header p { font-size: 13px; opacity: 0.7; margin-top: 5px; }
            .content { padding: 25px; }
            .file-box { border: 2px dashed #cbd5e1; border-radius: 12px; padding: 12px; margin-bottom: 12px; background: #f8fafc; position: relative; text-align: center; }
            .file-box input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer; }
            .file-label { font-size: 13px; color: #64748b; font-weight: 600; }
            .command-area { margin-top: 15px; }
            textarea { width: 100%; height: 100px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px; font-size: 14px; resize: none; outline: none; }
            textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15); }
            .btn-run { width: 100%; background: var(--accent); color: white; border: none; padding: 15px; font-size: 16px; font-weight: 700; border-radius: 12px; cursor: pointer; margin-top: 15px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
            .nav-future { display: flex; justify-content: space-around; margin-top: 20px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; }
        </style>
    </head>
    <body>
    <div class="container">
        <div class="header">
            <h1>RdvAsistan AI</h1>
            <p>Dosyaları yükle ve ne yapacağını Türkçe emret</p>
        </div>
        <div class="content">
            <form action="/yapay-zeka-islem" method="post" enctype="multipart/form-data">
                
                <!-- 3 Adet Opsiyonel Dosya Slotu (Mobilde seçimi rahatlatır) -->
                <div class="file-box">
                    <span class="file-label" id="lbl1">＋ 1. Excel Dosyası (Ana Dosya)</span>
                    <input type="file" name="file1" accept=".xlsx, .xls" onchange="document.getElementById('lbl1').innerText = this.files[0].name">
                </div>
                <div class="file-box">
                    <span class="file-label" id="lbl2">＋ 2. Excel Dosyası (Referans/Pivot Dosyası)</span>
                    <input type="file" name="file2" accept=".xlsx, .xls" onchange="document.getElementById('lbl2').innerText = this.files[0].name">
                </div>
                <div class="file-box">
                    <span class="file-label" id="lbl3">＋ 3. Excel Dosyası (Yedek Slot)</span>
                    <input type="file" name="file3" accept=".xlsx, .xls" onchange="document.getElementById('lbl3').innerText = this.files[0].name">
                </div>

                <div class="command-area">
                    <textarea name="komut" placeholder="Örn: 1. ve 2. dosyayı Musteri_ID sütunundan birleştir düşeyara yap." required></textarea>
                </div>

                <button type="submit" class="btn-run">Komutu Çalıştır</button>
            </form>
            
            <!-- İLERİDE EKLENECEK DİĞER MODÜLLER İÇİN BURASI HAZIR VİTRİN -->
            <div class="nav-future">
                <span>📊 Excel Motoru (Aktif)</span>
                <span>📄 PDF Çevirici (Yakında)</span>
                <span>🖼️ Görsel İşleme (Yakında)</span>
            </div>
        </div>
    </div>
    </body>
    </html>
    """

@app.post("/yapay-zeka-islem")
async def akilli_motor(
    komut: str = Form(...),
    file1: UploadFile = File(None),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None)
):
    try:
        komut_lower = komut.lower()
        
        # 1. DOSYALARI SORGULA VE DATAFRAME'E ÇEVİR
        dfs = {}
        if file1 and file1.filename:
            dfs[1] = pd.read_excel(io.BytesIO(await file1.read()))
            dfs[1].columns = dfs[1].columns.str.strip()
        if file2 and file2.filename:
            dfs[2] = pd.read_excel(io.BytesIO(await file2.read()))
            dfs[2].columns = dfs[2].columns.str.strip()
        if file3 and file3.filename:
            dfs[3] = pd.read_excel(io.BytesIO(await file3.read()))
            dfs[3].columns = dfs[3].columns.str.strip()

        if not dfs:
            raise HTTPException(status_code=400, detail="En az bir dosya yüklemelisin Rıdo!")

        output_path = os.path.join(OUTPUT_DIR, "asistan_sonuc.xlsx")

        # 2. AKILLI NİYET ANALİZİ (INTENT ROUTING)
        # Eğer metinde düşeyara/birleştirme geçiyorsa
        if any(x in komut_lower for x in ["düşeyara", "vlookup", "birleştir", "merge"]):
            if len(dfs) < 2:
                raise HTTPException(status_code=400, detail="Düşeyara için en az 2 dosya yüklemelisin!")
            
            # Komutun içinden hangi sütun isminin geçtiğini akıllıca bulma
            ortak_sutun = None
            for col in dfs[1].columns:
                if col.lower() in komut_lower:
                    ortak_sutun = col
                    break
            
            if not ortak_sutun:
                # Eğer yazıda sütun bulamazsa iki dosyadaki ilk kesişen ortak sütunu kendi bulur
                ortak_set = set(dfs[1].columns).intersection(set(dfs[2].columns))
                if ortak_set:
                    ortak_sutun = list(ortak_set)[0]
                else:
                    raise HTTPException(status_code=400, detail="Yazdığın komutta ortak sütun adını bulamadım ve dosya sütunları eşleşmiyor.")

            # İşlemi yap ve kaydet
            sonuc_df = pd.merge(dfs[1], dfs[2], on=ortak_sutun, how="left")
            sonuc_df.to_excel(output_path, index=False)

        # Eğer metinde pivot/özet geçiyorsa
        elif any(x in komut_lower for x in ["pivot", "özet", "grupla", "toplam"]):
            target_df = dfs[1] # Varsayılan ilk dosyayı işler
            
            # Metinden index ve değer sütunlarını tahmin etme
            index_col = None
            value_col = None
            
            for col in target_df.columns:
                if col.lower() in komut_lower:
                    # Sayısal veri tipiyse değer alanı, metinse satır alanı yapalım
                    if pd.api.types.is_numeric_dtype(target_df[col]) and not value_col:
                        value_col = col
                    elif not index_col:
                        index_col = col
            
            # Bulamazsa ilk iki sütunu baz alır
            if not index_col: index_col = target_df.columns[0]
            if not value_col: value_col = target_df.columns[1]

            pivot_df = pd.pivot_table(target_df, values=value_col, index=index_col, aggfunc='sum').reset_index()
            pivot_df.to_excel(output_path, index=False)
        
        else:
            raise HTTPException(status_code=400, detail="Ne yapmak istediğini tam anlayamadım. Komutta 'düşeyara' veya 'pivot' kelimelerini geçirmeyi dene.")

        return FileResponse(output_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="asistan_sonuc.xlsx")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sihirbaz Hatası: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=port, reload=False)
