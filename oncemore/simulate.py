"""A disc simulator: what a DVD player does with the project, key by key,
without encoding anything.

It follows the same rules as the navigation commands `author.py` writes
(registers, the root-menu dispatcher, play all, playlists, remembered
buttons, the Menu and Title keys), so pressing keys here gives the same
menus, highlighted buttons, titles and chapters as a player running the
built disc. tests/test_e2e.py checks that against libdvdnav on real discs.

The state is a plain dict (JSON-ready, so the app can keep it between
requests):

  domain      "menu" | "title" | "stopped"
  menu        menu id (domain "menu")
  button      highlighted button, 1-based (the player's SPRM 8; it is kept
              when a menu does not set it, as players do)
  title       title id, chapter (domain "title")
  audio       audio stream, 1-based; subtitle: 0 = off, else the stream
  playall     play-all flag (g2); playlist / item_end: playlist state (g0 / g12)
  menu_key    menu the Menu key opens during the current title (g3)
  remember    {menu id: last button used} for menus that remember it
  loops       times the current menu has played (g4)
  last_menu   menu shown last (for `lastmenu` end actions), None before any
  override    end action replacing the playing title's own (a button's
              `override`), None when there is none
  resume      {"title", "chapter", "button"} the Menu / Title key left, for resume
              buttons (the player's resume information; None once the
              title ended, as the resume flag register says)
  log         what happened on the last key, for the app to show
"""

from . import author, navigation
from .project import parse_action

KEYS = ("up", "down", "left", "right", "enter", "menu", "title", "next", "prev",
        "play", "end", "timeout")


class SimError(ValueError):
    pass


class Simulator:
    def __init__(self, project, layouts=None):
        """`layouts`: {menu id: [{"id", "rect", "nav", "auto", "action"}]} from
        MenuBuilder.layout. Without it buttons are laid out in a column in
        project order (enough for tests of the logic)."""
        self.p = project
        self.layouts = layouts or {}
        self.states = author.playlist_states(project) if project.playlists else []

    # -- helpers ---------------------------------------------------------------
    def menu(self, mid):
        m = self.p.menu(mid)
        if m is None:
            raise SimError(f"no menu {mid!r}")
        return m

    def buttons(self, m):
        if m.id in self.layouts:
            return self.layouts[m.id]
        rects = [(0, 40 * k, 100, 40 * k + 30) for k in range(len(m.buttons))]
        nav = navigation.compute([(b.id, r, b.nav) for b, r in zip(m.buttons, rects)])
        return [{"id": b.id, "rect": r, "nav": nav[b.id], "auto": b.auto_activate,
                 "action": b.action} for b, r in zip(m.buttons, rects)]

    def root(self):
        return self.p.menus[0] if self.p.menus else None

    @staticmethod
    def note(s, text):
        s["log"].append(text)

    # -- start -----------------------------------------------------------------
    def start(self):
        s = {"domain": "stopped", "menu": None, "button": 1, "title": None, "chapter": 0,
             "audio": 1, "subtitle": 0, "playall": 0, "playlist": 0, "item_end": 0,
             "menu_key": None, "remember": {}, "loops": 0, "resume": None, "override": None, "last_menu": None, "log": []}
        sub = author.default_subtitle(self.p)
        if sub is not None:
            s["subtitle"] = sub + 1
        kind, target, _ = parse_action(self.p.disc.first_play)
        self.note(s, f"first play: {self.p.disc.first_play}")
        if kind == "menu":
            self.via_root(s, target)
        elif kind == "playlist":
            self.playlist_start(s, target)
        elif kind == "playall":
            s["playall"] = 1
            self.play(s, self.p.titles[0].id)
        else:
            self.play(s, target)
        return s

    # -- moving around -----------------------------------------------------------
    def enter_menu(self, s, mid):
        m = self.menu(mid)
        s.update(domain="menu", menu=m.id, title=None, chapter=0, loops=0, last_menu=m.id)
        n = len(m.buttons)
        ids = [b.id for b in m.buttons]
        default = ids.index(m.default_button) + 1 if m.default_button else 1
        if author.button_reg(m):
            s["button"] = s["remember"].get(m.id) or default
        elif m.default_button:
            s["button"] = default
        elif author.first_button_on_entry(self.p, m):
            s["button"] = 1
        elif not 1 <= s["button"] <= n:
            s["button"] = 1
        self.note(s, f"menu {m.id}")

    def via_root(self, s, mid):
        """g1 = menu; call the root menu, whose pre-commands dispatch."""
        s["menu_key"] = None             # the root menu's pre clears g3
        self.enter_menu(s, mid)

    def play(self, s, tid, chapter=1):
        t = self.p.title(tid)
        if t is None:
            raise SimError(f"no title {tid!r}")
        s.update(domain="title", menu=None, title=t.id, chapter=chapter, loops=0)
        if self.p.uses_remote_menu:
            s["menu_key"] = t.remote_menu or self.root().id
        self.note(s, f"title {t.id} chapter {chapter}")

    def stop(self, s):
        s.update(domain="stopped", menu=None, title=None, chapter=0)
        self.note(s, "stop")

    def single(self, s):
        s["override"] = None
        if self.p.uses_playall:
            s["playall"] = 0
        if self.p.uses_playlists:
            s["playlist"] = s["item_end"] = 0

    def playlist_start(self, s, pid):
        state, _, _, item = next(x for x in self.states if x[1].id == pid)
        s["override"] = None
        if self.p.uses_playall:
            s["playall"] = 0
        s["playlist"], s["item_end"] = state, item.last or 0
        self.play(s, item.title_id, item.first)

    def menu_command(self, s, action):
        """A button or a menu time-out (menu domain)."""
        kind, target, num = parse_action(action)
        if kind == "menu":
            self.enter_menu(s, target)
        elif kind == "playlist":
            self.playlist_start(s, target)
        elif kind == "playall":
            if self.p.uses_playlists:
                s["playlist"] = s["item_end"] = 0
            s["playall"] = 1
            s["override"] = None
            self.play(s, self.p.titles[0].id)
        elif kind == "title":
            self.single(s)
            self.play(s, target)
        elif kind == "resume":
            r = s.get("resume")
            if r:
                # the player's resume: no <pre>, so the Menu key target the
                # root menu cleared stays cleared; the button register (SPRM 8)
                # comes back as it was
                s.update(domain="title", menu=None, title=r["title"], chapter=r["chapter"],
                         button=r["button"], loops=0)
                self.note(s, f"resume title {r['title']} chapter {r['chapter']}")
            else:
                self.single(s)
                self.play(s, self.p.titles[0].id)
        elif kind == "chapter":
            self.single(s)
            self.play(s, target, num)
        elif kind == "audio":
            s["audio"] = num
            self.note(s, f"audio {num}")
        elif kind == "subtitle":
            s["subtitle"] = num
            self.note(s, f"subtitle {'off' if not num else num}")
        else:
            self.stop(s)

    def end_command(self, s, action):
        """A title's or playlist's end action (title domain)."""
        kind, target, _ = parse_action(action)
        if kind == "menu":
            self.via_root(s, target)
        elif kind == "lastmenu":
            # g1 = the last menu; 0 before any: the root's dispatcher then takes
            # the Menu-key target (g3) or stays on the first menu
            key = s["menu_key"] if self.p.uses_remote_menu else None
            self.via_root(s, s["last_menu"] or key or self.root().id)
        elif kind == "title":
            self.play(s, target)
        else:
            self.stop(s)

    def post(self, s):
        """The title has ended: playlist, then play all, then its end action."""
        t = self.p.title(s["title"])
        s["resume"] = None
        if s.get("override"):
            action, s["override"] = s["override"], None
            self.note(s, f"override: {action}")
            self.end_command(s, action)
            return
        for state, pl, i, it in self.states:
            if it.title_id != t.id or s["playlist"] != state:
                continue
            if i + 1 < len(pl.items):
                nxt = pl.items[i + 1]
                s["playlist"], s["item_end"] = state + 1, nxt.last or 0
                self.play(s, nxt.title_id, nxt.first)
            else:
                s["playlist"] = s["item_end"] = 0
                self.end_command(s, pl.end_action)
            return
        if self.p.uses_playall:
            nxt = self.p.playall_next(t)
            if nxt is None:
                s["playall"] = 0
            elif s["playall"] == 1:
                self.play(s, nxt.id)
                return
        self.end_command(s, t.end_action)

    def title_key(self, s):
        """The VMGM title menu: the remote's Title / Top Menu key."""
        if self.p.uses_remote_menu:
            s["menu_key"] = None
        tk = self.p.disc.title_key
        kind, target, _ = parse_action(tk) if tk else ("menu", self.root().id, None)
        if kind == "playlist":
            self.playlist_start(s, target)
        elif kind in ("title", "playall"):
            s["override"] = None
            if self.p.uses_playlists:
                s["playlist"] = s["item_end"] = 0
            if self.p.uses_playall:
                s["playall"] = 1 if kind == "playall" else 0
            self.play(s, self.p.titles[0].id if kind == "playall" else target)
        else:
            self.via_root(s, target)

    # -- keys ------------------------------------------------------------------
    def press(self, s, key):
        """Apply one remote key to state `s` (changed in place and returned)."""
        s["log"] = []
        if key.startswith("select:"):
            key, arg = "select", key[7:]
        elif key not in KEYS:
            raise SimError(f"unknown key {key!r}")
        if s["domain"] == "stopped":
            return s
        if s["domain"] == "title" and key in ("menu", "title") and self.p.menus:
            s["resume"] = {"title": s["title"], "chapter": s["chapter"], "button": s["button"]}
        if key == "title":
            if self.p.menus:
                self.title_key(s)
            return s
        if s["domain"] == "menu":
            m = self.menu(s["menu"])
            geoms = self.buttons(m)
            if key in navigation.DIRECTIONS and geoms:
                cur = geoms[s["button"] - 1]
                ids = [g["id"] for g in geoms]
                s["button"] = ids.index(cur["nav"][key]) + 1
                if geoms[s["button"] - 1]["auto"] and s["button"] != ids.index(cur["id"]) + 1:
                    self.activate(s, m, geoms)
            elif key == "select":
                ids = [g["id"] for g in geoms]
                s["button"] = ids.index(arg) + 1 if arg in ids else int(arg)
            elif key == "enter" and geoms:
                self.activate(s, m, geoms)
            elif key == "timeout" and m.loop is not None:
                self.note(s, f"menu {m.id} timed out")
                self.menu_command(s, m.end_action)
            elif key == "menu":
                self.via_root(s, self.root().id)
            return s
        # title domain
        t = self.p.title(s["title"])
        n = len(t.chapters)
        if key == "menu" and self.p.menus:
            target = s["menu_key"] if self.p.uses_remote_menu else None
            self.via_root(s, target or self.root().id)
        elif key == "next":
            if s["chapter"] < n:
                s["chapter"] += 1
                self.note(s, f"chapter {s['chapter']}")
            else:
                self.post(s)
        elif key == "prev":
            s["chapter"] = max(1, s["chapter"] - 1)
            self.note(s, f"chapter {s['chapter']}")
        elif key == "play":
            self.play_chapter(s, t)
        elif key == "end":
            here = s["title"]
            while s["domain"] == "title" and s["title"] == here:
                self.play_chapter(s, t)
        return s

    def play_chapter(self, s, t):
        """Play to the end of the current chapter."""
        k = s["chapter"]
        if k in author.item_end_chapters(self.p, t) and s["item_end"] == k:
            self.post(s)
        elif k >= len(t.chapters):
            self.post(s)
        else:
            s["chapter"] = k + 1
            self.note(s, f"chapter {k + 1}")

    def activate(self, s, m, geoms):
        g = geoms[s["button"] - 1]
        self.note(s, f"button {g['id']} -> {g['action']}")
        if author.button_reg(m) and parse_action(g["action"])[0] not in ("audio", "subtitle"):
            s["remember"][m.id] = s["button"]
        b = next((x for x in m.buttons if x.id == g["id"]), None)
        if b is not None and b.audio:
            s["audio"] = b.audio
        if b is not None and b.subtitle is not None:
            s["subtitle"] = b.subtitle
        self.menu_command(s, g["action"])
        if b is not None and b.override and parse_action(g["action"])[0] in ("title", "chapter"):
            s["override"] = b.override

    def view(self, s):
        """What a viewer sees: (domain, menu id / title number, button / chapter)."""
        if s["domain"] == "menu":
            return ("menu", s["menu"], s["button"])
        if s["domain"] == "title":
            t = self.p.title(s["title"])
            return ("title", t.global_number, s["chapter"])
        return ("stopped", None, None)
