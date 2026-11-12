# -*- coding: utf-8 -*-
"""ek2_ek_kayitlar.json dogrulama: tekrar, sayfa, kanit satiri.

Karsilastirma tabani: veri dosyasinda AYNI sayfada AYNI adi tasiyan kayitlar
(yeni derlemenin kendisi) yok sayilir; boylece betik, veri dosyasi birlesmis
olsa da ayni sonucu verir.
"""
import json
import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
ARAC = KOK / "arac"
TXT = KOK / "kaynak" / "txt"
VERI = KOK / "data" / "sozluk_kavram_data.json"


def norm(s):
    s = s.replace("İ", "I").replace("ı", "i").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def main():
    yeni = json.loads((ARAC / "ek2_ek_kayitlar.json").read_text(encoding="utf-8"))
    mevcut = json.loads(VERI.read_text(encoding="utf-8"))

    yeni_anahtar = {(int(k["sayfa"][-3:]), norm(k["kanonik_ad"])) for k in yeni}
    mevcut_ad = {}
    for r in mevcut:
        if "ek_2_baglantisi" in r:
            anahtar = (r["kaynak"]["sayfa_no"], norm(r["kanonik_ad"]))
            if anahtar in yeni_anahtar:
                continue
            mevcut_ad.setdefault(norm(r["kanonik_ad"]), []).append(r["kavram_id"])

    hata = []
    uyari = []
    gorulen = {}
    for k in yeni:
        n = norm(k["kanonik_ad"])
        if n in gorulen:
            hata.append(f"YENI TEKRAR: {k['kanonik_ad']} <-> {gorulen[n]}")
        gorulen[n] = k["kanonik_ad"]
        if n in mevcut_ad:
            hata.append(f"MEVCUT TEKRAR: {k['kanonik_ad']} ({mevcut_ad[n]})")

        sayfa = int(k["sayfa"][-3:])
        yol = TXT / f"ek2_{sayfa:03d}.txt"
        metin = yol.read_text(encoding="utf-8")
        metin_n = " ".join(metin.split())
        ham_n = " ".join(k["ham_satir"].split())
        if ham_n not in metin_n and ham_n[:40] not in metin_n:
            hata.append(f"KANIT YOK s{sayfa}: {k['kanonik_ad']} :: {k['ham_satir'][:70]}")

    print(f"yeni kayit: {len(yeni)}")
    print(f"hata: {len(hata)}")
    for h in hata:
        print(" -", h)
    if uyari:
        print(f"uyari: {len(uyari)}")
        for u in uyari:
            print(" *", u)


if __name__ == "__main__":
    main()
