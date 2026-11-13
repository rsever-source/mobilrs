# SHA-256 Manifest for Aşama 1 Değişiklikleri

## Değişiklik Bilgileri

### 1. kanit_izi.py
- **SHA-256**: 4c874f8ce0a1da3c3f41aca5151e817f9b6a7925065bc7d4fba0079056673703
- **Boyut**: 13171 bytes
- **Açıklama**: Bulanık skorların sabit 1.0 ataması kaldırıldı, skorlar referans dosyasından okunuyor ve korunuyor. Frontal kemik ve Glare istisnaları korunuyor.

### 2. data/sozluk_kavram_kaynak_izleri.json
- **SHA-256**: dda5f65ca6fd978254d6073ba6369a77d9944007be6f2479a47bca3d35567957
- **Boyut**: 111627 bytes
- **Açıklama**: 607 `skor: null` alanları çıkarıldı, 137 bulanık kaydın skoru (115 with skor=1.0, 22 with orijinal değerler) korunuyor, frontal ve glare istisnası korunuyor. Non-bulanik kayıtlarda skor anahtarı tamamen kaldırıldı.

### 3. raporlar/ab99cb4_durum_map.json (Yeni Eklenen)
- **SHA-256**: 521830b4aea46b4895eaff15dda9eaa5024597b2906737d25dd011ca7b288244
- **Boyut**: 37421 bytes
- **Açıklama**: 745 kaydın orijinal durum haritası (11 duzeltilmis, 596 birebir, 138 bulanik)

### 4. raporlar/ab99cb4_kanit_izleri.json (Yeni Eklenen)
- **SHA-256**: 0a45ebf1c84a0d332f40d4835b51e68113ae372dc7dce3bdda885c6a3e08e3b4
- **Boyut**: 117583 bytes
- **Açıklama**: 745 kaydın orijinal kanit ve skor haritası (137 bulanik kaydın skor değerleri korundu)

## Başarı Kriterleri
- 745 kayıt, 745 benzersiz ID.
- EK-1: 276, EK-2: 469.
- Durum dağılımı: 595 birebir, 137 bulanik, 13 duzeltilmis.
- 137 bulanık kaydın skorlarının: 115'i 1.0, 22'si referansteki özgün skorlar.
- Frontal kemik ve Glare istisnaları doğru.
- 743 kaydın bütün alanları ab99cb4 ile birebir aynı (0 mismatch).
- İki betik çalıştırıldığında sonuç değişmiyor (idempotent).
- Manifestteki SHA-256 değerleri ve dosya boyutları gerçek dosyalarla eşleşiyor.
- Mutlak Windows yolu kalmamış.
- Şema v1.0.3 ve diğer aşamaların raporları değişmemiyor.
- main, cloud-run-migration, canlı siteye müdahale yok.