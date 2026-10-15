"""The promises in README ("What oncemore promises"), checked so that none of
them can disappear by accident: a Mac app for both architectures, a disc
image written without any burner (burning is an optional step on request), an app that runs in a browser, and an open,
offline, protection-free tool."""

import ast
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def package_sources():
    for base, _, files in os.walk(os.path.join(ROOT, "oncemore")):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                with open(path, encoding="utf-8") as f:
                    yield os.path.relpath(path, ROOT), f.read()


class TestMacApp(unittest.TestCase):
    def test_built_and_smoke_tested_on_every_change(self):
        ci = read(".github", "workflows", "ci.yml")
        self.assertRegex(ci, r"\n  macos-app:")
        self.assertIn("Build Oncemore.app", ci)
        self.assertIn("Smoke test", ci)
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "macos")))

    def test_released_for_apple_silicon_and_intel(self):
        rel = read(".github", "workflows", "release.yml")
        self.assertRegex(rel, r"macos-\d+-intel|macos-13")
        self.assertRegex(rel, r"arm64|macos-(14|15|latest)")

    def test_signed_and_notarised_from_1_0(self):
        # a release from 1.0 on is refused without the signing secrets, so
        # the app opens without "Open Anyway" (DECISIONS §124)
        rel = read(".github", "workflows", "release.yml")
        self.assertIn('""|v0.*) ;;', rel)
        self.assertIn("must be signed and notarised", rel)
        self.assertIn("NOTARIZE=1", rel)
        from oncemore import __version__
        self.assertNotRegex(__version__, r"^0\.")
        self.assertNotIn("not notarised", read("README.md"))
        self.assertNotIn("まだ公証", read("README.ja.md"))
        notes = read("docs", "release-notes", f"v{__version__}.md")
        self.assertIn(f"Oncemore-{__version__}-arm64.zip", notes)
        self.assertNotIn("Open Anyway", notes)

    def test_release_run_by_hand_can_publish(self):
        # from 1.0 a release is a draft unless the run by hand says publish
        # (DECISIONS §128)
        rel = read(".github", "workflows", "release.yml")
        dispatch = rel.split("workflow_dispatch:", 1)[1].split("permissions:", 1)[0]
        self.assertRegex(dispatch, r"publish:\n(\s+.*\n)*?\s+type: boolean")
        self.assertRegex(dispatch, r"publish:\n(\s+.*\n)*?\s+default: false")
        self.assertIn("PUBLISH: ${{ inputs.publish && 'yes' || '' }}", rel)
        self.assertIn('if [ -n "$PUBLISH" ]; then kind="--latest"; else kind="--draft"; fi', rel)
        self.assertIn('v0.*) kind="--prerelease"', rel)
        self.assertIn("`publish`", read("README.md"))
        self.assertIn("`publish`", read("README.ja.md"))


class TestDiscImage(unittest.TestCase):
    def test_iso_and_folder_output(self):
        from oncemore import cli, tools
        parser_src = read("oncemore", "cli.py")
        for cmd in ('"iso"', '"build"'):
            self.assertIn(f"add_parser({cmd}", parser_src)
        self.assertTrue(hasattr(tools, "iso_tool"))
        self.assertTrue(callable(cli.main))

    def test_iso_built_and_played_in_ci(self):
        ci = read(".github", "workflows", "ci.yml")
        self.assertIn("unittest", ci)                       # e2e builds ISOs, libdvdnav plays them
        self.assertIn("Completion check (init + iso", ci)
        e2e = read("tests", "test_e2e.py")
        self.assertIn('run_cli("--json", "iso"', e2e)
        self.assertIn("dvdnav_sim.DvdSim", e2e)

    def test_no_iso_tool_needed(self):
        # the image is written by oncemore itself, whatever is installed
        from oncemore import tools
        old = os.environ.get("PATH")
        try:
            os.environ["PATH"] = ""
            tools.reset_cache()
            self.assertEqual(tools.iso_tool(), ("builtin", None))
            tools.require([], need_iso=True)
        finally:
            os.environ["PATH"] = old or ""
            tools.reset_cache()
        # (udfkit's writer, carried inside the package: DECISIONS §106)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "oncemore", "_vendor", "udfkit", "dvd.py")))

    def test_image_without_a_burner(self):
        # the image never needs a drive: only the burn step, run on request,
        # knows about burners, and building does not use it
        for path, src in package_sources():
            if path != os.path.join("oncemore", "burn.py"):
                self.assertNotRegex(src, r"\b(drutil|growisofs|cdrecord|wodim)\b", path)
        for name in ("build.py", "author.py", "discimage.py", "iso.py",
                     os.path.join("_vendor", "udfkit", "dvd.py")):
            self.assertNotIn("burn", read("oncemore", name).replace("burned", ""), name)


class TestBrowserApp(unittest.TestCase):
    def test_served_locally_as_a_web_page(self):
        self.assertIn('add_parser("gui"', read("oncemore", "cli.py"))
        html = read("oncemore", "gui", "static", "index.html")
        self.assertIn('src="app.js"', html)
        server = read("oncemore", "gui", "server.py")
        self.assertIn('"127.0.0.1"', server)                # never on the network

    def test_no_build_step_or_frontend_dependencies(self):
        static = os.path.join(ROOT, "oncemore", "gui", "static")
        self.assertFalse(os.path.exists(os.path.join(static, "package.json")))
        for name in os.listdir(static):
            if name.endswith((".html", ".js", ".css")):
                src = read("oncemore", "gui", "static", name)
                self.assertNotRegex(src, r"(src|href)=\"https?://", name)
                self.assertNotRegex(src, r"\bimport\s.+\bfrom\s+['\"]https?:", name)


class TestOpen(unittest.TestCase):
    def test_gpl_and_no_runtime_dependencies(self):
        self.assertIn("GNU GENERAL PUBLIC LICENSE", read("LICENSE"))
        self.assertIn("Version 3", read("LICENSE"))
        self.assertRegex(read("pyproject.toml"), r"dependencies = \[\]")

    def test_no_outbound_network(self):
        banned = {"urllib.request", "http.client", "requests", "httpx", "ftplib", "smtplib"}
        for path, src in package_sources():
            tree = ast.parse(src)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
                for n in names:
                    self.assertNotIn(n, banned, f"{path} imports {n}")

    def test_no_copy_protection(self):
        for path, src in package_sources():
            self.assertNotRegex(src.lower(), r"macrovision|cprm|aacs|css[_ ]?encrypt|region[_ ]?lock",
                                path)
        self.assertIn("no copy protection", read("README.md").lower())

    def test_no_third_party_product_names_in_the_app(self):
        names = re.compile(r"encore|adobe|dvd studio|idvd|dvdarchitect|photoshop elements",
                           re.I)
        for name in ("app.js", "index.html", "styleguide.html"):
            self.assertIsNone(names.search(read("oncemore", "gui", "static", name)), name)
        self.assertIsNone(names.search(read("docs", "DESIGN.md")))


if __name__ == "__main__":
    unittest.main()
