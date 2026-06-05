> **Not shipped in end-user releases** — integrator / multi-vendor contract doc. See [PUBLISH.md](../PUBLISH.md).

# Canonical MQTT topic schema

Version: 1.0  
Prefix: `solar/<SITE_ID>/<INVERTER_ID>` — derived from `stack.env` (`SITE_ID`, `INVERTER_ID`) unless `MQTT_TOPIC_PREFIX` is set explicitly.

This is the **stable contract** between acquisition and all downstream consumers (HA, Grafana, watchdog). Inverter-specific knowledge lives only in `deye-bridge/config.env`.

## Topics

| Suffix | Unit | Meaning | deye-bridge `micro` equivalent |
|---|---|---|---|
| `pv/power_w` | W | Instantaneous DC/PV power | `dc/pv1/power` (single MPPT) |
| `ac/power_w` | W | Instantaneous AC output | `ac/active_power` |
| `ac/voltage_v` | V | Grid voltage | `ac/l1/voltage` |
| `ac/current_a` | A | Output current | `ac/l1/current` |
| `ac/frequency_hz` | Hz | Grid frequency | `ac/freq` |
| `energy/today_kwh` | kWh | Energy today (resets midnight) | `day_energy` |
| `energy/total_kwh` | kWh | Lifetime energy (monotonic) | `total_energy` |
| `device/temperature_c` | °C | Inverter temperature | `radiator_temp` |
| `device/status` | enum | running/standby/fault | *(derived — not native)* |
| `_meta/availability` | online/offline | Bridge LWT | `{prefix}/status` |

## Status topics (native)

deye-inverter-mqtt also publishes:

| Topic | Values | Meaning |
|---|---|---|
| `<MQTT_TOPIC_PREFIX>/status` | online/offline | Bridge ↔ broker connectivity (LWT) |
| `<MQTT_TOPIC_PREFIX>/logger_status` | online/offline | Bridge ↔ logger connectivity |

## HA entity mapping

| Canonical | HA `device_class` | HA `state_class` |
|---|---|---|
| `ac/power_w` | `power` | `measurement` |
| `energy/today_kwh` | `energy` | `total` |
| `energy/total_kwh` | `energy` | `total_increasing` |
| `ac/voltage_v` | `voltage` | `measurement` |
| `device/temperature_c` | `temperature` | `measurement` |

## Remap layer

`deye-inverter-mqtt` publishes native suffix names under `MQTT_TOPIC_PREFIX` from `stack.env`. HA sensors are rendered into `homeassistant/packages/solar.yaml` from `config/templates/solar.yaml.tpl`.

Introduce a remap container only when adding a non-Deye adapter that uses different topic names.
