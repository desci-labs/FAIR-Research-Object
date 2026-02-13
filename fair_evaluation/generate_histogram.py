#!/usr/bin/env python3
"""
FAIR Score Histogram Generator
==============================

Generates comparison histograms for before/after FAIR score evaluations.

Usage:
    python generate_histogram.py --env dev
    python generate_histogram.py --before results/dev_before.json --after results/dev_after.json
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib not available. Install with: pip install matplotlib numpy")


def load_results(filepath: str) -> Dict[str, Any]:
    """Load evaluation results from JSON file"""
    with open(filepath, "r") as f:
        return json.load(f)


def extract_scores(data: Dict[str, Any]) -> List[float]:
    """Extract overall scores from results"""
    scores = []
    for result in data.get("results", []):
        score = result.get("overall_score")
        if score is not None:
            scores.append(score)
    return scores


def generate_histogram(
    before_scores: List[float],
    after_scores: List[float],
    output_path: str,
    title: str = "FAIR Score Distribution",
    env: str = ""
):
    """Generate side-by-side histogram comparison"""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ Cannot generate histogram - matplotlib not installed")
        return
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"{title} - {env.upper()}" if env else title, fontsize=16, fontweight='bold')
    
    # Color scheme
    before_color = '#e74c3c'  # Red
    after_color = '#27ae60'   # Green
    
    # Bins for histogram (0-100 in steps of 5)
    bins = np.arange(0, 105, 5)
    
    # Before histogram
    ax1 = axes[0]
    ax1.hist(before_scores, bins=bins, color=before_color, alpha=0.7, edgecolor='black', linewidth=0.5)
    ax1.set_xlabel('FAIR Score (%)', fontsize=12)
    ax1.set_ylabel('Number of dPIDs', fontsize=12)
    ax1.set_title('Before Optimization', fontsize=14)
    ax1.set_xlim(0, 100)
    ax1.grid(axis='y', alpha=0.3)
    
    # Add statistics text
    if before_scores:
        stats_text = f"n = {len(before_scores)}\nmean = {np.mean(before_scores):.1f}%\nmedian = {np.median(before_scores):.1f}%\nstd = {np.std(before_scores):.1f}%"
        ax1.text(0.95, 0.95, stats_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # After histogram
    ax2 = axes[1]
    ax2.hist(after_scores, bins=bins, color=after_color, alpha=0.7, edgecolor='black', linewidth=0.5)
    ax2.set_xlabel('FAIR Score (%)', fontsize=12)
    ax2.set_ylabel('Number of dPIDs', fontsize=12)
    ax2.set_title('After Optimization', fontsize=14)
    ax2.set_xlim(0, 100)
    ax2.grid(axis='y', alpha=0.3)
    
    # Add statistics text
    if after_scores:
        stats_text = f"n = {len(after_scores)}\nmean = {np.mean(after_scores):.1f}%\nmedian = {np.median(after_scores):.1f}%\nstd = {np.std(after_scores):.1f}%"
        ax2.text(0.95, 0.95, stats_text, transform=ax2.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"📊 Histogram saved to: {output_path}")
    
    # Also generate overlay comparison
    overlay_path = output_path.replace('.png', '_overlay.png')
    generate_overlay_histogram(before_scores, after_scores, overlay_path, title, env)


def generate_overlay_histogram(
    before_scores: List[float],
    after_scores: List[float],
    output_path: str,
    title: str = "FAIR Score Distribution",
    env: str = ""
):
    """Generate overlaid histogram comparison"""
    if not MATPLOTLIB_AVAILABLE:
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color scheme
    before_color = '#e74c3c'  # Red
    after_color = '#27ae60'   # Green
    
    bins = np.arange(0, 105, 5)
    
    # Plot both histograms with transparency
    ax.hist(before_scores, bins=bins, color=before_color, alpha=0.5, 
            edgecolor='darkred', linewidth=0.5, label='Before')
    ax.hist(after_scores, bins=bins, color=after_color, alpha=0.5, 
            edgecolor='darkgreen', linewidth=0.5, label='After')
    
    ax.set_xlabel('FAIR Score (%)', fontsize=12)
    ax.set_ylabel('Number of dPIDs', fontsize=12)
    ax.set_title(f"{title} - {env.upper()} (Overlay)" if env else f"{title} (Overlay)", 
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.grid(axis='y', alpha=0.3)
    ax.legend(loc='upper left')
    
    # Add improvement annotation
    if before_scores and after_scores:
        before_mean = np.mean(before_scores)
        after_mean = np.mean(after_scores)
        improvement = after_mean - before_mean
        improvement_text = f"Mean improvement: {improvement:+.1f}%\n({before_mean:.1f}% → {after_mean:.1f}%)"
        ax.text(0.95, 0.95, improvement_text, transform=ax.transAxes, fontsize=11,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"📊 Overlay histogram saved to: {output_path}")


def generate_category_comparison(
    before_data: Dict[str, Any],
    after_data: Dict[str, Any],
    output_path: str,
    env: str = ""
):
    """Generate bar chart comparing F, A, I, R category improvements"""
    if not MATPLOTLIB_AVAILABLE:
        return
    
    categories = ['Findable', 'Accessible', 'Interoperable', 'Reusable']
    category_keys = ['findable', 'accessible', 'interoperable', 'reusable']
    
    def get_category_means(data: Dict[str, Any]) -> List[float]:
        means = []
        for key in category_keys:
            scores = [r.get(key) for r in data.get("results", []) if r.get(key) is not None]
            means.append(np.mean(scores) if scores else 0)
        return means
    
    before_means = get_category_means(before_data)
    after_means = get_category_means(after_data)
    
    x = np.arange(len(categories))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, before_means, width, label='Before', color='#e74c3c', alpha=0.7)
    bars2 = ax.bar(x + width/2, after_means, width, label='After', color='#27ae60', alpha=0.7)
    
    ax.set_xlabel('FAIR Category', fontsize=12)
    ax.set_ylabel('Average Score (%)', fontsize=12)
    ax.set_title(f'FAIR Category Comparison - {env.upper()}' if env else 'FAIR Category Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
    
    add_labels(bars1)
    add_labels(bars2)
    
    plt.tight_layout()
    category_path = output_path.replace('.png', '_categories.png')
    plt.savefig(category_path, dpi=150, bbox_inches='tight')
    print(f"📊 Category comparison saved to: {category_path}")


def print_text_summary(before_data: Dict[str, Any], after_data: Dict[str, Any], env: str):
    """Print a text summary even without matplotlib"""
    print("\n" + "=" * 60)
    print(f"FAIR SCORE COMPARISON SUMMARY - {env.upper()}")
    print("=" * 60)
    
    before_scores = extract_scores(before_data)
    after_scores = extract_scores(after_data)
    
    print(f"\n{'Metric':<25} {'Before':>12} {'After':>12} {'Change':>12}")
    print("-" * 60)
    
    if before_scores:
        before_mean = sum(before_scores) / len(before_scores)
        before_median = sorted(before_scores)[len(before_scores) // 2]
        before_min = min(before_scores)
        before_max = max(before_scores)
    else:
        before_mean = before_median = before_min = before_max = 0
    
    if after_scores:
        after_mean = sum(after_scores) / len(after_scores)
        after_median = sorted(after_scores)[len(after_scores) // 2]
        after_min = min(after_scores)
        after_max = max(after_scores)
    else:
        after_mean = after_median = after_min = after_max = 0
    
    print(f"{'Count':<25} {len(before_scores):>12} {len(after_scores):>12} {len(after_scores) - len(before_scores):>+12}")
    print(f"{'Mean Score':<25} {before_mean:>11.1f}% {after_mean:>11.1f}% {after_mean - before_mean:>+11.1f}%")
    print(f"{'Median Score':<25} {before_median:>11.1f}% {after_median:>11.1f}% {after_median - before_median:>+11.1f}%")
    print(f"{'Min Score':<25} {before_min:>11.1f}% {after_min:>11.1f}% {after_min - before_min:>+11.1f}%")
    print(f"{'Max Score':<25} {before_max:>11.1f}% {after_max:>11.1f}% {after_max - before_max:>+11.1f}%")
    
    # Skipped counts
    before_skipped = len(before_data.get("skipped", []))
    after_skipped = len(after_data.get("skipped", []))
    print(f"{'Skipped/Errors':<25} {before_skipped:>12} {after_skipped:>12} {after_skipped - before_skipped:>+12}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate FAIR score comparison histograms",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default=None,
        help="Environment (uses default result paths)"
    )
    parser.add_argument(
        "--before",
        type=str,
        default=None,
        help="Path to before results JSON"
    )
    parser.add_argument(
        "--after",
        type=str,
        default=None,
        help="Path to after results JSON"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output image path"
    )
    
    args = parser.parse_args()
    
    # Determine file paths
    if args.env:
        before_path = args.before or f"results/{args.env}_before.json"
        after_path = args.after or f"results/{args.env}_after.json"
        output_path = args.output or f"fair_comparison_{args.env}.png"
        env = args.env
    elif args.before and args.after:
        before_path = args.before
        after_path = args.after
        output_path = args.output or "fair_comparison.png"
        env = ""
    else:
        print("❌ Must specify --env or both --before and --after")
        parser.print_help()
        return
    
    # Check files exist
    if not os.path.exists(before_path):
        print(f"❌ Before file not found: {before_path}")
        return
    if not os.path.exists(after_path):
        print(f"❌ After file not found: {after_path}")
        return
    
    print("=" * 60)
    print("FAIR Score Histogram Generator")
    print("=" * 60)
    print(f"Before: {before_path}")
    print(f"After: {after_path}")
    print(f"Output: {output_path}")
    
    # Load data
    before_data = load_results(before_path)
    after_data = load_results(after_path)
    
    before_scores = extract_scores(before_data)
    after_scores = extract_scores(after_data)
    
    print(f"\nLoaded {len(before_scores)} before scores, {len(after_scores)} after scores")
    
    # Print text summary (always works)
    print_text_summary(before_data, after_data, env)
    
    # Generate visualizations if matplotlib available
    if MATPLOTLIB_AVAILABLE:
        generate_histogram(before_scores, after_scores, output_path, 
                          "FAIR Score Distribution", env)
        generate_category_comparison(before_data, after_data, output_path, env)
        print("\n✅ All visualizations generated!")
    else:
        print("\n⚠️  Install matplotlib for visual histograms: pip install matplotlib numpy")


if __name__ == "__main__":
    main()

