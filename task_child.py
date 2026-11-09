"""Trusted, finite pilot task; never deserialize or execute project code."""
import sys
from .compute import compute_chain


def main():
    if len(sys.argv) != 4:
        raise SystemExit(2)
    seed, index, iterations = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    if not 0 <= index <= 99 or not 1 <= iterations <= 400000 or len(seed) > 128:
        raise SystemExit(2)
    print(compute_chain(seed, index, iterations), flush=True)

if __name__ == '__main__':
    main()
