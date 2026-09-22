"""Geometry regression tests for the ISO U1 controller case.

Run from the repository root:  pytest mechanical/controller -q
"""

import math
from pathlib import Path

import numpy as np
import pytest

import controller_datum as datum

OLD_SHELL = datum.OLD_DIR / "kumanda_alt.stl"
OLD_LID = datum.OLD_DIR / "kumanda_ust.stl"


def test_old_shell_posts_match_constants():
    measured = datum.measure_old_shell(OLD_SHELL)["posts"]
    expected = sorted(datum.BOARD_POSTS)
    assert len(measured) == 4
    for got, want in zip(measured, expected):
        assert got[0] == pytest.approx(want[0], abs=0.10)
        assert got[1] == pytest.approx(want[1], abs=0.10)


def test_old_lid_sticks_match_constants():
    measured = datum.measure_old_lid(OLD_LID)["sticks"]
    expected = sorted(datum.STICK_OLD)
    assert len(measured) == 2
    for got, want in zip(measured, expected):
        assert got[0] == pytest.approx(want[0], abs=0.10)
        assert got[1] == pytest.approx(want[1], abs=0.10)


def test_old_lid_screen_matches_constants():
    measured = datum.measure_old_lid(OLD_LID)
    assert measured["screen_bore"][0] == pytest.approx(datum.SCREEN_CENTER[0], abs=0.10)
    assert measured["screen_bore"][1] == pytest.approx(datum.SCREEN_CENTER[1], abs=0.10)
    assert measured["screen_shoulder"][0] == pytest.approx(datum.SCREEN_CENTER[0], abs=0.10)
    assert measured["screen_shoulder"][1] == pytest.approx(datum.SCREEN_CENTER[1], abs=0.10)


def test_old_shell_sits_in_the_d_frame():
    mesh = datum.load_old(OLD_SHELL)
    assert mesh.bounds[0][0] == pytest.approx(0.0, abs=0.01)
    assert mesh.bounds[0][1] == pytest.approx(0.0, abs=0.01)
    assert mesh.bounds[1][2] == pytest.approx(18.0, abs=0.01)
