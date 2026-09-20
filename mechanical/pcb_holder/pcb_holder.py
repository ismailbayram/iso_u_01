"""PCB holder for the u1flightcontroller board inside P39-MidFuseV3.

The holder is a flat open frame that rests on the two 8 mm ledges of the
mid-fuselage channel (z = -34.53 in the STL, walls at x = +/-28) and is glued
to the ledges and side walls. The PCB is screwed onto four standoffs with M2
self-tapping screws.

Coordinates: X across the fuselage, Y along it, Z up. Seen from above, the
hole pattern matches the KiCad top view (component side up).

Requirements: numpy, trimesh, manifold3d
Usage:        python pcb_holder.py [--check path/to/P39-MidFuseV3.stl]
"""

import argparse
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

# --- PCB (from u1flightcontroller.kicad_pcb, Edge.Cuts + MountingHole_2.2mm_M2) ---
PCB_W = 169.418 - 117.602  # 51.816
PCB_L = 168.021 - 67.564  # 100.457
PCB_ORIGIN = (117.602, 67.564)
PCB_HOLES_ABS = [
    (122.555, 72.009),
    (164.211, 72.009),
    (122.555, 164.719),
    (164.338, 163.830),
]

# --- Fuselage channel (measured from P39-MidFuseV3.stl) ---
CHANNEL_HALF_W = 28.0  # inner walls at x = +/-28
LEDGE_Z = -34.53  # top of the side ledges
LEDGE_INNER_X = 20.0  # ledges span |x| = 20..28

# --- Holder parameters ---
CLEARANCE = 0.3  # per side, between holder and fuselage wall
PLATE_T = 2.0
PLATE_L = PCB_L + 4.0
RAIL_INNER_X = 17.0  # side rails span |x| = RAIL_INNER_X..outer edge
END_BAR_W = 9.0
MID_BAR_W = 8.0
LIP_T = 1.6  # vertical glue lips against the side walls
LIP_H = 5.0  # above plate top; kept below the PCB so the board never touches them
STANDOFF_H = 6.0  # plate top to PCB bottom
STANDOFF_D = 6.0
STANDOFF_BASE_D = 9.0
STANDOFF_BASE_H = 1.5
PILOT_D = 1.8  # M2 self-tapping into PLA/PETG
SEGMENTS = 64


def pcb_holes_centered():
    """Hole centers relative to the PCB center, KiCad Y flipped to Z-up."""
    cx = PCB_ORIGIN[0] + PCB_W / 2
    cy = PCB_ORIGIN[1] + PCB_L / 2
    return [(x - cx, -(y - cy)) for x, y in PCB_HOLES_ABS]


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(d0, d1, h, x, y, z):
    return mf.Manifold.cylinder(h, d0 / 2, d1 / 2, SEGMENTS).translate([x, y, z])


def build_holder():
    half_w = CHANNEL_HALF_W - CLEARANCE
    half_l = PLATE_L / 2
    holes = pcb_holes_centered()

    plate = box(-half_w, half_w, -half_l, half_l, 0, PLATE_T)
    # Open the middle for wiring down into the lower channel, keeping side
    # rails, end bars and one mid bar.
    for y0, y1 in [
        (-half_l + END_BAR_W, -MID_BAR_W / 2),
        (MID_BAR_W / 2, half_l - END_BAR_W),
    ]:
        plate -= box(-RAIL_INNER_X, RAIL_INNER_X, y0, y1, -1, PLATE_T + 1)

    lips = box(half_w - LIP_T, half_w, -half_l, half_l, PLATE_T, PLATE_T + LIP_H)
    lips += box(-half_w, -half_w + LIP_T, -half_l, half_l, PLATE_T, PLATE_T + LIP_H)

    body = plate + lips
    for x, y in holes:
        body += cyl(STANDOFF_BASE_D, STANDOFF_D, STANDOFF_BASE_H, x, y, PLATE_T)
        body += cyl(STANDOFF_D, STANDOFF_D, STANDOFF_H, x, y, PLATE_T)
    for x, y in holes:
        body -= cyl(PILOT_D, PILOT_D, PLATE_T + STANDOFF_H + 2, x, y, -1)
    return body


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)


def check_fit(holder, stl_path, y_center):
    fuse = trimesh.load(stl_path)
    fuse_m = mf.Manifold(
        mf.Mesh(
            vert_properties=np.asarray(fuse.vertices, dtype=np.float32),
            tri_verts=np.asarray(fuse.faces, dtype=np.uint32),
        )
    )
    placed = holder.translate([0, y_center, LEDGE_Z + 0.01])
    overlap = (placed ^ fuse_m).volume()
    print(f"fit check at Y={y_center}: overlap volume = {overlap:.4f} mm^3")
    return overlap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path, help="P39-MidFuseV3.stl for a collision check")
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("pcb_holder.stl"))
    args = parser.parse_args()

    holder = build_holder()
    to_trimesh(holder).export(args.out)
    print(f"wrote {args.out}  volume={holder.volume():.0f} mm^3")
    for x, y in pcb_holes_centered():
        print(f"standoff at x={x:+.3f} y={y:+.3f}")

    if args.check:
        # Channel is clear with the ledges from Y=-10 to ~Y=124.
        for y in (-10 + PLATE_L / 2 + 1, 60.0, 124 - PLATE_L / 2):
            check_fit(holder, args.check, y)


if __name__ == "__main__":
    main()
