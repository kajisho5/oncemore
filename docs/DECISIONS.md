# Decisions

Judgement calls made while building phase 1, with the reasoning. Newest last.

## 1. One titleset for everything; GPRM dispatch for "return to menu X"

DVD-Video only lets a title *call* the root menu of its own titleset
(`CallSS`). Buttons in the titleset menu domain can jump to any menu
(`LinkPGCN`), title (`JumpVTS_TT`) or chapter (`JumpVTS_PTT`). So all menus and
titles go into titleset 1; the first-play menu becomes menu PGC 1 with
`entry="root"`, and a title's `end_action: menu:<id>` stores the target menu
number in `g1` before `call menu entry root;`. The root menu's `<pre>`
dispatches on `g1` and clears it. First play and the VMGM title menu use the
same mechanism. Verified with libdvdnav and VLC.

Consequence: all titles share one audio format and the disc has a single aspect
ratio. Mixed audio codecs are rejected by `validate` with a clear message
rather than silently transcoded. Multiple titlesets are phase 3.

## 2. ISO backend order: hdiutil → genisoimage → mkisofs → xorriso

The brief asked for `xorriso -as mkisofs -dvd-video`. Checking the actual tool
showed that **xorriso has no `-dvd-video` option** (`xorriso 1.5.6:
-as mkisofs: Unsupported option '-dvd-video'`) and its man page has no UDF
support. An ISO 9660-only image built with xorriso cannot be opened by
libdvdread (`DVDOpenFileUDF:UDFFindFile /VIDEO_TS/VIDEO_TS.IFO failed`), which
is what VLC and mpv use, and standalone players need UDF as well. The same
content written with `genisoimage -dvd-video -udf` opened and navigated
correctly.

So oncemore prefers tools that write a UDF + ISO 9660 bridge: `hdiutil
makehybrid -udf -udf-version 1.02 -iso` (built into macOS, so Mac users need no
extra package), then `genisoimage` / `mkisofs` (`-dvd-video -udf`). xorriso is
kept as a last resort with a prominent warning, and `doctor` reports it as not
ready. The README install commands reflect this (`genisoimage` instead of
`xorriso` on Linux). CI still installs xorriso because the tests use it to list
and extract files from the image.

## 3. Homebrew: `ffmpeg-full`, not `ffmpeg`

Homebrew's `ffmpeg` formula (9.0.2 at the time of writing) depends on neither
freetype nor fontconfig and is configured without `--enable-libfreetype`, so it
has no `drawtext` filter. `ffmpeg-full` has it but is keg-only. oncemore looks
in `/opt/homebrew/opt/ffmpeg-full/bin` and `/usr/local/opt/ffmpeg-full/bin`
before PATH (on macOS) and `doctor` checks for `drawtext` explicitly.

## 4. Frame-accurate chapters by planning the GOPs

Forcing a key frame at a chapter is not enough: dvdauthor merges a GOP shorter
than the 0.4 s minimum VOBU length into the next one, so with an 18-frame GOP
grid a chapter at 8.0 s landed on 7.807 s. oncemore encodes with a fixed GOP
grid (scene-cut I-frames disabled) and, for each chapter, splits the last
GOPs before it evenly so every GOP is 12–18 frames (NTSC) or 10–15 (PAL). The
chapter time handed to dvdauthor is the key frame plus half a frame. Chapters
less than about one second apart cannot always be satisfied and may still
shift by a GOP.

Closed GOPs (`-flags +cgop`) were tried, but mpeg2video refuses them together
with scene-change detection, and they are not needed for correct cell
boundaries.

## 5. Text rendered on a square-pixel canvas

DVD pixels are non-square (16:9 NTSC pixels are ~1.19× wide). Menus are drawn
at the display resolution (854×480, 640×480, 1024×576, 768×576) and scaled to
720 wide, so text and thumbnails keep their proportions. Project coordinates
stay in DVD pixels (720×480/576) as the brief specifies.

## 6. Button geometry from the rendered label

Each label is rendered alone with exactly the same filter chain as the menu,
read back as raw 8-bit gray, and scanned for its bounding box and glyph mask.
The highlight is the glyph mask plus an underline (text buttons) or a frame
around the thumbnail (chapter buttons). Rectangles get even y coordinates
(spumux warns otherwise) and overlapping buttons are an error.

## 7. Navigation algorithm

A neighbour in a direction must lie entirely on that side (e.g. its top edge at
or below our bottom edge); among those, distance along the direction plus twice
the sideways distance wins. Without a neighbour we wrap within the same column
(up/down) or row (left/right), else stay. This keeps a vertical list from
having "right" jump to a wider button below.

## 8. Menus loop; still frames are not used

Menus are a few seconds long (5 s, or the music length) and loop with
`jump cell 1;`, as the brief describes. This also gives background music a
natural loop.

## 9. Stereo audio, silent track when missing

All titles are down-mixed to 2 channels at 48 kHz (AC-3 or 16-bit LPCM).
Sources without audio get a silent track so every title has the same stream
layout. Menus always carry AC-3 (silence if no music).

## 10. Schema validation without dependencies

`oncemore/schemalite.py` implements the subset of JSON Schema used by the
project schema, so validation stays stdlib-only and the schema file is the
single source of truth. The schema lives inside the package
(`oncemore/project.schema.json`) so `pip install` ships it; `schema/` holds an
identical copy, enforced by a unit test.

## 11. Chapter menu shape

`auto_chapter_menu` sits on the title (`true` or an options object). Six
thumbnails per page (3×2), BACK/PREV/NEXT on a bottom row, default id
`chapters_<title id>`, pages `_2`, `_3`… Thumbnails are taken 1 s into each
chapter (or half-way for short chapters) to avoid black frames at cuts.

## 12. Automated "remote control" tests via libdvdnav

mpv does not support DVD menus (its manual says so), so it cannot verify
navigation. The E2E tests load libdvdnav with ctypes and select/activate
buttons, then check the title/chapter that starts and where playback returns.
The same scenario was repeated manually in VLC 3.0.20 through its `oldrc`
interface (`key key-nav-down`, `key key-nav-activate`, `title`, `chapter`).

## 13. Sample media

`oncemore init` synthesises everything with ffmpeg (`testsrc2`, `sine`, `geq`
gradient) and encodes it with the built-in `mpeg4` and `aac` encoders, which
exist in every ffmpeg build. Sample A is 1280×720 16:9 with on-screen chapter
labels; sample B is 640×480 4:3 at 25 fps with 44.1 kHz audio, to exercise
pillarboxing and rate conversion.
