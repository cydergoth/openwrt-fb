import logging
import psutil
import datetime
from PIL import ImageFont
from PIL.ImageColor import getrgb
from collections import deque
from widgets import (
    Widget,
    TitleDecorator,
    BorderDecorator,
    Screen,
    Point,
    Dimension,
    WidgetDecorator
    )
from periodic import Periodic
import asyncio
from typing import cast, Tuple
from math import floor
from local_types import Color, Dimension

logging.basicConfig(level=logging.INFO)

white: Color = getrgb("white")
black: Color = getrgb("black")
blue: Color  = getrgb("blue")

MAX_SAMPLES: int = 400
graph_font = ImageFont.truetype("inconsolata.ttf", 24)


class IfSampler:
    """Class to sample some statistics from an ether interface."""

    def __init__(self, ifname, attribute, sample_len):
        """Create a new sampler for a specific interface."""
        self._ifname = ifname
        self._attribute = attribute
        self._sample_len = sample_len
        self._buffer = deque(maxlen=sample_len)
        self._last_sample_ts = datetime.datetime.now()
        sample = psutil.net_io_counters(pernic=True)[self._ifname]
        self._last_sample = getattr(sample, attribute)
        self._scrape = Periodic(self._do_scrape, 1)

    async def start(self):
        return await self._scrape.start()

    def _do_scrape(self):
        sample = psutil.net_io_counters(pernic=True)[self._ifname]
        val = getattr(sample, self._attribute)
        last_val = self._last_sample
        delta = val - last_val
        self._last_sample = val
        self._last_sample_ts = datetime.datetime.now()
        self._buffer.append(delta)

    @property
    def last_sample(self):
        return self._last_sample

    def copy(self):
        return self._buffer.copy()


class SeriesGraph(Widget):

    def __init__(self, sampler, size: Dimension, background=black,  **kwargs):
        super().__init__(size, background=background, **kwargs)
        self._sampler = sampler
        self._max = 1
        self._current = 0
        super().draw()

    @property
    def current(self):
        return self._current

    @property
    def max(self):
        return self._max

    def ddraw(self, drawable):
        super().ddraw(drawable)
        (w, h) = self._size
        series = self._sampler.copy()
        self._max = max([*series, self._max])
        # normalize
        scaled_samples = [x/self._max for x in series]
        heights = [floor(x*h) for x in scaled_samples]
        #drawable.rectangle([0, 0, w, h], fill=self._background)
        s_x = 0
        for sample in heights:
            drawable.line([s_x, h, s_x, h-sample], fill=white, width=2)
            s_x = s_x + 2
        if len(series) > 0:
            self._current = series[-1]


class SeriesGraphDecorator(WidgetDecorator):

    @classmethod
    def _get_loc(cls, font: ImageFont) -> Point:
        # origin of the graph is 1px right of left axis and 1/2 way down upper left label
        # Upper Left axis tag
        (_, _, ul_fw, fh) = font.getbbox("9999", anchor="la")  # MiB/s
        oy = fh//2
        ox = 5 + ul_fw
        return Point(ox, oy)

    @classmethod
    def _get_size(cls, widget: SeriesGraph, font: ImageFont) -> Dimension:
        """Calculate the size of this widget based on the decorations"""
        (w, h) = widget.size

        # Left axis Line and ticks
        dw = w + 5

        # Lower axis Line and ticks
        dh = h + 5

        # Lower Left axis tag
        (_, _, ll_fw, fh) = font.getbbox(f"-{(w//2)//60}", anchor="la")
        dh = dh + fh

        # Lower right axis tag
        (_, _, fw, _) = font.getbbox("now", anchor="la")
        dw = dw + fw/2

        # Upper Left axis tag
        (_, _, ul_fw, fh) = font.getbbox("9999", anchor="la")  # MiB/s
        dw = dw + max(ul_fw, ll_fw//2)
        dh = dh + fh//2

        return Dimension(int(dw), int(dh))

    def __init__(self, widget: SeriesGraph, font: ImageFont, **kwargs):
        super().__init__(widget,
                         size=SeriesGraphDecorator._get_size(widget, font),
                         origin=SeriesGraphDecorator._get_loc(font),
                         **kwargs)
        self._font = font
        self._origin = self._get_loc(font)

    def _decorate(self, drawable):
        (ox, oy) = self._origin
        (ww, wh) = self._widget.size
        drawable.line([ox-2, oy, ox-2, oy+wh+1], fill=blue, width=2)  # Y axis
        drawable.line([ox-1, oy+wh+1, ox-1+ww, oy+wh+1], fill=blue, width=2)  # X axis
        # Upper left axis tag
        maxInKiB = self._widget.max//1024
        drawable.text((0, 0), f"{maxInKiB}")
        # Bottom left axix label
        (_, _, fw, fh) = self._font.getbbox(f"-{(ww/2)//60}", anchor="la")
        drawable.text((ox-1-fw/2, oy+4+wh), f"-{(ww/2)//60}", anchor="la")


if __name__ == "__main__":
    from fb import DirectFB
    fb = DirectFB()
    sent_sampler = IfSampler("eth0.2", "bytes_sent", MAX_SAMPLES)
    recv_sampler = IfSampler("eth0.2", "bytes_recv", MAX_SAMPLES)
    with fb as display:
        display.clear(Color(128, 128, 128, 255))

        ssg = SeriesGraph(sent_sampler, size=Dimension(MAX_SAMPLES*2, 80))
        ssgd = SeriesGraphDecorator(ssg, graph_font)
        sent = TitleDecorator(BorderDecorator(ssgd, border_width=24), "eth0.2:sent")
        recv = TitleDecorator(
            BorderDecorator(
                SeriesGraphDecorator(
                    SeriesGraph(recv_sampler, size=Dimension(MAX_SAMPLES*2, 80)),
                    graph_font),
                border_width=24),
            "eth0.2:recv")
        widgets: list[Tuple[Widget, Point]] = [(sent, Point(40, 40)), (recv, Point(40, 200))]
        screen = Screen(display, widgets)

        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.create_task(sent_sampler.start())
        loop.create_task(recv_sampler.start())
        loop.create_task(screen.start())
        loop.run_forever()
