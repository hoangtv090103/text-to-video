#!/usr/bin/env python3
"""
Test Suite Runner for Text-to-Video Service

This script runs all test suites and generates comprehensive reports.
"""
import os
import sys
import subprocess
from datetime import datetime


def print_banner(text):
    """Print a formatted banner."""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def run_test_suite(test_file, description):
    """Run a specific test suite."""
    print_banner(description)
    
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_file,
        "-v",
        "-s",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner."""
    print_banner("TEXT-TO-VIDEO SERVICE - COMPREHENSIVE TESTING SUITE")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Change to tests directory
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(tests_dir)
    
    # Ensure reports directory exists
    reports_dir = os.path.join(tests_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    results = []
    
    # Run each test suite
    test_suites = [
        ("test_performance.py::test_generate_performance_report", "Performance Testing Suite"),
        ("test_reliability.py::test_generate_reliability_report", "Reliability Testing Suite"),
        ("test_resources.py::test_generate_resources_report", "Resource Usage Testing Suite")
    ]
    
    for test_file, description in test_suites:
        success = run_test_suite(test_file, description)
        results.append((description, success))
    
    # Print summary
    print_banner("TEST EXECUTION SUMMARY")
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {description}: {status}")
    
    # Check for generated reports
    print("\n" + "-"*80)
    print("Generated Reports:")
    print("-"*80)
    
    report_files = [
        "performance_report.md",
        "reliability_report.md",
        "resources_report.md"
    ]
    
    for report_file in report_files:
        report_path = os.path.join(reports_dir, report_file)
        if os.path.exists(report_path):
            size = os.path.getsize(report_path) / 1024  # KB
            print(f"  ✓ {report_file} ({size:.1f} KB)")
        else:
            print(f"  ✗ {report_file} (not generated)")
    
    print("\n" + "="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Exit with appropriate code
    all_passed = all(success for _, success in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
