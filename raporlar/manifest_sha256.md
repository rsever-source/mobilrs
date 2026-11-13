# SHA-256 Manifest for Aşama 1 Değişiklikleri

## Değişiklik Bilgileri

### 1. kanit_izi.py
- **SHA-256**: 922ed78bae00b5533633ce56c01bfed0b4bd0365d89c1b3a48fac936aa4f3dfe
- **Boyut**: 12456 bytes
- **Açıklama**: Bulanık skorların sabit 1.0 ataması kaldırıldı, skorlar referans dosyasından okunuyor ve korunuyor. Frontal kemik ve Glare istisnaları korunuyor.

### 2. data/sozluk_kavram_kaynak_izleri.json
- **SHA-256**: 00e95690313814698dfca175f138b7e8bfa504df7b715a785ea0d99bbc747ccd
- **Boyut**: 121726 bytes
- **Açıklama**: 606+1 girişten `skor: null` alanları çıkarıldı, 137 bulanık kaydın skoru (115 with skor=1.0, 22 with orijinal değerler) korunuyor, frontal ve glare istisnası korunuyor. Non-bulanik kayıtlarda skor anahtarı tamamen kaldırıldı.

### 3. raporlar/ab99cb4_durum_map.json (Yeni Eklenen)
- **SHA-256**: 521830b4aea46b4895eaff15dda9eaa5024597b2906737d25dd011ca7b288244
- **Boyut**: 37421 bytes
- **Açıklama**: 745 kaydın orijinal durum haritası (11 duzeltilmis, 596 birebir, 138 bulanik)

### 4. raporlar/ab99cb4_kanit_izleri.json (Yeni Eklenen)
- **SHA-256**: 2d2898186cb9b16844bb1d1cfe2f5de5898e5ada4e6678d56b2bbb8cc1e5a04b
- **Boyut**: 121448 bytes
- **Açıklama**: 745 kaydın orijinal kanit ve skor haritası (137 bulanik kaydın skor değerleri korundu)

## Başarı Kriterleri
- 745 kayıt, 745 benzersiz ID.
- EK-1: 276, EK-2: 469.
- Durum dağılımı: 595 birebir, 137 bulanik, 13 duzeltilmis.
- 137 bulanık kaydın skorlarının: 115'i 1.0, 22'si referanstaki özgün skorlar (0.802-0.994).
- Frontal kemik ve Glare istisnaları doğru.
- 743 kaydın bütün alanları ab99cb4 ile birebir aynı (0 mismatch).
- İki betik çalıştırıldığında sonuç değişmiyor (idempotent).
- Manifestteki SHA-256 değerleri ve dosya boyutları gerçek dosyalarla eşleşiyor.
- Mutlak Windows yolu kalmamış.
- Şema v1.0.3 ve diğer aşamaların raporları değişmemiyor.
- main, cloud-run-migration, canlı siteye müdahale yok.