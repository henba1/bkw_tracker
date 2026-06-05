# Morning checklist — hardware gate

Run in order. Do not start `deye-bridge` until step 4 passes.

## 1. Confirm logger is on the LAN

- [ ] Sun is up; panel is producing (WiFi module needs PV power).
- [ ] Router DHCP/connected-devices shows the Deye logger.
- [ ] Note the **actual IP** (expect `192.168.178.100` if static config took).
- [ ] Update `deye-bridge/config.env` → `DEYE_LOGGER_IP_ADDRESS` if different.

## 2. Layer-3 reachability (from Pi)

```bash
ping -c 2 <LOGGER_IP>
nc -zv <LOGGER_IP> 8899
```

- [ ] Ping succeeds (or HTTP `curl -m 3 http://<LOGGER_IP>/` returns 200).
- [ ] Port 8899 is open.

## 3. Discovery (optional — serial confirmation)

```bash
cd pysolarmanv5
python utils/solarman_uni_scan.py eth0
# or direct probe:
python - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2); s.connect(("<LOGGER_IP>", 48899))
s.sendall(b"WIFIKIT-214028-READ")
print(s.recv(1024))
PY
```

- [ ] Serial printed matches sticker (`4145330384`) or note the actual value.
- [ ] If no UDP response but 8899 is open → proceed anyway with sticker serial.

## 4. Smoke test (blocking gate)

```bash
pip install ./pysolarmanv5
python scripts/smoke_read.py --ip <LOGGER_IP> --serial 4145330384
```

If auth fails:

```bash
python scripts/smoke_read.py --ip <LOGGER_IP> --serial 2208093531
```

- [ ] Prints `OK: [...]` with a non-empty register value.

## 5. Start the stack

```bash
./scripts/setup_mqtt_password.sh          # if not done yet
cd mosquitto && docker compose up -d
cd ../deye-bridge && docker compose up -d
```

## 6. Verify MQTT flow

```bash
mosquitto_sub -h 192.168.178.52 -u solar -P '<pw>' -t 'solar/#' -v
```

- [ ] `ac/active_power`, `day_energy`, `total_energy` update every ~30 s.
- [ ] Daylight values ≤ ~300 W; plausible voltage ~230 V.

## 7. Protocol fallback (only if bridge logs show read timeouts)

Edit `deye-bridge/config.env`:

| Attempt | `DEYE_LOGGER_PROTOCOL` | `DEYE_LOGGER_PORT` |
|---|---|---|
| 1 (default) | `solarman_v5` | `8899` |
| 2 | `tcp` | `8899` |
| 3 | `at` | `48899` (+ `DEYE_LOGGER_MAX_REG_RANGE_LENGTH=16`) |

Restart: `cd deye-bridge && docker compose restart`
