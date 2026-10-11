"""User operations: remote keys a title or a menu does not allow.

A project lists them by name in a title's or a menu's `prohibit` (for
example a notice that cannot be skipped: ["next", "fast_forward", "menu"]).
On a DVD they are the program chain's prohibited user operations (UOP 0-24
in the PGC, 4 bytes at offset 8, written by vtskit from `dvd_mask`); on a
Blu-ray they are the playlist's and its play items' UO mask (64 bits,
written with the playlist).
"""

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
