# Engelli.me Kavram Sözlüğü — Devam Denetimi

**Tarih:** 11.11.2026  
**Kapsam:** DeepSeek Aşama 1 çıktıları + Gemini Aşama 2 raporu + resmî mevzuat/PDF kontrolü.  
**Depo:** Değişiklik yapılmadı.

## 1. Çalışmanın amacı

Kullanıcının günlük/halk dilindeki ifadelerini, doğru resmî kavrama ve ilgili mevzuat konumuna bağlayan bir sözlük oluşturmak. EK-1 (çalışma gücü kaybı/maluliyet) ile EK-2 (engellilik değerlendirmesi) ayrı kayıt evrenleri olarak kalır. Ortak kavram iki ayrı kayıt olur. Oran hesaplama, Balthazard ve mevzuatta olmayan kurallar sözlük kavramı gibi üretilmez. ICD-10 etiketi doğrulaması ile ICD kodunun belirli bir EK-2 kavramına eşleşmesi ayrı denetlenir.

## 2. Yapılan teknik işler

- v1.0.1 mevcut taslağı korundu; özgün v1.0.0/v1.0.1 dosyalarının üzerine yazılmadı.
- v1.0.1 testleri yeniden çalıştırıldı: 20/20 ve genişletilmiş bağımsız testler 24/24 PASS.
- Kaynak PDF'nin gerçek yapısı v1.0.1'de ek bir eksikliği gösterdi: EK-2'de bazı hastalıklar yalnızca ad + oran satırı olarak listeleniyor, ayrı açıklama cümlesi yok. Her EK-2 kaydında `tanim` zorunlu tutulursa tanım uydurmak gerekir.
- Bu nedenle ayrı bir **v1.0.2 taslağı** hazırlandı: EK-2 `tanim` opsiyonel; `kaynak.sayfa_no` zorunlu; bir ICD-10 kodu eklenirse `esleme_notu` zorunlu.
- v1.0.2 şeması: 29/29 test PASS.
- Veri doğrulayıcı CLI hazırlandı. Şema hatalarını, kayıtlar arası kimlik tekrarını, aynı kayıttaki ICD tekrarını, eş anlamlı tekrarını ve tüm tarih alanlarının takvim geçerliliğini ayrı denetler; varsa WHO kanıt dosyasındaki kod/etiket/URL ile eşleşmeyi kontrol eder.

## 3. Resmî kaynak kontrolü

### EK-1

Resmî yönetmeliğin tam adı **Maluliyet ve Çalışma Gücü Kaybı Tespiti İşlemleri Yönetmeliği**; 28.09.2021 tarihli ve 31612 sayılı Resmî Gazete'de yayımlanmıştır. Önceki örneklerde kullanılan kısa/eski “Maluliyet Tespiti İşlemleri Yönetmeliği” başlığı kayıtların `belge_adi` alanında kullanılmamalıdır.

- Madde 5/4 ve 6/2: birden fazla hastalıkta en ağır sekel bulgu dikkate alınır; Balthazard uygulanmaz.
- Madde 18: hastalık listesindeki tıbbi kriterler Kurumca en geç üç yılda bir değerlendirilir. Bu hüküm, değerlendirme yapılmış olduğunu tek başına kanıtlamaz; SGK'nın fiilî revizyon durumu ayrıca araştırılmalıdır.
- Resmî metin: https://resmigazete.gov.tr/eskiler/2021/09/20210928-4.htm
- Bakanlığın yayımladığı mevzuat metni: https://aile.gov.tr/eyhgm/mevzuat/ulusal-mevzuat/yonetmelikler/maluliyet-ve-calisma-gucu-kaybi-tespiti-islemleri-yonetmeligi/

### EK-2

Resmî başlık **Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik**; 20.02.2019 tarihli ve 30692 sayılı Resmî Gazete'de yayımlanmıştır.

- Madde 4/1(g) ICD kodunu tanımlar.
- Madde 8/1(c) ICD kodlarının muayene formunda yer almasını düzenler. Bu, her ICD kodunun EK-2 alan kılavuzundaki belirli bir satıra otomatik eşlendiğini göstermez.
- Madde 10/3-5 EK-2 alan kılavuzunu ve fonksiyon kayıplarını esas alır. Madde 10/4 birden fazla engelde Balthazard ve 65 yaş üzeri için %10 eklemeyi düzenler.
- Resmî metin: https://www.resmigazete.gov.tr/eskiler/2019/02/20190220-2.htm
- EK-2 PDF (172 sayfa): https://www.resmigazete.gov.tr/eskiler/2019/02/20190220-2-1.pdf
- Bakanlığın yayımladığı mevzuat metni: https://www.aile.gov.tr/eyhgm/mevzuat/ulusal-mevzuat/yonetmelikler/eriskinler-icin-engellilik-degerlendirmesi-hakkinda-yonetmelik/

Resmî PDF'nin 3. sayfasında KBB / A-İŞİTME altında “Kalıcı işitme engeli” ve “Kalıcı iki taraflı işitme engeli” tanımları görülüyor. İkinci tanım yalnızca iki taraflı işitme kaybı diyor; sensörinöral tip belirtmiyor. Bu nedenle H90.3 bu genel kavrama eklenmedi.

Resmî PDF'nin basılı 20. sayfasında bazı hastalıklar yalnız hastalık adı ve oran satırlarıyla listeleniyor. Bu kayıtlar için ayrı bir tanım cümlesi yoksa `tanim` alanı boş bırakılmalı/yazılmamalı; açıklama uydurulmamalı.

## 4. Kısmi, kaynaklı veri başlangıcı

`sozluk_kavram_data_kismi_ek2_s03.json` içinde resmî PDF'nin 3. sayfasından iki EK-2 kavramı çıkarıldı:

1. Kalıcı işitme engeli
2. Kalıcı iki taraflı işitme engeli

Her iki kayıtta da bölüm, alt bölüm, madde etiketi, birebir tanım, Resmî Gazete künyesi, PDF URL'si ve sayfa numarası bulunur. Kaynak metin sensörinöral tür belirtmediği için ICD-10 eşlemesi eklenmedi. Kayıtlar v1.0.2 ile **2/2 PASS**; veri düzeyi hatası ve uyarısı yok.

Bu iki kayıt yalnızca ilk kaynaklı parçadır; nihai `sozluk_kavram_data.json` değildir.

## 5. Sayım çelişkileri — çözülmedi

Gemini raporları arasında EK-1 için önce 104+88=192, sonra 134+141=275 sayıları verilmiştir. Son rapordaki bölüm derece sayıları 275'e toplansa da “benzersiz madde” sütunundaki bölüm değerleri 158'e toplandığı hâlde raporda 154 denmiştir. Ham `u1_ek1_001_020.json` ve `u2_ek1_021_040.json` bu oturumda bulunmadığından hangi sayının doğru olduğu bağımsız olarak teyit edilemedi.

EK-2 s.3–24 için 95 kayıt, bunların 46'sında etiket ve 49'unda etiketsiz kayıt olduğu Gemini tarafından raporlandı. Ham `u3b_ek2_003_024.json` bu oturumda bulunmadığından 95/46/49 sayıları henüz bağımsız olarak yeniden hesaplanamadı. v1.0.2 taslağı etiketsiz kaydı ve ayrı tanımı olmayan liste öğesini destekler.

## 6. Amaç açısından hâlâ açık olan iş

Şu anda oluşturulan örnek kayıtlar resmî kavram adlarını ve kaynak konumlarını içeriyor; `es_anlamli` alanları boş. Bu nedenle sözlük henüz halk dilindeki aramaları eşleştirme amacını tamamlamış değildir. Önce kanonik mevzuat kayıtları tamamlanmalı; ardından halk dili karşılıkları, mevcut site arama terimleri ve güvenilir terminoloji kaynaklarıyla ayrı bir eşleştirme turunda eklenmelidir. Kaynaksız eş anlamlı üretilmemelidir.

## 7. Gerçek veri üretimini tamamlamak için eksik ham girdiler

Bu oturumdaki dosyalar arasında aşağıdaki kaynak dosyalar yoktur:

- `u1_ek1_001_020.json`
- `u2_ek1_021_040.json`
- `u3b_ek2_003_024.json`
- `icd10_who.json`
- EK-2 OCR `ek2_025.txt`–`ek2_172.txt` ve `ek2_170.png`

Bunlar olmadan önceki 275 EK-1 / 95 EK-2 adayını asıl kayıtlarla karşılaştırmak veya EK-2'nin 25–172. sayfalarını eksiksiz çıkarmak mümkün değildir. Resmî PDF bağlantısı bulunmuş olsa da bu çalışma ortamında PDF'nin tam dosya baytları indirilemedi; seçili sayfalar görsel olarak kontrol edilebildi.

## 8. Durum

- v1.0.1: korunuyor.
- v1.0.2: kaynak yapısına göre hazırlanan taslak; 29/29 test PASS.
- v1.0.1 bağımsız testler: 24/24 PASS.
- v1.0.1 ilk test paketi: 20/20 PASS.
- Kısmi EK-2 s.3 veri: 2/2 PASS.
- Nihai sözlük verisi: oluşturulmadı.
- Git/proje deposu: değiştirilmedi.
- Aşama 2: devam ediyor, tamamlanmadı.