# -*- coding: utf-8 -*-
"""Bulanık kanıt izlerinin dağılımı ve inceleme listesi."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ARSIV = Path(__file__).resolve().parents[1]


def main():
    izler = json.loads((ARSIV / "data" / "sozluk_kavram_kaynak_izleri.json").read_text(encoding="utf-8"))
    veri = json.loads((ARSIV / "data" / "sozluk_kavram_data.json").read_text(encoding="utf-8"))
    konum = {k["kavram_id"]: k for k in veri}
    bulanik = [i for i in izler if i["durum"] == "bulanik"]
    print("bulanik:", len(bulanik))
    ek1 = sum(1 for i in bulanik if "ek_1_baglantisi" in konum[i["kavram_id"]])
    print("ek1:", ek1, "ek2:", len(bulanik) - ek1)
    sayfa = Counter(konum[i["kavram_id"]]["kaynak"]["sayfa_no"] for i in bulanik)
    print("sayfa sayisi:", len(sayfa))
    print("sayfa dagilimi:", sorted(sayfa.items()))
    skor = Counter(round(i.get("skor", 0), 2) for i in bulanik)
    print("skor:", sorted(skor.items()))
    # ornek
    for i in bulanik[:3]:
        k = konum[i["kavram_id"]]
        print(json.dumps({"id": i["kavram_id"], "sayfa": k["kaynak"]["sayfa_no"],
                          "ad": k["kanonik_ad"], "kanit": i["kanit"], "skor": i.get("skor")},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
