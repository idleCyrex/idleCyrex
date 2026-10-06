#!/usr/bin/env python3
"""
Render data/contributions.json as a GitHub-style contribution calendar in
phosphor green: 53 weeks x 7 days of rounded boxes, revealed once by a scan
beam sweeping left to right (cells pop in behind it, then everything holds),
plus a Less->More legend and a stats footer.

    python scripts/render_heatmap_svg.py [output.svg]

Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import sys

import theme as t

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(t.ASSETS, "contrib-heatmap.svg")

CELL, GAP = 12, 3
STEP = CELL + GAP
PAD = 22
LEFT_LABEL_W = 30
TOP_LABEL_H = 22
FOOTER_H = 92

SWEEP = 2.6       # seconds for the beam to cross the grid
CELL_DUR = 0.35


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
    art_w = len(grid) * STEP - GAP
    w = PAD + LEFT_LABEL_W + art_w + PAD
    h = t.TITLEBAR_H + TOP_LABEL_H + 7 * STEP + FOOTER_H
    grid_left = PAD + LEFT_LABEL_W
    grid_top = t.TITLEBAR_H + TOP_LABEL_H

    css = (f'.c{{opacity:0;transform-box:fill-box;transform-origin:center;'
           f'animation:pop {CELL_DUR}s ease-out both}}'
           '@keyframes pop{0%{opacity:0;transform:scale(.3)}60%{opacity:1;transform:scale(1.15)}'
           '100%{opacity:1;transform:scale(1)}}'
           f'.beam{{animation:sweep {SWEEP}s linear both}}'
           f'@keyframes sweep{{0%{{transform:translateX(0);opacity:.9}}'
           f'95%{{opacity:.9}}100%{{transform:translateX({art_w + 6}px);opacity:0}}}}'
           '.f{opacity:0;animation:fade .6s ease-out both}'
           '@keyframes fade{to{opacity:1}}')
    parts = t.open_svg(w, h, f"{t.PROMPT}: ~$ git log --graph --since=1.year", css)

    # month labels over the first column that starts a month
    seen = set()
    for ci, column in enumerate(grid):
        first = next((c for c in column if c), None)
        date = datetime.date.fromisoformat(first["date"])
        if date.day <= 7 and (date.year, date.month) not in seen:
            seen.add((date.year, date.month))
            parts.append(f'<text x="{grid_left + ci * STEP}" y="{t.TITLEBAR_H + 16}" '
                         f'fill="{t.DIM}" font-size="10">{date.strftime("%b").lower()}</text>')
    for ri, name in [(1, "mon"), (3, "wed"), (5, "fri")]:
        parts.append(f'<text x="{PAD}" y="{grid_top + ri * STEP + CELL * 0.8:.1f}" '
                     f'fill="{t.DIM}" font-size="9">{name}</text>')

    parts.append('<g filter="url(#glow)">')
    for ci, column in enumerate(grid):
        delay = SWEEP * ci / len(grid)
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            n = cell["count"]
            parts.append(
                f'<rect class="c" x="{grid_left + ci * STEP}" y="{grid_top + ri * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2.5" fill="{t.LEVELS[cell["level"]]}" '
                f'style="animation-delay:{delay + ri * 0.02:.3f}s">'
                f'<title>{cell["date"]}: {n} contribution{"" if n == 1 else "s"}</title></rect>'
            )
    parts.append('</g>')

    # the scan beam that "draws" the grid
    parts.append(f'<rect class="beam" x="{grid_left - 4}" y="{grid_top - 4}" width="3" '
                 f'height="{7 * STEP + 5}" rx="1.5" fill="{t.MINT}" filter="url(#glow)"/>')

    # legend
    leg_y = grid_top + 7 * STEP + 4
    lx = w - PAD - len(t.LEVELS) * STEP - 34
    parts.append(f'<text x="{lx - 6}" y="{leg_y + 9}" fill="{t.DIM}" font-size="10" text-anchor="end">less</text>')
    for i, color in enumerate(t.LEVELS):
        parts.append(f'<rect x="{lx + i * STEP}" y="{leg_y}" width="{CELL - 1}" height="{CELL - 1}" '
                     f'rx="2.2" fill="{color}"/>')
    parts.append(f'<text x="{lx + len(t.LEVELS) * STEP + 4}" y="{leg_y + 9}" fill="{t.DIM}" font-size="10">more</text>')

    sep_y = leg_y + CELL + 12
    parts.append(f'<line x1="0" y1="{sep_y}" x2="{w}" y2="{sep_y}" stroke="{t.FRAME}" stroke-opacity="0.6"/>')

    cur, lng, best = data["current_streak"], data["longest_streak"], data["best_day"]
    rng = data["range"]
    footer = f'<g class="f" style="animation-delay:{SWEEP:.1f}s">'
    y1, y2 = sep_y + 26, sep_y + 50
    footer += (f'<text x="{PAD}" y="{y1}" font-size="13" fill="{t.DIM}">&gt; '
               f'<tspan fill="{t.GREEN}" font-weight="700">{data["total_contributions"]:,}</tspan>'
               f' contributions in the last year</text>')
    footer += (f'<text x="{w - PAD}" y="{y1}" font-size="12" fill="{t.DIM}" text-anchor="end">'
               f'{rng["start"]} &#8594; {rng["end"]}</text>')
    footer += (f'<text x="{PAD}" y="{y2}" font-size="13" fill="{t.DIM}">&gt; streak '
               f'<tspan fill="{t.MINT}" font-weight="700">{cur["length"]}d</tspan>'
               f'  ·  longest <tspan fill="{t.MINT}" font-weight="700">{lng["length"]}d</tspan></text>')
    footer += (f'<text x="{w - PAD}" y="{y2}" font-size="12" fill="{t.DIM}" text-anchor="end">'
               f'best day <tspan fill="{t.AMBER}" font-weight="700">{best["count"]}</tspan> on {best["date"]}</text>')
    parts.append(footer + '</g>')

    parts += t.close_svg(w, h)
    t.write(OUT, parts)


if __name__ == "__main__":
    with open(t.DATA_PATH) as f:
        render(json.load(f))
