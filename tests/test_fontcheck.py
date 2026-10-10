import glob
import os
import struct
import tempfile
import unittest

from oncemore import fontcheck


def cmap_format4(segments):
    """segments: [(start, end, delta)]; a terminating 0xFFFF segment is added."""
    segs = list(segments) + [(0xFFFF, 0xFFFF, 1)]
    n = len(segs)
    body = struct.pack(f">{n}H", *[e for _, e, _ in segs]) + b"\0\0"
    body += struct.pack(f">{n}H", *[s for s, _, _ in segs])
    body += struct.pack(f">{n}h", *[d for _, _, d in segs])
    body += struct.pack(f">{n}H", *([0] * n))
    head = struct.pack(">HHHHHHH", 4, 14 + len(body), 0, 2 * n, 0, 0, 0)
    return head + body


def cmap_format12(groups):
    """groups: [(start, end, first_glyph)]"""
    body = b"".join(struct.pack(">III", *g) for g in groups)
    return struct.pack(">HHIII", 12, 0, 16 + len(body), 0, len(groups)) + body


def sfnt(subtable, pid=3, eid=1):
    cmap = struct.pack(">HHHHI", 0, 1, pid, eid, 12) + subtable
    header = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
    record = struct.pack(">4sIII", b"cmap", 0, 12 + 16, len(cmap))
    return header + record + cmap


def ttc(font):
    head = struct.pack(">4sIII", b"ttcf", 0x00010000, 1, 16)
    # table offsets inside the font are absolute in a collection
    font = bytearray(font)
    off, = struct.unpack_from(">I", font, 12 + 8)
    struct.pack_into(">I", font, 12 + 8, off + 16)
    return head + bytes(font)


class TestFontCheck(unittest.TestCase):
    def write(self, data):
        f = tempfile.NamedTemporaryFile(suffix=".ttf", delete=False)
        f.write(data)
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_format4(self):
        # A-C mapped; D maps to glyph 0 (delta -0x44) -> missing
        path = self.write(sfnt(cmap_format4([(0x41, 0x43, 1), (0x44, 0x44, -0x44)])))
        self.assertEqual(fontcheck.missing(path, "ABC A"), [])
        self.assertEqual(fontcheck.missing(path, "ABCDE"), ["D", "E"])

    def test_format12_and_ttc(self):
        font = sfnt(cmap_format12([(0x30A2, 0x30F3, 5), (0x1F600, 0x1F600, 0)]), 3, 10)
        for data in (font, ttc(font)):
            path = self.write(data)
            self.assertEqual(fontcheck.missing(path, "アイウ"), [])
            self.assertEqual(fontcheck.missing(path, "ア漢😀"), ["漢", "😀"])

    def test_not_a_font(self):
        path = self.write(b"\x89PNG not a font at all")
        with self.assertRaises(fontcheck.FontError):
            fontcheck.coverage(path)

    def test_real_fonts_if_installed(self):
        cjk = (glob.glob("/usr/share/fonts/**/NotoSansCJK*.ttc", recursive=True)
               + glob.glob("/System/Library/Fonts/*W6.ttc"))
        latin = glob.glob("/usr/share/fonts/**/DejaVuSans-Bold.ttf", recursive=True)
        if not cjk and not latin:
            self.skipTest("no reference fonts installed")
        for path in cjk[:1]:
            self.assertEqual(fontcheck.missing(path, "PLAY チャプター選択 第1章"), [])
        for path in latin[:1]:
            self.assertEqual(fontcheck.missing(path, "PLAY ALL é"), [])
            self.assertIn("チ", fontcheck.missing(path, "チャプター"))


if __name__ == "__main__":
    unittest.main()
