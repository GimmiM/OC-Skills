---
name: openclaw-safe-update
description: Safely update OpenClaw with mandatory pre-update backup, verification, and rollback capabilities. Use when user explicitly requests to update OpenClaw, when new version is available and user confirms with "UPDATE", or when rolling back after a failed update.
---

# OpenClaw Safe Update

Perform safe, reversible OpenClaw updates with full backup protection.

## Workflow

1. **Pre-update backup** (mandatory)
2. **Document current state**
3. **Get explicit confirmation**
4. **Execute update**
5. **Verify post-update**
6. **Report results**

## Commands

### Check for updates
```bash
python3 scripts/update-orchestrator.py --action check --json
```

### Create pre-update backup
```bash
python3 scripts/update-orchestrator.py --action backup --json
```

### Perform update (requires --confirm-update flag)
```bash
python3 scripts/update-orchestrator.py --action update --confirm-update --json
```

### Verify after update
```bash
python3 scripts/update-orchestrator.py --action verify --json
```

### Rollback to previous version
```bash
python3 scripts/update-orchestrator.py --action rollback --json
```

## Safety Requirements

**NEVER proceed without:**
1. Successful backup creation
2. User explicitly typing "UPDATE" or "ОБНОВИТЬ"
3. User acknowledgment of 5-10 minute downtime

## JSON Output Format

All scripts output structured JSON:
```json
{
  "status": "success|error|needs_confirmation",
  "action": "check|backup|update|verify|rollback",
  "request_id": "uuid",
  "duration_ms": 1234,
  "data": { ... },
  "error": null
}
```

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Backup failed (do not proceed)
- `3` - Update failed (rollback available)
- `4` - Verification failed
- `5` - Needs user confirmation

## Testing

Run smoke tests to verify functionality:
```bash
python3 scripts/eval-smoke.py
```

Tests cover: version check, backup creation, confirmation requirement, and system verification.

## References

- Full protocol: `references/update-protocol.md`
- Troubleshooting: `references/troubleshooting.md`
- Rollback procedures: `references/rollback-guide.md`
