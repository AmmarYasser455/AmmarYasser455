"""Draw the "Languages by commit" chart for the profile README.

Counts GH_USERNAME's commits over the last 12 months in public repositories (forks and
EXCLUDE_REPOS left out), attributes each repository's commits to its primary language as
GitHub reports it, and writes two SVGs: assets/languages.svg (light) and
assets/languages-dark.svg (dark). Files are only rewritten when the numbers change.

Colours are the OpenTerra palette, chosen so neighbouring languages never share a hue.
"""

import html
import json
import os
import subprocess
import sys
from collections import Counter

USERNAME = os.environ.get("GH_USERNAME", "AmmarYasser455")
EXCLUDE = {r.strip().lower() for r in os.environ.get("EXCLUDE_REPOS", "").split(",") if r.strip()}
TOP = 5
COLOURS = ["#F2552C", "#8B6CF6", "#14A39A", "#E0A21B", "#5B8DEF", "#9AA3AF"]  # last one is "Other"
THEMES = {
    "assets/languages.svg": {"text": "#121417", "muted": "#5F6670", "track": "#E7E2D8"},
    "assets/languages-dark.svg": {"text": "#F3EEE4", "muted": "#A9A39A", "track": "#2A2C31"},
}
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  commitContributionsByRepository(maxRepositories: 100) {
    repository { nameWithOwner isPrivate isFork primaryLanguage { name } }
    contributions { totalCount } } } } }"""


def fetch():
    res = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={USERNAME}"],
                         capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(f"GraphQL failed: {res.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(res.stdout)["data"]["user"]["contributionsCollection"]["commitContributionsByRepository"]


def tally(rows):
    out = Counter()
    for row in rows:
        repo = row["repository"]
        lang = (repo.get("primaryLanguage") or {}).get("name")
        if repo["isPrivate"] or repo["isFork"] or not lang or repo["nameWithOwner"].lower() in EXCLUDE:
            continue
        out[lang] += row["contributions"]["totalCount"]
    return out


def series(counts):
    top = counts.most_common(TOP)
    rest = sum(counts.values()) - sum(n for _, n in top)
    items = [(name, n, COLOURS[i]) for i, (name, n) in enumerate(top)]
    if rest:
        items.append(("Other", rest, COLOURS[-1]))
    return items


def svg(items, theme):
    w, pad = 460, 22
    total = sum(n for _, n, _ in items) or 1
    rows = len(items)
    h = 104 + rows * 26
    font = "font-family=\"'Segoe UI',Helvetica,Arial,sans-serif\""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="Languages by commit">',
           f'<text x="{pad}" y="34" {font} font-size="17" font-weight="600" fill="{theme["text"]}">Languages by commit</text>',
           f'<text x="{pad}" y="54" {font} font-size="11.5" fill="{theme["muted"]}">Public repositories, last 12 months · '
           f'{total} commits</text>']
    # one stacked bar, then a legend row per language
    bar_w, y = w - 2 * pad, 70
    out.append(f'<clipPath id="r"><rect x="{pad}" y="{y}" width="{bar_w}" height="12" rx="6"/></clipPath>')
    out.append(f'<g clip-path="url(#r)"><rect x="{pad}" y="{y}" width="{bar_w}" height="12" fill="{theme["track"]}"/>')
    x = pad
    for _name, n, colour in items:
        seg = bar_w * n / total
        out.append(f'<rect x="{x:.2f}" y="{y}" width="{seg + 0.5:.2f}" height="12" fill="{colour}"/>')
        x += seg
    out.append("</g>")
    for i, (name, n, colour) in enumerate(items):
        ry = 106 + i * 26
        pct = 100 * n / total
        out.append(f'<rect x="{pad}" y="{ry - 10}" width="11" height="11" rx="3" fill="{colour}"/>')
        out.append(f'<text x="{pad + 20}" y="{ry}" {font} font-size="13" fill="{theme["text"]}">{html.escape(name)}</text>')
        out.append(f'<text x="{w - pad - 92}" y="{ry}" {font} font-size="13" font-weight="600" text-anchor="end" '
                   f'fill="{theme["text"]}">{pct:.1f}%</text>')
        out.append(f'<text x="{w - pad}" y="{ry}" {font} font-size="11.5" text-anchor="end" '
                   f'fill="{theme["muted"]}">{n} commits</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    items = series(tally(fetch()))
    if not items:
        print("No public commits with a known language; charts left unchanged.")
        return
    os.makedirs("assets", exist_ok=True)
    for path, theme in THEMES.items():
        text = svg(items, theme)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if text != old:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            print(f"Updated {path}")
    print(", ".join(f"{name} {n}" for name, n, _ in items))


if __name__ == "__main__":
    main()
