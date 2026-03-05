#!/usr/bin/env python3
"""Mandatory pre-install gate for external skills."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_scan(scan_script: Path, target: Path, policy: Path, rules_file: Path) -> dict:
    cmd = [
        sys.executable,
        str(scan_script),
        str(target),
        "--policy",
        str(policy),
        "--rules-file",
        str(rules_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"scan failed rc={proc.returncode}: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def write_gate_receipt(base: Path, report: dict, approved: bool, reason: str) -> Path:
    out_dir = base / "gate" / "receipts"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = report.get("target_sha256", "unknown")[:16]
    p = out_dir / f"{ts}-{sha}.json"

    receipt = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target": report.get("target"),
        "target_sha256": report.get("target_sha256"),
        "risk_level": report.get("risk_level"),
        "decision": report.get("decision"),
        "approved_for_install": approved,
        "approval_reason": reason,
    }
    p.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def main() -> int:
    base = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Internal AV pre-install gate")
    parser.add_argument("target", help="Path to skill folder/.zip/.skill")
    parser.add_argument("--policy", default=str(base / "policy.yaml"))
    parser.add_argument("--rules-file", default=str(base / "rules" / "curated_v2.yaml"))
    parser.add_argument("--owner-approve-risk", action="store_true", help="Allow review_and_confirm decisions")
    parser.add_argument("--approval-reason", default="", help="Required with --owner-approve-risk")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    policy = Path(args.policy).expanduser().resolve()
    rules_file = Path(args.rules_file).expanduser().resolve()

    scan_script = base / "scripts" / "scan_skill.py"
    report = run_scan(scan_script, target, policy, rules_file)

    decision = str(report.get("decision", "review_and_confirm"))
    allowed = decision in {"allow", "allow_with_caution"}

    if decision == "review_and_confirm":
        if args.owner_approve_risk:
            if not args.approval_reason.strip():
                print(json.dumps({"ok": False, "error": "--approval-reason required with --owner-approve-risk"}, ensure_ascii=False))
                return 2
            allowed = True

    if decision == "block":
        allowed = False

    receipt = write_gate_receipt(base, report, approved=allowed, reason=args.approval_reason.strip())

    out = {
        "ok": allowed,
        "gate_receipt": str(receipt),
        "scan": report,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if allowed else 3


if __name__ == "__main__":
    raise SystemExit(main())
