"""Menus imported from layered Photoshop files (fictional designs made with
tests/psd_writer.py)."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import psdmenu, tools
from oncemore.scaffold import sample_project

from .helpers import have, json_lines, run_cli
from .psd_writer import Group, Pixel, build_psd, solid

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

FFMPEG = have("ffmpeg", "ffprobe")
TOOLS_OK = (have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)

W, H = 720, 480
NAVY, WHITE, GREY = (10, 20, 60, 255), (240, 240, 240, 255), (128, 128, 128, 255)


def layer(name, box, rgba, **kw):
    l, t, r, b = box
    return Pixel(name, solid(r - l, b - t, rgba), box, **kw)


def frame(name, box, rgba, t=4, **kw):
    """A hollow rectangle (a typical highlight frame)."""
    l, top, r, b = box
    w, h = r - l, b - top
    px = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            if x < t or y < t or x >= w - t or y >= h - t:
                px[(y * w + x) * 4:(y * w + x + 1) * 4] = bytes(rgba)
    return Pixel(name, bytes(px), box, **kw)


def flatten(w, h, layers):
    """The flattened picture of opaque rectangles (bottom first)."""
    out = bytearray(solid(w, h, (0, 0, 0, 255)))
    for (l, t, r, b), rgba in layers:
        for y in range(t, b):
            out[(y * w + l) * 4:(y * w + r) * 4] = bytes(rgba) * (r - l)
    return bytes(out)


PLAY_ART, PLAY_HL = (100, 300, 260, 330), (100, 334, 260, 340)
CH2_THUMB, CH2_ART, CH2_HL = (400, 120, 560, 210), (400, 214, 560, 240), (396, 116, 564, 244)
EXTRA_ART = (100, 380, 220, 410)


def design(highlights_visible=False, composite=True):
    """Background, a hidden decoration, and three buttons: PLAY (underline
    highlight), CHAPTER 2 (thumbnail placeholder + frame highlight) and
    EXTRAS (no highlight layer)."""
    layers = [
        Group("(+) Play", [
            layer("(=1) underline", PLAY_HL, WHITE, visible=highlights_visible),
            layer("PLAY", PLAY_ART, WHITE),
        ]),
        Group("(+) Chapter 2", [
            frame("(=1) frame", CH2_HL, WHITE, visible=highlights_visible),
            layer("(%) thumbnail", CH2_THUMB, GREY, visible=highlights_visible),
            layer("label", CH2_ART, WHITE),
        ], open=False),
        Group("(+) Extras", [layer("EXTRAS", EXTRA_ART, WHITE)]),
        layer("old logo", (600, 20, 700, 60), (255, 0, 0, 255), visible=False),
        layer("Background", (0, 0, W, H), NAVY),
    ]
    flat = flatten(W, H, [((0, 0, W, H), NAVY), (PLAY_ART, WHITE), (CH2_ART, WHITE),
                          (EXTRA_ART, WHITE)]
                   + ([(PLAY_HL, WHITE), (CH2_THUMB, GREY)]
                      if highlights_visible else []))
    return build_psd(W, H, layers, composite=flat if composite else None)


def pixel(png, x, y):
    out = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-i", png, "-vf",
                          f"crop=1:1:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return tuple(out[:3])


def size(png):
    out = subprocess.run([tools.find("ffprobe"), "-v", "error", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", png],
                         capture_output=True, text=True, check=True).stdout
    return tuple(int(v) for v in out.strip().split(","))


class TestGuessAction(unittest.TestCase):
    def test_names(self):
        p = sample_project()
        g = psdmenu.guess_action
        self.assertEqual(g("Play", p)[0], "playall")
        self.assertEqual(g("Play Movie", p)[0], "title:t1")
        self.assertEqual(g("Sample Title B", p)[0], "title:t2")
        self.assertEqual(g("Scene 03", p)[0], "chapter:t1:3")
        self.assertEqual(g("chapters", p)[0], "menu:chapters")      # a generated menu
        self.assertEqual(g("Subtitles off", p)[0], "subtitle:off")
        self.assertEqual(g("Audio 2", p)[0], "audio:2")
        self.assertIsNone(g("Bonus", p)[0])
        used = set()
        self.assertEqual([psdmenu.slug(n, used) for n in ("Play Movie", "play movie", "★")],
                         ["play_movie", "play_movie_2", "button"])


@unittest.skipUnless(FFMPEG, "needs ffmpeg")
class TestImport(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-psd-")
        self.project = sample_project()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_import(self, data, menu_id="art"):
        path = os.path.join(self.dir, "design.psd")
        with open(path, "wb") as f:
            f.write(data)
        return psdmenu.import_psd(path, self.project, menu_id,
                                  os.path.join(self.dir, "media", "psd"), self.dir)

    def test_buttons_and_background(self):
        menu, notes = self.run_import(design())
        self.assertEqual(menu["background"], "media/psd/art-background.png")
        self.assertEqual(menu["psd"], "design.psd")
        b = {x["id"]: x for x in menu["buttons"]}
        self.assertEqual(list(b), ["play", "chapter_2", "extras"])
        self.assertEqual(b["play"]["action"], "playall")
        self.assertEqual((b["play"]["x"], b["play"]["y"], b["play"]["width"]), (100, 334, 160))
        self.assertEqual(b["chapter_2"]["action"], "chapter:t1:2")
        self.assertEqual(b["chapter_2"]["thumbnail"], {"x": 400, "y": 120, "w": 160, "h": 90})
        self.assertEqual((b["chapter_2"]["x"], b["chapter_2"]["y"]), (396, 116))
        self.assertEqual(b["extras"]["action"], "title:t1")      # placeholder
        msgs = " ".join(n["message"] for n in notes)
        self.assertIn("no action could be guessed from the name 'Extras'", msgs)
        self.assertIn("button 'extras' has no (=1) highlight layer", msgs)
        # the background is the file's flattened image, stretched to 854 x 480
        bg = os.path.join(self.dir, menu["background"])
        self.assertEqual(size(bg), (854, 480))
        self.assertEqual(pixel(bg, 50, 50), NAVY[:3])
        self.assertEqual(pixel(bg, round(180 * 854 / 720), 315), WHITE[:3])     # PLAY art
        self.assertEqual(pixel(bg, round(180 * 854 / 720), 337), NAVY[:3])      # hidden hl
        hl = os.path.join(self.dir, b["play"]["highlight_image"])
        self.assertEqual(size(hl), (round(160 * 854 / 720), 6))
        # the project accepts it
        self.project["menus"].append(menu)
        from oncemore.project import build_project
        p = build_project(self.project, os.path.join(self.dir, "project.oncemore.json"),
                          check_files=False)
        self.assertEqual(p.menu("art").buttons[1].thumb.title_id, "t1")

    def test_visible_highlights_rebuild_background(self):
        menu, notes = self.run_import(design(highlights_visible=True))
        self.assertIn("rebuilt from the layers", " ".join(n["message"] for n in notes))
        bg = os.path.join(self.dir, menu["background"])
        self.assertEqual(pixel(bg, round(180 * 854 / 720), 337), NAVY[:3])      # hl left out
        self.assertEqual(pixel(bg, round(180 * 854 / 720), 315), WHITE[:3])
        self.assertEqual(pixel(bg, round(450 * 854 / 720), 150), NAVY[:3])      # thumb box too

    def test_reimport_keeps_actions(self):
        menu, _ = self.run_import(design())
        menu["buttons"][2]["action"] = "menu:chapters"
        menu["loop"] = 2
        self.project["menus"].append(menu)
        again, _ = self.run_import(design())
        self.assertEqual(again["buttons"][2]["action"], "menu:chapters")
        self.assertEqual(again["loop"], 2)

    def test_no_buttons(self):
        data = build_psd(W, H, [layer("Background", (0, 0, W, H), NAVY)],
                         composite=solid(W, H, NAVY))
        menu, notes = self.run_import(data)
        self.assertEqual(menu["buttons"], [])
        self.assertIn("no layer group is named", notes[0]["message"])


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), dvdauthor, spumux and an ISO tool")
class TestImportedMenuOnDisc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-psd-")
        rc, _, err = run_cli("init", "p", cwd=cls.tmp)
        assert rc == 0, err
        cls.proj = os.path.join(cls.tmp, "p")
        with open(os.path.join(cls.proj, "design.psd"), "wb") as f:
            f.write(design())
        rc, out, err = run_cli("--json", "import-psd", cls.proj, "design.psd", "--menu", "art",
                               "--first-play", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]
        cls.iso = os.path.join(cls.tmp, "p.iso")
        rc, out, err = run_cli("--json", "iso", cls.proj, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_project_updated(self):
        with open(os.path.join(self.proj, "project.oncemore.json")) as f:
            data = json.load(f)
        self.assertEqual(data["disc"]["first_play"], "menu:art")
        art = next(m for m in data["menus"] if m["id"] == "art")
        self.assertEqual([b["id"] for b in art["buttons"]], ["play", "chapter_2", "extras"])
        self.assertEqual(self.result["menu"], "art")

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_buttons_work(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            self.assertEqual(d.button_count(), 3)
            self.assertEqual(d.move("right"), 2)          # PLAY -> CHAPTER 2 (to its right)
            d.activate()
            self.assertEqual(d.wait_title(), (1, 2))


if __name__ == "__main__":
    unittest.main()
