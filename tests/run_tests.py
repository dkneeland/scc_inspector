#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Primary test runner - executes all test suites."""

import sys
import subprocess
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def run_test(script_name):
    """Run a test script and return pass/fail status."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"\n{'=' * 70}")
    print(f"Running {script_name}...")
    print("=" * 70)

    result = subprocess.run([sys.executable, script_path], capture_output=False)
    return result.returncode == 0


if __name__ == "__main__":
    tests = [
        "test_all.py",
        "test_buffer.py",
        "test_control_commands.py",
        "test_overflow.py",
    ]

    results = {}
    for test in tests:
        results[test] = run_test(test)

    print(f"\n{'=' * 70}")
    print("FINAL RESULTS")
    print("=" * 70)

    for test, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test}: {status}")

    all_passed = all(results.values())
    print("=" * 70)

    if all_passed:
        print("\n✓ All test suites passed!")
        sys.exit(0)
    else:
        print("\n✗ Some test suites failed!")
        sys.exit(1)
