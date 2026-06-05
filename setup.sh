#!/usr/bin/env bash
# One-command entry point for new users.
exec "$(cd "$(dirname "$0")" && pwd)/scripts/setup.sh" "$@"
