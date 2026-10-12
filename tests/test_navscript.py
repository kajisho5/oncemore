"""Navigation scripts (commands:<id>): the language, the project's checks,
the registers they get, the commands they become, the simulator and the
flowchart; and a built disc driven with libdvdnav."""

import json
import os
import random
import shutil
import subprocess
import tempfile
import unittest

from oncemore import author, build, graph, navscript, schemalite, tools
from oncemore.errors import ProjectError
from oncemore.project import build_project, load_schema
from oncemore.scaffold import sample_project
from oncemore.simulate import SimError, Simulator

from .helpers import have, json_lines, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

TOOLS_OK = (have("ffmpeg", "ffprobe") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)

TWICE = "# the second press plays title B\n$n += 1;\nif ($n >= 2) { $n = 0; play title:t2; }\nelse play menu:main;"
DICE = "$r = random(1); if ($r == 1) play title:t1; else play title:t2;"


def data(scripts=None, **actions):
    """The sample project with `scripts`; `actions` {button id of the main
    menu: action}."""
    d = sample_project()
    d["scripts"] = scripts if scripts is not None else {"twice": TWICE}
    for b in d["menus"][0]["buttons"]:
        b["action"] = actions.get(b["id"], b["action"])
    if not actions:
        d["menus"][0]["buttons"][2]["action"] = "commands:twice"
    return d


def project(d):
    return build_project(d, "/virtual/project.oncemore.json", check_files=False)


def problems(d):
    try:
        project(d)
    except ProjectError as e:
        return " | ".join(f"{i['path']}: {i['message']}" for i in e.issues)
    raise AssertionError("expected a ProjectError")


class TestLanguage(unittest.TestCase):
    def test_parse_and_expand(self):
        stmts = navscript.parse(TWICE)
        self.assertEqual(navscript.variables(stmts), ["n"])
        self.assertEqual(navscript.actions(stmts), ["title:t2", "menu:main"])
        text = navscript.expand(stmts, {"n": "g9"}, lambda a: f"<{a}>")
        self.assertEqual(text, "g9 += 1; if (g9 >= 2) { g9 = 0; <title:t2> } else { <menu:main> }")
        # an expression is worked out in place, one operation a command
        stmts = navscript.parse("$r = random(6) + 1 * 2; $s = $r; $s -= audio;"
                                "if ($r == 3 and audio != 1) play stop; else play playall;")
        self.assertEqual(navscript.expand(stmts, {"r": "g8", "s": "g7"}, lambda a: a),
                         "g8 = random(6); g8 += 1; g8 *= 2; g7 = g8; g7 -= audio; "
                         "if ((g8 == 3) and (audio != 1)) { stop } else { playall }")
        self.assertEqual(navscript.expand(navscript.parse("$x = $x * 3; button = $x; play stop;"),
                                          {"x": "g1"}, lambda a: "exit;"),
                         "g1 *= 3; button = g1; exit;")

    def test_refused(self):
        cases = [
            ("", "empty"),
            ("play audio:2;", "must end with play"),
            ("if ($a == 1) play stop;", "must end with play"),
            ("play stop; $x = 1;", "nothing after play stop runs"),
            ("if ($a == 1) { play stop; $b = 1; } else play stop;", "nothing after play stop"),
            ("$x = $y + $x; play stop;", "may only come first"),
            ("if (1 == 2) play stop; else play stop;", "compares two numbers"),
            ("if ($a == 1 and $b == 1 or $c == 1) play stop; else play stop;", "not both"),
            ("$x /= 0; play stop;", "/ 0"),
            ("$x = $y % 0; play stop;", "% 0"),
            ("$x += random(3); play stop;", "random(n) is the first value"),
            ("if (random(3) == 1) play stop; else play stop;", "random(n) is the first value"),
            ("button = 3; play stop;", "button number * 1024"),
            ("audio = 9; play stop;", "0 to 7"),
            ("audio += 1; play stop;", "takes = only"),
            ("audio = 1 + $x; play stop;", "';'"),
            ("jump title 1;", "use play <action>"),
            ("g3 = 1; play stop;", "use play <action>"),
            ("$x = 70000; play stop;", "not 0 to 65535"),
            ("play resume;", "play takes an action"),
            ("play audio:x;", "not 'audio:x'"),
            ("play chapter:t1;", "not 'chapter:t1'"),
            ("$x = 1 play stop;", "expected ';'"),
        ]
        for text, why in cases:
            with self.assertRaises(navscript.ScriptError, msg=text) as e:
                navscript.parse(text)
            self.assertIn(why, str(e.exception), text)

    def test_run(self):
        played, regs = [], {"audio": 1}
        env = {"vars": {}, "get": regs.get, "set": regs.__setitem__, "play": played.append}
        stmts = navscript.parse(TWICE)
        self.assertTrue(navscript.run(stmts, env))
        self.assertEqual((played, env["vars"]), (["menu:main"], {"n": 1}))
        navscript.run(stmts, env)
        self.assertEqual((played[-1], env["vars"]), ("title:t2", {"n": 0}))
        # a sound switch plays on; random(n) is 1 to n
        navscript.run(navscript.parse("play audio:2; $r = random(3) + audio; audio = $r;"
                                      "play stop;"), dict(env, rng=random.Random(1)))
        self.assertEqual(played[-2:], ["audio:2", "stop"])
        self.assertIn(env["vars"]["r"], (2, 3, 4))
        self.assertEqual(regs["audio"], env["vars"]["r"])
        # outside 0 to 65535: not described, so the simulator stops there
        with self.assertRaises(navscript.ScriptError) as e:
            navscript.run(navscript.parse("$n -= 1; play stop;"), {"vars": {"n": 0}})
        self.assertIn("not described", str(e.exception))


class TestProject(unittest.TestCase):
    def test_loaded(self):
        p = project(data())
        self.assertEqual(list(p.scripts), ["twice"])
        # what the scripts play counts as the disc's actions
        self.assertIn("title:t2", p.actions())
        self.assertNotIn("commands:twice", p.actions())
        self.assertIn("commands:twice", p.actions(scripts=False))

    def test_schema(self):
        schema = load_schema()
        d = data()
        self.assertEqual(schemalite.validate(d, schema), [])
        d["scripts"] = {"bad id": "play stop;"}
        self.assertIn("name", " ".join(m for _, m in schemalite.validate(d, schema)))
        d = data(play="commands:twice")
        d["titles"][0]["buttons"] = []
        d["menus"][0]["buttons"][0]["override"] = "commands:twice"       # (not for overrides)
        self.assertTrue(schemalite.validate(d, schema))

    def test_refused(self):
        cases = [
            (data({"twice": "play audio:1;"}), "scripts.twice: the script must end"),
            (data(b="commands:nope"), "no script with id 'nope'"),
            (dict(data(), disc=dict(data()["disc"], first_play="commands:twice")),
             "does not match"),                          # (the schema's: not at first play)
            (data({"twice": "play lastmenu;"}, b="commands:twice"), "lastmenu is only for"),
            (data({"twice": "play menu:nope;"}, b="commands:twice"), "(script 'twice'): no menu"),
            (data({"twice": " ".join(f"$v{k} = 1;" for k in range(13)) + " play stop;"},
                  b="commands:twice"), "the scripts use 13 variables"),
        ]
        for d, why in cases:
            self.assertIn(why, problems(d))

    def test_unused(self):
        p = project(data({"twice": TWICE, "spare": "play stop;"}, b="commands:twice"))
        self.assertIn("scripts.spare is not run by any button, time-out or end action",
                      p.warnings)


class TestAuthor(unittest.TestCase):
    def test_registers_left_free(self):
        d = data({"twice": TWICE, "dice": DICE + " # $n too\n"}, b="commands:twice",
                 play="resume")
        d["titles"][1]["end_action"] = "commands:dice"
        p = project(d)
        regs = author.script_registers(p)
        self.assertEqual(list(regs), ["n", "r"])
        taken = {author.resume_reg(p), author.NAV_REG, author.PLAYALL_REG}
        taken |= {author.button_reg(m) for m in p.menus}
        self.assertFalse(taken & set(regs.values()), (taken, regs))
        self.assertEqual(len(set(regs.values())), 2)

    def test_commands(self):
        d = data({"twice": TWICE, "dice": DICE}, b="commands:twice")
        d["titles"][1]["end_action"] = "commands:dice"
        p = project(d)
        n = author.script_registers(p)["n"]
        main = p.menu("main")
        b = main.buttons[2]
        text = author.menu_button_command(p, main, b)
        self.assertEqual(text, f"{author.button_reg(main)} = button; {n} += 1; if ({n} >= 2) {{ "
                               f"{n} = 0; {author._single(p)}jump title 2; }} else {{ jump menu 1; }}")
        r = author.script_registers(p)["r"]
        post = author.end_command(p, "commands:dice", p.title("t2"))
        self.assertIn(f"{r} = random(1); if ({r} == 1) {{ jump title 1; }} else {{ jump title 2; }}",
                      post)
        self.assertEqual(build.script_issues(p), [])
        self.assertIn("are for DVD", build.script_issues(p, bd=True)[0]["message"])

    def test_title_scripts_call_menus(self):
        d = data({"back": "if (audio == 0) play menu:main; else play subtitle:off; play stop;"},
                 b="title:t2")
        d["titles"][1]["buttons"] = [{"id": "x", "start": 1, "x": 10, "y": 10, "width": 100,
                                      "height": 50, "action": "commands:back"}]
        p = project(d)
        t = p.title("t2")
        text = author.title_button_command(p, t, "commands:back")
        self.assertEqual(text, "if (audio == 0) { g1 = 1; call menu entry root; } else "
                               "{ subtitle = 0; } exit;")
        self.assertEqual(build.script_issues(p), [])


class TestSimulatorAndFlowchart(unittest.TestCase):
    def test_counter(self):
        p = project(data())
        sim = Simulator(p)
        s = sim.start()
        sim.press(s, "select:b")
        sim.press(s, "enter")
        self.assertEqual((s["domain"], s["menu"], s["vars"]), ("menu", "main", {"n": 1}))
        sim.press(s, "enter")
        self.assertEqual((s["domain"], s["title"], s["vars"]), ("title", "t2", {"n": 0}))
        json.dumps(s)                                      # (the app keeps it between requests)

    def test_registers_and_errors(self):
        d = data({"aud": "$a = audio; button = 2048; play title:t1;",
                  "down": "$z -= 1; play stop;"}, b="commands:aud", ch="commands:down")
        p = project(d)
        sim = Simulator(p)
        s = sim.start()
        sim.press(s, "select:b")
        sim.press(s, "enter")
        self.assertEqual((s["title"], s["vars"]["a"], s["button"]), ("t1", 0, 2))
        sim.press(s, "menu")
        sim.press(s, "select:ch")
        with self.assertRaises(SimError) as e:
            sim.press(s, "enter")
        self.assertIn("not described", str(e.exception))

    def test_flowchart(self):
        g = graph.build(project(data()))
        edges = [(e["from"], e["to"], e["label"]) for e in g["edges"] if e["kind"] == "button"]
        self.assertIn((graph.node_id("menu", "main"), graph.node_id("title", "t2"), "b · script twice"),
                      edges)
        self.assertIn((graph.node_id("menu", "main"), graph.node_id("menu", "main"), "b · script twice"),
                      edges)


@unittest.skipUnless(TOOLS_OK, "needs ffmpeg (drawtext), ffprobe and an ISO tool")
class TestOnDisc(unittest.TestCase):
    """The main menu's third button counts its presses (the first returns to
    the menu, the second plays title B) and the first throws a one-sided die
    (random(1) is 1: title A)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-script-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "s")
        for name in ("sample_a.mp4", "sample_b.mp4"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=s=640x360:r=30000/1001:d=4", "-f", "lavfi", "-i",
                            "sine=f=440:d=4", "-c:v", "mpeg4", "-q:v", "3", "-c:a", "aac",
                            "-shortest", os.path.join(proj, "media", name)], check=True)
        cls.path = os.path.join(proj, "project.oncemore.json")
        with open(cls.path) as f:
            d = json.load(f)
        d["titles"][0]["chapters"] = [0]
        d["scripts"] = {"twice": TWICE, "dice": DICE}
        d["menus"][0]["buttons"][0]["action"] = "commands:dice"
        d["menus"][0]["buttons"][2]["action"] = "commands:twice"
        with open(cls.path, "w") as f:
            json.dump(d, f)
        cls.iso = os.path.join(cls.tmp, "s.iso")
        cls.rc, cls.out, cls.err = run_cli("--json", "iso", cls.path, "-o", cls.iso, "--fast",
                                           cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_built(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        self.assertEqual([e["message"] for e in json_lines(self.out) if e.get("level") == "warn"], [])

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_counter(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            d.activate(3)                                # first press: back to the menu
            d.wait_menu()
            self.assertEqual(d.domain(), "vtsm")
            d.activate(3)                                # second: title B
            self.assertEqual(d.wait_title(), (2, 1))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_random(self):
        self.assertEqual(self.rc, 0, self.err + self.out)
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            d.wait_menu()
            d.activate(1)                                # random(1) == 1: title A
            self.assertEqual(d.wait_title(), (1, 1))


if __name__ == "__main__":
    unittest.main()
