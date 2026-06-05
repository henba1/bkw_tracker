# Deye solar inverter monitoring

This software reads power and energy data from a **Deye micro-inverter** (e.g. SUN300G3) and makes it available for **Home Assistant** and other apps via MQTT.

You run it on a small always-on computer on your home network (for example a Raspberry Pi).

---

## Before you start

You will need:

| Item | Notes |
|---|---|
| A Raspberry Pi or similar | On the same Wi-Fi as the inverter, with Docker installed |
| Your inverter on the home Wi-Fi | Configured in the inverter’s settings (not only its own hotspot) |
| The inverter’s **network address** | From your router’s “connected devices” list (e.g. `192.178.152.42`) |
| Daylight (for first inverter test) | The inverter’s Wi-Fi module is powered by the solar panel |


---

## Setup (recommended — about 2 minutes)

Open a terminal in this folder and run:

```bash
./setup.sh
```

The wizard will ask you:

### 1. MQTT password

Choose a password (at least 8 characters). You will enter the same password later in Home Assistant.

This is **not** your Wi-Fi password — it only protects access to the solar data on your network.

### 2. Inverter IP address

The inverter’s address on your home network.

- **Inverter is on and producing?** Enter the IP from your router.
- **Inverter is off (night / no sun)?** Press Enter to skip — you can add it tomorrow.

### 3. Logger serial number

Printed on a **small sticker** on the inverter (10 digits, often starting with `41…`).

Press **Enter** to accept the default if it matches your sticker.

### What the wizard does automatically

- Saves your answers to `stack.env`
- Detects this computer’s network address (no need to type the Pi’s IP)
- Starts the MQTT message broker
- Optionally connects to the inverter (if you provided an IP and it responds)

When setup finishes, note the screen that shows:

```
This computer's address: 192.168.x.x
MQTT port: 1883
MQTT username: solar
MQTT password: (the one you just chose)
```

You need these four values for Home Assistant.

---

## Connect Home Assistant

1. In Home Assistant: **Settings → Devices & services → Add integration → MQTT**
2. Enter:
   - **Broker:** this Pi’s address from setup (e.g. `192.178.152.41`) — not the inverter IP
   - **Port:** `1883`
   - **Username:** `solar`
   - **Password:** the password you chose in `./setup.sh`
3. After the inverter is running, copy the generated sensor file:
   ```bash
   cp homeassistant/packages/solar.yaml <your-ha-config>/packages/
   ```
   Then reload MQTT in Home Assistant (or restart HA).

You should see sensors for AC power, today’s energy, total energy, voltage, and temperature.

---

## Add the inverter later (skipped IP during setup)

When the panel is producing and the inverter is on the network:

```bash
./setup.sh --add-inverter
```

Enter the inverter IP when asked. The script checks the connection and starts data collection.

---

## Daily use — useful commands

| What you want | Command |
|---|---|
| Check if services are running | `./scripts/stack.sh ps` |
| View live MQTT messages | `./scripts/stack.sh verify-broker` (Ctrl-C to stop) |
| Stop everything | `./scripts/stack.sh down` |
| Start everything | `./scripts/stack.sh up` |
| Test inverter connection | `./scripts/stack.sh smoke` |

---

## Troubleshooting

### “Could not reach the inverter”

- Wait until **daylight** — the inverter Wi-Fi needs solar power.
- Confirm the IP in your router’s device list.
- Run `./setup.sh --add-inverter` again with the correct IP.

### Setup worked but Home Assistant shows no data

- Inverter bridge not started yet → run `./scripts/stack.sh up`
- Wrong MQTT password in HA → must match `./setup.sh`
- HA package not installed → copy `homeassistant/packages/solar.yaml` into HA `packages/`

### Wrong logger serial

Edit `stack.env`, change `LOGGER_SERIAL=`, then:

```bash
./scripts/stack.sh render
./scripts/stack.sh up
```

If reads still fail, try `LOGGER_SERIAL_FALLBACK` value from [docs/INVERTER_NOTES.md](docs/INVERTER_NOTES.md).

### Start over from scratch

```bash
./scripts/stack.sh down
rm -f stack.env deye-bridge/config.env mosquitto/config/passwd
sudo rm -rf mosquitto/data
./setup.sh
```

---

## For advanced users

| Topic | Location |
|---|---|
| What to include in a release tarball | [PUBLISH.md](PUBLISH.md) |
| Full implementation plan *(dev only)* | [PLAN.md](PLAN.md) |
| MQTT topic schema | [docs/SCHEMA.md](docs/SCHEMA.md) |
| Inverter / protocol notes | [docs/INVERTER_NOTES.md](docs/INVERTER_NOTES.md) |
| Morning hardware checklist | [docs/MORNING_CHECKLIST.md](docs/MORNING_CHECKLIST.md) |
| Manual config (no wizard) | Copy `stack.env.example` → `stack.env`, use `./scripts/stack.sh` |
| All env variables | [stack.env.example](stack.env.example) |

Swapping to a different Deye inverter later: edit logger settings in `stack.env`, run `./scripts/stack.sh render && ./scripts/stack.sh up`.
