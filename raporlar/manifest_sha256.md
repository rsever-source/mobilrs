# SHA-256 Manifest for Aşama 1 Değişiklikleri

## Değişiklik Bilgileri

### 1. kanit_izi.py
- **SHA-256**: 7c9775f9a1027691e1193086cddefb5a0ef61bb2717e498f1f183b351bbd9096
- **Boyut**: 12191 bytes
- **Açıklama**: Mutlak Windows yollarının kaldırılması, relative path kullanımı, skorların referans dosyasından okunması

### 2. data/sozluk_kavram_kaynak_izleri.json
- **SHA-256**: f5b7206fbdff19159323ca069ec95033da94675a55ff3be5634cae452bf1e8a2
- **Boyut**: 111586 bytes
- **Açıklama**: 22 blayıks kaydın orijinal skorlarının (1.0 dışı) geri yüklenmesi,frontal ve glare istisnası korunması

### 3. raporlar/ab99cb4_durum_map.json (Yeni Eklenen)
- **SHA-256**: 521830b4aea46b4895eaff15dda9eaa5024597b2906737d25dd011ca7b288244
- **Boyut**: 37421 bytes
- **Açıklama**: 745 kaydın orijinal durum haritası (11 duzeltilmis, 596 birebir, 138 bulanik)

### 4. raporlar/ab99cb4_kanit_izleri.json (Yeni Eklenen)
- **SHA-256**: 2d2898186cb9b16844bb1d1cfe2f5de5898e5ada4e6678d56b2bbb8cc1e5a04b
- **Boyut**: 121448 bytes
- **Açıklama**: 745 kaydın orijinal kanit ve skor haritası (137 bulanik kaydın skor değerleri korundu)

## Başarı Kriterleri
- Toplam 745 kayıt, 745 benzersiz ID
- EK-1: 276, EK-2: 469
- Durum dağılımı: 595 birebir, 137 bulanik, 13 duzeltilmis
- 137 bulanık kaydın skorlarının tamamı referans dosyasındaki değerlerle birebir aynı
- Frontal ve Glare istisnaları doğru
- 743 kaydın bütün alanları ab99cb4 ile birebir aynı
- İki betik çalıştırıldığında sonuç değişmemeli
- Manifest hashler gerçek dosya içerikleriyle doğrulanmalı