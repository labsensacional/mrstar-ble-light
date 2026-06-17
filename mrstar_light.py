#!/usr/bin/env python3
"""
Control an "MR Star" / GATT-DEMO RGB BLE light from Python.

These cheap RGB strips/lamps (BLE name `GATT-DEMO`, Android app "MR Star",
`com.frok.mrstar`) speak an undocumented GATT protocol. This is the result of
reverse-engineering it: see docs/ble_reverse_engineering.md.

Protocol summary
----------------
  Write characteristic: 0000fff3-0000-1000-8000-00805f9b34fb
  Frame:  BC <cmd> <len> <data...> 55
  Colors are sent in HSV, not RGB:  hue 0-360, saturation 0-1000.

The build_* functions are pure (no Bluetooth) so you can test the protocol
without a lamp -- see examples/protocol_demo.py.

Usage
-----
  python3 mrstar_light.py on
  python3 mrstar_light.py color 255 120 0      # RGB; converted to HSV for you
  python3 mrstar_light.py brightness 50
  python3 mrstar_light.py mode running
  python3 mrstar_light.py speed 40
  python3 mrstar_light.py list-modes

Device address (first match wins):
  --mac AA:BB:CC:DD:EE:FF   |   env MRSTAR_MAC   |   auto-scan for "GATT-DEMO"
"""
import argparse
import asyncio
import colorsys
import os
import sys

WRITE_CHAR = "0000fff3-0000-1000-8000-00805f9b34fb"
DEVICE_NAME = "GATT-DEMO"

# --- Protocol (pure, no Bluetooth) ---------------------------------------

def build_power(on: bool) -> bytes:
    return bytes([0xBC, 0x01, 0x01, 0x01 if on else 0x00, 0x55])


def build_color_hsv(r: int, g: int, b: int) -> bytes:
    """RGB 0-255 -> device HSV frame (hue 0-360, saturation 0-1000)."""
    h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = int(h * 360)
    sat = int(s * 1000)
    return bytes([0xBC, 0x04, 0x06, hue // 256, hue % 256, sat // 256, sat % 256, 0, 0, 0x55])


def build_brightness(pct: int) -> bytes:
    """Brightness 0-100 (clamped to a visible minimum of 3)."""
    val = max(3, min(100, pct))
    return bytes([0xBC, 0x05, 0x06, val // 256, val % 256, 0, 0, 0, 0, 0x55])


def build_white() -> bytes:
    return bytes([0xBC, 0x13, 0x02, 0x00, 0x00, 0x55])


def build_mode(index: int) -> bytes:
    """Animated effect, 1-117 (see MODES for friendly aliases)."""
    if not 1 <= index <= 117:
        raise ValueError("mode must be 1-117")
    return bytes([0xBC, 0x06, 0x02, index // 255, index % 255, 0x55])


def build_speed(value: int) -> bytes:
    return bytes([0xBC, 0x08, 0x01, max(0, min(100, value)), 0x55])


def build_direction(forward: bool) -> bytes:
    return bytes([0xBC, 0x07, 0x01, 0x00 if forward else 0x01, 0x55])


# A practical subset of the 1-117 effects; any index in range also works.
MODES = {
    "auto": 1, "symphony": 2, "energy": 3, "jumps": 4, "strobe": 7,
    "gradient": 10, "flutter": 26, "rgb-flutter": 27, "brush": 29,
    "opening": 35, "transition": 45, "water": 55, "flow": 63,
    "trailing": 76, "running": 91,
}

NAMED_COLORS = {
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
    "yellow": (255, 255, 0), "purple": (128, 0, 255), "orange": (255, 90, 0),
    "cyan": (0, 255, 255), "pink": (255, 60, 120),
}


# --- BLE transport --------------------------------------------------------

async def resolve_address(explicit: str | None) -> str:
    addr = explicit or os.environ.get("MRSTAR_MAC")
    if addr:
        return addr
    from bleak import BleakScanner
    print(f"Scanning for a '{DEVICE_NAME}' device... (set --mac to skip)")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10)
    if not device:
        raise SystemExit(f"No '{DEVICE_NAME}' device found. Pass --mac or set MRSTAR_MAC.")
    print(f"Found {device.address}")
    return device.address


async def send(address: str, *frames: bytes, retries: int = 3):
    from bleak import BleakClient
    for attempt in range(retries):
        try:
            async with BleakClient(address, timeout=10) as client:
                for frame in frames:
                    await client.write_gatt_char(WRITE_CHAR, frame, response=False)
                    await asyncio.sleep(0.2)
                return
        except Exception:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(1)


# --- CLI ------------------------------------------------------------------

def parse_command(args: list[str]) -> tuple[bytes, bool]:
    """Return (frame, is_power_command). Raises ValueError on bad input."""
    cmd = args[0].lower()
    if cmd in ("on", "off"):
        return build_power(cmd == "on"), True
    if cmd in ("white", "warm"):
        return build_white(), False
    if cmd in NAMED_COLORS:
        return build_color_hsv(*NAMED_COLORS[cmd]), False
    if cmd == "color" and len(args) == 4:
        return build_color_hsv(int(args[1]), int(args[2]), int(args[3])), False
    if cmd == "brightness" and len(args) == 2:
        return build_brightness(int(args[1])), False
    if cmd == "mode" and len(args) == 2:
        token = args[1].lower()
        index = MODES.get(token, int(token) if token.isdigit() else 0)
        return build_mode(index), False
    if cmd == "speed" and len(args) == 2:
        return build_speed(int(args[1])), False
    if cmd == "direction" and len(args) == 2:
        return build_direction(args[1].lower() == "forward"), False
    raise ValueError(f"unknown or malformed command: {' '.join(args)}")


def print_help():
    print(__doc__)
    print("Named colors:", ", ".join(NAMED_COLORS))


async def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mac")
    parser.add_argument("words", nargs="*")
    args = parser.parse_args()

    if not args.words or args.words[0] in ("-h", "--help", "help"):
        print_help()
        return
    if args.words[0] == "list-modes":
        for name, index in sorted(MODES.items(), key=lambda x: x[1]):
            print(f"{index:3}  {name}")
        return

    try:
        frame, is_power = parse_command(args.words)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    address = await resolve_address(args.mac)
    # The controller ignores color/effect changes while powered off.
    if is_power:
        await send(address, frame)
    else:
        await send(address, build_power(True), frame)
    print(f"OK: {frame.hex()}")


if __name__ == "__main__":
    asyncio.run(main())
