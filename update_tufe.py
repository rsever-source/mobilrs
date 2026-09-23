from tufe_service import update_cache_from_tuik


if __name__ == "__main__":

    try:
        data = update_cache_from_tuik()

        print(
            "TÜFE cache güncellendi:"
        )

        print(
            f"Dönem: {data['period']}"
        )

        print(
            f"12 aylık ortalama: %{data['rate']}"
        )

        print(
            f"Kaynak: {data['source']}"
        )

    except Exception as e:

        print(
            f"TÜFE güncelleme başarısız: {e}"
        )

        raise
