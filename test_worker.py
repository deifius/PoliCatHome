from pathlib import Path
import yaml
import pytest
from polyc.crypto import sign_project
from polyc.worker import Worker, UnsafeToRun
from polyc.policy import policy_digest
from tests.conftest import ADMIN


def make_worker(setup, tmp_path):
    client, app, c, sign, pub=setup
    config = tmp_path/'cat.yaml'
    pause = tmp_path/'cat.pause'
    config.write_text(yaml.safe_dump({'node_id':'cat-one','token':'n'*32,'constitution':c,'pause_file':str(pause)}))
    w=Worker(str(config),'http://127.0.0.1:8765')
    return w,pause


def test_local_pause_bypasses_coordinator(setup,tmp_path):
    w,pause=make_worker(setup,tmp_path)
    pause.touch()
    assert w.local_ready() == (False,'owner pause file is present')
    assert w.tick().startswith('local defer')
    pause.unlink()
    assert w.local_ready()[0]
    w.request_stop()
    assert w.local_ready()[0] is False


def test_worker_denies_tampered_project_even_after_lease(setup,tmp_path):
    client, app, c, sign, pub=setup
    w,_=make_worker(setup,tmp_path)
    original=sign().model_dump(mode='json')
    lease={'signed_project':original,'task_index':0}
    assert w.validate_assignment(lease)
    lease['signed_project']['project']['title']='Marauding cats'
    with pytest.raises(UnsafeToRun):
        w.validate_assignment(lease)
