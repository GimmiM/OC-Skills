PYTHON ?= python3
POLICY ?= policy.yaml

.PHONY: policy-check policy-check-json setup scan-surface scan-skill preinstall-gate install-skill rotate-audit regression report

policy-check:
	$(PYTHON) scripts/policy_check.py --policy $(POLICY)

policy-check-json:
	$(PYTHON) scripts/policy_check.py --policy $(POLICY) --json

setup:
	$(PYTHON) scripts/setup_wizard.py --policy $(POLICY)

scan-surface:
	$(PYTHON) scripts/scan_surface.py --pretty

scan-skill:
	@if [ -z "$(TARGET)" ]; then echo "Usage: make scan-skill TARGET=/path/to/skill"; exit 1; fi
	$(PYTHON) scripts/scan_skill.py "$(TARGET)" --policy $(POLICY) --pretty

preinstall-gate:
	@if [ -z "$(TARGET)" ]; then echo "Usage: make preinstall-gate TARGET=/path/to/skill"; exit 1; fi
	$(PYTHON) scripts/preinstall_gate.py "$(TARGET)" --pretty

install-skill:
	@if [ -z "$(TARGET)" ] || [ -z "$(INSTALL_CMD)" ]; then echo "Usage: make install-skill TARGET=/path/to/skill INSTALL_CMD='openclaw skill install /path/to/skill'"; exit 1; fi
	$(PYTHON) scripts/install_skill.py "$(TARGET)" -- $(INSTALL_CMD)

rotate-audit:
	$(PYTHON) scripts/rotate_audit.py

regression:
	$(PYTHON) scripts/run_regression.py --policy $(POLICY)

report:
	$(PYTHON) scripts/report.py --pretty
