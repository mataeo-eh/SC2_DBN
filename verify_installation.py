#!/usr/bin/env python3
"""
Installation Verification Script

This script verifies that the SC2 Replay Ground Truth Extraction Pipeline
is properly installed and configured.

Usage:
    python verify_installation.py
"""

import sys
from pathlib import Path


def print_header(text):
    """Print a section header."""
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)
    print()


def print_check(name, status, details=""):
    """Print a check result."""
    symbol = "✓" if status else "✗"
    print(f"{symbol} {name}")
    if details:
        for line in details.split('\n'):
            if line.strip():
                print(f"  {line}")


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    required = (3, 9)

    status = version >= required
    details = f"Python {version.major}.{version.minor}.{version.micro}"

    if not status:
        details += f"\nRequired: Python {required[0]}.{required[1]}+"

    return status, details


def check_dependencies():
    """Check required packages."""
    packages = {
        'pandas': '2.0.0',
        'pyarrow': '12.0.0',
        'numpy': '1.24.0',
        'pysc2': '4.0.0'
    }

    all_ok = True
    results = []

    for package, min_version in packages.items():
        try:
            mod = __import__(package)
            version = getattr(mod, '__version__', 'unknown')
            results.append((package, True, f"{package} {version}"))
        except ImportError:
            results.append((package, False, f"{package} not installed\nInstall: pip install {package}"))
            all_ok = False

    return all_ok, results


def check_sc2_installation():
    """Check SC2 installation."""
    try:
        from pysc2.run_configs import get

        run_config = get()
        exec_path = run_config.exec_path
        return True, f"SC2 found at:\n{exec_path}"
    except Exception as e:
        return False, f"SC2 not found: {e}\nInstall from: https://starcraft2.com/"


def check_pipeline_structure():
    """Check pipeline files exist."""
    required_files = [
        'src_new/__init__.py',
        'src_new/extraction/state_extractor.py',
        'src_new/extraction/wide_table_builder.py',
        'src_new/extraction/schema_manager.py',
        'src_new/extraction/parquet_writer.py',
        'src_new/pipeline/extraction_pipeline.py',
        'src_new/pipeline/parallel_processor.py',
        'src_new/utils/validation.py',
        'tests/conftest.py',
        'run_tests.py',
    ]

    missing = []
    found = []

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            found.append(file_path)
        else:
            missing.append(file_path)

    all_ok = len(missing) == 0

    details = f"Found: {len(found)}/{len(required_files)} files"
    if missing:
        details += "\nMissing files:"
        for file_path in missing[:5]:  # Show first 5
            details += f"\n  - {file_path}"
        if len(missing) > 5:
            details += f"\n  ... and {len(missing) - 5} more"

    return all_ok, details


def check_pipeline_imports():
    """Check pipeline can be imported."""
    try:
        # Add project root to path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))

        # Try importing main components
        from src_new.pipeline import process_replay_quick
        from src_new.extraction import StateExtractor, WideTableBuilder
        from src_new.utils import OutputValidator

        return True, "All pipeline modules import successfully"
    except ImportError as e:
        return False, f"Import error: {e}\nEnsure you're in the project root directory"


def check_tests():
    """Check if tests can run."""
    try:
        import pytest
        return True, "pytest available for testing"
    except ImportError:
        return False, "pytest not installed\nInstall: pip install pytest"


def run_quick_test():
    """Run a quick pipeline test."""
    try:
        from src_new.extraction import StateExtractor

        # Try to create extractor
        extractor = StateExtractor()

        # Check it has the right components
        assert hasattr(extractor, 'unit_extractor')
        assert hasattr(extractor, 'building_extractor')
        assert hasattr(extractor, 'economy_extractor')
        assert hasattr(extractor, 'upgrade_extractor')

        return True, "StateExtractor instantiates correctly"
    except Exception as e:
        return False, f"Quick test failed: {e}"


def main():
    """Run all verification checks."""
    print_header("SC2 Replay Extraction Pipeline - Installation Verification")

    # Check Python version
    print("Checking Python version...")
    status, details = check_python_version()
    print_check("Python version", status, details)

    # Track overall success
    all_checks_passed = status

    # Check dependencies
    print()
    print("Checking dependencies...")
    status, results = check_dependencies()
    for package, pkg_status, pkg_details in results:
        print_check(package, pkg_status, pkg_details)
    all_checks_passed = all_checks_passed and status

    # Check SC2
    print()
    print("Checking SC2 installation...")
    status, details = check_sc2_installation()
    print_check("StarCraft II", status, details)
    all_checks_passed = all_checks_passed and status

    # Check pipeline structure
    print()
    print("Checking pipeline structure...")
    status, details = check_pipeline_structure()
    print_check("Pipeline files", status, details)
    all_checks_passed = all_checks_passed and status

    # Check imports
    print()
    print("Checking pipeline imports...")
    status, details = check_pipeline_imports()
    print_check("Pipeline imports", status, details)
    all_checks_passed = all_checks_passed and status

    # Check tests
    print()
    print("Checking test infrastructure...")
    status, details = check_tests()
    print_check("Testing framework", status, details)
    # Don't require tests to pass overall check

    # Quick test
    print()
    print("Running quick test...")
    status, details = run_quick_test()
    print_check("Quick test", status, details)
    all_checks_passed = all_checks_passed and status

    # Summary
    print_header("Summary")

    if all_checks_passed:
        print("✓ ALL CHECKS PASSED - Installation is complete!")
        print()
        print("Your installation is ready to use.")
        print()
        print("Next steps:")
        print("  1. Run the quick start:")
        print("     python quickstart.py")
        print()
        print("  2. Run tests to verify everything works:")
        print("     python run_tests.py --fast")
        print()
        print("  3. Process your first replay:")
        print("     See docs/usage.md for examples")
        print()
        print("  4. Read the documentation:")
        print("     - README_SC2_PIPELINE.md - Project overview")
        print("     - docs/installation.md - Installation guide")
        print("     - docs/usage.md - Usage guide")
        print("     - docs/data_dictionary.md - Output schema")
        print()
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Please fix the issues above")
        print()
        print("Common solutions:")
        print()
        print("  1. Install missing dependencies:")
        print("     pip install -r requirements_extraction.txt")
        print()
        print("  2. Install pysc2:")
        print("     pip install pysc2")
        print()
        print("  3. Install StarCraft II:")
        print("     https://starcraft2.com/")
        print()
        print("  4. Set SC2 path (if installed in custom location):")
        print("     export SC2PATH='/path/to/StarCraft II'")
        print("     # Or on Windows:")
        print("     set SC2PATH=C:\\path\\to\\StarCraft II")
        print()
        print("For more help, see:")
        print("  - docs/installation.md - Detailed installation guide")
        print("  - docs/troubleshooting.md - Common issues and solutions")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
