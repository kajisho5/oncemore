"""The disc for the web: a folder a browser plays as the disc does.

The menus are pictures (or videos, for motion menus and menus with sound)
with their buttons where they are on the disc and their highlights as
drawn there; the titles are MP4 (H.264 and AAC, 720 lines) with their
chapters and subtitles (WebVTT). A small player (webplayer/) follows the
disc's links: buttons and their arrows, end actions, play all, playlists,
the Menu and Title keys, menu time-outs and link transitions. It opens
from the folder itself (index.html, no server) or from any web server.

What a browser cannot do the way a disc does: one sound track per title
(the first), no DVD subpicture colours (subtitles are WebVTT text; picture
subtitles are left out), no buttons over a title.
"""

import dataclasses
import json
import os
import shutil

from . import encode, tools
from .menu import MenuBuilder, display_width, link_font
from .project import FILM_FPS

PLAYER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webplayer")
PLAYER_FILES = ("index.html", "player.js", "player.css")
HEIGHT = 720
AUDIO = ["-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "48000"]


@dataclasses.dataclass
class WebFrame:
    """Stands in for the Disc when fitting pictures: square pixels, 720 lines."""
    standard: str
    fps: tuple
    width: int
    height: int
    aspect: str
    matrix: str = "bt709"

    @property
    def dar(self):
        a, b = self.aspect.split(":")
        return int(a) / int(b)


def frame_for(disc, aspect=None):
    aspect = aspect or disc.aspect
    a, b = aspect.split(":")
    return WebFrame(disc.standard, disc.fps, round(HEIGHT * int(a) / int(b) / 2) * 2, HEIGHT,
                    aspect)


def video_args(fast):
    return ["-c:v", "libx264", "-preset", "ultrafast" if fast else "medium",
            "-crf", "26" if fast else "21", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"]


def encode_title(title, info, disc, out, work, fast=False, probes=None, on_progress=None):
    """A title as an MP4: its picture in square pixels, 720 lines, and its
    first sound track in stereo AAC."""
    frame = frame_for(disc, title.aspect)
    mode = "pulldown" if title.video_mode == "pulldown" else "progressive"
    if mode == "pulldown":
        frame = dataclasses.replace(frame, fps=FILM_FPS)
    duration = info["duration"]
    probes = dict(probes or {})
    probes.setdefault(title.source, info)
    plain = dataclasses.replace(title, audio_codec="ac3", audio_channels=2,
                                audio_tracks=title.audio_tracks[:1])
    if title.clips:
        for c in title.clips:
            probes.setdefault(c.source, encode.probe(c.source))
        inputs, graph, labels = encode.clip_graph(plain, probes, frame, mode)
        maps = ["-filter_complex", graph] + [x for lab in labels for x in ("-map", lab)]
    else:
        extra, agraph, alabels = encode.audio_graph(plain, probes)
        inputs = ["-i", title.source] + extra
        vin = "0:v:0"
        if "still" in info:
            inputs += encode.still_input(info, frame.fps, duration, (frame.width, frame.height))
            vin = f"{inputs.count('-i') - 1}:v:0"
        vf = encode.fit_filter(info, frame, mode=mode, ivtc=encode.is_ivtc(title))
        maps = ["-filter_complex", f"[{vin}]{vf},setsar=1,format=yuv420p[v];{agraph}",
                "-map", "[v]", "-map", alabels[0]]
    encode.run_ffmpeg(inputs + maps + video_args(fast) + AUDIO + ["-t", f"{duration:.3f}", out],
                      duration, os.path.join(work, "logs", f"web-title-{title.id}.log"),
                      on_progress, cwd=work, what=f"ffmpeg (title {title.id} for the web)")
    return out


def encode_clip(path, info, disc, out, work, fast=False):
    """A link transition: its picture and sound (or silence)."""
    frame = frame_for(disc)
    vf = encode.fit_filter(info, frame)
    sound = "[0:a:0]aresample=48000,apad[a]" if info.get("has_audio") else \
        "anullsrc=channel_layout=stereo:sample_rate=48000[a]"
    encode.run_ffmpeg(["-i", path, "-filter_complex", f"[0:v:0]{vf},setsar=1,format=yuv420p[v];"
                       f"{sound}", "-map", "[v]", "-map", "[a]"] + video_args(fast) + AUDIO +
                      ["-t", f"{info['duration']:.3f}", out], info["duration"],
                      os.path.join(work, "logs", f"web-{os.path.basename(out)}.log"), cwd=work,
                      what=f"ffmpeg (transition {os.path.basename(path)} for the web)")
    return out


def _vtt_time(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def to_vtt(cues, position="bottom"):
    """Text cues as WebVTT (picture cues are left out)."""
    out = ["WEBVTT", ""]
    for c in cues:
        if not c.lines:
            continue
        top = (c.position or position) == "top"
        out.append(f"{_vtt_time(c.start)} --> {_vtt_time(c.end)}" + (" line:0" if top else ""))
        out += [line.replace("-->", "->") for line in c.lines] + [""]
    return "\n".join(out) + "\n"


def chapters_vtt(title, duration):
    out = ["WEBVTT", ""]
    starts = list(title.chapters) + [duration]
    for k, (a, b) in enumerate(zip(starts, starts[1:]), 1):
        name = (title.chapter_names[k - 1] if k - 1 < len(title.chapter_names) else None) \
            or f"Chapter {k}"
        out += [f"{_vtt_time(a)} --> {_vtt_time(b)}", name, ""]
    return "\n".join(out) + "\n"


class MenuRenderer:
    """Menus as the player shows them: square-pixel pictures (or videos) and
    the button highlights on a transparent picture of the same size."""

    def __init__(self, project, work, out_dir, font, fast, reporter):
        self.p = project
        self.mb = MenuBuilder(project, work, reporter, font=font)
        self.out = out_dir
        self.work = work
        self.fast = fast
        self.ffmpeg = tools.find("ffmpeg")
        self.W, self.H = project.disc.width, project.disc.height
        self.dw = display_width(project.disc)

    def _scale_png(self, src, dst, flags):
        tools.run([self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", src, "-vf",
                   f"scale={self.dw}:{self.H}:flags={flags},setsar=1,format=rgba", "-frames:v",
                   "1", "-update", "1", dst], what="ffmpeg (menu for the web)", timeout=600)
        return dst

    def overlay(self, menu, geoms, state, color, name):
        from . import png4
        canvas = self.mb.state_canvas(menu, geoms, state, every=True)
        src = os.path.join(self.mb.work, f"{menu.id}.web-{name}.png")
        png4.write_indexed_png(src, canvas, self.mb.state_palette(menu, color))
        return self._scale_png(src, os.path.join(self.out, "menus", f"{menu.id}-{name}.png"),
                               "neighbor")

    def video(self, menu, assets, dur):
        """A motion menu, or a still one with sound, as an MP4 of one loop."""
        out = os.path.join(self.out, "menus", f"{menu.id}.mp4")
        num, den = self.p.disc.fps
        finish = f"scale={self.dw}:{self.H}:flags=bicubic,setsar=1,format=yuv420p"
        if menu.fade_in:
            finish = f"fade=t=in:st=0:d={menu.fade_in:.3f}," + finish
        if menu.background_video:
            inputs, graph = self.mb.compose(menu)
            graph = graph.replace("[out]", "[menu]") + f";[menu]{finish}[v]"
        else:
            inputs = ["-loop", "1", "-framerate", f"{num}/{den}", "-t", f"{dur:.3f}",
                      "-i", assets.base_png]
            graph = f"[0:v]{finish}[v]"
        n = inputs.count("-i")
        if menu.audio:
            inputs += ["-i", menu.audio]
            graph += f";[{n}:a:0]aresample=48000,apad[a]"
        elif menu.background_video and self.mb._probe(menu.background_video).get("has_audio"):
            graph += ";[0:a:0]aresample=48000,apad[a]"
        else:
            graph += ";anullsrc=channel_layout=stereo:sample_rate=48000[a]"
        encode.run_ffmpeg(inputs + ["-filter_complex", graph, "-map", "[v]", "-map", "[a]"] +
                          video_args(self.fast) + AUDIO + ["-t", f"{dur:.3f}", out], dur,
                          os.path.join(self.work, "logs", f"web-menu-{menu.id}.log"),
                          cwd=self.mb.work, what=f"ffmpeg (menu {menu.id} for the web)")
        return out

    def render(self, menu):
        assets = self.mb.prepare(menu)
        dur = self.mb.menu_duration(menu)
        k = self.dw / self.W
        entry = {"size": [self.dw, self.H], "duration": round(dur, 3),
                 "highlight": "menus/" + os.path.basename(
                     self.overlay(menu, assets.buttons, "highlight", menu.highlight_color,
                                  "highlight"))}
        if menu.normal_color:
            entry["normal"] = "menus/" + os.path.basename(
                self.overlay(menu, assets.buttons, "normal", None, "normal"))
        if menu.background_video or menu.audio:
            self.video(menu, assets, dur)
            entry["video"] = f"menus/{menu.id}.mp4"
        self._scale_png(assets.base_png, os.path.join(self.out, "menus", f"{menu.id}.png"),
                        "bicubic")
        entry["image"] = f"menus/{menu.id}.png"
        by_id = {b.id: b for b in menu.buttons}
        entry["buttons"] = []
        for n, g in enumerate(assets.buttons, 1):
            b = by_id.get(g.id)
            x0, y0, x1, y1 = g.rect
            entry["buttons"].append({
                "id": g.id, "number": n + menu.button_offset, "action": g.action,
                "rect": [round(x0 * k), y0, round((x1 + 1) * k), y1 + 1],
                "nav": dict(g.nav), "auto": bool(g.auto),
                **({"override": b.override} if b and b.override else {}),
                **({"subtitle": b.subtitle} if b and b.subtitle is not None else {}),
                **({"transition": transition_file(self.p, b)} if b and b.transition else {})})
        return entry


def transition_file(project, button):
    paths = sorted({key[0] for key in project.link_transitions})
    return f"transitions/{paths.index(button.transition) + 1}.mp4"


def disc_data(project, titles, menus, chapters):
    """What the player needs to know about the disc (window.DISC)."""
    def action(a):
        return a if a else "stop"
    root = project.menus[0].id if project.menus else None
    return {
        "label": project.disc.label,
        "first_play": project.disc.first_play,
        "title_key": project.disc.title_key or (f"menu:{root}" if root else None),
        "root": root,
        "menus": {m.id: dict(menus[m.id], loop=m.loop, loop_point=m.loop_point,
                             end_action=action(m.end_action), remember=m.remember_button,
                             default=m.default_button, prohibit=list(m.prohibit or ()))
                  for m in project.menus},
        "titles": {t.id: dict(titles[t.id], chapters=[round(c, 3) for c in chapters[t.id]],
                              end_action=action(t.end_action),
                              menu_key=t.remote_menu or root,
                              prohibit=list(t.prohibit or ()))
                   for t in project.titles},
        "order": [t.id for t in project.titles],
        "playlists": {pl.id: {"items": [{"title": it.title_id, "first": it.first,
                                         "last": it.last} for it in pl.items],
                              "end_action": action(pl.end_action), "order": pl.order}
                      for pl in project.playlists},
    }


def build_web(project, out_dir, reporter, fast=False, keep_work=False):
    """Write the web version of the disc into out_dir (see the module)."""
    from . import build                       # (build imports this module's callers)
    tools.require(["ffmpeg", "ffprobe"], need_drawtext=bool(project.menus))
    out_dir = os.path.abspath(out_dir)
    work = os.path.join(out_dir, ".work")
    for d in ("menus", "titles", os.path.join(".work", "logs")):
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)
    reporter.step("probe", "Checking sources")
    infos, plan = build.inspect(project, reporter, bd=True)
    for w in project.warnings + plan["warnings"]:
        reporter.warn(w)
    probes = plan["_probes"]
    titles, chapters = {}, {}
    for t in project.titles:
        info = infos[t.id]
        reporter.step("encode", f"Encoding title '{t.id}' for the web ({info['duration']:.1f}s)",
                      item=t.id)
        encode_title(t, info, project.disc, os.path.join(out_dir, "titles", f"{t.id}.mp4"),
                     work, fast=fast, probes=probes,
                     on_progress=lambda f, tid=t.id: reporter.progress("encode", f, tid))
        entry = {"src": f"titles/{t.id}.mp4", "duration": round(info["duration"], 3),
                 "subtitles": []}
        chapters[t.id] = [c for c in t.chapters if c < info["duration"]] or [0.0]
        with open(os.path.join(out_dir, "titles", f"{t.id}.chapters.vtt"), "w",
                  encoding="utf-8") as f:
            f.write(chapters_vtt(dataclasses.replace(t, chapters=chapters[t.id]),
                                 info["duration"]))
        entry["chapters_vtt"] = f"titles/{t.id}.chapters.vtt"
        for j, sub in enumerate(t.subtitles):
            cues = plan["_cues"][(t.id, j)]
            if any(c.image for c in cues):
                reporter.warn(f"title {t.id!r} subtitles[{j}]: picture subtitles are left out "
                              "of the web version")
            name = f"titles/{t.id}.sub{j + 1}.vtt"
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                f.write(to_vtt(cues, sub.position))
            entry["subtitles"].append({"src": name, "lang": sub.lang or "", "default": sub.default})
        titles[t.id] = entry
        if t.buttons:
            reporter.warn(f"title {t.id!r}: its buttons over the picture are left out of the web "
                          "version (it plays without them)")
    if len(project.titles[0].audio_tracks) > 1 or any(len(t.audio_tracks) > 1
                                                      for t in project.titles):
        reporter.warn("the web version has the first sound track of each title only")
    menus = {}
    if project.menus:
        renderer = MenuRenderer(project, work, out_dir, link_font(plan["font"], work), fast,
                                reporter)
        for m in project.menus:
            reporter.step("menu", f"Rendering menu '{m.id}' for the web", item=m.id)
            menus[m.id] = renderer.render(m)
    for k, path in enumerate(sorted({key[0] for key in project.link_transitions}), 1):
        os.makedirs(os.path.join(out_dir, "transitions"), exist_ok=True)
        reporter.step("menu", f"Encoding transition {os.path.basename(path)} for the web")
        encode_clip(path, probes.get(path) or encode.probe(path), project.disc,
                    os.path.join(out_dir, "transitions", f"{k}.mp4"), work, fast=fast)
    data = disc_data(project, titles, menus, chapters)
    with open(os.path.join(out_dir, "disc.js"), "w", encoding="utf-8") as f:
        f.write("window.DISC = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    for name in PLAYER_FILES:
        shutil.copyfile(os.path.join(PLAYER_DIR, name), os.path.join(out_dir, name))
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    size = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(out_dir)
               for f in files)
    return {"web": out_dir, "index": os.path.join(out_dir, "index.html"), "bytes": size,
            "titles": len(project.titles), "menus": len(project.menus)}

