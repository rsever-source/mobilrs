import io
import json
import re
import threading
import unicodedata
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from cloud_storage import load_json as gcs_load_json, save_json as gcs_save_json

import pdfplumber
import requests
from bs4 import BeautifulSoup

LIMIT_2026 = 2_873_900
MIN_LOCALITY = 40.0
OTV_REFRESH_LOCK = threading.Lock()
CACHE_FILE = "otv_cache.json"
TZ = ZoneInfo("Europe/Istanbul")

MINISTRY_PAGE = "https://www.sanayi.gov.tr/merkez-birimi/6f188a931f68/yerli-mali"
MINISTRY_PDF = "https://www.sanayi.gov.tr/assets/pdf/birimler/2026YiliMotorluAraclarYerliKatkiOraniBeyanlari.pdf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
}

# Uygun araç listesi burada tutulmaz. Yalnız Bakanlığın 2026 yerli katkı
# beyanından gelir; aşağıdakiler üretici/marka bazlı fiyat okuma kaynaklarıdır.
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

TOYOTA_MODEL_IDS = {
    "COROLLA": "65bfd91d-f2a8-4cbb-bdbc-3834b400492a",
    "C HR": "6c193d6b-514c-436f-ab43-654d97e601d8",
}
TOYOTA_MODEL_URLS = {
    "COROLLA": "https://www.toyota.com.tr/araba-modelleri/corolla-sedan",
    "C HR": "https://www.toyota.com.tr/araba-modelleri/c-hr",
}
TOYOTA_GRADE_URL = "https://dxp-webcarconfig.toyota-europe.com/v1/grade-selector/tr/tr?modelId={}"
HYUNDAI_DEALER_URL = "https://ferhat.hyundaiplaza.com.tr/fiyat-listesi"
FIAT_DEALER_URL = "https://www.tanoto.com.tr/fiat-fiyat-listesi/"
FIAT_ULYSSE_URL = "https://www.tanoto.com.tr/arac-detay/ulysse/"
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
