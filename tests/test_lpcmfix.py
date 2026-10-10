import struct
import unittest

from oncemore import lpcmfix


def lpcm_pes(payload_len, nframes=7, fau=4, sid=0xA0):
    """MPEG-2 private stream 1 PES with a DVD LPCM header (stereo 16-bit 48k)."""
    hdr_ext = b"\x21\x00\x01\x00\x01"                     # a PTS (5 bytes)
    body = bytes([sid, nframes]) + struct.pack(">H", fau) + bytes([0x00, 0x01, 0x80])
    body += bytes(payload_len)
    pes = b"\x00\x00\x01\xbd" + struct.pack(">H", 3 + len(hdr_ext) + len(body))
    return pes + b"\x81\x80" + bytes([len(hdr_ext)]) + hdr_ext + body


class TestLpcmFix(unittest.TestCase):
    def test_counts_and_pointers(self):
        # 320-byte frames: packets of 2000 bytes start frames at 0, 320, ...
        buf = bytearray(lpcm_pes(2000) + lpcm_pes(2000) + lpcm_pes(100))
        state = {}
        self.assertEqual(lpcmfix.fix_buffer(buf, state), 3)
        pkts = []
        i = 0
        while (i := buf.find(b"\x00\x00\x01\xbd", i)) >= 0:
            sub = i + 9 + buf[i + 8]
            pkts.append((buf[sub + 1], struct.unpack_from(">H", buf, sub + 2)[0]))
            i += 4
        # packet 1: bytes 0..1999 -> frames at 0..1920 = 7, first at 0
        # packet 2: bytes 2000..3999 -> first frame at 2240 (offset 240), 6 frames
        # packet 3: bytes 4000..4099 -> frame at 4160? no -> 0 frames
        self.assertEqual(pkts, [(7, 4), (6, 244), (0, 0)])
        self.assertEqual(state, {0xA0: 4100})

    def test_streams_are_independent_and_other_packets_untouched(self):
        other = b"\x00\x00\x01\xe0\x00\x03\x80\x00\x00"
        buf = bytearray(lpcm_pes(400, sid=0xA0) + other + lpcm_pes(400, sid=0xA1))
        before = bytes(buf)
        state = {}
        lpcmfix.fix_buffer(buf, state)
        self.assertEqual(state, {0xA0: 400, 0xA1: 400})
        self.assertIn(other, bytes(buf))
        self.assertEqual(len(buf), len(before))

    def test_frame_bytes(self):
        self.assertEqual(lpcmfix._frame_bytes(0x01), 320)     # 16-bit 48 kHz stereo
        self.assertEqual(lpcmfix._frame_bytes(0x81), 480)     # 24-bit
        self.assertEqual(lpcmfix._frame_bytes(0x00), 160)     # mono


if __name__ == "__main__":
    unittest.main()
