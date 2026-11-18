from parking.android_art import CAR_VIEWS, DENSITIES, icon_layers, large_icon, splash, status_icon
from parking.imaging import car
from parking.imaging.street import parked


def pixels(im):
    return [im.getpixel((x, y)) for y in range(im.height) for x in range(im.width)]


def test_car_size_and_paint():
    sprite = car.render()
    assert sprite.size == (car.W, car.H) == (64, 24)
    colors = {px[:3] for px in pixels(sprite) if px[3]}
    # Blue body ramp, red tail light, warm headlight all present.
    assert {car.BLUE_DARK, car.BLUE, car.BLUE_LIGHT, car.BLUE_HI} <= colors
    assert car.COLORS[car.TAIL] in colors and car.COLORS[car.HEAD] in colors


def test_car_is_blue_with_black_cladding():
    blues = {car.BLUE_DARK, car.BLUE, car.BLUE_LIGHT, car.BLUE_HI}
    body = [px[:3] for px in pixels(car.render()) if px[3]]
    # Blue is the biggest share; the crossover's cladding, glass and big wheels take the rest.
    assert sum(c in blues for c in body) / len(body) > 0.25
    assert car.COLORS[car.CLAD] in body


def test_wheels_turn_between_frames():
    assert car.render(0).tobytes() != car.render(1).tobytes()
    sheet = car.sprite_sheet()
    assert sheet.size == (64 * 3, 24)
    assert sheet.crop((0, 0, 64, 24)).tobytes() == sheet.crop((64, 0, 128, 24)).tobytes()


def test_car_has_outline_and_transparent_corners():
    sprite = car.render()
    assert sprite.getpixel((0, 0))[3] == 0
    assert car.OUTLINE in {px[:3] for px in pixels(sprite) if px[3]}


def test_status_icon_is_white_with_alpha():
    for _, _, px in DENSITIES.values():
        icon = status_icon(px)
        assert icon.size == (px, px)
        opaque = [p for p in pixels(icon) if p[3]]
        assert opaque, "silhouette is empty"
        assert all(p[:3] == (255, 255, 255) for p in opaque)
        assert icon.getpixel((0, 0))[3] == 0


def test_icon_layers_sizes_and_car_in_safe_zone():
    bg, fg = icon_layers(108)
    assert bg.size == fg.size == (108, 108)
    assert bg.getpixel((0, 0))[3] == 255
    box = fg.getbbox()
    # The car stays within the 66dp safe square (21..87) horizontally and near the middle vertically.
    assert box[0] >= 20 and box[2] <= 88
    assert 30 <= (box[1] + box[3]) / 2 <= 66


def test_large_icon_and_splash():
    icons = {view: large_icon(view) for view in CAR_VIEWS}
    assert all(im.size == (216, 216) for im in icons.values())
    assert len({im.tobytes() for im in icons.values()}) == 3
    assert splash((480, 800)).size == (480, 800)
    assert splash((1920, 1080)).size == (1920, 1080)
    assert parked(160, 72).size == (160, 72)
