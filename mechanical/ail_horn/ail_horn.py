import numpy as np, trimesh

SRC = "/Users/ismailbayram/Downloads/Bell P-39 Airacobra RC Model Plane/files/"
OUT = "/Users/ismailbayram/maker/iso_u_01/mechanical/ail_horn/"

WIRE_D   = 2.6     # modelled wire hole dia; this printer loses ~0.5 mm on holes -> ~2.1 printed.
                   # Fit does not matter: the M3 set screw clamps the wire, the bore is only a guide.
OLD_D    = 2.30    # plug dia, slightly over the original 2.268 (fills the stock hole before recutting)
SET_D    = 2.5     # M3 self-tapping pilot
HY, HZ   = 121.507, 4.544   # wire hole axis (Y,Z)
SET_Y    = 120.6            # set-screw axis Y (clears the 3 mm slot at Y=122.10)
SET_Z_END= 4.2              # screw tip stops just past wire centre

def cyl(d, axis, a, b, c1, c2):
    """cylinder of dia d along `axis`, from a to b, centred at (c1,c2) in the other two axes"""
    m = trimesh.creation.cylinder(radius=d/2.0, height=b-a, sections=96)
    T = np.eye(4)
    if axis == 0:
        T[:3,:3] = trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])[:3,:3]
        T[:3,3] = [(a+b)/2.0, c1, c2]
    elif axis == 2:
        T[:3,3] = [c1, c2, (a+b)/2.0]
    m.apply_transform(T)
    return m

def rework(name, sign):
    m = trimesh.load(SRC + name)
    x0, x1 = (1.0, 10.0) if sign > 0 else (-10.0, -1.0)
    sx = 5.5 * sign

    m = m.union(cyl(OLD_D,  0, x0, x1, HY, HZ))                  # fill old sloppy hole
    m = m.difference(cyl(WIRE_D, 0, x0-1, x1+1, HY, HZ))         # new snug wire hole
    m = m.difference(cyl(SET_D,  2, SET_Z_END, 16.0, sx, SET_Y)) # M3 set-screw hole

    m.process(validate=True)
    m.export(OUT + name.replace(".stl", "-v2.stl"))
    print(f"{name}: watertight={m.is_watertight} vol={m.volume:.1f}mm3 bbox={m.bounds.round(2).tolist()}")
    return m

import os; os.makedirs(OUT, exist_ok=True)
L = rework("P39-AilHornL.stl",  1)
R = rework("P39-AilHornR.stl", -1)
