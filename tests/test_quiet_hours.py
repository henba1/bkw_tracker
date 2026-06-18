"""Tests for resilience_lib.quiet_hours."""

from __future__ import annotations

import sys
from datetime import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from resilience_lib.quiet_hours import (
    QUIET_HOURS_END,
    QUIET_HOURS_START,
    env_bool,
    in_quiet_hours,
    quiet_hours_label,
)


@pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON"])
def test_env_bool_truthy_strings(monkeypatch, value):
    monkeypatch.setenv("TEST_FLAG", value)
    assert env_bool("TEST_FLAG") is True


@pytest.mark.parametrize("value", ["0", "false", "False", "no", "off", "", "random"])
def test_env_bool_falsy_strings(monkeypatch, value):
    monkeypatch.setenv("TEST_FLAG", value)
    assert env_bool("TEST_FLAG") is False


def test_env_bool_missing_uses_default(monkeypatch):
    monkeypatch.delenv("TEST_FLAG", raising=False)
    assert env_bool("TEST_FLAG", default=True) is True
    assert env_bool("TEST_FLAG", default=False) is False


def test_in_quiet_hours_inside_window(monkeypatch):
    monkeypatch.setenv("LOGGER_RESILIENCE_DAYLIGHT_ONLY", "1")
    # 02:30 is inside 00:00-04:45
    fake_time = time(2, 30)
    with patch("resilience_lib.quiet_hours.datetime") as mock_dt:
        mock_dt.now.return_value.time.return_value = fake_time
        assert in_quiet_hours() is True


def test_in_quiet_hours_outside_window(monkeypatch):
    monkeypatch.setenv("LOGGER_RESILIENCE_DAYLIGHT_ONLY", "1")
    fake_time = time(10, 0)
    with patch("resilience_lib.quiet_hours.datetime") as mock_dt:
        mock_dt.now.return_value.time.return_value = fake_time
        assert in_quiet_hours() is False


def test_in_quiet_hours_disabled_always_false(monkeypatch):
    monkeypatch.setenv("LOGGER_RESILIENCE_DAYLIGHT_ONLY", "false")
    # Even at 02:00 (inside window) it should return False when disabled
    fake_time = time(2, 0)
    with patch("resilience_lib.quiet_hours.datetime") as mock_dt:
        mock_dt.now.return_value.time.return_value = fake_time
        assert in_quiet_hours() is False


def test_quiet_hours_label_format():
    label = quiet_hours_label()
    start = QUIET_HOURS_START.strftime("%H:%M")
    end = QUIET_HOURS_END.strftime("%H:%M")
    assert label == f"{start}-{end} local"


def test_quiet_hours_boundary_start(monkeypatch):
    monkeypatch.setenv("LOGGER_RESILIENCE_DAYLIGHT_ONLY", "1")
    with patch("resilience_lib.quiet_hours.datetime") as mock_dt:
        mock_dt.now.return_value.time.return_value = QUIET_HOURS_START
        assert in_quiet_hours() is True


def test_quiet_hours_boundary_end(monkeypatch):
    monkeypatch.setenv("LOGGER_RESILIENCE_DAYLIGHT_ONLY", "1")
    # Exactly at end is NOT inside [start, end)
    with patch("resilience_lib.quiet_hours.datetime") as mock_dt:
        mock_dt.now.return_value.time.return_value = QUIET_HOURS_END
        assert in_quiet_hours() is False
