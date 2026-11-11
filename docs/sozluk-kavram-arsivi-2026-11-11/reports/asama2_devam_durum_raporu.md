# Engelli.me Kavram Sözlüğü — Devam Durumu

**Tarih:** 11.11.2026  
**Kapsam:** DeepSeek Aşama 1 şema planı + Gemini Aşama 2 denetim raporunun bağımsız değerlendirmesi.  
**Depo işlemi:** Yapılmadı.

## 1. Yapılan çalışma

- DeepSeek raporunda sunulan v1.0.0 JSON Schema metninden, `madde_etiketi` alanı zorunluluktan çıkarılarak v1.0.1 taslağı üretildi. Bu, kullanıcının 49 etiketsiz EK-2 kaydını kaybetmeme kararını uygular.
- ICD-10 kod deseninde virgül ondalık ayırıcı olarak kabul edilmez; nokta kullanılır.
- EK-1 bağlantısında Resmî Gazete tarihi/sayısı `28.09.2021 / 31612`, EK-2 bağlantısında `20.02.2019 / 30692` olacak şekilde koşullu doğrulama eklendi. EK-2 MBS numarası girilirse `31275` olmalı.
- Eski v1.0.0 şema metni korunmuştur; oluşturulan dosya taslak olarak adlandırılmıştır.
- Draft-07 şema kontrolü ve 20 senaryolu test çalıştırıldı: **20/20 PASS**.

Şema taslağı SHA256: `d554671fb2c8ba0836a41caa5d6ce92a62f86485bd8e667c981c91f97c15fcf6`  
Test betiği SHA256: `f8f4434aa84c53d0f5800ade2977acd769f88a010bf7e41bcf80d0f3b2324278`

Not: v1.0.0 şemasının gerçek çalışma klasöründeki dosyası bu oturumda bulunmadığından v1.0.1, DeepSeek raporuna gömülü şema metninden yeniden kuruldu. Bu nedenle taslaktır; gerçek v1.0.0 dosyasıyla byte-diff yapılmış değildir.

## 2. Gemini raporundan doğrulanabilen aritmetik

- Bölüm derece kayıtları toplamı: **275** (raporda verilen 17 bölüm sayısının toplamı).
- Önceki 192 toplamı yanlıştır; raporun kendi son dökümü 134 + 141 = 275 demektedir.
- A–G bölüm kayıtları 133'tür; u1 toplamı H/1 ağır kaydıyla 134 olur.
- Ancak rapordaki “benzersiz madde” bölüm sayılarının toplamı **158**'dir; raporda yazan **154** ile uyuşmuyor. Ham u1/u2 JSON dosyaları bu oturumda bulunmadığından hangi bölüm sayısının hatalı olduğu bağımsız olarak belirlenemedi.
- EK-2 s.3–24 için bildirilen 95 kaydın 46'sı etiketli, 49'u etiketsiz. v1.0.1 taslağı bu 49 kaydın `madde_etiketi` olmadan temsil edilmesine izin verir; kayıtların gerçek içeriği henüz doğrulanmadı.

## 3. İçerik kararları

- Dört EK-1 derecesiz kural maddesi (E/24, G/2, G/3, O/8) hastalık/derece kayıtlarına karıştırılmamalı; ayrı kural listesinde tutulmalı.
- Genel “kalıcı iki taraflı işitme kaybı” ifadesi sensörinöral niteliği kanıtlamaz. Bu nedenle H90.3, kaynak metin sensörinöral tip belirtmediği sürece bu kayda bağlanmamalı.
- WHO ICD-10 etiketinin doğrulanması, o kodun mevzuattaki kavramla eşleştiğini tek başına kanıtlamaz. Kod-kavram eşlemesi ayrı gerekçelendirilmelidir.

## 4. Bu aşamada üretilemeyen çıktı

`sozluk_kavram_data.json` oluşturulmadı. Çünkü Gemini raporunun dayandığı şu kaynak dosyalar bu çalışma oturumunda mevcut değil:

- `u1_ek1_001_020.json`
- `u2_ek1_021_040.json`
- `u3b_ek2_003_024.json`
- `icd10_who.json`
- EK-2 OCR dosyaları `ek2_025.txt`–`ek2_172.txt` ve `ek2_170.png`

Bu dosyalar olmadan 275 EK-1 ve 95 EK-2 kaydının tamamını asıl metinlerinden doğrulamak, 49 etiketsiz kaydın başlık/tanım bütünlüğünü kontrol etmek veya EK-2'nin 25–172. sayfalarını çıkarmak mümkün değildir. Rapordaki örnekler tam veri seti değildir.

## 5. Resmî mevzuat künyesi

Resmî Gazete kayıtları 2019 EK-2 yönetmeliğini 20.02.2019 / 30692, 2021 EK-1 yönetmeliğini 28.09.2021 / 31612 olarak gösteriyor. Kaynaklar: https://www.resmigazete.gov.tr/eskiler/2019/02/20190220-2.htm ve https://resmigazete.gov.tr/eskiler/2021/09/20210928-4.htm.

## 6. Sonraki gerekli adım

Ham `u1`, `u2`, `u3b` ve `icd10_who.json` dosyaları ile EK-2'nin 25–172. sayfa OCR/PDF kaynakları aynı çalışma alanına alınmalı. Sonra:

1. 275 EK-1 kaydının gerçek JSON uzunlukları ve bölüm dağılımı doğrulanmalı; 154/158 farkı çözülmeli.
2. 95 EK-2 kaydının tamamı v1.0.1 taslağıyla doğrulanmalı.
3. EK-2 25–172 sayfaları çıkarılmalı; 170. sayfa ayrıca görselden incelenmeli.
4. Kod-kavram eşleşmeleri, yalnızca metnin desteklediği özgüllükte yapılmalı.
5. Ancak tüm kayıtlar kaynak/sayfa bazında denetlendikten sonra nihai `sozluk_kavram_data.json` oluşturulmalı.

**Durum:** v1.0.1 şema taslağı ve 20 senaryolu test hazır. Gerçek veri üretimi ham kaynak dosyalarına erişim bekliyor. Aşama 2 tamamlanmış değildir.