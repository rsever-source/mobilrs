import io
import json
import re
import unicodedata
from datetime import datetime
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

BRAND_PRICE_SOURCES = {
    "RENAULT": ["https://www.renault.com.tr/renault-fiyat-listeleri/binek-arac-fiyat-listesi.html"],
    "HYUNDAI": ["https://www.hyundai.com/tr/tr/satis/fiyat-listesi.html"],
    "TOYOTA": ["https://turkiye.toyota.com.tr/middle/fiyat-listesi/", "https://www.toyota.com.tr/araba-modelleri"],
    "FIAT": ["https://www.fiat.com.tr/fiyat-listeleri"],
    "TOGG": ["https://togg.com.tr/price-list", "https://www.togg.com.tr/t10f-price-list"],
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


def _get(url, timeout=30):
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


def _find_ministry_pdf():
    try:
        r = _get(MINISTRY_PDF, 35)
        if r.content[:4] == b"%PDF":
            return MINISTRY_PDF, r.content
    except Exception:
        pass
    r = _get(MINISTRY_PAGE, 35)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        label = _norm(a.get_text(" ", strip=True))
        if "2026" not in label or "MOTORLU" not in label or "YERLI" not in label:
            continue
        href = a["href"]
        if href.startswith("/"):
            href = "https://www.sanayi.gov.tr" + href
        rr = _get(href, 35)
        if rr.content[:4] == b"%PDF":
            return href, rr.content
    raise RuntimeError("Bakanlığın 2026 yerli katkı PDF'i indirilemedi")


def _parse_ministry_pdf(pdf_bytes):
    result = []
    debug_count = 0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table or []:
                    if not row or len(row) < 10:
                        continue
                    c = [_clean(x) for x in row]
                    if debug_count < 12 and any(x.upper() in {"M1", "M1-AF", "M1-AC"} or "M1" in x.upper() for x in c):
                        print("OTV RAW ROW", debug_count, list(enumerate(c)))
                        debug_count += 1
                    locality = _ratio(c[-2])
                    if locality is None:
                        continue
                    brand, model, category, fuel, trim = c[2], c[3], c[4], c[6], c[8]
                    if not brand or not model or not re.search(r"(?:^|\s)M1(?:\s|$|[-–])", category.upper()):
                        continue
                    result.append({
                        "brand": "Togg" if _norm(brand) == "TOGG" else brand.title(),
                        "brand_key": _norm(brand),
                        "model": model,
                        "model_key": _norm(model),
                        "category": category,
                        "fuel": fuel.title(),
                        "trim": trim,
                        "locality": locality,
                    })
    if not result:
        raise RuntimeError("Bakanlık PDF'inden M1 araç kayıtları okunamadı")
    return result


def _eligible_models(rows):
    grouped = {}
    for r in rows:
        if r["locality"] < MIN_LOCALITY:
            continue
        grouped.setdefault((r["brand_key"], r["model_key"]), []).append(r)
    out = []
    for items in grouped.values():
        b = dict(items[0])
        b["locality_min"] = round(min(x["locality"] for x in items), 2)
        b["locality_max"] = round(max(x["locality"] for x in items), 2)
        trims = sorted({_clean(x["trim"]) for x in items if _clean(x["trim"])})
        fuels = sorted({_clean(x["fuel"]) for x in items if _clean(x["fuel"])})
        b["trim"] = " / ".join(trims[:3]) + ("…" if len(trims) > 3 else "")
        b["fuel"] = "/".join(fuels)
        out.append(b)
    return out


def _official_source_key(brand_key):
    bk = _norm(brand_key)
    for key in BRAND_PRICE_SOURCES:
        if key in bk or bk in key:
            return key
    return None


def _page_text(url):
    r = _get(url, 25)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def _price_candidates(text):
    out = []
    pat = r"(?:₺\s*)?([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:\s*(?:TL|₺))?"
    for m in re.finditer(pat, text, re.I):
        p = _money(m.group(1))
        if p and 700_000 <= p <= 15_000_000:
            out.append((m.start(), p))
    return out


def _model_position(text, model):
    m = re.search(re.escape(_clean(model)), text, re.I)
    if m:
        return m.start()
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", _norm(model)) if t and t not in {"YENI", "NEW"}]
    for token in tokens:
        m = re.search(r"\b" + re.escape(token) + r"\b", text, re.I)
        if m:
            return m.start()
    return None


def _price_near_model(text, model):
    pos = _model_position(text, model)
    if pos is None:
        return None
    window = text[max(0, pos - 80):pos + 900]
    candidates = _price_candidates(window)
    if not candidates:
        return None
    lower = window.lower()
    anchors = [m.start() for m in re.finditer(r"(?:tavsiye edilen\s+)?liste fiyat", lower)]
    if anchors:
        return min(candidates, key=lambda x: min(abs(x[0] - a) for a in anchors))[1]
    return candidates[0][1]


def _fetch_pages(brand_key):
    key = _official_source_key(brand_key)
    if not key:
        return []
    pages = []
    for url in BRAND_PRICE_SOURCES[key]:
        try:
            pages.append((url, _page_text(url)))
        except Exception as e:
            print("OTV price source failed:", key, url, repr(e))
    return pages


def _resolve_price(item, cache):
    key = _official_source_key(item["brand_key"])
    if not key:
        return None
    if key not in cache:
        cache[key] = _fetch_pages(item["brand_key"])
    found = []
    for url, text in cache[key]:
        p = _price_near_model(text, item["model"])
        if p:
            found.append((p, url))
    return min(found, key=lambda x: x[0]) if found else None


def _estimated_exempt_price(price, fuel):
    if "elektr" in str(fuel).lower():
        return None
    return round(price / 1.80)


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
        ministry_rows = _parse_ministry_pdf(pdf_bytes)
        candidates = _eligible_models(ministry_rows)
        page_cache, vehicles, unresolved = {}, [], []
        for item in candidates:
            price_info = _resolve_price(item, page_cache)
            if not price_info:
                unresolved.append(f"{item['brand']} {item['model']}")
                continue
            price, source_url = price_info
            if price > LIMIT_2026:
                continue
            vehicles.append({
                "brand": item["brand"], "model": item["model"], "trim": item.get("trim", ""),
                "fuel": item.get("fuel", ""), "price": int(price),
                "exempt_price": _estimated_exempt_price(price, item.get("fuel", "")),
                "locality": item["locality_min"], "locality_range": [item["locality_min"], item["locality_max"]],
                "source_name": f"{item['brand']} Türkiye", "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı", "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
            })
        vehicles.sort(key=lambda v: (v["brand"], v["price"], v["model"]))
        print("OTV unresolved:", unresolved)
        print("OTV verified vehicles:", [(v["brand"], v["model"], v["price"]) for v in vehicles])
        if not vehicles:
            raise RuntimeError("Bakanlıkta uygun modeller bulundu ancak resmî fiyatlar doğrulanamadı")
        return _save({
            "limit": LIMIT_2026, "min_locality": MIN_LOCALITY,
            "updated_at": now.strftime("%d.%m.%Y %H:%M"), "updated_time": now.strftime("%H:%M"),
            "source_mode": "ministry_live", "ministry_source": ministry_url,
            "candidate_count": len(candidates), "unresolved": unresolved, "vehicles": vehicles,
        })
    except Exception as e:
        if old and old.get("vehicles"):
            old = dict(old); old["refresh_error"] = str(e); old["refresh_failed_at"] = now.strftime("%d.%m.%Y %H:%M")
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
