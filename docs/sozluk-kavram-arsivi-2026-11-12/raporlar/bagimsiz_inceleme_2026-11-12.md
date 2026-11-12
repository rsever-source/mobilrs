# Bağımsız GitHub incelemesi — 12.11.2026

## Kısa sonuç

İnceleme dalı: `archive/sozluk-kavram-asama2-devam-2026-11-12`

- `data/sozluk_kavram_data.json` GitHub'dan indirilebilir ve geçerli JSON olarak ayrıştırıldı: **745 kayıt**.
- Dağılım: **276 EK-1 + 469 EK-2**.
- `kavram_id` alanında **745/745 benzersiz** kimlik var.
- Yeni EK-2 kaynak listesi **259 kayıt**, **12 bölüm**, PDF sayfa **29-169** aralığında ve 82 farklı sayfaya dağılmış.
- 259 yeni kaydın tamamı nihai veri dosyasında aynı PDF sayfası + kanonik ad eşleşmesiyle bulundu.
- EK-2 toplamında 17 üst bölümün tamamı temsil ediliyor.
- Kaynak izleri dosyasında 745 kayıt var; durum dağılımı **596 birebir, 11 düzeltilmiş, 138 bulanık**, boş kanıt metni 0.

Bu kontroller dosyanın arşivde bulunmasını, JSON yapısını ve kayıtların kaynak listesiyle bütünleşmesini doğrular. Tek başına tıbbi kavramların PDF görüntüsüne göre doğru sınıflandırıldığını kanıtlamaz.

## Önemli bulgu: 259/259 "birebir" kontrolünün kapsamı

Mevcut `arac/ek2_ek_dogrula.py` betiği, her kayıttaki `ham_satir` metninin ilgili sayfanın OCR metninde bulunup bulunmadığını kontrol ediyor. `kanonik_ad` değerinin aynı kanıt satırında veya sayfanın başka bir yerinde bulunduğunu kontrol etmiyor.

Ayrıca `arac/kanit_izi.py`, yeni kayıtlar için `arac/ek2_kaynak_eslesme.json` dosyasındaki `durum` değerini doğrudan kanıt durumuna aktarıyor. Dolayısıyla rapordaki 259/259 sonucu, **ham satırın sayfada bulunması** için geçerli; kavram adının her bir kanonik kayda doğru bağlandığına ilişkin bağımsız bir kontrol değil.

Benim bağımsız metin kontrolümde, Türkçe karakter ve noktalama farkları normalleştirildiğinde:

- **160/259** kanonik ad, kendi kaydındaki `ham_satir` alanında doğrudan bulunuyor.
- **99/259** kanonik ad, kendi `ham_satir` alanında doğrudan bulunmuyor.

Bu 99 kayıt otomatik olarak yanlış değildir. Ad başka OCR satırında bulunabilir, OCR yazımı farklı olabilir veya ad birkaç satırın birleştirilmesiyle oluşmuş olabilir. Fakat bu kayıtlar için kanıt satırı ilişkisinin güçlendirilmesi gerekir.

Örnek: s.40'taki `Kontrast duyarlık ve kamaşma (glare) kusuru` kaydının `ham_satir` değeri `o Tek gözde mevcut ise`. Aynı sayfanın OCR metninde kavramın kendisi daha üst satırlarda bulunuyor. Kayıt muhtemelen doğru, ancak mevcut kanıt satırı kavramı göstermiyor.

Bu amaçla `arac/ek2_kavram_kanit_kontrol.py` eklendi. Betik ana veriyi değiştirmez; kanonik adı ilgili sayfanın tamamında arar, 1-4 satırlık OCR pencerelerinde yakın eşleşme arar ve inceleme listesini `raporlar/ek2_kavram_kanit_kontrol.json` dosyasına yazar.

Çalıştırma:

```powershell
python -X utf8 arac\ek2_kavram_kanit_kontrol.py
```

Betik GitHub arşivine eklendi; bu oturumda GitHub içeriğini yeniden klonlayıp bütün 82 OCR sayfası üzerinde çalıştırmadım. Çıktı alındığında birebir, yaklaşık ve bulunamayan adlar ayrı incelenmelidir. OCR metin kontrolü de orijinal PDF görüntüsü üzerinde görsel teyidin yerine geçmez.

## İçerik sınıflandırması için öneri

259 yeni kayıt içinde hastalık adlarının yanında işlev kaybı, anatomik bozukluk, prosedür, sistem başlığı ve değerlendirme başlığı niteliğindeki terimler de var. Örnekler:

- `Kalp transplantasyonu`, `Gastrostomi`: işlem / durum terimleri.
- `Alt ekstremite sorunları`, `Üst ekstremite sorunları`: değerlendirme başlığı.
- `Anorektal sistem nörolojik bozuklukları`: fonksiyon bozukluğu kategorisi.
- `Sistemik romatizmal hastalıklar` (s.169): raporun da belirttiği üzere sayfada hastalık listesi değil, bölüm başlığı ve değerlendirme kuralı var.

Bunlar vatandaşın arama yapmasında yine yararlı olabilir; ancak hepsini "hastalık" olarak değerlendirmek doğru olmaz. Nihai arama katmanında `hastalık`, `bulgu`, `fonksiyon_kaybi`, `işlem_durum`, `anatomik_terim`, `degerlendirme_basligi` gibi bir kayıt türü ayrımı önerilir. Bu ayrım mevcut v1.0.3 şemasına bu commit'te eklenmedi.

## Sonraki iş

1. Yeni eklenen 259 kaydın tümünde kanonik ad–OCR sayfası eşleşmesini `ek2_kavram_kanit_kontrol.py` ile üret.
2. Yaklaşık veya bulunamayanları PDF sayfa görüntülerinden tek tek teyit et.
3. Başlık / hastalık / fonksiyon kaybı / prosedür kayıt türlerini ayrı işaretle.
4. `bulanik` durumundaki 138 eski kaydı da aynı sayfa-temelli yöntemle ele al.
5. Ancak bu incelemeden sonra yeni kayıtların "doğrulandı" statüsü kesinleştirilsin.

## Değişiklik sınırı

Bu bağımsız incelemede `sozluk_kavram_data.json` veya şema değiştirilmedi. Yalnızca kontrol betiği ve bu rapor eklendi. `main`, `cloud-run-migration`, ilk yedek dal ve canlı hizmete dokunulmadı.
