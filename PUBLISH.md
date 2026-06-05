# Publishing guide — what ships to end users

> **Maintainer doc** — not included in end-user release tarballs (see `.publishignore`).

This repo contains **development artifacts** alongside the user-facing app. When packaging for non-technical users, exclude flagged paths. Nothing listed here should be deleted from the dev repo.

## End-user release (ship)

Minimum files a homeowner needs to run `./setup.sh`:

| Path | Purpose |
|---|---|
| `README.md` | Setup instructions |
| `setup.sh` | One-command wizard |
| `stack.env.example` | Config template |
| `compose.yml` | Stack definition |
| `config/templates/` | Rendered service configs |
| `mosquitto/config/mosquitto.conf` | Broker config |
| `scripts/setup.sh`, `scripts/stack.sh` | Runtime tooling |
| `scripts/lib/` | Config loader / renderer |
| `scripts/healthcheck.sh` | Optional watchdog |
| `homeassistant/packages/.gitkeep` | Output dir for generated HA package |

**Optional but useful in releases:**

| Path | Purpose |
|---|---|
| `docs/INVERTER_NOTES.md` | Hardware-specific troubleshooting |
| `scripts/smoke_read.py` | Manual inverter test (needs `pysolarmanv5`) |

## Internal — do not ship

| Path | Why |
|---|---|
| `PLAN.md` | Implementation plan for coding agents / operators |
| `docs/MORNING_CHECKLIST.md` | Developer bring-up checklist |
| `PUBLISH.md` | This file |
| `.publishignore` | Packaging manifest |
| `scripts/setup_mqtt_password.sh` | Deprecated; superseded by `setup.sh` |
| `mosquitto/compose.yml` | Legacy stub → use root `compose.yml` |
| `deye-bridge/compose.yml` | Legacy stub → use root `compose.yml` |
| `docs/SCHEMA.md` | MQTT contract for integrators / future multi-vendor work |

## Never ship (generated or secret)

| Path | Why |
|---|---|
| `stack.env` | Local secrets |
| `mosquitto/config/passwd` | MQTT credentials |
| `mosquitto/data/` | Broker persistence |
| `deye-bridge/config.env` | Rendered secrets |
| `homeassistant/packages/solar.yaml` | Rendered per-site |
| `.git/`, `.gitmodules` | VCS metadata |

## Optional diagnostic bundle (exclude from minimal release)

| Path | Why |
|---|---|
| `pysolarmanv5/` | Git submodule for `stack.sh smoke` and network discovery; large. End users can use `./setup.sh --add-inverter` instead. Include only in **developer** or **full** distro. |

## Create a release tarball

```bash
tar -czvf bkw_tracker-release.tar.gz \
  --exclude-from=.publishignore \
  -C "$(dirname "$PWD")" "$(basename "$PWD")"
```

Or from repo root:

```bash
git archive --format=tar.gz --prefix=bkw_tracker/ HEAD \
  $(git ls-files | grep -v -F -f .publishignore)
```

(`git archive` only includes tracked files; prefer the `tar` command above for working-tree releases that respect `.publishignore`.)

## Flagging convention

Internal-only markdown files carry this banner at the top:

```markdown
> **Not shipped in end-user releases** — see [PUBLISH.md](…).
```

Search the repo: `Not shipped in end-user releases`
