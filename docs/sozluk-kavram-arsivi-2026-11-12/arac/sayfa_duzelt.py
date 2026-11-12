# -*- coding: utf-8 -*-
"""24 sayfa numarasi kaymasini kaynak dosyada duzeltir (arac/sayfa_fark.txt)."""
import re
from pathlib import Path

P = Path(__file__).resolve().parent / "ek2_ek_kayitlar.py"

# ad -> (eski sayfa, yeni sayfa)
DUZELTME = {
    "Curling ülseri": (85, 84),
    "Yanığa bağlı özefagus darlığı": (85, 84),
    "Torakal omurga hareket kısıtlılığı": (100, 99),
    "Omurga ankilozu": (99, 97),
    "Spinal sinir lezyonu": (138, 139),
    "Brakial pleksus lezyonu": (138, 139),
    "Alt ekstremite sorunları": (138, 141),
    "Alt ekstremite uzunluk farklılıkları": (139, 143),
    "Yürüyüş bozukluğu": (139, 144),
    "Bacak kaslarındaki atrofi": (141, 145),
    "Alt ekstremite kas kuvveti kaybı": (142, 146),
    "Kalça eklemi hareket kısıtlılığı": (144, 147),
    "Diz eklemi hareket kısıtlılığı": (144, 148),
    "Ayak bileği eklemi hareket kısıtlılığı": (145, 148),
    "Topuk hareket kısıtlılığı": (145, 148),
    "Ayak bileği veya topuk deformitesi": (145, 148),
    "Ayak başparmak bozuklukları": (146, 149),
    "Kalça ankilozu": (147, 149),
    "Diz ankilozu": (149, 150),
    "Ayak bileği ankilozu": (150, 152),
    "Ayak ankilozu": (152, 153),
    "Ayak parmaklarının ankilozu": (153, 154),
    "Alt ekstremite ampütasyonları": (154, 155),
}

metin = P.read_text(encoding="utf-8")
satirlar = metin.split("\n")
degisen = 0
for i, satir in enumerate(satirlar):
    m = re.match(r'^    \((\d+), ([A-Z]+), "([^"]*)", "([^"]*)", "([^"]*)",$', satir)
    if not m:
        continue
    sayfa, ad = int(m.group(1)), m.group(5)
    if ad not in DUZELTME:
        continue
    eski, yeni = DUZELTME[ad]
    if sayfa != eski:
        raise SystemExit(f"BEKLENMEYEN SAYFA: {ad} = {sayfa}, beklenen {eski}")
    satirlar[i] = satir.replace(f"({eski},", f"({yeni},", 1)
    degisen += 1

# Omurgaya ait sorunlar: OCR'daki gercek yazim (dotless i)
eski_ham = '"Omurgaya ait sorunlar",\n     "I. OMURGAYA AİT SORUNLARDA ENGELLİLİK"),'
yeni_ham = '"Omurgaya ait sorunlar",\n     "ı. OMURGAYA AİT SORUNLARDA ENGELLİLİK"),'
yeni_metin = "\n".join(satirlar)
if yeni_metin.count(eski_ham) != 1:
    raise SystemExit("Omurgaya ait sorunlar kanit satiri bulunamadi")
yeni_metin = yeni_metin.replace(eski_ham, yeni_ham, 1)

P.write_text(yeni_metin, encoding="utf-8")
print(f"sayfa duzeltmesi: {degisen} / {len(DUZELTME)}")
