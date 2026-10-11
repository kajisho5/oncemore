"""Button numbers: the remote's number keys select a menu's buttons by their
place, plus the menu's offset (Properties > Number, button_offset).

The project field, the simulator, the DVD (the button offset number in the
menu's navigation packs, read back by libdvdnav) and the Blu-ray (the
buttons' numeric select values, pressed through libbluray).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import tools, uops
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator

from .helpers import have, json_lines, run_cli

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

TOOLS_OK = (have("ffmpeg", "ffprobe") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)


def project(data):
    return build_project(data, "/virtual/project.oncemore.json", check_files=False)


class TestProjectAndSimulator(unittest.TestCase):
    def test_offset(self):
        d = sample_project()
        d["menus"][0]["button_offset"] = 10
        self.assertEqual(project(d).menus[0].button_offset, 10)
        self.assertEqual(project(sample_project()).menus[0].button_offset, 0)
        d["menus"][0]["button_offset"] = 97              # three buttons: 98, 99, 100
        with self.assertRaises(ProjectError) as cm:
            project(d)
        self.assertIn("button_offset", str(cm.exception.issues))

    def test_number_keys(self):
        d = sample_project()
        d["menus"][0]["button_offset"] = 10
        sim = Simulator(project(d))
        s = sim.start()
        self.assertEqual((s["domain"], s["menu"]), ("menu", "main"))
        sim.press(s, "2")                                   # 2 - 10: no such button
        self.assertEqual((s["domain"], s["log"]), ("menu", ["no button 2 here"]))
        sim.press(s, "number:12")                           # the second button: CHAPTERS
        self.assertEqual((s["domain"], s["menu"]), ("menu", "chapters"))
        s = sim.start()
        sim.press(s, "number:11")                           # the first: PLAY ALL
        self.assertEqual((s["domain"], s["title"]), ("title", "t1"))


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext) and an ISO tool")
class TestDvd(unittest.TestCase):
    """A sample disc whose main menu numbers its buttons from 11."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-bnum-")
        rc, _, err = run_cli("init", "n", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "n", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["menus"][0]["button_offset"] = 10
        with open(path, "w") as f:
            json.dump(data, f)
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("--json", "build", path, "-o", cls.out,
                                                 "--fast", cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def packs(self):
        """(button offset, buttons) of every navigation pack with buttons in
        the menu VOB."""
        out = []
        with open(os.path.join(self.out, "VIDEO_TS", "VTS_01_0.VOB"), "rb") as f:
            data = f.read()
        for at in range(0, len(data), 2048):
            p = data[at:at + 2048]
            if p[:4] == b"\0\0\1\xba" and p[38:42] == b"\0\0\1\xbf" and p[44] == 0 and p[0x9E]:
                out.append((p[0x9D], p[0x9E]))
        return out

    def test_offset_in_the_main_menu_only(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        packs = self.packs()
        # the main menu (three buttons) is numbered from 11; the chapter
        # menu (its own buttons) is not
        self.assertIn((10, 3), packs)
        self.assertTrue(all(off == 10 for off, n in packs if n == 3), packs)
        self.assertTrue(any(off == 0 and n != 3 for off, n in packs), packs)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_read_back_by_libdvdnav(self):
        with dvdnav_sim.DvdSim(os.path.join(self.out, "VIDEO_TS"), LIBDVDNAV) as d:
            d.wait_menu()
            self.assertEqual(d.button_numbers(), (10, 3))


def ffmpeg_has_x264():
    try:
        out = subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                             capture_output=True, text=True).stdout
    except Exception:
        return False
    return "libx264" in out


@unittest.skipUnless(ffmpeg_has_x264() and LIBBLURAY and tools.has_drawtext(),
                     "needs ffmpeg with libx264 and drawtext, and libbluray")
class TestBluray(unittest.TestCase):
    """Three buttons numbered from 4: the number key 5 selects the second."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-bdnum-")
        for name in ("a.mp4", "b.mp4", "c.mp4"):
            subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=size=640x360:rate=30000/1001:duration=1", "-c:v", "libx264",
                            "-preset", "ultrafast", os.path.join(d, name)], check=True)
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1,
                       "disc": {"label": "BD_NUM", "standard": "NTSC", "aspect": "16:9",
                                "first_play": "menu:main"},
                       "titles": [{"id": k, "source": f"{k}.mp4"} for k in "abc"],
                       "menus": [{"id": "main", "button_offset": 3, "buttons": [
                           {"id": k, "label": k.upper(), "x": 100, "y": 100 + 70 * n,
                            "action": f"title:{k}"} for n, k in enumerate("abc")]}]}, f)
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--format", "bluray",
                                                 "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def plays(self, *keys):
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            disc.info()
            events = disc.play(keys=keys)
        after = events[max(i for i, e in enumerate(events) if e[0] == "key") + 1:]
        return next((e[1] for e in after if e[0] == "playlist" and e[1] != 0xFFFF), None)

    def test_number_keys(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        self.assertEqual(self.plays("enter"), 1)            # the first button: title a
        self.assertEqual(self.plays("5", "enter"), 2)       # 5 - 3: the second, title b
        self.assertEqual(self.plays("6", "enter"), 3)


if __name__ == "__main__":
    unittest.main()
