"""Buttons over a title (DVD): the project's buttons, their checks, the
commands they run, the key frames that start a VOBU where they change, the
simulator and the flowchart; and a built disc driven with libdvdnav."""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from oncemore import author, encode, graph, titlebuttons, tools
from oncemore.errors import ProjectError
from oncemore.project import build_project, button_stretches, title_fps
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator

from .helpers import have, json_lines, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

TOOLS_OK = (have("ffmpeg", "ffprobe") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)

GO = {"id": "go", "start": 2, "end": 6, "x": 100, "y": 100, "width": 200, "height": 60,
      "action": "title:t1"}
BACK = {"id": "back", "start": 2, "end": 6, "x": 100, "y": 300, "width": 200, "height": 60,
        "action": "menu:main"}


def data(*buttons, **title):
    d = sample_project()
    d["titles"][1].update({"chapters": [0, 8], "buttons": list(buttons) or [GO, BACK], **title})
    return d


def project(d):
    return build_project(d, "/virtual/project.oncemore.json", check_files=False)


def problems(d):
    with self_raises() as e:
        project(d)
    return " | ".join(i["message"] for i in e.issues)


class self_raises:
    def __enter__(self):
        return self

    def __exit__(self, kind, value, tb):
        if not isinstance(value, ProjectError):
            raise AssertionError(f"expected a ProjectError, got {value!r}")
        self.issues = value.issues
        return True


class TestModel(unittest.TestCase):
    def test_loaded(self):
        to_end = {k: v for k, v in BACK.items() if k != "end"}
        p = project(data(GO, dict(to_end, start=4),
                         button_colors={"highlight": "#00FF00", "select": "#0000FF80"}))
        t = p.title("t2")
        self.assertEqual([(b.id, b.start, b.end, b.x, b.width) for b in t.buttons],
                         [("go", 2.0, 6.0, 100, 200), ("back", 4.0, None, 100, 200)])
        self.assertEqual((t.button_highlight, t.button_select), ("#00FF00", "#0000FF80"))
        # the stretches: go alone, go and back, back alone to the end
        self.assertEqual(button_stretches(t), [(2.0, 4.0), (4.0, 6.0), (6.0, None)])
        self.assertIn("title:t1", p.actions())

    def test_refused(self):
        cases = [
            (data(dict(GO, end=1)), "must be after start"),
            (data(dict(GO, x=600)), "is not inside the 720 x 480 picture"),
            (data(GO, dict(BACK, id="go")), "another button of the title is 'go'"),
            (data(dict(GO, start=7.5)), "leave at least 1.0 s"),            # 0.5 s from chapter 2
            (data(GO, dict(BACK, start=2.4)), "leave at least 1.0 s"),
            (data(dict(GO, action="menu:nope")), "no menu with id 'nope'"),
            (data(subtitles=[{"file": "media/a.srt"}]), "cannot have subtitles yet"),
            (data(*[dict(GO, id=f"b{k}") for k in range(37)]), "at most 36 at a time"),
        ]
        for d, why in cases:
            self.assertIn(why, problems(d))
        bad = data(dict(GO, action="resume"))
        with self.assertRaises(ProjectError):                    # (not in the schema's pattern)
            project(bad)

    def test_commands(self):
        p = project(data(GO, BACK, dict(GO, id="snd", start=6, end=8, action="audio:1")))
        t = p.title("t2")
        texts = [author.title_button_command(p, t, b.action) for b in t.buttons]
        self.assertEqual(texts[0], author._single(p) + "jump title 1;")   # (play all ends)
        self.assertIn("g2 = 0;", texts[0])
        self.assertTrue(texts[1].endswith("call menu entry root;"), texts[1])
        self.assertEqual(texts[2], "audio = 0;")
        xml = author.build_xml(p, {m.id: "m.mpg" for m in p.menus},
                               {x.id: f"{x.id}.mpg" for x in p.titles}, "/out")
        self.assertIn(f'<button name="go">{texts[0]}</button>', xml)

    def test_key_frames_where_buttons_change(self):
        p = project(data())
        t = p.title("t2")
        args = encode._video_args(t, p.disc_for(t), 5_000_000, "ntsc-dvd", "progressive")
        keys = [float(k) for k in args[args.index("-force_key_frames") + 1].split(",")]
        fps = title_fps(t, p.disc)
        for time in (2.0, 6.0, 8.0):                     # the buttons, and chapter 2
            self.assertTrue(any(abs(k - time) < fps[1] / fps[0] for k in keys), (time, keys))

    def test_stretches_and_navigation(self):
        p = project(data(GO, BACK, dict(GO, id="side", x=400, y=100)))
        t = p.title("t2")
        fps = title_fps(t, p.disc)
        tbs = titlebuttons.vts_buttons(t, fps, [bytes(8)] * 3)
        self.assertEqual(len(tbs), 1)
        tb = tbs[0]
        self.assertAlmostEqual(tb.start, 2.0, delta=0.02)
        # go (1) above back (2), side (3) right of go
        go, back, side = tb.buttons
        self.assertEqual((go.down, go.right, back.up, side.left), (2, 3, 1, 1))
        self.assertEqual(go.rect, (100, 100, 300, 160))
        self.assertEqual((tb.highlight[0], tb.select[0]), (0, 1))


class TestSimulatorAndFlowchart(unittest.TestCase):
    def setUp(self):
        self.p = project(data())
        self.sim = Simulator(self.p)
        self.s = self.sim.start()
        self.sim.press(self.s, "select:" + self.p.menus[0].buttons[-1].id)
        self.sim.press(self.s, "enter")                  # title t2
        self.assertEqual(self.s["title"], "t2")

    def test_buttons_only_while_shown(self):
        sim, s = self.sim, self.s
        sim.press(s, "down")                              # 0 s: no buttons, nothing happens
        sim.press(s, "enter")
        self.assertEqual((s["title"], s["chapter"]), ("t2", 1))
        sim.press(s, "seek:3")
        self.assertEqual(s["button"], 1)
        sim.press(s, "down")
        self.assertEqual(s["button"], 2)                  # back
        sim.press(s, "enter")
        self.assertEqual((s["domain"], s["menu"]), ("menu", "main"))
        self.assertEqual(s["resume"]["title"], "t2")      # a call, as the Menu key's

    def test_link_and_seek_past(self):
        sim, s = self.sim, self.s
        sim.press(s, "seek:7")
        sim.press(s, "enter")                             # gone at 6 s
        self.assertEqual(s["title"], "t2")
        sim.press(s, "seek:2")
        sim.press(s, "1")                                 # number key: go, at once
        self.assertEqual((s["title"], s["chapter"]), ("t1", 1))

    def test_flowchart(self):
        g = graph.build(self.p)
        edges = [(e["from"], e["to"], e["label"]) for e in g["edges"] if e["kind"] == "button"]
        self.assertIn((graph.node_id("title", "t2"), graph.node_id("title", "t1"), "go"), edges)
        self.assertIn((graph.node_id("title", "t2"), graph.node_id("menu", "main"), "back"), edges)


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), ffprobe and an ISO tool")
class TestOnDisc(unittest.TestCase):
    """Title B (8 s) with two buttons from 2 s to 6 s: "go" plays title A,
    "back" calls the main menu. libdvdnav offers them in those seconds alone,
    the first selected, and they run their links."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-tbtn-")
        rc, _, err = run_cli("init", "b", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "b")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=s=640x360:r=30000/1001:d=8", "-f", "lavfi", "-i", "sine=f=440:d=8",
                        "-c:v", "mpeg4", "-q:v", "3", "-c:a", "aac", "-shortest",
                        os.path.join(proj, "media", "b.mp4")], check=True)
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            d = json.load(f)
        d["titles"][1].update({"source": "media/b.mp4", "chapters": [0], "buttons": [GO, BACK]})
        with open(cls.path, "w") as f:
            json.dump(d, f)
        cls.iso = os.path.join(cls.tmp, "b.iso")
        cls.rc, cls.out, cls.err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast",
                                           cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_built(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        self.assertEqual([e["message"] for e in json_lines(self.out) if e.get("level") == "warn"], [])

    def to_title_b(self, d):
        d.wait_menu()
        d.activate(d.button_count())                     # SAMPLE TITLE B
        self.assertEqual(d.wait_title(), (2, 1))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_buttons_while_shown(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        seen = []                                        # (seconds into the title, buttons)
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.to_title_b(d)                           # (at the title's first navigation pack)

            def at():
                # the VOBU's start from the PCI libdvdnav has now, which its
                # buttons come from (pci_t: VOBU_S_PTM at 12, host order)
                pci = ctypes.string_at(LIBDVDNAV.dvdnav_get_current_nav_pci(d.h), 16)
                return int.from_bytes(pci[12:16], sys.byteorder)
            first = at()
            seen.append((0.0, d.button_count()))
            for _ in range(400_000):
                e = d.step()
                if e == dvdnav_sim.EV_NAV_PACKET and d.domain() == "title" and d.title_part()[0] == 2:
                    seen.append(((at() - first) / 90000, d.button_count()))
                elif d.stopped or d.domain() != "title" or d.title_part()[0] != 2:
                    break
        during = [n for t, n in seen if 2.0 <= t < 5.9]
        outside = [n for t, n in seen if t < 1.9 or t >= 6.0]
        self.assertTrue(during and outside, seen)
        self.assertEqual(set(during), {2}, seen)
        self.assertEqual(set(outside), {0}, seen)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_links(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.to_title_b(d)
            d.run_until(lambda e: e == dvdnav_sim.EV_NAV_PACKET and d.button_count() > 0)
            self.assertEqual(d.highlight(), 1)           # the title's pre: button 1
            self.assertEqual(d.move("down"), 2)
            d.activate()                                 # back: the main menu
            d.wait_menu()
            self.assertEqual(d.domain(), "vtsm")
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.to_title_b(d)
            d.run_until(lambda e: e == dvdnav_sim.EV_NAV_PACKET and d.button_count() > 0)
            d.activate(1)                                # go: title A
            self.assertEqual(d.wait_title(), (1, 1))


if __name__ == "__main__":
    unittest.main()
