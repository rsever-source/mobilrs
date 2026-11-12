# Sözlük Kavram Arşivi — 12.11.2026

Engelli.me kavram sözlüğünün **Aşama 2 (devam)** çıktısı. Bu klasör, veriyi
üreten kaynak dosyaları, şemaları, testleri, kanıt metinlerini ve denetim
raporlarını **tekrar üretilebilir** biçimde içerir.

**Dal:** `archive/sozluk-kavram-asama2-devam-2026-11-12`
**Veri:** `data/sozluk_kavram_data.json` — 745 kayıt (EK-1 276 + EK-2 469)
**Boyut / SHA-256:** 509.283 bayt · `710f86b20806910475c4c733404237c38cd117a780be7b0e9cb2dbf6ec003702`

> Bu arşiv **arşivdir**: uygulama kodu değildir, canlı hizmette kullanılmaz.
> `main`, `cloud-run-migration` ve canlı servis bu çalışmayla değiştirilmemiştir.

---

## 1. İçerik

| Yol | İçerik |
| --- | --- |
| `data/sozluk_kavram_data.json` | **Nihai sözlük verisi** (745 kayıt) |
| `data/sozluk_kavram_kaynak_izleri.json` | Kayıt başına kanıt izi (745 iz) |
| `data/ek1_derecesiz_kurallar.json` | EK-1'in 4 derecesiz kural maddesi (veri dosyasına girmez) |
| `schema/sozluk_kavram.v1.0.3_taslak.json` | **Bağlayıcı şema** (Draft-07) |
| `schema/sozluk_kavram.v1.0.0.json` | Önceki şema (karşılaştırma için) |
| `kanit/icd10_who.json` | WHO ICD-10 kanıt dosyası (kullanılmadı — 0 ICD kodu) |
| `arac/` | Veriyi üreten betikler ve kaynak parçaları |
| `testler/` | Aşama 1 yapısal (46) ve içerik (12) testleri |
| `kaynak/txt/` | EK-2 OCR metni (172 sayfa) — kanıt kaynağı |
| `raporlar/` | Denetim raporu, belirsizlik listesi, SHA-256 manifesti |

---

## 2. Tekrar üretim

Tüm komutlar **bu klasörün kökünde**, PowerShell'de
`$env:PYTHONIOENCODING="utf-8"` ayarlıyken koşulur. Betikler göreli yol kullanır;
sisteme özgü yol içermez.

```powershell
python -X utf8 arac\ek2_ek_kayitlar.py     # 259 yeni kaydın kaynak dosyası
python -X utf8 arac\birlestir_nihai.py     # veri + kaynak eşleşme dosyası
python -X utf8 arac\kanit_izi.py           # kanıt izleri
python -X utf8 arac\nihai_denetim.py       # şema / XOR / kimlik / künye denetimi
python -X utf8 arac\ek2_ek_dogrula.py      # yeni kayıt doğrulaması (0 hata)
python -X utf8 testler\test_sozluk_kavram.py
python -X utf8 testler\veri_testleri.py
```

Beklenen sonuç:

| Ölçüt | Değer |
| --- | --- |
| Kayıt | 745 (EK-1 276 + EK-2 469) |
| Veri boyutu / SHA-256 | 509.283 bayt · `710f86b2…003702` |
| Şema v1.0.3 | 745/745 PASS |
| Şema v1.0.0 | 275/745 PASS (şema farkı) |
| XOR / kimlik / künye / sayfa hatası | 0 / 0 / 0 / 0 |
| Yeni kayıt doğrulaması | 259 kayıt, 0 hata |
| Kanıt izi | 596 birebir, 11 düzeltilmiş, 138 bulanık, 0 eşleşmeyen |
| Testler | 46/46 + 12/12 PASS |

Not: `birlestir_nihai.py` her koşuda `arac/ek2_kaynak_eslesme.json` dosyasını
yeniden yazar; `kanit_izi.py` bu dosyayı okuduğu için **sıra korunmalıdır**.

---

## 3. Verinin kaynağı

| Belge | Künye |
| --- | --- |
| EK-1 — Maluliyet ve Çalışma Gücü Kaybı Tespiti İşlemleri Yönetmeliği Hastalık Listesi | 28.09.2021 / 31612 sayılı RG |
| EK-2 — Erişkinler İçin Engellilik Sağlık Kurulu Raporları Engel Oranları Alan Kılavuzu | 20.02.2019 / 30692 sayılı RG (MBS 31275) |

EK-2 PDF'inin metin katmanı yoktur (172 sayfanın tamamında 0 karakter); bu yüzden
EK-2 tarafındaki bütün ad, etiket ve sayfa bilgisi **OCR çıktısına**
dayanır ve PDF metniyle bağımsız doğrulanamaz.

---

## 4. Kurallar

- Her kayıt **tek** mevzuat bağlantısı taşır (`ek_1_baglantisi` XOR `ek_2_baglantisi`).
- Tanım, derece, oran, ICD kodu, eş anlamlı ve madde etiketi **uydurulmaz**;
  kaynakta yoksa boş bırakılır.
- Oran/puan/Balthazard/saf değerlendirme kriteri satırları kavram sayılmaz;
  yalnız tablo içindeki **gerçek hastalık/kavram adları** alınır.
- Aynı kavram iki ayrı mevzuatta geçiyorsa **iki ayrı kayıt** olur.
- EK-1'deki derecesiz 4 kural ayrı dosyada tutulur
  (`data/ek1_derecesiz_kurallar.json`).

---

## 5. Raporlar

- `raporlar/asama2_devam_denetim_raporu.md` — bu aşamanın üretim ve denetim kaydı
- `raporlar/asama2_belirsizler.md` — alınmayan/alınamayan noktalar ve açık kararlar
- `raporlar/manifest_sha256.md` — arşivdeki tüm dosyaların SHA-256 özeti

Önceki arşiv (11.11.2026 tarihli, 486 kayıt) aynı depodaki
`docs/sozluk-kavram-arsivi-2026-11-11/` klasöründedir ve **değiştirilmemiştir**.
