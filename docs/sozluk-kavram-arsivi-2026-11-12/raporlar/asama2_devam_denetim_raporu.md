# Aşama 2 (devam) — Denetim Raporu

**Üretim tarihi:** 12.11.2026
**Çıktı:** `sozluk_kavram_data.json`
**Boyut:** 509.283 bayt
**SHA-256:** `710f86b20806910475c4c733404237c38cd117a780be7b0e9cb2dbf6ec003702`
**Kayıt:** **745** (EK-1: 276, EK-2: 469) — önceki aşamanın 486 kaydının üzerine
**259 yeni EK-2 kaydı** eklendi.
**Dal:** `archive/sozluk-kavram-asama2-devam-2026-11-12`

Bu rapor, aşama 2 devamında eklenen 259 kaydın nasıl üretildiğini, hangi
denetimlerden geçtiğini ve hangi noktaların açık kaldığını kayda geçirir.
Kaynakta bulunmayan hiçbir tanım, derece, oran, ICD kodu, eş anlamlı veya
madde etiketi yazılmamıştır.

---

## 1. Özet

| Ölçüt | Sonuç |
| --- | --- |
| Kayıt sayısı | **745** (EK-1 276 + EK-2 469) |
| Yeni eklenen kavram | **259** (tamamı EK-2, 12 bölüm, s.29-169) |
| Şema v1.0.3_taslak | **745/745 PASS** |
| Şema v1.0.0 | 275/745 PASS (470 hata — şema farkı, veri kusuru değil) |
| `kavram_id` benzersizliği | 745/745 |
| XOR (tek mevzuat bağlantısı) ihlali | 0 |
| `kavram_id` önek hatası | 0 |
| Resmî Gazete künye hatası | 0 |
| `kaynak.sayfa_no` aralık hatası | 0 |
| Uydurulmuş ICD kodu / eş anlamlı / tanım | 0 / 0 / 0 |
| Kanıt izi | 745 kayıt için iz: 596 birebir, 11 düzeltilmiş, 138 bulanık, **0 eşleşmeyen** |
| Aşama 1 testleri | 46/46 + 12/12 PASS |
| Yeni kayıt kanıt doğrulaması | 259/259 birebir (0 hata) |

`main`, `cloud-run-migration` ve canlı hizmet üzerinde hiçbir işlem yapılmadı.

---

## 2. Kaynak

| Dosya | Bayt | SHA-256 |
| --- | --- | --- |
| `ek2_2019_rg.pdf` (172 sayfa, OCR kaynağı) | 4.853.292 | `b630f6adfc12144d22b9ce36f1ac7e660650b4f13e9dfd8d207ba21501d9ad28` |
| `ek2_025_169_kaynak_adaylari.json` (aşama 2 aday havuzu) | 60.914 | `6889e7ffbb192ae05e49fe8d934546c165750b9479bcd050f001ac13ed72e60a` |
| `ek2_ek_kayitlar.json` (yeni kayıt kaynağı, 259 kayıt) | 68.641 | `c0df33eb9c0ca1b95e8304e0e9858e09a377f22c1971e2ebfb8a8cfa604cdb02` |
| `u1_ek1_001_020.json` (135) | 28.363 | `73ac0e18d7fc48242936d8f529abc8b94cb03c9d2cd696f8564dfed287a14d86` |
| `u2_ek1_021_040.json` (141) | 28.209 | `0216ab14584b97cf5c63964571494e5a62fd3296ba3eb96a582f3d429d471773` |
| `u3b_ek2_003_024.json` (142) | 42.017 | `7046a3a66ded03411ba715a503abee5055f93d209f4fa70440c9b763c5ebe3dd` |
| `sozluk_kavram.v1.0.3_taslak.json` (bağlayıcı şema) | 11.762 | `e5e3f409bd78371e1e6e341c689a7964c532868bcc1e39aa550bcfc410db49d2` |

EK-2 PDF'inin metin katmanı 172 sayfanın tamamında **0 karakterdir**; bu yüzden
EK-2 tarafındaki bütün ad/etiket/sayfa bilgisi OCR çıktısına dayanır ve PDF
metniyle bağımsız doğrulanamaz (bkz. `asama2_belirsizler.md` §1.1).

---

## 3. Aday farklarının açıklanması

### 3.1 "142 / 141" (EK-2 s.3-24)

`u3b_ek2_003_024.json` parça dosyasında **142** kayıt vardır. Veri dosyasına
**141** kayıt geçer; fark tek kayıttır: **Eritroderma (s.21)** sayfada iki kez
geçtiği için aynı sayfa + aynı ad anahtarıyla tek kayda indirilmiştir.
Ayrıntı: `asama2_belirsizler.md` §? / `birlestir_nihai.py::ek2_birlestir`.

### 3.2 "555 / 136" (EK-2 s.25-169 adayları)

| Sayı | Kaynak dosya | Ne ölçüyor |
| --- | --- | --- |
| **555** | `arsiv_cikti/ek2_025_169_kavram_aday_havuzu.json` (arşiv noktası, 1.000 satırda kesik, JSON olarak geçersiz) | 2026-11-11 turunda üretilen **ham OCR satır adayları** — başlık, açıklama, tablo satırı ve kavram hiyerarşisi ayrımı yapılmamış satırlar |
| **136** | `arac/ek2_25_169_kayitlar.json` | `ek2_25_169_ayristir.py` ayrıştırıcısının ürettiği **filtrelenmiş aday kayıtları** (bölüm/alt bölüm/madde etiketi/ad alanları doldurulmuş) |

Bu ikisi farklı sayım birimleridir; 555 "kavram sayısı" değildir. Doğrulanabilir
olan sayı **136**'dır ve bu dosya yeniden üretilebilir
(`python arac/ek2_25_169_ayristir.py` → 136 kayıt). 136 = 69 alınan + 67 elenen
(`arac/aday_farki.txt`).

> Arşivdeki 555'lik dosya 1.000 satırda kesik olduğu için içeriği bağımsız
> olarak doğrulanamaz; bu nedenle kavram sayısı olarak kullanılmaz.

### 3.3 EK-1: 5 derece farkı ve 8 ad uyuşmazlığı

`ek1_metinli.pdf` metin katmanıyla yapılan karşılaştırma sonucu aynen geçerlidir:
155 PDF anahtarı / 158 veri anahtarı, 154 ortak, 149 derece birebir aynı.

| Fark | Sonuç |
| --- | --- |
| F/6, İ/3 derece farkı + R/1, R/2, R/3 "ortak hüküm" | Ayrıştırıcı yapıntısı; **veri kaynağa uygundur** |
| 8 ad uyuşmazlığı (7 yazım farkı + 1 yapı farkı = J/1) | Kaynak/OCR yazım farkı; **uydurma değildir** |

Tam liste ve gerekçeler: `asama2_belirsizler.md` §4.3-4.4.

### 3.4 Kanıtsız 3 kayıt — çözüldü

Aşama 2'de s.20'deki üç kaydın (`derinin premalign tümörlerine bağlı doku veya
fonksiyon kayıpları`, `malign deri tümörlerinde doku veya fonksiyon kayıpları`,
`ileri klinik evreli, tedaviye cevap vermeyen malign deri tümörü`) kanıt izi
bulunamıyordu (`durum: "yok"`, benzerlik 0,62-0,71). Bu kayıtların kanıt metni
kaynakta **iki satıra bölünmüş** hâlde duruyordu. `kanit_izi.py`, bu durum için
`u3b` parça dosyasındaki kaynak metni (OCR satırlarının birebir birleşimi)
kullanacak şekilde genişletildi; üç kayıt da `durum: "duzeltilmis"` ile kanıt
metnine bağlandı. **Artık kanıt metni olmayan kayıt yoktur (0/745).**

---

## 4. Yeni kayıtların üretimi

### 4.1 Yöntem

EK-2'nin aşama 2'de kapsam dışı bırakılan 29-169. sayfaları **elle** tarandı.
Her kayıt için kaynak sayfada geçen **gerçek hastalık/kavram adı** alındı;
tablo içindeki oran/puan satırları, Balthazard formülü satırları, saf ses
(kriter) satırları ve değerlendirme kriterleri kayıt yapılmadı.

Kaynak dosya: `arac/ek2_ek_kayitlar.py` → `arac/ek2_ek_kayitlar.json`
(259 kayıt; her satır `sayfa | bolum_adi | alt_bolum | madde_etiketi |
kanonik_ad | ham_satir`).

`ham_satir`, terimin OCR metninde geçtiği satırdır ve **kanıt izi olarak
birebir saklanır**.

### 4.2 Sayfa numarası kaymalarının düzeltilmesi

İlk derlemede 24 kaydın sayfa numarası, kanıt satırının gerçekten bulunduğu
OCR sayfasıyla uyuşmuyordu (ör. "Curling ülseri" 85 yerine 84; "Tablo 3.30"
başlığı 154 yerine 155). `arac/sayfa_duzelt.py` ile 23 kaydın sayfası, 1 kaydın
kanıt satırı (OCR'da `ı. OMURGAYA AİT SORUNLARDA ENGELLİLİK` yazımı) düzeltildi.
Doğrulayıcı `arac/ek2_ek_dogrula.py` **0 hata** verir.

### 4.3 Yinelenen kayıt

`ENTEROKÜTAN FİSTÜLLER` (s.69) başlığı aşama 2'de zaten kayıt olarak vardı;
yeni derlemede aynı başlığın ikinci bir kaydı üretildi ve **elenerek** mevcut
kayıt korundu (aşama 2 verisi bozulmadı).

### 4.4 Dağılım

| Sayfa aralığı | Bölüm | Yeni kayıt |
| --- | --- | --- |
| s.29-34 | KARDİYOVASKÜLER SİSTEM | 23 |
| s.35-64 | GÖRME SİSTEMİ | 28 |
| s.65-71 | SİNDİRİM SİSTEMİ | 21 |
| s.72-73 | KADIN HASTALIKLARI VE DOĞUM | 4 |
| s.74-78 | ÜROGENİTAL / ÜRİNER SİSTEM | 39 |
| s.79-82 | ENDOKRİN SİSTEM | 7 |
| s.83 | GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ | 7 |
| s.84-85 | YANIKLAR | 6 |
| s.86 | ONKOLOJİ | 3 |
| s.87-92 | SİNİR SİSTEMİ | 23 |
| s.93-137 | KAS-İSKELET (omurga, üst ekstremite) | 27 |
| s.138-169 | KAS-İSKELET (alt ekstremite, nöroloji) | 71 |
| | **Toplam** | **259** |

### 4.5 EK-2 toplam dağılım (469 kayıt)

| Bölüm | Kayıt | | Bölüm | Kayıt |
| --- | --- | --- | --- | --- |
| KAS-İSKELET SİSTEMİ | 98 | | SİNDİRİM SİSTEMİ | 26 |
| DERİ | 70 | | HEMATOLOJİK HASTALIKLAR | 25 |
| KULAK BURUN BOĞAZ | 44 | | GEÇİCİ FONKSİYON KAYBINA NEDEN OLAN RUHSAL HASTALIKLAR | 16 |
| ENDOKRİN SİSTEMİ | 35 | | ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR | 11 |
| ÜRİNER SİSTEM VE ERKEK GENİTAL SİSTEM | 31 | | YANIKLAR | 8 |
| SİNİR SİSTEMİ | 29 | | ÜROGENİTAL SİSTEM | 8 |
| GÖRME SİSTEMİ | 28 | | GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ | 7 |
| KARDİYOVASKÜLER SİSTEMİ | 26 | | KADIN HASTALIKLARI VE DOĞUM | 4 |
| | | | ONKOLOJİ | 3 |

EK-2 artık **3-169 sayfa aralığında 105 farklı sayfada** kayıt içerir; EK-2'nin
17 üst bölümünün tamamı sözlükte temsil edilir.

### 4.6 Alan doluluk oranları (EK-2, 469 kayıt)

| Alan | Dolu | Boş |
| --- | --- | --- |
| `bolum_adi` | 469 | 0 |
| `alt_bolum` | 392 | 77 |
| `madde_etiketi` | 194 | 275 |
| `tanim` | 0 | 469 |
| `icd10` | 0 | 469 |

EK-1'de de `icd10` 0'dır: `kanit/icd10_who.json` içindeki 8 WHO kodunun hiçbiri
mevcut kavramlarla yeterli özgüllükte eşleşmedi. `es_anlamli` tüm veri
dosyasında 0'dır.

---

## 5. Doğrulama sonuçları

### 5.1 Şema uyumu

| Şema | Geçen | Kalan | Sonuç |
| --- | --- | --- | --- |
| v1.0.3_taslak | 745 | 0 | **745/745 PASS** |
| v1.0.0 | 275 | 470 | Fark, veri kusuru değil (şema farkı) |

### 5.2 Yapısal denetim

| Denetim | Sonuç |
| --- | --- |
| `kavram_id` benzersizliği | 745/745 |
| XOR (aynı kayıtta iki mevzuat bağlantısı) | 0 ihlal |
| `kavram_id` önek uyumu (`ek1_`/`ek2_`) | 0 ihlal |
| RG künyesi (tarih/sayı/MBS/URL) | 0 ihlal |
| `sayfa_no` aralığı (EK-1 1-40, EK-2 3-169) | 0 ihlal |
| EK-1'de / EK-2'de `icd10` bulunması | 0 / 0 |
| Yeni kayıt: kendi içinde yinelenen ad | 0 |
| Yeni kayıt: mevcut 210 EK-2 kaydıyla çakışma | 0 |
| Yeni kayıt: kanıt satırının sayfası ile `sayfa_no` uyuşmazlığı | 0 |

### 5.3 Aşama 1 testlerinin yeniden koşulması

| Test dosyası | Sonuç |
| --- | --- |
| `testler/test_sozluk_kavram.py` (yapısal) | **46/46 PASS** |
| `testler/veri_testleri.py` (içerik, D1-D7) | **12/12 PASS** |

`pytest` bu ortamda kurulu değildir; testler doğrudan Python ile koşulur.

### 5.4 Veri kalite taraması

| Tarama | Sonuç |
| --- | --- |
| Ad içinde `U+FFFD` / `?` / çift boşluk / boşlukla biten ad | 0 / 0 / 0 / 0 |
| 200+ karakter ad | 4 (en uzun 236) |
| `tanim` dolu kayıt | 0 |
| `es_anlamli` dolu kayıt | 0 |

---

## 6. Tekrar üretim

Tüm komutlar arşiv klasörünün kökünde, PowerShell'de
`$env:PYTHONIOENCODING="utf-8"` ayarlıyken koşulur:

```powershell
python -X utf8 arac\ek2_ek_kayitlar.py     # 259 kaydin kaynak dosyasi
python -X utf8 arac\birlestir_nihai.py     # veri dosyasi + kaynak eslesme
python -X utf8 arac\kanit_izi.py           # kanit izleri
python -X utf8 arac\nihai_denetim.py       # sema / XOR / kimlik / kunye denetimi
python -X utf8 arac\ek2_ek_dogrula.py      # yeni kayit dogrulama (0 hata)
python -X utf8 testler\test_sozluk_kavram.py
python -X utf8 testler\veri_testleri.py
```

Beklenen sonuç: **745 kayıt, 509.283 bayt, SHA-256
`710f86b20806910475c4c733404237c38cd117a780be7b0e9cb2dbf6ec003702`,
v1.0.3 745/745 PASS, testler 46/46 + 12/12 PASS.**

Not: `birlestir_nihai.py` her koşuda `arac\ek2_kaynak_eslesme.json` dosyasını
yeniden yazar; `kanit_izi.py` bu dosyayı okuduğu için sıra korunmalıdır.

---

## 7. Bilinen sınırlar

| Konu | Durum |
| --- | --- |
| EK-2 adlarının PDF metniyle bağımsız doğrulanması | Mümkün değil — PDF'te metin katmanı yok |
| EK-2 `tanim` alanı | Boş (469/469); kaynakta kavram bazlı tanım alanı yok |
| ICD-10 eşleştirmesi | 0 kod; 8 WHO kodu yeterli özgüllükte eşleşmedi |
| Eş anlamlılar | 0; kaynakta doğrulanmış liste yok |
| Oran/puan/Balthazard aktarımı | Hiç yapılmadı (kapsam dışı) |
| Kanıt izi "bulanık" olan 138 kayıt | Ad, sayfadaki en yakın satırla eşleşti (skor ≥ 0,80); metin birebir değildir |
| `pytest` ile koşum | Kurulu değil; testler doğrudan Python ile koşuldu |

Ayrıntılı belirsizlik listesi: `asama2_belirsizler.md`.
