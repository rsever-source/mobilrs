# -*- coding: utf-8 -*-
"""23 belirsiz bulanık izin PDF görüntüsünden doğrulanması ve kanıt düzeltmeleri.

Kaynak: `raporlar/ek2_bulanik_inceleme.json` (115 dogrulandi + 23 belirsiz).
23 kayıt için PDF sayfa görüntüsü (150 DPI) tek tek okundu. Kanıt metni
görüntüdeki basılı satırla değiştirilir; sayfa numarası değiştirilmez.

Çıktılar:
- `raporlar/ek2_bulanik_inceleme.json` güncellenir (durum + yeni kanıt).
- `raporlar/ek2_bulanik_gorsel.md` (23 kaydın görsel sonucu).
- `arac/ek2_u3b_duzeltme.json` (kanit_izi.py için 138 kayıtlık geçersiz kılma).
Veri dosyasına dokunmaz.
"""
import json
from collections import Counter
from pathlib import Path

ARSIV = Path(__file__).resolve().parents[1]
RAPOR = ARSIV / "raporlar" / "ek2_bulanik_inceleme.json"
CIKTI_MD = ARSIV / "raporlar" / "ek2_bulanik_gorsel.md"
OVERRIDE = ARSIV / "arac" / "ek2_u3b_duzeltme.json"

# PDF görüntüsünden okunan basılı satırlar. Anahtar: kavram_id
GORSEL = {
    "ek2_s008_elektif_mutizm": (
        "12. Elektif mutizm",
        "duzeltildi",
        "Liste maddesi 12; OCR'da 'Elektifmutizm' bitişik okunmuş.",
    ),
    "ek2_s012_frontal_kemikte_egilme": (
        "Frontal kemikte çökme",
        "yazim_farki",
        "Kaynakta 'çökme' basılı; OCR 'eğkme' okuyup ad 'eğilme' olmuş. Ad düzeltildi.",
    ),
    "ek2_s012_dis_kulagin_cift_tarafli_kaybi_veya_se": (
        "Dış kulağın çift taraflı kaybı veya şekil bozukluğu",
        "duzeltildi",
        "Sınıf 2 satırı; OCR son harfi 'p' okumuş.",
    ),
    "ek2_s012_dogumsal_anomali_travma_kanser_ve_veya": (
        "Doğumsal anomali, travma, kanser ve/veya kanser ameliyatına bağlı olarak normal yüz anatomisinin aşırı bozukluğu",
        "duzeltildi",
        "Sınıf 4 satırı; OCR nokta/virgül ve 'olarak' kelimesini düşürmüş.",
    ),
    "ek2_s012_doku_kaybi_skarli_fiksasyon_veya_felce": (
        "Doku kaybı, skarlı fiksasyon veya felce bağlı dilin fonksiyon kaybı (hafif)",
        "duzeltildi",
        "OCR satırı okunamaz halde; basılı satır görüntüden alındı.",
    ),
    "ek2_s013_burun_ve_sinus_bosluguna_acilma_ile_bi": (
        "Burun ve sinüs boşluğuna açılma ile birlikte maksilla'nın tam kaybı (fonksiyon kaybı ile birlikte alveoler çıkıntıda %50'den fazla kayıp)",
        "duzeltildi",
        "Sayfa başındaki 45 puanlık satır; OCR 'maksilla'nm' okumuş.",
    ),
    "ek2_s013_doku_kaybi_skarli_fiksasyon_veya_felce": (
        "Doku kaybı, skarlı fiksasyon veya felce bağlı dilin fonksiyon kaybı (Tam dil yokluğu veya konuşma ve yutmayı zorlaştıracak derecede dilin en az 2/3'sinin alındığı dil harabiyeti veya bilateral hipoglossal sinir paralizisi)",
        "duzeltildi",
        "55 puanlık satır; OCR birkaç kelimeyi bozmuş.",
    ),
    "ek2_s016_beyin_hasari_beyin_islev_bozukluguna_b": (
        "II- Beyin Hasarı, Beyin İşlev Bozukluğuna Bağlı Davranış Bozuklukları",
        "duzeltildi",
        "II numaralı bölüm başlığı; OCR 'Bozulduğuna/Davramş' okumuş.",
    ),
    "ek2_s016_organik_kisilik_bozuklugu_frontal_lob": (
        "(Organik kişilik bozukluğu, frontal lob sendromunu, beyin sarsılması sonrası postkontüzyonel sendrom içerir.)",
        "dogrulandi",
        "Parantez içi açıklama; OCR metni basılı satırla aynı.",
    ),
    "ek2_s017_anksiyete_bozukluklari_obsesif_kompuls": (
        "IV-Anksiyete bozuklukları( panik bozukluk, yaygın anksiyete bozukluğu, agorafobi), obsesif-kompülsif bozukluklar, somatoform bozukluklar ve yeme bozuklukları:",
        "duzeltildi",
        "IV numaralı başlık; OCR yalnız kuyruğunu yakalamış.",
    ),
    "ek2_s017_anksiyete_bozukluklari_panik_bozukluk": (
        "a) Anksiyete bozuklukları( panik bozukluk, yaygın anksiyete bozukluğu, agorafobi) ve somatoform bozukluklar",
        "duzeltildi",
        "a) alt başlığı; OCR 'bozukluları/bozulduk' okumuş.",
    ),
    "ek2_s017_kisilik_bozukluklari": (
        "VI-Kişilik bozuklukları",
        "duzeltildi",
        "VI numaralı başlık; OCR 'bozuldukları' okumuş.",
    ),
    "ek2_s018_hidradenitis_supurativa_akne_konglobat": (
        "B- Hidradenitis supurativa, akne konglobata ve folliküler oklüzyon Triadı",
        "duzeltildi",
        "B- satırı; OCR son kelimeyi 'Triadl' okumuş.",
    ),
    "ek2_s019_alopesi_universalis": (
        "2-Alopesi universalis",
        "duzeltildi",
        "II. bölüm 2. satır; OCR 'AIopesi' okumuş.",
    ),
    "ek2_s019_dermatitler_kontakt_dermatit_staz_derm": (
        "B- Dermatitler (Kontakt dermatit, staz dermatit, dishidrotik ekzema) klinik şiddetine göre değerlendirilecek.",
        "duzeltildi",
        "B- satırı; OCR cümleyi yarıda kesmiş.",
    ),
    "ek2_s020_psikiyatrik_etyolojili_deri_hastalikla_2": (
        "Psikiyatrik etyolojili deri hastalıkları (nörotik ekskoriasyon, faktisiyel dermatit, vb.)",
        "duzeltildi",
        "V. bölüm alt satırı; OCR 'Psikiatrik' okumuş.",
    ),
    "ek2_s020_solar_urtiker_aktinik_retikuloid_persi": (
        "1-Solar ürtiker, aktinik retikuloid, persistan ışık reaksiyonu, polimorf ışık erüpsiyonu klinik şiddete göre değerlendirilir.",
        "duzeltildi",
        "VII. bölüm 1. satırı; OCR 'I-SoIar' ve 'Işık' okumuş.",
    ),
    "ek2_s021_porfirialar": (
        "2-Porfirialar",
        "duzeltildi",
        "Sayfa başındaki 2. satır; OCR 'PorfiriaIar' okumuş.",
    ),
    "ek2_s021_pigment_bozuklugu_ile_seyreden_hastali": (
        "Pigment bozukluğu ile (Vitiligo, depigmentasyon ve melanoderma yapan hastalıklar) seyreden hastalıklar",
        "duzeltildi",
        "IX. bölüm alt satırı; OCR cümleyi yarıda kesmiş.",
    ),
    "ek2_s021_otoimmun_bullu_hastaliklar_pemfigus_vu": (
        "Otoimmün büllü hastalıklar (Pemfigus vulgaris, büllöz pemfigoid, dermatitis herpetiformis ve diğer otoimmün büllü hastalıklar)",
        "duzeltildi",
        "X. bölüm satırı; OCR 'biillü' okumuş.",
    ),
    "ek2_s022_norokutanoz_hastaliklar_norofibromatoz": (
        "Nörokutanöz hastalıklar (Nörofibromatosis, Tuberoz skleroz, Psödoksantoma elastikum, Ataksi telenjiektazi, vb.)",
        "duzeltildi",
        "XI. bölüm satırı; OCR 'Ataksi' kelimesini düşürmüş.",
    ),
    "ek2_s023_kseroderma_pigmentozum_rothmund_thomps": (
        "Kseroderma pigmentozum, Rothmund-Thompson Send., Diskeratozis konjenita, Werner send. vb.",
        "dogrulandi",
        "Satır basılı haliyle aynı; kısaltmalar ad içinde açılmış.",
    ),
    "ek2_s024_kutanoz_langerhans_hucreli_histiyosito": (
        "Kutanöz (Langerhans hücreli) histiyositozlar",
        "duzeltildi",
        "XIII. bölüm satırı; OCR 'histiyosistozlar' okumuş.",
    ),
}


def main():
    rapor = json.loads(RAPOR.read_text(encoding="utf-8"))
    sayac = Counter()
    md = [
        "# EK-2 bulanık izlerin görsel doğrulaması (23 kayıt)",
        "",
        "138 `bulanik` kanıt izinden OCR'da adı geçmeyen 23 kayıt, 150 DPI PDF",
        "sayfa görüntüsünden tek tek okundu. Sayfa numaraları değiştirilmedi;",
        "kanıt metni yalnız görüntüdeki basılı satırdan düzeltildi.",
        "",
        "| Sayfa | Kanonik ad | Görsel sonuç |",
        "| --- | --- | --- |",
    ]
    for k in rapor["kayitlar"]:
        if k["durum"] != "belirsiz":
            continue
        yeni, durum, not_ = GORSEL[k["kavram_id"]]
        k["eski_durum"] = k["durum"]
        k["durum"] = durum
        k["yeni_kanit"] = yeni
        k["gorsel_not"] = not_
        sayac[durum] += 1
        md.append(f"| {k['sayfa']} | {k['kanonik_ad']} | `{durum}` — {not_} |")

    md += ["", "## Özet", ""]
    for d in ("dogrulandi", "duzeltildi", "yazim_farki"):
        md.append(f"- `{d}`: **{sayac[d]}**")
    md += [
        "",
        "`yazim_farki`: kaynakta \"Frontal kemikte çökme\" basılı; OCR \"eğkme\"",
        "okuduğu için kavram adı \"eğilme\" olmuş. Ad, kanıtla birlikte düzeltildi.",
    ]
    CIKTI_MD.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    # kanit_izi.py için: 115 dogrulandi + 23 görsel sonuç
    override = []
    for k in rapor["kayitlar"]:
        if k["durum"] == "dogrulandi":
            override.append({"kavram_id": k["kavram_id"], "kanit": k["yeni_kanit"], "durum": "birebir"})
        elif k["durum"] in ("duzeltildi", "yazim_farki"):
            override.append({"kavram_id": k["kavram_id"], "kanit": k["yeni_kanit"], "durum": "duzeltilmis"})
    OVERRIDE.write_text(json.dumps(override, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8", newline="\n")

    toplam = Counter(k["durum"] for k in rapor["kayitlar"])
    rapor["sayim"] = dict(toplam)
    rapor["aciklama"] = (
        "138 'bulanik' kanıt izinin OCR ve PDF görüntüsüyle yeniden eşleştirilmesi. "
        "115 kayıt ad-satır eşleşmesiyle (skor 1.0), 23 kayıt 150 DPI sayfa "
        "görüntüsünden doğrulandı. Ayrıntı: raporlar/ek2_bulanik_gorsel.md"
    )
    RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
    print("görsel:", dict(sayac), "toplam:", dict(toplam), "override:", len(override))


if __name__ == "__main__":
    main()
