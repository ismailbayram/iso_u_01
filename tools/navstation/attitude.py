"""Telemetri ham degerlerini fiziksel birimlere ceviren saf fonksiyonlar.

Bu modul hicbir G/C yapmaz ve hicbir GUI kutuphanesi import etmez.
"""

import math

# ADXL345 varsayilan DATA_FORMAT: +-2 g, 10 bit, 256 LSB/g.
# Ucus firmware'i ham degeri 4'e boluyor, geriye 64 LSB/g kaliyor.
ACCEL_LSB_PER_G = 64.0

# ITG3205 FS_SEL=3: +-2000 derece/saniye.
GYRO_LSB_PER_DPS = 14.375

# Barometrik irtifa formulu (ISA).
_ALTITUDE_COEFFICIENT = 44330.0
_ALTITUDE_EXPONENT = 0.1902949


def accel_to_g(raw: float) -> float:
    return raw / ACCEL_LSB_PER_G


def gyro_to_dps(raw: float) -> float:
    return raw / GYRO_LSB_PER_DPS


def pitch_roll_deg(ax: int, ay: int, az: int) -> tuple[float, float]:
    """Ivmeolcer vektorunden pitch ve roll, derece cinsinden.

    Olcek sadelestigi icin LSB katsayisi sonucu etkilemez.
    Uc eksen de sifirsa (sensor yok) 0, 0 doner; istisna atilmaz.
    """
    roll = math.degrees(math.atan2(ay, az))
    pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))
    return pitch, roll


def heading_deg(raw_decideg: int) -> float:
    """Firmware pusula acisini deci-derece olarak yolluyor."""
    return (raw_decideg / 10.0) % 360.0


def relative_altitude_m(pressure_pa: int, reference_pa: int) -> float:
    """Referans basinca gore irtifa. Gecersiz girdide 0.0."""
    if pressure_pa <= 0 or reference_pa <= 0:
        return 0.0
    ratio = pressure_pa / reference_pa
    return _ALTITUDE_COEFFICIENT * (1.0 - ratio**_ALTITUDE_EXPONENT)
