"""Front view and 45-degree rear view of the display car, built from its side view.

The side profile in car.py is extruded across the car's width to make a simple
3D body, then drawn through an orthographic camera at the chosen angle:
- Each face that points toward the camera is sampled finely across its surface;
  every sample is projected to a screen pixel and coloured by the face's texture
  function from car.py (glass, tail light, grille, ...).
- Above the beltline the cabin narrows toward the roof (tumblehome), as on the
  real car, so the roof is narrower than the body.
- In the rear view the near side samples the side sprite directly, so its doors,
  windows and wheels match car.render() exactly.
- Faces are painted far to near, and the result gets the same 1px outline as
  the side view.

This module is the engine; everything about the particular car is in car.py.

Coordinates: X runs along the car (rear 0 to front 64, as in the side sprite),
Y across it (0 to WIDTH), Z up (0 = ground). Sprite pixel (x, y) is X = x, Z = 23 - y.
"""

from __future__ import annotations

import math
from typing import Callable

from PIL import Image

from . import car
from .car import BLUE, BLUE_HI, COLORS, OUTLINE

RGB = tuple[int, int, int]
Vec = tuple[float, float, float]
Tex = Callable[[float, float], "RGB | None"]

WIDTH = car.WIDTH
BELT_Z, ROOF_Z, TUMBLE = car.BELT_Z, car.ROOF_Z, car.TUMBLE
PROFILE = car.PROFILE
GLASS, REFLECT, TRIM, TIRE = car.GLASS_C, car.REFLECT_C, car.TRIM_C, car.TIRE_C
HEAD, TAIL, FOG, CLAD = car.HEAD_C, car.TAIL_C, car.FOG_C, car.CLAD_C
CHROME, PLATE = car.CHROME, car.PLATE


def inset(z: float) -> float:
    """How far the body side is pulled in from Y=0 at height z."""
    return TUMBLE * min(1.0, max(0.0, (z - BELT_Z) / (ROOF_Z - BELT_Z)))


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class Camera:
    """Orthographic camera. yaw is the compass direction the camera sits in, seen from the car:
    0 = in front (+X), 225 = behind and to the right. pitch tilts it up to look down on the car."""

    def __init__(self, yaw: float, pitch: float, scale: float) -> None:
        phi, p = math.radians(yaw), math.radians(pitch)
        self.toward = (math.cos(p) * math.cos(phi), math.cos(p) * math.sin(phi), math.sin(p))
        self.right = (-math.sin(phi), math.cos(phi), 0.0)
        self.up = (-math.sin(p) * math.cos(phi), -math.sin(p) * math.sin(phi), math.cos(p))
        self.scale = scale
        self.ox = self.oy = 0.0

    def project(self, P: Vec) -> tuple[float, float]:
        return self.ox + self.scale * _dot(self.right, P), self.oy - self.scale * _dot(self.up, P)

    def depth(self, P: Vec) -> float:
        """Larger is nearer the camera."""
        return _dot(self.toward, P)


class Painter:
    def __init__(self, cam: Camera, w: int, h: int) -> None:
        self.cam = cam
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.img.load()

    def plot(self, P: Vec, c: RGB) -> None:
        x, y = self.cam.project(P)
        x, y = int(math.floor(x)), int(math.floor(y))
        if 0 <= x < self.img.width and 0 <= y < self.img.height:
            self.px[x, y] = (*c, 255)

    def face(self, corner: Callable[[float, float], Vec], tex: Tex) -> None:
        """Paint the surface corner(t, s), t and s in 0..1, coloured by tex(t, s).

        The surface is sampled densely enough that neighbouring samples land less
        than half a pixel apart on screen, so faces come out solid with no gaps.
        """
        def span(a: Vec, b: Vec) -> float:
            (ax, ay), (bx, by) = self.cam.project(a), self.cam.project(b)
            return math.hypot(bx - ax, by - ay)

        nt = max(2, math.ceil(3 * max(span(corner(0, 0), corner(1, 0)), span(corner(0, 1), corner(1, 1)))))
        ns = max(2, math.ceil(3 * max(span(corner(0, 0), corner(0, 1)), span(corner(1, 0), corner(1, 1)))))
        for i in range(nt + 1):
            t = i / nt
            for j in range(ns + 1):
                u = j / ns
                c = tex(t, u)
                if c is not None:
                    self.plot(corner(t, u), c)

    def outline(self) -> Image.Image:
        """The sprite with a 1px outline, cropped tight. Sets self.offset to the crop's top-left."""
        out = self.img.copy()
        opx = out.load()
        w, h = out.size
        for y in range(h):
            for x in range(w):
                if self.px[x, y][3]:
                    continue
                if any(0 <= x + dx < w and 0 <= y + dy < h and self.px[x + dx, y + dy][3]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    opx[x, y] = (*OUTLINE, 255)
        box = out.getbbox()
        self.offset = box[:2]
        return out.crop(box)  # tight, so the sprite is centred on its content

    def anchor(self) -> tuple[float, float]:
        """Where the world origin (rear, near-side corner of the car, on the ground) projects to
        in the cropped sprite, so a scene drawn through the same camera can line up with it."""
        return self.cam.ox - self.offset[0], self.cam.oy - self.offset[1]


def _xz(x: float, y: float) -> tuple[float, float]:
    return x, 23.0 - y


def _profile_faces() -> list[tuple[str, Vec, Vec]]:
    """(name, start (X, Z), end (X, Z)) for each profile edge, extruded across the width."""
    faces = []
    for i, (x, y, name) in enumerate(PROFILE):
        nx, ny, _ = PROFILE[(i + 1) % len(PROFILE)]
        faces.append((name, _xz(x, y), _xz(nx, ny)))
    return faces


def _edge_corner(a: tuple[float, float], b: tuple[float, float]) -> Callable[[float, float], Vec]:
    """Surface between profile points a and b, spanning the (tumblehome-narrowed) width."""
    def corner(t: float, s: float) -> Vec:
        X = a[0] + (b[0] - a[0]) * t
        Z = a[1] + (b[1] - a[1]) * t
        i = inset(Z)
        return X, i + (WIDTH - 2 * i) * s, Z
    return corner


def _outward(a: tuple[float, float], b: tuple[float, float]) -> Vec:
    # PROFILE runs clockwise on screen (Z up), so the outward normal of edge (dx, dz) is (-dz, dx).
    return (-(b[1] - a[1]), 0.0, b[0] - a[0])


def _fit(cam: Camera, points: list[Vec], margin: int = 1) -> tuple[int, int]:
    """Shift the camera so every point lands inside the image; returns the image size."""
    xs, ys = zip(*(cam.project(p) for p in points))
    cam.ox, cam.oy = margin - min(xs) + 0.5, margin - min(ys) + 0.5
    return math.ceil(max(xs) - min(xs)) + 2 * margin + 1, math.ceil(max(ys) - min(ys)) + 2 * margin + 1


def _box_points() -> list[Vec]:
    pts = []
    for x, y, _ in PROFILE:
        X, Z = _xz(x, y)
        pts += [(X, 0.0, Z), (X, WIDTH, Z)]
    return pts + [(X, Y, 0.0) for X in (8, 56) for Y in (-1, WIDTH + 1)]


def _paint_body(p: Painter, textures: dict[str, Tex], extra: list[tuple[float, Callable[[], None]]]) -> None:
    """Paint visible profile faces plus `extra` (depth, draw) items, far to near."""
    cam = p.cam
    items: list[tuple[float, Callable[[], None]]] = list(extra)
    for name, a, b in _profile_faces():
        if _dot(_outward(a, b), cam.toward) <= 0 or name not in textures:
            continue
        mid = ((a[0] + b[0]) / 2, WIDTH / 2, (a[1] + b[1]) / 2)
        corner, tex = _edge_corner(a, b), textures[name]
        items.append((cam.depth(mid), lambda corner=corner, tex=tex: p.face(corner, tex)))
    for _, draw in sorted(items, key=lambda it: it[0]):
        draw()


def _solid(c: RGB) -> Tex:
    return lambda t, s: c


def _tire_disc(p: Painter, X: float, Z: float, Y: float, r: float = 4.5) -> None:
    """A wheel seen side-on in the plane at Y (only used where the face shows)."""
    def tex(t: float, s: float) -> RGB | None:
        dx, dz = (t - 0.5) * 2 * r, (s - 0.5) * 2 * r
        return TIRE if dx * dx + dz * dz <= r * r else None
    p.face(lambda t, s: (X - r + 2 * r * t, Y, Z - r + 2 * r * s), tex)


# --- rear three-quarter view ----------------------------------------------------

REAR_YAW, REAR_PITCH, REAR_SCALE = 225.0, 18.0, 1.25


def rear_camera() -> Camera:
    """The camera the rear view is drawn with; street.street_rear() draws the street through it too."""
    return Camera(yaw=REAR_YAW, pitch=REAR_PITCH, scale=REAR_SCALE)


def rear_quarter() -> Image.Image:
    """The car from behind and to the right, 45 degrees off its tail."""
    return rear_quarter_anchored()[0]


def rear_quarter_anchored() -> tuple[Image.Image, tuple[float, float]]:
    """(sprite, anchor): the rear view, and where the world origin lands in it (see Painter.anchor)."""
    cam = rear_camera()
    w, h = _fit(cam, _box_points())
    p = Painter(cam, w, h)
    side = car.render()
    spx = side.load()

    def side_tex(t: float, s: float) -> RGB | None:
        x, y = min(63, int(t * 64)), min(23, int(s * 24))
        c = spx[x, y]
        if not c[3] or (c[:3] == OUTLINE and y < 10):
            return None  # the cabin leans in, so its old outline would cut across the roof
        return c[:3]

    far_wheels = [
        (cam.depth((wx, WIDTH, car.WHEEL_Z)), lambda wx=wx: _tire_disc(p, wx + 0.5, car.WHEEL_Z, WIDTH - 1.5, car.TIRE_R))
        for wx, _ in car.WHEELS
    ]
    def near_side_corner(t: float, s: float) -> Vec:
        Z = 23 - 24 * s
        return 64 * t, inset(Z), Z

    near_side = (cam.depth((32, 0, 10)) + 100, lambda: p.face(near_side_corner, side_tex))
    _paint_body(p, car.rear_faces(), far_wheels + [near_side])
    sprite = p.outline()
    return sprite, p.anchor()


# --- front view -------------------------------------------------------------------

def front(scale: float = 1.6) -> Image.Image:
    """The car head-on, looking slightly down onto the hood."""
    cam = Camera(yaw=0, pitch=6, scale=scale)
    out = car.MIRROR_OUT
    pts = _box_points() + [(car.MIRROR_X, -out - 0.5, 16), (car.MIRROR_X, WIDTH + out + 0.5, 16)]
    w, h = _fit(cam, pts)
    # Put the centre line through the middle of a pixel column, so mirror-image points
    # round to mirror-image pixels and the head-on view comes out exactly symmetric.
    # (On a pixel edge, faces ending exactly on a boundary would round one side outward.)
    centre = cam.ox + cam.scale * WIDTH / 2
    cam.ox -= centre - math.floor(centre) - 0.5
    p = Painter(cam, w, h)
    X = car.FRONT_WHEEL_X

    def tires() -> None:
        for y0 in (0.3, WIDTH - car.TIRE_W - 0.3):
            p.face(lambda t, s, y0=y0: (X, y0 + car.TIRE_W * t, car.TIRE_TALL * s), _solid(TIRE))

    def flares() -> None:
        # The black arch flares stand out past the body on both sides.
        for y0, dy in ((0.0, -car.FLARE_W), (WIDTH, car.FLARE_W)):
            p.face(lambda t, s, y0=y0, dy=dy: (X + 4, y0 + dy * t, 3 + 8 * s), _solid(CLAD))

    def mirrors() -> None:
        for y0, dy in ((0.0, -out), (WIDTH, out)):
            p.face(lambda t, s, y0=y0, dy=dy: (car.MIRROR_X, y0 + dy * t, car.MIRROR_Z + car.MIRROR_H * s),
                   lambda t, s: BLUE_HI if s > 0.7 else BLUE)

    _paint_body(p, car.front_faces(), [
        (cam.depth((X, 0, 4)), tires),
        (cam.depth((X + 4, 0, 6)), flares),
        (cam.depth((car.MIRROR_X, 0, 14)), mirrors),
    ])
    return p.outline()
