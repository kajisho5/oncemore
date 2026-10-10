"""Built-in menu templates: starting points that fill in buttons for the
project's titles, chapter menus, playlists and streams.

Each template returns an ordinary menu object (the same JSON as in
project.oncemore.json), laid out on the 720-wide menu grid for the disc's
height, so everything stays editable afterwards.
"""

from .project import STANDARDS

TEMPLATES = {
    "classic": {"en": "Classic — title and a column of buttons on a panel",
                "ja": "クラシック — タイトルとパネル上の縦並びボタン"},
    "banner": {"en": "Banner — buttons in a bar along the bottom",
               "ja": "バナー — 下部の帯に横並びのボタン"},
    "minimal": {"en": "Minimal — centred title, buttons below",
                "ja": "ミニマル — 中央のタイトルと下のボタン"},
    "setup": {"en": "Setup — audio and subtitle choices with a BACK button",
              "ja": "設定 — 音声・字幕の切り替えと BACK ボタン"},
}


def _entries(project):
    """(label, action) for the main things a menu can start, in order."""
    titles = project.get("titles", [])
    out = []
    if len(titles) > 1:
        out.append(("PLAY ALL", "playall"))
    for t in titles[:6]:
        out.append(((t.get("name") or t["id"]).upper()[:24], f"title:{t['id']}"))
    for t in titles:
        cm = t.get("auto_chapter_menu")
        if cm:
            mid = (cm.get("id") if isinstance(cm, dict) else None) or f"chapters_{t['id']}"
            out.append(("SCENES" if len(titles) == 1 else
                        f"SCENES: {(t.get('name') or t['id']).upper()}"[:24], f"menu:{mid}"))
    for pl in project.get("playlists", [])[:3]:
        out.append(((pl.get("name") or pl["id"]).upper()[:24], f"playlist:{pl['id']}"))
    if not out:
        out.append(("PLAY", "stop"))
    return out[:8]


def _streams(project):
    titles = project.get("titles", [])
    n_audio = max([len(t.get("audio_tracks", [])) for t in titles] + [1])
    n_subs = max([len(t.get("subtitles", [])) for t in titles] + [0])
    return n_audio, n_subs


def _fit(label, width, size):
    """Shorten `label` so it stays within `width` menu pixels at `size`
    (a generous 0.62 em per character for bold caps)."""
    n = max(3, int(width / (size * 0.62)))
    return label if len(label) <= n else label[:n - 3].rstrip() + "..."   # ASCII: any font


def _row_size(dy, largest):
    """Font size that leaves room for the underline and hit-area margins."""
    return max(16, min(largest, dy - 18))


def _buttons(entries, x, y0, dy, size):
    used, out = set(), []
    for k, (label, action) in enumerate(entries):
        bid = "".join(c for c in label.lower() if c.isalnum())[:20] or "button"
        while bid in used:
            bid += "2"
        used.add(bid)
        out.append({"id": bid, "label": label, "x": x, "y": y0 + k * dy, "action": action,
                    "size": size})
    return out


def make_menu(template, project, menu_id, back=None):
    """A new menu object for `project` (project JSON) from `template`."""
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}")
    disc = project["disc"]
    H = STANDARDS[disc["standard"]][1]
    k = H / 480
    label = disc.get("label", "MY DISC").replace("_", " ")
    entries = _entries(project)
    menu = {"id": menu_id, "background_color": "#101820", "highlight_color": "#FFD400",
            "select_color": "#FF5A00"}
    if template == "classic":
        n = len(entries)
        dy = round(min(52, 300 / max(n, 1)) * k)
        dy += dy % 2
        top = round(150 * k)
        menu.update({
            "background_color": "#0B1A2E",
            "shapes": [{"x": 60, "y": top - round(20 * k), "w": 330,
                        "h": n * dy + round(30 * k), "color": "#00000099"},
                       {"x": 60, "y": round(118 * k), "w": 330, "h": 4, "color": "#FFD400"}],
            "texts": [{"text": label, "x": 60, "y": round(60 * k), "size": 44,
                       "shadow": "#000000AA"}],
            "buttons": [dict(b, label=_fit(b["label"], 290, b["size"]))
                        for b in _buttons(entries, 84, top, dy, _row_size(dy, 30))],
        })
    elif template == "banner":
        y = round(392 * k)
        n = len(entries[:5])
        step = 600 // max(n, 1)
        buttons = _buttons(entries[:5], 0, y, 0, 22)
        for j, b in enumerate(buttons):
            b["x"] = 60 + j * step
            b["label"] = _fit(b["label"], step - 24, 22)
        menu.update({
            "background_color": "#151515",
            "shapes": [{"x": 0, "y": y - round(18 * k), "w": 720, "h": round(64 * k),
                        "color": "#000000B3"}],
            "texts": [{"text": label, "x": 60, "y": round(70 * k), "size": 52,
                       "outline": "#000000", "outline_width": 3}],
            "buttons": buttons,
        })
    elif template == "minimal":
        dy = round(min(48, 240 / len(entries)) * k)
        dy += dy % 2
        menu.update({
            "background_color": "#000000",
            "texts": [{"text": label, "x": 200, "y": round(110 * k), "size": 48}],
            "buttons": _buttons(entries, 290, round(220 * k), dy, _row_size(dy, 28)),
        })
    else:  # setup
        n_audio, n_subs = _streams(project)
        entries = [(f"AUDIO {a + 1}", f"audio:{a + 1}") for a in range(n_audio)]
        entries += [(f"SUBTITLES {s + 1}", f"subtitle:{s + 1}") for s in range(n_subs)]
        if n_subs:
            entries.append(("SUBTITLES OFF", "subtitle:off"))
        entries.append(("BACK", back or "stop"))
        dy = round(min(46, 320 / len(entries)) * k)
        dy += dy % 2
        menu.update({
            "background_color": "#1A1026",
            "texts": [{"text": "SETUP", "x": 80, "y": round(50 * k), "size": 40}],
            "buttons": _buttons(entries, 100, round(130 * k), dy, _row_size(dy, 26)),
        })
    return menu
