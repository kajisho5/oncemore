"""Typesetting menu texts (DECISIONS §103): lines broken to fit a box with
the Japanese line-break rules, vertical text, underline and strikethrough,
drawn on the menu and shown the same way in the editor."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import bdmenu, tools, typeset
from oncemore.project import build_project

from .helpers import have, run_cli


def em(s):
    return 10 * len(s)


class TestWrap(unittest.TestCase):
    def test_words_and_wide_characters(self):
        self.assertEqual(typeset.wrap("The quick brown fox jumps", em, 100),
                         "The quick\nbrown fox\njumps")
        self.assertEqual(typeset.wrap("あいうえおかきくけこ", em, 40), "あいうえ\nおかきく\nけこ")
        # a word wider than the box is cut by character
        self.assertEqual(typeset.wrap("abcdefghij", em, 40), "abcd\nefgh\nij")
        # the text's own newlines stay; no box, nothing changes
        self.assertEqual(typeset.wrap("ab\ncd", em, 100), "ab\ncd")
        self.assertEqual(typeset.wrap("あいうえお", em, None), "あいうえお")

    def test_kinsoku(self):
        # 。 cannot start a line: え goes down with it
        self.assertEqual(typeset.wrap("あいうえ。かき", em, 40), "あいう\nえ。かき")
        # small kana and the long vowel mark neither
        self.assertEqual(typeset.wrap("あいうえっ", em, 40), "あいう\nえっ")
        self.assertEqual(typeset.wrap("あいうえー", em, 40), "あいう\nえー")
        # 「 cannot end a line: it goes down with what follows
        self.assertEqual(typeset.wrap("あいう「えお」", em, 40), "あいう\n「えお」")
        for line in typeset.wrap("これは、テストです。「かぎ括弧」もあります。", em, 50).split("\n"):
            self.assertNotIn(line[0], typeset.NO_START, line)
            self.assertNotIn(line[-1], typeset.NO_END, line)

    def test_vertical_forms(self):
        have_all = lambda c: True
        self.assertEqual(typeset.vertical_char("。", have_all), "︒")
        self.assertEqual(typeset.vertical_char("「", have_all), "﹁")
        self.assertEqual(typeset.vertical_char("あ", have_all), "あ")
        self.assertEqual(typeset.vertical_char("。", lambda c: False), "。")   # (font without it)


class TestBluray(unittest.TestCase):
    def test_box_scaled_to_hd(self):
        p = build_project({"version": 1, "disc": {"label": "T", "standard": "NTSC", "aspect": "16:9"},
                           "menus": [{"id": "m", "texts": [
                               {"text": "あ", "x": 0, "y": 0, "width": 360, "underline": True},
                               {"text": "い", "x": 0, "y": 0, "height": 240, "vertical": True}],
                               "buttons": [{"id": "a", "label": "A", "x": 0, "y": 100, "action": "title:t"}]}],
                           "titles": [{"id": "t", "source": "a.mp4"}]},
                          "/x/project.oncemore.json", check_files=False)
        m = bdmenu.scale_menu(p.menus[0], p.disc, None)
        self.assertEqual((m.texts[0].width, m.texts[1].height), (960, 540))
        self.assertTrue(m.texts[0].underline and m.texts[1].vertical)


def ink(png, W, H):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    return lambda x, y: raw[y * W + x] > 128


def runs(values):
    out = []
    for v in values:
        if out and v == out[-1][1] + 1:
            out[-1][1] = v
        else:
            out.append([v, v])
    return out


@unittest.skipUnless(have("ffmpeg") and tools.has_drawtext(), "needs ffmpeg with drawtext")
class TestDrawn(unittest.TestCase):
    """The menu drawn: 16:9 NTSC, 854 x 480 display pixels."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-type-")
        d = os.path.join(cls.tmp, "p")
        os.makedirs(d)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=640x360:rate=30000/1001:duration=1", "-f", "lavfi", "-i",
                        "sine=d=1", "-c:v", "mpeg4", "-c:a", "aac", "-shortest",
                        os.path.join(d, "a.mp4")], check=True)
        texts = {
            # a box 300 storage pixels (356 display) wide
            "wrapped": {"text": "これは折り返しのテストです。「かぎ括弧」もあります。", "x": 20, "y": 20,
                        "size": 28, "width": 300},
            "under": {"text": "下線つき", "x": 20, "y": 260, "size": 28, "underline": True},
            "struck": {"text": "取り消し", "x": 20, "y": 340, "size": 28, "strikethrough": True},
            # two columns, the first 6 characters of 30 pixels, the second 3
            "vertical": {"text": "縦書きです。\nいい？", "x": 500, "y": 20, "size": 30, "vertical": True},
        }
        cls.out = {}
        for name, text in texts.items():
            project = {"version": 1, "disc": {"label": "TYPE", "standard": "NTSC", "aspect": "16:9",
                                              "first_play": "menu:m"},
                       "menus": [{"id": "m", "texts": [text], "buttons": [
                           {"id": "a", "label": "▶", "x": 640, "y": 440, "action": "title:t"}]}],
                       "titles": [{"id": "t", "source": "a.mp4"}]}
            with open(os.path.join(d, "project.oncemore.json"), "w") as f:
                json.dump(project, f)
            png = os.path.join(cls.tmp, f"{name}.png")
            rc, out, err = run_cli("preview-menu", d, "-o", png, "--state", "normal")
            assert rc == 0, err + out
            cls.out[name] = ink(png, 854, 480)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rows(self, name, x0, x1, y0=0, y1=430):
        at = self.out[name]
        return [y for y in range(y0, y1) if any(at(x, y) for x in range(x0, x1))]

    def cols(self, name, x0=0, x1=854, y0=0, y1=430):
        at = self.out[name]
        return [x for x in range(x0, x1) if any(at(x, y) for y in range(y0, y1))]

    def test_wrapped_in_the_box(self):
        xs = self.cols("wrapped")
        self.assertGreaterEqual(min(xs), 22)
        self.assertLessEqual(max(xs), 24 + 356)            # x 20 -> 24 display, + the box
        self.assertGreater(max(xs) - min(xs), 300)          # filled, not one character a line
        # 26 characters of 28 pixels, 12 to a line: 3 lines
        self.assertEqual(len(runs(self.rows("wrapped", 0, 854))), 3)

    def test_underline_and_strikethrough(self):
        # a full-width bar: one row inked all along the text
        at = self.out["under"]
        xs = self.cols("under", y0=250, y1=330)
        full = [y for y in range(250, 330) if all(at(x, y) for x in range(min(xs) + 2, max(xs) - 2))]
        self.assertTrue(full, "no underline")
        glyphs = self.rows("under", min(xs), max(xs), 250, min(full))
        self.assertLess(max(glyphs), min(full) + 1)       # under the letters
        at = self.out["struck"]
        xs = self.cols("struck", y0=330, y1=420)
        full = [y for y in range(330, 420) if all(at(x, y) for x in range(min(xs) + 2, max(xs) - 2))]
        self.assertTrue(full, "no strikethrough")
        glyphs = self.rows("struck", min(xs), max(xs), 330, 420)
        self.assertTrue(min(glyphs) < min(full) and max(full) < max(glyphs))   # through them

    def test_vertical_columns(self):
        cols = runs(self.cols("vertical"))
        self.assertEqual(len(cols), 2, cols)
        right, left = cols[1], cols[0]
        # the first line is the right-hand column, 6 characters of 30 pixels down
        tall = self.rows("vertical", right[0], right[1] + 1)
        self.assertGreater(max(tall) - min(tall), 5 * 30)
        self.assertLessEqual(max(tall), 20 + 6 * 30)
        short = self.rows("vertical", left[0], left[1] + 1)
        self.assertLess(max(short) - min(short), 3 * 30 + 1)
        self.assertLessEqual(right[1] - right[0], 32)       # one character wide


try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestEditor(unittest.TestCase):
    def test_properties_and_stage(self):
        from .test_gui import GuiServer, TestGuiBrowser
        tmp = tempfile.mkdtemp(prefix="oncemore-type-gui-")
        self.addCleanup(shutil.rmtree, tmp, True)
        s = GuiServer(tmp)
        self.addCleanup(s.close)
        s.call("/api/new", "POST", {"sample": True})
        path = os.path.join(tmp, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["menus"][0].setdefault("texts", []).append({"text": "縦書きの文字", "x": 400, "y": 40})
        s.call("/api/project", "PUT", {"project": data})

        def text():
            with open(path) as f:
                return json.load(f)["menus"][0]["texts"][-1]
        with sync_playwright() as p:
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{s.base}/#token={s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            n = len(data["menus"][0]["texts"]) - 1
            page.locator(f"#stage .el.text[data-i='{n}']").click()

            def until(test, what):
                for _ in range(100):
                    if test():
                        return
                    page.wait_for_timeout(50)
                raise AssertionError(what)
            page.check("#inspector input[data-k=vertical]")
            until(lambda: text().get("vertical") is True, "vertical")
            el = page.locator(f"#stage .el.text[data-i='{n}']")
            until(lambda: el.evaluate("e => getComputedStyle(e).writingMode") == "vertical-rl", "stage")
            # the box is now the column length
            page.fill("#inspector #text-box", "120")
            page.locator("#inspector #text-box").dispatch_event("change")
            until(lambda: text().get("height") == 120 and "width" not in text(), "height")
            page.check("#inspector input[data-k=underline]")
            until(lambda: text().get("underline") is True, "underline")
            until(lambda: "underline" in el.evaluate("e => getComputedStyle(e).textDecorationLine"), "deco")
            page.uncheck("#inspector input[data-k=vertical]")
            until(lambda: "vertical" not in text() and "height" not in text(), "horizontal again")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
