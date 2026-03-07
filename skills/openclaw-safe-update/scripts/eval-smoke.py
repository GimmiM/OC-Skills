#!/usr/bin/env python3
"""
Eval-smoke tests for openclaw-safe-update
Critical path tests only (4 tests)
Run: python3 scripts/eval-smoke.py
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent / "update-orchestrator.py"

def run_test(args, expected_exit=None):
    """Run a test case"""
    cmd = ["python3", str(SCRIPT_PATH)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        output = json.loads(result.stdout)
    except:
        output = {"raw": result.stdout, "error": "Invalid JSON"}
    
    success = result.returncode == expected_exit if expected_exit is not None else True
    
    return {
        "success": success,
        "exit_code": result.returncode,
        "output": output
    }

def test_check():
    """Test 1: Check returns version info"""
    print("Test 1: Check versions...")
    result = run_test(["--action", "check", "--json"], expected_exit=0)
    
    data = result["output"].get("data", {})
    has_versions = all(k in data for k in ["installed_version", "latest_available"])
    
    passed = result["success"] and has_versions
    print(f"  {'✅' if passed else '❌'} Version check")
    return passed

def test_backup():
    """Test 2: Backup creates archive"""
    print("Test 2: Create backup...")
    result = run_test(["--action", "backup", "--json"], expected_exit=0)
    
    data = result["output"].get("data", {})
    has_path = "backup_path" in data
    
    passed = result["success"] and has_path
    print(f"  {'✅' if passed else '❌'} Backup created")
    return passed

def test_update_requires_confirmation():
    """Test 3: Update without confirmation fails"""
    print("Test 3: Update requires confirmation...")
    result = run_test(["--action", "update", "--json"], expected_exit=5)
    
    is_needs_confirm = result["output"].get("status") == "needs_confirmation"
    
    passed = result["success"] and is_needs_confirm
    print(f"  {'✅' if passed else '❌'} Confirmation required")
    return passed

def test_verify():
    """Test 4: Verify checks system state"""
    print("Test 4: Verify system...")
    result = run_test(["--action", "verify", "--json"], expected_exit=0)
    
    data = result["output"].get("data", {})
    has_checks = "checks" in data and len(data["checks"]) > 0
    
    passed = result["success"] and has_checks
    print(f"  {'✅' if passed else '❌'} System verified")
    return passed

def main():
    print("=" * 40)
    print("OpenClaw Safe Update - Smoke Tests")
    print("=" * 40)
    print()
    
    tests = [test_check, test_backup, test_update_requires_confirmation, test_verify]
    results = []
    
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 40)
    print(f"Results: {passed}/{total} passed")
    print("=" * 40)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
