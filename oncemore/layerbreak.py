"""The layer break of a dual-layer (DVD-9) disc.

A dual-layer DVD-Video is written opposite track path: the first layer from
the inside out, the second from where the first ended back in. The player
jumps between them once, and the picture can hold still for a moment there,
so the break is put where it shows least: at the start of a chapter (a cell
of a title). The disc formats ask that

* the break is on an ECC block boundary (16 sectors of 2048 bytes),
* the first layer holds at least as much as the second, and
* the first layer is no larger than a layer of a DVD±R DL (2,085,856
  sectors: half the smaller of the two, a DVD-R DL).

The break is `disc.layer_break`: "auto" (the first chapter past the middle of
the disc) or "<title id>:<chapter>". The built-in image writer moves VIDEO_TS
by up to 15 sectors so that chapter falls on an ECC block; images from the
other tools are checked as they are. The sector is reported, for the
tool that writes the disc (burn.py gives it to its writer).

Sector numbers in the IFO files are relative: the title VOBs start at
`vtstt_vobs` (0xC4) of their VTS_NN_0.IFO, and a cell's first sector (in the
program chain's cell playback table) is counted from there.
"""

import os
import struct

from .errors import OncemoreError

SECTOR = 2048
ECC = 16
LAYER_MAX = 2_085_856          # sectors on one layer of a DVD-R DL (4,171,712 / 2)
SINGLE_LAYER = 2_295_104       # sectors on a single-layer DVD±R


def _u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def _u32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def chapter_cells(ifo):
    """The chapters of a VTS_NN_0.IFO (its bytes): [(title number in the
    titleset, chapter, first sector)], the sector relative to the start of
    the title VOBs."""
    if ifo[:12] != b"DVDVIDEO-VTS":
        raise OncemoreError("not a titleset IFO")
    ptt = _u32(ifo, 0xC8) * SECTOR
    pgcit = _u32(ifo, 0xCC) * SECTOR
    ntitles, end = _u16(ifo, ptt), ptt + _u32(ifo, ptt + 4) + 1
    offsets = [ptt + _u32(ifo, ptt + 8 + 4 * k) for k in range(ntitles)] + [end]
    out = []
    for ttn in range(1, ntitles + 1):
        a, b = offsets[ttn - 1], offsets[ttn]
        for ch, o in enumerate(range(a, b - 3, 4), 1):
            pgcn, pgn = _u16(ifo, o), _u16(ifo, o + 2)
            pgc = pgcit + _u32(ifo, pgcit + 8 + 8 * (pgcn - 1) + 4)
            cell = ifo[pgc + _u16(ifo, pgc + 0xE6) + pgn - 1]          # the program's entry cell
            cpb = pgc + _u16(ifo, pgc + 0xE8) + 24 * (cell - 1)
            out.append((ttn, ch, _u32(ifo, cpb + 8)))
    return out


def vts_bases(ifo_bytes):
    """{titleset: sector of its title VOBs, relative to VIDEO_TS.IFO} from
    the VMG and VTS IFOs ({"VIDEO_TS.IFO": bytes, "VTS_01_0.IFO": bytes, ...})."""
    vmg = ifo_bytes["VIDEO_TS.IFO"]
    if vmg[:12] != b"DVDVIDEO-VMG":
        raise OncemoreError("VIDEO_TS.IFO is not a DVD-Video IFO")
    tt = _u32(vmg, 0xC4) * SECTOR
    starts = {}
    for k in range(_u16(vmg, tt)):
        o = tt + 8 + 12 * k
        starts[vmg[o + 6]] = _u32(vmg, o + 8)
    return {vts: start + _u32(ifo_bytes[f"VTS_{vts:02d}_0.IFO"], 0xC4)
            for vts, start in starts.items()}


def chapters(ifo_bytes):
    """Every chapter on the disc: [(titleset, title number, chapter, sector
    relative to VIDEO_TS.IFO)], in disc order."""
    out = []
    for vts, base in sorted(vts_bases(ifo_bytes).items()):
        for ttn, ch, s in chapter_cells(ifo_bytes[f"VTS_{vts:02d}_0.IFO"]):
            out.append((vts, ttn, ch, base + s))
    return sorted(out, key=lambda c: c[3])


def read_folder(video_ts):
    """The IFO files of a VIDEO_TS folder."""
    out = {}
    for n in os.listdir(video_ts):
        if n == "VIDEO_TS.IFO" or n.endswith("_0.IFO"):
            with open(os.path.join(video_ts, n), "rb") as f:
                out[n] = f.read()
    return out


# -- an ISO 9660 image -------------------------------------------------------------

def _records(f, lba, size):
    f.seek(lba * SECTOR)
    data = f.read(size)
    i = 0
    while i < len(data):
        n = data[i]
        if n == 0:                         # the rest of this sector is padding
            i = (i // SECTOR + 1) * SECTOR
            continue
        rec = data[i:i + n]
        name = rec[33:33 + rec[32]]
        yield name.split(b";")[0].decode("ascii", "replace").upper(), _u32(rec, 6), _u32(rec, 14), \
            bool(rec[25] & 2)
        i += n


def iso_video_ts(path):
    """{file name: (first sector, bytes)} of VIDEO_TS in an ISO image."""
    with open(path, "rb") as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if pvd[:6] != b"\x01CD001":
            raise OncemoreError(f"{path} has no ISO 9660 volume")
        root = pvd[156:190]
        for name, lba, size, is_dir in _records(f, _u32(root, 6), _u32(root, 14)):
            if is_dir and name == "VIDEO_TS":
                return {n: (lba2, size2) for n, lba2, size2, d in _records(f, lba, size) if not d}
    raise OncemoreError(f"{path} has no VIDEO_TS folder")


def iso_chapters(path):
    """The chapters of a DVD image with their sector on the disc, and the
    image's sectors: ([(titleset, title, chapter, sector)], total)."""
    files = iso_video_ts(path)
    ifos = {}
    with open(path, "rb") as f:
        for n, (lba, size) in files.items():
            if n == "VIDEO_TS.IFO" or n.endswith("_0.IFO"):
                f.seek(lba * SECTOR)
                ifos[n] = f.read(size)
    at = files["VIDEO_TS.IFO"][0]
    return [(v, t, c, at + s) for v, t, c, s in chapters(ifos)], os.path.getsize(path) // SECTOR


# -- choosing ------------------------------------------------------------------

def problem(sector, total):
    """Why `sector` cannot be the layer break of an image of `total` sectors
    (None when it can)."""
    if 2 * sector < total:
        return "the second layer would hold more than the first"
    if sector > LAYER_MAX:
        return f"the first layer would hold more than a layer of a dual-layer disc " \
               f"({LAYER_MAX} sectors)"
    if sector % ECC:
        return f"sector {sector} is not on an ECC block (a multiple of {ECC})"
    return None


def needed(total):
    return total > SINGLE_LAYER


def pick(chapter_list, total, want=None, shift_ok=False):
    """The layer break: (chapter tuple, sector, shift) where shift is the
    number of sectors VIDEO_TS would move (0..15, only with `shift_ok`; the
    image grows by as much). `want` = (titleset, title, chapter) or None for
    the first one that works. Raises OncemoreError when none does."""
    def fits(s):
        shift = (-s) % ECC if shift_ok else 0
        return shift, problem(s + shift, total + shift)

    if want is not None:
        for c in chapter_list:
            if c[:3] == tuple(want):
                shift, why = fits(c[3])
                if why:
                    raise OncemoreError(f"the layer break cannot go there: {why}")
                return c, c[3] + shift, shift
        raise OncemoreError("the layer break chapter is not on the disc")
    for c in chapter_list:
        shift, why = fits(c[3])
        if not why:
            return c, c[3] + shift, shift
    raise OncemoreError("no chapter is in the middle part of the disc where the layer "
                        "break can go",
                        hint="Add a chapter near the middle of the disc, or choose one in "
                             "Disc > Layer break.")
