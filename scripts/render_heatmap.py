
# Render contributions heatmaps (light + dark) from JSON produced by github_contributions.py
import json
import sys

import matplotlib
matplotlib.use('Agg')  # headless rendering in CI
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches

LIGHT_PALETTE = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
DARK_PALETTE  = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']  # GitHub dark green scale

BOUNDS = [0, 1, 4, 7, 10, 1000]  # 0, 1-3, 4-6, 7-9, 10+

DAY_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', '']  # Show Mon/Wed/Fri like GitHub

def build_array(days):
    """Return (7 x n_weeks array, start_date) where row 0 = Sunday of contribution counts."""
    if not days:
        return None, None

    start = min(d for d, _ in days)
    # Align to Sunday (Monday=0..Sunday=6)
    if start.weekday() != 6:
        start = start - timedelta(days=(start.weekday() + 1))

    counts = {d: c for d, c in days}
    end = max(d for d, _ in days)

    weeks = []
    cur = start
    while cur <= end:
        sunday = cur if cur.weekday() == 6 else cur - timedelta(days=(cur.weekday() + 1))
        week_counts = [counts.get(sunday + timedelta(days=o), 0) for o in range(7)]
        weeks.append(week_counts)
        cur = sunday + timedelta(days=7)

    return np.array(weeks).T, start  # shape (7, n_weeks), start date

def get_month_positions(start_date, n_weeks):
    """Calculate month label positions and labels for the heatmap."""
    month_labels = []
    month_positions = []
    current_month = None
    
    for week_idx in range(n_weeks):
        week_start = start_date + timedelta(weeks=week_idx)
        month = week_start.month
        
        if month != current_month:
            current_month = month
            month_labels.append(week_start.strftime('%b'))
            month_positions.append(week_idx)
    
    return month_positions, month_labels

def render_svg(arr, start_date, palette, out_svg, theme='light'):
    """Render heatmap with given palette to SVG, GitHub style with month labels."""
    if arr is None:
        fig = plt.figure(figsize=(10, 1))
        plt.text(0.5, 0.5, 'No data', ha='center', va='center')
        plt.axis('off')
        fig.savefig(out_svg, bbox_inches='tight')
        return

    cmap = ListedColormap(palette)
    norm = BoundaryNorm(BOUNDS, cmap.N)

    h, w = arr.shape  # h=7 (days), w=number of weeks
    
    # Calculate figure size similar to GitHub
    cell_size = 0.14  # inches per cell
    fig_width = max(w * cell_size + 1.5, 10)  # Add space for day labels
    fig_height = h * cell_size + 0.8  # Add space for month labels
    
    # Set background color based on theme
    bg_color = 'white' if theme == 'light' else '#0d1117'
    text_color = '#24292f' if theme == 'light' else '#c9d1d9'
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor=bg_color)
    
    # Draw individual squares like GitHub
    for day in range(h):
        for week in range(w):
            count = arr[day, week]
            # Determine color based on count
            color_idx = 0
            for i, bound in enumerate(BOUNDS[1:]):
                if count >= BOUNDS[i]:
                    color_idx = i
            
            color = palette[color_idx]
            rect = mpatches.Rectangle((week, day), 1, 1, 
                                     linewidth=0.5, 
                                     edgecolor=bg_color,
                                     facecolor=color)
            ax.add_patch(rect)
    
    # Set axis limits and aspect
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect('equal')
    
    # Add day labels on the left (like GitHub)
    ax.set_yticks([i + 0.5 for i in range(h)])
    ax.set_yticklabels(DAY_LABELS, fontsize=8, color=text_color)
    ax.tick_params(left=False, labelleft=True)
    
    # Add month labels at the top
    month_positions, month_labels = get_month_positions(start_date, w)
    ax.set_xticks([pos + 0.5 for pos in month_positions])
    ax.set_xticklabels(month_labels, fontsize=8, color=text_color, ha='left')
    ax.tick_params(top=False, bottom=False, labeltop=True, labelbottom=False)
    
    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    fig.patch.set_facecolor(bg_color)
    fig.savefig(out_svg, bbox_inches='tight', facecolor=bg_color, dpi=100)
    plt.close(fig)

def main():
    if len(sys.argv) < 4:
        print('Usage: python scripts/render_heatmap.py data/contributions.json assets/contributions_heatmap_light.svg assets/contributions_heatmap_dark.svg')
        sys.exit(1)

    in_json, out_light, out_dark = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(in_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    days = [(datetime.strptime(d['date'], '%Y-%m-%d').date(), d['count'])
            for d in data.get('calendar_days', [])]

    arr, start_date = build_array(days)

    # Light theme
    render_svg(arr, start_date, LIGHT_PALETTE, out_light, theme='light')
    # Dark theme
    render_svg(arr, start_date, DARK_PALETTE, out_dark, theme='dark')
    
    print(f"✓ Generated heatmaps: {out_light}, {out_dark}")

if __name__ == '__main__':
    main()
