# -*- coding: utf-8 -*-
"""Araç-2 prototipinin testleri (standart kütüphane; ek paket gerekmez).

Kapsam:
* ``gosterim_ekle()`` ham değerlere dokunmaz, G-1…G-4 kuralıyla metin üretir;
* ``/api/hesapla`` uç noktası ortak motoru çağırır (kopya hesap yok);
* motorun hata kodları **değiştirilmeden** geçer;
* bozuk istek transport düzeyinde 400 döner, motor sözleşmesine karışmaz;
* ``/`` ekranı UTF-8 HTML olarak sunulur.

Çalıştırma (bu klasörde):

    <python> -m unittest -v test_arac2
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import arac2_sunucu
from arac2_sunucu import gosterim_ekle


class GosterimEkle(unittest.TestCase):
    def test_ham_deger_degismez(self):
        sonuc = arac2_sunucu.balthazard({"oranlar": [33, 33], "yas": "65_ve_uzeri"})
        onceki = json.dumps(sonuc, sort_keys=True)
        gosterim = gosterim_ekle(sonuc)
        self.assertEqual(json.dumps(sonuc, sort_keys=True), onceki)
        self.assertEqual(sonuc["sonuc"]["deger"], 59.599)
        self.assertEqual(gosterim["sonuc"], "59,6")

    def test_adimlar_metinlestirilir(self):
        sonuc = arac2_sunucu.balthazard({"oranlar": [33, 33], "yas": "65_ve_uzeri"})
        gosterim = gosterim_ekle(sonuc)
        self.assertEqual(len(gosterim["adimlar"]), len(sonuc["adimlar"]))
        self.assertEqual([a["sonuc"] for a in gosterim["adimlar"]], ["33", "55,11", "59,6"])
        self.assertEqual(gosterim["adimlar"][-1]["onceki"], "55,11")

    def test_yuvarlama_uygulanmadi_kalir(self):
        sonuc = arac2_sunucu.balthazard({"oranlar": [40, 30], "yas": "65_alti"})
        gosterim_ekle(sonuc)
        self.assertIs(sonuc["yuvarlama"]["uygulandi"], False)
        self.assertIsNone(sonuc["yuvarlama"]["kural"])
        self.assertEqual(sonuc["sonuc"]["deger"], 58)


class Sunucu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), arac2_sunucu.Isleyici)
        cls.adres = "http://127.0.0.1:%d" % cls.sunucu.server_port
        cls.islec = threading.Thread(target=cls.sunucu.serve_forever, daemon=True)
        cls.islec.start()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()
        cls.sunucu.server_close()
        cls.islec.join(timeout=5)

    def _post(self, govde):
        istek = urllib.request.Request(
            self.adres + "/api/hesapla",
            data=govde,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(istek, timeout=5) as yanit:
            return yanit.status, json.loads(yanit.read().decode("utf-8"))

    def test_hesapla_ham_ve_gosterim(self):
        durum, veri = self._post(
            json.dumps({"oranlar": [40, 30], "yas": "65_ve_uzeri"}).encode("utf-8")
        )
        self.assertEqual(durum, 200)
        self.assertTrue(veri["ok"])
        self.assertEqual(veri["sonuc"]["deger"], 62.2)
        self.assertEqual(veri["gosterim"]["sonuc"], "62,2")
        self.assertTrue(veri["yas_eklemesi"]["uygulandi"])

    def test_65_alti_ek_yok(self):
        _, veri = self._post(
            json.dumps({"oranlar": [40], "yas": "65_alti"}).encode("utf-8")
        )
        self.assertEqual(veri["sonuc"]["deger"], 40)
        self.assertFalse(veri["yas_eklemesi"]["uygulandi"])
        self.assertEqual(veri["gosterim"]["sonuc"], "40")

    def test_motor_hatasi_aynen_gecer(self):
        _, veri = self._post(json.dumps({"oranlar": [], "yas": "65_alti"}).encode("utf-8"))
        self.assertFalse(veri["ok"])
        self.assertEqual(veri["hata"]["kod"], "E_ORAN_YOK")
        self.assertNotIn("gosterim", veri)

    def test_yas_eksik(self):
        _, veri = self._post(json.dumps({"oranlar": [40]}).encode("utf-8"))
        self.assertEqual(veri["hata"]["kod"], "E_YAS_SECILMEDI")

    def test_gecerli_json_sozluk_degilse_motor_hatasi_aynen_gecer(self):
        for govde in ([], 40, None):
            with self.subTest(govde=govde):
                _, veri = self._post(json.dumps(govde).encode("utf-8"))
                self.assertFalse(veri["ok"])
                self.assertEqual(veri["hata"]["kod"], "E_ORAN_TIP")
                self.assertEqual(veri["hata"]["alan"], "girdi")

    def test_html_baglantilar_ve_girdi_filtresi(self):
        with urllib.request.urlopen(self.adres + "/", timeout=5) as yanit:
            html = yanit.read().decode("utf-8")
        self.assertIn('href="http://127.0.0.1:8766/arac1"', html)
        self.assertIn("function oranFiltresiKur", html)
        self.assertIn("yalnız tam sayı kabul eder", html)
        for parca in ("id=\"eski-uyari\"", "id=\"yas-eki-satiri\"", "id=\"adimlar\"", "window.confirm"):
            self.assertIn(parca, html)

    def test_bozuk_govde_400(self):
        istek = urllib.request.Request(
            self.adres + "/api/hesapla",
            data=b"{bozuk",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as baglam:
            urllib.request.urlopen(istek, timeout=5)
        hata = baglam.exception
        try:
            self.assertEqual(hata.code, 400)
            veri = json.loads(hata.read().decode("utf-8"))
        finally:
            hata.close()
        self.assertFalse(veri["ok"])
        self.assertIn("mesaj", veri)

    def test_ekran_utf8_html(self):
        with urllib.request.urlopen(self.adres + "/", timeout=5) as yanit:
            self.assertEqual(yanit.status, 200)
            self.assertIn("text/html", yanit.headers["Content-Type"])
            self.assertIn("charset=utf-8", yanit.headers["Content-Type"])
            govde = yanit.read().decode("utf-8")
        self.assertIn("Balthazard Hesaplama", govde)
        self.assertIn("yaş aralığını seçin".lower(), govde.lower())

    def test_bilinmeyen_yol_404(self):
        with self.assertRaises(urllib.error.HTTPError) as baglam:
            urllib.request.urlopen(self.adres + "/yok", timeout=5)
        hata = baglam.exception
        try:
            self.assertEqual(hata.code, 404)
        finally:
            hata.close()

    def test_saglik(self):
        with urllib.request.urlopen(self.adres + "/saglik", timeout=5) as yanit:
            self.assertEqual(json.loads(yanit.read().decode("utf-8")), {"ok": True})


if __name__ == "__main__":
    unittest.main()
