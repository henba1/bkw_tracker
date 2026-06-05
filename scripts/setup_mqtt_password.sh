#!/usr/bin/env bash
# publish:exclude — deprecated; use ./setup.sh instead. See PUBLISH.md.
# Deprecated wrapper — use ./scripts/stack.sh init or ./scripts/stack.sh render instead.
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/stack.sh" render
