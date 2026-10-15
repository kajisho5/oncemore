"""The authoring mode (`disc.format`): a project made for a DVD or for a
Blu-ray. New Project chooses it; the disc's Properties change it; Build,
Check project and the command line make that format unless told otherwise."""

import json
import os
import shutil
import tempfile
import unittest

from oncemore import cli, scaffold
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have, json_lines, run_cli
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


def project(d):
    return build_project(d, "/virtual/project.oncemore.json", check_files=False)


class TestModel(unittest.TestCase):
    def test_loaded(self):
        d = sample_project()
        self.assertEqual(project(d).disc.format, "dvd")             # (the default)
        d["disc"]["format"] = "bluray"
        self.assertEqual(project(d).disc.format, "bluray")
        d["disc"]["format"] = "web"                                  # (a build, not a mode)
        with self.assertRaises(ProjectError) as e:
            project(d)
        self.assertIn("disc.format", str(e.exception.issues))

    def test_command_line_default(self):
        parser = cli.make_parser()
        for cmd in (["build", "p", "-o", "out"], ["iso", "p", "-o", "x.iso"], ["validate", "p"]):
            self.assertIsNone(parser.parse_args(cmd).format, cmd)   # (the project's, then)


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestCheck(unittest.TestCase):
    """validate checks for the project's format: a navigation script (DVD
    only) is refused once the project is made for a Blu-ray."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-mode-")
        scaffold.init(cls.tmp)
        cls.path = os.path.join(cls.tmp, "project.oncemore.json")
        with open(cls.path) as f:
            d = json.load(f)
        d["scripts"] = {"go": "play title:t1;"}
        d["menus"][0]["buttons"][0]["action"] = "commands:go"
        cls.data = d

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def validate(self, fmt, *args):
        d = json.loads(json.dumps(self.data))
        if fmt:
            d["disc"]["format"] = fmt
        with open(self.path, "w") as f:
            json.dump(d, f)
        rc, out, _ = run_cli("--json", "validate", self.tmp, *args)
        issues = [i["message"] for e in json_lines(out) for i in e.get("issues", [])]
        return rc, issues

    def test_follows_the_mode(self):
        self.assertEqual(self.validate(None), (0, []))
        rc, issues = self.validate("bluray")
        self.assertNotEqual(rc, 0)
        self.assertIn("navigation scripts (commands:...) are for DVD", " ".join(issues))
        self.assertEqual(self.validate("bluray", "--format", "dvd"), (0, []))


class TestServer(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-mode-new-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)

    def disc(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)["disc"]

    def test_new_project(self):
        status, _ = self.s.call("/api/new", "POST", {"format": "bluray", "label": "HD"})
        self.assertEqual(status, 200)
        self.assertEqual(self.disc()["format"], "bluray")
        self.s.call("/api/new", "POST", {"force": True})
        self.assertNotIn("format", self.disc())                      # (DVD: the default)
        status, r = self.s.call("/api/new", "POST", {"force": True, "format": "hddvd"})
        self.assertEqual(status, 400)


@unittest.skipUnless(PLAYWRIGHT and have("ffmpeg"), "needs playwright and ffmpeg")
class TestApp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-mode-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.path = os.path.join(self.dir, "project.oncemore.json")

    def disc(self):
        with open(self.path) as f:
            return json.load(f)["disc"]

    def until(self, page, test, what):
        for _ in range(300):
            if os.path.exists(self.path) and test(self.disc()):
                return
            page.wait_for_timeout(100)
        raise AssertionError(f"{what}: {self.disc() if os.path.exists(self.path) else None}")

    def test_new_project_for_a_bluray(self):
        from .test_gui import TestGuiBrowser
        with sync_playwright() as p:
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            # New Project: DVD or Blu-ray, and what each is encoded to
            self.assertIn("MPEG-2", page.locator("#np-tx").inner_text())
            page.check("input[name=np-mode][value=bluray]")
            self.assertIn("H.264", page.locator("#np-tx").inner_text())
            page.click("#np-sample")
            self.until(page, lambda d: d.get("format") == "bluray", "made for a Blu-ray")
            # the disc's Properties: the Blu-ray's size, not the DVD's
            page.click(".nav-item[data-view=disc]", timeout=120000)
            page.locator("select[data-k='bluray.target']").wait_for()
            self.assertEqual(page.locator("select[data-k=target]").count(), 0)
            page.select_option("select[data-k='bluray.target']", "BD50")
            self.until(page, lambda d: d.get("bluray") == {"target": "BD50"}, "BD-50")
            # Build makes a Blu-ray
            page.click("[data-lt=build]")
            self.assertEqual(page.locator("#sidebar #bformat").input_value(), "bluray")
            # back to DVD: the default, so it is left out
            page.click("[data-lt=project]")
            page.click(".nav-item[data-view=disc]")
            page.select_option("select[data-k=format]", "dvd")
            self.until(page, lambda d: "format" not in d, "made for a DVD")
            page.locator("select[data-k=target]").wait_for()
            page.click("[data-lt=build]")
            self.assertEqual(page.locator("#sidebar #bformat").input_value(), "dvd")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
