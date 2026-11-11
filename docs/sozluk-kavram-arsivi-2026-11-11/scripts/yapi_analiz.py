# -*- coding: utf-8 -*-
"""EK-1 ve EK-2 OCR metninde yapi analizi: bolum, madde, derece bloklari, tablo sayfalari."""
import re
from pathlib import Path

TXT = Path(r"%TEMP%\o05\txt")

SAYFA = re.compile(r"===== SAYFA (\w+) \((\d+) karakter\) =====", re.M)
MADDE = re.compile(r"^\s*(?:(\d{1,2})[.)]|([Ilİ|])[.)])\s*(\S.{0,120})$")
BOLUM1 = re.compile(r"^([A-PR])\.\s+(.+)$")
ORGAN = re.compile(r"^[A-ZÇĞİÖŞÜ0-9 ,.\-()/]{12,}$")
ALT = re.compile(r"^([A-ZÇĞİÖŞÜ])\s*[-–]\s*(.{3,})$")


def sayfalar(onek):
    for yol in sorted(TXT.glob(f"{onek}_*.txt")):
        yield yol.stem, yol.read_text(encoding="utf-8", errors="replace")


def analiz_ek1():
    print("========== EK-1 ==========")
    toplam_madde = 0
    for ad, metin in sayfalar("ek1"):
        satirlar = metin.splitlines()
        bolum = [s for s in satirlar if BOLUM1.match(s) and ("ÇALIŞMA" in s or "ORTAK" in s.upper())]
        maddeler = []
        for s in satirlar:
            m = MADDE.match(s)
            if m and len(m.group(3)) > 3:
                maddeler.append(s.strip()[:80])
        derece = {
            "agir": sum(1 for s in satirlar if re.search(r"A[ğg][ıi]r\s+D[üu]zey", s)),
            "orta": sum(1 for s in satirlar if re.search(r"Orta\s+D[üu]zey", s)),
            "hafif": sum(1 for s in satirlar if re.search(r"Hafif\s+D[üu]zey", s)),
        }
        toplam_madde += len(maddeler)
        if bolum or maddeler or any(derece.values()):
            print(f"\n-- {ad}: bolum={[b[:45] for b in bolum]} derece={derece}")
            for s in maddeler[:12]:
                print(f"     madde? {s}")
    print(f"\nEK-1 toplam 'madde gorunumlu' satir: {toplam_madde}")


def analiz_ek2():
    print("\n========== EK-2 ==========")
    for ad, metin in sayfalar("ek2"):
        satirlar = [s.strip() for s in metin.splitlines() if s.strip()]
        if not satirlar:
            print(f"-- {ad}: BOS SAYFA")
            continue
        organ = [s for s in satirlar if ORGAN.fullmatch(s) and any(c.isalpha() for c in s) and len(s) < 60]
        alt = [s for s in satirlar if ALT.match(s) and len(s) < 60]
        maddeler = []
        for s in satirlar:
            m = re.match(r"^(\d{1,2})[.)]\s*(\S.{2,})$", s)
            if m:
                maddeler.append(s[:70])
        sayisal = sum(1 for s in satirlar if re.fullmatch(r"[\d.,%]+", s))
        oran = sayisal / max(1, len(satirlar))
        etiket = "TABLO" if oran > 0.5 else "metin"
        if organ or alt or maddeler:
            print(f"\n-- {ad} [{etiket} d={oran:.2f}] organ={[o[:40] for o in organ[:3]]} alt={alt[:3]} madde={len(maddeler)}")
            for s in maddeler[:6]:
                print(f"     madde? {s}")


if __name__ == "__main__":
    analiz_ek1()
    analiz_ek2()