"""HIRD/process: a *trusted built-in task* subprocess; NOT a VM/security sandbox."""
from __future__ import annotations
import os
import resource
import signal
import subprocess
import sys
import time


def _limits(memory_mib: int, cpu_seconds: int):
    def apply():
        # Linux POSIX process guardrails; child can only run our bundled task.
        os.nice(19)
        resource.setrlimit(resource.RLIMIT_AS, (memory_mib * 1024 * 1024, memory_mib * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    return apply


def start_builtin(seed: str, index: int, iterations: int, memory_mib: int, max_runtime: int):
    # No shell or network supplied to child. Not a general arbitrary-code executor.
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'PYTHONPATH': os.environ.get('PYTHONPATH', '')}
    return subprocess.Popen(
        [sys.executable, '-m', 'polyc.task_child', seed, str(index), str(iterations)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True, preexec_fn=_limits(memory_mib, max(2, max_runtime)), env=env)


def stop_process(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
