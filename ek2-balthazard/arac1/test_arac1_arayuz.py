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
        self.assertIn('id="model-bolum-listesi"', html)
        self.assertIn("position:sticky", html)
        self.assertIn("grid-row:2", html)
        self.assertIn("grid-auto-flow:column", html)
        self.assertIn("ozelHesaplamalariCiz", html)
        self.assertNotIn("Hakkında", html)
        self.assertNotIn("v2.0", html)

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
