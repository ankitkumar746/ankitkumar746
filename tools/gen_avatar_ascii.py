#!/usr/bin/env python3
"""
Generate ASCII-art avatar tspans for the profile SVGs.

Fetches a GitHub user's avatar, converts it to a 40x25 character grid
using a dense ramp, XML-escapes each row, and prints <tspan> lines
ready to drop into dark_mode.svg and light_mode.svg.

Why two variants:
  - light_mode uses the NORMAL ramp (dense char = shadow), drawn in dark
    ink on a light background -> reads as a correct positive.
  - dark_mode uses the INVERTED ramp (dense char = highlight), drawn in
    light ink on a dark background -> also reads as a correct positive.
  Using one shared block (like the original Andrew6rant template) makes
  one of the two themes look like a photographic negative.

The output tspans use x="15" and y = 30, 50, ..., 510 to match the
existing ASCII block layout (25 rows). Replace the 25 <tspan x="15" ...>
lines inside <text ... class="ascii">...</text> in each SVG.

Usage:
    pip install Pillow requests
    python tools/gen_avatar_ascii.py [username]            # prints both variants
    python tools/gen_avatar_ascii.py ankitkumar746 --mode light
    python tools/gen_avatar_ascii.py ankitkumar746 --mode dark
"""
import argparse
import sys
from io import BytesIO

import requests
from PIL import Image, ImageOps, ImageFilter

COLS = 40
ROWS = 25
# Dense ramp, index 0 = sparsest (highlights) .. last = densest (shadows).
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetch_avatar(username):
    # https://github.com/<user>.png 302-redirects to the real avatar image.
    r = requests.get(f"https://github.com/{username}.png", timeout=30)
    r.raise_for_status()
    return Image.open(BytesIO(r.content))


def render(img, cols, rows, invert, contrast=True, gamma=1.15, sharpen=True):
    """Return a list of `rows` strings, each `cols` wide.

    Image enhancements (v2) for crisper facial features at low resolution:
      - autocontrast: stretch the tonal range so shadows/highlights separate.
      - gamma > 1: lift midtones (faces read better than under linear mapping).
      - unsharp mask: accentuate edges (eyes, nose, mouth, glasses).
    """
    gray = img.convert("L")
    if contrast:
        # ignore the darkest/lightest 1% so a single stray pixel can't set the range
        gray = ImageOps.autocontrast(gray, cutoff=1)
    if gamma and gamma != 1.0:
        lut = [int(255 * (i / 255) ** (1.0 / gamma)) for i in range(256)]
        gray = gray.point(lut)
    if sharpen:
        gray = gray.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=3))
    # Sample at cols x (rows*2) then average vertical pixel pairs so each
    # output character represents a 1-wide x 2-tall source region. This
    # matches the ~2:1 (taller-than-wide) aspect of monospace glyphs and
    # keeps a square avatar from looking vertically squashed.
    sampled = gray.resize((cols, rows * 2))
    px = sampled.load()
    last = len(RAMP) - 1
    lines = []
    for r in range(rows):
        out = []
        for c in range(cols):
            p = (px[c, r * 2] + px[c, r * 2 + 1]) // 2  # 0=black .. 255=white
            if invert:
                # dark mode: dense = highlight (bright pixel -> dense light mark)
                idx = p * last // 255
            else:
                # light mode: dense = shadow (dark pixel -> dense dark mark)
                idx = (255 - p) * last // 255
            out.append(RAMP[idx])
        lines.append("".join(out))
    return lines


def emit(lines, label):
    print(f"=== {label} ===")
    for i, row in enumerate(lines):
        y = 30 + i * 20
        print(f'<tspan x="15" y="{y}">{xml_escape(row)}</tspan>')
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("username", nargs="?", default="ankitkumar746")
    ap.add_argument("--mode", choices=["light", "dark", "both"], default="both")
    ap.add_argument("--cols", type=int, default=COLS)
    ap.add_argument("--rows", type=int, default=ROWS)
    ap.add_argument("--gamma", type=float, default=1.15,
                    help="midtone lift; 1.0 disables, >1 brightens features (default 1.15)")
    ap.add_argument("--no-contrast", dest="contrast", action="store_false",
                    help="disable autocontrast tonal stretch")
    ap.add_argument("--no-sharpen", dest="sharpen", action="store_false",
                    help="disable unsharp-mask edge enhancement")
    args = ap.parse_args()

    img = fetch_avatar(args.username)
    print(f"# ASCII avatar for {args.username} | source {img.size} | grid {args.cols}x{args.rows}"
          f" | contrast={args.contrast} gamma={args.gamma} sharpen={args.sharpen}\n")
    if args.mode in ("light", "both"):
        emit(render(img, args.cols, args.rows, invert=False, contrast=args.contrast,
                    gamma=args.gamma, sharpen=args.sharpen),
             "LIGHT MODE (normal ramp) -> light_mode.svg")
    if args.mode in ("dark", "both"):
        emit(render(img, args.cols, args.rows, invert=True, contrast=args.contrast,
                    gamma=args.gamma, sharpen=args.sharpen),
             "DARK MODE (inverted ramp) -> dark_mode.svg")


if __name__ == "__main__":
    main()
