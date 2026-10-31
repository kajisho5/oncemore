"""Buttons over a title in the app: Properties > Buttons over the title adds
one at the playhead, sets its link and times; its box on the picture shows
while it is shown and drags to move and resize; Preview's time in the title
brings the buttons up, and they run their links."""

import json
import os
import shutil
import tempfile
import unittest

from .test_gui import GuiServer

try:
    from playwright.sync_api import expect, sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestTitleButtonsEditor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-tbtn-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        self.path = os.path.join(self.dir, "project.oncemore.json")

    def project(self):
        with open(self.path) as f:
            return json.load(f)

    def open(self, p, view):
        from .test_gui import TestGuiBrowser
        browser = TestGuiBrowser.launch(self, p)
        page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{self.s.base}/#token={self.s.app.token}")
        page.click(view, timeout=120000)
        return browser, page, errors

    def until(self, page, test, what):
        for _ in range(300):
            t = self.project()["titles"][0]
            if test(t):
                return t
            page.wait_for_timeout(100)
        raise AssertionError(f"{what}: {self.project()['titles'][0].get('buttons')}")

    def test_editor(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p, ".nav-item[data-view=title][data-id=t1]")
            page.locator("#add-tbtn").wait_for()
            page.click("#add-tbtn")                              # at the playhead (0 s), 5 s long
            t = self.until(page, lambda t: len(t.get("buttons", [])) == 1, "added")
            b = t["buttons"][0]
            self.assertEqual((b["id"], b["start"], b["end"], b["width"], b["height"]), ("b1", 0, 5, 200, 60))
            # its link and its end
            page.select_option("[data-tbtn='0'] select", "menu:main")
            self.until(page, lambda t: t["buttons"][0]["action"] == "menu:main", "link")
            page.fill("[data-tbtn='0'] [data-k=end]", "00:00:06.000")
            page.press("[data-tbtn='0'] [data-k=end]", "Enter")
            self.until(page, lambda t: t["buttons"][0]["end"] == 6, "end")
            # its box on the picture, moved and resized by dragging
            box = page.locator("#tbtn-layer .tbtn-box")
            box.wait_for()
            r = box.bounding_box()
            page.mouse.move(r["x"] + r["width"] / 2, r["y"] + r["height"] / 2)
            page.mouse.down()
            page.mouse.move(r["x"] + r["width"] / 2 + 40, r["y"] + r["height"] / 2 - 30, steps=5)
            page.mouse.up()
            t = self.until(page, lambda t: t["buttons"][0]["x"] > 260, "moved")
            self.assertLess(t["buttons"][0]["y"], b["y"])
            r = page.locator("#tbtn-layer .tbtn-corner").bounding_box()
            page.mouse.move(r["x"] + 5, r["y"] + 5)
            page.mouse.down()
            page.mouse.move(r["x"] + 45, r["y"] + 25, steps=5)
            page.mouse.up()
            self.until(page, lambda t: t["buttons"][0]["width"] > 200 and t["buttons"][0]["height"] > 60,
                       "resized")
            # a bar under the picture; past its end, no box
            self.assertEqual(page.locator("#timeline .tbtn-bar").count(), 1)
            page.fill("#tc-input", "00:00:07.000")
            page.press("#tc-input", "Enter")
            expect(page.locator("#tbtn-layer .tbtn-box")).to_have_count(0)   # the page's CSP forbids eval
            # its colours, then gone
            page.locator("[data-tbtn-color=highlight]").evaluate(
                "(e) => { e.value = '#00ff00'; e.dispatchEvent(new Event('change')); }")
            self.until(page, lambda t: t.get("button_colors", {}).get("highlight") == "#00FF00", "colour")
            page.click("[data-del-tbtn='0']")
            self.until(page, lambda t: "buttons" not in t and "button_colors" not in t, "removed")
            browser.close()
        self.assertEqual(errors, [])

    def test_not_with_subtitles(self):
        data = self.project()
        os.makedirs(os.path.join(self.dir, "media"), exist_ok=True)
        with open(os.path.join(self.dir, "media", "a.srt"), "w") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHello\n")
        data["titles"][0]["subtitles"] = [{"file": "media/a.srt"}]
        with open(self.path, "w") as f:
            json.dump(data, f)
        with sync_playwright() as p:
            browser, page, errors = self.open(p, ".nav-item[data-view=title][data-id=t1]")
            page.locator("#add-tbtn").wait_for()
            self.assertTrue(page.locator("#add-tbtn").is_disabled())
            page.locator(".hint.warn", has_text="subtitles").wait_for()
            browser.close()
        self.assertEqual(errors, [])

    def test_preview(self):
        data = self.project()
        data["disc"]["first_play"] = "title:t2"
        data["titles"][1]["buttons"] = [
            {"id": "go", "start": 2, "end": 6, "x": 100, "y": 100, "width": 200, "height": 60,
             "action": "title:t1"},
            {"id": "back", "start": 2, "end": 6, "x": 100, "y": 300, "width": 200, "height": 60,
             "action": "menu:main"}]
        with open(self.path, "w") as f:
            json.dump(data, f)
        with sync_playwright() as p:
            browser, page, errors = self.open(p, ".nav-item[data-view=title][data-id=t2]")
            page.select_option("#workspaces", "sim")             # Project Preview, from first play
            page.locator("#sim-status", has_text="t2").wait_for(timeout=120000)
            self.assertEqual(page.locator("#sim-screen .tbtn-sim").count(), 0)     # at 0 s
            page.locator("#sim-seek").evaluate(
                "(e) => { e.value = '3'; e.dispatchEvent(new Event('change')); }")
            expect(page.locator("#sim-screen .tbtn-sim")).to_have_count(2, timeout=60000)
            page.locator("#sim-screen").press("ArrowDown")       # back
            page.locator("#sim-screen").press("Enter")
            page.locator("#sim-status", has_text="main").wait_for(timeout=120000)
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
