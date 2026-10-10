"""Which characters a font file can draw (stdlib only).

ffmpeg's drawtext loads exactly one font file and has no fallback chain: a
character the font lacks is drawn as an empty box and ffmpeg still exits 0.
So before rendering a menu we read the font's `cmap` table and refuse text it
cannot draw, instead of authoring a disc full of "tofu".

Supports TrueType/OpenType (.ttf/.otf) and collections (.ttc; drawtext uses
face 0, and so do we), cmap subtable formats 4 and 12.
"""

import struct

_UNICODE_SUBTABLES = ((3, 10), (0, 6), (0, 4), (3, 1), (0, 3), (0, 2), (0, 1), (0, 0))


class FontError(ValueError):
    pass


def _table_dir(data, offset):
    if data[offset:offset + 4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        raise FontError("not a TrueType/OpenType font")
    (num,) = struct.unpack_from(">H", data, offset + 4)
    tables = {}
    for i in range(num):
        tag, _, off, length = struct.unpack_from(">4sIII", data, offset + 12 + 16 * i)
        tables[tag] = (off, length)
    return tables


class Coverage:
    """Codepoint ranges [(start, end_inclusive), ...] from a cmap subtable."""

    def __init__(self, ranges):
        self.ranges = sorted(ranges)

    def __contains__(self, cp):
        lo, hi = 0, len(self.ranges)
        while lo < hi:
            mid = (lo + hi) // 2
            s, e = self.ranges[mid]
            if cp < s:
                hi = mid
            elif cp > e:
                lo = mid + 1
            else:
                return True
        return False


def _format4(data, off):
    (seg2,) = struct.unpack_from(">H", data, off + 6)
    n = seg2 // 2
    ends = struct.unpack_from(f">{n}H", data, off + 14)
    starts = struct.unpack_from(f">{n}H", data, off + 16 + seg2)
    deltas = struct.unpack_from(f">{n}h", data, off + 16 + 2 * seg2)
    ro_base = off + 16 + 3 * seg2
    ro = struct.unpack_from(f">{n}H", data, ro_base)
    ranges = []
    for i in range(n):
        s, e = starts[i], ends[i]
        if s == 0xFFFF:
            continue
        if ro[i] == 0:
            # glyph = (cp + delta) & 0xFFFF; glyph 0 means "missing"
            run = None
            for cp in range(s, e + 1):
                ok = (cp + deltas[i]) & 0xFFFF != 0
                if ok and run is None:
                    run = cp
                elif not ok and run is not None:
                    ranges.append((run, cp - 1))
                    run = None
            if run is not None:
                ranges.append((run, e))
        else:
            run = None
            for cp in range(s, e + 1):
                gpos = ro_base + 2 * i + ro[i] + 2 * (cp - s)
                (g,) = struct.unpack_from(">H", data, gpos) if gpos + 2 <= len(data) else (0,)
                ok = g != 0
                if ok and run is None:
                    run = cp
                elif not ok and run is not None:
                    ranges.append((run, cp - 1))
                    run = None
            if run is not None:
                ranges.append((run, e))
    return ranges


def _format12(data, off):
    (ngroups,) = struct.unpack_from(">I", data, off + 12)
    ranges = []
    for i in range(ngroups):
        s, e, g = struct.unpack_from(">III", data, off + 16 + 12 * i)
        if g == 0:
            s += 1  # the first code of this group maps to .notdef
        if s <= e:
            ranges.append((s, e))
    return ranges


def coverage(path):
    """Coverage of face 0 of the font file at `path`."""
    with open(path, "rb") as f:
        data = f.read()
    offset = 0
    if data[:4] == b"ttcf":
        (offset,) = struct.unpack_from(">I", data, 12)
    tables = _table_dir(data, offset)
    if b"cmap" not in tables:
        raise FontError("font has no cmap table")
    base = tables[b"cmap"][0]
    (n,) = struct.unpack_from(">H", data, base + 2)
    subs = {}
    for i in range(n):
        pid, eid, off = struct.unpack_from(">HHI", data, base + 4 + 8 * i)
        subs.setdefault((pid, eid), base + off)
    for key in _UNICODE_SUBTABLES:
        if key not in subs:
            continue
        off = subs[key]
        (fmt,) = struct.unpack_from(">H", data, off)
        if fmt == 12:
            return Coverage(_format12(data, off))
        if fmt == 4:
            return Coverage(_format4(data, off))
    raise FontError("font has no Unicode cmap (format 4 or 12)")


def missing(path, text):
    """Sorted distinct characters of `text` the font cannot draw."""
    cov = coverage(path)
    return sorted({ch for ch in text if not ch.isspace() and ord(ch) not in cov})
