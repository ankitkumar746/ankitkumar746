"""
Generates dark_mode.svg and light_mode.svg — a retro terminal-style
GitHub stats card, in the spirit of Andrew6rant's neofetch profile.

Run manually:
    GH_USERNAME=yourname GITHUB_TOKEN=ghp_xxx python today.py

In CI, GITHUB_TOKEN is provided automatically by GitHub Actions.
"""

import os
from io import BytesIO

import requests
from PIL import Image

USERNAME = os.environ.get("GH_USERNAME", "ankitkumar746")
TOKEN = os.environ.get("GITHUB_TOKEN")

API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": f"{USERNAME}-profile-svg"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

ASCII_CHARS = "@%#*+=-:. "


def fetch_user():
    r = requests.get(f"{API}/users/{USERNAME}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_repos():
    repos, page = [], 1
    while True:
        r = requests.get(
            f"{API}/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=15,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def compute_stats(user, repos):
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)

    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    top_langs = ", ".join(sorted(langs, key=langs.get, reverse=True)[:4]) or "N/A"

    return {
        "name": user.get("name") or USERNAME,
        "location": user.get("location") or "N/A",
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "stars": stars,
        "forks": forks,
        "languages": top_langs,
        "created": (user.get("created_at") or "")[:10],
    }


def image_to_ascii(avatar_url, cols=34, rows=17):
    resp = requests.get(avatar_url, timeout=15)
    img = Image.open(BytesIO(resp.content)).convert("L").resize((cols, rows))
    pixels = list(img.getdata())
    rows_out = []
    for i in range(rows):
        chunk = pixels[i * cols:(i + 1) * cols]
        row = "".join(ASCII_CHARS[p * (len(ASCII_CHARS) - 1) // 255] for p in chunk)
        rows_out.append(row)
    return rows_out


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(ascii_rows, stats, theme="dark"):
    if theme == "dark":
        bg, fg, accent, dim, ascii_color = "#0d1117", "#c9d1d9", "#58a6ff", "#8b949e", "#39d353"
    else:
        bg, fg, accent, dim, ascii_color = "#ffffff", "#24292f", "#0969da", "#57606a", "#1a7f37"

    font = "font-family='Consolas, Menlo, monospace' font-size='13px'"
    line_height = 16

    ascii_svg = []
    for i, row in enumerate(ascii_rows):
        y = 30 + i * 13
        ascii_svg.append(
            f"<text x='20' y='{y}' fill='{ascii_color}' font-family='monospace' "
            f"font-size='11px' xml:space='preserve'>{esc(row)}</text>"
        )

    handle = stats["name"].lower().replace(" ", "")
    info_lines = [
        ("title", f"{handle}@github", None),
        ("sep", "-" * 30, None),
        ("kv", "Role", "Site Reliability / Infra Engineer"),
        ("kv", "Location", stats["location"]),
        ("kv", "Joined", stats["created"]),
        ("kv", "Languages", stats["languages"]),
        ("blank", "", None),
        ("kv", "Focus.Now", "Reliability & security at scale"),
        ("kv", "Focus.Next", "AI infra, GPU workload optimisation"),
        ("blank", "", None),
        ("title", "- GitHub Stats", None),
        ("sep", "-" * 30, None),
    ]

    text_x = 340
    y = 30
    right_svg = []
    for kind, key, value in info_lines:
        if kind == "title":
            right_svg.append(f"<text x='{text_x}' y='{y}' fill='{accent}' {font} font-weight='bold'>{esc(key)}</text>")
        elif kind == "sep":
            right_svg.append(f"<text x='{text_x}' y='{y}' fill='{dim}' {font}>{esc(key)}</text>")
        elif kind == "kv":
            right_svg.append(
                f"<text x='{text_x}' y='{y}'>"
                f"<tspan fill='{accent}' {font}>{esc(key)}: </tspan>"
                f"<tspan fill='{fg}' {font}>{esc(value)}</tspan></text>"
            )
        y += line_height

    stat_rows = [
        ("Repos", stats["public_repos"], "Followers", stats["followers"]),
        ("Following", stats["following"], "Stars", stats["stars"]),
        ("Forks", stats["forks"], "", ""),
    ]
    for lk, lv, rk, rv in stat_rows:
        line = f"<tspan fill='{accent}' {font}>{esc(lk)}: </tspan><tspan fill='{fg}' {font}>{esc(lv)}</tspan>"
        if rk:
            line += (
                f"<tspan fill='{fg}' {font}>   |   </tspan>"
                f"<tspan fill='{accent}' {font}>{esc(rk)}: </tspan><tspan fill='{fg}' {font}>{esc(rv)}</tspan>"
            )
        right_svg.append(f"<text x='{text_x}' y='{y}'>{line}</text>")
        y += line_height

    height = max(30 + len(ascii_rows) * 13 + 20, y + 20)

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='760' height='{height}' "
        f"viewBox='0 0 760 {height}'>"
        f"<rect width='760' height='{height}' rx='10' fill='{bg}'/>"
        f"{''.join(ascii_svg)}{''.join(right_svg)}"
        f"</svg>"
    )


def main():
    user = fetch_user()
    repos = fetch_repos()
    stats = compute_stats(user, repos)
    ascii_rows = image_to_ascii(user["avatar_url"])

    with open("dark_mode.svg", "w") as f:
        f.write(render_svg(ascii_rows, stats, theme="dark"))
    with open("light_mode.svg", "w") as f:
        f.write(render_svg(ascii_rows, stats, theme="light"))

    print(f"Generated dark_mode.svg and light_mode.svg for {USERNAME}")


if __name__ == "__main__":
    main()