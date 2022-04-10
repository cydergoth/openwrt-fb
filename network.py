from fb import Framebuffer
from PIL import Image, ImageDraw

import psutil

fb = Framebuffer()

img = Image.new(mode="RGBA", size=(fb.x,fb.y))
draw_img = ImageDraw.Draw(img)

data = ['4','5','87','1','44','83','93','2','54','84','100','64'] 
x = 0

for i in data:
    x = x + 30  
    y = 200 - int(i) 
    draw_img.line((x,200,x,y), width=10, fill=(255,0,0,255))

with fb as display:
   display.write_screen(img.tobytes())
