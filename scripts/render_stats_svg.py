#!/usr/bin/env python3
"""
Render the streak / numbers card from data/contributions.json as a terminal
window that sits beside ascii-portrait.svg (same 840 x 880 canvas, so the two
line up when the README shows them at equal widths).

Six stat tiles slide in and their numbers count up to the real value, then a
contributions-per-month bar chart grows in underneath. The count-up is a stack
of pre-rendered frames toggled with SMIL <set>, since GitHub never runs JS
inside <img> SVGs.

    python scripts/render_stats_svg.py [output.svg]

Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import sys

import theme as t

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(t.ASSETS, "stats.svg")

W, H = 840, 880
PAD = 20
COLS, ROWS = 2, 3
GAP = 16
TILE_W = (W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H = 150
TILES_TOP = t.TITLEBAR_H + PAD + 4
CHART_TOP = TILES_TOP + ROWS * TILE_H + (ROWS - 1) * GAP + GAP

TILE_STAGGER = 0.15
SLIDE_DUR = 0.45
COUNT_DUR = 1.2
FRAMES = 16
BAR_START = TILE_STAGGER * COLS * ROWS + 0.4
BAR_STAGGER = 0.06
BAR_DUR = 0.6


def short(d):
    return datetime.date.fromisoformat(d).strftime("%b %-d").lower()


def span(s):
    return f'{short(s["start"])} → {short(s["end"])}' if s["length"] else "start one today"


def fmt(v, like):
    return f"{v:,.1f}" if isinstance(like, float) else f"{int(round(v)):,}"


def render(data):
    cur, lng, best = data["current_streak"], data["longest_streak"], data["best_day"]
    n_days = len(data["days"])
    # (command, value, suffix, caption, accent)
    tiles = [
        ("streak --current", cur["length"], " days", span(cur), t.GREEN),
        ("streak --longest", lng["length"], " days", span(lng), t.MINT),
        ("git rev-list --count", data["total_contributions"], "", "contributions, last 365d", t.GREEN),
        ("uptime", data["active_days"], f" / {n_days}",
         f'days active · {data["active_days"] / n_days:.0%} of the year', t.MINT),
        ("peak --day", best["count"], "", f'commits on {short(best["date"])}', t.AMBER),
        ("avg --per-active-day", data["avg_per_active_day"], "",
         f'busiest day: {data.get("busiest_weekday", "?").lower()}', t.MINT),
    ]

    css = (f'.t{{opacity:0;animation:in {SLIDE_DUR}s ease-out both}}'
           '@keyframes in{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}'
           f'.b{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);'
           f'animation:grow {BAR_DUR}s ease-out both}}'
           '@keyframes grow{to{transform:scaleY(1)}}')
    parts = t.open_svg(W, H, f"{t.PROMPT}: ~$ ./stats.sh", css)

    for i, (label, value, suffix, caption, accent) in enumerate(tiles):
        x = PAD + (i % COLS) * (TILE_W + GAP)
        y = TILES_TOP + (i // COLS) * (TILE_H + GAP)
        start = i * TILE_STAGGER
        count_start = start + SLIDE_DUR * 0.6

        parts.append(f'<g class="t" style="animation-delay:{start:.2f}s">')
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="10" '
                     f'fill="{t.TILE}" stroke="{t.FRAME}"/>')
        parts.append(f'<text x="{x + 24:.1f}" y="{y + 40}" fill="{t.DIM}" font-size="21">$ {label}</text>')

        # count-up frames, ease-out so it decelerates into the real number
        parts.append('<g filter="url(#glow)">')
        for k in range(1, FRAMES + 1):
            v = value * (1 - (1 - k / FRAMES) ** 3)
            anim = f'<set attributeName="opacity" to="1" begin="{count_start + COUNT_DUR * (k - 1) / FRAMES:.3f}s"/>'
            if k < FRAMES:
                anim += f'<set attributeName="opacity" to="0" begin="{count_start + COUNT_DUR * k / FRAMES:.3f}s"/>'
            parts.append(
                f'<text x="{x + 24:.1f}" y="{y + 100}" opacity="0" font-size="54" font-weight="700" fill="{accent}">'
                f'{fmt(v, value)}<tspan font-size="24" font-weight="400" fill="{t.DIM}">{suffix}</tspan>'
                f'{anim}</text>'
            )
        parts.append('</g>')
        parts.append(f'<text x="{x + 24:.1f}" y="{y + 132}" fill="{t.DIM}" font-size="19">{caption}</text>')
        parts.append('</g>')

    # contributions per month
    monthly = data["monthly"]
    chart_w, chart_h = W - PAD * 2, H - PAD - CHART_TOP
    parts.append(f'<g class="t" style="animation-delay:{BAR_START - 0.3:.2f}s">'
                 f'<rect x="{PAD}" y="{CHART_TOP}" width="{chart_w}" height="{chart_h}" rx="10" '
                 f'fill="{t.TILE}" stroke="{t.FRAME}"/>'
                 f'<text x="{PAD + 24}" y="{CHART_TOP + 40}" fill="{t.DIM}" font-size="21">'
                 f'$ git log --format=%ad | uniq -c</text></g>')

    plot_top, plot_bot = CHART_TOP + 64, CHART_TOP + chart_h - 40
    plot_l, plot_r = PAD + 24, PAD + chart_w - 24
    slot = (plot_r - plot_l) / len(monthly)
    bar_w = slot * 0.62
    peak = max(m["total"] for m in monthly) or 1
    parts.append('<g filter="url(#glow)">')
    for i, m in enumerate(monthly):
        bh = max(2, (plot_bot - plot_top) * m["total"] / peak)
        bx = plot_l + i * slot + (slot - bar_w) / 2
        delay = BAR_START + i * BAR_STAGGER
        is_peak = m["total"] == peak
        parts.append(f'<rect class="b" x="{bx:.1f}" y="{plot_bot - bh:.1f}" width="{bar_w:.1f}" '
                     f'height="{bh:.1f}" rx="3" fill="{t.GREEN if is_peak else t.LEVELS[2]}" '
                     f'style="animation-delay:{delay:.2f}s"><title>{m["month"]}: {m["total"]}</title></rect>')
        mon = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")[0].lower()
        parts.append(f'<text x="{bx + bar_w / 2:.1f}" y="{plot_bot + 28}" fill="{t.DIM}" font-size="18" '
                     f'text-anchor="middle">{mon}</text>')
        if is_peak:
            parts.append(f'<text class="t" style="animation-delay:{delay + BAR_DUR:.2f}s" '
                         f'x="{bx + bar_w / 2:.1f}" y="{plot_bot - bh - 10:.1f}" fill="{t.INK}" '
                         f'font-size="18" text-anchor="middle">{peak:,}</text>')
    parts.append('</g>')

    parts += t.close_svg(W, H)
    t.write(OUT, parts)


if __name__ == "__main__":
    with open(t.DATA_PATH) as f:
        render(json.load(f))
