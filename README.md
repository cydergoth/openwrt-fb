# openwrt-fb

## Introduction

Python Framebuffer (fb) monitoring for OpenWRT

This is a very minimal toolkit for displaying information from OpenWRT on an LCD
which is connected to a Linux Framebuffer device.

Specifically in this case, an Intel embedded "i915drmfb" driver on the i915 Chipset -
it works for me, but it may not work on your platform

It is deliberately designed to use only the python libraries available from OpenWRT stock builds via opkg


``` shell
okpg update
okpg install python3 # you may be able to get away with python3-light here
okpg install python3-pillow # Image and drawing library
okpg install python3-psutil # OS information library
```


## Running it

Entry point is network.py


``` shell
# python3 network.py
```

## Configuration

There is none. Edit it

## Interaction

There is none

## Windows

There is one - Screen - widgets are laid out on this according to their anchor and z order

## Future

Could this evolve into a system similar to MagicMirror2?

.... it's possible but unlikely
