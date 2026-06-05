# Inverter notes — Deye SUN300G3-EU-230

Configure hardware-specific values in `stack.env`. Rendered into service configs via `./scripts/stack.sh render`.

## Label values

| Field | `stack.env` key | Default |
|---|---|---|
| Model | `HA_INVERTER_MODEL` | `SUN300G3-EU-230` |
| Inverter serial (QR sticker) | `LOGGER_SERIAL_FALLBACK` | `2208093531` |
| Logger serial (small S/N sticker) | `LOGGER_SERIAL` | `4145330384` |

## Network

| Setting | `stack.env` key | Notes |
|---|---|---|
| Broker host IP | `HOST_IP` | `auto` = detect at render time |
| Logger IP | `LOGGER_IP` | set after STA join + DHCP/lease confirm |
| Solarman TCP | `LOGGER_PORT` | `8899` |
| Discovery UDP | — | `48899`; optional, often silent on G3 |

## Power dependency

The built-in WIFI-G3 module is **solar-powered**. The logger is only reachable on the LAN during daylight.

## Protocol fallback order

1. `LOGGER_PROTOCOL=solarman_v5` port `8899`
2. `LOGGER_PROTOCOL=tcp` port `8899`
3. `LOGGER_PROTOCOL=at` port `48899`

## Metric group

`DEYE_METRIC_GROUPS=micro` — see [deye-inverter-mqtt micro docs](https://github.com/kbialek/deye-inverter-mqtt/blob/main/docs/metric_group_micro.md).
