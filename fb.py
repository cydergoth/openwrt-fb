import os
import mmap
import traceback

class Framebuffer():

    def __init__(self, fbdev="fb0"):
        self._fbdev=fbdev
        self._fb = None
        self._fb_bytes = None

        with open(f"/sys/class/graphics/{fbdev}/name", "r") as f:
            data=f.read()
            self._name=data

        # Get screen size
        with open(f"/sys/class/graphics/{fbdev}/virtual_size", "r") as f:
            data = f.read()
            (x,y) = data.split(",")
            self._size = (int(x), int(y))

        # Get bit per pixel
        with open(f"/sys/class/graphics/{fbdev}/bits_per_pixel", "r") as f:
            self._bpp = int(f.read())


    @property
    def name(self):
        return self._name

    @property
    def fbdev(self):
        return self._fbdev

    @property
    def size(self):
        return self._size

    @property
    def bpp(self):
        return self._bpp

    def __enter__(self):
        # Open the framebuffer device
        self._fb = os.open(f"/dev/{self._fbdev}", os.O_RDWR)

        # Map framebuffer to memory
        (x,y) = self.size
        self._fb_bytes = mmap.mmap(self._fb, x*y*self.bpp//8, mmap.MAP_SHARED, mmap.PROT_WRITE|mmap.PROT_READ, offset=0)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
        self._fb_bytes.close()
        os.close(self._fb)

    # fill should be (rgba)
    def clear(self, fill):
        (r,g,b,a) = fill
        mapped = (b, g, r, a)
        (x,y) = self.size
        screen = bytearray(bytes(mapped))*x*y
        self._fb_bytes.write(screen)

    def write_screen(self,some_bytes):
        self._fb_bytes.seek(0)
        self._fb_bytes.write(some_bytes)


if __name__ == "__main__":
    fb0 = Framebuffer("fb0")
    with fb0 as display:
        display.clear((0,255,0,128))
