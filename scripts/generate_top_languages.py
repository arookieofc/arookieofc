#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top Languages 卡片生成器：github-readme-stats compact 布局的深色卡片。
顶部一条堆叠进度条，下方圆点 + 名称 + 占比两列图例。

设计用于 GitHub Actions（也可本地运行），仅 Python 标准库。
fork / archived 仓库自动排除。

环境变量:
  GITHUB_TOKEN  可选。Actions 内用 secrets.GITHUB_TOKEN；本地缺省时尝试 `gh auth token`
  GITHUB_USER   用户名，默认 arookieofc
  OUTPUT_PATH   输出文件名，默认 assets/top-languages.svg
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape


USER = os.environ.get("GITHUB_USER", "arookieofc")
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", ROOT / "assets" / "top-languages.svg"))

LANG_COLORS = {
    "C++": "#f34b7d",
    "C": "#555555",
    "Rust": "#dea584",
    "Java": "#b07219",
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Vue": "#41b883",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Go": "#00ADD8",
    "Kotlin": "#A97BFF",
    "C#": "#178600",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "Dockerfile": "#384d54",
    "CMake": "#DA3434",
    "Lua": "#000080",
    "SQL": "#e38c00",
}

TOP_N = 6
WIDTH = 500
PAD = 30
BG = "#141321"
BORDER = "#fe428e"
TITLE = "#2f81f7"
TRACK = "#2d2d44"
LEGEND = "#a9fef7"


def token():
    value = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if value:
        return value
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return ""


TOKEN = token()


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-top-languages",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 + attempt * 3)
                continue
            raise


def collect_languages():
    languages = {}
    page = 1
    while True:
        batch = request_json(
            f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner&sort=updated"
        )
        if not batch:
            break
        for repo in batch:
            if repo.get("fork") or repo.get("archived"):
                continue
            for name, size in request_json(
                f"https://api.github.com/repos/{USER}/{repo['name']}/languages"
            ).items():
                languages[name] = languages.get(name, 0) + int(size)
        page += 1
    return languages


def render_svg(languages):
    total_all = sum(languages.values()) or 1
    top = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:TOP_N]
    top_total = sum(size for _, size in top) or 1

    bar_x = PAD
    bar_w = WIDTH - PAD * 2
    bar_y = 52
    bar_h = 8

    # 堆叠进度条：圆角裁剪，方便首尾自然圆角
    segs = []
    x = bar_x
    for name, size in top:
        w = bar_w * size / top_total
        segs.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="{bar_h}" fill="{LANG_COLORS.get(name, "#64748b")}"/>')
        x += w

    # 图例：两列
    legend_y0 = 88
    row_h = 26
    col_x = [PAD, WIDTH // 2 + 10]
    legend = []
    for i, (name, size) in enumerate(top):
        pct = size / total_all * 100
        cx = col_x[i % 2]
        cy = legend_y0 + (i // 2) * row_h
        color = LANG_COLORS.get(name, "#64748b")
        legend.append(f'<circle cx="{cx}" cy="{cy - 4}" r="6" fill="{color}"/>')
        legend.append(f'<text x="{cx + 14}" y="{cy}" fill="{LEGEND}" font-family="Segoe UI, Arial, sans-serif" font-size="13">{escape(name)} {pct:.2f}%</text>')

    height = legend_y0 + ((len(top) + 1) // 2 - 1) * row_h + 28

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(USER)} most used languages">
  <defs>
    <clipPath id="langbar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h // 2}"/></clipPath>
  </defs>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="4.5" fill="{BG}" stroke="{BORDER}" stroke-opacity="0.6"/>
  <text x="{PAD}" y="32" fill="{TITLE}" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="700">Most Used Languages</text>
  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h // 2}" fill="{TRACK}"/>
  <g clip-path="url(#langbar)">
    {"".join(segs)}
  </g>
  {"".join(legend)}
</svg>'''


def main():
    languages = collect_languages()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_svg(languages), encoding="utf-8")
    top = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:TOP_N]
    print(f"[top-languages] {OUTPUT_PATH} 生成完毕")
    print(json.dumps({k: v for k, v in top}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"failed to generate top languages: {exc}", file=sys.stderr)
        raise
