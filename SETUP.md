# GitHub Profile Contributions Setup

This repository automatically generates a contributions summary on your GitHub profile page, including **both public and private contributions**.

## How It Works

The workflow uses GitHub's GraphQL API with the `viewer` query, which allows you to see your own private contributions when authenticated with a personal access token (PAT).

### Key Components

1. **GitHub Workflow** (`.github/workflows/update-contributions.yml`)
   - Runs daily at 02:00 UTC
   - Can be triggered manually from Actions tab
   - Fetches last 12 months of contributions
   - Generates heatmap visualizations (light + dark mode)
   - Updates README.md automatically

2. **Python Scripts**
   - `scripts/github_contributions.py` - Fetches contribution data via GraphQL
   - `scripts/render_heatmap.py` - Generates SVG heatmaps
   - `scripts/update_readme.py` - Updates README with summary

## Setup Instructions

### 1. Create a Fine-Grained Personal Access Token

1. Go to https://github.com/settings/tokens?type=beta
2. Click "Generate new token"
3. Configure the token:
   - **Name**: `GH_CONTRIB_TOKEN` (or any descriptive name)
   - **Expiration**: Choose appropriate duration (90 days, 1 year, etc.)
   - **Resource owner**: Select yourself
   - **Repository access**: Choose "All repositories" OR select specific repos
   - **Permissions** (Account permissions section):
     - ✅ **Read access to metadata** (usually enabled by default)
   - **Organization permissions** (if you have org contributions):
     - ✅ **Read access to members** (for org contributions)

   **Important for Fine-Grained Tokens:**
   - If using a classic token instead, ensure it has: `read:user`, `repo`, `read:org` scopes
   - Fine-grained tokens need "All repositories" access to count contributions across all your repos
   - For organizations, you may need org admin to authorize the token

4. Click "Generate token" and copy it

### 2. Add Token as Repository Secret

1. Go to your repository settings
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click "New repository secret"
4. Name: `GH_CONTRIB_TOKEN`
5. Value: Paste your token
6. Click "Add secret"

### 3. Enable Private Contributions in Profile Settings

**Important:** To include private contributions, you must enable them in your GitHub profile:

1. Go to https://github.com/settings/profile
2. Scroll to "Contributions & Activity"
3. Check: **"Private contributions"**
   - This allows the GraphQL API to return your private contribution counts

### 4. Add Markers to README

Add these markers to your `README.md` where you want the summary to appear:

```markdown
<!--CONTRIB_SUMMARY_START-->
<!--CONTRIB_SUMMARY_END-->
```

The workflow will automatically populate content between these markers.

## What Data is Collected

The workflow collects:

- **Public contributions**: All your public commits, PRs, issues, reviews
- **Private contributions**: Anonymized counts from private repositories
  - Shows total count
  - Does NOT reveal repository names or specific details
  - Only shows aggregated numbers per type (commits, PRs, etc.)

### Privacy Note

Private repository names and details are included in the data but only displayed as aggregated counts. The heatmap shows combined public + private activity.

## Manual Trigger

To run the workflow manually:

1. Go to **Actions** tab in your repository
2. Select "Update contributions" workflow
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Click "Run workflow"

## Troubleshooting

### No private contributions showing

1. Verify token is set correctly as `GH_CONTRIB_TOKEN`
2. Check that private contributions are enabled in profile settings
3. Ensure token hasn't expired
4. Check workflow logs for errors

### Workflow fails with authentication error

- Token may be expired or invalid
- Regenerate token and update the secret

### Heatmap not showing

- Check that `assets/` directory exists
- Verify `matplotlib` is installed in workflow (it is by default)
- Check workflow logs for rendering errors

## Required Dependencies

The workflow automatically installs:
- `requests` - For GraphQL API calls
- `matplotlib` - For heatmap generation

## Workflow Schedule

- **Daily**: 02:00 UTC
- **Manual**: Via Actions tab
- **On push**: To main branch (bootstrap)

## Output Files

- `data/contributions.json` - Raw contribution data
- `data/summary.md` - Markdown summary
- `assets/contributions_heatmap_light.svg` - Light mode heatmap
- `assets/contributions_heatmap_dark.svg` - Dark mode heatmap
- `README.md` - Updated with latest summary

## Token Permissions Explained

### Why Repository Access is Needed

Even though you're querying your own data, GitHub's GraphQL API requires proper authorization:

**Fine-Grained Token:**
- Needs **"All repositories"** access (or at minimum, all repos you've contributed to)
- Needs **organization permissions** if you have org contributions
- Without these, contributions show as "restricted" (anonymized)

**Classic Token (Alternative):**
- Scopes needed: `read:user`, `repo`, `read:org`
- Simpler but less secure than fine-grained tokens
- To create: https://github.com/settings/tokens (select "Tokens (classic)")

### If Most Contributions Show as "Restricted"

This means the token can see you HAVE contributions but can't access the details:
1. **Regenerate token** with "All repositories" access
2. **Check organization settings** - org admin may need to approve the token
3. **Try a classic token** with full scopes if fine-grained tokens have issues
