"""Simple CLI utility to dump in-memory metrics as JSON.

Usage:
  python -m Main.metrics_cli            # pretty JSON
  python Main/metrics_cli.py --raw      # compact
"""
from __future__ import annotations

import argparse, json
from Main.core.metrics import METRICS  # type: ignore

def main():
    p = argparse.ArgumentParser(description='Dump in-memory metrics snapshot')
    p.add_argument('--raw', action='store_true', help='Compact JSON output')
    args = p.parse_args()
    snap = METRICS.snapshot()
    if args.raw:
        print(json.dumps(snap, separators=(',',':')))
    else:
        print(json.dumps(snap, indent=2))

if __name__ == '__main__':
    main()
