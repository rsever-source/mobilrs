import io
import os
import re
from datetime import date
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn
from PIL import Image
from typing import List
import pdfplumber


app = FastAPI(title="Rdv Asistan")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# TÜİK - CANLI TÜFE VERİSİ
# =========================================================

TUIK_BASE = "https://veriportali.tuik.gov.tr"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/136 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
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


def parse_reference_period(text: str):
    match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi\s*,?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|"
        r"Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+(\d{4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    month_text = match.group(1).lower()
    year = int(match.group(2))
    month = TR_MONTHS.get(month_text)

    if not month:
        return None

    return year, month


def find_latest_tufe_bulletin():
    discovery_urls = [
        f"{TUIK_BASE}/B",
        f"{TUIK_BASE}/tr/",
        (
            f"{TUIK_BASE}/Search/Search"
            "?dil=1&text=T%C3%BCketici%20Fiyat%20Endeksi"
        ),
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

            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                label = " ".join(a.stripped_strings)

                if (
                    "/press/" in href.lower()
                    and "tüketici fiyat endeksi" in label.lower()
                ):
                    full_url = urljoin(TUIK_BASE, href)

                    press_match = re.search(r"/press/(\d+)", full_url)

                    press_id = (
                        int(press_match.group(1))
                        if press_match
                        else 0
                    )

                    candidates.append((press_id, full_url))

        except Exception:
            continue

    unique_candidates = {}

    for press_id, url in candidates:
        unique_candidates[url] = press_id

    candidates = [
        (press_id, url)
        for url, press_id in unique_candidates.items()
    ]

    candidates.sort(key=lambda x: x[0], reverse=True)

    for _, bulletin_url in candidates[:10]:
        try:
            data = read_tufe_bulletin(bulletin_url)

            if data:
                return data

        except Exception:
            continue

    raise RuntimeError(
        "TÜİK'ten güncel TÜFE bülteni bulunamadı. "
        "Eski veya sabit oran kullanılmadı."
    )


def read_tufe_bulletin(url: str):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=12,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    if "Tüketici Fiyat Endeksi" not in text:
        return None

    rate_match = re.search(
        r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
        r"\s*(?:değişim\s*)?(?:oranı\s*)?"
        r"%?\s*([0-9]+(?:[,.][0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if not rate_match:
        return None

    rate_text = rate_match.group(1).replace(",", ".")
    rate = float(rate_text)

    reference = parse_reference_period(text)

    if not reference:
        return None

    reference_year, reference_month = reference

    publication_match = re.search(
        r"Yayım\s+Tarihi\s*:?\s*"
        r"([0-9]{1,2}\s+"
        r"(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|"
        r"Ağustos|Eylül|Ekim|Kasım|Aralık)"
        r"\s+[0-9]{4})",
        text,
        re.IGNORECASE,
    )

    publication_date = (
        publication_match.group(1)
        if publication_match
        else "TÜİK bülteni"
    )

    next_match = re.search(
        r"bir\s+sonraki\s+haber\s+bülteninin\s+"
        r"yayımlanma\s+tarihi\s*:?\s*"
        r"([0-9]{1,2}\s+"
        r"(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|"
        r"Ağustos|Eylül|Ekim|Kasım|Aralık)"
        r"\s+[0-9]{4})",
        text,
        re.IGNORECASE,
    )

    next_publication_date = (
        next_match.group(1)
        if next_match
        else None
    )

    return {
        "rate": rate,
        "reference_year": reference_year,
        "reference_month": reference_month,
        "reference_name": (
            f"{MONTH_NAMES[reference_month]} "
            f"{reference_year}"
        ),
        "publication_date": publication_date,
        "next_publication_date": next_publication_date,
        "source_url": url,
    }


def calculate_next_renewal_month(selected_month: int):
    today = date.today()

    if selected_month >= today.month:
        renewal_year = today.year
    else:
        renewal_year = today.year + 1

    return renewal_year


def previous_month(year: int, month: int):
    if month == 1:
        return year - 1, 12

    return year, month - 1


def turkish_money(value: float):
    formatted = f"{value:,.2f}"

    formatted = (
        formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return formatted + " TL"


# =========================================================
# ANA SAYFA
# =========================================================

@app.get("/", response_class=HTMLResponse)
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
                --bg-color: #f1f5f9;
                --card-bg: #ffffff;
                --primary: #0f172a;
                --accent: #3b82f6;
                --text: #1e293b;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    sans-serif;
            }

            body {
                background: var(--bg-color);
                color: var(--text);
                padding: 15px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }

            .container {
                width: 100%;
                max-width: 500px;
                background: var(--card-bg);
                border-radius: 20px;
                box-shadow:
                    0 10px 30px rgba(0,0,0,0.08);
                overflow: hidden;
            }

            .header {
                background: var(--primary);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }

            .header h1 {
                font-size: 26px;
                font-weight: 800;
            }

            .tabs {
                display: flex;
                background: #e2e8f0;
                padding: 5px;
                gap: 4px;
                overflow-x: auto;
            }

            .tab-btn {
                flex: 1;
                min-width: 85px;
                border: none;
                background: none;
                padding: 12px 5px;
                font-size: 11px;
                font-weight: 700;
                color: #64748b;
                cursor: pointer;
                border-radius: 10px;
                transition: all 0.2s;
                text-align: center;
                white-space: nowrap;
            }

            .tab-btn.active {
                background: var(--card-bg);
                color: var(--primary);
                box-shadow:
                    0 2px 8px rgba(0,0,0,0.05);
            }

            .content {
                padding: 25px;
            }

            .tab-content {
                display: none;
            }

            .tab-content.active {
                display: block;
            }

            .file-box {
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 12px;
                background: #f8fafc;
                position: relative;
                text-align: center;
            }

            .file-box input {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }

            .file-label {
                font-size: 13px;
                color: #64748b;
                font-weight: 600;
            }

            .command-area {
                margin-top: 15px;
            }

            textarea {
                width: 100%;
                height: 90px;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
                padding: 12px;
                font-size: 14px;
                resize: none;
                outline: none;
            }

            .btn-run {
                width: 100%;
                background: var(--accent);
                color: white;
                border: none;
                padding: 15px;
                font-size: 16px;
                font-weight: 700;
                border-radius: 12px;
                cursor: pointer;
                margin-top: 15px;
            }

            .btn-pdf-excel {
                background: #10b981;
            }

            .btn-image-pdf {
                background: #6366f1;
            }

            .btn-kira {
                background: #f59e0b;
            }

            .info-text {
                font-size: 12px;
                color: #64748b;
                margin-bottom: 15px;
                line-height: 1.5;
                text-align: center;
                background: #f8fafc;
                padding: 10px;
                border-radius: 8px;
            }

            .field-label {
                display: block;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 6px;
                color: #475569;
            }

            .input-box {
                width: 100%;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                outline: none;
                margin-bottom: 14px;
                background: white;
            }

            .kira-result {
                display: none;
                margin-top: 18px;
                border-radius: 14px;
                background: #f8fafc;
                padding: 16px;
                border: 1px solid #e2e8f0;
            }

            .result-main {
                text-align: center;
                padding: 12px 0;
            }

            .result-main .rate {
                font-size: 30px;
                font-weight: 900;
                color: #f59e0b;
            }

            .result-main .rent {
                font-size: 26px;
                font-weight: 900;
                color: #0f172a;
                margin-top: 8px;
            }

            .result-row {
                padding: 9px 0;
                border-top: 1px solid #e2e8f0;
                font-size: 13px;
                line-height: 1.5;
            }

            .status-exact {
                background: #dcfce7;
                color: #166534;
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 10px;
            }

            .status-estimate {
                background: #fef3c7;
                color: #92400e;
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 10px;
            }

            .error-box {
                background: #fee2e2;
                color: #991b1b;
                padding: 12px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
            }

            .source-link {
                color: #2563eb;
                text-decoration: none;
                font-weight: 700;
            }

            .small-note {
                margin-top: 13px;
                font-size: 11px;
                line-height: 1.5;
                color: #64748b;
            }

        </style>


        <script>

            function switchTab(event, tabId) {

                var contents =
                    document.getElementsByClassName(
                        "tab-content"
                    );

                for (
                    var i = 0;
                    i < contents.length;
                    i++
                ) {
                    contents[i].classList.remove(
                        "active"
                    );
                }

                var buttons =
                    document.getElementsByClassName(
                        "tab-btn"
                    );

                for (
                    var i = 0;
                    i < buttons.length;
                    i++
                ) {
                    buttons[i].classList.remove(
                        "active"
                    );
                }

                document
                    .getElementById(tabId)
                    .classList
                    .add("active");

                event.currentTarget
                    .classList
                    .add("active");
            }


            async function kiraHesapla(event) {

                event.preventDefault();

                const button =
                    document.getElementById(
                        "kira-btn"
                    );

                const result =
                    document.getElementById(
                        "kira-result"
                    );

                const kira =
                    document.getElementById(
                        "mevcut-kira"
                    ).value;

                const ay =
                    document.getElementById(
                        "yenileme-ayi"
                    ).value;

                button.disabled = true;

                button.innerText =
                    "TÜİK güncel verisi kontrol ediliyor...";

                result.style.display = "block";

                result.innerHTML =
                    '<div class="info-text">' +
                    'TÜİK canlı verisi kontrol ediliyor...' +
                    '</div>';

                try {

                    const formData =
                        new URLSearchParams();

                    formData.append(
                        "mevcut_kira",
                        kira
                    );

                    formData.append(
                        "yenileme_ayi",
                        ay
                    );

                    const response =
                        await fetch(
                            "/kira-hesapla",
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type":
                                    "application/x-www-form-urlencoded"
                                },
                                body: formData
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

                    let statusClass =
                        data.kesin_mi
                        ? "status-exact"
                        : "status-estimate";

                    let nextInfo = "";

                    if (
                        data.sonraki_tufe_tarihi
                    ) {

                        nextInfo =
                            '<div class="result-row">' +
                            '<b>Bir sonraki TÜFE açıklaması:</b><br>' +
                            data.sonraki_tufe_tarihi +
                            '</div>';

                    }

                    result.innerHTML =

                        '<div class="' +
                        statusClass +
                        '">' +
                        data.durum_mesaji +
                        '</div>' +

                        '<div class="result-main">' +

                        '<div>12 aylık ortalama TÜFE</div>' +

                        '<div class="rate">%' +
                        data.oran +
                        '</div>' +

                        '<div class="rent">' +
                        data.yeni_kira +
                        '</div>' +

                        '</div>' +

                        '<div class="result-row">' +
                        '<b>Mevcut kira:</b> ' +
                        data.mevcut_kira +
                        '</div>' +

                        '<div class="result-row">' +
                        '<b>Aylık artış:</b> ' +
                        data.artis_tutari +
                        '</div>' +

                        '<div class="result-row">' +
                        '<b>Yenileme dönemi:</b> ' +
                        data.yenileme_donemi +
                        '</div>' +

                        '<div class="result-row">' +
                        '<b>Hedef TÜFE dönemi:</b> ' +
                        data.hedef_tufe_donemi +
                        '</div>' +

                        '<div class="result-row">' +
                        '<b>Kullanılan TÜFE dönemi:</b> ' +
                        data.kullanilan_tufe_donemi +
                        '</div>' +

                        '<div class="result-row">' +
                        '<b>TÜİK yayım tarihi:</b> ' +
                        data.yayim_tarihi +
                        '</div>' +

                        nextInfo +

                        '<div class="result-row">' +
                        '<b>Kaynak:</b> ' +
                        '<a class="source-link" ' +
                        'target="_blank" href="' +
                        data.kaynak +
                        '">' +
                        'TÜİK Veri Portalı' +
                        '</a>' +
                        '</div>' +

                        '<div class="small-note">' +
                        'Hesaplama TÜFE’nin on iki aylık ' +
                        'ortalamalara göre değişim oranını ' +
                        'esas alır.' +
                        '</div>';

                } catch (error) {

                    result.innerHTML =
                        '<div class="error-box">' +
                        error.message +
                        '</div>';

                } finally {

                    button.disabled = false;

                    button.innerText =
                        "Güncel TÜFE ile Hesapla";

                }

            }

        </script>

    </head>


    <body>

    <div class="container">

        <div class="header">
            <h1>Rdv Asistan</h1>
        </div>


        <div class="tabs">

            <button
                class="tab-btn active"
                onclick="switchTab(event, 'kira-tab')"
            >
                🏠 Kira
            </button>

            <button
                class="tab-btn"
                onclick="switchTab(event, 'excel-tab')"
            >
                📊 Excel
            </button>

            <button
                class="tab-btn"
                onclick="switchTab(event, 'pdf-tab')"
            >
                📄 Resim → PDF
            </button>

            <button
                class="tab-btn"
                onclick="switchTab(event, 'pdf2excel-tab')"
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

                <div class="info-text">
                    Hesapla'ya bastığında TÜİK'te
                    yayımlanmış en güncel
                    <b>12 aylık ortalama TÜFE</b>
                    oranı kontrol edilir.
                </div>


                <form
                    onsubmit="kiraHesapla(event)"
                >

                    <label class="field-label">
                        Mevcut Aylık Kira
                    </label>

                    <input
                        id="mevcut-kira"
                        class="input-box"
                        type="number"
                        min="1"
                        step="0.01"
                        placeholder="Örn: 16000"
                        required
                    >


                    <label class="field-label">
                        Kira Yenileme Ayı
                    </label>

                    <select
                        id="yenileme-ayi"
                        class="input-box"
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
                        type="submit"
                        class="btn-run btn-kira"
                    >
                        Güncel TÜFE ile Hesapla
                    </button>

                </form>


                <div
                    id="kira-result"
                    class="kira-result"
                ></div>

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
                            class="file-label"
                            id="xl1"
                        >
                            ＋ 1. Excel (Ana Dosya)
                        </span>

                        <input
                            type="file"
                            name="file1"
                            accept=".xlsx, .xls"
                            required
                            onchange="
                            document.getElementById(
                                'xl1'
                            ).innerText =
                            this.files[0].name
                            "
                        >

                    </div>


                    <div class="file-box">

                        <span
                            class="file-label"
                            id="xl2"
                        >
                            ＋ 2. Excel (Referans Dosyası)
                        </span>

                        <input
                            type="file"
                            name="file2"
                            accept=".xlsx, .xls"
                            required
                            onchange="
                            document.getElementById(
                                'xl2'
                            ).innerText =
                            this.files[0].name
                            "
                        >

                    </div>


                    <div class="command-area">

                        <textarea
                            name="komut"
                            placeholder="Örn: Dosyaları Musteri_ID sütunundan düşeyara yap."
                            required
                        ></textarea>

                    </div>


                    <button
                        type="submit"
                        class="btn-run"
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

                    <div class="info-text">
                        Galeriden istediğin kadar
                        fotoğrafı aynı anda seçip
                        tek bir PDF yapabilirsin.
                    </div>

                    <div class="file-box">

                        <span
                            class="file-label"
                            id="img1"
                        >
                            ＋ Fotoğrafları Seç
                        </span>

                        <input
                            type="file"
                            name="images"
                            accept=".png, .jpg, .jpeg"
                            multiple
                            required
                            onchange="
                            document.getElementById(
                                'img1'
                            ).innerText =
                            this.files.length +
                            ' fotoğraf seçildi'
                            "
                        >

                    </div>

                    <button
                        type="submit"
                        class="btn-run btn-image-pdf"
                    >
                        Sıkıştırıp PDF Yap
                    </button>

                </form>

            </div>


            <!-- PDF EXCEL -->

            <div
                id="pdf2excel-tab"
                class="tab-content"
            >

                <form
                    action="/pdf-excel-islem"
                    method="post"
                    enctype="multipart/form-data"
                >

                    <div class="info-text">
                        İçinde tablo veya liste olan
                        PDF dosyasını düzenlenebilir
                        Excel'e çevir.
                    </div>

                    <div class="file-box">

                        <span
                            class="file-label"
                            id="pdfsrc"
                        >
                            ＋ PDF Dosyasını Seç
                        </span>

                        <input
                            type="file"
                            name="pdf_file"
                            accept=".pdf"
                            required
                            onchange="
                            document.getElementById(
                                'pdfsrc'
                            ).innerText =
                            this.files[0].name
                            "
                        >

                    </div>

                    <button
                        type="submit"
                        class="btn-run btn-pdf-excel"
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
# KİRA HESAPLAMA
# =========================================================

@app.post("/kira-hesapla")
async def kira_hesapla(
    mevcut_kira: float = Form(...),
    yenileme_ayi: int = Form(...),
):

    if mevcut_kira <= 0:
        raise HTTPException(
            status_code=400,
            detail="Kira tutarı 0'dan büyük olmalı.",
        )

    if yenileme_ayi < 1 or yenileme_ayi > 12:
        raise HTTPException(
            status_code=400,
            detail="Geçerli bir yenileme ayı seç.",
        )

    try:

        tufe = find_latest_tufe_bulletin()

    except Exception as e:

        raise HTTPException(
            status_code=503,
            detail=(
                "TÜİK canlı verisine şu anda "
                "ulaşılamadı. "
                f"Detay: {str(e)}"
            ),
        )


    rate = tufe["rate"]

    artis_tutari = mevcut_kira * rate / 100

    yeni_kira = mevcut_kira + artis_tutari


    renewal_year = calculate_next_renewal_month(
        yenileme_ayi
    )


    target_year, target_month = previous_month(
        renewal_year,
        yenileme_ayi,
    )


    current_period = (
        tufe["reference_year"],
        tufe["reference_month"],
    )

    target_period = (
        target_year,
        target_month,
    )


    kesin_mi = current_period == target_period


    if kesin_mi:

        durum_mesaji = (
            f"✅ {MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} yenilemesi için "
            f"gerekli {MONTH_NAMES[target_month]} "
            f"{target_year} TÜFE verisi yayımlanmış."
        )

    elif current_period < target_period:

        durum_mesaji = (
            f"⏳ {MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} yenilemesi için kesin oran "
            f"henüz yayımlanmadı. Şu anki en güncel "
            f"resmi TÜFE oranına göre tahmini kira "
            f"gösteriliyor."
        )

    else:

        durum_mesaji = (
            "ℹ️ Hesap mevcut en güncel resmi "
            "TÜİK oranıyla yapıldı."
        )


    oran_goster = (
        f"{rate:.2f}"
        .replace(".", ",")
    )


    return JSONResponse(
        {
            "oran": oran_goster,

            "mevcut_kira":
                turkish_money(mevcut_kira),

            "artis_tutari":
                turkish_money(artis_tutari),

            "yeni_kira":
                turkish_money(yeni_kira),

            "yenileme_donemi":
                (
                    f"{MONTH_NAMES[yenileme_ayi]} "
                    f"{renewal_year}"
                ),

            "hedef_tufe_donemi":
                (
                    f"{MONTH_NAMES[target_month]} "
                    f"{target_year}"
                ),

            "kullanilan_tufe_donemi":
                tufe["reference_name"],

            "yayim_tarihi":
                tufe["publication_date"],

            "sonraki_tufe_tarihi":
                tufe["next_publication_date"],

            "kaynak":
                tufe["source_url"],

            "kesin_mi":
                kesin_mi,

            "durum_mesaji":
                durum_mesaji,
        }
    )


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
            df_main.columns.str.strip()
        )

        df_ref.columns = (
            df_ref.columns.str.strip()
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

                if col.lower() in komut_lower:

                    ortak_sutun = col
                    break


            if not ortak_sutun:

                ortak_set = list(
                    set(df_main.columns)
                    .intersection(
                        set(df_ref.columns)
                    )
                )

                if ortak_set:

                    ortak_sutun = ortak_set[0]

                else:

                    raise HTTPException(
                        status_code=400,
                        detail="Ortak sütun bulunamadı.",
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

            index_col = None
            value_col = None

            for col in df_main.columns:

                if col.lower() in komut_lower:

                    if (
                        pd.api.types
                        .is_numeric_dtype(
                            df_main[col]
                        )
                        and not value_col
                    ):

                        value_col = col

                    elif not index_col:

                        index_col = col


            if not index_col:
                index_col = df_main.columns[0]

            if not value_col:
                value_col = df_main.columns[1]


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
            detail=f"Excel Hatası: {str(e)}",
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


        for f in images:

            if (
                f.filename
                and any(
                    f.filename.lower().endswith(ext)
                    for ext in [
                        ".jpg",
                        ".jpeg",
                        ".png",
                    ]
                )
            ):

                img = Image.open(
                    io.BytesIO(
                        await f.read()
                    )
                )


                if img.mode in (
                    "RGBA",
                    "LA",
                    "P",
                ):

                    img = img.convert("RGB")


                pil_images.append(img)


        if not pil_images:

            raise HTTPException(
                status_code=400,
                detail="Geçerli resim bulunamadı.",
            )


        output_pdf_path = os.path.join(
            OUTPUT_DIR,
            "rdv_pdf_sonuc.pdf",
        )


        pil_images[0].save(
            output_pdf_path,
            "PDF",
            save_all=True,
            append_images=pil_images[1:],
            quality=65,
        )


        return FileResponse(
            output_pdf_path,
            media_type="application/pdf",
            filename="rdv_pdf_sonuc.pdf",
        )


    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"PDF Hatası: {str(e)}",
        )


# =========================================================
# PDF -> EXCEL
# =========================================================

@app.post("/pdf-excel-islem")
async def pdf_excel_motor(
    pdf_file: UploadFile = File(...)
):

    try:

        pdf_bytes = await pdf_file.read()

        extracted_data = []


        with pdfplumber.open(
            io.BytesIO(pdf_bytes)
        ) as pdf:

            for page in pdf.pages:

                tables = page.extract_tables()


                for table in tables:

                    for row in table:

                        cleaned_row = [
                            str(cell).strip()
                            if cell is not None
                            else ""
                            for cell in row
                        ]

                        extracted_data.append(
                            cleaned_row
                        )


                if not tables:

                    text = page.extract_text()

                    if text:

                        for line in text.split("\n"):

                            if line.strip():

                                extracted_data.append(
                                    line.split()
                                )


        if not extracted_data:

            raise HTTPException(
                status_code=400,
                detail="PDF içinde veri bulunamadı.",
            )


        df = pd.DataFrame(
            extracted_data
        )


        output_excel_path = os.path.join(
            OUTPUT_DIR,
            "pdf_to_excel_sonuc.xlsx",
        )


        df.to_excel(
            output_excel_path,
            index=False,
            header=False,
        )


        return FileResponse(
            output_excel_path,
            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            filename="pdf_to_excel_sonuc.xlsx",
        )


    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"PDF → Excel Hatası: {str(e)}",
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
