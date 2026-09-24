import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

NEWS_FILE="news.json"
SOURCES_FILE="news_sources.json"
MAX_ITEMS=10
LOOKBACK_HOURS=72
OPENAI_MODEL=os.environ.get("OPENAI_MODEL","gpt-5.6-luna")
UA="EngelliMe-NewsBot/1.0 (+https://engelli.me)"
TIMEOUT=20
KEYWORDS=("engelli","engelliler","engelli birey","engelli vatandaş","engelli aylığı","evde bakım","erişilebilir","ekpss","özel eğitim","özel gereksinim","ötv","muafiyet","sosyal yardım","malulen emekl","çalışma gücü kaybı","bakım yardımı","ücretsiz seyahat","erişilebilirlik")

def _load_json(path,default):
    try:
        with open(path,encoding="utf-8") as f:return json.load(f)
    except Exception:return default

def _save_json(path,data):
    with open(path,"w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)

def _clean(text):
    text=unescape(str(text or ""))
    return re.sub(r"\s+"," ",BeautifulSoup(text,"html.parser").get_text(" ",strip=True)).strip()

def _date(value):
    if not value:return None
    try:return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        try:return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)
        except Exception:return None

def _feed_items(source):
    r=requests.get(source["url"],headers={"User-Agent":UA},timeout=TIMEOUT);r.raise_for_status()
    root=ET.fromstring(r.content);items=[]
    for node in root.findall(".//item"):
        title=_clean(node.findtext("title"));link=_clean(node.findtext("link"));description=_clean(node.findtext("description"))
        pub=_date(node.findtext("pubDate") or node.findtext("published"))
        if title and link:items.append({"source":source["name"],"title":title,"url":link,"description":description,"published_at":pub.isoformat() if pub else None})
    return items

def _relevant_candidate(item):
    text=f"{item['title']} {item['description']}".lower()
    return any(k in text for k in KEYWORDS)

def _article_text(url):
    r=requests.get(url,headers={"User-Agent":UA},timeout=TIMEOUT,allow_redirects=True);r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    for tag in soup(["script","style","noscript","svg","nav","footer"]):tag.decompose()
    return _clean(soup.get_text(" ",strip=True))[:18000]

def _openai(prompt):
    key=os.environ.get("OPENAI_API_KEY","").strip()
    if not key:raise RuntimeError("OPENAI_API_KEY ayarlanmamış")
    payload={"model":OPENAI_MODEL,"input":[{"role":"system","content":"Sen engelli.me için çalışan bir haber editörüsün. Yalnızca verilen kaynak metnindeki doğrulanabilir bilgileri kullan. Haber engelli bireyleri doğrudan ilgilendirmiyorsa yayınlama. Özgün, kısa ve tarafsız Türkçe özet hazırla. Kaynak metnini kopyalama. Yanıtı yalnızca geçerli JSON olarak döndür."},{"role":"user","content":prompt}],"text":{"format":{"type":"json_schema","name":"engelli_haber","strict":True,"schema":{"type":"object","properties":{"publish":{"type":"boolean"},"category":{"type":"string"},"title":{"type":"string"},"summary":{"type":"string"}},"required":["publish","category","title","summary"],"additionalProperties":False}}},"store":False}
    r=requests.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=payload,timeout=60);r.raise_for_status()
    data=r.json();chunks=[]
    for out in data.get("output",[]):
        for content in out.get("content",[]):
            if content.get("type") in ("output_text","text"):chunks.append(content.get("text",""))
    raw="".join(chunks).strip()
    if not raw:raise RuntimeError("OpenAI boş yanıt verdi")
    return json.loads(raw)

def _id(item):return hashlib.sha256(item["url"].encode("utf-8")).hexdigest()[:20]

def update_news():
    now=datetime.now(timezone.utc);sources=_load_json(SOURCES_FILE,[]);old=_load_json(NEWS_FILE,{"updated_at":None,"items":[]});known={x.get("id") for x in old.get("items",[])}
    candidates=[]
    for source in sources:
        try:
            for item in _feed_items(source):
                item["id"]=_id(item)
                if item["id"] in known:continue
                published=_date(item.get("published_at"))
                if published and published<now-timedelta(hours=LOOKBACK_HOURS):continue
                if _relevant_candidate(item):candidates.append(item)
        except Exception as exc:print("Kaynak okunamadı:",source["name"],repr(exc))
    added=[]
    for item in candidates[:12]:
        try:
            article=_article_text(item["url"])
            result=_openai(f"Kaynak: {item['source']}\nBaşlık: {item['title']}\nKaynak özeti: {item['description']}\nKaynak metni:\n{article}\n\nKurallar: Özet 3-5 kısa cümle olsun. Yeni bilgi, yorum veya tahmin ekleme. Başlık kısa olsun. Uygun değilse publish=false ver.")
            if not result.get("publish"):continue
            summary=_clean(result.get("summary"))
            if not summary:continue
            added.append({"id":item["id"],"title":_clean(result.get("title"))[:180],"summary":summary[:900],"category":_clean(result.get("category"))[:50] or "Gündem","source":item["source"],"url":item["url"],"published_at":item.get("published_at"),"created_at":now.isoformat()})
        except Exception as exc:print("Haber işlenemedi:",item["title"],repr(exc))
    merged=added+old.get("items",[]);merged.sort(key=lambda x:x.get("published_at") or x.get("created_at") or "",reverse=True)
    result={"updated_at":now.isoformat(),"items":merged[:MAX_ITEMS]};_save_json(NEWS_FILE,result)
    print(f"Yeni haber: {len(added)} | Toplam: {len(result['items'])}")
    return result

if __name__=="__main__":update_news()
