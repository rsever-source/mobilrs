import io
import json
import re
import unicodedata
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import pdfplumber
import requests
from bs4 import BeautifulSoup

LIMIT_2026 = 2_873_900
MIN_LOCALITY = 40.0
CACHE_FILE = "otv_cache.json"
TZ = ZoneInfo("Europe/Istanbul")

MINISTRY_PAGE = "https://www.sanayi.gov.tr/merkez-birimi/6f188a931f68/yerli-mali"
MINISTRY_PDF = "https://www.sanayi.gov.tr/assets/pdf/birimler/2026YiliMotorluAraclarYerliKatkiOraniBeyanlari.pdf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
}

# Uygun araç listesi burada tutulmaz. Adaylar yalnız Bakanlığın 2026 yerli katkı
# beyanından gelir; aşağıdakiler üretici/marka bazlı fiyat okuma kaynaklarıdır.
RENAULT_PACKAGE_URLS = {
    ("BOREAL", "EVOLUTION"): "https://www.renault.com.tr/hybrid-araclar/boreal/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM1",
    ("BOREAL", "TECHNO"): "https://www.renault.com.tr/hybrid-araclar/boreal/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM2",
    ("BOREAL", "ICONIC"): "https://www.renault.com.tr/hybrid-araclar/boreal/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM3",
    ("DUSTER", "EVOLUTION"): "https://www.renault.com.tr/hybrid-araclar/yeni-renault-duster/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM1",
    ("DUSTER", "TECHNO"): "https://www.renault.com.tr/hybrid-araclar/yeni-renault-duster/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM2",
    ("CLIO", "EVOLUTION PLUS"): "https://www.renault.com.tr/hybrid-araclar/yeni-clio/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM1",
    ("CLIO", "ESPRIT ALPINE"): "https://www.renault.com.tr/hybrid-araclar/yeni-clio/modeller-versiyonlar.html?gradeCode=ENS_MDL2P1SERIELIM2",
    ("MEGANE", "TOUCH"): "https://www.renault.com.tr/binek-araclar/megane-sedan.html",
    ("MEGANE", "ICON"): "https://www.renault.com.tr/binek-araclar/megane-sedan.html",
}

TOYOTA_PRICE_URL = "https://turkiye.toyota.com.tr/middle/fiyat-listesi/"
HYUNDAI_DEALER_URL = "https://ferhat.hyundaiplaza.com.tr/fiyat-listesi"
FIAT_DEALER_URL = "https://www.tanoto.com.tr/fiat-fiyat-listesi/"
FIAT_ULYSSE_URL = "https://www.tanoto.com.tr/arac-detay/ulysse/"
TOGG_URLS = {
    "T10X": "https://togg.com.tr/price-list",
    "T10F": "https://www.togg.com.tr/t10f-price-list",
}


def _clean(v):
    return re.sub(r"\s+", " ", str(v or "").replace("\n", " ")).strip()


def _norm(v):
    s = unicodedata.normalize("NFKD", _clean(v))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).upper().replace("İ", "I")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", s)).strip()


def _ratio(v):
    m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)", str(v or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def _money(v):
    d = re.sub(r"\D", "", str(v or ""))
    return int(d) if d else None


def _get(url, timeout=35):
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


def _page(url):
    r = _get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    visible = BeautifulSoup(r.text, "html.parser")
    for tag in visible(["script", "style", "noscript"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", visible.get_text(" ", strip=True))
    raw = re.sub(r"\s+", " ", r.text)
    return soup, text, raw


def _find_ministry_pdf():
    try:
        r = _get(MINISTRY_PDF)
        if r.content[:4] == b"%PDF":
            return MINISTRY_PDF, r.content
    except Exception:
        pass

    soup = BeautifulSoup(_get(MINISTRY_PAGE).text, "html.parser")
    for a in soup.find_all("a", href=True):
        label = _norm(a.get_text(" ", strip=True))
        if "2026" not in label or "MOTORLU" not in label or "YERLI" not in label:
            continue
        href = urljoin(MINISTRY_PAGE, a["href"])
        rr = _get(href)
        if rr.content[:4] == b"%PDF":
            return href, rr.content
    raise RuntimeError("Bakanlığın 2026 yerli katkı PDF'i indirilemedi")


def _parse_ministry_pdf(pdf_bytes):
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table or []:
                    if not row or len(row) < 11:
                        continue
                    c = [_clean(x) for x in row]
                    locality = _ratio(c[-2])
                    if locality is None:
                        continue
                    brand, model, category, trim = c[2], c[3], c[4], c[8]
                    if not brand or not model or not trim:
                        continue
                    if not re.search(r"(?:^|\s)M1(?:\s|$|[-–])", category.upper()):
                        continue
                    rows.append({
                        "brand": "Togg" if _norm(brand) == "TOGG" else brand.title(),
                        "brand_key": _norm(brand),
                        "model": model,
                        "model_key": _norm(model),
                        "trim": trim,
                        "locality": locality,
                    })
    if not rows:
        raise RuntimeError("Bakanlık PDF'inden M1 araç kayıtları okunamadı")
    return rows


def _eligible_packages(rows):
    """Motor/şanzımanı kullanıcıya göstermeden model+paket düzeyinde tekilleştir."""
    out = {}
    for r in rows:
        if r["locality"] < MIN_LOCALITY:
            continue
        key = (r["brand_key"], r["model_key"], _norm(r["trim"]))
        old = out.get(key)
        if old is None or r["locality"] > old["locality"]:
            out[key] = dict(r)
    return list(out.values())


def _prices(text, minimum=1_000_000, maximum=15_000_000):
    vals = []
    pat = r"(?:₺\s*)?([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?\s*(?:₺|TL)?"
    for m in re.finditer(pat, text, re.I):
        v = _money(m.group(1))
        if v and minimum <= v <= maximum:
            vals.append((m.start(), v))
    return vals


def _first_price_after(text, phrase, max_chars=650):
    low = text.lower()
    p = low.find(phrase.lower())
    if p < 0:
        return None
    vals = _prices(text[p:p + max_chars])
    return vals[0][1] if vals else None


def _table_rows(soup):
    rows = []
    for tr in soup.find_all("tr"):
        cells = [_clean(c.get_text(" ", strip=True)) for c in tr.find_all(["th", "td"])]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        heading = tr.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        context = _clean(heading.get_text(" ", strip=True)) if heading else ""
        rows.append((context, cells))
    return rows


def _section_after(text, heading, next_headings, start_at=0):
    low = text.lower()
    start = low.find(heading.lower(), max(0, start_at))
    if start < 0:
        return ""
    ends = []
    for h in next_headings:
        p = low.find(h.lower(), start + len(heading))
        if p > start:
            ends.append(p)
    end = min(ends) if ends else min(len(text), start + 16000)
    return text[start:end]


# ---------- Renault ----------

def _renault_price(item, cache):
    key = (_norm(item["model"]), _norm(item["trim"]))
    url = RENAULT_PACKAGE_URLS.get(key)
    if not url:
        return None
    if url not in cache:
        cache[url] = _page(url)
    _soup, text, raw = cache[url]
    trim = _clean(item["trim"])
    for source in (text, raw):
        for phrase in (f"versiyon {trim}", trim):
            price = _first_price_after(source, phrase, 750)
            if price:
                return price, url
    return None


# ---------- Toyota ----------

def _toyota_target(item):
    n = _norm(item["trim"])
    n = n.replace("TOYOTA", " ")
    model = _norm(item["model"])
    if model == "C HR":
        n = n.replace("C HR", " ")
    else:
        n = n.replace(model, " ")
    n = re.sub(r"\bMDS\b", "MULTIDRIVE S", n)
    n = n.replace("ECVT", "E CVT")
    return re.sub(r"\s+", " ", n).strip()


def _toyota_context_ok(model_key, context):
    c = _norm(context)
    if model_key == "C HR":
        return "C HR" in c
    if model_key == "COROLLA":
        return "COROLLA" in c and "CROSS" not in c and "HATCHBACK" not in c
    return False


def _toyota_price(item, cache):
    url = TOYOTA_PRICE_URL
    if url not in cache:
        cache[url] = _page(url)
    soup, text, _raw = cache[url]
    target = _toyota_target(item)
    model_key = _norm(item["model"])
    if not target:
        return None

    # Birincil yol: Toyota'nın HTML fiyat tablolarındaki versiyon satırını okuyup
    # ilk normal/tavsiye edilen liste fiyatını al.
    matches = []
    for context, cells in _table_rows(soup):
        if not _toyota_context_ok(model_key, context):
            continue
        row_name = _norm(cells[0])
        if target not in row_name and row_name not in target:
            continue
        row_prices = []
        for cell in cells[1:]:
            row_prices.extend(v for _, v in _prices(cell, 1_000_000, 6_000_000))
        if row_prices:
            matches.append(row_prices[0])
    if matches:
        return min(matches), url

    # Fallback: sayfanın görünür metninde yalnız ilgili model bloğunda ara.
    marker = text.lower().find("toyota fiyat listesi")
    if model_key == "COROLLA":
        section = _section_after(text, "Corolla", ["Toyota C-HR Hybrid", "C-HR Hybrid", "Corolla Cross"], marker)
    elif model_key == "C HR":
        section = _section_after(text, "C-HR Hybrid", ["Corolla Cross", "Yaris", "RAV4"], marker)
        if not section:
            section = _section_after(text, "Toyota C-HR Hybrid", ["Corolla Cross", "Yaris", "RAV4"], marker)
    else:
        return None
    ns = _norm(section)
    pos = ns.find(target)
    if pos < 0:
        return None

    # Normalizasyon metni uzatıp kısaltabildiğinden paket adının ayırt edici
    # kelimeleri üzerinden özgün metinde tekrar konum bul.
    words = [w for w in target.split() if len(w) >= 4 and w not in {"HYBRID", "MULTIDRIVE"}]
    low = section.lower()
    starts = []
    for w in words:
        p = low.find(w.lower())
        if p >= 0:
            starts.append(p)
    if not starts:
        return None
    p = min(starts)
    vals = _prices(section[p:p + 650], 1_000_000, 6_000_000)
    return (vals[0][1], url) if vals else None


# ---------- Togg ----------

def _togg_alias(item):
    n = _norm(item["trim"])
    model = _norm(item["model"])
    if n.startswith(model + " "):
        n = n[len(model):].strip()
    aliases = {
        "V1 SR": "V1 RWD STANDART MENZIL",
        "V1 LR": "V1 RWD UZUN MENZIL",
        "V2 LR": "V2 RWD UZUN MENZIL",
        "V2 LR AWD": "V2 4MORE",
    }
    return aliases.get(n)


def _togg_price(item, cache):
    model = _norm(item["model"])
    url = TOGG_URLS.get(model)
    alias = _togg_alias(item)
    if not url or not alias:
        return None
    if url not in cache:
        cache[url] = _page(url)
    _soup, text, raw = cache[url]
    source = text if "Teslim Fiyat" in text else raw
    start = source.lower().find("teslim fiyat")
    if start < 0:
        return None
    vals = [v for _, v in _prices(source[start:start + 1400], 1_000_000, 6_000_000)]
    versions = ["V1 RWD STANDART MENZIL", "V1 RWD UZUN MENZIL", "V2 RWD UZUN MENZIL", "V2 4MORE"]
    if len(vals) < len(versions) or alias not in versions:
        return None
    return vals[versions.index(alias)], url


# ---------- Hyundai ----------

def _hyundai_model_ok(model_key, context):
    c = _norm(context)
    if model_key == "I20":
        return "I20" in c
    if model_key == "BAYON":
        return "BAYON" in c
    return False


def _hyundai_price(item, cache):
    url = HYUNDAI_DEALER_URL
    if url not in cache:
        cache[url] = _page(url)
    soup, text, _raw = cache[url]
    model = _norm(item["model"])
    trim = _norm(item["trim"]).replace("SYTLE", "STYLE")

    # Birincil yol: yetkili Hyundai satıcısının güncel tablo satırı.
    matches = []
    for context, cells in _table_rows(soup):
        if not _hyundai_model_ok(model, context):
            continue
        version = _norm(cells[0])
        if trim not in version:
            continue
        vals = []
        for cell in cells[1:]:
            vals.extend(v for _, v in _prices(cell, 1_000_000, 5_000_000))
        if vals:
            # Tabloda ilk büyük tutar azami/maksimum liste fiyatıdır.
            matches.append(vals[0])
    if matches:
        return min(matches), url

    # Fallback: navigasyon menüsündeki i20/BAYON isimlerine takılmamak için fiyat
    # listesi başlangıç işaretinden sonra model bloğunu seç.
    marker = text.lower().find("azami / maksimum satış fiyatları")
    if marker < 0:
        marker = text.lower().find("maksimum satış fiyatları")
    if model == "I20":
        section = _section_after(text, "i20", ["i30", "BAYON"], marker)
    elif model == "BAYON":
        section = _section_after(text, "BAYON", ["KONA", "TUCSON"], marker)
    else:
        return None
    if not section:
        return None

    low = section.lower()
    prices = []
    aliases = [trim.lower()]
    if trim == "STYLE":
        aliases.append("sytle")
    for alias in aliases:
        for hit in re.finditer(r"\b" + re.escape(alias) + r"\b", low, re.I):
            vals = _prices(section[hit.start():hit.start() + 350], 1_000_000, 5_000_000)
            if vals:
                prices.append(vals[0][1])
    return (min(prices), url) if prices else None


# ---------- Fiat ----------

def _fiat_model_ok(model_key, context):
    c = _norm(context)
    if model_key == "EGEA SEDAN":
        return "EGEA SEDAN" in c
    if model_key == "EGEA CROSS":
        return "EGEA CROSS" in c and "WAGON" not in c
    return False


def _fiat_price(item, cache):
    model = _norm(item["model"])

    # Ulysse binek fiyat tablosunda her zaman görünmeyebildiği için yetkili satıcının
    # güncel Ulysse model sayfasındaki başlangıç/listelenen fiyatı kullan.
    if model == "ULYSSE":
        url = FIAT_ULYSSE_URL
        if url not in cache:
            cache[url] = _page(url)
        _soup, text, _raw = cache[url]
        vals = _prices(text, 1_000_000, 6_000_000)
        if not vals:
            return None
        # Sayfanın en üstündeki araç fiyatı ilk büyük tutardır.
        return vals[0][1], url

    url = FIAT_DEALER_URL
    if url not in cache:
        cache[url] = _page(url)
    soup, text, _raw = cache[url]

    # Bakanlık Fiat Egea için donanımı "Standart Donanım" diye beyan ediyor.
    # Ekranda motor/şanzıman istemediğimiz için modelin güncel en düşük normal liste
    # fiyatını gösteriyoruz; farklı satış paketlerini uygunmuş gibi uydurmuyoruz.
    if _norm(item["trim"]) != "STANDART DONANIM":
        return None

    matches = []
    for context, cells in _table_rows(soup):
        if not _fiat_model_ok(model, context):
            continue
        vals = []
        for cell in cells[1:]:
            vals.extend(v for _, v in _prices(cell, 1_000_000, 6_000_000))
        if vals:
            matches.append(vals[0])
    if matches:
        return min(matches), url

    marker = text.lower().find("güncelleme tarihi")
    if model == "EGEA SEDAN":
        section = _section_after(text, "Egea Sedan", ["Egea Cross", "Grande Panda"], marker)
    elif model == "EGEA CROSS":
        section = _section_after(text, "Egea Cross", ["Grande Panda", "500e", "600"], marker)
    else:
        return None
    vals = _prices(section, 1_000_000, 6_000_000)
    return (min(v for _, v in vals), url) if vals else None


# ---------- Ortak ----------

def _resolve_price(item, cache):
    brand = _norm(item["brand"])
    if brand == "RENAULT":
        return _renault_price(item, cache)
    if brand == "TOYOTA":
        return _toyota_price(item, cache)
    if brand == "TOGG":
        return _togg_price(item, cache)
    if brand == "HYUNDAI":
        return _hyundai_price(item, cache)
    if brand == "FIAT":
        return _fiat_price(item, cache)
    return None


def _display_trim(item):
    t = _clean(item["trim"])
    # Bakanlık PDF'sindeki Hyundai yazım hatasını kullanıcıya taşımıyoruz.
    if _norm(t) == "SYTLE":
        return "STYLE"
    return t


def _source_name(brand, url):
    if "hyundaiplaza.com.tr" in url:
        return "Hyundai Yetkili Satıcı"
    if "tanoto.com.tr" in url:
        return "Fiat Yetkili Satıcı"
    return f"{brand} Türkiye"


def _save(data):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass
    return data


def _load():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def refresh_otv_data(force=False):
    now = datetime.now(TZ)
    old = _load()
    try:
        ministry_url, pdf_bytes = _find_ministry_pdf()
        candidates = _eligible_packages(_parse_ministry_pdf(pdf_bytes))
        cache, vehicles, unresolved, over_limit = {}, [], [], []

        for item in candidates:
            label = f"{item['brand']} {item['model']} — {_display_trim(item)}"
            try:
                info = _resolve_price(item, cache)
            except Exception as e:
                print("OTV official price read failed:", label, repr(e))
                info = None
            if not info:
                unresolved.append(label)
                continue
            price, source_url = info
            if price > LIMIT_2026:
                over_limit.append(label)
                continue
            vehicles.append({
                "brand": item["brand"],
                "model": item["model"],
                "trim": _display_trim(item),
                "price": int(price),
                "locality": round(float(item["locality"]), 2),
                "source_name": _source_name(item["brand"], source_url),
                "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı",
                "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
            })

        unique = {}
        for v in vehicles:
            unique[(v["brand"], v["model"], _norm(v["trim"]))] = v
        vehicles = sorted(unique.values(), key=lambda v: (v["brand"], v["model"], v["price"], v["trim"]))

        print("OTV package candidates:", len(candidates))
        print("OTV unresolved packages:", unresolved)
        print("OTV over-limit packages:", over_limit)
        print("OTV verified packages:", [(v["brand"], v["model"], v["trim"], v["price"], v["locality"]) for v in vehicles])

        if not vehicles:
            raise RuntimeError("Hiçbir paket fiyatı doğrulanamadı")

        return _save({
            "limit": LIMIT_2026,
            "min_locality": MIN_LOCALITY,
            "updated_at": now.strftime("%d.%m.%Y %H:%M"),
            "updated_time": now.strftime("%H:%M"),
            "source_mode": "ministry_package_live",
            "ministry_source": ministry_url,
            "candidate_count": len(candidates),
            "unresolved": unresolved,
            "over_limit": over_limit,
            "vehicles": vehicles,
        })
    except Exception as e:
        if old and old.get("vehicles"):
            old = dict(old)
            old["refresh_error"] = str(e)
            old["refresh_failed_at"] = now.strftime("%d.%m.%Y %H:%M")
            return old
        raise


def get_otv_data():
    data = _load()
    if not data:
        return refresh_otv_data()
    try:
        dt = datetime.strptime(data["updated_at"], "%d.%m.%Y %H:%M").replace(tzinfo=TZ)
        if (datetime.now(TZ) - dt).total_seconds() > 86400:
            return refresh_otv_data()
    except Exception:
        return refresh_otv_data()
    return data


if __name__ == "__main__":
    print(json.dumps(refresh_otv_data(force=True), ensure_ascii=False, indent=2))
