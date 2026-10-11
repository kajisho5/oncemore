"""`oncemore mcp`: the MCP server AI assistants drive oncemore through.

Both protocol eras (2026-07-28: version per request, server/discover; the
earlier ones: an initialize handshake), the tools on a project, the
folders it may not touch, and the stdio framing of a real process.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from oncemore import mcp, tools

from .helpers import have

MODERN = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
          "io.modelcontextprotocol/clientCapabilities": {}}


class McpCase(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="oncemore-mcp-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.server = mcp.Server([self.root])
        self.n = 0

    def rpc(self, method, params=None, meta=True):
        self.n += 1
        params = dict(params or {})
        if meta:
            params["_meta"] = MODERN
        return self.server.handle({"jsonrpc": "2.0", "id": self.n, "method": method,
                                   "params": params})

    def call(self, name, **args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})
        self.assertIn("result", r, r)
        return r["result"]


class TestProtocol(McpCase):
    def test_discover(self):
        r = self.rpc("server/discover")["result"]
        self.assertEqual(r["resultType"], "complete")
        self.assertEqual(r["supportedVersions"][0], "2026-07-28")
        self.assertIn("2025-11-25", r["supportedVersions"])
        self.assertEqual(r["capabilities"], {"tools": {"listChanged": False}})
        self.assertEqual(r["_meta"]["io.modelcontextprotocol/serverInfo"]["name"], "oncemore")
        self.assertIn("project", r["instructions"])

    def test_tools_listed(self):
        tools_ = self.rpc("tools/list")["result"]["tools"]
        names = [t["name"] for t in tools_]
        self.assertEqual(names, ["project_format", "create_project", "read_project",
                                 "write_project", "edit_project", "import_media", "validate",
                                 "preview_menu", "simulate", "import_psd", "build",
                                 "build_status", "doctor"])
        for t in tools_:
            self.assertEqual(t["inputSchema"]["type"], "object", t["name"])
            self.assertTrue(t["description"])
            self.assertNotIn("fn", t)
        ro = {t["name"] for t in tools_ if t["annotations"]["readOnlyHint"]}
        self.assertIn("read_project", ro)
        self.assertNotIn("build", ro)

    def test_version_rules(self):
        # an unknown version: the supported ones, to retry with
        r = self.rpc("tools/list", {"_meta": dict(MODERN, **{
            "io.modelcontextprotocol/protocolVersion": "1900-01-01"})}, meta=False)
        self.assertEqual(r["error"]["code"], -32022)
        self.assertEqual(r["error"]["data"]["requested"], "1900-01-01")
        self.assertIn("2026-07-28", r["error"]["data"]["supported"])
        # no version at all and no session: malformed
        self.assertEqual(self.rpc("tools/list", meta=False)["error"]["code"], -32602)
        # (capabilities are required too)
        r = self.rpc("tools/list", {"_meta": {"io.modelcontextprotocol/protocolVersion":
                                              "2026-07-28"}}, meta=False)
        self.assertEqual(r["error"]["code"], -32602)
        self.assertEqual(self.rpc("nothing/here")["error"]["code"], -32601)

    def test_earlier_revisions_with_initialize(self):
        r = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "t", "version": "1"}}, meta=False)
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(r["result"]["serverInfo"]["name"], "oncemore")
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0",
                                              "method": "notifications/initialized"}))
        r = self.rpc("tools/list", meta=False)["result"]
        self.assertNotIn("resultType", r)                  # (that revision has none)
        self.assertTrue(r["tools"])
        # a revision it does not know: the newest earlier one it does
        r = self.rpc("initialize", {"protocolVersion": "2099-01-01"}, meta=False)
        self.assertEqual(r["result"]["protocolVersion"], "2025-11-25")

    def test_bad_messages(self):
        self.assertEqual(self.server.handle([1, 2])["error"]["code"], -32600)
        self.assertEqual(self.server.handle({"id": 1})["error"]["code"], -32600)
        r = self.rpc("tools/call", {"name": "nope", "arguments": {}})
        self.assertEqual(r["error"]["code"], -32602)
        self.assertEqual(self.rpc("ping")["result"]["resultType"], "complete")


class TestTools(McpCase):
    def folder(self, name="disc"):
        return os.path.join(self.root, name)

    def test_create_edit_and_check(self):
        r = self.call("create_project", folder=self.folder(), label="MY_FILM")
        self.assertFalse(r["isError"], r)
        self.assertEqual(r["structuredContent"]["project"]["disc"]["label"], "MY_FILM")
        # a second time: refused unless asked
        self.assertTrue(self.call("create_project", folder=self.folder())["isError"])
        # media come in under media/, with their project paths
        src = os.path.join(self.root, "my clip.srt")
        with open(src, "w") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
        r = self.call("import_media", folder=self.folder(), files=[src, src])
        self.assertEqual(r["structuredContent"]["imported"],
                         ["media/my clip.srt", "media/my clip-2.srt"])
        # an invalid change is not written, and says why
        with open(os.path.join(self.folder(), "media", "a.mp4"), "wb") as f:
            f.write(b"\0" * 16)
        film = [{"id": "film", "source": "media/a.mp4"}]
        r = self.call("edit_project", folder=self.folder(),
                      patch={"titles": film, "menus": [{"id": "main", "buttons": [
                          {"id": "go", "label": "GO", "x": 100, "y": 100, "action": "title:nope"}]}]})
        self.assertTrue(r["isError"])
        self.assertIn("not written", r["content"][0]["text"])
        self.assertIn("nope", r["content"][0]["text"])
        with open(os.path.join(self.folder(), "project.oncemore.json")) as f:
            self.assertEqual(json.load(f)["menus"], [])
        # a valid one is (merge patch: null deletes)
        r = self.call("edit_project", folder=self.folder(),
                      patch={"titles": film, "disc": {"label": "OTHER", "target": None}})
        self.assertFalse(r["isError"], r)
        disc = r["structuredContent"]["project"]["disc"]
        self.assertEqual(disc["label"], "OTHER")
        self.assertNotIn("target", disc)
        r = self.call("project_format")
        self.assertIn("titles", r["structuredContent"]["schema"]["properties"])

    def test_only_inside_the_roots(self):
        for args in ({"folder": "/etc"}, {"folder": "relative/path"},
                     {"folder": os.path.join(self.root, "..", "escape")}):
            r = self.call("read_project", **args)
            self.assertTrue(r["isError"], args)
        os.makedirs(self.folder())
        self.call("create_project", folder=self.folder())
        r = self.call("import_media", folder=self.folder(), files=["/etc/hostname"])
        self.assertTrue(r["isError"])
        self.assertIn("outside", r["content"][0]["text"])

    def test_merge_patch(self):
        self.assertEqual(mcp.merge_patch({"a": 1, "b": {"c": 2, "d": 3}},
                                         {"b": {"c": None, "e": 4}, "f": [1]}),
                         {"a": 1, "b": {"d": 3, "e": 4}, "f": [1]})

    @unittest.skipUnless(have("ffmpeg", "ffprobe") and tools.has_drawtext(),
                         "needs ffmpeg with drawtext")
    def test_sample_menu_preview_and_simulator(self):
        r = self.call("create_project", folder=self.folder(), sample=True)
        self.assertFalse(r["isError"], r)
        self.assertTrue(r["structuredContent"]["check"]["valid"])
        r = self.call("preview_menu", folder=self.folder())
        self.assertFalse(r["isError"], r)
        image = r["content"][0]
        self.assertEqual((image["type"], image["mimeType"]), ("image", "image/png"))
        import base64
        self.assertEqual(base64.b64decode(image["data"])[:8], b"\x89PNG\r\n\x1a\n")
        r = self.call("simulate", folder=self.folder(), keys=["enter"])
        steps = r["structuredContent"]["steps"]
        self.assertEqual(steps[0]["view"][:2], ["menu", "main"])
        self.assertEqual(steps[1]["view"][0], "title")          # PLAY ALL
        r = self.call("validate", folder=self.folder())
        self.assertFalse(r["isError"], r)
        self.assertTrue(r["structuredContent"]["valid"])


@unittest.skipUnless(have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext(),
                     "needs ffmpeg with drawtext and dvdauthor")
class TestBuild(McpCase):
    def test_build_in_the_background(self):
        import time
        folder = os.path.join(self.root, "disc")
        self.assertFalse(self.call("create_project", folder=folder, sample=True)["isError"])
        r = self.call("build", folder=folder, output="iso", fast=True)
        self.assertFalse(r["isError"], r)
        job = r["structuredContent"]["job"]
        self.assertTrue(self.call("build", folder=folder)["isError"])   # (one at a time)
        for _ in range(600):
            st = self.call("build_status", folder=folder, job=job)["structuredContent"]
            if st["done"]:
                break
            time.sleep(1)
        self.assertTrue(st["ok"], st)
        self.assertTrue(os.path.isfile(st["result"]["iso"]))
        self.assertTrue(st["steps"])
        self.assertTrue(self.call("build_status", folder=folder, job="nope")["isError"])


class TestStdio(unittest.TestCase):
    """A real `oncemore mcp` process: one JSON message per line, nothing else on stdout."""

    def test_process(self):
        root = os.path.realpath(tempfile.mkdtemp(prefix="oncemore-mcp-io-"))
        self.addCleanup(shutil.rmtree, root, True)
        p = subprocess.Popen([sys.executable, "-m", "oncemore", "mcp", "--root", root],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": MODERN}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                "not json",
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                    "_meta": MODERN, "name": "create_project",
                    "arguments": {"folder": os.path.join(root, "d")}}}]
        out, err = p.communicate("\n".join(m if isinstance(m, str) else json.dumps(m)
                                           for m in msgs) + "\n", timeout=60)
        self.assertEqual(p.returncode, 0, err)
        lines = [json.loads(line) for line in out.splitlines()]
        self.assertEqual([m.get("id") for m in lines], [1, None, 2])     # (no reply to the notification)
        self.assertEqual(lines[1]["error"]["code"], -32700)
        self.assertFalse(lines[2]["result"]["isError"], lines[2])
        self.assertTrue(os.path.isfile(os.path.join(root, "d", "project.oncemore.json")))


if __name__ == "__main__":
    unittest.main()
