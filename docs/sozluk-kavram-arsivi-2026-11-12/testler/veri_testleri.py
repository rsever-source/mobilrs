# -*- coding: utf-8 -*-
"""Asama 1 - VERI (icerik) testleri: D1-D7.

Bu dosya semayla uygulanamayan kurallari olcer:
  D1 kavram_id tekilligi
  D2 ayni kayitta ayni icd10.kod tekrari
  D3 takvim gecerliligi (rg_tarihi, kaynak.erisim_tarihi, icd10[].erisim_tarihi)
  D4 es anlamlida ayni dil + ayni termin (farkli kaynakla bile) tekrari
  D5 data icindeki who_etiketi'nin kanit dosyasiyla birebir uyumu
  D6 kanit dosyasinin butunlugu (8/8 kod, ham JsonGetConcept yaniti)
  D7 bolum basina madde sayimi (gercek OCR sayimi Asama 2-A'da baglanacak)

GERCEK VERI UYARISI: `sozluk_kavram_data.json` bu asamada URETILMEZ. Bu yuzden
D1-D5 ve D7, kuralin gercekten yakaladigini gostermek icin sentetik kusurlu
kayitlarla (regresyon testi) dogrulanir; gercek veri Asama 2'de baglanacaktir.
D6 ise GERCEK kanit dosyasi uzerinde calisir.
"""
import hashlib
import html as html_mod
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ortak import KOK, RAPOR_DIR, Kosum, ek1, ek2, uygula  # noqa: E402

KANIT_YOLU = KOK / "kanit" / "icd10_who.json"
BEKLENEN_KODLAR = ["H54.1", "H90.3", "H91.1", "H92.0", "H28.1", "H93.3", "E70", "E78"]
API_TABAN = "https://icd.who.int/browse10/2019/en/JsonGetConcept?ConceptId="


# --- D1 ----------------------------------------------------------------------
def kavram_id_tekilligi(kayitlar):
    sorunlar = []
    gorulen = {}
    for i, kayit in enumerate(kayitlar):
        kid = kayit.get("kavram_id")
        if kid in gorulen:
            sorunlar.append(
                f"D1: kavram_id tekrari {kid!r} (kayit {gorulen[kid]} ve {i})"
            )
        else:
            gorulen[kid] = i
    return sorunlar


# --- D2 ----------------------------------------------------------------------
def icd10_kod_tekrari(kayitlar):
    sorunlar = []
    for i, kayit in enumerate(kayitlar):
        kodlar = [
            o.get("kod") for o in kayit.get("ek_2_baglantisi", {}).get("icd10", [])
        ]
        tekrar = sorted({k for k in kodlar if kodlar.count(k) > 1})
        if tekrar:
            sorunlar.append(
                f"D2: kayit {i} ({kayit.get('kavram_id')}) icinde ayni icd10.kod tekrarli: {tekrar}"
            )
    return sorunlar


# --- D3 ----------------------------------------------------------------------
def _tarih_gecerli(metin, bicim):
    try:
        okunan = datetime.strptime(metin, bicim)
    except (TypeError, ValueError):
        return False
    return okunan.strftime(bicim) == metin


def tarih_gecerlilik(kayitlar):
    sorunlar = []
    for i, kayit in enumerate(kayitlar):
        kid = kayit.get("kavram_id", f"#{i}")

        rg = kayit.get("kaynak", {}).get("rg_tarihi")
        if rg is not None and not _tarih_gecerli(rg, "%d.%m.%Y"):
            sorunlar.append(f"D3: {kid} kaynak.rg_tarihi takvimde gecersiz: {rg!r}")

        erisim = kayit.get("kaynak", {}).get("erisim_tarihi")
        if erisim is not None and not _tarih_gecerli(erisim, "%Y-%m-%d"):
            sorunlar.append(
                f"D3: {kid} kaynak.erisim_tarihi takvimde gecersiz: {erisim!r}"
            )

        for j, oge in enumerate(kayit.get("ek_2_baglantisi", {}).get("icd10", [])):
            tarih = oge.get("erisim_tarihi")
            if tarih is not None and not _tarih_gecerli(tarih, "%Y-%m-%d"):
                sorunlar.append(
                    f"D3: {kid} icd10[{j}].erisim_tarihi takvimde gecersiz: {tarih!r}"
                )
    return sorunlar


# --- D4 ----------------------------------------------------------------------
def es_anlamli_tekrari(kayitlar):
    sorunlar = []
    for i, kayit in enumerate(kayitlar):
        kid = kayit.get("kavram_id", f"#{i}")
        gruplar = {}
        for oge in kayit.get("es_anlamli", []):
            anahtar = (oge.get("dil"), oge.get("termin"))
            gruplar.setdefault(anahtar, []).append(oge.get("kaynak"))
        for (dil, termin), kaynaklar in gruplar.items():
            if len(kaynaklar) > 1:
                sorunlar.append(
                    f"D4: {kid} icinde ayni dil+termin tekrarli: dil={dil!r} "
                    f"termin={termin!r} kaynaklar={kaynaklar!r}"
                )
    return sorunlar


# --- D5 ----------------------------------------------------------------------
def kanit_indeksi(kanit):
    return {k["kod"]: k for k in kanit.get("kayitlar", [])}


def who_etiket_tutarliligi(kayitlar, kanit):
    sorunlar = []
    indeks = kanit_indeksi(kanit)
    for i, kayit in enumerate(kayitlar):
        kid = kayit.get("kavram_id", f"#{i}")
        for j, oge in enumerate(kayit.get("ek_2_baglantisi", {}).get("icd10", [])):
            kod = oge.get("kod")
            referans = indeks.get(kod)
            if referans is None:
                sorunlar.append(f"D5: {kid} icd10[{j}] kodu {kod!r} kanit dosyasinda yok")
                continue
            if oge.get("who_etiketi") != referans.get("secilen_etiket"):
                sorunlar.append(
                    f"D5: {kid} icd10[{j}] who_etiketi kanitla uyusmuyor: "
                    f"veri={oge.get('who_etiketi')!r} kanit={referans.get('secilen_etiket')!r}"
                )
            if oge.get("kaynak_url") != referans.get("sorgu_url"):
                sorunlar.append(
                    f"D5: {kid} icd10[{j}] kaynak_url kanittaki sorgu_url ile ayni degil"
                )
    return sorunlar


# --- D6 ----------------------------------------------------------------------
def _html_metne(html):
    metin = re.sub(r"<[^>]+>", " ", html)
    metin = html_mod.unescape(metin).replace("\xa0", " ")
    return re.sub(r"\s+", " ", metin).strip()


def kanit_butunlugu(kanit):
    sorunlar = []
    if kanit.get("surum") != "ICD-10 Version:2019":
        sorunlar.append(f"D6: surum beklenen 'ICD-10 Version:2019', bulunan {kanit.get('surum')!r}")
    if not kanit.get("erisim_tarihi") or not _tarih_gecerli(kanit.get("erisim_tarihi"), "%Y-%m-%d"):
        sorunlar.append(f"D6: erisim_tarihi gecersiz: {kanit.get('erisim_tarihi')!r}")

    kayitlar = kanit.get("kayitlar", [])
    kodlar = [k.get("kod") for k in kayitlar]
    if len(kodlar) != len(set(kodlar)):
        sorunlar.append("D6: kanit dosyasinda ayni kod birden fazla kez var")
    eksik = [k for k in BEKLENEN_KODLAR if k not in kodlar]
    fazla = [k for k in kodlar if k not in BEKLENEN_KODLAR]
    if eksik:
        sorunlar.append(f"D6: kanit dosyasinda eksik kod(lar): {eksik}")
    if fazla:
        sorunlar.append(f"D6: kanit dosyasinda beklenmeyen kod(lar): {fazla}")

    for kayit in kayitlar:
        kod = kayit.get("kod")
        if kayit.get("sorgu_turu") != "tek_kavram":
            sorunlar.append(f"D6: {kod} sorgu_turu 'tek_kavram' degil")
        beklenen_url = API_TABAN + kod
        if kayit.get("sorgu_url") != beklenen_url:
            sorunlar.append(f"D6: {kod} sorgu_url beklenenden farkli: {kayit.get('sorgu_url')!r}")
        ham = kayit.get("ham_yanit")
        if not isinstance(ham, str) or not ham.strip():
            sorunlar.append(f"D6: {kod} ham_yanit bos")
            continue
        if kayit.get("ham_yanit_sha256") != hashlib.sha256(ham.encode("utf-8")).hexdigest():
            sorunlar.append(f"D6: {kod} ham_yanit_sha256 uyusmuyor")
        try:
            veri = json.loads(ham)
        except json.JSONDecodeError as exc:
            sorunlar.append(f"D6: {kod} ham_yanit gecerli JSON degil: {exc}")
            continue
        if veri.get("ID") != kod:
            sorunlar.append(f"D6: {kod} ham yanitin ID alani {veri.get('ID')!r}")
        if "JsonGetConcept" not in (kayit.get("sorgu_url") or ""):
            sorunlar.append(f"D6: {kod} sorgu_url JsonGetConcept degil")
        etiket = kayit.get("secilen_etiket") or ""
        if not etiket:
            sorunlar.append(f"D6: {kod} secilen_etiket bos")
        elif etiket not in _html_metne(veri.get("html", "")):
            sorunlar.append(f"D6: {kod} secilen_etiket ham yanit HTML'inde bulunamadi")
    return sorunlar


# --- D7 ----------------------------------------------------------------------
def bolum_madde_sayisi(sayim, beklenen):
    """sayim: {"A": 12, ...} OCR'dan gelen madde sayilari."""
    sorunlar = []
    for bolum, beklenen_adet in beklenen.items():
        bulunan = sayim.get(bolum)
        if bulunan is None:
            sorunlar.append(f"D7: {bolum} bolumu sayimda yok")
        elif bulunan != beklenen_adet:
            sorunlar.append(
                f"D7: {bolum} bolumu icin beklenen {beklenen_adet}, sayilan {bulunan}"
            )
    return sorunlar


# --- kosum -------------------------------------------------------------------
def main():
    kosum = Kosum("Asama 1 - Icerik (veri) denetimi")
    kanit = json.loads(KANIT_YOLU.read_text(encoding="utf-8"))

    # D6: gercek kanit dosyasi
    sorunlar = kanit_butunlugu(kanit)
    if sorunlar:
        kosum.kalkar("D6", "Kanit dosyasi butunlugu (GERCEK dosya)", "; ".join(sorunlar))
    else:
        kosum.gecer(
            "D6",
            f"Kanit dosyasi butunlugu: {len(kanit['kayitlar'])}/8 kod, her biri ayri "
            "JsonGetConcept ham yaniti + tam URL + surum + erisim tarihi",
        )

    # D1: tekillik (regresyon)
    kusurlu = [ek1(), ek2(), uygula(ek2(), ["kavram_id"], ek1()["kavram_id"])]
    sorunlar = kavram_id_tekilligi(kusurlu)
    if any("kavram_id tekrari" in s for s in sorunlar):
        kosum.gecer("D1", "kavram_id tekilligi ihlali yakalaniyor (regresyon)")
    else:
        kosum.kalkar("D1", "kavram_id tekilligi", f"yakalanmadi: {sorunlar}")

    # D2: ayni kod tekrari (regresyon)
    tekrarli = uygula(
        ek2(),
        ["ek_2_baglantisi", "icd10"],
        [
            {
                "kod": "H90.3",
                "who_etiketi": "Sensorineural hearing loss, bilateral",
                "kaynak_url": API_TABAN + "H90.3",
                "erisim_tarihi": "2026-11-11",
            },
            {
                "kod": "H90.3",
                "who_etiketi": "Baska etiket",
                "kaynak_url": API_TABAN + "H90.3",
                "erisim_tarihi": "2026-11-11",
            },
        ],
    )
    sorunlar = icd10_kod_tekrari([tekrarli])
    if sorunlar:
        kosum.gecer("D2", "Ayni kayitta ayni icd10.kod tekrari yakalaniyor (regresyon)")
    else:
        kosum.kalkar("D2", "Ayni kayitta ayni icd10.kod tekrari", "yakalanmadi")

    # D3: takvim gecerliligi - uc alan, dort kusur
    vakalar = {
        "rg_tarihi 31.02.2021": uygula(ek1(), ["kaynak", "rg_tarihi"], "31.02.2021"),
        "rg_tarihi 29.02.2021 (artik yil degil)": uygula(
            ek1(), ["kaynak", "rg_tarihi"], "29.02.2021"
        ),
        "kaynak.erisim_tarihi 2026-02-30": uygula(
            ek1(), ["kaynak", "erisim_tarihi"], "2026-02-30"
        ),
        "icd10.erisim_tarihi 2026-13-01": uygula(
            ek2(), ["ek_2_baglantisi", "icd10", 0, "erisim_tarihi"], "2026-13-01"
        ),
    }
    yakalanmayan = []
    for ad, kayit in vakalar.items():
        if not tarih_gecerlilik([kayit]):
            yakalanmayan.append(ad)
    if yakalanmayan:
        kosum.kalkar("D3", "Takvim gecerliligi", f"yakalanmayan: {yakalanmayan}")
    else:
        kosum.gecer(
            "D3",
            "Takvim gecerliligi: rg_tarihi + kaynak.erisim_tarihi + icd10.erisim_tarihi "
            "kusurlari yakalaniyor (31.02, 29.02.2021, 2026-02-30, 2026-13-01)",
        )
    if tarih_gecerlilik([ek1(), ek2()]):
        kosum.kalkar("D3b", "Gecerli tarihli kayitlar temiz gecer", str(tarih_gecerlilik([ek1(), ek2()])))
    else:
        kosum.gecer("D3b", "Gecerli tarihli kayitlar (28.09.2021 / 20.02.2019 / erisim) temiz gecer")

    # D4: ayni dil+termin, farkli kaynak
    kusurlu = uygula(
        ek1(),
        ["es_anlamli"],
        [
            {"dil": "tr", "termin": "sagir", "kaynak": "mevzuat"},
            {"dil": "tr", "termin": "sagir", "kaynak": "site_verisi"},
        ],
    )
    sorunlar = es_anlamli_tekrari([kusurlu])
    if any("dil+termin tekrarli" in s for s in sorunlar):
        kosum.gecer(
            "D4",
            "Ayni dil + ayni termin farkli kaynakla tekrarlanirsa yakalaniyor (duzeltme 4)",
        )
    else:
        kosum.kalkar("D4", "Ayni dil + ayni termin tekrari", f"yakalanmadi: {sorunlar}")

    # D4b: farkli dil ayni termin -> kabul
    kabul = uygula(
        ek1(),
        ["es_anlamli"],
        [{"dil": "tr", "termin": "sagir"}, {"dil": "en", "termin": "deaf"}],
    )
    if es_anlamli_tekrari([kabul]):
        kosum.kalkar("D4b", "Farkli dil + farkli termin kabul edilmeli", str(es_anlamli_tekrari([kabul])))
    else:
        kosum.gecer("D4b", "Farkli dil + farkli termin tekrar sayilmiyor")

    # D5: WHO etiketi / URL kanitle birebir
    indeks = kanit_indeksi(kanit)
    uygun = uygula(
        ek2(),
        ["ek_2_baglantisi", "icd10"],
        [
            {
                "kod": kod,
                "who_etiketi": indeks[kod]["secilen_etiket"],
                "kaynak_url": indeks[kod]["sorgu_url"],
                "erisim_tarihi": kanit["erisim_tarihi"],
            }
            for kod in BEKLENEN_KODLAR
        ],
    )
    sorunlar = who_etiket_tutarliligi([uygun], kanit)
    if sorunlar:
        kosum.kalkar("D5", "8 kodun tamami kanitle birebir uyumlu", "; ".join(sorunlar))
    else:
        kosum.gecer("D5", "8 kodun tamami kanit dosyasindaki etiket ve URL ile birebir uyumlu")

    bozuk = uygula(
        ek2(), ["ek_2_baglantisi", "icd10", 0, "who_etiketi"], "Uydurma etiket"
    )
    if any("who_etiketi kanitla uyusmuyor" in s for s in who_etiket_tutarliligi([bozuk], kanit)):
        kosum.gecer("D5b", "Uydurma WHO etiketi yakalaniyor (regresyon)")
    else:
        kosum.kalkar("D5b", "Uydurma WHO etiketi", "yakalanmadi")

    # D6b: kanit butunlugunun kendisi de kusuru yakalamali (regresyon)
    eksik = dict(kanit)
    eksik["kayitlar"] = kanit["kayitlar"][:-1]
    bulunan = kanit_butunlugu(eksik)
    if any("eksik kod" in s for s in bulunan):
        kosum.gecer("D6b", "Kanit dosyasindan bir kod eksiltilirse yakalaniyor (regresyon)")
    else:
        kosum.kalkar("D6b", "Eksik kod regresyonu", f"yakalanmadi: {bulunan}")

    # D7: bolum basina madde sayimi altyapisi (gercek OCR sayimi Asama 2-A)
    sayim = {"A": 12, "B": 7}
    if not bolum_madde_sayisi(sayim, {"A": 12, "B": 7}):
        kosum.gecer("D7", "Bolum basina madde sayimi altyapisi calisiyor (tutarlı sayim)")
    else:
        kosum.kalkar("D7", "Bolum madde sayimi altyapisi", str(bolum_madde_sayisi(sayim, {"A": 12, "B": 7})))
    if any("beklenen 13" in s for s in bolum_madde_sayisi(sayim, {"A": 13})):
        kosum.gecer("D7b", "Sayim uyusmazligi yakalaniyor (regresyon)")
    else:
        kosum.kalkar("D7b", "Sayim uyusmazligi", "yakalanmadi")
    print(
        "      not: D7 gercek veriyle Aşama 2-A'da kosacak; bu asamada yalniz "
        "altyapi ve regresyon dogrulandi."
    )

    return kosum.ozet_yaz(RAPOR_DIR / "icerik_sonuc.json")


if __name__ == "__main__":
    sys.exit(0 if main() == "PASS" else 1)
