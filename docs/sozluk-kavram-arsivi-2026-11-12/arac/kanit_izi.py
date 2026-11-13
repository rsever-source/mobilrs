# -*- coding: utf-8 -*-
"""Kayit basina kanit izi eslestirmesi ve eslesme oraninin olculmesi.

- EK-1: arac/parca/u1,u2 icindeki kanit_metin (birebir).
- EK-2 s.25-169: arac/ek2_25_169_kayitlar.json ham_satir (birebir).
- EK-2 s.3-24: sayfa OCR metninde ada en yakin satir (difflib); zayifsa bos.
"""
import difflib
import json
import re
from collections import Counter
from pathlib import Path

K = Path(__file__).resolve().parents[1]
PARCALAR = K / "arac" / "parca"
TXT = K / "kaynak" / "txt"


def norm(s):
    s = s.replace("İ", "I").replace("ı", "i").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def sayfa_metni(n):
    yol = TXT / f"ek2_{n:03d}.txt"
    if not yol.exists():
        return []
    return [s.strip() for s in yol.read_text(encoding="utf-8", errors="replace").splitlines() if s.strip()]


def en_iyi_satir(ad, satirlar):
    """Sayfa satirlarindan ada en yakin kanit penceresini secer.

    Uzun kavram adlari OCR'da 2-3 satira bolunebildigi icin tek satir yaninda
    2 ve 3 satirlik pencereler de denenir.
    """
    hedef = norm(ad)
    adaylar = []
    for i in range(len(satirlar)):
        adaylar.append(" ".join(satirlar[i : i + 1]))
        if i + 1 < len(satirlar):
            adaylar.append(" ".join(satirlar[i : i + 2]))
        if i + 2 < len(satirlar):
            adaylar.append(" ".join(satirlar[i : i + 3]))
    en, skor = "", 0.0
    for s in adaylar:
        n = norm(s)
        if not n:
            continue
        if hedef and hedef in n:
            # adi iceren en kisa pencere en iyi kanittir
            if skor < 1.0 or len(s) < len(en):
                en, skor = s, 1.0
            continue
        if skor >= 1.0:
            continue
        oran = difflib.SequenceMatcher(None, hedef, n).ratio()
        if oran > skor:
            en, skor = s, oran
    return en, skor


def main():
    veri = json.loads((K / "data" / "sozluk_kavram_data.json").read_text(encoding="utf-8"))

    ek1_kanit = {}
    for ad in ("u1_ek1_001_020.json", "u2_ek1_021_040.json"):
        d = json.loads((PARCALAR / ad).read_text(encoding="utf-8"))
        for k in d["kayitlar"]:
            anahtar = (k["bolum_harfi"], k["sira_no"], k["derece"], k["kanonik_ad"])
            ek1_kanit.setdefault(anahtar, k.get("kanit_metin", ""))

    ek2_sec = {}
    for k in json.loads((K / "arac" / "ek2_25_169_kayitlar.json").read_text(encoding="utf-8")):
        ek2_sec.setdefault((int(re.search(r"(\d{3})$", k["sayfa"]).group(1)), norm(k["kanonik_ad"])), k)

    # EK-2 s.3-24 (u3b) kaynak satirlari. Kaynak metin bazen iki satira
    # bolunmus olur; bu kayitlarda kanit metni parca dosyasindaki "tanim"
    # alanindan (OCR metninin birebir birlestirilmis hali) alinir.
    ek2_u3b_kanit = {}
    for k in json.loads((PARCALAR / "u3b_ek2_003_024.json").read_text(encoding="utf-8"))["kayitlar"]:
        if k.get("tanim"):
            ek2_u3b_kanit.setdefault(
                (int(re.search(r"(\d{3})$", k["sayfa"]).group(1)), norm(k["kanonik_ad"])), k["tanim"]
            )

    # EK-2 secim kayitlari icin birebir kaynak satiri eslesmesi (duzeltilmis adlar dahil)
    ek2_eslesme = {
        x["kavram_id"]: x
        for x in json.loads((K / "arac" / "ek2_kaynak_eslesme.json").read_text(encoding="utf-8"))
    }

    izler = []
    eslesme = Counter()
    for k in veri:
        if "ek_1_baglantisi" in k:
            b = k["ek_1_baglantisi"]
            kanit = ek1_kanit.get((b["bolum_harfi"], b["sira_no"], b["derece"], k["kanonik_ad"]), "")
            izler.append({"kavram_id": k["kavram_id"], "kanit": kanit, "durum": "birebir" if kanit else "yok"})
            eslesme["ek1_birebir" if kanit else "ek1_yok"] += 1
            continue
        sayfa = k["kaynak"]["sayfa_no"]
        sec = ek2_eslesme.get(k["kavram_id"])
        if sec:
            izler.append({"kavram_id": k["kavram_id"], "kanit": sec["ham_satir"], "durum": sec["durum"]})
            eslesme[f"ek2_{sec['durum']}"] += 1
            continue
        # Önce u3b_kanit'i kontrol et (parca dosyasından tanim)
        kanit = ek2_u3b_kanit.get((sayfa, norm(k["kanonik_ad"])), "")
        if kanit:
            izler.append({"kavram_id": k["kavram_id"], "kanit": kanit, "durum": "duzeltilmis"})
            eslesme["ek2_duzeltilmis"] += 1
            continue
        
        sec = ek2_sec.get((sayfa, norm(k["kanonik_ad"])))
        if sec and sec.get("ham_satir"):
            izler.append({"kavram_id": k["kavram_id"], "kanit": sec["ham_satir"], "durum": "birebir"})
            eslesme["ek2_birebir"] += 1
            continue
        satir, skor = en_iyi_satir(k["kanonik_ad"], sayfa_metni(sayfa))
        if skor >= 0.80:
            izler.append({"kavram_id": k["kavram_id"], "kanit": satir, "durum": "bulanik", "skor": round(skor, 3)})
            eslesme["ek2_bulanik"] += 1
            continue
        # kaynakta iki satira bolunmus metinler: parca dosyasindaki kaynak
        # metni (OCR satirlarinin birlestirilmis hali) kanit olarak kullanilir
        izler.append({"kavram_id": k["kavram_id"], "kanit": "", "durum": "yok", "skor": round(skor, 3)})
        eslesme["ek2_yok"] += 1
        print(f"ESLESMEDI {skor:.2f} s{sayfa} {k['kanonik_ad'][:70]}")

    (K / "data" / "sozluk_kavram_kaynak_izleri.json").write_text(
        json.dumps(izler, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    print(dict(eslesme))
    print("toplam iz:", len(izler))


if __name__ == "__main__":
    main()
