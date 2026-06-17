# mrstar-ble-light

Control cheap **"MR Star" / GATT-DEMO RGB BLE lights** from Python — no app, no
cloud. The result of reverse-engineering the undocumented GATT protocol these
lamps use.

If your RGB strip/lamp advertises over Bluetooth as **`GATT-DEMO`** and its
Android app is **"MR Star"** (`com.frok.mrstar`), this controls it directly.

## Protocol in one line

```
Write char 0000fff3-...   Frame:  BC <cmd> <len> <data...> 55   Colors in HSV
```

Full write-up (decompiled command table, how it was found): see
[`docs/ble_reverse_engineering.md`](docs/ble_reverse_engineering.md).

## Try it in 5 seconds (no lamp, no Bluetooth)

```bash
python3 examples/protocol_demo.py
```

Prints the raw frame bytes for every command and shows the RGB→HSV conversion —
the exact bytes the real control writes over BLE.

## Install

```bash
pip install bleak
```

## Use it with a real lamp

```bash
python3 examples/scan.py            # find your light's address
python3 mrstar_light.py on
python3 mrstar_light.py color 255 120 0     # RGB; auto-converted to HSV
python3 mrstar_light.py brightness 50
python3 mrstar_light.py mode running
python3 mrstar_light.py speed 40
python3 mrstar_light.py direction reverse
python3 mrstar_light.py list-modes
```

### Choosing the device

No MAC is hardcoded. The address is resolved, in order:

1. `--mac AA:BB:CC:DD:EE:FF`
2. `MRSTAR_MAC` environment variable
3. auto-scan for the first `GATT-DEMO` device

```bash
python3 mrstar_light.py --mac AA:BB:CC:DD:EE:FF green
export MRSTAR_MAC=AA:BB:CC:DD:EE:FF      # then omit --mac
```

## Use it as a library

```python
import asyncio
from mrstar_light import build_color_hsv, build_power, send

async def main():
    addr = "AA:BB:CC:DD:EE:FF"
    await send(addr, build_power(True), build_color_hsv(255, 0, 128))

asyncio.run(main())
```

All `build_*` functions are pure (return `bytes`), so they're trivial to test
or reuse without any Bluetooth stack.

## Notes

- The controller ignores color/effect changes while powered off, so the CLI
  sends "power on" before non-power commands automatically.
- Colors are HSV on the wire (hue 0–360, saturation 0–1000); RGB→HSV conversion
  is handled for you.
- Tested on Linux with BlueZ via `bleak`; `bleak` is cross-platform so macOS /
  Windows should work too.

## License

MIT — see [LICENSE](LICENSE).
