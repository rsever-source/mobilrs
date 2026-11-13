# EK-2 görsel doğrulama listesi

Kaynak: `raporlar/ek2_kavram_kanit_kontrol.json`.
Bu liste, **kanonik adı kendi `ham_satir` alanında bulunmayan** kayıtları
sayfaya göre gruplar. Doğrulama PDF sayfa görüntüsü üzerinden yapılır;
OCR metin benzerliği görsel doğrulama sayılmaz.

- Kayıt: **99**
- Farklı sayfa: **56**

| Durum (OCR) | Kayıt |
| --- | --- |
| `ad_sayfada_birebir` | 20 |
| `ad_sayfada_yaklasik_inceleme` | 20 |
| `ad_sayfada_dogrulanamadi` | 59 |

## PDF sayfa 30

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Hipertansif serebrovasküler hastalık | 2. Hipenansif serebrovasküler hastalık | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 34

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Derin ven trombozu | 4- Venöz sistem hastalıkları: İnvaziv ve noninvaziv tetkiklerle tespit edilmiş derin ven | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 2 | Fonksiyonel damar hastalıkları | 2- Fonksiyonel damar hastalığı olanlar (Reynaud Fenomeni, Akrosiyanozis vs.) | `ad_sayfada_dogrulanamadi` | 0.574 | (bekliyor) |
| 3 | Raynaud fenomeni | 2- Fonksiyonel damar hastalığı olanlar (Reynaud Fenomeni, Akrosiyanozis vs.) | `ad_sayfada_dogrulanamadi` | 0.368 | (bekliyor) |

## PDF sayfa 40

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Kontrast duyarlık ve kamaşma (glare) kusuru | o Tek gözde mevcut ise | `ad_sayfada_dogrulanamadi` | 0.618 | (bekliyor) |

## PDF sayfa 42

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Tek gözlülük (monokülarite) | "tek gözlülük durumu” (monokülarite) diyeceğimiz özel bir durum ortaya çıkar. | `ad_sayfada_dogrulanamadi` | 0.414 | (bekliyor) |

## PDF sayfa 43

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Göz ekzanterasyonu | Ekzanterasyon ameliyatı geçirmiş veya travmatik nedenle aynı derecede kayıp gerçekleşmiş, tek göz | `ad_sayfada_dogrulanamadi` | 0.353 | (bekliyor) |

## PDF sayfa 44

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Lakrimal kanal tıkanıklığı | Sürekli göz sulanmasına neden olan lakrimal kanal tıkanmalarında (tedavi ile düzelmesi | `ad_sayfada_dogrulanamadi` | 0.414 | (bekliyor) |

## PDF sayfa 45

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Ambliyopi | Tanı: Açıklanmayan amliyopi, muhtemelen konjenital. | `ad_sayfada_dogrulanamadi` | 0.333 | (bekliyor) |
| 2 | Göz ve adneksleri tümörü | Göz Ve Adnekslerinde Tümör Varlığında Engel Oranının DeğerIendirilmesi | `ad_sayfada_dogrulanamadi` | 0.489 | (bekliyor) |

## PDF sayfa 49

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Stargardt juvenil makulopati | Tam: Stargardtjuvenil makulopati. | `ad_sayfada_yaklasik_inceleme` | 0.915 | (bekliyor) |

## PDF sayfa 57

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Bitemporal hemianopsi | Bitemporal hemianopislerde ise her bir gözün farklı yarılarında kayıp olduğu İçin binoküler görme | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 2 | Periferik görme alanı defekti | Periferik Görme Alam Defekti | `ad_sayfada_yaklasik_inceleme` | 0.947 | (bekliyor) |

## PDF sayfa 65

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Mide-duodenum bozuklukları | Mide-duedonum bozukluğuna ait semptom ve İşaretler bulantı-kusma, ağrı, kanama, | `ad_sayfada_dogrulanamadi` | 0.451 | (bekliyor) |
| 2 | Özefagus bozuklukları | Özefagus bozukluğunu işaret eden semptomlar disfaji, pirozis, retrosternal ağrı, | `ad_sayfada_dogrulanamadi` | 0.415 | (bekliyor) |
| 3 | İnce bağırsak bozuklukları | bozukluğuna ait semptomlar karın ağrısı, ishal, steatore, kanama, tıkanıklık ve kilo kaybım içerir. | `ad_sayfada_dogrulanamadi` | 0.4 | (bekliyor) |

## PDF sayfa 67

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Üst sindirim kanalı bozuklukları | 2. ÜST SİNDİRİM KANALI (özefagus, mide ve duedonum, ince bağırsak, ve pankreas) | `ad_sayfada_dogrulanamadi` | 0.772 | (bekliyor) |

## PDF sayfa 70

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Karaciğer transplantasyonu | Karaciğer transplantasyonlu hastalarda Engel Oranı %70 oranına Tablo 7'de | `ad_sayfada_dogrulanamadi` | 0.622 | (bekliyor) |
| 2 | Kolostomi | KOLOSTO | `ad_sayfada_yaklasik_inceleme` | 0.875 | (bekliyor) |
| 3 | İleostomi | LEOSTOMİ | `ad_sayfada_yaklasik_inceleme` | 0.941 | (bekliyor) |

## PDF sayfa 71

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Koledok obstrüksiyonu | Kalıcı sarılık; Oltak safra kanalı (koledok) | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 72

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Servikal darlık | b-Tedavi gerektirmeyen servikal darhk var veya | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 2 | Serviks ve uterus hastalıkları | Serviks Ve Uterus'un Kalıcı Bozukluklarının DeğerIendirilmesinde Kriterler | `ad_sayfada_dogrulanamadi` | 0.694 | (bekliyor) |
| 3 | Vulva ve vajina hastalıkları | Vulva ve Vagina'nın Kalıcı Bozulduklarının DeğerIendirilmesinde Kriterler | `ad_sayfada_dogrulanamadi` | 0.622 | (bekliyor) |

## PDF sayfa 73

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Fallopian tüp ve over hastalıkları | Fallopian Tüp Ve Overlerin Kalıcı Bozulduklarının | `ad_sayfada_dogrulanamadi` | 0.73 | (bekliyor) |

## PDF sayfa 74

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Kronik böbrek hastalığı | Kronik böbrek hastalı I | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 2 | Nefrotik düzeyde proteinüri ile seyreden nefropatiler | Nefrotik düzeyde proteinüri (»3.5 gr/gün) ile seyreden nefropatiler, 6 ay süren tedaviye | `ad_sayfada_dogrulanamadi` | 0.774 | (bekliyor) |
| 3 | Nonnefrotik proteinüri ile seyreden nefropatiler | Nonnefrotik proteinüri (mikroalbüminüri) ile seyreden nefropatiler, 6 ay süren tedaviye | `ad_sayfada_dogrulanamadi` | 0.727 | (bekliyor) |
| 4 | Renal replasman tedavisi | Renal re Iasman tedavisi hemodi aliz, eriton di alizİ erektiren kronik böbrek hastalı" | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 5 | Renal tübüler hastalık | İleri kalıcı renal tübüler hastalığa eşlik eden, en az 6 aylık tedavi altında ve 3 ölçümde serum | `ad_sayfada_dogrulanamadi` | 0.474 | (bekliyor) |

## PDF sayfa 75

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Üreterointestinal diversiyon (Coffey) | Üreterointestinal (coffey) | `ad_sayfada_yaklasik_inceleme` | 0.814 | (bekliyor) |

## PDF sayfa 76

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Aşırı aktif mesane | Devamlı tedavi gerektiren sistitizm semptomları da Qşırı aktif mesane | `ad_sayfada_dogrulanamadi` | 0.529 | (bekliyor) |

## PDF sayfa 77

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Prostat ve veziküloseminalis hastalığı | Tedaviyle düzeltilebilen tekrarlayan prostat. vezikuloseminalis hastalığı | `ad_sayfada_yaklasik_inceleme` | 0.848 | (bekliyor) |
| 2 | Testis ve epididim hastalığı | Tedaviyle düzeltilebilen tekrarlayan testis, epididim hastalığı | `ad_sayfada_dogrulanamadi` | 0.655 | (bekliyor) |

## PDF sayfa 78

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Üriner inkontinans | İ)RİNER İNKONTİNANS | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 83

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Ekstrapulmoner tüberküloz | * *Ekstra pulmoner tüberkülozlu olgularda ise tedavi sonunda ilgili branş tarafindan engel | `ad_sayfada_dogrulanamadi` | 0.471 | (bekliyor) |
| 2 | Kronik kor pulmonale | c- Ağır derecede etkilenme varsa veya kronik kor pulmonqle gelişmişse | `ad_sayfada_dogrulanamadi` | 0.432 | (bekliyor) |

## PDF sayfa 84

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Yanığa bağlı özefagus darlığı | b)Yamğa bağlı özefagus darlıkları ilgili branş tarafından değerlendirilir. | `ad_sayfada_dogrulanamadi` | 0.529 | (bekliyor) |

## PDF sayfa 85

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Heterotopik periartiküler kemik oluşumu | d)Yamk sonrası kostal kondritis ve heterotopik periartiküler kemik oluşması ilgili branş tarafından | `ad_sayfada_dogrulanamadi` | 0.536 | (bekliyor) |
| 2 | Yanık sonrası periferik sinir lezyonu | a)Yamk sonrası oluşan merkezi ve periferik sinir lezyonları ilgili branş tarafından değerlendirilir. | `ad_sayfada_dogrulanamadi` | 0.5 | (bekliyor) |

## PDF sayfa 86

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Glioblastoma multiforme | 6-Yüksek dereli opere beyin tümörleri: (örn G4 glioblastomi multiforme) | `ad_sayfada_dogrulanamadi` | 0.484 | (bekliyor) |

## PDF sayfa 87

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Motor afazi | A-MOTOR | `ad_sayfada_dogrulanamadi` | 0.692 | (bekliyor) |
| 2 | Sensöriyel afazi | B-SENSÖRİYEL | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 89

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Nörojenik kaynaklı ağrı | NÖROJENİK KAYNAKLI | `ad_sayfada_yaklasik_inceleme` | 0.878 | (bekliyor) |

## PDF sayfa 91

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Periferik fasiyal paralizi | PERİFERİK FASİAL PARALİZİ | `ad_sayfada_yaklasik_inceleme` | 0.98 | (bekliyor) |

## PDF sayfa 92

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Athetozis | tremor, chorea, athetosis, hemiballismus ve distoniler ekstremitelerin rahat kullanımını | `ad_sayfada_dogrulanamadi` | 0.414 | (bekliyor) |
| 2 | Disfaji | Hafif derecede dizartri, distoni veya | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 3 | Kore | tremor, chorea, athetosis, hemiballismus ve distoniler ekstremitelerin rahat kullanımını | `ad_sayfada_dogrulanamadi` | 0.5 | (bekliyor) |

## PDF sayfa 97

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Omurga ankilozu | Eğer omurgada bir miktar hareket olmasına rağmen aynı zamanda ankiloz var ise, nötral pozisyona en yakın hareket derecesi ankiloz derecesi olarak kabul edilir ve | `ad_sayfada_dogrulanamadi` | 0.357 | (bekliyor) |

## PDF sayfa 99

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Servikal omurga hareket kısıtlılığı | Tablo 1.4- Servikal omurgada hareket kısıtlılığına bağlı engellilik oranları (Eklem Hareket Açıklığı | `ad_sayfada_yaklasik_inceleme` | 0.866 | (bekliyor) |
| 2 | Torakal omurga hareket kısıtlılığı | Tablo 1.5- Torakal omurgada hareket kısıtlılığına bağlı engellilik oranları. | `ad_sayfada_dogrulanamadi` | 0.758 | (bekliyor) |

## PDF sayfa 101

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Lomber omurga hareket kısıtlılığı | Tablo 1.6- Lomber omurgada hareket kısıtlılığına bağlı engellilik oranları. | `ad_sayfada_yaklasik_inceleme` | 0.831 | (bekliyor) |

## PDF sayfa 102

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Vertebra kompresyon kırığı | Bir vertebra cisminin kompresyonu | `ad_sayfada_dogrulanamadi` | 0.644 | (bekliyor) |
| 2 | İntervertebral disk lezyonu | İntervertebral disk veya diğer yumuşak doku lezyonu | `ad_sayfada_dogrulanamadi` | 0.692 | (bekliyor) |

## PDF sayfa 108

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Üst ekstremite sorunları | 2. ÜST EKSTREMİTEYE AİT SORUNLARDA ENGELLİLİK ORANLARI | `ad_sayfada_dogrulanamadi` | 0.623 | (bekliyor) |

## PDF sayfa 135

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Başparmak ampütasyonu | -Başparmak: | `ad_sayfada_dogrulanamadi` | 0.6 | (bekliyor) |
| 2 | Metakarpofalangeal ampütasyon | smetakarpofalangiyal eklem | `ad_sayfada_dogrulanamadi` | 0.691 | (bekliyor) |
| 3 | Omuz dezartikülasyonu | -Omuz dezanikülasyonu | `ad_sayfada_yaklasik_inceleme` | 0.927 | (bekliyor) |
| 4 | Parmak ampütasyonu | Parmak | `ad_sayfada_dogrulanamadi` | 0.629 | (bekliyor) |
| 5 | Skapulotorasik ampütasyon | -Skapulotorasik | `ad_sayfada_dogrulanamadi` | 0.733 | (bekliyor) |

## PDF sayfa 136

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Tüm dirsek artroplastisi | Tüm dirsek | `ad_sayfada_dogrulanamadi` | 0.667 | (bekliyor) |
| 2 | Tüm el bileği artroplastisi | Tüm el bileği | `ad_sayfada_dogrulanamadi` | 0.692 | (bekliyor) |
| 3 | Tüm omuz artroplastisi | Tüm omuz | `ad_sayfada_dogrulanamadi` | 0.65 | (bekliyor) |

## PDF sayfa 139

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Brakial pleksus lezyonu | Tablo 2.13- Brakial pleksusun motor, duyu veya birleşik kayıplarının üst ekstremitede neden | `ad_sayfada_yaklasik_inceleme` | 0.789 | (bekliyor) |
| 2 | Spinal sinir lezyonu | Tablo 2.12- Spinal sinirlerin unilateral duyu, motor veya birleşik kayıplarının üst | `ad_sayfada_dogrulanamadi` | 0.4 | (bekliyor) |

## PDF sayfa 141

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Alt ekstremite sorunları | 3. ALT EKSTREMİTEYE AİT SORUNLARDA ENGELLİLİK ORANLARI | `ad_sayfada_dogrulanamadi` | 0.623 | (bekliyor) |

## PDF sayfa 143

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Alt ekstremite uzunluk farklılıkları | Tablo 3.3- Alt ekstremitenin uzunluk farklılıklarından kaynaklanan engellilik. (bkz tablo | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 144

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Yürüyüş bozukluğu | Tablo 3.4- Yürüyüş bozulduğuna göre engellilik oranları. (bkz tablo 3.1) | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 146

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Alt ekstremite kas kuvveti kaybı | Tablo 3.7- Alt ekstremite kas kuvvetinde kayba bağlı engellilik yüzdeleri. (bkz tablo 3,1) | `ad_sayfada_dogrulanamadi` | 0.609 | (bekliyor) |

## PDF sayfa 147

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Kalça eklemi hareket kısıtlılığı | Tablo 3.8b-KaI a eklemi hareket kısıtlı ı iddetine ba 11 en ellili | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 148

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Ayak bileği veya topuk deformitesi | Tablo 3.12- Ayak bileği veya topuk deformite bozuldukları. | `ad_sayfada_dogrulanamadi` | 0.733 | (bekliyor) |

## PDF sayfa 149

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Kalça ankilozu | Tablo 3.14- Kalçanın fleksiyon pozisyonunda ankilozuna bağlı engellilik oranlan. (*)(bkz tablo | `ad_sayfada_dogrulanamadi` | 0.688 | (bekliyor) |

## PDF sayfa 150

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Diz ankilozu | Tablo 3.19- Dizin varus pozisyonunda ankilozuna bağlı engellilik. | `ad_sayfada_dogrulanamadi` | 0.621 | (bekliyor) |

## PDF sayfa 152

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Ayak bileği ankilozu | Tablo 3.23- Ayak bileğinin plantar fleksiyon-dorsofleksiyonda ankilozuna bağlı engellilik. | `ad_sayfada_dogrulanamadi` | 0.435 | (bekliyor) |

## PDF sayfa 153

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Ayak ankilozu | Ayak (Arkaayak, Ortaayak, Önayak): Ayağın subtalar parçası İçin optimal ankiloz pozisyonu, | `ad_sayfada_dogrulanamadi` | 0.281 | (bekliyor) |

## PDF sayfa 155

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Alt ekstremite ampütasyonları | 3.7. AMPUTASYONLAR | `ad_sayfada_dogrulanamadi` | 0.652 | (bekliyor) |
| 2 | Chopart ampütasyonu | -Chopart (orta ayak) | `ad_sayfada_dogrulanamadi` | 0.611 | (bekliyor) |
| 3 | Diz altı ampütasyon | -Diz altı | `ad_sayfada_dogrulanamadi` | 0.667 | (bekliyor) |
| 4 | Diz üstü ampütasyon | -Diz üstü | `ad_sayfada_dogrulanamadi` | 0.667 | (bekliyor) |
| 5 | Syme ampütasyonu | -Syme (ayak) | `ad_sayfada_dogrulanamadi` | 0.667 | (bekliyor) |
| 6 | Transmetatarsal ampütasyon | -Transmetatarsal | `ad_sayfada_dogrulanamadi` | 0.732 | (bekliyor) |

## PDF sayfa 159

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Girdlestone artroplastisi | Girdlestone artroplasti | `ad_sayfada_yaklasik_inceleme` | 0.958 | (bekliyor) |
| 2 | Pelvis kırığı | Pelvis Kırıkları | `ad_sayfada_yaklasik_inceleme` | 0.828 | (bekliyor) |

## PDF sayfa 160

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Unikondüler replasman | Unikondüler | `ad_sayfada_yaklasik_inceleme` | 0.952 | (bekliyor) |

## PDF sayfa 161

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Ayak bileği kırığı | Kırık | `ad_sayfada_dogrulanamadi` | 0.759 | (bekliyor) |
| 2 | Ayak bileği ligamentöz instabilitesi | Ligamentöz instabilite (stres röntgenleri ile) | `ad_sayfada_yaklasik_inceleme` | 0.783 | (bekliyor) |
| 3 | Kalkaneal kırık | Ekstra-artikü ler (kalkaneal) | `ad_sayfada_dogrulanamadi` | 0.629 | (bekliyor) |
| 4 | Kalkaneoküboid kemik kırığı | Kalkaneoküboid kemik | `ad_sayfada_yaklasik_inceleme` | 0.851 | (bekliyor) |
| 5 | Subtalar kemik kırığı | Subtalar kemik | `ad_sayfada_yaklasik_inceleme` | 0.8 | (bekliyor) |
| 6 | Talonaviküler kemik kırığı | Talonaviküler kemik | `ad_sayfada_yaklasik_inceleme` | 0.844 | (bekliyor) |

## PDF sayfa 162

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Metatarsal kırık | kırık | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 163

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Alt ekstremitede doku kaybı | 3.9. DOKU KAYBI | `ad_sayfada_dogrulanamadi` | 0.585 | (bekliyor) |

## PDF sayfa 164

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Periferal vasküler hastalık | Tablo 3.36- Alt ekstremitenin periferik vasküler hastalığına bağlı engellilik. (bkz tablo 3. I) | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 166

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Periferik sinir sistemi, nöromüsküler bileşke ve kas sistemi hastalıkları | PERİFERİK SİNİR SİSTEMİ, NÖROMUSKÜLER BİLEŞKE ve KAS SİSTEMİ | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 167

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Üst ekstremite bozuklukları (santral) | Tablo 4.2.a- Üst ekstremite bozuklukları | `ad_sayfada_birebir` | 1.0 | (bekliyor) |

## PDF sayfa 168

| # | Kanonik ad | ham_satir | OCR durum | Skor | Görsel sonuç |
| --- | --- | --- | --- | --- | --- |
| 1 | Anorektal sistem nörolojik bozuklukları | Anorektal Sistem | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 2 | Cinsel fonksiyon bozukluğu | Cinsel Fonksiyon | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 3 | Solunumda nörolojik bozukluklar | Solunumda Nörolojik | `ad_sayfada_birebir` | 1.0 | (bekliyor) |
| 4 | Üriner sistem ve mesane fonksiyon bozukluğu | Üriner Sistem/Mesane | `ad_sayfada_yaklasik_inceleme` | 0.964 | (bekliyor) |
