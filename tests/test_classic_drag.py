"""Dragging and dropping the way the classic authoring app's help describes it.

* An asset from the Project panel dropped on a menu: a video makes a title and
  a button that plays it (on a button: that button plays it), with Alt it is
  the motion background; a picture is placed where it lands (with Alt: the
  background); a sound is the menu's music.
* A chapter from the Timelines panel dropped on a button links it there, and a
  pick whip reaches chapters too.
* On the menu: a box dragged around objects selects them, Alt-drag leaves a
  copy, Shift-drag moves in a straight line.
* A layered Photoshop file dropped in from the Finder becomes a menu.
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False

MEDIA = "application/x-oncemore-media"
LINK = "application/x-oncemore-link"

# a drop the way the browser sends it, with the keys held (Playwright's own
# drag cannot hold Alt)
DROP = """([sel, type, data, alt, fx, fy]) => {
  const el = document.querySelector(sel), r = el.getBoundingClientRect();
  const dt = new DataTransfer(); dt.setData(type, data);
  const o = {bubbles: true, cancelable: true, dataTransfer: dt, altKey: alt,
             clientX: r.left + r.width * fx, clientY: r.top + r.height * fy};
  el.dispatchEvent(new DragEvent('dragover', o));
  el.dispatchEvent(new DragEvent('drop', o));
}"""

FILE_DROP = """([name, b64]) => {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const dt = new DataTransfer(); dt.items.add(new File([bytes], name));
  const o = {bubbles: true, cancelable: true, dataTransfer: dt};
  window.dispatchEvent(new DragEvent('dragenter', o));
  window.dispatchEvent(new DragEvent('drop', o));
}"""


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestClassicDrag(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-edrag-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=d=2",
                        os.path.join(self.dir, "media", "tune.wav")], check=True)

    def project(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)

    def menu(self):
        return self.project()["menus"][0]

    def open(self, p):
        from .test_gui import TestGuiBrowser
        browser = TestGuiBrowser.launch(self, p)
        page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{self.s.base}/#token={self.s.app.token}")
        page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
        page.locator(".stage .el.button").first.wait_for()
        self.page = page
        return browser, page, errors

    def until(self, test, what):
        for _ in range(300):
            if test():
                return
            self.page.wait_for_timeout(100)
        raise AssertionError(what)

    def test_assets_onto_a_menu(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            n_titles, n_buttons = len(self.project()["titles"]), len(self.menu()["buttons"])
            # a video on empty space: a title and a button that plays it, where it landed
            page.locator(".media-item[data-media='media/sample_b.mp4']").drag_to(
                page.locator("#stage"), target_position={"x": 500, "y": 80})
            self.until(lambda: len(self.menu()["buttons"]) == n_buttons + 1, "a button")
            titles, b = self.project()["titles"], self.menu()["buttons"][-1]
            self.assertEqual(len(titles), n_titles + 1)
            self.assertEqual(titles[-1]["source"], "media/sample_b.mp4")
            self.assertEqual(b["action"], f"title:{titles[-1]['id']}")
            self.assertEqual(b["label"], "SAMPLE_B")
            # a video on a button: that button plays the new title
            page.evaluate(DROP, [".stage .el.button[data-i='0']", MEDIA, "media/sample_a.mp4", False, .5, .5])
            self.until(lambda: len(self.project()["titles"]) == n_titles + 2, "another title")
            self.assertEqual(self.menu()["buttons"][0]["action"], f"title:{self.project()['titles'][-1]['id']}")
            self.assertEqual(len(self.menu()["buttons"]), n_buttons + 1)
            # Alt + video: the motion background, no title
            page.evaluate(DROP, ["#stage", MEDIA, "media/sample_a.mp4", True, .8, .8])
            self.until(lambda: self.menu().get("background_video") == "media/sample_a.mp4", "motion bg")
            self.assertEqual(len(self.project()["titles"]), n_titles + 2)
            # a picture: placed where it lands
            page.evaluate(DROP, ["#stage", MEDIA, "media/menu_bg.png", False, .5, .5])
            self.until(lambda: self.menu().get("images"), "a picture")
            img = self.menu()["images"][0]
            self.assertLess(abs(img["x"] + img["w"] / 2 - 360), 4)
            # a sound: the menu's music
            page.evaluate(DROP, ["#stage", MEDIA, "media/tune.wav", False, .5, .5])
            self.until(lambda: self.menu().get("audio") == "media/tune.wav", "music")
            browser.close()
        self.assertEqual(errors, [])

    def test_chapters(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            # the last title opened keeps its chapters in the Timelines panel
            page.click(".nav-item[data-view=title][data-id=t1]")
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.click("#left-tabs [data-lt=timelines]")
            row = page.locator(".crow[data-link='chapter:t1:2']")
            row.wait_for()
            row.drag_to(page.locator(".stage .el.button[data-i='1']"))
            self.until(lambda: self.menu()["buttons"][1]["action"] == "chapter:t1:2", "linked")
            # the pick whip reaches chapters too
            page.locator(".stage .el.button[data-i='2']").click()
            whip = page.locator("#inspector .whip[data-whip=action]")
            a, b = whip.bounding_box(), page.locator(".crow[data-link='chapter:t1:3']").bounding_box()
            page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
            page.mouse.down()
            page.mouse.move(b["x"] + 20, b["y"] + b["height"] / 2, steps=8)
            page.mouse.up()
            self.until(lambda: self.menu()["buttons"][2]["action"] == "chapter:t1:3", "whipped")
            browser.close()
        self.assertEqual(errors, [])

    def test_on_the_menu(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            stage = page.locator("#stage").bounding_box()
            b = page.locator(".stage .el.button")
            # a box around the first two buttons selects both
            b0, b1 = b.nth(0).bounding_box(), b.nth(1).bounding_box()
            page.mouse.move(b0["x"] - 10, b0["y"] - 6)
            page.mouse.down()
            page.mouse.move(b1["x"] + b1["width"] + 10, b1["y"] + b1["height"] + 6, steps=6)
            page.mouse.up()
            self.assertEqual(page.locator(".stage .el.selected").count(), 2)
            # a click on empty space clears it
            page.mouse.click(stage["x"] + stage["width"] - 20, stage["y"] + 20)
            self.assertEqual(page.locator(".stage .el.selected").count(), 0)
            # Alt-drag leaves the button and drops a copy
            n = len(self.menu()["buttons"])
            c = b.nth(2).bounding_box()
            page.mouse.move(c["x"] + 5, c["y"] + 5)
            page.keyboard.down("Alt")
            page.mouse.down()
            page.mouse.move(c["x"] + 5 + 120, c["y"] + 5, steps=6)
            page.mouse.up()
            page.keyboard.up("Alt")
            self.until(lambda: len(self.menu()["buttons"]) == n + 1, "a copy")
            bs = self.menu()["buttons"]
            self.assertEqual((bs[2]["x"], bs[2]["y"]), (120, 340))     # the original stays
            self.assertGreater(bs[-1]["x"], 160)
            self.assertEqual(bs[-1]["y"], 340)
            self.assertNotEqual(bs[-1]["id"], bs[2]["id"])
            # Shift-drag moves in a straight line (a slanting drag stays level)
            c = b.nth(0).bounding_box()
            page.mouse.move(c["x"] + 5, c["y"] + 5)
            page.keyboard.down("Shift")
            page.mouse.down()
            page.mouse.move(c["x"] + 5 + 100, c["y"] + 5 + 12, steps=6)
            page.mouse.up()
            page.keyboard.up("Shift")
            self.until(lambda: self.menu()["buttons"][0]["x"] != 120, "moved")
            self.assertEqual(self.menu()["buttons"][0]["y"], 220)
            browser.close()
        self.assertEqual(errors, [])

    def test_resize_handles(self):
        # a rectangle's handles: the corner resizes it from the opposite corner,
        # Shift keeps its proportions, Alt resizes it from its centre
        data = self.project()
        data["menus"][0].setdefault("shapes", []).append({"x": 480, "y": 300, "w": 100, "h": 50, "color": "#FF000080"})
        self.s.call("/api/project", "PUT", {"project": data})
        shape = lambda: {k: self.menu()["shapes"][-1][k] for k in ("x", "y", "w", "h")}  # noqa: E731
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            n = len(self.menu()["shapes"]) - 1
            page.locator(f".stage .el[data-kind=shape][data-i='{n}']").click()
            st = page.locator("#stage").bounding_box()
            kx = st["width"] / 720                                   # (screen px per grid px, across)
            ky = st["height"] / (self.project()["disc"].get("height") or 480)

            def drag(h, dx, dy, keys=()):
                hb = page.locator(f".stage .rz-h[data-h={h}]").bounding_box()
                x, y = hb["x"] + hb["width"] / 2, hb["y"] + hb["height"] / 2
                page.mouse.move(x, y)
                for k in keys:
                    page.keyboard.down(k)
                page.mouse.down()
                page.mouse.move(x + dx * kx, y + dy * ky, steps=5)
                page.mouse.up()
                for k in keys:
                    page.keyboard.up(k)
            drag("se", 50, 30)
            self.until(lambda: shape()["w"] != 100, "resized")
            b = shape()
            self.assertEqual((b["x"], b["y"]), (480, 300))
            self.assertLess(abs(b["w"] - 150), 3)
            self.assertLess(abs(b["h"] - 80), 3)
            # Shift: the proportions stay (150:80)
            drag("se", 75, 10, ["Shift"])
            self.until(lambda: shape()["w"] != b["w"], "resized again")
            c = shape()
            self.assertLess(abs(c["w"] / c["h"] - b["w"] / b["h"]), 0.05)
            self.assertEqual((c["x"], c["y"]), (480, 300))
            # Alt: from the centre (the left edge moves out as far as the right)
            cx = c["x"] + c["w"] / 2
            drag("e", 20, 0, ["Alt"])
            self.until(lambda: shape()["w"] != c["w"], "from the centre")
            d = shape()
            self.assertLess(abs(d["x"] + d["w"] / 2 - cx), 1.5)
            self.assertLess(d["x"], c["x"])
            self.assertEqual(d["h"], c["h"])
            browser.close()
        self.assertEqual(errors, [])

    def test_routing_arrow_onto_a_button(self):
        # with routing shown, an arrow dragged onto another button: that key goes there
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            page.check("#routing")
            bs = self.menu()["buttons"]
            first, last = bs[0]["id"], bs[-1]["id"]
            hit = page.locator(f".stage svg.routing path.route-hit[data-hit='{first}:down']")
            hit.wait_for(timeout=60000)
            # a point on the arrow: halfway along it
            x, y = page.evaluate("""(sel) => { const p = document.querySelector(sel), l = p.getTotalLength(),
                q = p.getPointAtLength(l / 2), m = p.getScreenCTM(); return [q.x * m.a + m.e, q.y * m.d + m.f]; }""",
                                 f".stage svg.routing path.route-hit[data-hit='{first}:down']")
            t = page.locator(".stage .el.button").last.bounding_box()
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(t["x"] + t["width"] / 2, t["y"] + t["height"] / 2, steps=8)
            page.mouse.up()
            self.until(lambda: self.menu()["buttons"][0].get("nav", {}).get("down") == last, "routed")
            page.locator(f".stage svg.routing path.manual[data-route='{first}:down']").wait_for(timeout=60000)
            browser.close()
        self.assertEqual(errors, [])

    def test_text_typed_in_place(self):
        # double-click a text: type in it (Backspace does not delete the object); Esc ends it.
        # A button's words: Enter ends it
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            n_texts, n_buttons = len(self.menu().get("texts", [])), len(self.menu()["buttons"])
            page.locator(".stage .el.text[data-i='0']").dblclick()
            page.locator(".stage .el.text.editing").wait_for()
            page.keyboard.type("HELLOX")
            page.keyboard.press("Backspace")
            page.keyboard.press("Escape")
            self.until(lambda: self.menu()["texts"][0]["text"] == "HELLO", "text")
            page.locator(".stage .el.button[data-i='1']").dblclick()
            page.locator(".stage .el.button.editing").wait_for()
            page.keyboard.type("GO ON")
            page.keyboard.press("Enter")
            self.until(lambda: self.menu()["buttons"][1]["label"] == "GO ON", "label")
            m = self.menu()
            self.assertEqual((len(m["texts"]), len(m["buttons"])), (n_texts, n_buttons))
            browser.close()
        self.assertEqual(errors, [])

    def test_type_handles(self):
        # a text's corner handle scales its type; the opposite corner stays
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            t0 = self.menu()["texts"][0]
            size0 = t0["size"]                                      # (56 in the sample)
            page.locator(".stage .el.text[data-i='0']").click()
            self.assertEqual(page.locator(".stage .rz-h").count(), 4)
            hb, el = page.locator(".stage .rz-h[data-h=se]").bounding_box(), page.locator(".stage .el.text[data-i='0']").bounding_box()
            x, y = hb["x"] + hb["width"] / 2, hb["y"] + hb["height"] / 2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + el["width"] / 2, y + 2, steps=6)       # half as wide again
            page.mouse.up()
            self.until(lambda: self.menu()["texts"][0]["size"] != size0, "type scaled")
            t1 = self.menu()["texts"][0]
            self.assertEqual((t1["x"], t1["y"]), (t0["x"], t0["y"]))
            self.assertLess(abs(t1["size"] / size0 - 1.5), 0.15)
            browser.close()
        self.assertEqual(errors, [])

    def test_photoshop_file_becomes_a_menu(self):
        from .test_psdmenu import design
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            n = len(self.project()["menus"])
            page.evaluate(FILE_DROP, ["art.psd", base64.b64encode(design()).decode()])
            self.until(lambda: len(self.project()["menus"]) == n + 1, "a menu")
            self.assertEqual(self.project()["menus"][-1]["psd"], "media/art.psd")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
