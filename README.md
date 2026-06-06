<div align="center">

[![Documentation](https://img.shields.io/badge/📖_Documentation-GitHub_Pages-0969da?style=for-the-badge)](https://henba1.github.io/bkw_tracker/)

</div>

# Deye solar inverter monitoring

<p align="center">
  <a href="https://henba1.github.io/bkw_tracker/">
    <img src="assets/image.png" alt="Home Assistant Solar dashboard — AC power over 7 days" width="720">
  </a>
</p>

Reads power and energy from a **Deye micro-inverter** (tested on SUN300G3) and publishes to **MQTT** for **Home Assistant**.

Runs on a small always-on Linux host with Docker (e.g. Raspberry Pi).

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Host** | Linux with Docker and Docker Compose v2 |
| **Python** (optional) | 3.11+ with [uv](https://docs.astral.sh/uv/) — for discovery/smoke tools only |
| **Network** | Host on the same LAN as the inverter |
| **Inverter** | Joined to your home Wi-Fi (not only its AP hotspot) |
| **Daylight** | First inverter test needs sun — the built-in Wi-Fi module is solar-powered |
| **Home Assistant** | Optional but this repo targets it — see below |

### Home Assistant

Works with an **existing Home Assistant Docker container** (recommended on the same Pi):

- Container name defaults to `homeassistant` (`HA_CONTAINER` in `stack.env`)
- Config path is auto-detected from the container’s `/config` mount
- If HA uses **host networking** on the same machine as Mosquitto → broker is `127.0.0.1:1883` (default)
- If HA runs elsewhere → set `HA_CONFIG` to its config directory and `MQTT_BROKER_HOST` to this Pi’s LAN IP

This project runs **Mosquitto + deye-bridge** only — it does not install Home Assistant.

### Inverter (SUN300G3 defaults)

`stack.env.example` ships working defaults for SUN300G3 (`LOGGER_PROTOCOL=at`, `LOGGER_PORT=48899`). You still need:

- **Logger IP** — from your router’s device list (reserve a static DHCP lease)
- **Logger serial** — 10-digit sticker on the unit (often `41…`)

---

## Quick start

```bash
./setup.sh
```

The wizard asks for an MQTT password, inverter IP (skippable), and logger serial. It writes `stack.env`, starts Mosquitto, and optionally starts data collection.

Note the printed **host IP**, **MQTT port** (`1883`), **username** (`solar`), and **password** — needed if you configure HA manually.

```bash
./scripts/stack.sh up          # start broker + bridge
./scripts/stack.sh verify-metrics   # one MQTT reading (needs daylight + logger online)
```

---

## Home Assistant

One command installs sensors, Lovelace dashboard, and MQTT broker config (HA 2024+ requires broker via config entry, not YAML):

```bash
./scripts/install_ha_package.sh --restart
```

Then in HA: **Settings → Dashboards → Energy** → add solar production:

`sensor.deye_sun300g3_eu_230_solar_total_energy`

A **Solar** sidebar dashboard is added automatically. Entity names include the device prefix `deye_sun300g3_eu_230_…` — sensors show `unavailable` when the logger is offline (expected at night).

**Overrides** in `stack.env`: `HA_CONTAINER`, `HA_CONFIG`, `MQTT_BROKER_HOST`.

---

## Add inverter later

```bash
./setup.sh --add-inverter
```

---

## Commands

| Task | Command |
|---|---|
| Start stack | `./scripts/stack.sh up` |
| Stop stack | `./scripts/stack.sh down` |
| Service status | `./scripts/stack.sh ps` |
| Live MQTT traffic | `./scripts/stack.sh verify-broker` |
| Check metrics | `./scripts/stack.sh verify-metrics` |
| Install / update HA | `./scripts/install_ha_package.sh --restart` |
| Watchdog cron (optional) | `./scripts/install_healthcheck_cron.sh` |

Manual config: copy `stack.env.example` → `stack.env`, then `./scripts/stack.sh init`.

### Python tools (optional)

Discovery and smoke-test scripts use the `pysolarmanv5` submodule:

```bash
uv sync          # creates .venv, installs deps from pyproject.toml
uv run scripts/smoke_read.py --help
uv run solarman-uni-scan eth0
```

The Docker stack does not need Python — only these diagnostic commands do.

---

## Troubleshooting

**Inverter unreachable** — wait for daylight; confirm IP in router; run `./setup.sh --add-inverter`.

**HA shows no data** — run `./scripts/stack.sh up`; re-run `./scripts/install_ha_package.sh --restart`; check logger is online (`docker logs deye-bridge --tail 20`).

**Wrong serial** — edit `LOGGER_SERIAL` in `stack.env`, then `./scripts/stack.sh render && ./scripts/stack.sh up`. If reads still fail, try `LOGGER_SERIAL_FALLBACK`.

**Reads time out** — uncomment `DEYE_LOGGER_MAX_REG_RANGE_LENGTH=16` in `stack.env`.

**Different Deye model** — edit logger keys in `stack.env` (`LOGGER_PROTOCOL`, `LOGGER_PORT`, `HA_INVERTER_MODEL`), render, restart.

**Start over**

```bash
./scripts/stack.sh down
rm -f stack.env deye-bridge/config.env mosquitto/config/passwd
sudo rm -rf mosquitto/data
./setup.sh
```
