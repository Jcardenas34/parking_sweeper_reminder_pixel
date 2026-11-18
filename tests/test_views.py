from parking.imaging import car, views


def pixels(im):
    return [im.getpixel((x, y)) for y in range(im.height) for x in range(im.width)]


def colors(im):
    return {p[:3] for p in pixels(im) if p[3]}


def test_front_is_symmetric_blue_with_lights():
    im = views.front()
    assert im.width > 40 and im.height > 30
    c = colors(im)
    assert {car.BLUE, car.BLUE_LIGHT} <= c
    assert views.HEAD in c and views.FOG in c and views.GLASS in c
    assert views.TAIL not in c
    # The silhouette is its own mirror image.
    flipped = im.transpose(0)  # FLIP_LEFT_RIGHT
    assert [p[3] for p in pixels(im)] == [p[3] for p in pixels(flipped)]


def test_rear_quarter_shows_tail_lights_side_and_wheels():
    im = views.rear_quarter()
    assert im.width > im.height
    c = colors(im)
    assert views.TAIL in c and views.PLATE in c and views.GLASS in c
    assert car.COLORS[car.SPOKE] in c  # near-side wheels from the side sprite
    assert views.HEAD in c  # headlight visible at the far front corner


def test_views_are_outlined_and_transparent_around():
    for im in (views.front(), views.rear_quarter()):
        assert im.getpixel((0, 0))[3] == 0
        assert im.getbbox() == (0, 0, im.width, im.height)  # cropped tight
        assert car.OUTLINE in colors(im)


def test_cabin_narrows_toward_roof():
    assert views.inset(views.BELT_Z) == 0
    assert views.inset(views.ROOF_Z) == views.TUMBLE
    assert views.inset(0) == 0


def test_rear_street_lines_up_with_the_rear_car():
    from parking.imaging import street

    w, h, left, top = 160, 72, 41, 18
    scene = street.street_rear(w, h, left, top)
    assert scene.size == (w, h)
    assert all(p[3] == 255 for p in pixels(scene))  # opaque backdrop

    # Project world points with the car's own camera, placed where the sprite is pasted:
    # the kerb face behind and ahead of the car must land on kerb pixels.
    _, (ax, ay) = views.rear_quarter_anchored()
    cam = views.rear_camera()
    cam.ox, cam.oy = left + ax, top + ay
    kerb = {street.CURB, street._shade(street.CURB, 0.75)}
    for X in (-30.0, 90.0):
        x, y = cam.project((X, street.KERB_Y - 0.01, street.KERB_H / 2))
        assert scene.getpixel((int(x), int(y)))[:3] in kerb, X
    assert street.LANE in colors(scene)
