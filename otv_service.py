import json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

LIMIT_2026 = 2_873_900
CACHE_FILE = "otv_cache.json"
TZ = ZoneInfo("Europe/Istanbul")

SEEDS = [
    {"brand":"Renault","model":"Yeni Clio","trim":"Başlangıç","fuel":"Benzin","price":1830000,"otv_rate":80,"source_name":"Renault Türkiye","source_url":"https://www.renault.com.tr/hybrid-araclar/yeni-clio.html"},
    {"brand":"Renault","model":"Duster","trim":"Başlangıç","fuel":"Benzin/Hybrid/LPG","price":1865000,"otv_rate":80,"source_name":"Renault Türkiye","source_url":"https://www.renault.com.tr/hybrid-araclar/yeni-renault-duster.html"},
    {"brand":"Renault","model":"Boreal","trim":"Başlangıç","fuel":"Benzin/Hybrid","price":2269000,"otv_rate":80,"source_name":"Renault Türkiye","source_url":"https://www.renault.com.tr/hybrid-araclar/boreal.html"},
    {"brand":"Renault","model":"Megane Sedan","trim":"Başlangıç","fuel":"Benzin","price":2199000,"otv_rate":80,"source_name":"Renault Türkiye","source_url":"https://www.renault.com.tr/binek-araclar/megane-sedan.html"},
    {"brand":"Fiat","model":"Egea","trim":"Dizel başlangıç","fuel":"Dizel","price":1384900,"otv_rate":80,"source_name":"Fiat Türkiye","source_url":"https://www.fiat.com.tr/kampanyalar"},
    {"brand":"Toyota","model":"Corolla","trim":"Sedan başlangıç","fuel":"Benzin/Hybrid","price":1850000,"otv_rate":80,"source_name":"Toyota Türkiye","source_url":"https://www.toyota.com.tr/araba-modelleri/corolla-sedan"},
    {"brand":"Toyota","model":"C-HR","trim":"Hybrid Flame","fuel":"Hybrid","price":2325000,"otv_rate":80,"source_name":"Toyota Türkiye","source_url":"https://www.toyota.com.tr/araba-modelleri/c-hr"},
    {"brand":"Hyundai","model":"i20","trim":"Başlangıç","fuel":"Benzin","price":1555000,"otv_rate":80,"source_name":"Hyundai Türkiye","source_url":"https://www.hyundai.com/tr/tr/modeller/i20.html"},
    {"brand":"Hyundai","model":"BAYON","trim":"Başlangıç","fuel":"Benzin","price":1625000,"otv_rate":80,"source_name":"Hyundai Türkiye","source_url":"https://www.hyundai.com/tr/tr/modeller/bayon.html"},
    {"brand":"Togg","model":"T10X","trim":"V1 RWD Standart Menzil","fuel":"Elektrik","price":1909048,"otv_rate":25,"source_name":"Togg","source_url":"https://togg.com.tr/price-list","fixed_trim_price":True},
    {"brand":"Togg","model":"T10X","trim":"V1 RWD Uzun Menzil","fuel":"Elektrik","price":2219668,"otv_rate":25,"source_name":"Togg","source_url":"https://togg.com.tr/price-list","fixed_trim_price":True},
    {"brand":"Togg","model":"T10X","trim":"V2 RWD Uzun Menzil","fuel":"Elektrik","price":2411000,"otv_rate":25,"source_name":"Togg","source_url":"https://togg.com.tr/price-list","fixed_trim_price":True},
    {"brand":"Togg","model":"T10F","trim":"V1 RWD Standart Menzil","fuel":"Elektrik","price":1884980,"otv_rate":25,"source_name":"Togg","source_url":"https://www.togg.com.tr/t10f-price-list","fixed_trim_price":True},
    {"brand":"Togg","model":"T10F","trim":"V1 RWD Uzun Menzil","fuel":"Elektrik","price":2195600,"otv_rate":25,"source_name":"Togg","source_url":"https://www.togg.com.tr/t10f-price-list","fixed_trim_price":True},
    {"brand":"Togg","model":"T10F","trim":"V2 RWD Uzun Menzil","fuel":"Elektrik","price":2370930,"otv_rate":25,"source_name":"Togg","source_url":"https://www.togg.com.tr/t10f-price-list","fixed_trim_price":True},
]

def exempt_price(price, rate):
    return round(price / (1 + rate/100))

def _stamp(rows):
    now=datetime.now(TZ)
    cleaned=[]
    for v in rows:
        v.pop("fixed_trim_price",None)
        v["exempt_price"]=exempt_price(v["price"],v["otv_rate"])
        v["checked_at"]=now.strftime("%H:%M")
        if v["price"]<=LIMIT_2026:
            cleaned.append(v)
    return {"limit":LIMIT_2026,"updated_at":now.strftime("%d.%m.%Y %H:%M"),"updated_time":now.strftime("%H:%M"),"vehicles":cleaned}

def _save(data):
    try:
        with open(CACHE_FILE,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False)
    except Exception: pass
    return data

def _load():
    try:
        with open(CACHE_FILE,encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def _text(url):
    r=requests.get(url,timeout=12,headers={"User-Agent":"Mozilla/5.0 RDV-Asistan/1.0"})
    r.raise_for_status()
    return BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True)

def _money(s): return int(re.sub(r"\D","",s))
def _nearest_price(text, model):
    patterns=[
        re.escape(model)+r".{0,260}?(?:başlangıç fiyatı|başlayan fiyatlarla|fiyat fırsatı ile|fiyatı)?\s*(?:₺|TL)?\s*([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})",
        r"(?:başlangıç fiyatı|başlayan fiyatlarla)\s*(?:₺|TL)?\s*([1-9]\d{0,2}(?:[.\s]\d{3}){1,2})",
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            return _money(m.group(1))
    return None

def refresh_otv_data(force=False):
    rows=[dict(v) for v in SEEDS]
    page_cache={}
    for v in rows:
        if v.get("fixed_trim_price"):
            continue
        url=v["source_url"]
        if url not in page_cache:
            try: page_cache[url]=_text(url)
            except Exception: page_cache[url]=""
        p=_nearest_price(page_cache[url],v["model"])
        if p and 700000<=p<=10_000_000:
            v["price"]=p
    return _save(_stamp(rows))

def get_otv_data():
    data=_load()
    if not data: return refresh_otv_data()
    try:
        dt=datetime.strptime(data["updated_at"],"%d.%m.%Y %H:%M").replace(tzinfo=TZ)
        if (datetime.now(TZ)-dt).total_seconds()>86400: return refresh_otv_data()
    except Exception: return refresh_otv_data()
    return data

if __name__=="__main__":
    print(json.dumps(refresh_otv_data(force=True),ensure_ascii=False,indent=2))
