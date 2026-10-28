# Araç-2 — Metinsel Ekran Taslağı (Wireframe)

Sürüm: 0.4 · Tarih: 28.10.2026 · Durum: **uygulama öncesi son**
Bağlı olduğu belgeler: `ARAC-1-SOZLESME.md`, `ARAC-1-WIREFRAME.md`, `ORTAK-MOTOR-SOZLESME.md`
Kapsam: Balthazard hesaplama — **hastalık kataloğu içermez**

> **0.4 değişikliği (gösterim kararı):** G-1…G-4 **kapandı** (§6.1): sonuç ve adım dökümü
> en fazla **2 ondalık**, **yarı yukarı**, tam sayıda ondalık yok, sondaki sıfırlar atılır,
> Türkçe virgül; yuvarlama **tek kez ve yalnız sunumda**. Ham değer, `adimlar[]` ve
> `yuvarlama.uygulandi = false` **değişmedi**. B-4, B-5, B-8 açık.

> **0.3 değişikliği (karar uygulaması):** B-2/B-3 motorda **ham değer** olarak kapandı;
> **gösterim hassasiyeti** ayrı bir karar noktası olarak tanımlandı (§6.1). B-6 ve B-7 ürün
> kararıyla kapandı (§8.5). B-4, B-5, B-8 **açık**. O-1 kararı gereği Araç-2 yaş ekinin
> **tek** uygulama yeridir.

> **0.2 değişikliği:** `%40 → %46` örneği eklendi (yuvarlama gerektirmeyen tek örnek);
> "yüzde 10 eklenir" ifadesinin **Balthazard** olduğu netleştirildi; `X-Z02` → **`Z-056`**;
> yaş seçimi modeli (varsayılansız iki radio) gerekçelendirildi; boş durumda `%0` yerine nötr
> durum; girdi değişince "sonuç eski" durumu (§12.2); referans görsel değerlendirmesi (§13).
>
> Bu belge **kod değildir**. Yerleşim, metin ve davranış sözleşmesidir.
> **Motor yuvarlamaz** (B-2, 28.10.2026) ve **gösterim kuralı 0.4'te kapandı** (§6.1):
> ondalıklı örnekler artık iki değerle verilir — **ham değer** ve **gösterim metni** — ve
> ikisi hiçbir yerde birbirine karıştırılmaz.

---

## 1. İki araç — neden ayrı

| | **Araç-1: Engel Oranı Bul** | **Araç-2: Balthazard Hesapla** |
| --- | --- | --- |
| Soru | "Bu hastalık ve seviye için mevzuatta hangi oran var?" | "Bildiğim oranların bileşkesi ne eder?" |
| Girdi | hastalık + seviye seçimi | **elle girilen oranlar** |
| Veri | katalog (276 kesin / 286 satır) | **yok** |
| Hastalık bilgisi | var | **yok** |
| Kısıt denetimi | evet | **hayır — yapılamaz** |
| Hesap modeli | **canlı** — seçim/ekleme anında sonuç yenilenir | **"Hesapla" butonu** — sonuç yalnız butonla üretilir |
| Sonuç | tek oran (bileşen) | bileşke |

**Ortak hesaplama motoru:** iki araç aynı `balthazard()` fonksiyonunu, aynı yuvarlama
kuralını ve aynı 65 yaş eki uygulamasını kullanır. Hesap kodu **tek yerde** yazılır;
hiçbir ekran kendi hesabını yapmaz. 65 yaş eki **tek uygulama noktasında** devreye girer.

Araç-2, Araç-1'in yerine geçmez; Araç-1'den gelen oranı da **sorgulamaz**, yalnız taşır.

---

## 2. Kalıcı uyarı (her ekranda, kapatılamaz)

Ekranın üstünde, sayfa boyunca sabit:

```
┌──────────────────────────────────────────────────────────────┐
│ ⓘ Bu araç yalnızca girdiğiniz oranları birleştirir.           │
│   Oranların doğruluğu ve kullanım kuralları burada            │
│   denetlenmez.                                               │
│                                                              │
│   Hastalığa ve mevzuata özgü kısıtlar (ör. yıllık yeniden     │
│   değerlendirme, vergi indiriminde kullanılamama, remisyonda  │
│   oran verilmemesi) bu araçta doğrulanamaz. Bunlar için       │
│   "Engel Oranı Bul" aracına bakın.                            │
└──────────────────────────────────────────────────────────────┘
```

Kurallar:

- Uyarı **kapatılamaz**, katlanamaz, kaydırınca kaybolmaz.
- Hesaplama sonucunun **hemen üstünde** tekrar edilir (kısa hâli).
- Araç-1'e bağlantı metin olarak verilir; Araç-2 kendi içinde hastalık araması **yapmaz**.

---

## 3. Ekran: Boş durum (giriş)

```
┌──────────────────────────────────────────────────────────────┐
│  Engel Oranı Bul   [ Balthazard Hesapla ]        ← aktif sekme│
├──────────────────────────────────────────────────────────────┤
│ ⓘ Bu araç yalnızca girdiğiniz oranları birleştirir…           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Bildiğiniz oranları girin                                  │
│                                                              │
│      Oran (%)  [      ]   Etiket (isteğe bağlı) [          ]  │
│      [ + Ekle ]                                              │
│                                                              │
│  Henüz oran eklenmedi.                                       │
│                                                              │
│  ── veya ──                                                  │
│  [ Engel Oranı Bul aracından oran aktar ]                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
  Bilgilendirme amaçlıdır; resmî sağlık kurulu raporu yerine geçmez.
```

- Boş durumda "Hesapla" butonu **pasif**; neden pasif olduğu yazılı: "En az bir oran girin."
- **Boş durumda sonuç kutusu çizilmez.** Referans görselde boşken `%0` gösteren büyük bir
  halka vardı; bu, "sonuç var" izlenimi verdiği için **alınmadı**. Yerine nötr metin:
  "Henüz oran eklenmedi."
- Hastalık adı, tanı, seviye alanı **yoktur**. Yalnız sayı ve isteğe bağlı etiket.
- **Yaş kontrolü bu ekranda yok**; ilk oran eklendiğinde §5'te görünür. Varsayılan seçim
  yapılmaz — kullanıcı seçmeden "Hesapla" **pasiftir** ("Yaş aralığını seçin.").
- **Bu araçta hesap canlı değildir:** sonuç yalnız "Hesapla" ile üretilir. Canlı güncellenen
  hesap, katalogdan oran bulan **Engel Oranı Bul** aracının davranışıdır; iki araç bu noktada
  bilinçli olarak farklıdır (28.10.2026 kararı).

### 3.1 Formül açıklaması (katlanabilir, varsayılan kapalı)

Giriş ekranının altında, tek satır başlık: **"Nasıl hesaplanır?"** Açıldığında 4 kısa adım:

```
1) Oranlar büyükten küçüğe sıralanır (kural; kullanıcı seçmez).
2) İlk iki oran birleştirilir:  A + (100 − A) × B / 100
3) Çıkan sonuç, sonraki oranla aynı formülle birleştirilir.
4) 65 yaş ve üzeri seçildiyse, bileşkeye %10 aynı formülle eklenir.
```

- Bu kart **eğitim amaçlıdır**, sonuç üretmez; örnek olarak yalnız `%40 → %46` verilir (yaş eki).
- Referans görseldeki 4 adımlı anlatım **fikir olarak** alındı; metin ve görsel düzen
  Engelli.me'ye göre yeniden yazıldı, kopyalanmadı.

---

## 4. Ekran: Oran ekleme

```
┌──────────────────────────────────────────────────────────────┐
│  Oran (%)  [  40  ]    Etiket (isteğe bağlı) [ Sağ kulak    ] │
│                                                              │
│  [ + Ekle ]                                                  │
│                                                              │
│  ⚠ Girdiğiniz değer 0 ile 100 arasında olmalıdır.            │
│  ⚠ Yalnız sayı girin; "%" işareti otomatik eklenir.          │
└──────────────────────────────────────────────────────────────┘
```

**Doğrulama kuralları**

| Girdi | Davranış | Mesaj |
| --- | --- | --- |
| Boş | Ekleme yapılmaz | "Bir oran girin." |
| 0-100 dışı | Ekleme yapılmaz | "Oran 0 ile 100 arasında olmalıdır." |
| Ondalıklı (ör. 12,5) | **İlk sürümde kabul edilmez** | "Oran tam sayı olmalıdır." |
| Harf/özel karakter | Girdi maskesi engeller | — |
| 0 | Kabul edilir | "0 oranı listeye eklendi. Bileşkeyi değiştirmez." |
| 100 | Kabul edilir, **uyarı** | "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?" |
| Aynı değer tekrar | **Kabul edilir; engellenmez** | Bilgi: "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir." |
| Etiket boş | Kabul edilir | Liste satırında "Etiketsiz oran" görünür |

- **Tam sayı girişi bir ürün tercihidir, mevzuat kuralı değildir** (B-7, 28.10.2026).
  Yönetmelikte "tam sayı olmalıdır" hükmü **yok**; Ek-3 notu yalnız oranların ondalık
  karşılıklarından söz eder. İlk sürümde giriş maskesi tam sayıya kilitlenir; ondalık desteği
  gerekirse **yeni tarihli ürün kararıyla** açılır ve motor sözleşmesi sürümü artırılır.
- **Tekrar eden oran engellenmez** (B-6, 28.10.2026): aynı değer iki kez girilebilir, ikisi de
  hesaplamaya katılır. Uyarı **bilgilendiricidir**, onay istemez ve kullanıcıyı engellemez.
  Gerekçe: mevzuat bu konuda susuyor; sessizce veri atmak / zorla birleştirmek yerine
  kullanıcının girdiği her oran hesaba dahil edilir ve olası çift sayım riski yazıyla bildirilir.
- Etiket serbest metindir; **hastalık adı zorunlu değildir**, teşhis istemez.
- Etiket uzunluğu 60 karakter; liste satırında kısaltılır, tamamı ipucunda görünür.

---

## 5. Ekran: Liste (çoklu oran)

```
┌──────────────────────────────────────────────────────────────┐
│  Girdiğiniz oranlar (3)                        [ Tümünü sil ] │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 1.  %40   Sağ kulak                       [düzenle][×] │  │
│  │ 2.  %30   Sol göz                         [düzenle][×] │  │
│  │ 3.  %10   Etiketsiz oran                  [düzenle][×] │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [ + Oran ekle ]                                             │
│                                                              │
│  Sıralama: büyükten küçüğe (kural gereği, değiştirilemez)     │
│                                                              │
│  Yaş:  ( ) 65 yaş altı   ( ) 65 yaş ve üzeri                 │
│                                                              │
│  [ Hesapla ]                                                 │
└──────────────────────────────────────────────────────────────┘
```

**Ekleme / silme / düzenleme**

- Ekleme: satır listenin sonuna eklenir; odak yeni satıra gider.
- `[×]` tek satırı siler; **geri alma** bağlantısı 5 saniye görünür ("Geri al").
- `[düzenle]` satırı yerinde düzenler; iptal eski değeri korur.
- `[Tümünü sil]` onay ister: "Tüm oranlar silinecek. Emin misiniz?"
- Liste boşalırsa §3'e dönülür, sonuç alanı temizlenir.

**Sıra seçimi yok.** Yönetmelik sırayı sabitler: "Bu oranlar en yükseğinden başlanarak
sıraya konulur" (Geçici M. 2/2-b; bkz. §8.2/1). Kullanıcı sıra seçemez; liste ekranda
giriş sırasıyla görünse bile motor her zaman **büyükten küçüğe** sıralayarak hesaplar.
Ekranda bu yalnız bilgi satırı olarak yazılır, kontrol (radio/switch) çizilmez.

**Yaş kuralı kesin — ürün kararı (28.10.2026).** İki seçenekten biri işaretlenir; **varsayılan
seçim yoktur**, seçilmeden "Hesapla" pasiftir. Etiket **"65 yaş ve üzeri"** (M. 10/4).
Seçilirse hesaplanan orana **%10, Balthazard formülüyle** eklenir; doğrudan 10 puan eklenmez.
"65 yaş ve üzeri" seçiliyken sonucun altında kaynak künyesi görünür (§6). Ek-3'ün (e) bendinde
"60 yaş" yazması resmî kaynaklar arasındaki bir çelişkidir ve kayıt olarak durur; **uygulama
kararı 65'tir** (§8.5/B-1). Eşik motorda **tek sabit** olarak tutulur.

**"%10 eklenir" ne demek — netleştirme.** Yönetmelik "Balthazard formülü ile %10 eklenerek"
diyor; bu **aritmetik toplama değildir**. Yani "%40 + %10 = %50" **yanlıştır**. Doğru okuma:
%10, yeni bir bileşen gibi formüle sokulur → `40 + (100 − 40) × 10 / 100 = 46`.

> **Tek sayısal örnek (yuvarlama gerektirmez):** %40 → **%46**. Bu örnek hem §5'teki açıklama
> kutusunda hem motor testinde kullanılır. Ondalıklı örnekler yalnız §6.1'deki tabloda,
> **ham değer + gösterim** olarak verilir; ikisi karıştırılmaz.

**Neden anahtar (switch) değil, iki radio?** Referans görselde tek bir "65 yaş ve üzeri" anahtarı
vardı; anahtarın kapalı hâli **sessiz bir "65 altı" kabulü** demektir ve kullanıcı hiç dokunmadan
hesaplarsa yaş kuralı sessizce uygulanmamış olur. İki radio + **varsayılansız** durum, kararı
kullanıcıya açıkça verdirir.

---

## 6. Ekran: Sonuç

```
┌──────────────────────────────────────────────────────────────┐
│  Girdiğiniz oranlar (3)                                      │
│   %40 Sağ kulak · %30 Sol göz · %10 Etiketsiz                │
│                                                              │
│                      ┌────────────┐                          │
│                      │     …      │   Bileşke oran           │
│                      └────────────┘   (hesaplama motoru)     │
│                                                              │
│  Hesaplama adımları (büyükten küçüğe)                        │
│   1) …                                                       │
│   2) …                                                       │
│   3) …                                                       │
│   Yuvarlama: …  ← motor yuvarlamaz: "uygulanmadı" (B-2)      │
│   65 yaş eki: …  ← 65+ ise uygulandı, dayanağıyla            │
│                                                              │
│  ⓘ Bu sonuç yalnızca girdiğiniz oranların bileşkesidir.      │
│    Hastalık kısıtları denetlenmemiştir.                      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ↳ Yalnız "65 yaş ve üzeri" seçiliyken görünür:              │
│  Kaynak: Erişkinler İçin Engellilik Değerlendirmesi          │
│  Hakkında Yönetmelik (Resmî Gazete 20.02.2019, sayı 30692),  │
│  Ek-2 Erişkinler İçin Engelli Sağlık Kurulu Raporları Engel  │
│  Oranları Alan Kılavuzu ve Ek-3 Balthazard formülü.          │
│                                                              │
│  [ Yeni hesaplama ]     [ Girdileri kopyala ]                │
└──────────────────────────────────────────────────────────────┘
```

Kurallar:

- **Sonuç kutusu tek bir sayıdır**; yanında "engellilik oranınız" gibi bir hüküm yazmaz.
- Adım adım döküm **motorun döndürdüğü** veridir; arayüz kendi hesabını yapmaz. Adımlar
  her zaman büyükten küçüğe sırada gösterilir (§8.2/1).
- Yuvarlama satırı motorun "uygulanmadı" bildirimini gösterir (`yuvarlama.uygulandi = false`);
  arayüz kendi hesabını yapmaz. **Gösterim kuralı §6.1'de kapandı** (en fazla 2 ondalık,
  yarı yukarı, sondaki sıfırlar atılır, Türkçe virgül); ham değer korunur ve gizlenmez.
- 65 yaş eki satırı **yalnız motor `yas_eklemesi.uygulandi = true` dediğinde** çizilir.
  Arayüz "65 yaş eki eklenmedi" gibi bir yorum **üretmez**.
- **Kaynak metni** yalnız **"65 yaş ve üzeri"** seçiliyken, **hesaplama sonucunun altında**
  gösterilir; ince bir ayırıcı çizgiyle ayrılır. Birebir aşağıdaki metin yazılır (yalnız
  satır sonları sarılır; sözcük değişmez).
- Bu metin **bir uyarı değil, kaynak künyesidir**: kırmızı kullanılmaz, ikon konmaz; gövde
  metninden bir kademe küçük ve sakin (soluk) tonda, sola hizalı, sade biçimde gösterilir.
- **"65 yaş altı" seçilirse veya liste boşalıp §3'e dönülürse** ("Tümünü sil") kaynak metni
  **gizlenir**: boş yer bırakılmaz, yerine "kaynak yok" benzeri bir ifade de yazılmaz.
- **Sonuç ve kaynak metni birlikte güncellenir:** ikisi de aynı yaş seçiminden türetilir,
  seçim değişince aynı render'da yenilenir; eski sonuç + yeni kaynak karışımı görünmez (§12.1).
- Kısıt uyarısı burada **yoktur**; yerine §2'deki kalıcı uyarı tekrar edilir.
- Sonuç, "resmî rapor" veya "kesin sonuç" olarak adlandırılmaz.

**Sonuç ekranındaki kaynak metni (birebir):**

> Kaynak: Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik (Resmî Gazete 20.02.2019, sayı 30692), Ek-2 Erişkinler İçin Engelli Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu ve Ek-3 Balthazard formülü.

**Ondalıklı örnekler:** motor ham değer döndürür, gösterim kuralı §6.1'de kapandı.
Bu yüzden ondalık örnekler iki değerle verilir (`55.11` → `55,11`); tek bir "yuvarlanmış
toplam" hiçbir yerde tek başına yazılmaz.

### 6.1 Gösterim kuralı — **kapandı** (G-1…G-4, 28.10.2026)

**Karar:** Hesap **ham** değerle yapılır; ara aşamalarda yuvarlama **yoktur**. Gösterim ise
hesaplanan değerden **ayrı** bir katmandır ve kuralları şunlardır:

| Katman | Kural |
| --- | --- |
| Motor (hesap) | Ham değer; ara adımlarda yuvarlama **yok**; `sonuc.tam_sayi_mi` ile bildirilir |
| Yaş eki | Ham bileşkeye uygulanır (§5); yuvarlanmış değere **uygulanmaz** |
| Sonuç kutusu | En fazla **2 ondalık**, **yarı yukarı** (`ROUND_HALF_UP`); tam sayıda ondalık yok; sondaki sıfırlar atılır; Türkçe virgül |
| Adım dökümü | Aynı kural (en fazla 2 ondalık); ham değer `adimlar[]` içinde **korunur** |
| Kopyalama / dışa aktarma | **Ham değer** (yuvarlanmamış); gösterim metni kopyalanmaz |

**Kapanan maddeler:**

| # | Soru | Karar |
| --- | --- | --- |
| G-1 | Kaç ondalık? | En fazla **2**; gereksiz sondaki sıfırlar atılır (`62,20 → 62,2`) |
| G-2 | Yuvarlama yönü | **Yarı yukarı** (`ROUND_HALF_UP`); kesme ve yarı çift kullanılmaz |
| G-3 | Yaş eki ile yuvarlamanın sırası | Ham bileşke → yaş eki (ham) → **tek** yuvarlama |
| G-4 | Adım dökümünde ondalık | **Gösterilir**, aynı kuralla; ham değer de taşınır |

- **Yuvarlama tek kez, yalnız sunumda**; zincirde ikinci yuvarlama yoktur.
- **Ham değer değişmez:** gösterim motora geri yazılmaz; `sonuc.deger`, `adimlar[]` ve
  `yuvarlama.uygulandi = false` aynı kalır.
- Ekran, `sonuc.tam_sayi_mi = true` ise ondalık göstermez; `false` ise **gizlemez**, 2 ondalığa
  gösterir.
- Hiçbir ekran "yaklaşık", "~" veya "en yakın tam sayı" ifadesini **kendi başına** eklemez;
  yuvarlama sessizce yapılır, ek etiket gerekmez.
- Tek uygulama yeri: `balthazard_motoru.bicimle_gosterim()` (sunum yardımcısı); Balthazard
  hesabıyla aynı modülde ama **ayrı** katmanda durur.

**Gösterim örnekleri (ham → metin):**

| Ham `sonuc.deger` | Gösterim | Not |
| --- | --- | --- |
| `40` / `46` / `58` | `40` / `46` / `58` | Tam sayıda ondalık yok (G-1) |
| `55.11` | `55,11` | İki ondalık korunur |
| `62.2` | `62,2` | Sondaki sıfır atılır |
| `59.599` | `59,6` | Yarı yukarı: `59,60` → `59,6` |
| `69.9237` | `69,92` | İki basamak |
| `82` | `82` | Tam sayı |

---

## 7. Ekran: Araç-1'den gelen oranlar

Araç-1'de "Bu oranı hesaplamaya ekle" denildiğinde:

```
┌──────────────────────────────────────────────────────────────┐
│  Engel Oranı Bul aracından 2 oran aktarıldı                  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ %40   A- Psoriasis, 4- Çok şiddetli         [düzenle][×]│  │
│  │ %30   Allojenik kemik iliği nakli, 1- …      [düzenle][×]│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ⓘ Etiketler yalnız hatırlatma içindir. Bu araç hastalığı     │
│    tanımaz, oranı doğrulamaz, kısıt denetlemez.              │
└──────────────────────────────────────────────────────────────┘
```

- Aktarılan oran **kilitli değildir**; kullanıcı düzenleyebilir ve silebilir.
- Aktarım yalnız **sayı + etiket** taşır; kayıt kimliği taşınmaz, taşınsa bile kullanılmaz.
- Aynı kayıt ikinci kez aktarılırsa: "Bu oran listede zaten var." (engellenmez)
- Etiket **prefiks** olarak gösterilir, tıklanabilir bağlantı değildir (hastalık sayfasına
  gidiş yok; Araç-2 katalogla konuşmaz).

---

## 8. Ortak motor sözleşmesi ve **doğrulanması gerekenler**

### 8.1 Sözleşme (bağlayıcı — tam metin: `ORTAK-MOTOR-SOZLESME.md`)

```
balthazard({ oranlar[], yas, yas_ekle = true }) → {
    sonuc:        {deger: sayı, tam_sayi_mi: bool},   // HAM değer
    adimlar:      [{onceki, eklenen, sonuc}],         // motor üretir, ham
    siralama:     "buyukten_kucuge",                  // kural sabit (§8.2/1)
    yuvarlama:    {uygulandi: false, kural: null},    // KAPANDI: motor yuvarlamaz (§6.1)
    yas_eklemesi: {uygulandi: bool, miktar: tam sayı, dayanak: metin}
}
```

- Tek fonksiyon; iki araç da bunu çağırır. **Kopya hesap kodu yasak.**
- Oranlar motorda **büyükten küçüğe** sıralanır; arayüz sıra bilgisi göndermez.
- `yas` **zorunlu** girdidir. 65 ve üzeri ise nihai orana %10, Balthazard ile birleştirilerek
  eklenir (§8.2/3). Yaş kontrolü arayüzde vardır (§5, §8.4).
- 65 yaş eki **yalnız bu fonksiyonun içinde** uygulanır; ekranlar ekleme yapmaz. **O-1 kararı
  gereği Araç-1 bu çağrıyı `yas_ekle=false` ile yapar ve sonucu yaş eki olmadan gösterir.**
- **Motor yuvarlamaz:** `sonuc.deger` ham değerdir; `yuvarlama.uygulandi` her zaman `false`.
  Gösterim kuralı ayrı katmandadır ve §6.1'de kapandı (G-1…G-4).
- Arayüz, motorun döndürmediği bir sayıyı **göstermez**; ham değeri yalnız `bicimle_gosterim()`
  ile metne çevirir, kendi yuvarlamasını **yapmaz**.

### 8.2 Sekiz maddenin resmî kaynakla karşılaştırılması

Durum kodları: **DOĞRULANDI** = metinde açık hüküm var · **DOĞRULANAMADI** = kaynakta hüküm
yok, tahmin yürütülmedi · **KAPANDI** = tarihli ürün kararıyla bağlandı (dayanağı yazılı).
(Bir madde kısmen açık kalırsa hangi parçasının açık olduğu yazılır.)

| # | Soru | Durum | Doğrulanmış kural | Dayanak |
| --- | --- | --- | --- | --- |
| 1 | Birleştirme sırası | **DOĞRULANDI** | "Bu oranlar **en yükseğinden başlanarak** sıraya konulur." Ek-3 notu aynı şeyi söyler: "**Her işlem sırasında büyük değer mutlaka sol dikey kenarda yer almalıdır.**" | Yönetmelik Geçici M. 2/2-b · Ek-3 notu |
| 2 | Yuvarlama: aşama, yön, basamak | **KAPANDI — 28.10.2026** (motor + gösterim) | Yönetmelikte hüküm yok. **Ek-3'ün resmî metni (RG ek dosyası, s.170) doğrudan okundu: yuvarlama hükmü yok.** Ek-3'ün bütün açıklama metni `A+B(1−A)` formülü, tablo okuma sırası, %35 + %20 = %48 örneği ve "işlem sonsuza kadar devam ettirilebilir" notundan oluşuyor; "yuvarlama", "küsurat" veya "tam sayı" ifadesi **geçmiyor**. EK-2 kılavuzunda yuvarlama **yalnız bölüm bazında**: göz (s.49, s.60: "bir üst tam sayıya"), kas-iskelet (s.92: "virgülden sonraki sayı 0,5 ve üzerinde ise bir üst… altında ise bir alt"). **s.13-26'da yok.** → **Ürün kararı: motorda ve ara aşamalarda yuvarlama yapılmaz, ham değer döner; gösterim en fazla 2 ondalık, yarı yukarı, tek kez (§6.1).** | EK-2 s.49, s.60, s.92 · Ek-3 s.170 (sessiz) |
| 3 | 65 yaş eki: kime, hangi aşamada | **KAPANDI — 65 (28.10.2026 ürün kararı)** | Madde 10/4: "**65 yaş ve üzeri** bireylerin engellilik oranına Balthazard formülü ile **%10 eklenerek**" → *aşama*: birleştirilmiş nihai orana, formülle (aritmetik +10 değil). **Kaynak çelişkisi kayıtlı:** resmî **Ek-3 (e) bendi (s.170)** "60 yaşın üzerindekilerde" diyor; uygulama kararı **65** | Yönetmelik M. 10/4 · RG 20.2.2019/30692 · Ek-3 s.170 (çelişki) |
| 4 | 65 yaş eki üst sınırı, tavan | **DOĞRULANAMADI** | Genel tavan/kırpma hükmü yok. Matematik gereği bileşke 100'ü aşmaz (Balthazard 100'e asimptotik yaklaşır) — ama bu bir **yorum**, hüküm değil. Bölüm bazlı özel tavanlar var (göz %92, s.41) — bizim bölümlerde yok | — |
| 5 | 0 ve 100 uç değerleri | **DOĞRULANAMADI** | Özel hüküm yok. Matematik: 0 etkisiz, 100 kilitler. Katalogda oran 0 gerçek bir kayıttır (`Z-056`, eski `X-Z02`; remisyonda) | — |
| 6 | Oran sayısı üst sınırı | **DOĞRULANDI — sınır yok** | Ek-3 notu: "…daha sonra bu değerle üçüncü değeri kullanarak toplam değeri bulun. **Bu işlem sonsuza kadar devam ettirilebilir.**" → yöntemde sayı sınırı yok. Arayüze yapay sınır koymak **ürün kararıdır**, mevzuat gereği değil | Ek-3 notu · Geçici M. 2/2-d |
| 7 | Aynı oranın iki kez girilmesi | **KAPANDI (ürün kararı) — 28.10.2026** | Yönetmelik, Ek-3 ve kılavuz **susuyor**. Kılavuzdaki "bir patoloji iki kez hesaplanmış olur" uyarısı (s.55) göz puanlamasına ait, girdi kuralı değil. **Karar:** tekrar **engellenmez**; her giriş hesaplamaya katılır; yalnız **bilgilendirici** uyarı gösterilir | EK-2 s.55 (ilgisiz) · ürün kararı |
| 8 | Ondalıklı oran kabulü | **KAPANDI (ürün tercihi) — 28.10.2026** | "Tam sayı olmalıdır" hükmü **yok**. Ek-3 notu oranların "ondalık karşılıkları"ndan söz eder (formülün matematiği için), giriş formatı hakkında hüküm vermez. **Karar:** ilk sürümde **tam sayı girişi**; bu bir **ürün tercihidir, mevzuat kuralı değildir** | Ek-3 (dolaylı) · EK-2 s.105 · ürün kararı |

**Özet:** 3 doğrulandı (1, 3, 6) · **3 ürün kararıyla kapandı** (2, 7, 8) · 2 hâlâ açık (4, 5).
3. maddede resmî kaynaklar çelişiyordu
(madde **65**, Ek-3 (e) **60**); **28.10.2026 ürün kararıyla 65 seçildi** (B-1 kapandı,
çelişki kayıtlı). Yaş ekinin yuvarlamaya göre sırası **B-3** de aynı kararla kapandı:
ham bileşke → yaş eki → **tek** gösterim yuvarlaması (§6.1/G-3).

#### Bu karşılaştırmanın sonuçları

1. **Sıra seçimi arayüzden kalkar.** Kural sırayı sabitliyor (büyükten küçüğe, iki ayrı
   kaynakta); kullanıcıya "girdiğim sıra" seçeneği sunmak kurala aykırı olur. §5 güncellendi.
2. **Yaş, motorun zorunlu girdisidir.** 65 yaş eki doğrulandığına göre motor yaş bilgisi
   olmadan doğru sonuç üretemez. §5'e "65 yaş ve üzeri mi?" kontrolü eklendi ve **eşik
   28.10.2026 tarihli ürün kararıyla 65 olarak kesinleşti** (M. 10/4). Ek-3 (e) bendindeki
   60 ifadesi kaynak çelişkisi olarak kayıtlıdır, uygulanmaz.
3. **Hiçbir belirsizlik ürün kararıyla sessizce kapatılmaz.** 28.10.2026'da yuvarlama (2,
   motor katmanı), tekrar eden oran (7) ve ondalık (8) **gerekçesi yazılarak** kapatıldı;
   gösterim katmanı (2'nin sunum yarısı, §6.1) ve yaş ekinin sırası (B-3) **aynı gün, ayrı
   kararla** kapatıldı. Tavan (4) ve 0/100 (5) belgelenmiş **açık** madde olarak durur.
   Hepsinin kaydı §8.5'tedir.

### 8.3 Kaynaklar (bu turda kullanılan)

| Kaynak | Künye | Kullanıldığı yer |
| --- | --- | --- |
| **Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik** | RG 20.2.2019, No. 30692 · Bakanlığın **güncel mevzuat sayfası** ve Resmî Gazete künyesiyle teyit edildi | M. 4/1-a (tanım), **M. 10/4 (65 yaş eki)**, Geçici M. 2 (algoritma, sıra) |
| **EK-2 Engelli Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu** | Projede `ek2_pages.json`, 168 sayfa (katalogun kaynağı) | Yuvarlama hükümleri: s.49, s.60, s.92; örnek: s.105; kapsam taraması: s.13-26 |
| **Ek-3 Balthazard Hesaplama Tablosu** | Yönetmelik eki. **Resmî kaynağa ulaşıldı:** RG 20.2.2019/30692 sayısının ek dosyası (`20190220-2-1.pdf`, 172 sayfa, **taranmış görüntü** — metin katmanı yok). EK-3 **tek sayfa**: s.170; s.171-172 EK-4 formu | Sayfa görüntüsü doğrudan okundu: `A+B(1−A)` formülü, "büyük değer sol dikey kenarda" kuralı, %35 + %20 = %48 örneği, "işlem sonsuza kadar devam ettirilebilir" notu, **yuvarlama hakkında sessizlik**, **(e) bendinde "60 yaşın üzerindekilerde … %10"** |
| Mülga **Özürlülük Ölçütü, Sınıflandırması ve Özürlülere Verilecek Sağlık Kurulu Raporları Hakkında Yönetmelik** | RG 30.3.2013, No. 28603 — **yürürlükten kaldırıldı** (yeni Yönetmelik M. 18) | **Geçici M. 2 (a)-(e)**; "60 yaşın üzerindekilerde … %10" bendi **bu metnin (e) bendidir**. Yürürlükteki yönetmeliğin Geçici M. 2'si ise **(a)-(d) ile biter, yaş bendi yoktur** — yaş kuralı orada yalnız M. 10/4'te (65). Ek-3'te aynı bent duruyor |

**Kapsam taraması sonucu:** s.13-26 arasındaki üç bölümde `Balthazard`, "aritmetik",
"toplanır", yuvarlama veya üst sınır ifadesi **hiç geçmiyor**. Yani bu üç bölüm için
"alan kılavuzunda aksi belirtilmedikçe" istisnası devreye girmez; genel kural geçerlidir.
(DERİ'de yalnız iki kayıt düzeyi notu var: s.16 yıllık kontrol, s.19 "yüz ve ele lokalize
lezyonlar için ayrıca %5 eklenir" — ikincisinin aritmetik mi Balthazard mı olduğu
belirtilmemiştir; tek hastalık oranını ilgilendirir, motorun bileşke adımını değil.)

**Sınır:** Yönetmelik metni bakanlığın güncel mevzuat sayfası ve RG künyesiyle teyit edildi.
Ek-3, Resmî Gazete'nin kendi ek dosyasından alındı; dosya **taranmış görüntü** olduğu için
metin katmanı yok, sayfa görüntüsü okunarak incelendi (tek sayfa, s.170). Bu turda
**yuvarlama sorusu kesin olarak kapandı: Ek-3'te yuvarlama hükmü yok.** Yaş bendi de
kesinleşti: **Ek-3 "60" diyor, madde "65" diyor.** Bu çelişki **28.10.2026 tarihli ürün
kararıyla 65 lehine** kapatıldı; Ek-3'ün 60 ifadesi kaynak çelişkisi olarak §8.5/B-1'de duruyor.

### 8.4 Yaş kuralı — kesin: 65 yaş (28.10.2026 ürün kararı)

65 yaş eki doğrulandığı hâlde iki araçta da yaş sorulmuyordu. Araç-2'ye **"65 yaş ve üzeri
mi?"** kontrolü eklendi (§5). Seçenekler değerlendirildi:

| Seçenek | Sonuç |
| --- | --- |
| (a) Araç-2'de "65 yaş ve üzeri mi?" kontrolü | **Seçildi** — en küçük değişiklik; Araç-1'den gelen oranlarda da geçerli |
| (b) Doğum yılı, eşik motor içinde | Fazladan alan; şimdilik gerekmiyor |
| (c) Yaş sorulmaz, ek uygulanmaz | **Yanlış** — doğrulanmış kuralı sessizce atlar |

**Karar (28.10.2026):** eşik **65 yaş ve üzeri**; orana **%10 Balthazard formülüyle** eklenir,
doğrudan 10 puan eklenmez. Dayanak: M. 10/4 (RG 20.02.2019, 30692). Resmî kaynaklar
arasındaki çelişki (Ek-3 (e) bendi "60 yaşın üzerindekilerde") **bilinerek** kayda geçirildi;
uygulama 65'tir. Yaş ekinin yuvarlamaya göre sırası **hâlâ açık** (B-3) — bu karar onu
kapatmaz. Eşik motorda **tek sabit** olarak tutulur.

### 8.5 Belirsizlik kaydı — kapatma kuralı

Bu maddeler **varsayımla doldurulmaz**. Her biri ya resmî metinle ya da **tarih ve gerekçesi
yazılmış açık ürün kararıyla** kapanır; kapanan karar bu tabloya işlenir.
**Durum (28.10.2026): B-1, B-2 (motor + gösterim), B-3, B-6, B-7 kapandı;
B-4, B-5, B-8 açık.**

| ID | Konu | Ne bilinmiyor | Neden kritik | Durum / yapılmayacak |
| --- | --- | --- | --- | --- |
| B-1 | Yaş eşiği (65 ↔ 60) | **KAPANDI — 28.10.2026, ürün kararı.** Uygulama: **65 yaş ve üzeri**; %10, **Balthazard formülüyle** eklenir (doğrudan +10 değil). Dayanak: **Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik, M. 10/4 (RG 20.02.2019, sayı 30692).** **Kaynak çelişkisi kayıtlı:** aynı Yönetmeliğin **Ek-3 (e) bendi (s.170)** "60 yaşın üzerindekilerde" diyor; mülga 2013 metninin Geçici 2/e bendi de 60'tı, yürürlükteki Geçici 2 ise (a)-(d) ile bitiyor | 60-64 yaş aralığı bu nedenle karara bağlandı | **Karar verildi: 65.** 60'a dönülmez; eşik motorda tek sabit. Değişiklik ancak **yeni tarihli bir kararla** yapılır |
| B-2 | Yuvarlama | **KAPANDI — 28.10.2026 (motor + gösterim).** Motor **ham** değer döndürür, ara aşamalarda yuvarlama **yapmaz**. Gösterim: en fazla 2 ondalık, yarı yukarı, tek kez (§6.1, G-1…G-4) | Ham değer korunur; sunum kararı hesaplanan değeri değiştirmez | `yuvarlama.uygulandi = false`; biçimlendirme yalnız `bicimle_gosterim()` |
| B-3 | Yaş ekinin sırası | **KAPANDI — 28.10.2026 (§6.1/G-3).** Ham bileşke → yaş eki (ham) → tek gösterim yuvarlaması | Yuvarlanmış değere yaş eki uygulanırsa sonuç 1 puan oynayabilir | Sıra motorda sabit: yaş eki ham değere uygulanır, yuvarlama en sonda |
| B-4 | Tavan / 100 aşımı | Kırpma hükmü yok | Pratikte ulaşılmaz ama kural yok | **AÇIK.** Kırpma kuralı uydurulmaz |
| B-5 | 0 ve 100 | Özel davranış tanımlı değil | 0 gerçek kayıt (`Z-056`, eski `X-Z02`), 100 sınır | **AÇIK.** Özel işlem eklenmez |
| B-6 | Aynı oranın tekrarı | **KAPANDI — 28.10.2026, ürün kararı.** Mevzuat susuyor | Bileşkeyi şişirebilir | **Engelleme yok; her giriş hesaplamaya katılır.** Yalnız bilgilendirici uyarı (onay istemez, engellemez) |
| B-7 | Ondalıklı giriş | **KAPANDI — 28.10.2026, ürün tercihi (mevzuat kuralı değil).** İlk sürümde tam sayı | Sonucu doğrudan değiştirir | Maske tam sayıya kilitli; **gerekçe ürün tercihi**. Ondalık ancak yeni kararla açılır |
| B-8 | DERİ s.19 "ayrıca %5 eklenir" | Aritmetik mi, Balthazard mı | Yanlış yöntem yanlış oran üretir | **AÇIK.** Kataloğa ve motora **eklenmedi**; yalnız not olarak duruyor (X-D03 belirsizde) |

**Kayıt kuralı:** B-1…B-8'den biri kapandığında satır silinmez; "kapandı + tarih + dayanak"
olarak işaretlenir. Sessizce koda gömülmesi yasaktır.

---

## 9. Kenar durumlar

| Durum | Davranış |
| --- | --- |
| Tek oran girildi | Hesapla aktif; sonuç = o oran (motor ne döndürürse) |
| Hiç oran yok | Hesapla pasif, "En az bir oran girin." |
| **Yaş aralığı seçilmedi (varsayılan)** | Hesapla pasif, "Yaş aralığını seçin." Varsayılan seçim yapılmaz |
| **"65 yaş altı" seçili + Hesapla** | Sonuç 65 eki olmadan gösterilir; kaynak künyesi **görünmez** |
| **"65 yaş ve üzeri" seçili + Hesapla** | %10 Balthazard formülüyle eklenir; sonucun altında kaynak künyesi görünür (§6) |
| **Sonuç görünürken yaş seçimi değişti** | Sonuç ve kaynak metni **aynı anda** yeniden hesaplanır; eski sonuç + yeni kaynak karışımı görünmez (§12.1) |
| Tüm oranlar 0 | Hesapla aktif; sonuç motorun döndürdüğü değer; uyarı yok |
| 100 var | Onay istenir (§4) |
| **Aynı oran iki kez girildi** | **Engellenmez**; her iki giriş de hesaplanır; bilgilendirici uyarı görünür (B-6) |
| **Ondalıklı değer girildi** | Reddedilir: "Oran tam sayı olmalıdır." — **ürün tercihi**, mevzuat kuralı değil (B-7) |
| **Sonuç ondalıklı çıktı** | Gizlenmez; en fazla **2 ondalık**, yarı yukarı, Türkçe virgül ile gösterilir (`55.11 → 55,11`); ham değer korunur (§6.1) |
| Çok sayıda oran | Liste kaydırılır; yöntemde üst sınır yok (§8.2/6) |
| Sayfa yenilendi | Girdiler **saklanmaz** (varsayılan); kalıcılık istenirse ayrı karar |
| Araç-1 sekmesine dönüş | Liste korunur (aynı oturum) |

---

## 10. Metin sözlüğü

| Yer | Metin |
| --- | --- |
| Kalıcı uyarı | "Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım kuralları burada denetlenmez." |
| Kısıt sınırı | "Hastalığa ve mevzuata özgü kısıtlar bu araçta doğrulanamaz. Bunlar için 'Engel Oranı Bul' aracına bakın." |
| Sonuç etiketi | "Bileşke oran" |
| Sonuç altı not | "Bu sonuç yalnızca girdiğiniz oranların bileşkesidir. Hastalık kısıtları denetlenmemiştir." |
| Alt bilgi | "Bu araç bilgilendirme amaçlıdır. Resmî engelli sağlık kurulu raporu yerine geçmez." |
| Aktarım notu | "Etiketler yalnız hatırlatma içindir. Bu araç hastalığı tanımaz, oranı doğrulamaz." |
| Yaş seçenekleri | "( ) 65 yaş altı   ( ) 65 yaş ve üzeri" — **varsayılan seçim yok** |
| Hesapla pasif (oran yok) | "En az bir oran girin." |
| Hesapla pasif (yaş yok) | "Yaş aralığını seçin." |
| **Boş / geçersiz oran** | "Bir oran girin." · "Oran 0 ile 100 arasında olmalıdır." |
| **Ondalıklı giriş reddi** (B-7) | "Oran tam sayı olmalıdır." — *ürün tercihi; mevzuat kuralı değil* |
| **Tekrar eden oran uyarısı** (B-6) | "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir." — bilgi, onay istemez |
| **0 oranı eklendi** | "0 oranı listeye eklendi. Bileşkeyi değiştirmez." |
| **100 oranı onayı** | "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?" |
| **Yuvarlama satırı** (B-2) | "Yuvarlama: uygulanmadı (motor ham değer döndürür)." — motor `yuvarlama.uygulandi = false` dediği sürece sabit |
| **Gösterim kuralı** (G-1…G-4) | *Ek metin gerekmez:* yuvarlama sessizce uygulanır (en fazla 2 ondalık, yarı yukarı, sondaki sıfırlar atılır, Türkçe virgül). "yaklaşık", "~", "en yakın tam sayı" **yazılmaz** (§6.1) |
| Kaynak künyesi (yalnız 65+) | "Kaynak: Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik (Resmî Gazete 20.02.2019, sayı 30692), Ek-2 Erişkinler İçin Engelli Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu ve Ek-3 Balthazard formülü." |

**Yasak ibareler** (hiçbir ekranda geçmez):

- "çalışma gücü kaybı oranı" / "çalışma gücü kaybınız"
- "kesin engellilik oranınız" / "engellilik oranınız hesaplandı"
- "maluliyet oranı"
- "resmî raporunuz" / "bu sonuç rapor yerine geçer"
- Sonucu teşhis veya hukuki hüküm gibi sunan her ifade

**Kavram sınırı:** engellilik oranı, EK-2 oranlarının bileşkesidir. Çalışma gücü kaybı
değerlendirmesi **ayrı bir hukuki süreçtir**; bu araçlar onu hesaplamaz, onunla eşitlenemez
ve sonuç ekranında bu ayrım yazılı olarak korunur.

---

## 11. Bu taslakta yapılmayanlar

- Kod, bileşen, API — yok.
- Formül adımları ve sıra kuralı **doğrulandı** (§8.2); **65 yaş eşiği 28.10.2026 ürün
  kararıyla kesinleşti** (§8.5/B-1). **Yuvarlama tamamen kapandı:** motor ham değer döndürür,
  ara aşamada yuvarlama yok (B-2); **gösterim en fazla 2 ondalık, yarı yukarı, tek kez**
  (§6.1, G-1…G-4). Ondalıklı örnekler ham değer + gösterim olarak verilir.
- Belirsizlik tablosunun **28.10.2026 son durumu**: B-1, B-2 (motor + gösterim), B-3, B-6, B-7
  **kapandı**; **B-4, B-5, B-8 açık**. Hiçbiri varsayımla kapatılmadı; kayıt §8.5'te.
- DERİ s.19'daki "ayrıca %5" notu **kataloğa ve motora eklenmedi** (§8.5/B-8, X-D03).
- Katalog verisi, oran, kısıt değişmedi; Araç-2 kataloğu **okumaz**.
- Hastalık arama, tanı seçimi, seviye seçimi bu araçta **yok**.
- İmla düzeltme listesi uygulanmadı.

---

## 12. Uygulamaya aktarımda doğrulanacaklar

Bu belge koda dönüşürken aşağıdakiler **tek tek** doğrulanır; biri geçmezse aktarım
tamamlanmış sayılmaz.

### 12.1 Yaş seçimi — sonuç ve kaynak metni birlikte güncellenir

Sonuç **yalnız "Hesapla" ile** üretilir (canlı hesap bu araçta yoktur; canlı hesap **Engel Oranı
Bul** aracının davranışıdır). Buna karşılık yaş seçimi, sonuç ve kaynak künyesi **tek bir
durumdan** türetilir; hiçbiri diğerinden bağımsız çizilemez. Yaş seçimi değiştiğinde sonuç ve
kaynak metni **aynı render'da** yenilenir; arada "eski sonuç + yeni kaynak" veya tersi görünmez.

| # | Adım | Beklenen davranış |
| --- | --- | --- |
| 1 | "65 yaş altı" seçilip Hesapla'ya basılır | Sonuç 65 eki uygulanmadan gösterilir; kaynak metni **çizilmez** |
| 2 | "65 yaş ve üzeri" seçilip Hesapla'ya basılır | Sonuç 65 ekiyle (Balthazard) gösterilir; kaynak metni **aynı render'da** sonucun altında çizilir |
| 3 | Sonuç görünürken "65 altı" → "65 yaş ve üzeri" | Sonuç 65 ekiyle **yeniden hesaplanır**; kaynak metni **aynı anda** görünür |
| 4 | Sonuç görünürken "65 yaş ve üzeri" → "65 altı" | Sonuç, 65 eki uygulanmadan yeniden hesaplanır; kaynak metni **aynı anda** kaybolur |
| 5 | Liste boşalır ("Tümünü sil", §3'e dönüş) | Sonuç alanı ve kaynak metni **birlikte** temizlenir; Hesapla yeniden pasif |
| 6 | Sonuç sayısal olarak değişmese bile (örn. tüm oranlar 0) | Kaynak metni **yine** seçime uyar; "sonuç değişmedi" diye metin bırakılmaz |
| 7 | Hızlı ardışık değişim (hızlı seçim değiştirme, çift tıklama) | Son görünen durum tutarlı: sonuç ve metin **aynı** seçime ait; ara durum ekranda kalmaz |

**Ek kurallar:**

- Kaynak metni **hesaplanan değere bağlanmaz** ("sonuç > 0 ise göster" gibi bir koşul
  yazılmaz). Tek koşulu yaş seçimidir.
- Yaş seçimi değişince kullanıcıdan **tekrar Hesapla'ya basması beklenmez**; 3 ve 4. maddeler
  bu yüzden "yeniden hesaplanır" der. Aksi hâlde ekranda eski sonuç + yeni kaynak (veya tersi)
  kalır ve bu belge ihlal edilmiş olur.
- Oran ekleme/silme/düzenleme **sonucu kendiliğinden yenilemez**; bunun için Hesapla gerekir.
  Yaş seçimi bu kuralın tek istisnasıdır ve istisna bilinçlidir.

### 12.2 Girdi değişti ama Hesapla'ya basılmadı — "sonuç eski" durumu

Sonuç bir kez üretildikten sonra kullanıcı oran ekler/siler/düzenlerse, ekranda **eski sonuç**
kalır. Bu durum sessiz bırakılmaz:

| Durum | Gösterim |
| --- | --- |
| Sonuç görünürken liste değişti | Sonuç kutusunun üstünde `⚠ Bu sonuç önceki girdilere ait. Güncellemek için "Hesapla"ya basın.` |
| Sonuç görünürken liste boşaldı | Sonuç ve kaynak metni **birlikte** temizlenir, §3 boş duruma dönülür |
| "Hesapla"ya basıldı | Uyarı kalkar, sonuç ve kaynak metni aynı render'da yenilenir |
| Yaş seçimi değişti | **Uyarı çıkmaz**; sonuç ve kaynak metni anında yenilenir (§12.1) |

- Eski sonuç **soluklaştırılmaz veya gizlenmez** (kullanıcı karşılaştırma yapabilsin), ama
  güncel sanılmaması için uyarı zorunludur.
- Uyarı metni **"sonuç geçersiz"** demez; yalnız "güncel değil" der. Hesap hatası ima edilmez.

### 12.3 Gösterim kuralı — aktarımda doğrulanacaklar (G-1…G-4)

| # | Kontrol | Beklenen |
| --- | --- | --- |
| 1 | Sonuç kutusu biçimi | `55.11 → 55,11` · `62.2 → 62,2` · `59.599 → 59,6` · `69.9237 → 69,92` |
| 2 | Tam sayı sonuç | `40 → 40` (ondalık ve virgül **yok**) |
| 3 | Yuvarlama yönü | `55.115 → 55,12` (yarı yukarı; kesme değil) |
| 4 | Yuvarlama sayısı | Tek kez: ham bileşke → yaş eki → gösterim; ara adımda yuvarlama yok |
| 5 | Ham değer | `sonuc.deger` ve `adimlar[]` gösterimden sonra **değişmemiş** |
| 6 | Kopyala / dışa aktar | Ham değeri taşır (`59.599`), `59,6` metnini değil |
| 7 | Biçimlendirme yeri | Yalnız `bicimle_gosterim()`; ekranlarda `round()`, `toFixed`, `f"{…:.2f}"` benzeri **yok** |

---

## 13. Referans görselden alınanlar / alınmayanlar

Görsel (Engelliler.biz kaynaklı Balthazard ekranı) **yalnız tasarım referansıdır**; birebir
kopyalanmadı, oradaki metin ve oranlar doğru kabul edilmedi.

**Alınanlar:**

| Fikir | Nasıl uygulanır |
| --- | --- |
| Tek ekranda giriş + sonuç | Giriş, liste ve sonuç aynı sayfada; ayrı "sonuç sayfası" yok (§3, §5, §6) |
| "+ Oran ekle" ile çoğaltma | §5: `[ + Oran ekle ]`; satır bazında `[düzenle] [×]` |
| Sonuçta formülün gösterilmesi | §6 "Hesaplama adımları" + §3.1 "Nasıl hesaplanır?" kartı |
| Kısa, sade yönlendirme metinleri | §10 metin sözlüğü; uzun paragraf yok |
| Yaş seçeneğinin sonuç altında kaynak göstermesi | §6: kaynak künyesi yalnız "65 yaş ve üzeri" seçiliyken |

**Alınmayanlar:**

| Fikir | Neden alınmadı |
| --- | --- |
| Oran girişinde **kaydırıcı (slider)** | 0-100 arası hassas giriş için sayı alanı daha hızlı ve erişilebilir; slider tek başına tam sayı seçimini zorlaştırır, mobilde yanlış dokunmaya açık |
| Boşken **%0 gösteren büyük halka** | Hesap yapılmadan sonuç varmış izlenimi verir; nötr boş durum kullanılır |
| **"65 yaş ve üzeri" anahtarı (switch)** | Kapalı hâli sessiz "65 altı" kabulü olur; iki varsayılansız radio kullanılır (§5) |
| Dev gradyan başlık / rozet şeridi | Engelli.me'nin sade tasarımıyla uyumsuz; mobilde dikey yer kaybı |
| Görseldeki örnek oranların birebir aktarılması | Doğrulanmamış; yalnız `%40 → %46` (yaş eki) kullanılır |
