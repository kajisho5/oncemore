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

## Phase 2 — Mac GUI

A native menu editor that uses the CLI as its backend (`--json` events for
progress, `preview-menu` for rendering, the project file as the document):
drag buttons onto the menu, set chapters on a timeline, live preview,
one-click "Make ISO".

## Phase 3 — richer discs

* Subtitles: SRT → spumux subpictures, several languages
* Multiple audio tracks (languages, commentary), 5.1 AC-3 pass-through
* Video backgrounds and motion menus, menu transitions
* Several titlesets (mixed aspect ratios / audio formats on one disc)
* "Play all" playlists and resume-aware returns

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
