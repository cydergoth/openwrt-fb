import sys
from fb import Framebuffer, Color, Dimension
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageColor import getrgb
import traceback
import PIL.features
from collections import namedtuple
from periodic import Periodic
from datetime import datetime, timezone
from typing import Tuple, Callable

# Define types so we can use type checking
Point = namedtuple("Point", "x y")

# Get the values for the default colors
white: Color = getrgb("white")
black: Color = getrgb("black")
green: Color = getrgb("green")
red: Color = getrgb("red")

# Bail if freetype isn't available
if not PIL.features.check("freetype2"):
    print("ERROR: freetype2 isn't available", file=sys.stderr)
    sys.exit(1)

# Load a default font
font = ImageFont.truetype("inconsolata.ttf", 24)


class Widget:
    """Base class for all widgets"""

    def __init__(self,
                 size: Dimension,
                 background: Color = None  # Set to None for no fill
                 ):
        """Create a new widget

        Parameters
        ----------
        size : Dimension
             a formatted string to print out what the animal says
        background: Color
             the background color of the widget or None for transparent
        """
        self._size = size
        self._background = background
        self._img = Image.new("RGBA", size)
        self._drawable = ImageDraw.Draw(self._img)

    @property
    def size(self) -> Dimension:
        """Get the size of this widget in pixels"""
        return self._size

    @property
    def img(self) -> Image:
        """Get the PIL image backing this widget"""
        return self._img

    @property
    def drawable(self) -> ImageDraw:
        """Get the widget's drawing surface"""
        return self._drawable

    def draw(self) -> Image:
        """Draw this widget into the backing image"""
        self.ddraw(self._drawable)
        return self._img

    def ddraw(self, drawable) -> None:
        """Draw the widget components into the widget's backing image
        using the drawing surface

        If background is set this will clear the widget image"""
        if self._background is not None:
            (w, h) = self._size
            drawable.rectangle([0, 0, w, h], fill=self._background)


class CarouselWidget(Widget):
    """Widget to cycle through a set of pages of other widgets"""

    def __init__(self,
                 pages: list[Tuple[int, list[Tuple[Widget, Point]]]],
                 background: Color = black,
                 **kwargs):
        """Create a new CarouselWidget

        Parameters
        ----------
        pages: list[Tuple[int, list[Tuple[Widget, Point]]]]
            a list of pages (delay, widgets) where widgets is list of (widget, origin)
        background: Color
            The background color for the entire text widget
        **kwargs: map of arguments
            Passed to the superclass (Widget)
        """
        super().__init__(**kwargs)
        self._last_displayed: int = 0
        self._pages: list[Tuple[int, list[Tuple[Widget, Point]]]] = pages
        self._page: int = 0
        self._delay: int = 0

    def _check_page(self):
        """Rotate the page if sufficient time has passed"""
        now = datetime.now().timestamp()
        if now - self._last_displayed > self._delay:
            self._last_displayed = now
            self._page = (self._page + 1) % len(self._pages)
            (self._delay, _) = self._pages[self._page]

    def ddraw(self, drawable):
        """Draw the widgets from the current page"""
        super().ddraw(drawable)
        self._check_page()
        (delay, page) = self._pages[self._page]
        for (widget, origin) in page:
            img = widget.draw()
            self._img.alpha_composite(img, origin)


class ClockWidget(Widget):

    @classmethod
    def _get_size(cls, text: str, font: ImageFont) -> Dimension:
        """Calculate the size of this widget based on the text"""
        (x, y, w, h) = font.getbbox(text, anchor="la")
        return Dimension(w, h)

    def __init__(self,
                 font: ImageFont = font,
                 background: Color = black,
                 foreground: Color = white,
                 **kwargs):
        """Create a new ClockWidget

        Parameters
        ----------
        font: ImageFont
            The PIL font (truetype) to render the text with. Includes font size!
        background: Color
            The background color for the entire text widget
        foreground: Color
            The color of the text
        **kwargs: map of arguments
            Passed to the superclass (Widget)
        """
        super().__init__(size=ClockWidget._get_size("XX:XX:XX", font),
                         background=background,
                         **kwargs)
        self._font: ImageFont = font
        self._foreground: Color = foreground

    def ddraw(self, drawable: ImageDraw) -> None:
        """Render the text into this widget"""
        super().ddraw(drawable)
        now = datetime.now(timezone.utc)
        now_str: str = now.astimezone().strftime("%H:%M:%S")
        drawable.text((0, 0), now_str, font=self._font, fill=self._foreground, anchor="ra")


class BarGaugeWidget(Widget):
    """Widget to draw a Bar Gauge, often used for percentages

    Parameters
    ----------
    value_reporter: Callable[[None]], float]
            a function which returns a value between 0 and 1 when called
    """
    def __init(self, value_reporter: Callable[[None], float], **kwargs):
        self._value_reporter = value_reporter

    def ddraw(self, drawable):
        (w, h) = self._size
        value = self._value_reporter()  # 0 .. 1
        split: int = round(self._size * value)
        drawable.rectangle([0, 0, h - split, w], fill=green)
        drawable.rectangle([0, h, split, w], fill=red)


class TextWidget(Widget):
    """Widget to draw a line of text"""

    @classmethod
    def _get_size(cls, text: str, font: ImageFont) -> Dimension:
        """Calculate the size of this widget based on the text"""
        (x, y, w, h) = font.getbbox(text, anchor="la")
        return Dimension(w, h)

    def __init__(self,
                 text: str,
                 font: ImageFont = font,
                 background: Color = black,
                 foreground: Color = white,
                 **kwargs):
        """Create a new TextWidget

        Parameters
        ----------
        text: string
            The text to render
        font: ImageFont
            The PIL font (truetype) to render the text with. Includes font size!
        background: Color
            The background color for the entire text widget
        foreground: Color
            The color of the text
        **kwargs: map of arguments
            Passed to the superclass (Widget)
        """
        super().__init__(size=TextWidget._get_size(text, font),
                         background=background,
                         **kwargs)
        self._text = text
        self._font = font
        self._foreground = foreground

    def ddraw(self, drawable: ImageDraw) -> None:
        """Render the text into this widget"""
        super().ddraw(drawable)
        drawable.text((0, 0), self._text, font=self._font, fill=self._foreground, anchor="la")


class WidgetDecorator(Widget):
    """Class for a widget which wraps another widget and adds extra decoration

    Decorator widgets always draw on top of their client widgets unless ddraw() is overridden
    """

    def __init__(self,
                 widget: Widget,
                 size: Dimension,
                 origin: Point = Point(0, 0),
                 **kwargs):
        """Create a new WidgetDecorator

        Parameters
        ----------
        widget: Widget
              the widget to wrap
        origin: Point
              where in the decorator widget the top left of the wrapped widget will be
        """
        super().__init__(size, **kwargs)
        self._origin = origin
        self._widget = widget

    @property
    def widget(self) -> Widget:
        """Get the wrapped widget"""
        return self._widget

    def ddraw(self, drawable: ImageDraw) -> None:
        """Draw the wrapped widget and decorate it"""
        super().ddraw(drawable)
        widget_img = self._widget.draw()
        self._img.alpha_composite(widget_img, self._origin)
        self._decorate(drawable)

    def _decorate(self, drawable: ImageDraw) -> None:
        """Draw the decorators on top of the wrapped widget"""
        pass


class TitleDecorator(WidgetDecorator):
    """Class for a widget which wraps another widget and adds a title decoration


    This widget is intended to be used as a wrapper for BorderDecorator
    so it assumes the space to render the title into will be provided
    by the underlying BorderDecorator"""

    def __init__(self,
                 widget: Widget,
                 title: str,
                 font: ImageFont = font,
                 foreground: Color = white,
                 background: Color = black,
                 loc: str = "top_left",
                 **kwargs):
        """Create a new TitleDecorator

        Parameters
        ----------

        widget: Widget
              the widget to wrap with this decorator
        title: str
              the title to display
        font: ImageFont
              font for the title
        """
        super().__init__(widget,
                         widget.size,
                         background=background,
                         **kwargs)
        self._title = title
        self._font = font
        self._foreground = foreground
        self.loc = loc  # Currently ignored, will be e.g. top_left etc

    def _decorate(self, drawable) -> None:
        """Draw the decorator on the widget

        This method uses an explicit drawable
        """
        bbox = self._font.getbbox(self._title, anchor="la")
        (x, y, w, h) = bbox
        drawable.rectangle([x+24, 0, w+24, h], fill=self._background)
        drawable.text((24, 0),
                      self._title,
                      font=self._font,
                      fill=self._foreground,
                      anchor="la")


class BorderDecorator(WidgetDecorator):
    """Decorator to render a border around another widget

    This decorator allocates a new Image with sufficient additional
    space for the border
    """

    @classmethod
    def _get_size(cls, widget: Widget, border_width: int) -> Dimension:
        """Calculate the additional size needed for the image with border"""
        (w, h) = widget.size
        return Dimension(w+border_width*2, h+border_width*2)

    def __init__(self,
                 widget: Widget,
                 border_color: Color = white,
                 border_width: int = 6,
                 line_width: int = 2,
                 **kwargs):
        """Create a new Border decorator

        Parameters
        ----------
        widget: Widget
              the widget to wrap
        border_color: Color
              color for the border
        border_width: int
              Total width of the space reserved for the border on each side
        line_width: int
              Width of the pen used to draw the border
        """
        super().__init__(widget,
                         BorderDecorator._get_size(widget, border_width),
                         origin=Point(border_width, border_width),
                         **kwargs)
        self._border_color = border_color
        self._border_width = border_width
        self._line_width = line_width

    def _decorate(self, drawable: ImageDraw) -> None:
        """Draw the client widget and decorate it with the border"""
        (w, h) = self._size
        offset = self._border_width//2
        if self._border_color is not None:
            drawable.rectangle([offset, offset, w-offset, h-offset],
                               outline=self._border_color,
                               width=self._line_width)


class Screen:
    """Screen widget which represents all the widgets on a screen"""

    def __init__(self,
                 display: Framebuffer,
                 widgets: list[tuple[Widget, Point]],
                 interval: int = 1):
        """Create a new screen for the specific display

        display: Framebuffer
                a simple python wrapper around the Linux framebuffer device
        widgets: list[Widget]
                a list of widgets in left to right Z-order (left is lowest)
        interval: int
                interval in seconds between screen refreshes
        """
        self._display = display
        self._widgets = widgets
        self._periodic = Periodic(self._draw, interval)
        self._screen = Image.new(mode="RGBA", size=display.size)
        self._screen_drawable = ImageDraw.Draw(self._screen)
        self.clear()
        self._draw()

    def clear(self, color: Color = black) -> None:
        """Clear the screen"""
        (w, h) = self._display.size
        self._screen_drawable.rectangle([0, 0, w, h], fill=color)
        self._display.write_screen(self._screen.tobytes())

    def _draw(self) -> None:
        """Draw all the widgets into the screen Image and send it to the Framebuffer"""
        for (widget, viewport) in self._widgets:
            try:
                img = widget.draw()
                self._screen.alpha_composite(img, viewport)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
        # Nasty trick to swap two of the channels for the specific
        # ordering of the framebuffer
        (r, g, b, a) = self._screen.split()
        im_bgr = Image.merge('RGBA', (b, g, r, a))
        self._display.write_screen(im_bgr.tobytes())

    async def start(self):
        """Start periodically rendering the screen"""
        await self._periodic.start()


if __name__ == "__main__":
    fb = Framebuffer()
    with fb as display:
        display.clear(Color(128, 128, 128, 255))
        t = TextWidget("Hello World")
        w = TitleDecorator(BorderDecorator(t, border_width=24), "Title")
        screen = Screen(display, [(w, Point(0, 0))])
