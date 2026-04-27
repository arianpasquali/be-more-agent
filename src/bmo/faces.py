from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

log = logging.getLogger(__name__)

__all__ = ["FacePlayer", "FaceState", "valid_transition"]


class FaceState(str, Enum):  # noqa: UP042
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"
    WARMUP = "warmup"


def valid_transition(_from: FaceState, _to: FaceState) -> bool:
    return True


class FacePlayer:
    """Renders PNG-sequence loops in a Tk window. Thread-safe set_state()."""

    def __init__(self, faces_dir: str = "faces", fps: int = 8):
        self.faces_dir = Path(faces_dir)
        self.fps = fps
        self._state = FaceState.WARMUP
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._tk: tk.Tk | None = None
        self._label: tk.Label | None = None

    def set_state(self, state: FaceState) -> None:
        with self._lock:
            self._state = state

    def _frames_for(self, state: FaceState) -> list[Path]:
        d = self.faces_dir / state.value
        if not d.exists():
            return []
        return sorted(d.glob("*.png"))

    def run(self, on_close: Callable[[], None] | None = None) -> None:
        import tkinter as tk

        from PIL import Image, ImageTk

        root = tk.Tk()
        self._tk = root
        root.title("BMO")
        # tkinter stub for .attributes() has an Unknown overload; this is a known stub gap
        root.attributes("-fullscreen", True)  # pyright: ignore[reportUnknownMemberType]
        root.configure(bg="black")
        label = tk.Label(root, bg="black")
        self._label = label
        label.pack(expand=True)

        cache: dict[Path, ImageTk.PhotoImage] = {}

        def tick(idx: int = 0) -> None:
            if self._stop.is_set():
                root.destroy()
                if on_close:
                    on_close()
                return
            with self._lock:
                state = self._state
            frames = self._frames_for(state)
            if frames:
                f = frames[idx % len(frames)]
                if f not in cache:
                    cache[f] = ImageTk.PhotoImage(Image.open(f))
                label.config(image=cache[f])
            root.after(int(1000 / self.fps), tick, idx + 1)

        tick()
        root.mainloop()

    def stop(self) -> None:
        self._stop.set()
