#!/usr/bin/env python3
"""
Render data/contributions.json as a compact contribution calendar SVG
(53 weeks x 7 days) in the README's green palette. Columns fade in left to
right once, then hold.

    python scripts/render_heatmap_svg.py [output.svg]

Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_PATH = os.path.join(ROOT, "data", "contributions.json")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "contrib-heatmap.svg")

BG = "#020a05"
BORDER = "#123d22"
MUTED = "#2f9d5b"
TEXT = "#c9ffdc"
LEVELS = ["#0b1f12", "#0f4d27", "#178a40", "#1fc458", "#28ff6a"]
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

CELL, GAP = 11, 3
STEP = CELL + GAP
PAD = 16
LEFT_LABEL_W = 26
TOP_LABEL_H = 16
FOOTER_H = 30


def build_grid(days):
    """Columns of 7 (Sun..Sat), None for days outside the range."""
    grid, col = [], []
    for d in days:
        weekday = (datetime.date.fromisoformat(d["date"]).weekday() + 1) % 7  # sunday=0
        while len(col) < weekday:
            col.append(None)
        col.append(d)
        if len(col) == 7:
            grid.append(col)
            col = []
    if col:
        grid.append(col + [None] * (7 - len(col)))
    return grid


def render(data):
    grid = build_grid(data["days"])
    grid_left = PAD + LEFT_LABEL_W
    grid_top = PAD + TOP_LABEL_H
    w = grid_left + len(grid) * STEP - GAP + PAD
    h = grid_top + 7 * STEP - GAP + FOOTER_H + PAD // 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT}" font-size="10">',
        '<style>.c{opacity:0;animation:in .4s ease-out both}@keyframes in{to{opacity:1}}'
        '@media (prefers-reduced-motion: reduce){.c{animation:none;opacity:1}}</style>',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
    ]

    seen = set()
    for ci, column in enumerate(grid):
        date = datetime.date.fromisoformat(next(c for c in column if c)["date"])
        if date.day <= 7 and (date.year, date.month) not in seen:
            seen.add((date.year, date.month))
            parts.append(f'<text x="{grid_left + ci * STEP}" y="{PAD + 8}" fill="{MUTED}">'
                         f'{date.strftime("%b")}</text>')
    for ri, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(f'<text x="{PAD}" y="{grid_top + ri * STEP + CELL - 2}" fill="{MUTED}" '
                     f'font-size="9">{name}</text>')

    for ci, column in enumerate(grid):
        delay = 1.5 * ci / len(grid)
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            n = cell["count"]
            parts.append(
                f'<rect class="c" x="{grid_left + ci * STEP}" y="{grid_top + ri * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2" fill="{LEVELS[cell["level"]]}" '
                f'style="animation-delay:{delay:.2f}s">'
                f'<title>{cell["date"]}: {n} contribution{"" if n == 1 else "s"}</title></rect>'
            )

    foot_y = grid_top + 7 * STEP - GAP + 20
    longest = data["longest_streak"]["length"]
    parts.append(f'<text x="{grid_left}" y="{foot_y}" fill="{MUTED}" font-size="11">'
                 f'<tspan fill="{TEXT}">{data["total_contributions"]:,}</tspan> contributions in the last year'
                 f' · longest streak <tspan fill="{TEXT}">{longest}</tspan> day{"" if longest == 1 else "s"}</text>')

    # Less [][][][][] More, right-aligned with the grid
    lx = w - PAD - 26 - len(LEVELS) * STEP
    parts.append(f'<text x="{lx - 5}" y="{foot_y}" fill="{MUTED}" text-anchor="end">Less</text>')
    for i, color in enumerate(LEVELS):
        parts.append(f'<rect x="{lx + i * STEP}" y="{foot_y - 9}" width="{CELL - 1}" height="{CELL - 1}" '
                     f'rx="2" fill="{color}"/>')
    parts.append(f'<text x="{lx + len(LEVELS) * STEP + 2}" y="{foot_y}" fill="{MUTED}">More</text>')

    parts.append('</svg>')
    svg = "".join(parts)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    with open(DATA_PATH) as f:
        render(json.load(f))
