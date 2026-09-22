# Kumanda Kutusu v2 — Implementasyon Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ISO U1 kumandasının kutusunu, içindeki elle lehimlenmiş 133 mm'lik karta hiç dokunmadan yeniden çizmek: dört baskı parçası üreten parametrik bir Python script'i yazmak.

**Architecture:** Bütün geometri `manifold3d` ile CSG olarak kurulur. Dış kabuk, üst ve alt dış hat boyunca dizilmiş küre kümesinin dışbükey kabuğudur; kürelerin yarıçapını düşürmek kabuğu içeri ofsetler, böylece duvar kalınlığı, kapak eteği ve geçme boşluğu tek bir fonksiyondan çıkar. Karta bağlı bütün ölçüler eski STL'lerden okunup adlandırılmış sabit olarak durur; anten/USB kanalı ise yorumlanmadan, eski gövdeden boolean ile kopyalanır.

**Tech Stack:** Python 3.14, `manifold3d`, `numpy`, `trimesh`, `scipy` (küme analizi), `matplotlib` (yazı dış hatları + önizleme), `Pillow` (önizleme), `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-22-controller-case-design.md`

## Global Constraints

- **D çerçevesi.** XY orijini eski `kumanda_alt.stl`'in sınır kutusu minimum köşesi (dünya 135.15, 14.11), Z orijini kart oturma düzlemi. Bütün kod bu çerçevede çalışır.
- **Karta bağlı ölçüler değiştirilemez.** Direk koordinatları, joystick X merkezleri, ekran merkezi, anten/USB kanalı. Spec Bölüm 3.
- **Z düzlemleri:** gövde tabanı −20.0, iç zemin −18.0, kart oturma 0.0, kart üstü 1.6, duvar üstü 16.0, ekran omzu 17.0, kapak eteği altı 11.0, kapak plakası altı 21.0, kapak üstü 23.0.
- **Dış gövde** 150.0 × 142.0 mm, D'de x = −7.0 … 143.0, y = −3.37 … 138.63. Plan köşesi R14, kenar yuvarlaması R3, yan duvar eğimi 5°.
- **Kart cebi** 136.0 × 136.0, D'de x = 0.0 … 136.0, y = −0.37 … 135.63, köşe R4. (R6 olsaydı yuvarlatma kartın köşelerini keserdi: kart köşesi cep köşesinden (1.5, 1.5) içeride, yayın merkezine uzaklık 3.54 mm.)
- **Kod stili:** `mechanical/` altındaki diğer parçalarla aynı — modül başında docstring, bütün ölçüler modül seviyesinde adlandırılmış sabit, `build_*()` fonksiyonları, `main()` içinde `argparse`. Hiçbir ölçü fonksiyon gövdesine gömülmez.
- **Her parça** su geçirmez (`is_watertight`) ve tek gövde (`body_count == 1`) olmalı.
- Bütün komutlar repo kökünden (`/Users/ismailbayram/maker/iso_u_01`) çalıştırılır.

---

## Dosya Yapısı

| Dosya | Sorumluluk |
|---|---|
| `mechanical/controller/controller_datum.py` | Eski STL'lerden okunan ölçüler (sabitler) ve onları yeniden ölçen fonksiyonlar. Donanımla sözleşme. |
| `mechanical/controller/controller_geom.py` | Katı modelleme yardımcıları: kutu, silindir, yuvarlatılmış dikdörtgen, küre kabuğu, küresel çukur, yazı, `to_trimesh`. Hiçbir parçaya özel bilgi içermez. |
| `mechanical/controller/controller_case.py` | `build_shell()`, `build_lid()`, `build_grip()`, `build_shim()`, `check_against_old()`, `render_preview()`, `main()`. |
| `mechanical/controller/test_controller_case.py` | pytest. Ölçüm doğrulaması, geometri değişmezleri, eski parçaya göre regresyon. |

---

## Task 1: Ölçüm modülü

**Files:**
- Create: `mechanical/controller/controller_datum.py`
- Test: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: hiçbir şey.
- Produces: sabitler `ALT_ORIGIN`, `SHELL_BOTTOM_Z`, `FLOOR_TOP_Z`, `BOARD_SEAT_Z`, `BOARD_T`, `WALL_TOP_Z`, `SCREEN_SEAT_Z`, `LID_SKIRT_BOTTOM_Z`, `LID_PLATE_BOTTOM_Z`, `LID_TOP_Z`, `BOARD_POSTS`, `POST_OD`, `POST_PILOT_D`, `POST_PILOT_DEPTH`, `STICK_OLD`, `STICK_OLD_D`, `SCREEN_CENTER`, `SCREEN_BORE_OLD`, `SCREEN_SHOULDER_OLD`, `CHANNEL_REGION`, `CHANNEL_EXTENSION`, `CABLE_SLOT`, `OLD_DIR`; fonksiyonlar `load_old(path) -> trimesh.Trimesh`, `to_manifold(mesh) -> manifold3d.Manifold`, `section_boxes(mesh, z) -> list[tuple[np.ndarray, np.ndarray]]`, `measure_old_shell(path) -> dict`, `measure_old_lid(path) -> dict`.

- [ ] **Step 1: pytest'i kur**

```bash
pip install pytest
```

- [ ] **Step 2: Testi yaz**

`mechanical/controller/test_controller_case.py` oluştur:

```python
"""Geometry regression tests for the ISO U1 controller case.

Run from the repository root:  pytest mechanical/controller -q
"""

import math
from pathlib import Path

import numpy as np
import pytest

import controller_datum as datum

OLD_SHELL = datum.OLD_DIR / "kumanda_alt.stl"
OLD_LID = datum.OLD_DIR / "kumanda_ust.stl"


def test_old_shell_posts_match_constants():
    measured = datum.measure_old_shell(OLD_SHELL)["posts"]
    expected = sorted(datum.BOARD_POSTS)
    assert len(measured) == 4
    for got, want in zip(measured, expected):
        assert got[0] == pytest.approx(want[0], abs=0.10)
        assert got[1] == pytest.approx(want[1], abs=0.10)


def test_old_lid_sticks_match_constants():
    measured = datum.measure_old_lid(OLD_LID)["sticks"]
    expected = sorted(datum.STICK_OLD)
    assert len(measured) == 2
    for got, want in zip(measured, expected):
        assert got[0] == pytest.approx(want[0], abs=0.10)
        assert got[1] == pytest.approx(want[1], abs=0.10)


def test_old_lid_screen_matches_constants():
    measured = datum.measure_old_lid(OLD_LID)
    assert measured["screen_bore"][0] == pytest.approx(datum.SCREEN_CENTER[0], abs=0.10)
    assert measured["screen_bore"][1] == pytest.approx(datum.SCREEN_CENTER[1], abs=0.10)
    assert measured["screen_shoulder"][0] == pytest.approx(datum.SCREEN_CENTER[0], abs=0.10)
    assert measured["screen_shoulder"][1] == pytest.approx(datum.SCREEN_CENTER[1], abs=0.10)


def test_old_shell_sits_in_the_d_frame():
    mesh = datum.load_old(OLD_SHELL)
    assert mesh.bounds[0][0] == pytest.approx(0.0, abs=0.01)
    assert mesh.bounds[0][1] == pytest.approx(0.0, abs=0.01)
    assert mesh.bounds[1][2] == pytest.approx(18.0, abs=0.01)
```

Ayrıca `mechanical/controller/conftest.py` oluştur, böylece testler modülleri isimle import edebilir:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 3: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'controller_datum'`

- [ ] **Step 4: `controller_datum.py`'yi yaz**

```python
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

# --- antenna / USB channel, copied as a boolean ---------------------------
# (x0, x1, y0, y1, z0, z1)
CHANNEL_REGION = (28.0, 108.0, 126.0, 136.07, -21.0, 24.0)
CHANNEL_EXTENSION = (36.27, 103.94, 136.07, 145.0, -21.0, 24.0)
CABLE_SLOT = (62.69, 74.29, 120.37, 145.0, 20.0, 24.0)

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
```

- [ ] **Step 5: Testi çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 4 passed

- [ ] **Step 6: Commit**

```bash
git add mechanical/controller/controller_datum.py mechanical/controller/conftest.py mechanical/controller/test_controller_case.py
git commit -m "feat(mechanical): read the old controller case into a datum module"
```

---

## Task 2: Geometri yardımcıları

**Files:**
- Create: `mechanical/controller/controller_geom.py`
- Modify: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: `controller_datum` sabitleri (`SHELL_BOTTOM_Z`, `LID_TOP_Z`).
- Produces: sabitler `SEGMENTS`, `SPHERE_SEGMENTS`, `EDGE_R`, `PLAN_R`, `DRAFT_DEG`, `OUTER_X`, `OUTER_Y`, `CAVITY_X`, `CAVITY_Y`, `CAVITY_R`; fonksiyonlar `box(x0, x1, y0, y1, z0, z1)`, `cyl(d, h, x, y, z)`, `rounded_rect_points(x0, x1, y0, y1, radius, per_corner=8)`, `hull_of_spheres(chain)`, `outer_skin(inset=0.0)`, `cavity_solid(z0, z1)`, `spherical_dish(x, y, top_z, diameter, depth, steps=16)`, `text_solid(text, size, x, y, z0, z1, align="center")`, `to_trimesh(solid)`. Hepsi `manifold3d.Manifold` döndürür (`to_trimesh` hariç).

- [ ] **Step 1: Testleri yaz**

`test_controller_case.py`'nin sonuna ekle:

```python
import controller_geom as geom


def test_outer_skin_matches_the_specified_envelope():
    skin = geom.outer_skin()
    low_x, low_y, low_z, high_x, high_y, high_z = skin.bounding_box()
    assert low_x == pytest.approx(geom.OUTER_X[0], abs=0.02)
    assert high_x == pytest.approx(geom.OUTER_X[1], abs=0.02)
    assert low_y == pytest.approx(geom.OUTER_Y[0], abs=0.02)
    assert high_y == pytest.approx(geom.OUTER_Y[1], abs=0.02)
    assert low_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.02)
    assert high_z == pytest.approx(datum.LID_TOP_Z, abs=0.02)


def test_outer_skin_inset_shrinks_by_exactly_the_inset():
    inset = 2.2
    outer = geom.outer_skin().bounding_box()
    inner = geom.outer_skin(inset).bounding_box()
    for axis in range(3):
        assert inner[axis] == pytest.approx(outer[axis] + inset, abs=0.02)
        assert inner[axis + 3] == pytest.approx(outer[axis + 3] - inset, abs=0.02)


def test_outer_skin_side_walls_carry_the_draft():
    """The side wall leans in by DRAFT_DEG between the two rounded edges.

    Sampled clear of the R3 edge rounding, which pulls the section in near
    the top and bottom faces and would swamp the angle being measured.
    """
    skin = geom.outer_skin()
    high_z = datum.LID_TOP_Z - geom.EDGE_R - 1.0
    low_z = datum.SHELL_BOTTOM_Z + geom.EDGE_R + 1.0
    expected = math.tan(math.radians(geom.DRAFT_DEG)) * (high_z - low_z)
    top = geom.section_width(skin, high_z)
    bottom = geom.section_width(skin, low_z)
    assert (top - bottom) / 2 == pytest.approx(expected, abs=0.05)


def test_spherical_dish_has_the_asked_for_depth_and_diameter():
    dish = geom.spherical_dish(0.0, 0.0, 0.0, 46.0, 1.2)
    low_x, low_y, low_z, high_x, high_y, high_z = dish.bounding_box()
    assert high_x - low_x == pytest.approx(46.0, abs=0.4)
    assert low_z == pytest.approx(-1.2, abs=0.02)


def test_text_solid_is_not_empty_and_lands_where_asked():
    solid = geom.text_solid("ISO U1", 10.0, 68.0, 20.0, 0.0, 0.6)
    low_x, low_y, low_z, high_x, high_y, high_z = solid.bounding_box()
    assert solid.volume() > 10.0
    assert (low_x + high_x) / 2 == pytest.approx(68.0, abs=0.5)
    assert low_z == pytest.approx(0.0, abs=0.01)
    assert high_z == pytest.approx(0.6, abs=0.01)
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'controller_geom'`

- [ ] **Step 3: `controller_geom.py`'yi yaz**

```python
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
    draft = math.tan(math.radians(DRAFT_DEG)) * (LID_TOP_Z - SHELL_BOTTOM_Z)
    levels = (
        (OUTER_X[0], OUTER_X[1], OUTER_Y[0], OUTER_Y[1], LID_TOP_Z - EDGE_R),
        (OUTER_X[0] + draft, OUTER_X[1] - draft,
         OUTER_Y[0] + draft, OUTER_Y[1] - draft, SHELL_BOTTOM_Z + EDGE_R),
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


def spherical_dish(x, y, top_z, diameter, depth, steps=16):
    """A shallow spherical cap to subtract from a face at `top_z`.

    Built as the hull of a stack of discs following the sphere's profile,
    which keeps the mesh small: a true sphere of the required radius would
    need thousands of segments to stay smooth over this little cap.
    """
    radius = ((diameter / 2) ** 2 + depth ** 2) / (2 * depth)
    centre_z = top_z - depth + radius
    discs = []
    for step in range(steps + 1):
        z = top_z - depth + depth * step / steps
        r = math.sqrt(max(radius ** 2 - (centre_z - z) ** 2, 0.0))
        discs.append(cyl(max(2 * r, 0.05), 0.02, x, y, z))
    discs.append(cyl(diameter, 0.02, x, y, top_z + 5.0))
    return mf.Manifold.batch_hull(discs)


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
    mesh = solid.to_mesh()
    return trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 9 passed

- [ ] **Step 5: Commit**

```bash
git add mechanical/controller/controller_geom.py mechanical/controller/test_controller_case.py
git commit -m "feat(mechanical): add the case's solid-modelling helpers"
```

---

## Task 3: Gövde

**Files:**
- Create: `mechanical/controller/controller_case.py`
- Modify: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: `controller_geom`'un tamamı, `controller_datum`'un sabitleri ve `load_old` / `to_manifold`.
- Produces: sabitler `SKIRT_T`, `SKIRT_GAP`, `LID_SCREWS`, `LID_SCREW_BOSS_D`, `LID_SCREW_PILOT_D`, `LID_SCREW_PILOT_DEPTH`, `GRIP_SCREWS`, `GRIP_PAD_D`, `GRIP_PAD_TOP_Z`, `GRIP_PILOT_D`, `GRIP_PILOT_DEPTH`, `SHELL_TEXT`, `SHELL_TEXT_SIZE`, `SHELL_TEXT_POS`, `TEXT_DEPTH`; fonksiyonlar `shell_outer_surface()`, `antenna_channel()`, `build_shell()`. `build_shell()` `manifold3d.Manifold` döndürür.

- [ ] **Step 1: Testleri yaz**

`test_controller_case.py`'nin sonuna ekle:

```python
import controller_case as case


@pytest.fixture(scope="module")
def shell():
    return case.build_shell()


def test_shell_is_a_single_watertight_body(shell):
    mesh = geom.to_trimesh(shell)
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_shell_occupies_the_specified_envelope(shell):
    low_x, low_y, low_z, high_x, high_y, high_z = shell.bounding_box()
    assert low_x == pytest.approx(geom.OUTER_X[0], abs=0.05)
    assert high_x == pytest.approx(geom.OUTER_X[1], abs=0.05)
    assert low_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.05)
    assert high_z == pytest.approx(datum.WALL_TOP_Z, abs=0.05)


def test_shell_leaves_room_for_the_board(shell):
    """A 133 mm slab at the seating plane must not touch the shell."""
    centre_x = sum(p[0] for p in datum.BOARD_POSTS) / 4
    centre_y = sum(p[1] for p in datum.BOARD_POSTS) / 4
    board = geom.box(centre_x - 66.5, centre_x + 66.5,
                     centre_y - 66.5, centre_y + 66.5,
                     datum.BOARD_SEAT_Z, datum.BOARD_SEAT_Z + datum.BOARD_T)
    assert (board ^ shell).volume() == pytest.approx(0.0, abs=1.0)


def test_shell_posts_reach_the_seating_plane(shell):
    mesh = geom.to_trimesh(shell)
    boxes = datum.section_boxes(mesh, datum.BOARD_SEAT_Z - 0.5)
    posts = [((low + high) / 2).round(2) for low, high in boxes
             if abs((high - low)[0] - datum.POST_OD) < 0.6
             and abs((high - low)[1] - datum.POST_OD) < 0.6]
    assert len(posts) == 4
    for got in sorted(tuple(p) for p in posts):
        assert min(math.dist(got, want) for want in datum.BOARD_POSTS) < 0.2


def test_shell_keeps_the_antenna_channel_open(shell):
    """Everything the old shell left open in the channel region stays open."""
    old = datum.to_manifold(datum.load_old(datum.OLD_DIR / "kumanda_alt.stl"))
    opening = geom.box(*datum.CHANNEL_REGION) - old
    assert (opening ^ shell).volume() == pytest.approx(0.0, abs=1.0)


def test_shell_has_four_lid_screw_pilots(shell):
    mesh = geom.to_trimesh(shell)
    boxes = datum.section_boxes(mesh, datum.WALL_TOP_Z - 2.0)
    pilots = [((low + high) / 2).round(2) for low, high in boxes
              if abs((high - low)[0] - case.LID_SCREW_PILOT_D) < 0.4]
    assert len(pilots) == 4
    for got in sorted(tuple(p) for p in pilots):
        assert min(math.dist(got, want) for want in case.LID_SCREWS) < 0.2
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'controller_case'`

- [ ] **Step 3: `controller_case.py`'nin gövde bölümünü yaz**

```python
"""The ISO U1 transmitter case: shell, lid, two grips and the screen shim.

The perfboard inside is hand-built and already drilled, so every feature the
board dictates comes from `controller_datum` and is never recomputed here.
What this module is free to shape is the outer form: a drafted, rounded
shell, thumb dishes around the sticks, debossed lettering, and two bolt-on
grips.

Coordinates: the D frame described in `controller_datum`.

Requirements: numpy, scipy, trimesh, manifold3d, matplotlib, Pillow
Usage:        python controller_case.py [--check] [--out DIR]
"""

import argparse
import math
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

import controller_datum as datum
import controller_geom as geom
from controller_geom import box, cyl

# --- lid interface --------------------------------------------------------
SKIRT_T = 2.0
SKIRT_GAP = 0.2

LID_SCREWS = ((-2.5, 30.0), (-2.5, 105.0), (138.5, 30.0), (138.5, 105.0))
LID_SCREW_BOSS_D = 6.0
LID_SCREW_PILOT_D = 2.5
LID_SCREW_PILOT_DEPTH = 12.0

# --- grip interface -------------------------------------------------------
GRIP_SCREWS = {
    "left": ((12.0, 8.0), (38.0, 4.0)),
    "right": ((124.0, 8.0), (98.0, 4.0)),
}
GRIP_PAD_D = 10.0
GRIP_PAD_TOP_Z = -12.0
GRIP_PILOT_D = 2.5
GRIP_PILOT_DEPTH = 7.0

# --- lettering ------------------------------------------------------------
TEXT_DEPTH = 0.6
SHELL_TEXT = "İstikbal Göklerdedir"
SHELL_TEXT_SIZE = 10.0
SHELL_TEXT_POS = (68.0, 66.0)


def shell_outer_surface():
    """The shell's outer skin: full size up to the skirt, rebated above it."""
    below = box(-40.0, 180.0, -40.0, 180.0,
                datum.SHELL_BOTTOM_Z, datum.LID_SKIRT_BOTTOM_Z)
    rebate = box(-40.0, 180.0, -40.0, 180.0,
                 datum.LID_SKIRT_BOTTOM_Z, datum.WALL_TOP_Z)
    return (geom.outer_skin() ^ below) + (geom.outer_skin(SKIRT_T + SKIRT_GAP) ^ rebate)


def antenna_channel():
    """The void the old shell left for the antenna and the USB cable."""
    old = datum.to_manifold(datum.load_old(datum.OLD_DIR / "kumanda_alt.stl"))
    return (box(*datum.CHANNEL_REGION) - old) + box(*datum.CHANNEL_EXTENSION)


def build_shell():
    outer = shell_outer_surface()
    shell = outer - geom.cavity_solid(datum.FLOOR_TOP_Z, datum.LID_TOP_Z + 10.0)

    for x, y in datum.BOARD_POSTS:
        shell += cyl(datum.POST_OD, datum.BOARD_SEAT_Z - datum.FLOOR_TOP_Z,
                     x, y, datum.FLOOR_TOP_Z)

    towers = mf.Manifold()
    for x, y in LID_SCREWS:
        towers += cyl(LID_SCREW_BOSS_D, datum.WALL_TOP_Z - datum.FLOOR_TOP_Z,
                      x, y, datum.FLOOR_TOP_Z)
    shell += towers ^ outer

    for x, y in GRIP_SCREWS["left"] + GRIP_SCREWS["right"]:
        shell += cyl(GRIP_PAD_D, GRIP_PAD_TOP_Z - datum.SHELL_BOTTOM_Z,
                     x, y, datum.SHELL_BOTTOM_Z)

    shell -= antenna_channel()

    for x, y in datum.BOARD_POSTS:
        shell -= cyl(datum.POST_PILOT_D, datum.POST_PILOT_DEPTH + 1.0, x, y,
                     datum.BOARD_SEAT_Z - datum.POST_PILOT_DEPTH)
    for x, y in LID_SCREWS:
        shell -= cyl(LID_SCREW_PILOT_D, LID_SCREW_PILOT_DEPTH + 1.0, x, y,
                     datum.WALL_TOP_Z - LID_SCREW_PILOT_DEPTH)
    for x, y in GRIP_SCREWS["left"] + GRIP_SCREWS["right"]:
        shell -= cyl(GRIP_PILOT_D, GRIP_PILOT_DEPTH + 1.0, x, y,
                     datum.SHELL_BOTTOM_Z - 1.0)

    shell -= geom.text_solid(SHELL_TEXT, SHELL_TEXT_SIZE,
                             SHELL_TEXT_POS[0], SHELL_TEXT_POS[1],
                             datum.SHELL_BOTTOM_Z - 0.01,
                             datum.SHELL_BOTTOM_Z + TEXT_DEPTH)
    return shell
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 15 passed

- [ ] **Step 5: Commit**

```bash
git add mechanical/controller/controller_case.py mechanical/controller/test_controller_case.py
git commit -m "feat(mechanical): build the controller shell"
```

---

## Task 4: Kapak

**Files:**
- Modify: `mechanical/controller/controller_case.py`
- Modify: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: Task 3'ün sabitleri (`SKIRT_T`, `LID_SCREWS`, `TEXT_DEPTH`), `antenna_channel()`.
- Produces: sabitler `STICK_NEW`, `STICK_BORE_D`, `DISH_D`, `DISH_DEPTH`, `COLLAR_OUTER`, `SCREEN_NEST`, `SCREEN_WINDOW`, `SCREEN_PANEL`, `SCREEN_PANEL_DEPTH`, `SCREEN_NEST_TOP_Z`, `LID_SCREW_CLEAR_D`, `LID_SCREW_HEAD_D`, `LID_SCREW_HEAD_DEPTH`, `LID_TEXT`, `LID_TEXT_SIZE`, `LID_TEXT_POS`; fonksiyon `build_lid()`.

- [ ] **Step 1: Testleri yaz**

`test_controller_case.py`'nin sonuna ekle:

```python
@pytest.fixture(scope="module")
def lid():
    return case.build_lid()


def test_lid_is_a_single_watertight_body(lid):
    mesh = geom.to_trimesh(lid)
    assert mesh.is_watertight
    assert mesh.body_count == 1


def test_lid_spans_the_skirt_and_the_plate(lid):
    _, _, low_z, _, _, high_z = lid.bounding_box()
    assert low_z == pytest.approx(datum.LID_SKIRT_BOTTOM_Z, abs=0.05)
    assert high_z == pytest.approx(datum.LID_TOP_Z, abs=0.05)


def test_lid_skirt_clears_the_shell(shell, lid):
    assert (shell ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_new_stick_bores_swallow_the_old_ones(lid):
    """Both old bores must fall inside the new ones, or a stick will bind."""
    for old_x, old_y in datum.STICK_OLD:
        old_bore = geom.cyl(datum.STICK_OLD_D, 6.0, old_x, old_y,
                            datum.LID_PLATE_BOTTOM_Z - 1.0)
        assert (old_bore ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_stick_bores_share_one_y_and_keep_the_measured_x(lid):
    assert case.STICK_NEW[0][1] == case.STICK_NEW[1][1]
    assert case.STICK_NEW[0][0] == pytest.approx(datum.STICK_OLD[0][0], abs=0.01)
    assert case.STICK_NEW[1][0] == pytest.approx(datum.STICK_OLD[1][0], abs=0.01)


def test_screen_module_can_rise_into_its_nest(lid):
    """A 38 x 12 x 1.6 board ending at the seat plane must not be obstructed."""
    module = geom.box(datum.SCREEN_CENTER[0] - 19.0, datum.SCREEN_CENTER[0] + 19.0,
                      datum.SCREEN_CENTER[1] - 6.0, datum.SCREEN_CENTER[1] + 6.0,
                      datum.SCREEN_SEAT_Z - datum.BOARD_T, datum.SCREEN_SEAT_Z)
    assert (module ^ lid).volume() == pytest.approx(0.0, abs=1.0)


def test_screen_window_is_smaller_than_the_module(lid):
    """The lip is what stops the module passing through the window."""
    assert case.SCREEN_WINDOW[0] < 38.0
    assert case.SCREEN_WINDOW[1] < 12.0
    mesh = geom.to_trimesh(lid)
    boxes = datum.section_boxes(mesh, datum.LID_TOP_Z - 0.5)
    windows = [high - low for low, high in boxes
               if abs((high - low)[0] - case.SCREEN_WINDOW[0]) < 0.4]
    assert len(windows) == 1


def test_lid_keeps_the_antenna_channel_open(lid):
    old = datum.to_manifold(datum.load_old(datum.OLD_DIR / "kumanda_alt.stl"))
    opening = geom.box(*datum.CHANNEL_REGION) - old
    assert (opening ^ lid).volume() == pytest.approx(0.0, abs=1.0)
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `AttributeError: module 'controller_case' has no attribute 'build_lid'`

- [ ] **Step 3: Kapağı yaz**

`controller_case.py`'de `SHELL_TEXT_POS` satırından sonra sabitleri ekle:

```python
# --- lid ------------------------------------------------------------------
STICK_NEW = ((datum.STICK_OLD[0][0], 51.00), (datum.STICK_OLD[1][0], 51.00))
STICK_BORE_D = 33.0
DISH_D = 46.0
DISH_DEPTH = 1.2

COLLAR_OUTER = (44.2, 18.2)
SCREEN_NEST = (39.2, 13.2)
SCREEN_NEST_TOP_Z = datum.SCREEN_SEAT_Z
SCREEN_WINDOW = (36.5, 10.5)
SCREEN_PANEL = (46.0, 20.0)
SCREEN_PANEL_DEPTH = 1.0

LID_SCREW_CLEAR_D = 3.4
LID_SCREW_HEAD_D = 6.0
LID_SCREW_HEAD_DEPTH = 0.8  # the plate is only 2.0 mm thick

LID_TEXT = "ISO U1"
LID_TEXT_SIZE = 10.0
LID_TEXT_POS = (68.0, 20.0)
```

Ve `build_shell()`'den sonra:

```python
def _centred_box(centre, size, z0, z1):
    half_x, half_y = size[0] / 2, size[1] / 2
    return box(centre[0] - half_x, centre[0] + half_x,
               centre[1] - half_y, centre[1] + half_y, z0, z1)


def build_lid():
    band = box(-40.0, 180.0, -40.0, 180.0, datum.LID_SKIRT_BOTTOM_Z, datum.LID_TOP_Z)
    hollow = box(-40.0, 180.0, -40.0, 180.0,
                 datum.LID_SKIRT_BOTTOM_Z - 1.0, datum.LID_PLATE_BOTTOM_Z)
    lid = (geom.outer_skin() ^ band) - (geom.outer_skin(SKIRT_T) ^ hollow)

    # Overlaps the plate by 0.5 mm; a coplanar union would be degenerate.
    collar = _centred_box(datum.SCREEN_CENTER, COLLAR_OUTER,
                          datum.WALL_TOP_Z, datum.LID_PLATE_BOTTOM_Z + 0.5)
    lid += collar
    lid -= _centred_box(datum.SCREEN_CENTER, SCREEN_NEST,
                        datum.WALL_TOP_Z - 1.0, SCREEN_NEST_TOP_Z)
    lid -= _centred_box(datum.SCREEN_CENTER, SCREEN_WINDOW,
                        SCREEN_NEST_TOP_Z, datum.LID_TOP_Z + 1.0)
    lid -= _centred_box(datum.SCREEN_CENTER, SCREEN_PANEL,
                        datum.LID_TOP_Z - SCREEN_PANEL_DEPTH, datum.LID_TOP_Z + 1.0)

    for x, y in STICK_NEW:
        lid -= cyl(STICK_BORE_D, 8.0, x, y, datum.LID_PLATE_BOTTOM_Z - 2.0)
        lid -= geom.spherical_dish(x, y, datum.LID_TOP_Z, DISH_D, DISH_DEPTH)

    for x, y in LID_SCREWS:
        lid -= cyl(LID_SCREW_CLEAR_D, 6.0, x, y, datum.LID_PLATE_BOTTOM_Z - 1.0)
        lid -= cyl(LID_SCREW_HEAD_D, LID_SCREW_HEAD_DEPTH + 1.0, x, y,
                   datum.LID_TOP_Z - LID_SCREW_HEAD_DEPTH)

    lid -= antenna_channel()
    lid -= box(*datum.CABLE_SLOT)
    lid -= geom.text_solid(LID_TEXT, LID_TEXT_SIZE, LID_TEXT_POS[0], LID_TEXT_POS[1],
                           datum.LID_TOP_Z - TEXT_DEPTH, datum.LID_TOP_Z + 0.01)
    return lid
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 23 passed

- [ ] **Step 5: Commit**

```bash
git add mechanical/controller/controller_case.py mechanical/controller/test_controller_case.py
git commit -m "feat(mechanical): build the controller lid"
```

---

## Task 5: Kabzalar

**Files:**
- Modify: `mechanical/controller/controller_case.py`
- Modify: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: `GRIP_SCREWS`, `geom.hull_of_spheres`, `geom.outer_skin`.
- Produces: sabitler `GRIP_CHAIN_LEFT`, `GRIP_MIRROR_X`, `GRIP_WALL`, `GRIP_SOLID_ROOT_Z`, `GRIP_CLEAR_D`, `GRIP_HEAD_D`, `GRIP_HEAD_Z`; fonksiyonlar `grip_chain(side)`, `grip_envelope(side)`, `build_grip(side)`. `side` yalnızca `"left"` veya `"right"`.

- [ ] **Step 1: Testleri yaz**

`test_controller_case.py`'nin sonuna ekle:

```python
@pytest.fixture(scope="module")
def grips():
    return {side: case.build_grip(side) for side in ("left", "right")}


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_is_a_single_watertight_body(grips, side):
    mesh = geom.to_trimesh(grips[side])
    assert mesh.is_watertight
    assert mesh.body_count == 1


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_stays_below_the_shell(grips, side):
    _, _, low_z, _, _, high_z = grips[side].bounding_box()
    assert high_z == pytest.approx(datum.SHELL_BOTTOM_Z, abs=0.05)
    assert low_z == pytest.approx(-38.0, abs=0.5)


def test_grips_reach_the_specified_width(grips):
    low_x = grips["left"].bounding_box()[0]
    high_x = grips["right"].bounding_box()[3]
    assert low_x == pytest.approx(-25.0, abs=0.5)
    assert high_x == pytest.approx(161.0, abs=0.5)
    assert high_x - low_x == pytest.approx(186.0, abs=1.0)


def test_grips_are_mirror_images(grips):
    left = grips["left"].bounding_box()
    right = grips["right"].bounding_box()
    assert left[0] + right[3] == pytest.approx(case.GRIP_MIRROR_X, abs=0.05)
    assert left[1] == pytest.approx(right[1], abs=0.05)


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_does_not_intersect_the_shell(shell, grips, side):
    assert (shell ^ grips[side]).volume() == pytest.approx(0.0, abs=1.0)


@pytest.mark.parametrize("side", ["left", "right"])
def test_grip_screw_seats_are_deep_enough_to_take_an_m3x14(side):
    """Each seat needs 10 mm of grip below the shell's underside.

    Measured against the grip's envelope, not the finished part: the head
    counterbore has already hollowed out the volume the screw head needs.
    """
    envelope = case.grip_envelope(side)
    for x, y in case.GRIP_SCREWS[side]:
        probe = geom.cyl(case.GRIP_HEAD_D, 0.5, x, y, case.GRIP_HEAD_Z)
        assert (probe - envelope).volume() == pytest.approx(0.0, abs=0.3)
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `AttributeError: module 'controller_case' has no attribute 'build_grip'`

- [ ] **Step 3: Kabzayı yaz**

`controller_case.py`'ye sabitleri ekle:

```python
# --- grips ----------------------------------------------------------------
# (x, y, z, radius); hulled together, then cut off at the shell's underside.
GRIP_CHAIN_LEFT = (
    (30.0, 14.0, -22.0, 16.0),
    (20.0, 3.0, -24.0, 14.0),
    (8.0, -8.0, -26.0, 12.0),
    (-5.0, -17.0, -28.0, 10.0),
    (-17.0, -25.0, -30.0, 8.0),
)
GRIP_MIRROR_X = 136.0
GRIP_WALL = 2.5
GRIP_SOLID_ROOT_Z = -30.0
GRIP_CLEAR_D = 3.4
GRIP_HEAD_D = 6.5
GRIP_HEAD_Z = -30.0
```

Ve `build_lid()`'den sonra:

```python
def grip_chain(side):
    if side == "left":
        return GRIP_CHAIN_LEFT
    return tuple((GRIP_MIRROR_X - x, y, z, r) for x, y, z, r in GRIP_CHAIN_LEFT)


def grip_envelope(side):
    """The grip's outer solid, before it is hollowed or drilled."""
    return geom.hull_of_spheres(grip_chain(side))


def build_grip(side):
    chain = grip_chain(side)
    outer = grip_envelope(side)
    inner = geom.hull_of_spheres(
        tuple((x, y, z, r - GRIP_WALL) for x, y, z, r in chain))
    below = box(-60.0, 200.0, -60.0, 200.0, -60.0, datum.SHELL_BOTTOM_Z)
    root = box(-60.0, 200.0, -60.0, 200.0, GRIP_SOLID_ROOT_Z, datum.SHELL_BOTTOM_Z)

    grip = ((outer - inner) + (outer ^ root)) ^ below

    for x, y in GRIP_SCREWS[side]:
        grip -= cyl(GRIP_CLEAR_D, datum.SHELL_BOTTOM_Z - GRIP_HEAD_Z + 1.0,
                    x, y, GRIP_HEAD_Z)
        grip -= cyl(GRIP_HEAD_D, 4.0, x, y, GRIP_HEAD_Z - 0.5)
    return grip
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 34 passed

- [ ] **Step 5: Commit**

```bash
git add mechanical/controller/controller_case.py mechanical/controller/test_controller_case.py
git commit -m "feat(mechanical): build the bolt-on controller grips"
```

---

## Task 6: Ekran tablası

**Files:**
- Modify: `mechanical/controller/controller_case.py`
- Modify: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: `controller_geom.box`.
- Produces: sabitler `SHIM_OUTER`, `SHIM_RIM`, `SHIM_LIP_H`, `SHIM_LIP_T`, `SHIM_NOMINAL_H`, `SHIM_HEIGHTS`; fonksiyon `build_shim(height)`. Tabla kendi yerel çerçevesinde durur: XY merkezde, taban z = 0.

- [ ] **Step 1: Testleri yaz**

`test_controller_case.py`'nin sonuna ekle:

```python
def test_shim_nominal_height_places_the_module_on_the_seat():
    """board top + shim + PCB must land exactly on the lid's shoulder."""
    board_top = datum.BOARD_SEAT_Z + datum.BOARD_T
    assert board_top + case.SHIM_NOMINAL_H + datum.BOARD_T == pytest.approx(
        datum.SCREEN_SEAT_Z, abs=0.01)


@pytest.mark.parametrize("height", [13.3, 13.8, 14.3])
def test_shim_is_a_single_watertight_body(height):
    mesh = geom.to_trimesh(case.build_shim(height))
    assert mesh.is_watertight
    assert mesh.body_count == 1


@pytest.mark.parametrize("height", [13.3, 13.8, 14.3])
def test_shim_top_face_sits_at_the_asked_for_height(height):
    shim = case.build_shim(height)
    _, _, low_z, _, _, high_z = shim.bounding_box()
    assert low_z == pytest.approx(0.0, abs=0.01)
    assert high_z == pytest.approx(height + case.SHIM_LIP_H, abs=0.01)


def test_shim_footprint_clears_the_module():
    shim = case.build_shim(case.SHIM_NOMINAL_H)
    low_x, low_y, _, high_x, high_y, _ = shim.bounding_box()
    assert high_x - low_x == pytest.approx(
        case.SHIM_OUTER[0] + 2 * case.SHIM_LIP_T, abs=0.05)
    assert high_y - low_y == pytest.approx(
        case.SHIM_OUTER[1] + case.SHIM_LIP_T, abs=0.05)


def test_shim_is_open_on_the_header_edge():
    """The pin row and its solder must pass straight through."""
    shim = case.build_shim(case.SHIM_NOMINAL_H)
    probe = geom.box(-case.SHIM_OUTER[0] / 2 + case.SHIM_RIM,
                     case.SHIM_OUTER[0] / 2 - case.SHIM_RIM,
                     -case.SHIM_OUTER[1] / 2 - case.SHIM_LIP_T - 1.0,
                     case.SHIM_OUTER[1] / 2 - case.SHIM_RIM,
                     0.0, case.SHIM_NOMINAL_H)
    assert (probe ^ shim).volume() == pytest.approx(0.0, abs=0.5)
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `AttributeError: module 'controller_case' has no attribute 'build_shim'`

- [ ] **Step 3: Tablayı yaz**

`controller_case.py`'ye sabitleri ekle:

```python
# --- screen shim ----------------------------------------------------------
SHIM_OUTER = (38.4, 12.4)
SHIM_RIM = 3.0
SHIM_LIP_H = 1.0
SHIM_LIP_T = 0.8
SHIM_NOMINAL_H = datum.SCREEN_SEAT_Z - datum.BOARD_T - (
    datum.BOARD_SEAT_Z + datum.BOARD_T)
SHIM_HEIGHTS = (SHIM_NOMINAL_H - 0.5, SHIM_NOMINAL_H, SHIM_NOMINAL_H + 0.5)
```

Ve `build_grip()`'ten sonra:

```python
def build_shim(height):
    """A little table that holds the OLED module flat on the perfboard.

    Open along one long edge so the soldered pin header and its blobs pass
    through; the other three edges are what stop the module tipping.
    """
    half_x, half_y = SHIM_OUTER[0] / 2, SHIM_OUTER[1] / 2
    shim = box(-half_x, half_x, -half_y, half_y, 0.0, height)
    shim -= box(-half_x + SHIM_RIM, half_x - SHIM_RIM,
                -half_y - 1.0, half_y - SHIM_RIM, -1.0, height + 1.0)

    lip = box(-half_x - SHIM_LIP_T, half_x + SHIM_LIP_T,
              -half_y, half_y + SHIM_LIP_T, height, height + SHIM_LIP_H)
    lip -= box(-half_x, half_x, -half_y - 1.0, half_y,
               height - 1.0, height + SHIM_LIP_H + 1.0)
    return shim + lip
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 43 passed

- [ ] **Step 5: Commit**

```bash
git add mechanical/controller/controller_case.py mechanical/controller/test_controller_case.py
git commit -m "feat(mechanical): add the OLED shim that keeps the module flat"
```

---

## Task 7: CLI, önizleme ve eski parçaya karşı doğrulama

**Files:**
- Modify: `mechanical/controller/controller_case.py`
- Modify: `mechanical/controller/test_controller_case.py`

**Interfaces:**
- Consumes: bütün `build_*` fonksiyonları.
- Produces: `PARTS` (isim → üretici eşlemesi), `check_against_old() -> list[str]`, `render_preview(parts, path)`, `main()`.

- [ ] **Step 1: Testleri yaz**

`test_controller_case.py`'nin sonuna ekle:

```python
def test_check_against_old_reports_no_problems():
    assert case.check_against_old() == []


def test_cli_writes_every_part(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "controller_case.py", "--out", str(tmp_path), "--check"],
        cwd=str(Path(case.__file__).parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    expected = {
        "controller_shell.stl",
        "controller_lid.stl",
        "controller_grip_left.stl",
        "controller_grip_right.stl",
        "screen_shim_133.stl",
        "screen_shim_138.stl",
        "screen_shim_143.stl",
        "controller_case_preview.png",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `pytest mechanical/controller -q`
Expected: FAIL, `AttributeError: module 'controller_case' has no attribute 'check_against_old'`

- [ ] **Step 3: CLI'yı, önizlemeyi ve doğrulamayı yaz**

`controller_case.py`'nin sonuna ekle:

```python
PREVIEW_SIZE = (1400, 1000)
PREVIEW_VIEWS = (
    ("top", (0.0, 0.0)),
    ("front", (-75.0, 0.0)),
    ("corner", (-60.0, 35.0)),
)


def parts():
    """Every printable part, keyed by output file stem."""
    built = {
        "controller_shell": build_shell(),
        "controller_lid": build_lid(),
        "controller_grip_left": build_grip("left"),
        "controller_grip_right": build_grip("right"),
    }
    for height in SHIM_HEIGHTS:
        built["screen_shim_%03d" % round(height * 10)] = build_shim(height)
    return built


def check_against_old():
    """Compare the new parts with the old ones; returns a list of problems."""
    problems = []
    old_shell_path = datum.OLD_DIR / "kumanda_alt.stl"
    old_lid_path = datum.OLD_DIR / "kumanda_ust.stl"

    measured_posts = datum.measure_old_shell(old_shell_path)["posts"]
    for got, want in zip(measured_posts, sorted(datum.BOARD_POSTS)):
        if math.dist(got, want) > 0.10:
            problems.append("post %s drifted from %s" % (got, want))

    measured_lid = datum.measure_old_lid(old_lid_path)
    for got, want in zip(measured_lid["sticks"], sorted(datum.STICK_OLD)):
        if abs(got[0] - want[0]) > 0.30:
            problems.append("stick X %s drifted from %s" % (got, want))
    for key in ("screen_bore", "screen_shoulder"):
        got = measured_lid[key]
        if got is None or math.dist(got, datum.SCREEN_CENTER) > 0.30:
            problems.append("%s at %s, expected %s" % (key, got, datum.SCREEN_CENTER))

    shell = build_shell()
    lid = build_lid()
    old_solid = datum.to_manifold(datum.load_old(old_shell_path))
    opening = box(*datum.CHANNEL_REGION) - old_solid
    for name, solid in (("shell", shell), ("lid", lid)):
        blocked = (opening ^ solid).volume()
        if blocked > 1.0:
            problems.append("%s blocks %.1f mm^3 of the antenna channel" % (name, blocked))

    for old_x, old_y in datum.STICK_OLD:
        old_bore = cyl(datum.STICK_OLD_D, 6.0, old_x, old_y,
                       datum.LID_PLATE_BOTTOM_Z - 1.0)
        blocked = (old_bore ^ lid).volume()
        if blocked > 1.0:
            problems.append("lid blocks %.1f mm^3 of the old stick bore at "
                            "(%.2f, %.2f)" % (blocked, old_x, old_y))
    return problems


def render_preview(built, path):
    """Three flat-shaded views, drawn back to front with Pillow."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", PREVIEW_SIZE, (28, 30, 34))
    draw = ImageDraw.Draw(image)
    meshes = [geom.to_trimesh(solid) for solid in built.values()]
    scene = trimesh.util.concatenate(meshes)
    panel_w = PREVIEW_SIZE[0] // len(PREVIEW_VIEWS)

    for index, (_, (pitch, yaw)) in enumerate(PREVIEW_VIEWS):
        rotated = scene.copy()
        rotated.apply_transform(trimesh.transformations.euler_matrix(
            math.radians(pitch), math.radians(yaw), 0.0))
        vertices = rotated.vertices
        faces = rotated.faces
        span = max(vertices[:, 0].ptp(), vertices[:, 1].ptp())
        scale = 0.8 * min(panel_w, PREVIEW_SIZE[1]) / span
        centre = vertices.mean(axis=0)
        screen = (vertices[:, :2] - centre[:2]) * [scale, -scale] + [
            panel_w * (index + 0.5), PREVIEW_SIZE[1] / 2]

        normals = rotated.face_normals
        depth = vertices[faces][:, :, 2].mean(axis=1)
        shade = np.clip(0.25 + 0.75 * np.abs(normals[:, 2]), 0.0, 1.0)
        for face_index in np.argsort(depth):
            level = int(40 + 190 * shade[face_index])
            draw.polygon([tuple(screen[v]) for v in faces[face_index]],
                         fill=(level, level, min(255, level + 12)))
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent,
                        help="directory the STLs and the preview are written to")
    parser.add_argument("--check", action="store_true",
                        help="verify the carried-over features against the old case")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    built = parts()
    for name, solid in built.items():
        mesh = geom.to_trimesh(solid)
        path = args.out / ("%s.stl" % name)
        mesh.export(path)
        print("wrote %s  volume=%.0f mm^3  watertight=%s  bodies=%d"
              % (path.name, solid.volume(), mesh.is_watertight, mesh.body_count))

    render_preview(built, args.out / "controller_case_preview.png")
    print("wrote controller_case_preview.png")

    if args.check:
        problems = check_against_old()
        for problem in problems:
            print("CHECK FAILED: %s" % problem)
        if problems:
            raise SystemExit(1)
        print("check passed: every carried-over feature is where it was")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `pytest mechanical/controller -q`
Expected: PASS, 45 passed

- [ ] **Step 5: Parçaları üret ve önizlemeye bak**

```bash
python mechanical/controller/controller_case.py --check
```

Expected: yedi STL, bir PNG, `check passed: every carried-over feature is where it was`

- [ ] **Step 6: Commit**

```bash
git add mechanical/controller/controller_case.py mechanical/controller/test_controller_case.py mechanical/controller/*.stl mechanical/controller/controller_case_preview.png
git commit -m "feat(mechanical): generate the controller case parts and preview"
```

---

## Doğrulama özeti

Plan bittiğinde şunlar doğrulanmış olur:

| Spec maddesi | Nerede doğrulanıyor |
|---|---|
| 3.2 direk koordinatları | `test_old_shell_posts_match_constants`, `test_shell_posts_reach_the_seating_plane` |
| 3.3 joystick ve ekran merkezleri | `test_old_lid_sticks_match_constants`, `test_old_lid_screen_matches_constants` |
| 3.4 anten / USB kanalı | `test_shell_keeps_the_antenna_channel_open`, `test_lid_keeps_the_antenna_channel_open` |
| 4.1 kart boşluğu | `test_shell_leaves_room_for_the_board` |
| 4.2 dış hat, eğim | `test_outer_skin_matches_the_specified_envelope`, `test_outer_skin_side_walls_carry_the_draft` |
| 4.3 joystick delikleri | `test_new_stick_bores_swallow_the_old_ones`, `test_stick_bores_share_one_y_and_keep_the_measured_x` |
| 4.4 kapak vidaları | `test_shell_has_four_lid_screw_pilots`, `test_lid_skirt_clears_the_shell` |
| 5 ekran yuvası ve tabla | `test_screen_module_can_rise_into_its_nest`, `test_screen_window_is_smaller_than_the_module`, `test_shim_*` |
| 6 kabza ölçüleri | `test_grips_reach_the_specified_width`, `test_grip_stays_below_the_shell`, `test_grips_are_mirror_images` |
| 6.1 kabza bağlantısı | `test_grip_screw_seats_are_deep_enough_to_take_an_m3x14` |
| 7 baskı yönü | `test_grip_stays_below_the_shell` (kök yüzü düz ve z = −20'de) |
| 8 çıktı dosyaları | `test_cli_writes_every_part` |

Doğrulanmayan, gözle bakılacak tek şey estetik: `controller_case_preview.png`. Kabza kavisi veya başparmak çukuru kötü görünürse `GRIP_CHAIN_LEFT` ve `DISH_D` / `DISH_DEPTH` sabitleri tek tek değiştirilip script yeniden çalıştırılır; başka hiçbir yere dokunmak gerekmez.
