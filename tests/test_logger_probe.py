"""Tests for resilience_lib.logger_probe."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from resilience_lib.logger_probe import ProbeResult, format_report, logger_reachable


def _ok(name: str) -> ProbeResult:
    return ProbeResult(name=name, ok=True, detail="open")


def _fail(name: str) -> ProbeResult:
    return ProbeResult(name=name, ok=False, detail="timed out")


# --- logger_reachable ---


def test_logger_reachable_true_when_tcp_ok():
    results = [_fail("icmp_ping"), _ok("tcp/80")]
    assert logger_reachable(results) is True


def test_logger_reachable_false_when_only_icmp_ok():
    """ICMP alone must not count as reachable — loggers often block ping."""
    results = [_ok("icmp_ping"), _fail("tcp/80"), _fail("udp/48899 WIFIKIT")]
    assert logger_reachable(results) is False


def test_logger_reachable_false_all_fail():
    results = [_fail("icmp_ping"), _fail("tcp/80"), _fail("tcp/8899")]
    assert logger_reachable(results) is False


def test_logger_reachable_true_on_udp_discovery():
    results = [_fail("icmp_ping"), _ok("udp/48899 WIFIKIT"), _fail("tcp/80")]
    assert logger_reachable(results) is True


def test_logger_reachable_empty_list():
    assert logger_reachable([]) is False


# --- format_report ---


def test_format_report_contains_ip():
    results = [_ok("tcp/80")]
    report = format_report("192.168.1.99", results)
    assert "192.168.1.99" in report


def test_format_report_reachable_summary():
    results = [_fail("icmp_ping"), _ok("tcp/8899")]
    report = format_report("10.0.0.1", results)
    assert "reachable" in report.lower()
    assert "unreachable" not in report.lower()


def test_format_report_unreachable_summary():
    results = [_fail("icmp_ping"), _fail("tcp/80")]
    report = format_report("10.0.0.1", results)
    assert "unreachable" in report.lower()


def test_format_report_ok_fail_labels():
    results = [_ok("tcp/80"), _fail("tcp/8899")]
    report = format_report("10.0.0.1", results)
    assert "[OK  ]" in report
    assert "[FAIL]" in report
