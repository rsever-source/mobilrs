# -*- coding: utf-8 -*-
"""Araç-1 insan modeli, ek katalog ve özel tablo API testleri."""

from __future__ import annotations

import json
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import arac1_sunucu as a


class Arac1ArayuzTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), a.Isleyici)
        cls.port = cls.sunucu.server_address[1]
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()

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

    def test_insan_modeli_ve_masaustu_mobil_duzeni(self):
        html = self._al("/arac1").decode("utf-8")
        self.assertNotIn('id="model-bolum-listesi"', html)
        self.assertNotIn("modelBolumListesi", html)
        self.assertIn("position:sticky", html)
        self.assertIn("grid-row:2", html)
        self.assertIn('id="ozel-hesaplama-kutusu"', html)
        self.assertIn('<details class="kart" id="ozel-hesaplama-kutusu"', html)
        self.assertIn('class="insan-model-gorsel"', html)
        self.assertIn('id="model-secim-cagri"', html)
        self.assertIn("function modeliGuncelle(bolumAdi)", html)
        self.assertIn('id="yas-ek-goster" type="checkbox" aria-controls="yas-ek-bilgi"', html)
        self.assertNotIn('id="yas-ek-goster" type="checkbox" checked', html)
        self.assertNotIn("Vücut üzerindeki işaretleri seçerek ilgili hastalık bölümüne geçin.", html)
        self.assertIn("@media(max-width:520px)", html)
        self.assertIn("position:static", html)
        self.assertIn('<header class="site-header" role="banner">', html)
        self.assertIn('class="site-brand" href="/" aria-label="Engelli.me ana sayfa"', html)
        self.assertIn('id="siteAccessibilityToggle"', html)
        self.assertIn('id="siteAccessibilityPanel"', html)
        self.assertIn('class="site-mobile-home" href="/">Anasayfa</a>', html)
        self.assertIn('data-site-font="1.12"', html)
        self.assertIn('id="siteContrastToggle"', html)
        self.assertIn('id="siteDarkToggle"', html)
        self.assertIn('id="yas-ek-bilgi"', html)
        self.assertIn("ozelHesaplamalariCiz", html)
        self.assertIn("function hastaliklariCiz()", html)
        self.assertIn("satir.ad", html)
        self.assertIn("satir.seviye", html)
        self.assertIn("satir.kaynak", html)
        self.assertIn('id="listeyi-kopyala">Oranları kopyala</button>', html)
        self.assertNotIn('id="sepet-temizle"', html)
        self.assertNotIn("Seçimleri temizle", html)
        self.assertIn('id="listeyi-kopyala">Oranları kopyala</button>', html)
        self.assertIn("Araç-2'ye geç →", html)
        self.assertNotIn("İnsan Modeli</h2>", html)
        self.assertNotIn("Bölüme göre filtrele", html)
        self.assertIn("Araç-2'ye geç →", html)
        self.assertIn('return "%" + s.gosterim', html)
        self.assertNotIn("Alışverişe devam", html)
        self.assertNotIn('id="gruplar"', html)
        self.assertNotIn('id="gruplar-baslik"', html)
        self.assertNotIn("function grupSec(", html)
        self.assertIn('ek_kayit: grup.rozet === "EK-2"', html)
        self.assertNotIn("Hakkında", html)
        self.assertNotIn("v2.0", html)
        from pathlib import Path
        ana_uygulama = Path(__file__).resolve().parents[2] / "excel_vlookup_api.py"
        ana_html = ana_uygulama.read_text(encoding="utf-8")
        self.assertIn("<b>Hastalık Oranı Bulma</b>", ana_html)
        self.assertNotIn("<b>EK-2 Hastalık Oranı Bulma</b>", ana_html)

    def test_bolumler_ve_sayilar(self):
        data = self._json("/api/bolumler")
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["bolumler"]), 12)
        short = {x["kisa"]: x["kayit_sayisi"] for x in data["bolumler"]}
        self.assertEqual(short["Kalp-Damar"], 93)
        self.assertEqual(short["Sinir Sistemi"], 21)
        self.assertEqual(short["Sindirim"], 22)

    def test_ek_katalog_kaydi_acilir(self):
        data = self._json("/api/kayit/KV-001")
        self.assertTrue(data["ok"])
        self.assertEqual(data["id"], "KV-001")
        self.assertEqual(data["rozet"], "EK-2 ek kayıt")
        self.assertIn("kaynak", data)

    def test_yeni_bolum_gezinmesi_ve_arama(self):
        data = self._json("/api/gezinme?bolum=" + urllib.parse.quote("Sinir Sistemi"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["bolum"]["kayit_sayisi"], 21)
        search = self._json("/api/ara?metin=" + urllib.parse.quote("epilepsi") +
                            "&bolum=" + urllib.parse.quote("Sinir Sistemi"))
        self.assertTrue(search["ok"])
        self.assertTrue(any(x["id"].startswith("SN-") for x in search["sonuclar"]))

    def test_ozel_hesaplama_tablolari_ayri_verilir(self):
        data = self._json("/api/ozel-hesaplamalar")
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["ozel_hesaplamalar"]), 5)
        eye = next(x for x in data["ozel_hesaplamalar"] if x["id"] == "OZ-GOR-001")
        self.assertEqual(len(eye["tablolar"][0]["satirlar"]), 27)
        spine = next(x for x in data["ozel_hesaplamalar"] if x["id"] == "OZ-KIS-001")
        self.assertGreater(sum(len(t.get("satirlar", [])) for t in spine["tablolar"]), 70)


if __name__ == "__main__":
    unittest.main()
