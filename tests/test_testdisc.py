"""`oncemore testdisc`: the player test disc (DECISIONS §134).

The project it makes is valid as a DVD and as a Blu-ray, its checklist says
the same in English and Japanese, the command, the app and the MCP server
make it, and the DVD built from it plays as the checklist says through
libdvdnav. Also the titleset of a title with buttons (§135).
"""

import json
import os
import shutil
import tempfile
import unittest

from oncemore import mcp, testdisc, tools
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have, json_lines, run_cli
from .test_gui import GuiServer

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


def built(data):
    return build_project(data, "/virtual/project.oncemore.json", check_files=False)


class TestProject(unittest.TestCase):
    def test_valid_as_dvd_and_bluray(self):
        for fmt in ("dvd", "bluray"):
            for standard in ("NTSC", "PAL"):
                for aspect in ("16:9", "4:3"):
                    p = built(testdisc.test_project(fmt, standard, aspect))
                    self.assertEqual(p.disc.format, fmt)
                    ids = [t.id for t in p.titles]
                    # buttons over a title are DVD only (a Blu-ray has the pop-up)
                    self.assertEqual("buttons" in ids, fmt == "dvd", ids)
                    main = p.menu("main")
                    self.assertEqual(len(main.buttons), 8 if fmt == "dvd" else 7)
                    movie = p.title("movie")
                    self.assertEqual(len(movie.audio_tracks), 2)
                    self.assertEqual(len(movie.subtitles), 2)
                    self.assertEqual(movie.chapters, testdisc.MOVIE_CHAPTERS)

    def test_checklist(self):
        for fmt, rows in (("dvd", 13), ("bluray", 12)):
            text = testdisc.checklist(fmt)
            en, ja = text.split("# oncemore 実機テスト")
            self.assertIn(testdisc.REPORT_URL, en)
            self.assertIn(testdisc.REPORT_URL, ja)
            for half in (en, ja):
                numbered = [ln for ln in half.splitlines() if ln[:2] == "| " and ln[2].isdigit()]
                self.assertEqual(len(numbered), rows, (fmt, half))
            self.assertEqual("pop-up" in en, fmt == "bluray")
            self.assertEqual("BUTTONS ON VIDEO" in text, fmt == "dvd")

    def test_report_template(self):
        """The checklist's link opens the repository's issue template."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, ".github", "ISSUE_TEMPLATE", "player-test.md")
        self.assertTrue(testdisc.REPORT_URL.endswith("template=player-test.md"))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("---\nname:"), text[:40])
        self.assertIn("make and model", text)


class TestTitleButtonsTitleset(unittest.TestCase):
    """A title with buttons over it and a subtitled title of the same
    format: their first subpicture streams are a button highlight and a
    subtitle, which one titleset cannot describe both ways (§135)."""

    def test_own_titleset(self):
        d = sample_project()
        d["titles"][1]["aspect"] = None
        d["titles"][1].pop("aspect")
        d["titles"][0]["subtitles"] = [{"file": "media/a.srt", "lang": "en"}]
        d["titles"][1]["buttons"] = [{"id": "go", "start": 1, "end": 3, "x": 100, "y": 100,
                                      "width": 200, "height": 60, "action": "title:t1"}]
        p = built(d)
        a, b = p.titles[0], p.titles[1]
        self.assertEqual((a.aspect, a.audio_codec), (b.aspect, b.audio_codec))
        self.assertNotEqual(a.titleset, b.titleset)

    def test_test_disc(self):
        p = built(testdisc.test_project("dvd"))
        self.assertNotEqual(p.title("movie").titleset, p.title("buttons").titleset)


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), ffprobe and an ISO tool")
class TestMade(unittest.TestCase):
    """Made by the command, the app and the MCP server."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="oncemore-testdisc-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_command(self):
        rc, out, err = run_cli("--json", "testdisc", "t", "--format", "bluray", cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        result = [e for e in json_lines(out) if e.get("event") == "result"][0]
        self.assertTrue(os.path.isfile(result["checklist"]))
        names = sorted(os.path.basename(m) for m in result["media"])
        self.assertIn("surround.mkv", names)
        self.assertNotIn("buttons.mkv", names)                 # (DVD only)
        rc, out, err = run_cli("validate", "t", cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        # a second time: refused unless --force
        rc, _, err = run_cli("testdisc", "t", cwd=self.tmp)
        self.assertNotEqual(rc, 0)
        self.assertIn("--force", err)

    def test_app(self):
        s = GuiServer(self.tmp)
        self.addCleanup(s.close)
        status, r = s.call("/api/new", "POST", {"sample": "testdisc", "format": "dvd",
                                                "standard": "PAL"})
        self.assertEqual(status, 200, r)
        self.assertEqual(r["project"]["disc"]["label"], "PLAYER_TEST")
        self.assertEqual(r["project"]["disc"]["standard"], "PAL")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "TEST-CHECKLIST.md")))

    def test_mcp(self):
        server = mcp.Server([self.tmp])
        r = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "create_project",
            "arguments": {"folder": os.path.join(self.tmp, "d"), "test_disc": "dvd"},
            "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                      "io.modelcontextprotocol/clientCapabilities": {}}}})
        r = r["result"]
        self.assertFalse(r["isError"], r)
        self.assertTrue(r["structuredContent"]["check"]["valid"], r)
        self.assertTrue(r["structuredContent"]["checklist"].endswith("TEST-CHECKLIST.md"))


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), ffprobe and an ISO tool")
class TestDvd(unittest.TestCase):
    """The DVD built from it, played through libdvdnav as the checklist
    says it plays."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-testdisc-dvd-")
        rc, out, err = run_cli("testdisc", "t", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.iso = os.path.join(cls.tmp, "t.iso")
        cls.rc, cls.out, cls.err = run_cli("--json", "iso", "t", "-o", cls.iso, "--fast",
                                           cwd=cls.tmp)
        with open(os.path.join(cls.tmp, "t", "project.oncemore.json"), encoding="utf-8") as f:
            cls.data = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_built(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        self.assertEqual([e["message"] for e in json_lines(self.out) if e.get("level") == "warn"],
                         [])

    def sim(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        return dvdnav_sim.DvdSim(self.iso, LIBDVDNAV)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_menu_movie_streams_and_chapters(self):
        second = self.data["titles"][0]["audio_tracks"][1]["lang"]
        with self.sim() as d:
            d.wait_menu()
            self.assertEqual(d.button_count(), 8)            # "eight buttons"
            d.activate(1)                                    # PLAY MOVIE
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual([d.audio_lang(0), d.audio_lang(1)], ["en", second])
            self.assertEqual([d.subtitle_lang(0), d.subtitle_lang(1)], ["en", second])
            self.assertEqual(d.num_parts(1), 4)
            d.next_chapter()
            d.run_until(lambda e: e == dvdnav_sim.EV_NAV_PACKET and d.title_part() == (1, 2))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_chapter_menu(self):
        with self.sim() as d:
            d.wait_menu()
            d.activate(2)                                    # CHAPTERS
            d.run_until(lambda e: e == dvdnav_sim.EV_NAV_PACKET and d.button_count() == 5)
            d.activate(4)                                    # chapter 4
            self.assertEqual(d.wait_title(), (1, 4))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_surround_and_buttons_over_a_title(self):
        with self.sim() as d:
            d.wait_menu()
            d.activate(6)                                    # 5.1 SOUND
            self.assertEqual(d.wait_title()[0], 3)
            self.assertEqual(d.audio_channels(0), 6)
        with self.sim() as d:
            d.wait_menu()
            d.activate(8)                                    # BUTTONS ON VIDEO
            self.assertEqual(d.wait_title()[0], 4)
            d.run_until(lambda e: e == dvdnav_sim.EV_NAV_PACKET and d.button_count() > 0)
            self.assertEqual(d.button_count(), 2)
            d.activate(1)                                    # chapter 3 of the movie
            self.assertEqual(d.wait_title(), (1, 3))


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), ffprobe and an ISO tool")
@unittest.skipUnless(LIBBLURAY, "libbluray not installed")
class TestBluray(unittest.TestCase):
    """The Blu-ray built from it, played through libbluray: the movie's
    chapters and streams, and its pop-up menu over the playing movie."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-testdisc-bd-")
        rc, out, err = run_cli("testdisc", "t", "--format", "bluray", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.iso = os.path.join(cls.tmp, "t.iso")
        cls.rc, cls.out, cls.err = run_cli("--json", "iso", "t", "-o", cls.iso, "--fast",
                                           cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.rc, 0, self.err + self.out)

    def test_movie(self):
        with bluray_sim.Disc(LIBBLURAY, self.iso) as d:
            self.assertTrue(d.info()["first_play"])
            movie = d.playlist(1)
        self.assertEqual(len(movie["chapters"]), 4)
        self.assertEqual(len(movie["audio"]), 2)
        self.assertEqual(movie["audio"][0][2], "eng")
        self.assertEqual([lang for _, lang in movie["pg"]][:1], ["eng"])
        self.assertEqual(len(movie["pg"]), 2)

    def test_popup_switches_the_sound(self):
        with bluray_sim.Disc(LIBBLURAY, self.iso) as d:
            d.info()
            events = d.play(keys=("enter", "live:popup", "live:down", "live:enter"), audio=True)
        keys = [i for i, e in enumerate(events) if e[0] == "key"]
        # PLAY MOVIE, then the pop-up's seven buttons over it; AUDIO 2 chosen
        self.assertIn(("title", 1), events[keys[0]:keys[1]])
        self.assertEqual(len(events[keys[1] + 1][1]), 7, events)
        self.assertIn(("audio_stream", 2), events[keys[3]:])


if __name__ == "__main__":
    unittest.main()
