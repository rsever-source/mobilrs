# Araç-1 Veri Sözleşmesi ve Ekran Akışı

Sürüm: 0.3-taslak · Tarih: 28.10.2026 · Durum: **uygulama öncesi son**
Kapsam: Ruh Sağlığı (Z), Deri (D), Hematoloji (H) — EK-2 s.13-26

> **0.3 değişikliği (karar uygulaması):** O-1 ve O-2 **kapandı**; O-3 kaynak araştırmasıyla
> kısmen doğrulandı, JSON'a dokunulmadı. Araç-1 yaş hesabı yapmaz (§3.8). Eski "12" rakamı
> tarihsel nota dönüştü (§3.3).
>
> **0.2 değişikliği:** 11 belirsiz kayıt kesin kataloğa aktarıldı (276 kesin / 10 belirsiz);
> belirsiz kayıt mesajı güncellendi. Oranlar ve kısıtlar değişmedi.

Bu belge **kod içermez**. Amaç, Araç-1'in katalog verisiyle nasıl konuşacağını ve ekranda
neyi nasıl göstereceğini bağlayıcı biçimde tanımlamak.

---

## 1. İki araç — ayrım (temel kabul)

| | **Araç-1: Oran Bul** | **Araç-2: Balthazard Hesapla** |
| --- | --- | --- |
| Kullanıcı girdisi | hastalık + seviye seçimi | **elle girilen oranlar** |
| Veri kaynağı | katalog (286 satırın 276 kesin kaydı) | yok |
| Ne üretir | mevzuattaki tek oran | oranların bileşkesi |
| Kısıt denetimi | **evet** | **hayır** — gösterilemez, uyarı zorunlu |
| Hastalık bilgisi | var | **yok** (yalnız sayı) |
| 65 yaş eki | **uygulanmaz**; bilgi olarak açıklanır (§3.8) | **uygulanır** (tek nokta: motor) |

**Değişmez kurallar:**

1. Araç-2 hiçbir zaman "bu hastalığa şu oran verilir" demez. Yalnız girilen sayıları birleştirir.
2. Araç-1'in ürettiği oran, **çalışma gücü kaybı oranı değildir**; EK-2'de hastalık ve şiddet
   seviyesi karşılığı olarak tanımlanmış orandır. İki kavram hiçbir ekranda eşitlenmez.
3. Araç-1'in çıktısı ile Araç-2'nin çıktısı **aynı hukuki sonuç** gibi sunulmaz: biri bileşen,
   diğeri bileşkedir.
4. İki araç **aynı hesaplama motorunu** kullanır: `balthazard()` + yuvarlama + 65 yaş eki.
   65 yaş eki **tek uygulama noktasında** uygulanır; hiçbir ekran kendi ekini hesaplamaz.

---

## 2. Veri sözleşmesi

### 2.1 Kaynak dosyalar — salt okunur

| Dosya | Rol | Yazma |
| --- | --- | --- |
| `katalog_taslak.json` | **276 kesin kayıt** | **hayır** |
| `belirsiz.json` | 21 satır (11 `cozuldu`, 10 `belirsiz`) | **hayır** |

`belirsiz.json` içindeki `cozuldu` satırlar **tarihsel iz**tir: kataloğa aktarılmışlardır,
arama sonucu olarak **gösterilmezler**. Yalnız `durum: "belirsiz"` olan 10 satır §3.5'e girer.

Uygulama açılışta okur, bellekte tutar. Katalog çalışma zamanında **hiçbir koşulda** yazılmaz;
türetilmiş alanlar dosyaya eklenmez.

### 2.2 Kullanılan alanlar

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

### 2.3 Türetilmiş (bellekte, dosyaya yazılmaz)

| Türetim | Kural |
| --- | --- |
| `arama_metni` | `hastalik` + `alt_tur`, küçük harf, Türkçe `İ→i`, `I→ı`, aksan katlama |
| `baslik` | `hastalik` başındaki `V- ` / `VI- A. ` gibi numaralandırma ayrılır; ekranda rozet olarak gösterilir |
| `hastalik_ayrac` | 64 kayıtta `hastalik` alanı `«grup başlığı — alt madde»` biçimindedir; `—` solundaki kısım hastalık adı, sağındaki kısım **seviye etiketi**dir |
| `seviye_etiketi` | öncelik sırası: `alt_tur` başındaki `1-`/`a-`/`2.` → yoksa `hastalik_ayrac` sağ tarafı → yoksa "tek oran" |
| `grup_anahtari` | `bolum` + (`grup` varsa `grup`) + `hastalik_ayrac` sol tarafı |

### 2.4 Korunması zorunlu değişmezler

Yükleme anında doğrulanır; biri bozulursa uygulama **açılmaz**, hata verir:

- `kayitlar` = 276, `belirsiz` (durum=belirsiz) = 10, toplam = 286
- bölüm dağılımı: Z 56 / D 142 / H 78
- tüm `oran` değerleri tam sayı ve 0 ≤ `oran` ≤ 100
- `(hastalik, alt_tur)` çifti **tekil** (bugün 0 çakışma)
- her kayıtta `id`, `bolum`, `hastalik`, `oran`, `sayfa` dolu
- katalogda `X-` kimliği **yok**; 11 çözülen kayıt `Z-055/Z-056`, `D-139…D-142`, `H-074…H-078`
  kimlikleriyle **bir kez** bulunur

---

## 3. Ekran akışı

```
[1] Bölüm seçimi / arama
        │
        ├── arama metni girildi ──► sonuç listesi (bölüm ön filtresi uygulanır)
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
          [6] 65 yaş bilgi bloğu       ← ayrı blok, oranı DEĞİŞTİRMEZ (§3.8)
                │
          [7] "Hesaplamaya ekle" ──► Araç-2 (yalnız id + oran + kısa etiket)
```

### 3.1 Hastalık arama

- Arar: `hastalik` + `alt_tur` (türetilmiş `arama_metni`).
- Türkçe duyarsız: `psoriazis` ≈ `psoriasis`, `işitme`/`isitme` eşleşir.
- Numaralandırma aramayı engellemez: `VI` veya `A` yazınca başlık rozetleri de taranır.
- Sonuç satırında: hastalık adı, seviye etiketi, oran, bölüm rozeti.
- **Boş sonuç ≠ hata.** §5'teki belirsiz/veri yok durumları ayrı mesajla gösterilir.

### 3.2 Bölüm / grup ve seviye seçimi

| Düzey | Z ve H | DERİ |
| --- | --- | --- |
| 1 | Bölüm (3 seçenek) | Bölüm |
| 2 | Roma başlığı (I…VI / I…X) | `grup` (15) |
| 3 | Hastalık | Hastalık |
| 4 | Seviye | Seviye |

Z ve H'de `grup` alanı yok — bu bir eksik değil, kaynakta o düzeyin bulunmamasıdır.

### 3.3 Tek kayıtlı grupta seviye adımı atlanır

**9** hastalık grubu tek kayıtlıdır. Bu sayı 28.10.2026'da 276 kayıt üzerinden yeniden
hesaplanmış ve **ürün kararıyla kabul edilmiştir (O-2)**. Eski belgelerdeki **"12"** rakamı
güncel veriyle yeniden üretilemediği için **tarihsel not** olarak yalnız burada anılır; hiçbir
kural, test veya ekran metni bu sayıya dayanmaz.

Bu gruplarda **[4] adımı hiç gösterilmez**; hastalık seçilince doğrudan [5] sonuç ekranı açılır.
Kullanıcıya "tek seviye" ibaresi gösterilir, seçim yaptırılmaz.

Ölçüt: `bolum` + (`grup` varsa `grup`) + `hastalik` ayracının **sol** tarafı aynı olan hastalık
grubunda tek kayıt. Bugünkü liste: D-013, D-014, D-017, D-049, D-062, D-075, D-086, D-134,
H-056. (Z bölümünde tek kayıtlı grup yoktur.)

### 3.4 Seviyesi olmayan kayıtlar

6 kayıtta `alt_tur` yerine `—` vardır: D-013, D-014, D-017, D-062, H-056, H-065.
Bunlar **iki farklı durumdur**, aynı davranmazlar:

**(a) Tek kayıtlı grupta `—` — 5 kayıt** (D-013, D-014, D-017, D-062, H-056)

- Seviye adımı zaten yok (§3.3); doğrudan sonuç.
- Not: "Bu hastalıkta kaynak tek oran veriyor, şiddet basamağı yok."

**(b) Çok kayıtlı grupta `—` — 1 kayıt** (H-065)

H-065, `VIII- Kronik nötropeniler` grubunun 3 kaydından biridir ve seviyesi `alt_tur`'da değil,
`hastalik` metnindedir: `VIII- Kronik nötropeniler — 1- Ağır (Kostmann sendromu)`.
Bu grupta seviye listesi şöyle kurulur:

| Kayıt | Seviye etiketi (kaynak) |
| --- | --- |
| H-065 | `1- Ağır (Kostmann sendromu)` ← `hastalik` ayracının sağı |
| H-066 | `Sık ve ağır enfeksiyon geçirmesine neden olmayan vakalar` ← `alt_tur` |
| H-067 | `Sık ve ağır enfeksiyon geçirmesine neden olan vakalar` ← `alt_tur` |

**Genel kural:** `—` **hiçbir koşulda ekranda gösterilmez**. Seviye etiketi üç kaynaktan
sırayla alınır: `alt_tur` → `hastalik` ayracının sağı → "tek oran". Hiçbiri yoksa seviye adımı
atlanır. Veri **değiştirilmez**; ekran `—` değerini yutar, seviye yokmuş gibi davranmaz —
varsa etiketi başka yerden bulur.

> Bu davranış, `alt_tur` alanının "resmî metindeki ifade" sözleşmesiyle çelişmez; `—` bir ifade
> değildir. Alanın isteğe bağlı tanımlanması ayrı bir şema kararıdır (bkz. §8).

### 3.5 Belirsiz kayıtlar (10)

`belirsiz.json` 21 satır içerir; **11'i `cozuldu`** olarak işaretlenip kesin kataloğa aktarılmıştır.
Araç-1 yalnız `durum: "belirsiz"` olan **10 satırı** bu bölümün kapsamına alır:

| # | Bölüm | Oran | Sayfa | Sorun tipi |
| --- | --- | --- | --- | --- |
| X-Z03 | Z | 40 | 14 | `coklu_kosul_tek_oran` (III-b/III-c seçim kuralı yok) |
| X-Z04 | Z | 70 | 14 | aynı |
| X-D01 | D | 15 | 18 | `ekleme_kurali` ("ayrıca"nın yöntemi yok) |
| X-D02 | D | 15 | 18 | aynı + bozuk ifade |
| X-D03 | D | 5 | 19 | `ekleme_kurali` (NOT (a) +%5 yöntemi, NOT (b) kapsamı) |
| X-D04 | D | 10 | 19 | aynı |
| X-D05 | D | 20 | 19 | aynı (albinizm kapsamı) |
| X-D06 | D | 40 | 19 | primer hastalıkla birlikte kullanım |
| X-H02 | H | 40 | 23 | Fanconi hiyerarşisi |
| X-H03 | H | 80 | 23 | aynı |

Bu kayıtlar Araç-1 sonuç listesinde **oran olarak sunulmaz**, ama kullanıcı boş sonuçla
bırakılmaz. Arama bu hastalıklardan birine denk geldiğinde:

> **"Kaynakta bu hastalık için tek bir oran belirlenmemiştir. Bu nedenle burada oran
> hesaplanamaz; değerlendirme için ilgili uzman hekime başvurulmalıdır."**
>
> Kaynak notu (EK-2 s.<sayfa>): bu satır birden fazla klinik durumu tek orana bağlıyor ya da
> bir ekleme kuralına tabi.
> *Belirsiz kayıt: X-D03 — inceleme notu: "NOT (a) yüz ve ele lokalize lezyonlar için ayrıca
> %5 eklenmesini öngörüyor; bu ek bağımsız hastalık oranı değil ve uygulama yöntemi
> (tek mi, bölge başına mı) belirtilmemiş."*

- `X-*` kayıtlarında `oran` alanı **gösterilmez** (teknik olarak dolu olsa bile).
- **`durum: cozuldu` satırlar arama sonucu değildir**; kataloğa aktarılan karşılıkları
  (Z-055, Z-056, D-139…D-142, H-074…H-078) normal kayıt olarak döner. Aynı hastalık için
  hem çözülmüş iz hem belirsiz satır gösterilmez.
- Kullanıcıya "bulunamadı" denmez; kaynağın sınırlaması açıklanır. Fark önemlidir.
- Mesaj teşhis veya kesin tıbbi yönlendirme içermez; yalnız kaynak sınırlamasını ve
  uzman hekime başvuru gereğini belirtir.
- Kesinleştirme, tahmin veya birleştirme **yapılmaz**.

### 3.6 Kısıtların gösterilmesi

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

Toplam **228** kısıt kaydı vardır; **182** kayıt en az bir kısıt taşır, **94** kayıt kısıtsızdır.
Sayımlar 28.10.2026 aktarımından sonra yeniden alınmıştır (276 kayıt üzerinden).

`R-VERGI` ve `R-REMISYON` **sonucu doğrudan etkiler** (oran kullanılamaz / verilmez);
bu ikisi diğerlerinden görsel olarak ayrılmalı (kırmızı, sonuç bloğunun içinde).

### 3.6.1 Bölüm düzeyi not — kayıt kısıtı değil

Yalnız **Hematoloji** bölümü seçildiğinde, sonuç alanının altında, kayıt kısıtlarından görsel
olarak ayrı (nötr/gri) bir **bölüm notu** gösterilir. Kaynağın ifadesi birebir kullanılır:

> **Bölüm notu (kaynak s.26):** "Hastalığın aktivasyonunda ilerleme veya gerileme ihtimali olan
> hastalarda raporun geçerlilik süresi belirtilmelidir."

Kurallar:

- Bu not **78 hematoloji kaydının tamamına uygulanmış bir kısıt gibi gösterilmez**.
- "Bölüm notu" etiketi taşır; `R-*` kodu ile karışmaz, kısıt sayısına eklenmez.
- Kaynağın anlamı daraltılmaz: "sadece nakil hastaları için" ifadesi **eklenmez**.
- 6 nakil kaydında (H-068…H-073) ayrıca `R-NAKIL` kayıt kısıtı görünür. İkisi çelişmez:
  biri kayıt düzeyi, diğeri bölüm düzeyi bilgidir; aynı anda gösterilir.

### 3.7 Oran bulunduğunda sonraki adım

Sonuç ekranı şunları taşır: hastalık adı, seviye, **oran**, kaynak (EK-2 s.<sayfa>), kısıtlar.

- **"Hesaplamaya ekle"** → Araç-2'ye yalnız `{id, oran, kisa_etiket}` aktarılır.
- Araç-2 bu etiketi yalnız liste başlığı olarak gösterir; **hastalık bilgisi taşımaz, kısıt
  denetlemez**. Arayüz bunu açıkça yazar:

> "Bu araç yalnızca girdiğiniz oranları birleştirir. Oranların doğruluğu ve kullanım
> kısıtları burada denetlenmez."

- Aynı hastalık iki kez eklenirse uyarı verilir (çift sayım riski), engellenmez.

### 3.8 65 yaş kuralı — Araç-1'de gösterim (**KAPANDI — 28.10.2026, ürün kararı O-1**)

**Karar (O-1):** Araç-1 **EK-2 temel oranını yaş eklemesi olmadan** gösterir ve **otomatik yaş
hesabı yapmaz**. 65 yaş ve üzeri için %10 ek oran kuralı **ayrı ve nötr bir bilgi bloğunda**
açıklanır. Gösterilen oran, "EK-2'de bu hastalık ve seviye için tanımlı oran"dır.
65 yaş eklemesi yalnız **Araç-2'de** (bileşke üzerinden) uygulanır.

Gerekçe: Araç-1 tek bileşen gösterir; bileşene yaş eki eklemek "nihai oran" izlenimi verir ve
§1'deki "çalışma gücü kaybı oranı değildir" ilkesini zedeler.

Sonuç ekranında, oranın **altında**, orandan görsel olarak ayrılmış nötr bir bilgi bloğu
(gri/bilgi ikonu, kırmızı değil) gösterilir:

> **65 yaş ve üzeri için ek oran**
> Mevzuata göre 65 yaş ve üzerindeki bireylerin engellilik oranına Balthazard formülü ile
> **%10** eklenir. Bu ek, yukarıdaki orana düz toplama ile eklenmez; Araç-2'de diğer oranlarla
> birlikte Balthazard yöntemiyle hesaplanır.
> Örnek: %40 → %46.

Kurallar:

- Blok **her sonuçta** görünür (kullanıcının yaşı sorulmaz, varsayım yapılmaz); yalnız
  "65 yaş ve üzeriyseniz" koşuluyla çerçevelenir.
- Blok **oranı değiştirmez**; ekranda "nihai oranınız" hesabı yapılmaz.
- Blok içinde "Hesaplamaya ekle" ile %10 **otomatik aktarılmaz**; kullanıcı Araç-2'de yaş
  seçeneğini kendisi işaretler (bkz. `ORTAK-MOTOR-SOZLESME.md` §4).
- Araç-1 motoru çağırırken **`yas_ekle = false`** gönderir; motor ek uygulamaz, sonuç EK-2 temel
  oranı olarak döner. Böylece tek hesap kodu korunur, Araç-1 kendi hesabını yapmaz
  (`ORTAK-MOTOR-SOZLESME.md` §2).
- Kaynak künyesi bu blokta verilir: 20.02.2019 tarihli ve 30692 sayılı Resmî Gazete'de
  yayımlanan *Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik* (m. 10/4).
  **Künye çelişkisi** (JSON `meta` 31275 diyor) §8/O-3'te açık bırakılmıştır.

---

## 4. Araç-2 sınırı

- Girdi: 0-100 arası sayı listesi (+ isteğe bağlı etiket) **ve yaş seçimi** (varsayılansız).
- Çıktı: bileşke oran, adım adım Balthazard zinciri, 65 yaş eki (tek noktada).
- 65 yaş eki, yaş seçeneği **açıkça işaretlenmeden** uygulanmaz ve hesaplama başlatılamaz.
- Yapmaz: hastalık → oran eşlemesi, kısıt denetimi, seviye seçimi, "bu oran doğru mu" yorumu.
- Ekranın üstünde kalıcı uyarı: kısıtlar denetlenmiyor.
- Ayrıntılı sözleşme: `ORTAK-MOTOR-SOZLESME.md`.

---

## 5. Durum matrisi (kullanıcı ne görür)

| Durum | Adet | Gösterim |
| --- | --- | --- |
| Çok kayıtlı grupta normal kayıt | 266 | seviye listesi + oran |
| Çok kayıtlı grupta `alt_tur = "—"` (H-065) | 1 | seviye etiketi `hastalik` ayracından gelir |
| Tek kayıtlı grup | 9 | seviye adımı yok, doğrudan oran; 5'inde "şiddet basamağı yok" notu |
| **Kesin toplam** | **276** | |
| Kısıtlı kayıt (üsttekiyle kesişir) | 182 | oran + kısıt uyarıları |
| Belirsiz kayıt (`durum: belirsiz`) | 10 | oran gösterilmez, belirsiz kayıt mesajı (§3.5) |
| Çözülmüş iz (`durum: cozuldu`) | 11 | **arama sonucu değil**; kataloğa aktarılmış karşılığı döner |
| Kapsam dışı bölüm | — | "bu bölüm henüz eklenmedi" (oran uydurulmaz) |
| 65 yaş bilgi bloğu | 276 sonucun tamamı | ayrı blok, oranı değiştirmez (§3.8) |

Toplam satır kontrolü: 266 + 1 + 9 = **276** kesin; 276 + 10 belirsiz = **286** kaynak satırı.

---

## 6. Terminoloji (arayüz metinleri)

| Kavram | Doğru kullanım | Yasak |
| --- | --- | --- |
| Katalog `oran` | "EK-2'de bu hastalık ve seviye için tanımlı oran" | "çalışma gücü kaybı oranı" |
| Balthazard sonucu | "oranların bileşkesi" | "kesin engellilik oranınız" |
| Çalışma gücü kaybı | ayrı bir değerlendirme; bu araçların konusu değil | eşanlamlı kullanım |

Her iki aracın altında kalıcı not:

> Bu araçlar bilgilendirme amaçlıdır; resmî engelli sağlık kurulu raporu yerine geçmez.
> Oranlar EK-2 kılavuzundan alınmıştır. Çalışma gücü kaybı değerlendirmesi ayrı bir
> hukuki süreçtir ve bu oranlarla eşitlenemez.

---

## 7. Kabul kriterleri

1. **276** kesin kaydın tamamı arama ile bulunabilir; hiçbiri ulaşılamaz değil.
2. Aynı `(hastalik, alt_tur)` iki farklı oran döndürmez.
3. **9** tek kayıtlı grupta seviye adımı görünmez.
4. 6 `—` kaydında ekranda `—` karakteri **hiç** görünmez; H-065'in seviye etiketi
   `hastalik` ayracından (`1- Ağır (Kostmann sendromu)`) gelir.
5. **10** belirsiz kayıtta oran gösterilmez, uyarı gösterilir; **11** `cozuldu` satırı
   arama sonucu olarak dönmez, katalog karşılığı döner.
6. `R-VERGI` bulunan **34** kayıtta sonuç "vergi indiriminde kullanılamaz" uyarısıyla gelir.
7. Araç-2, kısıt denetlemediğini her zaman yazar.
8. Katalog dosyaları uygulama çalışırken değişmez (mtime sabit kalır).
9. Hiçbir ekranda "çalışma gücü kaybı oranı" ibaresi geçmez.
10. Araç-1 sonucunda **65 yaş bilgi bloğu** görünür ve gösterilen oran **yaş eklenmemiş**
    EK-2 oranıdır; "nihai oran" ifadesi geçmez.
11. Araç-2'de yaş seçimi yapılmadan hesaplama **etkinleşmez**; hiçbir yaş seçeneği
    varsayılan işaretli değildir.
12. Katalog dosyalarının MD5 değerleri `katalog_taslak.json` `B77AEF76A1310DE4AE93E703183E2A09`
    ve `belirsiz.json` `89AE83AAFFF9D6541B75D4073FC1BE82` ile aynı kalır.

---

## 8. Karar durumu

**Ürün kararları — 28.10.2026:**

| # | Konu | Durum | Sonuç |
| --- | --- | --- | --- |
| O-1 | **Araç-1 65 yaş gösterimi** | **KAPANDI** | Araç-1 EK-2 temel oranını **yaş eklemesi olmadan** gösterir; **otomatik yaş hesabı yapmaz**; %10 kuralı ayrı ve nötr bilgi bloğunda açıklanır (§3.8) |
| O-2 | **Tek kayıtlı grup sayısı** | **KAPANDI** | **9** kabul edildi (D-013, D-014, D-017, D-049, D-062, D-075, D-086, D-134, H-056). Eski "12" **tarihsel not** olarak kalır (§3.3) |
| O-3 | **Künye çelişkisi (30692 ↔ 31275)** | **AÇIK — kısmen doğrulandı** | JSON `meta` **değiştirilmedi**. 30692 resmî kaynaklarla doğrulandı; 31275'in 15.10.2020 RG olduğu ve bu Yönetmelikle **ilgisiz** olduğu gösterildi; ancak JSON'a bu sayının **nasıl girdiği** izlenemiyor → düzeltme ayrı onay (ayrıntı: §8.1) |

### 8.1 O-3 kaynak araştırması

| Sav | Kaynak | Sonuç |
| --- | --- | --- |
| **30692 = 20.02.2019**, *Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik* | Sağlık Bakanlığı **e-Rapor kullanıcı kılavuzu**: "30692 sayılı Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik — Resmî Gazete Sayısı: 30692, 20.02.2019"; KHK Genelge 2019/0; MEB/üniversite duyuruları | **DOĞRULANDI** |
| Aynı tarihte *Çocuklar İçin Özel Gereksinim Değerlendirmesi Hakkında Yönetmelik* de 30692'de yayımlandı | Genelge ve kurum duyuruları | **DOĞRULANDI** |
| Yönetmelik 30.03.2013 / 28603 sayılı Özürlülük Ölçütü Yönetmeliğini yürürlükten kaldırdı | Yönetmelik m. 18; kurum açıklamaları | **DOĞRULANDI** |
| **31275 = 15.10.2020** RG içeriği: MEB Eğitim Kurumları Sosyal Etkinlikler Yönetmeliği değişikliği, Veri Depolama Kuruluşu Yönetmeliği değişikliği, Bursa Uludağ Üniv. TÖMER Yönetmeliği + andlaşma/CB kararı | Resmî Gazete fihristleri (15.10.2020 / 31275) | **DOĞRULANDI — engellilik yönetmeliğiyle ilgisi yok** |
| 31275'in engellilik yönetmeliğine **değişiklik** getirdiği | — | **DOĞRULANAMADI** (böyle bir değişiklik kaydı bulunamadı) |
| JSON `meta`'ya 31275'in nasıl girdiği | — | **DOĞRULANAMADI** (kaynak izi yok) |

**Sonuç:** Belgelerde **20.02.2019 / 30692** kullanılır. JSON `meta.kaynak` alanı **bilinçli
olarak değiştirilmedi**; düzeltme, veri dosyasına dokunma yetkisi verildiğinde ayrı işlemle
yapılır. "31275" alanı bu turda **açık** kalır.

**Mevzuat/şema kaynaklı, bloklamayan:**

1. **Hematoloji NOT kapsamı** — s.26 NOT'u 6 nakil kaydına mı, 78 kaydın tamamına mı?
   (Ayrı rapor; veri değiştirilmedi. §3.6.1 bugünkü gösterim kararı.)
2. **`alt_tur` şema sözleşmesi** — alan isteğe bağlı mı ilan edilecek, `—` kaldırılacak mı?
   (Şu an ekran `—`'yı yutuyor; veri değişikliği gerekmiyor.)
3. **`kisit` tipi** — sözleşmede "liste" olarak yazılmalı (metin değil). Bugün 7 kod, 228 kayıt.
4. **72 imla/biçim kalemi** — bloklamıyor; tek partide uygulanabilir.
5. **A-1…A-6 belirsiz kayıt maddeleri** — X-D03 hâlâ açık (NOT (a) +%5 yöntemi ve NOT (b)
   kapsamı). Bağlayıcı Bakanlık görüşü/genelge olmadan kapatılmaz.

---

## 9. Kapsam dışı

- Kod, arayüz, dağıtım (deploy) — bu turda yok.
- Katalog verisi, oranlar, hesaplama mantığı değişmez.
- Göz, işitme, konuşma, kas-iskelet bölümleri eklenmez.
- Balthazard motorunun kendisi (formül, yuvarlama, 65 yaş eki) bu belgenin konusu değil;
  yalnız "tek motor, tek uygulama noktası" sınırı bağlayıcıdır. Gösterim kuralı da ortak
  motorda tanımlıdır (`ORTAK-MOTOR-SOZLESME.md` §7.2); Araç-1 kendi biçimlendirmesini yapmaz.
