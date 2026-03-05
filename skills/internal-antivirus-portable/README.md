# Internal Antivirus for OpenClaw

Portable security toolkit for OpenClaw skill installation with mandatory pre-install gating, static analysis, and audit trails.

## Features

- **Mandatory pre-install gate** — blocks malicious skills before installation
- **Static analysis** — 21 detection rules (RCE, exfiltration, persistence, reverse shells, etc.)
- **Surface audit** — host port exposure checks
- **Policy enforcement** — strict allow/review/block decisions
- **Audit trail** — JSONL logs of all scans and decisions
- **Reputation tracking** — SHA256-based artifact history

## Quick Start

```bash
# 1. Extract skill
tar -xzf internal-antivirus-portable.skill

# 2. Run setup wizard (optional - for Telegram delivery lock)
cd internal-antivirus-portable
python3 scripts/setup_wizard.py

# 3. Check policy
python3 scripts/policy_check.py

# 4. Scan external skill before install
python3 scripts/scan_skill.py /path/to/suspicious.skill --pretty

# 5. Install ONLY through gate wrapper
python3 scripts/install_skill.py /path/to/skill.skill -- openclaw skill install /path/to/skill.skill
```

## Commands

- `/av help` — show help
- `/av setup` — configure delivery lock
- `/av scan <path>` — scan skill package
- `/av install <path> -- <cmd>` — gated install
- `/av surface` — host surface audit
- `/av policy-check` — validate policy
- `/av regression` — run test suite
- `/av report` — audit summary

## Security Model

1. **Block** (critical/high risk) — installation forbidden
2. **Review** (medium risk) — requires explicit owner approval
3. **Allow** (low/minimal risk) — proceeds with warning

## Requirements

- Python 3.9+
- PyYAML (`pip install pyyaml`)

## License

MIT
