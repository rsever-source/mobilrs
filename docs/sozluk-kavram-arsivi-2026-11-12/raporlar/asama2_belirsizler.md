# Aşama 2 — Belirsizlikler ve Çözülemeyen Noktalar

**Üretim tarihi:** 12.11.2026 (aşama 2 devam güncellemesi ile)
**Veri dosyası:** `sozluk_kavram_data.json` — **745 kayıt** (EK-1 276 + EK-2 469),
SHA-256 ve boyut için `raporlar/asama2_devam_denetim_raporu.md`
**Kaynaklar:** EK-1 (28.09.2021/31612) ve EK-2 (20.02.2019/30692)

> **Güncelleme notu (12.11.2026, aşama 2 devam):** EK-2'nin 29-169. sayfaları
> elle derlenerek **259 yeni kayıt** eklendi; sözlük 486 → 745 kayda çıktı.
> Bu notta işaretlenen §2.3, §3.1, §3.3, §5, §6.1 ve §8 maddeleri güncel
> durumla değiştirilmiştir. Ayrıntılı üretim ve denetim kaydı:
> `raporlar/asama2_devam_denetim_raporu.md`.

Bu rapor, sözlüğe **alınmayan**, **alınamayan** veya **alınırken yorum gerektiren**
her noktayı listeler. Hiçbir yerde kaynakta olmayan bir bilgi tamamlanmamıştır;
okunamayan yerler boş bırakılmış veya kapsam dışı sayılmıştır.

---

## 1. Kaynak belirsizlikleri

### 1.1 EK-2 PDF'inde metin katmanı yok

`ek2_2019_rg.pdf` (4.853.292 bayt, 172 sayfa, SHA-256 `b630f6ad…d9ad28`)
taranmış görüntüdür: **172 sayfanın tamamında metin katmanı 0 karakterdir.**
Bu nedenle EK-2 tarafındaki bütün ad, etiket ve sayfa bilgileri OCR çıktısına
dayanır ve PDF metniyle bağımsız olarak doğrulanamaz.

- EK-1'de bu eksik yoktur: `ek1_metinli.pdf` 40 sayfa, 108.818 karakterlik gerçek
  metin katmanı içerir; EK-1 kayıtları ayrıca PDF metniyle karşılaştırılmıştır (§4.3).

### 1.2 `ek2_170` boş sayfa → EK-3 Balthazard tablosu

OCR çıktısında `ek2_170.txt` **0 karakterdir**. Sayfa görüntüsü elle okunduğunda
bu sayfanın **"BALTHAZARD HESAPLAMA TABLOSU" (EK-3)** olduğu görülmüştür.
Yani boşluk bir OCR hatası değil, sayfanın tablo olmasındandır; sayfa kavram
sözlüğüne alınmamıştır.

Aynı bölümde: s.169 yalnızca sistemik romatizmal hastalıklar için değerlendirme
kuralı metnidir (kavram adı yok), s.171-172 **EK-4** sağlık kurulu raporu
formlarıdır (Önyüz/Arkayüz). Üçü de kapsam dışıdır.

### 1.3 `kaynak.sayfa_no` PDF sayfasıdır, basılı sayfa numarası değildir

Kayıtlardaki `sayfa_no`, PDF dosyasındaki fiziksel sayfa indeksidir (EK-1: 1-40,
EK-2: 1-172). Belgenin üzerinde basılı numara farklı olabilir; örneğin PDF 21.
sayfada basılı "40" yazmaktadır. Bir kaydı kâğıt üzerinde ararken bu fark
gözetilmelidir.

---

## 2. OCR kaynaklı belirsizlikler (EK-2)

### 2.1 Karakter karışmaları

OCR, Türkçe harfleri ve rakamları düzensiz bozar. Sözlüğe alınan adlarda bu
bozulmalar **yalnızca anlamı kesin olan yerlerde** düzeltilmiştir; şüpheli
olanlar olduğu gibi bırakılmıştır.

| OCR çıktısı | Doğrusu | Nerede |
| --- | --- | --- |
| `0rta` | Orta | s.20, 21, 79 |
| `ŞiddetIi`, `Şiddetlİ` | Şiddetli | s.20, 21 |
| `I -`, `l.`, `ı-` | 1- | hemen her tablo |
| `yğnelik` | yönelik | s.20 |
| `biillü` | büllü | s.21 |
| `Kryle` | Kyrle | s.20 |
| `%50-94100` | %50-94 / %100 (bozuk) | s.21 |
| `Difftiz` | Diffüz | s.79, 81 |
| `MarjoIİn` | Marjolin | s.84 |
| `Konfijzyonel` | Konfüzyonel | s.89 |
| `ACJH` | ACTH | s.79 |
| `Hasta11klar1` | Hastalıkları | s.26 |
| `fpnksiyon`, `tarafmdan`, `aıliriti` | fonksiyon, tarafından, ağırlığı | s.12, 81 |

Sözlükte `U+FFFD` (bozuk karakter), `?` veya çift boşluk **hiç yoktur**
(0/486). Yani bozuk karakterler veriye taşınmamıştır; sorun yalnızca harf
düzeyindeki karışmalardır.

### 2.2 Satır kayması nedeniyle kesilen 8 ad — düzeltildi

EK-2'de uzun kavram adları 2-3 satıra bölünür. Otomatik ayrıştırıcı yalnız ilk
satırı aldığı için 8 ad yarım kalmıştı. Adlar, kaynak sayfadaki **aynı cümlenin
devamı** olan satırlarla birleştirilerek tamamlandı; ham OCR satırı kanıt
dosyasında `durum: "duzeltilmis"` olarak saklanır.

| Sayfa | Düzeltilen ad | Ne yapıldı |
| --- | --- | --- |
| 81 | Diffüz primer osteoporoz (radyolojik dekalsifikasyonla birlikte spontan kırıklar, şekil bozuklukları yapan) | Satır devamı eklendi, `Difftiz`→`Diffüz` |
| 84 | Yanık zemininde gelişen Marjolin ülseri ve skuamöz kanserler | Cümle kuyruğu (`İlgili branş tarafından`) çıkarıldı, `MarjoIİn`→`Marjolin` |
| 88 | İnsomniler (…7 alt tip…) | 3 satır birleştirildi |
| 88 | Uykuda solunum bozuklukları (…) | 2 satır birleştirildi |
| 88 | Hipersomniler (…) | 2 satır birleştirildi |
| 89 | Sirkadiyen uyku-uyanıklık ritm bozuklukları (…) | 5 satır birleştirildi |
| 89 | Parasomniler (…) | 3 satır birleştirildi |
| 89 | Uykuda hareket bozuklukları (…) | 2 satır birleştirildi |

Bu 8 ad, `kavram_id` üretimini de değiştirmiştir; eski kimliklerle eşleştirme
yapılacaksa `arac/ek2_kaynak_eslesme.json` kullanılmalıdır.

### 2.3 Kanıt satırı bulunamayan 3 kayıt (s.20) — **çözüldü**

Aşağıdaki üç kayıtta ad, sayfadaki tek bir satırdan birebir çıkmaz; ad, bölüm
başlığı ile açıklama cümlesinin birleşiminden oluşur. Benzerlik skoru
0,62 / 0,63 / 0,71 idi (eşik 0,80).

- `ek2_s020_derinin_premalign_tumorlerine_bagli_do`
- `ek2_s020_malign_deri_tumorlerinde_doku_veya_fon`
- `ek2_s020_ileri_klinik_evreli_tedaviye_cevap_ver`

Kaynak metin (s.20): *"B DERİNİN PREMALİGN TÜMÖRLERİ / Primer tümörün sebep
olduğu veya bu tümöre yönelik tedavi sonrasında gelişen doku veya fonksiyon
kayıpları"*. Ad bu iki parçadan türetilmiştir; **yeni bir ifade eklenmemiştir**.

**Aşama 2 devamda çözüldü:** kanıt izi üretimi, kaynak metni iki satıra
bölünmüş bu üç kayıt için `u3b_ek2_003_024.json` parça dosyasındaki kaynak
metninden (OCR satırlarının birebir birleştirilmiş hâli) alınacak şekilde
genişletildi. Üç kayıt da `durum: "duzeltilmis"` ile kanıt metnine bağlandı;
artık **kanıt metni olmayan kayıt yoktur** (0/745).

### 2.4 s.81-82 metabolizma: sütun karışması

Bu sayfalarda harf listesi (`a)`…`p)`) ile hastalık adları ayrı sütunlarda,
puanlar ise adlardan tamamen kopuk biçimde alt alta gelmektedir. OCR sırayı
koruyamadığı için:

- Hangi puanın hangi maddeye ait olduğu **güvenilir biçimde belirlenemez**;
  bu nedenle sözlüğe hiçbir oran/puan alınmamıştır.
- Yalnız adı net okunan maddeler alınmıştır (Metabolizma Hastalıkları,
  Diffüz primer osteoporoz, Osteomalazi, Lesch-Nyhan, Ciddi Obezite).
- s.82'deki `l)`-`p)` maddeleri (Glikozaminoglikan/Glikoprotein metabolizması,
  Kistik fibrozis, İskelet displazileri, Akondroplazi) adları okunabildiği hâlde
  **hangi üst maddeye bağlı oldukları belirsiz** olduğu için alınmamıştır.

### 2.5 s.72-73 sağ kenar kesik (KADIN HASTALIKLARI VE DOĞUM)

Kriter cümleleri sayfanın sağ kenarından kesilmiştir ("…müsait v", "…süregen
tedavi gerektirmeye", "…servikal darhk"). Cümleler tamamlanamadığı ve bu
bölümde kavram **adı** değil derece kriteri yazıldığı için bölümün tamamı
(0 kayıt) kapsam dışı bırakılmıştır.

### 2.6 Numarasız oran listeleri

s.74-78, s.83, s.86-87 ve s.90-92 sayfalarında madde numarası olmayan, yalnız
yüzde/oran ve kısa açıklama içeren listeler vardır. Bunlar "hastalık kavramı"
değil **puanlama satırı** olduğundan sözlüğe alınmamıştır.

---

## 3. Kapsam dışı bırakılan sayfa ve adaylar

### 3.1 Aşama 2'de bütünüyle kapsam dışı sayılan 107 sayfa — güncel durum

Aşama 2'de aşağıdaki sayfa aralıkları "yalnız puanlama tablosu" gerekçesiyle
tamamen dışarıda bırakılmıştı. **Aşama 2 devamda bu sayfalar elle tarandı** ve
içlerindeki **gerçek hastalık/kavram adları** sözlüğe alındı; puan, oran,
Balthazard ve saf değerlendirme kriteri satırları yine alınmadı.

| Sayfa aralığı | Sayfa | Aşama 2 gerekçesi | Aşama 2 devam sonucu |
| --- | --- | --- | --- |
| 35-64 | 30 | GÖRME: işlevsel puanlama yöntemi, eşdeğerlik/alan tabloları | **28 kayıt** (GÖRME bölümü) |
| 93-137 | 45 | KAS-İSKELET: eklem hareket açıklığı/tanı modelleri | **27 kayıt** (omurga hastalıkları, üst ekstremite ampütasyon/artroplasti/tenosinovit) |
| 138-164 | 27 | KAS-İSKELET: periferik sinir, amputasyon, artroplasti tabloları | **71 kayıt** (alt ekstremite: uzunluk farkı, yürüyüş, kas kuvveti, eklem, ankiloz, ampütasyon, artroplasti, kırık, vasküler) |
| 165-168 | 4 | Sınıflama tabloları (Tablo 4.1-4.3) | **4 kayıt** (bölüm/konu başlıkları) |
| 169 | 1 | SİSTEMİK ROMATİZMAL: yalnız değerlendirme kuralı metni | **1 kayıt** (bölüm adı; hastalık listesi sayfada yok) |

Aşama 2 devamda da **kayıt içermeyen 62 sayfa** var (3-169 aralığında); bunlar
yalnız ölçüm/puan tablosu, örnek olay veya oran satırı içeren sayfalardır
(ör. s.36-39, 41, 50, 52-55, 59-64 GÖRME eşdeğerlik tabloları; s.109-134 üst
ekstremite hareket açıklığı tabloları; s.94-96, 100, 105-106 örnek/tablo
sayfaları). Tam liste: `arac/ek2_25_169_kapsam_disi.json` ve
`arac/aralik_dagilim.py` çıktısı.

### 3.2 Ayrıştırıcının ürettiği 136 adaydan elenen 67 satır

Otomatik ayrıştırma s.25-169 için 136 "aday" üretti; bunlardan **69'u** elle
denetlenerek alındı, **67'si** alınmadı. Eleme gerekçeleri:

| Bölüm | Elenen | Tipik gerekçe |
| --- | --- | --- |
| YANIKLAR | 22 | Alt bentler ("…ilgili branş tarafından değerlendirilir") ve yüzde dilimleri |
| HEMATOLOJİK | 10 | Aynı hastalığın alt evresi/risk sınıfı (İntermedya, transfüzyon bağımlı, IPSS düşük) |
| KARDİYOVASKÜLER | 10 | Kriter cümlesi, implant adı, eşik değeri (İCD implantasyonu, 30-40 mmHg) |
| ENDOKRİN | 7 | Alt bent, komplikasyon tanımı, tek başına derece etiketi |
| SİNİR | 6 | Nöbet sıklık sınıfları, ağrı dereceleri, okunamayan artık satır (`I) kullanılacaktır`) |
| SİNDİRİM | 5 | Sınıflama kriteri başlığı (s.65-67, 70-71) |
| KADIN HASTALIKLARI | 3 | "1-Derece fonksiyonel/yapısal kayıp" kriter satırları |
| ONKOLOJİ | 3 | Evre/remisyon alt bentleri |
| GÖĞÜS | 1 | Tüberküloz değerlendirme kuralı |

Tam liste: `arac/aday_farki.py` çıktısı (`arac/aday_farki.txt`).

### 3.3 Sözlükte hiç kaydı olmayan EK-2 bölümleri — güncel durum

Aşama 2'de GÖRME, KAS-İSKELET, KADIN, GÖĞÜS ve ONKOLOJİ bölümlerinin
tamamı boştu. **Aşama 2 devamda bu beş bölümün tamamı dolduruldu** (aynı
bölümdeki kayıt sayılarıyla):

| Bölüm | Kayıt | Sayfa |
| --- | --- | --- |
| GÖRME SİSTEMİ | 28 | 35-58 |
| KAS-İSKELET SİSTEMİ | 98 | 93-169 |
| KADIN HASTALIKLARI VE DOĞUM | 4 | 72-73 |
| GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ | 7 | 83 |
| ONKOLOJİ | 3 | 86 |

EK-2'nin **17 üst bölümünün tamamının** artık en az bir kaydı vardır
(bkz. `arac/bolum_basliklari.py` çıktısı). Ancak bu bölümlerde alınan kayıtlar
**hastalık/kavram adlarıdır**; puanlama tablosunun kendisi alınmamıştır.

İçerik olarak hâlâ alınmayan tek başlık, s.169'daki **SİSTEMİK ROMATİZMAL
HASTALIKLAR** bölümüdür: sayfada yalnız değerlendirme kuralı metni vardır,
hastalık listesi yoktur; bölüm adının kendisi tek kayıt olarak alınmıştır.

---

## 4. EK-1 belirsizlikleri

### 4.1 Derecesi olmayan 4 kural maddesi (veri dosyasına alınmadı)

Şemada `ek_1_baglantisi.derece` zorunludur. Aşağıdaki dört madde ağır/orta/hafif
bloğu içermediği için sözlüğe alınmamış, ayrı arşiv dosyasında tutulmuştur
(`arsiv_cikti/ek1_derecesiz_kurallar.json`):

| Bölüm | Sıra | Konu |
| --- | --- | --- |
| E | 24 | Maluliyet süresi kuralı (18 ay) |
| G | 2 | İki orta ampütasyon → ağır sayılır |
| G | 3 | İki hafif ampütasyon → orta sayılır |
| O | 8 | "Karar verilemeyen durumlar" (KPET değerlendirme kuralı) |

### 4.2 J/1: tek sıra numarası altında iki ayrı kavram

Kaynakta J/1 tek numaradır ama iki alt grup içerir:

- "Kutanöz T hücreli lenfomalar" (ağır, hafif)
- "MF dışı diğer kutanöz lenfomalar" (ağır, hafif)

Her alt grup ayrı kayıt olarak tutuldu (**4 kayıt**). PDF'te üst ad
"Kütanöz lenfoma a) Kutanöz T hücreli lenfomalar" biçimindedir; veri alt grup
adlarını kullanır. Bu, aynı bölüm+sıra numarasını paylaşan tek çoklu-ad
durumudur.

### 4.3 EK-1 PDF metin katmanı karşılaştırması

`ek1_metinli.pdf`'in metin katmanı (yazı tipi kalın/gövde ayrımıyla) ayrıştırıldı
ve veriyle karşılaştırıldı: **155 PDF anahtarı / 158 veri anahtarı, 154 ortak,
149 derece birebir aynı.**

Kalan farkların tamamı açıklanmıştır:

| Fark | Açıklama |
| --- | --- |
| Yalnız PDF: O/8 | "Karar verilemeyen durumlar" — derecesi yok, §4.1 gereği alınmadı |
| Yalnız veri: F/7, J/6, K/8, İ/4 | Bu maddelerin başlık satırı PDF'te **kalın değil**; ayrıştırıcı atladı. Metinde maddeler mevcut, veri doğru |
| F/6 ve İ/3 derece farkı | Ayrıştırıcı, kalın olmayan başlık yüzünden **sonraki maddenin** derece bloğunu öncekine ekledi. Veri doğru (F/6 yalnız ağır; İ/3 ağır+hafif) |
| R/1-3 | "ORTAK HÜKÜMLER" bloğunda derece etiketi yok; veri `ortak_hukum` kullanır |

Ad karşılaştırması: **143 tam, 3 kısmi, 8 uyuşmazlık** (7 yazım farkı + 1 yapı
farkı — J/1).

### 4.4 Yazım varyantları (veri ↔ PDF)

Bunlar hata değil, kaynak/OCR yazım farkıdır; veri OCR okumasını izler:

| Veri | PDF metni |
| --- | --- |
| Kuadripleji/Kuadraparezi | Kuadripleji/Kuadriparezi |
| Miyelodisplastik / Miyeloproliferatif neoplaziler **(MDS/MPN)** … | aynı ad, kısaltma eklenmemiş |
| Ampütasyonlar | Amputasyonlar |
| Epidermolizis bülloza | Epidermolizis büllosa |
| Hipertrofik ve restriktif kardiyomiyopati | … kardiyomyopati |
| Raynaud Fenomeni | Reynaud Fenomeni |
| Tiroid ve Paratiroid bez hastalıkları | … Parotiroid … |

`MDS/MPN` eki ve "Ampütasyonlar" yazımı veri tarafında kalmıştır; ikisi de
kaynakta geçen biçimlerdir, uydurma değildir.

### 4.5 Bölüm harfi `İ`

EK-1'de `I` harfi bölüm olarak kullanılmaz; sıra `… H, İ, J …` biçimindedir.
`kavram_id` üretiminde `İ→I` dönüşümü yapılır (`ek1_i_01_…`), `bolum_harfi`
alanında ise kaynaktaki `İ` korunur.

---

## 5. Boş bırakılan alanlar ve gerekçeleri

| Alan | Durum | Gerekçe |
| --- | --- | --- |
| `ek_2_baglantisi.tanim` | **469/469 boş** | EK-2 bir puanlama tablosudur; kavram bazlı tanım alanı yoktur. Başlıktan sonra gelen satır çoğu zaman ya başlığın tekrarı, ya bir alt madde, ya bir puan satırıdır. Bu satırları "tanım" saymak yanlış atıf olurdu; alan tamamen boşaltıldı. Kaynak satırlar `arac/kanit_izleri.json` içinde durur |
| `ek_2_baglantisi.icd10` | **0** | Sekiz WHO kodunun hiçbiri EK-2 kavramlarıyla yeterli özgüllükte eşleşmiyor; eşleşmeyen kod yazılmadı |
| `es_anlamli` | **0/745** | Kaynaklarda doğrulanmış eş anlamlı listesi yok; uydurulmadı |
| `ek_2_baglantisi.madde_etiketi` | 275 kayıtta boş (194 dolu) | Kaynakta madde numarası/rumuz yok (bölüm başlığı düzeyindeki kavramlar) |
| `ek_2_baglantisi.alt_bolum` | 77 kayıtta boş (392 dolu) | Kaynakta ara başlık yok |

---

## 6. Şema belirsizlikleri

### 6.1 v1.0.0 ile v1.0.3 çelişkisi

- **v1.0.3_taslak** (11.762 bayt, `e5e3f409…b49d2`) bağlayıcı kabul edildi:
  `kanonik_ad` 500, `tanim`/`madde_etiketi` opsiyonel, `kaynak.sayfa_no` zorunlu.
- **v1.0.0** (10.273 bayt) ile 745 kaydın **275'i** geçer, 470'i geçmez.
  Farklar veri kusuru değil şema farkıdır:
  - 276 × `required @ ek_2_baglantisi` (`tanim`, `madde_etiketi`)
  - 12 × `maxLength @ ek_2_baglantisi/alt_bolum` (120 karakter sınırı)
  - 4 × `maxLength @ kanonik_ad` (200 karakter sınırı; en uzun ad 236)

Aynı dosya iki şemaya göre farklı sonuç verdiği için, hangi şemanın yürürlükte
olduğu **açıkça kararlaştırılmalıdır**. Bu çalışma v1.0.3'ü esas alır.

### 6.2 `kanit_metin` alanı şema dışında

Aşama 1'de EK-1 parça dosyalarında `kanit_metin` alanı kullanılmıştı; şemada
böyle bir alan yok. Bu yüzden kanıt metinleri veri dosyasına değil, ayrı
`arac/kanit_izleri.json` dosyasına yazıldı (486 iz). Şema değişikliği
yapılmadı.

---

## 7. "424 / 560 / 555 / 418" sayıları hakkında uyarı

Bu sayılar çeşitli yerlerde "resmî kavram sayısı" gibi anılmaktadır. **Değildir.**
Sırasıyla farklı sayım birimlerine (madde, derece bloğu, alt bent, tablo satırı)
karşılık gelirler ve birbirleriyle tutarsızdır. Bu çalışmada kavram sayısı
olarak yalnız **üretilen kayıt sayısı** (486) ve onun belgelenmiş dağılımı
kullanılır.

---

## 8. Karar bekleyen noktalar

1. **Şema sürümü:** v1.0.3 mü yürürlükte, yoksa v1.0.0'a göre mi uyum isteniyor?
   *(Aşama 2 devamda da v1.0.3 esas alındı; 745/745 PASS.)*
2. **`tanim` alanı:** boş bırakılması kabul ediliyor mu, yoksa EK-2 için elle
   tanım yazılması mı isteniyor? (Elle yazım, kaynak dışı bilgi riski taşır.)
3. ~~**Kapsam dışı bölümler:** GÖRME, KAS-İSKELET, KADIN, GÖĞÜS, ONKOLOJİ
   bölümleri ayrı bir elle derleme turuyla eklenmeli mi?~~
   → **Çözüldü (12.11.2026):** beş bölüm de elle derlendi, 140 kayıt eklendi.
4. **`Ampütasyonlar` / `MDS/MPN` yazımları:** OCR biçimi korunsun mu, PDF metin
   katmanındaki biçime mi çevrilsin?
5. ~~**Git:** değişiklikler henüz commit edilmedi.~~
   → **Çözüldü:** `archive/sozluk-kavram-asama2-devam-2026-11-12` dalında
   arşivlendi; `main` / `cloud-run-migration` / canlı hizmet değiştirilmedi.
