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

Tyres are printed in TPU 95A and stretched on over the flanges (foam rings
were tried first and would not stay put). Each tyre's bore is the negative of
its rim channel, undersized by TPU_FIT on the radius so the bead grips without
glue. The front rim's channel is only 10.0 wide, which is not enough rubber
under the whole nose load, so the front tyre's tread overhangs the flanges and
runs 14.0 wide; the rims themselves are unchanged and need no reprint.

Print everything hub/tyre axis vertical. The rim goes counterbore face up,
plain hub face on the bed. Every shoulder and bore cone is 45 degrees, so
neither part needs support.

    rim   3+ perimeters, >=30% infill  - the hub carries the airframe on a
                                         steel bolt, the stock 1-perimeter
                                         no-infill aircraft profile will not do
    tyre  2 perimeters, 8% gyroid      - see tpu_profile.json

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

# --- tyre ---
TPU_FIT  = 0.15   # radial interference at the bead seat -> 0.30 mm on diameter
TPU_CLR  = 0.05   # radial clearance over the flange, so only the bead is stretched
TREAD_CH = 0.8    # 45 deg chamfer on the tread edges
TPU_RHO  = 1.21   # g/cm3, typical TPU 95A (Creality ships 1.12 and 1.24 in its own profiles)

# --- per wheel. tyre/floor_d/flange_d/floor_w/hole_* describe the rim;
#     tread_w is the tyre's tread width (>= the channel mouth). ---
MAIN  = dict(tyre=56.0, floor_d=40.0, flange_d=46.0, floor_w=7.8,
             hole_d=8.0, pcd=25.0, holes=5, tread_w=13.8)
FRONT = dict(tyre=45.0, floor_d=31.0, flange_d=36.0, floor_w=5.0,
             hole_d=6.0, pcd=19.0, holes=5, tread_w=14.0)

SECTIONS = 128


def cyl(d, z0, z1, x=0.0, y=0.0):
    """cylinder of diameter d spanning z0..z1, axis at (x, y)"""
    m = trimesh.creation.cylinder(radius=d / 2.0, height=z1 - z0, sections=SECTIONS)
    m.apply_translation([x, y, (z0 + z1) / 2.0])
    return m


def channel(p):
    """the rim channel in rim coordinates: floor radius, flange radius, and the
    z of the floor edges (z0, z1) and of the mouth edges (o0, o1)"""
    r_floor, r_flange = p["floor_d"] / 2.0, p["flange_d"] / 2.0
    mid = WIDTH / 2.0
    rise = r_flange - r_floor               # 45 deg shoulder: radial rise == axial run
    z0, z1 = mid - p["floor_w"] / 2.0, mid + p["floor_w"] / 2.0
    return r_floor, r_flange, z0, z1, z0 - rise, z1 + rise


def build(p):
    r_floor, r_flange, z0, z1, o0, o1 = channel(p)
    mid = WIDTH / 2.0

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

    for i in range(p["holes"]):
        a = 2.0 * np.pi * i / p["holes"]
        m = m.difference(cyl(p["hole_d"], mid - WEB_T, mid + WEB_T,
                             x=p["pcd"] / 2.0 * np.cos(a), y=p["pcd"] / 2.0 * np.sin(a)))

    m = m.difference(cyl(BORE, -1.0, WIDTH + 1.0))
    m = m.difference(cyl(CB_D, WIDTH - CB_DEPTH, WIDTH + 1.0))

    m.process(validate=True)
    return m


def build_tyre(p):
    """TPU tyre. Its bore is the negative of the rim channel, tightened by
    TPU_FIT at the bead seat; the tread may run wider than the channel mouth
    and then simply lies over the flange."""
    r_floor, r_flange, z0, z1, o0, o1 = channel(p)
    r_seat = r_floor - TPU_FIT
    r_bore = r_flange + TPU_CLR
    r_tread = p["tyre"] / 2.0
    mid = WIDTH / 2.0
    t0, t1 = mid - p["tread_w"] / 2.0, mid + p["tread_w"] / 2.0

    assert t0 >= 0.0 and t1 <= WIDTH, "tread is wider than the rim"
    assert t0 <= o0 and t1 >= o1, "tread is narrower than the channel mouth"
    assert r_tread - TREAD_CH > r_bore, "tread chamfer eats the whole sidewall"

    # closed CCW section in (r, z): out along the lower sidewall, up the tread,
    # back in along the upper sidewall, then down the bore
    section = [
        (r_bore, t0), (r_tread - TREAD_CH, t0), (r_tread, t0 + TREAD_CH),
        (r_tread, t1 - TREAD_CH), (r_tread - TREAD_CH, t1), (r_bore, t1),
        (r_bore, o1), (r_seat, z1), (r_seat, z0), (r_bore, o0),
    ]
    pts = [section[0]]
    for q in section[1:]:
        if abs(q[0] - pts[-1][0]) > 1e-9 or abs(q[1] - pts[-1][1]) > 1e-9:
            pts.append(q)
    pts.append(pts[0])

    m = trimesh.creation.revolve(np.array(pts), sections=SECTIONS)
    m.process(validate=True)
    return m


def check_tyre(rim, tyre, name, p):
    grip = rim.intersection(tyre)
    seat_len = p["floor_w"]
    r_floor = p["floor_d"] / 2.0
    want = np.pi * (r_floor ** 2 - (r_floor - TPU_FIT) ** 2) * seat_len
    print(f"{name}: watertight={tyre.is_watertight} vol={tyre.volume/1000:.2f}cm3 "
          f"solid@{TPU_RHO}={tyre.volume*TPU_RHO/1000:.1f}g "
          f"bbox={(tyre.bounds[1]-tyre.bounds[0]).round(2).tolist()}")
    print(f"   bead seat  D{p['floor_d']-2*TPU_FIT:.1f} on a D{p['floor_d']:.1f} channel "
          f"-> {2*TPU_FIT:.2f} mm squeeze, stretches over the D{p['flange_d']:.1f} flange "
          f"({100*(p['flange_d']/p['floor_d']-1):.0f}%)")
    print(f"   interference volume {grip.volume:7.1f} mm3 (bead seat alone predicts {want:.1f})")
    mouth = (p["flange_d"] - p["floor_d"]) + p["floor_w"]
    print(f"   tread {p['tread_w']:.1f} wide vs channel mouth {mouth:.1f}, sits inside the "
          f"{WIDTH:.1f} rim with {(WIDTH-p['tread_w'])/2.0:.1f} mm of rim lip showing each side")


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
    main_w, front_w = build(MAIN), build(FRONT)
    main_t, front_t = build_tyre(MAIN), build_tyre(FRONT)
    main_w.export(OUT / "wheel_main.stl")
    front_w.export(OUT / "wheel_front.stl")
    main_t.export(OUT / "tyre_main.stl")
    front_t.export(OUT / "tyre_front.stl")

    check(main_w, "wheel_main (x2)", MAIN["tyre"], "P39-LegMainL.stl", (78.0, 10.0),
          [("strut side", 4.85, +1), ("domed side", -10.00, -1)])
    check(front_w, "wheel_front (x1)", FRONT["tyre"], "P39-LegFront.stl", (105.0, -30.0),
          [("outboard", 20.00, +1), ("inboard", 7.50, -1)])

    print()
    check_tyre(main_w, main_t, "tyre_main (x2)", MAIN)
    check_tyre(front_w, front_t, "tyre_front (x1)", FRONT)

    preview([("wheel_main  D56", main_w), ("wheel_front  D45", front_w),
             ("tyre_main  D56", main_t), ("tyre_front  D45", front_t)],
            OUT / "wheels_preview.png")

    shank_free = 17.7 - WIDTH
    print(f"\nbolt check: shank 17.7 - rim {WIDTH} = {shank_free:.1f} mm end float")
    for leg_name, hub_t in (("main", 14.79), ("front", 12.50)):
        print(f"   {leg_name} leg: thread 20.3 - hub {hub_t} = {20.3 - hub_t:.2f} mm "
              f"for washer+nut (M4 nut 3.2 + washer 0.8 = 4.0)")


if __name__ == "__main__":
    main()
