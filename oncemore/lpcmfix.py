"""Repair the LPCM private-stream headers ffmpeg writes into DVD program streams.

Each DVD LPCM PES payload starts with a 7-byte header; two of its fields say
how many audio frames (1/600 s each) *start* in the packet and where the first
one begins. ffmpeg's mpeg muxer writes fixed values there (7 frames, offset 4),
so dvdauthor, which derives packet durations from that count, reports
thousands of "Audio pts ... moves backwards" warnings and builds its audio
timing tables from wrong data.

oncemore encodes LPCM in 80-sample frames (exactly one DVD LPCM frame) so the
PTS ffmpeg writes is the PTS of the first frame starting in each packet; this
module then rewrites the frame count and first-frame pointer of every LPCM
packet in place, from the byte position of the packet in its audio stream.
"""

import struct

_SAMPLES_PER_FRAME = {0: 80, 1: 160}   # 48 kHz, 96 kHz: 1/600 s
_BITS = {0: 16, 1: 20, 2: 24}


def _frame_bytes(hdr1):
    """Bytes per 1/600 s from the second LPCM header byte."""
    quant, freq, ch = hdr1 >> 6, (hdr1 >> 4) & 3, (hdr1 & 7) + 1
    return _SAMPLES_PER_FRAME.get(freq, 80) * ch * _BITS.get(quant, 16) // 8


def fix_buffer(buf, state):
    """Patch LPCM PES headers inside `buf` (a bytearray). `state` maps
    substream id -> bytes of that stream seen so far. Returns packets fixed."""
    fixed = 0
    i, n = 0, len(buf)
    while True:
        i = buf.find(b"\x00\x00\x01\xbd", i)
        if i < 0 or i + 9 > n:
            return fixed
        length = struct.unpack_from(">H", buf, i + 4)[0]
        end = i + 6 + length
        if end > n or (buf[i + 6] & 0xC0) != 0x80:   # not an MPEG-2 PES we understand
            i += 4
            continue
        sub = i + 9 + buf[i + 8]                      # after the PES header extension
        if sub + 7 <= end and 0xA0 <= buf[sub] <= 0xA7:
            sid = buf[sub]
            fb = _frame_bytes(buf[sub + 5])
            payload = end - (sub + 7)
            seen = state.get(sid, 0)
            first = (-seen) % fb                      # offset of the first frame start
            count = 0 if first >= payload else 1 + (payload - first - 1) // fb
            buf[sub + 1] = count
            # pointer counts from the byte after itself, across the 3 LPCM
            # header bytes, to the first byte of the frame (0 = none)
            struct.pack_into(">H", buf, sub + 2, first + 4 if count else 0)
            state[sid] = seen + payload
            fixed += 1
        i = end


def fix_file(path, chunk=2048 * 512):
    """Fix every LPCM packet of an MPEG-PS file in place. Returns packets fixed.

    DVD program streams from ffmpeg use 2048-byte packs and a PES never
    crosses a pack, so the file is processed in whole packs.
    """
    state, fixed = {}, 0
    with open(path, "r+b") as f:
        pos = 0
        while True:
            f.seek(pos)
            data = f.read(chunk)
            if not data:
                break
            usable = len(data) - len(data) % 2048 if len(data) >= 2048 else len(data)
            buf = bytearray(data[:usable])
            fixed += fix_buffer(buf, state)
            f.seek(pos)
            f.write(buf)
            pos += usable
            if usable == 0:
                break
    return fixed
