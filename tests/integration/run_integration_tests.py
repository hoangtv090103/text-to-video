#!/usr/bin/env python3
"""
Integration Test Runner - Runs all integration tests against real server.

IMPORTANT: All services must be running before executing these tests!
See README.md for setup instructions.
"""
import subprocess
import sys
import os
from datetime import datetime


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def run_test_suite(test_file, suite_name):
    """Run a single test suite."""
    print_header(f"{suite_name}")
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v", "-s",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    
    if result.returncode == 0:
        print(f"\n✓ {suite_name} completed successfully")
        return True
    else:
        print(f"\n✗ {suite_name} failed with exit code {result.returncode}")
        return False


def main():
    """Run all integration test suites."""
    print_header("TEXT-TO-VIDEO SERVICE - INTEGRATION TESTING SUITE")
    
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "="*80)
    print("  IMPORTANT: Verify All Services Are Running")
    print("="*80)
    print("\nRequired services:")
    print("  1. Text-to-Video Server (port 8000)")
    print("  2. TTS Service (port 4123)")
    print("  3. LLM Service (Ollama on port 11434 or OpenAI-compatible)")
    print("  4. Redis (port 6379)")
    print("\nSee README.md for setup instructions.")
    print("\nPress Ctrl+C to cancel if services are not running...")
    
    import time
    time.sleep(5)
    
    # Test suites to run
    test_suites = [
        ("test_integration_performance.py", "Performance Testing Suite"),
        ("test_integration_reliability.py", "Reliability Testing Suite"),
        ("test_integration_resources.py", "Resource Usage Testing Suite"),
    ]
    
    results = {}
    
    # Run each test suite
    for test_file, suite_name in test_suites:
        success = run_test_suite(test_file, suite_name)
        results[suite_name] = success
    
    # Print summary
    print_header("TEST EXECUTION SUMMARY")
    
    for suite_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {suite_name}: {status}")
    
    print("\n" + "-"*80)
    print("Generated Reports:")
    print("-"*80)
    
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    if os.path.exists(reports_dir):
        for filename in sorted(os.listdir(reports_dir)):
            if filename.endswith(".md"):
                print(f"  ✓ {filename}")
    else:
        print("  ✗ No reports generated")
    
    print("\n" + "="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Exit with error if any tests failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        sys.exit(1)
