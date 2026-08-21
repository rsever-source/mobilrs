import os
import re
import json
from datetime import datetime, timezone
from urllib.parse import quote_plus, unquote

import requests
from bs4 import BeautifulSoup
import redis


# =========================================================
# AYARLAR
# =========================================================

CACHE_KEY = "rdv:tufe:last_official"

TUIK_PRESS_PREFIX = (
    "https://veriportali.tuik.gov.tr/tr/press/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}


MONTHS = {
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


# =========================================================
# HTTP
# =========================================================

def get_html(url, timeout=20):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
    )

    response.raise_for_status()

    return response.text


def html_to_text(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return soup.get_text(
        " ",
        strip=True,
    )


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
# RESMİ TÜİK SAYFASINI OKU
# =========================================================

def parse_tuik_press_page(url):

    try:

        html = get_html(
            url
        )

    except Exception:
        return None


    text = html_to_text(
        html
    )


    if not re.search(
        r"Tüketici\s+Fiyat\s+Endeksi",
        text,
        re.IGNORECASE,
    ):
        return None


    # -----------------------------------------------------
    # DÖNEM
    #
    # Örn:
    # Tüketici Fiyat Endeksi, Temmuz 2026
    # -----------------------------------------------------

    period_pattern = (
        r"Tüketici\s+Fiyat\s+Endeksi"
        r"\s*[,–\-]?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+"
        r"(20\d{2})"
    )


    period_match = re.search(
        period_pattern,
        text,
        re.IGNORECASE,
    )


    if not period_match:
        return None


    month_name_raw = (
        period_match
        .group(1)
        .lower()
    )

    year = int(
        period_match.group(2)
    )

    month = MONTHS.get(
        month_name_raw
    )


    if not month:
        return None


    # -----------------------------------------------------
    # 12 AYLIK ORTALAMA
    #
    # Resmi bültendeki paragraf:
    # "... on iki aylık ortalamalara göre %31,90 ..."
    # -----------------------------------------------------

    rate_patterns = [

        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r"\s*%"
            r"\s*([0-9]{1,3}[,.][0-9]{1,2})"
        ),

        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r".{0,50}?"
            r"%\s*([0-9]{1,3}[,.][0-9]{1,2})"
        ),

        (
            r"On\s+iki\s+aylık\s+ortalamalara\s+göre"
            r"\s+değişim\s+oranı"
            r".{0,100}?"
            r"([0-9]{1,3}[,.][0-9]{1,2})"
        ),
    ]


    rate = None


    for pattern in rate_patterns:

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

            break


    if rate is None:
        return None


    if not (
        0 < rate < 200
    ):
        return None


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


# =========================================================
# ARAMA SONUÇLARINDAN SADECE TÜİK /press/ LINKLERİNİ BUL
# =========================================================

def extract_press_urls(html):

    # URL encode edilmiş olabileceği için çöz
    html = unquote(
        html
    )


    pattern = (
        r"https?://"
        r"veriportali\.tuik\.gov\.tr"
        r"/tr/press/"
        r"\d+"
    )


    urls = re.findall(
        pattern,
        html,
        re.IGNORECASE,
    )


    # tekrarları kaldır
    return list(
        dict.fromkeys(
            urls
        )
    )


# =========================================================
# BING
# =========================================================

def search_bing():

    query = (
        'site:veriportali.tuik.gov.tr/tr/press/ '
        '"Tüketici Fiyat Endeksi"'
    )


    url = (
        "https://www.bing.com/search?q="
        + quote_plus(query)
        + "&count=30"
    )


    html = get_html(
        url
    )


    return extract_press_urls(
        html
    )


# =========================================================
# DUCKDUCKGO YEDEK
# =========================================================

def search_duckduckgo():

    query = (
        'site:veriportali.tuik.gov.tr/tr/press/ '
        '"Tüketici Fiyat Endeksi"'
    )


    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(query)
    )


    html = get_html(
        url
    )


    return extract_press_urls(
        html
    )


# =========================================================
# TÜİK SAYFALARINI KEŞFET
# =========================================================

def discover_tuik_press_urls():

    urls = []


    # Bing
    try:

        urls.extend(
            search_bing()
        )

    except Exception:
        pass


    # DuckDuckGo
    try:

        urls.extend(
            search_duckduckgo()
        )

    except Exception:
        pass


    urls = list(
        dict.fromkeys(
            urls
        )
    )


    if not urls:

        raise RuntimeError(
            "TÜİK TÜFE bülten bağlantıları bulunamadı."
        )


    return urls


# =========================================================
# EN YENİ RESMİ TÜİK VERİSİ
# =========================================================

def fetch_live_tufe():

    urls = discover_tuik_press_urls()


    valid_results = []


    for url in urls:

        try:

            data = parse_tuik_press_page(
                url
            )

            if data:

                valid_results.append(
                    data
                )

        except Exception:
            continue


    if not valid_results:

        raise RuntimeError(
            "Resmi TÜİK TÜFE bültenleri bulundu "
            "ancak 12 aylık ortalama oran okunamadı."
        )


    # En yeni dönem
    latest = max(
        valid_results,
        key=lambda x: (
            int(x["year"]),
            int(x["month"]),
        ),
    )


    latest["data_mode"] = (
        "live"
    )


    return latest


# =========================================================
# HESAPLA:
#
# 1. CANLI
# 2. REDIS
# =========================================================

def get_current_tufe():

    live_error = None


    try:

        data = fetch_live_tufe()


        # Başarılı canlı veriyi Redis'e yaz
        save_cache(
            data
        )


        data["data_mode"] = (
            "live"
        )


        return data


    except Exception as exc:

        live_error = str(
            exc
        )


    # -----------------------------------------------------
    # CANLI ÇALIŞMADI -> REDIS
    # -----------------------------------------------------

    cached = load_cache()


    if cached:

        cached["data_mode"] = (
            "cache"
        )

        cached["live_error"] = (
            live_error
        )

        return cached


    raise RuntimeError(
        "Güncel TÜİK verisi alınamadı ve "
        "kayıtlı son başarılı veri henüz yok. "
        f"Canlı hata: {live_error}"
    )


# =========================================================
# SPARK GÜNLÜK GÜNCELLEME
# =========================================================

def update_cache_from_tuik():

    data = fetch_live_tufe()


    if not save_cache(
        data
    ):

        raise RuntimeError(
            "TÜFE bulundu fakat Redis'e kaydedilemedi."
        )


    return data
