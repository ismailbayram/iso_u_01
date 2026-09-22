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
