"""
Fetches your currently pinned GitHub repos via the GraphQL API
and rewrites the Featured Projects section in README.md.

The README must contain these two marker comments:
    <!-- PINNED-REPOS-START -->
    <!-- PINNED-REPOS-END -->
Everything between them gets replaced on every run.
"""

import os
import sys
import requests

# ── Config ────────────────────────────────────────────────────────────────────

GITHUB_USERNAME = "TejaSai22"
README_PATH     = "README.md"
MARKER_START    = "<!-- PINNED-REPOS-START -->"
MARKER_END      = "<!-- PINNED-REPOS-END -->"

# Map primary language names → shields.io badge colors
LANG_COLORS = {
    "Python":     "3776AB",
    "TypeScript": "3178C6",
    "JavaScript": "F7DF1E",
    "Java":       "007396",
    "Go":         "00ADD8",
    "Rust":       "DEA584",
    "C++":        "00599C",
    "C":          "A8B9CC",
    "Shell":      "4EAA25",
    "HTML":       "E34F26",
    "CSS":        "1572B6",
    "Jupyter Notebook": "F37626",
}
LANG_TEXT_COLORS = {
    "JavaScript": "black",
}
DEFAULT_COLOR = "58a6ff"

# ── GraphQL query ─────────────────────────────────────────────────────────────

QUERY = """
{
  user(login: "%s") {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          forkCount
          primaryLanguage { name color }
          repositoryTopics(first: 5) {
            nodes { topic { name } }
          }
        }
      }
    }
  }
}
""" % GITHUB_USERNAME

# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_pinned_repos(token: str) -> list[dict]:
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        print("GraphQL errors:", data["errors"], file=sys.stderr)
        sys.exit(1)

    return data["data"]["user"]["pinnedItems"]["nodes"]

# ── Markdown builder ──────────────────────────────────────────────────────────

def lang_badge(lang_name: str) -> str:
    color     = LANG_COLORS.get(lang_name, DEFAULT_COLOR)
    text_color = LANG_TEXT_COLORS.get(lang_name, "white")
    label     = lang_name.replace(" ", "_").replace("+", "%2B")
    return (
        f'<img src="https://img.shields.io/badge/{label}-{color}'
        f'?style=flat-square&logoColor={text_color}"/>'
    )

def star_badge(count: int) -> str:
    return (
        f'<img src="https://img.shields.io/badge/⭐_Stars-{count}'
        f'-yellow?style=flat-square"/>'
    )

def fork_badge(count: int) -> str:
    return (
        f'<img src="https://img.shields.io/badge/🍴_Forks-{count}'
        f'-blue?style=flat-square"/>'
    )

def build_projects_section(repos: list[dict]) -> str:
    if not repos:
        return "_No pinned repositories found._\n"

    # Pair repos into rows of 2
    rows = []
    for i in range(0, len(repos), 2):
        pair = repos[i : i + 2]
        cells = []
        for repo in pair:
            name        = repo["name"]
            url         = repo["url"]
            description = repo.get("description") or "_No description provided._"
            stars       = repo.get("stargazerCount", 0)
            forks       = repo.get("forkCount", 0)
            lang        = repo.get("primaryLanguage")
            topics      = [
                n["topic"]["name"]
                for n in repo.get("repositoryTopics", {}).get("nodes", [])
            ]

            # Badge row: language first, then stars/forks if non-zero
            badges = []
            if lang:
                badges.append(lang_badge(lang["name"]))
            if stars > 0:
                badges.append(star_badge(stars))
            if forks > 0:
                badges.append(fork_badge(forks))
            # Topics as plain text tags (subtle, not overwhelming)
            topic_line = ""
            if topics:
                topic_line = (
                    "\n      <br/><sub>"
                    + " &nbsp;·&nbsp; ".join(f"`{t}`" for t in topics[:4])
                    + "</sub>"
                )

            badge_line = "\n      ".join(badges)

            cells.append(
                f"""    <td width="50%" valign="top">
      <h3>🔗 <a href="{url}">{name}</a></h3>
      <p>{description}{topic_line}</p>
      {badge_line}
    </td>"""
            )

        # If odd number of repos, pad with empty cell
        if len(cells) == 1:
            cells.append('    <td width="50%"></td>')

        rows.append("  <tr>\n" + "\n".join(cells) + "\n  </tr>")

    table = "<table>\n" + "\n".join(rows) + "\n</table>"
    return table + "\n"

# ── README patcher ────────────────────────────────────────────────────────────

def patch_readme(new_section: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_START not in content or MARKER_END not in content:
        print(
            f"ERROR: Could not find markers '{MARKER_START}' / '{MARKER_END}' in {README_PATH}.",
            file=sys.stderr,
        )
        sys.exit(1)

    before = content.split(MARKER_START)[0]
    after  = content.split(MARKER_END)[1]
    updated = f"{before}{MARKER_START}\n{new_section}{MARKER_END}{after}"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print("✅ README.md updated successfully.")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching pinned repos for @{GITHUB_USERNAME} …")
    repos = fetch_pinned_repos(token)
    print(f"Found {len(repos)} pinned repo(s): {[r['name'] for r in repos]}")

    section = build_projects_section(repos)
    patch_readme(section)

if __name__ == "__main__":
    main()
