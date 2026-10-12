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
server (same code as the build) and shows the true button hit areas. A native
.app wrapper (WKWebView) is the next step.

## 24. Image buttons: a frame by default

A DVD highlight is a 2-bit subpicture laid over the video, so it can only
recolour pixels, not swap in another picture. For a picture button oncemore
offers two highlights: a 3-pixel frame around the picture (default, the same
as chapter thumbnails, readable on any picture) or the picture's own shape
(pixels with alpha ≥ 50 % painted in the highlight colour, for icon-like
pictures; a semi-transparent highlight colour tints instead of covering).
The picture is drawn by the same ffmpeg overlay chain as thumbnails, so motion
menus work too, and it is checked to stay inside the frame. The editor picks
a starting width that keeps the picture on screen.

## 25. Playback preview through a cached proxy

Browsers cannot play most camera or editing formats, and WebKit (the Mac app)
only plays a video from a server that answers byte-range requests. The GUI
server therefore encodes a 360-line H.264/AAC MP4 (or VP8/Opus WebM when the
page reports no H.264, e.g. Chromium test builds or Firefox) once per source,
caches it in `.oncemore-cache/proxy/` (keyed by path, size and mtime) and
serves it with `Range` support. Playback is for watching only: when it stops
the editor shows the exact frame from the source again, so chapter marks stay
frame-accurate.

## 26. Menu timing and remote keys, in a fixed register map

Registers: g1 target menu (the root menu consumes it and resets it to 0),
g2 play-all flag, g3 the Menu-key target of the playing title, g4 the loop
counter of the current menu, g5-g11 the last button used in menus 1-7
(g5-g12 for menus 1-8 until playlists took g12, see 27).
g13-g15 are left alone: dvdauthor uses them as scratch registers, notably for
buttons with several statements, which it compiles into a dispatcher in the
PGC's post commands. That dispatcher falls through from one button's code into
the next when a block does not jump, so only buttons that leave the menu get
the extra "remember this button" statement; stream-switch buttons stay single
statements.

* `g1` now always holds the explicit menu number (1 for the root menu). That
  makes 0 mean "nothing pending", which the VMGM title menu uses to tell the
  remote's Title key (g1 == 0) from a route out of another titleset (g1 set),
  so `disc.title_key` can target any menu, title or play-all.
* Menu key: a title with `remote_menu` sets g3 in its pre commands; the root
  menu takes g3 when g1 is 0. Titlesets after the first get a root menu
  without video that sends the Menu key back through the VMGM (before, the
  Menu key did nothing there).
* Loop count / loop point / end action: the menu post counts plays in g4.
  A loop point splits the menu VOB into two cells (with a forced keyframe at
  the point, so the cell starts a VOBU) and repeats jump to cell 2.
* Default and remembered buttons set SPRM8 (`button = …`) in the menu's pre.
* Auto-activate buttons are spumux `<action>` elements, which dvdauthor writes
  with the button's auto-action flag.

All of it is checked by driving a disc through libdvdnav (Menu / Title keys,
highlight after returning, an intro that plays cells 1, 2, 2 and times out).

## 27. Playlists as a state machine over the existing titles

A playlist does not copy video: every item of every playlist is a state
number kept in g0, and g12 holds the chapter at which the current item stops
(0 = the end of the title). Starting an item sets both and jumps to its first
chapter.

dvdauthor allows exactly one VM instruction per cell command, so a title in
which some item stops early is written as explicit chapter cells, each with
`if (g12 == k) jump pgc tail;`. That runs the title's post commands, which
dispatch on g0: the next item (directly in the same titleset, or through the
VMGM with g1 = 1000 when it is in another one) or the playlist's end action.
Titles nobody stops early keep the plain `chapters=` form. Single plays
(title, chapter, play all) clear g0 and g12 — a stale g12 would otherwise cut
the next title short at that chapter.

Verified with libdvdnav: a playlist "t1:2, t2:2-3, t1:1" plays exactly
(1,2) → (2,2) (2,3) → (1,1) → menu, across two titlesets.

## 28. Menu design stays within what a DVD can show

* Rectangles, outlines and shadows are drawn into the menu picture (drawbox,
  drawtext's border and shadow), so they cost nothing at playback. The
  highlight mask is still measured from the plain letters: the highlight
  recolours the letters, and the outline / shadow stay as they are.
* A font per element is linked into the work folder under an ASCII name, like
  the disc font, and checked for every character of that element (drawtext
  has no fallback). The editor loads the same font file to draw the stage.
* A button's `highlight_image` replaces the automatic highlight with the
  opaque pixels of a picture — the equivalent of a hand-drawn highlight layer.
  Its hit area covers both the label (or image) and the picture.
* Animated thumbnails are the title itself, fitted the same way as still
  thumbnails and overlaid on the motion background, so they cost no extra
  encode step; they need a motion background (a still menu is one frame).
* Templates are plain menu JSON generated for the project (its titles, chapter
  menus, playlists and streams), sized for NTSC or PAL; labels are shortened
  to fit their slot so the layout never produces overlapping buttons (tested
  for every template with 2 and 8 titles on both standards).

## 29. Encode cache, per-title bitrate, AC-3 copy, DVD-ROM files

* Cache: encoded titles (after the LPCM header fix, before subtitles) and
  menus are stored under `<project>/.oncemore-cache/encode` and hard-linked
  into the build. The key covers everything that changes the bytes —
  sources' path, size and mtime, the title or menu definition, disc format,
  bitrate, 1-/2-pass, the ffmpeg and spumux versions, and a hash of
  oncemore's encoding modules, so a new oncemore never reuses stale output.
  Adding a title changes the shared bitrate and therefore re-encodes; that is
  the price of a correct key.
* Per-title bitrate: titles with `video_bitrate` take their share first; the
  others share what is left, still capped by the DVD rate limits.
* AC-3 copy: only 48 kHz AC-3 with the title's channel count is accepted
  (checked per stream); the streams are mapped directly with `-c:a copy`,
  so there is no padding — DVD allows audio shorter than the video.
* DVD-ROM content is copied next to VIDEO_TS and included when the ISO is
  staged; VIDEO_TS / AUDIO_TS cannot be overwritten that way.

## 30. Subtitle formats, placement and colour

* WebVTT and ASS / SSA are read into the same cues as SRT (WebVTT timing
  without hours, `line:` settings; ASS styles' alignment and primary colour,
  `\N` line breaks, override tags). Cue text loses its tags; placement and
  colour survive as cue attributes.
* Precedence: the cue's own tag, then the track's `color` / `position` in the
  project, then the subtitle file's style, then `disc.subtitle_style`.
* Cues are always rendered white on black, so the brightness-based 4-level
  quantiser keeps working for dark colours too; the real colour goes into
  each cue's PNG palette (fill, outline, and their mix for anti-aliasing).
  spumux merges the palettes, and a title's 16-entry subpicture palette
  limits it to about 7 text colours, which validation checks.
* Free positioning is left out on purpose: lines stay centred at the top or
  the bottom, which covers signs and speaker separation without a layout
  editor for every cue.

## 31. Slideshows and the subtitle editor

* A slideshow is rendered to a lossless intermediate (FFV1 + PCM in Matroska)
  instead of being fed to the MPEG-2 encoder directly: the encode, cache,
  bitrate plan, chapters and subtitles then treat it exactly like a video
  title, and the expensive filter graph runs only when the show changes (its
  file name is a hash of the pictures' path, size and mtime, the settings,
  the disc format and the slideshow code).
* One ffmpeg graph: each picture is fitted on the square-pixel canvas with the
  background colour, held for its duration plus the fade, and joined by
  `xfade` (offset = sum of the earlier durations) or `concat`. So the total
  length is the sum of the durations and slide *k* begins at a frame the
  chapter list can name exactly. Pan & zoom uses `zoompan` on a canvas twice
  the size, alternating zoom in and out, to avoid whole-pixel wobble.
* Inputs are always bounded (`-t` per still picture, `d=` for zoompan,
  `atrim` + `apad` on music, `-t` on the output): with endless inputs
  (`tpad=stop=-1`, an unbounded loop) Homebrew's ffmpeg 9 on macOS could
  stall forever. Every ffmpeg run also has a watchdog that stops it after
  five minutes without progress.
* The subtitle editor writes SubRip only. WebVTT and ASS files are read and
  shown but never overwritten (their styling would be lost); *Save as .srt*
  converts, keeping placement and colour as `{\an8}` and `<font color>`.
  Writes are limited to subtitle extensions inside the project and are atomic
  (temp file + rename).

## 32. Interlaced output and soft 3:2 pulldown

* `scan: auto` picks per title from the probed source: interlaced at the
  disc's frame rate (or reporting its field rate) and progressive 59.94 / 50
  fps sources are stored interlaced, 23.976 fps progressive sources on NTSC
  get soft pulldown, everything else stays progressive as before. Exactly
  24.000 fps is not treated as film: playing it at 23.976 would drift from
  its audio by 0.1 %.
* Interlaced: the picture is processed one field at a time (bwdif
  `send_field` for interlaced sources, the 59.94 / 50 fps frames as they
  are), scaled, and woven back with `interlace=scan=tff`, so resizing never
  mixes the two moments in one field. The low-pass against line twitter is
  used only when the picture was resized; same-size sources keep their
  original lines. Encoded top field first with interlaced motion estimation
  and DCT, and alternate scan.
* Pulldown: ffmpeg's MPEG-2 encoder cannot write repeat_first_field, so the
  film frames are encoded at 23.976 into an elementary stream and
  `oncemore/pulldown.py` edits fixed-position header bits afterwards
  (frame_rate_code 4, progressive_sequence 0, and per picture
  progressive_frame 1 with top_field_first / repeat_first_field cycling
  (1,1) (0,0) (0,1) (1,0) by display order from temporal_reference). No
  byte is added, the file is memory-mapped, and the stream is then muxed
  with `-c:v copy` and generated timestamps. Players show 3, 2, 3, 2 fields
  per frame and the field parity never breaks, as on film DVDs.
* Film GOPs are at most 14 pictures (35 fields, under the 36-field NTSC
  limit) and at least 10 (25 fields, over 0.4 s); chapter marks and forced
  key frames use the 23.976 frame grid of the encoded pictures.

## 33. Flowchart, navigation check and the disc simulator

* One navigation graph (`oncemore/graph.py`) feeds the flowchart and the
  checks: nodes are first play, the Title key, menus, titles, playlists, play
  all and stop; edges are buttons, menu time-outs, end actions, play-all
  succession, playlist items and the Menu key of each title. Columns are the
  breadth-first distance from first play; unreachable nodes get the last
  column, so they stand out.
* Checks are warnings only where a viewer is really affected: a menu, title
  or playlist that nothing leads to, and a menu with neither a button that
  leaves it nor a time-out. A title that stops playback, or a menu end action
  that can never run because the menu loops forever, is an "info" note.
* The simulator (`oncemore/simulate.py`) is not a second design of the
  navigation but a transcription of what `author.py` compiles: the root-menu
  dispatcher, g0 / g2 / g3 / g12, remembered buttons in g5–g11, playlist
  cell commands that only fire at the end of their chapter (so skipping past
  them continues the title), Next on the last chapter running the post
  commands, and the player keeping the highlighted button number (SPRM 8)
  when a menu does not set one. Button geometry and arrow-key neighbours come
  from the same layout code as the disc.
* It is checked against libdvdnav: a disc using two titlesets, a playlist
  across them, play all, remembered and default buttons, an auto-activate
  button, stream buttons, Menu / Title key targets and an intro that times
  out is driven by seeded random key sequences, and after every key both must
  show the same menu and button or the same title and chapter (600 keys over
  20 sessions agreed while developing it; the test runs 12 sessions).
* In the app the menu pictures are the exact previews without highlights
  plus one highlight overlay per button, rendered once per menu definition
  and cached, so moving around is instant.

## 34. Layered Photoshop menus

* The reader (`oncemore/psd.py`) is our own, stdlib only, like the rest of
  the core: PSD and PSB, RGB and grayscale, 8 and 16 bits (16 reduced to 8),
  raw / PackBits / ZIP / ZIP-with-prediction channels, layer masks, groups
  from section dividers, Unicode names. It was cross-checked against
  psd-tools in both directions (files from our test writer read by psd-tools,
  files written by psd-tools read by us; pixels exact) and fuzzed with
  truncated and corrupted files, which only ever raise `PsdError`. CMYK, Lab,
  indexed and 32-bit files are refused with a message to save as RGB.
* The import follows the long-standing DVD layer-name prefixes — `(+)` button
  groups, `(=1)`–`(=3)` highlight layers, `(%)` thumbnail placeholders — so
  existing designs and templates work unchanged. It produces plain project
  JSON (a background picture, buttons with a `highlight_image` and an
  optional `thumbnail`), so imported menus are edited, simulated and built
  like any other; nothing depends on keeping the .psd.
* Background: the file's flattened image is used whenever it shows exactly
  the artwork (highlight and placeholder layers hidden), because only it has
  Photoshop's layer effects, adjustment layers and blend modes applied. When
  those layers are visible the background is rebuilt with ffmpeg overlays
  (normal blending, opacity including parent groups), and the note says what
  is lost.
* Geometry: the document is stretched to the menu frame, so a design made at
  720 × 480 / 576 (non-square DVD pixels, the usual DVD template size) and one
  made at the square-pixel size both land where they were drawn. The
  highlight pictures are written at square-pixel size so the existing image
  placement (width on the 720 grid, height from the aspect) reproduces them.
* Re-import keeps each button's action, navigation and auto-activate by
  button id (the slug of the group name) and the menu's own settings, so a
  designer can iterate in Photoshop without re-linking the buttons.
* Text layers are imported as their rendered pixels (the text itself is not
  editable here); vector shapes and smart objects likewise.

## 35. The workspace and the design system

* The app keeps the panel layout that disc authoring and video editing
  people already know (project on the left, editor with a timeline in the
  middle, properties and layers on the right, workspaces in the top bar), but
  its look is our own: colours, icons, wording and artwork are not taken from
  any product. docs/DESIGN.md is the reference.
* Tokens are CSS custom properties in one file; components only use them.
  Tests fail on an undefined variable, a raw hex colour in the component
  stylesheet, a colour token missing from the light theme or the style guide,
  and on English / Japanese key lists that differ.
* Still no build step and no front-end dependencies: plain HTML, CSS and one
  script, so the Mac app, the browser app and a future in-browser version
  share the same files.
* Panel sizes and the theme are stored in localStorage (wrapped so private
  windows keep working); everything that belongs to the disc stays in the
  project file.
* The timeline is a view of the title, not a second editor: dragging a
  chapter mark writes the same chapter list as the chapter table, snapped to
  frames, and subtitle clips come from the same cue API as the cue editor.

## 36. Titles made of clips

* A title can list clips (file, in, out) instead of one source. They are
  joined inside the title's own ffmpeg run (one filter graph: cut with
  -ss / -t on each input, convert each clip to the disc format, concat), so
  no intermediate file is written for the disc and nothing is re-encoded
  twice.
* Each clip is converted on its own before the join, which is what lets
  clips of different sizes, frame rates and sample rates be joined; a clip
  without sound gets generated silence of its length.
* Clip lengths are rounded up to whole frames of the title (picture is held
  on its last frame if the file is shorter) and the sound is cut to exactly
  that length, so picture and sound meet at every join instead of drifting
  by up to a frame per clip. The chapter at clip *k* is the same rounded
  sum, so it lands on the first frame of the clip.
* Scan mode: all clips 23.976p film -> soft pulldown, all interlaced ->
  interlaced, otherwise progressive (joining field-based and frame-based
  pictures in one stream would need per-clip flags DVD players handle
  badly).
* One sound track per clip title: extra tracks would need their own
  timeline per clip, and AC-3 pass-through cannot be cut at arbitrary
  points. Both are rejected in validation rather than silently ignored.
* The app needs one file to show frames from and to play, so it asks the
  server for a joined preview (MPEG-4 + PCM at the disc size, cached by the
  clips and the disc format). The disc never uses that preview.
* Anything that needs a picture at a time of the title (menu thumbnails,
  poster frames, the simulator) maps the time to the clip playing then.

## 37. A built-in UDF + ISO 9660 writer

* Writing the image needed an external tool (hdiutil on macOS, genisoimage
  or mkisofs elsewhere), and xorriso — the one most often installed — cannot
  write UDF, which libdvdread players need. The image format is small and
  fixed, so oncemore writes it itself (udfwriter.py, standard library only)
  and the external tools remain as `--iso-tool` choices.
* Layout follows genisoimage `-dvd-video -udf`: ISO 9660 + UDF 1.02 bridge,
  VIDEO_TS first and in DVD order, every VIDEO_TS file at the sector the
  IFOs give (gaps zero-filled; genisoimage leaves uninitialised memory
  there), AVDP at 256 and at the end. The tests compare the sector of every
  file with genisoimage's image of the same folder and play the result with
  libdvdnav.
* Every input problem stops with an error and removes the partial image
  (labels, 8.3 names in VIDEO_TS, files over 1 GiB, missing IFOs, IFOs that
  contradict the file sizes). Hidden entries (the build's .work folder) are
  never written.
* One timestamp for every structure, so the same folder and date give a
  byte-identical image.

## 38. Menus, right-click menus and shortcuts

* Desktop authoring apps are driven from a menu bar, right-click menus and
  shortcuts as much as from panels, so the app has all three, built on one
  command list (app.js `COMMANDS`: what runs, when it is available, its
  shortcut). A command added there is available everywhere at once.
* Oncemore.app shows the Mac's own menu bar; its items call
  `window.oncemoreCommand(id)` in the page, and the page hides its own menu
  bar when the user agent says it runs inside the app. A test checks that
  every native item names an existing command.
* Shortcuts avoid keys browsers keep for themselves: workspaces are ⌥1–⌥4
  (⌘1–⌘4 switch browser tabs), chapter marks and playback use single keys (M,
  Space) only when no field has the focus. Undo in the native menu edits the
  focused field when there is one, otherwise the project.
* Delete from the keyboard only removes menu elements; titles, menus and
  playlists are deleted from a menu, with a confirmation.

## 39. Routing view and drag-to-link

* The routing drawn on the stage is not re-computed in the page: the server
  lays the menu out with the same code as the build (MenuBuilder.layout +
  navigation.compute) and returns each button's rectangle and up / down /
  left / right targets (`POST /api/routing`, cached with the simulator's
  layouts). What is drawn is what the disc will do.
* Linking by dragging uses a private drag type, so it never mixes with
  dropping files into the project; a drop on a button only changes its
  action, a drop elsewhere adds a button labelled with the item's name.

## 40. Transcode now

* Authoring apps let you encode ("transcode") assets while you are still
  designing menus, so the final build is quick. oncemore already had an
  encode cache keyed by everything a title's encode depends on; transcoding
  now just fills that cache ahead of time (`build.transcode`), and the build
  finds the results the same way it finds titles it encoded before.
* The key includes the title's share of the disc's bitrate, so adding a title
  or changing the disc size can make transcoded titles out of date (the mark
  in the project panel goes hollow again). A title with its own
  video_bitrate keeps its encode.
* The status (`build.encode_status`) never encodes or renders anything:
  slideshows that were not rendered yet count as not transcoded.
* The transcode uses the same 1- / 2-pass choice as the build; a 2-pass
  build does not reuse a 1-pass transcode.

## 41. Working the way disc authoring people work

* The name says it: oncemore brings back the tool many Mac users authored
  DVDs with. Its operating model was checked against that product's own
  published help (panel layout, tools, viewer controls, linking, shortcuts),
  and the app follows it where the model is a convention people know:
  menu bar order, a tools strip with selection / text / zoom, a viewer bar
  under the menu with safe area, routing and the normal / selected /
  activated highlight views, red outlines for overlapping buttons, a pick
  whip next to links, linking by dragging in the flowchart with unused items
  in their own row, and the same keys (V T Z, `*` for a chapter, PgUp / PgDn,
  ⇧Space preview, number keys and Home in preview, ⌘L, ⌥⇧ + number for
  workspaces).
* What is not taken: names, icons, artwork, screenshots, wording or files.
  The look stays ours (docs/DESIGN.md); a test keeps product names out of the
  app and the design docs.
* Shortcuts that browsers keep (⌘1–9, ⌘T, ⌘W …) are avoided; single-key
  shortcuts only act when no text field has the focus; ⇧Space is not a
  native menu key equivalent so it never takes the key from text fields.
* Overlapping buttons are still an error at build time; the editor asks the
  layout to collect them instead, so they can be shown while you fix them.

## 42. The classic look

* The first pass kept the operating model but drew its own look; that was
  not what people coming back to the tool expect. The look now follows the
  classic app as its published help shows it: the frame layout (Project /
  Menus / Timelines / Build, Monitor / Menu Viewer / Flowchart, Properties
  and Library / Layers on the right, the Timeline across the bottom), the
  Tools panel with the Workspace menu, tab strips with grips and close boxes,
  mid-grey panels, light text fields with dark text, right-aligned labels,
  amber timecode and the amber outline on the panel in use. The greys were
  measured from the help's screenshots.
* Still not taken: names, logos, icons, artwork or screenshots. The icons are
  drawn in app.js; the help's pictures were only looked at, never copied into
  the repository. A test keeps product names out of the app and design docs.
* Disc settings moved into Properties (select the disc: the Project preview
  or the Flowchart's disc), Build into the Project frame, the Project Preview
  into a window of its own. Undo / Redo, Check and Build left the top bar for
  the Edit and File menus and the Build panel; the theme and language moved to
  Edit > Preferences.
* The classic look is a skin, *Classic*; the default skin, *Modern*, keeps
  the same layout and controls with a current look (dark flat panels, dark
  fields, underlined tabs, blue for the panel in use and timecode). The
  choice is in Edit > Preferences and remembered per browser. Skins differ
  only in tokens plus a short block of Classic-only rules, so every feature
  works the same in both.

## 43. Replacing assets and editing designs elsewhere

* A file's uses are found by walking the whole project for strings that are
  paths of media files (by extension), not by a list of known fields: new
  fields that hold files are covered without touching this code. A label
  that happens to equal a path exactly would be replaced too; that is
  accepted.
* Edit menu in Photoshop opens the `.psd` with the program the system uses
  for it (`open` / `xdg-open`), only for existing files inside the project
  folder. The app then checks the file's modification time every two
  seconds and, when it changes, offers Import again instead of importing on
  its own: importing replaces the menu's pictures, and the person may still
  be saving in between.

## 44. Colour sets

* A DVD button subpicture has three pictures: the display image (always
  shown), the highlight and the select picture (swapped in inside the
  selected / activated button). The menu's colour set maps onto them
  directly: `normal_color` paints the buttons' shapes into the display
  image, `highlight_color` and `select_color` stay as before. All three take
  `#RRGGBBAA`; spumux turns the alpha into the DVD contrast (alpha >> 4, 16
  levels), checked on a built disc with spuunmux.
* One colour per state (not the classic app's two groups of three): the
  shapes oncemore draws are one colour each, and that is what keeps a
  button's pixels to the four colours a subpicture allows.
* Previews draw the selected button in its state colour and the others in
  the normal colour; the simulator gets the plain menu plus one picture per
  selected button, so it shows exactly that too.

## 45. Hidden layers and the template library

* `hidden` elements are removed when the project is read, before anything
  else sees the menu: layout, routing, graph, simulator and build all work on
  what is on the disc without each knowing about visibility. Routes to a
  hidden button are dropped and a hidden default button falls back to the
  first; hiding every button is an error.
* A saved template must outlive its project, so it is a folder with copies
  of the files it uses, in the user's data folder (not the project). Applying
  it copies them into the project's media/ folder (reusing an identical file
  of the same name, renaming otherwise) and turns links to things the
  project lacks into "stop", so the new menu is valid at once.

## 46. Project backups

* The app saves half a second after every edit, so a mistake is saved at
  once; Undo covers the session, backups cover the rest. The server keeps
  the file a save is about to replace, at most every five minutes, the last
  30 (`.oncemore-backup/`, hidden from the media list), and never fails a
  save because a backup could not be written.
* Reverting happens in the page, as one more edit (Undo brings the current
  project back), not on the server.

## 47. Inverse telecine

* Telecined film is 29.97i in which every fifth frame is made of fields of
  two film frames. Deinterlacing it keeps that frame (blended or combed)
  and stores 20 % more frames; matching the fields back together
  (`fieldmatch`), deinterlacing only what does not match (`yadif
  deint=interlaced`) and dropping the duplicate (`decimate`) recovers the
  film frames, which are then stored like 23.976p film (soft pulldown).
  On the test source this measured 39.6 dB against the original film after
  encoding, deinterlacing 35.6 dB.
* It is chosen, not detected: telling telecined film from video needs to
  look at many frames, and getting it wrong on real video would drop
  frames. `scan: ivtc` is NTSC only.

## 48. Resume buttons

* A player keeps resume information when the Menu or Title key leaves a
  title (and when a title's own `call` returns to a menu); the RSM command
  goes back to it. With none, players differ (libdvdnav stops), and after
  a title ended RSM would replay its last cell, so a `resume` button checks
  a flag first: 1 from a title's `<pre>`, 0 in its `<post>`. Every way from
  a title into a menu either stores fresh resume information (the keys) or
  runs the `<post>` (the flag is 0), so flag 1 always means "the title the
  keys left".
* With nothing to resume the button plays the first title, like a Play
  button; that is what the viewer wants at the start of the disc.
* The flag takes the first register the disc does not already use (g12,
  then down), so discs without a resume button are unchanged. Only a disc
  using every one (playlists, play all, Menu-key targets, a loop count and
  seven remembering menus) has none left; that is reported.
* A resumed title does not run its `<pre>`, so its Menu key opens the
  first menu rather than its own `remote_menu`. The simulator does the same.

## 49. Menu fade-in

* A transition into a menu is drawn into the menu's own video: the first
  `fade_in` seconds fade from black (and the sound from silence), and the
  loop point moves to the end of the fade, so it plays once and the
  repeats are the menu itself. No extra cells, PGCs or registers.
* The button subpicture starts with the menu, not after the fade: a
  subpicture that starts later lands near the cell boundary, and a repeat
  jumping to the second cell could miss it, leaving the menu without
  highlights. Buttons work during the fade.
* Fades between two particular menus (a dissolve from the menu you came
  from) would need a video per link; not done.

## 50. End-action overrides

* An override is per play, not per title, so it lives in a register: the
  button stores the override's number (1 = the first distinct override in
  the project), and each title's `<post>` checks it before anything else
  and clears it, so a title it then jumps to ends normally.
* Every other way of starting a title (title / chapter buttons without an
  override, play all, playlists, menu time-outs, the Title key) clears it;
  a resume keeps it, since it is the same play going on.
* It takes the next free register after the resume flag. Discs without
  overrides are unchanged.

## 51. Return to the last menu

* `lastmenu` is for the places where something ends: a title's or a
  playlist's end action and a button's override. A menu button or time-out
  would only find the menu it is on.
* Each menu's `<pre>` writes its number to a register; the end action
  routes there through the root menu like any menu end action. Before any
  menu was shown the register is 0, which the root menu reads as the Menu-key
  target (or itself), a sensible place to land.
* The register is handed out after the resume flag and the override, so
  discs not using it are unchanged.
* dvdauthor highlights button 1 in a menu that has no pre commands. A menu
  whose only pre command is this bookkeeping says `button = 1024` itself, so
  adding the register changes no highlight; the simulator follows the same
  rule (libdvdnav showed the difference).

## 52. Burning discs

* The burn uses what each system documents for writing an image: macOS
  `hdiutil burn` (with `-forceclose`, and its default verify after
  writing), elsewhere growisofs `-dvd-compat -Z device=image.iso`, which
  closes the disc too. A closed disc is what DVD players expect.
* It always burns the image the build just wrote, so the disc and the
  .iso are the same thing and the .iso stays for more copies.
* Windows burns images itself (Explorer: Burn disc image), so oncemore
  only points there.
* Tests use fake burners that record their arguments; no test burns.

## 53. Blu-ray

* oncemore writes the BDMV navigation files itself (index.bdmv,
  MovieObject.bdmv, playlists, clip information with the EP map); there is
  no free authoring tool to lean on the way dvdauthor serves DVD, and the
  files are small. The layouts follow what libbluray reads (and what
  tsMuxeR writes); the tests read every disc back with libbluray, including
  first play through the HDMV commands.
* ffmpeg encodes straight into BDAV transport streams (192-byte packets,
  the Blu-ray PIDs). Pictures are coded at a constant quality (x264 CRF,
  `bluray-compat`, level 4.1, 4 slices, one-second GOPs) capped at the rate
  that fills BD25 / BD50, so the disc never overflows and short projects
  are not padded with bits.
* The HD frame is 1920×1080. Film stays 23.976p; NTSC and PAL video become
  progressive frames in a 1080i stream at 29.97 / 25 fps, because Blu-ray
  has no 1080p at those rates.
* The EP map is built from the stream itself: every picture is one PES
  packet and key frames carry the random-access flag. Chapters are made key
  frames when encoding, and the marks sit on those frames.
* One playlist per title, per project playlist and for Play All; a movie
  object per playlist plays it and jumps to the next title when the end
  action names one. Without menus, any other end action stops; first play
  and the Top Menu key fall back to the first title when they name a menu.

## 54. Blu-ray images

* Blu-ray discs carry UDF 2.50 only (no ISO 9660), with the file system's
  own structures in a metadata partition. None of the image tools oncemore
  uses for DVD writes that portably (genisoimage and mkisofs stop at UDF
  1.02, xorriso has no UDF), so oncemore writes it, as it does UDF 1.02.
* Layout: the metadata file at partition block 32 and its mirror at the end
  of the partition, both in 32-block units with their Extended File
  Entries at partition blocks 0 and 1; the file set, directories and file
  entries inside it, the file data in between, one file after another. File
  entries reach the data with long_ad descriptors naming the physical
  partition.
* Tests check the structures and read every file back with libudfread, the
  reader libbluray opens images with, and play the image with libbluray.

## 55. Blu-ray subtitles

* ffmpeg cannot encode PGS, so oncemore writes the .sup stream itself and
  ffmpeg only muxes it (stream copy). Cues are drawn exactly as for DVD
  (white text, black outline on a transparent frame) at HD size; each
  pixel's lightness and opacity, 8 steps each, pick one of 64 palette
  entries that run from the outline to the fill colour. The arithmetic runs
  on whole rows as big integers, so it costs nothing next to drawing.
* Every cue is an epoch-start display set (composition, window, palette,
  object), cleared at its end; a cue ends 0.2 s before the next, the
  decoding gap players need (other authoring tools warn about too-close
  cues for the same reason). The stream begins with an empty composition
  at time 0 because ffmpeg starts every input at 0.
* The default track is switched on by a Set Stream command in front of
  Play PlayList; titles with subtitles but no default switch them off.

## 56. Blu-ray menus

* A menu is drawn by the same builder as for DVD, given a copy of the
  project whose disc is the 1920 x 1080 frame and whose menus are scaled
  to it (4:3 menus pillarboxed). One drawing code means the two discs'
  menus look alike, and everything a DVD menu can hold works on Blu-ray.
* The buttons are an Interactive Graphics stream in the menu's clip: one
  always-on composition, a button per menu button (in its own overlap
  group: buttons never overlap), whose selected and activated objects are
  the DVD highlight shapes in the highlight and select colours (and a
  normal object in the normal colour, when the menu has one). Keeping the
  DVD shapes keeps the look; Blu-ray just shows them in full colour.
* ffmpeg has no IG muxer, but it copies segment streams as PGS: the menu's
  .sup goes in at PID 0x1400 as such, and oncemore then marks it 0x91 in
  every PMT of the clip (fixing the section CRC); playlists and clip
  information list it as IG anyway.
* Menus are titles after the content titles. A menu object writes its
  title number to GPR 1 and plays its playlist; a still menu's clip is one
  second, held by the play item's still mode; a menu with motion or music
  plays again from its loop point (a mark) for ever. "lastmenu" is Jump
  Title to GPR 1. Buttons that start a chapter jump to a movie object made
  for that chapter (playlists cannot change from button commands).
* libbluray runs menus only when a player draws them: the tests register
  an overlay callback, read which button graphics are drawn in which
  colour, and press keys with bd_user_input / bd_menu_call.

## 57. Buttons after the intro

* dvdauthor writes a menu's highlight information into every VOBU of the
  program chain that has buttons, from its first VOBU on (dvdvob.c), so a
  later spumux start does not hold them back. A menu whose buttons wait for
  the loop point is therefore two PGCs: the intro (encoded on its own, no
  subpicture), whose post jumps to the next PGC, and the part with the
  buttons, which repeats. The menu's number is the intro's PGC, so every
  jump to the menu shows the intro again; the PGCs after it are numbered on.
  The buttons' PGC sets the starting button again (dvdauthor would give a
  PGC without commands button 1).
* On Blu-ray the buttons' composition is muxed at the loop point
  (ffmpeg's -itsoffset on the IG stream), so there are none before it.

## 58. Still pictures in timelines

* A picture in a title's clips is read by ffmpeg as a video of its length
  (`-loop 1 -framerate <title rate> -t <duration>`), so it goes through the
  same per-clip fit, frame trim and concat as a video clip, with silence for
  its sound. Its length is given (`duration`), not probed: a picture file has
  none of its own. It does not count when the title's scan mode is chosen;
  it takes the mode of the videos around it.
* `fill` crops the picture to the frame's display aspect before the usual
  fit (so nothing is padded); `fit` pads. The crop keeps even sizes, as the
  chroma needs.
* In the GUI a title whose only clip is a picture stays a clip title (a
  title's `source` must be a video).

## 59. Links to a menu button

* DVD: a jump cannot name a button, so the link puts the button (k * 1024,
  the SPRM 8 form) in a free GPRM (`entry_reg`, after the resume flag,
  override and last menu) and jumps as usual. Only the menus such links
  reach check it: their <pre> first sets the default or remembered button
  (always one: a <pre> without one would keep whatever SPRM 8 held), then
  takes the register's button if it is not 0 and clears it. With the
  buttons in a PGC after the intro, the intro checks without clearing and
  the buttons' PGC checks again and clears.
* Blu-ray: an IG page's default button always wins over the selected button
  (PSR 10) when a menu starts (libbluray graphics_controller.c, 5.9.8.3),
  so a linked menu's composition has no default (0xFFFF) and its movie
  object selects the button itself (Set Button Page): the one in GPR 2 if a
  link put one there, otherwise its default; then GPR 2 is cleared. The
  link sets GPR 2 (the button id: its index) and jumps to the menu's title.
* In the app, a link whose button is deleted or made into text falls back
  to opening its menu as usual.

## 60. End actions to chapters, playlists and play all

* A title's <post> can jump to a chapter of a title in its own titleset
  (`jump title K chapter N`), but not of another titleset: there the target
  gets a route number in g1 (2000 + its place in `end_chapters`) and the
  VMGM title menu, which can jump anywhere, takes it, like the playlist
  route (1000). That needs the VMGM menu, so a disc with several titlesets
  and no menu cannot have such end actions (reported).
* A playlist from an end action starts like one from a button (state and
  end-chapter registers, play all off) and jumps to its first item, through
  the playlist route when that item is in another titleset. Play all sets
  its flag and jumps to the first title.
* On Blu-ray every chapter any action names (not only buttons') gets its
  own movie object; that also covers a menu's end action to a chapter.

## 61. Blu-ray menu loops and end-action overrides

* A menu with a loop count counts its plays in GPR 3 inside its movie
  object: play, then while the count is below the loop count add one and
  play again from the loop point mark; then its end action (or nothing:
  the object ends, playback stops). A still menu then cannot hold its
  picture forever: its PlayItem uses still mode 1 with the menu's length
  as still time, after which the object goes on.
* Overrides work as on DVD with GPR 4: a button with an override sets it
  to k before it jumps, other buttons that start a title clear it, and a
  title's (and a chapter's) object checks it after playing: for k it jumps
  to override object k, which clears it and goes where the override says.

## 62. Slideshows fitted to their music

* The music's length is only known once it is probed, so a slideshow with
  `fit_to_audio` is fitted where the build probes its sources (and when the
  app renders it): the durations are scaled, then the title points at the
  render for those durations and its chapters move to the new starts. In
  the project file the durations stay what the author typed: proportions.
* The project's check that every picture outlasts the cross-fade is left
  to the fitting for such shows: it keeps each picture 0.1 s longer than
  the fade.
* Several pieces of music are each resampled to one format and joined with
  concat before the usual trim and fade-out.

## 63. Sources used as they are (`transcode: false`)

* The picture is copied (`-c:v copy`) into the DVD program stream; the
  sound still goes through the title's audio settings, so tracks, LPCM
  framing and 5.1 work as for any title. The check before building lists
  every reason a file does not qualify (codec, frame size including 704,
  frame rate or NTSC film, aspect, bitrate) instead of encoding anyway.
* The title keeps its own video rate in the disc plan (the stream's rate,
  else the file's), so the other titles share what is left.
* Chapter cells can only start on the copied GOPs, so a chapter starts at
  a key frame of the source rather than exactly at its time. Blu-ray needs H.264 and
  encodes such titles anyway (with a warning); an H.264 source that already
  is Blu-ray video is copied there (§77).

## 64. Slideshow transitions

* Every change between two pictures is either an ffmpeg xfade transition
  (cross-fade, dissolve, through black / white, wipes, slides, circles,
  radial, pixelate: all in ffmpeg 4.4 and later) or a cut (concat). A
  picture runs on for the transition's length only when a transition
  follows it, so the starts (chapters) stay the sums of the durations.
* `random` draws a kind for each change from a generator seeded with the
  number of pictures and the change's place, so a build (and its cache
  key) is the same every time.

## 65. Blu-ray pop-up menus

* The remote's Menu key has no per-title target on Blu-ray, but its
  Pop-up key opens the pop-up menu carried in the playing clip. So a
  title's `remote_menu` becomes its pop-up: an Interactive Graphics stream
  with a pop-up composition (user interface model 1) muxed into the
  title's clip, as libbluray reads it (ig_decode.c, graphics_controller.c).
* The video under a pop-up is the title, so the buttons must carry their
  own look: the menu is drawn on a transparent picture (no background;
  shapes overlaid, as drawbox leaves the alpha alone), each button's area
  of it is the normal state, and the same with the highlight shapes
  painted over in the highlight / select colours are the selected and
  activated states. drawtext and overlay blend onto transparent black, so
  the colours are divided by alpha again first.
* All objects share one palette of at most 255 colours: the channels are
  cut to fewer bits until the colours fit (the rarest then go to their
  nearest kept colour).
* Only what lies inside the buttons' areas appears: IG objects belong to
  buttons, and a non-button object covering the rest would overlap them.
* Buttons that only change streams also close the pop-up (Pop-up Off).

## 66. Slideshows advanced by hand

* Every picture is rendered as a moment of video (1 s, a chapter of its
  own) and then held: on DVD its cell has an infinite still (`pause="inf"`,
  which the player's Next / Play ends); on Blu-ray each picture is its own
  play item with still mode "infinite". Pictures change with cuts (a
  transition cannot be held half way) and there is no music (it would
  stop at every picture).

## 67. Titles from sound files

* A source with sound and no picture is a title like any other: the
  picture is the title's `picture` (or black) given to ffmpeg as one more
  input after the sound ones (so the audio graph's input numbers stay as
  they are) and fitted like a video frame; its signature is part of the
  encode cache key. Menu thumbnails of such a title show the picture (or a
  black box).

## 68. Link transitions

* A button's `transition` video plays between the press and the link. On
  a DVD it is a menu PGC of its own after the menus' (titleset 1): the
  button only remembers itself and jumps there; the PGC has no buttons and
  its <post> is exactly what the button would have run (streams, override,
  entry button, link). Staying in the menu domain keeps a menu-to-menu
  dissolve seamless, leaves "last menu" on the menu whose button was
  pressed, and needs no register.
* On a Blu-ray it is a title of its own after the menus' titles, whose
  movie object plays it and then runs the button's commands; the button
  jumps to that title.
* One transition per (video, link, override, streams): buttons that do
  the same share it. Each such program carries its own copy of the video
  (dvdauthor writes a PGC's VOB each time), so the bitrate plan counts it
  once per program. The video is fitted to the disc's picture like a
  title and encoded with its sound (or silence) like a menu.
* Not allowed on stream buttons, Resume or Stop: there is nothing to lead
  into, and a Blu-ray title in between would lose what Resume resumes.

## 69. One menu bar, the page's

* The menus are a list in the page (`MENUBAR`, items are `COMMANDS`, with
  submenus). The browser draws it; Oncemore.app makes its native menu bar
  from the same list, which the page posts to it (WKScriptMessageHandler)
  whenever it changes: its language, what can be done now (greyed items),
  what is on (ticks). Before, the app's menus were written out again in
  Swift and drifted from the page's (no View menu, English only, items
  enabled that did nothing).
* Only keys with ⌘ or ⌥ become native key equivalents: a plain V, T, Space
  or Delete in a menu would take the key from the page's text fields. The
  app keeps a few items of its own: New / Open project (the system's
  panels), Undo / Redo / Cut / Copy / Paste / Select All (they also work on
  text in fields; on objects the page gets the copy / cut / paste events),
  and the window items.
* Opening another project switches the folder the running server works on
  (`App.open`) rather than starting another server: one process, one
  token, and it works the same in a browser and in the app. Nothing
  switches while a build or transcode runs. The recent list lives with the
  user's settings (`ONCEMORE_CONFIG`, else Application Support / XDG config),
  never in a project.
* Save as copies the project folder (the project and its media) without
  what can be made again (output, caches, backups), then works there; the
  original stays as it was last saved. A project is a folder, so a copy of
  the project file alone would point at media it does not have.
* Exports (a menu or a frame as a picture, subtitles as SubRip) are written
  into `exports/` in the project folder, never over an earlier one: a page
  cannot save to an arbitrary place on disk, and the folder is where the
  person looks for the project's files anyway (Reveal shows it).

## 70. Remote keys turned off

* A title or a menu lists the remote keys it turns off by name
  (`prohibit`), the same names for both formats; each name stands for the
  user operations a player checks for that key (the Menu key is the root
  menu call and the other menu calls on a DVD, menu call and pop-up on a
  Blu-ray; the number keys are title, chapter and time play / search).
* dvdauthor writes no prohibited user operations, so the IFO files (and
  their .BUP copies) are patched after it: the 4 bytes at offset 8 of the
  title's program chain (one per title, in titleset order) and of the
  menu's (by menu number, with its loop program when the intro is apart).
  A title without number keys also says so in the title search table
  (UOP 0 and 1), which some players check before the program chain.
  Patching what dvdauthor wrote, at known offsets of the IFO tables, keeps
  dvdauthor as the author of everything else.
* On a Blu-ray the masks are written with the playlists: a title's or a
  menu's for its whole playlist; in a playlist or play all, each play item
  carries its own title's.
* The project names keys, not operation numbers: the person thinks "this
  notice cannot be skipped", and the same project builds both formats.

## 71. An MCP server for AI assistants

* `oncemore mcp` speaks the Model Context Protocol over stdio, written with
  the standard library (JSON-RPC, one message per line), like everything
  else at runtime: no SDK to install or keep up with.
* Both protocol eras: revision 2026-07-28 (every request carries its
  version and capabilities in `_meta`; `server/discover`; results say
  `resultType`) and the earlier revisions that open with `initialize`
  (2024-11-05 to 2025-11-25), which most clients still use.
* The tools are thin: they run the CLI's own commands (validate, simulate,
  preview-menu, import-psd, doctor) with a reporter that collects their JSON
  events, and the GUI server's App for saving (backups) and builds (one at a
  time, in the background, followed with build_status). An assistant gets
  exactly what the CLI and the app do, and nothing is implemented twice.
* Every tool names its project folder: no call depends on an earlier one
  (the protocol is stateless; a build job id is an explicit handle).
* A project is checked before it is written; an invalid one is refused with
  its issues as a tool error, which an assistant reads and corrects.
* Only folders inside the allowed roots (`--root`, default the home folder)
  are read or written; media are copied in, never linked from elsewhere.
  stdout carries protocol messages only: anything else that would print is
  sent to stderr.

## 72. Hardening from a code review

An outside review pointed at the parts most likely to break: Blu-ray
navigation, the encode cache, clip and slideshow timelines, and the app
server's resources. Each point was checked against the code, a test was
written that fails before the fix, and then the fix:

* **Blu-ray stream links.** A button that picks an audio or subtitle stream
  and plays a title set the stream, and then the title's start set its
  default subtitles over it. A register (5) now says "streams were just
  chosen"; the title start sets its defaults only when it is clear, and
  clears it. The registers in use (5 of 4096 general purpose) leave room.
* **`scan_m2ts`.** A packet whose PES header does not fit, or without a PTS,
  is not a key frame; a stream with no key frame is refused (an EP map
  pointing at nothing makes players seek wrong) rather than indexed.
* **Cache keys.** A menu's key covers what each thumbnail shows, not just
  the title's first file. The code hash covers every module that shapes an
  encode. Entries are written to a file of the writer's own and moved into
  place, so two builds storing one entry cannot mix. `--no-cache` means
  "encode again", so its results replace the old entries. Sources are still
  known by path, size and modification time (a hash of every source would
  read gigabytes before each build); a file replaced by one of the same
  size and time (`cp -p`) needs `--no-cache` or `oncemore clean`.
* **Frames.** Every place that turns a time into a frame uses one rule
  (the first frame at or after it, with a thousandth of a frame of slack):
  times are kept to the microsecond, and at 29.97 fps that rounding alone
  pushed a clip's chapter one frame late.
* **Chapters before lengths.** A title made of clips has a chapter at every
  clip, but the clips' lengths are known only when their files are read,
  after the project is checked. The number of chapters is known before
  (one per clip), so links and chapter menus are checked against it; the
  times are filled in later, and thumbnails that follow a chapter's start
  (rather than a time given in the project) move with them. Slideshows
  fitted to their music do the same.
* **Slideshow frames.** Each picture was rendered for a whole number of
  frames on its own, which adds up: a hundred five-second pictures at
  29.97 fps ended half a second late, with chapters a picture early. Each
  change is now on the frame nearest its time, counted from the start.
* **A picture used as it is** (`transcode: false`). The check now also
  refuses 4:2:2 MPEG-2, groups of pictures longer than DVD allows (read
  from the first minute's packet flags, nothing decoded), a VBR stream
  whose file rate shows it is over 9.8 Mbit/s (such a stream does not say
  its own rate), and a picture and sound that together pass the
  10.08 Mbit/s a player reads; it accepts half D1 (352 wide), which is
  DVD video. 23.976 film was accepted but went on the disc without
  pulldown flags, which dvdauthor marks as no DVD frame rate; it now gets
  them, as an encoded film does.
* **"The last menu" from another titleset.** The route back goes through
  the VMGM, where "no menu" (0) means the Title key, so a title in the
  second titleset that ended on "the last menu" before any menu was shown
  played what the Title key plays. It now asks for the Menu-key menu (or
  the first) there, as the simulator always did.
* **Subtitle colours.** A title's palette was counted with the subtitle
  style's colour even when every cue has its own, which refused subtitles
  that fit; it now counts the colours cues are drawn in.
* **Checked and fine.** The disc image writer splits files into extents
  under 1 GiB and was read back by libudfread across 1, 2 and 3 GiB and
  past 4 GiB, with non-Latin, long and punctuated names and deep folders;
  a name outside Unicode's first plane (an emoji) stays written as a
  surrogate pair, as decided for the writer (readers show it as two
  unknown characters, and libudfread cannot open it by that name).
* **App resources.** Previews are made two at a time (each is an ffmpeg);
  frames and waveforms are kept up to 64 MB, the oldest dropped first;
  finished jobs past the last 20 are forgotten; the state names the running
  job, so a page opened again follows it, and a page stops following a job
  the server no longer knows. Builds still cannot be cancelled from the
  page: stopping dvdauthor or a burn halfway leaves files a person must not
  mistake for a disc, so it waits for a design of its own.

## 73. Guides, rotate and flip

* Guides belong to a menu (`menus[].guides`), at pixel positions of its
  720-wide grid, as a Photoshop document keeps them, so a menu made from a
  file brings the file's guides (image resource 1032, in 1/32 pixel; a file
  without any keeps the menu's own). They are for the editor only.
* A guide is drawn twice: its line over every object (it takes no clicks)
  and a band to grab it under the objects. An object placed on a guide,
  the usual reason for having one, stays clickable where it covers it; the
  guide is grabbed anywhere it shows.
* An object's turn is stored as degrees clockwise about its centre and a
  flip made before the turn, the order a CSS transform and the renderer
  both apply. Object > Flip works on the screen's axes, so flipping a
  turned object also turns it the other way (a mirror image of a turn is
  the opposite turn of the mirror image).
* The renderer draws a turned object alone on a clear layer, cuts a square
  around its centre big enough for any angle, mirrors and turns it there,
  and lays it back: one way for texts, rectangles, pictures and buttons, on
  DVD and Blu-ray (whose menus are scaled copies of the same objects).
  Turning happens in square display pixels, as the person sees the menu,
  not in the DVD's narrow storage pixels.
* A turned button's highlight is its usual highlight (glyphs and underline,
  frame or picture shape) drawn on a layer and turned the same way by
  ffmpeg, so the lit area is exactly the turned button; its area on the
  disc is the box around it. A thumbnail does not turn with its button:
  the frame of a video still is not a design element, and its highlight
  frame stays with it.

## 74. Subtitle text scripts

* A text script (number, start and end timecode, text, more lines of text
  after it) is used as a subtitle track as it is, like the other formats,
  not converted on import: the file stays the one the subtitler delivered,
  and a corrected script replaces it. The app's subtitle editor shows it
  and converts it to SubRip when it is to be edited.
* Its timecode is the disc's: `hh;mm;ss;ff` is always NTSC drop frame (the
  semicolons say so); `hh:mm:ss:ff` counts frames of 30 on an NTSC disc and
  25 on a PAL one. A time with milliseconds (`hh:mm:ss,mmm`) is read too,
  since subtitle tools write that as well and it cannot be mistaken.
* "Relative" timecode, a script timed against a source that starts at
  01;00;00;00 and the like, is a track's `offset`, taken off every
  subtitle when the disc is made, for every subtitle format. The file is
  not rewritten, so its times still match the source's timecode sheet.
  Converting such a track to SubRip writes the times as the title shows
  them and drops the offset.
* Exporting a text script writes NTSC drop-frame timecode on NTSC discs
  (the semicolon form) and frames of 25 on PAL ones. A script has no
  position or colour, so those are not written.
* Show chapter names is a view setting of each open timeline, not part of
  the project.

## 75. Button numbers

* A button's number is its place in the menu's list: renumbering a button
  moves it there and the others close up, so numbers always run 1, 2, …
  without gaps, as a disc needs them. The ids (what links and the default
  button name) do not change.
* The offset is the menu's (`button_offset`), as on a disc: a DVD keeps one
  "button offset number" per highlight, in every navigation pack of the
  menu. dvdauthor writes 0 there, so the menu VOB is patched after it: each
  navigation pack names its VOB and cell (in its DSI), and the IFO's menu
  program chains name theirs, so only that menu's packs change.
* A Blu-ray button carries its own number for the number keys (its numeric
  select value); oncemore wrote none before, so number keys did nothing on
  a Blu-ray menu. It is now the button's place plus the offset.
* What a number key does differs: a DVD player selects and runs the button
  (libdvdnav has a call for just that); libbluray only selects it (and runs
  it if it runs on selection), one digit at a time. The simulator does as a
  DVD does; the app's preview takes two digits typed together, as players
  do.

## 76. DTS sound

* DTS is copied, never encoded: ffmpeg's DTS encoder is experimental, and
  the authoring apps this follows passed DTS through too. So `codec: "dts"`
  means the copy (`passthrough` is implied; `false` is refused), clips are
  refused (their sound is joined, so encoded), and the build checks that
  each track's stream is 48 kHz DTS with the channels the title declares
  (5.1 unless told; titles are grouped into DVD titlesets by them).
* The copy goes through ffmpeg's `dca_core` filter: plain DTS passes
  unchanged (the tests compare the stream's bytes), and a DTS-HD source
  gives its DTS core, which is what a DVD takes and what a Blu-ray's
  "DTS" stream type (0x82) means. DTS-HD as such would need its own stream
  types and is not offered.
* Its bitrate is the source's (1536k budgeted until measured); a DVD takes
  DTS up to 1536 kbit/s, so a higher rate is an error there.
* A DVD player need not decode DTS (the DVD format asks for an AC-3 or LPCM
  track alongside it), and oncemore keeps one format for all of a title's
  tracks, so a DVD title with DTS gets a warning. Blu-ray players decode the
  DTS core, so there is none there.

## 77. H.264 used as it is on a Blu-ray

* `transcode: false` already meant "this picture is ready for the disc" for
  a DVD; on a Blu-ray it now means the same for H.264 (it used to be
  ignored there, with a warning). A picture that does not qualify is still
  encoded, with a warning naming every reason: a project made for a DVD
  with MPEG-2 sources keeps building as a Blu-ray.
* What is checked is what ffprobe and the stream say: High or Main profile
  up to level 4.1, 4:2:0, 1920x1080 with square pixels, a rate oncemore
  writes (23.976 progressive; 25 and 29.97 as 1080i), a key frame at least
  every second (the entry points and chapters need them), at most
  40 Mbit/s. 1080i needs a stream coded for fields, which ffprobe does not
  tell (a progressive picture coded as 1080i reads "progressive"), so the
  sequence parameter set's frame_mbs_only_flag is read. What is not checked
  (slices per picture, the buffer model, B-pyramid) is left to the encoder
  that made the file.
* An MP4 or MKV keeps the parameter sets aside and the SEI in the pictures;
  ffmpeg's conversion to a stream put them after the SEI, one even before
  the access unit delimiter. ffmpeg's own decoder then complains about a
  buffering period naming an unknown SPS, and a Blu-ray stream wants
  AUD, SPS, PPS, SEI, slices. So the delimiters are dropped, the parameter
  sets put at the start of every key picture, and the muxer starts each
  picture with a new delimiter (`COPY_BSF`); the tests decode the copy to
  the source's very frames and read that order back.
* Chapters land on the copied key frames (at most a second off, as on a
  DVD), and the plan keeps the copied picture's rate so the encoded titles
  share what is left.

## 78. Image scripts

* Authoring tools take subtitles as pictures too: the same numbered script
  with a picture file in place of the text. oncemore reads it as a text
  script whose text is just a picture's name (relative to the script); a
  name with more text, or a second line, stays text, so a script can mix
  both.
* Pictures for subtitles are usually made with a flat background colour
  instead of transparency; one without any transparency has its top-left
  colour keyed out (ffmpeg's colorkey), one with transparency is used as
  it is.
* A frame-sized picture (480, 576, 720 or 1080 lines) is the whole frame,
  scaled to the disc's; a smaller one keeps its size in square pixels (on
  a DVD squeezed to its pixels, as the text is) and sits where text
  would, centred at the margin.
* Colours are the picture's own, reduced by keeping the commonest and
  giving every other pixel the nearest of them: three per picture on a DVD
  (the fourth is transparent), 255 with eight opacity steps on a Blu-ray.
  A DVD title's subpictures share 16 colours; text colours are checked
  before the build, pictures' only once they are drawn, so a title over
  the limit stops the build with the count.
* The app imports a script and its pictures together (several files): they
  land side by side in media/, which is what the script's names need.

## 79. The web version

* Authoring apps used to export the disc for the web as well. oncemore's is
  a static folder: `index.html`, a small player (`oncemore/webplayer/`,
  copied as it is) and `disc.js` with what the player needs to know. A
  script file rather than JSON so that `index.html` works opened from the
  folder (browsers do not fetch files from a file:// page).
* The menus are drawn by the same code as the disc's (MenuBuilder): the
  first frame scaled to square pixels, and the buttons' highlight shapes
  for all buttons on one transparent picture that the player clips to the
  selected button. A motion menu, or a still menu with sound, is an MP4 of
  one loop; the player loops it from the loop point and counts the loops.
* The titles are encoded with the Blu-ray path's inputs (clips, slideshows,
  music titles) into H.264 / AAC MP4 at 720 lines: what every current
  browser plays. Browsers switch sound tracks inconsistently, so only the
  first goes in, and DVD subpicture colours have no web counterpart, so
  subtitles are WebVTT text (picture subtitles are left out, with a
  warning).
* The player follows the rules of simulate.py (itself checked against
  libdvdnav on built discs), in JavaScript. The test builds a disc with a
  playlist, a transition and subtitles and presses the same seventeen keys
  in the simulator and in the player in a browser, comparing the domain,
  menu, button, title and chapter after each.

## 80. Closed captions

* A DVD carries line-21 captions inside its video: user data after every
  GOP header ("CC", then a word pair per field for each of the GOP's
  frames), which the player sends to line 21 of its analogue output or
  decodes itself. ffmpeg's encoder writes captions only in the ATSC form,
  from captions it decodes; so the title's picture goes to an elementary
  stream (the path soft pulldown already took), the user data is inserted
  after each GOP header, and the stream is muxed with the sound. The
  titleset's video attributes say "line 21, field 1" (dvdauthor's
  caption="field1").
* A Scenarist file is the format caption tools write: CEA-608 byte pairs
  with a timecode, used as they are. Anything else is read as subtitles
  and made into pop-on captions, the usual way for prerecorded video: each
  is loaded into the hidden memory after the previous one went up (its
  "end of caption" swaps the memories), shown at its start and erased at
  its end; one with too much text to load in time is shown late, with a
  warning. The basic character set is ASCII with a few accented letters;
  anything else becomes a space (with a count in the warnings).
* Captions follow frames at 29.97 per second. A film title with soft
  pulldown has 23.976 coded pictures, two or three fields each, which the
  DVD form counts differently, so it is refused rather than mistimed.
* The tests read the captions back with ffmpeg's own decoder (lavfi's
  subcc on the built VOB): the text, and the times to within a GOP, since
  the decoder takes a GOP's captions at its start.

## 81. My styles

* The Library already had built-in text looks (outline, shadow). Authoring
  apps also keep the user's own: save the look of an object, give it to
  others, in any project. oncemore's styles live next to the user's menu
  templates ($ONCEMORE_STYLES, or "styles" beside the template library),
  one folder each with its properties and a copy of its font, so a style
  keeps working when the project it came from is gone.
* A style is the look only: font, size, colour, outline and its width,
  shadow and its offset. Applying it replaces those on texts and buttons
  (properties the style does not have are cleared, so the result is the
  style, not a mix); a shape has only a colour and takes that. The font is
  copied into the project's media/ the first time, reused after, and a
  different file of the same name is kept with the style's beside it.

## 82. The layer break

* A dual-layer DVD-Video is written opposite track path, and the player
  jumps between the layers once; the picture may hold still for a moment
  there, so authoring apps let the author place it, at a chapter. oncemore
  takes `disc.layer_break` (a chapter, or auto: the first one past the
  middle of the disc) and only for DVD9.
* The rules: the break is on an ECC block (16 sectors), the first layer is
  at least as large as the second, and no larger than a layer of a DVD-R DL
  (2,085,856 sectors, half its 4,171,712; a DVD+R DL layer is a little
  larger, so this fits both). The chapters and their sectors come from the
  IFO files (the titles' chapter table, their program chains' cells, the
  title VOBs' place in the titleset), read from the image itself, so images
  from any ISO tool are checked the same way.
* A chapter's sector depends on everything before it, which dvdauthor
  decides. Rather than pad the video, the built-in writer moves the whole
  of VIDEO_TS by up to 15 sectors: the IFO addresses are relative to
  VIDEO_TS.IFO, so nothing inside changes, and the chapter lands on an ECC
  block. Images from other tools are taken as they are; a chosen chapter
  that does not fit is an error that says to use the built-in writer or
  another chapter. With auto and nothing that fits, a warning: the burner
  then folds the disc in the middle, as it did before.
* The sector goes to growisofs (`-use-the-force-luke=break:N`). hdiutil has
  no such option, so on macOS the burn warns and leaves it to hdiutil.
  `oncemore burn` finds the break in the image when it is not given one.
* A real DVD-9 image is over 4.38 GiB; the tests build the small sample
  disc as if a layer held one sector, check that every chapter sector is a
  navigation pack, that the break is on an ECC block, and that libdvdnav
  still plays the moved image.

## 83. Paragraphs

* Menu text was one line per text. A description, credits or a list of
  extras on a menu is several lines, lined up the same way, so a text can
  hold newlines, with `align` (left, centre, right) and `line_spacing`
  (pixels added between the lines). x is still the left edge of the whole
  paragraph, so changing the alignment moves the lines, not the paragraph.
* The menus are drawn with ffmpeg's drawtext, which takes the lines as they
  are (`line_spacing`) and lines them up within the paragraph with
  `text_align` (ffmpeg 6.1 on). With an older ffmpeg the paragraph is drawn
  left-aligned, with a warning, rather than measured and drawn line by line.
* Only texts: a button label stays one line, since the button's highlight
  is cut from the label's own pixels and the remote moves between labels.
* The tests draw a long line over a short one and check where the short
  one's pixels are for each alignment, and that the spacing moves the
  second line down by as much.

## 84. Menus with pages

* A menu of many buttons (a long list of extras, a scene index) is spread
  over pages that the viewer turns with a button. A menu gets `pages`, and
  each of its buttons, texts, rectangles and pictures a `page`, or none:
  then it is on every page (a heading, a background shape, the buttons that
  turn the pages). Buttons go to another page with `page:next`,
  `page:prev` or `page:<n>`; next from the last page goes to the first,
  and prev from the first to the last, so one NEXT / PREV pair on every
  page is enough.
* On the disc each page is a menu of its own, `<id>~<n>` after the first
  (the menu's id is page 1, so every link to the menu still opens it
  there). The pages are expanded when the project is read, so the DVD,
  the Blu-ray, the web version, the simulator, the flowchart and the
  checks all see ordinary menus and need nothing of their own. `~` cannot
  be in an id a project gives, so a page never clashes with a menu.
  `menu:<id>:<button>` opens the page that holds the button.
* Blu-ray menus could hold the pages in one interactive composition
  (pages of one IG stream). The menus are separate titles here, as on the
  DVD: turning a page restarts the menu's background, which a menu whose
  pages share a still picture does not show. One page per title keeps the
  Blu-ray writer as it is; pages within one composition can come later
  if a menu needs them (a moving background that should not restart).
* A page's buttons are numbered on their own (the remote's number keys,
  `button_offset`), the default button is used on the page that has it,
  and a button may only route to buttons of its page or of every page.
* In the editor the viewer shows one page at a time, with a page strip in
  its bar; Menu > Add new page makes the next page with a BACK button (and
  a NEXT where the page before has none; the first time, the menu's
  buttons become page 1's); Delete page removes the page shown and what
  is on it alone. New objects go on the page shown; Properties > Page
  moves one to another page or to every page.
* Menus from a Photoshop file with a layer group per page are not done
  yet: each page there has its own artwork, which needs a background per
  page.

## 85. Random and shuffled playlists

* A playlist can play its items shuffled (each once, in a random order) or
  at random (as many items as it has, each picked at random, so one can
  come twice and another not at all), as the classic apps' chapter
  playlists did on Blu-ray and the web; a DVD plays them as listed, as
  they did there too (with a warning when one is set).
* The Blu-ray format has its own playlist playback types for this, but
  libbluray (and so VLC, mpv and Kodi) reads them and plays the items in
  order anyway, so the disc does it with commands, which every HDMV player
  runs: each item becomes a playlist file of its own (after the titles'),
  and the playlist's movie object counts the items played, picks one with
  the random-number command (Set RND), plays it, and goes again until it
  has played as many as there are; for shuffle it keeps a register per
  item and picks again when the item was played already. Then the
  playlist's end action, as before.
* The web version shuffles or picks in the player the same way.
* The tests read the object's commands, and play discs built both ways in
  libbluray from first play: shuffle plays the three items once each,
  random three items from them. libbluray seeds its random numbers from
  the clock, and the orders seen differ from run to run.

## 86. Slideshows of more than 99 pictures

* A slideshow takes up to 999 pictures, as many chapters as a Blu-ray
  playlist can mark. A DVD title has at most 99 chapters, so there the
  pictures after the 98th are part of chapter 99, with a warning, as the
  classic apps did; a slideshow advanced by hand has a chapter (and a
  still) per picture, so on a DVD it is refused past 99.
* The slideshow is drawn by one ffmpeg graph with every picture an input
  of its own, which does not scale to hundreds (open files, memory). A
  show of more than 60 pictures is drawn in pieces of 60: each piece
  begins where the transition into its first picture ends (the piece
  before draws that, with the start of the picture), and the pieces are
  joined frame by frame into the same lossless video. Joining them by
  stream copy (the concat demuxer) put frames out of place, so they are
  decoded and joined by the concat filter, FFV1 again.
* The tests draw a show of 13 pictures at once and in pieces of 4, with
  cross-fades, cuts across the joins, random transitions and pan & zoom,
  and compare every frame (framemd5): they are the same. A 120-picture
  show built as a DVD has 99 chapters (libdvdnav) and as a Blu-ray 120
  (libbluray).
* That test found pan & zoom pictures one frame short each: zoompan makes
  its frames at the disc's rate already, and the fps filter after it
  dropped the last one. It is left out after zoompan now.

## 87. The bit budget

* The size estimate was one number. The classic apps showed where the
  space goes, so the plan now keeps its parts: each title (its length,
  video rate as planned, audio rate, and bytes with the packet overhead),
  the menus, the disc's own files (the IFO reserve) and what is left.
  The parts add up to the estimate the plan already made, so the bar and
  the number agree.
* On a Blu-ray the pictures are encoded at a constant quality up to a peak
  rate, so a title's part is the most it takes, not what it will take.
* Check Project shows a bar of the whole disc (titles in turn, menus, disc
  files) and a table; `oncemore validate` prints each title's rates and
  size, and the free space. Changing a title's bitrate (Properties) and
  checking again shows the effect before anything is encoded.

## 88. The media cache folder

* The media cache was always `<project>/.oncemore-cache`. Encodes of long
  titles fill a project's drive, so the classic apps let the cache live
  anywhere; now Preferences > Media cache (or ONCEMORE_CACHE) chooses a
  folder, kept in this computer's settings (settings.json next to the
  recent projects list), not in the project.
* Each project gets its own folder in it, named after the project folder
  with a hash of its full path: two projects of the same name do not
  share one, and `oncemore clean` still removes one project's cache only.
  (The cache keys are content keys, so sharing would be safe; keeping
  them apart keeps clean and the sizes simple.)
* Everything that writes to the cache asks settings.cache_dir: encodes,
  slideshows, joined clips and the editor's playback copies. A slideshow
  fitted to its music used to find the project from its render's path
  (three folders up); it now keeps the render's folder, wherever that is.

## 89. Chapters at scene changes

* Chapters usually go where the scene changes. ffmpeg scores how much each
  picture differs from the one before (the select filter's scene score,
  0 to 1); the pictures over a threshold are cuts. It runs on a 320-wide
  copy of the picture, which is enough to see a cut and much quicker.
* Sensitivity low, medium and high are thresholds 0.5, 0.35 and 0.2. Cuts
  closer than a gap (10 s by default) to the one kept before, or to the
  start, are dropped, so a flash or a quick montage does not become a run
  of chapters.
* A title made of clips is looked at clip by clip (only the part of each
  file it uses), and the cuts are placed on the title's time line. The
  dialog finds them first and says how many chapters that makes; OK puts
  them in, replacing the chapters there are or adding to them, as Add
  chapter points at intervals does.
* `oncemore scenes` lists them for a file; the editor's server has
  POST /api/scenes.

## 90. Bold, italic, letter spacing and kerning

* drawtext draws one font file. Bold and italic text is drawn with the bold
  or italic face of the font's family, another file: oncemore reads the
  family name and the weight and italic bits (the `name` and `OS/2` tables)
  of the fonts next to the chosen one and of the family's installed fonts
  (fontconfig), and picks the face. A family without that face is an error
  at the media check that says which face is missing; the editor greys out
  Bold or Italic for such a family. Making a face up (drawing over itself,
  slanting) is left out: it never looks like the real one.
* drawtext has no letter spacing, and kerns by itself. With letter spacing,
  or kerning off, the characters are drawn one by one: each where the
  font's advances put it (`hmtx`), plus its kerning pairs when kerning is on
  (the `kern` feature of `GPOS`, PairPos formats 1 and 2, or a `kern`
  table), plus the spacing. Every character sits on the baseline drawtext
  gives the whole text: the first line's top at y, its baseline that line's
  ascent below, and the lines a pitch apart, both read off two small
  renders. So a text drawn one by one with no spacing lands where drawtext
  draws it (the same box, tested). Characters drawn alone are not shaped
  together: scripts that join their letters should keep spacing 0 and
  kerning on.
* Letter spacing is in pixels, like line spacing; Blu-ray menus scale both
  with the text. A saved style carries the four, and the bold or italic
  face file with its font.
* The editor's stage loads the face file when it is in the project
  (otherwise the browser makes one up) and uses CSS letter-spacing and
  font-kerning. Font names in the stage's style attributes are now in single
  quotes: in double quotes they cut the attribute short, and a text with its
  own font lost its font, alignment and outline on the stage.

## 91. Button highlights: own pixels, frame, line or a drawn shape

* A button's highlight is one of four styles, for text and image buttons
  alike: `shape` (its own pixels: the letters, or a picture's opaque
  pixels), `frame`, `underline` (text buttons) or `drawn`. Text buttons kept
  their look (letters and a line under them) as the default, image buttons
  theirs (a frame), so no project changes.
* `drawn` is a rectangle or an ellipse on the 720-wide grid
  (`highlight_area`), filled or a 3-pixel outline like the frames. It is the
  whole highlight and the button's area (what the remote's arrows and a
  pointer go by), the way a highlight layer drawn in an image editor is. An
  ellipse is made as rows of runs, not by ffmpeg, so DVD, Blu-ray (scaled
  with the menu) and the web version get the same shape. A turned button's
  drawn highlight stays as drawn: the person drew it where it is.
* A highlight picture (`highlight_image`) and a drawn highlight are one or
  the other; the editor clears one when the other is chosen. Moving the
  button (drag, arrows, align, duplicate, X/Y) moves its drawn highlight
  with it; dragging the dashed shape itself, or its corner, moves or sizes
  only the highlight.

## 92. VIDEO_TS is written by vtskit, not dvdauthor

* The IFO files, the navigation packs, the menus' button subpictures and
  highlight information and the titles' subtitle streams are written by
  oncemore's copy of [vtskit](https://github.com/kajisho5/vtskit)
  (`oncemore/_vendor/vtskit`, LGPL-3.0-or-later, by the same author), so
  dvdauthor and spumux are no longer needed. vtskit writes what dvdauthor
  wrote, byte for byte where it can be compared (its tests do), and plays
  back the same under libdvdnav; it also writes what dvdauthor cannot
  (angle blocks).
* The navigation keeps dvdauthor's command language: `author.py` writes
  the same texts as before (`g1 = 1; call menu entry root;`) and
  `vtskit.lang` compiles them for the domain they run in, to the commands
  dvdauthor compiled. The whole description is still put together as
  dvdauthor's XML, kept in the work folder as `navigation.xml`: a readable
  record nobody runs. Buttons of several commands, the pads for jumps into
  another titleset's chapters (what dvdauthor called jumppads, built here
  from `vtskit.lang.Disc.vmgm_pads` / `vts_pad`) and the default `exit`
  of a menu without post commands all come out as dvdauthor's did.
* `videots.py` turns the project into vtskit's titles and menus: the
  menus' buttons from `menu.py`'s layout (areas, arrow keys, the shapes
  that light up as the overlay), the colours converted to Y/Cr/Cb as
  spumux converted them (alpha >> 4 is the contrast), the remote keys a
  title or menu turns off and the menus' button offsets written straight
  into the IFOs and navigation packs (no patching afterwards), a title's
  stills and cell commands as before.
* Subtitles: `subtitles.stream_xml` still renders each cue to a 4-colour
  PNG and writes the stream's XML (the same record as before);
  `mux_streams` reads them back and muxes them with `vtskit.subtitles`,
  which places each unit where spumux did and writes the same bytes. The
  title's 16-colour palette is gathered from the cues' PNGs in the order
  the colours are first used and given to the title's program chain.
* A menu's cached stream no longer carries its subpicture (vtskit adds it
  when the disc is written), so the encode cache's version went to 2.
* Still from the tools: ffmpeg/ffprobe, and an ISO tool if the built-in
  writer is not wanted. libdvdnav stays a test-only dependency.

## 93. Multi-angle titles

* A title's `angles` are more video files of the same scene; the source is
  angle 1. dvdauthor could not write angle blocks; vtskit interleaves them
  (units of about a second, each angle's VOBUs in turn) and points every
  unit at the next unit of every angle, so a player switches without a
  break and a jump lands in the right angle.
* The angles must line up VOBU for VOBU, so each is encoded exactly as the
  title is: the same bitrate, frame rate, GOP grid and chapter key frames,
  the title's own sound tracks (so the sound does not jump when the picture
  does), and cut to the title's length and to exactly as many pictures as
  the title's stream has (vtskit refuses angles whose GOPs or lengths
  differ); a shorter angle is refused at validation. (ffmpeg 8 stamps a
  PTS on the first picture of a packet only; vtskit times the others from
  their display order, else the last picture went uncounted and the two
  streams seemed a frame apart.) Subtitles are muxed into every angle's stream, so they stay
  on when the angle changes.
* Angles are DVD only (a Blu-ray build warns and leaves them out), and a
  title made of clips, a slideshow, or one whose picture is copied as it is
  (`transcode: false`) cannot have them. Each angle is encoded and cached
  as a title of its own (`<id>-angle2.mpg`, ...).

## 94. Sources with a variable frame rate

* Phones and screen recorders write video whose frames come at uneven
  intervals. A tool that lays such frames end to end at the disc's fixed
  rate puts the picture out of step with the sound, more and more as the
  title goes on; it is a long-standing complaint about the classic apps
  (forum threads on Blu-ray builds that lose sync, with workarounds and no
  fix).
* oncemore needs nothing special for it: ffmpeg encodes to the disc's rate
  (`-r`) from each frame's own time, repeating or dropping frames where the
  intervals are uneven, and the sound is taken from the same source in the
  same run. `tests/test_vfr.py` holds it to that: a source whose frames come
  every 1/60, 1/30 and 1/20 s, with flashes and beeps together, built for
  DVD (NTSC and PAL) and Blu-ray; each beep must be within 40 ms (just over
  an NTSC frame) of its flash, with no drift from the first to the last. A
  copy made the naive way (every frame at a fixed 1/29.97 s) is already
  110 ms off 6 s in, so the test would see it.

## 95. Right click and modifier keys on a Mac

* A right click is the second button, or Control-click on a Mac (a
  one-button mouse; a trackpad's two-finger click already comes as the
  second button). It opens the shortcut menu of what is under it and
  selects that unless it is already in the selection. It never adds to a
  selection, takes from it, starts a drag, seeks the timeline or moves a
  guide, a splitter or a chapter mark. Before, Control-click on a Mac was
  read as a click to add to the selection, and the menu that followed
  acted on that changed selection.
* Adding to a selection is Shift-click, and ⌘-click on a Mac or Ctrl-click
  elsewhere, as in the classic apps and the Finder. The "mod" of shortcuts
  is ⌘ on a Mac and Ctrl elsewhere. On a Mac, Control is a key of its own,
  so Control+D does not duplicate.
* In the Mac app, a right click where oncemore has no menu shows nothing,
  not the web view's Reload / Back menu. Text fields keep their own menu
  (Copy, Paste). A browser keeps its menu everywhere oncemore has none.
* `tests/test_rightclick.py` plays a Mac by giving the page a Mac platform
  and the events a Mac sends for Control-click (pointerdown with Control
  and the first button, then contextmenu).

## 96. Dragging and dropping as the classic apps' help describes it (1)

The help of the classic authoring apps lists what a drag does with each key
held. oncemore follows it where it has the same objects:

* **Assets onto a menu** (from the Project panel):
  * A video makes a title, and a button for it where it lands. On a button,
    that button plays the new title. With Alt (⌥), it is the menu's motion
    background and no title is made.
  * A picture is placed where it lands. With Alt, it is the background (on
    an image button: that button's picture).
  * A sound is the menu's music.
  * A layered Photoshop file makes a menu from its layers.
  * A video made into a title this way takes its source's chapter marks,
    as "Title from file" does.
* **Chapters**: a chapter in the Timelines panel (or on the timeline) is a
  link source like a title. Drag it onto a button, or reach it with the pick
  whip. The Timelines panel keeps the last title opened while a menu is
  open, so its chapters are there to drag.
* **On the menu**:
  * A box dragged on empty space selects what it touches. With Shift, ⌘ or
    Ctrl held, it adds to the selection. A click on empty space clears the
    selection.
  * Alt-drag leaves the objects where they are and drops copies. Copied
    buttons get new ids and automatic routing.
  * Shift-drag moves only across, down or at 45°. Snapping then works only
    along that line, so the line stays straight.
  * Shift / ⌘ / Ctrl-click still adds to the selection or takes from it.
    Pressing on an object adds it at once, so a Shift-drag moves it with the
    rest; a click without moving takes a selected object out.
  * Before, Alt held while dragging turned snapping off. Alt is now the
    copy, so turning snapping off moved to ⌘ (Ctrl elsewhere). The help says
    nothing about a key for that; snapping is otherwise View > Snap.
* **Files from the Finder**: a layered Photoshop file dropped into the
  window becomes a menu, as it does in the classic apps. With Alt, it is
  only imported, as a picture.
* `tests/test_encore_drag.py` checks each of these in a browser. Playwright
  cannot hold Alt during its own drag, so those drops are sent as the
  browser would send them, with the key held.
* The rest is listed in the ROADMAP; the Timeline viewer and resize
  handles are §97.

## 97. The Timeline viewer's keys, and resize handles (2)

From the same tables of the classic apps' help ("Keys for working in the
Timeline Viewer", "Keys for working in the Menu Viewer"):

* **The current-time indicator** follows a click or a drag in the ruler or
  the picture track. Home goes to the start and End to the last frame. ← / →
  move one frame, and so does the wheel with ⌘ (Ctrl elsewhere). The wheel
  alone scrolls the timeline sideways.
* **Chapters and poster frames**:
  * Shift+8 adds a chapter. It is matched by the key, not the character,
    so it works on keyboards where Shift+8 is not `*`; the keypad's `*`
    still works.
  * ⇧* on the keypad or ⌘⇧8 / Ctrl+Shift+8 sets the poster frame of the
    chapter the indicator is in, as Timeline > Set poster frame does.
  * ⌘⌥-drag (Ctrl+Alt) from a chapter mark puts that chapter's poster
    frame where it is let go, inside the chapter. The mark itself stays.
* **Zoom**: ⌘. (Ctrl+.) and the keypad's + / − zoom the timeline. The help
  also gives ⌘, for zooming out. oncemore keeps ⌘, for Preferences, as every
  Mac app does, so the keypad − and the zoom buttons are how to zoom out.
* These keys are not in the menus (the help says the same of its tables).
  They are handled by the page, so the Mac app's menu bar does not see
  them.
* **Resize handles**: a single selected rectangle or picture shows eight
  handles. Dragging one resizes the object from the opposite side. With
  Shift it keeps its proportions; with Alt (⌥) it grows or shrinks around
  its centre. A turned object has no handles; its size is set in
  Properties. Text and buttons are sized by their type, which is not done
  by handles yet.
* Ripple delete (Shift+Backspace) and slipping a clip's sound (Alt-drag)
  have no counterpart. A timeline of clips is a list of parts of files
  (each with its own in and out) played one after another. There are no
  gaps to close, because removing a clip already closes up the rest, and
  each clip's sound belongs to its picture, so there is nothing to slip.
* `tests/test_encore_timeline.py` and `test_encore_drag.test_resize_handles`
  check each of these in a browser.

## 98. Flowchart drops, routing arrows, text in place and small keys (3)

From the classic apps' help ("Add elements to the Flowchart", "Set button
routing", and the keyboard tables):

* **Flowchart**:
  * A title, menu or playlist dragged in from the Project panel links by
    where it lands. On the disc, it is first play. On a title or playlist,
    it is that item's end action. On one of the buttons listed under a menu,
    that button plays it. On the menu itself, a new button for it goes under
    the last one. On empty space, nothing happens.
  * The pick whip drawn from one of those button rows links that button
    directly, without asking which.
* **Routing**: with routing shown, an arrow dragged onto another button
  sends that remote key there. It is stored in the button's `nav`, and so it
  is drawn solid, as one set by hand. The help also turns automatic routing
  off for the menu first. oncemore has no such switch: what is set by hand
  wins, and the rest stays automatic.
* **Text in place**: double-click a text, or a button's words, to type in
  it. Esc or a click elsewhere ends it and keeps what was typed; on a
  button, Enter ends it too. While typing, keys go to the text, so Backspace
  does not delete the object.
* **Show menu layers**: Ctrl + right click (⌘-Control-click on a Mac) lists
  the objects under the pointer, top first, to pick one that is covered.
* **Small keys**:
  * In the Project panel, when it is the panel in use, ↑ / ↓ go to the item
    above or below. A title, menu or playlist opens as it is reached, which
    is how a click works in oncemore; an asset shows its properties. Home /
    End scroll to the top or bottom.
  * A tool key (V, R, T, Z) held down for a moment chooses the tool only
    while it is held, then the one before comes back. A quick press keeps
    the new tool.
  * In the preview, Space plays and ⌘← / ⌘→ (Ctrl elsewhere) go to the
    previous or next chapter. The arrows alone still move between buttons.
* **Not taken over**:
  * The Direct Select (A) and Move (M) tools: they pick a single layer
    inside a button's layer set. oncemore's buttons are single objects.
  * Resizing the preview with ⌘= / ⌘−: the preview follows the window.
* `tests/test_encore_flow.py`, `tests/test_encore_keys.py` and
  `test_encore_drag` (routing arrow, text in place) check these in a
  browser.

## 99. Reordering by drag, and handles on text and buttons (4)

* **Reordering by drag**: a slideshow's slides, a timeline's clips, a
  playlist's items and a menu's layers can be dragged to a new place in
  their list, as in the classic apps' panels. ▲ / ▼ stay.
  * A row is grabbed by a part that is not a field or a button.
  * It lands at the place of the row nearest the pointer. Slides are a grid,
    so this works across as well as down.
  * The click that ends a drag does not also choose the row.
  * Layers move only among their own kind. Their order is the stacking
    order, and for buttons the order of the button numbers.
* **Handles on text and buttons**: a single selected text or button has
  four corner handles. Dragging one scales the object with its
  proportions: a text's or a word button's type size follows, and a picture
  button's width follows. The opposite corner stays put, or with Alt the
  centre does. Rectangles and pictures keep their eight handles (§97).
* **Selecting in a text**: while typing in place (§98), double-click
  selects a word and triple-click a paragraph, as the page does natively.
  The help's four and five clicks (paragraph, all) are not added: ⌘A / Ctrl+A
  selects all the text.
* `tests/test_encore_reorder.py` and `test_encore_drag.test_type_handles`
  check these in a browser.

## 100. Blu-ray at 720p, and AVCHD's 1440×1080 as it is

* A Blu-ray had one picture: 1920×1080, with 25 and 29.97 frames a second
  coded as 1080i. A 50p or 60p source (sports, games, phones) lost every
  other frame. `disc.bluray.video: "720"` (Build > Picture) makes the
  whole disc 1280×720 progressive at twice the disc's rate: 59.94 for
  NTSC, 50 for PAL. Film stays 23.976p. Every picture of a 60p source
  stays, and so does every field of a 1080i one: bwdif already gives a
  picture per field, and the rate filter keeps them all at 59.94.
* It is a setting of the disc, not of a title. Titles, menus, pop-up menus,
  subtitles and link transitions all use the same frame, so no playlist
  (Play All, chapter playlists) mixes 720p and 1080 pieces. Mixing
  resolutions inside one playlist is left alone: oncemore has not checked
  what players do with it.
* The codes in the clip and playlist files come from libbluray's
  `bd_video_format_e` / `bd_video_rate_e`, read in its `bluray.h`
  (code.videolan.org/videolan/libbluray): 720P = 5; 23.976 = 1, 50 = 6,
  59.94 = 7 (1080I = 4, 1080P = 6, 25 = 3, 29.97 = 4, as before).
* A 720p stream has no fields, so x264's fake-interlaced flag is only set
  for 1080i. A key frame still comes at least every second (60 pictures
  at 59.94).
* A picture copied as it is (`transcode: false`) may now also be AVCHD's
  1440×1080 H.264 with 4:3 pixels (at 1080i or 1080p, the same codes as
  1920×1080). On a 720 disc only 1280×720 at 50 / 59.94 (or 23.976) is
  copied; anything else is encoded, with the reason as a warning, as
  before.
* Still missing (ROADMAP): SD on Blu-ray (720×480 / 576), 24.000p, and
  MPEG-2 Blu-ray video.
* `tests/test_bd720.py` builds a 720 disc from a 59.94p and a 1080i
  source, with a menu, a pop-up menu and subtitles. It checks:
  * every stream is 1280×720 at 60000/1001;
  * each picture moves on from the one before (a 29.97 source shown twice
    alternates about 2 and 0.02 there; the test asks for more than 0.3);
  * the subtitles' composition is 1280×720;
  * libbluray reads the codes as 720p 59.94.

## 104. Subtitle scripts as subtitling houses deliver them

The classic app's manual (pp. 136–138) names three script forms besides the
plain text script: the image script with a `Display_Area` and a `Directory`
line, the FAB image script, and scripts saved as UTF-16. oncemore read the
plain forms only.

* **Image script headers**: `Display_Area (left top right bottom)` before
  the first subtitle sets where every picture of the script is drawn;
  `Directory <path>` names the pictures' folder. The manual's path is
  absolute and written on the computer that made the script (a Windows
  `C:\...` path in its example), so it is tried first and the script's own
  folder after it; the GUI imports the pictures next to the script.
* **FAB image scripts**: one line a picture, `name start end left top right
  bottom`. Encore asks for the pictures' folder on import; oncemore takes
  them from the script's folder (the project keeps them together). A file
  name may hold spaces: the line is read from its end. A `.txt` script is
  a FAB script when its first line is in that form.
* **The place**: the numbers are frame pixels, 720 × 480 for NTSC and 720 ×
  576 for PAL in the manual; the picture is scaled into that rectangle (a
  delivered picture is usually that size already). On a Blu-ray the frame
  is the HD frame and the rectangle is scaled with it, as a frame-sized
  picture already was. A script whose numbers go past the DVD frame is read
  as 1920 × 1080. A picture without a place is drawn as before (frame-sized:
  the whole frame; smaller: centred at the margin).
* **UTF-16**: a byte order mark, or a NUL in nearly every other byte (UTF-16
  without one), selects UTF-16; other files are tried as UTF-8, Shift_JIS
  and Latin-1 as before.
* Written back (the subtitle editor's Export as text script), pictures that
  each have a place are written as a FAB script, so the places survive.
* **Map Colors** (eyedroppers choosing a picture's background, fill and
  outline for the colour set) is not taken over: oncemore keeps a picture's
  own colours (§78), keying out the corner colour of a picture without
  transparency.
* `tests/test_subtitle_deliveries.py` reads the manual's examples (headers
  with a Windows folder that is not there, FAB lines with a space in a
  name, UTF-16 with and without a byte order mark) and builds a DVD with a
  UTF-16 FAB track and a Display_Area track, checking the picture's colour
  inside its rectangle and nothing at the bottom centre.

## 101. The disc's starting audio track, and subtitles off from the start

* A disc with several audio tracks played whichever the player picked (its
  language setting). An audio track marked `default` now starts the disc,
  as `subtitles[].default` already did for subtitles (§18). It is set once
  at first play (DVD: `audio = n` in the first-play program; Blu-ray: a Set
  Stream for the primary audio in the first-play object). A viewer who
  changes the track later, by remote or with a menu button, keeps it.
* Track numbers are the same on every title (§18), so the first title with
  a default track decides it, as for subtitles. One default per title.
* `disc.subtitles_off` starts a DVD with subtitles off (`subtitle = 0`)
  instead of the player's language choice. A subtitle track marked
  `default` wins over it. A Blu-ray title that has subtitles already sets
  its own default, or none, as it starts (§55), so a Blu-ray starts with
  them off either way.
* The simulator starts with the same streams.
* Still to come (ROADMAP): a menu's default button following the audio or
  subtitle track playing, streams per playlist item, and playlists inside
  playlists. The first needs the player's stream registers in a menu's
  commands; that is left until it can be checked against libdvdnav and
  libbluray.
* `tests/test_default_streams.py` checks the commands. It also builds a
  DVD read with libdvdnav (English audio, the second track, and subtitles
  off) and a Blu-ray read with libbluray (audio stream 2 before the title
  plays, no subtitles shown). The DVD check fails without the change.

## 102. More source formats: .m2v, .mp2, .mpa, .wma, .gif, .tga

The classic app's manual lists sources oncemore turned away or could not
read. ffmpeg decodes all of these; what was missing was in oncemore.

* **`.m2v`** (an MPEG-2 video elementary stream, often delivered apart from
  its AC-3) is a title's `source`, its sound in `audio_tracks`. Such a
  stream has no container, so two things read from the container are
  wrong or missing:
  * its length: ffprobe gives none. `encode.probe` then takes the end of
    the last packet (the larger of its pts and dts, plus its duration).
  * its rate: ffprobe's `avg_frame_rate` is the raw demuxer's default
    (25), whatever the stream says. For the raw formats (`mpegvideo`,
    `mpeg1video`, `h264`, `hevc`, `m4v`) `r_frame_rate`, the rate in the
    stream's own headers, is used.
* **`.mp2`, `.mpa`** (MPEG Layer II) and **`.wma`** are sound sources like
  any other and are made AC-3 (or the disc's codec).
* **`.gif`** and **`.tga`** are stills: menu backgrounds, slides, clips,
  the picture of a sound-only title and image-script subtitles. ffmpeg's
  gif demuxer has no `-loop`, so a looped still goes through the image2
  demuxer with the gif decoder (`tools.still_input`), which reads the first
  picture. An animated GIF therefore shows its first picture, as a still
  should. Browsers draw GIF but not Targa (nor TIFF in most), so the editor
  gets those as PNG from `/api/file`.
* **PICT** is left out: ffmpeg has no decoder for it.
* `tests/test_source_formats.py` builds a DVD from all of them (the `.m2v`
  with three separate tracks and a GIF image-script subtitle, a GIF menu
  background, a Targa and a GIF slide) and checks the streams, the length
  and the rate.

## 105. The libraries are made in their own repositories, released, and copied in

The disc formats live in four libraries, each in its own repository and on
PyPI: vtskit (DVD-Video IFO/VOB), udfkit (UDF / ISO 9660 images), bdmvkit
(Blu-ray BDMV) and dvdcc (line-21 captions). oncemore itself is not put on
PyPI; it ships as the Mac app and GitHub releases.

* **Where work happens**: a change to a disc format is made, tested and
  released in the library's repository (a version bump on its `main`
  publishes it: `.github/workflows/release.yml`, trusted publishing).
  oncemore then takes the release. A fix is not made in oncemore's copy.
* **How oncemore takes it**: `tools/vendor.py <library> --pypi <version>`
  (or `--pypi` alone for the latest) copies the release's wheel into
  `oncemore/_vendor/<library>`. The wheel's SHA-256 must be the one PyPI
  publishes and `__version__` inside it the version asked for; only the
  package's `*.py` and its licence files are taken (vtskit: COPYING.LESSER;
  udfkit and dvdcc: LICENSE and NOTICE; bdmvkit: COPYING and
  COPYING.LESSER). `UPSTREAM` names the version, the wheel and its digest.
  `tools/vendor.py <library> <checkout>` copies a clean, pushed checkout
  instead, for work not released yet; `UPSTREAM` then names the commit.
  `tools/vendor_vtskit.py` stays as the name vtskit's README gives.
* **Why a copy, not a dependency**: oncemore installs with no dependencies,
  the Mac app carries one Python tree, and a disc built today is built by
  the same library code tomorrow.
* vtskit's copy was refreshed from PyPI 0.1.0; its modules and licence are
  byte-for-byte those of commit f2098cd, which it replaced, so only
  `UPSTREAM` changed. udfkit, bdmvkit and dvdcc are still oncemore's own
  modules (`udfwriter.py`, `udf250.py`, the Blu-ray writer, `captions.py`);
  each is replaced by its library's copy in a change of its own, with the
  output checked to be the same.
* `tests/test_vendor.py` reads either form of `UPSTREAM` and runs the PyPI
  path on wheels made in the test (no network), each library with its
  licence files.

## 106. Disc images written by udfkit

oncemore's UDF writers (`udfwriter.py` for DVD-Video, `udf250.py` for
Blu-ray, `udfinfo.py` to read the names back) were the code udfkit was made
from. udfkit 0.1.0 is now on PyPI, so oncemore carries it
(`oncemore/_vendor/udfkit`, §105) and the three modules are gone.

* `oncemore/discimage.py` is where oncemore calls it: `write_dvd`,
  `plan_dvd` (the layer break), `write_bluray` and `volume_names`, with
  udfkit's `UdfError` raised as `OncemoreError`, as the old modules raised.
* The images are the same but for udfkit's name: the UDF implementation
  identifier is `*udfkit` (was `*oncemore`) and the ISO 9660 application
  identifier `UDFKIT` (was `ONCEMORE`). Checked by writing a DVD and a
  Blu-ray folder through the old writers and through udfkit with the same
  date: every other differing byte is the tag checksum or CRC of a
  descriptor that holds one of those identifiers.
* The tests of the writers (`test_udfwriter`, `test_udf250`,
  `test_udfinfo`) stay and now test the copy oncemore carries; library
  calls raise `UdfError`. `test_promises` checks for udfkit's writer inside
  the package, as it checked for oncemore's.

## 103. Typesetting menu texts: boxes, vertical text, underline

The classic app's manual describes paragraph text in a box, vertical text
and underline / strikethrough for Japanese menus. drawtext lays out one
line of characters left to right and nothing more, so oncemore lays the
text out itself (`oncemore/typeset.py`, `MenuBuilder._wrapped`,
`_vertical`, `_lines`) and hands drawtext lines or single characters.

* **Line breaks** (`width`, or `height` when vertical): a line may break at
  a space between words, between two Japanese or Chinese characters, or
  inside a word only when the word alone is wider than the box. A character
  that may not start a line (stops, closing brackets, small kana, the long
  vowel mark, iteration marks; JIS X 4051's line-start prohibited classes
  without the optional ones) takes the character before it to the next line
  (oidashi); an opening bracket at the end of a line goes down with what
  follows. There is no hanging punctuation (burasage) and no justification:
  the lines are left, centred or right as `align` says. Widths come from the
  font's advances and kerning pairs (`fontfaces.Font.offsets`), the same
  numbers letter spacing already uses.
* **Vertical text**: each line is a column, the first on the right. Each
  character is drawn alone in a square of the font size, centred across
  the column, letter spacing added down the column; columns are as far
  apart as the same text's lines would be across (line spacing added), so
  a vertical paragraph is as open as a horizontal one. drawtext cannot use
  a font's `vert` substitutions, so punctuation and brackets are drawn as
  the characters of Unicode's Vertical Forms and CJK Compatibility Forms
  blocks (︒ for 。, ﹁ for 「, ︱ for ー ...) when the font has them, and
  as they are otherwise. Small kana are moved by a tenth of the size to the
  upper right of their square, near where `vert` puts them in the CJK
  fonts tried (Noto Sans CJK); this is an approximation, not the font's own
  vertical glyph. Latin letters and digits stay upright, one per square.
  The square's baseline is 0.88 of the size below its top, the ideographic
  em box of CJK fonts (typo ascender 880 of 1000).
* **Underline / strikethrough**: a bar of the text's colour, a fifteenth of
  the size thick: under each line just below the baseline, or through it
  at 0.3 of the size above the baseline; in vertical text on the right of
  each column (the side Japanese puts a sideline on) or through its middle.
  The bar has no outline or shadow.
* **Formatting part of a text** (one word bold or coloured) is not done:
  a text has one style. It stays in the roadmap.
* The editor shows the same layout with CSS (`writing-mode: vertical-rl`,
  `line-break: strict` in a box of the text's width, `text-decoration`).
  The browser uses the font's own vertical glyphs and line-break rules, so
  small details can differ from the disc; the build is what counts.
* Blu-ray menus scale the box with the rest of the menu.
* `tests/test_typeset.py`: the line-break rules, the vertical forms, the HD
  box, ink measured on drawn menus (lines inside the box, a full-width bar
  under or through the letters, two columns of the right lengths, right to
  left), and the Properties fields and the stage in a browser.

## 107. Closed captions written by dvdcc

oncemore's `captions.py` was the code dvdcc was made from. dvdcc 0.1.1 is on
PyPI (0.1.1 added UTF-16 subtitle files, which oncemore already read: the
change was made there first, §105), so oncemore carries it
(`oncemore/_vendor/dvdcc`) and `captions.py` is now a wrapper over it:
`load` and `inject_file`, with dvdcc's `CaptionError` raised as
`ProjectError`, as the old module raised.

* dvdcc reads subtitle files with its own copy of the subtitle parsers.
  oncemore's `subtitles.py` keeps its own (it also draws the subpictures
  and reads image scripts' `Display_Area`, `Directory` and FAB scripts,
  which dvdcc has not). Captions are text, so an image script carries none:
  one of plain lines gave no captions before and gives none now; one that
  opens with `Display_Area` or `Directory` gave no captions without a word
  and is now refused at that line. A FAB script is refused the same way.
* Checked by loading SubRip, WebVTT, ASS, drop-frame and non-drop text
  scripts, a Scenarist file, a UTF-16 and a Shift_JIS file, each with and
  without an offset and at the top and the bottom, through the old module
  and through dvdcc: the same frames and the same notes. The same schedules
  written into one MPEG-2 stream give byte-identical files.
* `test_captions` now tests the copy oncemore carries, and checks that a
  file dvdcc refuses reaches the project check as a `ProjectError`.

## 109. New library releases are taken by a pull request opened every day

The libraries are released on their own (§105), so oncemore can fall behind
them without anyone noticing. `.github/workflows/library-updates.yml` runs
every day (00:17 UTC) and by hand:

* `python tools/vendor.py --outdated` lists each carried library whose
  latest PyPI release is newer than the copy's `__version__` (versions
  compared number by number: 0.10 is newer than 0.9; a library oncemore does
  not carry yet is left out).
* For each, unless the branch `library/<name>-<version>` is there already,
  it copies the release in with `tools/vendor.py <name> --pypi <version>`
  (the wheel checked against PyPI's SHA-256), pushes that branch and opens
  a draft pull request. Nothing is merged by it.
* A pull request opened with `GITHUB_TOKEN` does not start CI on its own
  (GitHub makes such runs wait for approval); `workflow_dispatch` is the
  exception, so the workflow starts `ci.yml` on the branch and its checks
  show on the pull request.
* Opening pull requests needs the repository setting "Allow GitHub Actions
  to create and approve pull requests" (Settings > Actions > General >
  Workflow permissions); without it the step fails and says so.
* A release that changes an API or the bytes oncemore writes needs a change
  in oncemore too: it is made on the same branch before merging, with its
  DECISIONS entry.
