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

# Bunlar uygun araç listesi değildir; yalnızca Bakanlıktan gelen model/paketi
# üreticinin resmî sayfasına yönlendirmek için kaynak adresleridir.
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
FIAT_SOURCES = [
    "https://www.fiat.com.tr/engelsiz-otomobil",
    "https://www.fiat.com.tr/fiyat-listeleri",
]
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


def _text(url):
    r = _get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


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


def _first_price_after(text, phrase, max_chars=450):
    """Phrase'den sonra gelen ilk milyonluk fiyatı alır. Paket sayfalarında güvenlidir."""
    low = text.lower()
    p = low.find(phrase.lower())
    if p < 0:
        return None
    window = text[p:p + max_chars]
    m = re.search(r"(?:₺\s*)?([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?\s*(?:₺|TL)?", window, re.I)
    if not m:
        return None
    val = _money(m.group(1))
    return val if val and 1_000_000 <= val <= 15_000_000 else None


def _renault_price(item, cache):
    key = (_norm(item["model"]), _norm(item["trim"]))
    url = RENAULT_PACKAGE_URLS.get(key)
    if not url:
        return None
    if url not in cache:
        cache[url] = _text(url)
    text = cache[url]
    trim = _clean(item["trim"])
    # Önce "versiyon <paket>" bölümünü hedefle; ana model başlangıç fiyatını yanlış alma.
    price = _first_price_after(text, f"versiyon {trim}", 330)
    if not price:
        price = _first_price_after(text, trim, 330)
    return (price, url) if price else None


def _toyota_simple_trim(item):
    n = _norm(item["trim"])
    n = n.replace("TOYOTA", " ").replace(_norm(item["model"]), " ")
    n = re.sub(r"\b1\s*[58]\b", " ", n)
    n = n.replace("HYBRID", " ").replace("E CVT", " ").replace("ECVT", " ").replace("MDS", " ")
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _toyota_price(item, cache):
    url = TOYOTA_PRICE_URL
    if url not in cache:
        cache[url] = _text(url)
    text = cache[url]
    model = _norm(item["model"])
    package = _toyota_simple_trim(item)
    nt = _norm(text)
    # Toyota tablo satırında model/versiyon adı ve Tavsiye Edilen Liste Fiyatı birlikte bulunur.
    targets = []
    if model == "COROLLA":
        targets.append(package)
    else:
        targets.extend([f"C HR {package}", package])
    for target in targets:
        pos = nt.find(target)
        if pos < 0:
            continue
        # normalize edilmiş metinde karakter konumu özgün metinle birebir değil; hedef satırı
        # görünür metinde paket kelimeleri üzerinden tekrar bul.
        words = [w for w in package.split() if len(w) > 2]
        if not words:
            continue
        low = text.lower()
        starts = [low.find(w.lower()) for w in words]
        starts = [x for x in starts if x >= 0]
        if not starts:
            continue
        p = min(starts)
        window = text[max(0, p-180):p+650]
        # Kampanyalı/ÖTV muaf fiyat yerine tablo içindeki en yüksek normal liste fiyatını seç.
        vals = []
        for m in re.finditer(r"([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?", window):
            v = _money(m.group(1))
            if v and 1_000_000 <= v <= 5_000_000:
                vals.append(v)
        if vals:
            return max(vals), url
    return None


def _togg_alias(item):
    n = _norm(item["trim"])
    model = _norm(item["model"])
    if n.startswith(model + " "):
        n = n[len(model):].strip()
    aliases = {
        "V1 SR": "V1 RWD Standart Menzil",
        "V1 LR": "V1 RWD Uzun Menzil",
        "V2 LR": "V2 RWD Uzun Menzil",
        "V2 LR AWD": "V2 4More",
    }
    return aliases.get(n)


def _togg_price(item, cache):
    model = _norm(item["model"])
    url = TOGG_URLS.get(model)
    alias = _togg_alias(item)
    if not url or not alias:
        return None
    if url not in cache:
        cache[url] = _text(url)
    text = cache[url]
    # Togg sayfasında versiyonlar önce, fiyatlar aynı sırada ayrı blokta. Bu yüzden
    # tüm versiyon/fiyat sıralarını resmi tablodan birlikte çıkarıyoruz.
    if model == "T10X":
        versions = ["V1 RWD Standart Menzil", "V1 RWD Uzun Menzil", "V2 RWD Uzun Menzil", "V2 4More Obsidiyen"]
    else:
        versions = ["V1 RWD Standart Menzil", "V1 RWD Uzun Menzil", "V2 RWD Uzun Menzil", "V2 4More"]
    prices_section = text.lower().find("teslim fiyat")
    if prices_section < 0:
        return None
    vals = []
    for m in re.finditer(r"([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})\s*₺", text[prices_section:prices_section+600]):
        v = _money(m.group(1))
        if v and v >= 1_000_000:
            vals.append(v)
    if len(vals) < len(versions):
        return None
    idx = None
    for i, vname in enumerate(versions):
        if alias == vname or (alias == "V2 4More" and vname.startswith("V2 4More")):
            idx = i
            break
    return (vals[idx], url) if idx is not None else None


def _hyundai_price(item, cache):
    # Hyundai'nin halka açık fiyat sayfası şu anda paketlerin isimlerini gösteriyor fakat
    # statik HTML'de Jump/Style/Elite için ayrı liste fiyatları güvenilir şekilde sunmuyor.
    # Yanlış kampanya tutarı eşleştirmek yerine beklet.
    return None


def _fiat_price(item, cache):
    # Fiat'ın resmi sayfaları Render IP'lerine 403 döndürüyor. Resmi fiyat çekilemediği
    # sürece fiyat uydurulmaz; Bakanlık paketi bekleyen olarak görünür.
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
            key = (v["brand"], v["model"], _norm(v["trim"]))
            unique[key] = v
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
