#!/usr/bin/env python3
"""Install wrapper with mandatory pre-install gate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    base = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Install skill through internal AV gate")
    parser.add_argument("target", help="Path to skill folder/.zip/.skill")
    parser.add_argument("--owner-approve-risk", action="store_true")
    parser.add_argument("--approval-reason", default="")
    parser.add_argument("install_cmd", nargs=argparse.REMAINDER, help="Install command after --")
    args = parser.parse_args()

    if not args.install_cmd:
        print("Usage: install_skill.py <target> -- <install command>")
        return 2

    gate_cmd = [
        sys.executable,
        str(base / "scripts" / "preinstall_gate.py"),
        str(Path(args.target).expanduser().resolve()),
        "--pretty",
    ]

    if args.owner_approve_risk:
        gate_cmd.extend(["--owner-approve-risk", "--approval-reason", args.approval_reason])

    gate = subprocess.run(gate_cmd)
    if gate.returncode != 0:
        print("[BLOCKED] Pre-install gate did not approve this artifact.")
        return gate.returncode

    cmd = args.install_cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    if not cmd:
        print("Usage: install_skill.py <target> -- <install command>")
        return 2

    print(f"[APPROVED] Running install command: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
