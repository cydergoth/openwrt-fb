import sys
import time
import logging
from fb import Framebuffer
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageColor import getrgb
import traceback
import PIL.features
from collections import namedtuple
from periodic import Periodic

Color = namedtuple("Color","r g b a")

white: Color = getrgb("white")
black: Color = getrgb("black")

if not PIL.features.check("freetype2"):
    print("ERROR: freetype2 isn't available", file=sys.stderr)
    sys.exit(1)

# Load a default font
font = ImageFont.truetype("inconsolata.ttf", 24)


class Widget:
    """Base class for all widgets"""

    def __init__(self,
                 size: (int, int),
                 background: Color = None # Set to None for no fill
                 ):
        """Create a new widget

        Parameters
        ----------
        size : (int, int)
             a formatted string to print out what the animal says
        drawable: ImageDraw
             the surface on which to render the widget
        background: Color
             the background color of the widget or None for transparent
        """
        self._size = size
        self._background = background
        self._img = Image.new("RGBA",size)
        self._drawable = ImageDraw.Draw(self._img)

    @property
    def size(self):
        """Get the size of this widget in pixels"""
        return self._size

    @property
    def img(self):
        return self._img

    @property
    def drawable(self):
        return self._drawable

    def draw(self):
        self.ddraw(self._drawable)
        return self._img

    def ddraw(self, drawable):
        (w,h) = self._size
        if self._background is not None:
            drawable.rectangle([0, 0, w, h],fill=self._background)


class TextWidget(Widget):
    """Widget to draw a line of text"""

    @classmethod
    def _get_size(cls,text:str,font):
        (x,y,w,h)=font.getbbox(text,anchor="la")
        return (w,h)

    def __init__(self,
                 text: str,
                 font: ImageFont=font,
                 background: Color=black,
                 foreground: Color=white, **kwargs):
        """Create a new TextWidget

        Parameters
        ----------
        text: string
            The text to render
        font: ImageFont
            The PIL font (truetype) to render the text with. Includes font size
        foreground: Color
            The color of the text
        **kwargs: map of arguments
            Passed to the superclass (Widget)
        """
        super().__init__(size=TextWidget._get_size(text, font), background=background, **kwargs)
        self._text=text
        self._font=font
        self._foreground=foreground

    def ddraw(self,drawable):
        super().ddraw(drawable)
        drawable.text((0,0), self._text, font=self._font, fill=self._foreground, anchor="la")


class WidgetDecorator(Widget):
    """Class for a widget which wraps another widget and adds extra decoration"""

    def __init__(self, widget: Widget, origin: (int,int)=(0,0), **kwargs):
        super().__init__(**kwargs)
        self._origin = origin
        self._widget = widget

    @property
    def widget(self):
        return self._property

    def ddraw(self,drawable: ImageDraw):
        super().ddraw(drawable)
        widget_img = self._widget.draw()
        self._img.alpha_composite(widget_img,self._origin)
        self._decorate(drawable)

    def decorate(self, drawable):
        pass


class TitleDecorator(WidgetDecorator):

    def __init__(self,
                 widget: Widget,
                 title: str,
                 font: ImageFont=font,
                 foreground: Color=white,
                 background: Color=black,
                 loc: str="top_left", **kwargs):
        super().__init__(widget,
                         size=widget.size,
                         background=background,
                         **kwargs)
        self._title = title
        self._font = font
        self._foreground = foreground
        self.loc = loc # Currently ignored, will be e.g. top_left etc
        self.draw()

    def _decorate(self,drawable):
        """Draw the decorator on the widget

        This method uses an explicit drawable
        """
        bbox=self._font.getbbox(self._title,anchor="la")
        (x,y,w,h)=bbox
        drawable.rectangle([x+24,0,w+24,h], fill=self._background)
        drawable.text((24,0),
                      self._title,
                      font=self._font,
                      fill=self._foreground,
                      anchor="la")


class BorderDecorator(WidgetDecorator):

    @classmethod
    def _get_size(cls, widget: Widget, border_width: int):
        (w,h)=widget.size
        return (w + border_width*2,h+border_width*2)

    def __init__(self,
                 widget: Widget,
                 border_color: Color=white,
                 border_width: int=6,
                 line_width: int=2,
                 **kwargs):
        super().__init__(widget,
                         origin=(border_width, border_width),
                         size=BorderDecorator._get_size(widget,border_width),**kwargs)
        self._border_color=border_color
        self._border_width=border_width
        self._line_width = line_width

    def _decorate(self, drawable: ImageDraw):
        (w,h)=self._size
        offset=self._border_width//2
        drawable.rectangle([offset, offset, w-offset, h-offset],
                                outline=self._border_color, width=self._line_width)



class Screen:

    def __init__(self, display, widgets: list[Widget]):
        self._display = display
        self._widgets = widgets
        self._periodic = Periodic(self._draw,5)
        self._screen = Image.new(mode="RGBA",size=fb.size)
        self._screen_drawable = ImageDraw.Draw(self._screen)
        #screen_drawable.text((10, 10), "eth0.2", fill=getrgb("white"))
        (w,h) = display.size
        self._screen_drawable.rectangle([0,0,w-1,h-1], outline=getrgb("white"), fill=None, width=2)
        self._draw()

    def _draw(self):
        for (widget, viewport) in self._widgets:
            try:
                img = widget.draw()
                self._screen.alpha_composite(img,viewport)
            except Exception as e:
                traceback.print_exc(e)
        self._display.write_screen(self._screen.tobytes())

    async def start(self):
        await self._periodic.start()


if __name__ == "__main__":
    fb = Framebuffer()
    with fb as display:
        display.clear((128, 128, 128,255))
        t = TextWidget("Hello World")
        w = TitleDecorator(BorderDecorator(t, border_width=24),"Title")
        widgets = [(w, (40,40))]
        screen = Screen(display, widgets)
