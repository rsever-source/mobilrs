# Aşama 2 — Yeni Yüklenen Kaynaklarla Devam Raporu

## 1. Yeni kaynakların durumu

- `ek2_2019_rg.pdf`: 172 sayfa. PDF görüntüleri incelendi; PDF sayfaları 25-169 için OCR metni üretildi.
- `ek1_025.txt`: EK-1 OCR parçası alındı. Metin, alt/üst ekstremite işlev ölçütlerinin devamı ile gastroenteroloji bölümüne geçiş içeriyor. `u2` içinde `ek1_025` sayfasına bağlanmış Portal hipertansiyona bağlı gastrointestinal kanama kaydı bulunuyor; ancak OCR parçası ile bütün sayfa içeriği satır satır eşleştirilmiş sayılmıyor. Bu nedenle EK-1'e yeni kayıt eklenmedi.
- `ek2_172.txt`: EK-4 rapor formunun arka yüzüne ait. EK-2 kavram kaynağı değildir.

## 2. PDF sayfa ayrımı

| PDF sayfası | İçerik | Sözlük kapsamı |
|---|---|---|
| 1-2 | Sağlık kurulu raporu formu (EK-1 form yüzleri) | Hastalık/kavram kaydı değil |
| 3-169 | EK-2 engel alanları kılavuzu, vücut sistemleri ve kriterler | Kavram kaynağı |
| 170 | EK-3 Balthazard Hesaplama Tablosu | Hesaplama tablosu; kavram sözlüğüne aktarılmadı |
| 171-172 | EK-4 terör/kaza/yaralanma rapor formu | EK-2 kavram kaynağı değil |

Önemli: Önceki raporlarda `ek2_170.txt` boş olduğu için bekleyen sayfa olarak yazılmıştı. Yüklenen PDF'deki 170. sayfa görüntüsü incelendi; bu sayfa EK-3 Balthazard Hesaplama Tablosu. Sözlük kavram sayfası değildir. `ek2_172.txt` de EK-4 arka yüzüdür.

## 3. Tamamlanan OCR

- PDF sayfa 25-169: **145/145 sayfa** OCR metni üretildi.
- OCR aday havuzu: **555 numaralı/harfli satır adayı**.
- Her aday satırın PDF sayfası, Resmî Gazete basılı sayfası, ham satırı ve önceki/sonraki satır bağlamı saklandı.
- OCR adayları nihai sözlük kaydı değildir; insan kontrolü gerektirir.

## 4. Bölüm bazında OCR aday satırları

| Bölüm | OCR satır adayı |
|---|---:|
| OMURGA VE ÜST EKSTREMİTE | 107 |
| HEMATOLOJİK HASTALIKLAR | 101 |
| ENDOKRİN SİSTEM VE METABOLİZMA | 66 |
| KARDİYOVASKÜLER SİSTEM | 58 |
| ALT EKSTREMİTE | 47 |
| GÖRME SİSTEMİ | 42 |
| YANIKLAR | 31 |
| KADIN GENİTAL SİSTEM | 22 |
| SİNİR SİSTEMİ | 22 |
| ÜRİNER SİSTEM VE ERKEK GENİTAL SİSTEM | 14 |
| SANTRAL VE PERİFERİK SİNİR SİSTEMİ | 13 |
| SİNDİRİM SİSTEMİ | 12 |
| GÖĞÜS HASTALIKLARI VE GÖĞÜS CERRAHİSİ | 9 |
| TÜMÖRLERİN SINIFLAMASI | 8 |
| SİSTEMİK ROMATİZMAL HASTALIKLAR | 3 |

## 5. EK-1 / EK-2 önceki sayımının düzeltilmesi

- `u1_ek1_001_020.json`: **135** derece kaydı.
- `u2_ek1_021_040.json`: **141** derece kaydı.
- EK-1 toplamı: **276** derece kaydı.
- EK-1 benzersiz bölüm+sıra referansı: **158**.
- EK-1 bölüm+sıra+kanonik ad grubu: **159**.
- Derecesiz EK-1 kural maddesi: **4**, ayrı dosyada.
- `u3b_ek2_003_024.json`: **142** aday.
- Basılı `madde_etiketi` bulunmayan EK-2 kaydı: **67**.

Önceki Gemini raporundaki 134+141=275 toplamı, yüklenen u1 dosyasının gerçek uzunluğuyla uyuşmuyor: u1 dizisi 135 kayıttır. Bu nedenle doğru toplam 276'dır.

## 6. ICD-10 eşlemesi

- Bu yeni sayfa OCR adaylarına ICD-10 kodu otomatik eklenmedi.
- WHO etiketinin doğruluğu, kodun belirli bir EK-2 kavramıyla eşleştiğini tek başına kanıtlamaz.
- Özellikle genel işitme kaybı maddesine H90.3 eklenmedi; kaynak metin sensörinöral alt tipi belirtmiyor.

## 7. Henüz yapılmayan / açık işler

1. 555 OCR satır adayı içinden gerçek kavram başlıkları, tanımlar, tablo başlıkları ve yöntem adımları ayrıştırılmalı.
2. OCR hatalı görünen satırlar PDF görselinden tek tek düzeltilmeli; tahminle düzeltme yapılmamalı.
3. Kavram adı tekrarları ve bölüm/alt bölüm hiyerarşisi elle denetlenmeli.
4. Halk dili eş anlamlıları için ayrı kaynak/terim araştırması yapılmalı; şu an eş anlamlı alanları boş.
5. ICD-10 eşlemesi yalnızca kavram metninin desteklediği özgüllükte eklenmeli.
6. Ancak manuel doğrulama sonrası sayfa 25-169 adayları v1.0.3 şemasıyla nihai veriye aktarılmalı.

## 8. Testler

- [x] OCR sayfa kapsamı 25-169 tam
- [x] OCR boş sayfa yok
- [x] OCR aday kimlikleri benzersiz
- [x] Adayların sayfa aralığı 25-169
- [x] Adayların ham satır ve terim alanı dolu
- [x] Mevcut 418 veri seti korunmuş
- [x] EK-1 kaynak kayıt sayısı yeniden hesaplandı
- [x] EK-2 u3b kaydı yeniden sayıldı
- [x] Etiketsiz EK-2 kaynak kaydı sayısı
- [x] EK-1 derecesiz kural sayısı

Toplam aday havuzu testi: **10/10 PASS**.

Bu rapor, sözlük amacını korur: EK-1 çalışma gücü kaybı ve EK-2 engellilik oranı ayrı tutulur; kavramlar yalnız resmi metnin desteklediği ölçüde tanımlanır; oran kataloğu ve Balthazard hesaplama kuralları kavram sözlüğüne karıştırılmaz.