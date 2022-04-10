import os
import mmap 

class Framebuffer():
	def __init__(self, fbdev="fb0"):
		self.fbdev=fbdev
		with open(f"/sys/class/graphics/{fbdev}/name", "r") as f:
		   data=f.read()
		   self.name=data

		# Get screen size
		with open(f"/sys/class/graphics/{fbdev}/virtual_size", "r") as f:
			data = f.read()
			(x,y) = data.split(",")
			self.x = int(x)
			self.y = int(y)

		# Get bit per pixel
		with open(f"/sys/class/graphics/{fbdev}/bits_per_pixel", "r") as f:
         		self.bpp = int(f.read())

	def __enter__(self):
		# Open the framebuffer device
		self.fbdev = os.open(f"/dev/{self.fbdev}", os.O_RDWR)

		# Map framebuffer to memory
		self.fb = mmap.mmap(self.fbdev, self.x*self.y*self.bpp//8, mmap.MAP_SHARED, mmap.PROT_WRITE|mmap.PROT_READ, offset=0)
		return self

	def __exit__(self, exc_type, exc_value, tb):
		if exc_type is not None:
			traceback.print_exception(exc_type, exc_value, tb)
		self.fb.close()
		os.close(self.fbdev)

	def drawpixel(self, x, y, r, g, b, t=0):
		'''
		drawpixel function
		Draw a single pixel with color
		Require:
			x: x coordinate of the pixel
			y: y coordinate of the pixel
			
			RGB color:
				r: Red color (0 -> 255)
				g: Green color (0 -> 255)
				b: Blue color (0 -> 255)

			t: transparency (default set to 0)
		'''
		self.fb.seek((x+(y*self.x))*(self.bpp//8)) # Set the pixel location

		if self.bpp == 32:
			# 32 bit per pixel
			self.fb.write(b.to_bytes(1, byteorder='little')) # Write blue
			self.fb.write(g.to_bytes(1, byteorder='little')) # Write green
			self.fb.write(r.to_bytes(1, byteorder='little')) # Write red
			self.fb.write(t.to_bytes(1, byteorder='little')) # Write transparency

		else:
			# 16 bit per pixel
			self.fb.write(r.to_bytes(1, byteorder='little') << 11 | g.to_bytes(1, byteorder='little') << 5 | b.to_bytes(1, byteorder='little'))

	def clear(self, r=255, g=255, b=255, t=0):
		'''
		clear function
		Clear the screen with color
		Require:
			RGB color:
					r: Red color (0 -> 255)
					g: Green color (0 -> 255)
					b: Blue color (0 -> 255)

			t: transparency (default set to 0)
		'''
		for y in range(self.y):
			for x in range(self.x):
				self.drawpixel(x, y, r, g, b, t)

	def write_screen(self,some_bytes):
		self.fb.write(some_bytes)

if __name__ == "__main__":
	fb0 = Framebuffer("/dev/fb0")
	fb0.clear(r=255,g=255,b=255)
	#for y in range(fb0.y):
	#	for x in range(fb0.x):
	#		fb0.drawpixel(x, y, x%300, y%400, (x+y)%500)

