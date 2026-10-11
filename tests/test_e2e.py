"""End-to-end: oncemore init -> oncemore iso -> inspect the image.

Needs ffmpeg (with drawtext), ffprobe, dvdauthor/spumux and an ISO tool.
The navigation checks additionally need libdvdnav (skipped otherwise).
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from oncemore import tools
from oncemore.project import CAPACITY

from .helpers import have, json_lines, read_rgba_png, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

TOOLS_OK = (have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)
SKIP_REASON = "needs ffmpeg (drawtext), ffprobe, dvdauthor, spumux and an ISO tool"


def ffprobe_streams(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                        "-probesize", "50M", "-analyzeduration", "50M", path],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)["streams"]


def iso_list(iso):
    """Paths inside the ISO 9660 tree of an image."""
    if shutil.which("xorriso"):
        p = subprocess.run(["xorriso", "-indev", iso, "-find", "/", "-type", "f"],
                           capture_output=True, text=True, check=True)
        return sorted(line.strip().strip("'") for line in p.stdout.splitlines()
                      if line.strip().startswith("'/"))
    if shutil.which("isoinfo"):
        p = subprocess.run(["isoinfo", "-f", "-i", iso], capture_output=True, text=True,
                           check=True)
        return sorted(line.split(";")[0] for line in p.stdout.splitlines()
                      if "." in line.rsplit("/", 1)[-1])
    raise unittest.SkipTest("needs xorriso or isoinfo to list the image")


def iso_extract(iso, inner, dest):
    if shutil.which("xorriso"):
        subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", inner, dest],
                       capture_output=True, check=True)
    elif shutil.which("isoinfo"):
        with open(dest, "wb") as f:
            subprocess.run(["isoinfo", "-i", iso, "-x", inner + ";1"], stdout=f, check=True)
    else:
        raise unittest.SkipTest("needs xorriso or isoinfo to extract files")
    return dest


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestDefaultSample(unittest.TestCase):
    """The completion criterion: init + iso with no edits, default settings."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-")
        rc, out, err = run_cli("init", "demo", cwd=cls.tmp)
        assert rc == 0, err
        cls.iso = os.path.join(cls.tmp, "demo.iso")
        rc, out, err = run_cli("--json", "iso", "demo/project.oncemore.json", "-o", "demo.iso",
                               cwd=cls.tmp)
        cls.rc, cls.events, cls.err = rc, json_lines(out), err
        assert rc == 0, err + out
        cls.result = cls.events[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_json_progress_and_result(self):
        kinds = [e["event"] for e in self.events]
        self.assertIn("step", kinds)
        self.assertIn("progress", kinds)
        self.assertEqual(self.result["event"], "result")
        self.assertTrue(self.result["ok"])
        # realpath: on macOS the temp dir is /var -> /private/var
        self.assertEqual(os.path.realpath(self.result["iso"]), os.path.realpath(self.iso))
        steps = [e["step"] for e in self.events if e["event"] == "step"]
        for s in ("probe", "menu", "encode", "author", "iso"):
            self.assertIn(s, steps)

    def test_build_dir_removed(self):
        self.assertEqual(sorted(os.listdir(self.tmp)), ["demo", "demo.iso"])

    def test_written_by_the_builtin_writer(self):
        self.assertEqual((self.result["iso_tool"], self.result["iso_udf"]), ("builtin", True))

    def test_iso_contains_video_ts(self):
        files = iso_list(self.iso)
        for name in ("VIDEO_TS.IFO", "VIDEO_TS.BUP", "VTS_01_0.IFO", "VTS_01_0.BUP",
                     "VTS_01_0.VOB", "VTS_01_1.VOB"):
            self.assertIn(f"/VIDEO_TS/{name}", files)
        self.assertFalse([f for f in files if ".work" in f], "work files leaked into the ISO")

    def test_iso_is_udf_readable(self):
        if not self.result.get("iso_udf"):
            self.skipTest("ISO tool without UDF")
        with open(self.iso, "rb") as f:
            f.seek(16 * 2048)
            vrs = f.read(2048 * 4)
        self.assertIn(b"CD001", vrs)  # ISO 9660 primary descriptor
        self.assertIn(b"NSR02", vrs)  # UDF 1.02 descriptor
        self.assertEqual(vrs[1:6], b"CD001")
        # PVD volume id; genisoimage pads with spaces, hdiutil with NULs
        self.assertEqual(vrs[40:72].decode("ascii").rstrip(" \x00"), "SAMPLE_DISC")
        # libdvdread (VLC, mpv) shows the UDF volume name as the disc title
        from oncemore.udfinfo import volume_names
        names = volume_names(self.iso)
        self.assertEqual(names, self.result["volume_names"])
        self.assertEqual(names["udf_volume"], "SAMPLE_DISC", names)

    def test_title_vob_streams(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_1.VOB", os.path.join(self.tmp, "t.vob"))
        streams = ffprobe_streams(vob)
        v = [s for s in streams if s["codec_type"] == "video"]
        a = [s for s in streams if s["codec_type"] == "audio"]
        self.assertEqual(v[0]["codec_name"], "mpeg2video")
        self.assertEqual((v[0]["width"], v[0]["height"]), (720, 480))
        self.assertEqual(v[0]["r_frame_rate"], "30000/1001")
        self.assertEqual(v[0]["display_aspect_ratio"], "16:9")
        self.assertEqual(a[0]["codec_name"], "ac3")
        self.assertEqual(a[0]["sample_rate"], "48000")

    def test_menu_vob_has_subpictures(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_0.VOB", os.path.join(self.tmp, "m.vob"))
        codecs = [s["codec_name"] for s in ffprobe_streams(vob)]
        self.assertIn("mpeg2video", codecs)
        self.assertIn("dvd_subtitle", codecs)

    def test_size_within_target(self):
        self.assertLessEqual(self.result["bytes"], CAPACITY["DVD5"])
        self.assertLessEqual(os.path.getsize(self.iso), CAPACITY["DVD5"])
        self.assertEqual(self.result["iso_bytes"], os.path.getsize(self.iso))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_menu_navigation(self):
        """Press buttons like a remote control would, through libdvdnav."""
        if not self.result.get("iso_udf"):
            self.skipTest("libdvdread needs a UDF image")
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.num_titles(), 2)
            self.assertEqual(d.num_parts(1), 3)
            # first play lands on the main menu with three buttons
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 3)
            self.assertEqual(d.highlight(), 1)
            self.assertEqual(d.move("down"), 2)
            self.assertEqual(d.move("down"), 3)
            self.assertEqual(d.move("down"), 1)       # wraps
            self.assertEqual(d.move("right"), 1)      # nothing to the right
            # CHAPTERS -> generated chapter menu
            d.activate(2)
            self.assertEqual(d.wait_menu(), 2)
            self.assertEqual(d.button_count(), 4)
            self.assertEqual(d.move("right"), 2)
            # chapter 2 button starts title 1 at chapter 2
            d.activate(2)
            self.assertEqual(d.wait_title(), (1, 2))
            # played on its own, title 1 ends -> end_action menu:main
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            # PLAY ALL: title 1, then title 2, then title 2's end_action
            d.activate(1)
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual(d.play_to_end_of_title(), ("title", (2, 1)))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            # chapter 3 after PLAY ALL is a single play again
            d.activate(2)
            self.assertEqual(d.wait_menu(), 2)
            d.activate(3)
            self.assertEqual(d.wait_title(), (1, 3))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            # BACK from the chapter menu returns to main
            d.activate(2)
            self.assertEqual(d.wait_menu(), 2)
            d.activate(4)
            self.assertEqual(d.wait_menu(), 1)
            # SAMPLE TITLE B plays title 2 directly
            d.activate(3)
            self.assertEqual(d.wait_title(), (2, 1))


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestPalLpcmBuild(unittest.TestCase):
    """PAL 4:3 with LPCM audio, `build` to a folder, --fast, --keep-work."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-pal-")
        rc, _, err = run_cli("init", "pal", "--standard", "PAL", "--aspect", "4:3", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "pal", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        for t in data["titles"]:
            t["audio"] = {"codec": "lpcm"}
        data["disc"]["label"] = "Sample PAL disc"
        # colour set: buttons shown in white at ~40% when not selected, a 75% highlight
        data["menus"][0]["normal_color"] = "#FFFFFF60"
        data["menus"][0]["highlight_color"] = "#FFD400C0"
        with open(path, "w") as f:
            json.dump(data, f)
        cls.out = os.path.join(cls.tmp, "out")
        rc, out, err = run_cli("--json", "build", path, "-o", cls.out, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]
        cls.project = path

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_folder_layout(self):
        self.assertTrue(os.path.isdir(os.path.join(self.out, ".work")))
        self.assertTrue(os.path.isdir(os.path.join(self.out, "AUDIO_TS")))
        files = sorted(os.listdir(os.path.join(self.out, "VIDEO_TS")))
        self.assertEqual(files, self.result["files"])
        self.assertIn("VTS_01_1.VOB", files)
        self.assertIn("disc.label normalised to 'SAMPLE_PAL_DISC'", self.result["warnings"])

    def test_dvdauthor_reports_no_timing_problems(self):
        """ffmpeg writes fixed LPCM frame counts; without lpcmfix dvdauthor
        prints thousands of 'Audio pts ... moves backwards' warnings."""
        with open(os.path.join(self.out, ".work", "logs", "dvdauthor.log")) as f:
            warns = [l for l in f if l.startswith("WARN")]
        self.assertEqual(warns, [])

    def test_pal_lpcm_streams(self):
        streams = ffprobe_streams(os.path.join(self.out, "VIDEO_TS", "VTS_01_1.VOB"))
        v = next(s for s in streams if s["codec_type"] == "video")
        a = next(s for s in streams if s["codec_type"] == "audio")
        self.assertEqual((v["width"], v["height"], v["r_frame_rate"]), (720, 576, "25/1"))
        self.assertEqual(v["display_aspect_ratio"], "4:3")
        self.assertEqual(a["codec_name"], "pcm_dvd")
        self.assertEqual(a["sample_rate"], "48000")

    @unittest.skipUnless(have("dvdunauthor"), "dvdunauthor not installed")
    def test_chapter_cells_are_frame_accurate(self):
        d = os.path.join(self.tmp, "unauthor")
        os.makedirs(d, exist_ok=True)
        subprocess.run(["dvdunauthor", os.path.join(self.out, "VIDEO_TS")], cwd=d,
                       capture_output=True, check=True)
        with open(os.path.join(d, "dvdauthor.xml")) as f:
            xml = f.read()
        # title 1 chapters at 0, 8 and 16 s (exact frames at 25 fps)
        self.assertIn('<cell start="0:00:00.000" end="0:00:08.000" chapter="1"/>', xml)
        self.assertIn('<cell start="0:00:08.000" end="0:00:16.000" chapter="1"/>', xml)

    def test_menu_colours_survive_encoding(self):
        """A solid background must decode to (nearly) the same RGB. Catches a
        double colour-matrix conversion such as ffmpeg 7.1+'s colourspace
        negotiation re-converting already-BT.601 frames."""
        mpg = os.path.join(self.out, ".work", "menus", "chapters.mpg")
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", mpg, "-frames:v", "1",
                            "-vf", "crop=32:32:680:536,scale=in_color_matrix=bt601:in_range=tv,"
                                   "format=rgb24",
                            "-f", "rawvideo", "pipe:1"], capture_output=True, check=True)
        px = p.stdout
        avg = [sum(px[i::3]) / (len(px) // 3) for i in range(3)]
        for got, want in zip(avg, (0x10, 0x18, 0x20)):  # DEFAULT_BG #101820
            self.assertAlmostEqual(got, want, delta=6, msg=f"decoded {avg}")

    @unittest.skipUnless(have("spuunmux"), "spuunmux not installed")
    def test_menu_colour_set_on_disc(self):
        """The normal colour is the subpicture's display image; the colours'
        alpha becomes the DVD contrast (16 levels)."""
        d = os.path.join(self.tmp, "spu")
        os.makedirs(d, exist_ok=True)
        subprocess.run(["spuunmux", "-s", "0", os.path.join(self.out, ".work", "menus", "main.mpg")],
                       cwd=d, capture_output=True, check=True, env={**os.environ, "VIDEO_FORMAT": "PAL"})
        def colours(name):
            return {p for p in read_rgba_png(os.path.join(d, name))[2] if p[3]}
        self.assertEqual(colours("sub00000.png"), {(255, 255, 255, 0x60 // 16 * 17)})
        self.assertEqual({p[3] for p in colours("sub00000h.png")}, {0xC0 // 16 * 17})
        self.assertEqual({p[3] for p in colours("sub00000s.png")}, {255})

    def test_validate_reports_plan(self):
        rc, out, err = run_cli("--json", "validate", self.project)
        self.assertEqual(rc, 0, err)
        r = json_lines(out)[-1]
        self.assertEqual(r["video_bps"], 8_000_000)
        self.assertEqual([t["audio"] for t in r["titles"]], ["lpcm", "lpcm"])
        self.assertEqual(r["titles"][0]["chapters"], [0.0, 8.0, 16.0])
        self.assertTrue(r["font"])

    def test_preview_menu(self):
        png = os.path.join(self.tmp, "preview.png")
        rc, out, err = run_cli("--json", "preview-menu", self.project, "--menu", "chapters",
                               "--button", "ch2", "-o", png)
        self.assertEqual(rc, 0, err)
        r = json_lines(out)[-1]
        self.assertEqual(r["size"], [768, 576])  # square-pixel 4:3 PAL
        self.assertEqual(r["button"], "ch2")
        with open(png, "rb") as f:
            head = f.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(int.from_bytes(head[16:20], "big"), 768)
        rc, _, err = run_cli("preview-menu", self.project, "--menu", "nope", "-o", png)
        self.assertEqual(rc, 1)
        self.assertIn("no menu 'nope'", err)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestMixedTitlesets(unittest.TestCase):
    """A 16:9 AC-3 title and a 4:3 LPCM title on one disc: two titlesets,
    menus in the first, jumps and returns across them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-mixed-")
        rc, _, err = run_cli("init", "mixed", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "mixed", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        b = data["titles"][1]
        b.update({"aspect": "4:3", "audio": {"codec": "lpcm"}, "chapters": [0, 6],
                  "end_action": "menu:chapters_b",
                  "auto_chapter_menu": {"id": "chapters_b", "back": "menu:main"}})
        data["menus"][0]["buttons"].append(
            {"id": "cb", "label": "B CHAPTERS", "x": 120, "y": 400, "action": "menu:chapters_b"})
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "mixed.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_two_titlesets(self):
        files = iso_list(self.iso)
        for name in ("VTS_01_0.IFO", "VTS_01_1.VOB", "VTS_02_0.IFO", "VTS_02_1.VOB"):
            self.assertIn(f"/VIDEO_TS/{name}", files)
        self.assertEqual([(t["titleset"], t["aspect"], t["audio"]) for t in self.result["titles"]],
                         [(1, "16:9", "ac3"), (2, "4:3", "lpcm")])
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_02_1.VOB", os.path.join(self.tmp, "b.vob"))
        streams = ffprobe_streams(vob)
        v = next(s for s in streams if s["codec_type"] == "video")
        a = next(s for s in streams if s["codec_type"] == "audio")
        self.assertEqual(v["display_aspect_ratio"], "4:3")
        self.assertEqual(a["codec_name"], "pcm_dvd")

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_navigation_across_titlesets(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.num_titles(), 2)
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 4)
            d.activate(4)                                    # B CHAPTERS (menu 3)
            self.assertEqual(d.wait_menu(), 3)
            d.activate(2)                                    # chapter 2 of the 4:3 title
            self.assertEqual(d.wait_title(), (2, 2))
            # end_action menu:chapters_b from titleset 2, routed through VMGM
            self.assertEqual(d.play_to_end_of_title(), ("menu", 3))
            d.activate(3)                                    # BACK
            self.assertEqual(d.wait_menu(), 1)
            d.activate(1)                                    # PLAY ALL: t1 -> t2 across titlesets
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual(d.play_to_end_of_title(), ("title", (2, 1)))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 3))  # last title's end_action


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestTracksSubtitlesMotionMenu(unittest.TestCase):
    """Two audio tracks, two subtitle languages (Japanese on by default),
    stream-switch buttons and a motion menu, written as an ISO."""

    SRT_JA = ("1\n00:00:01,000 --> 00:00:03,000\n日本語の字幕です\n\n"
              "2\n00:00:04,000 --> 00:00:06,000\n二行目の\nテストです\n")
    SRT_EN = "1\n00:00:01,500 --> 00:00:05,000\nDemo subtitle in English\n"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-tracks-")
        media = os.path.join(cls.tmp, "proj", "media")
        os.makedirs(media)

        def ff(*args):
            subprocess.run(["ffmpeg", "-v", "error", "-y"] + list(args), check=True)
        ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30000/1001:d=8", "-f", "lavfi", "-i",
           "sine=f=440:d=8", "-c:v", "mpeg4", "-c:a", "aac", "-shortest",
           os.path.join(media, "main.mp4"))
        ff("-f", "lavfi", "-i", "sine=f=880:d=6", "-c:a", "pcm_s16le",
           os.path.join(media, "commentary.wav"))
        ff("-f", "lavfi", "-i", "mandelbrot=s=640x360:r=25", "-t", "3", "-c:v", "mpeg4",
           os.path.join(media, "loop.mp4"))
        for name, text in (("ja.srt", cls.SRT_JA), ("en.srt", cls.SRT_EN)):
            with open(os.path.join(media, name), "w", encoding="utf-8") as f:
                f.write(text)
        project = {
            "version": 1,
            "disc": {"label": "SAMPLE_TRACKS", "standard": "NTSC", "aspect": "16:9"},
            "titles": [{"id": "t1", "name": "Sample Tracks", "source": "media/main.mp4",
                        "audio_tracks": [{"lang": "ja"},
                                         {"source": "media/commentary.wav", "lang": "en"}],
                        "subtitles": [{"file": "media/ja.srt", "lang": "ja", "default": True},
                                      {"file": "media/en.srt", "lang": "en"}]}],
            "menus": [{"id": "main", "background_video": "media/loop.mp4",
                       "texts": [{"text": "サンプル", "x": 100, "y": 40, "size": 40}],
                       "buttons": [
                           {"id": "play", "label": "PLAY", "x": 100, "y": 120,
                            "action": "title:t1"},
                           {"id": "a2", "label": "COMMENTARY", "x": 100, "y": 180,
                            "action": "audio:2"},
                           {"id": "s2", "label": "ENGLISH SUBTITLES", "x": 100, "y": 240,
                            "action": "subtitle:2"},
                           {"id": "off", "label": "SUBTITLES OFF", "x": 100, "y": 300,
                            "action": "subtitle:off"},
                           {"id": "plain", "label": "PLAY, ORIGINAL SOUND ONLY", "x": 100,
                            "y": 360, "action": "title:t1", "audio": 1, "subtitle": 0}]}],
        }
        cls.project = os.path.join(cls.tmp, "proj", "project.oncemore.json")
        with open(cls.project, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False)
        cls.iso = os.path.join(cls.tmp, "tracks.iso")
        rc, out, err = run_cli("--json", "iso", cls.project, "-o", cls.iso, "--fast",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_title_streams(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_1.VOB", os.path.join(self.tmp, "t.vob"))
        codecs = [s["codec_name"] for s in ffprobe_streams(vob)]
        self.assertEqual(codecs.count("ac3"), 2)
        self.assertEqual(codecs.count("dvd_subtitle"), 2)
        t = self.result["titles"][0]
        self.assertEqual([a["lang"] for a in t["audio_tracks"]], ["ja", "en"])
        self.assertEqual([s["cues"] for s in t["subtitles"]], [2, 1])
        self.assertEqual(t["audio_bps"], 2 * 192_000)

    def test_motion_menu_moves(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_0.VOB", os.path.join(self.tmp, "m.vob"))
        frames = []
        for n in (0, 45):
            p = subprocess.run(["ffmpeg", "-v", "error", "-i", vob, "-vf",
                                f"select=eq(n\\,{n}),scale=64:36,format=gray",
                                "-frames:v", "1", "-f", "rawvideo", "pipe:1"],
                               capture_output=True, check=True)
            frames.append(p.stdout)
        diff = sum(abs(a - b) for a, b in zip(*frames)) / len(frames[0])
        self.assertGreater(diff, 2.0, "menu background did not change between frames")

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_stream_selection(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 5)
            d.activate(1)
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual([d.audio_lang(0), d.audio_lang(1)], ["ja", "en"])
            self.assertEqual([d.subtitle_lang(0), d.subtitle_lang(1)], ["ja", "en"])
            self.assertEqual(d.active_audio(), 0)
            self.assertEqual(d.active_subtitle(), (0, True))     # Japanese, on by default
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            d.activate(2)                                         # COMMENTARY
            d.activate(3)                                         # ENGLISH SUBTITLES
            d.activate(1)
            d.wait_title()
            self.assertEqual(d.active_audio(), 1)
            self.assertEqual(d.active_subtitle(), (1, True))
            d.play_to_end_of_title()
            d.activate(4)                                         # SUBTITLES OFF
            d.activate(1)
            d.wait_title()
            self.assertFalse(d.active_subtitle()[1])
            d.play_to_end_of_title()
            d.activate(3)                                         # English subtitles on
            d.activate(5)    # PLAY, ORIGINAL SOUND ONLY: audio 1 (commentary before), subtitles off
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual(d.active_audio(), 0)
            self.assertFalse(d.active_subtitle()[1])


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestSurround(unittest.TestCase):
    """Title B from a 5.1 source kept as 5.1 AC-3 (its own titleset), title A
    stereo; a stereo source asked for 5.1 gets a warning."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-51-")
        rc, _, err = run_cli("init", "surround", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "surround")
        # 6 s of video with a different tone on each of the six channels
        tones = "|".join(f"0.3*sin({f}*2*PI*t)" for f in (330, 440, 550, 60, 660, 770))
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30000/1001:d=6",
                        "-f", "lavfi", "-i", f"aevalsrc={tones}:c=5.1:s=48000:d=6",
                        "-c:v", "mpeg4", "-q:v", "5", "-c:a", "aac", "-b:a", "384k",
                        "-shortest", os.path.join(proj, "media", "surround.mp4")], check=True)
        path = os.path.join(proj, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["titles"][1].update({"source": "media/surround.mp4",
                                  "audio": {"codec": "ac3", "channels": 6}})
        cls.data, cls.path = data, path
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "surround.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_51_track(self):
        self.assertEqual([(t["titleset"], t["audio_channels"]) for t in self.result["titles"]],
                         [(1, 2), (2, 6)])
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_02_1.VOB", os.path.join(self.tmp, "b.vob"))
        a = next(s for s in ffprobe_streams(vob) if s["codec_type"] == "audio")
        self.assertEqual((a["codec_name"], a["channels"]), ("ac3", 6))
        # the centre channel (550 Hz in the source) survived as its own channel
        p = subprocess.run(["ffmpeg", "-v", "info", "-i", vob, "-vn",
                            "-af", "pan=mono|c0=FC,volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True)
        mean = float(p.stderr.split("mean_volume:")[1].split("dB")[0])
        self.assertGreater(mean, -30)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_player_sees_six_channels(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            d.activate(3)                                   # SAMPLE TITLE B
            self.assertEqual(d.wait_title(), (2, 1))
            self.assertEqual(d.audio_channels(0), 6)

    def test_stereo_source_warns(self):
        data = json.loads(json.dumps(self.data))
        data["titles"][0]["audio"] = {"codec": "ac3", "channels": 6}
        path = os.path.join(self.tmp, "surround", "warn.oncemore.json")
        with open(path, "w") as f:
            json.dump(data, f)
        rc, out, err = run_cli("--json", "validate", path, cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        self.assertIn("only use the front speakers", out)



@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestImageButtons(unittest.TestCase):
    """Two picture buttons (one highlighted by its shape, one by a frame)
    next to the sample's text buttons."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-img-")
        rc, _, err = run_cli("init", "img", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "img")
        # a "play" triangle on a transparent background
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=black@0:s=120x90,format=rgba", "-vf",
                        "geq=r=255:g=200:b=40:a='if(lt(abs(Y-45),(110-X)/2.4)*gt(X,10),255,0)'",
                        "-frames:v", "1", os.path.join(proj, "media", "play.png")], check=True)
        path = os.path.join(proj, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["menus"][0]["buttons"] += [
            {"id": "ip", "image": "media/play.png", "x": 470, "y": 200, "width": 100,
             "highlight": "shape", "action": "title:t2"},
            {"id": "if", "image": "media/play.png", "x": 470, "y": 330, "width": 80,
             "action": "menu:chapters"}]
        with open(path, "w") as f:
            json.dump(data, f)
        cls.path = path
        cls.iso = os.path.join(cls.tmp, "img.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_highlight_shapes(self):
        from oncemore import menu as menu_mod, png4
        from oncemore.project import load_project
        project = load_project(self.path)
        mb = menu_mod.MenuBuilder(project, os.path.join(self.tmp, "work"))
        geoms = {g.id: g for g in mb.layout(project.menu("main"))}
        # shape: the triangle's opaque pixels, inside the 100 px wide picture
        x0, y0, x1, y1 = geoms["ip"].rect
        self.assertTrue(468 <= x0 and x1 <= 574, geoms["ip"].rect)
        mask = geoms["ip"].shape[0]
        self.assertIsInstance(mask, png4.Mask)
        mx0, my0, mx1, my1 = mask.bbox()
        self.assertLess(mx1 - mx0, 100)                  # transparent margins left out
        # frame: a rectangle around the 80 px picture
        kind, (fx0, fy0, fx1, fy1) = geoms["if"].shape[0]
        self.assertEqual((kind, fx0, fy0), ("frame", 466, 326))
        self.assertEqual(fx1 - fx0, 80 + 7)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_press_picture_buttons(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 5)
            self.assertEqual(d.move("right"), 4)         # PLAY ALL -> the shape button
            d.activate(4)
            self.assertEqual(d.wait_title(), (2, 1))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            d.activate(5)                                # the framed one
            self.assertEqual(d.wait_menu(), 2)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestMenuTimingAndRemote(unittest.TestCase):
    """Default and remembered buttons, an auto-activate button, Menu / Title
    keys (also from a second titleset), and an intro menu that plays twice
    from a loop point and then times out to a title."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-remote-")
        rc, _, err = run_cli("init", "remote", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "remote", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["disc"]["title_key"] = "menu:intro"
        t1, t2 = data["titles"]
        t1["remote_menu"] = "chapters"
        t2.update({"aspect": "4:3", "audio": {"codec": "lpcm"}})       # titleset 2
        main = data["menus"][0]
        main["default_button"] = "b"
        main["buttons"].append({"id": "auto", "label": "AUTO", "x": 470, "y": 220,
                                "action": "title:t2", "auto_activate": True})
        data["menus"].append({"id": "intro", "background_video": "media/sample_a.mp4",
                              "duration": 6, "loop": 2, "loop_point": 3,
                              "end_action": "title:t2",
                              "buttons": [{"id": "skip", "label": "SKIP", "x": 80, "y": 380,
                                           "action": "menu:main"}]})
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "remote.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_remote(self):
        MAIN, INTRO, CHAPTERS = 1, 2, 3
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), MAIN)
            self.assertEqual(d.highlight(), 3)                  # default_button "b"
            d.activate(2)                                       # CHAPTERS
            self.assertEqual(d.wait_menu(), CHAPTERS)
            d.activate(4)                                       # BACK
            self.assertEqual(d.wait_menu(), MAIN)
            self.assertEqual(d.highlight(), 2)                  # remembers CHAPTERS
            d.activate(2)
            self.assertEqual(d.wait_menu(), CHAPTERS)
            d.activate(2)                                       # chapter 2
            self.assertEqual(d.wait_title(), (1, 2))
            d.menu_key()                                        # remote_menu of t1
            self.assertEqual(d.wait_menu(), CHAPTERS)
            self.assertEqual(d.highlight(), 2)                  # the chapter just played
            d.activate(4)
            self.assertEqual(d.wait_menu(), MAIN)
            d.select(1)
            self.assertEqual(d.move("right"), 4)                # AUTO runs on selection
            self.assertEqual(d.wait_title(), (2, 1))            # title 2 = titleset 2
            d.menu_key()                                        # Menu key outside titleset 1
            self.assertEqual(d.wait_menu(), MAIN)
            d.title_key()                                       # Title key -> intro
            self.assertEqual(d.wait_menu(), INTRO)
            seen = len(d.cells)
            # intro: cells 1, 2, then 2 again from the loop point, then title 2
            self.assertEqual(d.wait_title(max_events=2_000_000), (2, 1))
            intro = [c for dom, pgc, c in d.cells[seen - 1:] if dom == "vtsm" and pgc == INTRO]
            self.assertEqual(intro, [1, 2, 2], d.cells[seen - 1:])


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestPlaylists(unittest.TestCase):
    """A playlist of chapter ranges that hops between two titlesets and back,
    stopping in the middle of titles; named chapters with a poster frame."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-playlist-")
        rc, _, err = run_cli("init", "pl", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "pl", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        t1, t2 = data["titles"]
        t1["chapters"] = [{"time": 0, "name": "Opening"},
                          {"time": "00:00:08", "name": "Middle", "poster": 10}, 16]
        t2.update({"aspect": "4:3", "audio": {"codec": "lpcm"}, "chapters": [0, 4, 8]})
        data["playlists"] = [{"id": "best", "name": "Best of",
                              "items": ["t1:2", "t2:2-3", "t1:1"], "end_action": "menu:main"}]
        data["menus"][0]["buttons"].append({"id": "pl", "label": "BEST OF", "x": 470, "y": 220,
                                            "action": "playlist:best"})
        with open(path, "w") as f:
            json.dump(data, f)
        cls.path = path
        cls.iso = os.path.join(cls.tmp, "pl.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_playlist_plays_its_ranges(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            d.activate(4)                                     # BEST OF
            seen, menu = d.trace_until_menu()
            # t1 ch2 (stops before ch3), t2 ch2-3, t1 ch1 (stops before ch2), menu
            self.assertEqual(seen, [(1, 2), (2, 2), (2, 3), (1, 1)])
            self.assertEqual(menu, 1)
            # a single title afterwards is not part of the playlist any more
            d.activate(3)                                     # SAMPLE TITLE B
            seen, menu = d.trace_until_menu()
            self.assertEqual((seen, menu), ([(2, 1), (2, 2), (2, 3)], 1))
            # and play all still plays whole titles
            d.activate(1)
            seen, menu = d.trace_until_menu()
            self.assertEqual((seen, menu), ([(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)], 1))

    def test_named_chapter_menu(self):
        from oncemore import menu as menu_mod
        from oncemore.project import load_project
        project = load_project(self.path)
        ch = project.menu("chapters")
        self.assertEqual([b.label for b in ch.buttons[:3]], ["Opening", "Middle", "Chapter 3"])
        out = os.path.join(self.tmp, "chapters.png")
        menu_mod.MenuBuilder(project, os.path.join(self.tmp, "work")).preview(ch, out)
        self.assertTrue(os.path.getsize(out) > 1000)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestMenuDesign(unittest.TestCase):
    """Rectangles, outlined / shadowed text, a font per element, a button
    with its own highlight picture, a motion chapter menu whose
    thumbnails play, and a main menu that fades in from black once."""

    @classmethod
    def setUpClass(cls):
        from oncemore.menu import find_font
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-design-")
        rc, _, err = run_cli("init", "design", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "design")
        # a ring: the highlight picture of the CHAPTERS button
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=black@0:s=40x40,format=rgba", "-vf",
                        "geq=r=255:g=255:b=255:a='if(between(hypot(X-20,Y-20),12,18),255,0)'",
                        "-frames:v", "1", os.path.join(proj, "media", "ring.png")], check=True)
        # a logo: blue, with a transparent left half
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=blue:s=80x40,format=rgba", "-vf",
                        "geq=r=0:g=0:b=255:a='if(lt(X,40),0,255)'",
                        "-frames:v", "1", os.path.join(proj, "media", "logo.png")], check=True)
        path = os.path.join(proj, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        main = data["menus"][0]
        main["shapes"] = [{"x": 100, "y": 200, "w": 300, "h": 200, "color": "#FF0000"}]
        main["images"] = [{"file": "media/logo.png", "x": 300, "y": 220, "w": 160, "h": 80},
                          {"file": "media/logo.png", "x": 0, "y": 0, "w": 80, "h": 40,
                           "hidden": True}]
        main["fade_in"] = 1
        main["buttons_at_loop"] = True        # no buttons during the fade
        main["texts"][0].update({"outline": "#000000", "outline_width": 3, "shadow": "#00000080"})
        main["buttons"][0]["font"] = find_font(text="PLAY ALL")      # an element's own font
        main["buttons"][1].update({"highlight_image": "media/ring.png", "x": 160})
        data["titles"][0]["auto_chapter_menu"].update(
            {"background_video": "media/sample_b.mp4", "duration": 4, "animated_thumbnails": True})
        with open(path, "w") as f:
            json.dump(data, f)
        cls.path = path
        cls.iso = os.path.join(cls.tmp, "design.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def builder(self):
        from oncemore import menu as menu_mod
        from oncemore.project import load_project
        project = load_project(self.path)
        return project, menu_mod.MenuBuilder(project, os.path.join(self.tmp, "work"))

    def test_shapes_and_highlight_picture(self):
        from oncemore import png4
        project, mb = self.builder()
        main = project.menu("main")
        base = mb.render_base(main)
        pixels = subprocess.run(["ffmpeg", "-v", "error", "-i", base, "-f", "rawvideo",
                                 "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        w = project.disc.width
        r, g, b = pixels[(300 * w + 380) * 3:(300 * w + 380) * 3 + 3]   # inside the panel
        self.assertTrue(r > 200 and g < 60 and b < 60, (r, g, b))

        def px(x, y):
            return tuple(pixels[(y * w + x) * 3:(y * w + x) * 3 + 3])
        r, g, b = px(420, 260)                          # the logo's opaque half, over the panel
        self.assertTrue(b > 200 and r < 60 and g < 60, (r, g, b))
        r, g, b = px(330, 260)                          # its transparent half shows the panel
        self.assertTrue(r > 200 and b < 60, (r, g, b))
        geoms = {gm.id: gm for gm in mb.layout(main)}
        ring = geoms["ch"].shape[0]
        self.assertIsInstance(ring, png4.Mask)
        x0, y0, x1, y1 = ring.bbox()
        self.assertAlmostEqual(y0, 280 + 2, delta=2)                 # the ring, at the button's y
        self.assertAlmostEqual(y1, 280 + 38, delta=2)
        self.assertLess(x0, 160 + 10)

    def test_thumbnails_play(self):
        project, mb = self.builder()
        ch = project.menu("chapters")
        inputs, graph = mb.compose(ch)
        out = subprocess.run(["ffmpeg", "-v", "error"] + inputs +
                             ["-filter_complex", graph, "-map", "[out]", "-frames:v", "40",
                              "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             cwd=mb.work, capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr[-800:])
        w, h = project.disc.width, project.disc.height
        frames = [out.stdout[i * w * h:(i + 1) * w * h] for i in (0, 39)]
        t = ch.buttons[0].thumb

        def region(f):
            return [f[y * w + x] for y in range(t.y + 5, t.y + t.h - 5, 4)
                    for x in range(t.x + 5, t.x + t.w - 5, 4)]
        a, b = region(frames[0]), region(frames[1])
        diff = sum(abs(p - q) for p, q in zip(a, b)) / len(a)
        self.assertGreater(diff, 2.0, "the chapter thumbnail did not move")

    def test_fade_in(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_0.VOB", os.path.join(self.tmp, "m.vob"))
        means = []
        for n in (0, 15, 60):                        # 0, 0.5 and 2 s (main is the first menu)
            p = subprocess.run(["ffmpeg", "-v", "error", "-i", vob, "-vf",
                                f"select=eq(n\\,{n}),scale=72:48,format=gray",
                                "-frames:v", "1", "-f", "rawvideo", "pipe:1"],
                               capture_output=True, check=True)
            means.append(sum(p.stdout) / len(p.stdout))
        self.assertLess(means[0], 20, means)          # black (video range starts at 16)
        self.assertLess(means[0] + 3, means[1], means)
        self.assertLess(means[1] + 3, means[2], means)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_buttons_wait_for_the_loop_point(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            counts = []
            d.run_until(lambda e: e == dvdnav_sim.EV_NAV_PACKET and d.domain() == "vtsm"
                        and (counts.append(d.button_count()) or counts[-1] > 0),
                        max_events=500_000)
        # the first second (the fade, about two VOBUs a second) has no buttons
        self.assertGreaterEqual(counts.count(0), 2, counts)
        self.assertEqual(counts[-1], 3)

    def test_disc_navigates(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            # the buttons wait for the end of the fade: the fade is PGC 1, played
            # once, the buttons' PGC 2 then repeats
            self.assertEqual(d.wait_menu(), 2)
            self.assertEqual(d.button_count(), 3)
            d.run_until(lambda e: [(pgc, c) for dom, pgc, c in d.cells if dom == "vtsm"][-3:]
                        == [(1, 1), (2, 1), (2, 1)], max_events=3_000_000)
            d.activate(2)
            self.assertEqual(d.wait_menu(), 3)                 # the chapter menu
            self.assertEqual(d.button_count(), 4)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestTemplates(unittest.TestCase):
    """Every menu template gives a valid menu whose buttons do not overlap,
    for the sample and for a disc with many titles, on NTSC and PAL."""

    def test_templates_lay_out(self):
        from oncemore import menu as menu_mod, templates
        from oncemore.project import build_project
        from oncemore.scaffold import sample_project
        tmp = tempfile.mkdtemp(prefix="oncemore-e2e-tpl-")
        self.addCleanup(shutil.rmtree, tmp, True)
        big = sample_project()
        big["titles"] = [dict(big["titles"][1], id=f"t{i}", name=f"A rather long title name {i}")
                         for i in range(1, 9)]
        big["playlists"] = [{"id": "pl", "name": "Highlights", "items": ["t1", "t2"]}]
        for standard in ("NTSC", "PAL"):
            for data in (sample_project(), big):
                data = json.loads(json.dumps(data))
                data["disc"]["standard"] = standard
                if "chapters" not in [m["id"] for m in data["menus"]]:
                    data["titles"][0]["auto_chapter_menu"] = {"id": "chapters", "back": "menu:main"}
                for tpl in templates.TEMPLATES:
                    data["menus"] = [m for m in data["menus"] if m["id"] == "main"]
                    data["menus"].append(templates.make_menu(tpl, data, "tpl", back="menu:main"))
                    p = build_project(data, "/v/project.oncemore.json", check_files=False)
                    mb = menu_mod.MenuBuilder(p, os.path.join(tmp, f"{standard}-{tpl}"))
                    geoms = mb.layout(p.menu("tpl"))           # raises on overlaps / empty labels
                    self.assertGreaterEqual(len(geoms), 2, (standard, tpl))


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestCacheRomPassthrough(unittest.TestCase):
    """A title with its own bitrate, AC-3 copied unchanged, DVD-ROM files on
    the disc, and a rebuild that reuses everything that did not change."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-cache-")
        rc, _, err = run_cli("init", "c", cwd=cls.tmp)
        assert rc == 0, err
        proj = cls.proj = os.path.join(cls.tmp, "c")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc2=s=640x360:r=30000/1001:d=6", "-f", "lavfi",
                        "-i", "sine=f=500:d=6", "-c:v", "mpeg4", "-c:a", "ac3", "-b:a", "320k",
                        "-ar", "48000", "-ac", "2", "-shortest",
                        os.path.join(proj, "media", "ac3.mkv")], check=True)
        os.makedirs(os.path.join(proj, "extras"))
        with open(os.path.join(proj, "extras", "README.txt"), "w") as f:
            f.write("Bonus material for computers.\n")
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            data = json.load(f)
        data["disc"]["rom_files"] = ["extras"]
        data["titles"][1]["video_bitrate"] = "3M"
        data["titles"].append({"id": "t3", "name": "AC-3 source", "source": "media/ac3.mkv",
                               "audio": {"codec": "ac3", "passthrough": True},
                               "end_action": "menu:main"})
        with open(cls.path, "w") as f:
            json.dump(data, f)
        cls.data = data
        cls.iso = os.path.join(cls.tmp, "c.iso")
        rc, out, err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.first = json_lines(out)
        cls.build_dir = cls.first[-1]["build_dir"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_title_bitrate_and_rom_files(self):
        res = self.first[-1]
        rates = {t["id"]: t["video_bps"] for t in res["titles"]}
        self.assertEqual(rates["t2"], 3_000_000)
        self.assertGreater(rates["t1"], 3_000_000)
        self.assertIn("/extras/readme.txt", [f.lower() for f in iso_list(self.iso)])

    def test_ac3_copied(self):
        t3 = os.path.join(self.build_dir, ".work", "titles", "t3.mpg")
        a = [s for s in ffprobe_streams(t3) if s["codec_type"] == "audio"]
        # the source's 320k AC-3, not a re-encode at the default 192k
        self.assertEqual([(s["codec_name"], int(s["bit_rate"])) for s in a], [("ac3", 320_000)])

    def test_rebuild_uses_the_cache(self):
        again = os.path.join(self.tmp, "again.iso")
        rc, out, err = run_cli("--json", "iso", self.path, "-o", again, "--fast", cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        steps = [e["message"] for e in json_lines(out) if e["event"] == "step"]
        self.assertEqual(sum("(cached)" in m for m in steps), 3 + 2, steps)   # 3 titles, 2 menus
        self.assertEqual(os.path.getsize(again), os.path.getsize(self.iso))
        # change one label: only that menu is rendered again
        data = json.loads(json.dumps(self.data))
        data["menus"][0]["buttons"][1]["label"] = "SCENES"
        path = os.path.join(self.proj, "changed.oncemore.json")
        with open(path, "w") as f:
            json.dump(data, f)
        rc, out, err = run_cli("--json", "iso", path, "-o", again, "--fast", cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        steps = [e["message"] for e in json_lines(out) if e["event"] == "step"]
        self.assertTrue(any(m == "Rendering menu 'main'" for m in steps), steps)
        self.assertEqual(sum("(cached)" in m for m in steps), 3 + 1, steps)

    def test_passthrough_needs_matching_ac3(self):
        data = json.loads(json.dumps(self.data))
        data["titles"][0]["audio"] = {"codec": "ac3", "passthrough": True}   # an AAC source
        path = os.path.join(self.proj, "bad.oncemore.json")
        with open(path, "w") as f:
            json.dump(data, f)
        rc, out, err = run_cli("--json", "validate", path, cwd=self.tmp)
        self.assertNotEqual(rc, 0)
        self.assertIn("only 48 kHz AC-3 can be copied", out)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestSlideshow(unittest.TestCase):
    """A title made from three pictures with cross-fades, pan & zoom and
    music: one chapter per picture, and the rendered show is reused. A
    second one fitted to two pieces of music played one after another, a
    third advanced by hand (every picture held until Next / Play)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-slides-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "s")
        for i, (src, size) in enumerate((("testsrc2", "800x600"), ("smptebars", "1280x720"),
                                         ("rgbtestsrc", "600x900"))):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"{src}=s={size}:d=1", "-frames:v", "1",
                            os.path.join(proj, "media", f"pic{i}.png")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=330:d=4",
                        os.path.join(proj, "media", "music.wav")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=660:d=2",
                        "-ac", "2", "-ar", "44100", os.path.join(proj, "media", "music2.m4a")],
                       check=True)
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            data = json.load(f)
        data["titles"].append({"id": "pics", "name": "Pictures", "end_action": "menu:main",
                               "slideshow": {"slides": [{"image": "media/pic0.png", "duration": 3},
                                                        {"image": "media/pic1.png", "duration": 2.5},
                                                        {"image": "media/pic2.png", "duration": 2}],
                                             "pan_zoom": True, "audio": "media/music.wav"}})
        # durations as proportions (1 : 3) of the music's 4 + 2 s
        data["titles"].append({"id": "fitted", "end_action": "menu:main", "slideshow": {
            "slides": [{"image": "media/pic0.png", "duration": 1},
                       {"image": "media/pic1.png", "duration": 3}],
            "audio": ["media/music.wav", "media/music2.m4a"], "fit_to_audio": True}})
        data["menus"][0]["buttons"].append({"id": "pics", "label": "PICTURES", "x": 100,
                                            "y": 380, "action": "title:pics"})
        data["menus"][0]["buttons"].append({"id": "fitted", "label": "FITTED", "x": 400,
                                            "y": 380, "action": "title:fitted"})
        data["titles"].append({"id": "byhand", "end_action": "menu:main", "slideshow": {
            "slides": [{"image": "media/pic0.png"}, {"image": "media/pic1.png"},
                       {"image": "media/pic2.png"}], "advance": "manual"}})
        data["menus"][0]["buttons"].append({"id": "byhand", "label": "BY HAND", "x": 400,
                                            "y": 320, "action": "title:byhand"})
        with open(cls.path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "s.iso")
        rc, out, err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.events = json_lines(out)
        cls.build_dir = cls.events[-1]["build_dir"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_title_streams(self):
        res = self.events[-1]
        pics = next(t for t in res["titles"] if t["id"] == "pics")
        self.assertAlmostEqual(pics["duration"], 7.5, delta=0.1)
        self.assertEqual(pics["chapters"], [0.0, 3.0, 5.5])
        mpg = os.path.join(self.build_dir, ".work", "titles", "pics.mpg")
        v = [s for s in ffprobe_streams(mpg) if s["codec_type"] == "video"]
        a = [s for s in ffprobe_streams(mpg) if s["codec_type"] == "audio"]
        self.assertEqual((v[0]["width"], v[0]["height"]), (720, 480))
        self.assertEqual(len(a), 1)            # the music, padded to the end
        steps = [e["message"] for e in self.events if e["event"] == "step"]
        self.assertTrue(any(m.startswith("Rendering slideshow 'pics' (3 pictures, 7.5s)")
                            for m in steps), steps)

    def test_fitted_to_its_music(self):
        fitted = next(t for t in self.events[-1]["titles"] if t["id"] == "fitted")
        self.assertAlmostEqual(fitted["duration"], 6.0, delta=0.1)
        self.assertEqual(fitted["chapters"], [0.0, 1.5])
        mpg = os.path.join(self.build_dir, ".work", "titles", "fitted.mpg")
        # the second piece (660 Hz) plays after the first (330 Hz)
        def tone(start):
            out = subprocess.run(
                [tools.find("ffmpeg"), "-v", "error", "-ss", str(start), "-t", "0.5", "-i", mpg,
                 "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                capture_output=True, check=True).stdout
            samples = [int.from_bytes(out[i:i + 2], "little", signed=True)
                       for i in range(0, len(out) - 1, 2)]
            return sum(1 for a, b in zip(samples, samples[1:]) if a < 0 <= b) / 0.5
        self.assertAlmostEqual(tone(1.0), 330, delta=30)
        self.assertAlmostEqual(tone(4.2), 660, delta=60)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_advanced_by_hand(self):
        byhand = next(t for t in self.events[-1]["titles"] if t["id"] == "byhand")
        self.assertEqual(byhand["chapters"], [0.0, 1.0, 2.0])      # a moment each
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            d.activate(d.button_count())                          # BY HAND
            title, _ = d.wait_title()
            seen, _ = d.trace_until_menu()
        self.assertEqual([p for t, p in seen if t == title], [1, 2, 3])
        # every picture ends in a still held until Next / Play (255)
        held = [s for s in d.stills if s[0] == "title"]
        self.assertEqual([(c, length) for _, _, c, length in held], [(1, 255), (2, 255), (3, 255)])

    def test_rendered_once(self):
        again = os.path.join(self.tmp, "again.iso")
        rc, out, err = run_cli("--json", "iso", self.path, "-o", again, "--fast", cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        steps = [e["message"] for e in json_lines(out) if e["event"] == "step"]
        self.assertFalse(any("slideshow" in m.lower() for m in steps), steps)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_chapters_on_disc(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            n = d.button_count()
            d.activate(n - 2)                               # PICTURES
            title, part = d.wait_title()
            self.assertEqual(part, 1)
            self.assertEqual(d.num_parts(title), 3)
            seen, _ = d.trace_until_menu()
            self.assertEqual([p for t, p in seen if t == title], [1, 2, 3])


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestNoTranscode(unittest.TestCase):
    """A source that already is DVD video: its picture goes on the disc as
    it is (the same MPEG-2 packets), while its sound is made anew; a source
    that is not is refused with the reasons."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-copy-")
        rc, _, err = run_cli("init", "c", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "c")
        cls.src = os.path.join(proj, "media", "dvd.mpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=s=720x480:r=30000/1001:d=4", "-f", "lavfi", "-i",
                        "sine=f=440:d=4", "-target", "ntsc-dvd", "-aspect", "16:9",
                        "-b:v", "4000000", "-c:a", "mp2", "-b:a", "192k", cls.src], check=True)
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            cls.data = json.load(f)
        cls.data["titles"][1].update({"source": "media/dvd.mpg", "chapters": [0, 2],
                                      "transcode": False})
        with open(cls.path, "w") as f:
            json.dump(cls.data, f)
        cls.iso = os.path.join(cls.tmp, "c.iso")
        cls.rc, cls.out, cls.err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast",
                                           "--keep-work", cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def video_md5(self, path):
        return subprocess.run([tools.find("ffmpeg"), "-v", "error", "-i", path, "-map", "0:v",
                               "-c", "copy", "-f", "md5", "-"],
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_picture_copied(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        build_dir = json_lines(self.out)[-1]["build_dir"]
        mpg = os.path.join(build_dir, ".work", "titles", "t2.mpg")
        self.assertEqual(self.video_md5(mpg), self.video_md5(self.src))
        audio = [s for s in ffprobe_streams(mpg) if s["codec_type"] == "audio"]
        self.assertEqual(audio[0]["codec_name"], "ac3")          # the title's audio setting
        steps = " ".join(e.get("message", "") for e in json_lines(self.out))
        self.assertNotIn("error", steps.lower())

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_chapters_on_disc(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            n = d.button_count()
            d.activate(n)                                        # SAMPLE TITLE B
            title, part = d.wait_title()
            self.assertEqual((part, d.num_parts(title)), (1, 2))

    def test_not_dvd_video_is_refused(self):
        data = json.loads(json.dumps(self.data))
        data["titles"][0]["transcode"] = False                   # an MP4 (H.264)
        path = os.path.join(self.tmp, "c", "bad.oncemore.json")
        with open(path, "w") as f:
            json.dump(data, f)
        rc, out, err = run_cli("--json", "validate", path, cwd=self.tmp)
        self.assertNotEqual(rc, 0)
        self.assertIn("titles[0].transcode", out + err)
        self.assertIn("not MPEG-2", out + err)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestScanModes(unittest.TestCase):
    """23.976p film gets soft 3:2 pulldown, 1080i and 59.94p sources stay
    interlaced, and a 25 fps source is converted to progressive 29.97."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-scan-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "s")
        media = os.path.join(proj, "media")

        def make(name, src, vf, extra):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src,
                            "-f", "lavfi", "-i", "sine=f=440:d=6"] + (["-vf", vf] if vf else [])
                           + extra + ["-c:a", "aac", "-shortest", os.path.join(media, name)],
                           check=True)
        make("film.mp4", "testsrc2=s=1280x720:r=24000/1001:d=6", None, ["-c:v", "libx264"])
        make("i1080.ts", "testsrc2=s=1920x1080:r=60000/1001:d=6",
             "interlace=scan=tff,setfield=tff",
             ["-c:v", "mpeg2video", "-b:v", "12M", "-flags", "+ilme+ildct"])
        make("p60.mp4", "testsrc2=s=1280x720:r=60000/1001:d=6", None, ["-c:v", "libx264"])
        # film telecined to 29.97i (3:2 pulldown burnt into the fields), and the film itself
        cls.film720 = os.path.join(cls.tmp, "film720.mkv")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc2=s=720x480:r=24000/1001:d=6", "-vf", "setsar=32/27",
                        "-pix_fmt", "yuv420p",
                        "-c:v", "ffv1", cls.film720], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cls.film720, "-f", "lavfi",
                        "-i", "sine=f=440:d=6", "-vf", "telecine=first_field=top:pattern=23",
                        "-c:v", "mpeg2video", "-q:v", "2", "-flags", "+ilme+ildct", "-aspect", "16:9",
                        "-c:a", "mp2", "-shortest", os.path.join(media, "tc.mpg")], check=True)
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            data = json.load(f)
        data["titles"] = [
            {"id": "film", "source": "media/film.mp4", "chapters": [0, 2.5, 5],
             "end_action": "menu:main"},
            {"id": "i1080", "source": "media/i1080.ts", "end_action": "menu:main"},
            {"id": "p60", "source": "media/p60.mp4", "end_action": "menu:main"},
            {"id": "pal", "source": "media/sample_b.mp4", "end_action": "menu:main"},
            {"id": "tc", "source": "media/tc.mpg", "scan": "ivtc", "end_action": "menu:main"},
        ]
        data["menus"] = [{"id": "main", "buttons": [
            {"id": t["id"], "label": t["id"].upper(), "x": 100, "y": 120 + 60 * k,
             "action": f"title:{t['id']}"} for k, t in enumerate(data["titles"])]}]
        data["disc"]["first_play"] = "menu:main"
        with open(cls.path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "s.iso")
        rc, out, err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]
        cls.work = os.path.join(cls.result["build_dir"], ".work", "titles")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def frames(self, tid):
        out = subprocess.run(
            [tools.find("ffprobe"), "-v", "error", "-select_streams", "v", "-show_frames",
             "-show_entries", "frame=repeat_pict,interlaced_frame,top_field_first",
             "-of", "json", os.path.join(self.work, f"{tid}.mpg")],
            capture_output=True, text=True, check=True).stdout
        return json.loads(out)["frames"]

    def test_modes_reported(self):
        modes = {t["id"]: t["scan"] for t in self.result["titles"]}
        self.assertEqual(modes, {"film": "pulldown", "i1080": "interlaced",
                                 "p60": "interlaced", "pal": "progressive", "tc": "pulldown"})

    def test_inverse_telecine(self):
        """The film frames come back whole: 23.976 frames a second with soft
        pulldown flags, and closer to the original film than deinterlacing
        the telecined fields would be."""
        fr = self.frames("tc")
        self.assertAlmostEqual(len(fr), 144, delta=2)
        self.assertEqual([f["repeat_pict"] for f in fr][:4], [1, 0, 1, 0])
        def psnr(args):
            out = subprocess.run(["ffmpeg", "-v", "info"] + args + ["-i", self.film720, "-lavfi",
                                  "[0:v]setpts=N/(24000/1001)/TB[a];[1:v]setpts=N/(24000/1001)/TB[b];"
                                  "[a][b]psnr", "-f", "null", "-"], capture_output=True, text=True).stderr
            return float(re.findall(r"average:([0-9.]+)", out)[-1])
        ours = psnr(["-i", os.path.join(self.work, "tc.mpg")])
        naive = os.path.join(self.tmp, "naive.mkv")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(self.tmp, "s", "media", "tc.mpg"),
                        "-vf", "bwdif,fps=24000/1001", "-c:v", "ffv1", naive], check=True)
        self.assertGreater(ours, psnr(["-i", naive]) + 2.0)     # (measured: +4 dB)

    def test_soft_pulldown(self):
        fr = self.frames("film")
        # every film frame once (6 s x 23.976), shown as 3, 2, 3, 2 fields
        self.assertAlmostEqual(len(fr), 144, delta=2)
        rff = [f["repeat_pict"] for f in fr]
        self.assertEqual(rff[:8], [1, 0, 1, 0, 1, 0, 1, 0])
        tff = [f["top_field_first"] for f in fr]
        self.assertEqual(tff[:8], [1, 0, 0, 1, 1, 0, 0, 1])
        v = [s for s in ffprobe_streams(os.path.join(self.work, "film.mpg"))
             if s["codec_type"] == "video"][0]
        num, den = map(int, v["avg_frame_rate"].split("/"))
        self.assertAlmostEqual(num / den, 29.97, delta=0.1)   # shown at the NTSC rate
        fmt = json.loads(subprocess.run(
            [tools.find("ffprobe"), "-v", "error", "-show_format", "-of", "json",
             os.path.join(self.work, "film.mpg")], capture_output=True, text=True).stdout)
        self.assertAlmostEqual(float(fmt["format"]["duration"]), 6.0, delta=0.15)

    def test_interlaced(self):
        for tid in ("i1080", "p60"):
            fr = self.frames(tid)
            self.assertAlmostEqual(len(fr), 180, delta=2, msg=tid)     # 29.97 frames/s
            self.assertTrue(all(f["interlaced_frame"] == 1 and f["top_field_first"] == 1
                                for f in fr), tid)
        fr = self.frames("pal")
        self.assertTrue(all(f["interlaced_frame"] == 0 for f in fr))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_film_chapters_on_disc(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            d.activate(1)
            title, part = d.wait_title()
            self.assertEqual((part, d.num_parts(title)), (1, 3))
            seen, _ = d.trace_until_menu()
            self.assertEqual([p for t, p in seen if t == title], [1, 2, 3])


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestSubtitleFormats(unittest.TestCase):
    """A WebVTT track whose first cue is placed at the top, and an ASS track
    with a red sign, rendered onto a disc."""

    VTT = ("WEBVTT\n\n00:01.000 --> 00:03.000 line:0\nAt the top\n\n"
           "00:04.000 --> 00:06.000\nAt the bottom\n")
    ASS = ("[Script Info]\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, Alignment\n"
           "Style: Default,Arial,20,&H00FFFFFF,2\n\n[Events]\n"
           "Format: Layer, Start, End, Style, Text\n"
           "Dialogue: 0,0:00:01.00,0:00:03.00,Default,{\\c&H0000FF&}A red sign\n"
           "Dialogue: 0,0:00:04.00,0:00:06.00,Default,White again\n")

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-subfmt-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "s")
        for name, text in (("en.vtt", cls.VTT), ("signs.ass", cls.ASS)):
            with open(os.path.join(proj, "media", name), "w", encoding="utf-8") as f:
                f.write(text)
        path = os.path.join(proj, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["titles"][1]["subtitles"] = [{"file": "media/en.vtt", "lang": "en"},
                                          {"file": "media/signs.ass", "lang": "ja",
                                           "position": "top", "color": "#FFFF00"}]
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "s.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.subs = os.path.join(json_lines(out)[-1]["build_dir"], ".work", "subs", "t2")
        cls.H = 480

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def spus(self, stream):
        import re as _re
        xml = [f for f in os.listdir(self.subs) if f.startswith(f"sub{stream}_")
               and f.endswith(".spumux.xml")][0]
        with open(os.path.join(self.subs, xml)) as f:
            return [(m[0], int(m[1])) for m in
                    _re.findall(r'image="([^"]+)" xoffset="\d+" yoffset="(\d+)"', f.read())]

    def test_positions(self):
        (top, y0), (bottom, y1) = self.spus(0)
        self.assertLess(y0, self.H / 3)          # line:0 -> top
        self.assertGreater(y1, self.H / 2)
        (_, a), (_, b) = self.spus(1)            # the whole ASS track is placed at the top
        self.assertLess(max(a, b), self.H / 3)

    def test_colours(self):
        from oncemore import png4
        (red, _), (white, _) = self.spus(1)
        def palette(name):
            with open(os.path.join(self.subs, name), "rb") as f:
                return png4.read_indexed_png(f.read())[1]
        pal_red, pal_track = palette(red), palette(white)
        self.assertEqual(tuple(pal_red[1][:3]), (255, 0, 0))      # the cue's own colour
        self.assertEqual(tuple(pal_track[1][:3]), (255, 255, 0))  # the track colour

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_streams_on_disc(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            d.activate(3)
            self.assertEqual(d.wait_title(), (2, 1))
            self.assertEqual([d.subtitle_lang(0), d.subtitle_lang(1)], ["en", "ja"])


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestClips(unittest.TestCase):
    """Titles made of clips: parts of three files of different sizes, rates
    and sound (one without any) and a 4:3 still picture filling the 16:9
    frame, joined into one title with a chapter at every clip, and two film
    clips joined with soft pulldown."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-clips-")
        rc, _, err = run_cli("init", "c", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "c")
        media = os.path.join(proj, "media")

        def ff(*args):
            subprocess.run(["ffmpeg", "-v", "error", "-y"] + list(args), check=True)
        ff("-f", "lavfi", "-i", "mandelbrot=s=640x360:r=25", "-t", "2", "-c:v", "mpeg4",
           os.path.join(media, "silent.mp4"))
        # green, with red bands at the top and bottom that filling 16:9 cuts off
        ff("-f", "lavfi", "-i", "color=c=0x00C000:s=400x300", "-vf",
           "drawbox=y=0:w=iw:h=30:color=red:t=fill,drawbox=y=270:w=iw:h=30:color=red:t=fill",
           "-frames:v", "1", os.path.join(media, "still.png"))
        for name, size, tone in (("film1.mp4", "1280x720", 300), ("film2.mp4", "1920x1080", 500)):
            ff("-f", "lavfi", "-i", f"testsrc2=s={size}:r=24000/1001:d=3", "-f", "lavfi", "-i",
               f"sine=f={tone}:d=3", "-c:v", "libx264", "-c:a", "aac", "-shortest",
               os.path.join(media, name))
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            data = json.load(f)
        data["titles"] = [
            {"id": "mix", "end_action": "menu:main", "clips": [
                {"source": "media/sample_a.mp4", "in": 2, "out": 5},
                {"source": "media/silent.mp4"},
                {"source": "media/sample_b.mp4", "out": "00:00:03"},
                {"source": "media/still.png", "duration": 1.5, "fit": "fill"}]},
            {"id": "film", "end_action": "menu:main", "audio": {"codec": "lpcm"},
             "chapters": [0], "clips": [{"source": "media/film1.mp4"},
                                        {"source": "media/film2.mp4", "in": 0.5}]},
        ]
        data["menus"] = [{"id": "main", "buttons": [
            {"id": "mix", "label": "MIX", "x": 100, "y": 120, "action": "title:mix",
             # 4 s into the title: inside the silent clip
             "thumbnail": {"x": 400, "y": 100, "w": 160, "h": 90, "time": 4}},
            {"id": "film", "label": "FILM", "x": 100, "y": 300, "action": "title:film"}]}]
        data["disc"]["first_play"] = "menu:main"
        with open(cls.path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "c.iso")
        rc, out, err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]
        cls.work = os.path.join(cls.result["build_dir"], ".work")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def frames(self, tid):
        out = subprocess.run(
            [tools.find("ffprobe"), "-v", "error", "-select_streams", "v", "-count_frames",
             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0",
             os.path.join(self.work, "titles", f"{tid}.mpg")],
            capture_output=True, text=True, check=True).stdout
        return int(out.strip().strip(","))

    def volume(self, tid, start, end):
        err = subprocess.run(
            [tools.find("ffmpeg"), "-v", "info", "-ss", str(start), "-to", str(end), "-i",
             os.path.join(self.work, "titles", f"{tid}.mpg"), "-vn", "-af", "volumedetect",
             "-f", "null", "-"], capture_output=True, text=True).stderr
        return float(re.search(r"mean_volume: (-?[\d.]+) dB", err).group(1))

    def test_summary(self):
        mix, film = self.result["titles"]
        f = 1001 / 30000
        self.assertEqual([c["duration"] for c in mix["clips"]],
                         [round(90 * f, 6), round(60 * f, 6), round(90 * f, 6), round(45 * f, 6)])
        self.assertEqual(mix["chapters"], [0.0, round(90 * f, 6), round(150 * f, 6),
                                           round(240 * f, 6)])
        self.assertEqual(mix["scan"], "progressive")
        self.assertEqual(film["scan"], "pulldown")
        self.assertEqual(film["chapters"], [0.0])           # its own chapters are kept

    def test_joined_picture_and_sound(self):
        self.assertEqual(self.frames("mix"), 285)             # 3 + 2 + 3 + 1.5 s at 29.97
        self.assertLess(self.volume("mix", 8.2, 9.4), -80)    # the picture is silent
        self.assertLess(self.volume("mix", 3.2, 4.8), -80)    # the clip without sound
        self.assertGreater(self.volume("mix", 0.2, 2.8), -40)
        self.assertGreater(self.volume("mix", 5.2, 7.8), -40)
        self.assertEqual(self.frames("film"), 132)            # 72 + 60 film frames

    def test_thumbnail_from_the_clip_playing(self):
        def mean(path, at=None):
            out = subprocess.run(
                [tools.find("ffmpeg"), "-v", "error"] + (["-ss", str(at)] if at else []) +
                ["-i", path, "-frames:v", "1", "-vf", "scale=1:1:flags=area", "-f", "rawvideo",
                 "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
            return list(out[:3])
        thumb = mean(os.path.join(self.work, "menus", "main.mix.thumb.png"))
        media = os.path.join(os.path.dirname(self.path), "media")
        # 4 s into the title is 1 s into the second clip: the purple fractal,
        # not the grey test pattern of the first file
        purple = lambda c: c[0] - c[1] > 20 and c[2] - c[1] > 20  # noqa: E731
        self.assertTrue(purple(mean(os.path.join(media, "silent.mp4"), 0.997)))
        self.assertFalse(purple(mean(os.path.join(media, "sample_a.mp4"), 4)))
        self.assertTrue(purple(thumb), thumb)

    def test_still_fills_the_frame(self):
        # 16 x 9 samples of a frame of the picture: all green, no bars, no red
        out = subprocess.run(
            [tools.find("ffmpeg"), "-v", "error", "-ss", "8.8", "-i",
             os.path.join(self.work, "titles", "mix.mpg"), "-frames:v", "1", "-vf",
             "scale=16:9:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True).stdout
        px = [tuple(out[i:i + 3]) for i in range(0, 16 * 9 * 3, 3)]
        green = [p for p in px if p[1] > 120 and p[0] < 80 and p[2] < 80]
        self.assertEqual(len(green), len(px), px)

    def test_external_iso_tools_still_work(self):
        from oncemore import iso
        disc = os.path.join(self.result["build_dir"], "disc")
        for name in ("genisoimage", "mkisofs", "hdiutil"):
            if tools.iso_tool(name)[0] is None:
                continue
            out = os.path.join(self.tmp, f"{name}.iso")
            info = iso.make_iso(disc, out, "SAMPLE_DISC", name)
            self.assertEqual((info["tool"], info["udf"]), (name, True))
            self.assertEqual(sorted(f for f in iso_list(out) if "VIDEO_TS" in f),
                             sorted(f for f in iso_list(self.iso) if "VIDEO_TS" in f))
            break
        else:
            self.skipTest("no external UDF ISO tool")

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_chapters_on_disc(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            d.activate(1)
            title, part = d.wait_title()
            self.assertEqual((part, d.num_parts(title)), (1, 4))
            seen, _ = d.trace_until_menu()
            self.assertEqual([p for t, p in seen if t == title], [1, 2, 3, 4])



@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestTranscodeNow(unittest.TestCase):
    """`oncemore transcode` encodes titles ahead of the build, and the build
    reuses them."""

    def test_transcode_then_build(self):
        tmp = tempfile.mkdtemp(prefix="oncemore-e2e-tc-")
        try:
            rc, _, err = run_cli("init", "t", cwd=tmp)
            self.assertEqual(rc, 0, err)
            proj = os.path.join(tmp, "t", "project.oncemore.json")
            rc, out, err = run_cli("--json", "transcode", proj, "--status", "--fast")
            self.assertEqual(json_lines(out)[-1]["titles"], {"t1": False, "t2": False})
            rc, out, err = run_cli("--json", "transcode", proj, "--title", "t2", "--fast")
            self.assertEqual(rc, 0, err + out)
            self.assertEqual(json_lines(out)[-1]["titles"], {"t2": "transcoded"})
            rc, out, err = run_cli("--json", "transcode", proj, "--status", "--fast")
            self.assertEqual(json_lines(out)[-1]["titles"], {"t1": False, "t2": True})
            rc, out, err = run_cli("--json", "transcode", proj, "--title", "t2", "--fast")
            self.assertEqual(json_lines(out)[-1]["titles"], {"t2": "cached"})
            rc, out, err = run_cli("--json", "iso", proj, "-o", os.path.join(tmp, "t.iso"),
                                   "--fast")
            self.assertEqual(rc, 0, err + out)
            steps = [e.get("message", "") for e in json_lines(out) if e["event"] == "step"]
            self.assertIn("Title 't2' unchanged (cached)", steps)
            self.assertTrue(any(m.startswith("Encoding title 't1'") for m in steps), steps)
            rc, out, err = run_cli("--json", "transcode", proj, "--title", "nope")
            self.assertNotEqual(rc, 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
