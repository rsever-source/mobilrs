@app.post("/kira-hesapla")
async def kira_hesapla(
    mevcut_kira: float = Form(...),
    yenileme_ayi: int = Form(...),
):

    if mevcut_kira <= 0:
        raise HTTPException(
            status_code=400,
            detail="Geçerli kira tutarı gir.",
        )

    if yenileme_ayi < 1 or yenileme_ayi > 12:
        raise HTTPException(
            status_code=400,
            detail="Geçerli yenileme ayı seç.",
        )

    try:
        tufe = get_current_tufe()

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )


    rate = float(
        tufe["rate"]
    )

    artis = (
        mevcut_kira
        * rate
        / 100
    )

    yeni_kira = (
        mevcut_kira
        + artis
    )


    today = date.today()

    if yenileme_ayi >= today.month:
        renewal_year = today.year
    else:
        renewal_year = today.year + 1


    if yenileme_ayi == 1:
        target_year = (
            renewal_year - 1
        )
        target_month = 12
    else:
        target_year = renewal_year
        target_month = (
            yenileme_ayi - 1
        )


    MONTH_NAMES = {
        1: "Ocak",
        2: "Şubat",
        3: "Mart",
        4: "Nisan",
        5: "Mayıs",
        6: "Haziran",
        7: "Temmuz",
        8: "Ağustos",
        9: "Eylül",
        10: "Ekim",
        11: "Kasım",
        12: "Aralık",
    }


    current_period = (
        int(tufe["year"]),
        int(tufe["month"]),
    )

    target_period = (
        target_year,
        target_month,
    )


    if current_period == target_period:

        durum = (
            f"{MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} yenilemesi için "
            f"gerekli {tufe['period']} verisi "
            f"yayımlanmış. Hesap güncel resmi "
            f"TÜİK oranıyla yapıldı."
        )

    elif current_period < target_period:

        durum = (
            f"Son resmi veri {tufe['period']}. "
            f"{MONTH_NAMES[yenileme_ayi]} "
            f"{renewal_year} yenilemesi için "
            f"{MONTH_NAMES[target_month]} "
            f"{target_year} verisi henüz "
            f"yayımlanmadı. Şimdilik son "
            f"resmi oran kullanıldı."
        )

    else:

        durum = (
            f"Hesap son resmi "
            f"{tufe['period']} TÜFE verisiyle "
            f"yapıldı."
        )


    if (
        tufe.get("data_mode")
        == "cache"
    ):

        durum += (
            " TÜİK canlı bağlantısı o anda "
            "sonuç vermediği için daha önce "
            "başarıyla alınmış son resmi veri "
            "kullanıldı."
        )


    def money_tr(value):

        text = f"{value:,.2f}"

        text = (
            text
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        return text + " TL"


    return JSONResponse(
        {
            "oran": (
                f"{rate:.2f}"
                .replace(".", ",")
            ),

            "yeni_kira":
                money_tr(
                    yeni_kira
                ),

            "mevcut_kira":
                money_tr(
                    mevcut_kira
                ),

            "artis":
                money_tr(
                    artis
                ),

            "donem":
                tufe["period"],

            "durum":
                durum,

            "source":
                tufe["source"],

            "data_mode":
                tufe.get(
                    "data_mode",
                    "live",
                ),
        }
    )
