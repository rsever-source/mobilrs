# -*- coding: utf-8 -*-
"""Görsel doğrulama notlarının kapsam denetimi (99 kayıt)."""
import json
from collections import Counter
from pathlib import Path

ARSIV = Path(__file__).resolve().parents[1]
NOTLAR = Path(r"C:\Users\RIDVAN\AppData\Local\Temp\ek2_notlar.md")


def main():
    rows = [l.split("\t") for l in NOTLAR.read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("#")]
    kontrol = json.loads((ARSIV / "raporlar" / "ek2_kavram_kanit_kontrol.json").read_text(encoding="utf-8"))
    hedef = {(x["sayfa"], x["kanonik_ad"]) for x in kontrol["kayitlar"] if not x["ad_ham_satirda"]}
    notset = {(int(r[0]), r[1]) for r in rows}
    print("not satiri:", len(rows), "hedef:", len(hedef))
    print("eksik:", len(hedef - notset))
    for x in sorted(hedef - notset):
        print("  EKSIK", x)
    print("fazla:", len(notset - hedef))
    for x in sorted(notset - hedef):
        print("  FAZLA", x)
    print("durum:", dict(Counter(r[3] for r in rows)))


if __name__ == "__main__":
    main()
