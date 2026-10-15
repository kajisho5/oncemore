"""The Flowchart as the classic authoring app's help describes it: a title,
menu or playlist dragged in from the Project panel links by where it lands
(the disc: first play; a title: its end action; one of a menu's buttons:
that button; a menu: a new button), and the pick whip from one of a menu's
buttons listed in the Flowchart links that button.
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


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestClassicFlow(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-eflow-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})

    def project(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)

    def test_flowchart(self):
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1800, "height": 1000}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=flow]", timeout=120000)

            def until(test, what):
                for _ in range(200):
                    if test(self.project()):
                        return
                    page.wait_for_timeout(50)
                raise AssertionError(what)

            def node(sel):
                loc = page.locator(f"#flow {sel}")
                loc.wait_for(timeout=60000)
                return loc
            t2 = page.locator(".nav-item[data-view=title][data-id=t2]")
            # onto the disc: it plays first
            t2.drag_to(node("g.node[data-node=fp]"))
            until(lambda d: d["disc"]["first_play"] == "title:t2", "first play")
            # onto a title: it follows that title
            t2.drag_to(node("g.node[data-node='title:t1']"))
            until(lambda d: d["titles"][0]["end_action"] == "title:t2", "end action")
            # onto one of a menu's buttons: that button plays it
            t2.drag_to(node("g.node[data-node='menu:main'] [data-btn='1']"))
            until(lambda d: d["menus"][0]["buttons"][1]["action"] == "title:t2", "button")
            # onto the menu itself: a new button, under the last one
            n = len(self.project()["menus"][0]["buttons"])
            page.evaluate("document.querySelector('#flow svg').dataset.old = '1'")
            t2.drag_to(node("g.node[data-node='menu:main']"), target_position={"x": 30, "y": 25})
            until(lambda d: len(d["menus"][0]["buttons"]) == n + 1, "new button")
            bs = self.project()["menus"][0]["buttons"]
            self.assertEqual(bs[-1]["action"], "title:t2")
            self.assertGreater(bs[-1]["y"], bs[-2]["y"])
            for _ in range(200):                  # (the flowchart drawn again before going on)
                if page.evaluate("(() => { const s = document.querySelector('#flow svg'); return !!s && !s.dataset.old; })()"):
                    break
                page.wait_for_timeout(50)
            # the pick whip from the first button's row: that button, without asking
            a = node("g.node[data-node='menu:main'] [data-btn='0']").bounding_box()
            b = page.locator(".nav-item[data-view=title][data-id=t1]").bounding_box()   # (to the Project panel)
            page.mouse.move(a["x"] + 20, a["y"] + a["height"] / 2)
            page.mouse.down()
            for k in range(1, 11):
                page.mouse.move(a["x"] + 20 + (b["x"] + b["width"] / 2 - a["x"] - 20) * k / 10,
                                a["y"] + a["height"] / 2 + (b["y"] + b["height"] / 2 - a["y"] - a["height"] / 2) * k / 10)
            page.mouse.up()
            until(lambda d: d["menus"][0]["buttons"][0]["action"] == "title:t1", "whip from a button")
            self.assertEqual(page.locator(".popup").count(), 0)
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
