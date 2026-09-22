import math

import pytest

from navstation import attitude


def test_accel_scale_uses_64_lsb_per_g():
    assert attitude.accel_to_g(64) == pytest.approx(1.0)
    assert attitude.accel_to_g(-32) == pytest.approx(-0.5)


def test_gyro_scale_uses_itg3205_2000dps_range():
    assert attitude.gyro_to_dps(14.375) == pytest.approx(1.0)


def test_level_attitude_is_zero():
    pitch, roll = attitude.pitch_roll_deg(0, 0, 64)
    assert pitch == pytest.approx(0.0)
    assert roll == pytest.approx(0.0)


def test_roll_right_is_positive():
    # Saga yatinca y bileseni yercekimini gormeye baslar.
    pitch, roll = attitude.pitch_roll_deg(0, 64, 64)
    assert roll == pytest.approx(45.0)
    assert pitch == pytest.approx(0.0)


def test_pitch_up_is_positive():
    pitch, roll = attitude.pitch_roll_deg(-64, 0, 64)
    assert pitch == pytest.approx(45.0)
    assert roll == pytest.approx(0.0)


def test_all_zero_accel_does_not_raise():
    pitch, roll = attitude.pitch_roll_deg(0, 0, 0)
    assert math.isfinite(pitch)
    assert math.isfinite(roll)


def test_heading_converts_decidegrees():
    assert attitude.heading_deg(1234) == pytest.approx(123.4)


def test_heading_wraps_into_0_360():
    assert attitude.heading_deg(-100) == pytest.approx(350.0)
    assert attitude.heading_deg(3700) == pytest.approx(10.0)


def test_altitude_zero_at_reference():
    assert attitude.relative_altitude_m(101325, 101325) == pytest.approx(0.0)


def test_altitude_positive_when_pressure_drops():
    # ~12 Pa dusus deniz seviyesinde kabaca 1 metre.
    assert attitude.relative_altitude_m(101325 - 12, 101325) == pytest.approx(1.0, abs=0.2)


def test_altitude_returns_zero_for_invalid_input():
    assert attitude.relative_altitude_m(0, 101325) == 0.0
    assert attitude.relative_altitude_m(101325, 0) == 0.0
