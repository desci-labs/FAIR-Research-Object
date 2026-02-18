#!/usr/bin/env python3
"""
test_real_input.py - Test FAIROs with real RO-Crates from the web
=================================================================

This script tests FAIROs with real-world RO-Crates downloaded from:
- WorkflowHub (https://workflowhub.eu)
- Zenodo (https://zenodo.org)

It runs the full FAIROs assessment pipeline including:
- F-UJI for dataset/URL FAIR assessment
- SOMEF for software repository analysis
- Built-in RO-Crate validation

Prerequisites:
- F-UJI server running on localhost:1071
- SOMEF configured
- Network access to download RO-Crates

Usage:
    python test_real_input.py
"""

import subprocess
import sys
import os
import json
import shutil
import zipfile
import tempfile

# Paths
FAIROS_DIR = os.path.dirname(os.path.abspath(__file__))
CLI_SCRIPT = os.path.join(FAIROS_DIR, "code/fair_assessment/full_ro_fairness.py")
TEST_DIR = os.path.join(FAIROS_DIR, "test-ro-crates")

# Real RO-Crates to test from WorkflowHub
# See: https://workflowhub.eu/workflows
TEST_SOURCES = [
    {
        "name": "WorkflowHub - Galaxy Cheminformatics",
        "url": "https://workflowhub.eu/workflows/18/ro_crate?version=1",
        "type": "zip",
        "folder": "workflow-18"
    },
    {
        "name": "WorkflowHub - Mass Spectrometry",
        "url": "https://workflowhub.eu/workflows/57/ro_crate?version=1",
        "type": "zip", 
        "folder": "workflow-57"
    }
]


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def check_prerequisites():
    """Check that F-UJI and network are available"""
    print("\n🔍 Checking prerequisites...")
    
    # Check F-UJI
    try:
        import requests
        resp = requests.get("http://localhost:1071/fuji/api/v1/", timeout=5)
        print("   ✅ F-UJI server running")
        fuji_ok = True
    except:
        print("   ❌ F-UJI server not running")
        print("      Start it with: cd ../fuji && source venv/bin/activate && python -m fuji_server -c fuji_server/config/server.ini")
        fuji_ok = False
    
    # Check network
    try:
        import requests
        resp = requests.get("https://workflowhub.eu", timeout=10)
        print("   ✅ Network access OK")
        network_ok = True
    except:
        print("   ❌ Network access failed")
        network_ok = False
    
    return fuji_ok and network_ok


def download_rocrate(source):
    """Download an RO-Crate from the web"""
    import requests
    
    print(f"\n📥 Downloading: {source['name']}...")
    
    target_dir = os.path.join(TEST_DIR, source['folder'])
    
    # Skip if already downloaded
    if os.path.exists(os.path.join(target_dir, "ro-crate-metadata.json")):
        print(f"   ✅ Already downloaded: {target_dir}")
        return target_dir
    
    # Create test directory
    os.makedirs(TEST_DIR, exist_ok=True)
    
    try:
        # Download
        resp = requests.get(source['url'], timeout=60)
        resp.raise_for_status()
        
        if source['type'] == 'zip':
            # Save and extract zip
            zip_path = os.path.join(TEST_DIR, f"{source['folder']}.zip")
            with open(zip_path, 'wb') as f:
                f.write(resp.content)
            
            # Extract
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(target_dir)
            
            # Clean up zip
            os.remove(zip_path)
            
            print(f"   ✅ Downloaded and extracted to: {target_dir}")
        else:
            # JSON directly
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, "ro-crate-metadata.json"), 'w') as f:
                f.write(resp.text)
            print(f"   ✅ Downloaded to: {target_dir}")
        
        return target_dir
        
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return None


def run_fairos_assessment(ro_path, output_name):
    """Run FAIROs CLI on an RO-Crate"""
    print(f"\n🔬 Running FAIROs assessment...")
    print(f"   Input: {ro_path}")
    
    output_file = os.path.join(FAIROS_DIR, output_name)
    
    # Run CLI
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, 
         "-ro", ro_path, 
         "-o", output_file,
         "-m", "true"],  # Evaluate RO metadata
        capture_output=True,
        text=True,
        cwd=os.path.join(FAIROS_DIR, "code/fair_assessment"),
        timeout=600  # 10 minute timeout
    )
    
    if result.returncode == 0 and os.path.exists(output_file):
        print(f"   ✅ Assessment completed")
        return output_file
    else:
        print(f"   ❌ Assessment failed")
        if result.stderr:
            # Show first few lines of error
            error_lines = result.stderr.split('\n')[:10]
            for line in error_lines:
                print(f"      {line}")
        return None


def display_results(output_file, source_name):
    """Display the assessment results"""
    print(f"\n📊 Results for: {source_name}")
    print("-" * 50)
    
    try:
        with open(output_file) as f:
            data = json.load(f)
        
        # Overall score
        if 'overall_score' in data:
            score = data['overall_score'].get('score', 'N/A')
            print(f"\n   🎯 Overall FAIR Score: {score}%")
        
        # Components
        print(f"\n   📦 Components Assessed: {len(data.get('components', []))}")
        
        for comp in data.get('components', []):
            comp_name = comp.get('name', 'Unknown')
            comp_type = comp.get('type', 'unknown')
            tools = ', '.join(comp.get('tool-used', []))
            
            print(f"\n   ┌─ {comp_name}")
            print(f"   │  Type: {comp_type}")
            print(f"   │  Tools: {tools}")
            
            # Count checks
            checks = comp.get('checks', [])
            passed = sum(1 for c in checks if c.get('status') in ['ok', 'pass'])
            print(f"   │  Checks: {passed}/{len(checks)} passed")
            
            # Show score breakdown if available
            if 'score' in comp:
                print(f"   │  Scores by category:")
                for cat, scores in comp['score'].items():
                    cat_score = scores.get('score', 0)
                    cat_total = scores.get('total_score', 0)
                    if cat_total > 0:
                        pct = (cat_score / cat_total) * 100
                        print(f"   │    {cat}: {pct:.0f}%")
            
            print(f"   └────────────────────────")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error reading results: {e}")
        return False


def test_rocrate(source):
    """Full test pipeline for one RO-Crate"""
    print_section(f"Testing: {source['name']}")
    
    # Download
    ro_path = download_rocrate(source)
    if not ro_path:
        return False
    
    # Find the actual ro-crate-metadata.json
    metadata_file = os.path.join(ro_path, "ro-crate-metadata.json")
    if not os.path.exists(metadata_file):
        # Check subdirectories
        for root, dirs, files in os.walk(ro_path):
            if "ro-crate-metadata.json" in files:
                ro_path = root
                break
    
    if not os.path.exists(os.path.join(ro_path, "ro-crate-metadata.json")):
        print(f"   ❌ ro-crate-metadata.json not found in {ro_path}")
        return False
    
    # Run assessment
    output_name = f"test_results_{source['folder']}.json"
    output_file = run_fairos_assessment(ro_path, output_name)
    
    if not output_file:
        return False
    
    # Display results
    success = display_results(output_file, source['name'])
    
    return success


def main():
    """Run tests on real RO-Crates"""
    print_section("FAIROs - Real World Input Tests")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please ensure F-UJI is running and network is available.")
        return 1
    
    results = []
    
    # Test each RO-Crate source
    for source in TEST_SOURCES:
        try:
            success = test_rocrate(source)
            results.append((source['name'], success))
        except Exception as e:
            print(f"\n❌ Error testing {source['name']}: {e}")
            results.append((source['name'], False))
    
    # Summary
    print_section("Test Summary")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} {name}")
        if not passed:
            all_passed = False
    
    # List output files
    print(f"\n📁 Output files saved in: {FAIROS_DIR}")
    for f in os.listdir(FAIROS_DIR):
        if f.startswith("test_results_") and f.endswith(".json"):
            print(f"   - {f}")
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 All real-world tests passed!")
    else:
        print("⚠️  Some tests failed. Check individual results above.")
    print("="*70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

