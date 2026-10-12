"""Navigation scripts in the app: the disc's Properties add, check, rename
and delete them; a link chooses one; Preview runs it and shows the
variables."""

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

TWICE = "$n += 1; if ($n >= 2) { $n = 0; play title:t2; } else play menu:main;"


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestScriptsEditor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-script-gui-")
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
            d = self.project()
            if test(d):
                return d
            page.wait_for_timeout(100)
        raise AssertionError(f"{what}: {self.project().get('scripts')}")

    def test_check_endpoint(self):
        status, r = self.s.call("/api/script_check", "POST", {"text": TWICE})
        self.assertEqual((status, r), (200, {"ok": True, "variables": ["n"],
                                             "actions": ["title:t2", "menu:main"]}))
        status, r = self.s.call("/api/script_check", "POST", {"text": "jump title 1;"})
        self.assertFalse(r["ok"])
        self.assertIn("use play <action>", r["error"])

    def test_editor(self):
        with sync_playwright() as p:
            browser, page, errors = self.open(p, ".nav-item[data-view=disc]")
            page.click("#add-script")                            # script1: to the first menu
            self.until(page, lambda d: d.get("scripts") == {"script1": "play menu:main;"}, "added")
            row = page.locator("[data-script=script1]")
            row.locator("[data-scheck]", has_text="goes to: menu:main").wait_for()
            ta = row.locator("[data-stext]")
            ta.fill("$n += 1;")                                  # (it does not go anywhere)
            row.locator("[data-scheck].warn", has_text="must end with play").wait_for()
            ta.fill(TWICE)
            row.locator("[data-scheck]", has_text="Variables: $n · goes to: title:t2, menu:main").wait_for()
            ta.blur()
            self.until(page, lambda d: d["scripts"]["script1"] == TWICE, "saved")
            # a button takes it as its link; renaming the script keeps the link
            d = self.project()
            d["menus"][0]["buttons"][2]["action"] = "commands:script1"
            with open(self.path, "w") as f:
                json.dump(d, f)
            page.reload()
            page.click(".nav-item[data-view=disc]", timeout=120000)
            page.locator("[data-script=script1] [data-sid]").fill("twice")
            page.locator("[data-script=script1] [data-sid]").press("Enter")
            d = self.until(page, lambda d: "twice" in d.get("scripts", {}), "renamed")
            self.assertEqual(d["menus"][0]["buttons"][2]["action"], "commands:twice")
            # the button's Properties offer it; Preview runs it
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator("#stage").focus()
            page.keyboard.press("Shift+Space")
            page.locator("#sim-status", has_text="main").wait_for(timeout=120000)
            page.locator("#sim-screen").press("3")               # its button: back to the menu
            page.locator("#sim-status", has_text="Variables: $n = 1").wait_for(timeout=120000)
            page.locator("#sim-screen").press("3")               # the second press: title B
            page.locator("#sim-status", has_text="t2").wait_for(timeout=120000)
            browser.close()
        self.assertEqual(errors, [])

    def test_menu_renamed_in_scripts(self):
        d = self.project()
        d["scripts"] = {"twice": TWICE, "dice": "$r = random(2); if ($r == 1) play menu:main:b; "
                                                "else play menu:mainly;"}
        with open(self.path, "w") as f:
            json.dump(d, f)
        with sync_playwright() as p:
            browser, page, errors = self.open(p, ".nav-item[data-view=menu][data-id=main]")
            page.locator("#menu-id").fill("home")
            page.locator("#menu-id").press("Enter")
            d = self.until(page, lambda d: d["menus"][0]["id"] == "home", "renamed")
            self.assertEqual(d["scripts"]["twice"], TWICE.replace("menu:main", "menu:home"))
            self.assertIn("play menu:home:b;", d["scripts"]["dice"])
            self.assertIn("play menu:mainly;", d["scripts"]["dice"])      # (another id)
            browser.close()
        self.assertEqual(errors, [])

    def test_link_choices(self):
        d = self.project()
        d["scripts"] = {"twice": TWICE}
        with open(self.path, "w") as f:
            json.dump(d, f)
        with sync_playwright() as p:
            browser, page, errors = self.open(p, ".nav-item[data-view=title][data-id=t1]")
            # a title's end can run it; the disc's first play cannot
            page.locator("select[data-k=end_action] option[value='commands:twice']").wait_for(
                state="attached")
            page.click(".nav-item[data-view=disc]")
            page.locator("#scripts").wait_for()
            self.assertEqual(page.locator("select[data-k=first_play] option[value='commands:twice']")
                             .count(), 0)
            page.locator("[data-script=twice] [data-del-script]").click()
            self.until(page, lambda d: "scripts" not in d, "deleted")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
