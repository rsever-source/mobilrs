import io
import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from PIL import Image
from typing import List
import pdfplumber

app = FastAPI(title="Rid Asistan")

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
        <title>Rdv Asistan</title>
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
            .header h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
            
            /* SEKME/MENÜ BUTONLARI */
            .tabs { display: flex; background: #e2e8f0; padding: 5px; gap: 5px; }
            .tab-btn { flex: 1; border: none; background: none; padding: 12px 5px; font-size: 12px; font-weight: 700; color: #64748b; cursor: pointer; border-radius: 10px; transition: all 0.2s; text-align: center; }
            .tab-btn.active { background: var(--card-bg); color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
            
            .content { padding: 25px; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            
            .file-box { border: 2px dashed #cbd5e1; border-radius: 12px; padding: 15px; margin-bottom: 12px; background: #f8fafc; position: relative; text-align: center; }
            .file-box input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer; }
            .file-label { font-size: 13px; color: #64748b; font-weight: 600; }
            
            .command-area { margin-top: 15px; }
            textarea { width: 100%; height: 90px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px; font-size: 14px; resize: none; outline: none; }
            textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15); }
            
            .btn-run { width: 100%; background: var(--accent); color: white; border: none; padding: 15px; font-size: 16px; font-weight: 700; border-radius: 12px; cursor: pointer; margin-top: 15px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
            .btn-pdf-excel { background: #10b981; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); }
            .btn-image-pdf { background: #6366f1; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
            
            .info-text { font-size: 12px; color: #64748b; margin-bottom: 15px; line-height: 1.5; text-align: center; background: #f8fafc; padding: 10px; border-radius: 8px; }
        </style>
        <script>
            function switchTab(event, tabId) {
                var contents = document.getElementsByClassName("tab-content");
                for (var i = 0; i < contents.length; i++) {
                    contents[i].classList.remove("active");
                }
                var buttons = document.getElementsByClassName("tab-btn");
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].classList.remove("active");
                }
                document.getElementById(tabId).classList.add("active");
                event.currentTarget.classList.add("active");
            }
        </script>
    </head>
    <body>
    <div class="container">
        <div class="header">
            <h1>Rdv Asistan</h1>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab(event, 'excel-tab')">📊 Excel</button>
            <button class="tab-btn" onclick="switchTab(event, 'pdf-tab')">📄 Resim -> PDF</button>
            <button class="tab-btn" onclick="switchTab(event, 'pdf2excel-tab')">🟢 PDF -> Excel</button>
        </div>
        
        <div class="content">
            
            <div id="excel-tab" class="tab-content active">
                <form action="/excel-islem" method="post" enctype="multipart/form-data">
                    <div class="file-box">
                        <span class="file-label" id="xl1">＋ 1. Excel (Ana Dosya)</span>
                        <input type="file" name="file1" accept=".xlsx, .xls" required onchange="document.getElementById('xl1').innerText = this.files[0].name">
                    </div>
                    <div class="file-box">
                        <span class="file-label" id="xl2">＋ 2. Excel (Referans Dosyası)</span>
                        <input type="file" name="file2" accept=".xlsx, .xls" required onchange="document.getElementById('xl2').innerText = this.files[0].name">
                    </div>
                    <div class="command-area">
                        <textarea name="komut" placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap." required></textarea>
                    </div>
                    <button type="submit" class="btn-run">Excel İşlemini Başlat</button>
                </form>
            </div>
            
            <div id="pdf-tab" class="tab-content">
                <form action="/resim-pdf-islem" method="post" enctype="multipart/form-data">
                    <div class="info-text">Galeriden istediğin kadar fotoğrafı aynı anda seçip tek bir PDF yapabilirsin Rıdo.</div>
                    <div class="file-box">
                        <span class="file-label" id="img1">＋ Fotoğrafları Seç (Çoklu Seçim)</span>
                        <input type="file" name="images" accept=".png, .jpg, .jpeg" multiple required onchange="document.getElementById('img1').innerText = this.files.length + ' fotoğraf seçildi'">
                    </div>
                    <button type="submit" class="btn-run btn-image-pdf">Sıkıştırıp PDF Yap</button>
                </form>
            </div>
            
            <div id="pdf2excel-tab" class="tab-content">
                <form action="/pdf-excel-islem" method="post" enctype="multipart/form-data">
                    <div class="info-text">İçinde tablo veya liste olan bir PDF dosyasını yükle, anında düzenlenebilir Excel'e çevirelim Rıdo.</div>
                    <div class="file-box">
                        <span class="file-label" id="pdfsrc">＋ Dönüştürülecek PDF Dosyasını Seç</span>
                        <input type="file" name="pdf_file" accept=".pdf" required onchange="document.getElementById('pdfsrc').innerText = this.files[0].name">
                    </div>
                    <button type="submit" class="btn-run btn-pdf-excel">PDF'i Excel'e Çevir</button>
                </form>
            </div>

        </div>
    </div>
    </body>
    </html>
    """

@app.post("/excel-islem")
async def excel_motor(komut: str = Form(...), file1: UploadFile = File(...), file2: UploadFile = File(...)):
    try:
        komut_lower = komut.lower()
        df_main = pd.read_excel(io.BytesIO(await file1.read()))
        df_ref = pd.read_excel(io.BytesIO(await file2.read()))
        df_main.columns = df_main.columns.str.strip()
        df_ref.columns = df_ref.columns.str.strip()
        
        # DÜŞEYARA SENARYOSU
        if any(x in komut_lower for x in ["düşeyara", "vlookup", "birleştir", "merge"]):
            ortak_sutun = None
            for col in df_main.columns:
                if col.lower() in komut_lower:
                    ortak_sutun = col
                    break
            if not ortak_sutun:
                ortak_set = list(set(df_main.columns).intersection(set(df_ref.columns)))
                if ortak_set: ortak_sutun = ortak_set[0]
                else: raise HTTPException(status_code=400, detail="Ortak sütun adını komutta bulamadım.")
            
            result_df = pd.merge(df_main, df_ref, on=ortak_sutun, how="left")
            
        # PIVOT SENARYOSU
        elif any(x in komut_lower for x in ["pivot", "özet", "grupla", "toplam"]):
            index_col, value_col = None, None
            for col in df_main.columns:
                if col.lower() in komut_lower:
                    if pd.api.types.is_numeric_dtype(df_main[col]) and not value_col: value_col = col
                    elif not index_col: index_col = col
            if not index_col: index_col = df_main.columns[0]
            if not value_col: value_col = df_main.columns[1]
            result_df = pd.pivot_table(df_main, values=value_col, index=index_col, aggfunc='sum').reset_index()
        else:
            result_df = df_main

        output_path = os.path.join(OUTPUT_DIR, "excel_sonuc.xlsx")
        result_df.to_excel(output_path, index=False)
        return FileResponse(output_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="excel_sonuc.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel Hatası: {str(e)}")

@app.post("/resim-pdf-islem")
async def resim_pdf_motor(images: List[UploadFile] = File(...)):
    try:
        pil_images = []
        for f in images:
            if f.filename and any(f.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                img = Image.open(io.BytesIO(await f.read()))
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                pil_images.append(img)
        
        if not pil_images:
            raise HTTPException(status_code=400, detail="Hiç geçerli resim dosyası yüklenmedi Rıdo!")
        
        output_pdf_path = os.path.join(OUTPUT_DIR, "rdv_pdf_sonuc.pdf")
        pil_images[0].save(output_pdf_path, "PDF", save_all=True, append_images=pil_images[1:], quality=65)
        return FileResponse(output_pdf_path, media_type="application/pdf", filename="rdv_pdf_sonuc.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Oluşturma Hatası: {str(e)}")

@app.post("/pdf-excel-islem")
async def pdf_excel_motor(pdf_file: UploadFile = File(...)):
    try:
        pdf_bytes = await pdf_file.read()
        extracted_data = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        extracted_data.append(cleaned_row)
                if not tables:
                    text = page.extract_text()
                    if text:
                        for line in text.split("\n"):
                            if line.strip():
                                extracted_data.append(line.split())
        if not extracted_data:
            raise HTTPException(status_code=400, detail="PDF içerisinden aktarılacak veri bulamadım Rıdo!")
        df = pd.DataFrame(extracted_data)
        output_excel_path = os.path.join(OUTPUT_DIR, "pdf_to_excel_sonuc.xlsx")
        df.to_excel(output_excel_path, index=False, header=False)
        return FileResponse(output_excel_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="pdf_to_excel_sonuc.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF'ten Excel'e Çevirme Hatası: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=port, reload=False)
