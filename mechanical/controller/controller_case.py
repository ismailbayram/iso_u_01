"""The ISO U1 transmitter case: shell, lid, two grips and the screen shim.

The perfboard inside is hand-built and already drilled, so every feature the
board dictates comes from `controller_datum` and is never recomputed here.
What this module is free to shape is the outer form: a drafted, rounded
shell, thumb dishes around the sticks, debossed lettering, and two bolt-on
grips.

Coordinates: the D frame described in `controller_datum`.

Requirements: numpy, scipy, trimesh, manifold3d, matplotlib, Pillow
Usage:        python controller_case.py [--check] [--out DIR]
"""

import argparse
import math
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

import controller_datum as datum
import controller_geom as geom
from controller_geom import box, cyl

# --- lid interface --------------------------------------------------------
SKIRT_T = 2.0
SKIRT_GAP = 0.2

LID_SCREWS = ((-2.5, 30.0), (-2.5, 105.0), (138.5, 30.0), (138.5, 105.0))
LID_SCREW_BOSS_D = 6.0
LID_SCREW_PILOT_D = 2.5
LID_SCREW_PILOT_DEPTH = 12.0

# --- grip interface -------------------------------------------------------
# Kept clear of the rounded bottom edge: the flat underside only starts at
# y = 2.49, so a 10 mm pad centred below y = 7.5 would hang off the part.
GRIP_SCREWS = {
    "left": ((12.0, 9.0), (40.0, 16.0)),
    "right": ((124.0, 9.0), (96.0, 16.0)),
}
GRIP_PAD_D = 10.0
GRIP_PAD_TOP_Z = -12.0
GRIP_PILOT_D = 2.5
GRIP_PILOT_DEPTH = 7.0

# --- lettering ------------------------------------------------------------
TEXT_DEPTH = 0.6
SHELL_TEXT = "İstikbal Göklerdedir"
SHELL_TEXT_SIZE = 10.0
SHELL_TEXT_POS = (68.0, 66.0)

# --- lid ------------------------------------------------------------------
STICK_NEW = ((datum.STICK_OLD[0][0], 51.00), (datum.STICK_OLD[1][0], 51.00))
STICK_BORE_D = 33.0
DISH_D = 46.0
DISH_DEPTH = 1.2

COLLAR_OUTER = (44.2, 18.2)
SCREEN_NEST = (39.2, 13.2)
SCREEN_NEST_TOP_Z = datum.SCREEN_SEAT_Z
SCREEN_WINDOW = (36.5, 10.5)
SCREEN_PANEL = (46.0, 20.0)
SCREEN_PANEL_DEPTH = 1.0

LID_SCREW_CLEAR_D = 3.4
LID_SCREW_HEAD_D = 6.0
LID_SCREW_HEAD_DEPTH = 0.8  # the plate is only 2.0 mm thick

LID_TEXT = "ISO U1"
LID_TEXT_SIZE = 10.0
LID_TEXT_POS = (68.0, 20.0)

# --- grips ----------------------------------------------------------------
# (x, y, z, radius); hulled together, then cut off at the shell's underside.
# Runs down and toward the user rather than out to the side, so the grips
# stay inside the body's silhouette instead of reading as wings.
GRIP_CHAIN_LEFT = (
    (28.0, 14.0, -18.0, 20.0),
    (22.0, 4.0, -20.0, 18.0),
    (16.0, -6.0, -22.0, 16.0),
    (10.0, -15.0, -24.0, 14.0),
    (3.0, -24.0, -27.0, 11.0),
)
GRIP_MIRROR_X = 136.0
GRIP_WALL = 2.5
GRIP_SOLID_ROOT_Z = -30.0
GRIP_CLEAR_D = 3.4
GRIP_HEAD_D = 6.5
GRIP_HEAD_Z = -30.0

# --- screen shim ----------------------------------------------------------
SHIM_OUTER = (38.4, 12.4)
SHIM_RIM = 3.0
SHIM_LIP_H = 1.0
SHIM_LIP_T = 0.8
SHIM_NOMINAL_H = datum.SCREEN_SEAT_Z - datum.BOARD_T - (
    datum.BOARD_SEAT_Z + datum.BOARD_T)
SHIM_HEIGHTS = (SHIM_NOMINAL_H - 0.5, SHIM_NOMINAL_H, SHIM_NOMINAL_H + 0.5)


def shell_outer_surface():
    """The shell's outer skin: full size up to the skirt, rebated above it."""
    below = box(-40.0, 180.0, -40.0, 180.0,
                datum.SHELL_BOTTOM_Z, datum.LID_SKIRT_BOTTOM_Z)
    rebate = box(-40.0, 180.0, -40.0, 180.0,
                 datum.LID_SKIRT_BOTTOM_Z, datum.WALL_TOP_Z)
    return (geom.outer_skin() ^ below) + (geom.outer_skin(SKIRT_T + SKIRT_GAP) ^ rebate)


WALL_CUT_Y = (130.0, 145.0)  # spans the top wall from inside the cavity to clear


def antenna_hole():
    """The bore the SMA's antenna passes through, along Y in the top wall."""
    x, z = datum.ANTENNA_CENTER
    length = WALL_CUT_Y[1] - WALL_CUT_Y[0]
    return (mf.Manifold.cylinder(length, datum.ANTENNA_D / 2, datum.ANTENNA_D / 2,
                                 geom.SEGMENTS)
            .rotate([-90.0, 0.0, 0.0])
            .translate([x, WALL_CUT_Y[0], z]))


def usb_slot():
    """A rectangular window in the top wall for the micro-USB cable.

    The old case ran the cable out through the same sprawling channel as
    the antenna; this is the part of it that still has to be there, cut to
    the connector's own footprint.
    """
    return box(datum.USB_SLOT_X[0], datum.USB_SLOT_X[1],
               WALL_CUT_Y[0], WALL_CUT_Y[1],
               datum.USB_SLOT_Z[0], datum.USB_SLOT_Z[1])


def build_shell():
    outer = shell_outer_surface()
    shell = outer - geom.cavity_solid(datum.FLOOR_TOP_Z, datum.LID_TOP_Z + 10.0)

    for x, y in datum.BOARD_POSTS:
        shell += cyl(datum.POST_OD, datum.BOARD_SEAT_Z - datum.FLOOR_TOP_Z,
                     x, y, datum.FLOOR_TOP_Z)

    towers = mf.Manifold()
    for x, y in LID_SCREWS:
        towers += cyl(LID_SCREW_BOSS_D, datum.WALL_TOP_Z - datum.FLOOR_TOP_Z,
                      x, y, datum.FLOOR_TOP_Z)
    shell += towers ^ outer

    pads = mf.Manifold()
    for x, y in GRIP_SCREWS["left"] + GRIP_SCREWS["right"]:
        pads += cyl(GRIP_PAD_D, GRIP_PAD_TOP_Z - datum.SHELL_BOTTOM_Z,
                    x, y, datum.SHELL_BOTTOM_Z)
    shell += pads ^ outer

    cuts = antenna_hole() + usb_slot()
    for x, y in datum.BOARD_POSTS:
        cuts += cyl(datum.POST_PILOT_D, datum.POST_PILOT_DEPTH + 1.0, x, y,
                    datum.BOARD_SEAT_Z - datum.POST_PILOT_DEPTH)
    for x, y in LID_SCREWS:
        cuts += cyl(LID_SCREW_PILOT_D, LID_SCREW_PILOT_DEPTH + 1.0, x, y,
                    datum.WALL_TOP_Z - LID_SCREW_PILOT_DEPTH)
    for x, y in GRIP_SCREWS["left"] + GRIP_SCREWS["right"]:
        cuts += cyl(GRIP_PILOT_D, GRIP_PILOT_DEPTH + 1.0, x, y,
                    datum.SHELL_BOTTOM_Z - 1.0)
    cuts += geom.text_solid(SHELL_TEXT, SHELL_TEXT_SIZE,
                            SHELL_TEXT_POS[0], SHELL_TEXT_POS[1],
                            datum.SHELL_BOTTOM_Z - 0.01,
                            datum.SHELL_BOTTOM_Z + TEXT_DEPTH)

    # See build_lid: one union, not a chain, or manifold3d's batched
    # evaluation leaves stray coplanar faces across the openings.
    return shell - cuts


def _centred_box(centre, size, z0, z1):
    half_x, half_y = size[0] / 2, size[1] / 2
    return box(centre[0] - half_x, centre[0] + half_x,
               centre[1] - half_y, centre[1] + half_y, z0, z1)


def build_lid():
    band = box(-40.0, 180.0, -40.0, 180.0, datum.LID_SKIRT_BOTTOM_Z, datum.LID_TOP_Z)
    hollow = box(-40.0, 180.0, -40.0, 180.0,
                 datum.LID_SKIRT_BOTTOM_Z - 1.0, datum.LID_PLATE_BOTTOM_Z)
    lid = (geom.outer_skin() ^ band) - (geom.outer_skin(SKIRT_T) ^ hollow)

    # Overlaps the plate by 0.5 mm; a coplanar union would be degenerate.
    lid += _centred_box(datum.SCREEN_CENTER, COLLAR_OUTER,
                        datum.WALL_TOP_Z, datum.LID_PLATE_BOTTOM_Z + 0.5)

    cuts = _centred_box(datum.SCREEN_CENTER, SCREEN_NEST,
                        datum.WALL_TOP_Z - 1.0, SCREEN_NEST_TOP_Z)
    cuts += _centred_box(datum.SCREEN_CENTER, SCREEN_WINDOW,
                         SCREEN_NEST_TOP_Z, datum.LID_TOP_Z + 1.0)
    cuts += _centred_box(datum.SCREEN_CENTER, SCREEN_PANEL,
                         datum.LID_TOP_Z - SCREEN_PANEL_DEPTH, datum.LID_TOP_Z + 1.0)

    for x, y in STICK_NEW:
        cuts += cyl(STICK_BORE_D, 8.0, x, y, datum.LID_PLATE_BOTTOM_Z - 2.0)
        cuts += geom.spherical_dish(x, y, datum.LID_TOP_Z, DISH_D, DISH_DEPTH)

    for x, y in LID_SCREWS:
        cuts += cyl(LID_SCREW_CLEAR_D, 6.0, x, y, datum.LID_PLATE_BOTTOM_Z - 1.0)
        cuts += cyl(LID_SCREW_HEAD_D, LID_SCREW_HEAD_DEPTH + 1.0, x, y,
                    datum.LID_TOP_Z - LID_SCREW_HEAD_DEPTH)

    cuts += usb_slot()
    cuts += geom.text_solid(LID_TEXT, LID_TEXT_SIZE, LID_TEXT_POS[0], LID_TEXT_POS[1],
                            datum.LID_TOP_Z - TEXT_DEPTH, datum.LID_TOP_Z + 0.01)

    # One subtraction, not a chain of them. manifold3d evaluates lazily, and
    # a long chain of differences batches into a single pass that leaves
    # stray coplanar faces behind — a 1010 mm^2 triangle roofed over the
    # right stick bore. Unioning the negatives first avoids the whole class.
    return lid - cuts


def grip_chain(side):
    if side == "left":
        return GRIP_CHAIN_LEFT
    return tuple((GRIP_MIRROR_X - x, y, z, r) for x, y, z, r in GRIP_CHAIN_LEFT)


def grip_envelope(side):
    """The grip's outer solid, before it is hollowed or drilled."""
    return geom.hull_of_spheres(grip_chain(side))


def build_grip(side):
    """One bolt-on grip, cut flat where it meets the shell's underside.

    The flat root is what makes it printable: stood on that face it is a
    dome that narrows as it rises, with nothing overhanging. Its first
    10 mm are solid so the screw seats have something to hold on to.
    """
    chain = grip_chain(side)
    outer = grip_envelope(side)
    inner = geom.hull_of_spheres(
        tuple((x, y, z, r - GRIP_WALL) for x, y, z, r in chain))
    below = box(-60.0, 200.0, -60.0, 200.0, -60.0, datum.SHELL_BOTTOM_Z)
    root = box(-60.0, 200.0, -60.0, 200.0, GRIP_SOLID_ROOT_Z, datum.SHELL_BOTTOM_Z)

    grip = ((outer - inner) + (outer ^ root)) ^ below

    for x, y in GRIP_SCREWS[side]:
        grip -= cyl(GRIP_CLEAR_D, datum.SHELL_BOTTOM_Z - GRIP_HEAD_Z + 1.0,
                    x, y, GRIP_HEAD_Z)
        grip -= cyl(GRIP_HEAD_D, 4.0, x, y, GRIP_HEAD_Z - 0.5)
    return grip


def build_shim(height):
    """A little table that holds the OLED module flat on the perfboard.

    Open along one long edge so the soldered pin header and its blobs pass
    through; the other three edges are what stop the module tipping. The old
    case supported only one end of it, which is why it sat crooked.
    """
    half_x, half_y = SHIM_OUTER[0] / 2, SHIM_OUTER[1] / 2
    shim = box(-half_x, half_x, -half_y, half_y, 0.0, height)
    shim -= box(-half_x + SHIM_RIM, half_x - SHIM_RIM,
                -half_y - 1.0, half_y - SHIM_RIM, -1.0, height + 1.0)

    lip = box(-half_x - SHIM_LIP_T, half_x + SHIM_LIP_T,
              -half_y, half_y + SHIM_LIP_T, height, height + SHIM_LIP_H)
    lip -= box(-half_x, half_x, -half_y - 1.0, half_y,
               height - 1.0, height + SHIM_LIP_H + 1.0)
    return shim + lip


def parts():
    """Every printable part, keyed by output file stem."""
    built = {
        "controller_shell": build_shell(),
        "controller_lid": build_lid(),
        "controller_grip_left": build_grip("left"),
        "controller_grip_right": build_grip("right"),
    }
    for height in SHIM_HEIGHTS:
        built["screen_shim_%03d" % round(height * 10)] = build_shim(height)
    return built


def check_against_old():
    """Compare the new parts with the old ones; returns a list of problems."""
    problems = []
    old_shell_path = datum.OLD_DIR / "kumanda_alt.stl"
    old_lid_path = datum.OLD_DIR / "kumanda_ust.stl"

    measured_posts = datum.measure_old_shell(old_shell_path)["posts"]
    for got, want in zip(measured_posts, sorted(datum.BOARD_POSTS)):
        if math.dist(got, want) > 0.10:
            problems.append("post %s drifted from %s" % (got, want))

    measured_lid = datum.measure_old_lid(old_lid_path)
    for got, want in zip(measured_lid["sticks"], sorted(datum.STICK_OLD)):
        if abs(got[0] - want[0]) > 0.30:
            problems.append("stick X %s drifted from %s" % (got, want))
    for key in ("screen_bore", "screen_shoulder"):
        got = measured_lid[key]
        if got is None or math.dist(got, datum.SCREEN_CENTER) > 0.30:
            problems.append("%s at %s, expected %s" % (key, got, datum.SCREEN_CENTER))

    measured_antenna = datum.measure_old_antenna(old_shell_path)
    if measured_antenna is None:
        problems.append("no antenna bore found in the old shell")
    else:
        drift = math.dist(measured_antenna["centre"], datum.ANTENNA_CENTER)
        if drift > 0.05:
            problems.append("antenna bore at %s, expected %s"
                            % (measured_antenna["centre"], datum.ANTENNA_CENTER))
        if abs(measured_antenna["diameter"] - datum.ANTENNA_D_OLD) > 0.05:
            problems.append("antenna bore is %.3f wide, expected %.3f"
                            % (measured_antenna["diameter"], datum.ANTENNA_D_OLD))

    shell = build_shell()
    lid = build_lid()

    rod_x, rod_z = datum.ANTENNA_CENTER
    rod = (mf.Manifold.cylinder(15.0, datum.ANTENNA_D / 2, datum.ANTENNA_D / 2,
                                geom.SEGMENTS)
           .rotate([-90.0, 0.0, 0.0])
           .translate([rod_x, WALL_CUT_Y[0], rod_z]))
    blocked = (rod ^ shell).volume()
    if blocked > 1.0:
        problems.append("shell blocks %.1f mm^3 of the antenna bore" % blocked)

    for name, solid in (("shell", shell), ("lid", lid)):
        plug = box(datum.USB_SLOT_X[0], datum.USB_SLOT_X[1],
                   WALL_CUT_Y[0], WALL_CUT_Y[1], 0.0, 8.0)
        blocked = (plug ^ solid).volume()
        if blocked > 1.0:
            problems.append("%s blocks %.1f mm^3 of the USB window"
                            % (name, blocked))

    lid_mesh = geom.to_trimesh(lid)
    origins = np.array([[x, y, 40.0] for x, y in STICK_NEW])
    directions = np.tile([0.0, 0.0, -1.0], (len(origins), 1))
    locations, ray_index, _ = lid_mesh.ray.intersects_location(origins, directions)
    for index, (x, y) in enumerate(STICK_NEW):
        hits = len(locations[ray_index == index])
        if hits:
            problems.append("lid roofs the stick bore at (%.2f, %.2f) with %d face(s)"
                            % (x, y, hits))

    for old_x, old_y in datum.STICK_OLD:
        old_bore = cyl(datum.STICK_OLD_D, 6.0, old_x, old_y,
                       datum.LID_PLATE_BOTTOM_Z - 1.0)
        blocked = (old_bore ^ lid).volume()
        if blocked > 1.0:
            problems.append("lid blocks %.1f mm^3 of the old stick bore at "
                            "(%.2f, %.2f)" % (blocked, old_x, old_y))
    return problems


PREVIEW_SIZE = (1400, 1000)
PREVIEW_VIEWS = (
    ("top", (0.0, 0.0)),
    ("front", (-75.0, 0.0)),
    ("corner", (-60.0, 35.0)),
)
PREVIEW_LIGHT = (-0.35, 0.45, 0.82)


def render_preview(built, path):
    """Three flat-shaded views, drawn back to front with Pillow."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", PREVIEW_SIZE, (28, 30, 34))
    draw = ImageDraw.Draw(image)
    scene = trimesh.util.concatenate([geom.to_trimesh(s) for s in built.values()])
    panel_w = PREVIEW_SIZE[0] // len(PREVIEW_VIEWS)

    for index, (_, (pitch, yaw)) in enumerate(PREVIEW_VIEWS):
        rotated = scene.copy()
        rotated.apply_transform(trimesh.transformations.euler_matrix(
            math.radians(pitch), math.radians(yaw), 0.0))
        vertices = rotated.vertices
        faces = rotated.faces
        span = max(np.ptp(vertices[:, 0]), np.ptp(vertices[:, 1]))
        scale = 0.8 * min(panel_w, PREVIEW_SIZE[1]) / span
        centre = vertices.mean(axis=0)
        screen = (vertices[:, :2] - centre[:2]) * [scale, -scale] + [
            panel_w * (index + 0.5), PREVIEW_SIZE[1] / 2]

        normals = rotated.face_normals
        depth = vertices[faces][:, :, 2].mean(axis=1)
        # Off-axis light; shading straight off the Z component would leave
        # every up-facing surface the same flat tone and hide the relief.
        light = np.array(PREVIEW_LIGHT) / np.linalg.norm(PREVIEW_LIGHT)
        shade = np.clip(0.18 + 0.82 * np.abs(normals @ light), 0.0, 1.0)
        for face_index in np.argsort(depth):
            level = int(40 + 190 * shade[face_index])
            draw.polygon([tuple(screen[v]) for v in faces[face_index]],
                         fill=(level, level, min(255, level + 12)))
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent,
                        help="directory the STLs and the preview are written to")
    parser.add_argument("--check", action="store_true",
                        help="verify the carried-over features against the old case")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    built = parts()
    for name, solid in built.items():
        mesh = geom.to_trimesh(solid)
        path = args.out / ("%s.stl" % name)
        mesh.export(path)
        print("wrote %s  volume=%.0f mm^3  watertight=%s  bodies=%d"
              % (path.name, solid.volume(), mesh.is_watertight, mesh.body_count))

    render_preview(built, args.out / "controller_case_preview.png")
    print("wrote controller_case_preview.png")

    if args.check:
        problems = check_against_old()
        for problem in problems:
            print("CHECK FAILED: %s" % problem)
        if problems:
            raise SystemExit(1)
        print("check passed: every carried-over feature is where it was")


if __name__ == "__main__":
    main()
