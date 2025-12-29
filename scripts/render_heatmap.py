# Render contributions heatmap SVG from JSON produced by github_contributions.py
import json, sys, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

if len(sys.argv) < 3:
    print('Usage: python scripts/render_heatmap.py data/contributions.json assets/contributions_heatmap.svg')
    sys.exit(1)

in_json, out_svg = sys.argv[1], sys.argv[2]

with open(in_json, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Build calendar grid (weeks x weekdays). GitHub calendar is weeks horizontally, Sunday..Saturday vertically
# We'll sort by date and fill columns by week
from datetime import date

# Parse dates and counts
days = [(datetime.strptime(d['date'], '%Y-%m-%d').date(), d['count']) for d in data['calendar_days']]
if not days:
    # Create empty placeholder
    fig = plt.figure(figsize=(10,1))
    plt.text(0.5,0.5,'No data', ha='center', va='center')
    plt.axis('off')
    fig.savefig(out_svg, bbox_inches='tight')
    sys.exit(0)

# Determine week index mapping
start = min(d for d,_ in days)
# Align to Sunday
start = start if start.weekday()==6 else start - datetime.timedelta(days=(start.weekday()+1))

# Build mapping date->count
counts = {d:c for d,c in days}

# Create continuous range from start to end
end = max(d for d,_ in days)
# extend to Saturday
# Python weekday: Monday=0..Sunday=6; we want Sunday=6 bottom row, so we will compute accordingly

# Build grid columns week by week
cur = start
weeks = []
col = []
while cur <= end:
    # Week column: Sunday(6) at index 0 to Saturday(5)?? Let's map to 0..6 from Sunday..Saturday
    # We'll fill 7 entries per week
    week = []
    # Determine the Sunday of this week
    sunday = cur if cur.weekday()==6 else cur - datetime.timedelta(days=(cur.weekday()+1))
    for offset in range(7):
        d = sunday + datetime.timedelta(days=offset)
        week.append(counts.get(d, 0))
    weeks.append(week)
    cur = sunday + datetime.timedelta(days=7)

import numpy as np
arr = np.array(weeks).T  # shape (7, n_weeks), rows=weekdays

# Color palette reminiscent of classic GitHub greens
from matplotlib.colors import ListedColormap, BoundaryNorm
colors = ['#ebedf0','#9be9a8','#40c463','#30a14e','#216e39']
cmap = ListedColormap(colors)
# Boundaries: 0,1-3,4-6,7-9,10+
bounds = [0,1,4,7,10,1000]
norm = BoundaryNorm(bounds, cmap.N)

h, w = arr.shape
fig, ax = plt.subplots(figsize=(w*0.18, 1.8))
im = ax.imshow(arr, aspect='auto', cmap=cmap, norm=norm, origin='lower')
ax.set_axis_off()
fig.savefig(out_svg, bbox_inches='tight', transparent=True)
