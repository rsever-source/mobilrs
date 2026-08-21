import os
import re
import json
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
import redis


TUIK_MAIN = "https://www.tuik.gov.tr/"
TUIK_BASE = "https://veriportali.tuik.gov.tr"

CACHE_KEY = "rdv:tufe:last_official"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
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


MONTH_SLUGS = {
    1: "Ocak",
    2: "Subat",
    3: "Mart",
    4: "Nisan",
    5: "Mayis",
    6: "Haziran",
    7: "Temmuz",
    8: "Agustos",
    9: "Eylul",
    10: "Ekim",
    11: "Kasim",
    12: "Aralik",
}


def get_html(url):
    r = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )

    r.raise_for_status()

    return r.text


def html_to_text(html):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return soup.get_text(
        " ",
        strip=True,
    )


def get_text(url):
    return html_to_text(
        get_html(url)
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
# TÜİK ANA SAYFA -> SON TÜFE DÖNEMİ
# =========================================================

def find_latest_period():

    text = get_text(
        TUIK_MAIN
    )

    patterns = [
        (
            r"Tüketici\s+Fiyat\s+Endeksi"
            r".{0,150}?"
            r"(\d{4})\s*/\s*(\d{1,2})"
        ),
        (
            r"TÜFE"
            r".{0,150}?"
            r"(\d{4})\s*/\s*(\d{1,2})"
        ),
    ]

    periods = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        for year_text, month_text in matches:

            year = int(
                year_text
            )

            month = int(
                month_text
            )

            if 1 <= month <= 12:

                periods.append(
                    (
                        year,
                        month,
                    )
                )

    if not periods:

        raise RuntimeError(
            "TÜİK ana sayfasından son TÜFE dönemi bulunamadı."
        )

    return max(periods)


# =========================================================
# BÜLTEN ORANINI OKU
# =========================================================

def parse_bulletin(
    url,
    expected_year,
    expected_month,
):

    try:

        text = get_text(
            url
        )

    except Exception:
        return None


    if (
        "Tüketici Fiyat Endeksi"
        not in text
    ):
        return None


    month_name = (
        MONTH_NAMES[
            expected_month
        ]
    )

    period_checks = [
        f"{month_name} {expected_year}",
        f"{month_name}, {expected_year}",
    ]

    if not any(
        x.lower() in text.lower()
        for x in period_checks
    ):

        return None


    patterns = [
        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r".{0,120}?"
            r"%\s*([0-9]{1,3}[,.][0-9]{1,2})"
        ),
        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r".{0,120}?"
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
                match.group(1)
                .replace(",", ".")
            )

            if 0 < rate < 200:

                return {
                    "rate": rate,
                    "year": expected_year,
                    "month": expected_month,
                    "period": (
                        f"{month_name} "
                        f"{expected_year}"
                    ),
                    "source": url,
                }


    return None


# =========================================================
# RESMİ BÜLTEN URL'SİNİ BUL
# =========================================================

def candidate_urls(
    year,
    month,
):

    month_slug = (
        MONTH_SLUGS[
            month
        ]
    )

    slug = (
        "Tuketici-Fiyat-Endeksi-"
        f"{month_slug}-{year}"
    )


    candidates = []


    # 1) TÜİK'in bülten index URL yapısı
    candidates.append(
        (
            f"{TUIK_BASE}/Bulten/Index"
            f"?dil=1&p={slug}"
        )
    )


    # 2) Aynı sayfanın dil parametresiz hali
    candidates.append(
        (
            f"{TUIK_BASE}/Bulten/Index"
            f"?p={slug}"
        )
    )


    # 3) Arama motorundan değil,
    # TÜİK ana sayfasındaki HTML içinde
    # bülten URL/id yakalamaya çalış
    try:

        html = get_html(
            TUIK_MAIN
        )

        press_ids = re.findall(
            r"(?:press|Bulten/Index)"
            r"[^\"']{0,100}?"
            r"(\d{5})",
            html,
            re.IGNORECASE,
        )

        for bulletin_id in press_ids:

            candidates.append(
                (
                    f"{TUIK_BASE}/tr/press/"
                    f"{bulletin_id}"
                )
            )

    except Exception:
        pass


    return list(
        dict.fromkeys(
            candidates
        )
    )


def find_bulletin(
    year,
    month,
):

    urls = candidate_urls(
        year,
        month,
    )

    for url in urls:

        data = parse_bulletin(
            url,
            year,
            month,
        )

        if data:
            return data

    return None


def previous_period(
    year,
    month,
):

    if month == 1:
        return (
            year - 1,
            12,
        )

    return (
        year,
        month - 1,
    )


# =========================================================
# CANLI TÜİK
# =========================================================

def fetch_live_tufe():

    year, month = (
        find_latest_period()
    )


    # Son dönem bültenine ulaşılamazsa
    # birkaç ay geriye doğru dene.
    for _ in range(6):

        data = find_bulletin(
            year,
            month,
        )

        if data:

            data["data_mode"] = (
                "live"
            )

            return data


        year, month = (
            previous_period(
                year,
                month,
            )
        )


    raise RuntimeError(
        "TÜİK'in resmi TÜFE bülteninden "
        "12 aylık ortalama oran okunamadı."
    )


# =========================================================
# CANLI -> REDIS FALLBACK
# =========================================================

def get_current_tufe():

    live_error = None

    try:

        data = fetch_live_tufe()

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
        "Güncel TÜİK verisi alınamadı "
        "ve kayıtlı son başarılı veri henüz yok."
    )


# =========================================================
# SPARK / GÜNLÜK GÜNCELLEME İÇİN
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
