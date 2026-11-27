"""A disc from a typed build request (DECISIONS §142): `oncemore request`
checks it and gives a token; `iso --request --confirm` builds it only with
that token, and the DVD image read back has the request's chapters."""

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest

from oncemore import request as requestmod, tools
from oncemore.errors import ProjectError

from .helpers import ROOT, have, json_lines, run_cli

DVD_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext()
EXAMPLE = os.path.join(ROOT, "examples", "request", "request.json")


def write_media(folder, seconds=9):
    os.makedirs(os.path.join(folder, "media"), exist_ok=True)
    subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size=320x240:rate=30000/1001:duration={seconds}", "-f", "lavfi", "-i",
                    f"sine=duration={seconds}", "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", os.path.join(folder, "media", "day1.mp4")], check=True)
    with open(os.path.join(folder, "media", "day1.en.srt"), "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,500 --> 00:00:02,500\nOpening remarks\n\n"
                "2\n00:00:03,500 --> 00:00:05,500\nKeynote\n")


class TestRequest(unittest.TestCase):
    """The request, the project it makes and its token (no encoding)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-request-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(EXAMPLE, encoding="utf-8") as f:
            self.request = json.load(f)

    def write(self, request, name="request.json"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(request, f)
        return path

    def test_schema_copies_agree(self):
        with open(os.path.join(ROOT, "schema", "build-request.schema.json"), encoding="utf-8") as a, \
                open(os.path.join(ROOT, "oncemore", "build-request.schema.json"), encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read())

    def test_one_title_with_sessions_as_chapters(self):
        p = requestmod.to_project(self.request)
        [title] = p["titles"]
        self.assertEqual([c["name"] for c in title["chapters"]],
                         ["Opening remarks", "Keynote", "Panel discussion"])
        self.assertEqual(title["auto_chapter_menu"]["id"], "chapters_t1")
        self.assertEqual(title["subtitles"], [{"file": "media/day1.en.srt", "lang": "en", "default": False}])
        [menu] = p["menus"]
        self.assertEqual([t["text"] for t in menu["texts"]], ["Annual Meeting 2026", "Day 1 - Main hall"])
        self.assertEqual([(b["label"], b["action"]) for b in menu["buttons"]],
                         [("PLAY", "title:t1"), ("SESSIONS", "menu:chapters_t1")])
        self.assertEqual(p["disc"]["standard"], "NTSC")

    def test_several_titles_get_a_button_each(self):
        self.request["titles"].append({"name": "Day 2", "source": "media/day2.mp4"})
        p = requestmod.to_project(self.request)
        self.assertEqual([(b["label"], b["action"]) for b in p["menus"][0]["buttons"]],
                         [("PLAY ALL", "playall"), ("Day 1", "title:t1"), ("Day 2", "title:t2")])
        self.assertEqual(p["titles"][1]["chapters"], [{"time": 0}])
        self.assertNotIn("auto_chapter_menu", p["titles"][1])

    def test_a_first_chapter_after_0_gets_one_at_0(self):
        self.request["titles"][0]["chapters"] = [{"time": "00:00:03", "name": "Keynote"}]
        self.assertEqual(requestmod.expected_chapters(self.request), [2])

    def test_bluray(self):
        self.request["format"] = "bluray"
        disc = requestmod.to_project(self.request)["disc"]
        self.assertEqual(disc["format"], "bluray")
        self.assertNotIn("standard", disc)

    def test_schema_errors(self):
        bad = dict(self.request, extra=1)
        with self.assertRaises(ProjectError):
            requestmod.read_request(self.write(bad))
        many = dict(self.request, titles=[{"name": f"T{k}", "source": "x.mp4"} for k in range(6)])
        with self.assertRaises(ProjectError):
            requestmod.read_request(self.write(many))
        with self.assertRaises(ProjectError):
            requestmod.read_request(self.write(dict(self.request, schema="oncemore/build-request@2")))

    def test_token_follows_the_request_and_its_files(self):
        path = self.write(self.request)
        first = requestmod.token(self.request, path)
        self.assertEqual(first, requestmod.token(json.loads(json.dumps(self.request)), path))
        changed = json.loads(json.dumps(self.request))
        changed["titles"][0]["chapters"][1]["name"] = "Keynote lecture"
        self.assertNotEqual(first, requestmod.token(changed, path))
        srt = os.path.join(self.tmp, "media", "day1.en.srt")
        os.makedirs(os.path.dirname(srt), exist_ok=True)
        with open(srt, "a", encoding="utf-8") as f:
            f.write("\n")
        future = time.time() + 10
        os.utime(srt, (future, future))
        self.assertNotEqual(first, requestmod.token(self.request, path))

    def test_build_needs_the_token(self):
        path = self.write(self.request)
        code, out, _ = run_cli("iso", "--request", path, "-o", os.path.join(self.tmp, "x.iso"), "--json")
        self.assertEqual(code, 2)
        self.assertIn("only once it is confirmed", json_lines(out)[-1]["message"])
        code, out, _ = run_cli("iso", "--request", path, "--confirm", "0" * 16,
                               "-o", os.path.join(self.tmp, "x.iso"), "--json")
        self.assertEqual(code, 2)
        self.assertIn("does not match", json_lines(out)[-1]["message"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "x.iso")))

    def test_a_project_and_a_request_together_are_refused(self):
        path = self.write(self.request)
        code, out, _ = run_cli("build", os.path.join(ROOT, "examples", "basic"), "--request", path,
                               "-o", os.path.join(self.tmp, "out"), "--json")
        self.assertEqual(code, 2)
        code, out, _ = run_cli("build", os.path.join(ROOT, "examples", "basic"), "--confirm", "abc",
                               "-o", os.path.join(self.tmp, "out"), "--json")
        self.assertEqual(code, 2)


@unittest.skipUnless(DVD_OK, "needs ffmpeg with drawtext")
class TestBuildFromRequest(unittest.TestCase):
    """The roadmap's Done when: a request with three sessions builds a disc
    image with three chapters."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-request-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copy(EXAMPLE, self.tmp)
        write_media(self.tmp)
        self.path = os.path.join(self.tmp, "request.json")

    def test_three_sessions_build_an_image_with_three_chapters(self):
        code, out, err = run_cli("request", self.path, "--json")
        self.assertEqual(code, 0, err + out)
        checked = json_lines(out)[-1]
        self.assertEqual(checked["chapters"], [3])
        token = checked["confirm"]
        self.assertEqual(checked["next"][:6], ["oncemore", "iso", "--request", self.path, "--confirm", token])

        image = os.path.join(self.tmp, "day1.iso")
        code, out, err = run_cli("iso", "--request", self.path, "--confirm", token, "-o", image,
                                 "--fast", "--json")
        self.assertEqual(code, 0, err + out)
        res = json_lines(out)[-1]
        self.assertTrue(res["ok"])
        self.assertEqual(res["verified"], {"chapters": [3]})
        self.assertEqual(requestmod.dvd_chapters(image), [3])          # read back independently
        self.assertEqual(res["disc"]["label"], "ANNUAL_MEETING_2026")

        # the request changed after it was confirmed: refused
        with open(self.path, encoding="utf-8") as f:
            changed = json.load(f)
        changed["titles"][0]["chapters"].pop()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(changed, f)
        code, out, _ = run_cli("iso", "--request", self.path, "--confirm", token, "-o", image, "--json")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
