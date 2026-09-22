"""Giris noktasi:  python -m navstation  [--port /dev/cu.usbserial-XXXX]

Port verilmezse pencere baglantisiz acilir ve alt seritten secilir.
"""

import argparse

from . import ui


def main() -> int:
    parser = argparse.ArgumentParser(description="ISO U1 yer istasyonu")
    parser.add_argument("--port", default=None,
                        help="Acilista baglanilacak seri port. Verilmezse "
                             "arayuzden secilir.")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    window = ui.NavStationWindow(baud=args.baud, initial_port=args.port)
    try:
        window.run()
    finally:
        window.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
