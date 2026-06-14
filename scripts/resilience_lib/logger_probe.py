"""LAN reachability probes for Deye WiFi loggers."""

from __future__ import annotations

import socket
import subprocess
import time
from dataclasses import dataclass

WIFIKIT_MAGIC = b"WIFIKIT-214028-READ"
HF_MAGIC = b"HF-A11ASSISTHREAD"
DEFAULT_TCP_PORTS = (80, 8899)
DEFAULT_TIMEOUT = 2.0


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str


def ping_host(ip: str, timeout: float) -> ProbeResult:
    try:
        completed = subprocess.run(
            ["ping", "-c", "1", "-W", str(max(1, int(timeout)))],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return ProbeResult("icmp_ping", True, "host replied to ping")
        return ProbeResult("icmp_ping", False, "no ping reply (many loggers block ICMP)")
    except FileNotFoundError:
        return ProbeResult("icmp_ping", False, "ping command not available")


def tcp_connect(ip: str, port: int, timeout: float) -> ProbeResult:
    label = f"tcp/{port}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        banner = ""
        try:
            sock.settimeout(0.5)
            chunk = sock.recv(256)
            if chunk:
                banner = chunk.decode(errors="replace").strip()
        except OSError:
            pass
        detail = "port open"
        if banner:
            detail = f"port open, banner={banner[:120]!r}"
        return ProbeResult(label, True, detail)
    except TimeoutError:
        return ProbeResult(label, False, "connection timed out")
    except OSError as exc:
        return ProbeResult(label, False, str(exc))
    finally:
        sock.close()


def udp_wifi_discovery(ip: str, timeout: float) -> ProbeResult:
    for magic, label in ((WIFIKIT_MAGIC, "udp/48899 WIFIKIT"), (HF_MAGIC, "udp/48899 HF-A11")):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(magic, (ip, 48899))
            data, _addr = sock.recvfrom(1024)
            text = data.decode(errors="replace").strip()
            parts = text.split(",")
            if len(parts) == 3:
                reported_ip, mac, serial = parts
                return ProbeResult(
                    label,
                    True,
                    f"logger responded: ip={reported_ip} mac={mac} serial={serial}",
                )
            return ProbeResult(label, True, f"unexpected payload: {text!r}")
        except TimeoutError:
            continue
        except OSError as exc:
            return ProbeResult(label, False, str(exc))
        finally:
            sock.close()
    return ProbeResult("udp/48899 discovery", False, "no reply to WIFIKIT or HF-A11 probes")


def run_probe(ip: str, tcp_ports: tuple[int, ...] = DEFAULT_TCP_PORTS, timeout: float = DEFAULT_TIMEOUT) -> list[ProbeResult]:
    results = [ping_host(ip, timeout)]
    results.append(udp_wifi_discovery(ip, timeout))
    results.extend(tcp_connect(ip, port, timeout) for port in tcp_ports)
    return results


def logger_reachable(results: list[ProbeResult]) -> bool:
    return any(r.ok for r in results if r.name != "icmp_ping")


def wakeup_logger(
    ip: str,
    *,
    attempts: int,
    interval_sec: float,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bool, list[ProbeResult]]:
    """Send spaced UDP discovery probes; return on first success."""
    last_results: list[ProbeResult] = []
    for attempt in range(1, attempts + 1):
        result = udp_wifi_discovery(ip, timeout)
        last_results = [result]
        if result.ok:
            return True, last_results
        if attempt < attempts:
            time.sleep(interval_sec)
    return False, last_results


def format_report(ip: str, results: list[ProbeResult]) -> str:
    lines = [
        f"Logger probe for {ip} @ {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "-" * 72,
    ]
    for result in results:
        status = "OK" if result.ok else "FAIL"
        lines.append(f"[{status:4}] {result.name:24} {result.detail}")
    lines.append("-" * 72)
    if logger_reachable(results):
        lines.append("Summary: logger reachable on at least one service port (ICMP may still fail).")
    else:
        lines.append("Summary: logger unreachable on all probed ports — WiFi module likely down or wrong IP.")
    return "\n".join(lines)
