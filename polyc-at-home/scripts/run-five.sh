#!/usr/bin/env bash
set -euo pipefail
python -m polyc.demo --workdir "${1:-runtime/five-cats}"
