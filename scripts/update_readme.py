# Update README.md between markers and ensure heatmap embed line exists
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print('Usage: python scripts/update_readme.py data/summary.md README.md')
    sys.exit(1)

summary_path = Path(sys.argv[1])
readme_path = Path(sys.argv[2])

start_marker = '<!--CONTRIB_SUMMARY_START-->'
end_marker = '<!--CONTRIB_SUMMARY_END-->'

summary = summary_path.read_text(encoding='utf-8')
readme = readme_path.read_text(encoding='utf-8')

if start_marker not in readme or end_marker not in readme:
    # append section
    block = f"\n\n{start_marker}\n{summary}\n![Contributions heatmap](assets/contributions_heatmap.svg)\n{end_marker}\n"
    readme += block
else:
    pre, rest = readme.split(start_marker, 1)
    cur, post = rest.split(end_marker, 1)
    new_block = f"\n{start_marker}\n{summary}\n![Contributions heatmap](assets/contributions_heatmap.svg)\n{end_marker}\n"
    readme = pre + new_block + post

readme_path.write_text(readme, encoding='utf-8')
print('README updated.')
