"""Real child-process smoke tests: do not confuse this with VM isolation tests."""
import time
from polyc.hird import start_builtin, stop_process
from polyc.compute import compute_chain
from polyc.chronicle import describe


def test_bundled_process_completes_under_resource_bounds():
    proc = start_builtin('test', 1, 25, 768, 10)
    try:
        out, err = proc.communicate(timeout=10)
        assert proc.returncode == 0, err
        assert out.strip() == compute_chain('test',1,25)
    finally:
        stop_process(proc)


def test_local_owner_can_kill_subprocess():
    proc = start_builtin('long-job', 1, 400000, 768, 20)
    try:
        stop_process(proc)
        assert proc.poll() is not None
    finally:
        stop_process(proc)


def test_chronicle_does_not_invent_work():
    text=describe({'node_id':'cat-1','projects':[]})
    assert 'no completed tasks' in text
    assert 'No GPU use' in text
