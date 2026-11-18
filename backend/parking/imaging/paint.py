"""Pixel-painting helpers: hard-edged shapes and ordered dithering between colour bands.

The canvas can be any size and can be transparent (RGBA), because it draws icons
and sprites as well as scenes.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from PIL import Image, ImageDraw

RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]


class Canvas:
    def __init__(self, w: int, h: int, seed: int = 0, transparent: bool = False) -> None:
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0 if transparent else 255))
        self.px = self.img.load()
        self.draw = ImageDraw.Draw(self.img)
        self.rng = random.Random(seed)

    # --- primitives --------------------------------------------------------
    def put(self, x: float, y: float, c: RGB | RGBA) -> None:
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = c if len(c) == 4 else (*c, 255)

    def rect(self, x0: float, y0: float, x1: float, y1: float, c: RGB) -> None:
        """Filled rectangle, x1/y1 exclusive."""
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        if x1 > x0 and y1 > y0:
            self.draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=c)

    def poly(self, pts: Sequence[tuple[float, float]], c: RGB) -> None:
        self.draw.polygon([(round(x), round(y)) for x, y in pts], fill=c)

    def disc(self, cx: float, cy: float, r: float, c: RGB) -> None:
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.put(x, y, c)

    def dither_rect(self, x0: int, y0: int, x1: int, y1: int, a: RGB, b: RGB) -> None:
        """50% checkerboard of a and b (8-bit stand-in for a blend)."""
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.put(x, y, a if (x + y) % 2 == 0 else b)

    # --- scenery ------------------------------------------------------------
    def sky(self, bands: Sequence[RGB], bottom: int, top: int = 0) -> None:
        """Horizontal color bands with ordered dithering at each boundary."""
        band_h = (bottom - top) / len(bands)
        for y in range(top, bottom):
            pos = (y - top) / band_h
            i = min(int(pos), len(bands) - 1)
            frac = pos - i
            base, nxt = bands[i], bands[min(i + 1, len(bands) - 1)]
            for x in range(self.w):
                if frac > 0.9:
                    c = base if (x + y) % 4 == 0 else nxt
                elif frac > 0.7:
                    c = nxt if (x + y) % 2 == 0 else base
                else:
                    c = base
                self.put(x, y, c)

    def stars(self, n: int, y_max: int, colors: Sequence[RGB]) -> None:
        for _ in range(n):
            self.put(self.rng.randrange(self.w), self.rng.randrange(y_max), self.rng.choice(colors))

    def moon(self, cx: int, cy: int, r: int, c: RGB, shade: RGB) -> None:
        self.disc(cx, cy, r, c)
        for x, y in ((cx - 2, cy - 1), (cx + 1, cy + 2), (cx + 2, cy - 2)):
            self.put(x, y, shade)

    def halo(self, cx: float, cy: float, r: float, c: RGB, density: int = 2) -> None:
        """Dithered glow over whatever is already painted (lamps, lit windows)."""
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                d = math.hypot(x - cx, y - cy)
                if d > r:
                    continue
                core = d <= r * 0.55 and (x + y) % 2 == 0
                rim = x % 2 == 0 and y % 2 == 0 and (x // 2 + y // 2) % max(1, density - 1) == 0
                if core or rim:
                    self.put(x, y, c)

    def lamp(self, x: int, base: int, h: int, post: RGB, glow: RGB, halo: RGB | None = None) -> None:
        """Street lamp: footing, post and a glowing lantern."""
        self.rect(x - 1, base - 2, x + 2, base, post)
        self.rect(x, base - h, x + 1, base, post)
        if halo:
            self.halo(x + 0.5, base - h - 1, 5, halo)
        self.rect(x - 1, base - h - 3, x + 2, base - h, glow)
        self.put(x, base - h - 4, post)
        self.rect(x - 1, base - h - 3, x + 2, base - h - 2, post)


def scale(im: Image.Image, factor: int) -> Image.Image:
    """Integer nearest-neighbour upscale: pixels stay square and sharp."""
    return im.resize((im.width * factor, im.height * factor), Image.NEAREST)
