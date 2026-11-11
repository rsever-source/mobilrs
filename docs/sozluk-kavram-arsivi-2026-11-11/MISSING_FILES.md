# Devam için eksik / yeniden sağlanması gereken kaynaklar

1. **Özgün `ek2_2019_rg.pdf` ikili dosyası:** Bu arşivde PDF'nin kendisi yok; SHA-256 ve kaynak künyesi `PDF_SOURCE.md` içinde. OCR aday havuzu eklendi.
2. **`icd10_who.json` ham kanıt dosyası:** Önceki raporlar sekiz WHO kodunun ham kanıt dosyasına atıf yapıyor, fakat ham JSON dosyası bu arşiv commit'inde bulunmuyor.
3. **Tam sayfa OCR dökümü:** 25–169 sayfaları için OCR aday havuzu eklendi; sayfa başına ham OCR metin paketi bu commit'e eklenmedi.
4. **Eski ana şema / Aşama 1 kaynak raporlarının bazı sürümleri:** Tarihsel şema kopyaları ve model denetim raporlarının bir kısmı `history/` ve `reports/` altındadır. Kullanılacak tek güncel taslak v1.0.3 olarak işaretlenmiştir; önceki dosyalar gerektiğinde karşılaştırma içindir.
5. **Tam OCR / PDF görüntü karşılaştırması:** EK-2 25–169 adayları kaynak görüntüleriyle manuel doğrulama bekliyor.

Eksik dosyalar varmış gibi davranma. Yeniden sağlandıklarında SHA-256 ile kaydet ve bu arşive yeni bir ek commit oluştur.
