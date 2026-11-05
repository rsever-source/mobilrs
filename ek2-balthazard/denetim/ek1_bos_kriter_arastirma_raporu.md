# EK-1 BOŞ KRİTER METİNLERİ — ARAŞTIRMA VE DENETİM RAPORU

Tarih: 2026-11-05
Çalışma kopyası: `worktrees/ek2-arac1-duzeltme` (dal `feature/ek2-arac1-duzeltme`, taban commit `98e513b`)
İncelenen veri: `origin/cloud-run-migration` → `ek2-balthazard/arac3/arac3.html` içindeki gömülü `ARAC3_MAPPING_DATA`
ve `ek2-balthazard/arac3/arac3_182_ek1_eslestirme.json`

> **Sonuç:** 11 kaydın tamamı incelendi. Resmî Ek-1'de bu maddelerin altında **yalnızca düzey başlığı** bulunduğu,
> kriter gövdesinin **hiç yazılmadığı** üç bağımsız kaynakla doğrulandı. Bu nedenle hiçbir metin eklenmedi:
> **tamamlanan 0, boş bırakılan 11**. Veri dosyalarında **değişiklik yapılmadı**.

---

## 1. AMAÇ VE KAPSAM

Ek-1 Hastalık Listesi kaynaklı 182 kayıtlık Araç 3 eşleştirmesinde, düzey başlığı bulunmasına rağmen
kriter metni boş kalan 11 kaydın, resmî ve güvenilir kaynaklardan tamamlanması.

Kurallar:

- Önce araştırma/envanter; veri yalnızca **doğrulanmış** metinle doldurulur.
- Kaynakta bulunamayan kriter için **tahmin yürütülmez**; kayıt "çözümlenemedi" olarak raporlanır.
- Yalnızca başlık bulunması kriter metni türetmek için gerekçe sayılmaz.
- Hafif/orta/ağır koşulları karıştırılmaz; kaynakta olmayan oran/eşik/tıbbi ifade eklenmez.
- Kayıt kimlikleri, sıralamalar ve mevcut doğru veriler değiştirilmez.

---

## 2. YÖNTEM (ÜÇ BAĞIMSIZ DOĞRULAMA)

| # | Kaynak | Yöntem | Sonuç |
| --- | --- | --- | --- |
| 1 | Resmî Ek-1, metin katmanlı PDF (40 sayfa) | Sayfa sayfa metin çıkarımı; s.18, s.28, s.39 ayrıntılı okundu | 11 maddenin altında yalnızca düzey başlığı var, gövde yok |
| 2 | Resmî Gazete taranmış PDF | İlgili sayfalar 150 dpi görüntüye çevrilip **görsel** olarak okundu | Aynı sonuç: başlık var, kriter gövdesi yok |
| 3 | Engelliler.biz karşılaştırma aracı verisi (`veri.v1.js`) | 11 kaydın veri nesneleri tek tek okundu | 11 maddenin tamamında `"d":{"agir":[]}` — kriter dizisi boş, ek not yok |

Ek olarak: gömülü `ARAC3_MAPPING_DATA` ile yan JSON (`arac3_182_ek1_eslestirme.json`) **birebir aynı**
(sıralı JSON karşılaştırması: eşit), canlı sitedeki veriyle de aynı.

---

## 3. KAYNAK BAĞLANTILARI

- **Resmî Ek-1 (asıl dayanak):** <https://www.resmigazete.gov.tr/eskiler/2021/09/20210928-4-1.pdf>
  — 28.09.2021 tarihli, 31612 sayılı Resmî Gazete, Maluliyet ve Çalışma Gücü Kaybı Tespiti İşlemleri Yönetmeliği Ek-1.
- **Yönetmelik metni:** <https://www.resmigazete.gov.tr/eskiler/2021/09/20210928-4.htm>
- **Karşılaştırma (resmî olmayan):** <https://www.engelliler.biz/maluliyet-ve-calisma-gucu-kaybi-hesaplama/>
  - Veri dosyası: <https://www.engelliler.biz/js/engellilerbiz/maluliyet/veri.v1.js>
- Not: Ek-1'in HTML sürümü (`20210928-4-1.htm`) yayımlanmamıştır (HTTP 404); tek resmî sürüm PDF'tir.

---

## 4. BULGULAR — KAYIT BAZLI TABLO

| Kayıt | Hastalık / alt madde | Resmî yer (Ek-1) | Sayfa | Tamamlanma durumu | Yapılan işlem |
| --- | --- | --- | --- | --- | --- |
| MEVCUT-088 | Skapulotorasik (tek taraflı) | G. Ortopedi ve Travmatolojik Hastalıklar, madde 1(a)(1) — Üst Ekstremite Amputasyon Düzeyi | 18 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-089 | Omuz dezartikülasyonu (tek taraflı) | Aynı yer, madde 1(a)(2) | 18 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-090 | Kol (omuz ile dirsek arası) (tek taraflı) | Aynı yer, madde 1(a)(3) | 18 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-091 | Dirsek dezartikülasyonu (tek taraflı) | Aynı yer, madde 1(a)(4) | 18 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-096 | Hemipelvektomi | Aynı yer, madde 1(b)(1) — Alt Ekstremite Amputasyon Düzeyi | 18 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-097 | Kalça dezartikülasyonu (tek taraflı) | Aynı yer, madde 1(b)(2) | 18 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-120 | Kalıcı ileostomi veya kolostomiler | İ. Gastroenteroloji, madde 10 | 28 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-121 | Bağırsak transplantasyonu | Aynı yer, madde 11 | 28 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-122 | Total pankreatektomi | Aynı yer, madde 12 | 28 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-123 | Whipple operasyonu | Aynı yer, madde 13 | 28 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |
| MEVCUT-181 | Akciğer Transplantasyonu | O. Göğüs Hastalıkları, madde 7 | 39 | Kriter gövdesi yok — çözümlenemedi | Değişiklik yapılmadı |

11 kaydın hepsinde veri durumu aynıdır: tek düzey `Ağır`, `kriter` boş, `kriter_durumu = baslik_var_metin_yok`,
`kaynak_dogrulama = metin_ve_gorsel_kontrol_edildi`.

Resmî metindeki görünüm (örnek, s.18): madde 1 altındaki amputasyon tablosunda düzey adı yazılmış,
altında **"Ağır Düzeyde Çalışma Gücü Kaybına Neden Olan Durumlar"** başlığı yer almış, ancak başlığın altında
hiçbir açıklama/kriter cümlesi bulunmamaktadır. Aynı desen s.28'de (Gastroenteroloji 10–13) ve s.39'da
(Göğüs 7) birebir tekrarlanmaktadır. Bu, tablo ayrıştırma hatası değil, **kaynağın kendisindeki boşluktur.**

---

## 5. SAYIMLAR (DOĞRULANMIŞ GERÇEK DURUM)

| Ölçüt | Değer |
| --- | --- |
| Toplam kayıt | 182 (182 benzersiz `mevcut_kayit_id`) |
| En az bir kriter metni dolu kayıt | **166** |
| Düzey başlığı var, kriter metni boş kayıt | **11** |
| Hiç düzeyi olmayan kayıt | **5** |
| Düzey başlığı bulunan kayıt | 177 |
| Toplam düzey nesnesi | 309 (298 dolu kriter + 11 boş kriter) |
| İncelenen / tamamlanan / boş bırakılan | **11 / 0 / 11** |

166 + 11 + 5 = 182. İstenen 166 ve 182 sayıları birebir tutmaktadır; hiçbir sayı zorla eşitlenmemiştir.

---

## 6. VERİ NEDEN DEĞİŞTİRİLMEDİ

- Resmî Ek-1'de bu 11 madde için kriter gövdesi **yoktur**; ek/geçici madde, dipnot veya yürürlük hükmü de yoktur.
- Başka maddelerden kriter türetmek (ör. amputasyon tablosundaki diğer satırlardan) mevzuatta karşılığı olmayan
  bir yorum olur; "hafif/orta/ağır" ayrımını ve tıbbi eşikleri bozar.
- Engelliler.biz aracı da aynı maddelerde boş dizi tutmaktadır; bağımsız ikinci kaynak da metin üretmemiştir.
- Bu nedenle `kriter` alanları boş, `ozet` sayıları ve `kriter_metni_var=false` işaretleri **olduğu gibi** korunmuştur.

**Değiştirilen dosyalar: yok.** Gömülü `ARAC3_MAPPING_DATA`, `arac3_182_ek1_eslestirme.json` ve `ozet`
alanlarına dokunulmadı; yedek alınmasını gerektiren bir değişiklik oluşmadı.

---

## 7. ARAYÜZ DAVRANIŞI (ŞİKAYETİN KAYNAĞI)

`renderLevelPicker` fonksiyonu, `kriter` alanı boş olan düzeyi bilinçli olarak **seçilemez** yapar ve
şu uyarıyı gösterir: *"Bu düzey başlığı kaynak veride bulunuyor ancak kriter metni boş. Seçilebilir düzey
olarak sunulmadı."*

Dolayısıyla bu 11 kayıt seçilemediği için "çalışmıyor" görünmektedir. Bu bir yazılım hatası değil,
**kaynak verideki boşluğun arayüzde doğru şekilde yansıtılmasıdır**. Arayüzde seçilebilir hale getirmek
kriter metni üretmez; ayrı bir tasarım/ürün kararı gerektirir ve bu görevin kapsamı dışındadır.

---

## 8. TEST SONUÇLARI

Geçici kopyada (`python -m unittest`, `pytest` kurulu değil) **11 test** çalıştırıldı: **10 geçti, 1 başarısız**.

- **Geçen:** `test_ek1_mapping_dataset_integrity` (182 kayıt / 177 düzey başlığı / 166 dolu / 11 boş),
  `test_mapping_is_embedded_and_does_not_depend_on_api`, `test_complete_source_counts`,
  `test_expected_fas_connections`, `test_source_traceability_is_present`,
  `test_source_markers_are_not_standalone_records`, `test_cognitive_mild_criterion_excludes_kds_table`,
  `test_mapping_notice_count_and_mobile_header_match_arac1`,
  `test_arac3_initializes_embedded_data_and_mobile_controls`,
  `test_shared_accessibility_toolbar_footer_and_mobile_layout`.
- **Başarısız:** `test_disease_specific_level_selection_ui`
  - Aranan metin: `Her hastalık için yalnızca seçtiğiniz düzeyin kendi kriteri gösterilir`
  - Arayüzdeki güncel metin: `Her hastalık için yalnızca seçilen düzeyin kriteri gösterilir.`
  - Bu, **bu görevle ilgisiz ve önceden var olan** test/metin uyumsuzluğudur: aynı uyumsuzluk
    `origin/cloud-run-migration` üzerinde de mevcuttur (HTML güncellenmiş, test güncellenmemiştir).
    Veri kaynaklı değildir ve bu görevde düzeltilmemiştir.

---

## 9. ÇELİŞKİLİ / DİKKAT EDİLMESİ GEREKEN BİLGİLER

1. **Başlık ≠ kriter.** Amputasyon tablosunda düzey adları (ör. "Skapulotorasik") dolu görünse de bunlar
   tablo satırı etiketidir; düzey başlığının altındaki kriter gövdesi değildir.
2. **`not` ve `dipnotlar` alanları arayüzde gösterilmez.** Bu alanlara açıklama eklemek kullanıcıya görünür
   bir değişiklik üretmez; yalnızca veri belgelenmiş olur.
3. **Testlerdeki 11 sayısı bilinçli sabittir.** Veri doldurulursa `ozet` alanları ve testler birlikte
   güncellenmelidir; aksi hâlde tutarsızlık oluşur.
4. **Gömülü veri ile yan JSON birebir aynıdır;** biri güncellenirse diğeri de güncellenmelidir.
5. **Sayfa numaraları PDF fiziksel sayfasıdır** (basılı Resmî Gazete sayfa numarasıyla birebir aynı).
6. Ek-1'in HTML sürümü bulunmadığı için doğrulama PDF (metin + taranmış görüntü) üzerinden yapılmıştır.

---

## 10. SONUÇ VE ÖNERİLER

- **Yapılabilecek en doğru işlem:** veriyi olduğu gibi bırakmak (kaynağa sadık; mevcut arayüz de bunu
  doğru biçimde açıklıyor).
- İstenirse, yalnızca veri belgesi olarak kayıt düzeyi `not` alanına "resmî kaynakta bu düzey için kriter
  gövdesi bulunmamaktadır" açıklaması eklenebilir (arayüzde görünmez).
- Bu 11 düzeyin arayüzde seçilebilir olması isteniyorsa, kriter metni üretmeden yalnızca seçim davranışını
  değiştiren ayrı bir ürün kararı ve onay gerekir.
- Resmî kaynak güncellenirse (Ek-1'de değişiklik/resmî açıklama yayımlanırsa) 11 kayıt yeniden değerlendirilmelidir.
