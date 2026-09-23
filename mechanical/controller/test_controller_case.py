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


def test_outer_skin_spans_the_full_height():
    skin = geom.outer_skin()
    _, low_y, low_z, _, high_y, high_z = skin.bounding_box()
    assert low_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.02)
    assert high_z == pytest.approx(datum.LID_TOP_Z, abs=0.02)
    assert low_y == pytest.approx(geom.OUTER_Y[0], abs=0.02)
    assert high_y == pytest.approx(geom.OUTER_Y[1], abs=0.02)


def test_outline_is_narrow_at_the_screen_end_and_opens_toward_the_user():
    """The flare is the whole point of the plan shape."""
    assert geom.flare_at(geom.OUTER_Y[1]) == pytest.approx(0.0, abs=0.01)
    assert geom.flare_at(geom.OUTER_Y[0]) == pytest.approx(geom.FLARE, abs=0.01)
    outline = np.array(geom.plan_outline())
    # Stops short of the very front, where the corner rounding turns the
    # outline back in again.
    ordered = []
    for y in (135.0, 100.0, 60.0, 20.0, 5.0):
        band = outline[np.abs(outline[:, 1] - y) < 4.0]
        ordered.append(band[:, 0].max() - band[:, 0].min())
    assert ordered == sorted(ordered), f"outline does not open out: {ordered}"
    assert ordered[-1] - ordered[0] > 15.0


def test_top_face_is_a_barrel_with_its_crest_on_the_centre_line():
    centre = (geom.CAVITY_X[0] + geom.CAVITY_X[1]) / 2
    assert geom.barrel_z(centre) == pytest.approx(datum.LID_TOP_Z, abs=0.01)
    mesh = geom.to_trimesh(geom.outer_skin())
    for x in (centre - 68.0, centre - 34.0, centre, centre + 34.0, centre + 68.0):
        origins = np.array([[x, 68.0, 60.0]])
        locations, _, _ = mesh.ray.intersects_location(
            origins, np.array([[0.0, 0.0, -1.0]]))
        assert locations[:, 2].max() == pytest.approx(geom.barrel_z(x), abs=0.05)


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
    mesh = geom.to_trimesh(geom.outer_skin())
    high_z = datum.LID_TOP_Z - geom.BARREL_DROP - geom.EDGE_R - 1.0
    low_z = datum.SHELL_BOTTOM_Z + geom.EDGE_R + 1.0
    expected = math.tan(math.radians(geom.DRAFT_DEG)) * (high_z - low_z)

    # Measured by ray at one Y, because the outline's width also changes
    # with Y and a section's vertices are sparse along the straight runs.
    def half_width(z):
        origin = np.array([[68.0, 68.0, z]])
        hits = []
        for direction in ([[1.0, 0.0, 0.0]], [[-1.0, 0.0, 0.0]]):
            locations, _, _ = mesh.ray.intersects_location(
                origin, np.array(direction))
            hits.append(np.abs(locations[:, 0] - 68.0).max())
        return sum(hits) / 2

    assert half_width(high_z) - half_width(low_z) == pytest.approx(expected, abs=0.15)


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


def test_old_antenna_bore_matches_constants():
    measured = datum.measure_old_antenna(OLD_SHELL)
    assert measured["centre"][0] == pytest.approx(datum.ANTENNA_CENTER[0], abs=0.02)
    assert measured["centre"][1] == pytest.approx(datum.ANTENNA_CENTER[1], abs=0.02)
    assert measured["diameter"] == pytest.approx(datum.ANTENNA_D_OLD, abs=0.02)


def test_shell_antenna_bore_goes_right_through_the_wall(shell):
    """A rod on the old bore's axis must pass clean through the top wall."""
    x, z = datum.ANTENNA_CENTER
    rod = (geom.cyl(datum.ANTENNA_D, 15.0, 0.0, 0.0, 0.0)
           .rotate([-90.0, 0.0, 0.0])
           .translate([x, 130.0, z]))
    assert (rod ^ shell).volume() == pytest.approx(0.0, abs=1.0)


def test_shell_wall_never_runs_out(shell):
    """Every wall stays at least MIN_WALL thick all the way to the floor.

    Wall thickness is quoted at the top of the lid, but the draft takes
    3.24 mm out of it by the floor. At 3 mm the front and back walls went
    negative below z = -15 and the pocket broke out through the outside of
    the shell, opening the underside along both edges.
    """
    mesh = geom.to_trimesh(geom.outer_skin())
    # From the floor's top face upward: below that the pocket does not
    # exist, and the sample would only be measuring the bottom edge roll.
    for z in (datum.FLOOR_TOP_Z, -15.0, -10.0, 0.0, 10.0, 15.0):
        boxes = datum.section_boxes(mesh, z)
        low = [min(box[0][axis] for box in boxes) for axis in (0, 1)]
        high = [max(box[1][axis] for box in boxes) for axis in (0, 1)]
        assert geom.CAVITY_X[0] - low[0] >= geom.MIN_WALL - 0.05, f"left wall at z={z}"
        assert high[0] - geom.CAVITY_X[1] >= geom.MIN_WALL - 0.05, f"right wall at z={z}"
        assert geom.CAVITY_Y[0] - low[1] >= geom.MIN_WALL - 0.05, f"front wall at z={z}"
        assert high[1] - geom.CAVITY_Y[1] >= geom.MIN_WALL - 0.05, f"back wall at z={z}"


def test_shell_floor_is_closed(shell):
    """Nothing in the pocket sees daylight downward.

    Rays fired down from just above the floor, on a grid covering the whole
    pocket, must each cross at least one surface. When the pocket broke out
    of the skin the front and back edges of the underside were simply open,
    and rays there left the part without touching anything. A single
    crossing is fine: over a grip pad the ray starts inside solid.
    """
    mesh = geom.to_trimesh(shell)
    xs = np.linspace(geom.CAVITY_X[0] + 1.0, geom.CAVITY_X[1] - 1.0, 21)
    ys = np.linspace(geom.CAVITY_Y[0] + 1.0, geom.CAVITY_Y[1] - 1.0, 21)
    grid = np.array([[x, y, datum.FLOOR_TOP_Z + 0.5] for x in xs for y in ys])
    directions = np.tile([0.0, 0.0, -1.0], (len(grid), 1))
    locations, ray_index, _ = mesh.ray.intersects_location(grid, directions)

    pilots = case.GRIP_SCREWS["left"] + case.GRIP_SCREWS["right"]
    open_points = []
    for index, point in enumerate(grid):
        if len(locations[ray_index == index]):
            continue
        # A grip screw's pilot goes right through the floor on purpose.
        if any(math.dist(point[:2], pilot) < case.GRIP_PILOT_D for pilot in pilots):
            continue
        open_points.append(point[:2].round(1).tolist())
    assert not open_points, f"floor open under {open_points[:8]}"


def test_shell_has_no_leftover_channel_pockets(shell):
    """The old sprawling channel is gone; only the bore and the USB window.

    Copying the old shell's negative carved a set of pockets into the floor
    that served nothing — a single bore is what the antenna actually needs.
    """
    mesh = geom.to_trimesh(shell)
    floor = geom.box(0.0, 136.0, 0.0, 136.0,
                     datum.SHELL_BOTTOM_Z, datum.FLOOR_TOP_Z)
    solid_floor = (floor ^ shell).volume()
    # grip pads add material, pilots remove a little; the floor is otherwise
    # a plain 2 mm slab over the cavity footprint.
    assert solid_floor > 0.93 * floor.volume()


def test_shell_usb_window_is_open(shell):
    """The cable has to reach the ESP32; the window is all that is left."""
    plug = geom.box(datum.USB_SLOT_X[0], datum.USB_SLOT_X[1],
                    130.0, 145.0, 0.0, 8.0)
    assert (plug ^ shell).volume() == pytest.approx(0.0, abs=1.0)


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
    # The screw pads stand proud of the top face; nothing else does.
    assert high_z == pytest.approx(datum.LID_TOP_Z + case.LID_PAD_PROUD, abs=0.05)


def test_every_screw_head_lands_on_a_flat_pad(lid):
    """All four pads read the same, and leave the shell its thickness.

    Two of the screws sit in the 8 mm edge roll, where the top face falls
    1.7 mm across one screw head. A recess there would have cut through the
    2 mm shell on its shallow side, so the heads sit on pads instead.
    """
    mesh = geom.to_trimesh(lid)
    for x, y in case.LID_SCREWS:
        on_pad = np.array([[x + case.LID_SCREW_HEAD_D / 2 + 1.0, y, 60.0]])
        locations, _, _ = mesh.ray.intersects_location(
            on_pad, np.array([[0.0, 0.0, -1.0]]))
        assert locations[:, 2].max() == pytest.approx(
            datum.LID_TOP_Z + case.LID_PAD_PROUD, abs=0.05), f"pad at ({x}, {y})"

        under_head = np.array([[x + case.LID_SCREW_CLEAR_D / 2 + 0.3, y, 60.0]])
        locations, _, _ = mesh.ray.intersects_location(
            under_head, np.array([[0.0, 0.0, -1.0]]))
        crossings = sorted(locations[:, 2], reverse=True)
        assert crossings[0] - crossings[-1] > 1.5, f"thin under head at ({x}, {y})"


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
    z = geom.barrel_z(datum.SCREEN_CENTER[0]) - case.SCREEN_PANEL_DEPTH - 0.5
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
    """Sampled under the recess's lowest corner, since the face is curved.

    The barrel drops about 1 mm across the recess's 46 mm, so there is no
    single height at which the whole footprint is both open and surrounded
    by material — except below the outboard end's own floor.
    """
    mesh = geom.to_trimesh(lid)
    centre_x, centre_y = datum.SCREEN_CENTER
    half_x = case.SCREEN_PANEL[0] / 2

    # Inside the recess but clear of the window, the surface must sit one
    # recess-depth below the barrel, at both ends as well as the middle.
    for x in (centre_x - half_x + 2.0, centre_x, centre_x + half_x - 2.0):
        origins = np.array([[x, centre_y + 8.0, 60.0]])
        locations, _, _ = mesh.ray.intersects_location(
            origins, np.array([[0.0, 0.0, -1.0]]))
        top = locations[:, 2].max()
        assert top == pytest.approx(geom.barrel_z(x) - case.SCREEN_PANEL_DEPTH,
                                    abs=0.08), f"recess depth wrong at x={x}"

    # And just outside it the surface is back up on the barrel.
    origins = np.array([[centre_x + half_x + 4.0, centre_y + 8.0, 60.0]])
    locations, _, _ = mesh.ray.intersects_location(
        origins, np.array([[0.0, 0.0, -1.0]]))
    assert locations[:, 2].max() == pytest.approx(
        geom.barrel_z(centre_x + half_x + 4.0), abs=0.08)


def test_lid_has_no_shallow_overhang_inside_its_outline(lid):
    """Nothing inside the part may face up at less than 45 degrees.

    The lid prints top face down, so a surface facing up in model space
    faces down on the plate. A thumb dish did this: 46 mm across and
    1.2 mm deep put its edge 6 degrees off horizontal, which prints as a
    near-flat overhang growing inward over nothing. Support does not save
    a surface at that angle, it only leaves its marks on it.

    The edge roll is exempt. Every rounded edge laid face down grows
    outward over air for its first few layers; that is what a fillet is.
    """
    mesh = geom.to_trimesh(lid)
    normal_z = mesh.face_normals[:, 2]
    shallow = (normal_z > math.cos(math.radians(45.0))) & (normal_z < 0.995)

    outline = np.array(geom.plan_outline())
    centres = mesh.triangles_center[shallow][:, :2]
    from scipy.spatial import cKDTree
    from_edge = cKDTree(outline).query(centres)[0]

    inside = mesh.area_faces[shallow][from_edge >= geom.EDGE_R + 1.0]
    assert inside.sum() < 1.0, "%.0f mm^2 of shallow overhang inside" % inside.sum()


def test_lid_shell_keeps_its_thickness_across_the_barrel(lid):
    """A flat plate would thin to nothing where the barrel falls away."""
    mesh = geom.to_trimesh(lid)
    for x in (10.0, 68.0, 126.0):
        origins = np.array([[x, 90.0, 60.0]])
        locations, _, _ = mesh.ray.intersects_location(
            origins, np.array([[0.0, 0.0, -1.0]]))
        crossings = sorted(locations[:, 2], reverse=True)
        assert len(crossings) >= 2, f"no shell at x={x}"
        assert crossings[0] - crossings[1] == pytest.approx(case.SKIRT_T, abs=0.15)


def test_lid_leaves_the_usb_window_open(lid):
    """The lid's skirt would otherwise close the top of the wall window."""
    plug = geom.box(datum.USB_SLOT_X[0], datum.USB_SLOT_X[1], 130.0, 145.0,
                    datum.LID_SKIRT_BOTTOM_Z, datum.LID_PLATE_BOTTOM_Z)
    assert (plug ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_lid_stick_bores_are_open_to_the_sky(lid):
    """A ray straight down each bore must hit nothing.

    Volume tests cannot see this: a stray zero-thickness face roofing the
    bore displaces nothing, but it still prints as a closed hole. One did,
    over the right stick, when the cuts were applied as a chain.
    """
    mesh = geom.to_trimesh(lid)
    origins = np.array([[x, y, 40.0] for x, y in case.STICK_NEW])
    directions = np.tile([0.0, 0.0, -1.0], (len(origins), 1))
    locations, ray_index, _ = mesh.ray.intersects_location(origins, directions)
    for index in range(len(origins)):
        assert len(locations[ray_index == index]) == 0


@pytest.fixture(scope="module")
def grips():
    return {side: case.build_grip(side) for side in ("left", "right")}


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_is_a_single_watertight_body(grips, side):
    mesh = geom.to_trimesh(grips[side])
    assert mesh.is_watertight
    assert mesh.body_count == 1


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_stays_below_the_shell(grips, side):
    _, _, low_z, _, _, high_z = grips[side].bounding_box()
    assert high_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.05)
    assert low_z == pytest.approx(-38.0, abs=0.5)


def test_grips_stay_inside_the_body_silhouette(grips):
    """Grips hang down and forward, not out to the side.

    Splayed sideways they read as wings rather than handles, and they widen
    the footprint on the bed for nothing. Half a millimetre of overhang past
    the lid's edge is the outward flare, and all of it.
    """
    low_x = grips["left"].bounding_box()[0]
    high_x = grips["right"].bounding_box()[3]
    outline = np.array(geom.plan_outline())
    assert low_x >= outline[:, 0].min()
    assert high_x <= outline[:, 0].max()


def test_grips_sit_under_the_body_front_corners(grips):
    """Each grip hangs off a front corner and curls under the front lip.

    Centred under the body instead, it reads as a foot rather than as the
    flared body carrying on downward.
    """
    outline = np.array(geom.plan_outline())
    front = outline[:, 1].min()
    for side, grip in grips.items():
        low_x, low_y, _, high_x, high_y, _ = grip.bounding_box()
        assert low_y < front, f"{side} grip stops short of the front lip"
        assert high_x - low_x > 40.0, f"{side} grip root is too narrow"


def test_grips_are_mirror_images(grips):
    left = grips["left"].bounding_box()
    right = grips["right"].bounding_box()
    assert left[0] + right[3] == pytest.approx(case.GRIP_MIRROR_X, abs=0.05)
    assert left[1] == pytest.approx(right[1], abs=0.05)


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_does_not_intersect_the_shell(shell, grips, side):
    assert (shell ^ grips[side]).volume() == pytest.approx(0.0, abs=1.0)


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_screw_seats_are_deep_enough_to_take_an_m3x14(side):
    """Each seat needs 10 mm of grip below the shell's underside.

    Measured against the grip's envelope, not the finished part: the head
    counterbore has already hollowed out the volume the screw head needs.
    """
    envelope = case.grip_envelope(side)
    for x, y in case.GRIP_SCREWS[side]:
        probe = geom.cyl(case.GRIP_HEAD_D, 0.5, x, y, case.GRIP_HEAD_Z)
        assert (probe - envelope).volume() == pytest.approx(0.0, abs=0.3)


@pytest.fixture(scope="module")
def seated_blank():
    """The blank dropped into the lid's screen opening from above."""
    return (case.build_screen_blank()
            .mirror([0.0, 0.0, 1.0])
            .translate([datum.SCREEN_CENTER[0], datum.SCREEN_CENTER[1],
                        datum.LID_TOP_Z]))


def test_screen_blank_is_a_single_watertight_body():
    mesh = geom.to_trimesh(case.build_screen_blank())
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_screen_blank_finishes_flush_with_the_lid(seated_blank):
    low_z, high_z = seated_blank.bounding_box()[2], seated_blank.bounding_box()[5]
    assert high_z == pytest.approx(datum.LID_TOP_Z, abs=0.01)
    assert low_z == pytest.approx(case.SCREEN_NEST_TOP_Z, abs=0.01)


def test_screen_blank_touches_the_lid_only_at_its_ribs(lid, seated_blank):
    """Everything but the ribs slides in; the ribs are the interference."""
    assert (seated_blank ^ lid).volume() > 0.5, "ribs are not gripping"

    proud = case.BLANK_RIB_PROUD
    case.BLANK_RIB_PROUD = 0.0
    try:
        plain = (case.build_screen_blank()
                 .mirror([0.0, 0.0, 1.0])
                 .translate([datum.SCREEN_CENTER[0], datum.SCREEN_CENTER[1],
                             datum.LID_TOP_Z]))
    finally:
        case.BLANK_RIB_PROUD = proud
    assert (plain ^ lid).volume() == pytest.approx(0.0, abs=0.1)


def test_screen_blank_cannot_fall_through_the_window():
    """The cap is what stops it dropping inside; the ribs stop it falling out."""
    assert case.SCREEN_PANEL[0] - 2 * case.BLANK_FIT > case.SCREEN_WINDOW[0]
    assert case.SCREEN_PANEL[1] - 2 * case.BLANK_FIT > case.SCREEN_WINDOW[1]


def test_shim_nominal_height_places_the_module_on_the_seat():
    """board top + shim + PCB must land exactly on the lid's shoulder."""
    board_top = datum.BOARD_SEAT_Z + datum.BOARD_T
    assert board_top + case.SHIM_NOMINAL_H + datum.BOARD_T == pytest.approx(
        datum.SCREEN_SEAT_Z, abs=0.01)


@pytest.mark.parametrize("height", [13.3, 13.8, 14.3])
def test_shim_is_a_single_watertight_body(height):
    mesh = geom.to_trimesh(case.build_shim(height))
    assert mesh.is_watertight
    assert mesh.body_count == 1


@pytest.mark.parametrize("height", [13.3, 13.8, 14.3])
def test_shim_top_face_sits_at_the_asked_for_height(height):
    shim = case.build_shim(height)
    _, _, low_z, _, _, high_z = shim.bounding_box()
    assert low_z == pytest.approx(0.0, abs=0.01)
    assert high_z == pytest.approx(height + case.SHIM_LIP_H, abs=0.01)


def test_shim_footprint_clears_the_module():
    shim = case.build_shim(case.SHIM_NOMINAL_H)
    low_x, low_y, _, high_x, high_y, _ = shim.bounding_box()
    assert high_x - low_x == pytest.approx(
        case.SHIM_OUTER[0] + 2 * case.SHIM_LIP_T, abs=0.05)
    assert high_y - low_y == pytest.approx(
        case.SHIM_OUTER[1] + case.SHIM_LIP_T, abs=0.05)


def test_shim_is_open_on_the_header_edge():
    """The pin row and its solder must pass straight through."""
    shim = case.build_shim(case.SHIM_NOMINAL_H)
    probe = geom.box(-case.SHIM_OUTER[0] / 2 + case.SHIM_RIM,
                     case.SHIM_OUTER[0] / 2 - case.SHIM_RIM,
                     -case.SHIM_OUTER[1] / 2 - case.SHIM_LIP_T - 1.0,
                     case.SHIM_OUTER[1] / 2 - case.SHIM_RIM,
                     0.0, case.SHIM_NOMINAL_H)
    assert (probe ^ shim).volume() == pytest.approx(0.0, abs=0.5)


def test_check_against_old_reports_no_problems():
    assert case.check_against_old() == []


def test_cli_writes_every_part(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "controller_case.py", "--out", str(tmp_path), "--check"],
        cwd=str(Path(case.__file__).parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    expected = {
        "controller_shell.stl",
        "controller_lid.stl",
        "controller_grip_left.stl",
        "controller_grip_right.stl",
        "screen_shim_133.stl",
        "screen_shim_138.stl",
        "screen_shim_143.stl",
        "controller_case_preview.png",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
