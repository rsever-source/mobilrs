# -*- coding: utf-8 -*-
"""EK-2 OCR metninden aday kayit cikarir (organ sistemi / alt bolum / madde / tanim).

Kural: hicbir metin uydurulmaz; tanim = sayfadaki satirlarin birlestirilmis hali.
Cikti: arac/ek2_adaylar.json + arac/ek2_adaylar.md (insan denetimi icin)
"""
import json
import re
from pathlib import Path

TXT = Path(r"%TEMP%\o05\txt")
ARAC = Path(__file__).resolve().parent

TABLO_ISARET = ("TABLO", "Tablo ", "ŞEKİL", "Şekil ", "PUAN", "GRAFİK")
FORM_ISARET = ("SAĞLIK KURULU RAPORU", "EK-4", "EK-1 (Arkayüz)", "EK-I (Arkayüz)", "Mühür")
DERECE = re.compile(r"^(?:I|İ|1|l)\s*[-–]\s*(Ağır|Orta|Hafif|Çok|Tam)\b", re.I)
ALT = re.compile(r"^([A-ZÇĞİÖŞÜ]|I{1,3}V?|IV|V|VI{1,3}|IX|X{1,3})\s*[-–]\s*(.+)$")
ORGAN = re.compile(r"^[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9 ,.\-()/%]{5,80}$")
MADDE = re.compile(r"^(\d{1,2})\s*[.)]\s*(.{3,})$")
MADDE_HARF = re.compile(r"^([a-zçğıöşü])\s*[.)]\s*(.{3,})$")


def sayfa_metni(yol):
    return [s.strip() for s in yol.read_text(encoding="utf-8", errors="replace").splitlines()]


def organ_mu(satir):
    if len(satir) < 6 or not organ_harf(satir):
        return False
    if not any(c.isupper() for c in satir):
        return False
    if re.search(r"[a-zçğıöşü]{3,}", satir):
        return False
    if satir.startswith(("TABLO", "Tablo")):
        return False
    return True


def organ_harf(satir):
    harfler = [c for c in satir if c.isalpha()]
    return bool(harfler) and sum(1 for c in harfler if c.isupper()) / len(harfler) > 0.85


def main():
    adaylar = []
    sayfa_durum = {}
    organ = None
    alt = None
    sayfa_no = 0
    for yol in sorted(TXT.glob("ek2_*.txt")):
        sayfa_no += 1
        satirlar = sayfa_metni(yol)
        metin = "\n".join(satirlar)
        if not satirlar:
            sayfa_durum[yol.stem] = "bos"
            continue
        if any(i in metin for i in FORM_ISARET) and len(metin) < 3000:
            sayfa_durum[yol.stem] = "form/kapak"
            continue
        kalan = [s for s in satirlar if s]
        sayisal = sum(1 for s in kalan if re.fullmatch(r"[\d.,%\-–]+", s))
        if sayisal / max(1, len(kalan)) > 0.45:
            sayfa_durum[yol.stem] = "tablo"
            continue
        if sum(1 for s in kalan if s.startswith(TABLO_ISARET)) >= 3:
            sayfa_durum[yol.stem] = "tablo"
            continue

        i = 0
        uretilen = 0
        while i < len(satirlar):
            s = satirlar[i]
            if not s:
                i += 1
                continue
            if organ_mu(s):
                organ = s
                alt = None
                i += 1
                continue
            m_alt = ALT.match(s)
            if m_alt and len(s) < 80 and not DERECE.match(s):
                alt = s
                i += 1
                continue
            m = MADDE.match(s) or MADDE_HARF.match(s)
            if m:
                etiket = s.split(")")[0].split(".")[0].strip() if ")" in s else s.split(".")[0].strip()
                govde = [m.group(2).strip()]
                j = i + 1
                while j < len(satirlar):
                    n = satirlar[j]
                    if not n:
                        j += 1
                        continue
                    if organ_mu(n) or (MADDE.match(n) and len(n) > 5) or (ALT.match(n) and len(n) < 80 and not DERECE.match(n)):
                        break
                    if sum(1 for c in n if c.isdigit()) / max(1, len(n)) > 0.5:
                        break
                    govde.append(n)
                    j += 1
                tanim = " ".join(govde).strip()
                if len(tanim) >= 15 and organ:
                    adaylar.append(
                        {
                            "sayfa": yol.stem,
                            "sayfa_no": sayfa_no,
                            "organ": organ,
                            "alt": alt,
                            "etiket": etiket,
                            "tanim": tanim,
                        }
                    )
                    uretilen += 1
                i = j
                continue
            i += 1
        sayfa_durum[yol.stem] = f"metin ({uretilen} aday)"

    (ARAC / "ek2_adaylar.json").write_text(
        json.dumps(adaylar, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    satirlar = ["# EK-2 aday kayitlar (insan denetimi)", ""]
    organ_say = {}
    for a in adaylar:
        organ_say[a["organ"]] = organ_say.get(a["organ"], 0) + 1
        satirlar.append(f"- **{a['sayfa']}** | organ: {a['organ']} | alt: {a['alt']} | etiket: `{a['etiket']}`")
        satirlar.append(f"  - tanim: {a['tanim'][:220]}")
    (ARAC / "ek2_adaylar.md").write_text("\n".join(satirlar), encoding="utf-8")

    print(f"aday sayisi: {len(adaylar)}")
    print("\norgan bazinda:")
    for k, v in sorted(organ_say.items(), key=lambda x: -x[1]):
        print(f"  {v:4d}  {k}")
    print("\nsayfa durumlari:")
    for k, v in sayfa_durum.items():
        if not v.startswith("metin"):
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()