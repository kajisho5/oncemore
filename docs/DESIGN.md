# Design system

How the authoring app looks and is put together. The living version is the
style guide page served by the app itself: open `/styleguide.html` next to
the app's address (e.g. `http://127.0.0.1:PORT/styleguide.html`).

## Principles

1. **Pictures read true.** The workspace is neutral grey (dark by default, a
   light theme is one click away). Menus and video sit on black, never on a
   tinted surface, so colours are judged against what a TV shows.
2. **One accent, and it means "highlight".** The accent yellow is the default
   DVD button highlight; it marks the selected thing (active tab, selected
   row, primary action). Orange is "activated / selected" as on a disc.
3. **Every kind of object has one colour, everywhere.** Menus are yellow,
   titles green, playlists purple, remote-control and system entries blue,
   audio teal, subtitles pink, chapters orange: in the project panel, the
   flowchart, the timeline and the layers panel alike.
4. **The workspace is familiar.** The layout is the one people already know
   from professional disc authoring and video editing — a project panel on
   the left, the editor in the middle with a timeline under it, properties
   and layers on the right, workspaces in the top bar. It is our own design:
   no names, icons, artwork or wording are taken from other products.
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
| Surfaces | `--c-bg-0` app, `--c-bg-1` panels, `--c-bg-2` raised / headers, `--c-bg-3` selected, `--c-field`, `--c-line`, `--c-line-strong`, `--c-scrim` |
| Text | `--c-text`, `--c-text-2` (labels, hints), `--c-text-on-accent` |
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
┌ top bar: brand · disc · save state │ Author  Flowchart  Preview  Build │ undo redo  Check  Build  ◐  文A ┐
├ Project | Library ─┬─ ● Menu  main ───────────────────────┬─ Properties ──────────┤
│ Disc               │                                      │ (everything about the │
│ Flowchart          │   editor: menu stage / title viewer  │  selected object)     │
│ Simulator          │   / slideshow / playlist / flowchart │                       │
│ Titles  + Slideshow│   / simulator / build                ├─ Layers ──────────────┤
│ Menus   + Add      ├──────────────────────────────────────┤ Buttons · Texts ·     │
│ Playlists + Add    │ Timeline: ruler · video · chapters · │ Rectangles · Background│
│ Media (drop zone)  │ audio tracks · subtitle tracks       │                       │
└────────────────────┴──────────────────────────────────────┴───────────────────────┘
  status bar: issues · missing tools · project folder
```

* **Workspaces** (top bar) switch the centre between authoring, the
  flowchart, the remote-control preview and the build; Author returns to the
  last edited object.
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
| Workspaces | `.workspaces > button(.active)` |
| Tree / list rows | `.nav-item(.active)`, `.nav-head`, `.media-item`, `.layer-row(.selected)`, `.layer-group` |
| Library | `.lib-section`, `.lib-grid`, `.lib-item` |
| Timeline | `.tl`, `.tl-row`, `.tl-label`, `.tl-track`, `.tl-ruler`, `.tl-lane`, `.tl-clip.audio/.sub`, `.tl-chapter`, `.tl-playhead` |
| Card, notes | `.card`, `.hint`, `.issues li.warning/.info`, `.pill` |
| Modal | `#modal .modal-card` |

## Writing

* Sentence case for labels; verbs on buttons ("Import again", "Render & play").
* Say what will happen, not how ("Every picture starts a chapter").
* No third-party product names in the interface, the docs or the code.
* Japanese strings are written for Japanese readers, not translated word by
  word; keep both lists in `app.js` (`I18N.en`, `I18N.ja`) in step — a test
  checks that every key exists in both.
