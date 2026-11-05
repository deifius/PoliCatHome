"""Independent node owner agent; locally revocable even if coordinator is offline."""
from __future__ import annotations
import json
import logging
import os
import signal
import time
from pathlib import Path
import httpx
import psutil
import yaml
from .crypto import verify_project
from .hird import start_builtin, stop_process
from .models import SignedProject
from .policy import compatible, policy_digest, validate_constitution

LOG = logging.getLogger(__name__)


class UnsafeToRun(Exception):
    pass


class Worker:
    def __init__(self, config_path: str, server: str, pause_file: str | None = None):
        cfg = yaml.safe_load(Path(config_path).read_text())
        self.node_id = cfg['node_id']
        self.token = cfg['token']
        self.constitution = cfg['constitution']
        validate_constitution(self.constitution)
        self.policy_hash = policy_digest(self.constitution)
        self.server = server.rstrip('/')
        self.pause_file = Path(pause_file or cfg.get('pause_file', f'runtime/{self.node_id}.pause'))
        self.client = httpx.Client(timeout=3, headers={'Authorization': f'Bearer {self.token}'})
        self.active_process = None
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True
        if self.active_process:
            stop_process(self.active_process)

    def local_ready(self) -> tuple[bool, str]:
        if self.stop_requested:
            return False, 'owner stopped the daemon'
        if self.pause_file.exists():
            return False, 'owner pause file is present'
        s = self.constitution['spec']
        max_cpu = s.get('local_activity', {}).get('max_host_cpu_percent')
        if max_cpu is not None and psutil.cpu_percent(interval=0.05) > max_cpu:
            return False, 'host CPU busy'
        limit = s.get('thermal', {}).get('cpu_package_c_max')
        if limit is not None:
            temperatures = psutil.sensors_temperatures(fahrenheit=False) or {}
            # No hard-coded fan sensors are accepted as CPU package telemetry.
            values = [e.current for group, sensors in temperatures.items()
                      if any(k in group.lower() for k in ('coretemp', 'k10temp', 'cpu_thermal'))
                      for e in sensors if 'package' in e.label.lower() or 'tctl' in e.label.lower()]
            if not values:
                return False, 'mandatory CPU package temperature sensor unavailable'
            if max(values) >= limit:
                return False, 'CPU thermal policy limit exceeded'
        return True, 'ready'

    def _get(self, path: str, **kw):
        r = self.client.get(f'{self.server}{path}', **kw)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict):
        r = self.client.post(f'{self.server}{path}', json=data)
        r.raise_for_status()
        return r.json()

    def validate_assignment(self, lease: dict) -> SignedProject:
        sp = SignedProject.model_validate(lease['signed_project'])
        trusted = self.constitution['spec']['trust']['trusted_signers']
        if not verify_project(sp, trusted):
            raise UnsafeToRun('project signature invalid or signer not trusted by owner')
        issues = compatible(self.constitution, sp.project, self.node_id)
        if issues:
            raise UnsafeToRun('; '.join(issues))
        if sp.project.work.kind != 'sha256_chain_v1':
            raise UnsafeToRun('task artifact not bundled with this worker')
        if not (0 <= lease['task_index'] < sp.project.work.tasks):
            raise UnsafeToRun('task index outside declared manifest')
        return sp

    def run_task(self, lease: dict) -> str:
        sp = self.validate_assignment(lease)
        ready, reason = self.local_ready()
        if not ready:
            raise UnsafeToRun(reason)
        work = sp.project.work
        nice = self.constitution['spec']['nice_plus']
        maximum = nice['task_runtime_seconds_max']
        start = time.monotonic()
        proc = start_builtin(work.seed, lease['task_index'], work.iterations, nice['memory_mib_max'], maximum)
        self.active_process = proc
        try:
            suspended = False
            while proc.poll() is None:
                # Nice Plus CPU duty-cycle cap (best effort, not a cgroup quota).
                permitted = ((time.monotonic()-start) % 1.0) < (nice['cpu_percent_max'] / 100)
                if not permitted and not suspended:
                    os.killpg(proc.pid, signal.SIGSTOP)
                    suspended = True
                elif permitted and suspended:
                    os.killpg(proc.pid, signal.SIGCONT)
                    suspended = False
                ready, reason = self.local_ready()
                if not ready:
                    raise UnsafeToRun(reason)
                if time.monotonic() - start > maximum:
                    raise UnsafeToRun('task runtime limit exceeded')
                # Host can revoke locally; project author can cancel centrally.
                try:
                    status = self._get(f'/api/tasks/{lease["task_id"]}/status', params={'node_id': self.node_id})
                except httpx.HTTPError:
                    raise UnsafeToRun('coordinator unreachable: fail closed')
                if not status['active'] or time.time() >= status['lease_until']:
                    raise UnsafeToRun('project consent revoked or task lease expired')
                time.sleep(.06)
            stdout, stderr = proc.communicate(timeout=1)
            if proc.returncode:
                raise UnsafeToRun(f'trusted built-in task failed (exit {proc.returncode}): {stderr[:100]}')
            value = stdout.strip()
            if len(value) != 64 or any(x not in '0123456789abcdef' for x in value):
                raise UnsafeToRun('invalid built-in task result')
            # Check local policy once more, even after result is computed.
            ready, reason = self.local_ready()
            if not ready:
                raise UnsafeToRun(reason)
            self._post(f'/api/tasks/{lease["task_id"]}/complete',
                       {'node_id': self.node_id, 'lease_id': lease['lease_id'], 'digest': value,
                        'duration_seconds': round(time.monotonic()-start, 4)})
            return value
        finally:
            stop_process(proc)
            self.active_process = None

    def tick(self) -> str:
        ready, reason = self.local_ready()
        if not ready:
            return f'local defer: {reason}'
        lease = self._post('/api/lease', {'node_id': self.node_id, 'constitution_digest': self.policy_hash})['assignment']
        if not lease:
            return 'no eligible task'
        try:
            self.run_task(lease)
            return f'completed {lease["task_id"]}'
        except (UnsafeToRun, httpx.HTTPError) as e:
            LOG.warning('%s: %s', self.node_id, e)
            # Best effort; local shutdown still succeeds if coordinator is down.
            try:
                self._post(f'/api/tasks/{lease["task_id"]}/fail',
                           {'node_id': self.node_id, 'lease_id': lease['lease_id'], 'reason': str(e)[:200]})
            except httpx.HTTPError:
                pass
            return f'deferred {lease["task_id"]}: {e}'

    def loop(self, interval: float = .5, max_seconds: float | None = None):
        start = time.monotonic()
        try:
            while not self.stop_requested and (max_seconds is None or time.monotonic()-start < max_seconds):
                try:
                    result = self.tick()
                except httpx.HTTPError as ex:
                    result = f'coordinator unavailable: {str(ex)[:120]}'
                LOG.info('%s: %s', self.node_id, result)
                time.sleep(interval)
        finally:
            self.request_stop()
            self.client.close()
