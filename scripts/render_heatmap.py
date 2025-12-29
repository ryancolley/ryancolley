
# Render contributions heatmaps (light + dark) from JSON produced by github_contributions.py
import json
import sys

import matplotlib
matplotlib.use('Agg')  # headless rendering in CI
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm

LIGHT_PALETTE = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
DARK_PALETTE  = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']  # GitHub dark green scale

BOUNDS = [0, 1, 4, 7, 10, 1000]  # 0, 1-3, 4-6, 7-9, 10+

def build_array(days):
    """Return 7 x n_weeks array (row 0 = Sunday) of contribution counts."""
    if not days:
        return None

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

    return np.array(weeks).T  # shape (7, n_weeks)

def render_svg(arr, palette, out_svg):
    """Render heatmap with given palette to SVG."""
    if arr is None:
        fig = plt.figure(figsize=(10, 1))
        plt.text(0.5, 0.5, 'No data', ha='center', va='center')
        plt.axis('off')
        fig.savefig(out_svg, bbox_inches='tight')
        return

    cmap = ListedColormap(palette)
    norm = BoundaryNorm(BOUNDS, cmap.N)

    h, w = arr.shape
    fig_height = 1.8
    fig_width  = max(w * 0.18, 3)  # ensure minimum width

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.imshow(arr, aspect='auto', cmap=cmap, norm=norm, origin='lower')
    ax.set_axis_off()
    fig.savefig(out_svg, bbox_inches='tight', transparent=True)

def main():
    if len(sys.argv) < 4:
        print('Usage: python scripts/render_heatmap.py data/contributions.json assets/contributions_heatmap_light.svg assets/contributions_heatmap_dark.svg')
        sys.exit(1)

    in_json, out_light, out_dark = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(in_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    days = [(datetime.strptime(d['date'], '%Y-%m-%d').date(), d['count'])
            for d in data.get('calendar_days', [])]

    arr = build_array(days)

    # Light
    render_svg(arr, LIGHT_PALETTE, out_light)
    # Dark
    render_svg(arr, DARK_PALETTE, out_dark)

if __name__ == '__main__':
    main()
