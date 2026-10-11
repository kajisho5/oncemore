"""The web version of a disc (build --format web).

The pieces (WebVTT, the frame, what the player is told about the disc), and
a sample disc built for the web: its files, and its player opened from the
folder in a browser, pressed key by key next to the disc simulator (the
same rules as the built DVD) and checked to end up in the same places.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from oncemore import tools, web
from oncemore.project import build_project
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator
from oncemore.subtitles import Cue

from .helpers import have, run_cli

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


def x264():
    try:
        return "libx264" in subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                                           capture_output=True, text=True).stdout
    except Exception:
        return False


BUILD_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext() and x264()


class TestPieces(unittest.TestCase):
    def test_vtt(self):
        cues = [Cue(1.0, 2.5, ["Hello", "there -->"]), Cue(3, 4, ["Up"], position="top"),
                Cue(5, 6, [], image="/x/a.png")]
        self.assertEqual(web.to_vtt(cues),
                         "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHello\nthere ->\n\n"
                         "00:00:03.000 --> 00:00:04.000 line:0\nUp\n\n")
        p = build_project(sample_project(), "/virtual/project.oncemore.json", check_files=False)
        t = p.titles[0]
        t.chapter_names = ["Opening", None, None]
        self.assertEqual(web.chapters_vtt(t, 24.0).split("\n\n")[1:3],
                         ["00:00:00.000 --> 00:00:08.000\nOpening",
                          "00:00:08.000 --> 00:00:16.000\nChapter 2"])

    def test_frame(self):
        p = build_project(sample_project(aspect="4:3"), "/virtual/p.json", check_files=False)
        f = web.frame_for(p.disc)
        self.assertEqual((f.width, f.height, round(f.dar, 3)), (960, 720, 1.333))
        self.assertEqual(web.frame_for(p.disc, "16:9").width, 1280)

    def test_disc_data(self):
        d = sample_project()
        d["playlists"] = [{"id": "pl", "items": ["t2", "t1:2-3"],
                           "end_action": "menu:main"}]
        p = build_project(d, "/virtual/p.json", check_files=False)
        data = web.disc_data(p, {t.id: {"src": f"titles/{t.id}.mp4"} for t in p.titles},
                             {m.id: {"buttons": []} for m in p.menus},
                             {t.id: t.chapters for t in p.titles})
        self.assertEqual((data["first_play"], data["root"], data["title_key"]),
                         ("menu:main", "main", "menu:main"))
        self.assertEqual(data["order"], ["t1", "t2"])
        self.assertEqual(data["titles"]["t1"]["chapters"], [0.0, 8.0, 16.0])
        self.assertEqual(data["titles"]["t1"]["menu_key"], "main")
        self.assertEqual(data["playlists"]["pl"]["items"][1], {"title": "t1", "first": 2, "last": None})  # (to the end)


def probe_streams(path):
    out = subprocess.run([tools.find("ffprobe"), "-v", "error", "-show_entries",
                          "stream=codec_name,height", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return [(s["codec_name"], s.get("height")) for s in json.loads(out)["streams"]]


@unittest.skipUnless(BUILD_OK, "needs ffmpeg with drawtext and libx264")
class TestBuilt(unittest.TestCase):
    """The sample disc with a playlist (its third button plays it), subtitles
    on the first title, built for the web."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-web-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        cls.dir = os.path.join(cls.tmp, "s")
        path = os.path.join(cls.dir, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        with open(os.path.join(cls.dir, "media", "en.srt"), "w") as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nHello\n")
        data["titles"][0]["subtitles"] = [{"file": "media/en.srt", "lang": "en", "default": True}]
        data["playlists"] = [{"id": "pl", "items": ["t2", "t1:2-3"],
                              "end_action": "menu:main:ch"}]
        data["menus"][0]["buttons"][2]["action"] = "playlist:pl"
        # (a link transition before the playlist, and the main menu with sound:
        # a video)
        data["menus"][0]["buttons"][2]["transition"] = "media/sample_b.mp4"
        subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "sine=d=3:r=48000", os.path.join(cls.dir, "media", "tone.wav")],
                       check=True)
        data["menus"][0]["audio"] = "media/tone.wav"
        with open(path, "w") as f:
            json.dump(data, f)
        cls.data = data
        cls.out = os.path.join(cls.tmp, "web")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", cls.dir, "-o", cls.out, "--format",
                                                 "web", "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_files(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        for name in ("index.html", "player.js", "player.css", "disc.js", "menus/main.png",
                     "menus/main-highlight.png", "menus/chapters.png", "titles/t1.chapters.vtt",
                     "titles/t1.sub1.vtt"):
            self.assertTrue(os.path.isfile(os.path.join(self.out, name)), name)
        self.assertFalse(os.path.exists(os.path.join(self.out, ".work")))
        self.assertEqual(probe_streams(os.path.join(self.out, "transitions", "1.mp4")),
                         [("h264", 720), ("aac", None)])
        self.assertEqual(probe_streams(os.path.join(self.out, "menus", "main.mp4")),
                         [("h264", 480), ("aac", None)])
        # MP4: H.264 at 720 lines, AAC
        self.assertEqual(probe_streams(os.path.join(self.out, "titles", "t1.mp4")),
                         [("h264", 720), ("aac", None)])
        with open(os.path.join(self.out, "titles", "t1.sub1.vtt")) as f:
            self.assertIn("00:00:01.000 --> 00:00:03.000\nHello", f.read())

    @unittest.skipUnless(PLAYWRIGHT, "needs playwright")
    def test_player_follows_the_disc(self):
        """Key by key, the player in a browser and the simulator agree on
        the menu, the button, the title and the chapter."""
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        with open(os.path.join(self.out, "disc.js")) as f:
            disc = json.loads(f.read().split("=", 1)[1].rstrip().rstrip(";"))
        project = build_project(self.data, os.path.join(self.dir, "project.oncemore.json"))
        layouts = {mid: [{"id": b["id"], "rect": b["rect"], "nav": b["nav"], "auto": b["auto"],
                          "action": b["action"]} for b in m["buttons"]]
                   for mid, m in disc["menus"].items()}
        sim = Simulator(project, layouts)
        s = sim.start()
        keys = ["down", "enter",              # CHAPTERS
                "right", "enter",             # chapter 2 of t1
                "next", "prev", "menu",       # the Menu key: the main menu
                "down", "down", "enter",      # the playlist: t2, then t1 from chapter 2
                "end", "end",                 # ... its end action: main, CHAPTERS lit
                "enter", "left", "enter",     # chapter 1 of t1
                "end",                        # t1's end action: the main menu
                "title"]

        def view_sim():
            return (s["domain"], s["menu"], s["button"] - 1 if s["domain"] == "menu" else None,
                    s["title"], s["chapter"] if s["domain"] == "title" else None)

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                from .test_gui import _chromium
                if not _chromium():
                    self.skipTest("no Chromium for Playwright")
                browser = p.chromium.launch(executable_path=_chromium())
            page = browser.new_page(viewport={"width": 1000, "height": 700})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("file://" + os.path.join(self.out, "index.html"))
            page.wait_for_function("window.oncemorePlayer && window.oncemorePlayer.state.domain === 'menu'")

            def view_web():
                st = page.evaluate("window.oncemorePlayer.state")
                return (st["domain"], st["menu"], st["button"] if st["domain"] == "menu" else None,
                        st["title"], st["chapter"] if st["domain"] == "title" else None)

            self.assertEqual(view_web(), view_sim())
            # the highlight sits on the first button
            clip = page.evaluate("document.getElementById('menu-highlight').style.clipPath")
            x0, y0, x1, y1 = disc["menus"]["main"]["buttons"][0]["rect"]
            w, h = disc["menus"]["main"]["size"]
            got = [float(v) for v in re.findall(r"[\d.]+", clip)]
            want = [y0 / h * 100, (1 - x1 / w) * 100, (1 - y1 / h) * 100, x0 / w * 100]
            self.assertTrue(all(abs(a - b) < 0.01 for a, b in zip(got, want)), (clip, want))
            for key in keys:
                sim.press(s, key)
                if key == "end":
                    page.evaluate("document.getElementById('title').dispatchEvent(new Event('ended'))")
                else:
                    page.evaluate(f"window.oncemorePlayer.press({json.dumps(key)})")
                if not page.evaluate("document.getElementById('transition').hidden"):
                    # a link transition plays first; the link follows when it ends
                    self.assertEqual(page.evaluate(
                        "document.getElementById('transition').getAttribute('src')"),
                        "transitions/1.mp4")
                    page.evaluate("document.getElementById('transition').dispatchEvent(new Event('ended'))")
                self.assertEqual(view_web(), view_sim(), f"after {key}")
            # the title plays its file, with its subtitles
            page.evaluate("window.oncemorePlayer.press('enter')")     # (the main menu: PLAY ALL)
            self.assertEqual(page.evaluate("document.getElementById('title').getAttribute('src')"),
                             "titles/t1.mp4")
            self.assertEqual(page.evaluate("document.querySelectorAll('#title track').length"), 1)
            # the main menu with sound plays as a video, under the buttons
            page.evaluate("window.oncemorePlayer.press('menu')")
            self.assertEqual(page.evaluate("document.getElementById('menu-video').getAttribute('src')"),
                             "menus/main.mp4")
            # the keyboard: arrows, and number keys (two together are one number)
            page.locator("#screen").focus()
            page.keyboard.press("ArrowDown")
            self.assertEqual(page.evaluate("window.oncemorePlayer.state.button"), 1)
            page.keyboard.press("2")
            page.wait_for_function("window.oncemorePlayer.state.menu === 'chapters'")
            page.keyboard.press("m")
            # a click on a button runs it
            page.click("#hotspots button[data-id='ch']")
            self.assertEqual(page.evaluate("window.oncemorePlayer.state.menu"), "chapters")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
