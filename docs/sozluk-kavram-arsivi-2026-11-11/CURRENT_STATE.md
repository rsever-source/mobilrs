# Güncel çalışma durumu — 11.11.2026

## 1. Amaç

Engelli.me içinde arama/ eşleştirme için güvenilir bir kavram sözlüğü kurmak: halk dilindeki arama ifadesi → kanonik kavram → doğru mevzuat çerçevesi / madde / sayfa / gerekçeli ICD-10 bağlantısı.

Bu sözlük oran kataloğu değildir. Oranlar, Balthazard hesaplaması ve diğer hesaplama kuralları sözlüğe taşınmaz; gerekiyorsa ayrı veri/hesaplama katmanında kalır.

## 2. Bağlayıcı ayrımlar

- EK-1 (çalışma gücü kaybı/maluliyet) ile EK-2 (engellilik oranı) ayrı çerçevelerdir.
- Kayıt başına tek mevzuat bağlantısı (XOR).
- Aynı kavram iki çerçevede yer alırsa iki ayrı kayıt.
- ICD-10 yalnız EK-2 içinde.
- WHO ICD-10 etiketinin doğrulanması, kodun belirli bir mevzuat kavramıyla eşleştiğini tek başına kanıtlamaz.
- Kaynakta olmayan madde etiketi, tanım, eş anlamlı veya kod uydurulmaz.
- EK-1 derecesiz kurallar hastalık/derece kayıtlarına karıştırılmaz.

## 3. Güncel kısmi sayımlar

Kaynak JSON dosyalarının gerçek `kayitlar` dizileri üzerinden:
- `u1_ek1_001_020.json`: 135 kayıt.
- `u2_ek1_021_040.json`: 141 kayıt.
- EK-1 toplam: **276 derece kaydı**.
- EK-1 benzersiz bölüm+sıra referansı: **158**.
- EK-1 bölüm+sıra+kanonik ad grubu: **159** (J/1 altında iki ayrı kanonik ad bulunduğu için).
- EK-1 derecesiz kural maddesi: **4**, ayrı `data/ek1_derecesiz_kurallar.json`.
- `u3b_ek2_003_024.json`: **142 EK-2 adayı**.
- EK-2'de basılı `madde_etiketi` bulunmayan: **67**; şema etiketi zorunlu tutmaz, kaynakta olmayan etiket yazılmaz.
- Kısmi dataset: **418 kayıt** (276 + 142).

Önceki raporlardaki 192, 275, 154 ve 95/49 sayıları yüklenen güncel kaynak dosyalarının gerçek uzunluklarıyla uyuşmuyor. Bu arşivdeki sayımlar yüklenen dosyalardan yeniden hesaplandı.

## 4. Şema ve testler

- Güncel taslak: `schema/sozluk_kavram.v1.0.3_taslak.json`.
- JSON Schema Draft-07.
- EK-2 `madde_etiketi`, `alt_bolum` ve ayrı `tanim` alanı opsiyonel olabilir; kaynakta sadece başlık/kavram adı görünen kayıt kaybedilmez.
- Uzun resmî kanonik ad ve alt bölüm başlıkları kesilmez.
- EK-1/EK-2 kimlik önekleri bağlantıyla eşleştirilir.
- RG künyesi EK-1/EK-2'ye göre kontrol edilir.
- ICD-10 nokta biçimi kullanılır; virgüllü kod kabul edilmez.
- Raporlanan testler: 31/31 sentetik test ve 8/8 gerçek veri meta/şema kontrolü PASS; gerçek veri şema hatası 0, tekrarlı kimlik 0.
- Test PASS sonucu OCR metninin, mevzuat yorumunun veya kavram içeriğinin doğru olduğunu kanıtlamaz.

## 5. EK-2 PDF / OCR

Yüklenen `ek2_2019_rg.pdf` 172 sayfadır.
- PDF s.3–169: EK-2 kılavuzunun kavram/metin/tanım/kriter içeriği.
- PDF s.170: EK-3 Balthazard hesaplama tablosu; kavram sözlüğüne dahil edilmedi.
- PDF s.171–172: EK-4 rapor formu; EK-2 kavram kaynağı değil.
- PDF s.25–169 için OCR çalışmasıyla **555 numaralı/harfli satır adayı** çıkarıldı; `candidates/ek2_025_169_kavram_aday_havuzu.json`.
- 555 satır onaylı kavram değildir. Üst başlık, hastalık adı, açıklama, değerlendirme yöntemi, tablo satırı ve oran girdisi ayrıştırılmalı; PDF görüntüsüyle doğrulanmalı.
- `sources/ek2_172.txt` EK-4 arka yüz metnidir.

## 6. ICD-10 durumu

- Genel “kalıcı iki taraflı işitme kaybı” ifadesi sensörinöral tipi kanıtlamaz. H90.3 bu kavrama otomatik eklenmemelidir.
- WHO kod etiketi ve kod-kavram eşleşmesi ayrı doğrulamalardır.
- Eski raporlarda 8 kodluk `icd10_who.json` kanıt dosyası anılıyor; bu ham JSON bu arşive yüklenen belgeler arasında bulunmuyor. Dosya geldiğinde tam ham yanıt, URL, sürüm, tarih ve hash kontrol edilmelidir.
- H54.1, H92.0, H28.1 gibi önceki raporlarda yanlış açıklanmış kodlar körü körüne kopyalanmamalı; resmî WHO etiketi yeniden okunmalıdır.

## 7. Henüz bitmeyen işler

1. 555 OCR adayını PDF görüntüsüyle tek tek doğrula ve kavram hiyerarşisini kur.
2. OCR bozulmaları / aynı etiketle çıkan farklı alt bentler / eksik üst başlıklar için belirsizlikleri ayrı tut.
3. EK-1 ve EK-2 bütün kayıtlarını kaynak sayfa ile eşleştirip denetle.
4. Halk dili ve klinik kullanım eş anlamlılarını güvenilir kaynaklardan araştır; `es_anlamli: []` boş kalması, eş anlamlı uydurmaktan iyidir.
5. WHO ICD-10 ham kanıt dosyasını temin et ve her kodun mevzuat kavramıyla uygun özgüllükte eşleştiğini ayrıca kanıtla.
6. EK-2'nin tüm sayfalarını kapsayan doğrulanmış kavram kaydı üret.
7. Kısmi veriyi nihai `sozluk_kavram_data.json` olarak adlandırma. Nihai dosya ancak kapsam tamamlanınca oluşturulmalı.

## 8. Dosya yerleşimi

- `sources/`: Kullanıcının yüklediği kaynak JSON/TXT dosyaları.
- `scripts/`: OCR ve analiz amaçlı betikler. Arşiv kopyalarında kullanıcı profilinin mutlak Windows yolu `%TEMP%` ile maskelenmiştir.
- `schema/`: v1.0.3 taslak.
- `data/`: kısmi aday sözlük ve ayrı EK-1 kuralları.
- `candidates/`: EK-2 25–169 OCR satır adayları.
- `reports/`: denetim ve belirsizlik raporları.
- `history/`: eski şema dosyaları, yalnızca geçmiş karşılaştırma için.
