#!/usr/bin/env python3
"""Phase-0 smoke test: single SolarmanV5 Modbus read from the logger."""

import argparse
import os
import sys
from pathlib import Path


def load_stack_env() -> None:
    """Load stack.env into os.environ when not already set."""
    root = Path(__file__).resolve().parent.parent
    env_file = root / "stack.env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def main() -> int:
    load_stack_env()
    parser = argparse.ArgumentParser(description="Smoke-test a single Modbus read via SolarmanV5")
    parser.add_argument("--ip", default=os.environ.get("LOGGER_IP"), help="Logger IP (or set LOGGER_IP)")
    parser.add_argument(
        "--serial",
        type=int,
        default=int(os.environ["LOGGER_SERIAL"]) if os.environ.get("LOGGER_SERIAL") else None,
        help="Logger serial (or set LOGGER_SERIAL)",
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("LOGGER_PORT", "8899")))
    parser.add_argument("--register", type=lambda x: int(x, 0), default=0x3C, help="Holding register (0x3C = day energy)")
    args = parser.parse_args()

    if not args.ip or args.serial is None:
        print("Provide --ip/--serial or run via: ./scripts/stack.sh smoke", file=sys.stderr)
        return 1

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
