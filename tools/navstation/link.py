"""ESP32 kumandaya USB seri baglanti: satir ayristirma ve komut gonderme.

Bu modul GUI bilmez. Ayristirici hicbir kosulda istisna atmaz; bozuk satir
None doner ve cagiran taraf sayar.
"""

import threading
from dataclasses import dataclass

import serial

# Firmware INT16_MIN yolluyor: sensor yok demek, 0 derece degil.
TEMP_ABSENT = -32768

FLAG_ACCEL = 0x01
FLAG_GYRO = 0x02
FLAG_MAG = 0x04
FLAG_BARO = 0x08
FLAG_CALIBRATED = 0x10
FLAG_ARMED = 0x20

_COMMANDS = {"CAL", "CALCLR", "DISARM"}


@dataclass(frozen=True)
class Telemetry:
    t_ms: int
    voltage_mv: int
    batt_temp_centi: int
    esc_temp_centi: int
    ax: int
    ay: int
    az: int
    gx: int
    gy: int
    gz: int
    heading_decideg: int
    pressure_pa: int
    baro_temp_centi: int
    flags: int
    rx_count: int


@dataclass(frozen=True)
class Sticks:
    lx: int
    ly: int
    rx: int
    ry: int


def parse_line(line: str) -> Telemetry | Sticks | None:
    """Tek satiri ayristirir. Taninmayan veya bozuk satirda None doner."""
    # Bytes, None veya baska bir tip gelebilir; ayristirici hicbir girdide
    # istisna atmamali. Tip kontrolu, istisna filtresinden daha guvenli:
    # bytes.strip() basariyla calisir ve hatayi bir satir asagi tasir.
    if not isinstance(line, str):
        return None

    text = line.strip()

    if not text.startswith("$"):
        return None

    parts = text.split(",")
    tag = parts[0]

    if tag == "$T":
        fields = parts[1:]
        if len(fields) != 15:
            return None
        values = _to_ints(fields)
        return None if values is None else Telemetry(*values)

    if tag == "$S":
        fields = parts[1:]
        if len(fields) != 4:
            return None
        values = _to_ints(fields)
        return None if values is None else Sticks(*values)

    return None


def _to_ints(fields: list[str]) -> list[int] | None:
    try:
        return [int(f) for f in fields]
    except ValueError:
        return None


class SerialLink:
    """Arka planda seri portu okuyan thread ve son-deger tutucu."""

    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.last_error: str | None = None
        self.bad_line_count = 0

        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._telemetry: Telemetry | None = None
        self._sticks: Sticks | None = None

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def open(self) -> bool:
        # Acikken tekrar cagrilirsa onceki thread ve port sahipsiz kalirdi.
        if self._thread is not None or self._serial is not None:
            self.close()

        self.last_error = None
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.2)
        except (serial.SerialException, OSError) as exc:
            self.last_error = str(exc)
            self._serial = None
            return False

        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def close(self) -> None:
        self._stop.set()

        port = self._serial
        if port is not None:
            try:
                port.close()
            except (serial.SerialException, OSError):
                pass

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        self._serial = None

    def latest_telemetry(self) -> Telemetry | None:
        with self._lock:
            return self._telemetry

    def latest_sticks(self) -> Sticks | None:
        with self._lock:
            return self._sticks

    def send_command(self, name: str) -> bool:
        if name not in _COMMANDS:
            return False

        # Yerel referans: close() baska bir thread'den self._serial'i None
        # yapabilir, kontrol ile yazim arasinda kaybolmasin.
        port = self._serial
        if port is None or not port.is_open:
            return False

        try:
            port.write((name + "\n").encode("ascii"))
            return True
        except (serial.SerialException, OSError, AttributeError) as exc:
            self.last_error = str(exc)
            return False

    def _read_loop(self) -> None:
        # Yerel referans: close() self._serial'i None yaptiginda bu dongu
        # yarim kalmis bir okumanin ortasinda AttributeError almasin.
        port = self._serial
        if port is None:
            return

        while not self._stop.is_set():
            try:
                raw = port.readline()
            except (serial.SerialException, OSError, AttributeError) as exc:
                self.last_error = str(exc)
                return

            if not raw:
                continue

            record = parse_line(raw.decode("ascii", errors="replace"))
            if record is None:
                if raw.startswith(b"$"):
                    self.bad_line_count += 1
                continue

            with self._lock:
                if isinstance(record, Telemetry):
                    self._telemetry = record
                else:
                    self._sticks = record
