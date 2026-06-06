# Publishing guide

> **Maintainer doc** — excluded from end-user tarballs (`.publishignore`).

## Recommended: GitHub repo + release tarball

**Use a public GitHub repository as the primary publication** (`henba1/bkw_tracker`), not a standalone tarball.

| Approach | Role |
|---|---|
| **GitHub repo** | Source of truth, issues, `git pull` updates, discoverability |
| **GitHub Release + `.tar.gz`** | Optional download for users who do not use git |
| **Tarball only** | Not recommended — no version history, no issues, no easy updates |

Workflow:

1. Tag a release: `git tag v1.0.0 && git push origin v1.0.0`
2. Build artifact: `./scripts/release.sh v1.0.0`
3. Attach `dist/bkw_tracker-v1.0.0.tar.gz` to the GitHub Release
4. Point users to the README quick start

## GitHub Pages

README is published at **https://henba1.github.io/bkw_tracker/** via `.github/workflows/pages.yml` (builds from `README.md` + `assets/` on each push to `main`).

One-time repo setting: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## End-user release contents

Everything needed for `./setup.sh`, excluding paths in `.publishignore`:

- `README.md`, `assets/`, `setup.sh`, `compose.yml`, `stack.env.example`
- `config/templates/`, `mosquitto/config/`, `scripts/`
- `homeassistant/lovelace/`, `homeassistant/packages/.gitkeep`

Key scripts not obvious from layout: `install_ha_package.sh`, `configure_ha_mqtt.py`, `install_healthcheck_cron.sh`.

## Internal — do not ship

`PLAN.md`, `PUBLISH.md`, `.publishignore`, `docs/*` (all dev/operator notes), legacy per-service `compose.yml` stubs, `pysolarmanv5/` submodule.

## Never ship

`stack.env`, `mosquitto/config/passwd`, `mosquitto/data/`, `deye-bridge/config.env`, rendered `homeassistant/packages/solar.yaml`, `.git/`.

## Build tarball

```bash
./scripts/release.sh          # → dist/bkw_tracker-<git-describe>.tar.gz
./scripts/release.sh v1.0.0   # → dist/bkw_tracker-v1.0.0.tar.gz
```
