# -*- coding: utf-8 -*-
"""Ortak test altyapisi.

Kurallar (plana baglayici):
- Dogrulama YALNIZCA gercek jsonschema Draft7Validator ile yapilir.
- format denetimi FormatChecker ile ACIKTIR (date, date-time, uri).
- oneOf / if-then hatalari error.context icinde ic ice gelir; bu yuzden
  hatalar ozyinelemeli olarak duzlestirilir.
- Her negatif test UC seyi birden dogrular: mesaj alt dizisi + validator
  anahtari + json_path (absolute_path).
"""
import copy
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

KOK = Path(__file__).resolve().parent.parent
SEMA_YOLU = Path(os.environ.get("SOZLUK_SEMA", KOK / "schema" / "sozluk_kavram.v1.0.0.json"))
RAPOR_DIR = Path(os.environ.get("SOZLUK_RAPOR_DIR", KOK / "raporlar"))

try:
    from jsonschema import Draft7Validator, FormatChecker
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "HATA: jsonschema kurulu degil. Bu testler basit dogrulamaya DUSMEZ. "
        f"Ayrinti: {exc}"
    )

# jsonschema 4.26, 'date-time' icin rfc3339-validator, 'uri' icin rfc3987
# paketlerine baglidir. Bunlar kurulu degilse FormatChecker bu iki bicimi
# SESSIZCE atlar (checkers sozlugunde kayit bulunmaz). Asagida bu bosluk
# jsonschema'nin belgelenmis genisletme yolu (FormatChecker.checks) ile
# kapatilir; boylece format denetimi gercekten calisir.
EKSIK_DENETLEYICILER = []


def _uri_gecerli(deger):
    if any(c.isspace() for c in deger):
        return False
    parcalar = urlsplit(deger)
    if not parcalar.scheme or not parcalar.netloc:
        return False
    if parcalar.scheme not in ("http", "https"):
        return False
    konak = parcalar.hostname or ""
    if "." not in konak and konak != "localhost":
        return False
    if parcalar.port is not None and not (0 < parcalar.port < 65536):
        return False
    return True


def format_checker_uret():
    fc = FormatChecker()
    kayitli = set(fc.checkers)

    if "date-time" not in kayitli:
        @fc.checks("date-time", raises=ValueError)
        def _kati_date_time(deger):
            if not isinstance(deger, str):
                return True
            metin = deger[:-1] + "+00:00" if deger[-1:] in ("Z", "z") else deger
            datetime.fromisoformat(metin)  # ValueError -> gecersiz
            return True

        EKSIK_DENETLEYICILER.append(
            "date-time: yerlesik denetleyici yoktu (rfc3339-validator kurulu degil), "
            "kati denetleyici kaydedildi"
        )

    if "uri" not in kayitli:
        @fc.checks("uri")
        def _kati_uri(deger):
            return True if not isinstance(deger, str) else _uri_gecerli(deger)

        EKSIK_DENETLEYICILER.append(
            "uri: yerlesik denetleyici yoktu (rfc3987 kurulu degil), "
            "kati denetleyici kaydedildi"
        )

    return fc


def sema_yukle():
    with SEMA_YOLU.open(encoding="utf-8") as fh:
        return json.load(fh)


def dogrulayici(sema=None):
    return Draft7Validator(sema or sema_yukle(), format_checker=format_checker_uret())


def hatalari_duzlestir(hata):
    """error.context agacini (validator, absolute_path, message) uclulerine indirir."""
    cikti = [(hata.validator, tuple(hata.absolute_path), hata.message)]
    for alt in hata.context:
        cikti.extend(hatalari_duzlestir(alt))
    return cikti


def tum_hatalar(validator, kayit):
    cikti = []
    for hata in validator.iter_errors(kayit):
        cikti.extend(hatalari_duzlestir(hata))
    return cikti


# --- kayit kurma yardimcilari -------------------------------------------------

YER_TUTUCU_URL = "https://ornek.invalid/test-kaynagi"


def ek1(**degisiklik):
    kayit = {
        "kavram_id": "ek1_isitme_kaybi_agir",
        "kanonik_ad": "Isitme kaybi (cift tarafli, agir)",
        "es_anlamli": [],
        "ek_1_baglantisi": {"bolum_harfi": "A", "sira_no": 1, "derece": "agir"},
        "kaynak": {
            "belge_adi": "Maluliyet ve Calisma Gucu Kaybi Tespit Islemleri Yonetmeligi EK-1",
            "rg_tarihi": "28.09.2021",
            "rg_sayisi": 31612,
            "url": YER_TUTUCU_URL + "/ek1",
            "erisim_tarihi": "2026-11-11",
        },
    }
    return _birlestir(kayit, degisiklik)


def ek2(**degisiklik):
    kayit = {
        "kavram_id": "ek2_isitme_kaybi_bilateral",
        "kanonik_ad": "Bilateral isitme kaybi",
        "es_anlamli": [],
        "ek_2_baglantisi": {
            "bolum_adi": "KULAK BURUN BOGAZ",
            "alt_bolum": "A-ISITME",
            "madde_etiketi": "1",
            "tanim": "Bilateral isitme kaybi; tablo I-a ve I-b ile degerlendirilir.",
            "icd10": [
                {
                    "kod": "H90.3",
                    "who_etiketi": "Sensorineural hearing loss, bilateral",
                    "kaynak_url": "https://icd.who.int/browse10/2019/en/JsonGetConcept?ConceptId=H90.3",
                    "erisim_tarihi": "2026-11-11",
                }
            ],
        },
        "kaynak": {
            "belge_adi": "Engelli Saglik Kurulu Raporlari Engel Oranlari Alan Kilavuzu EK-2",
            "rg_tarihi": "20.02.2019",
            "rg_sayisi": 30692,
            "mbs_no": 31275,
            "url": YER_TUTUCU_URL + "/ek2",
            "erisim_tarihi": "2026-11-11",
        },
    }
    return _birlestir(kayit, degisiklik)


def _birlestir(kayit, degisiklik):
    kayit = copy.deepcopy(kayit)
    for anahtar, deger in degisiklik.items():
        if deger is _SIL:
            kayit.pop(anahtar, None)
        else:
            kayit[anahtar] = deger
    return kayit


class _Sil:
    def __repr__(self):
        return "<SIL>"


_SIL = _Sil()


def sil(*yol):
    """Ic ice alan silme icin isaretleyici uretir: sil("kaynak", "rg_sayisi")."""
    return ("__sil__", yol)


def uygula(kayit, yol, deger):
    """kayit icinde yol'a deger yazar; deger sil(...) ise alani kaldirir."""
    kayit = copy.deepcopy(kayit)
    hedef = kayit
    for adim in yol[:-1]:
        hedef = hedef[adim]
    son = yol[-1]
    if isinstance(deger, tuple) and deger and deger[0] == "__sil__":
        hedef.pop(son, None)
    else:
        hedef[son] = copy.deepcopy(deger)
    return kayit


# --- test kosum kaydi ---------------------------------------------------------

class Kosum:
    def __init__(self, ad):
        self.ad = ad
        self.kayitlar = []

    def gecer(self, test_id, aciklama):
        self.kayitlar.append(
            {"test": test_id, "durum": "PASS", "aciklama": aciklama, "ayrinti": ""}
        )
        print(f"PASS  {test_id:6s} {aciklama}")

    def kalkar(self, test_id, aciklama, ayrinti):
        self.kayitlar.append(
            {"test": test_id, "durum": "FAIL", "aciklama": aciklama, "ayrinti": ayrinti}
        )
        print(f"FAIL  {test_id:6s} {aciklama} :: {ayrinti}")

    def hata_say(self):
        return sum(1 for k in self.kayitlar if k["durum"] == "FAIL")

    def ozet_yaz(self, yol):
        gecen = sum(1 for k in self.kayitlar if k["durum"] == "PASS")
        toplam = len(self.kayitlar)
        veri = {
            "baslik": self.ad,
            "toplam": toplam,
            "gecen": gecen,
            "kalan": toplam - gecen,
            "sonuc": "PASS" if self.hata_say() == 0 else "FAIL",
            "format_denetleyici_notlari": EKSIK_DENETLEYICILER,
            "testler": self.kayitlar,
        }
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n== {self.ad}: {gecen}/{toplam} PASS -> {veri['sonuc']}")
        return veri["sonuc"]


def bekle_gecerli(kosum, test_id, aciklama, validator, kayit):
    hatalar = tum_hatalar(validator, kayit)
    if hatalar:
        ayrinti = "; ".join(
            f"[{v}] {'/'.join(str(p) for p in yol)} :: {m}" for v, yol, m in hatalar
        )
        kosum.kalkar(test_id, aciklama, "beklenmeyen hata(lar): " + ayrinti)
    else:
        kosum.gecer(test_id, aciklama)


def bekle_hata(kosum, test_id, aciklama, hatalar, validator_adi, json_yolu, mesaj_parcasi):
    """Mesaj parcasi + validator anahtari + json_path birlikte eslesmeli."""
    eslesen = [
        (v, yol, m)
        for v, yol, m in hatalar
        if v == validator_adi and list(yol) == list(json_yolu) and mesaj_parcasi in m
    ]
    if eslesen:
        kosum.gecer(test_id, aciklama)
        return
    # Teshis icin ayni yoldaki hatalari da raporla
    ayni_yol = [(v, m) for v, yol, m in hatalar if list(yol) == list(json_yolu)]
    ayrinti = (
        f"beklenen validator={validator_adi!r} yol={list(json_yolu)!r} "
        f"mesaj~={mesaj_parcasi!r}; ayni yolda gorulen={ayni_yol!r}; "
        f"tum hatalar="
        + "; ".join(f"[{v}] {'/'.join(str(p) for p in yol)} :: {m}" for v, yol, m in hatalar)
    )
    kosum.kalkar(test_id, aciklama, ayrinti)
