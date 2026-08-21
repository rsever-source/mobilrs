import io
import os
from datetime import date
from typing import List
from urllib.parse import urlparse

import pandas as pd
import pdfplumber
import uvicorn

from PIL import Image

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Query,
)

from fastapi.responses import (
    HTMLResponse,
    FileResponse,
    JSONResponse,
)

from tufe_service import (
    get_current_tufe,
    save_cache,
)


# =========================================================
# UYGULAMA
# =========================================================

app = FastAPI(
    title="Rdv Asistan"
)

OUTPUT_DIR = "outputs"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True,
)


MONTH_NAMES = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

def money_tr(value: float):

    text = f"{value:,.2f}"

    text = (
        text
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return text + " TL"


def next_renewal_year(
    renewal_month: int
):

    today = date.today()

    if renewal_month >= today.month:
        return today.year

    return today.year + 1


def previous_month(
    year: int,
    month: int,
):

    if month == 1:
        return year - 1, 12

    return year, month - 1


# =========================================================
# SPARK -> REDIS GÜNCELLEME
# =========================================================

@app.get(
    "/tufe-guncelle"
)
async def spark_tufe_guncelle(
    key: str = Query(...),
    source: str = Query(...),
    rate: float = Query(...),
    year: int = Query(...),
    month: int = Query(...),
):

    # -----------------------------------------------------
    # GİZLİ ANAHTAR
    # -----------------------------------------------------

    expected_key = os.environ.get(
        "SPARK_TUFE_KEY",
        "",
    ).strip()


    if not expected_key:

        raise HTTPException(
            status_code=500,
            detail=(
                "SPARK_TUFE_KEY ayarlanmamış."
            ),
        )


    if key != expected_key:

        raise HTTPException(
            status_code=403,
            detail="Yetkisiz erişim.",
        )


    # -----------------------------------------------------
    # KAYNAK KONTROLÜ
    # SADECE RESMİ TÜİK
    # -----------------------------------------------------

    try:

        parsed = urlparse(
            source
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Geçersiz kaynak adresi.",
        )


    host = (
        parsed.hostname
        or ""
    ).lower()


    if host != "veriportali.tuik.gov.tr":

        raise HTTPException(
            status_code=400,
            detail=(
                "Sadece resmi TÜİK kaynağı kabul edilir."
            ),
        )


    if not parsed.path.startswith(
        "/tr/press/"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Kaynak resmi TÜİK haber bülteni olmalı."
            ),
        )


    # -----------------------------------------------------
    # VERİ KONTROLLERİ
    # -----------------------------------------------------

    if not (
        1 <= month <= 12
    ):

        raise HTTPException(
            status_code=400,
            detail="Geçersiz ay.",
        )


    if not (
        2020 <= year <= 2100
    ):

        raise HTTPException(
            status_code=400,
            detail="Geçersiz yıl.",
        )


    if not (
        0 < rate < 200
    ):

        raise HTTPException(
            status_code=400,
            detail="Geçersiz TÜFE oranı.",
        )


    # -----------------------------------------------------
    # REDIS'E YAZILACAK VERİ
    # -----------------------------------------------------

    data = {
        "rate": round(
            float(rate),
            2,
        ),

        "year": year,

        "month": month,

        "period": (
            f"{MONTH_NAMES[month]} "
            f"{year}"
        ),

        "source": source,

        "data_mode": "spark",
    }


    # -----------------------------------------------------
    # REDIS'E KAYDET
    # -----------------------------------------------------

    if not save_cache(
        data
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "Veri Redis'e kaydedilemedi."
            ),
        )


    return JSONResponse(
        {
            "ok": True,

            "message":
                "TÜFE başarıyla kaydedildi.",

            "oran": (
                f"{rate:.2f}"
                .replace(".", ",")
            ),

            "donem":
                data["period"],

            "source":
                source,
        }
    )


# =========================================================
# KİRA HESAPLAMA
# =========================================================

@app.post(
    "/kira-hesapla"
)
async def kira_hesapla(
    mevcut_kira: float = Form(...),
    yenileme_ayi: int = Form(...),
):

    if mevcut_kira <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Geçerli bir kira tutarı gir."
            ),
        )


    if (
        yenileme_ayi < 1
        or yenileme_ayi > 12
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Geçerli bir kira yenileme ayı seç."
            ),
        )


    # -----------------------------------------------------
    # TÜFE VERİSİNİ AL
    #
    # get_current_tufe:
    # canlı çalışırsa canlı
    # çalışmazsa Redis cache
    # -----------------------------------------------------

    try:

        tufe = get_current_tufe()

    except Exception as e:

        raise HTTPException(
            status_code=503,
            detail=(
                "Güncel TÜFE verisi alınamadı. "
                f"{str(e)}"
            ),
        )


    try:

        rate = float(
            tufe["rate"]
        )

        tufe_year = int(
            tufe["year"]
        )

        tufe_month = int(
            tufe["month"]
        )

        tufe_period = str(
            tufe["period"]
        )

        source = str(
            tufe["source"]
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail=(
                "TÜFE verisi geçersiz biçimde geldi."
            ),
        )


    # -----------------------------------------------------
    # KİRA HESABI
    # -----------------------------------------------------

    artis = (
        mevcut_kira
        * rate
        / 100
    )


    yeni_kira = (
        mevcut_kira
        + artis
    )


    # -----------------------------------------------------
    # YENİLEME DÖNEMİ
    # -----------------------------------------------------

    renewal_year = next_renewal_year(
        yenileme_ayi
    )


    target_year, target_month = (
        previous_month(
            renewal_year,
            yenileme_ayi,
        )
    )


    current_period = (
        tufe_year,
        tufe_month,
    )


    target_period = (
        target_year,
        target_month,
    )


    # -----------------------------------------------------
    # DURUM METNİ
    # -----------------------------------------------------

    if current_period == target_period:

        durum = (
            f"{MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} kira yenilemesi için "
            f"gerekli {tufe_period} TÜFE verisi "
            f"yayımlanmış. Hesap güncel resmi "
            f"TÜİK oranıyla yapıldı."
        )


    elif current_period < target_period:

        durum = (
            f"Son resmi TÜFE verisi "
            f"{tufe_period} dönemine ait. "
            f"{MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} yenilemesi için "
            f"{MONTH_NAMES[target_month]} "
            f"{target_year} verisi henüz "
            f"yayımlanmadı. Şimdilik son "
            f"resmi oranla hesaplandı."
        )


    else:

        durum = (
            f"Hesap, TÜİK'in yayımladığı "
            f"son resmi {tufe_period} "
            f"verisiyle yapıldı."
        )


    # -----------------------------------------------------
    # REDIS / SPARK KULLANILDIYSA
    # -----------------------------------------------------

    data_mode = tufe.get(
        "data_mode",
        "cache",
    )


    if data_mode in (
        "cache",
        "spark",
    ):

        durum += (
            " Günlük olarak kaydedilmiş "
            "son resmi TÜİK verisi kullanıldı."
        )


    return JSONResponse(
        {
            "oran": (
                f"{rate:.2f}"
                .replace(".", ",")
            ),

            "mevcut_kira":
                money_tr(
                    mevcut_kira
                ),

            "artis":
                money_tr(
                    artis
                ),

            "yeni_kira":
                money_tr(
                    yeni_kira
                ),

            "donem":
                tufe_period,

            "durum":
                durum,

            "source":
                source,

            "data_mode":
                data_mode,
        }
    )


# =========================================================
# ANA SAYFA
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def index():

    return """
<!DOCTYPE html>

<html lang="tr">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Rdv Asistan</title>


<style>

:root {
    --bg:#f1f5f9;
    --card:#ffffff;
    --primary:#0f172a;
    --accent:#3b82f6;
    --text:#1e293b;
    --rent:#f59e0b;
    --green:#10b981;
    --purple:#6366f1;
}

* {
    box-sizing:border-box;
    margin:0;
    padding:0;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

body {
    background:var(--bg);
    color:var(--text);
    padding:15px;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
}

.container {
    width:100%;
    max-width:500px;
    background:var(--card);
    border-radius:20px;
    overflow:hidden;
    box-shadow:
        0 10px 30px
        rgba(0,0,0,.08);
}

.header {
    background:var(--primary);
    color:white;
    padding:28px 20px;
    text-align:center;
}

.header h1 {
    font-size:26px;
    font-weight:800;
}

.tabs {
    display:flex;
    background:#e2e8f0;
    padding:5px;
    gap:4px;
    overflow-x:auto;
}

.tab-btn {
    flex:1;
    min-width:82px;
    border:none;
    background:none;
    padding:12px 5px;
    font-size:11px;
    font-weight:700;
    color:#64748b;
    cursor:pointer;
    border-radius:10px;
    white-space:nowrap;
}

.tab-btn.active {
    background:white;
    color:var(--primary);
    box-shadow:
        0 2px 8px
        rgba(0,0,0,.05);
}

.content {
    padding:25px;
}

.tab-content {
    display:none;
}

.tab-content.active {
    display:block;
}

.info {
    font-size:12px;
    color:#64748b;
    background:#f8fafc;
    border-radius:10px;
    padding:11px;
    text-align:center;
    line-height:1.5;
    margin-bottom:18px;
}

label {
    display:block;
    font-size:13px;
    font-weight:700;
    margin-bottom:6px;
}

.input {
    width:100%;
    padding:14px;
    border:1px solid #cbd5e1;
    border-radius:12px;
    font-size:16px;
    margin-bottom:15px;
    background:white;
    outline:none;
}

.input:focus {
    border-color:var(--rent);
}

.btn {
    width:100%;
    padding:15px;
    border:0;
    border-radius:12px;
    color:white;
    background:var(--accent);
    font-size:16px;
    font-weight:700;
    cursor:pointer;
    margin-top:5px;
}

.btn:disabled {
    opacity:.65;
}

.btn-rent {
    background:var(--rent);
}

.btn-green {
    background:var(--green);
}

.btn-purple {
    background:var(--purple);
}

.result {
    display:none;
    margin-top:18px;
    padding:17px;
    border-radius:14px;
    background:#f8fafc;
    border:1px solid #e2e8f0;
}

.result-rate {
    text-align:center;
    color:#64748b;
    font-size:13px;
}

.rate {
    text-align:center;
    font-size:29px;
    font-weight:900;
    color:var(--rent);
    margin:4px 0 12px;
}

.new-rent {
    text-align:center;
    font-size:27px;
    font-weight:900;
    color:#0f172a;
    margin-bottom:16px;
}

.status {
    background:#fff7ed;
    color:#9a3412;
    padding:12px;
    border-radius:10px;
    font-size:13px;
    line-height:1.55;
}

.error {
    background:#fee2e2;
    color:#991b1b;
}

.source {
    text-align:center;
    font-size:11px;
    margin-top:12px;
}

.source a {
    color:#2563eb;
    text-decoration:none;
    font-weight:700;
}

.file-box {
    border:2px dashed #cbd5e1;
    border-radius:12px;
    padding:15px;
    margin-bottom:12px;
    background:#f8fafc;
    position:relative;
    text-align:center;
}

.file-box input {
    position:absolute;
    inset:0;
    width:100%;
    height:100%;
    opacity:0;
    cursor:pointer;
}

.file-label {
    font-size:13px;
    color:#64748b;
    font-weight:600;
}

textarea {
    width:100%;
    height:90px;
    border:1px solid #cbd5e1;
    border-radius:12px;
    padding:12px;
    font-size:14px;
    resize:none;
    outline:none;
}

</style>


<script>

function switchTab(
    event,
    tabId
) {

    document
    .querySelectorAll(
        ".tab-content"
    )
    .forEach(
        el =>
        el.classList.remove(
            "active"
        )
    );


    document
    .querySelectorAll(
        ".tab-btn"
    )
    .forEach(
        el =>
        el.classList.remove(
            "active"
        )
    );


    document
    .getElementById(
        tabId
    )
    .classList
    .add(
        "active"
    );


    event
    .currentTarget
    .classList
    .add(
        "active"
    );
}


async function kiraHesapla(
    event
) {

    event.preventDefault();


    const button =
        document.getElementById(
            "kira-btn"
        );


    const result =
        document.getElementById(
            "kira-result"
        );


    const rent =
        document.getElementById(
            "mevcut-kira"
        ).value;


    const month =
        document.getElementById(
            "yenileme-ayi"
        ).value;


    button.disabled = true;

    button.innerText =
        "Hesaplanıyor...";


    result.style.display =
        "block";


    result.innerHTML =
        '<div class="info">' +
        'Güncel veri kontrol ediliyor...' +
        '</div>';


    try {

        const body =
            new URLSearchParams();


        body.append(
            "mevcut_kira",
            rent
        );


        body.append(
            "yenileme_ayi",
            month
        );


        const response =
            await fetch(
                "/kira-hesapla",
                {
                    method:"POST",

                    headers:{
                        "Content-Type":
                        "application/x-www-form-urlencoded"
                    },

                    body:body
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Hesaplama yapılamadı."
            );
        }


        result.innerHTML =

            '<div class="result-rate">' +
            '12 aylık ortalama TÜFE' +
            '</div>' +

            '<div class="rate">%' +
            data.oran +
            '</div>' +

            '<div class="new-rent">' +
            data.yeni_kira +
            '</div>' +

            '<div class="status">' +
            data.durum +
            '</div>' +

            '<div class="source">' +
            'Kaynak: ' +
            '<a target="_blank" href="' +
            data.source +
            '">' +
            'TÜİK' +
            '</a>' +
            '</div>';


    } catch(error) {

        result.innerHTML =
            '<div class="status error">' +
            error.message +
            '</div>';

    } finally {

        button.disabled = false;

        button.innerText =
            "Hesapla";
    }
}

</script>

</head>


<body>

<div class="container">


<div class="header">

    <h1>
        Rdv Asistan
    </h1>

</div>


<div class="tabs">


<button
    class="tab-btn active"
    onclick="
        switchTab(
            event,
            'kira-tab'
        )
    "
>
🏠 Kira
</button>


<button
    class="tab-btn"
    onclick="
        switchTab(
            event,
            'excel-tab'
        )
    "
>
📊 Excel
</button>


<button
    class="tab-btn"
    onclick="
        switchTab(
            event,
            'pdf-tab'
        )
    "
>
📄 Resim → PDF
</button>


<button
    class="tab-btn"
    onclick="
        switchTab(
            event,
            'pdfexcel-tab'
        )
    "
>
🟢 PDF → Excel
</button>


</div>


<div class="content">


<!-- =====================================================
KİRA
===================================================== -->

<div
    id="kira-tab"
    class="tab-content active"
>


<div class="info">

    Mevcut kira tutarını ve
    kira yenileme ayını seç.

</div>


<form
    onsubmit="
        kiraHesapla(event)
    "
>


<label>
Mevcut kira
</label>


<input
    id="mevcut-kira"
    class="input"
    type="number"
    min="1"
    step="0.01"
    placeholder="Örn: 16000"
    required
>


<label>
Kira yenileme ayı
</label>


<select
    id="yenileme-ayi"
    class="input"
    required
>

<option value="">
Ay seç
</option>

<option value="1">
Ocak
</option>

<option value="2">
Şubat
</option>

<option value="3">
Mart
</option>

<option value="4">
Nisan
</option>

<option value="5">
Mayıs
</option>

<option value="6">
Haziran
</option>

<option value="7">
Temmuz
</option>

<option value="8">
Ağustos
</option>

<option value="9">
Eylül
</option>

<option value="10">
Ekim
</option>

<option value="11">
Kasım
</option>

<option value="12">
Aralık
</option>

</select>


<button
    id="kira-btn"
    class="btn btn-rent"
    type="submit"
>
Hesapla
</button>


</form>


<div
    id="kira-result"
    class="result"
>
</div>


</div>


<!-- =====================================================
EXCEL
===================================================== -->

<div
    id="excel-tab"
    class="tab-content"
>


<form
    action="/excel-islem"
    method="post"
    enctype="multipart/form-data"
>


<div class="file-box">

<span
    id="xl1"
    class="file-label"
>
＋ 1. Excel (Ana Dosya)
</span>


<input
    type="file"
    name="file1"
    accept=".xlsx,.xls"
    required

    onchange="
        document
        .getElementById(
            'xl1'
        )
        .innerText =
        this.files[0].name
    "
>

</div>


<div class="file-box">

<span
    id="xl2"
    class="file-label"
>
＋ 2. Excel (Referans Dosyası)
</span>


<input
    type="file"
    name="file2"
    accept=".xlsx,.xls"
    required

    onchange="
        document
        .getElementById(
            'xl2'
        )
        .innerText =
        this.files[0].name
    "
>

</div>


<textarea
    name="komut"
    placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap."
    required
></textarea>


<button
    class="btn"
    type="submit"
>
Excel İşlemini Başlat
</button>


</form>

</div>


<!-- =====================================================
RESİM -> PDF
===================================================== -->

<div
    id="pdf-tab"
    class="tab-content"
>


<form
    action="/resim-pdf-islem"
    method="post"
    enctype="multipart/form-data"
>


<div class="info">

    Fotoğrafları seç,
    tek PDF dosyası oluştur.

</div>


<div class="file-box">

<span
    id="img1"
    class="file-label"
>
＋ Fotoğrafları Seç
</span>


<input
    type="file"
    name="images"
    accept=".png,.jpg,.jpeg"
    multiple
    required

    onchange="
        document
        .getElementById(
            'img1'
        )
        .innerText =
        this.files.length +
        ' fotoğraf seçildi'
    "
>

</div>


<button
    class="btn btn-purple"
    type="submit"
>
PDF Yap
</button>


</form>

</div>


<!-- =====================================================
PDF -> EXCEL
===================================================== -->

<div
    id="pdfexcel-tab"
    class="tab-content"
>


<form
    action="/pdf-excel-islem"
    method="post"
    enctype="multipart/form-data"
>


<div class="info">

    PDF içindeki tablo veya
    metni Excel'e aktar.

</div>


<div class="file-box">

<span
    id="pdfsrc"
    class="file-label"
>
＋ PDF Dosyasını Seç
</span>


<input
    type="file"
    name="pdf_file"
    accept=".pdf"
    required

    onchange="
        document
        .getElementById(
            'pdfsrc'
        )
        .innerText =
        this.files[0].name
    "
>

</div>


<button
    class="btn btn-green"
    type="submit"
>
PDF'i Excel'e Çevir
</button>


</form>

</div>


</div>

</div>

</body>

</html>
"""


# =========================================================
# EXCEL MOTORU
# =========================================================

@app.post(
    "/excel-islem"
)
async def excel_motor(
    komut: str = Form(...),
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):

    try:

        komut_lower = (
            komut.lower()
        )


        df_main = pd.read_excel(
            io.BytesIO(
                await file1.read()
            )
        )


        df_ref = pd.read_excel(
            io.BytesIO(
                await file2.read()
            )
        )


        df_main.columns = (
            df_main.columns
            .astype(str)
            .str.strip()
        )


        df_ref.columns = (
            df_ref.columns
            .astype(str)
            .str.strip()
        )


        # -------------------------------------------------
        # DÜŞEYARA / MERGE
        # -------------------------------------------------

        if any(
            x in komut_lower
            for x in [
                "düşeyara",
                "vlookup",
                "birleştir",
                "merge",
            ]
        ):

            ortak_sutun = None


            for col in df_main.columns:

                if (
                    col.lower()
                    in komut_lower
                ):

                    if col in df_ref.columns:

                        ortak_sutun = col
                        break


            if not ortak_sutun:

                ortak = list(
                    set(
                        df_main.columns
                    )
                    .intersection(
                        set(
                            df_ref.columns
                        )
                    )
                )


                if ortak:

                    ortak_sutun = (
                        ortak[0]
                    )


                else:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "İki Excel dosyasında "
                            "ortak sütun bulunamadı."
                        ),
                    )


            result_df = pd.merge(
                df_main,
                df_ref,
                on=ortak_sutun,
                how="left",
            )


        # -------------------------------------------------
        # PIVOT / ÖZET
        # -------------------------------------------------

        elif any(
            x in komut_lower
            for x in [
                "pivot",
                "özet",
                "grupla",
                "toplam",
            ]
        ):

            index_col = (
                df_main.columns[0]
            )


            numeric_cols = (
                df_main
                .select_dtypes(
                    include="number"
                )
                .columns
                .tolist()
            )


            if not numeric_cols:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Pivot için sayısal "
                        "sütun bulunamadı."
                    ),
                )


            value_col = (
                numeric_cols[0]
            )


            result_df = (
                pd.pivot_table(
                    df_main,
                    values=value_col,
                    index=index_col,
                    aggfunc="sum",
                )
                .reset_index()
            )


        else:

            result_df = (
                df_main
            )


        output_path = os.path.join(
            OUTPUT_DIR,
            "excel_sonuc.xlsx",
        )


        result_df.to_excel(
            output_path,
            index=False,
        )


        return FileResponse(
            output_path,

            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),

            filename=(
                "excel_sonuc.xlsx"
            ),
        )


    except HTTPException:
        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Excel Hatası: {str(e)}"
            ),
        )


# =========================================================
# RESİM -> PDF
# =========================================================

@app.post(
    "/resim-pdf-islem"
)
async def resim_pdf_motor(
    images: List[UploadFile] = File(...)
):

    try:

        pil_images = []


        for file in images:

            if not file.filename:
                continue


            if not file.filename.lower().endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                )
            ):
                continue


            image = Image.open(
                io.BytesIO(
                    await file.read()
                )
            )


            if image.mode != "RGB":

                image = image.convert(
                    "RGB"
                )


            pil_images.append(
                image
            )


        if not pil_images:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Geçerli fotoğraf bulunamadı."
                ),
            )


        output_path = os.path.join(
            OUTPUT_DIR,
            "rdv_pdf_sonuc.pdf",
        )


        pil_images[0].save(
            output_path,
            "PDF",

            save_all=True,

            append_images=(
                pil_images[1:]
            ),

            quality=65,
        )


        return FileResponse(
            output_path,

            media_type=(
                "application/pdf"
            ),

            filename=(
                "rdv_pdf_sonuc.pdf"
            ),
        )


    except HTTPException:
        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF Hatası: {str(e)}"
            ),
        )


# =========================================================
# PDF -> EXCEL
# =========================================================

@app.post(
    "/pdf-excel-islem"
)
async def pdf_excel_motor(
    pdf_file: UploadFile = File(...)
):

    try:

        pdf_bytes = (
            await pdf_file.read()
        )


        extracted_data = []


        with pdfplumber.open(
            io.BytesIO(
                pdf_bytes
            )
        ) as pdf:


            for page in pdf.pages:

                tables = (
                    page.extract_tables()
                )


                if tables:

                    for table in tables:

                        for row in table:

                            cleaned_row = [
                                (
                                    str(cell).strip()
                                    if cell
                                    is not None
                                    else ""
                                )
                                for cell
                                in row
                            ]


                            extracted_data.append(
                                cleaned_row
                            )


                else:

                    text = (
                        page.extract_text()
                    )


                    if text:

                        for line in text.split(
                            "\n"
                        ):

                            if line.strip():

                                extracted_data.append(
                                    line.split()
                                )


        if not extracted_data:

            raise HTTPException(
                status_code=400,
                detail=(
                    "PDF içinde Excel'e "
                    "aktarılacak veri bulunamadı."
                ),
            )


        df = pd.DataFrame(
            extracted_data
        )


        output_path = os.path.join(
            OUTPUT_DIR,
            "pdf_to_excel_sonuc.xlsx",
        )


        df.to_excel(
            output_path,
            index=False,
            header=False,
        )


        return FileResponse(
            output_path,

            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),

            filename=(
                "pdf_to_excel_sonuc.xlsx"
            ),
        )


    except HTTPException:
        raise


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF → Excel Hatası: {str(e)}"
            ),
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8000,
        )
    )


    uvicorn.run(
        "excel_vlookup_api:app",

        host="0.0.0.0",

        port=port,

        reload=False,
    )
