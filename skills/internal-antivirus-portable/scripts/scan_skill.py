#!/usr/bin/env python3
"""
Internal Antivirus v1: static scan for skill folders/packages.
Scripts-first, deterministic, low-latency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# local import
from policy_engine import decide


TEXT_EXTENSIONS = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".mjs", ".cjs",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf",
    ".ps1", ".bat", ".cmd", ".go", ".rs", ".java", ".php", ".rb", ".sql",
}
SKIP_DIRS = {".git", "node_modules", "dist", "build", "venv", ".venv", "__pycache__"}
MAX_FILE_SIZE = 2 * 1024 * 1024


@dataclass
class Rule:
    rid: str
    severity: str
    weight: int
    category: str
    pattern: str
    message: str


@dataclass
class Finding:
    rule_id: str
    severity: str
    category: str
    message: str
    file: str
    line: int
    snippet: str


BASE_RULES: List[Rule] = [
    Rule("RCE-PIPE", "critical", 40, "remote_execution", r"(?:curl|wget)[^\n|]{0,260}\|\s*(?:bash|sh|zsh|python|python3|pwsh|powershell)", "Remote command execution via shell pipe."),
    Rule("OBF-BASE64-EXEC", "high", 25, "obfuscation", r"base64\s+(?:-d|-D|--decode)[^\n]{0,260}\|\s*(?:bash|sh|python|python3|pwsh|powershell)", "Base64 decode followed by execution."),
    Rule("BIN-DOWNLOAD", "high", 22, "binary_delivery", r"(?:curl|wget|download)[^\n]{0,260}\.(?:exe|dmg|pkg|appimage|bin|msi|apk)", "External binary download pattern."),
    Rule("EXFIL-POST", "critical", 35, "exfiltration", r"(?:curl|wget)[^\n]{0,260}\s-(?:X\s*)?POST[^\n]{0,260}(?:--data|--data-binary|@)", "Possible data exfiltration via POST."),
    Rule("UNSAFE-EVAL", "high", 18, "code_injection", r"\b(?:eval|exec)\s*\(", "Dynamic code execution (eval/exec)."),
    Rule("UNSAFE-SHELLTRUE", "medium", 12, "unsafe_exec", r"subprocess\.(?:run|Popen|call)\([^\n]{0,260}shell\s*=\s*True", "subprocess shell=True is risky."),
    Rule("UNSAFE-OSSYSTEM", "medium", 10, "unsafe_exec", r"\bos\.system\s*\(", "os.system usage found."),
    Rule("HTTP-IP-SRC", "high", 20, "insecure_transport", r"http://|https?://(?:\d{1,3}\.){3}\d{1,3}", "HTTP or raw IP download endpoint."),
    Rule("PRIV-SUDO", "high", 20, "privilege_escalation", r"\bsudo\b", "sudo usage in skill code/instructions."),
]

KEY_RX = re.compile(r"(?:\.mykey|private\s*key|seed\s*phrase|mnemonic|wallet|api[_-]?key|secret[_-]?key)", re.IGNORECASE)
OUTBOUND_RX = re.compile(r"(?:curl\b|requests\.post\b|axios\.post\b|fetch\s*\(|webhook|telegram\.org|discord\.com/api|pastebin|glot\.io)", re.IGNORECASE)


def load_rules(rules_file: Path) -> List[Rule]:
    rules: List[Rule] = list(BASE_RULES)
    if not rules_file.exists():
        return rules

    try:
        data = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return rules

    for item in data.get("rules", []) or []:
        try:
            rules.append(
                Rule(
                    rid=str(item["rid"]),
                    severity=str(item["severity"]).lower(),
                    weight=int(item["weight"]),
                    category=str(item["category"]),
                    pattern=str(item["pattern"]),
                    message=str(item["message"]),
                )
            )
        except Exception:
            continue

    return rules


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    for member in zf.infolist():
        name = member.filename
        if name.startswith("/") or name.startswith("~"):
            raise ValueError(f"Unsafe archive path: {name}")
        target = (dest / name).resolve()
        if not str(target).startswith(str(dest.resolve())):
            raise ValueError(f"ZipSlip path traversal detected: {name}")
    zf.extractall(dest)


def prepare_target(target: Path) -> Tuple[Path, Optional[tempfile.TemporaryDirectory]]:
    if target.is_dir():
        return target, None
    if target.is_file() and target.suffix.lower() in {".zip", ".skill"}:
        tmp = tempfile.TemporaryDirectory(prefix="internal-av-")
        with zipfile.ZipFile(target, "r") as zf:
            _safe_extract(zf, Path(tmp.name))
        return Path(tmp.name), tmp
    raise FileNotFoundError("Target must be folder or .zip/.skill file")


def is_candidate_file(path: Path, scan_docs: bool) -> bool:
    lower_name = path.name.lower()
    if lower_name == "skill.md":
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if scan_docs and path.suffix.lower() in {".md", ".txt"}:
        return True
    # Always inspect installer-like files
    return lower_name in {"install.sh", "setup.sh", "dockerfile"}


def iter_files(root: Path, scan_docs: bool) -> List[Path]:
    out = []
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file():
            continue
        if p.stat().st_size > MAX_FILE_SIZE:
            continue
        if is_candidate_file(p, scan_docs):
            out.append(p)
    return out


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def line_num(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def line_snippet(text: str, ln: int) -> str:
    lines = text.splitlines()
    if 1 <= ln <= len(lines):
        return lines[ln - 1].strip()[:240]
    return ""


def run_scan(root: Path, scan_docs: bool, rules: List[Rule]) -> Tuple[List[Finding], int, Dict[str, int], int]:
    findings: List[Finding] = []
    score = 0
    scanned = 0
    sev_counter = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for f in iter_files(root, scan_docs=scan_docs):
        scanned += 1
        text = read_text(f)
        if not text:
            continue

        rel = str(f.relative_to(root))
        seen_local = set()

        for rule in rules:
            for m in re.finditer(rule.pattern, text, flags=re.IGNORECASE):
                ln = line_num(text, m.start())
                snip = line_snippet(text, ln)

                # avoid obvious self-signature noise in scanners/rule catalogs
                is_rule_catalog = (
                    ("RULES" in text and "Rule(" in text)
                    or "risk-matrix" in rel.lower()
                    or rel.lower().endswith("/scan_skill.py")
                )
                if is_rule_catalog and (
                    snip.startswith("r\"")
                    or "pattern" in snip.lower()
                    or "rule_id" in snip.lower()
                    or "R-" in snip
                    or "severity" in snip.lower()
                    or "sudo" in snip.lower()
                ):
                    continue

                key = (rule.rid, ln, snip)
                if key in seen_local:
                    continue
                seen_local.add(key)

                findings.append(
                    Finding(
                        rule_id=rule.rid,
                        severity=rule.severity,
                        category=rule.category,
                        message=rule.message,
                        file=rel,
                        line=ln,
                        snippet=snip,
                    )
                )
                score += rule.weight
                sev_counter[rule.severity] = sev_counter.get(rule.severity, 0) + 1

        key_hit = KEY_RX.search(text)
        out_hit = OUTBOUND_RX.search(text)
        looks_like_rule_catalog = rel.lower().endswith("/scan_skill.py") and ("RULES" in text and "Rule(" in text)
        if key_hit and out_hit and f.suffix.lower() != ".md" and not looks_like_rule_catalog:
            ln = line_num(text, key_hit.start())
            snip = line_snippet(text, ln)
            findings.append(
                Finding(
                    rule_id="CHAIN-SECRET-EXFIL",
                    severity="critical",
                    category="credential_theft",
                    message="Sensitive material + outbound channel pattern.",
                    file=rel,
                    line=ln,
                    snippet=snip,
                )
            )
            score += 35
            sev_counter["critical"] += 1

    return findings, min(score, 100), sev_counter, scanned


def write_audit(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def artifact_sha256(target: Path) -> str:
    if target.is_file():
        return _sha256_file(target)

    h = hashlib.sha256()
    for p in sorted([x for x in target.rglob("*") if x.is_file()]):
        rel = str(p.relative_to(target)).encode("utf-8", errors="ignore")
        h.update(rel)
        try:
            h.update(_sha256_file(p).encode("ascii"))
        except Exception:
            continue
    return h.hexdigest()


def update_reputation(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def default_audit_log() -> Path:
    base = Path(__file__).resolve().parents[1] / "reports"
    date = datetime.now(timezone.utc).date().isoformat()
    return base / f"audit-{date}.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal AV static scan")
    parser.add_argument("target", help="Path to folder or .zip/.skill")
    parser.add_argument("--policy", default=str(Path(__file__).resolve().parents[1] / "policy.yaml"))
    parser.add_argument("--rules-file", default=str(Path(__file__).resolve().parents[1] / "rules" / "curated_v2.yaml"), help="Path to external curated rules")
    parser.add_argument("--scan-docs", action="store_true", help="Include .md/.txt scan (higher FP)")
    parser.add_argument("--audit-log", default="", help="Optional JSONL audit log path (defaults to reports/audit-YYYY-MM-DD.jsonl)")
    parser.add_argument("--reputation-db", default=str(Path(__file__).resolve().parents[1] / "data" / "reputation.jsonl"), help="Path to reputation JSONL")
    parser.add_argument("--no-reputation", action="store_true", help="Do not append verdict to reputation DB")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print(json.dumps({"error": f"target not found: {target}"}, ensure_ascii=False))
        return 2

    root, tmp = prepare_target(target)
    try:
        rules_file = Path(args.rules_file).expanduser().resolve()
        rules = load_rules(rules_file)

        findings, score, sev, scanned = run_scan(root, scan_docs=args.scan_docs, rules=rules)
        level, decision, reason = decide(score=score, findings=[asdict(f) for f in findings], policy_path=args.policy)

        artifact_hash = artifact_sha256(target)
        generated_at = datetime.now(timezone.utc).isoformat()

        report = {
            "generated_at": generated_at,
            "target": str(target),
            "target_sha256": artifact_hash,
            "scan_root": str(root),
            "rules_file": str(rules_file),
            "rules_loaded": len(rules),
            "scanned_files": scanned,
            "risk_score": score,
            "risk_level": level,
            "decision": decision,
            "reason": reason,
            "summary": {
                "total_findings": len(findings),
                "critical": sev.get("critical", 0),
                "high": sev.get("high", 0),
                "medium": sev.get("medium", 0),
                "low": sev.get("low", 0),
            },
            "findings": [asdict(f) for f in findings],
        }

        audit_path = Path(args.audit_log).expanduser().resolve() if args.audit_log else default_audit_log()
        write_audit(audit_path, {
            "type": "scan_skill",
            "target": str(target),
            "target_sha256": artifact_hash,
            "decision": decision,
            "risk_level": level,
            "risk_score": score,
            "ts": generated_at,
        })

        if not args.no_reputation:
            update_reputation(Path(args.reputation_db).expanduser().resolve(), {
                "ts": generated_at,
                "target": str(target),
                "sha256": artifact_hash,
                "decision": decision,
                "risk_level": level,
                "risk_score": score,
                "findings": len(findings),
            })

        print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0
    finally:
        if tmp is not None:
            tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
