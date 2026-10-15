"""The Mac app carries its own ffmpeg and ffprobe (DECISIONS §130): built from
pinned sources, put inside the app, used before any other, tested without
Homebrew, and released with its sources."""

import os
import re
import stat
import tempfile
import unittest
from unittest import mock

from oncemore import tools

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def fake_program(directory, name):
    path = os.path.join(directory, name)
    with open(path, "w") as f:
        f.write("#!/bin/sh\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return path


class TestFind(unittest.TestCase):
    def setUp(self):
        tools.reset_cache()
        self.addCleanup(tools.reset_cache)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_next_to_the_package_in_the_app(self):
        # Contents/Resources/app/oncemore/tools.py -> Contents/Resources/ffmpeg
        resources = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(tools.__file__))))
        self.assertEqual(tools._BUNDLED_DIR, os.path.join(resources, "ffmpeg"))

    def test_the_apps_own_comes_first(self):
        own = {n: fake_program(self.tmp.name, n) for n in ("ffmpeg", "ffprobe")}
        env = {k: v for k, v in os.environ.items()
               if k not in ("ONCEMORE_FFMPEG", "ONCEMORE_FFPROBE")}
        with mock.patch.object(tools, "_BUNDLED_DIR", self.tmp.name), \
                mock.patch.dict(os.environ, env, clear=True):
            for name in ("ffmpeg", "ffprobe"):
                self.assertEqual(tools.find(name), own[name])

    def test_a_chosen_program_still_wins(self):
        fake_program(self.tmp.name, "ffmpeg")
        chosen = fake_program(tempfile.mkdtemp(dir=self.tmp.name), "my-ffmpeg")
        with mock.patch.object(tools, "_BUNDLED_DIR", self.tmp.name), \
                mock.patch.dict(os.environ, {"ONCEMORE_FFMPEG": chosen}):
            self.assertEqual(tools.find("ffmpeg"), chosen)

    def test_without_one_the_others_are_used(self):
        with mock.patch.object(tools, "_BUNDLED_DIR", os.path.join(self.tmp.name, "none")):
            found = tools.find("ffmpeg")
        self.assertFalse(found and found.startswith(self.tmp.name))


class TestBuild(unittest.TestCase):
    def test_built_from_pinned_sources(self):
        script = read("macos", "build_ffmpeg.sh")
        sources = [l.split() for l in script.split('SOURCES="', 1)[1].split('"', 1)[0].splitlines()
                   if l.strip()]
        self.assertEqual([s[0].split("-")[0] for s in sources],
                         ["ffmpeg", "x264", "freetype", "harfbuzz"])
        for file, sha, url in sources:
            self.assertRegex(sha, r"^[0-9a-f]{64}$")
            self.assertTrue(url.startswith("https://"), url)
        self.assertIn('[ "$got" = "$sum" ]', script)

    def test_what_oncemore_needs_and_nothing_from_outside(self):
        script = read("macos", "build_ffmpeg.sh")
        for flag in ("--enable-gpl", "--enable-libx264", "--enable-libfreetype",
                     "--enable-libharfbuzz", "--disable-autodetect", "--disable-network",
                     "--enable-static", "--disable-shared"):
            self.assertIn(flag, script)
        self.assertIn("drawtext", script)
        self.assertIn("libx264", script)
        self.assertIn("otool -L", script)          # only macOS's libraries

    def test_inside_the_app(self):
        app = read("macos", "build_app.sh")
        self.assertIn('"$ROOT/macos/build_ffmpeg.sh"', app)
        self.assertIn('"$APP/Contents/Resources/ffmpeg/"', app)
        self.assertIn("licenses", app)
        self.assertNotIn("only need\n# Homebrew", app)

    def test_tested_without_homebrew(self):
        smoke = read("macos", "smoke_test.sh")
        self.assertIn('export PATH="/usr/bin:/bin:/usr/sbin:/sbin"', smoke)
        self.assertNotIn("/opt/homebrew", smoke)
        self.assertIn('"/Contents/Resources/ffmpeg/" + name', smoke)
        self.assertIn("--format bluray", smoke)
        for wf in ("ci.yml", "release.yml"):
            text = read(".github", "workflows", wf)
            self.assertNotIn("brew install ffmpeg-full\n", text.split("macos-app:")[-1]
                             if wf == "ci.yml" else text)
            self.assertIn("hashFiles('macos/build_ffmpeg.sh')", text)

    def test_released_with_its_sources(self):
        rel = read(".github", "workflows", "release.yml")
        self.assertIn("name: ffmpeg-sources", rel)
        self.assertIn("dist/ffmpeg-arm64/sources/*", rel)
        self.assertRegex(rel, r'gh release create "\$TAG" [^\n]*dist/sources/\*')


class TestDocuments(unittest.TestCase):
    def test_the_mac_app_needs_nothing_installed(self):
        en = read("README.md").split("## The Mac app", 1)[1].split("\n## ", 1)[0]
        ja = read("README.ja.md").split("## Mac アプリ", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("brew install", en)
        self.assertNotIn("brew install", ja)
        self.assertIn("build_ffmpeg.sh", en)
        self.assertIn("build_ffmpeg.sh", ja)
        self.assertIn("Mac app carries its own", read("oncemore", "gui", "static", "manual-en.md"))
        self.assertIn("Mac アプリには同梱", read("oncemore", "gui", "static", "manual-ja.md"))
        self.assertTrue(re.search(r"## 130\. ", read("docs", "DECISIONS.md")))


if __name__ == "__main__":
    unittest.main()
