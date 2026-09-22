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
OUTER_X = (-7.0, 143.0)
OUTER_Y = (-3.37, 138.63)
EDGE_R = 3.0
PLAN_R = 14.0
DRAFT_DEG = 5.0

# --- board cavity ---------------------------------------------------------
CAVITY_X = (0.0, 136.0)
CAVITY_Y = (-0.37, 135.63)
CAVITY_R = 4.0

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


def outer_skin(inset=0.0):
    """The controller's outer surface, offset inward by `inset` millimetres."""
    high_z = LID_TOP_Z - EDGE_R
    low_z = SHELL_BOTTOM_Z + EDGE_R
    # The wall is the common tangent of the two sphere rings, so it runs
    # parallel to the line joining their centres. The offset is therefore
    # measured over the centre separation, not the part's full height.
    draft = math.tan(math.radians(DRAFT_DEG)) * (high_z - low_z)
    levels = (
        (OUTER_X[0], OUTER_X[1], OUTER_Y[0], OUTER_Y[1], high_z),
        (OUTER_X[0] + draft, OUTER_X[1] - draft,
         OUTER_Y[0] + draft, OUTER_Y[1] - draft, low_z),
    )
    chain = []
    for x0, x1, y0, y1, z in levels:
        for px, py in rounded_rect_points(x0 + EDGE_R, x1 - EDGE_R,
                                          y0 + EDGE_R, y1 - EDGE_R,
                                          PLAN_R - EDGE_R):
            chain.append((px, py, z, EDGE_R - inset))
    return hull_of_spheres(chain)


def cavity_solid(z0, z1):
    """The prism the PCB lives in, open at the top."""
    section = mf.CrossSection(
        [rounded_rect_points(CAVITY_X[0], CAVITY_X[1],
                             CAVITY_Y[0], CAVITY_Y[1], CAVITY_R)],
        mf.FillRule.Positive,
    )
    return mf.Manifold.extrude(section, z1 - z0).translate([0.0, 0.0, z0])


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
