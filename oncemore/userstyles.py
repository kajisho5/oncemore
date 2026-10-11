"""The user's own styles (Library > My styles): the look of a text, a
button or a shape saved under a name, for any menu of any project.

A style is a folder in the user's style library holding its properties and
a copy of the font it uses, so it still works after the project it came
from is gone:

    <library>/<id>/style.json   {"name": ..., "props": {...}}
    <library>/<id>/files/...    the font

The library is $ONCEMORE_STYLES, or "styles" next to the template library
(see usertemplates.library).
"""

import json
import os
import shutil

from . import usertemplates
from .errors import OncemoreError

# what a style carries (a shape uses its colour only)
PROPS = ("font", "size", "color", "outline", "outline_width", "shadow", "shadow_offset")


def library():
    return os.environ.get("ONCEMORE_STYLES") or \
        os.path.join(os.path.dirname(usertemplates.library()), "styles")


def _folder(sid):
    if not usertemplates._ID_RE.match(sid or ""):
        raise ValueError(f"bad style id {sid!r}")
    return os.path.join(library(), sid)


def list_styles():
    root, out = library(), []
    if os.path.isdir(root):
        for sid in sorted(os.listdir(root)):
            try:
                with open(os.path.join(root, sid, "style.json"), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            out.append({"id": sid, "name": data.get("name") or sid,
                        "props": data.get("props") or {}})
    return out


def save(props, name, project_dir):
    """Save the style properties of an element (project JSON) as `name`;
    returns its id. Only the properties a style carries are kept; the font,
    when it is a file of the project, is copied."""
    if not isinstance(props, dict):
        raise ValueError("props must be an object")
    props = {k: props[k] for k in PROPS if props.get(k) is not None}
    if not props:
        raise ValueError("nothing to save: the element has no style of its own")
    name = (name or "style").strip()[:80] or "style"
    root = library()
    os.makedirs(root, exist_ok=True)
    base = usertemplates._slug(name)
    sid, n = base, 1
    while os.path.exists(os.path.join(root, sid)):
        n += 1
        sid = f"{base}_{n}"
    folder = os.path.join(root, sid)
    os.makedirs(os.path.join(folder, "files"))
    font = props.get("font")
    if font:
        project_dir = os.path.realpath(project_dir)
        full = os.path.realpath(os.path.join(project_dir, font))
        if full.startswith(project_dir + os.sep) and os.path.isfile(full):
            shutil.copy2(full, os.path.join(folder, "files", os.path.basename(full)))
            props["font"] = "files/" + os.path.basename(full)
    with open(os.path.join(folder, "style.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "props": props}, f, indent=2, ensure_ascii=False)
    return sid


def apply(sid, project_dir):
    """The properties of style `sid` for a project: its font copied into the
    project's media/ folder (the same file is not copied twice)."""
    folder = _folder(sid)
    try:
        with open(os.path.join(folder, "style.json"), encoding="utf-8") as f:
            props = dict(json.load(f).get("props") or {})
    except OSError:
        raise FileNotFoundError(folder)
    except ValueError:
        raise OncemoreError(f"style {sid!r} is damaged")
    font = props.get("font")
    if font and font.startswith("files/") and "/" not in font[6:]:
        src = os.path.join(folder, font)
        if os.path.isfile(src):
            media = os.path.join(project_dir, "media")
            os.makedirs(media, exist_ok=True)
            stem, ext = os.path.splitext(os.path.basename(font))
            dst, k = os.path.join(media, os.path.basename(font)), 1
            while os.path.exists(dst) and not usertemplates._same(src, dst):
                k += 1
                dst = os.path.join(media, f"{stem}_{k}{ext}")
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
            props["font"] = "media/" + os.path.basename(dst)
    return props


def delete(sid):
    folder = _folder(sid)
    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)
    shutil.rmtree(folder)
