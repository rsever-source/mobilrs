# -*- coding: utf-8 -*-
"""Araç-1 — Engel Oranı Bul ekranı için küçük, bağımsız sunucu (prototip).

Sözleşme: ``SOZLESME.md`` §3 (veri sözleşmesi) ve §4 (ekran sözleşmesi).

Tasarım kararları (sözleşmeye bağlı):

* Katalog **salt okunur** yüklenir (``katalog_okuyucu``); dosyalara yazılmaz,
  ``—``/belirsiz kayıt yorumlanmaz (§3.1, §3.4, §3.9, §3.10).
* Ekran **hesap yapmaz**: her oran motordan ``balthazard()`` +
  ``bicimle_gosterim()`` ile alınır; kopya formül yoktur (§3.14, §2.7).
* Yaş eki **uygulanmaz**: çağrı ``yas_ekle=False`` ile yapılır (O-1). Motor
  ``yas`` alanını zorunlu tuttuğu için ``65_alti`` gönderilir; ek uygulanmaz.
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

from balthazard_motoru import YAS_ALTI, balthazard, bicimle_gosterim  # noqa: E402
from katalog_okuyucu import Katalog, KatalogHatasi, katla, yukle  # noqa: E402

SAYFA = BURASI / "arac1.html"
VARSAYILAN_PORT = 8766
ARAC2_ADRESI = "http://127.0.0.1:8765/arac2"
AZAMI_SORGU = 120
EK_KATALOG_YOLU = KOK / "veri" / "katalog_ek2_ek.json"
OZEL_HESAPLAMA_YOLU = KOK / "veri" / "ozel_hesaplamalar.json"
_EK_KATALOG: dict | None = None
_OZEL_HESAPLAMALAR: dict | None = None

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

BOLUM_NOTU = {
    "baslik": "Bölüm notu (kaynak s.26)",
    "metin": (
        "Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali olan hastalarda "
        "raporun geçerlilik süresi belirtilmelidir."
    ),
    "not": "Bu not kayıt kısıtı değildir; kısıt sayısına eklenmez.",
}

BOS_SONUC = {
    "yazim": "Yazımı kontrol edin veya bölüm seçerek ilerleyin.",
    "kapsam": "Göz, işitme, konuşma ve kas-iskelet bölümleri bu araçta henüz yok.",
}

ARAMA_IPUCU = "Arama 3 karakterden sonra çalışır."

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
        try:
            veri = json.loads(EK_KATALOG_YOLU.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as hata:
            raise KatalogHatasi("Ek katalog yüklenemedi: %s" % hata) from hata
        kimlikler = set()
        for bolum in veri.get("bolumler", []):
            for kayit in bolum.get("kayitlar", []):
                if not kayit.get("id") or kayit["id"] in kimlikler:
                    raise KatalogHatasi("Ek katalogda boş/tekrarlı kimlik.")
                if not isinstance(kayit.get("oran"), int) or not 0 <= kayit["oran"] <= 100:
                    raise KatalogHatasi("Ek katalogda geçersiz oran: %s" % kayit.get("id"))
                if not kayit.get("hastalik") or not kayit.get("sayfa"):
                    raise KatalogHatasi("Ek katalogda zorunlu alan eksik: %s" % kayit["id"])
                kimlikler.add(kayit["id"])
        _EK_KATALOG = veri
    return _EK_KATALOG


def ozel_hesaplamalar() -> dict:
    """Formül/tablo gerektiren kaynak yöntemleri; bunlar sabit oran olarak sunulmaz."""
    global _OZEL_HESAPLAMALAR
    if _OZEL_HESAPLAMALAR is None:
        try:
            veri = json.loads(OZEL_HESAPLAMA_YOLU.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as hata:
            raise KatalogHatasi("Özel hesaplama kataloğu yüklenemedi: %s" % hata) from hata
        if not isinstance(veri.get("ozel_hesaplamalar"), list):
            raise KatalogHatasi("Özel hesaplama kataloğu biçimi geçersiz.")
        _OZEL_HESAPLAMALAR = veri
    return _OZEL_HESAPLAMALAR


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


def bolum_kisa(ad: str) -> str:
    for bolum in katalog().bolumler:
        if bolum.ad == ad:
            return bolum.kisa
    return ad


def gezinme_yuku(bolum_adi: str | None) -> dict:
    katalog_nesnesi = katalog()
    if bolum_adi:
        bolum = katalog_nesnesi.bolum(bolum_adi)
        if bolum is None:
            return {"ok": False, "mesaj": "Bilinmeyen bölüm."}
        return {
            "ok": True,
            "bolum": {"ad": bolum.ad, "kisa": bolum.kisa, "kayit_sayisi": len(bolum.kayitlar)},
            "gruplar": [
                {
                    "anahtar": grup.anahtar,
                    "ad": grup.ad,
                    "rozet": grup.rozet,
                    "kayit_sayisi": len(grup.kayitlar),
                    "hastaliklar": [hastalik_sozluk(h) for h in grup.hastaliklar],
                }
                for grup in bolum.gruplar
            ],
        }
    return {
        "ok": True,
        "bolumler": [
            {
                "ad": bolum.ad,
                "kisa": bolum.kisa,
                "kayit_sayisi": len(bolum.kayitlar),
                "grup_sayisi": len(bolum.gruplar),
            }
            for bolum in katalog_nesnesi.bolumler
        ],
        "kapsam_disi": list(katalog_nesnesi.meta.get("kapsam_disi") or []),
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
    if bolum_adi:
        bolum = katalog_nesnesi.bolum(bolum_adi)
        ek_bolum = next(
            (b for b in ek_katalog().get("bolumler", [])
             if bolum_adi in (b.get("ad"), b.get("kisa"))),
            None,
        )
        if bolum is None and ek_bolum is None:
            return {"ok": False, "mesaj": "Bilinmeyen bölüm."}
        if bolum is not None:
            bolum_adi = bolum.ad

    kayitlar = list(katalog_nesnesi.ara(temiz, bolum_adi))
    belirsizler = list(katalog_nesnesi.belirsiz_ara(temiz, bolum_adi))
    # EK-2 ek kayıtları ayrı dosyada doğrulanır; ana kataloğun sayım değişmezleri korunur.
    for bolum in ek_katalog().get("bolumler", []):
        if bolum_adi and bolum_adi not in (bolum.get("ad"), bolum.get("kisa")):
            continue
        for satir in bolum.get("kayitlar", []):
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
                "bolum_kisa": bolum.get("kisa", bolum["ad"]),
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
        # Araç-1 hesap yapmaz; yazma ucu bilinçli olarak yoktur.
        self._json(
            {"ok": False, "mesaj": "Bu ekran yalnız okuma yapar."},
            HTTPStatus.METHOD_NOT_ALLOWED,
        )

    # --- uçlar --------------------------------------------------------------

    def _saglik(self) -> None:
        katalog_nesnesi = katalog()
        self._json(
            {
                "ok": True,
                "kayit": len(katalog_nesnesi.kayitlar),
                "belirsiz": sum(1 for s in katalog_nesnesi.belirsiz if s.durum == "belirsiz"),
                "bolumler": [b.kisa for b in katalog_nesnesi.bolumler],
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
                    gosterim = oran_gosterim(satir["oran"])
                    self._json({
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
                        "kisitlar": [], "kisit_basligi": "Bu oran için geçerli kurallar (0)",
                        "tek_kayit": True, "seviye_adimi": False,
                        "tek_seviye_notu": "Bu kaynak satırı ayrı kayıt olarak aktarılmıştır; bölümün tamamı henüz eksiksiz değildir.",
                        "yas_bloku": dict(YAS_BLOGU), "bolum_notu": None,
                        "kisa_etiket": kisa_etiket(satir["id"], satir["sayfa"]),
                        "alt_bilgi": dict(ALT_BILGI),
                    })
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
