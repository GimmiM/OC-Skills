#!/usr/bin/env python3
"""
Portable policy consistency checker.
- Validates required structure
- Enforces non-bypass security invariants
- Supports local mode out of the box
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def has(seq, item):
    return isinstance(seq, list) and item in seq


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate portable internal antivirus policy")
    parser.add_argument(
        "--policy",
        default=str(Path(__file__).resolve().parents[1] / "policy.yaml"),
        help="Path to policy.yaml",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    path = Path(args.policy).expanduser().resolve()
    if not path.exists():
        msg = f"Policy file not found: {path}"
        if args.json:
            print(json.dumps({"ok": False, "errors": [msg]}, ensure_ascii=False))
        else:
            print(f"❌ {msg}")
        return 2

    with path.open("r", encoding="utf-8") as f:
        policy = yaml.safe_load(f)

    errors = []
    warnings = []

    required_top = [
        "version",
        "name",
        "owner",
        "modes",
        "report_delivery_lock",
        "command_interface",
        "security_hard_guards",
        "install_workflow",
        "components",
        "risk_update_policy",
        "change_control",
        "acceptance_criteria",
    ]
    for k in required_top:
        if k not in policy:
            errors.append(f"Missing top-level key: {k}")

    modes = policy.get("modes", {})
    if modes.get("default_mode") != "strict":
        warnings.append("default_mode is not strict")

    available = modes.get("available", {})
    for mode_name in ("strict", "assist", "change_on_command"):
        if mode_name not in available:
            errors.append(f"modes.available missing: {mode_name}")
            continue
        if available[mode_name].get("llm_apply_active") is not False:
            errors.append(f"{mode_name}.llm_apply_active must be false")

    # Delivery lock (portable)
    delivery = policy.get("report_delivery_lock", {})
    enabled = delivery.get("enabled") is True
    if enabled:
        for k in ("channel", "chat_id", "thread_id", "topic"):
            if not str(delivery.get(k, "")).strip():
                errors.append(f"report_delivery_lock.{k} must be non-empty when enabled=true")
    else:
        if str(delivery.get("channel", "")).strip() not in {"local", ""}:
            warnings.append("delivery lock disabled; channel is not local")

    ci = policy.get("command_interface", {})
    if ci.get("enabled") is not True:
        errors.append("command_interface.enabled must be true")

    aliases = ci.get("aliases", [])
    triggers = ci.get("triggers", [])

    required_aliases = {
        "/av help",
        "/av setup",
        "/av scan <path|url>",
        "/av install <path> -- <install_cmd>",
        "/av surface",
        "/av policy-check",
        "/av regression",
        "/av rotate-audit",
        "/av report",
    }
    for a in required_aliases:
        if a not in aliases:
            errors.append(f"command_interface.aliases missing '{a}'")

    for t in {"av", "/av", "antivirus", "policy check"}:
        if t not in triggers:
            errors.append(f"command_interface.triggers missing '{t}'")

    # install workflow invariants
    iw = policy.get("install_workflow", {})
    if iw.get("mandatory_preinstall_gate") is not True:
        errors.append("install_workflow.mandatory_preinstall_gate must be true")
    if not str(iw.get("gate_script", "")).endswith("scripts/preinstall_gate.py"):
        errors.append("install_workflow.gate_script must end with scripts/preinstall_gate.py")
    if not str(iw.get("install_wrapper_script", "")).endswith("scripts/install_skill.py"):
        errors.append("install_workflow.install_wrapper_script must end with scripts/install_skill.py")
    if "block" not in (iw.get("blocked_decisions", []) or []):
        errors.append("install_workflow.blocked_decisions must include 'block'")
    if iw.get("review_requires_owner_approval") is not True:
        errors.append("install_workflow.review_requires_owner_approval must be true")

    guards = policy.get("security_hard_guards", {})
    for k in [
        "no_install_during_intel_collection",
        "no_exec_during_intel_collection",
        "no_skill_apply_without_owner_approval",
        "no_network_exfiltration",
        "immutable_audit_log",
        "require_hash_for_artifacts",
    ]:
        if guards.get(k) is not True:
            errors.append(f"security_hard_guards.{k} must be true")

    components = policy.get("components", {})
    intel = components.get("intel_collector", {})
    denied = intel.get("denied_actions", [])
    for action in ("exec", "install_skill", "modify_active_rules"):
        if not has(denied, action):
            errors.append(f"intel_collector.denied_actions must include '{action}'")

    publisher = components.get("publisher", {})
    if publisher.get("ruleset_flow", []) != ["incoming", "staging", "approved", "active"]:
        errors.append("publisher.ruleset_flow must be exactly [incoming, staging, approved, active]")

    upd = policy.get("risk_update_policy", {})
    auto_active = upd.get("auto_to_active", {})
    for sev in ("minimal", "low", "medium", "high", "critical"):
        if auto_active.get(sev) is not False:
            errors.append(f"risk_update_policy.auto_to_active.{sev} must be false")

    cc = policy.get("change_control", {})
    if cc.get("llm_can_directly_modify_active") is not False:
        errors.append("change_control.llm_can_directly_modify_active must be false")
    if cc.get("llm_can_run_dangerous_commands") is not False:
        errors.append("change_control.llm_can_run_dangerous_commands must be false")

    ok = len(errors) == 0
    payload = {"ok": ok, "policy": str(path), "errors": errors, "warnings": warnings}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if ok:
            print(f"✅ Policy check passed: {path}")
            for w in warnings:
                print(f"⚠️ {w}")
        else:
            print(f"❌ Policy check failed: {path}")
            for e in errors:
                print(f"  - {e}")
            for w in warnings:
                print(f"⚠️ {w}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
