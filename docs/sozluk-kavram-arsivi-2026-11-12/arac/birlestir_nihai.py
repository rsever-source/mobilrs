# -*- coding: utf-8 -*-
"""Nihai sozluk_kavram_data.json birlestiricisi.

Kaynaklar:
- arac/parca/u1_ek1_001_020.json (135) ve u2_ek1_021_040.json (141): EK-1 derece kayitlari
- arac/parca/u3b_ek2_003_024.json (142): EK-2 s.3-24
- arac/ek2_25_169_kayitlar.json + elle secim listesi: EK-2 s.25-169 terim kayitlari

Kurallar:
- Tanim/derece/etiket/oran/ICD uydurulmaz; yalnizca kaynakta olan aktarilir.
- Her kayit tek mevzuat baglantisi tasir (XOR) ve kaynak.sayfa_no zorunludur.
- EK-1 derecesiz kurallar bu dosyaya alinmaz (ayri tutulur).
"""
import json
import re
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
ARAC = KOK / "arac"
PARCALAR = ARAC / "parca"

ERISIM = "2026-11-12"
OLUSTURMA = "2026-11-12T00:00:00Z"

EK1_KAYNAK = {
    "belge_adi": "Maluliyet ve Çalışma Gücü Kaybı Tespiti İşlemleri Yönetmeliği EK-1 Hastalık Listesi",
    "rg_tarihi": "28.09.2021",
    "rg_sayisi": 31612,
    "url": "https://www.resmigazete.gov.tr/eskiler/2021/09/20210928-4.htm",
    "erisim_tarihi": ERISIM,
}
EK2_KAYNAK = {
    "belge_adi": "Erişkinler İçin Engellilik Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu (EK-2)",
    "rg_tarihi": "20.02.2019",
    "rg_sayisi": 30692,
    "mbs_no": 31275,
    "url": "https://www.resmigazete.gov.tr/eskiler/2019/02/20190220-2.htm",
    "erisim_tarihi": ERISIM,
}

# EK-2 s.25-169: elle denetlenen kayit secimi [(sayfa, etiket, ad_onu), ...]
EK2_SECIM = [
    ("ek2_025", "ı.", "ANEMİLER"),
    ("ek2_025", "A.", "Aplastik Anemi"),
    ("ek2_025", "B.", "Diamond Blacfan Anemisi"),
    ("ek2_025", "C.", "Hemolitik Anemiler"),
    ("ek2_025", "a.", "Eritrosit enzim defektleri"),
    ("ek2_025", "b.", "Paroksismal Nokturnal Hemoglobinüri"),
    ("ek2_025", "c.", "Oto-immün hemolitik anemiler"),
    ("ek2_025", "D.", "Hemoglobinopatiler"),
    ("ek2_025", "a.", "Orak hücreli anemi"),
    ("ek2_025", "b.", "Thalassemi"),
    ("ek2_026", "11.", "MİYELOFİBROZİS"),
    ("ek2_026", "A.", "Akut Lösemiler"),
    ("ek2_026", "B.", "Kronik Lösemiler"),
    ("ek2_026", "a.", "Kronik Myelositik Lösemi"),
    ("ek2_026", "b.", "Kronik Lenfositik Lösemi"),
    ("ek2_026", "c.", "Monoklonal Gammapatiler"),
    ("ek2_026", "C.", "Hemofagositik Sendrom"),
    ("ek2_026", "A.", "Hemorajik Diatezler"),
    ("ek2_027", "b.", "Koagülopatiler"),
    ("ek2_027", "c.", "Hipofibrinojenemi"),
    ("ek2_027", "B.", "Akkiz ve herediter trombotik durumlar"),
    ("ek2_027", "C.", "Trombotik Trombositopenik Purpura"),
    ("ek2_027", "D.", "Dissemine İntravasküler Koagülopati"),
    ("ek2_027", "a.", "Hodgkin Lenfoma"),
    ("ek2_027", "b.", "Non-Hodgkin Lenfoma"),
    ("ek2_032", "A.", "Kapak hastalıkları"),
    ("ek2_032", "B.", "Koroner arter hastalığı"),
    ("ek2_030", "3)", "Hipertansif retinopati"),
    ("ek2_067", "3.", "KOLON, REKTUM VE ANÜS"),
    ("ek2_069", "4.", "ENTEROKÜTAN FİSTÜLLER"),
    ("ek2_070", "5.", "KARACİĞER VE SAFRA YOLLARI"),
    ("ek2_071", "6.", "HERNİLER"),
    ("ek2_071", "7.", "SPLENEKTOMİ"),
    ("ek2_079", "I-", "Hipotalamik hastalıklar"),
    ("ek2_079", "II-", "Hipofizer hastalıklar"),
    ("ek2_079", "a)", "Hipofiz Bezinin Hiperfonksiyonu"),
    ("ek2_079", "I-", "Gigantizm ve Akromegali"),
    ("ek2_079", "b)", "Hipofiz Bezinin Hipofonksiyonu"),
    ("ek2_079", "III-", "Tiroid hastalıkları"),
    ("ek2_079", "a)", "Guatrlar"),
    ("ek2_079", "b)", "Kretinizm"),
    ("ek2_079", "c)", "Doğuştan iyot eksikliği sendromu"),
    ("ek2_079", "g)", "Tirotoksikoz"),
    ("ek2_079", "IV-", "Paratiroid Hastalıkları"),
    ("ek2_079", "b)", "Hipoparatiroidi"),
    ("ek2_079", "I-", "İdiopatik Primer Hipoparatiroidi (Replasmanla Kompanse)"),
    ("ek2_080", "V-", "Adrenal hastalıkları"),
    ("ek2_080", "a)", "İki taraflı hiperplazi"),
    ("ek2_080", "b)", "Adrenal korteks yetersizliği"),
    ("ek2_080", "c)", "Hiperaldosteronizm"),
    ("ek2_080", "d)", "Feokromasitomalar"),
    ("ek2_080", "e)", "Adrenogenital bozukluklar"),
    ("ek2_080", "a)", "Ergenlik bozuklukları"),
    ("ek2_080", "b)", "Çoğul bez"),
    ("ek2_080", "c)", "Timus hastalıkları"),
    ("ek2_080", "a)", "Diabetes mellitus"),
    ("ek2_081", "VIII-", "Metabolizma Hastalıkları"),
    ("ek2_081", "a)", "Difftiz primer osteoporoz"),
    ("ek2_081", "b)", "Osteomalazi"),
    ("ek2_081", "I-", "Lesch-Nyhan Hastalığı"),
    ("ek2_081", "I-", "Ciddi Obezite"),
    ("ek2_084", "a)", "Vücut yüzeyinin % 10'unu kaplayan"),
    ("ek2_084", "e)", "Yanık zemininde gelişen MarjoIİn ülseri"),
    ("ek2_088", "I.", "İnsomniler"),
    ("ek2_088", "2.", "Uykuda solunum bozuklukları"),
    ("ek2_088", "3.", "Hipersomniler"),
    ("ek2_089", "4.", "Sirkadiyen uyku-uyanıklık ritm bozuklukları"),
    ("ek2_089", "5.", "Parasomniler"),
    ("ek2_089", "6.", "Uykuda hareket bozuklukları"),
]

# OCR satir kaydirmasi nedeniyle kesilmis 8 kavram adi.
# Ad, kaynak sayfadaki satir(lar)in birebir devamidir; yalnizca satir sonu
# noktalamasi ve belirgin OCR harf hatalari (Difftiz->Diffüz, MarjoIİn->Marjolin,
# Konfijzyonel->Konfüzyonel, dekalsiflkasyon->dekalsifikasyon) duzeltilmistir.
# Ham OCR satiri kanit_izleri.json icinde "duzeltilmis" durumuyla saklanir.
EK2_AD_DUZELTME = [
    (
        "ek2_081",
        "Difftiz primer osteoporoz",
        "Diffüz primer osteoporoz (radyolojik dekalsifikasyonla birlikte spontan kırıklar, "
        "şekil bozuklukları yapan)",
    ),
    (
        "ek2_084",
        "Yanık zemininde gelişen MarjoIİn ülseri",
        "Yanık zemininde gelişen Marjolin ülseri ve skuamöz kanserler",
    ),
    (
        "ek2_088",
        "İnsomniler",
        "İnsomniler (Uyarlanmış insomni, psikofizyolojik insomni, paradoksal insomni, "
        "idiyopatik insomni, mental bozukluğa bağlı insomni, yetersiz uyku hijyenine bağlı "
        "insomni, çocukluk çağının davranışsal insomnisi)",
    ),
    (
        "ek2_088",
        "Uykuda solunum bozuklukları",
        "Uykuda solunum bozuklukları (Santral uyku apne sendromları, obstruktif uyku apne "
        "sendromları, uykuda hipoventilasyon ve hipoksemik sendromlar)",
    ),
    (
        "ek2_088",
        "Hipersomniler",
        "Hipersomniler (Narkolepsi sendromları, rekürren hipersomniler, idiyopatik hipersomniler)",
    ),
    (
        "ek2_089",
        "Sirkadiyen uyku-uyanıklık ritm bozuklukları",
        "Sirkadiyen uyku-uyanıklık ritm bozuklukları (Geçikmiş uyku fazı sendromu, erken uyku "
        "fazı sendromu, düzensiz uyku-uyanıklık ritmi, serbest ritm bozukluğu, jet-lag, "
        "vardiyalı çalışmaya bağlı ritm bozukluğu)",
    ),
    (
        "ek2_089",
        "Parasomniler",
        "Parasomniler (Konfüzyonel uyanma, uykuda yürüme, gece terörü, uyku paralizisi, kâbus "
        "bozukluğu, uykuda dissosiyatif bozukluk, enürezis, inleme, patlayan baş sendromu, "
        "hipnagojik veya hipnopompik hallüsinasyon, uykuda yeme-içme sendromu)",
    ),
    (
        "ek2_089",
        "Uykuda hareket bozuklukları",
        "Uykuda hareket bozuklukları (Huzursuz bacak sendromu, uykuda periyodik hareket "
        "bozukluğu, uyku ile ilişkili bacak krampları, bruksizm, uykuda ritmik hareket bozukluğu)",
    ),
]

TR = str.maketrans("çğıöşüâîûÇĞİÖŞÜI", "cgiosuaiuCGIOSUI")


def slug(metin, uzunluk=38):
    s = metin.translate(TR).lower()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:uzunluk].strip("_") or "kavram"


def sayfa_no(ad):
    return int(re.search(r"(\d{3})$", ad).group(1))


def benzersiz(temel, kullanilan):
    ad = temel[:79]
    if ad not in kullanilan:
        kullanilan.add(ad)
        return ad
    n = 2
    while True:
        ek = f"_{n}"
        aday = temel[: 79 - len(ek)] + ek
        if aday not in kullanilan:
            kullanilan.add(aday)
            return aday
        n += 1


def ek1_kayitlari():
    kayitlar = []
    gorulen = set()
    for ad in ("u1_ek1_001_020.json", "u2_ek1_021_040.json"):
        veri = json.loads((PARCALAR / ad).read_text(encoding="utf-8"))
        for k in veri["kayitlar"]:
            anahtar = (k["bolum_harfi"], k["sira_no"], k["derece"], k["kanonik_ad"])
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            kayitlar.append(k)
    return kayitlar


def norm(metin):
    """Karsilastirma icin Turkce/OCR varyantlarini esitler (yalniz karsilastirmada)."""
    s = metin.replace("İ", "I").replace("ı", "i").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def ek2_birlestir(kayitlar):
    """Ayni sayfada ayni ada sahip kayitlari tek kayda indirger.

    Kaynakta bir baslik hem baslik satiri hem alt aciklama satiri olarak iki kez
    goruntulenebiliyor (orn. EK-2 s.21 'VIII. ERİTRODERMA'). Bu durumda tek kayit
    tutulur; madde etiketi ve tanim alanlari bos olan taraftan tamamlanir.
    """
    sonuc = []
    indeks = {}
    for k in kayitlar:
        anahtar = (sayfa_no(k["sayfa"]), norm(k["kanonik_ad"]))
        if anahtar not in indeks:
            indeks[anahtar] = len(sonuc)
            sonuc.append(dict(k))
            continue
        mevcut = sonuc[indeks[anahtar]]
        if not mevcut.get("madde_etiketi") and k.get("madde_etiketi"):
            mevcut["madde_etiketi"] = k["madde_etiketi"]
        if not mevcut.get("tanim") and k.get("tanim"):
            mevcut["tanim"] = k["tanim"]
    return sonuc


def ek2_u3b():
    veri = json.loads((PARCALAR / "u3b_ek2_003_024.json").read_text(encoding="utf-8"))
    return veri["kayitlar"]


def ek2_ek_kayitlar():
    """EK-2 29-169 bos bolumleri icin elle derlenmis 259 kavram kaydi."""
    return json.loads((ARAC / "ek2_ek_kayitlar.json").read_text(encoding="utf-8"))


def ek2_secili():
    ham = json.loads((ARAC / "ek2_25_169_kayitlar.json").read_text(encoding="utf-8"))
    indeks = {}
    for h in ham:
        indeks.setdefault((h["sayfa"], h["madde_etiketi"]), []).append(h)
    secilen = []
    for sayfa, etiket, on in EK2_SECIM:
        adaylar = [h for h in indeks.get((sayfa, etiket), []) if h["kanonik_ad"].startswith(on)]
        if len(adaylar) != 1:
            raise SystemExit(f"SECIM HATASI: {sayfa} {etiket} {on} -> {len(adaylar)} aday")
        secilen.append(dict(adaylar[0]))

    for kayit in secilen:
        for sayfa, on, yeni in EK2_AD_DUZELTME:
            if kayit["sayfa"] == sayfa and kayit["kanonik_ad"].startswith(on):
                kayit["kanonik_ad"] = yeni
                kayit["duzeltilmis"] = True
                break
    return secilen


def main():
    kullanilan = set()
    cikti = []

    for k in ek1_kayitlari():
        bolum = k["bolum_harfi"].translate(TR).lower()
        temel = f"ek1_{bolum}_{k['sira_no']:02d}_{slug(k['kanonik_ad'])}_{k['derece']}"
        cikti.append(
            {
                "kavram_id": benzersiz(temel, kullanilan),
                "kanonik_ad": k["kanonik_ad"],
                "es_anlamli": [],
                "ek_1_baglantisi": {
                    "bolum_harfi": k["bolum_harfi"],
                    "sira_no": k["sira_no"],
                    "derece": k["derece"],
                },
                "kaynak": {**EK1_KAYNAK, "sayfa_no": sayfa_no(k["sayfa"])},
                "olusturulma_tarihi": OLUSTURMA,
            }
        )

    ek2_hepsi = ek2_birlestir(ek2_u3b() + ek2_secili() + ek2_ek_kayitlar())
    eslesme = []
    for k in ek2_hepsi:
        temel = f"ek2_s{sayfa_no(k['sayfa']):03d}_{slug(k['kanonik_ad'])}"
        baglanti = {"bolum_adi": k["bolum_adi"]}
        if k.get("alt_bolum"):
            baglanti["alt_bolum"] = k["alt_bolum"][:120]
        if k.get("madde_etiketi"):
            baglanti["madde_etiketi"] = str(k["madde_etiketi"])[:20]
        kimlik = benzersiz(temel, kullanilan)
        if k.get("ham_satir"):
            eslesme.append(
                {
                    "kavram_id": kimlik,
                    "ham_satir": k["ham_satir"],
                    "durum": "duzeltilmis" if k.get("duzeltilmis") or k.get("durum") == "duzeltilmis" else "birebir",
                }
            )
        cikti.append(
            {
                "kavram_id": kimlik,
                "kanonik_ad": k["kanonik_ad"].strip(),
                "es_anlamli": [],
                "ek_2_baglantisi": baglanti,
                "kaynak": {**EK2_KAYNAK, "sayfa_no": sayfa_no(k["sayfa"])},
                "olusturulma_tarihi": OLUSTURMA,
            }
        )

    (ARAC / "ek2_kaynak_eslesme.json").write_text(
        json.dumps(eslesme, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )

    hedef = KOK / "data" / "sozluk_kavram_data.json"
    hedef.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    ek1 = sum(1 for r in cikti if "ek_1_baglantisi" in r)
    ek2 = sum(1 for r in cikti if "ek_2_baglantisi" in r)
    print(f"toplam: {len(cikti)}  EK-1: {ek1}  EK-2: {ek2}")
    print(f"dosya: {hedef} ({hedef.stat().st_size} bayt)")


if __name__ == "__main__":
    main()
