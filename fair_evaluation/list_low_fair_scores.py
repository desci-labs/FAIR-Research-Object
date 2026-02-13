#!/usr/bin/env python3
"""
List all dPIDs with FAIR score below a threshold from evaluation results.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def extract_low_scores(results_file: Path, threshold: float = 80.0) -> list:
    """Extract dPIDs with scores below threshold."""
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    low_score_dpids = []
    
    for r in results:
        if r.get('skipped', False):
            continue
        
        # Support both 'score' and 'overall_score' keys
        score = r.get('overall_score') or r.get('score')
        if score is not None and score < threshold:
            low_score_dpids.append({
                'dpid': r.get('dpid'),
                'score': score,
                'duration': r.get('duration_seconds', 0)
            })
    
    # Sort by score ascending
    low_score_dpids.sort(key=lambda x: x['score'])
    
    return low_score_dpids


def main():
    parser = argparse.ArgumentParser(description="List dPIDs with low FAIR scores")
    parser.add_argument("--results", type=str, required=True, help="Path to evaluation results JSON")
    parser.add_argument("--threshold", type=float, default=80.0, help="Score threshold (default: 80)")
    parser.add_argument("--output", type=str, help="Output file path")
    
    args = parser.parse_args()
    
    results_file = Path(args.results)
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        return 1
    
    low_scores = extract_low_scores(results_file, args.threshold)
    
    # Generate report
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(f"dPIDs with FAIR Score < {args.threshold}%")
    report_lines.append(f"Source: {results_file}")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append("=" * 60)
    report_lines.append("")
    report_lines.append(f"Total dPIDs below threshold: {len(low_scores)}")
    report_lines.append("")
    report_lines.append("-" * 40)
    report_lines.append(f"{'dPID':>6s}  {'Score':>7s}  Notes")
    report_lines.append("-" * 40)
    
    for item in low_scores:
        dpid = item['dpid']
        score = item['score']
        report_lines.append(f"{dpid:>6d}  {score:>6.1f}%")
    
    report_lines.append("-" * 40)
    
    # Statistics
    if low_scores:
        scores = [x['score'] for x in low_scores]
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        report_lines.append(f"\nStatistics for low-scoring dPIDs:")
        report_lines.append(f"  Average: {avg_score:.1f}%")
        report_lines.append(f"  Min: {min_score:.1f}%")
        report_lines.append(f"  Max: {max_score:.1f}%")
    
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save output
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save both text and JSON
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"\nText report saved to: {output_file}")
        
        # Save JSON version
        json_file = output_file.with_suffix('.json')
        with open(json_file, 'w') as f:
            json.dump({
                "threshold": args.threshold,
                "source": str(results_file),
                "generated": datetime.now().isoformat(),
                "count": len(low_scores),
                "dpids": low_scores,
                "dpid_list": [x['dpid'] for x in low_scores]
            }, f, indent=2)
        print(f"JSON data saved to: {json_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())

