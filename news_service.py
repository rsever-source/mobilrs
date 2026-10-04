import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

NEWS_FILE = "news.json"
AI_LOG_FILE = "news_ai_log.json"
SOURCES_FILE = "news_sources.json"
MAX_ITEMS = 10
MAX_PENDING = 30
LOOKBACK_HOURS = 168
SEEN_URL_RETENTION_HOURS = 168
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
UA = "EngelliMe-NewsBot/1.0 (+https://engelli.me)"
TIMEOUT = 20
AI_TIMEOUT = 60
GEMINI_MIN_INTERVAL = 4
GEMINI_RETRY_DELAYS = (2, 4, 8, 16)
_gemini_last_request_at = None


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


def _article_published_at(url):
    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for attrs in (
            {"property": "article:published_time"},
            {"name": "article:published_time"},
            {"itemprop": "datePublished"},
            {"property": "datePublished"},
            {"name": "datePublished"},
        ):
            node = soup.find("meta", attrs=attrs)
            if node and node.get("content"):
                parsed = _date(node.get("content"))
                if parsed:
                    return parsed.isoformat()
        for node in soup.find_all("time"):
            value = node.get("datetime") or node.get_text(" ", strip=True)
            parsed = _date(value)
            if parsed:
                return parsed.isoformat()
    except Exception as exc:
        print("Haber tarihi okunamadı:", url, repr(exc))
    return None


def _title_published_at(title):
    text = _clean(title)
    match = re.search(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)", text)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


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
            published_at = _title_published_at(title)
            if not published_at:
                published_at = _article_published_at(href)
            if not published_at:
                continue
            items.append({
                "source": source["name"], "title": title[:300], "url": href,
                "description": title, "published_at": published_at
            })
    return items


def _source_items(source):
    if source.get("kind") == "html":
        return _html_items(source)
    return _feed_items(source)


def _article_text(url):
    response = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()
    return _clean(soup.get_text(" ", strip=True))[:18000]


def _gemini(prompt):
    global _gemini_last_request_at
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    for attempt in range(len(GEMINI_RETRY_DELAYS) + 1):
        if attempt == 0 and _gemini_last_request_at is not None:
            elapsed = time.monotonic() - _gemini_last_request_at
            if elapsed < GEMINI_MIN_INTERVAL:
                time.sleep(GEMINI_MIN_INTERVAL - elapsed)
        response = requests.post(url, headers=headers, json=payload, timeout=AI_TIMEOUT)
        _gemini_last_request_at = time.monotonic()
        if response.status_code in (408, 429, 503) and attempt < len(GEMINI_RETRY_DELAYS):
            delay = GEMINI_RETRY_DELAYS[attempt]
            print(f"Gemini geçici hata {response.status_code}; {delay} saniye sonra yeniden denenecek ({attempt + 1}/{len(GEMINI_RETRY_DELAYS)})")
            time.sleep(delay)
            continue
        response.raise_for_status()
        data = response.json()
        try:
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Gemini boş veya beklenmeyen yanıt verdi") from exc
        if not raw:
            raise RuntimeError("Gemini boş yanıt verdi")
        return json.loads(raw)
    raise RuntimeError("Gemini geçici hatası yeniden denemelerden sonra devam etti")


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
    cutoff = now - timedelta(hours=LOOKBACK_HOURS)
    seen_cutoff = now - timedelta(hours=SEEN_URL_RETENTION_HOURS)

    # Aynı URL'yi 7 gün boyunca Gemini'ye tekrar gönderme.
    # Kayıtlar her çalışmada 7 günden eski olanlar temizlenerek dosyanın şişmesi önlenir.
    raw_seen_urls = old.get("seen_urls", {})
    if not isinstance(raw_seen_urls, dict):
        raw_seen_urls = {}
    seen_urls = {}
    for url, seen_at in raw_seen_urls.items():
        parsed = _date(seen_at)
        if parsed and parsed >= seen_cutoff and parsed <= now:
            seen_urls[url] = parsed.isoformat()

    for item in pending:
        if item.get("id") and item["id"] not in known:
            published = _date(item.get("published_at"))
            if published and published <= now and published >= cutoff:
                candidates.append(item)
                candidate_ids.add(item["id"])

    source_counts = {}
    for source in sources:
        try:
            source_items = _source_items(source)
            source_counts[source["name"]] = len(source_items)
            for item in source_items:
                item["id"] = _id(item)
                if item["id"] in known or item["id"] in candidate_ids or item.get("url") in seen_urls:
                    continue
                published = _date(item.get("published_at"))
                if not published or published > now or published < cutoff:
                    continue
                candidates.append(item)
                candidate_ids.add(item["id"])
        except Exception as exc:
            print("Kaynak okunamadı:", source["name"], repr(exc))

    print("Kaynak kayıtları:", source_counts)
    print("AI adayları:", len(candidates))
    added = []
    failed = []
    ai_log = {"run_at": now.isoformat(), "model": GEMINI_MODEL, "candidates": []}

    for item in candidates:
        ai_entry = {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at"),
            "status": "not_sent",
        }
        try:
            article = _article_text(item["url"])
            prompt = f"""Sen engelli.me için çalışan bir haber editörüsün.
Yalnızca verilen kaynak metnindeki doğrulanabilir bilgileri kullan.
Haberin Engelli.me için uygun olup olmadığına kendin karar ver.
Başlıkta veya kısa açıklamada belirli anahtar kelimelerin geçmesini şart koşma; haber metninin tamamındaki bağlamı değerlendir.
Engelli bireylerin hakları, gelir veya sosyal yardımları, bakımı, istihdamı, eğitimi,
sağlığı, ulaşımı, erişilebilirliği, araç/ÖTV durumu veya ilgili mevzuatla doğrudan ya da
anlamlı biçimde ilgiliyse publish=true ver.
Genel ekonomi, siyaset, savaş, trafik veya gündem haberlerini yalnızca engelli bireyler
üzerinde açık ve somut bir etkisi varsa publish=true ver.
Aksi durumda publish=false ver.

ÖNEMLİ: MÜKERRER HABER KONTROLÜ YAP.
Aşağıdaki "Mevcut sitedeki haberler" listesini yeni haberle karşılaştır.
duplicate kararı yalnızca başlık veya genel konu benzerliğine göre verilmemeli.
İki haberin aynı somut olay, aynı duyuru veya aynı gelişme olup olmadığını belirle.
Aynı olay farklı başlıkla veya farklı kaynakta anlatılıyorsa duplicate=true olabilir.
Ancak aynı konu hakkında daha sonra gerçekleşen yeni bir gelişme duplicate değildir.
Özellikle tarih, dönem, ödeme ayı, tutar, karar, uygulama veya sonuç değişmişse yeni gelişme olarak değerlendir.
Örneğin:
- Eylül Evde Bakım Yardımı ödemelerinin farklı kaynaklardaki duyuruları aynı Eylül ödemesini anlatıyorsa mükerrerdir.
- Ekim Evde Bakım Yardımı ödemesi Eylül haberinden ayrı, yeni bir gelişmedir.
duplicate_reason alanında mükerrerliği somut olay veya dönem üzerinden açıkla.
Sadece "aynı konu", "benzer haber" veya "aynı alan" gibi genel gerekçeler duplicate için yeterli değildir.

Mevcut sitedeki haberler:
{{existing_news}}

duplicate=true ise publish=false ver.

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
            ai_entry["status"] = "gemini_decision"
            ai_entry["publish"] = bool(result.get("publish"))
            ai_entry["duplicate"] = bool(result.get("duplicate"))
            ai_entry["duplicate_reason"] = _clean(result.get("duplicate_reason"))
            ai_entry["generated_title"] = _clean(result.get("title"))
            ai_entry["summary"] = _clean(result.get("summary"))
            ai_entry["decision"] = (
                "duplicate" if result.get("duplicate")
                else "publish" if result.get("publish")
                else "reject"
            )
            # Gemini değerlendirmesi tamamlandı; aynı URL 7 gün boyunca tekrar işlenmesin.
            seen_urls[item["url"]] = now.isoformat()
            if result.get("duplicate"):
                print("Mükerrer haber atlandı:", item.get("title"), "|", result.get("duplicate_reason", ""))
                ai_log["candidates"].append(ai_entry)
                continue
            if not result.get("publish"):
                ai_log["candidates"].append(ai_entry)
                continue
            summary = _clean(result.get("summary"))
            title = _clean(result.get("title"))
            if not summary or not title:
                ai_entry["status"] = "gemini_invalid_output"
                ai_log["candidates"].append(ai_entry)
                continue
            ai_entry["status"] = "published"
            ai_log["candidates"].append(ai_entry)
            added.append({
                "id": item["id"], "title": title[:180], "summary": summary[:900],
                "source": item["source"], "url": item["url"],
                "published_at": item.get("published_at"), "created_at": now.isoformat()
            })
        except Exception as exc:
            print("Haber işlenemedi:", item.get("title"), repr(exc))
            ai_entry["status"] = "not_processed"
            ai_entry["error"] = repr(exc)
            ai_log["candidates"].append(ai_entry)
            failed.append(item)

    merged = added + existing_items
    merged.sort(key=lambda item: item.get("published_at") or item.get("created_at") or "", reverse=True)
    failed_by_id = {item["id"]: item for item in failed}
    result = {
        "updated_at": now.isoformat(),
        "items": merged[:MAX_ITEMS],
        "pending": list(failed_by_id.values())[:MAX_PENDING],
        "seen_urls": seen_urls,
    }
    previous_ai_logs = _load_json(AI_LOG_FILE, [])
    if not isinstance(previous_ai_logs, list):
        previous_ai_logs = []
    previous_ai_logs.append(ai_log)
    _save_json(AI_LOG_FILE, previous_ai_logs[-7:])
    _save_json(NEWS_FILE, result)
    print(f"Yeni haber: {len(added)} | Toplam: {len(result['items'])} | Bekleyen: {len(result['pending'])}")
    return result


if __name__ == "__main__":
    update_news()
