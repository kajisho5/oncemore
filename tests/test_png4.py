import unittest
import zlib

from oncemore import png4


class TestPng4(unittest.TestCase):
    def roundtrip(self, w, h, palette, pattern):
        c = png4.Canvas(w, h)
        for y in range(h):
            for x in range(w):
                c.pixels[y * w + x] = pattern(x, y)
        data = png4.encode_indexed_png(c, palette)
        back, pal = png4.read_indexed_png(data)
        self.assertEqual((back.width, back.height), (w, h))
        self.assertEqual(bytes(back.pixels), bytes(c.pixels))
        return data, pal

    def test_two_bit_roundtrip_with_odd_width(self):
        pal = [(0, 0, 0, 0), (255, 212, 0), (255, 90, 0), (255, 255, 255)]
        data, back = self.roundtrip(13, 7, pal, lambda x, y: (x + y) % 4)
        self.assertEqual(data[24], 2, "bit depth should be 2 for 4 colours")
        self.assertEqual(data[25], 3, "colour type should be palette")
        self.assertEqual(back[0], (0, 0, 0, 0))
        self.assertEqual(back[1], (255, 212, 0, 255))

    def test_bit_depths(self):
        for n, depth in ((2, 1), (4, 2), (16, 4), (17, 8)):
            pal = [(i, i, i) for i in range(n)]
            data, _ = self.roundtrip(9, 3, pal, lambda x, y, n=n: (x * 3 + y) % n)
            self.assertEqual(data[24], depth)

    def test_full_frame_highlight(self):
        c = png4.Canvas(720, 480)
        c.stroke_rect(100, 100, 300, 150, 1, width=3)
        c.fill_rect(10, 10, 20, 20, 1)
        data = png4.encode_indexed_png(c, [(0, 0, 0, 0), (255, 0, 0)])
        back, _ = png4.read_indexed_png(data)
        self.assertEqual(back.get(100, 100), 1)
        self.assertEqual(back.get(150, 125), 0)   # inside the outline
        self.assertEqual(back.get(299, 149), 1)
        self.assertEqual(back.get(300, 150), 0)   # half-open
        self.assertEqual(back.used_indices(), [0, 1])

    def test_trns_only_when_needed(self):
        c = png4.Canvas(2, 2)
        opaque = png4.encode_indexed_png(c, [(1, 2, 3), (4, 5, 6)])
        self.assertNotIn(b"tRNS", opaque)
        transparent = png4.encode_indexed_png(c, [(0, 0, 0, 0), (4, 5, 6)])
        self.assertIn(b"tRNS", transparent)

    def test_rejects_bad_input(self):
        c = png4.Canvas(2, 2)
        c.pixels[0] = 3
        with self.assertRaises(ValueError):
            png4.encode_indexed_png(c, [(0, 0, 0), (1, 1, 1)])
        with self.assertRaises(ValueError):
            png4.encode_indexed_png(c, [(0, 0, 0)] * 5, bit_depth=2)
        with self.assertRaises(ValueError):
            png4.Canvas(0, 5)

    def test_crc_is_checked(self):
        data = bytearray(png4.encode_indexed_png(png4.Canvas(4, 4), [(0, 0, 0), (9, 9, 9)]))
        data[30] ^= 0xFF
        with self.assertRaises(ValueError):
            png4.read_indexed_png(bytes(data))

    def test_idat_is_valid_zlib(self):
        data = png4.encode_indexed_png(png4.Canvas(5, 5), [(0, 0, 0), (1, 1, 1)])
        i = data.index(b"IDAT")
        length = int.from_bytes(data[i - 4:i], "big")
        raw = zlib.decompress(data[i + 4:i + 4 + length])
        self.assertEqual(len(raw), 5 * (1 + 1))  # filter byte + 5 px at 1 bit

    def test_mask_from_gray(self):
        w, h = 6, 4
        gray = bytearray(w * h)
        for (x, y) in ((1, 1), (2, 1), (4, 2)):
            gray[y * w + x] = 255
        gray[0] = 50  # below threshold
        m = png4.Mask.from_gray(bytes(gray), w, h, threshold=128)
        self.assertEqual(m.bbox(), (1, 1, 5, 3))
        self.assertEqual(sorted(m.points()), [(1, 1), (2, 1), (4, 2)])
        self.assertIsNone(png4.Mask.from_gray(bytes(w * h), w, h).bbox())

    def test_parse_color(self):
        self.assertEqual(png4.parse_color("#FFD400"), (255, 212, 0, 255))
        self.assertEqual(png4.parse_color("#00000080"), (0, 0, 0, 128))
        with self.assertRaises(ValueError):
            png4.parse_color("#123")


if __name__ == "__main__":
    unittest.main()
