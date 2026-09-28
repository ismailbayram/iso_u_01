from navstation import controls


def test_center_stick_gives_center_servo():
    assert controls.servo_deg(2048) == 90


def test_inside_aircraft_deadband_snaps_to_center():
    # STM32 44 birime kadar sapmayi yok sayar; trim bu esigi asmali.
    assert controls.servo_deg(2048 + 44) == 90
    assert controls.servo_deg(2048 - 44) == 90


def test_outside_deadband_moves_servo():
    # Tamsayi map() keserek yuvarlar: +100 ve -100 simetrik degil.
    assert controls.servo_deg(2048 + 100) == 92
    assert controls.servo_deg(2048 - 100) == 87


def test_full_travel_hits_limits():
    assert controls.servo_deg(0) == 45
    assert controls.servo_deg(4095) == 135


def test_out_of_range_input_is_clamped():
    assert controls.servo_deg(-50) == 45
    assert controls.servo_deg(5000) == 135


def test_center_offset_is_signed():
    assert controls.center_offset(2060) == 12
    assert controls.center_offset(2000) == -48


def test_throttle_range_matches_esc_limits():
    assert controls.throttle_us(0) == 1100
    assert controls.throttle_us(4095) == 1940
