import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from oncemore import usertemplates as U


class TestUserTemplates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-utpl-")
        self.lib = os.path.join(self.tmp, "library")
        self.env = mock.patch.dict(os.environ, {"ONCEMORE_TEMPLATES": self.lib})
        self.env.start()
        self.a = os.path.join(self.tmp, "a")
        os.makedirs(os.path.join(self.a, "media"))
        with open(os.path.join(self.a, "media", "bg.png"), "wb") as f:
            f.write(b"\\x89PNG background")
        self.menu = {"id": "main", "background": "media/bg.png", "end_action": "title:t9",
                     "buttons": [{"id": "p", "label": "PLAY", "x": 80, "y": 200, "action": "title:t1"},
                                 {"id": "c", "label": "SCENE 2", "x": 80, "y": 260, "action": "chapter:t1:2"},
                                 {"id": "s", "label": "SETUP", "x": 80, "y": 320, "action": "menu:setup"},
                                 {"id": "x", "label": "ALL", "x": 80, "y": 380, "action": "playall"}],
                     "texts": [{"text": "media/not-a-file.png", "x": 0, "y": 0}]}

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_list_apply_delete(self):
        tid = U.save(self.menu, "My Main Menu", self.a)
        self.assertEqual(tid, "my_main_menu")
        self.assertEqual(U.save(self.menu, "My Main Menu", self.a), "my_main_menu_2")   # no overwrite
        with open(os.path.join(self.lib, tid, "template.json")) as f:
            saved = json.load(f)
        self.assertEqual(saved["menu"]["background"], "files/bg.png")              # copied with it
        self.assertEqual(saved["menu"]["texts"][0]["text"], "media/not-a-file.png")  # not a file
        self.assertEqual([t["name"] for t in U.list_templates()], ["My Main Menu", "My Main Menu"])
        # into another project: the picture comes along, links it lacks become stop
        b = os.path.join(self.tmp, "b")
        os.makedirs(os.path.join(b, "media"))
        with open(os.path.join(b, "media", "bg.png"), "wb") as f:
            f.write(b"another picture")                                      # same name, other file
        other = {"titles": [{"id": "t1"}], "menus": [], "playlists": []}
        menu = U.apply(tid, other, b, "main2")
        self.assertEqual(menu["id"], "main2")
        self.assertEqual(menu["background"], "media/bg_2.png")
        with open(os.path.join(b, "media", "bg_2.png"), "rb") as f:
            self.assertEqual(f.read(), b"\\x89PNG background")
        self.assertEqual([x["action"] for x in menu["buttons"]],
                         ["title:t1", "chapter:t1:2", "stop", "playall"])
        self.assertNotIn("end_action", menu)
        # applying again reuses the copy that is already there
        self.assertEqual(U.apply(tid, other, b, "main3")["background"], "media/bg_2.png")
        self.assertFalse(os.path.exists(os.path.join(b, "media", "bg_3.png")))
        U.delete(tid)
        self.assertEqual(len(U.list_templates()), 1)

    def test_ids_and_files_stay_inside(self):
        for bad in ("../x", "a/b", "", "X"):
            with self.assertRaises(ValueError):
                U.apply(bad, {}, self.a, "m")
        outside = dict(self.menu, background="../../etc/passwd.png")
        tid = U.save(outside, "outside", self.a)
        with open(os.path.join(self.lib, tid, "template.json")) as f:
            self.assertEqual(json.load(f)["menu"]["background"], "../../etc/passwd.png")
        self.assertEqual(os.listdir(os.path.join(self.lib, tid, "files")), [])
        with self.assertRaises(FileNotFoundError):
            U.apply("missing", {}, self.a, "m")


if __name__ == "__main__":
    unittest.main()
