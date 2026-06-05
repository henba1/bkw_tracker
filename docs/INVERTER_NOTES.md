# Inverter notes — Deye SUN300G3-EU-230

## Label values

| Field | Value |
|---|---|
| Model | `SUN300G3-EU-230` |
| Rated output | 300 W / 230 Vac |
| Inverter serial (QR sticker) | `2208093531` |
| Logger serial (small S/N sticker) | `4145330384` ← use for SolarmanV5 auth |

## Network

| Setting | Value | Status |
|---|---|---|
| Intended static IP | `192.168.178.100` | configured on logger; confirm via router lease table tomorrow |
| Solarman TCP port | `8899` | required for polling |
| Discovery UDP port | `48899` | optional; may not respond on G3 firmware |
| Pi (broker host) | `192.168.178.52` | eth0 |

## Power dependency

The built-in WIFI-G3 module is **solar-powered**. The logger is only reachable on the LAN during daylight when the panel produces enough to power the WiFi module. Plan hardware tests for morning.

## Protocol fallback order

Test in this order if reads fail:

1. `DEYE_LOGGER_PROTOCOL=solarman_v5` port `8899` (G3 firmware with V5 handshake)
2. `DEYE_LOGGER_PROTOCOL=tcp` port `8899` (legacy Modbus/TCP)
3. `DEYE_LOGGER_PROTOCOL=at` port `48899` (UDP AT-Modbus — some G3 batches)

If timeouts occur with `at`, add `DEYE_LOGGER_MAX_REG_RANGE_LENGTH=16`.

## Serial ambiguity

If auth fails with `4145330384`, retry with inverter serial `2208093531`.

## Metric group

`DEYE_METRIC_GROUPS=micro` — register map in [deye-inverter-mqtt micro docs](https://github.com/kbialek/deye-inverter-mqtt/blob/main/docs/metric_group_micro.md).

Key registers for smoke test: holding `0x3C` (dec 60) = production today.
