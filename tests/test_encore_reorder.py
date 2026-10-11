"""Rows dragged to a new place, as in the classic authoring app's panels:
a slideshow's slides, a timeline's clips, a playlist's items and a menu's
layers (▲ / ▼ stay)."""

import json
import os
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
class TestEncoreReorder(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-ereorder-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        shutil.copy(os.path.join(self.dir, "media", "menu_bg.png"), os.path.join(self.dir, "media", "second.png"))
        data = self.project()
        data["titles"].append({"id": "pics", "slideshow": {"slides": [
            {"image": "media/menu_bg.png"}, {"image": "media/second.png"}]}})
        data["titles"].append({"id": "joined", "clips": [
            {"source": "media/sample_a.mp4"}, {"source": "media/sample_b.mp4"}]})
        data.setdefault("playlists", []).append({"id": "pl", "items": ["t1", "t2"]})
        self.s.call("/api/project", "PUT", {"project": data})

    def project(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)

    def title(self, tid):
        return next(t for t in self.project()["titles"] if t["id"] == tid)

    def test_reorder(self):
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator(".nav-item[data-view=title][data-id=t1]").wait_for(timeout=120000)

            def until(test, what):
                for _ in range(200):
                    if test():
                        return
                    page.wait_for_timeout(50)
                raise AssertionError(what)

            def drag(src, dst, at=(8, 8)):
                a, b = page.locator(src).bounding_box(), page.locator(dst).bounding_box()
                page.mouse.move(a["x"] + at[0], a["y"] + at[1])
                page.mouse.down()
                page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=8)
                page.mouse.up()
            # a playlist's items
            page.click(".nav-item[data-view=playlist][data-id=pl]")
            page.locator("[data-item='1']").wait_for()
            drag("[data-item='1']", "[data-item='0']")
            until(lambda: next(x for x in self.project()["playlists"] if x["id"] == "pl")["items"] == ["t2", "t1"], "items")
            # a slideshow's slides (by the card, not its fields)
            page.click(".nav-item[data-view=title][data-id=pics]")
            page.locator("[data-slide='1']").wait_for(timeout=60000)
            drag("[data-slide='1']", "[data-slide='0']", at=(4, 4))
            until(lambda: [s["image"] for s in self.title("pics")["slideshow"]["slides"]] == ["media/second.png", "media/menu_bg.png"], "slides")
            # a timeline's clips (by the number)
            page.click(".nav-item[data-view=title][data-id=joined]")
            page.locator("tr[data-clip='1'] td.n").wait_for(timeout=60000)
            drag("tr[data-clip='0'] td.n", "tr[data-clip='1']", at=(4, 4))
            until(lambda: [c["source"] for c in self.title("joined")["clips"]] == ["media/sample_b.mp4", "media/sample_a.mp4"], "clips")
            # a menu's layers: the third button to the top
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator("#layers .layer-row[data-lk=button][data-li='2']").wait_for(timeout=60000)
            ids = [b["id"] for b in self.project()["menus"][0]["buttons"]]
            drag("#layers .layer-row[data-lk=button][data-li='2'] .nm", "#layers .layer-row[data-lk=button][data-li='0']")
            until(lambda: [b["id"] for b in self.project()["menus"][0]["buttons"]] == [ids[2], ids[0], ids[1]], "layers")
            page.locator("#layers .layer-row.selected[data-lk=button][data-li='0']").wait_for()
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
