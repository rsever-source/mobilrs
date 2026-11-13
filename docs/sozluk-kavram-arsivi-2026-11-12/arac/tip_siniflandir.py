# -*- coding: utf-8 -*-
"""745 EK-1+EK-2 kayıtın 6 tip sınıflandırmasını uygular.

6 tip (bolum_adi + kanonik_ad kombinasyonuna göre):
  1. hastalık
  2. klinik bulgu/belirti
  3. fonksiyon kaybı
  4. anatomik terim
  5. cerrahi işlem/durum
  6. değerlendirme başlığı

Çıktı: `raporlar/ek2_tip_dendi.json`.
"""
import json
import re
from collections import Counter
from pathlib import Path

ARSIV = Path(__file__).resolve().parents[1]
VERI = ARSIV / "data" / "sozluk_kavram_data.json"
CIKTI = ARSIV / "raporlar" / "ek2_tip_dendi.json"


# --- Tip sınıflandırması: bolum_adi (bölüm başlığı) eşleşmesi ---
# Bölüm başlıkları Türkçe EK-2 taksitinde kullanılan standart başlıklardır.
# Bu, kanonik_adın anlamına gelmediği için "başlık hastalık gibi gösterilmeyecek" kuralı sağlanır.

BOLUM_TIPI_MAP = {
    # 1. hastalık - tanı oluşturan hastalık listeleri
    "HEMATOLOJİK HASTALIKLAR": "hastalık",
    "KARDİYOVASKÜLER SİSTEM": "hastalık",
    "GÖRME SİSTEMİ": "hastalık",
    "ENDOKRİN SİSTEM": "hastalık",
    "ÜRİNER SİSTEM VE ERKEK GENİTAL SİSTEM": "hastalık",
    "KULAK BURUN BOĞAZ": "hastalık",
    "DERİ": "hastalık",
    "SİNİR SİSTEMİ": "hastalık",  # some are symptoms, but mostly diagnoses here
    "ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR": "hastalık",

    # 2. cerrahi işlem/durum - ameliyat ve cerrahi tablolar
    "YANIKLAR": "cerrahi islem/durum",
    "ONKOLOJİ": "cerrahi islem/durum",
    "GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ": "cerrahi islem/durum",

    # 3. fonksiyon kaybı - fonksiyon bozuklukları, hareket kısıtlamaları
    "SİNDİRİM SİSTEMİ": "fonksiyon kaybi",
    "KAS-İSKELET SİSTEMİ": "fonksiyon kaybi",

    # 4. değerlendirme başlığı - değerlendirme/kriter tabloları
    # (böyle başlıklara sahip kayıtlar varsa değerlendirme başlığı)

    # 5. anatomik terim - anatomical structure names
    # (bolum başlığına göre ayırt edilecekseniz burada)

    # 6. klinik bulgu/belirti - belirtiler ve bulgular
    # (belirsiz kategori, kanonik_ad ile ayırt edilir)
}


# --- Ek: kanonik_ad'e dayalı fallback sınıflandırma ---
# bolum_adi eşleşme bulunamazsa kullanılır.

HASTALIK_KELIMELER = {
    "hastalık", "sendrom", "kanser", "tumör", "nöbettä", "infeksiyon",
    "hipertansiyon", "diabetes", "polip", "nöb", "hipoplazi", "hiperplazi",
    "benign", "malign", "ami", "polip",
}

KLINIK_BULGU_KELIMELER = {
    "bozukluk", "kusur", "anomal", "defis",
    "görünüm", "deformit", "kısıtlılık", "kaybı",
    "afazi", "dizartri", "spas", "tremor", "atez", "hemiballi",
    "paral", "distoni", "nisfi", "tam", "kısmi",
    "bitemporal", "homonim", "periferik",
}

FONKISYON_KAYBI_KELIMELER = {
    "fonksiyon", "kaybı", "engel", "yetersiz",
    "dayanıklılık", "mobilite", "durgunluk",
}

ANATOMIK_TERIM_KELIMELER = {
    "omurga", "serebral", "lüso", "nöron", "sinir", "glez",
    "maruz", "disk", "kemik", "plantar", "dorsal",
    "proksimal", "distal", "medyal", "lateral",
    "kavak", "kas", "spina", "foramen",
}


def kelime_seti(metin):
    """Metni küçültüp tek kelimelere ayırır."""
    metin = metin.lower()
    for sep in [" - ", " ve ", " ile ", "/"]:
        metin = metin.replace(sep, " ")
    return set(re.findall(r"[a-zçğıöşü]+", metin))


def tipi_tahmin(kayit):
    """Kayıt için 6 tipten birini tahmin eder."""
    e1 = "ek_1_baglantisi" in kayit
    e2 = "ek_2_baglantisi" in kayit
    ad = kayit.get("kanonik_ad", "")
    bolum = ""
    if e2:
        bolum = kayit.get("ek_2_baglantisi", {}).get("bolum_adi", "")
    elif e1:
        bolum = kayit.get("ek_1_baglantisi", {}).get("bolum_adi", "")

    # 1. Bolum başlığına bak (EK-2 çoğunluğu)
    if bolum and bolum in BOLUM_TIPI_MAP:
        return BOLUM_TIPI_MAP[bolum]

    # 2. Kanonik_ad kelime eşleşmesi (fallback)
    kelimeler = kelime_seti(ad)

    # Değerlendirme başlığı (en genel)
    if kelimeler & {"degerlendirme", "kriter", "skor", "sınıf", "evre", "tablo"}:
        return "degerlendirme baslik"

    # Cerrahi işlem/durum
    if kelimeler & {"amputasyon", "artroplastik", "transplant", "replastik",
                    "syme", "chopart", "fiş", "graft", "kanal",
                    "derin ven", "staz", "lenfödem"}:
        return "cerrahi islem/durum"

    # Anatomik terim
    if kelimeler & {"omurga", "serebral", "lüso", "nöron", "sinir",
                    "disk", "kemik", "plantar", "dorsal",
                    "proksimal", "distal", "kavak", "kas"}:
        return "anatomik terim"

    # Hastalık
    if kelimeler & HASTALIK_KELIMELER:
        return "hastalık"

    # Klinik bulgu/belirti
    if kelimeler & KLINIK_BULGU_KELIMELER:
        return "klinik bulgu/belirti"

    # Fonksiyon kaybı (varsayılan)
    return "fonksiyon kaybi"


def main():
    veri = json.loads(VERI.read_text(encoding="utf-8"))
    sonuc = []
    tipi_sayilari = Counter()
    for k in veri:
        tip = tipi_tahmin(k)
        tipi_sayilari[tip] += 1
        k["ek2_tip"] = tip
        sonuc.append({"kavram_id": k["kavram_id"], "kanonik_ad": k["kanonik_ad"], "tip": tip})
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
    print("tip dağılımı:", dict(tipi_sayilari))
    print("toplam:", len(sonuc))


if __name__ == "__main__":
    main()