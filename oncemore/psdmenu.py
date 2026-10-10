"""Menus from layered Photoshop files.

A menu designed in Photoshop becomes an ordinary oncemore menu: the visible
artwork is the background, and layer groups marked as buttons become buttons
whose highlight is drawn by their highlight layers. The layer names follow
the prefixes long used for DVD menus:

  (+) Name     a layer group that is a button (its name becomes the id and
               suggests the action, see guess_action)
  (=1) ...     inside a button: the highlight. (=2) and (=3) are taken too;
               a DVD highlight here has one colour, so they are merged
  (%) ...      inside a button: where the title / chapter thumbnail goes

Everything else that is visible is artwork. Highlight layers never are,
visible or not. Without highlight layers a button lights up in the shape
of its own visible pixels.

The background is the file's own flattened image when the highlight and
thumbnail layers are hidden (then it is exact, layer effects included);
otherwise it is rebuilt from the layers' pixels with normal blending and
their opacity, and a note says so.

Coordinates: the document is stretched to the menu (a 720 x 480 design is
read as non-square DVD pixels, a 854 x 480 or 640 x 480 one as square),
so a design of either kind lands where the designer drew it.
"""

import os
import re
import shutil
import subprocess
import tempfile

from . import psd, tools
from .errors import OncemoreError
from .menu import display_width
from .project import STANDARDS, Disc

BUTTON = "(+)"
THUMB = "(%)"
_HIGHLIGHT = re.compile(r"^\(=[123]\)")


def _clean(name, prefix):
    return name[len(prefix):].strip() if name.startswith(prefix) else name.strip()


def slug(name, used):
    """A button id from a layer name ("Play Movie" -> "play_movie")."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_").lower()[:36] or "button"
    out, n = s, 2
    while out in used:
        out, n = f"{s}_{n}", n + 1
    used.add(out)
    return out


def guess_action(name, project):
    """An action for a button named `name`, or (None, why)."""
    titles = project.get("titles", [])
    menus = [m["id"] for m in project.get("menus", [])]
    for t in titles:
        spec = t.get("auto_chapter_menu")
        if spec:
            menus.append((spec.get("id") if isinstance(spec, dict) else None)
                         or f"chapters_{t['id']}")
    n = name.lower().strip()
    if re.fullmatch(r"play( all| movie| everything)?", n) and titles:
        return ("playall" if len(titles) > 1 and n != "play movie" else
                f"title:{titles[0]['id']}"), None
    for t in titles:
        if n in (t["id"].lower(), str(t.get("name", "")).lower()):
            return f"title:{t['id']}", None
    m = re.fullmatch(r"(?:chapter|scene|ch)\s*0*(\d+)", n)
    if m and titles:
        return f"chapter:{titles[0]['id']}:{int(m.group(1))}", None
    for mid in menus:
        if n == mid.lower():
            return f"menu:{mid}", None
    m = re.fullmatch(r"audio\s*(\d)", n)
    if m:
        return f"audio:{m.group(1)}", None
    m = re.fullmatch(r"subtitles?\s*(\d|off)", n)
    if m:
        return f"subtitle:{m.group(1)}", None
    return None, f"no action could be guessed from the name {name!r}"


def _union(boxes):
    boxes = [b for b in boxes if b and b[2] > b[0] and b[3] > b[1]]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _clip(box, w, h):
    if box is None:
        return None
    l, t, r, b = max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3])
    return (l, t, r, b) if r > l and b > t else None


def _opacity(layer):
    o = layer.opacity / 255 * getattr(layer, "fill_opacity", 255) / 255
    p = layer.parent
    while p is not None:
        o *= p.opacity / 255
        p = p.parent
    return o


def _alpha_union(layers, box, threshold=128):
    """RGBA picture (white, alpha = union of the layers' alpha) of `box`."""
    l, t, r, b = box
    w, h = r - l, b - t
    alpha = bytearray(w * h)
    for layer in layers:
        if layer.is_empty or layer.is_group:
            continue
        px = layer.rgba()
        lw = layer.width
        for y in range(max(t, layer.top), min(b, layer.bottom)):
            row = (y - layer.top) * lw
            out = (y - t) * w
            for x in range(max(l, layer.left), min(r, layer.right)):
                a = px[(row + x - layer.left) * 4 + 3]
                if a > alpha[out + x - l]:
                    alpha[out + x - l] = a
    rgba = bytearray(w * h * 4)
    for i, a in enumerate(alpha):
        if a >= threshold:
            rgba[i * 4:i * 4 + 4] = b"\xff\xff\xff\xff"
    return w, h, bytes(rgba)


def _scale_png(src, dst, w, h, log):
    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-i", src,
               "-vf", f"scale={w}:{h}:flags=bicubic,format=rgba", "-frames:v", "1",
               "-update", "1", dst], log=log, what="ffmpeg (Photoshop import)", timeout=300)


def _composite(doc, layers, out_png, size, background, work, log):
    """Flatten `layers` (bottom first) over `background` with ffmpeg, scaled
    to `size` (the menu's square-pixel canvas)."""
    inputs = ["-f", "lavfi", "-i",
              f"color=c={background}:s={doc.width}x{doc.height}:d=1"]
    chains, cur = [], "0:v"
    k = 0
    for layer in layers:
        if layer.is_empty or layer.is_group:
            continue
        k += 1
        png = os.path.join(work, f"layer{k}.png")
        psd.write_png(png, layer.width, layer.height, layer.rgba())
        inputs += ["-i", png]
        op = _opacity(layer)
        pre = f"[{k}:v]format=rgba" + (f",colorchannelmixer=aa={op:.4f}" if op < 0.999 else "")
        chains.append(f"{pre}[l{k}]")
        chains.append(f"[{cur}][l{k}]overlay={layer.left}:{layer.top}:format=auto[c{k}]")
        cur = f"c{k}"
    w, h = size
    chains.append(f"[{cur}]scale={w}:{h}:flags=bicubic,setsar=1,format=rgb24[out]")
    # (passed inline: -filter_complex_script is gone in ffmpeg 8, and its
    # replacement "-/filter_complex" does not exist before ffmpeg 7)
    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y"] + inputs +
              ["-filter_complex", ";".join(chains), "-map", "[out]", "-frames:v", "1",
               "-update", "1", out_png], log=log, what="ffmpeg (Photoshop import)", timeout=600)


def import_psd(psd_path, project, menu_id, out_dir, rel_base):
    """Build a menu from a layered Photoshop file.

    `project`: the project JSON (dict), used for the disc format, the
    existing menu with this id (its button actions and settings are kept on
    re-import) and to guess actions. Pictures are written to `out_dir`;
    paths in the returned menu are relative to `rel_base`.
    Returns (menu dict, notes)."""
    tools.require(["ffmpeg"])
    doc = psd.read_psd(psd_path)
    disc = project["disc"]
    W, H = STANDARDS[disc["standard"]][:2]
    dw = display_width(Disc(label="X", standard=disc["standard"],
                            aspect=disc.get("aspect", "16:9"), target="DVD5", first_play=None))
    sx, sy = W / doc.width, H / doc.height          # document -> storage pixels
    fx, fy = dw / doc.width, H / doc.height         # document -> square display pixels
    notes = []
    old = next((m for m in project.get("menus", []) if m.get("id") == menu_id), None)
    old_buttons = {x["id"]: x for x in (old or {}).get("buttons", [])}

    groups = [l for l in doc.walk() if l.is_group and l.name.startswith(BUTTON)]
    if not groups:
        notes.append({"level": "warning", "message": "no layer group is named \"(+) ...\"; "
                      "the menu has the artwork but no buttons"})
    in_button = {}
    for g in groups:
        for layer in g.walk():
            in_button[id(layer)] = g
    special = set()
    for layer in doc.walk():
        if _HIGHLIGHT.match(layer.name):
            special.add(id(layer))
            if id(layer) not in in_button:
                notes.append({"level": "info", "message": f"highlight layer {layer.name!r} is "
                              "not inside a \"(+)\" button group and was left out"})
        elif layer.name.startswith(THUMB) and id(layer) in in_button:
            special.add(id(layer))

    def descendants(g):
        return list(g.walk())

    os.makedirs(out_dir, exist_ok=True)
    rel = lambda p: os.path.relpath(p, rel_base).replace(os.sep, "/")
    work = tempfile.mkdtemp(prefix="oncemore-psd-")
    log = os.path.join(work, "import.log")
    try:
        # -- background ---------------------------------------------------------
        bg_png = os.path.join(out_dir, f"{menu_id}-background.png")
        visible_special = any(x.effective_visible for x in doc.walk() if id(x) in special)
        merged = doc.composite() if not visible_special else None
        if merged is not None:
            raw = os.path.join(work, "merged.png")
            psd.write_png(raw, doc.width, doc.height, merged)
            tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-f", "lavfi",
                       "-i", f"color=c=black:s={doc.width}x{doc.height}:d=1", "-i", raw,
                       "-filter_complex",
                       f"[0:v][1:v]overlay=0:0:format=auto,scale={dw}:{H}:flags=bicubic,"
                       "setsar=1,format=rgb24[out]", "-map", "[out]", "-frames:v", "1",
                       "-update", "1", bg_png], log=log, what="ffmpeg (Photoshop import)",
                      timeout=300)
        else:
            art = [x for x in reversed(list(doc.walk())) if x.effective_visible
                   and id(x) not in special]
            # walk() is top first; flatten bottom first
            _composite(doc, art, bg_png, (dw, H), "black", work, log)
            if visible_special:
                notes.append({"level": "info", "message": "highlight or thumbnail layers are "
                              "visible in the file, so the background was rebuilt from the "
                              "layers (layer effects such as shadows are not included); hide "
                              "them and save with Maximize Compatibility for an exact "
                              "background"})
            else:
                notes.append({"level": "info", "message": "the file has no flattened image; "
                              "the background was rebuilt from the layers"})
        odd = sorted({x.blend_mode.strip() for x in doc.walk()
                      if x.effective_visible and not x.is_group and x.blend_mode != "norm"})
        if odd and merged is None:
            notes.append({"level": "info", "message": "blend modes "
                          f"{', '.join(odd)} were drawn as normal"})
        kinds = sorted({x.kind for x in doc.walk() if x.kind == "adjustment"
                        and x.effective_visible})
        if kinds and merged is None:
            notes.append({"level": "info", "message": "adjustment layers are not applied"})

        # -- buttons ------------------------------------------------------------
        used, buttons = set(), []
        for g in groups:
            name = _clean(g.name, BUTTON) or "button"
            bid = slug(name, used)
            kids = descendants(g)
            hls = [x for x in kids if _HIGHLIGHT.match(x.name)]
            thumbs = [x for x in kids if x.name.startswith(THUMB)]
            art = [x for x in kids if id(x) not in special and x.effective_visible]
            area = _clip(_union([x.bounds for x in kids if not x.is_group and not x.is_empty]),
                         doc.width, doc.height)
            if area is None:
                notes.append({"level": "warning", "message": f"button group {g.name!r} is "
                              "empty or off the canvas and was left out"})
                continue
            source = hls or art
            if not hls:
                notes.append({"level": "info", "message": f"button {bid!r} has no (=1) "
                              "highlight layer; it lights up in the shape of its artwork"})
            hl_box = _clip(_union([x.bounds for x in source if not x.is_empty]),
                           doc.width, doc.height) or area
            w, h, rgba = _alpha_union(source, hl_box)
            if not any(rgba[3::4]):
                notes.append({"level": "warning", "message": f"the highlight of button "
                              f"{bid!r} is empty and was left out"})
                continue
            raw = os.path.join(work, f"{bid}.png")
            psd.write_png(raw, w, h, rgba)
            hl_png = os.path.join(out_dir, f"{menu_id}-{bid}-highlight.png")
            _scale_png(raw, hl_png, max(2, round(w * fx)), max(2, round(h * fy)), log)
            btn = {"id": bid, "x": round(hl_box[0] * sx), "y": round(hl_box[1] * sy),
                   "width": max(8, round(w * sx)), "highlight_image": rel(hl_png)}
            prev = old_buttons.get(bid)
            if prev:
                for k in ("action", "nav", "auto_activate"):
                    if k in prev:
                        btn[k] = prev[k]
            if "action" not in btn:
                action, why = guess_action(name, project)
                if action is None:
                    titles = project.get("titles", [])
                    action = f"title:{titles[0]['id']}" if titles else "stop"
                    notes.append({"level": "info", "message": f"button {bid!r}: {why}; it "
                                  f"plays {action.split(':', 1)[-1]} for now"})
                btn["action"] = action
            if thumbs:
                tb = _clip(_union([x.bounds for x in thumbs]), doc.width, doc.height)
                kind = btn["action"].split(":")[0]
                if tb and kind in ("title", "chapter"):
                    btn["thumbnail"] = {"x": round(tb[0] * sx), "y": round(tb[1] * sy),
                                        "w": max(8, round((tb[2] - tb[0]) * sx)),
                                        "h": max(8, round((tb[3] - tb[1]) * sy))}
                else:
                    notes.append({"level": "info", "message": f"button {bid!r}: the (%) "
                                  "thumbnail needs a title or chapter action"})
            buttons.append(btn)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    menu = dict(old or {}, id=menu_id, background=rel(bg_png), buttons=buttons)
    for k in ("texts", "shapes", "images"):
        menu.pop(k, None)              # the artwork is in the background now
    if menu.get("default_button") not in {x["id"] for x in buttons}:
        menu.pop("default_button", None)
    menu["psd"] = rel(os.path.abspath(psd_path))
    return menu, notes
