# Ek-2 katalog taslağı — okubeni

Bu klasör, engelli raporu hesaplama aracı için **veri taslağı** içerir. Balthazard motoru,
doğrulanmış EK-3 tablosu ve yuvarlama kuralı bu turda **değiştirilmedi**; burada yalnız
"hastalık seç → oran" eşlemesi için katalog verisi vardır.

> **28.10.2026 ek:** Klasörde artık **onaylı ortak motor** ve **Araç-2 ekran prototipi** de
> var (`balthazard_motoru.py`, `test_balthazard_motoru.py` = 77 test; `arac2/` = ekran +
> sunucu + 11 test). Katalog JSON'ları **değişmedi**; motor/ekran depoya **eklenmedi**, canlı
> uygulamaya bağlanmadı.

Kapsam üç bölümdür: **ZİHİNSEL/RUHSAL/DAVRANIŞSAL**, **DERİ**, **HEMATOLOJİK**.
Göz, işitme, konuşma ve kas-iskelet tabloları bu turda **kapsam dışıdır** (ayrı hesaplayıcılar).

## Dosyalar

| Dosya | İçerik |
| --- | --- |
| `katalog_taslak.json` | `meta` + `kurallar` + **276 kesin kayıt** (`kayitlar`) |
| `belirsiz.json` | **21 satır**: 11'i `cozuldu` (kesin kataloğa aktarıldı), **10'u belirsiz** |
| `OKUBENI.md` | bu açıklama |

> **Son durum (28.10.2026):** 11 kayıt kesin kataloğa aktarıldı (bkz. §"Çözülen 11 kayıt").
> `belirsiz.json` satırları **silinmedi**; çözülenler `durum: cozuldu` + `cozum_tarihi` +
> `kaynak_sayfa` ile işaretlendi (izlenebilirlik).

Kaynak: resmî **EK-2 Engelli Sağlık Kurulu Raporu Alan Kılavuzu** (20.02.2019 tarihli
*Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik*, RG **30692** eki), basılı
sayfa 13-26. Her kayıt resmî sayfa metniyle karşılaştırıldı.

> **Künye notu:** JSON `meta.kaynak` alanında hâlâ "Mevzuat No **31275**" yazıyor. 28.10.2026
> kontrolünde **31275'in 15.10.2020 tarihli** bir Resmî Gazete olduğu ve bu Yönetmelikle
> bağlantısının **doğrulanamadığı** görüldü; doğrulanan künye **20.02.2019 / 30692**.
> Veri dosyasına dokunulmadı; düzeltme ayrı onayla yapılır (bkz. §Künye notu, son bölüm).

## Sayılar

| Bölüm | Sayfa | Toplam satır | Kesin | Belirsiz |
| --- | --- | --- | --- | --- |
| ZİHİNSEL, RUHSAL, DAVRANIŞSAL | 13-15 | 58 | 56 | 2 |
| DERİ | 16-22 | 148 | 142 | 6 |
| HEMATOLOJİK | 23-26 | 80 | 78 | 2 |
| **Toplam** | 13-26 | **286** | **276** | **10** |

Sayfa bazında kesin kayıt dağılımı:

| Sayfa | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kayıt | 22 | 16 | 18 | 5 | 27 | 21 | 21 | 28 | 25 | 15 | 21 | 26 | 27 | 4 |

## Kayıt alanları

`id`, `bolum`, `hastalik`, `alt_tur`, `oran`, `sayfa`, `kisit` (varsa), `kaynak_not` (varsa).
DERİ kayıtlarında ek olarak `grup` (resmî ana başlık numarası; tam adı `meta.grup_adlari`).

- `oran` her kayıtta **tek tam sayıdır**. Bu üç bölümde satır başına tek oran vardır; oran aralığı
  yoktur. Aralıklar yalnız **kriter** olarak geçer (IQ 70-80, Hb 8-10 g/dl, faktör aktivitesi %2-5,
  vücut yüzeyi %20-49 gibi) ve `alt_tur` içinde metin olarak korunur.
- `id` numaraları bölüm içinde **kesintisizdir** (Z-001…Z-056, D-001…D-142, H-001…H-078).
  **İlk dağıtımda** (Z-001…Z-054, D-001…D-138, H-001…H-073) numaralar resmî sayfa sırasını
  izler; sonradan eklenen 11 kayıt mevcut kimlikler yeniden numaralandırılmadan **bölüm sonuna**
  eklenmiştir. Bu nedenle eklenen blokta sayfa sırası bölümün tamamı için geçerli değildir
  (`meta.id_kurali`). Belirsiz satırlar bu dosyada yer almaz; `belirsiz.json` içinde
  X-Z##/X-D##/X-H## kimlikleriyle **ayrı bir dizide** tutulur.

## Kullanım kısıtı kodları

| Kod | Anlam | Sayfa | Kapsam |
| --- | --- | --- | --- |
| `R-YILLIK` | Talep hâlinde oranlar yıllık kontrollerle tekrar değerlendirilir | 16 | tüm DERİ (142) |
| `R-GECICI` | 1 yıl sonra kontrol; geçici fonksiyon kaybı, bir yıl sonra kesin karar | 14 | s.14-15 (34) |
| `R-VERGI` | İş başvurusu ve vergi indiriminde bu derecelendirme dikkate alınmaz | 15 | s.14-15 (34) |
| `R-REMISYON` | Remisyondaki yineleyen depresif bozukluğa oran verilmez | 14 | III-b, III-c (4) |
| `R-NAKIL` | Aktivasyon/gerileme ihtimali varsa rapor geçerlilik süresi belirtilir | 26 | allojenik/otolog nakil (6) |
| `R-IKTIYOZ` | Alt tip ayrılmaz; şiddet grup bütünü için belirlenir | 20 | iktiyozis grubu (4) |
| `R-EKTO` | Alt tip ayrılmaz; şiddet grup bütünü için belirlenir | 21 | ektodermal displazi (4) |

> **Hematoloji bölüm notu:** `R-NAKIL` yalnız 6 nakil kaydına (H-068…H-073) bağlıdır. Kaynak
> s.26'daki NOT kayıt bazlı bir kısıt değildir ve 78 hematoloji kaydının tamamına uygulanmış
> sayılmaz. Bölüm düzeyinde, kaynağın ifadesiyle gösterilir:
> “Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali olan hastalarda raporun geçerlilik
> süresi belirtilmelidir.”

Kısıt kodları **oranı değiştirmez**; veri modelinde oranla birlikte taşınır ki hesaplayıcı
"bu oran bu amaçla kullanılamaz / bir yıl sonra yenilenir" uyarısını gösterebilsin.

## Hastalık seçeneği sayılmayanlar

Bunlar katalogda kayıt değildir; hesap motoruna oran olarak girmez:

1. **Bölüm ve alt başlıklar.** Ör. "VI- Yaygın gelişimsel bozukluklar", "X- İmmun, otoimmun ve
   sistemik hastalıkların deri bulguları", "VI-A Benign neoplazm ve hiperplaziler". Başlıklar
   yalnız gruplama/arama için kullanılır.
2. **TABLO 1 — Hastalık şiddeti değerlendirme tablosu (s.16).** Hafif/orta/şiddetli/çok şiddetli
   tanımları oran değil **kriter** metnidir. Arayüzde şiddet seçiminin yardım metni olarak
   kullanılmalıdır.
3. **Tek başına ölçüm aralıkları** (IQ bantları, Hb eşikleri, faktör aktivitesi, kaplanan vücut
   yüzeyi). Bunlar aynı kaydın `alt_tur` metnidir, ayrı seçenek değildir.
4. **Ekleme kuralları.** DERİ'de iki "ayrıca … 15" satırı ve pigment bozukluklarındaki
   "ayrıca %5" NOT'u bağımsız oran değildir; `belirsiz.json` içinde `ekleme_kurali` olarak ayrı
   tutuldu, Balthazard zincirine sokulmaması gerekir.
5. **NOT'lar.** Remisyon (s.14), vergi indirimi + yıllık değerlendirme (s.15), iktiyozis grup
   bütünü (s.20), ektodermal displazi grup bütünü (s.21), nakilde rapor süresi (s.26) ve
   otizm dipnotu (s.13) ilgili kayıtlara kısıt kodu veya `kaynak_not` olarak bağlandı.
6. **s.16 giriş hükümleri.** Deri tümörleri ve eritroderma dışında, deri hastalığına eşlik eden
   hastalık/komplikasyonların ayrıca değerlendirilmesi kuralı oran değildir.

## Belirsiz satırlar — 21 satırın 10'u açık

`belirsiz.json` 21 satırı **korumaya devam eder**; 11 satır `durum: cozuldu` olarak işaretlendi
ve kesin kataloğa aktarıldı. Aşağıdaki tablo **hâlâ açık olan 10 satırı** gösterir. Hiçbiri
tahminle düzeltilmedi; oran ve metin kaynaktaki hâliyle korundu.

| # | Bölüm | Satır | Oran | Sayfa | Sorun |
| --- | --- | --- | --- | --- | --- |
| X-Z03 | ZİHİNSEL | III-c) kısmen düzelen | 40 | 14 | III-b (20) ↔ III-c (40) seçim kuralı metinde yok (A-5) |
| X-Z04 | ZİHİNSEL | III-c) düzelmeyen | 70 | 14 | aynı (A-5) |
| X-D01 | DERİ | saçlı deri/yüz >yarısı (kan damarları) | 15 | 18 | "ayrıca"nın yöntemi yok: ek mi, yerine mi (A-3) |
| X-D02 | DERİ | saçlı deri/yüz >yarısı (skar-keloid) | 15 | 18 | aynı + bozuk ifade (A-3) |
| X-D03 | DERİ | pigment %20-50 | 5 | 19 | NOT (a) +%5 yöntemi ve NOT (b) kapsamı (A-1, A-2) |
| X-D04 | DERİ | pigment %50-100 | 10 | 19 | aynı (A-1, A-2) |
| X-D05 | DERİ | pigment — albinizm | 20 | 19 | aynı; albinizme uygulanıp uygulanmadığı (A-1, A-2) |
| X-D06 | DERİ | eritroderma | 40 | 19 | primer hastalıkla birlikte kullanım kuralı `R-PRIMER` kodunu gerektiriyor |
| X-H02 | HEMA | Fanconi — transfüzyonsuz | 40 | 23 | 4. maddenin 1-3 ile hiyerarşisi (A-4) |
| X-H03 | HEMA | Fanconi — transfüzyonlu | 80 | 23 | aynı (A-4) |

### Çözülen 11 kayıt (kesin kataloğa aktarıldı)

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

Gerekçeler ve kaynak sayfaları `BELIRSIZ-COZUM-RAPORU.md`, şema kontrolü ve uygulama paketi
`KATALOG-SON-KONTROL.md` içindedir. Katalogda **11'i tekrar eklenmez**.

## Açık ve kapanmış konular

**Durum kodları:** KAPANDI = kaynak metinle çözüldü · AÇIK = bağlayıcı açıklama/ürün kararı bekliyor.

| # | Konu | Durum | Not |
| --- | --- | --- | --- |
| 1 | **Fanconi hiyerarşisi (s.23)** — 4. madde 1-3 basamaklarının yerine mi geçiyor? | **AÇIK** (A-4) | X-H02/X-H03 belirsizde; oran 40↔70↔80 oynuyor |
| 2 | **NHL numaralandırma atlaması (s.25)** — 4'ten 6'ya atlıyor | **KAPANDI** | Kayıt düzeyinde oran açık → **H-078** (`kaynak_not` ile) |
| 3 | **Otizm çift "d)" (s.13)** | **KAPANDI** | Oran–tanı eşleşmesi tek anlamlı → **Z-055** (`kaynak_not` ile) |
| 4 | **KTCL evre birleştirmeleri (s.21)** | **KAPANDI** | Evre adları metinde yazılı → **D-141** (IIB, III → 40), **D-142** (IVA, IVB → 60) |
| 5 | **Pigment NOT'ları (s.19)** — +%5'in yöntemi, NOT (b)'nin kapsamı | **AÇIK** (A-1, A-2) | X-D03…X-D05 belirsizde; `R-BASKAH` kodu yok |
| 6 | **Eritroderma (s.19)** — primer hastalıkla birlikte kullanım | **AÇIK** | X-D06 belirsizde; `R-PRIMER` kodu yok |
| 7 | **`0lanlar` yazım hatası (s.23)** | **KAPANDI** | Anlam bozulmuyor → H-019 `kaynak_not` ile |
| 8 | **III-c ile III-b farkı (s.14)** | **KISMEN** (A-5) | Oran farkı çelişki değil, ayrı başlık; b/c seçim kuralı metinde yok → X-Z03/X-Z04 belirsizde |
| 9 | **DERİ şiddet ölçütü** — TABLO 1 (s.16) | **BİLGİ** | Tablo oran değil kriter; arayüzde yardım metni olarak kullanılır |

A-1…A-4 için **bağlayıcı açıklama** (Bakanlık görüşü/genelge/uzman kurul kararı) gerekir; metin
içi karşılaştırmayla kapanmaz. A-5/A-6 klinik sınıflama sorularıdır (uzman görüşü).
Ayrıntı: `BELIRSIZ-COZUM-RAPORU.md` §6.

## Doğrulama

- **Sayım:** iki bağımsız yöntemle yapıldı (resmî sayfa metninden elle sayım; docx akışından
  otomatik çıkarım). Toplamlar uyuştu: 286 satır = 58 + 148 + 80.
- **Aktarım sonrası kontrol (28.10.2026):** 276 kesin + 10 belirsiz = 286; bölüm toplamları
  58/148/80 korundu; kimlikler kesintisiz (Z-056, D-142, H-078); `(hastalik, alt_tur)` tekrarı 0;
  tüm `oran` tam sayı ve 0-100; DERİ'de 142/142 `grup` + `R-YILLIK`; yalnız mevcut 7 kısıt kodu
  kullanılıyor. Eski 265 kayıt **birebir** değişmedi.
- **Sayfa etiketleri:** otomatik çıkarımın sayfa etiketleri ZİHİNSEL bölümünde 12 satır kaydığı
  için sayfa alanları resmî basılı sayfa numarasından alındı.
- **Oran dizisi karşılaştırması:** her sayfa için kaynak metinden çıkarılan oran listesi ile
  katalog + belirsiz dosyasındaki oranlar karşılaştırıldı; 14 sayfanın 12'si birebir eşit.
  İki fark, kaynakta oranın **tek başına satırda** durduğu iki yerden kaynaklanır
  (s.19 eritroderma 40; s.21 KTCL 3. madde 40). Bunlardan s.21 kaydı çözülüp **D-141** olarak
  kataloğa girdi; **X-D06 (eritroderma)** belirsizde kaldı.
- **Oran aralığı yok:** üç bölümde hiçbir satırda oran aralığı bulunmadığı ayrıca kontrol edildi;
  aralıklar yalnız kriter metinlerinde geçiyor.

## Künye notu (doğrulanmadı → doğrulandı → O-3 açık)

Bu dosyanın önceki sürümü kaynağı "**3.1.2019** tarihli Yönetmelik eki, **Mevzuat No 31275**"
diye yazıyordu. 28.10.2026 kontrolünde:

- **20.02.2019 / 30692** künyesi, "Erişkinler İçin Engellilik Değerlendirmesi Hakkında
  Yönetmelik"in Resmî Gazete künyesi olarak **birden fazla resmî/kurumsal sayfada doğrulandı**
  (Sağlık Bakanlığı e-Rapor kullanıcı kılavuzu, genelge, kurum duyuruları);
  M. 10/4'ün "65 yaş ve üzeri … Balthazard formülü ile %10" ifadesi de bu metinde geçiyor.
  Aynı sayıda *Çocuklar İçin Özel Gereksinim Değerlendirmesi Hakkında Yönetmelik* de yayımlandı.
- **31275** sayısı **15.10.2020** tarihli Resmî Gazete'ye karşılık geliyor. O gün yayımlanan
  yönetmelikler (MEB Eğitim Kurumları Sosyal Etkinlikler Yönetmeliğinde değişiklik, Veri Depolama
  Kuruluşu Yönetmeliğinde değişiklik, Bursa Uludağ Üniv. TÖMER Yönetmeliği) **engellilik
  değerlendirmesiyle ilgili değil**. Bu Yönetmeliğe **değişiklik getirdiğine dair kayıt bulunamadı**.

**Açık kalan nokta (O-3):** 31275'in JSON `meta` alanına **nasıl girdiği izlenemiyor**; kaynak
izi yok. Bu yüzden katalog JSON'unun `meta` alanındaki künye **değiştirilmedi** (veri dosyasına
dokunulmadı); düzeltme istenirse ayrı onayla yapılır. Ayrıntılı kaynak tablosu:
`ARAC-1-SOZLESME.md` §8.1.

## Sınırlar

- Bu turda **kod yazılmadı**, proje kaynak dosyaları değiştirilmedi, commit/push/build/deploy
  yapılmadı. Dosyalar yalnız geçici çalışma klasöründedir.
- Katalog hesap motoruna bağlanmadı; Balthazard zinciri, EK-3 tablosu ve yuvarlama kuralı
  olduğu gibi bırakıldı.
- Göz, işitme, konuşma ve kas-iskelet tabloları bilinçli olarak eklenmedi.
