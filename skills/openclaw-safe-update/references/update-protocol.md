# OpenClaw Update Protocol

## Overview

This document describes the complete safety protocol for updating OpenClaw while protecting against:
- Lost API keys
- Disappearing skills
- Memory/state loss
- Configuration corruption

## Pre-Update Checklist

### 1. System State Check
```bash
python3 scripts/update-orchestrator.py --action check --json
```

Expected output:
```json
{
  "status": "success",
  "data": {
    "installed_version": "2026.2.25",
    "config_version": "2026.2.25",
    "latest_available": "2026.3.1",
    "needs_update": true
  }
}
```

### 2. Create Backup (Mandatory)
```bash
python3 scripts/update-orchestrator.py --action backup --json
```

Backup includes:
- `openclaw.json` - Main configuration
- `.env` - Environment variables
- `workspace/` - All skills, memory, tasks
- `cron/` - Scheduled jobs
- `agents/` - Agent configurations
- `versions.json` - Version metadata

### 3. Get Explicit Confirmation

User MUST explicitly confirm by:
- Using `--confirm-update` flag, OR
- Typing "UPDATE" or "ОБНОВИТЬ" in chat

Without confirmation, update will abort with exit code 5.

## Update Execution

### Step-by-Step

1. **Stop Gateway**
   ```bash
   pkill -f 'openclaw gateway'
   ```

2. **Run NPM Update**
   ```bash
   cd ~/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw
   npm update
   ```

3. **Verify Installation**
   ```bash
   python3 scripts/update-orchestrator.py --action verify --json
   ```

## Post-Update Verification

### Critical Checks

| Check | Method | Expected Result |
|-------|--------|-----------------|
| Config loads | Parse JSON | Valid JSON, no errors |
| Auth profiles | Check structure | `auth.profiles` exists |
| Channels | Check structure | `channels` configured |
| Workspace | Directory exists | `workspace/` present |
| Skills | Directory exists | `workspace/skills/` present |

### Manual Verification Steps

1. Check gateway starts without errors
2. Verify Telegram bot responds
3. Test one simple skill
4. Check cron jobs are loaded

## Rollback Procedure

If anything fails during or after update:

```bash
# Automatic rollback
python3 scripts/update-orchestrator.py --action rollback --json

# Manual rollback (if automatic fails)
tar -xzf ~/.openclaw/backups/pre-update-YYYYMMDD-HHMMSS.tar.gz -C ~/.openclaw/
```

## Known Issues and Mitigations

### Issue: API Keys "Sticking"
**Symptom:** New API key set but old one still used
**Cause:** Cached credentials in config
**Mitigation:** Full config backup + restore on rollback

### Issue: Skills Disappearing
**Symptom:** Skills not loaded after update
**Cause:** Skills directory not preserved
**Mitigation:** Workspace backup includes skills/

### Issue: Memory Loss
**Symptom:** Long-term memory files empty
**Cause:** Workspace not backed up
**Mitigation:** Full workspace backup

### Issue: Cron Jobs Lost
**Symptom:** Scheduled tasks not running
**Cause:** Cron directory not preserved
**Mitigation:** Cron directory in backup

## Safety Rules

1. **Never skip backup**
2. **Never update without confirmation**
3. **Never update during active tasks**
4. **Always verify after update**
5. **Keep last 5 backups minimum**

## Backup Retention

Default retention: 10 pre-update backups

To clean old backups:
```bash
ls -t ~/.openclaw/backups/pre-update-*.tar.gz | tail -n +11 | xargs rm -f
```
