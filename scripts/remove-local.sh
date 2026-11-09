#!/usr/bin/env bash
# Deliberate local Commons teardown. Refuses to destroy registered owner credentials.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ${1:-} != '--purge-data' ]]; then
  cat <<'EOF'
Usage: bash scripts/remove-local.sh --purge-data

This is intentionally different from scripts/stop-local.sh.
STOP:              bash scripts/stop-local.sh   (retains Docker database and token)
REMOVE:            bash scripts/remove-local.sh --purge-data

REMOVE irreversibly deletes this Compose project's coordinator container,
its Docker DB volume, and runtime/admin-token.txt. Task receipts and history
in the local database will be lost. Source files and unrelated Docker data are
NOT deleted. Make a backup first if you need historical evidence.

If an owner's Catbox exists, revoke/remove it FIRST:
  bash scripts/catbox-local.sh remove
EOF
  exit 0
fi
if [[ -s runtime/catbox-owner/owner.yaml ]]; then
  echo 'A native Catbox is still registered. First: bash scripts/catbox-local.sh remove' >&2
  echo 'Do not erase the Commons before revoking its contributor token.' >&2
  exit 1
fi
docker compose version >/dev/null 2>&1 || { echo 'Docker Compose is required.' >&2; exit 1; }
[[ -s runtime/admin-token.txt ]] || { echo 'Local administrator token missing; cannot identify this Commons.' >&2; exit 1; }
cat <<'EOF'
DANGER: PERMANENTLY DELETE LOCAL COMMONS DATA.
This removes the coordinator container, its database volume, and admin token.
It does not delete your source checkout, or unrelated containers/volumes.
Type exactly: DELETE MY COMMONS
EOF
read -r -p '> ' response
if [[ "$response" != 'DELETE MY COMMONS' ]]; then
  echo 'Cancelled. Commons data retained.'; exit 0
fi
export POLYC_ADMIN_TOKEN="$(tr -d '\r\n' < runtime/admin-token.txt)"
docker compose down --volumes
a="runtime/admin-token.txt"
rm -f -- "$a"
echo 'Commons container, its Docker database volume and this local token removed.'
echo 'Source files remain. To restart with a fresh identity: bash scripts/start-local.sh'
