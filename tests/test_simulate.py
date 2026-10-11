"""The disc simulator and the navigation graph.

Unit tests run the simulator on projects without media. The end-to-end
test builds a disc that uses every navigation feature and drives the ISO
through libdvdnav and the simulator with the same keys, checking after each
key that both show the same menu and highlighted button, or the same title
and chapter.
"""

import json
import os
import random
import shutil
import tempfile
import unittest

from oncemore import graph, tools
from oncemore.project import build_project, load_project
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator

from .helpers import have, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

TOOLS_OK = (have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)


def project(data):
    return build_project(data, "/virtual/project.oncemore.json", check_files=False)


def rich_project():
    """Two titlesets, a playlist across them, play all, remote keys, a
    remembered menu, an auto button, an intro that times out, stream buttons,
    a resume button, end-action overrides (one back to the last menu), links
    that open a menu on a particular button (from a button and an override),
    a playlist that ends in a chapter of the other titleset, an override
    that starts play all."""
    d = sample_project()
    t1, t2 = d["titles"]
    t1["remote_menu"] = "chapters"
    t2.update({"aspect": "4:3", "audio": {"codec": "lpcm"}, "chapters": [0, 4, 8],
               "end_action": "title:t1"})
    d["disc"]["title_key"] = "menu:intro"
    main = d["menus"][0]
    main["buttons"] += [
        {"id": "all", "label": "PLAY ALL", "x": 470, "y": 160, "action": "playall"},
        {"id": "best", "label": "BEST OF", "x": 470, "y": 220, "action": "playlist:best"},
        {"id": "setup", "label": "SETUP", "x": 470, "y": 280, "action": "menu:setup"},
        {"id": "b2", "label": "B THEN SETUP", "x": 470, "y": 340, "action": "title:t2",
         "override": "menu:setup"},
        {"id": "b3", "label": "CH 2 THEN BACK", "x": 470, "y": 400, "action": "chapter:t1:2",
         "override": "lastmenu"},
        {"id": "b4", "label": "B THEN BACK", "x": 120, "y": 400, "action": "title:t2",
         "override": "menu:setup:back"},
        {"id": "tail", "label": "TAIL", "x": 120, "y": 160, "action": "playlist:tail"},
        {"id": "b5", "label": "B THEN ALL", "x": 300, "y": 160, "action": "title:t2",
         "override": "playall"}]
    d["menus"].append({"id": "setup", "remember_button": False, "buttons": [
        {"id": "a1", "label": "AUDIO 1", "x": 100, "y": 150, "action": "audio:1"},
        {"id": "off", "label": "SUBTITLES OFF", "x": 100, "y": 210, "action": "subtitle:off"},
        {"id": "go", "label": "GO", "x": 100, "y": 270, "action": "title:t2",
         "auto_activate": True},
        {"id": "back", "label": "BACK", "x": 100, "y": 330, "action": "menu:main"},
        {"id": "res", "label": "RESUME", "x": 420, "y": 150, "action": "resume"},
        {"id": "tob", "label": "TO B", "x": 420, "y": 210, "action": "menu:main:b"}]})
    d["menus"].append({"id": "intro", "background_video": "media/sample_a.mp4",
                       "duration": 4, "loop": 1, "end_action": "menu:main",
                       "buttons": [{"id": "skip", "label": "SKIP", "x": 80, "y": 380,
                                    "action": "chapter:t1:3"}]})
    d["playlists"] = [{"id": "best", "items": ["t1:2", "t2:2-3", "t1:1"],
                       "end_action": "menu:setup"},
                      {"id": "tail", "items": ["t2:3"], "end_action": "chapter:t1:3"}]
    return d


class TestSimulator(unittest.TestCase):
    def setUp(self):
        self.p = project(rich_project())
        self.sim = Simulator(self.p)

    def keys(self, *keys, s=None):
        s = s or self.sim.start()
        for k in keys:
            self.sim.press(s, k)
        return s

    def test_start(self):
        s = self.sim.start()
        self.assertEqual(self.sim.view(s), ("menu", "main", 1))
        self.assertEqual((s["audio"], s["subtitle"]), (1, 0))

    def test_button_index_kept_or_reset(self):
        s = self.sim.start()
        self.sim.press(s, "select:setup")          # button 6 of main
        self.sim.press(s, "enter")
        self.assertEqual(s["button"], 1)          # setup has 5 buttons: back to 1
        self.sim.press(s, "select:back")
        self.sim.press(s, "enter")
        self.assertEqual(self.sim.view(s), ("menu", "main", 6))     # main remembers SETUP

    def test_links_to_a_button(self):
        s = self.keys("select:setup", "enter", "select:tob", "enter")
        self.assertEqual(self.sim.view(s), ("menu", "main", 3))     # B, not the remembered 6
        self.sim.press(s, "select:b4")
        self.sim.press(s, "enter")
        self.sim.press(s, "end")                   # its override: setup, on BACK
        self.assertEqual(self.sim.view(s), ("menu", "setup", 4))

    def test_auto_button_and_streams(self):
        s = self.keys("select:setup", "enter", "select:off", "enter")
        self.assertEqual((s["domain"], s["subtitle"]), ("menu", 0))
        self.sim.press(s, "down")                  # onto GO: runs at once
        self.assertEqual(self.sim.view(s), ("title", 2, 1))

    def test_playlist(self):
        s = self.keys("select:best", "enter")
        seen = [self.sim.view(s)]
        while s["domain"] == "title":
            self.sim.press(s, "play")
            seen.append(self.sim.view(s))
        self.assertEqual(seen, [("title", 1, 2), ("title", 2, 2), ("title", 2, 3),
                                ("title", 1, 1), ("menu", "setup", 1)])   # no pre: button 1

    def test_play_all_and_end_actions(self):
        s = self.keys("select:all", "enter")
        self.sim.press(s, "end")
        self.assertEqual(self.sim.view(s), ("title", 2, 1))
        self.sim.press(s, "end")                   # last title: play all ends, t2 -> t1
        self.assertEqual(self.sim.view(s), ("title", 1, 1))
        self.assertEqual(s["playall"], 0)
        self.sim.press(s, "end")
        self.assertEqual(self.sim.view(s), ("menu", "main", 4))      # t1 ends at main

    def test_remote_keys(self):
        s = self.keys("select:b", "enter")
        self.sim.press(s, "end")                   # t2 ends -> t1 (its end action)
        self.sim.press(s, "next")
        self.assertEqual(self.sim.view(s), ("title", 1, 2))
        self.sim.press(s, "menu")                  # remote_menu of t1
        self.assertEqual(s["menu"], "chapters")
        self.sim.press(s, "title")                 # disc.title_key
        self.assertEqual(s["menu"], "intro")
        self.sim.press(s, "timeout")
        self.assertEqual(s["menu"], "main")
        s = self.keys("select:b", "enter", "menu")
        self.assertEqual(s["menu"], "main")        # t2 has no remote_menu: the root menu
        s = self.keys("title", "enter")            # intro SKIP -> chapter 3
        self.assertEqual(self.sim.view(s), ("title", 1, 3))
        self.sim.press(s, "next")                  # past the last chapter: the title ends
        self.assertEqual(s["menu"], "main")

    def test_override(self):
        s = self.keys("select:b2", "enter")
        self.assertEqual(self.sim.view(s), ("title", 2, 1))
        self.sim.press(s, "end")                     # t2 ends: the override, not t1
        self.assertEqual(s["menu"], "setup")
        self.sim.press(s, "select:go")
        self.sim.press(s, "enter")                   # t2 again, without the override
        self.sim.press(s, "end")
        self.assertEqual(self.sim.view(s), ("title", 1, 1))   # its own end action
        s = self.keys("select:b2", "enter", "menu", "select:all", "enter", "end")
        self.assertEqual(self.sim.view(s), ("title", 2, 1))   # play all cleared it

    def test_last_menu(self):
        s = self.keys("select:b3", "enter")
        self.assertEqual(self.sim.view(s), ("title", 1, 2))
        self.sim.press(s, "end")
        self.assertEqual(s["menu"], "main")          # the menu it was started from
        s = self.keys("select:b3", "enter", "menu", "select:back", "enter")
        self.assertEqual((s["menu"], s["last_menu"]), ("main", "main"))
        s = self.keys("select:b3", "enter", "menu")  # t1's Menu key: the chapters menu
        self.assertEqual(s["last_menu"], "chapters")
        self.sim.press(s, "title")                   # -> intro, which times out to main
        self.sim.press(s, "timeout")
        self.assertEqual(s["last_menu"], "main")

    def test_resume(self):
        s = self.keys("select:setup", "enter", "select:res", "enter")
        self.assertEqual(self.sim.view(s), ("title", 1, 1))     # nothing to resume yet
        self.sim.press(s, "next")
        self.sim.press(s, "menu")                               # t1 -> chapters menu
        self.sim.press(s, "title")
        self.sim.press(s, "timeout")
        self.sim.press(s, "select:setup")
        self.sim.press(s, "enter")
        self.sim.press(s, "select:res")
        self.sim.press(s, "enter")
        self.assertEqual(self.sim.view(s), ("title", 1, 2))     # back where it was
        self.assertEqual(s["log"], ["button res -> resume", "resume title t1 chapter 2"])
        self.sim.press(s, "menu")
        self.assertEqual(s["menu"], "main")         # the resumed title's Menu key: root
        s = self.keys("select:b", "enter", "end", "end")        # t2, then t1 ends at main
        self.assertEqual(s["menu"], "main")
        self.sim.press(s, "select:setup")
        self.sim.press(s, "enter")
        self.sim.press(s, "select:res")
        self.sim.press(s, "enter")
        self.assertEqual(self.sim.view(s), ("title", 1, 1))     # it ended: from the start


class TestGraph(unittest.TestCase):
    def test_flowchart_and_reachability(self):
        p = project(rich_project())
        g = graph.build(p)
        ids = {n["id"] for n in g["nodes"]}
        self.assertTrue({"fp", "title_key", "menu:main", "menu:setup", "menu:intro",
                         "title:t1", "title:t2", "playlist:best", "playall"} <= ids)
        edges = {(e["from"], e["to"], e["kind"]) for e in g["edges"]}
        self.assertIn(("menu:intro", "menu:main", "timeout"), edges)
        self.assertIn(("menu:intro", "title:t1", "button"), edges)
        self.assertIn(("title:t1", "menu:chapters", "menu_key"), edges)
        self.assertIn(("playlist:best", "title:t2", "item"), edges)
        self.assertIn(("menu:setup", "menu:main", "button"), edges)
        # TO B: the button, then the one it opens on
        self.assertIn("tob · b", [e["label"] for e in g["edges"] if e["from"] == "menu:setup"])
        self.assertIn(("title:t1", "title:t2", "playall"), edges)
        self.assertNotIn("stop", ids)               # nothing stops
        cols = {n["id"]: n["col"] for n in g["nodes"]}
        self.assertEqual(cols["fp"], 0)
        self.assertEqual(cols["menu:main"], 1)
        self.assertEqual([n for n in graph.check(p) if n["level"] == "warning"], [])

    def test_problems(self):
        d = sample_project()
        d["menus"][0]["buttons"][0]["action"] = "title:t1"       # no play all
        d["menus"].append({"id": "lost", "buttons": [
            {"id": "a", "label": "AUDIO", "x": 100, "y": 100, "action": "audio:1"}]})
        d["titles"].append({"id": "t3", "source": "media/sample_a.mp4", "end_action": "stop"})
        d["playlists"] = [{"id": "unused", "items": ["t1"]}]
        notes = graph.check(project(d))
        text = "\n".join(f"{n['level']} {n['path']}: {n['message']}" for n in notes)
        self.assertIn("warning menu:lost: menu 'lost' cannot be reached", text)
        self.assertIn("warning menu:lost: menu 'lost' has no button that leaves it", text)
        self.assertIn("warning title:t3: title 't3' cannot be reached", text)
        self.assertIn("info title:t3: playback stops after title 't3'", text)
        self.assertIn("warning playlist:unused: playlist 'unused' is not started", text)


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), dvdauthor, spumux and an ISO tool")
@unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
class TestSimulatorMatchesDisc(unittest.TestCase):
    """Random remote-control sessions on a built disc: libdvdnav and the
    simulator must agree after every key."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-sim-")
        rc, _, err = run_cli("init", "sim", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "sim", "project.oncemore.json")
        with open(path, "w") as f:
            json.dump(rich_project(), f)
        cls.iso = os.path.join(cls.tmp, "sim.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out
        from oncemore.menu import MenuBuilder
        cls.project = load_project(path)
        mb = MenuBuilder(cls.project, os.path.join(cls.tmp, "layout"))
        cls.layouts = {m.id: [{"id": g.id, "rect": g.rect, "nav": g.nav, "auto": g.auto,
                               "action": g.action} for g in mb.layout(m)]
                       for m in cls.project.menus}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -- the player side ---------------------------------------------------------
    def settle(self, d):
        """Run until something is shown: a menu with buttons, or a title."""
        def shown(e):
            return e == dvdnav_sim.EV_NAV_PACKET and (
                d.domain() == "title" or (d.domain() in ("vtsm", "vmgm") and d.button_count()))
        try:
            d.run_until(shown, 3_000_000)
        except dvdnav_sim.NavError:
            if not d.stopped:
                raise

    def play_until(self, d, changed):
        def ev(e):
            if e != dvdnav_sim.EV_NAV_PACKET:
                return False
            if d.domain() == "title":
                return changed(d.title_part())
            return d.domain() in ("vtsm", "vmgm") and d.button_count() > 0
        try:
            d.run_until(ev, 3_000_000)
        except dvdnav_sim.NavError:
            if not d.stopped:
                raise

    def view(self, d):
        if d.stopped:
            return ("stopped", None, None)
        if d.domain() == "title":
            return ("title",) + d.title_part()
        menu = next(m for m in self.project.menus if m.number == d.pgcn())
        return ("menu", menu.id, d.highlight())

    def player_key(self, d, key, before):
        if key in ("up", "down", "left", "right"):
            old = d.highlight()
            new = d.move(key)
            geoms = {i + 1: g for i, g in enumerate(self.layouts[before[1]])}
            if new != old and geoms[new]["auto"]:
                self.settle(d)
        elif key == "enter":
            d.activate()
            self.settle(d)
        elif key == "menu":
            d.menu_key()
            self.settle(d)
        elif key == "title":
            d.title_key()
            self.settle(d)
        elif key == "timeout":
            pgc = d.pgcn()

            def left(e):
                return e == dvdnav_sim.EV_NAV_PACKET and (
                    d.domain() == "title" or (d.button_count() > 0 and d.pgcn() != pgc))
            try:
                d.run_until(left, 3_000_000)
            except dvdnav_sim.NavError:
                if not d.stopped:
                    raise
        elif key in ("next", "prev"):
            here = d.title_part()
            ok = d.next_chapter() if key == "next" else d.prev_chapter()
            if ok:
                self.play_until(d, lambda tp: tp != here or key == "prev")
        elif key == "play":
            here = d.title_part()
            self.play_until(d, lambda tp: tp != here)
        elif key == "end":
            t = d.title_part()[0]
            self.play_until(d, lambda tp: tp[0] != t)

    # -- the session ---------------------------------------------------------------
    def keys_for(self, view, rng):
        if view[0] == "menu":
            m = self.project.menu(view[1])
            keys = ["up", "down", "left", "right", "enter", "enter"]
            if m.loop is not None:
                keys.append("timeout")
            keys += ["menu", "title"] if rng.random() < 0.15 else []
            return keys
        return ["play", "play", "play", "next", "prev", "menu", "title", "end"]

    def test_resume(self):
        """RESUME before any title, after the Menu key, and after a title ended."""
        sim = Simulator(self.project, self.layouts)
        s = sim.start()
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.settle(d)

            def press(*keys):
                for key in keys:
                    before = sim.view(s)
                    sim.press(s, key)
                    if key.startswith("select:"):
                        ids = [g["id"] for g in self.layouts[before[1]]]
                        d.select(ids.index(key[7:]) + 1)
                    else:
                        self.player_key(d, key, before)
                    self.assertEqual(self.view(d), sim.view(s), f"{before} --{key}-->")
                return sim.view(s)

            resume = ("select:setup", "enter", "select:res", "enter")
            self.assertEqual(press(*resume), ("title", 1, 1))       # nothing to resume
            self.assertEqual(press("next", "menu", "title", "timeout"), ("menu", "main", 6))
            self.assertEqual(press(*resume), ("title", 1, 2))       # where the Menu key left
            self.assertEqual(press("end")[0], "menu")               # t1 ended
            self.assertEqual(press(*resume), ("title", 1, 1))

    def test_button_links_on_disc(self):
        """TO B opens main on B (not its remembered button); B THEN BACK's
        override opens setup on BACK after title 2 (in titleset 2)."""
        sim = Simulator(self.project, self.layouts)
        s = sim.start()
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.settle(d)

            def press(*keys):
                for key in keys:
                    before = sim.view(s)
                    sim.press(s, key)
                    if key.startswith("select:"):
                        ids = [g["id"] for g in self.layouts[before[1]]]
                        d.select(ids.index(key[7:]) + 1)
                    else:
                        self.player_key(d, key, before)
                    self.assertEqual(self.view(d), sim.view(s), f"{before} --{key}-->")
                return sim.view(s)

            self.assertEqual(press("select:setup", "enter", "select:tob", "enter"),
                             ("menu", "main", 3))
            self.assertEqual(press("select:b4", "enter"), ("title", 2, 1))
            self.assertEqual(press("end"), ("menu", "setup", 4))

    def test_end_actions_on_disc(self):
        """TAIL plays chapter 3 of title 2 (titleset 2), then chapter 3 of
        title 1 (through the VMGM); B THEN ALL plays title 2, then all."""
        sim = Simulator(self.project, self.layouts)
        s = sim.start()
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.settle(d)

            def press(*keys):
                for key in keys:
                    before = sim.view(s)
                    sim.press(s, key)
                    if key.startswith("select:"):
                        ids = [g["id"] for g in self.layouts[before[1]]]
                        d.select(ids.index(key[7:]) + 1)
                    else:
                        self.player_key(d, key, before)
                    self.assertEqual(self.view(d), sim.view(s), f"{before} --{key}-->")
                return sim.view(s)

            self.assertEqual(press("select:tail", "enter"), ("title", 2, 3))
            self.assertEqual(press("end"), ("title", 1, 3))
            self.assertEqual(press("end")[:2], ("menu", "main"))
            self.assertEqual(press("select:b5", "enter"), ("title", 2, 1))
            self.assertEqual(press("end"), ("title", 1, 1))
            self.assertEqual(press("end"), ("title", 2, 1))      # play all goes on

    def test_override_on_disc(self):
        """B THEN SETUP plays title 2 and then the setup menu, instead of
        title 2's own end action (title 1); GO plays it without."""
        sim = Simulator(self.project, self.layouts)
        s = sim.start()
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.settle(d)

            def press(*keys):
                for key in keys:
                    before = sim.view(s)
                    sim.press(s, key)
                    if key.startswith("select:"):
                        ids = [g["id"] for g in self.layouts[before[1]]]
                        d.select(ids.index(key[7:]) + 1)
                    else:
                        self.player_key(d, key, before)
                    self.assertEqual(self.view(d), sim.view(s), f"{before} --{key}-->")
                return sim.view(s)

            self.assertEqual(press("select:b2", "enter"), ("title", 2, 1))
            self.assertEqual(press("end")[:2], ("menu", "setup"))
            self.assertEqual(press("select:go", "enter", "end"), ("title", 1, 1))

    def test_random_sessions(self):
        for seed in range(12):
            rng = random.Random(seed)
            sim = Simulator(self.project, self.layouts)
            s = sim.start()
            history = []
            with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
                self.settle(d)
                self.assertEqual(self.view(d), sim.view(s), "start")
                for step in range(30):
                    before = sim.view(s)
                    if before[0] == "stopped":
                        break
                    key = rng.choice(self.keys_for(before, rng))
                    history.append(f"{before} --{key}-->")
                    sim.press(s, key)
                    self.player_key(d, key, before)
                    with self.subTest(seed=seed, step=step):
                        self.assertEqual(self.view(d), sim.view(s), "\n".join(history))
                    if self.view(d) != sim.view(s):
                        break


if __name__ == "__main__":
    unittest.main()
