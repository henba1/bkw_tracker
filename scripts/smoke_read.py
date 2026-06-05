#!/usr/bin/env python3
"""Phase-0 smoke test: single SolarmanV5 Modbus read from the logger."""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a single Modbus read via SolarmanV5")
    parser.add_argument("--ip", default="192.168.178.100", help="Logger IP on the LAN")
    parser.add_argument("--serial", type=int, default=4145330384, help="Logger serial (not inverter QR)")
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--register", type=lambda x: int(x, 0), default=0x3C, help="Holding register (0x3C = day energy)")
    args = parser.parse_args()

    try:
        from pysolarmanv5 import PySolarmanV5
    except ImportError:
        print("Install pysolarmanv5 first: pip install ./pysolarmanv5", file=sys.stderr)
        return 1

    inv = PySolarmanV5(args.ip, args.serial, port=args.port, mb_slave_id=1, verbose=True)
    try:
        result = inv.read_holding_registers(register_addr=args.register, quantity=1)
        print(f"OK: register {args.register:#06x} = {result}")
        return 0
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        inv.disconnect()


if __name__ == "__main__":
    sys.exit(main())
