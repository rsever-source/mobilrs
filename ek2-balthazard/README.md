# EK-2 Balthazard — inceleme paketi

Sürüm: 1.2 · Tarih: 28.10.2026 · Durum: **inceleme/prototip — üretime bağlı değil**

Bu klasör, EK-2 (Erişkinler İçin Engellilik Değerlendirmesi) kapsamındaki üç bölüm
(ZİHİNSEL/RUHSAL/DAVRANIŞSAL, DERİ, HEMATOLOJİK) için hazırlanan **ortak Balthazard
motorunu**, **Araç-2 ekran prototipini** ve iki aracın **bağlayıcı sözleşmesini** tek
yerde toplar.

- **Araç-1 (Engel Oranı Bul):** hastalık + seviye seçiminden EK-2'de tanımlı tek oranı
  bulur. Sözleşmesi hazırdır; **ekranı henüz geliştirilmedi**.
- **Araç-2 (Balthazard Hesapla):** elle girilen oranların bileşkesini hesaplar.
  Çalışan prototipi `arac2/` altındadır.
- **Ortak motor:** iki araç da aynı `balthazard()` fonksiyonunu çağırır; kopya hesap
  kodu yasaktır. 65 yaş eki ve sıralama yalnız motorda uygulanır.

Ayrıntılı kurallar, kararlar ve doğrulama sonuçları: [`SOZLESME.md`](SOZLESME.md).

---

## Dosya yapısı

```
ek2-balthazard/
├── README.md                     bu dosya: amaç, çalıştırma, kararlar, açık konular
├── SOZLESME.md                   ortak motor + Araç-1 + Araç-2 bağlayıcı sözleşmesi
├── balthazard_motoru.py          ortak motor (stdlib, MOTOR_SURUMU = "0.2")
├── test_balthazard_motoru.py     77 unittest
├── veri/
│   ├── katalog.json              276 doğrulanmış kesin kayıt (değiştirilmez)
│   └── belirsiz.json             21 satır: 11 çözüldü + 10 belirsiz
└── arac2/
    ├── arac2.html                Araç-2 ekranı (HTML + CSS + JS, harici bağımlılık yok)
    ├── arac2_sunucu.py           stdlib http.server; yerel prototip sunucusu
    └── test_arac2.py             11 unittest
```

Klasör kendi kendine yeterlidir: yalnız **Python standart kütüphanesi** kullanılır, ek
paket, `requirements.txt` değişikliği veya dış servis gerekmez.

---

## Çalıştırma (Araç-2 prototipi)

Python 3.10+ yeterlidir. Sunucu yalnız `127.0.0.1` üzerinde dinler, dışarıya açılmaz.

```
cd ek2-balthazard/arac2
python arac2_sunucu.py            # http://127.0.0.1:8765
python arac2_sunucu.py 9000       # başka port
```

Uç noktalar: `GET /` ve `GET /arac2` (ekran), `GET /saglik` (sağlık kontrolü),
`POST /api/hesapla` (motor çağrısı). Gövde hatasında transport katmanı
`400 {"ok": false, "mesaj": …}` döner; **yeni motor hata kodu uydurulmaz**.

Prototip canlı FastAPI uygulamasına **bağlanmadı**; `/api/hesapla` yalnız yerel sunucuda
vardır.

---

## Testler

```
cd ek2-balthazard
python -m unittest -v test_balthazard_motoru     # beklenen: 77 test, OK

cd ek2-balthazard/arac2
python -m unittest -v test_arac2                 # beklenen: 11 test, OK
```

Testler `unittest` ile yazılmıştır (pytest gerekmez). 28.10.2026 doğrulaması: **77 + 11
test OK**.

---

## Kapalı kararlar (özet)

Ayrıntı ve gerekçeler `SOZLESME.md` §7'dedir.

| ID | Karar | Sonuç |
| --- | --- | --- |
| **O-1** | Araç-1'de 65 yaş | Araç-1 yaş eklemesi **yapmaz**; EK-2 temel oranını gösterir. %10 kuralı ayrı, nötr bilgi bloğunda açıklanır; motor `yas_ekle=false` ile çağrılır |
| **O-2** | Tek kayıtlı grup sayısı | **9** kabul edildi (D-013, D-014, D-017, D-049, D-062, D-075, D-086, D-134, H-056). Eski "12" yalnız tarihsel nottur |
| **B-1** | Yaş eşiği | **65 yaş ve üzeri**. Ek-3 (e) bendindeki "60" kaynak çelişkisi olarak kayıtlıdır, uygulanmaz |
| **B-2** | Yuvarlama | Motor **ham** değer döndürür, ara aşamada yuvarlamaz (`yuvarlama.uygulandi=false`) |
| **B-3** | Yaş ekinin sırası | Ham bileşke → yaş eki (ham) → **tek** gösterim yuvarlaması |
| **B-6** | Aynı oranın tekrarı | Engellenmez; her giriş hesaba katılır; yalnız bilgilendirici uyarı |
| **B-7** | Ondalıklı giriş | İlk sürümde tam sayı — **ürün tercihi**, mevzuat kuralı değil |
| **G-1…G-4** | Gösterim | En fazla **2 ondalık**, **yarı yukarı** (`ROUND_HALF_UP`), tam sayıda ondalık yok, sondaki sıfırlar atılır, Türkçe virgül; yuvarlama **tek kez ve yalnız sunumda** |

**Değişmeyen hesap:** motorun çıktısı (`sonuc.deger`, `adimlar[]`, `yuvarlama`) gösterim
kararından etkilenmez. Biçimlendirme yalnız `bicimle_gosterim()` ile yapılır; ekranlar
kendi yuvarlamasını yapmaz. Kopyalama/dışa aktarma **ham değeri** taşır.

---

## Açık konular

Hiçbiri motoru bloklamaz; hiçbiri tahminle kapatılmamıştır.
Ayrıntı: `SOZLESME.md` §7.3 ve §3.11.

| ID | Konu | Bugünkü davranış |
| --- | --- | --- |
| **B-4** | Tavan / 100 aşımı | Kırpma yapılmaz; hüküm bulunana kadar kural eklenmez |
| **B-5** | 0 ve 100 uç değerleri | Özel işlem yok; 0 etkisiz, 100 sonucu kilitler. 0 gerçek kayıttır (Z-056) |
| **B-8** | DERİ s.19 "ayrıca %5" | Kataloğa ve motora **eklenmedi**; X-D03 belirsizde |
| **O-3** | Künye 30692 ↔ 31275 | Belgeler **20.02.2019 / 30692** kullanır; JSON `meta` değiştirilmedi; 31275'in JSON'a giriş izi bulunamadı |
| **A-1…A-6** | 10 belirsiz katalog satırı | Oran gösterilmez; uzman hekim yönlendirmesi. Bağlayıcı Bakanlık görüşü/genelge gerekir |
| — | Hematoloji s.26 NOT kapsamı | Bölüm notu olarak gösterilir; 78 kaydın tamamına uygulanmış kısıt sayılmaz |
| — | `alt_tur` / `kisit` şema sözleşmesi | Ekran `—` değerini yutar; `kisit` liste olarak ele alınır. Veri değişikliği yapılmadı |
| — | 72 imla/biçim kalemi | Uygulanmadı; bloklamıyor |

---

## Katalog verisi

Katalog dosyaları depoda **`veri/`** altındadır ve EK-2 çalışmalarında tek doğruluk
kaynağıdır:

| Dosya | İçerik |
| --- | --- |
| `veri/katalog.json` | **276** doğrulanmış kesin kayıt (kaynak `katalog_taslak.json`'ın kopyası) |
| `veri/belirsiz.json` | **21** satır: 11 `cozuldu` (tarihsel iz) + 10 `belirsiz` |

İçerik kaynak sürümle **bayt düzeyinde aynıdır**; yalnız dosya adı ve yolu değişti. Aşağıdaki
sayılar ve MD5 değerleri bu dosyaların 28.10.2026 tarihinde salt okunur doğrulanmasının
sonucudur:

| Ölçü | Değer |
| --- | --- |
| Kesin kayıt | **276** (Z 56 · D 142 · H 78) |
| Belirsiz satır | **10** (`durum: belirsiz`) |
| Çözülüp kataloğa aktarılan | **11** (`durum: cozuldu`, arama sonucu olarak dönmez) |
| Toplam kaynak satırı | **286** |
| Kısıt kodu / kısıt kaydı | 7 kod · 228 kayıt |
| Kısıtlı / kısıtsız kayıt | 182 / 94 |
| Tek kayıtlı grup | 9 |
| `alt_tur = "—"` | 6 (D-013, D-014, D-017, D-062, H-056, H-065) |
| Doğrulanan MD5 | `veri/katalog.json` `B77AEF76A1310DE4AE93E703183E2A09` · `veri/belirsiz.json` `89AE83AAFFF9D6541B75D4073FC1BE82` |

Kaynak künyesi: *Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik*
(RG **20.02.2019, 30692**), EK-2 kılavuzu s.13-26. Göz, işitme, konuşma ve kas-iskelet
bölümleri bu çalışmanın kapsamı dışındadır.

---

## Sınırlar

- Bu paket **üretim koduna entegre edilmedi**: FastAPI uç noktaları, workflow'lar,
  `cloudbuild.yaml` ve dağıtım ayarları değişmedi.
- Katalog dosyaları `veri/` altında **değiştirilmeden** depoda tutulur; uygulama henüz
  bunları okumaz, entegrasyon ayrı adımdır. Sayı, şema ve çakışma kanıtları
  `SOZLESME.md` §8.1.1'dedir.
- Araç-1 ekranı geliştirilmedi; yalnız sözleşmesi korunuyor.
- Nashi projesine ve ilgisiz dosyalara dokunulmadı.
- Ekran görüntüleri, ölçüm betikleri ve geçici dosyalar depoya eklenmedi.

---

## Tarihsel notlar

- 28.10.2026 sadeleştirmesi: altı ayrı belge (`OKUBENI`, `ORTAK-MOTOR-SOZLESME`,
  `ARAC-1-SOZLESME`, `ARAC-1-WIREFRAME`, `ARAC-2-WIREFRAME`, `ARAC-1-2-HAZIRLIK-RAPORU`)
  içerik kaybı olmadan bu iki belgeye birleştirildi.
- Eski belgelerdeki **265 kayıt / 21 belirsiz** sayıları 11 kayıt uygulanmadan önceki
  durumu gösterir (tarihsel); güncel sayılar yukarıdadır ve `SOZLESME.md` §8.1.1'de
  geçiş tablosu vardır. **12 tek kayıtlı grup** sayısı ve eski MD5 değerleri geçersizdir.
- Belirsiz kayıt örneği eskiden X-D09 idi; X-D09 çözülüp **D-141** olduğu için örnek
  **X-D03**'e taşındı.
- `YARIN-DEVAM.md`, `BELIRSIZ-COZUM-RAPORU.md`, `KATALOG-SON-KONTROL.md` ve `_yedek/`
  arşiv/veri raporlarıdır; **bu pakete alınmadı, depoya yüklenmedi**. Bu dosyalardaki
  sayılar güncel değildir. Katalog kontrol raporundaki güncel ve önemli kanıtlar
  (şema uyumu, çakışma kontrolü, sayaç değişimi, `kaynak_not` değerleri, hash geçmişi)
  kaybolmasın diye `SOZLESME.md` §8.1.1'e taşındı.
- Yedekler ve eski devam notları bilinçli olarak yüklenmez; depoda **güncel katalog verisi**
  (`veri/`) ve doğrulama sonuçları durur, geçici çalışma dosyaları durmaz.
- Bu çalışma `feature/ek2-balthazard-arac2` dalında yürütülür; ana dala merge ve canlı
  deploy yapılmaz.
