#!/usr/bin/env python3
"""
Eval-smoke tests for openclaw-safe-update
Run: python3 scripts/eval-smoke.py
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent / "update-orchestrator.py"

def run_test(args, expected_exit=None, check_contains=None):
    """Run a test case"""
    cmd = ["python3", str(SCRIPT_PATH)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        output = json.loads(result.stdout)
    except:
        output = {"raw": result.stdout, "error": "Invalid JSON"}
    
    success = True
    errors = []
    
    if expected_exit is not None and result.returncode != expected_exit:
        success = False
        errors.append(f"Expected exit {expected_exit}, got {result.returncode}")
    
    if check_contains:
        for key, value in check_contains.items():
            if key == "status":
                if output.get("status") != value:
                    success = False
                    errors.append(f"Expected status '{value}', got '{output.get('status')}'")
            elif key in output.get("data", {}):
                if output["data"][key] != value:
                    success = False
                    errors.append(f"Expected data.{key}='{value}', got '{output['data'][key]}'")
    
    return {
        "success": success,
        "exit_code": result.returncode,
        "output": output,
        "errors": errors
    }

def test_check_action():
    """Test 1: Check action returns version info"""
    print("Test 1: Check action...")
    result = run_test(
        ["--action", "check", "--json"],
        expected_exit=0,
        check_contains={"status": "success"}
    )
    
    # Verify structure
    data = result["output"].get("data", {})
    required_fields = ["installed_version", "config_version", "latest_available", "needs_update"]
    for field in required_fields:
        if field not in data:
            result["success"] = False
            result["errors"].append(f"Missing field: {field}")
    
    print(f"  {'✅' if result['success'] else '❌'} Check action")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_backup_dry_run():
    """Test 2: Backup dry-run mode"""
    print("Test 2: Backup dry-run...")
    result = run_test(
        ["--action", "backup", "--dry-run", "--json"],
        expected_exit=0,
        check_contains={"status": "success"}
    )
    
    # Verify dry_run flag in output
    data = result["output"].get("data", {})
    if not data.get("dry_run"):
        result["success"] = False
        result["errors"].append("dry_run not set in response")
    
    print(f"  {'✅' if result['success'] else '❌'} Backup dry-run")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_backup_real():
    """Test 3: Backup creates actual archive"""
    print("Test 3: Backup real...")
    result = run_test(
        ["--action", "backup", "--json"],
        expected_exit=0,
        check_contains={"status": "success"}
    )
    
    # Verify backup path exists
    data = result["output"].get("data", {})
    backup_path = data.get("backup_path")
    if backup_path and not Path(backup_path).exists():
        result["success"] = False
        result["errors"].append(f"Backup file not found: {backup_path}")
    
    print(f"  {'✅' if result['success'] else '❌'} Backup real")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_update_needs_confirmation():
    """Test 4: Update without confirmation fails"""
    print("Test 4: Update needs confirmation...")
    result = run_test(
        ["--action", "update", "--json"],
        expected_exit=5,  # EXIT_NEEDS_CONFIRMATION
        check_contains={"status": "needs_confirmation"}
    )
    
    print(f"  {'✅' if result['success'] else '❌'} Update needs confirmation")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_update_dry_run():
    """Test 5: Update dry-run"""
    print("Test 5: Update dry-run...")
    result = run_test(
        ["--action", "update", "--dry-run", "--json"],
        expected_exit=0,
        check_contains={"status": "success"}
    )
    
    data = result["output"].get("data", {})
    if not data.get("dry_run"):
        result["success"] = False
        result["errors"].append("dry_run not set in response")
    
    print(f"  {'✅' if result['success'] else '❌'} Update dry-run")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_verify_action():
    """Test 6: Verify action checks system state"""
    print("Test 6: Verify action...")
    result = run_test(
        ["--action", "verify", "--json"],
        expected_exit=0,
        check_contains={"status": "success"}
    )
    
    # Verify checks structure
    data = result["output"].get("data", {})
    checks = data.get("checks", {})
    required_checks = ["config_exists", "workspace_exists", "skills_exist"]
    for check in required_checks:
        if check not in checks:
            result["success"] = False
            result["errors"].append(f"Missing check: {check}")
    
    print(f"  {'✅' if result['success'] else '❌'} Verify action")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_rollback_dry_run():
    """Test 7: Rollback dry-run"""
    print("Test 7: Rollback dry-run...")
    result = run_test(
        ["--action", "rollback", "--dry-run", "--json"],
        expected_exit=0,
        check_contains={"status": "success"}
    )
    
    print(f"  {'✅' if result['success'] else '❌'} Rollback dry-run")
    if not result["success"]:
        print(f"    Errors: {result['errors']}")
    return result["success"]

def test_json_output_structure():
    """Test 8: All outputs have required JSON fields"""
    print("Test 8: JSON structure...")
    
    required_fields = ["status", "action", "request_id", "duration_ms", "data", "error"]
    all_pass = True
    
    for action in ["check", "backup", "verify"]:
        result = run_test(["--action", action, "--json"], expected_exit=0)
        output = result["output"]
        
        for field in required_fields:
            if field not in output:
                all_pass = False
                print(f"  ❌ Action '{action}' missing field: {field}")
    
    if all_pass:
        print(f"  ✅ JSON structure")
    return all_pass

def test_exit_codes():
    """Test 9: Verify correct exit codes"""
    print("Test 9: Exit codes...")
    
    tests = [
        (["--action", "check", "--json"], 0, "check success"),
        (["--action", "update", "--json"], 5, "update needs confirmation"),
    ]
    
    all_pass = True
    for args, expected, desc in tests:
        result = run_test(args, expected_exit=expected)
        if not result["success"]:
            all_pass = False
            print(f"  ❌ {desc}: expected exit {expected}")
    
    if all_pass:
        print(f"  ✅ Exit codes")
    return all_pass

def test_invalid_action():
    """Test 10: Invalid action handling"""
    print("Test 10: Invalid action...")
    
    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--action", "invalid", "--json"],
        capture_output=True, text=True
    )
    
    # Should fail with argparse error
    success = result.returncode != 0
    
    print(f"  {'✅' if success else '❌'} Invalid action rejected")
    return success

def main():
    print("=" * 50)
    print("OpenClaw Safe Update - Eval Smoke Tests")
    print("=" * 50)
    print()
    
    tests = [
        test_check_action,
        test_backup_dry_run,
        test_backup_real,
        test_update_needs_confirmation,
        test_update_dry_run,
        test_verify_action,
        test_rollback_dry_run,
        test_json_output_structure,
        test_exit_codes,
        test_invalid_action,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            results.append(False)
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
