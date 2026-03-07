# Troubleshooting Guide

## Common Update Issues

### Exit Code 2: Backup Failed

**Symptoms:**
- Backup command returns error
- Archive not created

**Solutions:**
1. Check disk space: `df -h ~/.openclaw`
2. Check permissions: `ls -la ~/.openclaw/`
3. Verify backup directory exists: `mkdir -p ~/.openclaw/backups`

**Manual backup:**
```bash
cd ~/.openclaw
tar -czf backup-manual-$(date +%Y%m%d).tar.gz openclaw.json .env workspace/ cron/ agents/
```

### Exit Code 3: Update Failed

**Symptoms:**
- NPM update returns error
- Version not changed

**Common causes:**
1. Network issues
2. NPM registry unavailable
3. Permission denied

**Solutions:**
1. Check network: `ping registry.npmjs.org`
2. Clear NPM cache: `npm cache clean --force`
3. Try with sudo if permissions issue

**Immediate rollback:**
```bash
python3 scripts/update-orchestrator.py --action rollback --json
```

### Exit Code 4: Verification Failed

**Symptoms:**
- Config file corrupted
- Skills directory missing
- Auth profiles empty

**Solutions:**
1. Check specific component:
   ```bash
   python3 -c "import json; json.load(open('~/.openclaw/openclaw.json'))"
   ```
2. Restore from backup
3. Manual config repair if partial corruption

### Exit Code 5: Needs Confirmation

**Symptoms:**
- Update aborted
- Message: "requires explicit confirmation"

**Solution:**
Add `--confirm-update` flag:
```bash
python3 scripts/update-orchestrator.py --action update --confirm-update --json
```

## Post-Update Issues

### API Keys Not Working

**Symptoms:**
- "Invalid API key" errors
- Providers in "cooldown"

**Diagnosis:**
```bash
# Check if keys are in config
grep -o '"apiKey"' ~/.openclaw/openclaw.json | wc -l
```

**Solutions:**
1. Verify keys in backup: `tar -tzf backup.tar.gz | grep openclaw.json`
2. Restore from backup if different
3. Re-run onboarding: `openclaw onboard`

### Skills Not Loading

**Symptoms:**
- Skills directory empty
- Custom skills missing

**Check:**
```bash
ls ~/.openclaw/workspace/skills/ | wc -l
```

**Solution:**
```bash
# Restore from backup
tar -xzf ~/.openclaw/backups/pre-update-*.tar.gz -C /tmp/
cp -r /tmp/pre-update-*/workspace/skills ~/.openclaw/workspace/
```

### Memory Files Empty

**Symptoms:**
- `MEMORY.md` is default/empty
- Daily memory files missing

**Check:**
```bash
ls ~/.openclaw/workspace/memory/ | head
```

**Solution:**
Restore workspace from backup:
```bash
tar -xzf ~/.openclaw/backups/pre-update-*.tar.gz -C /tmp/
cp -r /tmp/pre-update-*/workspace/memory ~/.openclaw/workspace/
cp /tmp/pre-update-*/workspace/MEMORY.md ~/.openclaw/workspace/
```

### Cron Jobs Lost

**Symptoms:**
- Scheduled tasks not running
- Empty cron list

**Check:**
```bash
ls ~/.openclaw/cron/
```

**Solution:**
```bash
tar -xzf ~/.openclaw/backups/pre-update-*.tar.gz -C /tmp/
cp -r /tmp/pre-update-*/cron ~/.openclaw/
```

## Emergency Recovery

If everything fails:

1. Stop gateway completely
2. Restore full backup:
   ```bash
   tar -xzf ~/.openclaw/backups/pre-update-YYYYMMDD-HHMMSS.tar.gz -C ~/.openclaw/
   ```
3. Reinstall exact version:
   ```bash
   cd ~/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw
   npm install openclaw@PREVIOUS_VERSION
   ```
4. Restart gateway

## Debug Mode

Enable verbose output:
```bash
python3 scripts/update-orchestrator.py --action verify --json 2>&1 | tee debug.log
```

## Getting Help

If issues persist after rollback:
1. Check OpenClaw documentation: https://docs.openclaw.ai
2. Review CHANGELOG for breaking changes
3. Check GitHub issues: https://github.com/openclaw/openclaw/issues
