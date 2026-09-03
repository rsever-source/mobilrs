import html
import io
import json
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
}

BRAND_PRICE_SOURCES = {
    "RENAULT": ["https://www.renault.com.tr/renault-fiyat-listeleri/binek-arac-fiyat-listesi.html"],
    "HYUNDAI": ["https://www.hyundai.com/tr/tr/models.html"],
    "TOYOTA": ["https://www.toyota.com.tr/araba-modelleri"],
    "FIAT": [
        "https://www.fiat.com.tr/engelsiz-otomobil",
        "https://www.fiat.com.tr/fiyat-listeleri",
        "https://www.fiat.com.tr/kampanyalar",
    ],
    "TOGG": ["https://togg.com.tr/price-list", "https://www.togg.com.tr/t10f-price-list"],
}


def _clean(v):
    return re.sub(r"\s+", " ", str(v or "").replace("\n", " ")).strip()


def _norm(v):
    s = unicodedata.normalize("NFKD", _clean(v))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).upper().replace("İ", "I")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", s)).strip()


def _compact(v):
    return re.sub(r"[^a-z0-9]", "", _norm(v).lower())


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
    soup = BeautifulSoup(_get(MINISTRY_PAGE, 35).text, "html.parser")
    for a in soup.find_all("a", href=True):
        label = _norm(a.get_text(" ", strip=True))
        if "2026" not in label or "MOTORLU" not in label or "YERLI" not in label:
            continue
        href = urljoin(MINISTRY_PAGE, a["href"])
        rr = _get(href, 35)
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
    by_key = {}
    for r in rows:
        if r["locality"] < MIN_LOCALITY:
            continue
        key = (r["brand_key"], r["model_key"], _norm(r["trim"]))
        old = by_key.get(key)
        if old is None or r["locality"] > old["locality"]:
            by_key[key] = dict(r)
    return list(by_key.values())


def _official_source_key(brand_key):
    bk = _norm(brand_key)
    for key in BRAND_PRICE_SOURCES:
        if key in bk or bk in key:
            return key
    return None


def _page(url):
    r = _get(url, 30)
    soup = BeautifulSoup(r.text, "html.parser")
    visible = BeautifulSoup(r.text, "html.parser")
    for tag in visible(["script", "style", "noscript"]):
        tag.decompose()
    visible_text = re.sub(r"\s+", " ", visible.get_text(" ", strip=True))
    raw_text = html.unescape(re.sub(r"\s+", " ", r.text))
    return soup, visible_text + " " + raw_text


def _price_candidates(text):
    """Yalnızca fiyat gibi biçimlenmiş milyonluk tutarları kabul eder.
    TL/₺ zorunlu değildir; ancak yakınında fiyat/price/tutar ifadesi ya da para simgesi bulunmalıdır.
    Böylece eski doğru okuma davranışı korunur, 800480 gibi ID/kW sayıları fiyat sanılmaz.
    """
    out, seen = [], set()
    pat = r"(?<!\d)([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?(?!\d)"
    for m in re.finditer(pat, text, re.I):
        p = _money(m.group(1))
        if not p or not (1_000_000 <= p <= 15_000_000):
            continue
        local = text[max(0, m.start()-220):m.end()+220]
        if not re.search(r"(?:₺|\bTL\b|fiyat|price|tutar|anahtar\s+teslim)", local, re.I):
            continue
        key = (m.start(), p)
        if key in seen:
            continue
        seen.add(key)
        out.append((m.start(), p))
    return sorted(out)


def _find_model_page(soup, base_url, item, brand):
    target = _compact(item["model"])
    choices = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        label = _compact(a.get_text(" ", strip=True))
        path = _compact(href)
        score = 100
        if target and target in label:
            score -= 30
        if target and target in path:
            score -= 35
        if brand == "HYUNDAI" and "/tr/tr/modeller/" not in href:
            continue
        if brand == "TOYOTA" and "toyota.com.tr/araba-modelleri/" not in href:
            continue
        if brand == "TOYOTA" and _norm(item["model"]) == "COROLLA":
            if "cross" in href.lower() or "hatchback" in href.lower():
                score += 80
            if "corolla-sedan" in href.lower():
                score -= 50
        if brand == "TOYOTA" and _norm(item["model"]) == "C-HR" and "c-hr" in href.lower():
            score -= 50
        if score < 100:
            choices.append((score, len(href), href))
    return min(choices)[2] if choices else None


def _package_aliases(item):
    raw = _norm(item.get("trim"))
    model = _norm(item.get("model"))
    aliases = {raw, raw.replace("SYTLE", "STYLE")}
    if raw == "ICON":
        aliases.add("ICONIC")
    if raw.startswith("ICON "):
        aliases.add(raw.replace("ICON ", "ICONIC ", 1))

    if _norm(item.get("brand")) == "TOYOTA":
        simple = raw
        for token in ["TOYOTA", model, "HYBRID", "E CVT", "ECVT", "MDS"]:
            if token:
                simple = simple.replace(token, " ")
        simple = re.sub(r"\b\d+(?:\s+\d+)?\b", " ", simple)
        simple = re.sub(r"\s+", " ", simple).strip()
        if simple:
            aliases.add(simple)

    if _norm(item.get("brand")) == "TOGG" and model and raw.startswith(model + " "):
        aliases.add(raw[len(model):].strip())

    return sorted({a.strip() for a in aliases if a and a.strip()}, key=len, reverse=True)


def _package_present(norm_context, item):
    for alias in _package_aliases(item):
        if alias in norm_context:
            return True
        if len(alias.split()) == 1:
            for w in norm_context.split():
                if len(w) >= 4 and SequenceMatcher(None, alias, w).ratio() >= 0.88:
                    return True
    return False


def _package_price_from_text(text, item, dedicated_model_page=False):
    model = _norm(item["model"])
    ranked = []
    for pos, price in _price_candidates(text):
        context = text[max(0, pos - 1400):pos + 1400]
        nc = _norm(context)
        if not _package_present(nc, item):
            continue
        if not dedicated_model_page and model and model not in nc:
            continue

        score = 0
        if re.search(r"(?:liste\s*fiyat|anahtar\s*teslim|tavsiye\s*edilen|teslim\s*fiyat|başlangıç\s*fiyat|başlayan\s+fiyat)", context, re.I):
            score -= 20
        if re.search(r"(?:kredi|finansman|aylık|taksit)", context, re.I):
            score += 30

        center = len(nc) // 2
        distances = []
        for alias in _package_aliases(item):
            distances.extend(abs(m.start() - center) for m in re.finditer(re.escape(alias), nc))
        if distances:
            score += min(distances) / 45
        ranked.append((score, price))

    if not ranked:
        return None
    ranked.sort(key=lambda x: (x[0], x[1]))
    if len(ranked) > 1 and ranked[0][1] != ranked[1][1] and abs(ranked[0][0] - ranked[1][0]) < 1.5:
        return None
    return ranked[0][1]


def _resolve_package_price(item, cache):
    brand = _official_source_key(item["brand_key"])
    if not brand:
        return None

    if brand not in cache:
        cache[brand] = []
        for url in BRAND_PRICE_SOURCES[brand]:
            try:
                cache[brand].append((url, *_page(url)))
            except Exception as e:
                print("OTV price source failed:", brand, url, repr(e))
    pages = list(cache[brand])

    if brand in {"HYUNDAI", "TOYOTA"} and pages:
        model_url = _find_model_page(pages[0][1], pages[0][0], item, brand)
        if model_url:
            key = (brand + "_MODEL", model_url)
            if key not in cache:
                try:
                    cache[key] = _page(model_url)
                except Exception as e:
                    print("OTV model page failed:", model_url, repr(e))
                    cache[key] = (None, "")
            _, text = cache[key]
            if text and "çok yakında" not in text.lower():
                p = _package_price_from_text(text, item, dedicated_model_page=True)
                if p:
                    return p, model_url
        return None

    if brand == "TOGG":
        mk = _norm(item["model"])
        if mk == "T10F":
            preferred = [p for p in pages if "t10f" in p[0].lower()]
        elif mk == "T10X":
            preferred = [p for p in pages if "t10f" not in p[0].lower()]
        else:
            preferred = []
        for url, _soup, text in preferred:
            p = _package_price_from_text(text, item, dedicated_model_page=True)
            if p:
                return p, url
        return None

    for url, _soup, text in pages:
        p = _package_price_from_text(text, item, dedicated_model_page=False)
        if p:
            return p, url
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
        page_cache, vehicles, unresolved, over_limit = {}, [], [], []

        for item in candidates:
            info = _resolve_package_price(item, page_cache)
            package_name = _clean(item.get("trim"))
            label = f"{item['brand']} {item['model']} — {package_name}"
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
                "trim": package_name,
                "price": int(price),
                "exempt_price": None,
                "locality": round(float(item["locality"]), 2),
                "source_name": f"{item['brand']} Türkiye",
                "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı",
                "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
                "engine": "",
                "transmission": "",
                "fuel": "",
            })

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
