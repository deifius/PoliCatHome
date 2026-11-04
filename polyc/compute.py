"""The ONLY pilot workload. No uploaded code, shell, Python expressions or model weights."""
import hashlib


def compute_chain(seed: str, task_index: int, iterations: int) -> str:
    state = f'{seed}:{task_index}'.encode('utf-8')
    for _ in range(iterations):
        state = hashlib.sha256(state).digest()
    return state.hex()
