"""Stacked battery + PCB tray for P39-MidFuseV3.

Two printed parts:

  sled  - glued into the fuselage. Rests on the two channel ledges like
          pcb_holder (same rails and glue lips) and slides along them until
          the CG is right. The battery drops through its open middle onto the
          floor of the 40 mm lower channel; a collar along its sides and rear
          keeps it from moving. The front (-Y, nose side) is left fully open
          because the main and balance leads leave the whole battery end face
          and bend right away. Four posts carry the deck: two with a heat-set
          insert, two with alignment pins.
  deck  - removable. Sits on the posts, held by two thumb screws, and
          presses the battery down through a ~3 mm EVA foam pad glued under
          it. The PCB screws onto its four standoffs (M2 self-tapping).

To swap the battery: remove the two thumb screws, lift the deck (PCB and
wiring stay on it), swap the battery, put the deck back, tighten.

Coordinates: X across the fuselage, Y along it, Z up. z = 0 is the top of the
fuselage ledges (z = -34.53 in the STL). Both parts print flat side down.

Requirements: numpy, trimesh, manifold3d
Usage:        python battery_tray.py [--check path/to/P39-MidFuseV3.stl]
"""

import argparse
import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pcb_holder"))
from pcb_holder import (  # noqa: E402
    CHANNEL_HALF_W,
    CLEARANCE,
    LEDGE_Z,
    LIP_H,
    LIP_T,
    PCB_L,
    PCB_W,
    PILOT_D,
    PLATE_T,
    STANDOFF_BASE_D,
    STANDOFF_BASE_H,
    STANDOFF_D,
    STANDOFF_H,
    box,
    cyl,
    pcb_holes_centered,
    to_trimesh,
)

# --- Fuselage ---
FLOOR_Z = -43.53 - LEDGE_Z  # lower channel floor, -9.0 below the ledges
LOWER_HALF_W = 20.0  # lower channel spans |x| < 20

# --- Battery (3S 2200 mAh, 106 x 33.5 x 25) ---
BAT_L, BAT_W, BAT_H = 106.0, 33.5, 25.0
BAT_FIT = 0.5  # per side
BAT_TOP_Z = FLOOR_Z + BAT_H

# --- Sled ---
OPEN_HALF_W = BAT_W / 2 + BAT_FIT  # 17.25
OPEN_HALF_L = BAT_L / 2 + BAT_FIT  # 53.5
COLLAR_T = 2.0
COLLAR_H = 10.0  # above plate top; stays below the battery top
WIRE_GAP_W = 18.0  # gap in the rear collar wall, in case the battery goes in reversed
POST_X = 23.5
POST_D = 8.0
SCREW_POST_Y = 53.0  # +Y end: thumb screws, clear of the PCB
PIN_POST_Y = -38.0  # alignment pins, far enough from the -Y PCB standoffs to keep their deck holes open
HALF_L = 57.0

# --- Deck ---
FOAM_GAP = 1.5  # deck underside above battery top; ~3 mm foam pad compresses into it
DECK_Z = BAT_TOP_Z + FOAM_GAP  # deck underside = post tops
DECK_T = 2.5
DECK_CLEARANCE = 0.6  # per side, deck to fuselage wall
INSERT_OD = 3.5  # measured outer diameter of the heat-set inserts
INSERT_D = INSERT_OD - 0.3  # hole the insert is melted into
INSERT_DEPTH = 6.0
SCREW_CLEAR_D = 3.4  # passes M2 or M3 thumb screws; the pins do the locating
PIN_D = 3.0
PIN_H = 2.0  # stays inside the deck thickness
PIN_HOLE_D = 3.5
PCB_EDGE_TO_SCREW = 5.5  # PCB edge kept this far from the screw axis
PCB_OFFSET_Y = SCREW_POST_Y - PCB_EDGE_TO_SCREW - PCB_L / 2  # PCB shifted toward -Y
WINDOWS = [(-11.0, 11.0, -44.0, -6.0), (-11.0, 11.0, 4.0, 38.0)]  # deck lightening


def post_positions():
    return {
        "screw": [(POST_X, SCREW_POST_Y), (-POST_X, SCREW_POST_Y)],
        "pin": [(POST_X, PIN_POST_Y), (-POST_X, PIN_POST_Y)],
    }


def build_sled():
    half_w = CHANNEL_HALF_W - CLEARANCE

    plate = box(-half_w, half_w, -HALF_L, HALF_L, 0, PLATE_T)
    # Opening runs out through the front end so the battery leads clear the plate.
    plate -= box(-OPEN_HALF_W, OPEN_HALF_W, -HALF_L - 1, OPEN_HALF_L, -1, PLATE_T + 1)

    lips = box(half_w - LIP_T, half_w, -HALF_L, HALF_L, PLATE_T, PLATE_T + LIP_H)
    lips += box(-half_w, -half_w + LIP_T, -HALF_L, HALF_L, PLATE_T, PLATE_T + LIP_H)

    outer_w = OPEN_HALF_W + COLLAR_T
    outer_l = OPEN_HALF_L + COLLAR_T
    collar = box(-outer_w, outer_w, -outer_l, outer_l, PLATE_T, PLATE_T + COLLAR_H)
    collar -= box(-OPEN_HALF_W, OPEN_HALF_W, -outer_l - 1, OPEN_HALF_L, 0, PLATE_T + COLLAR_H + 1)
    collar -= box(-WIRE_GAP_W / 2, WIRE_GAP_W / 2, OPEN_HALF_L - 1, outer_l + 1, PLATE_T, PLATE_T + COLLAR_H + 1)

    body = plate + lips + collar
    posts = post_positions()
    post_h = DECK_Z - PLATE_T
    for x, y in posts["screw"] + posts["pin"]:
        body += cyl(POST_D, POST_D, post_h, x, y, PLATE_T)
    for x, y in posts["pin"]:
        body += cyl(PIN_D, PIN_D, PIN_H, x, y, DECK_Z)
    for x, y in posts["screw"]:
        body -= cyl(INSERT_D, INSERT_D, INSERT_DEPTH + 1, x, y, DECK_Z - INSERT_DEPTH)
    return body


def build_deck():
    half_w = CHANNEL_HALF_W - DECK_CLEARANCE
    top = DECK_Z + DECK_T

    deck = box(-half_w, half_w, -HALF_L, HALF_L, DECK_Z, top)
    for x0, x1, y0, y1 in WINDOWS:
        deck -= box(x0, x1, y0, y1, DECK_Z - 1, top + 1)

    posts = post_positions()
    for x, y in posts["screw"]:
        deck -= cyl(SCREW_CLEAR_D, SCREW_CLEAR_D, DECK_T + 2, x, y, DECK_Z - 1)
    for x, y in posts["pin"]:
        deck -= cyl(PIN_HOLE_D, PIN_HOLE_D, DECK_T + 2, x, y, DECK_Z - 1)

    holes = [(x, y + PCB_OFFSET_Y) for x, y in pcb_holes_centered()]
    for x, y in holes:
        deck += cyl(STANDOFF_BASE_D, STANDOFF_D, STANDOFF_BASE_H, x, y, top)
        deck += cyl(STANDOFF_D, STANDOFF_D, STANDOFF_H, x, y, top)
    # Blind pilot holes: stop 0.5 mm above the deck underside.
    for x, y in holes:
        deck -= cyl(PILOT_D, PILOT_D, DECK_T - 0.5 + STANDOFF_H + 1, x, y, DECK_Z + 0.5)
    return deck


def battery_box():
    return box(-BAT_W / 2, BAT_W / 2, -BAT_L / 2, BAT_L / 2, FLOOR_Z, BAT_TOP_Z)


def pcb_box():
    z0 = DECK_Z + DECK_T + STANDOFF_H
    return box(-PCB_W / 2, PCB_W / 2, -PCB_L / 2 + PCB_OFFSET_Y, PCB_L / 2 + PCB_OFFSET_Y, z0, z0 + 1.6)


def load_fuselage(stl_path):
    fuse = trimesh.load(stl_path)
    return mf.Manifold(
        mf.Mesh(
            vert_properties=np.asarray(fuse.vertices, dtype=np.float32),
            tri_verts=np.asarray(fuse.faces, dtype=np.uint32),
        )
    )


def check_fit(stl_path):
    fuse = load_fuselage(stl_path)
    sled, deck, bat, pcb = build_sled(), build_deck(), battery_box(), pcb_box()
    # Channel is clear with the ledges from Y=-10 to ~Y=124.
    for y in (-10 + HALF_L + 1, 60.0, 124 - HALF_L):
        at = lambda m: m.translate([0, y, LEDGE_Z + 0.01])  # noqa: E731
        pairs = {
            "sled/fuselage": (at(sled), fuse),
            "deck/fuselage": (at(deck), fuse),
            "battery/fuselage": (at(bat), fuse),
            "pcb/fuselage": (at(pcb), fuse),
            "battery/sled": (at(bat), at(sled)),
            "battery/deck": (at(bat), at(deck)),
            "deck/sled": (at(deck), at(sled)),
        }
        print(f"Y={y:6.1f}  " + "  ".join(f"{k}={(a ^ b).volume():.3f}" for k, (a, b) in pairs.items()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path, help="P39-MidFuseV3.stl for a collision check")
    args = parser.parse_args()

    here = Path(__file__).parent
    for name, part in (("battery_sled", build_sled()), ("battery_deck", build_deck())):
        out = here / f"{name}.stl"
        to_trimesh(part).export(out)
        print(f"wrote {out}  volume={part.volume():.0f} mm^3")
    print(f"battery top z={BAT_TOP_Z:.2f}  deck underside z={DECK_Z:.2f}  PCB offset y={PCB_OFFSET_Y:+.2f}")
    print(f"PCB top z={DECK_Z + DECK_T + STANDOFF_H + 1.6:.2f} (fuselage z={LEDGE_Z + DECK_Z + DECK_T + STANDOFF_H + 1.6:.2f})")

    if args.check:
        check_fit(args.check)


if __name__ == "__main__":
    main()
