# Engelli.me — Kavram Sözlüğü çalışma arşivi

Bu klasör, EK-1 / EK-2 kavram sözlüğü çalışmasının kaynaklarını, ara verilerini, denetim raporlarını ve devam kararlarını saklar.

> **Bu arşiv uygulama kodu değildir.** İçindeki `sozluk_kavram_data_kismi_v1.0.3.json` kısmi çalışma verisidir; nihai sözlük veya canlıya alınabilir veri değildir.

## Çalışmanın amacı

Kullanıcının günlük/halk dilinde aradığı ifadeyi, doğru resmî kavrama ve ilgili mevzuat kaydına bağlayan denetlenebilir bir sözlük oluşturmak. EK-1 ile EK-2 birbirine karıştırılmaz:

- EK-1: çalışma gücü kaybı / maluliyet çerçevesi.
- EK-2: engellilik oranı çerçevesi.
- Bir kavram her iki mevzuatta da bulunuyorsa iki ayrı kayıt tutulur.
- Her kayıt yalnızca bir mevzuat bağlantısına sahip olur.
- ICD-10 yalnızca EK-2 kaydında ve kavramla özgüllük düzeyinde gerçekten eşleşiyorsa kullanılır.
- Kaynakta bulunmayan tanım, etiket, derece, oran, eş anlamlı veya kod uydurulmaz.

## Güncel durum

Ayrıntı: [CURRENT_STATE.md](CURRENT_STATE.md)  
Kararlar: [DECISIONS.md](DECISIONS.md)  
Eksikler: [MISSING_FILES.md](MISSING_FILES.md)

- Şema: `sozluk_kavram.v1.0.3_taslak.json` (Draft-07).
- Kısmi aday veri: 418 kayıt — 276 EK-1 derece kaydı + 142 EK-2 aday kaydı.
- EK-1 derecesiz 4 kural ayrı dosyada.
- EK-2'de 67 kayıtta basılı madde etiketi yok; bunlar kaybedilmedi ve etiket uydurulmadı.
- EK-2 PDF sayfa 25–169 için 555 satırlık OCR aday havuzu çıkarıldı. Adaylar insan denetimi gerektirir.
- Sentetik şema testleri 31/31; gerçek kısmi veri kontrolleri 8/8 PASS olarak raporlandı. Bu sonuçlar içerik doğruluğunun tamamlandığı anlamına gelmez.

## Önemli sınır

Bu klasör `archive/sozluk-kavram-asama2-2026-11-11` dalında tutulur. `cloud-run-migration` dalından ayrıdır; uygulama dağıtım dalına birleştirilmemiştir. Bu arşiv commit'i canlı siteye dağıtım yapılması amacı taşımaz.

## Gelecekte devam edecek model için

Önce [CURRENT_STATE.md](CURRENT_STATE.md), sonra [DECISIONS.md](DECISIONS.md), ardından [reports/](reports/) ve [candidates/](candidates/) belgelerini oku. Ham kaynak JSON'ları [sources/](sources/) altındadır. `history/` içindeki eski şemalar karşılaştırma içindir; güncel taslak v1.0.3'tür.

**İlk sonraki iş:** 555 OCR satır adayını kaynak PDF görüntüleriyle karşılaştırarak gerçek kavram başlığı, tanım, değerlendirme yöntemi, tablo satırı ve oran girdisi olarak sınıflandırmak. Oran tablolarını kavram sözlüğüne karıştırma. Nihai `sozluk_kavram_data.json` dosyasını ancak tam kaynak denetimi bittikten sonra üret.
