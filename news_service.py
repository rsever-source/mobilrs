import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin

from system_report import append_news_run
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NEWS_FILE = "news.json"
AI_LOG_FILE = "news_ai_log.json"
SOURCES_FILE = "news_sources.json"
MAX_ITEMS = 12
MAX_PENDING = 30
LOOKBACK_HOURS = 168
SEEN_URL_RETENTION_HOURS = 168
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
UA = "Mozilla/5.0 (compatible; EngelliMe-News/1.0; +https://engelli.me)"
TIMEOUT = 20
AI_TIMEOUT = 60

# Per-run diagnostics included in the central news report.
_GIB_SOURCE_DIAGNOSTICS = {}
_SOURCE_DIAGNOSTICS = {}

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
    root_name = str(root.tag).split("}")[-1].lower()
    rss_structure_errors = []
    if root_name not in {"rss", "feed", "rdf"}:
        rss_structure_errors.append(
            f"Beklenmeyen RSS/Atom kök etiketi: {root.tag!r}"
        )
    elif root_name == "rss" and root.find("channel") is None:
        rss_structure_errors.append("RSS yanıtında beklenen channel düğümü bulunamadı.")
    elif root_name == "feed" and not root.findall(".//{*}title"):
        rss_structure_errors.append("Atom yanıtında beklenen title alanı bulunamadı.")
    _SOURCE_DIAGNOSTICS[source["name"]] = {
        "stage": "rss", "root_tag": root.tag,
        "item_or_entry_nodes": len(nodes), "errors": rss_structure_errors,
    }
    print(
        "Haber kaynağı ayrıştırma:",
        {"source": source["name"], "stage": "rss", "root_tag": root.tag,
         "item_or_entry_nodes": len(nodes), "errors": rss_structure_errors}
    )
    # Geçerli RSS/Atom akışında sıfır öğe tek başına hata değildir:
    # kaynak gerçekten boş olabilir. Sayı source_diagnostics içinde yine görünür.
    if rss_structure_errors:
        raise ValueError("; ".join(rss_structure_errors))
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
        published_at = pub.isoformat() if pub else None
        # AA RSS öğelerinin her birinin detay sayfasını ayrıca aç; mümkünse
        # yayın tarihini doğrudan haber sayfasından al, okunamazsa RSS tarihini koru.
        if title and link and source.get("name", "").startswith("Anadolu Ajansı"):
            detail_published_at = _article_published_at(link)
            if detail_published_at:
                published_at = detail_published_at
        if title and link:
            items.append({
                "source": source["name"], "title": title, "url": link,
                "description": description, "published_at": published_at
            })
    if nodes and not items:
        rss_structure_errors.append(
            "RSS/Atom içinde item/entry kayıtları var ancak başlık ve bağlantı alanları ayrıştırılamadı."
        )
    _SOURCE_DIAGNOSTICS[source["name"]] = {
        "stage": "rss", "root_tag": root.tag,
        "item_or_entry_nodes": len(nodes), "parsed_items": len(items),
        "errors": rss_structure_errors,
    }
    print(
        "Haber kaynağı sonuç:",
        {"source": source["name"], "stage": "rss", "parsed_items": len(items)}
    )
    return items


def _article_published_at(url, diagnostics=None):
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

        # AA'nın bazı haberlerinde tarih meta/JSON-LD/time alanında değil,
        # başlık-yazar-tarih bloğunda normal görünür metin olarak yer alıyor.
        # Sayfanın tamamını taramak yan haber tarihini seçebileceğinden yalnızca
        # başlığın yakınındaki küçük kapsayıcıları kontrol et ve tek tarih varsa kabul et.
        # AA haber sayfalarında başlık h1 değil; yayın tarihi yazar-tarih
        # bloğunda (div.news-writeby / div.news-maindiv) düz metin olarak
        # yer alır. h1/main bulunmasa da bu bloğu oku.
        aa_published = _aa_byline_published_at(soup)
        if aa_published:
            return aa_published.isoformat()
        heading = soup.find("h1")
        if heading:
            parent = heading
            for _ in range(5):
                parent = parent.parent
                if parent is None:
                    break
                context = _clean(parent.get_text(" ", strip=True))
                if not context or len(context) > 2500:
                    continue
                numeric_dates = re.findall(
                    r"(?<!\d)\d{1,2}[./-]\d{1,2}[./-]\d{4}(?!\d)", context
                )
                turkish_dates = re.findall(
                    r"(?<!\d)\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}(?!\d)",
                    context, re.IGNORECASE,
                )
                if len(numeric_dates) + len(turkish_dates) != 1:
                    continue
                parsed = _date_from_text(context)
                if parsed:
                    return parsed.isoformat()
        if diagnostics is not None:
            # Başarısız ayrıştırmada gerçek HTML yapısını teşhis et; sayfanın
            # tamamını loglamadan başlıkları ve tarih içeren küçük DOM parçalarını kaydet.
            headings = [
                {"tag": node.name, "text": _clean(node.get_text(" ", strip=True))[:100]}
                for node in soup.find_all(["h1", "h2", "h3"])[:8]
            ]
            date_pattern = re.compile(
                r"(?<!\d)(?:\d{1,2}[./-]\d{1,2}[./-]\d{4}|"
                r"\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|"
                r"Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4})(?!\d)",
                re.IGNORECASE,
            )
            date_nodes = []
            for node in soup.find_all(True):
                node_text = _clean(node.get_text(" ", strip=True))
                matches = date_pattern.findall(node_text)
                if not matches:
                    continue
                # Üst kapsayıcıların tekrar eden metnini azalt: yaprak/alt öğe
                # veya tarih sınıfı taşıyan öğeler daha ayırt edicidir.
                child_has_date = any(
                    date_pattern.search(_clean(child.get_text(" ", strip=True)))
                    for child in node.find_all(True, recursive=False)
                )
                classes = node.get("class", [])
                class_text = " ".join(classes) if isinstance(classes, list) else str(classes)
                if child_has_date and not re.search(r"date|time|publish|article|author|meta", class_text + " " + str(node.get("id", "")), re.I):
                    continue
                ancestors = []
                parent = node
                for _ in range(3):
                    parent = parent.parent
                    if parent is None or not getattr(parent, "name", None):
                        break
                    parent_classes = parent.get("class", [])
                    if isinstance(parent_classes, list):
                        parent_classes = " ".join(parent_classes)
                    ancestors.append({
                        "tag": parent.name,
                        "class": str(parent_classes)[:80],
                        "id": str(parent.get("id", ""))[:60],
                        "contains_heading": bool(
                            headings and any(
                                heading["text"] and heading["text"] in _clean(parent.get_text(" ", strip=True))
                                for heading in headings[:3]
                            )
                        ),
                    })
                date_nodes.append({
                    "tag": node.name,
                    "class": str(class_text)[:80],
                    "id": str(node.get("id", ""))[:60],
                    "dates": matches[:3],
                    "text": node_text[:140],
                    "ancestors": ancestors,
                })
                if len(date_nodes) >= 8:
                    break
            diagnostic_detail = {
                "h1_found": soup.find("h1") is not None,
                "headings": headings,
                "date_nodes": date_nodes,
                "main_found": soup.find("main") is not None,
                "article_found": soup.find("article") is not None,
            }
            diagnostics.append(
                f"HTTP {response.status_code}; bytes={len(response.content)}; "
                f"DOM tanısı={json.dumps(diagnostic_detail, ensure_ascii=False, separators=(',', ':'))}"
            )
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        print("Haber tarihi okunamadı:", url, reason)
        if diagnostics is not None:
            diagnostics.append(reason)
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


# Türkçe haber sayfalarında görülen tarih biçimleri (sayısal ve ay adlı).
_TR_DATE_TOKEN = (
    r"(?:\d{1,2}[./-]\d{1,2}[./-]\d{4}"
    r"|\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4})"
)
# Yalnızca baştan sona tarihten (isteğe bağlı saatle) oluşan metinler.
_DATE_ONLY_RE = re.compile(
    r"^\s*" + _TR_DATE_TOKEN + r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\s*$",
    re.IGNORECASE,
)
# Haber gövdesindeki (ör. haberde anılan geçmiş olay) tarihlerin yayın tarihi
# sanılmaması için gövde metni kaplarını dışla.
_BODY_CONTAINER_SELECTORS = (
    ".contentBodyDiv", ".article-body", ".news-detail-body", ".body-text", ".haber-metni",
)


def _unique_date_in_text(text):
    """Metinde tek bir belirgin tarih varsa onu döndür; aksi halde None."""
    matches = {match.strip() for match in re.findall(_TR_DATE_TOKEN, text, re.IGNORECASE)}
    if len(matches) == 1:
        return _date_from_text(next(iter(matches)))
    return None


def _aa_byline_published_at(soup):
    """AA haber sayfalarında yayın tarihini h1/main olmadan oku.

    AA makalelerinde başlık h1 değil (spot h3, alt başlık h2), tarih ise
    yazar-tarih bloğunda (div.news-writeby) veya onu saran div.news-maindiv
    içinde düz metin olarak bulunur. Yalnızca tek bir belirgin tarih varsa
    kabul et; gövde metnindeki tarihleri ele ve güvenilir tarih yoksa None
    döndürerek uydurma tarih üretme.
    """
    body_containers = soup.select(", ".join(_BODY_CONTAINER_SELECTORS))

    def in_body(node):
        return any(
            node is container or container in node.parents
            for container in body_containers
        )

    for selector in ("[class*='writeby']", "[class*='news-maindiv']"):
        for container in soup.select(selector):
            # Yazar-tarih şeridi kısa olduğundan tek bir tarih içeriyorsa doğrudan kullan.
            if selector == "[class*='writeby']":
                parsed = _unique_date_in_text(_clean(container.get_text(" ", strip=True)))
                if parsed:
                    return parsed
            # Yalnızca tamamen tarihten oluşan ve haber gövdesinin dışındaki öğeler.
            candidates = set()
            for node in container.find_all(True):
                if in_body(node):
                    continue
                text = _clean(node.get_text(" ", strip=True))                if not text or len(text) > 32 or not _DATE_ONLY_RE.match(text):
                    continue
                parsed = _date_from_text(text)
                if parsed:
                    candidates.add(parsed)
            if len(candidates) == 1:
                return next(iter(candidates))
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
    missing_date_items = []
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
            detail_diagnostic = []
            published_at = _article_published_at(href, diagnostics=detail_diagnostic)
            if not published_at:
                missing_date_items.append({
                    "title": title[:300], "url": href,
                    "reason": detail_diagnostic[-1] if detail_diagnostic else "Yayın tarihi bulunamadı; neden ayrıntısı yok."
                })
                continue
            detail_successes += 1
        items.append({
            "source": source["name"], "title": title[:300], "url": href,
            "description": title, "published_at": published_at
        })
    diagnostic = {
        "stage": "html_list", "anchors": links_seen,
        "path_matches": path_matches, "dated_from_title": dated_from_title,
        "dated_from_context": dated_from_context, "detail_attempts": detail_attempts,
        "detail_successes": detail_successes, "parsed_items": len(items),
        "missing_date_items": missing_date_items,
        "errors": [],
    }
    if links_seen == 0:
        diagnostic["errors"].append("Sayfada bağlantı bulunamadı; beklenen HTML yapısı değişmiş olabilir.")
    elif include and path_matches == 0:
        diagnostic["errors"].append(
            f"Beklenen haber bağlantısı yolu bulunamadı: include_path={include!r}"
        )
    if detail_attempts > detail_successes:
        diagnostic["errors"].append(
            f"{detail_attempts - detail_successes} detay sayfasından yayın tarihi okunamadı."
        )
    _SOURCE_DIAGNOSTICS[source["name"]] = diagnostic
    print(
        "Haber kaynağı sonuç:",
        {"source": source["name"], "stage": "html_list", "anchors": links_seen,
         "path_matches": path_matches, "dated_from_title": dated_from_title,
         "dated_from_context": dated_from_context, "detail_attempts": detail_attempts,
         "detail_successes": detail_successes, "parsed_items": len(items),
         "missing_date_items": missing_date_items,
         "errors": diagnostic["errors"]}
    )
    if diagnostic["errors"] and (links_seen == 0 or (include and path_matches == 0)):
        raise RuntimeError("; ".join(diagnostic["errors"]))
    return items


def _tbb_mevzuat_items(source):
    response = _SESSION.get(source["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    keywords = [str(k).lower() for k in source.get("keywords", [])]
    items = []
    seen = set()
    article_links = 0
    detail_attempts = 0
    detail_errors = []
    missing_dates = []

    for a in soup.find_all("a", href=True):
        href = urljoin(source["url"], a.get("href", ""))
        title = _clean(a.get_text(" ", strip=True))
        if not title or len(title) < 12 or href in seen:
            continue
        if not href.startswith("https://www.tbb.gov.tr/tr/mevzuat-duyurulari/"):
            continue
        if href.rstrip("/") == source["url"].rstrip("/"):
            continue
        article_links += 1
        if not any(k in title.lower() for k in keywords):
            continue

        seen.add(href)
        description = title
        published_at = None
        detail_attempts += 1
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
            error = f"Detay sayfası okunamadı ({href}): {type(exc).__name__}: {str(exc)[:250]}"
            detail_errors.append(error)
            print("TBB mevzuat duyurusu okunamadı:", href, repr(exc))

        if not published_at:
            if not any(error.startswith(f"Detay sayfası okunamadı ({href})") for error in detail_errors):
                missing_dates.append(f"Yayın tarihi çözümlenemedi: {href}")
            continue

        items.append({
            "source": source["name"],
            "title": title[:300],
            "url": href,
            "description": description[:900],
            "published_at": published_at,
        })

    errors = []
    if len(soup.find_all("a", href=True)) == 0:
        errors.append("Sayfada bağlantı bulunamadı; beklenen HTML yapısı değişmiş olabilir.")
    elif article_links == 0:
        errors.append("TBB mevzuat duyurusu bağlantıları bulunamadı; sayfa yapısı değişmiş olabilir.")
    errors.extend(detail_errors)
    errors.extend(missing_dates)
    _SOURCE_DIAGNOSTICS[source["name"]] = {
        "stage": "tbb_mevzuat", "anchors": len(soup.find_all("a", href=True)),
        "article_links": article_links, "keyword_matches": len(seen),
        "detail_attempts": detail_attempts, "detail_errors": len(detail_errors),
        "missing_dates": len(missing_dates), "parsed_items": len(items),
        "errors": errors[:30],
    }
    if errors and (not article_links or detail_errors or missing_dates):
        # Partial results remain usable; update_news records the diagnostic as a source error.
        print("TBB kaynak tanılama hataları:", source["name"], errors[:10])
    return items


def _gib_datetime(value):
    """GİB zaman damgalarını UTC ISO biçimine çevir.

    Duyuru tarihleri Türkiye saatine göre ve saat dilimi bilgisi olmadan gelir
    (ör. 2026-10-11T10:35:00). Bu değerleri UTC+3 kabul et; aksi halde tarih
    gelecekte görünür ve 7 günlük filtre duyuruyu atlar.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=3)))
    return parsed.astimezone(timezone.utc).isoformat()


def _gib_api_items(source):
    """GİB Duyuru Arşivi'ni JSON API'sinden oku.

    Duyuru listesi sayfada istemci tarafında oluşturulduğu için liste HTML'inde
    duyuru bulunmaz; veri sayfanın kullandığı listPublish uç noktasından alınır.
    Duyuru gövdesi yanıttaki "description" alanındadır, detay sayfası kazınmaz.
    Yalnızca engellilik ve ÖTV ile ilgili duyurular kaynakta süzülür.

    Raporlama: alınan, anahtar kelime nedeniyle elenen, tarihi okunamayan,
    daha önce işlenmiş ve 7 günlük pencereye giren kayıt sayıları; elenen
    duyuruların başlığı ve elenme nedeni stdout'a yazılır (Cloud Run logları).
    news.json burada yalnızca okunur; fonksiyon hiçbir dosyaya yazmaz.
    """
    keywords = [str(k).casefold() for k in source.get("keywords", [])]
    detail_base = str(source.get("detail_url", "")).rstrip("/")
    file_base = str(source.get("file_url", ""))
    size = int(source.get("size", 10))
    items = []
    seen = set()
    scanned = 0
    invalid_rows = 0
    duplicate_in_scan = 0
    keyword_eliminated = 0
    invalid_date = 0
    eliminated = []
    source_error = None

    # Raporlama için: aynı duyuru daha önce yayımlanmış ya da işlenmiş mi?
    # update_news() ile aynı anahtarlar kullanılır (id = url özeti, seen_urls).
    previous = _load_json(NEWS_FILE, {})
    if not isinstance(previous, dict):
        previous = {}
    raw_items = previous.get("items", [])
    known_ids = {entry.get("id") for entry in raw_items if isinstance(entry, dict)}
    seen_before = previous.get("seen_urls", {})
    if not isinstance(seen_before, dict):
        seen_before = {}
    window_start = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    already_processed = 0
    in_window = 0
    new_candidates = 0

    for page in range(int(source.get("pages", 1))):
        params = {
            "preview": "false",
            "page": page,
            "size": size,
            "sortFieldName": "startdate",
            "sortType": "DESC",
        }
        started = time.monotonic()
        try:
            response = _SESSION.post(
                source["url"], json=source.get("body", {}), params=params,
                headers={"Content-Type": "application/json"}, timeout=TIMEOUT,
            )
        except Exception as exc:
            # Zaman aşımı/bağlantı hatası: yanıt gelmediği için durum kodu yok.
            print(
                "GİB duyuru API'si okunamadı:",
                {"source": source["name"], "stage": "gib_api", "page": page,
                 "http_status": None, "error": exc.__class__.__name__,
                 "timeout": isinstance(exc, requests.exceptions.Timeout),
                 "timeout_s": TIMEOUT, "detail": str(exc)[:300]}
            )
            source_error = f"page {page}: {exc.__class__.__name__}: {str(exc)[:300]}"
            break
        elapsed_ms = round((time.monotonic() - started) * 1000)
        print(
            "Haber kaynağı HTTP:",
            {"source": source["name"], "stage": "gib_api", "page": page,
             "status": response.status_code,
             "content_type": response.headers.get("Content-Type", ""),
             "bytes": len(response.content), "elapsed_ms": elapsed_ms}
        )
        if response.status_code != 200:
            print(
                "GİB duyuru API'si hata döndü:",
                {"source": source["name"], "stage": "gib_api", "page": page,
                 "http_status": response.status_code, "timeout_s": TIMEOUT,
                 "detail": response.text[:300]}
            )
            source_error = f"page {page}: HTTP {response.status_code}: {response.text[:300]}"
            break
        try:
            payload = response.json()
        except Exception as exc:
            source_error = f"page {page}: JSON parse {exc.__class__.__name__}: {str(exc)[:300]}"
            print("GİB duyuru yanıtı ayrıştırılamadı:", page, repr(exc))
            break
        if not isinstance(payload, dict) or not isinstance(payload.get("resultContainer"), dict):
            source_error = f"page {page}: beklenmeyen JSON yanıt yapısı"
            print("GİB duyuru yanıt yapısı beklenenden farklı:", page)
            break
        rows = payload["resultContainer"].get("content") or []
        if not isinstance(rows, list):
            source_error = f"page {page}: resultContainer.content liste değil"
            print("GİB duyuru kayıt listesi beklenenden farklı:", page)
            break
        if not rows:
            break
        scanned += len(rows)

        for row in rows:
            title = _clean(row.get("title"))
            slug = str(row.get("slug") or "").strip()
            if not title or not slug:
                invalid_rows += 1
                continue
            url = f"{detail_base}/{slug}"
            if url in seen:
                duplicate_in_scan += 1
                continue

            description = _clean(row.get("description"))
            searchable = f"{title} {description}".casefold()
            if keywords and not any(keyword in searchable for keyword in keywords):
                keyword_eliminated += 1
                eliminated.append({"title": title[:120],
                                   "reason": "anahtar kelime eşleşmedi"})
                continue
            published_at = _gib_datetime(row.get("startdate") or row.get("ts"))
            if not published_at:
                invalid_date += 1
                eliminated.append({"title": title[:120],
                                   "reason": "yayın tarihi okunamadı"})
                continue

            # Ek dosyalar (ör. PDF) duyuru metninde bağlantı olarak verilir;
            # adresleri gövdeye ekle ki özet üretilirken kaybolmasın.
            content = description
            attachments = [
                f"{file_base}{name}" for name in row.get("fileNames") or []
                if name and file_base
            ]
            if attachments:
                content = f"{description}\n\nEk dosyalar:\n" + "\n".join(attachments)

            seen.add(url)
            parsed_published = _date(published_at)
            is_known = _id({"url": url}) in known_ids or url in seen_before
            if is_known:
                already_processed += 1
            if parsed_published and parsed_published >= window_start:
                in_window += 1
                if not is_known:
                    new_candidates += 1
            items.append({
                "source": source["name"],
                "title": title[:300],
                "url": url,
                "description": description[:900],
                "content": content[:18000],
                "published_at": published_at,
            })

    diagnostic = {
        "stage": "gib_api", "scanned": scanned, "parsed_items": len(items),
        "keyword_eliminated": keyword_eliminated, "invalid_date": invalid_date,
        "invalid_rows": invalid_rows, "duplicate_in_scan": duplicate_in_scan,
        "already_processed": already_processed, "in_7_day_window": in_window,
        "new_candidates_for_gemini": new_candidates,
        "lookback_hours": LOOKBACK_HOURS, "error": source_error,
        "eliminated_examples": eliminated[:10],
    }
    _GIB_SOURCE_DIAGNOSTICS[source["name"]] = diagnostic
    if eliminated:
        print(
            "GİB duyuru eleme ayrıntısı:",
            {"source": source["name"], "stage": "gib_api",
             "count": len(eliminated), "items": eliminated[:10],
             "truncated": len(eliminated) > 10}
        )
    print(
        "Haber kaynağı sonuç:",
        {"source": source["name"], "stage": "gib_api", "scanned": scanned,
         "parsed_items": len(items), "keyword_eliminated": keyword_eliminated,
         "invalid_date": invalid_date, "invalid_rows": invalid_rows,
         "duplicate_in_scan": duplicate_in_scan,
         "already_processed": already_processed, "in_7_day_window": in_window,
         "new_candidates_for_gemini": new_candidates,
         "lookback_hours": LOOKBACK_HOURS, "error": source_error}
    )
    return items


def _source_items(source):
    if source.get("kind") == "tbb_mevzuat":
        return _tbb_mevzuat_items(source)
    if source.get("kind") == "gib_api":
        return _gib_api_items(source)
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
                    "duplicate_label": {"type": "STRING"},
                    "reject_reason": {"type": "STRING"},
                    "reject_label": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "summary": {"type": "STRING"},
                    "detail_summary": {"type": "STRING"},
                },
                "required": ["publish", "duplicate", "duplicate_reason", "duplicate_label", "reject_reason", "reject_label", "title", "summary", "detail_summary"],
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
    _GIB_SOURCE_DIAGNOSTICS.clear()
    _SOURCE_DIAGNOSTICS.clear()
    now = datetime.now(timezone.utc)
    sources = _load_json(SOURCES_FILE, [])
    old = _load_json(NEWS_FILE, {"updated_at": None, "items": [], "pending": []})
    existing_items = old.get("items", [])
    pending = old.get("pending", [])
    known = {item.get("id") for item in existing_items}
    candidates = []
    candidate_ids = set()
    # Filtre kararlarını değiştirmeden, neden sayılarını raporla.
    # Örnek başlıkları yalnızca sıfır aday durumunda ekleyerek raporu küçük tut.
    filter_counts = {
        "pending_unknown_or_expired_date": 0,
        "already_published": 0,
        "duplicate_in_this_run": 0,
        "url_seen_within_7_days": 0,
        "missing_date": 0,
        "future_date": 0,
        "older_than_7_days": 0,
        "accepted_as_candidate": 0,
    }
    filter_examples = {}
    def note_filter(reason, item):
        filter_counts[reason] += 1
        examples = filter_examples.setdefault(reason, [])
        if len(examples) < 2:
            examples.append({
                "source": str(item.get("source") or "")[:120],
                "title": str(item.get("title") or "")[:200],
            })
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
        if not item.get("id") or item["id"] in known:
            note_filter("already_published", item)
            continue
        published = _date(item.get("published_at"))
        if not published:
            note_filter("pending_unknown_or_expired_date", item)
        elif published > now:
            note_filter("future_date", item)
        elif published < cutoff:
            note_filter("older_than_7_days", item)
        else:
            candidates.append(item)
            candidate_ids.add(item["id"])
            filter_counts["accepted_as_candidate"] += 1

    source_counts = {}
    source_errors = []
    parsed_total = 0
    for source in sources:
        try:
            source_items = _source_items(source)
            source_counts[source["name"]] = len(source_items)
            parsed_total += len(source_items)
            for item in source_items:
                item["id"] = _id(item)
                if item["id"] in known:
                    note_filter("already_published", item)
                    continue
                if item["id"] in candidate_ids:
                    note_filter("duplicate_in_this_run", item)
                    continue
                if item.get("url") in seen_urls:
                    note_filter("url_seen_within_7_days", item)
                    continue
                published = _date(item.get("published_at"))
                if not published:
                    note_filter("missing_date", item)
                    continue
                if published > now:
                    note_filter("future_date", item)
                    continue
                if published < cutoff:
                    note_filter("older_than_7_days", item)
                    continue
                candidates.append(item)
                candidate_ids.add(item["id"])
                filter_counts["accepted_as_candidate"] += 1

        except Exception as exc:
            error_text = repr(exc)
            print("Kaynak okunamadı:", source["name"], error_text)
            source_errors.append({
                "source": source["name"],
                "error": error_text,
                "kind": "source_fetch_error",
            })

    # HTML/TBB sayfaları HTTP 200 dönse bile beklenen yapı veya tarih alanları
    # kaybolmuş olabilir. Tanılama bulgularını açık kaynak hatalarına dönüştür.
    for source_name, diagnostic in _SOURCE_DIAGNOSTICS.items():
        errors = diagnostic.get("errors") or []
        if not errors:
            continue
        matching_error = next(
            (entry for entry in source_errors if entry.get("source") == source_name),
            None,
        )
        diagnostic_text = "; ".join(str(error) for error in errors[:8])
        if matching_error:
            matching_error["kind"] = "source_parse_error"
            if diagnostic_text not in matching_error.get("error", ""):
                matching_error["error"] = (
                    str(matching_error.get("error") or "") + "; " + diagnostic_text
                ).strip("; ")
        else:
            source_errors.append({
                "source": source_name,
                "error": diagnostic_text,
                "kind": "source_parse_error",
            })

    # GİB API hataları fonksiyon içinde kısmi sonuçları korumak için yakalanır;
    # bunları mevcut kaynak hata raporuna da ekle ki sessizce sıfır kayıt görünmesin.
    for source_name, diagnostic in _GIB_SOURCE_DIAGNOSTICS.items():
        if diagnostic.get("error") and not any(
            entry.get("source") == source_name for entry in source_errors
        ):
            source_errors.append({
                "source": source_name,
                "error": diagnostic["error"],
                "kind": "source_fetch_error",
            })
    print("Kaynak kayıtları:", source_counts)
    print("Kaynak hataları:", source_errors)
    print("Filtre nedenleri:", filter_counts)
    print("AI adayları:", len(candidates))
    added = []
    failed = []
    ai_log = {
        "run_at": now.isoformat(),
        "model": GEMINI_MODEL,
        "source_errors": source_errors,
        "source_diagnostics": {
            **_SOURCE_DIAGNOSTICS,
            **_GIB_SOURCE_DIAGNOSTICS,
        },
        "filter_diagnostics": {
            "parsed_total": parsed_total,
            "counts": filter_counts,
            "examples": filter_examples if not candidates else {},
            "zero_candidates_is_not_an_error": True,
        },
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
                        official_url = href                        break
                if not official_url:
                    raise RuntimeError("TBB duyurusunda Resmî Gazete bağlantısı bulunamadı")
                article = _article_text(official_url)
            else:
                # İstemci tarafında oluşturulan duyuru sayfalarında gövde kaynakta
                # hazır gelir; detay sayfasını kazımaya gerek yok.
                article = item.get("content") or _article_text(item["url"])
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

RET GEREKÇESİ: duplicate=false ve publish=false olduğunda reject_reason alanına neden uygun olmadığını açıklayan tek kısa Türkçe cümle yaz. reject_label alanına aynı nedenin açık ve özgül 1-2 kelimelik özetini yaz. Etiket haber başlığının kısaltması değil, ret nedeninin bağlama uygun özeti olmalı. Haber metninden bir ifade doğrudan alınıyorsa, bu ifade ret nedenini bağlam içinde doğru ve anlaşılır biçimde anlatıyorsa kullanılabilir; yalnızca kelimeyi kopyalayıp anlamı belirsizleştirme. "Destek yok" ifadesini otomatik olarak yasaklama veya kullanma; haberin gerçek bağlamına göre karar ver. Kaynağa göre uygun örnekler: "Engellilikle ilgisiz", "Genel sağlık", "Genel siyaset", "Kapsam dışı". En uygun etiketi haberin gerçek nedenine göre seç; örnekleri otomatik kullanma. Uygun haberlerde veya mükerrer haberlerde iki alanı da boş bırak. Gerekçeyi yalnızca kaynak metnine dayanarak yaz; tahmin yürütme.

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
duplicate_reason alanında mükerrerliği somut olay veya dönem üzerinden tek kısa Türkçe cümleyle açıkla.
duplicate_label alanına aynı gerekçenin raporda gösterilecek 1-2 kelimelik, açık ve özgül özetini yaz. Başlığı kısaltma; mükerrerliğin nedenini belirt. Uygun örnekler: "Aynı duyuru", "Aynı ödeme", "Aynı karar". Mükerrer değilse iki alanı da boş bırak.
Sadece "aynı konu", "benzer haber" veya "aynı alan" gibi genel gerekçeler duplicate için yeterli değildir.

KANIT EŞİĞİ:
- Mevcut haber listesinde her haberin başlığını, kaynağını, tarihini ve URL'sini dikkate al. URL ve tarih tek başına karar verdirmez; somut olayın aynı olup olmadığını anlamaya yardımcı olur.
- Yeni adayın kaynak metnini, mevcut haberin özetinde anlatılan somut olayla karşılaştır. Mevcut haberin özeti yeni adayın ayrıntılarını doğrulamaya yetmiyorsa, aynı olay olduğunu varsayma.
- Aynı kurumun aynı konu başlığında yayımladığı farklı tarihli veya farklı numaralı duyurular otomatik olarak mükerrer değildir. Yeni duyuru yeni karar, liste sürümü, değişiklik, yürürlük tarihi, tutar, dönem veya başka yeni bilgi içeriyorsa duplicate=false ver.
- Resmî duyurularda duyuru/karar numarası ve ek dosya adı farklıysa bunları ayrı yayınlar olarak değerlendir; eklerin içeriği karşılaştırılmadan aynı içerik olduklarını varsayma.
- İki duyurunun ekleri veya tam metinleri elinde yoksa ve aynı somut gelişmeyi anlattıkları kanıtlanamıyorsa duplicate=true verme; duplicate=false ver, çünkü yalnızca konu benzerliği mükerrerlik kanıtı değildir.
- duplicate=true için mevcut haberle ortak olan somut olayı açıkça belirt. Yalnızca aynı kurum, konu veya anahtar kelimeleri sayma.

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
                f"- Başlık: {n.get('title', '')}\n"
                f"  Kaynak: {n.get('source', '')}\n"
                f"  Yayın tarihi: {n.get('published_at') or n.get('date') or 'bilinmiyor'}\n"
                f"  URL: {n.get('url', '')}\n"
                f"  Özet: {n.get('summary', '')}"
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
            # duplicate=true için gerekçe zorunlu: duplicate_reason boş veya yalnızca
            # boşluk ise kanıt yoktur, haber mükerrer sayılmaz; publish/reject kararı
            # normal akışa bırakılır.
            if result.get("duplicate") and not _clean(result.get("duplicate_reason")):
                result["duplicate"] = False
            ai_entry["status"] = "gemini_decision"
            ai_entry["publish"] = bool(result.get("publish"))
            ai_entry["duplicate"] = bool(result.get("duplicate"))
            ai_entry["duplicate_reason"] = _clean(result.get("duplicate_reason"))[:180] if result.get("duplicate") else ""
            ai_entry["duplicate_label"] = " ".join(_clean(result.get("duplicate_label")).split()[:2]) if result.get("duplicate") else ""
            ai_entry["reject_reason"] = _clean(result.get("reject_reason"))[:180] if not result.get("publish") and not result.get("duplicate") else ""
            ai_entry["reject_label"] = " ".join(_clean(result.get("reject_label")).split()[:2]) if not result.get("publish") and not result.get("duplicate") else ""
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
    # Central report writer merges by latest GitHub SHA, so concurrent workflow writes
    # cannot overwrite one another. News history remains limited to the latest 31 runs.
    try:
        previous_ai_logs = append_news_run(ai_log)
        print("Merkezi Gemini/sistem raporu güncellendi.")
    except Exception as exc:
        previous_ai_logs = _load_json(AI_LOG_FILE, [])
        if isinstance(previous_ai_logs, dict):
            previous_ai_logs = previous_ai_logs.get("news_runs", [])
        if not isinstance(previous_ai_logs, list):
            previous_ai_logs = []
        previous_ai_logs = (previous_ai_logs + [ai_log])[-31:]
        print("Merkezi rapor yazılamadı; haber güncellemesi durdurulmadı:", repr(exc))
    _update_source_alert(previous_ai_logs)
    _save_json(NEWS_FILE, result)
    print(f"Yeni haber: {len(added)} | Toplam: {len(result['items'])} | Bekleyen: {len(result['pending'])}")
    return result


if __name__ == "__main__":
    update_news()