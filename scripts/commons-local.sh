#!/usr/bin/env bash
# Inspect LOCAL Commons without asking the operator to export a secret manually.
# This script is for the Commons operator, not for Catnap contributors.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -s runtime/admin-token.txt ]]; then
  echo 'Local Commons operator credential not found. Run bash scripts/start-local.sh first.' >&2
  exit 1
fi
export POLYC_ADMIN_TOKEN="$(tr -d '\r\n' < runtime/admin-token.txt)"
case "${1:-status}" in
  status) docker compose ps commons ;;
  logs) docker compose logs --tail=80 -f commons ;;
  *) echo 'Usage: bash scripts/commons-local.sh [status|logs]' >&2; exit 2 ;;
esac
