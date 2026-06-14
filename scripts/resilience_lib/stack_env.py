"""Load stack.env into os.environ."""

from __future__ import annotations

import os
from pathlib import Path


def stack_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_stack_env(*, root: Path | None = None) -> Path:
    root = root or stack_root()
    env_file = root / "stack.env"
    if not env_file.exists():
        return env_file
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)
    return env_file
