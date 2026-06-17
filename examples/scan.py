#!/usr/bin/env python3
"""
Scan for nearby BLE devices and highlight likely MR Star / GATT-DEMO lights.

    python3 examples/scan.py
"""
import asyncio

from bleak import BleakScanner

TARGET = "GATT-DEMO"


async def main():
    print("Scanning 10s...")
    devices = await BleakScanner.discover(timeout=10)
    for d in sorted(devices, key=lambda x: x.name or "~"):
        mark = "  <-- looks like an MR Star light" if (d.name or "") == TARGET else ""
        print(f"  {d.address}  {d.name or '(no name)'}{mark}")


if __name__ == "__main__":
    asyncio.run(main())
