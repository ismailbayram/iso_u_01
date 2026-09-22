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


import controller_geom as geom


def test_outer_skin_matches_the_specified_envelope():
    skin = geom.outer_skin()
    low_x, low_y, low_z, high_x, high_y, high_z = skin.bounding_box()
    assert low_x == pytest.approx(geom.OUTER_X[0], abs=0.02)
    assert high_x == pytest.approx(geom.OUTER_X[1], abs=0.02)
    assert low_y == pytest.approx(geom.OUTER_Y[0], abs=0.02)
    assert high_y == pytest.approx(geom.OUTER_Y[1], abs=0.02)
    assert low_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.02)
    assert high_z == pytest.approx(datum.LID_TOP_Z, abs=0.02)


def test_outer_skin_inset_shrinks_by_exactly_the_inset():
    inset = 2.2
    outer = geom.outer_skin().bounding_box()
    inner = geom.outer_skin(inset).bounding_box()
    for axis in range(3):
        assert inner[axis] == pytest.approx(outer[axis] + inset, abs=0.02)
        assert inner[axis + 3] == pytest.approx(outer[axis + 3] - inset, abs=0.02)


def test_outer_skin_side_walls_carry_the_draft():
    """The side wall leans in by DRAFT_DEG between the two rounded edges.

    Sampled clear of the R3 edge rounding, which pulls the section in near
    the top and bottom faces and would swamp the angle being measured.
    """
    skin = geom.outer_skin()
    high_z = datum.LID_TOP_Z - geom.EDGE_R - 1.0
    low_z = datum.SHELL_BOTTOM_Z + geom.EDGE_R + 1.0
    expected = math.tan(math.radians(geom.DRAFT_DEG)) * (high_z - low_z)
    top = geom.section_width(skin, high_z)
    bottom = geom.section_width(skin, low_z)
    assert (top - bottom) / 2 == pytest.approx(expected, abs=0.05)


def test_spherical_dish_has_the_asked_for_depth_and_diameter():
    dish = geom.spherical_dish(0.0, 0.0, 0.0, 46.0, 1.2)
    low_x, low_y, low_z, high_x, high_y, high_z = dish.bounding_box()
    assert high_x - low_x == pytest.approx(46.0, abs=0.4)
    assert low_z == pytest.approx(-1.2, abs=0.02)


def test_text_solid_is_not_empty_and_lands_where_asked():
    solid = geom.text_solid("ISO U1", 10.0, 68.0, 20.0, 0.0, 0.6)
    low_x, low_y, low_z, high_x, high_y, high_z = solid.bounding_box()
    assert solid.volume() > 10.0
    assert (low_x + high_x) / 2 == pytest.approx(68.0, abs=0.5)
    assert low_z == pytest.approx(0.0, abs=0.01)
    assert high_z == pytest.approx(0.6, abs=0.01)
