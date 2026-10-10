# Roadmap

oncemore is built in layers: a scriptable core (this repository, phase 1) with a
stable project format and machine-readable CLI output, and user interfaces on top.

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
* Title playback (cached H.264/WebM proxy), ▲/▼ ordering of titles and menus,
  image buttons (frame or shape highlight)

Next:

* A native macOS wrapper (.app with a WKWebView around the same UI, signed and
  notarised) so it starts like any Mac app, without a terminal
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

Still to do:

* 5.1 AC-3 pass-through (today everything is down-mixed to stereo)
* Menu transitions, animated buttons
* "Play all" playlists and resume-aware returns
* Per-cue subtitle position/colour, ASS input

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
* Telecine / inverse telecine for film sources.
