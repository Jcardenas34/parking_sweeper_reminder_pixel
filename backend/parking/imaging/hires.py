"""A high-resolution sample of the 45-degree rear scene (car parked on the angled street).

The app's version is 160x72 with the camera at REAR_SCALE. Scaling that camera up isn't
enough on its own: the car's near side samples the 64x24 side sprite, so it would only
get blockier. Here the near side comes from car.side_color(), which reads the same
continuous shapes the sprite is sampled from, so everything stays crisp at k times the
size:
- the rear, liftgate and roof faces use car.py's textures, which are already
  continuous;
- the street is ray-cast through the same camera (street.street_rear_cam);
- the outline is k pixels thick, so it keeps its weight relative to the car.

    python -m parking --hd-sample out.png [--hd-scale 3]
"""

from __future__ import annotations

from PIL import Image

from . import car, views
from .car import OUTLINE
from .street import street_rear_cam
from .views import Vec

side_color = car.side_color  # kept here too: tests and callers know it as hires.side_color


def _thick_outline(img: Image.Image, k: int) -> Image.Image:
    """Grow a k-pixel OUTLINE ring around the sprite's silhouette."""
    out = img.copy()
    for _ in range(k):
        src = out.copy()
        spx, opx = src.load(), out.load()
        w, h = out.size
        for y in range(h):
            for x in range(w):
                if spx[x, y][3]:
                    continue
                if any(0 <= x + dx < w and 0 <= y + dy < h and spx[x + dx, y + dy][3]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    opx[x, y] = (*OUTLINE, 255)
    return out


def rear_quarter_hd(k: int = 3) -> tuple[Image.Image, tuple[float, float]]:
    """(sprite, anchor) like views.rear_quarter_anchored(), drawn k times larger."""
    cam = views.Camera(views.REAR_YAW, views.REAR_PITCH, views.REAR_SCALE * k)
    w, h = views._fit(cam, views._box_points(), margin=k + 1)
    p = views.Painter(cam, w, h)

    def near_side(t: float, s: float) -> Vec:
        Z = 23 - 24 * s
        return 64 * t, views.inset(Z), Z

    far_wheels = [
        (cam.depth((wx, views.WIDTH, car.WHEEL_Z)),
         lambda wx=wx: views._tire_disc(p, wx + 0.5, car.WHEEL_Z, views.WIDTH - 1.5, car.TIRE_R))
        for wx, _ in car.WHEELS
    ]
    side = (cam.depth((32, 0, 10)) + 100, lambda: p.face(near_side, lambda t, s: side_color(64 * t, 24 * s)))
    views._paint_body(p, car.rear_faces(), far_wheels + [side])
    sprite = _thick_outline(p.img, k)
    box = sprite.getbbox()
    return sprite.crop(box), (cam.ox - box[0], cam.oy - box[1])


def rear_scene_hd(k: int = 3, w: int = 160, h: int = 72, seed: int = 7) -> Image.Image:
    """The app header's 45-degree scene (w x h at 1x), rendered at k times the resolution.

    The car sits exactly where the header puts it: the 1x camera origin is found the way
    android_art.export_web_art() places the sprite, then scaled by k.
    """
    from ..android_art import HEADER_STAND_BOTTOM  # the header layout this sample mirrors

    small, (ax, ay) = views.rear_quarter_anchored()
    ox = (w - small.width) // 2 + ax
    oy = HEADER_STAND_BOTTOM - small.height + ay

    car, (hx, hy) = rear_quarter_hd(k)
    cam = views.Camera(views.REAR_YAW, views.REAR_PITCH, views.REAR_SCALE * k)
    cam.ox, cam.oy = ox * k, oy * k
    scene = street_rear_cam(w * k, h * k, cam, seed)
    scene.alpha_composite(car, (round(cam.ox - hx), round(cam.oy - hy)))
    return scene
