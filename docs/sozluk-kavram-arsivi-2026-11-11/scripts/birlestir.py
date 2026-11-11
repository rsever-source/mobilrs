# -*- coding: utf-8 -*-
"""OCR sayfa dosyalarini sayfa isaretleriyle birlestirir."""
from pathlib import Path

TXT = Path(r"%TEMP%\o05\txt")
HEDEF = Path(__file__).resolve().parent

for onek in ("ek1", "ek2"):
    parcalar = []
    for yol in sorted(TXT.glob(f"{onek}_*.txt")):
        metin = yol.read_text(encoding="utf-8", errors="replace")
        parcalar.append(f"===== SAYFA {yol.stem} ({len(metin)} karakter) =====\n{metin}")
    hedef = HEDEF / f"{onek}_birlesik.txt"
    hedef.write_text("\n".join(parcalar), encoding="utf-8")
    print(f"{hedef} -> {sum(len(p) for p in parcalar)} karakter")