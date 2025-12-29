
# Render contributions heatmap SVG from JSON produced by github_contributions.py
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm

if len(sys.argv) < 3:
    print('Usage: python scripts/render_heatmap.py data/contributions.json assets/contributions_heatmap.svg')
    sys.exit(1)

in_json, out_svg = sys.argv[1], sys.argv[2]

with open(in_json, 'r', encoding='utf-8') as f:
    data = json.load(f)

days = [(datetime.strptime(d['date'], '%Y-%m-%d').date(), d['count']) for d in data.get('calendar_days', [])]

if not days:
    fig = plt.figure(figsize=(10, 1))
    plt.text(0.5, 0.5, 'No data', ha='center', va='center')
    plt.axis('off')
    fig.savefig(out_svg, bbox_inches='tight')
    sys.exit(0)

start = min(d for d, _ in days)
if start.weekday() != 6:  # Monday=0 .. Sunday=6
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

arr = np.array(weeks).T  # (7, n_weeks), row 0 = Sunday

colors = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
cmap = ListedColormap(colors)
bounds = [0, 1, 4, 7, 10, 1000]
norm = BoundaryNorm(bounds, cmap.N)

h, w = arr.shape
fig_height = 1.8
fig_width = max(w * 0.18, 3)

fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.imshow(arr, aspect='auto', cmap=cmap, norm=norm, origin='lower')
ax.set_axis_off()
fig.savefig(out_svg, bbox_inches='tight', transparent=True)
``
