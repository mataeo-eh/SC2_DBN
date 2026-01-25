#!/usr/bin/env python3
"""
Test runner script for SC2 Replay Extraction Pipeline.

This script provides convenient ways to run the test suite with different
configurations and generate coverage reports.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --fast       # Run only fast unit tests
    python run_tests.py --coverage   # Run with coverage report
    python run_tests.py --markers extraction  # Run specific marker
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_pytest(args_list):
    """Run pytest with given arguments."""
    cmd = ['pytest'] + args_list
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='Run SC2 Extraction Pipeline tests')

    parser.add_argument(
        '--fast',
        action='store_true',
        help='Run only fast unit tests (skip slow/integration tests)'
    )

    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )

    parser.add_argument(
        '--markers',
        type=str,
        help='Run tests with specific marker (unit, integration, slow, etc.)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Run specific test file'
    )

    parser.add_argument(
        '--parallel',
        '-n',
        type=int,
        metavar='NUM',
        help='Run tests in parallel with NUM workers (requires pytest-xdist)'
    )

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = []

    if args.verbose:
        pytest_args.append('-v')

    if args.fast:
        pytest_args.extend(['-m', 'not slow and not integration'])
        print("Running fast unit tests only...")

    if args.markers:
        pytest_args.extend(['-m', args.markers])
        print(f"Running tests with marker: {args.markers}")

    if args.file:
        pytest_args.append(args.file)
        print(f"Running specific file: {args.file}")

    if args.coverage:
        pytest_args.extend([
            '--cov=src_new',
            '--cov-report=html',
            '--cov-report=term',
            '--cov-report=xml'
        ])
        print("Coverage reporting enabled")

    if args.parallel:
        pytest_args.extend(['-n', str(args.parallel)])
        print(f"Running tests in parallel with {args.parallel} workers")

    # If no specific args, run all tests
    if not pytest_args:
        print("Running all tests...")

    # Add tests directory if not running specific file
    if not args.file:
        pytest_args.append('tests/')

    # Run tests
    return run_pytest(pytest_args)


if __name__ == '__main__':
    sys.exit(main())
