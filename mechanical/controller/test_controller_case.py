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


import controller_case as case


@pytest.fixture(scope="module")
def shell():
    return case.build_shell()


def test_shell_is_a_single_watertight_body(shell):
    mesh = geom.to_trimesh(shell)
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_shell_occupies_the_specified_envelope(shell):
    """The shell spans floor to wall top and stays inside the outer skin.

    It is narrower than the 150 mm envelope: the widest section of the part
    is the top of the lid, and the draft pulls everything below it in. The
    shell's own widest point is the bottom of the skirt rebate.
    """
    low_x, low_y, low_z, high_x, high_y, high_z = shell.bounding_box()
    assert low_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.05)
    assert high_z == pytest.approx(datum.WALL_TOP_Z, abs=0.05)
    assert (shell - geom.outer_skin()).volume() == pytest.approx(0.0, abs=1.0)

    widest = geom.section_width(geom.outer_skin(), datum.LID_SKIRT_BOTTOM_Z)
    assert high_x - low_x == pytest.approx(widest, abs=0.05)


def test_shell_leaves_room_for_the_board(shell):
    """A 133 mm slab at the seating plane must not touch the shell."""
    centre_x = sum(p[0] for p in datum.BOARD_POSTS) / 4
    centre_y = sum(p[1] for p in datum.BOARD_POSTS) / 4
    board = geom.box(centre_x - 66.5, centre_x + 66.5,
                     centre_y - 66.5, centre_y + 66.5,
                     datum.BOARD_SEAT_Z, datum.BOARD_SEAT_Z + datum.BOARD_T)
    assert (board ^ shell).volume() == pytest.approx(0.0, abs=1.0)


def test_shell_posts_reach_the_seating_plane(shell):
    mesh = geom.to_trimesh(shell)
    boxes = datum.section_boxes(mesh, datum.BOARD_SEAT_Z - 0.5)
    posts = [((low + high) / 2).round(2) for low, high in boxes
             if abs((high - low)[0] - datum.POST_OD) < 0.6
             and abs((high - low)[1] - datum.POST_OD) < 0.6]
    assert len(posts) == 4
    for got in sorted(tuple(p) for p in posts):
        assert min(math.dist(got, want) for want in datum.BOARD_POSTS) < 0.2


def test_shell_keeps_the_antenna_channel_open(shell):
    """Everything the old shell left open in the channel region stays open."""
    old = datum.to_manifold(datum.load_old(datum.OLD_DIR / "kumanda_alt.stl"))
    opening = geom.box(*datum.CHANNEL_REGION) - old
    assert (opening ^ shell).volume() == pytest.approx(0.0, abs=1.0)


def test_shell_has_four_lid_screw_pilots(shell):
    mesh = geom.to_trimesh(shell)
    boxes = datum.section_boxes(mesh, datum.WALL_TOP_Z - 2.0)
    pilots = [((low + high) / 2).round(2) for low, high in boxes
              if abs((high - low)[0] - case.LID_SCREW_PILOT_D) < 0.4]
    assert len(pilots) == 4
    for got in sorted(tuple(p) for p in pilots):
        assert min(math.dist(got, want) for want in case.LID_SCREWS) < 0.2


@pytest.fixture(scope="module")
def lid():
    return case.build_lid()


def test_lid_is_a_single_watertight_body(lid):
    mesh = geom.to_trimesh(lid)
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_lid_spans_the_skirt_and_the_plate(lid):
    _, _, low_z, _, _, high_z = lid.bounding_box()
    assert low_z == pytest.approx(datum.LID_SKIRT_BOTTOM_Z, abs=0.05)
    assert high_z == pytest.approx(datum.LID_TOP_Z, abs=0.05)


def test_lid_skirt_clears_the_shell(shell, lid):
    assert (shell ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_new_stick_bores_swallow_the_old_ones(lid):
    """Both old bores must fall inside the new ones, or a stick will bind."""
    for old_x, old_y in datum.STICK_OLD:
        old_bore = geom.cyl(datum.STICK_OLD_D, 6.0, old_x, old_y,
                            datum.LID_PLATE_BOTTOM_Z - 1.0)
        assert (old_bore ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_stick_bores_share_one_y_and_keep_the_measured_x(lid):
    assert case.STICK_NEW[0][1] == case.STICK_NEW[1][1]
    assert case.STICK_NEW[0][0] == pytest.approx(datum.STICK_OLD[0][0], abs=0.01)
    assert case.STICK_NEW[1][0] == pytest.approx(datum.STICK_OLD[1][0], abs=0.01)


def test_screen_module_can_rise_into_its_nest(lid):
    """A 38 x 12 x 1.6 board ending at the seat plane must not be obstructed."""
    module = geom.box(datum.SCREEN_CENTER[0] - 19.0, datum.SCREEN_CENTER[0] + 19.0,
                      datum.SCREEN_CENTER[1] - 6.0, datum.SCREEN_CENTER[1] + 6.0,
                      datum.SCREEN_SEAT_Z - datum.BOARD_T, datum.SCREEN_SEAT_Z)
    assert (module ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_screen_window_is_smaller_than_the_module(lid):
    """The lip is what stops the module passing up through the window.

    Sampled below the panel recess; the top 1 mm of the plate is opened out
    to 46 x 20 and would read as the window otherwise.
    """
    assert case.SCREEN_WINDOW[0] < 38.0
    assert case.SCREEN_WINDOW[1] < 12.0
    mesh = geom.to_trimesh(lid)
    z = datum.LID_TOP_Z - case.SCREEN_PANEL_DEPTH - 0.5
    windows = [high - low for low, high in datum.section_boxes(mesh, z)
               if abs((high - low)[0] - case.SCREEN_WINDOW[0]) < 0.4]
    assert len(windows) == 1
    assert windows[0][1] == pytest.approx(case.SCREEN_WINDOW[1], abs=0.05)


def test_screen_nest_is_a_step_between_the_collar_and_the_window(lid):
    """Module rises into the nest, stops on the shoulder at the seat plane."""
    mesh = geom.to_trimesh(lid)
    below = {tuple((high - low).round(2))
             for low, high in datum.section_boxes(mesh, datum.SCREEN_SEAT_Z - 0.5)}
    above = {tuple((high - low).round(2))
             for low, high in datum.section_boxes(mesh, datum.SCREEN_SEAT_Z + 1.0)}
    assert case.SCREEN_NEST in below
    assert case.COLLAR_OUTER in below
    assert case.SCREEN_WINDOW in above


def test_lid_top_carries_the_screen_panel_recess(lid):
    mesh = geom.to_trimesh(lid)
    sizes = {tuple((high - low).round(2))
             for low, high in datum.section_boxes(mesh, datum.LID_TOP_Z - 0.5)}
    assert case.SCREEN_PANEL in sizes


def test_lid_keeps_the_antenna_channel_open(lid):
    old = datum.to_manifold(datum.load_old(datum.OLD_DIR / "kumanda_alt.stl"))
    opening = geom.box(*datum.CHANNEL_REGION) - old
    assert (opening ^ lid).volume() == pytest.approx(0.0, abs=1.0)
