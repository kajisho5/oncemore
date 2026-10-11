"""The bit budget: where the disc's space goes before anything is encoded.

Each title's length, video and audio rates and bytes, the menus, the
disc's own files and what is left, for a DVD and a Blu-ray plan, and from
`oncemore validate` of the sample project.
"""

import os
import shutil
import tempfile
import unittest

from oncemore import bluray, build, encode
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have, json_lines, run_cli


class TestPlans(unittest.TestCase):
    def test_dvd(self):
        cap = 4_700_000_000
        plan = encode.plan_bitrate([(3600, 192_000), (600, 448_000, 3_000_000)], cap,
                                   menu_seconds=60)
        b = plan["budget"]
        v = plan["per_title"][0]
        # an hour at the shared rate, ten minutes at its own
        self.assertEqual(b["titles"][0], int(3600 * (v + 192_000) / 8 * (1 + encode.MUX_OVERHEAD)))
        self.assertEqual(b["titles"][1],
                         int(600 * (3_000_000 + 448_000) / 8 * (1 + encode.MUX_OVERHEAD)))
        self.assertGreater(b["menus"], 0)
        self.assertEqual(b["other"], encode.IFO_RESERVE)
        # the parts add up to the estimate
        self.assertAlmostEqual(sum(b["titles"]) + b["menus"] + b["other"],
                               plan["estimated_bytes"], delta=4)

    def test_bluray(self):
        plan = bluray.plan([(3600, 640_000), (60, 192_000, 20_000_000)], 25_025_314_816)
        b = plan["budget"]
        self.assertEqual(len(b["titles"]), 2)
        self.assertEqual(b["titles"][1], int(60 * 20_192_000 / 8 * (1 + bluray.DISC_SAFETY)))
        self.assertLessEqual(sum(b["titles"]), plan["capacity"])

    def test_summary(self):
        p = build_project(sample_project(), "/virtual/project.oncemore.json", check_files=False)
        infos = {t.id: {"duration": d} for t, d in zip(p.titles, (24.0, 12.0))}
        plan = encode.plan_bitrate([(24.0, t.audio_bps) for t in p.titles[:1]] +
                                   [(12.0, p.titles[1].audio_bps)], p.disc.capacity, 10)
        b = build.budget(p, infos, plan)
        self.assertEqual([(x["id"], x["seconds"]) for x in b["titles"]], [("t1", 24.0), ("t2", 12.0)])
        self.assertEqual(b["titles"][0]["video_bps"], plan["per_title"][0])
        used = sum(x["bytes"] for x in b["titles"]) + b["menus"] + b["other"]
        self.assertEqual(b["free"], p.disc.capacity - used)


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestValidate(unittest.TestCase):
    def test_sample(self):
        tmp = tempfile.mkdtemp(prefix="oncemore-budget-")
        self.addCleanup(shutil.rmtree, tmp, True)
        rc, _, err = run_cli("init", "s", cwd=tmp)
        self.assertEqual(rc, 0, err)
        rc, out, err = run_cli("--json", "validate", os.path.join(tmp, "s"))
        self.assertEqual(rc, 0, err)
        s = json_lines(out)[-1]
        b = s["budget"]
        self.assertEqual([x["id"] for x in b["titles"]], ["t1", "t2"])
        self.assertTrue(all(x["bytes"] > 0 for x in b["titles"]))
        self.assertGreater(b["free"], 0.9 * b["capacity"])           # a minute of video
        rc, out, err = run_cli("validate", os.path.join(tmp, "s"))
        self.assertIn("MiB]", out)
        self.assertIn("free", out)


if __name__ == "__main__":
    unittest.main()
