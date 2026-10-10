"""Soft 3:2 pulldown: turn a 23.976 fps progressive MPEG-2 video stream into
one that NTSC players show at 29.97 fps, without encoding a single extra
picture.

The encoder writes the film frames as they are. This module then edits
fixed-position bits in the stream's headers, the same way film DVDs are
made:

* sequence header: frame_rate_code 1 (23.976) -> 4 (29.97)
* sequence extension: progressive_sequence 1 -> 0
* picture coding extension of every picture: progressive_frame = 1, and
  top_field_first / repeat_first_field cycling through
  (1,1) (0,0) (0,1) (1,0) in display order, so every frame shows 3, 2, 3, 2
  fields and the field parity never breaks.

Display order is taken from each picture's temporal_reference, counted from
the GOP header, so streams with B-frames are handled. No byte is inserted or
removed, so the stream stays valid and the same size.
"""

import mmap

PATTERN = ((1, 1), (0, 0), (0, 1), (1, 0))      # (top_field_first, repeat_first_field)


def soft_pulldown(b):
    """Patch `b` (a bytearray or a writable mmap) in place; returns the
    number of pictures."""
    i = pictures = base = in_gop = 0
    tr = 0
    size = len(b)
    while True:
        i = b.find(b"\x00\x00\x01", i)
        if i < 0 or i + 9 > size:
            break
        code = b[i + 3]
        if code == 0xB3:                     # sequence header
            b[i + 7] = (b[i + 7] & 0xF0) | 4
        elif code == 0xB8:                   # GOP: display order starts again
            base += in_gop
            in_gop = 0
        elif code == 0x00:                   # picture header
            tr = (b[i + 4] << 2) | (b[i + 5] >> 6)
            in_gop = max(in_gop, tr + 1)
        elif code == 0xB5:
            ext = b[i + 4] >> 4
            if ext == 1:                     # sequence extension
                b[i + 5] &= 0xF7             # progressive_sequence = 0
            elif ext == 8:                   # picture coding extension
                tff, rff = PATTERN[(base + tr) % 4]
                # byte 7: top_field_first(7) ... repeat_first_field(1) chroma_420_type(0)
                b[i + 7] = (b[i + 7] & 0x7C) | (tff << 7) | (rff << 1) | 0x01
                b[i + 8] |= 0x80             # progressive_frame
                pictures += 1
        i += 4
    return pictures


def patch_file(path):
    """Apply soft pulldown to an MPEG-2 elementary stream file in place
    (memory-mapped, so a feature-length stream is not read into memory)."""
    with open(path, "r+b") as f, mmap.mmap(f.fileno(), 0) as m:
        n = soft_pulldown(m)
        m.flush()
    return n
