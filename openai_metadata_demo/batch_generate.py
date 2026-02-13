#!/usr/bin/env python3
"""
Batch metadata generation for multiple dPIDs.

Usage:
    python batch_generate.py --start 1 --end 10
    python batch_generate.py --dpids 46,500,1024
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

from generate_metadata import (
    fetch_dpid_jsonld,
    fetch_dpid_tree,
    parse_dpid_content,
    generate_metadata_with_openai,
    save_results,
    format_file_size
)


def main():
    parser = argparse.ArgumentParser(
        description='Batch generate metadata for multiple dPIDs'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--dpids',
        type=str,
        help='Comma-separated list of dPID numbers (e.g., 46,500,1024)'
    )
    group.add_argument(
        '--start',
        type=int,
        help='Start dPID number (use with --end)'
    )
    
    parser.add_argument(
        '--end',
        type=int,
        help='End dPID number (use with --start)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=os.environ.get('OPENAI_API_KEY'),
        help='OpenAI API key'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o-mini',
        help='OpenAI model to use'
    )
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://beta.dpid.org',
        help='Base URL for dPID resolver'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./batch_results',
        help='Output directory'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between API calls in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip dPIDs that already have results'
    )
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: OpenAI API key required")
        sys.exit(1)
    
    # Determine dPIDs to process
    if args.dpids:
        dpids = [int(d.strip()) for d in args.dpids.split(',')]
    else:
        if args.end is None:
            print("Error: --end required with --start")
            sys.exit(1)
        dpids = list(range(args.start, args.end + 1))
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"=" * 60)
    print(f"Batch Metadata Generation")
    print(f"=" * 60)
    print(f"dPIDs to process: {len(dpids)}")
    print(f"Model: {args.model}")
    print(f"Output: {output_dir}")
    print(f"=" * 60)
    
    # Track results
    results = {
        'started': datetime.utcnow().isoformat(),
        'model': args.model,
        'total': len(dpids),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'dpids': {}
    }
    
    for i, dpid in enumerate(dpids, 1):
        print(f"\n[{i}/{len(dpids)}] Processing dPID {dpid}...")
        
        # Check if already exists
        if args.skip_existing:
            metadata_file = output_dir / f"dpid_{dpid}_metadata.json"
            if metadata_file.exists():
                print(f"  ⏭️  Skipping (already exists)")
                results['skipped'] += 1
                results['dpids'][dpid] = {'status': 'skipped', 'reason': 'exists'}
                continue
        
        try:
            # Fetch data
            jsonld = fetch_dpid_jsonld(dpid, args.base_url)
            if not jsonld:
                print(f"  ❌ Failed to fetch JSON-LD")
                results['failed'] += 1
                results['dpids'][dpid] = {'status': 'failed', 'reason': 'jsonld_fetch'}
                continue
            
            tree = fetch_dpid_tree(dpid, args.base_url)
            if not tree:
                print(f"  ❌ Failed to fetch file tree")
                results['failed'] += 1
                results['dpids'][dpid] = {'status': 'failed', 'reason': 'tree_fetch'}
                continue
            
            # Parse content
            content = parse_dpid_content(dpid, jsonld, tree)
            print(f"  📁 {content.total_files} files ({format_file_size(content.total_size)})")
            
            # Generate metadata
            metadata = generate_metadata_with_openai(content, args.api_key, args.model)
            
            # Save results
            save_results(content, metadata, output_dir)
            
            print(f"  ✅ Success")
            results['success'] += 1
            results['dpids'][dpid] = {
                'status': 'success',
                'title': content.title,
                'files': content.total_files,
                'keywords': metadata.keywords[:5]
            }
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results['failed'] += 1
            results['dpids'][dpid] = {'status': 'failed', 'reason': str(e)[:100]}
        
        # Rate limiting
        if i < len(dpids):
            time.sleep(args.delay)
    
    # Save summary
    results['finished'] = datetime.utcnow().isoformat()
    summary_file = output_dir / 'batch_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n" + "=" * 60)
    print("BATCH COMPLETE")
    print(f"=" * 60)
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Skipped: {results['skipped']}")
    print(f"\nSummary saved to: {summary_file}")


if __name__ == '__main__':
    main()

