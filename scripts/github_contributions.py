
# -*- coding: utf-8 -*-
"""
Fetch GitHub contributions via GraphQL and output JSON + Markdown summary.

Usage:
  export GITHUB_TOKEN=your_token
  python scripts/github_contributions.py --username USER --from 2025-01-01 --to 2025-12-31 \
    --out-json data/contributions.json --out-md data/summary.md
"""
import os
import sys
import json
import argparse

try:
    import requests
except Exception:
    requests = None

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


QUERY = """
query {
  viewer {
    login
    name
    contributionsCollection {
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
"""

def fetch(token: str) -> dict:
    import requests
    headers = {"Authorization": f"bearer {token}"}
    payload = {"query": QUERY}
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    # Note: top field is 'viewer' now
    return data["data"]["viewer"]

def summarize(viewer: dict) -> dict:
    user = viewer
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [{"date": d["date"], "count": d["contributionCount"], "level": d["contributionLevel"]}
            for w in cal["weeks"] for d in w["contributionDays"]]
    def conv(entries):
        return [{"repo": e["repository"]["nameWithOwner"],
                 "isPrivate": e["repository"]["isPrivate"],
                 "count": e["contributions"]["totalCount"]}
                for e in entries]
    return {
        "user": {"login": viewer["login"], "name": viewer.get("name")},
        "range": {"from": "profile-last-year", "to": "profile-last-year"},  # descriptive placeholders
        "totals": {
            "calendar_total": cal["totalContributions"],
            "commits": cc["totalCommitContributions"],
            "issues": cc["totalIssueContributions"],
            "pull_requests": cc["totalPullRequestContributions"],
            "reviews": cc["totalPullRequestReviewContributions"],
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

def main():
    ap = argparse.ArgumentParser(description="Export GitHub contributions (profile last year)")
    # username/from/to are no longer needed
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN env var required", file=sys.stderr)
        sys.exit(1)

    viewer = fetch(token)
    summary = summarize(viewer)

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    md = to_md(summary)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {args.out_json} and {args.out_md}")

"""

def fetch(token: str, username: str, start: str, end: str) -> dict:
    """Call GitHub GraphQL API to get contributions for a date range."""
    if requests is None:
        raise RuntimeError("Install 'requests' and run locally/CI.")
    headers = {"Authorization": f"bearer {token}"}
    payload = {"query": QUERY,
               "variables": {"username": username,
                             "from": f"{start}T00:00:00Z",
                             "to":   f"{end}T23:59:59Z"}}
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]["user"]

def summarize(user: dict, start: str, end: str) -> dict:
    """Transform API payload into an easy-to-publish summary."""
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [{"date": d["date"],
             "count": d["contributionCount"],
             "level": d["contributionLevel"]}
            for w in cal["weeks"] for d in w["contributionDays"]]

    def conv(entries):
        return [{"repo": e["repository"]["nameWithOwner"],
                 "isPrivate": e["repository"]["isPrivate"],
                 "count": e["contributions"]["totalCount"]}
                for e in entries]

    return {
        "user": {"login": user["login"], "name": user.get("name")},
        "range": {"from": start, "to": end},
        "totals": {
            "calendar_total": cal["totalContributions"],
            "commits": cc["totalCommitContributions"],
            "issues": cc["totalIssueContributions"],
            "pull_requests": cc["totalPullRequestContributions"],
            "reviews": cc["totalPullRequestReviewContributions"],
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
    t = summary["totals"]
    lines = []
    lines.append(f"### Contributions summary (last 12 months)")
    lines.append(f"- Total contributions: **{t['calendar_total']}**")
    lines.append(f"- Commits: **{t['commits']}**, Issues: **{t['issues']}**, "
                 f"PRs: **{t['pull_requests']}**, Reviews: **{t['reviews']}**")
    if t["restricted_contributions_present"]:
        lines.append(f"- Includes anonymized private/internal activity: "
                     f"**{t['restricted_contributions_count']}**")
    lines.append("")

    def section(title: str, key: str):
        items = sorted(summary["by_repository"][key], key=lambda e: e["count"], reverse=True)[:10]
        lines.append(f"#### Top {title}")
        if not items:
            lines.append("_No data_")
        else:
            for e in items:
                priv = " (private)" if e["isPrivate"] else ""
                lines.append(f"- **{e['repo']}**: {e['count']}{priv}")
        lines.append("")

    section("commit repos", "commits")
    section("PR repos", "pull_requests")
    section("issue repos", "issues")
    section("reviewed repos", "reviews")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="Export GitHub contributions")
    ap.add_argument("--username", required=True)
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN env var required", file=sys.stderr)
        sys.exit(1)

    user = fetch(token, args.username, args.start, args.end)
    summary = summarize(user, args.start, args.end)

    # Safety: create output folders if missing
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    md = to_md(summary)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote {args.out_json} and {args.out_md}")

if __name__ == "__main__":
    main()
