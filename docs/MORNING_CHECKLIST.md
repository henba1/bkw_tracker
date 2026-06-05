> **Not shipped in end-user releases** — operator bring-up checklist. See [PUBLISH.md](../PUBLISH.md).

# Morning checklist — hardware gate

Run in order. Do not start `deye-bridge` until step 4 passes.

## 1. Confirm logger is on the LAN

- [ ] Sun is up; panel is producing (WiFi module needs PV power).
- [ ] Router DHCP/connected-devices shows the Deye logger.
- [ ] Set `LOGGER_IP` in `stack.env` to the **actual** address.
- [ ] Run `./scripts/stack.sh render`.

## 2. Layer-3 reachability (from Pi)

```bash
source <(grep -v '^#' stack.env | grep -v '^$' | sed 's/^/export /')
ping -c 2 "$LOGGER_IP"
nc -zv "$LOGGER_IP" "$LOGGER_PORT"
```

- [ ] Ping or HTTP succeeds.
- [ ] Port 8899 is open.
- check 

## 3. Discovery (optional — serial confirmation)

```bash
cd pysolarmanv5
python utils/solarman_uni_scan.py eth0
```

- [ ] Serial matches `LOGGER_SERIAL` in `stack.env`, or note the actual value and update `stack.env`.

## 4. Smoke test (blocking gate)

```bash
pip install ./pysolarmanv5
./scripts/stack.sh smoke
```

If auth fails, set `LOGGER_SERIAL` to `LOGGER_SERIAL_FALLBACK` in `stack.env` and retry.

- [ ] Prints `OK: register 0x003c = [...]`.

## 5. Start the stack

```bash
./scripts/stack.sh up
```

## 6. Verify MQTT flow

```bash
./scripts/stack.sh verify-broker
# in another terminal, filter topics:
mosquitto_sub -h "$HOST_IP" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "${MQTT_TOPIC_PREFIX}/#" -v
```

- [ ] `ac/active_power`, `day_energy`, `total_energy` update every ~30 s.

## 7. Protocol fallback (only if bridge logs show read timeouts)

Edit `LOGGER_PROTOCOL` in `stack.env`:

| Attempt | `LOGGER_PROTOCOL` | `LOGGER_PORT` |
|---|---|---|
| 1 (default) | `solarman_v5` | `8899` |
| 2 | `tcp` | `8899` |
| 3 | `at` | `48899` (+ `DEYE_LOGGER_MAX_REG_RANGE_LENGTH=16` in template/stack) |

```bash
./scripts/stack.sh render && ./scripts/stack.sh up deye-bridge
```
