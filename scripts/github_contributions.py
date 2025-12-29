# -*- coding: utf-8 -*-
"""
Fetch GitHub contributions via GraphQL and output JSON + Markdown summary.

Usage:
  export GITHUB_TOKEN=your_token
  python scripts/github_contributions.py --out-json data/contributions.json --out-md data/summary.md

IMPORTANT: To get accurate contribution counts including private/org activity:
1. Ensure your GITHUB_TOKEN has appropriate scopes (read:user, repo)
2. Go to https://github.com/settings/profile
3. Enable "Private contributions" (Show private contributions on my profile)
4. Enable organization contributions visibility in your profile settings

The API will only return contributions that are visible according to your
privacy settings. Restricted contributions are anonymized but counted.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta

try:
    import requests
except Exception:
    requests = None

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


def build_query(from_date: str, to_date: str) -> str:
    """Build GraphQL query with explicit date range."""
    return """
query {
  viewer {
    login
    name
    contributionsCollection(from: "%s", to: "%s") {
      hasAnyRestrictedContributions
      restrictedContributionsCount
      earliestRestrictedContributionDate
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalRepositoryContributions
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
        contributions { totalCount }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
        contributions { totalCount }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
        contributions { totalCount }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
        contributions { totalCount }
      }
    }
  }
}
""" % (from_date, to_date)

def fetch(token: str) -> dict:
    """Call GitHub GraphQL API to get contributions (viewer = authenticated user)."""
    if requests is None:
        raise RuntimeError("Install 'requests' and run locally/CI.")
    
    # Calculate date range: last 365 days from today
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=365)
    
    # Format as ISO 8601 datetime strings (required by GitHub GraphQL API)
    from_str = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_str = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    query = build_query(from_str, to_str)
    
    headers = {"Authorization": f"bearer {token}"}
    payload = {"query": query}
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]["viewer"]

def summarize(viewer: dict) -> dict:
    """Transform API payload into an easy-to-publish summary."""
    cc = viewer["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [{"date": d["date"], "count": d["contributionCount"], "level": d["contributionLevel"]}
            for w in cal["weeks"] for d in w["contributionDays"]]
    
    # Get date range from calendar data
    date_range_from = days[0]["date"] if days else "N/A"
    date_range_to = days[-1]["date"] if days else "N/A"
    
    def conv(entries):
        return [{"repo": e["repository"]["nameWithOwner"],
                 "isPrivate": e["repository"]["isPrivate"],
                 "count": e["contributions"]["totalCount"]}
                for e in entries]
    
    return {
        "user": {"login": viewer["login"], "name": viewer.get("name")},
        "range": {"from": date_range_from, "to": date_range_to},
        "totals": {
            "calendar_total": cal["totalContributions"],
            "commits": cc["totalCommitContributions"],
            "issues": cc["totalIssueContributions"],
            "pull_requests": cc["totalPullRequestContributions"],
            "reviews": cc["totalPullRequestReviewContributions"],
            "repositories": cc.get("totalRepositoryContributions", 0),
            "restricted_contributions_present": cc["hasAnyRestrictedContributions"],
            "restricted_contributions_count": cc["restrictedContributionsCount"],
            "earliest_restricted_contribution_date": cc["earliestRestrictedContributionDate"]
        },
        "by_repository": {
            "commits": conv(cc["commitContributionsByRepository"]),
            "issues": conv(cc["issueContributionsByRepository"]),
            "pull_requests": conv(cc["pullRequestContributionsByRepository"]),
            "reviews": conv(cc["pullRequestReviewContributionsByRepository"])
        },
        "calendar_days": days
    }


def to_md(summary: dict) -> str:
    """Generate markdown summary from contribution data."""
    t = summary["totals"]
    r = summary["range"]
    lines = []
    lines.append(f"### Contributions summary ({r['from']} → {r['to']})")
    lines.append(f"- Total contributions: **{t['calendar_total']}**")
    lines.append(f"- Commits: **{t['commits']}**, Issues: **{t['issues']}**, "
                 f"PRs: **{t['pull_requests']}**, Reviews: **{t['reviews']}**")
    
    if t.get('repositories', 0) > 0:
        lines.append(f"- Repositories contributed to: **{t['repositories']}**")
    
    if t["restricted_contributions_present"]:
        earliest = t.get("earliest_restricted_contribution_date", "N/A")
        lines.append(f"- Includes anonymized private/internal activity: "
                     f"**{t['restricted_contributions_count']}**"
                     f"{f' (since {earliest})' if earliest and earliest != 'N/A' else ''}")
    lines.append("")

    def section(title: str, key: str):
        items = sorted(summary["by_repository"][key], key=lambda e: e["count"], reverse=True)[:10]
        lines.append(f"#### Top {title}")
        if not items:
            lines.append("_No data_")
        else:
            for e in items:
                lines.append(f"- **{e['repo']}**: {e['count']}")
        lines.append("")

    section("commit repos", "commits")
    section("PR repos", "pull_requests")
    section("issue repos", "issues")
    section("reviewed repos", "reviews")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Export GitHub contributions (last 12 months)")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN env var required", file=sys.stderr)
        sys.exit(1)

    viewer = fetch(token)
    summary = summarize(viewer)

    # Safety: create output folders if missing
    os.makedirs(os.path.dirname(args.out_json) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.out_md) or ".", exist_ok=True)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    md = to_md(summary)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
