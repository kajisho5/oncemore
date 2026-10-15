"""The findings of the October 2026 review (DECISIONS §131), each pinned by a
test that fails without its fix."""

import json
import os
import re
import tempfile
import types
import unittest
from unittest import mock

from oncemore import bluray, encode, project as project_mod, psdmenu, schemalite, simulate
from oncemore import usertemplates
from oncemore.errors import ProjectError
from oncemore.project import PROJECT_FILENAME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DVD5 = 4_700_372_992
BD25 = bluray.CAPACITY["BD25"]


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestDvdPlan(unittest.TestCase):
    def test_a_copied_picture_keeps_its_own_rate(self):
        # 9 Mbit/s copied from the source is not the 8 Mbit/s encoder cap
        plan = encode.plan_bitrate([(3600, 192_000, 9_000_000, True), (1800, 192_000)], DVD5 * 2)
        self.assertEqual(plan["per_title"][0], 9_000_000)
        encoded = encode.plan_bitrate([(3600, 192_000, 9_000_000), (1800, 192_000)], DVD5 * 2)
        self.assertLess(encoded["per_title"][0], 9_000_000)        # an encoded rate is capped

    def test_rom_files_and_motion_menus_are_on_the_disc(self):
        base = encode.plan_bitrate([(7200, 192_000)], DVD5, 60)
        rom = encode.plan_bitrate([(7200, 192_000)], DVD5, 60, other_bytes=500_000_000)
        motion = encode.plan_bitrate([(7200, 192_000)], DVD5, 60, motion_seconds=60)
        self.assertLess(rom["video_bps"], base["video_bps"])
        self.assertEqual(rom["budget"]["other"] - base["budget"]["other"], 500_000_000)
        self.assertLess(motion["video_bps"], base["video_bps"])
        self.assertGreater(motion["budget"]["menus"], base["budget"]["menus"])

    def test_the_hint_names_a_bigger_disc_only_when_there_is_one(self):
        with self.assertRaises(ProjectError) as e:
            encode.plan_bitrate([(20 * 3600, 192_000)], DVD5 * 2, bigger=None)
        self.assertNotIn("DVD9", e.exception.message)
        with self.assertRaises(ProjectError) as e:
            encode.plan_bitrate([(20 * 3600, 192_000)], DVD5, bigger="DVD9")
        self.assertIn("Use DVD9", e.exception.message)

    def test_copied_titles_that_fill_the_disc_say_so(self):
        with self.assertRaises(ProjectError) as e:
            encode.plan_bitrate([(5 * 3600, 192_000, 9_000_000, True), (600, 192_000)], DVD5)
        self.assertIn("already take the whole disc", e.exception.message)
        self.assertNotIn("0.00 Mbit/s", e.exception.message)


class TestBlurayPlan(unittest.TestCase):
    def test_menus_and_rom_files_are_budgeted(self):
        base = bluray.plan([(3600, 640_000)], BD25)
        menus = bluray.plan([(3600, 640_000)], BD25, menu_seconds=600, other_bytes=1 << 30)
        self.assertLess(menus["max_bps"], base["max_bps"] + 1)
        self.assertGreater(menus["budget"]["menus"], 0)
        self.assertEqual(menus["budget"]["other"], 1 << 30)

    def test_copied_titles_alone_too_big(self):
        with self.assertRaises(ProjectError) as e:
            bluray.plan([(7200, 192_000, 40_000_000)], BD25)
        self.assertIn("already take the whole disc", e.exception.message)
        self.assertNotIn("0.0 min", e.exception.message)

    def test_a_folder_has_no_capacity(self):
        plan = bluray.plan([(20 * 3600, 4_608_000)], float("inf"))
        self.assertEqual(plan["max_bps"], bluray.MAX_VIDEO_BPS)
        json.dumps(plan["budget"], allow_nan=False)            # (finite numbers for the page)

    def test_the_bd50_hint_only_on_bd25(self):
        with self.assertRaises(ProjectError) as e:
            bluray.plan([(40 * 3600, 640_000)], bluray.CAPACITY["BD50"], bigger=None)
        self.assertNotIn("BD50", e.exception.message)


class TestEncoding(unittest.TestCase):
    def test_a_bare_streams_rate_is_its_size_over_its_length(self):
        with tempfile.NamedTemporaryFile(suffix=".h264") as f:
            f.write(b"\0" * 3_000_000)
            f.flush()
            info = {"path": f.name, "duration": 1.0}
            self.assertEqual(encode.source_video_bps(info, bd=True), 24_000_000)
        self.assertEqual(encode.source_video_bps({}, bd=True), 40_000_000)
        self.assertEqual(encode.source_video_bps({}), encode.DVD_MAX_VIDEO_BPS)

    def test_720p_keeps_the_fields(self):
        disc = types.SimpleNamespace(standard="PAL", fps=(25, 1), bluray_video="720",
                                     aspect="16:9", width=1920, height=1080)
        hd = bluray.hd_frame(disc)
        vf = encode.fit_filter({"width": 720, "height": 576, "interlaced": True, "sar": 1},
                               hd, mode="fields")
        self.assertTrue(vf.startswith("bwdif=mode=send_field,fps=50/1"), vf)
        self.assertIn('"fields" if bd_fps(disc.fps, disc) != disc.fps', read("oncemore", "bluray.py"))

    def test_the_patched_picture_is_the_input_after_all_the_others(self):
        # a sound-only title with captions: the still is an input too
        calls = []
        title = types.SimpleNamespace(id="t", captions=None, captions_offset=0)
        inputs = ["-i", "music.wav", "-loop", "1", "-i", "still.png"]
        with mock.patch.object(encode, "run_ffmpeg", lambda args, *a, **k: calls.append(args)), \
                mock.patch.object(encode.os, "remove"):
            encode._pulldown_mux(title, inputs, ["-map", "1:v:0"], [], [], 10.0, "out.mpg",
                                 "/tmp", None, pulldown_flags=False)
        mux = calls[-1]
        self.assertEqual(mux[mux.index("-c:v") - 1], "2:v:0")


class TestPassthroughWithoutSound(unittest.TestCase):
    def test_says_there_is_nothing_to_copy(self):
        self.assertIn('"message": f"{os.path.basename(tr.source)} has no audio "',
                      read("oncemore", "build.py"))


class TestInterfaces(unittest.TestCase):
    def test_simulator_keys_are_checked(self):
        sim = simulate.Simulator.__new__(simulate.Simulator)
        geoms = [{"id": "play"}, {"id": "scenes"}]
        self.assertEqual(sim._pick(geoms, "scenes"), 2)
        self.assertEqual(sim._pick(geoms, "1"), 1)
        for bad in ("foo", "9", "0"):
            with self.assertRaises(simulate.SimError):
                sim._pick(geoms, bad)

    def test_chapter_label_format(self):
        lab = project_mod._chapter_label
        self.assertEqual(lab("Chapter {n}", 3), "Chapter 3")
        self.assertEqual(lab("{n:02d}", 3), "03")
        self.assertEqual(lab("Chapter {}", 3), "Chapter {}")
        self.assertEqual(lab("{foo} {n}", 3), "{foo} 3")

    def test_schema_patterns_end_at_the_end(self):
        self.assertTrue(schemalite.validate("t1\n", {"type": "string", "pattern": "^[a-z0-9]+$"}))
        self.assertFalse(schemalite.validate("t1", {"type": "string", "pattern": "^[a-z0-9]+$"}))

    def test_true_is_not_one(self):
        self.assertTrue(schemalite.validate(True, {"const": 1}))
        self.assertTrue(schemalite.validate(True, {"enum": [2, 6]}))
        self.assertFalse(schemalite.validate(6, {"enum": [2, 6]}))

    def test_mcp_arguments_are_checked_against_the_tool(self):
        from oncemore import mcp
        server = mcp.Server()
        out = server.call({"name": "import_psd", "arguments": {"folder": "/tmp"}})
        self.assertTrue(out["isError"])
        self.assertIn("psd", out["content"][0]["text"])
        out = server.call({"name": "simulate", "arguments": {"folder": "/tmp", "keys": "up"}})
        self.assertTrue(out["isError"])
        self.assertIn("array", out["content"][0]["text"])

    def test_template_links_to_a_menus_button_and_scripts(self):
        targets = usertemplates._targets({"menus": [{"id": "main"}], "scripts": {"go": "x"}})
        self.assertTrue(usertemplates._link_ok("menu:main:play", targets))
        self.assertTrue(usertemplates._link_ok("commands:go", targets))
        self.assertFalse(usertemplates._link_ok("commands:gone", targets))
        self.assertFalse(usertemplates._link_ok("menu:other", targets))

    def test_psd_names_give_only_valid_actions(self):
        project = {"titles": [{"id": "t1"}], "menus": []}
        for name in ("Chapter 0", "Audio 0", "Audio 9", "Subtitle 0", "Subtitle 40"):
            action, _ = psdmenu.guess_action(name, project)
            self.assertIsNone(action, name)
        self.assertEqual(psdmenu.guess_action("Subtitle 12", project)[0], "subtitle:12")
        self.assertEqual(psdmenu.guess_action("Chapter 3", project)[0], "chapter:t1:3")


class TestServer(unittest.TestCase):
    def setUp(self):
        from .test_gui import GuiServer
        # (real paths: macOS's /var is /private/var, and the cache folder's name
        # comes from the project's path)
        self.dir = os.path.realpath(tempfile.mkdtemp())
        self.cache = os.path.realpath(tempfile.mkdtemp())
        with open(os.path.join(self.dir, PROJECT_FILENAME), "w") as f:
            json.dump({"version": 1, "disc": {"label": "T", "standard": "NTSC",
                                              "aspect": "16:9", "target": "DVD5"},
                       "titles": [], "menus": []}, f)
        env = mock.patch.dict(os.environ, {"ONCEMORE_CACHE": self.cache})
        env.start()
        self.addCleanup(env.stop)
        self.srv = GuiServer(self.dir)
        self.addCleanup(self.srv.close)

    def test_files_in_the_media_cache_are_served(self):
        from oncemore import settings
        cache = settings.cache_dir(self.dir)
        os.makedirs(cache, exist_ok=True)
        with open(os.path.join(cache, "x.srt"), "w") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
        rel = os.path.relpath(os.path.join(cache, "x.srt"), self.dir)
        status, _ = self.srv.call("/api/file?" + __import__("urllib.parse").parse.urlencode({"path": rel}))
        self.assertEqual(status, 200)

    def test_a_body_that_is_not_an_object_is_answered(self):
        status, body = self.srv.call("/api/sim", "POST", raw=b"[]",
                                     headers={"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertIn("JSON object", body["error"])

    def test_a_cue_with_no_time_is_answered(self):
        status, body = self.srv.call("/api/subtitles?path=media/s.srt", "PUT",
                                     body={"cues": [{"start": None, "end": 1, "text": "a"}]})
        self.assertEqual(status, 400)
        self.assertIn("cue 1", body["error"])
        status, body = self.srv.call("/api/subtitles?path=media/s.srt", "PUT",
                                     body={"cues": [{"start": 2, "end": 1, "text": "a"}]})
        self.assertEqual((status, body["cues"]), (200, 0))     # (dropped, as before)


class TestPage(unittest.TestCase):
    def setUp(self):
        self.js = read("oncemore", "gui", "static", "app.js")

    def test_no_string_is_defined_twice(self):
        i, j = self.js.index("  en: {"), self.js.index("  ja: {")
        k = self.js.index("\n  },\n", j)
        for table in (self.js[i:j], self.js[j:k]):
            keys = re.findall(r'(?<![\w.])([a-z_][a-z0-9_]*): (?:"|`)', table)
            self.assertEqual(sorted({x for x in keys if keys.count(x) > 1}), [])

    def test_state_that_belongs_to_a_project_or_a_title(self):
        js = self.js
        self.assertIn("S.clipJoins = {}; S.simMenus = {}", js)        # project switched
        self.assertIn('S.titleSeek = null;      // (set again below', js)
        self.assertIn("function renameState(kind, id, nid)", js)
        self.assertEqual(js.count("renameState("), 4)                  # (definition + 3 renames)
        self.assertIn('$("#sim-screen")?.focus()', js)
        self.assertIn("if (S.renderPending === a) return;", js)

    def test_failures_are_shown(self):
        js = self.js
        self.assertEqual(len(re.findall(r'try \{ r = await api\("/api/template"', js)), 2)
        self.assertIn('try { r = await api("/api/new"', js)
        self.assertIn('alert(t("cue_bad_time", { n: bad + 1 }))', js)

    def test_the_page_frame_is_translated(self):
        html = read("oncemore", "gui", "static", "index.html")
        self.assertNotRegex(html, r'(?<![-\w])title="[^"]+"(?![^>]*data-i18n-title)')
        self.assertIn('data-i18n-title="drag_resize"', html)
        self.assertIn('querySelectorAll("[data-i18n-title]")', self.js)

    def test_no_names_of_the_classic_apps(self):
        for path in ("oncemore/gui/static/app.js", "oncemore/author.py", "oncemore/psd.py"):
            self.assertEqual(re.findall(r"scenarist|encore|adobe", read(path), re.I), [], path)
        self.assertEqual([f for f in os.listdir(os.path.join(ROOT, "tests"))
                          if re.search("encore|adobe", f, re.I)], [])


class TestDocuments(unittest.TestCase):
    def test_title_buttons_on_a_blu_ray_stop_the_build(self):
        self.assertIn("a Blu-ray build stops with a\n  message", read("README.md"))
        self.assertIn("Blu-ray のビルドはメッセージを出して止まります", read("README.ja.md"))
        self.assertIn("Blu-ray build stops on them", read("oncemore", "gui", "static", "manual-en.md"))
        self.assertIn("Blu-ray のビルドはこれがあると止まり", read("oncemore", "gui", "static", "manual-ja.md"))

    def test_the_buttons_row_is_in_the_menus_table(self):
        for name in ("README.md", "README.ja.md"):
            text = read(name)
            row = text.index("| `buttons[]` |")
            self.assertEqual(text[text.rindex("\n", 0, row - 1) + 1], "|", name)

    def test_folders_and_formats(self):
        for name in ("README.md", "README.ja.md"):
            text = read(name)
            for var in ("ONCEMORE_CACHE", "ONCEMORE_TEMPLATES", "ONCEMORE_STYLES", "ONCEMORE_CONFIG"):
                self.assertIn(var, text, name)
            self.assertIn("`xorriso`", text)
            self.assertNotIn("apt-get install ffmpeg genisoimage", text)
            self.assertIn("WebVTT", text)


class TestAutomation(unittest.TestCase):
    def test_no_grep_q_at_the_end_of_a_pipe(self):
        for path in ("macos/build_app.sh", "macos/build_ffmpeg.sh", ".claude/hooks/session-start.sh"):
            self.assertNotRegex(read(path), r"\|\s*grep -q", path)

    def test_the_bundled_python_is_always_checked(self):
        app = read("macos", "build_app.sh")
        self.assertNotIn("checksum not verified", app)
        self.assertNotIn('-p "SHA256SUMS" --clobber || true', app)

    def test_a_release_tag_and_its_commit(self):
        rel = read(".github", "workflows", "release.yml")
        self.assertIn('[ "$at" = "$GITHUB_SHA" ]', rel)
        self.assertIn("pyproject.toml has", rel)

    def test_a_library_branch_without_its_pull_request(self):
        wf = read(".github", "workflows", "library-updates.yml")
        self.assertIn('gh pr list --head "$branch" --state all', wf)

    def test_the_app_keeps_the_url_and_a_bounded_log(self):
        swift = read("macos", "Oncemore", "main.swift")
        self.assertIn("String(decoding: data, as: UTF8.self)", swift)
        self.assertIn("log = String(log.suffix(32768))", swift)

    def test_vendor_refuses_what_it_would_not_copy(self):
        self.assertIn("vendor.py copies only the top-level .py files", read("tools", "vendor.py"))


if __name__ == "__main__":
    unittest.main()
