"""The media cache in a folder of one's choosing (Preferences, or
ONCEMORE_CACHE): where each project's cache goes, everything that writes
to it (encodes, slideshows, joined clips, playback copies) following it,
`oncemore clean`, and the editor's settings API and Preferences."""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from oncemore import build, clips, settings, slideshow
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import run_cli
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


def until(page, expr, seconds=60):
    """Wait for a condition on the page (evaluated, not eval'd: the page's
    content security policy has no unsafe-eval)."""
    for _ in range(seconds * 10):
        if page.evaluate(f"() => !!({expr})"):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"timed out: {expr}")


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-settings-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = {"ONCEMORE_CONFIG": os.path.join(self.tmp, "config")}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        os.environ.pop("ONCEMORE_CACHE", None)
        self.addCleanup(self.env.stop)


class TestCacheDir(Temp):
    def test_where(self):
        a = os.path.join(self.tmp, "one", "My Disc")
        b = os.path.join(self.tmp, "two", "My Disc")
        self.assertEqual(settings.cache_dir(a), os.path.join(a, ".oncemore-cache"))
        cache = os.path.join(self.tmp, "cache")
        settings.set_cache_folder(cache)
        self.assertTrue(os.path.isdir(cache))
        self.assertEqual(settings.load()["cache_dir"], cache)
        ca, cb = settings.cache_dir(a), settings.cache_dir(b)
        # a folder per project, named after it; two of the same name do not share
        self.assertEqual(os.path.dirname(ca), cache)
        self.assertTrue(os.path.basename(ca).startswith("My_Disc-"))
        self.assertNotEqual(ca, cb)
        self.assertEqual(ca, settings.cache_dir(a))
        # ONCEMORE_CACHE first
        with mock.patch.dict(os.environ, {"ONCEMORE_CACHE": os.path.join(self.tmp, "env")}):
            self.assertEqual(os.path.dirname(settings.cache_dir(a)), os.path.join(self.tmp, "env"))
        settings.set_cache_folder(None)
        self.assertEqual(settings.cache_dir(a), os.path.join(a, ".oncemore-cache"))
        with self.assertRaises(ValueError):
            settings.set_cache_folder("relative/path")

    def test_users(self):
        cache = os.path.join(self.tmp, "cache")
        settings.set_cache_folder(cache)
        p = build_project(sample_project(), os.path.join(self.tmp, "p", "project.oncemore.json"),
                          check_files=False)
        mine = settings.cache_dir(p.base_dir)
        self.assertEqual(build.encode_cache_dir(p), os.path.join(mine, "encode"))
        show = slideshow.Slideshow([slideshow.Slide("/a.png", 2.0)])
        self.assertEqual(os.path.dirname(slideshow.output_path(p.base_dir, show, p.disc)),
                         os.path.join(mine, "slideshow"))
        t = p.titles[0]
        self.assertEqual(os.path.dirname(clips.preview_path(p.base_dir, t, p.disc)),
                         os.path.join(mine, "clips"))

    def test_fitted_slideshow_stays_in_the_cache(self):
        cache = os.path.join(self.tmp, "cache")
        settings.set_cache_folder(cache)
        d = sample_project()
        d["titles"].append({"id": "show", "slideshow": {
            "slides": [{"image": "a.png"}, {"image": "b.png"}], "audio": "m.mp3",
            "fit_to_audio": True}})
        p = build_project(d, os.path.join(self.tmp, "p", "project.oncemore.json"),
                          check_files=False)
        t = p.title("show")
        before = os.path.dirname(t.source)
        slideshow.apply(t, p.disc, lambda path: {"duration": 30.0})
        self.assertEqual(os.path.dirname(t.source), before)
        self.assertEqual(before, os.path.join(settings.cache_dir(p.base_dir), "slideshow"))

    def test_clean(self):
        rc, _, err = run_cli("init", "s", cwd=self.tmp)
        self.assertEqual(rc, 0, err)
        cache = os.path.join(self.tmp, "cache")
        env = {"ONCEMORE_CACHE": cache, "ONCEMORE_CONFIG": os.path.join(self.tmp, "config")}
        with mock.patch.dict(os.environ, env):
            mine = settings.cache_dir(os.path.join(self.tmp, "s"))
            os.makedirs(os.path.join(mine, "encode"))
            with open(os.path.join(mine, "encode", "x.mpg"), "wb") as f:
                f.write(b"x" * 100)
            rc, out, err = run_cli("clean", os.path.join(self.tmp, "s"))
        self.assertEqual(rc, 0, err)
        self.assertFalse(os.path.exists(mine))
        self.assertTrue(os.path.isdir(cache))           # (other projects' are left)


class TestApi(Temp):
    def test_settings(self):
        proj = os.path.join(self.tmp, "proj")
        os.makedirs(proj)
        s = GuiServer(proj)
        self.addCleanup(s.close)
        code, r = s.call("/api/settings")
        self.assertEqual((code, r["cache_dir"]), (200, None))
        self.assertEqual(r["project_cache"], os.path.join(proj, ".oncemore-cache"))
        cache = os.path.join(self.tmp, "cache")
        code, r = s.call("/api/settings", "PUT", {"cache_dir": cache})
        self.assertEqual((code, r["cache_dir"]), (200, cache))
        self.assertEqual(os.path.dirname(r["project_cache"]), cache)
        self.assertEqual(s.call("/api/settings", "PUT", {"cache_dir": "x/y"})[0], 400)
        code, r = s.call("/api/settings", "PUT", {"cache_dir": None})
        self.assertEqual(r["cache_dir"], None)
        with open(os.path.join(self.tmp, "config", "settings.json")) as f:
            self.assertNotIn("cache_dir", json.load(f))

    @unittest.skipUnless(PLAYWRIGHT, "needs playwright")
    def test_preferences(self):
        proj = os.path.join(self.tmp, "proj")
        os.makedirs(proj)
        s = GuiServer(proj)
        self.addCleanup(s.close)
        s.call("/api/new", "POST", {"sample": True})
        cache = os.path.join(self.tmp, "cache")
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{s.base}/#token={s.app.token}")
            page.locator(".nav-item[data-view=menu][data-id=main]").wait_for(timeout=120000)
            page.evaluate("window.oncemoreCommand('preferences')")
            page.locator("#pref-cache").wait_for()
            until(page, "document.querySelector('#pref-cache-hint').textContent.includes('.oncemore-cache')")
            page.fill("#pref-cache", cache)
            page.click("#pref-cache-set")
            until(page, f"document.querySelector('#pref-cache-hint').textContent.includes({json.dumps(cache)})")
            self.assertEqual(settings.load()["cache_dir"], cache)
            page.click("#pref-cache-def")
            until(page, "document.querySelector('#pref-cache').value === ''")
            self.assertNotIn("cache_dir", settings.load())
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
