# Reverse engineering an MR Star / GATT-DEMO RGB BLE light

A write-up of how the BLE protocol for these cheap RGB lamps was recovered, in
case it helps anyone with the same hardware. The protocol turned out to be
poorly documented online, so the decompiled command table below is the useful
result.

## Device

- **BLE name**: `GATT-DEMO`
- **MAC**: varies per unit (find yours with `python3 examples/scan.py`)
- **Android app**: MR Star (`com.frok.mrstar`) on Google Play
- **Also ships with**: an IR remote + button

## Process

### 1. Pick a transport

The lamp ships with an app and an IR remote; the goal was programmatic control.
Options were IR (short range, line of sight), BLE, or Wi-Fi. IR was dropped for
range reasons. A BLE scan with `bleak` found a device advertising as
`GATT-DEMO`.

### 2. Explore the GATT services

With nRF Connect (Nordic Semiconductor) connected to the device:

| UUID | Type | Use |
|---|---|---|
| `0000FFF0-...` | Primary Service | Main service |
| `0000FFF3-...` | Write / Write No Response | Command channel |
| `0000FFF4-...` | Notify | Device responses |

### 3. Failed attempts with known protocols

The usual cheap-Chinese-BLE-light protocols were tried, all with no effect:

- `7E 00 04 F0 00 01 FF 00 EF` (Magic Home / WF-style, variant 1)
- `7E 04 04 F0 00 01 FF 00 EF` (Magic Home, variant 2)
- `56 FF 00 00 00 F0 AA` (Magic Home RGB direct)
- `CC 23 33` / `CC 24 33` (classic on/off)

### 4. Decompile the APK

The APK was pulled straight from the phone over ADB, no root needed:

```bash
adb shell pm path com.frok.mrstar
# /data/app/~~.../com.frok.mrstar-.../base.apk
adb pull /data/app/.../base.apk /tmp/mrstar.apk
```

Decompiled with [jadx](https://github.com/skylot/jadx) (needs Java):

```bash
jadx -d mrstar_java/ mrstar.apk
```

### 5. The real protocol, found in the code

In `com/findn/ui/fragment/AdjustFragment.java` the actual BLE writes appeared:

```java
// power
sendDataToBle(new byte[]{-68, 1, 1, 1, 85});  // on
sendDataToBle(new byte[]{-68, 1, 1, 0, 85});  // off

// color (HSV, not RGB)
sendDataToBle(new byte[]{-68, 4, 6, hue/256, hue%256, sat/256, sat%256, 0, 0, 85});

// brightness
sendDataToBle(new byte[]{-68, 5, 6, val/256, val%256, 0, 0, 0, 0, 85});
```

Java bytes are signed: `-68` = `0xBC`, `85` = `0x55`.

**Frame format**: `BC <cmd> <len> <data...> 55`

**Key detail**: colors go out in **HSV, not RGB**. The app converts internally
with `RgbUtils.getHsvFromRgb()`:
- Hue: 0–360 (integer)
- Saturation: 0–1000 (integer, i.e. `s * 1000`)

### 6. Command table

| Action | Bytes (hex) |
|---|---|
| Power on | `BC 01 01 01 55` |
| Power off | `BC 01 01 00 55` |
| Color (HSV) | `BC 04 06 [H/256] [H%256] [S/256] [S%256] 00 00 55` |
| Brightness (0-100) | `BC 05 06 00 [val] 00 00 00 00 55` |
| Color temperature | `BC 13 02 [val/256] [val%256] 55` |
| Animated mode (1–117) | `BC 06 02 [mode/255] [mode%255] 55` |
| Effect speed (0–100) | `BC 08 01 [speed] 55` |
| Direction forward | `BC 07 01 00 55` |
| Direction reverse | `BC 07 01 01 55` |

The APK groups effects into families:

| Modes | Family / examples |
|---|---|
| 1–32 | Basics: auto loop, symphony, jumps, strobe, gradient, flutter, brush |
| 35–44 | Opening & closing |
| 45–54 | Light/dark transitions |
| 55–62 | Running water |
| 63–75 | Flow |
| 76–83 | Trailing |
| 84–117 | Running, incl. colored dots over fixed backgrounds |

Examples:

```bash
python3 mrstar_light.py mode running    # mode 91: seven colors running
python3 mrstar_light.py mode 55         # seven colors, water style
python3 mrstar_light.py speed 50
python3 mrstar_light.py direction reverse
python3 mrstar_light.py list-modes
```

The script's named modes are a practical selection; any index 1–117 works.

### 7. Implementation

`mrstar_light.py` converts RGB→HSV internally so the interface stays natural.
Warm color example (`color 255 180 80`):
- RGB (255, 180, 80) → HSV (34°, 69%)
- Frame: `BC 04 06 00 22 02 AE 00 00 55`

## Tools used

- `bleak` (Python BLE) — scanning and sending commands
- nRF Connect (Android) — manual GATT exploration
- `adb` — pulling the APK without root
- `jadx` — decompiling the APK to readable Java
