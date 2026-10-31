# -*- coding: utf-8 -*-
"""Araç-1 arayüz eşlemesi testleri (kategori / alt başlık / pasif bölüm / eşanlamlı).

Çalıştırma (depo kökünden):

    python -m unittest discover -s ek2-balthazard/arac1 -p "test_arac1_arayuz.py" -v

Eşleme ``arac1.html`` içindeki ``<script type="application/json" id="arayuz-esleme">``
bloğundadır ve **yalnız görünümü** belirler. Kayıtların oranı/adı/sayfası hep API'den
gelir. Bu testler eşlemenin resmî Ek-2 kataloğuyla tutarlı kaldığını denetler:
hiçbir kesin kayıt kaybolmaz, hiçbiri iki yerde görünmez, belirsiz satırlar oran
almaz, eşanlamlılar yalnız doğrulanmış kayıt kimliklerine bağlıdır.
"""

from __future__ import annotations

import json
import re
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import arac1_sunucu as a  # noqa: E402  (sys.path'i kendisi kurar)

VERI = Path(__file__).resolve().parent.parent / "veri"

PASIF_ACIKLAMA = "Bu bölüm Araç-1'de henüz desteklenmiyor"

# Kullanıcının istediği eşanlamlılar (hepsi yapılandırmada bulunmalı).
ISTENEN_TERIMLER = (
    "talasemi", "sedef", "tssb", "travma sonrası stres bozukluğu",
    "zihinsel yetersizlik", "zekâ geriliği", "anoreksiya", "kemik iliği nakli",
    "smoldering miyelom", "aşırı terleme",
)

_KATLA = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
                        "â": "a", "î": "i", "û": "u"})


def katla(metin: str) -> str:
    """Tarayıcıdaki katla() ile aynı Türkçe duyarsız karşılaştırma."""
    t = metin.replace("İ", "i").replace("I", "ı").lower().translate(_KATLA)
    return re.sub(r"\s+", " ", t).strip()


class Arac1ArayuzTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), a.Isleyici)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()

        cls.html = cls._al("/arac1").decode("utf-8")
        blok = re.search(
            r'<script type="application/json" id="arayuz-esleme">\s*(.*?)\s*</script>',
            cls.html, re.S)
        assert blok, "arayuz-esleme bloğu bulunamadı"
        cls.esleme = json.loads(blok.group(1))

        cls.kayitlar = json.loads((VERI / "katalog.json").read_text(encoding="utf-8"))["kayitlar"]
        satirlar = json.loads((VERI / "belirsiz.json").read_text(encoding="utf-8"))["kayitlar"]
        cls.belirsiz = [s for s in satirlar if s["durum"] == "belirsiz"]
        cls.cozuldu = [s for s in satirlar if s["durum"] != "belirsiz"]
        cls.bolumler = json.loads(cls._al("/api/bolumler"))["bolumler"]
        cls.kisa_ad = {b["kisa"]: b["ad"] for b in cls.bolumler}

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()
        cls.sunucu.server_close()

    @classmethod
    def _al(cls, yol: str) -> bytes:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (cls.port, yol), timeout=10) as y:
            return y.read()

    @classmethod
    def _json(cls, yol: str) -> dict:
        return json.loads(cls._al(yol))

    def _maddeler(self):
        for b in self.esleme["bolumler"]:
            for ab in b["altBasliklar"]:
                for m in ab["maddeler"]:
                    yield b["bolum"], ab["ad"], m

    # --- bölümler ---------------------------------------------------------
    def test_surum_ve_bolum_adlari_tutarli(self):
        self.assertEqual(self.esleme["surum"], 1)
        yapilandirilan = [b["bolum"] for b in self.esleme["bolumler"]]
        self.assertEqual(yapilandirilan, ["Ruh Sağlığı", "Deri", "Hematoloji"])
        # KBB ve Kalp-Damar API'den doğrudan gösterilir; özel alt başlık
        # eşlemesi bulunmayan kayıtlar "Diğer kayıtlar" fallback'ine düşer.
        self.assertEqual(set(self.kisa_ad), {"Ruh Sağlığı", "Deri", "Hematoloji", "KBB", "Kalp-Damar"})
        self.assertIn('sonuc.push({ ad: "Diğer kayıtlar"', self.html)

    # --- kategori / alt başlık eşlemesi ----------------------------------
    def test_hicbir_kesin_kayit_kaybolmaz_ve_cift_gorunmez(self):
        kimlikler = [i for _, _, m in self._maddeler() for i in m["ids"]]
        self.assertEqual(len(kimlikler), len(set(kimlikler)), "bir kayıt birden fazla yerde")
        # Özel eşleme üç bölüm içindir; KBB ve Kalp-Damar API ağacından gelir.
        eslenen = {k["id"] for k in self.kayitlar if k["bolum"] in
                   {"ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR", "DERİ", "HEMATOLOJİK HASTALIKLAR"}}
        self.assertEqual(set(kimlikler), eslenen)
        self.assertEqual(len(kimlikler), len(eslenen))
        self.assertEqual(len(self.kayitlar), 424)

    def test_kayitlar_dogru_bolumde(self):
        bolum_of = {k["id"]: k["bolum"] for k in self.kayitlar}
        for bolum, _, m in self._maddeler():
            for kimlik in m["ids"]:
                self.assertEqual(bolum_of[kimlik], self.kisa_ad[bolum],
                                 "%s yanlış bölümde: %s" % (kimlik, bolum))

    def test_alt_basliklar_anlamli_ve_benzersiz(self):
        for b in self.esleme["bolumler"]:
            adlar = [ab["ad"] for ab in b["altBasliklar"]]
            self.assertEqual(len(adlar), len(set(adlar)), b["bolum"])
            for ad in adlar:
                self.assertTrue(ad.strip())
                self.assertIsNone(re.fullmatch(r"[IVXLC]+|\d+", ad.strip()),
                                  "Roma/sayı adı kullanıcıya gösterilmez: " + ad)
        for _, _, m in self._maddeler():
            self.assertTrue(m["ad"].strip())
            self.assertTrue(m["ids"] or m["belirsiz"], "boş madde: " + m["ad"])

    def test_maddelerdeki_seviye_etiketleri_ayirt_edilir(self):
        ad_of = {}
        for b in self.bolumler:
            for g in self._json("/api/gezinme?bolum=" + urllib.parse.quote(b["ad"]))["gruplar"]:
                for h in g["hastaliklar"]:
                    for s in h["seviyeler"]:
                        ad_of[s["id"]] = s["seviye"]
        for _, _, m in self._maddeler():
            etiketler = [ad_of[i] for i in m["ids"]]
            self.assertEqual(len(etiketler), len(set(etiketler)), m["ad"])

    # --- belirsiz kayıtlar ------------------------------------------------
    def test_belirsiz_kimlikler_tam_ve_cozulenler_haric(self):
        bel = [i for _, _, m in self._maddeler() for i in m["belirsiz"]]
        eslenen_belirsiz = {s["id"] for s in self.belirsiz if s["bolum"] in
                            {"ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR", "DERİ", "HEMATOLOJİK HASTALIKLAR"}}
        self.assertEqual(sorted(bel), sorted(eslenen_belirsiz))
        self.assertEqual(len(bel), len(set(bel)))
        for s in self.cozuldu:
            self.assertNotIn(s["id"], bel)

    def test_belirsiz_kayitlar_kesin_oran_uretmez(self):
        kesin = {k["id"] for k in self.kayitlar}
        for _, _, m in self._maddeler():
            for kimlik in m["belirsiz"]:
                self.assertNotIn(kimlik, kesin)
                self.assertNotIn(kimlik, m["ids"])
                yanit = self._json("/api/kayit/" + urllib.parse.quote(kimlik))
                self.assertEqual(yanit.get("tur"), "belirsiz", kimlik)
                self.assertNotIn("oran", yanit, kimlik)
                self.assertNotIn("kisitlar", yanit, kimlik)

    def test_belirlenen_belirsiz_maddeler_eslenmis(self):
        adlar = {m["ad"]: m for _, _, m in self._maddeler()}
        def bul(parca):
            bulunan = [m for ad, m in adlar.items() if parca.lower() in ad.lower()]
            self.assertEqual(len(bulunan), 1, parca)
            return bulunan[0]
        self.assertEqual(bul("Eritroderma")["ids"], [])
        self.assertEqual(bul("Pigment bozuklukları")["ids"], [])
        self.assertEqual(bul("Fankoni")["ids"], [])
        self.assertEqual(bul("şimdiki nöbet psikotik")["belirsiz"], ["X-Z03", "X-Z04"])
        self.assertEqual(len(bul("şimdiki nöbet psikotik")["ids"]), 1)
        self.assertIn("X-D01", bul("Kan damarlarının benign")["belirsiz"])
        self.assertIn("X-D02", bul("Hipertrofik skar")["belirsiz"])

    # --- pasif bölümler ---------------------------------------------------
    def test_pasif_bolumler(self):
        pasif = self.esleme["pasifBolumler"]
        self.assertEqual(len(pasif), 11)
        self.assertEqual(len(set(pasif)), 11)
        for ad in pasif:
            self.assertNotIn(ad, self.kisa_ad)
        for beklenen in ("Kas-İskelet Sistemi", "Romatizmal Hastalıklar",
                         "Onkoloji (Kanserler)", "Göz (Görme Sistemi)"):
            self.assertIn(beklenen, pasif)
        self.assertIn(PASIF_ACIKLAMA, self.html)

    def test_pasif_bolum_islevi_istek_yapmaz(self):
        govde = re.search(r"function pasifBolumleriKur\(\) \{.*?\n  \}\n", self.html, re.S)
        self.assertIsNotNone(govde)
        for yasak in ("fetch(", "json(", "kayitAc(", "ara(", "sepeteEkle("):
            self.assertNotIn(yasak, govde.group(0))

    # --- eşanlamlılar -----------------------------------------------------
    def test_istenen_esanlamlilar_var_ve_dogrulanamayan_yok(self):
        terimler = [katla(t) for e in self.esleme["esanlamlilar"] for t in e["terimler"]]
        self.assertEqual(len(terimler), len(set(terimler)), "yinelenen terim")
        for t in ISTENEN_TERIMLER:
            self.assertIn(katla(t), terimler, t)
        # "multipl miyelom" kaynak metinde geçmez; yalnız kaynakta geçen "myeloma" bağlanır.
        for t in terimler:
            self.assertNotIn("multipl", t)
        for riskli in ("kelebek hastalığı", "saç dökülmesi", "depresyon", "bulimiya", "yeme bozukluğu", "miyelom"):
            self.assertNotIn(katla(riskli), terimler, riskli)

    def test_esanlamlilar_gercek_kayitlara_baglidir(self):
        metin_of = {}
        for k in self.kayitlar:
            metin_of[k["id"]] = katla(k["hastalik"] + " " + str(k["alt_tur"]))
        for s in self.belirsiz:
            metin_of[s["id"]] = katla(s["hastalik"] + " " + str(s["alt_tur"]))
        for e in self.esleme["esanlamlilar"]:
            self.assertTrue(e["terimler"] and e["ids"], e)
            self.assertTrue(set(e["ids"]) <= set(metin_of), e)
            # Arama hedefi kaynak metinde geçmeli (doğrulanabilir karşılık).
            hedef = katla(e["ara"])
            self.assertTrue(any(hedef in metin_of[i] for i in e["ids"]),
                            "kaynakta doğrulanamadı: " + e["ara"])
            # Arama hedefi, bağlı kimliklerin hepsini döndürmeli.
            yanit = self._json("/api/ara?metin=" + urllib.parse.quote(e["ara"]))
            bulunan = {k["id"] for k in yanit["sonuclar"]} | {k["id"] for k in yanit["belirsizler"]}
            self.assertTrue(set(e["ids"]) <= bulunan, (e["ara"], set(e["ids"]) - bulunan))

    def test_belirsiz_baglantili_esanlamli_oran_vermez(self):
        for e in self.esleme["esanlamlilar"]:
            bel = [i for i in e["ids"] if i.startswith("X-")]
            if not bel:
                continue
            yanit = self._json("/api/ara?metin=" + urllib.parse.quote(e["ara"]))
            kesin = {k["id"] for k in yanit["sonuclar"]}
            for i in bel:
                self.assertNotIn(i, kesin)

    # --- ekran ------------------------------------------------------------
    def test_ekran_yedegi_ve_kapsam_siniri(self):
        self.assertIn("Diğer kayıtlar", self.html)          # eşlenmemiş kayıt kaybolmaz
        self.assertIn("Tüm bölümler", self.html)
        self.assertNotIn('type="checkbox"', self.html)       # 65 yaş ilavesi/anahtar yok
        self.assertNotIn("/api/hesapla", self.html)          # Araç-1 hesap yapmaz
        self.assertNotIn('src="http', self.html)


if __name__ == "__main__":
    unittest.main()