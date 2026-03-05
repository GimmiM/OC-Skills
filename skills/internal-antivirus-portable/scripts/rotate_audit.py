#!/usr/bin/env python3
"""Rotate internal-antivirus audit logs by retention days."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate internal-antivirus audit logs")
    parser.add_argument("--reports-dir", default=str(Path(__file__).resolve().parents[1] / "reports"))
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    reports = Path(args.reports_dir).expanduser().resolve()
    reports.mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.retention_days)
    removed = []

    for p in sorted(reports.glob("audit-*.jsonl")):
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            removed.append(p)
            if not args.dry_run:
                p.unlink(missing_ok=True)

    print(f"reports_dir={reports}")
    print(f"retention_days={args.retention_days}")
    print(f"removed={len(removed)}")
    for r in removed:
        print(r)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
