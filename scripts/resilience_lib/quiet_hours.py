"""Local quiet-hours gate for logger resilience recovery."""

from __future__ import annotations

import os
from datetime import datetime, time

# No PV / logger sleep window for this deployment (local time on the host).
QUIET_HOURS_START = time(0, 0)
QUIET_HOURS_END = time(4, 45)


def env_bool(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def in_quiet_hours() -> bool:
    """Return True when recovery should stay idle (00:00 <= now < 04:45 local)."""
    if not env_bool("LOGGER_RESILIENCE_DAYLIGHT_ONLY", default=True):
        return False
    now = datetime.now().time()
    return QUIET_HOURS_START <= now < QUIET_HOURS_END


def quiet_hours_label() -> str:
    return f"{QUIET_HOURS_START.strftime('%H:%M')}–{QUIET_HOURS_END.strftime('%H:%M')} local"
