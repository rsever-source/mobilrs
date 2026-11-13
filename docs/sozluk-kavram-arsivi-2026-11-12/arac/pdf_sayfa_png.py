# -*- coding: utf-8 -*-
"""PDF sayfalarını görüntü olarak dışa aktarır (görsel doğrulama için).

Kullanım:
    python -X utf8 arac\\pdf_sayfa_png.py 30 34 40
    python -X utf8 arac\\pdf_sayfa_png.py --hepsi

Çıktı: <gecici>/ek2_png/ek2_p030.png
PDF: C:\\Users\\RIDVAN\\AppData\\Local\\Temp\\pdf\\ek2_2019_rg.pdf
"""
import sys
from pathlib import Path

import pymupdf

PDF = Path(r"C:\Users\RIDVAN\AppData\Local\Temp\pdf\ek2_2019_rg.pdf")
OUT = Path(r"C:\Users\RIDVAN\AppData\Local\Temp\ek2_png")
DPI = 150


def render(sayfalar, dpi=DPI, out=OUT, onek="ek2_p"):
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(PDF)
    yollar = []
    for n in sayfalar:
        page = doc[n - 1]
        pix = page.get_pixmap(dpi=dpi)
        yol = out / f"{onek}{n:03d}.png"
        pix.save(yol)
        yollar.append(yol)
    return yollar


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--hepsi":
        sayfalar = list(range(1, 173))
    else:
        sayfalar = [int(a) for a in args]
    for yol in render(sayfalar):
        print(yol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
