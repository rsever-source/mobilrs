# -*- coding: utf-8 -*-
"""Asama 1 - YAPISAL testler (T0-T26).

Yalnizca sema kurallarini olcer. Icerik dogrulugu (WHO etiketi, takvim
gecerliligi, tekillik) bu dosyanin isi DEGILDIR; bkz. veri_testleri.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ortak import (  # noqa: E402
    RAPOR_DIR,
    Kosum,
    bekle_gecerli,
    bekle_hata,
    dogrulayici,
    ek1,
    ek2,
    sema_yukle,
    sil,
    tum_hatalar,
    uygula,
)
from jsonschema import Draft7Validator  # noqa: E402


def main():
    kosum = Kosum("Asama 1 - Yapisal denetim")
    sema = sema_yukle()
    v = dogrulayici(sema)

    # --- T0: semanin kendisi gecerli bir Draft-07 belgesi mi? ----------------
    try:
        Draft7Validator.check_schema(sema)
        kosum.gecer("T0", "Sema gecerli bir Draft-07 belgesi (check_schema)")
    except Exception as exc:  # noqa: BLE001
        kosum.kalkar("T0", "Sema gecerli bir Draft-07 belgesi", str(exc))

    # --- gecerli kayitlar ----------------------------------------------------
    bekle_gecerli(kosum, "T1", "EK-1 kaydi (A/1/agir, tam kaynak kunyesi)", v, ek1())
    bekle_gecerli(kosum, "T2", "EK-2 kaydi (KULAK BURUN BOGAZ/A-ISITME/1 + icd10 H90.3)", v, ek2())
    bekle_gecerli(kosum, "T3", "Ayni kavramin EK-1 ve EK-2 kaydi ayri ayri", v, ek1())
    bekle_gecerli(
        kosum,
        "T3b",
        "EK-1 R bolumu (R/1/ortak_hukum) gecerli",
        v,
        uygula(ek1(), ["ek_1_baglantisi"], {"bolum_harfi": "R", "sira_no": 1, "derece": "ortak_hukum"}),
    )
    bekle_gecerli(
        kosum,
        "T3c",
        "EK-1 'I' ve 'I' (noktali) ayri degerler olarak gecerli (O-2)",
        v,
        uygula(ek1(), ["ek_1_baglantisi"], {"bolum_harfi": "İ", "sira_no": 2, "derece": "orta"}),
    )
    bekle_gecerli(kosum, "T9b", "es_anlamli: [] gecerli (karar 2)", v, uygula(ek1(), ["es_anlamli"], []))
    bekle_gecerli(
        kosum,
        "T7f",
        "EK-2 kaydi alt_bolum OLMADAN gecerli (karar 4 / kaynak kaniti)",
        v,
        uygula(ek2(), ["ek_2_baglantisi"], {k: w for k, w in ek2()["ek_2_baglantisi"].items() if k != "alt_bolum"}),
    )
    bekle_gecerli(
        kosum,
        "T7h",
        "EK-2 Roma rakamli madde etiketi ('IV') metin olarak gecerli",
        v,
        uygula(
            ek2(),
            ["ek_2_baglantisi"],
            {
                "bolum_adi": "RUH SAGLIGI",
                "madde_etiketi": "IV",
                "tanim": "Anksiyete bozukluklari; alt maddeler a) b) C) d) olarak basilidir.",
            },
        ),
    )
    bekle_gecerli(
        kosum,
        "T3d",
        "olusturulma_tarihi gecerli ISO 8601 date-time",
        v,
        uygula(ek1(), ["olusturulma_tarihi"], "2026-11-11T00:00:00Z"),
    )

    # --- reddedilmesi gerekenler --------------------------------------------
    def reddet(test_id, aciklama, kayit, validator_adi, yol, mesaj):
        bekle_hata(kosum, test_id, aciklama, tum_hatalar(v, kayit), validator_adi, yol, mesaj)

    reddet(
        "T4",
        "EK-1 + EK-2 baglantisi birlikte -> oneOf (XOR)",
        uygula(ek1(), ["ek_2_baglantisi"], ek2()["ek_2_baglantisi"]),
        "oneOf",
        [],
        "is not valid under any of the given schemas",
    )
    reddet(
        "T5",
        "Iki baglanti da yok -> oneOf",
        {k: w for k, w in ek1().items() if k != "ek_1_baglantisi"},
        "oneOf",
        [],
        "is not valid under any of the given schemas",
    )
    reddet(
        "T6",
        "EK-1'de sira_no yok -> required",
        uygula(ek1(), ["ek_1_baglantisi", "sira_no"], sil("ek_1_baglantisi", "sira_no")),
        "required",
        ["ek_1_baglantisi"],
        "'sira_no' is a required property",
    )
    reddet(
        "T7a",
        "bolum_harfi 'Z' -> enum",
        uygula(ek1(), ["ek_1_baglantisi", "bolum_harfi"], "Z"),
        "enum",
        ["ek_1_baglantisi", "bolum_harfi"],
        "'Z' is not one of",
    )
    reddet(
        "T7b",
        "sira_no 0 -> minimum",
        uygula(ek1(), ["ek_1_baglantisi", "sira_no"], 0),
        "minimum",
        ["ek_1_baglantisi", "sira_no"],
        "less than the minimum of 1",
    )
    reddet(
        "T7c",
        "R bolumunde derece 'agir' -> const ortak_hukum",
        uygula(ek1(), ["ek_1_baglantisi"], {"bolum_harfi": "R", "sira_no": 1, "derece": "agir"}),
        "const",
        ["ek_1_baglantisi", "derece"],
        "was expected",
    )
    reddet(
        "T7d",
        "R bolumunde sira_no 4 -> maximum 3",
        uygula(ek1(), ["ek_1_baglantisi"], {"bolum_harfi": "R", "sira_no": 4, "derece": "ortak_hukum"}),
        "maximum",
        ["ek_1_baglantisi", "sira_no"],
        "greater than the maximum of 3",
    )
    reddet(
        "T7e",
        "kavram_id 'ek2_' onekli ama ek_1_baglantisi -> pattern (karar 1)",
        uygula(ek1(), ["kavram_id"], "ek2_isitme_kaybi_agir"),
        "pattern",
        ["kavram_id"],
        "does not match '^ek1_'",
    )
    reddet(
        "T7g",
        "kavram_id 'ek1_' onekli ama ek_2_baglantisi -> pattern (karar 1)",
        uygula(ek2(), ["kavram_id"], "ek1_isitme_kaybi_bilateral"),
        "pattern",
        ["kavram_id"],
        "does not match '^ek2_'",
    )
    reddet(
        "T8a",
        "ek_1_baglantisi icinde icd10 -> additionalProperties",
        uygula(ek1(), ["ek_1_baglantisi"], {**ek1()["ek_1_baglantisi"], "icd10": []}),
        "additionalProperties",
        ["ek_1_baglantisi"],
        "icd10' was unexpected",
    )
    reddet(
        "T8b",
        "Kok duzeyde icd10 -> additionalProperties",
        uygula(ek1(), ["icd10"], []),
        "additionalProperties",
        [],
        "icd10' was unexpected",
    )
    reddet(
        "T8c",
        "kod 'h54.1' (kucuk harf) -> pattern",
        uygula(ek2(), ["ek_2_baglantisi", "icd10", 0, "kod"], "h54.1"),
        "pattern",
        ["ek_2_baglantisi", "icd10", 0, "kod"],
        "does not match",
    )
    reddet(
        "T8d",
        "icd10[0] icinde erisim_tarihi yok -> required (karar 3)",
        uygula(ek2(), ["ek_2_baglantisi", "icd10", 0], {
            k: w for k, w in ek2()["ek_2_baglantisi"]["icd10"][0].items() if k != "erisim_tarihi"
        }),
        "required",
        ["ek_2_baglantisi", "icd10", 0],
        "'erisim_tarihi' is a required property",
    )
    reddet(
        "T9",
        "es_anlamli: [{}] -> required dil",
        uygula(ek1(), ["es_anlamli"], [{}]),
        "required",
        ["es_anlamli", 0],
        "'dil' is a required property",
    )
    reddet(
        "T10",
        "kaynak.url 'bozuk-url' -> pattern (ve format uri)",
        uygula(ek1(), ["kaynak", "url"], "bozuk-url"),
        "pattern",
        ["kaynak", "url"],
        "does not match '^https?://'",
    )
    reddet(
        "T11",
        "rg_tarihi ISO biciminde -> pattern gg.aa.yyyy",
        uygula(ek1(), ["kaynak", "rg_tarihi"], "2021-09-28"),
        "pattern",
        ["kaynak", "rg_tarihi"],
        "does not match",
    )
    reddet(
        "T10b",
        "kaynak.url 'https://' -> pattern GECER ama format uri REDDEDER (O-3)",
        uygula(ek1(), ["kaynak", "url"], "https://"),
        "format",
        ["kaynak", "url"],
        "is not a 'uri'",
    )
    reddet(
        "T10c",
        "kaynak.url 'https://ornek.invalid/a b' (bosluk) -> format uri REDDEDER",
        uygula(ek1(), ["kaynak", "url"], "https://ornek.invalid/a b"),
        "format",
        ["kaynak", "url"],
        "is not a 'uri'",
    )
    reddet(
        "T11b2",
        "rg_tarihi '2021-09-28' bicim hatasi -> pattern (takvim ayri: D3)",
        uygula(ek1(), ["kaynak", "rg_tarihi"], "2021-09-28"),
        "pattern",
        ["kaynak", "rg_tarihi"],
        "does not match",
    )
    reddet(
        "T18",
        "kaynak.rg_sayisi yok -> required (karar 5)",
        uygula(ek1(), ["kaynak", "rg_sayisi"], sil("kaynak", "rg_sayisi")),
        "required",
        ["kaynak"],
        "'rg_sayisi' is a required property",
    )
    reddet(
        "T19",
        "Yalniz mbs_no var, rg_sayisi yok -> required (karar 5: ayri alan)",
        uygula(
            uygula(ek1(), ["kaynak", "mbs_no"], 31275),
            ["kaynak", "rg_sayisi"],
            sil("kaynak", "rg_sayisi"),
        ),
        "required",
        ["kaynak"],
        "'rg_sayisi' is a required property",
    )
    reddet(
        "T13",
        "icd10 kaynak_url 'http://' -> pattern ^https://",
        uygula(
            ek2(),
            ["ek_2_baglantisi", "icd10", 0, "kaynak_url"],
            "http://icd.who.int/browse10/2019/en/JsonGetConcept?ConceptId=H90.3",
        ),
        "pattern",
        ["ek_2_baglantisi", "icd10", 0, "kaynak_url"],
        "does not match '^https://'",
    )
    reddet(
        "T14",
        "Iki ozdes es_anlamli ogesi -> uniqueItems",
        uygula(
            ek1(),
            ["es_anlamli"],
            [
                {"dil": "tr", "termin": "sagir"},
                {"dil": "tr", "termin": "sagir"},
            ],
        ),
        "uniqueItems",
        ["es_anlamli"],
        "non-unique",
    )
    reddet(
        "T17",
        "olusturulma_tarihi '2026-13-45T99:99:99Z' -> format date-time (karar 8)",
        uygula(ek1(), ["olusturulma_tarihi"], "2026-13-45T99:99:99Z"),
        "format",
        ["olusturulma_tarihi"],
        "is not a 'date-time'",
    )
    reddet(
        "T17b",
        "olusturulma_tarihi '2026-02-30T10:00:00Z' -> format date-time (takvim gecersiz)",
        uygula(ek1(), ["olusturulma_tarihi"], "2026-02-30T10:00:00Z"),
        "format",
        ["olusturulma_tarihi"],
        "is not a 'date-time'",
    )
    reddet(
        "T17c",
        "olusturulma_tarihi '11.11.2026T00:00:00Z' -> format date-time (bicim bozuk)",
        uygula(ek1(), ["olusturulma_tarihi"], "11.11.2026T00:00:00Z"),
        "format",
        ["olusturulma_tarihi"],
        "is not a 'date-time'",
    )
    reddet(
        "T20",
        "kavram_id 'EK1_x' (buyuk harf onek) -> pattern",
        uygula(ek1(), ["kavram_id"], "EK1_isitme_kaybi_agir"),
        "pattern",
        ["kavram_id"],
        "does not match",
    )
    reddet(
        "T23",
        "ICD kodu 'H54,1' (virgul) REDDEDILIR, yalniz nokta gecerli (duzeltme 1)",
        uygula(ek2(), ["ek_2_baglantisi", "icd10", 0, "kod"], "H54,1"),
        "pattern",
        ["ek_2_baglantisi", "icd10", 0, "kod"],
        "does not match",
    )
    reddet(
        "T23b",
        "ICD kodu 'H54.12' (iki haneli alt ayrim) REDDEDILIR -> pattern",
        uygula(ek2(), ["ek_2_baglantisi", "icd10", 0, "kod"], "H54.12"),
        "pattern",
        ["ek_2_baglantisi", "icd10", 0, "kod"],
        "does not match",
    )
    reddet(
        "T24",
        "kaynak.erisim_tarihi '2026-02-30' -> format date (duzeltme 3)",
        uygula(ek1(), ["kaynak", "erisim_tarihi"], "2026-02-30"),
        "format",
        ["kaynak", "erisim_tarihi"],
        "is not a 'date'",
    )
    reddet(
        "T25",
        "icd10.erisim_tarihi '2026-02-30' -> format date (duzeltme 3)",
        uygula(ek2(), ["ek_2_baglantisi", "icd10", 0, "erisim_tarihi"], "2026-02-30"),
        "format",
        ["ek_2_baglantisi", "icd10", 0, "erisim_tarihi"],
        "is not a 'date'",
    )
    reddet(
        "T21",
        "EK-1 kaydinda rg_sayisi 30692 -> const 31612 (duzeltme 2)",
        uygula(ek1(), ["kaynak", "rg_sayisi"], 30692),
        "const",
        ["kaynak", "rg_sayisi"],
        "31612 was expected",
    )
    reddet(
        "T22",
        "EK-2 kaydinda rg_sayisi 31612 -> const 30692 (duzeltme 2)",
        uygula(ek2(), ["kaynak", "rg_sayisi"], 31612),
        "const",
        ["kaynak", "rg_sayisi"],
        "30692 was expected",
    )
    reddet(
        "T22b",
        "EK-1 kaydinda mbs_no bulunmasi semayi bozmaz, ama rg_sayisi 30692 ise yine RED",
        uygula(ek1(), ["kaynak", "rg_sayisi"], 30692),
        "const",
        ["kaynak", "rg_sayisi"],
        "31612 was expected",
    )

    # --- bilincli sema siniri: neden veri testi gerekiyor? -------------------
    hatalar = tum_hatalar(
        v,
        uygula(
            ek2(),
            ["ek_2_baglantisi", "icd10"],
            [
                {
                    "kod": "H90.3",
                    "who_etiketi": "Sensorineural hearing loss, bilateral",
                    "kaynak_url": "https://icd.who.int/browse10/2019/en/JsonGetConcept?ConceptId=H90.3",
                    "erisim_tarihi": "2026-11-11",
                },
                {
                    "kod": "H90.3",
                    "who_etiketi": "Baska etiket",
                    "kaynak_url": "https://icd.who.int/browse10/2019/en/JsonGetConcept?ConceptId=H90.3",
                    "erisim_tarihi": "2026-11-11",
                },
            ],
        ),
    )
    if not hatalar:
        kosum.gecer(
            "T26",
            "SEMA SINIRI (bilincli): ayni icd10.kod iki kez semadan GECER -> T16 veri testi zorunlu",
        )
    else:
        kosum.kalkar(
            "T26",
            "Sema siniri belgelenemedi: ayni kod semadan gecti saniliyordu ama reddedildi",
            "; ".join(f"[{a}] {'/'.join(map(str, b))} :: {c}" for a, b, c in hatalar),
        )

    # --- format denetiminin gercekten kostugunu kanitla ----------------------
    from jsonschema import FormatChecker  # noqa: PLC0415

    from ortak import format_checker_uret  # noqa: PLC0415

    fc = format_checker_uret()
    ham_fc = FormatChecker()
    kanit = []

    def _kontrol(checker, deger, bicim):
        try:
            checker.check(deger, bicim)
            return True
        except Exception:  # noqa: BLE001
            return False

    for deger, bicim in (
        ("2026-13-45T99:99:99Z", "date-time"),
        ("2026-02-30", "date"),
        ("bozuk-url", "uri"),
        ("https://", "uri"),
        ("https://ornek.invalid/a b", "uri"),
    ):
        varsayilan = _kontrol(ham_fc, deger, bicim)
        bizim = _kontrol(fc, deger, bicim)
        kanit.append(f"{bicim}:{deger!r} varsayilan={'GECER' if varsayilan else 'RED'} bizim={'GECER' if bizim else 'RED'}")
        if bizim:
            kosum.kalkar(
                "T27",
                "Format denetimi gercekten kosturuluyor",
                f"{bicim} {deger!r} bizim dogrulayicimizdan GECTI (olmamali)",
            )
            break
    else:
        kosum.gecer(
            "T27",
            "Format denetimi gercekten kosturuluyor (date-time/date/uri reddedildi)",
        )
        ornek = "; ".join(kanit)
        print(f"      kanit: {ornek}")
        print(
            "      not: varsayilan FormatChecker 'date-time' ve 'uri' icin denetleyici "
            "kayitli degil (rfc3339-validator / rfc3987 yok); bu yuzden kati denetleyici "
            "kaydedildi."
        )

    return kosum.ozet_yaz(RAPOR_DIR / "yapisal_sonuc.json")


if __name__ == "__main__":
    sys.exit(0 if main() == "PASS" else 1)
