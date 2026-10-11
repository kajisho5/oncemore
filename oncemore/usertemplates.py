"""Menus saved as templates (Menu > Save menu as template), for any project.

A template is a folder in the user's template library holding the menu's
JSON and a copy of every file it uses (backgrounds, button pictures, fonts,
music), so it still works after the project it came from is gone:

    <library>/<id>/template.json   {"name": ..., "menu": {...}}
    <library>/<id>/files/...        the copied files

The library is $ONCEMORE_TEMPLATES, or the platform's per-user data folder
(macOS: ~/Library/Application Support/oncemore/templates; elsewhere
$XDG_DATA_HOME/oncemore/templates, default ~/.local/share/...).
"""

import json
import os
import re
import shutil
import sys

from .errors import OncemoreError

# strings in a menu that name a file it uses (the same extensions the app
# treats as media; checked against the project folder before copying)
_FILE_RE = re.compile(r"\.(mp4|m4v|mov|mkv|avi|mpe?g|m2ts|mts|ts|vob|webm|dv|wav|aiff?|mp3|m4a|"
                      r"aac|ac3|flac|png|jpe?g|bmp|tiff?|gif|webp|psd|psb|ttf|otf|ttc)$", re.I)
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def library():
    env = os.environ.get("ONCEMORE_TEMPLATES")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/oncemore/templates")
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "oncemore", "templates")


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]
    return s or "menu"


def _folder(tid):
    if not _ID_RE.match(tid or ""):
        raise ValueError(f"bad template id {tid!r}")
    return os.path.join(library(), tid)


def _walk(value, fn):
    """Apply fn to every string in a JSON value; returns the new value."""
    if isinstance(value, dict):
        return {k: _walk(v, fn) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(v, fn) for v in value]
    return fn(value) if isinstance(value, str) else value


def list_templates():
    root = library()
    out = []
    if os.path.isdir(root):
        for tid in sorted(os.listdir(root)):
            path = os.path.join(root, tid, "template.json")
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            out.append({"id": tid, "name": data.get("name") or tid,
                        "buttons": len(data.get("menu", {}).get("buttons", []))})
    return out


def save(menu, name, project_dir):
    """Save `menu` (project JSON) as a template named `name`; returns its id."""
    if not isinstance(menu, dict) or not isinstance(menu.get("buttons"), list):
        raise ValueError("menu must be a menu object")
    name = (name or menu.get("id") or "menu").strip()[:80]
    root = library()
    os.makedirs(root, exist_ok=True)
    base, n = _slug(name), 1
    tid = base
    while os.path.exists(os.path.join(root, tid)):
        n += 1
        tid = f"{base}_{n}"
    folder = os.path.join(root, tid)
    os.makedirs(os.path.join(folder, "files"))
    project_dir = os.path.realpath(project_dir)
    copied = {}

    def keep(s):
        if not _FILE_RE.search(s):
            return s
        if s in copied:
            return copied[s]
        full = os.path.realpath(os.path.join(project_dir, s))
        if not full.startswith(project_dir + os.sep) or not os.path.isfile(full):
            return s                           # not a file of this project: leave as written
        stored, k = os.path.basename(full), 1
        while stored in copied.values() or os.path.exists(os.path.join(folder, "files", stored)):
            k += 1
            stem, ext = os.path.splitext(os.path.basename(full))
            stored = f"{stem}_{k}{ext}"
        shutil.copy2(full, os.path.join(folder, "files", stored))
        copied[s] = "files/" + stored
        return copied[s]

    data = {"name": name, "menu": _walk(menu, keep)}
    with open(os.path.join(folder, "template.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return tid


def delete(tid):
    folder = _folder(tid)
    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)
    shutil.rmtree(folder)


def _targets(project):
    """Every link target that exists in `project` (JSON)."""
    out = {"playall", "stop"}
    for t in project.get("titles", []):
        out.add(f"title:{t['id']}")
        cm = t.get("auto_chapter_menu")
        if cm:
            out.add("menu:" + ((cm.get("id") if isinstance(cm, dict) else None) or f"chapters_{t['id']}"))
    for m in project.get("menus", []):
        out.add(f"menu:{m['id']}")
    for p in project.get("playlists", []):
        out.add(f"playlist:{p['id']}")
    return out


def _link_ok(action, targets):
    if not isinstance(action, str):
        return True
    kind = action.split(":", 1)[0]
    if kind == "chapter":                      # chapter:<title>:<n>
        return f"title:{action.split(':')[1]}" in targets
    if kind in ("title", "menu", "playlist"):
        return action in targets
    return True                                 # playall, stop, audio:/subtitle: switches


def apply(tid, project, project_dir, menu_id):
    """A menu for `project` from template `tid`: its files are copied into the
    project's media/ folder, and links to things the project does not have
    become "stop" (so it is valid at once; link the buttons afterwards)."""
    folder = _folder(tid)
    try:
        with open(os.path.join(folder, "template.json"), encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        raise FileNotFoundError(folder)
    except ValueError:
        raise OncemoreError(f"template {tid!r} is damaged")
    media = os.path.join(project_dir, "media")
    os.makedirs(media, exist_ok=True)
    placed = {}

    def place(s):
        if not s.startswith("files/") or "/" in s[6:] or s in placed:
            return placed.get(s, s)
        src = os.path.join(folder, s)
        if not os.path.isfile(src):
            return s
        name, k = os.path.basename(s), 1
        dst = os.path.join(media, name)
        while os.path.exists(dst) and not _same(src, dst):
            k += 1
            stem, ext = os.path.splitext(os.path.basename(s))
            dst = os.path.join(media, f"{stem}_{k}{ext}")
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
        placed[s] = "media/" + os.path.basename(dst)
        return placed[s]

    menu = _walk(data["menu"], place)
    menu["id"] = menu_id
    targets = _targets(project) | {f"menu:{menu_id}"}
    for b in menu.get("buttons", []):
        if not _link_ok(b.get("action"), targets):
            b["action"] = "stop"
            b.pop("override", None)
            b.pop("transition", None)          # (a stop has no link to lead into)
        if not _link_ok(b.get("override"), targets):
            b.pop("override", None)
    if not _link_ok(menu.get("end_action"), targets):
        menu.pop("end_action", None)
    return menu


def _same(a, b):
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if x != y:
                return False
            if not x:
                return True
