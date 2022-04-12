import sys
import time
import logging
from fb import Framebuffer
from PIL import Image, ImageDraw
from PIL.ImageColor import getrgb
from collections import deque
import psutil
import datetime
import traceback
import PIL.features
from PIL import ImageFont
from widgets import Widget, TitleDecorator, BorderDecorator, Screen
from periodic import Periodic
import asyncio

logging.basicConfig(level=logging.INFO)
white = getrgb("white")
black = getrgb("black")

class IfSampler:

    def __init__(self, ifname, attribute, sample_len):
        self._ifname=ifname
        self._attribute = attribute
        self._sample_len=sample_len
        self._buffer=deque(maxlen=sample_len)
        self._last_sample_ts=datetime.datetime.now()
        sample=psutil.net_io_counters(pernic=True)[self._ifname]
        self._last_sample=getattr(sample, attribute)
        self._scrape=Periodic(self._do_scrape,5)

    async def start(self):
        return await self._scrape.start()

    def _do_scrape(self):
        sample=psutil.net_io_counters(pernic=True)[self._ifname]
        val = getattr(sample, self._attribute)
        last_val = self._last_sample
        delta = val - last_val
        self._last_sample = val
        self._last_sample_ts = datetime.datetime.now()
        self._buffer.append(delta)

    def copy(self):
        return self._buffer.copy()



class SeriesGraph(Widget):

    def __init__(self, sampler, **kwargs):
        super().__init__(**kwargs)
        self._sampler = sampler
        self._max = 1
        super().draw()

    def ddraw(self,drawable):
        super().ddraw(drawable)
        (w,h) = self._size
        series = self._sampler.copy()
        self._max= max([*series,self._max])
        # normalize
        scaled_samples = [x/self._max for x in series]
        heights=[ x*h for x in scaled_samples ]
        s_x=0
        for sample in heights:
            drawable.line([s_x,h,s_x,h-sample],fill=white, width=2)
            s_x = s_x + 2



if __name__ == "__main__":
    fb = Framebuffer()
    #print(f"{fb.size} {fb.bpp}")
    sent_sampler = IfSampler("eth0.2", "bytes_sent", 400)
    recv_sampler = IfSampler("eth0.2", "bytes_recv", 400)
    with fb as display:
        display.clear((128, 128, 128,255))

        sent = TitleDecorator(
            BorderDecorator(
                SeriesGraph(sent_sampler, size=(800,80)),
                border_width=24),
            "eth0.2:sent")
        recv = TitleDecorator(
            BorderDecorator(
                SeriesGraph(recv_sampler, size=(800,80)),
                border_width=24),
                "eth0.2:recv")
        widgets = [(sent, (40,40)), (recv, (40,160))]
        screen = Screen(display, widgets)

        loop=asyncio.get_event_loop()
        loop.set_debug(True)
        loop.create_task(sent_sampler.start())
        loop.create_task(recv_sampler.start())
        loop.create_task(screen.start())
        loop.run_forever()
