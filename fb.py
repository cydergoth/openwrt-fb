"""Framebuffer using directfd as a backend."""
from __future__ import annotations
import os
import mmap
from typing import Optional, Any
from local_types import Dimension, Color
from framebuffer import Framebuffer


class DirectFB(Framebuffer):
    """Framebuffer using directfb as a backend."""

    def __init__(self, fbdev: str = "fb0"):
        """Create a new framebuffer using directfb as a backend."""
        super().__init__("", mode="BGRA", bpp=0, size=Dimension(0, 0))
        self._fbdev = fbdev
        self._fb: Optional[int] = None
        self._fb_bytes: Optional[Any] = None

        with open(f"/sys/class/graphics/{fbdev}/name", "r") as fb_data:
            data = fb_data.read()
            self._name = data

        # Get screen size
        with open(f"/sys/class/graphics/{fbdev}/virtual_size", "r") as fb_data:
            data = fb_data.read()
            (size_x, size_y) = data.split(",")
            self._size = Dimension(int(size_x), int(size_y))

        # Get bit per pixel
        with open(f"/sys/class/graphics/{fbdev}/bits_per_pixel", "r") as fb_data:
            self._bpp = int(fb_data.read())

    @property
    def fbdev(self) -> str:
        """Get the name of the directfb device."""
        return self._fbdev

    def __enter__(self) -> Framebuffer:
        """Support python 'with' statement entry."""
        # Open the framebuffer device
        self._fb = os.open(f"/dev/{self._fbdev}", os.O_RDWR)

        # Map framebuffer to memory
        (size_x, size_y) = self.size
        self._fb_bytes = mmap.mmap(self._fb,
                                   size_x*size_y*self.bpp//8,
                                   mmap.MAP_SHARED,
                                   mmap.PROT_WRITE | mmap.PROT_READ,
                                   offset=0)
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        """Support python 'with' statement exit."""
        super().__exit__(exc_type, exc_value, tb)
        if self._fb_bytes is not None:
            self._fb_bytes.close()
        if self._fb is not None:
            os.close(self._fb)

    def clear(self, fill: Color) -> None:
        """Clear this Framebuffer."""
        # Map colors as Intel use a weird byte order
        (c_r, c_g, c_b, c_a) = fill
        mapped = (c_b, c_g, c_r, c_a)
        (size_x, size_y) = self.size
        screen = bytearray(bytes(mapped))*size_x*size_y
        if self._fb_bytes is not None:
            self._fb_bytes.write(screen)

    def write_screen(self, some_bytes: list[bytes]) -> None:
        if self._fb_bytes is not None:
            self._fb_bytes.seek(0)
            self._fb_bytes.write(some_bytes)


if __name__ == "__main__":
    fb0 = DirectFB("fb0")
    with fb0 as display:
        display.clear(Color(0, 255, 0, 128))
