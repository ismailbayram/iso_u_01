r"""Printed rims for the P-39 landing gear, running on an M4 part-threaded bolt.

The stock legs are drilled for carbon rod (P39-Instructions.pdf: "x2 56mm
wheels / 4mm carbon rod, x1 45mm wheel / 3mm carbon rod"). Measured from the
STLs, the axle bore of P39-LegMainL/R is 4.30 mm through a 14.79 mm hub
(X = -9.94 .. +4.85, bore centre Y=78.0 Z=10.0) and P39-LegFront is 3.26 mm
through a 12.50 mm hub (X = 7.5 .. 20.0, bore centre Y=105.0 Z=-30.0). The
front leg is drilled out to 4 mm so one bolt size does all three.

Bolt stack, per leg:

    [head] [RIM 17.0 spins on the plain shank] [leg hub] [washer] [nut]
      \_________ plain shank 17.7 ________/    \___ thread 20.3 ___/

The nut pulls against the leg, so the bolt is rigid with the leg and the rim
turns on the ground shank. The head sits in a counterbore in the rim's outer
face and is what holds the rim on. Reversing the bolt does not work: only
2.9 mm of shank would be left outboard and the rim would ride on the thread.

Tyres are foam rings cut with a hole saw and glued into the rim channel:

    main  ring  OD 56 / ID 40 / 13.8 wide   (rim channel opens to 13.8 at D46)
    front ring  OD 45 / ID 31 / 10.0 wide   (rim channel opens to 10.0 at D36)

Print hub axis vertical, counterbore face up, plain hub face on the bed. The
channel shoulders are 45 degrees so nothing overhangs. Use 3 perimeters and
>=30% infill; the stock 1-perimeter/no-infill profile is not enough for a hub
carrying the whole airframe on a steel bolt.

Requirements: numpy, trimesh, manifold3d
Usage:        python wheels.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(__file__).parent
LEGS = Path("/Users/ismailbayram/Downloads/Bell P-39 Airacobra RC Model Plane/files")

# --- shared hub, set by the bolt ---
WIDTH    = 17.0   # shank is 17.7 -> 0.7 mm end float, rim turns free
BORE     = 4.6    # modelled; this printer loses ~0.5 mm on holes -> ~4.1 printed.
                  # Ream to 4.2 if it binds on the shank.
HUB_D    = 10.0
CB_D     = 9.0    # counterbore, prints ~8.5: clears an M4 socket cap (D7.0) and a hex head (8.1 a/c)
CB_DEPTH = 4.2    # socket cap is 4.0 tall, so the head never clamps the rim
WEB_T    = 2.2    # web disc, on the rim centreline
WALL     = 2.0    # channel floor wall

# --- per wheel: tyre OD, channel floor dia, flange dia, channel floor width,
#                lightening hole dia, hole pitch circle, hole count ---
MAIN  = dict(tyre=56.0, floor_d=40.0, flange_d=46.0, floor_w=7.8, hole_d=8.0, pcd=25.0, holes=5)
FRONT = dict(tyre=45.0, floor_d=31.0, flange_d=36.0, floor_w=5.0, hole_d=6.0, pcd=19.0, holes=5)

SECTIONS = 128


def cyl(d, z0, z1, x=0.0, y=0.0):
    """cylinder of diameter d spanning z0..z1, axis at (x, y)"""
    m = trimesh.creation.cylinder(radius=d / 2.0, height=z1 - z0, sections=SECTIONS)
    m.apply_translation([x, y, (z0 + z1) / 2.0])
    return m


def build(tyre, floor_d, flange_d, floor_w, hole_d, pcd, holes):
    r_floor, r_flange = floor_d / 2.0, flange_d / 2.0
    mid = WIDTH / 2.0
    rise = r_flange - r_floor               # 45 deg shoulder: radial rise == axial run
    z0, z1 = mid - floor_w / 2.0, mid + floor_w / 2.0   # channel floor
    o0, o1 = z0 - rise, z1 + rise                       # channel mouth

    assert o0 > 0 and o1 < WIDTH, "channel mouth runs off the rim face"

    # solid of revolution: flange face, 45 deg shoulder, channel floor, shoulder, flange face
    profile = np.array([
        [0.0, 0.0], [r_flange, 0.0], [r_flange, o0], [r_floor, z0],
        [r_floor, z1], [r_flange, o1], [r_flange, WIDTH], [0.0, WIDTH],
    ])
    m = trimesh.creation.revolve(profile, sections=SECTIONS)

    # hollow both sides down to the web, then put the hub back
    r_in = r_floor - WALL
    m = m.difference(cyl(2 * r_in, -1.0, mid - WEB_T / 2.0))
    m = m.difference(cyl(2 * r_in, mid + WEB_T / 2.0, WIDTH + 1.0))
    m = m.union(cyl(HUB_D, 0.0, WIDTH))

    for i in range(holes):
        a = 2.0 * np.pi * i / holes
        m = m.difference(cyl(hole_d, mid - WEB_T, mid + WEB_T,
                             x=pcd / 2.0 * np.cos(a), y=pcd / 2.0 * np.sin(a)))

    m = m.difference(cyl(BORE, -1.0, WIDTH + 1.0))
    m = m.difference(cyl(CB_D, WIDTH - CB_DEPTH, WIDTH + 1.0))

    m.process(validate=True)
    return m


def check(m, name, tyre, leg, bore_c, faces):
    """report the fit against the printed leg: which face the rim goes on, and
    whether anything on the leg is inside the swept tyre."""
    leg = trimesh.load(LEGS / leg)
    v = leg.vertices
    radial = np.hypot(v[:, 1] - bore_c[0], v[:, 2] - bore_c[1])   # bore axis is leg X
    outside_bore = radial > BORE / 2.0        # anything inside the bore just enters the rim hole
    print(f"{name}: watertight={m.is_watertight} vol={m.volume/1000:.2f}cm3 "
          f"mass@1.24={m.volume*1.24/1000:.1f}g bbox={(m.bounds[1]-m.bounds[0]).round(2).tolist()}")
    for label, x_face, direction in faces:
        beyond = ((v[:, 0] - x_face) * direction > 0.05) & outside_bore
        clear = radial[beyond].min() if beyond.any() else np.inf
        verdict = "CLEAR" if clear > tyre / 2.0 else f"FOULS (needs >{tyre/2.0:.1f})"
        print(f"   {label:<16} face X={x_face:+7.2f}  nearest leg material at r={clear:6.2f}  {verdict}")


def preview(parts, path):
    fig = plt.figure(figsize=(11, 5.5))
    for i, (name, m) in enumerate(parts):
        for j, (el, az) in enumerate(((22, -55), (0, -90))):
            ax = fig.add_subplot(2, len(parts), j * len(parts) + i + 1, projection="3d")
            ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor="#8ab4c8",
                                                 edgecolor="k", linewidths=0.08))
            c, r = m.bounds.mean(0), (m.bounds[1] - m.bounds[0]).max() / 2
            ax.set_xlim(c[0] - r, c[0] + r)
            ax.set_ylim(c[1] - r, c[1] + r)
            ax.set_zlim(c[2] - r, c[2] + r)
            ax.view_init(el, az)
            ax.set_title(name, fontsize=8)
            ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    main_w = build(**MAIN)
    front_w = build(**FRONT)
    main_w.export(OUT / "wheel_main.stl")
    front_w.export(OUT / "wheel_front.stl")

    check(main_w, "wheel_main (x2)", MAIN["tyre"], "P39-LegMainL.stl", (78.0, 10.0),
          [("strut side", 4.85, +1), ("domed side", -10.00, -1)])
    check(front_w, "wheel_front (x1)", FRONT["tyre"], "P39-LegFront.stl", (105.0, -30.0),
          [("outboard", 20.00, +1), ("inboard", 7.50, -1)])

    preview([("wheel_main  D56", main_w), ("wheel_front  D45", front_w)],
            OUT / "wheels_preview.png")

    shank_free = 17.7 - WIDTH
    print(f"\nbolt check: shank 17.7 - rim {WIDTH} = {shank_free:.1f} mm end float")
    for leg_name, hub_t in (("main", 14.79), ("front", 12.50)):
        print(f"   {leg_name} leg: thread 20.3 - hub {hub_t} = {20.3 - hub_t:.2f} mm "
              f"for washer+nut (M4 nut 3.2 + washer 0.8 = 4.0)")


if __name__ == "__main__":
    main()
