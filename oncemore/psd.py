"""Layered Photoshop reader (PSD, and PSB "large document" files), stdlib only.

Used to import layered menu designs: button groups, highlight layers and
thumbnail placeholders keep their names, visibility, bounds and pixels.

File layout (all integers big-endian; PSB widens some lengths to 8 bytes):

  header          "8BPS", version (1 = PSD, 2 = PSB), 6 reserved bytes,
                  channels, height, width, depth (bits per channel), colour mode
  colour mode     length + data (palette of indexed files; skipped)
  resources       length + "8BIM" blocks (id, Pascal name, sized data)
  layer & mask    length (8 in PSB), then:
    layer info    length (8 in PSB), layer count (negative: the merged image's
                  first extra channel is its transparency), the layer records,
                  then every record's channel data, in record order
    global mask   length + data (skipped)
    extra blocks  "8BIM"/"8B64" key length data; 16-bit documents keep their
                  layer info here, in an "Lr16" block
  merged image    compression, then every channel of the flattened image

Layer records are stored bottom-to-top. Groups are bracketed: a "bounding
section divider" record (additional info "lsct" type 3, named "</Layer group>")
comes first, i.e. lowest, then the children, then the record that *is* the
group (lsct type 1 = open folder, 2 = closed folder), which carries the
group's name, visibility and opacity.

Each layer channel is (id, data): 0, 1, 2 = red, green, blue (0 = gray in
grayscale documents), -1 = transparency, -2 = user (pixel) layer mask, sized
by the mask rectangle, -3 = real user mask (pixel + vector, not applied).
Channel data starts with its compression: 0 raw, 1 PackBits with a table of
per-row byte counts (2 bytes each in PSD, 4 in PSB), 2 zlib, 3 zlib over
per-row deltas.

Supported: RGB and Grayscale at 8 bits (16 bits are reduced to 8 by taking
the high byte); all four compressions (32-bit predicted ZIP is not). Pixel
data is decoded lazily, on Layer.rgba() / Document.composite(), as
straight (not premultiplied) RGBA. Blend modes, opacity, clipping and effects
are reported but never applied; rendering a document is left to the caller.
"""

import os
import struct
import zlib
from itertools import accumulate

from .errors import OncemoreError

MAX_DIMENSION = 300_000     # the PSB limit; PSD itself stops at 30,000
MAX_LAYERS = 10_000
MAX_CHANNELS = 56           # per layer and per document (Photoshop's limit)
MAX_PIXELS = 1 << 27        # largest bitmap decoded at once (512 MiB as RGBA)

RGB, GRAYSCALE = 3, 1
_MODE_NAMES = {0: "Bitmap", 1: "Grayscale", 2: "Indexed", 3: "RGB", 4: "CMYK",
               7: "Multichannel", 8: "Duotone", 9: "Lab"}
_BASE_CHANNELS = {RGB: 3, GRAYSCALE: 1}

# Additional-info keys whose length is 8 bytes in PSB files: Adobe's list plus
# the ones psd-tools found in real files.
_BIG_KEYS = {b"LMsk", b"Lr16", b"Lr32", b"Layr", b"Mt16", b"Mt32", b"Mtrn",
             b"Alph", b"FMsk", b"lnk2", b"lnk3", b"lnkE", b"FEid", b"FXid",
             b"PxSD", b"FELS", b"artd", b"cinf", b"extd", b"extn", b"pths"}

_GROUP_KEYS = (b"lsct", b"lsdk")
_TEXT_KEYS = (b"TySh", b"tySh")
_SMART_KEYS = (b"SoLd", b"PlLd", b"SoLE")
_VECTOR_KEYS = (b"vmsk", b"vsms")
_FILL_KEYS = (b"SoCo", b"GdFl", b"PtFl")
_ADJUSTMENT_KEYS = (b"levl", b"curv", b"hue ", b"hue2", b"brit", b"blnc",
                    b"blwh", b"expA", b"vibA", b"mixr", b"selc", b"phfl",
                    b"nvrt", b"post", b"thrs", b"grdm", b"clrL")

OPEN_FOLDER, CLOSED_FOLDER, DIVIDER = 1, 2, 3


class PsdError(OncemoreError):
    """The file is not a Photoshop document this reader can use."""


# --- byte reading -------------------------------------------------------------

class _Reader:
    """Bounds-checked cursor over [pos, end) of a bytes-like object."""

    def __init__(self, data, pos=0, end=None):
        self.data = data
        self.pos = pos
        self.end = len(data) if end is None else min(end, len(data))

    def left(self):
        return self.end - self.pos

    def need(self, n, what):
        if n < 0 or n > self.left():
            raise PsdError(f"truncated or damaged Photoshop file: {what} at byte "
                           f"{self.pos} needs {n} bytes, only {max(self.left(), 0)} left")

    def take(self, n, what):
        self.need(n, what)
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def unpack(self, fmt, what):
        size = struct.calcsize(fmt)
        self.need(size, what)
        v = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return v

    def u8(self, what):
        return self.unpack(">B", what)[0]

    def u16(self, what):
        return self.unpack(">H", what)[0]

    def u32(self, what):
        return self.unpack(">I", what)[0]

    def length(self, wide, what):
        """A length field: 4 bytes, or 8 when `wide` (PSB)."""
        return self.unpack(">Q" if wide else ">I", what)[0]

    def sub(self, n, what):
        """A reader over the next n bytes; this one skips past them."""
        self.need(n, what)
        r = _Reader(self.data, self.pos, self.pos + n)
        self.pos += n
        return r


def _pascal(r, pad, what):
    """Pascal string padded so length byte + text is a multiple of `pad`."""
    n = r.u8(what)
    raw = bytes(r.take(n, what))
    r.pos += min((-(n + 1)) % pad, r.left())     # tolerate a missing pad byte
    try:
        return raw.decode("mac_roman")
    except UnicodeDecodeError:  # pragma: no cover - mac_roman maps every byte
        return raw.decode("latin-1")


def _unicode_string(data):
    """'luni'-style string: 4-byte UTF-16 unit count, UTF-16BE text."""
    if len(data) < 4:
        return None
    (n,) = struct.unpack_from(">I", data, 0)
    raw = bytes(data[4:4 + 2 * n])
    return raw.decode("utf-16-be", errors="replace").rstrip("\x00")


def _blocks(r, wide, pad):
    """Additional-info blocks until the end of `r`: {key: memoryview}.

    Layer-level blocks trust the length (pad 1); the global ones are aligned to
    4 bytes. Stops quietly at anything that is not a block signature."""
    out = {}
    while r.left() >= 12:
        sig = bytes(r.data[r.pos:r.pos + 4])
        if sig not in (b"8BIM", b"8B64"):
            break
        r.pos += 4
        key = bytes(r.take(4, "additional-info key"))
        n = r.length(wide and key in _BIG_KEYS, f"length of {key!r} block")
        out.setdefault(key, r.take(n, f"{key!r} block"))
        skip = (-n) % pad
        r.pos += min(skip, r.left())
    return out


# --- decompression ------------------------------------------------------------

def _unpackbits(src, n):
    """PackBits-decode one row, giving exactly n bytes (short rows are zero-padded)."""
    out = bytearray()
    i, end = 0, len(src)
    while i < end and len(out) < n:
        c = src[i]
        i += 1
        if c < 128:
            out += src[i:i + c + 1]
            i += c + 1
        elif c > 128 and i < end:
            out += src[i:i + 1] * (257 - c)
            i += 1
    if len(out) < n:
        out += bytes(n - len(out))
    return bytes(out[:n])


def _rle_counts(r, rows, wide, what):
    fmt = ">%d%s" % (rows, "I" if wide else "H")
    return r.unpack(fmt, f"{what} row byte counts")


def _inflate(data, size, what):
    """zlib-decompress at most `size` bytes (guards against zip bombs)."""
    d = zlib.decompressobj()
    try:
        out = d.decompress(bytes(data), size)
    except zlib.error as e:
        raise PsdError(f"{what}: damaged ZIP data ({e})") from None
    if len(out) < size:
        raise PsdError(f"{what}: ZIP data holds {len(out)} bytes, expected {size}")
    return out


def _unpredict(data, width, height, depth, what):
    """Undo ZIP prediction: each row stores deltas from the previous sample."""
    if depth == 8:
        rows = (accumulate(data[y * width:(y + 1) * width], lambda a, b: (a + b) & 255)
                for y in range(height))
        return b"".join(bytes(row) for row in rows)
    if depth == 16:
        out = bytearray()
        for y in range(height):
            row = struct.unpack_from(">%dH" % width, data, y * width * 2)
            out += struct.pack(">%dH" % width,
                               *accumulate(row, lambda a, b: (a + b) & 0xFFFF))
        return bytes(out)
    raise PsdError(f"{what}: ZIP prediction at {depth} bits is not supported")


def _to8(plane, depth):
    """8-bit samples from 8- or 16-bit (big-endian: keep the high byte)."""
    return plane if depth == 8 else bytes(plane[0::2])


def _decode(comp, data, width, height, depth, wide, what):
    """One channel's data (after the compression word) -> 8-bit plane."""
    row = width * depth // 8
    size = row * height
    if size == 0:
        return b""
    if comp == 0:
        if len(data) < size:
            raise PsdError(f"{what}: raw data is {len(data)} bytes, expected {size}")
        plane = bytes(data[:size])
    elif comp == 1:
        r = _Reader(data)
        counts = _rle_counts(r, height, wide, what)
        if sum(counts) * 64 < size:     # PackBits expands 2 bytes to 128 at most
            raise PsdError(f"{what}: PackBits data too short for {width} x {height}")
        parts = []
        for n in counts:
            parts.append(_unpackbits(bytes(r.take(n, what)), row))
        plane = b"".join(parts)
    elif comp == 2:
        plane = _inflate(data, size, what)[:size]
    elif comp == 3:
        plane = _unpredict(_inflate(data, size, what), width, height, depth, what)
    else:
        raise PsdError(f"{what}: unknown compression {comp}")
    return _to8(plane, depth)


def _interleave(planes, alpha, count):
    """RGBA bytes from 1 (gray) or 3 colour planes plus an alpha plane."""
    out = bytearray(count * 4)
    if len(planes) == 1:
        planes = planes * 3
    for i in range(3):
        out[i::4] = planes[i]
    out[3::4] = alpha
    return bytes(out)


_MUL = None


def _mul_table():
    """MUL[a << 8 | m] = a * m / 255, rounded: alpha times mask."""
    global _MUL
    if _MUL is None:
        _MUL = bytes((a * m + 127) // 255 for a in range(256) for m in range(256))
    return _MUL


_UNMATTE = None


def _unmatte_table():
    """Undo the merged image's white matte: stored = c*a + 255*(1-a)."""
    global _UNMATTE
    if _UNMATTE is None:
        t = bytearray(65536)
        for a in range(256):
            for s in range(256):
                if a == 0:
                    v = s
                else:
                    v = min(255, max(0, round((s - (255 - a)) * 255 / a)))
                t[a << 8 | s] = v
        _UNMATTE = bytes(t)
    return _UNMATTE


def _check_pixels(width, height, what):
    if width * height > MAX_PIXELS:
        raise PsdError(f"{what} is {width} x {height} pixels; too large to decode")


# --- layers -------------------------------------------------------------------

class LayerMask:
    """The user (pixel) mask of a layer: its own rectangle and default colour."""

    def __init__(self, layer, top, left, bottom, right, default_color, flags):
        self._layer = layer
        self.top, self.left, self.bottom, self.right = top, left, bottom, right
        self.default_color = default_color   # value outside the rectangle
        self.flags = flags
        self.relative = bool(flags & 1)       # "position relative to layer"
        self.disabled = bool(flags & 2)

    @property
    def bounds(self):
        return (self.left, self.top, self.right, self.bottom)

    @property
    def width(self):
        return max(0, self.right - self.left)

    @property
    def height(self):
        return max(0, self.bottom - self.top)

    def data(self):
        """8-bit mask values for the mask rectangle (width * height bytes),
        or None when the layer stores no mask channel."""
        ch = self._layer._channels.get(-2)
        if ch is None:
            return None
        _check_pixels(self.width, self.height, f"mask of layer {self._layer.name!r}")
        return self._layer._decode_channel(ch, self.width, self.height, "mask")


class Layer:
    """One layer record. Groups have `children` (top first); every layer but a
    top-level one has a `parent`. `index` is the record's position in the file
    (0 = bottom-most record, section dividers included)."""

    def __init__(self, doc, index):
        self._doc = doc
        self.index = index
        self.name = ""
        self.kind = "pixel"
        self.visible = True
        self.opacity = 255
        self.fill_opacity = 255
        self.blend_mode = "norm"
        self.clipping = False
        self.flags = 0
        self.top = self.left = self.bottom = self.right = 0
        self.children = []
        self.parent = None
        self.folder = None        # OPEN_FOLDER, CLOSED_FOLDER, DIVIDER or None
        self.layer_id = None      # Photoshop's "lyid", stable across saves
        self.mask = None
        self.info = {}            # additional-info key -> raw bytes
        self._channels = {}       # channel id -> (compression, memoryview)

    def __repr__(self):
        return f"<Layer {self.index} {self.kind} {self.name!r} {self.bounds}>"

    @property
    def bounds(self):
        """(left, top, right, bottom) in document pixels."""
        return (self.left, self.top, self.right, self.bottom)

    @property
    def width(self):
        return max(0, self.right - self.left)

    @property
    def height(self):
        return max(0, self.bottom - self.top)

    @property
    def is_empty(self):
        return self.width == 0 or self.height == 0

    @property
    def is_group(self):
        return self.kind == "group"

    @property
    def folder_open(self):
        """For groups: whether the folder is expanded in the Layers panel."""
        return self.folder == OPEN_FOLDER if self.is_group else None

    @property
    def effective_visible(self):
        """Visible, and so is every enclosing group."""
        layer = self
        while layer is not None:
            if not layer.visible:
                return False
            layer = layer.parent
        return True

    @property
    def path(self):
        """Names from the top-level group down to this layer."""
        names = []
        layer = self
        while layer is not None:
            names.append(layer.name)
            layer = layer.parent
        return tuple(reversed(names))

    def walk(self):
        """This layer's descendants, depth first, top first."""
        for child in self.children:
            yield child
            yield from child.walk()

    def _decode_channel(self, ch, width, height, what):
        comp, data = ch
        doc = self._doc
        return _decode(comp, data, width, height, doc.depth, doc.is_psb,
                       f"layer {self.name!r} {what} channel")

    def rgba(self):
        """The layer's own pixels as RGBA bytes (width * height * 4) for its
        bounds. A missing transparency channel means opaque; an enabled user
        mask is multiplied into alpha. Opacity and blending are not applied."""
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return b""
        _check_pixels(w, h, f"layer {self.name!r}")
        count = w * h
        ids = (0,) if self._doc.color_mode == GRAYSCALE else (0, 1, 2)
        planes = []
        for cid in ids:
            ch = self._channels.get(cid)
            planes.append(self._decode_channel(ch, w, h, str(cid)) if ch
                          else bytes(count))
        ch = self._channels.get(-1)
        alpha = self._decode_channel(ch, w, h, "alpha") if ch else b"\xff" * count
        if self.mask is not None and not self.mask.disabled and -2 in self._channels:
            alpha = self._apply_mask(alpha)
        return _interleave(planes, alpha, count)

    def _apply_mask(self, alpha):
        m = self.mask
        values = m.data()
        mul = _mul_table()
        w = self.width
        out = bytearray()
        default = bytes([m.default_color])
        # columns of the layer covered by the mask rectangle
        x0 = min(max(m.left, self.left), self.right)
        x1 = max(min(m.right, self.right), x0)
        before, inside, after = x0 - self.left, x1 - x0, self.right - x1
        mw = m.width
        for y in range(self.top, self.bottom):
            if m.top <= y < m.bottom and inside:
                o = (y - m.top) * mw + (x0 - m.left)
                mrow = default * before + values[o:o + inside] + default * after
            else:
                mrow = default * w
            o = (y - self.top) * w
            arow = alpha[o:o + w]
            out += bytes(mul[a << 8 | v] for a, v in zip(arow, mrow))
        return bytes(out)


def _classify(layer):
    info = layer.info
    for key in _GROUP_KEYS:
        if key in info and len(info[key]) >= 4:
            kind = struct.unpack_from(">I", info[key], 0)[0]
            if kind in (OPEN_FOLDER, CLOSED_FOLDER, DIVIDER):
                layer.folder = kind
                if len(info[key]) >= 12 and bytes(info[key][4:8]) == b"8BIM":
                    layer.blend_mode = bytes(info[key][8:12]).decode("latin-1")
                return "divider" if kind == DIVIDER else "group"
    if any(k in info for k in _TEXT_KEYS):
        return "text"
    if any(k in info for k in _SMART_KEYS):
        return "smart"
    has_fill = any(k in info for k in _FILL_KEYS)
    if any(k in info for k in _VECTOR_KEYS) and (has_fill or b"vscg" in info):
        return "shape"
    if has_fill:
        return "fill"
    if any(k in info for k in _ADJUSTMENT_KEYS):
        return "adjustment"
    return "pixel"


def _read_record(doc, r, index):
    """One layer record; returns (layer, [(channel id, length)])."""
    what = f"layer record {index}"
    layer = Layer(doc, index)
    top, left, bottom, right, nch = r.unpack(">4iH", what)
    if nch > MAX_CHANNELS:
        raise PsdError(f"{what} claims {nch} channels")
    for size in (right - left, bottom - top):
        if size > MAX_DIMENSION:
            raise PsdError(f"{what} is {right - left} x {bottom - top} pixels; "
                           f"the limit is {MAX_DIMENSION}")
    layer.top, layer.left, layer.bottom, layer.right = top, left, bottom, right
    channels = []
    for _ in range(nch):
        cid = r.unpack(">h", what)[0]
        channels.append((cid, r.length(doc.is_psb, what)))
    sig, blend, opacity, clipping, flags, _ = r.unpack(">4s4sBBBB", what)
    if sig not in (b"8BIM", b"8B64"):
        raise PsdError(f"{what}: bad blend-mode signature {sig!r}")
    layer.blend_mode = blend.decode("latin-1")
    layer.opacity = opacity
    layer.clipping = clipping != 0
    layer.flags = flags
    layer.visible = not flags & 2
    extra = r.sub(r.u32(what), what)

    mask = extra.sub(extra.u32(what), f"{what} mask")
    if mask.left() >= 18:
        mt, ml, mb, mr, default, mflags = mask.unpack(">4iBB", f"{what} mask")
        layer.mask = LayerMask(layer, mt, ml, mb, mr, default, mflags)
        if layer.mask.width > MAX_DIMENSION or layer.mask.height > MAX_DIMENSION:
            raise PsdError(f"{what}: mask rectangle is too large")
    extra.sub(extra.u32(what), f"{what} blending ranges")
    pascal = _pascal(extra, 4, f"{what} name")
    layer.info = {k: bytes(v) for k, v in _blocks(extra, doc.is_psb, 1).items()}

    unicode_name = _unicode_string(layer.info.get(b"luni", b""))
    layer.name = unicode_name if unicode_name else pascal
    if len(layer.info.get(b"lyid", b"")) >= 4:
        layer.layer_id = struct.unpack(">I", layer.info[b"lyid"][:4])[0]
    if layer.info.get(b"iOpa"):
        layer.fill_opacity = layer.info[b"iOpa"][0]
    layer.kind = _classify(layer)
    return layer, channels


def _read_layer_info(doc, r):
    """Layer count, records and channel data (the body of the layer info)."""
    if r.left() < 2:
        return []
    count = r.unpack(">h", "layer count")[0]
    doc.merged_alpha_flag = count < 0
    count = abs(count)
    if count > MAX_LAYERS:
        raise PsdError(f"the file claims {count} layers; the limit is {MAX_LAYERS}")
    records = [_read_record(doc, r, i) for i in range(count)]
    for layer, channels in records:
        for cid, length in channels:
            what = f"layer {layer.name!r} channel {cid}"
            body = r.sub(length, what)
            if length < 2:
                continue    # no data stored (zero-length channel)
            comp = body.u16(what)
            layer._channels[cid] = (comp, body.data[body.pos:body.end])
    return [layer for layer, _ in records]


def _build_tree(records):
    """Top-first nested lists from bottom-first records."""
    stack = [[]]    # open groups' children, bottom first
    for layer in records:
        if layer.kind == "divider":
            stack.append([])
        elif layer.kind == "group":
            children = stack.pop() if len(stack) > 1 else []
            layer.children = children[::-1]
            for child in layer.children:
                child.parent = layer
            stack[-1].append(layer)
        else:
            stack[-1].append(layer)
    # unmatched dividers: hand their layers to the level below
    while len(stack) > 1:
        orphans = stack.pop()
        stack[-1].extend(orphans)
    return stack[0][::-1]


# --- document -----------------------------------------------------------------

class Document:
    """A parsed Photoshop file. `layers` is the top level, top first."""

    def __init__(self):
        self.version = 1
        self.width = self.height = 0
        self.depth = 8
        self.channels = 0
        self.color_mode = RGB
        self.layers = []
        self.records = []       # every layer record in file order (bottom first)
        self.resources = {}     # image resource id -> bytes
        self.merged_alpha_flag = False
        self.global_info = {}   # global additional-info key -> bytes
        self._merged = None     # (compression, memoryview) of the merged image

    @property
    def is_psb(self):
        return self.version == 2

    @property
    def color_mode_name(self):
        return _MODE_NAMES.get(self.color_mode, str(self.color_mode))

    def walk(self):
        """Every layer of the tree, depth first, top first (a group comes
        before its children). Section dividers are not included."""
        for layer in self.layers:
            yield layer
            yield from layer.walk()

    def find(self, name):
        """The first layer (in walk() order) with this name, or None."""
        return next((layer for layer in self.walk() if layer.name == name), None)

    def has_transparency(self):
        """Whether the merged image's first extra channel is its alpha."""
        base = _BASE_CHANNELS[self.color_mode]
        if self.channels <= base:
            return False
        if any(k in self.global_info for k in (b"Mtrn", b"Mt16", b"Mt32")):
            return True
        if self.merged_alpha_flag:
            return True
        ids = self.resources.get(1053)     # alpha channel identifiers
        if ids and len(ids) >= 4:
            values = struct.unpack(">%dI" % (len(ids) // 4), ids[:len(ids) // 4 * 4])
            if all(v > 0 for v in values):
                return False
        return not self.records

    def composite(self):
        """The merged (flattened) image saved by Photoshop as RGBA bytes, or
        None when the file has none. Its white matte is removed where the
        document is transparent."""
        if self._merged is None:
            return None
        comp, data = self._merged
        w, h, depth = self.width, self.height, self.depth
        _check_pixels(w, h, "the merged image")
        base = _BASE_CHANNELS[self.color_mode]
        alpha_index = base if self.has_transparency() else None
        wanted = base + (1 if alpha_index is not None else 0)
        row = w * depth // 8
        size = row * h
        planes = []
        what = "merged image"
        if comp == 0:
            for i in range(wanted):
                chunk = data[i * size:(i + 1) * size]
                planes.append(_decode(0, chunk, w, h, depth, False, what))
        elif comp == 1:
            r = _Reader(data)
            counts = _rle_counts(r, h * self.channels, self.is_psb, what)
            pos = r.pos
            for i in range(wanted):
                parts = []
                for n in counts[i * h:(i + 1) * h]:
                    parts.append(_unpackbits(bytes(data[pos:pos + n]), row))
                    pos += n
                planes.append(_to8(b"".join(parts), depth))
        elif comp in (2, 3):
            raw = _inflate(data, size * wanted, what)
            for i in range(wanted):
                plane = raw[i * size:(i + 1) * size]
                if comp == 3:
                    plane = _unpredict(plane, w, h, depth, what)
                planes.append(_to8(plane, depth))
        else:
            raise PsdError(f"merged image: unknown compression {comp}")
        count = w * h
        if alpha_index is None:
            return _interleave(planes, b"\xff" * count, count)
        alpha = planes[alpha_index]
        table = _unmatte_table()
        colour = [bytes(table[a << 8 | s] for a, s in zip(alpha, p))
                  for p in planes[:base]]
        return _interleave(colour, alpha, count)


def _read_header(doc, r):
    sig, version = r.unpack(">4sH", "header")
    if sig != b"8BPS":
        raise PsdError("not a Photoshop file (no 8BPS signature)")
    if version not in (1, 2):
        raise PsdError(f"unknown Photoshop file version {version}")
    r.take(6, "header")
    channels, height, width, depth, mode = r.unpack(">HIIHH", "header")
    doc.version, doc.channels = version, channels
    doc.width, doc.height, doc.depth, doc.color_mode = width, height, depth, mode
    if not 1 <= channels <= MAX_CHANNELS:
        raise PsdError(f"the file claims {channels} channels")
    if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION):
        raise PsdError(f"image size {width} x {height} is out of range "
                       f"(1 to {MAX_DIMENSION} pixels per side)")
    if mode not in _BASE_CHANNELS:
        raise PsdError(f"{doc.color_mode_name} Photoshop files are not supported; "
                       "save the design as RGB",
                       hint="In Photoshop, choose Image > Mode > RGB Color "
                            "(8 Bits/Channel) and save again.")
    if depth not in (8, 16):
        raise PsdError(f"{depth}-bit Photoshop files are not supported; "
                       "save the design as 8 bits per channel",
                       hint="In Photoshop, choose Image > Mode > 8 Bits/Channel "
                            "and save again.")
    if channels < _BASE_CHANNELS[mode]:
        raise PsdError(f"{doc.color_mode_name} file with only {channels} channels")


def _read_resources(doc, r):
    while r.left() >= 12:
        if bytes(r.take(4, "image resource")) != b"8BIM":
            break
        rid = r.u16("image resource id")
        _pascal(r, 2, "image resource name")
        n = r.u32("image resource length")
        doc.resources[rid] = bytes(r.take(n, f"image resource {rid}"))
        r.take(n % 2 if r.left() else 0, "image resource padding")


def _read_layer_and_mask(doc, r):
    wide = doc.is_psb
    info = r.sub(r.length(wide, "layer info length"), "layer info")
    records = _read_layer_info(doc, info)
    # global layer mask info: present unless the extra blocks start right away
    if r.left() >= 4 and bytes(r.data[r.pos:r.pos + 4]) not in (b"8BIM", b"8B64"):
        r.sub(r.u32("global layer mask length"), "global layer mask")
    doc.global_info = {k: bytes(v) for k, v in _blocks(r, wide, 4).items()}
    if not records:
        if b"Lr16" in doc.global_info:
            records = _read_layer_info(doc, _Reader(doc.global_info[b"Lr16"]))
        elif b"Lr32" in doc.global_info:
            raise PsdError("32-bit layers are not supported",
                           hint="Convert the document to 8 Bits/Channel.")
    return records


def read_psd(source):
    """Parse a .psd / .psb file (a path or the file's bytes) into a Document."""
    if isinstance(source, (bytes, bytearray, memoryview)):
        data = bytes(source)
    else:
        try:
            with open(os.fspath(source), "rb") as f:
                data = f.read()
        except OSError as e:
            raise PsdError(f"cannot read {source}: {e.strerror or e}") from None
    data = memoryview(data)
    doc = Document()
    r = _Reader(data)
    _read_header(doc, r)
    r.sub(r.u32("colour mode data length"), "colour mode data")
    _read_resources(doc, r.sub(r.u32("image resources length"), "image resources"))
    lm = r.sub(r.length(doc.is_psb, "layer section length"), "layer and mask section")
    doc.records = _read_layer_and_mask(doc, lm)
    doc.layers = _build_tree(doc.records)
    if r.left() >= 2:
        comp = r.u16("merged image compression")
        doc._merged = (comp, data[r.pos:r.end])
        _check_merged(doc)
    return doc


def _check_merged(doc):
    """Make sure the merged image's data is all there (so truncation is
    reported by read_psd, not later)."""
    comp, data = doc._merged
    row = doc.width * doc.depth // 8
    what = "merged image"
    if comp == 0:
        _Reader(data).need(row * doc.height * doc.channels, what)
    elif comp == 1:
        r = _Reader(data)
        counts = _rle_counts(r, doc.height * doc.channels, doc.is_psb, what)
        r.need(sum(counts), what)
    elif comp not in (2, 3):
        raise PsdError(f"merged image: unknown compression {comp}")


# --- PNG output ---------------------------------------------------------------

def _png_chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png_bytes(width, height, rgba):
    """An 8-bit RGBA PNG (colour type 6) from straight RGBA bytes."""
    if len(rgba) != width * height * 4:
        raise ValueError(f"expected {width * height * 4} RGBA bytes, got {len(rgba)}")
    stride = width * 4
    raw = b"".join(b"\x00" + bytes(rgba[y * stride:(y + 1) * stride])
                   for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(raw, 9))
            + _png_chunk(b"IEND", b""))


def write_png(path, width, height, rgba):
    """Write straight RGBA bytes as a PNG file; returns the path."""
    with open(path, "wb") as f:
        f.write(png_bytes(width, height, rgba))
    return path
