# -*- coding: utf-8 -*-
"""Ortak Balthazard motoru testleri.

Sözleşme: ``ORTAK-MOTOR-SOZLESME.md`` (0.3). Testler yalnız standart kütüphane
kullanır (``unittest``); ek paket gerekmez.

Çalıştırma (bu klasörde):

    <python> -m unittest -v test_balthazard_motoru

Kapsam: tek oran, çoklu oran + sıralama, %0/%100, tekrarlanan oranlar, 65 altı /
65 ve üzeri, ``yas_ekle`` tip kuralı, boş ve geçersiz girdiler, ham değer +
yuvarlama yapılmadığının doğrulanması, gösterim kuralı (G-1…G-4: en fazla 2
ondalık, yarı yukarı, sondaki sıfırlar atılır, ham değer korunur).
"""

import unittest

from balthazard_motoru import (
    DAYANAK,
    YAS_EKI_ORANI,
    bicimle_gosterim,
    balthazard,
)

YAS_ALTI = "65_alti"
YAS_USTU = "65_ve_uzeri"


def cagir(oranlar, yas=YAS_ALTI, **ek):
    """Testler için kısa yardımcı: sözleşme zarfını kurar."""
    girdi = {"oranlar": oranlar, "yas": yas}
    girdi.update(ek)
    return balthazard(girdi)


class SozlesmeVektorleri(unittest.TestCase):
    """Sözleşme §9'daki 13 vektör birebir geçmeli."""

    BASARI = [
        # (oranlar, yas, yas_ekle, beklenen)
        ([40], YAS_ALTI, True, 40),
        ([40, 30], YAS_ALTI, True, 58),
        ([40], YAS_USTU, True, 46),
        ([0], YAS_ALTI, True, 0),
        ([100], YAS_ALTI, True, 100),
        ([0, 40], YAS_ALTI, True, 40),
        ([100, 40], YAS_ALTI, True, 100),
        ([30, 40], YAS_ALTI, True, 58),
        ([40], YAS_USTU, False, 40),
    ]

    HATA = [
        ([], YAS_ALTI, "E_ORAN_YOK"),
        ([120], YAS_ALTI, "E_ORAN_ARALIK"),
        ([12.5], YAS_ALTI, "E_ORAN_TAMSAYI"),
        ([40], None, "E_YAS_SECILMEDI"),
    ]

    def test_vektor_1_9_birebir(self):
        for sira, (oranlar, yas, yas_ekle, beklenen) in enumerate(self.BASARI, start=1):
            with self.subTest(vektor=sira, oranlar=oranlar, yas=yas):
                sonuc = cagir(oranlar, yas, yas_ekle=yas_ekle)
                self.assertTrue(sonuc["ok"])
                self.assertEqual(sonuc["sonuc"]["deger"], beklenen)

    def test_vektor_10_13_birebir(self):
        for sira, (oranlar, yas, kod) in enumerate(self.HATA, start=10):
            with self.subTest(vektor=sira, oranlar=oranlar):
                sonuc = cagir(oranlar, yas)
                self.assertFalse(sonuc["ok"])
                self.assertEqual(sonuc["hata"]["kod"], kod)


class TekOran(unittest.TestCase):
    def test_tek_oran_kendisini_dondurur(self):
        for oran in (1, 10, 40, 55, 99):
            with self.subTest(oran=oran):
                self.assertEqual(cagir([oran])["sonuc"]["deger"], oran)

    def test_tek_oran_tam_sayi_tipi(self):
        deger = cagir([40])["sonuc"]["deger"]
        self.assertIsInstance(deger, int)
        self.assertNotIsInstance(deger, bool)

    def test_tek_oran_adim_sayisi_bir(self):
        sonuc = cagir([40])
        self.assertEqual(len(sonuc["adimlar"]), 1)
        self.assertEqual(sonuc["adimlar"][0]["tur"], "bileske")
        self.assertEqual(sonuc["adimlar"][0]["onceki"], 0)
        self.assertEqual(sonuc["adimlar"][0]["eklenen"], 40)
        self.assertEqual(sonuc["adimlar"][0]["sonuc"], 40)


class CokluOranVeSiralama(unittest.TestCase):
    def test_iki_oran_bileske(self):
        self.assertEqual(cagir([40, 30])["sonuc"]["deger"], 58)

    def test_siralama_buyukten_kucuge(self):
        sonuc = cagir([30, 40])
        self.assertEqual(sonuc["siralama"]["kural"], "buyukten_kucuge")
        self.assertEqual(sonuc["siralama"]["uygulanan"], [40, 30])
        self.assertEqual(sonuc["adimlar"][0]["eklenen"], 40)

    def test_girdi_sirasi_sonucu_degistirmez(self):
        self.assertEqual(
            cagir([30, 40])["sonuc"]["deger"], cagir([40, 30])["sonuc"]["deger"]
        )

    def test_uc_oran_bileske(self):
        # 50 -> 60 -> 64
        sonuc = cagir([10, 50, 20])
        self.assertEqual(sonuc["sonuc"]["deger"], 64)
        self.assertEqual(sonuc["siralama"]["uygulanan"], [50, 20, 10])

    def test_dort_oran_bileske(self):
        # 40 -> 58 -> 66.4 -> 69.76
        self.assertEqual(cagir([20, 40, 30, 10])["sonuc"]["deger"], 69.76)

    def test_adimlar_sirali_ve_tutarli(self):
        sonuc = cagir([40, 30, 20])
        adimlar = sonuc["adimlar"]
        self.assertEqual([a["sira"] for a in adimlar], [1, 2, 3])
        self.assertEqual(adimlar[0]["onceki"], 0)
        for onceki, sonraki in zip(adimlar, adimlar[1:]):
            self.assertEqual(sonraki["onceki"], onceki["sonuc"])
        self.assertEqual(adimlar[-1]["sonuc"], sonuc["sonuc"]["deger"])

    def test_girdi_listesi_degistirilmez(self):
        oranlar = [30, 40, 20]
        cagir(oranlar)
        self.assertEqual(oranlar, [30, 40, 20])

    def test_siralama_uygulanan_yeni_liste(self):
        oranlar = [30, 40]
        sonuc = cagir(oranlar)
        self.assertIsNot(sonuc["siralama"]["uygulanan"], oranlar)


class UcDegerler(unittest.TestCase):
    def test_sifir_etkisiz(self):
        self.assertEqual(cagir([0, 40])["sonuc"]["deger"], 40)
        self.assertEqual(cagir([40, 0])["sonuc"]["deger"], 40)

    def test_sifir_uyarisi(self):
        kodlar = [u["kod"] for u in cagir([0, 40])["uyarilar"]]
        self.assertIn("U_ORAN_SIFIR", kodlar)

    def test_yuz_kilitler(self):
        self.assertEqual(cagir([100, 40])["sonuc"]["deger"], 100)
        self.assertEqual(cagir([40, 100])["sonuc"]["deger"], 100)

    def test_yuz_uyarisi(self):
        kodlar = [u["kod"] for u in cagir([100, 40])["uyarilar"]]
        self.assertIn("U_ORAN_100", kodlar)

    def test_sifir_ve_yuz_birlikte(self):
        sonuc = cagir([0, 100])
        self.assertEqual(sonuc["sonuc"]["deger"], 100)
        kodlar = [u["kod"] for u in sonuc["uyarilar"]]
        self.assertIn("U_ORAN_SIFIR", kodlar)
        self.assertIn("U_ORAN_100", kodlar)

    def test_sifir_sifir(self):
        sonuc = cagir([0, 0])
        self.assertEqual(sonuc["sonuc"]["deger"], 0)
        self.assertTrue(sonuc["sonuc"]["tam_sayi_mi"])


class TekrarlananOranlar(unittest.TestCase):
    def test_tekrar_engellenmez_iki_giris_de_sayilir(self):
        # B-6: engelleme yok, her giriş hesaba katılır -> 40 + 60*40/100 = 64
        sonuc = cagir([40, 40])
        self.assertTrue(sonuc["ok"])
        self.assertEqual(sonuc["sonuc"]["deger"], 64)
        self.assertEqual(sonuc["siralama"]["uygulanan"], [40, 40])

    def test_tekrar_uyarisi_bir_kez(self):
        kodlar = [u["kod"] for u in cagir([40, 40])["uyarilar"]]
        self.assertEqual(kodlar.count("U_ORAN_TEKRAR"), 1)

    def test_tekrar_uc_giris(self):
        # 40 -> 64 -> 78.4
        self.assertEqual(cagir([40, 40, 40])["sonuc"]["deger"], 78.4)

    def test_tekrar_uyari_mesaji_sozlesmeye_uygun(self):
        uyari = [u for u in cagir([30, 30])["uyarilar"] if u["kod"] == "U_ORAN_TEKRAR"][0]
        self.assertEqual(
            uyari["mesaj"],
            "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir.",
        )


class YasKurali(unittest.TestCase):
    def test_65_ustu_yuzde_on_balthazard(self):
        self.assertEqual(cagir([40], YAS_USTU)["sonuc"]["deger"], 46)

    def test_65_alti_ek_yok(self):
        sonuc = cagir([40], YAS_ALTI)
        self.assertEqual(sonuc["sonuc"]["deger"], 40)
        self.assertFalse(sonuc["yas_eklemesi"]["uygulandi"])

    def test_65_ustu_ek_aritmetik_degil(self):
        # 80 + (100-80)*10/100 = 82 ; aritmetik +10 olsa 90 olurdu
        sonuc = cagir([80], YAS_USTU)
        self.assertEqual(sonuc["sonuc"]["deger"], 82)
        self.assertNotEqual(sonuc["sonuc"]["deger"], 90)

    def test_yas_ekle_false_ek_uygulanmaz(self):
        sonuc = cagir([40], YAS_USTU, yas_ekle=False)
        self.assertEqual(sonuc["sonuc"]["deger"], 40)
        self.assertFalse(sonuc["yuvarlama"]["uygulandi"])
        self.assertFalse(sonuc["yas_eklemesi"]["uygulandi"])

    def test_yas_eki_son_adim(self):
        sonuc = cagir([40, 30], YAS_USTU)
        self.assertEqual(sonuc["adimlar"][-1]["tur"], "yas_eki")
        self.assertEqual(sonuc["adimlar"][-1]["eklenen"], YAS_EKI_ORANI)
        self.assertEqual(sonuc["adimlar"][-1]["sonuc"], 62.2)

    def test_yas_dahil_tutarliligi(self):
        for yas, ekle, beklenen in (
            (YAS_USTU, True, True),
            (YAS_USTU, False, False),
            (YAS_ALTI, True, False),
            (YAS_ALTI, False, False),
        ):
            with self.subTest(yas=yas, yas_ekle=ekle):
                sonuc = cagir([50], yas, yas_ekle=ekle)
                self.assertIs(sonuc["sonuc"]["yas_dahil"], beklenen)
                self.assertIs(sonuc["yas_eklemesi"]["uygulandi"], beklenen)

    def test_yas_eki_100_ustunde_degismez(self):
        self.assertEqual(cagir([100], YAS_USTU)["sonuc"]["deger"], 100)

    def test_bileske_sonrasi_ek(self):
        # 58 + (100-58)*10/100 = 62.2 ; bileşkeden önce eklenirse farklı olurdu
        self.assertEqual(cagir([40, 30], YAS_USTU)["sonuc"]["deger"], 62.2)


class YasEkleTipi(unittest.TestCase):
    """`yas_ekle` yalnızca gerçek bool; sessiz `bool()` dönüşümü yok.

    Sözleşmede bu alan için ayrı kod bulunmadığından mevcut yaş kodu
    (``E_YAS_GECERSIZ``) kullanılır ve hata ``alan="yas_ekle"`` ile bildirilir.
    """

    REDDEDILEN = ("false", "true", "False", "0", 0, 1, 0.0, 1.0, None, [], {})

    def test_bool_olmayan_degerler_reddedilir(self):
        for deger in self.REDDEDILEN:
            with self.subTest(yas_ekle=deger):
                sonuc = cagir([40], YAS_USTU, yas_ekle=deger)
                self.assertFalse(sonuc["ok"])
                self.assertEqual(sonuc["hata"]["kod"], "E_YAS_GECERSIZ")
                self.assertEqual(sonuc["hata"]["alan"], "yas_ekle")
                self.assertNotIn("sonuc", sonuc)

    def test_sessiz_donusum_yok(self):
        # "false" bool() ile True olup yaş ekini uygulamamalı: çağrı reddedilir.
        sonuc = cagir([40], YAS_USTU, yas_ekle="false")
        self.assertFalse(sonuc["ok"])
        self.assertNotIn("sonuc", sonuc)

    def test_gercek_bool_degerler_kabul_edilir(self):
        ustu = cagir([40], YAS_USTU, yas_ekle=True)
        self.assertTrue(ustu["ok"])
        self.assertEqual(ustu["sonuc"]["deger"], 46)

        alti = cagir([40], YAS_USTU, yas_ekle=False)
        self.assertTrue(alti["ok"])
        self.assertEqual(alti["sonuc"]["deger"], 40)

    def test_alan_verilmezse_varsayilan_true(self):
        sonuc = balthazard({"oranlar": [40], "yas": YAS_USTU})
        self.assertTrue(sonuc["ok"])
        self.assertEqual(sonuc["sonuc"]["deger"], 46)
        self.assertIs(sonuc["yas_eklemesi"]["uygulandi"], True)

    def test_dogrulama_sirasi(self):
        # oranlar -> yas -> yas_ekle: geçersiz oran ve geçersiz bayrak birlikte
        # geldiğinde önce oran hatası döner.
        self.assertEqual(
            balthazard({"oranlar": [], "yas": None, "yas_ekle": "x"})["hata"]["kod"],
            "E_ORAN_YOK",
        )
        self.assertEqual(
            balthazard({"oranlar": [40], "yas": None, "yas_ekle": "x"})["hata"]["kod"],
            "E_YAS_SECILMEDI",
        )
        self.assertEqual(
            balthazard({"oranlar": [40], "yas": YAS_ALTI, "yas_ekle": "x"})["hata"]["alan"],
            "yas_ekle",
        )


class Hatalar(unittest.TestCase):
    def test_bos_liste(self):
        sonuc = cagir([])
        self.assertFalse(sonuc["ok"])
        self.assertEqual(sonuc["hata"]["kod"], "E_ORAN_YOK")
        self.assertEqual(sonuc["hata"]["alan"], "oranlar")

    def test_aralik_ustu(self):
        self.assertEqual(cagir([101])["hata"]["kod"], "E_ORAN_ARALIK")

    def test_aralik_alti(self):
        self.assertEqual(cagir([-1])["hata"]["kod"], "E_ORAN_ARALIK")

    def test_ondalikli_oran(self):
        self.assertEqual(cagir([12.5])["hata"]["kod"], "E_ORAN_TAMSAYI")

    def test_yas_eksik(self):
        sonuc = balthazard({"oranlar": [40]})
        self.assertEqual(sonuc["hata"]["kod"], "E_YAS_SECILMEDI")
        self.assertEqual(sonuc["hata"]["alan"], "yas")

    def test_yas_gecersiz(self):
        for yas in ("65", "", 65, "65_ÜZERİ", True):
            with self.subTest(yas=yas):
                self.assertEqual(cagir([40], yas)["hata"]["kod"], "E_YAS_GECERSIZ")

    def test_oranlar_liste_degil(self):
        for oranlar in ("40", 40, None, {"a": 1}, 40.0):
            with self.subTest(oranlar=oranlar):
                sonuc = balthazard({"oranlar": oranlar, "yas": YAS_ALTI})
                self.assertEqual(sonuc["hata"]["kod"], "E_ORAN_TIP")

    def test_oran_oge_tipi(self):
        for oge in ("40", None, [40], {"oran": 40}):
            with self.subTest(oge=oge):
                self.assertEqual(cagir([oge])["hata"]["kod"], "E_ORAN_TIP")

    def test_bool_oran_reddedilir(self):
        for oge in (True, False):
            with self.subTest(oge=oge):
                self.assertEqual(cagir([oge])["hata"]["kod"], "E_ORAN_TIP")

    def test_nan_inf_reddedilir(self):
        for oge in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(oge=oge):
                self.assertEqual(cagir([oge])["hata"]["kod"], "E_ORAN_TIP")

    def test_girdi_sozluk_degil(self):
        for girdi in (None, "metin", 40, [40]):
            with self.subTest(girdi=girdi):
                sonuc = balthazard(girdi)
                self.assertFalse(sonuc["ok"])
                self.assertEqual(sonuc["hata"]["alan"], "girdi")

    def test_hata_zarfi(self):
        sonuc = cagir([])
        self.assertEqual(set(sonuc.keys()), {"ok", "hata"})
        self.assertEqual(set(sonuc["hata"].keys()), {"kod", "mesaj", "alan"})
        for alan in ("kod", "mesaj", "alan"):
            self.assertIsInstance(sonuc["hata"][alan], str)
            self.assertTrue(sonuc["hata"][alan])

    def test_hata_oncesi_oranlar_dogrulanir(self):
        # Oranlar yaş'tan önce doğrulanır (sözleşme vektör sırası 10–13).
        sonuc = balthazard({"oranlar": [120], "yas": None})
        self.assertEqual(sonuc["hata"]["kod"], "E_ORAN_ARALIK")

    def test_beklenmeyen_girdiler_istisna_firlatmaz(self):
        girdiler = [
            {},
            {"oranlar": []},
            {"oranlar": [None], "yas": YAS_ALTI},
            {"oranlar": [{}], "yas": YAS_ALTI},
            {"oranlar": [40], "yas": {"a": 1}},
            {"oranlar": [40], "yas": [1, 2]},
            {"oranlar": (40, 30), "yas": YAS_ALTI},
            {"oranlar": [40], "yas": YAS_ALTI, "yas_ekle": "hayır"},
            {"oranlar": [40, 40, 40, 40], "yas": YAS_USTU},
            {"oranlar": [10**9], "yas": YAS_ALTI},
        ]
        for girdi in girdiler:
            with self.subTest(girdi=girdi):
                try:
                    sonuc = balthazard(girdi)
                except Exception as exc:  # pragma: no cover - kasıtlı güvence
                    self.fail(f"İstisna fırlatıldı: {exc!r}")
                self.assertIn("ok", sonuc)


class HamDegerVeYuvarlama(unittest.TestCase):
    def test_yuvarlama_uygulanmadi(self):
        for oranlar in ([40], [40, 30], [33, 33], [49, 49], [33, 33, 33]):
            with self.subTest(oranlar=oranlar):
                yuvarlama = cagir(oranlar)["yuvarlama"]
                self.assertIs(yuvarlama["uygulandi"], False)
                self.assertIsNone(yuvarlama["kural"])
                self.assertTrue(yuvarlama["not"])

    def test_ham_ondalik_korunur(self):
        self.assertEqual(cagir([33, 33])["sonuc"]["deger"], 55.11)
        self.assertEqual(cagir([49, 49])["sonuc"]["deger"], 73.99)

    def test_ara_adimda_yuvarlama_yok(self):
        sonuc = cagir([49, 49])
        self.assertEqual(sonuc["adimlar"][-1]["sonuc"], 73.99)
        self.assertNotEqual(sonuc["adimlar"][-1]["sonuc"], 74)
        self.assertNotEqual(sonuc["sonuc"]["deger"], 74)

    def test_kesinlik_kaybi_yok_uc_oran(self):
        # 33 -> 55.11 -> 69.9237 (ara yuvarlama olsaydı 69.92/69.93 çıkardı)
        self.assertEqual(cagir([33, 33, 33])["sonuc"]["deger"], 69.9237)

    def test_tam_sayi_mi_bayragi(self):
        self.assertTrue(cagir([40, 30])["sonuc"]["tam_sayi_mi"])
        self.assertFalse(cagir([33, 33])["sonuc"]["tam_sayi_mi"])
        self.assertFalse(cagir([40, 30], YAS_USTU)["sonuc"]["tam_sayi_mi"])
        self.assertTrue(cagir([80], YAS_USTU)["sonuc"]["tam_sayi_mi"])

    def test_deri_bes_eklenmez(self):
        # B-8 (X-D03) açık: DERİ "+%5" kataloğa ve motora eklenmez.
        self.assertEqual(cagir([20])["sonuc"]["deger"], 20)
        self.assertNotEqual(cagir([20])["sonuc"]["deger"], 25)

    def test_tavan_asilmaz(self):
        self.assertEqual(cagir([100, 100])["sonuc"]["deger"], 100)
        self.assertEqual(cagir([100, 100], YAS_USTU)["sonuc"]["deger"], 100)


class Gosterim(unittest.TestCase):
    """Sunum katmanı: en fazla 2 ondalık, sondaki sıfırlar atılır."""

    def test_tam_sayilar(self):
        for deger, beklenen in ((0, "0"), (40, "40"), (46, "46"), (58, "58"), (100, "100")):
            with self.subTest(deger=deger):
                self.assertEqual(bicimle_gosterim(deger), beklenen)

    def test_iki_ondalik(self):
        self.assertEqual(bicimle_gosterim(55.11), "55,11")
        self.assertEqual(bicimle_gosterim(73.99), "73,99")
        self.assertEqual(bicimle_gosterim(69.9237), "69,92")

    def test_sondaki_sifirlar_atilir(self):
        self.assertEqual(bicimle_gosterim(62.20), "62,2")
        self.assertEqual(bicimle_gosterim(59.599), "59,6")
        self.assertEqual(bicimle_gosterim(55.0), "55")

    def test_yari_yukari(self):
        self.assertEqual(bicimle_gosterim(55.115), "55,12")
        self.assertEqual(bicimle_gosterim(2.675), "2,68")
        self.assertEqual(bicimle_gosterim(0.125), "0,13")

    def test_basamak_sifir(self):
        self.assertEqual(bicimle_gosterim(55.11, basamak=0), "55")
        self.assertEqual(bicimle_gosterim(55.5, basamak=0), "56")
        self.assertEqual(bicimle_gosterim(46, basamak=0), "46")

    def test_basamak_bir(self):
        self.assertEqual(bicimle_gosterim(55.11, basamak=1), "55,1")
        self.assertEqual(bicimle_gosterim(62.2, basamak=1), "62,2")

    def test_nokta_ayirici(self):
        self.assertEqual(bicimle_gosterim(55.11, ayirici="."), "55.11")
        self.assertEqual(bicimle_gosterim(62.2, ayirici="."), "62.2")

    def test_motoru_degistirmez(self):
        sonuc = cagir([33, 33])
        onceki = sonuc["sonuc"]["deger"]
        self.assertEqual(bicimle_gosterim(onceki), "55,11")
        self.assertEqual(sonuc["sonuc"]["deger"], onceki)
        self.assertIs(sonuc["yuvarlama"]["uygulandi"], False)

    def test_gercek_sonuclarin_gosterimi(self):
        ornekler = [
            ([40], YAS_ALTI, "40"),
            ([40], YAS_USTU, "46"),
            ([40, 30], YAS_ALTI, "58"),
            ([40, 30], YAS_USTU, "62,2"),
            ([33, 33], YAS_ALTI, "55,11"),
            ([33, 33], YAS_USTU, "59,6"),
            ([0], YAS_ALTI, "0"),
            ([100], YAS_ALTI, "100"),
        ]
        for oranlar, yas, beklenen in ornekler:
            with self.subTest(oranlar=oranlar, yas=yas):
                sonuc = cagir(oranlar, yas)
                self.assertEqual(bicimle_gosterim(sonuc["sonuc"]["deger"]), beklenen)

    def test_gecersiz_deger(self):
        for deger in ("40", None, True, float("nan")):
            with self.subTest(deger=deger):
                with self.assertRaises(TypeError):
                    bicimle_gosterim(deger)
        with self.assertRaises(ValueError):
            bicimle_gosterim(40, basamak=-1)


class GosterimKarari(unittest.TestCase):
    """G-1…G-4 kapandı (28.10.2026): belge, motor ve sunum aynı kuralı söylemeli."""

    # Sözleşme §9.1, vektör 14-20: (oranlar, yas, ham deger, gosterim metni)
    VEKTORLER = [
        ([33, 33], YAS_ALTI, 55.11, "55,11"),
        ([49, 49], YAS_ALTI, 73.99, "73,99"),
        ([40, 30], YAS_USTU, 62.2, "62,2"),
        ([33, 33], YAS_USTU, 59.599, "59,6"),
        ([33, 33, 33], YAS_ALTI, 69.9237, "69,92"),
        ([40, 40], YAS_ALTI, 64, "64"),
        ([80], YAS_USTU, 82, "82"),
    ]

    def test_sozlesme_vektor_14_20(self):
        for sira, (oranlar, yas, ham, metin) in enumerate(self.VEKTORLER, start=14):
            with self.subTest(vektor=sira, oranlar=oranlar, yas=yas):
                sonuc = cagir(oranlar, yas)
                self.assertTrue(sonuc["ok"])
                self.assertEqual(sonuc["sonuc"]["deger"], ham)
                self.assertEqual(bicimle_gosterim(sonuc["sonuc"]["deger"]), metin)

    def test_ham_deger_gosterimden_sonra_degismez(self):
        sonuc = cagir([33, 33], YAS_USTU)
        onceki_sonuc = dict(sonuc["sonuc"])
        onceki_adimlar = [dict(adim) for adim in sonuc["adimlar"]]
        onceki_yuvarlama = dict(sonuc["yuvarlama"])

        self.assertEqual(bicimle_gosterim(sonuc["sonuc"]["deger"]), "59,6")

        self.assertEqual(sonuc["sonuc"], onceki_sonuc)
        self.assertEqual(sonuc["adimlar"], onceki_adimlar)
        self.assertEqual(sonuc["yuvarlama"], onceki_yuvarlama)
        self.assertIs(sonuc["yuvarlama"]["uygulandi"], False)
        self.assertIsNone(sonuc["yuvarlama"]["kural"])

    def test_yas_eki_ham_bileskeye_uygulanir(self):
        # G-3: yuvarlama en sonda; yaş ekinin girdisi ham bileşke (55.11) olmalı.
        sonuc = cagir([33, 33], YAS_USTU)
        son_adim = sonuc["adimlar"][-1]
        self.assertEqual(son_adim["tur"], "yas_eki")
        self.assertEqual(son_adim["onceki"], 55.11)
        self.assertEqual(son_adim["sonuc"], 59.599)
        self.assertNotEqual(son_adim["sonuc"], 59.6)  # yuvarlanmış değere eklenmedi

    def test_gosterim_tek_kez_iki_basamak(self):
        # Hiçbir değer iki basamaktan fazla ondalık göstermez, ara yuvarlama yok.
        self.assertEqual(bicimle_gosterim(0.123456789), "0,12")
        self.assertEqual(bicimle_gosterim(55.114), "55,11")
        self.assertEqual(bicimle_gosterim(2.674), "2,67")
        self.assertEqual(bicimle_gosterim(2.675), "2,68")

    def test_kopya_ham_degeri_tasir(self):
        sonuc = cagir([33, 33], YAS_USTU)
        self.assertEqual(repr(sonuc["sonuc"]["deger"]), "59.599")
        self.assertEqual(bicimle_gosterim(sonuc["sonuc"]["deger"]), "59,6")

    def test_yuvarlama_notu_kararla_uyumlu(self):
        notu = cagir([40])["yuvarlama"]["not"]
        self.assertIn("ham", notu.lower())
        self.assertIn("gösterim", notu)
        self.assertIn("2 ondalık", notu)


class Yapi(unittest.TestCase):
    def test_basari_anahtarlari(self):
        sonuc = cagir([40])
        self.assertEqual(
            set(sonuc.keys()),
            {"ok", "sonuc", "adimlar", "siralama", "yas_eklemesi", "yuvarlama", "uyarilar"},
        )
        self.assertEqual(
            set(sonuc["sonuc"].keys()), {"deger", "tam_sayi_mi", "yas_dahil"}
        )

    def test_yas_eklemesi_alani(self):
        sonuc = cagir([40], YAS_USTU)
        self.assertEqual(sonuc["yas_eklemesi"]["oran"], 10)
        self.assertEqual(sonuc["yas_eklemesi"]["dayanak"], DAYANAK)
        self.assertIn("30692", sonuc["yas_eklemesi"]["dayanak"])

    def test_uyari_sirasi(self):
        kodlar = [u["kod"] for u in cagir([40, 40, 0, 100])["uyarilar"]]
        self.assertEqual(kodlar, ["U_ORAN_TEKRAR", "U_ORAN_100", "U_ORAN_SIFIR"])

    def test_uyari_yok(self):
        self.assertEqual(cagir([40, 30])["uyarilar"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
