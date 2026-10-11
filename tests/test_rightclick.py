"""Right clicks on the menu stage, on a Mac and elsewhere.

On a Mac a right click is also Control-click (a one-button mouse); a
trackpad's two-finger click comes as the second button. Either one opens
the shortcut menu of what is under it, and selects it unless it is already
part of the selection; it never adds to a selection, takes from it or
starts a drag. Adding to a selection is ⌘-click on a Mac, Ctrl-click
elsewhere (and Shift-click on both); shortcuts use ⌘ on a Mac, so Control+D
does not duplicate there.

The Mac is played by the page seeing a Mac platform and getting the events
a Mac sends for Control-click: a pointerdown with the Control key and the
first button, then contextmenu.
"""

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

MAC = "Object.defineProperty(Navigator.prototype, 'platform', {get: () => 'MacIntel'});"

CONTROL_CLICK = """(el) => {
  const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  const o = {bubbles: true, cancelable: true, button: 0, ctrlKey: true, clientX: x, clientY: y};
  el.dispatchEvent(new PointerEvent('pointerdown', {...o, pointerId: 1, isPrimary: true}));
  el.dispatchEvent(new MouseEvent('contextmenu', o));
}"""


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestRightClick(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-rclick-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})

    def buttons(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)["menus"][0]["buttons"]

    def open(self, p, mac, app=False):
        from .test_gui import TestGuiBrowser
        browser = TestGuiBrowser.launch(self, p)
        extra = {"user_agent": "Mozilla/5.0 (Macintosh) OncemoreApp/1"} if app else {}
        page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US", **extra)
        if mac:
            page.add_init_script(MAC)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{self.s.base}/#token={self.s.app.token}")
        page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
        page.locator(".stage .el.button").first.wait_for()
        return browser, page, errors

    def selected(self, page):
        return page.locator(".stage .el.selected").count()

    def test_mac(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p, mac=True)
            b = page.locator(".stage .el.button")
            # ⌘-click adds to the selection
            b.nth(0).click()
            b.nth(1).click(modifiers=["Meta"])
            self.assertEqual(self.selected(page), 2)
            # Control-click on one of them: its menu, the selection kept
            b.nth(0).evaluate(CONTROL_CLICK)
            page.locator(".popup").wait_for()
            self.assertEqual(self.selected(page), 2)
            self.assertIn("Duplicate", page.inner_text(".popup"))
            page.keyboard.press("Escape")
            # Control-click on one outside the selection: it alone, and its menu
            b.nth(2).evaluate(CONTROL_CLICK)
            page.locator(".popup").wait_for()
            self.assertEqual(self.selected(page), 1)
            self.assertIn("selected", b.nth(2).get_attribute("class"))
            page.keyboard.press("Escape")
            # shortcuts are ⌘ there: Control+D does nothing, ⌘D duplicates
            n = len(self.buttons())
            page.locator("#stage").focus()
            page.keyboard.press("Control+d")
            page.wait_for_timeout(500)
            self.assertEqual(len(self.buttons()), n)
            page.keyboard.press("Meta+d")
            for _ in range(100):
                if len(self.buttons()) == n + 1:
                    break
                page.wait_for_timeout(100)
            self.assertEqual(len(self.buttons()), n + 1)
            browser.close()
        self.assertEqual(errors, [])

    def test_elsewhere(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p, mac=False)
            b = page.locator(".stage .el.button")
            # Ctrl-click adds to the selection
            b.nth(0).click()
            b.nth(1).click(modifiers=["Control"])
            self.assertEqual(self.selected(page), 2)
            # a right click on one of them keeps both, and opens their menu
            b.nth(0).click(button="right")
            page.locator(".popup").wait_for()
            self.assertEqual(self.selected(page), 2)
            page.keyboard.press("Escape")
            # nothing moved
            self.assertEqual([(x["x"], x["y"]) for x in self.buttons()][:2],
                             [(120, 220), (120, 280)])
            browser.close()
        self.assertEqual(errors, [])

    def test_app_has_no_web_menu(self):
        # in the Mac app a right click where oncemore has no menu shows none
        # (not the web view's Reload / Back), but text fields keep theirs
        shown = """(sel) => document.querySelector(sel).dispatchEvent(
            new MouseEvent('contextmenu', {bubbles: true, cancelable: true, button: 2}))"""
        with sync_playwright() as p:
            browser, page, errors = self.open(p, mac=True, app=True)
            self.assertFalse(page.evaluate(shown, "#stage"))          # (prevented)
            page.locator("#inspector input").first.wait_for()
            self.assertTrue(page.evaluate(shown, "#inspector input"))
            browser.close()
            browser, page, errors2 = self.open(p, mac=True, app=False)
            self.assertTrue(page.evaluate(shown, "#stage"))           # a browser keeps its own
            browser.close()
        self.assertEqual(errors + errors2, [])


if __name__ == "__main__":
    unittest.main()
