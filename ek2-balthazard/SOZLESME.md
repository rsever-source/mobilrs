# EK-2 Balthazard — Bağlayıcı Sözleşme

Sürüm: 1.3 · Tarih: 29.10.2026 · Durum: **Araç-1/Araç-2 yerel prototipleri çalışıyor**
Kapsam: ortak hesaplama motoru, Araç-1 (Engel Oranı Bul) veri/ekran kuralları,
Araç-2 (Balthazard Hesapla) davranışı, resmî kaynak karşılaştırması ve karar durumu.

> Bu belge **kod değildir**; bağlayıcı davranış sözleşmesidir. 28.10.2026'da altı ayrı
> belge (`ORTAK-MOTOR-SOZLESME`, `ARAC-1-SOZLESME`, `ARAC-1-WIREFRAME`,
> `ARAC-2-WIREFRAME`, `ARAC-1-2-HAZIRLIK-RAPORU`, `OKUBENI`) içerik kaybı olmadan bu
> dosyada birleştirildi. Sürüm geçmişi §10'dadır.
>
> **Temel ilke:** iki araç aynı motoru çağırır; hiçbir ekran kendi hesabını yapmaz ve
> motorun döndürmediği bir sayıyı göstermez.

---

## 1. İki araç ve ortak motor

| | **Araç-1: Engel Oranı Bul** | **Araç-2: Balthazard Hesapla** |
| --- | --- | --- |
| Soru | "Bu hastalık ve seviye için mevzuatta hangi oran var?" | "Bildiğim oranların bileşkesi ne eder?" |
| Kullanıcı girdisi | hastalık + seviye seçimi | **elle girilen oranlar** |
| Veri kaynağı | katalog (286 satırın 276 kesin kaydı) | yok |
| Ne üretir | mevzuattaki tek oran (bileşen) | oranların bileşkesi |
| Kısıt denetimi | **evet** | **hayır** — yapılamaz, uyarı zorunlu |
| Hastalık bilgisi | var | **yok** (yalnız sayı + isteğe bağlı etiket) |
| 65 yaş eki | **uygulanmaz**; bilgi olarak açıklanır (§3.14) | **uygulanır** (tek nokta: motor) |
| Hesap modeli | canlı — seçim/ekleme anında sonuç yenilenir | **"Hesapla" butonu** — sonuç yalnız butonla üretilir |

**Değişmez kurallar:**

1. Araç-2 hiçbir zaman "bu hastalığa şu oran verilir" demez; yalnız girilen sayıları
   birleştirir.
2. Araç-1'in ürettiği oran **çalışma gücü kaybı oranı değildir**; EK-2'de hastalık ve
   şiddet seviyesi karşılığı tanımlanmış orandır. İki kavram hiçbir ekranda eşitlenmez.
3. Araç-1'in çıktısı (bileşen) ile Araç-2'nin çıktısı (bileşke) **aynı hukuki sonuç**
   gibi sunulmaz.
4. İki araç **aynı hesaplama motorunu** kullanır: `balthazard()` + yaş eki. 65 yaş eki
   **tek uygulama noktasında** uygulanır; hiçbir ekran kendi ekini hesaplamaz.

Araç-1 motoru tek bileşenle çağırır: `oranlar = [x]`, `yas` yine zorunlu,
**`yas_ekle = false`**. Motor `yas_eklemesi.uygulandi = false` döner ve Araç-1 yaş eki
satırını **çizmez**. Yaş eklemesinin tek uygulama yeri yine motordur; Araç-1 onu
**istemez**, kendi eklemez.

---

## 2. Ortak motor sözleşmesi

Modül: `balthazard_motoru.py` · `MOTOR_SURUMU = "0.2"` · yalnız standart kütüphane.

```
balthazard(girdi) → cikti
```

### 2.1 Girdi

| Alan | Tip | Zorunlu | Kural |
| --- | --- | --- | --- |
| `girdi.oranlar` | tam sayı listesi | **evet** | En az 1 öğe; her öğe 0–100; sıra **anlamsız** (motor sıralar) |
| `girdi.yas` | `"65_alti" \| "65_ve_uzeri"` | **evet** | Varsayılan **yok**; `null`/eksik → hata |
| `girdi.yas_ekle` | gerçek `bool` | hayır (varsayılan `true`) | Yalnız Araç-1 gibi bilgi amaçlı çağrılarda `false` |

- **Etiket, hastalık adı, kayıt kimliği motora girmez.** Motor veri tanımaz; yalnız sayı
  ve yaş alır.
- Oran sayısı için **üst sınır yok** (Ek-3: "işlem sonsuza kadar devam ettirilebilir").
- Girdi listesi motor içinde **değiştirilmez** (kopya üzerinde çalışılır).
- `yas_ekle` **yalnızca** `True`/`False` kabul eder. `"false"`, `0`, `1`, `None`, `0.0`
  sessizce `bool()` ile dönüştürülmez; çağrı reddedilir. Sözleşmede bu alan için ayrı
  kod yoktur; uygulama `E_YAS_GECERSIZ` + `alan: "yas_ekle"` eşlemesini kullanır ve yeni
  kod/metin uydurmaz. Doğrulama sırası: `oranlar` → `yas` → `yas_ekle`.

### 2.2 Çıktı

```
{
  ok: true,
  sonuc: {
    deger: sayı,            // ham (yuvarlanmamış) değer
    tam_sayi_mi: boolean,   // deger % 1 == 0
    yas_dahil: boolean
  },
  adimlar: [
    { sira: 1, onceki: sayı, eklenen: sayı, sonuc: sayı, tur: "bileske" | "yas_eki" }
  ],
  siralama: {
    kural: "buyukten_kucuge",
    uygulanan: [sayı, …]    // motorun gerçekten kullandığı sıra
  },
  yas_eklemesi: {
    uygulandi: boolean,
    oran: 10,               // sabit
    dayanak: "Yönetmelik m. 10/4 (RG 20.02.2019, 30692)"
  },
  yuvarlama: {
    uygulandi: false,       // B-2: motor yuvarlamaz
    kural: null,
    not: "Ham değer döndürülür; yuvarlama yalnız gösterim katmanında, en fazla 2 ondalık (G-1…G-4)."
  },
  uyarilar: [
    { kod: "U_ORAN_TEKRAR", mesaj: "…" }
  ]
}
```

Hata durumunda:

```
{ ok: false, hata: { kod: "E_…", mesaj: "kullanıcıya gösterilecek metin", alan: "oranlar" } }
```

- **İstisna (exception) fırlatılmaz**; her durum `ok` alanıyla döner. Arayüz `ok=false`
  ise sonuç çizmez, `hata.mesaj`'ı gösterir.
- `adimlar` her zaman **büyükten küçüğe** üretilir; yaş eki varsa **son adım** olarak
  `tur: "yas_eki"` ile eklenir. Arayüz adım üretmez, yalnız çizer.
- `siralama.uygulanan`, "biz sıraladık" bilgisini göstermek için döner; arayüz bu listeyi
  **değiştiremez**.
- `yuvarlama.uygulandi` **her zaman `false`**, `yuvarlama.kural` **her zaman `null`**.

### 2.3 Hata kodları

| Kod | Durum | Kullanıcıya gösterilecek metin | Alan |
| --- | --- | --- | --- |
| `E_ORAN_YOK` | Liste boş | "En az bir oran girin." | `oranlar` |
| `E_ORAN_ARALIK` | Öğe < 0 veya > 100 | "Oran 0 ile 100 arasında olmalıdır." | `oranlar` |
| `E_ORAN_TAMSAYI` | Öğe tam sayı değil | "Oran tam sayı olmalıdır." (**ürün tercihi**, B-7) | `oranlar` |
| `E_ORAN_TIP` | Öğe sayı değil | "Yalnız sayı girin." | `oranlar` |
| `E_YAS_SECILMEDI` | `yas` boş/null | "Yaş aralığını seçin." | `yas` |
| `E_YAS_GECERSIZ` | Bilinmeyen değer | "Yaş aralığını seçin." | `yas` |

**Kötü niyetli/bozuk girdilerde yeni kod uydurulmaz**, en yakın sözleşme kodu kullanılır:
`girdi` sözlük değilse → `E_ORAN_TIP` (`alan="girdi"`); `oranlar` liste/demet değilse →
`E_ORAN_TIP` (`alan="oranlar"`); `bool` oran → `E_ORAN_TIP`; `NaN`/`inf` → `E_ORAN_TIP`;
`12.0` gibi tam sayı değerli float tam sayıya normalize edilir; `12.5` →
`E_ORAN_TAMSAYI`.

### 2.4 Uyarılar (hata değil, `uyarilar` dizisi)

| Kod | Durum | Metin | Davranış |
| --- | --- | --- | --- |
| `U_ORAN_TEKRAR` | Aynı değer iki kez | "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir." | **Engellenmez**; bilgi, onay istemez (B-6) |
| `U_ORAN_100` | 100 var | "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?" | Onay istenir (B-4 açık: kırpma kuralı yok) |
| `U_ORAN_SIFIR` | 0 var | "0 oranı listeye eklendi. Bileşkeyi değiştirmez." | Bilgi |

**Katalog bütünlük hataları** motorun değil, yükleme katmanının konusudur (§3.4):
sayı değişmişse, kimlik boşluğu varsa veya `oran` aralık dışıysa uygulama **açılmaz**.

### 2.5 Yaş kuralı

**Eşik: 65 yaş ve üzeri.** Dayanak: *Erişkinler İçin Engellilik Değerlendirmesi Hakkında
Yönetmelik*, m. 10/4 — "65 yaş ve üzeri bireylerin engellilik oranına Balthazard formülü
ile %10 eklenerek".

| Kural | Açıklama |
| --- | --- |
| Yöntem | **Balthazard**: `yeni = A + (100 − A) × 10 / 100`. Aritmetik `+10` **değil** |
| Aşama | Bileşke hesaplandıktan **sonra**, son adım olarak |
| Seçim | `yas` zorunlu; `65_alti` seçilirse ek uygulanmaz |
| Tek nokta | Ek yalnız bu fonksiyonun içinde; arayüz/ekran ekleme yapmaz |
| Araç-1 | `yas_ekle=false`; sonuç EK-2 temel oranıdır (O-1) |
| Örnek | `[40] + 65+` → **46** (yuvarlama gerekmez) |
| Kaynak gösterimi | Kaynak künyesi **yalnız** "65 yaş ve üzeri" seçiliyken sonucun altında (§5.7) |

**Kaynak çelişkisi (kayıtlı, kapatılmadı):** Ek-3'ün (e) bendi "60 yaşın üzerindekilerde"
diyor. Uygulama kararı **65**'tir (B-1, 28.10.2026 ürün kararı). Eşik motorda **tek
sabit** olarak tutulur; iki ayrı yerde yazılmaz.

**B-3 kapandı:** sıra ham bileşke → yaş eki (ham) → **tek** gösterim yuvarlaması. Yaş eki
yuvarlanmış değere uygulanmaz.

### 2.6 Sıralama

- Kural: **büyükten küçüğe**, iki kez doğrulandı (Geçici m. 2/2-b ve Ek-3 notu).
- Kullanıcı sıra **seçemez**; arayüz sıra bilgisi **göndermez**.
- Eşit değerlerde sıra değişmez (kararlı sıralama); sonucu etkilemez.
- Sıralama **sayısal**dır (metin sıralaması yasak: `"100" < "40"` tuzağı).

### 2.7 Yuvarlama ve gösterim

**Hesap (motor) — B-2 kapandı:**

- Motor **ham** değeri döndürür (`sonuc.deger`), `sonuc.tam_sayi_mi` ile birlikte; ara
  aşamalarda yuvarlama **yapmaz**.
- `yuvarlama.uygulandi = false`, `yuvarlama.kural = null`.
- Ara adımlar (`adimlar[]`) da ham değer taşır; hiçbir katman adımı yeniden yuvarlamaz.
- İçeride ikili kayan nokta gürültüsünü önlemek için **`Fraction`** aritmetiği kullanılır;
  dışarıya tek dönüşümle `int` (tam sayıysa) veya `float` verilir. Bu bir yuvarlama
  değildir; `tam_sayi_mi` kesrin paydasından **kesin** hesaplanır.

**Gösterim — G-1…G-4 kapandı (28.10.2026 ürün kararı):**

Dayanak: mevzuatta (Yönetmelik, EK-2 kılavuzu, Ek-3) **gösterim hükmü yoktur**. Karar
ürün/arayüz tercihidir, hukuki kural değildir; hesabı değiştirmez.

| # | Karar | Sonuç |
| --- | --- | --- |
| G-1 | Ondalık basamak | **En fazla 2**, sondaki gereksiz sıfırlar atılır; **tam sayıda ondalık gösterilmez** |
| G-2 | Yuvarlama yönü | **Yarı yukarı** (`ROUND_HALF_UP`); kesme ve yarı çift (`banker's`) kullanılmaz |
| G-3 | Yaş ekinin sırası | Ham bileşke → **yaş eki (ham)** → **tek yuvarlama** |
| G-4 | Adım dökümünde ondalık | **Evet**, aynı kural; ham değer ayrıca taşınır |

**Bağlayıcı kurallar:**

1. **Yuvarlama tek kez, yalnız sunumda:** ham değer → metin. Zincirde ikinci yuvarlama
   yoktur (adım → toplam → metin gibi ara yuvarlama yasak).
2. **Ham değer korunur:** gösterim motora geri yazılmaz; `sonuc.deger` ve `adimlar[]`
   yuvarlanmış değerle değiştirilmez.
3. **Kopyalama / dışa aktarma ham değeri taşır** (yuvarlanmış metin değil).
4. **Türkçe ondalık virgül** varsayılandır; teknik çıktı (JSON, test) **nokta** kullanır.
5. Ondalık ayırıcı yalnız sunum katmanında belirlenir; hesap katmanı ayırıcı bilmez.
6. Ekran "yaklaşık", "~" veya "en yakın tam sayı" ifadesini **kendi başına eklemez**.
7. Gösterim kuralı değişirse (ör. 1 ondalık) **yalnız sunum katmanı** değişir; motor, test
   vektörleri ve ham değerler aynı kalır.

**Uygulama:** `balthazard_motoru.bicimle_gosterim(deger, basamak=2, ayirici=",")` — ayrı
**sunum** yardımcısıdır, `balthazard()` çıktısını değiştirmez.

**Gösterim örnekleri:**

| Ham `sonuc.deger` | Gösterim | Not |
| --- | --- | --- |
| `40` / `46` / `58` | `40` / `46` / `58` | Tam sayıda ondalık yok (G-1) |
| `55.11` | `55,11` | İki ondalık korunur |
| `62.2` | `62,2` | Sondaki sıfır atılır |
| `59.599` | `59,6` | Yarı yukarı: `59,60` → `59,6` |
| `69.9237` | `69,92` | İki basamak |
| `82` | `82` | Tam sayı |

### 2.8 Test vektörleri — ham değer

| # | `oranlar` | `yas` | Beklenen `sonuc.deger` | Not |
| --- | --- | --- | --- | --- |
| 1 | `[40]` | `65_alti` | `40` | Tek oran → kendisi |
| 2 | `[40, 30]` | `65_alti` | `58` | `40 + 60×30/100` |
| 3 | `[40]` | `65_ve_uzeri` | `46` | `40 + 60×10/100` — ürün örneği |
| 4 | `[0]` | `65_alti` | `0` | 0 gerçek kayıt (Z-056) |
| 5 | `[100]` | `65_alti` | `100` | Üst sınır |
| 6 | `[0, 40]` | `65_alti` | `40` | 0 etkisiz |
| 7 | `[100, 40]` | `65_alti` | `100` | 100 kilitler |
| 8 | `[30, 40]` | `65_alti` | `58` | Girdi sırası sonucu değiştirmez |
| 9 | `[40]` | `65_ve_uzeri` + `yas_ekle=false` | `40` | Araç-1 bilgi çağrısı |

**Beklenen hatalar:**

| # | Girdi | Beklenen |
| --- | --- | --- |
| 10 | `[]` | `E_ORAN_YOK` |
| 11 | `[120]` | `E_ORAN_ARALIK` |
| 12 | `[12.5]` | `E_ORAN_TAMSAYI` |
| 13 | `[40]`, `yas = null` | `E_YAS_SECILMEDI` |

**Ondalık sonuçlu vektörler — ham değer ve gösterim ayrı doğrulanır:**

| # | `oranlar` | `yas` | Ham `sonuc.deger` | Gösterim |
| --- | --- | --- | --- | --- |
| 14 | `[33, 33]` | `65_alti` | `55.11` | `55,11` |
| 15 | `[49, 49]` | `65_alti` | `73.99` | `73,99` |
| 16 | `[40, 30]` | `65_ve_uzeri` | `62.2` | `62,2` |
| 17 | `[33, 33]` | `65_ve_uzeri` | `59.599` | `59,6` |
| 18 | `[33, 33, 33]` | `65_alti` | `69.9237` | `69,92` |
| 19 | `[40, 40]` | `65_alti` | `64` | `64` |
| 20 | `[80]` | `65_ve_uzeri` | `82` | `82` |

- Ham değer yuvarlanmış beklentiyle karşılaştırılmaz (17 için `59.6` yazılmaz).
- `59.599 → "59,6"`, sondaki sıfır atmanın yuvarlamadan **ayrı** bir adım olduğunu gösterir.
- Tam sayı çıkan ham değerlerde gösterim de ondalıksızdır.

### 2.9 Açık kararların motora etkisi

| ID | Konu | Motor bugün ne yapar | Kod için gerekli mi? |
| --- | --- | --- | --- |
| B-2 | Yuvarlama | Yuvarlamaz, ham döner | **Hayır (kapandı)** |
| B-3 | Yaş ekinin sırası | Yaş ekini ham bileşkeye uygular | **Hayır (kapandı)** |
| B-4 | Tavan / 100 aşımı | Kırpma yapmaz | Hayır — **açık**, kural uydurulmaz |
| B-5 | 0 / 100 | Özel işlem yapmaz | Hayır — **açık**, özel işlem eklenmez |
| B-6 | Aynı oranın tekrarı | Engellemez; `U_ORAN_TEKRAR` bilgi uyarısı | Hayır (kapandı) |
| B-7 | Ondalıklı giriş | `E_ORAN_TAMSAYI` ile reddeder | Hayır (kapandı — ürün tercihi) |
| B-8 | DERİ +%5 | **Uygulamaz**; katalogda yok | Hayır — **açık** (X-D03) |

### 2.10 Uygulamaya aktarımda doğrulanacaklar

1. İki araç da **aynı** fonksiyonu çağırıyor (kopya hesap yok) — kod aramasıyla doğrulanır.
2. `yas` parametresi olmadan çağrı reddediliyor (zorunlu alan).
3. Yaş eki ve sıralama yalnız motorda; arayüzde `sort`, `+10`, `× 0.9` benzeri hesap yok.
4. Test vektörleri 1–20 birebir geçiyor (1–13 ham tam sayı, 14–20 ham ondalık).
5. `yuvarlama.uygulandi` her yanıtta `false`; hiçbir katman kendi yuvarlamasını yapmıyor.
6. Motor katalog dosyalarını **okumaz**; yalnız sayı listesi ve yaş alır.
7. **Gösterim tek yerde:** ekranlar `bicimle_gosterim()` dışında biçimlendirme yapmıyor.
8. **Ham değer korunuyor:** gösterimden sonra `sonuc.deger` / `adimlar[]` değişmiyor;
   kopyala/dışa aktar ham değeri taşıyor.

---

## 3. Araç-1 — veri sözleşmesi

### 3.1 Kaynak dosyalar — salt okunur

| Dosya | Rol | Yazma |
| --- | --- | --- |
| `veri/katalog.json` | **276 kesin kayıt** | **hayır** |
| `veri/belirsiz.json` | 21 satır (11 `cozuldu`, 10 `belirsiz`) | **hayır** |

Dosyalar depoda `ek2-balthazard/veri/` altında tutulur ve EK-2 çalışmalarında tek doğruluk
kaynağıdır. Kaynak sürümler geçici klasörde `katalog_taslak.json` / `belirsiz.json` adıyla
duruyordu; depoya alınırken **yalnız ad ve yol** değişti, içerik **bayt düzeyinde aynıdır**
(MD5 §8.1). Katalog verisi kendiliğinden yorumlanmaz; açık kararlar bu dosyaya bakılarak
kapatılmaz.

`veri/belirsiz.json` içindeki `cozuldu` satırlar **tarihsel iz**tir: kataloğa aktarılmışlardır,
arama sonucu olarak **gösterilmezler**. Yalnız `durum: "belirsiz"` olan 10 satır §3.10'a
girer.

Uygulama açılışta okur, bellekte tutar. Katalog çalışma zamanında **hiçbir koşulda**
yazılmaz; türetilmiş alanlar dosyaya eklenmez.

### 3.2 Kullanılan alanlar

| Alan | Tip | Kullanım |
| --- | --- | --- |
| `id` | metin | **tek anahtar**; seçim ve aktarım yalnız bununla |
| `bolum` | metin | 1. düzey gezinme |
| `grup` | metin (yalnız DERİ, 142/142) | 2. düzey gezinme |
| `hastalik` | metin | 3. düzey: hastalık adı |
| `alt_tur` | metin | 4. düzey: seviye / ölçüt |
| `oran` | tam sayı | **sonuç** (0-100; 0 = "oran verilmez") |
| `sayfa` | tam sayı | kaynak izlenebilirliği |
| `kisit` | **liste** | uyarı üretimi |
| `kaynak_not` | metin (varsa) | dipnot gösterimi |

### 3.3 Türetilmiş alanlar (bellekte, dosyaya yazılmaz)

| Türetim | Kural |
| --- | --- |
| `arama_metni` | `hastalik` + `alt_tur`, küçük harf, Türkçe `İ→i`, `I→ı`, aksan katlama |
| `baslik` | `hastalik` başındaki `V- ` / `VI- A. ` gibi numaralandırma ayrılır; ekranda rozet olarak gösterilir |
| `hastalik_ayrac` | 64 kayıtta `hastalik` alanı `«grup başlığı — alt madde»` biçimindedir; `—` solundaki kısım hastalık adı, sağındaki kısım **seviye etiketi**dir |
| `seviye_etiketi` | öncelik: `alt_tur` başındaki `1-`/`a-`/`2.` → yoksa `hastalik_ayrac` sağ tarafı → yoksa "tek oran" |
| `grup_anahtari` | `bolum` + (`grup` varsa `grup`) + `hastalik_ayrac` sol tarafı |

### 3.4 Korunması zorunlu değişmezler

Yükleme anında doğrulanır; biri bozulursa uygulama **açılmaz**, hata verir:

- `kayitlar` = 276, `belirsiz` (durum=belirsiz) = 10, toplam = 286
- bölüm dağılımı: Z 56 / D 142 / H 78
- tüm `oran` değerleri tam sayı ve 0 ≤ `oran` ≤ 100
- `(hastalik, alt_tur)` çifti **tekil** (bugün 0 çakışma)
- her kayıtta `id`, `bolum`, `hastalik`, `oran`, `sayfa` dolu
- katalogda `X-` kimliği **yok**; 11 çözülen kayıt `Z-055/Z-056`, `D-139…D-142`,
  `H-074…H-078` kimlikleriyle **bir kez** bulunur
- `id` numaraları bölüm içinde **kesintisizdir** (Z-001…Z-056, D-001…D-142,
  H-001…H-078). İlk dağıtımda (Z-001…Z-054, D-001…D-138, H-001…H-073) numaralar resmî
  sayfa sırasını izler; sonradan eklenen 11 kayıt mevcut kimlikler yeniden
  numaralandırılmadan **bölüm sonuna** eklenmiştir (`meta.id_kurali`). Bu nedenle eklenen
  blokta sayfa sırası bölümün tamamı için geçerli değildir. Belirsiz satırlar bu dosyada
  yer almaz; `veri/belirsiz.json` içinde `X-Z##`/`X-D##`/`X-H##` kimlikleriyle **ayrı dizide**
  tutulur.

#### 3.4.1 Katalog kaydı sayılmayanlar

Bunlar katalogda kayıt değildir; hesap motoruna oran olarak girmez:

1. **Bölüm ve alt başlıklar** (ör. "VI- Yaygın gelişimsel bozukluklar", "X- İmmun,
   otoimmun ve sistemik hastalıkların deri bulguları", "VI-A Benign neoplazm ve
   hiperplaziler"). Yalnız gruplama/arama için kullanılır.
2. **TABLO 1 — Hastalık şiddeti değerlendirme tablosu (s.16).** Hafif/orta/şiddetli/çok
   şiddetli tanımları oran değil **kriter** metnidir; arayüzde şiddet seçiminin yardım
   metni olarak kullanılmalıdır.
3. **Tek başına ölçüm aralıkları** (IQ bantları, Hb eşikleri, faktör aktivitesi, kaplanan
   vücut yüzeyi). Bunlar aynı kaydın `alt_tur` metnidir, ayrı seçenek değildir.
4. **Ekleme kuralları.** DERİ'de iki "ayrıca … 15" satırı ve pigment bozukluklarındaki
   "ayrıca %5" NOT'u bağımsız oran değildir; `veri/belirsiz.json` içinde `ekleme_kurali` olarak
   ayrı tutuldu, Balthazard zincirine sokulmaması gerekir.
5. **NOT'lar.** Remisyon (s.14), vergi indirimi + yıllık değerlendirme (s.15), iktiyozis
   grup bütünü (s.20), ektodermal displazi grup bütünü (s.21), nakilde rapor süresi (s.26)
   ve otizm dipnotu (s.13) ilgili kayıtlara kısıt kodu veya `kaynak_not` olarak bağlandı.
6. **s.16 giriş hükümleri.** Deri tümörleri ve eritroderma dışında, deri hastalığına eşlik
   eden hastalık/komplikasyonların ayrıca değerlendirilmesi kuralı oran değildir.

### 3.5 Ekran akışı

```
[1] Bölüm seçimi / arama
        │
        ├── arama metni ──► sonuç listesi (bölüm ön filtresi uygulanır)
        │
        └── bölüm seçildi
                │
          [2] Grup / başlık seçimi     (DERİ: 15 grup; Z: 6, H: 10 başlık)
                │
          [3] Hastalık seçimi          (78 hastalık adı; arama burada da çalışır)
                │
          [4] Seviye seçimi            ← tek kayıtlı grupta ATLANIR
                │
          [5] Sonuç: oran + kaynak + kısıt uyarıları
                │
          [6] 65 yaş bilgi bloğu       ← ayrı blok, oranı DEĞİŞTİRMEZ (§3.14)
                │
          [7] "Hesaplamaya ekle" ──► Araç-2 (yalnız id + oran + kısa etiket)
```

### 3.6 Hastalık arama

- Arar: `hastalik` + `alt_tur` (türetilmiş `arama_metni`); 3 karakterden sonra çalışır.
- Türkçe duyarsız: `psoriazis` ≈ `psoriasis`, `işitme`/`isitme` eşleşir.
- Numaralandırma aramayı engellemez: `VI` veya `A` yazınca başlık rozetleri de taranır.
- Sonuç satırında: hastalık adı, seviye etiketi, oran, bölüm rozeti.
- **Boş sonuç ≠ hata.** §3.10/§4.8'deki belirsiz/veri yok durumları ayrı mesajla gösterilir.

### 3.7 Bölüm / grup ve seviye seçimi

| Düzey | Z ve H | DERİ |
| --- | --- | --- |
| 1 | Bölüm (3 seçenek) | Bölüm |
| 2 | Roma başlığı (I…VI / I…X) | `grup` (15) |
| 3 | Hastalık | Hastalık |
| 4 | Seviye | Seviye |

Z ve H'de `grup` alanı yok — bu bir eksik değil, kaynakta o düzeyin bulunmamasıdır.

### 3.8 Tek kayıtlı gruplarda seviye adımı atlanır

**9** hastalık grubu tek kayıtlıdır; sayı 28.10.2026'da 276 kayıt üzerinden yeniden
hesaplanmış ve **ürün kararıyla kabul edilmiştir (O-2)**: D-013, D-014, D-017, D-049,
D-062, D-075, D-086, D-134, H-056. (Z bölümünde tek kayıtlı grup yoktur.)

Eski belgelerdeki **"12"** rakamı güncel veriyle yeniden üretilemediği için **tarihsel
not** olarak yalnız burada anılır; hiçbir kural, test veya ekran metni bu sayıya dayanmaz.

Bu gruplarda **[4] adımı hiç gösterilmez**; hastalık seçilince doğrudan [5] sonuç ekranı
açılır. Kullanıcıya "tek seviye" ibaresi gösterilir, seçim yaptırılmaz.

Ölçüt: `bolum` + (`grup` varsa `grup`) + `hastalik` ayracının **sol** tarafı aynı olan
hastalık grubunda tek kayıt.

### 3.9 Seviyesi olmayan kayıtlar (`—`)

6 kayıtta `alt_tur` yerine `—` vardır: D-013, D-014, D-017, D-062, H-056, H-065.
Bunlar **iki farklı durumdur**:

**(a) Tek kayıtlı grupta `—` — 5 kayıt** (D-013, D-014, D-017, D-062, H-056)

- Seviye adımı zaten yok; doğrudan sonuç.
- Not: "Bu hastalıkta kaynak tek oran veriyor, şiddet basamağı yok."

**(b) Çok kayıtlı grupta `—` — 1 kayıt** (H-065)

H-065, `VIII- Kronik nötropeniler` grubunun 3 kaydından biridir ve seviyesi `alt_tur`'da
değil, `hastalik` metnindedir: `VIII- Kronik nötropeniler — 1- Ağır (Kostmann sendromu)`.
Bu grupta seviye listesi şöyle kurulur:

| Kayıt | Seviye etiketi (kaynak) |
| --- | --- |
| H-065 | `1- Ağır (Kostmann sendromu)` ← `hastalik` ayracının sağı |
| H-066 | `Sık ve ağır enfeksiyon geçirmesine neden olmayan vakalar` ← `alt_tur` |
| H-067 | `Sık ve ağır enfeksiyon geçirmesine neden olan vakalar` ← `alt_tur` |

**Genel kural:** `—` **hiçbir koşulda ekranda gösterilmez**. Seviye etiketi üç kaynaktan
sırayla alınır: `alt_tur` → `hastalik` ayracının sağı → "tek oran". Hiçbiri yoksa seviye
adımı atlanır. Veri **değiştirilmez**; ekran `—` değerini yutar, seviye yokmuş gibi
davranmaz — varsa etiketi başka yerden bulur.

### 3.10 Belirsiz kayıtlar (10)

Araç-1 yalnız `durum: "belirsiz"` olan **10 satırı** kapsama alır:

| # | Bölüm | Satır | Oran | Sayfa | Sorun |
| --- | --- | --- | --- | --- | --- |
| X-Z03 | Z | III-c) kısmen düzelen | 40 | 14 | III-b (20) ↔ III-c (40) seçim kuralı yok (A-5) |
| X-Z04 | Z | III-c) düzelmeyen | 70 | 14 | aynı (A-5) |
| X-D01 | D | saçlı deri/yüz >yarısı (kan damarları) | 15 | 18 | "ayrıca"nın yöntemi yok: ek mi, yerine mi (A-3) |
| X-D02 | D | saçlı deri/yüz >yarısı (skar-keloid) | 15 | 18 | aynı + bozuk ifade (A-3) |
| X-D03 | D | pigment %20-50 | 5 | 19 | NOT (a) +%5 yöntemi ve NOT (b) kapsamı (A-1, A-2) |
| X-D04 | D | pigment %50-100 | 10 | 19 | aynı (A-1, A-2) |
| X-D05 | D | pigment — albinizm | 20 | 19 | aynı; albinizme uygulanıp uygulanmadığı (A-1, A-2) |
| X-D06 | D | eritroderma | 40 | 19 | primer hastalıkla birlikte kullanım (`R-PRIMER` kodu yok) |
| X-H02 | H | Fanconi — transfüzyonsuz | 40 | 23 | 4. maddenin 1-3 ile hiyerarşisi (A-4) |
| X-H03 | H | Fanconi — transfüzyonlu | 80 | 23 | aynı (A-4) |

Bu kayıtlar sonuç listesinde **oran olarak sunulmaz**, ama kullanıcı boş sonuçla
bırakılmaz. Eşleşmede şu mesaj gösterilir:

> "Kaynakta bu hastalık için tek bir oran belirlenmemiştir. Bu nedenle burada oran
> hesaplanamaz; değerlendirme için ilgili uzman hekime başvurulmalıdır."

Kaynak notu (EK-2 s.`<sayfa>`): bu satır birden fazla klinik durumu tek orana bağlıyor ya
da bir ekleme kuralına tabi.

- `X-*` kayıtlarında `oran` alanı **gösterilmez** (teknik olarak dolu olsa bile).
- **`durum: cozuldu` satırlar arama sonucu değildir**; kataloğa aktarılan karşılıkları
  (Z-055, Z-056, D-139…D-142, H-074…H-078) normal kayıt olarak döner.
- Kullanıcıya "bulunamadı" denmez; kaynağın sınırlaması açıklanır.
- Mesaj teşhis veya kesin tıbbi yönlendirme içermez.
- Kesinleştirme, tahmin veya birleştirme **yapılmaz**.

**Çözülüp kesin kataloğa aktarılan 11 satır** (izlenebilirlik; `veri/belirsiz.json` satırları
silinmedi, `durum: cozuldu` + `cozum_tarihi` + `kaynak_sayfa` ile işaretlendi):

| Belirsiz satır | Yeni katalog kimliği | Sayfa | Oran |
| --- | --- | --- | --- |
| X-Z01 | Z-055 | 13 | 80 |
| X-Z02 | Z-056 | 14 | 0 |
| X-D07 | D-140 | 19 | 10 |
| X-D08 | D-139 | 18 | 80 |
| X-D09 | D-141 | 21 | 40 |
| X-D10 | D-142 | 21 | 60 |
| X-H01 | H-074 | 23 | 70 |
| X-H04 | H-075 | 23 | 80 |
| X-H05 | H-076 | 24 | 80 |
| X-H06 | H-077 | 25 | 60 |
| X-H07 | H-078 | 25 | 80 |

Katalogda **11'i tekrar eklenmez**.

### 3.11 Kısıtlar

`kisit` bir **liste**dir; her kod sonuç ekranında ayrı uyarı satırına dönüşür.
Kısıt **oranı değiştirmez**, kullanımını sınırlar.

| Kod | Ekranda gösterilecek metin | Kapsam (bugün) |
| --- | --- | --- |
| `R-YILLIK` | Talep hâlinde yıllık kontrolle yeniden değerlendirilir. | 142 (tüm DERİ) |
| `R-GECICI` | Geçici fonksiyon kaybı; 1 yıl sonra kesin karar. | 34 |
| `R-VERGI` | İş başvurusu ve vergi indiriminde bu derecelendirme dikkate alınmaz. | 34 |
| `R-REMISYON` | Remisyonda ise oran verilmez. | 4 |
| `R-NAKIL` | Aktivasyon/gerileme ihtimali varsa rapor geçerlilik süresi belirtilir. | 6 |
| `R-IKTIYOZ` | Alt tip ayrılmaz; şiddet grup bütünü için belirlenir. | 4 |
| `R-EKTO` | Alt tip ayrılmaz; şiddet grup bütünü için belirlenir. | 4 |

Toplam **228** kısıt kaydı; **182** kayıt en az bir kısıt taşır, **94** kayıt kısıtsızdır
(276 kayıt üzerinden, 28.10.2026).

`R-VERGI` ve `R-REMISYON` **sonucu doğrudan etkiler** (oran kullanılamaz / verilmez);
bu ikisi diğerlerinden görsel olarak ayrılmalı (kırmızı, sonuç bloğunun içinde).

### 3.12 Hematoloji bölüm notu — kayıt kısıtı değil

Yalnız **Hematoloji** bölümü seçildiğinde, sonuç alanının altında, kayıt kısıtlarından
görsel olarak ayrı (nötr/gri) bir **bölüm notu** gösterilir. Kaynağın ifadesi birebir:

> **Bölüm notu (kaynak s.26):** "Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali
> olan hastalarda raporun geçerlilik süresi belirtilmelidir."

Kurallar:

- 78 hematoloji kaydının tamamına uygulanmış bir kısıt gibi **gösterilmez**.
- "Bölüm notu" etiketi taşır; `R-*` kodu ile karışmaz, kısıt sayısına eklenmez.
- Kaynağın anlamı daraltılmaz: "sadece nakil hastaları için" ifadesi **eklenmez**.
- 6 nakil kaydında (H-068…H-073) ayrıca `R-NAKIL` kayıt kısıtı görünür; ikisi çelişmez,
  aynı anda gösterilir.

### 3.13 Sonuç ve Araç-2'ye aktarım

Sonuç ekranı şunları taşır: hastalık adı, seviye, **oran**, kaynak (EK-2 s.`<sayfa>`),
kısıtlar.

- **"Hesaplamaya ekle"** → Araç-2'ye yalnız `{id, oran, kisa_etiket}` aktarılır.
- Araç-2 bu etiketi yalnız liste başlığı olarak gösterir; **hastalık bilgisi taşımaz,
  kısıt denetlemez**. Arayüz bunu açıkça yazar:

> "Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım
> kısıtları burada denetlenmez."

- Aynı kayıt iki kez eklenirse uyarı verilir (çift sayım riski), engellenmez.
- %10 yaş eki **otomatik aktarılmaz**; kullanıcı yaşı Araç-2'de kendisi işaretler.

### 3.14 65 yaş kuralı — Araç-1'de gösterim (O-1, kapandı)

**Karar:** Araç-1 **EK-2 temel oranını yaş eklemesi olmadan** gösterir ve **otomatik yaş
hesabı yapmaz**. 65 yaş ve üzeri için %10 ek oran kuralı **ayrı ve nötr bir bilgi
bloğunda** açıklanır. Gösterilen oran, "EK-2'de bu hastalık ve seviye için tanımlı
oran"dır. 65 yaş eklemesi yalnız **Araç-2'de** (bileşke üzerinden) uygulanır.

Gerekçe: Araç-1 tek bileşen gösterir; bileşene yaş eki eklemek "nihai oran" izlenimi
verir ve §1'deki "çalışma gücü kaybı oranı değildir" ilkesini zedeler.

Sonuç ekranında, oranın **altında**, orandan görsel olarak ayrılmış nötr bilgi bloğu
(gri/bilgi ikonu, kırmızı değil) gösterilir:

> **65 yaş ve üzeri için ek oran**
> Mevzuata göre 65 yaş ve üzerindeki bireylerin engellilik oranına Balthazard formülü ile
> **%10** eklenir. Bu ek, yukarıdaki orana düz toplama ile eklenmez; Araç-2'de diğer
> oranlarla birlikte Balthazard yöntemiyle hesaplanır.
> Örnek: %40 → %46.

Kurallar:

- Blok **her sonuçta** görünür (yaş sorulmaz, varsayım yapılmaz); "65 yaş ve
  üzerindeyseniz" koşuluyla çerçevelenir.
- Blok **oranı değiştirmez**; "nihai oranınız" hesabı yapılmaz.
- %10 **otomatik aktarılmaz**; "Hesaplamaya ekle" yalnız katalog oranını taşır.
- Araç-1 motoru **`yas_ekle = false`** gönderir; sonuç EK-2 temel oranıdır. Böylece tek
  hesap kodu korunur, Araç-1 kendi hesabını yapmaz.
- Kaynak künyesi bu blokta verilir: 20.02.2019 tarihli ve 30692 sayılı Resmî Gazete'de
  yayımlanan *Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik* (m. 10/4).
  **Künye çelişkisi** (JSON `meta` 31275 diyor) §7.2/O-3'te açıktır.

### 3.15 Durum matrisi

| Durum | Adet | Gösterim |
| --- | --- | --- |
| Çok kayıtlı grupta normal kayıt | 266 | seviye listesi + oran |
| Çok kayıtlı grupta `alt_tur = "—"` (H-065) | 1 | seviye etiketi `hastalik` ayracından gelir |
| Tek kayıtlı grup | 9 | seviye adımı yok, doğrudan oran; 5'inde "şiddet basamağı yok" notu |
| **Kesin toplam** | **276** | |
| Kısıtlı kayıt (üsttekiyle kesişir) | 182 | oran + kısıt uyarıları |
| Belirsiz kayıt (`durum: belirsiz`) | 10 | oran gösterilmez, belirsiz kayıt mesajı (§3.10) |
| Çözülmüş iz (`durum: cozuldu`) | 11 | **arama sonucu değil**; kataloğa aktarılmış karşılığı döner |
| Kapsam dışı bölüm | — | "bu bölüm henüz eklenmedi" (oran uydurulmaz) |
| 65 yaş bilgi bloğu | 276 sonucun tamamı | ayrı blok, oranı değiştirmez (§3.14) |

Toplam satır kontrolü: 266 + 1 + 9 = **276** kesin; 276 + 10 belirsiz = **286** kaynak
satırı.

### 3.16 Terminoloji (arayüz metinleri)

| Kavram | Doğru kullanım | Yasak |
| --- | --- | --- |
| Katalog `oran` | "EK-2'de bu hastalık ve seviye için tanımlı oran" | "çalışma gücü kaybı oranı" |
| Balthazard sonucu | "oranların bileşkesi" | "kesin engellilik oranınız" |
| Çalışma gücü kaybı | ayrı bir değerlendirme; bu araçların konusu değil | eşanlamlı kullanım |

Her iki aracın altında kalıcı not:

> Bu araçlar bilgilendirme amaçlıdır; resmî engelli sağlık kurulu raporu yerine geçmez.
> Oranlar EK-2 kılavuzundan alınmıştır. Çalışma gücü kaybı değerlendirmesi ayrı bir
> hukuki süreçtir ve bu oranlarla eşitlenemez.

### 3.17 Kabul kriterleri (Araç-1)

1. **276** kesin kaydın tamamı arama ile bulunabilir; hiçbiri ulaşılamaz değil.
2. Aynı `(hastalik, alt_tur)` iki farklı oran döndürmez.
3. **9** tek kayıtlı grupta seviye adımı görünmez.
4. 6 `—` kaydında ekranda `—` karakteri **hiç** görünmez; H-065'in seviye etiketi
   `hastalik` ayracından (`1- Ağır (Kostmann sendromu)`) gelir.
5. **10** belirsiz kayıtta oran gösterilmez, uyarı gösterilir; **11** `cozuldu` satırı
   arama sonucu olarak dönmez, katalog karşılığı döner.
6. `R-VERGI` bulunan **34** kayıtta sonuç "vergi indiriminde kullanılamaz" uyarısıyla
   gelir.
7. Araç-2, kısıt denetlemediğini her zaman yazar.
8. Katalog dosyaları uygulama çalışırken değişmez (mtime sabit kalır).
9. Hiçbir ekranda "çalışma gücü kaybı oranı" ibaresi geçmez.
10. Araç-1 sonucunda **65 yaş bilgi bloğu** görünür ve gösterilen oran **yaş eklenmemiş**
    EK-2 oranıdır; "nihai oran" ifadesi geçmez.
11. Araç-2'de yaş seçimi yapılmadan hesaplama **etkinleşmez**; hiçbir yaş seçeneği
    varsayılan işaretli değildir.
12. Katalog dosyalarının MD5 değerleri `B77AEF76A1310DE4AE93E703183E2A09` ve
    `89AE83AAFFF9D6541B75D4073FC1BE82` ile aynı kalır.

---

## 4. Araç-1 — ekran sözleşmesi

### 4.1 Yerleşim

- İki araç **ayrı sekmelerdir**: "Engel Oranı Bul" ve "Balthazard Hesapla".
  Uygulama notu (S-2a): iki prototip **ayrı sunucu ve portta** çalışır (Araç-1
  `127.0.0.1:8766`, Araç-2 `127.0.0.1:8765`); her ekranın üstünde diğer araca
  bağlantı bulunur. İki uygulama birbirine bağımlı değildir (§4.12).
- Araç-1 tek sayfadır: arama + bölüm çipleri (Tümü / Ruh Sağlığı / Deri / Hematoloji)
  üstte, sonuç alanı altta; modal/açılır pencere yok.
- Her ekranda kalıcı alt bilgi vardır (§3.16).
- Mobil: tek sütun, çipler yatay kaydırılır, sonuç kartı tam genişlik.

### 4.2 Arama ve boş durum

- Arama 3 karakterden sonra çalışır; Türkçe duyarsızdır; hastalık adı + seviye metni +
  başlık rozetleri taranır.
- Sonuç satırı: hastalık adı, seviye etiketi, oran, bölüm/grup rozeti.
- Satıra tıklamak seviye adımını atlar, doğrudan sonuca gider.
- Sonuç yoksa §4.8; belirsiz kayıtla eşleşme varsa §4.7 gösterilir.
- Bölüm seçilince: sol sütun bölüm → grup/başlık; sağ sütun hastalık → seviyeler + oranlar.
  Tek kayıtlı grupta seviye listesi çizilmez.

### 4.3 Sonuç ekranı

- Tek ve büyük **oran**; yanında "EK-2'de bu hastalık ve seviye için tanımlı oran" etiketi.
- Altında kaynak satırı: "Kaynak: EK-2, sayfa `<n>` · kayıt `<id>`".
- Kısıtlar ayrı blokta: "Bu oran için geçerli kurallar (`n`)".
- Butonlar: "Bu oranı hesaplamaya ekle" ve "Yeni arama".
- **Oran 0 durumu** (ör. Z-022): kutu `0` gösterir, açıklama "Bu basamakta kaynak 0 oran
  veriyor"; kısıtlar normal gösterilir.
- Kısıt **oran kutusunun içinde değil, altında** gösterilir.
- Sonuç yuvarlak "skor" gibi sunulmaz; "nihai oran" izlenimi verilmez.

### 4.4 Kısıt gösterimi

Renk **tek başına anlam taşımaz**. Her kısıt üç katmanla gösterilir: (1) **tür etiketi**
(kelimeyle), (2) **ikon** (şekiller farklı), (3) **açıklama metni**. Renk destekleyici
ipucudur.

| Kod | Tür etiketi | Önem | İkon + renk | Açıklama metni |
| --- | --- | --- | --- | --- |
| `R-VERGI` | KULLANIM SINIRI | **Dikkat** | ⛔ kırmızı | "İş başvurusu ve vergi indiriminde bu derecelendirme dikkate alınmaz." |
| `R-REMISYON` | ORAN VERİLMEZ | **Dikkat** | ⛔ kırmızı | "Remisyonda ise oran verilmez." |
| `R-GECICI` | GEÇİCİ DEĞERLENDİRME | Orta | ⚠ amber | "Geçici fonksiyon kaybı; 1 yıl sonra değerlendirilip kesin karara varılır." |
| `R-NAKIL` | GEÇERLİLİK SÜRESİ | Orta | ⚠ amber | "Aktivasyon/gerileme ihtimali varsa rapor geçerlilik süresi belirtilir." |
| `R-YILLIK` | YENİDEN DEĞERLENDİRME | Bilgi | ℹ nötr | "Talep hâlinde yıllık kontrolle yeniden değerlendirilir." |
| `R-IKTIYOZ` | DEĞERLENDİRME YÖNTEMİ | Bilgi | ℹ nötr | "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir." |
| `R-EKTO` | DEĞERLENDİRME YÖNTEMİ | Bilgi | ℹ nötr | "Alt tip ayrılmaz; şiddet grup bütünü için belirlenir." |

Kırmızı **yalnız** sonucun kullanılabilirliğini ortadan kaldıran `R-VERGI` ve
`R-REMISYON` için kullanılır; diğerleri amber veya nötrdür.

### 4.5 65 yaş bilgi bloğu

- Oran kutusunun ve kısıtların **altında**, "Hesaplamaya ekle" butonundan önce.
- **Nötr** (gri/bilgi); kırmızı/amber değil; kısıt değildir, kısıt sayısına eklenmez.
- **Yukarıdaki oran değişmez**; %46 yalnız örnek cümlesinde geçer.
- "Nihai oran", "yaş dahil oran" gibi başlık kullanılmaz.
- %10 otomatik aktarılmaz; kullanıcının yaşı sorulmaz, koşullu cümle kullanılır.

Metin ve kurallar için §3.14.

### 4.6 Hematoloji bölüm notu

- Yalnız Hematoloji bölümünde, sonuç alanının en altında, kısıtlardan görsel olarak ayrı.
- Gri/nötr kutu; `⚠`/`⛔` kullanılmaz; kısıt sayısına eklenmez, `R-*` kodu gösterilmez.
- Metin birebir §3.12'deki gibidir; daraltıcı ifade eklenmez.
- Nakil kaydı seçildiğinde `R-NAKIL` kısıtı ile birlikte görünür.

### 4.7 Belirsiz kayıt ekranı

- `durum: "belirsiz"` olan **10 satır** için; **oran kutusu hiç çizilmez**, "Hesaplamaya
  ekle" **görünmez**, kaydın oranı (`5` gibi) veri olarak dolu olsa da **gösterilmez**.
- Mesaj §3.10'daki gibidir; "bulunamadı" denmez.
- Kaynak notu satırı kaynağın sınırlamasını açıklar.
- `sorun_tipi` kullanıcıya teknik kod olarak gösterilmez; tek cümleye çevrilir:

| `sorun_tipi` | Kullanıcıya gösterilen cümle |
| --- | --- |
| `coklu_kosul_tek_oran` | "Bu satır birden fazla klinik durumu tek orana bağlıyor." |
| `ekleme_kurali` | "Bu satır bağımsız oran değil, başka oranlara eklenen bir kural." |
| `olcum_iki_kriter` | "Oran iki ölçütün birlikte sağlanmasına bağlı." |
| `hiyerarsi_belirsiz` | "Alt koşulların üst basamakların yerine mi geçtiği belirsiz." |
| `harf_tekrari` | "Kaynakta madde numarası tekrar ediyor." |
| `kombinasyon_kisiti` | "Bu oran başka bir hastalıkla birlikte kullanılamaz." |
| `numaralandirma_atlamasi` | "Kaynakta madde numarası atlıyor." |

- `durum: "cozuldu"` satırları (11) bu ekrana düşmez.

### 4.8 Boş sonuç / kapsam dışı

- "… için sonuç bulunamadı" + "Yazımı kontrol edin veya bölüm seçerek ilerleyin." +
  "Göz, işitme, konuşma ve kas-iskelet bölümleri bu araçta henüz yok."
- Kapsam dışı bölüm seçilirse "Bu bölüm henüz eklenmedi" — **oran uydurulmaz**.
- Belirsiz kayıtla eşleşme varsa boş sonuç yerine §4.7 gösterilir.

### 4.9 Araç-2'ye geçiş

- "Hesaplamaya eklendi: %`<oran>` — `<kısa etiket>`" bildirimi.
- "Eklenen oranlar (`n`)" listesi; her satırda oran + etiket + kaldır.
- Butonlar: "Balthazard ile hesapla →" ve "Alışverişe devam".
- Araç-2'ye yalnız **sayı + kısa etiket** geçer; hastalık bilgisi taşınmaz.
- Aynı kayıt ikinci kez eklenirse uyarı: "Bu kayıt zaten listede." (engellenmez)

**Uygulama notu (S-1a, 29.10.2026):** Bu turda liste **yalnız Araç-1'de** (tarayıcı
oturumunda) tutulur; Araç-2'ye **otomatik aktarım yapılmaz**. Kullanıcı listeyi
kopyalayıp Araç-2'ye elle girer; ekranda Araç-2'ye bağlantı verilir. Kısa etiket
`EK-2 kaydı <id> · s.<sayfa>` biçimindedir, hastalık adı taşımaz. Araç-2'nin kodu ve
davranışı bu kararla değişmemiştir; `?oranlar=` benzeri bir aktarım yeni ve onaylı bir
adım gerektirir.

### 4.10 Metin sözlüğü ve yasak ibareler

| Yer | Metin |
| --- | --- |
| Oran etiketi | "EK-2'de bu hastalık ve seviye için tanımlı oran" |
| Kısıt başlığı | "Bu oran için geçerli kurallar" |
| Kısıt tür etiketleri | KULLANIM SINIRI · ORAN VERİLMEZ · GEÇİCİ DEĞERLENDİRME · GEÇERLİLİK SÜRESİ · YENİDEN DEĞERLENDİRME · DEĞERLENDİRME YÖNTEMİ |
| Önem etiketleri | "Dikkat" · "Orta" · "Bilgi" |
| Bölüm notu başlığı | "Bölüm notu (kaynak s.26)" |
| Belirsiz mesajı | §3.10'daki metin |
| Alt bilgi (her ekran) | "Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık kurulu raporu yerine geçmez." |
| Araç-2 uyarısı | "Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım kuralları burada denetlenmez." |

**Yasak ibareler** (hiçbir ekranda geçmez): "çalışma gücü kaybı oranı", "kesin engellilik
oranınız", "maluliyet oranı", "resmî raporunuz" / "bu sonuç rapor yerine geçer".

### 4.11 Referans görsellerden alınanlar / alınmayanlar

İki ekran görüntüsü (Engelliler.biz kaynaklı) **yalnız tasarım ve kullanım kolaylığı**
referansıdır; birebir kopyalanmadı, oradaki metin/oranlar doğru kabul edilmedi.

**Alınanlar:** tek ekranda arama + sonuç; 3 bölüm çipi + "Tümü"; "Eklenen oranlar" listesi
(oran toplamı gösterilmez); boş durum metni; kalıcı alt bilgi.

**Alınmayanlar:** anatomi figürü (3 bölüm için gereksiz, erişilebilirlik yükü); boşken
`%0` gösteren halka ("oran var" izlenimi); dev gradyan başlık bandı; 19 kategori çipi;
oranı yuvarlak "skor" gibi sunma ("nihai oran" izlenimi).

### 4.12 Uygulama notu — Araç-1 prototipi (29.10.2026)

Bu bölüm **teknik uygulama** bilgisidir; hukuki/veri kararı içermez ve §7.3'teki açık
maddeleri (B-4, B-5, B-8, O-3, A-1…A-6) kapatmaz.

| Bileşen | Dosya | Görev |
| --- | --- | --- |
| Yükleyici | `katalog_okuyucu.py` | Salt okunur okuma, §3.4 değişmez denetimi, §3.3 türetilmiş alanlar |
| Sunucu | `arac1/arac1_sunucu.py` | stdlib `http.server`, `127.0.0.1:8766`, yalnız `GET` |
| Ekran | `arac1/arac1.html` | Arama, bölüm çipleri, gezinme, sonuç, eklenen oranlar |

Uçlar: `/arac1` (ekran), `/saglik`, `/api/bolumler`, `/api/gezinme?bolum=…`,
`/api/ara?metin=&bolum=`, `/api/kayit/<id>`, `/api/belirsiz/<id>`. `POST` → `405`
(Araç-1 hesap yapmaz, yazmaz).

Bağlı uygulama kuralları:

- Her oran motordan `balthazard({"oranlar": [oran], "yas": "65_alti", "yas_ekle": False})`
  ve `bicimle_gosterim()` ile alınır; Araç-1'de kopya formül yoktur (§2, O-1).
- `—` değeri ekranda hiç görünmez: seviye etiketi `alt_tur` → `hastalik` ayracının sağı →
  "tek oran" sırasıyla türetilir (§3.9).
- Belirsiz kayıt yanıtında `oran`, kısıt ve "hesaplamaya ekle" alanı **hiç üretilmez**;
  `durum: cozuldu` satırları `404` döner (§3.10).
- Kısıtlar §4.4 tablosundaki tür/önem/ikon/açıklama ile birebir taşınır; 65 yaş bloğu ve
  hematoloji bölüm notu ayrı nötr bloklardır, oranı değiştirmez, kısıt sayılmaz.
- Katalog dosyaları çalışma sırasında **değişmez**; testler `mtime`/boyut sabitliğini
  doğrular (§3.17/8).
- Araç-2'ye otomatik aktarım yoktur (S-1a); iki uygulama ayrı portta bağımsızdır (S-2a).

---

## 5. Araç-2 — sözleşme

### 5.1 Sınır

- Girdi: 0-100 arası **tam sayı** listesi (+ isteğe bağlı etiket) **ve yaş seçimi**
  (varsayılansız).
- Çıktı: bileşke oran, adım adım Balthazard zinciri, 65 yaş eki (tek noktada).
- Yapmaz: hastalık → oran eşlemesi, kısıt denetimi, seviye seçimi, "bu oran doğru mu"
  yorumu.
- Araç-2, Araç-1'in yerine geçmez; Araç-1'den gelen oranı **sorgulamaz**, yalnız taşır.
- Katalogla konuşmaz; katalog dosyalarını okumaz.

### 5.2 Kalıcı uyarı (her ekranda, kapatılamaz)

> ⓘ Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım
> kuralları burada denetlenmez.
>
> Hastalığa ve mevzuata özgü kısıtlar (ör. yıllık yeniden değerlendirme, vergi
> indiriminde kullanılamama, remisyonda oran verilmemesi) bu araçta doğrulanamaz. Bunlar
> için "Engel Oranı Bul" aracına bakın.

- Uyarı kapatılamaz, katlanamaz, kaydırınca kaybolmaz.
- Sonucun **hemen üstünde** kısa hâli tekrar edilir.
- Araç-1'e bağlantı metin olarak verilir; Araç-2 kendi içinde hastalık araması yapmaz.

### 5.3 Giriş / boş durum

- Alanlar: "Oran (%)" + "Etiket (isteğe bağlı)" + "[ + Ekle ]".
- **Boş durumda sonuç kutusu çizilmez**; nötr metin: "Henüz oran eklenmedi."
- "Hesapla" **pasif**; nedeni yazılı: "En az bir oran girin."
- Hastalık adı, tanı, seviye alanı **yoktur**.
- Yaş kontrolü ilk oran eklendiğinde görünür; varsayılan seçim yapılmaz.
- **Hesap canlı değildir:** sonuç yalnız "Hesapla" ile üretilir (Araç-1 canlıdır; bu
  fark bilinçlidir).

**"Nasıl hesaplanır?"** (katlanabilir, varsayılan kapalı, 4 adım):

```
1) Oranlar büyükten küçüğe sıralanır (kural; kullanıcı seçmez).
2) İlk iki oran birleştirilir:  A + (100 − A) × B / 100
3) Çıkan sonuç, sonraki oranla aynı formülle birleştirilir.
4) 65 yaş ve üzeri seçildiyse, bileşkeye %10 aynı formülle eklenir.
```

Kart eğitim amaçlıdır, sonuç üretmez; örnek olarak yalnız `%40 → %46` verilir.

### 5.4 Oran ekleme ve doğrulama

| Girdi | Davranış | Mesaj |
| --- | --- | --- |
| Boş | Ekleme yapılmaz | "Bir oran girin." |
| 0-100 dışı | Ekleme yapılmaz | "Oran 0 ile 100 arasında olmalıdır." |
| Ondalıklı (ör. 12,5) | **İlk sürümde kabul edilmez** | "Oran tam sayı olmalıdır." |
| Harf/özel karakter | Girdi maskesi engeller | — |
| 0 | Kabul edilir | "0 oranı listeye eklendi. Bileşkeyi değiştirmez." |
| 100 | Kabul edilir, **onay** | "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?" |
| Aynı değer tekrar | **Kabul edilir; engellenmez** | "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir." |
| Etiket boş | Kabul edilir | Listede "Etiketsiz oran" |

- **Tam sayı girişi ürün tercihidir, mevzuat kuralı değildir** (B-7): Yönetmelikte "tam
  sayı olmalıdır" hükmü yoktur; Ek-3 notu yalnız oranların ondalık karşılıklarından söz
  eder. Ondalık desteği ancak **yeni tarihli ürün kararıyla** açılır ve motor sözleşmesi
  sürümü artırılır.
- **Tekrar eden oran engellenmez** (B-6): her giriş hesaba katılır; uyarı bilgilendiricidir,
  onay istemez. Gerekçe: mevzuat susuyor; sessizce veri atmak yerine çift sayım riski
  yazıyla bildirilir.
- Etiket serbest metindir; hastalık adı zorunlu değildir, teşhis istemez. 60 karakter;
  listede kısaltılır, tamamı ipucunda görünür.

### 5.5 Liste

- Ekleme listenin sonuna; odak yeni satıra gider.
- Her satırda `[düzenle] [×]`; `[×]` siler ve 5 saniye "Geri al" gösterir.
- `[Tümünü sil]` onay ister: "Tüm oranlar silinecek. Emin misiniz?"
- Liste boşalırsa §5.3'e dönülür, sonuç alanı temizlenir.
- **Sıra seçimi yok:** liste giriş sırasıyla görünür, motor her zaman büyükten küçüğe
  sıralar. Ekranda yalnız bilgi satırı: "Sıralama: büyükten küçüğe (kural gereği,
  değiştirilemez)".

### 5.6 Yaş seçimi

- İki radio: "( ) 65 yaş altı   ( ) 65 yaş ve üzeri" — **varsayılan seçim yok**.
- Seçilmeden "Hesapla" pasiftir: "Yaş aralığını seçin."
- "65 yaş ve üzeri" seçilirse %10 **Balthazard formülüyle** eklenir; doğrudan 10 puan
  eklenmez. `%40 + %10 = %50` **yanlıştır**; doğru: `40 + (100 − 40) × 10 / 100 = 46`.
- Kaynak çelişkisi (Ek-3 (e) "60") kayıtlıdır; uygulama **65**'tir (B-1).
- Neden switch değil: anahtarın kapalı hâli sessiz "65 altı" kabulü olurdu.
- Değerlendirilen seçenekler: (a) Araç-2'de "65 yaş ve üzeri mi?" kontrolü — **seçildi**,
  en küçük değişiklik ve Araç-1'den gelen oranlarda da geçerli; (b) doğum yılı, eşik motor
  içinde — fazladan alan, şimdilik gerekmiyor; (c) yaş sorulmaz, ek uygulanmaz — **yanlış**,
  doğrulanmış kural sessizce atlanır.

### 5.7 Sonuç ve gösterim

- Sonuç kutusu **tek sayıdır**; "engellilik oranınız" gibi hüküm yazmaz.
- Adım dökümü **motorun döndürdüğü** veridir; arayüz hesap yapmaz; adımlar büyükten
  küçüğe gösterilir.
- "Yuvarlama: uygulanmadı (motor ham değer döndürür)." satırı motorun
  `yuvarlama.uygulandi = false` bildirimini yansıtır.
- 65 yaş eki satırı **yalnız** `yas_eklemesi.uygulandi = true` ise çizilir; arayüz yorum
  üretmez.
- **Kaynak künyesi** yalnız "65 yaş ve üzeri" seçiliyken, sonucun altında, ince ayırıcıyla
  gösterilir; uyarı değil künyedir (kırmızı/ikon yok, sakin ton). "65 altı" seçilirse
  veya liste boşalırsa gizlenir; yerine "kaynak yok" yazılmaz.
- Sonuç ve kaynak metni **aynı yaş seçiminden** türetilir ve aynı render'da yenilenir.
- Kısıt uyarısı burada yoktur; §5.2 uyarısı tekrar edilir.
- Sonuç "resmî rapor" veya "kesin sonuç" olarak adlandırılmaz.

**Kaynak metni (birebir):**

> Kaynak: Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik (Resmî Gazete 20.02.2019, sayı 30692), Ek-2 Erişkinler İçin Engelli Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu ve Ek-3 Balthazard formülü.

**Gösterim:** hesap ham değerle yapılır; gösterim ayrı katmandır (§2.7). Sonuç kutusu ve
adım dökümü en fazla 2 ondalık, yarı yukarı, Türkçe virgül; tam sayıda ondalık yok.
`sonuc.tam_sayi_mi = false` ise değer gizlenmez, 2 ondalığa gösterilir. Kopyalama/dışa
aktarma **ham değeri** taşır.

### 5.8 Araç-1'den gelen oranlar

- "Engel Oranı Bul aracından `n` oran aktarıldı" bildirimi.
- Aktarılan oran **kilitli değildir**; düzenlenebilir, silinebilir.
- Yalnız **sayı + etiket** taşınır; kayıt kimliği taşınsa bile kullanılmaz.
- Aynı kayıt ikinci kez aktarılırsa "Bu oran listede zaten var." (engellenmez).
- Etiket **prefiks** olarak gösterilir, tıklanabilir bağlantı değildir.
- Not: "Etiketler yalnız hatırlatma içindir. Bu araç hastalığı tanımaz, oranı doğrulamaz."

### 5.9 Kenar durumlar

| Durum | Davranış |
| --- | --- |
| Tek oran | Hesapla aktif; sonuç = o oran |
| Hiç oran yok | Hesapla pasif, "En az bir oran girin." |
| Yaş seçilmedi | Hesapla pasif, "Yaş aralığını seçin." |
| "65 yaş altı" + Hesapla | Sonuç eki olmadan; kaynak künyesi görünmez |
| "65 yaş ve üzeri" + Hesapla | %10 Balthazard ile eklenir; kaynak künyesi görünür |
| Sonuç görünürken yaş değişti | Sonuç ve kaynak **aynı anda** yenilenir |
| Tüm oranlar 0 | Hesapla aktif; sonuç motorun değeri; 0 girişleri bilgi uyarısı üretir, engellemez |
| 100 var | Onay istenir |
| Aynı oran iki kez | Engellenmez; bilgi uyarısı |
| Ondalıklı değer | Reddedilir: "Oran tam sayı olmalıdır." (ürün tercihi) |
| Sonuç ondalıklı | Gizlenmez; en fazla 2 ondalık, yarı yukarı, Türkçe virgül; ham değer korunur |
| Çok sayıda oran | Liste kaydırılır; yöntemde üst sınır yok |
| Sayfa yenilendi | Girdiler saklanmaz (varsayılan); kalıcılık ayrı karar |
| Araç-1 sekmesine dönüş | Liste korunur (aynı oturum) |

### 5.10 Girdi değişti ama Hesapla'ya basılmadı — "sonuç eski"

| Durum | Gösterim |
| --- | --- |
| Sonuç görünürken liste değişti | Sonuç kutusunun üstünde "⚠ Bu sonuç önceki girdilere ait. Güncellemek için 'Hesapla'ya basın." |
| Liste boşaldı | Sonuç ve kaynak metni birlikte temizlenir, §5.3'e dönülür |
| "Hesapla"ya basıldı | Uyarı kalkar; sonuç ve kaynak aynı render'da yenilenir |
| Yaş seçimi değişti | **Uyarı çıkmaz**; anında yenilenir (§5.11) |

- Eski sonuç soluklaştırılmaz/gizlenmez, ama uyarı zorunludur.
- "Sonuç geçersiz" denmez; yalnız "güncel değil" denir.

### 5.11 Aktarımda doğrulanacaklar

**Yaş seçimi (12.1):**

1. "65 altı" + Hesapla → sonuç eki olmadan; kaynak çizilmez.
2. "65 yaş ve üzeri" + Hesapla → sonuç ekli; kaynak aynı render'da çizilir.
3. Sonuç görünürken "65 altı" → "65+" → sonuç yeniden hesaplanır; kaynak aynı anda gelir.
4. "65+" → "65 altı" → sonuç eki olmadan yenilenir; kaynak aynı anda kaybolur.
5. Liste boşalır → sonuç ve kaynak birlikte temizlenir; Hesapla pasif.
6. Sonuç sayısal olarak değişmese bile (tüm oranlar 0) kaynak seçime uyar.
7. Hızlı ardışık değişimde son görünen durum tutarlıdır; ara durum kalmaz.

**Gösterim (12.3):**

| # | Kontrol | Beklenen |
| --- | --- | --- |
| 1 | Sonuç biçimi | `55.11 → 55,11` · `62.2 → 62,2` · `59.599 → 59,6` · `69.9237 → 69,92` |
| 2 | Tam sayı | `40 → 40` (ondalık/virgül yok) |
| 3 | Yön | `55.115 → 55,12` (yarı yukarı) |
| 4 | Sayı | Tek kez: ham bileşke → yaş eki → gösterim |
| 5 | Ham değer | `sonuc.deger` ve `adimlar[]` değişmemiş |
| 6 | Kopyala | Ham değer (`59.599`), metin (`59,6`) değil |
| 7 | Biçimlendirme yeri | Yalnız `bicimle_gosterim()`; `round()`, `toFixed`, `f"{…:.2f}"` yok |

### 5.12 Metin sözlüğü ve yasak ibareler

| Yer | Metin |
| --- | --- |
| Kalıcı uyarı | "Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım kuralları burada denetlenmez." |
| Kısıt sınırı | "Hastalığa ve mevzuata özgü kısıtlar bu araçta doğrulanamaz. Bunlar için 'Engel Oranı Bul' aracına bakın." |
| Sonuç etiketi | "Bileşke oran" |
| Sonuç altı not | "Bu sonuç yalnızca girdiğiniz oranların bileşkesidir. Hastalık kısıtları denetlenmemiştir." |
| Alt bilgi | "Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık kurulu raporu yerine geçmez." |
| Aktarım notu | "Etiketler yalnız hatırlatma içindir. Bu araç hastalığı tanımaz, oranı doğrulamaz." |
| Yaş seçenekleri | "( ) 65 yaş altı   ( ) 65 yaş ve üzeri" — varsayılan yok |
| Hesapla pasif | "En az bir oran girin." · "Yaş aralığını seçin." |
| Oran doğrulama | "Bir oran girin." · "Oran 0 ile 100 arasında olmalıdır." |
| Ondalık reddi | "Oran tam sayı olmalıdır." (ürün tercihi) |
| Tekrar uyarısı | "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir." |
| 0 bilgisi | "0 oranı listeye eklendi. Bileşkeyi değiştirmez." |
| 100 onayı | "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?" |
| Yuvarlama satırı | "Yuvarlama: uygulanmadı (motor ham değer döndürür)." |
| Gösterim | Ek metin yok; "yaklaşık", "~", "en yakın tam sayı" yazılmaz |

**Yasak ibareler:** "çalışma gücü kaybı oranı" / "çalışma gücü kaybınız", "kesin
engellilik oranınız" / "engellilik oranınız hesaplandı", "maluliyet oranı", "resmî
raporunuz" / "bu sonuç rapor yerine geçer", sonucu teşhis veya hukuki hüküm gibi sunan
ifadeler.

### 5.13 Referans görselden alınanlar / alınmayanlar

Görsel (Engelliler.biz kaynaklı Balthazard ekranı) yalnız tasarım referansıdır; birebir
kopyalanmadı.

**Alınanlar:** tek ekranda giriş + sonuç; "+ Oran ekle" ile çoğaltma; formülün
gösterilmesi ("Hesaplama adımları" + "Nasıl hesaplanır?"); kısa yönlendirme metinleri;
yaş seçiliyken sonuç altında kaynak künyesi.

**Alınmayanlar:** kaydırıcı (slider) — hassas giriş ve erişilebilirlik; boşken `%0`
halkası — hesapsız sonuç izlenimi; "65 yaş ve üzeri" switch'i — sessiz "65 altı" kabulü;
dev gradyan başlık/rozet şeridi; görseldeki örnek oranların birebir aktarılması.

---

## 6. Resmî kaynak karşılaştırması

Durum kodları: **DOĞRULANDI** = metinde açık hüküm var · **DOĞRULANAMADI** = kaynakta
hüküm yok, tahmin yürütülmedi · **KAPANDI** = tarihli ürün kararıyla bağlandı.

| # | Soru | Durum | Doğrulanmış kural / karar | Dayanak |
| --- | --- | --- | --- | --- |
| 1 | Birleştirme sırası | **DOĞRULANDI** | "Bu oranlar **en yükseğinden başlanarak** sıraya konulur." Ek-3: "Her işlem sırasında büyük değer mutlaka sol dikey kenarda yer almalıdır." | Geçici M. 2/2-b · Ek-3 notu |
| 2 | Yuvarlama: aşama, yön, basamak | **KAPANDI (28.10.2026)** | Yönetmelikte hüküm yok; Ek-3'ün resmî metni (RG ek dosyası s.170) **sessiz**. EK-2 kılavuzunda yuvarlama yalnız bölüm bazında: göz (s.49, s.60 "bir üst tam sayıya"), kas-iskelet (s.92 "0,5 ve üzerinde ise bir üst"). s.13-26'da yok. → Motor ham değer döndürür; gösterim en fazla 2 ondalık, yarı yukarı, tek kez | EK-2 s.49, s.60, s.92 · Ek-3 s.170 |
| 3 | 65 yaş eki: kime, hangi aşamada | **KAPANDI — 65 (28.10.2026)** | M. 10/4: "65 yaş ve üzeri bireylerin engellilik oranına Balthazard formülü ile %10 eklenerek" → birleştirilmiş nihai orana, formülle. **Kaynak çelişkisi:** Ek-3 (e) "60 yaşın üzerindekilerde" | Yönetmelik M. 10/4 · RG 20.02.2019/30692 · Ek-3 s.170 |
| 4 | Tavan / kırpma | **DOĞRULANAMADI** | Genel tavan hükmü yok. Matematik gereği bileşke 100'ü aşmaz (asimptotik) — bu **yorum**, hüküm değil. Bölüm bazlı özel tavanlar (göz %92, s.41) bizim bölümlerde yok | — |
| 5 | 0 ve 100 | **DOĞRULANAMADI** | Özel hüküm yok. Matematik: 0 etkisiz, 100 kilitler. 0 gerçek kayıttır (Z-056) | — |
| 6 | Oran sayısı üst sınırı | **DOĞRULANDI — sınır yok** | Ek-3: "…Bu işlem sonsuza kadar devam ettirilebilir." Arayüze yapay sınır koymak ürün kararı olur | Ek-3 notu · Geçici M. 2/2-d |
| 7 | Aynı oranın iki kez girilmesi | **KAPANDI (28.10.2026)** | Mevzuat susuyor. Kılavuzdaki "bir patoloji iki kez hesaplanmış olur" uyarısı (s.55) göz puanlamasına ait. Tekrar engellenmez; her giriş katılır; bilgi uyarısı | EK-2 s.55 (ilgisiz) · ürün kararı |
| 8 | Ondalıklı oran kabulü | **KAPANDI (28.10.2026)** | "Tam sayı olmalıdır" hükmü yok. İlk sürümde tam sayı; bu **ürün tercihi**, mevzuat kuralı değil | Ek-3 (dolaylı) · EK-2 s.105 · ürün kararı |

**Özet:** 3 doğrulandı (1, 3, 6) · 3 ürün kararıyla kapandı (2, 7, 8) · 2 açık (4, 5).
3. maddede kaynaklar çelişiyordu (madde **65**, Ek-3 (e) **60**); 28.10.2026 ürün
kararıyla 65 seçildi (B-1 kapandı, çelişki kayıtlı). Yaş ekinin yuvarlamaya göre sırası
(B-3) de aynı gün kapandı.

**Sonuçlar:**

1. **Sıra seçimi arayüzden kalkar** — kural sırayı sabitliyor.
2. **Yaş, motorun zorunlu girdisidir** — 65 yaş eki doğrulandı.
3. **Hiçbir belirsizlik ürün kararıyla sessizce kapatılmaz**; kapananlar tarih + gerekçeyle
   kayıtlıdır; tavan (4) ve 0/100 (5) açık maddelerdir.

### 6.1 Kaynaklar

| Kaynak | Künye | Kullanıldığı yer |
| --- | --- | --- |
| **Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik** | RG 20.02.2019, No. 30692 · Bakanlığın güncel mevzuat sayfası ve RG künyesiyle teyit | M. 4/1-a, **M. 10/4 (65 yaş eki)**, Geçici M. 2 (algoritma, sıra) |
| **EK-2 Engelli Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu** | Projede `ek2_pages.json`, 168 sayfa (katalogun kaynağı) | Yuvarlama: s.49, s.60, s.92; örnek: s.105; kapsam: s.13-26 |
| **Ek-3 Balthazard Hesaplama Tablosu** | Yönetmelik eki; RG 20.02.2019/30692 ek dosyası (`20190220-2-1.pdf`, 172 sayfa, **taranmış görüntü** — metin katmanı yok). EK-3 tek sayfa: s.170; s.171-172 EK-4 formu | `A+B(1−A)` formülü, "büyük değer sol dikey kenarda", %35 + %20 = %48 örneği, "işlem sonsuza kadar devam ettirilebilir", **yuvarlama hakkında sessizlik**, (e) bendinde "60 yaş" |
| Mülga **Özürlülük Ölçütü… Yönetmeliği** | RG 30.03.2013, No. 28603 — **yürürlükten kaldırıldı** (yeni Yönetmelik M. 18) | Geçici M. 2 (a)-(e); "60 yaş" bendi **bu metnin (e) bendidir**. Yürürlükteki Geçici M. 2 (a)-(d) ile biter, yaş yalnız M. 10/4'te (65) |

**Kapsam taraması:** s.13-26'daki üç bölümde `Balthazard`, "aritmetik", "toplanır",
yuvarlama veya üst sınır ifadesi **hiç geçmiyor**; genel kural geçerlidir. (DERİ'de iki
kayıt notu var: s.16 yıllık kontrol, s.19 "yüz ve ele lokalize lezyonlar için ayrıca %5" —
ikincisinin yöntemi belirtilmemiştir; B-8 açık.)

**Sınır:** Ek-3 taranmış görüntü olduğu için sayfa görüntüsü okunarak incelendi.
Yuvarlama sorusu kesin olarak kapandı: **Ek-3'te yuvarlama hükmü yok.** Yaş bendi
çelişkisi (60 ↔ 65) 28.10.2026 kararıyla 65 lehine kapatıldı.

---

## 7. Karar durumu

### 7.1 Kapalı kararlar (28.10.2026)

| # | Konu | Sonuç |
| --- | --- | --- |
| **O-1** | Araç-1 65 yaş gösterimi | Araç-1 EK-2 temel oranını **yaş eklemesi olmadan** gösterir; otomatik yaş hesabı yapmaz; %10 kuralı nötr bilgi bloğunda (§3.14). Motor `yas_ekle=false` |
| **O-2** | Tek kayıtlı grup sayısı | **9** kabul edildi (D-013, D-014, D-017, D-049, D-062, D-075, D-086, D-134, H-056). Eski "12" tarihsel not |
| **B-1** | Yaş eşiği (65 ↔ 60) | **65**. Ek-3 (e) "60" kaynak çelişkisi olarak kayıtlı; eşik motorda tek sabit |
| **B-2** | Yuvarlama | Motor **ham** değer döndürür, ara aşamada yuvarlamaz; gösterim ayrı katman |
| **B-3** | Yaş ekinin sırası | Ham bileşke → yaş eki (ham) → tek gösterim yuvarlaması |
| **B-6** | Aynı oranın tekrarı | Engellenmez; her giriş hesaba katılır; bilgilendirici uyarı |
| **B-7** | Ondalıklı giriş | İlk sürümde tam sayı — **ürün tercihi**, mevzuat kuralı değil |
| **G-1…G-4** | Gösterim | En fazla 2 ondalık, yarı yukarı, tam sayıda ondalık yok, sondaki sıfırlar atılır, Türkçe virgül; tek kez ve yalnız sunumda |
| **S-1a** | Araç-1 → Araç-2 aktarım | **29.10.2026, teknik karar:** liste yalnız Araç-1 oturumunda; kopyala + bağlantı. Otomatik aktarım yok, Araç-2 değişmedi |
| **S-2a** | Sayfa düzeni | **29.10.2026, teknik karar:** iki uygulama ayrı sunucu/port (8766 / 8765), üstte karşılıklı bağlantı |

### 7.2 Kaynak çelişkileri (kayıtlı)

- **Yaş eşiği:** Yönetmelik M. 10/4 **65**; Ek-3 (e) ve mülga 2013 metni **60**.
  Uygulama 65'tir (B-1). 60'a dönülmez; değişiklik yeni tarihli karar gerektirir.
- **Künye (O-3):** JSON `meta.kaynak` "3.1.2019 … Mevzuat No 31275" diyor. Doğrulanan
  künye **20.02.2019 / 30692**. **31275 = 15.10.2020** tarihli RG'dir; o gün yayımlanan
  yönetmelikler (MEB sosyal etkinlikler değişikliği, Veri Depolama, Uludağ Üniv. TÖMER)
  engellilik değerlendirmesiyle **ilgisizdir**. Bu Yönetmeliğe değişiklik getirdiğine dair
  kayıt bulunamadı. **JSON `meta` değiştirilmedi**; 31275'in dosyaya nasıl girdiği
  izlenemiyor → düzeltme ayrı onayla yapılır.
- **Tek kayıtlı grup 12 ↔ 9:** eski "12" güncel veriyle yeniden üretilemedi; 9 kabul
  edildi (O-2).
- **"%10 eklenir" okuması:** aritmetik `+10` değil, Balthazard'dır; `%40 + %10 = %50`
  yanlıştır.
- **Kısıt sayıları:** 11 kayıt eklendikten sonra yeniden sayıldı: R-YILLIK 142,
  R-GECICI 34, R-VERGI 34, R-REMISYON 4, R-NAKIL 6, R-IKTIYOZ 4, R-EKTO 4.
- **Belirsiz örnek:** X-D09 çözülüp D-141 olduğu için ekran örneği **X-D03**'tür.
- **YARIN-DEVAM / arşiv belgeleri:** eski sayı ve hash'ler geçersizdir; tarihsel kayıttır,
  bu pakete alınmadı.

**O-3 kaynak araştırması (özet):**

| Sav | Dayanak | Sonuç |
| --- | --- | --- |
| **30692 = 20.02.2019**, *Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik* | Sağlık Bakanlığı e-Rapor kullanıcı kılavuzu; KHK Genelge 2019/0; MEB/üniversite duyuruları | **DOĞRULANDI** |
| Aynı tarihte *Çocuklar İçin Özel Gereksinim Değerlendirmesi Hakkında Yönetmelik* de 30692'de yayımlandı | Genelge ve kurum duyuruları | **DOĞRULANDI** |
| Yönetmelik 30.03.2013 / 28603 sayılı Özürlülük Ölçütü Yönetmeliğini yürürlükten kaldırdı | Yönetmelik m. 18; kurum açıklamaları | **DOĞRULANDI** |
| **31275 = 15.10.2020** RG içeriği: MEB Eğitim Kurumları Sosyal Etkinlikler değişikliği, Veri Depolama Kuruluşu değişikliği, Bursa Uludağ Üniv. TÖMER Yönetmeliği | Resmî Gazete fihristleri (15.10.2020 / 31275) | **DOĞRULANDI — engellilikle ilgisiz** |
| 31275'in bu Yönetmeliğe değişiklik getirdiği | — | **DOĞRULANAMADI** |
| 31275'in JSON `meta`'ya nasıl girdiği | — | **DOĞRULANAMADI** (kaynak izi yok) |

### 7.3 Açık kararlar (tahminle kapatılmadı)

| ID | Konu | Neden açık | Geçici davranış |
| --- | --- | --- | --- |
| **O-3** | Künye 30692 ↔ 31275 | 30692 doğrulandı; 31275 ilgisiz; JSON'a giriş izi yok | JSON `meta` değişmez; belgeler 30692 kullanır |
| **B-4** | Tavan / 100 aşımı | Kırpma hükmü yok | Kırpma yapılmaz |
| **B-5** | 0 ve 100 | Özel hüküm yok; 0 gerçek kayıt (Z-056) | Özel işlem yok |
| **B-8** | DERİ s.19 "ayrıca %5" | Aritmetik mi Balthazard mı belirsiz; X-D03 belirsizde | Kataloğa ve motora **eklenmedi** |
| **A-1…A-6** | 10 belirsiz kaydın çözümü | Bağlayıcı Bakanlık görüşü/genelge gerekir | Oran gösterilmez; uzman hekim yönlendirmesi |
| — | Hematoloji s.26 NOT kapsamı | 6 nakil kaydına mı, 78 kaydın tamamına mı? | Bölüm notu olarak gösterilir; kısıt sayılmaz |
| — | `alt_tur` şema sözleşmesi | Alan isteğe bağlı mı ilan edilecek, `—` kaldırılacak mı? | Ekran `—` değerini yutar; veri değişmez |
| — | `kisit` tipi | Sözleşmede "liste" olarak yazılmalı (metin değil) | Bugün 7 kod, 228 kayıt; liste olarak ele alınır |
| — | 72 imla/biçim kalemi | Bloklamıyor | Uygulanmadı |

**Kapalı olduğu için bu tabloya eklenmeyenler:** B-1, B-2, B-3, B-6, B-7, G-1…G-4,
O-1, O-2, S-1a, S-2a.

**Özet:** 10 karar grubu kapandı (8 motor/ürün + 2 teknik uygulama: S-1a, S-2a);
**3 madde açık** (B-4, B-5, B-8) + O-3'ün izi + A-1…A-6 ve üç veri/şema notu. Açık
maddelerin hiçbiri motoru **bloklamıyor**: motor ham değerle, kırpma yapmadan, tam sayı
maskesiyle çalışır; gösterim kuralı kapalı olduğu için iki araç aynı metni üretir.

### 7.4 Kayıt kuralı

B-1…B-8'den biri kapandığında satır **silinmez**; "kapandı + tarih + dayanak" olarak
işaretlenir. Sessizce koda gömülmesi yasaktır. Aynı kural O-, G- ve A- maddeleri için
geçerlidir.

---

## 8. Doğrulama sonuçları

Katalog dosyaları depoda `veri/` altında **değiştirilmeden** saklanır; bu pakette veriye
yazılmadı (salt okunur doğrulama). Aşağıdaki değerler 28.10.2026 tarihinde yeniden
hesaplandı.

### 8.1 Katalog sayıları

| Kontrol | Sonuç |
| --- | --- |
| `veri/katalog.json` kayıt | **276** |
| Oran toplamı | **8.990** |
| Bölüm dağılımı | Z **56** · D **142** · H **78** |
| `veri/belirsiz.json` satır | **21** (belirsiz **10** / çözüldü **11**) |
| Toplam satır | **286** (276 + 10) |
| Grup sayısı (ayraç solu) | **78**; tek kayıtlı **9** |
| Durum matrisi | 266 + 1 + 9 = **276** |
| `(hastalik, alt_tur)` tekrarı | **0** |
| `alt_tur = "—"` | **6** (D-013, D-014, D-017, D-062, H-056, H-065) |
| `hastalik` içinde `" — "` | **64** |
| JSON geçerliliği | İki dosya da hatasız parse |
| katalog MD5 | `B77AEF76A1310DE4AE93E703183E2A09` (68.914 B) |
| belirsiz MD5 | `89AE83AAFFF9D6541B75D4073FC1BE82` (19.037 B) |
| Depodaki kopya | `veri/katalog.json` / `veri/belirsiz.json`; kaynakla bayt düzeyinde aynı |

**Sayfa bazında kesin kayıt dağılımı (s.13-26):** 22 · 16 · 18 · 5 · 27 · 21 · 21 · 28 ·
25 · 15 · 21 · 26 · 27 · 4.

**Doğrulama yöntemi:** iki bağımsız sayım (resmî sayfa metninden elle; docx akışından
otomatik çıkarım) uyuştu: 286 = 58 + 148 + 80. Otomatik çıkarımın sayfa etiketleri
ZİHİNSEL bölümünde 12 satır kaydığı için sayfa alanları resmî basılı sayfa numarasından
alındı. Her sayfanın oran listesi katalog + belirsiz dosyasıyla karşılaştırıldı; 14 sayfanın
12'si birebir eşit. İki fark, oranın kaynakta **tek başına satırda** durduğu yerlerden
kaynaklanır (s.19 eritroderma 40; s.21 KTCL 3. madde 40). s.21 kaydı **D-141** olarak
kataloğa girdi; X-D06 (eritroderma) belirsizde kaldı. Üç bölümde oran aralığı olmadığı
ayrıca kontrol edildi.

#### 8.1.1 Katalog kontrol kanıtları (28.10.2026)

Kataloğa aktarılan 11 satır, alınmadan önce üç eksende kontrol edildi: **(1)** resmî sayfa,
**(2)** kaynakta yazan oran, **(3)** mevcut şemaya uyum. Aşağıdaki sonuçlar 28.10.2026
tarihinde dosyalar üzerinde yeniden doğrulandı.

| Kontrol | Sonuç |
| --- | --- |
| Sayfa + oran eşleşmesi | **11/11** doğru; hiçbirinde sayfa kayması yok (eşleme tablosu §3.10) |
| Kullanılan alanlar | Yalnız mevcut alanlar: `id, bolum, hastalik, alt_tur, oran, sayfa, kisit, kaynak_not` (+ DERİ'de `grup`) |
| `oran` / `sayfa` tipi | Hepsi tek tam sayı; `oran` 0–100 (0 değeri şemada serbest: `Z-012`, `Z-015`, `Z-022` de 0) |
| Kısıt kodları | Yalnız mevcut kodlar: `R-YILLIK`, `R-GECICI`, `R-VERGI`, `R-REMISYON`; **yeni kod gerekmedi** |
| `grup` değerleri (DERİ) | `X`, `VI-C`, `XIII` — üçü de `meta.grup_adlari` içinde tanımlı |
| `bolum` değerleri | Mevcut üç bölüm adıyla birebir |
| Kimlik çakışması | **Yok**; `(hastalik, alt_tur)` çifti hâlâ tekil |
| `kaynak_not` | Alan tanımlı; **yeni 6 kayıtta** yalnız kaynağa dair uyarı için kullanıldı (mevcut `H-019` ile toplam 7), oranı değiştirmez |

**Çakışma kontrolü (özet):** her aday, aynı ailedeki mevcut kayıtlarla karşılaştırıldı ve
hepsinde **eksik madde** tamamlandı: Z-055 ↔ Z-018…Z-021 · Z-056 ↔ Z-031…Z-036 ·
D-139 ↔ D-049/D-050 · D-140 ↔ D-066 · D-141 ↔ D-119…D-123 · D-142 ↔ aynı aile ·
H-074 ↔ H-001/H-002 · H-075 ↔ H-014 · H-076 ↔ H-020 · H-077 ↔ H-052…H-055 ·
H-078 ↔ H-061…H-064. Hiçbiri mevcut bir kaydın tekrarı değildir.

**Sayaç değişimi (uygulanan paket):**

| Ölçü | Önce | Sonra |
| --- | --- | --- |
| Kesin / belirsiz | 265 / 21 | **276 / 10** |
| Z kesin / belirsiz | 54 / 4 | 56 / 2 |
| D kesin / belirsiz | 138 / 10 | 142 / 6 |
| H kesin / belirsiz | 73 / 7 | 78 / 2 |
| Oran toplamı | 8.350 | **8.990** (+640 = 11 kaydın oran toplamı) |
| Toplam satır | 286 | **286** (değişmedi) |

12. aday (X-D03, %5) da alınsaydı 277 / 9 ve 8.995 olurdu; **alınmadı**.

**X-D03 neden bloke:** X-D03, X-D04 ve X-D05 ile **aynı NOT bloğunu** paylaşır. NOT (a)
"ayrıca %5 eklenir" der (ek mi, yerine mi belirsiz); NOT (b) "tanımlanmış başka bir hastalık
varsa puan almaz" der ve bu, oranın **uygulanıp uygulanmayacağını** değiştirir. `kaynak_not`
"oranı değiştirmez" alanıdır, bu kural oraya yazılamaz; doğru yer `kisit` olurdu ve
`R-BASKAH` kodu **yoktur**. Üçünü ayırmanın metinden dayanağı olmadığı için üçü birlikte
belirsizde bekler (A-1, A-2).

**`kaynak_not` değerleri (6 kayıt; oranı değiştirmez):**

| id | `kaynak_not` |
| --- | --- |
| Z-055 | Kaynakta iki ayrı madde "d)" ile numaralanmış (atipik otizm ve otizm); harf tekrarı düzeltilmedi. |
| D-139 | Kaynak metin yalnız iki kategori veriyor (10 ve 80); ara kombinasyonlar tanımsız. |
| H-074 | İki ölçüt birlikte aranır; yalnız biri sağlanırsa 1. madde (ağır olmayan, 40) uygulanır. |
| H-076 | İki ölçüt birlikte; sağlanmıyorsa 2. madde (40). Parantezdeki ifade sitopenileri niteler. |
| H-077 | Kaynakta "ya da veya" ve "__" yazım artefaktı var; anlam değişmedi. |
| H-078 | Kaynakta 5 numaralı madde yok; numaralandırma 4'ten 6'ya atlıyor, düzeltilmedi. |

**Ad / yol eşlemesi:** kaynak `katalog_taslak.json` → depoda `veri/katalog.json`;
`belirsiz.json` → `veri/belirsiz.json`. Depoya alınırken içerik değişmedi: iki dosya da
kaynak sürümle **bayt düzeyinde aynı** (SHA-256 eşit), MD5'ler §8.1'deki gibidir.
Uygulama bu dosyaları **salt okunur** okur (`katalog_okuyucu.py`); yazma yolu yoktur,
dosyaların mtime/boyut değerleri çalışma sırasında değişmez. Canlı sisteme entegrasyon
ayrı ve onaylı bir adımdır.

**Hash geçmişi:** kontrol raporu alındığında dosyalar 265 / 21 durumundaydı (rapor anındaki
kısa hash'ler `4B75FC52…`, `782DE5E7…`). 11 kayıt işlendikten sonra dosyalar değişti;
**güncel** değerler §8.1'deki `B77AEF76…` / `89AE83AA…` MD5'leridir. Rapor hash'leri
tarihsel izdir, güncel doğrulamada kullanılmaz.

### 8.2 Kısıt sayıları

R-YILLIK **142** · R-GECICI **34** · R-VERGI **34** · R-NAKIL **6** · R-REMISYON **4** ·
R-IKTIYOZ **4** · R-EKTO **4**. Toplam **228** kısıt kaydı; **182** kısıtlı, **94**
kısıtsız kayıt.

### 8.3 Motor doğrulaması

- `MOTOR_SURUMU = "0.2"`; davranış sözleşmeyle uyumlu, `bicimle_gosterim()` ayrı sunum
  katmanı.
- Doğrulanmış değerler: `[40]`→40 · `[40]`+65→46 · `[40,30]`→58 · `[40,30]`+65→62.2
  ("62,2") · `[33,33]`→55.11 · `[33,33]`+65→59.599 ("59,6") · `[33,33,33]`→69.9237
  ("69,92") · `[49,49]`→73.99 · `[40,40]`→64 · `[80]`+65→82 · `[100,100]`→100.
- DERİ +%5 uygulanmadı: `[20]` → 20 (25 değil).

### 8.4 Testler

| Grup | Komut | Sonuç |
| --- | --- | --- |
| Ortak motor | `python -m unittest -v test_balthazard_motoru` | **77 test, OK** |
| Katalog yükleyici | `python -m unittest -v test_katalog_okuyucu` | **27 test, OK** |
| Araç-1 | `python -m unittest -v test_arac1` | **33 test, OK** |
| Araç-2 | `python -m unittest -v test_arac2` | **11 test, OK** |

Toplam **148** test; 29.10.2026 tarihinde depo kökünden çalıştırıldı ve tamamı geçti.

Araç-1 testleri: sayı/dağılım değişmezleri, arama (§3.6), 276 sonucun alanları, `—` ve
H-065 seviyesi, 9 tek kayıtlı grup, 10 belirsiz / 11 çözülen ayrımı, 7 kısıt metni,
`R-VERGI` sayısı, 65 yaş bloğu, hematoloji notu, yasak ibareler, `mtime` sabitliği.

Araç-2 testleri: gösterim katmanı, `POST /api/hesapla`, hata geçişi (motor kodu
değiştirilmez), UTF-8, 404.

### 8.5 Belgeler arası tutarlılık (28.10.2026)

| Kontrol | Sonuç |
| --- | --- |
| Eski sayılar (265 / 21 / 12 / 138 / 177 / 252 / 73) | 265 / 21 yalnız §8.1.1'de **geçiş tablosu** olarak bilinçli; diğerleri yalnız tarihsel/arşiv belgelerinde |
| "X-D09 örneği" | Yalnız değişiklik notunda ("X-D09 → X-D03"); örnek X-D03 |
| Motor imzası | `balthazard({oranlar, yas, yas_ekle=true})` her yerde aynı |
| Tekrar uyarısı metni | Aynı; onay istemez |
| Tam sayı gerekçesi | Her yerde "ürün tercihi, mevzuat kuralı değil" |
| Künye | Her yerde 20.02.2019 / 30692; 31275 açık; JSON `meta` değişmedi |
| Tek kayıtlı grup | Her yerde **9**; 12 yalnız tarihsel not |
| Yuvarlanmış örnek | Yalnız `%40 → %46` ve ham değer + gösterim çiftleri; tek başına yuvarlanmış toplam yok |

---

## 9. Sınırlar

- Bu sözleşme **kod değildir**; uygulama kodu, build ve deploy bu belgenin kapsamı
  dışındadır. Araç-1 ekranı `arac1/` altında **yerel prototip** olarak geliştirildi
  (§4.12); canlı uygulamaya bağlanmadı.
- Katalog verisi, oranlar ve kısıt değerleri değiştirilmez; dosyalar `veri/` altında depoda
  saklanır, Araç-1 bunları yalnız **okur** (yazma yolu yoktur; kanıtlar §8.1.1).
- Göz, işitme, konuşma ve kas-iskelet bölümleri kapsam dışıdır; oran uydurulmaz.
- 11 çözülen kayıt tekrar eklenmez; 10 belirsiz kayıt kesin oran gibi gösterilmez.
- Canlı FastAPI uygulaması, workflow'lar ve dağıtım ayarları değiştirilmez.
- İmla düzeltme listesi (72 kalem) uygulanmadı.

---

## 10. Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
| --- | --- | --- |
| 0.1 | 28.10.2026 | Araç-1/Araç-2 ilk sözleşme ve wireframe taslakları; ortak motor sözleşmesi |
| 0.2 | 28.10.2026 | Motor ham değer döndürür (B-2); B-6/B-7 kapandı; katalog 276/10 |
| 0.3 | 28.10.2026 | O-1, O-2 kapandı; 65 yaş Araç-1'de bilgi bloğu; O-3 kaynak araştırması |
| 0.4 | 28.10.2026 | G-1…G-4 gösterim kararı; B-3 kapandı; test vektörleri 14–20; Araç-2 §12.3 |
| **1.0** | 28.10.2026 | Altı belge tek `SOZLESME.md` + `README.md` olarak birleştirildi; içerik korundu, tekrarlar kaldırıldı |
| **1.1** | 28.10.2026 | "Katalog JSON'ları okunmadı" ifadesi düzeltildi (yalnız salt okunur doğrulama); katalog kontrol kanıtları §8.1.1'e kalıcı olarak eklendi |
| **1.2** | 28.10.2026 | Katalog verisi `veri/katalog.json` + `veri/belirsiz.json` olarak depoya alındı (içerik değişmedi); §3.1 ve §8 yolları güncellendi |
| **1.3** | 29.10.2026 | Araç-1 ekranı ve salt okunur yükleyici geliştirildi; §4.1/§4.9 uygulama notları, §4.12 ve S-1a/S-2a teknik kararları eklendi; test toplamı 145. Açık kararlar (B-4, B-5, B-8, O-3, A-1…A-6) değişmedi |
