# Roadmap

oncemore is built in layers: a scriptable core (this repository, phase 1) with a
stable project format and machine-readable CLI output, and user interfaces on top.

## Parity with professional DVD authoring tools

Goal: everything a disc made with the classic professional authoring apps
(the ones Mac users relied on until they were discontinued) can do on a
DVD-Video, oncemore can do too — without copying their names, files or look.
Each milestone is one pull request with tests (unit, libdvdnav navigation,
browser) and lands only with green CI.

**P1 — Menu timing and the remote control** (done)
- [x] Menu loop count (`loop`: forever or *n*), loop point for motion menus
  (intro once, then loop from *t*), and a menu end action after the last loop
  (timeout to a title / menu / play all)
- [x] Default button per menu; each menu remembers the last button used
- [x] Auto-activate buttons (selecting runs them)
- [x] Menu key target per title, Title (top menu) key target per disc; the Menu
  key also works in titles outside the first titleset

**P2 — Playlists and chapters** (done)
- [x] Playlists: any sequence of titles and chapter ranges with their own end
  action, reachable from buttons (`playlist:<id>`)
- [x] Chapter names and poster frames, used by chapter menus

**P3 — Menu design** (done)
- [x] Text styles: font per element, outline / shadow; decorative rectangles
- [x] Editor: multi-select, align / distribute, snapping guides, arrow-key
  nudge, duplicate / copy-paste
- [x] Custom highlight layers (a picture whose pixels are the highlight)
- [x] Menu templates (main, scene selection, setup) to start from
- [x] Animated (video) thumbnail buttons in motion menus

**P4 — Content and encoding** (done)
- [x] Slideshows: pictures with durations, cross-fades, pan & zoom, music
- [x] WebVTT / ASS input; top / bottom placement and colour per track and per cue
- [x] Subtitle editing in the app
- [x] Encode cache (unchanged titles and menus are not re-encoded) and
  per-title quality (bitrate) settings
- [x] Interlaced output for interlaced sources; soft 3:2 pulldown for 23.976p film
- [x] AC-3 pass-through
- [x] DVD-ROM content (extra files next to VIDEO_TS on the disc)

**P5 — Seeing and checking the whole disc** (done)
- [x] Flowchart of the navigation (menus, titles, playlists and their links)
- [x] Project check: unreachable titles / menus, dead ends, missing end actions
- [x] Disc simulator in the app: a remote control that drives menus,
  highlights, titles and end actions before anything is encoded

**P6 — Bringing existing designs** (done)
- [x] Layered PSD menus using the common layer-name convention (button layer
  groups, highlight layers, thumbnail placeholders)

**P7 — The workspace** (done)
- [x] Design system: tokens (colour, type, spacing, shape, motion), dark and
  light themes, a style guide page, checks that keep components on the tokens
- [x] Panel workspace: Project / Library, editor with a Timeline (picture,
  chapters you drag, audio and subtitle tracks), Properties / Layers,
  workspaces in the top bar, resizable and remembered panels

**P8 — The disc image without extra tools** (done)
- [x] oncemore's own UDF 1.02 + ISO 9660 writer, the default ISO backend:
  no hdiutil / genisoimage / mkisofs needed; same layout as genisoimage on
  the test discs, checked with isoinfo, xorriso and libdvdnav

**P9 — Titles from several videos** (done)
- [x] A title made of clips (parts of several files with in / out points),
  joined while encoding, a chapter per clip; clip editor and timeline in the
  app, joined preview, simulator and menu thumbnails follow the clips

**P10 — Menus and shortcuts** (done)
- [x] A menu bar with every command; the Mac
  app's native menu bar runs the same commands
- [x] Right-click menus for project items, media files and menu elements
- [x] Keyboard shortcuts and a list of them (?)

**P11 — Linking and routing on the menu** (done)
- [x] Button routing drawn on the menu, as computed for the disc
- [x] Drag titles, menus and playlists onto buttons to link them, or onto the
  menu to add a linked button

**P12 — Transcode now** (done)
- [x] Encode titles ahead of the build (app and `oncemore transcode`), with a
  transcoded / not yet mark per title; the build reuses them
- [x] Sound waveforms on the timeline

**P13 — Working like a disc authoring app** (done)
- [x] Menu bar order File / Edit / Object / Menu / Timeline / Window / Help
  (also in the Mac app), Object commands (align, distribute, arrange, convert)
- [x] Tools strip (selection, text, zoom, preview) and a viewer bar (zoom,
  safe area, routing, highlight states of all buttons, overlap outlines)
- [x] Pick whip for links; linking by dragging in the flowchart; unused items
  in their own row; preview from the current menu with number / Home / End keys
- [x] The usual shortcuts (V T Z, + −, `*`, PgUp / PgDn, ⇧Space, ⌘L, ⌥⇧1–4)

**P14 — The classic look and panel layout** (done)
- [x] Mid-grey panels on a near-black ground, light text fields, amber outline
  on the panel in use, amber timecode, tabs with grip and close box
- [x] Tools panel with the Workspace menu and search; Project · Menus ·
  Timelines · Build | Monitor · Menu Viewer · Flowchart | Properties and
  Library · Layers; the Timeline across the bottom, always there
- [x] Project panel with a preview of the selection; Monitor transport bar;
  Properties with right-aligned labels; flowchart cards with pictures;
  New Project dialog; Project Preview window; View menu; Edit > Preferences
  (skin, brightness, theme, language)
- [x] Two skins: Modern (default, a current flat dark look) and Classic (the
  classic look above)

**P15 — Authoring conveniences** (done)
- [x] Chapter points at intervals; Replace asset (relink a missing file
  everywhere it is used); File > Project settings; Window menu items for
  every panel; Edit menu in Photoshop with a notice when the file is saved

**P16 — Menu colour sets** (done)
- [x] Normal / Highlight / Activated colours with opacity (16 DVD levels);
  the Normal state is the subpicture's display image, shown on every button
  that is not selected; previews and the simulator compose it as a player does

**P17 — Menu tools** (done)
- [x] Layer visibility (hidden elements stay in the project, not on the disc)
- [x] Save menu as template: a per-user template library with copies of the
  files a menu uses; My templates in the Library; Create chapter index

**P18 — Project safety** (done)
- [x] Automatic versions of the project file (.oncemore-backup, every five
  minutes at most, the last 30) and File > Revert to a saved version

**P19 — Inverse telecine** (done)
- [x] `scan: ivtc` for film already telecined to 29.97i: field matching and
  decimation back to 23.976 film frames, stored with soft 3:2 pulldown

**P21 — Resume** (done)
- [x] Resume buttons (`resume`): back to where the Menu / Title key left the
  title, or the first title when there is nothing to resume

**P22 — Menu fade-in** (done)
- [x] A menu can fade in from black (picture and sound) when it starts,
  once; repeats start after the fade

Not planned: copy protection of any kind (never); DDP masters. Multi-angle
titles are left for later.

## Phase 1 — core CLI and project format (done)

* `project.oncemore.json` + JSON Schema
* `init`, `validate`, `build`, `iso`, `preview-menu`, `doctor`, `--json` output
* 2-pass MPEG-2, AC-3 / LPCM, automatic bitrate, letterbox/pillarbox
* Still menus with drawtext labels, spumux highlights, automatic navigation,
  generated chapter menus with thumbnails, frame-accurate chapters
* End-to-end tests including button presses through libdvdnav

## Phase 2 — the authoring app

Done (as a local web app, `oncemore gui`):

* Media bin with drag & drop, titles with a frame-accurate scrubber and
  one-click chapters, chapter-menu switch
* Menu editor: drag buttons and text over the background, pick targets,
  colours, remote navigation; exact server-side preview with hit areas
* Check (size estimate, issues) and Build (ISO / folder) with live progress
* Autosave, undo/redo, English/Japanese UI
* Oncemore.app: a native macOS window around the same UI with bundled Python,
  built for Apple silicon and Intel by the release workflow (notarised once a
  Developer ID is configured)
* Title playback (cached H.264/WebM proxy), ▲/▼ ordering of titles and menus,
  image buttons (frame or shape highlight)

Next:

* Playback preview of menu navigation (titles play since the proxy preview)
* Multi-select, alignment guides and snapping in the menu editor
* Drag-and-drop reordering in the sidebar (▲/▼ buttons exist)

## Phase 3 — richer discs

Done:

* Subtitles: SRT → 4-colour subpictures via spumux, several languages, default-on track
* Multiple audio tracks with language tags (other files or other streams)
* Menu buttons that switch audio / subtitle streams (`audio:<n>`, `subtitle:<n|off>`)
* Motion menus (video background, its sound or separate music)
* Several titlesets: titles with another aspect ratio or audio codec on one disc
* "Play all" (`playall` buttons / first play) that keeps single-title returns
* 5.1 AC-3 audio (`audio.channels: 6`)

Still to do:

* Transitions between particular menus (dissolves), animated buttons

## Phase 4 — web version

ffmpeg.wasm plus the authoring core compiled to WebAssembly, so a browser can
produce the ISO locally without uploading anything. Needs the built-in writers
below.

## Phase 5 — Blu-ray

First menu-less BDMV (titles + chapters), then IGS menus.

## Later

* Replace dvdauthor with a built-in IFO/VOB writer.
* Built-in UDF 1.02 + ISO 9660 bridge writer, so no external ISO tool is
  needed on any platform (xorriso cannot write UDF; see DECISIONS.md).
