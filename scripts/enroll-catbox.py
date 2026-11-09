#!/usr/bin/env python3
"""Consent-led, local native Catbox enrollment. Standard library only.

Not a remote Docker launcher. Produces a private config for the fixed built-in
SHA-256 worker, which scripts/catbox-local.sh starts separately.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request


def safe_server(url: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.path not in ('', '/') or p.query or p.fragment:
        raise ValueError('server must be a bare http://localhost:PORT or HTTPS base URL')
    if p.scheme == 'http' and p.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('remote coordinators require HTTPS; refuse to send owner credentials over HTTP')
    return url.rstrip('/')


def json_request(base: str, path: str, obj: dict | None = None, token: str | None = None) -> dict:
    headers = {'Accept': 'application/json'}
    if obj is not None:
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(base + path, headers=headers,
                                 data=json.dumps(obj).encode() if obj is not None else None,
                                 method='POST' if obj is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        try:
            detail = json.load(err).get('detail', err.reason)
        except (ValueError, OSError):
            detail = err.reason
        raise RuntimeError(f'Commons returned HTTP {err.code}: {detail}') from err
    except urllib.error.URLError as err:
        raise RuntimeError(f'Commons unreachable: {err.reason}') from err


def choose_cats(catalog: list[dict]) -> tuple[list[str], list[str]]:
    print('\nAPPROVED CATS (operator reviewed; not an independent source-code audit)')
    if not catalog:
        print('No approved Cats yet. You may enroll IDLE, trusting nobody until you re-enroll.')
        return [], ['open_science']
    for n, cat in enumerate(catalog, 1):
        print(f'  {n}. {cat.get("title", cat.get("project_id", "Cat"))} [{cat.get("category", "unknown")}]')
        print(f'     creator: {cat.get("creator_key", "unknown")}')
        print(f'     commercial: {cat.get("commercial", "unknown")}')
    raw = input('Select Cat numbers (e.g. 1,2); Enter trusts nobody: ').strip()
    if not raw:
        return [], ['open_science']
    indexes = []
    for part in raw.split(','):
        if not re.fullmatch(r'[1-9][0-9]*', part.strip()):
            raise ValueError('enter Cat numbers separated by commas, or leave blank')
        idx = int(part.strip())-1
        if not 0 <= idx < len(catalog):
            raise ValueError('Cat number is outside the displayed catalog')
        indexes.append(idx)
    selected = [catalog[i] for i in sorted(set(indexes))]
    # Trust attaches to creators rather than individual Cats; tell people explicitly.
    return sorted(set(x['creator_key'] for x in selected)), sorted(set(x['category'] for x in selected))


def prepare_config(template: dict, keys: list[str], categories: list[str], *, allow_commercial: bool) -> dict:
    c = template
    spec = c['spec']
    spec['trust']['trusted_signers'] = keys
    spec['content']['allow_categories'] = categories
    spec['ethos']['allow_commercial_projects'] = allow_commercial
    spec['nice_plus']['cpu_percent_max'] = 25  # best effort inside a hard 0.5 CPU Docker quota
    spec['nice_plus']['memory_mib_max'] = 512
    spec['nice_plus']['task_runtime_seconds_max'] = 15
    spec['nice_plus']['gpu_utilization_percent_max'] = 0
    spec['thermal']['cpu_package_c_max'] = None
    spec['energy']['require_meter'] = False
    spec.pop('financial', None)
    spec['reporting']['catnap_enabled'] = True
    node_id = 'catbox-' + secrets.token_hex(5)
    c['metadata']['name'] = node_id
    return {'node_id': node_id, 'token': secrets.token_urlsafe(36), 'constitution': c}


def enroll(base: str, output: Path) -> None:
    if output.exists():
        raise RuntimeError(f'{output} already exists. Revoke/remove your existing Catbox before re-enrolling.')
    opts = json_request(base, '/api/catnap/enrollment-options')
    if not opts.get('self_enroll'):
        raise RuntimeError('This Commons has self-enrollment disabled; no administrator workaround is attempted.')
    catalog = json_request(base, '/api/catnap/catalog')['cats']
    keys, categories = choose_cats(catalog)
    commercial = input('Allow commercial Cats compatible with your categories? [y/N]: ').strip().lower() == 'y'
    template = json_request(base, '/api/catnap/constitution-template')['constitution']
    config = prepare_config(template, keys, categories, allow_commercial=commercial)
    print('\nYOUR NATIVE CATBOX POLIC / INFORMED CONSENT')
    print(f'  Coordinator: {base}')
    print(f'  Trust: {len(keys)} creator key(s), including their FUTURE operator-approved Cats')
    print(f'  Allowed categories: {", ".join(categories)}; commercial: {commercial}')
    print('  Work: ONLY bundled SHA-256 tasks. No arbitrary Docker images, GPU jobs, payments or rewards.')
    print('  Container: 0.5 CPU hard cgroup quota; 768 MiB total RAM; 64 PIDs; non-root; read-only rootfs.')
    print('  Process: best-effort 25% CPU pacing + 15s task timeouts; Docker controls do NOT limit heat.')
    print('  Network: Catbox can connect to Commons; its network is NOT isolated from the internet.')
    print('  Files: mounts only local owner config read-only; no Docker socket and no personal files.')
    print('  Background: once you run START it continues until PAUSED/REVOKED or Docker stops it.')
    print('  CPU quota is HALF OF ONE logical CPU, NOT half the entire computer.')
    print('  Admin account: not required. Creating this identity does NOT start any CPU work.')
    print('  Stop anytime: bash scripts/catbox-local.sh pause')
    print('  Revoke + remove: bash scripts/catbox-local.sh remove')
    print('  Server-stored node consent/revocation and provisional task receipts may remain in Commons history.')
    phrase = input('\nTo register this node, type I CONSENT (anything else cancels): ').strip()
    if phrase != 'I CONSENT':
        print('Cancelled. No identity was registered or files created.')
        return
    json_request(base, '/api/catbox/enroll', {'node': config, 'accepted_resource_disclosure': True})
    # Write after server accepted. Never make the owner token world-readable.
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output.parent, 0o700)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('\nEnrolled (CPU still idle). Start separately: bash scripts/catbox-local.sh start')
    if not keys:
        print('No Cat creators trusted: this Catbox will remain idle. Revoke + re-enroll to change your PoliC.')


def revoke(base: str, path: Path) -> None:
    config = json.loads(path.read_text())
    node_id = config['node_id']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,63}', node_id):
        raise ValueError('invalid node identifier in local configuration')
    json_request(base, f'/api/nodes/{node_id}/revoke', {}, config['token'])
    print(f'Commons confirmed consent revoked for {node_id}.')


def main() -> None:
    p = argparse.ArgumentParser(description='Manage opt-in native Catbox enrollment. Does not launch Docker.')
    p.add_argument('action', choices=['enroll', 'revoke'])
    p.add_argument('--server', default='http://127.0.0.1:8765')
    p.add_argument('--config', default='runtime/catbox-owner/owner.yaml')
    a = p.parse_args()
    try:
        base = safe_server(a.server)
        if a.action == 'enroll':
            enroll(base, Path(a.config))
        else:
            revoke(base, Path(a.config))
    except (ValueError, RuntimeError, KeyError, OSError, json.JSONDecodeError) as err:
        print(f'Catbox setup: {err}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
