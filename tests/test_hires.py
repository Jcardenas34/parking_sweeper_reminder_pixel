from parking.android_art import HEADER_H, HEADER_STAND_BOTTOM, HEADER_W
from parking.imaging import car, hires, views
from parking.imaging.street import street_rear


def test_street_rear_unchanged_at_app_scale():
    """Splitting out street_rear_cam() must not move a pixel of the app's header art."""
    car = views.rear_quarter()
    left, top = (HEADER_W - car.width) // 2, HEADER_STAND_BOTTOM - car.height
    cam = views.rear_camera()
    _, (ax, ay) = views.rear_quarter_anchored()
    cam.ox, cam.oy = left + ax, top + ay
    from parking.imaging.street import street_rear_cam

    assert street_rear(HEADER_W, HEADER_H, left, top).tobytes() == street_rear_cam(HEADER_W, HEADER_H, cam).tobytes()


def test_side_color_matches_sprite_materials():
    """The continuous side agrees with the 64x24 sprite at pixel centres."""
    sprite = car.render()
    agree = total = 0
    for y in range(24):
        for x in range(64):
            c = hires.side_color(x + 0.5, y + 0.5)
            s = sprite.getpixel((x, y))
            if s[3] and s[:3] != car.OUTLINE:
                total += 1
                agree += c is not None
    assert agree == total


def test_hd_scene_size_and_car():
    im = hires.rear_scene_hd(2)
    assert im.size == (HEADER_W * 2, HEADER_H * 2)
    colors = {im.getpixel((x, y))[:3] for y in range(im.height) for x in range(im.width)}
    assert {car.BLUE, car.BLUE_LIGHT, views.TAIL, views.PLATE} <= colors
