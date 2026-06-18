"""Tests for resilience_watcher module-level helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from resilience_watcher import env_bool, logger_status_topic, resilience_topic

# --- env_bool ---


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "True", "YES"])
def test_env_bool_truthy(monkeypatch, val):
    monkeypatch.setenv("MY_FLAG", val)
    assert env_bool("MY_FLAG") is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", ""])
def test_env_bool_falsy(monkeypatch, val):
    monkeypatch.setenv("MY_FLAG", val)
    assert env_bool("MY_FLAG") is False


def test_env_bool_unset_uses_default(monkeypatch):
    monkeypatch.delenv("MY_FLAG", raising=False)
    assert env_bool("MY_FLAG", default=True) is True
    assert env_bool("MY_FLAG", default=False) is False


# --- logger_status_topic ---


def test_logger_status_topic_default(monkeypatch):
    monkeypatch.delenv("SITE_ID", raising=False)
    monkeypatch.delenv("INVERTER_ID", raising=False)
    monkeypatch.delenv("MQTT_TOPIC_PREFIX", raising=False)
    monkeypatch.delenv("MQTT_TOPIC_DEVICE_STATUS", raising=False)

    topic = logger_status_topic()
    assert topic == "solar/home/inverter/logger_status"


def test_logger_status_topic_custom_site_inverter(monkeypatch):
    monkeypatch.setenv("SITE_ID", "garage")
    monkeypatch.setenv("INVERTER_ID", "deye1")
    monkeypatch.delenv("MQTT_TOPIC_PREFIX", raising=False)
    monkeypatch.delenv("MQTT_TOPIC_DEVICE_STATUS", raising=False)

    topic = logger_status_topic()
    assert topic == "solar/garage/deye1/logger_status"


def test_logger_status_topic_custom_prefix(monkeypatch):
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "myprefix/devices")
    monkeypatch.delenv("MQTT_TOPIC_DEVICE_STATUS", raising=False)

    topic = logger_status_topic()
    assert topic == "myprefix/devices/logger_status"


def test_logger_status_topic_custom_suffix(monkeypatch):
    monkeypatch.delenv("MQTT_TOPIC_PREFIX", raising=False)
    monkeypatch.setenv("SITE_ID", "home")
    monkeypatch.setenv("INVERTER_ID", "inverter")
    monkeypatch.setenv("MQTT_TOPIC_DEVICE_STATUS", "device_status")

    topic = logger_status_topic()
    assert topic == "solar/home/inverter/device_status"


# --- resilience_topic ---


def test_resilience_topic_default(monkeypatch):
    monkeypatch.delenv("SITE_ID", raising=False)
    monkeypatch.delenv("INVERTER_ID", raising=False)
    monkeypatch.delenv("MQTT_TOPIC_PREFIX", raising=False)

    topic = resilience_topic()
    assert topic == "solar/home/inverter/_meta/resilience"


def test_resilience_topic_custom_prefix(monkeypatch):
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "pv/main")
    topic = resilience_topic()
    assert topic == "pv/main/_meta/resilience"
