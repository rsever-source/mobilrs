# -*- coding: utf-8 -*-
"""EK-2 s.25-169: hastalik/durum TERIMLERI (harf ve Roma etiketli basliklar).

Yalnizca harf etiketli (A., a.) ve Roma rakamli (I., IV.) terim satirlari alinir;
bunlar kaynakta hastalik/bozukluk grubu adidir. Numarali satirlar (1-, 2-) agirlikla
siddet/kriter varyantidir ve kavram sozlugune alinmaz (kural: saf siddet etiketi
kavram sayilmaz). Tanim yalnizca satirin devamindaki duz metinden alinir; "Klas/EVRE"
gibi puanlama basligi gorulunce kesilir.
"""
import json
import re
from pathlib import Path

TXT = Path(__file__).resolve().parents[1] / "kaynak" / "txt"
ARAC = Path(__file__).resolve().parent

BOLUM_ARALIKLARI = [
    (25, 28, "HEMATOLOJİK HASTALIKLAR"),
    (29, 34, "KARDİYOVASKÜLER SİSTEM"),
    (65, 71, "SİNDİRİM SİSTEMİ"),
    (72, 73, "KADIN HASTALIKLARI VE DOĞUM"),
    (74, 78, "ÜROGENİTAL SİSTEM"),
    (79, 82, "ENDOKRİN SİSTEM"),
    (83, 83, "GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ"),
    (84, 85, "YANIKLAR"),
    (86, 86, "ONKOLOJİ"),
    (87, 92, "SİNİR SİSTEMİ"),
]

ORAN_SATIRI = re.compile(r"^[\d\s.,%\-–/]+$")
BASLIK_ATLA = ("TABLO", "Tablo", "EK-", "Klas", "KLAS", "EVRE", "Evre", "Not:", "NOT:", "Şekil", "ŞEKİL", "Çizelge")
SINIF_ETIKETI = re.compile(r"^(Klas|KLAS|Sınıf|SINIF|Evre|EVRE|Grup|GRUP|A-?Grubu|B-?Grubu|C-?Grubu)\b", re.I)
SADECE_DUZEY = re.compile(
    r"^(hafif|orta|ağır|agir|çok ağır|cok agir|tam|yok|evre|klas|sınıf|semptom)\b[\s:.\-–]*$", re.I
)
# Kriter/siddet cumlesi gibi baslayan satirlar terim degildir
KRITER_BASI = re.compile(
    r"^(hafif|orta|ağır|agir|çok|kişi|kisi|hastalığı|hastaligi|tıbbi|tibbi|cerrahi|sempatektomi|"
    r"faktör|faktor|transfüzyon|transfuzyon|steroid|kronik faz|tam remisyonda|tedavi|nadir|birden|"
    r"bir kez|mükerrer|hemostatik|düşük dereceli|yılda|ilaç|kalıcı|kateter|i14ç|aritmi|proteinüri|"
    r"hemostaz|primer hemostaz|venöz sistem|fonksiyonel damar|travmatik damar|tıkayıcı damar|"
    r"sık|hayatı|gerçek|total|parsiyel|bilateral|unilateral|komplikasyon|organ|diğer|diğerleri)\b",
    re.I,
)
ROMA = re.compile(r"^(?P<etiket>(?:[IVX]+|[ıİi]{1,3})\s*[.\-–)]?)\s+(?P<kalan>.+)$")
LATIN = re.compile(r"^(?P<etiket>(?:[A-ZÇĞİÖŞÜa-zçğıöşü])[.)])\s*(?P<kalan>.+)$")
SAYI = re.compile(r"^(?P<etiket>\d{1,2}\s*[-.)])\s*(?P<kalan>.+)$")


def bolum_bul(sayfa):
    for a, b, ad in BOLUM_ARALIKLARI:
        if a <= sayfa <= b:
            return ad
    return None


def satirlar(n):
    return [s.strip() for s in (TXT / f"ek2_{n:03d}.txt").read_text(encoding="utf-8", errors="replace").splitlines()]


def buyuk_harf_orani(s):
    h = [c for c in s if c.isalpha()]
    return (sum(1 for c in h if c.isupper()) / len(h)) if h else 0.0


def baslik_mu(s):
    if not (5 <= len(s) <= 95) or s.startswith(BASLIK_ATLA):
        return False
    if not s[0].isalpha() or re.search(r"\d", s):
        return False
    return buyuk_harf_orani(s) >= 0.9 and len(s.split()) >= 2


def terim_mu(s):
    if not (4 <= len(s) <= 120):
        return False
    h = [c for c in s if c.isalpha()]
    if len(h) < 4:
        return False
    if sum(1 for c in s if c.isdigit()) > len(s) * 0.25:
        return False
    if re.search(r"[bcçdfgğhjklmnprsştvyz]{5,}", s.lower()):
        return False
    if KRITER_BASI.match(s):
        return False
    return True


def tanim_temizle(s):
    s = re.sub(r"\s{2,}", " ", s).strip()
    parca = re.split(r"\b(Klas|KLAS|EVRE|Evre|Sınıf|SINIF)\b", s)[0].strip()
    return parca


def main():
    kayitlar = []
    bolum = grup = None
    son_sayfa = None
    gorulen = set()

    for n in range(25, 170):
        b = bolum_bul(n)
        if b is None:
            continue
        if b != bolum:
            bolum, grup = b, None
        ss = satirlar(n)
        i = 0
        while i < len(ss):
            s = ss[i]
            if not s:
                i += 1
                continue
            if baslik_mu(s):
                birlesik = s
                j = i + 1
                while j < len(ss) and baslik_mu(ss[j]) and not birlesik.endswith((".", ":")):
                    birlesik = (birlesik + " " + ss[j]).strip()
                    j += 1
                grup = birlesik
                i = j
                continue

            m = ROMA.match(s)
            tur = "roma"
            if not m or len(m.group("kalan")) < 4:
                m = LATIN.match(s)
                tur = "latin"
            if not m or len(m.group("kalan")) < 4:
                m = SAYI.match(s)
                tur = "sayi"
            if not m:
                i += 1
                continue
            etiket = m.group("etiket").strip()
            kalan = m.group("kalan").strip()
            if SINIF_ETIKETI.match(kalan) or SADECE_DUZEY.match(kalan.rstrip(":")):
                i += 1
                continue
            aday = re.sub(r"\s+\d{1,3}(?:\s+\d{1,3})*\s*$", "", kalan).strip(" .;-–\t")
            if not terim_mu(aday):
                i += 1
                continue

            if tur == "roma":
                grup = aday.rstrip(":")

            govde = []
            j = i + 1
            while j < len(ss):
                n2 = ss[j]
                if not n2:
                    j += 1
                    continue
                if baslik_mu(n2) or ORAN_SATIRI.fullmatch(n2):
                    break
                if ROMA.match(n2) or LATIN.match(n2):
                    break
                if re.match(r"^(Klas|KLAS|EVRE|Evre|Sınıf|TABLO|Tablo|Şekil|EK-)", n2):
                    break
                govde.append(n2)
                j += 1
            tanim = tanim_temizlele = tanim_temizle(" ".join(govde)) if govde else ""

            anahtar = (bolum, aday)
            if anahtar in gorulen:
                i = j
                continue
            gorulen.add(anahtar)
            kayitlar.append(
                {
                    "sayfa": f"ek2_{n:03d}",
                    "pdf_sayfasi": n,
                    "bolum_adi": bolum,
                    "alt_bolum": grup if grup and grup != aday else None,
                    "madde_etiketi": etiket,
                    "kanonik_ad": aday.rstrip(":"),
                    "tanim": tanim,
                    "ham_satir": s,
                }
            )
            i = j

    (ARAC / "ek2_25_169_kayitlar.json").write_text(json.dumps(kayitlar, ensure_ascii=False, indent=1), encoding="utf-8")

    inceleme = ["# EK-2 s.25-169 terim cikarimi (inceleme)", "", f"Kayit: {len(kayitlar)}", ""]
    for k in kayitlar:
        inceleme.append(f"- `{k['sayfa']}` | {k['bolum_adi']} | alt={k['alt_bolum'] or '-'} | `{k['madde_etiketi']}` | **{k['kanonik_ad']}**")
        if k["tanim"]:
            inceleme.append(f"  - tanım: {k['tanim'][:200]}")
    (ARAC / "ek2_25_169_inceleme.md").write_text("\n".join(inceleme), encoding="utf-8")

    print(f"kayit: {len(kayitlar)}")
    dagilim = {}
    for k in kayitlar:
        dagilim[k["bolum_adi"]] = dagilim.get(k["bolum_adi"], 0) + 1
    for b, c in sorted(dagilim.items(), key=lambda x: -x[1]):
        print(f"  {c:4d}  {b}")


if __name__ == "__main__":
    main()
