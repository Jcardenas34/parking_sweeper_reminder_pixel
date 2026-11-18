"""Night street scene: the backdrop for the launcher icon, splash and in-app header.

Sky with stars and a moon, a row of buildings with lit windows, a street lamp,
the sidewalk and kerb, a "no parking" sweeping sign and the road. `curb_y` is
where the road starts, so callers can park the car right against the kerb.
"""

from __future__ import annotations

import math
import random
from typing import Callable

from PIL import Image

from . import car, views
from .paint import Canvas
from .views import RGB, Vec

SKY = [(10, 12, 38), (18, 22, 60), (29, 43, 83), (44, 58, 110)]
BUILDINGS = [(22, 26, 48), (30, 34, 62), (26, 30, 56)]
LIT = (255, 213, 110)
DARK_WIN = (40, 46, 78)
SIDEWALK = (96, 100, 118)
SIDEWALK_HI = (120, 124, 142)
CURB = (170, 172, 184)
ASPHALT = (38, 40, 50)
ASPHALT_HI = (48, 50, 62)
LANE = (255, 204, 0)
POST = (70, 74, 90)
ASPHALT_SHADOW = (26, 27, 36)
LAMPLIT = (138, 134, 120)


def street(w: int, h: int, seed: int = 7, curb: float = 0.68) -> tuple[Image.Image, int]:
    """(scene, curb_y): an RGBA w x h night street; the road starts `curb` of the way down."""
    c = Canvas(w, h, seed)
    curb_y = round(h * curb)
    walk_top = curb_y - max(5, round(h * 0.1))

    c.sky(SKY, walk_top)
    c.stars(max(6, w * h // 220), walk_top // 2, [(255, 255, 255), (170, 190, 255), (255, 236, 170)])
    c.moon(w - max(8, w // 8), max(6, h // 8), max(3, w // 30), (244, 240, 220), (200, 196, 176))

    # Buildings: blocky silhouettes with a sparse grid of lit windows.
    x = -c.rng.randint(0, 6)
    i = 0
    while x < w:
        bw = c.rng.randint(max(10, w // 9), max(14, w // 5))
        top = walk_top - c.rng.randint(h // 6, h // 3)
        c.rect(x, top, x + bw, walk_top, BUILDINGS[i % len(BUILDINGS)])
        for wy in range(top + 3, walk_top - 3, 4):
            for wx in range(x + 2, x + bw - 2, 3):
                c.rect(wx, wy, wx + 1, wy + 2, LIT if c.rng.random() < 0.3 else DARK_WIN)
        x += bw + c.rng.randint(0, 2)
        i += 1

    # Sidewalk (dithered paving), kerb, road with a dashed centre line.
    c.rect(0, walk_top, w, curb_y, SIDEWALK)
    for y in range(walk_top, curb_y, 3):
        c.rect(0, y, w, y + 1, SIDEWALK_HI)
    c.rect(0, curb_y - 2, w, curb_y, CURB)
    c.rect(0, curb_y, w, h, ASPHALT)
    c.dither_rect(0, curb_y, w, curb_y + 2, ASPHALT, ASPHALT_HI)
    lane_y = curb_y + round((h - curb_y) * 0.78)
    for lx in range(2, w, 12):
        c.rect(lx, lane_y, lx + 6, lane_y + 1, LANE)

    # Street lamp on the left, sweeping sign on the right.
    c.lamp(max(6, w // 10), walk_top + 2, round(h * 0.32), POST, (255, 236, 160), (255, 220, 120))
    _no_parking_sign(c, w - max(10, w // 7), walk_top + 2, round(h * 0.2))
    return c.img, curb_y


def _no_parking_sign(c: Canvas, x: int, base: int, h: int) -> None:
    """Post with a white plate showing a red 'no' circle (the sweeping-day sign)."""
    c.rect(x, base - h, x + 1, base, POST)
    top = base - h - 9
    c.rect(x - 3, top, x + 4, top + 9, (240, 240, 240))
    red = (214, 40, 40)
    for px, py in ((-2, 1), (-1, 0), (0, 0), (1, 0), (2, 1), (-2, 7), (-1, 8), (0, 8), (1, 8), (2, 7),
                   (-3, 2), (-3, 3), (-3, 4), (-3, 5), (-3, 6), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
                   (-2, 2), (-1, 3), (0, 4), (1, 5), (2, 6)):
        c.put(x + px, top + py, red)


# Tires (bottom row 22 of the sprite) sit three rows into the road.
CAR_ABOVE_CURB = 22 - 3


def parked(w: int, h: int, seed: int = 7, curb: float = 0.68) -> Image.Image:
    """The street with the car parked against the kerb, centred."""
    scene, curb_y = street(w, h, seed, curb)
    sprite = car.render()
    scene.alpha_composite(sprite, ((w - sprite.width) // 2, curb_y - CAR_ABOVE_CURB))
    return scene


# --- the street seen from 45 degrees behind the car ---------------------------------
#
# The same street, built in 3D in the car's world coordinates (views.py: X along the
# sprite, rear 0 to front 64; Y across it, from the road-side flank at 0 toward the kerb;
# Z up) and drawn through views.rear_camera(), so the kerb, lane line and shopfronts
# run parallel to the car. Each pixel casts a ray into the scene: the road, the kerb
# face, the raised sidewalk, and a terrace of buildings whose fronts, roofs and stepped
# side walls face the camera. Rays that clear the rooftops show the sky.

KERB_Y = views.WIDTH + 2.0  # a hand's width between the far-side tyres and the kerb
KERB_H = 2.0
WALK_W = 20.0
FRONT_Y = KERB_Y + WALK_W  # building fronts
BLOCK_D = 18.0  # building depth; the sky starts behind it
LANE_Y = -32.5  # the dashed centre line, out in the road
LAMP_X, SIGN_X = -34.0, 78.0  # behind the car and just past its nose
POST_Y = KERB_Y + 3.0
SIDE_DARK = 0.7  # building side walls are in shade
ROOF_LIGHT = 1.35


def _shade(c: RGB, k: float) -> RGB:
    return tuple(min(255, round(v * k)) for v in c)  # type: ignore[return-value]


def _hash(*ns: int) -> int:
    h = 2166136261
    for n in ns:
        h = ((h ^ (n & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h


def _terrace(seed: int, x0: float, x1: float) -> list[tuple[float, float, float, RGB]]:
    """Buildings (left X, right X, height, colour) shoulder to shoulder from x0 to x1."""
    rng = random.Random(seed)
    out, x, i = [], x0, 0
    while x < x1:
        bw = rng.randint(22, 40)
        out.append((x, x + bw, float(rng.randint(12, 34)), BUILDINGS[i % len(BUILDINGS)]))
        x += bw
        i += 1
    return out


def street_rear(w: int, h: int, car_left: int, car_top: int, seed: int = 7) -> Image.Image:
    """An RGBA w x h night street seen from behind the car's right rear corner, laid out so
    that views.rear_quarter() pasted at (car_left, car_top) sits parked against the kerb."""
    _, (ax, ay) = views.rear_quarter_anchored()
    cam = views.rear_camera()
    cam.ox, cam.oy = car_left + ax, car_top + ay
    return street_rear_cam(w, h, cam, seed)


def street_rear_cam(w: int, h: int, cam: views.Camera, seed: int = 7) -> Image.Image:
    """street_rear() through an already-positioned camera, at any scale.

    The road, kerb and buildings are ray-cast, so they render at whatever scale the
    camera has. The lamp and sign are pixel sprites; at k times REAR_SCALE they're
    drawn at 1x and blown up k times, so their pixels match the rest of the scene.
    """
    s = cam.scale
    toward, right, up = cam.toward, cam.right, cam.up
    # Along any screen column, one pixel down moves this far in Y across the road. A lane
    # exactly two of these wide is exactly 2px thick everywhere, so its edges step cleanly.
    lane_half = 1 / (2 * s * up[0])

    c = Canvas(w, h, seed)
    c.sky(SKY, h)
    c.stars(max(6, w * h // 220), h, [(255, 255, 255), (170, 190, 255), (255, 236, 170)])
    # The moon low over the rooftops on the left, where the street recedes toward the camera.
    c.moon(max(8, w // 8), max(6, h // 8), max(3, w // 30), (244, 240, 220), (200, 196, 176))

    # World X range on screen: generous, so the terrace and road cover every column.
    reach = (w + h) / s * 2
    blocks = _terrace(seed, -reach, reach)

    def ground(P: Vec, Y: float, X: float) -> RGB:
        if Y < KERB_Y:  # road
            if 1 <= X <= 63 and -1.5 <= Y <= views.WIDTH + 0.5:
                return ASPHALT_SHADOW  # under the car
            if abs(Y - LANE_Y) < lane_half and (X % 14) < 7:
                return LANE
            if Y > KERB_Y - 3:
                return ASPHALT_HI if (round(P[0] * 3) + round(P[2] * 3)) % 2 else ASPHALT  # gutter
            return ASPHALT
        # Sidewalk: slabs with joints, a pool of lamplight around the lamp.
        lit = math.hypot(X - LAMP_X, Y - POST_Y) < 16
        if (X % 9) < 1.0 or abs(Y - (KERB_Y + WALK_W / 2)) < 0.5:
            return SIDEWALK if lit else _shade(SIDEWALK, 0.82)
        return LAMPLIT if lit else SIDEWALK_HI if Y < KERB_Y + 2.5 else SIDEWALK

    def window(bi: int, a: float, z: float, base: RGB, top: float) -> RGB:
        """Windows on a wall: a in wall units along it, z up it."""
        col, row = math.floor(a / 3.4), math.floor(z / 3.6)
        if a % 3.4 < 1.2 or z % 3.6 < 1.5 or z < 6 or z > top - 3:
            return base
        return LIT if _hash(seed, bi, col, row) % 100 < 30 else DARK_WIN

    def shade_px(sx: int, sy: int) -> RGB | None:
        u, v = (sx + 0.5 - cam.ox) / s, -(sy + 0.5 - cam.oy) / s
        B = tuple(u * right[k] + v * up[k] for k in range(3))
        best: tuple[float, RGB] | None = None

        def hit(t: float, col: RGB) -> None:
            nonlocal best
            if best is None or t > best[0]:
                best = (t, col)

        def at(t: float) -> Vec:
            return (B[0] + t * toward[0], B[1] + t * toward[1], B[2] + t * toward[2])

        # Road (Z = 0) and sidewalk top (Z = KERB_H).
        for z0, lo, hi in ((0.0, -1e9, KERB_Y), (KERB_H, KERB_Y, FRONT_Y)):
            t = (z0 - B[2]) / toward[2]
            P = at(t)
            if lo <= P[1] < hi:
                hit(t, ground(P, P[1], P[0]))
        # Kerb face (Y = KERB_Y), facing the road.
        t = (KERB_Y - B[1]) / toward[1]
        P = at(t)
        if 0 <= P[2] <= KERB_H:
            hit(t, CURB if P[2] > KERB_H - 0.8 else _shade(CURB, 0.75))
        # Buildings: front (Y = FRONT_Y), roof (Z = top), left side wall (X = x0).
        tf = (FRONT_Y - B[1]) / toward[1]
        Pf = at(tf)
        for bi, (x0, x1, top, col) in enumerate(blocks):
            if x0 <= Pf[0] < x1 and 0 <= Pf[2] <= top:
                hit(tf, window(bi, Pf[0] - x0, Pf[2], col, top) if Pf[2] < top - 1.2 else _shade(col, ROOF_LIGHT))
            t = (top - B[2]) / toward[2]
            P = at(t)
            if x0 <= P[0] < x1 and FRONT_Y <= P[1] <= FRONT_Y + BLOCK_D:
                hit(t, _shade(col, ROOF_LIGHT) if P[1] < FRONT_Y + 1.5 else _shade(col, 1.12))
            prev_top = blocks[bi - 1][2] if bi else 0.0
            if top > prev_top:
                t = (x0 - B[0]) / toward[0]
                P = at(t)
                if FRONT_Y <= P[1] <= FRONT_Y + BLOCK_D and prev_top <= P[2] <= top:
                    hit(t, window(bi + 1000, P[1] - FRONT_Y, P[2], _shade(col, SIDE_DARK), top))
        return best[1] if best else None

    for sy in range(h):
        for sx in range(w):
            col = shade_px(sx, sy)
            if col is not None:
                c.put(sx, sy, col)

    # Lamp and sign stand on the sidewalk; draw them as upright sprites at their projected feet.
    def foot(X: float) -> tuple[int, int]:
        x, y = cam.project((X, POST_Y, KERB_H))
        return math.floor(x), math.floor(y)

    k = max(1, round(s / views.REAR_SCALE))
    lx, ly = foot(LAMP_X)
    sx_, sy_ = foot(SIGN_X)
    if k == 1:
        c.lamp(lx, ly, round(h * 0.32), POST, (255, 236, 160), (255, 220, 120))
        _no_parking_sign(c, sx_, sy_, round(h * 0.2))
        return c.img

    def blown_up(draw: Callable[[Canvas, int, int], None], fx: int, fy: int, size: int) -> None:
        small = Canvas(size, size, seed, transparent=True)
        draw(small, size // 2, size - 1)
        big = small.img.resize((size * k, size * k), Image.NEAREST)
        c.img.alpha_composite(big, (fx - (size // 2) * k, fy - (size - 1) * k))

    lamp_h, sign_h = round(h * 0.32 / k), round(h * 0.2 / k)
    blown_up(lambda cv, x, y: cv.lamp(x, y, lamp_h, POST, (255, 236, 160), (255, 220, 120)), lx, ly, lamp_h + 12)
    blown_up(lambda cv, x, y: _no_parking_sign(cv, x, y, sign_h), sx_, sy_, sign_h + 12)
    return c.img


def parked_rear(w: int, h: int, bottom: int, seed: int = 7) -> Image.Image:
    """The 45-degree street with the rear-view car parked on it, centred, its lowest pixel at `bottom`."""
    sprite = views.rear_quarter()
    left, top = (w - sprite.width) // 2, bottom - sprite.height
    scene = street_rear(w, h, left, top, seed)
    scene.alpha_composite(sprite, (left, top))
    return scene
