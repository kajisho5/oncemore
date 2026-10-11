"""Regenerate the oncemore logo files (see docs/DESIGN.md, Brand).

The mark is drawn from geometry; the wordmark is "oncemore" set in Outfit
SemiBold (SIL Open Font License, Google Fonts) and converted to outlines, so
no font is needed to show it. Only this script needs fontTools and the font
file; oncemore itself does not:

    pip install fonttools
    python docs/images/logo/make_logo.py path/to/Outfit-SemiBold.ttf

Writes the files next to this script and the two the app serves
(oncemore/gui/static/favicon.svg, brand-lockup.svg). macos/AppIcon.png is
appicon.svg rendered at 1024 x 1024 with a transparent outside.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "..", "..", "..", "oncemore", "gui", "static")
# the brand colours (tokens.css: --brand-highlight, --brand-ink, --brand-paper)
HIGHLIGHT, INK, PAPER = "#ffd400", "#181b22", "#f2f2f2"


def svg(w, h, body, title, view=None):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view or f"0 0 {w:g} {h:g}"}" '
            f'width="{w:g}" height="{h:g}" role="img" aria-label="{title}"><title>{title}</title>'
            f'{body}</svg>\n')


def mark():
    """A disc whose rim is a loop arrow (play it once more), on a 100 x 100 grid."""
    cx = cy = 50
    r, sw = 33, 13
    a0, a1 = math.radians(340), math.radians(-90)          # clockwise from 340 to 270 degrees
    p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
    p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
    tx, ty = -math.sin(a1), math.cos(a1)                   # the direction it runs at the end
    nx, ny = -ty, tx
    tip = (p1[0] + tx * 17, p1[1] + ty * 17)
    b1 = (p1[0] + nx * 15 - tx, p1[1] + ny * 15 - ty)
    b2 = (p1[0] - nx * 15 - tx, p1[1] - ny * 15 - ty)
    return (f'<path d="M{p0[0]:.2f} {p0[1]:.2f} A{r} {r} 0 1 1 {p1[0]:.2f} {p1[1]:.2f}" '
            f'fill="none" stroke="{HIGHLIGHT}" stroke-width="{sw}"/>'
            f'<path d="M{tip[0]:.2f} {tip[1]:.2f} L{b1[0]:.2f} {b1[1]:.2f} L{b2[0]:.2f} {b2[1]:.2f} Z" '
            f'fill="{HIGHLIGHT}"/><circle cx="{cx}" cy="{cy}" r="9" fill="{HIGHLIGHT}"/>')


def wordmark(font_path, size, x0, baseline, track=-0.01):
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    font = TTFont(font_path)
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    s = size / font["head"].unitsPerEm
    x, parts = x0, []
    for ch in "oncemore":
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
        parts.append(pen.getCommands())
        x += hmtx[g][0] * s + track * size
    return " ".join(parts), x - track * size - x0


def main(font_path):
    def save(path, text):
        with open(path, "w") as f:
            f.write(text)
    m = mark()
    save(os.path.join(HERE, "mark.svg"), svg(100, 100, m, "oncemore"))
    tile = f'<rect x="100" y="100" width="824" height="824" rx="185" fill="{INK}"/>'
    icon = tile + f'<g transform="translate(212 212) scale(6)">{m}</g>'
    save(os.path.join(HERE, "appicon.svg"), svg(1024, 1024, icon, "oncemore"))
    # the favicon: the tile without the margin macOS icons keep
    save(os.path.join(STATIC, "favicon.svg"), svg(64, 64, icon, "oncemore", view="100 100 824 824"))
    wm, width = wordmark(font_path, 64, 112, 66)
    w = round(112 + width + 8)
    lockup = svg(w, 100, f'<rect width="{w}" height="100" fill="{INK}"/>' + m +
                 f'<path d="{wm}" fill="{PAPER}"/>', "oncemore")
    save(os.path.join(HERE, "lockup-dark.svg"), lockup)
    save(os.path.join(STATIC, "brand-lockup.svg"), lockup)
    for tone, fill in (("light", PAPER), ("ink", INK)):
        wm, width = wordmark(font_path, 96, 0, 96 * 0.78)
        save(os.path.join(HERE, f"wordmark-{tone}.svg"),
             svg(round(width), 96, f'<path d="{wm}" fill="{fill}"/>', "oncemore"))


if __name__ == "__main__":
    main(sys.argv[1])
