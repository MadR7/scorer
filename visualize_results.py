#!/usr/bin/env python3
"""
Visualize scoring results from scores.csv
Shows win rates, per-video breakdowns, and statistical analysis.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
import numpy as np

# Configuration
SCORES_FILE = Path("./output/scores.csv")
OUTPUT_DIR = Path("./output/visualizations")
OUTPUT_DIR.mkdir(exist_ok=True)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

def load_and_clean_data():
    """Load and clean the scores data."""
    df = pd.read_csv(SCORES_FILE)
    
    # Separate binary and detailed modes
    # For binary mode, 'coverage' column contains 'binary' and score is in 'order' column
    binary_df = df[df['coverage'] == 'binary'].copy()
    detailed_df = df[df['coverage'] != 'binary'].copy()
    
    # Fix binary scores - they're stored in the 'order' column due to CSV structure
    if len(binary_df) > 0:
        binary_df['score'] = pd.to_numeric(binary_df['order'])
    
    return df, binary_df, detailed_df


def analyze_binary_results(binary_df):
    """Analyze binary comparison results."""
    print("=" * 80)
    print("BINARY COMPARISON RESULTS")
    print("=" * 80)
    
    # Overall win rates
    total_comparisons = len(binary_df) // 2  # Each comparison has 2 rows
    
    finetuned_wins = binary_df[binary_df['model'] == 'finetuned']['score'].sum()
    baseline_wins = binary_df[binary_df['model'] == 'baseline']['score'].sum()
    ties = total_comparisons - (finetuned_wins + baseline_wins)
    
    print(f"\nTotal Comparisons: {total_comparisons}")
    print(f"  Finetuned Wins: {int(finetuned_wins)} ({finetuned_wins/total_comparisons*100:.1f}%)")
    print(f"  Baseline Wins: {int(baseline_wins)} ({baseline_wins/total_comparisons*100:.1f}%)")
    print(f"  Ties: {int(ties)} ({ties/total_comparisons*100:.1f}%)")
    
    # Per-video breakdown
    print("\n" + "-" * 80)
    print("PER-VIDEO BREAKDOWN")
    print("-" * 80)
    
    video_stats = []
    for video in sorted(binary_df['video'].unique()):
        video_data = binary_df[binary_df['video'] == video]
        ft_score = video_data[video_data['model'] == 'finetuned']['score'].sum()
        bl_score = video_data[video_data['model'] == 'baseline']['score'].sum()
        n_raters = len(video_data) // 2
        
        video_stats.append({
            'video': video,
            'finetuned': ft_score,
            'baseline': bl_score,
            'n_raters': n_raters
        })
        
        print(f"{video:12} | Finetuned: {int(ft_score)}/{n_raters} | Baseline: {int(bl_score)}/{n_raters}")
    
    # Per-rater breakdown
    print("\n" + "-" * 80)
    print("PER-RATER BREAKDOWN")
    print("-" * 80)
    
    for rater in sorted(binary_df['rater_id'].unique()):
        rater_data = binary_df[binary_df['rater_id'] == rater]
        ft_score = rater_data[rater_data['model'] == 'finetuned']['score'].sum()
        bl_score = rater_data[rater_data['model'] == 'baseline']['score'].sum()
        n_videos = len(rater_data) // 2
        
        print(f"{rater:12} | Finetuned: {int(ft_score)}/{n_videos} | Baseline: {int(bl_score)}/{n_videos}")
    
    return pd.DataFrame(video_stats), finetuned_wins, baseline_wins, ties


def create_visualizations(binary_df, video_stats, ft_wins, bl_wins, ties):
    """Create visualization plots."""
    
    fig = plt.figure(figsize=(16, 10))
    
    # Plot 1: Overall Win Rate (Pie Chart)
    ax1 = plt.subplot(2, 3, 1)
    colors = ['#4CAF50', '#F44336', '#FFC107']
    sizes = [ft_wins, bl_wins, ties]
    labels = [f'Finetuned\n{int(ft_wins)} wins', f'Baseline\n{int(bl_wins)} wins', f'Ties\n{int(ties)}']
    explode = (0.1, 0, 0) if ft_wins > bl_wins else (0, 0.1, 0)
    
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
            startangle=90, explode=explode, textprops={'fontsize': 10})
    ax1.set_title('Overall Win Rate', fontsize=14, fontweight='bold')
    
    # Plot 2: Per-Video Wins
    ax2 = plt.subplot(2, 3, 2)
    videos = video_stats['video'].values
    x = np.arange(len(videos))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, video_stats['finetuned'], width, label='Finetuned', color='#4CAF50')
    bars2 = ax2.bar(x + width/2, video_stats['baseline'], width, label='Baseline', color='#F44336')
    
    ax2.set_xlabel('Video')
    ax2.set_ylabel('Number of Wins')
    ax2.set_title('Wins Per Video', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(videos, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # Plot 3: Per-Rater Preferences
    ax3 = plt.subplot(2, 3, 3)
    rater_stats = []
    for rater in sorted(binary_df['rater_id'].unique()):
        rater_data = binary_df[binary_df['rater_id'] == rater]
        ft_score = rater_data[rater_data['model'] == 'finetuned']['score'].sum()
        bl_score = rater_data[rater_data['model'] == 'baseline']['score'].sum()
        rater_stats.append({'rater': rater, 'finetuned': ft_score, 'baseline': bl_score})
    
    rater_df = pd.DataFrame(rater_stats)
    x = np.arange(len(rater_df))
    
    bars1 = ax3.bar(x - width/2, rater_df['finetuned'], width, label='Finetuned', color='#4CAF50')
    bars2 = ax3.bar(x + width/2, rater_df['baseline'], width, label='Baseline', color='#F44336')
    
    ax3.set_xlabel('Rater')
    ax3.set_ylabel('Number of Wins')
    ax3.set_title('Preferences Per Rater', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f"R{i+1}" for i in range(len(rater_df))], rotation=0)
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)
    
    # Plot 4: Win Rate by Video (Percentage)
    ax4 = plt.subplot(2, 3, 4)
    video_stats['ft_pct'] = video_stats['finetuned'] / video_stats['n_raters'] * 100
    video_stats['bl_pct'] = video_stats['baseline'] / video_stats['n_raters'] * 100
    
    videos_sorted = video_stats.sort_values('ft_pct', ascending=True)
    y_pos = np.arange(len(videos_sorted))
    
    ax4.barh(y_pos, videos_sorted['ft_pct'], color='#4CAF50', label='Finetuned', alpha=0.8)
    ax4.barh(y_pos, -videos_sorted['bl_pct'], color='#F44336', label='Baseline', alpha=0.8)
    
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(videos_sorted['video'])
    ax4.set_xlabel('Win Rate (%)')
    ax4.set_title('Win Rate Per Video (Diverging)', fontsize=14, fontweight='bold')
    ax4.axvline(x=0, color='black', linewidth=0.8)
    ax4.legend()
    ax4.grid(axis='x', alpha=0.3)
    
    # Plot 5: Score Distribution Heatmap
    ax5 = plt.subplot(2, 3, 5)
    
    # Create matrix of scores
    pivot_data = []
    for video in sorted(binary_df['video'].unique()):
        for rater in sorted(binary_df['rater_id'].unique()):
            vid_rater = binary_df[(binary_df['video'] == video) & 
                                  (binary_df['rater_id'] == rater)]
            if len(vid_rater) > 0:
                ft_score = vid_rater[vid_rater['model'] == 'finetuned']['score'].values
                if len(ft_score) > 0:
                    pivot_data.append({
                        'video': video,
                        'rater': rater,
                        'winner': 'Finetuned' if ft_score[0] == 1 else ('Baseline' if ft_score[0] == 0 else 'Tie')
                    })
    
    if pivot_data:
        pivot_df = pd.DataFrame(pivot_data)
        pivot_table = pivot_df.pivot(index='video', columns='rater', values='winner')
        
        # Convert to numeric for heatmap
        winner_map = {'Finetuned': 1, 'Tie': 0.5, 'Baseline': 0}
        pivot_numeric = pivot_table.map(lambda x: winner_map.get(x, np.nan))
        
        sns.heatmap(pivot_numeric, annot=pivot_table.values, fmt='', cmap='RdYlGn',
                   cbar_kws={'label': 'Winner'}, ax=ax5, vmin=0, vmax=1,
                   linewidths=0.5, linecolor='gray')
        ax5.set_title('Rater Choices Heatmap', fontsize=14, fontweight='bold')
        ax5.set_xlabel('Rater')
        ax5.set_ylabel('Video')
    
    # Plot 6: Statistics Summary
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    # Binomial test
    n_comparisons = int(ft_wins + bl_wins + ties)
    result = stats.binomtest(int(ft_wins), n_comparisons, p=0.5, alternative='two-sided')
    p_value = result.pvalue
    
    # Effect size (win rate difference)
    effect_size = (ft_wins - bl_wins) / n_comparisons * 100
    
    stats_text = f"""
    STATISTICAL SUMMARY
    {'=' * 40}
    
    Total Comparisons: {n_comparisons}
    
    Finetuned Wins: {int(ft_wins)} ({ft_wins/n_comparisons*100:.1f}%)
    Baseline Wins: {int(bl_wins)} ({bl_wins/n_comparisons*100:.1f}%)
    Ties: {int(ties)} ({ties/n_comparisons*100:.1f}%)
    
    Effect Size: {effect_size:+.1f}%
    (Finetuned - Baseline)
    
    Binomial Test:
    p-value = {p_value:.4f}
    {'✓ Significant (p < 0.05)' if p_value < 0.05 else '✗ Not significant (p ≥ 0.05)'}
    
    Confidence: {(1-p_value)*100:.1f}%
    
    Interpretation:
    {'Finetuned model is significantly' if p_value < 0.05 else 'No significant difference'}
    {'better than baseline.' if p_value < 0.05 and ft_wins > bl_wins else ''}
    {'worse than baseline.' if p_value < 0.05 and ft_wins < bl_wins else ''}
    """
    
    ax6.text(0.1, 0.5, stats_text, fontsize=11, verticalalignment='center',
             fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'results_overview.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualization saved to: {OUTPUT_DIR / 'results_overview.png'}")
    
    return fig


def main():
    print("\n" + "=" * 80)
    print("SCORING RESULTS VISUALIZATION")
    print("=" * 80 + "\n")
    
    # Load data
    df, binary_df, detailed_df = load_and_clean_data()
    
    if len(binary_df) == 0:
        print("No binary comparison data found!")
        return
    
    # Analyze results
    video_stats, ft_wins, bl_wins, ties = analyze_binary_results(binary_df)
    
    # Create visualizations
    fig = create_visualizations(binary_df, video_stats, ft_wins, bl_wins, ties)
    
    print("\n" + "=" * 80)
    print("✓ Analysis complete!")
    print("=" * 80 + "\n")
    
    # Show plot
    plt.show()


if __name__ == "__main__":
    main()
