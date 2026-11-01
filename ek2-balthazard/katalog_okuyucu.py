# -*- coding: utf-8 -*-
"""EK-2 katalog verisini **salt okunur** yükleyen yardımcı.

Amaç: ``veri/katalog.json`` ve ``veri/belirsiz.json`` dosyalarını Araç-1'in
ihtiyaç duyduğu biçimde (bölüm → grup/başlık → hastalık → seviye) hazırlamak ve
sözleşmedeki değişmezleri yükleme anında doğrulamak.

Sözleşme: ``SOZLESME.md`` §3 (veri sözleşmesi) ve §3.4 (korunması zorunlu
değişmezler). Bu modül:

* dosyaları yalnız **okur** — yazma yolu yoktur, ``mtime`` değişmez;
* veriyi **yorumlamaz**: oran eklemez, kısıt üretmez, belirsiz kaydı
  kesinleştirmez, kimlik yeniden numaralandırmaz;
* bir değişmez bozulursa **sessizce devam etmez**, ``KatalogHatasi`` yükseltir
  (§3.4: "biri bozulursa uygulama açılmaz").

Türetilmiş alanlar (§3.3) yalnız bellekte tutulur ve dosyaya yazılmaz:
``ad``, ``rozet``, ``seviye``, ``arama_metni``, grup anahtarları.

Bu modül standart kütüphane dışında bağımlılık kullanmaz.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

__all__ = [
    "KatalogHatasi",
    "Kayit",
    "BelirsizKayit",
    "Hastalik",
    "Grup",
    "Bolum",
    "Katalog",
    "yukle",
    "katla",
    "KATALOG_ADI",
    "BELIRSIZ_ADI",
    "BOLUM_KISA_ADLARI",
    "GECERLI_KISIT_KODLARI",
    "SORUN_TIPLERI",
]

KOK = Path(__file__).resolve().parent
VERI_KLASORU = KOK / "veri"
KATALOG_ADI = "katalog.json"
BELIRSIZ_ADI = "belirsiz.json"

# --- Sözleşme sabitleri ------------------------------------------------------

BOLUM_KISA_ADLARI = {
    "ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR": "Ruh Sağlığı",
    "DERİ": "Deri",
    "HEMATOLOJİK HASTALIKLAR": "Hematoloji",
    "KULAK BURUN BOĞAZ": "KBB",
    "KARDİYOVASKÜLER SİSTEM": "Kalp-Damar",
}

# §3.11 / §4.4 — katalogda yalnız bu yedi kod bulunur.
GECERLI_KISIT_KODLARI = (
    "R-YILLIK",
    "R-GECICI",
    "R-VERGI",
    "R-REMISYON",
    "R-NAKIL",
    "R-IKTIYOZ",
    "R-EKTO",
)

# §4.7 — belirsiz satırın kullanıcıya gösterilen tek cümlesi.
SORUN_TIPLERI = {
    "coklu_kosul_tek_oran": "Bu satır birden fazla klinik durumu tek orana bağlıyor.",
    "ekleme_kurali": "Bu satır bağımsız oran değil, başka oranlara eklenen bir kural.",
    "olcum_iki_kriter": "Oran iki ölçütün birlikte sağlanmasına bağlı.",
    "hiyerarsi_belirsiz": "Alt koşulların üst basamakların yerine mi geçtiği belirsiz.",
    "harf_tekrari": "Kaynakta madde numarası tekrar ediyor.",
    "kombinasyon_kisiti": "Bu oran başka bir hastalıkla birlikte kullanılamaz.",
    "numaralandirma_atlamasi": "Kaynakta madde numarası atlıyor.",
}

# §3.4 — değişmezler.
BEKLENEN_KESIN = 424
BEKLENEN_BELIRSIZ = 16
BEKLENEN_TOPLAM = 440
BEKLENEN_BOLUM_DAGILIMI = {
    "ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR": 56,
    "DERİ": 142,
    "HEMATOLOJİK HASTALIKLAR": 78,
    "KULAK BURUN BOĞAZ": 87,
    "KARDİYOVASKÜLER SİSTEM": 61,
}
# §3.10 — çözülen belirsiz satır → kataloğa aktarılan kimlik (11 satır).
BEKLENEN_COZULEN = {
    "X-Z01": "Z-055",
    "X-Z02": "Z-056",
    "X-D07": "D-140",
    "X-D08": "D-139",
    "X-D09": "D-141",
    "X-D10": "D-142",
    "X-H01": "H-074",
    "X-H04": "H-075",
    "X-H05": "H-076",
    "X-H06": "H-077",
    "X-H07": "H-078",
}
BEKLENEN_BELIRSIZ_IDLER = (
    "X-Z03", "X-Z04",
    "X-D01", "X-D02", "X-D03", "X-D04", "X-D05", "X-D06",
    "X-H02", "X-H03",
    "X-K01", "X-K02",
    "X-V01", "X-V02", "X-V03", "X-V04",
)
BEKLENEN_TIRE_IDLER = ("D-013", "D-014", "D-017", "D-062", "H-056", "H-065")
BEKLENEN_TEK_KAYITLI = ("D-013", "D-014", "D-017", "D-049", "D-062",
                        "D-075", "D-086", "D-134", "H-056",
                        "K-082", "V-042")

_TIRE = "—"
_KIMLIK = re.compile(r"^(Z|D|H|K|V)-(\d{3})$")
# "VI- Yaygın ...", "VI-A Benign ...", "I- A. Aplastik ..." gibi ön ekler.
# Numaradan sonra alt harf varsa (``I- A.`` / ``VI-A ``) rozete eklenir; yoksa
# yalnız ayraç (``- ``) yutulur ve hastalık adı temiz kalır.
_ON_EK = re.compile(r"^\s*([IVX]+)\s*(?:-\s*([A-Z])\s*[.\-]\s*|-\s*)")
# "psoriazis" ~ "psoriasis" eşleşmesi §3.6'da istendiği için yalnız arama
# metninde uygulanan simetrik katlama (veri değişmez, ekranda veri gösterilmez).
_KATLAMA = str.maketrans(
    "çğıöşüâîû", "cgiosuaiu"
)


class KatalogHatasi(Exception):
    """Katalog dosyası okunamadığında veya bir değişmez bozulduğunda."""


@dataclass(frozen=True)
class Kayit:
    """Kesin katalog kaydı + yalnız bellekte tutulan türetilmiş alanlar."""

    id: str
    bolum: str
    grup: str | None
    hastalik: str
    alt_tur: str
    oran: int
    sayfa: int
    kisit: tuple[str, ...]
    kaynak_not: str
    ad: str
    rozet: str
    seviye: str
    arama_metni: str

    def sozluk(self) -> dict:
        """JSON yanıtı için sade sözlük (ham alanlar + türetilmiş alanlar)."""
        return {
            "id": self.id,
            "bolum": self.bolum,
            "grup": self.grup,
            "hastalik": self.hastalik,
            "ad": self.ad,
            "rozet": self.rozet,
            "alt_tur": self.alt_tur,
            "seviye": self.seviye,
            "oran": self.oran,
            "sayfa": self.sayfa,
            "kisit": list(self.kisit),
            "kaynak_not": self.kaynak_not,
        }


@dataclass(frozen=True)
class BelirsizKayit:
    """``belirsiz.json`` satırı (yalnız ``durum=belirsiz`` olanlar ekrana girer)."""

    id: str
    bolum: str
    hastalik: str
    alt_tur: str
    oran: int | None
    sayfa: int | None
    durum: str
    sorun_tipi: str
    aciklama: str
    kaynak_metin: str
    cozum_tarihi: str
    kaynak_sayfa: int | None
    arama_metni: str
    ad: str
    seviye: str

    @property
    def sorun_cumlesi(self) -> str:
        return SORUN_TIPLERI[self.sorun_tipi]

    def sozluk(self) -> dict:
        """Dikkat: ``oran`` bilinçli olarak dışarı verilmez (§3.10)."""
        return {
            "id": self.id,
            "bolum": self.bolum,
            "ad": self.ad,
            "seviye": self.seviye,
            "sayfa": self.sayfa,
            "sorun_tipi": self.sorun_tipi,
            "sorun": self.sorun_cumlesi,
            "aciklama": self.aciklama,
        }


@dataclass(frozen=True)
class Hastalik:
    """3. düzey: hastalık adı ve altındaki seviyeler."""

    anahtar: str
    ad: str
    kayitlar: tuple[Kayit, ...]

    @property
    def tek_kayit(self) -> bool:
        return len(self.kayitlar) == 1

    def sozluk(self) -> dict:
        return {
            "anahtar": self.anahtar,
            "ad": self.ad,
            "tek_kayit": self.tek_kayit,
            "kayitlar": [
                {"id": k.id, "seviye": k.seviye, "oran": k.oran, "sayfa": k.sayfa}
                for k in self.kayitlar
            ],
        }


@dataclass(frozen=True)
class Grup:
    """2. düzey: DERİ'de grup, Z/H'de Roma başlığı."""

    anahtar: str
    ad: str
    rozet: str
    kayitlar: tuple[Kayit, ...]
    hastaliklar: tuple[Hastalik, ...]

    def sozluk(self) -> dict:
        return {
            "anahtar": self.anahtar,
            "ad": self.ad,
            "rozet": self.rozet,
            "kayit_sayisi": len(self.kayitlar),
            "hastaliklar": [h.sozluk() for h in self.hastaliklar],
        }


@dataclass(frozen=True)
class Bolum:
    ad: str
    kisa: str
    kayitlar: tuple[Kayit, ...]
    gruplar: tuple[Grup, ...]

    def sozluk(self) -> dict:
        return {
            "ad": self.ad,
            "kisa": self.kisa,
            "kayit_sayisi": len(self.kayitlar),
            "gruplar": [g.sozluk() for g in self.gruplar],
        }


@dataclass(frozen=True)
class Katalog:
    kayitlar: tuple[Kayit, ...]
    belirsiz: tuple[BelirsizKayit, ...]
    id_ile: MappingProxyType
    bolumler: tuple[Bolum, ...]
    meta: MappingProxyType
    belirsiz_meta: MappingProxyType
    dosya_ozeti: MappingProxyType

    # --- sorgular -----------------------------------------------------------

    def kayit(self, kimlik: str) -> Kayit | None:
        return self.id_ile.get(kimlik)

    def belirsiz_kayit(self, kimlik: str) -> BelirsizKayit | None:
        for satir in self.belirsiz:
            if satir.id == kimlik and satir.durum == "belirsiz":
                return satir
        return None

    def bolum(self, ad: str) -> Bolum | None:
        for bolum in self.bolumler:
            if bolum.ad == ad or bolum.kisa == ad:
                return bolum
        return None

    def ara(self, metin: str, bolum: str | None = None) -> tuple[Kayit, ...]:
        """``hastalik + alt_tur + rozet`` üzerinde Türkçe duyarsız arama.

        §3.6: 3 karakterden kısa sorgu çalışmaz (boş sonuç). Sonuç sayısı
        sınırlanmaz; 276 kaydın tamamı arama ile bulunabilir (§3.17/1).
        """
        sorgu = katla(metin).strip()
        if len(sorgu) < 3:
            return ()
        secili = self.bolum(bolum).ad if bolum else None
        return tuple(
            k
            for k in self.kayitlar
            if sorgu in k.arama_metni and (secili is None or k.bolum == secili)
        )

    def belirsiz_ara(self, metin: str, bolum: str | None = None) -> tuple[BelirsizKayit, ...]:
        sorgu = katla(metin).strip()
        if len(sorgu) < 3:
            return ()
        secili = self.bolum(bolum).ad if bolum else None
        return tuple(
            s
            for s in self.belirsiz
            if s.durum == "belirsiz"
            and sorgu in s.arama_metni
            and (secili is None or s.bolum == secili)
        )


# --- Yardımcılar -------------------------------------------------------------


def katla(metin: str) -> str:
    """Türkçe duyarsız arama anahtarı üretir.

    ``İ→i``, ``I→ı`` sonra küçük harf; aksanlar katlanır (``ç→c``, ``ş→s`` …).
    §3.6'daki ``psoriazis ≈ psoriasis`` beklentisi için **yalnız arama
    metninde** ``z→s`` de katlanır. Bu dönüşüm ekranda gösterilen metni veya
    veriyi değiştirmez.
    """
    if not isinstance(metin, str):
        return ""
    kucuk = metin.replace("İ", "i").replace("I", "ı").lower()
    return kucuk.translate(_KATLAMA).replace("z", "s")


def _metin(ham, alan: str) -> str:
    if not isinstance(ham, str) or not ham.strip():
        raise KatalogHatasi(f"'{alan}' alanı boş veya metin değil.")
    return ham.strip()


def _tam_sayi(ham, alan: str) -> int:
    if isinstance(ham, bool) or not isinstance(ham, int):
        raise KatalogHatasi(f"'{alan}' alanı tam sayı değil.")
    return ham


def _ayir(hastalik: str) -> tuple[str, str | None, str]:
    """``hastalik`` alanını (ad, seviye etiketi, rozet) olarak ayırır (§3.3)."""
    sol, ayrac, sag = hastalik.partition(" — ")
    eslesme = _ON_EK.match(sol)
    if eslesme:
        rozet = eslesme.group(1)
        if eslesme.group(2):
            rozet = f"{rozet}-{eslesme.group(2)}"
        ad = sol[eslesme.end():].strip()
    else:
        rozet, ad = "", sol.strip()
    if not ad:
        raise KatalogHatasi(f"Hastalık adı ayrıştırılamadı: {hastalik!r}")
    return ad, (sag.strip() if ayrac else None), rozet


def _bolum_2_anahtari(kayit: dict, rozet: str) -> tuple[str, str]:
    """2. düzey anahtarı ve ekran etiketi (§3.7)."""
    if kayit["bolum"] == "DERİ":
        grup = kayit.get("grup")
        if not grup:
            raise KatalogHatasi(f"{kayit['id']}: DERİ kaydında 'grup' yok.")
        ad = (kayit.get("_grup_adlari") or {}).get(grup, grup)
        return f"grup:{grup}", ad
    if not rozet:
        # K/V bölümlerinde rozet None olabilir, grup kullan
        if kayit.get("bolum") in ("KULAK BURUN BOĞAZ", "KARDİYOVASKÜLER SİSTEM"):
            grup = kayit.get("grup")
            if not grup:
                raise KatalogHatasi(f"{kayit['id']}: {kayit['bolum']} kaydında 'grup' yok.")
            ad = (kayit.get("_grup_adlari") or {}).get(grup)
            if not ad:
                raise KatalogHatasi(
                    f"{kayit['id']}: {kayit['bolum']} için '{grup}' grup adı katalog meta.grup_adlari içinde yok."
                )
            return f"baslik:{grup}", ad
        raise KatalogHatasi(f"{kayit['id']}: Roma başlığı belirlenemedi.")
    temel = rozet.split("-", 1)[0]
    return f"baslik:{temel}", temel


def _oku(yol: Path, ad: str) -> dict:
    try:
        with open(yol, "r", encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except FileNotFoundError as exc:
        raise KatalogHatasi(f"{ad} bulunamadı: {yol}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise KatalogHatasi(f"{ad} okunamadı: {yol} ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise KatalogHatasi(f"{ad} geçerli JSON değil: {yol} ({exc})") from exc
    if not isinstance(veri, dict):
        raise KatalogHatasi(f"{ad} kök nesnesi sözlük değil: {yol}")
    return veri


# --- Yükleme -----------------------------------------------------------------


def yukle(katalog_yolu: Path | str | None = None,
          belirsiz_yolu: Path | str | None = None) -> Katalog:
    """Katalog dosyalarını okur, değişmezleri doğrular ve modeli döndürür.

    Dosyalara **yazmaz**. Herhangi bir değişmez bozulursa ``KatalogHatasi``.
    """
    katalog_yolu = Path(katalog_yolu) if katalog_yolu else VERI_KLASORU / KATALOG_ADI
    belirsiz_yolu = Path(belirsiz_yolu) if belirsiz_yolu else VERI_KLASORU / BELIRSIZ_ADI

    katalog_ham = _oku(katalog_yolu, "katalog.json")
    belirsiz_ham = _oku(belirsiz_yolu, "belirsiz.json")

    kayitlar_ham = katalog_ham.get("kayitlar")
    if not isinstance(kayitlar_ham, list):
        raise KatalogHatasi("katalog.json içinde 'kayitlar' dizisi yok.")
    belirsiz_satirlar = belirsiz_ham.get("kayitlar")
    if not isinstance(belirsiz_satirlar, list):
        raise KatalogHatasi("belirsiz.json içinde 'kayitlar' dizisi yok.")

    meta = katalog_ham.get("meta") or {}
    grup_adlari = meta.get("grup_adlari") or {}

    # 1) Kayıtları normalize et
    kayitlar: list[Kayit] = []
    gorulen: set[tuple[str, str]] = set()
    for ham in kayitlar_ham:
        if not isinstance(ham, dict):
            raise KatalogHatasi("Katalog kaydı sözlük değil.")
        kimlik = _metin(ham.get("id"), "id")
        bolum = _metin(ham.get("bolum"), "bolum")
        if bolum not in BEKLENEN_BOLUM_DAGILIMI:
            raise KatalogHatasi(f"{kimlik}: bilinmeyen bölüm {bolum!r}.")
        hastalik = _metin(ham.get("hastalik"), "hastalik")
        alt_tur = ham.get("alt_tur")
        if alt_tur is None:
            raise KatalogHatasi(f"{kimlik}: 'alt_tur' eksik.")
        if not isinstance(alt_tur, str):
            raise KatalogHatasi(f"{kimlik}: 'alt_tur' metin değil.")
        oran = _tam_sayi(ham.get("oran"), f"{kimlik}.oran")
        if not 0 <= oran <= 100:
            raise KatalogHatasi(f"{kimlik}: oran 0-100 aralığında değil ({oran}).")
        sayfa = _tam_sayi(ham.get("sayfa"), f"{kimlik}.sayfa")

        kisit = ham.get("kisit") or []
        if not isinstance(kisit, list) or not all(isinstance(k, str) for k in kisit):
            raise KatalogHatasi(f"{kimlik}: 'kisit' metin listesi değil.")
        bilinmeyen = [k for k in kisit if k not in GECERLI_KISIT_KODLARI]
        if bilinmeyen:
            raise KatalogHatasi(f"{kimlik}: bilinmeyen kısıt kodu {bilinmeyen}.")
        if len(set(kisit)) != len(kisit):
            raise KatalogHatasi(f"{kimlik}: aynı kısıt kodu birden fazla.")

        anahtar = (hastalik, alt_tur)
        if anahtar in gorulen:
            raise KatalogHatasi(f"{kimlik}: (hastalik, alt_tur) tekrarı.")
        gorulen.add(anahtar)

        not_metni = ham.get("kaynak_not") or ""
        if not isinstance(not_metni, str):
            raise KatalogHatasi(f"{kimlik}: 'kaynak_not' metin değil.")

        ad, sag, rozet = _ayir(hastalik)
        if alt_tur.strip() and alt_tur.strip() != _TIRE:
            seviye = alt_tur.strip()
        elif sag:
            seviye = sag
        else:
            seviye = "tek oran"

        kayitlar.append(
            Kayit(
                id=kimlik,
                bolum=bolum,
                grup=ham.get("grup"),
                hastalik=hastalik,
                alt_tur=alt_tur,
                oran=oran,
                sayfa=sayfa,
                kisit=tuple(kisit),
                kaynak_not=not_metni.strip(),
                ad=ad,
                rozet=rozet,
                seviye=seviye,
                arama_metni=katla(" ".join((hastalik, alt_tur, rozet, seviye))),
            )
        )

    # 2) Sayı ve kimlik değişmezleri
    if len(kayitlar) != BEKLENEN_KESIN:
        raise KatalogHatasi(
            f"Kesin kayıt sayısı {len(kayitlar)}; beklenen {BEKLENEN_KESIN}."
        )
    dagilim = {b: sum(1 for k in kayitlar if k.bolum == b) for b in BEKLENEN_BOLUM_DAGILIMI}
    if dagilim != BEKLENEN_BOLUM_DAGILIMI:
        raise KatalogHatasi(f"Bölüm dağılımı {dagilim}; beklenen {BEKLENEN_BOLUM_DAGILIMI}.")

    id_ile = {k.id: k for k in kayitlar}
    if len(id_ile) != len(kayitlar):
        raise KatalogHatasi("Aynı kimlik birden fazla kayıtta kullanılmış.")
    if any(k.id.startswith("X-") for k in kayitlar):
        raise KatalogHatasi("Katalogda 'X-' kimliği olmamalı (§3.4).")

    numaralar: dict[str, list[int]] = {}
    for k in kayitlar:
        eslesme = _KIMLIK.match(k.id)
        if not eslesme:
            raise KatalogHatasi(f"Geçersiz kimlik biçimi: {k.id}")
        numaralar.setdefault(eslesme.group(1), []).append(int(eslesme.group(2)))
    for onek, sayilar in numaralar.items():
        if sorted(sayilar) != list(range(1, len(sayilar) + 1)):
            raise KatalogHatasi(f"{onek} kimlikleri kesintisiz değil.")

    for belirsiz_kimlik, katalog_kimlik in BEKLENEN_COZULEN.items():
        if katalog_kimlik not in id_ile:
            raise KatalogHatasi(f"Çözülen kayıt katalogda yok: {katalog_kimlik}")

    tire_idler = tuple(sorted(k.id for k in kayitlar if k.alt_tur.strip() == _TIRE))
    if tire_idler != BEKLENEN_TIRE_IDLER:
        raise KatalogHatasi(f"'—' kayıtları değişmiş: {tire_idler}")

    # 3) Gezinme ağacı (§3.5/§3.7)
    bolum_sirasi = [b for b in BEKLENEN_BOLUM_DAGILIMI if dagilim[b]]
    bolumler: list[Bolum] = []
    for bolum_adi in bolum_sirasi:
        bolum_kayitlari = tuple(k for k in kayitlar if k.bolum == bolum_adi)
        grup_sirasi: list[tuple[str, str]] = []
        grup_kayitlari: dict[str, list[Kayit]] = {}
        for kayit in bolum_kayitlari:
            ham = {"bolum": kayit.bolum, "id": kayit.id,
                   "grup": kayit.grup, "_grup_adlari": grup_adlari}
            anahtar, ad = _bolum_2_anahtari(ham, kayit.rozet)
            if anahtar not in grup_kayitlari:
                grup_sirasi.append((anahtar, ad))
                grup_kayitlari[anahtar] = []
            grup_kayitlari[anahtar].append(kayit)

        gruplar: list[Grup] = []
        for anahtar, ad in grup_sirasi:
            uyeler = tuple(grup_kayitlari[anahtar])
            hastalik_sirasi: list[str] = []
            hastalik_kayitlari: dict[str, list[Kayit]] = {}
            for kayit in uyeler:
                if kayit.ad not in hastalik_kayitlari:
                    hastalik_sirasi.append(kayit.ad)
                    hastalik_kayitlari[kayit.ad] = []
                hastalik_kayitlari[kayit.ad].append(kayit)
            hastaliklar = tuple(
                Hastalik(
                    anahtar=f"{anahtar}|{hastalik_adi}",
                    ad=hastalik_adi,
                    kayitlar=tuple(hastalik_kayitlari[hastalik_adi]),
                )
                for hastalik_adi in hastalik_sirasi
            )
            rozet = (
                uyeler[0].grup
                if bolum_adi in (
                    "DERİ",
                    "KULAK BURUN BOĞAZ",
                    "KARDİYOVASKÜLER SİSTEM",
                )
                else uyeler[0].rozet.split("-", 1)[0]
            )
            gruplar.append(
                Grup(anahtar=anahtar, ad=ad, rozet=rozet, kayitlar=uyeler,
                     hastaliklar=hastaliklar)
            )

        if bolum_adi == "DERİ" and len(gruplar) != 15:
            raise KatalogHatasi(f"DERİ grup sayısı {len(gruplar)}; beklenen 15.")
        if bolum_adi == "ZİHİNSEL, RUHSAL, DAVRANIŞSAL BOZUKLUKLAR" and len(gruplar) != 6:
            raise KatalogHatasi(f"Z başlık sayısı {len(gruplar)}; beklenen 6.")
        if bolum_adi == "HEMATOLOJİK HASTALIKLAR" and len(gruplar) != 10:
            raise KatalogHatasi(f"H başlık sayısı {len(gruplar)}; beklenen 10.")
        if bolum_adi == "KULAK BURUN BOĞAZ" and len(gruplar) != 7:
            raise KatalogHatasi(f"KBB grup sayısı {len(gruplar)}; beklenen 7.")
        if bolum_adi == "KARDİYOVASKÜLER SİSTEM" and len(gruplar) != 9:
            raise KatalogHatasi(f"Kalp-Damar grup sayısı {len(gruplar)}; beklenen 9.")

        bolumler.append(
            Bolum(
                ad=bolum_adi,
                kisa=BOLUM_KISA_ADLARI.get(bolum_adi, bolum_adi),
                kayitlar=bolum_kayitlari,
                gruplar=tuple(gruplar),
            )
        )

    tek_kayitli = tuple(
        sorted(
            h.kayitlar[0].id
            for bolum in bolumler
            for grup in bolum.gruplar
            for h in grup.hastaliklar
            if h.tek_kayit
        )
    )
    if tek_kayitli != BEKLENEN_TEK_KAYITLI:
        raise KatalogHatasi(f"Tek kayıtlı gruplar değişmiş: {tek_kayitli}")

    # 4) Belirsiz dosyası
    belirsizler: list[BelirsizKayit] = []
    for ham in belirsiz_satirlar:
        if not isinstance(ham, dict):
            raise KatalogHatasi("belirsiz.json satırı sözlük değil.")
        kimlik = _metin(ham.get("id"), "id")
        durum = decl = _metin(ham.get("durum"), "durum")
        if decl not in ("belirsiz", "cozuldu"):
            raise KatalogHatasi(f"{kimlik}: bilinmeyen durum {durum!r}.")
        bolum = _metin(ham.get("bolum"), "bolum")
        hastalik = _metin(ham.get("hastalik"), "hastalik")
        alt_tur = ham.get("alt_tur") or ""
        if not isinstance(alt_tur, str):
            raise KatalogHatasi(f"{kimlik}: 'alt_tur' metin değil.")
        sorun = ham.get("sorun_tipi")
        if not isinstance(sorun, str) or sorun not in SORUN_TIPLERI:
            raise KatalogHatasi(f"{kimlik}: bilinmeyen sorun_tipi {sorun!r}.")

        oran = ham.get("oran")
        if oran is not None and (isinstance(oran, bool) or not isinstance(oran, int)):
            raise KatalogHatasi(f"{kimlik}: 'oran' tam sayı değil.")
        sayfa = ham.get("sayfa")
        if sayfa is not None and (isinstance(sayfa, bool) or not isinstance(sayfa, int)):
            raise KatalogHatasi(f"{kimlik}: 'sayfa' tam sayı değil.")

        cozum = ham.get("cozum_tarihi") or ""
        if not isinstance(cozum, str):
            raise KatalogHatasi(f"{kimlik}: 'cozum_tarihi' metin değil.")
        kaynak_sayfa = ham.get("kaynak_sayfa")
        if durum == "cozuldu":
            if not cozum or not isinstance(kaynak_sayfa, int):
                raise KatalogHatasi(
                    f"{kimlik}: çözüldü satırında cozum_tarihi/kaynak_sayfa eksik."
                )
            if kimlik not in BEKLENEN_COZULEN:
                raise KatalogHatasi(f"{kimlik}: beklenmeyen çözüldü satırı.")
        if kimlik in id_ile:
            raise KatalogHatasi(f"{kimlik}: katalogda da bulunuyor (mükerrer).")

        belirsiz_ad, belirsiz_sag, _rozet = _ayir(hastalik)
        if alt_tur.strip() and alt_tur.strip() != _TIRE:
            belirsiz_seviye = alt_tur.strip()
        elif belirsiz_sag:
            belirsiz_seviye = belirsiz_sag
        else:
            belirsiz_seviye = "tek oran"

        belirsizler.append(
            BelirsizKayit(
                id=kimlik,
                bolum=bolum,
                hastalik=hastalik,
                alt_tur=alt_tur,
                oran=oran,
                sayfa=sayfa,
                durum=durum,
                sorun_tipi=sorun,
                aciklama=ham.get("aciklama") if isinstance(ham.get("aciklama"), str) else "",
                kaynak_metin=ham.get("kaynak_metin") if isinstance(ham.get("kaynak_metin"), str) else "",
                cozum_tarihi=cozum,
                kaynak_sayfa=kaynak_sayfa if isinstance(kaynak_sayfa, int) else None,
                arama_metni=katla(" ".join((hastalik, alt_tur))),
                ad=belirsiz_ad,
                seviye=belirsiz_seviye,
            )
        )

    acik = tuple(sorted(b.id for b in belirsizler if b.durum == "belirsiz"))
    if acik != tuple(sorted(BEKLENEN_BELIRSIZ_IDLER)):
        raise KatalogHatasi(f"Açık belirsiz satırlar değişmiş: {acik}")
    cozulen = tuple(sorted(b.id for b in belirsizler if b.durum == "cozuldu"))
    if cozulen != tuple(sorted(BEKLENEN_COZULEN)):
        raise KatalogHatasi(f"Çözülen satırlar değişmiş: {cozulen}")

    sayi = meta.get("sayi") or {}
    if sayi.get("kesin_kayit") != BEKLENEN_KESIN or sayi.get("belirsiz_kayit") != BEKLENEN_BELIRSIZ:
        raise KatalogHatasi("meta.sayi kesin/belirsiz sayıları beklenenle uyuşmuyor.")
    if sayi.get("toplam_sayisal_satir") != BEKLENEN_TOPLAM:
        raise KatalogHatasi("meta.sayi toplam satır sayısı beklenenle uyuşmuyor.")
    if len(kayitlar) + len(acik) != BEKLENEN_TOPLAM:
        raise KatalogHatasi(f"Kesin + belirsiz toplamı {BEKLENEN_TOPLAM} değil.")

    dosya_ozeti = MappingProxyType(
        {
            "katalog": {"yol": str(katalog_yolu), "boyut": katalog_yolu.stat().st_size},
            "belirsiz": {"yol": str(belirsiz_yolu), "boyut": belirsiz_yolu.stat().st_size},
        }
    )

    return Katalog(
        kayitlar=tuple(kayitlar),
        belirsiz=tuple(belirsizler),
        id_ile=MappingProxyType(id_ile),
        bolumler=tuple(bolumler),
        meta=MappingProxyType(meta),
        belirsiz_meta=MappingProxyType(belirsiz_ham.get("meta") or {}),
        dosya_ozeti=dosya_ozeti,
    )
