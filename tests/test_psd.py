import os
import pathlib
import random
import struct
import tempfile
import unittest
import zlib

from oncemore import psd
from oncemore.errors import OncemoreError
from tests.psd_writer import (RAW, RLE, TEXT_STUB, ZIP, ZIP_PREDICT, Group, Pixel,
                              build_psd, encode_channel, packbits, pattern, solid)

W, H = 32, 24


def ramp(w, h):
    """An 8-bit mask plane: a horizontal ramp with a hole in the middle."""
    return bytes(0 if (w // 3 <= x < 2 * w // 3 and y == h // 2)
                 else (x * 255) // max(1, w - 1) for y in range(h) for x in range(w))


def menu(compression=None):
    """A small menu design, top first as in the Layers panel."""
    return [
        Group("Buttons", [
            Group("Play", [
                Pixel("highlight", pattern(10, 4, 1), (2, 2, 12, 6), opacity=128,
                      compression=compression),
                Pixel("normal", pattern(10, 4, 2), (2, 2, 12, 6), visible=False,
                      compression=compression),
            ]),
            Group("Chapters", [
                Pixel("select", pattern(10, 4, 3), (2, 10, 12, 14), compression=compression),
            ], open=False, visible=False, opacity=64),
        ]),
        Pixel("Thumbnail", pattern(8, 6, 4), (20, 4, 28, 10), compression=compression),
        Pixel("Background", pattern(W, H, 5), (0, 0, W, H), alpha=False,
              compression=compression),
    ]


def opaque(rgba):
    return bytes(255 if i % 4 == 3 else v for i, v in enumerate(rgba))


class TestHeader(unittest.TestCase):
    def test_size_depth_mode(self):
        doc = psd.read_psd(build_psd(W, H, menu()))
        self.assertEqual((doc.width, doc.height, doc.depth), (W, H, 8))
        self.assertEqual(doc.color_mode, psd.RGB)
        self.assertEqual(doc.color_mode_name, "RGB")
        self.assertEqual(doc.version, 1)
        self.assertFalse(doc.is_psb)
        self.assertEqual(doc.channels, 4)

    def test_reads_paths_and_bytes(self):
        data = build_psd(W, H, menu())
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "menu.psd")
            with open(path, "wb") as f:
                f.write(data)
            for source in (path, pathlib.Path(path), data, bytearray(data), memoryview(data)):
                doc = psd.read_psd(source)
                self.assertEqual([l.name for l in doc.layers],
                                 ["Buttons", "Thumbnail", "Background"])

    def test_missing_file(self):
        with self.assertRaises(psd.PsdError):
            psd.read_psd("/nonexistent/menu.psd")

    def test_error_is_an_oncemore_error(self):
        self.assertTrue(issubclass(psd.PsdError, OncemoreError))


class TestTree(unittest.TestCase):
    def setUp(self):
        self.doc = psd.read_psd(build_psd(W, H, menu()))

    def test_top_first_order_and_parents(self):
        doc = self.doc
        self.assertEqual([l.name for l in doc.layers], ["Buttons", "Thumbnail", "Background"])
        buttons = doc.layers[0]
        self.assertTrue(buttons.is_group)
        self.assertEqual(buttons.kind, "group")
        self.assertEqual([l.name for l in buttons.children], ["Play", "Chapters"])
        play, chapters = buttons.children
        self.assertEqual([l.name for l in play.children], ["highlight", "normal"])
        self.assertIs(play.parent, buttons)
        self.assertIs(play.children[0].parent, play)
        self.assertIsNone(buttons.parent)
        self.assertEqual(doc.find("select").path, ("Buttons", "Chapters", "select"))

    def test_walk_is_depth_first_top_first(self):
        self.assertEqual([l.name for l in self.doc.walk()],
                         ["Buttons", "Play", "highlight", "normal", "Chapters", "select",
                          "Thumbnail", "Background"])

    def test_records_are_in_file_order_with_dividers(self):
        recs = self.doc.records
        self.assertEqual([r.index for r in recs], list(range(len(recs))))
        self.assertEqual(recs[0].name, "Background")      # bottom-most first
        kinds = [r.kind for r in recs]
        self.assertEqual(kinds.count("divider"), 3)
        self.assertEqual(kinds.count("group"), 3)
        # a divider comes before (below) its group's children
        names = [r.name for r in recs]
        self.assertEqual(names[2], "</Layer group>")
        self.assertEqual(names[-1], "Buttons")
        self.assertNotIn("divider", [l.kind for l in self.doc.walk()])
        self.assertEqual(self.doc.find("Buttons").index, len(recs) - 1)

    def test_open_and_closed_folders(self):
        self.assertTrue(self.doc.find("Play").folder_open)
        self.assertFalse(self.doc.find("Chapters").folder_open)
        self.assertEqual(self.doc.find("Chapters").folder, psd.CLOSED_FOLDER)
        self.assertIsNone(self.doc.find("Thumbnail").folder_open)

    def test_visibility_and_opacity(self):
        doc = self.doc
        self.assertFalse(doc.find("normal").visible)
        self.assertTrue(doc.find("highlight").visible)
        self.assertEqual(doc.find("highlight").opacity, 128)
        chapters = doc.find("Chapters")
        self.assertFalse(chapters.visible)
        self.assertEqual(chapters.opacity, 64)
        self.assertTrue(doc.find("select").visible)
        self.assertFalse(doc.find("select").effective_visible)
        self.assertTrue(doc.find("highlight").effective_visible)

    def test_blend_mode_and_bounds(self):
        doc = self.doc
        hl = doc.find("highlight")
        self.assertEqual(hl.blend_mode, "norm")
        self.assertEqual(doc.find("Play").blend_mode, "pass")
        self.assertEqual(hl.bounds, (2, 2, 12, 6))
        self.assertEqual((hl.width, hl.height), (10, 4))
        self.assertFalse(hl.clipping)

    def test_clipping(self):
        doc = psd.read_psd(build_psd(W, H, [
            Pixel("clipped", solid(2, 2, (1, 2, 3, 255)), (0, 0, 2, 2), clipping=True),
            Pixel("base", solid(2, 2, (1, 2, 3, 255)), (0, 0, 2, 2))]))
        self.assertTrue(doc.find("clipped").clipping)
        self.assertFalse(doc.find("base").clipping)

    def test_empty_group(self):
        doc = psd.read_psd(build_psd(W, H, [Group("Nothing", [])]))
        self.assertEqual(doc.layers[0].children, [])
        self.assertTrue(doc.layers[0].is_empty)
        self.assertEqual(doc.layers[0].rgba(), b"")

    def test_unmatched_dividers_are_tolerated(self):
        def rec(i, kind, name):
            layer = psd.Layer(None, i)
            layer.kind, layer.name = kind, name
            return layer
        # a divider whose group record is missing: its layers move up a level
        top = psd._build_tree([rec(0, "pixel", "bg"), rec(1, "divider", ""),
                               rec(2, "pixel", "a"), rec(3, "pixel", "b")])
        self.assertEqual([l.name for l in top], ["b", "a", "bg"])
        # a group record without a divider: an empty group
        top = psd._build_tree([rec(0, "pixel", "bg"), rec(1, "group", "g")])
        self.assertEqual([(l.name, l.children) for l in top], [("g", []), ("bg", [])])


class TestNames(unittest.TestCase):
    def test_japanese_names_via_luni(self):
        doc = psd.read_psd(build_psd(W, H, [
            Group("メニュー", [Pixel("再生ボタン", solid(2, 2, (9, 9, 9, 255)), (0, 0, 2, 2))]),
            Pixel("チャプター 1", solid(2, 2, (9, 9, 9, 255)), (0, 0, 2, 2))]))
        self.assertEqual([l.name for l in doc.walk()], ["メニュー", "再生ボタン", "チャプター 1"])

    def test_pascal_name_is_mac_roman(self):
        doc = psd.read_psd(build_psd(W, H, [
            Pixel("Café Menü", solid(1, 1, (0, 0, 0, 255)), (0, 0, 1, 1), luni=False)]))
        self.assertEqual(doc.layers[0].name, "Café Menü")

    def test_luni_preferred_over_pascal(self):
        doc = psd.read_psd(build_psd(W, H, [
            Pixel("ボタン", solid(1, 1, (0, 0, 0, 255)), (0, 0, 1, 1))]))
        layer = doc.layers[0]
        self.assertEqual(layer.name, "ボタン")
        self.assertIn(b"luni", layer.info)


class TestKinds(unittest.TestCase):
    def kind_of(self, *extra):
        doc = psd.read_psd(build_psd(W, H, [
            Pixel("x", solid(1, 1, (0, 0, 0, 255)), (0, 0, 1, 1), extra=list(extra))]))
        return doc.layers[0].kind

    def test_kinds(self):
        self.assertEqual(self.kind_of(), "pixel")
        self.assertEqual(self.kind_of((b"TySh", TEXT_STUB)), "text")
        self.assertEqual(self.kind_of((b"SoLd", b"\0" * 8)), "smart")
        self.assertEqual(self.kind_of((b"PlLd", b"\0" * 8)), "smart")
        self.assertEqual(self.kind_of((b"vmsk", b"\0" * 8), (b"SoCo", b"\0" * 8)), "shape")
        self.assertEqual(self.kind_of((b"SoCo", b"\0" * 8)), "fill")
        self.assertEqual(self.kind_of((b"GdFl", b"\0" * 8)), "fill")
        for key in (b"levl", b"curv", b"hue2", b"brit", b"nvrt", b"thrs"):
            self.assertEqual(self.kind_of((key, b"\0" * 8)), "adjustment", key)

    def test_layer_id_and_fill_opacity(self):
        doc = psd.read_psd(build_psd(W, H, [
            Pixel("x", solid(1, 1, (0, 0, 0, 255)), (0, 0, 1, 1),
                  extra=[(b"lyid", struct.pack(">I", 42)), (b"iOpa", b"\x80\0\0\0")])]))
        self.assertEqual(doc.layers[0].layer_id, 42)
        self.assertEqual(doc.layers[0].fill_opacity, 128)

    def test_unknown_blocks_are_kept(self):
        doc = psd.read_psd(build_psd(W, H, [
            Pixel("x", solid(1, 1, (0, 0, 0, 255)), (0, 0, 1, 1), extra=[(b"zzzz", b"abcd")])]))
        self.assertEqual(doc.layers[0].info[b"zzzz"], b"abcd")


class TestPixels(unittest.TestCase):
    def check_menu(self, data):
        doc = psd.read_psd(data)
        self.assertEqual(doc.find("highlight").rgba(), pattern(10, 4, 1))
        self.assertEqual(doc.find("normal").rgba(), pattern(10, 4, 2))
        self.assertEqual(doc.find("Thumbnail").rgba(), pattern(8, 6, 4))
        self.assertEqual(doc.find("Background").rgba(), opaque(pattern(W, H, 5)))
        return doc

    def test_compressions_8bit(self):
        for comp in (RAW, RLE, ZIP, ZIP_PREDICT):
            with self.subTest(compression=comp):
                self.check_menu(build_psd(W, H, menu(comp), compression=comp))

    def test_compressions_16bit_lr16(self):
        for comp in (RAW, RLE, ZIP, ZIP_PREDICT):
            with self.subTest(compression=comp):
                data = build_psd(W, H, menu(comp), compression=comp, depth=16)
                doc = self.check_menu(data)
                self.assertEqual(doc.depth, 16)
                self.assertIn(b"Lr16", doc.global_info)

    def test_16bit_in_layer_info(self):
        doc = self.check_menu(build_psd(W, H, menu(), depth=16, lr16=False))
        self.assertNotIn(b"Lr16", doc.global_info)

    def test_16bit_takes_high_byte(self):
        # 0x12FF must read as 0x12, not rounded to 0x13
        plane16 = struct.pack(">4H", 0x12FF, 0x0080, 0xFF00, 0x0001)
        for comp in (RAW, RLE, ZIP, ZIP_PREDICT):
            body = encode_channel(plane16, 2, 2, 16, comp)
            (c,) = struct.unpack(">H", body[:2])
            self.assertEqual(psd._decode(c, memoryview(body)[2:], 2, 2, 16, False, "t"),
                             bytes([0x12, 0x00, 0xFF, 0x00]))

    def test_zip_prediction_wraps(self):
        plane = bytes([250, 3, 3, 0, 255, 1])
        body = encode_channel(plane, 3, 2, 8, ZIP_PREDICT)
        self.assertEqual(psd._decode(3, body[2:], 3, 2, 8, False, "t"), plane)

    def test_packbits_runs_and_literals(self):
        row = bytes([1] * 200 + [2, 3, 4] + [5] * 3 + list(range(150)))
        enc = packbits(row)
        self.assertLess(len(enc), len(row))
        self.assertEqual(psd._unpackbits(enc, len(row)), row)
        # PackBits no-op byte (128) is skipped
        self.assertEqual(psd._unpackbits(b"\x80\x01ab", 2), b"ab")

    def test_grayscale(self):
        g = pattern(6, 5, 7)
        doc = psd.read_psd(build_psd(W, H, [Pixel("g", g, (1, 1, 7, 6))], gray=True))
        self.assertEqual(doc.color_mode, psd.GRAYSCALE)
        out = doc.layers[0].rgba()
        self.assertEqual(out[0::4], g[0::4])
        self.assertEqual(out[1::4], g[0::4])
        self.assertEqual(out[2::4], g[0::4])
        self.assertEqual(out[3::4], g[3::4])

    def test_missing_alpha_is_opaque(self):
        doc = psd.read_psd(build_psd(W, H, [Pixel("bg", pattern(4, 4), (0, 0, 4, 4),
                                                   alpha=False)]))
        self.assertEqual(doc.layers[0].rgba()[3::4], b"\xff" * 16)

    def test_empty_layer(self):
        doc = psd.read_psd(build_psd(W, H, [Pixel("empty", b"", (0, 0, 0, 0)),
                                            Pixel("thin", b"", (5, 5, 5, 9))]))
        for layer in doc.layers:
            self.assertTrue(layer.is_empty)
            self.assertEqual(layer.rgba(), b"")

    def test_layer_outside_canvas(self):
        px = pattern(6, 6, 3)
        doc = psd.read_psd(build_psd(W, H, [Pixel("off", px, (-3, -2, 3, 4))]))
        self.assertEqual(doc.layers[0].bounds, (-3, -2, 3, 4))
        self.assertEqual(doc.layers[0].rgba(), px)


class TestMasks(unittest.TestCase):
    def layer(self, **mask):
        px = solid(8, 4, (10, 20, 30, 200))
        doc = psd.read_psd(build_psd(W, H, [Pixel("m", px, (4, 4, 12, 8), mask=mask)]))
        return doc.layers[0]

    def test_mask_multiplies_alpha(self):
        layer = self.layer(bounds=(4, 4, 12, 8), data=ramp(8, 4))
        out = layer.rgba()
        expect = bytes((200 * m + 127) // 255 for m in ramp(8, 4))
        self.assertEqual(out[3::4], expect)
        self.assertEqual(out[0::4], b"\x0a" * 32)     # colour untouched
        self.assertEqual(layer.mask.bounds, (4, 4, 12, 8))
        self.assertEqual(layer.mask.data(), ramp(8, 4))

    def test_mask_rectangle_and_default_colour(self):
        # mask covers columns 6..9 and rows 5..6 only; outside it is white
        m = bytes([0]) * 8
        layer = self.layer(bounds=(6, 5, 10, 7), data=m, default=255)
        alpha = layer.rgba()[3::4]
        for y in range(4):
            for x in range(8):
                inside = 6 <= x + 4 < 10 and 5 <= y + 4 < 7
                self.assertEqual(alpha[y * 8 + x], 0 if inside else 200, (x, y))

    def test_mask_default_black_and_overhang(self):
        # mask rectangle sticks out of the layer on the left and the bottom
        m = bytes([255]) * (6 * 6)
        layer = self.layer(bounds=(1, 6, 7, 12), data=m, default=0)
        alpha = layer.rgba()[3::4]
        for y in range(4):
            for x in range(8):
                inside = x + 4 < 7 and y + 4 >= 6
                self.assertEqual(alpha[y * 8 + x], 200 if inside else 0, (x, y))

    def test_disabled_mask_is_ignored(self):
        layer = self.layer(bounds=(4, 4, 12, 8), data=bytes(32), disabled=True)
        self.assertTrue(layer.mask.disabled)
        self.assertEqual(layer.rgba()[3::4], b"\xc8" * 32)

    def test_mask_compressions(self):
        for comp in (RAW, RLE, ZIP, ZIP_PREDICT):
            doc = psd.read_psd(build_psd(W, H, [Pixel("m", solid(8, 4, (1, 2, 3, 255)),
                                                      (4, 4, 12, 8), compression=comp,
                                                      mask=dict(bounds=(4, 4, 12, 8),
                                                                data=ramp(8, 4)))]))
            self.assertEqual(doc.layers[0].rgba()[3::4], ramp(8, 4), comp)


class TestComposite(unittest.TestCase):
    def test_transparent_composite_is_unmatted(self):
        flat = solid(W, H, (200, 100, 50, 255))[:-4 * W] + solid(W, 1, (0, 0, 255, 128))
        doc = psd.read_psd(build_psd(W, H, menu(), composite=flat))
        self.assertTrue(doc.has_transparency())
        out = doc.composite()
        self.assertEqual(len(out), W * H * 4)
        self.assertEqual(out[:4], bytes((200, 100, 50, 255)))
        r, g, b, a = out[-4:]
        self.assertEqual(a, 128)
        self.assertLessEqual(abs(r - 0) + abs(g - 0) + abs(b - 255), 3)

    def test_opaque_composite(self):
        flat = opaque(pattern(W, H, 8))
        doc = psd.read_psd(build_psd(W, H, menu(), composite=flat, merged_alpha=False))
        self.assertFalse(doc.has_transparency())
        self.assertEqual(doc.composite(), flat)

    def test_fully_transparent_pixels_keep_stored_colour(self):
        doc = psd.read_psd(build_psd(W, H, []))
        self.assertEqual(doc.layers, [])
        self.assertEqual(doc.composite(), solid(W, H, (255, 255, 255, 0)))

    def test_16bit_and_gray_composites(self):
        flat = opaque(pattern(W, H, 8))
        doc = psd.read_psd(build_psd(W, H, menu(), composite=flat, depth=16,
                                     merged_alpha=False))
        self.assertEqual(doc.composite(), flat)
        doc = psd.read_psd(build_psd(W, H, menu(), composite=flat, gray=True,
                                     merged_alpha=False))
        out = doc.composite()
        self.assertEqual(out[0::4], flat[0::4])
        self.assertEqual(out[2::4], flat[0::4])

    def test_absent_composite(self):
        data = build_psd(W, H, menu())
        cut = len(data) - len(_merged_section(data))
        doc = psd.read_psd(data[:cut])
        self.assertIsNone(doc.composite())
        self.assertEqual(doc.find("Thumbnail").rgba(), pattern(8, 6, 4))


class TestPsb(unittest.TestCase):
    def test_psb(self):
        for comp in (RAW, RLE, ZIP, ZIP_PREDICT):
            with self.subTest(compression=comp):
                flat = opaque(pattern(W, H, 8))
                data = build_psd(W, H, menu(comp), compression=comp, psb=True,
                                 composite=flat, merged_alpha=False)
                self.assertEqual(data[4:6], b"\x00\x02")
                doc = psd.read_psd(data)
                self.assertTrue(doc.is_psb)
                self.assertEqual([l.name for l in doc.walk()][:3], ["Buttons", "Play", "highlight"])
                self.assertEqual(doc.find("highlight").rgba(), pattern(10, 4, 1))
                self.assertEqual(doc.composite(), flat)

    def test_psb_16bit_lr16_has_wide_length(self):
        data = build_psd(W, H, menu(), psb=True, depth=16)
        i = data.index(b"8BIMLr16")
        (length,) = struct.unpack(">Q", data[i + 8:i + 16])
        self.assertGreater(length, 0)
        doc = psd.read_psd(data)
        self.assertEqual(doc.find("Thumbnail").rgba(), pattern(8, 6, 4))

    def test_psb_masks(self):
        data = build_psd(W, H, [Pixel("m", solid(8, 4, (1, 2, 3, 255)), (4, 4, 12, 8),
                                      mask=dict(bounds=(4, 4, 12, 8), data=ramp(8, 4)))],
                         psb=True)
        self.assertEqual(psd.read_psd(data).layers[0].rgba()[3::4], ramp(8, 4))


def _merged_section(data):
    """The merged image section (compression word + data) of a build_psd file."""
    doc = psd.read_psd(data)
    return b"cc" + bytes(doc._merged[1])


class TestErrors(unittest.TestCase):
    def patched(self, offset, fmt, value, data=None):
        data = bytearray(data or build_psd(W, H, menu()))
        struct.pack_into(fmt, data, offset, value)
        return bytes(data)

    def test_cmyk_and_others_rejected(self):
        for mode, name in ((4, "CMYK"), (9, "Lab"), (2, "Indexed"), (0, "Bitmap")):
            with self.subTest(mode=name):
                data = build_psd(W, H, menu(), color_mode=mode)
                with self.assertRaises(psd.PsdError) as cm:
                    psd.read_psd(data)
                self.assertIn(name, str(cm.exception))
                self.assertIn("RGB", str(cm.exception))

    def test_32bit_rejected(self):
        with self.assertRaises(psd.PsdError) as cm:
            psd.read_psd(self.patched(22, ">H", 32))
        self.assertIn("8 bits", str(cm.exception))

    def test_lr32_rejected(self):
        data = build_psd(W, H, [], global_blocks=[(b"Lr32", b"\0" * 8)])
        with self.assertRaises(psd.PsdError):
            psd.read_psd(data)

    def test_not_a_psd(self):
        for data in (b"", b"GIF89a" + bytes(40), b"8BPS\x00\x03" + bytes(40)):
            with self.assertRaises(psd.PsdError):
                psd.read_psd(data)

    def test_absurd_dimensions(self):
        for offset in (14, 18):         # height, width
            with self.assertRaises(psd.PsdError) as cm:
                psd.read_psd(self.patched(offset, ">I", 300_001))
            self.assertIn("out of range", str(cm.exception))
        with self.assertRaises(psd.PsdError):
            psd.read_psd(self.patched(14, ">I", 0))

    def test_absurd_layer_count(self):
        data = build_psd(W, H, menu())
        i = 26 + 4 + 4 + 4 + 4             # header, mode data, resources, section, info
        self.assertEqual(struct.unpack(">h", data[i:i + 2])[0], -11)
        with self.assertRaises(psd.PsdError) as cm:
            psd.read_psd(self.patched(i, ">h", 20000, data))
        self.assertIn("layers", str(cm.exception))

    def test_absurd_layer_bounds(self):
        data = build_psd(W, H, menu())
        first = 26 + 4 + 4 + 4 + 4 + 2    # first record: top, left, bottom, right
        with self.assertRaises(psd.PsdError):
            psd.read_psd(self.patched(first + 12, ">i", 2_000_000_000, data))

    def test_huge_layer_is_refused_on_decode(self):
        data = build_psd(W, H, [Pixel("big", b"", (0, 0, 0, 0))])
        first = 26 + 4 + 4 + 4 + 4 + 2
        data = self.patched(first + 8, ">i", 250_000, data)
        data = self.patched(first + 12, ">i", 250_000, data)
        doc = psd.read_psd(data)
        with self.assertRaises(psd.PsdError):
            doc.layers[0].rgba()

    def test_truncation_always_raises_psd_error(self):
        data = build_psd(W, H, menu(), composite=pattern(W, H, 3))
        merged_start = len(data) - len(_merged_section(data))
        for cut in range(0, len(data), 7):
            try:
                doc = psd.read_psd(data[:cut])
            except psd.PsdError:
                continue
            # only cutting off the whole merged image is still a valid file
            self.assertGreaterEqual(cut, merged_start, cut)
            self.assertIsNone(doc.composite())

    def test_damaged_files_never_crash_otherwise(self):
        base = build_psd(W, H, menu(ZIP_PREDICT), composite=pattern(W, H, 3))
        rnd = random.Random(1234)
        for _ in range(300):
            data = bytearray(base)
            for _ in range(rnd.randint(1, 4)):
                data[rnd.randrange(26, len(data))] = rnd.randrange(256)
            try:
                doc = psd.read_psd(bytes(data))
                for layer in doc.records:
                    layer.rgba()
                doc.composite()
            except psd.PsdError:
                pass

    def test_damaged_zip(self):
        body = b"\x00" + zlib.compress(bytes(8))[1:]
        with self.assertRaises(psd.PsdError):
            psd._decode(2, body, 4, 2, 8, False, "t")
        with self.assertRaises(psd.PsdError):
            psd._decode(2, zlib.compress(bytes(3)), 4, 2, 8, False, "t")


class TestPng(unittest.TestCase):
    def test_png_roundtrip(self):
        w, h = 5, 3
        rgba = pattern(w, h, 2)
        data = psd.png_bytes(w, h, rgba)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">IIBB", data[16:26]), (w, h, 8, 6))
        n = struct.unpack(">I", data[33:37])[0]
        self.assertEqual(data[37:41], b"IDAT")
        raw = zlib.decompress(data[41:41 + n])
        self.assertEqual(b"".join(raw[y * (w * 4 + 1) + 1:(y + 1) * (w * 4 + 1)]
                                  for y in range(h)), rgba)
        with tempfile.TemporaryDirectory() as tmp:
            path = psd.write_png(os.path.join(tmp, "x.png"), w, h, rgba)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), data)
        with self.assertRaises(ValueError):
            psd.png_bytes(2, 2, b"\0" * 15)


if __name__ == "__main__":
    unittest.main()
