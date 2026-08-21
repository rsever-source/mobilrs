import io
import os
import uuid
from datetime import date
from typing import List
from urllib.parse import urlparse

import pandas as pd
import pdfplumber
import uvicorn

from PIL import Image, ImageOps

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

from starlette.background import BackgroundTask

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


# =========================================================
# DOSYA LİMİTLERİ
# =========================================================

# Tek Excel / PDF / fotoğraf için 25 MB
MAX_FILE_SIZE = 25 * 1024 * 1024

# Çoklu fotoğraflarda toplam 100 MB
MAX_IMAGES_TOTAL_SIZE = 100 * 1024 * 1024


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
# LOG
# =========================================================

def app_log(message: str):
    print(
        f"[RDV] {message}",
        flush=True,
    )


# =========================================================
# DOSYA YARDIMCILARI
# =========================================================

def unique_output_path(extension: str):
    filename = (
        f"rdv_{uuid.uuid4().hex}.{extension}"
    )

    return os.path.join(
        OUTPUT_DIR,
        filename,
    )


def delete_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)

            app_log(
                f"GECICI DOSYA SILINDI path={path}"
            )

    except Exception as e:
        app_log(
            f"GECICI DOSYA SILME HATASI: {e}"
        )


async def read_upload_limited(
    upload: UploadFile,
    max_size: int = MAX_FILE_SIZE,
):

    data = await upload.read()

    if len(data) > max_size:
        raise HTTPException(
            status_code=413,
            detail=(
                f"{upload.filename or 'Dosya'} çok büyük. "
                f"Maksimum boyut "
                f"{max_size // (1024 * 1024)} MB."
            ),
        )

    return data


def check_extension(
    filename: str,
    allowed_extensions,
):

    filename_lower = (
        filename or ""
    ).lower()

    return filename_lower.endswith(
        allowed_extensions
    )


# =========================================================
# EXCEL YARDIMCILARI
# =========================================================

def normalize_column_name(value):
    return str(value).strip()


def select_join_column(
    df_main: pd.DataFrame,
    df_ref: pd.DataFrame,
    command: str,
):

    command_lower = command.lower()

    main_columns = list(
        df_main.columns
    )

    ref_columns = list(
        df_ref.columns
    )

    common_columns = [
        col
        for col in main_columns
        if col in ref_columns
    ]


    if not common_columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "İki Excel dosyasında ortak "
                "sütun bulunamadı."
            ),
        )


    # Önce kullanıcının komutta belirttiği sütunu ara
    for col in common_columns:

        if str(col).lower() in command_lower:
            return col


    # Yaygın anahtar sütun isimlerine öncelik ver
    preferred_words = [
        "id",
        "kod",
        "code",
        "no",
        "numara",
        "musteri",
        "müşteri",
        "container",
        "konteyner",
        "referans",
        "ref",
        "sicil",
    ]


    for preferred in preferred_words:

        for col in common_columns:

            col_lower = str(col).lower()

            if preferred in col_lower:
                return col


    # Geriye uyumluluk:
    # eski sistem gibi ilk ortak sütunu kullan
    return common_columns[0]


def find_command_columns(
    df: pd.DataFrame,
    command: str,
):

    command_lower = (
        command.lower()
    )

    matches = []

    for col in df.columns:

        col_text = str(col)

        if col_text.lower() in command_lower:
            matches.append(
                col
            )

    return matches


# =========================================================
# KİRA YARDIMCILARI
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
# SPARK -> REDIS TÜFE GÜNCELLEME
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

    app_log(
        "SPARK ISTEK GELDI "
        f"source={source} "
        f"rate={rate} "
        f"year={year} "
        f"month={month}"
    )


    expected_key = os.environ.get(
        "SPARK_TUFE_KEY",
        "",
    ).strip()


    if not expected_key:

        app_log(
            "SUNUCU AYAR HATASI: "
            "SPARK_TUFE_KEY TANIMLI DEGIL"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "SPARK_TUFE_KEY ayarlanmamış."
            ),
        )


    if key != expected_key:

        app_log(
            "SPARK ANAHTAR HATASI"
        )

        raise HTTPException(
            status_code=403,
            detail="Yetkisiz erişim.",
        )


    try:

        parsed = urlparse(
            source
        )

    except Exception as e:

        app_log(
            "SPARK PARAMETRE HATASI: "
            f"KAYNAK URL OKUNAMADI: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail="Geçersiz kaynak adresi.",
        )


    host = (
        parsed.hostname
        or ""
    ).lower()


    if host != "veriportali.tuik.gov.tr":

        app_log(
            "SPARK PARAMETRE HATASI: "
            f"GECERSIZ KAYNAK HOST={host}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Sadece resmi TÜİK kaynağı kabul edilir."
            ),
        )


    if not parsed.path.startswith(
        "/tr/press/"
    ):

        app_log(
            "SPARK PARAMETRE HATASI: "
            f"GECERSIZ TUIK PATH={parsed.path}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Kaynak resmi TÜİK haber bülteni olmalı."
            ),
        )


    if not (
        1 <= month <= 12
    ):

        app_log(
            "SPARK PARAMETRE HATASI: "
            f"GECERSIZ AY={month}"
        )

        raise HTTPException(
            status_code=400,
            detail="Geçersiz ay.",
        )


    if not (
        2020 <= year <= 2100
    ):

        app_log(
            "SPARK PARAMETRE HATASI: "
            f"GECERSIZ YIL={year}"
        )

        raise HTTPException(
            status_code=400,
            detail="Geçersiz yıl.",
        )


    if not (
        0 < rate < 200
    ):

        app_log(
            "SPARK PARAMETRE HATASI: "
            f"GECERSIZ ORAN={rate}"
        )

        raise HTTPException(
            status_code=400,
            detail="Geçersiz TÜFE oranı.",
        )


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


    saved = save_cache(
        data
    )


    if not saved:

        app_log(
            "REDIS KAYIT HATASI"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Veri Redis'e kaydedilemedi."
            ),
        )


    app_log(
        "TUFE REDIS'E KAYDEDILDI "
        f"donem={data['period']} "
        f"oran={data['rate']}"
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

    app_log(
        "KIRA HESAPLA ISTEGI "
        f"kira={mevcut_kira} "
        f"ay={yenileme_ayi}"
    )


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


    try:

        tufe = get_current_tufe()

    except Exception as e:

        app_log(
            "KIRA HESAPLA TUFE HATASI: "
            f"{str(e)}"
        )

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

    except Exception as e:

        app_log(
            "KIRA HESAPLA VERI FORMAT HATASI: "
            f"{str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "TÜFE verisi geçersiz biçimde geldi."
            ),
        )


    data_mode = tufe.get(
        "data_mode",
        "cache",
    )


    app_log(
        "KIRA HESAPLA TUFE VERISI "
        f"donem={tufe_period} "
        f"oran={rate} "
        f"mode={data_mode}"
    )


    artis = (
        mevcut_kira
        * rate
        / 100
    )


    yeni_kira = (
        mevcut_kira
        + artis
    )


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


    if data_mode in (
        "cache",
        "spark",
    ):

        durum += (
            " Günlük olarak kaydedilmiş "
            "son resmi TÜİK verisi kullanıldı."
        )


    app_log(
        "KIRA HESAP BASARILI "
        f"yeni_kira={yeni_kira:.2f}"
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


<!-- KİRA -->

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


<!-- EXCEL -->

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


<!-- RESİM -> PDF -->

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


<!-- PDF -> EXCEL -->

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

    output_path = None

    try:

        app_log(
            "EXCEL ISLEM BASLADI "
            f"file1={file1.filename} "
            f"file2={file2.filename}"
        )


        if not check_extension(
            file1.filename,
            (".xlsx", ".xls"),
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "1. dosya geçerli bir "
                    "Excel dosyası değil."
                ),
            )


        if not check_extension(
            file2.filename,
            (".xlsx", ".xls"),
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "2. dosya geçerli bir "
                    "Excel dosyası değil."
                ),
            )


        bytes1 = await read_upload_limited(
            file1
        )

        bytes2 = await read_upload_limited(
            file2
        )


        df_main = pd.read_excel(
            io.BytesIO(
                bytes1
            )
        )


        df_ref = pd.read_excel(
            io.BytesIO(
                bytes2
            )
        )


        if df_main.empty:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Ana Excel dosyasında "
                    "veri bulunamadı."
                ),
            )


        if df_ref.empty:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Referans Excel dosyasında "
                    "veri bulunamadı."
                ),
            )


        df_main.columns = [
            normalize_column_name(col)
            for col in df_main.columns
        ]


        df_ref.columns = [
            normalize_column_name(col)
            for col in df_ref.columns
        ]


        komut_lower = (
            komut.lower().strip()
        )


        # -------------------------------------------------
        # DÜŞEYARA / MERGE
        # -------------------------------------------------

        if any(
            word in komut_lower
            for word in [
                "düşeyara",
                "duseyara",
                "vlookup",
                "birleştir",
                "birlestir",
                "merge",
                "eşleştir",
                "eslestir",
            ]
        ):

            ortak_sutun = (
                select_join_column(
                    df_main,
                    df_ref,
                    komut,
                )
            )


            app_log(
                "EXCEL BIRLESTIRME "
                f"ortak_sutun={ortak_sutun}"
            )


            result_df = pd.merge(
                df_main,
                df_ref,
                on=ortak_sutun,
                how="left",
                suffixes=(
                    "",
                    "_referans",
                ),
            )


        # -------------------------------------------------
        # PIVOT / ÖZET
        # -------------------------------------------------

        elif any(
            word in komut_lower
            for word in [
                "pivot",
                "özet",
                "ozet",
                "grupla",
                "toplam",
            ]
        ):

            command_columns = (
                find_command_columns(
                    df_main,
                    komut,
                )
            )


            numeric_columns = (
                df_main
                .select_dtypes(
                    include="number"
                )
                .columns
                .tolist()
            )


            if not numeric_columns:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Pivot/özet için "
                        "sayısal sütun bulunamadı."
                    ),
                )


            # Komutta geçen sayısal sütunu bul
            value_col = None

            for col in command_columns:

                if col in numeric_columns:
                    value_col = col
                    break


            if value_col is None:
                value_col = (
                    numeric_columns[0]
                )


            # Komutta geçen sayısal olmayan sütunu bul
            index_col = None

            for col in command_columns:

                if col != value_col:
                    index_col = col
                    break


            if index_col is None:

                non_numeric = [
                    col
                    for col in df_main.columns
                    if col != value_col
                ]

                if not non_numeric:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Pivot için grup "
                            "sütunu bulunamadı."
                        ),
                    )

                index_col = (
                    non_numeric[0]
                )


            app_log(
                "EXCEL PIVOT "
                f"index={index_col} "
                f"value={value_col}"
            )


            result_df = (
                pd.pivot_table(
                    df_main,
                    values=value_col,
                    index=index_col,
                    aggfunc="sum",
                    fill_value=0,
                )
                .reset_index()
            )


        # -------------------------------------------------
        # KOMUT TANINMADI
        # -------------------------------------------------

        else:

            app_log(
                "EXCEL KOMUT TANINMADI "
                "ANA DOSYA AYNEN AKTARILDI"
            )

            result_df = (
                df_main.copy()
            )


        output_path = (
            unique_output_path(
                "xlsx"
            )
        )


        result_df.to_excel(
            output_path,
            index=False,
        )


        app_log(
            "EXCEL ISLEM BASARILI "
            f"satir={len(result_df)}"
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

            background=BackgroundTask(
                delete_file,
                output_path,
            ),
        )


    except HTTPException:
        raise


    except Exception as e:

        if output_path:
            delete_file(
                output_path
            )

        app_log(
            f"EXCEL HATASI: {str(e)}"
        )

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

    output_path = None
    pil_images = []

    try:

        app_log(
            "RESIM PDF ISLEM BASLADI "
            f"adet={len(images)}"
        )


        total_size = 0


        for file in images:

            if not file.filename:
                continue


            if not check_extension(
                file.filename,
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                ),
            ):

                continue


            data = await read_upload_limited(
                file
            )


            total_size += len(
                data
            )


            if (
                total_size
                > MAX_IMAGES_TOTAL_SIZE
            ):

                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Seçilen fotoğrafların "
                        "toplam boyutu çok büyük. "
                        "Maksimum 100 MB."
                    ),
                )


            image = Image.open(
                io.BytesIO(
                    data
                )
            )


            # iPhone / telefon fotoğrafı yönünü düzelt
            image = (
                ImageOps.exif_transpose(
                    image
                )
            )


            if image.mode != "RGB":

                image = image.convert(
                    "RGB"
                )


            # Görüntüyü belleğe bağımsız kopyala
            image = image.copy()


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


        output_path = (
            unique_output_path(
                "pdf"
            )
        )


        pil_images[0].save(
            output_path,
            "PDF",
            save_all=True,
            append_images=(
                pil_images[1:]
            ),
            resolution=150.0,
        )


        app_log(
            "RESIM PDF BASARILI "
            f"adet={len(pil_images)}"
        )


        return FileResponse(
            output_path,

            media_type=(
                "application/pdf"
            ),

            filename=(
                "rdv_pdf_sonuc.pdf"
            ),

            background=BackgroundTask(
                delete_file,
                output_path,
            ),
        )


    except HTTPException:

        if output_path:
            delete_file(
                output_path
            )

        raise


    except Exception as e:

        if output_path:
            delete_file(
                output_path
            )

        app_log(
            f"RESIM PDF HATASI: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF Hatası: {str(e)}"
            ),
        )


    finally:

        for image in pil_images:

            try:
                image.close()
            except Exception:
                pass


# =========================================================
# PDF -> EXCEL
# =========================================================

@app.post(
    "/pdf-excel-islem"
)
async def pdf_excel_motor(
    pdf_file: UploadFile = File(...)
):

    output_path = None

    try:

        app_log(
            "PDF EXCEL ISLEM BASLADI "
            f"file={pdf_file.filename}"
        )


        if not check_extension(
            pdf_file.filename,
            (".pdf",),
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Geçerli bir PDF dosyası seç."
                ),
            )


        pdf_bytes = (
            await read_upload_limited(
                pdf_file
            )
        )


        extracted_data = []


        with pdfplumber.open(
            io.BytesIO(
                pdf_bytes
            )
        ) as pdf:


            app_log(
                "PDF ACILDI "
                f"sayfa={len(pdf.pages)}"
            )


            for page_number, page in enumerate(
                pdf.pages,
                start=1,
            ):

                tables = (
                    page.extract_tables()
                )


                if tables:

                    for table in tables:

                        for row in table:

                            if not row:
                                continue


                            cleaned_row = [
                                (
                                    str(cell)
                                    .replace(
                                        "\n",
                                        " ",
                                    )
                                    .strip()
                                    if cell
                                    is not None
                                    else ""
                                )
                                for cell
                                in row
                            ]


                            if any(
                                cell
                                for cell
                                in cleaned_row
                            ):

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

                            line = (
                                line.strip()
                            )

                            if line:

                                extracted_data.append(
                                    [
                                        line
                                    ]
                                )


        if not extracted_data:

            app_log(
                "PDF EXCEL VERI BULUNAMADI"
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "PDF içinde Excel'e "
                    "aktarılacak metin veya "
                    "tablo bulunamadı. "
                    "Taranmış/resim PDF ise "
                    "OCR gerekir."
                ),
            )


        # Farklı uzunluktaki satırları eşitle
        max_columns = max(
            len(row)
            for row
            in extracted_data
        )


        normalized_rows = []


        for row in extracted_data:

            normalized_row = (
                row
                + [""] * (
                    max_columns
                    - len(row)
                )
            )

            normalized_rows.append(
                normalized_row
            )


        df = pd.DataFrame(
            normalized_rows
        )


        output_path = (
            unique_output_path(
                "xlsx"
            )
        )


        df.to_excel(
            output_path,
            index=False,
            header=False,
        )


        app_log(
            "PDF EXCEL BASARILI "
            f"satir={len(df)} "
            f"sutun={len(df.columns)}"
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

            background=BackgroundTask(
                delete_file,
                output_path,
            ),
        )


    except HTTPException:

        if output_path:
            delete_file(
                output_path
            )

        raise


    except Exception as e:

        if output_path:
            delete_file(
                output_path
            )

        app_log(
            f"PDF EXCEL HATASI: {str(e)}"
        )

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
