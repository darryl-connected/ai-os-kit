#!/bin/bash
set -eu
KIT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "${PYTHON:-python3}" "$KIT_ROOT/scripts/install-kit.py" "$@"
