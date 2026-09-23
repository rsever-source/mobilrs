import hashlib
import io
import re
import unicodedata
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from google.cloud import storage
from PIL import Image

from cloud_storage import load_json as gcs_load_json, save_json as gcs_save_json

POOL_FILE = "vehicle_image_pool.json"
POOL_PREFIX = "vehicle-images/"
POOL_VERSION = 4
HEADERS = {
    "User-Agent": "EngelliMeVehicleImagePool/3.0 (https://engelli.me)",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

# Official manufacturer/model pages. The worker finds the model-specific exterior
# image on the official page, downloads it once, then serves only our GCS copy.
OFFICIAL_SOURCES = {
    "RENAULT|BOREAL": "https://www.renault.com.tr/hybrid-araclar/boreal.html",
    "RENAULT|DUSTER": "https://www.renault.com.tr/hybrid-araclar/yeni-renault-duster.html",
    "RENAULT|CLIO": "https://www.renault.com.tr/hybrid-araclar/yeni-clio.html",
    "RENAULT|MEGANE": "https://www.renault.com.tr/binek-araclar/megane-sedan.html",
    "RENAULT|MEGANE SEDAN": "https://www.renault.com.tr/binek-araclar/megane-sedan.html",
    "TOYOTA|C HR": "https://www.toyota.com.tr/araba-modelleri/c-hr",
    "TOYOTA|COROLLA": "https://www.toyota.com.tr/araba-modelleri/corolla-sedan",
    "HYUNDAI|I20": "https://www.hyundai.com/tr/tr/modeller/i20.html",
    "HYUNDAI|BAYON": "https://www.hyundai.com/tr/tr/modeller/bayon.html",
    "TOGG|T10X": "https://www.togg.eu/tr/t10x",
    "TOGG|T10F": "https://www.togg.eu/tr/t10f",
    "FIAT|EGEA SEDAN": "https://www.fiat.com.tr/modeller/egea/sedan",
    "FIAT|EGEA CROSS": "https://www.fiat.com.tr/modeller/egea/cross",
    "FIAT|ULYSSE": "https://www.fiat.com.tr/professional/modeller/ulysse",
}


def _norm(value):
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", s)).strip()


def _key(brand, model):
    return f"{_norm(brand)}|{_norm(model)}"


def _load_pool():
    pool = gcs_load_json(POOL_FILE)
    return pool if isinstance(pool, dict) else {}


def _save_pool(pool):
    return gcs_save_json(POOL_FILE, pool)


def _bucket():
    from os import environ
    name = environ.get("GCS_BUCKET", "").strip()
    return storage.Client().bucket(name) if name else None


def _model_terms(brand, model):
    model_n = _norm(model)
    terms = [model_n]
    if model_n == "C HR":
        terms.append("C HR HYBRID")
    if model_n == "I20":
        terms.append("I20")
    if model_n == "MEGANE SEDAN":
        terms.append("MEGANE SEDAN")
    return [x for x in dict.fromkeys(terms) if x]


def _candidate_urls(tag, base_url):
    values = []
    for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-fsrc"):
        value = tag.get(attr)
        if value:
            values.append(urljoin(base_url, value))
    srcset = tag.get("srcset") or tag.get("data-srcset")
    if srcset:
        for part in srcset.split(","):
            value = part.strip().split(" ")[0]
            if value:
                values.append(urljoin(base_url, value))
    return values


def _page_image_candidates(response, brand, model):
    soup = BeautifulSoup(response.text, "html.parser")
    terms = _model_terms(brand, model)
    candidates = []

    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        content = meta.get("content")
        if content and prop in {"og:image", "twitter:image"}:
            candidates.append((urljoin(response.url, content), "", 100))

    for img in soup.find_all("img"):
        alt = _norm(img.get("alt") or img.get("title") or "")
        urls = _candidate_urls(img, response.url)
        if not urls:
            continue
        score = 10
        if any(term in alt for term in terms):
            score += 90
        if any(x in alt for x in ("LOGO", "ICON", "JANT", "IC TASARIM", "INTERIOR")):
            score -= 70
        for url in urls:
            low = url.lower()
            if "mobile" in low:
                score -= 15
            if any(x in low for x in ("hero", "overview", "product", "exterior", "background")):
                score += 12
            candidates.append((url, alt, score))

    best = {}
    for url, alt, score in candidates:
        old = best.get(url)
        if old is None or score > old[2]:
            best[url] = (url, alt, score)
    return sorted(best.values(), key=lambda x: x[2], reverse=True)


def _normalize_image(data, content_type, resolved_url):
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
        width, height = image.size
        if width < 600 or height < 400:
            return None

        if width > 1600:
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            width, height = image.size

        out = io.BytesIO()
        image.save(out, format="JPEG", quality=92, optimize=True, progressive=True)
        return out.getvalue(), "image/jpeg", resolved_url, width, height
    except Exception:
        return None


def _download_image(source_url, brand, model):
    r = requests.get(source_url, headers=HEADERS, timeout=30, allow_redirects=True)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()

    if ctype.startswith("image/"):
        return _normalize_image(r.content, ctype, r.url)

    candidates = _page_image_candidates(r, brand, model)
    attempts = []
    model_token = _norm(model).lower()

    for url, alt, score in candidates[:30]:
        try:
            rr = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            rr.raise_for_status()
            ct = (rr.headers.get("content-type") or "").lower()
            if not ct.startswith("image/") or len(rr.content) < 10000:
                continue
            normalized = _normalize_image(rr.content, ct, rr.url)
            if not normalized:
                continue
            data, out_type, resolved, width, height = normalized
            aspect = width / max(height, 1)
            shape_bonus = 25 if 1.15 <= aspect <= 2.2 else 0
            model_bonus = 20 if model_token in (alt + " " + url).lower() else 0
            attempts.append((score + shape_bonus + model_bonus, width * height, normalized))
        except Exception:
            continue

    if not attempts:
        return None
    attempts.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return attempts[0][2]


def _store_image(key, brand, model, source_url):
    downloaded = _download_image(source_url, brand, model)
    if not downloaded:
        return None
    data, content_type, resolved_url, width, height = downloaded
    bucket = _bucket()
    if bucket is None:
        return None

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    object_name = f"{POOL_PREFIX}{digest}.jpg"
    bucket.blob(object_name).upload_from_string(data, content_type=content_type)

    return {
        "version": POOL_VERSION,
        "object_name": object_name,
        "content_type": content_type,
        "source_url": source_url,
        "resolved_url": resolved_url,
        "source": "official manufacturer",
        "brand": brand,
        "model": model,
        "width": width,
        "height": height,
    }


def ensure_vehicle_image(brand, model):
    key = _key(brand, model)
    pool = _load_pool()
    existing = pool.get(key) or {}
    source_url = OFFICIAL_SOURCES.get(key)

    if not source_url:
        return ""

    if existing.get("version") == POOL_VERSION and existing.get("object_name"):
        return f"/vehicle-image?key={quote(key, safe='')}"

    try:
        entry = _store_image(key, brand, model, source_url)
        if not entry:
            return ""
        pool[key] = entry
        _save_pool(pool)
        print("Vehicle image pool updated:", key, entry.get("resolved_url"))
        return f"/vehicle-image?key={quote(key, safe='')}"
    except Exception as exc:
        print("Vehicle image pool write failed:", brand, model, repr(exc))
        return ""


def pool_needs_refresh(vehicles):
    pool = _load_pool()
    for vehicle in vehicles:
        key = _key(vehicle.get("brand"), vehicle.get("model"))
        entry = pool.get(key) or {}
        if entry.get("version") != POOL_VERSION or not entry.get("object_name"):
            return True
    return False


def get_vehicle_image(key):
    pool = _load_pool()
    entry = pool.get(key) or {}
    object_name = entry.get("object_name")
    if not object_name:
        return None
    bucket = _bucket()
    if bucket is None:
        return None
    blob = bucket.blob(object_name)
    try:
        if not blob.exists():
            return None
        return blob.download_as_bytes(), entry.get("content_type", "image/jpeg")
    except Exception as exc:
        print("Vehicle image pool read failed:", key, repr(exc))
        return None


def vehicle_image_url(brand, model):
    return ensure_vehicle_image(brand, model)


def enrich_vehicles(vehicles):
    for vehicle in vehicles:
        vehicle["image_url"] = vehicle_image_url(vehicle["brand"], vehicle["model"])
    return vehicles
