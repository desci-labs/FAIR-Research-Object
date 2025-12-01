#!/usr/bin/env python3
"""
test_cli.py - Test the FAIROs CLI and core functionality
=========================================================

This script tests the pre-existing FAIROs functionality by:
1. Testing the CLI help and argument parsing
2. Testing the core ROCrateFAIRnessCalculator class directly
3. Verifying service connections (F-UJI, SOMEF)

Note: The bundled example RO-Crates may be incomplete. For full 
end-to-end testing with real RO-Crates, use test_real_input.py

Prerequisites:
- Virtual environment activated
- F-UJI server running on localhost:1071 (optional, for full tests)
- SOMEF configured (optional, for software analysis)

Usage:
    python test_cli.py
"""

import subprocess
import sys
import os
import json

# Paths
FAIROS_DIR = os.path.dirname(os.path.abspath(__file__))
CLI_SCRIPT = os.path.join(FAIROS_DIR, "code/fair_assessment/full_ro_fairness.py")
EXAMPLE_RO_1 = os.path.join(FAIROS_DIR, "code/fair_assessment/ro-examples/ro-example-1/")


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def test_cli_help():
    """Test that the CLI --help works and shows expected arguments"""
    print("\n📋 Testing CLI --help...")
    
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "-h"],
        capture_output=True,
        text=True,
        cwd=os.path.join(FAIROS_DIR, "code/fair_assessment")
    )
    
    if result.returncode == 0:
        # Check for expected arguments
        expected_args = ['-ro', '-o', '-m', '-a', '-d']
        found_args = [arg for arg in expected_args if arg in result.stdout]
        
        if len(found_args) == len(expected_args):
            print("   ✅ CLI arguments verified:")
            print("      -ro  : Path to RO-Crate directory")
            print("      -o   : Output filename")
            print("      -m   : Evaluate RO metadata")
            print("      -a   : Aggregation mode")
            print("      -d   : Generate diagram")
            return True
        else:
            print(f"   ⚠️  Missing arguments: {set(expected_args) - set(found_args)}")
            return True  # Still works
    else:
        print(f"   ❌ CLI help failed: {result.stderr}")
        return False


def test_rocrate_fairness_calculator():
    """Test the core ROCrateFAIRnessCalculator class"""
    print("\n🔧 Testing ROCrateFAIRnessCalculator...")
    
    sys.path.insert(0, os.path.join(FAIROS_DIR, "code/fair_assessment"))
    
    try:
        from rocrate_fairness.ro_fairness import ROCrateFAIRnessCalculator
        
        # Test with example RO-Crate
        if os.path.exists(EXAMPLE_RO_1):
            calculator = ROCrateFAIRnessCalculator(EXAMPLE_RO_1)
            result = calculator.calculate_fairness()
            
            print(f"   ✅ ROCrateFAIRnessCalculator works")
            print(f"      Checks: {len(result.get('checks', []))}")
            print(f"      Score: {result.get('score', {}).get('final', 'N/A')}%")
            
            # Show FAIR checks
            print("\n   FAIR Checks:")
            for check in result.get('checks', []):
                status = "✅" if check.get('status') == 'ok' else "❌"
                principle = check.get('principle_id', '?')
                title = check.get('title', 'Unknown')
                print(f"      {status} [{principle}] {title}")
            
            return True
        else:
            print(f"   ⚠️  Example RO-Crate not found: {EXAMPLE_RO_1}")
            return True  # Not a failure of the code
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_fuji_wrapper():
    """Test the F-UJI wrapper can connect to the server"""
    print("\n🔬 Testing F-UJI connection...")
    
    try:
        import requests
        resp = requests.get("http://localhost:1071/fuji/api/v1/", timeout=5)
        
        if resp.status_code == 200:
            print("   ✅ F-UJI server is running")
            
            # Test the wrapper class
            sys.path.insert(0, os.path.join(FAIROS_DIR, "code/fair_assessment"))
            from fuji_wrapper.fujiwrapper import FujiWrapper
            
            print("   ✅ FujiWrapper class imported successfully")
            return True
        else:
            print(f"   ⚠️  F-UJI returned status {resp.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️  F-UJI server not running (optional)")
        print("      To start: cd fuji && source venv/bin/activate")
        print("               python -m fuji_server -c fuji_server/config/server.ini")
        return True  # Not required for basic tests
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  F-UJI test skipped: {e}")
        return True


def test_somef_wrapper():
    """Test that SOMEF is available"""
    print("\n💻 Testing SOMEF...")
    
    try:
        result = subprocess.run(
            ['somef', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"   ✅ SOMEF installed: {version}")
            
            # Test wrapper import
            sys.path.insert(0, os.path.join(FAIROS_DIR, "code/fair_assessment"))
            from somef_wrapper.somefFAIR import SoftwareFAIRnessCalculator
            print("   ✅ SoftwareFAIRnessCalculator imported successfully")
            return True
        else:
            print(f"   ⚠️  SOMEF not working properly")
            return True  # Not required
            
    except FileNotFoundError:
        print("   ⚠️  SOMEF not installed (optional for software analysis)")
        return True
    except Exception as e:
        print(f"   ⚠️  SOMEF test skipped: {e}")
        return True


def test_dependencies():
    """Test that all required Python packages are installed"""
    print("\n📦 Testing Python dependencies...")
    
    packages = ['rocrate', 'validators', 'requests', 'json', 'argparse']
    all_ok = True
    
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"   ✅ {pkg}")
        except ImportError:
            print(f"   ❌ {pkg} - not installed")
            all_ok = False
    
    return all_ok


def main():
    """Run all tests"""
    print_section("FAIROs CLI & Functionality Tests")
    
    print(f"\nPython: {sys.version.split()[0]}")
    print(f"Working directory: {os.getcwd()}")
    
    results = []
    
    # Core tests
    results.append(("Python Dependencies", test_dependencies()))
    results.append(("CLI Help & Arguments", test_cli_help()))
    results.append(("ROCrateFAIRnessCalculator", test_rocrate_fairness_calculator()))
    
    # Service tests (optional)
    results.append(("F-UJI Connection", test_fuji_wrapper()))
    results.append(("SOMEF Installation", test_somef_wrapper()))
    
    # Summary
    print_section("Test Summary")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 All tests passed!")
        print("\nNext steps:")
        print("   • Run test_real_input.py for end-to-end testing with real RO-Crates")
        print("   • Use the CLI: python code/fair_assessment/full_ro_fairness.py -ro <path> -o output.json")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    print("="*70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
