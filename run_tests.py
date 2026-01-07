#!/usr/bin/env python
"""
Test runner script for Bloomberg Data Crawler.

Runs all tests and provides a summary of results.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[int, str]:
    """
    Run a command and return the exit code and output.

    Args:
        cmd: Command to run as list
        description: Description of the command

    Returns:
        Tuple of (exit_code, output)
    """
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"{'=' * 80}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode, result.stdout

    except Exception as e:
        print(f"Error running command: {e}")
        return 1, str(e)


def main():
    """Run test suite and display results."""
    print("\n" + "=" * 80)
    print(" Bloomberg Data Crawler - Test Suite Runner")
    print("=" * 80)

    # Test configurations
    test_configs = [
        {
            "name": "Quick Test - Cost Tracker",
            "cmd": ["python", "-m", "pytest", "tests/test_cost_tracker.py", "-v", "--tb=short"],
            "required": True
        },
        {
            "name": "Quick Test - Cache Manager",
            "cmd": ["python", "-m", "pytest", "tests/test_cache_manager.py", "-v", "--tb=short"],
            "required": True
        },
        {
            "name": "Quick Test - Bloomberg Parser",
            "cmd": ["python", "-m", "pytest", "tests/test_bloomberg_parser.py", "-v", "--tb=short"],
            "required": True
        },
        {
            "name": "Quick Test - Hybrid Source",
            "cmd": ["python", "-m", "pytest", "tests/test_hybrid_source.py", "-v", "--tb=short"],
            "required": True
        },
        {
            "name": "All Tests with Coverage",
            "cmd": ["python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing", "-v"],
            "required": False
        }
    ]

    results = []
    failed = []

    for config in test_configs:
        exit_code, output = run_command(config["cmd"], config["name"])

        results.append({
            "name": config["name"],
            "passed": exit_code == 0,
            "required": config["required"]
        })

        if exit_code != 0:
            failed.append(config["name"])
            if config["required"]:
                print(f"\n❌ REQUIRED TEST FAILED: {config['name']}")

    # Print summary
    print("\n" + "=" * 80)
    print(" TEST SUMMARY")
    print("=" * 80 + "\n")

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for result in results:
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        required = "(REQUIRED)" if result["required"] else "(OPTIONAL)"
        print(f"{status:12} {required:12} {result['name']}")

    print(f"\n{'=' * 80}")
    print(f"Total: {passed_count}/{total_count} test suites passed")
    print(f"{'=' * 80}\n")

    if failed:
        print("❌ Failed test suites:")
        for name in failed:
            print(f"   - {name}")
        print()

    # Exit with error if required tests failed
    required_failed = [r for r in results if not r["passed"] and r["required"]]
    if required_failed:
        print("❌ CRITICAL: Required tests failed. Please fix before committing.")
        sys.exit(1)
    else:
        print("✅ SUCCESS: All required tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
