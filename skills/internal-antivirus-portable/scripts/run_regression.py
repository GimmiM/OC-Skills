#!/usr/bin/env python3
"""Run basic regression checks for internal-antivirus scan_skill."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run regression suite")
    parser.add_argument("--suite", default=str(Path(__file__).resolve().parents[1] / "tests" / "regression.json"))
    parser.add_argument("--policy", default=str(Path(__file__).resolve().parents[1] / "policy.yaml"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    suite_path = Path(args.suite).expanduser().resolve()
    policy = Path(args.policy).expanduser().resolve()

    if not suite_path.exists():
        print(f"suite not found: {suite_path} (portable mode: skipping)")
        return 0

    suite = json.loads(suite_path.read_text(encoding="utf-8"))

    failed = 0
    for case in suite:
        target = (root / case["target"]).resolve()
        cmd = [
            sys.executable,
            str((root / "scripts" / "scan_skill.py").resolve()),
            str(target),
            "--policy",
            str(policy),
            "--no-reputation",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            failed += 1
            print(f"[FAIL] {case['name']}: scan returned {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
            continue

        try:
            out = json.loads(proc.stdout)
        except Exception as e:
            failed += 1
            print(f"[FAIL] {case['name']}: invalid json output ({e})")
            continue

        decision = out.get("decision")
        expected = set(case.get("expected_decisions", []))
        if decision not in expected:
            failed += 1
            print(f"[FAIL] {case['name']}: decision={decision}, expected one of {sorted(expected)}")
        else:
            print(f"[OK] {case['name']}: decision={decision}")

    print(f"suite={suite_path} total={len(suite)} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
