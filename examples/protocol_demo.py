#!/usr/bin/env python3
"""
Hello world -- no lamp, no Bluetooth required.

Builds the raw BLE frames for each command and prints them, so you can see the
`BC <cmd> <len> <data...> 55` protocol and the RGB->HSV conversion in action.

    python3 examples/protocol_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mrstar_light import (  # noqa: E402
    build_power, build_color_hsv, build_brightness, build_white,
    build_mode, build_speed, build_direction, MODES,
)


def show(label, frame):
    print(f"  {label:<22} {frame.hex(' ')}")


def main():
    print("Power:")
    show("on", build_power(True))
    show("off", build_power(False))

    print("\nColors (RGB -> HSV on the wire):")
    for label, rgb in [("red (255,0,0)", (255, 0, 0)),
                       ("green (0,255,0)", (0, 255, 0)),
                       ("warm (255,180,80)", (255, 180, 80))]:
        show(label, build_color_hsv(*rgb))
    show("white", build_white())

    print("\nBrightness / effects:")
    show("brightness 50%", build_brightness(50))
    show("mode 'running' (91)", build_mode(MODES["running"]))
    show("speed 40", build_speed(40))
    show("direction reverse", build_direction(forward=False))

    print("\nThese are exactly the bytes mrstar_light.py writes to")
    print("characteristic 0000fff3-... on a real GATT-DEMO light.")


if __name__ == "__main__":
    main()
