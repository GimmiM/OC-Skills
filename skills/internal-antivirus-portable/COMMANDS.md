# Internal Antivirus Portable — Commands

## Main commands

- `/av help`
- `/av setup`
- `/av scan <path|url>`
- `/av install <path> -- <install_cmd>`
- `/av surface`
- `/av policy-check`
- `/av regression`
- `/av rotate-audit`
- `/av report`

## Local script usage

```bash
python3 scripts/setup_wizard.py
python3 scripts/policy_check.py --policy policy.yaml
python3 scripts/scan_skill.py <TARGET> --policy policy.yaml --pretty
python3 scripts/preinstall_gate.py <TARGET> --pretty
python3 scripts/install_skill.py <TARGET> -- <INSTALL_COMMAND>
python3 scripts/scan_surface.py --pretty
python3 scripts/run_regression.py --policy policy.yaml
python3 scripts/report.py --pretty
```

## Trigger words

- av
- /av
- antivirus
- policy check
- scan skill
- preinstall gate
- regression
- audit log
