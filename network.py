import logging
from fb import Framebuffer, Color
from PIL.ImageColor import getrgb
from collections import deque
import psutil
import datetime
from widgets import Widget, TitleDecorator, BorderDecorator, Screen, Point
from periodic import Periodic
import asyncio
from typing import cast, Tuple
from math import floor

logging.basicConfig(level=logging.INFO)


def rgb(color: str) -> Color:
    return cast(Color, getrgb(color))


white = rgb("white")
black = rgb("black")

MAX_SAMPLES: int = 400

class IfSampler:

    def __init__(self, ifname, attribute, sample_len):
        self._ifname = ifname
        self._attribute = attribute
        self._sample_len = sample_len
        self._buffer = deque(maxlen=sample_len)
        self._last_sample_ts = datetime.datetime.now()
        sample = psutil.net_io_counters(pernic=True)[self._ifname]
        self._last_sample = getattr(sample, attribute)
        self._scrape = Periodic(self._do_scrape, 5)

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

    def copy(self):
        return self._buffer.copy()


class SeriesGraph(Widget):

    def __init__(self, sampler, background=black,  **kwargs):
        super().__init__(background=background, **kwargs)
        self._sampler = sampler
        self._max = 1
        super().draw()

    def ddraw(self, drawable):
        super().ddraw(drawable)
        (w, h) = self._size
        series = self._sampler.copy()
        self._max = max([*series, self._max])
        # normalize
        scaled_samples = [x/self._max for x in series]
        heights = [floor(x*h) for x in scaled_samples]
        drawable.rectangle([0, 0, w, h], fill=self._background)
        s_x = 0
        for sample in heights:
            drawable.line([s_x, h, s_x, h-sample], fill=white, width=2)
            s_x = s_x + 2


if __name__ == "__main__":
    fb = Framebuffer()
    sent_sampler = IfSampler("eth0.2", "bytes_sent", MAX_SAMPLES)
    recv_sampler = IfSampler("eth0.2", "bytes_recv", MAX_SAMPLES)
    with fb as display:
        display.clear(Color(128, 128, 128, 255))

        sent = TitleDecorator(
            BorderDecorator(
                SeriesGraph(sent_sampler, size=(MAX_SAMPLES*2, 80)),
                border_width=24),
            "eth0.2:sent")
        recv = TitleDecorator(
            BorderDecorator(
                SeriesGraph(recv_sampler, size=(MAX_SAMPLES*2, 80)),
                border_width=24),
            "eth0.2:recv")
        widgets: list[Tuple[Widget, Point]] = [(sent, Point(40, 40)), (recv, Point(40, 160))]
        screen = Screen(display, widgets)

        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.create_task(sent_sampler.start())
        loop.create_task(recv_sampler.start())
        loop.create_task(screen.start())
        loop.run_forever()
