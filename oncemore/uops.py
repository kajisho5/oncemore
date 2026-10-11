"""User operations: remote keys a title or a menu does not allow.

A project lists them by name in a title's or a menu's `prohibit` (for
example a notice that cannot be skipped: ["next", "fast_forward", "menu"]).
On a DVD they are the program chain's prohibited user operations (UOP 0-24
in the PGC, 4 bytes at offset 8; dvdauthor leaves them clear, so the IFO
files are patched after it); on a Blu-ray they are the playlist's and its
play items' UO mask (64 bits, written with the playlist).
"""

import os
import struct

# names the project uses, in the order the app shows them
NAMES = ("next", "prev", "fast_forward", "rewind", "pause", "stop", "search", "menu", "title",
         "audio", "subtitle")

# DVD: UOP numbers (bit n of the big-endian 32-bit field)
DVD_UOPS = {
    "search": (0, 1, 2, 5),            # title / chapter / time play and search (number keys)
    "stop": (3,),
    "prev": (6,),
    "next": (7,),
    "fast_forward": (8,),
    "rewind": (9,),
    "title": (10,),                    # Menu_Call(Title)
    "menu": (11, 12, 13, 14, 15),      # Menu_Call(Root) and the other menus
    "pause": (19,),
    "audio": (20,),
    "subtitle": (21,),
}

# Blu-ray: UO_mask_table bits, counted from the most significant
BD_UOS = {
    "menu": (0, 24),                   # menu call (top menu), pop-up on
    "title": (0,),
    "search": (1, 2, 3),               # title / chapter / time search
    "next": (4,),
    "prev": (5,),
    "stop": (7,),
    "pause": (8,),
    "fast_forward": (11,),
    "rewind": (12,),
    "audio": (21,),
    "subtitle": (26, 27),
}


def dvd_mask(names):
    mask = 0
    for n in names or ():
        for bit in DVD_UOPS[n]:
            mask |= 1 << bit
    return mask


def bd_mask(names):
    mask = 0
    for n in names or ():
        for bit in BD_UOS[n]:
            mask |= 1 << (63 - bit)
    return mask


# -- DVD IFO files -------------------------------------------------------------

SECTOR = 2048


def _u16(buf, at):
    return struct.unpack_from(">H", buf, at)[0]


def _u32(buf, at):
    return struct.unpack_from(">I", buf, at)[0]


def _pgcit_pgcs(buf, start):
    """Byte offsets of the PGCs of a PGC information table at `start`."""
    n = _u16(buf, start)
    return [start + _u32(buf, start + 8 + 8 * k + 4) for k in range(n)]


def _menu_pgcs(buf, ut):
    """Per language unit of a PGCI_UT at `ut`: its PGCs' byte offsets."""
    n = _u16(buf, ut)
    return [_pgcit_pgcs(buf, ut + _u32(buf, ut + 8 + 8 * k + 4)) for k in range(n)]


def _set(buf, pgc, mask):
    struct.pack_into(">I", buf, pgc + 8, _u32(buf, pgc + 8) | mask)


def _patch(path, fn):
    """Apply fn to the IFO file and to its backup (the .BUP copy)."""
    for p in (path, path[:-4] + ".BUP"):
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as f:
            buf = bytearray(f.read())
        fn(buf)
        with open(p, "wb") as f:
            f.write(buf)


def patch_dvd(video_ts, project):
    """Write the titles' and menus' prohibited user operations into the
    VIDEO_TS of a built disc (as authored by author.build_xml: one PGC per
    title in its titleset, the menus' PGCs in titleset 1 by number)."""
    changed = 0
    for ts in range(1, project.titleset_count + 1):
        titles = project.titleset_titles(ts)
        menus = project.menus if ts == 1 else []
        want_t = {k: dvd_mask(t.prohibit) for k, t in enumerate(titles)}
        want_m = {}
        for m in menus:
            mask = dvd_mask(m.prohibit)
            for n in {m.number, m.loop_pgc or m.number}:
                want_m[n - 1] = mask
        if not any(want_t.values()) and not any(want_m.values()):
            continue

        def fn(buf, want_t=want_t, want_m=want_m):
            pgcs = _pgcit_pgcs(buf, _u32(buf, 0xCC) * SECTOR)
            for k, mask in want_t.items():
                if mask:
                    _set(buf, pgcs[k], mask)
            if any(want_m.values()) and _u32(buf, 0xD0):
                for unit in _menu_pgcs(buf, _u32(buf, 0xD0) * SECTOR):
                    for k, mask in want_m.items():
                        if mask and k < len(unit):
                            _set(buf, unit[k], mask)
        _patch(os.path.join(video_ts, f"VTS_{ts:02d}_0.IFO"), fn)
        changed += 1
    # the title search table: a title whose number keys are off says so too
    searchless = [t.global_number for t in project.titles if "search" in (t.prohibit or ())]
    if searchless:
        def vmg(buf):
            srpt = _u32(buf, 0xC4) * SECTOR
            for n in searchless:
                buf[srpt + 8 + 12 * (n - 1)] |= 0x03     # UOP 0 and 1 for the whole title
        _patch(os.path.join(video_ts, "VIDEO_TS.IFO"), vmg)
    return changed
