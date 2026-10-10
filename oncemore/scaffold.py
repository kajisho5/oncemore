"""`oncemore init`: a ready-to-build sample project with generated media.

All sample media are synthesised with ffmpeg test sources (testsrc2, sine,
gradients), so nothing large is stored in the repository and every name is
obviously fictional.
"""

import json
import os
import shutil
import tempfile

from . import tools
from .errors import OncemoreError
from .menu import find_font
from .project import PROJECT_FILENAME

SAMPLE_A_SECONDS = 24
SAMPLE_A_CHAPTERS = ["00:00:00", "00:00:08", "00:00:16"]
SAMPLE_B_SECONDS = 12


def sample_project(standard="NTSC", aspect="16:9"):
    return {
        "version": 1,
        "disc": {
            "label": "SAMPLE_DISC",
            "standard": standard,
            "aspect": aspect,
            "target": "DVD5",
            "first_play": "menu:main",
            "font": None,
        },
        "titles": [
            {
                "id": "t1",
                "name": "Sample Title A",
                "source": "media/sample_a.mp4",
                "chapters": SAMPLE_A_CHAPTERS,
                "audio": {"codec": "ac3", "bitrate": "192k"},
                "end_action": "menu:main",
                "auto_chapter_menu": {"id": "chapters", "back": "menu:main"},
            },
            {
                "id": "t2",
                "name": "Sample Title B",
                "source": "media/sample_b.mp4",
                "chapters": [0],
                "audio": {"codec": "ac3", "bitrate": "192k"},
                "end_action": "menu:main",
            },
        ],
        "menus": [
            {
                "id": "main",
                "background": "media/menu_bg.png",
                "audio": None,
                "texts": [{"text": "SAMPLE DISC", "x": 120, "y": 90, "size": 56}],
                "buttons": [
                    {"id": "play", "label": "PLAY ALL", "x": 120, "y": 220, "action": "playall"},
                    {"id": "ch", "label": "CHAPTERS", "x": 120, "y": 280, "action": "menu:chapters"},
                    {"id": "b", "label": "SAMPLE TITLE B", "x": 120, "y": 340, "action": "title:t2"},
                ],
                "highlight_color": "#FFD400",
                "select_color": "#FF5A00",
            }
        ],
    }


def _ff(args, cwd, what):
    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-v", "error"] + args,
              cwd=cwd, what=what)


def init(target, standard="NTSC", aspect="16:9", force=False, reporter=None):
    tools.require(["ffmpeg"])
    target = os.path.abspath(target)
    project_path = os.path.join(target, PROJECT_FILENAME)
    if os.path.exists(project_path) and not force:
        raise OncemoreError(f"{project_path} already exists", hint="Use --force to overwrite.")
    media = os.path.join(target, "media")
    os.makedirs(media, exist_ok=True)
    fps = "30000/1001" if standard == "NTSC" else "25"

    tmp = tempfile.mkdtemp(prefix="oncemore-init-")
    try:
        text = tools.has_drawtext()
        font = None
        if text:
            try:
                src = find_font(text="Sample Title AB - Demo Chapter 0123456789 (4:3 source)")
                font = "font" + (os.path.splitext(src)[1] or ".ttf")
                try:
                    os.symlink(src, os.path.join(tmp, font))
                except OSError:
                    shutil.copyfile(src, os.path.join(tmp, font))
            except OncemoreError:
                text = False

        def overlay(lines, size=48):
            """drawtext chain: [(text, start, end)] centred near the bottom."""
            if not text:
                return ""
            parts = []
            for i, (msg, start, end) in enumerate(lines):
                fn = f"t{len(os.listdir(tmp))}_{i}.txt"
                with open(os.path.join(tmp, fn), "w", encoding="utf-8") as f:
                    f.write(msg)
                parts.append(f"drawtext=fontfile={font}:textfile={fn}:expansion=none:"
                             f"fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.6:"
                             f"boxborderw=12:x=(w-text_w)/2:y=h-text_h-60:"
                             f"enable='between(t,{start},{end})'")
            return "," + ",".join(parts)

        if reporter:
            reporter.step("init", "Generating sample media (ffmpeg test sources)")
        chap = [0, 8, 16, SAMPLE_A_SECONDS]
        a_lines = [(f"Sample Title A - Demo Chapter {i + 1}", chap[i], chap[i + 1])
                   for i in range(3)]
        _ff(["-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate={fps}:duration={SAMPLE_A_SECONDS}",
             "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={SAMPLE_A_SECONDS}",
             "-vf", "format=yuv420p" + overlay(a_lines),
             "-c:v", "mpeg4", "-q:v", "3", "-c:a", "aac", "-b:a", "128k", "-shortest",
             os.path.join(media, "sample_a.mp4")], tmp, "ffmpeg (sample_a)")
        b_lines = [("Sample Title B (4:3 source)", 0, SAMPLE_B_SECONDS)]
        _ff(["-f", "lavfi", "-i", f"testsrc2=size=640x480:rate=25:duration={SAMPLE_B_SECONDS}",
             "-f", "lavfi", "-i", f"sine=frequency=660:sample_rate=44100:duration={SAMPLE_B_SECONDS}",
             "-vf", "format=yuv420p" + overlay(b_lines, 36),
             "-c:v", "mpeg4", "-q:v", "3", "-c:a", "aac", "-b:a", "128k", "-shortest",
             os.path.join(media, "sample_b.mp4")], tmp, "ffmpeg (sample_b)")
        w, h = (1920, 1080) if aspect == "16:9" else (1440, 1080)
        _ff(["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d=1",
             "-vf", (f"format=rgb24,geq=r='18+40*X/W':g='24+50*Y/H':b='60+110*(X+Y)/(W+H)',"
                     f"drawbox=x=0:y={int(h * 0.82)}:w={w}:h=6:color=0xFFD400@0.8:t=fill"),
             "-frames:v", "1", "-update", "1", os.path.join(media, "menu_bg.png")],
            tmp, "ffmpeg (menu background)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    with open(project_path, "w", encoding="utf-8") as f:
        json.dump(sample_project(standard, aspect), f, indent=2, ensure_ascii=False)
        f.write("\n")
    return {"project": project_path,
            "media": sorted(os.path.join(media, n) for n in os.listdir(media))}
