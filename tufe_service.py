import os
import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import redis


CACHE_KEY = "rdv:tufe:last_official"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
}


MONTHS_TR = {
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


MONTHS_EN = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
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


# =========================================================
# HTTP
# =========================================================

def get_html(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=25,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response.text


def html_to_text(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        " ",
        strip=True,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# =========================================================
# REDIS
# =========================================================

def get_redis_client():

    redis_url = os.environ.get(
        "REDIS_URL",
        "",
    ).strip()

    if not redis_url:
        return None

    try:

        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        client.ping()

        return client

    except Exception:
        return None


def save_cache(data):

    client = get_redis_client()

    if client is None:
        return False

    payload = dict(data)

    payload["cached_at"] = (
        datetime.now(timezone.utc)
        .isoformat()
    )

    try:

        client.set(
            CACHE_KEY,
            json.dumps(
                payload,
                ensure_ascii=False,
            ),
        )

        return True

    except Exception:
        return False


def load_cache():

    client = get_redis_client()

    if client is None:
        return None

    try:

        raw = client.get(
            CACHE_KEY
        )

        if not raw:
            return None

        return json.loads(
            raw
        )

    except Exception:
        return None


# =========================================================
# DÖNEM BUL
# =========================================================

def extract_period(text):

    tr_pattern = (
        r"Tüketici\s+Fiyat\s+Endeksi"
        r"\s*[,–\-]?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+"
        r"(20\d{2})"
    )

    match = re.search(
        tr_pattern,
        text,
        re.IGNORECASE,
    )

    if match:

        month = MONTHS_TR.get(
            match.group(1).lower()
        )

        year = int(
            match.group(2)
        )

        if month:
            return year, month


    en_pattern = (
        r"Consumer\s+Price\s+Index"
        r"\s*[,–\-]?\s*"
        r"(January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
        r"\s+"
        r"(20\d{2})"
    )

    match = re.search(
        en_pattern,
        text,
        re.IGNORECASE,
    )

    if match:

        month = MONTHS_EN.get(
            match.group(1).lower()
        )

        year = int(
            match.group(2)
        )

        if month:
            return year, month


    return None


# =========================================================
# 12 AYLIK ORTALAMA ORANI BUL
# =========================================================

def extract_rate(text):

    patterns = [
        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r"\s*%"
            r"\s*([0-9]{1,3}[,.][0-9]{1,2})"
        ),
        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r".{0,100}?"
            r"%\s*([0-9]{1,3}[,.][0-9]{1,2})"
        ),
        (
            r"On\s+iki\s+aylık\s+ortalamalara\s+göre"
            r"\s+değişim\s+oranı"
            r"\s*"
            r"([0-9]{1,3}[,.][0-9]{1,2})"
        ),
        (
            r"increased\s+by\s+"
            r"([0-9]{1,3}[,.][0-9]{1,2})%"
            r"\s+by\s+the\s+twelve\s+month\s+moving\s+averages"
        ),
        (
            r"Rate\s+of\s+change\s+in\s+12\s+months\s+averages"
            r"\s*"
            r"([0-9]{1,3}[,.][0-9]{1,2})"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            rate = float(
                match
                .group(1)
                .replace(",", ".")
            )

            if 0 < rate < 200:
                return rate

    return None


# =========================================================
# TÜİK PRESS SAYFASI PARSER
# =========================================================

def parse_single_page(url):

    try:

        html = get_html(
            url
        )

        text = html_to_text(
            html
        )

    except Exception:
        return None

    period = extract_period(
        text
    )

    rate = extract_rate(
        text
    )

    if not period:
        return None

    if rate is None:
        return None

    year, month = period

    return {
        "rate": rate,
        "year": year,
        "month": month,
        "period": (
            f"{MONTH_NAMES[month]} "
            f"{year}"
        ),
        "source": url,
    }


def parse_tuik_press_page(source_url):

    parsed = urlparse(
        source_url
    )

    host = (
        parsed.hostname
        or ""
    ).lower()

    if host != "veriportali.tuik.gov.tr":
        return None

    id_match = re.search(
        r"/(?:tr|en)/press/(\d+)",
        parsed.path,
        re.IGNORECASE,
    )

    if not id_match:
        return None

    press_id = id_match.group(1)

    urls = [
        f"https://veriportali.tuik.gov.tr/tr/press/{press_id}",
        f"https://veriportali.tuik.gov.tr/en/press/{press_id}",
        f"https://veriportali.tuik.gov.tr/tr/press/{press_id}/metadata",
        f"https://veriportali.tuik.gov.tr/en/press/{press_id}/metadata",
    ]

    for url in urls:

        data = parse_single_page(
            url
        )

        if data:
            data["source"] = (
                f"https://veriportali.tuik.gov.tr/"
                f"tr/press/{press_id}"
            )
            return data

    return None


# =========================================================
# CANLI TÜİK - DATABROWSER2
# =========================================================

def _jsonstat_pos_to_code(dim):
    index = dim.get("category", {}).get("index") or []
    if isinstance(index, dict):
        return {int(pos): code for code, pos in index.items()}
    return {pos: code for pos, code in enumerate(index)}


def _jsonstat_unravel(flat_index, sizes):
    coords = [0] * len(sizes)
    rem = int(flat_index)
    for i in range(len(sizes) - 1, -1, -1):
        coords[i] = rem % sizes[i]
        rem //= sizes[i]
    return coords


def fetch_live_tufe():
    """Resmi TÜİK DataBrowser2 üzerinden son kira artış TÜFE oranını al."""

    flow = "TR,DF_TUFE_SDMX_TT10,1.0"
    base = (
        "https://databrowser2.tuik.gov.tr/api/core/nodes/1/datasets/"
        + flow
    )

    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    structure_response = requests.get(
        base + "/structure",
        headers=headers,
        timeout=20,
    )
    structure_response.raise_for_status()
    structure = structure_response.json()

    criteria = structure.get("template", {}).get("criteria")
    if not criteria:
        raise RuntimeError("TÜİK DataBrowser2 kriterleri alınamadı.")

    data_response = requests.post(
        base + "/data",
        headers=headers,
        json=criteria,
        timeout=45,
    )
    data_response.raise_for_status()
    payload = data_response.json()

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    dims = payload.get("dimension") or {}
    values = payload.get("value") or {}

    required = {
        "REF_AREA",
        "FREQ",
        "SINIFLAMA_DUZEYI",
        "DEGISIM",
        "COICOP_2018",
        "TIME_PERIOD",
    }
    if not required.issubset(ids) or not values:
        raise RuntimeError("TÜİK DataBrowser2 veri yapısı beklenenden farklı.")

    pos_to_code = {
        dim_id: _jsonstat_pos_to_code(dims[dim_id])
        for dim_id in ids
    }

    matches = []
    for flat, raw_value in values.items():
        coords = _jsonstat_unravel(flat, sizes)
        row = {
            dim_id: pos_to_code[dim_id].get(pos)
            for dim_id, pos in zip(ids, coords)
        }

        if (
            row.get("REF_AREA") == "TR"
            and row.get("FREQ") == "M"
            and row.get("SINIFLAMA_DUZEYI") == "TUFE"
            and row.get("DEGISIM") == "5"
            and row.get("COICOP_2018") == "0"
        ):
            try:
                rate = float(raw_value)
            except (TypeError, ValueError):
                continue

            period_code = str(row.get("TIME_PERIOD") or "")
            if re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", period_code):
                matches.append((period_code, rate))

    if not matches:
        raise RuntimeError("TÜİK 12 aylık ortalama TÜFE serisi bulunamadı.")

    matches.sort(key=lambda item: item[0])
    period_code, rate = matches[-1]

    year = int(period_code[:4])
    month = int(period_code[5:7])

    if not (0 < rate < 200):
        raise RuntimeError("TÜİK oranı geçersiz görünüyor.")

    return {
        "rate": round(rate, 2),
        "year": year,
        "month": month,
        "period": f"{MONTH_NAMES[month]} {year}",
        "source": base,
        "data_mode": "tuik_databrowser2",
    }


# =========================================================
# HESAPLA
# =========================================================

def get_current_tufe():

    live_error = None

    try:
        data = fetch_live_tufe()
        save_cache(data)
        data["data_mode"] = "live"
        return data

    except Exception as exc:
        live_error = str(exc)

    cached = load_cache()

    if cached:
        cached["data_mode"] = "cache"
        cached["live_error"] = live_error
        return cached

    raise RuntimeError(
        "Güncel TÜİK verisi alınamadı ve "
        "kayıtlı son başarılı veri henüz yok."
    )


# =========================================================
# GÜNCELLEME
# =========================================================

def update_cache_from_tuik():

    data = fetch_live_tufe()

    if not save_cache(data):
        raise RuntimeError(
            "TÜFE bulundu fakat Redis'e kaydedilemedi."
        )

    return data
