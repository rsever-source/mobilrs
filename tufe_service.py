import os
import re
import json
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import redis


TUIK_MAIN = "https://www.tuik.gov.tr/"
TUIK_CALENDAR = "https://www.tuik.gov.tr/Kurumsal/Veri_Takvimi"
TUIK_MEDIA = "https://veriportali.tuik.gov.tr/media/"
TUIK_INDEX = "https://veriportali.tuik.gov.tr/Bulten/Index"
TUIK_BASE = "https://veriportali.tuik.gov.tr"

CACHE_KEY = "rdv:tufe:last_official"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
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


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=25,
    )

    response.raise_for_status()

    return response.text


def get_text(url):
    html = get_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return soup.get_text(
        " ",
        strip=True,
    )


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

        return json.loads(raw)

    except Exception:
        return None


def extract_periods_from_text(text):
    pattern = (
        r"Tüketici\s+Fiyat\s+Endeksi"
        r".{0,120}?"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"[\s,]+(\d{4})"
    )

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE,
    )

    periods = []

    for month_name, year_text in matches:
        month = TR_MONTHS.get(
            month_name.lower()
        )

        if month:
            periods.append(
                (
                    int(year_text),
                    month,
                )
            )

    return periods


def period_from_main_page():
    text = get_text(
        TUIK_MAIN
    )

    periods = []


    # Örnek:
    # Tüketici Fiyat Endeksi-Yıllık (%)
    # 2026/7 (Ay)
    pattern_numeric = (
        r"Tüketici\s+Fiyat\s+Endeksi"
        r".{0,120}?"
        r"(\d{4})\s*/\s*(\d{1,2})"
    )

    for year_text, month_text in re.findall(
        pattern_numeric,
        text,
        re.IGNORECASE,
    ):
        year = int(year_text)
        month = int(month_text)

        if 1 <= month <= 12:
            periods.append(
                (
                    year,
                    month,
                )
            )


    periods.extend(
        extract_periods_from_text(
            text
        )
    )

    if not periods:
        return None

    return max(periods)


def period_from_calendar():
    text = get_text(
        TUIK_CALENDAR
    )

    periods = extract_periods_from_text(
        text
    )

    if not periods:
        return None

    return max(periods)


def period_from_media():
    text = get_text(
        TUIK_MEDIA
    )

    periods = extract_periods_from_text(
        text
    )

    if not periods:
        return None

    return max(periods)


def find_latest_official_period():
    periods = []

    functions = [
        period_from_main_page,
        period_from_calendar,
        period_from_media,
    ]

    for func in functions:
        try:
            result = func()

            if result:
                periods.append(
                    result
                )

        except Exception:
            pass

    if not periods:
        raise RuntimeError(
            "TÜİK'ten güncel TÜFE dönemi belirlenemedi."
        )

    return max(periods)


def candidate_links_from_html(
    html,
    year,
    month,
):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    month_name = (
        MONTH_NAMES[month]
        .lower()
    )

    links = []

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

        combined = (
            label
            + " "
            + href
        ).lower()

        if (
            "tüketici fiyat endeksi"
            not in combined
            and
            "tuketici-fiyat-endeksi"
            not in combined
        ):
            continue

        if month_name not in combined:
            continue

        if str(year) not in combined:
            continue

        full_url = urljoin(
            TUIK_BASE,
            href,
        )

        if (
            "/press/" in full_url.lower()
            or
            "/bulten/" in full_url.lower()
        ):
            links.append(
                full_url
            )

    return list(
        dict.fromkeys(
            links
        )
    )


def bulletin_candidates(
    year,
    month,
):
    candidates = []

    pages = [
        TUIK_MAIN,
        TUIK_MEDIA,
        TUIK_INDEX,
        (
            TUIK_INDEX
            + "?p=Tuketici-Fiyat-Endeksi"
        ),
    ]

    for page in pages:
        try:
            html = get_html(
                page
            )

            candidates.extend(
                candidate_links_from_html(
                    html,
                    year,
                    month,
                )
            )

        except Exception:
            pass

    return list(
        dict.fromkeys(
            candidates
        )
    )


def parse_tufe_bulletin(
    url,
    expected_year=None,
    expected_month=None,
):
    text = get_text(
        url
    )

    if (
        "Tüketici Fiyat Endeksi"
        not in text
    ):
        return None


    period_pattern = (
        r"Tüketici\s+Fiyat\s+Endeksi"
        r"\s*,?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"[\s,]+(\d{4})"
    )

    period_match = re.search(
        period_pattern,
        text,
        re.IGNORECASE,
    )

    if not period_match:
        return None


    month = TR_MONTHS.get(
        period_match
        .group(1)
        .lower()
    )

    year = int(
        period_match.group(2)
    )

    if not month:
        return None


    if (
        expected_year is not None
        and
        year != expected_year
    ):
        return None


    if (
        expected_month is not None
        and
        month != expected_month
    ):
        return None


    # Kira için gereken oran:
    # "on iki aylık ortalamalara göre %31,90"
    patterns = [
        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r".{0,80}?"
            r"%\s*([0-9]{1,3}[,.][0-9]{1,2})"
        ),
        (
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r".{0,80}?"
            r"([0-9]{1,3}[,.][0-9]{1,2})"
        ),
        (
            r"On\s+iki\s+aylık\s+ortalamalara\s+göre\s+değişim\s+oranı"
            r".{0,80}?"
            r"([0-9]{1,3}[,.][0-9]{1,2})"
        ),
    ]


    rate = None

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

            break


    if rate is None:
        raise RuntimeError(
            "12 aylık ortalama TÜFE oranı "
            "resmi bültende bulunamadı."
        )


    if not (
        0 < rate < 200
    ):
        raise RuntimeError(
            "Okunan TÜFE oranı geçersiz."
        )


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


def previous_period(
    year,
    month,
):
    if month == 1:
        return year - 1, 12

    return year, month - 1


def find_bulletin(
    year,
    month,
):
    candidates = bulletin_candidates(
        year,
        month,
    )

    for url in candidates:
        try:
            data = parse_tufe_bulletin(
                url,
                expected_year=year,
                expected_month=month,
            )

            if data:
                return data

        except Exception:
            continue

    return None


def fetch_live_tufe():
    year, month = (
        find_latest_official_period()
    )


    # Önce en güncel dönemi dene.
    # Gerekirse birkaç ay geriye giderek
    # son erişilebilir resmi bülteni bul.
    for _ in range(6):

        data = find_bulletin(
            year,
            month,
        )

        if data:
            data["data_mode"] = "live"

            return data

        year, month = previous_period(
            year,
            month,
        )


    raise RuntimeError(
        "TÜİK'in resmi TÜFE bültenine ulaşılamadı."
    )


def get_current_tufe():
    live_error = None


    try:
        data = fetch_live_tufe()

        save_cache(
            data
        )

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


def update_cache_from_tuik():
    data = fetch_live_tufe()

    if not save_cache(
        data
    ):
        raise RuntimeError(
            "TÜFE verisi alındı fakat Redis'e kaydedilemedi."
        )

    return data
