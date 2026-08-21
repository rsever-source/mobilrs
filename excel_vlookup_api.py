import io
import os
import re
from datetime import date
from urllib.parse import urljoin
from typing import List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from PIL import Image
import pdfplumber
import uvicorn


app = FastAPI(title="Rdv Asistan")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TUIK_HOME = "https://veriportali.tuik.gov.tr"
TUIK_LATEST = "https://veriportali.tuik.gov.tr/K"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/136 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

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

TR_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}


# =========================================================
# TÜİK CANLI VERİ
# =========================================================

def parse_period(text: str):

    match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi\s*,?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|"
        r"Temmuz|Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|"
        r"Aralık|Aralik)\s+(\d{4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    month_name = match.group(1).lower()
    year = int(match.group(2))

    month = TR_MONTHS.get(month_name)

    if not month:
        return None

    return year, month


def read_tufe_bulletin(url: str):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    if "Tüketici Fiyat Endeksi" not in text:
        return None

    period = parse_period(text)

    if not period:
        return None

    # Örn:
    # "... on iki aylık ortalamalara göre %31,90 artış ..."
    rate_match = re.search(
        r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
        r".{0,50}?%?\s*([0-9]{1,3}[,.][0-9]{1,2})",
        text,
        re.IGNORECASE,
    )

    if not rate_match:
        return None

    rate = float(
        rate_match.group(1).replace(",", ".")
    )

    year, month = period

    next_match = re.search(
        r"bir\s+sonraki\s+haber\s+bülteninin\s+"
        r"yayımlanma\s+tarihi\s*:?\s*"
        r"([0-9]{1,2}\s+"
        r"(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|"
        r"Ağustos|Eylül|Ekim|Kasım|Aralık)\s+[0-9]{4})",
        text,
        re.IGNORECASE,
    )

    next_date = (
        next_match.group(1)
        if next_match
        else None
    )

    return {
        "rate": rate,
        "year": year,
        "month": month,
        "period": f"{MONTH_NAMES[month]} {year}",
        "source": url,
        "next_date": next_date,
        "live": True,
    }


def find_latest_tufe():

    try:

        response = requests.get(
            TUIK_LATEST,
            headers=HEADERS,
            timeout=15,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        candidates = []

        for a in soup.find_all("a", href=True):

            title = " ".join(
                a.stripped_strings
            )

            href = a.get("href", "")

            if "tüketici fiyat endeksi" not in title.lower():
                continue

            full_url = urljoin(
                TUIK_HOME,
                href,
            )

            if (
                "/press/" in full_url.lower()
                or "/bulten/" in full_url.lower()
            ):

                candidates.append(
                    full_url
                )

        # Aynı linkleri temizle
        candidates = list(
            dict.fromkeys(candidates)
        )

        # Önce bulunan bültenleri dene
        for url in candidates:

            try:

                result = read_tufe_bulletin(
                    url
                )

                if result:
                    return result

            except Exception:
                continue

    except Exception:
        pass


    # -----------------------------------------------------
    # YEDEK KEŞİF
    # -----------------------------------------------------

    discovery_urls = [
        "https://veriportali.tuik.gov.tr/B",
        "https://veriportali.tuik.gov.tr/tr/",
    ]

    candidates = []

    for discovery_url in discovery_urls:

        try:

            response = requests.get(
                discovery_url,
                headers=HEADERS,
                timeout=12,
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            for a in soup.find_all(
                "a",
                href=True,
            ):

                label = " ".join(
                    a.stripped_strings
                )

                href = a.get(
                    "href",
                    "",
                )

                if (
                    "tüketici fiyat endeksi"
                    in label.lower()
                ):

                    full_url = urljoin(
                        TUIK_HOME,
                        href,
                    )

                    if (
                        "/press/" in full_url.lower()
                        or "/bulten/"
                        in full_url.lower()
                    ):

                        candidates.append(
                            full_url
                        )

        except Exception:
            continue


    candidates = list(
        dict.fromkeys(candidates)
    )


    for url in candidates:

        try:

            result = read_tufe_bulletin(
                url
            )

            if result:
                return result

        except Exception:
            continue


    # -----------------------------------------------------
    # SON DOĞRULANMIŞ RESMİ YEDEK VERİ
    #
    # Canlı TÜİK erişimi geçici olarak çalışmazsa
    # kullanıcı tamamen sonuçsuz kalmasın.
    # -----------------------------------------------------

    return {
        "rate": 31.90,
        "year": 2026,
        "month": 7,
        "period": "Temmuz 2026",
        "source": (
            "https://veriportali.tuik.gov.tr/"
            "tr/press/58297"
        ),
        "next_date": "03 Eylül 2026",
        "live": False,
    }


# =========================================================
# KİRA HESABI
# =========================================================

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


def money_tr(value: float):

    text = f"{value:,.2f}"

    text = (
        text
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return text + " TL"


@app.post("/kira-hesapla")
async def kira_hesapla(
    mevcut_kira: float = Form(...),
    yenileme_ayi: int = Form(...),
):

    if mevcut_kira <= 0:

        raise HTTPException(
            status_code=400,
            detail="Geçerli kira tutarı gir.",
        )

    if yenileme_ayi not in MONTH_NAMES:

        raise HTTPException(
            status_code=400,
            detail="Geçerli yenileme ayı seç.",
        )


    tufe = find_latest_tufe()

    rate = tufe["rate"]

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
        tufe["year"],
        tufe["month"],
    )

    target_period = (
        target_year,
        target_month,
    )


    # -----------------------------------------------------
    # KISA DURUM MESAJI
    # -----------------------------------------------------

    if current_period == target_period:

        durum = (
            f"{MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} kira yenilemesi için "
            f"{tufe['period']} TÜFE verisi yayımlanmış. "
            f"Hesap güncel resmi oranla yapıldı."
        )

    elif current_period < target_period:

        durum = (
            f"Son resmi TÜFE verisi "
            f"{tufe['period']} dönemine ait. "
            f"{MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} yenilemesi için "
            f"{MONTH_NAMES[target_month]} "
            f"{target_year} verisi henüz yayımlanmadı. "
            f"Şimdilik son resmi oranla hesaplandı."
        )

    else:

        durum = (
            f"Hesap, TÜİK'in yayımladığı "
            f"son resmi {tufe['period']} "
            f"verisiyle yapıldı."
        )


    if not tufe["live"]:

        durum += (
            " Canlı TÜİK bağlantısı "
            "kullanılamadığı için son "
            "doğrulanmış resmi veri kullanıldı."
        )


    return JSONResponse(
        {
            "oran": (
                f"{rate:.2f}"
                .replace(".", ",")
            ),

            "yeni_kira":
                money_tr(yeni_kira),

            "mevcut_kira":
                money_tr(mevcut_kira),

            "artis":
                money_tr(artis),

            "donem":
                tufe["period"],

            "durum":
                durum,

            "source":
                tufe["source"],

            "live":
                tufe["live"],
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
}

* {
    box-sizing:border-box;
    margin:0;
    padding:0;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
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

.btn-rent {
    background:var(--rent);
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
    margin:4px 0 12px 0;
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
    line-height:1.5;
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
    button.innerText = "Hesaplanıyor...";

    result.style.display =
        "block";

    result.innerHTML =
        '<div class="info">' +
        'Güncel TÜİK verisi kontrol ediliyor...' +
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
            '<div class="status">' +
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

    Kira yenileme ayını seç.
    Hesapla dediğinde yayımlanmış
    son resmi TÜFE verisi kullanılır.

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



<!-- RESİM PDF -->

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
Fotoğrafları tek PDF yap.
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
    class="btn"
    type="submit"
>
PDF Yap
</button>


</form>

</div>



<!-- PDF EXCEL -->

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
PDF içindeki tabloyu Excel'e aktar.
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
    class="btn"
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

@app.post("/excel-islem")
async def excel_motor(
    komut: str = Form(...),
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):

    try:

        komut_lower = komut.lower()

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
            .str.strip()
        )

        df_ref.columns = (
            df_ref.columns
            .str.strip()
        )


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

                    ortak_sutun = col
                    break


            if not ortak_sutun:

                ortak = list(
                    set(
                        df_main.columns
                    ).intersection(
                        set(
                            df_ref.columns
                        )
                    )
                )

                if ortak:

                    ortak_sutun = ortak[0]

                else:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Ortak sütun bulunamadı."
                        ),
                    )


            result_df = pd.merge(
                df_main,
                df_ref,
                on=ortak_sutun,
                how="left",
            )


        elif any(
            x in komut_lower
            for x in [
                "pivot",
                "özet",
                "grupla",
                "toplam",
            ]
        ):

            index_col = df_main.columns[0]

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
                        "Sayısal sütun bulunamadı."
                    ),
                )

            value_col = numeric_cols[0]

            result_df = pd.pivot_table(
                df_main,
                values=value_col,
                index=index_col,
                aggfunc="sum",
            ).reset_index()


        else:

            result_df = df_main


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
            filename="excel_sonuc.xlsx",
        )


    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Excel Hatası: {e}"
            ),
        )


# =========================================================
# RESİM -> PDF
# =========================================================

@app.post("/resim-pdf-islem")
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
            append_images=pil_images[1:],
            quality=65,
        )


        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename="rdv_pdf_sonuc.pdf",
        )


    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF Hatası: {e}"
            ),
        )


# =========================================================
# PDF -> EXCEL
# =========================================================

@app.post("/pdf-excel-islem")
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

                            extracted_data.append(
                                [
                                    (
                                        str(cell).strip()
                                        if cell
                                        is not None
                                        else ""
                                    )
                                    for cell in row
                                ]
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
                    "PDF içinde aktarılacak "
                    "veri bulunamadı."
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
                f"PDF → Excel Hatası: {e}"
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
