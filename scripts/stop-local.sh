#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -s runtime/admin-token.txt ]]; then
  echo 'Local administrator credential not found; refusing to infer deployment state.' >&2
  exit 1
fi
export POLYC_ADMIN_TOKEN="$(tr -d '\r\n' < runtime/admin-token.txt)"
docker compose down
printf '%s\n' 'PoliC@home stopped. Its Docker database volume and private runtime/admin-token.txt are retained.'
