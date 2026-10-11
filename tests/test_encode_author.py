import json
import unittest

from oncemore import author, encode
from oncemore.errors import ProjectError
from oncemore.project import CAPACITY, build_project
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator


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
        self.assertIn('<fpc>g1 = 1; jump titleset 1 menu entry root;</fpc>', x)
        self.assertIn('<pgc entry="root">', x)
        self.assertIn("<pre>if (g1 == 2) { g1 = 0; jump menu 2; } g1 = 0; "
                      "if (g5 != 0) { button = g5; } else { button = 1024; }</pre>", x)
        self.assertIn('<button name="play">g5 = button; g2 = 1; jump title 1;</button>', x)
        self.assertIn('<button name="ch">g5 = button; jump menu 2;</button>', x)
        self.assertIn('<button name="b">g5 = button; g2 = 0; jump title 2;</button>', x)
        self.assertIn('<button name="ch2">g6 = button; g2 = 0; jump title 1 chapter 2;</button>', x)
        # t1: on to t2 when playing all, else back to main
        self.assertIn('<post>if (g2 == 1) { jump title 2; } g1 = 1; call menu entry root;</post>', x)
        self.assertIn('<post>g2 = 0; g1 = 1; call menu entry root;</post>', x)  # last title
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
        self.assertIn('<button name="play">g5 = button; jump title 1;</button>', x)
        self.assertIn('<post>jump title 2;</post>', x)
        self.assertIn('<post>g1 = 1; call menu entry root;</post>', x)

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
            "<post>if (g2 == 1) { jump titleset 2 title 1; } g1 = 1; call menu entry root;</post>", x)
        self.assertEqual(encode.audio_args("ac3", 448_000, channels=6)[-2:], ["-ac", "6"])
        _, graph, _ = encode.audio_graph(t2, {t2.source: {"audio_streams": 0}})
        self.assertEqual(graph, "anullsrc=channel_layout=5.1:sample_rate=48000[a0]")

    def p1_project(self):
        d = sample_project()
        d["disc"]["title_key"] = "menu:intro"
        d["titles"][0]["remote_menu"] = "chapters"
        main = d["menus"][0]
        main["default_button"] = "b"
        main["buttons"].append({"id": "auto", "label": "AUTO", "x": 470, "y": 220,
                                "action": "title:t2", "auto_activate": True})
        d["menus"].append({"id": "intro", "background_video": "media/sample_a.mp4",
                           "duration": 6, "loop": 2, "loop_point": 3, "end_action": "title:t2",
                           "remember_button": False,
                           "buttons": [{"id": "skip", "label": "SKIP", "x": 80, "y": 380,
                                        "action": "menu:main"}]})
        return build_project(d, "/v/project.oncemore.json", check_files=False)

    def test_menu_timing_and_remote(self):
        p = self.p1_project()
        self.assertEqual([m.id for m in p.menus], ["main", "intro", "chapters"])
        x = author.build_xml(p, {"main": "m", "intro": "i", "chapters": "c"},
                             {"t1": "a", "t2": "b"}, "/o")
        # Title key -> intro (menu 2); Menu key: the title's remote_menu, via g3
        self.assertIn('<pgc entry="title"><pre>g3 = 0; if (g1 == 0) { g1 = 2; } '
                      'jump titleset 1 menu entry root;</pre></pgc>', x)
        self.assertIn("<pre>if (g1 == 0) { g1 = g3; } g3 = 0; "
                      "if (g1 == 2) { g1 = 0; jump menu 2; } if (g1 == 3) { g1 = 0; jump menu 3; } "
                      "g1 = 0; if (g5 != 0) { button = g5; } else { button = 3072; }</pre>", x)
        self.assertIn("<pre>g3 = 3;</pre>", x)                        # t1: Menu -> chapters
        self.assertIn("<pre>g3 = 1;</pre>", x)                        # t2: the root menu
        # intro: plays 0-6 s, then 3-6 s again, then title 2; no button memory
        self.assertIn('<vob file="i"><cell start="0" end="0:00:03.000" chapter="1"/>'
                      '<cell start="0:00:03.000"/></vob>', x)
        self.assertIn("<post>g4 += 1; if (g4 lt 2) { jump cell 2; } g2 = 0; jump title 2;</post>", x)
        self.assertIn("<pre>g4 = 0;</pre>", x)
        self.assertIn('<button name="skip">jump menu 1;</button>', x)
        import xml.dom.minidom
        xml.dom.minidom.parseString(x)

    def test_title_key_to_title_and_validation(self):
        d = sample_project()
        d["disc"]["title_key"] = "playall"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("if (g1 == 0) { g2 = 1; jump title 1; }", author.vmgm_title_command(p))
        d["menus"][0]["default_button"] = "nope"
        d["menus"][0]["loop"] = 3
        d["menus"][0]["end_action"] = "menu:missing"
        d["titles"][0]["remote_menu"] = "gone"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        msg = json.dumps(cm.exception.issues)
        self.assertIn("no button 'nope' in this menu", msg)
        self.assertIn("no menu with id 'missing'", msg)
        self.assertIn("titles[0].remote_menu", msg)

    def test_resume(self):
        d = sample_project()
        d["menus"][0]["buttons"].append({"id": "res", "label": "RESUME", "x": 470, "y": 220,
                                         "action": "resume"})
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertTrue(p.uses_resume)
        self.assertEqual(author.resume_reg(p), "g12")    # no playlists: g12 is free
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn('<button name="res">g5 = button; '
                      'if (g12 == 1) { resume; } g2 = 0; jump title 1;</button>', x)
        self.assertEqual(x.count("<pre>g12 = 1;</pre>"), 2)          # every title
        self.assertIn('<post>g12 = 0; g2 = 0; g1 = 1; call menu entry root;</post>', x)
        # playlists take g0 and g12: the next free one
        d["playlists"] = [{"id": "pl", "items": ["t1"]}]
        self.assertEqual(author.resume_reg(build_project(d, "/v/p.json", check_files=False)),
                         "g11")
        # only menu buttons can resume
        d["titles"][0]["end_action"] = "resume"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("titles[0].end_action", json.dumps(cm.exception.issues))
        # every register taken: playlists, play all, Menu key, a loop, 7 remembering menus
        d["titles"][0]["end_action"] = "menu:main"
        d["titles"][0]["remote_menu"] = "main"
        d["menus"][0]["loop"] = 2
        for k in range(5):
            d["menus"].append({"id": f"m{k}", "buttons": [
                {"id": "x", "label": "X", "x": 100, "y": 100, "action": "menu:main"}]})
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("a resume button needs one free player register",
                      json.dumps(cm.exception.issues))

    def test_override(self):
        d = sample_project()
        d["menus"][0]["buttons"].append({"id": "b2", "label": "B THEN CHAPTERS", "x": 470,
                                         "y": 220, "action": "title:t2",
                                         "override": "menu:chapters"})
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertEqual((p.overrides, author.override_reg(p)), (["menu:chapters"], "g12"))
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn('<button name="b2">g5 = button; g2 = 0; g12 = 1; jump title 2;</button>', x)
        self.assertIn('<button name="b">g5 = button; g2 = 0; g12 = 0; jump title 2;</button>', x)
        self.assertIn('<button name="play">g5 = button; g12 = 0; g2 = 1; jump title 1;</button>', x)
        # every title's post: the override first (cleared), then its own end
        self.assertIn('<post>if (g12 == 1) { g12 = 0; g1 = 2; call menu entry root; } '
                      'g2 = 0; g1 = 1; call menu entry root;</post>', x)
        # with a resume button too, the override takes the next free register
        d["menus"][0]["buttons"].append({"id": "res", "label": "RESUME", "x": 470, "y": 280,
                                         "action": "resume"})
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertEqual((author.resume_reg(p), author.override_reg(p)), ("g12", "g11"))
        # an override needs a title / chapter action and a target that exists
        d["menus"][0]["buttons"][-1]["override"] = "title:nope"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        msg = json.dumps(cm.exception.issues)
        self.assertIn("an override needs a title:... or chapter:... action", msg)
        self.assertIn("no title with id 'nope'", msg)

    def test_links_to_a_button(self):
        d = sample_project()
        d["titles"][1]["end_action"] = "menu:main:b"
        d["menus"][0]["buttons"][0]["action"] = "menu:main:ch"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertEqual(author.entry_reg(p), "g12")
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        # the title's end: B (button 3) in g12, then to the main menu
        self.assertIn("g12 = 3072; g1 = 1; call menu entry root;</post>", x)
        # a button of the main menu that opens it on CHAPTERS
        self.assertIn("g5 = button; g12 = 2048; jump menu 1;", x)
        # main: its remembered button, then the link's, which it clears
        self.assertIn("if (g5 != 0) { button = g5; } else { button = 1024; } "
                      "if (g12 != 0) { button = g12; } g12 = 0;</pre>", x)
        # the chapters menu is not a link target: unchanged
        self.assertNotIn("g12", x.split("<pgc>")[2].split("</pgc>")[0])
        # the button must exist in that menu
        d["titles"][1]["end_action"] = "menu:main:nope"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("menu 'main' has no button 'nope'", json.dumps(cm.exception.issues))

    def test_last_menu(self):
        d = sample_project()
        d["titles"][1]["end_action"] = "lastmenu"
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertEqual(author.last_menu_reg(p), "g12")
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn("g1 = 0; g12 = 1; if (g5 != 0)", x)               # the root menu's pre
        self.assertIn("<pre>g12 = 2; if (g6 != 0)", x)                  # the chapters menu
        self.assertIn("<post>g2 = 0; g1 = g12; call menu entry root;</post>", x)
        # before any menu (first play straight into the title): the first menu
        d["disc"]["first_play"] = "title:t2"
        sim = Simulator(build_project(d, "/v/project.oncemore.json", check_files=False))
        s = sim.start()
        sim.press(s, "end")
        self.assertEqual((s["domain"], s["menu"]), ("menu", "main"))
        # only where something ends
        d["disc"]["first_play"] = "menu:main"
        d["menus"][0]["loop"], d["menus"][0]["end_action"] = 2, "lastmenu"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("menus[0].end_action", json.dumps(cm.exception.issues))

    def p2_project(self):
        d = sample_project()
        d["titles"][1].update({"aspect": "4:3", "audio": {"codec": "lpcm"}, "chapters": [0, 4, 8]})
        d["titles"][0]["chapters"] = [{"time": 0, "name": "Opening"},
                                      {"time": "00:00:08", "name": "Middle", "poster": 10}, 16]
        d["playlists"] = [{"id": "best", "items": ["t1:2", "t2:2-3", "t1:1"],
                           "end_action": "menu:main"}]
        d["menus"][0]["buttons"].append({"id": "pl", "label": "BEST", "x": 470, "y": 220,
                                         "action": "playlist:best"})
        return build_project(d, "/v/project.oncemore.json", check_files=False)

    def test_playlists(self):
        p = self.p2_project()
        self.assertEqual([(i.title_id, i.first, i.last) for i in p.playlist("best").items],
                         [("t1", 2, 2), ("t2", 2, None), ("t1", 1, 1)])   # t2:2-3 runs to the end
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        # start: state 1, stop after chapter 2
        self.assertIn('<button name="pl">g5 = button; g2 = 0; g0 = 1; g12 = 2; '
                      'jump title 1 chapter 2;</button>', x)
        # single plays leave playlist and play-all mode
        self.assertIn('<button name="b">g5 = button; g2 = 0; g0 = 0; g12 = 0; '
                      'jump titleset 2 title 1;</button>', x)
        # t1's chapter cells stop early for items ending at chapters 1 and 2
        self.assertIn('<cell start="0:00:00.000" end="0:00:08.025" chapter="1">'
                      'if (g12 == 1) jump pgc tail;</cell>', x)
        self.assertIn('<cell start="0:00:08.025" end="0:00:16.033" chapter="1">'
                      'if (g12 == 2) jump pgc tail;</cell><cell start="0:00:16.033" chapter="1"></cell>', x)
        # t1 post: state 1 -> state 2 in titleset 2 (through the VMGM); state 3 -> end
        self.assertIn("if (g0 == 1) { g0 = 2; g12 = 0; g1 = 1000; call vmgm menu entry title; }", x)
        self.assertIn("if (g0 == 3) { g0 = 0; g12 = 0; g1 = 1; call menu entry root; }", x)
        # t2 post: state 2 -> state 3 back in titleset 1
        self.assertIn("if (g0 == 2) { g0 = 3; g12 = 1; g1 = 1000; call vmgm menu entry title; }", x)
        self.assertIn("if (g1 == 1000) { g1 = 0; if (g0 == 1) { jump titleset 1 title 1 chapter 2; } "
                      "if (g0 == 2) { jump titleset 2 title 1 chapter 2; } "
                      "if (g0 == 3) { jump titleset 1 title 1; } }", x)
        # chapter names and poster frames on the chapter menu
        ch = p.menu("chapters")
        self.assertEqual([b.label for b in ch.buttons[:3]], ["Opening", "Middle", "Chapter 3"])
        self.assertEqual(ch.buttons[1].thumb.time, 10.0)
        import xml.dom.minidom
        xml.dom.minidom.parseString(x)

    def test_playlist_validation(self):
        d = sample_project()
        d["playlists"] = [{"id": "x", "items": ["t1:2-9", "nope", "t2:0"]}]
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        msg = json.dumps(cm.exception.issues)
        self.assertIn("does not match", msg)                      # t2:0 (schema)
        d["playlists"] = [{"id": "x", "items": ["t1:2-9", "nope"]}]
        d["menus"][0]["buttons"][0]["action"] = "playlist:missing"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        msg = json.dumps(cm.exception.issues)
        self.assertIn("has chapters 1-3; 2-9", msg)
        self.assertIn("no title with id 'nope'", msg)
        self.assertIn("no playlist with id 'missing'", msg)

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
        self.assertIn("<fpc>subtitle = 65; g1 = 1; jump titleset 1 menu entry root;</fpc>", x)
        # switches made along with a link (play with the commentary, subtitles off)
        d["menus"][0]["buttons"].append({"id": "pc", "label": "PC", "x": 400, "y": 400,
                                         "action": "title:t1", "audio": 2, "subtitle": 0})
        p = build_project(d, "/v/project.oncemore.json", check_files=False)
        x = author.build_xml(p, {"main": "m", "chapters": "c"}, {"t1": "a", "t2": "b"}, "/o")
        self.assertIn('<button name="pc">audio = 1; subtitle = 0; g5 = button; g2 = 0; '
                      'jump title 1;</button>', x)
        sim = Simulator(p)
        s = sim.start()
        for k in ("select:pc", "enter"):
            sim.press(s, k)
        self.assertEqual((s["audio"], s["subtitle"], s["title"]), (2, 0, "t1"))
        d["menus"][0]["buttons"][-1]["action"] = "audio:2"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("already a stream button", json.dumps(cm.exception.issues))
        d["menus"][0]["buttons"][-1].update(audio=3, action="title:t1")
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/v/project.oncemore.json", check_files=False)
        self.assertIn("no audio stream 3", json.dumps(cm.exception.issues))

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
        self.assertIn('<button name="b">g5 = button; g2 = 0; jump titleset 2 title 1;</button>', x)
        self.assertIn('<button name="b2">g5 = button; g2 = 0; jump titleset 2 title 1 chapter 1;</button>', x)
        self.assertIn("<post>if (g2 == 1) { jump titleset 2 title 1; } "
                      "jump titleset 2 title 1;</post>", x)                           # t1 -> t2
        self.assertIn("<post>g2 = 0; g1 = 2; call vmgm menu entry title;</post>", x)  # t2 -> menu 2
        self.assertIn('<pgc entry="title"><pre>jump titleset 1 menu entry root;</pre></pgc>', x)
        # the Menu key inside titleset 2 goes back to the root menu through the VMGM
        self.assertIn('<pgc entry="root"><pre>g1 = 1; jump vmgm menu entry title;</pre></pgc>', x)
        self.assertIn('<video format="ntsc" aspect="4:3"/>', x)
        self.assertIn('<audio format="pcm"', x)
        import xml.dom.minidom
        xml.dom.minidom.parseString(x)

    def test_plan_with_title_bitrates(self):
        cap = CAPACITY["DVD5"]
        auto = encode.plan_bitrate([(3600, 192_000), (3600, 192_000)], cap)
        mixed = encode.plan_bitrate([(3600, 192_000, 3_000_000), (3600, 192_000)], cap)
        self.assertEqual(mixed["per_title"][0], 3_000_000)
        # the other title gets what the fixed one leaves: more than an even split
        self.assertGreater(mixed["per_title"][1], auto["video_bps"])
        self.assertLess(mixed["estimated_bytes"], cap)
        both = encode.plan_bitrate([(60, 192_000, 4_000_000), (60, 192_000, 6_000_000)], cap)
        self.assertEqual(both["per_title"], [4_000_000, 6_000_000])
        with self.assertRaises(ProjectError):            # fixed rates that cannot fit
            encode.plan_bitrate([(4 * 3600, 192_000, 8_000_000)], cap)

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
