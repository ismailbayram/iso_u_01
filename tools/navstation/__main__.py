"""Giris noktasi:  python -m navstation --port /dev/cu.usbserial-XXXX"""

import argparse
import sys

from . import link, ui


def main() -> int:
    parser = argparse.ArgumentParser(description="ISO U1 yer istasyonu")
    parser.add_argument("--port", required=True,
                        help="ESP32 kumandanin seri portu")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    serial_link = link.SerialLink(args.port, args.baud)
    if not serial_link.open():
        print(f"Port acilamadi: {serial_link.last_error}", file=sys.stderr)
        return 1

    try:
        ui.NavStationWindow(serial_link).run()
    finally:
        serial_link.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
