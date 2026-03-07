# Rollback Guide

## When to Rollback

Rollback immediately if:
- ❌ Gateway fails to start after update
- ❌ API keys not working
- ❌ Skills missing or not loading
- ❌ Memory/state lost
- ❌ Verification checks fail
- ❌ Any critical functionality broken

## Quick Rollback

### Automatic Rollback
```bash
python3 scripts/update-orchestrator.py --action rollback --json
```

This will:
1. Stop running gateway
2. Restore all files from last backup
3. Report what was restored

### Manual Rollback (if automatic fails)

#### Step 1: Stop Gateway
```bash
pkill -f 'openclaw gateway' 2>/dev/null || true
sleep 2
```

#### Step 2: Find Latest Backup
```bash
ls -t ~/.openclaw/backups/pre-update-*.tar.gz | head -1
```

#### Step 3: Extract Backup
```bash
BACKUP=$(ls -t ~/.openclaw/backups/pre-update-*.tar.gz | head -1)
tar -xzf "$BACKUP" -C /tmp/
```

#### Step 4: Restore Files
```bash
# Get backup directory name
BACKUP_DIR=$(tar -tzf "$BACKUP" | head -1 | cut -d'/' -f1)

# Restore config
cp /tmp/$BACKUP_DIR/openclaw.json ~/.openclaw/

# Restore environment
cp /tmp/$BACKUP_DIR/.env ~/.openclaw/ 2>/dev/null || true

# Restore workspace
rm -rf ~/.openclaw/workspace
cp -r /tmp/$BACKUP_DIR/workspace ~/.openclaw/

# Restore cron
rm -rf ~/.openclaw/cron
cp -r /tmp/$BACKUP_DIR/cron ~/.openclaw/ 2>/dev/null || true

# Restore agents
rm -rf ~/.openclaw/agents
cp -r /tmp/$BACKUP_DIR/agents ~/.openclaw/ 2>/dev/null || true
```

#### Step 5: NPM Rollback (if needed)

If NPM update caused issues:
```bash
cd ~/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw

# Get previous version from backup
cat /tmp/$BACKUP_DIR/versions.json

# Install specific version
npm install openclaw@PREVIOUS_VERSION
```

#### Step 6: Cleanup
```bash
rm -rf /tmp/$BACKUP_DIR
```

#### Step 7: Restart Gateway
```bash
~/.openclaw/gateway-start.sh
```

## Partial Rollback

If only specific component is broken:

### Restore Only Config
```bash
tar -xzf ~/.openclaw/backups/pre-update-*.tar.gz -C /tmp/
cp /tmp/pre-update-*/openclaw.json ~/.openclaw/
```

### Restore Only Workspace
```bash
tar -xzf ~/.openclaw/backups/pre-update-*.tar.gz -C /tmp/
rm -rf ~/.openclaw/workspace
cp -r /tmp/pre-update-*/workspace ~/.openclaw/
```

### Restore Only Skills
```bash
tar -xzf ~/.openclaw/backups/pre-update-*.tar.gz -C /tmp/
rm -rf ~/.openclaw/workspace/skills
cp -r /tmp/pre-update-*/workspace/skills ~/.openclaw/workspace/
```

## Verification After Rollback

Run verification to confirm rollback succeeded:
```bash
python3 scripts/update-orchestrator.py --action verify --json
```

Expected: All checks should pass.

## Post-Rollback Steps

1. **Verify API Keys**
   ```bash
   # Check gateway config endpoint (default port 18789)
   curl -s "http://localhost:${PORT}/config" | grep -q '"auth"' && echo "OK" || echo "FAIL"
   ```

2. **Test Telegram**
   Send test message to confirm bot responds.

3. **Check Skills**
   ```bash
   ls ~/.openclaw/workspace/skills/ | wc -l
   ```

4. **Verify Cron**
   ```bash
   # Check gateway cron endpoint (default port 18789)
   curl -s "http://localhost:${PORT}/cron/list" | grep -c "jobId"
   ```

## Prevention

To minimize rollback needs:
1. Always create backup before update
2. Read CHANGELOG for breaking changes
3. Test in non-production first (if available)
4. Update during low-activity periods
