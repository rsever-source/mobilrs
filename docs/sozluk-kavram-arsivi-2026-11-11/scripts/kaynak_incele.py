# -*- coding: utf-8 -*-
"""Kaynak OCR dosyalarini incele: kodlama, boyut, ilk satirlar, sayfa numarasi izleri."""
import re
from pathlib import Path

TXT = Path(r"%TEMP%\o05\txt")
for ad in ("ek1_001", "ek1_002", "ek1_010", "ek1_040", "ek2_001", "ek2_002", "ek2_003", "ek2_169", "ek2_170", "ek2_172"):
    yol = TXT / f"{ad}.txt"
    ham = yol.read_bytes()
    for kodlama in ("utf-8", "cp1254"):
        try:
            metin = ham.decode(kodlama)
            break
        except UnicodeDecodeError:
            metin = None
    if metin is None:
        print(f"--- {ad}: COZULEMEDI ilk baytlar {ham[:20]!r}")
        continue
    satirlar = metin.splitlines()
    print(f"--- {ad} ({len(ham)} bayt, {kodlama}, {len(satirlar)} satir)")
    for i, s in enumerate(satirlar[:6]):
        print(f"   {i+1:3d}| {s[:110]}")
    print("   ... son 4 satir:")
    for s in satirlar[-4:]:
        print(f"      | {s[:110]}")
    sayilar = [s.strip() for s in satirlar if re.fullmatch(r"\d{1,3}", s.strip())]
    print(f"   tek basina sayi satirlari: {sayilar[:10]}")