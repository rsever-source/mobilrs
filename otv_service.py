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

# Araç/model/paket listesi tutulmaz. Yalnızca markaların resmi Türkiye kaynakları tanımlıdır.
BRAND_PRICE_SOURCES = {
    "RENAULT": ["https://www.renault.com.tr/renault-fiyat-listeleri/binek-arac-fiyat-listesi.html"],
    "HYUNDAI": ["https://www.hyundai.com/tr/tr/models.html"],
    "TOYOTA": ["https://www.toyota.com.tr/araba-modelleri"],
    "FIAT": ["https://www.fiat.com.tr/fiyat-listeleri", "https://www.fiat.com.tr/kampanyalar"],
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
                    brand, model, category = c[2], c[3], c[4]
                    if not brand or not model or not re.search(r"(?:^|\s)M1(?:\s|$|[-–])", category.upper()):
                        continue
                    rows.append({
                        "brand": "Togg" if _norm(brand) == "TOGG" else brand.title(),
                        "brand_key": _norm(brand),
                        "model": c[3],
                        "model_key": _norm(c[3]),
                        "category": c[4],
                        "engine": c[5],
                        "fuel": c[6].title(),
                        "transmission": c[7].title(),
                        "trim": c[8],
                        "locality": locality,
                    })
    if not rows:
        raise RuntimeError("Bakanlık PDF'inden M1 araç kayıtları okunamadı")
    return rows


def _eligible_variants(rows):
    # Her paket/motor/sanziman kombinasyonu AYRI tutulur. Model seviyesinde birlestirme yok.
    by_key = {}
    for r in rows:
        if r["locality"] < MIN_LOCALITY:
            continue
        key = (
            r["brand_key"], r["model_key"], _norm(r["engine"]), _norm(r["fuel"]),
            _norm(r["transmission"]), _norm(r["trim"]),
        )
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
    # Bazi markalar paket/fiyat verisini sayfa icindeki JSON/script alaninda tutuyor.
    raw_text = html.unescape(re.sub(r"\s+", " ", r.text))
    return soup, visible_text + " " + raw_text


def _price_candidates(text):
    out = []
    pat = r"(?:₺\s*)?([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:[,.]00)?\s*(?:TL|₺)?"
    for m in re.finditer(pat, text, re.I):
        p = _money(m.group(1))
        if p and 700_000 <= p <= 15_000_000:
            out.append((m.start(), p))
    return out


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
    aliases = {n}
    # Bakanlik PDF'indeki bilinen yazim farklari.
    aliases.add(n.replace("SYTLE", "STYLE"))
    aliases.add(n.replace("ICON ", "ICONIC ") if n.startswith("ICON ") else n)
    if n == "ICON":
        aliases.add("ICONIC")
    return [x for x in aliases if x]


def _token_present(norm_context, value):
    v = _norm(value)
    if not v:
        return False
    if v in norm_context:
        return True
    # Motor hacmi: 1.332 cm3 <-> 1332 gibi farklari tolere et.
    digits = re.sub(r"\D", "", str(value or ""))
    return len(digits) >= 3 and digits in re.sub(r"\D", "", norm_context)


def _trim_present(norm_context, trim):
    for alias in _trim_aliases(trim):
        if alias in norm_context:
            return True
        words = alias.split()
        if len(words) == 1:
            # Style/Sytle gibi tek kelimelik ufak yazim farklari.
            for w in norm_context.split():
                if len(w) >= 4 and SequenceMatcher(None, alias, w).ratio() >= 0.86:
                    return True
    return False


def _variant_price_from_text(text, item, dedicated_model_page=False):
    """Yalnizca ayni paket/versiyonun yakinindaki fiyati kabul eder.
    Paket bulunamazsa modelin baslangic fiyatina dusmez; None dondurur.
    """
    model = _norm(item["model"])
    trim = _norm(item["trim"])
    if not trim:
        return None

    prices = _price_candidates(text)
    ranked = []
    for pos, price in prices:
        context = text[max(0, pos - 850):pos + 850]
        nc = _norm(context)
        if not _trim_present(nc, trim):
            continue
        if not dedicated_model_page and model and model not in nc:
            continue

        score = 0
        # Paket adi zorunlu; motor/sanziman/yakit varsa ayni satiri secmede puan kazandirir.
        if _token_present(nc, item.get("engine")):
            score -= 12
        if _token_present(nc, item.get("transmission")):
            score -= 8
        if _token_present(nc, item.get("fuel")):
            score -= 5
        if re.search(r"(?:liste\s*fiyat|anahtar\s*teslim|tavsiye\s*edilen|teslim\s*fiyat)", context, re.I):
            score -= 20
        if re.search(r"(?:kredi|finansman|aylık|taksit)", context, re.I):
            score += 25

        # Paket adinin fiyata uzakligi en onemli ayirici.
        trim_positions = []
        for alias in _trim_aliases(trim):
            for m in re.finditer(re.escape(alias), nc):
                trim_positions.append(m.start())
        if trim_positions:
            center = len(nc) // 2
            score += min(abs(x - center) for x in trim_positions) / 40
        ranked.append((score, price))

    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0])
    # Esit derecede guclu iki farkli fiyat varsa belirsiz say ve gosterme.
    if len(ranked) > 1 and ranked[0][1] != ranked[1][1] and abs(ranked[0][0] - ranked[1][0]) < 2:
        return None
    return ranked[0][1]


def _resolve_variant_price(item, cache):
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

    # Hyundai/Toyota: once ilgili resmi model sayfasina git, sonra paket fiyatini ara.
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
            _, model_text = cache[key]
            if model_text and "çok yakında" not in model_text.lower():
                price = _variant_price_from_text(model_text, item, dedicated_model_page=True)
                if price:
                    return price, model_url
        return None

    # Togg: T10F ve T10X fiyat sayfalari birbirine karistirilmaz.
    if brand == "TOGG":
        mk = _norm(item["model"])
        if mk == "T10F":
            preferred = [p for p in pages if "t10f" in p[0].lower()]
        elif mk == "T10X":
            preferred = [p for p in pages if "t10f" not in p[0].lower()]
        else:
            preferred = []
        for url, _soup, text in preferred:
            price = _variant_price_from_text(text, item, dedicated_model_page=True)
            if price:
                return price, url
        return None

    # Renault/Fiat: genel resmi fiyat sayfasinda model + paket birlikte eslesmeli.
    for url, _soup, text in pages:
        price = _variant_price_from_text(text, item, dedicated_model_page=False)
        if price:
            return price, url
    return None


def _estimated_exempt_price(price, fuel):
    # Elektrikli araclarda ÖTV dilimi guc/matraha gore degisebilir; yanlis oran uydurma.
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
        candidates = _eligible_variants(ministry_rows)
        page_cache, vehicles, unresolved, over_limit = {}, [], [], []

        for item in candidates:
            price_info = _resolve_variant_price(item, page_cache)
            variant_name = " / ".join(x for x in [item.get("trim"), item.get("engine"), item.get("transmission")] if _clean(x))
            if not price_info:
                unresolved.append(f"{item['brand']} {item['model']} — {variant_name}")
                continue
            price, source_url = price_info
            if price > LIMIT_2026:
                over_limit.append(f"{item['brand']} {item['model']} — {variant_name}")
                continue
            vehicles.append({
                "brand": item["brand"],
                "model": item["model"],
                "trim": item.get("trim", ""),
                "engine": item.get("engine", ""),
                "transmission": item.get("transmission", ""),
                "fuel": item.get("fuel", ""),
                "price": int(price),
                "exempt_price": _estimated_exempt_price(price, item.get("fuel", "")),
                "locality": round(float(item["locality"]), 2),
                "source_name": f"{item['brand']} Türkiye",
                "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı",
                "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
            })

        # Ayni paket birden fazla Bakanlik satirindan ayni fiyata dusmus olabilir; ekranda tekilleştir.
        unique = {}
        for v in vehicles:
            key = (v["brand"], v["model"], _norm(v["trim"]), _norm(v["engine"]), _norm(v["transmission"]), v["price"])
            unique[key] = v
        vehicles = sorted(unique.values(), key=lambda v: (v["brand"], v["model"], v["price"], v["trim"]))

        print("OTV variant candidates:", len(candidates))
        print("OTV unresolved variants:", unresolved)
        print("OTV over-limit variants:", over_limit)
        print("OTV verified variants:", [(v["brand"], v["model"], v["trim"], v["price"], v["locality"]) for v in vehicles])

        if not vehicles:
            raise RuntimeError("Bakanlıkta uygun paketler bulundu ancak resmi paket fiyatları doğrulanamadı")

        return _save({
            "limit": LIMIT_2026,
            "min_locality": MIN_LOCALITY,
            "updated_at": now.strftime("%d.%m.%Y %H:%M"),
            "updated_time": now.strftime("%H:%M"),
            "source_mode": "ministry_variant_live",
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
