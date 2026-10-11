"""Playlists played in random order or shuffled (Blu-ray and the web
version; a DVD plays them as listed).

The project field, the movie object that picks the items (each item its own
playlist file), the web version's data, and discs played by libbluray from
first play: shuffle plays every item once, random as many items as there
are, each one of them.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import bluray, tools, web
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import run_cli

try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None


def project(order):
    d = sample_project()
    d["playlists"] = [{"id": "pl", "items": ["t2", "t1:1", "t1:3"], "order": order}]
    return build_project(d, "/virtual/project.oncemore.json", check_files=False)


class TestProject(unittest.TestCase):
    def test_field(self):
        self.assertEqual(project("shuffle").playlists[0].order, "shuffle")
        d = sample_project()
        d["playlists"] = [{"id": "pl", "items": ["t2"]}]
        self.assertEqual(build_project(d, "/virtual/p.json", check_files=False)
                         .playlists[0].order, "sequential")
        with self.assertRaises(ProjectError):
            project("backwards")

    def test_item_playlists(self):
        nav = bluray.Nav(project("shuffle"))
        # the titles' own playlists first, then one per item
        n = len(nav.titles)
        self.assertEqual(nav.item_playlists, {"pl": [n + 1, n + 2, n + 3]})
        self.assertEqual(bluray.Nav(project("sequential")).item_playlists, {})

    def test_object(self):
        for order, size in (("shuffle", 6), ("random", 3)):
            nav = bluray.Nav(project(order))
            pl = nav.numbers["playlist:pl"]
            cmds = nav.objects()[pl - 1]
            items = nav.item_playlists["pl"]
            # each item played by its own playlist, once in the object
            for k in items:
                self.assertEqual(cmds.count(bluray.play_pl(k)), 1, order)
            self.assertNotIn(bluray.play_pl(pl), cmds)
            self.assertIn(bluray.rnd(bluray.PICK_REG, 3), cmds)
            self.assertIn(bluray.if_at_least(bluray.COUNT_REG, 3), cmds)
            # every goto lands inside the object (or just past the picking)
            for c in cmds:
                if c[:2] == bluray.goto(0)[:2]:
                    self.assertLess(int.from_bytes(c[4:8], "big"), len(cmds) + 1)
            blocks = [c for c in cmds if c == bluray.add(bluray.COUNT_REG, 1)]
            self.assertEqual(len(blocks), 3)
            self.assertGreaterEqual(len(cmds), size * 3)

    def test_web_data(self):
        p = project("random")
        data = web.disc_data(p, {t.id: {"src": f"titles/{t.id}.mp4"} for t in p.titles},
                             {m.id: {"buttons": []} for m in p.menus},
                             {t.id: t.chapters for t in p.titles})
        self.assertEqual(data["playlists"]["pl"]["order"], "random")


def x264():
    try:
        return "libx264" in subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                                           capture_output=True, text=True).stdout
    except Exception:
        return False


@unittest.skipUnless(x264() and LIBBLURAY and tools.has_drawtext(),
                     "needs ffmpeg with libx264 and drawtext, and libbluray")
class TestBluray(unittest.TestCase):
    """Three one-second titles in a playlist that first play starts."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-shuffle-")
        for name in ("a.mp4", "b.mp4", "c.mp4"):
            subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=size=640x360:rate=30000/1001:duration=1", "-c:v",
                            "libx264", "-preset", "ultrafast", os.path.join(d, name)],
                           check=True)
        cls.out = {}
        for order in ("shuffle", "random"):
            folder = os.path.join(d, order)
            os.makedirs(folder)
            for name in ("a.mp4", "b.mp4", "c.mp4"):
                shutil.copy(os.path.join(d, name), folder)
            with open(os.path.join(folder, "project.oncemore.json"), "w") as f:
                json.dump({"version": 1,
                           "disc": {"label": "SHUFFLE", "standard": "NTSC", "aspect": "16:9",
                                    "first_play": "playlist:pl"},
                           "titles": [{"id": k, "source": f"{k}.mp4"} for k in "abc"],
                           "playlists": [{"id": "pl", "items": ["a", "b", "c"],
                                          "order": order}]}, f)
            out = os.path.join(folder, "out")
            rc, stdout, stderr = run_cli("build", folder, "-o", out, "--format", "bluray",
                                         "--fast")
            assert rc == 0, stderr + stdout
            cls.out[order] = out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def played(self, order):
        """The playlist files played from first play on."""
        with bluray_sim.Disc(LIBBLURAY, self.out[order]) as disc:
            disc.info()
            events = disc.play()
        return [e[1] for e in events if e[0] == "playlist"]

    def test_shuffle(self):
        # titles a, b, c and the playlist's own title: the items are 5, 6, 7
        for _ in range(3):
            played = self.played("shuffle")
            self.assertEqual(sorted(played), [5, 6, 7], played)

    def test_random(self):
        for _ in range(3):
            played = self.played("random")
            self.assertEqual(len(played), 3, played)
            self.assertTrue(set(played) <= {5, 6, 7}, played)


if __name__ == "__main__":
    unittest.main()
