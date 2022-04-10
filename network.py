import time
import logging
from fb import Framebuffer
from PIL import Image, ImageDraw
from PIL.ImageColor import getrgb
from collections import deque
import psutil
import asyncio
from contextlib import suppress
import datetime
import traceback

logging.basicConfig(level=logging.INFO)


class IfSampler:

    def __init__(self, ifname, sample_len):
        self._ifname=ifname
        self._sample_len=sample_len
        self._buffer=deque(maxlen=sample_len)
        self._last_sample_ts=datetime.datetime.now()
        sample=psutil.net_io_counters(pernic=True)[self._ifname]
        (bytes_sent,bytes_recv,*_) = sample
        self._last_sample=(bytes_sent, bytes_recv)
        self._scrape=Periodic(self._do_scrape,5)

    async def start(self):
        return await self._scrape.start()

    def _do_scrape(self):
        sample=psutil.net_io_counters(pernic=True)[self._ifname]
        (bytes_sent,bytes_recv,*_) = sample
        (last_sent, last_recv) = self._last_sample
        sent_delta=bytes_sent - last_sent
        recv_delta=bytes_recv - last_recv
        self._last_sample = (bytes_sent, bytes_recv)
        self._last_sample_ts = datetime.datetime.now()
        delta=(sent_delta,recv_delta)
        self._buffer.append(delta)

    def copy(self):
        return self._buffer.copy()


class Periodic:
    def __init__(self, func, time):
        self._func = func
        self._time = time
        self._is_started = False
        self.__task = None

    async def start(self):
       if not self._is_started:
           self._is_started = True
           # Start task to call func periodically:
           self.__task = asyncio.ensure_future(self._run())

    async def stop(self):
       if self._is_started:
           self._is_started = False
           # Stop task and await it stopped:
           self.__task.cancel()
           with suppress(asyncio.CancelledError):
                await self.__task

    async def _run(self):
        while True:
           await asyncio.sleep(self._time)
           try:
                self._func()
           except Exception as e:
                traceback.print_exc(e)


class Graph:

    def __init__(self, ifname, size, sampler):
        self._ifname=ifname
        self._size=size
        self._img = Image.new(mode="RGBA", size=size)
        self._drawable = ImageDraw.Draw(self._img)
        self._sampler = sampler
        self._max = 10

    def draw(self):
        samples = self._sampler.copy()
        series = [x for (x,_) in samples]
        self._max= max([*series,self._max])
        # normalize
        scaled_samples = [x/self._max for x in series]
        (w,h) = self._size
        heights=[ x*h for x in scaled_samples]
        # Clear viewport
        self._drawable.rectangle([0,0,w,h],fill=getrgb("black"))
        s_x=0
        white = getrgb("white")
        for sample in heights:
            self._drawable.line([s_x,h,s_x,h-sample],fill=white)
            s_x = s_x + 1
        return self._img


class Screen:

    def __init__(self, display, widgets):
        self._display = display
        self._widgets = widgets
        self._periodic = Periodic(self._draw,5)
        self._screen = Image.new(mode="RGBA",size=fb.size)
        screen_drawable = ImageDraw.Draw(self._screen)
        screen_drawable.text((10, 10), "eth0.2", fill=getrgb("white"))
        (x,y) = display.size
        screen_drawable.rectangle([0,0,x-1,y-1], outline=getrgb("white"), fill=None, width=2)
        screen_data = self._screen.tobytes()
        display.write_screen(screen_data)

    def _draw(self):
        for (widget, viewport) in self._widgets:
            img = widget.draw()
            (x,y,_,_) = viewport
            self._screen.alpha_composite(img,(x,y))
        self._display.write_screen(self._screen.tobytes())

    async def start(self):
        await self._periodic.start()




if __name__ == "__main__":
    fb = Framebuffer()
    #print(f"{fb.size} {fb.bpp}")
    scraper = IfSampler("eth0.2", 800)
    with fb as display:
        display.clear((128, 128, 128,255))

        graph = Graph("eth0.2", (800,80), scraper)
        widgets = [(graph, (40,40,800,80))]
        screen = Screen(display, widgets)

        loop=asyncio.get_event_loop()
        loop.set_debug(True)
        loop.create_task(scraper.start())
        loop.create_task(screen.start())
        loop.run_forever()
