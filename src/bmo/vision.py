from __future__ import annotations

import base64
import io
import logging
from typing import Any, Protocol

from PIL import Image

log = logging.getLogger(__name__)

__all__ = ["CameraProtocol", "PiCamera", "capture_b64", "encode_image_b64", "rotate_image"]


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

    # _cam is typed Any because picamera2 ships no stubs and is unavailable off-Pi
    _cam: Any

    def __init__(self, rotation: int = 0):
        # picamera2 is Pi-only and ships no type stubs; both import and type are unknown off-Pi
        from picamera2 import (  # pyright: ignore[reportMissingImports]
            Picamera2,  # pyright: ignore[reportUnknownVariableType]
        )

        self._cam = Picamera2()  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        self._cam.configure(  # pyright: ignore[reportUnknownMemberType]
            self._cam.create_still_configuration(main={"size": (1024, 768)})  # pyright: ignore[reportUnknownMemberType]
        )
        self._cam.start()  # pyright: ignore[reportUnknownMemberType]
        self._rotation = rotation

    def capture(self) -> Image.Image:
        # picamera2 lacks stubs; capture_array returns an ndarray of unknown dtype
        arr: Any = self._cam.capture_array("main")  # pyright: ignore[reportUnknownMemberType]
        img = Image.fromarray(arr)
        return rotate_image(img, self._rotation)


def capture_b64(camera: CameraProtocol, rotation: int = 0) -> str:
    img = rotate_image(camera.capture(), rotation)
    return encode_image_b64(img)
