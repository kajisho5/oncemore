"""The disc's navigation as a graph, and the checks that read it.

Nodes are the places a viewer can be: the first-play action ("fp"), every
menu, title and playlist, and "stop". Edges are everything that moves the
viewer from one to another: buttons, a menu's time-out, a title's or a
playlist's end, play all, the remote's Menu key during a title and its
Title key. The app draws this as the flowchart; `check()` walks it to find
what a viewer can never reach and where they get stuck.
"""

import os

from .project import parse_action

STOP = "stop"


def node_id(kind, target=None):
    return f"{kind}:{target}" if target else kind


def _target(action, project=None):
    """Node an action leads to, and an edge label for chapter jumps.
    Audio / subtitle buttons stay on the menu (None). A resume button goes
    back to the title that was playing; drawn to the first title, which it
    plays when there is nothing to resume."""
    kind, target, num = parse_action(action)
    if kind == "resume":
        titles = project.titles if project else []
        return (node_id("title", titles[0].id), "resume") if titles else (None, None)
    if kind in ("audio", "subtitle"):
        return None, None
    if kind == "stop":
        return STOP, None
    if kind == "playall":
        return "playall", None
    if kind == "lastmenu":
        return "lastmenu", None
    if kind == "chapter":
        return node_id("title", target), f"ch {num}"
    if kind == "menu" and num:
        return node_id("menu", target), num          # opens on that button
    return node_id(kind, target), None


def build(project):
    """{"nodes": [...], "edges": [...]} for the flowchart (JSON-ready)."""
    nodes, edges = [], []

    def edge(src, action, kind, label=None, transition=None):
        dst, extra = _target(action, project)
        if dst is not None:
            e = {"from": src, "to": dst, "kind": kind,
                 "label": " · ".join(x for x in (label, extra) if x) or None}
            if transition:
                # (the link plays this video first)
                e["transition"] = os.path.basename(transition)
            edges.append(e)

    nodes.append({"id": "fp", "kind": "first_play", "label": "First play"})
    edge("fp", project.disc.first_play, "first_play")
    if project.disc.title_key:
        nodes.append({"id": "title_key", "kind": "title_key", "label": "Title key"})
        edge("title_key", project.disc.title_key, "title_key")
    for m in project.menus:
        # (a page of a menu with pages: "main · 2/3")
        label = f"{m.page_of} · {m.page}/{m.pages}" if m.page_of else m.id
        nodes.append({"id": node_id("menu", m.id), "kind": "menu", "label": label,
                      "generated": m.generated, "buttons": len(m.buttons),
                      "loop": m.loop})
        for b in m.buttons:
            edge(node_id("menu", m.id), b.action, "button", b.id, b.transition)
            # the title it plays then ends where the override says
            if b.override and parse_action(b.action)[0] in ("title", "chapter"):
                edge(node_id("title", parse_action(b.action)[1]), b.override, "override",
                     f"override ({m.id}/{b.id})")
        if m.loop is not None:
            edge(node_id("menu", m.id), m.end_action, "timeout",
                 f"after {m.loop} play{'s' if m.loop != 1 else ''}")
    uses_playall = project.uses_playall
    for t in project.titles:
        nid = node_id("title", t.id)
        nodes.append({"id": nid, "kind": "title", "label": t.name or t.id,
                      "chapters": len(t.chapters), "number": t.global_number or t.number})
        edge(nid, t.end_action, "end")
        for b in t.buttons:
            edge(nid, b.action, "button", b.id)
        if project.menus:
            edges.append({"from": nid, "to": node_id("menu", t.remote_menu or
                                                      project.menus[0].id),
                          "kind": "menu_key", "label": "Menu key"})
        nxt = project.playall_next(t) if uses_playall else None
        if nxt is not None:
            edges.append({"from": nid, "to": node_id("title", nxt.id), "kind": "playall",
                          "label": "play all"})
    if uses_playall and project.titles:
        nodes.append({"id": "playall", "kind": "playall", "label": "Play all"})
        edges.append({"from": "playall", "to": node_id("title", project.titles[0].id),
                      "kind": "playall", "label": None})
    for pl in project.playlists:
        nid = node_id("playlist", pl.id)
        nodes.append({"id": nid, "kind": "playlist", "label": pl.name or pl.id,
                      "items": len(pl.items)})
        for i, it in enumerate(pl.items):
            rng = "" if it.first == 1 and it.last is None else \
                f"ch {it.first}" + (f"-{it.last}" if it.last and it.last != it.first else "")
            edges.append({"from": nid, "to": node_id("title", it.title_id), "kind": "item",
                          "label": f"{i + 1}" + (f" · {rng}" if rng else "")})
        edge(nid, pl.end_action, "end")
    if any(e["to"] == STOP for e in edges):
        nodes.append({"id": STOP, "kind": "stop", "label": "Stop"})
    if any(e["to"] == "lastmenu" for e in edges):
        nodes.append({"id": "lastmenu", "kind": "last_menu", "label": "Last menu"})
    _layout(nodes, edges)
    return {"nodes": nodes, "edges": edges}


def reachable(graph, roots=("fp", "title_key")):
    """Node ids a viewer can get to from first play (and the Title key)."""
    nxt = {}
    for e in graph["edges"]:
        nxt.setdefault(e["from"], []).append(e["to"])
    ids = {n["id"] for n in graph["nodes"]}
    out = {r for r in roots if r in ids}
    todo = list(out)
    while todo:
        for m in nxt.get(todo.pop(), []):
            if m not in out:
                out.add(m)
                todo.append(m)
    return out


def _layout(nodes, edges):
    """Columns for the flowchart: first play, then breadth-first distance.
    Unreachable nodes go to a last column."""
    nxt = {}
    for e in edges:
        nxt.setdefault(e["from"], []).append(e["to"])
    col = {"fp": 0}
    if any(n["id"] == "title_key" for n in nodes):
        col["title_key"] = 0
    queue = [n for n in col]
    while queue:
        n = queue.pop(0)
        for m in nxt.get(n, []):
            if m not in col:
                col[m] = col[n] + 1
                queue.append(m)
    last = max(col.values()) + 1 if col else 0
    rows = {}
    for n in nodes:
        c = col.get(n["id"], last)
        n["col"] = c
        n["row"] = rows.get(c, 0)
        rows[c] = n["row"] + 1


def check(project):
    """Notes about the navigation: [{"level", "path", "message"}], where
    path is the flowchart node ("menu:<id>", "title:<id>", "playlist:<id>").

    level "warning": something a viewer cannot reach or cannot leave;
    level "info": playback simply stops somewhere (often intended)."""
    g = build(project)
    seen = reachable(g)
    notes = []
    for m in project.menus:
        where = node_id("menu", m.id)
        if node_id("menu", m.id) not in seen:
            notes.append({"level": "warning", "path": where,
                          "message": f"menu {m.id!r} cannot be reached from the start of "
                                     "the disc (no button, end action or remote key leads "
                                     "to it)"})
        leaves = [b for b in m.buttons if parse_action(b.action)[0] not in ("audio",
                                                                             "subtitle")]
        if not leaves and m.loop is None:
            notes.append({"level": "warning", "path": where,
                          "message": f"menu {m.id!r} has no button that leaves it and no "
                                     "time-out: viewers are stuck unless they use the "
                                     "remote's Title key"})
        if m.loop is None and m.end_action != "stop":
            notes.append({"level": "info", "path": where,
                          "message": f"menu {m.id!r} loops forever, so its end action "
                                     "is never used (set a loop count)"})
    for t in project.titles:
        where = node_id("title", t.id)
        if where not in seen:
            notes.append({"level": "warning", "path": where,
                          "message": f"title {t.id!r} cannot be reached: no button, "
                                     "playlist or end action plays it"})
        if parse_action(t.end_action)[0] == "stop" and project.menus:
            notes.append({"level": "info", "path": where,
                          "message": f"playback stops after title {t.id!r} (choose a menu "
                                     "to return to it instead)"})
    for pl in project.playlists:
        if node_id("playlist", pl.id) not in seen:
            notes.append({"level": "warning", "path": node_id("playlist", pl.id),
                          "message": f"playlist {pl.id!r} is not started by any button, "
                                     "end action or remote key"})
    return notes
