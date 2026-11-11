# Gelecek oturum için başlangıç yönergesi

Bu klasör bir çalışma arşividir. Önce `README.md`, `CURRENT_STATE.md`, `DECISIONS.md` ve `MISSING_FILES.md` dosyalarını oku.

## Ne yapmaya çalışıyoruz?

Engelli.me için halk dilindeki ifadeleri doğru resmî kavramlara eşleyen bir kavram sözlüğü oluşturuyoruz. Bu işlem oran hesaplayıcısı veya oran kataloğu üretme işi değildir.

## Başlamadan önce

1. `schema/sozluk_kavram.v1.0.3_taslak.json` ve `data/sozluk_kavram_data_kismi_v1.0.3.json` dosyalarını birlikte incele.
2. `sources/` içindeki ham JSON dosyalarını kaynak kabul et; `reports/` içindeki model raporlarını yalnızca geçmiş değerlendirme olarak gör.
3. Sayım konusunda şu değerleri koru: EK-1 276, EK-2 s.3–24 142, toplam kısmi veri 418. Bu değerler tam mevzuat toplamı değildir.
4. `candidates/ek2_025_169_kavram_aday_havuzu.json` içindeki 555 satırın tümünü otomatik kavram sayma. Önce başlık/tanım/yöntem/tablo/oran ayrımı yap.
5. Her kavramı orijinal PDF sayfasıyla doğrula. OCR yanlışlarını sessizce düzeltme; belirsiz kayıtları ayrı raporla.
6. EK-1 ile EK-2'yi karıştırma. Balthazard, oran ve hesaplama kurallarını kavram sözlüğüne aktarma.
7. ICD-10 etiketinin doğru olması, mevzuat kavramına doğru eşleştiği anlamına gelmez. H90.3 gibi alt tip kodlarını genel ifadeye bağlama.
8. Halk dili eş anlamlıları için güvenilir kaynak ve kaynak türü kaydet; uydurma eş anlamlı ekleme.
9. Önce küçük, sayfa bazlı ve denetlenebilir partiler oluştur. Tüm kaynak doğrulanmadan nihai `sozluk_kavram_data.json` üretme.
10. Hiçbir arşiv dosyasını üzerine yazma. Yeni sürüm ve rapor üret; mevcut hash'leri koru.

## İlk önerilen iş

EK-2 PDF s.25–169 için 555 OCR adayını:
- kanonik kavram,
- üst bölüm/alt bölüm başlığı,
- tanım veya kriter metni,
- değerlendirme yöntemi,
- oran tablosu satırı,
- yalnızca OCR gürültüsü

olarak sınıflandıran bir insan-denetim tablosu hazırla. Sonra ilk sayfa grubunu kaynak PDF görüntüleriyle karşılaştırıp yalnızca doğrulanan kavramları v1.0.3 şemasına aktar.
