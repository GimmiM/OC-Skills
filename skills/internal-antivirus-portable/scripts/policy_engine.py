#!/usr/bin/env python3
"""
Deterministic policy decision engine for Internal Antivirus.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import yaml


DEFAULT_DECISION_MAP = {
    "critical": "block",
    "high": "block",
    "medium": "review_and_confirm",
    "low": "allow_with_caution",
    "minimal": "allow",
}


def load_policy(policy_path: str | Path) -> dict:
    p = Path(policy_path).expanduser().resolve()
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_decision_map(policy: dict) -> Dict[str, str]:
    return (
        policy.get("components", {})
        .get("policy_engine", {})
        .get("decision_map", DEFAULT_DECISION_MAP)
    )


def risk_level_from_score(score: int, has_critical: bool) -> str:
    if has_critical:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 20:
        return "medium"
    if score >= 8:
        return "low"
    return "minimal"


def decide(
    score: int,
    findings: List[dict],
    policy_path: str | Path,
) -> Tuple[str, str, str]:
    """Returns (risk_level, decision, reason)."""
    has_critical = any(str(f.get("severity", "")).lower() == "critical" for f in findings)
    level = risk_level_from_score(score, has_critical)

    policy = load_policy(policy_path)
    dmap = get_decision_map(policy)
    decision = dmap.get(level, "review_and_confirm")

    reason = f"policy_engine decision: level={level}, score={score}, findings={len(findings)}"
    return level, decision, reason
