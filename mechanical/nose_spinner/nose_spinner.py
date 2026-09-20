"""One-piece spinner for a 2213-935KV outrunner with a 1045 prop on a P-39.

Measured on the aircraft, from the front face of the nose:
  26.2 mm  to the front face of the rotating motor can
  14.2 mm  of M6 thread beyond that, of which 2 mm shoulder + 8.5 mm prop hub
           + 2.9 mm nut hex are already used - nothing printed fits in there.

So the spinner touches neither the shaft nor the nose. It is a single shell
that rotates with the motor:

  - the rear opening matches the nose diameter and runs 2 mm clear of it
  - it wraps the exposed can with ~1 mm clearance
  - two slots let the propeller blades through
  - inside, a socket grips the bullet prop nut; two M3 grub screws run through
    solid struts in the wall and lock the shell to that nut
  - six holes near the wide end pump cooling air out

Assembly: fit the propeller and tighten its nut normally, metal on metal. Then
slide the shell on from the front, feeding the blades through the slots, and
tighten the two grub screws onto the nut.

Coordinates: Z along the motor axis, +Z forward, z = 0 at the nose opening.

Requirements: numpy, trimesh, manifold3d
Usage:        python nose_spinner.py [--check path/to/P39-Nose.stl]
"""

import argparse
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

# --- Nose (P39-Nose.stl: front face at z=354, axis x=0 y=182.4) ---
NOSE_R = 26.3
NOSE_FACE_Z = 354.0
NOSE_AXIS_Y = 182.4

# --- Measured on the aircraft ---
MOTOR_PROTRUSION = 26.2  # nose face to the can's front face
CAN_R = 14.0
CAN_GAP = 1.0
SHOULDER = 2.0  # can face to the propeller seat
HUB_T = 8.5  # 1045 hub thickness
PROP_HUB_D = 20.0
NUT_HEX_H = 2.9
NUT_BASE_D = 11.2
NUT_CONE_L = 12.9
BLADE_CHORD = 17.5  # blade width ~20 mm out from the centre
BLADE_T = 3.0  # blade thickness out there
BLADE_PITCH_IN = 4.5  # 1045: 4.5 inch pitch, sets how steeply the root sits

CAN_FRONT_Z = MOTOR_PROTRUSION
PROP_SEAT_Z = CAN_FRONT_Z + SHOULDER
HUB_FRONT_Z = PROP_SEAT_Z + HUB_T
NUT_TIP_Z = HUB_FRONT_Z + NUT_HEX_H + NUT_CONE_L

# --- Shell ---
REAR_GAP = 2.0  # air gap in front of the nose
TIP_Z = 62.0  # overall tip, ~9 mm past the nut
WALL = 2.0
SHELL_K, SHELL_P = 2.2, 0.62  # r(t) = R (1 - (t/L)^K)^P
VENT_D = 7.0
VENT_Z = 8.0
VENT_COUNT = 6

# --- Blade slots ---
SLOT_MARGIN = 3.5  # per slot, on top of the blade chord
SLOT_EXTRA_Z = 2.0  # axial margin per side on the swept blade height

# --- Nut socket and its struts ---
SOCKET_D = NUT_BASE_D + 0.4
SOCKET_STRAIGHT = 8.0
SOCKET_CONE_L = 9.0
BOSS_D = SOCKET_D + 5.0
STRUT_W = 8.0
STRUT_Z0 = 1.5  # strut starts this far in front of the nut hex
STRUT_L = 8.0
GRUB_PILOT_D = 2.5  # M3 grub screw cuts its own thread
GRUB_ANGLES = (90.0, 270.0)
SLOT_ANGLES = (0.0, 180.0)

SEGMENTS = 96
PROFILE_STEPS = 60


def shell_r(z, offset=0.0):
    """Outer radius of the shell; flat at the rear, pointed at the tip."""
    t = np.clip((z - REAR_GAP) / (TIP_Z - REAR_GAP), 0.0, 1.0)
    return NOSE_R * np.maximum(0.0, 1.0 - t**SHELL_K) ** SHELL_P - offset


def blade_angle():
    """Local pitch angle where the blade crosses the shell wall."""
    r_exit = shell_r((PROP_SEAT_Z + HUB_FRONT_Z) / 2) - WALL
    return np.arctan2(BLADE_PITCH_IN * 25.4, 2 * np.pi * r_exit)


def blade_slot_height():
    """Axial room the tilted blade section needs as the shell slides over it."""
    a = blade_angle()
    return BLADE_CHORD * np.sin(a) + BLADE_T * np.cos(a) + 2 * SLOT_EXTRA_Z


def revolve(points):
    return mf.Manifold.revolve(mf.CrossSection([[(float(r), float(z)) for r, z in points]]), SEGMENTS)


def solid_of(radius_at, z0, z1):
    zs = np.linspace(z0, z1, PROFILE_STEPS)
    pts = [(0.0, z0)] + [(max(float(radius_at(z)), 0.01), z) for z in zs] + [(0.0, z1)]
    return revolve(pts)


def cyl(d, h, z0):
    return mf.Manifold.cylinder(h, d / 2, d / 2, SEGMENTS).translate([0, 0, z0])


def nut_socket(z_base):
    return revolve(
        [
            (0.0, z_base),
            (SOCKET_D / 2, z_base),
            (SOCKET_D / 2, z_base + SOCKET_STRAIGHT),
            (1.6, z_base + SOCKET_STRAIGHT + SOCKET_CONE_L),
            (0.0, z_base + SOCKET_STRAIGHT + SOCKET_CONE_L),
        ]
    )


def build_spinner():
    body = solid_of(shell_r, REAR_GAP, TIP_Z)
    body -= solid_of(lambda z: shell_r(z, WALL), REAR_GAP - 1.0, TIP_Z - 5.0)
    body -= cyl(2 * (CAN_R + CAN_GAP), CAN_FRONT_Z + 1.0, REAR_GAP - 1.0)  # clear the can

    # nut socket on a boss, tied to the shell by two struts that also carry the
    # grub screws
    socket_z0 = HUB_FRONT_Z
    boss_top = socket_z0 + SOCKET_STRAIGHT + SOCKET_CONE_L
    body += cyl(BOSS_D, boss_top - socket_z0, socket_z0)
    strut_z0 = socket_z0 + STRUT_Z0
    for ang in GRUB_ANGLES:
        strut = mf.Manifold.cube([2 * NOSE_R, STRUT_W, STRUT_L], True)
        body += strut.translate([NOSE_R / 2, 0, strut_z0 + STRUT_L / 2]).rotate([0, 0, ang])
    body = body ^ solid_of(shell_r, REAR_GAP, TIP_Z)  # trim the struts to the shell
    body -= nut_socket(socket_z0)
    for ang in GRUB_ANGLES:
        hole = mf.Manifold.cylinder(2 * NOSE_R, GRUB_PILOT_D / 2, GRUB_PILOT_D / 2, 32)
        hole = hole.rotate([0, 90, 0]).translate([0, 0, strut_z0 + STRUT_L / 2])
        body -= hole.rotate([0, 0, ang])

    # blade slots
    slot_w = BLADE_CHORD + 2 * SLOT_MARGIN
    slot_h = blade_slot_height()
    slot_zc = (PROP_SEAT_Z + HUB_FRONT_Z) / 2
    for ang in SLOT_ANGLES:
        slot = mf.Manifold.cube([slot_w, 2 * NOSE_R + 10, slot_h], True)
        body -= slot.translate([0, (2 * NOSE_R + 10) / 2, slot_zc]).rotate([0, 0, ang])

    # cooling outlets
    for i in range(VENT_COUNT):
        vent = mf.Manifold.cylinder(60.0, VENT_D / 2, VENT_D / 2, 48)
        vent = vent.rotate([0, 90, 0]).translate([-30, 0, VENT_Z])
        body -= vent.rotate([0, 0, i * 360.0 / VENT_COUNT + 30.0])
    return body


def to_trimesh(m):
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
    t.merge_vertices()
    bodies = [b for b in t.split(only_watertight=False) if b.volume > 1e-6]
    return trimesh.util.concatenate(bodies) if len(bodies) > 1 else bodies[0]


def to_assembly(m):
    return m.translate([0, NOSE_AXIS_Y, NOSE_FACE_Z])


def motor_mock():
    parts = cyl(2 * CAN_R, MOTOR_PROTRUSION, 0.0)
    parts += cyl(PROP_HUB_D, HUB_T, PROP_SEAT_Z)
    parts += cyl(NUT_BASE_D, NUT_HEX_H, HUB_FRONT_Z)
    parts += revolve(
        [
            (0.0, HUB_FRONT_Z + NUT_HEX_H),
            (NUT_BASE_D / 2, HUB_FRONT_Z + NUT_HEX_H),
            (0.0, NUT_TIP_Z),
        ]
    )
    return parts


def blade_mock():
    """Both blade roots, tilted by the local pitch angle, out to the shell."""
    r_exit = shell_r((PROP_SEAT_Z + HUB_FRONT_Z) / 2) - WALL
    angle = np.degrees(np.arctan2(BLADE_PITCH_IN * 25.4, 2 * np.pi * r_exit))
    blades = mf.Manifold()
    for ang in SLOT_ANGLES:
        b = mf.Manifold.cube([BLADE_CHORD, 2 * NOSE_R, 3.0], True)
        b = b.rotate([0, -angle, 0]).translate([0, NOSE_R, (PROP_SEAT_Z + HUB_FRONT_Z) / 2])
        blades += b.rotate([0, 0, ang])
    return blades


def check(nose_path):
    nose_mesh = trimesh.load(nose_path)
    nose = mf.Manifold(
        mf.Mesh(
            vert_properties=np.asarray(nose_mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(nose_mesh.faces, dtype=np.uint32),
        )
    )
    spin, motor, blades = build_spinner(), motor_mock(), blade_mock()
    print(f"spinner/nose overlap  = {(to_assembly(spin) ^ nose).volume():.3f} mm^3")
    print(f"spinner/motor overlap = {(spin ^ motor).volume():.3f} mm^3 (socket takes the nut)")
    print(f"spinner/blade overlap = {(spin ^ blades).volume():.3f} mm^3")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path, help="P39-Nose.stl for a fit check")
    args = parser.parse_args()

    part = build_spinner()
    out = Path(__file__).parent / "spinner_one_piece.stl"
    to_trimesh(part).export(out)
    print(f"wrote {out.name}  volume={part.volume():.0f} mm^3  (~{part.volume() * 1.24e-3:.1f} g of PLA)")
    print(
        f"can front z={CAN_FRONT_Z:.1f}  prop seat z={PROP_SEAT_Z:.1f}  hub front z={HUB_FRONT_Z:.1f}  "
        f"nut tip z={NUT_TIP_Z:.1f}  shell tip z={TIP_Z:.1f}\n"
        f"shell radius: {shell_r(REAR_GAP):.1f} at the rear, {shell_r(PROP_SEAT_Z):.1f} at the prop, "
        f"{shell_r(HUB_FRONT_Z):.1f} at the nut\n"
        f"blade slots: {BLADE_CHORD + 2 * SLOT_MARGIN:.1f} wide x {blade_slot_height():.1f} tall, "
        f"grub screws at z={HUB_FRONT_Z + STRUT_Z0 + STRUT_L / 2:.1f}"
    )

    if args.check:
        check(args.check)


if __name__ == "__main__":
    main()
