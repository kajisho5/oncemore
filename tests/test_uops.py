"""User operations: the remote keys a title or a menu turns off.

The masks as the disc formats spell them, the project's checks, and the
simulator ignoring those keys. (The discs themselves are read back by
libdvdnav in test_e2e.TestUserOperations and by libbluray in
test_bluray.TestBlurayUserOperations.)
"""

import unittest

from oncemore import bluray, uops
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project
from oncemore.simulate import Simulator


def project(data):
    return build_project(data, "/virtual/project.oncemore.json", check_files=False)


class TestMasks(unittest.TestCase):
    def test_dvd(self):
        # UOP n is bit n of the PGC's 32-bit field
        self.assertEqual(uops.dvd_mask([]), 0)
        self.assertEqual(uops.dvd_mask(["next"]), 1 << 7)
        self.assertEqual(uops.dvd_mask(["fast_forward", "rewind"]), 1 << 8 | 1 << 9)
        self.assertEqual(uops.dvd_mask(["menu"]), 0b11111 << 11)
        self.assertEqual(uops.dvd_mask(["search"]), 1 | 2 | 4 | 32)
        self.assertEqual(uops.dvd_mask(["audio", "subtitle"]), 3 << 20)

    def test_bluray(self):
        # bit 0 of the UO mask table is its most significant
        self.assertEqual(uops.bd_mask(["menu"]), 1 << 63 | 1 << (63 - 24))
        self.assertEqual(uops.bd_mask(["next", "prev"]), 1 << 59 | 1 << 58)
        self.assertEqual(uops.bd_mask(["stop"]), 1 << 56)

    def test_every_name_has_both(self):
        self.assertEqual(set(uops.NAMES), set(uops.DVD_UOPS))
        self.assertEqual(set(uops.NAMES), set(uops.BD_UOS))

    def test_mpls_carries_them(self):
        item = ("00001", 0, 90000, 1, 4, [], [], False, 0, uops.bd_mask(["next"]))
        data = bluray.mpls([item], [], uops.bd_mask(["menu"]))
        self.assertEqual(data[48:56], uops.bd_mask(["menu"]).to_bytes(8, "big"))
        self.assertIn(uops.bd_mask(["next"]).to_bytes(8, "big"), data[56:])
        # (an item without one: none)
        self.assertEqual(bluray.mpls([item[:9]], [])[48:56], bytes(8))


class TestProject(unittest.TestCase):
    def test_parsed_in_order(self):
        d = sample_project()
        d["titles"][0]["prohibit"] = ["menu", "next", "menu"]
        d["menus"][0]["prohibit"] = ["title"]
        p = project(d)
        self.assertEqual(p.titles[0].prohibit, ["next", "menu"])
        self.assertEqual(p.titles[1].prohibit, [])
        self.assertEqual(p.menus[0].prohibit, ["title"])

    def test_unknown_key(self):
        d = sample_project()
        d["titles"][0]["prohibit"] = ["eject"]
        with self.assertRaises(ProjectError) as cm:
            project(d)
        self.assertIn("titles[0].prohibit", str(cm.exception.issues))


class TestSimulator(unittest.TestCase):
    def test_keys_turned_off_do_nothing(self):
        d = sample_project()
        d["disc"]["first_play"] = "title:t1"
        d["titles"][0]["prohibit"] = ["next", "menu"]
        d["menus"][0]["prohibit"] = ["title"]
        sim = Simulator(project(d))
        s = sim.start()
        self.assertEqual((s["domain"], s["title"], s["chapter"]), ("title", "t1", 1))
        sim.press(s, "next")
        self.assertEqual(s["chapter"], 1)
        self.assertEqual(s["log"], ["next not allowed here"])
        sim.press(s, "menu")
        self.assertEqual(s["domain"], "title")
        sim.press(s, "title")                       # (allowed here: the title menu)
        self.assertEqual((s["domain"], s["menu"]), ("menu", "main"))
        sim.press(s, "title")
        self.assertEqual(s["log"], ["title not allowed here"])
        sim.press(s, "enter")                       # PLAY ALL
        self.assertEqual(s["title"], "t1")


if __name__ == "__main__":
    unittest.main()
