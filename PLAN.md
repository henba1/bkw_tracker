> **Not shipped in end-user releases** — development artifact for coding agents and operators. See [PUBLISH.md](PUBLISH.md).

# Deye Inverter → Home Assistant Time-Series Pipeline — Implementation Plan

**Audience:** a coding agent (Claude Code or similar) plus the human operator.
**Goal:** continuously read production data from a Deye micro-inverter, store it as a queryable time-series, and surface it in Home Assistant dashboards. Architecture must tolerate swapping the inverter with **minimal** reconfiguration.

---

## 0. Hardware facts (from the inverter label)

| Field | Value |
|---|---|
| Model | Deye `SUN300G3-EU-230` (single-MPPT grid-tie micro-inverter, built-in WIFI-G3 logger) |
| Rated output | 300 W / 300 VA, 230 Vac, 50/60 Hz, 1.3 A |
| DC input | 25–55 Vdc operating, 60 Vdc max, 13 A max (single panel) |
| Inverter serial (QR sticker) | `2208093531` |
| **Logger serial (small S/N sticker)** | **`4145330384`** ← the SolarmanV5 tools need *this one* |

> **Critical disambiguation.** SolarmanV5 authenticates against the **data-logger** serial, not the inverter serial. `4145330384` is the likely logger serial (10 digits, matches the `41xx` micro-inverter logger family). **Do not trust this blindly** — confirm with `solarman_scan.py` in Phase 1. If polling auth fails, try `2208093531`.

---

## 1. Feasibility & protocol decision (resolved)

The WIFI-G3 logger exposes the **SolarmanV5** protocol on **TCP 8899** on the LAN. SolarmanV5 is a thin wrapper that tunnels **Modbus RTU** frames to the inverter. This is the local, cloud-free path. It is confirmed working for the `SUN###G3` micro family (300/600/800/…).

**Poll vs. push:**

- **Poll (recommended baseline).** Open a TCP socket to `logger_ip:8899`, send SolarmanV5-wrapped Modbus reads. Simple, no DNS tricks. The logger is the bottleneck.
- **Push (optional robustness upgrade, Phase 5).** Redirect the logger's cloud endpoint to a local "dummy cloud" that the inverter pushes to. More robust (no polling contention, keeps daily-energy counters correct) but requires DNS redirection. Defer unless polling proves flaky.

> **Push-back on the 5-second target.** These micro-inverter loggers refresh internal registers on the order of ~1 minute and reliably tolerate ~30–60 s polling. Polling faster than ~10 s causes TCP resets and contends with the logger's cloud uplink, with **no informational gain**: a 300 W single panel's output is smooth on second scales, and the stated use case (planning household consumption) operates on minute-to-hour scales. **Set `read_interval = 30 s`** as default; treat 5 s as out of scope. This is configurable if you disagree, but expect instability below ~15 s.

---

## 2. Architecture & the extensibility contract

The extensibility requirement is met by a single discipline: **decouple acquisition from storage/visualisation via a stable, vendor-neutral MQTT topic schema.** Inverter-specific knowledge lives *only* in the acquisition adapter. Everything downstream binds to the schema, not the hardware.

```
┌──────────────┐   SolarmanV5/Modbus    ┌─────────────────────┐
│ Deye logger  │  ◄──── TCP 8899 ─────► │ Acquisition adapter │  (vendor-specific layer)
│ (on LAN)     │                        │ deye-inverter-mqtt  │
└──────────────┘                        └─────────┬───────────┘
                                                   │ publishes CANONICAL schema
                                                   ▼
                                          ┌──────────────────┐
                                          │ MQTT (Mosquitto) │  ◄── the stable contract
                                          └─────────┬────────┘
                                                    │ HA MQTT autodiscovery
                                   ┌────────────────┼─────────────────┐
                                   ▼                ▼                 ▼
                          ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐
                          │ HA recorder + │ │ HA Energy    │ │ InfluxDB+Grafana │
                          │ long-term stat│ │ Dashboard    │ │ (optional, rich  │
                          │ (built-in)    │ │ (the goal)   │ │  historical viz) │
                          └───────────────┘ └──────────────┘ └──────────────────┘
```

**Swapping the inverter later:**

- *Same Deye family:* change `DEYE_METRIC_GROUPS`, logger serial, and IP. Nothing downstream changes.
- *Different brand:* replace the acquisition container with that brand's MQTT bridge **and map its output onto the same canonical topics** (a thin remap layer if its native topics differ). HA entities, dashboards, and Grafana panels are untouched.

### 2.1 Canonical MQTT topic schema (the abstraction boundary)

Define once; every adapter must conform. Prefix is configurable (`solar/<site>/<inverter_id>`).

| Canonical topic suffix | Unit | Meaning | Notes |
|---|---|---|---|
| `pv/power_w` | W | Instantaneous DC/PV power | primary live metric |
| `ac/power_w` | W | Instantaneous AC output power | what feeds the house |
| `ac/voltage_v` | V | Grid voltage | |
| `ac/current_a` | A | Output current | |
| `ac/frequency_hz` | Hz | Grid frequency | |
| `energy/today_kwh` | kWh | Energy produced today | resets at local midnight |
| `energy/total_kwh` | kWh | Lifetime energy | monotonic; use for HA `total_increasing` |
| `device/temperature_c` | °C | Inverter temperature | |
| `device/status` | enum | running/standby/fault | |
| `_meta/availability` | online/offline | LWT topic | drives HA `availability` |

`deye-inverter-mqtt` publishes near-equivalents already; the HA-discovery plugin maps them to entities. If the operator later forces strict canonical names, add a small remap (Section 6.4). Keep the schema in `docs/SCHEMA.md` under version control.

---

## 3. Software stack (chosen)

| Layer | Component | Why |
|---|---|---|
| Acquisition | **`ghcr.io/kbialek/deye-inverter-mqtt`** | Config-driven via env vars; has a dedicated `micro` metric group; supports micro-inverter fleets; actively maintained; HA-discovery plugin available. This *is* the vendor-abstraction layer. |
| HA-discovery | **`deye_plugin_ha_discovery`** plugin (bundled) | Auto-creates HA entities with correct `device_class`/`state_class`/units. No hand-written sensor YAML. |
| Transport | **Mosquitto** (`eclipse-mosquitto`) | Lightweight broker; the decoupling contract. |
| Hub | **Home Assistant Container** (already running) | MQTT integration consumes discovered entities. |
| Goal viz | **HA Energy Dashboard + long-term statistics** | Purpose-built for "production over time"; hourly stats retained indefinitely; zero extra infra. Solves the actual pain point. |
| Rich viz (optional) | **InfluxDB 2 + Grafana** | For high-resolution multi-week/month charts beyond HA's hourly long-term stats. Add only if HA's native history is insufficient. |

**Rejected / deferred alternatives (state in the repo README for the record):**
- *HA-native `davidrapan/ha-solarman` HACS integration* — simpler (no MQTT, no extra container), polls inside HA. **Rejected as primary** because it couples inverter logic into HA and weakens the brand-swap abstraction. Keep as documented fallback if MQTT proves overkill.
- *Modbus RS485 direct* — needs an RS485→TCP dongle; only required for *writing* to the inverter (charge schedules etc.), which is out of scope for a read-only micro-inverter.

---

## 4. Prerequisites (operator, blocking — do first)

The logger is currently **AP-only** (you disconnect from home Wi-Fi to reach it). It must join the home LAN as a client before anything can poll it.

1. Connect a laptop to the logger's AP. Open its config page (`http://10.10.100.254/` typical; hidden page `/config_hide.html` exposes more on G3 loggers).
2. Set the logger to **Station (STA) mode** and join the home Wi-Fi. Save/reboot.
3. Reconnect the laptop to home Wi-Fi. Find the logger's DHCP-assigned IP (router lease table or Pi-hole DHCP). **Reserve it as a static lease** — the whole pipeline depends on a stable IP.
4. Confirm the logger and its serial from Linux:
   ```bash
   git clone https://github.com/jmccrohan/pysolarmanv5
   python pysolarmanv5/utils/solarman_scan.py   # broadcasts; prints IP + logger serial
   ```
   Record the IP and the **logger serial it reports** — use that exact value downstream.
5. Smoke-test a single read before building anything:
   ```bash
   pip install pysolarmanv5
   python - <<'PY'
   from pysolarmanv5 import PySolarmanV5
   inv = PySolarmanV5("<LOGGER_IP>", <LOGGER_SERIAL>, port=8899, mb_slave_id=1, verbose=True)
   print(inv.read_holding_registers(register_addr=0x3C, quantity=1))  # adjust per micro reg map
   inv.disconnect()
   PY
   ```
   A non-empty response confirms the path. **Do not proceed past this until it works.**

> If STA mode is unstable or the AP refuses to join WPA3/your SSID: put the logger on a 2.4 GHz WPA2 SSID (these loggers are 2.4 GHz only and dislike WPA3).

---

## 5. Implementation phases

Each phase has an explicit **acceptance test**. Do not advance until it passes.

### Phase 1 — Repo & broker
- Create repo `solar-pipeline/` with the structure in Section 6.1.
- Deploy Mosquitto via its own `compose.yml` (per-service pattern matching the operator's existing `/opt/<service>/compose.yml` layout). Enable persistence; create an MQTT user `solar` (no anonymous access).
- **Accept:** `mosquitto_sub -h <pi-ip> -u solar -P <pw> -t '#' -v` connects and idles without error.

### Phase 2 — Acquisition (poll → MQTT)
- Deploy `deye-inverter-mqtt` with `config.env` (Section 6.2). Start with `LOG_LEVEL=DEBUG`, `DEYE_METRIC_GROUPS=micro`, `DEYE_DATA_READ_INTERVAL=30`.
- Try `DEYE_LOGGER_PROTOCOL=solarman_v5` first; fall back to `modbus_tcp` if reads fail.
- **Accept:** `mosquitto_sub -t 'solar/#' -v` shows `ac/power_w`, `energy/today_kwh`, `energy/total_kwh` updating every ~30 s; values are physically plausible (≤ ~300 W in daylight, 0 at night).

### Phase 3 — Home Assistant integration
- Enable the bundled HA-discovery plugin: `PLUGINS_ENABLED=deye_plugin_ha_discovery`, set `DEYE_HA_PLUGIN_INVERTER_MANUFACTURER=Deye`, `DEYE_HA_PLUGIN_INVERTER_MODEL=SUN300G3-EU-230`, `DEYE_HA_PLUGIN_EXPIRE_AFTER=120` (mark unavailable if no update in 120 s).
- Ensure HA's **MQTT integration** points at Mosquitto. Entities should appear automatically under a "Deye SUN300G3" device.
- **Accept:** an entity `sensor.deye_..._ac_power_w` exists, updates live, and has `device_class: power`, `state_class: measurement`. The lifetime-energy sensor has `state_class: total_increasing`.

### Phase 4 — Time-series storage & the dashboard (the actual goal)
- Verify HA **recorder** retains these sensors. Long-term statistics auto-aggregate hourly for `measurement`/`total_increasing` sensors.
- Configure the **HA Energy Dashboard**: add the lifetime-energy sensor (`energy/total_kwh`) as a solar production source. HA derives daily/weekly/monthly production curves from long-term stats.
- Build a Lovelace view: live AC power gauge, today's production, and a 7-/30-day production history (`statistics-graph` card).
- **Accept:** the Energy Dashboard shows a non-zero daily solar production bar and a multi-day history after one full day of running.

### Phase 5 — Resilience hardening (Section 7)
- Retry/backoff, container `restart: unless-stopped`, availability/LWT, watchdog.
- **Accept:** killing the logger's network for 5 min then restoring it → entities go `unavailable` then recover automatically without restarting any container.

### Phase 6 — *(Optional)* Rich historical viz: InfluxDB + Grafana
- Add InfluxDB 2 + Grafana containers. Forward HA sensors via HA's `influxdb:` integration **or** subscribe Grafana/Telegraf to MQTT directly (the latter keeps the chain HA-independent — better for the abstraction goal).
- Import a solar Grafana dashboard template; expose via the existing Caddy reverse proxy (`grafana.henpi`, `tls internal`, upstream `172.17.0.1:3000`).
- **Accept:** Grafana renders a daily production curve from stored data.

### Phase 7 — *(Optional)* Push model
- Deploy the `Hypfer/deye-microinverter-cloud-free` dummy-cloud; redirect the logger's cloud hostname (via Pi-hole DNS) to it. Replaces polling; keeps daily counters accurate.
- **Accept:** data flows to MQTT with the logger never reconnecting to the real cloud, and `energy/today_kwh` resets correctly at local midnight.

---

## 6. Concrete config & layout

### 6.1 Repo structure
```
solar-pipeline/
├─ README.md                 # stack rationale, rejected alternatives, runbook
├─ docs/
│  ├─ SCHEMA.md              # canonical MQTT topic schema (Section 2.1) — the contract
│  └─ INVERTER_NOTES.md      # label values, logger serial, reg-map quirks
├─ mosquitto/
│  ├─ compose.yml
│  └─ config/mosquitto.conf
├─ deye-bridge/
│  ├─ compose.yml
│  └─ config.env             # the ONLY file to touch when swapping a Deye model
├─ homeassistant/
│  └─ packages/solar.yaml    # any manual cards/template sensors (most is autodiscovered)
├─ influxdb-grafana/         # optional (Phase 6)
│  ├─ compose.yml
│  └─ grafana/provisioning/
└─ scripts/
   ├─ healthcheck.sh         # watchdog (Section 7)
   └─ smoke_read.py          # the Phase-0/1 single-read test
```

### 6.2 `deye-bridge/config.env` (fill the placeholders)
```env
LOG_LEVEL=INFO
# --- logger (the vendor-specific bit; the ONLY block to change per inverter) ---
DEYE_LOGGER_IP_ADDRESS=<LOGGER_STATIC_IP>
DEYE_LOGGER_PORT=8899
DEYE_LOGGER_SERIAL_NUMBER=4145330384      # verify via solarman_scan.py
DEYE_LOGGER_PROTOCOL=solarman_v5          # fallback: modbus_tcp
DEYE_METRIC_GROUPS=micro
DEYE_DATA_READ_INTERVAL=30
DEYE_PUBLISH_ON_CHANGE_MAX_INTERVAL=300   # heartbeat even if values are static
# DEYE_LOGGER_MAX_REG_RANGE_LENGTH=16     # uncomment if reads time out
# --- transport (stable contract) ---
MQTT_HOST=<PI_IP>
MQTT_PORT=1883
MQTT_USERNAME=solar
MQTT_PASSWORD=<MQTT_PW>
MQTT_TOPIC_PREFIX=solar/home/sun300g3
# --- HA autodiscovery ---
PLUGINS_ENABLED=deye_plugin_ha_discovery
DEYE_HA_PLUGIN_HA_MQTT_PREFIX=homeassistant
DEYE_HA_PLUGIN_INVERTER_MANUFACTURER=Deye
DEYE_HA_PLUGIN_INVERTER_MODEL=SUN300G3-EU-230
DEYE_HA_PLUGIN_EXPIRE_AFTER=120
```

### 6.3 `deye-bridge/compose.yml`
```yaml
services:
  deye-bridge:
    image: ghcr.io/kbialek/deye-inverter-mqtt:latest
    container_name: deye-bridge
    restart: unless-stopped
    env_file: ./config.env
    depends_on:
      - mosquitto   # only if same compose; otherwise rely on restart policy
```
> Bridge networking is fine here — it talks to the logger by **IP**, not container name, and to Mosquitto by IP. No `network_mode: host` needed (unlike HA).

### 6.4 Optional canonical remap
If `deye-inverter-mqtt`'s native topic names must be forced to the Section-2.1 schema, add a tiny subscriber that republishes `deye/.../active_power → solar/home/sun300g3/ac/power_w`. Keep it a separate ~30-line container so the contract stays explicit. Only build this if/when a non-Deye adapter is introduced.

---

## 7. Resilience requirements (must implement in Phase 5)

1. **Container policy:** `restart: unless-stopped` on every service.
2. **Reconnect/backoff:** the bridge already retries; ensure transient logger timeouts log at WARN, not crash. If it exits, the restart policy recovers it.
3. **Availability (LWT):** publish retained `_meta/availability=offline` as the MQTT Last Will; bridge sets `online` on connect. HA entities use this for `availability` → they show `unavailable` (not stale) when the logger drops.
4. **Staleness:** `DEYE_HA_PLUGIN_EXPIRE_AFTER=120` so a silent logger surfaces as unavailable rather than a frozen value.
5. **Monotonic energy:** map lifetime energy to `state_class: total_increasing` so HA handles midnight/counter resets correctly for the Energy Dashboard.
6. **Watchdog (`scripts/healthcheck.sh`, cron every 5 min):** if no MQTT message on `solar/#` for > N minutes during daylight, `docker restart deye-bridge` and log. (Guard with a sunrise/sunset check to avoid false alarms at night.)
7. **Static IP:** logger IP reserved in DHCP (Section 4.3). A changed lease silently breaks the pipeline.

---

## 8. Risks & open items

| Risk | Mitigation |
|---|---|
| Logger serial ambiguity (`4145330384` vs `2208093531`) | Resolve definitively with `solarman_scan.py` (Phase 4). |
| Logger AP-only / won't join LAN | 2.4 GHz WPA2 SSID; `/config_hide.html`; static lease. Blocking — Phase 0. |
| `micro` group reports wrong/empty metrics (G3 reg-map quirks) | Compare against `schwatter/solarman_mqtt` register list for `SUN600G3-230-EU` (same family); adjust group or add custom metrics YAML. |
| Polling instability | Raise interval to 60 s; lower `MAX_REG_RANGE_LENGTH`; escalate to Phase 7 push model. |
| Sub-15 s polling demanded | Documented as unsupported; expect resets (Section 1). |
| HA hourly long-term stats too coarse | Phase 6 InfluxDB+Grafana for high-res retention. |

---

## 9. Definition of done

- Logger on a static LAN IP, confirmed via `solarman_scan.py`.
- `deye-bridge` + Mosquitto running; canonical metrics on MQTT every ~30 s.
- HA shows a live "Deye SUN300G3" device with power/energy/voltage/temperature entities (autodiscovered).
- HA **Energy Dashboard** shows daily and multi-day solar production — the original objective.
- Network-drop test recovers automatically (Phase 5 accept test).
- Swapping a Deye model requires editing **only** `deye-bridge/config.env`; `docs/SCHEMA.md` documents the contract for non-Deye swaps.