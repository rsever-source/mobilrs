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
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
}

# Araç/paket elle tanımlanmaz; yalnız markaların resmi Türkiye kaynakları tutulur.
BRAND_PRICE_SOURCES = {
    "RENAULT": ["https://www.renault.com.tr/renault-fiyat-listeleri/binek-arac-fiyat-listesi.html"],
    "HYUNDAI": ["https://www.hyundai.com/tr/tr/models.html"],
    "TOYOTA": ["https://www.toyota.com.tr/araba-modelleri"],
    "FIAT": ["https://www.fiat.com.tr/engelsiz-otomobil", "https://www.fiat.com.tr/fiyat-listeleri", "https://www.fiat.com.tr/kampanyalar"],
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


def _get(url, timeout=35):
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


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
        if "2026" in label and "MOTORLU" in label and "YERLI" in label:
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
    # Kullanıcıya sadece paket gösterilir. Aynı model/paket Bakanlıkta birden fazla satırsa tekilleştirilir.
    out = {}
    for r in rows:
        if r["locality"] < MIN_LOCALITY:
            continue
        key = (r["brand_key"], r["model_key"], _norm(r["trim"]))
        old = out.get(key)
        if old is None or r["locality"] > old["locality"]:
            out[key] = dict(r)
    return list(out.values())


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
    # Önce TL/₺ etiketli fiyatlar; sonra paket yakınındaki etiketlenmemiş JSON fiyatları.
    found = []
    patterns = [
        (0, r"₺\s*([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?"),
        (0, r"([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?\s*(?:TL|₺)"),
        (1, r"(?<!\d)([1-9]\d{6})(?!\d)"),
        (1, r"(?<!\d)([1-9]\d{0,2}(?:[.]\d{3}){2})(?!\d)"),
    ]
    seen = set()
    for penalty, pat in patterns:
        for m in re.finditer(pat, text, re.I):
            p = _money(m.group(1))
            if not p or not 1_000_000 <= p <= 10_000_000:
                continue
            key = (m.start(), p)
            if key not in seen:
                seen.add(key)
                found.append((m.start(), p, penalty))
    return found


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


def _trim_aliases(trim):
    n = _norm(trim)
    aliases = {n, n.replace("SYTLE", "STYLE")}
    if n == "ICON":
        aliases.add("ICONIC")
    # Toyota Bakanlık satırlarında paket metni model/motor ile birlikte gelir.
    for prefix in ("TOYOTA COROLLA ", "TOYOTA C HR "):
        if n.startswith(prefix):
            aliases.add(n[len(prefix):])
    return sorted((x for x in aliases if x), key=len, reverse=True)


def _similar_word_present(context, alias):
    nc = _norm(context)
    if alias in nc:
        return True
    if len(alias.split()) == 1:
        return any(len(w) >= 4 and SequenceMatcher(None, alias, w).ratio() >= 0.86 for w in nc.split())
    return False


def _package_price_from_text(text, item, dedicated_model_page=False):
    model = _norm(item["model"])
    aliases = _trim_aliases(item["trim"])
    if not aliases:
        return None

    # Paket adının çevresindeki en yakın gerçek araç fiyatını seçer. Motor/şanzıman kullanılmaz.
    candidates = _price_candidates(text)
    ranked = []
    norm_text = _norm(text)
    for alias in aliases:
        # Normalize edilmiş metinde paket konumları.
        for m in re.finditer(re.escape(alias), norm_text):
            center = m.start()
            # normalize edilmiş ve ham metin konumları birebir olmayabilir; oranla yaklaşık eşle.
            raw_center = int(center / max(1, len(norm_text)) * len(text))
            raw_context = text[max(0, raw_center - 1100):raw_center + 1100]
            nc = _norm(raw_context)
            if not _similar_word_present(nc, alias):
                continue
            if not dedicated_model_page and model and model not in nc:
                continue
            for pos, price, label_penalty in candidates:
                dist = abs(pos - raw_center)
                if dist > 900:
                    continue
                around = text[max(0, pos - 180):pos + 180].lower()
                score = dist + label_penalty * 220
                if any(x in around for x in ("kredi", "finansman", "taksit", "aylık")):
                    score += 600
                if any(x in around for x in ("liste fiyat", "anahtar teslim", "tavsiye edilen", "başlangıç fiyat", "satış fiyat")):
                    score -= 180
                ranked.append((score, price))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0])
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
                p = _package_price_from_text(text, item, True)
                if p:
                    return p, model_url
        return None

    if brand == "TOGG":
        mk = _norm(item["model"])
        preferred = [p for p in pages if ("t10f" in p[0].lower()) == (mk == "T10F")]
        for url, _soup, text in preferred:
            p = _package_price_from_text(text, item, True)
            if p:
                return p, url
        return None

    for url, _soup, text in pages:
        p = _package_price_from_text(text, item, False)
        if p:
            return p, url
    return None


def _estimated_exempt_price(price, brand):
    # Togg elektrikli: dilimi ayrıca doğrulamadan muaf fiyat uydurma.
    if _norm(brand) == "TOGG":
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
        candidates = _eligible_packages(_parse_ministry_pdf(pdf_bytes))
        cache, vehicles, unresolved, over_limit = {}, [], [], []
        for item in candidates:
            info = _resolve_package_price(item, cache)
            label = f"{item['brand']} {item['model']} — {item['trim']}"
            if not info:
                unresolved.append(label)
                continue
            price, source_url = info
            if price > LIMIT_2026:
                over_limit.append(label)
                continue
            vehicles.append({
                "brand": item["brand"], "model": item["model"], "trim": item["trim"],
                "price": int(price), "exempt_price": _estimated_exempt_price(price, item["brand"]),
                "locality": round(float(item["locality"]), 2),
                "source_name": f"{item['brand']} Türkiye", "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı", "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
            })
        unique = {}
        for v in vehicles:
            unique[(v["brand"], v["model"], _norm(v["trim"]), v["price"])] = v
        vehicles = sorted(unique.values(), key=lambda v: (v["brand"], v["model"], v["price"], v["trim"]))
        print("OTV package candidates:", len(candidates))
        print("OTV unresolved packages:", unresolved)
        print("OTV over-limit packages:", over_limit)
        print("OTV verified packages:", [(v["brand"], v["model"], v["trim"], v["price"]) for v in vehicles])
        if not vehicles:
            raise RuntimeError("Bakanlıkta uygun paketler bulundu ancak resmi paket fiyatları doğrulanamadı")
        return _save({
            "limit": LIMIT_2026, "min_locality": MIN_LOCALITY,
            "updated_at": now.strftime("%d.%m.%Y %H:%M"), "updated_time": now.strftime("%H:%M"),
            "source_mode": "ministry_package_live", "ministry_source": ministry_url,
            "candidate_count": len(candidates), "unresolved": unresolved, "over_limit": over_limit,
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
