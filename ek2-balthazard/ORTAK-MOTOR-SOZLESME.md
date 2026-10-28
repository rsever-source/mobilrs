# Ortak Hesaplama Motoru — Arayüz Sözleşmesi

Sürüm: 0.3 · Tarih: 28.10.2026 · Durum: **uygulama öncesi son**
Bağlı belgeler: `ARAC-1-SOZLESME.md`, `ARAC-1-WIREFRAME.md`, `ARAC-2-WIREFRAME.md`
Kapsam: `balthazard()` fonksiyonunun **girdi/çıktı sözleşmesi**, yaş kuralı ve **gösterim kuralı**.

> **0.3 değişikliği (gösterim kararı):** G-1…G-4 **kapandı** (28.10.2026 ürün kararı).
> Gösterim en fazla **2 ondalık**, yarı yukarı (`ROUND_HALF_UP`), tam sayıda ondalık yok,
> sondaki gereksiz sıfırlar atılır, Türkçe virgül; yuvarlama **tek kez ve yalnız sunumda**
> yapılır. **Hesap değişmedi:** motor ham değeri döndürmeye devam eder
> (`yuvarlama.uygulandi = false`). Ayrıntı §7, vektörler §9.

> **0.2 değişikliği (karar uygulaması):** B-2 motorda kapandı — `balthazard()` **ham değer**
> döndürür, ara aşamalarda yuvarlama yapmaz (`yuvarlama.uygulandi = false`). **Gösterim
> hassasiyeti** (G-1…G-4) ayrı bir karar noktasıdır ve motora girmez
> (`ARAC-2-WIREFRAME.md` §6.1). B-6 ve B-7 ürün kararıyla kapandı; B-4, B-5, B-8 açık.

> Bu belge **kod değildir**; imza ve davranış sözleşmesidir. Amaç, iki aracın da aynı motoru
> çağırmasını ve hiçbir ekranın kendi hesabını yapmamasını garanti etmek.
> **Motor yuvarlamaz** (B-2 kapandı). §9'daki vektörler motorun **ham** çıktısını doğrular;
> ondalık sonuçlu örnekler yalnız §9.1'de, ham değer **ve** gösterim metni ayrı ayrı yazılır.

---

## 1. Neden ortak motor

| Kural | Gerekçe |
| --- | --- |
| Tek `balthazard()` fonksiyonu | İki araç da aynı formülü kullanır; kopya hesap kodu **yasak** |
| Tek yaş eki noktası | %10 eklemesi yalnız motorun içinde uygulanır; ekranlar ekleme yapmaz |
| Tek sıralama noktası | Büyükten küçüğe sıralama motorda; arayüz sıra göndermez |
| Arayüz motorun döndürmediği sayıyı **göstermez** | Yuvarlama/ekleme arayüzde yapılırsa iki araç farklı sonuç verir |

Araç-1 motoru **tek bileşenle** çağırır: `oranlar = [x]`, `yas` yine zorunlu, **`yas_ekle = false`**.
Araç-1 ekranda yaş ekini **göstermez** (bkz. `ARAC-1-SOZLESME.md` §3.8, O-1 kararı): motor
`yas_eklemesi.uygulandi = false` döner ve arayüz yaş eki satırını **çizmez**. Böylece tek hesap
kodu korunur, iki araç ayrışmaz. Yaş eklemesinin tek uygulama yeri yine motordur; Araç-1 onu
**istemez**, kendi eklemez.

---

## 2. Girdi sözleşmesi

```
balthazard(girdi) → cikti
```

| Alan | Tip | Zorunlu | Kural |
| --- | --- | --- | --- |
| `girdi.oranlar` | tam sayı listesi | **evet** | En az 1 öğe; her öğe 0–100; sıra **anlamsız** (motor sıralar) |
| `girdi.yas` | `"65_alti" \| "65_ve_uzeri"` | **evet** | Varsayılan **yok**; `null`/eksik → hata |
| `girdi.yas_ekle` | boolean | hayır (varsayılan `true`) | Yalnız Araç-1 gibi "bilgi amaçlı" çağrılarda `false`; normalde gönderilmez |

Notlar:

- **Etiket, hastalık adı, kayıt kimliği motora girmez.** Motor veri tanımaz; yalnız sayı ve yaş.
- `yas` metin yerine sayı olsaydı (doğum yılı) eşik motor içinde hesaplanırdı; bu turda
  **seçim metni** kullanılır (en küçük değişiklik).
- Oran sayısı için **üst sınır yok** (Ek-3: "işlem sonsuza kadar devam ettirilebilir").
- Girdi listesi motor içinde **değiştirilmez** (kopya üzerinde çalışılır).

---

## 3. Çıktı sözleşmesi

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
    uygulandi: false,       // KAPANDI (B-2): motor yuvarlamaz
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

- **İstisna (exception) fırlatılmaz**; her durum `ok` alanıyla döner. Arayüz `ok=false` ise
  sonuç çizmez, `hata.mesaj`'ı gösterir.
- `adimlar` her zaman **büyükten küçüğe** sırada üretilir; yaş eki varsa **son adım** olarak
  `tur: "yas_eki"` ile eklenir. Arayüz adım üretmez, yalnız çizer.
- `siralama.uygulanan`, kullanıcıya "biz sıraladık" bilgisini göstermek için döner; arayüz
  bu listeyi **değiştiremez**.
- `yuvarlama.uygulandi` **her zaman `false`** — motor ham değer döndürür (B-2, 28.10.2026).
  Gösterim kuralı (§7.2, G-1…G-4) ayrı katmanda uygulanır; motor alanları değişmez.

---

## 4. Yaş kuralı

**Eşik: 65 yaş ve üzeri.** Dayanak: *Erişkinler İçin Engellilik Değerlendirmesi Hakkında
Yönetmelik*, m. 10/4 — "65 yaş ve üzeri bireylerin engellilik oranına Balthazard formülü ile
%10 eklenerek".

| Kural | Açıklama |
| --- | --- |
| Yöntem | **Balthazard**: `yeni = A + (100 − A) × 10 / 100`. Aritmetik `+10` **değil** |
| Aşama | Bileşke hesaplandıktan **sonra**, son adım olarak |
| Seçim | `yas` zorunlu; `65_alti` seçilirse ek uygulanmaz |
| Tek nokta | Ek yalnız bu fonksiyonun içinde; arayüz/ekran ekleme yapmaz |
| Araç-1 | `yas_ekle=false` ile çağırır; motor ek uygulamaz, sonuç EK-2 temel oranıdır (O-1) |
| Örnek | `[40] + 65+` → **46** (yuvarlama gerekmez) |
| Kaynak gösterimi | Kaynak künyesi **yalnız** "65 yaş ve üzeri" seçiliyken sonucun altında (Araç-2 §6) |

**Kaynak çelişkisi (kayıtlı, kapatılmadı):** Ek-3'ün (e) bendi "60 yaşın üzerindekilerde" diyor.
Uygulama kararı **65**'tir (28.10.2026 ürün kararı, B-1). Eşik motorda **tek sabit** olarak
tutulur; iki ayrı yerde yazılmaz.

**B-3 (yaş ekinin yuvarlamaya göre sırası) kapandı (28.10.2026, §7.2/G-3).** Sıra:
ham bileşke → yaş eki (ham) → **tek** gösterim yuvarlaması. Yaş eki yuvarlanmış değere
uygulanmaz; `%40 → %46` örneği her iki kuralda da aynıdır.

---

## 5. Hata kodları

| Kod | Durum | Kullanıcıya gösterilecek metin | Alan |
| --- | --- | --- | --- |
| `E_ORAN_YOK` | Liste boş | "En az bir oran girin." | `oranlar` |
| `E_ORAN_ARALIK` | Öğe < 0 veya > 100 | "Oran 0 ile 100 arasında olmalıdır." | `oranlar` |
| `E_ORAN_TAMSAYI` | Öğe tam sayı değil | "Oran tam sayı olmalıdır." (**ürün tercihi**, B-7 kapandı) | `oranlar` |
| `E_ORAN_TIP` | Öğe sayı değil | "Yalnız sayı girin." | `oranlar` |
| `E_YAS_SECILMEDI` | `yas` boş/null | "Yaş aralığını seçin." | `yas` |
| `E_YAS_GECERSIZ` | Bilinmeyen değer | "Yaş aralığını seçin." | `yas` |

Uyarılar (hata değil, `uyarilar` dizisi):

| Kod | Durum | Metin | Davranış |
| --- | --- | --- | --- |
| `U_ORAN_TEKRAR` | Aynı değer iki kez | "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir." | **Engellenmez**; bilgi uyarısı, onay istemez (B-6 kapandı) |
| `U_ORAN_100` | 100 var | "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?" | Onay istenir (B-4 açık: kırpma kuralı yok) |
| `U_ORAN_SIFIR` | 0 var | "0 oranı listeye eklendi. Bileşkeyi değiştirmez." | Bilgi |

**Katalog bütünlük hataları** (motor değil, yükleme katmanı) — `ARAC-1-SOZLESME.md` §2.4:
sayı değişmişse, kimlik boşluğu varsa, `oran` aralık dışıysa uygulama **açılmaz**.

---

## 6. Sıralama

- Kural: **büyükten küçüğe**, iki kez doğrulandı (Geçici m. 2/2-b ve Ek-3 notu).
- Kullanıcı sıra **seçemez**; arayüz sıra bilgisi **göndermez**.
- **Eşit değerler:** sıra değişmez (kararlı sıralama); eşit iki değerin yeri sonucu değiştirmez,
  bu yüzden B-6 kapsamında ayrı karar **gerekmez**.
- Sıralama **sayısal**dır (metin sıralaması yasak: `"100" < "40"` tuzağı).

---

## 7. Yuvarlama ve gösterim — ikisi de kapandı

### 7.1 Hesap (motor) — değişmedi

- **B-2 kapandı, 28.10.2026:** motor **ham** değeri döndürür (`sonuc.deger`),
  `sonuc.tam_sayi_mi` ile birlikte; ara aşamalarda yuvarlama **yapmaz**.
- `yuvarlama.uygulandi` her zaman `false`, `yuvarlama.kural` her zaman `null`.
- Ara adımlar (`adimlar[]`) da ham değer taşır; hiçbir katman adımı yeniden yuvarlamaz.

### 7.2 Gösterim kararı — **G-1…G-4 kapandı (28.10.2026)**

**Dayanak:** Mevzuatta (Yönetmelik, Ek-2 kılavuzu, Ek-3) **gösterim hükmü yoktur**.
Bu nedenle karar bir **ürün/arayüz tercihidir**, hukuki kural değildir; dayanağı yazılı
olduğu için tarihli ürün kararıyla kapatılır ve **hesabı değiştirmez**.

| # | Karar | Sonuç |
| --- | --- | --- |
| G-1 | Ondalık basamak sayısı | **En fazla 2**, sondaki gereksiz sıfırlar atılır; **tam sayıda ondalık gösterilmez** |
| G-2 | Yuvarlama yönü | **Yarı yukarı** (`ROUND_HALF_UP`); kesme ve yarı çift (`banker's`) **kullanılmaz** |
| G-3 | Yaş ekinin gösterim sırası | Ham bileşke → **yaş eki (ham)** → **tek yuvarlama**; yuvarlama yaş ekini **etkilemez** |
| G-4 | Adım dökümünde ondalık | **Evet**, aynı kural (en fazla 2 ondalık, yarı yukarı); ham değer ayrıca taşınır |

**Bağlayıcı kurallar:**

1. **Yuvarlama tek kez, yalnız sunumda:** ham değer → metin. Zincirde ikinci bir yuvarlama
   **yoktur** (adım → toplam → metin gibi ara yuvarlama yasak).
2. **Ham değer korunur:** gösterim motora geri yazılmaz; `sonuc.deger` ve `adimlar[]`
   yuvarlanmış değerle **değiştirilmez**.
3. **Kopyalama / dışa aktarma ham değeri taşır** (yuvarlanmış metin değil). Böylece ekranda
   görünen 2 ondalıklı metin ile dışa aktarılan değer arasında bilgi kaybı olmaz.
4. **Türkçe ondalık virgül** varsayılandır; teknik çıktı (JSON, test) **nokta** kullanır.
5. **Ondalık ayırıcı yalnız sunum katmanında belirlenir**; hesap katmanı ayırıcı bilmez.
   `bicimle_gosterim()` bunun tek yeridir.
6. Ekran "yaklaşık", "~" veya "en yakın tam sayı" ifadesini **kendi başına eklemez**.
7. Gösterim kuralı değişirse (ör. 1 ondalık) **yalnız sunum katmanı** değişir; motor, test
   vektörleri ve ham değerler aynı kalır.

**Uygulama:** `balthazard_motoru.bicimle_gosterim(deger, basamak=2, ayirici=",")` — ayrı
**sunum** yardımcısıdır, `balthazard()` çıktısını değiştirmez (`ARAC-2-WIREFRAME.md` §6.1).

**B-3 (yaş ekinin yuvarlamaya göre sırası) bu kararla kapandı:** yaş eki ham bileşkeye
uygulanır, yuvarlama en sonda tek kez yapılır; `%40 → %46` örneği karar değişse de değişmez.

---

## 8. Açık kararların motora etkisi

| ID | Konu | Motor bugün ne yapar | Kod yazılmadan önce gerekli mi? |
| --- | --- | --- | --- |
| B-2 | Yuvarlama | Yuvarlamaz, ham döner | **Hayır (kapandı)** — motor ve gösterim ayrı ayrı kapandı (§7) |
| B-3 | Yaş ekinin sırası | Yaş ekini ham bileşkeye uygular; yuvarlama yok | **Hayır (kapandı)** — yuvarlama en sonda, tek kez (§7.2/G-3) |
| B-4 | Tavan / 100 aşımı | Kırpma yapmaz | Hayır (pratikte ulaşılmaz) — **açık**, kural uydurulmaz |
| B-5 | 0 / 100 | Özel işlem yapmaz | Hayır — **açık**, özel işlem eklenmez |
| B-6 | Aynı oranın tekrarı | Engellemez, `U_ORAN_TEKRAR` bilgi uyarısı verir; her giriş hesaba katılır | Hayır (kapandı) |
| B-7 | Ondalıklı giriş | `E_ORAN_TAMSAYI` ile reddeder | Hayır (kapandı — ürün tercihi) |
| B-8 | DERİ +%5 | **Uygulamaz**; katalogda yok | Hayır — Araç-1 kapsamı, **açık** (X-D03) |

---

## 9. Test vektörleri — ham değer

Bu tablo, motorun **ham** çıktısını doğrulamak için kullanılır. Tüm örneklerde sonuç tam
sayıdır; hiçbiri gösterim kararına bağlı değildir (gösterim kararı §7.2'de kapandı).

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

### 9.1 Ondalık sonuçlu vektörler — ham değer **ve** gösterim

Ham değer kesindir (motor içeride `Fraction` kullanır); gösterim metni §7.2 kuralıyla
**tek kez** üretilir. İki sütun birbirinden bağımsız doğrulanır.

| # | `oranlar` | `yas` | Ham `sonuc.deger` | Gösterim |
| --- | --- | --- | --- | --- |
| 14 | `[33, 33]` | `65_alti` | `55.11` | `55,11` |
| 15 | `[49, 49]` | `65_alti` | `73.99` | `73,99` |
| 16 | `[40, 30]` | `65_ve_uzeri` | `62.2` | `62,2` |
| 17 | `[33, 33]` | `65_ve_uzeri` | `59.599` | `59,6` |
| 18 | `[33, 33, 33]` | `65_alti` | `69.9237` | `69,92` |
| 19 | `[40, 40]` | `65_alti` | `64` | `64` |
| 20 | `[80]` | `65_ve_uzeri` | `82` | `82` |

- **Ham değer yuvarlanmış beklentiyle karşılaştırılmaz** (ör. 17 için `59.6` yazılmaz).
- `59.599 → "59,6"` örneği, sondaki sıfır atmanın (`59,60 → 59,6`) yuvarlamadan **ayrı**
  bir adım olduğunu gösterir.
- Tam sayı çıkan ham değerlerde (`64`, `82`) gösterim de ondalıksızdır (G-1).

---

## 10. Uygulamaya aktarımda doğrulanacaklar

1. İki araç da **aynı** fonksiyonu çağırıyor (kopya hesap yok) — kod aramasıyla doğrulanır.
2. `yas` parametresi olmadan çağrı **derlenmiyor/reddediliyor** (zorunlu alan).
3. Yaş eki ve sıralama yalnız motorda; arayüzde `sort`, `+10`, `× 0.9` benzeri hesap yok.
4. Test vektörleri 1–20 birebir geçiyor (1–13 ham tam sayı, 14–20 ham ondalık §9.1).
5. `yuvarlama.uygulandi` her yanıtta `false`; hiçbir katman kendi yuvarlamasını yapmıyor (B-2).
6. Motor, katalog dosyalarını **okumaz**; yalnız sayı listesi ve yaş alır.
7. **Gösterim tek yerde:** ekranlar `bicimle_gosterim()` dışında biçimlendirme yapmıyor;
   yuvarlama tek kez, en sonda (G-1…G-4).
8. **Ham değer korunuyor:** gösterimden sonra `sonuc.deger` / `adimlar[]` değişmiyor;
   kopyala/dışa aktar ham değeri taşıyor (§7.2/2-3).
