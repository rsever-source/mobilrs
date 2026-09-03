import io
import json
import os
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

# Model listesi burada tutulmaz. Sadece markaların resmî Türkiye fiyat kaynakları tanımlıdır.
# Aynı markaya yeni bir model eklendiğinde Bakanlık listesinden otomatik keşfedilir.
BRAND_PRICE_SOURCES = {
    "RENAULT": ["https://www.renault.com.tr/renault-fiyat-listeleri/binek-arac-fiyat-listesi.html"],
    "HYUNDAI": ["https://www.hyundai.com/tr/tr/satis/fiyat-listesi.html"],
    "TOYOTA": ["https://turkiye.toyota.com.tr/middle/fiyat-listesi/", "https://www.toyota.com.tr/araba-modelleri"],
    "FIAT": ["https://www.fiat.com.tr/fiyat-listeleri"],
    "TOGG": ["https://togg.com.tr/price-list", "https://www.togg.com.tr/t10f-price-list"],
}


def _norm(value):
    s = str(value or "").replace("\n", " ").strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().replace("İ", "I")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "").replace("\n", " ")).strip()


def _ratio(value):
    m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)", str(value or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def _money(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits) if digits else None


def _get(url, timeout=30):
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


def _find_ministry_pdf():
    # Resmî 2026 dosya adı sabit kaynak olarak denenir. Bakanlık sayfası değişirse
    # sayfadaki 2026 bağlantısı dinamik olarak bulunur.
    try:
        r = _get(MINISTRY_PDF, 35)
        if r.content[:4] == b"%PDF":
            return MINISTRY_PDF, r.content
    except Exception:
        pass

    r = _get(MINISTRY_PAGE, 35)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        text = _norm(a.get_text(" ", strip=True))
        href = a.get("href", "")
        if "2026" in text and "MOTORLU" in text and "YERLI" in text:
            if href.startswith("/"):
                href = "https://www.sanayi.gov.tr" + href
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
                    if not row or len(row) < 10:
                        continue
                    cells = [_clean(c) for c in row]
                    ratio = _ratio(cells[-1])
                    if ratio is None:
                        continue
                    brand = cells[2]
                    model = cells[3]
                    category = cells[4]
                    fuel = cells[6]
                    trim = cells[8]
                    if not brand or not model:
                        continue
                    if not re.search(r"(?:^|\s)M1(?:\s|$|[-–])", category.upper()):
                        continue
                    rows.append({
                        "brand": brand.title() if brand.upper() != "TOGG" else "Togg",
                        "brand_key": _norm(brand),
                        "model": model,
                        "model_key": _norm(model),
                        "trim": trim,
                        "fuel": fuel.title(),
                        "locality": ratio,
                        "category": category,
                    })
    if not rows:
        raise RuntimeError("Bakanlık PDF'inden M1 araç kayıtları okunamadı")
    return rows


def _eligible_models(rows):
    # Paket bazında oranlar korunur. Fiyat sayfasında paket güvenilir eşleşmiyorsa
    # model yalnızca Bakanlıkta görülen tüm paketleri %40+ ise otomatik gösterilebilir.
    grouped = {}
    for r in rows:
        key = (r["brand_key"], r["model_key"])
        grouped.setdefault(key, []).append(r)

    result = []
    for items in grouped.values():
        eligible = [x for x in items if x["locality"] >= MIN_LOCALITY]
        if not eligible:
            continue
        # Aynı modelde %40 altı paket de varsa başlangıç fiyatının hangi pakete ait
        # olduğu kesin bilinemez; yanlış uygunluk göstermemek için model gizlenir.
        if any(x["locality"] < MIN_LOCALITY for x in items):
            continue
        base = dict(eligible[0])
        base["locality_min"] = round(min(x["locality"] for x in eligible), 2)
        base["locality_max"] = round(max(x["locality"] for x in eligible), 2)
        trims = sorted({_clean(x["trim"]) for x in eligible if _clean(x["trim"])})
        base["trim"] = " / ".join(trims[:3]) + ("…" if len(trims) > 3 else "")
        fuels = sorted({_clean(x["fuel"]) for x in eligible if _clean(x["fuel"])})
        base["fuel"] = "/".join(fuels)
        result.append(base)
    return result


def _html_text(url):
    r = _get(url, 25)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def _candidate_prices(window):
    vals = []
    for m in re.finditer(r"(?:₺\s*)?([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})(?:\s*(?:TL|₺))?", window, re.I):
        p = _money(m.group(1))
        if p and 700_000 <= p <= 15_000_000:
            vals.append((m.start(), p))
    return vals


def _price_near_model(text, model):
    nt = _norm(text)
    model_key = _norm(model)
    # Normalize edilmiş metinde model konumunu kullanmak fiyat ayraçlarını bozduğu için
    # önce orijinal metinde esnek model regex'i aranır.
    words = [re.escape(w) for w in model_key.split() if w]
    if not words:
        return None
    pat = r"\b" + r"[\s\-–_/]*".join(words) + r"\b"
    matches = list(re.finditer(pat, _norm(text), re.I))
    if not matches:
        # Orijinal metinde doğrudan arama fallback
        m = re.search(re.escape(model), text, re.I)
        if not m:
            return None
        start = m.start()
    else:
        # normalized/original indeksler tam eşleşmeyebilir; model kelimelerinden ilkini kullan
        first = model.split()[0]
        m = re.search(re.escape(first), text, re.I)
        if not m:
            return None
        start = m.start()

    window = text[max(0, start - 100): start + 700]
    candidates = _candidate_prices(window)
    if not candidates:
        return None

    # "liste fiyat" ifadesine yakın tutarı önceliklendir; yoksa modelden sonraki
    # geçerli otomobil fiyatları arasından ilkini seç.
    lw = window.lower()
    list_pos = [m.start() for m in re.finditer(r"liste\s*fiyat", lw)]
    if list_pos:
        return min(candidates, key=lambda x: min(abs(x[0] - lp) for lp in list_pos))[1]
    return candidates[0][1]


def _fetch_brand_pages(brand_key):
    urls = BRAND_PRICE_SOURCES.get(brand_key, [])
    pages = []
    for url in urls:
        try:
            pages.append((url, _html_text(url)))
        except Exception:
            continue
    return pages


def _resolve_price(item, page_cache):
    brand_key = item["brand_key"]
    if brand_key not in page_cache:
        page_cache[brand_key] = _fetch_brand_pages(brand_key)
    best = None
    for url, text in page_cache[brand_key]:
        p = _price_near_model(text, item["model"])
        if p and (best is None or p < best[0]):
            best = (p, url)
    return best


def _estimated_exempt_price(price, fuel):
    # Sadece ekranda yaklaşık gösterim içindir. Elektrikli araçlarda güncel vergi
    # dilimi batarya/motor gücü ve matraha göre değişebildiği için tahmin üretilmez.
    if "elektr" in str(fuel).lower():
        return None
    # İçten yanmalı yerli modeller için önceki sistemde kullanılan yaklaşık %80 ÖTV.
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
        page_cache = {}
        vehicles = []
        unresolved = []

        for item in candidates:
            price_info = _resolve_price(item, page_cache)
            if not price_info:
                unresolved.append(f"{item['brand']} {item['model']}")
                continue
            price, source_url = price_info
            if price > LIMIT_2026:
                continue
            vehicles.append({
                "brand": item["brand"],
                "model": item["model"],
                "trim": item.get("trim", ""),
                "fuel": item.get("fuel", ""),
                "price": int(price),
                "exempt_price": _estimated_exempt_price(price, item.get("fuel", "")),
                "locality": item["locality_min"],
                "locality_range": [item["locality_min"], item["locality_max"]],
                "source_name": f"{item['brand']} Türkiye",
                "source_url": source_url,
                "locality_source_name": "T.C. Sanayi ve Teknoloji Bakanlığı",
                "locality_source_url": ministry_url,
                "checked_at": now.strftime("%H:%M"),
            })

        vehicles.sort(key=lambda v: (v["brand"], v["price"], v["model"]))
        if not vehicles:
            raise RuntimeError("Bakanlıkta uygun modeller bulundu ancak resmî fiyatlar doğrulanamadı")

        return _save({
            "limit": LIMIT_2026,
            "min_locality": MIN_LOCALITY,
            "updated_at": now.strftime("%d.%m.%Y %H:%M"),
            "updated_time": now.strftime("%H:%M"),
            "source_mode": "ministry_live",
            "ministry_source": ministry_url,
            "candidate_count": len(candidates),
            "unresolved": unresolved,
            "vehicles": vehicles,
        })
    except Exception as e:
        # Kaynak geçici olarak kapanırsa doğrulanmış son veriyi kaybetme; ancak
        # hatayı API'de görünür bırak ki sağlık kontrolü bunu yakalayabilsin.
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
