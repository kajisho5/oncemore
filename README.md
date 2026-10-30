<p><img src="docs/images/logo/lockup-dark.svg" alt="oncemore" height="56"></p>

# oncemore

*The DVD authoring app Mac forgot. Menus, chapters, ISO — once more.*

**Website: [kajisho5.github.io/oncemore](https://kajisho5.github.io/oncemore/)** · [日本語版 README](README.ja.md)

oncemore turns your video files into a **DVD-Video or Blu-ray disc image with
real menus**: a still menu with buttons, an auto-generated chapter menu with
thumbnails, chapter jumps, and "return to the menu when the movie ends". You
describe the disc in one JSON file and get a `.iso` you can play in VLC, burn,
or mount (or a web version that plays the disc in a browser).

It comes as an **authoring app that runs in your browser on your own Mac**
(`oncemore gui`), on top of a scriptable command-line core. Nothing is uploaded
anywhere: the app is served from your machine and works on your files.

![The menu editor](docs/images/gui-menu-en.png)

## What oncemore promises

These are the reasons it exists; the tests and CI guard each of them
(`tests/test_promises.py`), so they cannot quietly go away:

* **A real authoring app on the Mac** — Oncemore.app for Apple silicon and
  Intel, built and smoke-tested on every change.
* **A disc image first** — it writes a standard ISO (UDF + ISO 9660) or a
  VIDEO_TS folder with nothing else installed; burning it to a DVD is an
  optional last step (Build > Output: DVD disc, or `oncemore burn`).
* **Runs in a browser** — the app is a web page served from your own machine,
  so it also works on Linux and needs no installer beyond Python.
* **Open and yours** — GPL-3.0, no account, no network access, no telemetry,
  and no copy protection, ever. Projects are plain JSON.

## Why

Adobe Encore was discontinued in 2012; Apple's DVD Studio Pro and iDVD are gone,
and Final Cut Pro 10.8 removed disc output altogether. DVDStyler's macOS build is
still Intel-only. Meanwhile the codecs DVD-Video requires are patent-free
(MPEG-2 since 2018, AC-3 since 2017), so an open-source authoring tool can do
the whole job. oncemore is that tool — with no copy protection, ever.

## Install

oncemore itself is pure Python (3.11+, standard library only); the DVD-Video
structure (IFO files, navigation packs, button and subtitle subpictures) is
written by its own copy of [vtskit](https://github.com/kajisho5/vtskit), and
the disc images by its copy of [udfkit](https://github.com/kajisho5/udfkit) and
the closed captions by its copy of [dvdcc](https://github.com/kajisho5/dvdcc);
the Blu-ray navigation files and subtitles by its copy of
[bdmvkit](https://github.com/kajisho5/bdmvkit). It drives these programs (the
[Mac app](#the-mac-app) carries its own ffmpeg and ffprobe, so it needs none of
them installed):

| Program | Used for |
|---|---|
| `ffmpeg`, `ffprobe` (with the `drawtext` filter) | MPEG-2/AC-3 encoding, menu rendering, probing |
| *(nothing)* — oncemore writes the UDF + ISO 9660 disc image itself; `hdiutil`, `genisoimage`, `mkisofs` or `xorriso` (ISO 9660 only) can be chosen instead | the disc image |
| *(optional)* `growisofs` (dvd+rw-tools; macOS uses its own `hdiutil`) | burning the disc to a DVD |

### macOS (Homebrew)

```sh
brew install ffmpeg-full
pip install git+https://github.com/kajisho5/oncemore
oncemore doctor
```

* Use **`ffmpeg-full`**, not `ffmpeg`: Homebrew's plain `ffmpeg` formula is built
  without libfreetype, so it has no `drawtext` filter for menu text.
  `ffmpeg-full` is keg-only (not linked into your PATH); oncemore finds it in
  `$(brew --prefix)/opt/ffmpeg-full/bin` automatically.
* The ISO is written by oncemore itself (UDF 1.02 + ISO 9660), so no ISO
  tool is needed; `--iso-tool hdiutil` uses macOS's own instead.

### Debian / Ubuntu

```sh
sudo apt-get install ffmpeg
pip install git+https://github.com/kajisho5/oncemore
oncemore doctor
```

(`genisoimage` and `dvd+rw-tools` are optional: another ISO writer, and burning.)

You can also run it from a checkout without installing: `python -m oncemore ...`.

Tool locations can be overridden with `ONCEMORE_FFMPEG`, `ONCEMORE_FFPROBE`,
`ONCEMORE_GENISOIMAGE`, `ONCEMORE_MKISOFS`, `ONCEMORE_XORRISO`, and the menu
font with `ONCEMORE_FONT`. Folders: `ONCEMORE_CACHE` (the media cache),
`ONCEMORE_TEMPLATES` (My Templates), `ONCEMORE_STYLES` (My Styles) and
`ONCEMORE_CONFIG` (recent projects and settings).
If something is missing, oncemore says what and prints the install command.

## The Mac app

**Oncemore.app** wraps the same authoring UI in a normal Mac window: double-click
to start, *File › New Project… / Open Project…*, and it reopens your last
project. Nothing else needs installing: Python and its own ffmpeg and ffprobe
are inside the app (FFmpeg 9 with x264, FreeType and HarfBuzz, built by
`macos/build_ffmpeg.sh` from pinned sources; GPL, with the sources attached to
each release). The command line and the browser app still use the ffmpeg you
install (below).

Download `Oncemore-<version>-arm64.zip` (Apple silicon) or
`Oncemore-<version>-x86_64.zip` (Intel) from the
[Releases](https://github.com/kajisho5/oncemore/releases) page (or the latest CI
run's artifacts), unzip, and move *Oncemore.app* to Applications. From 1.0
on the release is signed with a Developer ID and notarised by Apple, so it
opens like any downloaded app (a CI artifact or a 0.x release is not:
open *System Settings › Privacy & Security* and click **Open Anyway**). oncemore never
connects to the internet, so it does not look for new versions by itself:
*Help › Check for Updates…* shows which version you have and opens the Releases
page (or click **Watch › Custom › Releases** on GitHub to be told). Its icon follows Apple's
[Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/app-icons):
on macOS 26 and later a layered icon (`macos/AppIcon.icon`, square and
unmasked: the system rounds it and adds its light, and makes the dark,
clear and tinted looks), on earlier macOS the flat one. Build it yourself
with `macos/build_app.sh` (needs `gh`, and Xcode 26 or later for the layered
icon, or an older Xcode with `NO_LAYERED_ICON=1`); with a Developer ID
set `CODESIGN_IDENTITY` and `NOTARIZE=1` to produce a signed, notarised app
(stapling the ticket is tried up to five times, as Apple's servers sometimes
drop the connection).
Pushing a tag `v<version>` runs `.github/workflows/release.yml`, which builds
both architectures, launches each on a sample project and attaches the zips to a
release (signed and notarised when the signing secrets listed in that file are
set; from 1.0 on it refuses to release without them): 0.x versions are published as pre-releases right away, 1.0 and later as
drafts; the notes come from `docs/release-notes/<tag>.md`. Running the
workflow by hand (Actions > Release > Run workflow) with `tag` set does the
same and makes the tag on the commit it ran on; with `publish` ticked as well,
a 1.0-or-later release is published at once as the latest instead of a draft.

## Quick start: the app in a browser

```sh
oncemore gui my-disc          # opens http://127.0.0.1:…/ in your browser
```

* **New project** → *Create sample project* gives you a working disc to explore,
  or start empty and **drop your video files** onto the window. *Player test
  disc* makes the disc for trying a set-top player (below).
* **Titles**: pick a video in *Media* → *Add as title*. Scrub through it and
  press **◆ Add chapter here** wherever a chapter should start; **▶ Play** plays
  it (a small preview copy is made the first time). Tick *Generate a
  chapter menu* for a thumbnail menu. Set what happens when it ends, audio
  tracks and subtitles (`.srt`, `.vtt`, `.ass` / `.ssa`, text scripts) in the right-hand panel. Below the
  timeline, **Subtitles** edits the cues (start / end, text, top or bottom):
  *+ Add cue at playhead* times a new one from where you are; files in other
  formats can be saved as a new `.srt` to edit.
* **+ Slideshow** turns the pictures in *Media* into a title: set each picture's
  duration and order, cross-fade or cut, slow zoom (pan & zoom) and music;
  **Render & play** shows it as it will be on the disc. Every picture starts a
  chapter.
* **Clips**: under a title's picture, *Add a clip…* joins more videos and still
  pictures into the same title — parts of files (in / out), in any order, of
  different sizes, frame rates and sound (or none); a picture is shown for the
  seconds you set, whole (fit) or filling the frame (fill). The title then
  shows and plays the joined result, the timeline shows each clip, and every
  clip starts a chapter unless you set chapters yourself.
* **Menus**: *+ Add* starts blank or from a template (classic, banner, minimal,
  setup), then drag buttons, text and rectangles where you want them —
  Shift-click (or ⌘-click) or a box dragged around them selects several, with
  align / distribute buttons, snapping guides, arrow-key nudging and ⌘D to
  duplicate. Shift-drag moves in a straight line, Alt (⌥)-drag leaves a copy,
  and holding ⌘ / Ctrl while dragging turns snapping off. A selected
  rectangle or picture has handles to resize it (Shift: keep the
  proportions, Alt: from the centre); a text or button has corner handles
  that scale its type. Slides, clips, playlist items and layers can be
  dragged to a new place in their lists. Choose
  each button's target (a menu, a title, a chapter, an audio or subtitle
  stream). A button can be a picture instead of text (*Image*, highlighted by a
  frame or by its shape). Use an image or a video as the background. **Exact preview**
  renders the menu exactly as the disc will show it, with button hit areas.
* ▲/▼ in the right-hand panel change the order of titles and menus.
* **Backups**: before a save replaces the project file, the version it
  replaces is kept in `.oncemore-backup/` next to it (at most every five
  minutes, the last 30). **File > Revert to a saved version** goes back to one
  of them; Undo returns to where you were.
* **Layers**: the eye switches an element off — it stays in the project but is
  not on the disc (a button's routes to it go too).
* **Save menu as template** (Menu menu): the menu and copies of its pictures,
  fonts and music go to your template library (`ONCEMORE_TEMPLATES`, or
  `~/Library/Application Support/oncemore/templates` on a Mac); **My templates**
  in the Library starts a menu from one in any project (links the project does
  not have become *stop*). **Create chapter index** makes a title's chapter menu.
* **Colour set** (menu Properties): Normal (buttons while not selected,
  optional), Highlight and Activated colours, each with an opacity; previews
  and the simulator show them as the player will.
* **Chapter markers from the file**: a video that carries chapter markers
  (MP4, MOV, MKV …) brings them along, names included, when it becomes a
  title; Timeline > Import chapter markers from the source reads them again
  (for titles made of clips, the markers inside each clip).
* **My styles** (Library): save the look of a text, button or shape (font,
  size, colour, outline, shadow, bold, italic, spacing) under a name, and give it to other objects
  in any project; the font is kept with the style.
* **Paragraphs** (a text's Properties): text of several lines, lined up
  left, centred or right, with the space between the lines.
* **Bold, italic, letter spacing and kerning** (a text's or button's
  Properties): bold and italic use those faces of the font's family (offered
  when the family has them); letter spacing spreads the characters out or
  closes them up, and kerning can be switched off.
* **Button highlights** (a button's Properties > Highlight): its own pixels
  (the letters, or a picture's opaque pixels), a frame, a line under it, or a
  rectangle or ellipse drawn on the menu (drag it, and its corner to resize;
  filled or just its outline). The highlight picture can still replace it.
* **Multi-angle titles** (a title's Properties > Angles, DVD): other videos
  of the same scene, switched with the remote's Angle key without a break
  (the new angle from the next interleaved unit, about a second); add,
  pick, order and remove them there (the title's own video is angle 1).
* **Buttons over a title** (a title's Properties > Buttons over the title,
  DVD): areas of the picture the viewer selects and presses while the title
  plays, each from a start to an end (a "skip intro" over the opening, links
  to the next episode over the credits). The video shows them; the disc
  lights the area. Add them at the playhead, set their link and times there,
  and drag their boxes on the picture to place and size them. The arrow
  keys go between the buttons shown at the time; a link plays a title or
  chapter, opens a menu (Resume comes back, as from the Menu key) or
  switches the sound or subtitles. Preview plays them (*Time in the title*;
  `seek:<seconds>` for `oncemore simulate`); the web version leaves them out
  (a Blu-ray build stops on them).
* **Navigation scripts** (the disc's Properties > Navigation scripts, DVD):
  a few lines of navigation for what a link cannot do (count presses,
  remember a choice, pick at random); **+ Script** adds one, the app says
  under the text which variables it uses and where it can go (or what is
  wrong), and a button, a menu's time-out or a title's or playlist's end
  takes *Script: <name>* as its link. Renaming a script keeps its links, and
  renaming a menu or title updates the links inside the scripts. Preview
  runs them and shows the variables. See [Navigation scripts](#navigation-scripts).
* **Menus with pages** (Menu > Add new page): a menu's buttons spread over
  pages, turned with buttons to the next, previous or a given page; a
  heading or background shape can be on every page. Each page is a menu of
  its own on the disc.
* **Layer break** (Disc panel, DVD-9): the chapter where a dual-layer disc
  goes on to its second layer, or the first one past the middle of the disc.
  The built-in ISO writer puts it on an ECC block, `oncemore iso` reports its
  sector, and burning passes it to growisofs.
* **Chapters at intervals** (Timeline menu): a chapter every *n* minutes or
  seconds, replacing the chapters there are or adding to them.
* **Chapters at scene changes** (Timeline menu): finds the cuts in the
  picture (sensitivity low, medium or high) and puts a chapter at each, at
  least so many seconds apart; `oncemore scenes video.mp4` lists them.
* **Replace asset** (File menu, or right-click a file): every use of one file
  in the project points to another — also how a missing file is found again
  (missing files are listed first, and the issue list offers it).
* **Edit menu in Photoshop** (Edit menu, Tools panel or Properties): opens a
  menu's `.psd`; when it is saved there, the Menu Viewer offers to import it
  again. **File > Project settings** shows the disc's settings; the **Window**
  menu brings any panel to the front.
* **Transcode now**: titles are encoded when the disc is built, or ahead of
  time with *Transcode this title now* / *Transcode all titles now* (right-click
  a title, or the Disc menu); the build then reuses them. A filled dot next to
  a title in the project panel means it is transcoded. The timeline draws each
  sound track's waveform.
* **Linking and routing**: drag a title, menu, playlist or chapter (from the
  Timelines panel) onto a button to link it, or onto an empty part of the
  menu to add a button for it. Assets drop onto a menu too: a video makes a
  title and a button that plays it (on a button: that button plays it; with
  Alt / ⌥: the motion background), a picture is placed where it lands (with
  Alt: the background), a sound is the menu's music. A layered Photoshop file
  dropped into the window becomes a menu (with Alt: just a picture). *Routing* draws where the remote's arrow keys go from each
  button (solid: set by you in Properties, dashed: automatic), exactly as the
  disc will have it; drag an arrow onto another button to send that key there.
  Double-click a text or a button's words to type them in place (Esc ends it).
  Ctrl + right click (⌘-Control-click on a Mac) lists the objects under the
  pointer, to pick one that is covered.
* **Menus and shortcuts**: the menu bar is laid out the way disc authoring
  people know it — File, Edit, Object, Menu, Timeline, View, Window, Help,
  with submenus (Import as, Transcode, Build, Align, Arrange, Show
  highlights, Workspace…); in Oncemore.app it is the Mac's own menu bar,
  made from the same list. File opens, makes and saves projects (Open
  recent, Save as copies the project folder), imports a file as a menu, a
  timeline, a slideshow or a pop-up menu, and builds DVD / Blu-ray images,
  folders or discs; Edit cuts, copies and pastes objects or whole titles and
  menus, renames, edits originals; Object aligns (one object: to the safe
  area), distributes, arranges and adds a drop shadow or stroke; Menu adds
  objects, sets the default button and the colour set and saves the menu as
  a picture; Timeline adds audio and subtitle tracks, imports text scripts
  (absolute or relative timecode), exports subtitles as SubRip or a text
  script, sets poster frames and saves frames (exports go to `exports/`).
  Right-click a title, menu or
  playlist (open, duplicate, move, play first, transcode, delete), a file in
  *Media* or an element on the menu. Shortcuts: ⌘N / ⌘O / ⌘S / ⇧⌘S new,
  open, save, save as, ⌘I import, ⌘B build, ⌘X / ⌘C / ⌘V / ⌘D cut, copy,
  paste, duplicate, ⌘A select all, ⌘Z / ⇧⌘Z undo / redo, ⌘[ / ⌘] / ⇧⌘[ /
  ⇧⌘] stacking order, ⌘0 fit, ⌘L link of the selected button, V / R / T / Z
  selection, rotate, text and zoom tools, ⌘; / ⌥⌘; / ⇧⌘; show / lock / snap to
  guides, + / − zoom, `*` (Shift+8) chapter at the
  playhead, PgUp / PgDn previous / next chapter, Space play / pause, Home /
  End and ← / → (a frame; ⌘ + wheel too) to move the playhead (or drag it in
  the ruler), ⇧* on the keypad or ⇧⌘8 poster frame (⌘⌥-drag from a chapter
  mark: that chapter's), ⌘. / keypad + − timeline zoom, ⇧Space
  preview, ⌥⇧1–4 workspaces, ? the list (Ctrl instead of ⌘ on other systems).
* **The menu editor**: a tools strip (selection, rotate — drag an object
  around its centre, text — click where it goes, zoom, new button /
  rectangle, preview) and a viewer bar under the menu: zoom, safe area,
  routing, snapping, guides and *New guide*, and *Highlights: Normal /
  Selected / Activated* showing every button as the disc will in that state.
  Buttons whose areas overlap are outlined in red, and *Check project*
  lists them (a disc cannot be built with them). Object > Rotate and Flip
  turn and mirror texts, buttons, rectangles and pictures (on the disc too,
  highlights included).
* **Pick whip**: drag the ◎ next to a button's link (or a title's end action,
  or the disc's first play) to a title, menu or playlist in the project panel
  or the flowchart. In the **flowchart**, drag from one item to another to link
  them (first play, end actions, or — from one of the buttons listed under a
  menu, or after picking it — a menu's button); a title, menu or playlist
  dragged in from the project panel links by where it lands (the disc: first
  play; a title or playlist: its end action; a menu's button: that button; a
  menu: a new button). Items nothing leads to sit in a "Not used" row at the
  bottom. In the project panel, ↑ / ↓ go through the items. A tool key held
  down chooses the tool only while it is held.
* **Preview** (⇧Space) starts the remote-control preview at the menu you are
  editing; in it, 1–9 press that button, Home is the Title key, Insert the
  Menu key, End plays to the end, Space plays, ⌘← / ⌘→ previous / next
  chapter. Keys pressed quickly one after another are taken in order.
* **Flowchart** shows the whole disc: first play, menus, titles, playlists and
  every link between them (buttons, end actions, time-outs, the remote's Menu
  and Title keys). Boxes a viewer can never reach, or menus they cannot leave,
  are outlined in red; click a box to edit it.
* **Simulator** plays the disc with an on-screen remote (arrows, OK, Menu,
  Title, ⏮ ⏭, play to the end, let a menu time out) before anything is
  encoded: menus are the exact previews with the real highlight, titles show
  the chapter's first frame. It follows the same navigation rules as the
  built disc (checked against libdvdnav in the tests).
* The **Build** panel (next to Project): **Check Project…** estimates the size
  and finds problems, with the bit budget: a bar of the whole disc and, for
  each title, its length, video and audio rates and the space it takes (and
  the menus' and what is left), before anything is encoded (`oncemore
  validate` prints it too); **Build** writes the `.iso` (or a VIDEO_TS folder) into
  `my-disc/output/`, with progress.
* **Help > oncemore help** (F1) opens the app's manual in a window of its
  own, without a connection: its contents, a search field, and a reference
  of every menu command made from the menu bar itself. F1 opens it at the
  part about what you are working on (a menu, a title, the flowchart, the
  preview, the build). The text is `oncemore/gui/static/manual-en.md` and
  `manual-ja.md`.
* Everything is saved automatically to `my-disc/project.oncemore.json`;
  ⌘Z / Ctrl+Z undoes. The UI follows your browser language (English/日本語;
  Edit > Preferences switches it, sets the brightness and a light theme).

![A title with its timeline: picture, chapters, audio and subtitle tracks](docs/images/gui-title-en.png)

The workspace is the classic disc authoring layout: the menu bar, a **Tools**
panel (selection, text, zoom, new button / rectangle, Photoshop, Preview) with
the **Workspace** menu and a search field; **Project · Menus · Timelines ·
Build** on the left, **Monitor · Menu Viewer · Flowchart** in the middle, the
**Timeline** across the bottom of both, **Properties** and **Library ·
Layers** on the right. Two skins (Edit > Preferences): **Modern**, the
default, and **Classic** — mid-grey panels, light text fields, an amber outline
on the panel you are working in, amber timecode. Panels are resized by dragging
their edges. The design rules are in [docs/DESIGN.md](docs/DESIGN.md) and the
app shows them at `/styleguide.html`.

![The flowchart](docs/images/gui-flow-en.png)
![The disc simulator](docs/images/gui-sim-en.png)

The app listens on 127.0.0.1 only, with a random per-launch key in the URL;
it reads and writes files only inside the project folder.

## Quick start: the command line

```sh
oncemore init demo                                   # sample project + generated test media
oncemore preview-menu demo --menu main -o main.png   # look at the menu
oncemore iso demo/project.oncemore.json -o demo.iso  # encode, author, write the ISO
```

The sample disc has a main menu (PLAY ALL / CHAPTERS / SAMPLE TITLE B), a
generated chapter menu with thumbnails, a 16:9 title with three chapters and a
4:3 title (pillarboxed). All sample media are synthesised with ffmpeg test
sources — nothing large lives in this repository.

## Commands

```
oncemore init <dir> [--standard NTSC|PAL] [--aspect 16:9|4:3] [--force]
oncemore testdisc <dir> [--format dvd|bluray] [--standard NTSC|PAL] [--aspect 16:9|4:3] [--force]   # a disc for trying a set-top player, with a checklist
oncemore validate <project> [--no-media] [--format dvd|bluray|web]   # schema + references + media + size estimate
oncemore build <project> -o out/               # out/VIDEO_TS (and out/AUDIO_TS), or out/BDMV for a Blu-ray project
oncemore build <project> -o out/ --format bluray  # writes out/BDMV (Blu-ray, HD)
oncemore iso <project> -o bd.iso --format bluray   # a Blu-ray image (UDF 2.50, built-in writer)
oncemore build <project> -o web/ --format web     # the disc for browsers: web/index.html
oncemore iso <project> -o out.iso [--iso-tool auto|builtin|hdiutil|genisoimage|mkisofs|xorriso]
oncemore preview-menu <project> --menu main -o main.png [--button id] [--state highlight|select|normal] [--outline]
oncemore simulate <project> --keys down,enter,menu   # press remote keys, no encoding
oncemore import-psd <project> design.psd --menu main [--first-play]   # a menu from Photoshop
oncemore gui [<dir>] [--port N] [--no-browser] # the authoring app
oncemore transcode <project> [--title ID] [--fast] [--status]  # encode a DVD's titles ahead of the build
oncemore burn out.iso [--device DEV] [--layer-break auto|none|SECTOR]   # write the image to a blank DVD or BD (macOS: hdiutil, else growisofs)
oncemore clean <project>                       # delete the encode cache (made again by the next build)
oncemore scenes video.mp4 [--sensitivity low|medium|high] [--min-gap S]   # scene changes: chapter suggestions
oncemore doctor                                # external tools, versions, ISO backend
oncemore mcp [--root DIR]                      # tools for AI assistants (MCP, below)
oncemore contract [--json]                     # machine-readable contract (AI Video Production OS)
```

* `<project>` is a `project.oncemore.json` file or the directory containing it.
* `validate` also checks the navigation: titles, menus and playlists nothing
  leads to, and menus without a way out, are reported as warnings
  (`navigation` in `--json` output).
* `build`, `iso` and `validate` make the project's `disc.format` (DVD unless
  it says `bluray`) when `--format` does not say; `validate --format web`
  checks for the web version.
* A DVD is encoded in **2 passes** by default (`--fast`: 1 pass); a Blu-ray
  and the web version at a constant quality (`--fast`: a quicker, slightly
  worse encode).
* Intermediate files go to `out/.work/` (for `iso`: a hidden build directory
  next to the ISO) and are deleted on success unless `--keep-work` is given.
  Every external command's log is in `.work/logs/`.
* `--json` (before or after the command) switches to **JSON Lines** on stdout
  for GUIs and scripts: `step`, `progress` (`fraction` 0–1), `log`, and a final
  `result` or `error` object. Exit codes: 0 ok, 1 error, 2 invalid project,
  3 missing tools, 4 an external tool failed.

## From an AI assistant (MCP)

`oncemore mcp` lets an AI assistant author discs for you: it serves
oncemore's operations as [Model Context Protocol](https://modelcontextprotocol.io)
tools over stdio, so you can ask in plain words ("make a DVD of these three
videos with a chapter menu, white text on black") and the assistant creates
the project, brings the videos in, writes the menus, checks the disc, shows
you the menu as a picture, presses the remote on it and builds the image.

Claude Code:

```
claude mcp add --scope user oncemore -- oncemore mcp
```

Claude Desktop (`claude_desktop_config.json`), or any MCP client:

```json
{"mcpServers": {"oncemore": {"command": "oncemore", "args": ["mcp"]}}}
```

Tools: `project_format` (the JSON Schema), `create_project`, `read_project`,
`write_project`, `edit_project` (a JSON Merge Patch), `import_media`,
`validate`, `preview_menu` (a PNG), `simulate`, `import_psd`, `build` with
`build_status` (in the background: a DVD or Blu-ray image or folder in
`<project>/output`), `doctor`. A project that would be invalid is never
written; the issues go back to the assistant to correct. Only folders inside
your home folder are touched (`--root DIR`, repeatable, to allow others or
narrow it). Nothing leaves your computer except through the assistant you
connected. Both protocol eras are spoken: revision 2026-07-28 and the earlier
ones that open with `initialize`.

The repository's root [`SKILL.md`](SKILL.md) is the same as a skill: when to
use oncemore, every command and MCP tool with its options, the exit codes,
what needs macOS (the app, `hdiutil`, burning) and what to be careful with.
An assistant that loads skills (or the AI Video Production OS marketplace)
reads it; `tests/test_skill.py` keeps it to commands, options and tools that
exist.

### With ffmpeg-skill: getting the videos ready first

oncemore makes the disc from the videos it is given; it does not edit them.
For an assistant that should also prepare the footage, add
[ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (local FFmpeg, no
cloud, no API keys) next to it:

```
npx ffmpeg-skill        # Claude Code; --cursor, --codex or --all for the others
```

Then one request can cover both, e.g. "trim the start of these phone videos,
even out their loudness and make a DVD with a chapter menu": ffmpeg-skill
cuts (`cut.py`, `silence.py`), turns HDR phone video into SDR
(`color.py --to-sdr`), evens out loudness (`loudness.py`, EBU R128) and makes
subtitle files (`caption.py`); oncemore takes the results, adds the menus and
builds the disc. Leave the final encode to oncemore: it encodes to what the
DVD and Blu-ray rules allow. The two never call each other: the assistant
uses both, and oncemore stays standard-library only and offline.

## Project file

`project.oncemore.json` is the only input. JSON Schema:
[schema/project.schema.json](schema/project.schema.json). Paths are relative to
the project file. Example: [examples/basic/project.oncemore.json](examples/basic/project.oncemore.json).

```jsonc
{
  "version": 1,
  "disc": {
    "label": "SAMPLE_DISC",      // volume label; normalised to A-Z 0-9 _ (max 32)
    "standard": "NTSC",          // NTSC (720x480, 29.97) | PAL (720x576, 25)
    "aspect": "16:9",            // 4:3 | 16:9
    "target": "DVD5",            // DVD5 (4.37 GiB) | DVD9 (7.95 GiB)
    "first_play": "menu:main",   // menu:<id> | title:<id> | playall | playlist:<id>; default: first menu
    "font": null,                // font file for menu text; null = auto
    "video_bitrate": "auto"      // "auto" = fit the disc, or e.g. "6M"
  },
  "titles": [
    {
      "id": "t1",
      "name": "Sample Title A",                     // used as chapter-menu heading
      "source": "media/sample_a.mp4",
      "chapters": ["00:00:00", "00:00:08", 16],     // "HH:MM:SS[.ms]", "MM:SS" or seconds
      "audio": { "codec": "ac3", "bitrate": "192k" },// ac3 | lpcm (48 kHz/16-bit) | dts (copied); "channels": 6 = 5.1
      "end_action": "menu:main",                    // menu:<id> | title:<id> | stop
      "auto_chapter_menu": { "id": "chapters", "back": "menu:main" }  // or true
    }
  ],
  "menus": [
    {
      "id": "main",
      "background": "media/menu_bg.png",   // still image; null = background_color
      "audio": null,                       // optional looping music
      "texts": [{ "text": "SAMPLE DISC", "x": 120, "y": 90, "size": 56 }],
      "buttons": [
        { "id": "play", "label": "PLAY ALL", "x": 120, "y": 220, "action": "playall" },
        { "id": "ch",   "label": "CHAPTERS", "x": 120, "y": 280, "action": "menu:chapters" }
      ],
      "highlight_color": "#FFD400",
      "select_color": "#FF5A00"
    }
  ]
}
```

### Reference

**disc**

| Key | Type / values | Default |
|---|---|---|
| `label` | string → A–Z 0–9 `_`, ≤ 32 chars | required |
| `standard` | `NTSC` \| `PAL` | required |
| `aspect` | `4:3` \| `16:9` | required |
| `format` | `dvd` \| `bluray`: the authoring mode, what a build, an image and a check make when `--format` (or the app's Build panel) does not say | `dvd` |
| `target` | `DVD5` \| `DVD9` | `DVD5` |
| `layer_break` | DVD9: where the second layer starts: `auto` \| `<title id>:<chapter>` | `auto` (the first chapter past the middle) |
| `first_play` | `menu:<id>` \| `title:<id>` \| `playall` \| `playlist:<id>` | first menu, else first title |
| `title_key` | what the remote's Title / Top Menu key opens: `menu:<id>` \| `title:<id>` \| `playall` \| `playlist:<id>` | first menu |
| `subtitles_off` | `true`: the disc starts with subtitles off instead of leaving it to the player's language setting (a subtitle track marked `default` still wins); set once at first play | `false` |
| `font` | path or `null` | auto: Hiragino (macOS) → Noto Sans CJK → DejaVu Sans |
| `video_bitrate` | `"auto"` or bitrate (`"6M"`, `5500000`), 1–8 Mbit/s | `auto` |
| `rom_files` | files / folders put next to VIDEO_TS (DVD-ROM content for computers) | none |
| `bluray.target` | `BD25` \| `BD50`: the disc size when the project is built as a Blu-ray | `BD25` |
| `bluray.video` | `1080` \| `720`: the Blu-ray's picture. `1080`: 1920×1080 (1080i at 25 / 29.97, film at 1080p 23.976). `720`: 1280×720 progressive at 50 / 59.94 (twice the disc's rate, so 50p / 60p motion is kept; film at 720p 23.976) | `1080` |
| `subtitle_style` | `{size, color, outline, outline_width, margin}` for all subtitles | 30 px (PAL 36), white, black outline 3 px, 36 px (PAL 43) from the bottom |

**titles[]** (1–99)

| Key | Type / values | Default |
|---|---|---|
| `id` | `[A-Za-z0-9_-]{1,40}` | required |
| `name` | string | the id |
| `source` | any video ffmpeg reads, an MPEG-2 elementary stream (`.m2v`) too (its sound from `audio_tracks`) | required (or `slideshow` / `clips`) |
| `slideshow` | a title made from pictures (below) | none |
| `clips` | a title made of parts of several videos (below) | none |
| `angles` | more views of the same scene (DVD only): video files the viewer switches between with the remote's Angle key, the `source` being angle 1; up to 8, each at least as long as the source, encoded with the title's settings and sound | `[]` |
| `buttons` | buttons over the title's picture (DVD only; not with `subtitles`): `[{id, start, end, x, y, width, height, action}]`, each an area of the picture (the disc's pixels) the viewer selects with the arrow keys and presses with Enter from `start` to `end` (seconds; no `end`: to the title's end). The video shows what they look like; the disc lights the area when selected and pressed. `action` as a menu button's, but `resume` and `page:` (a link leaves the title as its end action would; `audio:` / `subtitle:` switch and the title plays on). The times they change are at least 1 s apart, and from chapters | `[]` |
| `button_colors` | `{highlight, select}` of the buttons over the title | `#FFD400`, `#FF5A00` |
| `chapters` | list of times, or `{time, name, poster}` objects (`name` labels the chapter-menu button, `poster` is the time of its thumbnail); `0` is added if missing | `[0]` |
| `audio.codec` | `ac3` \| `lpcm` \| `dts` (DTS copied from the sources, never encoded; 5.1 or more unless `channels` says 2. A Blu-ray keeps DTS-HD (Master Audio or High Resolution, 48, 96 or 192 kHz, 7.1 too) whole, the picture leaving room for its peaks; a DVD takes the 48 kHz DTS core, up to 1536k) | `ac3` |
| `audio.bitrate` | AC-3 only, 64k–448k | `192k` (`448k` for 5.1) |
| `audio.passthrough` | copy 48 kHz AC-3 from the sources unchanged (channels must match) | `false` |
| `video_bitrate` | this title's own video bitrate; the other titles share the rest | shared |
| `scan` | `auto` \| `progressive` \| `interlaced` \| `pulldown` (NTSC film) \| `ivtc` (NTSC: film already telecined to 29.97i — its film frames are recovered and stored with soft pulldown): how the picture is stored, see Known limitations | `auto` |
| `picture` | a still shown for the whole title when its `source` is a sound file (music); without it the screen is black | none |
| `transcode` | `false`: the source already is DVD video (MPEG-2 at the disc's frame size and rate or NTSC 23.976 film, the disc's aspect, at most 9.8 Mbit/s) and its picture goes on the disc as it is; the sound is still made to the title's settings, chapters start at key frames of the source (GOP starts), not exactly at their times. On a Blu-ray the same setting copies an H.264 picture that already is Blu-ray video (High or Main profile up to level 4.1, 4:2:0, 1920x1080 square pixels or 1440x1080 with 4:3 pixels as AVCHD cameras record, 23.976 progressive or 25 / 29.97 coded for fields as 1080i; on a `720` disc 1280x720 at 50 / 59.94, a key frame at least every second, at most 40 Mbit/s); any other picture is encoded with a warning saying why | `true` |
| `audio.channels` | `2` (stereo, sources are down-mixed) \| `6` (5.1; with DTS, 5.1 or more) | `2` |
| `end_action` | `menu:<id>` \| `title:<id>` \| `chapter:<title id>:<n>` \| `playlist:<id>` \| `playall` \| `lastmenu` (back to the menu shown last) \| `stop` | first-play menu, else `stop` |
| `remote_menu` | menu the remote's Menu key opens during this title | first menu |
| `prohibit` | remote keys that do nothing during this title (user operations), e.g. a notice that cannot be skipped: `["next", "fast_forward", "menu"]`; any of `next` `prev` (chapter skip), `fast_forward` `rewind`, `pause`, `stop`, `search` (number keys: title, chapter and time search), `menu` (Menu / Pop-up key), `title` (Title / Top Menu key), `audio`, `subtitle` | none |
| `aspect` | `4:3` \| `16:9` for this title | `disc.aspect` |
| `audio.lang` | ISO 639-1 code of the (single) audio track | none |
| `audio_tracks` | 1–8 `{source?, stream?, lang?, default?}`: several audio streams (below); `default: true` (one per title): the disc starts with that track, set once at first play so a viewer's later choice stays | one track from `source` |
| `subtitles` | up to 32 `{file, lang?, default?}` subtitle files: SubRip, WebVTT, ASS/SSA or a text script (below) | none |
| `captions` | closed captions (line 21, CEA-608) on an NTSC DVD: an `.scc` caption file used as it is, or a subtitle file sent as pop-on captions; or `{file, offset}` (below) | none |
| `auto_chapter_menu` | `true` or object (below) | off |

`auto_chapter_menu` object: `id` (default `chapters_<title id>`; extra pages get
`_2`, `_3`…), `title` (heading), `back` (action of the BACK button, default:
the first-play menu), `label_format` (default `"Chapter {n}"`), `back_label`,
`prev_label`, `next_label`, `background`, `background_color`, `text_color`,
`highlight_color`, `select_color`, `normal_color`, `audio`, `duration`, `background_video` (a
motion chapter menu) and `animated_thumbnails` (with a motion background, the
thumbnails play their chapter). Six chapters per page, with PREV/NEXT buttons
when there are more.

**menus[]** (≤ 99)

| Key | Type / values | Default |
|---|---|---|
| `id` | identifier | required |
| `background` | still image or `null` | `null` |
| `background_color` | `#RRGGBB` | `#000000` |
| `background_video` | video file for a **motion menu** (overrides `background`) | `null` |
| `background_adjust` | `{crop: {x, y, w, h}, brightness, contrast, saturation}` made to the background picture or video before it is fitted to the menu: `crop` a part of it (fractions of its width and height from its top-left corner), `brightness` -1 to 1 (0: as it is), `contrast` and `saturation` 0 to 3 (1: as it is; saturation 0 is grey). In the app: the menu's Properties > Adjust | none |
| `audio` | music file or `null` | the background video's sound, else silence |
| `duration` | loop length, seconds | video / music length (≤ 600), else 5 |
| `loop` | `"forever"` or how many times it plays before `end_action` | `forever` |
| `loop_point` | repeats start here (time); the part before plays once as an intro | `0` |
| `fade_in` | seconds the menu fades in from black (picture and sound), at most 10; played once, repeats start after it | `0` |
| `buttons_at_loop` | the buttons appear (and work) only from the loop point (or the end of the fade-in) on, so the intro plays out | `false` |
| `end_action` | after the last loop: `menu:` \| `title:` \| `chapter:` \| `playall` \| `stop` | `stop` |
| `default_button` | button id highlighted when the menu opens | the first |
| `remember_button` | coming back highlights the button used last (menus 1–7) | `true` |
| `button_offset` | added to the buttons' numbers (their order, 1, 2, …) for the remote's number keys: with 10 the first button is 11 (Properties > Number renumbers a button) | `0` |
| `prohibit` | remote keys that do nothing while the menu shows (as for titles) | none |
| `font_size`, `text_color` | defaults for texts/buttons | `32`, `#FFFFFF` |
| `highlight_color`, `select_color` | button colours when selected / activated; `#RRGGBBAA` for translucent (a DVD has 16 levels of opacity) | `#FFD400`, `#FF5A00` |
| `hidden` (buttons, texts, shapes, images) | switched off in the Layers panel: kept in the project, not on the disc | `false` |
| `rotate`, `flip` (buttons, texts, shapes, images) | degrees turned clockwise about the object's centre, and `horizontal` / `vertical` / `both` to mirror it first (Object > Rotate / Flip, the Rotate tool). A button's label or picture turns with its highlight; its thumbnail stays as it is | `0`, none |
| `guides` | `{horizontal: [y…], vertical: [x…]}` guides for placing objects (View > New Guide; dragged in the editor; read from a Photoshop file's guides). Kept with the menu, never on the disc | none |
| `normal_color` | colour of the buttons' highlight shapes while not selected (the colour set's Normal state); none when absent | — |
| `texts[]` | `{text, x, y, size?, color?, animate?}` decorative text, plus the text style keys below | `[]` |
| `shapes[]` | `{x, y, w, h, color}` filled rectangles (bars, panels; `#RRGGBBAA` for translucent) drawn under texts and buttons | `[]` |
| `images[]` | `{file, x, y, w, h, opacity, adjust}` pictures that are not buttons (logos, photos; PNG keeps its transparency), drawn over the rectangles and under texts and buttons; `adjust` as `background_adjust`, the cropped part filling `w` × `h`. In the app: Tools > Picture, or right-click an image > Place on the menu | `[]` |
| `animate` (texts, images) | `{start, duration, dx, dy, scale, fade}`: the object **comes in** once, `start` seconds into the menu over `duration` (default 0 and 1): from `dx`, `dy` pixels away, growing from `scale` (pictures, 0.05–1) and fading in (`fade`), to where and as it is. The menu becomes a motion menu (DVD, Blu-ray and the web version); set its `loop_point` after the animation to play it once (the project check reminds you). Previews show the objects at rest. In the app: the text's or picture's Properties > Comes in | none |
| `buttons[]` | 1–36 buttons | required |

Text style (texts and text buttons): `font` (a font file for this element; it
must contain all its characters), `outline` + `outline_width`, `shadow` +
`shadow_offset`, `bold` and `italic` (the bold or italic face of the font's
family: its file next to the font, or installed), `letter_spacing` (pixels
added between the characters) and `kerning` (`false`: no kerning pairs).
A button's `highlight_image` is a picture whose opaque pixels
light up when it is selected, instead of the automatic highlight.
A button's `highlight` says how it lights up: `shape` (its own pixels: an image
button's opaque pixels, a text button's letters), `frame` (a frame around it),
`underline` (text buttons: the letters and a line under them; the default for
them, `frame` for image buttons) or `drawn`: the rectangle or ellipse in
`highlight_area` (`{x, y, w, h, form: "rectangle" | "ellipse", filled}`, on the
720-wide grid), which is then the whole highlight and the button's area.
A text can be a paragraph: its `text` holds several lines (newlines), `align`
lines them up (`left`, `center`, `right`; `x` is the paragraph's left edge)
and `line_spacing` adds pixels between them. With `width` (pixels, on the
720-wide grid) its lines are broken to fit that box: at spaces between words
and between Japanese or Chinese characters, keeping stops, closing brackets,
small kana and the long vowel mark off the start of a line and opening
brackets off its end. `vertical: true` sets it in columns, the first on the
right, its characters one under the other (`x`, `y` is the block's top left);
punctuation and brackets take their vertical forms where the font has them,
and `height` breaks the columns the same way. `underline` and
`strikethrough` draw a line under (beside, when vertical) or through each
line.
A menu with `pages` (2 or more) shows its buttons, texts, rectangles and
pictures with a `page` on that page only and the rest on every page; the
actions `page:next`, `page:prev` and `page:<n>` turn the pages (next from the
last page goes to the first). Page *n* is a menu of its own, `<id>~<n>`, and
`menu:<id>:<button>` opens the page that holds the button.

**buttons[]**: `id`, `label`, `x`, `y` (top-left of the label), `action`
(`menu:<id>` \| `title:<id>` \| `chapter:<title id>:<n>` \| `playall` \| `audio:<n>` \|
`subtitle:<n>` \| `subtitle:off` \| `page:next` \| `page:prev` \| `page:<n>` \| `resume` \| `stop`),
`auto_activate` (run as soon as the button is selected), optional `size`, `color`, and `nav`
(`{"up": id, "down": id, "left": id, "right": id}`) to override the automatic
navigation. `audio:<n>` / `subtitle:<n>` (1-based) select a stream and stay on
the menu, so a "setup" menu is just a few of these buttons plus a BACK button.
`playall` plays every title in project order and then follows the last title's
`end_action`; a title started on its own (by a title or chapter button) still
ends with its own `end_action`. `resume` continues the title the remote's Menu
or Title key interrupted, where it was left; when there is nothing to resume
(at the start of the disc, or after the title ended) it plays the first title.
Wherever an action can open a menu (buttons, end actions, overrides, first
play, the Title key), `menu:<id>:<button id>` opens it with that button
highlighted instead of its default or remembered one, e.g. a BACK button
that returns to the main menu on the button that led away from it, or a
title that ends on the main menu's next episode.
`override` on a `title:` / `chapter:` button (any end action)
replaces the end action of the title it plays, for that play only: titles
can chain into each other for "play all" while each song button still
returns to the menu. `audio` (1-based) and `subtitle` (1-based, `0` = off)
on a button switch streams along with its action, e.g. a "play with
commentary" button: `{"action": "title:film", "audio": 2, "subtitle": 0}`.
`transition` (a video file) on a button that leads somewhere (a menu, title,
chapter, playlist or play all) is a **link transition**: the video plays
when the button is pressed, then the button does what it says, e.g. the
main menu dissolving into the scene menu (render the dissolve as a short
clip in a video editor). On a DVD it plays as a menu program of its own,
on a Blu-ray as a title of its own; buttons with the same video and link
share one copy.
`thumbnail` `{x, y, w, h, time, animated, mask, mask_image}` on a `title:` /
`chapter:` button draws a frame of what it plays into that rectangle (`time`
seconds into it, default 1; `animated` plays it in a motion menu). `mask`
cuts it to a shape: `rounded` (corners of 15 % of the shorter side) or
`ellipse`; `mask_image` is a picture whose opaque pixels show it (a frame
shape, a heart), stretched to the rectangle, for a still thumbnail. The rest
shows the menu; the button's highlight is still drawn as the button says
(a drawn ellipse area matches an ellipse).
**Image buttons**: `image` (a picture, transparent PNG works best) replaces the
label (then optional), drawn with its top-left at `x`/`y`; `width` on the
720-wide grid (default: the picture's own width; the height follows its
aspect), and `highlight`: `frame` (default, a frame around it), `shape` (its
opaque pixels in the highlight colour) or `drawn` (a drawn shape, above).

### Menus from Photoshop

Design a menu as a layered `.psd` / `.psb` (RGB, 8 or 16 bits) and bring it in
with **Menus → + Add → Import from Photoshop** (or `oncemore import-psd`). The
layer names use the prefixes long common for DVD menus:

| Layer name | Meaning |
|---|---|
| `(+) Play Movie` | a **group** that is a button; the name becomes its id and suggests its target |
| `(=1) …` inside a button | its highlight (also `(=2)`, `(=3)`; merged, a DVD highlight here has one colour) |
| `(%) …` inside a button | where the title / chapter thumbnail goes |
| `(page) Scenes 1–6` | a top-level **group** that is a **page** of the menu: its artwork and buttons are on that page only |
| anything else visible | artwork, flattened into the background |

* The background is the file's own flattened image when the `(=n)` and `(%)`
  layers are hidden (exact, layer effects included; save with *Maximize
  Compatibility*). Otherwise it is rebuilt from the layers with normal blending.
* Buttons without a `(=1)` layer light up in the shape of their artwork.
* Names such as *Play*, *Play all*, *Scene 3*, a title's name, a menu id,
  *Audio 2* or *Subtitles off* are linked automatically; check the rest.
* A 720 × 480 (576) design is read as DVD pixels, an 854 × 480 or 1024 × 576
  one as square pixels: both land where they were drawn.
* **Import again** after editing the file updates the pictures and keeps every
  button's target and the menu's settings.
* **Pages**: each top-level `(page) …` group is a page, in the order of the
  Layers panel from the top, shown or hidden in the file alike. Its artwork
  becomes a picture on that page and its `(+)` buttons are on it; what is
  outside the pages is the background of every page (rebuilt from those
  layers). Buttons named *Next* or *Prev* turn the page.

Imported buttons are ordinary buttons with only a `highlight_image` (and a
`thumbnail` rectangle, which any title / chapter button can have).

### Playlists

```jsonc
"playlists": [{
  "id": "best", "name": "Best scenes",
  "items": ["t1:2", "t2:2-3", "t1"],   // a chapter, a chapter range, a whole title
  "end_action": "menu:main",           // any title end action; stop (default)
  "order": "shuffle"                   // sequential (default) | random | shuffle
}]
```

A button with `"action": "playlist:best"` (or `first_play` / `title_key`) plays the
items in order, also across titles with different formats; an item stops at the
end of its last chapter. Title, chapter and play-all buttons leave playlist mode.
`order` plays them shuffled (each once, in a random order) or at random (as many
items as the playlist has, each picked at random, so one can come again) on a
Blu-ray and in the web version; a DVD plays them as listed.

### Navigation scripts

For what a link alone cannot do (count, remember, choose at random, ask a
pass code), a DVD's navigation can be written by hand as a few lines of
dvdauthor's command language:

```jsonc
"scripts": {
  "twice": "# the second press plays the film\n$n += 1;\nif ($n >= 2) { $n = 0; play title:film; }\nelse play menu:main;",
  "dice":  "$r = random(3); if ($r == 1) play title:a; else if ($r == 2) play title:b; else play title:c;"
}
```

An action `commands:<id>` runs a script: on a menu's button (`chapter`
menus' BACK too), a menu's time-out, a title's end, a playlist's end and a
button over a title. Not at first play, the Title key or in an override.

* **Variables** are `$name`. oncemore gives each a player register its own
  navigation leaves free, so a script cannot break play all, playlists or
  remembered buttons; the same name is the same variable in every script.
  They are 0 when the disc starts and keep their value (0 to 65535) until
  a script changes them. A disc that uses every register for its own
  navigation has none left (fewer menus that remember their last button
  free some).
* **Links** are `play <action>;` with any action a button takes
  (`menu:<id>`, `menu:<id>:<button>`, `title:<id>`, `chapter:<id>:<n>`,
  `playlist:<id>`, `playall`, `lastmenu` at a title's end or on its
  buttons, `stop`, `audio:<n>`, `subtitle:<n>` / `subtitle:off`). It does
  what the action does there. `jump`, `call` and `gN` are not taken.
* **Statements**: `$x = <expression>;`, `$x += <value>;` (and `-= *= /= %=
  &= |= ^=`), `audio =`, `subtitle =`, `angle =`, `button =` (the
  player's own registers, as dvdauthor reads them: audio stream from 0,
  subtitle stream from 0 plus 64 when shown, button number × 1024; set to
  a number or a `$name`), `if (<condition>) { … } else { … }` and `play`.
  `#` starts a comment.
* **Expressions** are values (numbers, `$x`, `audio`, `subtitle`, `angle`,
  `button`) joined by `+ - * / % & | ^`, worked out from left to right;
  the first may be `random(n)` (1 to n). `$x` may only come first in its
  own expression (`$x = $x * 2 + 1`), since the disc computes it in place.
  A condition compares two values (`== != < <= > >=`), one of them a
  `$name` or a player register, and joins comparisons with `and` or with
  `or` (one kind in a condition; put an `if` inside an `if` for both).
* A script ends with a `play` that leaves (not a sound or subtitle switch)
  on every path, so the player always knows where to go; nothing may follow
  it in its block.

The project check reports a script it cannot read or the disc cannot hold,
and a script nothing runs. The simulator runs scripts (its state shows the
variables); a value outside 0 to 65535 or a division by 0 stops it there,
since what a player does then is not described. The flowchart draws an edge
to each place a script can go. Blu-ray and the web version have no scripts.

### Slideshows

```jsonc
"titles": [{
  "id": "holiday", "name": "Holiday",
  "slideshow": {
    "slides": [{ "image": "media/beach.jpg", "duration": 6 },   // seconds, default 5
               { "image": "media/hills.png" }],
    "transition": "crossfade",        // dissolve, fadeblack, fadewhite, wipeleft/right/up/down,
                                      // slideleft/right/up/down, circleopen/close, radial,
                                      // pixelize, random, or "none" (cuts); a slide's own
                                      // "transition" sets the change to the next one
    "transition_duration": 1,         // seconds, shorter than every slide
    "pan_zoom": true,                 // a slow zoom in / out on every picture
    "fit": "fill",                    // fill the frame (edges cropped); default "fit"
    "audio": "media/music.m4a",       // trimmed to the show and faded out; or a list,
                                      // played one after another
    "fit_to_audio": false,            // true: durations become proportions of the music's length
    "advance": "auto",                // "manual": each picture held until Next / Play (cuts, no music)
    "background_color": "#000000"     // around pictures of another shape
  },
  "end_action": "menu:main"
}]
```

The pictures are fitted on the disc's square-pixel canvas (854 × 480 for NTSC
16:9) and rendered once into a lossless video in `.oncemore-cache/slideshow`;
that video is then encoded like any other title (and re-rendered only when a
picture, a duration or a setting changes). Slide *k* starts at the sum of the
earlier durations and is a chapter unless `chapters` is given. A slideshow
can have up to 999 pictures; a DVD title has at most 99 chapters, so on a DVD
the pictures after the 98th are part of chapter 99 (one advanced by hand has
at most 99 pictures there), while a Blu-ray keeps a chapter for each. `fit` decides
what happens to pictures of another shape: `fit` shows all of each with the
background colour around, `fill` fills the frame and crops what is outside;
a slide can have its own `fit`. With `fit_to_audio` the pictures' durations
are scaled (in proportion) so the slideshow lasts exactly as long as its
music; the chapters move with them.

### Titles made of clips

```jsonc
"titles": [{
  "id": "evening", "name": "The evening",
  "clips": [
    { "source": "media/arrival.mov", "in": "00:01:10", "out": "00:03:00" },
    { "source": "media/speech.mp4" },                  // the whole file
    { "source": "media/phone.mp4", "out": 42.5 },      // seconds or HH:MM:SS(.mmm)
    { "source": "media/group.jpg", "duration": 6, "fit": "fill" }  // a still picture
  ],
  "end_action": "menu:main"
}]
```

The clips play one after another as one title, joined while the title is
encoded (nothing is rendered beforehand). Each clip is converted to the
disc's format on its own, so sizes, frame rates and sound formats can differ;
a clip without sound gets silence. Clip lengths are rounded up to whole
frames so picture and sound meet at every join. Clip *k* starts a chapter
unless `chapters` is given. All clips 23.976p film keep soft pulldown, all
interlaced stay interlaced; a mix is made progressive. A clip title has one
sound track (`audio_tracks` and `audio.passthrough` are not available).
Menu thumbnails and poster frames pick the clip that plays at that time.

A still picture (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.webp`,
`.gif` (its first picture), `.tga`) is shown for its `duration` (default 5 s, 0.5 s to 1 hour; no `in` / `out`) and
is silent. `fit` (default) shows all of it with black bars where its shape
differs from the frame; `fill` fills the frame and crops the edges.

### Audio tracks and subtitles

```jsonc
"titles": [{
  "id": "t1", "source": "media/movie.mp4",
  "audio": { "codec": "ac3", "bitrate": "192k" },          // applies to every track
  "audio_tracks": [
    { "lang": "ja" },                                       // stream 0 of `source`
    { "source": "media/commentary.wav", "lang": "en" },     // another file
    { "stream": 1, "lang": "fr" }                           // 2nd audio stream of `source`
  ],
  "subtitles": [
    { "file": "media/ja.srt", "lang": "ja", "default": true },
    { "file": "media/en.srt", "lang": "en" }
  ]
}]
```

* Tracks are padded with silence / cut to the video length; a missing stream
  is reported by `validate`.
* Stream *n* has one language for the whole disc (DVD stores stream attributes
  per titleset), so `lang` must agree between titles.
* Subtitles are SubRip (`.srt`), WebVTT (`.vtt`), ASS / SSA (`.ass`, `.ssa`) or
  a text script (`.txt`: on each subtitle's first line its number, start and
  end timecode and text, more lines of text after it; `hh;mm;ss;ff` is NTSC
  drop frame, `hh:mm:ss:ff` counts the disc standard's frames), UTF-8,
  UTF-16 or Shift_JIS. A track's `"offset"` (seconds, `"HH:MM:SS"` or a timecode such as
  `"01;00;00;00"`) is taken off every subtitle's time, for a file timed
  against a source's own timecode. Each cue is drawn with the menu font (white with an
  outline, see `disc.subtitle_style`), reduced to a 4-colour DVD subpicture and
  muxed into the title by vtskit; overlapping cues are shortened.
* Closed captions (`captions`): line-21 captions (CEA-608, CC1) for TVs and
  players with a caption decoder, written into the DVD's MPEG-2 video (user
  data after each GOP header, as DVDs carry them) and flagged in the IFO. An
  `.scc` caption file's byte pairs go in as they are; a subtitle file (any
  of the formats above) becomes pop-on captions: up to four centred rows of
  32 characters, Latin letters (other characters become spaces), loaded
  before their time, shown at their start and erased at their end. NTSC
  only, on 29.97 fps pictures (a film title with 3:2 pulldown is refused:
  set its scan to interlaced); Blu-ray and web builds leave them out.
* Image scripts: a text script whose subtitle text is a picture file next to
  the script (`.png`, `.bmp`, `.tif`, `.jpg`, `.webp`, `.gif`, `.tga`) shows that picture in
  its own colours. A picture without transparency has its top-left colour
  keyed out; a frame-sized one (480, 576, 720 or 1080 lines) fills the
  frame, a smaller one is centred at the bottom (or top) margin. A DVD keeps
  each picture's three commonest colours (a title's subpictures share 16),
  a Blu-ray up to 255 with their opacity. Import the script and its pictures
  together (Timeline > Import subtitles). An image script may open with
  `Display_Area (left top right bottom)`, where every picture is drawn, and
  `Directory <folder>`, where the pictures are (tried first; the script's own
  folder after it). A FAB image script gives each picture its own place, one
  line each: `picture start end left top right bottom`, the pictures next to
  the script. The places are pixels of the DVD frame (720 × 480 or 576, or
  1920 × 1080 when a number goes past those), scaled with the frame on a
  Blu-ray.
* Placement and colour: a track's `"position": "top"` and `"color": "#FFFF00"`,
  overridden per cue by `{\an8}` (SRT / ASS), `line:0` (WebVTT), an ASS style's
  alignment, `{\c&HBBGGRR&}` or `<font color="#RRGGBB">`. A title can use 16
  subpicture colours in all, about 7 different text colours.
* `"default": true` turns that subtitle stream on when the disc starts
  (players keep the viewer's later choice). Without one, a Blu-ray starts with
  subtitles off and a DVD leaves it to the player's language setting
  (`disc.subtitles_off: true` starts it with them off).

**Coordinates** are DVD pixels: 720 × 480 (NTSC) or 720 × 576 (PAL), whatever
the aspect ratio. oncemore draws text on a square-pixel canvas and squeezes it,
so lettering is never stretched on 16:9 discs. A button's hit area is computed
from where its label is actually drawn; up/down/left/right moves are computed
from the button positions (with wrap-around within a row/column).

### Blu-ray

The same project builds as a Blu-ray: `oncemore build <project> -o out/
--format bluray` for the BDMV folder, `oncemore iso <project> -o bd.iso
--format bluray` for a disc image, or Format: Blu-ray in the app's Build
panel (image, folder, or the image burned to a blank BD). A project made for
a Blu-ray says so (`disc.format: "bluray"`: the app's New Project and the
disc's Properties choose it as the Authoring mode); then building, Check
project and `oncemore validate` make a Blu-ray without being told, and
`--format dvd` still makes the DVD. oncemore writes the
whole BDMV folder itself, and the image with its own UDF 2.50 writer (the
file system of Blu-ray discs: the directory tree is stored twice, in a
metadata file and its mirror):

* every title in HD (1920×1080, H.264 with x264's Blu-ray settings; film at
  23.976p, NTSC video as 29.97 and PAL as 25 frames per second in a 1080i
  stream), with its audio tracks (AC-3, LPCM, or DTS copied from the source:
  DTS-HD Master Audio or High Resolution kept whole, 7.1 too) and their
  languages. With
  `disc.bluray.video: "720"` (Build > Picture) the whole disc is 1280×720
  progressive at 59.94 (NTSC) or 50 (PAL) frames a second instead, so 60p
  and 50p sources and the fields of 1080i ones keep their motion (film stays
  23.976p); menus and subtitles are drawn for the same frame;
* chapters on frames made key frames, so they start exactly there;
* first play, each title's end action when it starts another title, the
  project's playlists (chapter ranges included) and Play All as Blu-ray
  playlists, and the Top Menu key starting `disc.title_key`;
* subtitles as Blu-ray PGS streams: the same tracks, cues, colours and
  positions as on the DVD, drawn for the HD frame with smooth edges (64
  shades instead of a DVD's 4); the track marked `default` is shown from
  the start. A cue ends 0.2 s before the next one begins, which players
  need to decode it;
* menus: every menu, drawn exactly as for the DVD at HD size (texts,
  pictures, thumbnails, chapter menus, PSD artwork), with its buttons as a
  Blu-ray interactive menu: the same highlights in full colour, the same
  routing, links to titles, chapters, playlists, Play All and other menus,
  stream changes, Resume, end-action overrides and the remote's Top Menu
  key. A title's Menu-key menu (`remote_menu`) is its pop-up menu: the
  remote's Pop-up key shows its buttons over the playing picture. Still
  menus hold their picture; menus with motion or music repeat
  (from the loop point); with a loop count a menu plays that many times
  (a still one for its length each time) and then follows its end action;
* `disc.bluray.target` (`BD25` or `BD50`) caps the video rate so the
  titles always fit.

The tests read every Blu-ray back with libbluray, the library VLC, mpv and
Kodi play Blu-ray with: titles, lengths, chapters, streams, first play
through the title end actions, and menus driven with the remote's keys
(which button lights up in which colour, where each key goes); images are
also read file by file with libudfread.

### The web version

The same project also builds as a folder a browser plays as the disc:
`oncemore build <project> -o web/ --format web`, or Format: Web (HTML5) in
the app's Build panel (File > Build > Web (HTML5)…). Open `index.html` from
the folder, or put the folder on any web server; nothing else is needed.

* the menus as on the disc: their pictures (a video for a motion menu or a
  menu with sound), the buttons where they are, with their highlights;
  arrow keys and Enter, the mouse, and the number keys;
* every title as an MP4 (H.264, 720 lines, square pixels; its first sound
  track in AAC), with its chapters and its subtitles as WebVTT;
* the disc's links: buttons, end actions, Play All, playlists, the Menu
  (M) and Title (T) keys, resume, last menu, menu time-outs, link
  transitions; PageUp / PageDown change chapters. The player follows the
  same rules as the disc simulator, and the tests press the same keys in
  both and compare where they land.

A browser plays one sound track (the first) and draws subtitles as text:
picture subtitles are left out.

## How it works

```
sources ─ffprobe─▶ plan bitrate ─ffmpeg (2-pass MPEG-2 + AC-3/LPCM)─▶ titles/*.mpg
menu JSON ─ffmpeg drawtext─▶ base.png ─▶ menu.mpg
navigation (dvdauthor's command language) + menus + titles ─vtskit─▶ VIDEO_TS ─built-in UDF + ISO 9660 writer─▶ disc.iso
```

* **Bitrate**: from the total title length, the audio bitrates, a menu
  allowance and 2 % safety margin, capped at 8 Mbit/s video and 9.8 Mbit/s total.
* **Picture**: scaled and letter-/pillarboxed into 720×480/576, converted to
  29.97 or 25 fps, DAR flagged as 4:3 or 16:9, BT.601 colour.
* **Chapters** are frame-accurate: key frames are forced at chapter points and
  the GOPs before them are planned so each chapter starts its own VOBU (DVD
  requires VOBUs of at least 0.4 s; a short GOP would otherwise be merged with
  the one before and move the chapter up to half a second early).
* **Menus** all live in one titleset; buttons jump straight to menus, titles and
  chapters. A title can only *call* its titleset's root menu, so returning to
  another menu goes through the root menu with the target number in GPRM `g1`.
* **Titlesets**: DVD stores one video/audio format per titleset, so titles are
  grouped by (aspect, audio codec) automatically; a 4:3 LPCM title next to 16:9
  AC-3 ones simply lands in titleset 2. Menus stay in titleset 1, jumps across
  titlesets go through pad program chains (what dvdauthor calls jumppads), and
  a title in another titleset returns to a menu through the VMGM top menu.
* **Highlights** are the buttons' shapes as a 2-bit subpicture, written into
  the menu VOB by vtskit; **navigation commands** are written in dvdauthor's
  command language (`oncemore/author.py`) and compiled by vtskit, so the
  disc's logic reads the same as before the switch.

## Checking the result

Automated: `python -m unittest` runs unit tests and, when the tools are
present, end-to-end tests that build the sample ISO, inspect it with ffprobe /
xorriso, and **press the menu buttons through libdvdnav** (the navigation
library VLC uses) to check chapter jumps and returns to the menu.

By hand:

* **VLC** — `vlc dvd:///path/to/demo.iso`. Menus, button navigation, chapter
  jumps and the return to the menu work (checked with VLC 3.0.20 on Linux by
  driving the remote-control keys). Opening the `.iso` from VLC's GUI should
  behave the same but has not been checked on macOS yet.
* **mpv** — `mpv dvd://0 --dvd-device=demo.iso` plays title 1 (`dvd://1` is
  title 2). mpv **does not support DVD menus** (stated in its manual), so use it
  only to check the titles. When a title ends, mpv follows the disc program into
  the menu and keeps looping it without buttons — press `q`.
* **macOS DVD Player** — double-click the ISO to mount it, then in DVD Player
  choose *File → Open DVD Media…* and select the mounted `VIDEO_TS` folder
  (Apple documents opening VIDEO_TS folders for DVD Player 6.0 on macOS 26).
  Not yet verified by the authors with oncemore output — reports welcome.
* **A set-top player** — `oncemore testdisc player-test` (add `--format
  bluray` for a Blu-ray), or *Player test disc* in the app's New Project,
  makes a disc that uses every feature a player has to get right: the menus
  and the remote's Menu and Title keys, chapters and a chapter menu, two
  sound tracks and two subtitle tracks, a 4:3 title, 5.1 sound that names
  each speaker as it sounds, a motion menu with a loop point, and buttons
  over a title (DVD) or a pop-up menu (Blu-ray). Every title says on screen
  what you should see and hear. `TEST-CHECKLIST.md` beside the project lists
  what to press and what should happen (English and Japanese); build the
  image (`oncemore iso player-test -o player-test.iso`), burn it, follow the
  list and [report the player and the
  results](https://github.com/kajisho5/oncemore/issues/new?template=player-test.md).
* **Burning** — `oncemore burn demo.iso` (or Build > Output: DVD disc) runs
  `hdiutil burn` on macOS and `growisofs -dvd-compat` on Linux; any other
  burning tool works on the ISO as well. A dual-layer image gets its layer
  break (`-use-the-force-luke=break:N`); `hdiutil burn` has no such option
  and chooses the place itself.

## Rebuilding is fast

Encoded titles and menus are kept in `<project>/.oncemore-cache/encode`, keyed
by their sources (path, size, modification time), settings, bitrate, the ffmpeg
version and oncemore's own encoding code. A rebuild after a menu tweak only
renders that menu. Use `--no-cache` (or *Encode everything again* in the app)
to encode everything again (the cache is refreshed with the new encodes), and
`oncemore clean <project>` to delete the cache and reclaim the space (it is
all made again by the next build).

The cache (encodes, rendered slideshows, joined clips, playback copies) can
live elsewhere, say on a larger or faster drive: Preferences > Media cache,
or `ONCEMORE_CACHE=/path` on the command line. Each project then gets its
own folder in it, named after the project folder.

## Known limitations

* Motion menus loop one video (with an optional intro). Thumbnails play, and
  texts and pictures can come in once (`animate`), but there are no keyframed
  animations; a button's link transition is the way from one menu to another.
* Encoded audio is stereo or 5.1 (AC-3 or LPCM), unless `audio.passthrough`
  copies 48 kHz AC-3 sources; DTS is copied only (`audio.codec: "dts"`, 5.1 or
  more: a Blu-ray keeps DTS-HD whole, a DVD its core), and a title's tracks
  share one format (no DTS track beside an AC-3 one).
  Text subtitles: one font and size per disc, lines centred at the top or
  bottom (image subtitles can be placed anywhere); at most 16 subpicture
  colours per DVD title.
* Audio/subtitle stream *n* has one language for the whole disc. Menus have
  one aspect ratio (`disc.aspect`); titles may differ.
* Frame rates: 23.976p film on NTSC gets soft 3:2 pulldown; interlaced
  sources at the disc's rate and 59.94p / 50p sources are stored as fields
  (`scan`). Other rates (e.g. 25 fps on NTSC, 24 / 23.976 on PAL) are
  converted by dropping or repeating frames. Film that was already telecined
  to 29.97i is not detected by itself: choose `scan: ivtc` (Picture:
  Telecined film) to recover its film frames.
* `xorriso` cannot write UDF; images made with it are ISO 9660 only and are
  **not** opened by libdvdread-based players (VLC, mpv) or most DVD players.
  It is only used when chosen with `--iso-tool xorriso`, with a warning.
* The built-in ISO writer lays the disc out like genisoimage `-dvd-video
  -udf` (same sector for every file on the test discs, files placed where
  the IFOs say, UDF 1.02 + ISO 9660 bridge). It keeps one timestamp for the
  whole disc, not each file's.
* Highlights on a DVD are hard-edged (2-bit subpictures). Each text and button
  uses one font (the disc's or its own); every character must exist in it
  (drawtext has no fallback): oncemore checks the font's character map and
  stops instead of drawing empty boxes.
  Emoji are not supported.
* With `hdiutil` images, libdvdnav-based players (e.g. VLC) show no disc
  *title metadata*: libdvdnav reads the title raw from sector 32, where real
  DVDs and genisoimage keep the UDF volume descriptor, and hdiutil puts it
  elsewhere. The UDF and ISO 9660 volume names themselves are correct
  (checked by the tests); playback is unaffected.
* A Blu-ray pop-up menu shows the menu's buttons (whatever lies inside each
  button's area) over the picture; texts and pictures elsewhere on the menu
  and its background are left out. 4:3 titles and menus are
  pillarboxed in the 16:9 HD frame. Burning a BD uses the same tools as a DVD; growisofs
  documents BD media, `hdiutil burn` with a BD writer has not been tried.
* Navigation scripts (`commands:<id>`) are for DVD; a Blu-ray or web build
  with one stops with a message.
* Buttons over a title are for DVD, and not yet beside subtitles in the same
  title (the player lights a button in the subtitle stream it shows); the
  web version plays the title without them, and a Blu-ray build stops with a
  message.
* No copy protection (by design, permanently).

## Libraries

Parts of oncemore are published on their own, on PyPI, for other tools to
use. They are pure Python with no dependencies, like oncemore:

| Library | What it does | License |
|---|---|---|
| [udfkit](https://github.com/kajisho5/udfkit) | DVD-Video (UDF 1.02 + ISO 9660) and Blu-ray (UDF 2.50) disc images | Apache-2.0 |
| [bdmvkit](https://github.com/kajisho5/bdmvkit) | Blu-ray (BDMV) authoring: titles, playlists and menus and the navigation between them, clip information, PGS subtitles | LGPL-3.0-or-later |
| [dvdcc](https://github.com/kajisho5/dvdcc) | Line-21 closed captions (CEA-608) into a DVD's MPEG-2 video | Apache-2.0 |
| [vtskit](https://github.com/kajisho5/vtskit) | DVD-Video authoring: IFO files, navigation packs, menus, subtitles, angle blocks, dvdauthor's command language | LGPL-3.0-or-later |

Changes to them are made and released in their own repositories, and
oncemore carries a copy of each release (`oncemore/_vendor`, updated with
`tools/vendor.py`), so it still installs with no dependencies. All four are
carried so. On Blu-ray, bdmvkit writes the navigation (titles, playlists,
menus' commands, movie objects) and its files, the menus' button streams
and the PGS subtitles; oncemore still encodes the clips and draws the menus
and pop-up menus (each button's pictures) itself, until bdmvkit releases
those.

Every day `.github/workflows/library-updates.yml` looks on PyPI for a newer
release of each library oncemore carries and opens a draft pull request that
takes it, with CI run on it; merging it is still a person's call
(`python tools/vendor.py --outdated` shows the same list).

## Support oncemore

oncemore is free and stays free. If it saves you time, you can support its
development through [GitHub Sponsors](https://github.com/sponsors/kajisho5) (the **Sponsor** button at the top
of this repository); every sponsorship goes to keeping it going. Bug reports
and discs that do or do not play on your player help just as much:
[Issues](https://github.com/kajisho5/oncemore/issues).

## License

GPL-3.0-or-later (see [LICENSE](LICENSE)).
"Encore" and "Adobe" are trademarks of their owners; oncemore is not affiliated
with Adobe.
