"""Blu-ray output: a BDMV folder of HD titles with chapters (DECISIONS §53).

ffmpeg encodes every title (H.264 with x264's Blu-ray settings, AC-3 or
LPCM sound) straight into a BDAV transport stream (.m2ts). The files a
player navigates by are written here: index.bdmv (first play, the titles),
MovieObject.bdmv (the commands that play each title and say what follows
it), one playlist (.mpls) per title with its chapter marks, and the clip
information (.clpi) with the entry-point map players seek with.

The layouts follow the BD-ROM format as libbluray reads it; the tests read
every disc back with libbluray.
"""

import dataclasses
import math
import os
import shutil
import struct

from . import encode
from .errors import OncemoreError, ProjectError
from .project import parse_action, title_fps

CAPACITY = {"BD25": 25_025_314_816, "BD50": 50_050_629_632}
MAX_VIDEO_BPS = 40_000_000     # Blu-ray primary video limit
MIN_VIDEO_BPS = 4_000_000      # below this an HD picture falls apart
VBV_BUFFER = 30_000_000        # coded picture buffer at level 4.1
DISC_SAFETY = 0.03             # transport-stream overhead and some free space
TS_RATE = 48_000_000 // 8      # ts_recording_rate: the 48 Mbit/s maximum, in bytes/s

VIDEO_PID = 0x1011
AUDIO_PID = 0x1100             # + track number
PG_PID = 0x1200                # + subtitle track number
IG_PID = 0x1400                # a menu's buttons (Interactive Graphics)
LAST_MENU_REG = 1              # GPR: title number of the menu shown last
ENTRY_REG = 2                  # GPR: button a link highlights in the menu it opens (0 = none)
LOOP_REG = 3                   # GPR: times the current menu has played (menus with a loop count)
OVERRIDE_REG = 4               # GPR: end-action override k of the playing title (0 = none)
PMT_PID = 0x0100
VERSION = b"0200"

WIDTH, HEIGHT = 1920, 1080

# frame rate -> (video_format, frame_rate) codes; 25 and 29.97 fps are coded
# as progressive frames in an interlaced (1080i) stream, as the format has
# no 1080p at those rates
FORMATS = {
    (24000, 1001): (6, 1),     # 1080p 23.976
    (25, 1): (4, 3),           # 1080i 25
    (30000, 1001): (4, 4),     # 1080i 29.97
}
CODING_H264, CODING_LPCM, CODING_AC3, CODING_PG, CODING_IG = 0x1B, 0x80, 0x81, 0x90, 0x91

# ISO 639-1 (the project's codes) -> ISO 639-2/B (the disc's)
LANGS = {
    "ar": "ara", "bg": "bul", "ca": "cat", "cs": "cze", "da": "dan", "de": "ger",
    "el": "gre", "en": "eng", "es": "spa", "et": "est", "fa": "per", "fi": "fin",
    "fr": "fre", "he": "heb", "hi": "hin", "hr": "hrv", "hu": "hun", "id": "ind",
    "is": "ice", "it": "ita", "ja": "jpn", "ko": "kor", "lt": "lit", "lv": "lav",
    "ms": "may", "nl": "dut", "no": "nor", "pl": "pol", "pt": "por", "ro": "rum",
    "ru": "rus", "sk": "slo", "sl": "slv", "sr": "srp", "sv": "swe", "th": "tha",
    "tr": "tur", "uk": "ukr", "vi": "vie", "zh": "chi",
}


def lang3(code):
    return LANGS.get((code or "").lower(), "und")


@dataclasses.dataclass
class HDFrame:
    """Stands in for the Disc when fitting pictures: the 16:9 HD frame."""
    standard: str
    fps: tuple
    width: int = WIDTH
    height: int = HEIGHT
    aspect: str = "16:9"
    matrix: str = "bt709"

    @property
    def dar(self):
        return 16 / 9


# --------------------------------------------------------------------------
# planning and encoding
# --------------------------------------------------------------------------

def plan(items, capacity):
    """Highest video rate the titles may peak at so that they fit.

    items: (duration, audio bps) per title. Pictures are encoded at a
    constant quality and capped at this rate, so the disc is never
    overfilled. Returns {"max_bps", "estimated_bytes", "capacity", "warnings"}."""
    total = sum(d for d, _ in items)
    if total <= 0:
        raise ProjectError("titles have zero total duration")
    usable = capacity * (1 - DISC_SAFETY) * 8 - sum(d * a for d, a in items)
    fit = usable / total
    if fit < MIN_VIDEO_BPS:
        raise ProjectError(f"content does not fit: {total / 60:.1f} min would need a video "
                           f"bitrate of {max(fit, 0) / 1e6:.2f} Mbit/s (minimum "
                           f"{MIN_VIDEO_BPS / 1e6:.0f}). Use BD50 or shorter titles.")
    peak = int(min(MAX_VIDEO_BPS, fit))
    est = sum(d * (peak + a) for d, a in items) / 8 * (1 + DISC_SAFETY)
    return {"max_bps": peak, "estimated_bytes": int(min(est, capacity)), "capacity": capacity,
            "total_seconds": total, "warnings": []}


def audio_codec_args(title, k):
    """Encoder options for audio output stream k of a title."""
    if title.audio_passthrough:
        return [f"-c:a:{k}", "copy"]
    if title.audio_codec == "lpcm":
        return [f"-c:a:{k}", "pcm_bluray", f"-sample_fmt:a:{k}", "s16", f"-ar:a:{k}", "48000",
                f"-ac:a:{k}", "2"]
    return [f"-c:a:{k}", "ac3", f"-b:a:{k}", str(title.audio_bitrate), f"-ar:a:{k}", "48000",
            f"-ac:a:{k}", str(title.audio_channels)]


def key_times(chapters, fps):
    """Chapter starts snapped to frames: the pictures to make key frames."""
    num, den = fps
    frames = sorted({math.ceil(t * num / den - 1e-6) for t in chapters if t > 0})
    return [f * den / num for f in frames]


def video_args(title, disc, max_bps, fast):
    fps = title_fps(title, disc)
    if fps not in FORMATS:
        raise OncemoreError(f"title {title.id!r}: {fps[0]}/{fps[1]} fps has no Blu-ray format")
    return stream_video_args(fps, max_bps, fast, key_times(title.chapters, fps))


def stream_video_args(fps, max_bps, fast, keys=()):
    """x264 options for a Blu-ray video stream at `fps`; `keys`: times to make
    key frames (chapters, a menu's loop point)."""
    gop = round(fps[0] / fps[1])            # at most one second between key frames
    x264 = (f"bluray-compat=1:slices=4:aud=1:nal-hrd=vbr:keyint={gop}:min-keyint=1:"
            "force-cfr=1")
    if FORMATS[fps][0] == 4:
        x264 += ":fake-interlaced=1:pic-struct=1"
    args = ["-c:v", "libx264", "-preset", "ultrafast" if fast else "medium",
            "-crf", "24" if fast else "19", "-profile:v", "high", "-level", "4.1",
            "-maxrate", str(max_bps), "-bufsize", str(VBV_BUFFER), "-x264-params", x264,
            "-r", f"{fps[0]}/{fps[1]}", "-pix_fmt", "yuv420p", "-aspect", "16:9",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-forced-idr", "1"]
    if keys:
        args += ["-force_key_frames", ",".join(f"{t:.6f}" for t in keys)]
    return args


def encode_title(title, info, disc, max_bps, out_path, work, fast=False, on_progress=None,
                 probes=None, sups=()):
    """Encode one title to a Blu-ray transport stream (.m2ts); `sups` are its
    subtitle tracks as PGS streams (pgs.write_sup), muxed in as they are."""
    if not info.get("has_video"):
        raise OncemoreError(f"title {title.id!r}: {title.source} has no video stream")
    duration = info["duration"]
    hd = HDFrame(disc.standard, disc.fps)
    # film stays at 23.976; everything else becomes progressive frames
    mode = "pulldown" if title.video_mode == "pulldown" else "progressive"
    probes = dict(probes or {})
    probes.setdefault(title.source, info)
    # (the DVD LPCM framing does not apply: pcm_bluray frames itself)
    plain = dataclasses.replace(title, audio_codec="ac3")
    if title.clips:
        for c in title.clips:
            probes.setdefault(c.source, encode.probe(c.source))
        inputs, graph, labels = encode.clip_graph(plain, probes, hd, mode)
        maps = ["-filter_complex", graph]
        for lab in labels:
            maps += ["-map", lab]
        tracks = 1
    else:
        extra, agraph, alabels = encode.audio_graph(plain, probes)
        inputs = ["-i", title.source] + extra
        vf = encode.fit_filter(info, hd, mode=mode, ivtc=encode.is_ivtc(title))
        if title.audio_passthrough:
            sources = [title.source] + [extra[i + 1] for i in range(0, len(extra), 2)]
            maps = ["-map", "0:v:0", "-vf", vf]
            for tr in title.audio_tracks:
                maps += ["-map", f"{sources.index(tr.source)}:a:{tr.stream}"]
        else:
            maps = ["-filter_complex", f"[0:v:0]{vf}[v];{agraph}", "-map", "[v]"]
            for lab in alabels:
                maps += ["-map", lab]
        tracks = len(title.audio_tracks)
    acodec = []
    for k in range(tracks):
        acodec += audio_codec_args(title, k)
    pids = ["-streamid", f"0:{VIDEO_PID}"]
    for k in range(tracks):
        pids += ["-streamid", f"{k + 1}:{AUDIO_PID + k}"]
    n_inputs = inputs.count("-i")
    for k, sup in enumerate(sups):
        inputs = inputs + ["-i", sup]
        maps = maps + ["-map", f"{n_inputs + k}:s:0"]
        pids += ["-streamid", f"{1 + tracks + k}:{PG_PID + k}"]
    if sups:
        acodec += ["-c:s", "copy"]
    encode.run_ffmpeg(inputs + maps + video_args(title, disc, max_bps, fast) + acodec + pids +
                      ["-t", f"{duration:.3f}", "-f", "mpegts", "-mpegts_m2ts_mode", "1",
                       "-mpegts_pmt_start_pid", str(PMT_PID), out_path],
                      duration, os.path.join(work, "logs", f"title-{title.id}-bd.log"),
                      on_progress, cwd=work, what=f"ffmpeg (title {title.id})")
    return out_path


# --------------------------------------------------------------------------
# reading the transport stream back
# --------------------------------------------------------------------------

@dataclasses.dataclass
class ClipScan:
    packets: int          # 192-byte source packets
    first_pts: int        # 90 kHz, first picture shown
    end_pts: int          # 90 kHz, end of the last picture
    pcr_pid: int
    entries: list         # [(pts, spn, size in bytes)] of the key frames, in order


def _pts(b, i):
    return (((b[i] >> 1) & 7) << 30 | b[i + 1] << 22 | (b[i + 2] >> 1) << 15 |
            b[i + 3] << 7 | b[i + 4] >> 1)


def scan_m2ts(path, video_pid=VIDEO_PID):
    """Where the key frames of a .m2ts are (for the entry-point map) and the
    span of its pictures. Every picture is one PES packet (ffmpeg); key
    frames carry the random-access flag."""
    entries = []
    pts_all = []
    pcr_pid = None
    spn = 0
    with open(path, "rb") as f:
        while True:
            buf = f.read(192 * 8192)
            if not buf:
                break
            if len(buf) % 192:
                raise OncemoreError(f"{path} is not a BDAV stream (length is not 192 × n)")
            for off in range(0, len(buf), 192):
                p = off + 4
                b1 = buf[p + 1]
                if not b1 & 0x40:
                    continue
                if buf[p] != 0x47:
                    raise OncemoreError(f"{path}: lost sync at packet {spn + off // 192}")
                pid = (b1 & 0x1F) << 8 | buf[p + 2]
                if pid != video_pid:
                    continue
                afc = buf[p + 3] >> 4 & 3
                q = p + 4
                rai = False
                if afc & 2:
                    alen = buf[q]
                    if alen:
                        rai = bool(buf[q + 1] & 0x40)
                        if buf[q + 1] & 0x10:
                            pcr_pid = pid
                    q += 1 + alen
                if not afc & 1 or buf[q:q + 3] != b"\0\0\1" or not buf[q + 7] & 0x80:
                    continue
                pts = _pts(buf, q + 9)
                n = spn + off // 192
                if entries and entries[-1][2] is None:
                    entries[-1][2] = (n - entries[-1][1]) * 192
                pts_all.append(pts)
                if rai:
                    entries.append([pts, n, None])
            spn += len(buf) // 192
    if not pts_all or not entries:
        raise OncemoreError(f"{path}: no pictures with key frames found")
    if entries[-1][2] is None:
        entries[-1][2] = (spn - entries[-1][1]) * 192
    ordered = sorted(pts_all)
    step = ordered[1] - ordered[0] if len(ordered) > 1 else 3003
    return ClipScan(spn, ordered[0], ordered[-1] + step, pcr_pid or video_pid,
                    [tuple(e) for e in entries])


# --------------------------------------------------------------------------
# the navigation files
# --------------------------------------------------------------------------

def _u8(v):
    return struct.pack(">B", v)


def _u16(v):
    return struct.pack(">H", v)


def _u32(v):
    return struct.pack(">I", v)


def _pad(data, n):
    return data + b"\0" * (-len(data) % n)


def index_bdmv(title_objects, first_play, top_menu, video_format, frame_rate, interactive=()):
    """title_objects: the movie object of every title (title 1 first);
    interactive: the titles (1-based) that are menus."""
    app = _u32(34) + bytes([0, video_format << 4 | frame_rate]) + bytes(32)

    def hdmv(obj, playback_type):
        # playback_type 0 = movie, 1 = interactive
        return _u16(playback_type << 14) + _u16(obj) + _u32(0)

    body = _u32(1 << 30) + hdmv(first_play, 1) + _u32(1 << 30) + hdmv(top_menu, 1)
    body += _u16(len(title_objects))
    for n, obj in enumerate(title_objects, 1):
        body += _u32(1 << 30) + hdmv(obj, int(n in interactive))   # HDMV, access permitted
    index_start = 40 + len(app)
    return b"INDX" + VERSION + _u32(index_start) + _u32(0) + bytes(24) + app + \
        _u32(len(body)) + body


def _cmd(b0, b1, dst=0, src=0, b3=0, b2=0):
    """A 12-byte navigation command: operand count / group / sub-group,
    immediate flags / branch option, compare option, set option; operands."""
    return bytes([b0, b1, b2, b3]) + _u32(dst) + _u32(src)


def play_pl(playlist):
    """Play PlayList <playlist> (an immediate number)."""
    return _cmd(0x22, 0x80, playlist)


def set_subtitles(number):
    """Set Stream: subtitle (PG) track `number` shown, or 0 = none shown."""
    # Set group, SetSystem sub-group, two immediate operands, option 1 (Set Stream);
    # the first operand: PG stream number valid (0x8000), shown (0x4000)
    return _cmd(0x51, 0xC0, 0xC000 | number if number else 0, 0, 0x01)


def jump_title(title):
    """Jump Title <title>: 1..N, 0 = top menu."""
    return _cmd(0x21, 0x81, title)


def jump_title_reg(reg):
    """Jump Title to the number held in general register `reg`."""
    return _cmd(0x21, 0x01, reg)


def jump_object(obj):
    """Jump Object <obj> (a movie object number)."""
    return _cmd(0x21, 0x80, obj)


def play_pl_mark(playlist, mark):
    """Play PlayList <playlist> from mark <mark> (0-based)."""
    return _cmd(0x42, 0xC2, playlist, mark)


def goto(pc):
    """Goto command <pc> of the same object."""
    return _cmd(0x20, 0x81, pc)


def move(reg, value):
    """Move <value> into general register <reg>."""
    return _cmd(0x50, 0x40, reg, value, 0x01)


def set_button(button=None, reg=None):
    """Set Button Page: select button `button` (an id), or the one held in
    general register `reg`; the page stays."""
    # Set group, SetSystem sub-group, option 3; the operand's top bit: button valid
    if reg is not None:
        return _cmd(0x51, 0x40, 0x80000000 | reg, 0, 0x03)
    return _cmd(0x51, 0xC0, 0x80000000 | button, 0, 0x03)


def add(reg, value):
    """Add <value> to general register <reg>."""
    return _cmd(0x50, 0x40, reg, value, 0x03)


def if_at_least(reg, value):
    """Compare: the next command runs only if general register `reg` >= value."""
    return _cmd(0x48, 0x40, reg, value, b2=0x04)


def if_equal(reg, value):
    """Compare: the next command runs only if general register `reg` == value."""
    return _cmd(0x48, 0x40, reg, value, b2=0x02)


def if_not_equal(reg, value):
    """Compare: the next command runs only if general register `reg` != value."""
    return _cmd(0x48, 0x40, reg, value, b2=0x03)


def resume():
    """Resume the title the menu was called from."""
    return _cmd(0x01, 0x04)


def set_streams(audio=None, subtitle=None):
    """Set Stream: audio track `audio` (1-based) and/or subtitle track
    `subtitle` shown (0 = subtitles off)."""
    dst = 0
    if audio:
        dst |= 0x80000000 | audio << 16
    if subtitle is not None:
        dst |= (0xC000 | subtitle) if subtitle else 0
    return _cmd(0x51, 0xC0, dst, 0, 0x01)


def movie_objects(objects):
    """objects: lists of 12-byte navigation commands."""
    data = b""
    for cmds in objects:
        # resume_intention_flag set: a menu called during playback can resume it
        data += _u16(1 << 15) + _u16(len(cmds)) + b"".join(cmds)
    body = _u32(0) + _u16(len(objects)) + data
    return b"MOBJ" + VERSION + _u32(0) + bytes(28) + _u32(len(body)) + body


def _video_attr(video_format, frame_rate):
    return bytes([CODING_H264, video_format << 4 | frame_rate, 0, 0, 0])


def _audio_attr(track):
    coding, channels, lang = track
    fmt = 6 if channels > 2 else 3
    return bytes([coding, fmt << 4 | 1]) + lang.encode("ascii")


def _pg_attr(lang, coding=CODING_PG):
    return bytes([coding]) + lang.encode("ascii") + b"\0"


def mpls(items, marks):
    """A playlist. items: [(clip name, in, out, video_format, frame_rate,
    audio, pg, ig, still)] played one after the other, times in 45 kHz on
    each clip's time line, audio [(coding, channels, lang3)], pg [lang3]
    (subtitles), ig: the clip carries menu buttons, still: 2 holds the
    last picture (a still menu), (1, s) holds it for s seconds; marks:
    chapter marks as (item index, time)."""
    app = _u32(14) + bytes([0, 1]) + _u16(0) + bytes(8) + _u16(0)
    body = b""
    for clip, in_time, out_time, video_format, frame_rate, audio, pg, ig, still in items:
        stn = _u16(0) + bytes([1, len(audio), len(pg), int(ig), 0, 0, 0, 0]) + bytes(4)
        entry = _u8(1) + _u16(VIDEO_PID) + bytes(6)
        stn += _u8(len(entry)) + entry + _u8(5) + _video_attr(video_format, frame_rate)
        for k, tr in enumerate(audio):
            entry = _u8(1) + _u16(AUDIO_PID + k) + bytes(6)
            stn += _u8(len(entry)) + entry + _u8(5) + _audio_attr(tr)
        for k, lang in enumerate(pg):
            entry = _u8(1) + _u16(PG_PID + k) + bytes(6)
            stn += _u8(len(entry)) + entry + _u8(5) + _pg_attr(lang)
        if ig:
            entry = _u8(1) + _u16(IG_PID) + bytes(6)
            stn += _u8(len(entry)) + entry + _u8(5) + _pg_attr("und", CODING_IG)
        still_mode, still_time = still if isinstance(still, tuple) else (still, 0)
        # connection_condition 1: the clips are not seamless; STC id 0
        item = clip.encode("ascii") + b"M2TS" + _u16(1) + _u8(0) + _u32(in_time) + \
            _u32(out_time) + bytes(8) + _u8(0) + _u8(still_mode) + _u16(still_time) + \
            _u16(len(stn)) + stn
        body += _u16(len(item)) + item
    playlist = _u16(0) + _u16(len(items)) + _u16(0) + body
    playlist = _u32(len(playlist)) + playlist
    mark = _u16(len(marks))
    for ref, t in marks:
        mark += _u8(0) + _u8(1) + _u16(ref) + _u32(t) + _u16(0xFFFF) + _u32(0)
    mark = _u32(len(mark)) + mark
    list_pos = 40 + len(app)
    mark_pos = list_pos + len(playlist)
    return b"MPLS" + VERSION + _u32(list_pos) + _u32(mark_pos) + _u32(0) + bytes(20) + app + \
        playlist + mark


def ep_map(entries):
    """EP_map() of the video stream: a coarse entry whenever the upper PTS or
    packet-number bits change, a fine entry per key frame."""
    coarse, fine = [], []
    last = None
    for i, (pts, spn, size) in enumerate(entries):
        key = (pts >> 19, spn & 0xFFFE0000)
        if key != last:
            coarse.append((i, pts >> 19 & 0x3FFF, spn))
            last = key
        # I_end_position_offset: how many bytes the key picture takes, in steps
        end = next((k for k, lim in enumerate((131072, 262144, 393216, 589824, 917504,
                                               1310720), 1) if size < lim), 7)
        fine.append(end << 28 | (pts >> 9 & 0x7FF) << 17 | spn & 0x1FFFF)
    table = b"".join(_u32(ref << 14 | cpts) + _u32(cspn) for ref, cpts, cspn in coarse)
    one = _u32(4 + len(table)) + table + b"".join(_u32(v) for v in fine)
    # stream_PID, 10 reserved bits + EP_stream_type 1 (video), the coarse and
    # fine counts (16 + 18 bits), then where the stream's map starts
    counts = 1 << 34 | len(coarse) << 18 | len(fine)
    head_len = 2 + 2 + 6 + 4        # (the address counts from the start of EP_map)
    head = _u8(0) + _u8(1) + _u16(VIDEO_PID) + counts.to_bytes(6, "big") + _u32(head_len)
    return head + one


def clpi(scan, video_format, frame_rate, audio, pg=(), ig=False):
    """Clip information of one .m2ts: its streams, time span and EP map.
    audio: [(coding, channels, lang3)]; pg: [lang3]; ig: menu buttons."""
    ts_type = bytes([0x80]) + b"HDMV" + bytes(9) + bytes(16)
    info = _u16(0) + _u8(1) + _u8(1) + _u32(0) + _u32(TS_RATE) + _u32(scan.packets) + \
        bytes(128) + _u16(len(ts_type)) + ts_type
    info = _u32(len(info)) + info
    start, end = scan.first_pts // 2, scan.end_pts // 2
    seq = _u8(0) + _u8(1) + _u32(0) + _u8(1) + _u8(0) + _u16(scan.pcr_pid) + _u32(0) + \
        _u32(start) + _u32(end)
    seq = _u32(len(seq)) + seq
    isrc = b"0" * 12
    streams = _u16(VIDEO_PID)
    coding = bytes([CODING_H264, video_format << 4 | frame_rate, 3 << 4, 0, 0]) + isrc + bytes(4)
    streams += _u8(len(coding)) + coding
    for k, tr in enumerate(audio):
        coding = _audio_attr(tr) + isrc + bytes(4)
        streams += _u16(AUDIO_PID + k) + _u8(len(coding)) + coding
    for k, lang in enumerate(pg):
        coding = _pg_attr(lang) + isrc + bytes(4)
        streams += _u16(PG_PID + k) + _u8(len(coding)) + coding
    if ig:
        coding = _pg_attr("und", CODING_IG) + isrc + bytes(4)
        streams += _u16(IG_PID) + _u8(len(coding)) + coding
    prog = _u8(0) + _u8(1) + _u32(0) + _u16(PMT_PID) + \
        _u8(1 + len(audio) + len(pg) + int(ig)) + _u8(0) + streams
    prog = _u32(len(prog)) + prog
    cpi = _u16(1) + ep_map(scan.entries)          # 12 reserved bits, CPI_type 1 (EP map)
    cpi = _u32(len(cpi)) + cpi
    parts = [info, seq, prog, cpi, _u32(0)]       # (the last one: no clip marks)
    pos, offsets, body = 40, [], b""
    for part in parts:
        offsets.append(pos)
        part = _pad(part, 4)
        body += part
        pos += len(part)
    return b"HDMV" + VERSION + b"".join(_u32(o) for o in offsets[1:]) + _u32(0) + \
        bytes(12) + body


# --------------------------------------------------------------------------
# the disc
# --------------------------------------------------------------------------

DIRS = ["BDMV/PLAYLIST", "BDMV/CLIPINF", "BDMV/STREAM", "BDMV/AUXDATA", "BDMV/BDJO",
        "BDMV/JAR", "BDMV/META", "BDMV/BACKUP/PLAYLIST", "BDMV/BACKUP/CLIPINF",
        "BDMV/BACKUP/BDJO", "CERTIFICATE/BACKUP"]


@dataclasses.dataclass
class Piece:
    """An encoded title as the playlists see it."""
    clip: str             # clip name, e.g. "00001"
    video_format: int
    frame_rate: int
    audio: list           # [(coding, channels, lang3)]
    pg: list              # subtitle tracks [lang3]
    marks: list           # chapter starts, 45 kHz on the clip's time line
    end: int              # end of the clip, 45 kHz
    ig: bool = False      # a menu: the clip carries its buttons
    still: object = 0     # 2: hold the last picture (a still menu); (1, s): for s seconds

    def item(self, first=1, last=None):
        """PlayItem covering chapters first..last (1-based, inclusive)."""
        start = self.marks[first - 1]
        stop = self.marks[last] if last and last < len(self.marks) else self.end
        return (self.clip, start, stop, self.video_format, self.frame_rate, self.audio, self.pg,
                self.ig, self.still)


class Nav:
    """The disc's navigation: its Blu-ray titles (one per project title, one
    per project playlist, "play all" when something starts it, then one per
    menu), the movie objects that play them, and the commands an action
    (a button's, an end action, first play) turns into.

    Objects: one per Blu-ray title, in title order; then first play; then
    the top menu key; then one per (title, chapter) a menu button starts."""

    def __init__(self, project):
        self.project = project
        p = project
        titles = [("title", t.id, t.end_action) for t in p.titles]
        titles += [("playlist", x.id, x.end_action) for x in p.playlists]
        if p.uses_playall:
            titles.append(("playall", None, p.titles[-1].end_action))
        titles += [("menu", m.id, None) for m in p.menus]
        self.titles = titles
        self.numbers = {f"{k}:{i}" if i else k: n for n, (k, i, _) in enumerate(titles, 1)}
        chapters = []
        for a in p.actions():           # buttons, end actions, first play ...
            kind, tid, n = parse_action(a)
            if kind == "chapter" and (tid, n) not in chapters:
                chapters.append((tid, n))
        self.first_play = len(titles)
        self.top_menu = len(titles) + 1
        self.chapter_objects = {key: len(titles) + 2 + k for k, key in enumerate(chapters)}

    def menu_number(self, menu_id):
        return self.numbers.get(f"menu:{menu_id}")

    def go(self, action):
        """Commands that go where `action` says, or [] (stop, or nowhere)."""
        kind, ident, n = parse_action(action or "stop")
        if kind == "chapter":
            if n == 1:
                return [jump_title(self.numbers[f"title:{ident}"])]
            return [jump_object(self.chapter_objects[(ident, n)])]
        if kind == "lastmenu":
            return [jump_title_reg(LAST_MENU_REG)] if self.project.menus else []
        if kind == "resume":
            return [resume()]
        if kind == "menu" and n:
            # that button highlighted: the menu's object picks it up (objects)
            ids = [b.id for b in self.project.menu(ident).buttons]
            return [move(ENTRY_REG, ids.index(n)), jump_title(self.numbers[f"menu:{ident}"])]
        key = f"{kind}:{ident}" if ident else kind
        return [jump_title(self.numbers[key])] if key in self.numbers else []

    def button(self, b):
        """A menu button's commands: its streams, then its action."""
        kind, _, n = parse_action(b.action)
        cmds = []
        audio = n if kind == "audio" else b.audio
        sub = n if kind == "subtitle" else b.subtitle
        if audio or sub is not None:
            cmds.append(set_streams(audio, sub))
        if kind not in ("audio", "subtitle"):
            if b.override:
                # the title's object takes the override when it ends (_ends)
                cmds.append(move(OVERRIDE_REG, self.project.overrides.index(b.override) + 1))
            elif self.project.overrides and kind in ("title", "chapter", "playlist", "playall"):
                cmds.append(move(OVERRIDE_REG, 0))
            cmds += self.go(b.action)
        return cmds

    def _ends(self, end):
        """A title's commands after it played: an override a button set, else
        `end`. Overrides are objects of their own after the chapter ones."""
        p = self.project
        first = len(self.titles) + 2 + len(self.chapter_objects)
        out = []
        for k in range(1, len(p.overrides) + 1):
            out += [if_equal(OVERRIDE_REG, k), jump_object(first + k - 1)]
        return out + self.go(end)

    def _entry(self, menu):
        """For a menu that links open on a particular button: select that
        button, or else its default one, before it plays (its buttons then
        follow the selection; see bdmenu.ig_stream)."""
        if menu.id not in self.project.entry_buttons:
            return []
        ids = [b.id for b in menu.buttons]
        default = ids.index(menu.default_button) if menu.default_button else 0
        return [if_not_equal(ENTRY_REG, 0), set_button(reg=ENTRY_REG),
                if_equal(ENTRY_REG, 0), set_button(default), move(ENTRY_REG, 0)]

    def _start(self, title):
        """Subtitles as the title starts: its default track, or none."""
        if not title.subtitles:
            return []
        on = next((k for k, sub in enumerate(title.subtitles, 1) if sub.default), 0)
        return [set_subtitles(on)]

    def objects(self, menus=None):
        """All movie objects. menus: {menu id: (still, loop_mark)} for the
        menus' own objects (a still menu holds its picture; others play
        again from the loop point, mark 1, or from the start)."""
        p = self.project
        menus = menus or {}
        out = []
        for n, (kind, ident, end) in enumerate(self.titles, 1):
            if kind == "menu":
                still, loop_mark = menus.get(ident, (True, 0))
                m = p.menu(ident)
                cmds = self._entry(m) + [move(LAST_MENU_REG, n)]
                if m.loop is not None:
                    # played m.loop times (a still one holds its picture for its
                    # length each time), then its end action
                    cmds += [move(LOOP_REG, 1), play_pl(n)]
                    top = len(cmds)
                    end = self.go(m.end_action)
                    cmds += [if_at_least(LOOP_REG, m.loop), goto(top + 5), add(LOOP_REG, 1),
                             play_pl_mark(n, loop_mark), goto(top)] + end
                    out.append(cmds)
                    continue
                cmds.append(play_pl(n))
                if not still:
                    cmds += [play_pl_mark(n, loop_mark), goto(len(cmds))]
                out.append(cmds)
                continue
            first = p.title(ident) if kind == "title" else \
                p.title(p.playlist(ident).items[0].title_id) if kind == "playlist" \
                else p.titles[0]
            ends = self._ends(end) if kind == "title" else self.go(end)
            out.append(self._start(first) + [play_pl(n)] + ends)
        out.append(self.go(p.disc.first_play) or [jump_title(1)])
        top = p.disc.title_key or (f"menu:{p.menus[0].id}" if p.menus else None)
        out.append(self.go(top) or [jump_title(1)])
        for (tid, n), _ in sorted(self.chapter_objects.items(), key=lambda kv: kv[1]):
            t = p.title(tid)
            out.append(self._start(t) + [play_pl_mark(self.numbers[f"title:{tid}"], n - 1)] +
                       self._ends(t.end_action))
        for action in p.overrides:
            out.append([move(OVERRIDE_REG, 0)] + self.go(action))
        return out


def disc_titles(project):
    """The Blu-ray titles in order and {action: title number} (see Nav)."""
    nav = Nav(project)
    return nav.titles, nav.numbers


def playlist_items(project, kind, ident, pieces):
    """(items, marks) of one Blu-ray title's playlist."""
    if kind == "title":
        parts = [(pieces[ident], 1, None)]
    elif kind == "playlist":
        parts = [(pieces[it.title_id], it.first, it.last)
                 for it in project.playlist(ident).items]
    elif kind == "menu":
        parts = [(pieces[f"menu:{ident}"], 1, None)]
    else:
        parts = [(pieces[t.id], 1, None) for t in project.titles]
    items, marks = [], []
    for k, (piece, first, last) in enumerate(parts):
        item = piece.item(first, last)
        items.append(item)
        marks += [(k, m) for m in piece.marks if item[1] <= m < item[2]]
    return items, marks


def navigation(project, menus=None):
    """(objects, first play object, top menu object) (see Nav)."""
    nav = Nav(project)
    return nav.objects(menus), nav.first_play, nav.top_menu


def audio_streams(title):
    if title.audio_codec == "lpcm" and not title.audio_passthrough:
        coding, channels = CODING_LPCM, 2
    else:
        coding, channels = CODING_AC3, title.audio_channels
    n = 1 if title.clips else len(title.audio_tracks)
    return [(coding, channels, lang3(title.audio_tracks[k].lang if title.audio_tracks else None))
            for k in range(n)]


def _write(out_dir, rel, data):
    for base in ("BDMV", os.path.join("BDMV", "BACKUP")):
        with open(os.path.join(out_dir, base, rel), "wb") as f:
            f.write(data)


def write_bdmv(project, clips, out_dir, menus=None):
    """Write the BDMV folder. clips: {title id: encoded .m2ts}; menus:
    {menu id: {"m2ts", "still", "loop_point"}} (bdmenu.encode_menu). The
    streams are moved into BDMV/STREAM."""
    menus = menus or {}
    for d in DIRS:
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)
    pieces = {}
    for n, t in enumerate(project.titles, 1):
        name = f"{n:05d}"
        scan = scan_m2ts(clips[t.id])
        video_format, frame_rate = FORMATS[title_fps(t, project.disc)]
        audio = audio_streams(t)
        pg = [lang3(sub.lang) for sub in t.subtitles]
        pieces[t.id] = Piece(name, video_format, frame_rate, audio, pg,
                             chapter_marks(t, scan), scan.end_pts // 2)
        _write(out_dir, os.path.join("CLIPINF", f"{name}.clpi"),
               clpi(scan, video_format, frame_rate, audio, pg))
        dest = os.path.join(out_dir, "BDMV", "STREAM", f"{name}.m2ts")
        if os.path.abspath(clips[t.id]) != os.path.abspath(dest):
            shutil.move(clips[t.id], dest)
    loops = {}
    for k, m in enumerate(project.menus, len(project.titles) + 1):
        name, info = f"{k:05d}", menus[m.id]
        scan = scan_m2ts(info["m2ts"])
        video_format, frame_rate = FORMATS[project.disc.fps]
        audio = [(CODING_AC3, 2, "und")] if info.get("audio") else []
        marks = [scan.first_pts // 2]
        if info.get("loop_point"):
            # the second time round the menu plays from its loop point
            want = scan.first_pts + round(info["loop_point"] * 90000)
            marks.append(min((e[0] for e in scan.entries), key=lambda x: abs(x - want)) // 2)
        pieces[f"menu:{m.id}"] = Piece(name, video_format, frame_rate, audio, [], marks,
                                       scan.end_pts // 2, ig=True,
                                       still=((1, info["still_time"]) if info.get("still_time")
                                              else 2) if info["still"] else 0)
        loops[m.id] = (info["still"], len(marks) - 1)
        _write(out_dir, os.path.join("CLIPINF", f"{name}.clpi"),
               clpi(scan, video_format, frame_rate, audio, (), ig=True))
        shutil.move(info["m2ts"], os.path.join(out_dir, "BDMV", "STREAM", f"{name}.m2ts"))
    nav = Nav(project)
    titles = nav.titles
    for n, (kind, ident, _) in enumerate(titles, 1):
        items, marks = playlist_items(project, kind, ident, pieces)
        _write(out_dir, os.path.join("PLAYLIST", f"{n:05d}.mpls"), mpls(items, marks))
    objects, first, top = nav.objects(loops), nav.first_play, nav.top_menu
    first_piece = pieces[project.titles[0].id]
    interactive = {n for n, (kind, _, _) in enumerate(titles, 1) if kind == "menu"}
    _write(out_dir, "index.bdmv", index_bdmv(list(range(len(titles))), first, top,
                                             first_piece.video_format, first_piece.frame_rate,
                                             interactive))
    _write(out_dir, "MovieObject.bdmv", movie_objects(objects))
    return {"titles": len(titles), "playlists": [f"{n:05d}.mpls" for n in range(1, len(titles) + 1)]}


def chapter_marks(title, scan):
    """Chapter marks (45 kHz): every chapter on the key frame made for it,
    the first one at the start of the clip."""
    marks = [scan.first_pts // 2]
    keys = [pts for pts, _, _ in scan.entries]
    for t in sorted(c for c in title.chapters if c > 0):
        want = scan.first_pts + round(t * 90000)
        near = min(keys, key=lambda k: abs(k - want))
        if near // 2 > marks[-1]:
            marks.append(near // 2)
    return marks
