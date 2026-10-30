---
name: oncemore
description: Author DVD-Video and Blu-ray discs with real menus, chapters, playlists and subtitles from finished video files, with oncemore (a Mac app over a scriptable CLI and an MCP server) - make a project, check it, render a menu to PNG, press remote keys in a simulator, then build a VIDEO_TS or BDMV folder, a playable .iso image or a version that plays in a browser, and burn the image to a blank DVD or BD only when asked. Use when the user wants a DVD or Blu-ray made, a disc menu or chapter menu, a disc image (ISO), a disc for testing a set-top player, or chapter suggestions from a video's scene changes. Local and offline, Python 3.11+ and ffmpeg with drawtext (check with oncemore doctor). Not for editing, grading or mixing the videos, and never copy protection.
---

# oncemore

oncemore turns video files into a DVD-Video or Blu-ray disc with menus. A
**project** is a folder holding `project.oncemore.json` (the only input; schema
in `oncemore/project.schema.json`) and the media it uses, usually in `media/`.
Two ways in, the same engine behind both:

* the **CLI**: `oncemore <command> ... --json` (`python -m oncemore` from a
  checkout). Install: `pip install git+https://github.com/kajisho5/oncemore`
  (it is not on PyPI).
* the **MCP server**: `oncemore mcp`, registered once with
  `claude mcp add --scope user oncemore -- oncemore mcp`. Prefer it when it is
  connected: its tools read and write the project JSON for you and refuse an
  invalid project before writing it.

Run `oncemore doctor --json` first. `ready: false` (exit 3) means ffmpeg,
ffprobe or ffmpeg's `drawtext` filter is missing; tell the user and quote
the install hint from the output.

## CLI commands

`<project>` is a `project.oncemore.json` file or the folder holding it.

| Task | Command |
|---|---|
| Check the tools | `oncemore doctor --json` |
| Sample project (two titles, a menu, a chapter menu; media made with ffmpeg) | `oncemore init <dir> [--standard NTSC\|PAL] [--aspect 16:9\|4:3] [--force] --json` |
| Player test disc, with `TEST-CHECKLIST.md` | `oncemore testdisc <dir> [--format dvd\|bluray] [--standard NTSC\|PAL] [--aspect 16:9\|4:3] [--force] --json` |
| Check project, media and size plan | `oncemore validate <project> [--no-media] [--format dvd\|bluray\|web] --json` |
| Look at a menu | `oncemore preview-menu <project> --menu main -o main.png [--button ID] [--state highlight\|select\|normal] [--outline] --json` |
| Press the remote (no encoding) | `oncemore simulate <project> --keys down,enter,menu [--simple-layout] --json` |
| Menu from a layered Photoshop file | `oncemore import-psd <project> design.psd --menu main [--first-play] --json` |
| Chapter suggestions | `oncemore scenes video.mp4 [--sensitivity low\|medium\|high] [--min-gap SECONDS] --json` |
| Encode titles ahead of the build | `oncemore transcode <project> [--title ID] [--fast] [--status] --json` |
| Disc folder (VIDEO_TS, BDMV, or web) | `oncemore build <project> -o out/ [--format dvd\|bluray\|web] [--fast] [--keep-work] [--no-cache] --json` |
| Disc image | `oncemore iso <project> -o disc.iso [--format dvd\|bluray] [--iso-tool auto\|builtin\|hdiutil\|genisoimage\|mkisofs\|xorriso] [--build-dir DIR] [--fast] [--keep-work] [--no-cache] --json` |
| Burn the image (only on request) | `oncemore burn disc.iso [--device DEV] [--layer-break auto\|none\|SECTOR] --json` |
| Delete the encode cache | `oncemore clean <project> --json` |
| What this skill declares | `oncemore contract --json` |

`oncemore gui [<dir>] [--port N] [--no-browser]` (the authoring app in a
browser) and `oncemore mcp [--root DIR]` (the MCP server) keep running until
stopped: start them only when the user asks for the app, or to register the
server.

## MCP tools

Every tool takes `folder`, an absolute path inside the server's roots
(`oncemore mcp --root DIR`, repeatable; default the home folder).

| Tool | What it does |
|---|---|
| `doctor` | which external tools are found |
| `project_format` | the project JSON Schema and the rules for writing one; read it before `write_project` / `edit_project` |
| `create_project` | an empty project, the sample (`sample: true`) or the player test disc (`test_disc: dvd\|bluray`); `overwrite: true` to replace one |
| `read_project` | the JSON, the media in the folder, and what is wrong with it |
| `write_project` | replace the JSON (checked first; the old one kept in `.oncemore-backup`) |
| `edit_project` | a JSON Merge Patch (RFC 7386); arrays are replaced whole |
| `import_media` | copy files into `media/`; returns the project paths to use |
| `validate` | as a build would check it; `media: false` checks only the JSON |
| `preview_menu` | a menu as a PNG image, one button highlighted |
| `simulate` | `keys` pressed in order; where the disc is after each |
| `import_psd` | a menu from a layered `.psd` in the project |
| `build` | starts a background build (`format: dvd\|bluray\|web`, `output: iso\|folder`, `fast`) into `<folder>/output`; returns a `job` |
| `build_status` | that job's steps, progress, and finally `result` or `error` |

Typical flow: `create_project` (or `read_project`) -> `import_media` ->
`project_format` -> `write_project` with the first title and its menu in one
write -> `validate` -> `preview_menu` -> `simulate` -> `build`, then poll
`build_status` until `done`. Menus are laid out on a 720-wide grid (480 high
NTSC, 576 PAL); times are seconds or `"HH:MM:SS"`.

## Output and exit codes

With `--json` (before or after the command) stdout is JSON Lines: `step`,
`progress` (`fraction` 0-1), `log`, then one final `result` (`ok: true`) or
`error` (`ok: false`, `message`, `hint`, and `issues` for an invalid
project). Read the last line. Exit codes: `0` ok, `1` error, `2` invalid
project (or bad arguments), `3` missing tools (also `doctor` not ready),
`4` an external tool failed, `130` interrupted.

`validate` puts navigation problems (titles or menus nothing leads to, menus
with no way out) in `navigation`, and size warnings in `warnings`; `iso`
returns `iso`, `iso_bytes` and, for a dual-layer DVD, `layer_break`.

## What needs macOS

* **Oncemore.app** (the double-click Mac app, Apple silicon or Intel, with
  its own ffmpeg) is macOS only. The CLI, the browser app and the MCP server
  run on macOS and Linux with Python 3.11+ and an installed ffmpeg; Windows
  is not supported.
* On macOS install ffmpeg as `brew install ffmpeg-full` (plain `ffmpeg` has
  no `drawtext`, so menus cannot be drawn); oncemore finds the keg-only build
  itself.
* `--iso-tool hdiutil` is macOS only (elsewhere it fails as a missing tool).
  The default (`auto` = the built-in writer, UDF + ISO 9660) needs nothing
  installed on any system.
* `burn` uses `hdiutil burn` on macOS and `growisofs` (dvd+rw-tools) on Linux;
  on Windows it is refused. hdiutil chooses a dual-layer disc's layer break
  itself.

## Safety

* **Burning writes a physical disc and closes it.** Run `burn` only when the
  user asked for a disc to be burned, with a blank disc in the writer; name
  the device when there is more than one. The MCP server has no burn tool.
* `build` replaces `VIDEO_TS` / `AUDIO_TS` (or `BDMV`) inside its output
  folder, and `iso` writes its output file: point them at a folder or file
  that may be replaced. `init` / `testdisc` refuse an existing project
  unless `--force`; `create_project` unless `overwrite: true`.
* `clean` deletes only `<project>/.oncemore-cache`; the next build encodes
  everything again (minutes per title).
* Encoding takes minutes per title. Use `transcode`, or `--fast` for drafts
  (1 pass on a DVD), and give `transcode` the same `--fast` as the build.
* oncemore never uses the network and adds no copy protection; projects are
  plain JSON.

## Errors: report them as they are

* Exit `2` / `issues`: name each issue; nothing was written or built. Fix
  the JSON (or the MCP call) and validate again.
* Exit `3`: quote the missing tools and the `hint`; do not try another way
  of encoding.
* Exit `4`: an external tool (usually ffmpeg) failed; its log is in
  `.work/logs/` (kept with `--keep-work`).
* A font without a character used in a menu stops the build rather than
  drawing empty boxes: choose another font (`ONCEMORE_FONT` or the
  project's font). Emoji are not supported.
* A built image is done only when the final `result` says so. Say "playable"
  only for a `builtin`, `hdiutil`, `genisoimage` or `mkisofs` image: an
  `xorriso` image is ISO 9660 only and most players do not open it.
* `build_status` with "no such build" means the MCP server restarted: start
  the build again.

## Not this skill's job

Cutting, trimming, colour, loudness and subtitle making
(ffmpeg-skill, the video production skills): oncemore makes the disc from the
videos it is given and does its own final encode to the DVD and Blu-ray
rules. Copy protection of any kind, and network access of any kind, are never
provided.
