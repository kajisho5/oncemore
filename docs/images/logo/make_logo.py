"""Regenerate the oncemore logo files (see docs/DESIGN.md, Brand).

The mark is drawn from geometry; the wordmark is "oncemore" set in Outfit
SemiBold (SIL Open Font License, Google Fonts) and converted to outlines, so
no font is needed to show it. Only this script needs fontTools and the font
file; oncemore itself does not:

    pip install fonttools
    python docs/images/logo/make_logo.py path/to/Outfit-SemiBold.ttf

Writes the files next to this script, the two the app serves
(oncemore/gui/static/favicon.svg, brand-lockup.svg) and the Mac app's
layered icon, macos/AppIcon.icon (`--icon` writes that alone). macos/
AppIcon.png, the icon of macOS 15 and earlier, is appicon.svg rendered at
1024 x 1024 with a transparent outside.
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


def mark_outlined():
    """The mark as filled outlines of cubic curves alone (no arcs, no
    strokes): the same shapes as mark(), as Icon Composer reads them (its
    SVG import draws arcs and strokes as straight pieces)."""
    cx = cy = 50
    r, sw = 33, 13
    outer, inner = r + sw / 2, r - sw / 2
    a0, a1 = math.radians(340), math.radians(630)       # clockwise, as mark() draws it

    def pt(radius, a):
        return cx + radius * math.cos(a), cy + radius * math.sin(a)

    def arc(radius, start, end, parts=4):
        """Cubic pieces from `start` to `end` (radians) on a circle."""
        out = []
        step = (end - start) / parts
        k = 4 / 3 * math.tan(step / 4)
        for i in range(parts):
            s, e = start + i * step, start + (i + 1) * step
            p0, p3_ = pt(radius, s), pt(radius, e)
            c1 = (p0[0] - k * radius * math.sin(s), p0[1] + k * radius * math.cos(s))
            c2 = (p3_[0] + k * radius * math.sin(e), p3_[1] - k * radius * math.cos(e))
            out.append(f"C{c1[0]:.3f} {c1[1]:.3f} {c2[0]:.3f} {c2[1]:.3f} {p3_[0]:.3f} {p3_[1]:.3f}")
        return " ".join(out)
    o0, i1 = pt(outer, a0), pt(inner, a1)
    ring = (f"M{o0[0]:.3f} {o0[1]:.3f} {arc(outer, a0, a1)} L{i1[0]:.3f} {i1[1]:.3f} "
            f"{arc(inner, a1, a0)} Z")
    c0 = pt(9, 0)
    dot = f"M{c0[0]:.3f} {c0[1]:.3f} {arc(9, 0, 2 * math.pi)} Z"
    # the arrowhead, as mark() places it
    p1 = pt(r, a1)
    tx, ty = -math.sin(a1), math.cos(a1)
    nx, ny = -ty, tx
    tip = (p1[0] + tx * 17, p1[1] + ty * 17)
    b1 = (p1[0] + nx * 15 - tx, p1[1] + ny * 15 - ty)
    b2 = (p1[0] - nx * 15 - tx, p1[1] - ny * 15 - ty)
    head = f"M{tip[0]:.3f} {tip[1]:.3f} L{b1[0]:.3f} {b1[1]:.3f} L{b2[0]:.3f} {b2[1]:.3f} Z"
    return f'<path d="{ring} {dot} {head}" fill="{HIGHLIGHT}"/>'


def p3(hex_colour):
    """An sRGB colour as Icon Composer writes colours: "display-p3:r,g,b,a"."""
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    def enc(c):
        c = min(1.0, max(0.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    r, g, b = (lin(int(hex_colour[i:i + 2], 16) / 255) for i in (1, 3, 5))
    # linear sRGB to linear Display P3 (both D65)
    rgb = (0.822462 * r + 0.177538 * g, 0.033194 * r + 0.966806 * g,
           0.017083 * r + 0.072397 * g + 0.910520 * b)
    return "display-p3:" + ",".join(f"{enc(c):.5f}" for c in rgb) + ",1.00000"


def icon_bundle(folder):
    """macos/AppIcon.icon, the layered icon of macOS 26 and later (Apple's
    Human Interface Guidelines, App icons): a square, unmasked design the
    system masks and lights itself. The background is a solid ink fill; the
    mark, the one foreground layer, is centred at the size it has on the
    legacy icon's tile, drawn in filled curves (mark_outlined). Older macOS
    take AppIcon.png (macos/build_app.sh)."""
    assets = os.path.join(folder, "Assets")
    os.makedirs(assets, exist_ok=True)
    k = 600 / 824 * 1024 / 100                     # the mark's share of the tile, as before
    off = (1024 - 100 * k) / 2
    layer = svg(1024, 1024,
                f'<g transform="translate({off:g} {off:g}) scale({k:g})">{mark_outlined()}</g>',
                "oncemore")
    with open(os.path.join(assets, "mark.svg"), "w") as f:
        f.write(layer)
    doc = {
        "fill": {"solid": p3(INK)},
        "groups": [{
            "layers": [{"image-name": "mark.svg", "name": "mark",
                        "position": {"scale": 1, "translation-in-points": [0, 0]}}],
            "shadow": {"kind": "neutral", "opacity": 0.5},
            "specular": True,
            # (opaque: the mark keeps the brand yellow; the light is the system's)
            "translucency": {"enabled": False, "value": 0.5},
        }],
        "supported-platforms": {"squares": "shared"},
    }
    import json
    with open(os.path.join(folder, "icon.json"), "w") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")


def main(font_path):
    def save(path, text):
        with open(path, "w") as f:
            f.write(text)
    m = mark()
    save(os.path.join(HERE, "mark.svg"), svg(100, 100, m, "oncemore"))
    tile = f'<rect x="100" y="100" width="824" height="824" rx="185" fill="{INK}"/>'
    icon = tile + f'<g transform="translate(212 212) scale(6)">{m}</g>'
    save(os.path.join(HERE, "appicon.svg"), svg(1024, 1024, icon, "oncemore"))
    icon_bundle(os.path.join(HERE, "..", "..", "..", "macos", "AppIcon.icon"))
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
    if sys.argv[1:] == ["--icon"]:          # the layered macOS icon alone (no font needed)
        icon_bundle(os.path.join(HERE, "..", "..", "..", "macos", "AppIcon.icon"))
    else:
        main(sys.argv[1])
