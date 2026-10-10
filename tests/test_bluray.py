"""Blu-ray output: the BDMV navigation files, and a built disc read back
with libbluray (the player library of VLC, mpv and Kodi)."""

import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest

from oncemore import bluray, pgs
from oncemore.errors import ProjectError
from oncemore.project import build_project

from .helpers import have, run_cli

try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None
try:
    from . import udfread_sim
    LIBUDFREAD = udfread_sim.load_library()
except Exception:  # pragma: no cover
    LIBUDFREAD = None


def project(**extra):
    data = {"version": 1,
            "disc": {"label": "BD", "standard": "NTSC", "aspect": "16:9"},
            "titles": [{"id": "one", "source": "a.mp4", "chapters": [0, 2]},
                       {"id": "two", "source": "b.mp4"}]}
    for k, v in extra.items():
        if k == "disc":
            data["disc"].update(v)
        else:
            data[k] = v
    return build_project(data, "/x/project.oncemore.json", check_files=False)


def commands(obj):
    """(kind, operand) of every command of a movie object."""
    out = []
    for c in obj:
        b0, b1 = c[0], c[1]
        dst = struct.unpack(">I", c[4:8])[0]
        out.append({(0x22, 0x80): "play_pl", (0x21, 0x81): "jump_title"}[(b0, b1)] + f" {dst}")
    return out


class TestNavigationFiles(unittest.TestCase):
    def test_titles_playlists_and_play_all(self):
        p = project(disc={"first_play": "title:two", "title_key": "playall"},
                    titles=[{"id": "one", "source": "a.mp4", "end_action": "title:two"},
                            {"id": "two", "source": "b.mp4"}],
                    playlists=[{"id": "pl", "items": ["one:1", "two"], "end_action": "title:one"}])
        titles, numbers = bluray.disc_titles(p)
        self.assertEqual([k for k, _, _ in titles], ["title", "title", "playlist", "playall"])
        self.assertEqual(numbers, {"title:one": 1, "title:two": 2, "playlist:pl": 3, "playall": 4})
        objects, first, top = bluray.navigation(p)
        self.assertEqual([commands(o) for o in objects], [
            ["play_pl 1", "jump_title 2"],      # one, then two
            ["play_pl 2"],                      # two stops
            ["play_pl 3", "jump_title 1"],      # the playlist, then title one
            ["play_pl 4"],                      # play all ends like its last title
            ["jump_title 2"],                   # first play: title two
            ["jump_title 4"],                   # top menu key: play all
        ])
        self.assertEqual((first, top), (4, 5))

    def test_menus_fall_back_to_the_first_title(self):
        p = project(menus=[{"id": "m", "buttons": [{"id": "b", "label": "Play",
                                                    "x": 100, "y": 100,
                                                    "action": "title:two"}]}])
        objects, first, top = bluray.navigation(p)
        # titles end at the menu on a DVD; without menus they stop
        self.assertEqual(commands(objects[0]), ["play_pl 1"])
        self.assertEqual(commands(objects[first]), ["jump_title 1"])
        self.assertEqual(commands(objects[top]), ["jump_title 1"])

    def test_movie_object_file(self):
        data = bluray.movie_objects([[bluray.play_pl(1)], [bluray.jump_title(1)]])
        self.assertEqual(data[:8], b"MOBJ0200")
        length, _, n = struct.unpack(">IIH", data[40:50])
        self.assertEqual((length, n), (len(data) - 44, 2))
        flags, ncmd = struct.unpack(">HH", data[50:54])
        self.assertEqual((flags >> 15, ncmd), (1, 1))
        # Play PlayList 1: one immediate operand, branch group, play sub-group
        self.assertEqual(data[54:66], bytes([0x22, 0x80, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]))

    def test_ep_map_coarse_and_fine_entries(self):
        # three key frames; the third crosses a 2^17 packet boundary
        entries = [(126000, 10, 50000), (126000 + 45045, 60000, 300000),
                   (126000 + 90090, 0x20000 + 5, 2_000_000)]
        data = bluray.ep_map(entries)
        self.assertEqual(data[:2], b"\x00\x01")
        pid, bits, start = struct.unpack(">H6sI", data[2:14])
        bits = int.from_bytes(bits, "big")
        self.assertEqual(pid, bluray.VIDEO_PID)
        self.assertEqual(bits >> 34 & 0xF, 1)                      # EP_stream_type video
        n_coarse, n_fine = bits >> 18 & 0xFFFF, bits & 0x3FFFF
        self.assertEqual((n_coarse, n_fine, start), (2, 3, 14))
        one = data[start:]
        fine_start = struct.unpack(">I", one[:4])[0]
        coarse = [struct.unpack(">II", one[4 + 8 * i:12 + 8 * i]) for i in range(n_coarse)]
        self.assertEqual([c[0] >> 14 for c in coarse], [0, 2])     # ref to the fine entry
        self.assertEqual([c[1] for c in coarse], [10, 0x20000 + 5])
        fine = [struct.unpack(">I", one[fine_start + 4 * i:fine_start + 4 * i + 4])[0]
                for i in range(n_fine)]
        self.assertEqual([f >> 28 & 7 for f in fine], [1, 3, 7])  # key picture sizes
        for (pts, spn, _), c, f in zip(entries, [coarse[0]] * 2 + [coarse[1]], fine):
            # the way libbluray puts the time and place back together
            self.assertEqual(((c[0] & 0x3FFF) & ~1) << 18 | (f >> 17 & 0x7FF) << 8, pts >> 1 & ~0xFF)
            self.assertEqual((c[1] & ~0x1FFFF) + (f & 0x1FFFF), spn)

    def test_plan_caps_the_rate_to_fit(self):
        hour = 3600
        plan = bluray.plan([(hour, 640_000)], bluray.CAPACITY["BD25"])
        self.assertEqual(plan["max_bps"], bluray.MAX_VIDEO_BPS)
        plan = bluray.plan([(4 * hour, 640_000)], bluray.CAPACITY["BD25"])
        self.assertLess(plan["max_bps"], 14_000_000)
        self.assertLessEqual(plan["estimated_bytes"], bluray.CAPACITY["BD25"])
        with self.assertRaises(ProjectError):
            bluray.plan([(20 * hour, 640_000)], bluray.CAPACITY["BD25"])

    def test_languages(self):
        self.assertEqual([bluray.lang3(c) for c in ("ja", "en", "DE", None, "xx")],
                         ["jpn", "eng", "ger", "und", "und"])

    def test_disc_size_setting(self):
        self.assertEqual(project().disc.bluray_target, "BD25")
        self.assertEqual(project(disc={"bluray": {"target": "BD50"}}).disc.bluray_target, "BD50")
        with self.assertRaises(ProjectError):
            project(disc={"bluray": {"target": "BD100"}})


def ffmpeg_has_x264():
    if not have("ffmpeg", "ffprobe"):
        return False
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                         text=True).stdout
    return "libx264" in out


@unittest.skipUnless(ffmpeg_has_x264(), "needs ffmpeg with libx264 and ffprobe")
class TestBlurayBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-bd-")
        d = cls.tmp

        def media(name, size, rate, seconds, freq):
            subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y",
                            "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate}:duration={seconds}",
                            "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=48000:duration={seconds}",
                            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
                            os.path.join(d, name)], check=True)
        media("a.mp4", "720x480", "30000/1001", 6, 440)
        media("b.mp4", "640x360", "24000/1001", 4, 660)
        with open(os.path.join(d, "one.srt"), "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,500 --> 00:00:01,800\n字幕のテスト\n\n"
                    "2\n00:00:01,900 --> 00:00:03,000\nSecond line\ntwo rows\n")
        cls.project = {
            "version": 1,
            "disc": {"label": "BD_TEST", "standard": "NTSC", "aspect": "16:9",
                     "first_play": "title:one", "title_key": "playall"},
            "titles": [
                {"id": "one", "source": "a.mp4", "chapters": [0, 2, 4], "end_action": "title:two",
                 "audio_tracks": [{"lang": "en"}, {"source": "b.mp4", "lang": "ja"}],
                 "subtitles": [{"file": "one.srt", "lang": "ja", "default": True},
                               {"file": "one.srt", "lang": "en", "color": "#FFFF00"}]},
                {"id": "two", "source": "b.mp4", "chapters": [0, 1.5], "audio": {"codec": "lpcm"}},
            ],
            "playlists": [{"id": "pl", "items": ["two", "one:2"]}],
        }
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump(cls.project, f)
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--format", "bluray",
                                                 "--fast", "--json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)

    def test_folder_layout(self):
        names = {os.path.relpath(os.path.join(r, f), self.out)
                 for r, _, fs in os.walk(self.out) for f in fs}
        for rel in ("index.bdmv", "MovieObject.bdmv", "PLAYLIST/00001.mpls",
                    "PLAYLIST/00004.mpls", "CLIPINF/00001.clpi", "CLIPINF/00002.clpi"):
            self.assertIn(f"BDMV/{rel}", names)
            if not rel.startswith("STREAM"):
                self.assertIn(f"BDMV/BACKUP/{rel}", names)
        self.assertIn("BDMV/STREAM/00002.m2ts", names)
        for d in ("CERTIFICATE/BACKUP", "BDMV/AUXDATA", "BDMV/JAR", "BDMV/BDJO"):
            self.assertTrue(os.path.isdir(os.path.join(self.out, d)), d)
        self.assertFalse(os.path.exists(os.path.join(self.out, ".work")))
        result = json.loads(self.stdout.splitlines()[-1])
        self.assertEqual(result["event"], "result")
        self.assertEqual(result["bd_titles"], 4)
        self.assertEqual(result["disc"]["format"], "bluray")

    def test_streams(self):
        p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                            os.path.join(self.out, "BDMV", "STREAM", "00001.m2ts")],
                           capture_output=True, text=True, check=True)
        streams = json.loads(p.stdout)["streams"]
        v = streams[0]
        self.assertEqual((v["codec_name"], v["width"], v["height"], v["id"]),
                         ("h264", 1920, 1080, "0x1011"))
        self.assertEqual([(s["codec_name"], s["id"]) for s in streams[1:]],
                         [("ac3", "0x1100"), ("ac3", "0x1101"),
                          ("hdmv_pgs_subtitle", "0x1200"), ("hdmv_pgs_subtitle", "0x1201")])
        with open(os.path.join(self.out, "BDMV", "STREAM", "00002.m2ts"), "rb") as f:
            self.assertEqual(f.read(192 * 2)[4], 0x47)       # 192-byte source packets
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                            "stream=codec_name,id", "-of", "csv=p=0",
                            os.path.join(self.out, "BDMV", "STREAM", "00002.m2ts")],
                           capture_output=True, text=True, check=True)
        self.assertEqual(set(p.stdout.split()), {"pcm_bluray,0x1100"})

    @unittest.skipUnless(LIBBLURAY, "libbluray not installed")
    def test_libbluray_reads_the_titles(self):
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            info = disc.info()
            self.assertTrue(info["bluray"])
            self.assertEqual((info["hdmv_titles"], info["first_play"], info["top_menu"]),
                             (4, True, True))
            one, two, pl, every = (disc.playlist(n) for n in (1, 2, 3, 4))
        frame = 1001 / 30000
        self.assertAlmostEqual(one["duration"], 6, delta=3 * frame)
        self.assertEqual(len(one["chapters"]), 3)
        for got, want in zip(one["chapters"], (0, 2, 4)):
            self.assertAlmostEqual(got, want, delta=frame)      # on the frame made a key frame
        self.assertEqual(one["video"], [(0x1B, 4, 4)])           # H.264 1080i 29.97
        self.assertEqual([(c, lang) for c, _, lang in one["audio"]],
                         [(0x81, "eng"), (0x81, "jpn")])
        self.assertEqual(one["pg"], [(0x90, "jpn"), (0x90, "eng")])
        self.assertEqual(two["pg"], [])
        self.assertEqual(two["video"], [(0x1B, 6, 1)])           # 1080p 23.976 (film)
        self.assertEqual(two["audio"], [(0x80, 3, "und")])       # LPCM stereo
        self.assertAlmostEqual(two["duration"], 4, delta=3 * 1001 / 24000)
        # the playlist: title two, then chapter 2 of title one (2 s)
        self.assertAlmostEqual(pl["duration"], two["duration"] + 2, delta=0.1)
        self.assertEqual(len(pl["chapters"]), 3)
        self.assertAlmostEqual(every["duration"], one["duration"] + two["duration"], delta=0.05)
        self.assertEqual(len(every["chapters"]), 5)

    @unittest.skipUnless(LIBBLURAY, "libbluray not installed")
    def test_libbluray_plays_from_first_play(self):
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            disc.info()
            events = [e for e in disc.play() if e[0] != "title" or e[1] != 0xFFFF]
        # title one shows its default subtitles (track 1) from the start
        start = events.index(("title", 1))
        self.assertEqual(events[start + 1:start + 3], [("subtitles_shown", 1),
                                                       ("subtitle_stream", 1)])
        events = [e for e in events if not e[0].startswith("subtitle")]
        # first play starts title one, its end action starts title two, which stops
        self.assertEqual(events, [("title", 1), ("playlist", 1), ("chapter", 1), ("chapter", 2),
                                  ("chapter", 3), ("end", 0), ("title", 2), ("playlist", 2),
                                  ("chapter", 1), ("chapter", 2), ("end", 0)])

    def test_subtitles(self):
        m2ts = os.path.join(self.out, "BDMV", "STREAM", "00001.m2ts")
        # (ffmpeg writes the .sup on the title's time line: the video starts at 0)
        sup = os.path.join(self.tmp, "track1.sup")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", m2ts, "-map", "0:s:1", "-c", "copy",
                        "-f", "sup", sup], check=True)
        with open(sup, "rb") as f:
            sets = pgs.decode(f.read())
        shown = [(round(pts / 90000, 2), pics, pal) for pts, pics, pal in sets]
        # nothing at the start; cue 1 from 0.5 s, cleared 0.2 s before cue 2 at
        # 1.9 s, which ends at 3 s
        self.assertEqual([(t, len(p)) for t, p, _ in shown],
                         [(0.0, 0), (0.5, 1), (1.7, 0), (1.9, 1), (3.0, 0)])
        x, y, w, h, px = shown[3][1][0]
        self.assertGreater(y, 1080 // 2)                    # at the bottom, in the HD frame
        self.assertTrue(80 < w < 1920 and h > 60)           # two lines
        pal = shown[3][2]
        used = set(px) - {0}
        fill = max(used)                                    # the fill, fully opaque
        y_, cb, cr = pgs.ycbcr((255, 255, 0))
        self.assertEqual(pal[fill], (y_, cr, cb, 255))      # yellow (Y, Cr, Cb, alpha)

    @unittest.skipUnless(LIBBLURAY and LIBUDFREAD, "libbluray / libudfread not installed")
    def test_disc_image(self):
        iso = os.path.join(self.tmp, "bd.iso")
        rc, out, err = run_cli("iso", self.tmp, "-o", iso, "--format", "bluray", "--fast",
                               "--json")
        self.assertEqual(rc, 0, err + out)
        result = json.loads(out.splitlines()[-1])
        self.assertEqual((result["iso_udf"], result["iso_bytes"]),
                         ("2.50", os.path.getsize(iso)))
        # the titles were encoded once: the image reuses them from the cache
        self.assertIn("unchanged (cached)", out)
        with udfread_sim.Image(LIBUDFREAD, iso) as image:
            self.assertEqual(image.volume_id(), "BD_TEST")
            with open(os.path.join(self.out, "BDMV", "PLAYLIST", "00001.mpls"), "rb") as f:
                self.assertEqual(image.read("/BDMV/PLAYLIST/00001.mpls"), f.read())
            stream = image.read("/BDMV/STREAM/00001.m2ts")
            self.assertEqual(len(stream) % 192, 0)
            self.assertEqual(stream[4], 0x47)
        with bluray_sim.Disc(LIBBLURAY, iso) as disc:
            self.assertEqual(disc.info()["hdmv_titles"], 4)
            self.assertEqual(len(disc.playlist(1)["chapters"]), 3)
            events = [e for e in disc.play() if e[0] in ("title", "playlist") and e[1] != 0xFFFF]
        self.assertEqual(events[:2], [("title", 1), ("playlist", 1)])
        self.assertIn(("title", 2), events)


if __name__ == "__main__":
    unittest.main()
