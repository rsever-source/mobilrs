# -*- coding: utf-8 -*-
"""Ortak Balthazard hesaplama motoru.

Sözleşme: ``ORTAK-MOTOR-SOZLESME.md`` (sürüm 0.3, 28.10.2026).
Bu modül **yalnızca hesap yapar**; katalog okumaz, hastalık/etiket/kimlik bilmez.

Tek genel giriş noktası ``balthazard(girdi)``'dir. İki araç da (Araç-1 ve Araç-2)
aynı fonksiyonu çağırır; kopya hesap kodu yasaktır.

Sözleşmeye bağlı davranışlar
---------------------------
* Oranlar **büyükten küçüğe** sıralanır (kararlı sıralama); sıra kullanıcıya sorulmaz.
* Balthazard: ``yeni = A + (100 - A) * B / 100`` (yüzde ifadesiyle).
* 65 yaş ve üzeri seçiliyse %10, **aynı yöntemle** son adım olarak eklenir
  (aritmetik ``+10`` **değil**). Örnek: ``[40]`` + 65+ -> ``46``.
* ``yas_ekle=False`` (Araç-1 bilgi çağrısı) ise yaş eki **uygulanmaz**.
* **Motor yuvarlamaz**: ara aşamalarda ve sonuçta ham değer döner;
  ``yuvarlama.uygulandi`` her zaman ``False``.
* Hata durumunda **istisna fırlatılmaz**; ``{"ok": False, "hata": {...}}`` döner.

Yuvarlama ve gösterim
---------------------
Hesap, ikili kayan nokta gürültüsünü önlemek için içeride **kesirli (Fraction)**
aritmetikle yürütülür; dışarıya tek bir dönüşümle ``int`` (tam sayıysa) veya
``float`` olarak verilir. Bu bir yuvarlama değildir: ``tam_sayi_mi`` kesrin
paydasından **kesin** olarak hesaplanır.

Gösterim kuralı **kapandı** (G-1…G-4, 28.10.2026 ürün kararı): en fazla **2
ondalık**, **yarı yukarı** (``ROUND_HALF_UP``), tam sayıda ondalık yok, sondaki
gereksiz sıfırlar atılır, Türkçe virgül; yuvarlama **tek kez ve yalnız sunumda**
yapılır (ham bileşke -> yaş eki -> gösterim). Bu modüldeki ``bicimle_gosterim()``
ayrı bir **sunum** yardımcısıdır; motorun döndürdüğü ham değeri değiştirmez,
yalnızca ekranda gösterilecek metni üretir. ``balthazard()`` çıktısı (``sonuc``,
``adimlar``, ``yuvarlama``) bu kuraldan **etkilenmez**.

Sözleşmede karşılığı olmayan (kötü niyetli/bozuk) girdiler
---------------------------------------------------------
Yeni hata kodu **uydurulmaz**; en yakın sözleşme kodu kullanılır:

* ``girdi`` sözlük (Mapping) değilse -> ``E_ORAN_TIP`` (``alan="girdi"``)
* ``oranlar`` liste/demet değilse -> ``E_ORAN_TIP`` (``alan="oranlar"``)
* ``bool`` değer oran olarak verilirse -> ``E_ORAN_TIP`` (True/1 karışmasın)
* ``NaN`` / ``inf`` -> ``E_ORAN_TIP`` (kullanılabilir sayı değil)
* ``12.0`` gibi **tam sayı değerli** float -> tam sayıya normalize edilir
* ``12.5`` gibi ondalıklı değer -> ``E_ORAN_TAMSAYI`` (B-7: ürün tercihi)
* ``yas_ekle`` **yalnızca gerçek ``bool``** kabul eder (aşağıdaki "yas_ekle tip
  kuralı" bölümü)

``yas_ekle`` tip kuralı
-----------------------
``yas_ekle`` alanı **yalnızca** ``True`` veya ``False`` olabilir. Alan hiç
gönderilmezse sözleşme gereği varsayılan ``True``'dur. ``"false"``, ``0``, ``1``,
``None``, ``0.0`` gibi değerler **sessizce** ``bool()`` ile dönüştürülmez; çağrı
``ok=False`` ile reddedilir.

Sözleşmede (``ORTAK-MOTOR-SOZLESME.md`` §5) bu alan için **ayrı hata kodu yoktur**
ve bu modül **yeni kod uydurmaz**. Kullanılan eşleme:

* kod: ``E_YAS_GECERSIZ`` — alan yaş grubuna aittir (ek oranın uygulanıp
  uygulanmayacağını belirler), mevcut sözleşme kodlarından en yakını budur;
* ``alan``: ``"yas_ekle"`` — çağıran kod hatayı doğru alanda görür ve düzeltir;
* ``mesaj``: sözleşmedeki genel yaş metni olduğu gibi kalır (yeni metin
  uydurulmaz). Bu durum yalnızca **çağıran koddaki programlama hatasıyla**
  oluşabilir; kullanıcı arayüzü bu alanı göndermez.

Doğrulama sırası: ``oranlar`` -> ``yas`` -> ``yas_ekle``.

Açık maddeler (bu motorda **bilinçli olarak** uygulanmaz)
--------------------------------------------------------
* **B-4** tavan/kırpma: kırpma yapılmaz (sonuç matematik gereği 100'ü aşmaz).
* **B-5** 0 ve 100: özel işlem yok; 0 etkisizdir, 100 sonucu kilitler.
* **B-8** DERİ bölümündeki "+%5": kataloğa ve motora **eklenmez** (X-D03 açık).
* **B-3** yaş ekinin yuvarlamaya göre sırası: motor yuvarlamadığı için konu doğmaz.

Bu modül üretim/geliştirme ortamından bağımsızdır: yalnız standart kütüphane
kullanır.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fractions import Fraction
from numbers import Integral, Real

__all__ = [
    "balthazard",
    "bicimle_gosterim",
    "YAS_ALTI",
    "YAS_VE_UZERI",
    "YAS_EKI_ORANI",
    "DAYANAK",
    "MOTOR_SURUMU",
]

# --- Sözleşme sabitleri ------------------------------------------------------

MOTOR_SURUMU = "0.2"  # sözleşme 0.3 ile uyumlu; hesap değişmedi, gösterim kuralı kapandı

YAS_ALTI = "65_alti"
YAS_VE_UZERI = "65_ve_uzeri"
GECERLI_YAS = (YAS_ALTI, YAS_VE_UZERI)

YAS_EKI_ORANI = 10  # sabit; eşik motorda tek yerde (65) tutulur
YAS_ESIGI = 65

DAYANAK = "Yönetmelik m. 10/4 (RG 20.02.2019, 30692)"

SIRALAMA_KURALI = "buyukten_kucuge"

YUVARLAMA_NOT = (
    "Ham değer döndürülür; yuvarlama yalnız gösterim katmanında, en fazla 2 ondalık "
    "(G-1…G-4)."
)

# Hata ve uyarı metinleri — sözleşme §5 ile birebir aynı.
MESAJ_ORAN_YOK = "En az bir oran girin."
MESAJ_ORAN_ARALIK = "Oran 0 ile 100 arasında olmalıdır."
MESAJ_ORAN_TAMSAYI = "Oran tam sayı olmalıdır."
MESAJ_ORAN_TIP = "Yalnız sayı girin."
MESAJ_YAS = "Yaş aralığını seçin."

MESAJ_TEKRAR = (
    "Bu oran listede zaten var. Her iki giriş de hesaplamaya dahil edilir."
)
MESAJ_ORAN_100 = "100 oranı eklendiğinde bileşke üst sınıra ulaşır. Devam edilsin mi?"
MESAJ_ORAN_SIFIR = "0 oranı listeye eklendi. Bileşkeyi değiştirmez."

_ALAN_ORANLAR = "oranlar"
_ALAN_YAS = "yas"
_ALAN_YAS_EKLE = "yas_ekle"
_ALAN_GIRDI = "girdi"


# --- İç yardımcılar ----------------------------------------------------------


def _hata(kod: str, mesaj: str, alan: str) -> dict:
    """Sözleşme §3'teki hata zarfını üretir."""
    return {"ok": False, "hata": {"kod": kod, "mesaj": mesaj, "alan": alan}}


def _uyari(kod: str, mesaj: str) -> dict:
    return {"kod": kod, "mesaj": mesaj}


def _sayi(deger: Fraction):
    """Kesri dışa verilecek sayıya çevirir: tam sayıysa int, değilse float.

    Tek ve bilinçli dönüşüm noktası burasıdır; yuvarlama yapılmaz.
    """
    if deger.denominator == 1:
        return int(deger)
    return float(deger)


def _oran_normallestir(ham):
    """Tek bir oranı doğrular ve tam sayıya normalize eder.

    Dönüş: ``(deger, None)`` başarılıysa, ``(None, hata_kodu)`` değilse.
    """
    if isinstance(ham, bool):
        # bool, int'in alt sınıfıdır; True/1 karışmasını engellemek için ayrı ele alınır.
        return None, "E_ORAN_TIP"

    if isinstance(ham, Integral):
        deger = int(ham)
    elif isinstance(ham, Real):
        try:
            kayan = float(ham)
        except (TypeError, ValueError, OverflowError):
            return None, "E_ORAN_TIP"
        if not math.isfinite(kayan):
            return None, "E_ORAN_TIP"
        if not kayan.is_integer():
            return None, "E_ORAN_TAMSAYI"
        deger = int(kayan)
    else:
        return None, "E_ORAN_TIP"

    if deger < 0 or deger > 100:
        return None, "E_ORAN_ARALIK"
    return deger, None


def _birlestir(mevcut: Fraction, eklenen: Fraction) -> Fraction:
    """Balthazard: ``A + (100 - A) * B / 100`` (ham, yuvarlanmaz)."""
    return mevcut + (100 - mevcut) * eklenen / 100


# --- Genel giriş noktası -----------------------------------------------------


def balthazard(girdi) -> dict:
    """Oranları birleştirir ve yaş ekini (gerekiyorsa) uygular.

    Parametre ``girdi`` (sözleşme §2):

    * ``oranlar``: 0–100 tam sayı listesi, en az 1 öğe (sıra anlamsız).
    * ``yas``: ``"65_alti"`` veya ``"65_ve_uzeri"`` (zorunlu, varsayılan yok).
    * ``yas_ekle``: gerçek ``bool``, varsayılan ``True``. Araç-1 ``False``
      gönderir. ``True``/``False`` dışındaki değerler **kabul edilmez**
      (``E_YAS_GECERSIZ``, ``alan="yas_ekle"``); sessiz dönüşüm yapılmaz.

    Dönüş: sözleşme §3'teki sözlük. Hiçbir durumda istisna fırlatılmaz.
    """
    if not isinstance(girdi, Mapping):
        return _hata("E_ORAN_TIP", MESAJ_ORAN_TIP, _ALAN_GIRDI)

    oranlar = girdi.get("oranlar")
    yas = girdi.get("yas")
    yas_ekle = girdi.get("yas_ekle", True)

    # 1) Oranlar
    if not isinstance(oranlar, (list, tuple)):
        return _hata("E_ORAN_TIP", MESAJ_ORAN_TIP, _ALAN_ORANLAR)

    if len(oranlar) == 0:
        return _hata("E_ORAN_YOK", MESAJ_ORAN_YOK, _ALAN_ORANLAR)

    sayilar = []
    for ham in oranlar:
        deger, kod = _oran_normallestir(ham)
        if kod is not None:
            mesaj = {
                "E_ORAN_TIP": MESAJ_ORAN_TIP,
                "E_ORAN_TAMSAYI": MESAJ_ORAN_TAMSAYI,
                "E_ORAN_ARALIK": MESAJ_ORAN_ARALIK,
            }[kod]
            return _hata(kod, mesaj, _ALAN_ORANLAR)
        sayilar.append(deger)

    # 2) Yaş (oranlardan sonra doğrulanır — sözleşme test vektörleri 10–13)
    if yas is None:
        return _hata("E_YAS_SECILMEDI", MESAJ_YAS, _ALAN_YAS)

    try:
        yas_gecerli = yas in GECERLI_YAS
    except Exception:  # egzotik __eq__ uygulamalarına karşı
        yas_gecerli = False
    if not yas_gecerli:
        return _hata("E_YAS_GECERSIZ", MESAJ_YAS, _ALAN_YAS)

    # 2b) yas_ekle yalnızca gerçek bool (sessiz bool() dönüşümü yok).
    #     Sözleşmede bu alan için ayrı kod olmadığından mevcut yaş kodu kullanılır;
    #     hata, alan="yas_ekle" ile çağıran koda yönlendirilir. Yeni kod uydurulmadı.
    if not isinstance(yas_ekle, bool):
        return _hata("E_YAS_GECERSIZ", MESAJ_YAS, _ALAN_YAS_EKLE)

    # 3) Sıralama — büyükten küçüğe, kararlı, sayısal
    siralama = sorted(sayilar, reverse=True)

    # 4) Bileşke (ham, kesirli aritmetik)
    mevcut = Fraction(siralama[0])
    adimlar = [
        {
            "sira": 1,
            "onceki": 0,
            "eklenen": siralama[0],
            "sonuc": _sayi(mevcut),
            "tur": "bileske",
        }
    ]
    for sira, eklenen in enumerate(siralama[1:], start=2):
        yeni = _birlestir(mevcut, Fraction(eklenen))
        adimlar.append(
            {
                "sira": sira,
                "onceki": _sayi(mevcut),
                "eklenen": eklenen,
                "sonuc": _sayi(yeni),
                "tur": "bileske",
            }
        )
        mevcut = yeni

    # 5) 65 yaş eki — yalnız istenmişse ve 65+ seçiliyse, son adım olarak
    yas_dahil = yas_ekle and yas == YAS_VE_UZERI
    if yas_dahil:
        yeni = _birlestir(mevcut, Fraction(YAS_EKI_ORANI))
        adimlar.append(
            {
                "sira": len(adimlar) + 1,
                "onceki": _sayi(mevcut),
                "eklenen": YAS_EKI_ORANI,
                "sonuc": _sayi(yeni),
                "tur": "yas_eki",
            }
        )
        mevcut = yeni

    # 6) Bilgilendirici uyarılar — hiçbiri engellemez (B-6 kapandı)
    uyarilar = []
    if len(set(sayilar)) < len(sayilar):
        uyarilar.append(_uyari("U_ORAN_TEKRAR", MESAJ_TEKRAR))
    if 100 in sayilar:
        uyarilar.append(_uyari("U_ORAN_100", MESAJ_ORAN_100))
    if 0 in sayilar:
        uyarilar.append(_uyari("U_ORAN_SIFIR", MESAJ_ORAN_SIFIR))

    return {
        "ok": True,
        "sonuc": {
            "deger": _sayi(mevcut),
            "tam_sayi_mi": mevcut.denominator == 1,
            "yas_dahil": yas_dahil,
        },
        "adimlar": adimlar,
        "siralama": {
            "kural": SIRALAMA_KURALI,
            "uygulanan": list(siralama),
        },
        "yas_eklemesi": {
            "uygulandi": yas_dahil,
            "oran": YAS_EKI_ORANI,
            "dayanak": DAYANAK,
        },
        "yuvarlama": {
            "uygulandi": False,
            "kural": None,
            "not": YUVARLAMA_NOT,
        },
        "uyarilar": uyarilar,
    }


# --- Sunum katmanı (motora girmez) ------------------------------------------


def bicimle_gosterim(deger, basamak: int = 2, ayirici: str = ",") -> str:
    """Ham sonucu **ekran metnine** çevirir; motorun değerini değiştirmez.

    Kural **kapandı** (G-1…G-4, 28.10.2026 ürün kararı):

    * En fazla ``basamak`` ondalık (varsayılan 2) — G-1.
    * Yuvarlama yönü **yarı yukarı** (``ROUND_HALF_UP``) — G-2; kesme ve yarı çift
      kullanılmaz.
    * Yuvarlama **tek kez ve yalnız burada** yapılır; yaş eki ham bileşkeye uygulanır
      (G-3), adım dökümü de aynı kuralla biçimlenir (G-4).
    * Sondaki gereksiz sıfırlar atılır: ``62.20 -> "62,2"``, ``46.0 -> "46"``.
    * Türkçe ondalık ayırıcı varsayılandır; ``ayirici="."`` ile nokta kullanılabilir.

    Bu fonksiyon yalnızca **sunum** içindir: ``balthazard()`` çıktısındaki
    ``sonuc.deger`` ve ``adimlar[]`` ham kalır, ``yuvarlama.uygulandi`` her zaman
    ``False``'tur. Kopyalama/dışa aktarma ham değeri taşır, bu metni değil.

    Sayı olmayan ya da sonlu olmayan bir değer verilirse ``TypeError`` yükseltir;
    bu bir kullanıcı girdisi hatası değil, çağıran koddaki programlama hatasıdır.
    """
    if isinstance(deger, bool):
        raise TypeError("Gösterim için sayı gerekir.")

    if isinstance(deger, Fraction):
        ham = Decimal(deger.numerator) / Decimal(deger.denominator)
    elif isinstance(deger, Decimal):
        ham = deger
    elif isinstance(deger, int):
        ham = Decimal(deger)
    elif isinstance(deger, float):
        if not math.isfinite(deger):
            raise TypeError("Gösterim için sonlu bir sayı gerekir.")
        ham = Decimal(str(deger))
    else:
        raise TypeError("Gösterim için sayı gerekir.")

    if isinstance(basamak, bool) or not isinstance(basamak, int) or basamak < 0:
        raise ValueError("basamak 0 veya daha büyük bir tam sayı olmalıdır.")

    try:
        kesin = ham.quantize(Decimal(1).scaleb(-basamak), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:  # aşırı büyük/küçük değerler
        raise ValueError("Değer gösterim için biçimlendirilemedi.") from exc

    metin = f"{kesin:.{basamak}f}"
    if "." in metin:
        metin = metin.rstrip("0").rstrip(".")
    if metin in ("", "-0"):
        metin = "0"
    if ayirici != ".":
        metin = metin.replace(".", ayirici)
    return metin
