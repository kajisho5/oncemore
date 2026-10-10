import copy
import filecmp
import json
import os
import unittest

from oncemore import project as P
from oncemore.errors import ProjectError
from oncemore.scaffold import sample_project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(data):
    return P.build_project(data, "/virtual/project.oncemore.json", check_files=False)


class TestParsers(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(P.parse_time(0), 0.0)
        self.assertEqual(P.parse_time(90.5), 90.5)
        self.assertEqual(P.parse_time("00:01:30"), 90.0)
        self.assertEqual(P.parse_time("1:02:03.5"), 3723.5)
        self.assertEqual(P.parse_time("01:30"), 90.0)
        self.assertEqual(P.parse_time("45"), 45.0)
        for bad in ("1:75", "abc", "1:2:3:4", -1, True, "-3"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                P.parse_time(bad)

    def test_format_time(self):
        self.assertEqual(P.format_time(3723.5), "1:02:03.500")
        self.assertEqual(P.format_time(0), "0:00:00.000")

    def test_parse_bitrate(self):
        self.assertEqual(P.parse_bitrate("192k"), 192_000)
        self.assertEqual(P.parse_bitrate("5.5M"), 5_500_000)
        self.assertEqual(P.parse_bitrate(448000), 448_000)
        with self.assertRaises(ValueError):
            P.parse_bitrate("fast")

    def test_normalize_label(self):
        self.assertEqual(P.normalize_label("SAMPLE_DISC"), "SAMPLE_DISC")
        self.assertEqual(P.normalize_label("my demo disc! 2"), "MY_DEMO_DISC_2")
        self.assertEqual(P.normalize_label("***"), "DVD_VIDEO")
        self.assertEqual(len(P.normalize_label("x" * 50)), 32)

    def test_parse_action(self):
        self.assertEqual(P.parse_action("menu:main"), ("menu", "main", None))
        self.assertEqual(P.parse_action("title:t1"), ("title", "t1", None))
        self.assertEqual(P.parse_action("chapter:t1:3"), ("chapter", "t1", 3))
        self.assertEqual(P.parse_action("stop"), ("stop", None, None))


class TestChapterPoints(unittest.TestCase):
    def check_plan(self, chapters_s, fps):
        gop, minimum = P.gop_limits(fps)
        keys, marks = P.chapter_points(chapters_s, fps)
        num, den = fps
        frames = [round(k * num / den) for k in keys]
        chapter_frames = [round(m * num / den - 0.5) for m in marks]
        for c in chapter_frames:
            if c:
                self.assertIn(c, frames)
        # simulate the encoder: I-frame every `gop` frames after each forced one
        end = max(chapter_frames) + 1
        iframes, last = [0], 0
        forced = set(frames)
        for f in range(1, end):
            if f in forced or f - last >= gop:
                iframes.append(f)
                last = f
        for c in chapter_frames:
            if not c:
                continue
            i = iframes.index(c)
            before = c - iframes[i - 1]
            seg_start = max([p for p in chapter_frames if p < c], default=0)
            # chapters closer than ~1 s cannot always satisfy the 0.4 s VOBU
            # minimum on both sides; everything else must
            if c - seg_start >= 2 * gop:
                self.assertGreaterEqual(before, minimum,
                                        f"GOP before chapter frame {c} is {before} frames")
        return keys, marks

    def test_ntsc_alignment(self):
        keys, marks = self.check_plan([0, 8, 16], (30000, 1001))
        self.assertAlmostEqual(marks[1], 240.5 * 1001 / 30000)
        self.assertIn(240 * 1001 / 30000, keys)

    def test_awkward_spacing(self):
        for chapters in ([0, 1.3], [0, 0.9], [0, 5.25, 5.9, 61.03], [0, 100.37, 200.01]):
            self.check_plan(chapters, (30000, 1001))
            self.check_plan(chapters, (25, 1))

    def test_keyframe_plan_examples(self):
        self.assertEqual(P.keyframe_plan([0, 240], (30000, 1001)), [228, 240])
        self.assertEqual(P.keyframe_plan([0, 40], (30000, 1001)), [14, 27, 40])
        self.assertEqual(P.keyframe_plan([0, 103], (25, 1)), [103])  # 103 % 15 = 13 >= 10


class TestProject(unittest.TestCase):
    def setUp(self):
        self.data = sample_project()

    def errors(self, data):
        with self.assertRaises(ProjectError) as cm:
            build(data)
        return " | ".join(f"{i['path']}: {i['message']}" for i in cm.exception.issues)

    def test_fade_in(self):
        d = copy.deepcopy(self.data)
        m = d["menus"][0]
        m["fade_in"] = 1.5
        menu = build(d).menus[0]
        self.assertEqual((menu.fade_in, menu.loop_point), (1.5, 1.5))   # repeats skip the fade
        m["loop_point"] = 3
        self.assertEqual(build(d).menus[0].loop_point, 3.0)              # a later loop point stays
        m["fade_in"] = 12
        with self.assertRaises(ProjectError) as cm:
            build(d)
        self.assertIn("a fade-in is at most 10 s", json.dumps(cm.exception.issues))

    def test_buttons_at_loop_needs_a_loop_point(self):
        d = copy.deepcopy(self.data)
        d["menus"][0]["buttons_at_loop"] = True
        with self.assertRaises(ProjectError) as cm:
            build(d)
        self.assertIn("buttons_at_loop", json.dumps(cm.exception.issues))
        d["menus"][0]["loop_point"] = 2
        self.assertTrue(build(d).menus[0].buttons_at_loop)

    def test_hidden_elements_are_left_out(self):
        d = copy.deepcopy(self.data)
        m = d["menus"][0]
        ids = [b["id"] for b in m["buttons"]]
        m["buttons"][1]["hidden"] = True
        m["buttons"][0]["nav"] = {"down": ids[1]}
        m["default_button"] = ids[1]
        m.setdefault("texts", []).append({"text": "GONE", "x": 10, "y": 10, "hidden": True})
        m.setdefault("shapes", []).append({"x": 0, "y": 0, "w": 10, "h": 10, "hidden": True})
        m["images"] = [{"file": "logo.png", "x": 5, "y": 6, "w": 70, "h": 30, "opacity": 0.5},
                       {"file": "gone.png", "x": 0, "y": 0, "w": 10, "h": 10, "hidden": True}]
        menu = build(d).menus[0]
        self.assertEqual([b.id for b in menu.buttons], [ids[0]] + ids[2:])
        self.assertEqual(menu.buttons[0].nav, {})              # its route went with it
        self.assertIsNone(menu.default_button)
        self.assertNotIn("GONE", [t.text for t in menu.texts])
        self.assertNotIn((0, 0, 10, 10), [(s.x, s.y, s.w, s.h) for s in menu.shapes])
        self.assertEqual([(os.path.basename(p.file), p.x, p.y, p.w, p.h, p.opacity)
                          for p in menu.images], [("logo.png", 5, 6, 70, 30, 0.5)])
        for b in m["buttons"]:
            b["hidden"] = True
        with self.assertRaises(ProjectError) as cm:
            build(d)
        self.assertIn("every button is hidden", str(cm.exception.issues))

    def test_sample_project(self):
        p = build(self.data)
        self.assertEqual(p.disc.label, "SAMPLE_DISC")
        self.assertEqual((p.disc.width, p.disc.height), (720, 480))
        self.assertEqual([m.id for m in p.menus], ["main", "chapters"])
        self.assertEqual([m.number for m in p.menus], [1, 2])
        self.assertEqual(p.titles[0].chapters, [0.0, 8.0, 16.0])
        self.assertEqual(p.titles[0].end_action, "menu:main")
        self.assertEqual(p.menu("main").buttons[0].action, "playall")
        self.assertTrue(p.uses_playall)
        self.assertEqual(p.playall_next(p.titles[0]), p.titles[1])
        self.assertIsNone(p.playall_next(p.titles[1]))
        self.assertEqual(p.titles[1].end_action, "menu:main")
        ch = p.menu("chapters")
        self.assertTrue(ch.generated)
        self.assertEqual([b.action for b in ch.buttons],
                         ["chapter:t1:1", "chapter:t1:2", "chapter:t1:3", "menu:main"])
        self.assertEqual(ch.buttons[1].thumb.title_id, "t1")
        self.assertAlmostEqual(ch.buttons[1].thumb.time, 9.0)
        self.assertTrue(p.titles[0].source.endswith(os.path.join("media", "sample_a.mp4")))

    def test_example_matches_init_template(self):
        with open(os.path.join(ROOT, "examples", "basic", "project.oncemore.json")) as f:
            self.assertEqual(json.load(f), sample_project())

    def test_schema_copy_in_sync(self):
        self.assertTrue(filecmp.cmp(os.path.join(ROOT, "schema", "project.schema.json"),
                                    os.path.join(ROOT, "oncemore", "project.schema.json"),
                                    shallow=False),
                        "schema/project.schema.json must be a copy of oncemore/project.schema.json")

    def test_defaults(self):
        d = {"version": 1, "disc": {"label": "x", "standard": "PAL", "aspect": "4:3"},
             "titles": [{"id": "a", "source": "a.mp4"}]}
        p = build(d)
        self.assertEqual(p.disc.first_play, "title:a")
        self.assertEqual(p.disc.target, "DVD5")
        self.assertEqual(p.titles[0].chapters, [0.0])
        self.assertEqual(p.titles[0].end_action, "stop")
        self.assertEqual((p.disc.height, p.disc.fps), (576, (25, 1)))

    def test_first_play_menu_becomes_root(self):
        self.data["menus"].append({"id": "intro", "buttons": [
            {"id": "go", "label": "GO", "x": 10, "y": 10, "action": "menu:main"}]})
        self.data["disc"]["first_play"] = "menu:intro"
        p = build(self.data)
        self.assertEqual(p.menus[0].id, "intro")
        self.assertEqual(p.menu("main").number, 2)

    def test_zero_added_to_chapters(self):
        self.data["titles"][1]["chapters"] = ["0:05", 10]
        self.assertEqual(build(self.data).titles[1].chapters, [0.0, 5.0, 10.0])

    def test_schema_errors(self):
        d = copy.deepcopy(self.data)
        d["disc"]["standard"] = "SECAM"
        d["titles"][0]["bogus"] = 1
        d["menus"][0]["buttons"][0]["action"] = "play:t1"
        msg = self.errors(d)
        self.assertIn("disc.standard", msg)
        self.assertIn("titles[0].bogus: unknown property", msg)
        self.assertIn("menus[0].buttons[0].action", msg)

    def test_reference_errors(self):
        d = copy.deepcopy(self.data)
        d["menus"][0]["buttons"][0]["action"] = "menu:nope"
        d["menus"][0]["buttons"][1]["action"] = "chapter:t1:9"
        d["titles"][1]["end_action"] = "title:zz"
        d["menus"][0]["buttons"][2]["nav"] = {"up": "ghost"}
        msg = self.errors(d)
        self.assertIn("no menu with id 'nope'", msg)
        self.assertIn("has only 3 chapters", msg)
        self.assertIn("no title with id 'zz'", msg)
        self.assertIn("no button 'ghost'", msg)

    def test_duplicate_ids(self):
        d = copy.deepcopy(self.data)
        d["titles"][1]["id"] = "t1"
        self.assertIn("duplicate id 't1'", self.errors(d))

    def test_titlesets_by_aspect_and_codec(self):
        d = copy.deepcopy(self.data)
        d["titles"].append({"id": "t3", "source": "c.mp4", "aspect": "4:3"})
        d["titles"].append({"id": "t4", "source": "d.mp4", "audio": {"codec": "lpcm"}})
        d["titles"].append({"id": "t5", "source": "e.mp4"})
        p = build(d)
        got = [(t.id, t.titleset, t.number, t.global_number, t.aspect) for t in p.titles]
        self.assertEqual(got, [("t1", 1, 1, 1, "16:9"), ("t2", 1, 2, 2, "16:9"),
                               ("t3", 2, 1, 4, "4:3"), ("t4", 3, 1, 5, "16:9"),
                               ("t5", 1, 3, 3, "16:9")])
        self.assertEqual(p.titleset_count, 3)
        self.assertEqual(p.disc_for(p.title("t3")).aspect, "4:3")
        self.assertEqual(p.disc.aspect, "16:9")

    def test_chapter_order_and_range(self):
        d = copy.deepcopy(self.data)
        d["titles"][0]["chapters"] = [0, 20, 10]
        self.assertIn("strictly increasing", self.errors(d))
        d = copy.deepcopy(self.data)
        d["menus"][0]["buttons"][0]["y"] = 500
        self.assertIn("must be < 480", self.errors(d))

    def test_chapter_menu_pagination(self):
        d = copy.deepcopy(self.data)
        d["titles"][0]["chapters"] = list(range(0, 80, 10))  # 8 chapters
        p = build(d)
        pages = [m for m in p.menus if m.generated]
        self.assertEqual([m.id for m in pages], ["chapters", "chapters_2"])
        self.assertEqual([b.id for b in pages[0].buttons],
                         ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "back", "next"])
        self.assertEqual([b.id for b in pages[1].buttons], ["ch7", "ch8", "back", "prev"])
        self.assertEqual(pages[0].buttons[-1].action, "menu:chapters_2")
        self.assertEqual(pages[1].buttons[-1].action, "menu:chapters")
        self.assertIn("(1/2)", pages[0].texts[0].text)

    def test_pal_chapter_menu_layout_fits(self):
        d = copy.deepcopy(self.data)
        d["disc"]["standard"] = "PAL"
        p = build(d)
        for b in p.menu("chapters").buttons:
            self.assertLess(b.y + b.size, 576)
            if b.thumb:
                self.assertEqual((b.thumb.w, b.thumb.h), (180, 144))

    def test_missing_files_reported(self):
        with self.assertRaises(ProjectError) as cm:
            P.build_project(self.data, "/nonexistent/dir/project.oncemore.json")
        paths = [i["path"] for i in cm.exception.issues]
        self.assertIn("titles[0].source", paths)
        self.assertIn("menus[0].background", paths)

    def test_audio_tracks_and_subtitles(self):
        d = copy.deepcopy(self.data)
        d["titles"][0]["audio_tracks"] = [{"lang": "ja"}, {"source": "c.wav", "stream": 1,
                                                           "lang": "en"}]
        d["titles"][0]["subtitles"] = [{"file": "ja.srt", "lang": "ja", "default": True},
                                       {"file": "en.srt", "lang": "en"}]
        d["titles"][1]["subtitles"] = [{"file": "b.srt"}]
        d["menus"][0]["buttons"].append({"id": "a2", "label": "A2", "x": 400, "y": 220,
                                         "action": "audio:2"})
        d["menus"][0]["buttons"].append({"id": "so", "label": "OFF", "x": 400, "y": 280,
                                         "action": "subtitle:off"})
        p = build(d)
        t = p.titles[0]
        self.assertEqual([(os.path.basename(a.source), a.stream, a.lang) for a in t.audio_tracks],
                         [("sample_a.mp4", 0, "ja"), ("c.wav", 1, "en")])
        self.assertEqual(t.audio_bps, 2 * 192_000)
        self.assertEqual(p.titles[1].audio_bps, 192_000)
        self.assertEqual(p.audio_langs, ["ja", "en"])
        self.assertEqual(p.subtitle_langs, ["ja", "en"])   # title 2's unnamed stream 1 is ja
        self.assertTrue(t.subtitles[0].default)
        self.assertEqual(P.parse_action("audio:2"), ("audio", None, 2))
        self.assertEqual(P.parse_action("subtitle:off"), ("subtitle", None, 0))

    def test_stream_errors(self):
        d = copy.deepcopy(self.data)
        d["titles"][0]["subtitles"] = [{"file": "a.srt", "lang": "ja", "default": True},
                                       {"file": "b.srt", "lang": "en", "default": True}]
        d["titles"][1]["subtitles"] = [{"file": "c.srt", "lang": "fr"}]
        d["titles"][1]["audio_tracks"] = [{"lang": "en"}]
        d["titles"][0]["audio"] = {"codec": "lpcm"}
        d["titles"][1]["audio"] = {"codec": "lpcm"}
        d["titles"][0]["audio_tracks"] = [{"lang": "ja"}] * 6
        d["menus"][0]["buttons"][0]["action"] = "subtitle:3"
        msg = self.errors(d)
        self.assertIn("only one subtitle track can be the default", msg)
        self.assertIn("subtitle stream 1 is 'ja' in another title", msg)
        self.assertIn("audio stream 1 is 'ja' in another title", msg)
        self.assertIn("6 lpcm tracks need 9.22 Mbit/s", msg)
        self.assertIn("no subtitle stream 3", msg)

    def test_surround_and_playall_validation(self):
        d = copy.deepcopy(self.data)
        d["titles"][1]["audio"] = {"codec": "ac3", "channels": 4}
        self.assertIn("titles[1].audio.channels: must be one of 2, 6", self.errors(d))
        d["titles"][1]["audio"] = {"codec": "lpcm", "channels": 6}
        self.assertIn("5.1 needs AC-3", self.errors(d))
        d = copy.deepcopy(self.data)
        d["disc"]["first_play"] = "playall"
        d["titles"][1]["audio"] = {"codec": "ac3", "channels": 6, "bitrate": "192k"}
        p = build(d)
        self.assertEqual(p.disc.first_play, "playall")
        self.assertTrue(any("low for 5.1" in w for w in p.warnings))

    def test_image_buttons(self):
        d = copy.deepcopy(self.data)
        d["menus"][0]["buttons"].append({"id": "ib", "image": "media/play.png", "x": 400,
                                         "y": 300, "width": 90, "highlight": "shape",
                                         "action": "title:t2"})
        b = build(d).menu("main").buttons[-1]
        self.assertEqual((b.label, b.width, b.highlight), ("", 90, "shape"))
        self.assertTrue(b.image.endswith(os.path.join("media", "play.png")))
        del d["menus"][0]["buttons"][-1]["image"]
        self.assertIn("missing required property 'label'", self.errors(d))
        d["menus"][0]["buttons"][-1].update({"image": "x.png", "highlight": "glow"})
        self.assertIn("must be one of 'frame', 'shape'", self.errors(d))

    def test_subtitle_style_defaults(self):
        self.assertEqual(build(self.data).disc.subtitle_style["size"], 30)
        d = copy.deepcopy(self.data)
        d["disc"]["standard"] = "PAL"
        d["disc"]["subtitle_style"] = {"color": "#FFFF00"}
        st = build(d).disc.subtitle_style
        self.assertEqual((st["size"], st["color"], st["margin"]), (36, "#FFFF00", 43))

    def test_invalid_json_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "project.oncemore.json")
            with open(path, "w") as f:
                f.write("{ not json")
            with self.assertRaises(ProjectError) as cm:
                P.load_project(d)
            self.assertIn("invalid JSON", cm.exception.message)


if __name__ == "__main__":
    unittest.main()
