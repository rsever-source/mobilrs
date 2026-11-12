# -*- coding: utf-8 -*-
"""Nihai verinin bagimsiz denetimi: sema (v1.0.0 + v1.0.3), XOR, kimlik, kaynak, sayfa."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "testler"))

import ortak  # noqa: E402

VERI = KOK / "data" / "sozluk_kavram_data.json"
SEMA_100 = KOK / "schema" / "sozluk_kavram.v1.0.0.json"
SEMA_103 = KOK / "schema" / "sozluk_kavram.v1.0.3_taslak.json"


def dogrula(sema_yolu, kayitlar, etiket):
    sema = json.loads(sema_yolu.read_text(encoding="utf-8-sig"))
    v = ortak.dogrulayici(sema)
    hatali = {}
    for i, k in enumerate(kayitlar):
        hatalar = ortak.tum_hatalar(v, k)
        if hatalar:
            hatali.setdefault(i, []).append(
                "; ".join(f"[{h[0]}] {'/'.join(map(str, h[1]))} :: {h[2]}" for h in hatalar)
            )
    print(f"{etiket}: {len(kayitlar) - len(hatali)}/{len(kayitlar)} PASS")
    for i, h in list(hatali.items())[:10]:
        print(f"  #{i} {kayitlar[i]['kavram_id']}: {h[0][:220]}")
    if len(hatali) > 10:
        print(f"  ... toplam hatali {len(hatali)}")
    return hatali


def main():
    kayitlar = json.loads(VERI.read_text(encoding="utf-8"))
    print(f"dosya: {VERI.name} boyut={VERI.stat().st_size} kayit={len(kayitlar)}")

    h100 = dogrula(SEMA_100, kayitlar, "v1.0.0")
    h103 = dogrula(SEMA_103, kayitlar, "v1.0.3")

    # kimlik
    idler = [k["kavram_id"] for k in kayitlar]
    print(f"benzersiz kavram_id: {len(set(idler))}/{len(idler)}")
    print(f"ek1_ onekli: {sum(1 for i in idler if i.startswith('ek1_'))}")
    print(f"ek2_ onekli: {sum(1 for i in idler if i.startswith('ek2_'))}")
    print(f"farkli onek: {[i[:4] for i in idler if not i.startswith(('ek1_', 'ek2_'))][:5]}")

    # XOR + onek uyumu
    xor_hata = []
    for k in kayitlar:
        e1 = "ek_1_baglantisi" in k
        e2 = "ek_2_baglantisi" in k
        if e1 == e2:
            xor_hata.append(k["kavram_id"])
        if e1 and not k["kavram_id"].startswith("ek1_"):
            xor_hata.append("onek:" + k["kavram_id"])
        if e2 and not k["kavram_id"].startswith("ek2_"):
            xor_hata.append("onek:" + k["kavram_id"])
    print(f"XOR/onek hatasi: {len(xor_hata)} {xor_hata[:5]}")

    # kaynak
    rg_hata = []
    sayfa_hata = []
    for k in kayitlar:
        if "ek_1_baglantisi" in k:
            if k["kaynak"]["rg_sayisi"] != 31612 or k["kaynak"]["rg_tarihi"] != "28.09.2021":
                rg_hata.append(k["kavram_id"])
            if not (1 <= k["kaynak"].get("sayfa_no", 0) <= 40):
                sayfa_hata.append(k["kavram_id"])
        else:
            if k["kaynak"]["rg_sayisi"] != 30692 or k["kaynak"]["rg_tarihi"] != "20.02.2019":
                rg_hata.append(k["kavram_id"])
            if k["kaynak"].get("mbs_no") != 31275:
                rg_hata.append("mbs:" + k["kavram_id"])
            if not (3 <= k["kaynak"].get("sayfa_no", 0) <= 169):
                sayfa_hata.append(k["kavram_id"])
    print(f"RG kunye hatasi: {len(rg_hata)} {rg_hata[:5]}")
    print(f"sayfa_no aralik hatasi: {len(sayfa_hata)} {sayfa_hata[:5]}")

    # ICD yalniz EK-2
    icd_ek1 = [k["kavram_id"] for k in kayitlar if "ek_1_baglantisi" in k and "icd10" in k.get("ek_1_baglantisi", {})]
    icd_sayisi = sum(len(k.get("ek_2_baglantisi", {}).get("icd10", [])) for k in kayitlar)
    print(f"EK-1'de ICD: {len(icd_ek1)}; EK-2 ICD kodu toplam: {icd_sayisi}")

    # dagilim
    ek1 = [k for k in kayitlar if "ek_1_baglantisi" in k]
    ek2 = [k for k in kayitlar if "ek_2_baglantisi" in k]
    print(f"\nEK-1 {len(ek1)}, EK-2 {len(ek2)}")
    print("EK-1 derece:", dict(Counter(k["ek_1_baglantisi"]["derece"] for k in ek1)))
    print("EK-1 bolum:", dict(sorted(Counter(k["ek_1_baglantisi"]["bolum_harfi"] for k in ek1).items())))
    print("EK-2 bolum:")
    for b, c in Counter(k["ek_2_baglantisi"]["bolum_adi"] for k in ek2).most_common():
        print(f"   {c:4d}  {b}")
    print("EK-2 sayfa araligi:", min(k["kaynak"]["sayfa_no"] for k in ek2), "-", max(k["kaynak"]["sayfa_no"] for k in ek2))
    print("EK-2 tanimli:", sum(1 for k in ek2 if "tanim" in k["ek_2_baglantisi"]))
    print("EK-2 madde_etiketi:", sum(1 for k in ek2 if "madde_etiketi" in k["ek_2_baglantisi"]))
    print("es_anlamli dolu:", sum(1 for k in kayitlar if k["es_anlamli"]))

    # EK-1 ayni bolum+sira icin derece tekrari
    anahtar = Counter(
        (k["ek_1_baglantisi"]["bolum_harfi"], k["ek_1_baglantisi"]["sira_no"], k["ek_1_baglantisi"]["derece"])
        for k in ek1
    )
    print("EK-1 bolum+sira+derece tekrari:", [a for a, c in anahtar.items() if c > 1])

    # rapor
    rapor = {
        "dosya": VERI.name,
        "boyut": VERI.stat().st_size,
        "kayit": len(kayitlar),
        "ek1": len(ek1),
        "ek2": len(ek2),
        "sema_v1_0_0_hatali": len(h100),
        "sema_v1_0_3_hatali": len(h103),
        "kimlik_benzersiz": len(set(idler)) == len(idler),
        "xor_hata": xor_hata,
        "rg_hata": rg_hata,
        "sayfa_hata": sayfa_hata,
        "icd_kodu": icd_sayisi,
    }
    (KOK / "raporlar" / "asama2_yapisal_sonuc.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
