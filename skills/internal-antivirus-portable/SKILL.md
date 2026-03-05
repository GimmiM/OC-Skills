---
name: internal-antivirus-portable
description: Provides a portable scripts-first antivirus workflow for OpenClaw skill security, using /av commands for setup, pre-install gating, static scan, surface audit, policy checks, regression checks, and reporting; use when safely installing external skills on any OpenClaw host.
---

# Internal Antivirus Portable

Works out of the box in local mode.

## First run

```bash
python3 {baseDir}/scripts/setup_wizard.py
```

- Choose local-only mode (default), or
- Configure Telegram delivery lock for your environment.

## Commands

- `/av help`
- `/av setup`
- `/av scan <path|url>`
- `/av install <path> -- <install_cmd>`
- `/av surface`
- `/av policy-check`
- `/av regression`
- `/av rotate-audit`
- `/av report`

## Mandatory external-skill install path

```bash
python3 {baseDir}/scripts/install_skill.py <TARGET> -- <INSTALL_COMMAND>
```

For `review_and_confirm` decisions:

```bash
python3 {baseDir}/scripts/install_skill.py <TARGET> --owner-approve-risk --approval-reason "Owner approved" -- <INSTALL_COMMAND>
```

## Core scripts

- `scripts/setup_wizard.py`
- `scripts/preinstall_gate.py`
- `scripts/install_skill.py`
- `scripts/scan_skill.py`
- `scripts/scan_surface.py`
- `scripts/policy_check.py`
- `scripts/run_regression.py`
- `scripts/report.py`
- `scripts/rotate_audit.py`
