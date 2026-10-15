# oncemore Help

oncemore makes DVDs and Blu-ray discs with menus from your videos and
pictures: you lay out the menus, link their buttons to titles, chapters and
other menus, check the disc with an on-screen remote, and build a disc image,
a folder, a burned disc or a web version. Everything here works without an
internet connection.

Press **F1** anywhere in the app to open the part of this help about what you
are working on. **Help > Keyboard shortcuts** (or **?**) lists every key.

## Getting started {#start}

1. **File > New project…** chooses a folder and a name. In the New Project
   dialog, the *Authoring mode* is DVD or Blu-ray: what Build and Check
   project make (the disc's Properties change it later). *Create sample
   project* gives you a small working disc to look around in; or start
   empty.
2. Drop your video files onto the window (or **File > Import as > Import
   files…**). They appear in the **Project** panel.
3. Make a title from a video: select it and choose *Add as title*, or
   **Timeline > New title from a video…**. Add chapters where scenes start.
4. Make a menu: **Menu > New menu…** starts from a blank page or a template.
   Add buttons and link each one to a title, a chapter or another menu.
5. Press **Preview** (⇧Space) to play the disc with an on-screen remote.
6. **File > Check project** estimates the size and lists problems; **File >
   Build** writes the disc.

Everything you change is saved by itself in `project.oncemore.json` in the
project folder. Undo (⌘Z / Ctrl+Z) goes back step by step.

## The workspace {#workspace}

The window follows the classic disc authoring layout:

* the **menu bar** (File, Edit, Object, Menu, Timeline, View, Window, Help)
  and, under it, the **Tools** strip (selection, rotate, text, zoom, new
  button, new rectangle, Photoshop, Preview), the **Workspace** menu and a
  search field;
* on the left, **Project · Menus · Timelines · Build**;
* in the middle, **Monitor · Menu Viewer · Flowchart**, with the
  **Timeline** across the bottom;
* on the right, **Properties** and **Library · Layers**.

Panels are resized by dragging their edges. **Window > Workspace** switches
between the default layout, the flowchart, the Project Preview and the build
layout (⌥⇧1 to ⌥⇧4); *Reset workspace* puts every panel back. The **Window**
menu brings any panel to the front.

**Edit > Preferences…** sets the language (English or Japanese), the
brightness, the light or dark theme, the skin (*Modern* or *Classic*: mid-grey
panels and amber timecode) and where the media cache lives.

## Projects and saving {#projects}

A project is a folder: `project.oncemore.json` (the disc's description),
`media/` (your files), `output/` (built discs) and `exports/` (frames,
menus and subtitles you save as files).

* **File > Open project…** and **Open recent project** switch projects;
  **Save as…** copies the whole project folder to a new place and opens the
  copy.
* **Backups**: before a save replaces the project file, the version it
  replaces is kept in `.oncemore-backup/` (at most every five minutes, the
  last 30). **File > Revert to a saved version…** goes back to one of them;
  Undo returns to where you were.
* **File > Project settings…** shows the disc's settings: its name, the TV
  standard (NTSC or PAL), the aspect ratio, the authoring mode (DVD or
  Blu-ray), the disc size and the video bitrate (on a Blu-ray: BD-25 / BD-50
  and the 1080 / 720 picture), the disc font, the layer break, first play, what the remote's Title key opens, and how
  subtitles look.
* **File > Show project folder** opens the folder in the Finder or the file
  manager.

## Assets {#assets}

Videos, sounds, pictures, subtitle files and Photoshop files are the
project's assets; they live in `media/`.

* Drop files onto the window, or use **File > Import as**: *Import files…*,
  *Menu…* (a picture or a layered Photoshop file becomes a menu),
  *Timeline…* (a video becomes a title), *Slideshow…* (pictures become a
  slideshow) and *Pop-up menu…* (Blu-ray).
* **File > Replace asset…** points every use of one file to another. It is
  also how a missing file is found again: **Locate asset…** offers the
  missing ones first.
* **File > Interpret footage…** sets a title's aspect ratio and how its
  picture is scanned (progressive, interlaced, film with pulldown, or
  telecined film to recover).
* **Edit > Edit original** opens an asset in the program your system uses
  for it.

## Titles {#titles}

A title is a video the disc plays: one file, several clips joined
together, or a slideshow.

* Select a title to see it in the **Monitor** and its tracks in the
  **Timeline**: the picture, its chapters, its sound tracks with their
  waveforms and its subtitles.
* **▶ Play** (Space) plays it; the first time a small preview copy is made.
  Drag the playhead in the ruler, or use ← / → for a frame, Home / End, and
  PgUp / PgDn for the previous and next chapter.
* In **Properties**: the title's name, what happens when it ends (its *end
  action*: a menu, another title, the last menu, stop…), the menu the
  remote's Menu key opens, and the remote keys it turns off.
* **File > Transcode > Transcode settings…**: the title's video bitrate (or
  a share of the disc's), its sound (AC-3, LPCM, or DTS copied as it is,
  DTS-HD kept whole on a Blu-ray; stereo or 5.1), or using a disc-ready video as it is.
* **Transcode**: titles are encoded when the disc is built, or ahead of time
  with **File > Transcode > Transcode this title now** or *Transcode all
  titles now*; the build then reuses them. A filled dot next to a title in
  the Project panel means it is transcoded.
* **Multi-angle titles** (Properties > Angles, DVD): other videos of the same
  scene, switched with the remote's Angle key.

### Chapters {#chapters}

* **◆ Add chapter here** (or `*`) puts a chapter at the playhead. A chapter
  already within half a second of it is kept as it is.
* **Timeline > Add chapter points at intervals…**: a chapter every so many
  minutes or seconds, replacing the chapters or adding to them.
* **Timeline > Add chapter points at scene changes…**: finds the cuts in the
  picture (sensitivity low, medium or high), at least so many seconds apart.
* **Timeline > Import chapter markers from the source**: the chapter markers
  an MP4, MOV or MKV file carries, with their names.
* **Timeline > Clear all chapter points** removes them.
* Each chapter can have a name and a **poster frame** (the picture its
  button shows): **Timeline > Set poster frame at playhead**, or ⌘⌥-drag
  from a chapter mark. **View > Show chapter names** shows the names on the
  timeline.

### Sound and subtitles {#audio-subtitles}

* **Timeline > Add audio track…** adds another sound track: another stream of
  the same file, or another file. Each track has a language; track *n* has
  the same language on every title.
* **Timeline > Add subtitle track…** and **Import subtitles…** add subtitles
  from SubRip (`.srt`), WebVTT (`.vtt`), ASS / SSA or a text script (`.txt`,
  with timecodes, or with picture files for image subtitles).
* Under the timeline, **Subtitles** edits the cues: start, end, text, top or
  bottom. *+ Add cue at playhead* times a new one from where you are.
* A subtitle track marked *default* is shown when the title starts; without
  one, a Blu-ray starts with subtitles off and a DVD leaves it to the player's
  language setting.
* **Timeline > Export subtitles** saves a track as SubRip or a text script
  in `exports/`.

### Titles made of clips {#clips}

Under a title's picture, *Add a clip…* joins more videos and still pictures
into the same title: parts of files (in and out points), in any order, of
different sizes, frame rates and sound (or none). A picture is shown for the
seconds you set, whole (*Fit*, with bars around) or filling the frame (*Fill*, the edges cropped). Every clip
starts a chapter unless you set chapters yourself. Clips, like slides and
playlist items, are put in another order by dragging them.

### Buttons over a title {#title-buttons}

A title can have buttons over its picture (DVD): areas the viewer selects
with the arrow keys and presses with OK while the title plays, each from a
start to an end, such as a "skip intro" over the opening or "next episode"
over the credits. Draw what they look like into the video; the disc lights
the area in the highlight colour when one is selected and the select colour
when it is pressed.

* In **Properties > Buttons over the title**, **+ Button** adds one at the
  playhead. Set its link (a menu, a title or chapter, play all, a playlist,
  the last menu, stop, or a sound or subtitle track, which switches and the
  title plays on), when it appears and goes (⏱ takes the playhead; an
  empty *To* is the end of the title), and where it is.
* On the picture, the buttons shown at the playhead are boxes: drag one to
  move it, its corner to resize it. Under the picture, a bar marks when
  each button shows.
* The arrow keys go to the nearest button that way, as on a menu. A link
  to a menu can be come back from with Resume, as from the Menu key.
* The times buttons appear or go are at least a second apart, and from
  chapters. A title with buttons over it cannot have subtitles yet; a
  Blu-ray build and the web version leave the buttons out.

### Slideshows {#slideshows}

**Timeline > New slideshow** (or *+ Slideshow* in the Project panel, or
**File > Import as > Slideshow…**) turns pictures into a title.

* Set each picture's duration and the order (drag to move), the change
  between pictures (cross-fade, wipes, slides… or cuts), a slow zoom (*pan &
  zoom*), how pictures of another shape are shown (*Fit* or *Fill*) and the
  music.
* *Fit the pictures to the music* makes the slideshow last exactly as long as
  its music.
* *Advance by hand* holds each picture until the viewer presses Next or Play.
* **Render & play** (or **File > Render > Slideshows**) shows it as it will
  be on the disc. Every picture starts a chapter.

## Menus {#menus}

A menu is a picture with buttons. Select a menu to edit it in the **Menu
Viewer**.

* **Menu > New menu…** starts blank or from a template (classic, banner,
  minimal, setup, or one of *My templates*). **Menu > Create chapter
  index…** makes a title's chapter menu, six chapters a page, with their
  names and poster frames.
* **Menu > Add button**, **Add text**, **Add rectangle** and **Add picture…**
  add objects; so do the Tools strip and its keys (T: click where the text
  goes).
* The background is a picture, a video (a *motion menu*) or a colour; a
  menu can have music. Drop a picture onto the menu with Alt (⌥) to make it
  the background, a sound to make it the music.
* **Menu > Add new page** spreads a menu's buttons over pages, turned with
  buttons to the next, previous or a given page.
* **Menu > Set as default button** chooses the button that is selected when
  the menu opens. **Set as first play** makes the menu the first thing the
  disc shows.
* **Menu > Save menu as template…** keeps the menu (with its pictures, fonts
  and music) in your template library for any project; **Save menu as file**
  saves its picture in `exports/`.
* A menu can wait for a while and then go on by itself (Properties: loop
  count or time-out, and its end action); a motion menu repeats from its
  loop point.

### Objects on a menu {#menu-objects}

* Click to select; Shift-click (or ⌘-click) or a box dragged around objects
  selects several. ⌘A selects all.
* Drag to move; Shift-drag moves in a straight line, Alt (⌥)-drag leaves a
  copy, and holding ⌘ / Ctrl while dragging turns snapping off. The arrow keys
  move by a pixel, with Shift by 10. ⌘D duplicates.
* A selected rectangle or picture has handles to resize it (Shift keeps the
  proportions, Alt resizes from the centre); a text or button has corner
  handles that scale its type.
* **Object > Align**, **Distribute** and **Arrange** line objects up, space
  them evenly and change which is in front (⌘[ / ⌘] / ⇧⌘[ / ⇧⌘]). One object
  alone aligns to the safe area.
* **Object > Rotate**, **Flip horizontal** and **Flip vertical** turn and
  mirror texts, buttons, rectangles and pictures; the R tool rotates by
  dragging around the centre.
* A title or chapter button's **thumbnail** (its Properties > Thumbnail)
  can be cut to a **Shape**: rounded corners, an ellipse, or a picture whose
  opaque part shows it (still thumbnails), as the menu shows.
* **Comes in** (a text's or picture's Properties): the object comes in once,
  from a time into the menu over a time, moving from a distance away (a
  picture also growing from smaller) and fading in, to where it is on the
  menu. The menu becomes a motion menu; put its loop point after the
  animation to play it once. The menu editor shows the objects at rest.
* **Adjust** (a picture's Properties, and the menu's for its background
  picture or video): crop a part of it (left, top, width and height in
  percent), and set its brightness, contrast and saturation. The menu shows
  it as the disc will; **Reset** puts it back.
* **Object > Drop shadow and stroke…** adds a shadow and an outline.
  **Convert to button** and **Convert to object** change what an object is.
* Double-click a text or a button's words to type them in place (Esc ends
  it). Ctrl + right click (⌘-Control-click on a Mac) lists the objects under
  the pointer, to pick one that is covered.
* Text: font, size, colour, outline, shadow, bold, italic, letter spacing,
  kerning, and several lines aligned left, centred or right. **My styles**
  in the Library saves a look under a name for any project.
* **Layers**: the eye switches an object off; it stays in the project but is
  not on the disc.
* **View**: zoom (+ / −, ⌘0 fits), the safe area, snapping, guides (⌘; shows
  them, *New guide…* adds one), and *Show button routing*.

### Button highlights and colours {#highlights}

When the viewer moves to a button it lights up in the *highlight* colour;
when they press OK it shows the *activated* colour.

* A button's **Highlight** (Properties): its own pixels (the letters, or a
  picture's opaque pixels), a frame, a line under it, or a rectangle or
  ellipse drawn on the menu. A highlight picture can replace it.
* **Menu > Edit menu colour set…**: the Normal colour (buttons while not
  selected, optional), the Highlight and the Activated colour, each with its
  opacity.
* **View > Show highlights** shows every button as the disc will in the
  Normal, Selected or Activated state; **View > Exact preview** renders the
  menu exactly as the disc will show it, with the buttons' hit areas.
* Buttons whose areas overlap are outlined in red: the remote could not tell
  them apart, so **Check project** lists them and a disc cannot be built
  until they are moved apart.

### Menus from Photoshop {#photoshop}

**File > Import Photoshop design…** (or a layered `.psd` dropped onto the
window) makes a menu from a layered design. Layer groups named `(+) Name`
are buttons; inside them `(=1)` layers are their highlights and `(%)`
layers where a title or chapter thumbnail goes; everything else is the
background. Buttons named like *Play*, *Play all*, *Scene 3* or a title's
name are linked by themselves; check the rest. Top-level groups named
`(page) Name` are the menu's pages (from the top of the Layers panel, shown
or hidden): their artwork and buttons are on that page, buttons named
*Next* and *Prev* turn the page, and the rest is on every page.

**Edit > Edit menu in Photoshop** opens the menu's file; when it is saved
there, the Menu Viewer offers to import it again, keeping every button's link.

## Links and navigation {#links}

Every button, every title's end and the disc's first play has a *link*:
where the disc goes next.

* Choose a button's link in Properties, or with **Menu > Set link…** (⌘L).
  A link can be a title, a chapter, a playlist, *Play all titles*, another
  menu (on a chosen button), *Return to the last menu*, *Resume* (the title
  the Menu key left, from where it was), a sound or subtitle track, or *Stop*.
* **Pick whip**: drag the ◎ next to a link to a title, menu or playlist in
  the Project panel or the flowchart.
* Drag a title, menu, playlist or chapter onto a button to link it, or onto
  an empty part of the menu to add a button for it. A video dropped onto a
  menu makes a title and a button that plays it.
* **Routing**: the remote's arrow keys move between buttons by themselves.
  *Show button routing* draws where each key goes (solid: set by you,
  dashed: automatic); drag an arrow onto another button to send that key
  there.
* A button can play a short clip before it goes (a **link transition**), and
  can change where the title it starts goes when it ends (*Then (override)*).
* **Remote keys**: a title or menu can turn off keys (for example a notice
  that cannot be skipped). What the **Title** key opens is a disc setting;
  what the **Menu** key opens is set for each title.

### Navigation scripts {#scripts}

For what a link alone cannot do (count presses, remember a choice, pick a
title at random, ask a pass code), write a few lines of navigation in the
disc's Properties, under *Navigation scripts* (DVD only). **+ Script** adds
one; then choose *Script: <name>* as the link of a menu's or a title's
button, a menu's time-out, or the end of a title or playlist.

* `$name` is a variable: 0 when the disc starts, kept until a script
  changes it (0 to 65535).
* `play <link>;` goes somewhere, as a button would: `play menu:main;`,
  `play title:t1;`, `play chapter:t1:3;`, `play playlist:best;`, `play
  playall;`, `play stop;`, `play audio:2;`, `play subtitle:off;`.
* `if ($n >= 2) { … } else { … }`, `$n += 1;`, `$r = random(3);` (1 to 3).
* `audio`, `subtitle`, `angle` and `button` are the player's own values (as
  dvdauthor reads them: the button is its number × 1024).
* Every way through a script ends with a `play` that goes somewhere.

Example (the second press plays the film): `$n += 1; if ($n >= 2) { $n = 0; play title:film; } else play menu:main;`

Under the text the app says which variables the script uses and where it can
go, or what is wrong. Preview runs scripts and shows the variables; the
flowchart draws a line to each place a script can go. A Blu-ray and the web
version have no scripts.

## Playlists {#playlists}

**Timeline > New playlist** plays titles, chapters or ranges of chapters one
after another, in order, shuffled or at random (shuffled and random play on
a Blu-ray and in the web version; a DVD plays them in order). **New chapter
playlist…** makes one that plays a title's chapters one after another (each
an item you can reorder or remove). Link a button to the playlist to play it.

## Pop-up menus (Blu-ray) {#popups}

On a Blu-ray, a title's Menu-key menu becomes its pop-up menu: the remote's
Pop-up Menu key shows its buttons over the playing picture. **File > Import
as > Pop-up menu…** makes one from a picture or a Photoshop file. A pop-up
menu shows what lies inside each button's area; texts and pictures elsewhere
on the menu, and its background, are left out.

## Flowchart {#flowchart}

The **Flowchart** shows the whole disc: first play, menus, titles, playlists
and every link between them (buttons, end actions, time-outs, the Menu and
Title keys).

* Boxes a viewer can never reach, and menus they cannot leave, are outlined
  in red. Items nothing leads to sit in a *Not used* row at the bottom.
* Click a box to edit it. Drag from one item to another to link them; a
  title, menu or playlist dragged in from the Project panel links by where
  it lands.

## Project Preview {#preview}

**Preview** (⇧Space, or **File > Preview**) plays the disc with an on-screen
remote before anything is encoded: arrows, OK, Menu, Title, previous and
next chapter, play to the end, and letting a menu time out. Menus are shown
exactly as on the disc with their real highlights; titles show their
chapters' first frames. It follows the same navigation rules as the built
disc.

In a title with buttons over it, *Time in the title* under the picture
moves through the title: the buttons shown then answer the arrows, OK and
the number keys.

Keys: the arrow keys and Enter; 1–9 press that button; Home is the Title
key, Insert the Menu key; End plays to the end; Space plays; ⌘← / ⌘→ go to
the previous or next chapter. *Insert disc again* starts over; ✕ closes the
preview.

## Checking and building {#build}

The **Build** panel (next to Project) checks and builds the disc.

* **File > Check project** estimates the size and lists problems before
  anything is encoded: missing files, links that lead nowhere, overlapping
  buttons, characters the font does not have. The *bit budget* shows the
  whole disc and, for each title, its length, video and audio rates and the
  space it takes.
* **File > Build** writes a **DVD** or **Blu-ray** as a disc image (`.iso`),
  a folder (`VIDEO_TS` or `BDMV`) or a burned disc, or the **Web (HTML5)**
  version, into `output/`, with progress.
* A dual-layer DVD (DVD-9) has a **layer break**: the chapter where the
  second layer starts (the first one past the middle unless you choose).
* **File > DVD-ROM content…** adds files to the disc beside the video, for
  computers.
* Rebuilding is fast: encoded titles and menus are kept in the media cache
  and reused when nothing about them changed.

## Blu-ray {#bluray}

A project is made for a Blu-ray when its *Authoring mode* is Blu-ray (New
Project, or the disc's Properties); Build and Check project then make a
Blu-ray, and the Build panel can still make the other. Titles are encoded in
HD (1920 × 1080, or 1280 × 720 when the Picture setting says 720p);
subtitles become Blu-ray subtitle streams with smooth edges; menus are drawn
at HD size with highlights in any colour and opacity; Play All and playlists
work as on the DVD, and a title's Menu-key menu becomes its pop-up menu. The
disc size (BD-25 or BD-50) caps the video rate so the titles fit. Buttons
over a title, angles, closed captions and navigation scripts are DVD-only:
in a project made for a Blu-ray their settings say so.

## The web version {#web}

**File > Build > Web (HTML5)…** writes a folder a browser plays as the disc:
the menus with their buttons and highlights (arrow keys, Enter, the mouse
and the number keys), every title with its chapters and subtitles, and the
disc's links. Open `index.html` from the folder, or put the folder on any web
server. A browser plays the first sound track and shows text subtitles only.

## Keyboard shortcuts {#shortcuts}

**Help > Keyboard shortcuts** (or **?**) lists every key with what it does.
On a Mac ⌘ is the Command key; elsewhere use Ctrl. A tool key (V, R, T, Z)
held down chooses that tool only while it is held.

## Menu reference {#reference}

Every command of the menu bar, with its shortcut:

<!-- menu-reference -->

## When something goes wrong {#trouble}

* **A file is missing**: the Project panel lists it first; **File > Locate
  asset…** points the project to it again.
* **Buttons overlap**: move them apart until the red outline goes; Check
  project names them.
* **A character is missing from a font**: the build stops instead of drawing
  an empty box. Choose a font that has it for that text (Properties > Font;
  add `.ttf` / `.otf` files to the project to use them).
* **The build needs ffmpeg**: oncemore uses ffmpeg (with libx264 and
  drawtext) to encode; install it (on a Mac: `brew install ffmpeg-full`).
* **A disc does not play in a player**: try the Project Preview first; then
  play the image with VLC. Burn at a low speed on good media.

## Known limits {#limits}

* Highlights on a DVD have hard edges and one colour for each state (normal,
  selected, activated); a Blu-ray shows the same shapes in any colour and
  opacity.
* Subtitles use one font and size for the whole disc; emoji are not drawn.
* Sound track *n* and subtitle track *n* have one language on the whole disc.
* Buttons over a title are for DVD, and not yet in a title with subtitles.
* There is no copy protection, by design.
