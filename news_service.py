import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

NEWS_FILE = "news.json"
SOURCES_FILE = "news_sources.json"
MAX_ITEMS = 10
MAX_PENDING = 30
MAX_AI_CANDIDATES = 12
LOOKBACK_HOURS = 168
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
UA = "EngelliMe-NewsBot/1.0 (+https://engelli.me)"
TIMEOUT = 20
AI_TIMEOUT = 60

STRONG_KEYWORDS = (
    "engelli", "engelliler", "engelli birey", "engelli vatandaş",
    "engelli aylığı", "evde bakım", "erişilebilir", "erişilebilirlik",
    "ekpss", "özel eğitim", "özel gereksinim", "özel gereksinimli",
    "ötv", "muafiyet", "bakım yardımı", "ücretsiz seyahat",
    "malulen emekl", "çalışma gücü kaybı",
)

def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _clean(text):
    text = unescape(str(text or ""))
    return re.sub(r"\s+", " ", BeautifulSoup(text, "html.parser").get_text(" ", strip=True)).strip()

def _date(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

def _text(node, names):
    for name in names:
        value = node.findtext(name)
        if value:
            return _clean(value)
    return ""

def _feed_items(source):
    response = requests.get(source["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    nodes = root.findall(".//item") or root.findall(".//{*}entry")
    for node in nodes:
        title = _text(node, ["title", "{*}title"])
        link = _text(node, ["link", "{*}link"])
        if not link:
            link_node = node.find("{*}link")
            if link_node is not None:
                link = _clean(link_node.attrib.get("href", ""))
        description = _text(node, ["description", "summary", "{*}summary", "{*}description", "{*}content"])
        published = _text(node, ["pubDate", "published", "updated", "{*}published", "{*}updated"])
        pub = _date(published)
        if title and link:
            items.append({
                "source": source["name"], "title": title, "url": link,
                "description": description, "published_at": pub.isoformat() if pub else None
            })
    return items

def _html_items(source):
    response = requests.get(source["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = _clean(a.get_text(" ", strip=True))
        href = urljoin(source["url"], a.get("href", ""))
        if not title or len(title) < 12 or href in seen:
            continue
        include = source.get("include_path")
        if include:
            if include not in href or href.rstrip("/") == source["url"].rstrip("/"):
                continue
        elif "/ayrimcilikhatti/engelsiz-yasam/" not in href or href.rstrip("/") == source["url"].rstrip("/"):
            continue
        if href.startswith(source.get("allowed_prefix", "https://www.aa.com.tr/")):
            seen.add(href)
            items.append({
                "source": source["name"], "title": title[:300], "url": href,
                "description": title, "published_at": None
            })
    return items

def _source_items(source):
    if source.get("kind") == "html":
        return _html_items(source)
    return _feed_items(source)

def _strong_relevance(item):
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    return any(keyword in text for keyword in STRONG_KEYWORDS)

def _article_text(url):
    response = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()
    return _clean(soup.get_text(" ", strip=True))[:18000]

def _gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY ayarlanmamış")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 600,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "publish": {"type": "BOOLEAN"},
                    "duplicate": {"type": "BOOLEAN"},
                    "duplicate_reason": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "summary": {"type": "STRING"},
                },
                "required": ["publish", "duplicate", "duplicate_reason", "title", "summary"],
            },
        },
    }
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=payload,
        timeout=AI_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini boş veya beklenmeyen yanıt verdi") from exc
    if not raw:
        raise RuntimeError("Gemini boş yanıt verdi")
    return json.loads(raw)

def _id(item):
    return hashlib.sha256(item["url"].encode("utf-8")).hexdigest()[:20]

def update_news():
    now = datetime.now(timezone.utc)
    sources = _load_json(SOURCES_FILE, [])
    old = _load_json(NEWS_FILE, {"updated_at": None, "items": [], "pending": []})
    existing_items = old.get("items", [])
    pending = old.get("pending", [])
    known = {item.get("id") for item in existing_items}
    candidates = []
    candidate_ids = set()

    for item in pending:
        if item.get("id") and item["id"] not in known and _strong_relevance(item):
            candidates.append(item)
            candidate_ids.add(item["id"])

    source_counts = {}
    for source in sources:
        try:
            source_items = _source_items(source)
            source_counts[source["name"]] = len(source_items)
            is_disability_feed = (
                "Engelli Yaşam" in source.get("name", "")
                or "Engelsiz" in source.get("name", "")
            )
            for item in source_items:
                item["id"] = _id(item)
                if item["id"] in known or item["id"] in candidate_ids:
                    continue
                published = _date(item.get("published_at"))
                if published and published < now - timedelta(hours=LOOKBACK_HOURS):
                    continue
                if is_disability_feed or _strong_relevance(item):
                    candidates.append(item)
                    candidate_ids.add(item["id"])
        except Exception as exc:
            print("Kaynak okunamadı:", source["name"], repr(exc))

    print("Kaynak kayıtları:", source_counts)
    print("AI adayları:", len(candidates))

    candidates.sort(
        key=lambda item: (
            _strong_relevance(item),
            _date(item.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    added = []
    failed = []
    for item in candidates[:MAX_AI_CANDIDATES]:
        try:
            article = _article_text(item["url"])
            prompt = f"""Sen engelli.me için çalışan bir haber editörüsün.
Yalnızca verilen kaynak metnindeki doğrulanabilir bilgileri kullan.
Haber engelli bireylerin haklarını, gelir veya sosyal yardımlarını, bakımını, istihdamını,
eğitimini, sağlığını, ulaşımını, erişilebilirliğini, araç/ÖTV durumunu veya ilgili mevzuatı
somut biçimde etkiliyorsa publish=true ver.
Genel ekonomi, siyaset, savaş, trafik veya gündem haberlerini yalnızca engelli bireyler
üzerinde açık ve somut bir etkisi varsa yayınla; aksi halde publish=false ver.
Önceliği doğrudan engelli bireyleri ilgilendiren haberlere ver.

ÖNEMLİ: MÜKERRER HABER KONTROLÜ YAP.
Aşağıdaki "Mevcut sitedeki haberler" listesini yeni haberle karşılaştır.
Başlıklar veya URL'ler farklı olsa bile aynı olayı, aynı duyuruyu veya aynı gelişmeyi anlatıyorlarsa
duplicate=true ver ve bu haberi yayınlama.
Kararı yalnızca başlık eşleşmesine göre verme; haber metnindeki olay, kurum, kişi, konu, tarih,
ödeme/tutar bilgileri ve diğer somut ayrıntıları birlikte değerlendir.
Aynı konunun farklı bir tarihteki yeni gelişmesi veya gerçekten farklı bir olay ise duplicate=false ver.
Örneğin farklı URL'lere sahip "Evde Bakım Yardımı ödemeleri başladı" ve
"Evde Bakım Yardımı hesaplara yatırıldı" aynı ödeme duyurusunu anlatıyorsa mükerrerdir.
Ancak başka bir ayın yeni ödeme duyurusu ayrı bir haberdir.

Mevcut sitedeki haberler:
{existing_news}

duplicate=true ise publish=false ver.
duplicate_reason alanında kısa olarak neden mükerrer olduğunu belirt.

Mükerrer değilse:
Özgün ve tarafsız Türkçe özet hazırla; kaynak metnini kopyalama.
Özet 6-7 kısa ve tam cümleden oluşsun. Cümleyi ortasında kesme veya yarım bırakma.
Yalnızca kaynakta doğrulanabilen bilgileri içersin.
Başlığı kaynağın anlamını koruyarak kısa ve doğal Türkçe yaz.
Kaynak: {item["source"]}
Başlık: {item["title"]}
Kaynak özeti: {item.get("description", "")}
Kaynak metni:
{article}
"""
            existing_news = existing_items + added
            existing_news_text = "\n".join(
                f"- Başlık: {n.get('title', '')}\n  Özet: {n.get('summary', '')}"
                for n in existing_news
            ) or "Henüz yayınlanmış haber yok."
            prompt = prompt.replace("{existing_news}", existing_news_text)

            result = _gemini(prompt)
            if result.get("duplicate"):
                print("Mükerrer haber atlandı:", item.get("title"), "|", result.get("duplicate_reason", ""))
                continue
            if not result.get("publish"):
                continue
            summary = _clean(result.get("summary"))
            title = _clean(result.get("title"))
            if not summary or not title:
                continue
            added.append({
                "id": item["id"], "title": title[:180], "summary": summary[:900],
                "source": item["source"], "url": item["url"],
                "published_at": item.get("published_at"), "created_at": now.isoformat()
            })
        except Exception as exc:
            print("Haber işlenemedi:", item.get("title"), repr(exc))
            failed.append(item)

    merged = added + existing_items
    merged.sort(key=lambda item: item.get("published_at") or item.get("created_at") or "", reverse=True)
    failed_by_id = {item["id"]: item for item in failed}
    result = {
        "updated_at": now.isoformat(),
        "items": merged[:MAX_ITEMS],
        "pending": list(failed_by_id.values())[:MAX_PENDING],
    }
    _save_json(NEWS_FILE, result)
    print(f"Yeni haber: {len(added)} | Toplam: {len(result['items'])} | Bekleyen: {len(result['pending'])}")
    return result

if __name__ == "__main__":
    update_news()
