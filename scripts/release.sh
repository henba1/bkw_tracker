#!/usr/bin/env bash
# Build an end-user release tarball (respects .publishignore).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NAME="$(basename "$ROOT")"
VERSION="${1:-$(git -C "$ROOT" describe --tags --always --dirty 2>/dev/null || echo "snapshot")}"
VERSION="${VERSION#v}"
OUT_DIR="${ROOT}/dist"
ARCHIVE="${OUT_DIR}/${NAME}-v${VERSION}.tar.gz"

mkdir -p "$OUT_DIR"
tar -czvf "$ARCHIVE" --exclude-from="${ROOT}/.publishignore" -C "$(dirname "$ROOT")" "$NAME"
echo "Created ${ARCHIVE}"
