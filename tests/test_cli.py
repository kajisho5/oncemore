import json
import os
import sys
import tempfile
import unittest

from .helpers import ROOT, json_lines, run_cli


class TestCli(unittest.TestCase):
    def test_version_and_help(self):
        rc, out, _ = run_cli("--version")
        self.assertEqual(rc, 0)
        self.assertIn("oncemore", out)
        rc, out, _ = run_cli("--help")
        self.assertEqual(rc, 0)
        for cmd in ("init", "validate", "build", "iso", "preview-menu", "doctor", "simulate"):
            self.assertIn(cmd, out)

    def test_doctor_json(self):
        rc, out, _ = run_cli("doctor", "--json")
        self.assertIn(rc, (0, 3))
        events = json_lines(out)
        self.assertEqual(events[-1]["event"], "result")
        names = [t["name"] for t in events[-1]["tools"]]
        for n in ("ffmpeg", "ffprobe"):
            self.assertIn(n, names)
        self.assertNotIn("dvdauthor", names)
        self.assertIn("iso_tool", events[-1])
        self.assertIn("ok", events[-1]["drawtext_render"])

    def test_contract_json(self):
        rc, out, _ = run_cli("contract", "--json")
        self.assertEqual(rc, 0)
        c = json_lines(out)[-1]
        for k in ("skill_id", "version", "contract_version", "provides", "dependencies",
                  "not_provided"):
            self.assertIn(k, c)
        from oncemore import __version__
        self.assertEqual((c["skill_id"], c["version"]), ("oncemore", __version__))
        tool_ids = [t["tool_id"] for t in c["tools"]]
        ids = [p["id"] for p in c["provides"]]
        self.assertEqual(len(ids), len(set(ids)))
        for p in c["provides"]:
            self.assertEqual(set(p), {"id", "lifecycle", "tool_id"})
            self.assertIn(p["lifecycle"], ("PROPOSED", "EXPERIMENTAL", "STABLE", "DEPRECATED",
                                           "RETIRED"))
            self.assertIn(p["tool_id"], tool_ids)
        rc, out, _ = run_cli("--help")
        for t in c["tools"]:
            self.assertIn(t["command"], out)

    def test_missing_project_no_traceback(self):
        rc, out, err = run_cli("validate", "/nonexistent/project.oncemore.json")
        self.assertEqual(rc, 2)
        self.assertIn("not found", err)
        self.assertNotIn("Traceback", err + out)

    def test_validation_errors_as_json(self):
        with tempfile.TemporaryDirectory() as d:
            bad = {"version": 1, "disc": {"label": "X", "standard": "NTSC", "aspect": "16:9"},
                   "titles": [{"id": "t1", "source": "missing.mp4", "end_action": "menu:none"}]}
            with open(os.path.join(d, "project.oncemore.json"), "w") as f:
                json.dump(bad, f)
            rc, out, err = run_cli("--json", "validate", d)
            self.assertEqual(rc, 2)
            ev = json_lines(out)[-1]
            self.assertEqual(ev["event"], "error")
            self.assertFalse(ev["ok"])
            msgs = " ".join(i["message"] for i in ev["issues"])
            self.assertIn("file not found: missing.mp4", msgs)
            self.assertIn("no menu with id 'none'", msgs)
            self.assertNotIn("Traceback", err)

    def test_simulate_and_navigation_notes(self):
        with tempfile.TemporaryDirectory() as d:
            from oncemore.scaffold import sample_project
            data = sample_project()
            data["titles"].append({"id": "t3", "source": "media/sample_a.mp4"})
            data["menus"][0]["buttons"][0]["action"] = "title:t1"      # no play all
            with open(os.path.join(d, "project.oncemore.json"), "w") as f:
                json.dump(data, f)
            rc, out, err = run_cli("--json", "validate", "--no-media", d)
            self.assertEqual(rc, 0, err)
            nav = json_lines(out)[-1]["navigation"]
            self.assertIn({"level": "warning", "path": "title:t3",
                           "message": "title 't3' cannot be reached: no button, playlist or "
                                      "end action plays it"}, nav)
            rc, out, err = run_cli("--json", "simulate", d, "--simple-layout",
                                   "--keys", "down,enter,enter,play,menu")
            self.assertEqual(rc, 0, err)
            views = [s["view"] for s in json_lines(out)[-1]["steps"]]
            self.assertEqual(views, [["menu", "main", 1], ["menu", "main", 2],
                                     ["menu", "chapters", 1], ["title", 1, 1],
                                     ["title", 1, 2], ["menu", "main", 2]])
            rc, out, err = run_cli("simulate", d, "--simple-layout", "--keys", "jump")
            self.assertEqual(rc, 1)
            self.assertIn("unknown key 'jump'", err)

    def test_missing_tools_message(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.mp4"), "wb").close()
            data = {"version": 1, "disc": {"label": "X", "standard": "NTSC", "aspect": "16:9"},
                    "titles": [{"id": "t1", "source": "a.mp4"}]}
            with open(os.path.join(d, "project.oncemore.json"), "w") as f:
                json.dump(data, f)
            empty = os.path.join(d, "emptybin")
            os.mkdir(empty)
            env = {"PATH": empty, "ONCEMORE_FFMPEG": "", "ONCEMORE_FFPROBE": ""}
            if sys.platform == "darwin":
                self.skipTest("Homebrew kegs are searched outside PATH on macOS")
            rc, out, err = run_cli("build", d, "-o", os.path.join(d, "out"), env=env)
            self.assertEqual(rc, 3)
            self.assertIn("Missing external tools", err)
            self.assertIn("Install with", err)
            self.assertNotIn("Traceback", err)
            rc, out, err = run_cli("doctor", env=env)
            self.assertEqual(rc, 3)


if __name__ == "__main__":
    unittest.main()
