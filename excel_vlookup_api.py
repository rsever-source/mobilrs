import io
import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

app = FastAPI(title="Excel Mobil VLOOKUP & Pivot API")

# Geçici dosya kayıt dizini
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Excel Mobil Sihirbazı</title>
        <style>
            :root {
                --bg-color: #f4f7f6;
                --card-bg: #ffffff;
                --primary: #1e3a8a;
                --primary-hover: #172554;
                --accent: #0ea5e9;
                --text-color: #334155;
                --border-color: #cbd5e1;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background-color: var(--bg-color); color: var(--text-color); padding: 15px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
            .container { width: 100%; max-width: 500px; background: var(--card-bg); border-radius: 16px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05); overflow: hidden; }
            .header { background: var(--primary); color: white; padding: 24px 20px; text-align: center; }
            .header h1 { font-size: 20px; font-weight: 700; margin-bottom: 6px; }
            .header p { font-size: 13px; opacity: 0.8; }
            .tabs { display: flex; background: #e2e8f0; padding: 4px; }
            .tab-btn { flex: 1; background: none; border: none; padding: 12px; font-weight: 600; font-size: 14px; color: #64748b; cursor: pointer; border-radius: 8px; transition: all 0.2s; }
            .tab-btn.active { background: white; color: var(--primary); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .form-content { padding: 20px; }
            .form-section { display: none; }
            .form-section.active { display: block; }
            .form-group { margin-bottom: 18px; }
            .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #475569; }
            .file-input-wrapper { position: relative; border: 2px dashed var(--border-color); border-radius: 10px; padding: 15px; text-align: center; background: #f8fafc; cursor: pointer; transition: border-color 0.2s; }
            .file-input-wrapper:hover { border-color: var(--accent); }
            .file-input-wrapper input[type="file"] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
            .file-msg { font-size: 13px; color: #64748b; word-break: break-all; }
            input[type="text"] { width: 100%; padding: 12px; border: 1px solid var(--border-color); border-radius: 10px; font-size: 14px; outline: none; transition: border-color 0.2s; }
            input[type="text"]:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.15); }
            .btn-submit { width: 100%; background: var(--primary); color: white; border: none; padding: 14px; font-size: 15px; font-weight: 600; border-radius: 10px; cursor: pointer; transition: background 0.2s; margin-top: 10px; box-shadow: 0 4px 12px rgba(30, 58, 138, 0.15); }
            .btn-submit:hover { background: var(--primary-hover); }
            .footer-info { text-align: center; font-size: 11px; color: #94a3b8; margin-top: 15px; }
        </style>
    </head>
    <body>

    <div class="container">
        <div class="header">
            <h1>Excel Mobil Sihirbazı</h1>
            <p>Düşeyara (Merge) ve Pivot işlemlerini mobilden saniyeler içinde yapın</p>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('vlookup')">Düşeyara (VLOOKUP)</button>
            <button class="tab-btn" onclick="switchTab('pivot')">Pivot Tablo</button>
        </div>
        
        <div class="form-content">
            <!-- DÜŞEYARA FORMU -->
            <form id="vlookup-form" class="form-section active" action="/vlookup" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Ana Dosya (Verilerin Ekleneceği Dosya)</label>
                    <div class="file-input-wrapper">
                        <span class="file-msg" id="msg-main">Excel Dosyası Seç (.xlsx, .xls)</span>
                        <input type="file" name="file_main" accept=".xlsx, .xls" required onchange="updateFileName(this, 'msg-main')">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Referans Dosya (Arama Yapılacak Kaynak)</label>
                    <div class="file-input-wrapper">
                        <span class="file-msg" id="msg-ref">Excel Dosyası Seç (.xlsx, .xls)</span>
                        <input type="file" name="file_ref" accept=".xlsx, .xls" required onchange="updateFileName(this, 'msg-ref')">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Ana Dosyadaki Ortak Sütun Adı (Key)</label>
                    <input type="text" name="key_main" placeholder="Örn: Musteri_ID veya Barkod" required>
                </div>
                
                <div class="form-group">
                    <label>Referans Dosyadaki Ortak Sütun Adı (Key)</label>
                    <input type="text" name="key_ref" placeholder="Örn: ID veya Urun_Kodu" required>
                </div>
                
                <button type="submit" class="btn-submit">Birleştir ve İndir</button>
            </form>

            <!-- PIVOT FORMU -->
            <form id="pivot-form" class="form-section" action="/pivot" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Excel Dosyası</label>
                    <div class="file-input-wrapper">
                        <span class="file-msg" id="msg-pivot">Excel Dosyası Seç (.xlsx, .xls)</span>
                        <input type="file" name="file_pivot" accept=".xlsx, .xls" required onchange="updateFileName(this, 'msg-pivot')">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Satır Alanı (Index)</label>
                    <input type="text" name="index_col" placeholder="Gruplanacak sütun, Örn: Bolge, Kategori" required>
                </div>
                
                <div class="form-group">
                    <label>Değer Alanı (Values)</label>
                    <input type="text" name="value_col" placeholder="Hesaplanacak sayısal sütun, Örn: Satis_Tutari" required>
                </div>
                
                <button type="submit" class="btn-submit">Pivot Yap ve İndir</button>
            </form>
            
            <p class="footer-info">Powered by Python Pandas & FastAPI • Mobile Optimized</p>
        </div>
    </div>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.form-section').forEach(form => form.classList.remove('active'));
            
            if(tab === 'vlookup') {
                document.querySelector('.tabs .tab-btn:nth-child(1)').classList.add('active');
                document.getElementById('vlookup-form').classList.add('active');
            } else {
                document.querySelector('.tabs .tab-btn:nth-child(2)').classList.add('active');
                document.getElementById('pivot-form').classList.add('active');
            }
        }

        function updateFileName(input, targetId) {
            const fileName = input.files[0] ? input.files[0].name : "Excel Dosyası Seç";
            document.getElementById(targetId).innerText = fileName;
            document.getElementById(targetId).style.color = "#0f172a";
            document.getElementById(targetId).style.fontWeight = "600";
        }
    </script>
    </body>
    </html>
    """

@app.post("/vlookup")
async def do_vlookup(
    file_main: UploadFile = File(...),
    file_ref: UploadFile = File(...),
    key_main: str = Form(...),
    key_ref: str = Form(...)
):
    try:
        content_main = await file_main.read()
        content_ref = await file_ref.read()
        
        df_main = pd.read_excel(io.BytesIO(content_main))
        df_ref = pd.read_excel(io.BytesIO(content_ref))
        
        df_main.columns = df_main.columns.str.strip()
        df_ref.columns = df_ref.columns.str.strip()
        
        if key_main not in df_main.columns:
            raise HTTPException(status_code=400, detail=f"Ana dosyada '{key_main}' sütunu bulunamadı!")
        if key_ref not in df_ref.columns:
            raise HTTPException(status_code=400, detail=f"Referans dosyada '{key_ref}' sütunu bulunamadı!")
            
        result_df = pd.merge(df_main, df_ref, left_on=key_main, right_on=key_ref, how="left")
        
        output_filepath = os.path.join(OUTPUT_DIR, "vlookup_sonuc.xlsx")
        result_df.to_excel(output_filepath, index=False)
        
        return FileResponse(output_filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="duseyara_sonuc.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata oluştu: {str(e)}")

@app.post("/pivot")
async def do_pivot(
    file_pivot: UploadFile = File(...),
    index_col: str = Form(...),
    value_col: str = Form(...)
):
    try:
        content = await file_pivot.read()
        df = pd.read_excel(io.BytesIO(content))
        df.columns = df.columns.str.strip()
        
        if index_col not in df.columns or value_col not in df.columns:
            raise HTTPException(status_code=400, detail="Belirtilen sütun isimleri dosyada bulunamadı!")
            
        pivot_df = pd.pivot_table(df, values=value_col, index=index_col, aggfunc='sum').reset_index()
        
        output_filepath = os.path.join(OUTPUT_DIR, "pivot_sonuc.xlsx")
        pivot_df.to_excel(output_filepath, index=False)
        
        return FileResponse(output_filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="pivot_sonuc.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata oluştu: {str(e)}")

if __name__ == "__main__":
    # Render'ın port ayarıyla tam uyumlu çalışma alanı
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=port, reload=False)