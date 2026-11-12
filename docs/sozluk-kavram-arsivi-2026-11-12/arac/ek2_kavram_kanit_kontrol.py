# -*- coding: utf-8 -*-
"""EK-2 yeni kayıtlar için bağımsız ad/kanıt çapraz kontrolü.

Bu betik ana JSON'u DEĞİŞTİRMEZ. Mevcut ek2_ek_dogrula.py ham_satir
metninin OCR sayfasında bulunmasını denetler; bu betik ayrıca kanonik_ad
ifadesinin aynı sayfanın OCR metninde bulunup bulunmadığını kontrol eder.
OCR yazım hataları ve satır bölünmeleri otomatik onaylanmaz; yalnızca
manuel inceleme listesine alınır.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "arac" / "ek2_ek_kayitlar.json"
TXT = ROOT / "kaynak" / "txt"
OUT = ROOT / "raporlar" / "ek2_kavram_kanit_kontrol.json"
YAKIN_ESIK = 0.78


def norm(value: str) -> str:
    value = str(value or "").casefold().replace("ı", "i")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def page_number(value: str) -> int:
    match = re.search(r"(\d{3})$", str(value))
    if not match:
        raise ValueError(f"Geçersiz sayfa etiketi: {value!r}")
    return int(match.group(1))


def best_window_score(name: str, lines: list[str]) -> float:
    """Adı 1-4 ardışık OCR satırında arar; eşleşme kanıtı değil, inceleme ipucudur."""
    target = norm(name)
    if not target:
        return 0.0
    best = 0.0
    normalized = [norm(line) for line in lines]
    for i in range(len(normalized)):
        for width in range(1, 5):
            candidate = " ".join(normalized[i : i + width]).strip()
            if not candidate:
                continue
            if target in candidate:
                return 1.0
            score = difflib.SequenceMatcher(None, target, candidate).ratio()
            if score > best:
                best = score
    return round(best, 3)


def main() -> int:
    rows = json.loads(RAW.read_text(encoding="utf-8"))
    results = []
    counts = Counter()
    for row in rows:
        page = page_number(row.get("sayfa", ""))
        path = TXT / f"ek2_{page:03d}.txt"
        if not path.exists():
            results.append({
                "sayfa": page,
                "kanonik_ad": row.get("kanonik_ad", ""),
                "durum": "ocr_sayfasi_yok",
                "ham_satir_bulundu": False,
                "ad_ham_satirda": False,
                "ad_sayfada_birebir": False,
                "en_yakin_pencere_skoru": 0.0,
            })
            counts["ocr_sayfasi_yok"] += 1
            continue

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        page_text = norm(" ".join(lines))
        name = norm(row.get("kanonik_ad", ""))
        ham = norm(row.get("ham_satir", ""))
        ham_found = bool(ham) and (ham in page_text or ham[:40] in page_text)
        name_in_ham = bool(name) and name in ham
        name_on_page = bool(name) and name in page_text
        score = best_window_score(row.get("kanonik_ad", ""), lines)

        if name_on_page:
            status = "ad_sayfada_birebir"
        elif score >= YAKIN_ESIK:
            status = "ad_sayfada_yaklasik_inceleme"
        else:
            status = "ad_sayfada_dogrulanamadi"

        counts[status] += 1
        counts["ham_satir_bulundu" if ham_found else "ham_satir_bulunamadi"] += 1
        counts["ad_ham_satirda" if name_in_ham else "ad_ham_satirda_degil"] += 1

        results.append({
            "sayfa": page,
            "bolum_adi": row.get("bolum_adi", ""),
            "kanonik_ad": row.get("kanonik_ad", ""),
            "ham_satir": row.get("ham_satir", ""),
            "ham_satir_bulundu": ham_found,
            "ad_ham_satirda": name_in_ham,
            "ad_sayfada_birebir": name_on_page,
            "en_yakin_pencere_skoru": score,
            "durum": status,
        })

    output = {
        "aciklama": (
            "Bağımsız OCR metin çapraz kontrolüdür; PDF görüntüsü üzerinde "
            "insan teyidinin yerine geçmez. Bulanık/yok sonuçlar otomatik "
            "olarak yanlış kayıt sayılmaz, manuel inceleme adayıdır."
        ),
        "toplam_yeni_kayit": len(rows),
        "esik_yakin_eslesme": YAKIN_ESIK,
        "sayimlar": dict(counts),
        "kayitlar": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Yeni kayıt: {len(rows)}")
    for key, value in sorted(counts.items()):
        print(f"{key}: {value}")
    print(f"Rapor: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
