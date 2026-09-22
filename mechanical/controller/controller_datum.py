"""Measured geometry of the existing ISO U1 transmitter case.

Everything here is read off `old/kumanda_alt.stl` and `old/kumanda_ust.stl`
and expressed in the D frame: XY origin at the minimum corner of the old
bottom shell's bounding box (world 135.15, 14.11), Z origin at the PCB
seating plane, which is the top of the four mounting posts. X to the right,
Y toward the screen edge, Z up.

These values are the contract with the hardware. The perfboard is already
built, wired and drilled, so nothing in this module may be "improved" to
make the geometry tidier; see section 3 of the design spec.

Requirements: numpy, scipy, trimesh, manifold3d
"""

from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh
from scipy.cluster.hierarchy import fcluster, linkage

OLD_DIR = Path(__file__).parent / "old"

# World-space origin of the D frame, taken from the old bottom shell.
ALT_ORIGIN = (135.15, 14.11)

# --- Z planes -------------------------------------------------------------
SHELL_BOTTOM_Z = -20.0
FLOOR_T = 2.0
FLOOR_TOP_Z = SHELL_BOTTOM_Z + FLOOR_T
BOARD_SEAT_Z = 0.0
BOARD_T = 1.6
WALL_TOP_Z = 16.0
SCREEN_SEAT_Z = 17.0
LID_SKIRT_BOTTOM_Z = 11.0
LID_PLATE_BOTTOM_Z = 21.0
LID_TOP_Z = 23.0

# --- PCB mounting ---------------------------------------------------------
BOARD_POSTS = ((11.75, 10.96), (124.74, 10.66), (12.46, 124.34), (123.04, 124.54))
POST_OD = 5.0
POST_PILOT_D = 2.6
POST_PILOT_DEPTH = 8.0

# --- features carried over from the old lid -------------------------------
STICK_OLD = ((27.19, 50.61), (108.90, 51.39))
STICK_OLD_D = 30.0
SCREEN_CENTER = (107.44, 113.77)
SCREEN_BORE_OLD = (37.5, 12.2)
SCREEN_SHOULDER_OLD = (39.5, 14.2)

# --- antenna bore ---------------------------------------------------------
# A horizontal bore along Y through the top wall, below the board, for the
# SMA connector's antenna. Measured off the old shell's cylinder wall.
ANTENNA_CENTER = (32.993, -12.510)  # (x, z)
ANTENNA_D_OLD = 14.007  # what the old shell actually has
ANTENNA_D = 13.7  # what we cut; see the design spec

# --- micro-USB cable opening ----------------------------------------------
# The old case let the cable out through the same wide channel as the
# antenna. Its lid slot is the only part of it that pins the connector
# down, so its X range is what the new rectangular window uses.
USB_SLOT_X = (62.69, 74.29)
USB_SLOT_Z = (-2.0, 21.0)

SECTION_Z = 19.0  # a height where the old lid's bores read at full size


def load_old(path):
    """The named old STL, translated into the D frame."""
    mesh = trimesh.load(path)
    mesh.apply_translation([-ALT_ORIGIN[0], -ALT_ORIGIN[1], 0.0])
    return mesh


def to_manifold(mesh):
    return mf.Manifold(
        mf.Mesh(
            vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(mesh.faces, dtype=np.uint32),
        )
    )


def section_boxes(mesh, z):
    """Bounding boxes of every closed outline in a horizontal slice."""
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    boxes = []
    for loop in section.discrete:
        points = loop[:, :2]
        boxes.append((points.min(axis=0), points.max(axis=0)))
    return boxes


def _cluster_centres(points, max_gap):
    """Centres of point groups separated by more than `max_gap`."""
    labels = fcluster(linkage(points, "single"), max_gap, "distance")
    centres = []
    for label in np.unique(labels):
        group = points[labels == label]
        centres.append(tuple(((group.min(axis=0) + group.max(axis=0)) / 2).round(2)))
    return sorted(centres)


def measure_old_shell(path):
    """Post centres, read from the upward faces sitting on the seating plane."""
    mesh = load_old(path)
    upward = mesh.face_normals[:, 2] > 0.99
    on_seat = np.abs(mesh.triangles_center[:, 2] - BOARD_SEAT_Z) < 0.05
    points = mesh.triangles_center[upward & on_seat][:, :2]
    return {"posts": _cluster_centres(points, 8.0)}


def measure_old_lid(path):
    """Stick bores and the screen opening, read from a slice at SECTION_Z."""
    mesh = load_old(path)
    sticks = []
    screen_bore = None
    screen_shoulder = None
    for low, high in section_boxes(mesh, SECTION_Z):
        size = high - low
        centre = tuple(((low + high) / 2).round(2))
        if abs(size[0] - STICK_OLD_D) < 0.5 and abs(size[1] - STICK_OLD_D) < 0.5:
            sticks.append(centre)
        elif (abs(size[0] - SCREEN_BORE_OLD[0]) < 0.5
              and abs(size[1] - SCREEN_BORE_OLD[1]) < 0.5):
            screen_bore = centre
        elif (abs(size[0] - SCREEN_SHOULDER_OLD[0]) < 0.5
              and abs(size[1] - SCREEN_SHOULDER_OLD[1]) < 0.5):
            screen_shoulder = centre
    return {
        "sticks": sorted(sticks),
        "screen_bore": screen_bore,
        "screen_shoulder": screen_shoulder,
    }


def measure_old_antenna(path):
    """Centre and diameter of the old shell's antenna bore.

    The bore's wall is the one run of faces that is vertical to Y without
    being axis aligned — a round hole sweeps through every direction, a box
    corner does not.
    """
    mesh = load_old(path)
    normals = mesh.face_normals
    along_y = np.abs(normals[:, 1]) < 0.05
    axis_aligned = (np.abs(normals[:, 0]) > 0.999) | (np.abs(normals[:, 2]) > 0.999)
    candidates = np.where(along_y & ~axis_aligned)[0]
    labels = fcluster(linkage(mesh.triangles_center[candidates], "single"), 3.0,
                      "distance")

    best = None
    for label in np.unique(labels):
        faces = candidates[labels == label]
        points = np.asarray(mesh.vertices)[np.unique(mesh.faces[faces].ravel())]
        centre_x = (points[:, 0].min() + points[:, 0].max()) / 2
        centre_z = (points[:, 2].min() + points[:, 2].max()) / 2
        radii = np.hypot(points[:, 0] - centre_x, points[:, 2] - centre_z)
        if radii.max() - radii.min() > 0.05 or radii.max() < 3.0:
            continue  # not a circle, or too small to be the antenna
        if best is None or radii.max() > best["diameter"] / 2:
            best = {"centre": (round(float(centre_x), 3), round(float(centre_z), 3)),
                    "diameter": round(float(2 * radii.max()), 3)}
    return best
