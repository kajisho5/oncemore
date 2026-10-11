"""The encode cache: what goes into its keys, and how entries are written.

(Rebuilds that reuse it, and --no-cache, are exercised end to end in
test_e2e.TestCacheRomPassthrough.)
"""

import os
import shutil
import tempfile
import threading
import unittest

from oncemore import build
from oncemore.project import build_project
from oncemore.scaffold import sample_project


class TestCacheWrites(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-cache-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_writers_of_one_entry_at_once(self):
        """Several builds storing the same entry together: the entry ends up
        whole (one of theirs), and no half-written file is left behind."""
        cache = os.path.join(self.dir, "cache")
        size = 4 * 2**20
        sources = []
        for k in range(8):
            p = os.path.join(self.dir, f"src{k}.mpg")
            with open(p, "wb") as f:
                f.write(bytes([k]) * size)
            sources.append(p)
        errors = []

        def put(p):
            try:
                build._cache_put(cache, "k", p)
            except Exception as e:          # pragma: no cover (the bug this guards)
                errors.append(e)
        threads = [threading.Thread(target=put, args=(p,)) for p in sources]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(os.listdir(cache), ["k.mpg"])
        with open(os.path.join(cache, "k.mpg"), "rb") as f:
            data = f.read()
        self.assertEqual(len(data), size)
        self.assertEqual(len(set(data)), 1)            # all from one writer

    def test_get(self):
        cache = os.path.join(self.dir, "cache")
        src, out = os.path.join(self.dir, "a.mpg"), os.path.join(self.dir, "out.mpg")
        with open(src, "wb") as f:
            f.write(b"abc")
        self.assertFalse(build._cache_get(cache, "k", out))
        build._cache_put(cache, "k", src)
        self.assertTrue(build._cache_get(cache, "k", out))
        with open(out, "rb") as f:
            self.assertEqual(f.read(), b"abc")
        self.assertFalse(build._cache_get(None, "k", out))   # (not reused: --no-cache)


class TestClean(unittest.TestCase):
    def test_clean_removes_the_cache(self):
        from .helpers import run_cli
        d = tempfile.mkdtemp(prefix="oncemore-clean-")
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            f.write("{}")
        os.makedirs(os.path.join(d, ".oncemore-cache", "encode"))
        with open(os.path.join(d, ".oncemore-cache", "encode", "x.mpg"), "wb") as f:
            f.write(b"0" * 2048)
        rc, out, err = run_cli("--json", "clean", d)
        self.assertEqual(rc, 0, err)
        self.assertIn('"bytes": 2048', out)
        self.assertFalse(os.path.exists(os.path.join(d, ".oncemore-cache")))
        self.assertTrue(os.path.isfile(os.path.join(d, "project.oncemore.json")))
        rc, out, err = run_cli("clean", os.path.join(d, "nowhere"))
        self.assertNotEqual(rc, 0)


class TestMenuKeys(unittest.TestCase):
    """A menu's cache key follows what its thumbnails show."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-cache-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        for name in ("a.mp4", "b.mp4", "song.wav", "red.png", "blue.png"):
            with open(os.path.join(self.dir, name), "wb") as f:
                f.write(name.encode())

    def key(self, title):
        d = sample_project()
        d["titles"] = [title]
        d["menus"] = [{"id": "main", "buttons": [
            {"id": "play", "label": "PLAY", "x": 100, "y": 100, "action": f"title:{title['id']}",
             "thumbnail": {"x": 300, "y": 100, "w": 160, "h": 90}}]}]
        d["disc"]["first_play"] = "menu:main"
        p = build_project(d, os.path.join(self.dir, "project.oncemore.json"), check_files=False)
        return build.menu_cache_key(p, p.menus[0], None)

    def test_sound_title_picture(self):
        song = {"id": "t", "source": "song.wav", "picture": "red.png"}
        self.assertNotEqual(self.key(song), self.key(dict(song, picture="blue.png")))

    def test_clips_after_the_first(self):
        clips = {"id": "t", "clips": [{"source": "a.mp4"}, {"source": "b.mp4", "in": 2}]}
        other = {"id": "t", "clips": [{"source": "a.mp4"}, {"source": "b.mp4", "in": 5}]}
        self.assertNotEqual(self.key(clips), self.key(other))
        self.assertEqual(self.key(clips), self.key(dict(clips)))


if __name__ == "__main__":
    unittest.main()
