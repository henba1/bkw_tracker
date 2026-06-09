#!/usr/bin/env python3
"""Print lifetime total (kWh) at today's 03:00 local — for computed daily energy baseline."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

DB_PATH = Path("/config/home-assistant_v2.db")
CONFIG_PATH = Path("/config/.storage/core.config")
TOTAL_ENTITY = "sensor.deye_sun300g3_eu_230_solar_total_energy"


def homeassistant_timezone() -> ZoneInfo:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        tz_name = data.get("data", {}).get("time_zone", "Europe/Berlin")
        return ZoneInfo(tz_name)
    except (OSError, json.JSONDecodeError, KeyError):
        return ZoneInfo("Europe/Berlin")


def baseline_at_0300(entity_id: str) -> float | None:
    if not DB_PATH.is_file():
        return None

    tz = homeassistant_timezone()
    now_local = datetime.now(tz)
    at_local = datetime.combine(now_local.date(), time(3, 0), tzinfo=tz)
    at_ts = at_local.timestamp()

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT s.state
            FROM states s
            JOIN states_meta sm ON s.metadata_id = sm.metadata_id
            WHERE sm.entity_id = ?
              AND s.last_updated_ts <= ?
              AND s.state NOT IN ('unavailable', 'unknown', 'none', '')
            ORDER BY s.last_updated_ts DESC
            LIMIT 1
            """,
            (entity_id, at_ts),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    try:
        return float(row[0])
    except ValueError:
        return None


def main() -> int:
    value = baseline_at_0300(TOTAL_ENTITY)
    if value is None:
        print("unknown", file=sys.stderr)
        return 1
    print(f"{value:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
