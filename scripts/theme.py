"""
Shared palette + terminal-window chrome for every SVG this repo renders, so the
heatmap, the neofetch panel and the stats card all look like the same CRT.

Colors match the README badges (#020A05 background, #28FF6A phosphor green).
GitHub shows these SVGs through <img>, which runs CSS/SMIL animations and SVG
filters but never JS and never loads web fonts -- so everything is inline and
the font stack falls back to the viewer's system monospace.
"""
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_PATH = os.path.join(ROOT, "data", "contributions.json")
ASSETS = os.path.join(ROOT, "assets")

USERNAME = os.environ.get("GH_PROFILE_USER", "idleCyrex")
PROMPT = "alex@idlee"

BG = "#020a05"
BG2 = "#04140a"
TILE = "#061a0d"
FRAME = "#1c6e3e"
DIM = "#2f9d5b"
INK = "#c9ffdc"
GREEN = "#28ff6a"
MINT = "#5cffa0"
RED = "#ff2e4d"
AMBER = "#ffb000"

# contribution levels 0..4 (GitHub's own quartile buckets)
LEVELS = ["#0a1f12", "#0f4d27", "#178a40", "#1fc458", "#28ff6a"]

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

TITLEBAR_H = 30


def open_svg(w, h, title, css=""):
    """Start an SVG: CRT background, frame, scanlines, title bar with dots."""
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="{FONT}">',
        f'<style>{css}'
        # .c/.t/.b/.f are the animated classes the renderers use
        '@media (prefers-reduced-motion: reduce){.c,.t,.b,.f{animation:none!important;'
        'opacity:1!important;transform:none!important}.beam{display:none}}'
        '</style>',
        '<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
        f'<radialGradient id="vig" cx="0.5" cy="0.5" r="0.75">'
        f'<stop offset="0.6" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#000" fill-opacity="0.28"/></pattern>'
        '<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur stdDeviation="2.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>',
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#bg)"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{w}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
        *[f'<circle cx="{20 + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{c}"/>'
          for i, c in enumerate([RED, AMBER, GREEN])],
        f'<text x="{w/2}" y="{TITLEBAR_H/2 + 4}" fill="{DIM}" font-size="12" '
        f'text-anchor="middle">{title}</text>',
    ]


def close_svg(w, h):
    """Scanlines + vignette over everything, then the frame on top."""
    return [
        f'<rect y="{TITLEBAR_H}" width="{w}" height="{h - TITLEBAR_H}" fill="url(#scan)" pointer-events="none"/>',
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#vig)" pointer-events="none"/>',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12" fill="none" stroke="{FRAME}"/>',
        '</svg>',
    ]


def write(path, parts):
    svg = "".join(parts)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {os.path.relpath(path, ROOT)} ({len(svg)//1024} KB)")
