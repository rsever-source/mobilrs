# -*- coding: utf-8 -*-
"""Araç-1 ekranı ve sunucusu testleri (\x60\x60SOZLESME.md\x60\x60 §3-§4).

Çalıştırma (depo kökünden):

    python -m unittest discover -s ek2-balthazard/arac1 -p "test_arac1.py" -v

Sunucu rastgele bir yerel portta, yalnız bu test süreci boyunca çalışır. Katalog
dosyaları **yalnız okunur**; mtime/boyut değişmezliği de test edilir.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import arac1_sunucu as a  # noqa: E402  (sys.path'i kendisi kurar)
import katalog_okuyucu as ko  # noqa: E402

TIRE = "\\u2014"

# --- Sözleşmeden birebir alınan metinler (§3.10, §3.12, §3.14, §4.4, §4.10) --
ORAN_ETIKETI = "EK-2'de bu hastalık ve seviye için tanımlı oran"
KISIT_BASLIGI = "Bu oran için geçerli kurallar"
BELIRSIZ_MESAJ = (
    "Kaynakta bu hastalık için tek bir oran belirlenmemiştir. Bu nedenle burada "
    "oran hesaplanamaz; değerlendirme için ilgili uzman hekime başvurulmalıdır."
)
YAS_BASLIK = "65 yaş ve üzeri için ek oran"
YAS_ORNEK = "Örnek: %40 → %46."
BOLUM_NOTU_BASLIK = "Bölüm notu (kaynak s.26)"
BOLUM_NOTU_METIN = (
    "Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali olan hastalarda "
    "raporun geçerlilik süresi belirtilmelidir."
)
BOS_YAZIM = "Yazımı kontrol edin veya bölüm seçerek ilerleyin."
BOS_KAPSAM = "Göz, işitme, konuşma ve kas-iskelet bölümleri bu araçta henüz yok."
ALT_BILGI = "Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık kurulu raporu yerine geçmez."
SIFIR_ACIKLAMA = "Bu basamakta kaynak 0 oran veriyor"
TEK_SEVIYE_NOTU = "Bu hastalıkta kaynak tek oran veriyor, şiddet basamağı yok."

KISIT_BEKLE = {
    "R-VERGI": ("KULLANIM SINIRI", "Dikkat", "⛔",
                "İş başvurusu ve vergi indiriminde bu derecelendirme dikkate alınmaz."),
    "R-REMISYON": ("ORAN VERİLMEZ", "Dikkat", "⛔",
                   "Remisyonda ise oran verilmez."),
    "R-GECICI": ("GEÇİCİ DEĞERLENDİRME", "Orta", "⚠",
                 "Geçici fonksiyon kaybı; 1 yıl sonra değerlendirilip kesin karara varılır."),
    "R-NAKIL": ("GEÇERLİLİK SÜRESİ", "Orta", "⚠",
                "Aktivasyon/gerileme ihtimali varsa rapor geçerlilik süresi belirtilir."),
    "R-YILLIK": ("YENİDEN DEĞERLENDİRME", "Bilgi", "ℹ",
                 "Talep hâlinde yıllık kontrolle yeniden değerlendirilir."),
    "R-IKTIYOZ": ("DEĞERLENDİRME YÖNTEMİ", "Bilgi", "ℹ",
                  "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir."),
    "R-EKTO": ("DEĞERLENDİRME YÖNTEMİ", "Bilgi", "ℹ",
               "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir."),
}

SORUN_CUMLELERI = {
    "coklu_kosul_tek_oran": "Bu satır birden fazla klinik durumu tek orana bağlıyor.",
    "ekleme_kurali": "Bu satır bağımsız oran değil, başka oranlara eklenen bir kural.",
    "olcum_iki_kriter": "Oran iki ölçütün birlikte sağlanmasına bağlı.",
    "hiyerarsi_belirsiz": "Alt koşulların üst basamakların yerine mi geçtiği belirsiz.",
    "harf_tekrari": "Kaynakta madde numarası tekrar ediyor.",
    "kombinasyon_kisiti": "Bu oran başka bir hastalıkla birlikte kullanılamaz.",
    "numaralandirma_atlamasi": "Kaynakta madde numarası atlıyor.",
}

YASAK = (
    "çalışma gücü kaybı oranı",
    "kesin engellilik oranınız",
    "maluliyet oranı",
    "resmî raporunuz",
    "bu sonuç rapor yerine geçer",
    "nihai oran",
)


class Arac1Testleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), a.Isleyici)
        cls.port = cls.sunucu.server_address[1]
        cls.is_parcacigi = threading.Thread(target=cls.sunucu.serve_forever, daemon=True)
        cls.is_parcacigi.start()

        cls.katalog = ko.yukle()
        cls.dosya_durumu = cls._dosya_durumu()

        cls.html = cls._metin("/arac1")[2]
        cls.bolumler = cls._json("/api/bolumler")[2]
        cls.gezinme = {
            bolum.ad: cls._json("/api/gezinme?bolum=" + urllib.parse.quote(bolum.ad))[2]
            for bolum in cls.katalog.bolumler
        }
        cls.sonuclar = {
            kayit.id: cls._json("/api/kayit/" + urllib.parse.quote(kayit.id))[2]
            for kayit in cls.katalog.kayitlar
        }
        cls.belirsiz_ekran = {
            satir.id: cls._json("/api/kayit/" + urllib.parse.quote(satir.id))[2]
            for satir in cls.katalog.belirsiz
            if satir.durum == "belirsiz"
        }

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()
        cls.sunucu.server_close()

    # --- yardımcılar --------------------------------------------------------

    @classmethod
    def _istek(cls, yol: str, veri: bytes | None = None):
        adres = "http://127.0.0.1:%d%s" % (cls.port, yol)
        istek = urllib.request.Request(adres, data=veri, method="POST" if veri else "GET")
        try:
            with urllib.request.urlopen(istek, timeout=10) as yanit:
                return yanit.status, yanit.headers.get("Content-Type", ""), yanit.read()
        except urllib.error.HTTPError as hata:
            return hata.code, hata.headers.get("Content-Type", ""), hata.read()

    @classmethod
    def _json(cls, yol: str):
        durum, tur, govde = cls._istek(yol)
        return durum, tur, json.loads(govde.decode("utf-8"))

    @classmethod
    def _metin(cls, yol: str):
        durum, tur, govde = cls._istek(yol)
        return durum, tur, govde.decode("utf-8")

    @staticmethod
    def _dosya_durumu() -> dict:
        return {
            yol.name: (yol.stat().st_mtime_ns, yol.stat().st_size)
            for yol in (ko.VERI_KLASORU / ko.KATALOG_ADI, ko.VERI_KLASORU / ko.BELIRSIZ_ADI)
        }

    # --- ekran --------------------------------------------------------------

    def test_html_ekrani_servis_edilir(self):
        durum, tur, html = self._istek("/arac1")
        self.assertEqual(durum, 200)
        self.assertIn("text/html; charset=utf-8", tur)
        govde = html.decode("utf-8")
        self.assertIn("<title>Engel Oranı Bulma (Kılavuza Göre)", govde)
        self.assertIn("Engel Oranı Bulma", govde)
        self.assertIn("Balthazard Hesaplama", govde)
        self.assertIn('href="http://127.0.0.1:8765/arac2"', govde)
        self.assertNotIn('href="/arac2"', govde)
        self.assertIn("Arama 3 karakterden sonra çalışır", govde)
        self.assertIn(ALT_BILGI, govde)
        self.assertIn("Resmî engelli sağlık kurulu raporu yerine geçmez", govde)

    def test_html_harici_bagimlilik_yok(self):
        html = self.html.lower()
        for iz in ("cdn.", "googleapis", "unpkg", "jsdelivr", "@import", 'src="http'):
            self.assertNotIn(iz, html)

    def test_html_yasak_ibare_icermez(self):
        for ibare in YASAK:
            self.assertNotIn(ibare, self.html.lower())

    def test_html_aktarim_notu(self):
        self.assertIn("otomatik aktarılmaz", self.html)
        self.assertIn("Bu kayıt zaten listede.", self.html)

    def test_html_kopyalama_yedegi_ve_klavye_erisimi(self):
        self.assertIn("function yedekKopyala(metin)", self.html)
        self.assertIn('document.execCommand("copy")', self.html)
        self.assertIn("Kopyalama başarısız oldu. Listeyi seçip elle kopyalayabilirsiniz.", self.html)
        self.assertIn(":focus-visible", self.html)
        self.assertIn('id="sepet-temizle">Listeyi temizle</button>', self.html)

    # --- sağlık / bölüm / gezinme ------------------------------------------

    def test_saglik_ucu(self):
        durum, tur, veri = self._json("/saglik")
        self.assertEqual(durum, 200)
        self.assertTrue(veri["ok"])
        self.assertEqual(veri["kayit"], 424)
        self.assertEqual(veri["belirsiz"], 16)
        self.assertEqual(veri["bolumler"], ["Ruh Sağlığı", "Deri", "Hematoloji", "KBB", "Kalp-Damar"])

    def test_bolumler_ucu(self):
        veri = self.bolumler
        self.assertTrue(veri["ok"])
        self.assertEqual(len(veri["bolumler"]), 5)
        sayilar = {b["kisa"]: b["kayit_sayisi"] for b in veri["bolumler"]}
        self.assertEqual(sayilar, {"Ruh Sağlığı": 56, "Deri": 142, "Hematoloji": 78, "KBB": 87, "Kalp-Damar": 61})
        self.assertTrue(any("GÖRME" in k for k in veri["kapsam_disi"]))

    def test_gezinme_duzeyleri(self):
        sayilar = {ad: len(veri["gruplar"]) for ad, veri in self.gezinme.items()}
        self.assertEqual(
            sayilar,
            {"ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR": 6, "DERİ": 15,
             "HEMATOLOJİK HASTALIKLAR": 10, "KULAK BURUN BOĞAZ": 7, "KARDİYOVASKÜLER SİSTEM": 9},
        )
        toplam = sum(len(g["hastaliklar"]) for v in self.gezinme.values() for g in v["gruplar"])
        self.assertEqual(toplam, 102)

    def test_gezinme_tek_kayitli_gruplar(self):
        tekli = sorted(
            h["seviyeler"][0]["id"]
            for v in self.gezinme.values()
            for g in v["gruplar"]
            for h in g["hastaliklar"]
            if h["tek_kayit"]
        )
        self.assertEqual(
            tekli,
            ["D-013", "D-014", "D-017", "D-049", "D-062", "D-075", "D-086",
             "D-134", "H-056", "K-082", "V-042"],
        )
        for v in self.gezinme.values():
            for g in v["gruplar"]:
                for h in g["hastaliklar"]:
                    if h["tek_kayit"]:
                        self.assertEqual(len(h["seviyeler"]), 1, h["anahtar"])

    def test_bilinmeyen_bolum_404(self):
        durum, _, veri = self._json("/api/gezinme?bolum=YOK")
        self.assertEqual(durum, 404)
        self.assertFalse(veri["ok"])
        durum, _, veri = self._json("/api/ara?metin=anemi&bolum=YOK")
        self.assertEqual(durum, 404)
        self.assertFalse(veri["ok"])

    # --- arama --------------------------------------------------------------

    def test_arama_uc_karakter_esigi(self):
        durum, _, veri = self._json("/api/ara?metin=ab")
        self.assertEqual(durum, 200)
        self.assertEqual(veri["sonuclar"], [])
        self.assertEqual(veri["belirsizler"], [])
        self.assertIn("3 karakter", veri["mesaj"])

    def test_arama_turkce_duyarsiz(self):
        _, _, kucuk = self._json("/api/ara?metin=psoriazis")
        _, _, buyuk = self._json("/api/ara?metin=" + urllib.parse.quote("PSORİASİS"))
        self.assertTrue(kucuk["sonuclar"])
        self.assertEqual(
            [s["id"] for s in kucuk["sonuclar"]],
            [s["id"] for s in buyuk["sonuclar"]],
        )

    def test_arama_bolum_on_filtresi(self):
        _, _, tumu = self._json("/api/ara?metin=anemi")
        _, _, deri = self._json("/api/ara?metin=anemi&bolum=" + urllib.parse.quote("DERİ"))
        _, _, deri2 = self._json("/api/ara?metin=anemi&bolum=" + urllib.parse.quote("Deri"))
        self.assertTrue(all(s["bolum"] == "DERİ" for s in deri["sonuclar"]))
        self.assertEqual([s["id"] for s in deri["sonuclar"]],
                         [s["id"] for s in deri2["sonuclar"]])
        self.assertLessEqual(len(deri["sonuclar"]), len(tumu["sonuclar"]))

    def test_arama_tam_erisim(self):
        """Kabul kriteri 1: her kayıt aramayla bulunabilir."""
        for kimlik in ("H-065", "D-013", "Z-005", "D-001", "H-074", "Z-056"):
            kayit = self.katalog.kayit(kimlik)
            sorgu = kayit.ad if len(kayit.ad) >= 3 else kayit.seviye
            _, _, veri = self._json("/api/ara?metin=" + urllib.parse.quote(sorgu))
            self.assertIn(kimlik, [s["id"] for s in veri["sonuclar"]], sorgu)

    def test_bos_sonuc_mesaji(self):
        durum, _, veri = self._json("/api/ara?metin=zzzz")
        self.assertEqual(durum, 200)
        self.assertEqual(veri["sonuclar"], [])
        self.assertEqual(veri["mesaj"], "“zzzz” için sonuç bulunamadı")
        self.assertEqual(veri["ipucu"], {"yazim": BOS_YAZIM, "kapsam": BOS_KAPSAM})

    def test_belirsiz_arama(self):
        _, _, veri = self._json("/api/ara?metin=fanconi")
        self.assertEqual([b["id"] for b in veri["belirsizler"]], ["X-H02", "X-H03"])
        self.assertNotIn("X-H01", [b["id"] for b in veri["belirsizler"]])
        self.assertEqual(
            veri["belirsizler"][0]["sorun"],
            SORUN_CUMLELERI["hiyerarsi_belirsiz"],
        )

    # --- sonuç --------------------------------------------------------------

    def test_tum_sonuclar_zorunlu_alanlari_tasir(self):
        self.assertEqual(len(self.sonuclar), 424)
        for kayit in self.katalog.kayitlar:
            veri = self.sonuclar[kayit.id]
            self.assertTrue(veri["ok"], kayit.id)
            self.assertEqual(veri["tur"], "sonuc")
            self.assertEqual(veri["oran"]["ham"], kayit.oran)
            self.assertEqual(veri["oran"]["etiket"], ORAN_ETIKETI)
            self.assertEqual(veri["kaynak"],
                             "Kaynak: EK-2, sayfa %d · kayıt %s" % (kayit.sayfa, kayit.id))
            self.assertEqual(veri["kisit_basligi"],
                             "%s (%d)" % (KISIT_BASLIGI, len(kayit.kisit)))
            self.assertEqual([k["kod"] for k in veri["kisitlar"]], list(kayit.kisit))
            self.assertNotIn(TIRE, veri["ad"])
            self.assertNotIn(TIRE, veri["seviye"])
            self.assertNotIn(TIRE, veri["kaynak_not"])

    def test_tek_kayitli_gruplarda_seviye_adimi_yok(self):
        for kimlik in ("D-013", "D-014", "D-017", "D-049", "D-062", "D-075",
                       "D-086", "D-134", "H-056", "K-082", "V-042"):
            veri = self.sonuclar[kimlik]
            self.assertTrue(veri["tek_kayit"], kimlik)
            self.assertFalse(veri["seviye_adimi"], kimlik)
            self.assertEqual(veri["tek_seviye_notu"], TEK_SEVIYE_NOTU, kimlik)
        for kimlik in ("Z-005", "D-001", "H-065", "Z-056"):
            veri = self.sonuclar[kimlik]
            self.assertFalse(veri["tek_kayit"], kimlik)
            self.assertTrue(veri["seviye_adimi"], kimlik)
            self.assertIsNone(veri["tek_seviye_notu"], kimlik)

    def test_h065_seviyesi_ayracdan_gelir(self):
        veri = self.sonuclar["H-065"]
        self.assertEqual(veri["ad"], "Kronik nötropeniler")
        self.assertEqual(veri["seviye"], "1- Ağır (Kostmann sendromu)")
        self.assertFalse(veri["tek_kayit"])
        self.assertEqual(veri["oran"]["gosterim"], "80")

    def test_oran_sifir_ve_yuz(self):
        sifir = self.sonuclar["Z-022"]
        self.assertEqual(sifir["oran"]["gosterim"], "0")
        self.assertTrue(sifir["sifir"])
        self.assertEqual(sifir["sifir_aciklama"], SIFIR_ACIKLAMA)
        yuz = self.sonuclar["Z-005"]
        self.assertEqual(yuz["oran"]["gosterim"], "100")
        self.assertFalse(yuz["sifir"])
        self.assertIsNone(yuz["sifir_aciklama"])

    def test_kisit_metinleri_birebir(self):
        gorulen = set()
        for veri in self.sonuclar.values():
            for kisit in veri["kisitlar"]:
                tur, onem, ikon, aciklama = KISIT_BEKLE[kisit["kod"]]
                self.assertEqual(kisit["tur"], tur)
                self.assertEqual(kisit["onem"], onem)
                self.assertEqual(kisit["ikon"], ikon)
                self.assertEqual(kisit["aciklama"], aciklama)
                beklenen_ton = "kirmizi" if kisit["kod"] in ("R-VERGI", "R-REMISYON") else (
                    "amber" if onem == "Orta" else "notr")
                self.assertEqual(kisit["ton"], beklenen_ton)
                gorulen.add(kisit["kod"])
        self.assertEqual(gorulen, set(KISIT_BEKLE))

    def test_r_vergi_34_kayitta(self):
        vergi = [k for k in self.sonuclar if any(
            x["kod"] == "R-VERGI" for x in self.sonuclar[k]["kisitlar"])]
        self.assertEqual(len(vergi), 34)

    def test_yas_bloku_her_sonucta_ve_orani_degistirmez(self):
        for kimlik in ("Z-005", "D-001", "H-065"):
            veri = self.sonuclar[kimlik]
            blok = veri["yas_bloku"]
            self.assertEqual(blok["baslik"], YAS_BASLIK)
            self.assertEqual(blok["ornek"], YAS_ORNEK)
            self.assertIn("%10", blok["metin"])
            self.assertIn("düz toplama", blok["metin"])
            self.assertIn("30692", blok["kaynak"])
            self.assertEqual(veri["oran"]["ham"], self.katalog.kayit(kimlik).oran)

    def test_bolum_notu_yalniz_hematolojide(self):
        for kayit in self.katalog.kayitlar:
            veri = self.sonuclar[kayit.id]
            if kayit.bolum == "HEMATOLOJİK HASTALIKLAR":
                self.assertIsNotNone(veri["bolum_notu"], kayit.id)
                self.assertEqual(veri["bolum_notu"]["baslik"], BOLUM_NOTU_BASLIK)
                self.assertEqual(veri["bolum_notu"]["metin"], BOLUM_NOTU_METIN)
                self.assertNotIn(veri["bolum_notu"]["baslik"],
                                 [k["kod"] for k in veri["kisitlar"]])
            else:
                self.assertIsNone(veri["bolum_notu"], kayit.id)

    def test_nakil_kaydinda_bolum_notu_ve_kisit_birlikte(self):
        veri = self.sonuclar["H-068"]
        self.assertIn("R-NAKIL", [k["kod"] for k in veri["kisitlar"]])
        self.assertIsNotNone(veri["bolum_notu"])

    # --- belirsiz / çözülen -------------------------------------------------

    def test_belirsiz_ekrani_oran_gostermez(self):
        self.assertEqual(len(self.belirsiz_ekran), 16)
        for kimlik, veri in self.belirsiz_ekran.items():
            self.assertTrue(veri["ok"], kimlik)
            self.assertEqual(veri["tur"], "belirsiz")
            self.assertNotIn("oran", veri)
            self.assertNotIn("kisitlar", veri)
            self.assertNotIn("kisa_etiket", veri)
            self.assertEqual(veri["mesaj"], BELIRSIZ_MESAJ)
            self.assertIn(veri["sorun"], SORUN_CUMLELERI.values())
            self.assertTrue(veri["kaynak_notu"].startswith("Kaynak notu (EK-2 s."))
            self.assertNotIn(TIRE, veri["ad"])
            self.assertNotIn(TIRE, json.dumps(veri, ensure_ascii=False))

    def test_cozulen_satirlar_sonuc_donmez(self):
        for belirsiz_id, katalog_id in ko.BEKLENEN_COZULEN.items():
            durum, _, _ = self._json("/api/kayit/" + urllib.parse.quote(belirsiz_id))
            self.assertEqual(durum, 404, belirsiz_id)
            durum, _, _ = self._json("/api/belirsiz/" + urllib.parse.quote(katalog_id))
            self.assertEqual(durum, 404, katalog_id)
            self.assertIn(katalog_id, self.sonuclar)
        _, _, veri = self._json("/api/ara?metin=fanconi")
        self.assertNotIn("X-H01", json.dumps(veri, ensure_ascii=False))

    def test_bilinmeyen_kayit_404(self):
        for yol in ("/api/kayit/YOK-999", "/api/belirsiz/X-Z01", "/api/yok"):
            durum, _, veri = self._json(yol)
            self.assertEqual(durum, 404, yol)
            self.assertFalse(veri["ok"], yol)

    def test_post_reddedilir(self):
        durum, _, govde = self._istek("/api/hesapla", veri=b'{"oranlar":[40]}')
        self.assertEqual(durum, 405)
        self.assertFalse(json.loads(govde.decode("utf-8"))["ok"])

    # --- ortak sınırlar -----------------------------------------------------

    def test_yasak_ibareler_yanitlarda_yok(self):
        toplu = [self.html]
        toplu.append(json.dumps(self.bolumler, ensure_ascii=False))
        toplu.append(json.dumps(self.gezinme, ensure_ascii=False))
        toplu.append(json.dumps(self.sonuclar, ensure_ascii=False))
        toplu.append(json.dumps(self.belirsiz_ekran, ensure_ascii=False))
        metin = "\\n".join(toplu).lower()
        for ibare in YASAK:
            self.assertNotIn(ibare, metin, ibare)

    def test_katalog_dosyalari_degismedi(self):
        self.assertEqual(self._dosya_durumu(), self.dosya_durumu)
        self.assertEqual(len(self.sonuclar), len(self.katalog.kayitlar))
        self.assertEqual(self._dosya_durumu(), self.dosya_durumu)


if __name__ == "__main__":
    unittest.main(verbosity=2)
