# Engelli.me özel haber raporu

Bu ekran yalnızca haber sistemi durumunu okur. **Güncelle** düğmesi haber taraması veya Gemini çalıştırmaz; GitHub Actions durumunu, kayıtlı `news_ai_log.json` dosyasını ve canlı haber API'sini yeniden okur.

## Tek gerekli ayar

Cloud Run servisinde Secret Manager üzerinden `ADMIN_PASSWORD` adlı bir secret'ı ortam değişkeni olarak bağla. Bu değer, yalnızca bu yönetim ekranı için belirlenen güçlü bir yönetici parolası olmalıdır. Parolayı GitHub'a, kaynak koda veya sohbete yazma.

Redis, Passkey/WebAuthn veya ayrı bir oturum veritabanı gerekmez. Oturum, paroladan türetilen HMAC imzalı, `Secure`, `HttpOnly`, `SameSite=Strict` çerezle doğrulanır ve 12 saat sonra sona erer. Parola değişirse önceki oturumlar geçersiz olur.

## Açılış ve doğrulama

1. `ADMIN_PASSWORD` secret'ını Cloud Run'a bağla.
2. Yalnızca kod incelemesi ve CI başarılı olduktan sonra, onay verilirse dağıtım yap.
3. `https://engelli.me/admin/haber-durumu` adresini aç ve yönetici parolasıyla giriş yap.
4. Çıkış yaptıktan sonra rapor API'sinin oturum olmadan erişilemediğini kontrol et.
5. **Güncelle** düğmesinin rapor verisini yenilediğini, yeni tarama başlatmadığını doğrula.

## Güvenlik ve sınırlar

- Sayfa ve rapor API'si oturum gerektirir; `noindex` başlıkları ek bir koruma değil, yalnızca indeksleme yönergesidir.
- Parola yalnızca Cloud Run'ın secret yapılandırmasında tutulur; kaynak koda eklenmez.
- Oturum çerezi sunucu tarafında bir veritabanı gerektirmeyen imzalı bir belirteçtir; ömrü 12 saattir.
- GitHub token'ı tarayıcıya gönderilmez. Rapor, herkese açık depo verilerini okur.
- Bu PR birleştirilmeden ve dağıtım yapılmadan önce `ADMIN_PASSWORD` secret'ı yapılandırılmalıdır.
