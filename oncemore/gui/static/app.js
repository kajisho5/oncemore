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
    title_key: "Title / Top Menu key opens", menu_key: "Menu key opens", first_menu: "First menu",
    playback: "Playback", loop: "Plays", loop_forever: "Repeat forever", loop_n: "{n} time(s), then…",
    loop_point: "Repeat from (s)", menu_end: "After the last time", default_button: "Button highlighted first",
    remember_button: "Come back to the button used last", auto_activate: "Run on selection (no Enter needed)",
    chapter_menu: "Chapter menu", chapter_menu_on: "Generate a chapter menu with thumbnails",
    subtitles: "Subtitles", audio_tracks: "Audio tracks", default_on: "on at start",
    add_chapter: "Add chapter here", chapters: "Chapters", delete: "Delete",
    add_shape: "+ Rectangle", snap: "Snap", align: "Align", n_selected: "{n} selected",
    align_left: "Align left edges", align_hcenter: "Centre horizontally", align_right: "Align right edges",
    align_top: "Align tops", align_vcenter: "Centre vertically", align_bottom: "Align bottoms",
    distribute_h: "Distribute horizontally", distribute_v: "Distribute vertically",
    stage_keys: "Shift-click: select several · arrows: nudge · ⌘D: duplicate · ⌘C/⌘V · Alt: no snapping",
    multi_hint: "Drag to move them together, or use the align buttons above the menu.",
    shape: "Rectangle", height: "Height", fill: "Fill", opacity: "Opacity",
    text_style: "Text style", font: "Font", disc_font: "Disc font", outline: "Outline", shadow: "Shadow",
    font_hint: "Add .ttf / .otf files to Media to use them here.",
    highlight_image: "Highlight picture", highlight_image_hint: "Optional: a picture whose opaque pixels light up when the button is selected.",
    new_menu: "New menu", blank_menu: "Blank", template_hint: "Start from a layout; everything stays editable.",
    motion_bg: "Motion background", animated_thumbs: "Thumbnails play the chapter",
    auto_shared: "Automatic (share the disc)", passthrough: "Copy AC-3 unchanged",
    passthrough_hint: "For AC-3 (48 kHz) sources: no re-encoding. Channels must match the source.",
    rom_files: "DVD-ROM files", rom_hint: "Files or folders (one per line, relative to the project) put next to VIDEO_TS for computers.",
    no_cache: "Encode everything again (ignore the cache)",
    sub_bottom: "Bottom", sub_top: "Top", sub_color: "Own colour",
    image: "Image", width: "Width", highlight_style: "Highlight", hl_frame: "Frame around it", hl_shape: "Its shape",
    image_hint: "An image button shows the picture instead of the text (PNG with transparency works best).",
    chapter_name: "Name on the chapter menu", poster: "Poster", poster_hint: "Use the frame at the playhead as this chapter's thumbnail (click again to reset)",
    playlists: "Playlists", playlist: "Playlist", playlist_item: "Playlist: {p}", items: "Items", add_item: "+ Item",
    from_chapter: "From chapter", to_chapter: "To chapter", to_end: "the end", playlist_end: "After the last item",
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
    font_size: "Text size", text_color: "Text colour", highlight: "Highlight", select_color: "Activated",
    add_button: "+ Button", add_text: "+ Text", exact_preview: "Exact preview", hide_preview: "Hide preview",
    safe_area: "Safe area", button: "Button", text: "Text", action: "Action", size: "Size", color: "Colour",
    nav: "Remote navigation", nav_auto: "auto", none: "None", stop: "Stop",
    playall: "Play all titles", channels: "Channels", stereo: "Stereo", surround: "5.1 surround",
    generated_menu: "This menu is generated from the chapters of “{t}”. Change it in that title's settings.",
    go_to_title: "Open title",
    build_iso: "Disc image (.iso)", build_folder: "VIDEO_TS folder", fast: "Fast (1-pass) encoding",
    start_build: "Start", building: "Building…", build_done: "Done", build_failed: "Build failed",
    reveal: "Show in Finder", reveal_other: "Open folder", output: "Output", warnings: "Warnings",
    step_probe: "Checking sources", step_menu: "Rendering menu “{i}”", step_encode: "Encoding title “{i}”",
    step_subtitles: "Subtitles for “{i}”", step_author: "Authoring VIDEO_TS", step_iso: "Writing the disc image",
    check_ok: "Ready to build", estimated: "Estimated size", of: "of", video_avg: "Average video bitrate",
    menu_item: "Menu: {m}", title_item: "Title: {t}", chapter_item: "{t} › Chapter {n}",
    audio_item: "Audio stream {n}", subtitle_item: "Subtitles {n}", subtitle_off: "Subtitles off",
    nothing_selected: "Select a button or text on the menu, or edit the menu settings below.",
    rename_hint: "Changing an ID also updates everything that points to it.",
    disc_tips: "Coordinates are DVD pixels (720 wide). Text is drawn with the font that oncemore picks to cover all characters.",
    tools: "Tools", ok: "OK", missing: "missing", tracks_hint: "Leave empty to use the video's own sound.",
    stream: "Stream", file: "File", add_track: "+ Track", add_sub: "+ Subtitle file",
    frame_err: "Cannot show this frame", preview_err: "Preview failed",
    confirm_delete: "Delete “{x}”?", chapter_at: "Chapter {n}", playhead: "Playhead",
  },
  ja: {
    check: "チェック", build: "書き出し", drop_here: "ファイルをドロップしてプロジェクトに追加",
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
    title_key: "タイトル／トップメニューキーで開く", menu_key: "メニューキーで開く", first_menu: "最初のメニュー",
    playback: "再生", loop: "再生回数", loop_forever: "ずっと繰り返す", loop_n: "{n} 回再生して…",
    loop_point: "繰り返しの開始位置（秒）", menu_end: "最後の再生のあと", default_button: "最初に選ばれるボタン",
    remember_button: "戻ってきたら前に使ったボタンを選ぶ", auto_activate: "選んだだけで実行（決定キー不要）",
    chapter_menu: "チャプターメニュー", chapter_menu_on: "サムネイル付きチャプターメニューを自動生成",
    subtitles: "字幕", audio_tracks: "音声トラック", default_on: "最初から表示",
    add_chapter: "ここにチャプター", chapters: "チャプター", delete: "削除",
    add_shape: "＋四角形", snap: "スナップ", align: "整列", n_selected: "{n} 個選択中",
    align_left: "左揃え", align_hcenter: "左右中央揃え", align_right: "右揃え",
    align_top: "上揃え", align_vcenter: "上下中央揃え", align_bottom: "下揃え",
    distribute_h: "左右に等間隔", distribute_v: "上下に等間隔",
    stage_keys: "Shift+クリックで複数選択・矢印キーで移動・⌘D 複製・⌘C/⌘V・Alt でスナップなし",
    multi_hint: "ドラッグでまとめて移動、またはメニュー上の整列ボタンを使えます。",
    shape: "四角形", height: "高さ", fill: "塗り", opacity: "不透明度",
    text_style: "文字のスタイル", font: "フォント", disc_font: "ディスクのフォント", outline: "縁取り", shadow: "影",
    font_hint: ".ttf / .otf ファイルを素材に追加するとここで選べます。",
    highlight_image: "ハイライト画像", highlight_image_hint: "任意：不透明な部分が選択時に光る画像。",
    new_menu: "新しいメニュー", blank_menu: "白紙", template_hint: "レイアウトから始められます。あとから全部編集できます。",
    motion_bg: "動く背景", animated_thumbs: "サムネイルでチャプターを再生",
    auto_shared: "自動（ディスク全体で配分）", passthrough: "AC-3 をそのままコピー",
    passthrough_hint: "AC-3（48kHz）素材向け：再エンコードしません。チャンネル数は素材と同じにしてください。",
    rom_files: "DVD-ROM ファイル", rom_hint: "パソコン向けに VIDEO_TS と並べて入れるファイル／フォルダ（1 行に 1 つ、プロジェクトからの相対パス）。",
    no_cache: "すべてエンコードし直す（キャッシュを使わない）",
    sub_bottom: "下", sub_top: "上", sub_color: "色を指定",
    image: "画像", width: "幅", highlight_style: "ハイライト", hl_frame: "周りに枠", hl_shape: "画像の形",
    image_hint: "画像ボタンは文字の代わりに画像を表示します（透過 PNG がおすすめ）。",
    chapter_name: "チャプターメニューに出す名前", poster: "サムネイル", poster_hint: "再生位置のフレームをこのチャプターのサムネイルにする（もう一度押すと解除）",
    playlists: "プレイリスト", playlist: "プレイリスト", playlist_item: "プレイリスト：{p}", items: "再生する内容", add_item: "＋追加",
    from_chapter: "開始チャプター", to_chapter: "終了チャプター", to_end: "最後まで", playlist_end: "最後まで再生したら",
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
    font_size: "文字サイズ", text_color: "文字色", highlight: "選択中の色", select_color: "決定時の色",
    add_button: "＋ボタン", add_text: "＋テキスト", exact_preview: "実レンダリング確認", hide_preview: "確認を閉じる",
    safe_area: "セーフエリア", button: "ボタン", text: "テキスト", action: "リンク先", size: "サイズ", color: "色",
    nav: "リモコンの移動先", nav_auto: "自動", none: "なし", stop: "停止",
    playall: "全タイトルを連続再生", channels: "チャンネル", stereo: "ステレオ", surround: "5.1ch サラウンド",
    generated_menu: "このメニューは「{t}」のチャプターから自動生成されます。変更はそのタイトルの設定で行います。",
    go_to_title: "タイトルを開く",
    build_iso: "ディスクイメージ（.iso）", build_folder: "VIDEO_TS フォルダ", fast: "高速（1パス）エンコード",
    start_build: "開始", building: "書き出し中…", build_done: "完了", build_failed: "書き出しに失敗",
    reveal: "Finder で表示", reveal_other: "フォルダを開く", output: "出力先", warnings: "警告",
    step_probe: "素材をチェック", step_menu: "メニュー「{i}」を作成", step_encode: "タイトル「{i}」をエンコード",
    step_subtitles: "「{i}」の字幕を作成", step_author: "VIDEO_TS を構成", step_iso: "ディスクイメージを書き出し",
    check_ok: "書き出しできます", estimated: "推定サイズ", of: "／", video_avg: "平均映像ビットレート",
    menu_item: "メニュー：{m}", title_item: "タイトル：{t}", chapter_item: "{t} › チャプター {n}",
    audio_item: "音声 {n}", subtitle_item: "字幕 {n}", subtitle_off: "字幕オフ",
    nothing_selected: "メニュー上のボタンやテキストを選択するか、下のメニュー設定を編集してください。",
    rename_hint: "ID を変えると、それを参照している箇所もまとめて更新されます。",
    disc_tips: "座標は DVD のピクセル（幅 720）です。文字は全文字を描けるフォントを oncemore が自動で選んで描きます。",
    tools: "ツール", ok: "OK", missing: "不足", tracks_hint: "空なら動画自体の音声を使います。",
    stream: "ストリーム", file: "ファイル", add_track: "＋トラック", add_sub: "＋字幕ファイル",
    frame_err: "このフレームを表示できません", preview_err: "プレビューに失敗",
    confirm_delete: "「{x}」を削除しますか？", chapter_at: "チャプター {n}", playhead: "再生位置",
  },
};
let LANG = (() => {
  try { const saved = localStorage.getItem("oncemore.lang"); if (saved) return saved; } catch (e) { /* storage blocked */ }
  return (navigator.language || "en").toLowerCase().startsWith("ja") ? "ja" : "en";
})();
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
  if (!res.ok) { const e = new Error((data && data.error) || res.statusText); e.data = data; throw e; }
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
  const e = (title.chapters || []).map((c) => (typeof c === "object" && c !== null
    ? { time: parseTime(c.time), name: c.name || "", poster: c.poster == null ? null : parseTime(c.poster) }
    : { time: parseTime(c), name: "", poster: null })).sort((a, b) => a.time - b.time);
  if (!e.length || e[0].time > 0) e.unshift({ time: 0, name: "", poster: null });
  return e;
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
function actionOptions({ forButton = true, allowStop = true, includeChapters = forButton, allowPlayAll = forButton } = {}) {
  const p = P(), opts = [];
  for (const id of allMenuIds()) opts.push([`menu:${id}`, t("menu_item", { m: id })]);
  if (allowPlayAll && (p.titles || []).length) opts.push(["playall", t("playall")]);
  if (allowPlayAll) for (const pl of p.playlists || []) opts.push([`playlist:${pl.id}`, t("playlist_item", { p: pl.name || pl.id })]);
  for (const ti of p.titles || []) {
    opts.push([`title:${ti.id}`, t("title_item", { t: ti.name || ti.id })]);
    if (includeChapters) chaptersOf(ti).forEach((_, i) =>
      opts.push([`chapter:${ti.id}:${i + 1}`, t("chapter_item", { t: ti.name || ti.id, n: i + 1 })]));
  }
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
    if (kind === "title") {
      if (a === `title:${oldId}`) return `title:${newId}`;
      if (a.startsWith(`chapter:${oldId}:`)) return `chapter:${newId}:` + a.split(":")[2];
    }
    return a;
  };
  p.disc.first_play = fix(p.disc.first_play);
  for (const ti of p.titles || []) {
    ti.end_action = fix(ti.end_action);
    if (ti.auto_chapter_menu && typeof ti.auto_chapter_menu === "object") ti.auto_chapter_menu.back = fix(ti.auto_chapter_menu.back);
  }
  for (const m of p.menus || []) {
    for (const b of m.buttons || []) b.action = fix(b.action);
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
  S.preview = null;
  scheduleSave();
  if (render) renderAll();
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
}

// ---------------------------------------------------------------- rendering
function renderAll() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  renderTopbar(); renderSidebar(); renderMain(); renderInspector(); renderStatus();
}
function renderTopbar() {
  $("#disc-name").textContent = P()?.disc?.label || "";
  const st = $("#save-state");
  st.textContent = P() ? t({ saved: "saved", saving: "saving", unsaved: "unsaved", error: "save_error" }[S.saveState]) : "";
  st.className = "save-state" + (S.saveState === "error" ? " err" : "");
  $("#btn-undo").disabled = !S.undo.length;
  $("#btn-redo").disabled = !S.redo.length;
  $("#btn-check").disabled = !P(); $("#btn-build").disabled = !P();
}
function renderStatus() {
  const bar = $("#statusbar");
  if (!P()) { bar.textContent = S.dir; return; }
  const issues = S.check?.issues || [];
  const tl = S.tools, miss = [];
  if (!tl.ffmpeg) miss.push("ffmpeg"); else if (tl.drawtext === false) miss.push("drawtext");
  if (!tl.dvdauthor) miss.push("dvdauthor"); if (!tl.iso) miss.push("ISO");
  bar.innerHTML = `<span class="${issues.length ? "err" : "ok"}" id="st-issues">${issues.length ? "⚠ " + t("issues", { n: issues.length }) : "✓ " + t("no_issues")}</span>
    ${miss.length ? `<span class="warn">${esc(t("tools_missing", { t: miss.join(", ") }))} — <span class="mono">${esc(tl.install || "")}</span></span>` : ""}
    <span class="spacer"></span><span class="mono">${esc(S.dir)}</span>`;
  $("#st-issues").onclick = () => issues.length && showIssues(issues);
}
function showIssues(issues, title) {
  openModal(`<h2>${esc(title || t("issues", { n: issues.length }))}</h2><ul class="issues">${issues.map((i) =>
    `<li>${i.path ? `<span class="path">${esc(i.path)}</span><br>` : ""}${esc(i.message)}</li>`).join("")}</ul>`);
}
function openModal(html) { $("#modal-body").innerHTML = html; $("#modal").hidden = false; }
function closeModal() { $("#modal").hidden = true; }

function renderSidebar() {
  const sb = $("#sidebar");
  if (!P()) { sb.innerHTML = ""; return; }
  const v = S.sel;
  const item = (view, id, label, tag = "") =>
    `<div class="nav-item ${v.view === view && v.id === id ? "active" : ""}" data-view="${view}" data-id="${esc(id || "")}">${esc(label)}${tag ? `<span class="tag">${esc(tag)}</span>` : ""}</div>`;
  const titles = (P().titles || []).map((ti) => item("title", ti.id, ti.name || ti.id, ti.aspect || "")).join("");
  const menus = (P().menus || []).map((m) => item("menu", m.id, m.id)).join("");
  const gen = generatedMenus().map((g) => item("menu", g.id, g.id, t("generated"))).join("");
  const media = S.media.map((m) => `<div class="media-item ${S.selectedMedia === m.path ? "selected" : ""}" data-media="${esc(m.path)}" draggable="false">
      <span class="kind">${esc(m.kind)}</span><span class="name" title="${esc(m.path)}">${esc(m.path.replace(/^media\//, ""))}</span></div>`).join("");
  const ups = Object.entries(S.uploads).map(([n, pct]) => `<div class="media-item"><span class="name">${esc(n)}</span><span class="muted">${pct}%</span></div>`).join("");
  sb.innerHTML = `
    <div class="nav-group">${item("disc", "", t("disc"))}</div>
    <div class="nav-group"><div class="nav-head">${t("titles")}</div>${titles || `<div class="hint" style="padding:4px 18px">${esc(t("no_titles"))}</div>`}</div>
    <div class="nav-group"><div class="nav-head">${t("menus")}<button class="small" id="add-menu">${t("add")}</button></div>${menus}${gen}</div>
    <div class="nav-group"><div class="nav-head">${t("playlists")}<button class="small" id="add-playlist">${t("add")}</button></div>${(P().playlists || []).map((pl) => item("playlist", pl.id, pl.name || pl.id)).join("")}</div>
    <div class="nav-group"><div class="nav-head">${t("media")}</div>${media}${ups}
      <div class="dropzone" id="dropzone">${esc(t("add_files"))}</div></div>
    <div class="nav-group">${item("build", "", "▸ " + t("build"))}</div>`;
  sb.querySelectorAll(".nav-item").forEach((el) => (el.onclick = () => select(el.dataset.view, el.dataset.id)));
  sb.querySelectorAll(".media-item[data-media]").forEach((el) => (el.onclick = () => { S.selectedMedia = el.dataset.media; S.element = null; renderSidebar(); renderInspector(); }));
  $("#add-menu").onclick = addMenu;
  $("#add-playlist").onclick = addPlaylist;
  $("#dropzone").onclick = pickFiles;
}
function select(view, id) {
  S.sel = { view, id }; S.element = null; S.selectedMedia = null; S.preview = null;
  renderAll();
}

function renderMain() {
  const m = $("#main");
  if (!P()) return renderWelcome(m);
  const v = S.sel.view;
  if (v === "title") return renderTitle(m);
  if (v === "menu") return renderMenu(m);
  if (v === "playlist") return renderPlaylist(m);
  if (v === "build") return renderBuild(m);
  return renderDisc(m);
}
function renderInspector() {
  const el = $("#inspector");
  if (!P()) { el.innerHTML = ""; return; }
  if (S.selectedMedia) return renderMediaInspector(el);
  const v = S.sel.view;
  if (v === "title") return renderTitleInspector(el);
  if (v === "menu") return renderMenuInspector(el);
  if (v === "playlist") { el.innerHTML = `<h2>${t("playlist")}</h2><div class="hint">${esc(t("playlist_hint"))}</div>`; return; }
  el.innerHTML = `<h3>${t("tools")}</h3>
    <div class="hint">ffmpeg: ${S.tools.ffmpeg ? t("ok") : t("missing")}<br>drawtext: ${S.tools.drawtext ? t("ok") : t("missing")}<br>
    dvdauthor: ${S.tools.dvdauthor ? t("ok") : t("missing")}<br>ISO: ${esc(S.tools.iso || t("missing"))}</div>
    <h3>oncemore</h3><div class="hint">${esc(t("disc_tips"))}</div>`;
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
  m.innerHTML = `<div class="empty"><h2>${t("new_project")}</h2><p>${esc(t("new_hint", { dir: S.dir }))}</p>
    <div class="card" style="max-width:420px;margin:20px auto;text-align:left">
      <label class="field"><span>${t("label")}</span><input id="np-label" value="MY_DISC"></label>
      <div class="grid2">
        <label class="field"><span>${t("standard")}</span><select id="np-std"><option>NTSC</option><option>PAL</option></select></label>
        <label class="field"><span>${t("aspect")}</span><select id="np-aspect"><option>16:9</option><option>4:3</option></select></label>
      </div>
      <div class="row"><button id="np-empty">${t("empty_project")}</button><button id="np-sample" class="primary">${t("sample_project")}</button></div>
    </div></div>`;
  const go = async (sample) => {
    const r = await api("/api/new", { method: "POST", body: { sample, label: $("#np-label").value, standard: $("#np-std").value, aspect: $("#np-aspect").value } });
    applyState(r); S.sel = { view: "disc" }; renderAll();
  };
  $("#np-empty").onclick = () => go(false);
  $("#np-sample").onclick = () => go(true);
}

// ---------------------------------------------------------------- disc
function renderDisc(m) {
  const d = P().disc;
  const fp = actionOptions({ forButton: false, allowStop: false, includeChapters: false, allowPlayAll: true });
  m.innerHTML = `<div class="card" style="max-width:640px"><h2>${t("disc")}</h2>
    <label class="field"><span>${t("label")}</span><input data-k="label" value="${esc(d.label)}"></label>
    <div class="grid2">
      <label class="field"><span>${t("standard")}</span>${selectHtml("standard", [["NTSC", "NTSC (720×480, 29.97)"], ["PAL", "PAL (720×576, 25)"]], d.standard)}</label>
      <label class="field"><span>${t("aspect")}</span>${selectHtml("aspect", [["16:9", "16:9"], ["4:3", "4:3"]], d.aspect)}</label>
      <label class="field"><span>${t("target")}</span>${selectHtml("target", [["DVD5", "DVD-5 (4.7 GB)"], ["DVD9", "DVD-9 (8.5 GB)"]], d.target || "DVD5")}</label>
      <label class="field"><span>${t("video_bitrate")}</span>${selectHtml("video_bitrate", [["auto", t("auto")], ["4M", "4 Mbit/s"], ["5M", "5 Mbit/s"], ["6M", "6 Mbit/s"], ["7M", "7 Mbit/s"], ["8M", "8 Mbit/s"]], d.video_bitrate || "auto")}</label>
    </div>
    <label class="field"><span>${t("first_play")}</span>${selectHtml("first_play", [["__none__", t("auto")], ...fp], d.first_play || "__none__")}</label>
    <label class="field"><span>${t("title_key")}</span>${selectHtml("title_key", [["__none__", t("first_menu")], ...fp], d.title_key || "__none__")}</label>
    <label class="field" data-nobind><span>${t("rom_files")}</span><textarea id="rom-files" rows="3" placeholder="extras/">${esc((d.rom_files || []).join("\n"))}</textarea><div class="hint">${esc(t("rom_hint"))}</div></label>
  </div>`;
  bindFields(m, (p) => p.disc);
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
  const info = S.probes[ti.source];
  if (!info) { m.innerHTML = `<div class="muted">…</div>`; probe(ti.source).then(() => S.sel.view === "title" && renderMain()); return; }
  const fps = (() => { const [a, b] = String(info.fps || "30").split(/[/:]/).map(Number); return b ? a / b : a || 30; })();
  const dur = info.duration || 0;
  const ph = Math.min(S.playhead[ti.id] || 0, dur);
  const chapters = chaptersOf(ti);
  const ar = ti.aspect || P().disc.aspect;
  m.innerHTML = `<div class="card">
    <div class="row"><h2 class="shrink">${esc(ti.name || ti.id)}</h2><span class="muted">${esc(ti.source)} · ${info.width || "?"}×${info.height || "?"} · ${dur.toFixed(2)}s</span></div>
    <div class="viewer" style="aspect-ratio:${ar.replace(":", " / ")}"><img id="frame" alt=""><video id="player" playsinline preload="none" hidden></video>
      <span class="tc" id="tc">${fmtTime(ph)}</span><span class="proxy-msg" id="proxy-msg" hidden></span></div>
    <div class="timeline" id="timeline">
      ${chapters.map((c, i) => `<div class="marker" data-ch="${i}" title="${esc(t("chapter_at", { n: i + 1 }))} ${fmtTime(c)}" style="left:${dur ? (c / dur) * 100 : 0}%"></div>`).join("")}
      <input type="range" id="scrub" min="0" max="${dur}" step="${(1 / fps).toFixed(5)}" value="${ph}">
    </div>
    <div class="transport">
      <button id="play" class="shrink">▶ ${t("play")}</button>
      <button data-step="-1">−1s</button><button data-step="${-1 / fps}">−1f</button>
      <button data-step="${1 / fps}">+1f</button><button data-step="1">+1s</button>
      <input id="tc-input" class="mono" style="width:130px" value="${fmtTime(ph)}" title="${t("playhead")}">
      <span class="spacer"></span>
      <button id="add-ch" class="primary">◆ ${t("add_chapter")}</button>
    </div>
    <h3>${t("chapters")} (${chapters.length})</h3>
    <ul class="chapter-list">${chapterEntries(ti).map((c, i) => `<li><span class="n">${i + 1}</span><span class="t" data-seek="${c.time}">${fmtTime(c.time)}</span>
      <input class="ch-name" data-ch-name="${i}" value="${esc(c.name)}" placeholder="${esc(t("chapter_at", { n: i + 1 }))}" title="${esc(t("chapter_name"))}">
      <button class="small ${c.poster != null ? "on" : ""}" data-poster="${i}" title="${esc(t("poster_hint"))}">🖼 ${c.poster != null ? fmtTime(c.poster) : t("poster")}</button>
      ${i ? `<button class="small danger" data-del="${i}">✕</button>` : ""}</li>`).join("")}</ul>
  </div>`;
  const img = $("#frame");
  let pending = null, last = -1;
  const show = (time) => {
    S.playhead[ti.id] = time;
    $("#tc").textContent = fmtTime(time); $("#tc-input").value = fmtTime(time);
    clearTimeout(pending);
    pending = setTimeout(() => {
      if (Math.abs(time - last) < 1e-4) return;
      last = time;
      img.src = imgUrl("frame", { path: ti.source, t: time.toFixed(3), w: 960 });
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
    playBtn.textContent = "▶ " + t("play");
    if (time != null) seek(time);
  };
  const seek = (time) => {
    if (playing) toFrames(null);
    time = Math.max(0, Math.min(dur, time)); scrub.value = time; show(time);
  };
  scrub.oninput = () => { if (playing) toFrames(null); show(Number(scrub.value)); };
  video.onpause = () => { if (playing) toFrames(snap(video.currentTime)); };
  video.ontimeupdate = () => {
    if (!playing) return;
    scrub.value = video.currentTime; S.playhead[ti.id] = video.currentTime;
    $("#tc").textContent = fmtTime(video.currentTime); $("#tc-input").value = fmtTime(video.currentTime);
  };
  video.onerror = () => { if (video.getAttribute("src")) { msg.hidden = false; msg.textContent = t("play_err"); toFrames(null); } };
  playBtn.onclick = async () => {
    if (playing) { video.pause(); return; }
    playBtn.disabled = true;
    try {
      for (;;) {
        const st = await api("/api/proxy?" + new URLSearchParams({ path: ti.source, format }), { method: "POST" });
        if (st.state === "ready") break;
        if (st.state === "error") throw new Error(st.error || t("play_err"));
        msg.hidden = false; msg.textContent = t("preparing", { p: Math.round(st.fraction * 100) });
        await new Promise((r) => setTimeout(r, 500));
        if (S.sel.view !== "title" || S.sel.id !== ti.id || !document.body.contains(video)) return;
      }
    } catch (e) { msg.hidden = false; msg.textContent = e.message; return; }
    finally { playBtn.disabled = false; }
    msg.hidden = true;
    const src = imgUrl("proxy", { path: ti.source, format });
    if (video.getAttribute("src") !== src) video.src = src;
    video.currentTime = Number(scrub.value) >= dur - 0.05 ? 0 : Number(scrub.value);
    playing = true; video.hidden = false; img.hidden = true;
    playBtn.textContent = "❚❚ " + t("pause");
    video.play().catch((e) => { if (playing) { msg.hidden = false; msg.textContent = e.message; toFrames(null); } });
  };
  m.querySelectorAll("[data-step]").forEach((b) => (b.onclick = () => seek(Number(scrub.value) + Number(b.dataset.step))));
  m.querySelectorAll("[data-seek]").forEach((el) => (el.onclick = () => seek(Number(el.dataset.seek))));
  m.querySelectorAll(".marker").forEach((el) => (el.onclick = () => seek(chapters[Number(el.dataset.ch)])));
  $("#tc-input").onchange = (e) => seek(parseTime(e.target.value));
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
}

function renderTitleInspector(el) {
  const ti = curTitle();
  if (!ti) { el.innerHTML = ""; return; }
  const audio = ti.audio || {};
  const cm = ti.auto_chapter_menu;
  const ends = actionOptions({ forButton: false, includeChapters: false });
  const langs = [["", "—"], ["ja", "日本語 (ja)"], ["en", "English (en)"], ["fr", "Français (fr)"], ["de", "Deutsch (de)"], ["es", "Español (es)"], ["zh", "中文 (zh)"], ["ko", "한국어 (ko)"]];
  const subs = ti.subtitles || [], tracks = ti.audio_tracks || [];
  el.innerHTML = `<h2>${t("title_props")}</h2>
    <label class="field"><span>${t("name")}</span><input data-k="name" value="${esc(ti.name || "")}"></label>
    <label class="field"><span>${t("id")}</span><input id="ti-id" value="${esc(ti.id)}"><div class="hint">${esc(t("rename_hint"))}</div></label>
    <label class="field"><span>${t("source")}</span>${selectHtml("source", mediaOf("video").map((v) => [v, v]), ti.source)}</label>
    <label class="field"><span>${t("aspect")}</span>${selectHtml("aspect", [["__none__", `${t("auto")} (${P().disc.aspect})`], ["16:9", "16:9"], ["4:3", "4:3"]], ti.aspect || "__none__")}</label>
    <label class="field"><span>${t("end_action")}</span>${selectHtml("end_action", [["__none__", t("auto")], ...ends], ti.end_action || "__none__")}</label>
    <label class="field"><span>${t("menu_key")}</span>${selectHtml("remote_menu", [["__none__", t("first_menu")], ...allMenuIds().map((id) => [id, t("menu_item", { m: id })])], ti.remote_menu || "__none__")}</label>
    <h3>${t("audio")}</h3>
    <div class="grid2">
      <label class="field"><span>${t("codec")}</span>${selectHtml("audio.codec", [["ac3", "AC-3"], ["lpcm", "LPCM"]], audio.codec || "ac3")}</label>
      <label class="field"><span>${t("bitrate")}</span>${selectHtml("audio.bitrate", [["128k", "128k"], ["192k", "192k"], ["224k", "224k"], ["256k", "256k"], ["384k", "384k"], ["448k", "448k"]], audio.bitrate || (audio.channels === 6 ? "448k" : "192k"), audio.codec === "lpcm" ? "disabled" : "")}</label>
      <label class="field"><span>${t("channels")}</span>${selectHtml("audio.channels", [["2", t("stereo")], ["6", t("surround")]], String(audio.channels || 2), audio.codec === "lpcm" ? "disabled" : "")}</label>
      <label class="field"><span>${t("video_bitrate")}</span>${selectHtml("video_bitrate", [["__none__", t("auto_shared")], ...["3M", "4M", "5M", "6M", "7M", "8M"].map((b) => [b, b.replace("M", " Mbit/s")])], ti.video_bitrate || "__none__")}</label>
      <label class="field"><span></span><label title="${esc(t("passthrough_hint"))}"><input type="checkbox" data-k="audio.passthrough" ${audio.passthrough ? "checked" : ""} ${audio.codec === "lpcm" ? "disabled" : ""}> ${t("passthrough")}</label></label>
    </div>
    ${tracks.length ? "" : `<label class="field"><span>${t("language")}</span>${selectHtml("audio.lang", langs, audio.lang || "")}</label>`}
    <h3>${t("audio_tracks")}</h3>
    <div class="hint">${esc(t("tracks_hint"))}</div>
    ${tracks.map((tr, i) => `<div class="row" style="margin:6px 0" data-track="${i}" data-nobind>
        ${selectHtml("source", [["", ti.source], ...mediaOf("audio").map((a) => [a, a]), ...mediaOf("video").filter((v) => v !== ti.source).map((v) => [v, v])], tr.source || "")}
        <input type="number" min="0" class="shrink" style="width:52px" data-k="stream" value="${tr.stream || 0}" title="${t("stream")}">
        ${selectHtml("lang", langs, tr.lang || "", 'class="shrink" style="width:90px"')}
        <button class="small danger shrink" data-del-track="${i}">✕</button></div>`).join("")}
    <button class="small" id="add-track">${t("add_track")}</button>
    <h3>${t("subtitles")}</h3>
    ${subs.map((s, i) => `<div class="row" style="margin:6px 0" data-sub="${i}" data-nobind>
        ${selectHtml("file", mediaOf("subtitle").map((f) => [f, f.replace(/^media\//, "")]), s.file)}
        ${selectHtml("lang", langs, s.lang || "", 'class="shrink" style="width:90px"')}
        <label class="shrink" title="${t("default_on")}"><input type="checkbox" data-k="default" ${s.default ? "checked" : ""}> ${t("default_on")}</label>
        <button class="small danger shrink" data-del-sub="${i}">✕</button></div>
        <div class="row" style="margin:0 0 8px 0" data-sub="${i}" data-nobind>
        ${selectHtml("position", [["bottom", t("sub_bottom")], ["top", t("sub_top")]], s.position || "bottom", 'class="shrink"')}
        <label class="shrink"><input type="checkbox" data-k="has_color" ${s.color ? "checked" : ""}> ${t("sub_color")}</label>
        <input type="color" class="shrink" data-k="color" value="${esc(s.color || "#ffffff")}" ${s.color ? "" : "disabled"}></div>`).join("")}
    <button class="small" id="add-sub" ${mediaOf("subtitle").length ? "" : "disabled"}>${t("add_sub")}</button>
    <h3>${t("chapter_menu")}</h3>
    <label><input type="checkbox" id="cm-on" ${cm ? "checked" : ""}> ${t("chapter_menu_on")}</label>
    ${cm ? `<div style="margin-top:8px" data-nobind><label class="field"><span>BACK → </span>${selectHtml("back", [["__none__", t("auto")], ...actionOptions({ forButton: false, includeChapters: false })], (cm === true ? null : cm.back) || "__none__", 'id="cm-back"')}</label>
      <label class="field"><span>${t("motion_bg")}</span>${selectHtml("cmbg", [["__none__", t("none")], ...mediaOf("video").map((v) => [v, v])], (cm === true ? null : cm.background_video) || "__none__", 'id="cm-bgv"')}</label>
      <label><input type="checkbox" id="cm-anim" ${cm !== true && cm.animated_thumbnails ? "checked" : ""} ${cm !== true && cm.background_video ? "" : "disabled"}> ${t("animated_thumbs")}</label></div>` : ""}
    <h3></h3>${orderHtml(t("order_title"))}
    <h3></h3><button class="danger" id="del-title">${t("delete")}</button>`;
  const find = (p) => p.titles.find((x) => x.id === ti.id);
  bindFields(el, find, {
    numeric: ["audio.channels"],
    onAfter: (p, key, val) => {   // LPCM is stereo only; 2 is the default anyway
      const a = find(p).audio;
      if (a && (key === "audio.codec" && val === "lpcm" || key === "audio.channels" && val === 2)) delete a.channels;
      if (a && (key === "audio.codec" && val === "lpcm" || key === "audio.passthrough" && !val)) delete a.passthrough;
    },
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
  $("#add-sub").onclick = () => commit((p) => { const x = find(p); (x.subtitles = x.subtitles || []).push({ file: mediaOf("subtitle")[0] }); });
  $("#cm-on").onchange = (e) => commit((p) => { const x = find(p); if (e.target.checked) x.auto_chapter_menu = true; else delete x.auto_chapter_menu; });
  const cmSet = (key, val) => commit((p) => {
    const x = find(p), spec = x.auto_chapter_menu === true ? {} : x.auto_chapter_menu;
    if (val === undefined || val === false) delete spec[key]; else spec[key] = val;
    if (key === "background_video" && val === undefined) delete spec.animated_thumbnails;
    x.auto_chapter_menu = Object.keys(spec).length ? spec : true;
  });
  if ($("#cm-bgv")) $("#cm-bgv").onchange = (e) => cmSet("background_video", e.target.value === "__none__" ? undefined : e.target.value);
  if ($("#cm-anim")) $("#cm-anim").onchange = (e) => cmSet("animated_thumbnails", e.target.checked || undefined);
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
  bindOrder(el, "titles", ti.id);
  $("#del-title").onclick = () => {
    if (!confirm(t("confirm_delete", { x: ti.name || ti.id }))) return;
    commit((p) => { p.titles = p.titles.filter((x) => x.id !== ti.id); });
    select("disc");
  };
}

// ---------------------------------------------------------------- menus
const curMenu = () => (P().menus || []).find((x) => x.id === S.sel.id);
async function addMenu() {
  let list = [];
  try { list = (await api("/api/templates")).templates; } catch (e) { list = []; }
  openModal(`<h2>${t("new_menu")}</h2><div class="hint">${esc(t("template_hint"))}</div>
    <div class="template-list"><button class="template" data-template="">${esc(t("blank_menu"))}</button>
    ${list.map((x) => `<button class="template" data-template="${esc(x.id)}">${esc(x[LANG] || x.en)}</button>`).join("")}</div>`);
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
  const ends = actionOptions({ forButton: false, includeChapters: false, allowPlayAll: false });
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
    <label class="field" style="margin-top:12px"><span>${t("playlist_end")}</span>${selectHtml("end_action", ends, pl.end_action || "stop")}</label>
    <h3></h3><button class="danger" id="del-playlist">${t("delete")}</button></div>`;
  const find = (p) => p.playlists.find((x) => x.id === pl.id);
  bindFields(m, find, { onAfter: (p, key, val) => { if (key === "end_action" && val === "stop") delete find(p).end_action; } });
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
  $("#del-playlist").onclick = () => {
    if (!confirm(t("confirm_delete", { x: pl.name || pl.id }))) return;
    commit((p) => {
      p.playlists = p.playlists.filter((x) => x.id !== pl.id);
      if (!p.playlists.length) delete p.playlists;
      for (const mm of p.menus || []) for (const b of mm.buttons || []) if (b.action === `playlist:${pl.id}`) b.action = "stop";
    });
    select("disc");
  };
}

function renderMenu(m) {
  const menu = curMenu();
  const gen = generatedMenus().find((g) => g.id === S.sel.id);
  if (!menu && !gen) return select("disc");
  const H = discH(), DW = displayW();
  const avail = Math.max(320, Math.min(m.clientWidth - 40, 1000));
  const scale = avail / DW, sx = DW / 720;
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
    ...(menu.shapes || []).map((x, i) => ({ kind: "shape", i, x: x.x, y: x.y, w: x.w, h: x.h, color: x.color || "#00000080" })),
    ...(menu.texts || []).map((x, i) => ({ kind: "text", i, x: x.x, y: x.y, size: x.size || defSize, color: x.color || defColor, label: x.text, ...styleOf(x) })),
    ...(menu.buttons || []).map((b, i) => ({ kind: "button", i, x: b.x, y: b.y, size: b.size || defSize, color: b.color || defColor, label: b.label || "", image: b.image, width: b.width, ...styleOf(b) })),
  ];
  // selection: S.sels (all selected), S.element (the one the inspector shows)
  if (!S.element) S.sels = [];
  else if (!(S.sels || []).some((x) => x.kind === S.element.kind && x.i === S.element.i)) S.sels = [S.element];
  const isSel = (e) => S.sels.some((x) => x.kind === e.kind && x.i === e.i);
  const firstBtn = Math.max(0, (menu.buttons || []).findIndex((b) => b.id === menu.default_button));
  for (const e of els) if (e.font) loadFont(e.font);
  const css = (e) => {
    let st = `left:${e.x * sx * scale}px;top:${e.y * scale}px;`;
    if (e.kind === "shape") return st + `width:${e.w * sx * scale}px;height:${e.h * scale}px;background:${cssColor(e.color)}`;
    st += `font-size:${e.size * scale}px;color:${esc(e.kind === "button" && e.i === firstBtn ? (menu.highlight_color || "#FFD400") : e.color)};`;
    if (e.font) st += `font-family:${fontFamily(e.font)},sans-serif;`;
    const sh = [];
    if (e.outline) { const o = Math.max(1, e.outline_width * scale); for (const [dx, dy] of [[o, 0], [-o, 0], [0, o], [0, -o], [o, o], [-o, -o], [o, -o], [-o, o]]) sh.push(`${dx}px ${dy}px 0 ${cssColor(e.outline)}`); }
    if (e.shadow) sh.push(`${e.shadow_offset * scale}px ${e.shadow_offset * scale}px 0 ${cssColor(e.shadow)}`);
    if (sh.length) st += `text-shadow:${sh.join(",")};`;
    return st;
  };
  m.innerHTML = `<div class="stage-tools">
      <button id="add-btn">${t("add_button")}</button><button id="add-text">${t("add_text")}</button><button id="add-shape">${t("add_shape")}</button>
      <label class="shrink" style="display:flex;gap:4px;align-items:center"><input type="checkbox" id="safe" ${S.showSafe ? "checked" : ""}> ${t("safe_area")}</label>
      <label class="shrink" style="display:flex;gap:4px;align-items:center"><input type="checkbox" id="snap" ${S.snap === false ? "" : "checked"}> ${t("snap")}</label>
      <button id="exact" class="${S.preview ? "" : "primary"}">${S.preview ? t("hide_preview") : t("exact_preview")}</button>
    </div>
    ${S.sels.length > 1 ? `<div class="stage-tools align-tools">${t("align")}:
      ${[["left", "⇤"], ["hcenter", "↔"], ["right", "⇥"], ["top", "⤒"], ["vcenter", "↕"], ["bottom", "⤓"]].map(([k, i]) => `<button class="small" data-align="${k}" title="${esc(t("align_" + k))}">${i}</button>`).join("")}
      ${S.sels.length > 2 ? `<button class="small" data-distribute="h" title="${esc(t("distribute_h"))}">⇹</button><button class="small" data-distribute="v" title="${esc(t("distribute_v"))}">⇳</button>` : ""}
      <span class="hint">${esc(t("n_selected", { n: S.sels.length }))}</span></div>` : ""}
    <div class="stage-wrap"><div class="stage" id="stage" tabindex="0" style="width:${w}px;height:${h}px;background:${esc(menu.background_color || "#000")}">
      ${bg}
      ${S.showSafe ? `<div class="safe" style="left:${w * 0.05}px;top:${h * 0.05}px;width:${w * 0.9}px;height:${h * 0.9}px"></div>` : ""}
      ${els.map((e) => `<div class="el ${e.kind} ${isSel(e) ? "selected" : ""} ${e.kind === "button" && e.i === firstBtn ? "highlight" : ""}"
          data-kind="${e.kind}" data-i="${e.i}" style="${css(e)}">${e.kind === "shape" ? "" : e.image
            ? `<img src="${imgUrl("file", { path: e.image })}" alt="${esc(e.label)}" draggable="false" style="display:block;width:${(e.width || 160) * sx * scale}px${e.i === firstBtn ? `;outline:2px solid ${esc(menu.highlight_color || "#FFD400")}` : ""}">`
            : esc(e.label)}</div>`).join("")}
      <div class="guide gx" hidden></div><div class="guide gy" hidden></div>
    </div></div>
    <div class="hint" style="text-align:center;margin-top:8px">${w}×${h} · 720×${H} DVD px · ${esc(P().disc.aspect)} · ${esc(t("stage_keys"))}</div>`;
  const stage = $("#stage");
  const nodeOf = (k) => stage.querySelector(`.el[data-kind="${k.kind}"][data-i="${k.i}"]`);
  // element boxes on the 720-wide grid (texts measured from the page)
  const box = (k) => {
    const n = nodeOf(k), e = els.find((x) => x.kind === k.kind && x.i === k.i);
    const bw = e.kind === "shape" ? e.w : n.offsetWidth / scale / sx, bh = e.kind === "shape" ? e.h : n.offsetHeight / scale;
    return { x: e.x, y: e.y, w: bw, h: bh };
  };
  const listOf = (mm, kind) => (kind === "button" ? mm.buttons : kind === "text" ? (mm.texts = mm.texts || []) : (mm.shapes = mm.shapes || []));
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
      // drag every selected element; snap the grabbed one to the others' edges / centres
      const group = S.sels.map((x) => ({ k: x, b: box(x), node: nodeOf(x) }));
      const me = group.find((g) => g.k.kind === k.kind && g.k.i === k.i).b;
      const others = els.filter((e) => !isSel(e)).map((e) => box(e));
      const vx = [0, 360, 720, 36, 684, ...others.flatMap((o) => [o.x, o.x + o.w / 2, o.x + o.w])];
      const vy = [0, H / 2, H, H * 0.05, H * 0.95, ...others.flatMap((o) => [o.y, o.y + o.h / 2, o.y + o.h])];
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
        if (S.snap !== false && !e2.altKey) {
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
  stage.addEventListener("pointerdown", (ev) => { if (ev.target === stage || ev.target.classList.contains("bg")) { S.element = null; S.sels = []; renderMain(); renderInspector(); } });
  // align / distribute the selection
  const arrange = (fn) => commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    const items = S.sels.map((k) => ({ k, b: box(k), it: listOf(mm, k.kind)[k.i] }));
    fn(items);
    for (const x of items) { x.it.x = Math.max(0, Math.min(719, Math.round(x.it.x))); x.it.y = Math.max(0, Math.min(H - 1, Math.round(x.it.y))); }
  });
  m.querySelectorAll("[data-align]").forEach((b) => (b.onclick = () => arrange((items) => {
    const a = b.dataset.align, L = Math.min(...items.map((x) => x.b.x)), R = Math.max(...items.map((x) => x.b.x + x.b.w));
    const T = Math.min(...items.map((x) => x.b.y)), B = Math.max(...items.map((x) => x.b.y + x.b.h));
    for (const x of items) {
      if (a === "left") x.it.x = L;
      if (a === "right") x.it.x = R - x.b.w;
      if (a === "hcenter") x.it.x = (L + R) / 2 - x.b.w / 2;
      if (a === "top") x.it.y = T;
      if (a === "bottom") x.it.y = B - x.b.h;
      if (a === "vcenter") x.it.y = (T + B) / 2 - x.b.h / 2;
    }
  })));
  m.querySelectorAll("[data-distribute]").forEach((b) => (b.onclick = () => arrange((items) => {
    const hz = b.dataset.distribute === "h", pos = (x) => (hz ? x.b.x : x.b.y), size = (x) => (hz ? x.b.w : x.b.h);
    items.sort((p, q) => pos(p) - pos(q));
    const first = items[0], last = items[items.length - 1];
    const gap = (pos(last) + size(last) - pos(first) - items.reduce((s, x) => s + size(x), 0)) / (items.length - 1);
    let at = pos(first);
    for (const x of items) { if (hz) x.it.x = at; else x.it.y = at; at += size(x) + gap; }
  })));
  $("#safe").onchange = (e) => { S.showSafe = e.target.checked; renderMain(); };
  $("#snap").onchange = (e) => { S.snap = e.target.checked; };
  $("#add-btn").onclick = () => commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    const id = uniqueId("button", mm.buttons.map((b) => b.id));
    const last = mm.buttons[mm.buttons.length - 1];
    mm.buttons.push({ id, label: "BUTTON", x: last ? last.x : 80, y: last ? Math.min(H - 40, last.y + 60) : 200, action: "stop" });
    S.element = { kind: "button", i: mm.buttons.length - 1 }; S.sels = [S.element];
  });
  $("#add-text").onclick = () => commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    (mm.texts = mm.texts || []).push({ text: "TEXT", x: 80, y: 40 });
    S.element = { kind: "text", i: mm.texts.length - 1 }; S.sels = [S.element];
  });
  $("#add-shape").onclick = () => commit((p) => {
    const mm = p.menus.find((x) => x.id === menu.id);
    (mm.shapes = mm.shapes || []).push({ x: 60, y: Math.round(H * 0.7), w: 600, h: 60, color: "#00000080" });
    S.element = { kind: "shape", i: mm.shapes.length - 1 }; S.sels = [S.element];
  });
  $("#exact").onclick = () => { if (S.preview) { S.preview = null; renderMain(); } else requestPreview(menu.id, S.element && S.element.kind === "button" ? menu.buttons[S.element.i].id : null); };
  if (S.preview && S.previewFor === menu.id) drawPreview();
}
// keyboard editing on the menu stage: arrows nudge (Shift: 10 px), Delete,
// Cmd/Ctrl+D duplicate, Cmd/Ctrl+C / V copy and paste
function stageKeys(ev) {
  if (S.element && !S.sels?.length) S.sels = [S.element];
  if (S.sel.view !== "menu" || !S.sels?.length || ev.target.closest?.("input, textarea, select")) return;
  const menu = curMenu();
  if (!menu) return;
  const mod = ev.metaKey || ev.ctrlKey, H = discH();
  const listOf = (mm, kind) => (kind === "button" ? mm.buttons : kind === "text" ? (mm.texts = mm.texts || []) : (mm.shapes = mm.shapes || []));
  const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  if (arrows[ev.key] && !mod) {
    ev.preventDefault();
    const [ax, ay] = arrows[ev.key], n = ev.shiftKey ? 10 : 1;
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const k of S.sels) { const it = listOf(mm, k.kind)[k.i]; it.x = Math.max(0, Math.min(719, it.x + ax * n)); it.y = Math.max(0, Math.min(H - 1, it.y + ay * n)); }
    });
  } else if ((ev.key === "Delete" || ev.key === "Backspace") && !mod) {
    ev.preventDefault();
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id);
      for (const k of [...S.sels].sort((a, b) => b.i - a.i)) {
        const l = listOf(mm, k.kind);
        if (k.kind === "button" && l.length <= 1) continue;
        l.splice(k.i, 1);
      }
      S.element = null; S.sels = [];
    });
  } else if (mod && (ev.key === "c" || ev.key === "C")) {
    S.clip = S.sels.map((k) => ({ kind: k.kind, it: JSON.parse(JSON.stringify(listOf(menu, k.kind)[k.i])) }));
  } else if (mod && (ev.key === "d" || ev.key === "D" || ev.key === "v" || ev.key === "V")) {
    const src = ev.key.toLowerCase() === "d" ? S.sels.map((k) => ({ kind: k.kind, it: listOf(menu, k.kind)[k.i] })) : S.clip;
    if (!src?.length) return;
    ev.preventDefault();
    commit((p) => {
      const mm = p.menus.find((x) => x.id === menu.id), added = [];
      for (const { kind, it } of src) {
        const c = JSON.parse(JSON.stringify(it));
        c.x = Math.min(719, c.x + 12); c.y = Math.min(H - 1, c.y + 12);
        if (kind === "button") { c.id = uniqueId(c.id.replace(/\d+$/, "") || "button", mm.buttons.map((b) => b.id)); delete c.nav; }
        const l = listOf(mm, kind); l.push(c); added.push({ kind, i: l.length - 1 });
      }
      S.sels = added; S.element = added[added.length - 1];
    });
  }
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
async function requestPreview(menuId, button, generated = false) {
  const stage = $("#stage");
  if (stage) stage.style.opacity = 0.6;
  try {
    const r = await api("/api/preview", { method: "POST", body: { project: S.project, menu: menuId, button, outline: true } });
    S.preview = r; S.previewFor = menuId;
    drawPreview(generated);
  } catch (e) {
    if (e.data?.issues) showIssues(e.data.issues, t("preview_err")); else openModal(`<h2>${t("preview_err")}</h2><pre class="log">${esc(e.message + "\n" + (e.data?.output || ""))}</pre>`);
  } finally { if ($("#stage")) $("#stage").style.opacity = 1; }
}
function drawPreview() {
  const stage = $("#stage");
  if (!stage || !S.preview) return;
  stage.querySelectorAll(".exact").forEach((n) => n.remove());
  const img = document.createElement("img");
  img.className = "exact"; img.src = S.preview.image; img.alt = "";
  stage.appendChild(img);
  const ex = $("#exact"); if (ex) { ex.textContent = t("hide_preview"); ex.classList.remove("primary"); }
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
      <button class="danger" id="del-el">${t("delete")}</button>`;
    bindFields(el, (p) => find(p).shapes[sel.i], { numeric: ["x", "y", "w", "h"] });
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
    const btnIds = [["__none__", t("nav_auto")], ...menu.buttons.filter((b) => b !== it).map((b) => [b.id, `${b.id} (${b.label || b.image})`])];
    const isImage = sel.kind === "button" && it.image;
    el.innerHTML = `<h2>${sel.kind === "button" ? t("button") : t("text")}</h2>
      ${sel.kind === "button" ? `<label class="field"><span>${t("text")}</span><input data-k="label" value="${esc(it.label)}"></label>
        <label class="field"><span>${t("action")}</span>${selectHtml("action", actionOptions(), it.action)}</label>
        <label class="field"><span></span><label><input type="checkbox" data-k="auto_activate" ${it.auto_activate ? "checked" : ""}> ${t("auto_activate")}</label></label>
        <label class="field" data-nobind><span>${t("image")}</span>${selectHtml("image", [["__none__", t("none")], ...mediaOf("image").map((x) => [x, x])], it.image || "__none__")}
          <div class="hint">${esc(t("image_hint"))}</div></label>`
        : `<label class="field"><span>${t("text")}</span><input data-k="text" value="${esc(it.text)}"></label>`}
      <div class="grid2">
        <label class="field"><span>X</span><input type="number" data-k="x" min="0" max="719" value="${it.x}"></label>
        <label class="field"><span>Y</span><input type="number" data-k="y" min="0" max="${discH() - 1}" value="${it.y}"></label>
        ${isImage ? `<label class="field"><span>${t("width")}</span><input type="number" data-k="width" min="8" max="720" value="${it.width || ""}" placeholder="${t("auto")}"></label>
        <label class="field"><span>${t("highlight_style")}</span>${selectHtml("highlight", [["frame", t("hl_frame")], ["shape", t("hl_shape")]], it.highlight || "frame")}</label>`
        : `<label class="field"><span>${t("size")}</span><input type="number" data-k="size" min="8" max="200" value="${it.size || ""}" placeholder="${menu.font_size || 32}"></label>
        <label class="field"><span>${t("color")}</span><input type="color" data-k="color" value="${esc(it.color || menu.text_color || "#ffffff")}"></label>`}
      </div>
      ${isImage ? "" : `<h3>${t("text_style")}</h3>
      <label class="field"><span>${t("font")}</span>${selectHtml("font", fonts, it.font || "__none__")}<div class="hint">${esc(t("font_hint"))}</div></label>
      <div class="grid2" data-nobind>
        <label class="field"><span><input type="checkbox" id="st-outline" ${it.outline ? "checked" : ""}> ${t("outline")}</span>
          <span class="row"><input type="color" id="st-outline-c" value="${esc((it.outline || "#000000").slice(0, 7))}"><input type="number" id="st-outline-w" min="1" max="10" value="${it.outline_width || 2}" style="width:56px"></span></label>
        <label class="field"><span><input type="checkbox" id="st-shadow" ${it.shadow ? "checked" : ""}> ${t("shadow")}</span>
          <span class="row"><input type="color" id="st-shadow-c" value="${esc((it.shadow || "#000000").slice(0, 7))}"><input type="number" id="st-shadow-o" min="1" max="20" value="${it.shadow_offset || 3}" style="width:56px"></span></label>
      </div>`}
      ${sel.kind === "button" ? `<label class="field"><span>${t("highlight_image")}</span>${selectHtml("highlight_image", [["__none__", t("auto")], ...mediaOf("image").map((x) => [x, x])], it.highlight_image || "__none__")}<div class="hint">${esc(t("highlight_image_hint"))}</div></label>` : ""}
      ${sel.kind === "button" ? `<h3>${t("nav")}</h3><div class="grid2">${["up", "down", "left", "right"].map((d) =>
        `<label class="field"><span>${d}</span>${selectHtml("nav." + d, btnIds, (it.nav || {})[d] || "__none__")}</label>`).join("")}</div>` : ""}
      <button class="danger" id="del-el">${t("delete")}</button>`;
    bindFields(el, (p) => (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i], {
      numeric: ["x", "y", "size", "width"],
      onAfter: (p, key) => {
        const o = (sel.kind === "button" ? find(p).buttons : find(p).texts)[sel.i];
        if (o.nav && !Object.keys(o.nav).length) delete o.nav;
        if (key === "highlight" && o.highlight === "frame") delete o.highlight;
        if (key === "auto_activate" && !o.auto_activate) delete o.auto_activate;
      },
    });
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
  el.innerHTML = `<h2>${t("menu_props")}</h2><div class="hint">${esc(t("nothing_selected"))}</div><h3></h3>
    <label class="field"><span>${t("id")}</span><input id="menu-id" value="${esc(menu.id)}"></label>
    <label class="field"><span>${t("background")}</span>${selectHtml("background", [...none, ...mediaOf("image").map((x) => [x, x])], menu.background || "__none__")}</label>
    <label class="field"><span>${t("background_video")}</span>${selectHtml("background_video", [...none, ...mediaOf("video").map((x) => [x, x])], menu.background_video || "__none__")}</label>
    <div class="grid2">
      <label class="field"><span>${t("background_color")}</span><input type="color" data-k="background_color" value="${esc(menu.background_color || "#000000")}"></label>
      <label class="field"><span>${t("text_color")}</span><input type="color" data-k="text_color" value="${esc(menu.text_color || "#ffffff")}"></label>
      <label class="field"><span>${t("highlight")}</span><input type="color" data-k="highlight_color" value="${esc(menu.highlight_color || "#ffd400")}"></label>
      <label class="field"><span>${t("select_color")}</span><input type="color" data-k="select_color" value="${esc(menu.select_color || "#ff5a00")}"></label>
      <label class="field"><span>${t("font_size")}</span><input type="number" data-k="font_size" min="8" max="200" value="${menu.font_size || ""}" placeholder="32"></label>
      <label class="field"><span>${t("duration")}</span><input type="number" data-k="duration" min="1" max="600" value="${menu.duration || ""}" placeholder="${t("auto")}"></label>
    </div>
    <label class="field"><span>${t("music")}</span>${selectHtml("audio", [...none, ...mediaOf("audio").map((x) => [x, x])], menu.audio || "__none__")}</label>
    <h3>${t("playback")}</h3>
    <div class="grid2">
      <label class="field"><span>${t("loop")}</span>${selectHtml("loop", [["forever", t("loop_forever")], ...[1, 2, 3, 5, 10].map((n) => [String(n), t("loop_n", { n })])], String(menu.loop || "forever"))}</label>
      <label class="field"><span>${t("loop_point")}</span><input type="number" data-k="loop_point" min="0" step="0.1" value="${menu.loop_point ?? ""}" placeholder="0"></label>
    </div>
    ${menu.loop && menu.loop !== "forever" ? `<label class="field"><span>${t("menu_end")}</span>${selectHtml("end_action", actionOptions({ forButton: false, includeChapters: true, allowPlayAll: true }), menu.end_action || "stop")}</label>` : ""}
    <label class="field"><span>${t("default_button")}</span>${selectHtml("default_button", [["__none__", t("auto")], ...(menu.buttons || []).map((b) => [b.id, `${b.id} (${b.label || b.image || ""})`])], menu.default_button || "__none__")}</label>
    <label class="field"><span></span><label><input type="checkbox" id="remember-btn" ${menu.remember_button === false ? "" : "checked"}> ${t("remember_button")}</label></label>
    ${orderHtml(t("order_menu"))}
    <h3></h3><button class="danger" id="del-menu">${t("delete")}</button>`;
  bindFields(el, find, {
    numeric: ["font_size", "duration", "loop_point"],
    onAfter: (p, key, val) => {
      const mm = find(p);
      if (key === "loop") { if (val === "forever") { delete mm.loop; delete mm.end_action; } else mm.loop = Number(val); }
      if (key === "loop_point" && !val) delete mm.loop_point;
    },
  });
  $("#remember-btn").onchange = (e) => commit((p) => { const mm = find(p); if (e.target.checked) delete mm.remember_button; else mm.remember_button = false; });
  bindOrder(el, "menus", menu.id);
  $("#menu-id").onchange = (e) => {
    const nid = e.target.value.trim().replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 40);
    if (!nid || nid === menu.id || allMenuIds().includes(nid)) { e.target.value = menu.id; return; }
    commit((p) => { renameRefs(p, "menu", menu.id, nid); find(p).id = nid; });
    S.sel.id = nid; renderAll();
  };
  $("#del-menu").onclick = () => {
    if (!confirm(t("confirm_delete", { x: menu.id }))) return;
    commit((p) => { p.menus = p.menus.filter((x) => x.id !== menu.id); });
    select("disc");
  };
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
    if (menu) actions.push(`<button class="primary" data-act="bg">${t("use_as_bg")}</button>`);
    actions.push(`<button data-act="newmenu">${t("new_menu_with_bg")}</button>`);
  }
  if (item.kind === "audio" && menu) actions.push(`<button data-act="music">${t("use_as_music")}</button>`);
  if (item.kind === "subtitle" && (P().titles || []).length)
    actions.push(`<div class="hint">${t("add_sub_to")}</div>${(P().titles).map((x) => `<button data-act="sub" data-title="${esc(x.id)}">${esc(x.name || x.id)}</button>`).join(" ")}`);
  el.innerHTML = `<h2 style="word-break:break-all">${esc(path)}</h2>${preview}<p class="hint">${esc(item.kind)} · ${fmtBytes(item.bytes)} ${info}</p>
    <div style="display:flex;flex-direction:column;gap:8px">${actions.join("")}</div>`;
  el.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => mediaAction(b.dataset.act, path, b.dataset.title)));
}
function mediaAction(act, path, titleId) {
  const name = path.split("/").pop().replace(/\.[^.]+$/, "");
  if (act === "title") {
    const id = uniqueId("t", (P().titles || []).map((x) => x.id));
    commit((p) => { (p.titles = p.titles || []).push({ id, name, source: path, chapters: ["00:00:00"] }); });
    S.selectedMedia = null; return select("title", id);
  }
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
function uploadFiles(files) {
  for (const f of files) {
    S.uploads[f.name] = 0; renderSidebar();
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload?" + new URLSearchParams({ name: f.name }));
    xhr.setRequestHeader("X-Oncemore-Token", S.token);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) { S.uploads[f.name] = Math.round((e.loaded / e.total) * 100); renderSidebar(); } };
    xhr.onload = () => {
      delete S.uploads[f.name];
      try {
        const r = JSON.parse(xhr.responseText);
        if (xhr.status === 200) { S.media = r.media; S.selectedMedia = r.path; }
        else alert(r.error);
      } catch (e) { alert(xhr.statusText); }
      renderSidebar(); renderInspector();
    };
    xhr.onerror = () => { delete S.uploads[f.name]; renderSidebar(); };
    xhr.send(f);
  }
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
    const s = r.summary, pct = Math.min(100, (s.estimated_bytes / s.capacity_bytes) * 100);
    openModal(`<h2>✓ ${t("check_ok")}</h2>
      <p>${t("estimated")}: <b>${fmtBytes(s.estimated_bytes)}</b> ${t("of")} ${fmtBytes(s.capacity_bytes)}</p>
      <div class="sizebar"><div style="width:${pct}%"></div></div>
      <p>${t("video_avg")}: <b>${(s.video_bps / 1e6).toFixed(2)} Mbit/s</b></p>
      <table class="mono" style="width:100%">${s.titles.map((x) => `<tr><td>${esc(x.id)}</td><td>${x.duration.toFixed(1)}s</td><td>${x.input}</td><td>${x.chapters.length} ch</td><td>${x.audio}</td><td>${x.aspect || ""}</td></tr>`).join("")}</table>
      ${s.warnings.length ? `<h3>${t("warnings")}</h3><ul class="issues">${s.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}`);
  } catch (e) {
    if (e.data?.issues) showIssues(e.data.issues);
    else openModal(`<h2>${esc(e.message)}</h2>${e.data?.hint ? `<p class="hint">${esc(e.data.hint)}</p>` : ""}`);
  }
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
  m.innerHTML = `<div class="card" style="max-width:720px"><h2>${t("build")}</h2>
    <label style="display:block;margin:6px 0"><input type="radio" name="kind" value="iso" ${(S.buildKind || "iso") === "iso" ? "checked" : ""}> ${t("build_iso")}</label>
    <label style="display:block;margin:6px 0"><input type="radio" name="kind" value="folder" ${S.buildKind === "folder" ? "checked" : ""}> ${t("build_folder")}</label>
    <label style="display:block;margin:10px 0"><input type="checkbox" id="fast" ${S.buildFast ? "checked" : ""}> ${t("fast")}</label>
    <label style="display:block;margin:10px 0"><input type="checkbox" id="nocache" ${S.buildNoCache ? "checked" : ""}> ${t("no_cache")}</label>
    <button class="primary" id="start" ${job && !job.done ? "disabled" : ""}>${job && !job.done ? t("building") : t("start_build")}</button>
  </div>
  ${steps.length ? `<div class="card" style="max-width:720px"><ul class="steps">${steps.map((s, i) => {
    const f = progress[`${s.step}:${s.item ?? ""}`];
    const done = i < steps.length - 1 || (job && job.done);
    const pct = done ? 100 : f !== undefined ? Math.round(f * 100) : 0;
    const label = I18N.en["step_" + s.step] ? t("step_" + s.step, { i: s.item ?? "" }) : s.message;
    return `<li><div class="label"><span title="${esc(s.message)}">${esc(label)}</span><span class="muted">${done ? "✓" : pct + "%"}</span></div><div class="progress"><div style="width:${pct}%"></div></div></li>`;
  }).join("")}</ul></div>` : ""}
  ${result ? `<div class="card result-ok" style="max-width:720px"><h2>✓ ${t("build_done")}</h2>
      <p class="mono">${esc(result.iso || result.video_ts)}</p><p>${fmtBytes(result.iso_bytes || result.bytes)}</p>
      <button id="reveal">${t(S.platform === "darwin" ? "reveal" : "reveal_other")}</button>
      ${result.warnings?.length ? `<h3>${t("warnings")}</h3><ul class="issues">${result.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}</div>` : ""}
  ${error ? `<div class="card result-err" style="max-width:720px"><h2>✕ ${t("build_failed")}</h2><p>${esc(error.message)}</p>
      ${error.hint ? `<p class="hint">${esc(error.hint)}</p>` : ""}
      ${error.issues ? `<ul class="issues">${error.issues.map((i) => `<li><span class="path">${esc(i.path)}</span> ${esc(i.message)}</li>`).join("")}</ul>` : ""}
      ${error.output ? `<pre class="log">${esc(error.output)}</pre>` : ""}</div>` : ""}
  ${logs.length ? `<div class="card" style="max-width:720px"><div class="log">${esc(logs.join("\n"))}</div></div>` : ""}`;
  m.querySelectorAll("input[name=kind]").forEach((r) => (r.onchange = () => (S.buildKind = r.value)));
  $("#fast").onchange = (e) => (S.buildFast = e.target.checked);
  $("#nocache").onchange = (e) => (S.buildNoCache = e.target.checked);
  $("#start").onclick = startBuild;
  const rv = $("#reveal");
  if (rv) rv.onclick = () => api("/api/reveal", { method: "POST", body: { path: relPath(result.iso || result.video_ts) } }).catch((e) => alert(e.message));
}
const relPath = (abs) => abs.startsWith(S.dir) ? abs.slice(S.dir.length + 1) : abs;
async function startBuild() {
  clearTimeout(S.saveTimer); await save();
  try {
    const r = await api("/api/build", { method: "POST", body: { kind: S.buildKind || "iso", fast: !!S.buildFast, no_cache: !!S.buildNoCache } });
    S.job = { id: r.job, done: false }; S.jobEvents = []; S.jobNext = 0;
    pollJob();
  } catch (e) { alert(e.message); }
  if (S.sel.view === "build") renderMain();
}
async function pollJob() {
  if (!S.job) return;
  try {
    const r = await api(`/api/jobs/${S.job.id}?since=${S.jobNext}`);
    S.jobEvents.push(...r.events); S.jobNext = r.next; S.job.done = r.done; S.job.ok = r.ok;
  } catch (e) { console.error(e); }
  if (S.sel.view === "build") renderMain();
  if (!S.job.done) setTimeout(pollJob, 500);
}

// ---------------------------------------------------------------- boot
function applyState(r) {
  S.project = r.project; S.dir = r.dir; S.media = r.media; S.check = r.check;
  S.tools = r.tools; S.platform = r.platform;
}
async function boot() {
  const m = location.hash.match(/token=([\w-]+)/);
  if (m) { S.token = m[1]; sessionStorage.setItem("oncemore.token", S.token); history.replaceState(null, "", location.pathname); }
  else S.token = sessionStorage.getItem("oncemore.token") || "";
  try { applyState(await api("/api/state")); }
  catch (e) { document.body.innerHTML = `<div class="empty"><h2>oncemore</h2><p>${esc(e.message)}</p><p class="hint">Open the URL printed by <code>oncemore gui</code>.</p></div>`; return; }
  const first = P()?.menus?.[0];
  S.sel = first ? { view: "menu", id: first.id } : { view: "disc" };
  renderAll();
}
$("#btn-undo").onclick = undo;
$("#btn-redo").onclick = redo;
$("#btn-check").onclick = runCheck;
$("#btn-build").onclick = () => select("build");
$("#btn-lang").onclick = () => { LANG = LANG === "ja" ? "en" : "ja"; localStorage.setItem("oncemore.lang", LANG); renderAll(); };
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.classList.contains("modal-close")) closeModal(); });
window.addEventListener("keydown", (e) => {
  const inField = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName);
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z" && !inField) { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (e.key === "Escape") closeModal();
  if (inField) return;
  stageKeys(e);
});
window.addEventListener("resize", () => { if (S.sel.view === "menu") renderMain(); });
boot();
