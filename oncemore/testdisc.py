"""`oncemore testdisc`: a disc for trying oncemore's output on a real player.

A project whose every title says on screen what the viewer should see and
hear, with a checklist (TEST-CHECKLIST.md, English and Japanese) of what to
press and what should happen: menus and the remote's keys, chapters, the
sound and subtitle tracks, a 4:3 title, 5.1 sound speaker by speaker, a
motion menu, and buttons over a title (DVD) or a pop-up menu (Blu-ray).
All media are made with ffmpeg's test sources, as `oncemore init`'s are
(DECISIONS §134).
"""

import json
import os
import shutil
import tempfile

from . import __version__, tools
from .errors import OncemoreError
from .menu import find_font
from .project import PROJECT_FILENAME

MOVIE_SECONDS = 40
MOVIE_CHAPTERS = [0, 10, 20, 30]
NARROW_SECONDS = 15
SURROUND_SECONDS = 18           # three rounds of the six speakers
BUTTONS_SECONDS = 30
BUTTONS_SHOWN = (5, 25)
MOTION_SECONDS = 8
MOTION_LOOP = 3                 # the motion menu repeats from here
SPEAKERS = ["Front left", "Front right", "Centre", "LFE (a low tone)",
            "Surround left", "Surround right"]
REPORT_URL = "https://github.com/kajisho5/oncemore/issues/new?template=player-test.md"


def title_buttons(standard):
    """The buttons over the "Buttons over a title" title, in the disc's
    pixels (DVD only)."""
    h = 480 if standard == "NTSC" else 576
    y = h - 150
    return [
        {"id": "jump", "start": BUTTONS_SHOWN[0], "end": BUTTONS_SHOWN[1],
         "x": 60, "y": y, "width": 280, "height": 70, "action": "chapter:movie:3"},
        {"id": "back", "start": BUTTONS_SHOWN[0], "end": BUTTONS_SHOWN[1],
         "x": 380, "y": y, "width": 280, "height": 70, "action": "menu:main"},
    ]


def test_project(fmt="dvd", standard="NTSC", aspect="16:9", second_language="ja"):
    """The project (a dict) for a test disc made as `fmt` (dvd or bluray)."""
    dvd = fmt == "dvd"
    titles = [
        {"id": "movie", "name": "Movie", "source": "media/movie.mkv",
         "chapters": MOVIE_CHAPTERS,
         "audio": {"codec": "ac3", "bitrate": "192k"},
         "audio_tracks": [{"source": "media/movie.mkv", "lang": "en"},
                          {"source": "media/track2.wav", "lang": second_language}],
         "subtitles": [{"file": "media/subs-1.srt", "lang": "en"},
                       {"file": "media/subs-2.srt", "lang": second_language}],
         "end_action": "menu:main",
         # the Menu key: the setup menu (a pop-up over the movie on a Blu-ray)
         "remote_menu": "setup",
         "auto_chapter_menu": {"id": "chapters", "back": "menu:main"}},
        {"id": "narrow", "name": "4:3 title", "source": "media/narrow.mkv",
         "aspect": "4:3", "audio": {"codec": "ac3", "bitrate": "192k"},
         "end_action": "menu:main"},
        {"id": "surround", "name": "5.1 sound", "source": "media/surround.mkv",
         "audio": {"codec": "ac3", "channels": 6, "bitrate": "448k"},
         "end_action": "menu:main"},
    ]
    buttons = [
        ("movie", "PLAY MOVIE", "title:movie"),
        ("chapters", "CHAPTERS", "menu:chapters"),
        ("setup", "AUDIO & SUBTITLES", "menu:setup"),
        ("all", "PLAY ALL", "playall"),
        ("narrow", "4:3 TITLE", "title:narrow"),
        ("surround", "5.1 SOUND", "title:surround"),
        ("motion", "MOTION MENU", "menu:motion"),
    ]
    if dvd:
        titles.append({"id": "buttons", "name": "Buttons over a title",
                       "source": "media/buttons.mkv",
                       "audio": {"codec": "ac3", "bitrate": "192k"},
                       "buttons": title_buttons(standard), "end_action": "menu:main"})
        buttons.append(("buttons", "BUTTONS ON VIDEO", "title:buttons"))
    main = {"id": "main", "background": "media/menu_bg.png",
            "texts": [{"text": "ONCEMORE PLAYER TEST", "x": 80, "y": 50, "size": 40},
                      {"text": f"{'DVD' if dvd else 'BLU-RAY'} - {standard} {aspect} - "
                               f"oncemore {__version__}", "x": 80, "y": 100, "size": 22}],
            "buttons": [{"id": bid, "label": label, "x": 80 + 320 * (i // 4),
                         "y": 160 + 60 * (i % 4), "size": 28, "action": action}
                        for i, (bid, label, action) in enumerate(buttons)],
            "highlight_color": "#FFD400", "select_color": "#FF5A00"}
    setup = {"id": "setup", "background": "media/menu_bg.png",
             "texts": [{"text": "AUDIO & SUBTITLES", "x": 80, "y": 50, "size": 40}],
             "buttons": [{"id": bid, "label": label, "x": 80 + 320 * (i // 4),
                          "y": 140 + 60 * (i % 4), "size": 28, "action": action}
                         for i, (bid, label, action) in enumerate([
                             ("a1", "AUDIO 1 (STEADY)", "audio:1"),
                             ("a2", "AUDIO 2 (BEEPS)", "audio:2"),
                             ("s1", "SUBTITLES 1", "subtitle:1"),
                             ("s2", "SUBTITLES 2", "subtitle:2"),
                             ("soff", "SUBTITLES OFF", "subtitle:off"),
                             ("play", "PLAY MOVIE", "title:movie"),
                             ("back", "BACK", "menu:main")])],
             "highlight_color": "#FFD400", "select_color": "#FF5A00"}
    motion = {"id": "motion", "background_video": "media/motion.mkv",
              "fade_in": 1, "loop_point": MOTION_LOOP, "buttons_at_loop": True,
              "buttons": [{"id": "play", "label": "PLAY MOVIE", "x": 80, "y": 300, "size": 28,
                           "action": "title:movie"},
                          {"id": "back", "label": "BACK", "x": 400, "y": 300, "size": 28,
                           "action": "menu:main"}],
              "highlight_color": "#FFD400", "select_color": "#FF5A00"}
    disc = {"label": "PLAYER_TEST", "standard": standard, "aspect": aspect, "target": "DVD5",
            "first_play": "menu:main", "title_key": "menu:main"}
    if not dvd:
        disc["format"] = "bluray"
    return {"version": 1, "disc": disc, "titles": titles, "menus": [main, setup, motion]}


def checklist(fmt="dvd", standard="NTSC"):
    """TEST-CHECKLIST.md: what to press and what should happen (en, ja)."""
    dvd = fmt == "dvd"
    kind = "DVD" if dvd else "Blu-ray"
    en = [
        ("The disc starts", f"The main menu opens by itself, {'eight' if dvd else 'seven'} "
         "buttons, the first highlighted."),
        ("Arrows and OK", "The highlight moves with the arrows, in the order you expect; OK "
         "on PLAY MOVIE plays the movie."),
        ("Chapters", "The movie shows \"Chapter N of 4\" and its time. Next / Previous "
         "jump to chapters 1-4 at 0:00, 0:10, 0:20, 0:30."),
        ("End of the movie", "At the end the main menu comes back, PLAY MOVIE highlighted."),
        ("Chapter menu", "CHAPTERS shows four pictures; each plays its chapter; BACK returns."),
        ("Sound tracks", "AUDIO & SUBTITLES: AUDIO 1 is a steady tone, AUDIO 2 short beeps "
         "(choose one, then PLAY MOVIE). The player's own Audio key switches them too."),
        ("Subtitles", "SUBTITLES 1 shows \"Subtitle track 1\" lines, SUBTITLES 2 the second "
         "language, OFF none. The player's Subtitle key switches them too."),
        ("Menu key", "During the movie the Menu key opens AUDIO & SUBTITLES" +
         (" over the picture (a pop-up), the movie going on." if not dvd else ".") +
         " The Title / Top Menu key opens the main menu."),
        ("4:3 title", "4:3 TITLE: black bars at the sides on a 16:9 TV, nothing stretched."),
        ("5.1 sound", "5.1 SOUND: the screen names one speaker each second (front left, front "
         "right, centre, LFE, surround left, surround right); only that speaker sounds."),
        ("Motion menu", f"MOTION MENU fades in, plays once to {MOTION_LOOP} s, then repeats from "
         f"there; its two buttons appear at {MOTION_LOOP} s."),
        ("Play all", "PLAY ALL plays the titles one after the other, then the main menu."),
    ]
    if dvd:
        en.append(("Buttons over a title", "BUTTONS ON VIDEO: from 0:05 to 0:25 two boxes are "
                   "buttons; arrows highlight them, OK on the left one jumps to chapter 3 of "
                   "the movie, on the right one to the main menu."))
    ja = [
        ("ディスクの開始", f"メインメニューが自動で開き、ボタンが {8 if dvd else 7} 個あって先頭が選ばれている。"),
        ("矢印と決定", "矢印キーで選択が思った順に動く。PLAY MOVIE で決定すると本編が始まる。"),
        ("チャプター", "本編に「Chapter N of 4」と時刻が出る。次／前のチャプターで 0:00・0:10・0:20・0:30 の 1〜4 章へ移る。"),
        ("本編の終わり", "終わるとメインメニューに戻り、PLAY MOVIE が選ばれている。"),
        ("チャプターメニュー", "CHAPTERS に 4 つの画像があり、それぞれその章から再生される。BACK で戻る。"),
        ("音声トラック", "AUDIO & SUBTITLES で、AUDIO 1 は一定の音、AUDIO 2 は短いビープ音（選んでから PLAY MOVIE）。プレーヤーの音声切替キーでも切り替わる。"),
        ("字幕", "SUBTITLES 1 で「Subtitle track 1」、SUBTITLES 2 で 2 つ目の言語、OFF で字幕なし。プレーヤーの字幕切替キーでも切り替わる。"),
        ("メニューキー", "本編の再生中にメニューキーで AUDIO & SUBTITLES が開く" +
         ("（映像の上にポップアップで出て、本編は続く）。" if not dvd else "。") +
         "タイトル／トップメニューキーでメインメニューが開く。"),
        ("4:3 のタイトル", "4:3 TITLE は 16:9 のテレビで左右に黒い帯が出て、引き伸ばされない。"),
        ("5.1ch", "5.1 SOUND で画面に 1 秒ごとにスピーカー名（左前・右前・センター・LFE・左後ろ・右後ろ）が出て、そのスピーカーだけが鳴る。"),
        ("モーションメニュー", f"MOTION MENU は黒からフェードインし、{MOTION_LOOP} 秒までを一度だけ流したあと、そこから繰り返す。2 つのボタンは {MOTION_LOOP} 秒で現れる。"),
        ("全タイトル連続再生", "PLAY ALL でタイトルが順に再生され、最後にメインメニューに戻る。"),
    ]
    if dvd:
        ja.append(("タイトル上のボタン", "BUTTONS ON VIDEO で 0:05〜0:25 の間、2 つの枠がボタンになる。矢印で選べ、左で本編の 3 章へ、右でメインメニューへ移る。"))
    out = [f"# oncemore player test ({kind}, {standard})", "",
           "Burn the image (or the folder) to a disc, play it on a set-top player and "
           "tick what works. Then report the player's make and model and the results:",
           "", REPORT_URL, "", "| # | Check | What should happen | OK? |", "|---|---|---|---|"]
    out += [f"| {i} | {name} | {what} | |" for i, (name, what) in enumerate(en, 1)]
    out += ["", f"# oncemore 実機テスト（{kind}、{standard}）", "",
            "イメージ（またはフォルダー）をディスクに焼いて家庭用プレーヤーで再生し、"
            "動いたものに印を付けてください。結果はプレーヤーのメーカー・機種名と一緒に、"
            "こちらから報告してください：", "", REPORT_URL, "",
            "| # | 確認すること | 期待する動き | OK? |", "|---|---|---|---|"]
    out += [f"| {i} | {name} | {what} | |" for i, (name, what) in enumerate(ja, 1)]
    return "\n".join(out) + "\n"


def _ff(args, cwd, what):
    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-v", "error"] + args,
              cwd=cwd, what=what, timeout=600)


def init(target, fmt="dvd", standard="NTSC", aspect="16:9", force=False, reporter=None):
    """Make the test disc's project, media and checklist in `target`."""
    if fmt not in ("dvd", "bluray"):
        raise OncemoreError(f"format must be dvd or bluray, not {fmt!r}")
    tools.require(["ffmpeg"], need_drawtext=True)
    target = os.path.abspath(target)
    project_path = os.path.join(target, PROJECT_FILENAME)
    if os.path.exists(project_path) and not force:
        raise OncemoreError(f"{project_path} already exists", hint="Use --force to overwrite.")
    media = os.path.join(target, "media")
    os.makedirs(media, exist_ok=True)
    fps = "30000/1001" if standard == "NTSC" else "25"
    second = "ja"
    ja_line = "字幕トラック 2（日本語）"
    try:
        find_font(text=ja_line)
    except OncemoreError:
        second, ja_line = "fr", "Sous-titre piste 2 (francais)"   # (no Japanese font here)

    tmp = tempfile.mkdtemp(prefix="oncemore-testdisc-")
    try:
        src = find_font(text="ONCEMORE PLAYER TEST 0123456789 Chapter of: ()")
        font = "font" + (os.path.splitext(src)[1] or ".ttf")
        try:
            os.symlink(src, os.path.join(tmp, font))
        except OSError:
            shutil.copyfile(src, os.path.join(tmp, font))
        count = [0]

        def say(msg, start=0, end=10_000, size=44, y="h-text_h-60"):
            """drawtext of `msg` (a file, so any character is safe) from start to end."""
            count[0] += 1
            fn = f"t{count[0]}.txt"
            with open(os.path.join(tmp, fn), "w", encoding="utf-8") as f:
                f.write(msg)
            return (f"drawtext=fontfile={font}:textfile={fn}:expansion=none:fontsize={size}:"
                    f"fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=12:"
                    f"x=(w-text_w)/2:y={y}:enable='between(t,{start},{end})'")

        clock = (f"drawtext=fontfile={font}:text='%{{pts\\:hms}}':fontsize=36:fontcolor=white:"
                 "box=1:boxcolor=black@0.6:boxborderw=8:x=40:y=40")

        def video(name, seconds, size, filters, audio, extra=()):
            _ff(["-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}:duration={seconds}"]
                + list(audio) + ["-vf", ",".join(["format=yuv420p"] + filters),
                                 "-c:v", "mpeg4", "-q:v", "3"] + list(extra) +
                ["-shortest", os.path.join(media, name)], tmp, f"ffmpeg ({name})")

        if reporter:
            reporter.step("testdisc", "Generating the test disc's media (ffmpeg test sources)")
        chap = MOVIE_CHAPTERS + [MOVIE_SECONDS]
        video("movie.mkv", MOVIE_SECONDS, "1280x720",
              [say(f"Movie - Chapter {i + 1} of 4", chap[i], chap[i + 1]) for i in range(4)]
              + [clock],
              ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={MOVIE_SECONDS}"],
              ["-c:a", "pcm_s16le"])
        # the second sound track: short beeps, so the two are told apart by ear
        _ff(["-f", "lavfi", "-i",
             f"aevalsrc='0.5*sin(2*PI*880*t)*lt(mod(t\\,1)\\,0.25)':s=48000:d={MOVIE_SECONDS}",
             "-ac", "2", os.path.join(media, "track2.wav")], tmp, "ffmpeg (track2.wav)")
        for n, (lang_line, path) in enumerate([("Subtitle track 1 (English)", "subs-1.srt"),
                                               (ja_line, "subs-2.srt")], 1):
            with open(os.path.join(media, path), "w", encoding="utf-8") as f:
                for k in range(MOVIE_SECONDS // 5):
                    a, b = k * 5 + 1, k * 5 + 4
                    f.write(f"{k + 1}\n00:00:{a:02d},000 --> 00:00:{b:02d},000\n"
                            f"{lang_line} - {k + 1}\n\n")
        video("narrow.mkv", NARROW_SECONDS, "640x480",
              [say("4:3 title: bars at the sides on a 16:9 TV, nothing stretched", size=26)],
              ["-f", "lavfi", "-i", f"sine=frequency=330:sample_rate=48000:duration={NARROW_SECONDS}"],
              ["-c:a", "pcm_s16le", "-aspect", "4:3"])
        # 5.1: one speaker a second, in the order the screen names them
        exprs = []
        for k in range(6):
            tone = 60 if k == 3 else 440
            exprs.append(f"0.5*sin(2*PI*{tone}*t)*between(mod(t\\,6)\\,{k}\\,{k}+0.8)")
        names = [say(f"Now: {name}", f"{r * 6 + k}", f"{r * 6 + k + 1}")
                 for r in range(SURROUND_SECONDS // 6) for k, name in enumerate(SPEAKERS)]
        video("surround.mkv", SURROUND_SECONDS, "1280x720", names,
              ["-f", "lavfi", "-i", "aevalsrc='" + "|".join(exprs) +
               f"':s=48000:d={SURROUND_SECONDS}:channel_layout=5.1"],
              ["-c:a", "pcm_s16le"])
        if fmt == "dvd":
            h = 480 if standard == "NTSC" else 576
            sx, sy = 1280 / 720, 720 / h
            boxes = []
            for b, label in zip(title_buttons(standard), ["Chapter 3", "Main menu"]):
                x, y = int(b["x"] * sx), int(b["y"] * sy)
                w, hh = int(b["width"] * sx), int(b["height"] * sy)
                boxes.append(f"drawbox=x={x}:y={y}:w={w}:h={hh}:color=white@0.8:t=4:"
                             f"enable='between(t,{BUTTONS_SHOWN[0]},{BUTTONS_SHOWN[1]})'")
                boxes.append(say(label, *BUTTONS_SHOWN, size=36, y=f"{y + 30}").replace(
                    "x=(w-text_w)/2", f"x={x}+({w}-text_w)/2"))
            video("buttons.mkv", BUTTONS_SECONDS, "1280x720",
                  boxes + [say("Buttons over a title: 0:05-0:25", size=30, y="40"), clock],
                  ["-f", "lavfi", "-i",
                   f"sine=frequency=550:sample_rate=48000:duration={BUTTONS_SECONDS}"],
                  ["-c:a", "pcm_s16le"])
        video("motion.mkv", MOTION_SECONDS, "1280x720",
              [say(f"Motion menu: plays once to {MOTION_LOOP} s, then repeats from there",
                   size=30, y="60"), clock],
              ["-f", "lavfi", "-i", f"sine=frequency=262:sample_rate=48000:duration={MOTION_SECONDS}"],
              ["-c:a", "pcm_s16le"])
        w, h = (1920, 1080) if aspect == "16:9" else (1440, 1080)
        _ff(["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d=1",
             "-vf", ("format=rgb24,geq=r='20+30*X/W':g='28+40*Y/H':b='70+100*(X+Y)/(W+H)',"
                     f"drawbox=x=0:y={int(h * 0.86)}:w={w}:h=6:color=0xFFD400@0.8:t=fill"),
             "-frames:v", "1", "-update", "1", os.path.join(media, "menu_bg.png")],
            tmp, "ffmpeg (menu background)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    with open(project_path, "w", encoding="utf-8") as f:
        json.dump(test_project(fmt, standard, aspect, second), f, indent=2, ensure_ascii=False)
        f.write("\n")
    check = os.path.join(target, "TEST-CHECKLIST.md")
    with open(check, "w", encoding="utf-8") as f:
        f.write(checklist(fmt, standard))
    return {"project": project_path, "checklist": check,
            "media": sorted(os.path.join(media, n) for n in os.listdir(media))}
