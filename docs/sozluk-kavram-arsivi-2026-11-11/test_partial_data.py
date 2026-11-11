#!/usr/bin/env python3
"""Verify the archived partial glossary dataset. Run from this folder.

This checks structural/schema/data invariants only. It does NOT certify the
legal interpretation, OCR fidelity, completeness, synonym quality or ICD-10
concept matching.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft7Validator, FormatChecker

BASE = Path(__file__).resolve().parent
SCHEMA_PATH = BASE / "schema" / "sozluk_kavram.v1.0.3_taslak.json"
DATA_PATH = BASE / "data" / "sozluk_kavram_data_kismi_v1.0.3.json"
RULES_PATH = BASE / "data" / "ek1_derecesiz_kurallar.json"

schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))

fc = FormatChecker()

@fc.checks("date-time")
def strict_datetime(value):
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False

@fc.checks("uri")
def strict_uri(value):
    if not isinstance(value, str) or any(ch.isspace() for ch in value):
        return False
    try:
        u = urlsplit(value)
        return u.scheme in {"http", "https"} and bool(u.netloc) and bool(u.hostname)
    except ValueError:
        return False

def run_check(name, condition, details=""):
    if not condition:
        raise AssertionError(f"FAIL {name}: {details}")
    print(f"PASS {name}")

def main():
    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema, format_checker=fc)
    errors = []
    for i, item in enumerate(records):
        for err in validator.iter_errors(item):
            errors.append((i, item.get("kavram_id"), err.json_path, err.validator, err.message))

    ek1 = [r for r in records if "ek_1_baglantisi" in r]
    ek2 = [r for r in records if "ek_2_baglantisi" in r]
    ids = [r.get("kavram_id") for r in records]
    missing_labels = [r for r in ek2 if "madde_etiketi" not in r["ek_2_baglantisi"]]
    duplicate_ids = [k for k, n in Counter(ids).items() if n > 1]

    checks = [
        ("Draft-07 şema kendi kendini doğruluyor", True, ""),
        ("418 kayıt beklenen kısmi veri kümesinde", len(records) == 418, str(len(records))),
        ("EK-1 kayıt sayısı 276", len(ek1) == 276, str(len(ek1))),
        ("EK-2 kayıt sayısı 142", len(ek2) == 142, str(len(ek2))),
        ("418 kaydın tamamı Draft-07 + FormatChecker ile geçiyor", not errors, str(errors[:3])),
        ("kavram_id değerleri benzersiz", not duplicate_ids, str(duplicate_ids[:5])),
        ("67 etiketsiz EK-2 kaydı korunuyor", len(missing_labels) == 67, str(len(missing_labels))),
        ("4 EK-1 derecesiz kural ayrı dosyada", len(rules.get("kayitlar", [])) == 4, str(len(rules.get("kayitlar", [])))),
        ("Her kayıtta tek mevzuat bağlantısı var", all(("ek_1_baglantisi" in r) ^ ("ek_2_baglantisi" in r) for r in records), ""),
        ("EK-1 ve EK-2 RG künyeleri doğru", all(r["kaynak"]["rg_sayisi"] == 31612 for r in ek1) and all(r["kaynak"]["rg_sayisi"] == 30692 for r in ek2), ""),
        ("EK-1 kimlikleri ek1_ ile başlıyor", all(r["kavram_id"].startswith("ek1_") for r in ek1), ""),
        ("EK-2 kimlikleri ek2_ ile başlıyor", all(r["kavram_id"].startswith("ek2_") for r in ek2), ""),
    ]
    for name, ok, detail in checks:
        run_check(name, ok, detail)

    print(f"\nSONUÇ: {sum(1 for _, ok, _ in checks if ok)}/{len(checks)} PASS")
    print("Uyarı: PASS sonucu kayıtların hukuki/içerik doğruluğu veya kapsamın tamamlandığı anlamına gelmez.")
    print("Bu dosya yalnızca arşivdeki KISMİ veri setini kontrol eder.")

if __name__ == "__main__":
    main()
