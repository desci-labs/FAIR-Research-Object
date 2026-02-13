#!/usr/bin/env python3
"""
Analyze file content distribution across all dPIDs.
- Collects file tree for each dPID
- Saves individual dPID content info to separate files
- Generates overall file extension distribution
- Identifies dPIDs with only PDF files
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DpidContentInfo:
    dpid: int
    success: bool
    error: Optional[str] = None
    total_files: int = 0
    total_dirs: int = 0
    extensions: Dict[str, int] = None
    file_list: List[str] = None
    fetch_time: float = 0
    
    def __post_init__(self):
        if self.extensions is None:
            self.extensions = {}
        if self.file_list is None:
            self.file_list = []


def extract_files_from_tree(entry: dict, path_prefix: str = "") -> tuple[List[str], Dict[str, int], int, int]:
    """Recursively extract files and extensions from IPFS tree."""
    files = []
    extensions = defaultdict(int)
    file_count = 0
    dir_count = 0
    
    name = entry.get('name', '')
    current_path = f"{path_prefix}/{name}" if path_prefix else name
    
    if entry.get('type') == 'file':
        files.append(current_path)
        file_count = 1
        # Extract extension
        if '.' in name:
            ext = '.' + name.rsplit('.', 1)[1].lower()
        else:
            ext = '(no extension)'
        extensions[ext] = 1
    elif entry.get('type') == 'directory':
        dir_count = 1
    
    # Process children
    for child in entry.get('children', []):
        child_files, child_exts, child_fc, child_dc = extract_files_from_tree(child, current_path)
        files.extend(child_files)
        for ext, count in child_exts.items():
            extensions[ext] += count
        file_count += child_fc
        dir_count += child_dc
    
    return files, dict(extensions), file_count, dir_count


def fetch_dpid_content(dpid: int, base_url: str, timeout: int = 60) -> DpidContentInfo:
    """Fetch file tree for a single dPID."""
    start_time = time.time()
    result = DpidContentInfo(dpid=dpid, success=False)
    
    try:
        # Fetch full file tree
        url = f"{base_url}/api/v2/data/dpid/{dpid}?depth=full"
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 404:
            result.error = "dPID not found"
            result.fetch_time = time.time() - start_time
            return result
        
        response.raise_for_status()
        data = response.json()
        
        # Handle wrapped vs direct tree response
        tree = data.get('tree', data)
        
        # Extract file info
        files, extensions, file_count, dir_count = extract_files_from_tree(tree)
        
        result.success = True
        result.total_files = file_count
        result.total_dirs = dir_count
        result.extensions = extensions
        result.file_list = files
        
    except requests.exceptions.Timeout:
        result.error = f"Timeout after {timeout}s"
    except requests.exceptions.RequestException as e:
        result.error = f"Request failed: {str(e)[:100]}"
    except json.JSONDecodeError as e:
        result.error = f"Invalid JSON response: {str(e)[:50]}"
    except Exception as e:
        result.error = f"Unexpected error: {str(e)[:100]}"
    
    result.fetch_time = time.time() - start_time
    return result


def save_dpid_content(result: DpidContentInfo, output_dir: Path):
    """Save individual dPID content info to a file."""
    dpid_file = output_dir / f"dpid_{result.dpid:04d}.json"
    with open(dpid_file, 'w') as f:
        json.dump(asdict(result), f, indent=2)


def is_pdf_only(extensions: Dict[str, int]) -> bool:
    """Check if dPID contains only PDF files."""
    if not extensions:
        return False
    # Filter out directories and special entries
    file_extensions = {k: v for k, v in extensions.items() if k != '(no extension)'}
    return len(file_extensions) == 1 and '.pdf' in file_extensions


def analyze_all_dpids(
    base_url: str,
    start_dpid: int,
    end_dpid: int,
    output_dir: Path,
    workers: int = 5,
    timeout: int = 60
) -> tuple[Dict[str, int], List[int], List[DpidContentInfo]]:
    """Analyze all dPIDs and return aggregated results."""
    
    # Create output directory
    dpid_content_dir = output_dir / "dpid_content"
    dpid_content_dir.mkdir(parents=True, exist_ok=True)
    
    all_extensions = defaultdict(int)
    pdf_only_dpids = []
    all_results = []
    
    total_dpids = end_dpid - start_dpid + 1
    completed = 0
    successful = 0
    failed = 0
    
    print(f"\n{'='*60}")
    print(f"Analyzing dPIDs {start_dpid} to {end_dpid}")
    print(f"Base URL: {base_url}")
    print(f"Workers: {workers}, Timeout: {timeout}s")
    print(f"Output: {dpid_content_dir}")
    print(f"{'='*60}\n")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_dpid_content, dpid, base_url, timeout): dpid
            for dpid in range(start_dpid, end_dpid + 1)
        }
        
        for future in as_completed(futures):
            dpid = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                
                # Save individual dPID content
                save_dpid_content(result, dpid_content_dir)
                
                if result.success:
                    successful += 1
                    # Aggregate extensions
                    for ext, count in result.extensions.items():
                        all_extensions[ext] += count
                    
                    # Check for PDF-only
                    if is_pdf_only(result.extensions):
                        pdf_only_dpids.append(dpid)
                else:
                    failed += 1
                
                completed += 1
                
                # Progress update
                if completed % 50 == 0 or completed == total_dpids:
                    pct = (completed / total_dpids) * 100
                    print(f"Progress: {completed}/{total_dpids} ({pct:.1f}%) - Success: {successful}, Failed: {failed}")
                    
            except Exception as e:
                print(f"Error processing dPID {dpid}: {e}")
                failed += 1
                completed += 1
    
    return dict(all_extensions), sorted(pdf_only_dpids), all_results


def generate_report(
    all_extensions: Dict[str, int],
    pdf_only_dpids: List[int],
    all_results: List[DpidContentInfo],
    output_dir: Path
):
    """Generate summary report."""
    
    successful_results = [r for r in all_results if r.success]
    failed_results = [r for r in all_results if not r.success]
    
    # Sort extensions by count
    sorted_extensions = sorted(all_extensions.items(), key=lambda x: -x[1])
    
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("dPID FILE CONTENT ANALYSIS REPORT")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append("=" * 60)
    report_lines.append("")
    
    report_lines.append("## Summary")
    report_lines.append(f"- Total dPIDs analyzed: {len(all_results)}")
    report_lines.append(f"- Successful: {len(successful_results)}")
    report_lines.append(f"- Failed/Skipped: {len(failed_results)}")
    report_lines.append(f"- Total files found: {sum(r.total_files for r in successful_results)}")
    report_lines.append(f"- Total directories found: {sum(r.total_dirs for r in successful_results)}")
    report_lines.append(f"- Unique file extensions: {len(all_extensions)}")
    report_lines.append(f"- dPIDs with ONLY PDF files: {len(pdf_only_dpids)}")
    report_lines.append("")
    
    report_lines.append("## File Extension Distribution")
    report_lines.append("-" * 40)
    total_files = sum(all_extensions.values())
    for ext, count in sorted_extensions:
        pct = (count / total_files * 100) if total_files > 0 else 0
        report_lines.append(f"  {ext:20s}: {count:6d} ({pct:5.1f}%)")
    report_lines.append("-" * 40)
    report_lines.append(f"  {'TOTAL':20s}: {total_files:6d}")
    report_lines.append("")
    
    report_lines.append("## PDF-Only dPIDs")
    report_lines.append(f"Count: {len(pdf_only_dpids)}")
    if pdf_only_dpids:
        # Show first 50
        shown = pdf_only_dpids[:50]
        report_lines.append(f"dPIDs: {', '.join(map(str, shown))}")
        if len(pdf_only_dpids) > 50:
            report_lines.append(f"  ... and {len(pdf_only_dpids) - 50} more")
    report_lines.append("")
    
    # Failed dPIDs
    if failed_results:
        report_lines.append("## Failed/Skipped dPIDs")
        for r in failed_results[:20]:
            report_lines.append(f"  dPID {r.dpid}: {r.error}")
        if len(failed_results) > 20:
            report_lines.append(f"  ... and {len(failed_results) - 20} more")
    
    report_text = "\n".join(report_lines)
    
    # Save report
    report_file = output_dir / "content_analysis_report.txt"
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print("\n" + report_text)
    print(f"\nReport saved to: {report_file}")
    
    # Save extension distribution as JSON
    ext_file = output_dir / "extension_distribution.json"
    with open(ext_file, 'w') as f:
        json.dump({
            "extensions": dict(sorted_extensions),
            "total_files": total_files,
            "unique_extensions": len(all_extensions)
        }, f, indent=2)
    print(f"Extension distribution saved to: {ext_file}")
    
    # Save PDF-only list
    pdf_file = output_dir / "pdf_only_dpids.json"
    with open(pdf_file, 'w') as f:
        json.dump({
            "count": len(pdf_only_dpids),
            "dpids": pdf_only_dpids
        }, f, indent=2)
    print(f"PDF-only list saved to: {pdf_file}")
    
    # Save summary JSON
    summary_file = output_dir / "content_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "analysis_time": datetime.now().isoformat(),
            "total_dpids": len(all_results),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "total_files": sum(r.total_files for r in successful_results),
            "total_directories": sum(r.total_dirs for r in successful_results),
            "unique_extensions": len(all_extensions),
            "pdf_only_count": len(pdf_only_dpids),
            "pdf_only_dpids": pdf_only_dpids,
            "extension_distribution": dict(sorted_extensions),
            "failed_dpids": [{"dpid": r.dpid, "error": r.error} for r in failed_results]
        }, f, indent=2)
    print(f"Summary JSON saved to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description="Analyze file content distribution across dPIDs")
    parser.add_argument("--base-url", default="https://beta.dpid.org", help="Base URL for resolver")
    parser.add_argument("--start-dpid", type=int, default=1, help="Starting dPID")
    parser.add_argument("--end-dpid", type=int, default=834, help="Ending dPID")
    parser.add_argument("--output", type=str, default="./results/content_analysis", help="Output directory")
    parser.add_argument("--workers", type=int, default=5, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_extensions, pdf_only_dpids, all_results = analyze_all_dpids(
        base_url=args.base_url,
        start_dpid=args.start_dpid,
        end_dpid=args.end_dpid,
        output_dir=output_dir,
        workers=args.workers,
        timeout=args.timeout
    )
    
    generate_report(all_extensions, pdf_only_dpids, all_results, output_dir)


if __name__ == "__main__":
    main()

