"""A small layered PSD/PSB writer, used only by the tests to build fixtures.

It writes what Photoshop writes for a simple layered RGB (or grayscale)
document: layer records bottom-to-top with Pascal + "luni" names, the
visibility flag, opacity, blend mode, optional user masks (channel -2), group
folders bracketed by "lsct" section dividers (the type-3 divider record
first, then the children, then the type 1/2 folder record), per-channel
compression 0-3, and a PackBits merged image whose transparency is matted
against white, with a negative layer count announcing it.

Describe the document top first, as in the Layers panel:

    data = build_psd(64, 48, [
        Group("Buttons", [
            Pixel("Play", rgba, (8, 8, 24, 16)),
            Pixel("Chapters", rgba2, (8, 20, 24, 28), visible=False),
        ], open=False),
        Pixel("Background", bg, (0, 0, 64, 48)),
    ], composite=flat_rgba)

Extra additional-info blocks can be attached with `extra=[(b"TySh", ...)]`.
A real "TySh" block holds a text descriptor; TEXT_STUB below is just enough
for a reader that classifies layers by key (it is not a valid descriptor, so
other readers will not be able to show the text).
"""

import struct
import zlib

RAW, RLE, ZIP, ZIP_PREDICT = 0, 1, 2, 3
TEXT_STUB = struct.pack(">HH", 1, 50) + bytes(48)

_BIG_KEYS = {b"LMsk", b"Lr16", b"Lr32", b"Layr", b"Mt16", b"Mt32", b"Mtrn",
             b"Alph", b"FMsk", b"lnk2", b"lnk3", b"lnkE", b"FEid", b"FXid",
             b"PxSD", b"FELS", b"artd", b"cinf", b"extd", b"extn", b"pths"}


class Pixel:
    """A pixel layer. `rgba` covers `bounds` = (left, top, right, bottom).
    `mask` = dict(bounds=..., data=8-bit bytes, default=0, disabled=False)."""

    def __init__(self, name, rgba, bounds, visible=True, opacity=255,
                 blend=b"norm", clipping=False, mask=None, extra=(),
                 compression=None, alpha=True, luni=True):
        self.name, self.rgba, self.bounds = name, rgba, bounds
        self.luni = luni
        self.visible, self.opacity, self.blend = visible, opacity, blend
        self.clipping, self.mask, self.extra = clipping, mask, list(extra)
        self.compression, self.alpha = compression, alpha


class Group:
    """A layer group (folder); `children` top first."""

    def __init__(self, name, children, open=True, visible=True, opacity=255,
                 blend=b"pass", extra=()):
        self.name, self.children, self.open = name, children, open
        self.visible, self.opacity, self.blend = visible, opacity, blend
        self.extra = list(extra)


# --- encoders -----------------------------------------------------------------

def packbits(row):
    """PackBits-encode one row (runs of 3+ equal bytes become repeats)."""
    out = bytearray()
    i, n = 0, len(row)
    while i < n:
        j = i
        while j < n and j - i < 128 and row[j] == row[i]:
            j += 1
        if j - i >= 3:
            out += bytes([257 - (j - i), row[i]])
            i = j
            continue
        j = i
        while j < n and j - i < 128:
            if j + 2 < n and row[j] == row[j + 1] == row[j + 2]:
                break
            j += 1
        out.append(j - i - 1)
        out += row[i:j]
        i = j
    return bytes(out)


def predict(plane, width, height, depth):
    """ZIP prediction: per-row deltas (16-bit big-endian deltas at depth 16)."""
    out = bytearray()
    if depth == 8:
        for y in range(height):
            row = plane[y * width:(y + 1) * width]
            out += bytes((row[x] - (row[x - 1] if x else 0)) & 255 for x in range(width))
    else:
        for y in range(height):
            row = struct.unpack_from(">%dH" % width, plane, y * width * 2)
            out += struct.pack(">%dH" % width, *((row[x] - (row[x - 1] if x else 0)) & 0xFFFF
                                                 for x in range(width)))
    return bytes(out)


def encode_channel(plane, width, height, depth, compression, psb=False):
    """Channel data *with* its compression word. `plane` is at `depth` bits."""
    head = struct.pack(">H", compression)
    if compression == RAW:
        return head + plane
    if compression == RLE:
        row = width * depth // 8
        rows = [packbits(plane[y * row:(y + 1) * row]) for y in range(height)]
        fmt = ">%d%s" % (height, "I" if psb else "H")
        return head + struct.pack(fmt, *map(len, rows)) + b"".join(rows)
    if compression == ZIP:
        return head + zlib.compress(plane)
    if compression == ZIP_PREDICT:
        return head + zlib.compress(predict(plane, width, height, depth))
    raise ValueError(compression)


def widen(plane, depth):
    """8-bit samples -> `depth` bits (16-bit: v * 257, big-endian)."""
    if depth == 8:
        return bytes(plane)
    return b"".join(struct.pack(">H", v * 257) for v in plane)


def _pascal(text, pad):
    raw = text.encode("mac_roman", errors="replace")[:255]
    data = bytes([len(raw)]) + raw
    return data + bytes((-len(data)) % pad)


def _block(key, data, psb, pad=2):
    data = data + bytes((-len(data)) % pad)
    fmt = ">Q" if psb and key in _BIG_KEYS else ">I"
    return b"8BIM" + key + struct.pack(fmt, len(data)) + data


def _luni(name):
    units = name.encode("utf-16-be")
    return struct.pack(">I", len(units) // 2) + units


# --- document -----------------------------------------------------------------

def _flatten(layers):
    """Top-first tree -> bottom-first list of (kind, node) records."""
    out = []
    for node in reversed(layers):
        if isinstance(node, Group):
            out.append(("divider", node))
            out.extend(_flatten(node.children))
            out.append(("group", node))
        else:
            out.append(("pixel", node))
    return out


def _record(kind, node, opts):
    """(record bytes, channel data bytes) for one layer record."""
    psb, depth, gray = opts["psb"], opts["depth"], opts["gray"]
    extra = list(node.extra)
    mask_block = b""
    channels = []    # (id, encoded data)
    if kind == "pixel":
        left, top, right, bottom = node.bounds
        w, h = max(0, right - left), max(0, bottom - top)
        comp = node.compression if node.compression is not None else opts["compression"]
        rgba = node.rgba or b""
        planes = [(0, rgba[0::4])] if gray else [(0, rgba[0::4]), (1, rgba[1::4]),
                                                  (2, rgba[2::4])]
        if node.alpha:
            planes.insert(0, (-1, rgba[3::4]))
        for cid, plane in planes:
            channels.append((cid, encode_channel(widen(plane, depth), w, h, depth,
                                                 comp, psb)))
        if node.mask:
            ml, mt, mr, mb = node.mask["bounds"]
            mask_block = struct.pack(">4iBB2x", mt, ml, mb, mr,
                                     node.mask.get("default", 0),
                                     2 if node.mask.get("disabled") else 0)
            channels.append((-2, encode_channel(widen(node.mask["data"], depth),
                                                mr - ml, mb - mt, depth, comp, psb)))
        blend = node.blend
    else:
        top = left = bottom = right = 0
        for cid in ((-1, 0) if gray else (-1, 0, 1, 2)):
            channels.append((cid, struct.pack(">H", RAW)))
        if kind == "divider":
            extra.insert(0, (b"lsct", struct.pack(">I", 3)))
            blend = b"norm"
        else:
            folder = 1 if node.open else 2
            extra.insert(0, (b"lsct", struct.pack(">I4s4s", folder, b"8BIM", node.blend)))
            blend = node.blend
    name = node.name if kind != "divider" else "</Layer group>"
    visible = node.visible if kind != "divider" else True
    opacity = node.opacity if kind != "divider" else 255
    clipping = getattr(node, "clipping", False) if kind == "pixel" else False
    flags = 8 | (0 if visible else 2)

    ranges = struct.pack(">II", 0x0000FFFF, 0x0000FFFF) * (2 if gray else 4)
    body = struct.pack(">I", len(mask_block)) + mask_block
    body += struct.pack(">I", len(ranges)) + ranges
    body += _pascal(name, 4)
    if getattr(node, "luni", True):
        body += _block(b"luni", _luni(name), psb)
    for key, data in extra:
        body += _block(key, data, psb)
    record = struct.pack(">4iH", top, left, bottom, right, len(channels))
    for cid, data in channels:
        record += struct.pack(">hQ" if psb else ">hI", cid, len(data))
    record += b"8BIM" + blend + struct.pack(">BBBB", opacity, 1 if clipping else 0,
                                            flags, 0)
    record += struct.pack(">I", len(body)) + body
    return record, b"".join(data for _, data in channels)


def _layer_info(layers, opts, merged_alpha):
    records = _flatten(layers)
    count = len(records)
    out = struct.pack(">h", -count if merged_alpha else count)
    datas = []
    for kind, node in records:
        rec, data = _record(kind, node, opts)
        out += rec
        datas.append(data)
    out += b"".join(datas)
    return out + bytes((-len(out)) % 4)


def build_psd(width, height, layers, composite=None, compression=RLE,
              depth=8, gray=False, psb=False, lr16=None, merged_alpha=True,
              color_mode=None, resources=b"", global_blocks=()):
    """Bytes of a layered document. `layers` top first; `composite` is the
    flattened RGBA (default: transparent). 16-bit documents keep their layers
    in a global "Lr16" block, as Photoshop does (lr16=False to keep them in
    the layer info instead)."""
    opts = dict(psb=psb, depth=depth, gray=gray, compression=compression)
    base = 1 if gray else 3
    channels = base + (1 if merged_alpha else 0)
    mode = color_mode if color_mode is not None else (1 if gray else 3)
    header = (b"8BPS" + struct.pack(">H", 2 if psb else 1) + bytes(6)
              + struct.pack(">HIIHH", channels, height, width, depth, mode))
    out = header + struct.pack(">I", 0)                      # colour mode data
    out += struct.pack(">I", len(resources)) + resources

    info = _layer_info(layers, opts, merged_alpha) if layers else b""
    if lr16 is None:
        lr16 = depth == 16
    blocks = b""
    if lr16 and info:
        blocks += _block(b"Lr16", info, psb, pad=4)
        info = b""
    for key, data in global_blocks:
        blocks += _block(key, data, psb, pad=4)
    lfmt = ">Q" if psb else ">I"
    section = struct.pack(lfmt, len(info)) + info
    section += struct.pack(">I", 0)                            # global layer mask
    section += blocks
    out += struct.pack(lfmt, len(section)) + section

    # merged image: PackBits, colour matted against white where transparent
    n = width * height
    flat = composite if composite is not None else bytes(n * 4)
    alpha = flat[3::4]
    planes = []
    for i in range(base):
        c = flat[i::4]
        if merged_alpha:
            c = bytes((v * a + 255 * (255 - a) + 127) // 255 for v, a in zip(c, alpha))
        planes.append(c)
    if merged_alpha:
        planes.append(alpha)
    row = width * depth // 8
    rows = []
    for plane in planes:
        plane = widen(plane, depth)
        rows += [packbits(plane[y * row:(y + 1) * row]) for y in range(height)]
    fmt = ">%d%s" % (len(rows), "I" if psb else "H")
    out += struct.pack(">H", RLE) + struct.pack(fmt, *map(len, rows)) + b"".join(rows)
    return out


def solid(width, height, rgba):
    """width x height pixels of one RGBA colour."""
    return bytes(rgba) * (width * height)


def pattern(width, height, seed=0):
    """Deterministic, varied RGBA test pixels (some runs, some noise, partial alpha)."""
    out = bytearray()
    for y in range(height):
        for x in range(width):
            v = (x * 7 + y * 13 + seed * 31) & 255
            out += bytes([v, (x * 3 + seed) & 255 if y % 3 else 200,
                          (y * 11) & 255, 255 if x % 4 else (x * y + seed) & 255])
    return bytes(out)
