# =========================================================
# TÜİK CANLI TÜFE VERİSİ
# =========================================================

TUIK_MEDIA_URL = "https://veriportali.tuik.gov.tr/media/"
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


def get_latest_tufe_period():
    """
    TÜİK media sayfasındaki 'En Son Veriler' tablosundan
    en güncel Tüketici Fiyat Endeksi dönemini bulur.
    Örn: Temmuz 2026
    """

    response = requests.get(
        TUIK_MEDIA_URL,
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

    # Örn:
    # Tüketici Fiyat Endeksi Temmuz 2026 Haber Bülteni
    match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi\s+"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|"
        r"Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+(\d{4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        raise RuntimeError(
            "TÜİK media sayfasında güncel TÜFE dönemi bulunamadı."
        )

    month_name_raw = match.group(1)
    month_key = month_name_raw.lower()

    month = TR_MONTHS.get(month_key)
    year = int(match.group(2))

    if not month:
        raise RuntimeError(
            "TÜFE ayı çözümlenemedi."
        )

    return {
        "year": year,
        "month": month,
        "period": f"{MONTH_NAMES[month]} {year}",
    }


def find_official_tufe_bulletin(period_info):
    """
    TÜİK media sayfasındaki linklerden
    ilgili en güncel TÜFE haber bültenini bulur.
    """

    response = requests.get(
        TUIK_MEDIA_URL,
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    target_period = period_info["period"].lower()

    candidates = []

    for a in soup.find_all("a", href=True):
        label = " ".join(
            a.stripped_strings
        ).lower()

        href = a.get("href", "")

        if (
            "tüketici fiyat endeksi" in label
            and target_period in label
        ):
            full_url = urljoin(
                TUIK_BASE,
                href,
            )

            if (
                "/press/" in full_url.lower()
                or "/bulten/" in full_url.lower()
            ):
                candidates.append(
                    full_url
                )

    candidates = list(
        dict.fromkeys(candidates)
    )

    if not candidates:
        raise RuntimeError(
            f"{period_info['period']} TÜFE bülteni linki bulunamadı."
        )

    return candidates[0]


def read_tufe_bulletin(url: str):
    """
    Resmi TÜFE bülteninden kira artışında kullanılan
    'on iki aylık ortalamalara göre değişim oranı'nı alır.
    """

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
        raise RuntimeError(
            "Açılan sayfa TÜFE bülteni değil."
        )

    rate_match = re.search(
        r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
        r".{0,80}?%?\s*([0-9]{1,3}[,.][0-9]{1,2})",
        text,
        re.IGNORECASE,
    )

    if not rate_match:
        raise RuntimeError(
            "12 aylık ortalama TÜFE oranı bulunamadı."
        )

    rate = float(
        rate_match.group(1).replace(",", ".")
    )

    period_match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi\s*,?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|"
        r"Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+(\d{4})",
        text,
        re.IGNORECASE,
    )

    if not period_match:
        raise RuntimeError(
            "Bülten dönemi bulunamadı."
        )

    month = TR_MONTHS[
        period_match.group(1).lower()
    ]

    year = int(
        period_match.group(2)
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
    }


def find_latest_tufe():
    """
    Sabit oran kullanmaz.
    Her Hesapla tıklamasında:
    1) TÜİK media sayfasından son dönemi bulur
    2) resmi bülteni bulur
    3) 12 aylık ortalama oranı bültenden çeker
    """

    period_info = get_latest_tufe_period()

    bulletin_url = find_official_tufe_bulletin(
        period_info
    )

    tufe = read_tufe_bulletin(
        bulletin_url
    )

    return tufe
