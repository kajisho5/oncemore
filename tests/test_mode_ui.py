"""The app as the project's authoring mode makes it (DECISIONS §127): DVD-only
settings say so, and cannot be added, in a project made for a Blu-ray;
Check checks the format Build makes; controls that did nothing are gone or
work. And the web version plays a title without its buttons over the
picture instead of stopping on them."""

import json
import os
import shutil
import tempfile
import unittest

from oncemore import scaffold

from .helpers import have, json_lines, run_cli
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False

GO = {"id": "go", "start": 0, "end": 2, "x": 100, "y": 100, "width": 200, "height": 60,
      "action": "title:t1"}


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestCheckFormats(unittest.TestCase):
    """Buttons over a title: a DVD has them, a Blu-ray refuses them, the web
    version plays the title without them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-mode-ui-")
        scaffold.init(cls.tmp)
        path = os.path.join(cls.tmp, "project.oncemore.json")
        with open(path) as f:
            d = json.load(f)
        d["titles"][1]["buttons"] = [GO]
        with open(path, "w") as f:
            json.dump(d, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def validate(self, fmt):
        rc, out, _ = run_cli("--json", "validate", self.tmp, "--format", fmt)
        return rc, " ".join(i["message"] for e in json_lines(out) for i in e.get("issues", []))

    def test_formats(self):
        self.assertEqual(self.validate("dvd")[0], 0)
        rc, issues = self.validate("bluray")
        self.assertNotEqual(rc, 0)
        self.assertIn("buttons over a title are for DVD", issues)
        self.assertEqual(self.validate("web"), (0, ""))


@unittest.skipUnless(PLAYWRIGHT and have("ffmpeg"), "needs playwright and ffmpeg")
class TestApp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-mode-ui-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        self.path = os.path.join(self.dir, "project.oncemore.json")

    def edit(self, fn):
        with open(self.path) as f:
            d = json.load(f)
        fn(d)
        with open(self.path, "w") as f:
            json.dump(d, f)

    def open(self, p):
        from .test_gui import TestGuiBrowser
        browser = TestGuiBrowser.launch(self, p)
        page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{self.s.base}/#token={self.s.app.token}")
        page.locator(".nav-item[data-view=title][data-id=t1]").wait_for(timeout=120000)
        return browser, page, errors

    def test_bluray_mode(self):
        def bluray(d):
            d["disc"]["format"] = "bluray"
            d["scripts"] = {"go": "play title:t2;"}
        self.edit(bluray)
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            page.click(".nav-item[data-view=title][data-id=t1]")
            # DVD-only parts of a title: said so, and nothing new added
            for sel in ("#add-tbtn", "#add-angle"):
                self.assertTrue(page.locator(sel).is_disabled(), sel)
            body = page.locator("#inspector").inner_text()
            self.assertIn("a Blu-ray build stops on them", body)
            self.assertIn("its build leaves angles out", body)
            self.assertIn("its build leaves closed captions out", body)
            # a Blu-ray keeps no fields; the per-title DVD bitrate is not offered
            scans = page.locator("select[data-k=scan] option").evaluate_all(
                "(os) => os.map((o) => o.value)")
            self.assertNotIn("interlaced", scans)
            self.assertTrue(page.locator("select[data-k=video_bitrate]").evaluate(
                "(e) => e.closest('label').hidden"))
            # links cannot choose a navigation script
            self.assertEqual(page.locator("select[data-k=end_action] option[value='commands:go']")
                             .count(), 0)
            # Transcode now makes the DVD's video: not offered
            page.click(".nav-item[data-view=title][data-id=t1]", button="right")
            self.assertTrue(page.locator(".popup button:has-text('Transcode this title now')")
                            .is_disabled())
            page.keyboard.press("Escape")
            # Build: the Blu-ray's size; no Source row
            page.click("[data-lt=build]")
            info = page.locator("#sidebar .build-panel").inner_text()
            self.assertIn("BD25", info)
            self.assertNotIn("Current Project", info)
            browser.close()
        self.assertEqual(errors, [])

    def test_dvd_mode_and_controls(self):
        self.edit(lambda d: d.setdefault("playlists", []).append(
            {"id": "pl", "items": [{"title": "t1"}]}))
        with sync_playwright() as p:
            browser, page, errors = self.open(p)
            # Random and Shuffle say where they work
            page.click(".nav-item[data-view=playlist][data-id=pl]")
            labels = page.locator("select[data-k=order] option").all_inner_texts()
            self.assertIn("Random (Blu-ray / web; a DVD plays in order)", labels)
            # the scan choices keep fields on a DVD
            page.click(".nav-item[data-view=title][data-id=t1]")
            scans = page.locator("select[data-k=scan] option").evaluate_all(
                "(os) => os.map((o) => o.value)")
            self.assertIn("interlaced", scans)
            # nothing that does nothing: no panel menus, no close boxes
            self.assertEqual(page.locator(".panel-menu").count(), 0)
            self.assertEqual(page.locator(".tabbar .tab .x").count(), 0)
            # the timeline's ▾ lists the titles to open
            page.click("#tl-pick")
            page.click(".popup button:has-text('Sample Title B')")
            page.locator("#tl-pick", has_text="Sample Title B").wait_for()
            # Build after a Blu-ray chosen there, then the project opened again:
            # back on the project's mode (DVD)
            page.click("[data-lt=build]")
            page.select_option("#sidebar #bformat", "bluray")
            page.evaluate("projectSwitched(S)")
            page.click("[data-lt=build]")
            self.assertEqual(page.input_value("#sidebar #bformat"), "dvd")
            browser.close()
        self.assertEqual(errors, [])

    def test_new_project_dialog(self):
        os.remove(self.path)
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator("#np-sample").wait_for()
            self.assertEqual(page.locator("#np-sample").inner_text(), "Create sample project")
            self.assertEqual(page.locator(".np-dialog .tab").count(), 0)     # (one lone tab)
            self.assertEqual(page.locator(".np-dialog .dlg-title").inner_text(), "New project")
            browser.close()


class TestDocuments(unittest.TestCase):
    """What the documents say about formats, as the code does it."""

    def read(self, *parts):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, *parts), encoding="utf-8") as f:
            return f.read()

    def test_facts(self):
        from oncemore import cli
        fast = next(a for a in cli.make_parser()._subparsers._group_actions[0].choices["build"]
                    ._actions if "--fast" in a.option_strings)
        self.assertIn("Blu-ray", fast.help)                  # (two passes on a DVD only)
        for name in ("README.md", "README.ja.md"):
            text = self.read(name)
            self.assertIn("[--format dvd|bluray|web]", text, name)
            self.assertIn("playlist:<id>` |", text, name)
        self.assertNotIn("only chapter thumbnails\n  animate", self.read("README.md"))
        self.assertNotIn("Without it subtitles start off", self.read("README.md"))
        self.assertIn("Blu-ray", self.read("oncemore", "project.schema.json").split(
            '"transcode"')[1][:600])
        for name in ("manual-en.md", "manual-ja.md"):
            self.assertNotIn("smooth edges", self.read("oncemore", "gui", "static", name).split(
                "Highlights on a DVD")[-1][:200])


if __name__ == "__main__":
    unittest.main()
