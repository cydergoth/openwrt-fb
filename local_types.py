from collections import namedtuple

# Define types so we can use type checking
Point = namedtuple("Point", "x y")
Dimension = namedtuple("Dimension", "w h")
Color = namedtuple("Color", "r g b a")
