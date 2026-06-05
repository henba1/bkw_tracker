# bkw_tracker — Deye SUN300G3 solar pipeline

Continuously reads production data from a Deye `SUN300G3-EU-230` micro-inverter, publishes canonical MQTT metrics, and surfaces them in Home Assistant.

See [PLAN.md](PLAN.md) for the full architecture and phased rollout.

## Stack

| Service | Image | Role |
|---|---|---|
| Mosquitto | `eclipse-mosquitto:2` | MQTT broker (decoupling contract) |
| deye-bridge | `ghcr.io/kbialek/deye-inverter-mqtt:latest` | Solarman/Modbus → MQTT acquisition |
| Home Assistant | *(already running)* | MQTT consumer, Energy Dashboard |

## Repo layout

```
bkw_tracker/
├── mosquitto/          # broker compose + config
├── deye-bridge/        # acquisition compose + config.env
├── homeassistant/      # optional HA package (manual MQTT sensors)
├── docs/               # schema, inverter notes, morning checklist
└── scripts/            # smoke test, healthcheck, MQTT user setup
```

## First-time setup

### 1. MQTT broker password

```bash
./scripts/setup_mqtt_password.sh
```

Creates `mosquitto/config/passwd` for user `solar`. Prompts for a password interactively.

### 2. deye-bridge secrets

```bash
cp deye-bridge/config.env.example deye-bridge/config.env
# Edit logger IP/serial and MQTT password
```

`config.env` is gitignored.

### 3. Start Mosquitto

```bash
cd mosquitto && docker compose up -d
```

**Accept:** `mosquitto_sub -h 192.168.178.52 -u solar -P '<pw>' -t '#' -v` connects without error.

### 4. Start deye-bridge (after logger is online)

```bash
cd deye-bridge && docker compose up -d
```

**Accept:** `mosquitto_sub -h 192.168.178.52 -u solar -P '<pw>' -t 'solar/#' -v` shows metrics every ~30 s.

### 5. Home Assistant

Copy `homeassistant/packages/solar.yaml` into your HA `config/packages/` directory and reload MQTT entities, **or** rely on MQTT autodiscovery if your bridge publishes `homeassistant/` topics.

Point HA's MQTT integration at `192.168.178.52:1883` with user `solar`.

## Deploy to `/opt` (optional)

Matches the operator's existing per-service compose layout:

```bash
sudo mkdir -p /opt/mosquitto /opt/deye-bridge
sudo rsync -av mosquitto/ /opt/mosquitto/
sudo rsync -av deye-bridge/ /opt/deye-bridge/
cd /opt/mosquitto && sudo docker compose up -d
cd /opt/deye-bridge && sudo docker compose up -d
```

## Tomorrow morning — hardware gate

Follow [docs/MORNING_CHECKLIST.md](docs/MORNING_CHECKLIST.md) before starting the bridge.

Quick smoke test (requires daylight — WiFi module is solar-powered):

```bash
pip install ./pysolarmanv5
python scripts/smoke_read.py --ip 192.168.178.100 --serial 4145330384
```

## Rejected alternatives (for the record)

- **HA-native `ha-solarman` HACS** — simpler but couples inverter logic into HA; documented fallback only.
- **Modbus RS485 direct** — out of scope for read-only micro-inverter monitoring.
- **InfluxDB + Grafana** — optional Phase 6; HA Energy Dashboard is the primary goal.

## Swapping inverters

Edit **only** `deye-bridge/config.env` (logger IP, serial, protocol, metric groups). Downstream MQTT schema stays the same — see [docs/SCHEMA.md](docs/SCHEMA.md).
