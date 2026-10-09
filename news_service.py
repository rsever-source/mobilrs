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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NEWS_FILE = "news.json"
AI_LOG_FILE = "news_ai_log.json"
SOURCES_FILE = "news_sources.json"
MAX_ITEMS = 10
MAX_PENDING = 30
LOOKBACK_HOURS = 168
SEEN_URL_RETENTION_HOURS = 168
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
UA = "Mozilla/5.0 (compatible; EngelliMe-News/1.0; +https://engelli.me)"
TIMEOUT = 20
AI_TIMEOUT = 60

def _make_session():
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    retries = Retry(
        total=3, connect=3, read=2, backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

_SESSION = _make_session()
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
    started = time.monotonic()
    response = _SESSION.get(source["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    elapsed_ms = round((time.monotonic() - started) * 1000)
    print(
        "Haber kaynağı HTTP:",
        {"source": source["name"], "stage": "rss", "status": response.status_code,
         "content_type": response.headers.get("Content-Type", ""),
         "bytes": len(response.content), "elapsed_ms": elapsed_ms,
         "final_url": response.url}
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    # RSS öğeleri bazı yayınlarda namespace ile gelir; hem RSS hem Atom biçimini destekle.
    nodes = root.findall(".//{*}item") or root.findall(".//{*}entry")
    print(
        "Haber kaynağı ayrıştırma:",
        {"source": source["name"], "stage": "rss", "root_tag": root.tag,
         "item_or_entry_nodes": len(nodes)}
    )
    for node in nodes:
        title = _text(node, ["title", "{*}title"])
        link = _text(node, ["link", "{*}link"])
        if not link:
            link_node = node.find("{*}link")
            if link_node is not None:
                link = _clean(link_node.attrib.get("href", ""))
        description = _text(node, ["description", "{*}description", "summary", "{*}summary", "{*}encoded", "content", "{*}content"])
        published = _text(node, ["pubDate", "{*}pubDate", "published", "{*}published", "updated", "{*}updated", "date", "{*}date"])
        pub = _date(published)
        if title and link:
            items.append({
                "source": source["name"], "title": title, "url": link,
                "description": description, "published_at": pub.isoformat() if pub else None
            })
    print(
        "Haber kaynağı sonuç:",
        {"source": source["name"], "stage": "rss", "parsed_items": len(items)}
    )
    return items


def _article_published_at(url):
    try:
        response = _SESSION.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Yaygın yayın tarihi meta etiketleri.
        for attrs in (
            {"property": "article:published_time"},
            {"name": "article:published_time"},
            {"property": "og:article:published_time"},
            {"itemprop": "datePublished"},
            {"property": "datePublished"},
            {"name": "datePublished"},
            {"name": "pubdate"},
            {"name": "publishdate"},
            {"name": "parsely-pub-date"},
            {"name": "date"},
            {"name": "DC.date"},
        ):
            node = soup.find("meta", attrs=attrs)
            if node and node.get("content"):
                parsed = _date(node.get("content")) or _date_from_text(node.get("content"))
                if parsed:
                    return parsed.isoformat()

        # JSON-LD haber şemalarında tarih çoğunlukla datePublished alanındadır.
        for script in soup.find_all("script", type="application/ld+json"):
            match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', script.string or script.get_text())
            if match:
                parsed = _date(match.group(1))
                if parsed:
                    return parsed.isoformat()

        for node in soup.find_all("time"):
            value = node.get("datetime") or node.get_text(" ", strip=True)
            parsed = _date(value) or _date_from_text(value)
            if parsed:
                return parsed.isoformat()
    except Exception as exc:
        print("Haber tarihi okunamadı:", url, repr(exc))
    return None

def _date_from_text(value):
    """Türkçe haber listelerinde görülen tarihleri UTC ISO biçimine çevir."""
    text = _clean(value)
    match = re.search(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)", text)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None

    months = {
        "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
        "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
    }
    match = re.search(
        r"(?<!\d)(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})(?!\d)",
        text, re.IGNORECASE,
    )
    if match:
        day, month_name, year = match.groups()
        try:
            return datetime(int(year), months[month_name.lower()], int(day), tzinfo=timezone.utc)
        except (ValueError, KeyError):
            return None
    return None


def _title_published_at(title):
    return _date_from_text(title)

def _same_page(href, base):
    # Aynı sayfaya giden çıpa (ör. /eyhgm/haberler/#search) haber değildir.
    return href.split("#", 1)[0].rstrip("/") == base.split("#", 1)[0].rstrip("/")


def _html_items(source):
    started = time.monotonic()
    response = _SESSION.get(source["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    elapsed_ms = round((time.monotonic() - started) * 1000)
    print(
        "Haber kaynağı HTTP:",
        {"source": source["name"], "stage": "html_list", "status": response.status_code,
         "content_type": response.headers.get("Content-Type", ""),
         "bytes": len(response.content), "elapsed_ms": elapsed_ms,
         "final_url": response.url}
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links_seen = len(soup.find_all("a", href=True))
    include = source.get("include_path")
    title_keywords = (
        "engelli", "engelsiz", "engellilik", "erişilebilir",
        "serebral palsi", "down sendrom", "özel bakım",
        "bakım merkezi", "özel gereksinim", "görme engelli",
        "işitme engelli", "otizm", "para yüzücü",
    )
    # Aynı haber listede birden çok bağlantı olarak geçebilir: Bakanlık
    # listelerinde kenar çubuğunda tarihsiz, kartta tarihli bir bağlantı bulunur.
    # Önceki davranış ilk görüleni (tarihsiz) seçip tarihli kartı atlıyordu; bu da
    # tarihi detay sayfasından okumaya çalışıp (çoğu zaman başarısız/timeout) haberi
    # kaybediyordu. Tarih sağlayan varyantı tercih et; aksi halde ilk görüleni koru.
    variants = {}
    order = []
    for a in soup.find_all("a", href=True):
        title = _clean(a.get_text(" ", strip=True))
        href = urljoin(source["url"], a.get("href", ""))
        if not title or len(title) < 12 or _same_page(href, source["url"]):
            continue
        if href.rstrip("/") == source["url"].rstrip("/"):
            continue

        # AA bazen Engelsiz Yaşam haberlerini başka kategori URL'leriyle
        # yayımlıyor. Liste sayfasındaki başlık engellilikle ilgiliyse,
        # yalnızca URL yoluna bakarak haberi kaybetme; 7 günlük tarih filtresi
        # ve Gemini'nin uygunluk/mükerrerlik kararı aynen uygulanır.
        title_lower = title.casefold()
        title_relevant = any(keyword in title_lower for keyword in title_keywords)
        path_match = (
            include in href if include
            else "/ayrimcilikhatti/engelsiz-yasam/" in href
        )
        if not path_match and not (
            source.get("name", "").startswith("Anadolu Ajansı")
            and "/tr/ayrimcilikhatti/" in href
            and title_relevant
        ):
            continue
        if not href.startswith(source.get("allowed_prefix", "https://www.aa.com.tr/")):
            continue
        previous = variants.get(href)
        if previous is None:
            variants[href] = {"title": title, "anchor": a}
            order.append(href)
        elif _title_published_at(title) and not _title_published_at(previous["title"]):
            variants[href] = {"title": title, "anchor": a}

    items = []
    path_matches = len(order)
    detail_attempts = 0
    detail_successes = 0
    dated_from_title = 0
    dated_from_context = 0
    for href in order:
        title = variants[href]["title"]
        a = variants[href]["anchor"]

        # Bakanlık haber listelerinde tarih çoğu zaman detay sayfası yerine kartın
        # yanında bulunur. Önce bağlantı başlığını ve en yakın kart kapsayıcılarını tara.
        published = _title_published_at(title)
        if published:
            dated_from_title += 1
        if not published:
            parent = a
            for _ in range(4):
                parent = parent.parent
                if parent is None:
                    break
                context = _clean(parent.get_text(" ", strip=True))
                if len(context) <= 1200:
                    numeric_dates = re.findall(r"(?<!\d)\d{1,2}[./-]\d{1,2}[./-]\d{4}(?!\d)", context)
                    turkish_dates = re.findall(
                        r"(?<!\d)\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}(?!\d)",
                        context, re.IGNORECASE,
                    )
                    # Yalnızca tek bir tarih içeren en yakın kartı kullan; tüm listeyi
                    # kapsayan bir üst elemana ait tarihi başka habere kopyalama.
                    if len(numeric_dates) + len(turkish_dates) == 1:
                        published = _date_from_text(context)
                        if published:
                            dated_from_context += 1
                            break
        if published:
            published_at = published.isoformat()
        else:
            # Liste kartında tarih yoksa detay sayfasının meta/JSON-LD/time alanlarına bak.
            # Zaman aşımı olursa bu kaydı tarih uydurarak yayımlamak yerine atla.
            detail_attempts += 1
            published_at = _article_published_at(href)
            if not published_at:
                continue
            detail_successes += 1
        items.append({
            "source": source["name"], "title": title[:300], "url": href,
            "description": title, "published_at": published_at
        })
    print(
        "Haber kaynağı sonuç:",
        {"source": source["name"], "stage": "html_list", "anchors": links_seen,
         "path_matches": path_matches, "dated_from_title": dated_from_title,
         "dated_from_context": dated_from_context, "detail_attempts": detail_attempts,
         "detail_successes": detail_successes, "parsed_items": len(items)}
    )
    return items


def _tbb_mevzuat_items(source):
    response = _SESSION.get(source["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    keywords = [str(k).lower() for k in source.get("keywords", [])]
    items = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = urljoin(source["url"], a.get("href", ""))
        title = _clean(a.get_text(" ", strip=True))
        if not title or len(title) < 12 or href in seen:
            continue
        if not href.startswith("https://www.tbb.gov.tr/tr/mevzuat-duyurulari/"):
            continue
        if href.rstrip("/") == source["url"].rstrip("/"):
            continue
        if not any(k in title.lower() for k in keywords):
            continue

        seen.add(href)
        description = title
        published_at = None
        try:
            detail = _SESSION.get(href, headers={"User-Agent": UA}, timeout=TIMEOUT)
            detail.raise_for_status()
            detail_soup = BeautifulSoup(detail.text, "html.parser")
            detail_text = _clean(detail_soup.get_text(" ", strip=True))
            marker = re.search(
                r"([0-9]{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+[0-9]{4}\s+Tarihli.*?Resmî Gazete['’]?\s*de yayımlanmıştır\.)",
                detail_text,
                re.IGNORECASE,
            )
            if marker:
                description = marker.group(1)
                date_match = re.search(
                    r"([0-9]{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+([0-9]{4})",
                    description,
                    re.IGNORECASE,
                )
                if date_match:
                    months = {
                        "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
                        "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
                    }
                    day, month_name, year = date_match.groups()
                    published_at = datetime(
                        int(year), months[month_name.lower()], int(day), tzinfo=timezone.utc
                    ).isoformat()
        except Exception as exc:
            print("TBB mevzuat duyurusu okunamadı:", href, repr(exc))

        if not published_at:
            continue

        items.append({
            "source": source["name"],
            "title": title[:300],
            "url": href,
            "description": description[:900],
            "published_at": published_at,
        })

    return items

def _source_items(source):
    if source.get("kind") == "tbb_mevzuat":
        return _tbb_mevzuat_items(source)
    if source.get("kind") == "html":
        return _html_items(source)
    return _feed_items(source)


def _article_text(url):
    response = _SESSION.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
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
            "maxOutputTokens": 900,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "publish": {"type": "BOOLEAN"},
                    "duplicate": {"type": "BOOLEAN"},
                    "duplicate_reason": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "summary": {"type": "STRING"},
                    "detail_summary": {"type": "STRING"},
                },
                "required": ["publish", "duplicate", "duplicate_reason", "title", "summary", "detail_summary"],
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



def _update_source_alert(logs):
    """6 çalışmanın en az 5'inde hata veren kaynaklar için tek GitHub Issue yönetir."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "rsever-source/mobilrs")
    if not token:
        print("Kaynak alarmı: GITHUB_TOKEN yok; Issue güncellenmedi.")
        return

    recent_logs = logs[-6:]
    failures = {}
    for entry in recent_logs:
        failed_sources = {
            item.get("source")
            for item in entry.get("source_errors", [])
            if item.get("source")
        }
        for name in failed_sources:
            failures[name] = failures.get(name, 0) + 1

    active = {name: count for name, count in failures.items() if count >= 5}
    title = "Engelli.me haber kaynakları hata alarmı"
    api = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        response = requests.get(
            api, headers=headers, params={"state": "open", "per_page": 100}, timeout=15
        )
        response.raise_for_status()
        issue = next(
            (
                item for item in response.json()
                if item.get("title") == title and "pull_request" not in item
            ),
            None,
        )

        if active:
            details = "\n".join(
                f"- **{name}**: son {len(recent_logs)} çalışmanın {count}'inde başarısız."
                for name, count in sorted(active.items())
            )
            body = (
                "Otomatik kaynak izleme alarmı. Aynı kaynak son 6 haber çalışmasının "
                "en az 5'inde kaynak okuma hatası verdi.\n\n"
                f"{details}\n\n"
                f"Son kontrol: {datetime.now(timezone.utc).isoformat()}\n\n"
                "Bu Issue otomatik olarak güncellenir ve sorunlu kaynaklar düzeldiğinde kapatılır."
            )
            if issue:
                update = requests.patch(
                    f"{api}/{issue['number']}", headers=headers,
                    json={"body": body}, timeout=15
                )
                update.raise_for_status()
                print(f"Kaynak alarmı güncellendi: #{issue['number']}")
            else:
                created = requests.post(
                    api, headers=headers, json={"title": title, "body": body}, timeout=15
                )
                created.raise_for_status()
                print(f"Kaynak alarmı açıldı: #{created.json().get('number')}")
        elif issue:
            close = requests.patch(
                f"{api}/{issue['number']}", headers=headers,
                json={"state": "closed", "state_reason": "completed"}, timeout=15
            )
            close.raise_for_status()
            print(f"Kaynak alarmı kapatıldı: #{issue['number']}")
        else:
            print("Kaynak alarmı: alarm eşiğini aşan kaynak yok.")
    except Exception as exc:
        # Alarm sistemi arızası haber üretimini durdurmasın; hata Actions logunda görünür.
        print("Kaynak alarmı GitHub Issue güncellenemedi:", repr(exc))


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
    source_errors = []
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
            error_text = repr(exc)
            print("Kaynak okunamadı:", source["name"], error_text)
            source_errors.append({
                "source": source["name"],
                "error": error_text,
                "kind": "source_fetch_error",
            })

    print("Kaynak kayıtları:", source_counts)
    print("Kaynak hataları:", source_errors)
    print("AI adayları:", len(candidates))
    added = []
    failed = []
    ai_log = {
        "run_at": now.isoformat(),
        "model": GEMINI_MODEL,
        "source_errors": source_errors,
        "candidates": [],
    }

    for item in candidates:
        ai_entry = {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at"),
            "status": "not_sent",
        }
        try:
            if item.get("source") == "Türkiye Belediyeler Birliği – Mevzuat Duyuruları":
                tbb_response = _SESSION.get(item["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
                tbb_response.raise_for_status()
                tbb_soup = BeautifulSoup(tbb_response.text, "html.parser")
                official_url = ""
                for link in tbb_soup.find_all("a", href=True):
                    href = urljoin(item["url"], link.get("href", ""))
                    if "resmigazete.gov.tr/eskiler/" in href:
                        official_url = href
                        break
                if not official_url:
                    raise RuntimeError("TBB duyurusunda Resmî Gazete bağlantısı bulunamadı")
                article = _article_text(official_url)
            else:
                article = _article_text(item["url"])
            source_context = ""
            if item.get("source") == "Türkiye Belediyeler Birliği – Mevzuat Duyuruları":
                source_context = """TBB / RESMÎ GAZETE DUYURULARI İÇİN EK KURAL:
detail_summary içinde yönetmelikteki önemli maddeleri sırayla ve ayrı ayrı ver.
Her madde mutlaka yeni bir satırda başlasın; maddeleri aynı paragrafta birleştirme.
Format: "- Madde X: açıklama"
Mümkünse maddelerin arasında birer boş satır bırak.
Yalnızca Resmî Gazete metninde doğrulanabilen madde numaralarını ve içerikleri kullan; madde numarası uydurma.
"""
            if item.get("source") == "Sosyal Güvenlik Kurumu – Duyurular":
                source_context = """SGK DUYURULARI İÇİN EK KURAL:
Bu kaynak SGK'nın resmi Duyurular sayfasıdır. Kaynağın SGK olması tek başına yayınlama nedeni değildir.
Yalnızca engelli bireyler açısından doğrudan veya anlamlı ve somut etkisi olan duyuruları yayınla.
Özellikle malullük/engelli emekliliği, engelli istihdamı ve 2828 kapsamındaki yerleştirme/atama,
GSS ve sağlık hizmetleri, SUT değişiklikleri, ilaç geri ödeme düzenlemeleri, tıbbi malzeme,
protez/ortez veya görme/işitme gibi yardımcı cihazlara ilişkin ve engelli bireyleri doğrudan
etkileyen diğer sosyal güvenlik uygulamaları değerlendirilebilir.
Genel personel alımı, kurum içi görevlendirme, gayrimenkul satışları, teknik sistem duyuruları,
generic prim/işveren işlemleri veya engelli bireylere somut etkisi gösterilemeyen genel SGK
duyurularını publish=false ver.

"""
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
Bu "summary" alanı haber kartlarında ve mobil haber detayında kullanılır; gereksiz ayrıntıya girme.
Ayrıca "detail_summary" alanında aynı haberi biraz daha ayrıntılı anlatan 8-10 kısa ve tam cümle oluştur.
"detail_summary" yeni bilgi uydurmasın; yalnızca kaynak metnindeki doğrulanabilir ayrıntıları daha düzenli biçimde anlatsın.
İki özet aynı olmasın; detail_summary, summary'den yalnızca gerektiği kadar daha ayrıntılı olsun.
detail_summary metnini tek ve uzun bir paragraf halinde yazma. Her ayrı bilgi veya cümle yeni bir satırda yer alsın ve metin okunabilir bir düzende ilerlesin; mümkünse bilgi grupları arasında birer boş satır bırak.
Yalnızca kaynakta doğrulanabilen bilgileri içersin.
Başlığı kaynağın anlamını koruyarak kısa ve doğal Türkçe yaz.
Kaynak: {item["source"]}
{source_context}
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

            # Gemini'ye gönderilecek URL'yi çağrıdan hemen önce kalıcı olarak kaydet.
            # Gemini hata verse bile aynı URL sonraki çalışmada tekrar gönderilmesin.
            seen_urls[item["url"]] = now.isoformat()
            _save_json(NEWS_FILE, {
                **old,
                "seen_urls": seen_urls,
            })

            result = _gemini(prompt)
            ai_entry["status"] = "gemini_decision"
            ai_entry["publish"] = bool(result.get("publish"))
            ai_entry["duplicate"] = bool(result.get("duplicate"))
            ai_entry["duplicate_reason"] = _clean(result.get("duplicate_reason"))
            ai_entry["generated_title"] = _clean(result.get("title"))
            ai_entry["summary"] = _clean(result.get("summary"))
            ai_entry["detail_summary"] = _clean(result.get("detail_summary"))
            ai_entry["decision"] = (
                "duplicate" if result.get("duplicate")
                else "publish" if result.get("publish")
                else "reject"
            )
            if result.get("duplicate"):
                print("Mükerrer haber atlandı:", item.get("title"), "|", result.get("duplicate_reason", ""))
                ai_log["candidates"].append(ai_entry)
                continue
            if not result.get("publish"):
                ai_log["candidates"].append(ai_entry)
                continue
            if item.get("source") == "Türkiye Belediyeler Birliği – Mevzuat Duyuruları":
                title = item.get("title", "")
                summary = item.get("description", "")
                raw_detail_summary = result.get("detail_summary")
                detail_summary = re.sub(r"\s*([•-]\s*Madde\s+)", r"\n\n- Madde ", str(raw_detail_summary or ""), flags=re.IGNORECASE).strip()
                detail_summary = re.sub(r"(?<!^)\s*- Madde\s+", "- Madde ", detail_summary)
            else:
                summary = _clean(result.get("summary"))
                detail_summary = _clean(result.get("detail_summary")) or summary
                title = _clean(result.get("title"))
            if not summary or not title:
                ai_entry["status"] = "gemini_invalid_output"
                ai_log["candidates"].append(ai_entry)
                continue
            ai_entry["status"] = "published"
            ai_log["candidates"].append(ai_entry)
            added.append({
                "id": item["id"], "title": title[:180], "summary": summary[:900], "detail_summary": detail_summary[:1400],
                "source": item["source"], "url": item["url"],
                "published_at": item.get("published_at"), "created_at": now.isoformat()
            })
        except Exception as exc:
            print("Haber işlenemedi:", item.get("title"), repr(exc))
            ai_entry["status"] = "not_processed"
            ai_entry["error"] = repr(exc)
            ai_log["candidates"].append(ai_entry)
            failed.append(item)

    added_ids = {item.get("id") for item in added}
    merged = added + [item for item in existing_items if item.get("id") not in added_ids]
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
    # Mevcut log geçmişini koru; alarm hesabı yalnızca son 6 çalışmayı kullanır.
    previous_ai_logs = previous_ai_logs[-7:]
    _save_json(AI_LOG_FILE, previous_ai_logs)
    _update_source_alert(previous_ai_logs)
    _save_json(NEWS_FILE, result)
    print(f"Yeni haber: {len(added)} | Toplam: {len(result['items'])} | Bekleyen: {len(result['pending'])}")
    return result


if __name__ == "__main__":
    update_news()
