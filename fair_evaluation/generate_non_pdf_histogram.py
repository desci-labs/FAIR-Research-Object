#!/usr/bin/env python3
"""
Generate FAIR score histogram and statistics for non-PDF-only dPIDs.
These are research objects with diverse file types (code, data, etc.)
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
RESULTS_DIR = Path("/Volumes/Kandoz/DeSci/FAIR-Research-Object/fair_evaluation/results")
CONTENT_DIR = RESULTS_DIR / "content_analysis"
OUTPUT_DIR = RESULTS_DIR

def load_data():
    """Load FAIR scores and PDF-only list."""
    # Load prod_after.json
    with open(RESULTS_DIR / "prod_after.json", "r") as f:
        data = json.load(f)
    
    # Handle both flat list and nested structure
    if isinstance(data, dict) and "results" in data:
        fair_results = data["results"]
    else:
        fair_results = data
    
    # Load PDF-only dPIDs list
    with open(CONTENT_DIR / "content_summary.json", "r") as f:
        content_summary = json.load(f)
    
    pdf_only_dpids = set(content_summary.get("pdf_only_dpids", []))
    
    return fair_results, pdf_only_dpids, content_summary

def filter_non_pdf_only(fair_results, pdf_only_dpids):
    """Filter to only non-PDF-only dPIDs."""
    non_pdf_only = []
    pdf_only = []
    
    for result in fair_results:
        dpid = result.get("dpid")
        # Handle both "score" and "overall_score" field names
        score = result.get("overall_score") or result.get("score")
        
        if score is None or result.get("skipped"):
            continue
        
        # Normalize result to have "score" field
        result_normalized = {**result, "score": score}
            
        if dpid in pdf_only_dpids:
            pdf_only.append(result_normalized)
        else:
            non_pdf_only.append(result_normalized)
    
    return non_pdf_only, pdf_only

def calculate_statistics(results, label):
    """Calculate comprehensive statistics."""
    scores = [r["score"] for r in results if r.get("score") is not None]
    
    if not scores:
        return None
    
    scores = np.array(scores)
    
    stats = {
        "label": label,
        "count": len(scores),
        "mean": float(np.mean(scores)),
        "median": float(np.median(scores)),
        "std": float(np.std(scores)),
        "min": float(np.min(scores)),
        "max": float(np.max(scores)),
        "q25": float(np.percentile(scores, 25)),
        "q75": float(np.percentile(scores, 75)),
        "above_80": int(np.sum(scores >= 80)),
        "above_90": int(np.sum(scores >= 90)),
        "below_80": int(np.sum(scores < 80)),
    }
    stats["pct_above_80"] = (stats["above_80"] / stats["count"]) * 100
    stats["pct_above_90"] = (stats["above_90"] / stats["count"]) * 100
    
    return stats

def generate_histogram(non_pdf_scores, pdf_only_scores, output_path):
    """Generate a beautiful comparison histogram."""
    # Set up the plot with a nice style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Color scheme
    colors = {
        'non_pdf': '#2E86AB',  # Deep blue
        'pdf_only': '#A23B72',  # Magenta
        'threshold': '#E94F37'  # Red for 80% line
    }
    
    # Histogram bins
    bins = np.arange(0, 105, 5)
    
    # Top plot: Non-PDF-only dPIDs (diverse research objects)
    ax1 = axes[0]
    non_pdf_vals = [r["score"] for r in non_pdf_scores if r.get("score")]
    ax1.hist(non_pdf_vals, bins=bins, color=colors['non_pdf'], edgecolor='white', 
             linewidth=0.5, alpha=0.85)
    ax1.axvline(x=80, color=colors['threshold'], linestyle='--', linewidth=2, 
                label='80% Threshold')
    ax1.set_title('Multi-File Research Objects (Code, Data, Analysis)', 
                  fontsize=14, fontweight='bold', pad=10)
    ax1.set_xlabel('FAIR Score (%)', fontsize=11)
    ax1.set_ylabel('Number of dPIDs', fontsize=11)
    ax1.legend(loc='upper left')
    ax1.set_xlim(0, 100)
    
    # Add statistics text box
    non_pdf_stats = calculate_statistics(non_pdf_scores, "Non-PDF")
    stats_text = (f"n = {non_pdf_stats['count']}\n"
                  f"Mean: {non_pdf_stats['mean']:.1f}%\n"
                  f"Median: {non_pdf_stats['median']:.1f}%\n"
                  f"≥80%: {non_pdf_stats['above_80']} ({non_pdf_stats['pct_above_80']:.1f}%)\n"
                  f"≥90%: {non_pdf_stats['above_90']} ({non_pdf_stats['pct_above_90']:.1f}%)")
    ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Bottom plot: PDF-only dPIDs (publications)
    ax2 = axes[1]
    pdf_only_vals = [r["score"] for r in pdf_only_scores if r.get("score")]
    ax2.hist(pdf_only_vals, bins=bins, color=colors['pdf_only'], edgecolor='white', 
             linewidth=0.5, alpha=0.85)
    ax2.axvline(x=80, color=colors['threshold'], linestyle='--', linewidth=2, 
                label='80% Threshold')
    ax2.set_title('PDF-Only Research Objects (Publications)', 
                  fontsize=14, fontweight='bold', pad=10)
    ax2.set_xlabel('FAIR Score (%)', fontsize=11)
    ax2.set_ylabel('Number of dPIDs', fontsize=11)
    ax2.legend(loc='upper left')
    ax2.set_xlim(0, 100)
    
    # Add statistics text box
    pdf_stats = calculate_statistics(pdf_only_scores, "PDF-Only")
    if pdf_stats:
        stats_text2 = (f"n = {pdf_stats['count']}\n"
                       f"Mean: {pdf_stats['mean']:.1f}%\n"
                       f"Median: {pdf_stats['median']:.1f}%\n"
                       f"≥80%: {pdf_stats['above_80']} ({pdf_stats['pct_above_80']:.1f}%)\n"
                       f"≥90%: {pdf_stats['above_90']} ({pdf_stats['pct_above_90']:.1f}%)")
        ax2.text(0.02, 0.95, stats_text2, transform=ax2.transAxes, fontsize=10,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Main title
    fig.suptitle('FAIR Score Distribution by Research Object Type\nDeSci Labs dPIDs After Optimization', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Saved histogram to: {output_path}")
    return non_pdf_stats, pdf_stats

def generate_combined_histogram(non_pdf_scores, pdf_only_scores, output_path):
    """Generate a single combined histogram with overlay."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 8))
    
    colors = {
        'non_pdf': '#2E86AB',
        'pdf_only': '#A23B72',
        'threshold': '#E94F37'
    }
    
    bins = np.arange(0, 105, 5)
    
    non_pdf_vals = [r["score"] for r in non_pdf_scores if r.get("score")]
    pdf_only_vals = [r["score"] for r in pdf_only_scores if r.get("score")]
    
    # Plot both histograms
    ax.hist(non_pdf_vals, bins=bins, color=colors['non_pdf'], edgecolor='white', 
            linewidth=0.5, alpha=0.7, label=f'Multi-File (n={len(non_pdf_vals)})')
    ax.hist(pdf_only_vals, bins=bins, color=colors['pdf_only'], edgecolor='white', 
            linewidth=0.5, alpha=0.7, label=f'PDF-Only (n={len(pdf_only_vals)})')
    
    ax.axvline(x=80, color=colors['threshold'], linestyle='--', linewidth=2.5, 
               label='80% Threshold')
    
    ax.set_title('FAIR Score Distribution: Multi-File vs PDF-Only Research Objects\nDeSci Labs dPIDs After Optimization', 
                 fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel('FAIR Score (%)', fontsize=13)
    ax.set_ylabel('Number of dPIDs', fontsize=13)
    ax.legend(loc='upper left', fontsize=11)
    ax.set_xlim(0, 100)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Saved combined histogram to: {output_path}")

def print_detailed_stats(non_pdf_stats, pdf_stats):
    """Print detailed statistics comparison."""
    print("\n" + "="*70)
    print("📊 FAIR SCORE STATISTICS BY RESEARCH OBJECT TYPE")
    print("="*70)
    
    print("\n🔬 MULTI-FILE RESEARCH OBJECTS (Code, Data, Analysis, etc.)")
    print("-"*50)
    print(f"  Total dPIDs:        {non_pdf_stats['count']}")
    print(f"  Mean Score:         {non_pdf_stats['mean']:.1f}%")
    print(f"  Median Score:       {non_pdf_stats['median']:.1f}%")
    print(f"  Std Deviation:      {non_pdf_stats['std']:.1f}%")
    print(f"  Min Score:          {non_pdf_stats['min']:.1f}%")
    print(f"  Max Score:          {non_pdf_stats['max']:.1f}%")
    print(f"  25th Percentile:    {non_pdf_stats['q25']:.1f}%")
    print(f"  75th Percentile:    {non_pdf_stats['q75']:.1f}%")
    print(f"  dPIDs ≥80%:         {non_pdf_stats['above_80']} ({non_pdf_stats['pct_above_80']:.1f}%)")
    print(f"  dPIDs ≥90%:         {non_pdf_stats['above_90']} ({non_pdf_stats['pct_above_90']:.1f}%)")
    print(f"  dPIDs <80%:         {non_pdf_stats['below_80']}")
    
    if pdf_stats:
        print("\n📄 PDF-ONLY RESEARCH OBJECTS (Publications)")
        print("-"*50)
        print(f"  Total dPIDs:        {pdf_stats['count']}")
        print(f"  Mean Score:         {pdf_stats['mean']:.1f}%")
        print(f"  Median Score:       {pdf_stats['median']:.1f}%")
        print(f"  Std Deviation:      {pdf_stats['std']:.1f}%")
        print(f"  Min Score:          {pdf_stats['min']:.1f}%")
        print(f"  Max Score:          {pdf_stats['max']:.1f}%")
        print(f"  25th Percentile:    {pdf_stats['q25']:.1f}%")
        print(f"  75th Percentile:    {pdf_stats['q75']:.1f}%")
        print(f"  dPIDs ≥80%:         {pdf_stats['above_80']} ({pdf_stats['pct_above_80']:.1f}%)")
        print(f"  dPIDs ≥90%:         {pdf_stats['above_90']} ({pdf_stats['pct_above_90']:.1f}%)")
        print(f"  dPIDs <80%:         {pdf_stats['below_80']}")
    
    print("\n" + "="*70)
    print("📈 COMPARISON SUMMARY")
    print("="*70)
    if pdf_stats:
        print(f"\n  Multi-File dPIDs have {'higher' if non_pdf_stats['mean'] > pdf_stats['mean'] else 'lower'} mean scores")
        print(f"    Multi-File Mean:  {non_pdf_stats['mean']:.1f}%")
        print(f"    PDF-Only Mean:    {pdf_stats['mean']:.1f}%")
        print(f"    Difference:       {non_pdf_stats['mean'] - pdf_stats['mean']:.1f}%")
    print("\n" + "="*70)

def save_stats_report(non_pdf_stats, pdf_stats, non_pdf_scores, output_path):
    """Save statistics to a text report."""
    with open(output_path, "w") as f:
        f.write("="*70 + "\n")
        f.write("FAIR SCORE ANALYSIS: NON-PDF-ONLY dPIDs\n")
        f.write("DeSci Labs Production Environment - After Optimization\n")
        f.write("="*70 + "\n\n")
        
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-"*50 + "\n")
        f.write(f"Multi-file research objects (containing code, data, analysis files)\n")
        f.write(f"demonstrate strong FAIR compliance with {non_pdf_stats['pct_above_80']:.1f}%\n")
        f.write(f"achieving scores ≥80%.\n\n")
        
        f.write("MULTI-FILE RESEARCH OBJECTS\n")
        f.write("-"*50 + "\n")
        f.write(f"Total dPIDs:        {non_pdf_stats['count']}\n")
        f.write(f"Mean Score:         {non_pdf_stats['mean']:.1f}%\n")
        f.write(f"Median Score:       {non_pdf_stats['median']:.1f}%\n")
        f.write(f"Std Deviation:      {non_pdf_stats['std']:.1f}%\n")
        f.write(f"Min Score:          {non_pdf_stats['min']:.1f}%\n")
        f.write(f"Max Score:          {non_pdf_stats['max']:.1f}%\n")
        f.write(f"25th Percentile:    {non_pdf_stats['q25']:.1f}%\n")
        f.write(f"75th Percentile:    {non_pdf_stats['q75']:.1f}%\n")
        f.write(f"dPIDs ≥80%:         {non_pdf_stats['above_80']} ({non_pdf_stats['pct_above_80']:.1f}%)\n")
        f.write(f"dPIDs ≥90%:         {non_pdf_stats['above_90']} ({non_pdf_stats['pct_above_90']:.1f}%)\n")
        f.write(f"dPIDs <80%:         {non_pdf_stats['below_80']}\n\n")
        
        if pdf_stats:
            f.write("PDF-ONLY RESEARCH OBJECTS (for comparison)\n")
            f.write("-"*50 + "\n")
            f.write(f"Total dPIDs:        {pdf_stats['count']}\n")
            f.write(f"Mean Score:         {pdf_stats['mean']:.1f}%\n")
            f.write(f"Median Score:       {pdf_stats['median']:.1f}%\n")
            f.write(f"dPIDs ≥80%:         {pdf_stats['above_80']} ({pdf_stats['pct_above_80']:.1f}%)\n\n")
        
        # List low-scoring multi-file dPIDs
        low_scoring = [r for r in non_pdf_scores if r.get("score") and r["score"] < 80]
        if low_scoring:
            f.write("LOW-SCORING MULTI-FILE dPIDs (<80%)\n")
            f.write("-"*50 + "\n")
            for r in sorted(low_scoring, key=lambda x: x["score"]):
                f.write(f"  dPID {r['dpid']:>4}: {r['score']:.1f}%\n")
        else:
            f.write("All multi-file dPIDs achieved ≥80% FAIR compliance!\n")
    
    print(f"✅ Saved statistics report to: {output_path}")

def main():
    print("🔍 Loading data...")
    fair_results, pdf_only_dpids, content_summary = load_data()
    
    print(f"   Total results: {len(fair_results)}")
    print(f"   PDF-only dPIDs: {len(pdf_only_dpids)}")
    
    print("\n🔧 Filtering results...")
    non_pdf_only, pdf_only = filter_non_pdf_only(fair_results, pdf_only_dpids)
    
    print(f"   Non-PDF-only dPIDs with scores: {len(non_pdf_only)}")
    print(f"   PDF-only dPIDs with scores: {len(pdf_only)}")
    
    print("\n📊 Generating histograms...")
    non_pdf_stats, pdf_stats = generate_histogram(
        non_pdf_only, pdf_only, 
        OUTPUT_DIR / "non_pdf_fair_scores_histogram.png"
    )
    
    generate_combined_histogram(
        non_pdf_only, pdf_only,
        OUTPUT_DIR / "fair_scores_by_type_combined.png"
    )
    
    print_detailed_stats(non_pdf_stats, pdf_stats)
    
    save_stats_report(non_pdf_stats, pdf_stats, non_pdf_only,
                     OUTPUT_DIR / "non_pdf_fair_statistics.txt")
    
    # Save stats as JSON too
    with open(OUTPUT_DIR / "non_pdf_fair_statistics.json", "w") as f:
        json.dump({
            "non_pdf_only": non_pdf_stats,
            "pdf_only": pdf_stats
        }, f, indent=2)
    print(f"✅ Saved JSON statistics to: {OUTPUT_DIR / 'non_pdf_fair_statistics.json'}")

if __name__ == "__main__":
    main()

