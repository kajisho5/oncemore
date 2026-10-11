"""Menus with pages: one menu whose objects are each on one page or on every
page, with buttons that go to the next, previous or a given page.

The project (each page a menu of its own, page links, the page of a button a
link highlights, what is refused), the disc simulator, and the sample disc
with a two-page main menu built as a DVD (libdvdnav) and as a Blu-ray
(libbluray), its pages turned with the remote.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import tools
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator

from .helpers import have, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None
try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None

DVD_OK = have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()


def paged(menu):
    """The sample's main menu in three pages: PLAY ALL and a jump to page 3
    on page 1, title B on page 2, the chapter menu on page 3, NEXT and PREV
    on every page; a heading on page 2."""
    menu["pages"] = 3
    menu["buttons"] = [
        {"id": "play", "label": "PLAY ALL", "x": 120, "y": 220, "action": "playall", "page": 1},
        {"id": "go3", "label": "TO 3", "x": 120, "y": 280, "action": "page:3", "page": 1},
        {"id": "b", "label": "TITLE B", "x": 120, "y": 220, "action": "title:t2", "page": 2},
        {"id": "ch", "label": "CHAPTERS", "x": 120, "y": 220, "action": "menu:chapters",
         "page": 3},
        {"id": "next", "label": "NEXT", "x": 480, "y": 400, "action": "page:next"},
        {"id": "prev", "label": "PREV", "x": 240, "y": 400, "action": "page:prev"},
    ]
    menu["texts"].append({"text": "MORE", "x": 120, "y": 150, "page": 2})
    return menu


def project(data):
    return build_project(data, "/virtual/project.oncemore.json", check_files=False)


class TestProject(unittest.TestCase):
    def setUp(self):
        self.d = sample_project()
        paged(self.d["menus"][0])

    def test_pages(self):
        p = project(self.d)
        pages = p.menus[:3]
        self.assertEqual([m.id for m in p.menus], ["main", "main~2", "main~3", "chapters"])
        self.assertEqual([(m.page_of, m.page) for m in pages], [("main", n) for n in (1, 2, 3)])
        # each page a menu of its own on the disc
        self.assertEqual([m.number for m in p.menus], [1, 2, 3, 4])
        self.assertEqual([[b.id for b in m.buttons] for m in pages],
                         [["play", "go3", "next", "prev"], ["b", "next", "prev"],
                          ["ch", "next", "prev"]])
        self.assertEqual([[t.text for t in m.texts] for m in pages],
                         [["SAMPLE DISC"], ["SAMPLE DISC", "MORE"], ["SAMPLE DISC"]])
        # page links: next from the last page goes to the first, prev from
        # the first to the last
        links = [{b.id: b.action for b in m.buttons} for m in pages]
        self.assertEqual([(x["next"], x["prev"]) for x in links],
                         [("menu:main~2", "menu:main~3"), ("menu:main~3", "menu:main"),
                          ("menu:main", "menu:main~2")])
        self.assertEqual(links[0]["go3"], "menu:main~3")
        # (the menu itself is the first page: links to it are unchanged)
        self.assertEqual(p.menu("chapters").buttons[-1].action, "menu:main")
        # a link highlighting a button opens the page that holds it
        self.d["titles"][0]["end_action"] = "menu:main:ch"
        self.d["titles"][1]["end_action"] = "menu:main:next"
        p = project(self.d)
        self.assertEqual(p.titles[0].end_action, "menu:main~3:ch")
        self.assertEqual(p.titles[1].end_action, "menu:main:next")

    def test_default_button(self):
        self.d["menus"][0]["default_button"] = "b"
        p = project(self.d)
        self.assertEqual([m.default_button for m in p.menus[:3]], [None, "b", None])
        self.d["menus"][0]["default_button"] = "next"
        p = project(self.d)
        self.assertEqual([m.default_button for m in p.menus[:3]], ["next"] * 3)

    def test_one_page(self):
        p = project(sample_project())
        self.assertEqual((p.menus[0].pages, p.menus[0].page_of), (1, None))

    def test_refused(self):
        def issues(change):
            d = sample_project()
            paged(d["menus"][0])
            change(d["menus"][0])
            with self.assertRaises(ProjectError) as cm:
                project(d)
            return str(cm.exception.issues)

        self.assertIn("has 3 pages", issues(lambda m: m["buttons"][2].update(page=4)))
        self.assertIn("has 3 pages", issues(lambda m: m["texts"][-1].update(page=5)))
        self.assertIn("has 3 pages", issues(lambda m: m["buttons"][1].update(action="page:4")))
        self.assertIn("page 2 has no buttons",
                      issues(lambda m: (m["buttons"].pop(2), m["buttons"].pop(3),
                                        m["buttons"].pop(3))))
        # navigating to a button that is not on the page
        self.assertIn("on page 2 only",
                      issues(lambda m: m["buttons"][0].update(nav={"down": "b"})))
        self.assertIn("on page 1 only",
                      issues(lambda m: m["buttons"][4].update(nav={"up": "play"})))
        # page links on a menu without pages
        d = sample_project()
        d["menus"][0]["buttons"][0]["action"] = "page:next"
        with self.assertRaises(ProjectError) as cm:
            project(d)
        self.assertIn("menu with pages", str(cm.exception.issues))

    def test_button_offset_per_page(self):
        # four buttons on the fullest page: 96 + 4 = 100 is too many, 95 fits
        self.d["menus"][0]["button_offset"] = 95
        self.assertEqual(project(self.d).menus[1].button_offset, 95)
        self.d["menus"][0]["button_offset"] = 96
        with self.assertRaises(ProjectError):
            project(self.d)

    def test_simulator(self):
        sim = Simulator(project(self.d))
        s = sim.start()
        self.assertEqual(s["menu"], "main")
        sim.press(s, "select:next")
        sim.press(s, "enter")
        self.assertEqual(s["menu"], "main~2")
        sim.press(s, "select:b")
        sim.press(s, "enter")
        self.assertEqual((s["domain"], s["title"]), ("title", "t2"))
        s = sim.start()
        sim.press(s, "select:prev")
        sim.press(s, "enter")
        self.assertEqual(s["menu"], "main~3")
        sim.press(s, "select:ch")
        sim.press(s, "enter")
        self.assertEqual(s["menu"], "chapters")


def sample_disc(tmp):
    rc, _, err = run_cli("init", "s", cwd=tmp)
    assert rc == 0, err
    path = os.path.join(tmp, "s", "project.oncemore.json")
    with open(path) as f:
        data = json.load(f)
    paged(data["menus"][0])
    with open(path, "w") as f:
        json.dump(data, f)
    return path


@unittest.skipUnless(DVD_OK and LIBDVDNAV, "needs ffmpeg (drawtext), dvdauthor, spumux "
                                           "and libdvdnav")
class TestDvd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-pages-")
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", sample_disc(cls.tmp), "-o", cls.out,
                                                 "--fast", cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_turn_pages(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        with dvdnav_sim.DvdSim(os.path.join(self.out, "VIDEO_TS"), LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 4)
            d.activate(3)                                    # NEXT
            self.assertEqual(d.wait_menu(), 2)
            self.assertEqual(d.button_count(), 3)
            d.activate(3)                                    # PREV: back to page 1
            self.assertEqual(d.wait_menu(), 1)
            d.activate(2)                                    # TO 3
            self.assertEqual(d.wait_menu(), 3)
            d.activate(2)                                    # NEXT: round to page 1
            self.assertEqual(d.wait_menu(), 1)
            d.activate(4)                                    # PREV: page 3
            self.assertEqual(d.wait_menu(), 3)
            d.activate(3)                                    # PREV: page 2
            self.assertEqual(d.wait_menu(), 2)
            d.activate(1)                                    # TITLE B
            self.assertEqual(d.wait_title(), (2, 1))


def x264():
    try:
        return "libx264" in subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                                           capture_output=True, text=True).stdout
    except Exception:
        return False


@unittest.skipUnless(have("ffmpeg", "ffprobe") and tools.has_drawtext() and x264()
                     and LIBBLURAY, "needs ffmpeg with libx264 and drawtext, and libbluray")
class TestBluray(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-bdpages-")
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", sample_disc(cls.tmp), "-o", cls.out,
                                                 "--format", "bluray", "--fast", cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def titles(self, *keys):
        """The HDMV titles started after each key."""
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            disc.info()
            events = disc.play(keys=keys)
        out, cur = [], None
        for e in events:
            if e[0] == "key":
                cur = []
                out.append(cur)
            elif e[0] == "title" and cur is not None and e[1] != 0xFFFF:
                cur.append(e[1])
        return out

    def test_turn_pages(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        # HDMV titles: the sample's two, play all, then the menus in order:
        # main 4, main~2 5, main~3 6, chapters 7 (number keys select a
        # button, enter runs it)
        got = self.titles("3", "enter", "1", "enter")   # NEXT, then TITLE B on page 2
        self.assertEqual((got[1][:1], got[3][:1]), ([5], [2]))
        got = self.titles("4", "enter", "3", "enter")   # PREV to page 3, PREV to page 2
        self.assertEqual((got[1][:1], got[3][:1]), ([6], [5]))
        got = self.titles("2", "enter", "1", "enter")   # TO 3, then CHAPTERS
        self.assertEqual((got[1][:1], got[3][:1]), ([6], [7]))

if __name__ == "__main__":
    unittest.main()
