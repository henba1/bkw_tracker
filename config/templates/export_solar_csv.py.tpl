#!/usr/bin/env python3
"""Export solar entity time series from Home Assistant recorder to CSV."""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path("/config/home-assistant_v2.db")
EXPORT_DIR = Path("/config/exports")
ENTITY_PREFIXES = ("sensor.${HA_ENTITY_SLUG}", "binary_sensor.${HA_ENTITY_SLUG}")


def export_solar_csv() -> Path:
    if not DB_PATH.is_file():
        msg = f"Recorder database not found: {DB_PATH}"
        raise SystemExit(msg)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = EXPORT_DIR / f"solar_timeseries_{stamp}.csv"

    conn = sqlite3.connect(DB_PATH)
    try:
        placeholders = " OR ".join("sm.entity_id LIKE ?" for _ in ENTITY_PREFIXES)
        like_args = tuple(f"{prefix}%" for prefix in ENTITY_PREFIXES)
        query = f"""
            SELECT sm.entity_id, s.last_updated_ts, s.state
            FROM states s
            JOIN states_meta sm ON s.metadata_id = sm.metadata_id
            WHERE {placeholders}
            ORDER BY s.last_updated_ts ASC, sm.entity_id ASC
        """
        rows = conn.execute(query, like_args).fetchall()
    finally:
        conn.close()

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp_utc", "entity_id", "state"])
        for entity_id, ts, state in rows:
            if ts is None:
                continue
            ts_iso = datetime.fromtimestamp(float(ts), tz=UTC).isoformat()
            writer.writerow([ts_iso, entity_id, state])

    print(out_path)
    return out_path


if __name__ == "__main__":
    try:
        path = export_solar_csv()
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    sys.exit(0)
