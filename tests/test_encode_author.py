import unittest

from oncemore import author, encode
from oncemore.errors import ProjectError
from oncemore.project import CAPACITY, build_project
from oncemore.scaffold import sample_project


class TestBitrate(unittest.TestCase):
    def test_short_content_is_capped(self):
        plan = encode.plan_bitrate([(36, 192_000)], CAPACITY["DVD5"], 10)
        self.assertEqual(plan["video_bps"], encode.MAX_VIDEO_BPS)
        self.assertLess(plan["estimated_bytes"], CAPACITY["DVD5"])

    def test_two_hours_fill_dvd5(self):
        plan = encode.plan_bitrate([(7200, 192_000)], CAPACITY["DVD5"], 10)
        self.assertGreater(plan["video_bps"], 4_000_000)
        self.assertLess(plan["video_bps"], 4_800_000)
        self.assertLessEqual(plan["estimated_bytes"], CAPACITY["DVD5"])
        self.assertGreater(plan["estimated_bytes"], CAPACITY["DVD5"] * 0.9)

    def test_dvd9_doubles_room(self):
        a = encode.plan_bitrate([(3 * 3600, 192_000)], CAPACITY["DVD5"])["video_bps"]
        b = encode.plan_bitrate([(3 * 3600, 192_000)], CAPACITY["DVD9"])["video_bps"]
        self.assertGreater(b, a * 1.7)

    def test_lpcm_respects_total_limit(self):
        plan = encode.plan_bitrate([(60, 1_536_000)], CAPACITY["DVD5"])
        self.assertEqual(plan["video_bps"], encode.MAX_VIDEO_BPS)
        self.assertLessEqual(plan["video_bps"] + 1_536_000, encode.MAX_TOTAL_BPS)
        # a (hypothetical) 2 Mbit/s audio track pushes the total limit below 8M
        plan = encode.plan_bitrate([(60, 2_000_000)], CAPACITY["DVD5"])
        self.assertEqual(plan["video_bps"], encode.MAX_TOTAL_BPS - 2_000_000)
        self.assertEqual(encode.peak_bitrate(1_536_000), 9_800_000 - 1_536_000)
        self.assertEqual(encode.peak_bitrate(192_000), 9_000_000)

    def test_too_long_raises(self):
        with self.assertRaises(ProjectError):
            encode.plan_bitrate([(10 * 3600, 192_000)], CAPACITY["DVD5"])

    def test_low_bitrate_warns(self):
        plan = encode.plan_bitrate([(4 * 3600, 192_000)], CAPACITY["DVD5"])
        self.assertTrue(plan["warnings"])

    def test_fixed_bitrate(self):
        plan = encode.plan_bitrate([(600, 192_000)], CAPACITY["DVD5"], fixed=5_000_000)
        self.assertEqual(plan["video_bps"], 5_000_000)
        with self.assertRaises(ProjectError):
            encode.plan_bitrate([(4 * 3600, 192_000)], CAPACITY["DVD5"], fixed=8_000_000)


class TestGeometry(unittest.TestCase):
    def test_same_aspect(self):
        self.assertEqual(encode.fit_geometry(1920, 1080, 1, 720, 480, 16 / 9), (720, 480, 0, 0))

    def test_pillarbox_4x3_into_16x9(self):
        w, h, x, y = encode.fit_geometry(640, 480, 1, 720, 480, 16 / 9)
        self.assertEqual((w, h, y), (540, 480, 0))
        self.assertEqual(x, 90)

    def test_letterbox_16x9_into_4x3(self):
        w, h, x, y = encode.fit_geometry(1280, 720, 1, 720, 576, 4 / 3)
        self.assertEqual((w, h, x), (720, 432, 0))
        self.assertEqual(y, 72)

    def test_anamorphic_source(self):
        # 720x480 with 32:27 SAR is already 16:9
        from fractions import Fraction
        self.assertEqual(encode.fit_geometry(720, 480, Fraction(32, 27), 720, 480, 16 / 9),
                         (720, 480, 0, 0))

    def test_cinemascope(self):
        w, h, x, y = encode.fit_geometry(1920, 800, 1, 720, 480, 16 / 9)
        self.assertEqual(w, 720)
        self.assertEqual(h % 2, 0)
        self.assertAlmostEqual(h, 480 * (16 / 9) / 2.4, delta=2)
        self.assertEqual(y % 2, 0)


class TestAuthorXml(unittest.TestCase):
    def setUp(self):
        self.p = build_project(sample_project(), "/v/project.oncemore.json", check_files=False)
        self.xml = author.build_xml(self.p, {"main": "m.mpg", "chapters": "c.mpg"},
                                    {"t1": "t1.mpg", "t2": "t2.mpg"}, "/out")

    def test_structure(self):
        x = self.xml
        self.assertIn('<fpc>g1 = 0; jump titleset 1 menu entry root;</fpc>', x)
        self.assertIn('<pgc entry="root">', x)
        self.assertIn("if (g1 == 2) { g1 = 0; jump menu 2; }", x)
        self.assertIn('<button name="play">g2 = 1; jump title 1;</button>', x)   # play all
        self.assertIn('<button name="ch">jump menu 2;</button>', x)
        self.assertIn('<button name="b">g2 = 0; jump title 2;</button>', x)
        self.assertIn('<button name="ch2">g2 = 0; jump title 1 chapter 2;</button>', x)
        # t1: on to t2 when playing all, else back to main
        self.assertIn('<post>if (g2 == 1) { jump title 2; } g1 = 0; call menu entry root;</post>', x)
        self.assertIn('<post>g2 = 0; g1 = 0; call menu entry root;</post>', x)  # last title
        self.assertIn('<post>jump cell 1;</post>', x)                            # looping menu
        self.assertIn('widescreen="nopanscan"', x)
        self.assertIn('chapters="0:00:00.000,0:00:08.025,0:00:16.033"', x)

    def test_no_playall_no_g2(self):
        d = sample_project()
        d["menus"][0]["buttons"][0]["action"] = "title:t1"
        d["titles"][0]["end_action"] = "title:t2"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertNotIn("g2", x)
        self.assertIn('<button name="play">jump title 1;</button>', x)
        self.assertIn('<post>jump title 2;</post>', x)
        self.assertIn('<post>g1 = 0; call menu entry root;</post>', x)

    def test_first_play_playall(self):
        d = sample_project()
        d["disc"]["first_play"] = "playall"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertEqual(author.first_play_command(p), "g2 = 1; jump title 1;")
        # playall needs no button: the posts still chain
        self.assertTrue(p.uses_playall)
        self.assertEqual([m.number for m in p.menus], [1, 2])

    def test_surround_titleset(self):
        d = sample_project()
        d["titles"][1]["audio"] = {"codec": "ac3", "channels": 6}
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        t1, t2 = p.titles
        self.assertEqual((t2.audio_channels, t2.audio_bitrate), (6, 448_000))
        self.assertEqual((t1.titleset, t2.titleset), (1, 2))      # one audio format per VTS
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn('<audio format="ac3" channels="6"/>', x)
        self.assertIn('<audio format="ac3" channels="2"/>', x)
        self.assertIn(
            "<post>if (g2 == 1) { jump titleset 2 title 1; } g1 = 0; call menu entry root;</post>", x)
        self.assertEqual(encode.audio_args("ac3", 448_000, channels=6)[-2:], ["-ac", "6"])
        _, graph, _ = encode.audio_graph(t2, {t2.source: {"audio_streams": 0}})
        self.assertEqual(graph, "anullsrc=channel_layout=5.1:sample_rate=48000[a0]")

    def test_end_action_to_non_root_menu(self):
        d = sample_project()
        d["titles"][1]["end_action"] = "menu:chapters"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertEqual(author.end_command(p, "menu:chapters"), "g1 = 2; call menu entry root;")
        self.assertEqual(author.end_command(p, "stop"), "exit;")

    def test_first_play_title_and_lpcm(self):
        d = sample_project()
        d["disc"]["first_play"] = "title:t2"
        d["disc"]["aspect"] = "4:3"
        for t in d["titles"]:
            t["audio"] = {"codec": "lpcm"}
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn("<fpc>jump title 2;</fpc>", x)
        self.assertIn('format="pcm"', x)
        self.assertNotIn("widescreen", x)

    def test_streams_and_switch_buttons(self):
        d = sample_project()
        d["titles"][0]["audio_tracks"] = [{"lang": "ja"}, {"source": "c.wav", "lang": "en"}]
        d["titles"][0]["subtitles"] = [{"file": "en.srt", "lang": "en"},
                                       {"file": "ja.srt", "lang": "ja", "default": True}]
        d["menus"][0]["buttons"] += [
            {"id": "a2", "label": "A2", "x": 400, "y": 220, "action": "audio:2"},
            {"id": "s1", "label": "S1", "x": 400, "y": 280, "action": "subtitle:1"},
            {"id": "so", "label": "OFF", "x": 400, "y": 340, "action": "subtitle:off"}]
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn('<audio format="ac3" channels="2" lang="ja"/>', x)
        self.assertIn('<audio format="ac3" channels="2" lang="en"/>', x)
        self.assertLess(x.index('<subpicture lang="en"/>'), x.index('<subpicture lang="ja"/>'))
        self.assertIn('<button name="a2">audio = 1;</button>', x)
        self.assertIn('<button name="s1">subtitle = 64;</button>', x)
        self.assertIn('<button name="so">subtitle = 0;</button>', x)
        self.assertIn("<fpc>subtitle = 65; g1 = 0; jump titleset 1 menu entry root;</fpc>", x)

    def test_multiple_titlesets(self):
        d = sample_project()
        d["titles"][1].update({"aspect": "4:3", "audio": {"codec": "lpcm"},
                               "end_action": "menu:chapters"})
        d["titles"][0]["end_action"] = "title:t2"
        d["menus"][0]["buttons"].append({"id": "b2", "label": "B2", "x": 400, "y": 220,
                                         "action": "chapter:t2:1"})
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn('<dvdauthor dest="/o" jumppad="yes">', x)
        self.assertEqual(x.count("<titleset>"), 2)
        self.assertIn('<button name="b">g2 = 0; jump titleset 2 title 1;</button>', x)
        self.assertIn('<button name="b2">g2 = 0; jump titleset 2 title 1 chapter 1;</button>', x)
        self.assertIn("<post>if (g2 == 1) { jump titleset 2 title 1; } "
                      "jump titleset 2 title 1;</post>", x)                           # t1 -> t2
        self.assertIn("<post>g2 = 0; g1 = 2; call vmgm menu entry title;</post>", x)  # t2 -> menu 2
        self.assertIn('<pgc entry="title"><pre>jump titleset 1 menu entry root;</pre></pgc>', x)
        self.assertIn('<video format="ntsc" aspect="4:3"/>', x)
        self.assertIn('<audio format="pcm"', x)
        import xml.dom.minidom
        xml.dom.minidom.parseString(x)

    def test_audio_graph(self):
        d = sample_project()
        d["titles"][0]["audio_tracks"] = [{}, {"source": "c.wav", "stream": 1}, {"stream": 3}]
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        t = p.titles[0]
        probes = {t.source: {"audio_streams": 1}, t.audio_tracks[1].source: {"audio_streams": 2}}
        extra, graph, labels = encode.audio_graph(t, probes)
        self.assertEqual(extra, ["-i", t.audio_tracks[1].source])
        self.assertEqual(graph.split(";"), ["[0:a:0]aresample=48000,apad[a0]",
                                             "[1:a:1]aresample=48000,apad[a1]",
                                             "anullsrc=channel_layout=stereo:sample_rate=48000[a2]"])
        self.assertEqual(labels, ["[a0]", "[a1]", "[a2]"])

    def test_xml_is_well_formed(self):
        import xml.dom.minidom
        xml.dom.minidom.parseString(self.xml)

    def test_no_menus(self):
        d = sample_project()
        del d["menus"]
        del d["titles"][0]["auto_chapter_menu"]
        d["disc"].pop("first_play")
        for t in d["titles"]:
            t["end_action"] = "stop"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        x = author.build_xml(p, {}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn("<fpc>jump title 1;</fpc>", x)
        self.assertNotIn("<menus>", x)


if __name__ == "__main__":
    unittest.main()
