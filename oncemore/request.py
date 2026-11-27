"""A disc from a typed build request (DECISIONS §142).

    oncemore request request.json --json                  # what would be built, and its token
    oncemore iso --request request.json --confirm TOKEN -o disc.iso --json

A build request is what another program (an editing agent, from its own
plan) asks a disc to hold: the titles in play order, each title's chapters
with their names (a session per chapter), the menu's heading and lines, and
the subtitle tracks. Its shape is `build-request.schema.json`
(`oncemore/build-request@1`); paths are relative to the request file.

oncemore makes the project from it: one menu with the heading and lines, a
play button (PLAY, or PLAY ALL and a button per title), and for every title
with more than one chapter a chapter menu labelled with the chapter names.
Nothing is built until the request is confirmed: `oncemore request` checks
it as `validate` would (media probed, size plan) and gives a token; `build`
and `iso` with `--request` build only with that token, which is the request's
SHA-256 together with the size and modification time of every file it names,
so what is built is what was looked at. A DVD image is read back after it is
written: the chapters of each title in its IFO files must be the request's.
"""

import hashlib
import json
import os
import struct

from . import schemalite
from .errors import OncemoreError, ProjectError
from .project import build_project

SCHEMA = "oncemore/build-request@1"
SECTOR = 2048
_SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "build-request.schema.json")
# menu layout on the 720-wide grid (480 high on NTSC)
_HEADING_Y, _TEXT_Y, _TEXT_STEP, _BUTTON_Y, _BUTTON_STEP, _LEFT = 60, 120, 32, 230, 42, 80


def load_schema():
    with open(_SCHEMA_FILE, encoding="utf-8") as f:
        return json.load(f)


def read_request(path):
    """The request (checked against its schema) and its absolute path."""
    path = os.path.abspath(path)
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise OncemoreError(f"{path}: file not found") from None
    except json.JSONDecodeError as e:
        raise ProjectError(f"{path}: invalid JSON at line {e.lineno} column {e.colno}: {e.msg}") from None
    issues = [{"path": p, "message": m} for p, m in schemalite.validate(data, load_schema())]
    if issues:
        raise ProjectError(f"{path}: does not match the build request schema ({SCHEMA})", issues)
    return data, path


def _chapter_times(title):
    """The title's chapters as project chapter objects, 0 first."""
    chapters = [dict(c) for c in title.get("chapters") or []]
    if not chapters or _seconds(chapters[0]["time"]) > 0:
        chapters.insert(0, {"time": 0})
    return chapters


def _seconds(t):
    if isinstance(t, (int, float)):
        return float(t)
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def to_project(request):
    """The project JSON a request makes (see the module's docstring)."""
    menu = request.get("menu") or {}
    titles, buttons = [], []
    many = len(request["titles"]) > 1
    buttons.append({"id": "play", "label": menu.get("play_label") or ("PLAY ALL" if many else "PLAY"),
                    "action": "playall" if many else "title:t1"})
    for k, t in enumerate(request["titles"], 1):
        tid = f"t{k}"
        chapters = _chapter_times(t)
        title = {"id": tid, "name": t["name"], "source": t["source"], "chapters": chapters,
                 "end_action": "menu:main"}
        if t.get("subtitles"):
            title["subtitles"] = [dict(s) for s in t["subtitles"]]
        if len(chapters) > 1:
            title["auto_chapter_menu"] = {"id": f"chapters_{tid}", "title": t["name"], "back": "menu:main"}
        titles.append(title)
        if many:
            # a title with chapters opens its chapter menu (its first chapter
            # plays it from the start), so every chapter menu is reachable
            buttons.append({"id": f"title_{tid}", "label": t["name"],
                            "action": f"menu:chapters_{tid}" if len(chapters) > 1 else f"title:{tid}"})
        if len(chapters) > 1 and not many:
            buttons.append({"id": "chapters", "label": menu.get("chapters_label") or "CHAPTERS",
                            "action": f"menu:chapters_{tid}"})
    texts = [{"text": menu.get("heading") or request["label"], "x": _LEFT, "y": _HEADING_Y, "size": 36}]
    texts += [{"text": line, "x": _LEFT, "y": _TEXT_Y + k * _TEXT_STEP, "size": 22}
              for k, line in enumerate(menu.get("texts") or [])]
    for k, b in enumerate(buttons):
        b.update({"x": _LEFT, "y": _BUTTON_Y + k * _BUTTON_STEP})
    disc = {"label": request["label"], "standard": request.get("standard", "NTSC"),
            "aspect": request.get("aspect", "16:9"), "first_play": "menu:main"}
    if request.get("format", "dvd") == "bluray":
        disc["format"] = "bluray"
    return {"version": 1, "disc": disc, "titles": titles,
            "menus": [{"id": "main", "background": None, "texts": texts, "buttons": buttons}]}


def _files(request):
    for t in request["titles"]:
        yield t["source"]
        for s in t.get("subtitles") or []:
            yield s["file"]


def token(request, path):
    """The confirmation token: the request's canonical JSON and the size and
    modification time of every file it names, hashed (SHA-256, 16 hex)."""
    base = os.path.dirname(path)
    h = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":")).encode("utf-8"))
    for name in sorted(set(_files(request))):
        full = os.path.normpath(os.path.join(base, os.path.expanduser(name)))   # (as the project resolves it)
        st = os.stat(full) if os.path.isfile(full) else None
        h.update(f"\0{name}\0{st.st_size if st else -1}\0{st.st_mtime_ns if st else -1}".encode("utf-8"))
    return h.hexdigest()[:16]


def load(path, check_files=True):
    """(request, project, token) for the request file at `path`. The
    project is built as if its file were the request, so its paths and its
    encode cache (.oncemore-cache) are the request folder's."""
    request, path = read_request(path)
    data = to_project(request)
    project = build_project(data, path, check_files=check_files)
    return request, project, data, token(request, path)


def confirmed(path, given):
    """The project of a confirmed request, or an error naming what to do.
    The token is checked before the media are looked at."""
    request, path = read_request(path)
    want = token(request, path)
    if not given:
        raise ProjectError(f"{path}: a build request is built only once it is confirmed",
                           [{"path": "--confirm", "message": "run `oncemore request` on it, check what it "
                                                             "would build, and pass its token with --confirm"}])
    if given != want:
        raise ProjectError(f"{path}: the token does not match the request (it or a file it names changed "
                           "since it was confirmed)",
                           [{"path": "--confirm", "message": "run `oncemore request` again and confirm what "
                                                             "it shows now"}])
    return request, build_project(to_project(request), path)


def expected_chapters(request):
    return [len(_chapter_times(t)) for t in request["titles"]]


# ---- reading the chapters back from a DVD image ---------------------------


def dvd_chapters(image):
    """The number of chapters of every title in a DVD image, in title order,
    read from VIDEO_TS.IFO (the title table) and each VTS_nn_0.IFO (its part
    of title table), through the image's ISO 9660 directory."""
    from .batch import _iso9660_files

    with open(image, "rb") as f:
        files = _iso9660_files(f)

        def read(name, offset, size):
            sector, length = files[name]
            if offset + size > length:
                raise OncemoreError(f"{image}: VIDEO_TS/{name} is shorter than its tables say")
            f.seek(sector * SECTOR + offset)
            return f.read(size)

        if "VIDEO_TS.IFO" not in files:
            raise OncemoreError(f"{image}: no VIDEO_TS.IFO")
        # VMG: TT_SRPT (sector at 0xC4): titles with their VTS number and VTS title number
        tt = struct.unpack(">I", read("VIDEO_TS.IFO", 0xC4, 4))[0] * SECTOR
        count = struct.unpack(">H", read("VIDEO_TS.IFO", tt, 2))[0]
        out = []
        ptt_cache = {}
        for k in range(count):
            entry = read("VIDEO_TS.IFO", tt + 8 + 12 * k, 12)
            chapters, vts, vts_ttn = struct.unpack(">H", entry[2:4])[0], entry[6], entry[7]
            name = f"VTS_{vts:02d}_0.IFO"
            if name not in ptt_cache:
                ptt = struct.unpack(">I", read(name, 0xC8, 4))[0] * SECTOR
                n, _, end = struct.unpack(">HHI", read(name, ptt, 8))
                offsets = list(struct.unpack(f">{n}I", read(name, ptt + 8, 4 * n)))
                ptt_cache[name] = [((offsets[j + 1] if j + 1 < n else end + 1) - offsets[j]) // 4
                                   for j in range(n)]
            parts = ptt_cache[name][vts_ttn - 1]
            if parts != chapters:
                raise OncemoreError(f"{image}: title {k + 1} has {chapters} chapters in VIDEO_TS.IFO "
                                    f"and {parts} in {name}")
            out.append(parts)
        return out
