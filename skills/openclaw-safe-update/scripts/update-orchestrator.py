#!/usr/bin/env python3
"""
OpenClaw Safe Update Orchestrator
CLI contract: JSON I/O, fixed exit codes, --dry-run support
"""

import argparse
import json
import os
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime
from pathlib import Path

# Configuration
OPENCLAW_DIR = Path.home() / ".openclaw"
BACKUP_DIR = OPENCLAW_DIR / "backups"
NODE_MODULES_PATH = Path("~/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw").expanduser()
GATEWAY_URL = "http://localhost:PORT  # Set your OpenClaw gateway port"

# Exit codes
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_BACKUP_FAILED = 2
EXIT_UPDATE_FAILED = 3
EXIT_VERIFICATION_FAILED = 4
EXIT_NEEDS_CONFIRMATION = 5


def generate_request_id():
    return str(uuid.uuid4())[:8]


def json_output(status, action, data=None, error=None, duration_ms=0):
    return {
        "status": status,
        "action": action,
        "request_id": generate_request_id(),
        "duration_ms": duration_ms,
        "data": data or {},
        "error": error
    }


def run_command(cmd, capture=True):
    """Run shell command and return result"""
    try:
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            return {"returncode": os.system(cmd), "stdout": "", "stderr": ""}
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Timeout"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def action_check(args):
    """Check for available updates"""
    start = time.time()
    
    # Get current installed version
    try:
        package_json = NODE_MODULES_PATH / "package.json"
        if package_json.exists():
            import json as json_lib
            with open(package_json) as f:
                pkg = json_lib.load(f)
            current_version = pkg.get("version", "unknown")
        else:
            current_version = "unknown"
    except:
        current_version = "unknown"
    
    # Get config version
    try:
        config_file = OPENCLAW_DIR / "openclaw.json"
        if config_file.exists():
            import json as json_lib
            with open(config_file) as f:
                cfg = json_lib.load(f)
            config_version = cfg.get("meta", {}).get("lastTouchedVersion", "unknown")
        else:
            config_version = "unknown"
    except:
        config_version = "unknown"
    
    # Check npm for latest version
    npm_check = run_command("npm view openclaw version 2>/dev/null")
    latest_version = npm_check["stdout"].strip() if npm_check["returncode"] == 0 else "unknown"
    
    needs_update = latest_version != "unknown" and latest_version != current_version
    
    data = {
        "installed_version": current_version,
        "config_version": config_version,
        "latest_available": latest_version,
        "needs_update": needs_update
    }
    
    duration = int((time.time() - start) * 1000)
    print(json.dumps(json_output("success", "check", data, duration_ms=duration)))
    return EXIT_SUCCESS


def action_backup(args):
    """Create pre-update backup"""
    start = time.time()
    
    if args.dry_run:
        print(json.dumps(json_output(
            "success", "backup", 
            {"dry_run": True, "would_backup": str(BACKUP_DIR / "pre-update-<timestamp>.tar.gz")},
            duration_ms=0
        )))
        return EXIT_SUCCESS
    
    # Check available disk space (need at least 500MB)
    MIN_FREE_MB = 500
    try:
        stat = os.statvfs(OPENCLAW_DIR)
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        if free_mb < MIN_FREE_MB:
            print(json.dumps(json_output(
                "error", "backup",
                error=f"Insufficient disk space: {free_mb:.0f}MB free, need at least {MIN_FREE_MB}MB",
                duration_ms=int((time.time() - start) * 1000)
            )))
            return EXIT_BACKUP_FAILED
    except Exception as e:
        print(json.dumps(json_output(
            "error", "backup",
            error=f"Failed to check disk space: {str(e)}",
            duration_ms=int((time.time() - start) * 1000)
        )))
        return EXIT_BACKUP_FAILED
    
    # Ensure backup directory exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f"pre-update-{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    archive_path = BACKUP_DIR / f"{backup_name}.tar.gz"
    
    try:
        # Create backup directory
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Files to backup
        files_to_backup = [
            ("openclaw.json", OPENCLAW_DIR / "openclaw.json"),
            (".env", OPENCLAW_DIR / ".env"),
            ("workspace", OPENCLAW_DIR / "workspace"),
            ("cron", OPENCLAW_DIR / "cron"),
            ("agents", OPENCLAW_DIR / "agents"),
        ]
        
        backed_up = []
        for name, src in files_to_backup:
            if src.exists():
                dest = backup_path / name
                if src.is_dir():
                    import shutil
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    import shutil
                    shutil.copy2(src, dest)
                backed_up.append(name)
        
        # Create versions info
        versions_info = {
            "timestamp": datetime.now().isoformat(),
            "node_version": run_command("node --version")["stdout"].strip(),
            "npm_version": run_command("npm --version")["stdout"].strip(),
        }
        with open(backup_path / "versions.json", "w") as f:
            json.dump(versions_info, f, indent=2)
        
        # Create archive
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_name)
        
        # Verify archive
        if not tarfile.is_tarfile(archive_path):
            raise Exception("Archive integrity check failed")
        
        # Set secure permissions (owner only)
        import os
        os.chmod(archive_path, 0o600)  # rw-------
        os.chmod(BACKUP_DIR, 0o700)    # rwx------ (new files inherit)
        
        # Cleanup temp directory
        import shutil
        shutil.rmtree(backup_path)
        
        # Save last backup path
        with open(BACKUP_DIR / "last-backup-path.txt", "w") as f:
            f.write(str(archive_path))
        
        # Get archive size
        size_bytes = archive_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        data = {
            "backup_path": str(archive_path),
            "size_mb": size_mb,
            "backed_up_items": backed_up,
            "timestamp": timestamp
        }
        
        duration = int((time.time() - start) * 1000)
        print(json.dumps(json_output("success", "backup", data, duration_ms=duration)))
        return EXIT_SUCCESS
        
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        print(json.dumps(json_output("error", "backup", error=str(e), duration_ms=duration)))
        return EXIT_BACKUP_FAILED


def action_update(args):
    """Execute OpenClaw update"""
    start = time.time()
    
    # Check for confirmation
    if not args.confirm_update:
        data = {
            "message": "Update requires explicit confirmation. Use --confirm-update flag or type 'UPDATE'",
            "safety_requirements": [
                "Backup must be created first",
                "User must explicitly confirm with --confirm-update",
                "All tasks will be interrupted"
            ]
        }
        print(json.dumps(json_output("needs_confirmation", "update", data, duration_ms=0)))
        return EXIT_NEEDS_CONFIRMATION
    
    if args.dry_run:
        print(json.dumps(json_output(
            "success", "update",
            {"dry_run": True, "would_update": str(NODE_MODULES_PATH)},
            duration_ms=0
        )))
        return EXIT_SUCCESS
    
    # Verify backup exists
    last_backup_file = BACKUP_DIR / "last-backup-path.txt"
    if not last_backup_file.exists():
        print(json.dumps(json_output(
            "error", "update",
            error="No backup found. Run --action backup first",
            duration_ms=int((time.time() - start) * 1000)
        )))
        return EXIT_UPDATE_FAILED
    
    # Get current version for rollback info
    check_result = action_check(args)
    
    # Stop gateway
    stop_result = run_command("pkill -f 'openclaw gateway' 2>/dev/null || true")
    time.sleep(2)  # Wait for shutdown
    
    # Perform npm update
    update_result = run_command(f"cd {NODE_MODULES_PATH} && npm update 2>&1")
    
    if update_result["returncode"] != 0:
        error_data = {
            "npm_output": update_result["stdout"],
            "npm_error": update_result["stderr"],
            "suggestion": "Run --action rollback to restore previous version"
        }
        print(json.dumps(json_output(
            "error", "update", error_data,
            duration_ms=int((time.time() - start) * 1000)
        )))
        return EXIT_UPDATE_FAILED
    
    # Get new version
    new_check = run_command("npm view openclaw version 2>/dev/null")
    new_version = new_check["stdout"].strip() if new_check["returncode"] == 0 else "unknown"
    
    data = {
        "previous_version": "see backup", 
        "new_version": new_version,
        "npm_output": update_result["stdout"][:500] if update_result["stdout"] else "success"
    }
    
    duration = int((time.time() - start) * 1000)
    print(json.dumps(json_output("success", "update", data, duration_ms=duration)))
    return EXIT_SUCCESS


def action_verify(args):
    """Verify post-update state"""
    start = time.time()
    checks = {}
    
    # Check 1: Config loads
    config_file = OPENCLAW_DIR / "openclaw.json"
    checks["config_exists"] = config_file.exists()
    
    # Check 2: Gateway can start (basic check)
    # We'll check if the gateway binary/script exists
    gateway_start = OPENCLAW_DIR / "gateway-start.sh"
    checks["gateway_script_exists"] = gateway_start.exists()
    
    # Check 3: API keys structure intact
    try:
        with open(config_file) as f:
            cfg = json.load(f)
        checks["config_valid_json"] = True
        checks["auth_profiles_exist"] = "auth" in cfg and "profiles" in cfg["auth"]
        checks["channels_configured"] = "channels" in cfg
    except:
        checks["config_valid_json"] = False
        checks["auth_profiles_exist"] = False
        checks["channels_configured"] = False
    
    # Check 4: Workspace exists
    checks["workspace_exists"] = (OPENCLAW_DIR / "workspace").exists()
    
    # Check 5: Skills directory exists
    checks["skills_exist"] = (OPENCLAW_DIR / "workspace" / "skills").exists()
    
    all_passed = all(checks.values())
    
    data = {
        "all_checks_passed": all_passed,
        "checks": checks,
        "recommendation": "Run --action verify again after gateway start" if all_passed else "Run --action rollback immediately"
    }
    
    duration = int((time.time() - start) * 1000)
    status = "success" if all_passed else "error"
    print(json.dumps(json_output(status, "verify", data, duration_ms=duration)))
    
    return EXIT_SUCCESS if all_passed else EXIT_VERIFICATION_FAILED


def action_rollback(args):
    """Rollback to previous version from backup"""
    start = time.time()
    
    if args.dry_run:
        print(json.dumps(json_output(
            "success", "rollback",
            {"dry_run": True, "message": "Would restore from last backup"},
            duration_ms=0
        )))
        return EXIT_SUCCESS
    
    # Get last backup path
    last_backup_file = BACKUP_DIR / "last-backup-path.txt"
    if not last_backup_file.exists():
        print(json.dumps(json_output(
            "error", "rollback",
            error="No backup found to rollback to",
            duration_ms=int((time.time() - start) * 1000)
        )))
        return EXIT_GENERAL_ERROR
    
    with open(last_backup_file) as f:
        archive_path = Path(f.read().strip())
    
    if not archive_path.exists():
        print(json.dumps(json_output(
            "error", "rollback",
            error=f"Backup archive not found: {archive_path}",
            duration_ms=int((time.time() - start) * 1000)
        )))
        return EXIT_GENERAL_ERROR
    
    # Stop gateway
    run_command("pkill -f 'openclaw gateway' 2>/dev/null || true")
    time.sleep(2)
    
    # Verify archive integrity before extraction
    try:
        # Check 1: Valid tarfile
        if not tarfile.is_tarfile(archive_path):
            raise Exception(f"Archive is not a valid tar file: {archive_path}")
        
        # Check 2: Can list contents (not corrupted)
        with tarfile.open(archive_path, "r:gz") as test_tar:
            members = test_tar.getmembers()
            if not members:
                raise Exception("Archive is empty")
            # Check 3: No suspicious paths (basic path traversal check)
            for member in members:
                if member.name.startswith('/') or '..' in member.name:
                    raise Exception(f"Suspicious path in archive: {member.name}")
    except Exception as e:
        print(json.dumps(json_output(
            "error", "rollback",
            error=f"Archive verification failed: {str(e)}. Do not proceed with rollback.",
            duration_ms=int((time.time() - start) * 1000)
        )))
        return EXIT_GENERAL_ERROR
    
    try:
        # Extract backup to temp location first (safely)
        with tarfile.open(archive_path, "r:gz") as tar:
            # Extract to temp location first
            temp_extract = BACKUP_DIR / "rollback-temp"
            temp_extract.mkdir(exist_ok=True)
            tar.extractall(temp_extract)
            
            # Find the extracted directory
            extracted_dirs = [d for d in temp_extract.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise Exception("No directory found in backup archive")
            
            backup_content = extracted_dirs[0]
            
            # Verify extracted content has essential files before removing live data
            required_items = ["openclaw.json", "workspace"]
            missing = [item for item in required_items if not (backup_content / item).exists()]
            if missing:
                raise Exception(f"Backup missing essential items: {missing}. Aborting rollback.")
            
            # Restore files
            restored = []
            for item in backup_content.iterdir():
                dest = OPENCLAW_DIR / item.name
                if dest.exists():
                    if dest.is_dir():
                        import shutil
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                
                import shutil
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
                restored.append(item.name)
            
            # Cleanup temp
            import shutil
            shutil.rmtree(temp_extract)
        
        data = {
            "restored_from": str(archive_path),
            "restored_items": restored,
            "message": "Rollback complete. Restart gateway manually."
        }
        
        duration = int((time.time() - start) * 1000)
        print(json.dumps(json_output("success", "rollback", data, duration_ms=duration)))
        return EXIT_SUCCESS
        
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        print(json.dumps(json_output("error", "rollback", error=str(e), duration_ms=duration)))
        return EXIT_GENERAL_ERROR


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Safe Update Orchestrator")
    parser.add_argument("--action", required=True,
                       choices=["check", "backup", "update", "verify", "rollback"],
                       help="Action to perform")
    parser.add_argument("--json", action="store_true",
                       help="Output JSON (always enabled)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulate without making changes")
    parser.add_argument("--confirm-update", action="store_true",
                       help="Explicit confirmation for update action")
    
    args = parser.parse_args()
    
    actions = {
        "check": action_check,
        "backup": action_backup,
        "update": action_update,
        "verify": action_verify,
        "rollback": action_rollback,
    }
    
    exit_code = actions[args.action](args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
