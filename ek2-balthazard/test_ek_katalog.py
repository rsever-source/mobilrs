# -*- coding: utf-8 -*-
"""EK-2 ek katalog ve özel hesaplama şeması doğrulamaları."""

import json
import unittest
from pathlib import Path

import katalog_okuyucu as ko

VERI = Path(__file__).resolve().parent / "veri"


class EkKatalogTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ek = json.loads((VERI / "katalog_ek2_ek.json").read_text(encoding="utf-8"))
        cls.ozel = json.loads((VERI / "ozel_hesaplamalar.json").read_text(encoding="utf-8"))

    def test_okuyucu_ek_dosyalarini_yukler(self):
        ek = ko.yukle_ek_katalog()
        ozel = ko.yukle_ozel_hesaplamalar()
        self.assertEqual(sum(len(b["kayitlar"]) for b in ek["bolumler"]), 136)
        self.assertEqual(len(ozel["ozel_hesaplamalar"]), 5)

    def test_ek_katalog_bolumleri_ve_kayitlar(self):
        bolumler = self.ek["bolumler"]
        self.assertEqual(len(bolumler), 8)
        kayitlar = [r for b in bolumler for r in b["kayitlar"]]
        self.assertEqual(len(kayitlar), 136)
        self.assertEqual(len({r["id"] for r in kayitlar}), len(kayitlar))
        for bolum in bolumler:
            self.assertTrue(bolum["ad"])
            self.assertTrue(bolum["kisa"])
            self.assertTrue(bolum["kayitlar"])
            for kayit in bolum["kayitlar"]:
                self.assertTrue(kayit["hastalik"])
                self.assertTrue(kayit["alt_tur"])
                self.assertIsInstance(kayit["sayfa"], int)
                self.assertIsInstance(kayit["oran"], int)
                self.assertGreaterEqual(kayit["oran"], 0)
                self.assertLessEqual(kayit["oran"], 100)

    def test_ozel_hesaplamalar_sabit_oran_gibi_temsil_edilmez(self):
        ozel = self.ozel["ozel_hesaplamalar"]
        self.assertGreaterEqual(len(ozel), 5)
        ids = [x["id"] for x in ozel]
        self.assertEqual(len(ids), len(set(ids)))
        goz = next(x for x in ozel if x["id"] == "OZ-GOR-001")
        self.assertEqual(goz["tur"], "formul")
        self.assertTrue(any("GSYO = 100" in a.get("formul", "") for a in goz["adimlar"]))
        self.assertTrue(goz["tablolar"])
        kas = [x for x in ozel if x["bolum"] == "KAS-İSKELET SİSTEMİ"]
        self.assertGreaterEqual(len(kas), 3)
        omurga = next(x for x in kas if x["id"] == "OZ-KIS-001")
        for tablo_index, beklenen in ((0, 5), (1, 5), (2, 5), (3, 31), (4, 16), (5, 17)):
            self.assertEqual(len(omurga["tablolar"][tablo_index]["satirlar"]), beklenen)
        self.assertEqual(len(goz["tablolar"][0]["satirlar"]), 27)
        self.assertTrue(all("uyari" in x for x in ozel))

    def test_romatoloji_ayri_resmi_ust_bolum_varsayilmaz(self):
        rom = next(x for x in self.ozel["ozel_hesaplamalar"] if x["id"] == "OZ-ROM-001")
        self.assertEqual(rom["tur"], "kaynak_hiyerarsisi")
        self.assertIn("ayrı bir üst bölüm", rom["hesaplama_kurali"])


if __name__ == "__main__":
    unittest.main()
