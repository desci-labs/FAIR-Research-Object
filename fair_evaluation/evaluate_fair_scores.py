#!/usr/bin/env python3
"""
FAIR Score Evaluation Script
============================

Evaluates FAIR scores for all dPIDs in a given environment (dev/prod).
Supports parallel processing and graceful error handling.

Usage:
    python evaluate_fair_scores.py --env dev --state before --workers 5
    python evaluate_fair_scores.py --env prod --state after --timeout 120
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import requests

# Configuration
ENVIRONMENTS = {
    "local": "http://localhost:5460",
    "dev": "https://dev.dpid.org",
    "prod": "https://beta.dpid.org",
}

# Git commits for before/after states
GIT_COMMITS = {
    "before": {
        "nodes": "6a9b66370a046f257b987e24f9916d973cb536ed",
        "dpid-resolver": "1710783ea6e8b20699c01cc84c0e9eed58692790",
        "fuji": "18b213b",  # Before dPID/IPFS recognition
    },
    "after": {
        "nodes": "HEAD",  # Latest with FAIR optimizations
        "dpid-resolver": "HEAD",  # Latest with FAIR enhancements
        "fuji": "ee97605",  # With dPID/IPFS recognition
    },
}

# F-UJI server URL and credentials
FUJI_URL = "http://localhost:1071/fuji/api/v1/evaluate"
FUJI_AUTH = ("marvel", "wonderwoman")  # Default F-UJI credentials


@dataclass
class DpidResult:
    """Result of a single dPID assessment"""
    dpid: int
    overall_score: Optional[float] = None
    findable: Optional[float] = None
    accessible: Optional[float] = None
    interoperable: Optional[float] = None
    reusable: Optional[float] = None
    checks_passed: int = 0
    checks_total: int = 0
    error: Optional[str] = None
    skipped: bool = False
    duration_seconds: float = 0.0


def check_fuji_server() -> bool:
    """Check if F-UJI server is running"""
    try:
        resp = requests.get("http://localhost:1071/fuji/api/v1/", timeout=5)
        return resp.status_code in [200, 404]
    except Exception:
        return False


def get_total_dpids(base_url: str, timeout: int = 30) -> int:
    """Get total number of dPIDs from the resolver"""
    try:
        url = f"{base_url}/api/v2/query/dpids?page=1&size=1"
        resp = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        return data.get("pagination", {}).get("total", 0)
    except Exception as e:
        print(f"⚠️  Failed to get total dPIDs: {e}")
        return 0


def _fuji_request(assess_url: str, timeout: int) -> dict:
    """Make F-UJI request - separated for timeout wrapper"""
    payload = {
        "object_identifier": assess_url,
        "test_debug": False,
        "use_datacite": True,
    }
    
    resp = requests.post(
        FUJI_URL,
        json=payload,
        timeout=timeout,
        headers={"Content-Type": "application/json"},
        auth=FUJI_AUTH
    )
    resp.raise_for_status()
    return resp.json()


def assess_dpid_with_fuji(dpid: int, base_url: str, timeout: int = 60) -> DpidResult:
    """Assess a single dPID using F-UJI"""
    start_time = time.time()
    result = DpidResult(dpid=dpid)
    
    try:
        # Build the URL to assess
        assess_url = f"{base_url}/{dpid}"
        
        # Use ThreadPoolExecutor to enforce hard timeout on F-UJI request
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fuji_request, assess_url, timeout)
            try:
                data = future.result(timeout=timeout)
            except FuturesTimeoutError:
                raise TimeoutError(f"F-UJI assessment timed out after {timeout}s")
        
        # Extract scores from F-UJI response
        summary = data.get("summary", {})
        result.overall_score = summary.get("score_percent", {}).get("FAIR", 0)
        result.findable = summary.get("score_percent", {}).get("F", 0)
        result.accessible = summary.get("score_percent", {}).get("A", 0)
        result.interoperable = summary.get("score_percent", {}).get("I", 0)
        result.reusable = summary.get("score_percent", {}).get("R", 0)
        
        # Count checks
        results = data.get("results", [])
        result.checks_total = len(results)
        result.checks_passed = sum(
            1 for r in results 
            if r.get("test_status") == "pass"
        )
        
    except (requests.exceptions.Timeout, TimeoutError) as e:
        result.error = f"Timeout after {timeout}s"
        result.skipped = True
    except requests.exceptions.RequestException as e:
        result.error = f"Request failed: {str(e)[:50]}"
        result.skipped = True
    except Exception as e:
        result.error = f"Error: {str(e)[:50]}"
        result.skipped = True
    
    result.duration_seconds = time.time() - start_time
    return result


def assess_dpid_simple(dpid: int, base_url: str, timeout: int = 60) -> DpidResult:
    """
    Simple assessment without F-UJI - just check if dPID is accessible
    and extract basic metadata. Use this as a fallback.
    """
    start_time = time.time()
    result = DpidResult(dpid=dpid)
    
    try:
        url = f"{base_url}/{dpid}"
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"Accept": "application/json"},
            allow_redirects=True
        )
        resp.raise_for_status()
        
        # If we got here, dPID is accessible
        # This is a simple accessibility check, not full FAIR assessment
        result.overall_score = 50.0  # Placeholder - accessible but not fully assessed
        result.accessible = 100.0
        
    except requests.exceptions.Timeout:
        result.error = f"Timeout after {timeout}s"
        result.skipped = True
    except requests.exceptions.RequestException as e:
        result.error = f"Request failed: {str(e)}"
        result.skipped = True
    except Exception as e:
        result.error = f"Unexpected error: {str(e)}"
        result.skipped = True
    
    result.duration_seconds = time.time() - start_time
    return result


def evaluate_all_dpids(
    base_url: str,
    total_dpids: int,
    workers: int = 5,
    timeout: int = 60,
    start_dpid: int = 1,
    end_dpid: Optional[int] = None,
    use_fuji: bool = True,
    progress_callback=None
) -> Tuple[List[DpidResult], List[DpidResult]]:
    """
    Evaluate all dPIDs in parallel.
    
    Returns:
        Tuple of (successful_results, skipped_results)
    """
    if end_dpid is None:
        end_dpid = total_dpids
    
    dpids_to_assess = list(range(start_dpid, end_dpid + 1))
    total = len(dpids_to_assess)
    
    successful = []
    skipped = []
    completed = 0
    
    assess_func = assess_dpid_with_fuji if use_fuji else assess_dpid_simple
    
    print(f"\n📊 Starting evaluation of {total} dPIDs (workers={workers}, timeout={timeout}s)")
    print(f"   Using: {'F-UJI' if use_fuji else 'Simple accessibility check'}")
    print(f"   Range: dPID {start_dpid} to {end_dpid}")
    print("-" * 60)
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_dpid = {
            executor.submit(assess_func, dpid, base_url, timeout): dpid
            for dpid in dpids_to_assess
        }
        
        # Process as they complete
        for future in as_completed(future_to_dpid):
            dpid = future_to_dpid[future]
            completed += 1
            
            try:
                result = future.result()
                
                if result.skipped:
                    skipped.append(result)
                    status = f"⏭️  SKIP"
                    score_str = f"Error: {result.error[:40]}..." if result.error else "Unknown"
                else:
                    successful.append(result)
                    status = f"✅ OK"
                    score_str = f"Score: {result.overall_score:.1f}%"
                
                # Progress output
                pct = (completed / total) * 100
                print(f"[{completed:4d}/{total}] ({pct:5.1f}%) dPID {dpid:4d} {status} | {score_str} ({result.duration_seconds:.1f}s)")
                
                if progress_callback:
                    progress_callback(completed, total, result)
                    
            except Exception as e:
                print(f"[{completed:4d}/{total}] dPID {dpid} ❌ FAILED: {e}")
                skipped.append(DpidResult(dpid=dpid, error=str(e), skipped=True))
    
    return successful, skipped


def save_results(
    results: List[DpidResult],
    skipped: List[DpidResult],
    output_path: str,
    metadata: Dict[str, Any]
):
    """Save evaluation results to JSON file"""
    output = {
        "metadata": {
            **metadata,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_dpids": len(results) + len(skipped),
            "successful": len(results),
            "skipped": len(skipped),
        },
        "results": [asdict(r) for r in results],
        "skipped": [asdict(r) for r in skipped],
    }
    
    # Calculate summary statistics
    if results:
        scores = [r.overall_score for r in results if r.overall_score is not None]
        if scores:
            output["summary"] = {
                "mean_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "median_score": sorted(scores)[len(scores) // 2],
            }
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate FAIR scores for all dPIDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Evaluate dev environment with F-UJI
    python evaluate_fair_scores.py --env dev --state after

    # Evaluate prod with more workers
    python evaluate_fair_scores.py --env prod --workers 10

    # Test specific range
    python evaluate_fair_scores.py --env dev --start-dpid 1 --end-dpid 50
        """
    )
    
    parser.add_argument(
        "--env",
        choices=["local", "dev", "prod"],
        default="dev",
        help="Environment to evaluate (default: dev)"
    )
    parser.add_argument(
        "--state",
        choices=["before", "after"],
        default="after",
        help="State being evaluated (default: after)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: results/{env}_{state}.json)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout per dPID in seconds (default: 60)"
    )
    parser.add_argument(
        "--start-dpid",
        type=int,
        default=1,
        help="Start from this dPID number (default: 1)"
    )
    parser.add_argument(
        "--end-dpid",
        type=int,
        default=None,
        help="End at this dPID number (default: all)"
    )
    parser.add_argument(
        "--no-fuji",
        action="store_true",
        help="Skip F-UJI and just check accessibility"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Just print what would be done"
    )
    
    args = parser.parse_args()
    
    # Determine base URL
    base_url = ENVIRONMENTS.get(args.env)
    if not base_url:
        print(f"❌ Unknown environment: {args.env}")
        sys.exit(1)
    
    # Output path
    output_path = args.output or f"results/{args.env}_{args.state}.json"
    
    print("=" * 60)
    print("FAIR Score Evaluation")
    print("=" * 60)
    print(f"Environment: {args.env} ({base_url})")
    print(f"State: {args.state}")
    print(f"Output: {output_path}")
    print(f"Workers: {args.workers}")
    print(f"Timeout: {args.timeout}s")
    
    # Check F-UJI if needed
    use_fuji = not args.no_fuji
    if use_fuji:
        if check_fuji_server():
            print("F-UJI Server: ✅ Running")
        else:
            print("F-UJI Server: ❌ Not running")
            print("\nTo start F-UJI:")
            print("  cd fuji && source venv/bin/activate")
            print("  python -m fuji_server -c fuji_server/config/server.ini &")
            print("\nOr use --no-fuji for simple accessibility checks")
            sys.exit(1)
    
    # Get total dPIDs
    print("\n📡 Fetching dPID count...")
    total_dpids = get_total_dpids(base_url, timeout=30)
    
    if total_dpids == 0:
        print(f"❌ Could not get dPID count from {base_url}")
        print("   The server may be down or unreachable.")
        
        # Try to get from a sample request
        print("\n🔄 Trying alternative method...")
        try:
            # Try to access a known dPID
            test_resp = requests.get(f"{base_url}/46", timeout=10, allow_redirects=False)
            if test_resp.status_code in [200, 302, 308]:
                print("   Server is reachable, but couldn't get total count.")
                print("   Using manual range instead.")
                if args.end_dpid:
                    total_dpids = args.end_dpid
                else:
                    print("   Please specify --end-dpid to set the range.")
                    sys.exit(1)
        except Exception as e:
            print(f"   Alternative method failed: {e}")
            sys.exit(1)
    
    print(f"Total dPIDs: {total_dpids}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - would evaluate:")
        print(f"   dPIDs {args.start_dpid} to {args.end_dpid or total_dpids}")
        sys.exit(0)
    
    # Run evaluation
    start_time = time.time()
    successful, skipped = evaluate_all_dpids(
        base_url=base_url,
        total_dpids=total_dpids,
        workers=args.workers,
        timeout=args.timeout,
        start_dpid=args.start_dpid,
        end_dpid=args.end_dpid,
        use_fuji=use_fuji,
    )
    
    duration = time.time() - start_time
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total evaluated: {len(successful) + len(skipped)}")
    print(f"Successful: {len(successful)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    
    if successful:
        scores = [r.overall_score for r in successful if r.overall_score is not None]
        if scores:
            print(f"\nScore Statistics:")
            print(f"  Mean: {sum(scores)/len(scores):.1f}%")
            print(f"  Min: {min(scores):.1f}%")
            print(f"  Max: {max(scores):.1f}%")
            print(f"  Median: {sorted(scores)[len(scores)//2]:.1f}%")
    
    # Save results
    save_results(
        results=successful,
        skipped=skipped,
        output_path=output_path,
        metadata={
            "environment": args.env,
            "base_url": base_url,
            "state": args.state,
            "workers": args.workers,
            "timeout": args.timeout,
            "use_fuji": use_fuji,
            "duration_seconds": duration,
        }
    )
    
    print("\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()

