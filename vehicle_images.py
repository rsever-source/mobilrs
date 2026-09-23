import hashlib
import re
import unicodedata
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup
from google.cloud import storage

from cloud_storage import load_json as gcs_load_json, save_json as gcs_save_json

POOL_FILE = "vehicle_image_pool.json"
POOL_PREFIX = "vehicle-images/"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
POOL_VERSION = 3
HEADERS = {
    "User-Agent": "EngelliMeVehicleImagePool/2.0 (https://engelli.me)",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

# Sources are either direct images or official/Commons pages. The worker downloads
# the actual image into our GCS pool; the browser never depends on the source URL.
SEED_IMAGES = {
    "RENAULT|BOREAL": "https://upload.wikimedia.org/wikipedia/commons/4/42/2026_Renault_Boreal_front_view_01.png",
    "RENAULT|DUSTER": "https://img-ik.cars.co.za/news-site-za/images/2025/03/2025-Renault-Duster-Launch-6.jpg",
    "RENAULT|CLIO": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Renault_Clio_Evolution_(V,_Facelift)_%E2%80%93_f_04042026.jpg?width=1600",
    "RENAULT|MEGANE": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Renault_Megane_IV_Sedan_1X7A0225.jpg?width=1600",
    "TOYOTA|C HR": "https://www.toyota.com.tr/araba-modelleri/c-hr",
    "TOYOTA|COROLLA": "https://commons.wikimedia.org/wiki/Special:Redirect/file/TOYOTA_COROLLA_SEDAN_(E210)_China_(14).jpg?width=1600",
    "HYUNDAI|I20": "https://storage.googleapis.com/fp-media/1/2025/12/Hyundai-i20-MY26.jpg",
    "HYUNDAI|BAYON": "https://storage.googleapis.com/fp-media/1/2025/12/Hyundai-Bayon-MY26.jpg",
    "TOGG|T10X": "https://www.togg.eu/assets/img/68a4514343d1be59b0dab71b_T10X-Range.webp",
    "TOGG|T10F": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Togg_T10F_IAA_2025_DSC_2140.jpg?width=1600",
    "FIAT|EGEA SEDAN": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Fiat_Egea_in_Pendik_Istanbul.jpg?width=1600",
    "FIAT|EGEA CROSS": "https://www.fiat.com.tr/modeller/egea",
    "FIAT|ULYSSE": "https://manage.sifiraracal.com/public/resim/galeri/1002/43084/fiat-ulysse.png",
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


def _direct_image_url(url, response):
    ctype = (response.headers.get("content-type") or "").lower()
    if ctype.startswith("image/"):
        return response.url, ctype

    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception:
        return None, None

    candidates = []
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        content = meta.get("content")
        if content and prop in {"og:image", "twitter:image"}:
            candidates.append(urljoin(response.url, content))
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            candidates.append(urljoin(response.url, src))

    for candidate in candidates:
        try:
            rr = requests.get(candidate, headers=HEADERS, timeout=20)
            rr.raise_for_status()
            ct = (rr.headers.get("content-type") or "").lower()
            if ct.startswith("image/") and len(rr.content) >= 10000:
                return rr.url, ct
        except Exception:
            continue
    return None, None


def _download_image(source_url):
    r = requests.get(source_url, headers=HEADERS, timeout=25, allow_redirects=True)
    r.raise_for_status()
    final_url, content_type = _direct_image_url(source_url, r)
    if not final_url:
        return None
    if final_url != r.url:
        r = requests.get(final_url, headers=HEADERS, timeout=25, allow_redirects=True)
        r.raise_for_status()
        content_type = (r.headers.get("content-type") or content_type or "").lower()
    if not content_type.startswith("image/") or len(r.content) < 10000:
        return None
    return r.content, content_type, r.url


def _extension(content_type, url):
    if "png" in content_type:
        return "png"
    if "webp" in content_type:
        return "webp"
    if "gif" in content_type:
        return "gif"
    return "jpg"


def _store_image(key, brand, model, source_url, source_kind):
    downloaded = _download_image(source_url)
    if not downloaded:
        return None
    data, content_type, resolved_url = downloaded
    bucket = _bucket()
    if bucket is None:
        return None

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    object_name = f"{POOL_PREFIX}{digest}.{_extension(content_type, resolved_url)}"
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type=content_type)

    return {
        "version": POOL_VERSION,
        "object_name": object_name,
        "content_type": content_type,
        "source_url": source_url,
        "resolved_url": resolved_url,
        "source": source_kind,
        "brand": brand,
        "model": model,
    }


def _commons_search(brand, model):
    query = f'"{brand} {model}"'
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 12,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": 1600,
        "format": "json",
        "formatversion": 2,
    }
    try:
        r = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        pages = (r.json().get("query") or {}).get("pages") or []
    except Exception as exc:
        print("Vehicle image discovery failed:", brand, model, repr(exc))
        return None

    brand_n, model_n = _norm(brand), _norm(model)
    candidates = []
    for page in pages:
        title = _norm(page.get("title", ""))
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        mime = str(info.get("mime") or "")
        if not url or not mime.startswith("image/"):
            continue
        # Both brand and model must be in the Commons filename/title.
        if brand_n not in title or model_n not in title:
            continue
        score = 8
        if any(x in title for x in ("FRONT", "THREE QUARTER", "3 4", "SIDE")):
            score += 2
        width = int(info.get("width") or 0)
        if width < 800:
            continue
        candidates.append((score, width, url, page.get("title", "")))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    chosen = candidates[0]
    print("Vehicle image discovered:", brand, model, chosen[3], chosen[2])
    return chosen[2]


def ensure_vehicle_image(brand, model):
    key = _key(brand, model)
    pool = _load_pool()
    existing = pool.get(key) or {}

    # Versioned seeds allow us to replace old/wrong images once, then keep the
    # downloaded file locally in our pool on all later visits.
    source_url = SEED_IMAGES.get(key)
    source_kind = "verified seed"
    if source_url is None:
        source_url = _commons_search(brand, model)
        source_kind = "Wikimedia Commons auto-discovery"

    if not source_url:
        return ""

    if (
        existing.get("version") == POOL_VERSION
        and existing.get("object_name")
    ):
        return f"/vehicle-image?key={quote(key, safe='')}"

    try:
        entry = _store_image(key, brand, model, source_url, source_kind)
        if not entry:
            return ""
        pool[key] = entry
        _save_pool(pool)
        return f"/vehicle-image?key={quote(key, safe='')}"
    except Exception as exc:
        print("Vehicle image pool write failed:", brand, model, repr(exc))
        return ""


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
