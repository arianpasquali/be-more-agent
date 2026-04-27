import base64
import io

from PIL import Image

from bmo.vision import encode_image_b64, rotate_image


def make_test_image() -> Image.Image:
    return Image.new("RGB", (640, 480), color=(255, 0, 0))


def test_encode_image_b64_roundtrip():
    img = make_test_image()
    b64 = encode_image_b64(img)
    raw = base64.b64decode(b64)
    decoded = Image.open(io.BytesIO(raw))
    assert decoded.size == (640, 480)


def test_rotate_image_90():
    img = make_test_image()
    rotated = rotate_image(img, 90)
    assert rotated.size == (480, 640)


def test_rotate_image_zero_noop():
    img = make_test_image()
    assert rotate_image(img, 0) is img
