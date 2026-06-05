# Canonical MQTT topic schema

Version: 1.0  
Prefix: `solar/<site>/<inverter_id>` → configured as `solar/home/sun300g3`

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
| `solar/home/sun300g3/status` | online/offline | Bridge ↔ broker connectivity (LWT) |
| `solar/home/sun300g3/logger_status` | online/offline | Bridge ↔ logger connectivity |

## HA entity mapping

| Canonical | HA `device_class` | HA `state_class` |
|---|---|---|
| `ac/power_w` | `power` | `measurement` |
| `energy/today_kwh` | `energy` | `total` |
| `energy/total_kwh` | `energy` | `total_increasing` |
| `ac/voltage_v` | `voltage` | `measurement` |
| `device/temperature_c` | `temperature` | `measurement` |

## Remap layer

`deye-inverter-mqtt` publishes native suffix names under `MQTT_TOPIC_PREFIX`. A strict canonical remap (Section 6.4 of PLAN.md) is **not required** while only Deye hardware is used — HA sensors in `homeassistant/packages/solar.yaml` bind directly to native topics.

Introduce a remap container only when adding a non-Deye adapter that uses different topic names.
