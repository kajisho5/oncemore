"""Blu-ray output: a BDMV folder of HD titles with chapters (DECISIONS §53).

ffmpeg encodes every title (H.264 with x264's Blu-ray settings, AC-3 or
LPCM sound) straight into a BDAV transport stream (.m2ts); that, the bitrate
plan, 720p and copied H.264 are here. The files a player navigates by
(index.bdmv, MovieObject.bdmv, the playlists and the clip information) and
the navigation itself are bdmvkit's (DECISIONS §108): `program` turns
the project into a bdmvkit Program, which bdmvkit writes.

The tests read every disc back with libbluray.
"""

import dataclasses
import os
import subprocess

from . import encode, tools
from ._vendor.bdmvkit import m2ts as _bd_m2ts, nav as _nav, program as _program
from ._vendor.bdmvkit.errors import BdmvError
from ._vendor.bdmvkit.formats import (AUDIO_PID, CODING_AC3, CODING_DTS, CODING_LPCM, FORMATS,
                                      FORMATS_720, FRAMES, HEIGHT, IG_PID, MAX_VIDEO_BPS, PG_PID,
                                      PMT_PID, VBV_BUFFER, VIDEO_PID, WIDTH, lang3)
from ._vendor.bdmvkit.nav import parts_items
from .errors import OncemoreError, ProjectError
from .project import frame_at, title_fps

# (build, bdmenu and the tests use these from here)
from ._vendor.bdmvkit.formats import CODING_H264  # noqa: F401
from ._vendor.bdmvkit.hdmv import (  # noqa: F401
    add, goto, if_at_least, jump_title, movie_objects, play_pl, popup_off, rnd, set_streams,
    set_subtitles)
from ._vendor.bdmvkit.nav import COUNT_REG, PICK_REG, Piece  # noqa: F401
from ._vendor.bdmvkit.playlist import mpls  # noqa: F401

CAPACITY = {"BD25": 25_025_314_816, "BD50": 50_050_629_632}
MIN_VIDEO_BPS = 4_000_000      # below this an HD picture falls apart
DISC_SAFETY = 0.03             # transport-stream overhead and some free space


# disc.bluray.video "720": 1280 x 720 progressive, at twice the disc's rate so
# that 50 / 59.94 frames a second stay as they are (film stays 23.976); the
# codes (FORMATS_720) and sizes (FRAMES) are bdmvkit's


def frame_size(disc):
    """(width, height) of the disc's Blu-ray picture."""
    return FRAMES[getattr(disc, "bluray_video", "1080")]


def bd_fps(fps, disc):
    """The rate a picture at `fps` (the disc's or a film title's) goes on the
    Blu-ray at: 720p doubles 25 and 29.97 (50 / 59.94 progressive)."""
    if getattr(disc, "bluray_video", "1080") == "720" and fps in ((25, 1), (30000, 1001)):
        return (2 * fps[0], fps[1])
    return fps


def bd_format(fps, disc):
    """(video_format, frame_rate) codes of a picture at `fps` (before bd_fps)."""
    table = FORMATS_720 if getattr(disc, "bluray_video", "1080") == "720" else FORMATS
    rate = bd_fps(fps, disc)
    if rate not in table:
        raise OncemoreError(f"{rate[0]}/{rate[1]} fps has no Blu-ray format")
    return table[rate]


def interlaced_format(fps, disc):
    """Whether pictures at `fps` go on the disc as 1080i (fields)."""
    return bd_format(fps, disc)[0] == 4


def hd_frame(disc, fps=None):
    """The HD picture of the disc's Blu-ray (an HDFrame) for pictures at `fps`."""
    w, h = frame_size(disc)
    return HDFrame(disc.standard, bd_fps(fps or disc.fps, disc), w, h)


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

    items: (duration, audio bps) per title, or (duration, audio bps, video
    bps) for a picture used as it is (its own rate). Pictures are encoded at
    a constant quality and capped at this rate, so the disc is never
    overfilled. Returns {"max_bps", "estimated_bytes", "capacity", "warnings"}."""
    items = [(d, a, rest[0] if rest else None) for d, a, *rest in items]
    if sum(d for d, _, _ in items) <= 0:
        raise ProjectError("titles have zero total duration")
    total = sum(d for d, _, v in items if v is None)
    usable = capacity * (1 - DISC_SAFETY) * 8 - sum(d * (a + (v or 0)) for d, a, v in items)
    fit = usable / total if total else (MAX_VIDEO_BPS if usable >= 0 else -1)
    if fit < MIN_VIDEO_BPS:
        raise ProjectError(f"content does not fit: {total / 60:.1f} min would need a video "
                           f"bitrate of {max(fit, 0) / 1e6:.2f} Mbit/s (minimum "
                           f"{MIN_VIDEO_BPS / 1e6:.0f}). Use BD50 or shorter titles.")
    peak = int(min(MAX_VIDEO_BPS, fit))
    est = sum(d * ((peak if v is None else v) + a) for d, a, v in items) / 8 * (1 + DISC_SAFETY)
    # the bit budget: each title at most (pictures are encoded at a constant
    # quality, up to the peak rate)
    titles = [int(d * ((peak if v is None else v) + a) / 8 * (1 + DISC_SAFETY))
              for d, a, v in items]
    return {"max_bps": peak, "estimated_bytes": int(min(est, capacity)), "capacity": capacity,
            "total_seconds": total, "warnings": [],
            "budget": {"titles": titles, "menus": 0, "other": 0}}


# --------------------------------------------------------------------------
# a source's H.264 picture used as it is
# --------------------------------------------------------------------------

class _Bits:
    """Reads an H.264 parameter set (emulation prevention bytes removed)."""

    def __init__(self, data):
        self.data, self.pos = data, 0

    def u(self, n):
        v = 0
        for _ in range(n):
            byte = self.data[self.pos >> 3] if self.pos >> 3 < len(self.data) else 0
            v = v << 1 | (byte >> (7 - (self.pos & 7))) & 1
            self.pos += 1
        return v

    def ue(self):
        zeros = 0
        while not self.u(1):
            zeros += 1
            if zeros > 31:
                raise ValueError("bad exp-Golomb code")
        return (1 << zeros) - 1 + self.u(zeros)

    def se(self):
        k = self.ue()
        return (k + 1) // 2 if k & 1 else -(k // 2)


HIGH_PROFILES = (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135)


def sps_frame_mbs_only(sps):
    """frame_mbs_only_flag of an H.264 sequence parameter set (the NAL unit,
    header byte included): 0 when the stream may hold fields, as a 1080i
    Blu-ray stream does (fields, or progressive frames coded as such)."""
    rbsp = sps[1:].replace(b"\0\0\3", b"\0\0")
    b = _Bits(rbsp)
    profile = b.u(8)
    b.u(16)                                  # constraint flags, level
    b.ue()                                   # seq_parameter_set_id
    if profile in HIGH_PROFILES:
        if b.ue() == 3:                      # chroma_format_idc
            b.u(1)
        b.ue(), b.ue()                       # bit depths
        b.u(1)
        if b.u(1):                           # seq_scaling_matrix_present_flag
            for k in range(8):
                if b.u(1):
                    last = nxt = 8
                    for _ in range(16 if k < 6 else 64):
                        if nxt:
                            nxt = (last + b.se()) % 256
                        last = nxt or last
    b.ue()                                   # log2_max_frame_num_minus4
    poc = b.ue()
    if poc == 0:
        b.ue()
    elif poc == 1:
        b.u(1), b.se(), b.se()
        for _ in range(b.ue()):
            b.se()
    b.ue(), b.u(1)                           # max_num_ref_frames, gaps allowed
    b.ue(), b.ue()                           # picture size in macroblocks
    return b.u(1)


def coded_for_fields(path):
    """True when the H.264 video of `path` may hold fields (see
    sps_frame_mbs_only), False when it is frames only, None when it cannot
    be read."""
    cmd = [tools.find("ffmpeg"), "-v", "error", "-i", path, "-map", "0:v:0", "-c:v", "copy",
           "-bsf:v", "h264_mp4toannexb", "-frames:v", "1", "-f", "h264", "-"]
    try:
        data = subprocess.run(cmd, capture_output=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        return None
    for nal in data.replace(b"\0\0\0\1", b"\0\0\1").split(b"\0\0\1")[1:]:
        if nal and nal[0] & 0x1F == 7:
            try:
                return not sps_frame_mbs_only(nal)
            except (ValueError, IndexError):
                return None
    return None


# A picture used as it is gets its parameter sets where a Blu-ray stream has
# them: an MP4 / MKV source keeps them aside (and its SEI in the pictures),
# and the plain Annex B conversion puts them after the SEI, even before the
# delimiter. So the delimiters are dropped, the parameter sets put first in
# every key picture, and the muxer starts each picture with a new delimiter:
# AUD, SPS, PPS, SEI ..., slices (DECISIONS §77).
COPY_BSF = "h264_mp4toannexb,filter_units=remove_types=9,dump_extra=freq=keyframe"


def copy_compliance(info, fps, disc=None):
    """Why the picture of `info` (probe, with "gop" from encode.longest_gop
    and "fields" from coded_for_fields) cannot go on a Blu-ray as it is, at
    the title's rate `fps` (an empty list when it can): H.264 High or Main
    profile up to level 4.1, 4:2:0, the disc's frame (1920x1080 square pixels
    or 1440x1080 at 4:3 pixels, as AVCHD cameras record; 1280x720 for a 720
    disc), one of the rates oncemore writes (23.976 progressive; 25 and 29.97
    as 1080i, coded for fields; 50 and 59.94 for 720p), a key frame at least
    every second, at most 40 Mbit/s."""
    out = []
    if info.get("codec") != "h264":
        return [f"the video is {info.get('codec')}, not H.264"]
    if info.get("profile") not in ("High", "Main"):
        out.append(f"the H.264 profile is {info.get('profile')}, not High or Main")
    if info.get("level", 0) > 41:
        out.append(f"the H.264 level is {info['level'] / 10:.1f} (at most 4.1)")
    if info.get("pix_fmt") and info["pix_fmt"] != "yuv420p":
        out.append(f"the picture is {info['pix_fmt']}, not 4:2:0 (yuv420p)")
    w, h = frame_size(disc)
    size, sar = (info.get("width"), info.get("height")), float(info.get("sar") or 1)
    if not ((size == (w, h) and sar == 1) or (h == 1080 and size == (1440, 1080) and
                                             abs(sar - 4 / 3) < 0.01)):
        out.append(f"the frame is {size[0]}x{size[1]}, not {w}x{h} with square pixels" +
                   (" or 1440x1080 with 4:3 pixels" if h == 1080 else ""))
    num, den = rate = bd_fps(fps, disc)
    src = float(info.get("fps") or 0)
    table = FORMATS_720 if h == 720 else FORMATS
    if rate not in table or abs(src - num / den) > 0.01:
        out.append(f"the frame rate is {src:.3f}, not {num / den:.3f}")
    elif table[rate][0] == 4 and info.get("fields") is not True:
        out.append(f"{num / den:.3f} fps goes on a Blu-ray as 1080i, and the video is not "
                   "coded for fields")
    gop = info.get("gop")
    if not gop:
        out.append("its key frames cannot be found")
    elif gop > round(num / den):
        out.append(f"a group of pictures is {gop} frames long (a key frame at least every "
                   "second)")
    vbps = info.get("video_bit_rate") or max(
        0, (info.get("bit_rate") or 0) - sum(a.get("bit_rate") or 0 for a in info.get("audio", [])))
    if vbps > MAX_VIDEO_BPS:
        out.append(f"the video bitrate is {vbps / 1e6:.1f} Mbit/s (at most 40)")
    return out


def audio_codec_args(title, k):
    """Encoder options for audio output stream k of a title."""
    if title.audio_passthrough:
        return [f"-c:a:{k}", "copy"] + ([f"-bsf:a:{k}", "dca_core"] if title.audio_codec == "dts"
                                        else [])
    if title.audio_codec == "lpcm":
        return [f"-c:a:{k}", "pcm_bluray", f"-sample_fmt:a:{k}", "s16", f"-ar:a:{k}", "48000",
                f"-ac:a:{k}", "2"]
    return [f"-c:a:{k}", "ac3", f"-b:a:{k}", str(title.audio_bitrate), f"-ar:a:{k}", "48000",
            f"-ac:a:{k}", str(title.audio_channels)]


def key_times(chapters, fps):
    """Chapter starts snapped to frames: the pictures to make key frames."""
    num, den = fps
    frames = sorted({frame_at(t, fps) for t in chapters if t > 0})
    return [f * den / num for f in frames]


def video_args(title, disc, max_bps, fast):
    fps = title_fps(title, disc)
    try:
        bd_format(fps, disc)
    except OncemoreError as e:
        raise OncemoreError(f"title {title.id!r}: {e}") from None
    rate = bd_fps(fps, disc)
    return stream_video_args(fps, max_bps, fast, key_times(title.chapters, rate), disc)


def stream_video_args(fps, max_bps, fast, keys=(), disc=None):
    """x264 options for a Blu-ray video stream of pictures at `fps` (the disc's
    or a film title's; a 720 disc doubles 25 and 29.97); `keys`: times to make
    key frames (chapters, a menu's loop point)."""
    interlaced = interlaced_format(fps, disc)
    fps = bd_fps(fps, disc)
    gop = round(fps[0] / fps[1])            # at most one second between key frames
    x264 = (f"bluray-compat=1:slices=4:aud=1:nal-hrd=vbr:keyint={gop}:min-keyint=1:"
            "force-cfr=1")
    if interlaced:
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
                 probes=None, sups=(), popup=None):
    """Encode one title to a Blu-ray transport stream (.m2ts); `sups` are its
    subtitle tracks as PGS streams (pgs.write_sup), muxed in as they are;
    `popup` its pop-up menu as an IG stream (bdmenu.popup_stream; the caller
    marks it Interactive Graphics in the PMT, bdmenu.patch_ig_stream_type)."""
    if not info.get("has_video"):
        raise OncemoreError(f"title {title.id!r}: {title.source} has no video stream")
    duration = info["duration"]
    hd = hd_frame(disc)
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
        vin = "0:v:0"
        if "still" in info:
            # sound only: the picture comes from its own input, after the sound's
            inputs += encode.still_input(info, hd.fps, duration, (hd.width, hd.height))
            vin = f"{inputs.count('-i') - 1}:v:0"
        if title.audio_passthrough:
            sources = [title.source] + [extra[i + 1] for i in range(0, len(extra), 2)]
            maps = ["-map", vin] + ([] if title.bd_copy else ["-vf", vf])
            for tr in title.audio_tracks:
                maps += ["-map", f"{sources.index(tr.source)}:a:{tr.stream}"]
        elif title.bd_copy:
            maps = ["-filter_complex", agraph, "-map", vin]
            for lab in alabels:
                maps += ["-map", lab]
        else:
            maps = ["-filter_complex", f"[{vin}]{vf}[v];{agraph}", "-map", "[v]"]
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
    if popup:
        n = inputs.count("-i")
        inputs = inputs + ["-f", "sup", "-i", popup]
        maps = maps + ["-map", f"{n}:0"]
        pids += ["-streamid", f"{1 + tracks + len(sups)}:{IG_PID}"]
    if sups or popup:
        acodec += ["-c:s", "copy"]
    video = ["-c:v", "copy", "-bsf:v", COPY_BSF] if title.bd_copy else \
        video_args(title, disc, max_bps, fast)
    encode.run_ffmpeg(inputs + maps + video + acodec + pids +
                      ["-t", f"{duration:.3f}", "-f", "mpegts", "-mpegts_m2ts_mode", "1",
                       "-mpegts_pmt_start_pid", str(PMT_PID), out_path],
                      duration, os.path.join(work, "logs", f"title-{title.id}-bd.log"),
                      on_progress, cwd=work, what=f"ffmpeg (title {title.id})")
    return out_path


def encode_transition(path, info, disc, max_bps, out_path, work, fast=False, on_progress=None):
    """A link transition as a clip of its own: the HD picture and its sound
    (or silence) in AC-3, like a menu's."""
    duration = info["duration"]
    vf = encode.fit_filter(info, hd_frame(disc))
    graph = f"[0:v:0]{vf}[v];" + ("[0:a:0]aresample=48000,apad[a]" if info.get("has_audio")
                                   else "anullsrc=channel_layout=stereo:sample_rate=48000[a]")
    encode.run_ffmpeg(["-i", path, "-filter_complex", graph, "-map", "[v]", "-map", "[a]"] +
                      stream_video_args(disc.fps, max_bps, fast, disc=disc) +
                      ["-c:a", "ac3", "-b:a", "192000", "-ar", "48000", "-ac", "2",
                       "-streamid", f"0:{VIDEO_PID}", "-streamid", f"1:{AUDIO_PID}",
                       "-t", f"{duration:.3f}", "-f", "mpegts", "-mpegts_m2ts_mode", "1",
                       "-mpegts_pmt_start_pid", str(PMT_PID), out_path],
                      duration, os.path.join(work, "logs",
                                             f"transition-{os.path.basename(out_path)}.log"),
                      on_progress, cwd=work, what=f"ffmpeg (transition {os.path.basename(path)})")
    return out_path


# --------------------------------------------------------------------------
# the disc: the project as a bdmvkit Program
# --------------------------------------------------------------------------

def audio_streams(title):
    if title.audio_codec == "lpcm" and not title.audio_passthrough:
        coding, channels = CODING_LPCM, 2
    elif title.audio_codec == "dts":
        coding, channels = CODING_DTS, title.audio_channels
    else:
        coding, channels = CODING_AC3, title.audio_channels
    n = 1 if title.clips else len(title.audio_tracks)
    return [(coding, channels, lang3(title.audio_tracks[k].lang if title.audio_tracks else None))
            for k in range(n)]


def scan_m2ts(path, video_pid=VIDEO_PID):
    """The key frames and the times of a clip (bdmvkit's scan)."""
    try:
        return _bd_m2ts.scan_m2ts(path, video_pid)
    except BdmvError as e:
        raise OncemoreError(e.message) from e


def program(project, clips=None, menus=None, popups=(), transitions=None):
    """The project as a bdmvkit Program. clips: {title id: encoded .m2ts};
    menus: {menu id: {"m2ts", "still", "still_time", "loop_point", "audio"}}
    (bdmenu.encode_menu); popups: the ids of the titles whose clip carries a
    pop-up menu; transitions: {link transition video: encoded .m2ts}. Without
    them it is the navigation alone (the commands of buttons, the objects)."""
    clips, menus, disc = clips or {}, menus or {}, project.disc
    titles = []
    for t in project.titles:
        titles.append(_program.Title(
            t.id, clips.get(t.id), title_fps(t, disc), list(t.chapters),
            [_program.Audio(coding, channels, lang,
                            k < len(t.audio_tracks) and bool(t.audio_tracks[k].default))
             for k, (coding, channels, lang) in enumerate(audio_streams(t))],
            [_program.Subtitle(lang3(s.lang), bool(s.default)) for s in t.subtitles],
            t.end_action, list(t.prohibit), popup=t.id in popups,
            hold=bool(t.slideshow and t.slideshow.advance == "manual")))
    out_menus = []
    for m in project.menus:
        info = menus.get(m.id, {})
        out_menus.append(_program.Menu(
            m.id, info.get("m2ts"), list(m.buttons), default=m.default_button,
            still=info.get("still", True), still_time=info.get("still_time"),
            loop_point=info.get("loop_point"), loop=m.loop, end=m.end_action,
            music=bool(info.get("audio")), prohibit=list(m.prohibit)))
    playlists = [_program.Playlist(x.id, [_program.PlaylistItem(it.title_id, it.first, it.last)
                                          for it in x.items], x.order, x.end_action)
                 for x in project.playlists]
    return _program.Program(titles, playlists, out_menus, disc.first_play, disc.title_key,
                            fps=disc.fps, video=getattr(disc, "bluray_video", "1080"),
                            transitions=dict(transitions or {}))


def Nav(project):
    """The disc's navigation (bdmvkit's nav.Navigation): its Blu-ray titles,
    the commands of every action and button, the movie objects."""
    return _nav.Navigation(program(project))


def disc_titles(project):
    """The Blu-ray titles in order and {action: title number}."""
    nav = Nav(project)
    return nav.titles, nav.numbers


def navigation(project, menus=None):
    """(objects, first play object, top menu object)."""
    nav = Nav(project)
    return nav.objects(menus), nav.first_play, nav.top_menu


def playlist_items(project, kind, ident, pieces):
    """(items, marks) of one Blu-ray title's playlist."""
    nav = Nav(project)
    return parts_items(_nav._parts(nav.program, nav, kind, ident, pieces))


def write_bdmv(project, clips, out_dir, menus=None, popups=(), transitions=None):
    """Write the BDMV folder (bdmvkit's nav.write_program); see `program`.
    The streams are moved into BDMV/STREAM."""
    try:
        out = _nav.write_program(program(project, clips, menus, popups, transitions), out_dir)
    except BdmvError as e:
        raise OncemoreError(e.message) from e
    return {"titles": out["titles"], "playlists": out["playlists"]}
