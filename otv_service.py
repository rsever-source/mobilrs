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

TOYOTA_MODEL_IDS = {
    "COROLLA": "65bfd91d-f2a8-4cbb-bdbc-3834b400492a",
    "C HR": "6c193d6b-514c-436f-ab43-654d97e601d8",
}
TOYOTA_MODEL_URLS = {
    "COROLLA": "https://www.toyota.com.tr/araba-modelleri/corolla-sedan",
    "C HR": "https://www.toyota.com.tr/araba-modelleri/c-hr",
}
TOYOTA_GRADE_URL = "https://dxp-webcarconfig.toyota-europe.com/v1/grade-selector/tr/tr?modelId={}"
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

def _toyota_base_package(item):
    n = _norm(item["trim"])
    n = n.replace("TOYOTA", " ")
    model = _norm(item["model"])
    if model == "C HR":
        n = n.replace("C HR", " ")
    else:
        n = n.replace(model, " ")
    n = re.sub(r"\b1\s+[58]\b", " ", n)
    n = re.sub(r"\bHYBRID\b", " ", n)
    n = re.sub(r"\bMDS\b", " ", n)
    n = re.sub(r"\bE\s*CVT\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _toyota_is_hybrid(item):
    return "HYBRID" in _norm(item["trim"])


def _toyota_grade_base(name):
    n = _norm(name)
    n = re.sub(r"\bHYBRID\b", " ", n)
    n = re.sub(r"\bMULTIDRIVE\s+S\b", " ", n)
    n = re.sub(r"\bE\s*CVT\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _toyota_rows(model_key, cache):
    ck = ("TOYOTA_GRADES", model_key)
    if ck in cache:
        return cache[ck]
    model_id = TOYOTA_MODEL_IDS.get(model_key)
    model_url = TOYOTA_MODEL_URLS.get(model_key)
    if not model_id or not model_url:
        cache[ck] = []
        return []

    url = TOYOTA_GRADE_URL.format(model_id)
    headers = dict(HEADERS)
    headers.update({
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Referer": model_url,
    })
    r = requests.post(url, headers=headers, timeout=40)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    data_div = soup.find("div", id=re.compile(r"-data$"))
    if not data_div:
        raise RuntimeError(f"Toyota {model_key} paket verisi bulunamadı")
    data = json.loads(data_div.get_text())
    model = (data.get("gradeSelectorModel") or {}).get("model") or {}

    rows = []
    for gb in model.get("gradeBodyTypes") or []:
        if not isinstance(gb, dict):
            continue
        grade = gb.get("grade") or {}
        grade_name = _clean(grade.get("name") if isinstance(grade, dict) else grade)
        if not grade_name:
            continue
        for engine in gb.get("engines") or []:
            if not isinstance(engine, dict):
                continue
            engine_name = _clean(engine.get("name"))
            category = engine.get("category") or {}
            category_code = _norm(category.get("code") if isinstance(category, dict) else category)
            is_hybrid = "HYBRID" in _norm(engine_name) or category_code == "HEV"
            for trans in engine.get("transmissions") or []:
                if not isinstance(trans, dict):
                    continue
                for wd in trans.get("wheeldrives") or []:
                    if not isinstance(wd, dict):
                        continue
                    price = wd.get("price") or {}
                    if not isinstance(price, dict):
                        continue
                    list_price = price.get("list")
                    try:
                        list_price = int(float(list_price))
                    except Exception:
                        list_price = None
                    if list_price and 1_000_000 <= list_price <= 10_000_000:
                        rows.append({
                            "grade": grade_name,
                            "base": _toyota_grade_base(grade_name),
                            "hybrid": is_hybrid,
                            "price": list_price,
                        })
    cache[ck] = rows
    print("OTV Toyota live grades", model_key, [(r["grade"], r["price"]) for r in rows])
    return rows


def _toyota_price(item, cache):
    model_key = _norm(item["model"])
    package = _toyota_base_package(item)
    want_hybrid = _toyota_is_hybrid(item)
    rows = _toyota_rows(model_key, cache)
    matches = [r["price"] for r in rows if r["base"] == package and r["hybrid"] == want_hybrid]
    if not matches:
        return None
    return min(matches), TOYOTA_MODEL_URLS[model_key]


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
            matches.append(vals[0])
    if matches:
        return min(matches), url

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

    if model == "ULYSSE":
        url = FIAT_ULYSSE_URL
        if url not in cache:
            cache[url] = _page(url)
        _soup, text, _raw = cache[url]
        vals = _prices(text, 1_000_000, 6_000_000)
        if not vals:
            return None
        return vals[0][1], url

    url = FIAT_DEALER_URL
    if url not in cache:
        cache[url] = _page(url)
    soup, text, _raw = cache[url]

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


def _pretty_package(n):
    mapping = {
        "VISION PLUS": "Vision Plus",
        "DREAM": "Dream",
        "DREAM X PACK": "Dream X-Pack",
        "FLAME": "Flame",
        "FLAME X PACK": "Flame X-Pack",
        "PASSION": "Passion",
        "PASSION X PACK": "Passion X-Pack",
        "PASSION X SPORT": "Passion X-Sport",
        "GR SPORT": "GR Sport",
    }
    return mapping.get(n, n.title())


def _display_trim(item):
    t = _clean(item["trim"])
    if _norm(item["brand"]) == "TOYOTA":
        base = _toyota_base_package(item)
        return _pretty_package(base) if base else t
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

        # Aynı marka/model/paket farklı motor satırlarından gelirse kullanıcı yalnız paket
        # istediği için doğrulanmış en düşük normal liste fiyatını tek satırda göster.
        unique = {}
        for v in vehicles:
            key = (v["brand"], v["model"], _norm(v["trim"]))
            old_v = unique.get(key)
            if old_v is None or v["price"] < old_v["price"]:
                unique[key] = v
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
