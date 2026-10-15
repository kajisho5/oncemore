"""DTS sound copied from the sources (audio.codec "dts").

The project field, the DVD (its DTS audio, read back by libdvdnav;
the stream's bytes unchanged) and the Blu-ray (DTS in the transport stream
and the clip's stream attributes, read back by libbluray).
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from unittest import mock

from oncemore import author, bluray, build, encode, report, tools
from oncemore._vendor.bdmvkit.m2ts import stream_pids
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have, json_lines, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None
try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None


def project(data):
    return build_project(data, "/virtual/project.oncemore.json", check_files=False)


def ffmpeg_has(kind, name):
    try:
        out = subprocess.run([tools.find("ffmpeg"), "-hide_banner", f"-{kind}"],
                             capture_output=True, text=True).stdout
    except Exception:
        return False
    return any(line.split()[1:2] == [name] for line in out.splitlines() if line.strip())


def ffmpeg_has_bsf(name):
    try:
        out = subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-bsfs"],
                             capture_output=True, text=True).stdout
    except Exception:
        return False
    return name in out.split()


# (ffmpeg's DTS encoder makes the test sources; the build only copies them)
DTS_OK = have("ffmpeg", "ffprobe") and ffmpeg_has("encoders", "dca") and \
    ffmpeg_has_bsf("dca_core")


class TestProject(unittest.TestCase):
    def test_copied_and_51_by_default(self):
        d = sample_project()
        d["titles"][0]["audio"] = {"codec": "dts"}
        t = project(d).titles[0]
        self.assertEqual((t.audio_codec, t.audio_passthrough, t.audio_channels),
                         ("dts", True, 6))
        self.assertEqual(t.audio_bitrate, 1_536_000)      # until the source is measured
        d["titles"][0]["audio"] = {"codec": "dts", "channels": 2, "bitrate": "448k"}
        p = project(d)
        self.assertEqual(p.titles[0].audio_channels, 2)
        self.assertTrue(any("bitrate is ignored for dts" in w for w in p.warnings), p.warnings)

    def test_refused(self):
        for audio, extra, path in (({"codec": "dts", "passthrough": False}, {},
                                    "audio.passthrough"),
                                   ({"codec": "mp2"}, {}, "audio.codec"),
                                   ({"codec": "dts"}, {"clips": [{"source": "a.mp4"}]},
                                    "audio.codec")):
            d = sample_project()
            t = d["titles"][0]
            t["audio"] = audio
            if extra:
                del t["source"]
                t.update(extra)
            with self.assertRaises(ProjectError) as cm:
                project(d)
            self.assertIn(f"titles[0].{path}", str(cm.exception.issues))

    def test_its_own_titleset_and_streams(self):
        d = sample_project()
        d["titles"][0]["audio"] = {"codec": "dts"}           # (the second title: AC-3)
        p = project(d)
        self.assertEqual([t.titleset for t in p.titles], [1, 2])
        self.assertEqual(author.audio_tags(p, [p.titles[0]]), ['<audio format="dts" channels="6"/>'])
        self.assertEqual(bluray.audio_streams(p.titles[0]), [(bluray.CODING_DTS, 6, "und", 48000)])
        self.assertEqual(encode.copy_args(p.titles[0]), ["-c:a", "copy", "-bsf:a", "dca_core"])
        self.assertEqual(encode.copy_args(p.titles[1]), ["-c:a", "copy"])


def dts_digest(path):
    """MD5 of the first DTS stream of a file, as raw DTS."""
    raw = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-i", path, "-map", "0:a:0",
                          "-c", "copy", "-f", "dts", "-"], capture_output=True, check=True).stdout
    return hashlib.md5(raw).hexdigest()


def audio_of(path):
    out = subprocess.run([tools.find("ffprobe"), "-v", "error", "-select_streams", "a",
                          "-show_entries", "stream=codec_name,channels", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return [(s["codec_name"], s["channels"]) for s in json.loads(out)["streams"]]


class Sources:
    """Three-second test pictures with 5.1 DTS, stereo DTS and AC-3 sound."""

    @staticmethod
    def make(d, size, rate):
        ff = [tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y"]
        pic = ["-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate}:duration=3"]
        sine = ["-f", "lavfi", "-i", "sine=f=440:d=3:r=48000"]
        subprocess.run(ff + sine + ["-af", "pan=5.1|c0=c0|c1=c0|c2=c0|c3=c0|c4=c0|c5=c0",
                                    "-c:a", "dca", "-strict", "-2", os.path.join(d, "s51.dts")],
                       check=True)
        subprocess.run(ff + sine + ["-ac", "2", "-c:a", "dca", "-strict", "-2",
                                    os.path.join(d, "s20.dts")], check=True)
        for name, audio in (("surround.mkv", "s51.dts"), ("stereo.mkv", "s20.dts")):
            subprocess.run(ff + pic + ["-i", os.path.join(d, audio), "-map", "0:v", "-map", "1:a",
                                       "-c:v", "libx264" if ffmpeg_has("encoders", "libx264")
                                       else "mpeg4", "-c:a", "copy", os.path.join(d, name)],
                           check=True)
        subprocess.run(ff + pic + sine + ["-map", "0:v", "-map", "1:a", "-c:v", "mpeg4",
                                          "-c:a", "ac3", "-ac", "2", os.path.join(d, "ac3.mkv")],
                       check=True)


@unittest.skipUnless(DTS_OK, "needs ffmpeg (dca, dca_core)")
class TestDvd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-dts-")
        Sources.make(d, "720x480", "30000/1001")
        cls.write({"version": 1,
                   "disc": {"label": "DTS", "standard": "NTSC", "aspect": "4:3",
                            "first_play": "title:dts"},
                   "titles": [{"id": "dts", "source": "surround.mkv", "audio": {"codec": "dts"}},
                              {"id": "ac3", "source": "ac3.mkv"}]})
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("--json", "build", d, "-o", cls.out, "--fast")

    @classmethod
    def write(cls, data):
        with open(os.path.join(cls.tmp, "project.oncemore.json"), "w") as f:
            json.dump(data, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_copied_unchanged(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        vts = os.path.join(self.out, "VIDEO_TS")
        # the DTS title and the AC-3 title: two titlesets
        self.assertEqual(audio_of(os.path.join(vts, "VTS_01_1.VOB")), [("dts", 6)])
        self.assertEqual(audio_of(os.path.join(vts, "VTS_02_1.VOB")), [("ac3", 2)])
        self.assertEqual(dts_digest(os.path.join(vts, "VTS_01_1.VOB")),
                         dts_digest(os.path.join(self.tmp, "s51.dts")))
        warnings = [e for e in json_lines(self.stdout) if e.get("level") == "warn"]
        self.assertTrue(any("DTS only" in e.get("message", "") for e in warnings), warnings)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_read_back_by_libdvdnav(self):
        with dvdnav_sim.DvdSim(os.path.join(self.out, "VIDEO_TS"), LIBDVDNAV) as d:
            d.wait_title()
            self.assertEqual(d.audio_format(0), dvdnav_sim.AUDIO_DTS)
            self.assertEqual(d.audio_channels(0), 6)

    def test_sources_checked(self):
        d = tempfile.mkdtemp(prefix="oncemore-dts-check-", dir=self.tmp)
        for name in ("ac3.mkv", "stereo.mkv"):
            os.symlink(os.path.join(self.tmp, name), os.path.join(d, name))
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1, "disc": {"label": "X", "standard": "NTSC", "aspect": "4:3",
                                              "first_play": "title:a"},
                       "titles": [{"id": "a", "source": "ac3.mkv", "audio": {"codec": "dts"}},
                                  {"id": "b", "source": "stereo.mkv",
                                   "audio": {"codec": "dts"}}]}, f)
        rc, out, _ = run_cli("--json", "validate", d)
        self.assertNotEqual(rc, 0)
        issues = {i["path"]: i["message"] for e in json_lines(out) for i in e.get("issues", [])}
        self.assertIn("only 48 kHz DTS can be copied", issues["titles[0].audio_tracks[0]"])
        self.assertIn("set audio.channels to 2", issues["titles[1].audio.channels"])


@unittest.skipUnless(DTS_OK and ffmpeg_has("encoders", "libx264") and LIBBLURAY,
                     "needs ffmpeg (dca, dca_core, libx264) and libbluray")
class TestBluray(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-bddts-")
        Sources.make(d, "1280x720", "24000/1001")
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1,
                       "disc": {"label": "BD_DTS", "standard": "NTSC", "aspect": "16:9",
                                "first_play": "title:dts"},
                       "titles": [{"id": "dts", "source": "surround.mkv",
                                   "audio": {"codec": "dts"}}]}, f)
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--format", "bluray",
                                                 "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_dts_stream(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        m2ts = os.path.join(self.out, "BDMV", "STREAM", "00001.m2ts")
        self.assertEqual(audio_of(m2ts), [("dts", 6)])
        self.assertEqual(dts_digest(m2ts), dts_digest(os.path.join(self.tmp, "s51.dts")))
        # (no DVD-only warning on a Blu-ray: its players decode DTS)
        self.assertNotIn("DTS only", self.stdout + self.stderr)
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            disc.info()
            # DTS (0x82), multi-channel (6), the language unknown
            self.assertEqual(disc.playlist(1)["audio"], [(bluray.CODING_DTS, 6, "und")])



def as_dts_hd(sources, profile="DTS-HD MA", rate=48000, channels=None, rates=(3_000_000,
                                                                          9_000_000)):
    """encode.probe and encode.audio_rates telling of DTS-HD in `sources`
    (file names): ffmpeg encodes no DTS-HD, so the core it does encode stands
    in for it, and what oncemore does with a DTS-HD source is what is tested."""
    real_probe = encode.probe

    def probe(path, *a, **k):
        info = real_probe(path, *a, **k)
        if os.path.basename(path) in sources:
            info = dict(info, audio=[dict(x, profile=profile, rate=rate,
                                          channels=channels or x["channels"])
                                     for x in info["audio"]])
        return info
    return mock.patch.multiple(encode, probe=probe,
                               audio_rates=lambda path, stream=0: rates)


@unittest.skipUnless(DTS_OK, "needs ffmpeg (dca, dca_core)")
class TestDtsHdChecked(unittest.TestCase):
    """What a DTS-HD source may be, on a DVD and on a Blu-ray."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-dtshd-check-")
        Sources.make(cls.tmp, "1280x720", "24000/1001")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def inspect(self, bd, audio=None, **kw):
        d = {"version": 1, "disc": {"label": "X", "standard": "NTSC", "aspect": "16:9",
                                    "first_play": "title:a"},
             "titles": [{"id": "a", "source": "surround.mkv",
                         "audio": audio or {"codec": "dts"}}]}
        p = build_project(d, os.path.join(self.tmp, "project.oncemore.json"))
        with as_dts_hd({"surround.mkv"}, **kw):
            try:
                build.inspect(p, bd=bd, prepare=False)
            except ProjectError as e:
                return p.titles[0], {i["path"]: i["message"] for i in e.issues}
        return p.titles[0], {}

    def test_kept_on_a_bluray(self):
        t, issues = self.inspect(True, rate=96000, channels=8)        # (7.1 at 96 kHz)
        self.assertEqual(issues, {})
        self.assertEqual(t.dts_hd, [("dtshd_ma", 96000)])
        self.assertEqual((t.audio_bitrate, t.audio_peak_bps), (3_000_000, 9_000_000))
        self.assertEqual(bluray.audio_streams(t), [(bluray.CODECS["dtshd_ma"], 6, "und", 96000)])
        self.assertEqual(bluray.audio_codec_args(t, 0), ["-c:a:0", "copy"])   # (not its core)
        # the picture leaves room for the sound's peaks
        self.assertEqual(bluray.title_max_bps(t, 40_000_000),
                         bluray.STREAMS_BPS - 9_000_000)
        self.assertEqual(bluray.title_max_bps(t, 20_000_000), 20_000_000)
        t, _ = self.inspect(True, profile="DTS-HD HRA")
        self.assertEqual(t.dts_hd, [("dtshd", 48000)])

    def test_dvd_takes_the_core(self):
        t, issues = self.inspect(False, channels=8)                   # (7.1: a 5.1 core)
        self.assertEqual(issues, {})
        self.assertEqual((t.dts_hd, t.audio_peak_bps), ([None], 0))
        self.assertEqual(encode.copy_args(t), ["-c:a", "copy", "-bsf:a", "dca_core"])
        _, issues = self.inspect(False, rate=96000)
        self.assertIn("DTS-HD at 96 or 192 kHz too, on a Blu-ray",
                      issues["titles[0].audio_tracks[0]"])

    def test_refused(self):
        _, issues = self.inspect(True, profile="DTS Express")
        self.assertIn("DTS Express, which has no DTS core", issues["titles[0].audio_tracks[0]"])
        _, issues = self.inspect(True, audio={"codec": "dts", "channels": 2}, channels=8)
        self.assertIn("set audio.channels to 6", issues["titles[0].audio.channels"])
        _, issues = self.inspect(True, profile="DTS", rate=96000)    # (plain DTS: 48 kHz)
        self.assertIn("only 48 kHz DTS", issues["titles[0].audio_tracks[0]"])

    def test_cache_tells_it_apart(self):
        from oncemore import build as b
        t, _ = self.inspect(True)
        p = build_project({"version": 1, "disc": {"label": "X", "standard": "NTSC",
                                                  "aspect": "16:9"},
                           "titles": [{"id": "a", "source": "surround.mkv",
                                       "audio": {"codec": "dts"}}]},
                          os.path.join(self.tmp, "project.oncemore.json"))
        info = encode.probe(os.path.join(self.tmp, "surround.mkv"))
        core = b.title_cache_key(p, p.titles[0], info, 1, True)
        self.assertNotEqual(b.title_cache_key(p, t, info, 1, True), core)


@unittest.skipUnless(DTS_OK and ffmpeg_has("encoders", "libx264") and LIBBLURAY,
                     "needs ffmpeg (dca, dca_core, libx264) and libbluray")
class TestDtsHdBluray(unittest.TestCase):
    """A Blu-ray with a DTS-HD Master Audio track at 96 kHz: copied whole,
    and declared so in the clip, its PMT and its playlist (libbluray)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-bddtshd-")
        Sources.make(d, "1280x720", "24000/1001")
        p = build_project({"version": 1,
                           "disc": {"label": "BD_DTSHD", "standard": "NTSC", "aspect": "16:9",
                                    "first_play": "title:dts"},
                           "titles": [{"id": "dts", "source": "surround.mkv",
                                       "audio": {"codec": "dts", "lang": "en"}}]},
                          os.path.join(d, "project.oncemore.json"))
        cls.out = os.path.join(d, "out")
        with as_dts_hd({"surround.mkv"}, rate=96000):
            build.build_bluray(p, cls.out, report.Reporter(out=io.StringIO(), err=io.StringIO()),
                               fast=True, cache=False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_declared_dts_hd(self):
        m2ts = os.path.join(self.out, "BDMV", "STREAM", "00001.m2ts")
        self.assertEqual(dts_digest(m2ts), dts_digest(os.path.join(self.tmp, "s51.dts")))
        self.assertEqual(stream_pids(m2ts)[bluray.AUDIO_PID], bluray.CODECS["dtshd_ma"])
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            disc.info()
            pl = disc.playlist(1)
        self.assertEqual(pl["audio"], [(bluray.CODECS["dtshd_ma"], 6, "eng")])
        self.assertEqual(pl["audio_rate"], [14])             # (96 kHz over a 48 kHz core)


if __name__ == "__main__":
    unittest.main()
