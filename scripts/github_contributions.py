
# -*- coding: utf-8 -*-
"""
Fetch GitHub contributions via GraphQL and output JSON + Markdown summary.
Usage:
  export GITHUB_TOKEN=your_token
  python scripts/github_contributions.py --username USER --from 2025-01-01 --to 2025-12-31 \
    --out-json data/contributions.json --out-md data/summary.md
"""
import os, sys, json, argparse
try:
    import requests
except Exception:
    requests = None

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"

QUERY = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    login
    name
    contributionsCollection(from: $from, to: $to) {
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

def fetch(token, username, start, end):
    if requests is None:
        raise RuntimeError("Install requests and run locally/CI.")
    headers = {"Authorization": f"bearer {token}"}
    payload = {"query": QUERY, "variables": {"username": username, "from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"}}
    r = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
    r.raise_for_status()
    j = r.json()
    if 'errors' in j:
        raise RuntimeError(json.dumps(j['errors'], indent=2))
    return j['data']['user']

def summarize(user, start, end):
    cc = user['contributionsCollection']
    cal = cc['contributionCalendar']
    days = [{"date": d['date'], "count": d['contributionCount'], "level": d['contributionLevel']}
            for w in cal['weeks'] for d in w['contributionDays']]
    def conv(entries):
        return [{"repo": e['repository']['nameWithOwner'], "isPrivate": e['repository']['isPrivate'], "count": e['contributions']['totalCount']} for e in entries]
    return {
        "user": {"login": user['login'], "name": user.get('name')},
        "range": {"from": start, "to": end},
        "totals": {
            "calendar_total": cal['totalContributions'],
            "commits": cc['totalCommitContributions'],
            "issues": cc['totalIssueContributions'],
            "pull_requests": cc['totalPullRequestContributions'],
            "reviews": cc['totalPullRequestReviewContributions'],
            "restricted_contributions_present": cc['hasAnyRestrictedContributions'],
            "restricted_contributions_count": cc['restrictedContributionsCount'],
            "earliest_restricted_contribution_date": cc['earliestRestrictedContributionDate']
        },
        "by_repository": {
            "commits": conv(cc['commitContributionsByRepository']),
            "issues": conv(cc['issueContributionsByRepository']),
            "pull_requests": conv(cc['pullRequestContributionsByRepository']),
            "reviews": conv(cc['pullRequestReviewContributionsByRepository'])
        },
        "calendar_days": days
    }

def to_md(summary):
    r = summary['range']; t = summary['totals']
    out = []
    out.append(f"### Contributions summary ({r['from']} → {r['to']})")
    out.append(f"- Total contributions: **{t['calendar_total']}**")
    out.append(f"- Commits: **{t['commits']}**, Issues: **{t['issues']}**, PRs: **{t['pull_requests']}**, Reviews: **{t['reviews']}**")
    if t['restricted_contributions_present']:
        out.append(f"- Includes anonymized private/internal activity: **{t['restricted_contributions_count']}** (since {t['earliest_restricted_contribution_date']})")
    out.append("")
    def sec(title, key):
        items = sorted(summary['by_repository'][key], key=lambda e: e['count'], reverse=True)[:10]
        out.append(f"#### Top {title}")
        if not items:
            out.append("_No data_")
        else:
            for e in items:
                out.append(f"- **{e['repo']}**: {e['count']}{' (private)' if e['isPrivate'] else ''}")
        out.append("")
    sec("commit repos", "commits")
    sec("PR repos", "pull_requests")
    sec("issue repos", "issues")
    sec("reviewed repos", "reviews")
    return "\n".join(out)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--username', required=True)
    ap.add_argument('--from', dest='start', required=True)
    ap.add_argument('--to', dest='end', required=True)
    ap.add_argument('--out-json', required=True)
    ap.add_argument('--out-md', required=True)
    args = ap.parse_args()

    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('GITHUB_TOKEN env var required', file=sys.stderr)
        sys.exit(1)

    user = fetch(token, args.username, args.start, args.end)
    summary = summarize(user, args.start, args.end)

    # Ensure output dirs exist
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)

    with open(args.out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    md = to_md(summary)
    with open(args.out_md, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"Wrote {args.out_json} and {args.out_md}")
``
