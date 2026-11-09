#!/usr/bin/env bash
# Start a LOCALHOST-ONLY coordinator in Docker for browser acceptance testing.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker unavailable. Start your Docker daemon or enable Docker Desktop's WSL integration." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is unavailable. Install or enable the Compose plugin." >&2
  exit 1
fi
mkdir -p runtime
chmod 700 runtime
if [[ ! -s runtime/admin-token.txt ]]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(36))' > runtime/admin-token.txt
fi
export POLYC_ADMIN_TOKEN="$(tr -d '\r\n' < runtime/admin-token.txt)"
if [[ ${#POLYC_ADMIN_TOKEN} -lt 24 ]]; then
  echo "Invalid runtime/admin-token.txt: operator token must contain 24+ characters." >&2
  exit 1
fi
docker compose up --build -d
cat <<'EOF'

PoliC@home should be at http://localhost:8765/
Your operator token is in runtime/admin-token.txt (keep it private).
In WSL: cat runtime/admin-token.txt
In the browser: Commons -> paste token -> CONNECT OVERVIEW.
For status: bash scripts/commons-local.sh status
For logs: bash scripts/commons-local.sh logs
To stop: bash scripts/stop-local.sh

Note: This starts the Commons coordinator only. No visitor contributes
CPU until they enroll and click Start Catnap in their own browser.
You can also enroll and start a separate native Docker Catbox:
  bash scripts/catbox-local.sh enroll
  bash scripts/catbox-local.sh start
Review every option and full removal instructions at:
  http://localhost:8765/web/participate.html
To stop and retain the Commons database: bash scripts/stop-local.sh
To permanently remove the local Commons database: bash scripts/remove-local.sh --purge-data
EOF
