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

**P23 — Every setting in the app** (done)
- [x] Button thumbnails (a picture of the linked title / chapter: place,
  size, frame, playing in motion menus), shown on the stage; the chapter
  menu's heading and button texts; the subtitle look (size, colours,
  outline, margin)

**P24 — End-action overrides** (done)
- [x] A title / chapter button can say where to go when that title ends,
  instead of the title's own end action, for that play only; drawn in the
  flowchart, checked against libdvdnav

**P25 — Streams with links** (done)
- [x] A button can switch the audio and subtitle streams along with its
  link ("play with commentary", "subtitles off and play")

**P26 — Return to the last menu** (done)
- [x] `lastmenu` end action for titles, playlists and overrides: back to
  the menu the viewer came from

**P27 — Burning** (done)
- [x] Build > Output: DVD disc (the image, then written to a blank DVD in
  the chosen recorder) and `oncemore burn`

**P28 — Blu-ray, titles and chapters** (done)
- [x] Build > Format: Blu-ray and `build --format bluray`: a BDMV folder
  with every title in HD H.264, AC-3 / LPCM tracks, chapters, playlists,
  Play All, first play and title end actions; BD25 / BD50; read back with
  libbluray in the tests

**P29 — Blu-ray image** (done)
- [x] Built-in UDF 2.50 writer (metadata partition with mirror): `iso
  --format bluray`, Build > Blu-ray > image / BD disc; read back with
  libudfread and libbluray

**P30 — Blu-ray subtitles** (done)
- [x] Subtitle tracks as PGS streams (64-shade palette, BT.709), the
  default track switched on by the title's movie object, a decoding gap
  between cues

**P31 — Chapter markers from the file** (done)
- [x] A source's own chapter markers (with names) become the chapters of a
  new title; Timeline > Import chapter markers from the source

**P32 — Pictures on menus** (done)
- [x] Logos and photos that are not buttons (`images[]`): Tools > Picture
  or Place on the menu, natural proportions, resize keeping them, opacity,
  Layers; PSD re-import replaces them with the new artwork

**P33 — Blu-ray menus** (done)
- [x] Every menu as an HDMV interactive title: drawn at HD like the DVD
  menu, buttons as an Interactive Graphics stream (highlights in full
  colour, routing, auto-activate), links to titles / chapters / playlists /
  menus, stream changes, Resume, Top Menu key, last menu; checked by
  pressing keys in libbluray

**P34 — Buttons after the intro** (done)
- [x] `buttons_at_loop`: a menu's buttons appear at its loop point (or after
  the fade-in), on DVD and Blu-ray

**P35 — Still pictures in timelines** (done)
- [x] Still pictures as clips of a title, shown for a set time, silent
- [x] Scaling of pictures of another shape: fit (bars) or fill (cropped), for
  clips, slideshows and single slides

**P36 — Links to a menu button** (done)
- [x] `menu:<id>:<button id>`: any link opens the menu with that button
  highlighted, on DVD and Blu-ray, in the simulator, flowchart and link menus

**P37 — More end actions** (done)
- [x] Titles, playlists and overrides can end in a chapter, a playlist or
  play all (DVD across titlesets too, and Blu-ray)

**P38 — Blu-ray menu loops and overrides** (done)
- [x] Menu loop counts and the end action after them on Blu-ray (still
  menus held for their length)
- [x] End-action overrides on Blu-ray

**P39 — Slideshow music** (done)
- [x] Several pieces of music played one after another
- [x] Fit the pictures to the music (durations as proportions)

**P40 — Don't transcode** (done)
- [x] A source that already is DVD video goes on the disc as it is
  (`transcode: false`), checked against the disc's format

**P41 — Slideshow transitions** (done)
- [x] Dissolves, fades through black / white, wipes, slides, circles, radial,
  pixelate, random; per picture, mixed with cuts

**P42 — Blu-ray pop-up menus** (done)
- [x] A title's Menu-key menu is its pop-up menu on Blu-ray, shown over
  the picture with the Pop-up key

**P43 — Slideshows advanced by hand** (done)
- [x] `advance: manual`: every picture held until Next / Play, on DVD and
  Blu-ray

**P44 — Titles from sound files** (done)
- [x] A sound file as a title's source (music), shown with a still picture
  or black, on DVD and Blu-ray; thumbnails show the picture

**P45 — Link transitions** (done)
- [x] `transition` on a button: a video played when it is pressed, before
  its link (menu, title, chapter, playlist, play all), on DVD and Blu-ray;
  drawn in the flowchart, played in the simulator

**P65 — Random and shuffled playlists** (done)
- [x] `order` on a playlist: sequential, random or shuffle; on Blu-ray the
  movie object picks the items (Set RND), each item its own playlist
  file; the web version picks them the same way; a DVD plays them as
  listed (a warning)
- [x] Playlist panel > Order

**P64 — Menus with pages** (done)
- [x] `pages` on a menu and `page` on its objects (none: every page);
  `page:next`, `page:prev`, `page:<n>` links; each page a menu of its own
  on DVD, Blu-ray and the web version, played back by libdvdnav and
  libbluray in the tests
- [x] Menu > Add new page / Delete page, a page strip in the viewer,
  Properties > Page, page links among a button's links

**P62 — Paragraphs** (done)
- [x] Menu texts of several lines: `align` (left, centre, right) and
  `line_spacing`, drawn the same way on DVD and Blu-ray menus and the web
  version; a text box with Return for new lines, Lines and Line spacing in
  the Properties

**P61 — Layer break** (done)
- [x] `disc.layer_break` for a DVD-9: a chapter, or auto (the first one
  past the middle of the disc); checked against the disc's rules (an ECC
  block, the first layer the larger, a layer's size)
- [x] The built-in ISO writer moves VIDEO_TS so the chapter is on an ECC
  block; `oncemore iso` reports the sector; burning passes it to growisofs
- [x] Disc panel > Layer break

**P60 — My styles** (done)
- [x] Library > My styles: the look of a text, button or shape (font,
  size, colour, outline, shadow) saved under a name with its font, for
  any menu of any project; applied to the selection (a shape takes the
  colour), deleted from the library

**P59 — Closed captions** (done)
- [x] `titles[].captions`: line-21 captions (CEA-608) on NTSC DVDs, from a
  Scenarist .scc file or any subtitle file (pop-on), in the video's GOP
  user data, flagged in the IFO; read back by ffmpeg's caption decoder in
  the tests; a field in the app's title properties

**P58 — Web version** (done)
- [x] `build --format web` (and Build > Web in the app, `build` in MCP): a
  folder a browser plays as the disc: the menus with their buttons and
  highlights, the titles as MP4 with chapters and WebVTT subtitles, and a
  player following the disc's links (checked key by key against the
  simulator)

**P57 — Image scripts** (done)
- [x] Subtitles that are pictures: a text script whose text is a picture
  file (keyed or with transparency, frame-sized or smaller), in its own
  colours on DVD (three per picture, 16 per title, checked) and Blu-ray
  (255 with opacity); imported with its pictures, shown on the timeline,
  written back as an image script

**P56 — Blu-ray: H.264 used as it is** (done)
- [x] `transcode: false` on a Blu-ray copies an H.264 picture that already
  is Blu-ray video (profile, level, frame, rate, 1080i field coding read
  from the stream, key frames, bitrate), with its parameter sets reordered
  as a Blu-ray stream has them; anything else is encoded with a warning
  naming why; the disc plan keeps the copied picture's own rate

**P55 — DTS sound** (done)
- [x] `audio.codec: "dts"`: DTS copied from the sources unchanged (the DTS
  core of a DTS-HD source), on DVD (its own titleset; a warning that DVD
  players need not decode DTS) and Blu-ray; checked at build time (48 kHz
  DTS, the channels, 1536k at most on a DVD); DTS in the app's codec list

**P54 — Button numbers** (done)
- [x] Properties > Number renumbers a button (the others close up); a menu's
  button number offset for the number keys, on DVD (the navigation packs'
  button offset number) and Blu-ray (each button's numeric select value);
  numbers in the routing view; number keys (two digits) in the preview

**P53 — Subtitle scripts, chapter names in the ruler** (done)
- [x] Text-script subtitles (`.txt`: number, start and end timecode, text):
  read as tracks (drop-frame and non-drop-frame NTSC, PAL timecode),
  imported with an absolute or relative timecode (`subtitles[].offset`),
  exported from any track as a text script or SubRip (Timeline > Export
  subtitles ▸ SubRip / Text script)
- [x] View > Show chapter names: chapter names in the timeline's time ruler

**P52 — Guides, rotate and flip** (done)
- [x] Guides on a menu: View > Show / Lock / Clear guides, New guide…, Snap
  to guides; dragged to move, off the menu to remove; kept with the menu and
  brought from a Photoshop file's guides
- [x] Object > Rotate (180°, 90° CW, 90° CCW), Flip horizontal / vertical, the
  Rotate tool (Shift: 45° steps) and the angle in Properties, for texts,
  buttons, rectangles and pictures; drawn turned on DVD and Blu-ray menus,
  with button highlights turned with them

**P50 — Hardening from a code review** (done)
- [x] Blu-ray: a menu link that picks audio / subtitles and plays a title
  keeps them (the title's default subtitles no longer replace them);
  `scan_m2ts` refuses broken streams instead of indexing them; a test
  driving pop-up, loop, end-action override, last menu and button links
  together through libbluray
- [x] Encode cache: menu keys follow every thumbnail's picture (clips after
  the first, a sound title's picture); `--no-cache` refreshes the cache;
  writers of one entry at once each write their own file; all encoding
  modules in the code hash; `oncemore clean`
- [x] Timelines: chapters at clips land on the clip's first frame at
  29.97 / 23.976; links and chapter menus can use every clip's chapter;
  thumbnails follow chapters once clips are measured or a slideshow is
  fitted to its music; long slideshows no longer drift from their chapters;
  a warning when the music is too short for the pictures
- [x] App: two previews made at a time, frames kept up to 64 MB, old jobs
  dropped, a page opened again picks up the running build or transcode
- [x] DVD: `transcode: false` checks 4:2:0, GOP length, VBR and total rates,
  accepts half D1, and gives copied film its pulldown; "the last menu"
  from a later titleset before any menu opens the Menu-key menu; subtitle
  colours counted as drawn

**P51 — AI assistants (MCP)** (done)
- [x] `oncemore mcp`: an MCP server over stdio (revision 2026-07-28 and the
  earlier initialize-based ones) whose tools create, read and change
  projects, bring media in, validate, render menus, simulate the remote and
  build in the background; only inside allowed folders

**P49 — Remote keys turned off (user operations)** (done)
- [x] `prohibit` on a title or a menu: next / previous chapter, fast forward,
  rewind, pause, stop, the number keys, the Menu and Title keys, audio and
  subtitle changes; on a DVD the program chains' prohibited user
  operations (and the title search table), on a Blu-ray the playlists' UO
  masks; the simulator ignores them too; checkboxes in Properties

**P48 — The whole menu bar** (done)
- [x] File, Edit, Object, Menu, Timeline, View, Window and Help with
  submenus and every command behind them: new / open / open recent / save /
  save as projects, import as menu / timeline / slideshow / pop-up menu,
  locate asset, interpret footage, transcode settings, render slideshows,
  DVD-ROM content, build presets; cut / copy / paste / select all / rename /
  edit original; align to the safe area, distribute, arrange forward /
  backward, convert, drop shadow and stroke; add objects, default button,
  colour set, save menu as a picture; chapter playlists, audio and
  subtitle tracks, subtitles exported as SubRip, poster frames, frames
  saved as pictures, clear chapters; zoom, snap, highlights; reset workspace;
  help
- [x] Oncemore.app's native menu bar made from the page's (same items,
  language, keys, greyed and ticked state)

## Next

What is still to do, in order. Each item becomes a numbered milestone (one
pull request with tests) when it is started.

**Parity: what the classic apps did that oncemore does not yet** (checked
against their published help, not from memory)

- [x] Multi-page menus (P64): one menu with several pages of buttons
  (Menu > Add new page), objects on one page or on every page, buttons to
  the next, previous or a given page; each page a menu of its own on the
  disc (DVD, Blu-ray and the web version). The chapter index was already
  spread over pages
- [ ] Multi-page menus from a Photoshop file, a layer group per page (each
  page with its own artwork)
- [ ] DTS-HD kept as it is on Blu-ray (today DTS is cut down to its core)
- [x] Chapter playlists played in random order or shuffled, on Blu-ray and
  the web version (DVD keeps the order, as the classic apps did) (P65)
- [x] Slideshows of more than 99 pictures (the rest in the last chapter on
  DVD; up to 999 on Blu-ray) (P66)
- [ ] Text: letter spacing, kerning, bold and italic (of fonts that have
  those faces)
- [ ] Highlights: make a button's highlight layer from its own pixels or a
  shape in the editor, and replace it with another picture
- [ ] Replace a menu's background and layout with a template, keeping its
  buttons' links
- [x] Media cache in a folder of your choosing (Preferences) (P68)
- [ ] Bit budget: per title and menu, the bitrate and the space it takes
  on the disc, as a bar of the whole disc, before anything is encoded

**Beyond the classic apps**

- [ ] Check for Updates (Help): says which version this is and opens the
  releases page in the browser. oncemore itself makes no connection (no
  network access is one of its promises), so it does not look by itself
- [ ] Chapters from the picture: suggested chapter points where the scene
  changes, and the best thumbnail frame near each, to accept or drop
- [ ] Loudness: measure each title's loudness and offer to even them out
  (EBU R128), so menus and titles do not jump in level
- [ ] Quality preview: encode a few seconds at the planned bitrate and show
  them next to the source before the whole build
- [ ] Player test disc: one command builds a disc that exercises menus,
  remote keys, audio / subtitle switching and end actions, with a printed
  checklist, so people with a set-top player can report what works
- [ ] Share templates and styles: export menu templates and my styles as one
  file, and import it on another computer (fonts included)
- [ ] Accessibility of the app: keyboard reach for every panel, labels for
  screen readers, a high-contrast theme
- [ ] Accessible discs: menu templates with large, high-contrast buttons
  and highlights; an audio description track marked as such
- [ ] Watched marks: chapter menus that show which chapters were played,
  kept in the player's registers while the disc is in
- [ ] Batch builds: build several projects (a series) in one go from the
  command line and the MCP server, with one shared template
- [ ] Web version for hosting: an app manifest and offline caching when
  it is served from a web site (opening the folder from disk works today)
- [ ] Multi-angle titles, and DVD titlesets written by oncemore itself
  instead of dvdauthor ([#75](https://github.com/kajisho5/oncemore/issues/75))

**Not planned**

- Copy protection and region codes of any kind (never).
- DDP masters. The DDP format is not published: its specification comes
  only under a licence agreement with its owner. A disc image or a DVD-R
  master is what oncemore makes for replication.
- Built-in AI services (menu design, subtitle translation). oncemore keeps
  everything on your own computer; an AI assistant can already author
  through `oncemore mcp`, which is where such help belongs.
- Cloud builds and remote encoding (same reason: local first).
- BD-J (Java) Blu-ray menus; the classic apps did not make them either.

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

Menu-less BDMV with titles, chapters and playlists (P28) and its UDF 2.50
image (P29), PGS subtitles (P30) and menus (P33), menu loop counts and
overrides (P38), pop-up menus (P42): done.

## Later

* Replace dvdauthor with a built-in IFO/VOB writer ([#75](https://github.com/kajisho5/oncemore/issues/75)).
* Built-in UDF 1.02 + ISO 9660 bridge writer, so no external ISO tool is
  needed on any platform (xorriso cannot write UDF; see DECISIONS.md).
