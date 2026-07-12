import io
import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from PIL import Image

app = FastAPI(title="Rdv Asistan")

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
            .header { background: var(--primary); color: white; padding: 35px 20px; text-align: center; }
            .header h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
            .content { padding: 25px; }
            .file-box { border: 2px dashed #cbd5e1; border-radius: 12px; padding: 12px; margin-bottom: 12px; background: #f8fafc; position: relative; text-align: center; }
            .file-box input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer; }
            .file-label { font-size: 13px; color: #64748b; font-weight: 600; }
            .command-area { margin-top: 15px; }
            textarea { width: 100%; height: 100px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px; font-size: 14px; resize: none; outline: none; }
            textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15); }
            .btn-run { width: 100%; background: var(--accent); color: white; border: none; padding: 15px; font-size: 16px; font-weight: 700; border-radius: 12px; cursor: pointer; margin-top: 15px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
            .footer-tags { display: flex; justify-content: space-around; margin-top: 25px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; font-weight: 600; }
        </style>
    </head>
    <body>
    <div class="container">
        <div class="header">
            <h1>Rdv Asistan</h1>
        </div>
        <div class="content">
            <form action="/yapay-zeka-islem" method="post" enctype="multipart/form-data">
                
                <div class="file-box">
                    <span class="file-label" id="lbl1">＋ 1. Dosya (Excel veya Resim)</span>
                    <input type="file" name="file1" accept=".xlsx, .xls, .png, .jpg, .jpeg" onchange="document.getElementById('lbl1').innerText = this.files[0].name">
                </div>
                <div class="file-box">
                    <span class="file-label" id="lbl2">＋ 2. Dosya (Excel veya Resim)</span>
                    <input type="file" name="file2" accept=".xlsx, .xls, .png, .jpg, .jpeg" onchange="document.getElementById('lbl2').innerText = this.files[0].name">
                </div>
                <div class="file-box">
                    <span class="file-label" id="lbl3">＋ 3. Dosya (Excel veya Resim)</span>
                    <input type="file" name="file3" accept=".xlsx, .xls, .png, .jpg, .jpeg" onchange="document.getElementById('lbl3').innerText = this.files[0].name">
                </div>

                <div class="command-area">
                    <textarea name="komut" placeholder="Ne yapmak istediğini yaz Rıdo...&#10;Örn 1: Dosyaları Musteri_ID sütunundan düşeyara yap.&#10;Örn 2: Yüklediğim resimleri sıkıştırıp tek bir PDF yap." required></textarea>
                </div>

                <button type="submit" class="btn-run">Komutu Çalıştır</button>
            </form>
            
            <div class="footer-tags">
                <span>📊 Excel Motoru</span>
                <span>📄 PDF Dönüştürücü</span>
                <span>⚡ Otomatik Sıkıştırma</span>
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
        uploaded_files = [f for f in [file1, file2, file3] if f and f.filename]

        if not uploaded_files:
            raise HTTPException(status_code=400, detail="İşlem yapabilmek için en az bir dosya yüklemelisin Rıdo!")

        # 1. SENARYO: PDF ÇEVİRİCİ MOTORU
        if any(x in komut_lower for x in ["pdf", "resim", "görsel", "fotoğraf", "çevir"]):
            images = []
            for f in uploaded_files:
                filename_lower = f.filename.lower()
                if any(filename_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    img_bytes = await f.read()
                    img = Image.open(io.BytesIO(img_bytes))
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    images.append(img)
            
            if not images:
                raise HTTPException(status_code=400, detail="Yüklediğin dosyalar resim (.jpg, .png) değil Rıdo!")

            output_pdf_path = os.path.join(OUTPUT_DIR, "rdv_asistan_sonuc.pdf")
            images[0].save(output_pdf_path, "PDF", save_all=True, append_images=images[1:], quality=65)
            return FileResponse(output_pdf_path, media_type="application/pdf", filename="rdv_asistan_sonuc.pdf")

        # 2. SENARYO: EXCEL DÜŞEYARA MOTORU
        elif any(x in komut_lower for x in ["düşeyara", "vlookup", "birleştir", "merge"]):
            if len(uploaded_files) < 2:
                raise HTTPException(status_code=400, detail="Düşeyara için en az 2 Excel dosyası yüklemelisin!")
            
            df_main = pd.read_excel(io.BytesIO(await uploaded_files[0].read()))
            df_ref = pd.read_excel(io.BytesIO(await uploaded_files[1].read()))
            df_main.columns = df_main.columns.str.strip()
            df_ref.columns = df_ref.columns.str.strip()
            
            ortak_sutun = None
            for col in df_main.columns:
                if col.lower() in komut_lower:
                    ortak_sutun = col
                    break
            
            if not ortak_sutun:
                ortak_set = list(set(df_main.columns).intersection(set(df_ref.columns)))
                if ortak_set:
                    ortak_sutun = ortak_set[0]
                else:
                    raise HTTPException(status_code=400, detail="Ortak sütun adını bulamadım ve sütunlar otomatik eşleşmedi.")

            result_df = pd.merge(df_main, df_ref, on=ortak_sutun, how="left")
            output_excel_path = os.path.join(OUTPUT_DIR, "asistan_sonuc.xlsx")
            result_df.to_excel(output_excel_path, index=False)
            return FileResponse(output_excel_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="duseyara_sonuc.xlsx")

        # 3. SENARYO: EXCEL PIVOT MOTORU
        elif any(x in komut_lower for x in ["pivot", "özet", "grupla", "toplam"]):
            df = pd.read_excel(io.BytesIO(await uploaded_files[0].read()))
            df.columns = df.columns.str.strip()
            
            index_col, value_col = None, None
            for col in df.columns:
                if col.lower() in komut_lower:
                    if pd.api.types.is_numeric_dtype(df[col]) and not value_col:
                        value_col = col
                    elif not index_col:
                        index_col = col
            
            if not index_col: index_col = df.columns[0]
            if not value_col: value_col = df.columns[1]

            pivot_df = pd.pivot_table(df, values=value_col, index=index_col, aggfunc='sum').reset_index()
            output_excel_path = os.path.join(OUTPUT_DIR, "asistan_sonuc.xlsx")
            pivot_df.to_excel(output_excel_path, index=False)
            return FileResponse(output_excel_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="pivot_sonuc.xlsx")
        
        else:
            raise HTTPException(status_code=400, detail="Ne yapmak istediğini tam anlayamadım Rıdo. Komutta 'düşeyara', 'pivot' veya 'pdf' kelimelerini geçirmeyi dene.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Asistan Hatası: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("excel_vlookup_api:app", host="0.0.0.0", port=port, reload=False)
