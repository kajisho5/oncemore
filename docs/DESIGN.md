# Design system

How the authoring app looks and is put together. The living version is the
style guide page served by the app itself: open `/styleguide.html` next to
the app's address (e.g. `http://127.0.0.1:PORT/styleguide.html`).

## Principles

1. **Pictures read true.** The workspace is neutral grey in both skins
   (Edit > Preferences: Skin, light theme, Brightness). Menus and video sit
   on black, never on a tinted surface, so colours are judged against what a
   TV shows.
2. **Two skins, one layout.** *Modern* (the default): dark panels on a darker
   ground, dark fields, flat controls, underlined tabs, blue for the panel in
   use, for timecode and for selection. *Classic*: the classic disc
   authoring look — mid-grey panels, light fields with dark text, raised
   controls, boxed tabs with grips, amber outline and amber timecode. Only
   tokens and a short block of Classic-only rules differ; components are
   shared. The DVD highlight colours (yellow, orange) stay for what is on
   the disc in both.
3. **Every kind of object has one colour, everywhere.** Menus are yellow,
   titles green, playlists purple, remote-control and system entries blue,
   audio teal, subtitles pink, chapters orange: in the project panel, the
   flowchart, the timeline and the layers panel alike.
4. **The workspace is the classic one.** The layout (both skins) and the
   Classic skin's palette and controls follow the professional disc
   authoring app people learned on: a menu bar, a Tools
   panel with the Workspace menu, a Project frame (Project · Menus ·
   Timelines · Build) and the viewers (Monitor · Menu Viewer · Flowchart)
   side by side, the Timeline across the bottom of both, Properties and
   Library / Layers in a column on the right; tabs with a grip and a close
   box, light text fields, right-aligned labels. The greys were measured from
   that app's published help. Icons and wording are our own; no names, icons,
   artwork or screenshots of other products are used.
5. **Nothing is hidden behind modes.** Every setting of the selected object
   is in the Properties panel; the editor shows the disc exactly (exact
   preview, simulator) rather than an approximation.
6. **Two languages, same layout.** Every string exists in English and
   Japanese; layouts are checked with the longer of the two.

## Tokens

All values live in `oncemore/gui/static/tokens.css`. Components use the
variables only (a test fails if a stylesheet uses an undefined variable or a
raw hex colour outside the tokens).

| Group | Tokens |
|---|---|
| Surfaces | `--c-bg-0` gaps between frames, `--c-bg-1` panels, `--c-bg-2` tab strips / bars, `--c-bg-3` selected rows, `--c-bg-4` raised (headers, buttons, back tabs), `--c-bg-5` track headers, `--c-field` text fields, `--c-line`, `--c-line-strong`, `--c-scrim` |
| Text | `--c-text`, `--c-text-2` (labels, hints), `--c-text-field` (in text fields), `--c-text-on-accent`, `--c-text-on-ui` |
| Skin | `--raised`, `--raised-hi` (controls, headers), `--bevel`, `--field-shadow`, `--c-field-border`, `--r-field`, `--foot-h`; `:root[data-skin="classic"]` redefines these and the colours, type sizes, radii and bar heights |
| Working | `--c-active-panel` (outline of the panel in use), `--c-timecode`, `--c-playhead`, `--c-clip`, `--c-clip-head`, `--c-clip-audio`, `--c-clip-text` (timeline clips), `--c-ui`, `--c-ui-soft` |
| Accent | `--c-accent` (highlight yellow), `--c-accent-2` (activated orange), `--c-focus` |
| Status | `--c-success`, `--c-warning`, `--c-danger` |
| Kinds | `--c-kind-menu`, `-title`, `-playlist`, `-remote`, `-audio`, `-subtitle`, `-chapter` |
| Picture | `--c-picture` (black), `--c-on-picture`, `--c-guide` (snapping), `--c-hit` (hit areas) |
| Type | `--font-ui`, `--font-mono`, `--fs-xs` 11 / `-sm` 12 / `-md` 13 / `-lg` 15 / `-xl` 20, `--lh` |
| Space | `--sp-1` 2 … `--sp-7` 32 (4 px grid) |
| Shape | `--r-sm` 4, `--r-md` 6, `--r-lg` 10, `--r-pill`, `--shadow-1`, `--shadow-2` |
| Workspace | `--panel-head-h`, `--left-w`, `--right-w`, `--timeline-h`, `--splitter` (the three sizes follow the splitters and are remembered per browser) |
| Motion | `--dur-fast` 120 ms, `--dur-med` 200 ms |

The light theme (`:root[data-theme="light"]`) redefines the colour tokens
only; sizes and spacing never change between themes. Contrast: body text and
labels stay at 4.5:1 or more on their surface in both themes.

## Workspace anatomy

```
┌ menu bar: File Edit Object Menu Timeline View Window Help (the Mac app: the system menu bar) ┐
├ Tools: ↖ T ⌕ │ ▭ ■ │ PSD ◎ ……………………………………………… Workspace: [Default ▾]  (search) ┤
├ Project · Menus · Timelines · Build ┬ Monitor · Menu: main · Flowchart ┬ Properties ────────┤
│ ▾ [thumb] name                      │                                  │      Timeline      │
│          type, size / length        │   picture on black               │   Name: [……]       │
│ Name ▴        │ Type     │ Duration │                                  │  End action: ◎ [▾] │
│ ▭ Title A     │ Timeline │ 00:00:24 │ Fit▾ ⬚ │ ⏮ ◀| ▶ |▶ ⏭ │ ◆ … 00:00:00.000 ├ Library · Layers ──┤
│ ⇩ ▣ ▤ ≡                       🗑     │                                  │                    │
├ Title A ▾ × ───────────────────────────────────────────────────────────┤                    │
│ Timeline: 00:00:00 │ ruler 00:00 ··· 00:10 ··· 00:20                     │                    │
│ ▣ Video            │ [clip ………………………………]                               │                    │
│ ◆ Chapters         │ 1        2        3                                │                    │
│ ◁ Audio 1          │ [clip ………………………………]                               │                    │
└────────────────────┴───────────────────────────────────────────────────┴────────────────────┘
```

* **Frames and tabs**: each tab strip starts with a grip; the front tab joins
  its panel and has a close box; ≡ on the right is the panel menu. The panel
  you last clicked in has an amber outline.
* **Project** shows a preview of the selection (picture, type, size, length)
  above the list; the bar at the bottom imports files, adds a slideshow, a
  menu or a playlist, and deletes. The search field in the Tools panel
  filters it. Clicking the preview selects the disc (its settings appear in
  Properties).
* **Build** is a panel in the Project frame: Check Project, output (disc
  image or VIDEO_TS folder), settings, disc info and the Build button.
* **Monitor** plays the open timeline: zoom, safe area, ±1 s, frame steps,
  play, chapter navigation with the chapter number, add chapter, timecode.
* **Timeline** stays across the bottom with the last opened timeline, also
  while a menu or the flowchart is in front; "(no Timelines)" until one is
  opened.
* **Flowchart**: the disc first, then cards with each item's picture and
  name; menus list their buttons under an orange band.
* **Project Preview** (File > Preview, ⇧Space) opens in a window of its own.

* **Menu bar**: File, Edit, Object, Menu, Timeline, View, Window, Help. Every item is
  a command (app.js `COMMANDS`) that the right-click menus, the keyboard
  shortcuts and Oncemore.app's native menu bar run too; inside the Mac app
  the page hides its own menu bar.
* **Tools panel** (under the menu bar): selection V, text T, zoom Z, new
  button, new rectangle, a menu from a Photoshop file, Preview; the
  Workspace menu and the search field on the right.
* **Menu Viewer**: the menu on black with a viewer bar under it (zoom, safe
  area, routing, snapping, normal / selected / activated highlights, exact
  preview).
  Overlapping button areas get a red (danger) outline.
* **Pick whip** (◎, remote blue) next to links in Properties: drag it to a
  project item or a flowchart box; the line follows the pointer and the
  target gets a remote-blue outline. Flowchart boxes link the same way when
  dragged; unused items sit below a dashed line.
* **Menu stage**: *Routing* overlays the remote-control routing (remote
  blue; set by hand: accent, solid; automatic: dashed; wrapping routes arc
  outside the buttons). Project items can be dragged onto a button (link) or
  onto the menu (new linked button).
* **Right-click menus** on titles, menus and playlists in the project panel,
  on files in Media and on elements of the menu stage.
* **Workspaces** (Workspace menu, Window menu, ⌥⇧1–4): Default returns to
  the last edited object; Flowchart, Project Preview and Build bring those
  forward.
* **Project panel**: the disc's objects and the media bin. **Library** tab:
  menu templates, backgrounds from the media, text styles (applied to the
  selected buttons / texts) and Photoshop designs.
* **Timeline** (titles): click the ruler or the picture to move the playhead,
  drag a chapter mark to move it (frame-accurate), click a subtitle to jump
  to it. − / + zoom.
* **Layers** (menus): every element top first, selection shared with the
  stage (shift-click adds), ▲ ▼ reorder, ✕ delete.
* Panels are resized by dragging the splitters; sizes are remembered.

## Components

| Component | Class names |
|---|---|
| Button | `button`, `.primary`, `.danger`, `.small`, `.icon` |
| Field | `label.field > span + input/select`, `.grid2`, `.row`, `.shrink` |
| Panel | `.panel`, `.panel-head` (`.title`, `.crumb`, `.kind-dot`), `.panel-body` |
| Tabs | `.tabs > .tab(.active)` |
| Tools panel, workspace menu | `.toolbar`, `.tools > .tool(.on)`, `.ws-select`, `.search` |
| Frames | `.frame(.active-frame)`, `.tabbar` (`.grip`, `.tab .x`, `.panel-menu`), `.panel-foot .ficon` |
| Properties rows | `#inspector label.field` (label right-aligned, field after it), `fieldset.group`, `.frow > .fl` |
| Monitor | `.monitor`, `.monitor-screen`, `.monitor-bar (.micon, .chnum, .tc-amber)` |
| Dialogs, windows | `.dialog (.dlg-title, .dlg-tabs, .dlg-page, .dlg-buttons)`, `.float-window (.fw-title, .fw-body)` |
| Tree / list rows | `.nav-item(.active)`, `.nav-head`, `.media-item`, `.layer-row(.selected)`, `.layer-group` |
| Library | `.lib-section`, `.lib-grid`, `.lib-item` |
| Timeline | `.tl`, `.tl-row`, `.tl-label`, `.tl-track`, `.tl-ruler`, `.tl-lane`, `.tl-clip.audio/.sub`, `.tl-chapter`, `.tl-playhead` |
| Card, notes | `.card`, `.hint`, `.issues li.warning/.info`, `.pill` |
| Modal | `#modal .modal-card` |
| Menu bar, pop-up menus | `.menubar > button(.open)`, `.popup > button(.danger)` with `.key`, `.sep` |
| Menu editor | `.menu-viewer > .tools (button.on, .sep)`, `.viewer-main`, `.viewer-bar (.seg)`, `.overlap` |
| Pick whip | `.whip`, `svg.whip-line`, `.whip-target` |

## Writing

* Sentence case for labels; verbs on buttons ("Import again", "Render & play").
* Say what will happen, not how ("Every picture starts a chapter").
* No third-party product names in the interface, the docs or the code.
* Japanese strings are written for Japanese readers, not translated word by
  word; keep both lists in `app.js` (`I18N.en`, `I18N.ja`) in step — a test
  checks that every key exists in both.
