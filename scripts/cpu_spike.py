#!/usr/bin/env python3
"""Burn every CPU core on this server for a fixed time, then stop on its own.

Run on the servers through the Systems Manager Run Command document
onward-<env>-orders-cpu-spike (see scripts/demo/2-cpu-spike.sh in
AWS-onward-orders-infrastructure-Lab3-B). It is never
reachable from the website, so nobody on the internet can trigger it.
The time limit (max 15 minutes) caps the cost of a demo.
"""
import argparse
import multiprocessing
import os
import time


def burn(deadline: float) -> None:
    x = 0
    while time.time() < deadline:
        x = (x * 31 + 7) % 1_000_003


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=8)
    args = ap.parse_args()
    minutes = max(1.0, min(args.minutes, 15.0))
    deadline = time.time() + minutes * 60
    cores = os.cpu_count() or 1
    print(f"Burning {cores} core(s) for {minutes:g} minutes", flush=True)
    procs = [multiprocessing.Process(target=burn, args=(deadline,)) for _ in range(cores)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    print("CPU spike finished", flush=True)
