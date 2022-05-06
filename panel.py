from widgets import BorderDecorator, TitleDecorator,  Widget, BarGaugeWidget
from network import IfSampler, SeriesGraph, SeriesGraphDecorator
from local_types import Color, Dimension, Point
from typing import Tuple
from PIL import ImageFont

MAX_SAMPLES: int = 400

GiB: int = 1024*1024*1024

graph_font = ImageFont.truetype("inconsolata.ttf", 24)


def panel(sent_sampler, recv_sampler) -> list[Tuple[Widget, Point]]:
    """Create a panel of statistics"""
    ssg = SeriesGraph(sent_sampler, size=Dimension(MAX_SAMPLES * 2, 80))
    ssgd = SeriesGraphDecorator(ssg, graph_font)
    sent = TitleDecorator(BorderDecorator(ssgd, border_width=24), "eth0:sent")
    recv = TitleDecorator(
        BorderDecorator(
            SeriesGraphDecorator(
                SeriesGraph(recv_sampler, size=Dimension(MAX_SAMPLES*2, 80)),
                graph_font),
            border_width=24),
        "eth0:recv")
    sent_bar = BarGaugeWidget(lambda : sent_sampler.last_sample/GiB, size=Dimension(40, 80))
    widgets: list[Tuple[Widget, Point]] = [(sent, Point(40, 40)), (recv, Point(40, 200)), (sent_bar, Point(1000, 60))]
    return widgets
