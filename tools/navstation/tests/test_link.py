from navstation import link


VALID_T = "$T,12345,11850,2431,3012,1,-2,64,3,-4,5,1234,101325,2380,17,42"
VALID_S = "$S,2048,120,2050,3900"


def test_parses_telemetry_line():
    result = link.parse_line(VALID_T)
    assert isinstance(result, link.Telemetry)
    assert result.t_ms == 12345
    assert result.voltage_mv == 11850
    assert result.batt_temp_centi == 2431
    assert result.esc_temp_centi == 3012
    assert (result.ax, result.ay, result.az) == (1, -2, 64)
    assert (result.gx, result.gy, result.gz) == (3, -4, 5)
    assert result.heading_decideg == 1234
    assert result.pressure_pa == 101325
    assert result.baro_temp_centi == 2380
    assert result.flags == 17
    assert result.rx_count == 42


def test_parses_stick_line():
    result = link.parse_line(VALID_S)
    assert isinstance(result, link.Sticks)
    assert (result.lx, result.ly, result.rx, result.ry) == (2048, 120, 2050, 3900)


def test_tolerates_trailing_whitespace_and_crlf():
    assert isinstance(link.parse_line(VALID_T + "\r\n"), link.Telemetry)


def test_ignores_human_readable_lines():
    assert link.parse_line("[TEL] V=11.85 Tbatt=NA") is None
    assert link.parse_line("[E22] ayar zaten uygun") is None
    assert link.parse_line("") is None


def test_ignores_unknown_record_type():
    assert link.parse_line("$X,1,2,3") is None


def test_returns_none_on_wrong_field_count():
    assert link.parse_line("$T,1,2,3") is None
    assert link.parse_line(VALID_T + ",99") is None


def test_returns_none_on_non_numeric_field():
    broken = VALID_T.replace("11850", "abc")
    assert link.parse_line(broken) is None


def test_never_raises_on_garbage():
    for garbage in ["$T,", "$", "$S,,,,", "$T," + "," * 100, "\x00\xff"]:
        assert link.parse_line(garbage) is None


def test_flag_helpers_match_firmware_bits():
    assert link.FLAG_ACCEL == 0x01
    assert link.FLAG_GYRO == 0x02
    assert link.FLAG_MAG == 0x04
    assert link.FLAG_BARO == 0x08
    assert link.FLAG_CALIBRATED == 0x10
    assert link.FLAG_ARMED == 0x20


def test_temp_absent_sentinel_matches_int16_min():
    assert link.TEMP_ABSENT == -32768


def test_returns_none_for_non_string_input():
    assert link.parse_line(b"$T,1,2,3") is None
    assert link.parse_line(None) is None
    assert link.parse_line(12345) is None
    assert link.parse_line(["$T", "1"]) is None
