# -*- coding: utf-8 -*-
"""``katalog_okuyucu`` testleri — salt okunur yükleme ve §3.4 değişmezleri.

Çalıştırma (depo kökünden):

    python -m unittest discover -s ek2-balthazard -p "test_katalog_okuyucu.py" -v

Testler gerçek ``veri/`` dosyalarını **yalnız okur**; bozulma senaryoları geçici
klasördeki kopyalar üzerinde çalışır, depodaki dosyalara yazılmaz.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import katalog_okuyucu as ko

VERI = Path(__file__).resolve().parent / "veri"
KATALOG = VERI / "katalog.json"
BELIRSIZ = VERI / "belirsiz.json"


class YuklemeTestleri(unittest.TestCase):
    """Sayı, dağılım ve kimlik değişmezleri."""

    @classmethod
    def setUpClass(cls):
        cls.katalog = ko.yukle()

    def test_kesin_ve_toplam_sayilar(self):
        self.assertEqual(len(self.katalog.kayitlar), 424)
        acik = [b for b in self.katalog.belirsiz if b.durum == "belirsiz"]
        cozulen = [b for b in self.katalog.belirsiz if b.durum == "cozuldu"]
        self.assertEqual(len(acik), 16)
        self.assertEqual(len(cozulen), 11)
        self.assertEqual(len(acik) + len(self.katalog.kayitlar), 440)

    def test_bolum_dagilimi_ve_kisa_adlar(self):
        dagilim = {b.ad: len(b.kayitlar) for b in self.katalog.bolumler}
        self.assertEqual(
            dagilim,
            {
                "ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR": 56,
                "DERİ": 142,
                "HEMATOLOJİK HASTALIKLAR": 78,
                "KULAK BURUN BOĞAZ": 87,
                "KARDİYOVASKÜLER SİSTEM": 61,
            },
        )
        # Kisa adlar: BOLUM_KISA_ADLARI'nya varsayılan full name ile döndürür
        self.assertEqual(
            [b.kisa for b in self.katalog.bolumler],
            ["Ruh Sağlığı", "Deri", "Hematoloji", "KBB", "Kalp-Damar"],
        )

    def test_gezinme_duzeyleri(self):
        """DERİ 15 grup, Z 6 başlık, H 10 başlık, K 7 başlık, V 9 başlık, toplam 102 hastalık (§3.7)."""
        sayilar = {b.kisa: len(b.gruplar) for b in self.katalog.bolumler}
        self.assertEqual(sayilar, {"Ruh Sağlığı": 6, "Deri": 15, "Hematoloji": 10, "KBB": 7, "Kalp-Damar": 9})
        hastalik = sum(len(g.hastaliklar) for b in self.katalog.bolumler for g in b.gruplar)
        self.assertEqual(hastalik, 102)

    def test_kv_grup_adlari_kod_degil_insan_okur_etikettir(self):
        beklenen = {
            "KBB": {
                "K-ISI": "İşitme (Tablo 2 hesaplama)",
                "K-KON": "Konuşma (Tablo 5 hesaplama)",
                "K-DEN": "Denge (vestibüler)",
                "K-YUZ": "Yüz arızaları",
                "K-HAV": "Hava yolu defektleri",
                "K-KOK": "Koku ve tat duyusu kaybı",
                "K-YUT": "Çiğneme ve yutma",
            },
            "Kalp-Damar": {
                "V-ARI": "Aritmiler",
                "V-PUH": "Pulmoner hipertansiyon",
                "V-HIP": "Hipertansiyon",
                "V-PER": "Perikard hastalıkları",
                "V-HKM": "Hipertrofik kardiyomiyopati",
                "V-KY": "Kalp yetmezliği",
                "V-DKH": "Doğuştan kalp hastalıkları (DKH)",
                "V-KHK": "Edinsel kalp hastalıkları",
                "V-DMR": "Damar hastalıkları",
            },
        }
        for bolum in self.katalog.bolumler:
            if bolum.kisa not in beklenen:
                continue
            adlar = {grup.anahtar.removeprefix("baslik:"): grup.ad for grup in bolum.gruplar}
            self.assertEqual(adlar, beklenen[bolum.kisa])
            for grup in bolum.gruplar:
                self.assertNotEqual(grup.ad, grup.kayitlar[0].grup)

    def test_tek_kayitli_gruplar(self):
        tekli = sorted(
            h.kayitlar[0].id
            for b in self.katalog.bolumler
            for g in b.gruplar
            for h in g.hastaliklar
            if h.tek_kayit
        )
        self.assertEqual(
            tekli,
            ["D-013", "D-014", "D-017", "D-049", "D-062", "D-075", "D-086", "D-134", "H-056", "K-082", "V-042"],
        )
        for bolum in self.katalog.bolumler:
            for grup in bolum.gruplar:
                for hastalik in grup.hastaliklar:
                    self.assertEqual(hastalik.tek_kayit, len(hastalik.kayitlar) == 1)

    def test_oran_araligi_ve_tam_sayi(self):
        for kayit in self.katalog.kayitlar:
            self.assertIsInstance(kayit.oran, int)
            self.assertGreaterEqual(kayit.oran, 0)
            self.assertLessEqual(kayit.oran, 100)
        self.assertEqual(sorted([k.id for k in self.katalog.kayitlar if k.oran == 100]), ["V-008", "V-012", "V-021", "V-025", "V-037", "V-041", "Z-005"])
        self.assertEqual(sum(1 for k in self.katalog.kayitlar if k.oran == 0), 17)

    def test_hastalik_alt_tur_tekil(self):
        ciftler = [(k.hastalik, k.alt_tur) for k in self.katalog.kayitlar]
        self.assertEqual(len(ciftler), len(set(ciftler)))

    def test_kimlikler_kesintisiz_ve_x_yok(self):
        for kayit in self.katalog.kayitlar:
            self.assertFalse(kayit.id.startswith("X-"), kayit.id)
        for onek, sayi in (("Z", 56), ("D", 142), ("H", 78)):
            numaralar = sorted(
                int(k.id.split("-")[1]) for k in self.katalog.kayitlar if k.id.startswith(onek + "-")
            )
            self.assertEqual(numaralar, list(range(1, sayi + 1)), onek)

    def test_cozulen_kayitlar_katalogda_bir_kez(self):
        for belirsiz_id, katalog_id in ko.BEKLENEN_COZULEN.items():
            self.assertIn(katalog_id, self.katalog.id_ile)
            self.assertNotIn(belirsiz_id, self.katalog.id_ile)
        for belirsiz_id in ko.BEKLENEN_BELIRSIZ_IDLER:
            self.assertIsNone(self.katalog.kayit(belirsiz_id))


class TuretilmisAlanTestleri(unittest.TestCase):
    """§3.3 / §3.9 — rozet, seviye ve ``—`` yutma."""

    @classmethod
    def setUpClass(cls):
        cls.katalog = ko.yukle()

    def test_tire_hicbir_ekranda_gorunmez(self):
        for kayit in self.katalog.kayitlar:
            self.assertNotIn("—", kayit.seviye, kayit.id)
            self.assertTrue(kayit.seviye.strip(), kayit.id)

    def test_tire_kayitlari_beklenen_kumeyle_ayni(self):
        """Veride 6 `—` var; ekran etiketi başka yerden gelir."""
        ham = []
        with open(KATALOG, encoding="utf-8") as dosya:
            for satir in json.load(dosya)["kayitlar"]:
                if satir["alt_tur"].strip() == "—":
                    ham.append(satir["id"])
        self.assertEqual(sorted(ham), list(ko.BEKLENEN_TIRE_IDLER))

    def test_h065_seviyesi_hastalik_ayracindan(self):
        kayit = self.katalog.kayit("H-065")
        self.assertEqual(kayit.seviye, "1- Ağır (Kostmann sendromu)")
        self.assertEqual(kayit.ad, "Kronik nötropeniler")
        self.assertEqual(kayit.rozet, "VIII")
        grup = next(
            g for b in self.katalog.bolumler if b.kisa == "Hematoloji" for g in b.gruplar
            if kayit in g.kayitlar
        )
        self.assertEqual(len(grup.kayitlar), 3)

    def test_tek_kayitli_tire_kayitlari_tek_oran_etiketi(self):
        for kimlik in ("D-013", "D-014", "D-017", "D-062", "H-056"):
            self.assertEqual(self.katalog.kayit(kimlik).seviye, "tek oran", kimlik)

    def test_rozet_ve_ad_ayrilir(self):
        kayit = self.katalog.kayit("H-074")
        self.assertEqual(kayit.rozet, "I-A")
        self.assertTrue(kayit.ad.startswith("Aplastik anemi"), kayit.ad)
        z = self.katalog.kayit("Z-005")
        self.assertEqual(z.rozet, "I")
        self.assertEqual(z.ad, "Zekâ işlev bozuklukları")


class AramaTestleri(unittest.TestCase):
    """§3.6 — Türkçe duyarsız arama."""

    @classmethod
    def setUpClass(cls):
        cls.katalog = ko.yukle()

    def test_uc_karakterden_once_calismaz(self):
        self.assertEqual(self.katalog.ara("ab"), ())
        self.assertEqual(self.katalog.belirsiz_ara("ab"), ())
        self.assertIsInstance(self.katalog.ara("abc"), tuple)

    def test_turkce_duyarsiz(self):
        kucuk = {k.id for k in self.katalog.ara("psoriazis")}
        buyuk = {k.id for k in self.katalog.ara("PSORİASİS")}
        self.assertTrue(kucuk)
        self.assertEqual(kucuk, buyuk)

    def test_aksan_ve_i_katlama(self):
        self.assertEqual(
            {k.id for k in self.katalog.ara("sıtma")},
            {k.id for k in self.katalog.ara("sitma")},
        )
        self.assertEqual(
            {k.id for k in self.katalog.ara("işitme")},
            {k.id for k in self.katalog.ara("isitme")},
        )

    def test_276_kaydin_tamami_bulunabilir(self):
        bulunamayan = [
            k.id
            for k in self.katalog.kayitlar
            if k.id not in {x.id for x in self.katalog.ara(k.hastalik[:20])}
        ]
        self.assertEqual(bulunamayan, [])

    def test_bolum_on_filtresi(self):
        tumu = self.katalog.ara("anemi")
        deri = self.katalog.ara("anemi", "DERİ")
        self.assertTrue(all(k.bolum == "DERİ" for k in deri))
        self.assertLessEqual(len(deri), len(tumu))
        self.assertEqual(len(deri), sum(1 for k in tumu if k.bolum == "DERİ"))
        self.assertEqual(self.katalog.ara("anemi", "Deri"), deri)

    def test_belirsiz_arama_cozulenleri_dondurmez(self):
        sonuc = self.katalog.belirsiz_ara("fanconi")
        self.assertEqual([s.id for s in sonuc], ["X-H02", "X-H03"])
        self.assertTrue(all(s.durum == "belirsiz" for s in sonuc))
        for satir in self.katalog.belirsiz_ara("anemi"):
            self.assertEqual(satir.durum, "belirsiz")

    def test_belirsiz_sozlukte_oran_yok(self):
        satir = self.katalog.belirsiz_kayit("X-D03")
        self.assertIsNotNone(satir)
        self.assertNotIn("oran", satir.sozluk())
        self.assertEqual(
            satir.sorun_cumlesi,
            "Bu satır bağımsız oran değil, başka oranlara eklenen bir kural.",
        )


class KisitTestleri(unittest.TestCase):
    """§3.11 — kısıt kodları ve sayıları."""

    @classmethod
    def setUpClass(cls):
        cls.katalog = ko.yukle()

    def test_kisit_kodlari_gecerli(self):
        for kayit in self.katalog.kayitlar:
            for kod in kayit.kisit:
                self.assertIn(kod, ko.GECERLI_KISIT_KODLARI, kayit.id)
            self.assertEqual(len(set(kayit.kisit)), len(kayit.kisit), kayit.id)

    def test_kisit_sayilari(self):
        sayim = {kod: 0 for kod in ko.GECERLI_KISIT_KODLARI}
        for kayit in self.katalog.kayitlar:
            for kod in kayit.kisit:
                sayim[kod] += 1
        self.assertEqual(sayim["R-VERGI"], 34)
        self.assertEqual(sayim["R-YILLIK"], 142)
        self.assertEqual(sayim["R-NAKIL"], 6)
        self.assertEqual(sum(1 for k in self.katalog.kayitlar if k.kisit), 182)
        self.assertEqual(sum(1 for k in self.katalog.kayitlar if not k.kisit), 242)


class SaltOkunurlukTestleri(unittest.TestCase):
    """§3.17/8 — dosyalar okuma sırasında değişmez; bozulma sessiz geçilmez."""

    def test_yukleme_dosyalara_yazmaz(self):
        once = {yol: (yol.stat().st_mtime_ns, yol.stat().st_size) for yol in (KATALOG, BELIRSIZ)}
        katalog = ko.yukle()
        katalog.ara("anemi")
        sonra = {yol: (yol.stat().st_mtime_ns, yol.stat().st_size) for yol in (KATALOG, BELIRSIZ)}
        self.assertEqual(once, sonra)

    def test_eksik_dosya_hata_verir(self):
        with tempfile.TemporaryDirectory() as klasor:
            with self.assertRaises(ko.KatalogHatasi):
                ko.yukle(KATALOG, Path(klasor) / "yok.json")

    def test_bozuk_json_hata_verir(self):
        with tempfile.TemporaryDirectory() as klasor:
            bozuk = Path(klasor) / "bozuk.json"
            bozuk.write_text("{ bozuk", encoding="utf-8")
            with self.assertRaises(ko.KatalogHatasi):
                ko.yukle(bozuk, BELIRSIZ)

    def test_bozulmus_kopya_sessiz_gecilmez(self):
        with tempfile.TemporaryDirectory() as klasor:
            kopya = Path(klasor) / "katalog.json"
            shutil.copyfile(KATALOG, kopya)
            veri = json.loads(kopya.read_text(encoding="utf-8"))
            veri["kayitlar"] = veri["kayitlar"][:-1]  # 275 kayıt
            kopya.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ko.KatalogHatasi):
                ko.yukle(kopya, BELIRSIZ)
            # Depodaki asıl dosya değişmedi
            self.assertEqual(len(ko.yukle().kayitlar), 424)

    def test_katla_kurallari(self):
        self.assertEqual(ko.katla("İ"), "i")
        # `I → ı` adımından sonra aksan katlama `ı → i` yapar (simetrik arama).
        self.assertEqual(ko.katla("I"), "i")
        self.assertEqual(ko.katla("İŞİTME"), ko.katla("işitme"))
        self.assertEqual(ko.katla("ÇĞÖŞÜ"), "cgosu")
        self.assertEqual(ko.katla("psoriazis"), ko.katla("psoriasis"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
