# -*- coding: utf-8 -*-
"""Asama 2 oncesi yedek: calisma klasoru + kaynak OCR dosyalari.

Hicbir dosya silinmez/degistirilmez; yalnizca kopyalanir. Yedek klasoru
`_yedek` altindadir ve raporlardaki hash listelerinden haric tutulur.
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

KOK = Path(r"%TEMP%\sozluk_kavram")
YEDEK = KOK / "_yedek" / "2026-11-11-asama1-oncesi"
KAYNAKLAR = [
    Path(r"%TEMP%\o05\txt"),
    Path(r"%TEMP%\mvz"),
    Path(r"%TEMP%\ebjs"),
    Path(r"%TEMP%\opencode"),
]


def sha(yol):
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def kopyala(kaynak: Path, hedef: Path):
    if not kaynak.exists():
        return 0
    sayi = 0
    if kaynak.is_file():
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kaynak, hedef)
        return 1
    for dosya in kaynak.rglob("*"):
        if not dosya.is_file():
            continue
        if "_yedek" in dosya.parts or "__pycache__" in dosya.parts:
            continue
        goreli = dosya.relative_to(kaynak)
        hedef_dosya = hedef / goreli
        hedef_dosya.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dosya, hedef_dosya)
        sayi += 1
    return sayi


def main():
    manifest = {"olusturulma": datetime.now().isoformat(timespec="seconds"), "kopyalar": []}

    hedef_calisma = YEDEK / "sozluk_kavram"
    for dosya in KOK.rglob("*"):
        if not dosya.is_file():
            continue
        if "_yedek" in dosya.parts or "__pycache__" in dosya.parts:
            continue
        goreli = dosya.relative_to(KOK)
        hedef = hedef_calisma / goreli
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dosya, hedef)
        manifest["kopyalar"].append(
            {"kaynak": str(dosya), "yedek": str(hedef), "sha256": sha(dosya), "boyut": dosya.stat().st_size}
        )

    for kaynak in KAYNAKLAR:
        hedef = YEDEK / "kaynaklar" / kaynak.name
        sayi = kopyala(kaynak, hedef)
        manifest["kopyalar"].append({"kaynak": str(kaynak), "yedek": str(hedef), "dosya_sayisi": sayi})

    manifest_yolu = YEDEK / "yedek_manifest.json"
    manifest_yolu.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    toplam = sum(1 for k in manifest["kopyalar"] if "sha256" in k)
    print(f"yedek: {YEDEK}")
    print(f"calisma klasoru dosyasi: {toplam}")
    for k in manifest["kopyalar"]:
        if "dosya_sayisi" in k:
            print(f"kaynak klasoru: {k['kaynak']} -> {k['dosya_sayisi']} dosya")
    print(f"manifest: {manifest_yolu}")


if __name__ == "__main__":
    main()