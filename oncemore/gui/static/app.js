/* oncemore GUI — vanilla JS, no build step. Talks to oncemore/gui/server.py. */
"use strict";

// ---------------------------------------------------------------- i18n
const I18N = {
  en: {
    check: "Check", build: "Build", drop_here: "Drop files to add them to the project",
    disc: "Disc", titles: "Titles", menus: "Menus", media: "Media", generated: "generated",
    add: "+ Add", add_files: "Drop files here or click to add",
    saved: "Saved", saving: "Saving…", unsaved: "Unsaved", save_error: "Save failed",
    issues: "{n} issue(s)", no_issues: "No issues", tools_missing: "Missing tools: {t}",
    new_project: "New DVD project", new_hint: "No project in {dir} yet.",
    label: "Disc label", standard: "TV standard", aspect: "Aspect ratio", target: "Disc size",
    first_play: "When the disc starts", video_bitrate: "Video bitrate",
    auto: "Automatic", empty_project: "Create empty project", sample_project: "Create sample project",
    title_props: "Title", name: "Name", id: "ID", source: "Video file", audio: "Audio",
    codec: "Codec", bitrate: "Bitrate", language: "Language", end_action: "When it ends",
    title_key: "Title / Top Menu key opens", menu_key: "Menu key opens", menu_key_hint: "On a Blu-ray, a menu chosen here is this title's pop-up menu: the Pop-up key shows its buttons over the picture.", first_menu: "First menu",
    playback: "Playback", loop: "Plays", loop_forever: "Repeat forever", loop_n: "{n} time(s), then…",
    loop_point: "Repeat from (s)", buttons_at_loop: "Buttons appear at the loop point (the intro plays out)", fade_in: "Fade in from black (s)", menu_end: "After the last time", default_button: "Button highlighted first",
    remember_button: "Come back to the button used last", auto_activate: "Run on selection (no Enter needed)",
    chapter_menu: "Chapter menu", chapter_menu_on: "Generate a chapter menu with thumbnails",
    subtitles: "Subtitles", audio_tracks: "Audio tracks", default_on: "on at start",
    add_chapter: "Add chapter here", chapters: "Chapters", delete: "Delete",
    add_shape: "+ Rectangle", add_picture: "+ Picture", picture: "Picture", pictures: "Pictures",
    place_on_menu: "Place on the menu", picture_hint: "A picture on the menu that is not a button: a logo, a photo. PNG keeps its transparency.",
    pick_picture: "Choose a picture from the project's files (File > Import first).", keep_ratio: "Keep proportions", snap: "Snap", align: "Align", n_selected: "{n} selected",
    align_left: "Align left edges", align_hcenter: "Centre horizontally", align_right: "Align right edges",
    align_top: "Align tops", align_vcenter: "Centre vertically", align_bottom: "Align bottoms",
    distribute_h: "Distribute horizontally", distribute_v: "Distribute vertically",
    stage_keys: "Shift-click: select several · arrows: nudge · ⌘D: duplicate · ⌘C/⌘V · Alt: no snapping",
    multi_hint: "Drag to move them together, or use the align buttons above the menu.",
    shape: "Rectangle", height: "Height", fill: "Fill", opacity: "Opacity",
    paragraph: "Paragraph", para_align: "Lines", para_left: "Left", para_center: "Centre", para_right: "Right", line_spacing: "Line spacing", paragraph_hint: "Each line of the text is a line on the menu (Return starts a new one); X is the paragraph's left edge.",
    text_style: "Text style", font: "Font", disc_font: "Disc font", outline: "Outline", shadow: "Shadow",
    font_hint: "Add .ttf / .otf files to Media to use them here.",
    highlight_image: "Highlight picture", highlight_image_hint: "Optional: a picture whose opaque pixels light up when the button is selected.",
    new_menu: "New menu", blank_menu: "Blank", template_hint: "Start from a layout; everything stays editable.",
    motion_bg: "Motion background", animated_thumbs: "Thumbnails play the chapter",
    set_audio: "Set audio", set_subtitle: "Set subtitles", no_change: "No change",
    last_menu: "Return to the last menu",
    override: "Then (override)", override_none: "The title's own end action",
    override_hint: "Where to go when the title this button plays ends, instead of its own end action (only when started from this button).",
    transition: "Link transition", transition_hint: "A short video played when the button is pressed, before its link: for example this menu dissolving into the next one.",
    thumb_section: "Thumbnail", thumb_on: "Show a picture of the linked title / chapter",
    thumb_time: "Frame at (s)", thumb_anim: "Play it (motion menus)",
    sub_style: "Subtitle look (all tracks)", sub_margin: "Bottom margin", outline_w: "Outline width",
    cm_heading: "Heading", cm_label_format: "Labels ({n} = number)", cm_back_label: "BACK button",
    cm_prev_label: "PREV button", cm_next_label: "NEXT button",
    scan: "Picture", scan_auto: "Automatic", scan_progressive: "Progressive",
    scan_interlaced: "Interlaced (keep fields)", scan_pulldown: "Film, 3:2 pulldown (23.976)",
    scan_ivtc: "Telecined film (29.97i → 23.976 + pulldown)",
    scan_hint: "Automatic keeps interlaced and 60p video as fields and stores 23.976 film with pulldown flags.",
    no_transcode: "Don't transcode (the source already is DVD video)", no_transcode_hint: "MPEG-2 at the disc's frame size and rate goes on the disc as it is (on a Blu-ray: H.264 that already is Blu-ray video); the sound is still made to the settings below. The build says why when the file does not qualify.", status_no_transcode: "Don't transcode",
    auto_shared: "Automatic (share the disc)", passthrough: "Copy AC-3 unchanged",
    passthrough_hint: "For AC-3 (48 kHz) sources: no re-encoding. Channels must match the source.",
    dts_copy: "DTS (copy)", dts_hint: "DTS is copied from the sources as it is (48 kHz; DTS-HD keeps its DTS core). Channels must match the source.",
    layer_break: "Layer break", layer_break_hint: "Where a dual-layer disc goes on to its second layer: the start of a chapter past the middle of the disc. The built-in ISO writer puts it on an ECC block, and burning passes it to the writer.", layer_break_at: "{t}, chapter {n}",
    rom_files: "DVD-ROM files", rom_hint: "Files or folders (one per line, relative to the project) put next to VIDEO_TS for computers.",
    no_cache: "Encode everything again (ignore the cache)",
    sub_bottom: "Bottom", sub_top: "Top", sub_color: "Own colour",
    add_slideshow: "+ Slideshow", slideshow: "Slideshow", slideshow_hint: "A title made from pictures",
    slideshow_need_images: "Add some pictures to Media first (drop them onto the window).",
    slideshow_preview_hint: "Render & play shows the slideshow as it will be on the disc.",
    render_play: "Render & play", rendering: "Rendering…", add_picture: "+ Add a picture…", seconds: "Seconds on screen",
    transition: "Transition", crossfade: "Cross-fade", cut: "Cut", transition_duration: "Transition length (s)",
    tr_dissolve: "Dissolve", tr_fadeblack: "Through black", tr_fadewhite: "Through white", tr_wipeleft: "Wipe left", tr_wiperight: "Wipe right", tr_wipeup: "Wipe up", tr_wipedown: "Wipe down",
    tr_slideleft: "Slide left", tr_slideright: "Slide right", tr_slideup: "Slide up", tr_slidedown: "Slide down", tr_circleopen: "Circle open", tr_circleclose: "Circle close", tr_radial: "Radial", tr_pixelize: "Pixelate", tr_random: "Random", tr_own: "Slideshow's transition", tr_next: "To the next picture",
    pan_zoom: "Slow zoom in / out (pan & zoom)", slideshow_chapters: "Every picture starts a chapter.",
    routing: "Routing", routing_hint: "Show where the remote's arrow keys go from each button (solid: set by you, dashed: automatic)",
    link_hint: "Drag a title, menu or playlist from the project panel onto a button to link it, or onto the menu to add a button for it.",
    cmd_transcode_title: "Transcode this title now", cmd_transcode_all: "Transcode all titles now",
    transcoding: "Transcoding", transcoded: "Transcoded: the build will reuse it", not_transcoded: "Not transcoded yet (encoded when the disc is built)",
    m_object: "Object", m_menu: "Menu", m_timeline: "Timeline", m_view: "View", m_window: "Window",
    cmd_preview: "Preview", cmd_set_link: "Set link…", cmd_routing: "Show button routing", cmd_safe_area: "Show safe area",
    cmd_tool_select: "Selection tool", cmd_tool_text: "Text tool", cmd_tool_zoom: "Zoom tool", cmd_zoom_in: "Zoom in", cmd_zoom_out: "Zoom out",
    cmd_align_left: "Align left edges", cmd_align_hcenter: "Align horizontal centres", cmd_align_right: "Align right edges",
    cmd_align_top: "Align top edges", cmd_align_vcenter: "Align vertical centres", cmd_align_bottom: "Align bottom edges",
    cmd_distribute_h: "Distribute horizontally", cmd_distribute_v: "Distribute vertically", cmd_bring_front: "Bring to front", cmd_send_back: "Send to back",
    cmd_convert: "Convert text ⇄ button", cmd_new_timeline: "New title from a video…", cmd_prev_chapter: "Previous chapter", cmd_next_chapter: "Next chapter",
    new_timeline_hint: "Choose the video the title plays.", tools: "Tools", tool_select: "Selection", tool_text: "Text: click where the text goes", tool_zoom: "Zoom: click to zoom in, Alt-click to zoom out",
    zoom_fit: "Fit", zoom_hint: "Zoom (+ / −)", safe_hint: "Action-safe and title-safe areas: TVs may cut off the edges",
    subpictures: "Highlights:", subpictures_hint: "Show every button as it looks when not selected, selected or activated (the exact disc picture)",
    sp_normal: "Normal", sp_selected: "Selected", sp_activated: "Activated", overlap_hint: "This button's area overlaps another button: the remote may not reach one of them",
    whip_hint: "Drag to a title, menu or playlist (project panel or flowchart) to link it", flow_link_hint: "Drag from an item to another to link it: first play, end actions, a button of a menu.",
    pick_button: "Which button links there?", unused: "Not used",
    type_clips: "Timeline (clips)", type_timeline: "Timeline", type_chapter_menu: "Chapter menu", n_buttons: "{n} buttons", n_items: "{n} items", kind_video: "Video", kind_audio: "Audio", kind_image: "Still image", kind_subtitle: "Subtitles", kind_design: "Photoshop design", kind_font: "Font", col_name: "Name", col_type: "Type", col_duration: "Duration", col_buttons: "Buttons", col_first: "First play", col_chapters: "Chapters", col_transcode: "Transcode", buttons_of: "Buttons of {m}", chapters_of: "Chapters of {t}", status_transcoded: "Transcoded", status_untranscoded: "Untranscoded", add_menu_short: "+ Menu", add_playlist_short: "+ Playlist", panel_menu: "Panel menu", menu_viewer: "Menu Viewer", layers_hint: "Open a menu to see its layers.", timelines: "Timelines", preferences: "Preferences", cmd_preferences: "Preferences…", appearance: "Appearance", brightness: "Brightness", brightness_hint: "Lighter or darker interface greys (the menu and video pictures are not changed).", darker: "Darker", lighter: "Lighter", default: "Default", welcome: "Welcome", new_project_basic: "Basic", authoring_mode: "Authoring mode",
    m_file: "File", m_edit: "Edit", m_disc: "Disc", m_view: "View", m_help: "Help",
    cmd_import_files: "Import files…", cmd_import_psd: "Import Photoshop design…", cmd_check: "Check project",
    cmd_build: "Build disc…", cmd_reveal: "Show project folder", cmd_undo: "Undo", cmd_redo: "Redo",
    cmd_duplicate: "Duplicate", cmd_delete: "Delete", cmd_new_slideshow: "New slideshow", cmd_new_menu: "New menu…",
    cmd_new_playlist: "New playlist", cmd_add_chapter: "Add chapter at playhead", cmd_play: "Play / pause",
    cmd_ws_author: "Workspace: Default", cmd_ws_flow: "Workspace: Flowchart", cmd_ws_sim: "Project Preview", cmd_ws_build: "Build",
    cmd_theme: "Light / dark theme", cmd_language: "日本語", cmd_shortcuts: "Keyboard shortcuts", cmd_about: "About oncemore",
    open: "Open", set_first_play: "Play first when the disc starts", copy_of: "{x} copy", reveal_file: "Show in folder",
    copy: "Copy", paste: "Paste", nudge: "Move selected elements (10 px with Shift)", copy_paste: "Copy / paste elements",
    about_text: "Open-source DVD-Video authoring: menus, chapters, playlists and a disc image, on your own computer. No copy protection.",
    clips: "Clips", add_clip: "Add a clip…", clip_in: "In", clip_out: "Out", clip_end: "end",
    clips_hint: "The clips play one after another as one title. Without chapters of its own, every clip starts a chapter.",
    joining: "Joining the clips…", clip_whole: "whole file", clips_n: "{n} clips", clip_source_hint: "Add a clip to join more videos and still pictures into this title.",
    clip_still: "still", clip_duration: "Seconds the picture is shown", fit: "Scaling", fit_fit: "Fit (whole picture, bars around)", fit_fill: "Fill (crop the edges)", fit_own: "Slideshow's scaling",
    subtitle_editor: "Subtitle cues", no_sub_tracks: "No subtitle track yet.", new_srt: "+ New subtitle file",
    sub_readonly: "WebVTT / ASS files are shown read-only.", convert_srt: "Convert to .srt to edit",
    sub_track_pos: "Track", add_cue: "+ Cue at the playhead", new_cue_text: "New subtitle",
    image: "Image", width: "Width", highlight_style: "Highlight", hl_frame: "Frame around it", hl_shape: "Its shape",
    image_hint: "An image button shows the picture instead of the text (PNG with transparency works best).",
    chapter_name: "Name on the chapter menu", poster: "Poster", poster_hint: "Use the frame at the playhead as this chapter's thumbnail (click again to reset)",
    playlists: "Playlists", playlist: "Playlist", playlist_item: "Playlist: {p}", items: "Items", add_item: "+ Item",
    from_chapter: "From chapter", to_chapter: "To chapter", to_end: "the end", playlist_end: "After the last item",
    playlist_order: "Order", order_sequential: "As listed", order_random: "Random", order_shuffle: "Shuffle",
    order_hint: "Random plays as many items as there are, each picked at random (one can come again); Shuffle plays each once in a random order. On Blu-ray and the web version; a DVD plays them as listed.",
    playlist_hint: "A playlist plays titles and chapter ranges in this order. Point a button at it (“Playlist: …”).",
    move_up: "Move up", move_down: "Move down", order_title: "Play all follows this order.",
    order_menu: "The first menu opens when the disc starts, unless “When the disc starts” says otherwise.",
    play: "Play", pause: "Pause", preparing: "Preparing preview… {p}%", play_err: "This preview cannot be played here.",
    no_titles: "No titles yet. Drop a video file into Media, then choose “Add as title”.",
    add_as_title: "Add as title", use_as_bg: "Use as menu background", use_as_music: "Use as menu music",
    use_as_video_bg: "Use as motion menu background", add_sub_to: "Add as subtitles to",
    new_menu_with_bg: "New menu with this background",
    menu_props: "Menu", background: "Background image", background_video: "Background video",
    background_color: "Background colour", music: "Music", duration: "Loop length (s)",
    sound_picture: "Picture", black: "Black", sound_picture_hint: "The source is sound only: this still is shown while it plays.",
    advance_manual: "Advance by hand (each picture stays until Next / Play)",
    add_music: "+ Add music…", fit_to_music: "Fit the pictures to the music (their seconds become proportions)", fitted_to: "Fitted: {d}",
    font_size: "Text size", text_color: "Text colour", highlight: "Highlight", select_color: "Activated",
    add_button: "+ Button", add_text: "+ Text", exact_preview: "Exact preview", hide_preview: "Hide preview",
    safe_area: "Safe area", button: "Button", text: "Text", action: "Action", size: "Size", color: "Colour",
    nav: "Remote navigation", nav_auto: "auto", none: "None", stop: "Stop",
    playall: "Play all titles", resume: "Resume (the title the Menu key left)", channels: "Channels", stereo: "Stereo", surround: "5.1 surround",
    generated_menu: "This menu is generated from the chapters of “{t}”. Change it in that title's settings.",
    go_to_title: "Open title",
    build_iso: "Disc image (.iso)", build_folder: "VIDEO_TS folder", build_disc: "DVD disc (the image, then burned)",
    build_format: "Format", format_dvd: "DVD", format_bluray: "Blu-ray", format_web: "Web (HTML5)", build_web_folder: "A folder with index.html (open it in a browser, or put it on a web server)",
    web_note: "The disc for browsers: the menus with their buttons, the titles as MP4 with chapters and subtitles, and the links as on the disc. One sound track per title.", build_bdmv: "BDMV folder", build_bd_disc: "Blu-ray disc (the image, then burned)", bd_size: "Disc size",
    bd_note: "Blu-ray: titles in HD (1920×1080) with chapters, playlists and Play All. Menus and subtitles are DVD-only for now.",
    recorder: "Recorder", recorder_hint: "Empty: the first disc writer. Insert a blank disc (DVD, or BD for a Blu-ray) before you build.",
    burned: "Burned to the DVD", step_burn: "Burning the disc", fast: "Fast (1-pass) encoding",
    start_build: "Start", building: "Building…", build_done: "Done", build_failed: "Build failed",
    reveal: "Show in Finder", reveal_other: "Open folder", output: "Output", warnings: "Warnings",
    step_probe: "Checking sources", step_menu: "Rendering menu “{i}”", step_encode: "Encoding title “{i}”",
    step_subtitles: "Subtitles for “{i}”", step_author: "Authoring VIDEO_TS", step_iso: "Writing the disc image",
    media_cache: "Media cache", cache_folder: "Folder", cache_in_project: "In the project folder (.oncemore-cache)", cache_use: "Use",
    cache_in_project_short: "In the project", cache_now: "This project's: {p}",
    cache_hint: "Encoded titles and menus, rendered slideshows and playback copies are kept here so builds go fast. A folder for every project (e.g. on a larger or faster drive): each project gets its own folder in it.",
    check_ok: "Ready to build", estimated: "Estimated size", of: "of", video_avg: "Average video bitrate",
    budget: "Bit budget", budget_menus: "Menus", budget_other: "Disc files", budget_free: "Free", budget_video: "Video Mbit/s",
    budget_audio: "Audio", budget_size: "Size", budget_share: "Of the disc", col_length: "Length",
    menu_item: "Menu: {m}", menu_button_item: "Menu: {m} › {b}", title_item: "Title: {t}", chapter_item: "{t} › Chapter {n}",
    audio_item: "Audio stream {n}", subtitle_item: "Subtitles {n}", subtitle_off: "Subtitles off",
    nothing_selected: "Select a button or text on the menu, or edit the menu settings below.",
    rename_hint: "Changing an ID also updates everything that points to it.",
    flowchart: "Flowchart", simulator: "Simulator", menu: "Menu", title: "Title",
    ws_author: "Author", ws_preview: "Preview", properties: "Properties", project: "Project", library: "Library",
    lib_templates: "Menu templates", lib_backgrounds: "Backgrounds", lib_text_styles: "Text styles",
    lib_style_hint: "Select buttons or texts in a menu, then click a style.",
    style_plain: "Plain", style_outline: "Outline", style_shadow: "Shadow", style_outline_shadow: "Outline + shadow",
    layers: "Layers", buttons: "Buttons", texts: "Texts", shapes: "Rectangles", rectangle: "Rectangle",
    timeline: "Timeline", video: "Video",
    import_psd: "Import from Photoshop", import: "Import", importing: "Reading the layers…",
    import_psd_hint: "A layered .psd / .psb: groups named \"(+) Name\" become buttons, their \"(=1)\" layers the highlight and a \"(%)\" layer the thumbnail; everything else visible is the background. Drop the file onto the window to add it.",
    no_psd: "No Photoshop files in Media yet: drop a .psd onto the window.",
    imported_n: "{n} button(s) imported.", psd_actions_hint: "Check each button's target in the right-hand panel; names like \"Play\", \"Scene 2\" or a title's name are linked automatically.",
    reimport: "Import again", reimport_hint: "After editing the file in Photoshop: updates the pictures and keeps the buttons' targets.",
    make_menu_from_psd: "Make a menu from this design",
    flow_hint: "Everything a viewer can do on the disc: buttons, end actions, time-outs, playlists and the remote's Menu / Title keys. Click a box to edit it. Red boxes cannot be reached or cannot be left.",
    sim_hint: "Play the disc with a remote before building: arrows, OK, Menu, Title, next / previous chapter. Nothing is encoded; the pictures are the exact menu previews. Keyboard: arrow keys, Enter, M, T, N, P.",
    fp: "First play", title_key_node: "Title key", stop_node: "Stop", play_all: "Play all",
    nav_ok: "No navigation problems.", restart: "Insert disc again", play_chapter: "Play chapter",
    to_end: "Play to the end", time_out: "Let the menu time out", now: "Now", chapter_n: "Chapter {n} of {m}",
    stopped: "Playback stopped.", audio_n: "Audio {n}", sub_off: "Subtitles off", sub_n: "Subtitles {n}",
    in_playall: "playing all", in_playlist: "playlist",
    disc_tips: "Coordinates are DVD pixels (720 wide). Text is drawn with the font that oncemore picks to cover all characters.",
    tools: "Tools", ok: "OK", missing: "missing", tracks_hint: "Leave empty to use the video's own sound.",
    stream: "Stream", file: "File", add_track: "+ Track", add_sub: "+ Subtitle file",
    frame_err: "Cannot show this frame", preview_err: "Preview failed",
    confirm_delete: "Delete “{x}”?", chapter_at: "Chapter {n}", playhead: "Playhead",
    workspace: "Workspace", ws_default: "Default", monitor: "Monitor", no_menus: "(no Menus)", no_timelines: "(no Timelines)",
    project_preview: "Project Preview", search: "Search", fit: "Fit", step_back: "Step Backward", step_fwd: "Step Forward",
    prev_ch: "Previous Chapter", next_ch: "Next Chapter", tc_source: "Source", no_timeline_open: "Open a timeline from the Project panel to see it here.",
    prop_disc: "Disc", prop_title: "Timeline", prop_menu: "Menu", prop_button: "Button", prop_text: "Text", prop_shape: "Rectangle",
    prop_asset: "Asset", prop_playlist: "Chapter Playlist", prop_slideshow: "Slideshow",
    name_location: "Name and Location", project_settings: "Project Settings", location: "Location", transcode_settings: "Transcode Settings",
    np_transcode: "Codec: MPEG-2; Dimensions: {d}; Frame Rate: {f}; Audio: AC-3 / PCM; Maximum Audio/Video Bitrate: 9.8 Mbps",
    np_info: "The disc's settings can be changed at any time in the Properties panel (select the disc in the Flowchart).",
    np_open_sample: "Open the sample project", advanced: "Advanced", cancel: "Cancel",
    build_source: "Source", current_project: "Current Project", destination: "Destination", disc_info: "Disc Info",
    settings: "Settings", size_estimate: "Estimated size", check_project: "Check Project…", new_item: "New Item", delete_item: "Delete",
    tool_import_psd: "Make a menu from a Photoshop file", preview_close: "Close the preview",
    basic: "Basic", motion: "Motion", toggle_safe: "Show Safe Area",
    cmd_chapters_interval: "Add chapter points at intervals…", cmd_chapters_scenes: "Add chapter points at scene changes…",
    sc_sensitivity: "Sensitivity", sc_low: "Low (clear cuts only)", sc_medium: "Medium", sc_high: "High (smaller changes too)", sc_gap: "At least (s) apart",
    sc_find: "Find", sc_looking: "Looking for scene changes…", sc_found: "{n} scene changes found: {c} chapters.",
    sc_hint: "Finds the cuts in the picture and puts a chapter at each, at least the given seconds apart.", cmd_replace_asset: "Replace asset…", cmd_project_settings: "Project settings…",
    cmd_edit_psd: "Edit menu in Photoshop", cmd_win_project: "Project", cmd_win_menus: "Menus", cmd_win_timelines: "Timelines", cmd_win_build: "Build",
    cmd_win_monitor: "Monitor", cmd_win_flowchart: "Flowchart", cmd_win_properties: "Properties", cmd_win_layers: "Layers", cmd_win_library: "Library",
    ci_every: "A chapter every", ci_minutes: "minutes", ci_seconds: "seconds", ci_replace: "Remove the chapters there are now (the first stays)",
    ci_preview: "{n} chapters on {d}.", cmd_chapters_from_source: "Import chapter markers from the source",
    no_source_chapters: "The source has no chapter markers.", ra_what: "Replace", ra_with: "With", ra_uses: "Used {n} time(s) in the project.", ra_missing: "missing",
    ra_hint: "Every use in the project then points to the new file: titles, clips, audio and subtitle tracks, menu backgrounds, buttons, slideshows, music.",
    ra_none: "The project uses no files yet.", psd_changed: "The Photoshop file of this menu has changed.", open_failed: "This system has no program to open the file with.",
    colour_set: "Colour set", cs_normal: "Normal", opacity: "Opacity",
    cs_normal_hint: "Show the buttons' highlight shapes in this colour while they are not selected",
    cs_hint: "The colours of the buttons' highlight shapes: Normal (while not selected; optional), Highlight (selected) and Activated (pressed). A DVD player has 16 levels of opacity.",
    layer_hide: "Hide (not on the disc)", layer_show: "Show",
    cmd_revert_backup: "Revert to a saved version…", revert: "Revert", no_backups: "No earlier versions yet.",
    backups_hint: "oncemore keeps the project as it was before your changes, at most every {m} minutes (the last 30, in .oncemore-backup next to the project). Reverting is one more edit: Undo brings you back.",
    backup_counts: "{t} titles, {m} menus", confirm_revert: "Replace the project with this version? (Undo brings the current one back.)",
    cmd_save_template: "Save menu as template…", cmd_chapter_index: "Create chapter index…", cmd_add_page: "Add new page", cmd_delete_page: "Delete page",
    pages: "Pages", pages_hint: "The menu's pages, one shown at a time: each is a menu of its own on the disc. Buttons turn the pages (Next page, Previous page, Page n).",
    page_field: "Page", page_all: "every page", page_item: "Page {n}", page_next: "Next page", page_prev: "Previous page", page_of: "Page {n} of {m}",
    page_hint: "On this page only, or on every page of the menu (a heading, a background, buttons that turn the pages).", lib_my_styles: "My styles", ustyle_use: "Give the selected objects this look (a shape takes its colour)", ustyle_none: "No styles yet: select a text, button or shape and save its look.", ustyle_save: "Save selection as style…", ustyle_save_hint: "Keep the look of the selected object (font, size, colour, outline, shadow) for any menu of any project", ustyle_name: "Style name", ustyle_default_name: "My style", lib_my_templates: "My templates",
    utpl_use: "New menu from this template", utpl_none: "Menu > Save menu as template keeps a menu here, with its pictures, for every project.",
    utpl_hint: "The menu and copies of the files it uses (backgrounds, pictures, fonts, music) are kept in your template library, so any project can start a menu from it.",
    utpl_saved: "Saved “{n}” to the Library (My templates).",
    chapter_index_hint: "Makes the title's chapter menu (six chapters a page, with the chapters' names and poster frames) and opens it.",
    theme_dark: "Dark", theme_light: "Light",
    skin: "Skin", skin_modern: "Modern", skin_classic: "Classic", skin_hint: "Classic: the look of the classic disc authoring apps (mid-grey panels, light fields, amber timecode). The layout is the same.",
    // P48: the full menu bar
    m_open_recent: "Open recent project", m_import_as: "Import as", m_transcode: "Transcode", m_render: "Render", m_build: "Build", m_export_subs: "Export subtitles",
    m_align: "Align", m_distribute: "Distribute", m_arrange: "Arrange", m_rotate: "Rotate", m_tools: "Tools", m_highlights: "Show highlights", m_workspace: "Workspace",
    cmd_new_project: "New project…", cmd_open_project: "Open project…", cmd_save: "Save", cmd_save_as: "Save as…",
    cmd_import_menu: "Menu…", cmd_import_timeline: "Timeline…", cmd_import_slideshow: "Slideshow…", cmd_import_popup: "Pop-up menu…",
    cmd_locate_asset: "Locate asset…", cmd_interpret_footage: "Interpret footage…", cmd_transcode_settings: "Transcode settings…",
    cmd_render_slideshows: "Slideshows", cmd_rom_folder: "DVD-ROM content…",
    cmd_build_dvd_iso: "DVD image…", cmd_build_dvd_folder: "DVD folder…", cmd_build_dvd_disc: "DVD disc…",
    cmd_build_bd_iso: "Blu-ray image…", cmd_build_bd_folder: "Blu-ray folder…", cmd_build_bd_disc: "Blu-ray disc…", cmd_build_web: "Web (HTML5)…", cmd_close_window: "Close window",
    cmd_cut: "Cut", cmd_copy: "Copy", cmd_paste: "Paste", cmd_select_all: "Select all", cmd_deselect_all: "Deselect all",
    cmd_rename: "Rename…", cmd_edit_original: "Edit original",
    cmd_bring_forward: "Bring forward", cmd_send_backward: "Send backward", cmd_convert_button: "Convert to button", cmd_convert_object: "Convert to object",
    cmd_drop_shadow: "Drop shadow and stroke…",
    cmd_add_button: "Add button", cmd_add_text: "Add text", cmd_add_rectangle: "Add rectangle", cmd_add_picture: "Add picture…",
    cmd_default_button: "Set as default button", cmd_colour_set: "Edit menu colour set…", cmd_save_menu_file: "Save menu as file",
    cmd_set_first_play: "Set as first play",
    cmd_chapter_playlist: "New chapter playlist…", cmd_add_audio_track: "Add audio track…", cmd_add_subtitle_track: "Add subtitle track…",
    cmd_import_subtitles: "Import subtitles…", cmd_export_subtitles: "SubRip…", cmd_export_subtitles_script: "Text script…", cmd_clear_chapters: "Clear all chapter points",
    cmd_set_poster: "Set poster frame at playhead", cmd_save_frame: "Save frame as file",
    cmd_zoom_fit: "Fit in window", cmd_zoom_actual: "Actual size", cmd_snap: "Snap to objects and safe area",
    cmd_show_guides: "Show guides", cmd_lock_guides: "Lock guides", cmd_clear_guides: "Clear guides", cmd_new_guide: "New guide…",
    cmd_snap_guides: "Snap to guides", cmd_rotate_180: "180°", cmd_rotate_cw: "90° CW", cmd_rotate_ccw: "90° CCW",
    cmd_flip_h: "Flip horizontal", cmd_flip_v: "Flip vertical", cmd_tool_rotate: "Rotate tool",
    tool_rotate: "Rotate: drag an object around its centre (Shift: 45° steps)", guides: "Guides", new_guide: "New guide",
    guide_horizontal: "Horizontal guide", guide_vertical: "Vertical guide", guide_position: "Position (pixels)",
    guide_hint: "Guides help place objects in this menu; they are kept with it and never appear on the disc. Drag a guide to move it, off the menu to remove it.",
    transform: "Rotate and flip", rotation: "Rotation (° clockwise)", flip: "Flip", flip_none: "None", flip_horizontal: "Horizontal",
    flip_vertical: "Vertical", flip_both: "Both", transform_thumb_hint: "The label or picture turns with its highlight; the thumbnail stays as it is.",
    cmd_view_normal: "Normal", cmd_view_selected: "Selected", cmd_view_activated: "Activated", cmd_exact_preview: "Exact preview",
    cmd_reset_workspace: "Reset workspace", cmd_reload: "Reload", cmd_full_screen: "Enter full screen", cmd_minimize: "Minimise", cmd_zoom_window: "Zoom",
    cmd_help: "oncemore help",
    cmd_check_updates: "Check for Updates…", updates_text: "This is oncemore {v}. oncemore itself never connects to the internet, so it cannot look for new versions: the releases page lists every version with what is new in it and its download.", open_releases: "Open the releases page",
    cmd_sponsor: "Support oncemore (GitHub Sponsors)…", sponsor_text: "oncemore is free. If it helps you, you can support its development through GitHub Sponsors.",
    folder: "Folder", shadow_offset: "Shadow distance", outline_width: "Stroke width",
    no_recent: "No recent projects", folders: "Folders", fb_up: "Up one folder", fb_home: "Home", fb_empty: "No folders in here.",
    fb_hint_open: "Choose the project's folder (◉ marks folders with a project). A folder without one starts a new project.",
    fb_hint_new: "The project gets a folder of its own here: the project file, and the media you bring in.",
    fb_hint_save_as: "The project and its media are copied to a new folder here, which you then work in (builds and caches are not copied).",
    id_taken: "That id is empty or already used.", export: "Export", exported_to: "Saved in the project folder:",
    rendering_n: "Rendering {i} of {n}: {t}…", rendered_n: "{n} slideshows rendered.", this_title: "this title",
    chapter_playlist_hint: "A playlist that plays the title's chapters one after another (each is an item you can reorder or remove).",
    export_subs_hint: "Which track? It is saved in exports/.",
    fmt_srt: "SubRip (.srt)", fmt_script: "Text script (.txt)", script_import: "Import subtitles (text script)",
    script_hint: "A text script has a number, the start and end timecode and the text for each subtitle; its look comes from the subtitle style. Timecode hh;mm;ss;ff is NTSC drop frame. In an image script the text is a picture file next to the script (import them together); the pictures keep their own colours.",
    tc_absolute: "Absolute: the timecode is the title's", tc_relative: "Relative to", sub_offset: "Offset",
    captions: "Closed captions", cc_hint: "Line-21 captions for TVs and players with a caption decoder: a Scenarist .scc file as it is, or a subtitle file sent as pop-on captions (32 characters a row, Latin letters). DVD only.", cc_pal: "Closed captions (line 21) are for NTSC discs.",
    sub_offset_hint: "Taken off every subtitle's time: the start of the source's own timecode (e.g. 01;00;00;00)",
    cmd_chapter_names: "Show chapter names", chapter_label: "Chapter {n}",
    button_number: "Number", number_on_remote: "{n} (number key {k})",
    button_number_hint: "The button's number: the remote's number keys select it by this number. The other buttons are numbered again to close up.",
    button_offset: "Button number offset", button_offset_hint: "Added to every button's number for the number keys: with 10, the first button is 11 (to match chapter numbers, say).",
    confirm_clear_chapters: "Remove every chapter point after the start?",
    uops: "Remote keys turned off", uops_hint_title: "What the viewer cannot do while this title plays, e.g. skip a notice. Players follow it (DVD: user operations; Blu-ray: UO mask).",
    uops_hint_menu: "What the viewer cannot do while this menu shows.",
    uop_next: "Next chapter", uop_prev: "Previous chapter", uop_fast_forward: "Fast forward", uop_rewind: "Rewind", uop_pause: "Pause", uop_stop: "Stop",
    uop_search: "Number keys (title, chapter, time search)", uop_menu: "Menu / Pop-up key", uop_title: "Title / Top Menu key", uop_audio: "Audio change", uop_subtitle: "Subtitle change",
  },
  ja: {
    check: "チェック", build: "ビルド", drop_here: "ファイルをドロップしてプロジェクトに追加",
    disc: "ディスク", titles: "タイトル", menus: "メニュー", media: "素材", generated: "自動生成",
    add: "＋追加", add_files: "ここにファイルをドロップ、またはクリックして追加",
    saved: "保存済み", saving: "保存中…", unsaved: "未保存", save_error: "保存に失敗",
    issues: "問題 {n} 件", no_issues: "問題なし", tools_missing: "不足ツール：{t}",
    new_project: "新しい DVD プロジェクト", new_hint: "{dir} にはまだプロジェクトがありません。",
    label: "ディスクラベル", standard: "テレビ方式", aspect: "アスペクト比", target: "ディスク容量",
    first_play: "ディスク挿入時", video_bitrate: "映像ビットレート",
    auto: "自動", empty_project: "空のプロジェクトを作成", sample_project: "サンプル付きで作成",
    title_props: "タイトル", name: "名前", id: "ID", source: "動画ファイル", audio: "音声",
    codec: "形式", bitrate: "ビットレート", language: "言語", end_action: "再生終了後",
    title_key: "タイトル／トップメニューキーで開く", menu_key: "メニューキーで開く", menu_key_hint: "Blu-ray では、ここで選んだメニューがこのタイトルのポップアップメニューになり、ポップアップキーで映像の上にボタンが表示されます。", first_menu: "最初のメニュー",
    playback: "再生", loop: "再生回数", loop_forever: "ずっと繰り返す", loop_n: "{n} 回再生して…",
    loop_point: "繰り返しの開始位置（秒）", buttons_at_loop: "ボタンを繰り返しの開始位置から表示（イントロは最後まで再生）", fade_in: "黒からのフェードイン（秒）", menu_end: "最後の再生のあと", default_button: "最初に選ばれるボタン",
    remember_button: "戻ってきたら前に使ったボタンを選ぶ", auto_activate: "選んだだけで実行（決定キー不要）",
    chapter_menu: "チャプターメニュー", chapter_menu_on: "サムネイル付きチャプターメニューを自動生成",
    subtitles: "字幕", audio_tracks: "音声トラック", default_on: "最初から表示",
    add_chapter: "ここにチャプター", chapters: "チャプター", delete: "削除",
    add_shape: "＋四角形", add_picture: "＋画像", picture: "画像", pictures: "画像",
    place_on_menu: "メニューに配置", picture_hint: "ボタンではない画像（ロゴ・写真）。PNG は透明部分がそのまま残ります。",
    pick_picture: "プロジェクトのファイルから画像を選んでください（先にファイル > 読み込み）。", keep_ratio: "縦横比を保つ", snap: "スナップ", align: "整列", n_selected: "{n} 個選択中",
    align_left: "左揃え", align_hcenter: "左右中央揃え", align_right: "右揃え",
    align_top: "上揃え", align_vcenter: "上下中央揃え", align_bottom: "下揃え",
    distribute_h: "左右に等間隔", distribute_v: "上下に等間隔",
    stage_keys: "Shift+クリックで複数選択・矢印キーで移動・⌘D 複製・⌘C/⌘V・Alt でスナップなし",
    multi_hint: "ドラッグでまとめて移動、またはメニュー上の整列ボタンを使えます。",
    shape: "四角形", height: "高さ", fill: "塗り", opacity: "不透明度",
    paragraph: "段落", para_align: "行揃え", para_left: "左揃え", para_center: "中央揃え", para_right: "右揃え", line_spacing: "行間", paragraph_hint: "テキストの各行がメニューの 1 行になります（Return で改行）。X は段落の左端です。",
    text_style: "文字のスタイル", font: "フォント", disc_font: "ディスクのフォント", outline: "縁取り", shadow: "影",
    font_hint: ".ttf / .otf ファイルを素材に追加するとここで選べます。",
    highlight_image: "ハイライト画像", highlight_image_hint: "任意：不透明な部分が選択時に光る画像。",
    new_menu: "新しいメニュー", blank_menu: "白紙", template_hint: "レイアウトから始められます。あとから全部編集できます。",
    motion_bg: "動く背景", animated_thumbs: "サムネイルでチャプターを再生",
    set_audio: "音声を切替", set_subtitle: "字幕を切替", no_change: "変更しない",
    last_menu: "直前のメニューに戻る",
    override: "終了後（上書き）", override_none: "タイトル自身の終了時アクション",
    override_hint: "このボタンで再生したタイトルが終わったときの行き先。タイトル自身の終了時アクションの代わりに使われます（このボタンから再生したときだけ）。",
    transition: "リンクトランジション", transition_hint: "ボタンを押したとき、リンク先の前に再生する短いビデオ。たとえばこのメニューが次のメニューへ溶けていく映像。",
    thumb_section: "サムネイル", thumb_on: "リンク先のタイトル／チャプターの絵を表示",
    thumb_time: "フレーム位置（秒）", thumb_anim: "再生する（モーションメニュー）",
    sub_style: "字幕の見た目（全トラック）", sub_margin: "下の余白", outline_w: "縁取りの太さ",
    cm_heading: "見出し", cm_label_format: "ラベル（{n} = 番号）", cm_back_label: "BACK ボタン",
    cm_prev_label: "PREV ボタン", cm_next_label: "NEXT ボタン",
    scan: "走査方式", scan_auto: "自動", scan_progressive: "プログレッシブ",
    scan_interlaced: "インターレース（フィールドを保持）", scan_pulldown: "フィルム・3:2 プルダウン（23.976）",
    scan_ivtc: "テレシネ済みフィルム（29.97i → 23.976 + プルダウン）",
    scan_hint: "自動では、インターレースと 60p の映像はフィールドのまま、23.976 のフィルム素材はプルダウン指定で収録します。",
    no_transcode: "トランスコードしない（素材がすでに DVD ビデオ）", no_transcode_hint: "ディスクと同じフレームサイズ・フレームレートの MPEG-2 をそのまま収録します（Blu-ray では、すでに Blu-ray ビデオになっている H.264）。音声は下の設定で作り直します。条件を満たさないファイルはビルド時に理由を表示します。", status_no_transcode: "トランスコードしない",
    auto_shared: "自動（ディスク全体で配分）", passthrough: "AC-3 をそのままコピー",
    passthrough_hint: "AC-3（48kHz）素材向け：再エンコードしません。チャンネル数は素材と同じにしてください。",
    dts_copy: "DTS（コピー）", dts_hint: "DTS は素材からそのままコピーします（48kHz。DTS-HD はコア部分のみ）。チャンネル数は素材と同じにしてください。",
    layer_break: "レイヤーブレーク", layer_break_hint: "2 層ディスクが 2 層目へ移る位置です。ディスクの中ほどより後のチャプターの先頭に置きます。内蔵の ISO 書き出しが ECC ブロック境界に合わせ、書き込み時にドライブへ渡します。", layer_break_at: "{t}、チャプター {n}",
    rom_files: "DVD-ROM ファイル", rom_hint: "パソコン向けに VIDEO_TS と並べて入れるファイル／フォルダ（1 行に 1 つ、プロジェクトからの相対パス）。",
    no_cache: "すべてエンコードし直す（キャッシュを使わない）",
    sub_bottom: "下", sub_top: "上", sub_color: "色を指定",
    add_slideshow: "＋スライドショー", slideshow: "スライドショー", slideshow_hint: "写真から作るタイトル",
    slideshow_need_images: "先に写真を素材に追加してください（ウィンドウにドロップ）。",
    slideshow_preview_hint: "「書き出して再生」でディスクと同じ見え方を確認できます。",
    render_play: "書き出して再生", rendering: "書き出し中…", add_picture: "＋写真を追加…", seconds: "表示秒数",
    transition: "切り替え", crossfade: "クロスフェード", cut: "カット", transition_duration: "切り替えの長さ（秒）",
    tr_dissolve: "ディゾルブ", tr_fadeblack: "黒を経由", tr_fadewhite: "白を経由", tr_wipeleft: "ワイプ（左へ）", tr_wiperight: "ワイプ（右へ）", tr_wipeup: "ワイプ（上へ）", tr_wipedown: "ワイプ（下へ）",
    tr_slideleft: "スライド（左へ）", tr_slideright: "スライド（右へ）", tr_slideup: "スライド（上へ）", tr_slidedown: "スライド（下へ）", tr_circleopen: "円形（開く）", tr_circleclose: "円形（閉じる）", tr_radial: "放射状", tr_pixelize: "ピクセル化", tr_random: "ランダム", tr_own: "スライドショーの設定に従う", tr_next: "次の写真への切り替え",
    pan_zoom: "ゆっくりズーム（パン＆ズーム）", slideshow_chapters: "写真ごとにチャプターになります。",
    routing: "ルーティング", routing_hint: "各ボタンからリモコンの矢印キーで移る先を表示（実線：指定、破線：自動）",
    link_hint: "プロジェクトパネルのタイトル・メニュー・プレイリストをボタンにドラッグするとリンク、メニューの空いた所にドラッグするとそのボタンを追加します。",
    cmd_transcode_title: "このタイトルを今すぐトランスコード", cmd_transcode_all: "すべてのタイトルを今すぐトランスコード",
    transcoding: "トランスコード中", transcoded: "トランスコード済み（書き出し時に再利用）", not_transcoded: "未トランスコード（書き出し時にエンコード）",
    m_object: "オブジェクト", m_menu: "メニュー", m_timeline: "タイムライン", m_view: "表示", m_window: "ウィンドウ",
    cmd_preview: "プレビュー", cmd_set_link: "リンクを設定…", cmd_routing: "ボタンのルーティングを表示", cmd_safe_area: "セーフエリアを表示",
    cmd_tool_select: "選択ツール", cmd_tool_text: "テキストツール", cmd_tool_zoom: "ズームツール", cmd_zoom_in: "ズームイン", cmd_zoom_out: "ズームアウト",
    cmd_align_left: "左端揃え", cmd_align_hcenter: "左右中央揃え", cmd_align_right: "右端揃え",
    cmd_align_top: "上端揃え", cmd_align_vcenter: "上下中央揃え", cmd_align_bottom: "下端揃え",
    cmd_distribute_h: "左右に等間隔", cmd_distribute_v: "上下に等間隔", cmd_bring_front: "最前面へ", cmd_send_back: "最背面へ",
    cmd_convert: "テキスト ⇄ ボタンに変換", cmd_new_timeline: "動画から新規タイトル…", cmd_prev_chapter: "前のチャプター", cmd_next_chapter: "次のチャプター",
    new_timeline_hint: "タイトルで再生する動画を選んでください。", tools: "ツール", tool_select: "選択", tool_text: "テキスト：置きたい場所をクリック", tool_zoom: "ズーム：クリックで拡大、Alt+クリックで縮小",
    zoom_fit: "全体", zoom_hint: "表示倍率（+ / −）", safe_hint: "アクションセーフ／タイトルセーフ：テレビでは端が切れることがあります",
    subpictures: "ハイライト：", subpictures_hint: "全ボタンを通常・選択中・決定時の見え方で表示（ディスクと同じ画）",
    sp_normal: "通常", sp_selected: "選択中", sp_activated: "決定時", overlap_hint: "このボタンの範囲が他のボタンと重なっています：リモコンでどちらかに移れないことがあります",
    whip_hint: "タイトル・メニュー・プレイリスト（プロジェクトパネルかフローチャート）までドラッグしてリンク", flow_link_hint: "項目から別の項目へドラッグしてリンク：最初の再生、終了時の動作、メニューのボタン。",
    pick_button: "どのボタンからリンクしますか？", unused: "未使用",
    type_clips: "タイムライン（クリップ）", type_timeline: "タイムライン", type_chapter_menu: "チャプターメニュー", n_buttons: "ボタン {n}", n_items: "{n} 項目", kind_video: "ビデオ", kind_audio: "オーディオ", kind_image: "静止画", kind_subtitle: "字幕", kind_design: "Photoshop デザイン", kind_font: "フォント", col_name: "名前", col_type: "種類", col_duration: "デュレーション", col_buttons: "ボタン", col_first: "最初に再生", col_chapters: "チャプター", col_transcode: "トランスコード", buttons_of: "{m} のボタン", chapters_of: "{t} のチャプター", status_transcoded: "トランスコード済み", status_untranscoded: "未トランスコード", add_menu_short: "＋メニュー", add_playlist_short: "＋プレイリスト", panel_menu: "パネルメニュー", menu_viewer: "メニュービューア", layers_hint: "メニューを開くとレイヤーが表示されます。", timelines: "タイムライン", preferences: "環境設定", cmd_preferences: "環境設定…", appearance: "アピアランス", brightness: "明るさ", brightness_hint: "インターフェイスのグレーを明るく／暗くします（メニューや映像の画は変わりません）。", darker: "暗く", lighter: "明るく", default: "初期設定", welcome: "ようこそ", new_project_basic: "基本", authoring_mode: "オーサリングモード",
    m_file: "ファイル", m_edit: "編集", m_disc: "ディスク", m_view: "表示", m_help: "ヘルプ",
    cmd_import_files: "ファイルを読み込む…", cmd_import_psd: "Photoshop デザインを読み込む…", cmd_check: "プロジェクトをチェック",
    cmd_build: "ディスクをビルド…", cmd_reveal: "プロジェクトのフォルダを表示", cmd_undo: "取り消す", cmd_redo: "やり直す",
    cmd_duplicate: "複製", cmd_delete: "削除", cmd_new_slideshow: "新規スライドショー", cmd_new_menu: "新規メニュー…",
    cmd_new_playlist: "新規プレイリスト", cmd_add_chapter: "再生位置にチャプターを追加", cmd_play: "再生／一時停止",
    cmd_ws_author: "ワークスペース：初期設定", cmd_ws_flow: "ワークスペース：フローチャート", cmd_ws_sim: "プロジェクトプレビュー", cmd_ws_build: "ビルド",
    cmd_theme: "ライト／ダーク", cmd_language: "English", cmd_shortcuts: "キーボードショートカット", cmd_about: "oncemore について",
    open: "開く", set_first_play: "ディスクの最初に再生", copy_of: "{x} のコピー", reveal_file: "フォルダで表示",
    copy: "コピー", paste: "ペースト", nudge: "選択した要素を移動（Shift で 10px）", copy_paste: "要素のコピー／ペースト",
    about_text: "オープンソースの DVD-Video オーサリング。メニュー・チャプター・プレイリスト・ディスクイメージを自分のコンピュータで作れます。コピーガードはありません。",
    clips: "クリップ", add_clip: "クリップを追加…", clip_in: "イン", clip_out: "アウト", clip_end: "最後",
    clips_hint: "クリップは順番に続けて 1 つのタイトルとして再生されます。チャプターを指定しなければ、クリップごとにチャプターになります。",
    joining: "クリップをつないでいます…", clip_whole: "ファイル全体", clips_n: "{n} クリップ", clip_source_hint: "クリップを追加すると、複数の動画や静止画を 1 つのタイトルにつなげられます。",
    clip_still: "静止画", clip_duration: "静止画の表示秒数", fit: "拡大・縮小", fit_fit: "全体を表示（周囲に帯）", fit_fill: "画面いっぱい（端を切り抜き）", fit_own: "スライドショーの設定に従う",
    subtitle_editor: "字幕の編集", no_sub_tracks: "字幕トラックはまだありません。", new_srt: "＋新しい字幕ファイル",
    sub_readonly: "WebVTT / ASS は表示のみです。", convert_srt: ".srt に変換して編集",
    sub_track_pos: "トラック設定", add_cue: "＋再生位置に字幕を追加", new_cue_text: "新しい字幕",
    image: "画像", width: "幅", highlight_style: "ハイライト", hl_frame: "周りに枠", hl_shape: "画像の形",
    image_hint: "画像ボタンは文字の代わりに画像を表示します（透過 PNG がおすすめ）。",
    chapter_name: "チャプターメニューに出す名前", poster: "サムネイル", poster_hint: "再生位置のフレームをこのチャプターのサムネイルにする（もう一度押すと解除）",
    playlists: "プレイリスト", playlist: "プレイリスト", playlist_item: "プレイリスト：{p}", items: "再生する内容", add_item: "＋追加",
    from_chapter: "開始チャプター", to_chapter: "終了チャプター", to_end: "最後まで", playlist_end: "最後まで再生したら",
    playlist_order: "再生順", order_sequential: "並び順", order_random: "ランダム", order_shuffle: "シャッフル",
    order_hint: "ランダムは項目の数だけ、毎回ランダムに選んで再生します（同じ項目が続くこともあります）。シャッフルは全項目を 1 回ずつ、ランダムな順で再生します。Blu-ray と Web 版で有効です。DVD では並び順に再生します。",
    playlist_hint: "プレイリストはタイトルやチャプターの範囲をこの順に再生します。ボタンのリンク先に「プレイリスト：…」を選んでください。",
    move_up: "上へ", move_down: "下へ", order_title: "「全タイトルを連続再生」はこの順番で再生します。",
    order_menu: "ディスク挿入時は先頭のメニューが開きます（「ディスク挿入時」で別の指定がない場合）。",
    play: "再生", pause: "一時停止", preparing: "プレビューを準備中… {p}%", play_err: "このプレビューはここでは再生できません。",
    no_titles: "タイトルがまだありません。動画を「素材」にドロップして「タイトルとして追加」を選んでください。",
    add_as_title: "タイトルとして追加", use_as_bg: "メニュー背景に使う", use_as_music: "メニューの BGM に使う",
    use_as_video_bg: "動画背景（モーションメニュー）に使う", add_sub_to: "字幕として追加：",
    new_menu_with_bg: "この背景で新しいメニュー",
    menu_props: "メニュー", background: "背景画像", background_video: "背景動画",
    background_color: "背景色", music: "BGM", duration: "ループ長（秒）",
    sound_picture: "画像", black: "黒", sound_picture_hint: "素材が音声のみなので、再生中はこの静止画を表示します。",
    advance_manual: "手動で送る（次へ／再生を押すまで写真を表示）",
    add_music: "＋BGM を追加…", fit_to_music: "写真の表示時間を BGM の長さに合わせる（秒数は比率になります）", fitted_to: "調整後：{d}",
    font_size: "文字サイズ", text_color: "文字色", highlight: "選択中の色", select_color: "決定時の色",
    add_button: "＋ボタン", add_text: "＋テキスト", exact_preview: "実レンダリング確認", hide_preview: "確認を閉じる",
    safe_area: "セーフエリア", button: "ボタン", text: "テキスト", action: "リンク先", size: "サイズ", color: "色",
    nav: "リモコンの移動先", nav_auto: "自動", none: "なし", stop: "停止",
    playall: "全タイトルを連続再生", resume: "再生再開（メニューキーで中断したタイトル）", channels: "チャンネル", stereo: "ステレオ", surround: "5.1ch サラウンド",
    generated_menu: "このメニューは「{t}」のチャプターから自動生成されます。変更はそのタイトルの設定で行います。",
    go_to_title: "タイトルを開く",
    build_iso: "ディスクイメージ（.iso）", build_folder: "VIDEO_TS フォルダ", build_disc: "DVD ディスク（イメージを作って書き込み）",
    build_format: "フォーマット", format_dvd: "DVD", format_bluray: "Blu-ray", format_web: "Web（HTML5）", build_web_folder: "index.html の入ったフォルダー（ブラウザで開くか、Web サーバーに置きます）",
    web_note: "ブラウザ向けのディスク：ボタン付きのメニュー、チャプターと字幕付きの MP4 のタイトル、ディスクと同じリンク。音声はタイトルごとに 1 本です。", build_bdmv: "BDMV フォルダ", build_bd_disc: "Blu-ray ディスク（イメージを作って書き込み）", bd_size: "ディスク容量",
    bd_note: "Blu-ray: タイトルを HD（1920×1080）で、チャプター・プレイリスト・すべて再生付きで書き出します。メニューと字幕は今のところ DVD のみです。",
    recorder: "ドライブ", recorder_hint: "空欄なら最初のドライブ。ビルドの前に空のディスク（Blu-ray なら BD）を入れてください。",
    burned: "DVD に書き込みました", step_burn: "ディスクに書き込み", fast: "高速（1パス）エンコード",
    start_build: "開始", building: "ビルド中…", build_done: "完了", build_failed: "ビルドに失敗",
    reveal: "Finder で表示", reveal_other: "フォルダを開く", output: "出力先", warnings: "警告",
    step_probe: "素材をチェック", step_menu: "メニュー「{i}」を作成", step_encode: "タイトル「{i}」をエンコード",
    step_subtitles: "「{i}」の字幕を作成", step_author: "VIDEO_TS を構成", step_iso: "ディスクイメージを書き出し",
    media_cache: "メディアキャッシュ", cache_folder: "フォルダー", cache_in_project: "プロジェクトフォルダー内（.oncemore-cache）", cache_use: "使う",
    cache_in_project_short: "プロジェクト内", cache_now: "このプロジェクトの場所：{p}",
    cache_hint: "エンコード済みのタイトルとメニュー、書き出したスライドショー、再生用のコピーをここに置き、ビルドを速くします。全プロジェクト共通のフォルダー（容量の大きいドライブや速いドライブなど）を選ぶと、その中にプロジェクトごとのフォルダーを作ります。",
    check_ok: "書き出しできます", estimated: "推定サイズ", of: "／", video_avg: "平均映像ビットレート",
    budget: "ビットバジェット", budget_menus: "メニュー", budget_other: "ディスクのファイル", budget_free: "空き", budget_video: "映像 Mbit/s",
    budget_audio: "音声", budget_size: "サイズ", budget_share: "ディスクに占める割合", col_length: "長さ",
    menu_item: "メニュー：{m}", menu_button_item: "メニュー：{m} › {b}", title_item: "タイトル：{t}", chapter_item: "{t} › チャプター {n}",
    audio_item: "音声 {n}", subtitle_item: "字幕 {n}", subtitle_off: "字幕オフ",
    nothing_selected: "メニュー上のボタンやテキストを選択するか、下のメニュー設定を編集してください。",
    rename_hint: "ID を変えると、それを参照している箇所もまとめて更新されます。",
    flowchart: "フローチャート", simulator: "シミュレータ", menu: "メニュー", title: "タイトル",
    ws_author: "オーサリング", ws_preview: "プレビュー", properties: "プロパティ", project: "プロジェクト", library: "ライブラリ",
    lib_templates: "メニューテンプレート", lib_backgrounds: "背景", lib_text_styles: "文字スタイル",
    lib_style_hint: "メニューのボタンやテキストを選んでからスタイルをクリックします。",
    style_plain: "なし", style_outline: "縁取り", style_shadow: "影", style_outline_shadow: "縁取り＋影",
    layers: "レイヤー", buttons: "ボタン", texts: "テキスト", shapes: "四角形", rectangle: "四角形",
    timeline: "タイムライン", video: "映像",
    import_psd: "Photoshop から読み込み", import: "読み込む", importing: "レイヤーを読み込んでいます…",
    import_psd_hint: "レイヤー付きの .psd / .psb：「(+) 名前」のグループがボタン、その中の「(=1)」レイヤーがハイライト、「(%)」レイヤーがサムネイルの位置になり、それ以外の表示中のレイヤーが背景になります。ファイルはウィンドウにドロップして追加します。",
    no_psd: "素材に Photoshop ファイルがありません。.psd をウィンドウにドロップしてください。",
    imported_n: "{n} 個のボタンを読み込みました。", psd_actions_hint: "各ボタンのリンク先を右パネルで確認してください。「Play」「Scene 2」やタイトル名などの名前は自動でリンクします。",
    reimport: "読み込み直す", reimport_hint: "Photoshop で編集した後に：画像を更新し、ボタンのリンク先はそのまま残します。",
    make_menu_from_psd: "このデザインからメニューを作る",
    flow_hint: "ディスクで視聴者ができることの全体図です（ボタン、再生後の動作、タイムアウト、プレイリスト、リモコンのメニュー／タイトルキー）。箱をクリックすると編集できます。赤い箱はたどり着けないか、抜け出せない場所です。",
    sim_hint: "書き出す前にリモコンでディスクを操作できます（矢印・決定・メニュー・タイトル・前後のチャプター）。エンコードはせず、メニューは実レンダリングの画像です。キーボード：矢印、Enter、M、T、N、P。",
    fp: "ディスク挿入時", title_key_node: "タイトルキー", stop_node: "停止", play_all: "全タイトル連続再生",
    nav_ok: "ナビゲーションの問題はありません。", restart: "ディスクを入れ直す", play_chapter: "チャプターを再生",
    to_end: "最後まで再生", time_out: "メニューをタイムアウトさせる", now: "現在", chapter_n: "チャプター {n} / {m}",
    stopped: "再生が停止しました。", audio_n: "音声 {n}", sub_off: "字幕オフ", sub_n: "字幕 {n}",
    in_playall: "連続再生中", in_playlist: "プレイリスト",
    disc_tips: "座標は DVD のピクセル（幅 720）です。文字は全文字を描けるフォントを oncemore が自動で選んで描きます。",
    tools: "ツール", ok: "OK", missing: "不足", tracks_hint: "空なら動画自体の音声を使います。",
    stream: "ストリーム", file: "ファイル", add_track: "＋トラック", add_sub: "＋字幕ファイル",
    frame_err: "このフレームを表示できません", preview_err: "プレビューに失敗",
    confirm_delete: "「{x}」を削除しますか？", chapter_at: "チャプター {n}", playhead: "再生位置",
    workspace: "ワークスペース", ws_default: "初期設定", monitor: "モニター", no_menus: "（メニューなし）", no_timelines: "（タイムラインなし）",
    project_preview: "プロジェクトプレビュー", search: "検索", fit: "全体表示", step_back: "1 フレーム戻る", step_fwd: "1 フレーム進む",
    prev_ch: "前のチャプター", next_ch: "次のチャプター", tc_source: "ソース", no_timeline_open: "プロジェクトパネルでタイムラインを開くとここに表示されます。",
    prop_disc: "ディスク", prop_title: "タイムライン", prop_menu: "メニュー", prop_button: "ボタン", prop_text: "テキスト", prop_shape: "長方形",
    prop_asset: "アセット", prop_playlist: "チャプタープレイリスト", prop_slideshow: "スライドショー",
    name_location: "名前と場所", project_settings: "プロジェクト設定", location: "場所", transcode_settings: "トランスコード設定",
    np_transcode: "コーデック：MPEG-2、サイズ：{d}、フレームレート：{f}、音声：AC-3 / PCM、最大ビットレート：9.8 Mbps",
    np_info: "ディスクの設定は、あとからいつでもプロパティパネルで変更できます（フローチャートでディスクを選択）。",
    np_open_sample: "サンプルプロジェクトを開く", advanced: "詳細", cancel: "キャンセル",
    build_source: "ソース", current_project: "現在のプロジェクト", destination: "保存先", disc_info: "ディスク情報",
    settings: "設定", size_estimate: "推定サイズ", check_project: "プロジェクトをチェック…", new_item: "新規項目", delete_item: "削除",
    tool_import_psd: "Photoshop ファイルからメニューを作る", preview_close: "プレビューを閉じる",
    basic: "基本", motion: "モーション", toggle_safe: "セーフエリアを表示",
    cmd_chapters_interval: "一定間隔でチャプターポイントを追加…", cmd_chapters_scenes: "シーンチェンジにチャプターポイントを追加…",
    sc_sensitivity: "感度", sc_low: "低（はっきりしたカットだけ）", sc_medium: "中", sc_high: "高（小さな変化も）", sc_gap: "最小間隔（秒）",
    sc_find: "検出", sc_looking: "シーンチェンジを探しています…", sc_found: "シーンチェンジが {n} か所見つかりました：チャプター {c} 個。",
    sc_hint: "映像のカット（場面の切り替わり）を見つけ、指定した秒数以上の間隔でチャプターを置きます。", cmd_replace_asset: "アセットを置き換え…", cmd_project_settings: "プロジェクト設定…",
    cmd_edit_psd: "Photoshop でメニューを編集", cmd_win_project: "プロジェクト", cmd_win_menus: "メニュー", cmd_win_timelines: "タイムライン", cmd_win_build: "ビルド",
    cmd_win_monitor: "モニター", cmd_win_flowchart: "フローチャート", cmd_win_properties: "プロパティ", cmd_win_layers: "レイヤー", cmd_win_library: "ライブラリ",
    cmd_chapters_from_source: "ソースのチャプターマーカーを読み込む", no_source_chapters: "ソースにチャプターマーカーがありません。",
    ci_every: "チャプターの間隔", ci_minutes: "分", ci_seconds: "秒", ci_replace: "今あるチャプターを消す（最初のチャプターは残します）",
    ci_preview: "{d} の中にチャプターが {n} 個になります。", ra_what: "置き換えるファイル", ra_with: "新しいファイル", ra_uses: "プロジェクト内で {n} か所で使われています。", ra_missing: "見つかりません",
    ra_hint: "プロジェクト内のすべての使用箇所（タイトル、クリップ、音声・字幕トラック、メニューの背景、ボタン、スライドショー、BGM）が新しいファイルを指すようになります。",
    ra_none: "プロジェクトはまだファイルを使っていません。", psd_changed: "このメニューの Photoshop ファイルが変更されました。", open_failed: "このシステムにはファイルを開くプログラムがありません。",
    colour_set: "カラーセット", cs_normal: "通常時の色", opacity: "不透明度",
    cs_normal_hint: "選択されていないボタンのハイライト形状をこの色で表示します",
    cs_hint: "ボタンのハイライト形状の色：通常時（選択されていないとき・任意）、選択中、決定時。DVD プレーヤーの不透明度は 16 段階です。",
    layer_hide: "非表示にする（ディスクに入れない）", layer_show: "表示する",
    cmd_revert_backup: "保存済みの版に戻す…", revert: "戻す", no_backups: "まだ以前の版はありません。",
    backups_hint: "oncemore は変更前のプロジェクトを最大 {m} 分ごとに保存しています（直近 30 版、プロジェクトの隣の .oncemore-backup）。戻すのも 1 つの編集なので、取り消すで今の状態に戻れます。",
    backup_counts: "タイトル {t}・メニュー {m}", confirm_revert: "プロジェクトをこの版に置き換えますか？（取り消すで今の状態に戻せます）",
    cmd_save_template: "メニューをテンプレートとして保存…", cmd_chapter_index: "チャプターインデックスを作成…", cmd_add_page: "新規ページを追加", cmd_delete_page: "ページを削除",
    pages: "ページ", pages_hint: "メニューのページ（一度に 1 ページを表示）。ディスクではページごとに別のメニューになります。ボタンでページをめくります（次のページ・前のページ・ページ n）。",
    page_field: "ページ", page_all: "すべてのページ", page_item: "ページ {n}", page_next: "次のページ", page_prev: "前のページ", page_of: "ページ {n} / {m}",
    page_hint: "このページだけに置くか、メニューのすべてのページに置くか（見出し・背景・ページをめくるボタンなど）。", lib_my_styles: "マイスタイル", ustyle_use: "選択中のオブジェクトにこの見た目を適用（図形は色のみ）", ustyle_none: "まだありません：テキスト・ボタン・図形を選んで見た目を保存してください。", ustyle_save: "選択範囲をスタイルとして保存…", ustyle_save_hint: "選択中のオブジェクトの見た目（フォント・サイズ・色・縁取り・影）を、どのプロジェクトのどのメニューでも使えるよう保存します", ustyle_name: "スタイル名", ustyle_default_name: "マイスタイル", lib_my_templates: "マイテンプレート",
    utpl_use: "このテンプレートから新しいメニュー", utpl_none: "メニュー > メニューをテンプレートとして保存 で、画像ごとメニューをここに保存し、どのプロジェクトでも使えます。",
    utpl_hint: "メニューと、使っているファイル（背景・画像・フォント・BGM）のコピーをテンプレートライブラリに保存します。どのプロジェクトからでもこのメニューを元に作れます。",
    utpl_saved: "「{n}」をライブラリ（マイテンプレート）に保存しました。",
    chapter_index_hint: "タイトルのチャプターメニュー（1 ページ 6 チャプター、チャプター名とポスターフレーム付き）を作って開きます。",
    theme_dark: "ダーク", theme_light: "ライト",
    skin: "スキン", skin_modern: "モダン", skin_classic: "クラシック", skin_hint: "クラシック：昔ながらのディスクオーサリングアプリの見た目（中間グレーのパネル、明るい入力欄、琥珀色のタイムコード）。配置は同じです。",
    // P48: メニューバー
    m_open_recent: "最近使用したプロジェクトを開く", m_import_as: "読み込み", m_transcode: "トランスコード", m_render: "レンダリング", m_build: "ビルド", m_export_subs: "字幕を書き出し",
    m_align: "整列", m_distribute: "分布", m_arrange: "重ね順", m_rotate: "回転", m_tools: "ツール", m_highlights: "ハイライトを表示", m_workspace: "ワークスペース",
    cmd_new_project: "新規プロジェクト…", cmd_open_project: "プロジェクトを開く…", cmd_save: "保存", cmd_save_as: "別名で保存…",
    cmd_import_menu: "メニュー…", cmd_import_timeline: "タイムライン…", cmd_import_slideshow: "スライドショー…", cmd_import_popup: "ポップアップメニュー…",
    cmd_locate_asset: "アセットを探す…", cmd_interpret_footage: "フッテージを変換…", cmd_transcode_settings: "トランスコード設定…",
    cmd_render_slideshows: "スライドショー", cmd_rom_folder: "DVD-ROM コンテンツ…",
    cmd_build_dvd_iso: "DVD イメージ…", cmd_build_dvd_folder: "DVD フォルダー…", cmd_build_dvd_disc: "DVD ディスク…",
    cmd_build_bd_iso: "Blu-ray イメージ…", cmd_build_bd_folder: "Blu-ray フォルダー…", cmd_build_bd_disc: "Blu-ray ディスク…", cmd_build_web: "Web（HTML5）…", cmd_close_window: "ウインドウを閉じる",
    cmd_cut: "カット", cmd_copy: "コピー", cmd_paste: "ペースト", cmd_select_all: "すべてを選択", cmd_deselect_all: "選択を解除",
    cmd_rename: "名前を変更…", cmd_edit_original: "オリジナルを編集",
    cmd_bring_forward: "前面へ", cmd_send_backward: "背面へ", cmd_convert_button: "ボタンに変換", cmd_convert_object: "オブジェクトに変換",
    cmd_drop_shadow: "ドロップシャドウと境界線…",
    cmd_add_button: "ボタンを追加", cmd_add_text: "テキストを追加", cmd_add_rectangle: "長方形を追加", cmd_add_picture: "画像を追加…",
    cmd_default_button: "デフォルトのボタンに設定", cmd_colour_set: "メニューカラーセットを編集…", cmd_save_menu_file: "メニューをファイルとして保存",
    cmd_set_first_play: "ファーストプレイに設定",
    cmd_chapter_playlist: "新規チャプタープレイリスト…", cmd_add_audio_track: "オーディオトラックを追加…", cmd_add_subtitle_track: "字幕トラックを追加…",
    cmd_import_subtitles: "字幕を読み込み…", cmd_export_subtitles: "SubRip…", cmd_export_subtitles_script: "テキストスクリプト…", cmd_clear_chapters: "すべてのチャプターポイントを消去",
    cmd_set_poster: "再生ヘッドの位置をポスターフレームに設定", cmd_save_frame: "フレームをファイルとして保存",
    cmd_zoom_fit: "ウインドウに合わせる", cmd_zoom_actual: "実際のサイズ", cmd_snap: "オブジェクトとセーフエリアにスナップ",
    cmd_show_guides: "ガイドを表示", cmd_lock_guides: "ガイドをロック", cmd_clear_guides: "ガイドを消去", cmd_new_guide: "新規ガイド…",
    cmd_snap_guides: "ガイドにスナップ", cmd_rotate_180: "180°", cmd_rotate_cw: "90°（時計回り）", cmd_rotate_ccw: "90°（反時計回り）",
    cmd_flip_h: "水平方向に反転", cmd_flip_v: "垂直方向に反転", cmd_tool_rotate: "回転ツール",
    tool_rotate: "回転：オブジェクトを中心のまわりにドラッグ（Shift：45° ずつ）", guides: "ガイド", new_guide: "新規ガイド",
    guide_horizontal: "水平ガイド", guide_vertical: "垂直ガイド", guide_position: "位置（ピクセル）",
    guide_hint: "ガイドはこのメニューでオブジェクトを配置するための線です。メニューと一緒に保存され、ディスクには出ません。ドラッグで移動、メニューの外へドラッグで削除します。",
    transform: "回転と反転", rotation: "回転（時計回りの角度）", flip: "反転", flip_none: "なし", flip_horizontal: "水平",
    flip_vertical: "垂直", flip_both: "両方", transform_thumb_hint: "ラベルや画像はハイライトと一緒に回ります。サムネイルはそのままです。",
    cmd_view_normal: "通常", cmd_view_selected: "選択", cmd_view_activated: "決定", cmd_exact_preview: "正確なプレビュー",
    cmd_reset_workspace: "ワークスペースをリセット", cmd_reload: "再読み込み", cmd_full_screen: "フルスクリーンにする", cmd_minimize: "しまう", cmd_zoom_window: "拡大／縮小",
    cmd_help: "oncemore ヘルプ",
    cmd_check_updates: "アップデートを確認…", updates_text: "このアプリは oncemore {v} です。oncemore 自身はインターネットに接続しないため、新しい版を自動では探しません。リリースのページに、すべての版の新機能とダウンロードがあります。", open_releases: "リリースのページを開く",
    cmd_sponsor: "oncemore を支援（GitHub Sponsors）…", sponsor_text: "oncemore は無料です。役に立ったら GitHub Sponsors から開発を支援できます。",
    folder: "フォルダー", shadow_offset: "影の距離", outline_width: "境界線の幅",
    no_recent: "最近使用したプロジェクトはありません", folders: "フォルダー", fb_up: "1 つ上のフォルダー", fb_home: "ホーム", fb_empty: "フォルダーがありません。",
    fb_hint_open: "プロジェクトのフォルダーを選びます（◉ はプロジェクトのあるフォルダー）。プロジェクトのないフォルダーでは新しいプロジェクトを始めます。",
    fb_hint_new: "ここにプロジェクト専用のフォルダーを作ります（プロジェクトファイルと、読み込んだ素材が入ります）。",
    fb_hint_save_as: "プロジェクトと素材をここの新しいフォルダーにコピーし、以後はそちらで作業します（ビルド結果とキャッシュはコピーしません）。",
    id_taken: "ID が空か、すでに使われています。", export: "書き出し", exported_to: "プロジェクトのフォルダーに保存しました：",
    rendering_n: "{n} 件中 {i} 件目をレンダリング中：{t}…", rendered_n: "{n} 件のスライドショーをレンダリングしました。", this_title: "このタイトル",
    chapter_playlist_hint: "タイトルのチャプターを順に再生するプレイリストです（各チャプターが項目になり、並べ替えや削除ができます）。",
    export_subs_hint: "どのトラックを書き出しますか？ exports/ に保存します。",
    fmt_srt: "SubRip（.srt）", fmt_script: "テキストスクリプト（.txt）", script_import: "字幕を読み込み（テキストスクリプト）",
    script_hint: "テキストスクリプトは字幕ごとに番号・開始と終了のタイムコード・テキストを並べたファイルです。見た目は字幕スタイルに従います。タイムコード hh;mm;ss;ff は NTSC のドロップフレームです。画像スクリプトではテキストの代わりにスクリプトと同じ場所の画像ファイル名を書きます（スクリプトと一緒に読み込んでください）。画像は自分の色のまま使われます。",
    tc_absolute: "絶対：タイムコードがそのままタイトルの時間", tc_relative: "相対：基準", sub_offset: "オフセット",
    captions: "クローズドキャプション", cc_hint: "キャプションデコーダー付きのテレビやプレーヤー向けの Line 21 キャプション：Scenarist の .scc はそのまま、字幕ファイルはポップオン方式で送ります（1 行 32 文字、ラテン文字のみ）。DVD のみ。", cc_pal: "クローズドキャプション（Line 21）は NTSC のディスク用です。",
    sub_offset_hint: "各字幕の時間から引く値：素材自身のタイムコードの開始（例 01;00;00;00）",
    cmd_chapter_names: "チャプター名を表示", chapter_label: "チャプター {n}",
    button_number: "番号", number_on_remote: "{n}（数字キー {k}）",
    button_number_hint: "ボタンの番号：リモコンの数字キーでこの番号のボタンを選びます。他のボタンの番号は詰めて付け直されます。",
    button_offset: "ボタン番号のオフセット", button_offset_hint: "数字キー用に各ボタンの番号へ足す値。10 なら最初のボタンは 11（チャプター番号と合わせるときなど）。",
    confirm_clear_chapters: "先頭以外のチャプターポイントをすべて削除しますか？",
    uops: "無効にするリモコン操作", uops_hint_title: "このタイトルの再生中に視聴者ができない操作（注意書きを飛ばせないようにするなど）。プレーヤーはこれに従います（DVD：ユーザー操作、Blu-ray：UO マスク）。",
    uops_hint_menu: "このメニューの表示中に視聴者ができない操作。",
    uop_next: "次のチャプター", uop_prev: "前のチャプター", uop_fast_forward: "早送り", uop_rewind: "巻き戻し", uop_pause: "一時停止", uop_stop: "停止",
    uop_search: "数字キー（タイトル・チャプター・時間の検索）", uop_menu: "メニュー／ポップアップキー", uop_title: "タイトル／トップメニューキー", uop_audio: "音声の切り替え", uop_subtitle: "字幕の切り替え",
  },
};
let LANG = (() => {
  try { const saved = localStorage.getItem("oncemore.lang"); if (saved) return saved; } catch (e) { /* storage blocked */ }
  return (navigator.language || "en").toLowerCase().startsWith("ja") ? "ja" : "en";
})();
// links a link transition can lead into (not stream switches, resume or stop)
const TRANSITION_RE = /^(menu|title|chapter|playlist):|^playall$/;

function t(key, vars) {
  let s = (I18N[LANG] && I18N[LANG][key]) || I18N.en[key] || key;
  for (const [k, v] of Object.entries(vars || {})) s = s.replace(`{${k}}`, v);
  return s;
}

// ---------------------------------------------------------------- state
const S = {
  token: "", project: null, dir: "", media: [], check: null, tools: {}, platform: "",
  sel: { view: "disc" }, element: null, probes: {}, playhead: {},
  undo: [], redo: [], saveTimer: null, saveState: "saved",
  preview: null, previewFor: null, showSafe: true, selectedMedia: null,
  job: null, jobEvents: [], uploads: {},
};

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clone = (o) => JSON.parse(JSON.stringify(o));

async function api(path, { method = "GET", body, raw } = {}) {
  const headers = { "X-Oncemore-Token": S.token };
  let payload;
  if (raw !== undefined) payload = raw;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const res = await fetch(path, { method, headers, body: payload });
  const data = res.headers.get("Content-Type")?.includes("json") ? await res.json() : null;
  if (!res.ok) { const e = new Error((data && data.error) || res.statusText); e.data = data; e.status = res.status; throw e; }
  return data;
}
const imgUrl = (endpoint, params) =>
  `/api/${endpoint}?` + new URLSearchParams({ ...params, token: S.token }).toString();

// ---------------------------------------------------------------- time helpers
function parseTime(v) {
  if (typeof v === "number") return v;
  const parts = String(v).trim().split(":").map(Number);
  return parts.reduce((acc, p) => acc * 60 + p, 0);
}
function fmtTime(sec, ms = true) {
  sec = Math.max(0, sec);
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const ss = ms ? s.toFixed(3).padStart(6, "0") : String(Math.floor(s)).padStart(2, "0");
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${ss}`;
}
const fmtBytes = (n) => n > 2 ** 30 ? (n / 2 ** 30).toFixed(2) + " GiB" : n > 2 ** 20 ? (n / 2 ** 20).toFixed(1) + " MiB" : Math.round(n / 1024) + " KiB";

// ---------------------------------------------------------------- project model helpers
const P = () => S.project;
const discH = () => (P()?.disc?.standard === "PAL" ? 576 : 480);
const discDar = (aspect) => (aspect || P()?.disc?.aspect) === "4:3" ? 4 / 3 : 16 / 9;
const displayW = () => Math.round((discH() * discDar()) / 2) * 2;
// chapters are times or {time, name, poster} objects
function chapterEntries(title) {
  let e = (title.chapters || []).map((c) => (typeof c === "object" && c !== null
    ? { time: parseTime(c.time), name: c.name || "", poster: c.poster == null ? null : parseTime(c.poster) }
    : { time: parseTime(c), name: "", poster: null })).sort((a, b) => a.time - b.time);
  const join = !title.chapters && title.clips ? clipJoinNow(title) : null;
  if (join) e = join.starts.map((time) => ({ time, name: "", poster: null }));
  if (!e.length || e[0].time > 0) e.unshift({ time: 0, name: "", poster: null });
  return e;
}
// titles made of clips: the server joins them into one preview (cached) and
// says where each clip starts on the title's timeline
const clipKey = (ti) => JSON.stringify([ti.clips, P().disc.standard, ti.aspect || P().disc.aspect, ti.audio || {}]);
function clipJoin(ti) {
  S.clipJoins = S.clipJoins || {};
  const k = clipKey(ti);
  if (!S.clipJoins[k]) {
    S.clipJoins[k] = api("/api/clips", { method: "POST", body: { title: ti.id, project: S.project } })
      .then((r) => (S.clipJoins[k] = r), (e) => { delete S.clipJoins[k]; throw e; });
  }
  return Promise.resolve(S.clipJoins[k]);
}
function clipJoinNow(ti) {
  const r = S.clipJoins && S.clipJoins[clipKey(ti)];
  return r && !(r instanceof Promise) ? r : null;
}
const STILL_RE = /\.(png|jpe?g|bmp|tiff?|webp)$/i;
const isStill = (c) => STILL_RE.test(c.source || "");
function clipEditorHtml(ti, join) {
  const list = ti.clips || [];
  const add = selectHtml("addclip", [["", t("add_clip")], ...mediaOf("video").map((v) => [v, v.replace(/^media\//, "")]),
    ...mediaOf("image").filter((v) => STILL_RE.test(v)).map((v) => [v, `${v.replace(/^media\//, "")} (${t("clip_still")})`])], "", 'id="clip-add" class="shrink"');
  if (!list.length) return `<h3>${t("clips")}</h3><div class="row"><span class="hint">${esc(t("clip_source_hint"))}</span><span class="spacer"></span>${add}</div>`;
  return `<h3>${t("clips")} (${list.length})</h3><div class="hint">${esc(t("clips_hint"))}</div>
    <table class="clips"><tbody>${list.map((c, i) => {
      const j = join && join.clips[i];
      return `<tr data-clip="${i}"><td class="n">${i + 1}</td>
        <td class="src" ${j ? `data-cseek="${j.start}"` : ""}>${esc(c.source.replace(/^media\//, ""))}${j ? ` <span class="muted mono">${fmtTime(j.start)} · ${j.duration.toFixed(2)}s</span>` : ""}</td>
        ${isStill(c) ? `<td><input type="number" class="mono" data-cd min="0.5" max="3600" step="0.5" value="${c.duration != null ? parseTime(c.duration) : 5}" title="${esc(t("clip_duration"))}"> s</td>
        <td>${selectHtml("fit", [["fit", t("fit_fit")], ["fill", t("fit_fill")]], c.fit || "fit", `data-cfit title="${esc(t("fit"))}"`)}</td>`
        : `<td><input class="mono" data-cf="in" value="${c.in != null ? fmtTime(parseTime(c.in)) : ""}" placeholder="00:00:00.000" title="${esc(t("clip_in"))}"></td>
        <td><input class="mono" data-cf="out" value="${c.out != null ? fmtTime(parseTime(c.out)) : ""}" placeholder="${esc(t("clip_end"))}" title="${esc(t("clip_out"))}"></td>`}
        <td class="act"><button class="small" data-cmv="-1" ${i ? "" : "disabled"}>▲</button><button class="small" data-cmv="1" ${i + 1 < list.length ? "" : "disabled"}>▼</button><button class="small danger" data-crm ${list.length > 1 ? "" : "disabled"}>✕</button></td></tr>`;
    }).join("")}</tbody></table>
    <div class="row"><span class="spacer"></span>${add}</div>`;
}
function bindClipEditor(m, ti, seek) {
  const edit = (fn) => commit((p) => {
    const x = p.titles.find((y) => y.id === ti.id);
    fn(x);
    // one whole video clip left: an ordinary title again (a picture stays a clip)
    if (x.clips && x.clips.length === 1 && x.clips[0].in == null && x.clips[0].out == null && !isStill(x.clips[0])) { x.source = x.clips[0].source; delete x.clips; }
  });
  const add = m.querySelector("#clip-add");
  if (add) add.onchange = () => {
    const v = add.value;
    if (v) edit((x) => {
      if (!x.clips) {
        // the title's own video becomes the first clip; joined clips have one sound track
        x.clips = [{ source: x.source }]; delete x.source; delete x.audio_tracks;
        if (x.audio) delete x.audio.passthrough;
        // only the start marked: let every clip start a chapter instead
        if ((x.chapters || []).every((c) => typeof c !== "object" && parseTime(c) === 0)) delete x.chapters;
      }
      x.clips.push({ source: v });
    });
  };
  m.querySelectorAll("tr[data-clip]").forEach((row) => {
    const i = Number(row.dataset.clip);
    row.querySelectorAll("[data-cf]").forEach((inp) => (inp.onchange = () => edit((x) => {
      const v = inp.value.trim();
      if (v) x.clips[i][inp.dataset.cf] = fmtTime(parseTime(v)); else delete x.clips[i][inp.dataset.cf];
    })));
    const cd = row.querySelector("[data-cd]");
    if (cd) cd.onchange = () => edit((x) => {
      const v = Math.min(3600, Math.max(0.5, Number(cd.value) || 5));
      if (v !== 5) x.clips[i].duration = v; else delete x.clips[i].duration;
    });
    const cf = row.querySelector("[data-cfit]");
    if (cf) cf.onchange = () => edit((x) => { if (cf.value === "fill") x.clips[i].fit = "fill"; else delete x.clips[i].fit; });
    row.querySelectorAll("[data-cmv]").forEach((b) => (b.onclick = () => edit((x) => {
      const j = i + Number(b.dataset.cmv); [x.clips[i], x.clips[j]] = [x.clips[j], x.clips[i]];
    })));
    row.querySelector("[data-crm]").onclick = () => edit((x) => { x.clips.splice(i, 1); });
    const go = row.querySelector("[data-cseek]");
    if (go && seek) go.onclick = () => seek(Number(go.dataset.cseek));
  });
}
const chaptersOf = (title) => chapterEntries(title).map((e) => e.time);
function setChapters(title, entries) {
  title.chapters = entries.map((e) => {
    const time = e.time === 0 ? "00:00:00" : fmtTime(e.time);
    if (!e.name && e.poster == null) return time;
    const o = { time };
    if (e.name) o.name = e.name;
    if (e.poster != null) o.poster = fmtTime(e.poster);
    return o;
  });
}
function generatedMenus(p = P()) {
  const out = [];
  for (const ti of p?.titles || []) {
    const spec = ti.auto_chapter_menu;
    if (!spec) continue;
    const base = (spec === true ? null : spec.id) || `chapters_${ti.id}`;
    const pages = Math.max(1, Math.ceil(chaptersOf(ti).length / 6));
    for (let i = 0; i < pages; i++) out.push({ id: i ? `${base}_${i + 1}` : base, title: ti.id });
  }
  return out;
}
const allMenuIds = () => [...(P()?.menus || []).map((m) => m.id), ...generatedMenus().map((g) => g.id)];
function uniqueId(prefix, existing) {
  let n = 1;
  while (existing.includes(`${prefix}${n}`)) n++;
  return `${prefix}${n}`;
}
function actionOptions({ forButton = true, allowStop = true, includeChapters = forButton, allowPlayAll = forButton, allowLast = false } = {}) {
  const p = P(), opts = [];
  const here = forButton && S.sel.view === "menu" ? curMenu() : null;
  if (here && pagesOf(here) > 1) {
    opts.push(["page:next", pageName("next")], ["page:prev", pageName("prev")]);
    for (let i = 1; i <= pagesOf(here); i++) opts.push([`page:${i}`, pageName(String(i))]);
  }
  if (allowLast && (p.menus || []).length) opts.push(["lastmenu", t("last_menu")]);
  for (const id of allMenuIds()) {
    opts.push([`menu:${id}`, t("menu_item", { m: id })]);
    // the menu opened with one of its buttons highlighted
    for (const b of (p.menus || []).find((m) => m.id === id)?.buttons || [])
      opts.push([`menu:${id}:${b.id}`, t("menu_button_item", { m: id, b: b.label || b.id })]);
  }
  if (allowPlayAll && (p.titles || []).length) opts.push(["playall", t("playall")]);
  if (allowPlayAll) for (const pl of p.playlists || []) opts.push([`playlist:${pl.id}`, t("playlist_item", { p: pl.name || pl.id })]);
  for (const ti of p.titles || []) {
    opts.push([`title:${ti.id}`, t("title_item", { t: ti.name || ti.id })]);
    if (includeChapters) chaptersOf(ti).forEach((_, i) =>
      opts.push([`chapter:${ti.id}:${i + 1}`, t("chapter_item", { t: ti.name || ti.id, n: i + 1 })]));
  }
  if (forButton && (p.titles || []).length) opts.push(["resume", t("resume")]);
  if (forButton) {
    const na = Math.max(1, ...(p.titles || []).map((x) => (x.audio_tracks || []).length));
    const ns = Math.max(0, ...(p.titles || []).map((x) => (x.subtitles || []).length));
    if (na > 1) for (let i = 1; i <= na; i++) opts.push([`audio:${i}`, t("audio_item", { n: i })]);
    for (let i = 1; i <= ns; i++) opts.push([`subtitle:${i}`, t("subtitle_item", { n: i })]);
    if (ns) opts.push(["subtitle:off", t("subtitle_off")]);
  }
  if (allowStop) opts.push(["stop", t("stop")]);
  return opts;
}
// a button's audio / subtitle switches made along with its action
function streamsHtml(b) {
  const p = P();
  const na = Math.max(1, ...(p.titles || []).map((x) => (x.audio_tracks || []).length));
  const ns = Math.max(0, ...(p.titles || []).map((x) => (x.subtitles || []).length));
  if (/^(audio|subtitle):/.test(b.action || "") || (na < 2 && !ns)) return "";
  const range = (n) => Array.from({ length: n }, (_, i) => [String(i + 1), String(i + 1)]);
  return `<div class="grid2">
    ${na > 1 ? `<label class="field"><span>${t("set_audio")}</span>${selectHtml("audio", [["__none__", t("no_change")], ...range(na)], b.audio ? String(b.audio) : "__none__")}</label>` : ""}
    ${ns ? `<label class="field"><span>${t("set_subtitle")}</span>${selectHtml("subtitle", [["__none__", t("no_change")], ["0", t("subtitle_off")], ...range(ns)], b.subtitle != null ? String(b.subtitle) : "__none__")}</label>` : ""}
  </div>`;
}
function selectHtml(name, opts, value, attrs = "") {
  const has = opts.some(([v]) => v === value);
  const extra = !has && value ? `<option value="${esc(value)}" selected>${esc(value)}</option>` : "";
  return `<select data-k="${esc(name)}" ${attrs}>${extra}${opts.map(([v, l]) =>
    `<option value="${esc(v)}" ${v === value ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
}
function renameRefs(p, kind, oldId, newId) {
  const fix = (a) => {
    if (!a) return a;
    if (kind === "menu" && a === `menu:${oldId}`) return `menu:${newId}`;
    if (kind === "menu" && a.startsWith(`menu:${oldId}:`)) return `menu:${newId}:` + a.split(":")[2];
    if (kind === "title") {
      if (a === `title:${oldId}`) return `title:${newId}`;
      if (a.startsWith(`chapter:${oldId}:`)) return `chapter:${newId}:` + a.split(":")[2];
    }
    if (kind === "playlist" && a === `playlist:${oldId}`) return `playlist:${newId}`;
    return a;
  };
  p.disc.first_play = fix(p.disc.first_play);
  for (const ti of p.titles || []) {
    ti.end_action = fix(ti.end_action);
    if (kind === "menu" && ti.remote_menu === oldId) ti.remote_menu = newId;
    if (ti.auto_chapter_menu && typeof ti.auto_chapter_menu === "object") ti.auto_chapter_menu.back = fix(ti.auto_chapter_menu.back);
  }
  for (const m of p.menus || []) {
    for (const b of m.buttons || []) { b.action = fix(b.action); if (b.override) b.override = fix(b.override); }
    if (m.end_action) m.end_action = fix(m.end_action);
  }
  p.disc.title_key = fix(p.disc.title_key);
  for (const pl of p.playlists || []) {
    pl.end_action = fix(pl.end_action);
    if (kind === "title") pl.items = pl.items.map((it) => (it === oldId || it.startsWith(oldId + ":") ? newId + it.slice(oldId.length) : it));
  }
}
const mediaOf = (kind) => S.media.filter((m) => m.kind === kind).map((m) => m.path);
// ▲/▼ for the order of titles or menus (project order matters: play all, first menu)
const orderHtml = (hint) => `<div class="row" style="margin:10px 0 4px">
    <button class="small shrink" data-move="-1">▲ ${t("move_up")}</button>
    <button class="small shrink" data-move="1">▼ ${t("move_down")}</button></div><div class="hint">${esc(hint)}</div>`;
function bindOrder(el, listName, id) {
  el.querySelectorAll("[data-move]").forEach((b) => {
    const list = P()[listName] || [], i = list.findIndex((x) => x.id === id), j = i + Number(b.dataset.move);
    if (i < 0 || j < 0 || j >= list.length) { b.disabled = true; return; }
    b.onclick = () => commit((p) => { const l = p[listName]; [l[i], l[j]] = [l[j], l[i]]; });
  });
}

// ---------------------------------------------------------------- edits, undo, save
function commit(fn, { render = true } = {}) {
  S.undo.push(JSON.stringify(S.project));
  if (S.undo.length > 200) S.undo.shift();
  S.redo = [];
  fn(S.project);
  dropLostButtonLinks(S.project);
  S.preview = null;
  scheduleSave();
  if (render) renderAll();
}
// a link to a button that is gone (deleted, made text) opens its menu as usual
function dropLostButtonLinks(p) {
  const has = (mid, bid) => ((p.menus || []).find((m) => m.id === mid)?.buttons || []).some((b) => b.id === bid);
  const fix = (a) => {
    const m = /^menu:([^:]+):(.+)$/.exec(a || "");
    return m && !has(m[1], m[2]) ? `menu:${m[1]}` : a;
  };
  if (!p.disc) return;
  p.disc.first_play = fix(p.disc.first_play);
  if (p.disc.title_key) p.disc.title_key = fix(p.disc.title_key);
  for (const ti of p.titles || []) if (ti.end_action) ti.end_action = fix(ti.end_action);
  for (const pl of p.playlists || []) if (pl.end_action) pl.end_action = fix(pl.end_action);
  for (const m of p.menus || []) {
    if (m.end_action) m.end_action = fix(m.end_action);
    for (const b of m.buttons || []) { b.action = fix(b.action); if (b.override) b.override = fix(b.override); }
  }
}
function undo() {
  if (!S.undo.length) return;
  S.redo.push(JSON.stringify(S.project));
  S.project = JSON.parse(S.undo.pop());
  S.preview = null; scheduleSave(); renderAll();
}
function redo() {
  if (!S.redo.length) return;
  S.undo.push(JSON.stringify(S.project));
  S.project = JSON.parse(S.redo.pop());
  S.preview = null; scheduleSave(); renderAll();
}
function scheduleSave() {
  S.saveState = "unsaved"; renderTopbar();
  clearTimeout(S.saveTimer);
  S.saveTimer = setTimeout(save, 500);
}
async function save() {
  S.saveState = "saving"; renderTopbar();
  try {
    const r = await api("/api/project", { method: "PUT", body: { project: S.project } });
    S.check = r.check; S.saveState = "saved";
  } catch (e) { S.saveState = "error"; console.error(e); }
  renderTopbar(); renderStatus();
  refreshEncodeStatus();
}
// which titles are already transcoded (encoded into the cache ahead of the build)
function refreshEncodeStatus() {
  clearTimeout(S.encTimer);
  S.encTimer = setTimeout(async () => {
    if (!P() || S.check?.issues?.length) { S.encStatus = null; renderSidebar(); return; }
    try { S.encStatus = (await api("/api/encode_status", { method: "POST", body: { project: S.project } })).titles; }
    catch (e) { S.encStatus = null; }
    renderSidebar();
  }, 800);
}
async function transcode(ids) {
  clearTimeout(S.saveTimer); await save();
  let r;
  try { r = await api("/api/transcode", { method: "POST", body: { titles: ids || null } }); }
  catch (e) { alert(e.message); return; }
  followTranscode(r.job);
}
// (also after the page is opened again while one runs)
async function followTranscode(id) {
  S.transcoding = { id, next: 0, text: t("transcoding"), done: false };
  renderStatus();
  for (let misses = 0; ;) {
    let j;
    try { j = await api(`/api/jobs/${id}?since=${S.transcoding.next}`); misses = 0; }
    catch (e) {
      // gone (the app restarted): stop; not answering: try again for a while
      if (e.status === 404 || ++misses > JOB_MISSES) { S.transcoding.error = e.message; break; }
      await new Promise((res) => setTimeout(res, 1000));
      continue;
    }
    S.transcoding.next = j.next;
    for (const ev of j.events) {
      if (ev.event === "step" && ev.item) S.transcoding.text = `${t("transcoding")} ${ev.item}`;
      if (ev.event === "progress") S.transcoding.text = `${t("transcoding")} ${ev.item || ""} ${Math.round(ev.fraction * 100)}%`;
      if (ev.event === "error") S.transcoding.error = ev.message;
    }
    renderStatus();
    if (j.done) break;
    await new Promise((res) => setTimeout(res, 500));
  }
  S.transcoding.done = true;
  if (S.transcoding.error) alert(S.transcoding.error);
  S.transcoding = null;
  renderStatus(); refreshEncodeStatus();
}

async function refreshMedia() {
  try { S.media = (await api("/api/state")).media; } catch (e) { console.error(e); }
  renderSidebar();
}

// ---------------------------------------------------------------- rendering
function renderAll() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  renderMenubar(); renderTopbar(); renderToolbar(); renderWorkspaces(); renderLeft(); renderCenterHead(); renderMain();
  renderInspector(); renderTimeline(); renderStatus(); markFrame();
}
function renderTopbar() {
  const label = P()?.disc?.label || "";
  $("#disc-name").textContent = label;
  const st = $("#save-state");
  st.textContent = P() ? t({ saved: "saved", saving: "saving", unsaved: "unsaved", error: "save_error" }[S.saveState]) : "";
  st.className = "save-state" + (S.saveState === "error" ? " err" : "");
  // the window title names the project, with * while it has unsaved changes
  document.title = P() ? `${label}${S.saveState === "saved" ? "" : " *"} - oncemore` : "oncemore";
}
// The Tools panel under the menu bar: selection, text and zoom for the menu
// viewer, new button / rectangle, a menu from a Photoshop file, Preview.
function renderToolbar() {
  const bar = $("#tools"), onMenu = S.sel.view === "menu" && !!curMenu(), tool = S.tool || "select";
  const b = (attrs, title, icon, on = false, enabled = true) => `<button ${attrs} class="tool ${on ? "on" : ""}" title="${esc(title)}" ${enabled ? "" : "disabled"}>${icon}</button>`;
  bar.innerHTML = !P() ? "" : [
    b('data-tool="select"', `${t("tool_select")} (V)`, ICONS.select, tool === "select", onMenu),
    b('data-tool="rotate"', `${t("tool_rotate")} (R)`, ICONS.rotate, tool === "rotate", onMenu),
    b('data-tool="text" id="add-text"', `${t("tool_text")} (T)`, ICONS.text, tool === "text", onMenu),
    b('data-tool="zoom"', `${t("tool_zoom")} (Z)`, ICONS.zoom, tool === "zoom", onMenu),
    `<span class="sep"></span>`,
    b('id="add-btn"', t("add_button"), ICONS.button, false, onMenu),
    b('id="add-shape"', t("add_shape"), ICONS.rect, false, onMenu),
    b('id="add-picture"', t("add_picture"), ICONS.picture, false, onMenu),
    `<span class="sep"></span>`,
    b('id="tool-psd"', onMenu && curMenu().psd ? t("cmd_edit_psd") : t("tool_import_psd"), ICONS.psd),
    b('id="tool-preview"', `${t("cmd_preview")} (${keyLabel("shift+space")})`, ICONS.preview, false, (P().titles || []).length > 0),
  ].join("");
  bar.querySelectorAll("[data-tool]").forEach((x) => (x.onclick = () => setTool(x.dataset.tool)));
  const on = (id, fn) => { const x = $(id); if (x) x.onclick = fn; };
  on("#add-btn", addMenuButton);
  on("#add-shape", addMenuShape);
  on("#add-picture", pickMenuPicture);
  on("#tool-psd", () => (onMenu && curMenu().psd ? editPsd() : pickPsd()));
  on("#tool-preview", () => runCommand("preview"));
}
// small line icons for the tool buttons (drawn here; no images)
const svg = (d, extra = "") => `<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" ${extra}>${d}</svg>`;
const ICONS = {
  select: svg('<path d="M3 1.5v11.5l3-3 2 4.5 1.8-.8-2-4.4H12z" fill="currentColor"/>'),
  text: svg('<path d="M2.5 2.5h11v2.5h-1.3l-.4-1.2H9v8.7l1.4.4V14H5.6v-1.1l1.4-.4V3.8H4.2l-.4 1.2H2.5z" fill="currentColor"/>'),
  zoom: svg('<circle cx="6.5" cy="6.5" r="4.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M9.6 9.6l4.6 4.6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>'),
  rotate: svg('<path d="M12.6 8.6A4.8 4.8 0 1 1 10.8 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M9.2 1.6l3.6 1.9-2.6 3.1z" fill="currentColor"/>'),
  button: svg('<rect x="1.5" y="4" width="13" height="8" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5 8h6" stroke="currentColor" stroke-width="1.4"/>'),
  rect: svg('<rect x="2" y="3" width="12" height="10" fill="currentColor"/>'),
  picture: svg('<rect x="2" y="3" width="12" height="10" rx="1"/><path d="M3 12l3.5-4 2.5 3 1.5-1.5L13 12"/><circle cx="10.5" cy="6" r="1"/>'),
  psd: svg('<rect x="1.5" y="1.5" width="13" height="13" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M4 4.5h8M4 7.5h8M4 10.5h5" stroke="currentColor" stroke-width="1.3"/>'),
  preview: svg('<circle cx="8" cy="8" r="6.3" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="1.4" fill="currentColor"/><path d="M11 10.5l4 2.3-4 2.2z" fill="currentColor"/>'),
  import: svg('<path d="M8 1.5v8M4.5 6l3.5 3.5L11.5 6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 11v3h12v-3" fill="none" stroke="currentColor" stroke-width="1.5"/>'),
  slideshow: svg('<rect x="1.5" y="3" width="13" height="10" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M4 11l3-3.5 2 2 1.5-1.5 2 3z" fill="currentColor"/><circle cx="11" cy="6" r="1" fill="currentColor"/>'),
  menu: svg('<rect x="1.5" y="2.5" width="13" height="11" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M4 6h3M4 8.5h3M4 11h3M9 5.5h3.5v3H9z" fill="currentColor" stroke="currentColor" stroke-width=".8"/>'),
  playlist: svg('<path d="M2 3.5h9M2 7h9M2 10.5h6" stroke="currentColor" stroke-width="1.5"/><path d="M10 9.5l4.5 2.5-4.5 2.5z" fill="currentColor"/>'),
  trash: svg('<path d="M3 4.5h10M6 4.5V3h4v1.5M4.5 4.5l.7 9.5h5.6l.7-9.5" fill="none" stroke="currentColor" stroke-width="1.3"/>'),
  timeline: svg('<rect x="1.5" y="3" width="13" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M1.5 6h13M4 3v3M7 3v3M10 3v3M13 3v3" stroke="currentColor"/>'),
  disc: svg('<circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="1.8" fill="none" stroke="currentColor" stroke-width="1.2"/>'),
  video: svg('<rect x="1.5" y="3.5" width="9" height="9" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M10.5 7l4-2.5v7l-4-2.5z" fill="currentColor"/>'),
  audio: svg('<path d="M2 6h3l4-3v10l-4-3H2z" fill="currentColor"/><path d="M11 5.5a3.5 3.5 0 010 5M12.8 3.8a6 6 0 010 8.4" fill="none" stroke="currentColor" stroke-width="1.2"/>'),
  image: svg('<rect x="1.5" y="2.5" width="13" height="11" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M3.5 11.5l3.5-4 2.5 2.5 1.5-1.5 2 3z" fill="currentColor"/>'),
  safe: svg('<rect x="1.5" y="2.5" width="13" height="11" fill="none" stroke="currentColor" stroke-width="1.2"/><rect x="4" y="5" width="8" height="6" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="1.5 1"/>'),
  play: svg('<path d="M4.5 2.5l9 5.5-9 5.5z" fill="currentColor"/>'),
  pause: svg('<path d="M4 2.5h3v11H4zM9 2.5h3v11H9z" fill="currentColor"/>'),
  stepb: svg('<path d="M3 3h2v10H3zM13 3v10L6 8z" fill="currentColor"/>'),
  stepf: svg('<path d="M11 3h2v10h-2zM3 3v10l7-5z" fill="currentColor"/>'),
  prevch: svg('<path d="M3 2v12M3 3h4" stroke="currentColor" stroke-width="1.4" fill="none"/><path d="M13 5v6L8 8z" fill="currentColor"/>'),
  nextch: svg('<path d="M13 2v12M13 3H9" stroke="currentColor" stroke-width="1.4" fill="none"/><path d="M3 5v6l5-3z" fill="currentColor"/>'),
  addch: svg('<path d="M4 2v12M4 3h5l-1.5 2L9 7H4" stroke="currentColor" stroke-width="1.3" fill="none"/><path d="M11 9v5M8.5 11.5h5" stroke="currentColor" stroke-width="1.5"/>'),
  eye: svg('<path d="M1 8s2.6-4.5 7-4.5S15 8 15 8s-2.6 4.5-7 4.5S1 8 1 8z" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="2.2" fill="currentColor"/>'),
  eyeOff: svg('<path d="M1 8s2.6-4.5 7-4.5S15 8 15 8s-2.6 4.5-7 4.5S1 8 1 8z" fill="none" stroke="currentColor" stroke-width="1.3" opacity=".45"/><path d="M2.5 13.5l11-11" stroke="currentColor" stroke-width="1.4"/>'),
  mtnS: svg('<path d="M3 12l3-4 2 2 2-3 3 5z" fill="currentColor"/>'),
  mtnL: svg('<path d="M0.5 14l4.5-7 3 3.5 3-5 4.5 8.5z" fill="currentColor"/>'),
  panel: svg('<path d="M3 5l2.5 3L8 5z" fill="currentColor"/><path d="M9.5 4.5h4M9.5 7.5h4M9.5 10.5h4" stroke="currentColor" stroke-width="1.3"/>', 'width="18" height="14"'),
};
// the panel being worked in gets an amber outline
function markFrame() {
  document.querySelectorAll("[data-frame]").forEach((f) => f.classList.toggle("active-frame", f.dataset.frame === S.activeFrame));
}
document.addEventListener("pointerdown", (ev) => {
  const f = ev.target.closest?.("[data-frame]");
  if (f && S.activeFrame !== f.dataset.frame) { S.activeFrame = f.dataset.frame; markFrame(); }
}, true);
function renderStatus() {
  const bar = $("#statusbar");
  if (!P()) { bar.textContent = S.dir; return; }
  const issues = S.check?.issues || [];
  const tl = S.tools, miss = [];
  if (!tl.ffmpeg) miss.push("ffmpeg"); else if (tl.drawtext === false) miss.push("drawtext");
  if (!tl.iso) miss.push("ISO");
  bar.innerHTML = `<span class="${issues.length ? "err" : "ok"}" id="st-issues">${issues.length ? "⚠ " + t("issues", { n: issues.length }) : "✓ " + t("no_issues")}</span>
    ${miss.length ? `<span class="warn">${esc(t("tools_missing", { t: miss.join(", ") }))} — <span class="mono">${esc(tl.install || "")}</span></span>` : ""}
    ${S.transcoding ? `<span class="busy" id="st-transcode">${esc(S.transcoding.text)}</span>` : ""}
    <span class="spacer"></span><span class="mono">${esc(S.dir)}</span>`;
  $("#st-issues").onclick = () => issues.length && showIssues(issues);
}
function showIssues(issues, title) {
  const have = new Set(S.media.map((m) => m.path)), missing = P() ? [...assetRefs().keys()].filter((r) => !have.has(r)) : [];
  openModal(`<h2>${esc(title || t("issues", { n: issues.length }))}</h2><ul class="issues">${issues.map((i) =>
    `<li>${i.path ? `<span class="path">${esc(i.path)}</span><br>` : ""}${esc(i.message)}</li>`).join("")}</ul>
    ${missing.length ? `<div class="dlg-buttons"><span class="spacer"></span><button id="issues-replace">${t("cmd_replace_asset")}</button></div>` : ""}`);
  const b = $("#issues-replace");
  if (b) b.onclick = () => replaceAssetBox(missing[0]);
}
function openModal(html) { $("#modal-body").innerHTML = html; $("#modal").hidden = false; }
function closeModal() { $("#modal").hidden = true; }

// The Project frame: Project (every element and asset in one list with its
// type, length and state), Menus (menus and their buttons) and Timelines
// (titles with their chapters and encode state).
function renderSidebar() {
  const sb = $("#sidebar");
  if (!P()) { sb.innerHTML = ""; return; }
  const tab = S.leftTab || "project";
  if (tab === "build") return renderBuild(sb);
  if (tab === "menus") return renderMenusPanel(sb);
  if (tab === "timelines") return renderTimelinesPanel(sb);
  const v = S.sel;
  const enc = (id) => (S.encStatus && id in S.encStatus ? `<span class="enc ${S.encStatus[id] ? "ok" : ""}" title="${esc(t(S.encStatus[id] ? "transcoded" : "not_transcoded"))}"></span>` : `<span class="enc none"></span>`);
  const q = (S.search || "").toLowerCase(), hit = (...xs) => !q || xs.some((x) => String(x || "").toLowerCase().includes(q));
  const row = (view, id, ico, label, type, len, mark = "", extra = "") => !hit(label, id, type) ? "" :
    `<div class="nav-item prow ${v.view === view && v.id === id ? "active" : ""}" data-view="${view}" data-id="${esc(id || "")}" ${extra}>
      <span class="c-name"><span class="ico k-${view}">${ICONS[ico] || ico}</span>${mark}${esc(label)}</span><span class="c-type">${esc(type)}</span><span class="c-len">${esc(len)}</span></div>`;
  const len = (path) => { const pr = path && S.probes[path]; return pr && pr.duration ? fmtTime(pr.duration, false) : ""; };
  const titles = (P().titles || []).map((ti) => row("title", ti.id, ti.slideshow ? "slideshow" : "timeline", ti.name || ti.id,
    t(ti.slideshow ? "slideshow" : ti.clips ? "type_clips" : "type_timeline"), len(ti.source), enc(ti.id))).join("");
  const menus = (P().menus || []).map((m) => row("menu", m.id, "menu", m.id, t("menu"), t("n_buttons", { n: (m.buttons || []).length }))).join("");
  const gen = generatedMenus().map((g) => row("menu", g.id, "menu", g.id, t("type_chapter_menu"), "")).join("");
  const pls = (P().playlists || []).map((pl) => row("playlist", pl.id, "playlist", pl.name || pl.id, t("playlist"), t("n_items", { n: pl.items.length }))).join("");
  const media = S.media.filter((m) => hit(m.path, t("kind_" + m.kind))).map((m) => `<div class="media-item prow ${S.selectedMedia === m.path ? "selected" : ""}" data-media="${esc(m.path)}" draggable="false">
      <span class="c-name"><span class="ico">${{ video: ICONS.video, audio: ICONS.audio, image: ICONS.image, subtitle: "≣", design: ICONS.psd, font: "Aa" }[m.kind] || "·"}</span><span class="name" title="${esc(m.path)}">${esc(m.path.replace(/^media\//, ""))}</span></span>
      <span class="c-type">${esc(t("kind_" + m.kind))}</span><span class="c-len">${len(m.kind === "video" || m.kind === "audio" ? m.path : null) || fmtBytes(m.bytes)}</span></div>`).join("");
  const ups = Object.entries(S.uploads).map(([n, pct]) => `<div class="media-item prow"><span class="c-name"><span class="name">${esc(n)}</span></span><span class="c-type">${t("importing")}</span><span class="c-len">${pct}%</span></div>`).join("");
  const sel = (P().titles || []).find((x) => v.view === "title" && x.id === v.id);
  const prev = S.selectedMedia ? S.media.find((m) => m.path === S.selectedMedia) : null;
  const selMenu = v.view === "menu" ? (P().menus || []).find((x) => x.id === v.id) : null;
  const thumbPath = prev ? (prev.kind === "image" ? imgUrl("file", { path: prev.path }) : prev.kind === "video" ? imgUrl("frame", { path: prev.path, t: 1, w: 160 }) : "")
    : sel && sel.source && !sel.slideshow ? imgUrl("frame", { path: sel.source, t: 1, w: 160 })
    : selMenu && selMenu.background ? imgUrl("file", { path: selMenu.background })
    : selMenu && selMenu.background_video ? imgUrl("frame", { path: selMenu.background_video, t: 0, w: 160 }) : "";
  const name = prev ? prev.path.replace(/^media\//, "") : v.view === "disc" ? P().disc.label : sel ? sel.name || sel.id : (v.id || P().disc.label);
  const count = (P().titles || []).length + (P().menus || []).length + (P().playlists || []).length + S.media.length;
  const durOf = sel && !sel.slideshow ? len(sel.source) : prev ? len(prev.kind === "video" || prev.kind === "audio" ? prev.path : null) : "";
  const pi = prev ? S.probes[prev.path] : sel ? S.probes[sel.source] : null;
  const dims = pi && pi.width ? `${pi.width}×${pi.height}` : "";
  sb.innerHTML = `
    <div class="proj-preview nav-item ${v.view === "disc" && !prev ? "active" : ""}" data-view="disc" data-id="" title="${esc(t("prop_disc"))}">
      <span class="disclose" aria-hidden="true">▾</span>
      <div class="thumb">${thumbPath ? `<img src="${thumbPath}" alt="">` : `<div class="ph">${ICONS.disc}</div>`}<span class="tplay" aria-hidden="true">${ICONS.play}</span></div>
      <div class="info"><b>${esc(name)}</b><span>${esc(prev ? t("kind_" + prev.kind) : t(v.view === "title" ? "type_timeline" : v.view === "menu" ? "menu" : v.view === "playlist" ? "playlist" : "disc"))}${dims ? ", " + dims : ""}</span>
      <span>${esc(durOf || t("n_items", { n: count }))}</span></div></div>
    <div class="proj-table" role="grid">
      <div class="prow phead"><span class="c-name">${t("col_name")}</span><span class="c-type">${t("col_type")}</span><span class="c-len">${t("col_duration")}</span></div>
      ${titles}${pls}${menus}${gen}${media}${ups}
      ${count ? "" : `<div class="hint" style="padding:8px">${esc(t("no_titles"))}</div>`}
    </div>
    <div class="panel-foot">
      <button class="ficon" id="dropzone" title="${esc(t("add_files"))}">${ICONS.import}</button>
      <button class="ficon" id="add-slideshow" title="${esc(t("add_slideshow"))} — ${esc(t("slideshow_hint"))}">${ICONS.slideshow}</button>
      <button class="ficon" id="add-menu" title="${esc(t("add_menu_short"))}">${ICONS.menu}</button>
      <button class="ficon" id="add-playlist" title="${esc(t("add_playlist_short"))}">${ICONS.playlist}</button>
      <span class="spacer"></span>
      <button class="ficon" id="trash" title="${esc(t("delete_item"))}" ${LISTS[v.view] && v.id && editing() ? "" : "disabled"}>${ICONS.trash}</button>
    </div>`;
  sb.querySelectorAll(".nav-item").forEach((el) => (el.onclick = () => select(el.dataset.view, el.dataset.id)));
  bindLinkSources(sb);
  sb.querySelectorAll(".media-item[data-media]").forEach((el) => (el.onclick = () => { S.selectedMedia = el.dataset.media; S.element = null; renderSidebar(); renderInspector(); }));
  $("#add-menu").onclick = addMenu;
  $("#add-playlist").onclick = addPlaylist;
  $("#add-slideshow").onclick = addSlideshow;
  $("#dropzone").onclick = pickFiles;
  $("#trash").onclick = () => runCommand("delete");
  // durations of titles and media fill in as they are probed
  const want = [...(P().titles || []).filter((x) => x.source && !x.slideshow).map((x) => x.source), ...S.media.filter((m) => m.kind === "video" || m.kind === "audio").map((m) => m.path)]
    .filter((x) => !S.probes[x]);
  if (want.length && !S.probing) {
    S.probing = true;
    Promise.all(want.slice(0, 12).map(probe)).finally(() => { S.probing = false; if ((S.leftTab || "project") === "project") renderSidebar(); });
  }
}
function renderMenusPanel(sb) {
  const v = S.sel, menus = [...(P().menus || []).map((m) => ({ id: m.id, n: (m.buttons || []).length, gen: false })), ...generatedMenus().map((g) => ({ id: g.id, n: null, gen: true }))];
  const cur = v.view === "menu" ? curMenu() : null;
  sb.innerHTML = `<div class="proj-table">
      <div class="prow phead"><span class="c-name">${t("col_name")}</span><span class="c-type">${t("col_buttons")}</span><span class="c-len">${t("col_first")}</span></div>
      ${menus.map((m) => `<div class="nav-item prow ${v.view === "menu" && v.id === m.id ? "active" : ""}" data-view="menu" data-id="${esc(m.id)}">
        <span class="c-name"><span class="ico k-menu">${ICONS.menu}</span>${esc(m.id)}</span><span class="c-type">${m.gen ? t("generated") : m.n}</span><span class="c-len">${P().disc.first_play === "menu:" + m.id ? "◉" : ""}</span></div>`).join("")}
    </div>
    ${cur ? `<div class="sub-head">${esc(t("buttons_of", { m: cur.id }))}</div><div class="proj-table">
      ${cur.buttons.map((b, i) => `<div class="prow brow ${S.element?.kind === "button" && S.element.i === i ? "selected" : ""}" data-bi="${i}">
        <span class="c-name"><span class="ico">${i + 1}</span>${esc(b.label || b.id)}</span><span class="c-type">${esc(linkName(b.action))}</span><span class="c-len"></span></div>`).join("")}</div>` : ""}
    <div class="panel-foot"><button class="icon-text" id="add-menu">${t("add_menu_short")}</button></div>`;
  sb.querySelectorAll(".nav-item").forEach((el) => (el.onclick = () => select("menu", el.dataset.id)));
  bindLinkSources(sb);
  sb.querySelectorAll(".brow").forEach((r) => (r.onclick = () => {
    const b = cur.buttons[Number(r.dataset.bi)];
    if (b.page && b.page !== curPage(cur)) (S.pages = S.pages || {})[cur.id] = b.page;
    S.element = { kind: "button", i: Number(r.dataset.bi) }; S.sels = [S.element]; renderMain(); renderInspector(); renderSidebar(); renderLayers();
  }));
  $("#add-menu").onclick = addMenu;
}
function renderTimelinesPanel(sb) {
  const v = S.sel, ts = P().titles || [];
  const cur = v.view === "title" ? curTitle() : null;
  sb.innerHTML = `<div class="proj-table">
      <div class="prow phead"><span class="c-name">${t("col_name")}</span><span class="c-type">${t("col_chapters")}</span><span class="c-len">${t("col_transcode")}</span></div>
      ${ts.map((ti) => `<div class="nav-item prow ${v.view === "title" && v.id === ti.id ? "active" : ""}" data-view="title" data-id="${esc(ti.id)}">
        <span class="c-name"><span class="ico k-title">${ICONS.timeline}</span>${esc(ti.name || ti.id)}</span><span class="c-type">${chaptersOf(ti).length}</span>
        <span class="c-len">${ti.transcode === false ? t("status_no_transcode") : S.encStatus && ti.id in S.encStatus ? t(S.encStatus[ti.id] ? "status_transcoded" : "status_untranscoded") : ""}</span></div>`).join("")}
    </div>
    ${cur ? `<div class="sub-head">${esc(t("chapters_of", { t: cur.name || cur.id }))}</div><div class="proj-table">
      ${chapterEntries(cur).map((c, i) => `<div class="prow crow" data-ct="${c.time}"><span class="c-name"><span class="ico k-chapter">◆</span>${i + 1}${c.name ? " · " + esc(c.name) : ""}</span><span class="c-type mono">${fmtTime(c.time)}</span><span class="c-len"></span></div>`).join("")}</div>` : ""}
    <div class="panel-foot"><button class="icon-text" id="add-slideshow">${t("add_slideshow")}</button></div>`;
  sb.querySelectorAll(".nav-item").forEach((el) => (el.onclick = () => select("title", el.dataset.id)));
  bindLinkSources(sb);
  sb.querySelectorAll(".crow").forEach((r) => (r.onclick = () => S.titleSeek && S.titleSeek(Number(r.dataset.ct))));
  $("#add-slideshow").onclick = addSlideshow;
}
const linkName = (a) => {
  if (!a) return "";
  const [k, id, n] = a.split(":");
  if (k === "title") return "▶ " + id;
  if (k === "chapter") return `▶ ${id} ◆${n}`;
  if (k === "menu") return "▦ " + id + (n ? ` › ${n}` : "");
  if (k === "playlist") return "≡ " + id;
  if (k === "page") return "⇥ " + pageName(id);
  return a;
};
// -- pages: a menu with pages (menus[].pages) shows one page at a time in the
// viewer; its objects with a page are on that page only, the rest on every
// page. On the disc each page is a menu of its own, <id>~<n> after the first.
const pagesOf = (menu) => Math.max(1, Number(menu?.pages) || 1);
const curPage = (menu) => Math.min(pagesOf(menu), (S.pages || {})[menu?.id] || 1);
const onPage = (menu, x) => pagesOf(menu) === 1 || !x.page || x.page === curPage(menu);
const pageId = (menu) => (curPage(menu) > 1 ? `${menu.id}~${curPage(menu)}` : menu.id);
const newOnPage = (menu) => (pagesOf(menu) > 1 ? { page: curPage(menu) } : {});
const pageName = (n) => (n === "next" ? t("page_next") : n === "prev" ? t("page_prev") : t("page_item", { n }));
function showPage(menu, n) {
  (S.pages = S.pages || {})[menu.id] = n;
  S.element = null; S.sels = []; S.preview = null;
  renderMain(); renderInspector(); renderLayers();
}
// Menu > Add New Page: the page after the last, with a button back to the one
// before (and a NEXT button there if it has no way on). The first time, the
// menu's buttons become page 1's; its texts, rectangles and pictures stay on
// every page.
function addPage() {
  const menu = curMenu();
  if (!menu) return;
  const n = pagesOf(menu) + 1;
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    if (n === 2) for (const b of mm.buttons) if (!b.page) b.page = 1;
    mm.pages = n;
    const ids = () => mm.buttons.map((b) => b.id);
    const prev = mm.buttons.filter((b) => !b.page || b.page === n - 1);
    if (!prev.some((b) => b.action === "page:next"))
      mm.buttons.push({ id: uniqueId("next", ids()), label: "NEXT", x: 560, y: Math.min(discH() - 40, Math.round(discH() * 0.85)), action: "page:next", page: n - 1 });
    mm.buttons.push({ id: uniqueId("back", ids()), label: "BACK", x: 80, y: Math.round(discH() * 0.85), action: "page:prev", page: n });
  });
  showPage(curMenu(), n);
}
// Menu > Delete Page: the page shown and what is on it alone; the pages after
// it move up one, and so do the page links to them
function deletePage() {
  const menu = curMenu();
  if (!menu || pagesOf(menu) < 2) return;
  const pg = curPage(menu), n = pagesOf(menu) - 1;
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    for (const k of ["buttons", "texts", "shapes", "images"]) {
      if (!mm[k]) continue;
      mm[k] = mm[k].filter((x) => x.page !== pg);
      for (const x of mm[k]) if (x.page > pg) x.page -= 1;
    }
    for (const b of mm.buttons) {
      const m = /^page:(\d+)$/.exec(b.action);
      if (m && Number(m[1]) >= pg) b.action = Number(m[1]) === pg ? "page:prev" : `page:${Number(m[1]) - 1}`;
    }
    if (n === 1) {
      // one page left: no pages, no page links
      delete mm.pages;
      for (const k of ["buttons", "texts", "shapes", "images"]) for (const x of mm[k] || []) delete x.page;
      const rest = mm.buttons.filter((b) => !b.action.startsWith("page:"));
      if (rest.length) mm.buttons = rest; else for (const b of mm.buttons) b.action = "stop";
    } else mm.pages = n;
    if (!mm.buttons.length) mm.buttons.push({ id: "button1", label: "BUTTON", x: 80, y: 200, action: "stop" });
    if (mm.default_button && !mm.buttons.some((b) => b.id === mm.default_button)) delete mm.default_button;
    for (const b of mm.buttons) if (b.nav) for (const [d, v] of Object.entries(b.nav)) if (!mm.buttons.some((x) => x.id === v)) delete b.nav[d];
    dropLostButtonLinks(p);
  });
  showPage(curMenu(), Math.max(1, Math.min(pg, n)));
}
// the page an object is on (Properties): one page, or every page
function pageHtml(menu, it) {
  if (pagesOf(menu) < 2) return "";
  return `<label class="field" data-nobind><span>${t("page_field")}</span>${selectHtml("obj-page", [["0", t("page_all")], ...Array.from({ length: pagesOf(menu) }, (_, i) => [String(i + 1), t("page_item", { n: i + 1 })])], String(it.page || 0), 'id="obj-page"')}<div class="hint">${esc(t("page_hint"))}</div></label>`;
}
function bindPage(el, get) {
  const f = el.querySelector("#obj-page");
  if (!f) return;
  f.onchange = () => {
    const v = Number(f.value);
    commit((p) => { const o = get(p); if (v) o.page = v; else delete o.page; });
    if (v && v !== curPage(curMenu())) showPage(curMenu(), v);
  };
}
function select(view, id) {
  if (view === "build") {                       // Build is a panel in the Project frame
    S.leftTab = "build";
    if (S.sel.view === "sim") S.sel = S.lastAuthor || { view: "disc" };
    renderAll(); return;
  }
  if (view === "menu" && /~\d+$/.test(id || "")) {        // a page of a menu (flowchart)
    const [base, n] = id.split("~");
    (S.pages = S.pages || {})[base] = Number(n);
    id = base;
  }
  S.sel = { view, id }; S.element = null; S.selectedMedia = null; S.preview = null;
  if (workspaceOf(view) === "author") S.lastAuthor = { view, id };
  if (view === "title") S.lastTitle = id;
  if (view === "menu") S.lastMenu = id;
  if (view === "playlist") S.lastPlaylist = id;
  renderAll();
}

// redraw the Monitor once something it waited for has loaded, but never
// under the user's typing: with a field there focused, it waits for the blur
// (an edit committed meanwhile redraws it anyway)
function renderMainLater() {
  const a = document.activeElement, m = $("#main");
  if (a && m && m.contains(a) && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) {
    a.addEventListener("blur", () => setTimeout(() => { if (a.isConnected) renderMainLater(); }, 0), { once: true });
    return;
  }
  renderMain();
}
function renderMain() {
  const m = $("#main");
  postMenuSpec();                                       // (what the Mac app's menus can do now)
  if (S.sel.view !== "title") S.titleSeek = null;      // (the Monitor is not showing a timeline)
  renderPreviewWindow();
  if (!P()) return renderWelcome(m);
  const v = S.sel.view;
  if (v === "title") return renderTitle(m);
  if (v === "menu") return renderMenu(m);
  if (v === "playlist") return renderPlaylist(m);
  if (v === "flow") return renderFlow(m);
  return renderMonitorEmpty(m);
}
// the Monitor with nothing open in it
function renderMonitorEmpty(m) {
  m.innerHTML = `<div class="monitor empty"><div class="monitor-screen"><span class="hint">${esc(t("no_timeline_open"))}</span></div>
    <div class="monitor-bar"><select disabled class="shrink"><option>${esc(t("fit"))}</option></select><span class="spacer"></span><span class="tc-amber">00:00:00.000</span></div></div>`;
}
// File > Preview: the disc played with a remote, in a window of its own
function renderPreviewWindow() {
  const w = $("#pv-window"), body = $("#pv-body"), open = !!P() && S.sel.view === "sim";
  w.hidden = !open;
  if (!open) { if (body.childElementCount) body.innerHTML = ""; return; }
  $("#pv-title").textContent = t("project_preview");
  $("#pv-close").title = t("preview_close");
  $("#pv-close").onclick = () => { const last = S.lastAuthor || { view: "disc" }; select(last.view, last.id); };
  renderSim(body);
}
function renderInspector() {
  postMenuSpec();
  $("#right-head").innerHTML = tabStrip([["props", t("properties")]], "props", "data-rt");
  renderLayers();
  const el = $("#inspector");
  if (!P()) { el.innerHTML = ""; return; }
  if (S.selectedMedia) return renderMediaInspector(el);
  const v = S.sel.view;
  if (v === "title") return renderTitleInspector(el);
  if (v === "menu") return renderMenuInspector(el);
  if (v === "playlist") { el.innerHTML = `<h2>${t("playlist")}</h2><div class="hint">${esc(t("playlist_hint"))}</div>`; return; }
  if (v === "flow") { el.innerHTML = `<h2>${t("flowchart")}</h2><div class="hint">${esc(t("flow_hint"))}</div>`; return; }
  if (v === "sim") { el.innerHTML = `<h2>${t("project_preview")}</h2><div class="hint">${esc(t("sim_hint"))}</div>`; return; }
  return renderDisc(el);
}
function renderToolsInfo(el) {
  el.insertAdjacentHTML("beforeend", `<h3>${t("tools")}</h3>
    <div class="hint">ffmpeg: ${S.tools.ffmpeg ? t("ok") : t("missing")}<br>drawtext: ${S.tools.drawtext ? t("ok") : t("missing")}<br>
    ISO: ${esc(S.tools.iso || t("missing"))}</div>
    <h3>oncemore</h3><div class="hint">${esc(t("disc_tips"))}</div>`);
}

// generic binding: inputs with data-k="path.to.key" inside root update obj
function bindFields(root, getTarget, { numeric = [], onAfter } = {}) {
  root.querySelectorAll("[data-k]").forEach((el) => {
    if (el.closest("[data-nobind]")) return;   // rows with their own handlers
    el.addEventListener("change", () => {
      const key = el.dataset.k;
      let val = el.type === "checkbox" ? el.checked : el.value;
      if (numeric.includes(key)) val = val === "" ? undefined : Number(val);
      commit((p) => {
        const target = getTarget(p);
        const path = key.split(".");
        let o = target;
        for (const k of path.slice(0, -1)) o = o[k] = o[k] || {};
        const last = path[path.length - 1];
        if (val === undefined || val === "" || val === "__none__") delete o[last];
        else o[last] = val;
        onAfter && onAfter(p, key, val);
      });
    });
  });
}

// ---------------------------------------------------------------- welcome
function renderWelcome(m) {
  // File > New Project, over the empty workspace
  const tx = () => {
    const pal = $("#np-std")?.value === "PAL";
    return t("np_transcode", { d: pal ? "720 × 576" : "720 × 480", f: pal ? "25" : "29.97" });
  };
  m.innerHTML = `<div class="welcome"><div class="dialog np-dialog" role="dialog" aria-label="${esc(t("new_project"))}">
    <div class="np-brand"><img src="brand-lockup.svg" alt="oncemore"></div>
    <div class="dlg-title">${esc(t("new_project"))}</div>
    <div class="dlg-body">
      <div class="dlg-tabs"><span class="tab active">${t("basic")}</span></div>
      <div class="dlg-page">
        <fieldset class="group"><legend>${t("name_location")}</legend>
          <label class="frow"><span class="fl">${t("name")}:</span><input id="np-label" value="MY_DISC"></label>
          <div class="frow"><span class="fl">${t("location")}:</span><input class="mono" readonly value="${esc(S.dir)}" title="${esc(S.dir)}"></div>
        </fieldset>
        <fieldset class="group"><legend>${t("project_settings")}</legend>
          <div class="frow"><span class="fl">${t("authoring_mode")}:</span><label><input type="radio" name="np-mode" checked> DVD</label></div>
          <label class="frow"><span class="fl">${t("standard")}:</span><select id="np-std" class="shrink"><option>NTSC</option><option>PAL</option></select></label>
          <label class="frow"><span class="fl">${t("aspect")}:</span><select id="np-aspect" class="shrink"><option>16:9</option><option>4:3</option></select></label>
          <div class="frow top"><span class="fl">${t("transcode_settings")}:</span><span class="np-tx" id="np-tx"></span></div>
        </fieldset>
        <div class="np-info"><span class="i" aria-hidden="true">i</span><span>${esc(t("np_info"))}</span></div>
      </div>
      <div class="dlg-buttons"><button id="np-sample">${t("np_open_sample")}</button><span class="spacer"></span><button id="np-empty" class="primary">OK</button></div>
    </div></div></div>`;
  $("#np-tx").textContent = tx();
  $("#np-std").onchange = () => { $("#np-tx").textContent = tx(); };
  const go = async (sample) => {
    const r = await api("/api/new", { method: "POST", body: { sample, label: $("#np-label").value, standard: $("#np-std").value, aspect: $("#np-aspect").value } });
    applyState(r); S.sel = { view: "disc" }; renderAll(); refreshEncodeStatus();
  };
  $("#np-empty").onclick = () => go(false);
  $("#np-sample").onclick = () => go(true);
}

// ---------------------------------------------------------------- disc
// a frame of what a thumbnail button plays (its title's source, else nothing)
function thumbSrc(b) {
  const [kind, tid, n] = (b.action || "").split(":");
  const ti = (P().titles || []).find((x) => x.id === tid);
  if (!ti || !ti.source || ti.slideshow || !/^(title|chapter)$/.test(kind)) return "";
  const start = kind === "chapter" ? chaptersOf(ti)[Number(n) - 1] || 0 : 0;
  return imgUrl("frame", { path: ti.source, t: start + (b.thumbnail.time ?? 1), w: 240 });
}

function renderDisc(m) {
  const d = P().disc, ss = d.subtitle_style || {}, pal = d.standard === "PAL";
  const fp = actionOptions({ forButton: false, allowStop: false, includeChapters: false, allowPlayAll: true });
  m.innerHTML = `<h2>${t("prop_disc")}</h2><div class="card">
    <label class="field"><span>${t("label")}</span><input data-k="label" value="${esc(d.label)}"></label>
    <div class="grid2">
      <label class="field"><span>${t("standard")}</span>${selectHtml("standard", [["NTSC", "NTSC (720×480, 29.97)"], ["PAL", "PAL (720×576, 25)"]], d.standard)}</label>
      <label class="field"><span>${t("aspect")}</span>${selectHtml("aspect", [["16:9", "16:9"], ["4:3", "4:3"]], d.aspect)}</label>
      <label class="field"><span>${t("target")}</span>${selectHtml("target", [["DVD5", "DVD-5 (4.7 GB)"], ["DVD9", "DVD-9 (8.5 GB)"]], d.target || "DVD5")}</label>
      <label class="field"><span>${t("video_bitrate")}</span>${selectHtml("video_bitrate", [["auto", t("auto")], ["4M", "4 Mbit/s"], ["5M", "5 Mbit/s"], ["6M", "6 Mbit/s"], ["7M", "7 Mbit/s"], ["8M", "8 Mbit/s"]], d.video_bitrate || "auto")}</label>
    </div>
    ${d.target === "DVD9" ? `<label class="field"><span>${t("layer_break")}</span>${selectHtml("layer_break", [["__none__", t("auto")], ...(P().titles || []).flatMap((ti) => chaptersOf(ti).map((_, k) => [`${ti.id}:${k + 1}`, t("layer_break_at", { t: ti.name || ti.id, n: k + 1 })]))], d.layer_break || "__none__")}<div class="hint">${esc(t("layer_break_hint"))}</div></label>` : ""}
    <label class="field"><span>${t("first_play")} ${whipHtml("first_play")}</span>${selectHtml("first_play", [["__none__", t("auto")], ...fp], d.first_play || "__none__")}</label>
    <label class="field"><span>${t("title_key")}</span>${selectHtml("title_key", [["__none__", t("first_menu")], ...fp], d.title_key || "__none__")}</label>
    <label class="field" data-nobind><span>${t("rom_files")}</span><textarea id="rom-files" rows="3" placeholder="extras/">${esc((d.rom_files || []).join("\n"))}</textarea><div class="hint">${esc(t("rom_hint"))}</div></label>
    <h3>${t("sub_style")}</h3>
    <div class="grid2">
      <label class="field"><span>${t("size")}</span><input type="number" data-k="subtitle_style.size" min="12" max="80" value="${ss.size ?? ""}" placeholder="${pal ? 36 : 30}"></label>
      <label class="field"><span>${t("sub_margin")}</span><input type="number" data-k="subtitle_style.margin" min="0" max="200" value="${ss.margin ?? ""}" placeholder="${pal ? 43 : 36}"></label>
      <label class="field"><span>${t("color")}</span><input type="color" data-k="subtitle_style.color" value="${esc((ss.color || "#FFFFFF").slice(0, 7))}"></label>
      <label class="field"><span>${t("outline")}</span><input type="color" data-k="subtitle_style.outline" value="${esc((ss.outline || "#000000").slice(0, 7))}"></label>
      <label class="field"><span>${t("outline_w")}</span><input type="number" data-k="subtitle_style.outline_width" min="0" max="8" value="${ss.outline_width ?? ""}" placeholder="3"></label>
    </div>
  </div>`;
  renderToolsInfo(m);
  bindFields(m, (p) => p.disc, {
    numeric: ["subtitle_style.size", "subtitle_style.margin", "subtitle_style.outline_width"],
    onAfter: (p, key, val) => {
      const st = p.disc.subtitle_style;
      if (st && (key.endsWith(".color") || key.endsWith(".outline"))) st[key.split(".")[1]] = val.toUpperCase();
      if (st && !Object.keys(st).length) delete p.disc.subtitle_style;
    },
  });
  $("#rom-files").onchange = (e) => commit((p) => {
    const list = e.target.value.split("\n").map((x) => x.trim()).filter(Boolean);
    if (list.length) p.disc.rom_files = list; else delete p.disc.rom_files;
  });
}

// ---------------------------------------------------------------- titles
async function probe(path) {
  if (!path) return null;
  if (!S.probes[path]) {
    try { S.probes[path] = await api("/api/probe?" + new URLSearchParams({ path })); }
    catch (e) { S.probes[path] = { error: e.message }; }
  }
  return S.probes[path];
}
const curTitle = () => (P().titles || []).find((x) => x.id === S.sel.id);

function renderTitle(m) {
  const ti = curTitle();
  if (!ti) return select("disc");
  if (ti.slideshow) return renderSlideshow(m, ti);
  let src = ti.source, join = null;
  if (ti.clips) {
    join = clipJoinNow(ti);
    if (!join) {
      m.innerHTML = `<div class="card"><h2>${esc(ti.name || ti.id)}</h2><div class="muted" id="clip-wait">${esc(t("joining"))}</div><div id="clip-box">${clipEditorHtml(ti, null)}</div></div>`;
      bindClipEditor(m, ti);
      clipJoin(ti).then(() => S.sel.view === "title" && S.sel.id === ti.id && renderMainLater(),
        (e) => { const w = $("#clip-wait"); if (w) { w.className = "hint"; w.textContent = e.message; } });
      return;
    }
    src = join.path;
  }
  const info = S.probes[src];
  if (!info) { m.innerHTML = `<div class="muted">…</div>`; probe(src).then(() => S.sel.view === "title" && renderMainLater()); return; }
  const fps = (() => { const [a, b] = String(info.fps || "30").split(/[/:]/).map(Number); return b ? a / b : a || 30; })();
  const dur = join ? join.duration : info.duration || 0;
  const ph = Math.min(S.playhead[ti.id] || 0, dur);
  const chapters = chaptersOf(ti);
  const ar = ti.aspect || P().disc.aspect;
  const chNow = Math.max(1, chapters.filter((c) => c <= ph + 1e-6).length);
  const zoom = S.monZoom || "fit";
  m.innerHTML = `<div class="monitor">
    <div class="monitor-screen ${zoom === "fit" ? "fit" : ""}"><div class="viewer" style="aspect-ratio:${ar.replace(":", " / ")};${zoom === "fit" ? "" : `width:${Math.round(720 * Number(zoom))}px`}"><img id="frame" alt=""><video id="player" playsinline preload="none" hidden></video>
      ${S.showSafe ? `<div class="safe-guides"><i></i><b></b></div>` : ""}
      <span class="tc" id="tc">${fmtTime(ph)}</span><span class="proxy-msg" id="proxy-msg" hidden></span></div></div>
    <div class="timeline" id="timeline">
      ${chapters.map((c, i) => `<div class="marker" data-ch="${i}" title="${esc(t("chapter_at", { n: i + 1 }))} ${fmtTime(c)}" style="left:${dur ? (c / dur) * 100 : 0}%"></div>`).join("")}
      <input type="range" id="scrub" min="0" max="${dur}" step="${(1 / fps).toFixed(5)}" value="${ph}">
    </div>
    <div class="monitor-bar transport">
      <select id="mon-zoom" class="shrink" title="${esc(t("zoom_hint"))}">${[["fit", t("fit")], ["0.5", "50%"], ["1", "100%"]].map(([v, l]) => `<option value="${v}" ${v === zoom ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>
      <button class="micon ${S.showSafe ? "on" : ""}" id="mon-safe" title="${esc(t("toggle_safe"))}">${ICONS.safe}</button>
      <span class="sep"></span>
      <button class="micon" data-step="-1" title="−1s">−1s</button>
      <button class="micon" data-step="${-1 / fps}" title="${esc(t("step_back"))}">${ICONS.stepb}</button>
      <button id="play" class="micon play" title="${esc(t("play"))} (Space)">${ICONS.play}<span class="sr">${t("play")}</span></button>
      <button class="micon" data-step="${1 / fps}" title="${esc(t("step_fwd"))}">${ICONS.stepf}</button>
      <button class="micon" data-step="1" title="+1s">+1s</button>
      <span class="sep"></span>
      <button class="micon" id="mon-prev" title="${esc(t("prev_ch"))} (PgUp)">${ICONS.prevch}</button>
      <span class="chnum mono" id="mon-ch">${String(chNow).padStart(2, "0")}</span>
      <button class="micon" id="mon-next" title="${esc(t("next_ch"))} (PgDn)">${ICONS.nextch}</button>
      <button id="add-ch" class="micon" title="${esc(t("add_chapter"))} (*)">${ICONS.addch}</button>
      <span class="spacer"></span>
      <input id="tc-input" class="tc-amber mono" value="${fmtTime(ph)}" title="${t("playhead")}">
    </div>
    <div class="monitor-extra">
    <div class="meta-line"><b>${esc(ti.name || ti.id)}</b> <span class="muted">${join ? esc(t("clips_n", { n: ti.clips.length })) : esc(ti.source) + ` · ${info.width || "?"}×${info.height || "?"}`} · ${dur.toFixed(2)}s</span></div>
    <div id="clip-box">${clipEditorHtml(ti, join)}</div>
    <h3>${t("chapters")} (${chapters.length})</h3>
    <ul class="chapter-list">${chapterEntries(ti).map((c, i) => `<li><span class="n">${i + 1}</span><span class="t" data-seek="${c.time}">${fmtTime(c.time)}</span>
      <input class="ch-name" data-ch-name="${i}" value="${esc(c.name)}" placeholder="${esc(t("chapter_at", { n: i + 1 }))}" title="${esc(t("chapter_name"))}">
      <button class="small ${c.poster != null ? "on" : ""}" data-poster="${i}" title="${esc(t("poster_hint"))}">🖼 ${c.poster != null ? fmtTime(c.poster) : t("poster")}</button>
      ${i ? `<button class="small danger" data-del="${i}">✕</button>` : ""}</li>`).join("")}</ul>
    <div id="sub-editor"></div>
  </div></div>`;
  const img = $("#frame");
  let pending = null, last = -1;
  const show = (time) => {
    S.playhead[ti.id] = time; tlPlayhead(time);
    $("#tc").textContent = fmtTime(time); $("#tc-input").value = fmtTime(time);
    const n = Math.max(1, chapters.filter((c) => c <= time + 1e-6).length), chEl = $("#mon-ch");
    if (chEl) chEl.textContent = String(n).padStart(2, "0");
    const tlTc = $("#tl-tc"); if (tlTc) tlTc.textContent = fmtTime(time);
    clearTimeout(pending);
    pending = setTimeout(() => {
      if (Math.abs(time - last) < 1e-4) return;
      last = time;
      img.src = imgUrl("frame", { path: src, t: time.toFixed(3), w: 960 });
    }, 90);
  };
  img.onerror = () => { img.alt = t("frame_err"); };
  const scrub = $("#scrub");
  // Playback uses a small H.264 copy made by the server; when it stops, the
  // exact frame at that time is shown again (frame-accurate chapter marks).
  const video = $("#player"), msg = $("#proxy-msg"), playBtn = $("#play");
  const snap = (x) => Math.round(x * fps) / fps;
  const format = video.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"') ? "mp4" : "webm";
  let playing = false;
  const toFrames = (time) => {
    playing = false; video.pause(); video.hidden = true; img.hidden = false;
    playBtn.innerHTML = `${ICONS.play}<span class="sr">${t("play")}</span>`;
    if (time != null) seek(time);
  };
  const seek = (time) => {
    if (playing) toFrames(null);
    time = Math.max(0, Math.min(dur, time)); scrub.value = time; show(time);
  };
  S.titleSeek = seek;
  scrub.oninput = () => { if (playing) toFrames(null); show(Number(scrub.value)); };
  video.onpause = () => { if (playing) toFrames(snap(video.currentTime)); };
  video.ontimeupdate = () => {
    if (!playing) return;
    scrub.value = video.currentTime; S.playhead[ti.id] = video.currentTime; tlPlayhead(video.currentTime);
    $("#tc").textContent = fmtTime(video.currentTime); $("#tc-input").value = fmtTime(video.currentTime);
  };
  video.onerror = () => { if (video.getAttribute("src")) { msg.hidden = false; msg.textContent = t("play_err"); toFrames(null); } };
  playBtn.onclick = async () => {
    if (playing) { video.pause(); return; }
    playBtn.disabled = true;
    try {
      for (;;) {
        const st = await api("/api/proxy?" + new URLSearchParams({ path: src, format }), { method: "POST" });
        if (st.state === "ready") break;
        if (st.state === "error") throw new Error(st.error || t("play_err"));
        msg.hidden = false; msg.textContent = t("preparing", { p: Math.round(st.fraction * 100) });
        await new Promise((r) => setTimeout(r, 500));
        if (S.sel.view !== "title" || S.sel.id !== ti.id || !document.body.contains(video)) return;
      }
    } catch (e) { msg.hidden = false; msg.textContent = e.message; return; }
    finally { playBtn.disabled = false; }
    msg.hidden = true;
    const url = imgUrl("proxy", { path: src, format });
    if (video.getAttribute("src") !== url) video.src = url;
    video.currentTime = Number(scrub.value) >= dur - 0.05 ? 0 : Number(scrub.value);
    playing = true; video.hidden = false; img.hidden = true;
    playBtn.innerHTML = `${ICONS.pause}<span class="sr">${t("pause")}</span>`;
    video.play().catch((e) => { if (playing) { msg.hidden = false; msg.textContent = e.message; toFrames(null); } });
  };
  m.querySelectorAll("[data-step]").forEach((b) => (b.onclick = () => seek(Number(scrub.value) + Number(b.dataset.step))));
  m.querySelectorAll("[data-seek]").forEach((el) => (el.onclick = () => seek(Number(el.dataset.seek))));
  m.querySelectorAll(".marker").forEach((el) => (el.onclick = () => seek(chapters[Number(el.dataset.ch)])));
  $("#tc-input").onchange = (e) => seek(parseTime(e.target.value));
  $("#mon-prev").onclick = () => jumpChapter(-1);
  $("#mon-next").onclick = () => jumpChapter(1);
  $("#mon-zoom").onchange = (e) => { S.monZoom = e.target.value; renderMain(); };
  $("#mon-safe").onclick = () => { S.showSafe = !S.showSafe; renderMain(); };
  $("#add-ch").onclick = () => {
    if (playing) toFrames(snap(video.currentTime));
    const time = Number(scrub.value);
    if (chapters.some((c) => Math.abs(c - time) < 0.5)) return;
    commit((p) => {
      const x = p.titles.find((y) => y.id === ti.id);
      const list = chapterEntries(x); list.push({ time, name: "", poster: null }); list.sort((a, b) => a.time - b.time);
      setChapters(x, list);
    });
  };
  m.querySelectorAll("[data-del]").forEach((b) => (b.onclick = () => commit((p) => {
    const x = p.titles.find((y) => y.id === ti.id);
    const list = chapterEntries(x); list.splice(Number(b.dataset.del), 1);
    setChapters(x, list);
  })));
  // chapter names (chapter menu labels) and poster frames (their thumbnails)
  m.querySelectorAll("[data-ch-name]").forEach((inp) => (inp.onchange = () => commit((p) => {
    const x = p.titles.find((y) => y.id === ti.id), list = chapterEntries(x);
    list[Number(inp.dataset.chName)].name = inp.value.trim(); setChapters(x, list);
  })));
  m.querySelectorAll("[data-poster]").forEach((b) => (b.onclick = () => commit((p) => {
    const x = p.titles.find((y) => y.id === ti.id), list = chapterEntries(x), e = list[Number(b.dataset.poster)];
    e.poster = e.poster != null && b.classList.contains("on") ? null : Number(scrub.value); setChapters(x, list);
  })));
  show(ph);
  bindClipEditor(m, ti, seek);
  renderSubEditor(ti, () => Number(scrub.value), seek);
}

// ---------------------------------------------------------------- subtitle editor
async function renderSubEditor(ti, playhead, seek) {
  const box = $("#sub-editor");
  if (!box) return;
  const tracks = ti.subtitles || [];
  S.subTrack = Math.min(S.subTrack || 0, Math.max(0, tracks.length - 1));
  const head = `<h3>${t("subtitle_editor")}</h3>
    <div class="row">${tracks.length ? selectHtml("subtrack", tracks.map((x, i) => [String(i), `${i + 1}: ${x.file.replace(/^media\//, "")}${x.lang ? " (" + x.lang + ")" : ""}`]), String(S.subTrack), 'id="sub-track"') : `<span class="hint">${esc(t("no_sub_tracks"))}</span>`}
      <button class="small shrink" id="sub-new">${t("new_srt")}</button></div>`;
  if (!tracks.length) { box.innerHTML = head; bindNew(); return; }
  const path = tracks[S.subTrack].file, offset = tracks[S.subTrack].offset ?? "";
  let data;
  try { data = await api("/api/subtitles?" + new URLSearchParams({ path, offset })); }
  catch (e) { box.innerHTML = head + `<div class="hint">${esc(e.message)}</div>`; bindNew(); return; }
  const cues = data.cues;
  box.innerHTML = head + (data.editable ? "" : `<div class="hint">${esc(t("sub_readonly"))} <button class="small" id="sub-convert">${t("convert_srt")}</button></div>`) +
    `<table class="cues"><tbody>${cues.map((c, i) => `<tr data-cue="${i}">
      <td><input class="mono" data-f="start" value="${fmtTime(c.start)}" ${data.editable ? "" : "disabled"}></td>
      <td><input class="mono" data-f="end" value="${fmtTime(c.end)}" ${data.editable ? "" : "disabled"}></td>
      <td style="width:100%"><textarea data-f="text" rows="${Math.max(1, c.text.split("\n").length)}" ${data.editable ? "" : "disabled"}>${esc(c.image ? "▣ " + c.image.split("/").pop() : c.text)}</textarea></td>
      <td>${selectHtml("pos", [["", t("sub_track_pos")], ["top", t("sub_top")], ["bottom", t("sub_bottom")]], c.position || "", `data-f="position" ${data.editable ? "" : "disabled"}`)}</td>
      <td><button class="small" data-go="${i}" title="${esc(t("playhead"))}">▶</button>${data.editable ? `<button class="small danger" data-delcue="${i}">✕</button>` : ""}</td></tr>`).join("")}</tbody></table>
    ${data.editable ? `<button class="small" id="sub-add">${t("add_cue")}</button>` : ""}`;
  const save = async (list) => {
    await api("/api/subtitles?" + new URLSearchParams({ path }), { method: "PUT", body: { cues: list } });
    renderSubEditor(ti, playhead, seek);
  };
  box.querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => seek(cues[Number(b.dataset.go)].start)));
  if (data.editable) {
    box.querySelectorAll("tr[data-cue]").forEach((row) => row.querySelectorAll("[data-f]").forEach((inp) => (inp.onchange = () => {
      const c = cues[Number(row.dataset.cue)], f = inp.dataset.f;
      if (f === "start" || f === "end") c[f] = parseTime(inp.value); else c[f] = inp.value || null;
      save(cues);
    })));
    box.querySelectorAll("[data-delcue]").forEach((b) => (b.onclick = () => { cues.splice(Number(b.dataset.delcue), 1); save(cues); }));
    $("#sub-add").onclick = () => { const st = playhead(); cues.push({ start: st, end: st + 2, text: t("new_cue_text") }); save(cues); };
  } else {
    $("#sub-convert").onclick = async () => {
      const name = path.replace(/\.[^.]+$/, "") + ".srt";
      await api("/api/subtitles?" + new URLSearchParams({ path: name }), { method: "PUT", body: { cues } });
      await refreshMedia();
      // (written as the title shows them: the offset is in the times now)
      commit((p) => { const st = p.titles.find((x) => x.id === ti.id).subtitles[S.subTrack]; st.file = name; delete st.offset; });
    };
  }
  $("#sub-track").onchange = (e) => { S.subTrack = Number(e.target.value); renderSubEditor(ti, playhead, seek); };
  bindNew();
  function bindNew() {
    $("#sub-new").onclick = async () => {
      const used = new Set(S.media.map((x) => x.path));
      let n = 1, name;
      do { name = `media/${ti.id}-${n++}.srt`; } while (used.has(name));
      await api("/api/subtitles?" + new URLSearchParams({ path: name }), { method: "PUT", body: { cues: [] } });
      await refreshMedia();
      commit((p) => { const x = p.titles.find((y) => y.id === ti.id); (x.subtitles = x.subtitles || []).push({ file: name }); });
      S.subTrack = (ti.subtitles || []).length;
    };
  }
}

// ---------------------------------------------------------------- slideshows
function addSlideshow() {
  const images = mediaOf("image");
  if (!images.length) { openModal(`<h2>${t("add_slideshow")}</h2><p>${esc(t("slideshow_need_images"))}</p>`); return; }
  const id = uniqueId("slides", (P().titles || []).map((x) => x.id));
  commit((p) => { (p.titles = p.titles || []).push({ id, name: t("slideshow"), slideshow: { slides: images.map((image) => ({ image })) } }); });
  select("title", id);
}
const TRANSITION_KINDS = ["dissolve", "fadeblack", "fadewhite", "wipeleft", "wiperight", "wipeup", "wipedown", "slideleft", "slideright", "slideup", "slidedown", "circleopen", "circleclose", "radial", "pixelize"];
const transitionOptions = () => [["crossfade", t("crossfade")], ...TRANSITION_KINDS.map((k) => [k, t("tr_" + k)]), ["random", t("tr_random")], ["none", t("cut")]];
function renderSlideshow(m, ti) {
  const sh = ti.slideshow, slides = sh.slides || [];
  const music = sh.audio ? (Array.isArray(sh.audio) ? sh.audio : [sh.audio]) : [];
  const manual = sh.advance === "manual";
  const total = slides.reduce((a, s) => a + (s.duration || 5), 0);
  m.innerHTML = `<div class="card">
    <div class="row"><h2 class="shrink">${esc(ti.name || ti.id)}</h2><span class="muted">${esc(t("slideshow"))} · ${slides.length} · ${total.toFixed(1)}s</span></div>
    <div class="viewer" id="ss-viewer" style="aspect-ratio:${(ti.aspect || P().disc.aspect).replace(":", " / ")}">
      <video id="player" playsinline controls hidden></video><span class="proxy-msg" id="proxy-msg" hidden></span>
      <span class="hint" id="ss-hint">${esc(t("slideshow_preview_hint"))}</span></div>
    <div class="transport"><button id="ss-play" class="primary">▶ ${t("render_play")}</button></div>
    <div class="slides">${slides.map((s, i) => `<div class="slide" data-slide="${i}">
        <img src="${imgUrl("file", { path: s.image })}" alt="">
        <div class="row" ${manual ? 'style="display:none"' : ""}><input type="number" min="0.5" max="600" step="0.5" data-f="duration" value="${s.duration || 5}" title="${esc(t("seconds"))}"> s <span class="muted" data-fitted></span></div>
        <div class="row">${selectHtml("sfit", [["", t("fit_own")], ["fit", t("fit_fit")], ["fill", t("fit_fill")]], s.fit || "", `data-f="fit" title="${esc(t("fit"))}"`)}</div>
        ${i + 1 < slides.length && !manual ? `<div class="row">${selectHtml("str", [["", t("tr_own")], ...transitionOptions()], s.transition || "", `data-f="transition" title="${esc(t("tr_next"))}"`)}</div>` : ""}
        <div class="row"><button class="small" data-mv="-1" ${i ? "" : "disabled"}>◀</button><button class="small" data-mv="1" ${i + 1 < slides.length ? "" : "disabled"}>▶</button><button class="small danger" data-rm ${slides.length > 1 ? "" : "disabled"}>✕</button></div></div>`).join("")}
      <div class="slide add">${selectHtml("addimg", [["", t("add_picture")], ...mediaOf("image").map((x) => [x, x.replace(/^media\//, "")])], "", 'id="ss-add"')}</div></div>
    <label style="display:block;margin-top:12px"><input type="checkbox" id="ss-manual" ${manual ? "checked" : ""}> ${t("advance_manual")}</label>
    <div class="grid2" style="margin-top:12px${manual ? ";display:none" : ""}">
      <label class="field"><span>${t("transition")}</span>${selectHtml("transition", transitionOptions(), sh.transition || "crossfade", 'id="ss-tr"')}</label>
      <label class="field"><span>${t("transition_duration")}</span><input type="number" id="ss-td" min="0.1" max="5" step="0.1" value="${sh.transition_duration || 1}"></label>
      <div class="field"><span>${t("music")}</span><div>${music.map((x, i) => `<div class="row ss-music"><span class="mono">${esc(x.replace(/^media\//, ""))}</span><span class="spacer"></span><button class="small danger" data-rmmusic="${i}">✕</button></div>`).join("")}
        ${selectHtml("addmusic", [["", t("add_music")], ...mediaOf("audio").map((x) => [x, x.replace(/^media\//, "")])], "", 'id="ss-audio"')}
        <label><input type="checkbox" id="ss-fitaudio" ${sh.fit_to_audio ? "checked" : ""} ${music.length ? "" : "disabled"}> ${t("fit_to_music")}</label></div></div>
      <label class="field"><span></span><label><input type="checkbox" id="ss-pz" ${sh.pan_zoom ? "checked" : ""}> ${t("pan_zoom")}</label></label>
      <label class="field"><span>${t("fit")}</span>${selectHtml("fit", [["fit", t("fit_fit")], ["fill", t("fit_fill")]], sh.fit || "fit", 'id="ss-fit"')}</label>
    </div>
    <div class="hint">${esc(t("slideshow_chapters"))}</div></div>`;
  const edit = (fn) => commit((p) => { fn(p.titles.find((x) => x.id === ti.id).slideshow); });
  m.querySelectorAll("[data-slide]").forEach((card) => {
    const i = Number(card.dataset.slide);
    card.querySelector("[data-f=duration]").onchange = (e) => edit((x) => { const v = Number(e.target.value); if (v && v !== 5) x.slides[i].duration = v; else delete x.slides[i].duration; });
    card.querySelector("[data-f=fit]").onchange = (e) => edit((x) => { if (e.target.value) x.slides[i].fit = e.target.value; else delete x.slides[i].fit; });
    const tr = card.querySelector("[data-f=transition]");
    if (tr) tr.onchange = (e) => edit((x) => { if (e.target.value) x.slides[i].transition = e.target.value; else delete x.slides[i].transition; });
    card.querySelectorAll("[data-mv]").forEach((b) => (b.onclick = () => edit((x) => { const j = i + Number(b.dataset.mv); [x.slides[i], x.slides[j]] = [x.slides[j], x.slides[i]]; })));
    card.querySelector("[data-rm]").onclick = () => edit((x) => { x.slides.splice(i, 1); });
  });
  $("#ss-add").onchange = (e) => { if (e.target.value) edit((x) => { x.slides.push({ image: e.target.value }); }); };
  $("#ss-tr").onchange = (e) => edit((x) => { if (e.target.value === "crossfade") delete x.transition; else x.transition = e.target.value; });
  $("#ss-td").onchange = (e) => edit((x) => { const v = Number(e.target.value); if (v && v !== 1) x.transition_duration = v; else delete x.transition_duration; });
  // one file stays a string; several are a list, played one after another
  const setMusic = (x, list) => {
    if (!list.length) { delete x.audio; delete x.fit_to_audio; } else x.audio = list.length === 1 ? list[0] : list;
  };
  $("#ss-audio").onchange = (e) => { if (e.target.value) edit((x) => setMusic(x, [...music, e.target.value])); };
  m.querySelectorAll("[data-rmmusic]").forEach((b) => (b.onclick = () => edit((x) => setMusic(x, music.filter((_, i) => i !== Number(b.dataset.rmmusic))))));
  // by hand: a still per picture, so no timing, transitions or music
  $("#ss-manual").onchange = (e) => edit((x) => {
    if (!e.target.checked) { delete x.advance; return; }
    x.advance = "manual";
    for (const k of ["transition", "transition_duration", "audio", "fit_to_audio", "pan_zoom"]) delete x[k];
    for (const s of x.slides) { delete s.duration; delete s.transition; }
  });
  $("#ss-fitaudio").onchange = (e) => edit((x) => { if (e.target.checked) x.fit_to_audio = true; else delete x.fit_to_audio; });
  $("#ss-pz").onchange = (e) => edit((x) => { if (e.target.checked) x.pan_zoom = true; else delete x.pan_zoom; });
  $("#ss-fit").onchange = (e) => edit((x) => { if (e.target.value === "fill") x.fit = "fill"; else delete x.fit; });
  $("#ss-play").onclick = async () => {
    const btn = $("#ss-play"), msg = $("#proxy-msg"), video = $("#player");
    btn.disabled = true; msg.hidden = false; msg.textContent = t("rendering");
    try {
      await save();
      const r = await api("/api/slideshow", { method: "POST", body: { title: ti.id, project: S.project } });
      // fitted to the music: the seconds each picture got
      if (sh.fit_to_audio) (r.durations || []).forEach((d, i) => {
        const el = m.querySelector(`[data-slide="${i}"] [data-fitted]`);
        if (el) el.textContent = t("fitted_to", { d: `${d.toFixed(1)} s` });
      });
      const format = video.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"') ? "mp4" : "webm";
      for (;;) {
        const st = await api("/api/proxy?" + new URLSearchParams({ path: r.path, format }), { method: "POST" });
        if (st.state === "ready") break;
        if (st.state === "error") throw new Error(st.error || t("play_err"));
        msg.textContent = t("preparing", { p: Math.round(st.fraction * 100) });
        await new Promise((res) => setTimeout(res, 500));
      }
      msg.hidden = true; $("#ss-hint").hidden = true;
      video.src = imgUrl("proxy", { path: r.path, format }); video.hidden = false;
      video.play().catch(() => {});
    } catch (e) { msg.textContent = e.message; }
    finally { btn.disabled = false; }
  };
}

// ---------------------------------------------------------------- flowchart
async function renderFlow(m) {
  m.innerHTML = `<div class="card"><h2>${t("flowchart")}</h2><div class="hint">${esc(t("flow_link_hint"))}</div><div id="flow" class="flow"><span class="hint">…</span></div><div id="flow-notes"></div></div>`;
  let r;
  try { r = await api("/api/graph", { method: "POST", body: { project: S.project } }); }
  catch (e) { const f = $("#flow"); if (f) f.innerHTML = `<div class="hint">${esc(e.message)}</div>`; return; }
  if (S.sel.view !== "flow") return;
  const { nodes, edges } = r.graph;
  // each item is a card: its picture, its name under it; a menu also lists
  // its buttons under an orange band. First play is the disc itself.
  const W = 132, H = 74, CW = 200, RH = 150, PAD = 24;
  const pos = {};
  // items nothing leads to go in their own row at the bottom, as unused
  const unused = new Set(r.unused || []);
  const used = nodes.filter((n) => !unused.has(n.id));
  used.forEach((n) => (pos[n.id] = { x: PAD + n.col * CW, y: PAD + n.row * RH }));
  const usedRows = used.length ? Math.max(...used.map((n) => n.row)) + 1 : 0;
  const spareY = PAD + usedRows * RH + (unused.size ? 40 : 0);
  nodes.filter((n) => unused.has(n.id)).forEach((n, k) => (pos[n.id] = { x: PAD + k * CW, y: spareY }));
  const width = PAD * 2 + Math.max(...used.map((n) => n.col + 1), unused.size, 1) * CW;
  const height = (unused.size ? spareY + RH : PAD + usedRows * RH) + PAD;
  const level = {};
  r.notes.forEach((x) => { if (x.level === "warning" || !level[x.path]) level[x.path] = x.level; });
  const label = (n) => ({ first_play: t("fp"), title_key: t("title_key_node"), stop: t("stop_node"), playall: t("play_all"), last_menu: t("last_menu") }[n.kind] || n.label);
  const sub = (n) => n.kind === "menu" ? `${t("menu")} · ${n.buttons}` : n.kind === "title" ? `${t("title")} ${n.number} · ${n.chapters} ch` : n.kind === "playlist" ? `${t("playlist")} · ${n.items}` : "";
  const thumb = (n) => {
    const [kind, ...rest] = n.id.split(":"), id = rest.join(":");
    if (kind === "menu") {
      const mm = (P().menus || []).find((x) => x.id === id);
      if (mm?.background) return imgUrl("file", { path: mm.background });
      if (mm?.background_video) return imgUrl("frame", { path: mm.background_video, t: 0, w: 160 });
      // a generated chapter menu: its title's picture
      const g = !mm && generatedMenus().find((x) => x.id === id), gt = g && (P().titles || []).find((x) => x.id === g.title);
      if (gt?.source && !gt.slideshow) return imgUrl("frame", { path: gt.source, t: 1, w: 160 });
    }
    if (kind === "title") {
      const ti = (P().titles || []).find((x) => x.id === id);
      if (ti?.source && !ti.slideshow) return imgUrl("frame", { path: ti.source, t: 1, w: 160 });
    }
    return "";
  };
  const buttonsOf = (n) => n.kind !== "menu" ? [] : ((P().menus || []).find((x) => "menu:" + x.id === n.id)?.buttons || []).filter((b) => !b.hidden).map((b) => b.label || b.id);
  const card = (n) => {
    if (n.kind === "first_play") {
      return `<circle cx="${W / 2}" cy="${H / 2 - 2}" r="30" class="disc-ico"/><circle cx="${W / 2}" cy="${H / 2 - 2}" r="8" class="disc-hole"/>
        <rect class="lbl" y="${H}" width="${W}" height="18" rx="2"/><text x="6" y="${H + 13}" class="nl">${esc((P().disc.label || label(n)).slice(0, 20))}</text>`;
    }
    const src = thumb(n), bs = buttonsOf(n);
    const pic = src ? `<image href="${esc(src)}" x="3" y="3" width="${W - 6}" height="${H - 6}" preserveAspectRatio="xMidYMid slice"/>`
      : `<text x="${W / 2}" y="${H / 2 + 6}" text-anchor="middle" class="ph">${esc({ title_key: "TITLE", playall: "▶▶", stop: "■", playlist: "≡" }[n.kind] || "")}</text>`;
    return `<rect width="${W}" height="${H}" rx="2"/>${pic}
      <rect class="lbl" y="${H}" width="${W}" height="18" rx="2"/><text x="6" y="${H + 13}" class="nl">${esc(label(n).slice(0, 20))}</text>
      ${n.kind === "title" || n.kind === "playlist" ? `<text x="6" y="${H + 30}" class="ns">${esc(sub(n))}</text>` : ""}
      ${bs.length ? `<rect class="band" y="${H + 18}" width="${W}" height="4"/>${bs.slice(0, 4).map((b, k) => `<rect class="brow" y="${H + 22 + k * 15}" width="${W}" height="15"/><text x="8" y="${H + 33 + k * 15}" class="nb">${esc(String(b).slice(0, 20))}</text>`).join("")}${bs.length > 4 ? `<text x="8" y="${H + 33 + 4 * 15}" class="nb">…</text>` : ""}` : ""}`;
  };
  const path = (e, k) => {
    const a = pos[e.from], b = pos[e.to];
    if (!a || !b) return "";
    let x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2;
    const off = (k % 5) * 3 - 6;
    if (b.x === a.x) {          // same column: bulge out to the right
      x1 = a.x + W; x2 = b.x + W;
      const out = x1 + 22 + (k % 4) * 7;
      return `M${x1},${y1 + off} C${out},${y1 + off} ${out},${y2 + off} ${x2 + 2},${y2 + off}`;
    }
    if (b.x < a.x) {            // backwards: loop below
      x1 = a.x + W / 2 + off; y1 = a.y + H; x2 = b.x + W / 2 + off; y2 = b.y + H;
      const dip = Math.max(y1, y2) + 24 + (k % 4) * 6;
      return `M${x1},${y1} C${x1},${dip} ${x2},${dip} ${x2},${y2}`;
    }
    const mx = (x1 + x2) / 2;
    return `M${x1},${y1 + off} C${mx},${y1 + off} ${mx},${y2 + off} ${x2},${y2 + off}`;
  };
  const svg = `<svg class="flow-svg" width="${width}" height="${height + 40}" viewBox="0 0 ${width} ${height + 40}">
    <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrowhead"/></marker></defs>
    ${edges.map((e, k) => `<path class="edge ${e.kind}${e.transition ? " via-transition" : ""}" d="${path(e, k)}" marker-end="url(#arr)"><title>${esc(e.from)} → ${esc(e.to)}${e.label ? " (" + esc(e.label) + ")" : ""}${e.transition ? ` · ${esc(t("transition"))}: ${esc(e.transition)}` : ""}</title></path>`).join("")}
    ${unused.size ? `<line class="unused-line" x1="${PAD}" x2="${width - PAD}" y1="${spareY - 26}" y2="${spareY - 26}"/><text class="unused-label" x="${PAD}" y="${spareY - 8}">${esc(t("unused"))}</text>` : ""}
    ${nodes.map((n) => `<g class="node ${n.kind} ${level[n.id] || ""} ${unused.has(n.id) ? "unused" : ""}" data-node="${esc(n.id)}" transform="translate(${pos[n.id].x},${pos[n.id].y})">
      ${card(n)}</g>`).join("")}
  </svg>`;
  $("#flow").innerHTML = svg;
  $("#flow-notes").innerHTML = r.notes.length ? `<ul class="issues">${r.notes.map((x) => `<li class="${x.level}"><span class="path" data-node="${esc(x.path)}">${esc(x.path)}</span> ${esc(x.message)}</li>`).join("")}</ul>` : `<div class="hint ok">✓ ${esc(t("nav_ok"))}</div>`;
  const open = (node) => {
    const [kind, ...rest] = node.split(":"), id = rest.join(":");
    if (kind === "menu" || kind === "title" || kind === "playlist") select(kind, id);
    else if (kind === "fp" || kind === "title_key") select("disc");
  };
  m.querySelectorAll("#flow-notes [data-node]").forEach((g) => (g.onclick = () => open(g.dataset.node)));
  // click opens an item; dragging from it to another item links them
  m.querySelectorAll("#flow g.node[data-node]").forEach((g) => {
    g.onpointerdown = (ev) => {
      ev.preventDefault();                        // (no text selection while dragging)
      const x0 = ev.clientX, y0 = ev.clientY, src = g.dataset.node;
      const move = (e) => {
        if (Math.hypot(e.clientX - x0, e.clientY - y0) < 6) return;
        window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up);
        startWhip(e, (action) => flowLink(src, action, e), g);
      };
      const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); open(src); };
      window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
    };
  });
}

// a link made in the flowchart: from first play, the Title key, a title's or
// playlist's end, or a menu button (asked) to the dropped item
function flowLink(src, action, ev) {
  const [kind, ...rest] = src.split(":"), id = rest.join(":");
  if (src === action) return;
  if (kind === "fp") return commit((p) => { p.disc.first_play = action; });
  if (kind === "title_key") return commit((p) => { p.disc.title_key = action; });
  if (kind === "title") return commit((p) => { p.titles.find((x) => x.id === id).end_action = action; });
  if (kind === "playlist") return commit((p) => { p.playlists.find((x) => x.id === id).end_action = action; });
  if (kind === "menu") {
    const menu = (P().menus || []).find((x) => x.id === id);
    if (!menu || action === `menu:${id}`) return;
    openPopup(ev.clientX, ev.clientY, [{ label: t("pick_button"), disabled: true, run: () => {} }, "-",
      ...menu.buttons.map((b, i) => ({ label: `${i + 1}. ${b.label || b.id} → ${linkLabel(action)}`, run: () => commit((p) => { p.menus.find((x) => x.id === id).buttons[i].action = action; }) }))]);
  }
}

// ---------------------------------------------------------------- disc simulator
const SIM_KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Enter: "enter", m: "menu", t: "title", n: "next", p: "prev" };
async function simCall(key) {
  const body = { project: S.project };
  if (key && S.sim) { body.state = S.sim.state; body.key = key; }
  else if (S.simFrom) { body.from_menu = S.simFrom; S.simFrom = null; }
  try { S.sim = await api("/api/sim", { method: "POST", body }); S.simError = null; }
  catch (e) { S.simError = e.message; }
  if (S.sel.view === "sim") renderSimScreen();
}
async function renderSim(m) {
  m.innerHTML = `<div class="card sim">
    <div class="row"><h2 class="shrink">${t("simulator")}</h2><span class="spacer"></span><button class="small shrink" id="sim-restart">⟲ ${t("restart")}</button></div>
    <div class="sim-wrap">
      <div class="sim-screen" id="sim-screen" tabindex="0" style="aspect-ratio:${P().disc.aspect.replace(":", " / ")}"></div>
      <div class="remote" id="remote">
        <div class="pad"><span></span><button data-key="up" title="▲">▲</button><span></span>
          <button data-key="left">◀</button><button data-key="enter" class="ok">OK</button><button data-key="right">▶</button>
          <span></span><button data-key="down">▼</button><span></span></div>
        <div class="keys"><button data-key="menu">MENU</button><button data-key="title">TITLE</button></div>
        <div class="keys"><button data-key="prev" title="⏮">⏮</button><button data-key="play" title="${esc(t("play_chapter"))}">▶</button><button data-key="next" title="⏭">⏭</button></div>
        <div class="keys"><button data-key="end" title="${esc(t("to_end"))}">⏭⏭</button><button data-key="timeout" title="${esc(t("time_out"))}">⏱</button></div>
      </div>
    </div>
    <div class="sim-status" id="sim-status"></div></div>`;
  m.querySelectorAll("[data-key]").forEach((b) => (b.onclick = () => simCall(b.dataset.key)));
  $("#sim-restart").onclick = () => { S.sim = null; simCall(); };
  $("#sim-screen").onkeydown = async (e) => {
    // as on a player's remote: 0-9 press the button with that number (with
    // the menu's offset), Home the Title key,
    // Insert the Menu key, End plays to the end
    if (/^[0-9]$/.test(e.key) && S.sim?.state?.domain === "menu") {
      // (up to two digits, as players take them: the second within a moment)
      e.preventDefault();
      clearTimeout(S.simDigitTimer);
      S.simDigits = (S.simDigits || "") + e.key;
      const go = () => { const n = S.simDigits; S.simDigits = ""; if (n) simCall("number:" + Number(n)); };
      if (S.simDigits.length >= 2) go(); else S.simDigitTimer = setTimeout(go, 700);
      return;
    }
    const k = { Home: "title", Insert: "menu", End: "end" }[e.key] || SIM_KEYS[e.key] || SIM_KEYS[e.key.toLowerCase?.()];
    if (k) { e.preventDefault(); simCall(k); }
  };
  if (S.simFrom) { S.simProject = JSON.stringify(S.project); S.sim = null; S.simMenus = {}; await simCall(); }
  else if (!S.sim || S.simProject !== JSON.stringify(S.project)) { S.simProject = JSON.stringify(S.project); S.sim = null; S.simMenus = {}; await simCall(); }
  else renderSimScreen();
  $("#sim-screen").focus();
}
async function simMenu(id) {
  S.simMenus = S.simMenus || {};
  if (!S.simMenus[id]) S.simMenus[id] = api("/api/sim_menu", { method: "POST", body: { project: S.project, menu: id } });
  return S.simMenus[id];
}
async function renderSimScreen() {
  const scr = $("#sim-screen"), st = $("#sim-status");
  if (!scr) return;
  if (S.simError) { scr.innerHTML = `<div class="sim-msg">${esc(S.simError)}</div>`; return; }
  const sim = S.sim, s = sim.state;
  const flags = [s.audio ? t("audio_n", { n: s.audio }) : "", s.subtitle ? t("sub_n", { n: s.subtitle }) : t("sub_off"),
    s.playall ? t("in_playall") : "", s.playlist ? t("in_playlist") : ""].filter(Boolean).join(" · ");
  if (s.domain === "menu") {
    let mm;
    st.innerHTML = `<b>${t("now")}:</b> ${t("menu")} <span class="mono">${esc(s.menu)}</span> · ${esc(flags)}<div class="hint">${esc((s.log || []).join(" → "))}</div>`;
    if (!scr.dataset.menu || scr.dataset.menu !== s.menu) scr.innerHTML = `<div class="sim-msg">…</div>`;
    try { mm = await simMenu(s.menu); } catch (e) { scr.innerHTML = `<div class="sim-msg">${esc(e.message)}</div>`; return; }
    if (S.sim !== sim) return;
    const b = mm.buttons[s.button - 1];
    const [sw, sh] = mm.storage;
    scr.dataset.menu = s.menu;
    scr.innerHTML = `<img class="base" src="${mm.image}" alt="">${b ? `<img class="hl" src="${mm.overlays[b.id]}" alt="">` : ""}
      ${mm.buttons.map((x, i) => `<div class="hit" data-hit="${i + 1}" style="left:${x.rect[0] / sw * 100}%;top:${x.rect[1] / sh * 100}%;width:${(x.rect[2] - x.rect[0]) / sw * 100}%;height:${(x.rect[3] - x.rect[1]) / sh * 100}%" title="${esc(x.id)} → ${esc(x.action)}"></div>`).join("")}`;
    scr.querySelectorAll("[data-hit]").forEach((h) => (h.onclick = async () => { await simCall("select:" + h.dataset.hit); simCall("enter"); }));
    st.innerHTML = `<b>${t("now")}:</b> ${t("menu")} <span class="mono">${esc(s.menu)}</span> · ${esc(b ? b.id : "—")} · ${esc(flags)}<div class="hint">${esc((s.log || []).join(" → "))}</div>`;
  } else if (s.domain === "title") {
    scr.dataset.menu = "";
    const ti = sim.title, k = ti.chapter, start = ti.chapters[k - 1] || 0;
    const name = (ti.names || [])[k - 1];
    scr.innerHTML = `<img class="base" src="${imgUrl("frame", { path: ti.frame.path, t: ti.frame.t.toFixed(3), w: 720 })}" alt="">
      <div class="sim-osd">${esc(ti.name)} — ${esc(t("chapter_n", { n: k, m: ti.chapters.length }))}${name ? " · " + esc(name) : ""}</div>`;
    st.innerHTML = `<b>${t("now")}:</b> ${t("title")} <span class="mono">${esc(ti.id)}</span> · ${esc(t("chapter_n", { n: k, m: ti.chapters.length }))} · ${esc(flags)}<div class="hint">${esc((s.log || []).join(" → "))}</div>`;
  } else {
    scr.innerHTML = `<div class="sim-msg">■ ${esc(t("stopped"))}</div>`;
    st.innerHTML = `<div class="hint">${esc((s.log || []).join(" → "))}</div>`;
  }
}

// User operations: the remote keys a title or a menu turns off (prohibit)
const UOPS = ["next", "prev", "fast_forward", "rewind", "pause", "stop", "search", "menu", "title", "audio", "subtitle"];
function uopsHtml(obj, kind) {
  const on = new Set(obj.prohibit || []);
  return `<h3>${t("uops")}</h3><div class="hint">${esc(t("uops_hint_" + kind))}</div>
    <div class="uop-grid" data-nobind>${UOPS.map((k) => `<label><input type="checkbox" data-uop="${k}" ${on.has(k) ? "checked" : ""}> ${esc(t("uop_" + k))}</label>`).join("")}</div>`;
}
function bindUops(root, find) {
  root.querySelectorAll("[data-uop]").forEach((c) => (c.onchange = () => commit((p) => {
    const x = find(p), on = new Set(x.prohibit || []);
    if (c.checked) on.add(c.dataset.uop); else on.delete(c.dataset.uop);
    const list = UOPS.filter((k) => on.has(k));
    if (list.length) x.prohibit = list; else delete x.prohibit;
  })));
}
function renderTitleInspector(el) {
  const ti = curTitle();
  if (!ti) { el.innerHTML = ""; return; }
  const audio = ti.audio || {};
  const cm = ti.auto_chapter_menu;
  const ends = actionOptions({ forButton: false, includeChapters: true, allowPlayAll: true, allowLast: true });
  const langs = [["", "—"], ["ja", "日本語 (ja)"], ["en", "English (en)"], ["fr", "Français (fr)"], ["de", "Deutsch (de)"], ["es", "Español (es)"], ["zh", "中文 (zh)"], ["ko", "한국어 (ko)"]];
  const subs = ti.subtitles || [], tracks = ti.audio_tracks || [];
  const cap = typeof ti.captions === "string" ? { file: ti.captions } : (ti.captions || {});
  el.innerHTML = `<h2>${t("prop_title")}</h2>
    <label class="field"><span>${t("name")}</span><input data-k="name" value="${esc(ti.name || "")}"></label>
    <label class="field"><span>${t("id")}</span><input id="ti-id" value="${esc(ti.id)}"><div class="hint">${esc(t("rename_hint"))}</div></label>
    ${ti.slideshow || ti.clips ? `<label class="field"><span>${t("source")}</span><div class="hint">${esc(ti.clips ? t("clips_n", { n: ti.clips.length }) : t("slideshow"))}</div></label>`
      : `<label class="field"><span>${t("source")}</span>${selectHtml("source", [...mediaOf("video"), ...mediaOf("audio")].map((v) => [v, v]), ti.source)}</label>`}
    ${mediaOf("audio").includes(ti.source) ? `<label class="field"><span>${t("sound_picture")}</span>${selectHtml("picture", [["__none__", t("black")], ...mediaOf("image").map((v) => [v, v.replace(/^media\//, "")])], ti.picture || "__none__")}<div class="hint">${esc(t("sound_picture_hint"))}</div></label>` : ""}
    <label class="field"><span>${t("aspect")}</span>${selectHtml("aspect", [["__none__", `${t("auto")} (${P().disc.aspect})`], ["16:9", "16:9"], ["4:3", "4:3"]], ti.aspect || "__none__")}</label>
    ${ti.slideshow || ti.clips ? "" : `<label class="field"><span></span><label><input type="checkbox" id="ti-copy" ${ti.transcode === false ? "checked" : ""}> ${t("no_transcode")}</label><div class="hint">${esc(t("no_transcode_hint"))}</div></label>`}
    ${ti.transcode === false ? "" : `<label class="field"><span>${t("scan")}</span>${selectHtml("scan", [["__none__", t("scan_auto")], ["progressive", t("scan_progressive")], ["interlaced", t("scan_interlaced")], ...(P().disc.standard === "NTSC" ? [["pulldown", t("scan_pulldown")], ["ivtc", t("scan_ivtc")]] : [])], ti.scan || "__none__")}<div class="hint">${esc(t("scan_hint"))}</div></label>`}
    <label class="field"><span>${t("end_action")} ${whipHtml("end_action")}</span>${selectHtml("end_action", [["__none__", t("auto")], ...ends], ti.end_action || "__none__")}</label>
    <label class="field"><span>${t("menu_key")}</span>${selectHtml("remote_menu", [["__none__", t("first_menu")], ...allMenuIds().map((id) => [id, t("menu_item", { m: id })])], ti.remote_menu || "__none__")}<div class="hint">${esc(t("menu_key_hint"))}</div></label>
    <h3>${t("audio")}</h3>
    <div class="grid2">
      <label class="field"><span>${t("codec")}</span>${selectHtml("audio.codec", [["ac3", "AC-3"], ["lpcm", "LPCM"], ["dts", t("dts_copy")]], audio.codec || "ac3")}${audio.codec === "dts" ? `<div class="hint">${esc(t("dts_hint"))}</div>` : ""}</label>
      <label class="field"><span>${t("bitrate")}</span>${selectHtml("audio.bitrate", [["128k", "128k"], ["192k", "192k"], ["224k", "224k"], ["256k", "256k"], ["384k", "384k"], ["448k", "448k"]], audio.bitrate || (audio.channels === 6 ? "448k" : "192k"), audio.codec === "lpcm" || audio.codec === "dts" ? "disabled" : "")}</label>
      <label class="field"><span>${t("channels")}</span>${selectHtml("audio.channels", [["2", t("stereo")], ["6", t("surround")]], String(audio.channels || (audio.codec === "dts" ? 6 : 2)), audio.codec === "lpcm" ? "disabled" : "")}</label>
      <label class="field"><span>${t("video_bitrate")}</span>${selectHtml("video_bitrate", [["__none__", t("auto_shared")], ...["3M", "4M", "5M", "6M", "7M", "8M"].map((b) => [b, b.replace("M", " Mbit/s")])], ti.video_bitrate || "__none__", ti.transcode === false ? "disabled" : "")}</label>
      <label class="field"><span></span><label title="${esc(t("passthrough_hint"))}"><input type="checkbox" data-k="audio.passthrough" ${audio.passthrough || audio.codec === "dts" ? "checked" : ""} ${audio.codec === "lpcm" || audio.codec === "dts" ? "disabled" : ""}> ${t("passthrough")}</label></label>
    </div>
    ${tracks.length ? "" : `<label class="field"><span>${t("language")}</span>${selectHtml("audio.lang", langs, audio.lang || "")}</label>`}
    <h3>${t("audio_tracks")}</h3>
    <div class="hint">${esc(t("tracks_hint"))}</div>
    ${tracks.map((tr, i) => `<div class="row" style="margin:6px 0" data-track="${i}" data-nobind>
        ${selectHtml("source", [["", ti.source], ...mediaOf("audio").map((a) => [a, a]), ...mediaOf("video").filter((v) => v !== ti.source).map((v) => [v, v])], tr.source || "")}
        <input type="number" min="0" class="shrink" style="width:52px" data-k="stream" value="${tr.stream || 0}" title="${t("stream")}">
        ${selectHtml("lang", langs, tr.lang || "", 'class="shrink" style="width:90px"')}
        <button class="small danger shrink" data-del-track="${i}">✕</button></div>`).join("")}
    <button class="small" id="add-track" ${ti.clips ? "disabled" : ""}>${t("add_track")}</button>
    <h3>${t("subtitles")}</h3>
    ${subs.map((s, i) => `<div class="row" style="margin:6px 0 4px" data-sub="${i}" data-nobind>
        ${selectHtml("file", mediaOf("subtitle").filter((f) => !/\.scc$/i.test(f)).map((f) => [f, f.replace(/^media\//, "")]), s.file)}
        <button class="small danger shrink" data-del-sub="${i}">✕</button></div>
        <div class="row" style="margin:0 0 4px" data-sub="${i}" data-nobind>
        ${selectHtml("lang", langs, s.lang || "", 'class="shrink" style="width:90px"')}
        <label title="${t("default_on")}"><input type="checkbox" data-k="default" ${s.default ? "checked" : ""}> ${t("default_on")}</label></div>
        <div class="row" style="margin:0 0 10px" data-sub="${i}" data-nobind>
        ${selectHtml("position", [["bottom", t("sub_bottom")], ["top", t("sub_top")]], s.position || "bottom", 'class="shrink" style="width:90px"')}
        <label class="shrink"><input type="checkbox" data-k="has_color" ${s.color ? "checked" : ""}> ${t("sub_color")}</label>
        <input type="color" class="shrink" style="width:44px" data-k="color" value="${esc(s.color || "#ffffff")}" ${s.color ? "" : "disabled"}></div>
        <div class="row" style="margin:-6px 0 10px" data-sub="${i}" data-nobind><span class="shrink hint">${t("sub_offset")}</span>
        <input class="mono" data-k="offset" value="${esc(s.offset ?? "")}" placeholder="0" title="${esc(t("sub_offset_hint"))}"></div>`).join("")}
    <button class="small" id="add-sub" ${mediaOf("subtitle").length ? "" : "disabled"}>${t("add_sub")}</button>
    <h3>${t("captions")}</h3>
    <div class="row" style="margin:6px 0 4px" data-nobind>
      ${selectHtml("captions_file", [["", t("none")], ...mediaOf("subtitle").map((f) => [f, f.replace(/^media\//, "")])], cap.file || "", `id="cc-file" ${P().disc.standard === "PAL" ? "disabled" : ""}`)}</div>
    ${cap.file ? `<div class="row" style="margin:0 0 4px" data-nobind><span class="shrink hint">${t("sub_offset")}</span>
      <input class="mono" id="cc-offset" value="${esc(cap.offset ?? "")}" placeholder="0" title="${esc(t("sub_offset_hint"))}"></div>` : ""}
    <div class="hint">${esc(t(P().disc.standard === "PAL" ? "cc_pal" : "cc_hint"))}</div>
    <h3>${t("chapter_menu")}</h3>
    <label><input type="checkbox" id="cm-on" ${cm ? "checked" : ""}> ${t("chapter_menu_on")}</label>
    ${cm ? `<div style="margin-top:8px" data-nobind><label class="field"><span>BACK → </span>${selectHtml("back", [["__none__", t("auto")], ...actionOptions({ forButton: false, includeChapters: false })], (cm === true ? null : cm.back) || "__none__", 'id="cm-back"')}</label>
      <label class="field"><span>${t("motion_bg")}</span>${selectHtml("cmbg", [["__none__", t("none")], ...mediaOf("video").map((v) => [v, v])], (cm === true ? null : cm.background_video) || "__none__", 'id="cm-bgv"')}</label>
      <label><input type="checkbox" id="cm-anim" ${cm !== true && cm.animated_thumbnails ? "checked" : ""} ${cm !== true && cm.background_video ? "" : "disabled"}> ${t("animated_thumbs")}</label>
      ${[["title", "cm_heading", ti.name || ti.id], ["label_format", "cm_label_format", "Chapter {n}"], ["back_label", "cm_back_label", "BACK"],
        ["prev_label", "cm_prev_label", "PREV"], ["next_label", "cm_next_label", "NEXT"]].map(([k, l, ph]) =>
        `<label class="field"><span>${t(l)}</span><input data-cm="${k}" value="${esc(cm === true ? "" : cm[k] || "")}" placeholder="${esc(ph)}"></label>`).join("")}</div>` : ""}
    ${uopsHtml(ti, "title")}
    <h3></h3>${orderHtml(t("order_title"))}
    <h3></h3><button class="danger" id="del-title">${t("delete")}</button>`;
  const find = (p) => p.titles.find((x) => x.id === ti.id);
  bindFields(el, find, {
    numeric: ["audio.channels"],
    onAfter: (p, key, val) => {   // LPCM is stereo only; 2 (DTS: 6) is the default anyway
      const a = find(p).audio;
      if (a && (key === "audio.codec" && val === "lpcm" || key === "audio.channels" && val === (a.codec === "dts" ? 6 : 2))) delete a.channels;
      if (a && (key === "audio.codec" && (val === "lpcm" || val === "dts") || key === "audio.passthrough" && !val)) delete a.passthrough;
      if (a && key === "audio.codec" && val === "dts") delete a.bitrate;
    },
  });
  // the picture used as it is: nothing about its encoding applies
  const copy = el.querySelector("#ti-copy");
  if (copy) copy.onchange = () => commit((p) => {
    const x = find(p);
    if (copy.checked) { x.transcode = false; delete x.scan; delete x.video_bitrate; } else delete x.transcode;
  });
  el.querySelectorAll("[data-track]").forEach((row) => {
    const i = Number(row.dataset.track);
    row.querySelectorAll("[data-k]").forEach((inp) => inp.addEventListener("change", () => {
      commit((p) => {
        const tr = find(p).audio_tracks[i], k = inp.dataset.k;
        const v = k === "stream" ? Number(inp.value) : inp.value;
        if (v === "" || (k === "stream" && v === 0)) delete tr[k]; else tr[k] = v;
      });
    }));
  });
  el.querySelectorAll("[data-sub]").forEach((row) => {
    const i = Number(row.dataset.sub);
    row.querySelectorAll("[data-k]").forEach((inp) => inp.addEventListener("change", () => {
      commit((p) => {
        const list = find(p).subtitles, k = inp.dataset.k;
        if (k === "default") { list.forEach((s, j) => { if (j !== i) delete s.default; }); if (inp.checked) list[i].default = true; else delete list[i].default; }
        else if (k === "has_color") { if (inp.checked) list[i].color = "#FFFF00"; else delete list[i].color; }
        else if (k === "color") list[i].color = inp.value.toUpperCase();
        else if (k === "position" && inp.value === "bottom") delete list[i].position;
        else if (inp.value) list[i][k] = inp.value; else delete list[i][k];
      });
    }));
  });
  el.querySelectorAll("[data-del-track]").forEach((b) => (b.onclick = () => commit((p) => {
    const x = find(p); x.audio_tracks.splice(Number(b.dataset.delTrack), 1); if (!x.audio_tracks.length) delete x.audio_tracks;
  })));
  el.querySelectorAll("[data-del-sub]").forEach((b) => (b.onclick = () => commit((p) => {
    const x = find(p); x.subtitles.splice(Number(b.dataset.delSub), 1); if (!x.subtitles.length) delete x.subtitles;
  })));
  $("#add-track").onclick = () => commit((p) => { const x = find(p); x.audio_tracks = x.audio_tracks || [{}]; x.audio_tracks.push({}); });
  $("#add-sub").onclick = () => commit((p) => { const x = find(p); (x.subtitles = x.subtitles || []).push({ file: mediaOf("subtitle").find((f) => !/\.scc$/i.test(f)) }); });
  // closed captions: a file, or {file, offset}
  const ccSet = () => commit((p) => {
    const x = find(p), file = $("#cc-file").value, off = $("#cc-offset")?.value.trim();
    if (!file) delete x.captions;
    else x.captions = off ? { file, offset: off } : file;
  });
  $("#cc-file").onchange = ccSet;
  if ($("#cc-offset")) $("#cc-offset").onchange = ccSet;
  $("#cm-on").onchange = (e) => commit((p) => { const x = find(p); if (e.target.checked) x.auto_chapter_menu = true; else delete x.auto_chapter_menu; });
  const cmSet = (key, val) => commit((p) => {
    const x = find(p), spec = x.auto_chapter_menu === true ? {} : x.auto_chapter_menu;
    if (val === undefined || val === false) delete spec[key]; else spec[key] = val;
    if (key === "background_video" && val === undefined) delete spec.animated_thumbnails;
    x.auto_chapter_menu = Object.keys(spec).length ? spec : true;
  });
  if ($("#cm-bgv")) $("#cm-bgv").onchange = (e) => cmSet("background_video", e.target.value === "__none__" ? undefined : e.target.value);
  if ($("#cm-anim")) $("#cm-anim").onchange = (e) => cmSet("animated_thumbnails", e.target.checked || undefined);
  el.querySelectorAll("[data-cm]").forEach((inp) => (inp.onchange = () => cmSet(inp.dataset.cm, inp.value.trim() || undefined)));
  const back = $("#cm-back");
  if (back) back.addEventListener("change", () => {
    commit((p) => {
      const x = find(p); let spec = x.auto_chapter_menu === true ? {} : x.auto_chapter_menu;
      if (back.value === "__none__") delete spec.back; else spec.back = back.value;
      x.auto_chapter_menu = Object.keys(spec).length ? spec : true;
    });
  });
  $("#ti-id").onchange = (e) => {
    const nid = e.target.value.trim().replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 40);
    if (!nid || nid === ti.id || P().titles.some((x) => x.id === nid)) { e.target.value = ti.id; return; }
    commit((p) => { renameRefs(p, "title", ti.id, nid); find(p).id = nid; });
    S.sel.id = nid; renderAll();
  };
  bindUops(el, find);
  bindOrder(el, "titles", ti.id);
  $("#del-title").onclick = () => deleteItem("title", ti.id);
}

// ---------------------------------------------------------------- menus
const curMenu = () => (P().menus || []).find((x) => x.id === S.sel.id);
async function addMenu() {
  let list = [];
  try { list = (await api("/api/templates")).templates; } catch (e) { list = []; }
  openModal(`<h2>${t("new_menu")}</h2><div class="hint">${esc(t("template_hint"))}</div>
    <div class="template-list"><button class="template" data-template="">${esc(t("blank_menu"))}</button>
    ${list.map((x) => `<button class="template" data-template="${esc(x.id)}">${esc(x[LANG] || x.en)}</button>`).join("")}</div>
    <h3>${t("import_psd")}</h3><div class="hint">${esc(t("import_psd_hint"))}</div>
    ${mediaOf("design").length ? `<div class="row" style="margin-top:8px">${selectHtml("psd", mediaOf("design").map((x) => [x, x.replace(/^media\//, "")]), mediaOf("design")[0], 'id="psd-file"')}
      <button class="primary shrink" id="psd-go">${t("import")}</button></div>` : `<div class="hint">${esc(t("no_psd"))}</div>`}`);
  if ($("#psd-go")) $("#psd-go").onclick = () => {
    const path = $("#psd-file").value;
    const id = uniqueId(path.replace(/^.*\//, "").replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]+/g, "_").toLowerCase() || "menu", allMenuIds());
    closeModal(); importPsd(path, id);
  };
  document.querySelectorAll("[data-template]").forEach((b) => (b.onclick = async () => {
    closeModal();
    const id = uniqueId(b.dataset.template || "menu", allMenuIds());
    if (!b.dataset.template) return addBlankMenu(id);
    const first = (P().menus || [])[0];
    const r = await api("/api/template", { method: "POST", body: { template: b.dataset.template, id, project: S.project, back: first ? `menu:${first.id}` : null } });
    commit((p) => { (p.menus = p.menus || []).push(r.menu); });
    select("menu", id);
  }));
}
async function importPsd(path, id) {
  openModal(`<h2>${t("import_psd")}</h2><p class="hint">${esc(t("importing"))}</p>`);
  let r;
  try { r = await api("/api/import_psd", { method: "POST", body: { path, menu: id, project: S.project } }); }
  catch (e) { openModal(`<h2>${t("import_psd")}</h2><p>${esc(e.message)}</p>`); return; }
  S.media = r.media;
  commit((p) => {
    p.menus = p.menus || [];
    const i = p.menus.findIndex((x) => x.id === id);
    if (i >= 0) p.menus[i] = r.menu; else p.menus.push(r.menu);
  });
  S.preview = null;
  select("menu", id);
  openModal(`<h2>${t("import_psd")}</h2><p>${esc(t("imported_n", { n: r.menu.buttons.length }))}</p>
    ${r.notes.length ? `<ul class="issues">${r.notes.map((x) => `<li class="${x.level}">${esc(x.message)}</li>`).join("")}</ul>` : ""}
    <p class="hint">${esc(t("psd_actions_hint"))}</p>`);
}
function addBlankMenu(id) {
  const first = (P().titles || [])[0];
  commit((p) => {
    (p.menus = p.menus || []).push({ id, background_color: "#101820", texts: [{ text: "MY DISC", x: 80, y: 60, size: 48 }],
      buttons: [{ id: "play", label: "PLAY", x: 80, y: 200, action: first ? `title:${first.id}` : "stop" }] });
  });
  select("menu", id);
}
// ---------------------------------------------------------------- playlists
const curPlaylist = () => (P().playlists || []).find((x) => x.id === S.sel.id);
function addPlaylist() {
  const id = uniqueId("playlist", (P().playlists || []).map((x) => x.id));
  const first = (P().titles || [])[0];
  if (!first) return;
  commit((p) => { (p.playlists = p.playlists || []).push({ id, name: id, items: [first.id] }); });
  select("playlist", id);
}
function parseItem(s) {
  const m = /^(.+?)(?::(\d+)(?:-(\d+))?)?$/.exec(s);
  return { tid: m[1], a: m[2] ? Number(m[2]) : 1, b: m[2] ? Number(m[3] || m[2]) : 0 };   // b 0 = to the end
}
function itemString(tid, a, b, n) {
  if (a <= 1 && (b === 0 || b >= n)) return tid;
  if (b === 0 || b >= n) return `${tid}:${a}-${n}`;
  return a === b ? `${tid}:${a}` : `${tid}:${a}-${b}`;
}
function renderPlaylist(m) {
  const pl = curPlaylist();
  if (!pl) return select("disc");
  const titles = P().titles || [];
  const ends = actionOptions({ forButton: false, includeChapters: true, allowPlayAll: true, allowLast: true });
  m.innerHTML = `<div class="card" style="max-width:760px"><h2>${esc(pl.name || pl.id)}</h2>
    <label class="field"><span>${t("name")}</span><input data-k="name" value="${esc(pl.name || "")}"></label>
    <h3>${t("items")}</h3>
    ${pl.items.map((s, i) => {
      const it = parseItem(s), ti = titles.find((x) => x.id === it.tid), n = ti ? chaptersOf(ti).length : 1;
      const chs = Array.from({ length: n }, (_, k) => [String(k + 1), String(k + 1)]);
      return `<div class="row" style="margin:6px 0" data-item="${i}" data-nobind>
        <span class="n shrink" style="width:22px">${i + 1}</span>
        ${selectHtml("tid", titles.map((x) => [x.id, x.name || x.id]), it.tid)}
        <label class="shrink">${t("from_chapter")} ${selectHtml("a", chs, String(it.a), 'class="shrink"')}</label>
        <label class="shrink">${t("to_chapter")} ${selectHtml("b", [["0", t("to_end")], ...chs], String(it.b && it.b < n ? it.b : 0), 'class="shrink"')}</label>
        <button class="small shrink" data-item-move="-1" ${i ? "" : "disabled"}>▲</button>
        <button class="small shrink" data-item-move="1" ${i + 1 < pl.items.length ? "" : "disabled"}>▼</button>
        <button class="small danger shrink" data-item-del ${pl.items.length > 1 ? "" : "disabled"}>✕</button></div>`;
    }).join("")}
    <button class="small" id="add-item">${t("add_item")}</button>
    <label class="field" style="margin-top:12px"><span>${t("playlist_order")}</span>${selectHtml("order", [["sequential", t("order_sequential")], ["random", t("order_random")], ["shuffle", t("order_shuffle")]], pl.order || "sequential")}<div class="hint">${esc(t("order_hint"))}</div></label>
    <label class="field"><span>${t("playlist_end")}</span>${selectHtml("end_action", ends, pl.end_action || "stop")}</label>
    <h3></h3><button class="danger" id="del-playlist">${t("delete")}</button></div>`;
  const find = (p) => p.playlists.find((x) => x.id === pl.id);
  bindFields(m, find, { onAfter: (p, key, val) => {
    if (key === "end_action" && val === "stop") delete find(p).end_action;
    if (key === "order" && val === "sequential") delete find(p).order;
  } });
  m.querySelectorAll("[data-item]").forEach((row) => {
    const i = Number(row.dataset.item);
    const save = () => commit((p) => {
      const tid = row.querySelector("[data-k=tid]").value, ti = p.titles.find((x) => x.id === tid);
      const n = ti ? chaptersOf(ti).length : 1;
      let a = Number(row.querySelector("[data-k=a]").value), b = Number(row.querySelector("[data-k=b]").value);
      if (tid !== parseItem(pl.items[i]).tid) { a = 1; b = 0; }
      if (a > n) a = 1;
      if (b && b < a) b = a;
      find(p).items[i] = itemString(tid, a, b > n ? 0 : b, n);
    });
    row.querySelectorAll("select").forEach((sel) => (sel.onchange = save));
    row.querySelectorAll("[data-item-move]").forEach((b) => (b.onclick = () => commit((p) => {
      const l = find(p).items, j = i + Number(b.dataset.itemMove); [l[i], l[j]] = [l[j], l[i]];
    })));
    row.querySelector("[data-item-del]").onclick = () => commit((p) => { find(p).items.splice(i, 1); });
  });
  $("#add-item").onclick = () => commit((p) => { find(p).items.push(titles[0].id); });
  $("#del-playlist").onclick = () => deleteItem("playlist", pl.id);
}

function renderMenu(m) {
  const menu = curMenu();
  const gen = generatedMenus().find((g) => g.id === S.sel.id);
  if (!menu && !gen) return select("disc");
  const H = discH(), DW = displayW();
  const avail = Math.max(320, Math.min(m.clientWidth - 96, 1000));
  // zoom: fit the viewer, or a fixed size (100% = the menu as a TV shows it)
  const scale = S.menuZoom ? S.menuZoom : avail / DW, sx = DW / 720;
  const w = Math.round(DW * scale), h = Math.round(H * scale);
  if (gen) {
    const ti = P().titles.find((x) => x.id === gen.title);
    m.innerHTML = `<div class="card"><div class="hint">${esc(t("generated_menu", { t: ti?.name || gen.title }))}
      <button class="small" id="go-title">${t("go_to_title")}</button></div></div>
      <div class="stage-wrap"><div class="stage" style="width:${w}px;height:${h}px" id="stage"></div></div>`;
    $("#go-title").onclick = () => select("title", gen.title);
    requestPreview(gen.id, null, true);
    return;
  }
  let bg = "";
  if (menu.background_video) bg = `<img class="bg" src="${imgUrl("frame", { path: menu.background_video, t: 0, w: 960 })}" alt="">`;
  else if (menu.background) bg = `<img class="bg" src="${imgUrl("file", { path: menu.background })}" alt="">`;
  const defSize = menu.font_size || 32, defColor = menu.text_color || "#FFFFFF";
  const styleOf = (x) => ({ font: x.font, outline: x.outline, outline_width: x.outline_width || 2, shadow: x.shadow, shadow_offset: x.shadow_offset || 3 });
  const els = [
    ...(menu.shapes || []).map((x, i) => ({ kind: "shape", i, x: x.x, y: x.y, w: x.w, h: x.h, color: x.color || "#00000080", ...turnOf(x) })),
    ...(menu.images || []).map((x, i) => ({ kind: "image", i, x: x.x, y: x.y, w: x.w, h: x.h, file: x.file, opacity: x.opacity ?? 1, ...turnOf(x) })),
    ...(menu.texts || []).map((x, i) => ({ kind: "text", i, x: x.x, y: x.y, size: x.size || defSize, color: x.color || defColor, label: x.text, align: x.align, ls: x.line_spacing || 0, ...styleOf(x), ...turnOf(x) })),
    ...(menu.buttons || []).map((b, i) => ({ kind: "button", i, x: b.x, y: b.y, size: b.size || defSize, color: b.color || defColor, label: b.label || "", image: b.image, width: b.width, hl: !b.label && !b.image ? b.highlight_image : null, ...styleOf(b), ...turnOf(b) })),
  ].filter((e) => !menu[KIND_LIST[e.kind]][e.i].hidden && onPage(menu, menu[KIND_LIST[e.kind]][e.i]));   // (switched off in Layers; another page)
  // selection: S.sels (all selected), S.element (the one the inspector shows)
  if (!S.element) S.sels = [];
  else if (!(S.sels || []).some((x) => x.kind === S.element.kind && x.i === S.element.i)) S.sels = [S.element];
  const isSel = (e) => S.sels.some((x) => x.kind === e.kind && x.i === e.i);
  const shownBtns = (menu.buttons || []).map((b, i) => i).filter((i) => onPage(menu, menu.buttons[i]));
  const defBtn = (menu.buttons || []).findIndex((b) => b.id === menu.default_button);
  const firstBtn = shownBtns.includes(defBtn) ? defBtn : (shownBtns[0] ?? 0);
  const pg = curPage(menu), npg = pagesOf(menu);
  for (const e of els) if (e.font) loadFont(e.font);
  const css = (e) => {
    let st = `left:${e.x * sx * scale}px;top:${e.y * scale}px;${turnCss(e.rot, e.flip)}`;
    if (e.kind === "shape") return st + `width:${e.w * sx * scale}px;height:${e.h * scale}px;background:${cssColor(e.color)}`;
    if (e.kind === "image") return st + `width:${e.w * sx * scale}px;height:${e.h * scale}px;opacity:${e.opacity}`;
    st += `font-size:${e.size * scale}px;color:${esc(e.kind === "button" && e.i === firstBtn ? (menu.highlight_color || "#FFD400") : e.color)};`;
    if (e.font) st += `font-family:${fontFamily(e.font)},sans-serif;`;
    if (e.align) st += `text-align:${e.align};`;
    if (e.ls) st += `line-height:calc(1em + ${e.ls * scale}px);`;
    const sh = [];
    if (e.outline) { const o = Math.max(1, e.outline_width * scale); for (const [dx, dy] of [[o, 0], [-o, 0], [0, o], [0, -o], [o, o], [-o, -o], [o, -o], [-o, o]]) sh.push(`${dx}px ${dy}px 0 ${cssColor(e.outline)}`); }
    if (e.shadow) sh.push(`${e.shadow_offset * scale}px ${e.shadow_offset * scale}px 0 ${cssColor(e.shadow)}`);
    if (sh.length) st += `text-shadow:${sh.join(",")};`;
    return st;
  };
  const tool = S.tool || "select";
  const zoomSel = selectHtml("zoom", [["fit", t("zoom_fit")], ["0.5", "50%"], ["1", "100%"], ["1.5", "150%"], ["2", "200%"], ["3", "300%"]], S.menuZoom ? String(S.menuZoom) : "fit", 'id="zoom" class="shrink" title="' + esc(t("zoom_hint")) + '"');
  m.innerHTML = `<div class="menu-viewer">
    <div class="viewer-main">
    ${S.psdChanged === menu.id ? `<div class="notice" id="psd-changed">${esc(t("psd_changed"))} <button class="small" id="psd-reimport">${t("reimport")}</button></div>` : ""}
    ${S.sels.length > 1 ? `<div class="stage-tools align-tools">${t("align")}:
      ${[["left", "⇤"], ["hcenter", "↔"], ["right", "⇥"], ["top", "⤒"], ["vcenter", "↕"], ["bottom", "⤓"]].map(([k, i]) => `<button class="small" data-align="${k}" title="${esc(t("align_" + k))}">${i}</button>`).join("")}
      ${S.sels.length > 2 ? `<button class="small" data-distribute="h" title="${esc(t("distribute_h"))}">⇹</button><button class="small" data-distribute="v" title="${esc(t("distribute_v"))}">⇳</button>` : ""}
      <span class="hint">${esc(t("n_selected", { n: S.sels.length }))}</span></div>` : ""}
    <div class="stage-wrap"><div class="stage" id="stage" tabindex="0" style="width:${w}px;height:${h}px;background:${esc(menu.background_color || "#000")}">
      ${bg}
      ${S.showGuides === false ? "" : guidesHtml(menu, scale, sx, "uguide")}
      ${S.showSafe ? `<div class="safe" style="left:${w * 0.05}px;top:${h * 0.05}px;width:${w * 0.9}px;height:${h * 0.9}px"></div>` : ""}
      ${(menu.buttons || []).filter((b) => b.thumbnail && !b.hidden && onPage(menu, b)).map((b) => {
        const th = b.thumbnail, src = thumbSrc(b);
        return `<div class="thumb-pv" style="left:${th.x * sx * scale}px;top:${th.y * scale}px;width:${th.w * sx * scale}px;height:${th.h * scale}px">${src ? `<img src="${src}" alt="" draggable="false">` : ""}</div>`;
      }).join("")}
      ${els.map((e) => `<div class="el ${e.kind} ${isSel(e) ? "selected" : ""} ${e.kind === "button" && e.i === firstBtn ? "highlight" : ""}"
          data-kind="${e.kind}" data-i="${e.i}" style="${css(e)}">${e.kind === "shape" ? "" : e.kind === "image"
            ? `<img src="${imgUrl("file", { path: e.file })}" alt="" draggable="false" style="display:block;width:100%;height:100%">`
            : e.hl
            ? `<img class="area" src="${imgUrl("file", { path: e.hl })}" alt="" draggable="false" style="display:block;width:${(e.width || 160) * sx * scale}px;${e.i === firstBtn ? `filter:drop-shadow(0 0 0 ${esc(menu.highlight_color || "#FFD400")});opacity:.9` : "opacity:.35"}">`
            : e.image
            ? `<img src="${imgUrl("file", { path: e.image })}" alt="${esc(e.label)}" draggable="false" style="display:block;width:${(e.width || 160) * sx * scale}px${e.i === firstBtn ? `;outline:2px solid ${esc(menu.highlight_color || "#FFD400")}` : ""}">`
            : esc(e.label)}</div>`).join("")}
      <div class="guide gx" hidden></div><div class="guide gy" hidden></div>
      ${S.showGuides === false ? "" : guidesHtml(menu, scale, sx, "uline")}
    </div></div>
    <div class="viewer-bar">
      <span class="seg pages" title="${esc(t("pages_hint"))}"><span class="seg-label">${t("pages")}</span>${Array.from({ length: npg }, (_, i) => `<button class="small ${pg === i + 1 ? "on" : ""}" data-page="${i + 1}">${i + 1}</button>`).join("")}<button class="small" id="add-page" title="${esc(t("cmd_add_page"))}">+</button></span>
      ${zoomSel}
      <label title="${esc(t("safe_hint"))}"><input type="checkbox" id="safe" ${S.showSafe ? "checked" : ""}> ${t("safe_area")}</label>
      <label title="${esc(t("routing_hint"))}"><input type="checkbox" id="routing" ${S.showRouting ? "checked" : ""}> ${t("routing")}</label>
      <label><input type="checkbox" id="snap" ${S.snap === false ? "" : "checked"}> ${t("snap")}</label>
      <label title="${esc(t("guide_hint"))}"><input type="checkbox" id="show-guides" ${S.showGuides === false ? "" : "checked"}> ${t("guides")}</label>
      <button class="small" id="new-guide" title="${esc(t("cmd_new_guide"))}">${t("new_guide")}</button>
      <span class="seg" title="${esc(t("subpictures_hint"))}"><span class="seg-label">${t("subpictures")}</span>${[["normal", "sp_normal"], ["highlight", "sp_selected"], ["select", "sp_activated"]].map(([k, l]) => `<button class="small ${S.spView === k ? "on" : ""}" data-sp="${k}">${t(l)}</button>`).join("")}</span>
      <span class="spacer"></span>
      <button id="exact" class="small ${S.preview && !S.spView ? "" : "primary"}">${S.preview && !S.spView ? t("hide_preview") : t("exact_preview")}</button>
    </div>
    <div class="hint" style="text-align:center;margin-top:6px">${w}×${h} · 720×${H} DVD px · ${esc(P().disc.aspect)} · ${esc(t("stage_keys"))}</div>
    <div class="hint" style="text-align:center">${esc(t("link_hint"))}</div>
    </div></div>`;
  if ($("#psd-reimport")) $("#psd-reimport").onclick = () => { S.psdChanged = null; importPsd(menu.psd, menu.id); };
  m.querySelectorAll("[data-page]").forEach((b) => (b.onclick = () => showPage(menu, Number(b.dataset.page))));
  $("#add-page").onclick = addPage;
  const stage = $("#stage");
  const nodeOf = (k) => stage.querySelector(`.el[data-kind="${k.kind}"][data-i="${k.i}"]`);
  // element boxes on the 720-wide grid (texts measured from the page)
  const box = (k) => {
    const n = nodeOf(k), e = els.find((x) => x.kind === k.kind && x.i === k.i);
    const sized = e.kind === "shape" || e.kind === "image";
    const bw = sized ? e.w : n.offsetWidth / scale / sx, bh = sized ? e.h : n.offsetHeight / scale;
    return { x: e.x, y: e.y, w: bw, h: bh };
  };
  const listOf = elementList;
  stage.querySelectorAll(".el").forEach((node) => {
    node.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      stage.focus();
      const k = { kind: node.dataset.kind, i: Number(node.dataset.i) };
      if (ev.shiftKey || ev.metaKey || ev.ctrlKey) {
        const on = isSel(k);
        S.sels = on ? S.sels.filter((x) => !(x.kind === k.kind && x.i === k.i)) : [...S.sels, k];
        S.element = S.sels[S.sels.length - 1] || null;
        renderMain(); renderInspector();
        return;
      }
      const changedSel = !isSel(k) && S.sels.length > 1;
      if (!isSel(k)) S.sels = [k];
      S.element = k;
      stage.querySelectorAll(".el.selected").forEach((n) => n.classList.remove("selected"));
      S.sels.forEach((x) => nodeOf(x)?.classList.add("selected"));
      renderInspector();
      if (tool === "rotate") return rotateDrag(ev, node, menu, S.sels.map((x) => ({ k: x, node: nodeOf(x) })));
      // drag every selected element; snap the grabbed one to the others' edges / centres
      const group = S.sels.map((x) => ({ k: x, b: box(x), node: nodeOf(x) }));
      const me = group.find((g) => g.k.kind === k.kind && g.k.i === k.i).b;
      const others = els.filter((e) => !isSel(e)).map((e) => box(e));
      // snap lines: the other objects and the safe area (Snap), the guides (Snap to guides)
      const objs = S.snap !== false, gd = S.snapGuides !== false ? (menu.guides || {}) : {};
      const vx = [...(objs ? [0, 360, 720, 36, 684, ...others.flatMap((o) => [o.x, o.x + o.w / 2, o.x + o.w])] : []), ...(gd.vertical || [])];
      const vy = [...(objs ? [0, H / 2, H, H * 0.05, H * 0.95, ...others.flatMap((o) => [o.y, o.y + o.h / 2, o.y + o.h])] : []), ...(gd.horizontal || [])];
      const gx = stage.querySelector(".gx"), gy = stage.querySelector(".gy");
      const startX = ev.clientX, startY = ev.clientY;
      let dx = 0, dy = 0;
      node.setPointerCapture(ev.pointerId);
      const snapTo = (pos, size, lines) => {
        let best = null;
        for (const [off] of [[0], [size / 2], [size]]) for (const l of lines) {
          const d = l - (pos + off);
          if (Math.abs(d) <= 6 && (!best || Math.abs(d) < Math.abs(best.d))) best = { d, l };
        }
        return best;
      };
      const move = (e2) => {
        dx = Math.round((e2.clientX - startX) / scale / sx); dy = Math.round((e2.clientY - startY) / scale);
        gx.hidden = gy.hidden = true;
        if (!e2.altKey) {
          const sxp = snapTo(me.x + dx, me.w, vx), syp = snapTo(me.y + dy, me.h, vy);
          if (sxp) { dx += Math.round(sxp.d); gx.hidden = false; gx.style.left = sxp.l * sx * scale + "px"; }
          if (syp) { dy += Math.round(syp.d); gy.hidden = false; gy.style.top = syp.l * scale + "px"; }
        }
        for (const g of group) {
          const nx = Math.max(0, Math.min(719, g.b.x + dx)), ny = Math.max(0, Math.min(H - 1, g.b.y + dy));
          g.node.style.left = nx * sx * scale + "px"; g.node.style.top = ny * scale + "px";
        }
      };
      const up = () => {
        node.removeEventListener("pointermove", move); node.removeEventListener("pointerup", up);
        gx.hidden = gy.hidden = true;
        if (!dx && !dy && S.sels.length > 1) { S.sels = [k]; S.element = k; renderMain(); renderInspector(); return; }
        if (!dx && !dy && changedSel) { renderMain(); return; }      // the align bar goes away
        if (dx || dy) commit((p) => {
          const mm = p.menus.find((x) => x.id === menu.id);
          for (const g of group) {
            const it = listOf(mm, g.k.kind)[g.k.i];
            it.x = Math.max(0, Math.min(719, Math.round(g.b.x + dx))); it.y = Math.max(0, Math.min(H - 1, Math.round(g.b.y + dy)));
          }
        });
      };
      node.addEventListener("pointermove", move); node.addEventListener("pointerup", up);
    });
  });
  stage.addEventListener("pointerdown", (ev) => {
    const empty = ev.target === stage || ev.target.classList.contains("bg");
    const r = stage.getBoundingClientRect();
    const px = Math.round((ev.clientX - r.left) / scale / sx), py = Math.round((ev.clientY - r.top) / scale);
    if ((S.tool || "select") === "zoom") {
      const steps = [0.5, 1, 1.5, 2, 3], cur = S.menuZoom || scale;
      S.menuZoom = ev.altKey ? (steps.filter((z) => z < cur - 0.01).pop() || 0.5) : (steps.find((z) => z > cur + 0.01) || 3);
      renderMain();
      return;
    }
    if (S.tool === "text" && empty) {
      S.tool = "select";                    // one text per click, as with a text tool
      commit((p) => {
        const mm = p.menus.find((x) => x.id === menu.id);
        (mm.texts = mm.texts || []).push({ text: "TEXT", x: Math.max(0, Math.min(700, px)), y: Math.max(0, Math.min(H - 20, py)), ...newOnPage(menu) });
        S.element = { kind: "text", i: mm.texts.length - 1 }; S.sels = [S.element];
      });
      setTimeout(() => { const f = $("#inspector [data-k=text]"); if (f) { f.focus(); f.select?.(); } }, 0);
      return;
    }
    if (empty) { S.element = null; S.sels = []; renderMain(); renderInspector(); }
  });
  // align / distribute the selection (also Object > Align and Distribute)
  const arrange = (fn) => commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    const items = S.sels.map((k) => ({ k, b: box(k), it: listOf(mm, k.kind)[k.i] }));
    fn(items);
    for (const x of items) { x.it.x = Math.max(0, Math.min(719, Math.round(x.it.x))); x.it.y = Math.max(0, Math.min(H - 1, Math.round(x.it.y))); }
  });
  S.stageOps = {
    menu: menu.id,
    align: (a) => arrange((items) => alignItems(items, a, H)),
    distribute: (d) => arrange((items) => distributeItems(items, d === "h")),
  };
  m.querySelectorAll("[data-align]").forEach((b) => (b.onclick = () => S.stageOps.align(b.dataset.align)));
  m.querySelectorAll("[data-distribute]").forEach((b) => (b.onclick = () => S.stageOps.distribute(b.dataset.distribute)));
  $("#safe").onchange = (e) => { S.showSafe = e.target.checked; renderMain(); };
  $("#snap").onchange = (e) => { S.snap = e.target.checked; };
  $("#show-guides").onchange = (e) => { S.showGuides = e.target.checked; renderMain(); };
  $("#new-guide").onclick = newGuideBox;
  bindGuides(stage, menu, scale, sx);
  $("#routing").onchange = (e) => { S.showRouting = e.target.checked; renderMain(); };
  if (S.showRouting) drawRouting(stage, menu, scale, sx);
  bindLinkDrop(stage, menu, scale, sx);
  $("#zoom").onchange = (e) => { S.menuZoom = e.target.value === "fit" ? null : Number(e.target.value); renderMain(); };
  m.querySelectorAll("[data-sp]").forEach((b) => (b.onclick = () => {
    if (S.spView === b.dataset.sp) { S.spView = null; S.preview = null; renderMain(); return; }
    S.spView = b.dataset.sp; S.preview = null;
    requestPreview(pageId(menu), null, false, { every: true, state: b.dataset.sp });
    renderMain();
  }));
  $("#exact").onclick = () => { S.spView = null; if (S.preview) { S.preview = null; renderMain(); } else requestPreview(pageId(menu), S.element && S.element.kind === "button" ? menu.buttons[S.element.i].id : null); };
  if (S.preview && S.previewFor === pageId(menu)) drawPreview();
  stage.classList.toggle("tool-text", tool === "text");
  stage.classList.toggle("tool-zoom", tool === "zoom");
  stage.classList.toggle("tool-rotate", tool === "rotate");
  checkOverlaps(stage, menu, scale, sx);
}
// -- rotate and flip --------------------------------------------------------------
// An object's rotation (degrees clockwise about its centre) and flip (made
// first) as the project keeps them; the stage shows them with a CSS
// transform, the disc renderer draws them the same way.
const turnOf = (x) => ({ rot: Number(x.rotate) || 0, flip: x.flip || null });
const flipBits = (f) => ({ h: f === "horizontal" || f === "both", v: f === "vertical" || f === "both" });
const flipName = (h, v) => (h && v ? "both" : h ? "horizontal" : v ? "vertical" : null);
function turnCss(rot, flip) {
  if (!rot && !flip) return "";
  const b = flipBits(flip);
  return `transform:rotate(${rot}deg) scale(${b.h ? -1 : 1},${b.v ? -1 : 1});transform-origin:50% 50%;`;
}
function setTurn(o, rot, flip) {
  const r = Math.round(((Number(rot) % 360) + 360) % 360 * 10) / 10;
  if (r) o.rotate = r; else delete o.rotate;
  if (flip) o.flip = flip; else delete o.flip;
}
// Object > Rotate: turn every selected object by `deg`
function turnElements(deg) {
  const ks = selElements(), id = S.sel.id;
  commit((p) => {
    const mm = p.menus.find((x) => x.id === id);
    for (const k of ks) { const o = elementList(mm, k.kind)[k.i]; setTurn(o, (Number(o.rotate) || 0) + deg, o.flip); }
  });
}
// Object > Flip: mirrored on the screen's axis; as the flip is made before
// the turn, a turned object flipped this way also turns the other way
function flipElements(axis) {
  const ks = selElements(), id = S.sel.id;
  commit((p) => {
    const mm = p.menus.find((x) => x.id === id);
    for (const k of ks) {
      const o = elementList(mm, k.kind)[k.i], b = flipBits(o.flip);
      b[axis] = !b[axis];
      setTurn(o, -(Number(o.rotate) || 0), flipName(b.h, b.v));
    }
  });
}
// the Rotate tool: drag around the objects' centres (Shift: 45° steps)
function rotateDrag(ev, node, menu, group) {
  const r = node.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const angle = (e) => Math.atan2(e.clientY - cy, e.clientX - cx) * 180 / Math.PI;
  const start = angle(ev), list = (k) => elementList(menu, k.kind)[k.i];
  const base = group.map((g) => ({ ...g, rot: Number(list(g.k).rotate) || 0, flip: list(g.k).flip }));
  let delta = 0;
  node.setPointerCapture(ev.pointerId);
  const move = (e) => {
    delta = angle(e) - start;
    for (const g of base) {
      let a = g.rot + delta;
      if (e.shiftKey) a = Math.round(a / 45) * 45;
      g.now = a;
      const keep = g.node.style.cssText.replace(/transform[^;]*;/g, "");
      g.node.style.cssText = keep + turnCss(a, g.flip);
    }
  };
  const up = () => {
    node.removeEventListener("pointermove", move); node.removeEventListener("pointerup", up);
    if (!delta) return;
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const g of base) { const o = elementList(mm, g.k.kind)[g.k.i]; setTurn(o, g.now ?? g.rot, o.flip); }
    });
  };
  node.addEventListener("pointermove", move); node.addEventListener("pointerup", up);
}
function transformHtml(it, kind) {
  return `<h3>${t("transform")}</h3><div class="grid2" data-nobind>
    <label class="field"><span>${t("rotation")}</span><input type="number" id="tf-rot" min="-360" max="360" step="1" value="${Number(it.rotate) || 0}"></label>
    <label class="field"><span>${t("flip")}</span>${selectHtml("tf-flip", [["__none__", t("flip_none")], ["horizontal", t("flip_horizontal")], ["vertical", t("flip_vertical")], ["both", t("flip_both")]], it.flip || "__none__", 'id="tf-flip"')}</label>
  </div>${kind === "button" && it.thumbnail ? `<div class="hint">${esc(t("transform_thumb_hint"))}</div>` : ""}`;
}
function bindTransform(el, get) {
  const set = () => commit((p) => { const f = $("#tf-flip").value; setTurn(get(p), $("#tf-rot").value, f === "__none__" ? null : f); });
  if ($("#tf-rot")) { $("#tf-rot").onchange = set; $("#tf-flip").onchange = set; }
}
// -- guides --------------------------------------------------------------------
// Lines at pixel positions of the menu (on its 720-wide grid) for placing
// objects: kept with the menu (menus[].guides), never on the disc.
const guideCount = (m) => ((m?.guides?.horizontal || []).length + (m?.guides?.vertical || []).length);
// Each guide is drawn twice: the line over everything (it takes no clicks),
// and a band to grab it under the objects, so an object on a guide is still
// picked where it covers it, and the guide wherever it shows.
function guidesHtml(menu, scale, sx, part) {
  const g = menu.guides || {}, lock = S.lockGuides ? " locked" : "";
  const tip = (k, v) => (part === "uguide" ? ` title="${esc(t(k === "horizontal" ? "guide_horizontal" : "guide_vertical"))} ${v}"` : "");
  return [...(g.horizontal || []).map((y, i) => `<div class="${part} h${lock}" data-g="horizontal" data-gi="${i}" style="top:${y * scale}px"${tip("horizontal", y)}></div>`),
    ...(g.vertical || []).map((x, i) => `<div class="${part} v${lock}" data-g="vertical" data-gi="${i}" style="left:${x * sx * scale}px"${tip("vertical", x)}></div>`)].join("");
}
function setGuides(p, id, fn) {
  const mm = p.menus.find((x) => x.id === id), g = mm.guides || {};
  const out = { horizontal: [...(g.horizontal || [])], vertical: [...(g.vertical || [])] };
  fn(out);
  for (const k of ["horizontal", "vertical"]) { out[k] = [...new Set(out[k])].sort((a, b) => a - b); if (!out[k].length) delete out[k]; }
  if (Object.keys(out).length) mm.guides = out; else delete mm.guides;
}
// drag a guide to move it, off the menu to remove it (not while locked)
function bindGuides(stage, menu, scale, sx) {
  const H = discH();
  stage.querySelectorAll(".uguide").forEach((node) => node.addEventListener("pointerdown", (ev) => {
    if (S.lockGuides || (S.tool || "select") !== "select") return;
    ev.preventDefault(); ev.stopPropagation();
    const kind = node.dataset.g, i = Number(node.dataset.gi), r = stage.getBoundingClientRect();
    const line = stage.querySelector(`.uline[data-g="${kind}"][data-gi="${i}"]`), both = [node, line].filter(Boolean);
    const pos = (e) => (kind === "horizontal" ? (e.clientY - r.top) / scale : (e.clientX - r.left) / scale / sx);
    const max = kind === "horizontal" ? H : 720, from = menu.guides[kind][i], grab = pos(ev);
    let now = null;
    node.setPointerCapture(ev.pointerId);
    const move = (e) => {
      now = Math.round(from + pos(e) - grab);
      const off = now < 0 || now > max;
      for (const n of both) {
        n.classList.toggle("leaving", off);
        if (kind === "horizontal") n.style.top = Math.max(0, Math.min(H, now)) * scale + "px";
        else n.style.left = Math.max(0, Math.min(720, now)) * sx * scale + "px";
      }
    };
    const up = () => {
      node.removeEventListener("pointermove", move); node.removeEventListener("pointerup", up);
      if (now === null) return;
      commit((p) => setGuides(p, menu.id, (g) => { g[kind].splice(i, 1); if (now >= 0 && now <= max) g[kind].push(now); }));
    };
    node.addEventListener("pointermove", move); node.addEventListener("pointerup", up);
  }));
}
function clearGuides() {
  const id = S.sel.id;
  commit((p) => setGuides(p, id, (g) => { g.horizontal = []; g.vertical = []; }));
}
// View > New Guide: its direction and its position in pixels
function newGuideBox() {
  const id = S.sel.id, H = discH();
  openModal(`<h2>${t("new_guide")}</h2><div class="hint">${esc(t("guide_hint"))}</div>
    <label class="field"><span></span><label><input type="radio" name="gdir" value="horizontal" checked> ${t("guide_horizontal")}</label>
      <label><input type="radio" name="gdir" value="vertical"> ${t("guide_vertical")}</label></label>
    <label class="field"><span>${t("guide_position")}</span><input type="number" id="g-pos" min="0" max="720" value="${Math.round(H / 2)}"></label>
    <div class="actions"><button id="m-cancel">${t("cancel")}</button><button class="primary" id="m-ok">${t("ok")}</button></div>`);
  $("#m-cancel").onclick = closeModal;
  $("#m-ok").onclick = () => {
    const kind = $("input[name=gdir]:checked").value, max = kind === "horizontal" ? H : 720;
    const v = Math.max(0, Math.min(max, Math.round(Number($("#g-pos").value) || 0)));
    closeModal();
    S.showGuides = true;
    commit((p) => setGuides(p, id, (g) => g[kind].push(v)));
  };
  setTimeout(() => $("#g-pos")?.select(), 0);
}
// The menu's colour set: the buttons' subpicture colours in the three states
// a player shows (Normal = not selected, optional; Selected; Activated), each
// with an opacity (a DVD has 16 levels). Stored as #RRGGBB or #RRGGBBAA.
const COLOUR_SET = [["normal_color", "cs_normal", null], ["highlight_color", "highlight", "#FFD400"], ["select_color", "select_color", "#FF5A00"]];
const splitColour = (v, def) => {
  const s = String(v || def || "#FFFFFF").replace("#", "");
  return { rgb: "#" + s.slice(0, 6).toLowerCase(), pct: s.length === 8 ? Math.round(parseInt(s.slice(6), 16) / 255 * 100) : 100 };
};
const joinColour = (rgb, pct) => rgb.toUpperCase() + (pct >= 100 ? "" : Math.round(pct / 100 * 255).toString(16).padStart(2, "0").toUpperCase());
function colourSetHtml(menu) {
  return `<h3>${t("colour_set")}</h3>${COLOUR_SET.map(([k, l, def]) => {
    const on = def || menu[k], c = splitColour(menu[k], def || "#FFFFFF66");
    return `<label class="field" data-nobind><span>${t(l)}</span><div class="row cset">
      ${def ? "" : `<input type="checkbox" class="shrink" data-cs-on="${k}" ${menu[k] ? "checked" : ""} title="${esc(t("cs_normal_hint"))}">`}
      <input type="color" class="shrink" data-cs="${k}" value="${c.rgb}" ${on ? "" : "disabled"}>
      <input type="range" min="0" max="100" step="1" data-cs-a="${k}" value="${c.pct}" ${on ? "" : "disabled"} title="${esc(t("opacity"))}">
      <span class="shrink pct mono" data-cs-p="${k}">${c.pct}%</span></div></label>`;
  }).join("")}<div class="hint">${esc(t("cs_hint"))}</div>`;
}
function bindColourSet(root, menu) {
  const write = (k) => {
    const on = root.querySelector(`[data-cs-on="${k}"]`);
    const rgb = root.querySelector(`[data-cs="${k}"]`).value, pct = Number(root.querySelector(`[data-cs-a="${k}"]`).value);
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      if (on && !on.checked) delete mm[k]; else mm[k] = joinColour(rgb, pct);
    });
    S.preview = null; renderMain();
  };
  root.querySelectorAll("[data-cs]").forEach((x) => (x.onchange = () => write(x.dataset.cs)));
  root.querySelectorAll("[data-cs-a]").forEach((x) => {
    x.oninput = () => { root.querySelector(`[data-cs-p="${x.dataset.csA}"]`).textContent = `${x.value}%`; };
    x.onchange = () => write(x.dataset.csA);
  });
  root.querySelectorAll("[data-cs-on]").forEach((x) => (x.onchange = () => write(x.dataset.csOn)));
}
// Align: to each other, or one element alone to the safe area (the dashed
// frame, 5% in from the edges)
function alignItems(items, a, H) {
  const alone = items.length === 1;
  const L = alone ? 36 : Math.min(...items.map((x) => x.b.x)), R = alone ? 684 : Math.max(...items.map((x) => x.b.x + x.b.w));
  const T = alone ? Math.round(H * 0.05) : Math.min(...items.map((x) => x.b.y)), B = alone ? Math.round(H * 0.95) : Math.max(...items.map((x) => x.b.y + x.b.h));
  for (const x of items) {
    if (a === "left") x.it.x = L;
    if (a === "right") x.it.x = R - x.b.w;
    if (a === "hcenter") x.it.x = (L + R) / 2 - x.b.w / 2;
    if (a === "top") x.it.y = T;
    if (a === "bottom") x.it.y = B - x.b.h;
    if (a === "vcenter") x.it.y = (T + B) / 2 - x.b.h / 2;
  }
}
function distributeItems(items, hz) {
  const pos = (x) => (hz ? x.b.x : x.b.y), size = (x) => (hz ? x.b.w : x.b.h);
  items.sort((p, q) => pos(p) - pos(q));
  const first = items[0], last = items[items.length - 1];
  const gap = (pos(last) + size(last) - pos(first) - items.reduce((s, x) => s + size(x), 0)) / (items.length - 1);
  let at = pos(first);
  for (const x of items) { if (hz) x.it.x = at; else x.it.y = at; at += size(x) + gap; }
}
// new button / rectangle on the open menu (Tools panel)
function addMenuButton() {
  const menu = curMenu();
  if (!menu) return;
  const H = discH();
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    const id = uniqueId("button", mm.buttons.map((b) => b.id));
    const last = mm.buttons.filter((b) => onPage(menu, b)).pop();      // (of the page shown)
    mm.buttons.push({ id, label: "BUTTON", x: last ? last.x : 80, y: last ? Math.min(H - 40, last.y + 60) : 200, action: "stop", ...newOnPage(menu) });
    S.element = { kind: "button", i: mm.buttons.length - 1 }; S.sels = [S.element];
  });
}
function addMenuShape() {
  const menu = curMenu();
  if (!menu) return;
  const H = discH();
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    (mm.shapes = mm.shapes || []).push({ x: 60, y: Math.round(H * 0.7), w: 600, h: 60, color: "#00000080", ...newOnPage(menu) });
    S.element = { kind: "shape", i: mm.shapes.length - 1 }; S.sels = [S.element];
  });
}
// a picture on the menu: its natural size (square pixels), at most half the frame
function pickMenuPicture() {
  const imgs = mediaOf("image");
  if (!imgs.length) return alert(t("pick_picture"));
  openModal(`<h2>${t("add_picture")}</h2><p class="hint">${esc(t("picture_hint"))}</p>
    <div class="lib-grid">${imgs.map((x) => `<button class="lib-item" data-pic="${esc(x)}"><img src="${imgUrl("file", { path: x })}" alt=""><span>${esc(x.replace(/^media\//, ""))}</span></button>`).join("")}</div>`);
  document.querySelectorAll("[data-pic]").forEach((b) => (b.onclick = () => { closeModal(); placeMenuPicture(b.dataset.pic); }));
}
function placeMenuPicture(path) {
  const menu = curMenu();
  if (!menu) return;
  const H = discH(), sx = displayW() / 720, im = new Image();
  im.onload = () => {
    let w = im.naturalWidth / sx, h = im.naturalHeight;
    const k = Math.min(1, 360 / w, (H / 2) / h);
    w = Math.max(1, Math.round(w * k)); h = Math.max(1, Math.round(h * k));
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      (mm.images = mm.images || []).push({ file: path, x: Math.round((720 - w) / 2), y: Math.round((H - h) / 2), w, h, ...newOnPage(menu) });
      S.element = { kind: "image", i: mm.images.length - 1 }; S.sels = [S.element];
    });
  };
  im.src = imgUrl("file", { path });
}
// keyboard editing on the menu stage: arrows nudge (Shift: 10 px), Delete,
// Cmd/Ctrl+D duplicate, Cmd/Ctrl+C / V copy and paste
function stageKeys(ev) {
  if (S.element && !S.sels?.length) S.sels = [S.element];
  if (S.sel.view !== "menu" || !S.sels?.length || ev.target.closest?.("input, textarea, select")) return;
  const menu = curMenu();
  if (!menu) return;
  const mod = ev.metaKey || ev.ctrlKey, H = discH();
  const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  if (arrows[ev.key] && !mod) {
    ev.preventDefault();
    const [ax, ay] = arrows[ev.key], n = ev.shiftKey ? 10 : 1;
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const k of S.sels) { const it = elementList(mm, k.kind)[k.i]; it.x = Math.max(0, Math.min(719, it.x + ax * n)); it.y = Math.max(0, Math.min(H - 1, it.y + ay * n)); }
    });
  } else if ((ev.key === "Delete" || ev.key === "Backspace") && !mod) {
    ev.preventDefault();
    deleteElements();
  } else if (mod && (ev.key === "c" || ev.key === "C")) {
    copyElements();
  } else if (mod && (ev.key === "d" || ev.key === "D" || ev.key === "v" || ev.key === "V")) {
    if (duplicateElements(ev.key.toLowerCase() === "v")) ev.preventDefault();
  }
}
// the selected elements of the menu being edited (stage, layers, menu bar)
const KIND_LIST = { button: "buttons", text: "texts", shape: "shapes", image: "images" };
const elementList = (mm, kind) => (mm[KIND_LIST[kind]] = mm[KIND_LIST[kind]] || []);
const hasElements = () => S.sel.view === "menu" && !!curMenu() && !!(S.sels?.length || S.element);
function deleteElements() {
  const menu = curMenu();
  if (!menu || !hasElements()) return false;
  const sels = S.sels?.length ? S.sels : [S.element];
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    for (const k of [...sels].sort((a, b) => b.i - a.i)) {
      const l = elementList(mm, k.kind);
      if (k.kind === "button" && l.length <= 1) continue;     // a menu keeps one button
      l.splice(k.i, 1);
    }
    S.element = null; S.sels = [];
  });
  return true;
}
function copyElements() {
  const menu = curMenu();
  if (!menu || !hasElements()) return false;
  const sels = S.sels?.length ? S.sels : [S.element];
  S.clip = sels.map((k) => ({ kind: k.kind, it: JSON.parse(JSON.stringify(elementList(menu, k.kind)[k.i])) }));
  return true;
}
function duplicateElements(fromClipboard) {
  const menu = curMenu();
  if (!menu) return false;
  const sels = S.sels?.length ? S.sels : S.element ? [S.element] : [];
  const src = fromClipboard ? S.clip : sels.map((k) => ({ kind: k.kind, it: elementList(menu, k.kind)[k.i] }));
  if (!src?.length) return false;
  const H = discH();
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id), added = [];
    for (const { kind, it } of src) {
      const c = JSON.parse(JSON.stringify(it));
      c.x = Math.min(719, c.x + 12); c.y = Math.min(H - 1, c.y + 12);
      if (kind === "button") { c.id = uniqueId(c.id.replace(/\d+$/, "") || "button", mm.buttons.map((b) => b.id)); delete c.nav; }
      if (pagesOf(mm) < 2) delete c.page; else if (c.page) c.page = curPage(menu);   // (pasted on the page shown)
      const l = elementList(mm, kind); l.push(c); added.push({ kind, i: l.length - 1 });
    }
    S.sels = added; S.element = added[added.length - 1];
  });
  return true;
}
// menu fonts in the editor: load the element's font file so the stage looks right
const loadedFonts = new Set();
const fontFamily = (path) => `"om-${path.replace(/[^A-Za-z0-9]/g, "_")}"`;
function loadFont(path) {
  if (loadedFonts.has(path) || typeof FontFace === "undefined") return;
  loadedFonts.add(path);
  new FontFace(fontFamily(path).slice(1, -1), `url(${imgUrl("file", { path })})`).load()
    .then((f) => { document.fonts.add(f); if (S.sel.view === "menu") renderMain(); }).catch(() => {});
}
function cssColor(c) {
  if (!c) return "transparent";
  const m = /^#([0-9a-f]{6})([0-9a-f]{2})?$/i.exec(c);
  if (!m) return c;
  const n = parseInt(m[1], 16), a = m[2] ? parseInt(m[2], 16) / 255 : 1;
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a.toFixed(3)})`;
}
async function requestPreview(menuId, button, generated = false, opts = null) {
  const stage = $("#stage");
  if (stage) stage.style.opacity = 0.6;
  try {
    const r = await api("/api/preview", { method: "POST", body: { project: S.project, menu: menuId, button, ...(opts || { outline: true }) } });
    S.preview = r; S.previewFor = menuId;
    drawPreview(generated);
  } catch (e) {
    if (e.data?.issues?.length) showIssues(e.data.issues, t("preview_err")); else openModal(`<h2>${t("preview_err")}</h2><pre class="log">${esc(e.message + "\n" + (e.data?.output || ""))}</pre>`);
  } finally { if ($("#stage")) $("#stage").style.opacity = 1; }
}
function drawPreview() {
  const stage = $("#stage");
  if (!stage || !S.preview) return;
  stage.querySelectorAll(".exact").forEach((n) => n.remove());
  const img = document.createElement("img");
  img.className = "exact"; img.src = S.preview.image; img.alt = "";
  stage.appendChild(img);
  const ex = $("#exact"); if (ex && !S.spView) { ex.textContent = t("hide_preview"); ex.classList.remove("primary"); }
}

function renderMenuInspector(el) {
  const menu = curMenu();
  if (!menu) { el.innerHTML = ""; return; }
  const sel = S.element;
  const find = (p) => p.menus.find((x) => x.id === menu.id);
  if (sel && S.sels?.length > 1) {
    el.innerHTML = `<h2>${esc(t("n_selected", { n: S.sels.length }))}</h2><div class="hint">${esc(t("multi_hint"))}</div>`;
    return;
  }
  if (sel && sel.kind === "image") {
    const it = (menu.images || [])[sel.i];
    if (!it) { S.element = null; return renderMenuInspector(el); }
    el.innerHTML = `<h2>${t("picture")}</h2><div class="hint">${esc(t("picture_hint"))}</div>
      <label class="field"><span>${t("file")}</span>${selectHtml("file", mediaOf("image").map((x) => [x, x.replace(/^media\//, "")]), it.file, 'data-k="file"')}</label>
      <div class="grid2">
        <label class="field"><span>X</span><input type="number" data-k="x" min="0" max="719" value="${it.x}"></label>
        <label class="field"><span>Y</span><input type="number" data-k="y" min="0" max="${discH() - 1}" value="${it.y}"></label>
        <label class="field"><span>${t("width")}</span><input type="number" id="pic-w" min="1" max="720" value="${it.w}" data-nobind></label>
        <label class="field"><span>${t("height")}</span><input type="number" id="pic-h" min="1" max="${discH()}" value="${it.h}" data-nobind></label>
      </div>
      <label class="field" data-nobind><span></span><label><input type="checkbox" id="pic-ratio" ${S.picFree ? "" : "checked"}> ${t("keep_ratio")}</label></label>
      <label class="field" data-nobind><span>${t("opacity")}</span><input type="range" id="pic-a" min="0" max="100" value="${Math.round((it.opacity ?? 1) * 100)}"></label>
      ${pageHtml(menu, it)}${transformHtml(it, "image")}
      <button class="danger" id="del-el">${t("delete")}</button>`;
    bindFields(el, (p) => find(p).images[sel.i], { numeric: ["x", "y"] });
    bindTransform(el, (p) => find(p).images[sel.i]);
    bindPage(el, (p) => find(p).images[sel.i]);
    const resize = (which) => commit((p) => {
      const x = find(p).images[sel.i], ratio = x.h / x.w;
      const v = Math.max(1, Math.round(Number($(which === "w" ? "#pic-w" : "#pic-h").value) || 1));
      if (which === "w") { x.w = Math.min(720, v); if ($("#pic-ratio").checked) x.h = Math.max(1, Math.min(discH(), Math.round(x.w * ratio))); }
      else { x.h = Math.min(discH(), v); if ($("#pic-ratio").checked) x.w = Math.max(1, Math.min(720, Math.round(x.h / ratio))); }
    });
    $("#pic-w").onchange = () => resize("w"); $("#pic-h").onchange = () => resize("h");
    $("#pic-ratio").onchange = (e) => (S.picFree = !e.target.checked);
    $("#pic-a").onchange = (e) => commit((p) => { const x = find(p).images[sel.i], v = Number(e.target.value) / 100; if (v >= 1) delete x.opacity; else x.opacity = v; });
    $("#del-el").onclick = () => { commit((p) => { find(p).images.splice(sel.i, 1); if (!find(p).images.length) delete find(p).images; }); S.element = null; S.sels = []; renderAll(); };
    return;
  }
  if (sel && sel.kind === "shape") {
    const it = (menu.shapes || [])[sel.i];
    if (!it) { S.element = null; return renderMenuInspector(el); }
    const c = it.color || "#00000080";
    el.innerHTML = `<h2>${t("shape")}</h2>
      <div class="grid2">
        <label class="field"><span>X</span><input type="number" data-k="x" min="0" max="719" value="${it.x}"></label>
        <label class="field"><span>Y</span><input type="number" data-k="y" min="0" max="${discH() - 1}" value="${it.y}"></label>
        <label class="field"><span>${t("width")}</span><input type="number" data-k="w" min="1" max="720" value="${it.w}"></label>
        <label class="field"><span>${t("height")}</span><input type="number" data-k="h" min="1" max="${discH()}" value="${it.h}"></label>
      </div>
      <div class="grid2" data-nobind>
        <label class="field"><span>${t("fill")}</span><input type="color" id="shape-rgb" value="${esc(c.slice(0, 7))}"></label>
        <label class="field"><span>${t("opacity")}</span><input type="range" id="shape-a" min="0" max="255" value="${c.length > 7 ? parseInt(c.slice(7), 16) : 255}"></label>
      </div>
      ${pageHtml(menu, it)}${transformHtml(it, "shape")}
      <button class="danger" id="del-el">${t("delete")}</button>`;
    bindFields(el, (p) => find(p).shapes[sel.i], { numeric: ["x", "y", "w", "h"] });
    bindTransform(el, (p) => find(p).shapes[sel.i]);
    bindPage(el, (p) => find(p).shapes[sel.i]);
    const setColor = () => commit((p) => {
      const a = Number($("#shape-a").value);
      find(p).shapes[sel.i].color = $("#shape-rgb").value.toUpperCase() + (a >= 255 ? "" : a.toString(16).padStart(2, "0").toUpperCase());
    });
    $("#shape-rgb").onchange = setColor; $("#shape-a").onchange = setColor;
    $("#del-el").onclick = () => { commit((p) => { find(p).shapes.splice(sel.i, 1); if (!find(p).shapes.length) delete find(p).shapes; }); S.element = null; S.sels = []; renderAll(); };
    return;
  }
  if (sel) {
    const list = sel.kind === "button" ? menu.buttons : menu.texts || [];
    const it = list[sel.i];
    if (!it) { S.element = null; return renderMenuInspector(el); }
    const fonts = [["__none__", t("disc_font")], ...mediaOf("font").map((x) => [x, x.replace(/^media\//, "")])];
    // (on a menu with pages: the buttons on its page, or on every page)
    const btnIds = [["__none__", t("nav_auto")], ...menu.buttons.filter((b) => b !== it && (!b.page || b.page === it.page)).map((b) => [b.id, `${b.id} (${b.label || b.image})`])];
    const numbered = menu.buttons.map((b, i) => [b, i]).filter(([b]) => onPage(menu, b));
    const isImage = sel.kind === "button" && it.image;
    el.innerHTML = `<h2>${sel.kind === "button" ? t("button") : t("text")}</h2>
      ${sel.kind === "button" ? `<label class="field"><span>${t("text")}</span><input data-k="label" value="${esc(it.label)}"></label>
        <label class="field"><span>${t("action")} ${whipHtml("action")}</span>${selectHtml("action", actionOptions(), it.action)}</label>
        ${/^(title|chapter):/.test(it.action || "") ? `<label class="field"><span>${t("override")}</span>${selectHtml("override", [["__none__", t("override_none")], ...actionOptions({ forButton: false, includeChapters: true, allowPlayAll: true, allowLast: true })], it.override || "__none__")}<div class="hint">${esc(t("override_hint"))}</div></label>` : ""}
        ${TRANSITION_RE.test(it.action || "") ? `<label class="field"><span>${t("transition")}</span>${selectHtml("transition", [["__none__", t("none")], ...mediaOf("video").map((x) => [x, x])], it.transition || "__none__")}<div class="hint">${esc(t("transition_hint"))}</div></label>` : ""}
        ${streamsHtml(it)}
        <label class="field"><span></span><label><input type="checkbox" data-k="auto_activate" ${it.auto_activate ? "checked" : ""}> ${t("auto_activate")}</label></label>
        <label class="field" data-nobind><span>${t("image")}</span>${selectHtml("image", [["__none__", t("none")], ...mediaOf("image").map((x) => [x, x])], it.image || "__none__")}
          <div class="hint">${esc(t("image_hint"))}</div></label>`
        : `<label class="field"><span>${t("text")}</span><textarea data-k="text" id="text-body" rows="${Math.min(8, Math.max(2, String(it.text).split("\n").length))}">${esc(it.text)}</textarea></label>`}
      <div class="grid2">
        <label class="field"><span>X</span><input type="number" data-k="x" min="0" max="719" value="${it.x}"></label>
        <label class="field"><span>Y</span><input type="number" data-k="y" min="0" max="${discH() - 1}" value="${it.y}"></label>
        ${isImage ? `<label class="field"><span>${t("width")}</span><input type="number" data-k="width" min="8" max="720" value="${it.width || ""}" placeholder="${t("auto")}"></label>
        <label class="field"><span>${t("highlight_style")}</span>${selectHtml("highlight", [["frame", t("hl_frame")], ["shape", t("hl_shape")]], it.highlight || "frame")}</label>`
        : `<label class="field"><span>${t("size")}</span><input type="number" data-k="size" min="8" max="200" value="${it.size || ""}" placeholder="${menu.font_size || 32}"></label>
        <label class="field"><span>${t("color")}</span><input type="color" data-k="color" value="${esc(it.color || menu.text_color || "#ffffff")}"></label>`}
      </div>
      ${sel.kind === "text" ? `<h3>${t("paragraph")}</h3><div class="grid2">
        <label class="field"><span>${t("para_align")}</span>${selectHtml("align", [["left", t("para_left")], ["center", t("para_center")], ["right", t("para_right")]], it.align || "left")}</label>
        <label class="field"><span>${t("line_spacing")}</span><input type="number" data-k="line_spacing" min="-50" max="200" value="${it.line_spacing || 0}"></label>
      </div><div class="hint">${esc(t("paragraph_hint"))}</div>` : ""}
      ${isImage ? "" : `<h3>${t("text_style")}</h3>
      <label class="field"><span>${t("font")}</span>${selectHtml("font", fonts, it.font || "__none__")}<div class="hint">${esc(t("font_hint"))}</div></label>
      <div class="grid2" data-nobind>
        <label class="field"><span><input type="checkbox" id="st-outline" ${it.outline ? "checked" : ""}> ${t("outline")}</span>
          <span class="row"><input type="color" id="st-outline-c" value="${esc((it.outline || "#000000").slice(0, 7))}"><input type="number" id="st-outline-w" min="1" max="10" value="${it.outline_width || 2}" style="width:56px"></span></label>
        <label class="field"><span><input type="checkbox" id="st-shadow" ${it.shadow ? "checked" : ""}> ${t("shadow")}</span>
          <span class="row"><input type="color" id="st-shadow-c" value="${esc((it.shadow || "#000000").slice(0, 7))}"><input type="number" id="st-shadow-o" min="1" max="20" value="${it.shadow_offset || 3}" style="width:56px"></span></label>
      </div>`}
      ${sel.kind === "button" && /^(title|chapter):/.test(it.action || "") ? `<h3>${t("thumb_section")}</h3><div data-nobind>
        <label class="field"><span></span><label><input type="checkbox" id="th-on" ${it.thumbnail ? "checked" : ""}> ${t("thumb_on")}</label></label>
        ${it.thumbnail ? `<div class="grid2">${["x", "y", "w", "h"].map((k) =>
          `<label class="field"><span>${k === "w" ? t("width") : k === "h" ? t("height") : k.toUpperCase()}</span><input type="number" data-th="${k}" min="${k === "w" || k === "h" ? 8 : 0}" max="${k === "y" || k === "h" ? discH() : 720}" value="${it.thumbnail[k]}"></label>`).join("")}
          <label class="field"><span>${t("thumb_time")}</span><input type="number" data-th="time" min="0" step="0.1" value="${it.thumbnail.time ?? ""}" placeholder="1"></label></div>
          <label class="field"><span></span><label><input type="checkbox" id="th-anim" ${it.thumbnail.animated ? "checked" : ""} ${menu.background_video ? "" : "disabled"}> ${t("thumb_anim")}</label></label>` : ""}</div>` : ""}
      ${sel.kind === "button" ? `<label class="field"><span>${t("highlight_image")}</span>${selectHtml("highlight_image", [["__none__", t("auto")], ...mediaOf("image").map((x) => [x, x])], it.highlight_image || "__none__")}<div class="hint">${esc(t("highlight_image_hint"))}</div></label>` : ""}
      ${sel.kind === "button" ? `<label class="field" data-nobind><span>${t("button_number")}</span>${selectHtml("number", numbered.map(([, i], k) => [String(i), menu.button_offset ? t("number_on_remote", { n: k + 1, k: k + 1 + menu.button_offset }) : String(k + 1)]), String(sel.i), 'id="btn-number"')}<div class="hint">${esc(t("button_number_hint"))}</div></label>
        <h3>${t("nav")}</h3><div class="grid2">${["up", "down", "left", "right"].map((d) =>
        `<label class="field"><span>${d}</span>${selectHtml("nav." + d, btnIds, (it.nav || {})[d] || "__none__")}</label>`).join("")}</div>` : ""}
      ${pageHtml(menu, it)}${transformHtml(it, sel.kind)}
      <button class="danger" id="del-el">${t("delete")}</button>`;
    bindTransform(el, (p) => (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i]);
    bindPage(el, (p) => (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i]);
    // Number: the button moves to that place; the others close up
    if ($("#btn-number")) $("#btn-number").onchange = (e) => {
      const to = Number(e.target.value);
      commit((p) => { const list = find(p).buttons, [b] = list.splice(sel.i, 1); list.splice(to, 0, b); });
      S.element = { kind: "button", i: to }; S.sels = [S.element];
      renderMain(); renderInspector();
    };
    bindFields(el, (p) => (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i], {
      numeric: ["x", "y", "size", "width", "audio", "subtitle", "line_spacing"],
      onAfter: (p, key) => {
        const o = (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i];
        if (key === "align" && o.align === "left") delete o.align;
        if (key === "line_spacing" && !o.line_spacing) delete o.line_spacing;
        if (o.nav && !Object.keys(o.nav).length) delete o.nav;
        if (key === "highlight" && o.highlight === "frame") delete o.highlight;
        if (key === "auto_activate" && !o.auto_activate) delete o.auto_activate;
        if (key === "action" && !/^(title|chapter):/.test(o.action)) { delete o.thumbnail; delete o.override; }   // need a title / chapter
        if (key === "action" && /^(audio|subtitle):/.test(o.action)) { delete o.audio; delete o.subtitle; }      // already a switch
        if (key === "action" && !TRANSITION_RE.test(o.action)) delete o.transition;                           // nothing to lead into
      },
    });
    const thSet = (fn) => commit((p) => { const o = find(p).buttons[sel.i]; fn(o); });
    if ($("#th-on")) $("#th-on").onchange = (e) => thSet((o) => {
      if (!e.target.checked) { delete o.thumbnail; return; }
      const w = 144, h = Math.round(w * (P().disc.aspect === "4:3" ? 3 / 4 : 9 / 16) * discH() / 480);
      o.thumbnail = { x: Math.min(o.x, 720 - w), y: Math.max(0, Math.min(o.y - h - 8, discH() - h)), w, h };
    });
    el.querySelectorAll("[data-th]").forEach((inp) => (inp.onchange = () => thSet((o) => {
      const k = inp.dataset.th, v = inp.value === "" ? undefined : Number(inp.value);
      if (v === undefined && k === "time") delete o.thumbnail.time; else if (v !== undefined) o.thumbnail[k] = v;
    })));
    if ($("#th-anim")) $("#th-anim").onchange = (e) => thSet((o) => { if (e.target.checked) o.thumbnail.animated = true; else delete o.thumbnail.animated; });
    // outline / shadow: checkbox + colour + size
    const style = () => commit((p) => {
      const o = (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i];
      for (const [k, cb, col, num, nk, def] of [["outline", "#st-outline", "#st-outline-c", "#st-outline-w", "outline_width", 2],
        ["shadow", "#st-shadow", "#st-shadow-c", "#st-shadow-o", "shadow_offset", 3]]) {
        if ($(cb).checked) {
          o[k] = $(col).value.toUpperCase() + (k === "shadow" ? "B0" : "");
          const n = Number($(num).value); if (n && n !== def) o[nk] = n; else delete o[nk];
        } else { delete o[k]; delete o[nk]; }
      }
    });
    el.querySelectorAll("#st-outline, #st-outline-c, #st-outline-w, #st-shadow, #st-shadow-c, #st-shadow-o").forEach((x) => (x.onchange = style));
    // picking an image: start at a width that keeps the whole picture on screen
    const imgSel = el.querySelector("select[data-k=image]");
    if (imgSel) imgSel.addEventListener("change", async () => {
      const path = imgSel.value === "__none__" ? null : imgSel.value;
      let width = null;
      if (path) {
        const info = await probe(path), sx = displayW() / 720;
        const nw = info.width || 160, nh = info.height || 160;
        width = Math.round(Math.max(8, Math.min(nw / sx, 160, 720 - it.x, Math.floor((discH() - it.y) * nw / nh / sx) - 1)));
      }
      commit((p) => {
        const o = find(p).buttons[sel.i];
        if (path) { o.image = path; o.width = width; }
        else { delete o.image; delete o.width; delete o.highlight; if (!o.label) o.label = "BUTTON"; }
      });
    });
    $("#del-el").onclick = () => {
      if (sel.kind === "button" && menu.buttons.length <= 1) return;
      commit((p) => { (sel.kind === "button" ? find(p).buttons : find(p).texts).splice(sel.i, 1); });
      S.element = null; renderAll();
    };
    return;
  }
  const none = [["__none__", t("none")]];
  el.innerHTML = `<h2>${t("prop_menu")}</h2><div class="hint">${esc(t("nothing_selected"))}</div><h3></h3>
    <label class="field"><span>${t("id")}</span><input id="menu-id" value="${esc(menu.id)}"></label>
    <label class="field"><span>${t("background")}</span>${selectHtml("background", [...none, ...mediaOf("image").map((x) => [x, x])], menu.background || "__none__")}</label>
    <label class="field"><span>${t("background_video")}</span>${selectHtml("background_video", [...none, ...mediaOf("video").map((x) => [x, x])], menu.background_video || "__none__")}</label>
    <div class="grid2">
      <label class="field"><span>${t("background_color")}</span><input type="color" data-k="background_color" value="${esc(menu.background_color || "#000000")}"></label>
      <label class="field"><span>${t("text_color")}</span><input type="color" data-k="text_color" value="${esc(menu.text_color || "#ffffff")}"></label>
      <label class="field"><span>${t("font_size")}</span><input type="number" data-k="font_size" min="8" max="200" value="${menu.font_size || ""}" placeholder="32"></label>
      <label class="field"><span>${t("duration")}</span><input type="number" data-k="duration" min="1" max="600" value="${menu.duration || ""}" placeholder="${t("auto")}"></label>
    </div>
    <label class="field"><span>${t("music")}</span>${selectHtml("audio", [...none, ...mediaOf("audio").map((x) => [x, x])], menu.audio || "__none__")}</label>
    ${colourSetHtml(menu)}
    <h3>${t("playback")}</h3>
    <div class="grid2">
      <label class="field"><span>${t("loop")}</span>${selectHtml("loop", [["forever", t("loop_forever")], ...[1, 2, 3, 5, 10].map((n) => [String(n), t("loop_n", { n })])], String(menu.loop || "forever"))}</label>
      <label class="field"><span>${t("loop_point")}</span><input type="number" data-k="loop_point" min="0" step="0.1" value="${menu.loop_point ?? ""}" placeholder="0"></label>
      <label class="field"><span>${t("fade_in")}</span><input type="number" data-k="fade_in" min="0" max="10" step="0.1" value="${menu.fade_in ?? ""}" placeholder="0"></label>
    </div>
    ${menu.loop_point || menu.fade_in ? `<label class="field"><span></span><label><input type="checkbox" id="btn-at-loop" ${menu.buttons_at_loop ? "checked" : ""}> ${t("buttons_at_loop")}</label></label>` : ""}
    ${menu.loop && menu.loop !== "forever" ? `<label class="field"><span>${t("menu_end")}</span>${selectHtml("end_action", actionOptions({ forButton: false, includeChapters: true, allowPlayAll: true }), menu.end_action || "stop")}</label>` : ""}
    ${menu.psd ? `<label class="field"><span>Photoshop</span><div class="row"><span class="mono shrink" style="overflow:hidden;text-overflow:ellipsis">${esc(menu.psd)}</span><button class="small shrink" id="psd-edit">${t("cmd_edit_psd")}</button><button class="small shrink" id="psd-again">${t("reimport")}</button></div><div class="hint">${esc(t("reimport_hint"))}</div></label>` : ""}
    <label class="field"><span>${t("default_button")}</span>${selectHtml("default_button", [["__none__", t("auto")], ...(menu.buttons || []).map((b) => [b.id, `${b.id} (${b.label || b.image || ""})`])], menu.default_button || "__none__")}</label>
    <label class="field"><span></span><label><input type="checkbox" id="remember-btn" ${menu.remember_button === false ? "" : "checked"}> ${t("remember_button")}</label></label>
    <label class="field"><span>${t("button_offset")}</span><input type="number" data-k="button_offset" min="0" max="${Math.max(0, 99 - (menu.buttons || []).length)}" value="${menu.button_offset || ""}" placeholder="0"><div class="hint">${esc(t("button_offset_hint"))}</div></label>
    ${uopsHtml(menu, "menu")}
    ${orderHtml(t("order_menu"))}
    <h3></h3><button class="danger" id="del-menu">${t("delete")}</button>`;
  bindFields(el, find, {
    numeric: ["font_size", "duration", "loop_point", "fade_in", "button_offset"],
    onAfter: (p, key, val) => {
      const mm = find(p);
      if (key === "button_offset" && !val) delete mm.button_offset;
      if (key === "loop") { if (val === "forever") { delete mm.loop; delete mm.end_action; } else mm.loop = Number(val); }
      if (key === "loop_point" && !val) { delete mm.loop_point; if (!mm.fade_in) delete mm.buttons_at_loop; }
      if (key === "fade_in" && !val) { delete mm.fade_in; if (!mm.loop_point) delete mm.buttons_at_loop; }
    },
  });
  if ($("#psd-again")) $("#psd-again").onclick = () => { S.psdChanged = null; importPsd(menu.psd, menu.id); };
  if ($("#psd-edit")) $("#psd-edit").onclick = editPsd;
  bindColourSet(el, menu);
  if ($("#btn-at-loop")) $("#btn-at-loop").onchange = (e) => commit((p) => { const mm = find(p); if (e.target.checked) mm.buttons_at_loop = true; else delete mm.buttons_at_loop; });
  $("#remember-btn").onchange = (e) => commit((p) => { const mm = find(p); if (e.target.checked) delete mm.remember_button; else mm.remember_button = false; });
  bindUops(el, find);
  bindOrder(el, "menus", menu.id);
  $("#menu-id").onchange = (e) => {
    const nid = e.target.value.trim().replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 40);
    if (!nid || nid === menu.id || allMenuIds().includes(nid)) { e.target.value = menu.id; return; }
    commit((p) => { renameRefs(p, "menu", menu.id, nid); find(p).id = nid; });
    S.sel.id = nid; renderAll();
  };
  $("#del-menu").onclick = () => deleteItem("menu", menu.id);
}

// ---------------------------------------------------------------- media inspector
async function renderMediaInspector(el) {
  const path = S.selectedMedia, item = S.media.find((m) => m.path === path);
  if (!item) { S.selectedMedia = null; return renderInspector(); }
  let info = "";
  if (item.kind === "video" || item.kind === "audio") {
    const pr = await probe(path);
    if (S.selectedMedia !== path) return;
    info = pr?.error ? esc(pr.error) : `${pr.duration ? pr.duration.toFixed(2) + " s" : ""} ${pr.width ? `· ${pr.width}×${pr.height}` : ""} ${pr.has_audio ? "· ♪" : ""}`;
  }
  const preview = item.kind === "image" ? `<img src="${imgUrl("file", { path })}" style="width:100%;border-radius:6px">`
    : item.kind === "video" ? `<img src="${imgUrl("frame", { path, t: 1, w: 480 })}" style="width:100%;border-radius:6px">` : "";
  const menu = S.sel.view === "menu" ? curMenu() : null;
  const actions = [];
  if (item.kind === "video") {
    actions.push(`<button class="primary" data-act="title">${t("add_as_title")}</button>`);
    if (menu) actions.push(`<button data-act="vbg">${t("use_as_video_bg")}</button>`);
  }
  if (item.kind === "image") {
    if (menu) actions.push(`<button class="primary" data-act="bg">${t("use_as_bg")}</button>`, `<button data-act="pic">${t("place_on_menu")}</button>`);
    actions.push(`<button data-act="newmenu">${t("new_menu_with_bg")}</button>`);
  }
  if (item.kind === "audio") actions.push(`<button ${menu ? "" : 'class="primary"'} data-act="title">${t("add_as_title")}</button>`);
  if (item.kind === "audio" && menu) actions.push(`<button data-act="music">${t("use_as_music")}</button>`);
  if (item.kind === "design") actions.push(`<button class="primary" data-act="psd">${t("make_menu_from_psd")}</button><div class="hint">${esc(t("import_psd_hint"))}</div>`);
  if (item.kind === "subtitle" && (P().titles || []).length)
    actions.push(`<div class="hint">${t("add_sub_to")}</div>${(P().titles).map((x) => `<button data-act="sub" data-title="${esc(x.id)}">${esc(x.name || x.id)}</button>`).join(" ")}`);
  el.innerHTML = `<h2 style="word-break:break-all">${esc(path)}</h2>${preview}<p class="hint">${esc(item.kind)} · ${fmtBytes(item.bytes)} ${info}</p>
    <div style="display:flex;flex-direction:column;gap:8px">${actions.join("")}</div>`;
  el.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => mediaAction(b.dataset.act, path, b.dataset.title)));
}
function mediaAction(act, path, titleId) {
  const name = path.split("/").pop().replace(/\.[^.]+$/, "");
  if (act === "psd") return importPsd(path, uniqueId(name.replace(/[^A-Za-z0-9_-]+/g, "_").toLowerCase() || "menu", allMenuIds()));
  if (act === "title") {
    const id = uniqueId("t", (P().titles || []).map((x) => x.id));
    commit((p) => { (p.titles = p.titles || []).push({ id, name, source: path, chapters: ["00:00:00"] }); });
    // chapter markers the file brings with it become the title's chapters
    probe(path).then(() => {
      const ti = (P().titles || []).find((x) => x.id === id), list = sourceChapters(ti);
      if (ti && list.length > 1 && (ti.chapters || []).length === 1) commit((p) => setChapters(p.titles.find((x) => x.id === id), list));
    });
    S.selectedMedia = null; return select("title", id);
  }
  if (act === "pic") { S.selectedMedia = null; return placeMenuPicture(path); }
  if (act === "newmenu") {
    addBlankMenu(uniqueId("menu", allMenuIds())); const mid = S.sel.id;
    commit((p) => { p.menus.find((x) => x.id === mid).background = path; });
    S.selectedMedia = null; return renderAll();
  }
  const mid = S.sel.id;
  commit((p) => {
    const mm = (p.menus || []).find((x) => x.id === mid);
    if (act === "bg") { mm.background = path; delete mm.background_video; }
    if (act === "vbg") mm.background_video = path;
    if (act === "music") mm.audio = path;
    if (act === "sub") { const ti = p.titles.find((x) => x.id === titleId); (ti.subtitles = ti.subtitles || []).push({ file: path }); }
  });
  S.selectedMedia = null; renderAll();
}

// ---------------------------------------------------------------- uploads
function pickFiles() {
  const inp = document.createElement("input");
  inp.type = "file"; inp.multiple = true;
  inp.onchange = () => uploadFiles([...inp.files]);
  inp.click();
}
// (resolves to the project paths of the files that arrived)
function uploadFiles(files) {
  return Promise.all(files.map((f) => new Promise((resolve) => {
    S.uploads[f.name] = 0; renderSidebar();
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload?" + new URLSearchParams({ name: f.name }));
    xhr.setRequestHeader("X-Oncemore-Token", S.token);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) { S.uploads[f.name] = Math.round((e.loaded / e.total) * 100); renderSidebar(); } };
    xhr.onload = () => {
      delete S.uploads[f.name];
      try {
        const r = JSON.parse(xhr.responseText);
        if (xhr.status === 200) {
          S.media = r.media; S.selectedMedia = r.path;
          if (S.psdAfterUpload === f.name) { S.psdAfterUpload = null; mediaAction("psd", r.path); }
          resolve(r.path);
        }
        else { alert(r.error); resolve(null); }
      } catch (e) { alert(xhr.statusText); resolve(null); }
      renderSidebar(); renderInspector();
    };
    xhr.onerror = () => { delete S.uploads[f.name]; renderSidebar(); resolve(null); };
    xhr.send(f);
  }))).then((paths) => paths.filter(Boolean));
}
// File > Import as …: choose files, bring them into the project, then use them
function pickUpload(accept, multiple, then) {
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = accept; inp.multiple = multiple;
  inp.onchange = async () => { const paths = await uploadFiles([...inp.files]); if (paths.length) then(paths); };
  inp.click();
}
let dragDepth = 0;
window.addEventListener("dragenter", (e) => { if (P() && e.dataTransfer?.types?.includes("Files")) { dragDepth++; $("#drop-overlay").hidden = false; } });
window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; $("#drop-overlay").hidden = true; } });
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
  e.preventDefault(); dragDepth = 0; $("#drop-overlay").hidden = true;
  if (P() && e.dataTransfer?.files?.length) uploadFiles([...e.dataTransfer.files]);
});

// ---------------------------------------------------------------- check & build
async function runCheck() {
  openModal(`<h2>${t("check")}</h2><p class="muted">…</p>`);
  try {
    const r = await api("/api/validate", { method: "POST" });
    const s = r.summary;
    openModal(`<h2>✓ ${t("check_ok")}</h2>
      <p>${t("estimated")}: <b>${fmtBytes(s.estimated_bytes)}</b> ${t("of")} ${fmtBytes(s.capacity_bytes)}</p>
      ${budgetHtml(s)}
      <p>${t("video_avg")}: <b>${(s.video_bps / 1e6).toFixed(2)} Mbit/s</b></p>
      ${s.warnings.length ? `<h3>${t("warnings")}</h3><ul class="issues">${s.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}`);
  } catch (e) {
    if (e.data?.issues) showIssues(e.data.issues);
    else openModal(`<h2>${esc(e.message)}</h2>${e.data?.hint ? `<p class="hint">${esc(e.data.hint)}</p>` : ""}`);
  }
}
// the bit budget: a bar of the whole disc (each title, the menus, the disc's
// own files, what is left) and each title's rates and size, before encoding
function budgetHtml(s) {
  const b = s.budget, cap = b.capacity, pct = (n) => (n / cap) * 100;
  const parts = [...b.titles.map((x, i) => ({ cls: `title${i % 2 ? " alt" : ""}`, bytes: x.bytes, name: x.name || x.id })),
    { cls: "menus", bytes: b.menus, name: t("budget_menus") }, { cls: "other", bytes: b.other, name: t("budget_other") }];
  const info = Object.fromEntries(s.titles.map((x) => [x.id, x]));
  const row = (name, len, video, audio, bytes, extra = "") => `<tr><td>${esc(name)}</td><td>${len}</td><td>${video}</td><td>${audio}</td><td>${fmtBytes(bytes)}</td><td>${pct(bytes).toFixed(1)}%</td>${extra}</tr>`;
  return `<div class="budget" id="budget" role="img" aria-label="${esc(t("budget"))}">${parts.filter((x) => x.bytes > 0).map((x) =>
    `<div class="seg ${x.cls}" style="width:${pct(x.bytes)}%" title="${esc(x.name)} · ${fmtBytes(x.bytes)}"></div>`).join("")}</div>
    <table class="budget-table mono"><tr><th>${t("col_name")}</th><th>${t("col_length")}</th><th>${t("budget_video")}</th><th>${t("budget_audio")}</th><th>${t("budget_size")}</th><th>${t("budget_share")}</th><th></th></tr>
      ${b.titles.map((x) => row(x.name || x.id, `${x.seconds.toFixed(1)}s`, `${(x.video_bps / 1e6).toFixed(2)}`, `${Math.round(x.audio_bps / 1000)}k`, x.bytes,
        `<td class="muted">${info[x.id] ? `${info[x.id].chapters.length} ch · ${esc(info[x.id].audio)}` : ""}</td>`)).join("")}
      ${b.menus ? row(t("budget_menus"), "", "", "", b.menus) : ""}
      ${b.other ? row(t("budget_other"), "", "", "", b.other) : ""}
      ${row(t("budget_free"), "", "", "", b.free)}</table>`;
}
function renderBuild(m) {
  const job = S.job;
  const evs = S.jobEvents;
  const steps = [], progress = {};
  for (const e of evs) {
    if (e.event === "step") steps.push(e);
    if (e.event === "progress") progress[`${e.step}:${e.item ?? ""}`] = e.fraction;
  }
  const result = evs.find((e) => e.event === "result"), error = evs.find((e) => e.event === "error");
  const logs = evs.filter((e) => e.event === "log").map((e) => `${e.level === "warn" ? "⚠ " : ""}${e.message}`);
  const d = P().disc, fmt = S.buildFormat || "dvd", kind = S.buildKind || "iso";
  m.innerHTML = `<div class="build-panel">
    <div class="build-top"><button id="btn-check">${esc(t("check_project"))}</button><span class="spacer"></span>
      <button class="primary build-go" id="start" ${job && !job.done ? "disabled" : ""}>${job && !job.done ? t("building") : t("build")}</button></div>
    <fieldset class="group"><legend>${t("build_source")}</legend>
      <div class="frow"><span class="fl">${t("build_source")}</span><select disabled><option>${esc(t("current_project"))}</option></select></div></fieldset>
    <fieldset class="group"><legend>${t("build_format")}</legend>
      <label class="frow"><span class="fl">${t("build_format")}</span><select id="bformat">
        <option value="dvd" ${fmt === "dvd" ? "selected" : ""}>${t("format_dvd")}</option>
        <option value="bluray" ${fmt === "bluray" ? "selected" : ""}>${t("format_bluray")}</option>
        <option value="web" ${fmt === "web" ? "selected" : ""}>${t("format_web")}</option></select></label>
      ${fmt === "web" ? `<div class="frow"><span class="fl"></span><span class="hint">${esc(t("web_note"))}</span></div>` : ""}
      ${fmt === "bluray" ? `<label class="frow"><span class="fl">${t("bd_size")}</span><select id="bdsize">
        ${["BD25", "BD50"].map((v) => `<option ${(d.bluray?.target || "BD25") === v ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      <div class="frow"><span class="fl"></span><span class="hint">${esc(t("bd_note"))}</span></div>` : ""}</fieldset>
    <fieldset class="group"><legend>${t("output")}</legend>
      ${fmt === "web" ? `<div class="frow"><span class="fl"></span><span>${t("build_web_folder")}</span></div>` : `
      <label class="frow"><span class="fl"></span><span><input type="radio" name="kind" value="iso" ${kind === "iso" ? "checked" : ""}> ${t("build_iso")}</span></label>
      <label class="frow"><span class="fl"></span><span><input type="radio" name="kind" value="folder" ${kind === "folder" ? "checked" : ""}> ${t(fmt === "bluray" ? "build_bdmv" : "build_folder")}</span></label>
      <label class="frow"><span class="fl"></span><span><input type="radio" name="kind" value="disc" ${kind === "disc" ? "checked" : ""}> ${t(fmt === "bluray" ? "build_bd_disc" : "build_disc")}</span></label>`}
      ${kind === "disc" && fmt !== "web" ? `<label class="frow"><span class="fl">${t("recorder")}</span><input id="recorder" class="mono" value="${esc(S.recorder || "")}" placeholder="${S.platform === "darwin" ? "" : "/dev/sr0"}" title="${esc(t("recorder_hint"))}"></label>
      <div class="frow"><span class="fl"></span><span class="hint">${esc(t("recorder_hint"))}</span></div>` : ""}
      <div class="frow"><span class="fl">${t("destination")}</span><input class="mono" readonly value="${esc(S.dir)}/output"></div></fieldset>
    <fieldset class="group"><legend>${t("settings")}</legend>
      <label class="frow"><span class="fl"></span><span><input type="checkbox" id="fast" ${S.buildFast ? "checked" : ""}> ${t("fast")}</span></label>
      <label class="frow"><span class="fl"></span><span><input type="checkbox" id="nocache" ${S.buildNoCache ? "checked" : ""}> ${t("no_cache")}</span></label></fieldset>
    <fieldset class="group"><legend>${t("disc_info")}</legend>
      <div class="frow"><span class="fl">${t("label")}</span><span>${esc(d.label)}</span></div>
      <div class="frow"><span class="fl">${t("standard")}</span><span>${esc(d.standard)} · ${esc(d.aspect)} · ${esc(d.target || "DVD5")}</span></div></fieldset>
  </div>
  ${steps.length ? `<div class="card" style="max-width:720px"><ul class="steps">${steps.map((s, i) => {
    const f = progress[`${s.step}:${s.item ?? ""}`];
    const done = i < steps.length - 1 || (job && job.done);
    const pct = done ? 100 : f !== undefined ? Math.round(f * 100) : 0;
    const label = I18N.en["step_" + s.step] ? t("step_" + s.step, { i: s.item ?? "" }) : s.message;
    return `<li><div class="label"><span title="${esc(s.message)}">${esc(label)}</span><span class="muted">${done ? "✓" : pct + "%"}</span></div><div class="progress"><div style="width:${pct}%"></div></div></li>`;
  }).join("")}</ul></div>` : ""}
  ${result ? `<div class="card result-ok" style="max-width:720px"><h2>✓ ${t("build_done")}</h2>
      <p class="mono">${esc(result.index || result.iso || result.video_ts || result.bdmv)}</p><p>${fmtBytes(result.iso_bytes || result.bytes)}</p>
      ${result.burned ? `<p>✓ ${t("burned")}</p>` : ""}
      <button id="reveal">${t(S.platform === "darwin" ? "reveal" : "reveal_other")}</button>
      ${result.warnings?.length ? `<h3>${t("warnings")}</h3><ul class="issues">${result.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}</div>` : ""}
  ${error ? `<div class="card result-err" style="max-width:720px"><h2>✕ ${t("build_failed")}</h2><p>${esc(error.message)}</p>
      ${error.hint ? `<p class="hint">${esc(error.hint)}</p>` : ""}
      ${error.issues ? `<ul class="issues">${error.issues.map((i) => `<li><span class="path">${esc(i.path)}</span> ${esc(i.message)}</li>`).join("")}</ul>` : ""}
      ${error.output ? `<pre class="log">${esc(error.output)}</pre>` : ""}</div>` : ""}
  ${logs.length ? `<div class="card" style="max-width:720px"><div class="log">${esc(logs.join("\n"))}</div></div>` : ""}`;
  m.querySelectorAll("input[name=kind]").forEach((r) => (r.onchange = () => { S.buildKind = r.value; renderSidebar(); }));
  $("#bformat").onchange = (e) => { S.buildFormat = e.target.value; renderSidebar(); };
  if ($("#bdsize")) $("#bdsize").onchange = (e) => {
    commit(() => { if (e.target.value === "BD25") delete d.bluray; else d.bluray = { target: e.target.value }; });
  };
  if ($("#recorder")) $("#recorder").onchange = (e) => (S.recorder = e.target.value.trim());
  $("#fast").onchange = (e) => (S.buildFast = e.target.checked);
  $("#nocache").onchange = (e) => (S.buildNoCache = e.target.checked);
  $("#start").onclick = startBuild;
  $("#btn-check").onclick = runCheck;
  const rv = $("#reveal");
  if (rv) rv.onclick = () => api("/api/reveal", { method: "POST", body: { path: relPath(result.index || result.iso || result.video_ts || result.bdmv) } }).catch((e) => alert(e.message));
}
const relPath = (abs) => abs.startsWith(S.dir) ? abs.slice(S.dir.length + 1) : abs;
async function startBuild() {
  clearTimeout(S.saveTimer); await save();
  try {
    const r = await api("/api/build", { method: "POST", body: { format: S.buildFormat || "dvd", kind: S.buildKind || "iso", fast: !!S.buildFast, no_cache: !!S.buildNoCache, device: S.recorder || undefined } });
    S.job = { id: r.job, done: false }; S.jobEvents = []; S.jobNext = 0;
    pollJob();
  } catch (e) { alert(e.message); }
  if (S.leftTab === "build") renderSidebar();
}
// a job the server cannot be reached about this many times in a row is given up
const JOB_MISSES = 30;
async function pollJob() {
  if (!S.job) return;
  try {
    const r = await api(`/api/jobs/${S.job.id}?since=${S.jobNext}`);
    S.jobEvents.push(...r.events); S.jobNext = r.next; S.job.done = r.done; S.job.ok = r.ok;
    S.job.misses = 0;
  } catch (e) {
    console.error(e);
    if (e.status === 404 || (S.job.misses = (S.job.misses || 0) + 1) > JOB_MISSES) {
      S.jobEvents.push({ event: "error", message: e.message });
      S.job.done = true; S.job.ok = false;
    }
  }
  if (S.leftTab === "build") renderSidebar();
  if (!S.job.done) setTimeout(pollJob, S.job.misses ? 1000 : 500);
}

// ---------------------------------------------------------------- workspace
// Project | editor (+ Timeline) | Properties (+ Layers); see docs/DESIGN.md
const WORKSPACES = [["author", "ws_default"], ["flow", "flowchart"], ["sim", "project_preview"], ["build", "build"]];
const workspaceOf = (view) => (["flow", "sim", "build"].includes(view) ? view : "author");
const store = { get(k, d) { try { const v = localStorage.getItem("oncemore." + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("oncemore." + k, JSON.stringify(v)); } catch (e) { /* private mode */ } } };

// Window > Workspace, and the Workspace menu at the right of the Tools panel
function renderWorkspaces() {
  const ws = $("#workspaces");
  ws.disabled = !P();
  const cur = S.leftTab === "build" ? "build" : workspaceOf(S.sel.view);
  ws.innerHTML = WORKSPACES.map(([k, l]) => `<option value="${k}" data-ws="${k}" ${cur === k ? "selected" : ""}>${esc(t(l))}</option>`).join("");
  ws.onchange = () => WS(ws.value)();
}
// a tab strip of a frame: a grip, the tabs (the front one with its close
// box), then the panel menu on the right
const tabStrip = (tabs, cur, attr) => `<span class="grip" aria-hidden="true"></span><div class="tabs">${tabs.map(([k, l]) => `<button class="tab ${cur === k ? "active" : ""}" ${attr}="${k}">${esc(l)}${cur === k ? `<span class="x" aria-hidden="true">×</span>` : ""}</button>`).join("")}</div><span class="spacer"></span><button class="panel-menu" title="${esc(t("panel_menu"))}">${ICONS.panel}</button>`;
function renderLeft() {
  const tab = S.leftTab || "project";
  $("#left-tabs").innerHTML = P() ? tabStrip([["project", t("project")], ["menus", t("menus")], ["timelines", t("timelines")], ["build", t("build")]], tab, "data-lt") : "";
  $("#left-tabs").querySelectorAll("[data-lt]").forEach((b) => (b.onclick = () => { S.leftTab = b.dataset.lt; renderLeft(); renderWorkspaces(); }));
  renderSidebar();
}
// The viewer frame: Monitor (the open timeline), the Menu Viewer (named after
// the open menu), the open chapter playlist and the Flowchart. The Project
// Preview opens in a window of its own; Build is a panel in the Project frame.
function renderCenterHead() {
  const h = $("#center-head"), v = S.sel.view;
  if (!P()) { h.innerHTML = ""; return; }
  const ti = S.lastTitle && (P().titles || []).find((x) => x.id === S.lastTitle);
  const mn = S.lastMenu && ((P().menus || []).some((x) => x.id === S.lastMenu) || generatedMenus().some((g) => g.id === S.lastMenu)) ? S.lastMenu : null;
  const pl = S.lastPlaylist && (P().playlists || []).some((x) => x.id === S.lastPlaylist) ? S.lastPlaylist : null;
  const cur = v === "menu" ? "menu" : v === "flow" ? "flow" : v === "playlist" ? "playlist" : "monitor";
  const tab = (k, label, attrs) => `<button class="tab vtab ${cur === k ? "active" : ""}" ${attrs}>${esc(label)}${cur === k ? `<span class="x" aria-hidden="true">×</span>` : ""}</button>`;
  h.innerHTML = `<span class="grip" aria-hidden="true"></span><div class="tabs">
    ${tab("monitor", ti ? `${t("monitor")}` : t("monitor"), 'data-ctab="monitor"')}
    ${tab("menu", mn ? `${t("menu")}: ${mn}` : t("no_menus"), `data-ctab="menu" ${mn ? "" : "disabled"}`)}
    ${pl ? tab("playlist", `${t("playlist")}: ${pl}`, 'data-ctab="playlist"') : ""}
    ${tab("flow", t("flowchart"), 'data-view="flow" data-id="" data-ctab="flow"').replace('class="tab vtab', 'class="tab nav-item vtab')}
    </div><span class="spacer"></span><button class="panel-menu" title="${esc(t("panel_menu"))}">${ICONS.panel}</button>`;
  h.querySelectorAll("[data-ctab]").forEach((b) => (b.onclick = () => {
    const k = b.dataset.ctab;
    if (k === "monitor") { if (ti) select("title", ti.id); else select("disc"); }
    else if (k === "menu" && mn) select("menu", mn);
    else if (k === "playlist" && pl) select("playlist", pl);
    else if (k === "flow") select("flow");
  }));
}

// -- library: templates, backgrounds, text styles, Photoshop designs
const TEXT_STYLES = [
  ["plain", {}], ["outline", { outline: "#000000", outline_width: 3 }], ["shadow", { shadow: "#000000AA", shadow_offset: 3 }],
  ["outline_shadow", { outline: "#000000", outline_width: 2, shadow: "#00000088", shadow_offset: 4 }],
];
async function renderLibrary() {
  const el = $("#library");
  if (!S.templates) { try { S.templates = (await api("/api/templates")).templates; } catch (e) { S.templates = []; } }
  if (!S.userTemplates) { try { S.userTemplates = (await api("/api/user_templates")).templates; } catch (e) { S.userTemplates = []; } }
  if (!S.userStyles) { try { S.userStyles = (await api("/api/user_styles")).styles; } catch (e) { S.userStyles = []; } }
  if ((S.rightTab || "layers") !== "library") return;
  const menu = S.sel.view === "menu" ? curMenu() : null;
  const sels = menu ? (S.sels || []).filter((x) => x.kind !== "shape" && x.kind !== "image") : [];
  // (my styles: texts, buttons and shapes; a shape takes the colour)
  const anyEl = menu ? (S.sels || []).filter((x) => x.kind !== "image") : [];
  el.innerHTML = `
    <div class="lib-section"><h4>${t("lib_templates")}</h4><div class="lib-grid">
      ${S.templates.map((x) => `<button class="lib-item" data-tpl="${esc(x.id)}" title="${esc(x[LANG] || x.en)}"><b>${esc((x[LANG] || x.en).split(/ [—-] /)[0])}</b><span class="hint">${esc((x[LANG] || x.en).split(/ [—-] /)[1] || "")}</span></button>`).join("")}
    </div></div>
    <div class="lib-section"><h4>${t("lib_my_templates")}</h4>${S.userTemplates.length ? `<div class="lib-grid">
      ${S.userTemplates.map((x) => `<div class="lib-item utpl"><button class="lib-use" data-utpl="${esc(x.id)}" title="${esc(t("utpl_use"))}"><b>${esc(x.name)}</b><span class="hint">${esc(t("n_buttons", { n: x.buttons }))}</span></button><button class="small danger" data-utpl-del="${esc(x.id)}" title="${esc(t("delete"))}">✕</button></div>`).join("")}</div>`
      : `<div class="hint">${esc(t("utpl_none"))}</div>`}</div>
    <div class="lib-section"><h4>${t("lib_backgrounds")}</h4>${mediaOf("image").length ? `<div class="lib-grid">
      ${mediaOf("image").map((x) => `<button class="lib-item" data-bg="${esc(x)}" title="${esc(menu ? t("use_as_bg") : t("new_menu_with_bg"))}"><img src="${imgUrl("file", { path: x })}" alt=""><span>${esc(x.replace(/^media\//, ""))}</span></button>`).join("")}</div>`
      : `<div class="hint">${esc(t("add_files"))}</div>`}</div>
    <div class="lib-section"><h4>${t("lib_text_styles")}</h4><div class="lib-grid">
      ${TEXT_STYLES.map(([k, st]) => `<button class="lib-item" data-style="${k}" ${sels.length ? "" : "disabled"} title="${esc(t("lib_style_hint"))}"><span class="sw" style="color:var(--c-on-picture);${st.outline ? `text-shadow:1px 1px 0 #000,-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000${st.shadow ? ",3px 3px 0 rgba(0,0,0,.6)" : ""}` : st.shadow ? "text-shadow:3px 3px 0 rgba(0,0,0,.7)" : ""}">Aa</span><span>${esc(t("style_" + k))}</span></button>`).join("")}
    </div>${sels.length ? "" : `<div class="hint">${esc(t("lib_style_hint"))}</div>`}</div>
    <div class="lib-section"><h4>${t("lib_my_styles")}</h4>${S.userStyles.length ? `<div class="lib-grid">
      ${S.userStyles.map((x) => `<div class="lib-item utpl"><button class="lib-use" data-ustyle="${esc(x.id)}" ${anyEl.length ? "" : "disabled"} title="${esc(t("ustyle_use"))}"><span class="sw" style="color:${esc(x.props.color || "var(--c-on-picture)")};${x.props.outline ? "text-shadow:1px 1px 0 " + esc(x.props.outline) + ",-1px -1px 0 " + esc(x.props.outline) : ""}">Aa</span><span>${esc(x.name)}</span></button><button class="small danger" data-ustyle-del="${esc(x.id)}" title="${esc(t("delete"))}">✕</button></div>`).join("")}</div>`
      : `<div class="hint">${esc(t("ustyle_none"))}</div>`}
      <button class="small" id="save-style" ${anyEl.length === 1 ? "" : "disabled"} title="${esc(t("ustyle_save_hint"))}">${t("ustyle_save")}</button></div>
    <div class="lib-section"><h4>Photoshop</h4>${mediaOf("design").length ? `<div class="lib-grid">${mediaOf("design").map((x) => `<button class="lib-item" data-psd="${esc(x)}"><b>PSD</b><span>${esc(x.replace(/^media\//, ""))}</span></button>`).join("")}</div>` : `<div class="hint">${esc(t("no_psd"))}</div>`}</div>`;
  el.querySelectorAll("[data-tpl]").forEach((b) => (b.onclick = async () => {
    const id = uniqueId(b.dataset.tpl, allMenuIds()), first = (P().menus || [])[0];
    const r = await api("/api/template", { method: "POST", body: { template: b.dataset.tpl, id, project: S.project, back: first ? `menu:${first.id}` : null } });
    commit((p) => { (p.menus = p.menus || []).push(r.menu); });
    select("menu", id);
  }));
  el.querySelectorAll("[data-bg]").forEach((b) => (b.onclick = () => mediaAction(menu ? "bg" : "newmenu", b.dataset.bg)));
  el.querySelectorAll("[data-utpl]").forEach((b) => (b.onclick = () => applyUserTemplate(b.dataset.utpl)));
  el.querySelectorAll("[data-utpl-del]").forEach((b) => (b.onclick = async () => {
    const x = S.userTemplates.find((y) => y.id === b.dataset.utplDel);
    if (!x || !confirm(t("confirm_delete", { x: x.name }))) return;
    try { S.userTemplates = (await api("/api/delete_template", { method: "POST", body: { template: x.id } })).templates; } catch (err) { alert(err.message); }
    renderLibrary();
  }));
  el.querySelectorAll("[data-psd]").forEach((b) => (b.onclick = () => mediaAction("psd", b.dataset.psd)));
  el.querySelectorAll("[data-ustyle]").forEach((b) => (b.onclick = async () => {
    let r;
    try { r = await api("/api/apply_style", { method: "POST", body: { style: b.dataset.ustyle } }); } catch (err) { alert(err.message); return; }
    S.media = r.media;
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const k of anyEl) {
        const it = mm[KIND_LIST[k.kind]][k.i];
        if (k.kind === "shape") { if (r.props.color) it.color = r.props.color; continue; }
        for (const f of ["font", "size", "color", "outline", "outline_width", "shadow", "shadow_offset"]) delete it[f];
        Object.assign(it, r.props);
      }
    });
    S.preview = null; renderMain(); renderInspector();
  }));
  el.querySelectorAll("[data-ustyle-del]").forEach((b) => (b.onclick = async () => {
    const x = S.userStyles.find((y) => y.id === b.dataset.ustyleDel);
    if (!x || !confirm(t("confirm_delete", { x: x.name }))) return;
    try { S.userStyles = (await api("/api/delete_style", { method: "POST", body: { style: x.id } })).styles; } catch (err) { alert(err.message); }
    renderLibrary();
  }));
  const save = el.querySelector("#save-style");
  if (save) save.onclick = async () => {
    const k = anyEl[0], it = menu[KIND_LIST[k.kind]][k.i];
    const name = prompt(t("ustyle_name"), it.label || it.text || t("ustyle_default_name"));
    if (!name) return;
    try { S.userStyles = (await api("/api/save_style", { method: "POST", body: { name, props: it } })).styles; } catch (err) { alert(err.message); }
    renderLibrary();
  };
  el.querySelectorAll("[data-style]").forEach((b) => (b.onclick = () => {
    const st = TEXT_STYLES.find((x) => x[0] === b.dataset.style)[1];
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const k of sels) {
        const it = (k.kind === "button" ? mm.buttons : mm.texts)[k.i];
        for (const f of ["outline", "outline_width", "shadow", "shadow_offset"]) delete it[f];
        Object.assign(it, st);
      }
    });
    S.preview = null; renderMain(); renderInspector();
  }));
}

// -- layers: every element of the menu, top first, synced with the stage selection
function renderLayers() {
  const panel = $("#p-layers"), body = $("#layers"), lib = $("#library");
  panel.hidden = !P();
  if (!P()) return;
  // Layers and Library share a frame, as tabs
  const tab = S.rightTab || "layers";
  $("#layers-head").innerHTML = tabStrip([["layers", t("layers")], ["library", t("library")]], tab, "data-lt");
  $("#layers-head").querySelectorAll("[data-lt]").forEach((b) => (b.onclick = () => { S.rightTab = b.dataset.lt; renderLayers(); }));
  body.hidden = tab !== "layers"; lib.hidden = tab !== "library";
  if (tab === "library") { renderLibrary(); return; }
  const menu = S.sel.view === "menu" ? curMenu() : null;
  if (!menu) { body.innerHTML = `<div class="hint" style="padding:8px">${esc(t("layers_hint"))}</div>`; return; }
  const sel = (k, i) => (S.sels || []).some((x) => x.kind === k && x.i === i) || (S.element && S.element.kind === k && S.element.i === i);
  const listOfKind = (k) => menu[KIND_LIST[k]] || [];
  const row = (k, i, ico, name, to, n) => `<div class="layer-row ${sel(k, i) ? "selected" : ""} ${listOfKind(k)[i].hidden ? "off" : ""}" data-lk="${k}" data-li="${i}">
      <button class="eye" data-leye title="${esc(t(listOfKind(k)[i].hidden ? "layer_show" : "layer_hide"))}">${listOfKind(k)[i].hidden ? ICONS.eyeOff : ICONS.eye}</button>
      <span class="ico">${ico}</span><span class="nm">${esc(name)}</span>${to ? `<span class="to">${esc(to)}</span>` : ""}
      <span class="ops"><button class="small" data-lmove="-1" ${i ? "" : "disabled"} title="▲">▲</button><button class="small" data-lmove="1" ${i + 1 < n ? "" : "disabled"} title="▼">▼</button><button class="small danger" data-ldel title="${esc(t("delete"))}">✕</button></span></div>`;
  const bs = menu.buttons || [], ts = menu.texts || [], ss = menu.shapes || [], ims = menu.images || [];
  // (a menu with pages: the objects of the page shown, those on every page marked)
  const paged = pagesOf(menu) > 1, every = (x) => (paged && !x.page ? ` · ${t("page_all")}` : "");
  const rows = (list, fn) => list.map((x, i) => (onPage(menu, x) ? fn(x, i) : "")).join("");
  const count = (list) => list.filter((x) => onPage(menu, x)).length;
  body.innerHTML = `${paged ? `<div class="layer-group">${esc(t("page_of", { n: curPage(menu), m: pagesOf(menu) }))}</div>` : ""}
    <div class="layer-group">${t("buttons")} (${count(bs)})</div>${rows(bs, (b, i) => row("button", i, b.image ? "▣" : b.label ? "◉" : "⬚", (b.label || b.id) + every(b), linkName(b.action), bs.length))}
    ${count(ts) ? `<div class="layer-group">${t("texts")} (${count(ts)})</div>${rows(ts, (x, i) => row("text", i, "T", x.text + every(x), "", ts.length))}` : ""}
    ${count(ims) ? `<div class="layer-group">${t("pictures")} (${count(ims)})</div>${rows(ims, (x, i) => row("image", i, "▨", x.file.replace(/^media\//, "") + every(x), "", ims.length))}` : ""}
    ${count(ss) ? `<div class="layer-group">${t("shapes")} (${count(ss)})</div>${rows(ss, (x, i) => row("shape", i, "■", `${t("rectangle")} ${i + 1}` + every(x), "", ss.length))}` : ""}
    <div class="layer-group">${t("background")}</div><div class="layer-row"><span class="ico">▤</span><span class="nm">${esc(menu.background_video || menu.background || menu.background_color || "#000")}</span></div>`;
  const list = elementList;
  body.querySelectorAll(".layer-row[data-lk]").forEach((r) => {
    const k = r.dataset.lk, i = Number(r.dataset.li);
    r.onclick = (e) => {
      if (e.target.closest("button")) return;
      const key = { kind: k, i };
      if (e.shiftKey || e.metaKey || e.ctrlKey) S.sels = [...(S.sels || []).filter((x) => !(x.kind === k && x.i === i)), key];
      else S.sels = [key];
      S.element = key; S.selectedMedia = null;
      renderMain(); renderInspector();
    };
    r.querySelectorAll("[data-lmove]").forEach((b) => (b.onclick = () => {
      const j = i + Number(b.dataset.lmove);
      commit((p) => { const l = list(p.menus.find((x) => x.id === menu.id), k); [l[i], l[j]] = [l[j], l[i]]; });
      S.element = { kind: k, i: j }; S.sels = [S.element]; S.preview = null; renderMain(); renderInspector();
    }));
    r.querySelector("[data-leye]").onclick = (ev) => {
      ev.stopPropagation();
      commit((p) => { const it = list(p.menus.find((x) => x.id === menu.id), k)[i]; if (it.hidden) delete it.hidden; else it.hidden = true; });
      S.element = null; S.sels = []; S.preview = null; renderMain(); renderInspector();
    };
    r.querySelector("[data-ldel]").onclick = () => {
      commit((p) => { list(p.menus.find((x) => x.id === menu.id), k).splice(i, 1); });
      S.element = null; S.sels = []; S.preview = null; renderMain(); renderInspector();
    };
  });
}

// -- timeline: ruler, picture, chapters, audio and subtitle tracks of a title
function tlPlayhead(time) {
  const ph = $("#tl-playhead");
  if (ph && S.tl) ph.style.left = `${S.tl.x0 + time * S.tl.pps}px`;
}
async function renderTimeline() {
  const panel = $("#p-timeline"), split = $("#tl-splitter");
  // the open timeline, or the one opened last while a menu or the flowchart is in front
  const tlOf = () => { const id = S.sel.view === "title" ? S.sel.id : S.lastTitle; return P() && id ? (P().titles || []).find((x) => x.id === id) : null; };
  const ti = tlOf();
  const show = !!(ti && (ti.source || ti.clips) && !ti.slideshow);
  panel.hidden = split.hidden = !P();
  if (!show) {
    // the Timeline panel stays in its place, empty, as long as no timeline is open
    S.tl = null;
    if (!P()) return;
    $("#tl-head").innerHTML = `<span class="grip" aria-hidden="true"></span><div class="tabs"><button class="tab active" disabled>${esc(t("no_timelines"))}</button></div><span class="spacer"></span><button class="panel-menu" title="${esc(t("panel_menu"))}">${ICONS.panel}</button>`;
    $("#tl").innerHTML = `<div class="tl-empty"><div class="tl-row"><span class="tl-label tl-tcs"><span>${esc(t("timeline"))}:</span><span>${esc(t("tc_source"))}:</span></span><div class="tl-track tl-ruler"></div></div></div>`;
    return;
  }
  let src = ti.source, join = null;
  if (ti.clips) {
    try { join = await clipJoin(ti); } catch (e) { return; }
    src = join.path;
  }
  const info = await probe(src);
  if (tlOf() !== ti) return;
  const dur = join ? join.duration : info?.duration || 0;
  const zoom = S.tlZoom || 1;
  $("#tl-head").innerHTML = `<span class="grip" aria-hidden="true"></span><div class="tabs"><button class="tab active">${esc(ti.name || ti.id)}<span class="dd" aria-hidden="true">▾</span><span class="x" aria-hidden="true">×</span></button></div>
    <span class="spacer"></span>
    <button class="tlz" id="tl-out" title="${esc(t("zoom_hint"))}">${ICONS.mtnS}</button><button class="tlz" id="tl-in" title="${esc(t("zoom_hint"))}">${ICONS.mtnL}</button>
    <button class="panel-menu" title="${esc(t("panel_menu"))}">${ICONS.panel}</button>`;
  $("#tl-out").onclick = () => { S.tlZoom = Math.max(1, zoom / 2); renderTimeline(); };
  $("#tl-in").onclick = () => { S.tlZoom = Math.min(64, zoom * 2); renderTimeline(); };
  const box = $("#tl"), LABEL = 170;
  const width = Math.max(200, (box.clientWidth || 800) - LABEL - 16) * zoom;
  const pps = dur ? width / dur : 1;
  S.tl = { x0: LABEL, pps, dur };
  const step = [0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600].find((s) => s * pps >= 70) || 1200;
  const ticks = [];
  for (let x = 0; x <= dur; x += step) ticks.push(`<span class="tick" style="left:${x * pps}px">${fmtTime(x).replace(/\.\d+$/, "").replace(/^00:/, "")}</span>`);
  const thumbW = 78, nThumb = Math.min(200, Math.ceil(width / thumbW));
  const thumbs = Array.from({ length: nThumb }, (_, k) => `<img src="${imgUrl("frame", { path: src, t: Math.min(dur - 0.05, (k + 0.5) * thumbW / pps).toFixed(2), w: 160 })}" style="width:${thumbW}px" alt="">`).join("");
  const entries = chapterEntries(ti);
  // View > Show chapter names: in the time ruler, for this timeline
  if ((S.chapterNames || {})[ti.id]) ticks.push(...entries.map((c, i) => `<span class="ch-name" style="left:${c.time * pps}px" title="${esc(fmtTime(c.time))}">${esc(c.name || t("chapter_label", { n: i + 1 }))}</span>`));
  const tracks = ti.audio_tracks && ti.audio_tracks.length ? ti.audio_tracks : [{}];
  // the sound drawn under its clip (the waveform is the length of the file)
  const wave = (path, stream, len) => `<img class="tl-wave" alt="" draggable="false" style="width:${len * pps}px" src="${imgUrl("waveform", { path, s: stream, w: Math.round(Math.min(4000, Math.max(64, len * pps))), h: 48 })}">`;
  const subs = ti.subtitles || [];
  const LANE_ICON = { title: ICONS.video, audio: ICONS.audio, chapter: ICONS.addch, subtitle: "≣" };
  const lane = (label, cls, inner, kind = "") => `<div class="tl-row lane-${kind}"><span class="tl-label"><span class="tl-ico">${LANE_ICON[kind] || ""}</span><b>${esc(label)}</b></span><div class="tl-track tl-lane ${cls}" style="width:${width}px">${inner}</div></div>`;
  box.innerHTML = `<div class="tl" style="width:${LABEL + width + 16}px">
    <div class="tl-row tl-top"><span class="tl-label tl-tcs"><span>${esc(t("timeline"))}:<br><b class="tc-amber" id="tl-tc">${fmtTime(S.playhead[ti.id] || 0)}</b></span><span>${esc(t("tc_source"))}:<br><b class="tc-amber">${fmtTime(dur)}</b></span></span><div class="tl-track tl-ruler" id="tl-ruler" style="width:${width}px">${ticks.join("")}</div></div>
    ${lane(t("video"), "video", `<span class="vname">${esc(join ? ti.name || ti.id : (ti.source || "").replace(/^media\//, ""))}</span>` + thumbs, "title")}
    ${join ? lane(t("clips"), "clips", join.clips.map((c, k) => `<div class="tl-clip clip ${k % 2 ? "alt" : ""}" data-cstart="${c.start}" style="left:${c.start * pps}px;width:${Math.max(3, c.duration * pps)}px" title="${esc(c.source)}">${k + 1} ${esc(c.source.replace(/^media\//, ""))}</div>`).join(""), "title") : ""}
    ${lane(t("chapters"), "chapters", entries.map((c, i) => `<div class="tl-chapter ${i ? "" : "first"}" data-tlch="${i}" style="left:${c.time * pps}px" title="${esc(fmtTime(c.time))}"><span>${i + 1}${c.name ? " " + esc(c.name) : ""}</span></div>`).join(""), "chapter")}
    ${join ? lane(t("audio"), "", wave(join.path, 0, dur) + join.clips.map((c) => `<div class="tl-clip audio" style="left:${c.start * pps}px;width:${Math.max(3, c.duration * pps)}px">${esc(c.source.replace(/^media\//, ""))}</div>`).join(""), "audio")
      : tracks.map((a, k) => lane(`${t("audio")} ${k + 1}${a.lang ? " · " + a.lang : ""}`, "", wave(a.source || ti.source, a.stream || 0, dur) + `<div class="tl-clip audio" style="left:0;width:${dur * pps}px">${esc((a.source || ti.source).replace(/^media\//, ""))}${a.stream ? " #" + a.stream : ""}</div>`, "audio")).join("")}
    ${subs.map((s, k) => lane(`${t("subtitles")} ${k + 1}${s.lang ? " · " + s.lang : ""}`, "", `<span class="hint" data-subk="${k}"></span>`, "subtitle")).join("")}
    <div class="tl-playhead" id="tl-playhead"></div></div>`;
  tlPlayhead(S.playhead[ti.id] || 0);
  const at = (ev, el) => Math.max(0, Math.min(dur, (ev.clientX - el.getBoundingClientRect().left) / pps));
  const seek = (time) => (S.titleSeek ? S.titleSeek(time) : (S.playhead[ti.id] = time, tlPlayhead(time)));
  $("#tl-ruler").onpointerdown = (ev) => seek(at(ev, $("#tl-ruler")));
  box.querySelector(".tl-lane.video").onpointerdown = (ev) => seek(at(ev, ev.currentTarget));
  box.querySelectorAll(".tl-clip.clip").forEach((c) => (c.onclick = () => seek(Number(c.dataset.cstart))));
  box.querySelectorAll(".tl-wave").forEach((img) => (img.onerror = () => img.remove()));     // no sound
  // drag a chapter mark (not the first) to move it, frame-accurately
  const fps = (() => { const [a, b] = String(info.fps || "30").split(/[/:]/).map(Number); return b ? a / b : a || 30; })();
  box.querySelectorAll(".tl-chapter[data-tlch]").forEach((mk) => {
    const i = Number(mk.dataset.tlch);
    mk.onpointerdown = (ev) => {
      ev.stopPropagation();
      const track = mk.parentElement;
      if (!i) { seek(entries[0].time); return; }
      mk.setPointerCapture(ev.pointerId);
      let time = entries[i].time;
      const lo = entries[i - 1].time + 1 / fps, hi = (entries[i + 1]?.time ?? dur) - 1 / fps;
      mk.onpointermove = (e) => { time = Math.round(Math.max(lo, Math.min(hi, at(e, track))) * fps) / fps; mk.style.left = `${time * pps}px`; };
      mk.onpointerup = () => {
        mk.onpointermove = mk.onpointerup = null;
        if (Math.abs(time - entries[i].time) < 1e-6) { seek(time); return; }
        commit((p) => { const x = p.titles.find((y) => y.id === ti.id), list = chapterEntries(x); list[i].time = time; setChapters(x, list); });
        renderMain(); seek(time);
      };
    };
  });
  // subtitle cues as clips
  subs.forEach(async (s, k) => {
    let data;
    try { data = await api("/api/subtitles?" + new URLSearchParams({ path: s.file, offset: s.offset ?? "" })); } catch (e) { return; }
    const host = box.querySelector(`[data-subk="${k}"]`);
    if (!host) return;
    host.outerHTML = data.cues.map((c) => `<div class="tl-clip sub" data-cue="${c.start}" style="left:${c.start * pps}px;width:${Math.max(3, (c.end - c.start) * pps)}px" title="${esc(c.image || c.text)}">${c.image ? "▣ " + esc(c.image.split("/").pop()) : esc(c.text.split("\n")[0])}</div>`).join("");
    box.querySelectorAll(".tl-clip.sub").forEach((c) => (c.onclick = () => seek(Number(c.dataset.cue))));
  });
}

// -- splitters: drag to resize the side panels and the timeline (remembered)
function initSplitters() {
  const root = document.documentElement;
  for (const [k, d] of [["left-w", 250], ["right-w", 310], ["timeline-h", 190]]) {
    const v = store.get(k, null);
    if (v) root.style.setProperty("--" + k, v + "px");
    else root.style.removeProperty("--" + k);
    void d;
  }
  document.querySelectorAll(".splitter").forEach((sp) => {
    sp.onpointerdown = (ev) => {
      ev.preventDefault();
      sp.setPointerCapture(ev.pointerId); sp.classList.add("dragging");
      const which = sp.dataset.split;
      const start = { x: ev.clientX, y: ev.clientY,
        v: which === "left" ? $("#p-left").offsetWidth : which === "right" ? $("#p-right").offsetWidth : $("#p-timeline").offsetHeight };
      sp.onpointermove = (e) => {
        let v;
        if (which === "left") { v = Math.max(170, Math.min(520, start.v + e.clientX - start.x)); root.style.setProperty("--left-w", v + "px"); store.set("left-w", v); }
        else if (which === "right") { v = Math.max(240, Math.min(560, start.v - (e.clientX - start.x))); root.style.setProperty("--right-w", v + "px"); store.set("right-w", v); }
        else { v = Math.max(90, Math.min(window.innerHeight * 0.6, start.v - (e.clientY - start.y))); root.style.setProperty("--timeline-h", v + "px"); store.set("timeline-h", v); }
      };
      sp.onpointerup = () => { sp.onpointermove = sp.onpointerup = null; sp.classList.remove("dragging"); if (which !== "timeline" && S.sel.view === "title") renderTimeline(); };
    };
  });
}
function applyBrightness() {
  const b = Number(store.get("brightness", 0)) || 0;
  document.documentElement.style.setProperty("--ui-b", `${b}%`);
}
function preferencesBox() {
  const b = Number(store.get("brightness", 0)) || 0;
  openModal(`<h2>${t("preferences")}</h2><h3>${t("appearance")}</h3>
    <label class="field"><span>${t("brightness")}</span>
      <div class="row"><span class="shrink hint">${t("darker")}</span><input type="range" id="pref-bright" min="-8" max="14" step="1" value="${b}"><span class="shrink hint">${t("lighter")}</span>
      <button class="small shrink" id="pref-bright-def">${t("default")}</button></div>
      <div class="hint">${esc(t("brightness_hint"))}</div></label>
    <label class="field"><span>${t("skin")}</span>${selectHtml("skin", [["modern", t("skin_modern")], ["classic", t("skin_classic")]], store.get("skin", "modern"), 'id="pref-skin"')}<div class="hint">${esc(t("skin_hint"))}</div></label>
    <label class="field"><span>${t("cmd_theme")}</span>${selectHtml("theme", [["dark", t("theme_dark")], ["light", t("theme_light")]], store.get("theme", "dark"), 'id="pref-theme"')}</label>
    <label class="field"><span>${t("language")}</span>${selectHtml("lang", [["en", "English"], ["ja", "日本語"]], LANG, 'id="pref-lang"')}</label>
    <h3>${t("media_cache")}</h3>
    <label class="field"><span>${t("cache_folder")}</span>
      <div class="row"><input id="pref-cache" class="mono" placeholder="${esc(t("cache_in_project"))}">
      <button class="small shrink" id="pref-cache-set">${t("cache_use")}</button><button class="small shrink" id="pref-cache-def">${t("cache_in_project_short")}</button></div>
      <div class="hint" id="pref-cache-hint">${esc(t("cache_hint"))}</div></label>`);
  // the media cache: in the project folder, or one folder for every project
  const showCache = (r) => {
    if (!$("#pref-cache")) return;
    $("#pref-cache").value = r.cache_dir || "";
    $("#pref-cache-hint").textContent = `${t("cache_hint")} ${t("cache_now", { p: r.project_cache })}`;
  };
  const putCache = (v) => api("/api/settings", { method: "PUT", body: { cache_dir: v } }).then(showCache).catch((e) => alert(e.message));
  api("/api/settings").then(showCache).catch(() => {});
  $("#pref-cache-set").onclick = () => putCache($("#pref-cache").value.trim() || null);
  $("#pref-cache-def").onclick = () => putCache(null);
  const set = (v) => { store.set("brightness", v); applyBrightness(); };
  $("#pref-bright").oninput = (e) => set(Number(e.target.value));
  $("#pref-bright-def").onclick = () => { $("#pref-bright").value = 0; set(0); };
  $("#pref-lang").onchange = (e) => { LANG = e.target.value; try { localStorage.setItem("oncemore.lang", LANG); } catch (x) { /* storage blocked */ } renderAll(); preferencesBox(); };
  $("#pref-theme").onchange = (e) => { store.set("theme", e.target.value); applyTheme(); };
  $("#pref-skin").onchange = (e) => { store.set("skin", e.target.value); applyTheme(); renderAll(); };
}
function applyTheme() {
  const th = store.get("theme", "dark"), skin = store.get("skin", "modern");
  if (th === "light") document.documentElement.dataset.theme = "light"; else delete document.documentElement.dataset.theme;
  // the skin: Modern (default) or Classic (the classic disc authoring look)
  if (skin === "classic") document.documentElement.dataset.skin = "classic"; else delete document.documentElement.dataset.skin;
}

// ---------------------------------------------------------------- boot
function applyState(r) {
  S.project = r.project; S.dir = r.dir; S.media = r.media; S.check = r.check;
  S.tools = r.tools; S.platform = r.platform; S.version = r.version; S.runningJob = r.job;
}
async function boot() {
  const m = location.hash.match(/token=([\w-]+)/);
  if (m) { S.token = m[1]; sessionStorage.setItem("oncemore.token", S.token); history.replaceState(null, "", location.pathname); }
  else S.token = sessionStorage.getItem("oncemore.token") || "";
  try { applyState(await api("/api/state")); refreshEncodeStatus(); loadRecent(); }
  catch (e) { document.body.innerHTML = `<div class="empty"><h2>oncemore</h2><p>${esc(e.message)}</p><p class="hint">Open the URL printed by <code>oncemore gui</code>.</p></div>`; return; }
  const first = P()?.menus?.[0];
  S.sel = first ? { view: "menu", id: first.id } : { view: "disc" };
  renderAll();
  resumeJob(S.runningJob);
}
// the page was opened (or reloaded) while a build or transcode runs
function resumeJob(job) {
  if (!job) return;
  if (job.kind === "transcode") { if (!S.transcoding) followTranscode(job.id); return; }
  if (S.job && S.job.id === job.id) return;
  S.job = { id: job.id, done: false }; S.jobEvents = []; S.jobNext = 0;
  pollJob();
}
// ---------------------------------------------------------------- tools (menu viewer)
// Selection (V) selects and moves, Text (T) places a text where you click,
// Zoom (Z) zooms in (Alt / Option: out).
function setTool(tool) {
  S.tool = tool;
  renderToolbar();
  if (S.sel.view === "menu") renderMain();
}
// buttons whose areas overlap cannot both be reached reliably: outlined in red
// (areas measured by the server exactly as the build lays them out)
async function checkOverlaps(stage, menu, scale, sx) {
  S.routing = S.routing || {};
  const k = JSON.stringify([menu, curPage(menu), P().disc.standard, P().disc.aspect]);
  clearTimeout(S.overlapTimer);
  S.overlapTimer = setTimeout(async () => {
    if (!S.routing[k]) {
      try { S.routing[k] = await api("/api/routing", { method: "POST", body: { project: S.project, menu: pageId(menu) } }); }
      catch (e) { return; }
    }
    if (!document.body.contains(stage)) return;
    stage.querySelectorAll(".overlap").forEach((n) => n.remove());
    const b = S.routing[k].buttons;
    const hit = new Set();
    for (let i = 0; i < b.length; i++) for (let j = i + 1; j < b.length; j++) {
      const [a0, a1, a2, a3] = b[i].rect, [b0, b1, b2, b3] = b[j].rect;
      if (a0 < b2 && b0 < a2 && a1 < b3 && b1 < a3) { hit.add(i); hit.add(j); }
    }
    for (const i of hit) {
      const [x0, y0, x1, y1] = b[i].rect, d = document.createElement("div");
      d.className = "overlap"; d.dataset.button = b[i].id; d.title = t("overlap_hint");
      Object.assign(d.style, { left: `${x0 * sx * scale}px`, top: `${y0 * scale}px`, width: `${(x1 - x0) * sx * scale}px`, height: `${(y1 - y0) * scale}px` });
      stage.appendChild(d);
    }
  }, S.routing[k] ? 0 : 500);
}
// The pick whip: drag from the ◎ next to a link in Properties to a title, menu
// or playlist (project panel or flowchart) to set that link.
function startWhip(ev, apply, origin) {
  ev.preventDefault();
  const from = origin.getBoundingClientRect();
  const x0 = from.left + from.width / 2, y0 = from.top + from.height / 2;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "whip-line");
  svg.innerHTML = `<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y0}"/><circle cx="${x0}" cy="${y0}" r="4"/>`;
  document.body.appendChild(svg);
  const line = svg.querySelector("line"), dot = svg.querySelector("circle");
  const targetAt = (x, y) => {
    const el = document.elementFromPoint(x, y);
    const nav = el?.closest?.(".nav-item[data-view]");
    if (nav && LISTS[nav.dataset.view]) return { el: nav, action: `${nav.dataset.view}:${nav.dataset.id}` };
    const node = el?.closest?.("[data-node]");
    if (node) {
      const id = node.dataset.node;
      if (id === "playall" || id === "stop") return { el: node, action: id };
      if (/^(title|menu|playlist):/.test(id)) return { el: node, action: id };
    }
    return null;
  };
  let cur = null;
  const move = (e) => {
    line.setAttribute("x2", e.clientX); line.setAttribute("y2", e.clientY);
    dot.setAttribute("cx", e.clientX); dot.setAttribute("cy", e.clientY);
    // near the edge of the flowchart or the project panel: scroll it
    const sc = document.elementFromPoint(e.clientX, e.clientY)?.closest?.("#flow, #sidebar");
    if (sc) {
      const r = sc.getBoundingClientRect();
      if (e.clientX > r.right - 24) sc.scrollLeft += 16; else if (e.clientX < r.left + 24) sc.scrollLeft -= 16;
      if (e.clientY > r.bottom - 24) sc.scrollTop += 16; else if (e.clientY < r.top + 24) sc.scrollTop -= 16;
    }
    const tg = targetAt(e.clientX, e.clientY);
    if (cur?.el !== tg?.el) { cur?.el.classList.remove("whip-target"); tg?.el.classList.add("whip-target"); }
    cur = tg;
  };
  const up = () => {
    window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up);
    svg.remove(); cur?.el.classList.remove("whip-target");
    if (cur) apply(cur.action);
  };
  window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
}
const whipHtml = (key) => `<span class="whip" data-whip="${key}" title="${esc(t("whip_hint"))}" role="button" tabindex="-1">◎</span>`;
// Object menu: stacking order and converting texts and buttons
function arrangeElement(where) {
  const menu = curMenu(), k = S.element;
  if (!menu || !k) return;
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id), l = elementList(mm, k.kind), [it] = l.splice(k.i, 1);
    // (one kind of object stacks over another: pictures over shapes, texts over pictures, buttons on top)
    const to = { front: l.length, back: 0, forward: Math.min(l.length, k.i + 1), backward: Math.max(0, k.i - 1) }[where];
    l.splice(to, 0, it);
    S.element = { kind: k.kind, i: to }; S.sels = [S.element];
  });
}
function convertElement() {
  const menu = curMenu(), k = S.element;
  if (!menu || !k || k.kind === "shape" || k.kind === "image") return;
  commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    if (k.kind === "text") {
      const [tx] = mm.texts.splice(k.i, 1), { text, ...rest } = tx;
      mm.buttons.push({ ...rest, id: uniqueId("button", mm.buttons.map((b) => b.id)), label: text, action: "stop" });
      S.element = { kind: "button", i: mm.buttons.length - 1 };
    } else {
      const b = mm.buttons[k.i];
      if (mm.buttons.length <= 1 || !b.label) return;           // a menu keeps one button
      mm.buttons.splice(k.i, 1);
      const { id, label, action, nav, auto_activate, image, highlight_image, thumbnail, width, ...rest } = b;
      (mm.texts = mm.texts || []).push({ ...rest, text: label });
      S.element = { kind: "text", i: mm.texts.length - 1 };
    }
    S.sels = [S.element];
  });
}

// ---------------------------------------------------------------- routing and linking
// The remote's arrow keys between the buttons, as the disc will have them
// (computed by the server from the real layout; set ones solid, automatic
// ones dashed).
async function drawRouting(stage, menu, scale, sx) {
  S.routing = S.routing || {};
  const k = JSON.stringify([menu, curPage(menu), P().disc.standard, P().disc.aspect]);
  if (!S.routing[k]) {
    try { S.routing[k] = await api("/api/routing", { method: "POST", body: { project: S.project, menu: pageId(menu) } }); }
    catch (e) { return; }
  }
  const r = S.routing[k];
  if (!document.body.contains(stage) || stage.querySelector(".routing")) return;
  const byId = Object.fromEntries(r.buttons.map((b) => [b.id, b]));
  const X = (x) => x * sx * scale, Y = (y) => y * scale;
  const edge = (rect, d) => {
    const [x0, y0, x1, y1] = rect, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    return { up: [cx, y0], down: [cx, y1], left: [x0, cy], right: [x1, cy] }[d];
  };
  const back = { up: "down", down: "up", left: "right", right: "left" };
  // up / down (left / right) pairs run side by side instead of on top of each other
  const nudge = { up: [-4, 0], down: [4, 0], left: [0, -4], right: [0, 4] };
  const paths = [];
  for (const b of r.buttons) {
    for (const d of ["up", "down", "left", "right"]) {
      const to = byId[b.nav[d]];
      if (!to || to.id === b.id) continue;
      const vertical = d === "up" || d === "down";
      const [ax, ay] = edge(b.rect, d), [bx, by] = edge(to.rect, back[d]);
      // wrapping round (down from the last button to the first): an arc
      // outside the buttons instead of a line through them
      const wraps = vertical ? (d === "down") !== (by > ay) : (d === "right") !== (bx > ax);
      let path;
      if (wraps) {
        const side = vertical ? (d === "down" ? "right" : "left") : (d === "right" ? "down" : "up");
        const [sx1, sy1] = edge(b.rect, side), [sx2, sy2] = edge(to.rect, side);
        const out = { right: [36, 0], left: [-36, 0], down: [0, 30], up: [0, -30] }[side];
        const x1 = X(sx1), y1 = Y(sy1), x2 = X(sx2), y2 = Y(sy2);
        const far = vertical ? Math.max(x1, x2) * (side === "right") + Math.min(x1, x2) * (side === "left") : 0;
        const c1 = vertical ? [far + out[0], y1] : [x1, (side === "down" ? Math.max(y1, y2) : Math.min(y1, y2)) + out[1]];
        const c2 = vertical ? [far + out[0], y2] : [x2, c1[1]];
        path = `M${x1.toFixed(1)},${y1.toFixed(1)} C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`;
      } else {
        const [nx, ny] = nudge[d];
        const x1 = X(ax) + nx, y1 = Y(ay) + ny, x2 = X(bx) + nx, y2 = Y(by) + ny;
        path = `M${x1.toFixed(1)},${y1.toFixed(1)} L${x2.toFixed(1)},${y2.toFixed(1)}`;
      }
      const manual = (r.manual[b.id] || []).includes(d);
      paths.push(`<path class="${manual ? "manual" : ""} ${wraps ? "wrap" : ""}" data-route="${esc(b.id)}:${d}" d="${path}" marker-end="url(#route-arrow)"><title>${esc(b.id)} ${d} → ${esc(to.id)}</title></path>`);
    }
  }
  // each button's number on the remote (its place plus the menu's offset)
  r.buttons.forEach((b, i) => {
    const [x0, y0] = b.rect;
    paths.push(`<g class="bnum" data-bnum="${esc(b.id)}"><circle cx="${X(x0) + 9}" cy="${Y(y0) + 9}" r="9"/><text x="${X(x0) + 9}" y="${Y(y0) + 13}" text-anchor="middle">${i + 1 + (menu.button_offset || 0)}</text></g>`);
  });
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "routing");
  svg.setAttribute("width", stage.clientWidth); svg.setAttribute("height", stage.clientHeight);
  svg.innerHTML = `<defs><marker id="route-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>${paths.join("")}`;
  stage.appendChild(svg);
}
// Drag a title, menu or playlist from the project panel onto a button to link
// it, or onto an empty part of the menu to make a new button for it.
const LINK_TYPE = "application/x-oncemore-link";
function bindLinkSources(root) {
  root.querySelectorAll(".nav-item[data-view]").forEach((el) => {
    const kind = el.dataset.view;
    if (!["title", "menu", "playlist"].includes(kind)) return;
    el.draggable = true;
    el.ondragstart = (e) => { e.dataTransfer.setData(LINK_TYPE, `${kind}:${el.dataset.id}`); e.dataTransfer.effectAllowed = "link"; };
  });
}
function linkLabel(action) {
  const [kind, id] = action.split(":");
  if (kind === "title") { const x = P().titles.find((y) => y.id === id); return (x?.name || id).toUpperCase(); }
  if (kind === "playlist") { const x = (P().playlists || []).find((y) => y.id === id); return (x?.name || id).toUpperCase(); }
  return id.toUpperCase();
}
function bindLinkDrop(stage, menu, scale, sx) {
  const isLink = (e) => [...(e.dataTransfer?.types || [])].includes(LINK_TYPE);
  const clear = () => stage.querySelectorAll(".drop-target").forEach((x) => x.classList.remove("drop-target"));
  stage.addEventListener("dragover", (e) => {
    if (!isLink(e)) return;
    e.preventDefault(); e.dataTransfer.dropEffect = "link";
    clear();
    e.target.closest?.(".el.button")?.classList.add("drop-target");
    stage.classList.add("drop-on");
  });
  stage.addEventListener("dragleave", (e) => { if (!stage.contains(e.relatedTarget)) { clear(); stage.classList.remove("drop-on"); } });
  stage.addEventListener("drop", (e) => {
    if (!isLink(e)) return;
    e.preventDefault(); e.stopPropagation();
    clear(); stage.classList.remove("drop-on");
    const action = e.dataTransfer.getData(LINK_TYPE);
    if (action === `menu:${menu.id}`) return;                  // a menu does not link to itself
    const btn = e.target.closest?.(".el.button");
    const rect = stage.getBoundingClientRect();
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      if (btn) { mm.buttons[Number(btn.dataset.i)].action = action; S.element = { kind: "button", i: Number(btn.dataset.i) }; return; }
      const x = Math.max(0, Math.min(700, Math.round((e.clientX - rect.left) / (sx * scale))));
      const y = Math.max(0, Math.min(discH() - 20, Math.round((e.clientY - rect.top) / scale)));
      const id = uniqueId(action.split(":")[1].replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 30) + "_btn", mm.buttons.map((b) => b.id));
      mm.buttons.push({ id, label: linkLabel(action), x, y, action, ...newOnPage(menu) });
      S.element = { kind: "button", i: mm.buttons.length - 1 };
    });
    S.sels = [S.element];
  });
}

// ---------------------------------------------------------------- commands
// Everything the menus can do, in one place: the menu bar (in a browser), the
// Mac app's own menu bar (it calls window.oncemoreCommand), right-click menus
// and keyboard shortcuts all run these. "mod" is ⌘ on a Mac and Ctrl elsewhere.
const IS_MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
const IN_APP = /OncemoreApp/.test(navigator.userAgent);
const LISTS = { title: "titles", menu: "menus", playlist: "playlists" };
const hasProject = () => !!P();
const editing = () => (["title", "menu", "playlist"].includes(S.sel.view) && (P()[LISTS[S.sel.view]] || []).some((x) => x.id === S.sel.id));
function deleteItem(kind, id) {
  const x = (P()[LISTS[kind]] || []).find((y) => y.id === id);
  if (!x || !confirm(t("confirm_delete", { x: x.name || x.id }))) return;
  // what pointed at it (and at a title's generated chapter menus) stops instead
  const gone = new Set([`${kind}:${id}`, ...(kind === "title" ? generatedMenus().filter((g) => g.title === id).map((g) => `menu:${g.id}`) : [])]);
  commit((p) => {
    p[LISTS[kind]] = p[LISTS[kind]].filter((y) => y.id !== id);
    if (kind === "playlist" && !p.playlists.length) delete p.playlists;
    dropRefs(p, gone, kind === "title" ? id : null);
  });
  select("disc");
}
function dropRefs(p, gone, titleId) {
  const dead = (a) => !!a && (gone.has(a) || (titleId && a.startsWith(`chapter:${titleId}:`)));
  if (dead(p.disc.first_play)) delete p.disc.first_play;
  if (dead(p.disc.title_key)) delete p.disc.title_key;
  for (const ti of p.titles || []) {
    if (dead(ti.end_action)) ti.end_action = "stop";
    if (ti.auto_chapter_menu && typeof ti.auto_chapter_menu === "object" && dead(ti.auto_chapter_menu.back)) delete ti.auto_chapter_menu.back;
  }
  for (const m of p.menus || []) {
    for (const b of m.buttons || []) {
      if (dead(b.action)) { b.action = "stop"; delete b.override; delete b.transition; }
      if (dead(b.override)) delete b.override;
    }
    if (dead(m.end_action)) m.end_action = "stop";
  }
  for (const pl of p.playlists || []) {
    if (dead(pl.end_action)) pl.end_action = "stop";
    if (titleId) pl.items = pl.items.filter((it) => it !== titleId && !it.startsWith(titleId + ":"));
  }
  if (p.playlists) p.playlists = p.playlists.filter((pl) => pl.items.length);
  if (p.playlists && !p.playlists.length) delete p.playlists;
}
function duplicateItem(kind, id) {
  const list = P()[LISTS[kind]] || [], i = list.findIndex((y) => y.id === id);
  if (i < 0) return;
  const ids = kind === "menu" ? allMenuIds() : list.map((y) => y.id);
  const nid = uniqueId(`${id.replace(/_copy\d*$/, "")}_copy`, ids);
  commit((p) => {
    const c = JSON.parse(JSON.stringify(p[LISTS[kind]][i]));
    c.id = nid;
    if (c.name) c.name = t("copy_of", { x: c.name });
    if (kind === "title") delete c.auto_chapter_menu;      // its chapter menus would clash
    p[LISTS[kind]].splice(i + 1, 0, c);
  });
  select(kind, nid);
}
function moveItem(kind, id, delta) {
  const list = P()[LISTS[kind]] || [], i = list.findIndex((y) => y.id === id), j = i + delta;
  if (i < 0 || j < 0 || j >= list.length) return;
  commit((p) => { const l = p[LISTS[kind]]; [l[i], l[j]] = [l[j], l[i]]; });
}
function setFirstPlay(kind, id) { commit((p) => { p.disc.first_play = `${kind}:${id}`; }); }
function pickPsd() {
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".psd,.psb";
  inp.onchange = () => { if (inp.files[0]) { S.psdAfterUpload = inp.files[0].name; uploadFiles([inp.files[0]]); } };
  inp.click();
}
function revealProject() {
  api("/api/reveal", { method: "POST", body: { path: "project.oncemore.json" } }).catch((e) => alert(e.message));
}
function aboutBox() {
  openModal(`<h2>oncemore</h2><p>${esc(t("about_text"))}</p><p class="hint">${esc(S.version || "")} · GPL-3.0</p>
    <p>${esc(t("sponsor_text"))}</p><div class="dlg-buttons"><span class="spacer"></span><button id="about-sponsor">${esc(t("cmd_sponsor"))}</button></div>`);
  $("#about-sponsor").onclick = () => openLink(SPONSOR_URL);
}
function shortcutsSheet() {
  const rows = Object.entries(COMMANDS).filter(([, c]) => c.key && !c.app).map(([id, c]) => `<tr><td>${esc(t("cmd_" + id))}</td><td class="mono">${esc(keyLabel(c.key))}</td></tr>`).join("");
  openModal(`<h2>${t("cmd_shortcuts")}</h2><table class="shortcuts">${rows}
    <tr><td>${esc(t("nudge"))}</td><td class="mono">← ↑ → ↓ / ${esc(keyLabel("shift"))}</td></tr></table>`);
}
const WS = (k) => () => {
  if (k === "author") { if (S.leftTab === "build") S.leftTab = "project"; const last = S.lastAuthor || { view: "disc" }; select(last.view, last.id); }
  else select(k);
};
// what a command acts on
const inMenu = () => S.sel.view === "menu" && !!curMenu();
const inTitle = () => S.sel.view === "title" && !!curTitle();
const oneElement = () => hasElements() && (S.sels?.length || 1) === 1;
const selElements = () => (S.sels?.length ? S.sels : S.element ? [S.element] : []);
const curItem = () => (editing() ? { kind: S.sel.view, id: S.sel.id } : null);
const textField = () => ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName) || !!document.activeElement?.isContentEditable;
const toggle = (key) => () => { S[key] = !S[key]; renderMain(); };
const COMMANDS = {
  // -- File
  new_project: { key: "mod+n", run: () => folderBox("new") },
  open_project: { key: "mod+o", run: () => folderBox("open") },
  ...Object.fromEntries(Array.from({ length: 10 }, (_, i) => [`recent_${i + 1}`, { run: () => openRecent(i), when: () => !!S.recent?.[i]?.exists && S.recent[i].path !== S.dir, label: () => S.recent?.[i]?.name || "" }])),
  save: { key: "mod+s", run: saveNow, when: hasProject },
  save_as: { key: "mod+shift+s", run: () => folderBox("save_as"), when: hasProject },
  revert_backup: { run: backupsBox, when: hasProject },
  import_files: { key: "mod+i", run: pickFiles, when: hasProject },
  import_menu: { run: () => pickUpload(".psd,.psb,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp", false, ([path]) => importAsMenu(path)), when: hasProject },
  import_psd: { run: pickPsd, when: hasProject },
  import_timeline: { run: () => pickUpload("video/*,audio/*,.mkv,.m2ts,.mts,.vob,.ts,.dv,.ac3,.dts", true, (paths) => paths.forEach((x) => mediaAction("title", x))), when: hasProject },
  import_slideshow: { run: () => pickUpload("image/*", true, (paths) => newSlideshow(paths)), when: hasProject },
  import_popup: { run: () => pickUpload(".psd,.psb,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp", false, ([path]) => importAsMenu(path, popupTitle())), when: () => hasProject() && (P().titles || []).length > 0 },
  replace_asset: { run: () => replaceAssetBox(), when: hasProject },
  locate_asset: { run: () => replaceAssetBox(missingAssets()[0]), when: () => hasProject() && missingAssets().length > 0 },
  interpret_footage: { run: () => titleFieldsBox("interpret_footage"), when: () => inTitle() && !curTitle().slideshow },
  transcode_title: { run: () => transcode([S.sel.id]), when: () => S.sel.view === "title" && editing() && !S.transcoding },
  transcode_all: { run: () => transcode(null), when: () => hasProject() && (P().titles || []).length > 0 && !S.transcoding },
  transcode_settings: { run: () => titleFieldsBox("transcode_settings"), when: () => inTitle() && !curTitle().slideshow },
  render_slideshows: { run: renderSlideshows, when: () => hasProject() && (P().titles || []).some((x) => x.slideshow) && !S.rendering },
  project_settings: { run: () => { S.leftTab = S.leftTab === "build" ? "project" : S.leftTab; S.activeFrame = "props"; select("disc"); }, when: hasProject },
  rom_folder: { run: romFilesBox, when: hasProject },
  preview: { key: "shift+space", run: () => { S.simFrom = S.sel.view === "menu" && curMenu() ? S.sel.id : null; select("sim"); }, when: () => hasProject() && (P().titles || []).length > 0 },
  check: { run: runCheck, when: hasProject },
  build: { key: "mod+b", run: () => select("build"), when: hasProject },
  build_dvd_iso: { run: () => buildAs("dvd", "iso"), when: hasProject },
  build_dvd_folder: { run: () => buildAs("dvd", "folder"), when: hasProject },
  build_dvd_disc: { run: () => buildAs("dvd", "disc"), when: hasProject },
  build_bd_iso: { run: () => buildAs("bluray", "iso"), when: hasProject },
  build_bd_folder: { run: () => buildAs("bluray", "folder"), when: hasProject },
  build_bd_disc: { run: () => buildAs("bluray", "disc"), when: hasProject },
  build_web: { run: () => buildAs("web", "folder"), when: hasProject },
  reveal: { run: revealProject, when: hasProject },
  close_window: { app: true, key: "mod+w" },
  // -- Edit
  undo: { key: "mod+z", run: undo, when: () => S.undo.length > 0 },
  redo: { key: "mod+shift+z", run: redo, when: () => S.redo.length > 0 },
  cut: { key: "mod+x", run: () => { copySelection(); deleteSelection(); }, when: () => hasElements() || (!!curItem() && S.sel.view !== "playlist") },
  copy: { key: "mod+c", run: copySelection, when: () => hasElements() || !!curItem() },
  paste: { key: "mod+v", run: pasteClipboard, when: () => (inMenu() && !!S.clip?.length) || (hasProject() && !!S.clipItem) },
  delete: { key: "delete", run: (via) => (hasElements() ? deleteElements() : via !== "key" && deleteItem(S.sel.view, S.sel.id)),
    when: () => hasElements() || editing() },
  duplicate: { key: "mod+d", run: () => (hasElements() ? duplicateElements(false) : duplicateItem(S.sel.view, S.sel.id)),
    when: () => hasElements() || (editing() && S.sel.view !== "playlist") },
  select_all: { key: "mod+a", run: selectAllElements, when: () => inMenu() && menuElements().length > 0 },
  deselect_all: { key: "mod+shift+a", run: () => { S.element = null; S.sels = []; renderMain(); renderInspector(); }, when: hasElements },
  rename: { run: renameBox, when: () => !!curItem() },
  edit_original: { run: editOriginal, when: () => !!originalFile() },
  edit_psd: { run: editPsd, when: () => S.sel.view === "menu" && !!curMenu()?.psd },
  preferences: { key: "mod+,", run: preferencesBox },
  // -- Object
  align_left: alignCmd("left"), align_hcenter: alignCmd("hcenter"), align_right: alignCmd("right"),
  align_top: alignCmd("top"), align_vcenter: alignCmd("vcenter"), align_bottom: alignCmd("bottom"),
  distribute_h: { run: () => S.stageOps.distribute("h"), when: () => stageReady() && selElements().length > 2 },
  distribute_v: { run: () => S.stageOps.distribute("v"), when: () => stageReady() && selElements().length > 2 },
  bring_front: { key: "mod+shift+]", run: () => arrangeElement("front"), when: oneElement },
  bring_forward: { key: "mod+]", run: () => arrangeElement("forward"), when: oneElement },
  send_backward: { key: "mod+[", run: () => arrangeElement("backward"), when: oneElement },
  send_back: { key: "mod+shift+[", run: () => arrangeElement("back"), when: oneElement },
  convert_button: { run: convertElement, when: () => oneElement() && S.element?.kind === "text" },
  convert_object: { run: convertElement, when: () => oneElement() && S.element?.kind === "button" && curMenu().buttons.length > 1 && !!curMenu().buttons[S.element.i]?.label },
  convert: { run: convertElement, when: () => oneElement() && (S.element?.kind === "text" || S.element?.kind === "button") },
  drop_shadow: { run: dropShadowBox, when: () => hasElements() && selElements().some((k) => k.kind === "text" || k.kind === "button") },
  rotate_180: { run: () => turnElements(180), when: hasElements },
  rotate_cw: { run: () => turnElements(90), when: hasElements },
  rotate_ccw: { run: () => turnElements(-90), when: hasElements },
  flip_h: { run: () => flipElements("h"), when: hasElements },
  flip_v: { run: () => flipElements("v"), when: hasElements },
  // -- Menu
  new_menu: { run: () => addMenu(), when: hasProject },
  chapter_index: { run: chapterIndexBox, when: () => hasProject() && (P().titles || []).length > 0 },
  add_page: { run: addPage, when: inMenu },
  delete_page: { run: deletePage, when: () => inMenu() && pagesOf(curMenu()) > 1 },
  add_button: { run: addMenuButton, when: inMenu },
  add_text: { run: addMenuText, when: inMenu },
  add_rectangle: { run: addMenuShape, when: inMenu },
  add_picture: { run: pickMenuPicture, when: inMenu },
  set_link: { key: "mod+l", run: () => $("#inspector select[data-k=action]")?.focus(), when: () => S.sel.view === "menu" && S.element?.kind === "button" },
  default_button: { run: setDefaultButton, when: () => inMenu() && oneElement() && S.element?.kind === "button" && curMenu().default_button !== curMenu().buttons[S.element.i]?.id },
  colour_set: { run: colourSetBox, when: inMenu },
  save_template: { run: saveTemplateBox, when: inMenu },
  save_menu_file: { run: () => exportFile({ kind: "menu", project: S.project, menu: S.sel.id }), when: inMenu },
  tool_select: { key: "v", run: () => setTool("select"), when: inMenu },
  tool_text: { key: "t", run: () => setTool("text"), when: inMenu },
  tool_zoom: { key: "z", run: () => setTool("zoom"), when: inMenu },
  tool_rotate: { key: "r", run: () => setTool("rotate"), when: inMenu },
  set_first_play: { run: () => setFirstPlay(S.sel.view, S.sel.id), when: () => !!curItem() && P().disc.first_play !== `${S.sel.view}:${S.sel.id}` },
  // -- Timeline
  new_timeline: { run: () => newTitleFromMedia(), when: () => hasProject() && mediaOf("video").length > 0 },
  new_slideshow: { run: () => addSlideshow(), when: hasProject },
  new_playlist: { run: () => addPlaylist(), when: () => hasProject() && (P().titles || []).length > 0 },
  chapter_playlist: { run: chapterPlaylistBox, when: () => hasProject() && (P().titles || []).some((x) => chaptersOf(x).length > 1) },
  add_audio_track: { run: addAudioTrackBox, when: () => inTitle() && !curTitle().clips && !curTitle().slideshow },
  add_subtitle_track: { run: addSubtitleTrackBox, when: () => inTitle() && mediaOf("subtitle").length > 0 },
  // (an image script comes with its pictures: choose them together)
  import_subtitles: { run: () => pickUpload(".srt,.vtt,.ass,.ssa,.txt,.png,.bmp,.tif,.tiff,.jpg,.jpeg,.webp", true, (paths) => {
    const path = paths.find((x) => /\.(srt|vtt|ass|ssa|txt)$/i.test(x));
    if (path) /\.txt$/i.test(path) ? textScriptBox(curTitle().id, path) : addSubtitleTrack(curTitle().id, path);
  }), when: inTitle },
  export_subtitles: { run: () => exportSubtitlesBox("srt"), when: () => inTitle() && (curTitle().subtitles || []).length > 0 },
  export_subtitles_script: { run: () => exportSubtitlesBox("script"), when: () => inTitle() && (curTitle().subtitles || []).length > 0 },
  add_chapter: { key: "*", run: () => $("#add-ch")?.click(), when: () => S.sel.view === "title" && !!$("#add-ch") },
  chapters_interval: { run: chaptersAtIntervals, when: () => inTitle() && !curTitle().slideshow && titleLength(curTitle()) > 0 },
  chapters_scenes: { run: chaptersAtScenes, when: () => inTitle() && !curTitle().slideshow && titleLength(curTitle()) > 0 },
  chapters_from_source: { run: chaptersFromSource, when: () => inTitle() && !curTitle().slideshow },
  clear_chapters: { run: clearChapters, when: () => inTitle() && chaptersOf(curTitle()).length > 1 },
  set_poster: { run: setPosterFrame, when: () => inTitle() && !curTitle().slideshow },
  save_frame: { run: saveFrame, when: () => inTitle() && !curTitle().slideshow && !!frameSource() },
  prev_chapter: { key: "pageup", run: () => jumpChapter(-1), when: () => S.sel.view === "title" && !!S.titleSeek },
  next_chapter: { key: "pagedown", run: () => jumpChapter(1), when: () => S.sel.view === "title" && !!S.titleSeek },
  play: { key: "space", run: () => $("#play")?.click(), when: () => S.sel.view === "title" && !!$("#play") },
  chapter_names: { run: () => { const id = S.tl && (S.sel.view === "title" ? S.sel.id : S.lastTitle); S.chapterNames = { ...S.chapterNames, [id]: !(S.chapterNames || {})[id] }; renderTimeline(); },
    when: () => !!S.tl, on: () => !!(S.chapterNames || {})[S.sel.view === "title" ? S.sel.id : S.lastTitle] },
  // -- View
  zoom_in: { key: "+", run: () => zoomMenu(1), when: inMenu },
  zoom_out: { key: "-", run: () => zoomMenu(-1), when: inMenu },
  zoom_fit: { key: "mod+0", run: () => { S.menuZoom = null; renderMain(); }, when: inMenu, on: () => !S.menuZoom },
  zoom_actual: { run: () => { S.menuZoom = 1; renderMain(); }, when: inMenu, on: () => S.menuZoom === 1 },
  safe_area: { run: toggle("showSafe"), when: () => inMenu() || (S.sel.view === "title" && !!$("#mon-safe")), on: () => !!S.showSafe },
  routing: { run: toggle("showRouting"), when: inMenu, on: () => !!S.showRouting },
  snap: { run: () => { S.snap = S.snap === false; renderMain(); }, when: inMenu, on: () => S.snap !== false },
  show_guides: { key: "mod+;", run: () => { S.showGuides = S.showGuides === false; renderMain(); }, when: inMenu, on: () => S.showGuides !== false },
  lock_guides: { key: "mod+alt+;", run: () => { S.lockGuides = !S.lockGuides; renderMain(); }, when: inMenu, on: () => !!S.lockGuides },
  clear_guides: { run: clearGuides, when: () => inMenu() && guideCount(curMenu()) > 0 },
  new_guide: { run: newGuideBox, when: inMenu },
  snap_guides: { key: "mod+shift+;", run: () => { S.snapGuides = S.snapGuides === false; renderMain(); }, when: inMenu, on: () => S.snapGuides !== false },
  view_normal: spCmd("normal"), view_selected: spCmd("highlight"), view_activated: spCmd("select"),
  exact_preview: { run: () => $("#exact")?.click(), when: () => inMenu() && !!$("#exact"), on: () => !!S.preview && !S.spView && S.previewFor === S.sel.id },
  // -- Window
  ws_author: { key: "alt+shift+1", run: WS("author"), when: hasProject },
  ws_flow: { key: "alt+shift+2", run: WS("flow"), when: hasProject },
  ws_sim: { key: "alt+shift+3", run: WS("sim"), when: hasProject },
  ws_build: { key: "alt+shift+4", run: WS("build"), when: hasProject },
  reset_workspace: { run: resetWorkspace },
  win_project: { run: () => showLeft("project"), when: hasProject },
  win_menus: { run: () => showLeft("menus"), when: hasProject },
  win_timelines: { run: () => showLeft("timelines"), when: hasProject },
  win_build: { run: () => showLeft("build"), when: hasProject },
  win_monitor: { run: () => { S.activeFrame = "center"; if (S.lastTitle && (P().titles || []).some((x) => x.id === S.lastTitle)) select("title", S.lastTitle); else select("disc"); }, when: hasProject },
  win_flowchart: { run: () => { S.activeFrame = "center"; select("flow"); }, when: hasProject },
  win_properties: { run: () => { S.activeFrame = "props"; markFrame(); }, when: hasProject },
  win_layers: { run: () => showRight("layers"), when: hasProject },
  win_library: { run: () => showRight("library"), when: hasProject },
  theme: { run: toggleTheme },
  language: { run: toggleLang },
  reload: { app: true, key: "mod+r" },
  full_screen: { app: true, key: "mod+ctrl+f" },
  minimize: { app: true, key: "mod+m" },
  zoom_window: { app: true },
  // -- Help
  help: { run: openHelp },
  shortcuts: { key: "?", run: shortcutsSheet },
  sponsor: { run: () => openLink(SPONSOR_URL) },
  check_updates: { run: checkUpdates },
  about: { run: aboutBox },
};
// The menu bar, in the order disc authoring people know: File, Edit, Object,
// Menu, Timeline, View, Window, Help. [label, items]: an item is a command,
// "-", or [label, items] for a submenu. Commands marked app: true are only in
// the Mac app's own menu bar (it does them itself).
const MENUBAR = [
  ["m_file", ["new_project", "open_project", ["m_open_recent", "@recent"], "-", "save", "save_as", "revert_backup", "-",
    ["m_import_as", ["import_files", "import_menu", "import_timeline", "import_slideshow", "import_popup"]], "import_psd",
    "replace_asset", "locate_asset", "interpret_footage", "-",
    ["m_transcode", ["transcode_title", "transcode_all", "-", "transcode_settings"]], ["m_render", ["render_slideshows"]], "-",
    "project_settings", "rom_folder", "-", "preview", "check",
    ["m_build", ["build", "-", "build_dvd_iso", "build_dvd_folder", "build_dvd_disc", "-", "build_bd_iso", "build_bd_folder", "build_bd_disc", "-", "build_web"]],
    "-", "reveal", "close_window"]],
  ["m_edit", ["undo", "redo", "-", "cut", "copy", "paste", "delete", "duplicate", "-", "select_all", "deselect_all", "-",
    "rename", "edit_original", "edit_psd", "-", "preferences"]],
  ["m_object", [["m_align", ["align_left", "align_hcenter", "align_right", "-", "align_top", "align_vcenter", "align_bottom"]],
    ["m_distribute", ["distribute_h", "distribute_v"]], ["m_arrange", ["bring_front", "bring_forward", "send_backward", "send_back"]], "-",
    ["m_rotate", ["rotate_180", "rotate_cw", "rotate_ccw"]], "flip_h", "flip_v", "-",
    "convert_button", "convert_object", "-", "drop_shadow"]],
  ["m_menu", ["new_menu", "chapter_index", "add_page", "delete_page", "-", "add_button", "add_text", "add_rectangle", "add_picture", "-", "set_link", "default_button",
    "set_first_play", "-", "colour_set", "save_template", "save_menu_file", "-", ["m_tools", ["tool_select", "tool_rotate", "tool_text", "tool_zoom"]]]],
  ["m_timeline", ["new_timeline", "new_slideshow", "new_playlist", "chapter_playlist", "-", "add_audio_track", "add_subtitle_track",
    "import_subtitles", ["m_export_subs", ["export_subtitles", "export_subtitles_script"]], "-", "add_chapter", "chapters_interval", "chapters_scenes", "chapters_from_source", "clear_chapters", "set_poster", "-",
    "save_frame", "-", "prev_chapter", "next_chapter", "play"]],
  ["m_view", ["zoom_in", "zoom_out", "zoom_fit", "zoom_actual", "-", "safe_area", "routing", "snap", "-",
    "show_guides", "lock_guides", "clear_guides", "new_guide", "snap_guides", "-", "chapter_names", "-",
    ["m_highlights", ["view_normal", "view_selected", "view_activated"]], "exact_preview"]],
  ["m_window", [["m_workspace", ["ws_author", "ws_flow", "ws_sim", "ws_build", "-", "reset_workspace"]], "-",
    "win_project", "win_menus", "win_timelines", "win_build", "win_monitor", "win_flowchart", "win_properties", "win_layers", "win_library", "-",
    "theme", "language", "-", "reload", "full_screen", "minimize", "zoom_window"]],
  ["m_help", ["help", "shortcuts", "-", "check_updates", "sponsor", "about"]],
];
const MENU_ROLES = { m_file: "file", m_edit: "edit", m_window: "window", m_help: "help" };
// the menu items as the page shows them (and posts them to the Mac app)
function menuItems(ids) {
  const out = [];
  for (const id of ids) {
    if (id === "-") { if (out.length && out[out.length - 1] !== "-") out.push("-"); continue; }
    if (Array.isArray(id)) {
      const [label, sub] = id, items = sub === "@recent" ? recentItems() : menuItems(sub);
      out.push({ label: t(label), sub: items, disabled: !items.some((x) => x !== "-" && !x.disabled) });
      continue;
    }
    if (COMMANDS[id].app && !IN_APP) continue;
    out.push(cmdItem(id));
  }
  while (out[out.length - 1] === "-") out.pop();
  return out;
}
function recentItems() {
  const list = (S.recent || []).map((r, i) => (i < 10 ? cmdItem(`recent_${i + 1}`) : null)).filter(Boolean);
  return list.length ? list : [{ label: t("no_recent"), disabled: true, run: () => {} }];
}
// -- the Mac app's menu bar is made from the same list (posted when it changes)
window.oncemoreMenuSpec = () => MENUBAR.map(([label, ids]) => ({ title: t(label), role: MENU_ROLES[label] || "", items: specItems(menuItems(ids)) }));
const specItems = (items) => items.map((x) => (x === "-" ? "-" : { id: x.id || "", label: x.label, key: x.spec || "", disabled: !!x.disabled, checked: !!x.checked, ...(x.sub ? { sub: specItems(x.sub) } : {}) }));
let lastSpec = "";
function postMenuSpec() {
  const h = window.webkit?.messageHandlers?.oncemoreMenu;
  if (!h) return;
  clearTimeout(S.specTimer);
  S.specTimer = setTimeout(() => {
    const spec = JSON.stringify(window.oncemoreMenuSpec());
    if (spec !== lastSpec) { lastSpec = spec; h.postMessage(spec); }
  }, 120);
}

// ---------------------------------------------------------------- File
async function loadRecent() {
  try { S.recent = (await api("/api/recent")).recent; } catch (e) { S.recent = []; }
  postMenuSpec();
}
// after File > Open / New / Save as: another project folder, a fresh start
function projectSwitched(r) {
  applyState(r);
  S.undo = []; S.redo = []; S.probes = {}; S.preview = null; S.encStatus = null; S.job = null; S.jobEvents = [];
  S.element = null; S.sels = []; S.clip = null; S.clipItem = null; S.psdWatch = null; S.routing = {};
  const first = P()?.menus?.[0];
  S.sel = first ? { view: "menu", id: first.id } : { view: "disc" };
  renderAll(); refreshEncodeStatus(); loadRecent();
  window.webkit?.messageHandlers?.oncemoreProject?.postMessage(S.dir);
}
async function openRecent(i) {
  const r = S.recent?.[i];
  if (!r) return;
  clearTimeout(S.saveTimer); if (S.saveState !== "saved") await save();
  try { projectSwitched(await api("/api/switch", { method: "POST", body: { path: r.path } })); } catch (e) { alert(e.message); }
}
async function saveNow() {
  clearTimeout(S.saveTimer);
  await save();
}
// File > New project / Open project / Save as: a folder chooser (the page
// cannot use the system's; the Mac app's menu uses its own panels)
async function folderBox(mode) {
  const parent = (d) => d.replace(/[\\/][^\\/]*$/, "") || d;
  const start = S.dir ? parent(S.dir) : "";
  const named = mode !== "open";
  openModal(`<h2>${t("cmd_" + mode)}</h2>
    ${named ? `<label class="field"><span>${t("name")}</span><input id="fb-name" value="${esc(mode === "save_as" ? `${S.dir.split(/[\\/]/).pop()} copy` : "My DVD")}"></label>` : ""}
    <label class="field"><span>${t(named ? "location" : "folder")}</span><div class="row"><input id="fb-path" class="mono"><button class="small shrink" id="fb-up" title="${esc(t("fb_up"))}">↑</button><button class="small shrink" id="fb-home">${t("fb_home")}</button></div></label>
    <div class="fb-list" id="fb-list" role="listbox" aria-label="${esc(t("folders"))}"></div>
    <div class="hint">${esc(t("fb_hint_" + mode))}</div>
    <div class="dlg-buttons"><span class="hint" id="fb-err"></span><span class="spacer"></span><button id="fb-ok" class="primary">${t(mode === "open" ? "open" : "ok")}</button></div>`);
  let cur = null, asked = 0;
  const show = async (path) => {
    const mine = ++asked;            // (only the folder asked for last is shown)
    try {
      const r = await api("/api/dirs?" + new URLSearchParams(path ? { path } : {}));
      if (mine !== asked) return;
      cur = r; $("#fb-path").value = r.path; $("#fb-err").textContent = "";
      $("#fb-up").disabled = !r.parent; $("#fb-home").onclick = () => show(r.home);
      $("#fb-list").innerHTML = r.dirs.length ? r.dirs.map((d) => `<button class="fb-item ${d.project ? "is-project" : ""}" data-dir="${esc(d.name)}">${d.project ? "◉" : "▸"} ${esc(d.name)}</button>`).join("")
        : `<div class="hint">${esc(t("fb_empty"))}</div>`;
      $("#fb-list").querySelectorAll("[data-dir]").forEach((b) => {
        const full = r.path.replace(/[\\/]$/, "") + "/" + b.dataset.dir;
        b.onclick = () => show(full);
        b.ondblclick = () => { if (mode === "open") go(full); };
      });
    } catch (e) { if (mine === asked) $("#fb-err").textContent = e.message; }
  };
  $("#fb-path").onchange = () => show($("#fb-path").value.trim());
  $("#fb-up").onclick = () => cur?.parent && show(cur.parent);
  const go = async (path) => {
    clearTimeout(S.saveTimer); if (P() && S.saveState !== "saved") await save();
    try {
      const r = mode === "save_as" ? await api("/api/save_as", { method: "POST", body: { path, project: S.project } })
        : await api("/api/switch", { method: "POST", body: { path, create: mode === "new" } });
      closeModal(); projectSwitched(r);
    } catch (e) { $("#fb-err").textContent = e.message; }
  };
  $("#fb-ok").onclick = () => {
    const base = ($("#fb-path").value.trim() || cur?.path || "").replace(/[\\/]$/, "");
    const name = named ? $("#fb-name").value.trim().replace(/[\\/]/g, "_") : "";
    if (named && !name) return;
    go(named ? `${base}/${name}` : base);
  };
  await show(start);
}
function importAsMenu(path, popupFor) {
  const name = path.split("/").pop().replace(/\.[^.]+$/, "");
  const id = uniqueId(name.replace(/[^A-Za-z0-9_-]+/g, "_").toLowerCase().slice(0, 30) || "menu", allMenuIds());
  const done = () => { if (popupFor && allMenuIds().includes(id)) commit((p) => { p.titles.find((x) => x.id === popupFor).remote_menu = id; }); };
  if (/\.(psd|psb)$/i.test(path)) importPsd(path, id).then(done);
  else { mediaAction("newmenu", path); const mid = S.sel.id; if (popupFor) commit((p) => { p.titles.find((x) => x.id === popupFor).remote_menu = mid; }); }
}
// the title a pop-up menu is for: the one open, else the last one opened, else the first
const popupTitle = () => (inTitle() ? S.sel.id : (P().titles || []).some((x) => x.id === S.lastTitle) ? S.lastTitle : P().titles[0].id);
function newSlideshow(images) {
  const id = uniqueId("slides", (P().titles || []).map((x) => x.id));
  commit((p) => { (p.titles = p.titles || []).push({ id, name: t("slideshow"), slideshow: { slides: images.map((image) => ({ image })) } }); });
  select("title", id);
}
const missingAssets = () => { const have = new Set(S.media.map((m) => m.path)); return [...assetRefs().keys()].filter((x) => !have.has(x)); };
// Interpret footage / Transcode settings: the title's own settings in a dialog
function titleFieldsBox(which) {
  const ti = curTitle(), audio = ti.audio || {}, copy = ti.transcode === false;
  const scan = copy ? "" : `<label class="field"><span>${t("scan")}</span>${selectHtml("scan", [["__none__", t("scan_auto")], ["progressive", t("scan_progressive")], ["interlaced", t("scan_interlaced")], ...(P().disc.standard === "NTSC" ? [["pulldown", t("scan_pulldown")], ["ivtc", t("scan_ivtc")]] : [])], ti.scan || "__none__")}<div class="hint">${esc(t("scan_hint"))}</div></label>`;
  const body = which === "interpret_footage"
    ? `<label class="field"><span>${t("aspect")}</span>${selectHtml("aspect", [["__none__", `${t("auto")} (${P().disc.aspect})`], ["16:9", "16:9"], ["4:3", "4:3"]], ti.aspect || "__none__")}</label>${scan}`
    : `${ti.clips ? "" : `<label class="field"><span></span><label><input type="checkbox" id="tf-copy" ${copy ? "checked" : ""}> ${t("no_transcode")}</label><div class="hint">${esc(t("no_transcode_hint"))}</div></label>`}
      <label class="field"><span>${t("video_bitrate")}</span>${selectHtml("video_bitrate", [["__none__", t("auto_shared")], ...["3M", "4M", "5M", "6M", "7M", "8M"].map((b) => [b, b.replace("M", " Mbit/s")])], ti.video_bitrate || "__none__", copy ? "disabled" : "")}</label>
      <label class="field"><span>${t("codec")}</span>${selectHtml("audio.codec", [["ac3", "AC-3"], ["lpcm", "LPCM"], ["dts", t("dts_copy")]], audio.codec || "ac3")}${audio.codec === "dts" ? `<div class="hint">${esc(t("dts_hint"))}</div>` : ""}</label>
      <label class="field"><span>${t("bitrate")}</span>${selectHtml("audio.bitrate", [["128k", "128k"], ["192k", "192k"], ["224k", "224k"], ["256k", "256k"], ["384k", "384k"], ["448k", "448k"]], audio.bitrate || (audio.channels === 6 ? "448k" : "192k"), audio.codec === "lpcm" || audio.codec === "dts" ? "disabled" : "")}</label>
      <label class="field"><span>${t("channels")}</span>${selectHtml("audio.channels", [["2", t("stereo")], ["6", t("surround")]], String(audio.channels || (audio.codec === "dts" ? 6 : 2)), audio.codec === "lpcm" ? "disabled" : "")}</label>`;
  openModal(`<h2>${t("cmd_" + which)}</h2><div class="hint">${esc(ti.name || ti.id)}</div>${body}
    <div class="dlg-buttons"><span class="spacer"></span><button id="tf-ok" class="primary">OK</button></div>`);
  const root = $("#modal-body"), id = ti.id, find = (p) => p.titles.find((x) => x.id === id);
  bindFields(root, find, {
    numeric: ["audio.channels"],
    onAfter: (p, key, val) => {
      const a = find(p).audio;
      if (a && (key === "audio.codec" && val === "lpcm" || key === "audio.channels" && val === (a.codec === "dts" ? 6 : 2))) delete a.channels;
      if (a && key === "audio.codec" && (val === "lpcm" || val === "dts")) delete a.passthrough;
      if (a && key === "audio.codec" && val === "dts") delete a.bitrate;
      if (a && !Object.keys(a).length) delete find(p).audio;
    },
  });
  const cp = $("#tf-copy");
  if (cp) cp.onchange = () => { commit((p) => { const x = find(p); if (cp.checked) { x.transcode = false; delete x.scan; delete x.video_bitrate; } else delete x.transcode; }); titleFieldsBox(which); };
  root.querySelector("[data-k='audio.codec']")?.addEventListener("change", () => setTimeout(() => titleFieldsBox(which), 0));
  $("#tf-ok").onclick = closeModal;
}
// File > Render > Slideshows: make every slideshow's video now
async function renderSlideshows() {
  const list = (P().titles || []).filter((x) => x.slideshow);
  clearTimeout(S.saveTimer); await save();
  S.rendering = true;
  const errors = [];
  for (const [i, ti] of list.entries()) {
    openModal(`<h2>${t("cmd_render_slideshows")}</h2><p>${esc(t("rendering_n", { i: i + 1, n: list.length, t: ti.name || ti.id }))}</p>`);
    try { await api("/api/slideshow", { method: "POST", body: { title: ti.id, project: S.project } }); }
    catch (e) { errors.push(`${ti.name || ti.id}: ${e.message}`); }
  }
  S.rendering = false;
  openModal(`<h2>${t("cmd_render_slideshows")}</h2>${errors.length ? `<ul class="issues">${errors.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p>✓ ${esc(t("rendered_n", { n: list.length }))}</p>`}`);
}
// File > DVD-ROM content: folders and files put next to VIDEO_TS
async function romFilesBox() {
  let dirs = [];
  try { dirs = (await api("/api/dirs?" + new URLSearchParams({ path: S.dir }))).dirs.map((d) => d.name).filter((n) => !["media", "output", "exports"].includes(n)); } catch (e) { dirs = []; }
  const cur = P().disc.rom_files || [];
  openModal(`<h2>${t("cmd_rom_folder")}</h2><div class="hint">${esc(t("rom_hint"))}</div>
    ${dirs.length ? `<div class="fb-list">${dirs.map((d) => `<label class="fb-item"><input type="checkbox" data-rom="${esc(d + "/")}" ${cur.includes(d + "/") || cur.includes(d) ? "checked" : ""}> ${esc(d)}/</label>`).join("")}</div>` : ""}
    <label class="field"><span>${t("rom_files")}</span><textarea id="rom-list" rows="4" class="mono">${esc(cur.join("\n"))}</textarea></label>
    <div class="dlg-buttons"><span class="spacer"></span><button id="rom-ok" class="primary">OK</button></div>`);
  document.querySelectorAll("[data-rom]").forEach((c) => (c.onchange = () => {
    const lines = $("#rom-list").value.split("\n").map((x) => x.trim()).filter(Boolean).filter((x) => x !== c.dataset.rom && x !== c.dataset.rom.slice(0, -1));
    if (c.checked) lines.push(c.dataset.rom);
    $("#rom-list").value = lines.join("\n");
  }));
  $("#rom-ok").onclick = () => {
    const list = $("#rom-list").value.split("\n").map((x) => x.trim()).filter(Boolean);
    closeModal();
    commit((p) => { if (list.length) p.disc.rom_files = list; else delete p.disc.rom_files; });
  };
}
function buildAs(format, kind) { S.buildFormat = format; S.buildKind = kind; select("build"); }

// ---------------------------------------------------------------- Edit
// Cut / Copy / Paste: the selected objects of a menu, else the title, menu or
// playlist selected in the project
function copySelection() {
  if (hasElements()) { copyElements(); S.clipItem = null; return; }
  const it = curItem();
  if (!it) return;
  S.clipItem = { kind: it.kind, data: clone((P()[LISTS[it.kind]] || []).find((x) => x.id === it.id)) };
  S.clip = null;
}
function deleteSelection() {
  if (hasElements()) deleteElements();
  else if (curItem()) deleteItem(S.sel.view, S.sel.id);
}
function pasteClipboard() {
  if (inMenu() && S.clip?.length) { duplicateElements(true); return; }
  const c = S.clipItem;
  if (!c) return;
  const list = P()[LISTS[c.kind]] || [], ids = c.kind === "menu" ? allMenuIds() : list.map((y) => y.id);
  const nid = ids.includes(c.data.id) ? uniqueId(`${c.data.id.replace(/_copy\d*$/, "")}_copy`, ids) : c.data.id;
  commit((p) => {
    const x = clone(c.data);
    x.id = nid;
    if (c.kind === "title" && nid !== c.data.id) delete x.auto_chapter_menu;
    (p[LISTS[c.kind]] = p[LISTS[c.kind]] || []).push(x);
  });
  select(c.kind, nid);
}
const menuElements = () => {
  const m = curMenu();
  return m ? Object.entries(KIND_LIST).flatMap(([kind, l]) => (m[l] || []).map((x, i) => ({ kind, i, hidden: x.hidden }))).filter((x) => !x.hidden).map(({ kind, i }) => ({ kind, i })) : [];
};
function selectAllElements() {
  const all = menuElements();
  S.sels = all; S.element = all[all.length - 1] || null;
  renderMain(); renderInspector();
}
// Edit > Rename: a title's or playlist's name and id, a menu's id (what
// points at it follows)
function renameBox() {
  const { kind, id } = curItem(), x = (P()[LISTS[kind]] || []).find((y) => y.id === id), named = kind !== "menu";
  openModal(`<h2>${t("cmd_rename")}</h2>
    ${named ? `<label class="field"><span>${t("name")}</span><input id="rn-name" value="${esc(x.name || "")}"></label>` : ""}
    <label class="field"><span>${t("id")}</span><input id="rn-id" class="mono" value="${esc(x.id)}"><div class="hint">${esc(t("rename_hint"))}</div></label>
    <div class="dlg-buttons"><span class="hint" id="rn-err"></span><span class="spacer"></span><button id="rn-ok" class="primary">OK</button></div>`);
  (named ? $("#rn-name") : $("#rn-id")).select();
  $("#rn-ok").onclick = () => {
    const nid = $("#rn-id").value.trim().replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 40), name = named ? $("#rn-name").value.trim() : null;
    const ids = kind === "menu" ? allMenuIds() : (P()[LISTS[kind]] || []).map((y) => y.id);
    if (!nid || (nid !== id && ids.includes(nid))) { $("#rn-err").textContent = t("id_taken"); return; }
    closeModal();
    commit((p) => {
      const y = p[LISTS[kind]].find((z) => z.id === id);
      if (named) { if (name) y.name = name; else delete y.name; }
      if (nid !== id) { renameRefs(p, kind, id, nid); y.id = nid; }
    });
    S.sel = { view: kind, id: nid }; renderAll();
  };
}
// Edit > Edit original: the file in the program the system opens it with
function originalFile() {
  if (S.selectedMedia && S.sel.view === "disc") return S.selectedMedia;
  if (inTitle()) { const ti = curTitle(); return ti.slideshow ? null : ti.clips ? frameSource()?.path : ti.source; }
  if (inMenu()) {
    const m = curMenu(), k = S.element;
    const it = k ? elementList(m, k.kind)[k.i] : null;
    return it?.file || it?.image || m.psd || m.background || m.background_video || null;
  }
  return null;
}
function editOriginal() {
  api("/api/open", { method: "POST", body: { path: originalFile() } })
    .then((r) => { if (!r.opened) alert(t("open_failed")); }).catch((e) => alert(e.message));
}

// ---------------------------------------------------------------- Object
const stageReady = () => inMenu() && S.stageOps?.menu === S.sel.id && !!$("#stage");
function alignCmd(k) { return { run: () => S.stageOps.align(k), when: () => stageReady() && hasElements() }; }
// Object > Drop shadow: the shadow and the outline (stroke) of the selected texts and buttons
function dropShadowBox() {
  const menu = curMenu(), ks = selElements().filter((k) => k.kind === "text" || k.kind === "button");
  const first = elementList(menu, ks[0].kind)[ks[0].i];
  const row = (k, def, w, wdef, wl) => `<label class="field" data-nobind><span>${t(k === "shadow" ? "shadow" : "outline")}</span><div class="row cset">
      <input type="checkbox" class="shrink" id="ds-${k}-on" ${first[k] ? "checked" : ""}>
      <input type="color" class="shrink" id="ds-${k}" value="${esc((first[k] || def).slice(0, 7).toLowerCase())}">
      <input type="number" class="shrink" style="width:64px" min="1" max="20" id="ds-${w}" value="${first[w] || wdef}" title="${esc(t(wl))}"><span class="hint shrink">px</span></div></label>`;
  openModal(`<h2>${t("cmd_drop_shadow")}</h2><div class="hint">${esc(t("n_selected", { n: ks.length }))}</div>
    ${row("shadow", "#000000", "shadow_offset", 3, "shadow_offset")}${row("outline", "#000000", "outline_width", 2, "outline_width")}
    <div class="dlg-buttons"><span class="spacer"></span><button id="ds-ok" class="primary">OK</button></div>`);
  $("#ds-ok").onclick = () => {
    const v = (id) => $(id).value, on = (id) => $(id).checked;
    closeModal();
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const k of ks) {
        const it = elementList(mm, k.kind)[k.i];
        for (const [a, w, wdef] of [["shadow", "shadow_offset", 3], ["outline", "outline_width", 2]]) {
          if (!on(`#ds-${a}-on`)) { delete it[a]; delete it[w]; continue; }
          it[a] = v(`#ds-${a}`).toUpperCase();
          const n = Math.max(1, Math.min(20, Math.round(Number(v(`#ds-${w}`)) || wdef)));
          if (n === wdef) delete it[w]; else it[w] = n;
        }
      }
    });
  };
}

// ---------------------------------------------------------------- Menu
function addMenuText() {
  const H = discH();
  commit((p) => {
    const mm = p.menus.find((x) => x.id === S.sel.id);
    (mm.texts = mm.texts || []).push({ text: "TEXT", x: 80, y: Math.round(H / 2), ...newOnPage(curMenu()) });
    S.element = { kind: "text", i: mm.texts.length - 1 }; S.sels = [S.element];
  });
  setTimeout(() => { const f = $("#inspector [data-k=text]"); if (f) { f.focus(); f.select?.(); } }, 0);
}
function setDefaultButton() {
  const i = S.element.i;
  commit((p) => { const mm = p.menus.find((x) => x.id === S.sel.id); mm.default_button = mm.buttons[i].id; });
}
function colourSetBox() {
  const menu = curMenu();
  openModal(`<h2>${t("cmd_colour_set")}</h2><div class="hint">${esc(menu.id)}</div>${colourSetHtml(menu)}
    <div class="dlg-buttons"><span class="spacer"></span><button id="cs-ok" class="primary">OK</button></div>`);
  bindColourSet($("#modal-body"), menu);
  $("#cs-ok").onclick = closeModal;
}
// Save menu as file / Save frame as file / Export subtitles: a file in exports/
async function exportFile(body) {
  openModal(`<h2>${t("export")}</h2><p class="hint">…</p>`);
  try {
    const r = await api("/api/export", { method: "POST", body });
    S.media = r.media; renderSidebar();
    openModal(`<h2>${t("export")}</h2><p>${esc(t("exported_to"))}</p><p class="mono">${esc(r.path)}</p>
      <div class="dlg-buttons"><span class="spacer"></span><button id="ex-reveal">${t(S.platform === "darwin" ? "reveal" : "reveal_other")}</button></div>`);
    $("#ex-reveal").onclick = () => api("/api/reveal", { method: "POST", body: { path: r.path } }).catch((e) => alert(e.message));
  } catch (e) {
    if (e.data?.issues) showIssues(e.data.issues, t("export"));
    else openModal(`<h2>${t("export")}</h2><p>${esc(e.message)}</p>${e.data?.output ? `<pre class="log">${esc(e.data.output)}</pre>` : ""}`);
  }
}

// ---------------------------------------------------------------- Timeline
function chapterPlaylistBox() {
  const ts = (P().titles || []).filter((x) => chaptersOf(x).length > 1);
  openModal(`<h2>${t("cmd_chapter_playlist")}</h2>
    <label class="field"><span>${t("title")}</span><select id="cp-title">${ts.map((x) => `<option value="${esc(x.id)}" ${S.lastTitle === x.id ? "selected" : ""}>${esc(x.name || x.id)} (${chaptersOf(x).length})</option>`).join("")}</select></label>
    <div class="hint">${esc(t("chapter_playlist_hint"))}</div>
    <div class="dlg-buttons"><span class="spacer"></span><button id="cp-ok" class="primary">OK</button></div>`);
  $("#cp-ok").onclick = () => {
    const ti = P().titles.find((x) => x.id === $("#cp-title").value), n = chaptersOf(ti).length;
    const id = uniqueId(`${ti.id}_chapters`, (P().playlists || []).map((x) => x.id));
    closeModal();
    commit((p) => { (p.playlists = p.playlists || []).push({ id, name: t("chapters_of", { t: ti.name || ti.id }), items: Array.from({ length: n }, (_, i) => `${ti.id}:${i + 1}`) }); });
    select("playlist", id);
  };
}
const LANGS = [["", "—"], ["ja", "日本語 (ja)"], ["en", "English (en)"], ["fr", "Français (fr)"], ["de", "Deutsch (de)"], ["es", "Español (es)"], ["zh", "中文 (zh)"], ["ko", "한국어 (ko)"]];
function addAudioTrackBox() {
  const ti = curTitle();
  openModal(`<h2>${t("cmd_add_audio_track")}</h2><div class="hint">${esc(t("tracks_hint"))}</div>
    <label class="field"><span>${t("source")}</span>${selectHtml("source", [["", `${ti.source} (${t("this_title")})`], ...mediaOf("audio").map((a) => [a, a]), ...mediaOf("video").filter((v) => v !== ti.source).map((v) => [v, v])], "", 'id="at-src"')}</label>
    <label class="field"><span>${t("stream")}</span><input type="number" min="0" id="at-stream" value="${(ti.audio_tracks || []).filter((x) => !x.source).length || 0}"></label>
    <label class="field"><span>${t("language")}</span>${selectHtml("lang", LANGS, "", 'id="at-lang"')}</label>
    <div class="dlg-buttons"><span class="spacer"></span><button id="at-ok" class="primary">OK</button></div>`);
  $("#at-ok").onclick = () => {
    const tr = {}, src = $("#at-src").value, st = Number($("#at-stream").value) || 0, lang = $("#at-lang").value;
    if (src) tr.source = src;
    if (st) tr.stream = st;
    if (lang) tr.lang = lang;
    closeModal();
    commit((p) => { const x = p.titles.find((y) => y.id === ti.id); x.audio_tracks = x.audio_tracks || [{}]; x.audio_tracks.push(tr); });
  };
}
function addSubtitleTrack(tid, file, lang, offset) {
  commit((p) => { const x = p.titles.find((y) => y.id === tid); (x.subtitles = x.subtitles || []).push({ file, ...(lang ? { lang } : {}), ...(offset ? { offset } : {}) }); });
}
// Timeline > Import subtitles, a text script: its language, and whether its
// timecode is the title's (absolute) or counted from a start of its own
function textScriptBox(tid, file) {
  openModal(`<h2>${t("script_import")}</h2><div class="hint">${esc(t("script_hint"))}</div>
    <label class="field"><span>${t("file")}</span><span>${esc(file.replace(/^media\//, ""))}</span></label>
    <label class="field"><span>${t("language")}</span>${selectHtml("lang", LANGS, "", 'id="ts-lang"')}</label>
    <label class="field"><span></span><label><input type="radio" name="tsmode" value="abs" checked> ${t("tc_absolute")}</label></label>
    <label class="field"><span></span><span class="row"><label class="shrink"><input type="radio" name="tsmode" value="rel"> ${t("tc_relative")}</label>
      <input id="ts-offset" class="mono" placeholder="${P().disc.standard === "PAL" ? "01:00:00:00" : "01;00;00;00"}" title="${esc(t("sub_offset_hint"))}"></span></label>
    <div class="dlg-buttons"><span class="spacer"></span><button id="ts-ok" class="primary">OK</button></div>`);
  $("#ts-offset").oninput = () => { $("input[name=tsmode][value=rel]").checked = true; };
  $("#ts-ok").onclick = () => {
    const rel = $("input[name=tsmode]:checked").value === "rel", off = $("#ts-offset").value.trim();
    closeModal();
    addSubtitleTrack(tid, file, $("#ts-lang").value, rel && off ? off : null);
  };
}
function addSubtitleTrackBox() {
  const ti = curTitle();
  openModal(`<h2>${t("cmd_add_subtitle_track")}</h2>
    <label class="field"><span>${t("file")}</span>${selectHtml("file", mediaOf("subtitle").map((f) => [f, f.replace(/^media\//, "")]), mediaOf("subtitle")[0], 'id="st-file"')}</label>
    <label class="field"><span>${t("language")}</span>${selectHtml("lang", LANGS, "", 'id="st-lang"')}</label>
    <div class="dlg-buttons"><span class="spacer"></span><button id="st-ok" class="primary">OK</button></div>`);
  $("#st-ok").onclick = () => { const f = $("#st-file").value, l = $("#st-lang").value; closeModal(); addSubtitleTrack(ti.id, f, l); };
}
// Timeline > Export subtitles ▸ SubRip / Text script: a track (asked for
// when the title has several), timed as the title shows it
function exportSubtitlesBox(format) {
  const subs = curTitle().subtitles;
  const go = (s) => exportFile({ kind: "subtitles", path: s.file, offset: s.offset || "", format });
  if (subs.length === 1) return go(subs[0]);
  openModal(`<h2>${t("m_export_subs")}: ${t(format === "script" ? "fmt_script" : "fmt_srt")}</h2><div class="hint">${esc(t("export_subs_hint"))}</div>
    <div style="display:flex;flex-direction:column;gap:6px">${subs.map((s, i) => `<button data-exsub="${i}">${i + 1}. ${esc(s.file.replace(/^media\//, ""))}${s.lang ? ` (${esc(s.lang)})` : ""}</button>`).join("")}</div>`);
  document.querySelectorAll("[data-exsub]").forEach((b) => (b.onclick = () => go(subs[Number(b.dataset.exsub)])));
}
// (links to its chapters then play the title; playlist items the whole title)
function clearChapters() {
  if (!confirm(t("confirm_clear_chapters"))) return;
  const tid = S.sel.id, fix = (a) => (a && a.startsWith(`chapter:${tid}:`) ? `title:${tid}` : a);
  commit((p) => {
    setChapters(p.titles.find((x) => x.id === tid), [{ time: 0, name: "", poster: null }]);
    p.disc.first_play = fix(p.disc.first_play);
    if (p.disc.title_key) p.disc.title_key = fix(p.disc.title_key);
    for (const ti of p.titles || []) {
      if (ti.end_action) ti.end_action = fix(ti.end_action);
      if (ti.auto_chapter_menu && typeof ti.auto_chapter_menu === "object" && ti.auto_chapter_menu.back) ti.auto_chapter_menu.back = fix(ti.auto_chapter_menu.back);
    }
    for (const m of p.menus || []) {
      if (m.end_action) m.end_action = fix(m.end_action);
      for (const b of m.buttons || []) { b.action = fix(b.action); if (b.override) b.override = fix(b.override); }
    }
    for (const pl of p.playlists || []) {
      if (pl.end_action) pl.end_action = fix(pl.end_action);
      pl.items = pl.items.map((it) => (it.startsWith(`${tid}:`) ? tid : it));
    }
  });
}
// Set poster frame: the chapter the playhead is in shows this frame in chapter menus
function setPosterFrame() {
  const ti = curTitle(), now = S.playhead[ti.id] || 0, list = chapterEntries(ti);
  let i = 0;
  list.forEach((c, j) => { if (c.time <= now + 1e-6) i = j; });
  list[i].poster = Math.round(now * 1000) / 1000;
  commit((p) => setChapters(p.titles.find((x) => x.id === ti.id), list));
}
// the file and time inside it shown at the playhead (for clips: the clip there)
function frameSource() {
  const ti = curTitle();
  if (!ti) return null;
  const now = S.playhead[ti.id] || 0;
  if (!ti.clips) return ti.source && mediaOf("video").includes(ti.source) ? { path: ti.source, t: now } : null;
  const join = clipJoinNow(ti);
  if (!join) return null;
  for (const [i, c] of ti.clips.entries()) {
    const j = join.clips[i];
    if (now < j.start + j.duration || i === ti.clips.length - 1) return isStill(c) ? null : { path: c.source, t: (c.in != null ? parseTime(c.in) : 0) + Math.max(0, now - j.start) };
  }
  return null;
}
function saveFrame() { const f = frameSource(); exportFile({ kind: "frame", path: f.path, t: f.t }); }

// ---------------------------------------------------------------- View, Window, Help
function spCmd(state) {
  return {
    run: () => { S.spView = S.spView === state ? null : state; S.preview = null; if (S.spView) requestPreview(S.sel.id, null, false, { every: true, state }); renderMain(); },
    when: inMenu, on: () => S.spView === state,
  };
}
function resetWorkspace() {
  for (const k of ["left-w", "right-w", "timeline-h"]) {
    try { localStorage.removeItem("oncemore." + k); } catch (e) { /* storage blocked */ }
    document.documentElement.style.removeProperty("--" + k);
  }
  if (P()) WS("author")();
}
const SPONSOR_URL = "https://github.com/sponsors/kajisho5";
const RELEASES_URL = "https://github.com/kajisho5/oncemore/releases";
// (the browser opens the page: oncemore makes no connection of its own)
function checkUpdates() {
  openModal(`<h2>${esc(t("cmd_check_updates").replace(/…$/, ""))}</h2><p>${esc(t("updates_text", { v: S.version || "?" }))}</p>
    <div class="dlg-buttons"><span class="spacer"></span><button id="open-releases" class="primary">${esc(t("open_releases"))}</button></div>`);
  $("#open-releases").onclick = () => { openLink(RELEASES_URL); closeModal(); };
}
function openLink(url) {
  if (IN_APP) location.assign(url);              // (the app opens it in the browser)
  else window.open(url, "_blank", "noopener");
}
function openHelp() {
  openLink(`https://github.com/kajisho5/oncemore/blob/main/${LANG === "ja" ? "README.ja.md" : "README.md"}`);
}
// the page's copy / cut / paste events (the Mac app's Edit menu sends these):
// objects and project items when no text is being edited
for (const type of ["copy", "cut", "paste"]) {
  document.addEventListener(type, (e) => {
    if (!P() || textField() || (type !== "paste" && String(window.getSelection?.() || ""))) return;
    if (!runCommand(type, "event")) return;
    e.preventDefault();
  });
}
// File > Revert to a saved version: the server keeps the project file as it
// was before a save, every few minutes (.oncemore-backup/); going back is one
// more edit, so Undo returns to where you were
async function backupsBox() {
  let r;
  try { r = await api("/api/backups"); } catch (e) { alert(e.message); return; }
  const when = (s) => new Date(s * 1000).toLocaleString(LANG === "ja" ? "ja-JP" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
  openModal(`<h2>${t("cmd_revert_backup")}</h2><div class="hint">${esc(t("backups_hint", { m: Math.round(r.every / 60) }))}</div>
    ${r.backups.length ? `<table class="shortcuts backups">${r.backups.map((b) => `<tr><td>${esc(when(b.time))}</td>
      <td class="hint">${esc(t("backup_counts", { t: b.titles, m: b.menus }))}</td><td class="mono">${esc(fmtBytes(b.bytes))}</td>
      <td><button class="small" data-backup="${esc(b.name)}">${t("revert")}</button></td></tr>`).join("")}</table>`
      : `<p class="hint">${esc(t("no_backups"))}</p>`}`);
  document.querySelectorAll("[data-backup]").forEach((b) => (b.onclick = async () => {
    if (!confirm(t("confirm_revert"))) return;
    try {
      const { project } = await api("/api/backup?" + new URLSearchParams({ name: b.dataset.backup }));
      S.undo.push(JSON.stringify(S.project)); S.redo = [];
      S.project = project; S.preview = null; S.probes = {};
      closeModal(); scheduleSave();
      const first = P().menus?.[0];
      select(first ? "menu" : "disc", first?.id);
      refreshEncodeStatus();
    } catch (err) { alert(err.message); }
  }));
}
// Menu > Save menu as template: the menu and copies of its files go to the
// template library (for every project); the Library lists them
function saveTemplateBox() {
  const menu = curMenu();
  if (!menu) return;
  openModal(`<h2>${t("cmd_save_template")}</h2>
    <label class="field"><span>${t("name")}</span><input id="tpl-name" value="${esc(menu.id)}"></label>
    <div class="hint">${esc(t("utpl_hint"))}</div>
    <div class="dlg-buttons"><span class="spacer"></span><button id="tpl-ok" class="primary">OK</button></div>`);
  $("#tpl-name").select();
  $("#tpl-ok").onclick = async () => {
    try {
      const r = await api("/api/save_template", { method: "POST", body: { menu, name: $("#tpl-name").value } });
      S.userTemplates = r.templates;
      openModal(`<h2>${t("cmd_save_template")}</h2><p>${esc(t("utpl_saved", { n: $("#tpl-name")?.value || menu.id }))}</p>`);
      S.rightTab = "library"; renderLayers();
    } catch (err) { alert(err.message); }
  };
}
async function applyUserTemplate(tid) {
  const x = S.userTemplates.find((y) => y.id === tid), ids = allMenuIds(), id = ids.includes(tid) ? uniqueId(`${tid}_`, ids) : tid;
  try {
    const r = await api("/api/apply_template", { method: "POST", body: { template: tid, id, project: S.project } });
    S.media = r.media;
    commit((p) => { (p.menus = p.menus || []).push(r.menu); });
    select("menu", id);
  } catch (err) { alert(`${x ? x.name : tid}: ${err.message}`); }
}
// Menu > Create chapter index: a chapter menu for a title (the generated
// chapter menus, one page per six chapters), opened in the Menu Viewer
function chapterIndexBox() {
  const ts = (P().titles || []);
  openModal(`<h2>${t("cmd_chapter_index")}</h2>
    <label class="field"><span>${t("title")}</span><select id="ci-title">${ts.map((x) => `<option value="${esc(x.id)}" ${S.lastTitle === x.id ? "selected" : ""}>${esc(x.name || x.id)}${x.auto_chapter_menu ? " ✓" : ""}</option>`).join("")}</select></label>
    <div class="hint">${esc(t("chapter_index_hint"))}</div>
    <div class="dlg-buttons"><span class="spacer"></span><button id="cix-ok" class="primary">OK</button></div>`);
  $("#cix-ok").onclick = () => {
    const tid = $("#ci-title").value;
    closeModal();
    if (!(P().titles || []).find((x) => x.id === tid)?.auto_chapter_menu) commit((p) => { p.titles.find((x) => x.id === tid).auto_chapter_menu = true; });
    const g = generatedMenus().find((m) => m.title === tid);
    if (g) select("menu", g.id);
  };
}
// Window > (panel): bring a panel to the front of its frame
function showLeft(tab) { S.leftTab = tab; S.activeFrame = "left"; renderLeft(); renderWorkspaces(); markFrame(); }
function showRight(tab) { S.rightTab = tab; S.activeFrame = "layers"; renderLayers(); markFrame(); }
// the length of a title as the app knows it (joined clips or the probed file)
function titleLength(ti) {
  if (!ti) return 0;
  if (ti.clips) { const j = clipJoinNow(ti); return j ? j.duration : 0; }
  return S.probes[ti.source]?.duration || 0;
}
// the chapter markers in a title's source file(s), on the title's timeline
// (for clips: the markers inside each clip, moved to where the clip plays)
function sourceChapters(ti) {
  if (!ti || ti.slideshow) return [];
  const marks = (path) => (S.probes[path]?.chapters || []);
  let out = [];
  if (ti.clips) {
    const join = clipJoinNow(ti);
    if (!join) return [];
    ti.clips.forEach((c, i) => {
      const j = join.clips[i], a = c.in != null ? parseTime(c.in) : 0, b = a + j.duration;
      for (const m of marks(c.source)) if (m.time >= a - 1e-6 && m.time < b - 0.5) out.push({ time: j.start + m.time - a, name: m.name || "" });
    });
  } else out = marks(ti.source).map((m) => ({ time: m.time, name: m.name || "" }));
  out = out.filter((m, i) => !out.slice(0, i).some((o) => Math.abs(o.time - m.time) < 0.5))
    .map((m) => ({ time: Math.round(m.time * 1000) / 1000, name: m.name, poster: null }));
  if (!out.some((m) => m.time < 0.001)) out.unshift({ time: 0, name: "", poster: null });
  return out.sort((a, b) => a.time - b.time);
}
// Timeline > Import chapter markers from the source
async function chaptersFromSource() {
  const ti = curTitle();
  await Promise.all((ti.clips ? ti.clips.map((c) => c.source) : [ti.source]).map(probe));
  const list = sourceChapters(ti);
  if (list.length < 2) return alert(t("no_source_chapters"));
  commit((p) => setChapters(p.titles.find((x) => x.id === ti.id), list));
}
// Timeline > Add chapter points at intervals
function chaptersAtIntervals() {
  const ti = curTitle(), dur = titleLength(ti);
  const last = S.ciLast || { n: 5, unit: 60 };
  openModal(`<h2>${t("cmd_chapters_interval")}</h2>
    <label class="field"><span>${t("ci_every")}</span><div class="row"><input id="ci-n" type="number" min="1" step="1" value="${last.n}" class="shrink" style="width:90px">
      <select id="ci-unit" class="shrink"><option value="60" ${last.unit === 60 ? "selected" : ""}>${t("ci_minutes")}</option><option value="1" ${last.unit === 1 ? "selected" : ""}>${t("ci_seconds")}</option></select></div></label>
    <label class="field"><span></span><label><input type="checkbox" id="ci-replace" checked> ${esc(t("ci_replace"))}</label></label>
    <div class="hint" id="ci-preview"></div>
    <div class="dlg-buttons"><span class="spacer"></span><button id="ci-ok" class="primary">OK</button></div>`);
  const step = () => Number($("#ci-n").value) * Number($("#ci-unit").value);
  const planned = () => {
    const s = step(), keep = $("#ci-replace").checked ? chapterEntries(ti).slice(0, 1) : chapterEntries(ti), out = [...keep];
    if (s > 0) for (let x = s; x < dur - 0.5; x += s) if (!out.some((c) => Math.abs(c.time - x) < 0.5)) out.push({ time: Math.round(x * 1000) / 1000, name: "", poster: null });
    if (!out.length) out.push({ time: 0, name: "", poster: null });
    return out.sort((a, b) => a.time - b.time);
  };
  const upd = () => { $("#ci-preview").textContent = t("ci_preview", { n: planned().length, d: fmtTime(dur, false) }); };
  ["#ci-n", "#ci-unit", "#ci-replace"].forEach((s) => ($(s).oninput = $(s).onchange = upd));
  upd();
  $("#ci-ok").onclick = () => {
    if (!(step() > 0)) return;
    S.ciLast = { n: Number($("#ci-n").value), unit: Number($("#ci-unit").value) };
    const list = planned();
    closeModal();
    commit((p) => setChapters(p.titles.find((x) => x.id === ti.id), list));
  };
}
// Timeline > Add chapter points at scene changes: the cuts ffmpeg finds in the
// picture (each clip of a title made of clips on its own), at least a gap apart
function chaptersAtScenes() {
  const ti = curTitle(), dur = titleLength(ti);
  const last = S.scLast || { level: "medium", gap: 10 };
  openModal(`<h2>${t("cmd_chapters_scenes")}</h2>
    <label class="field"><span>${t("sc_sensitivity")}</span>${selectHtml("sc-level", [["low", t("sc_low")], ["medium", t("sc_medium")], ["high", t("sc_high")]], last.level, 'id="sc-level"')}</label>
    <label class="field"><span>${t("sc_gap")}</span><input id="sc-gap" type="number" min="1" step="1" value="${last.gap}" style="width:90px"></label>
    <label class="field"><span></span><label><input type="checkbox" id="sc-replace" checked> ${esc(t("ci_replace"))}</label></label>
    <div class="hint" id="sc-preview">${esc(t("sc_hint"))}</div>
    <div class="dlg-buttons"><button id="sc-find">${t("sc_find")}</button><span class="spacer"></span><button id="sc-ok" class="primary" disabled>OK</button></div>`);
  let found = null;
  // what to look at: the source, or each clip (where it plays on the title's timeline)
  const parts = () => {
    if (!ti.clips) return [{ path: ti.source, start: 0, end: null, at: 0 }];
    const join = clipJoinNow(ti);
    return ti.clips.map((c, i) => {
      if (isStill(c) || !join) return null;
      const start = c.in != null ? parseTime(c.in) : 0;
      return { path: c.source, start, end: start + join.clips[i].duration, at: join.clips[i].start };
    }).filter(Boolean);
  };
  const planned = () => {
    const keep = $("#sc-replace").checked ? chapterEntries(ti).slice(0, 1) : chapterEntries(ti), out = [...keep];
    for (const x of found || []) if (x < dur - 0.5 && !out.some((c) => Math.abs(c.time - x) < 0.5)) out.push({ time: Math.round(x * 1000) / 1000, name: "", poster: null });
    if (!out.length) out.push({ time: 0, name: "", poster: null });
    return out.sort((a, b) => a.time - b.time);
  };
  const reset = () => { found = null; $("#sc-ok").disabled = true; $("#sc-preview").textContent = t("sc_hint"); };
  ["#sc-level", "#sc-gap"].forEach((s) => ($(s).onchange = reset));
  $("#sc-replace").onchange = () => { if (found) $("#sc-preview").textContent = t("sc_found", { n: found.length, c: planned().length }); };
  $("#sc-find").onclick = async () => {
    const level = $("#sc-level").value, gap = Number($("#sc-gap").value) || 10;
    $("#sc-find").disabled = true; $("#sc-preview").textContent = t("sc_looking");
    try {
      const lists = await Promise.all(parts().map((x) => api("/api/scenes", { method: "POST", body: { path: x.path, sensitivity: level, min_gap: gap, start: x.start, end: x.end } })
        .then((r) => r.times.map((tm) => tm - x.start + x.at))));
      found = lists.flat().sort((a, b) => a - b);
      S.scLast = { level, gap };
      $("#sc-preview").textContent = t("sc_found", { n: found.length, c: planned().length });
      $("#sc-ok").disabled = !found.length;
    } catch (e) { $("#sc-preview").textContent = e.message; }
    finally { if ($("#sc-find")) $("#sc-find").disabled = false; }
  };
  $("#sc-ok").onclick = () => {
    const list = planned();
    closeModal();
    commit((p) => setChapters(p.titles.find((x) => x.id === ti.id), list));
  };
}
// File > Replace asset: every use of one file in the project points to another
const MEDIA_RE = /\.(mp4|m4v|mov|mkv|avi|mpe?g|m2ts|mts|ts|vob|webm|dv|wav|aiff?|mp3|m4a|aac|ac3|dts|flac|png|jpe?g|bmp|tiff?|gif|webp|srt|vtt|ass|ssa|scc|psd|psb|ttf|otf|ttc)$/i;
function assetRefs(p = P()) {
  const uses = new Map();
  const walk = (v) => {
    if (typeof v === "string") { if (MEDIA_RE.test(v)) uses.set(v, (uses.get(v) || 0) + 1); }
    else if (Array.isArray(v)) v.forEach(walk);
    else if (v && typeof v === "object") Object.values(v).forEach(walk);
  };
  walk(p);
  return uses;
}
function replaceAssetRefs(p, from, to) {
  const walk = (v) => {
    if (Array.isArray(v)) { v.forEach((x, i) => { v[i] = walk(x); }); return v; }
    if (v && typeof v === "object") { for (const k of Object.keys(v)) v[k] = walk(v[k]); return v; }
    return v === from ? to : v;
  };
  walk(p);
}
function replaceAssetBox(from) {
  const uses = assetRefs(), have = new Set(S.media.map((m) => m.path));
  const refs = [...uses.keys()].sort((a, b) => (have.has(a) - have.has(b)) || a.localeCompare(b));   // missing first
  if (!refs.length) { openModal(`<h2>${t("cmd_replace_asset")}</h2><p class="hint">${esc(t("ra_none"))}</p>`); return; }
  const cur = from && uses.has(from) ? from : refs[0];
  openModal(`<h2>${t("cmd_replace_asset")}</h2>
    <label class="field"><span>${t("ra_what")}</span><select id="ra-from">${refs.map((r) => `<option value="${esc(r)}" ${r === cur ? "selected" : ""}>${esc(r)}${have.has(r) ? "" : ` — ⚠ ${esc(t("ra_missing"))}`}</option>`).join("")}</select></label>
    <label class="field"><span>${t("ra_with")}</span><select id="ra-to">${S.media.map((m) => `<option value="${esc(m.path)}">${esc(m.path)}</option>`).join("")}</select></label>
    <div class="hint" id="ra-uses"></div><div class="hint">${esc(t("ra_hint"))}</div>
    <div class="dlg-buttons"><span class="spacer"></span><button id="ra-ok" class="primary" ${S.media.length ? "" : "disabled"}>OK</button></div>`);
  const upd = () => {
    $("#ra-uses").textContent = t("ra_uses", { n: uses.get($("#ra-from").value) || 0 });
    const ext = (s) => (s.match(/\.[^.]+$/) || [""])[0].toLowerCase(), want = ext($("#ra-from").value);
    const same = S.media.find((m) => ext(m.path) === want && m.path !== $("#ra-from").value);
    if (same && ext($("#ra-to").value) !== want) $("#ra-to").value = same.path;
  };
  $("#ra-from").onchange = upd; upd();
  $("#ra-ok").onclick = () => {
    const a = $("#ra-from").value, b = $("#ra-to").value;
    closeModal();
    if (!b || a === b) return;
    commit((p) => replaceAssetRefs(p, a, b));
    S.probes = {}; S.preview = null;
    renderAll(); refreshEncodeStatus();
  };
}
// Edit > Edit menu in Photoshop: open the menu's .psd; when it is saved
// there, the Menu Viewer offers to import it again
function editPsd() {
  const menu = curMenu();
  if (!menu?.psd) return;
  api("/api/stat?" + new URLSearchParams({ path: menu.psd })).then((st) => { S.psdWatch = { menu: menu.id, path: menu.psd, mtime: st.mtime }; watchPsd(); }).catch(() => {});
  api("/api/open", { method: "POST", body: { path: menu.psd } })
    .then((r) => { if (!r.opened) alert(t("open_failed")); })
    .catch((e) => alert(e.message));
}
function watchPsd() {
  clearTimeout(S.psdTimer);
  const w = S.psdWatch;
  if (!w || !P()) return;
  S.psdTimer = setTimeout(async () => {
    try {
      const st = await api("/api/stat?" + new URLSearchParams({ path: w.path }));
      if (st.mtime && w.mtime && st.mtime !== w.mtime) {
        w.mtime = st.mtime; S.psdChanged = w.menu;
        if (S.sel.view === "menu" && S.sel.id === w.menu) renderMain();
      }
    } catch (e) { /* the file went away: keep watching */ }
    watchPsd();
  }, 2000);
}
function jumpChapter(dir) {
  const ti = curTitle(), chapters = chaptersOf(ti), now = S.playhead[ti.id] || 0;
  const to = dir > 0 ? chapters.find((c) => c > now + 0.01) : [...chapters].reverse().find((c) => c < now - 0.01);
  if (to != null) S.titleSeek(to); else if (dir < 0) S.titleSeek(0);
}
function zoomMenu(dir) {
  const steps = [0.5, 1, 1.5, 2, 3], cur = S.menuZoom || 1;
  S.menuZoom = dir > 0 ? (steps.find((z) => z > cur + 0.01) || 3) : (steps.filter((z) => z < cur - 0.01).pop() || 0.5);
  renderMain();
}
function newTitleFromMedia() {
  const vids = mediaOf("video");
  openModal(`<h2>${t("cmd_new_timeline")}</h2><p class="hint">${esc(t("new_timeline_hint"))}</p>
    <div style="display:flex;flex-direction:column;gap:6px">${vids.map((v) => `<button data-newtl="${esc(v)}">${esc(v.replace(/^media\//, ""))}</button>`).join("")}</div>`);
  document.querySelectorAll("[data-newtl]").forEach((b) => (b.onclick = () => { closeModal(); mediaAction("title", b.dataset.newtl); }));
}
function runCommand(id, via = "menu") {
  const c = COMMANDS[id];
  if (!c || !c.run || (c.when && !c.when())) return false;
  closePopups();
  c.run(via);
  return true;
}
window.oncemoreCommand = (id) => runCommand(id, "menu");
function keyParts(spec) { return spec === "+" ? ["+"] : spec.split("+"); }
function keyLabel(spec) {
  const names = IS_MAC ? { mod: "⌘", ctrl: "⌃", shift: "⇧", alt: "⌥", delete: "⌫", space: "Space", pageup: "PgUp", pagedown: "PgDn" } : { mod: "Ctrl", ctrl: "Ctrl", shift: "Shift", alt: "Alt", delete: "Delete", space: "Space", pageup: "PgUp", pagedown: "PgDn" };
  // (as menus write them: ⌃⌥⇧⌘ on a Mac, Ctrl+Alt+Shift elsewhere)
  const order = IS_MAC ? { ctrl: 0, alt: 1, shift: 2, mod: 3 } : { mod: 0, ctrl: 0, alt: 1, shift: 2 };
  const parts = keyParts(spec).sort((a, b) => (order[a] ?? 9) - (order[b] ?? 9)).map((p) => names[p] || p.toUpperCase());
  return IS_MAC ? parts.join("") : parts.join("+");
}
function keyMatches(spec, e) {
  const parts = keyParts(spec), key = parts[parts.length - 1];
  const want = { mod: parts.includes("mod"), shift: parts.includes("shift"), alt: parts.includes("alt") };
  if (["?", "*", "+", "-"].includes(key)) return e.key === key && !(e.metaKey || e.ctrlKey || e.altKey);
  if (want.mod !== (e.metaKey || e.ctrlKey) || want.shift !== e.shiftKey || want.alt !== e.altKey) return false;
  if (key === "delete") return e.key === "Delete" || e.key === "Backspace";
  if (key === "space") return e.code === "Space";
  if (key === "pageup" || key === "pagedown") return e.key === { pageup: "PageUp", pagedown: "PageDown" }[key];
  if (key === "[" || key === "]") return e.code === (key === "[" ? "BracketLeft" : "BracketRight");
  if (key === ",") return e.code === "Comma";
  if (key === ";") return e.code === "Semicolon";
  if (/^[0-9]$/.test(key)) return e.code === "Digit" + key;
  return e.code === "Key" + key.toUpperCase();
}
function commandKeys(e) {
  for (const [id, c] of Object.entries(COMMANDS)) {
    if (!c.key || c.app || !keyMatches(c.key, e)) continue;
    if (c.when && !c.when()) return false;
    e.preventDefault();
    runCommand(id, "key");
    return true;
  }
  return false;
}
// -- the menu bar and right-click menus: one kind of pop-up list
function closePopups() { document.querySelectorAll(".popup").forEach((x) => x.remove()); $("#menubar")?.querySelectorAll(".open").forEach((b) => b.classList.remove("open")); }
function popupLevel(pop) { return Number(pop.dataset.level || 0); }
function closeSubs(pop) {
  document.querySelectorAll(".popup").forEach((x) => { if (popupLevel(x) > popupLevel(pop)) x.remove(); });
  pop.querySelectorAll(".has-sub.open").forEach((b) => b.classList.remove("open"));
}
// items: {label, key, disabled, danger, checked, run} | {label, sub: items} | "-"
function openPopup(x, y, items, parent = null) {
  if (!parent) closePopups();
  const pop = document.createElement("div");
  pop.className = "popup" + (parent ? " sub" : ""); pop.setAttribute("role", "menu");
  pop.dataset.level = parent ? popupLevel(parent) + 1 : 0;
  const checks = items.some((it) => it !== "-" && it.checked !== undefined && it.checkable);
  pop.innerHTML = items.map((it, k) => it === "-" ? `<div class="sep"></div>`
    : `<button role="${it.checkable ? "menuitemcheckbox" : "menuitem"}" data-k="${k}" class="${it.danger ? "danger" : ""} ${it.sub ? "has-sub" : ""}" ${it.disabled ? "disabled" : ""}
        ${it.sub ? 'aria-haspopup="true"' : ""} ${it.checkable ? `aria-checked="${!!it.checked}"` : ""}>${checks ? `<span class="check" aria-hidden="true">${it.checked ? "✓" : ""}</span>` : ""}<span class="lbl">${esc(it.label)}</span><span class="key">${it.sub ? "▸" : esc(it.key || "")}</span></button>`).join("");
  document.body.appendChild(pop);
  const r = pop.getBoundingClientRect();
  if (parent && x + r.width > innerWidth - 4) x = parent.getBoundingClientRect().left - r.width + 2;   // (no room on the right)
  pop.style.left = `${Math.max(4, Math.min(x, innerWidth - r.width - 4))}px`;
  pop.style.top = `${Math.max(4, Math.min(y, innerHeight - r.height - 4))}px`;
  pop.querySelectorAll("[data-k]").forEach((b) => {
    const it = items[Number(b.dataset.k)];
    if (it.sub) {
      const openSub = () => {
        if (b.classList.contains("open")) return;
        closeSubs(pop); b.classList.add("open");
        const br = b.getBoundingClientRect();
        openPopup(br.right - 2, br.top - 4, it.sub, pop);
      };
      b.onmouseenter = openSub;
      b.onclick = (ev) => { ev.stopPropagation(); openSub(); };
    } else {
      b.onmouseenter = () => closeSubs(pop);
      b.onclick = (ev) => { ev.stopPropagation(); closePopups(); it.run(); };
    }
  });
  return pop;
}
const cmdItem = (id) => {
  const c = COMMANDS[id];
  return { id, label: c.label ? c.label() : t("cmd_" + id), key: c.key ? keyLabel(c.key) : "", spec: c.key || "",
    checkable: !!c.on, checked: c.on ? !!c.on() : undefined, disabled: c.app ? false : c.when ? !c.when() : false, run: () => runCommand(id) };
};
function renderMenubar() {
  const bar = $("#menubar");
  bar.hidden = IN_APP;                        // the Mac app has its own menu bar
  bar.innerHTML = MENUBAR.map(([label], k) => `<button data-mb="${k}" aria-haspopup="true">${esc(t(label))}</button>`).join("");
  const open = (b) => {
    const [, ids] = MENUBAR[Number(b.dataset.mb)], r = b.getBoundingClientRect();
    openPopup(r.left, r.bottom + 2, menuItems(ids)).classList.add("from-bar");
    b.classList.add("open");
  };
  bar.querySelectorAll("[data-mb]").forEach((b) => {
    b.onclick = (ev) => { ev.stopPropagation(); if (b.classList.contains("open")) closePopups(); else open(b); };
    b.onmouseenter = () => { if (bar.querySelector(".open") && !b.classList.contains("open")) open(b); };
  });
  postMenuSpec();
}
function itemMenu(kind, id) {
  const list = P()[LISTS[kind]] || [], i = list.findIndex((y) => y.id === id);
  if (i < 0) return null;                     // (generated chapter menus have no menu)
  return [
    { label: t("open"), run: () => select(kind, id) },
    ...(kind !== "playlist" ? [{ label: t("cmd_duplicate"), run: () => duplicateItem(kind, id) }] : []),
    ...(kind === "title" ? [{ label: t("cmd_transcode_title"), disabled: !!S.transcoding, run: () => transcode([id]) }] : []),
    "-",
    { label: t("move_up"), disabled: i === 0, run: () => moveItem(kind, id, -1) },
    { label: t("move_down"), disabled: i === list.length - 1, run: () => moveItem(kind, id, 1) },
    { label: t("set_first_play"), disabled: P().disc.first_play === `${kind}:${id}`, run: () => setFirstPlay(kind, id) },
    "-",
    { label: t("delete"), danger: true, run: () => deleteItem(kind, id) },
  ];
}
function mediaMenu(path) {
  const item = S.media.find((m) => m.path === path);
  if (!item) return null;
  const menu = S.sel.view === "menu" ? curMenu() : null, out = [];
  if (item.kind === "video") { out.push({ label: t("add_as_title"), run: () => mediaAction("title", path) }); if (menu) out.push({ label: t("use_as_video_bg"), run: () => mediaAction("vbg", path) }); }
  if (item.kind === "image") { if (menu) out.push({ label: t("use_as_bg"), run: () => mediaAction("bg", path) }, { label: t("place_on_menu"), run: () => placeMenuPicture(path) }); out.push({ label: t("new_menu_with_bg"), run: () => mediaAction("newmenu", path) }); }
  if (item.kind === "audio") out.push({ label: t("add_as_title"), run: () => mediaAction("title", path) });
  if (item.kind === "audio" && menu) out.push({ label: t("use_as_music"), run: () => mediaAction("music", path) });
  if (item.kind === "design") out.push({ label: t("make_menu_from_psd"), run: () => mediaAction("psd", path) });
  if (out.length) out.push("-");
  out.push({ label: t("cmd_replace_asset"), disabled: !assetRefs().has(path), run: () => replaceAssetBox(path) });
  out.push({ label: t("reveal_file"), run: () => api("/api/reveal", { method: "POST", body: { path } }).catch((e) => alert(e.message)) });
  return out;
}
function stageMenu(el) {
  const k = { kind: el.dataset.kind, i: Number(el.dataset.i) };
  if (!(S.sels || []).some((x) => x.kind === k.kind && x.i === k.i)) { S.element = k; S.sels = [k]; renderMain(); renderInspector(); }
  return [
    { label: t("cmd_duplicate"), key: keyLabel("mod+d"), run: () => duplicateElements(false) },
    { label: t("copy"), key: keyLabel("mod+c"), run: copyElements },
    { label: t("paste"), key: keyLabel("mod+v"), disabled: !S.clip?.length, run: () => duplicateElements(true) },
    "-",
    { label: t("delete"), key: keyLabel("delete"), danger: true, run: deleteElements },
  ];
}
document.addEventListener("contextmenu", (ev) => {
  if (!P() || ev.target.closest("input, textarea, select")) return;
  const nav = ev.target.closest(".nav-item[data-view]"), media = ev.target.closest(".media-item[data-media]"), el = ev.target.closest(".stage .el[data-kind]");
  const items = nav && LISTS[nav.dataset.view] ? itemMenu(nav.dataset.view, nav.dataset.id) : media ? mediaMenu(media.dataset.media) : el ? stageMenu(el) : null;
  if (!items) return;
  ev.preventDefault();
  openPopup(ev.clientX, ev.clientY, items);
});
document.addEventListener("click", (ev) => { if (!ev.target.closest(".popup")) closePopups(); });
// pick whips in Properties (button link, title end action, first play)
document.addEventListener("pointerdown", (ev) => {
  const w = ev.target.closest?.("[data-whip]");
  if (!w || !P()) return;
  const key = w.dataset.whip, view = S.sel.view, id = S.sel.id, el = S.element;
  startWhip(ev, (action) => commit((p) => {
    if (key === "first_play") p.disc.first_play = action;
    else if (key === "end_action" && view === "title") p.titles.find((x) => x.id === id).end_action = action;
    else if (key === "action" && view === "menu" && el?.kind === "button") {
      const mm = p.menus.find((x) => x.id === id);
      if (action === `menu:${mm.id}`) return;                     // not to itself
      mm.buttons[el.i].action = action;
    }
  }), w);
});
window.addEventListener("blur", closePopups);

$("#search").oninput = (ev) => { S.search = ev.target.value; if ((S.leftTab || "project") !== "project") { S.leftTab = "project"; renderLeft(); } else renderSidebar(); };
function toggleTheme() { store.set("theme", store.get("theme", "dark") === "light" ? "dark" : "light"); applyTheme(); }
function toggleLang() { LANG = LANG === "ja" ? "en" : "ja"; try { localStorage.setItem("oncemore.lang", LANG); } catch (e) { /* storage blocked */ } renderAll(); }
applyTheme();
applyBrightness();
initSplitters();
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.classList.contains("modal-close")) closeModal(); });
window.addEventListener("keydown", (e) => {
  const inField = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
  if (e.key === "Escape") { closeModal(); closePopups(); }
  if (inField || !$("#modal").hidden && e.key !== "?") return;
  if (document.activeElement?.closest?.("#sim-screen")) return;     // the simulator's remote keys
  if (P() && commandKeys(e)) return;
  if (!P() && e.key === "?") { shortcutsSheet(); return; }
  stageKeys(e);
});
window.addEventListener("resize", () => { if (S.sel.view === "menu") renderMain(); });
// Re-rendering replaces panels with innerHTML. When that removes a text field
// the person was typing in, the browser fires its change event right then; the
// handler commits and renders the same panel again, inside the first render,
// which then fails ("the node to be removed is no longer a child"). A render
// asked for by such an event is therefore run just after the current one.
let renderDepth = 0, eventInRender = false;
for (const type of ["change", "blur", "focusout"]) {
  document.addEventListener(type, () => {
    if (renderDepth && !eventInRender) { eventInRender = true; queueMicrotask(() => { eventInRender = false; }); }
  }, true);
}
const outsideRender = (fn) => function (...args) {
  if (renderDepth && eventInRender) { queueMicrotask(() => outsideRender(fn)(...args)); return undefined; }
  renderDepth++;
  try { return fn.apply(this, args); } finally { renderDepth--; }
};
renderAll = outsideRender(renderAll);
renderMain = outsideRender(renderMain);
renderInspector = outsideRender(renderInspector);
renderSidebar = outsideRender(renderSidebar);
renderLeft = outsideRender(renderLeft);
renderLayers = outsideRender(renderLayers);
boot();
