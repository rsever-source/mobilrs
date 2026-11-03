# -*- coding: utf-8 -*-
"""Araç-1 — Engel Oranı Bul ekranı için küçük, bağımsız sunucu (prototip).

Sözleşme: ``SOZLESME.md`` §3 (veri sözleşmesi) ve §4 (ekran sözleşmesi).

Tasarım kararları (sözleşmeye bağlı):

* Katalog **salt okunur** yüklenir (``katalog_okuyucu``); dosyalara yazılmaz,
  ``—``/belirsiz kayıt yorumlanmaz (§3.1, §3.4, §3.9, §3.10).
* Ekran **hesap yapmaz**: her oran motordan ``balthazard()`` +
  ``bicimle_gosterim()`` ile alınır; kopya formül yoktur (§3.14, §2.7).
* Tek tek katalog oranlarının gösteriminde yaş eki **uygulanmaz**. Balthazard
  ön izlemesi ise kullanıcının 65+ kutusuna göre ``yas`` ve ``yas_ekle``
  değerlerini motora iletir; gerçek hesaplama ortak motorda yapılır.
* **POST ucu yoktur**; Araç-1 yalnız okur. Aktarım listesi istemcide (tarayıcı
  oturumunda) tutulur; Araç-2'ye otomatik aktarım yapılmaz (S-1a).
* Yalnız ``127.0.0.1:8766`` üzerinde dinler; Araç-2 kendi portunda (8765)
  bağımsız kalır (S-2a).

Uçlar:

    GET /arac1                  ekran (HTML)
    GET /saglik                 sağlık kontrolü + katalog sayıları
    GET /api/bolumler           bölüm çipleri ve kapsam dışı notu
    GET /api/gezinme?bolum=…    grup → hastalık → seviye ağacı
    GET /api/ara?metin=&bolum=  arama (3 karakterden sonra)
    GET /api/kayit/<id>         sonuç; belirsiz kayıtta belirsiz ekranı
    GET /api/belirsiz/<id>      yalnız belirsiz ekranı
    POST /api/hesapla           seçilen oranların ortak Balthazard ön izlemesi (65+ seçimi desteklenir)

Çalıştırma:

    <python> arac1_sunucu.py            # http://127.0.0.1:8766
    <python> arac1_sunucu.py 9000       # başka port
"""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "arac2"))

from balthazard_motoru import YAS_ALTI, balthazard, bicimle_gosterim  # noqa: E402
from arac2_sunucu import gosterim_ekle  # noqa: E402
from katalog_okuyucu import (Katalog, KatalogHatasi, katla, kural_kapsamini_dogrula,
                             yukle, yukle_ek_katalog, yukle_kurallar,
                             yukle_ozel_hesaplamalar)  # noqa: E402

SAYFA = BURASI / "arac1.html"
VARSAYILAN_PORT = 8766
ARAC2_ADRESI = "http://127.0.0.1:8765/arac2"
AZAMI_SORGU = 120
EK_KATALOG_YOLU = KOK / "veri" / "katalog_ek2_ek.json"
OZEL_HESAPLAMA_YOLU = KOK / "veri" / "ozel_hesaplamalar.json"
KURAL_YOLU = KOK / "veri" / "kurallar_ek2.json"
_EK_KATALOG: dict | None = None
_OZEL_HESAPLAMALAR: dict | None = None
_KURALLAR: dict | None = None

# --- Sözleşme metinleri (§3.10, §3.12, §3.14, §3.16, §4.4, §4.10) -----------

ORAN_ETIKETI = "EK-2'de bu hastalık ve seviye için tanımlı oran"
KISIT_BASLIGI = "Bu oran için geçerli kurallar"
SIFIR_ACIKLAMA = "Bu basamakta kaynak 0 oran veriyor"
TEK_SEVIYE_NOTU = "Bu hastalıkta kaynak tek oran veriyor, şiddet basamağı yok."

BELIRSIZ_MESAJ = (
    "Kaynakta bu hastalık için tek bir oran belirlenmemiştir. Bu nedenle burada "
    "oran hesaplanamaz; değerlendirme için ilgili uzman hekime başvurulmalıdır."
)
BELIRSIZ_KAYNAK_NOTU = (
    "Kaynak notu (EK-2 s.{sayfa}): bu satır birden fazla klinik durumu tek orana "
    "bağlıyor ya da bir ekleme kuralına tabi."
)

YAS_BLOGU = {
    "baslik": "65 yaş ve üzeri için ek oran",
    "metin": (
        "Mevzuata göre 65 yaş ve üzerindeki bireylerin engellilik oranına Balthazard "
        "formülü ile %10 eklenir. Bu ek, yukarıdaki orana düz toplama ile eklenmez; "
        "Araç-2'de diğer oranlarla birlikte Balthazard yöntemiyle hesaplanır."
    ),
    "ornek": "Örnek: %40 → %46.",
    "kaynak": (
        "20.02.2019 tarihli ve 30692 sayılı Resmî Gazete'de yayımlanan Erişkinler İçin "
        "Engellilik Değerlendirmesi Hakkında Yönetmelik (m. 10/4)."
    ),
    "not": "Bu blok yukarıdaki oranı değiştirmez; %10 otomatik aktarılmaz.",
}

# Tablo/formül gerektiren kategoriler: sabit oranlı hastalık kaydı ÜRETMEZ.
# Kaynakta bu alanlar için tek satırlık yüzde yoktur; hesaplama tabloları
# veri/ozel_hesaplamalar.json içindedir. Çipler bunları ayrı kategori olarak
# gösterir, seçildiğinde "kayıt yok" bilgisi + yöntem notu verilir.
TABLO_KATEGORILERI = (
    {
        "ad": "GÖRME SİSTEMİ",
        "kisa": "Göz Hastalıkları",
        "aciklama": ("Görme kaybı görme keskinliği ve görme alanı tablolarıyla "
                     "hesaplanır (OZ-GOR-001). Sabit oranlı hastalık kaydı yoktur."),
        "ozel_hesaplama_idler": ["OZ-GOR-001"],
    },
    {
        "ad": "KAS-İSKELET SİSTEMİ",
        "kisa": "Kas-İskelet Sistemi",
        "aciklama": ("Omurga, üst ve alt ekstremite tablolarıyla hesaplanır "
                     "(OZ-KIS-001/002/003). Sabit oranlı hastalık kaydı yoktur."),
        "ozel_hesaplama_idler": ["OZ-KIS-001", "OZ-KIS-002", "OZ-KIS-003"],
    },
    {
        "ad": "ROMATOLOJİ",
        "kisa": "Romatoloji",
        "aciklama": ("Romatolojik tanılar kaynakta ayrı bölüm değildir; kas-iskelet, deri, "
                     "böbrek, akciğer ve sinir sistemi bölümlerinde değerlendirilir "
                     "(OZ-ROM-001). Bu kategori ayrı oran üretmez."),
        "ozel_hesaplama_idler": ["OZ-ROM-001"],
    },
    {
        "ad": "YANIKLAR",
        "kisa": "Yanıklar",
        "aciklama": ("Yanık sekelleri yanan vücut yüzeyi alanına göre tabloyla belirlenir "
                     "(OZ-YAN-001). II–VI alt başlıkları ilgili branşa yönlendirir."),
        "ozel_hesaplama_idler": ["OZ-YAN-001"],
    },
)

BOLUM_NOTU = {
    "baslik": "Bölüm notu (kaynak s.26)",
    "metin": (
        "Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali olan hastalarda "
        "raporun geçerlilik süresi belirtilmelidir."
    ),
    "not": "Bu not kayıt kısıtı değildir; kısıt sayısına eklenmez.",
}

BOS_SONUC = {
    "yazim": "Farklı bir yazım deneyin. Bölüm seçimi sonuçları daraltır.",
    "kapsam": "Görme ve kas-iskelet sistemindeki bazı değerlendirmeler ölçüm, tablo dönüşümü veya birden fazla adım gerektirir; bunlar tek bir sabit oran olarak gösterilmez.",
}

ARAMA_IPUCU = (
    "Arama 3 karakterden sonra çalışır. Türkçe karakterlerin temel yazım farklılıkları "
    "desteklenir; eş anlamlı ve ses benzerliği eşleştirmesi yapılmaz."
)

ALT_BILGI = {
    "kisa": "Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık kurulu raporu yerine geçmez.",
    "uzun": (
        "Oranlar EK-2 kılavuzundan alınmıştır. Çalışma gücü kaybı değerlendirmesi ayrı "
        "bir hukuki süreçtir ve bu oranlarla eşitlenemez."
    ),
}

# §4.4 — renk tek başına anlam taşımaz: tür etiketi + farklı ikon + açıklama.
KISITLAR = {
    "R-VERGI": {
        "tur": "KULLANIM SINIRI",
        "onem": "Dikkat",
        "ikon": "⛔",
        "ton": "kirmizi",
        "aciklama": "İş başvurusu ve vergi indiriminde bu derecelendirme dikkate alınmaz.",
    },
    "R-REMISYON": {
        "tur": "ORAN VERİLMEZ",
        "onem": "Dikkat",
        "ikon": "⛔",
        "ton": "kirmizi",
        "aciklama": "Remisyonda ise oran verilmez.",
    },
    "R-GECICI": {
        "tur": "GEÇİCİ DEĞERLENDİRME",
        "onem": "Orta",
        "ikon": "⚠",
        "ton": "amber",
        "aciklama": "Geçici fonksiyon kaybı; 1 yıl sonra değerlendirilip kesin karara varılır.",
    },
    "R-NAKIL": {
        "tur": "GEÇERLİLİK SÜRESİ",
        "onem": "Orta",
        "ikon": "⚠",
        "ton": "amber",
        "aciklama": "Aktivasyon/gerileme ihtimali varsa rapor geçerlilik süresi belirtilir.",
    },
    "R-YILLIK": {
        "tur": "YENİDEN DEĞERLENDİRME",
        "onem": "Bilgi",
        "ikon": "ℹ",
        "ton": "notr",
        "aciklama": "Talep hâlinde yıllık kontrolle yeniden değerlendirilir.",
    },
    "R-IKTIYOZ": {
        "tur": "DEĞERLENDİRME YÖNTEMİ",
        "onem": "Bilgi",
        "ikon": "ℹ",
        "ton": "notr",
        "aciklama": "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir.",
    },
    "R-EKTO": {
        "tur": "DEĞERLENDİRME YÖNTEMİ",
        "onem": "Bilgi",
        "ikon": "ℹ",
        "ton": "notr",
        "aciklama": "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir.",
    },
}


# --- Katalog (tembel, salt okunur) ------------------------------------------

_KATALOG: Katalog | None = None
_TEK_KAYITLI: set[str] | None = None


def katalog() -> Katalog:
    """Kataloğu bir kez yükler; değişmez bozuksa ``KatalogHatasi`` yükselir."""
    global _KATALOG
    if _KATALOG is None:
        _KATALOG = yukle()
    return _KATALOG


def tek_kayitli_kimlikler() -> set[str]:
    """Tek kayıtlı hastalık gruplarının kimlikleri (§3.8: seviye adımı yok)."""
    global _TEK_KAYITLI
    if _TEK_KAYITLI is None:
        _TEK_KAYITLI = {
            kayit.id
            for bolum in katalog().bolumler
            for grup in bolum.gruplar
            for hastalik in grup.hastaliklar
            if hastalik.tek_kayit
            for kayit in hastalik.kayitlar
        }
    return _TEK_KAYITLI


def ek_katalog() -> dict:
    """Sabit oranlı ek kayıtları ana kataloğun değişmezlerinden ayrı, salt okunur yükler."""
    global _EK_KATALOG
    if _EK_KATALOG is None:
        _EK_KATALOG = yukle_ek_katalog(EK_KATALOG_YOLU)
    return _EK_KATALOG


def ek_mukerrer(satir: dict) -> bool:
    """Ana katalogda birebir karşılığı olan ek satır (``esdeger`` alanı).

    Bu satırlar veride korunur (kaynak izi ve ``/api/kayit/<id>`` erişimi için)
    ancak gezinme ve aramada gizlenir; aynı evre iki kez listelenmez.
    """
    return bool(satir.get("esdeger"))


def ozel_hesaplamalar() -> dict:
    """Formül/tablo gerektiren kaynak yöntemleri; bunlar sabit oran olarak sunulmaz."""
    global _OZEL_HESAPLAMALAR
    if _OZEL_HESAPLAMALAR is None:
        _OZEL_HESAPLAMALAR = yukle_ozel_hesaplamalar(OZEL_HESAPLAMA_YOLU)
    return _OZEL_HESAPLAMALAR


def kurallar() -> dict:
    """Ek kayıtların dışlama/birleşim/yönlendirme kural katmanı."""
    global _KURALLAR
    if _KURALLAR is None:
        _KURALLAR = yukle_kurallar(KURAL_YOLU)
        kural_kapsamini_dogrula(ek_katalog(), _KURALLAR)
    return _KURALLAR


def kural_listesi(satir: dict) -> list[dict]:
    """Ek kaydın bağlı olduğu kuralları arayüz biçimine çevirir."""
    harita = {k["kod"]: k for k in kurallar().get("kurallar", [])}
    sonuc = []
    for kod in satir.get("kural", []):
        kural = harita[kod]
        sonuc.append({
            "kod": kod,
            "tur": kural["tur"],
            "onem": kural["onem"],
            "ikon": kural["ikon"],
            "ton": kural["ton"],
            "aciklama": kural["aciklama"],
            "uygulama": kural["uygulama"],
            "kaynak": "EK-2, s.%s" % kural["kaynak"]["sayfa"],
        })
    return sonuc


def kisa_etiket(kayit_id: str, sayfa: int) -> str:
    """Aktarım listesi etiketi: **hastalık bilgisi taşımaz** (§4.9)."""
    return "EK-2 kaydı {0} · s.{1}".format(kayit_id, sayfa)


def oran_gosterim(oran: int) -> dict:
    """Katalog oranını **motordan** geçirir; Araç-1 kendi hesabını yapmaz."""
    motor = balthazard({"oranlar": [oran], "yas": YAS_ALTI, "yas_ekle": False})
    if not motor.get("ok"):
        raise KatalogHatasi("Motor oranı kabul etmedi: %r" % (motor.get("hata"),))
    if motor["yas_eklemesi"]["uygulandi"]:  # savunma: O-1 bozulmasın
        raise KatalogHatasi("Araç-1 yaş eki uygulamamalıdır (O-1).")
    return {
        "ham": motor["sonuc"]["deger"],
        "gosterim": bicimle_gosterim(motor["sonuc"]["deger"]),
    }


def kisit_listesi(kayit) -> list[dict]:
    return [dict(KISITLAR[kod], kod=kod) for kod in kayit.kisit]


def bolum_notu(kayit) -> dict | None:
    """Yalnız Hematoloji'de, kayıt kısıtlarından ayrı (§3.12)."""
    return dict(BOLUM_NOTU) if kayit.bolum == "HEMATOLOJİK HASTALIKLAR" else None


def kayit_ozeti(kayit) -> dict:
    """Arama satırı: hastalık adı, seviye, oran, bölüm/grup rozeti (§4.2)."""
    return {
        "id": kayit.id,
        "ad": kayit.ad,
        "seviye": kayit.seviye,
        "rozet": kayit.rozet,
        "bolum": kayit.bolum,
        "bolum_kisa": bolum_kisa(kayit.bolum),
        "grup": kayit.grup,
        "oran": kayit.oran,
        "oran_gosterim": oran_gosterim(kayit.oran)["gosterim"],
        "sayfa": kayit.sayfa,
        "tek_kayit": kayit.id in tek_kayitli_kimlikler(),
    }


def sonuc_yuku(kayit) -> dict:
    """Sonuç ekranı verisi (§4.3-§4.6)."""
    gosterim = oran_gosterim(kayit.oran)
    kisitlar = kisit_listesi(kayit)
    grup = None
    for bolum in katalog().bolumler:
        for grup_nesnesi in bolum.gruplar:
            if kayit in grup_nesnesi.kayitlar:
                grup = grup_nesnesi
                break
        if grup is not None:
            break
    tek_kayit = kayit.id in tek_kayitli_kimlikler()
    return {
        "ok": True,
        "tur": "sonuc",
        "id": kayit.id,
        "ad": kayit.ad,
        "seviye": kayit.seviye,
        "rozet": kayit.rozet,
        "bolum": kayit.bolum,
        "bolum_kisa": bolum_kisa(kayit.bolum),
        "grup": grup.ad if grup else None,
        "grup_rozet": grup.rozet if grup else None,
        "oran": {
            "ham": gosterim["ham"],
            "gosterim": gosterim["gosterim"],
            "etiket": ORAN_ETIKETI,
        },
        "sifir": kayit.oran == 0,
        "sifir_aciklama": SIFIR_ACIKLAMA if kayit.oran == 0 else None,
        "kaynak": "Kaynak: EK-2, sayfa {0} · kayıt {1}".format(kayit.sayfa, kayit.id),
        "kaynak_not": kayit.kaynak_not,
        "kisitlar": kisitlar,
        "kisit_basligi": "{0} ({1})".format(KISIT_BASLIGI, len(kisitlar)),
        "tek_kayit": tek_kayit,
        "seviye_adimi": not tek_kayit,
        "tek_seviye_notu": TEK_SEVIYE_NOTU if tek_kayit else None,
        "yas_bloku": dict(YAS_BLOGU),
        "bolum_notu": bolum_notu(kayit),
        "kisa_etiket": kisa_etiket(kayit.id, kayit.sayfa),
        "alt_bilgi": dict(ALT_BILGI),
    }


def belirsiz_yuku(satir) -> dict:
    """Belirsiz ekranı (§4.7): **oran yok**, hesaplamaya ekle yok."""
    return {
        "ok": True,
        "tur": "belirsiz",
        "id": satir.id,
        "bolum": satir.bolum,
        "bolum_kisa": bolum_kisa(satir.bolum),
        "ad": satir.ad,
        "seviye": satir.seviye,
        "mesaj": BELIRSIZ_MESAJ,
        "kaynak_notu": BELIRSIZ_KAYNAK_NOTU.format(sayfa=satir.sayfa),
        "sorun": satir.sorun_cumlesi,
        "sayfa": satir.sayfa,
        "alt_bilgi": dict(ALT_BILGI),
    }


def ek_kayit_sonuc_yuku(bolum: dict, satir: dict) -> dict:
    """EK-2 ek kaydını hem bağımsız Araç-1 hem ana site API'si için biçimlendirir."""
    gosterim = oran_gosterim(satir["oran"])
    kisitlar = kural_listesi(satir)
    esdeger = satir.get("esdeger")
    return {
        "ok": True, "tur": "sonuc", "id": satir["id"],
        "ad": satir["hastalik"], "seviye": satir["alt_tur"],
        "rozet": "EK-2 ek kayıt", "bolum": bolum["ad"],
        "bolum_kisa": bolum.get("kisa", bolum["ad"]),
        "grup": None, "grup_rozet": None,
        "oran": {"ham": gosterim["ham"], "gosterim": gosterim["gosterim"],
                 "etiket": "EK-2 kaynak satırında açıkça belirtilen sabit oran"},
        "sifir": satir["oran"] == 0, "sifir_aciklama": None,
        "kaynak": "Kaynak: EK-2, sayfa %s · kayıt %s" % (satir["sayfa"], satir["id"]),
        "kaynak_not": satir.get("kaynak_not", "Ek katalog kaydı."),
        "esdeger": esdeger,
        "esdeger_notu": (
            "Bu ek kayıt, ana katalogdaki %s kaydıyla aynı hükmü taşır; "
            "çift sayımı önlemek için listelerde gösterilmez." % esdeger
            if esdeger else None
        ),
        "kisitlar": kisitlar,
        "kisit_basligi": "{0} ({1})".format(KISIT_BASLIGI, len(kisitlar)),
        "tek_kayit": True, "seviye_adimi": False,
        "tek_seviye_notu": (
            "Bu kaynak satırı ayrı kayıt olarak aktarılmıştır; "
            "bölümün tamamı henüz eksiksiz değildir."
        ),
        "yas_bloku": dict(YAS_BLOGU), "bolum_notu": None,
        "kisa_etiket": kisa_etiket(satir["id"], satir["sayfa"]),
        "alt_bilgi": dict(ALT_BILGI),
    }


def bolum_kisa(ad: str) -> str:
    """Bölüm kısa adını ana ve ek kataloglarda tek biçimde döndürür."""
    for bolum in katalog().bolumler:
        if bolum.ad == ad:
            return bolum.kisa
    for bolum in ek_katalog().get("bolumler", []):
        if bolum.get("ad") == ad:
            return bolum.get("kisa", ad)
    return ad


def tablo_kategorisi(ad: str | None) -> dict | None:
    """Tablo/formül gerektiren kategori mi? (sabit oranlı kayıt üretmez)"""
    if not ad:
        return None
    return next((k for k in TABLO_KATEGORILERI if ad in (k["ad"], k["kisa"])), None)


def gezinme_yuku(bolum_adi: str | None) -> dict:
    katalog_nesnesi = katalog()
    ek_bolumler = ek_katalog().get("bolumler", [])

    tablo_kat = tablo_kategorisi(bolum_adi)
    if tablo_kat is not None:
        return {
            "ok": True,
            "bolum": {"ad": tablo_kat["ad"], "kisa": tablo_kat["kisa"], "kayit_sayisi": 0},
            "gruplar": [],
            "tablo_kategorisi": {
                "kisa": tablo_kat["kisa"],
                "aciklama": tablo_kat["aciklama"],
                "ozel_hesaplama_idler": list(tablo_kat.get("ozel_hesaplama_idler", [])),
            },
        }

    def ek_grubu(ek):
        harita = {}
        for satir in ek.get("kayitlar", []):
            if ek_mukerrer(satir):
                continue
            harita.setdefault(satir["hastalik"], []).append(satir)
        if not harita:
            return None
        hastaliklar = [{
            "anahtar": ad, "ad": ad, "tek_kayit": len(satirlar) == 1,
            "seviyeler": [{
                "id": s["id"], "seviye": s["alt_tur"], "oran": s["oran"],
                "oran_gosterim": oran_gosterim(s["oran"])["gosterim"], "sayfa": s["sayfa"],
            } for s in satirlar],
        } for ad, satirlar in harita.items()]
        return {
            "anahtar": ek["ad"], "ad": "EK-2 ek kayıtlar", "rozet": "EK-2",
            "kayit_sayisi": sum(len(s) for s in harita.values()), "hastaliklar": hastaliklar,
        }

    if bolum_adi:
        bolum = katalog_nesnesi.bolum(bolum_adi)
        ek = next((b for b in ek_bolumler if bolum_adi in (b.get("ad"), b.get("kisa"))), None)
        if bolum is None and ek is None:
            return {"ok": False, "mesaj": "Bilinmeyen bölüm."}
        if bolum is not None:
            gruplar = [{
                "anahtar": grup.anahtar, "ad": grup.ad, "rozet": grup.rozet,
                "kayit_sayisi": len(grup.kayitlar),
                "hastaliklar": [hastalik_sozluk(h) for h in grup.hastaliklar],
            } for grup in bolum.gruplar]
            ek_ayni = next((b for b in ek_bolumler if b.get("ad") == bolum.ad), None)
            ek_sayi = (
                sum(1 for s in ek_ayni.get("kayitlar", []) if not ek_mukerrer(s))
                if ek_ayni else 0
            )
            if ek_ayni:
                ek_grup = ek_grubu(ek_ayni)
                if ek_grup is not None:
                    gruplar.append(ek_grup)
            return {
                "ok": True,
                "bolum": {"ad": bolum.ad, "kisa": bolum.kisa,
                          "kayit_sayisi": len(bolum.kayitlar) + ek_sayi},
                "gruplar": gruplar,
            }
        return {
            "ok": True,
            "bolum": {"ad": ek["ad"], "kisa": ek.get("kisa", ek["ad"]),
                      "kayit_sayisi": len(ek.get("kayitlar", []))},
            "gruplar": [g for g in (ek_grubu(ek),) if g is not None],
        }

    bolum_listesi = []
    for bolum in katalog_nesnesi.bolumler:
        ek_ayni = next((b for b in ek_bolumler if b.get("ad") == bolum.ad), None)
        ek_sayi = (
            sum(1 for s in ek_ayni.get("kayitlar", []) if not ek_mukerrer(s))
            if ek_ayni else 0
        )
        bolum_listesi.append({
            "ad": bolum.ad, "kisa": bolum.kisa,
            "kayit_sayisi": len(bolum.kayitlar) + ek_sayi,
            "grup_sayisi": len(bolum.gruplar) + (1 if ek_sayi else 0),
        })
    for ek in ek_bolumler:
        if any(b.get("ad") == ek["ad"] for b in bolum_listesi):
            continue
        bolum_listesi.append({
            "ad": ek["ad"], "kisa": ek.get("kisa", ek["ad"]),
            "kayit_sayisi": len(ek.get("kayitlar", [])), "grup_sayisi": 1,
        })
    # Tablo/formül gerektiren kategoriler listenin sonuna eklenir.
    # Sabit oranlı kaydı olmadığı için kayit_sayisi=0 ve grup_sayisi=0'dır.
    for kat in TABLO_KATEGORILERI:
        bolum_listesi.append({
            "ad": kat["ad"], "kisa": kat["kisa"],
            "kayit_sayisi": 0, "grup_sayisi": 0, "tablo_kategorisi": True,
        })
    return {
        "ok": True, "bolumler": bolum_listesi,
        "kategori_notlari": [
            {"kisa": k["kisa"], "aciklama": k["aciklama"]} for k in TABLO_KATEGORILERI
        ],
        "kapsam_disi": list(katalog_nesnesi.meta.get("kapsam_disi") or []),
        "kapsam_kismi": list(katalog_nesnesi.meta.get("kapsam_kismi") or []),
    }


def hastalik_sozluk(hastalik) -> dict:
    return {
        "anahtar": hastalik.anahtar,
        "ad": hastalik.ad,
        "tek_kayit": hastalik.tek_kayit,
        "seviyeler": [
            {
                "id": kayit.id,
                "seviye": kayit.seviye,
                "oran": kayit.oran,
                "oran_gosterim": oran_gosterim(kayit.oran)["gosterim"],
                "sayfa": kayit.sayfa,
            }
            for kayit in hastalik.kayitlar
        ],
    }


def arama_yuku(metin: str, bolum_adi: str | None) -> dict:
    katalog_nesnesi = katalog()
    temiz = (metin or "").strip()[:AZAMI_SORGU]
    if len(temiz) < 3:
        return {
            "ok": True,
            "metin": temiz,
            "sonuclar": [],
            "belirsizler": [],
            "mesaj": ARAMA_IPUCU,
            "ipucu": None,
        }
    ek_bolum_secili = None
    ana_bolum_adi = None
    if bolum_adi:
        bolum = katalog_nesnesi.bolum(bolum_adi)
        ek_eslesen = next(
            (b for b in ek_katalog().get("bolumler", [])
             if bolum_adi in (b.get("ad"), b.get("kisa"))),
            None,
        )
        ek_bolum_secili = ek_eslesen if bolum is None else None
        if bolum is None and ek_bolum_secili is None:
            return {"ok": False, "mesaj": "Bilinmeyen bölüm."}
        if bolum is not None:
            ana_bolum_adi = bolum.ad

    kayitlar = list(katalog_nesnesi.ara(temiz, ana_bolum_adi)) if not ek_bolum_secili else []
    belirsizler = list(katalog_nesnesi.belirsiz_ara(temiz, ana_bolum_adi)) if not ek_bolum_secili else []
    # EK-2 ek kayıtları ayrı dosyada doğrulanır; ana kataloğun sayım değişmezleri korunur.
    for bolum in ek_katalog().get("bolumler", []):
        if bolum_adi and bolum_adi not in (bolum.get("ad"), bolum.get("kisa")):
            continue
        for satir in bolum.get("kayitlar", []):
            if ek_mukerrer(satir):
                continue
            metin_satir = katla(" ".join((satir.get("hastalik", ""), satir.get("alt_tur", ""), bolum.get("ad", ""))))
            if katla(temiz) not in metin_satir:
                continue
            oran = oran_gosterim(satir["oran"])
            kayitlar.append({
                "id": satir["id"],
                "ad": satir["hastalik"],
                "seviye": satir["alt_tur"],
                "rozet": "EK-2 ek kayıt",
                "bolum": bolum["ad"],
                "bolum_kisa": bolum_kisa(bolum["ad"]),
                "grup": None,
                "oran": satir["oran"],
                "oran_gosterim": oran["gosterim"],
            })
    yanit = {
        "ok": True,
        "metin": temiz,
        "sonuclar": [k if isinstance(k, dict) else kayit_ozeti(k) for k in kayitlar],
        "belirsizler": [
            {
                "id": s.id,
                "ad": s.ad,
                "seviye": s.seviye,
                "bolum": s.bolum,
                "bolum_kisa": bolum_kisa(s.bolum),
                "sorun": s.sorun_cumlesi,
            }
            for s in belirsizler
        ],
        "mesaj": None,
        "ipucu": None,
    }
    if not kayitlar and not belirsizler:
        yanit["mesaj"] = "“{0}” için sonuç bulunamadı".format(temiz)
        yanit["ipucu"] = dict(BOS_SONUC)
    return yanit


class Isleyici(BaseHTTPRequestHandler):
    server_version = "Arac1Prototip/0.1"
    sys_version = ""

    # --- yanıt yardımcıları -------------------------------------------------

    def _gonder(self, durum: HTTPStatus, govde: bytes, tur: str) -> None:
        self.send_response(durum)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(govde)

    def _json(self, veri: dict, durum: HTTPStatus = HTTPStatus.OK) -> None:
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self._gonder(durum, govde, "application/json; charset=utf-8")

    def _html(self) -> None:
        try:
            govde = SAYFA.read_bytes()
        except OSError:
            self._json(
                {"ok": False, "mesaj": "Ekran dosyası bulunamadı."},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._gonder(HTTPStatus.OK, govde, "text/html; charset=utf-8")

    # --- yönlendirme --------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 (http.server API'si)
        parca = urlsplit(self.path)
        yol = unquote(parca.path)
        sorgu = parse_qs(parca.query)

        if yol in ("/", "/arac1", "/arac1/"):
            self._html()
        elif yol == "/saglik":
            self._saglik()
        elif yol == "/api/bolumler":
            self._json(gezinme_yuku(None))
        elif yol == "/api/ozel-hesaplamalar":
            self._json({"ok": True, **ozel_hesaplamalar()})
        elif yol == "/api/kurallar":
            self._json({"ok": True, **kurallar()})
        elif yol == "/api/gezinme":
            veri = gezinme_yuku(_ilk(sorgu, "bolum"))
            self._json(veri, HTTPStatus.OK if veri.get("ok") else HTTPStatus.NOT_FOUND)
        elif yol == "/api/ara":
            veri = arama_yuku(_ilk(sorgu, "metin") or "", _ilk(sorgu, "bolum"))
            self._json(veri, HTTPStatus.OK if veri.get("ok") else HTTPStatus.NOT_FOUND)
        elif yol.startswith("/api/kayit/"):
            self._kayit(yol[len("/api/kayit/"):], belirsiz_zorunlu=False)
        elif yol.startswith("/api/belirsiz/"):
            self._kayit(yol[len("/api/belirsiz/"):], belirsiz_zorunlu=True)
        else:
            self._json({"ok": False, "mesaj": "Bulunamadı."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parca = urlsplit(self.path)
        if unquote(parca.path) != "/api/hesapla":
            self._json({"ok": False, "mesaj": "Bulunamadı."}, HTTPStatus.NOT_FOUND)
            return
        try:
            uzunluk = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            uzunluk = -1
        if uzunluk <= 0 or uzunluk > 64 * 1024:
            self._json({"ok": False, "mesaj": "İstek okunamadı."}, HTTPStatus.BAD_REQUEST)
            return
        try:
            girdi = json.loads(self.rfile.read(uzunluk).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json({"ok": False, "mesaj": "İstek okunamadı."}, HTTPStatus.BAD_REQUEST)
            return
        sonuc = balthazard(girdi)
        if sonuc.get("ok"):
            sonuc["gosterim"] = gosterim_ekle(sonuc)
        self._json(sonuc, HTTPStatus.OK if sonuc.get("ok") else HTTPStatus.BAD_REQUEST)

    # --- uçlar --------------------------------------------------------------

    def _saglik(self) -> None:
        katalog_nesnesi = katalog()
        self._json(
            {
                "ok": True,
                "kayit": len(katalog_nesnesi.kayitlar),
                "ek_kayit": sum(len(b.get("kayitlar", [])) for b in ek_katalog().get("bolumler", [])),
                "ek_mukerrer": sum(
                    1
                    for b in ek_katalog().get("bolumler", [])
                    for s in b.get("kayitlar", [])
                    if ek_mukerrer(s)
                ),
                "ozel_hesaplama": len(ozel_hesaplamalar().get("ozel_hesaplamalar", [])),
                "kural": len(kurallar().get("kurallar", [])),
                "belirsiz": sum(1 for s in katalog_nesnesi.belirsiz if s.durum == "belirsiz"),
                "bolumler": [b["kisa"] for b in gezinme_yuku(None)["bolumler"]],
            }
        )

    def _kayit(self, kimlik: str, belirsiz_zorunlu: bool) -> None:
        kimlik = kimlik.strip().strip("/")
        if not kimlik:
            self._json({"ok": False, "mesaj": "Kayıt kimliği gerekli."}, HTTPStatus.BAD_REQUEST)
            return
        katalog_nesnesi = katalog()
        if kimlik.startswith(("KV-", "KH-", "UG-", "SS-", "EM-", "GH-", "ON-", "SN-")):
            for bolum in ek_katalog().get("bolumler", []):
                for satir in bolum.get("kayitlar", []):
                    if satir.get("id") != kimlik:
                        continue
                    self._json(ek_kayit_sonuc_yuku(bolum, satir))
                    return
            self._json({"ok": False, "mesaj": "Ek katalog kaydı bulunamadı."}, HTTPStatus.NOT_FOUND)
            return
        if kimlik.startswith("X-"):
            satir = katalog_nesnesi.belirsiz_kayit(kimlik)
            if satir is None:
                # Çözülmüş satır arama sonucu değildir (§3.10).
                self._json(
                    {"ok": False, "mesaj": "Bu satır arama sonucu değildir."},
                    HTTPStatus.NOT_FOUND,
                )
                return
            self._json(belirsiz_yuku(satir))
            return
        if belirsiz_zorunlu:
            self._json({"ok": False, "mesaj": "Bulunamadı."}, HTTPStatus.NOT_FOUND)
            return
        kayit = katalog_nesnesi.kayit(kimlik)
        if kayit is None:
            self._json({"ok": False, "mesaj": "Kayıt bulunamadı."}, HTTPStatus.NOT_FOUND)
            return
        self._json(sonuc_yuku(kayit))

    # Gürültülü varsayılan günlük yerine tek satır.
    def log_message(self, kalip: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), kalip % args))


def _ilk(sorgu: dict, anahtar: str) -> str | None:
    degerler = sorgu.get(anahtar) or []
    return degerler[0] if degerler else None


def main(argv: list[str]) -> int:
    port = VARSAYILAN_PORT
    if len(argv) > 1:
        try:
            port = int(argv[1])
        except ValueError:
            print("Port tam sayı olmalıdır.", file=sys.stderr)
            return 2

    if not SAYFA.exists():
        print("Ekran dosyası bulunamadı: %s" % SAYFA, file=sys.stderr)
        return 1

    try:
        katalog()  # değişmezler bozuksa uygulama açılmaz (§3.4)
    except KatalogHatasi as hata:
        print("Katalog yüklenemedi: %s" % hata, file=sys.stderr)
        return 1

    sunucu = ThreadingHTTPServer(("127.0.0.1", port), Isleyici)
    print("Araç-1 prototipi: http://127.0.0.1:%d" % port)
    print("Durdurmak için Ctrl+C")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nDurduruldu.")
    finally:
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))