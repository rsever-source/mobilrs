# Araç-1 — Metinsel Ekran Taslağı (Wireframe)

Sürüm: 0.3 · Tarih: 28.10.2026 · Durum: **uygulama öncesi son**
Bağlı olduğu belge: `ARAC-1-SOZLESME.md`
Kapsam: Ruh Sağlığı · Deri · Hematoloji (EK-2 s.13-26)

> **0.3 değişikliği (karar uygulaması):** O-1 kararı işlendi — Araç-1 **yaş hesabı yapmaz**;
> %10 kuralı yalnız bilgi bloğunda açıklanır (§4.1). O-2 gereği tek kayıtlı grup sayısı 9'dur.
> Ekran akışı ve metinler değişmedi.
>
> **0.2 değişikliği:** sayılar 276 kesin / 10 belirsiz verisine göre güncellendi; belirsiz
> örneği X-D09 → **X-D03**; 65 yaş bilgi bloğu eklendi (§4.1); referans görsellerden alınan
> sadeleştirmeler §11'e işlendi. Görseller birebir kopyalanmadı.

> Bu belge **kod değildir**. Ekranların metin taslağıdır; geliştirici ve tasarımcı için
> yerleşim, metin ve davranış sözleşmesi. Örnekler katalogdaki gerçek kayıtlardan alınmıştır.

---

## 0. Genel yerleşim

```
┌──────────────────────────────────────────────────────────────┐
│  Engelli.me            [Engel Oranı Bul]   Balthazard Hesapla │  ← iki araç, iki sekme
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   [ Arama alanı ]                                            │
│   ┌────────────────────────────────────────────────────────┐ │
│   │ hastalık adı veya seviye yazın…                    🔍  │ │
│   └────────────────────────────────────────────────────────┘ │
│                                                              │
│   Bölüm:  ( Tümü )  Ruh Sağlığı   Deri   Hematoloji          │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│   SONUÇ ALANI (aşağıdaki ekranlar burada açılır)             │
└──────────────────────────────────────────────────────────────┘
  Bilgilendirme amaçlıdır; resmî sağlık kurulu raporu yerine geçmez.
```

İki araç **ayrı sekmelerdir**. Bu sayfa yalnız "Engel Oranı Bul" sekmesidir.

---

## 1. Ekran: Giriş / arama

Kullanıcı üç yoldan ilerleyebilir: arama, bölüm seçimi veya doğrudan listeden gezinme.

```
┌──────────────────────────────────────────────────────────────┐
│  Hastalığınızı arayın veya bölümden ilerleyin                │
│                                                              │
│  [ psori                                              🔍 ]   │
│                                                              │
│  Ruh Sağlığı (56)   Deri (142)   Hematoloji (78)             │
│  └ her biri tıklanabilir kart; sayı = kayıt sayısı           │
└──────────────────────────────────────────────────────────────┘
```

- Arama 3 karakterden sonra çalışır.
- Türkçe duyarsızdır: `psoriazis` → `psoriasis`, `isitme` → `işitme`.
- Arama hem hastalık adını hem seviye metnini tarar.
- Sonuç sayısı 0 ise Ekran 6'ya (boş/belirsiz) gidilir.

---

## 2. Ekran: Arama sonuçları

`psori` aramasının gerçek çıktısı:

```
┌──────────────────────────────────────────────────────────────┐
│  "psori" için 6 sonuç                        [ Filtreyi temizle ]│
│                                                              │
│  DERİ · A- Psoriasis                                    [V]  │
│    1- Hafif: vücudun %0-19'unu kaplayan             %5   >   │
│    2- Orta: vücudun %20-49'unu kaplayan             %15  >   │
│    3- Şiddetli: vücudun %50-79'unu kaplayan         %30  >   │
│    4- Çok şiddetli: vücudun %80-100'ünü kaplayan…   %40  >   │
│                                                              │
│  DERİ · Kütanöz T hücreli lenfoma                       [V]  │
│    5- Parapsoriazis geniş plak                      %10  >   │
│    6- Küçük plak parapsoriasis / dijitat dermatoz…  %10  >   │
└──────────────────────────────────────────────────────────────┘
```

- Satıra tıklamak seviye adımını **atlar**, doğrudan Ekran 4'ü açar.
- Bir seviye seçildiğinde diğer satırlar soluklaşır, seçim kalıcı olmaz.
- `[V]` = başlık rozeti (Roma numarası / harf), aramada da eşleşir.

---

## 3. Ekran: Bölüm → hastalık → seviye

Bölüm seçildiğinde hastalık listesi açılır; hastalık seçilince seviyeler sağda görünür.

```
┌───────────────────────┬──────────────────────────────────────┐
│ DERİ (142)            │  Kan damarlarının benign neoplazm ve  │
│                       │  hiperplazileri (kapiller anjiom,     │
│  ▸ I   Sebase…        │  kavernöz anjiom, lenfanjiom …)       │
│  ▸ II  Kıl follikülü  │  ─────────────────────────────────   │
│  ▸ III Egzematöz      │  ( ) 1- Hafif: %10-19…             %5 │
│  ▸ IV  İnflamatuvar   │  ( ) 2- Orta: %20-49…             %10 │
│  ▸ V   Psikiyatrik    │  ( ) 3- Şiddetli: %50-79…         %20 │
│  ▾ VI  Deri tümörleri │  ( ) 4- Çok şiddetli: %80-100…    %30 │
│      A. Benign …      │                                       │
│      B. Premalign     │  Kaynak: EK-2 s.18                    │
│      C. Malign        │                                       │
│  ▸ VII Fotosensitivite│                                       │
│  ▸ …                  │                                       │
└───────────────────────┴──────────────────────────────────────┘
```

- Sol sütun: bölüm → grup (DERİ'de 15 grup, Z'de 6, H'de 10 başlık).
- Sağ sütun: seçilen hastalığın seviyeleri + oranları.
- Seviye seçilince Ekran 4 açılır.

**Tek kayıtlı grupta seviye listesi görünmez.** Hastalık seçilir seçilmez sonuç açılır:

```
│  Reiter sendromu                      │  Tek oran: %5            │
│                                       │  Kaynak: EK-2 s.20       │
│                                       │  "Sadece deri lezyonları │
│                                       │   için"                  │
```

- Onay kutusu/radio yok, "seç" adımı yok.
- İkincil satırda `alt_tur` bir **ölçüt** olarak gösterilir (seviye değil).

---

## 4. Ekran: Sonuç

Bu ekran tasarımın merkezidir. Oran tek ve büyük; kısıtlar ayrı katmanda.

```
┌──────────────────────────────────────────────────────────────┐
│  DERİ · A- Psoriasis                                     [X]  │
│                                                              │
│     4- Çok şiddetli: vücudun %80-100'ünü kaplayan psoriasis  │
│                                                              │
│                         ┌──────────┐                         │
│                         │    %40   │   EK-2'de bu hastalık   │
│                         │          │   ve seviye için        │
│                         └──────────┘   tanımlı oran          │
│                                                              │
│  Kaynak: EK-2, sayfa 17 · kayıt D-028                        │
│                                                              │
│  Bu oran için geçerli kurallar (1)                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [YENİDEN DEĞERLENDİRME]  ℹ Bilgi                       │  │
│  │ Talep hâlinde yıllık kontrolle yeniden değerlendirilir.│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [ Bu oranı hesaplamaya ekle ]      [ Yeni arama ]           │
│                                                              │
│  Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık       │
│  kurulu raporu yerine geçmez.                                │
└──────────────────────────────────────────────────────────────┘
```

**Oran 0 durumu** (gerçek örnek: Z-022, Ruh Sağlığı s.14):

```
│                         ┌──────────┐                         │
│                         │    0     │   Bu basamakta kaynak   │
│                         │          │   0 oran veriyor        │
│                         └──────────┘                         │
│  Bu oran için geçerli kurallar (2)                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [KULLANIM SINIRI]  ⛔ Dikkat                           │  │
│  │ İş başvurusu ve vergi indiriminde bu derecelendirme    │  │
│  │ dikkate alınmaz.                                       │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ [GEÇİCİ DEĞERLENDİRME]  ⚠ Orta                        │  │
│  │ Geçici fonksiyon kaybı; 1 yıl sonra değerlendirilip    │  │
│  │ kesin karara varılır.                                  │  │
│  └────────────────────────────────────────────────────────┘  │
```

**Kısıt gösterimi kuralları**

Renk **tek başına anlam taşımaz**. Her kısıt üç katmanla gösterilir: (1) **tür etiketi**
(kelimeyle), (2) **ikon** (şekli birbirinden farklı), (3) **açıklama metni**. Renk yalnız
destekleyici ipucudur.

| Kod | Tür etiketi | Önem | İkon + renk | Açıklama metni |
| --- | --- | --- | --- | --- |
| `R-VERGI` | KULLANIM SINIRI | **Dikkat** | ⛔ kırmızı | "İş başvurusu ve vergi indiriminde bu derecelendirme dikkate alınmaz." |
| `R-REMISYON` | ORAN VERİLMEZ | **Dikkat** | ⛔ kırmızı | "Remisyonda ise oran verilmez." |
| `R-GECICI` | GEÇİCİ DEĞERLENDİRME | Orta | ⚠ amber | "Geçici fonksiyon kaybı; 1 yıl sonra değerlendirilip kesin karara varılır." |
| `R-NAKIL` | GEÇERLİLİK SÜRESİ | Orta | ⚠ amber | "Aktivasyon/gerileme ihtimali varsa rapor geçerlilik süresi belirtilir." |
| `R-YILLIK` | YENİDEN DEĞERLENDİRME | Bilgi | ℹ nötr | "Talep hâlinde yıllık kontrolle yeniden değerlendirilir." |
| `R-IKTIYOZ` | DEĞERLENDİRME YÖNTEMİ | Bilgi | ℹ nötr | "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir." |
| `R-EKTO` | DEĞERLENDİRME YÖNTEMİ | Bilgi | ℹ nötr | "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir." |

Kırmızı **yalnız** sonucun kullanılabilirliğini ortadan kaldıran iki durumda kullanılır
(`R-VERGI`, `R-REMISYON`). Diğerleri amber veya nötrdür; hiçbiri tek başına renkle anlatılmaz.

Kısıt **oranı değiştirmez**; oran kutusunun içinde değil, altında gösterilir.

### 4.1 65 yaş bilgi bloğu (her sonuçta)

> **Karar (O-1):** Araç-1 **yaş hesabı yapmaz** — bu blok bir hesap değil, bilgi bloğudur.
> %10 kuralı yalnız Araç-2'de uygulanır; burada **açıklanır**.

Oran kutusunun ve kısıtların **altında**, "Hesaplamaya ekle" butonundan önce:

```
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ℹ 65 yaş ve üzeri için ek oran                         │  │
│  │ Mevzuata göre 65 yaş ve üzerindeki bireylerin          │  │
│  │ engellilik oranına Balthazard formülü ile %10 eklenir. │  │
│  │ Bu ek yukarıdaki orana düz toplama ile eklenmez;       │  │
│  │ Balthazard yöntemiyle hesaplanır.  Örnek: %40 → %46.   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [ Bu oranı hesaplamaya ekle ]      [ Yeni arama ]           │
```

Kurallar:

- Blok **nötr** (gri/bilgi) — kırmızı veya amber **değil**; kısıt değildir, kısıt sayısına eklenmez.
- **Yukarıdaki oran değişmez.** %40 gösteriliyorsa kutu %40 kalır; %46 yalnız örnek cümlesinde
  geçer. "Nihai oran", "yaş dahil oran" gibi bir başlık **kullanılmaz**.
- %10 **otomatik aktarılmaz**; "Hesaplamaya ekle" yalnız katalog oranını taşır.
- Kullanıcının yaşı **sorulmaz**; blok koşullu cümleyle ("65 yaş ve üzerindeyseniz") verilir.

---

## 5. Ekran: Hematoloji bölüm notu

Yalnız Hematoloji bölümünde, sonuç alanının en altında, kısıtlardan görsel olarak ayrı:

```
│  ℹ Bölüm notu (kaynak s.26)                                  │
│  "Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali   │
│   olan hastalarda raporun geçerlilik süresi belirtilmelidir." │
│                                                              │
│  Bu not bölüm düzeyindedir; her kayda uygulanmış bir kısıt    │
│  değildir.                                                   │
```

- Gri/nötr kutu; `⚠`/`⛔` kullanılmaz (kısıt değildir).
- Kısıt sayısına **eklenmez**, `R-*` kodu **gösterilmez**.
- "Sadece nakil hastaları için" gibi daraltıcı ifade **eklenmez**.

Nakil kaydı seçildiğinde ikisi birlikte görünür (gerçek örnek: H-068, %30):

```
│  HEMATOLOJİ · IX- Allojenik kemik iliği/kök hücre nakli       │
│  1- Hastalığı remisyonda, komplikasyonu olmayan ve            │
│     immünosupresif tedavi almayanlar                         │
│                         ┌──────────┐                         │
│                         │    %30   │                         │
│                         └──────────┘                         │
│  [GEÇERLİLİK SÜRESİ]  ⚠ Orta                                │
│  Aktivasyon/gerileme ihtimali varsa rapor geçerlilik         │
│  süresi belirtilir.                    ← kayıt kısıtı         │
│  ℹ Bölüm notu (kaynak s.26): …          ← bölüm notu         │
```

---

## 6. Ekran: Belirsiz kayıt uyarısı

Bu kayıtlar `belirsiz.json` içinde `durum: "belirsiz"` olan **10 satırdır**; **oran gösterilmez**.
Gerçek örnek: **X-D03**.

```
┌──────────────────────────────────────────────────────────────┐
│  DERİ · IX- Pigment bozuklukları (vitiligo, depigmentasyon    │
│  ve melanoderma yapan hastalıklar)                        [X] │
│                                                              │
│  1- Vücut yüzeyinin %20-50'sini kaplayan                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Kaynakta bu hastalık için tek bir oran                │  │
│  │  belirlenmemiştir. Bu nedenle burada oran              │  │
│  │  hesaplanamaz; değerlendirme için ilgili uzman hekime  │  │
│  │  başvurulmalıdır.                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Kaynak notu (EK-2 s.19): bu satır bağımsız oran değil,      │
│  başka oranlara eklenen bir kurala tabi.                     │
│                                                              │
│  [ Yeni arama ]      [ İlgili diğer kayıtları gör ]           │
│                                                              │
│  Bu ekranda oran üretilmez, tahmin edilmez.                  │
└──────────────────────────────────────────────────────────────┘
```

Kurallar:

- "Bulunamadı" **denmez**; kaynağın sınırlaması açıklanır.
- Mesaj teşhis veya kesin tıbbi yönlendirme içermez; yalnız kaynak sınırlamasını ve
  uzman hekime başvuru gereğini belirtir.
- Oran kutusu hiç çizilmez (boş kutu bile gösterilmez).
- "Hesaplamaya ekle" butonu **görünmez**.
- Kaydın oranı (`5`) veri olarak dolu olsa da **gösterilmez**.
- **10** belirsiz kaydın tamamı aynı davranır; `sorun_tipi` kullanıcıya teknik kod olarak
  gösterilmez, tek cümleye çevrilir:

| `sorun_tipi` | Kullanıcıya gösterilen cümle |
| --- | --- |
| `coklu_kosul_tek_oran` | "Bu satır birden fazla klinik durumu tek orana bağlıyor." |
| `ekleme_kurali` | "Bu satır bağımsız oran değil, başka oranlara eklenen bir kural." |
| `olcum_iki_kriter` | "Oran iki ölçütün birlikte sağlanmasına bağlı." |
| `hiyerarsi_belirsiz` | "Alt koşulların üst basamakların yerine mi geçtiği belirsiz." |
| `harf_tekrari` | "Kaynakta madde numarası tekrar ediyor." |
| `kombinasyon_kisiti` | "Bu oran başka bir hastalıkla birlikte kullanılamaz." |
| `numaralandirma_atlamasi` | "Kaynakta madde numarası atlıyor." |

**`durum: "cozuldu"` satırları (11)** bu ekrana düşmez: kataloğa aktarılmışlardır ve normal
kayıt olarak sonuç verirler (Z-055, Z-056, D-139…D-142, H-074…H-078).

---

## 7. Ekran: Boş sonuç / kapsam dışı

```
│  "xyz" için sonuç bulunamadı                                 │
│  • Yazımı kontrol edin veya bölüm seçerek ilerleyin.         │
│  • Göz, işitme, konuşma ve kas-iskelet bölümleri bu araçta   │
│    henüz yok.                                                │
```

- Kapsam dışı bölüm seçilirse: "Bu bölüm henüz eklenmedi" — **oran uydurulmaz**.
- Belirsiz kayıtla eşleşme varsa boş sonuç yerine Ekran 6 gösterilir.

---

## 8. Araç-2'ye geçiş

"Hesaplamaya ekle" tıklandığında:

```
┌──────────────────────────────────────────────────────────────┐
│  Hesaplamaya eklendi: %40 — A- Psoriasis, 4- Çok şiddetli    │
│                                                              │
│  Eklenen oranlar (2)                                         │
│   • %40  A- Psoriasis, 4- Çok şiddetli          [kaldır]     │
│   • %30  Allojenik kemik iliği nakli, 1- …      [kaldır]     │
│                                                              │
│  [ Balthazard ile hesapla → ]    [ Alışverişe devam ]        │
└──────────────────────────────────────────────────────────────┘
```

Araç-2'ye geçildiğinde (ayrı sekme):

```
┌──────────────────────────────────────────────────────────────┐
│  Balthazard Hesapla                                          │
│                                                              │
│  ⓘ Bu araç yalnızca girdiğiniz oranları birleştirir.         │
│    Oranların doğruluğu ve kullanım kuralları burada          │
│    denetlenmez.                                              │
│                                                              │
│  %40   [etiket: A- Psoriasis, 4- Çok şiddetli]               │
│  %30   [etiket: Allojenik kemik iliği nakli, 1- …]           │
│  [ + Oran ekle ]                                             │
│                                                              │
│  Sonuç: …                                                    │
└──────────────────────────────────────────────────────────────┘
```

- Araç-2'ye yalnız **sayı + kısa etiket** geçer; hastalık bilgisi taşınmaz.
- Etiket yalnız liste başlığıdır; Araç-2 etiketten oran türetmez, kısıt denetlemez.
- Aynı kayıt ikinci kez eklenirse uyarı: "Bu kayıt zaten listede." (engellenmez)
- Araç-2'de kısıt uyarıları **gösterilmez**; yerine yukarıdaki kalıcı not bulunur.

---

## 9. Metin sözlüğü (birebir kullanılacak)

| Yer | Metin |
| --- | --- |
| Oran etiketi | "EK-2'de bu hastalık ve seviye için tanımlı oran" |
| Kısıt başlığı | "Bu oran için geçerli kurallar" |
| Kısıt tür etiketleri | KULLANIM SINIRI · ORAN VERİLMEZ · GEÇİCİ DEĞERLENDİRME · GEÇERLİLİK SÜRESİ · YENİDEN DEĞERLENDİRME · DEĞERLENDİRME YÖNTEMİ |
| Önem etiketleri | "Dikkat" · "Orta" · "Bilgi" |
| Bölüm notu başlığı | "Bölüm notu (kaynak s.26)" |
| Belirsiz mesajı | "Kaynakta bu hastalık için tek bir oran belirlenmemiştir. Bu nedenle burada oran hesaplanamaz; değerlendirme için ilgili uzman hekime başvurulmalıdır." |
| Alt bilgi (her ekran) | "Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık kurulu raporu yerine geçmez." |
| Araç-2 uyarısı | "Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım kuralları burada denetlenmez." |

**Yasak ibareler** (hiçbir ekranda geçmez):

- "çalışma gücü kaybı oranı"
- "kesin engellilik oranınız"
- "maluliyet oranı"
- "resmî raporunuz" / "bu sonuç rapor yerine geçer"

---

## 10. Bu taslakta yapılmayanlar

- Kod, bileşen, API, veritabanı — yok.
- Katalog verisi, oran, kısıt değeri değişmedi.
- Balthazard formülü ve yuvarlama bu belgede tanımlanmadı; yalnız "iki araç aynı motoru
  kullanır, 65 yaş eki tek noktada uygulanır" sınırı geçerlidir. Gösterim kuralı (en fazla
  2 ondalık, yarı yukarı, tek kez) **ortak motorda** tanımlıdır
  (`ORTAK-MOTOR-SOZLESME.md` §7.2; `bicimle_gosterim()`), bu belgede yeniden yazılmaz.
  65 yaşın **Araç-1'de gösterimi** §4.1'de tanımlıdır (hesaplama değil, bilgi bloğu).
- Göz, işitme, konuşma, kas-iskelet bölümleri kapsam dışı.

---

## 11. Referans görsellerden alınanlar / alınmayanlar

İki ekran görüntüsü (Engelliler.biz kaynaklı) **yalnız tasarım ve kullanım kolaylığı**
referansıdır; birebir kopyalanmadı, oradaki metin/oranlar doğru kabul edilmedi.

**Alınanlar (Araç-1):**

| Fikir | Nasıl uygulanır |
| --- | --- |
| Tek ekranda arama + sonuç | Arama ve sonuç aynı sayfada; modal/açılır pencere yok (§0) |
| Kategori çipleriyle hızlı daraltma | Yalnız **3 bölüm** çipi + "Tümü"; 19 kategori çipi kopyalanmaz |
| "Seçtikleriniz" özet kutusu | "Eklenen oranlar" listesi (§8), ama oran toplamı **gösterilmez** |
| Boş durum metni | §7: "sonuç bulunamadı" + yazım önerisi + kapsam dışı bilgisi |
| Kalıcı alt bilgi | Her ekranda bilgilendirme notu (§9 metin sözlüğü) |

**Alınmayanlar (Araç-1):**

| Fikir | Neden alınmadı |
| --- | --- |
| Anatomi figürü | 3 bölüm için gereksiz; mobilde yer kaybı, erişilebilirlik yükü |
| Boşken "%0" gösteren halka | Seçim yapılmadan oran varmış izlenimi verir |
| Dev gradyan başlık bandı | Engelli.me'nin sade tasarımıyla uyumsuz, mobilde yer kaybı |
| 19 kategori çipi | Kapsam 3 bölüm; çip sayısı gerçek veriyle sınırlı tutulur |
| Oranı yuvarlak "skor" gibi sunma | "Nihai oran" izlenimi verir; oran düz metin + kaynak künyesiyle verilir |
