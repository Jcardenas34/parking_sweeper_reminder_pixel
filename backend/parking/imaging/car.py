"""The display car: a pixel-art blue 2022 Subaru Crosstrek, side view facing right.

Everything car-specific lives here, so another model can be swapped in by editing
this one file:
- SHAPES and the wheel geometry define the side view as continuous shapes in
  sprite coordinates. material_at() reads them at any point. render() samples it at
  pixel centres to get the 64x24 sprite, and side_color() samples it finely for
  high-resolution renders (imaging/hires.py). The sprite and the hi-res side
  therefore always agree.
- WIDTH, the tumblehome, PROFILE and the face textures give views.py what it needs
  to build the 3D body for the front and 45-degree rear views.

Crosstrek cues: high ride height, black cladding round the wheel arches and along
the sills and bumpers, roof rails, a near-upright liftgate with a roof spoiler, a
hexagonal grille, C-shaped head and tail lights, and big 17" wheels.

Sprite coordinates: pixel (x, y) is centred on the point (x, y). The tyres touch the
ground at the bottom of row 22. views.py places a PROFILE point (x, y) at X = x, Z = 23 - y.
"""

from __future__ import annotations

import math
from typing import Callable

from PIL import Image

W, H = 64, 24

# Material ids.
(EMPTY, BODY, GLASS, TRIM, TIRE, RIM, SPOKE, HEAD, TAIL, FOG, HANDLE, REFLECT, HUB,
 CLAD, WELL, SIDEWALL) = range(16)

RGB = tuple[int, int, int]

# "Lapis Blue Pearl"-style ramp, darkest to brightest.
BLUE_DARK = (14, 30, 86)
BLUE = (30, 62, 168)
BLUE_LIGHT = (58, 104, 222)
BLUE_HI = (150, 182, 244)
OUTLINE = (8, 10, 24)

COLORS: dict[int, RGB] = {
    GLASS: (22, 34, 58),
    REFLECT: (110, 170, 220),
    TRIM: (14, 16, 24),
    TIRE: (26, 26, 30),
    RIM: (70, 74, 84),
    SPOKE: (172, 177, 188),
    HUB: (210, 214, 222),
    HEAD: (255, 244, 176),
    TAIL: (214, 40, 40),
    FOG: (255, 250, 210),
    HANDLE: BLUE_HI,
    CLAD: (36, 38, 46),
    WELL: (14, 16, 26),
    SIDEWALL: (48, 48, 56),
}

# --- side view ------------------------------------------------------------------

Pt = tuple[float, float]

# (material, kind, geometry, only_on): painted in order, later shapes win. Kinds:
#   poly: polygon vertices; anything within half a pixel of the edge counts as inside
#   rect: (x0, y0, x1, y1), inclusive pixel rows and columns
#   line: (x0, y0, x1, y1), a 1px stroke (thinner in fine renders)
# only_on limits a shape to pixels that already hold that material (window reflections).
SHAPES: list[tuple[int, str, tuple, int | None]] = [
    # Lower body: short front and rear overhangs, high sills.
    (BODY, "poly", ((2, 9), (44, 9), (54, 9.5), (60, 10.5), (62, 12), (62, 17.5), (60, 18.5), (4, 18.5), (2, 17.5)), None),
    # Cabin: raked windshield, long flat roof, near-upright liftgate. It reaches a row
    # into the body so the two shapes overlap instead of leaving slivers.
    (BODY, "poly", ((2, 10), (2, 4), (4, 2), (34, 2), (44, 9), (44, 10)), None),
    (BODY, "rect", (42, 7, 44, 8), None),  # mirror
    (GLASS, "poly", ((6, 3), (33, 3), (40.5, 8), (6, 8)), None),  # three side windows in one
    (TRIM, "line", (15, 3, 15, 8), None),  # C-pillar
    (TRIM, "rect", (27, 3, 28, 8), None),  # B-pillar
    (REFLECT, "line", (10, 7, 12, 5), GLASS),
    (REFLECT, "line", (33, 7, 35, 5), GLASS),
    (TRIM, "line", (8, 1, 31, 1), None),  # roof rail
    (TRIM, "line", (8, 1, 8, 2), None),
    (TRIM, "line", (31, 1, 31, 2), None),
    (TRIM, "line", (2, 3, 4, 3), None),  # roof spoiler lip
    # Door shut lines and handles.
    (TRIM, "line", (16, 9, 16, 12), None),
    (TRIM, "line", (28, 9, 28, 17), None),
    (TRIM, "line", (43, 10, 43, 15), None),
    (HANDLE, "line", (21, 11, 22, 11), None),
    (HANDLE, "line", (36, 11, 37, 11), None),
    # Black cladding: sills between the wheels, and the lower bumpers.
    (CLAD, "rect", (18, 17, 45, 19), None),
    (CLAD, "rect", (2, 16, 7, 18), None),
    (CLAD, "rect", (56, 15, 62, 18), None),
    # Lights and grille.
    (HEAD, "poly", ((55, 10), (60, 10.5), (61.5, 12), (57, 12)), None),
    (FOG, "rect", (59, 16, 60, 16), None),
    (TRIM, "rect", (61, 13, 62, 14), None),  # hexagonal grille, edge-on
    (TAIL, "rect", (2, 9, 3, 12), None),  # tail light wrapping round the corner
]

# Big 17" wheels: the tyres still reach row 22, so the car stands tall on them.
WHEELS = ((14, 17.6), (50, 17.6))
TIRE_R, RIM_R, ARCH_R, FLARE_R = 4.8, 3.0, 5.6, 7.0
WHEEL_Z = 22.5 - WHEELS[0][1]  # hub height in views.py's world (Z = 23 - y at pixel centres)
LINE_FINE = 0.22  # half-width of strokes in fine renders, in sprite pixels


def _seg_dist(x: float, y: float, x0: float, y0: float, x1: float, y1: float) -> float:
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L))
    return math.hypot(x - (x0 + t * dx), y - (y0 + t * dy))


def _in_poly(poly: tuple[Pt, ...], x: float, y: float) -> bool:
    hit = False
    for i, (x0, y0) in enumerate(poly):
        x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
        if _seg_dist(x, y, x0, y0, x1, y1) <= 0.5:
            return True
    return hit


def _covers(kind: str, g: tuple, x: float, y: float, fine: bool) -> bool:
    if kind == "poly":
        return _in_poly(g, x, y)
    if kind == "rect":
        return g[0] - 0.5 <= x <= g[2] + 0.5 and g[1] - 0.5 <= y <= g[3] + 0.5
    return _seg_dist(x, y, *g) <= (LINE_FINE if fine else 0.5)


def material_at(x: float, y: float, frame: int = 0, fine: bool = False) -> int:
    """The material at sprite point (x, y). frame 1 turns the wheel spokes 45 degrees;
    fine draws strokes and spokes thinner, for high-resolution renders."""
    m = EMPTY
    for mat, kind, g, only_on in SHAPES:
        if (only_on is None or m == only_on) and _covers(kind, g, x, y, fine):
            m = mat
    for cx, cy in WHEELS:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy)
        if d <= FLARE_R and dy <= 1.0 and m in (BODY, CLAD, TRIM, HANDLE):
            m = CLAD  # arch flare
        if d <= ARCH_R and m != EMPTY:
            m = WELL
        if d <= TIRE_R + 0.15:
            m = TIRE
        if d <= RIM_R + 0.45:
            m = SIDEWALL
        if d <= RIM_R:
            if d < 0.55:
                m = HUB
            else:
                u, v = (dx, dy) if frame % 2 == 0 else ((dx + dy) / math.sqrt(2), (dx - dy) / math.sqrt(2))
                m = SPOKE if min(abs(u), abs(v)) < (0.32 if fine else 0.5) else RIM
    return m


def _materials(frame: int = 0) -> list[list[int]]:
    """Material grid [y][x], sampled at pixel centres."""
    return [[material_at(x, y, frame) for x in range(W)] for y in range(H)]


def _shade(x: float, y: float, step: float, dither: bool) -> RGB:
    """Body colour at (x, y): a highlight on top edges, light upper panels, a character
    line at handle height, the mid tone through the doors, dark toward the sills."""
    if material_at(x, y - step) == EMPTY:
        return BLUE_HI
    if 12.6 <= y < 13.4:
        return BLUE_LIGHT
    if y < 11.5:
        return BLUE_LIGHT
    if y < 15.5:
        return BLUE
    if y < 16.5:
        return BLUE if dither else BLUE_DARK
    return BLUE_DARK


def render(frame: int = 0) -> Image.Image:
    """The car as a 64x24 RGBA image with a transparent background and a 1px outline."""
    grid = _materials(frame)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(H):
        for x in range(W):
            m = grid[y][x]
            if m == BODY:
                px[x, y] = (*_shade(x, y, 1.0, (x + y) % 2 == 1), 255)
            elif m != EMPTY:
                px[x, y] = (*COLORS[m], 255)
            elif any(
                0 <= x + dx < W and 0 <= y + dy < H and grid[y + dy][x + dx] != EMPTY
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                px[x, y] = (*OUTLINE, 255)
    return img


def side_color(x: float, y: float) -> RGB | None:
    """The side view at continuous sprite point (x, y), for high-resolution renders.

    (x, y) here has pixel (i, j) covering [i, i+1) x [j, j+1), so it is shifted half a
    pixel onto material_at()'s pixel-centred coordinates. A thin inner outline marks
    the edge of the car, in proportion to the sprite's 1px outline.
    """
    px, py = x - 0.5, y - 0.5
    m = material_at(px, py, fine=True)
    if m == EMPTY:
        return None
    e = 0.3
    if any(material_at(px + ex, py + ey) == EMPTY for ex, ey in ((e, 0), (-e, 0), (0, e), (0, -e))):
        return OUTLINE
    if m == BODY:
        return _shade(px, py, 0.55, (int(x * 3) + int(y * 3)) % 2 == 1)
    return COLORS[m]


def silhouette() -> Image.Image:
    """White-on-transparent car for the Android status bar.

    Android tints small notification icons, so only the alpha channel counts.
    The windows, wheel wells and rims are cut out so the shape still reads as a car at 24dp.
    """
    grid = _materials()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(H):
        for x in range(W):
            if grid[y][x] not in (EMPTY, GLASS, REFLECT, RIM, WELL):
                px[x, y] = (255, 255, 255, 255)
    return img


def sprite_sheet() -> Image.Image:
    """Three frames side by side: idle, drive A, drive B (the wheels turn between A and B)."""
    sheet = Image.new("RGBA", (W * 3, H), (0, 0, 0, 0))
    for i, frame in enumerate((0, 0, 1)):
        sheet.alpha_composite(render(frame), (i * W, 0))
    return sheet


# --- 3D body for views.py ----------------------------------------------------------

WIDTH = 25.0  # car width in sprite pixels: about 1.8 m against 4.5 m long
BELT_Z, ROOF_Z, TUMBLE = 14.0, 21.0, 3.5  # the cabin pulls in by TUMBLE a side by the roof

# Outer silhouette of the side view, rear-bottom going clockwise, in sprite coords.
# Each point names the face that runs from it to the next point.
PROFILE: list[tuple[float, float, str]] = [
    (2, 18, "rear"),
    (2, 9, "liftgate"),
    (3.5, 2, "roof"),
    (34, 2, "windshield"),
    (44, 9, "hood"),
    (54, 9.5, "hood"),
    (60, 10.5, "nose"),
    (62.5, 12, "bumper"),
    (62.5, 18, "chin"),
    (60, 19, "bottom"),
    (4, 19, "chamfer"),
]

# Front-view extras: wheel arches stand proud of the body, tyres show under the bumper.
FRONT_WHEEL_X = 50.0
TIRE_W, TIRE_TALL = 4.5, 9.0
FLARE_W = 1.2
MIRROR_X, MIRROR_Z, MIRROR_H, MIRROR_OUT = 43.0, 14.5, 2.0, 3.0

GLASS_C, REFLECT_C, TRIM_C = COLORS[GLASS], COLORS[REFLECT], COLORS[TRIM]
TIRE_C, HEAD_C, TAIL_C, FOG_C, CLAD_C = COLORS[TIRE], COLORS[HEAD], COLORS[TAIL], COLORS[FOG], COLORS[CLAD]
CHROME = COLORS[HUB]
PLATE = (232, 232, 220)
TAIL_HI = (255, 120, 110)

Tex = Callable[[float, float], "RGB | None"]


def _rails(s: float) -> bool:
    return s < 0.1 or s > 0.9


def _rear_face(t: float, s: float) -> RGB:
    """Lower liftgate and bumper. t runs bottom to top (z 5 to 14), s across the car."""
    z = 5 + t * 9
    yy = s * WIDTH
    edge = min(yy, WIDTH - yy)
    if z < 6.7:
        return TAIL_C if edge < 2 and z > 5.7 else CLAD_C  # bumper cladding, reflectors
    if 6.7 <= z < 7.2:
        return TRIM_C  # liftgate shut line
    if 10 <= z < 13.5 and edge < 5.5:
        if 2 <= edge < 4 and 10.8 <= z < 12.6:
            return BLUE  # the gap inside the C-shaped lamp
        return TAIL_HI if z >= 12.9 else TAIL_C
    if 11.2 <= z < 12.4 and abs(yy - WIDTH / 2) < 1.2:
        return CHROME  # badge
    if 7.2 <= z < 10 and abs(yy - WIDTH / 2) < 4.2:
        return TRIM_C if z < 7.7 or abs(yy - WIDTH / 2) > 3.6 else PLATE
    return BLUE


def _liftgate_glass(t: float, s: float) -> RGB:
    """Rear window in the liftgate, roof spoiler and brake light along its top."""
    yy = s * WIDTH
    if t > 0.84:
        if t < 0.9 and abs(yy - WIDTH / 2) < 2:
            return TAIL_C  # high-mounted brake light
        return BLUE_LIGHT if t > 0.9 else TRIM_C
    if t < 0.1 or yy < 2.5 or yy > WIDTH - 2.5:
        return BLUE_LIGHT  # D-pillars and frame
    if 0.12 <= t < 0.17 and WIDTH / 2 - 1 <= yy < WIDTH / 2 + 5:
        return TRIM_C  # rear wiper
    return REFLECT_C if abs((yy - 6) - t * 9) < 0.6 else GLASS_C


def rear_faces() -> dict[str, Tex]:
    return {
        "rear": _rear_face,
        "liftgate": _liftgate_glass,
        "roof": lambda t, s: TRIM_C if _rails(s) else BLUE_LIGHT,
        "hood": lambda t, s: BLUE_LIGHT,
        "chamfer": lambda t, s: CLAD_C,
    }


def _windshield(t: float, s: float) -> RGB:
    """t runs from the roof down to the hood."""
    yy = s * WIDTH
    if t < 0.1 or t > 0.93 or yy < 2 or yy > WIDTH - 2:
        return BLUE_LIGHT  # A-pillars and frame
    if abs((yy - 4) - t * 7) < 0.6 or abs((yy - 7.5) - t * 7) < 0.45:
        return REFLECT_C
    return GLASS_C


def _nose(t: float, s: float) -> RGB:
    """Top of the front: headlights at the corners, the grille's top edge between them."""
    yy = s * WIDTH
    edge = min(yy, WIDTH - yy)
    if edge < 7.5:
        return HEAD_C if edge > 1 else BLUE_HI
    return TRIM_C


def _bumper(t: float, s: float) -> RGB:
    """t runs top to bottom: the hexagonal grille between slim headlight tips, body
    colour, then the black lower bumper with the intake and fog-light pockets."""
    yy = s * WIDTH
    off = abs(yy - WIDTH / 2)
    edge = min(yy, WIDTH - yy)
    if t < 0.46:
        grille_half = 6.2 - max(0.0, t - 0.2) * 11  # straight sides, then narrowing: a hexagon
        if off < grille_half:
            if off < 1.4 and 0.2 <= t < 0.3:
                return CHROME  # oval badge
            return CHROME if 0.09 <= t < 0.14 else TRIM_C  # chrome wing across the grille
        if t < 0.1 and 1 < edge < 6.5:
            return HEAD_C  # headlight tips wrapping down
        return BLUE
    if t < 0.6:
        return BLUE
    if 0.66 <= t < 0.84 and 1.5 <= edge < 4.5:
        return FOG_C
    if 0.66 <= t < 0.9 and off < 6:
        return TRIM_C  # lower intake
    return CLAD_C


def front_faces() -> dict[str, Tex]:
    return {
        "roof": lambda t, s: TRIM_C if _rails(s) else (BLUE_HI if t > 0.85 else BLUE_LIGHT),
        "windshield": _windshield,
        "hood": lambda t, s: BLUE_LIGHT,
        "nose": _nose,
        "bumper": _bumper,
        "chin": lambda t, s: CLAD_C,
    }
