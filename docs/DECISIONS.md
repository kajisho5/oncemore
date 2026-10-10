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
