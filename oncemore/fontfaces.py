"""A font's faces and its spacing (stdlib only).

Bold and italic text are drawn with the bold or italic face of the same
family: another font file, found next to the regular one (or through
fontconfig). Letter spacing and kerning switched off need the characters
placed one by one, at the advances the font gives them and, with kerning,
its kerning pairs (the `kern` table, or the `kern` feature of `GPOS`).

TrueType/OpenType (.ttf/.otf) and face 0 of a collection (.ttc), which is
the face drawtext uses. Tables as the OpenType specification describes
them (https://learn.microsoft.com/typography/opentype/spec/).
"""

import functools
import os
import shutil
import struct
import subprocess

from .fontcheck import FontError, _table_dir

FONT_EXTS = (".ttf", ".otf", ".ttc")


def _u16(d, o):
    return struct.unpack_from(">H", d, o)[0]


def _i16(d, o):
    return struct.unpack_from(">h", d, o)[0]


def _u32(d, o):
    return struct.unpack_from(">I", d, o)[0]


class Font:
    """Face 0 of a font file: its names, style, advances and kerning."""

    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = d = f.read()
        offset = _u32(d, 12) if d[:4] == b"ttcf" else 0
        try:
            self.tables = _table_dir(d, offset)
        except struct.error:
            raise FontError("not a TrueType/OpenType font") from None
        self.path = path
        try:
            self._read()
        except struct.error:
            raise FontError(f"damaged font: {os.path.basename(path)}") from None

    def _table(self, tag):
        t = self.tables.get(tag)
        return t[0] if t else None

    def _read(self):
        d = self.data
        head = self._table(b"head")
        if head is None:
            raise FontError("font has no head table")
        self.upem = _u16(d, head + 18) or 1000
        mac_style = _u16(d, head + 44)
        os2 = self._table(b"OS/2")
        if os2 is not None:
            self.weight = _u16(d, os2 + 4)
            sel = _u16(d, os2 + 62)
            self.italic = bool(sel & 0x201)          # ITALIC or OBLIQUE
            bold_bit = bool(sel & 0x20)
        else:
            self.weight, self.italic, bold_bit = 400, bool(mac_style & 2), bool(mac_style & 1)
        self.bold = self.weight >= 600 or bold_bit
        self.family, self.subfamily = self._names()

    def _names(self):
        d = self.data
        base = self._table(b"name")
        if base is None:
            return os.path.splitext(os.path.basename(self.path))[0], ""
        count, strings = _u16(d, base + 2), base + _u16(d, base + 4)
        found = {}
        for i in range(count):
            pid, eid, lang, nid, length, off = struct.unpack_from(">6H", d, base + 6 + 12 * i)
            if nid not in (1, 2, 16, 17):
                continue
            raw = d[strings + off:strings + off + length]
            if pid == 3 or pid == 0:
                text, rank = raw.decode("utf-16-be", "replace"), 0 if lang == 0x409 else 1
            elif pid == 1 and eid == 0:
                text, rank = raw.decode("mac_roman", "replace"), 2
            else:
                continue
            if nid not in found or rank < found[nid][0]:
                found[nid] = (rank, text)
        family = (found.get(16) or found.get(1) or (0, ""))[1]
        sub = (found.get(17) or found.get(2) or (0, ""))[1]
        return family, sub

    # -- glyphs and advances ---------------------------------------------------------
    @functools.cached_property
    def _cmap(self):
        d = self.data
        base = self._table(b"cmap")
        if base is None:
            raise FontError("font has no cmap table")
        subs = {}
        for i in range(_u16(d, base + 2)):
            pid, eid, off = struct.unpack_from(">HHI", d, base + 4 + 8 * i)
            subs.setdefault((pid, eid), base + off)
        for key in ((3, 10), (0, 6), (0, 4), (3, 1), (0, 3), (0, 2), (0, 1), (0, 0)):
            if key in subs and _u16(d, subs[key]) in (4, 12):
                return subs[key]
        raise FontError("font has no Unicode cmap (format 4 or 12)")

    def glyph(self, ch):
        """The glyph of a character (0: none)."""
        d, off, cp = self.data, self._cmap, ord(ch)
        if _u16(d, off) == 12:
            for i in range(_u32(d, off + 12)):
                s, e, g = struct.unpack_from(">III", d, off + 16 + 12 * i)
                if s <= cp <= e:
                    return g + cp - s
            return 0
        if cp > 0xFFFF:
            return 0
        seg2 = _u16(d, off + 6)
        for i in range(seg2 // 2):
            end = _u16(d, off + 14 + 2 * i)
            if cp > end:
                continue
            start = _u16(d, off + 16 + seg2 + 2 * i)
            if cp < start:
                return 0
            delta = _i16(d, off + 16 + 2 * seg2 + 2 * i)
            ro_at = off + 16 + 3 * seg2 + 2 * i
            ro = _u16(d, ro_at)
            if ro == 0:
                return (cp + delta) & 0xFFFF
            g = _u16(d, ro_at + ro + 2 * (cp - start))
            return (g + delta) & 0xFFFF if g else 0
        return 0

    def advance(self, glyph):
        """A glyph's advance width, in font units."""
        d = self.data
        hhea, hmtx = self._table(b"hhea"), self._table(b"hmtx")
        if hhea is None or hmtx is None:
            raise FontError("font has no horizontal metrics")
        n = _u16(d, hhea + 34)
        return _u16(d, hmtx + 4 * min(glyph, n - 1))

    # -- kerning -----------------------------------------------------------------------
    @functools.cached_property
    def _kern_subtables(self):
        """The PairPos subtables of GPOS's `kern` feature, or None without one."""
        d = self.data
        gpos = self._table(b"GPOS")
        if gpos is None:
            return None
        features, lookups = gpos + _u16(d, gpos + 6), gpos + _u16(d, gpos + 8)
        indices = []
        for i in range(_u16(d, features)):
            tag, off = struct.unpack_from(">4sH", d, features + 2 + 6 * i)
            if tag == b"kern":
                f = features + off
                indices += [_u16(d, f + 4 + 2 * k) for k in range(_u16(d, f + 2))]
        if not indices:
            return None
        out = []
        for li in dict.fromkeys(indices):
            lk = lookups + _u16(d, lookups + 2 + 2 * li)
            kind, n = _u16(d, lk), _u16(d, lk + 4)
            subs = []
            for k in range(n):
                st = lk + _u16(d, lk + 6 + 2 * k)
                if kind == 9:                                    # extension
                    if _u16(d, st + 2) != 2:
                        continue
                    st += _u32(d, st + 4)
                elif kind != 2:
                    continue
                subs.append(st)
            out.append(subs)
        return out

    def _coverage(self, off, glyph):
        d = self.data
        fmt = _u16(d, off)
        if fmt == 1:
            n = _u16(d, off + 2)
            lo, hi = 0, n
            while lo < hi:
                mid = (lo + hi) // 2
                g = _u16(d, off + 4 + 2 * mid)
                if g == glyph:
                    return mid
                lo, hi = (mid + 1, hi) if g < glyph else (lo, mid)
            return None
        for i in range(_u16(d, off + 2)):
            s, e, idx = struct.unpack_from(">3H", d, off + 4 + 6 * i)
            if s <= glyph <= e:
                return idx + glyph - s
        return None

    def _class(self, off, glyph):
        d = self.data
        if _u16(d, off) == 1:
            start, n = _u16(d, off + 2), _u16(d, off + 4)
            return _u16(d, off + 6 + 2 * (glyph - start)) if start <= glyph < start + n else 0
        for i in range(_u16(d, off + 2)):
            s, e, c = struct.unpack_from(">3H", d, off + 4 + 6 * i)
            if s <= glyph <= e:
                return c
        return 0

    @staticmethod
    def _value_size(fmt):
        return 2 * bin(fmt & 0xFF).count("1")

    @staticmethod
    def _x_advance(d, at, fmt):
        if not fmt & 4:
            return 0
        return _i16(d, at + 2 * bin(fmt & 3).count("1"))

    def _pair(self, st, a, b):
        """The first glyph's x advance adjustment of a PairPos subtable, or
        None when the subtable has nothing for the pair."""
        d = self.data
        fmt, cov, vf1, vf2 = struct.unpack_from(">4H", d, st)
        ci = self._coverage(st + cov, a)
        if ci is None:
            return None
        s1, s2 = self._value_size(vf1), self._value_size(vf2)
        if fmt == 1:
            if ci >= _u16(d, st + 8):
                return None
            ps = st + _u16(d, st + 10 + 2 * ci)
            rec = 2 + s1 + s2
            lo, hi = 0, _u16(d, ps)
            while lo < hi:
                mid = (lo + hi) // 2
                at = ps + 2 + rec * mid
                g = _u16(d, at)
                if g == b:
                    return self._x_advance(d, at + 2, vf1)
                lo, hi = (mid + 1, hi) if g < b else (lo, mid)
            return None
        if fmt == 2:
            cd1, cd2, n1, n2 = struct.unpack_from(">4H", d, st + 8)
            c1, c2 = self._class(st + cd1, a), self._class(st + cd2, b)
            if c1 >= n1 or c2 >= n2:
                return None
            at = st + 16 + (c1 * n2 + c2) * (s1 + s2)
            return self._x_advance(d, at, vf1)
        return None

    @functools.cached_property
    def _kern_table(self):
        """Pairs of a `kern` table (format 0, horizontal): {(left, right): value}."""
        d = self.data
        base = self._table(b"kern")
        pairs = {}
        if base is None or _u16(d, base) != 0:
            return pairs
        at = base + 4
        for _ in range(_u16(d, base + 2)):
            length, coverage = _u16(d, at + 2), _u16(d, at + 4)
            if coverage >> 8 == 0 and coverage & 1:
                for k in range(_u16(d, at + 6)):
                    left, right, value = struct.unpack_from(">HHh", d, at + 14 + 6 * k)
                    pairs.setdefault((left, right), value)
            at += length
        return pairs

    def kern(self, a, b):
        """The kerning of a glyph pair, in font units."""
        subtables = self._kern_subtables
        if subtables is None:
            return self._kern_table.get((a, b), 0)
        total = 0
        for subs in subtables:
            for st in subs:
                v = self._pair(st, a, b)
                if v is not None:
                    total += v
                    break
        return total

    def offsets(self, text, size, spacing=0, kerning=True):
        """Where each character of one line starts (pixels from the line's
        start) at a font size, and the line's width."""
        scale = size / self.upem
        out, x, prev = [], 0.0, None
        for ch in text:
            g = self.glyph(ch)
            if prev is not None:
                if kerning:
                    x += self.kern(prev, g) * scale
                x += spacing
            out.append(x)
            x += self.advance(g) * scale
            prev = g
        return out, x


@functools.lru_cache(maxsize=64)
def font(path):
    return Font(path)


def _candidates(path, family):
    folder = os.path.dirname(os.path.abspath(path))
    seen = set()
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        names = []
    for n in names:
        if n.lower().endswith(FONT_EXTS):
            p = os.path.join(folder, n)
            seen.add(p)
            yield p
    fc = shutil.which("fc-list")
    if fc and family:
        try:
            out = subprocess.run([fc, f":family={family}", "file"], capture_output=True,
                                 text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for line in out.splitlines():
            p = line.split(":")[0].strip()
            if p and p not in seen and p.lower().endswith(FONT_EXTS):
                seen.add(p)
                yield p


@functools.lru_cache(maxsize=64)
def faces(path):
    """{(bold, italic): font file} of the family of the font at `path` (the
    regular, bold, italic and bold italic faces it has)."""
    base = font(path)
    out = {}
    for p in _candidates(path, base.family):
        try:
            f = font(p) if os.path.abspath(p) != os.path.abspath(path) else base
        except (OSError, FontError):
            continue
        if f.family != base.family:
            continue
        key = (f.bold, f.italic)
        want = 700 if f.bold else 400
        best = out.get(key)
        if best is None or abs(font(best).weight - want) > abs(f.weight - want) or \
                (os.path.abspath(p) == os.path.abspath(path)):
            out[key] = p
    out.setdefault((base.bold, base.italic), path)
    return out


def face(path, bold=False, italic=False):
    """The file of the face of `path`'s family that is bold and/or italic
    as asked (the font itself when it already is); None when the family
    has no such face."""
    base = font(path)
    if base.bold == bold and base.italic == italic:
        return path
    return faces(path).get((bold, italic))
