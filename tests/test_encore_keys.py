"""Small keys from the classic authoring app's help: ↑ / ↓ in the Project
panel; a tool key held down chooses the tool only while it is held; in the
Project Preview, Space plays and Ctrl (⌘) + ← / → go to the previous / next
chapter.
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
class TestEncoreKeys(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-ekeys-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})

    def test_keys(self):
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            rows = "#sidebar .nav-item[data-view], #sidebar .media-item[data-media]"
            page.locator(".nav-item[data-view=title][data-id=t1]").click(timeout=120000)
            order = page.evaluate(f"""[...document.querySelectorAll("{rows}")].map((r) => r.dataset.media || r.dataset.view + ':' + r.dataset.id)""")
            i = order.index("title:t1")
            # Project panel: ↓ the item below (opened), ↑ back
            page.keyboard.press("ArrowDown")
            nxt = order[i + 1]
            if ":" in nxt and not nxt.startswith("media/"):
                self.assertEqual(page.evaluate("S.sel.view + ':' + S.sel.id"), nxt)
            else:
                self.assertEqual(page.evaluate("S.selectedMedia"), nxt)
            page.keyboard.press("ArrowUp")
            self.assertEqual(page.evaluate("S.sel.view + ':' + S.sel.id"), "title:t1")
            # a tool key: pressed, the tool stays; held, only while held
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator(".stage .el.button").first.click()
            page.keyboard.press("t")
            self.assertEqual(page.evaluate("S.tool"), "text")
            page.keyboard.press("v")
            self.assertEqual(page.evaluate("S.tool"), "select")
            page.keyboard.down("z")
            self.assertEqual(page.evaluate("S.tool"), "zoom")
            page.wait_for_timeout(600)
            page.keyboard.up("z")
            self.assertEqual(page.evaluate("S.tool"), "select")
            # Project Preview: Space plays, Ctrl + → next chapter, Ctrl + ← previous
            page.keyboard.press("Shift+Space")
            page.locator("#sim-screen").wait_for(timeout=120000)
            page.evaluate("window.__keys = []; const o = simCall; simCall = (k) => { window.__keys.push(k); return o(k); };")
            page.locator("#sim-screen").focus()
            page.keyboard.press("Space")
            page.keyboard.press("Control+ArrowRight")
            page.keyboard.press("Control+ArrowLeft")
            page.keyboard.press("ArrowDown")
            self.assertEqual([k for k in page.evaluate("window.__keys") if k], ["play", "next", "prev", "down"])   # (None: the first screen)
            browser.close()
        self.assertEqual(errors, [])

    def test_layers_under_the_pointer(self):
        # Ctrl + right click (⌘-Control-click on a Mac): what is under the pointer, to pick a covered one
        import json
        import os
        path = os.path.join(self.dir, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        b = data["menus"][0]["buttons"][0]
        data["menus"][0].setdefault("shapes", []).append({"x": b["x"] - 20, "y": b["y"] - 10, "w": 240, "h": 50, "color": "#00000080"})
        self.s.call("/api/project", "PUT", {"project": data})
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            btn = page.locator(".stage .el.button[data-i='0']")
            btn.click(button="right", modifiers=["Control"])
            page.locator(".popup").wait_for()
            items = page.locator(".popup button").all_inner_texts()
            self.assertEqual(len(items), 2)
            self.assertIn(b["label"], items[0])
            page.locator(".popup button").nth(1).click()
            self.assertEqual(page.evaluate("JSON.stringify(S.sels)"), json.dumps([{"kind": "shape", "i": len(data["menus"][0]["shapes"]) - 1}], separators=(",", ":")))
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
