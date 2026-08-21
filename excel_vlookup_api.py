# =========================================================
# TÜİK - GÜNCEL KİRA TÜFE VERİSİ
# Sabit oran YOK.
# =========================================================

TUIK_MAIN = "https://www.tuik.gov.tr/"
TUIK_MEDIA = "https://veriportali.tuik.gov.tr/media/"
TUIK_PORTAL = "https://veriportali.tuik.gov.tr"
TUIK_CALENDAR = "https://takvim.tuik.gov.tr/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/136.0 Safari/537.36"
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


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    return response.text


def normalize_text(html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    return soup.get_text(
        " ",
        strip=True
    )


# ---------------------------------------------------------
# 1) TÜİK ANA SAYFASINDAN SON TÜFE DÖNEMİNİ BUL
# ---------------------------------------------------------

def period_from_main_page():

    text = normalize_text(
        get_html(TUIK_MAIN)
    )

    # Örnek:
    # Tüketici Fiyat Endeksi-Yıllık (%) 2026/7 (Ay)
    match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi"
        r".{0,100}?"
        r"(\d{4})\s*/\s*(\d{1,2})",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    year = int(match.group(1))
    month = int(match.group(2))

    if month < 1 or month > 12:
        return None

    return year, month


# ---------------------------------------------------------
# 2) VERİ PORTALINDAN SON TÜFE DÖNEMİNİ BUL
# ---------------------------------------------------------

def period_from_media():

    text = normalize_text(
        get_html(TUIK_MEDIA)
    )

    match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi"
        r".{0,100}?"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+(\d{4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    month = TR_MONTHS.get(
        match.group(1).lower()
    )

    year = int(
        match.group(2)
    )

    if not month:
        return None

    return year, month


# ---------------------------------------------------------
# 3) TÜİK TAKVİMİNDEN SON TÜFE DÖNEMİNİ BUL
# ---------------------------------------------------------

def period_from_calendar():

    text = normalize_text(
        get_html(TUIK_CALENDAR)
    )

    matches = re.findall(
        r"Tüketici\s+Fiyat\s+Endeksi"
        r"\s*,?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+(\d{4})",
        text,
        re.IGNORECASE,
    )

    if not matches:
        return None

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

    if not periods:
        return None

    return max(periods)


# ---------------------------------------------------------
# SON DÖNEMİ RESMİ KAYNAKLARDAN BELİRLE
# ---------------------------------------------------------

def find_latest_official_period():

    found = []

    sources = [
        period_from_main_page,
        period_from_media,
        period_from_calendar,
    ]

    for source in sources:

        try:

            result = source()

            if result:
                found.append(result)

        except Exception:
            pass

    if not found:

        raise RuntimeError(
            "TÜİK resmi kaynaklarından "
            "güncel TÜFE dönemi belirlenemedi."
        )

    # Kaynaklardan bulunan en yeni dönem
    return max(found)


# ---------------------------------------------------------
# VERİ PORTALINDA İLGİLİ TÜFE BÜLTENİNİ BUL
# ---------------------------------------------------------

def find_bulletin_url(year, month):

    html = get_html(TUIK_MEDIA)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    target_month = MONTH_NAMES[month]

    possible_urls = []


    # Önce media sayfasındaki linkleri tara
    for a in soup.find_all(
        "a",
        href=True
    ):

        label = " ".join(
            a.stripped_strings
        )

        href = a.get(
            "href",
            ""
        )

        label_lower = label.lower()

        if (
            "tüketici fiyat endeksi"
            in label_lower
            and target_month.lower()
            in label_lower
            and str(year)
            in label_lower
        ):

            full_url = urljoin(
                TUIK_PORTAL,
                href
            )

            if (
                "/press/" in full_url.lower()
                or "/bulten/" in full_url.lower()
            ):

                possible_urls.append(
                    full_url
                )


    # Aynı linkleri temizle
    possible_urls = list(
        dict.fromkeys(
            possible_urls
        )
    )


    # Bulunan adayların gerçekten doğru TÜFE
    # bülteni olduğunu doğrula
    for url in possible_urls:

        try:

            data = parse_bulletin(
                url,
                expected_year=year,
                expected_month=month,
            )

            if data:
                return url

        except Exception:
            continue


    # -----------------------------------------------------
    # Media linki bulunamazsa Veri Portalı genel listesini
    # kontrol et
    # -----------------------------------------------------

    portal_pages = [
        "https://veriportali.tuik.gov.tr/Bulten/Index",
        "https://veriportali.tuik.gov.tr/tr/",
    ]

    for page_url in portal_pages:

        try:

            html = get_html(page_url)

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            for a in soup.find_all(
                "a",
                href=True
            ):

                label = " ".join(
                    a.stripped_strings
                )

                if (
                    "tüketici fiyat endeksi"
                    not in label.lower()
                ):
                    continue

                if (
                    target_month.lower()
                    not in label.lower()
                ):
                    continue

                if str(year) not in label:
                    continue

                full_url = urljoin(
                    TUIK_PORTAL,
                    a["href"]
                )

                try:

                    data = parse_bulletin(
                        full_url,
                        expected_year=year,
                        expected_month=month,
                    )

                    if data:
                        return full_url

                except Exception:
                    continue

        except Exception:
            continue


    raise RuntimeError(
        f"{target_month} {year} "
        "TÜFE haber bülteni bulunamadı."
    )


# ---------------------------------------------------------
# BÜLTENDEN 12 AYLIK ORTALAMA TÜFE'Yİ OKU
# ---------------------------------------------------------

def parse_bulletin(
    url,
    expected_year=None,
    expected_month=None,
):

    text = normalize_text(
        get_html(url)
    )


    if "Tüketici Fiyat Endeksi" not in text:

        return None


    # Bülten dönemini doğrula
    period_match = re.search(
        r"Tüketici\s+Fiyat\s+Endeksi"
        r"\s*,?\s*"
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+(\d{4})",
        text,
        re.IGNORECASE,
    )


    if not period_match:

        return None


    month = TR_MONTHS.get(
        period_match.group(1).lower()
    )

    year = int(
        period_match.group(2)
    )


    if (
        expected_year is not None
        and year != expected_year
    ):

        return None


    if (
        expected_month is not None
        and month != expected_month
    ):

        return None


    # -----------------------------------------------------
    # ÖNEMLİ:
    # İlk paragraftaki GENEL TÜFE'nin
    # 12 AYLIK ORTALAMA oranını al.
    #
    # Temmuz 2026 örneği:
    # "... on iki aylık ortalamalara göre
    # %31,90 artış olarak gerçekleşti."
    # -----------------------------------------------------

    rate_match = re.search(
        r"TÜFE(?:'deki|'ndeki)?"
        r".{0,700}?"
        r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
        r"\s*%?\s*"
        r"([0-9]{1,3}[,.][0-9]{1,2})",
        text,
        re.IGNORECASE,
    )


    # İlk kalıp yakalayamazsa genel alternatif
    if not rate_match:

        rate_match = re.search(
            r"on\s+iki\s+aylık\s+ortalamalara\s+göre"
            r"\s*%?\s*"
            r"([0-9]{1,3}[,.][0-9]{1,2})"
            r"\s+artış\s+olarak\s+gerçekleşti",
            text,
            re.IGNORECASE,
        )


    if not rate_match:

        raise RuntimeError(
            "TÜİK bülteninde "
            "12 aylık ortalama TÜFE oranı bulunamadı."
        )


    rate = float(
        rate_match
        .group(1)
        .replace(",", ".")
    )


    # Mantık kontrolü
    if rate <= 0 or rate > 200:

        raise RuntimeError(
            "Okunan TÜFE oranı mantıksız görünüyor."
        )


    return {
        "rate": rate,
        "year": year,
        "month": month,
        "period": (
            f"{MONTH_NAMES[month]} {year}"
        ),
        "source": url,
    }


# ---------------------------------------------------------
# ANA FONKSİYON
# ---------------------------------------------------------

def find_latest_tufe():

    # 1. Son resmi dönemi bul
    year, month = (
        find_latest_official_period()
    )

    # 2. O dönemin resmi haber bültenini bul
    bulletin_url = find_bulletin_url(
        year,
        month
    )

    # 3. Bültenin içinden kira için gereken
    # 12 aylık ortalama TÜFE oranını çek
    data = parse_bulletin(
        bulletin_url,
        expected_year=year,
        expected_month=month,
    )

    if not data:

        raise RuntimeError(
            "Güncel TÜFE verisi okunamadı."
        )

    return data
