"""Solid-modelling helpers for the ISO U1 controller case.

The outer surface is built as the convex hull of a ring of spheres laid
along the top and bottom outlines. That one trick gives the 14 mm plan
corners, the 3 mm edge rounding and the 5 degree draft in a single
operation, and it makes offsetting trivial: shrinking every sphere by the
same amount offsets the whole surface inward by that amount, which is how
the wall, the lid skirt and its running clearance are derived.

Requirements: numpy, trimesh, manifold3d, matplotlib
"""

import math

import manifold3d as mf
import numpy as np
import trimesh
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

from controller_datum import LID_TOP_Z, SHELL_BOTTOM_Z

SEGMENTS = 64
SPHERE_SEGMENTS = 24

# --- outer envelope -------------------------------------------------------
# The plan outline is not a rectangle. It is only as wide as the pocket
# needs at the screen end and opens out toward the user, where the hands
# are; FLARE is what each side gains between the two, along a squared
# curve. The board sets the narrow end and nothing else, so everything
# below it is free.
#
# Wall thickness is quoted at the top of the lid; the draft eats
# tan(5 deg) * 37 = 3.24 mm of it by the time it reaches the floor, so every
# wall has to start thicker than that or it runs out and the pocket breaks
# out through the outside of the shell.
OUTER_X = (-7.0, 143.0)  # at the screen end, where the outline is narrowest
OUTER_Y = (-6.37, 141.63)
FLARE = 13.0
EDGE_R = 3.0
PLAN_R = 14.0
DRAFT_DEG = 5.0

# The top face is a shallow barrel across X rather than a flat plate: the
# crest runs along the centre line and the face falls away toward each
# side. BARREL_DROP is how far it falls at the widest point of the body.
BARREL_DROP = 2.0
BARREL_HALF_W = 88.0
OUTLINE_STEPS = 24
OUTLINE_MAX_STEP = 4.0

# --- board cavity ---------------------------------------------------------
CAVITY_X = (0.0, 136.0)
CAVITY_Y = (-0.37, 135.63)
CAVITY_R = 4.0
MIN_WALL = 2.0

FONT = FontProperties(family="DejaVu Sans", weight="bold")


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(d, h, x, y, z):
    return mf.Manifold.cylinder(h, d / 2, d / 2, SEGMENTS).translate([x, y, z])


def rounded_rect_points(x0, x1, y0, y1, radius, per_corner=8):
    """Points along a rounded rectangle, walked counter-clockwise."""
    points = []
    corners = (
        (x1 - radius, y1 - radius, 0.0),
        (x0 + radius, y1 - radius, 90.0),
        (x0 + radius, y0 + radius, 180.0),
        (x1 - radius, y0 + radius, 270.0),
    )
    for cx, cy, start in corners:
        for step in range(per_corner + 1):
            angle = math.radians(start + 90.0 * step / per_corner)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def hull_of_spheres(chain):
    """Convex hull of spheres given as (x, y, z, radius) tuples."""
    return mf.Manifold.batch_hull([
        mf.Manifold.sphere(radius, SPHERE_SEGMENTS).translate([x, y, z])
        for x, y, z, radius in chain
    ])


def flare_at(y):
    """How far each side has opened out by the time it reaches `y`."""
    span = OUTER_Y[1] - OUTER_Y[0]
    t = max(min((OUTER_Y[1] - y) / span, 1.0), 0.0)
    return FLARE * t * t


def plan_outline(inset=0.0):
    """Points along the flared plan outline, rounded at the corners.

    Built as a raw polygon and then rounded by offsetting in and back out,
    which rounds the convex corners without having to solve for the arcs
    where the flare meets the front and back edges.
    """
    # Counter-clockwise: up the right side, across the back, down the left,
    # across the front. The two straight edges are sampled as well, so the
    # barrelled top has points to follow all the way across X.
    raw = []
    for step in range(OUTLINE_STEPS + 1):
        y = OUTER_Y[0] + (OUTER_Y[1] - OUTER_Y[0]) * step / OUTLINE_STEPS
        raw.append((OUTER_X[1] + flare_at(y), y))
    for step in range(1, OUTLINE_STEPS):
        raw.append((OUTER_X[1] - (OUTER_X[1] - OUTER_X[0]) * step / OUTLINE_STEPS,
                    OUTER_Y[1]))
    for step in range(OUTLINE_STEPS + 1):
        y = OUTER_Y[1] - (OUTER_Y[1] - OUTER_Y[0]) * step / OUTLINE_STEPS
        raw.append((OUTER_X[0] - flare_at(y), y))
    front = FLARE
    for step in range(1, OUTLINE_STEPS):
        raw.append((OUTER_X[0] - front
                    + (OUTER_X[1] - OUTER_X[0] + 2 * front) * step / OUTLINE_STEPS,
                    OUTER_Y[0]))
    section = (mf.CrossSection([raw], mf.FillRule.Positive)
               .offset(-PLAN_R, mf.JoinType.Round, 2.0, SEGMENTS)
               .offset(PLAN_R - inset, mf.JoinType.Round, 2.0, SEGMENTS))
    return _resample(max(section.to_polygons(), key=len), OUTLINE_MAX_STEP)


def _resample(points, max_step):
    """Walk a closed polygon, splitting any segment longer than `max_step`.

    Offsetting leaves straight runs with only their endpoints, which is
    fine for a flat extrusion but not here: the barrelled top needs a
    sphere every few millimetres across X or the crest has nothing to rest
    on and the roof sags to a chord between the corners.
    """
    dense = []
    count = len(points)
    for index in range(count):
        start = np.asarray(points[index], dtype=float)
        end = np.asarray(points[(index + 1) % count], dtype=float)
        dense.append(tuple(start))
        splits = int(np.linalg.norm(end - start) // max_step)
        for split in range(1, splits + 1):
            dense.append(tuple(start + (end - start) * split / (splits + 1)))
    return dense


def barrel_z(x):
    """Height of the top face's crest line at `x`."""
    t = (x - (CAVITY_X[0] + CAVITY_X[1]) / 2) / BARREL_HALF_W
    return LID_TOP_Z - BARREL_DROP * t * t


def outer_skin(inset=0.0):
    """The controller's outer surface, offset inward by `inset` millimetres.

    Two rings of spheres: one under the barrelled top face, one just above
    the flat underside and pulled in by the draft. Their convex hull is the
    whole envelope — the barrel comes out of varying the top ring's height
    with X, since a cylinder along Y is exactly the hull of its own profile.
    """
    high_z = LID_TOP_Z - EDGE_R
    low_z = SHELL_BOTTOM_Z + EDGE_R
    # The wall is the common tangent of the two rings, so it runs parallel
    # to the line joining their centres. The offset is therefore measured
    # over the centre separation, not the part's full height.
    draft = math.tan(math.radians(DRAFT_DEG)) * (high_z - low_z)

    chain = []
    for px, py in plan_outline(EDGE_R):
        chain.append((px, py, barrel_z(px) - EDGE_R, EDGE_R - inset))
    for px, py in plan_outline(EDGE_R + draft):
        chain.append((px, py, low_z, EDGE_R - inset))
    return hull_of_spheres(chain)


def lowered_skin(depth):
    """The skin with its top face dropped by `depth`.

    Subtract this from a feature and what is left is a cut exactly `depth`
    deep measured down from the top face, wherever the feature lands. On a
    barrelled top face that is the only way a recess, a deboss or a
    counterbore keeps its depth: cut to a fixed plane instead and it runs
    out through the edge at one end and never reaches the surface at the
    other.

    Offsetting the skin inward instead would shave the sides too, and a
    feature that reaches the edge of the part — a screw counterbore, say —
    would slice a sliver off the wall on its way past.
    """
    return outer_skin().translate([0.0, 0.0, -depth])


def cavity_solid(z0, z1):
    """The pocket the PCB lives in, open at the top.

    Clipped against the outer surface offset inward by MIN_WALL. A straight
    prism would break out of the shell near the floor: the draft pulls the
    outer surface in by 3.24 mm over the part's height, which is more than
    the 3 mm the front and back walls start with, so the pocket ends up
    outside the skin and the floor opens along both edges. Clipping tapers
    the pocket instead, below the board where the room is not needed.
    """
    section = mf.CrossSection(
        [rounded_rect_points(CAVITY_X[0], CAVITY_X[1],
                             CAVITY_Y[0], CAVITY_Y[1], CAVITY_R)],
        mf.FillRule.Positive,
    )
    prism = mf.Manifold.extrude(section, z1 - z0).translate([0.0, 0.0, z0])
    return prism ^ outer_skin(MIN_WALL)


DISH_SPHERE_SEGMENTS = 256


def spherical_dish(x, y, top_z, diameter, depth):
    """A shallow spherical cap to subtract from a face at `top_z`.

    Cut from a real sphere rather than hulled from a stack of discs. The
    hulled version produced a solid that looked right and measured right,
    but subtracting it from a plate that already had a hole through it left
    a stray face roofing the hole over — invisible to any volume check,
    fatal on the printer. The sphere is large and coarsely faceted, but
    over a cap this shallow the chord error is under 0.02 mm.
    """
    radius = ((diameter / 2) ** 2 + depth ** 2) / (2 * depth)
    ball = mf.Manifold.sphere(radius, DISH_SPHERE_SEGMENTS).translate(
        [x, y, top_z - depth + radius])
    cap = ball ^ cyl(diameter, 4 * radius, x, y, top_z - depth)
    return cap + cyl(diameter, 5.0, x, y, top_z)


def text_solid(text, size, x, y, z0, z1, align="center"):
    """Extruded glyph outlines, centred on (x, y) when align is "center"."""
    path = TextPath((0, 0), text, size=size, prop=FONT)
    polygons = [[tuple(point) for point in polygon] for polygon in path.to_polygons()]
    section = mf.CrossSection(polygons, mf.FillRule.EvenOdd)
    solid = mf.Manifold.extrude(section, z1 - z0).translate([0.0, 0.0, z0])
    low_x, low_y, _, high_x, high_y, _ = solid.bounding_box()
    if align == "center":
        return solid.translate([x - (low_x + high_x) / 2, y - (low_y + high_y) / 2, 0.0])
    return solid.translate([x, y, 0.0])


def section_width(solid, z):
    """X extent of a horizontal slice; used by the draft test."""
    mesh = to_trimesh(solid)
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    points = np.vstack([loop[:, 0] for loop in section.discrete])
    return float(points.max() - points.min())


def to_trimesh(solid):
    """Wrap a Manifold's mesh without letting trimesh touch it.

    `process=True` would merge vertices that manifold3d deliberately keeps
    apart — two surfaces meeting at a point get welded into a non-manifold
    edge, and the result stops being watertight.
    """
    mesh = solid.to_mesh()
    return trimesh.Trimesh(vertices=mesh.vert_properties[:, :3],
                           faces=mesh.tri_verts, process=False)
