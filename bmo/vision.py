import base64
import io
import logging
from typing import Protocol
from PIL import Image

log = logging.getLogger(__name__)


def encode_image_b64(img: Image.Image, quality: int = 80) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def rotate_image(img: Image.Image, degrees: int) -> Image.Image:
    if degrees % 360 == 0:
        return img
    return img.rotate(-degrees, expand=True)


class CameraProtocol(Protocol):
    def capture(self) -> Image.Image: ...


class PiCamera:
    """picamera2 wrapper — only constructed on Pi."""

    def __init__(self, rotation: int = 0):
        from picamera2 import Picamera2
        self._cam = Picamera2()
        self._cam.configure(self._cam.create_still_configuration(main={"size": (1024, 768)}))
        self._cam.start()
        self._rotation = rotation

    def capture(self) -> Image.Image:
        arr = self._cam.capture_array("main")
        img = Image.fromarray(arr)
        return rotate_image(img, self._rotation)


def capture_b64(camera: CameraProtocol, rotation: int = 0) -> str:
    img = rotate_image(camera.capture(), rotation)
    return encode_image_b64(img)
