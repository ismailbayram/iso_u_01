"""Kumanda cubuk degerlerini ucagin servo ve ESC ciktisina ceviren saf fonksiyonlar.

STM32'nin applyOutputs() hesabinin aynisi; trim olcerken ekranda gorulen
aci, servoya giden aciyla birebir tutmali. Firmware'deki sabitler
degisirse burasi da degismeli. STM32'nin kendi alcak geciren filtresi
burada yok: cubuk sabitken sonuc ayni.

Bu modul hicbir G/C yapmaz ve hicbir GUI kutuphanesi import etmez.
"""

STICK_MAX = 4095
STICK_CENTER = 2048
# STM32'deki olu bolge; kumandanin kendi 18'lik olu bolgesinden genis.
AIRCRAFT_DEADBAND = 45

SERVO_CENTER_DEG = 90
SERVO_TRAVEL_DEG = 45
SERVO_MIN_DEG = SERVO_CENTER_DEG - SERVO_TRAVEL_DEG
SERVO_MAX_DEG = SERVO_CENTER_DEG + SERVO_TRAVEL_DEG

MIN_THROTTLE_US = 1100
MAX_THROTTLE_US = 1940


def _arduino_map(x: int, in_min: int, in_max: int, out_min: int, out_max: int) -> int:
    # Arduino map() tamsayi bolmesi yapar ve sifira dogru keser.
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min)) + out_min


def _clamp_stick(raw: int) -> int:
    return max(0, min(STICK_MAX, raw))


def center_offset(raw: int) -> int:
    """Cubugun merkezden sapmasi, ham birimde. Trim bu sayidan okunur."""
    return raw - STICK_CENTER


def servo_deg(raw: int) -> int:
    """Kanal degerinin STM32'de servoya yazilan acisi."""
    if abs(raw - STICK_CENTER) < AIRCRAFT_DEADBAND:
        raw = STICK_CENTER
    return _arduino_map(_clamp_stick(raw), 0, STICK_MAX, SERVO_MIN_DEG, SERVO_MAX_DEG)


def throttle_us(raw: int) -> int:
    """Gaz kanalinin armed durumda ESC'ye giden darbe genisligi."""
    return _arduino_map(_clamp_stick(raw), 0, STICK_MAX, MIN_THROTTLE_US, MAX_THROTTLE_US)
