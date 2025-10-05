#!/usr/bin/env python3
"""
Statistical Analysis of Model Comparison Scores
Performs paired t-test and generates summary statistics.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import sys

SCORES_FILE = Path("scores.csv")


def load_scores():
    """Load and validate scores."""
    if not SCORES_FILE.exists():
        print(f"ERROR: {SCORES_FILE} not found. No scores collected yet.")
        sys.exit(1)
    
    df = pd.read_csv(SCORES_FILE)
    return df


def analyze_paired_comparison(df):
    """
    Perform paired t-test comparing two models.
    
    For each clip, computes:
    - Average score across raters for each color (red/yellow)
    - Map colors back to models using color_mapping.json
    - Difference: D(i) = S(i,model2) - S(i,model1)
    - Paired t-test statistics
    """
    
    from pathlib import Path
    import json
    
    # Get latest run
    output_dir = Path("output")
    run_dirs = sorted(output_dir.glob("run_*"))
    if not run_dirs:
        print("ERROR: No run directories found")
        return
    
    mapping_file = run_dirs[-1] / "color_mapping.json"
    if not mapping_file.exists():
        print("WARNING: color_mapping.json not found - cannot map colors to models")
        color_mapping = {}
    else:
        with open(mapping_file, 'r') as f:
            color_mapping = json.load(f)
    
    # Group by video and text color
    video_color_scores = {}
    
    for (video_name, text_color), group in df.groupby(['video', 'text_color']):
        # Get all rater scores for this video+color combination
        scores = group['final_score'].values
        
        if video_name not in video_color_scores:
            video_color_scores[video_name] = {}
        
        video_color_scores[video_name][text_color] = {
            'scores': scores,
            'mean': np.mean(scores),
            'std': np.std(scores, ddof=1) if len(scores) > 1 else 0,
            'n_raters': len(scores)
        }
    
    print("=" * 80)
    print("STATISTICAL ANALYSIS: Model Comparison")
    print("=" * 80)
    print()
    
    # Overall statistics
    print(f"Total Videos: {len(video_color_scores)}")
    print(f"Total Ratings: {len(df) // 2}")  # Divided by 2 because each rating has red and yellow
    print(f"Unique Raters: {df['rater_id'].nunique()}")
    print()
    
    print("=" * 80)
    print("PER-VIDEO SCORES (by color)")
    print("=" * 80)
    print()
    
    for video_name in sorted(video_color_scores.keys()):
        print(f"{video_name}:")
        
        # Show color mapping if available
        if video_name in color_mapping:
            print(f"  Color Mapping:")
            for model, color in color_mapping[video_name].items():
                print(f"    {model}: {color}")
        
        # Show scores for each color
        for color in ['red', 'yellow']:
            if color in video_color_scores[video_name]:
                data = video_color_scores[video_name][color]
                print(f"  {color.upper()}:")
                print(f"    Mean: {data['mean']:.2f}")
                print(f"    Std Dev: {data['std']:.2f}")
                print(f"    N Raters: {data['n_raters']}")
        print()
    
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print()
    
    all_scores = df['final_score'].values
    print(f"Overall Mean Score: {np.mean(all_scores):.2f}")
    print(f"Overall Std Dev: {np.std(all_scores, ddof=1):.2f}")
    print(f"Min Score: {np.min(all_scores):.2f}")
    print(f"Max Score: {np.max(all_scores):.2f}")
    print()
    
    # Category-wise deductions
    print("=" * 80)
    print("CATEGORY-WISE DEDUCTIONS (Average)")
    print("=" * 80)
    print()
    
    deduction_cols = [col for col in df.columns if col.startswith('deduct_')]
    for col in deduction_cols:
        category = col.replace('deduct_', '').replace('_', ' ').title()
        mean_errors = df[col].mean()
        print(f"{category}: {mean_errors:.2f} errors (avg)")
    
    print()
    print("=" * 80)
    print(f"Results saved to: {SCORES_FILE}")
    print("=" * 80)


def main():
    """Main analysis function."""
    df = load_scores()
    analyze_paired_comparison(df)


if __name__ == "__main__":
    main()
