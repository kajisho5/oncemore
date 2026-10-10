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

Consequence (phase 1): all titles shared one audio format and aspect ratio.
Lifted in §20.

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

Titles are down-mixed to 2 channels at 48 kHz (AC-3 or 16-bit LPCM) unless
they ask for 5.1 (see 23).
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

## 14. Lessons taken from ffmpeg-skill's field notes

The author's ffmpeg-skill repository documents real-world ffmpeg pitfalls.
Three apply here and were acted on:

* **drawtext draws missing glyphs as empty boxes and exits 0.** oncemore reads
  the font's `cmap` (formats 4/12, TTF/OTF/TTC face 0, `fontcheck.py`) and
  auto-detection picks the first candidate that covers every menu character;
  an explicit font that does not cover them is an error naming the characters.
  `validate` runs the same check.
* **`-filters` can list drawtext on builds that cannot draw.** `doctor` now
  renders one frame with drawtext and checks that pixels were drawn.
* **ffmpeg 7.1+ turns output `-colorspace` into a conversion constraint.** For
  SD BT.601 output this should be a no-op, but rather than rely on reasoning
  the E2E suite decodes a solid menu background and checks the colour, so the
  macOS job (Homebrew ffmpeg 9.x) measures it.

## 15. Repairing ffmpeg's DVD LPCM headers

ffmpeg's MPEG-PS muxer writes every LPCM packet's private header with a fixed
"7 frames start here, first one at offset 4" (its source even says
`XXX: check nb_frames`). dvdauthor derives each audio packet's duration from
that count (150 ticks per 1/600 s frame), so every LPCM title produced
thousands of "Audio pts ... moves backwards / Discontinuity ... please
remultiplex" warnings and wrong audio timing tables; ffprobe and the earlier
tests did not notice. AC-3 is not affected.

Fix: encode LPCM in 80-sample frames (exactly one DVD LPCM frame; resampling
and remixing are done in the same filter chain *before* the split, otherwise
an auto-inserted converter re-chunks the frames), so the PTS ffmpeg writes is
the PTS of the first frame starting in each packet; then `lpcmfix.py` rewrites
the frame count and first-frame pointer of every LPCM packet in place from the
packet's byte position in its stream. The decoded audio is bit-identical
before and after, and dvdauthor reports no warnings; the PAL/LPCM E2E test
now asserts an empty warning list.
## 16. The empty disc title with hdiutil images is libdvdnav's, not the ISO's

macOS CI showed libdvdnav logging an empty "DVD Title" for hdiutil images.
Reading the image back (`udfinfo.py`) shows the UDF Primary Volume Descriptor
and the ISO 9660 descriptor both carry the label. libdvdnav's `dvd_read_name`
(src/vm/vm.c) reads the title raw from sector 32, where physical DVDs and
genisoimage place the UDF Main Volume Descriptor Sequence; hdiutil places it
elsewhere. Only the title *metadata* in libdvdnav players is affected, so
oncemore leaves hdiutil as the macOS default and documents it. `iso` still
warns if the UDF volume name ever differs from the label.

## 17. Subtitles are rendered by oncemore, not by spumux's text mode

spumux can render text subtitles itself, but with its own font handling and
no outline control. Drawing each cue with the same drawtext pipeline as the
menus gives the same font (with the cmap coverage check, so Japanese never
turns into boxes), a proper outline, and correct proportions on 16:9 discs.
The RGBA result is reduced to transparent / fill / outline / anti-alias,
cropped, and placed with spumux `xoffset`/`yoffset`. Cues are rendered in
parallel (about 80 ms each).

## 18. Stream defaults are disc-wide and set once at first play

DVD subtitle/audio selection lives in SPRM 1/2, shared by every title. Setting
it in each title's `<pre>` would override what the viewer picked in a setup
menu, so a `"default": true` subtitle is switched on once in the first-play
program instead. Stream languages are per titleset, hence per disc here, and
`validate` rejects titles that disagree.

## 19. Motion menus reuse the still-menu graph

The menu drawing graph (background → thumbnails → drawtext → squeeze) is
shared: for a still menu it renders one PNG which is then looped, for a motion
menu the same graph runs over every frame of the video (converted to the disc
frame rate, last frame held if `duration` is longer). Highlights are the same
spumux subpicture, so navigation is unchanged.

## 20. Several titlesets, grouped automatically

Titles are grouped by (aspect, audio codec) in project order; the first
title's group is titleset 1 and keeps all menus, so single-format projects
produce exactly the phase-1 structure (no jumppad). With more groups:

* buttons use `jump titleset N title K [chapter C]` and dvdauthor's
  `jumppad="yes"` builds the VMGM routing (verified with libdvdnav, including
  a chapter of a title in titleset 2);
* a title outside titleset 1 cannot CallSS titleset 1's menus, so it stores
  the target menu in g1 and calls the VMGM title menu, which jumps to
  titleset 1's root menu where the existing g1 dispatcher takes over. For
  that the VMGM title menu no longer clears g1 in multi-titleset discs (the
  dispatcher clears it after use, so the remote's Top Menu still lands on
  the root menu);
* each titleset gets its own `<video>`/`<audio>`/`<subpicture>` attributes;
  chapter-menu thumbnails are fitted from the title's own aspect into the
  menu's thumbnail box (a 4:3 title is pillarboxed in a 16:9 menu).

dvdauthor warns "The use of jumppad requires a menu; creating a dummy ENGLISH
menu" for titlesets without menus; that is expected and harmless.

## 21. The GUI is a local web app

The goal is an authoring app ordinary Mac users can run. A local web app was
chosen over a native Swift app for phase 2:

* it is built and tested here end to end (Playwright drives the real page:
  upload, chapters, menu drag and undo, preview, build), which a native UI
  could not be without a Mac;
* the same UI becomes the phase 4 in-browser version once the core runs as
  WebAssembly;
* it needs nothing beyond what the CLI needs (Python stdlib server, plain
  HTML/CSS/JS, no npm or build step).

Security: the server binds 127.0.0.1, requires a random per-launch token
(passed in the URL fragment, so it is never sent in requests or logged)
on every API call, rejects requests whose Host header is not this server
(DNS rebinding), serves files only from inside the project folder (images and
subtitles only), and sets a strict Content-Security-Policy (no inline or
eval'd script). `<img>` requests carry the token as a query parameter, which
only the frame/file endpoints accept.

The editor draws menus with HTML for instant dragging; text metrics differ
slightly from drawtext, so "Exact preview" renders the real menu on the
server (same code as the build) and shows the true button hit areas.
Oncemore.app wraps the same page in a WKWebView with a bundled Python.

## 22. "Play all" is a register flag, not a title chain

Before, the sample's PLAY ALL button started title 1 whose `end_action` was
`title:t2`, so title 1 could never be played on its own and return to the
menu. `playall` sets GPRM g2 = 1 and starts the first title; every title's
`<post>` begins with `if (g2 == 1) jump <next title>` (next in project order,
across titlesets through the jumppad), the last title clears g2 and then runs
its own `end_action`. Title and chapter buttons clear g2, so a single play
after a play-all ends normally. The commands are only emitted when some button
or `first_play` uses `playall`, so other discs' IFOs are unchanged. Pressing
Menu during play-all and resuming keeps the flag, as players expect.

## 23. 5.1 is opt-in and always re-encoded

`audio.channels: 6` encodes 5.1 AC-3 (default 448k). It is opt-in because a
stereo source would only be up-mixed to the front speakers (oncemore warns),
and LPCM 5.1 is refused (DVD allows it, but 4.6 Mbit/s of audio leaves little
for video). DVD fixes the audio format per stream per titleset, so the
channel count joins aspect and codec in the titleset grouping (20). Source
AC-3 is re-encoded rather than passed through: pass-through would need the
audio to start exactly with the video and match the title length, which the
pad-and-cut audio graph guarantees for re-encoded audio only; at 448k the
generation loss is small.
