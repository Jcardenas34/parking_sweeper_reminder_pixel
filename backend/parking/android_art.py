"""Android resources drawn from the pixel car (imaging/car.py).

    python -m parking --export-android frontend/android/app/src/main/res

Writes:
- adaptive launcher icons: the night street behind, the car in front
- ic_stat_car: the white status-bar silhouette
- car_large[_front|_rear]: the full-colour icon inside each notification, one per car view
- splash screens
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

from .imaging import car, views
from .imaging.street import CAR_ABOVE_CURB, parked, parked_rear, street, street_rear

# Density buckets: legacy icon px, adaptive layer px (108 dp), status-bar icon px (24 dp).
DENSITIES = {
    "mdpi": (48, 108, 24),
    "hdpi": (72, 162, 36),
    "xhdpi": (96, 216, 48),
    "xxhdpi": (144, 324, 72),
    "xxxhdpi": (192, 432, 96),
}
# The icon is drawn at 1 art pixel per dp. The 64 px car fits the 66 dp safe zone that
# every launcher mask shows, and the kerb is raised so the car sits near the middle.
ICON_ART = 108
ICON_CURB = 0.6


def _scaled(im: Image.Image, px: int) -> Image.Image:
    return im.resize((px, px), Image.NEAREST)


def icon_layers(px: int) -> tuple[Image.Image, Image.Image]:
    """(background, foreground) adaptive-icon layers of px x px."""
    bg, curb_y = street(ICON_ART, ICON_ART, curb=ICON_CURB)
    fg = Image.new("RGBA", (ICON_ART, ICON_ART), (0, 0, 0, 0))
    sprite = car.render()
    fg.alpha_composite(sprite, ((ICON_ART - sprite.width) // 2, curb_y - CAR_ABOVE_CURB))
    return _scaled(bg, px), _scaled(fg, px)


def legacy_icon(px: int) -> Image.Image:
    # Pre-Android-8 icons are not masked: render the 108 dp layers and trim to the visible 72 dp.
    layer = px * 108 // 72
    bg, fg = icon_layers(layer)
    bg.alpha_composite(fg)
    inset = (layer - px) // 2
    return bg.crop((inset, inset, inset + px, inset + px))


def status_icon(px: int) -> Image.Image:
    """White car silhouette, fitted to the width of a px x px status-bar icon."""
    sil = car.silhouette()
    w = px - max(1, px // 12)
    h = round(sil.height * w / sil.width)
    # Upscale crisply first, then shrink smoothly: at 24-96 px the edges need anti-aliasing.
    small = sil.resize((sil.width * 4, sil.height * 4), Image.NEAREST).resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (px, px), (255, 255, 255, 0))
    out.paste(small, ((px - w) // 2, (px - h) // 2))
    r, g, b, a = out.split()
    white = Image.new("L", out.size, 255)
    return Image.merge("RGBA", (white, white, white, a))


# The car views the user can pick in the app, with the suffix used in file names.
# Must match CAR_VIEWS in frontend/src/schedule.ts.
CAR_VIEWS = {"side": "", "front": "_front", "rear": "_rear"}


def car_view(view: str) -> Image.Image:
    if view == "front":
        return views.front()
    if view == "rear":
        return views.rear_quarter()
    return car.render()


def large_icon(view: str = "side") -> Image.Image:
    """Full-colour car on its street, 216 x 216."""
    if view == "side":
        return parked(72, 72, curb=0.62).resize((216, 216), Image.NEAREST)
    sprite = car_view(view)
    # Square scene a little wider than the car; front and rear stand a few rows out in the road.
    size = max(72, sprite.width + 6)
    bottom = round(size * 0.6) + 8
    if view == "rear":
        # The rear view gets the street drawn from its own 45-degree angle.
        return parked_rear(size, size, bottom).resize((216, 216), Image.NEAREST)
    scene, _ = street(size, size, curb=0.6)
    scene.alpha_composite(sprite, ((size - sprite.width) // 2, bottom - sprite.height))
    return scene.resize((216, 216), Image.NEAREST)


def splash(size: tuple[int, int]) -> Image.Image:
    """Parked-car scene filling `size`, with art pixels scaled up by a whole number."""
    sw, sh = size
    k = max(1, min(sw, sh) // 80)
    aw, ah = math.ceil(sw / k), math.ceil(sh / k)
    scene = parked(aw, ah, curb=0.6).resize((aw * k, ah * k), Image.NEAREST)
    left, top = (scene.width - sw) // 2, (scene.height - sh) // 2
    return scene.crop((left, top, left + sw, top + sh)).convert("RGB")


def export_android_art(res_dir: Path) -> None:
    for density, (legacy_px, layer_px, status_px) in DENSITIES.items():
        out = res_dir / f"mipmap-{density}"
        out.mkdir(parents=True, exist_ok=True)
        bg, fg = icon_layers(layer_px)
        bg.save(out / "ic_launcher_background.png")
        fg.save(out / "ic_launcher_foreground.png")
        icon = legacy_icon(legacy_px)
        icon.save(out / "ic_launcher.png")
        icon.save(out / "ic_launcher_round.png")

        drawable = res_dir / f"drawable-{density}"
        drawable.mkdir(parents=True, exist_ok=True)
        status_icon(status_px).save(drawable / "ic_stat_car.png")

    adaptive = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
"""
    anydpi = res_dir / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        (anydpi / name).write_text(adaptive)

    nodpi = res_dir / "drawable-nodpi"
    nodpi.mkdir(parents=True, exist_ok=True)
    for view, suffix in CAR_VIEWS.items():
        large_icon(view).save(nodpi / f"car_large{suffix}.png")

    # Replace Capacitor's placeholder splash in every size the template ships.
    for path in res_dir.glob("drawable*/splash.png"):
        with Image.open(path) as old:
            size = old.size
        splash(size).save(path)


# The in-app header canvas. Must match W, H and STAND_BOTTOM in frontend/src/scene.ts.
HEADER_W, HEADER_H = 160, 72
HEADER_STAND_BOTTOM = round(HEADER_H * 0.68) + 8


def export_web_art(out_dir: Path) -> None:
    """Sprites for the web UI: the empty streets, the side-view sheet and the other two angles."""
    out_dir.mkdir(parents=True, exist_ok=True)
    street(HEADER_W, HEADER_H)[0].save(out_dir / "street.png")
    # The 45-degree street, laid out for the rear car where scene.ts draws it:
    # centred (rounding down) with its lowest pixel on HEADER_STAND_BOTTOM.
    rear = views.rear_quarter()
    street_rear(HEADER_W, HEADER_H, (HEADER_W - rear.width) // 2,
                HEADER_STAND_BOTTOM - rear.height).save(out_dir / "street_rear.png")
    car.sprite_sheet().save(out_dir / "car_sheet.png")
    car.render().save(out_dir / "car_side.png")
    views.front().save(out_dir / "car_front.png")
    views.rear_quarter().save(out_dir / "car_rear_quarter.png")
    legacy_icon(192).save(out_dir / "icon.png")
