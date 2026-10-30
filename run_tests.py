#!/usr/bin/env python3
"""
Test Runner for Retention Analytics Platform.

Runs all test suites:
- Backend API tests (pytest)
- Frontend E2E tests (Playwright)
- Security tests
- Performance tests

Usage:
    python run_tests.py [--api] [--e2e] [--security] [--performance] [--all]
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestRunner:
    """Test runner for the retention-analytics-platform."""

    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_api_tests(self) -> dict:
        """Run API integration tests."""
        print("\n" + "=" * 60)
        print("Running API Integration Tests")
        print("=" * 60)

        start_time = time.time()
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                "apps/api/tests/",
                "-v",
                "--tb=short",
                "--tb=short",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        end_time = time.time()

        result_data = {
            "returncode": result.returncode,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:2000])

        return result_data

    def run_e2e_tests(self) -> dict:
        """Run E2E Playwright tests."""
        print("\n" + "=" * 60)
        print("Running E2E Tests")
        print("=" * 60)

        start_time = time.time()
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                "shared-canonical-services/shared/testing/playwright/tests/",
                "-v",
                "--tb=short",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        end_time = time.time()

        result_data = {
            "returncode": result.returncode,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:2000])

        return result_data

    def run_security_tests(self) -> dict:
        """Run security tests."""
        print("\n" + "=" * 60)
        print("Running Security Tests")
        print("=" * 60)

        start_time = time.time()
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                "apps/api/tests/integration/security/",
                "-v",
                "--tb=short",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        end_time = time.time()

        result_data = {
            "returncode": result.returncode,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:2000])

        return result_data

    def run_performance_tests(self) -> dict:
        """Run performance tests."""
        print("\n" + "=" * 60)
        print("Running Performance Tests")
        print("=" * 60)

        start_time = time.time()
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                "apps/api/tests/integration/performance/",
                "-v",
                "--tb=short",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        end_time = time.time()

        result_data = {
            "returncode": result.returncode,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:2000])

        return result_data

    def run_all(self) -> dict:
        """Run all test suites."""
        self.start_time = time.time()

        results = {}

        # Run API tests
        print("\n" + "#" * 60)
        print("# RETENTION ANALYTICS PLATFORM - TEST SUITE")
        print("#" * 60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        results["api_tests"] = self.run_api_tests()
        results["e2e_tests"] = self.run_e2e_tests()
        results["security_tests"] = self.run_security_tests()
        results["performance_tests"] = self.run_performance_tests()

        self.end_time = time.time()

        # Summary
        print("\n" + "#" * 60)
        print("# TEST SUMMARY")
        print("#" * 60)

        total_passed = sum(1 for r in results.values() if r["passed"])
        total_failed = len(results) - total_passed

        for name, result in results.items():
            status = "PASS" if result["passed"] else "FAIL"
            print(f"  {name}: {status} ({result['duration']:.2f}s)")

        print(f"\nTotal: {total_passed}/{len(results)} test suites passed")
        print(f"Total duration: {self.end_time - self.start_time:.2f}s")

        return {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_duration": self.end_time - self.start_time,
            "results": results,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Runner for Retention Analytics Platform")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests only")
    parser.add_argument("--security", action="store_true", help="Run security tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    runner = TestRunner()

    if args.api:
        results = {"api_tests": runner.run_api_tests()}
    elif args.e2e:
        results = {"e2e_tests": runner.run_e2e_tests()}
    elif args.security:
        results = {"security_tests": runner.run_security_tests()}
    elif args.performance:
        results = {"performance_tests": runner.run_performance_tests()}
    else:
        # Default: run all
        results = runner.run_all()

    # Exit with appropriate code
    all_passed = all(r["passed"] for r in results.values())
    exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()