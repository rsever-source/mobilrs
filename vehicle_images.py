import json
import re
import unicodedata
from urllib.parse import quote

import requests

from cloud_storage import load_json as gcs_load_json, save_json as gcs_save_json

POOL_FILE = "vehicle_image_pool.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {
    "User-Agent": "EngelliMeVehicleImagePool/1.0 (https://engelli.me)",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

# Hand-verified stable images for models already present. New models are discovered
# automatically from Wikimedia Commons and cached in the same pool.
SEED_IMAGES = {
    "RENAULT|BOREAL": "https://upload.wikimedia.org/wikipedia/commons/4/42/2026_Renault_Boreal_front_view_01.png",
    "RENAULT|DUSTER": "https://imgd.aeplcdn.com/1920x1080/n/cw/ec/163801/duster-exterior-right-front-three-quarter-5.jpeg?isig=0&q=90",
    "RENAULT|CLIO": "https://cms.bilhandel.dk/media/gihc2rsz/g0vc5o6wmaaitkp.jpeg",
    "RENAULT|MEGANE": "https://imagecdnsa.zigwheels.ae/large/gallery/exterior/33/371/renault-megane-24585.jpg",
    "TOYOTA|C HR": "https://toyota-media.ch/__image/a/2248486/alias/xxl/v/4/c/25/ar/16-9/fn/Toyota%20C-HR%202026_01.jpg",
    "TOYOTA|COROLLA": "https://modenamotorsgmbh.com/98819-thickbox_default/toyota-corolla-sedan-18-hybrid-elite-edition-my2026.jpg",
    "HYUNDAI|I20": "https://storage.googleapis.com/fp-media/1/2025/12/Hyundai-i20-MY26.jpg",
    "HYUNDAI|BAYON": "https://storage.googleapis.com/fp-media/1/2025/12/Hyundai-Bayon-MY26.jpg",
    "TOGG|T10X": "https://www.togg.eu/assets/img/68a4514343d1be59b0dab71b_T10X-Range.webp",
    "FIAT|EGEA SEDAN": "https://arbstorage.mncdn.com/modelphotos/60cf26a2-ff58-461c-a8a5-fbc3cbce58b1_912x513.jpg",
    "FIAT|EGEA CROSS": "https://www.fiat.com.tr/content/dam/fiat/cross/egea-cross/egea-cross-gallery.jpg",
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
    if isinstance(pool, dict):
        return pool
    return {}


def _save_pool(pool):
    gcs_save_json(POOL_FILE, pool)


def _is_image_url(url):
    return bool(url and re.search(r"\.(?:jpe?g|png|webp)(?:$|\?)", url, re.I))


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
        "iiurlwidth": 1200,
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

    brand_n = _norm(brand)
    model_n = _norm(model)
    # Only accept a result whose filename/title contains both brand and model.
    candidates = []
    for page in pages:
        title = _norm(page.get("title", ""))
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        mime = str(info.get("mime") or "")
        if not url or not mime.startswith("image/"):
            continue
        score = 0
        if brand_n in title:
            score += 3
        if model_n in title:
            score += 5
        if "front" in title or "3 4" in title or "three quarter" in title:
            score += 2
        if score >= 8:
            candidates.append((score, int(info.get("width") or 0), url, page.get("title", "")))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    score, width, url, title = candidates[0]
    if width and width < 500:
        return None
    print("Vehicle image discovered:", brand, model, title, url)
    return url


def ensure_vehicle_image(brand, model):
    key = _key(brand, model)
    pool = _load_pool()

    if key in pool and pool[key].get("url"):
        return pool[key]["url"]

    if key in SEED_IMAGES:
        pool[key] = {
            "url": SEED_IMAGES[key],
            "source": "seed",
            "brand": brand,
            "model": model,
        }
        _save_pool(pool)
        return SEED_IMAGES[key]

    url = _commons_search(brand, model)
    if not url:
        return ""
    pool[key] = {
        "url": url,
        "source": "Wikimedia Commons auto-discovery",
        "brand": brand,
        "model": model,
    }
    _save_pool(pool)
    return url


def enrich_vehicles(vehicles):
    for vehicle in vehicles:
        vehicle["image_url"] = ensure_vehicle_image(vehicle["brand"], vehicle["model"])
    return vehicles
