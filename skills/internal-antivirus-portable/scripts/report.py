#!/usr/bin/env python3
"""Generate Internal Antivirus summary report from audit + reputation logs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def parse_ts(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def keep_recent(rows: List[Dict[str, Any]], since: datetime) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        ts = parse_ts(str(r.get("ts") or r.get("generated_at") or ""))
        if ts and ts >= since:
            out.append(r)
    return out


def latest_audit_file(reports_dir: Path) -> Path | None:
    files = sorted(reports_dir.glob("audit-*.jsonl"))
    return files[-1] if files else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal Antivirus report")
    base = Path(__file__).resolve().parents[1]
    parser.add_argument("--reports-dir", default=str(base / "reports"))
    parser.add_argument("--reputation-db", default=str(base / "data" / "reputation.jsonl"))
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--last", type=int, default=10, help="Include last N events")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=max(args.hours, 1))

    reports_dir = Path(args.reports_dir).expanduser().resolve()
    rep_path = Path(args.reputation_db).expanduser().resolve()
    audit_path = latest_audit_file(reports_dir)

    audit_rows = load_jsonl(audit_path) if audit_path else []
    rep_rows = load_jsonl(rep_path)

    recent_audit = keep_recent(audit_rows, since)
    recent_rep = keep_recent(rep_rows, since)

    decision_counts = Counter(str(r.get("decision", "unknown")) for r in recent_audit)
    risk_counts = Counter(str(r.get("risk_level", "unknown")) for r in recent_audit)

    report = {
        "generated_at": now.isoformat(),
        "window_hours": args.hours,
        "sources": {
            "audit_file": str(audit_path) if audit_path else None,
            "reputation_db": str(rep_path),
        },
        "summary": {
            "audit_events_recent": len(recent_audit),
            "reputation_entries_recent": len(recent_rep),
            "decision_counts": dict(decision_counts),
            "risk_level_counts": dict(risk_counts),
        },
        "recent_events": {
            "audit": recent_audit[-args.last :],
            "reputation": recent_rep[-args.last :],
        },
    }

    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
