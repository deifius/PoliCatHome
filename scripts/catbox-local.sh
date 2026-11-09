#!/usr/bin/env bash
# One-owner, local Commons Docker Catbox lifecycle. Never mounts docker.sock.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command_name="${1:-help}"
owner_dir=runtime/catbox-owner
owner_config="$owner_dir/owner.yaml"
server_file="$owner_dir/server.url"
server_base="http://127.0.0.1:8765"
if [[ -s "$server_file" ]]; then server_base="$(cat "$server_file")"; fi
if [[ "$server_base" == http://127.0.0.1:8765 || "$server_base" == http://localhost:8765 ]]; then
  export CATBOX_SERVER=http://commons:8765
else
  export CATBOX_SERVER="$server_base"
fi
# Catbox is a separate opt-in service. Loading compose.yaml here incorrectly
# required the Commons administrator token for every contributor command.
# Standalone Compose in the same checkout still joins the existing project
# default network (and reaches local Commons as http://commons:8765).
compose=(docker compose -f compose.catbox.yaml)
check_docker() {
  docker compose version >/dev/null 2>&1 || { echo 'Docker Compose v2 is required.' >&2; exit 1; }
  export CATBOX_UID="$(id -u)" CATBOX_GID="$(id -g)"
}
case "$command_name" in
  enroll)
    case "$(pwd -P)" in
      /mnt/[a-z]/*|/mnt/[A-Z]/*)
        echo 'Refusing native credential enrollment on a Windows-mounted WSL path.' >&2
        echo 'Move this source to ~/projects/PoliCatHome-local-test on the Linux filesystem first.' >&2
        echo 'Windows-mounted DrvFs may not protect 0600 owner tokens as expected.' >&2
        exit 1;;
    esac
    if [[ -e "$owner_config" ]]; then
      echo "Existing Catbox policy found at $owner_config. Remove/revoke before re-enrolling." >&2; exit 1
    fi
    target_server="${2:-http://127.0.0.1:8765}"
    python3 scripts/enroll-catbox.py enroll --server "$target_server" --config "$owner_config"
    if [[ -s "$owner_config" ]]; then
      ( umask 077; printf "%s\n" "$target_server" > "$server_file" )
    fi
    ;;
  start|resume)
    [[ -s "$owner_config" ]] || { echo 'No private Catbox policy: run bash scripts/catbox-local.sh enroll first.' >&2; exit 1; }
    check_docker
    rm -f "$owner_dir/paused"
    "${compose[@]}" up --build --no-deps -d catbox
    echo 'Catbox container started: bundled SHA-256 jobs only.'
    echo 'If you trusted zero Cat creators, work stays idle until you revoke/remove and re-enroll.'
    echo 'Monitor: bash scripts/catbox-local.sh logs'
    ;;
  status)
    check_docker
    "${compose[@]}" ps catbox
    ;;
  logs)
    check_docker
    "${compose[@]}" logs --tail=80 -f catbox
    ;;
  pause|stop)
    # The flag prevents future leases even if the Docker service is restarted manually.
    if [[ -d "$owner_dir" ]]; then touch "$owner_dir/paused"; fi
    check_docker
    "${compose[@]}" stop catbox
    echo 'Catbox stopped locally; no new work can execute. Coordinator consent remains registered.'
    ;;
  revoke)
    check_docker
    if [[ -d "$owner_dir" ]]; then touch "$owner_dir/paused"; fi
    "${compose[@]}" stop catbox
    [[ -s "$owner_config" ]] || { echo 'No local policy to revoke.' >&2; exit 1; }
    python3 scripts/enroll-catbox.py revoke --server "$server_base" --config "$owner_config"
    echo 'Remote revocation confirmed; local credentials remain until remove is run.'
    ;;
  remove)
    check_docker
    if [[ -d "$owner_dir" ]]; then touch "$owner_dir/paused"; fi
    "${compose[@]}" stop catbox
    if [[ -s "$owner_config" ]]; then
      # Fail safely: do not erase the token if the remote coordinator cannot confirm revocation.
      python3 scripts/enroll-catbox.py revoke --server "$server_base" --config "$owner_config" || {
        echo 'Remote revoke could not be confirmed. Catbox is stopped; local token kept for retry.' >&2
        echo 'Run: bash scripts/catbox-local.sh revoke' >&2
        exit 1
      }
    fi
    "${compose[@]}" rm --force --stop catbox
    rm -f "$owner_config" "$owner_dir/paused" "$server_file"
    rmdir "$owner_dir" 2>/dev/null || true
    echo 'Catbox container and owner token removed. Commons DB/receipts are NOT erased.'
    ;;
  help|-h|--help)
    cat <<'EOF'
Local Catbox — approved built-in tasks only, NEVER arbitrary OCI/GPU workloads.
  bash scripts/catbox-local.sh enroll [https://your-commons.example] # choose Cats and consent
  bash scripts/catbox-local.sh start    # start own resource-capped Docker Catbox
  bash scripts/catbox-local.sh status   # inspect own Catbox
  bash scripts/catbox-local.sh logs     # follow own Catbox logs
  bash scripts/catbox-local.sh pause    # immediate local stop, keeps credentials
  bash scripts/catbox-local.sh resume   # re-enable work after pause
  bash scripts/catbox-local.sh revoke   # stop + server-side consent revocation
  bash scripts/catbox-local.sh remove   # revoke + remove only Catbox and its local token
Default Commons is localhost:8765. Remote HTTPS Commons URL may be supplied to enroll.
Remote Commons must enable self-enrollment and may require account-specific policies.
No administrator token, Docker socket, arbitrary images or payments are involved.
EOF
    ;;
  *) echo "Unknown action: $command_name; use help" >&2; exit 2;;
esac
