# Aşama 2 — Kısmi Kaynak Denetimi ve Belirsizlikler

Bu rapor yalnızca bu oturumda yüklenen `u1`, `u2`, `u3`, `u3b` JSON dosyalarına dayanır.

## Sayım düzeltmeleri
- EK-1 `u1_ek1_001_020.json`: 135 derece kaydı.
- EK-1 `u2_ek1_021_040.json`: 141 derece kaydı.
- EK-1 toplamı: 276 derece kaydı; 158 benzersiz bölüm+sıra referansı; J/1 altındaki iki ayrı ad nedeniyle 159 bölüm+sıra+kanonik ad grubu.
- EK-2 `u3b_ek2_003_024.json`: 142 aday kayıt; 67 kayıtta basılı `madde_etiketi` yok.
- Önceki raporlardaki 275/154 ve 95/49 sayıları bu yüklenen güncel JSON'larla uyuşmuyor; bu dosyalar üzerinden sayım 276/158/142/67.

## Kaynakla karşılaştırılarak yapılan tek düzeltme
- ek2_003 / Kalıcı iki taraflı işitme engeli: u3b etiketi `2,` iken daha önceki u3 dosyasında `2.`. Aday veride `2.` kullanıldı.

## EK-2 kaynak dosyasındaki belirsizler
- **ek2_011**: Vestibüler bozukluk tablosundaki 'Sınıf 1/2/3' kriter satırları yalnızca şiddet sınıfı olduğu için kavram olarak kaydedilmedi; yalnızca 'Vestibüler bozukluklar' kaydı alındı.
- **ek2_012**: D-YÜZ bölümündeki 'Sınıf 1:' ... 'Sınıf 5:' başlık açıklamaları şiddet sınıfı tanımıdır, kavram sayılmadı; bu sınıfların altındaki durum terimleri kaydedildi.
- **ek2_013**: E-HAVA YOLU DEFEKTLERİ bölümü 'Sınıf 1-5' / 'Hava pasajı defekti mevcut / dispne' kolonlarından oluşan tablo; yalnızca sayfa ek2_014'teki açıklayıcı metin 'Hava yolu defektleri' kaydı olarak alındı.
- **ek2_015**: 'I- Zekâ işlev bozuklukları' altındaki a)-e) maddeleri (Sınırda mental kapasite, Hafif, Orta, Ağır, Çok ağır) yalnızca şiddet sınıfı etiketi olduğu için kaydedilmedi.
- **ek2_018**: TABLO I. Hastalık şiddeti değerlendirme tablosu yalnızca şiddet sınıflarını (1-HAFİF, 2-ORTA, 3-ŞİDDETLİ, 4-ÇOK ŞİDDETLİ) ve kriterlerini içeriyor; kavram sayılmadı.
- **ek2_019**: Atopik dermatit ve psoriasis altındaki 'Hafif/Orta/Şiddetli/Çok şiddetli' maddeleri şiddet sınıfı olduğu için kaydedilmedi; ayrıca OCR satır sırası karışmış ('B- Dermatitler (Kontakt dermatit, staz dermatit, dishidrotik' satırı ile 'ekzema)' satırı arasına başka satırlar girmiş).
- **ek2_020**: Hipertrofik skar ve keloid ile kan damarı hiperplazileri altındaki yüzde aralıklı şiddet maddeleri (Hafif/Orta/Şiddetli/Çok şiddetli) şiddet sınıfı olduğu için ayrı kayıt yapılmadı.
- **ek2_023**: Adı okunamayan bir hastalık bloğu var: 'I-Hafif Qlgular / 2-0rta derecede / 3-Şiçlçletli olgular / 4-Çok şiddetli' satırlarının hangi hastalığa ait olduğu OCR metninde görünmüyor; tahmin yürütülmedi.

## EK-2 kapsam dışı bırakılan sayfalar
- **ek2_004**: Kavram/tanım içermiyor: işitme ölçüm tekniği ve Tablo I/2/3 kullanım kuralları (hesaplama yöntemi).
- **ek2_005**: Tamamen tablo: 'Tablo I- a- Binaural işitme kavbl hesaolama tablosu.' sayısal oran matrisi.
- **ek2_006**: Tamamen tablo: 'Tablo I. b- Binaural işitme kaybı hesaplama tablosu.' sayısal oran matrisi.
- **ek2_007**: Tamamen tablo: Tablo 2 (işitme engeli % → engel oranı) ve Tablo 3 (işitme kaybı derecesi / dört frekans tahmini eşik toplamı).
- **ek2_009**: Kavram/tanım içermiyor: muayene yönteminin f) maddesinin devamı ve 'JALENİN DÜNYASI' okuma parçası (test materyali).
- **ek2_010**: Tamamen tablo: 'TABLO 4. KONUŞMA ENGELİ PUANININ HESAPLANMASI' puanlama tablosu.

## Ek kontrol bulguları
- `ek2_015` sayfasında `Atipik otizm` ve `Otizm` kayıtları aynı `d)` etiketiyle geçiyor. Etiket OCR kaynağıyla netleştirilmeden değiştirilmedi.
- `ek2_019` sayfasında `B- Dermatitler` satırında OCR satır kayması raporlanmış; kaynak sırası bağımsız görsel teyit bekliyor.
- `ek2_023` sayfasında bazı şiddet satırlarının bağlı olduğu hastalık başlığı OCR'da görünmüyor; tahminle kayıt üretilmedi.
- `ek2_021` sayfasında `Eritroderma` iki ayrı kayıt/başlık düzeyinde yer alıyor. Kaynak hiyerarşisi görsel olarak kontrol edilmeli; otomatik birleştirme yapılmadı.
- 67 EK-2 kaydında `madde_etiketi` yok. v1.0.3 bu alanı opsiyonel kabul eder; eksik etiket uydurulmadı.
- Kaynak metinde tanım alanı kanonik adın aynısıysa `tanim` çıktı kaydına kopyalanmadı. Ham kaynak izi `sozluk_kavram_kaynak_izleri_kismi.json` içinde korundu.
- Eş anlamlılar için kaynak veri sağlanmadığından tüm kayıtlarda `es_anlamli: []` bırakıldı. Halk dili eş anlamlıları henüz çalışılmadı.
- Bu sayfalarda kanıtlanmış bir ICD-10 kavram eşlemesi yok. H90.3, genel 'kalıcı iki taraflı işitme kaybı' ifadesine sensörinöral alt tip kanıtı bulunmadığı için eklenmedi.

## Henüz sağlanmayan kaynaklar
- EK-2 s.25–172 OCR/PDF kaynakları yüklenmedi; 170. sayfanın görseli de bu ekler arasında yok.
- Bu nedenle mevcut JSON, EK-2'nin tamamı değil; yalnızca s.3–24 adaylarını içerir.
- Kaynak dosyalar dışında 2019 ve 2021 eklerinin tüm sayfaları yeniden görsel denetimden geçmedi.

## EK-1 derecesiz kuralları
- 4 madde ayrı `ek1_derecesiz_kurallar.json` dosyasına alındı. Bunlar 276 derece kaydına dahil değildir.

## Sonuç
- Bu paket kısmi bir aday veri derlemesidir; nihai `sozluk_kavram_data.json` değildir.
- Şema PASS sonucu, OCR metninin hukuki/içerik doğruluğunu veya kullanıcı dili eş anlamlılarını kanıtlamaz.