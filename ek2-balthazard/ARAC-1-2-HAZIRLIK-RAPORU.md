# Araç-1 ve Araç-2 — Hazırlık Raporu

Tarih: 28.10.2026 · Durum: **hazırlık belgeleri son hâlinde — uygulama kodu için onay bekliyor**
Kapsam: Analiz ve hazırlık **belgeleri**. Kod, build, deploy **yok**.
Veri: `katalog_taslak.json` **276 kesin kayıt** · `belirsiz.json` **21 satır (11 çözüldü / 10 belirsiz)** · toplam **286**

---

## 0. Görseller görüldü mü?

**Evet.** İki ekran görüntüsü bu oturumda **görüldü ve incelendi**:

- **Görsel 1 — Balthazard ekranı:** boşken `%0` gösteren büyük halka, oran için **kaydırıcı +
  sayı alanı**, "+ Engel Oranı Ekle" butonu, "65 yaş ve üzeri" **anahtarı (switch)**,
  `A + (100 − A) × B ÷ 100` formül kartı, 4 adımlı anlatım.
- **Görsel 2 — Engel oranı bulma ekranı:** arama alanı, **19 kategori çipi**, "Seçtikleriniz"
  özet paneli, **anatomi figürü**, boşken `%0` halka, "Listeyi temizle" bağlantısı.

Görseller **yalnız tasarım/kullanım referansı** olarak değerlendirildi; **birebir kopyalanmadı**
(kullanıcı talimatı). Görsellerdeki metin ve oranlar **resmî kaynak doğrulaması olmadan doğru
kabul edilmedi**; tasarım fikri ile mevzuat/veri doğruluğu ayrı tutuldu.

---

## 0.1 Karar tutanağı — 28.10.2026 (kullanıcı kararları uygulandı)

Bu bölüm, kullanıcının 28.10.2026 tarihli kararlarının **hangi belgeye nasıl işlendiğini**
kaydeder. Kod yazılmadı; yalnız belgeler güncellendi.

| ID | Karar | Durum | İşlendiği yer |
| --- | --- | --- | --- |
| **O-1** | Araç-1 EK-2 **temel oranını** yaş eklemesi olmadan gösterir; %10 kuralı **ayrı ve nötr bilgi bloğunda** açıklanır; **otomatik yaş hesabı yok** | **KAPANDI** | `ARAC-1-SOZLESME.md` §3.8 · `ARAC-1-WIREFRAME.md` §4.1 · `ORTAK-MOTOR-SOZLESME.md` §1/§4 (`yas_ekle=false`) · `ARAC-2-WIREFRAME.md` §8.1 |
| **O-2** | Güncel veriyle doğrulanan **9** tek kayıtlı grup kabul; eski **12** yalnız **tarihsel not** | **KAPANDI** | `ARAC-1-SOZLESME.md` §3.3 + §8 · `ARAC-1-WIREFRAME.md` başlık notu · `OKUBENI.md` |
| **O-3** | Resmî doğrulama olmadan JSON künyesi **değişmez**; 30692 ↔ 31275 farkı kaynaklarıyla araştırılır; doğrulanamayan nokta **açık** kalır | **KISMEN DOĞRULANDI / AÇIK** | `ARAC-1-SOZLESME.md` §8 + §8.1 (kaynak tablosu) · `OKUBENI.md` künye notu · **JSON `meta` değişmedi** |
| **B-2** | Motor **ham değer** döndürür, ara aşamada yuvarlama yok; **gösterim** kuralı ayrı katman | **KAPANDI (motor + gösterim)** | `ORTAK-MOTOR-SOZLESME.md` §3/§7 · `ARAC-2-WIREFRAME.md` §6.1 + §8.1 |
| **B-3** | Yaş eki **ham bileşkeye** uygulanır; yuvarlama en sonda **tek kez** | **KAPANDI** | `ORTAK-MOTOR-SOZLESME.md` §4/§7.2 · `ARAC-2-WIREFRAME.md` §6.1/G-3 · §10 ek karar |
| **G-1…G-4** | Sonuç ve adım dökümü: en fazla **2 ondalık**, **yarı yukarı**, tam sayıda ondalık yok, sondaki sıfırlar atılır, Türkçe virgül; yuvarlama **tek kez ve yalnız sunumda**; ham değer korunur | **KAPANDI** | `ORTAK-MOTOR-SOZLESME.md` §7.2/§9.1 · `ARAC-2-WIREFRAME.md` §6.1 + §12.3 · §10 ek karar |
| **B-6** | Aynı oranın tekrarı **engellenmez**; bilgilendirici uyarı; **her giriş** hesaba katılır | **KAPANDI** | `ARAC-2-WIREFRAME.md` §4 + §8.5/B-6 + §10 · `ORTAK-MOTOR-SOZLESME.md` §5 |
| **B-7** | İlk sürümde **tam sayı** girişi — **mevzuat kuralı değil, ürün tercihi** | **KAPANDI** | `ARAC-2-WIREFRAME.md` §4 + §8.2/8 + §8.5/B-7 · `ORTAK-MOTOR-SOZLESME.md` §5 |
| **B-4, B-5, B-8** | Tahminle kapatılmaz; **DERİ +%5** katalog veya motora **eklenmez** | **AÇIK** | `ARAC-2-WIREFRAME.md` §8.5 · `ARAC-1-SOZLESME.md` §3.5 (X-D03) |
| **Görseller** | Tasarım kararları korunur, **birebir kopya yok** | **Korundu** | §3.1–§3.3 · `ARAC-1-WIREFRAME.md` §11 · `ARAC-2-WIREFRAME.md` §13 |

**Karara bağlanmayan, açık kalan noktalar:** B-4 (tavan/kırpma), B-5 (0 ve 100 davranışı),
B-8 (DERİ +%5 yöntemi, X-D03), O-3'ün "31275 JSON'a nasıl girdi" izi, A-1…A-6 (belirsiz
10 kayıt), hematoloji NOT kapsamı, `alt_tur`/`kisit` şema sözleşmesi ve 72 imla kalemi.
(G-1…G-4 **28.10.2026 ek kararıyla kapandı** — bkz. §10.)

---

## 1. Değişen dosyalar ve nedenleri

| Dosya | Durum | Neden |
| --- | --- | --- |
| `OKUBENI.md` | güncellendi | 265/21 → **276/10** sayıları; sayfa dağılımı; yeni `id_kurali`; kısıt sayıları; 10 açık + 11 çözülen tablo; açık/kapanmış konular; künye notu (30692 + 31275 araştırması); doğrulama |
| `ARAC-1-SOZLESME.md` | güncellendi (**0.3**) | O-1/O-2/O-3 kararları işlendi (§3.8, §3.3, §8 + §8.1 kaynak araştırması); 276/10 verisi; belirsiz 10 kayıt tablosu; kısıt sayıları; durum matrisi; kabul kriterleri |
| `ARAC-1-WIREFRAME.md` | güncellendi (**0.3**) | bölüm sayıları 56/142/78; belirsiz örneği X-D09 → **X-D03**; 65 yaş **bilgi bloğu** (O-1: yaş hesabı yok, §4.1); görsellerden alınan/alınmayanlar (§11) |
| `ARAC-2-WIREFRAME.md` | güncellendi (**0.3**) | B-2/B-3 motor–gösterim ayrımı (§6.1, G-1…G-4); B-6/B-7 kapanışı (§4, §8.5); §8.2 tablosu; §10 metin sözlüğü; §11 durum; `%40 → %46`; `Z-056`; radio modeli; §12.2; §13 |
| `ORTAK-MOTOR-SOZLESME.md` | **yeni → 0.2** | `balthazard()` girdi/çıktı sözleşmesi, `yas_ekle`, hata/uyarı kodları, yaş kuralı, sıralama, **ham değer** yuvarlama politikası, yuvarlama gerektirmeyen test vektörleri |
| `ARAC-1-2-HAZIRLIK-RAPORU.md` | **yeni → bu sürüm** | Karar tutanağı (§0.1), çelişki tablosu, görsel değerlendirmesi, akışlar, güncel açık kararlar, doğrulama, onay isteği |
| `YARIN-DEVAM.md` | başına uyarı eklendi | Eski sayı/hash'ler geçersiz; tarihsel kayıt olarak korundu |
| `katalog_taslak.json` | **değişmedi** | MD5 `B77AEF76A1310DE4AE93E703183E2A09` |
| `belirsiz.json` | **değişmedi** | MD5 `89AE83AAFFF9D6541B75D4073FC1BE82` |
| `BELIRSIZ-COZUM-RAPORU.md`, `KATALOG-SON-KONTROL.md` | **değişmedi** | Bu turun konusu değil |

---

## 2. Belgeler arası çelişkiler (tespit + durum)

| # | Çelişki | Tespit | Bu turda ne yapıldı |
| --- | --- | --- | --- |
| Ç-1 | **Tek kayıtlı grup sayısı 12 ↔ 9** | Eski belgeler "12 hastalık grubu tek kayıtlı" diyordu. Yeni veriyle (276 kayıt, `bolum + grup + hastalik ayrac solu` anahtarı) **9** çıkıyor. Eski 12 rakamı **yeniden üretilemedi** | **O-2 kapandı (28.10.2026):** belgeler **9**; 12 yalnız **tarihsel not** olarak duruyor, hiçbir kural ona dayanmıyor |
| Ç-2 | **Künye 31275 ↔ 30692** | JSON `meta.kaynak` "3.1.2019 … Mevzuat No 31275" diyor. Doğrulanan künye: **20.02.2019 / 30692**. **31275 = 15.10.2020** tarihli RG; o gün yayımlanan yönetmelikler (MEB sosyal etkinlikler değişikliği, Veri Depolama, Uludağ Üniv. TÖMER) bu Yönetmelikle **ilgisiz** | Belgeler **30692** kullanıyor; JSON `meta` **değiştirilmedi** → **O-3 açık** (ayrıntı: `ARAC-1-SOZLESME.md` §8.1) |
| Ç-3 | **Kısıt sayıları** (138/33/33/3 → 142/34/34/4) | 11 kayıt eklendikten sonra eski sayılar geçersizdi | Yeniden sayıldı: R-YILLIK 142, R-GECICI 34, R-VERGI 34, R-REMISYON 4, R-NAKIL 6, R-IKTIYOZ 4, R-EKTO 4 |
| Ç-4 | **Belirsiz örneği X-D09** | X-D09 artık `cozuldu`, katalogda **D-141** | Wireframe örneği **X-D03** yapıldı (hâlâ açık) |
| Ç-5 | **"%10 eklenir" ifadesi** | İki farklı okumaya açık: aritmetik `+10` veya Balthazard | Her iki belgede **Balthazard** olduğu açıkça yazıldı; `%40 + %10 = %50` **yanlış** örneklendi |
| Ç-6 | **Araç-1'de 65 yaş** | Sözleşme "Araç-1 oranı çalışma gücü kaybı değildir" diyor ama 65 yaş ekinin nerede uygulanacağı yazmıyordu | **O-1 kapandı (28.10.2026):** Araç-1 **yaş hesabı yapmaz**, temel EK-2 oranını gösterir; %10 kuralı nötr bilgi bloğunda (§3.8) |
| Ç-7 | **`YARIN-DEVAM.md` eski sayıları** | Dosya 265/21 ve eski hash'leri "geçerli" gibi sunuyordu | Başına **güncellik uyarısı** eklendi; içerik tarihsel kayıt olarak korundu |

---

## 3. Görsellerden alınan somut tasarım kararları

### 3.1 Araç-1 (Görsel 2 — oran bulma)

| Karar | Gerekçe |
| --- | --- |
| **Tek ekranda arama + sonuç** (modal yok) | Görseldeki akış sade; mobilde ekran değiştirmek geri dönüşü zorlaştırıyor |
| Kategori daraltması **3 bölüm çipi + "Tümü"** | 19 çip gerçek kapsamı (3 bölüm) yansıtmıyor; çip kalabalığı yaratıyor |
| "Eklenen oranlar" listesi **korundu**, **oran toplamı gösterilmedi** | Toplam göstermek "sonuç" izlenimi verir; Araç-1 bileşen üretir |
| **Anatomi figürü alınmadı** | 3 bölüm için gereksiz; mobilde yer kaybı, erişilebilirlik yükü (ekran okuyucu için anlamsız görsel) |
| **Boşken `%0` halkası alınmadı** | Seçim yapılmadan "oran var" izlenimi veriyor; nötr boş durum metni kullanıldı |
| **Dev gradyan banner alınmadı** | Engelli.me'nin sade diliyle uyumsuz |
| **65 yaş bilgi bloğu eklendi** (görselde yok) | Mevzuat gereği; oranı değiştirmeden, ayrı ve nötr blokta |
| Sonuç **düz metin + kaynak künyesi**, yuvarlak "skor" değil | "Nihai oran" izlenimini engeller |

### 3.2 Araç-2 (Görsel 1 — Balthazard)

| Karar | Gerekçe |
| --- | --- |
| **Tek ekranda giriş + liste + sonuç** | Görseldeki gibi; ayrı sonuç sayfası yok |
| **"+ Oran ekle"** ile çoğaltma, satırda `[düzenle] [×]` | Görseldeki ekleme mantığı sadeleştirildi |
| **Kaydırıcı (slider) alınmadı**, yalnız sayı alanı | Tam sayı hassasiyeti + mobilde yanlış dokunma riski + erişilebilirlik |
| **`%0` halkası alınmadı** → nötr "Henüz oran eklenmedi." | Hesapsız sonuç göstermemek için |
| **"65 yaş ve üzeri" switch'i alınmadı** → **iki varsayılansız radio** | Switch'in kapalı hâli **sessiz "65 altı" kabulü**; kullanıcı dokunmadan hesaplarsa kural sessizce atlanır |
| **Formül kartı korundu** ("Nasıl hesaplanır?" katlanabilir, 4 adım) | Görseldeki en yararlı fikir; ama metin yeniden yazıldı |
| Kaynak künyesi **yalnız 65+ seçiliyken**, sonucun altında | Kullanıcı isteği; görseldeki "sonuç altı açıklama" fikriyle uyumlu |
| **"Sonuç eski" uyarısı eklendi** (§12.2) | Görselde yok; ama "Hesapla" modelinde girdi değişince eski sonuç sessizce kalıyor |

### 3.3 Her iki görselde ortak

- Sade, kısa yönlendirme metinleri; uzun paragraf yok.
- Kalıcı alt bilgi (bilgilendirme amaçlı) korunur.
- Mobil: tek sütun, çipler yatay kaydırılır, sonuç kartı tam genişlik.

---

## 4. Netleşen akışlar

### 4.1 Araç-1 — Oran Bul

```
[1] Ara / bölüm seç
      ├─ arama (≥3 karakter, Türkçe duyarsız) ─► sonuç listesi
      └─ bölüm ─► [2] grup/başlık ─► [3] hastalık ─► [4] seviye
                                                        │
[4] tek kayıtlı grupta ATLANIR (9 grup) ────────────────┤
                                                        ▼
[5] Sonuç: oran + "EK-2'de tanımlı oran" etiketi + kaynak s. + kısıtlar
                                                        │
[6] 65 yaş bilgi bloğu (nötr, oranı DEĞİŞTİRMEZ, %40 → %46 örneği)
                                                        │
[7] "Hesaplamaya ekle" ──► Araç-2'ye yalnız {id, oran, kısa etiket}
```

Özel durumlar:

- **Belirsiz (10):** oran kutusu çizilmez, "kaynakta tek oran yok" mesajı + uzman hekim yönlendirmesi.
- **Çözülmüş iz (11):** arama sonucu olarak **dönmez**; katalog karşılığı normal kayıt olarak döner.
- **Kısıtlar:** 7 kod, 228 kısıt kaydı, 182 kısıtlı kayıt; `R-VERGI`/`R-REMISYON` kırmızı, diğerleri amber/nötr.
- **Hematoloji bölüm notu:** s.26 NOT'u kısıt değil, bölüm düzeyi bilgi olarak gösterilir.

### 4.2 Araç-2 — Balthazard

```
[1] Oran gir (0-100 tam sayı) + isteğe bağlı etiket ─► [+ Ekle]
        │  (0 → bilgi, 100 → onay, tekrar → uyarı; hiçbiri engellenmez)
        ▼
[2] Liste (giriş sırası) — SATIŞ SIRASI KULLANICIYA SORULMAZ
        │  motor her zaman büyükten küçüğe sıralar
        ▼
[3] Yaş: ( ) 65 yaş altı   ( ) 65 yaş ve üzeri      ← VARSAYILAN YOK
        │
[4] [ Hesapla ]  ← oran yok VEYA yaş seçilmedi ise PASİF
        ▼
[5] Sonuç: bileşke + adım adım döküm + yuvarlama durumu
        │  + 65+ ise: yaş eki satırı (Balthazard %10)
        │  + 65+ ise: kaynak künyesi (30692)
        ▼
[6] Girdi değiştiyse: "Bu sonuç önceki girdilere ait" uyarısı
    Yaş değiştiyse: sonuç + kaynak AYNI ANDA yenilenir
```

---

## 5. Ortak motor sözleşmesi (özet)

Tam sözleşme: `ORTAK-MOTOR-SOZLESME.md`.

- **Girdi:** `oranlar` (0-100 tam sayı listesi, en az 1) + `yas` (`65_alti` / `65_ve_uzeri`, **zorunlu**) + isteğe bağlı `yas_ekle` (varsayılan `true`; Araç-1 `false` gönderir).
- **Çıktı:** `sonuc.deger` (ham), `adimlar`, `siralama.uygulanan`, `yas_eklemesi`, `yuvarlama`, `uyarilar`.
- **Hata:** istisna fırlatılmaz; `{ok:false, hata:{kod, mesaj}}`.
- **Yaş kuralı:** 65+ → `A + (100−A)×10/100`, **son adım**; tek uygulama noktası motor. Araç-1 `yas_ekle=false` ile çağırır → EK-2 temel oranı.
- **Yuvarlama (B-2, kapandı):** motor **ham değer** döndürür, ara aşamada yuvarlama **yok** (`yuvarlama.uygulandi = false`). Gösterim kuralı ayrı katmandadır ve **28.10.2026'da kapandı** (§10; G-1…G-4); motora girmez.
- **Motor katalog okumaz**; hastalık/etiket/kimlik bilmez.

**Test vektörleri (yalnız yuvarlama gerektirmeyen):** `[40]`→40 · `[40,30]`→58 · `[40]+65+`→**46** ·
`[0]`→0 · `[100]`→100 · `[0,40]`→40 · `[100,40]`→100 · `[30,40]`→58.

---

## 6. Karar durumu

### 6.1 Çözülen kararlar (28.10.2026)

| # | Karar | Sonuç |
| --- | --- | --- |
| **O-1** | Araç-1'de 65 yaş gösterimi | **Kapandı:** eki **uygulamaz**, temel EK-2 oranını gösterir; %10 kuralı **ayrı, nötr bilgi bloğunda**; otomatik yaş hesabı yok |
| **O-2** | Tek kayıtlı grup sayısı | **Kapandı:** **9** kabul (D-013, D-014, D-017, D-049, D-062, D-075, D-086, D-134, H-056); eski **12** tarihsel not |
| **B-1** | Yaş eşiği (65 ↔ 60) | **Kapandı:** 65; kaynak çelişkisi (Ek-3 (e) "60") kayıtlı |
| **B-2** | Yuvarlama (motor) | **Kapandı:** motor ham değer döndürür, ara aşamada yuvarlamaz |
| **B-6** | Aynı oranın tekrarı | **Kapandı:** engellenmez; bilgilendirici uyarı; her giriş hesaba katılır |
| **B-7** | Ondalıklı giriş | **Kapandı (ürün tercihi):** ilk sürümde tam sayı; mevzuat kuralı değil |

### 6.2 Açık kalan kararlar (tahminle kapatılmadı)

| ID | Konu | Neden açık | Geçici davranış |
| --- | --- | --- | --- |
| **O-3** | Künye 30692 ↔ 31275 | 30692 doğrulandı; 31275 = 15.10.2020 RG ve bu Yönetmelikle ilgisiz; **JSON'a nasıl girdiği izlenemiyor** | JSON `meta` değişmez; belgeler 30692 kullanır |
| **B-4** | Tavan / 100 aşımı | Kırpma hükmü yok | Kırpma yapılmaz |
| **B-5** | 0 ve 100 davranışı | Özel hüküm yok; 0 gerçek kayıt (`Z-056`) | Özel işlem yok |
| **B-8** | DERİ s.19 "ayrıca %5" | Aritmetik mi Balthazard mı belirsiz; `X-D03` bu nedenle belirsizde | **Kataloğa ve motora eklenmedi** |
| **A-1…A-6** | Belirsiz 10 kaydın çözümü | Bağlayıcı Bakanlık görüşü/genelge gerekir | Ekranda oran çizilmez, uzman hekim yönlendirmesi |

**Kapandı (bu tabloya eklenmez):** B-3 ve G-1…G-4, 28.10.2026 ek kararıyla kapandı (§10).

**Özet:** 8 karar kapandı (O-1, O-2, B-1, B-2, B-3, B-6, B-7, G-1…G-4); **3 madde açık**
(B-4, B-5, B-8) + O-3'ün izi + A-1…A-6. Açık maddelerin hiçbiri motoru **bloklamıyor**:
motor ham değerle, kırpma yapmadan, tam sayı maskesiyle çalışabilir; gösterim kuralı da
kapandığı için iki araç aynı metni üretir.

---

## 7. Doğrulama sonuçları

Veri dosyaları **değiştirilmedi**; aşağıdaki değerler bu oturumda yeniden hesaplandı.

| Kontrol | Sonuç |
| --- | --- |
| `katalog_taslak.json` kayıt | **276** |
| Oran toplamı | **8.990** |
| Bölüm dağılımı | Z **56** · D **142** · H **78** |
| `belirsiz.json` satır | **21** (belirsiz **10** / çözüldü **11**) |
| Toplam satır | **286** (276 + 10) |
| Grup sayısı (ayraç solu) | **78**; tek kayıtlı **9** |
| Durum matrisi | çok kayıtlı normal **266** + H-065 **1** + tek kayıtlı **9** = **276** |
| Kısıtlar | R-YILLIK 142 · R-GECICI 34 · R-VERGI 34 · R-NAKIL 6 · R-REMISYON 4 · R-IKTIYOZ 4 · R-EKTO 4 |
| Kısıtlı / kısıtsız kayıt | **182 / 94** |
| `(hastalik, alt_tur)` tekrarı | **0** |
| `alt_tur = "—"` | **6** (D-013, D-014, D-017, D-062, H-056, H-065) |
| `hastalik` içinde `" — "` | **64** |
| JSON geçerliliği | İki dosya da hatasız parse |
| **katalog MD5** | **`B77AEF76A1310DE4AE93E703183E2A09`** (68.914 B) — beklenenle aynı |
| **belirsiz MD5** | **`89AE83AAFFF9D6541B75D4073FC1BE82`** (19.037 B) — beklenenle aynı |

### 7.1 Belgeler arası tutarlılık taraması (28.10.2026)

| Kontrol | Yöntem | Sonuç |
| --- | --- | --- |
| Eski sayılar (265 / 21 / 12 / 138 / 177 / 252 / 73) | Tüm `.md` dosyalarında arama | **Yalnız tarihsel/arşiv belgelerinde** var: `YARIN-DEVAM.md` (başında güncellik uyarısı), `KATALOG-SON-KONTROL.md`, `BELIRSIZ-COZUM-RAPORU.md`. Hazırlık belgelerinde **temiz** |
| "X-D09 örneği" | Arama | Yalnız **değişiklik notlarında** ("X-D09 → X-D03") geçiyor; örnek olarak kullanılmıyor |
| "onay bekliyor" / "onayına sunuldu" | Arama | O-1, O-2, O-3 için **kaldırıldı**; yalnız bu raporun başlığındaki *"uygulama kodu için onay bekliyor"* ve `YARIN-DEVAM.md` tarihsel satırı kaldı |
| "B-2/B-3/B-6/B-7 açık" | Arama | Hepsi **kapandı**; B-3 ve G-1…G-4 **28.10.2026 ek kararıyla** kapandı — ifadeler belgeler arasında aynı |
| B-4 / B-5 / B-8 | Arama | Üç belgede de **açık**, "kırpma/özel işlem eklenmez", "DERİ +%5 eklenmedi" aynı |
| Motor imzası | `ARAC-2` §8.1 ↔ `ORTAK-MOTOR` §2/§3 | Aynı: `balthazard({oranlar, yas, yas_ekle=true})`; `yas_ekle` üç yerde aynı anlamda (`ARAC-1-SOZLESME` §3.8, `ORTAK-MOTOR` §1/§2/§4/§9, `ARAC-2` §8.1) |
| Tekrar uyarısı metni | `ARAC-2` §4/§10 ↔ `ORTAK-MOTOR` §5 | Aynı: "…Her iki giriş de hesaplamaya dahil edilir." (onay istemez) |
| Tam sayı gerekçesi | `ARAC-2` §4/§8.2/§8.5/§10 ↔ `ORTAK-MOTOR` §5 | Her yerde **"ürün tercihi, mevzuat kuralı değil"** |
| Künye | `OKUBENI`, `ARAC-1-SOZLESME` §8.1, `ARAC-2` §6/§10 | Her yerde **20.02.2019 / 30692**; 31275 **açık** olarak işaretli; JSON `meta` **değişmedi** |
| Tek kayıtlı grup | `ARAC-1-SOZLESME` §3.3/§5/§8, `ARAC-1-WIREFRAME`, bu rapor | Her yerde **9**; 12 yalnız tarihsel not |
| Belirsiz örnek | `ARAC-1-WIREFRAME` | **X-D03** (hâlâ belirsiz) — çözülmüş kayıt örnek olarak kullanılmıyor |
| Yuvarlanmış örnek | Tüm belgeler | Yalnız `%40 → %46` ve §9.1/§6.1'deki **ham değer + gösterim** çiftleri; tek başına yuvarlanmış toplam **yok** |

### 7.2 Dosya boyutu / MD5 (son ölçüm)

Belge dosyaları (bu turda üretilen/güncellenen):

| Dosya | Boyut | MD5 |
| --- | --- | --- |
| `OKUBENI.md` | 13.222 B | `64E794114FCF6D659A347D4034DA1EF9` |
| `ARAC-1-SOZLESME.md` | 22.400 B | `905D1DF4478A5230823DCBECA3C5CCF0` |
| `ARAC-1-WIREFRAME.md` | 26.042 B | `6B8FBA9FE1E63C4C414822E08C52D055` |
| `ARAC-2-WIREFRAME.md` | 45.157 B | `28BBBC619E0D53E79DA33112CC4B8415` |
| `ORTAK-MOTOR-SOZLESME.md` | 11.137 B | `4BBE440360F2298096184F792B369189` |
| `YARIN-DEVAM.md` | 6.410 B (yalnız uyarı eklendi) | `BBE90E4074430E52FF3D0DC55BF874A0` |
| `ARAC-1-2-HAZIRLIK-RAPORU.md` | *(bu dosya — her düzenlemede değişir)* | — |

---

## 8. Sınırlar — ne yapılmadı

- **Kod yazılmadı**, hiçbir uygulama dosyası oluşturulmadı/değiştirilmedi.
- **Katalog JSON'larına dokunulmadı**; oranlar, kısıtlar, kaynak bilgileri aynı (MD5 sabit).
- 11 çözülen kayıt **tekrar eklenmedi**; 10 belirsiz kayıt **kesin oran gibi gösterilmedi**.
- İlgisiz HTML/CSS/giriş sistemi/mevcut özelliklere **dokunulmadı**.
- **Git commit, push, merge, build, deploy yapılmadı.**
- Gereksiz test/build çalıştırılmadı (yalnız veri doğrulama betikleri).
- Doğrulanamayan noktalar **tahminle kapatılmadı**: B-4, B-5, B-8, O-3'ün izi, A-1…A-6.
  Kapatılanlar (O-1, O-2, B-1, B-2, B-3, B-6, B-7, G-1…G-4) **tarih + gerekçe** ile kayıtlıdır.
- DERİ +%5 (B-8/X-D03) **kataloğa ve motora eklenmedi**.

---

## 9. Uygulamaya geçiş için onay isteği

Hazırlık belgeleri **son hâlinde** ve kendi aralarında tutarlı. Aşağıdakiler onaylanırsa
kodlamaya geçilebilir:

1. **O-1** — Araç-1'de 65 yaş eki **uygulanmaz**; temel EK-2 oranı gösterilir; %10 kuralı nötr
   bilgi bloğunda açıklanır; otomatik yaş hesabı yok. (Motor çağrısı `yas_ekle=false`.)
2. **O-2** — Tek kayıtlı grup sayısı **9** kabul; eski 12 tarihsel not.
3. **O-3** — Belgelerde **30692** künyesi kullanılır; **JSON `meta` bu turda değişmez**.
   31275 farkı kaynaklarıyla araştırıldı (15.10.2020 RG, ilgisiz); JSON'a giriş izi **açık**.
4. **B-2 / B-3 / B-6 / B-7 / G-1…G-4** — Motor ham değer döndürür; yaş eki ham bileşkeye
   uygulanır; tekrar engellenmez; ilk sürümde tam sayı girişi (ürün tercihi); gösterim en
   fazla 2 ondalık, yarı yukarı, tek kez (§10).
5. **Açık maddeler kod başlamadan kapanmak zorunda değil:** B-4, B-5, B-8, A-1…A-6
   tahminle doldurulmadan, belgelenmiş geçici davranışla ilerlenir. **DERİ +%5 uygulanmaz.**
6. **`ORTAK-MOTOR-SOZLESME.md`** imzası (`balthazard(girdi) → cikti`, `yas_ekle`, hata/uyarı
   kodları, test vektörleri 1–20) onaylanır.

> **Onay bekliyorum.** Onay gelmeden uygulama koduna, build'e veya deploy'a geçilmeyecek.
> Bu turda commit, push, merge, build, deploy **yapılmadı**; canlı site ve JSON'lar **değişmedi**.

---

## 10. Ek karar — gösterim kuralı (G-1…G-4) kapandı, 28.10.2026

G-1…G-4 açık maddeleri, kullanıcının verdiği sıraya göre **ilk iş** olarak kapatıldı.
Karar bir **ürün/arayüz tercihidir**; mevzuatta (Yönetmelik, EK-2 kılavuzu, Ek-3) gösterim
hükmü **yoktur**. Bu yüzden hesap değişmedi, yalnız **sunum** kuralı bağlandı.

| # | Karar | Uygulama |
| --- | --- | --- |
| G-1 | Sonuç ve adım dökümü **en fazla 2 ondalık**; tam sayıda ondalık yok; sondaki gereksiz sıfırlar atılır | `bicimle_gosterim(deger, basamak=2)` |
| G-2 | **Yarı yukarı** (`ROUND_HALF_UP`); kesme ve yarı çift kullanılmaz | `Decimal.quantize(..., ROUND_HALF_UP)` |
| G-3 | Ham bileşke → yaş eki (ham) → **tek** gösterim yuvarlaması | Motor sırası korunur; yaş eki yuvarlanmış değere uygulanmaz |
| G-4 | Adım dökümünde ondalık **gösterilir**, aynı kuralla; ham değer de taşınır | `adimlar[]` değişmez |

**Değişmeyenler (açıkça doğrulandı):**

- `sonuc.deger` **ham** kalır; gösterim motora geri yazılmaz.
- `adimlar[]` ham değerleri taşır; adımlar yeniden yuvarlanmaz.
- `yuvarlama.uygulandi` **her zaman `false`**, `yuvarlama.kural` **`null`**.
- Kopyalama / dışa aktarma **ham değeri** taşır, gösterim metnini değil.
- Test vektörleri 1–13 aynı; ondalıklı örnekler **14–20** olarak, **ham değer + gösterim**
  çifti hâlinde sözleşmeye eklendi (`ORTAK-MOTOR-SOZLESME.md` §9.1).

**İşlendiği yerler:**

| Dosya | Sürüm | Değişiklik |
| --- | --- | --- |
| `ORTAK-MOTOR-SOZLESME.md` | 0.2 → **0.3** | §3 `yuvarlama.not` metni; §4/B-3 kapanışı; §7.1/§7.2 karar tablosu; §8 tablo; §9.1 ondalık vektörler; §10 doğrulama maddeleri |
| `ARAC-2-WIREFRAME.md` | 0.3 → **0.4** | §6.1 kapandı (karar + örnek tablo); §6 örnek notu; §8.2/2, §8.2 özeti, §8.5 B-2/B-3; §10 metin sözlüğü; §11; **yeni §12.3** aktarım kontrolleri |
| `ARAC-1-SOZLESME.md` | 0.3 (metin) | §11: gösterim kuralının ortak motorda olduğu, Araç-1'in kendi biçimlendirmesini yapmadığı |
| `ARAC-1-WIREFRAME.md` | 0.3 (metin) | §10: gösterim kuralı ortak motorda, burada yeniden yazılmaz |
| `balthazard_motoru.py` | `MOTOR_SURUMU` 0.1 → **0.2** | Docstring + `YUVARLAMA_NOT` + `bicimle_gosterim()` docstring kararla uyumlu; **davranış değişmedi** |
| `test_balthazard_motoru.py` | — | Yeni `GosterimKarari` sınıfı (6 test): vektör 14–20, ham değerin korunması, yaş ekinin ham bileşkeye uygulanması, tek yuvarlama, kopyanın ham değeri taşıması, `yuvarlama.not` uyumu. **71 → 77 test** |

**Doğrulama:** `python -m unittest test_balthazard_motoru` → **77 test, OK**. Katalog JSON'ları
(`katalog_taslak.json`, `belirsiz.json`) **değişmedi**; commit/push/build/deploy yok.
