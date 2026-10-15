"""The Timeline viewer's keys and drags as the classic authoring app's help
lists them: drag in the ruler to move the current-time indicator; Home / End;
← / → a frame; the wheel with Ctrl (⌘) a frame; Shift+8 adds a chapter;
Ctrl (⌘)+Shift+8 or Shift+* on the keypad sets the poster frame; Ctrl (⌘)+Alt
dragged from a chapter mark sets that chapter's poster frame; Ctrl (⌘)+. and
the keypad's + / − zoom.
"""

import shutil
import tempfile
import unittest

from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestClassicTimeline(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-etl-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})

    def test_timeline(self):
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.locator("#tl-ruler").wait_for()
            for _ in range(200):
                if page.evaluate("!!(S.tl && S.tl.dur && S.tl.fps)"):
                    break
                page.wait_for_timeout(50)
            fps, dur = page.evaluate("[S.tl.fps, S.tl.dur]")
            now = lambda: page.evaluate("S.playhead.t1 || 0")  # noqa: E731
            chapters = lambda: page.evaluate("chapterEntries(curTitle()).map((c) => [c.time, c.poster])")  # noqa: E731

            def until(test, what):
                for _ in range(100):
                    if test():
                        return
                    page.wait_for_timeout(50)
                raise AssertionError(f"{what}: {now()} {chapters()}")
            page.locator("#tl-tc").click()                       # (out of any field)
            # drag in the ruler: the indicator follows
            r = page.locator("#tl-ruler").bounding_box()
            page.mouse.move(r["x"] + 5, r["y"] + r["height"] / 2)
            page.mouse.down()
            page.mouse.move(r["x"] + r["width"] * 0.5, r["y"] + r["height"] / 2, steps=5)
            mid = now()
            self.assertGreater(mid, dur * 0.3)
            page.mouse.move(r["x"] + r["width"] * 0.25, r["y"] + r["height"] / 2, steps=5)
            page.mouse.up()
            self.assertLess(now(), mid)
            # Home / End / arrows
            page.keyboard.press("Home")
            self.assertEqual(now(), 0)
            page.keyboard.press("End")
            self.assertAlmostEqual(now(), round((dur - 1 / fps) * fps) / fps, places=3)
            page.keyboard.press("ArrowLeft")
            self.assertAlmostEqual(now(), round((dur - 2 / fps) * fps) / fps, places=3)
            page.keyboard.press("Home")
            page.keyboard.press("ArrowRight")
            page.keyboard.press("ArrowRight")
            self.assertAlmostEqual(now(), 2 / fps, places=3)
            # Ctrl + wheel: a frame
            r = page.locator("#tl").bounding_box()
            page.mouse.move(r["x"] + r["width"] / 2, r["y"] + r["height"] / 2)
            page.keyboard.down("Control")
            page.mouse.wheel(0, 100)
            page.keyboard.up("Control")
            until(lambda: abs(now() - 3 / fps) < 1e-3, "wheel")
            # Shift+8: a chapter at the indicator
            n = len(chapters())
            page.locator("#tl-tc").click()
            page.keyboard.press("End")
            page.keyboard.press("Shift+8")
            until(lambda: len(chapters()) == n + 1, "a chapter")
            # Ctrl+Shift+8 and Shift+* (keypad): the poster frame of the chapter the indicator is in
            page.keyboard.press("Home")
            for _ in range(10):
                page.keyboard.press("ArrowRight")
            page.keyboard.press("Control+Shift+8")
            until(lambda: chapters()[0][1] is not None and abs(chapters()[0][1] - 10 / fps) < 2e-3, "poster")
            page.keyboard.press("ArrowRight")
            page.keyboard.press("Shift+NumpadMultiply")
            until(lambda: abs(chapters()[0][1] - 11 / fps) < 2e-3, "poster from the keypad")
            self.assertEqual(len(chapters()), n + 1)                 # (not a chapter too)
            # Ctrl + Alt dragged from the second chapter mark: its poster frame, in that chapter
            mk = page.locator(".tl-chapter[data-tlch='1']")
            b = mk.bounding_box()
            c1, c2 = chapters()[1][0], chapters()[2][0]
            page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
            page.keyboard.down("Control")
            page.keyboard.down("Alt")
            page.mouse.down()
            page.mouse.move(b["x"] + 60, b["y"] + b["height"] / 2, steps=6)
            page.mouse.up()
            page.keyboard.up("Alt")
            page.keyboard.up("Control")
            until(lambda: chapters()[1][1] is not None, "poster by drag")
            self.assertGreater(chapters()[1][1], c1)
            self.assertLess(chapters()[1][1], c2)
            self.assertEqual(chapters()[1][0], c1)                    # (the mark did not move)
            # zoom: Ctrl+. in, keypad − out
            page.locator("#tl-tc").click()
            page.keyboard.press("Control+Period")
            until(lambda: page.evaluate("S.tlZoom") == 2, "zoom in")
            page.keyboard.press("NumpadSubtract")
            until(lambda: page.evaluate("S.tlZoom") == 1, "zoom out")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
