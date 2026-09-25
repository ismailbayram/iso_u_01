"""P-39 aileron control horn: give the stock M3 bolt a captive nut.

Model axes (checked against WingL / Rudder / AilL): X = spanwise, Y = up,
Z = fore/aft.  The horn stands with its fork up and the wire boss at the bottom.

The stock part (Gnat666, thing:4527392) has two features:

  * a 2.268 mm cross bore along X at (Y 121.507, Z 4.544) - the aileron torque
    wire lives here, and it has to, because a wire running spanwise can only
    cross the part through both 3 mm cheeks;
  * a 3.000 mm slot, walls at X=4.000 and X=7.000, running up and forward from
    that bore at about 43 degrees to the top surface.  Cross section 3.00 x 3.07
    mm - an M3 channel.  The stock M3 bolt is pushed down here to jam the wire.

3.000 mm is exactly M3 major diameter, so the bolt has no thread interference,
and whatever thread it does cut is in bare PLA and strips at once.

This version changes nothing except the bolt's home:

  * a 3.4 mm clearance channel on the slot axis, so the bolt drops in freely
    whatever the printer does to the slot width;
  * a nut pocket on that axis - the slot widened locally to 5.7 mm so an M3 nut
    seats in it, opened through the inboard face because a 5.5 mm nut cannot be
    dropped down a 3 mm slot.

The wire bore is left at its original 2.268 mm; the wire already passes it.
"""
import numpy as np, trimesh, os

SRC = "/Users/ismailbayram/Downloads/Bell P-39 Airacobra RC Model Plane/files/"
OUT = "/Users/ismailbayram/maker/iso_u_01/mechanical/ail_horn/"

CY, CZ  = 121.507, 4.544        # wire bore axis (Y, Z)
SLOT_A  = np.array([0.0, 0.727, 0.686])   # slot direction, up and forward
SLOT_N  = np.array([0.0, -0.686, 0.727])  # perpendicular, in the Y-Z plane
SIDE    = np.array([1.0, 0.0, 0.0])

BOLT_D  = 3.4                   # clearance channel for the M3 bolt
NUT_W   = 5.7                   # across flats of an M3 nut + fit
NUT_T   = 2.6                   # DIN 934 M3 is 2.4 thick
NUT_S   = 3.5                   # nut centre, measured up the slot from the bore
NUT_X1  = 8.7                   # backstop: nut is 6.35 across corners, on X=5.5


def on_axis(shape, s_mid, x_mid, sign, cols):
    """place `shape` on the slot axis.

    `cols` says which world direction each of the shape's own x/y/z becomes.
    trimesh builds boxes around all three axes but cylinders along their local
    z, so the two need different column orders.
    """
    M = np.eye(4)
    M[:3, :3] = np.stack(cols, axis=1)
    M[:3, 3] = [x_mid, CY + s_mid * SLOT_A[1], CZ + s_mid * SLOT_A[2]]
    shape.apply_transform(M)
    return shape


def bolt_channel(sign):
    m = trimesh.creation.cylinder(radius=BOLT_D / 2.0, height=24.0, sections=96)
    return on_axis(m, 12.0, 5.5 * sign, sign, (SIDE, -SLOT_N, SLOT_A))


def nut_pocket(sign):
    """slot widened to take the nut, open through the inboard face"""
    lx = NUT_X1 + 1.0                       # from outside X=-1 to the backstop
    m = trimesh.creation.box(extents=[lx, NUT_T, NUT_W])
    x_mid = sign * (NUT_X1 - 1.0) / 2.0
    return on_axis(m, NUT_S, x_mid, sign, (SIDE * sign, SLOT_A, SLOT_N))


def rework(name, sign):
    m = trimesh.load(SRC + name)
    m = m.difference(bolt_channel(sign))
    m = m.difference(nut_pocket(sign))
    m.process(validate=True)
    m.export(OUT + name.replace(".stl", "-v2.stl"))
    print(f"{name}: watertight={m.is_watertight} bodies={len(m.split(only_watertight=False))} "
          f"vol={m.volume:.1f} bbox={m.bounds.round(2).tolist()}")
    return m


os.makedirs(OUT, exist_ok=True)
rework("P39-AilHornL.stl", 1)
rework("P39-AilHornR.stl", -1)
