# Aşama 2 — Kayıt Sayımı ve Doğrulama Raporu

## Kaynak dosyalarının gerçek sayımları

| Kaynak | Kayit sayısı | Derecesiz kurallar | Belirsiz |
|---|---:|---:|---:|
| u1_ek1_001_020.json | 135 | 3 | 0 |
| u2_ek1_021_040.json | 141 | 1 | 0 |
| u3b_ek2_003_024.json | 142 | — | 8 |

## EK-1 bölüm dağılımı

| Bölüm | Derece kaydı | Benzersiz sıra | Ayrı ad grubu |
|---|---:|---:|---:|
| A | 52 | 19 | 19 |
| B | 17 | 10 | 10 |
| C | 6 | 4 | 4 |
| D | 10 | 6 | 6 |
| E | 23 | 23 | 23 |
| F | 19 | 13 | 13 |
| G | 7 | 3 | 3 |
| H | 21 | 7 | 7 |
| J | 28 | 18 | 19 |
| K | 18 | 9 | 9 |
| L | 8 | 5 | 5 |
| M | 13 | 7 | 7 |
| N | 12 | 6 | 6 |
| O | 11 | 7 | 7 |
| P | 1 | 1 | 1 |
| R | 3 | 3 | 3 |
| İ | 27 | 17 | 17 |
| **TOPLAM** | **276** | **158** | **159** |

EK-1 derece dağılımı: `{'agir': 139, 'orta': 68, 'hafif': 66, 'ortak_hukum': 3}`.

J/1 altında iki ayrı kanonik ad vardır: Kutanöz T hücreli lenfomalar ve MF dışı diğer kutanöz lenfomalar. Bu nedenle 158 bölüm+sıra referansı, 159 ayrı bölüm+sıra+ad grubuna açılır.

## EK-2 sayım

- Aday kayıt: **142**
- `madde_etiketi` olan: **75**
- `madde_etiketi` olmayan: **67**
- Ayrı tanım metni saklanan: **66**
- Tanımı kanonik adla aynı olduğu için ayrı `tanim` alanı yazılmayan: **76**

## Veri dönüşümü

- Dönüştürülen toplam aday kayıt: **418** (EK-1 276 + EK-2 142).
- EK-1 derecesiz kural maddeleri: **4**, ayrı dosyada.
- Düzeltilen madde etiketi: **1** (u3b `2,` → u3 ile doğrulanan `2.`).
- Eş anlamlılar kaynakta verilmediği için üretilmedi; tüm `es_anlamli` dizileri boş.
- ICD-10 kodu eklenmedi; mevcut sayfa kaynaklarıyla kod-kavram alt tür eşleşmesi kanıtlanmadı.

## Şema doğrulaması

- Draft-07 şema kendi kendini doğrulama: **PASS**.
- Gerçek aday kayıtların şemadan geçmesi: **418/418 PASS**.
- Tekil `kavram_id`: **418/418 benzersiz**.
- Veri-katmanı hata sayısı: **0**.

## Sınırlama

Bu veri seti yalnız yüklenen EK-1 s.1–40 ve EK-2 s.3–24 kaynak JSON'larından oluşturulmuştur. EK-2 s.25–172 henüz yoktur. Bu nedenle nihai sözlük değildir.