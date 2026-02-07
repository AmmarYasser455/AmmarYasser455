"""Fetch recent GitHub activity and update README.md."""

import json
import os
import subprocess
import sys

USERNAME = os.environ.get("GH_USERNAME", "AmmarYasser455")
MAX_LINES = int(os.environ.get("MAX_LINES", "5"))

SUPPORTED_EVENTS = {
    "PushEvent",
    "PullRequestEvent",
    "IssuesEvent",
    "IssueCommentEvent",
    "CreateEvent",
    "ReleaseEvent",
    "ForkEvent",
    "WatchEvent",
    "DeleteEvent",
}


def fetch_events():
    """Fetch recent public events from GitHub API."""
    result = subprocess.run(
        [
            "gh",
            "api",
            f"users/{USERNAME}/events/public?per_page=100",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error fetching events: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def format_event(event):
    """Format a single GitHub event into a markdown line."""
    repo = event["repo"]["name"]
    etype = event["type"]
    payload = event.get("payload", {})
    repo_link = f"[{repo}](https://github.com/{repo})"

    if etype == "PushEvent":
        commits = payload.get("commits", [])
        count = (
            len(commits)
            if commits
            else payload.get("distinct_size", payload.get("size", 0))
        )
        if count == 0:
            return None
        word = "commit" if count == 1 else "commits"
        branch = (payload.get("ref") or "").replace("refs/heads/", "")
        return f"⬆️ Pushed {count} {word} to `{branch}` in {repo_link}"

    if etype == "PullRequestEvent":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        num = pr.get("number", "")
        pr_link = f"[#{num}](https://github.com/{repo}/pull/{num})"
        if action == "opened":
            return f"💪 Opened PR {pr_link} in {repo_link}"
        if action == "closed" and pr.get("merged"):
            return f"🎉 Merged PR {pr_link} in {repo_link}"
        if action == "closed":
            return f"❌ Closed PR {pr_link} in {repo_link}"
        return None

    if etype == "IssuesEvent":
        action = payload.get("action", "")
        num = payload.get("issue", {}).get("number", "")
        emojis = {"opened": "❗", "closed": "🔒", "reopened": "🔓"}
        emoji = emojis.get(action, "ℹ️")
        issue_link = f"[#{num}](https://github.com/{repo}/issues/{num})"
        return f"{emoji} {action.capitalize()} issue {issue_link} in {repo_link}"

    if etype == "IssueCommentEvent":
        num = payload.get("issue", {}).get("number", "")
        url = payload.get("comment", {}).get("html_url", "")
        return f"🗣 Commented on [#{num}]({url}) in {repo_link}"

    if etype == "CreateEvent":
        ref_type = payload.get("ref_type", "")
        ref = payload.get("ref", "")
        if ref_type == "repository":
            return f"🆕 Created repository {repo_link}"
        if ref_type == "branch":
            return f"🌿 Created branch `{ref}` in {repo_link}"
        if ref_type == "tag":
            return f"🏷️ Created tag `{ref}` in {repo_link}"
        return None

    if etype == "ReleaseEvent":
        release = payload.get("release", {})
        tag = release.get("tag_name", "")
        url = release.get("html_url", "")
        return f"🚀 Released [{tag}]({url}) in {repo_link}"

    if etype == "ForkEvent":
        forkee = payload.get("forkee", {}).get("full_name", "")
        return f"🍴 Forked {repo_link} to [{forkee}](https://github.com/{forkee})"

    if etype == "WatchEvent":
        return f"⭐ Starred {repo_link}"

    if etype == "DeleteEvent":
        ref_type = payload.get("ref_type", "")
        ref = payload.get("ref", "")
        return f"🗑️ Deleted {ref_type} `{ref}` in {repo_link}"

    return None


def main():
    events = fetch_events()

    lines = []
    seen = set()

    for event in events:
        if event["type"] not in SUPPORTED_EVENTS:
            continue

        line = format_event(event)
        if line is None:
            continue

        # Deduplicate identical lines
        if line in seen:
            continue

        lines.append(line)
        seen.add(line)

        if len(lines) >= MAX_LINES:
            break

    if not lines:
        print("No recent activity found")
        return

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    START = "<!--START_SECTION:activity-->"
    END = "<!--END_SECTION:activity-->"

    start_idx = content.find(START)
    end_idx = content.find(END)

    if start_idx == -1 or end_idx == -1:
        print("Activity section markers not found in README.md")
        return

    activity = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines))
    new_content = (
        content[: start_idx + len(START)]
        + "\n"
        + activity
        + "\n"
        + content[end_idx:]
    )

    if new_content == content:
        print("No changes detected")
        return

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated README with {len(lines)} activity items")


if __name__ == "__main__":
    main()
