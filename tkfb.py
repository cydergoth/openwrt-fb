"""Framebuffer using TK as a backend."""
from __future__ import annotations
from tkinter import Tk, Label
from PIL import Image, ImageTk, ImageDraw, ImageFont
import asyncio
import aiotkinter
from typing import Tuple
from framebuffer import Framebuffer

from local_types import Color, Dimension, Point
from panel import panel, MAX_SAMPLES
from widgets import Screen

from network import IfSampler


class TkWindow(Framebuffer):
    """Create a fake framebuffer in a TK Window for development."""

    def __init__(self):
        """Create a new instance of the TkWindow Framebuffer."""
        super().__init__("tk", mode="RGBA", bpp=32, size=Dimension(1280, 720))
        self._root = Tk()
        self._root.geometry("1280x720")

        # Create a photoimage object of the image in the path
        self.fb = Image.new("RGBA", (1280, 720))
        self._drawable = ImageDraw.Draw(self.fb)
        self._tk_bridge = ImageTk.PhotoImage(self.fb)

        self._tk_host = Label(image=self._tk_bridge)

        # Position image
        self._tk_host.place(x=0, y=0)

    def __enter__(self) -> Framebuffer:
        """Support python 'with' statement entry."""
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        """Support python 'with' statement exit."""
        super().__exit__(exc_type, exc_value, tb)
        self._root.destroy()

    def clear(self, fill: Color) -> None:
        """Clear this Framebuffer."""
        self._drawable.rectangle(((0, 0), self.fb.size), fill=fill)

    def write_screen(self, some_bytes: list[bytes]) -> None:
        """Write an image as a raw stream of bytes to this Framebuffer."""
        new_image = Image.frombytes("RGBA", self.fb.size, some_bytes)
        self._tk_bridge.paste(new_image)


if __name__ == "__main__":
    fb = TkWindow()
    sent_sampler = IfSampler("eth0", "bytes_sent", MAX_SAMPLES)
    recv_sampler = IfSampler("eth0", "bytes_recv", MAX_SAMPLES)
    with fb as display:
        display.clear(Color(128, 0, 128, 255))

        screen = Screen(display, panel(sent_sampler, recv_sampler))

        asyncio.set_event_loop_policy(aiotkinter.TkinterEventLoopPolicy())
        loop = asyncio.new_event_loop()
        loop.set_debug(True)
        loop.create_task(sent_sampler.start())
        loop.create_task(recv_sampler.start())
        loop.create_task(screen.start())
        loop.run_forever()
