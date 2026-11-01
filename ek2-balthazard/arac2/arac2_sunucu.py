# -*- coding: utf-8 -*-
"""Araç-2 — Balthazard ekranı için küçük, bağımsız sunucu (prototip).

Amaç: ``SOZLESME.md`` §5 tasarımını **çalışan** bir ekran olarak
göstermek ve onaylı ortak motoru (``balthazard_motoru``) hiç kopyalamadan
kullanmak. Ekran kendi hesabını yapmaz; tüm sayılar motordan gelir.

Tasarım kararları (sözleşmeye bağlı):

* Hesap **yalnız** ``balthazard()`` ile yapılır; kopya formül yoktur.
* Gösterim **yalnız** ``bicimle_gosterim()`` ile üretilir (G-1…G-4): en fazla
  2 ondalık, yarı yukarı, sondaki sıfırlar atılır, Türkçe virgül.
* Ham değer (``sonuc.deger``) yanıtta **aynen** taşınır; istemci onu kopyalar.
* Motorun hata/uyarı kodları değiştirilmez; ekran yalnız ``hata.mesaj`` gösterir.

Bu dosya **prototiptir**: canlı FastAPI uygulamasına bağlanmadı, depoya
eklenmedi. Yalnız yerel olarak (127.0.0.1) çalışır; dışarıya açılmaz.

Çalıştırma:

    <python> arac2_sunucu.py            # http://127.0.0.1:8765
    <python> arac2_sunucu.py 9000       # başka port
"""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK))

from balthazard_motoru import balthazard, bicimle_gosterim  # noqa: E402

SAYFA = BURASI / "arac2.html"
AZAMI_GOVDE = 64 * 1024
_GOVDE_HATASI = object()
VARSAYILAN_PORT = 8765


def gosterim_ekle(sonuc: dict) -> dict:
    """Motor yanıtına **sunum** metinlerini ekler; ham değerlere dokunmaz."""
    adimlar = []
    for adim in sonuc["adimlar"]:
        adimlar.append(
            {
                "onceki": bicimle_gosterim(adim["onceki"]),
                "eklenen": bicimle_gosterim(adim["eklenen"]),
                "sonuc": bicimle_gosterim(adim["sonuc"]),
            }
        )
    return {
        "sonuc": bicimle_gosterim(sonuc["sonuc"]["deger"]),
        "adimlar": adimlar,
    }


class Isleyici(BaseHTTPRequestHandler):
    server_version = "Arac2Prototip/0.1"
    sys_version = ""

    # --- yanıt yardımcıları -------------------------------------------------

    def _gonder(self, durum: HTTPStatus, govde: bytes, tur: str) -> None:
        self.send_response(durum)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(govde)

    def _json(self, veri: dict, durum: HTTPStatus = HTTPStatus.OK) -> None:
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self._gonder(durum, govde, "application/json; charset=utf-8")

    def _html(self) -> None:
        try:
            govde = SAYFA.read_bytes()
        except OSError:
            self._json(
                {"ok": False, "mesaj": "Ekran dosyası bulunamadı."},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._gonder(HTTPStatus.OK, govde, "text/html; charset=utf-8")

    # --- yönlendirme --------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 (http.server API'si)
        yol = self.path.split("?", 1)[0]
        if yol in ("/", "/arac2", "/arac2/"):
            self._html()
        elif yol == "/saglik":
            self._json({"ok": True})
        else:
            self._json({"ok": False, "mesaj": "Bulunamadı."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        yol = self.path.split("?", 1)[0]
        if yol != "/api/hesapla":
            self._json({"ok": False, "mesaj": "Bulunamadı."}, HTTPStatus.NOT_FOUND)
            return

        girdi = self._govde_oku()
        if girdi is _GOVDE_HATASI:
            return

        sonuc = balthazard(girdi)  # tüm doğrulama ve hesap motorda
        if sonuc.get("ok"):
            sonuc["gosterim"] = gosterim_ekle(sonuc)
        self._json(sonuc)

    # --- gövde --------------------------------------------------------------

    def _govde_oku(self):
        """JSON gövdeyi okur. Bozuk istekte yanıtı yazıp ``None`` döner."""
        try:
            uzunluk = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            uzunluk = -1
        if uzunluk <= 0 or uzunluk > AZAMI_GOVDE:
            self._json(
                {"ok": False, "mesaj": "İstek okunamadı."}, HTTPStatus.BAD_REQUEST
            )
            return _GOVDE_HATASI

        ham = self.rfile.read(uzunluk)
        try:
            veri = json.loads(ham.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(
                {"ok": False, "mesaj": "İstek okunamadı."}, HTTPStatus.BAD_REQUEST
            )
            return _GOVDE_HATASI

        # JSON sözdizimi geçerliyse tür doğrulamasını ortak motor yapar;
        # böylece E_ORAN_TIP sözleşmesi ve hata gövdesi korunur.
        return veri

    # Gürültülü varsayılan günlük yerine tek satır.
    def log_message(self, kalip: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), kalip % args))


def main(argv: list[str]) -> int:
    port = VARSAYILAN_PORT
    if len(argv) > 1:
        try:
            port = int(argv[1])
        except ValueError:
            print("Port tam sayı olmalıdır.", file=sys.stderr)
            return 2

    if not SAYFA.exists():
        print("Ekran dosyası bulunamadı: %s" % SAYFA, file=sys.stderr)
        return 1

    sunucu = ThreadingHTTPServer(("127.0.0.1", port), Isleyici)
    print("Araç-2 prototipi: http://127.0.0.1:%d" % port)
    print("Durdurmak için Ctrl+C")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nDurduruldu.")
    finally:
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
