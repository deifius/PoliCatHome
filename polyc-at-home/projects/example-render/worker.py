"""Illustrative task-JSON adapter. Does not render images or support GPU work."""
import hashlib
import json
from pathlib import Path


def main():
    request = json.loads(Path('/polyc/input/task.json').read_text())
    data = json.dumps({'task_id': request['task_id'], 'shard': request['shard']}, sort_keys=True).encode()
    result = {'task_id': request['task_id'], 'output_sha256': hashlib.sha256(data).hexdigest(),
              'note': 'Example adapter, not a real rendering workload'}
    Path('/polyc/output/result.json').write_text(json.dumps(result, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
