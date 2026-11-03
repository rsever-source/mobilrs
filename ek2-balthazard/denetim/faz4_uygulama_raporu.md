# FAZ 4 DENETİM TESPİTLERİ — UYGULAMA RAPORU

Tarih: 2026-11-03
Dal: `feature/ek2-arac1-duzeltme` (worktree: `Projects\Engelli.me\worktrees\ek2-arac1-duzeltme`)
Commit: `98e513b` (üzerine commit YAPILMADI)
Kaynak: 20.02.2019 / 30692 sayılı Resmî Gazete, EK-2 — `20190220-2-1.pdf`
(SHA256 `B630F6AD…AD28`, basılı sayfa = PDF fiziksel sayfa + 113)

---

## 1. DEĞİŞEN DOSYALAR

| Dosya | Değişiklik |
| --- | --- |
| `ek2-balthazard/veri/katalog_ek2_ek.json` | 136 → 206 kayıt; 32 mükerrer/ana katalog kopyası çıkarıldı, **102** kaynak doğrulamalı kayıt eklendi (§6 sayım tablosu) |
| `ek2-balthazard/veri/kurallar_ek2.json` (yeni) | 15 → 19 kural; STOMA, NÖROJEN-MESANE, AFAZI, NAKIL, EPILEPSI, UYKU kapsamları düzeltildi; 4 kural eklendi |
| `ek2-balthazard/test_katalog_okuyucu.py` | Faz 4 doğrulama testleri (32 test) |
| `ek2-balthazard/arac1/test_arac1.py` | Sayılar ve kimlikler güncellendi (37 test) |
| `ek2-balthazard/arac1/test_arac1_arayuz.py` | Sayılar ve kimlikler güncellendi (5 test) |
| `ek2-balthazard/denetim/faz4_uygulama_betigi.py` (yeni) | Uygulama betiği — testlerin parçası değildir, kayıt izlenebilirliği için saklandı |

**Dokunulmayanlar:** `veri/katalog.json` (424, salt okunur), `veri/belirsiz.json`, `arac2/` (hiç değişmedi — `git diff` boş), `arac1_sunucu.py`, `katalog_okuyucu.py`, `ozel_hesaplamalar.json` (önceki oturumdan kalan değişiklikler aynen korundu).

---

## 2. YAPILAN DÜZELTMELER

### 2.1 İnfertilite — DOĞRULANDI, %10
- Kaynak: **s.190**, *"İnfertilite … 10"* (sayfa görüntüsünden birebir okundu).
- Eklenen kayıt: `UG-0xx — İnfertilite — İnfertilite — 10 — s.190`.
- Aynı sayfadan: Penis 4 (5/10/15/20), Testis-epididim 6 (5/10/10/15/15/20), Orşiektomi 2 (10/20), Prostat 4 (5/10/15/20) kayıtları da eklendi.

### 2.2 `K-STOMA-ORGAN` yalnız 6 stoma kaydına bağlandı
- Kaynak: **s.183**, Tablo 6 — Özefagostomi 15 · Gastrostomi 15 · Jejunostomi 20 · İleostomi 20 · İleal-poş anal anastomoz 20 · Kolostomi 10.
- Önceki durum: kural SS-001…SS-019'un **19 kaydına** bağlıydı (stoma olmayan üst sindirim, kolon, anal, karaciğer, safra kayıtları dahil).
- Yeni durum: kapsam `SS-023…SS-028` (yalnız 6 stoma). SS-001…SS-019'dan kural kaldırıldı.

### 2.3 Nörojen mesane kuralının yanlış bağlantıları düzeltildi
- Kaynak: **s.189**, *"Nörojen mesane için kas-iskelet sistemi bölümü sayfa 189'daki tablo 4.3'e bakınız."*
- Önceki durum: kural `UG-011/012/013` (genel mesane hastalıkları — sistitizm, sistektomi) kayıtlarına bağlıydı. Kaynak bu kayıtları değil, **nörojen mesane tanısını** yönlendiriyor.
- Yeni durum: `idler: []`, `hastaliklar: ["Nörojen mesane"]`, `gruplar: ["norojen-mesane"]`; üç kayıttan kural kaldırıldı, `uyari` alanı eklendi.

### 2.4 Eksik kayıtlar tamamlandı — net **102** yeni kayıt

> Ara adımda 129 kayıt yazılmıştı; 27'si (§2.7'de açıklanır) net toplama girmediği için gerçek net ekleme **102**'dir.

| Bölüm | Eklenen | Dayanak |
| --- | --- | --- |
| Kadın hastalıkları | 3 (vulva/vajina 2/4/10) | s.185 |
| Ürogenital — nefroloji | 17 (proteinüri 15/25/40/60, KBH evre 1–5 + A/B, RRT 90, böbrek nakli 70, Fanconi 30/50) | s.187 |
| Ürogenital — diğer | 33 (üst üriner %5; nefrektomi %30; diversiyon 20/30/30; mesane 5/20/40; penis 4; testis 6; orşiektomi 2; infertilite 1; prostat 4) | s.188–190 |
| Sindirim | 9 (6 stoma, pankreas nakli 70, karaciğer nakli 70, splenektomi 10) | s.180/183/184 |
| Endokrin | 27 (hipofiz izole 20, sekonder hipoparatiroidi 20, adrenal hiperplazi 45, hiperaldosteronizm 0/30/50, adrenogenital 40, puberte/çoğul bez/timus 20/60/40, iyot 0, tirotoksikoz 10, tiroidektomi 0, osteomalazi 50, Lesch-Nyhan 90, gut 10, porfiria 40, lipid 6, depo hastalıkları 4) | s.192–194 |
| Sinir — epilepsi | 1 (**%70**) | s.201 |
| Sinir — uyku | 7 (genel şiddet 5/10/35; sirkadiyen 10, parasomni 10, REM 35, hareket 10) | s.201–202 |
| Sinir — afazi | 6 (motor 10/25/45, sensöryel 20/40/60) | s.200 |
| Sinir — trigeminal | 1 (**%15**) | s.204 |

**JSON'dan hesaplanan gerçek ekleme:** KH-004…KH-006 (3), UG-019…UG-066 (48), SS-023…SS-031 (9), EM-029…EM-055 (27), SN-022…SN-036 (15) = **102**.

### 2.5 Göğüs bölümü kural sayısı ve kapsamı
- Kaynak **s.196**'da **6** uygulama kuralı vardır: SFT zorunluluğu, akut dönem sonrası + optimal tedavi, TB'de tedavi sonunda, malignitede onkolojiye yönlendirme, toraks cerrahisi sonrası yıllık kontrol, nakilde Balthazard.
- 5 sabit oran kaydı (20/40/80/10/70) kaynakla **birebir** doğru → değiştirilmedi.
- `K-GOGUS-CERRAHI` kapsamı `[GH-004]` olarak sabitlendi; bölüme `kural_notu` alanı eklendi (6 kural, "9 kural" iddiası düzeltildi).

### 2.6 Mükerrer temizliği
- `KV-001…KV-032` → `V-001…V-033` ile birebir aynı (32 kayıt).
- Kapak/koroner/kalp nakli/damar/venöz/lenf kayıtları `V-034…V-061` ile **zaten mevcut** olduğu tespit edildi (isim + oran + evre eşleşmesi yüksek güvenle doğrulandı).
- **Kardiyovasküler bölümü tamamen kaldırıldı**; `V-034…V-061` korunuyor (mevcut kimlikler değiştirilmedi).

### 2.7 Neden 27 kayıt net eklemeye dahil edilmedi

Uygulama iki adımda yapıldı ve önceki raporda ikinci adım hesaba katılmamıştır:

1. **Birinci adım:** `KV-001…KV-032` (mükerrer) çıkarıldı, yerine geçici olarak `KV-001…KV-027` kimlikleriyle **27 yeni kayıt** yazıldı (kapak Klas 1–4, koroner Klas 1–4, kalp nakli, ASO, Buerger, travmatik damar, venöz, lenf). Bunlar 129'luk planın içindeydi.
2. **İkinci adım:** Bu 27 kaydın tamamının ana katalogda `V-034…V-061` olarak **zaten var olduğu** isim + oran düzeyinde doğrulandı. Bu nedenle geçici `KV-*` bloğu, kardiyovasküler bölümüyle birlikte **bütünüyle silindi** (32 mükerrer + 27 kopya = 59 kimlik).

Sonuç: bu 27 kayıt *geçici olarak yazıldı ve silindi*. Net ekleme hesabına girmez, çünkü aynı bilgi `V-034…V-061` altında hâlihazırda katalogda durmaktadır; ikinci kez eklemek mükerrer kayıt üretirdi.

Tekrarlanan denklem:

| Yanlış (önceki rapor) | Doğru (JSON sayımı) |
| --- | --- |
| 136 − 32 + 129 = 233 | 136 − 32 + 102 = **206** |

Önceki raporda geçen "104" sayısı başka bir şeydir: 136'nın mükerrer olmayan kısmıdır (silinen 32 KV hariç) ve eklenen kayıtlarla ilgisi yoktur.

### 2.7 Yeni kurallar (4)
| Kod | Dayanak |
| --- | --- |
| `K-TRAKEOTOMI-KONUSMA` | s.127 — trakeotomi %40 + konuşma engeli Balthazard |
| `K-ISITME-KONUSMA` | s.117 — işitme + eşlik eden konuşma bozukluğu Balthazard |
| `K-FASIYAL-TRIGEMINAL` | s.204 — bilateral fasiyal paralizi + trigeminal nevralji Balthazard |
| `K-ONKOLOJI-YILLIK-TAKIP` | s.199 — yılda en az bir kez metastaz/nüks değerlendirmesi |

---

## 3. TEST SONUÇLARI

| Test dosyası | Test | Sonuç |
| --- | --- | --- |
| `test_balthazard_motoru.py` | 77 | **OK** |
| `test_katalog_okuyucu.py` | 32 | **OK** |
| `arac1/test_arac1.py` | 37 | **OK** |
| `arac1/test_arac1_arayuz.py` | 5 | **OK** |
| `arac2/test_arac2.py` | 13 | **OK** |
| **Toplam** | **164** | **tamamı başarılı** |

Araç-2 testleri değiştirilmeden çalıştı ve geçti (dosyalarına dokunulmadı).

---

## 4. ÇÖZÜLEMEYEN / UYGULANMAYAN KONULAR

| # | Konu | Neden uygulanmadı |
| --- | --- | --- |
| 1 | **"Faz 4'ün 18 kaydı"** | Liste hiçbir dosyada yok; bu çalışmayla eklenen kayıt sayısı **102** oldu. Liste verilmeden karşılaştırılamaz. |
| 2 | **Onkolojide "net %20 ilave"** | Mutlak puan mı göreli artış mı mevzuattan çıkarılamıyor → kural olarak eklenmedi, yalnız yıllık takip kuralı eklendi. |
| 3 | **Fallop tüpü ve overler (s.186)** | Sayfa görüntüsü doğrulanmadı; oran okunmadan eklenmedi. |
| 4 | **Kistik fibrozis (EM-027), FMF (EM-028)** | s.194–195'te görsel doğrulanamadı; mevcut kayıtlar **korundu**, yenisi eklenmedi. |
| 5 | **Aritmi/perikard/KBH gibi grupların alt satır doğrulaması** | 424'lük ana katalog **salt okunur** — değiştirilmedi; ana katalog satırları bu çalışmanın kapsamı dışında bırakıldı. |
| 6 | **`K-TRAKEOTOMI-KONUSMA` ve `K-NOROJEN-MESANE`** | `idler` boş: hedef kayıtlar 424'lük ana katalogda (K-082) veya kas-iskelet bölümünde (Tablo 4.3) — bu paket kapsamında değil. |
| 7 | **`K-GOGUS-TB` / `K-GOGUS-MALIGNITE`** | Dayanakları doğru; hedef kayıt (tüberküloz, malignite) sabit oranlı katalogda yok — kural korundu, kapsam boş. |
| 8 | **Canlı "560" katalog** | Dosya olarak yok; canlı ortam karşılaştırması yapılmadı. |

---

## 5. DOĞRULAMA KOMUTLARI

```
cd Projects\Engelli.me\worktrees\ek2-arac1-duzeltme
python -m unittest discover -s ek2-balthazard -p "test_balthazard_motoru.py"
python -m unittest discover -s ek2-balthazard -p "test_katalog_okuyucu.py"
python -m unittest discover -s ek2-balthazard/arac1 -p "test_arac1.py"
python -m unittest discover -s ek2-balthazard/arac1 -p "test_arac1_arayuz.py"
python -m unittest discover -s ek2-balthazard/arac2 -p "test_arac2.py"
```

Commit / push / deploy **yapılmadı**.

---

## 6. SAYIM DOĞRULAMASI (JSON'dan)

Kaynak: `veri/katalog_ek2_ek.json` — "önce" = `git show HEAD` sürümü, "sonra" = güncel dosya.

| | Değer |
| --- | --- |
| Önceki toplam | **136** |
| Silinen | **32** (`KV-001`…`KV-032`) |
| Eklenen | **102** |
| Hesap | 136 − 32 + 102 = **206** |
| Son toplam | **206** (tekil kimlik 206, çakışma yok, boşluk yok) |
| Bölüm sayısı | **7** |

**Kategori bazında gerçek kayıt sayıları**

| Bölüm | Önce | Sonra | Silinen | Eklenen |
| --- | ---: | ---: | ---: | ---: |
| Kadın Hastalıkları | 3 | **6** | 0 | 3 |
| Böbrek ve İdrar | 18 | **66** | 0 | 48 |
| Sindirim | 22 | **31** | 0 | 9 |
| Endokrin ve Metabolizma | 28 | **55** | 0 | 27 |
| Göğüs Hastalıkları | 5 | **5** | 0 | 0 |
| Onkoloji | 7 | **7** | 0 | 0 |
| Sinir Sistemi | 21 | **36** | 0 | 15 |
| Kalp ve Damar | 32 | **0** | 32 | 0 |
| **TOPLAM** | **136** | **206** | **32** | **102** |

**Kimlik bütünlüğü:** her bölüm 1'den kesintisiz (KH 1–6, UG 1–66, SS 1–31, EM 1–55, GH 1–5, ON 1–7, SN 1–36); tekrarlı kimlik 0; yabancı ön ek 0.