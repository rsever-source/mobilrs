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

# Üreticiye özel fiyat okuyucuları. Araç uygunluğu burada tutulmaz; uygun adaylar
# her zaman Bakanlığın %40+ yerli katkı listesinden gelir.
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
HYUNDAI_PRICE_URL = "https://www.hyundai.com/tr/tr/satis/fiyat-listesi.html"
FIAT_OTV_URL = "https://www.fiat.com.tr/engelsiz-otomobil"
FIAT_PRICE_URL = "https://www.fiat.com.tr/fiyat-listeleri"
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


def _text(url):
    return _page(url)[1]


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
    for m in re.finditer(r"(?:₺\s*)?([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?\s*(?:₺|TL)?", text, re.I):
        v = _money(m.group(1))
        if v and minimum <= v <= maximum:
            vals.append((m.start(), v))
    return vals


def _first_price_after(text, phrase, max_chars=550):
    low = text.lower()
    p = low.find(phrase.lower())
    if p < 0:
        return None
    vals = _prices(text[p:p + max_chars])
    return vals[0][1] if vals else None


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
            price = _first_price_after(source, phrase, 700)
            if price:
                return price, url
    return None


def _toyota_simple_trim(item):
    n = _norm(item["trim"])
    n = n.replace("TOYOTA", " ").replace(_norm(item["model"]), " ")
    n = re.sub(r"\b1\s*[58]\b", " ", n)
    n = n.replace("HYBRID", " ").replace("E CVT", " ").replace("ECVT", " ").replace("MDS", " ")
    return re.sub(r"\s+", " ", n).strip()


def _toyota_price(item, cache):
    url = TOYOTA_PRICE_URL
    if url not in cache:
        cache[url] = _page(url)
    _soup, text, raw = cache[url]
    package = _toyota_simple_trim(item)
    if not package:
        return None
    # Toyota resmi fiyat tablosunda versiyon satırından sonra önce tavsiye edilen liste,
    # ardından kampanyalı fiyat gelir. İlk milyonluk tutarı alıyoruz.
    for source in (text, raw):
        ns = _norm(source)
        target = _norm(package)
        pos = ns.find(target)
        if pos < 0:
            continue
        # Normalize konumu birebir kullanmak yerine gerçek metinde paketin en ayırt edici
        # iki kelimesini bulup kısa pencere açıyoruz.
        words = [w for w in package.split() if len(w) >= 4]
        low = source.lower()
        starts = [low.find(w.lower()) for w in words]
        starts = [x for x in starts if x >= 0]
        if not starts:
            continue
        p = min(starts)
        window = source[max(0, p - 120):p + 550]
        vals = _prices(window, 1_000_000, 6_000_000)
        if vals:
            return vals[0][1], url
    return None


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
    # Resmi Togg tablosunda versiyonlar ve teslim fiyatları aynı sıradadır.
    vals = [v for _, v in _prices(source[start:start + 1200], 1_000_000, 6_000_000)]
    if model == "T10X":
        versions = ["V1 RWD STANDART MENZIL", "V1 RWD UZUN MENZIL", "V2 RWD UZUN MENZIL", "V2 4MORE"]
    else:
        versions = ["V1 RWD STANDART MENZIL", "V1 RWD UZUN MENZIL", "V2 RWD UZUN MENZIL", "V2 4MORE"]
    if len(vals) < len(versions) or alias not in versions:
        return None
    return vals[versions.index(alias)], url


def _hyundai_model_url(item):
    model = _norm(item["model"])
    slug = {"I20": "i20", "BAYON": "bayon"}.get(model)
    return f"https://www.hyundai.com/tr/tr/modeller/{slug}/konfigurator.html" if slug else None


def _hyundai_price(item, cache):
    url = _hyundai_model_url(item)
    if not url:
        return None
    if url not in cache:
        cache[url] = _page(url)
    _soup, text, raw = cache[url]
    trim = _norm(item["trim"]).replace("SYTLE", "STYLE")

    # Hyundai konfigüratörü paket/fiyat verisini çoğunlukla script/JSON içinde tutuyor.
    # Paket adının çevresindeki price/listPrice/msrp alanlarını önceliklendiriyoruz.
    for source in (raw, text):
        ns = _norm(source)
        for m in re.finditer(re.escape(trim), ns):
            # Normalizasyon uzunluğu birebir olmadığı için aynı paketi gerçek metinde de ara.
            pass
        low = source.lower()
        aliases = [trim.lower(), trim.lower().replace("style", "sytle")]
        for alias in aliases:
            for hit in re.finditer(re.escape(alias), low, re.I):
                window = source[max(0, hit.start() - 1000):hit.start() + 1800]
                ranked = []
                for pos, val in _prices(window, 1_000_000, 5_000_000):
                    around = window[max(0, pos - 100):pos + 100].lower()
                    score = abs(pos - 1000)
                    if any(k in around for k in ["listprice", "list_price", "price", "fiyat", "msrp", "amount"]):
                        score -= 700
                    if any(k in around for k in ["kredi", "faiz", "indirim", "opsiyon", "renk"]):
                        score += 900
                    ranked.append((score, val))
                if ranked:
                    ranked.sort(key=lambda x: x[0])
                    return ranked[0][1], url

    # Paket bazlı veri bulunamazsa model başlangıç fiyatını yalnızca JUMP için kullan.
    # Jump taban donanımdır; Style/Elite'e aynı fiyatı yapıştırmayız.
    if trim == "JUMP":
        model_url = url.replace("/konfigurator.html", ".html")
        try:
            if model_url not in cache:
                cache[model_url] = _page(model_url)
            _s, t, r = cache[model_url]
            for source in (t, r):
                p = _first_price_after(source, "Başlangıç fiyatı", 220)
                if p:
                    return p, model_url
        except Exception:
            pass
    return None


def _fiat_model_url(item):
    model = _norm(item["model"])
    if model == "EGEA SEDAN":
        return "https://www.fiat.com.tr/modeller/egea/sedan"
    if model == "EGEA CROSS":
        return "https://www.fiat.com.tr/modeller/egea/cross"
    if model == "ULYSSE":
        return "https://www.fiat.com.tr/modeller/ulysse"
    return None


def _fiat_price(item, cache):
    # Önce Fiat'ın normal fiyat sayfasını deneriz. Render 403 verirse model sayfasına geçeriz.
    sources = [FIAT_PRICE_URL, _fiat_model_url(item)]
    trim = _norm(item["trim"])
    for url in [u for u in sources if u]:
        try:
            if url not in cache:
                cache[url] = _page(url)
            _soup, text, raw = cache[url]
        except Exception as e:
            print("OTV Fiat source failed:", url, repr(e))
            continue
        # Bakanlık Fiat'ta "STANDART DONANIM" diyebiliyor. Böyle durumda modelin resmi
        # başlangıç fiyatını kullanmak güvenlidir; belirli bir üst pakete atamayız.
        if trim == "STANDART DONANIM":
            for source in (text, raw):
                p = _first_price_after(source, "Başlangıç", 350)
                if p:
                    return p, url
        else:
            for source in (text, raw):
                p = _first_price_after(source, _clean(item["trim"]), 500)
                if p:
                    return p, url
    return None


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
            label = f"{item['brand']} {item['model']} — {_clean(item['trim'])}"
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
                "trim": _clean(item["trim"]),
                "price": int(price),
                "locality": round(float(item["locality"]), 2),
                "source_name": f"{item['brand']} Türkiye",
                "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı",
                "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
                "exempt_price": None,
                "engine": "",
                "transmission": "",
                "fuel": "",
            })

        unique = {}
        for v in vehicles:
            unique[(v["brand"], v["model"], _norm(v["trim"]))] = v
        vehicles = sorted(unique.values(), key=lambda v: (v["brand"], v["model"], v["price"], v["trim"]))

        print("OTV package candidates:", len(candidates))
        print("OTV unresolved packages:", unresolved)
        print("OTV over-limit packages:", over_limit)
        print("OTV verified packages:", [(v["brand"], v["model"], v["trim"], v["price"], v["locality"]) for v in vehicles])

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
        if old:
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
