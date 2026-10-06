#!/usr/bin/env python3
"""
Turn assets/source-photo.jpg into a monochrome, phosphor-green ASCII SVG that
"types" itself in row by row like a terminal, then holds.

Dark parts of the photo (me, my shadow, the ridge line) become dense, bright
characters; bright sand fades to blank, so the subject reads as glowing on the
black CRT. A difference-of-gaussians edge pass is added on top so mid-tones
that would otherwise wash out (legs, footprints) still get an outline.

GitHub runs SMIL inside <img> SVGs (never JS), so each row is revealed with a
left-to-right clip wipe and a block cursor riding the edge.

    python scripts/make_ascii_svg.py [photo] [output.svg]
    STATIC=1 python scripts/make_ascii_svg.py   # frozen frame, for previews

Only needs re-running when the photo or the tuning below changes.
"""
import html
import os
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

import theme as t

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(t.ASSETS, "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(t.ASSETS, "ascii-portrait.svg")
STATIC = bool(os.environ.get("STATIC"))

# region of the photo to keep, as fractions (left, top, right, bottom)
CROP = (0.12, 0.40, 0.76, 0.88)

# tone curve on "darkness" (1 - luminance): below LO -> blank, above HI -> '@'
LO, HI, GAMMA = 0.52, 0.95, 1.3
EDGE = 3.5            # how much the edge pass adds
RAMP = " .`:-=+*cs#%@"

W, H = 840, 880       # same canvas as stats.svg so they line up side by side
PAD = 20
STATUS_H = 30
ART_W = W - PAD * 2
ART_H = H - t.TITLEBAR_H - STATUS_H - PAD
COLS = int(os.environ.get("COLS", 160))
CELL_W = ART_W / COLS
CELL_H = CELL_W * 15 / 8          # ~1:1.875 monospace cell
ROWS = int(ART_H // CELL_H)

ROW_DUR = 5.0 / ROWS              # whole picture prints in ~5s


def sample():
    im = Image.open(SRC).convert("L")
    w, h = im.size
    im = im.crop((int(w * CROP[0]), int(h * CROP[1]), int(w * CROP[2]), int(h * CROP[3])))
    im = ImageOps.autocontrast(im, cutoff=1)

    lum = np.asarray(im, dtype=np.float32) / 255
    fine = np.asarray(im.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255
    coarse = np.asarray(im.filter(ImageFilter.GaussianBlur(10)), dtype=np.float32) / 255
    dark = np.clip((1 - lum - LO) / (HI - LO), 0, 1) ** GAMMA
    dark = np.clip(dark + EDGE * np.abs(fine - coarse), 0, 1)

    grid = Image.fromarray((dark * 255).astype(np.uint8)).resize((COLS, ROWS), Image.LANCZOS)
    grid = np.asarray(grid, dtype=np.float32) / 255
    top = len(RAMP) - 1
    return ["".join(RAMP[int(v * top + 0.5)] for v in row) for row in grid]


def render(rows):
    parts = t.open_svg(W, H, f"{t.PROMPT}: ~$ ./portrait.sh --ascii")
    art_top = t.TITLEBAR_H + PAD * 0.4
    font_size = CELL_H * 0.86

    parts.append('<g filter="url(#glow)">')
    for ry, line in enumerate(rows):
        row_y = art_top + ry * CELL_H
        text = (f'<text xml:space="preserve" x="{PAD}" y="{row_y + CELL_H * 0.74:.1f}" fill="{t.GREEN}" '
                f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">'
                f'{html.escape(line)}</text>')
        if STATIC:
            parts.append(text)
            continue
        begin = ry * ROW_DUR
        parts.append(
            f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H:.2f}" width="0">'
            f'<animate attributeName="width" from="0" to="{ART_W}" begin="{begin:.3f}s" '
            f'dur="{ROW_DUR:.3f}s" fill="freeze"/></rect></clipPath>'
            f'<g clip-path="url(#r{ry})">{text}</g>'
        )
    parts.append('</g>')

    if not STATIC:
        # one cursor that rasters down the rows, then disappears
        n = len(rows)
        x_kt, x_vals = [], []
        for ry in range(n):
            x_kt += [ry / n, (ry + 1) / n - (1e-4 if ry < n - 1 else 0)]
            x_vals += [PAD, PAD + ART_W]
        ys = ";".join(f"{art_top + ry * CELL_H + 1:.1f}" for ry in range(n))
        y_kt = ";".join(f"{ry / n:.5f}" for ry in range(n))
        total = ROW_DUR * n
        parts.append(
            f'<rect width="{CELL_W * 1.4:.1f}" height="{CELL_H - 2:.1f}" fill="{t.MINT}" opacity="0.9">'
            f'<animate attributeName="x" values="{";".join(map(str, x_vals))}" '
            f'keyTimes="{";".join(f"{k:.5f}" for k in x_kt)}" dur="{total:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" values="{ys}" keyTimes="{y_kt}" dur="{total:.2f}s" '
            f'fill="freeze" calcMode="discrete"/>'
            f'<set attributeName="opacity" to="0" begin="{total:.2f}s"/></rect>'
        )

    line_y = H - STATUS_H - PAD * 0.6
    parts.append(f'<line x1="0" y1="{line_y:.1f}" x2="{W}" y2="{line_y:.1f}" stroke="{t.FRAME}"/>')
    status_y = line_y + 20
    cmd = f"{t.PROMPT}:~$ whoami "
    name = "Alex · full-stack dev · Romania → France"
    parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{t.DIM}" font-size="13">{html.escape(cmd)}'
                 f'<tspan fill="{t.INK}">{html.escape(name)}</tspan></text>')
    parts.append(f'<rect x="{PAD + (len(cmd) + len(name) + 1) * 13 * 0.6:.1f}" y="{status_y - 12:.1f}" '
                 f'width="8" height="14" fill="{t.GREEN}">'
                 '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
                 'dur="1s" repeatCount="indefinite"/></rect>')

    parts += t.close_svg(W, H)
    t.write(OUT, parts)


if __name__ == "__main__":
    render(sample())
