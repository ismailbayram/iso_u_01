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
GRIP_CHAIN_LEFT = (
    (30.0, 14.0, -22.0, 16.0),
    (20.0, 3.0, -24.0, 14.0),
    (8.0, -8.0, -26.0, 12.0),
    (-5.0, -17.0, -28.0, 10.0),
    (-17.0, -25.0, -30.0, 8.0),
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


def antenna_channel():
    """The void the old shell left for the antenna and the USB cable."""
    old = datum.to_manifold(datum.load_old(datum.OLD_DIR / "kumanda_alt.stl"))
    return (box(*datum.CHANNEL_REGION) - old) + box(*datum.CHANNEL_EXTENSION)


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

    shell -= antenna_channel()

    for x, y in datum.BOARD_POSTS:
        shell -= cyl(datum.POST_PILOT_D, datum.POST_PILOT_DEPTH + 1.0, x, y,
                     datum.BOARD_SEAT_Z - datum.POST_PILOT_DEPTH)
    for x, y in LID_SCREWS:
        shell -= cyl(LID_SCREW_PILOT_D, LID_SCREW_PILOT_DEPTH + 1.0, x, y,
                     datum.WALL_TOP_Z - LID_SCREW_PILOT_DEPTH)
    for x, y in GRIP_SCREWS["left"] + GRIP_SCREWS["right"]:
        shell -= cyl(GRIP_PILOT_D, GRIP_PILOT_DEPTH + 1.0, x, y,
                     datum.SHELL_BOTTOM_Z - 1.0)

    shell -= geom.text_solid(SHELL_TEXT, SHELL_TEXT_SIZE,
                             SHELL_TEXT_POS[0], SHELL_TEXT_POS[1],
                             datum.SHELL_BOTTOM_Z - 0.01,
                             datum.SHELL_BOTTOM_Z + TEXT_DEPTH)
    return shell


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
    collar = _centred_box(datum.SCREEN_CENTER, COLLAR_OUTER,
                          datum.WALL_TOP_Z, datum.LID_PLATE_BOTTOM_Z + 0.5)
    lid += collar
    lid -= _centred_box(datum.SCREEN_CENTER, SCREEN_NEST,
                        datum.WALL_TOP_Z - 1.0, SCREEN_NEST_TOP_Z)
    lid -= _centred_box(datum.SCREEN_CENTER, SCREEN_WINDOW,
                        SCREEN_NEST_TOP_Z, datum.LID_TOP_Z + 1.0)
    lid -= _centred_box(datum.SCREEN_CENTER, SCREEN_PANEL,
                        datum.LID_TOP_Z - SCREEN_PANEL_DEPTH, datum.LID_TOP_Z + 1.0)

    for x, y in STICK_NEW:
        lid -= cyl(STICK_BORE_D, 8.0, x, y, datum.LID_PLATE_BOTTOM_Z - 2.0)
        lid -= geom.spherical_dish(x, y, datum.LID_TOP_Z, DISH_D, DISH_DEPTH)

    for x, y in LID_SCREWS:
        lid -= cyl(LID_SCREW_CLEAR_D, 6.0, x, y, datum.LID_PLATE_BOTTOM_Z - 1.0)
        lid -= cyl(LID_SCREW_HEAD_D, LID_SCREW_HEAD_DEPTH + 1.0, x, y,
                   datum.LID_TOP_Z - LID_SCREW_HEAD_DEPTH)

    lid -= antenna_channel()
    lid -= box(*datum.CABLE_SLOT)
    lid -= geom.text_solid(LID_TEXT, LID_TEXT_SIZE, LID_TEXT_POS[0], LID_TEXT_POS[1],
                           datum.LID_TOP_Z - TEXT_DEPTH, datum.LID_TOP_Z + 0.01)
    return lid


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
