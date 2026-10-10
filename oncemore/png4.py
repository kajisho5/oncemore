"""Minimal indexed-colour PNG writer/reader (stdlib only: zlib + struct).

DVD button highlights are 2-bit subpictures, so spumux wants images with at
most 4 colours (one of them transparent). We write palette PNGs (colour type 3)
with a tRNS chunk carrying per-entry alpha.
"""

import struct
import zlib

_SIG = b"\x89PNG\r\n\x1a\n"


class Canvas:
    """A width x height grid of palette indices (0 = first palette entry)."""

    def __init__(self, width, height, fill=0):
        if width <= 0 or height <= 0:
            raise ValueError("canvas size must be positive")
        self.width = width
        self.height = height
        self.pixels = bytearray([fill]) * (width * height)

    def _clip(self, x0, y0, x1, y1):
        """Half-open rectangle clipped to the canvas."""
        return max(0, x0), max(0, y0), min(self.width, x1), min(self.height, y1)

    def fill_rect(self, x0, y0, x1, y1, index):
        """Fill [x0, x1) x [y0, y1)."""
        x0, y0, x1, y1 = self._clip(x0, y0, x1, y1)
        if x1 <= x0:
            return
        row = bytes([index]) * (x1 - x0)
        for y in range(y0, y1):
            o = y * self.width
            self.pixels[o + x0:o + x1] = row

    def stroke_rect(self, x0, y0, x1, y1, index, width=2):
        """Outline of [x0, x1) x [y0, y1), `width` pixels thick, drawn inside."""
        self.fill_rect(x0, y0, x1, y0 + width, index)
        self.fill_rect(x0, y1 - width, x1, y1, index)
        self.fill_rect(x0, y0, x0 + width, y1, index)
        self.fill_rect(x1 - width, y0, x1, y1, index)

    def blit_mask(self, mask, index):
        """Set `index` wherever mask (a Mask) is set."""
        for (x, y) in mask.points():
            if 0 <= x < self.width and 0 <= y < self.height:
                self.pixels[y * self.width + x] = index

    def get(self, x, y):
        return self.pixels[y * self.width + x]

    def used_indices(self):
        return sorted(set(self.pixels))


class Mask:
    """Binary mask stored as a set of row runs, from an 8-bit gray frame."""

    def __init__(self, width, height, runs=None):
        self.width = width
        self.height = height
        self.runs = runs or []  # (y, x0, x1) half-open

    @classmethod
    def from_gray(cls, data, width, height, threshold=128):
        runs = []
        for y in range(height):
            row = data[y * width:(y + 1) * width]
            x = 0
            while x < width:
                if row[x] >= threshold:
                    s = x
                    while x < width and row[x] >= threshold:
                        x += 1
                    runs.append((y, s, x))
                else:
                    x += 1
        return cls(width, height, runs)

    def bbox(self):
        """(x0, y0, x1, y1) half-open, or None if empty."""
        if not self.runs:
            return None
        return (min(r[1] for r in self.runs), min(r[0] for r in self.runs),
                max(r[2] for r in self.runs), max(r[0] for r in self.runs) + 1)

    def points(self):
        for (y, x0, x1) in self.runs:
            for x in range(x0, x1):
                yield (x, y)


def _chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _bit_depth_for(n):
    for d in (1, 2, 4, 8):
        if n <= (1 << d):
            return d
    raise ValueError("palette has more than 256 entries")


def encode_indexed_png(canvas, palette, bit_depth=None):
    """Return PNG bytes. `palette` is a list of (r, g, b) or (r, g, b, a)."""
    if not palette:
        raise ValueError("palette is empty")
    if max(canvas.pixels, default=0) >= len(palette):
        raise ValueError("canvas uses an index outside the palette")
    depth = bit_depth or _bit_depth_for(len(palette))
    if len(palette) > (1 << depth):
        raise ValueError(f"{len(palette)} colours do not fit in {depth} bits")
    w, h = canvas.width, canvas.height
    per_byte = 8 // depth
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type: None
        row = canvas.pixels[y * w:(y + 1) * w]
        if depth == 8:
            raw += row
            continue
        for i in range(0, w, per_byte):
            b = 0
            for j in range(per_byte):
                v = row[i + j] if i + j < w else 0
                b |= v << (8 - depth * (j + 1))
            raw.append(b)
    plte = b"".join(struct.pack("BBB", *c[:3]) for c in palette)
    alphas = bytes((c[3] if len(c) > 3 else 255) for c in palette)
    out = _SIG
    out += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, 3, 0, 0, 0))
    out += _chunk(b"PLTE", plte)
    if any(a != 255 for a in alphas):
        # tRNS may omit trailing fully-opaque entries
        trns = alphas.rstrip(b"\xff")
        out += _chunk(b"tRNS", trns)
    out += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += _chunk(b"IEND", b"")
    return out


def write_indexed_png(path, canvas, palette, bit_depth=None):
    data = encode_indexed_png(canvas, palette, bit_depth)
    with open(path, "wb") as f:
        f.write(data)
    return path


def read_indexed_png(data):
    """Decode a non-interlaced palette PNG written by this module (or similar).

    Returns (canvas, palette) where palette entries are (r, g, b, a).
    """
    if data[:8] != _SIG:
        raise ValueError("not a PNG")
    pos = 8
    ihdr = None
    plte = b""
    trns = b""
    idat = b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise ValueError(f"bad CRC in {kind!r}")
        pos += 12 + length
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            plte = body
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
    if ihdr is None:
        raise ValueError("missing IHDR")
    w, h, depth, ctype, _, _, interlace = ihdr
    if ctype != 3 or interlace != 0:
        raise ValueError("only non-interlaced palette PNGs are supported")
    raw = zlib.decompress(idat)
    stride = (w * depth + 7) // 8
    canvas = Canvas(w, h)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        _unfilter(ftype, line, prev, 1)
        prev = line
        per_byte = 8 // depth
        mask = (1 << depth) - 1
        for x in range(w):
            if depth == 8:
                v = line[x]
            else:
                b = line[x // per_byte]
                shift = 8 - depth * ((x % per_byte) + 1)
                v = (b >> shift) & mask
            canvas.pixels[y * w + x] = v
    palette = []
    for i in range(len(plte) // 3):
        a = trns[i] if i < len(trns) else 255
        palette.append((plte[3 * i], plte[3 * i + 1], plte[3 * i + 2], a))
    return canvas, palette


def _unfilter(ftype, line, prev, bpp):
    for i in range(len(line)):
        a = line[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        if ftype == 0:
            continue
        elif ftype == 1:
            line[i] = (line[i] + a) & 0xFF
        elif ftype == 2:
            line[i] = (line[i] + b) & 0xFF
        elif ftype == 3:
            line[i] = (line[i] + ((a + b) >> 1)) & 0xFF
        elif ftype == 4:
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
            line[i] = (line[i] + pr) & 0xFF
        else:
            raise ValueError(f"unknown PNG filter {ftype}")


def parse_color(value):
    """'#RRGGBB' or '#RRGGBBAA' -> (r, g, b, a)."""
    s = value.lstrip("#")
    if len(s) not in (6, 8):
        raise ValueError(f"invalid colour {value!r}")
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    a = int(s[6:8], 16) if len(s) == 8 else 255
    return (r, g, b, a)
