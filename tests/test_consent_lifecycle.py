"""Documented three-path onboarding, native opt-in, removal safety tests."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import sys
from fastapi.testclient import TestClient
from polyc.api import create_app
from polyc.demo import constitution
from polyc.policy import policy_digest
from tests.conftest import ADMIN

ROOT = Path(__file__).resolve().parents[1]


def load_bootstrap():
    spec = importlib.util.spec_from_file_location('catbox_enrollment', ROOT / 'scripts/enroll-catbox.py')
    obj = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(obj)
    return obj


def test_consent_guide_routes_available_and_correct(tmp_path):
    app = create_app(str(tmp_path/'guide.sqlite'), ADMIN)
    with TestClient(app) as client:
        home = client.get('/').text
        guide = client.get('/web/participate.html')
        js = client.get('/web/guide.js')
        assert guide.status_code == 200 and 'text/html' in guide.headers['content-type']
        assert js.status_code == 200
        for section in ('id="browser"', 'id="catbox"', 'id="commons"', 'id="remove"'):
            assert section in guide.text
        assert 'this website cannot launch Docker' in guide.text
        assert 'runtime/admin-token.txt' in guide.text
        assert 'remote coordinator is unreachable' in guide.text or 'server is offline' in guide.text
        assert 'Read the source' in guide.text or 'review what you run' in guide.text
        assert 'href="/web/participate.html#catbox"' in home
        assert 'href="/web/participate.html#commons"' in home
        assert 'id="contribute"' in home
        assert client.get('/web/downloads/PoliCatHome-source.zip').status_code == 200
    app.state.store.db.close()


def test_native_catbox_enrollment_requires_disclosure_and_server_opt_in(tmp_path, monkeypatch):
    c = constitution('a'*64)
    c['spec']['nice_plus']['memory_mib_max'] = 512
    c['spec']['nice_plus']['cpu_percent_max'] = 25
    n = {'node_id': 'native-catbox-1', 'token': 'c'*32, 'constitution': c}
    monkeypatch.delenv('POLYC_SELF_ENROLL', raising=False)
    app = create_app(str(tmp_path/'off.sqlite'), ADMIN)
    with TestClient(app) as client:
        assert client.post('/api/catbox/enroll', json={'node': n,'accepted_resource_disclosure':True}).status_code == 403
    app.state.store.db.close()
    monkeypatch.setenv('POLYC_SELF_ENROLL', '1')
    app = create_app(str(tmp_path/'on.sqlite'), ADMIN)
    with TestClient(app) as client:
        assert client.post('/api/catbox/enroll', json={'node': n}).status_code == 422
        r = client.post('/api/catbox/enroll', json={'node': n,'accepted_resource_disclosure':True})
        assert r.status_code == 200, r.text
        assert not r.json()['compute_started']
        # An approved project still cannot be leased if no creator is authorized.
        reg = constitution('a'*64)
        reg['spec']['trust']['trusted_signers'] = []
        reg['spec']['nice_plus']['memory_mib_max'] = 512
        reg['spec']['nice_plus']['cpu_percent_max'] = 25
        assert client.post('/api/catbox/enroll', json={'node': {'node_id':'native-idle-1','token':'d'*32,
            'constitution':reg}, 'accepted_resource_disclosure': True}).status_code == 200
        lease = client.post('/api/lease',headers={'Authorization':'Bearer '+'d'*32},json={
            'node_id':'native-idle-1','constitution_digest':policy_digest(reg)})
        assert lease.status_code == 200 and lease.json()['assignment'] is None
        # Deny native configurations that pretend GPU/thermal controls are enforceable.
        hotter = constitution('a'*64)
        hotter['spec']['nice_plus']['memory_mib_max']=512
        hotter['spec']['thermal']['cpu_package_c_max']=65
        result = client.post('/api/catbox/enroll', json={'node': {'node_id':'native-hot-1','token':'h'*32,
            'constitution': hotter}, 'accepted_resource_disclosure':True})
        assert result.status_code == 422 and 'cannot enforce' in result.json()['detail']
    app.state.store.db.close()


def test_bootstrap_refuses_plaintext_remote_host_and_unconsented_creation(tmp_path, monkeypatch):
    mod = load_bootstrap()
    for url in ('http://example.com', 'http://192.168.1.2:8765','https://user:pass@example.com'):
        try:
            mod.safe_server(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f'dangerous URL accepted: {url}')
    assert mod.safe_server('https://polic.example.org') == 'https://polic.example.org'
    assert mod.safe_server('http://127.0.0.1:8765') == 'http://127.0.0.1:8765'
    cat = {'title': 'A Research Cat', 'creator_key': 'a'*64, 'category': 'open_science', 'commercial': False}
    from polyc.demo import constitution
    calls=[]
    def fake_request(base, path, obj=None, token=None):
        calls.append((path, obj))
        if path.endswith('enrollment-options'): return {'self_enroll': True}
        if path.endswith('catalog'): return {'cats': [cat]}
        if path.endswith('constitution-template'): return {'constitution':constitution('0'*64)}
        if path.endswith('enroll'): return {'enrolled': True}
        raise RuntimeError(path)
    monkeypatch.setattr(mod,'json_request',fake_request)
    response_iter=iter(['1','n','not consenting'])
    monkeypatch.setattr('builtins.input',lambda _:next(response_iter))
    out=tmp_path/'owner'/'owner.yaml'
    mod.enroll('http://127.0.0.1:8765',out)
    assert not out.exists()
    assert not any(path.endswith('/enroll') for path,obj in calls)
    response_iter=iter(['1','n','I CONSENT'])
    monkeypatch.setattr('builtins.input',lambda _:next(response_iter))
    mod.enroll('http://127.0.0.1:8765',out)
    assert out.exists()
    assert os.stat(out).st_mode & 0o777 == 0o600
    assert os.stat(out.parent).st_mode & 0o777 == 0o700
    cfg=__import__('json').loads(out.read_text())
    assert cfg['constitution']['spec']['trust']['trusted_signers'] == ['a'*64]
    assert any(path.endswith('/api/catbox/enroll') for path,obj in calls)
    assert cfg['token'] not in (ROOT/'polyc/web/participate.html').read_text()


def test_docker_compose_is_nonroot_and_bound_and_cleanup_requires_confirmation():
    import yaml
    service = yaml.safe_load((ROOT/'compose.catbox.yaml').read_text())['services']['catbox']
    assert service['read_only'] is True
    assert service['cap_drop'] == ['ALL']
    assert service['mem_limit'] == '768m'
    assert service['cpus'] == 0.5
    assert service['restart'] == 'no'
    assert service['pids_limit'] == 64
    assert not any('docker.sock' in volume for volume in service['volumes'])
    assert service['user'].startswith('${CATBOX_UID:')
    assert '127.0.0.1:8765:8765' in yaml.safe_load((ROOT/'compose.yaml').read_text())['services']['commons']['ports']
    purge=(ROOT/'scripts/remove-local.sh').read_text()
    assert 'DELETE MY COMMONS' in purge
    assert 'docker compose down --volumes' in purge
    assert '--purge-data' in purge
    assert 'rm -rf' not in purge
    catbox=(ROOT/'scripts/catbox-local.sh').read_text()
    assert 'python3 scripts/enroll-catbox.py revoke' in catbox
    assert 'rm -f "$owner_config"' in catbox
    assert 'Remote revoke could not be confirmed' in catbox


def test_native_catbox_commands_do_not_request_commons_admin_token(tmp_path):
    """Regression: `catbox-local.sh start` must not parse compose.yaml.

    Use a fake Docker executable so no Docker daemon is needed for the test.
    """
    import shutil
    import subprocess
    root = tmp_path / 'checkout'
    (root / 'scripts').mkdir(parents=True)
    shutil.copyfile(ROOT / 'scripts/catbox-local.sh', root / 'scripts/catbox-local.sh')
    shutil.copyfile(ROOT / 'compose.catbox.yaml', root / 'compose.catbox.yaml')
    (root / 'runtime/catbox-owner').mkdir(parents=True)
    (root / 'runtime/catbox-owner/owner.yaml').write_text('{}')
    bindir = tmp_path / 'mockbin'
    bindir.mkdir()
    fake = bindir / 'docker'
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DOCKER_CALLS_FILE"\n')
    fake.chmod(0o755)
    calls = tmp_path / 'calls.txt'
    env = dict(os.environ)
    env.pop('POLYC_ADMIN_TOKEN', None)
    env['PATH'] = str(bindir) + os.pathsep + env.get('PATH', '')
    env['DOCKER_CALLS_FILE'] = str(calls)
    for action in ('start', 'status', 'logs', 'pause'):
        p = subprocess.run(['bash', 'scripts/catbox-local.sh', action], cwd=root,
                           env=env, text=True, capture_output=True)
        assert p.returncode == 0, (action, p.stdout, p.stderr)
    trace = calls.read_text()
    assert 'compose -f compose.catbox.yaml up --build --no-deps -d catbox' in trace
    assert 'compose -f compose.catbox.yaml ps catbox' in trace
    assert 'compose -f compose.catbox.yaml logs --tail=80 -f catbox' in trace
    assert 'compose -f compose.catbox.yaml stop catbox' in trace
    assert 'compose.yaml' not in trace.replace('compose.catbox.yaml', '')
    assert (root / 'runtime/catbox-owner/paused').is_file()


def test_operator_inspection_wrapper_reads_existing_token_safely(tmp_path):
    """`status`/`logs` should work even when parent shell has no token."""
    import shutil
    import subprocess
    root = tmp_path / 'checkout'
    (root / 'scripts').mkdir(parents=True)
    shutil.copyfile(ROOT / 'scripts/commons-local.sh', root / 'scripts/commons-local.sh')
    (root / 'runtime').mkdir()
    (root / 'runtime/admin-token.txt').write_text('only-for-local-tests-operator-token\n')
    bindir = tmp_path / 'mockbin'
    bindir.mkdir()
    fake = bindir / 'docker'
    fake.write_text('#!/bin/sh\n[ "$POLYC_ADMIN_TOKEN" = "only-for-local-tests-operator-token" ] || exit 73\nprintf "%s\\n" "$*" >> "$DOCKER_CALLS_FILE"\n')
    fake.chmod(0o755)
    calls = tmp_path / 'calls.txt'
    env = dict(os.environ)
    env.pop('POLYC_ADMIN_TOKEN', None)
    env['PATH'] = str(bindir) + os.pathsep + env.get('PATH', '')
    env['DOCKER_CALLS_FILE'] = str(calls)
    for action in ('status', 'logs'):
        p = subprocess.run(['bash', 'scripts/commons-local.sh', action], cwd=root,
                           env=env, text=True, capture_output=True)
        assert p.returncode == 0, (action, p.stdout, p.stderr)
    assert 'compose ps commons' in calls.read_text()
    assert 'compose logs --tail=80 -f commons' in calls.read_text()
