"""Bold and italic text, letter spacing and kerning.

A family of faces is made here from whatever font the system has (copies
of it whose OS/2 table says bold or italic), so the tests do not depend on
the fonts installed: which face a text is drawn with, refused when the
family lacks it, saved with a style. The characters drawn one by one (for
letter spacing, and kerning off) land where drawtext would put them, and
spread out as asked; Blu-ray menus scale the spacing; the editor offers
the faces the family has.
"""

import json
import os
import shutil
import struct
import tempfile
import unittest
from unittest import mock

from oncemore import bdmenu, fontfaces, png4, tools, userstyles
from oncemore.errors import OncemoreError
from oncemore.menu import MenuBuilder, check_element_fonts, find_font
from oncemore.project import Text, build_project
from oncemore.scaffold import sample_project

from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False

DRAWTEXT = bool(tools.find("ffmpeg")) and tools.has_drawtext()


def base_font():
    """A font of this system that draws Latin letters."""
    try:
        return find_font(text="AVATAR Wave Toyota")
    except OncemoreError:
        return None


def make_face(src, dst, bold, italic):
    """A copy of a font whose OS/2 table says it is bold and/or italic."""
    with open(src, "rb") as f:
        data = bytearray(f.read())
    offset = struct.unpack_from(">I", data, 12)[0] if data[:4] == b"ttcf" else 0
    os2 = fontfaces._table_dir(bytes(data), offset)[b"OS/2"][0]
    struct.pack_into(">H", data, os2 + 4, 700 if bold else 400)
    sel = struct.unpack_from(">H", data, os2 + 62)[0] & ~0x261
    sel |= (0x20 if bold else 0) | (0x01 if italic else 0) | (0x40 if not (bold or italic) else 0)
    struct.pack_into(">H", data, os2 + 62, sel)
    with open(dst, "wb") as f:
        f.write(data)
    return dst


BASE = base_font()


@unittest.skipUnless(BASE, "needs a font")
class TestFaces(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-faces-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fontfaces.faces.cache_clear()
        fontfaces.font.cache_clear()
        ext = os.path.splitext(BASE)[1]
        self.regular = make_face(BASE, os.path.join(self.tmp, f"Fam-Regular{ext}"), False, False)
        self.bold = make_face(BASE, os.path.join(self.tmp, f"Fam-Bold{ext}"), True, False)
        self.italic = make_face(BASE, os.path.join(self.tmp, f"Fam-Italic{ext}"), False, True)

    def test_faces_of_the_family(self):
        faces = fontfaces.faces(self.regular)
        self.assertEqual(faces[(False, False)], self.regular)
        self.assertEqual(faces[(True, False)], self.bold)
        self.assertEqual(faces[(False, True)], self.italic)
        self.assertEqual(fontfaces.face(self.regular, bold=True), self.bold)
        self.assertEqual(fontfaces.face(self.bold, bold=False), self.regular)
        self.assertIsNone(fontfaces.face(self.regular, bold=True, italic=True))
        # (a font of another family next to it is not one of its faces)
        self.assertEqual(fontfaces.font(self.regular).family, fontfaces.font(BASE).family)

    def test_advances_and_spacing(self):
        f = fontfaces.font(self.regular)
        offs, width = f.offsets("ABCD", 40)
        self.assertEqual(offs[0], 0)
        self.assertTrue(all(b > a for a, b in zip(offs, offs[1:])))
        spaced, wide = f.offsets("ABCD", 40, spacing=7, kerning=False)
        plain, _ = f.offsets("ABCD", 40, kerning=False)
        self.assertAlmostEqual(wide - f.offsets("ABCD", 40, kerning=False)[1], 21, places=6)
        self.assertEqual([round(b - a, 6) for a, b in zip(plain, spaced)], [0, 7, 14, 21])

    def test_kerning_pairs(self):
        f = fontfaces.font(BASE)
        pairs = [p for p in ("AV", "AT", "To", "Ty", "LT", "Yo", "VA", "Te", "AW", "We")
                 if f.kern(f.glyph(p[0]), f.glyph(p[1]))]
        if not pairs:
            self.skipTest(f"{os.path.basename(BASE)} has no kerning")
        p = pairs[0]
        on, _ = f.offsets(p, 100)
        off, _ = f.offsets(p, 100, kerning=False)
        self.assertNotAlmostEqual(on[1], off[1])

    def test_dejavu_kerns_av(self):
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if not os.path.isfile(path):
            self.skipTest("needs DejaVu Sans")
        f = fontfaces.font(path)
        # (its GPOS kern feature; AV and To tighten)
        self.assertLess(f.kern(f.glyph("A"), f.glyph("V")), 0)
        self.assertLess(f.kern(f.glyph("T"), f.glyph("o")), 0)
        self.assertEqual(f.kern(f.glyph("H"), f.glyph("H")), 0)

    def test_missing_face_refused(self):
        p = build_project(sample_project(), os.path.join(self.tmp, "p", "project.oncemore.json"),
                          check_files=False)
        m = p.menus[0]
        m.texts.append(Text("Bold", 40, 40, 30, "#FFFFFF", font=self.regular, bold=True))
        check_element_fonts(p, self.regular)
        m.texts.append(Text("Both", 40, 90, 30, "#FFFFFF", font=self.regular, bold=True,
                            italic=True))
        with self.assertRaises(OncemoreError) as e:
            check_element_fonts(p, self.regular)
        self.assertIn("no bold italic face", str(e.exception))
        self.assertIn("next to", e.exception.hint)
        # (the disc's font too)
        m.texts[-1] = Text("Italic", 40, 90, 30, "#FFFFFF", italic=True)
        check_element_fonts(p, self.regular)
        lone = make_face(BASE, os.path.join(self.tmp, "lone", "Lone.ttf") if
                         os.makedirs(os.path.join(self.tmp, "lone")) is None else "", False, False)
        with mock.patch("oncemore.fontfaces._candidates", lambda path, family: iter([path])):
            fontfaces.faces.cache_clear()
            with self.assertRaises(OncemoreError):
                check_element_fonts(p, lone)

    def test_style_keeps_its_face(self):
        lib = os.path.join(self.tmp, "lib")
        a, b = os.path.join(self.tmp, "a"), os.path.join(self.tmp, "b")
        os.makedirs(os.path.join(a, "media"))
        ext = os.path.splitext(self.regular)[1]
        for src in (self.regular, self.bold):
            shutil.copy(src, os.path.join(a, "media", os.path.basename(src)))
        fontfaces.faces.cache_clear()
        with mock.patch.dict(os.environ, {"ONCEMORE_STYLES": lib}):
            sid = userstyles.save({"font": f"media/Fam-Regular{ext}", "bold": True,
                                   "letter_spacing": 4, "kerning": False, "size": 40},
                                  "Bold title", a)
            props = userstyles.list_styles()[0]["props"]
            self.assertEqual((props["bold"], props["letter_spacing"], props["kerning"]),
                             (True, 4, False))
            self.assertEqual(sorted(os.listdir(os.path.join(lib, sid, "files"))),
                             [f"Fam-Bold{ext}", f"Fam-Regular{ext}"])
            props = userstyles.apply(sid, b)
        self.assertEqual(sorted(os.listdir(os.path.join(b, "media"))),
                         [f"Fam-Bold{ext}", f"Fam-Regular{ext}"])
        fontfaces.faces.cache_clear()
        self.assertEqual(fontfaces.face(os.path.join(b, props["font"]), bold=True),
                         os.path.join(b, "media", f"Fam-Bold{ext}"))


class TestProject(unittest.TestCase):
    def test_fields(self):
        data = sample_project()
        data["menus"][0].setdefault("texts", []).append(
            {"text": "Spaced", "x": 10, "y": 10, "bold": True, "italic": True,
             "letter_spacing": 6, "kerning": False})
        data["menus"][0]["buttons"][0].update(letter_spacing=-2, bold=True)
        p = build_project(data, "/virtual/project.oncemore.json", check_files=False)
        t = p.menus[0].texts[-1]
        self.assertEqual((t.bold, t.italic, t.letter_spacing, t.kerning), (True, True, 6, False))
        b = p.menus[0].buttons[0]
        self.assertEqual((b.bold, b.italic, b.letter_spacing, b.kerning), (True, False, -2, True))
        data["menus"][0]["texts"][-1]["letter_spacing"] = 500
        with self.assertRaises(Exception):
            build_project(data, "/virtual/project.oncemore.json", check_files=False)

    def test_bluray_scales_the_spacing(self):
        data = sample_project()
        data["menus"][0]["texts"] = [{"text": "Spaced", "x": 10, "y": 10, "size": 30,
                                      "letter_spacing": 10, "line_spacing": 10}]
        p = build_project(data, "/virtual/project.oncemore.json", check_files=False)
        hd = bdmenu.scale_menu(p.menus[0], p.disc, lambda path: {"width": 100, "height": 100})
        t = hd.texts[0]
        self.assertEqual(t.letter_spacing, t.line_spacing)
        self.assertGreater(t.letter_spacing, 10)


@unittest.skipUnless(BASE and DRAWTEXT, "needs ffmpeg with drawtext and a font")
class TestRendering(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-spacing-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.p = build_project(sample_project(), os.path.join(self.tmp, "project.oncemore.json"),
                               check_files=False)
        self.mb = MenuBuilder(self.p, self.tmp, font=BASE)

    def mask(self, name, t):
        return self.mb.glyphs(name, t.text, t)

    def test_one_by_one_lands_where_drawtext_does(self):
        # the same text drawn at once and a character at a time: the same box
        W, H = self.p.disc.width, self.p.disc.height
        for i, t in enumerate([Text("AVATAR Toyota Wave", 40, 60, 48, "#FFFFFF"),
                               Text("One\nLonger second line\nthird", 40, 200, 36, "#FFFFFF",
                                    align="center", line_spacing=6),
                               Text("Right\nAV two", 60, 340, 40, "#FFFFFF", align="right")]):
            tf = self.mb._textfile(f"same{i}.txt", t.text)
            at_once = self.mb._render_gray(self.mb._drawtext(tf, t.x, t.y, t.size, "#FFFFFF", t,
                                                             style=False))
            one_by_one = self.mb._render_gray(self.mb._spaced(tf, t.x, t.y, t.size, "#FFFFFF",
                                                              t, False))

            def box(g):
                lit = [k for k in range(len(g)) if g[k] > 110]
                xs = [k % self.mb.dw for k in lit]
                ys = [k // self.mb.dw for k in lit]
                return min(xs), min(ys), max(xs), max(ys)
            a, b = box(at_once), box(one_by_one)
            for u, v in zip(a, b):
                self.assertLessEqual(abs(u - v), 1, (t.text, a, b))

    def test_letter_spacing_spreads_the_text(self):
        plain = self.mask("plain", Text("HHHHHH", 40, 100, 40, "#FFFFFF")).bbox()
        wide = self.mask("wide", Text("HHHHHH", 40, 100, 40, "#FFFFFF",
                                      letter_spacing=12)).bbox()
        tight = self.mask("tight", Text("HHHHHH", 40, 100, 40, "#FFFFFF",
                                        letter_spacing=-3)).bbox()
        grow = (wide[2] - wide[0]) - (plain[2] - plain[0])
        # five gaps of 12 display pixels, in storage pixels
        self.assertAlmostEqual(grow, 5 * 12 / self.mb.sx, delta=3)
        self.assertLess(tight[2] - tight[0], plain[2] - plain[0])
        self.assertEqual((wide[0], wide[1], wide[3]), (plain[0], plain[1], plain[3]))

    def test_kerning_off(self):
        f = fontfaces.font(BASE)
        pair = next((p for p in ("AV", "To", "AT", "Ty", "LT", "VA", "AW")
                     if f.kern(f.glyph(p[0]), f.glyph(p[1])) < 0), None)
        if pair is None:
            self.skipTest(f"{os.path.basename(BASE)} kerns none of the pairs tried")
        text = pair * 4
        kerned = self.mask("kerned", Text(text, 40, 100, 48, "#FFFFFF")).bbox()
        loose = self.mask("loose", Text(text, 40, 100, 48, "#FFFFFF", kerning=False)).bbox()
        self.assertGreater(loose[2] - loose[0], kerned[2] - kerned[0])

    def test_bold_is_drawn_with_the_bold_face(self):
        ext = os.path.splitext(BASE)[1]
        regular = make_face(BASE, os.path.join(self.tmp, f"Fam-Regular{ext}"), False, False)
        bold = make_face(BASE, os.path.join(self.tmp, f"Fam-Bold{ext}"), True, False)
        fontfaces.faces.cache_clear()
        t = Text("Bold", 40, 40, 30, "#FFFFFF", font=regular, bold=True)
        self.assertEqual(self.mb.face_path(t), bold)
        link = os.path.join(self.mb.work, self.mb.font_for(t))
        self.assertEqual(os.path.realpath(link), os.path.realpath(bold))
        self.assertIsNotNone(self.mask("bold", t).bbox())


@unittest.skipUnless(BASE, "needs a font")
class TestEditor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-faces-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        fontfaces.faces.cache_clear()
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        ext = os.path.splitext(BASE)[1]
        self.ext = ext
        make_face(BASE, os.path.join(self.dir, "media", f"Fam-Regular{ext}"), False, False)
        make_face(BASE, os.path.join(self.dir, "media", f"Fam-Bold{ext}"), True, False)

    def test_api(self):
        code, r = self.s.call(f"/api/font_faces?path=media/Fam-Regular{self.ext}")
        self.assertEqual(code, 200)
        self.assertEqual(r["faces"]["bold"], {"path": f"media/Fam-Bold{self.ext}"})
        self.assertEqual(r["faces"]["regular"], {"path": f"media/Fam-Regular{self.ext}"})
        self.assertNotIn("italic", r["faces"])
        self.assertEqual(self.s.call("/api/font_faces?path=../x.ttf")[0], 403)

    @unittest.skipUnless(PLAYWRIGHT, "needs playwright")
    def test_character_panel(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            data = json.load(f)
        data["menus"][0]["texts"] = [{"text": "Hello", "x": 100, "y": 100,
                                      "font": f"media/Fam-Regular{self.ext}"}]
        self.s.call("/api/project", "PUT", {"project": data})
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.locator(".el.text").first.click()
            page.locator("#st-bold").wait_for()

            def until(expr):
                for _ in range(600):
                    if page.evaluate(f"() => !!({expr})"):
                        return
                    page.wait_for_timeout(100)
                raise AssertionError(expr)
            # the family has no italic: offered off; bold is there
            until("document.querySelector('#st-italic').disabled")
            self.assertFalse(page.is_disabled("#st-bold"))
            page.check("#st-bold")
            page.fill("#st-tracking", "8")
            page.dispatch_event("#st-tracking", "change")
            page.uncheck("#st-kerning")

            def text():
                with open(os.path.join(self.dir, "project.oncemore.json")) as f:
                    return json.load(f)["menus"][0]["texts"][0]
            for _ in range(100):
                if text().get("kerning") is False:
                    break
                page.wait_for_timeout(100)
            t = text()
            self.assertEqual((t.get("bold"), t.get("letter_spacing"), t.get("kerning")),
                             (True, 8, False))
            # the stage draws it with the bold file, spaced
            until("getComputedStyle(document.querySelector('.el.text')).letterSpacing !== 'normal'")
            family = page.evaluate("getComputedStyle(document.querySelector('.el.text')).fontFamily")
            self.assertIn("Bold", family)
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
