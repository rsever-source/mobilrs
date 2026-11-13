# -*- coding: utf-8 -*-
"""Doğrulanmış kanıt/ad düzeltmelerini uygular.

1) `ek2_s012_frontal_kemikte_egilme`: PDF'te "Frontal kemikte çökme" basılı.
   OCR "eğkme" okuduğu için ad "eğilme" olmuş; kanonik ad düzeltilir.
   kavram_id geriye dönük uyumluluk için değiştirilmez.
2) s.40 "Kontrast duyarlık ve kamaşma (glare) kusuru": kanıt satırı kavramı
   göstermiyordu; yerine basılı başlık konur.
"""
import json
from pathlib import Path

ARSIV = Path(__file__).resolve().parents[1]
ESKI = "Frontal kemikte eğilme"
YENI = "Frontal kemikte çökme"
KID = "ek2_s012_frontal_kemikte_egilme"

# 1) kanonik ad
for yol, girinti, satir_sonu in (
    (ARSIV / "data" / "sozluk_kavram_data.json", 2, ""),
    (ARSIV / "arac" / "parca" / "u3b_ek2_003_024.json", 1, "\n"),
):
    d = json.loads(yol.read_text(encoding="utf-8"))
    kayitlar = d if isinstance(d, list) else d["kayitlar"]
    n = 0
    for k in kayitlar:
        ayni = (
            k.get("kavram_id") == KID
            or (str(k.get("sayfa", "")).endswith("012") and k.get("kanonik_ad") == ESKI)
        )
        if ayni and k["kanonik_ad"] in (ESKI, YENI):
            k["kanonik_ad"] = YENI
            n += 1
    if n != 1:
        raise SystemExit(f"{yol}: beklenen 1, bulunan {n}")
    yol.write_text(json.dumps(d, ensure_ascii=False, indent=girinti) + satir_sonu,
                   encoding="utf-8", newline="\n")
    print("ad düzeltildi:", yol.relative_to(ARSIV))

# 2) s.40 kanıt satırı: OCR metninin ilk 5 satırı (görüntüdeki başlık)
txt = (ARSIV / "kaynak" / "txt" / "ek2_040.txt").read_text(encoding="utf-8")
satirlar = [s.strip() for s in txt.splitlines() if s.strip()]
i = next(i for i, s in enumerate(satirlar) if s.startswith("Klinik olarak anlamlı kontrast"))
kanit = " ".join(satirlar[i:i + 4])
if not kanit.startswith("Klinik olarak anlamlı kontrast duyarlık"):
    raise SystemExit("başlık bulunamadı")
print("s.40 kanıt:", kanit[:90], "...")

yol = ARSIV / "arac" / "ek2_kaynak_eslesme.json"
d = json.loads(yol.read_text(encoding="utf-8"))
n = 0
for x in d:
    if x["kavram_id"].startswith("ek2_s040_kontrast"):
        x["ham_satir"] = kanit
        x["durum"] = "duzeltilmis"
        n += 1
if n != 1:
    raise SystemExit(f"s.40: beklenen 1, bulunan {n}")
yol.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("s.40 kanıt izi düzeltildi")
