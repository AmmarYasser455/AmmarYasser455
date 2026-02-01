#!/usr/bin/env python3
"""
Fetch recent public events for the given user and update README.md between
markers <!-- START_CONTRIBS --> and <!-- END_CONTRIBS -->.
"""

import os
import sys
import requests
from datetime import datetime, timezone
from dateutil import parser as dateparser

GITHUB_API = "https://api.github.com"
USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_ACTOR") or "AmmarYasser455"
TOKEN = os.environ.get("GITHUB_TOKEN")  # provided by Actions

README_PATH = "README.md"
START_MARKER = "<!-- START_CONTRIBS -->"
END_MARKER = "<!-- END_CONTRIBS -->"
EVENTS_PER_PAGE = 30  # how many recent events to show

HEADERS = {}
if TOKEN:
    HEADERS["Authorization"] = f"token {TOKEN}"
HEADERS["Accept"] = "application/vnd.github.v3+json"


def fetch_events(user, per_page=EVENTS_PER_PAGE):
    url = f"{GITHUB_API}/users/{user}/events/public?per_page={per_page}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fmt_event(ev):
    t = ev.get("type")
    repo = ev.get("repo", {}).get("name", "")
    repo_url = f"https://github.com/{repo}" if repo else ""
    created = ev.get("created_at")
    when = ""
    if created:
        try:
            when = dateparser.parse(created).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            when = created

    if t == "PushEvent":
        commits = ev.get("payload", {}).get("size", 0)
        return f"- [{repo}]({repo_url}) — pushed {commits} commit(s) ({when})"
    if t == "PullRequestEvent":
        action = ev.get("payload", {}).get("action", "")
        pr = ev.get("payload", {}).get("pull_request", {})
        pr_url = pr.get("html_url")
        title = pr.get("title", "PR")
        if pr_url:
            return f"- [{repo}]({repo_url}) — {action} pull request [{title}]({pr_url}) ({when})"
        return f"- [{repo}]({repo_url}) — {action} pull request ({when})"
    if t == "IssuesEvent":
        action = ev.get("payload", {}).get("action", "")
        issue = ev.get("payload", {}).get("issue", {})
        issue_url = issue.get("html_url")
        title = issue.get("title", "issue")
        if issue_url:
            return f"- [{repo}]({repo_url}) — {action} issue [{title}]({issue_url}) ({when})"
        return f"- [{repo}]({repo_url}) — {action} issue ({when})"
    if t == "IssueCommentEvent":
        comment = ev.get("payload", {}).get("comment", {})
        url = comment.get("html_url")
        return f"- [{repo}]({repo_url}) — commented on an issue ([link]({url})) ({when})"
    if t == "PullRequestReviewCommentEvent":
        comment = ev.get("payload", {}).get("comment", {})
        url = comment.get("html_url")
        return f"- [{repo}]({repo_url}) — commented on a PR ([link]({url})) ({when})"
    if t == "CreateEvent":
        ref_type = ev.get("payload", {}).get("ref_type", "")
        ref = ev.get("payload", {}).get("ref", "")
        if ref_type:
            return f"- [{repo}]({repo_url}) — created {ref_type} `{ref}` ({when})"
        return f"- [{repo}]({repo_url}) — created something ({when})"
    if t == "WatchEvent":
        return f"- [{repo}]({repo_url}) — starred ({when})"
    # fallback
    return f"- [{repo}]({repo_url}) — {t} ({when})"


def build_block(events):
    lines = []
    lines.append("## Recent activity")
    lines.append("")
    lines.append(f"Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    if not events:
        lines.append("_No recent public activity found._")
    else:
        for ev in events:
            try:
                lines.append(fmt_event(ev))
            except Exception:
                lines.append(f"- {ev.get('type')} — {ev.get('repo', {}).get('name', '')}")
    lines.append("")
    lines.append("> This section is updated automatically by a GitHub Action")
    return "\n".join(lines)


def readme_replace_block(readme_text, new_block):
    if START_MARKER in readme_text and END_MARKER in readme_text:
        pre, rest = readme_text.split(START_MARKER, 1)
        _, post = rest.split(END_MARKER, 1)
        return pre + START_MARKER + "\n" + new_block + "\n" + END_MARKER + post
    else:
        # append markers at the end
        if not readme_text.endswith("\n"):
            readme_text += "\n"
        return readme_text + "\n" + START_MARKER + "\n" + new_block + "\n" + END_MARKER + "\n"


def main():
    try:
        events = fetch_events(USER)
    except Exception as e:
        print("Failed to fetch events:", e, file=sys.stderr)
        events = []

    new_block = build_block(events)

    try:
        if os.path.exists(README_PATH):
            with open(README_PATH, "r", encoding="utf-8") as f:
                readme = f.read()
        else:
            readme = "# " + USER + "\n\n"

        updated = readme_replace_block(readme, new_block)

        if updated != readme:
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(updated)
            print("README.md updated.")
        else:
            print("No changes to README.md.")
    except Exception as e:
        print("Failed to update README.md:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
