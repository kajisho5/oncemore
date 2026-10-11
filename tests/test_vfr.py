"""Sound stays with the picture when the source has a variable frame rate.

Phones and screen recorders write video whose frames come at uneven
intervals. An authoring tool that takes such a stream frame by frame at a
fixed rate drifts out of sync, the further the more (a long-standing
complaint about classic DVD and Blu-ray authoring apps). oncemore encodes
to the disc's fixed rate from the frames' own times, so the sound keeps its
place; this test holds it to that.

The source: 12 s of black whose frames come every 1/60, 1/30 or 1/20 s in
turn (an average of about 27 a second), with a white flash and a beep
together at 1, 6 and 11 s. The title is built for DVD (NTSC and PAL) and
Blu-ray, and each flash is matched with its beep in what is on the disc.
"""

import glob
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from oncemore import build, report, tools
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have

TOOLS_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext()
EVENTS = (1, 6, 11)                # seconds: a flash and a beep together
LIMIT = 0.040                      # the most sound may be off (s): just over an NTSC frame


def make_vfr(path):
    on = "+".join(f"between(t,{t},{t}.2)" for t in EVENTS)
    keep = (f"if(gt({on},0),1,if(lt(t,4),not(mod(n,2)),"
            f"if(lt(t,8),not(mod(n,3))+not(mod(n,7)),not(mod(n,5))+eq(mod(n,5),2))))")
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=black:s=640x360:r=60:d=12",
        "-f", "lavfi", "-i", "sine=f=1000:r=48000:d=12",
        "-filter_complex",
        f"[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='{on}',"
        f"select='{keep}'[v];[1:a]volume=0:enable='not({on})'[a]",
        "-map", "[v]", "-map", "[a]", "-fps_mode", "vfr",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", path], check=True)


def onsets(path):
    """(flash times, beep times) in a media file, from its own timestamps."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:v:0", "-vf",
         "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"],
        capture_output=True, text=True).stdout
    flashes, lit, t = [], False, None
    for line in out.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
        m = re.search(r"YAVG=([\d.]+)", line)
        if m:
            bright = float(m.group(1)) > 128
            if bright and not lit:
                flashes.append(t)
            lit = bright
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af",
         "silencedetect=n=-30dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    beeps = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return flashes, beeps


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext) and ffprobe")
class TestVariableFrameRate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="oncemore-vfr-")
        cls.src = os.path.join(cls.dir, "phone.mp4")
        make_vfr(cls.src)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def project(self, standard):
        d = sample_project()
        d["disc"].update(standard=standard, first_play="title:t1")
        d["titles"] = [{"id": "t1", "name": "Phone", "source": self.src}]
        m = d["menus"][0]
        m.pop("background", None)
        m["background_color"] = "#000000"
        m["buttons"] = [{"id": "play", "label": "PLAY", "x": 120, "y": 220,
                         "action": "title:t1"}]
        d["menus"] = [m]
        pdir = os.path.join(self.dir, standard)
        os.makedirs(pdir, exist_ok=True)
        path = os.path.join(pdir, "project.oncemore.json")
        with open(path, "w") as f:
            json.dump(d, f)
        return build_project(d, path), pdir

    def check(self, path):
        flashes, beeps = onsets(path)
        self.assertEqual(len(flashes), len(EVENTS), flashes)
        # (the source's sound runs to its end: the last silence ends there too)
        pairs = list(zip(flashes, beeps))
        for want, (flash, beep) in zip(EVENTS, pairs):
            self.assertAlmostEqual(flash, want, delta=0.1)
            self.assertLess(abs(beep - flash), LIMIT,
                            f"sound {1000 * (beep - flash):+.0f} ms off the picture at {flash:.2f} s")
        # and no drift from the first event to the last
        first, last = pairs[0], pairs[-1]
        self.assertLess(abs((last[1] - last[0]) - (first[1] - first[0])), LIMIT)

    def test_source_is_variable(self):
        # (the test means something only if the source really is uneven)
        times = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                                "-show_entries", "frame=pts_time", "-of", "csv=p=0", self.src],
                               capture_output=True, text=True, check=True).stdout.split()
        times = [float(x.strip(",")) for x in times if x.strip(",")]
        steps = {round(b - a, 3) for a, b in zip(times, times[1:])}
        self.assertGreaterEqual(len(steps), 3, steps)

    def test_dvd(self):
        for standard in ("NTSC", "PAL"):
            with self.subTest(standard=standard):
                p, pdir = self.project(standard)
                out = os.path.join(pdir, "dvd")
                build.build(p, out, report.Reporter(out=io.StringIO(), err=io.StringIO()), fast=True,
                            cache=False)
                title = os.path.join(pdir, "title.vob")
                with open(title, "wb") as w:
                    for vob in sorted(glob.glob(os.path.join(out, "VIDEO_TS", "VTS_01_[1-9].VOB"))):
                        with open(vob, "rb") as r:
                            shutil.copyfileobj(r, w)
                self.check(title)

    def test_blu_ray(self):
        p, pdir = self.project("NTSC")
        out = os.path.join(pdir, "bd")
        build.build_bluray(p, out, report.Reporter(out=io.StringIO(), err=io.StringIO()), fast=True,
                           cache=False)
        # the title's clip (the menu's is a short still)
        clip = max(glob.glob(os.path.join(out, "BDMV", "STREAM", "*.m2ts")), key=os.path.getsize)
        self.check(clip)


if __name__ == "__main__":
    unittest.main()
