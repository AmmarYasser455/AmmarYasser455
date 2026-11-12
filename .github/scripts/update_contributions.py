"""Update the open-source contributions section of README.md.

Lists pull requests authored by GH_USERNAME in repositories owned by others,
split into merged and in-review, using the GitHub search API through `gh`.
Repositories in EXCLUDE_REPOS (comma-separated owner/name) are left out.
"""

import datetime as dt
import json
import os
import subprocess
import sys

USERNAME = os.environ.get("GH_USERNAME", "AmmarYasser455")
EXCLUDE = {r.strip().lower() for r in os.environ.get("EXCLUDE_REPOS", "").split(",") if r.strip()}
MAX_ROWS = int(os.environ.get("MAX_ROWS", "8"))
START = "<!--START_SECTION:contributions-->"
END = "<!--END_SECTION:contributions-->"


def search(query):
    items, page = [], 1
    while True:
        res = subprocess.run(
            ["gh", "api", "-X", "GET", "search/issues", "-f", f"q={query}",
             "-f", "per_page=100", "-f", f"page={page}"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if res.returncode != 0:
            print(f"Search failed: {res.stderr}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(res.stdout)
        items += data.get("items", [])
        if len(items) >= data.get("total_count", 0) or not data.get("items") or page >= 10:
            return items
        page += 1


def repo_of(item):
    return item["repository_url"].split("/repos/", 1)[1]


def cell(text):
    return text.replace("|", "\\|").replace("\n", " ").strip()


def month(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %Y")


def table(rows, when_label):
    out = [f"| Project | Pull request | {when_label} |", "|---|---|---|"]
    for repo, item, when in rows[:MAX_ROWS]:
        out.append(
            f"| [{repo}](https://github.com/{repo}) "
            f"| [#{item['number']}]({item['html_url']}) {cell(item['title'])} "
            f"| {month(when)} |"
        )
    if len(rows) > MAX_ROWS:
        out.append(f"| | *and {len(rows) - MAX_ROWS} more* | |")
    return "\n".join(out)


def main():
    items = search(f"author:{USERNAME} type:pr -user:{USERNAME}")
    merged, review = [], []
    for it in items:
        repo = repo_of(it)
        if repo.lower() in EXCLUDE:
            continue
        merged_at = (it.get("pull_request") or {}).get("merged_at")
        if merged_at:
            merged.append((repo, it, merged_at))
        elif it["state"] == "open":
            review.append((repo, it, it["created_at"]))
    merged.sort(key=lambda r: r[2], reverse=True)
    review.sort(key=lambda r: r[2], reverse=True)
    projects = len({r for r, _, _ in merged + review})
    today = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")

    parts = [
        f"**{len(merged)} merged** · **{len(review)} in review** · "
        f"**{projects} projects** <sub>(updated {today})</sub>",
        "",
    ]
    if merged:
        parts += ["#### ✅ Merged", "", table(merged, "Merged"), ""]
    if review:
        parts += ["#### 🔍 In review", "", table(review, "Opened"), ""]
    section = "\n".join(parts).rstrip()

    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    a, b = content.find(START), content.find(END)
    if a == -1 or b == -1:
        print("Contributions markers not found in README.md")
        return
    new = content[: a + len(START)] + "\n" + section + "\n" + content[b:]
    if new == content:
        print("No changes")
        return
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new)
    print(f"Contributions: {len(merged)} merged, {len(review)} in review")


if __name__ == "__main__":
    main()
