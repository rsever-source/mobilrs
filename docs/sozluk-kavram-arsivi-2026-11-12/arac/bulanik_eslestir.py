# -*- coding: utf-8 -*-
"""138 bulanık kanıt izinin sayfa/kanıt metniyle yeniden eşleştirilmesi.

Kural:
- Kanıt metni, adı (normalize edilmiş) içeriyorsa: kanıt satırı geçerli -> "dogrulandi".
- Kanıt metni adı içermiyor ama sayfadaki başka bir satır içeriyorsa: kanıt satırı
  o satırla değiştirilir -> "duzeltildi" (tahmin yok, OCR satırı birebir).
- Sayfada adı içeren satır yoksa: "belirsiz" (kanıt ve sayfa değiştirilmez).

Çıktı: raporlar/ek2_bulanik_inceleme.json
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ARSIV = Path(__file__).resolve().parents[1]
TXT = ARSIV / "kaynak" / "txt"
OUT = ARSIV / "raporlar" / "ek2_bulanik_inceleme.json"


def norm(value):
    value = str(value or "").casefold().replace("ı", "i")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def sayfa_satirlari(n):
    yol = TXT / f"ek2_{n:03d}.txt"
    if not yol.exists():
        return []
    return [s.strip() for s in yol.read_text(encoding="utf-8", errors="replace").splitlines() if s.strip()]


def main():
    izler = json.loads((ARSIV / "data" / "sozluk_kavram_kaynak_izleri.json").read_text(encoding="utf-8"))
    veri = json.loads((ARSIV / "data" / "sozluk_kavram_data.json").read_text(encoding="utf-8"))
    konum = {k["kavram_id"]: k for k in veri}
    sonuc = []
    sayac = Counter()
    for iz in izler:
        if iz["durum"] != "bulanik":
            continue
        k = konum[iz["kavram_id"]]
        n = k["kaynak"]["sayfa_no"]
        ad = norm(k["kanonik_ad"])
        kanit = iz.get("kanit", "")
        satirlar = sayfa_satirlari(n)
        # adı içeren satırlar (birebir, normalize)
        ad_satirlari = [s for s in satirlar if ad and ad in norm(s)]
        if ad and ad in norm(kanit):
            durum = "dogrulandi"
            yeni = kanit
        elif ad_satirlari:
            durum = "duzeltildi"
            yeni = ad_satirlari[0]
        else:
            durum = "belirsiz"
            yeni = kanit
        sayac[durum] += 1
        sonuc.append({
            "kavram_id": iz["kavram_id"],
            "sayfa": n,
            "bolum_adi": k["ek_2_baglantisi"]["bolum_adi"],
            "kanonik_ad": k["kanonik_ad"],
            "eski_kanit": kanit,
            "yeni_kanit": yeni,
            "eski_skor": iz.get("skor"),
            "durum": durum,
            "ad_gecen_satir_sayisi": len(ad_satirlari),
        })
    rapor = {
        "aciklama": (
            "138 'bulanik' kanıt izinin OCR sayfasıyla yeniden eşleştirilmesi. "
            "Doğrulama yalnız OCR satırına dayanır; ayrıca görsel liste: "
            "raporlar/ek2_bulanik_gorsel.md"
        ),
        "toplam": len(sonuc),
        "sayim": dict(sayac),
        "kayitlar": sonuc,
    }
    OUT.write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print("toplam:", len(sonuc), dict(sayac))
    for s in sonuc:
        if s["durum"] != "dogrulandi":
            print(f"  {s['durum']:10s} s{s['sayfa']:03d} skor={s['eski_skor']} {s['kanonik_ad'][:60]}")


if __name__ == "__main__":
    main()
