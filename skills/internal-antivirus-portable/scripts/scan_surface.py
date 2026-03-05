#!/usr/bin/env python3
"""
Internal Antivirus v1: lightweight runtime surface audit.
Checks listening ports + simple OpenClaw runtime signals.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import platform
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


SENSITIVE_PORTS = {
    22: ("medium", "SSH service exposed"),
    2375: ("critical", "Docker daemon (2375) exposed"),
    2376: ("high", "Docker daemon TLS port exposed"),
    3306: ("high", "MySQL port exposed"),
    5432: ("high", "PostgreSQL port exposed"),
    6379: ("critical", "Redis port exposed"),
    27017: ("high", "MongoDB port exposed"),
    18789: ("high", "OpenClaw default gateway port exposed"),
}


@dataclass
class PortFinding:
    protocol: str
    host: str
    port: int
    exposure: str
    severity: str
    reason: str


def _run(cmd: List[str]) -> str:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            return res.stdout
    except Exception:
        pass
    return ""


def exposure(host: str) -> str:
    h = host.strip().lower()
    if h == "localhost":
        return "local_only"
    if h == chr(42):  # '*'
        return "public"

    try:
        ip = ipaddress.ip_address(h)
        if ip.is_loopback:
            return "local_only"
        if ip.is_unspecified:
            return "public"
        return "private_net"
    except ValueError:
        return "private_net"


def parse_darwin_lsof() -> List[Tuple[str, str, int]]:
    out = _run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
    lines = out.splitlines()[1:] if out else []
    results = []
    for line in lines:
        m = re.search(r"(TCP)\s+([^\s:>]+):(\d+)\s*\(LISTEN\)", line)
        if m:
            proto = m.group(1).lower()
            host = m.group(2)
            port = int(m.group(3))
            results.append((proto, host, port))
    return results


def parse_linux_ss() -> List[Tuple[str, str, int]]:
    out = _run(["ss", "-lntuH"])
    if not out:
        return []
    results = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto = "udp" if parts[0].startswith("udp") else "tcp"
        addr = parts[4]
        if addr.startswith("["):
            m = re.match(r"\[(.*)]:(\d+)$", addr)
            if not m:
                continue
            host, port = m.group(1), int(m.group(2))
        else:
            i = addr.rfind(":")
            if i <= 0:
                continue
            host, port = addr[:i], int(addr[i + 1:])
        results.append((proto, host, port))
    return results


def collect_ports() -> List[Tuple[str, str, int]]:
    sysname = platform.system().lower()
    if "darwin" in sysname:
        return parse_darwin_lsof()
    ports = parse_linux_ss()
    if ports:
        return ports
    # fallback for linux/mac if parsers fail
    out = _run(["netstat", "-an"])
    results = []
    for line in out.splitlines():
        if "LISTEN" not in line.upper():
            continue
        m = re.search(r"([0-9a-fA-F:.]+)\.(\d+)", line)
        if m:
            results.append(("tcp", m.group(1), int(m.group(2))))
    return results


def audit_ports() -> List[PortFinding]:
    findings: List[PortFinding] = []
    for proto, host, port in collect_ports():
        if port not in SENSITIVE_PORTS:
            continue
        sev, reason = SENSITIVE_PORTS[port]
        exp = exposure(host)
        if exp == "local_only":
            sev = "low" if sev != "critical" else "medium"
            reason = f"{reason} (local-only)"
        findings.append(PortFinding(proto, host, port, exp, sev, reason))
    return findings


def score_findings(findings: List[PortFinding]) -> Tuple[int, str, str]:
    score = 0
    has_critical = False
    for f in findings:
        if f.severity == "critical":
            score += 50
            has_critical = True
        elif f.severity == "high":
            score += 30
        elif f.severity == "medium":
            score += 15
        else:
            score += 5
    score = min(score, 100)

    if has_critical:
        level = "critical"
    elif score >= 45:
        level = "high"
    elif score >= 20:
        level = "medium"
    elif score >= 8:
        level = "low"
    else:
        level = "minimal"

    recommendation = "investigate_now" if level in {"critical", "high"} else ("review" if level == "medium" else "monitor")
    return score, level, recommendation


def write_audit(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal AV runtime surface scan")
    parser.add_argument("--audit-log", default="", help="Optional JSONL path")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    findings = audit_ports()
    score, level, recommendation = score_findings(findings)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host_os": platform.system(),
        "risk_score": score,
        "risk_level": level,
        "recommendation": recommendation,
        "summary": {
            "total_findings": len(findings),
            "critical": sum(1 for x in findings if x.severity == "critical"),
            "high": sum(1 for x in findings if x.severity == "high"),
            "medium": sum(1 for x in findings if x.severity == "medium"),
            "low": sum(1 for x in findings if x.severity == "low"),
        },
        "findings": [asdict(f) for f in findings],
    }

    if args.audit_log:
        write_audit(Path(args.audit_log), {
            "type": "scan_surface",
            "risk_level": level,
            "risk_score": score,
            "recommendation": recommendation,
            "ts": report["generated_at"],
        })

    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
