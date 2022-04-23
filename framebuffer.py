from __future__ import annotations
import traceback
from typing import Optional, Any
from local_types import Dimension, Color

class Framebuffer():

    def __init__(self, name: str, mode: str, bpp: int, size: Dimension):
        self._mode = mode
        self._name = name
        self._bpp = bpp
        self._size = size

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> Dimension:
        return self._size

    @property
    def bpp(self) -> int:
        return self._bpp

    def __enter__(self) -> Framebuffer:
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)

    def clear(self, fill: Color) -> None:
        pass

    def write_screen(self, some_bytes: list[bytes]) -> None:
        pass
