# -*- coding: utf-8 -*-
"""Görsel doğrulama listesi: kanonik adı kendi ham_satir'inda bulunmayan kayıtlar.

`raporlar/ek2_kavram_kanit_kontrol.json` çıktısını okur; ad_ham_satirda=false
olan kayıtları sayfaya göre gruplar ve `raporlar/ek2_gorsel_dogrulama_listesi.md`
dosyasını üretir. Veri dosyasına dokunmaz.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KONTROL = ROOT / "raporlar" / "ek2_kavram_kanit_kontrol.json"
OUT = ROOT / "raporlar" / "ek2_gorsel_dogrulama_listesi.md"


def main():
    veri = json.loads(KONTROL.read_text(encoding="utf-8"))
    kayitlar = veri["kayitlar"]
    hedef = [k for k in kayitlar if not k["ad_ham_satirda"]]
    sayfa_grup = defaultdict(list)
    for k in hedef:
        sayfa_grup[k["sayfa"]].append(k)

    satirlar = [
        "# EK-2 görsel doğrulama listesi",
        "",
        "Kaynak: `raporlar/ek2_kavram_kanit_kontrol.json`.",
        "Bu liste, **kanonik adı kendi `ham_satir` alanında bulunmayan** kayıtları",
        "sayfaya göre gruplar. Doğrulama PDF sayfa görüntüsü üzerinden yapılır;",
        "OCR metin benzerliği görsel doğrulama sayılmaz.",
        "",
        f"- Kayıt: **{len(hedef)}**",
        f"- Farklı sayfa: **{len(sayfa_grup)}**",
        "",
        "| Durum (OCR) | Kayıt |",
        "| --- | --- |",
    ]
    for durum in ("ad_sayfada_birebir", "ad_sayfada_yaklasik_inceleme", "ad_sayfada_dogrulanamadi"):
        n = sum(1 for k in hedef if k["durum"] == durum)
        satirlar.append(f"| `{durum}` | {n} |")

    for sayfa in sorted(sayfa_grup):
        satirlar += ["", f"## PDF sayfa {sayfa}", "",
                     "| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |",
                     "| --- | --- | --- | --- | --- | --- |"]
        for i, k in enumerate(sorted(sayfa_grup[sayfa], key=lambda x: x["kanonik_ad"]), 1):
            ham = (k["ham_satir"] or "").replace("|", "\\|")
            ad = k["kanonik_ad"].replace("|", "\\|")
            satirlar.append(
                f"| {i} | {ad} | {ham} | `{k['durum']}` | {k['en_yakin_pencere_skoru']} | (bekliyor) |"
            )
    OUT.write_text("\n".join(satirlar) + "\n", encoding="utf-8", newline="\n")
    print(f"kayıt: {len(hedef)}  sayfa: {len(sayfa_grup)}")
    print(f"rapor: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
