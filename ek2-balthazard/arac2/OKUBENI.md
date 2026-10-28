# Araç-2 — Balthazard ekranı (prototip)

`ARAC-2-WIREFRAME.md` **0.4** tasarımının çalışan prototipi. Onaylı ortak motoru
(`../balthazard_motoru.py`) **kopyalamadan** kullanır: hesap `balthazard()`, gösterim
`bicimle_gosterim()`.

> **Durum:** prototip. Depoya eklenmedi, canlı FastAPI uygulamasına bağlanmadı, deploy
> edilmedi. Yalnız `127.0.0.1` üzerinde çalışır.

## Çalıştırma

```
<python> arac2_sunucu.py            # http://127.0.0.1:8765
<python> arac2_sunucu.py 9000       # başka port
```

Python 3.10+ yeterli; **ek paket gerekmez** (yalnız standart kütüphane).

## Dosyalar

| Dosya | İçerik |
| --- | --- |
| `arac2_sunucu.py` | `http.server` tabanlı küçük sunucu; `POST /api/hesapla` → motor |
| `arac2.html` | Ekran (HTML + CSS + JS, harici bağımlılık yok) |
| `test_arac2.py` | 11 test: gösterim katmanı, uç nokta, hata geçişi, UTF-8, 404 |

## Sözleşmeye bağlı davranışlar

- **Tek hesap yeri:** `balthazard()`; ekranda formül, `+10`, sıralama veya yuvarlama kodu **yok**.
- **Tek biçimlendirme yeri:** sunucudaki `gosterim_ekle()` → `bicimle_gosterim()`
  (en fazla 2 ondalık, yarı yukarı, sondaki sıfırlar atılır, Türkçe virgül — G-1…G-4).
- **Ham değer korunur:** `sonuc.deger` yanıtta aynen döner; “Ham değeri kopyala” onu kopyalar
  (`59.599`), gösterim metnini (`59,6`) değil.
- **Yaş eki:** iki radio, **varsayılan seçim yok**; seçilmeden “Hesapla” pasif. Yaş seçimi
  değişince sonuç ve kaynak künyesi **aynı anda** yenilenir (§12.1). Liste değişirse sonuç
  **eskimedi** uyarısı çıkar; “Hesapla” ile güncellenir (§12.2).
- **Uyarılar:** `U_ORAN_TEKRAR` ve `U_ORAN_SIFIR` bilgi olarak; 100 için onay istenir.
  Hatalar motordan **olduğu gibi** (`hata.mesaj`) gösterilir; yeni kod üretilmez.
- **Kaynak künyesi** yalnız “65 yaş ve üzeri” seçiliyken sonucun altında çizilir.

## Testler

```
<python> -m unittest -v test_arac2
```

Kapsam dışı (bilinçli): Araç-1 sekmesi (henüz yok), kalıcılık, kullanıcı hesabı,
katalog bağlantısı (Araç-2 katalog okumaz).
