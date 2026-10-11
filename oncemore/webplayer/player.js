// The web version of a disc made with oncemore: follows the disc's links as
// a player does (the rules of oncemore/simulate.py), with window.DISC from
// disc.js. Keys: arrows and Enter in menus, number keys, M = Menu key,
// T = Title key, PageUp / PageDown = previous / next chapter, Space = pause.
"use strict";
(() => {
  const D = window.DISC;
  const $ = (id) => document.getElementById(id);
  const screen = $("screen"), menuBox = $("menu"), image = $("menu-image"), mvideo = $("menu-video"),
    normal = $("menu-normal"), highlight = $("menu-highlight"), hotspots = $("hotspots"),
    tvideo = $("title"), trans = $("transition"), stopped = $("stopped");
  const S = {
    domain: "stopped", menu: null, button: 0, title: null, chapter: 1, playall: false,
    playlist: null, item: 0, queue: null, pos: 0, endAt: null, override: null, lastMenu: null, menuKey: null,
    remember: {}, resume: null, loops: 0, subtitle: null, log: [],
  };
  window.oncemorePlayer = { state: S, press, disc: D };
  let timer = null;

  function note(text) { S.log.push(text); if (S.log.length > 50) S.log.shift(); }
  function parse(a) {
    a = a || "stop";
    if (["stop", "playall", "resume", "lastmenu"].includes(a)) return [a, null, null];
    const i = a.indexOf(":"), kind = a.slice(0, i), rest = a.slice(i + 1);
    if (kind === "chapter") { const j = rest.lastIndexOf(":"); return ["chapter", rest.slice(0, j), +rest.slice(j + 1)]; }
    if (kind === "audio" || kind === "subtitle") return [kind, null, rest === "off" ? 0 : +rest];
    if (kind === "menu") { const j = rest.indexOf(":"); return j < 0 ? ["menu", rest, null] : ["menu", rest.slice(0, j), rest.slice(j + 1)]; }
    return [kind, rest, null];
  }
  const play = (v) => { const p = v.play(); if (p && p.catch) p.catch(() => {}); };
  function hideAll() {
    clearTimeout(timer);
    for (const v of [mvideo, tvideo, trans]) v.pause();
    menuBox.hidden = true; tvideo.hidden = true; trans.hidden = true; stopped.hidden = true;
  }

  // -- menus -------------------------------------------------------------------
  function enterMenu(id, button) {
    const m = D.menus[id];
    if (!m) return stop();
    hideAll();
    Object.assign(S, { domain: "menu", menu: id, title: null, loops: 0, lastMenu: id, endAt: null });
    const ids = m.buttons.map((b) => b.id);
    let k = m.default ? ids.indexOf(m.default) : 0;
    if (m.remember && S.remember[id] != null) k = S.remember[id];
    if (button && ids.includes(button)) k = ids.indexOf(button);
    S.button = Math.max(0, k);
    const [w, h] = m.size;
    screen.style.setProperty("--ratio", `${w} / ${h}`);
    image.src = m.image;
    normal.hidden = !m.normal;
    if (m.normal) normal.src = m.normal;
    highlight.src = m.highlight;
    hotspots.replaceChildren(...m.buttons.map((b, i) => {
      const el = document.createElement("button");
      const [x0, y0, x1, y1] = b.rect;
      Object.assign(el.style, { left: `${(x0 / w) * 100}%`, top: `${(y0 / h) * 100}%`,
        width: `${((x1 - x0) / w) * 100}%`, height: `${((y1 - y0) / h) * 100}%` });
      el.type = "button"; el.dataset.id = b.id; el.title = String(b.number);
      el.setAttribute("aria-label", b.id);
      el.onmouseenter = () => select(i);
      el.onclick = (e) => { e.preventDefault(); select(i); activate(); };
      return el;
    }));
    menuBox.hidden = false;
    if (m.video) {
      mvideo.hidden = false; mvideo.src = m.video; mvideo.currentTime = 0; play(mvideo);
    } else {
      mvideo.hidden = true; mvideo.removeAttribute("src");
      if (m.loop != null) timer = setTimeout(() => timeout(id), m.duration * Math.max(1, m.loop) * 1000);
    }
    showHighlight();
    note(`menu ${id}`);
    screen.focus({ preventScroll: true });
  }
  function showHighlight() {
    const m = D.menus[S.menu], b = m && m.buttons[S.button];
    if (!b) { highlight.style.clipPath = "inset(100%)"; return; }
    const [w, h] = m.size, [x0, y0, x1, y1] = b.rect;
    highlight.style.clipPath = `inset(${(y0 / h) * 100}% ${(1 - x1 / w) * 100}% ${(1 - y1 / h) * 100}% ${(x0 / w) * 100}%)`;
  }
  function select(i) {
    if (S.domain !== "menu" || i === S.button) return;
    S.button = i;
    showHighlight();
    if (D.menus[S.menu].buttons[i].auto) activate();
  }
  function timeout(id) {
    if (S.domain !== "menu" || S.menu !== id) return;
    note(`menu ${id} timed out`);
    menuCommand(D.menus[id].end_action);
  }
  mvideo.addEventListener("ended", () => {
    const m = D.menus[S.menu];
    if (S.domain !== "menu" || !m) return;
    S.loops += 1;
    if (m.loop != null && S.loops >= m.loop) return timeout(S.menu);
    mvideo.currentTime = m.loop_point || 0; play(mvideo);
  });
  function activate() {
    const m = D.menus[S.menu], b = m && m.buttons[S.button];
    if (!b) return;
    note(`button ${b.id} -> ${b.action}`);
    const kind = parse(b.action)[0];
    if (m.remember && kind !== "audio" && kind !== "subtitle") S.remember[S.menu] = S.button;
    const go = () => {
      if (b.subtitle != null) S.subtitle = b.subtitle;
      menuCommand(b.action);
      if (b.override && (kind === "title" || kind === "chapter")) S.override = b.override;
    };
    if (b.transition) {
      hideAll(); trans.hidden = false; trans.src = b.transition; trans.currentTime = 0;
      trans.onended = () => { trans.onended = null; go(); };
      note(`transition ${b.transition}`);
      play(trans);
    } else go();
  }

  // -- titles ------------------------------------------------------------------
  function playTitle(id, chapter = 1, at = null) {
    const t = D.titles[id];
    if (!t) return stop();
    hideAll();
    Object.assign(S, { domain: "title", menu: null, title: id, chapter, loops: 0 });
    S.menuKey = t.menu_key;
    screen.style.setProperty("--ratio", "16 / 9");
    if (tvideo.dataset.title !== id) {
      tvideo.dataset.title = id;
      tvideo.src = t.src;
      tvideo.replaceChildren(...t.subtitles.map((s, i) => {
        const tr = document.createElement("track");
        Object.assign(tr, { kind: "subtitles", src: s.src, srclang: s.lang || "und", label: s.lang || `${i + 1}`, default: !!s.default });
        return tr;
      }));
    }
    tvideo.hidden = false;
    const start = at != null ? at : t.chapters[Math.min(chapter, t.chapters.length) - 1] || 0;
    try { tvideo.currentTime = start; } catch (e) { /* not loaded yet */ }
    tvideo.dataset.start = start;
    applySubtitle();
    play(tvideo);
    note(`title ${id} chapter ${chapter}`);
    screen.focus({ preventScroll: true });
  }
  function applySubtitle() {
    if (S.subtitle == null) return;
    [...tvideo.textTracks].forEach((tr, i) => { tr.mode = i + 1 === S.subtitle ? "showing" : "disabled"; });
  }
  tvideo.addEventListener("loadedmetadata", () => {
    const s = +tvideo.dataset.start || 0;
    if (s && Math.abs(tvideo.currentTime - s) > 0.5) tvideo.currentTime = s;
    applySubtitle();
  });
  function chapterAt(time) {
    const ch = D.titles[S.title].chapters;
    let k = 1;
    ch.forEach((c, i) => { if (time + 0.05 >= c) k = i + 1; });
    return k;
  }
  tvideo.addEventListener("timeupdate", () => {
    if (S.domain !== "title") return;
    S.chapter = chapterAt(tvideo.currentTime);
    if (S.endAt != null && tvideo.currentTime >= S.endAt) post();
  });
  tvideo.addEventListener("ended", () => { if (S.domain === "title") post(); });
  function single() { S.override = null; S.playall = false; S.playlist = null; S.endAt = null; }
  function stop() {
    hideAll();
    Object.assign(S, { domain: "stopped", menu: null, title: null, endAt: null });
    stopped.hidden = false;
    note("stop");
  }
  // the items in the order they play: as listed, shuffled (each once) or
  // random (as many picks as there are items, one may come again)
  function itemOrder(pl) {
    const n = pl.items.length, out = [...Array(n).keys()];
    if (pl.order === "random") return out.map(() => Math.floor(Math.random() * n));
    if (pl.order === "shuffle") for (let i = n - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }
  function playlistStart(pid, pos = 0, queue = null) {
    const pl = D.playlists[pid];
    if (!pl) return stop();
    queue = queue || itemOrder(pl);
    const index = queue[pos];
    if (index == null || !pl.items[index]) return stop();
    const it = pl.items[index], t = D.titles[it.title];
    S.override = null; S.playall = false; S.playlist = pid; S.item = index; S.queue = queue; S.pos = pos;
    S.endAt = it.last && t && it.last < t.chapters.length ? t.chapters[it.last] : null;
    playTitle(it.title, it.first || 1);
  }

  // -- what buttons, menus and titles do -----------------------------------------
  function menuCommand(action) {
    const [kind, target, num] = parse(action);
    if (kind === "menu") enterMenu(target, num);
    else if (kind === "playlist") playlistStart(target);
    else if (kind === "playall") { single(); S.playall = true; playTitle(D.order[0]); }
    else if (kind === "title") { single(); playTitle(target); }
    else if (kind === "chapter") { single(); playTitle(target, num); }
    else if (kind === "resume") {
      const r = S.resume;
      if (r) { S.resume = null; playTitle(r.title, r.chapter, r.time); note(`resume ${r.title}`); }
      else { single(); playTitle(D.order[0]); }
    } else if (kind === "subtitle") { S.subtitle = num; applySubtitle(); note(`subtitle ${num || "off"}`); }
    else if (kind === "audio") note(`audio ${num} (the web version has one sound track)`);
    else stop();
  }
  function endCommand(action) {
    const [kind, target, num] = parse(action);
    if (kind === "menu") enterMenu(target, num);
    else if (kind === "lastmenu") enterMenu(S.lastMenu || S.menuKey || D.root);
    else if (kind === "title") { S.endAt = null; playTitle(target); }
    else if (kind === "chapter") { S.endAt = null; playTitle(target, num); }
    else if (kind === "playlist") playlistStart(target);
    else if (kind === "playall") { S.playall = true; playTitle(D.order[0]); }
    else stop();
  }
  function post() {
    const id = S.title;
    note(`title ${id} ended`);
    S.resume = null; S.endAt = null;
    if (S.override) { const a = S.override; S.override = null; return endCommand(a); }
    if (S.playlist) {
      const pl = D.playlists[S.playlist];
      if (S.pos + 1 < S.queue.length) return playlistStart(S.playlist, S.pos + 1, S.queue);
      S.playlist = null;
      return endCommand(pl.end_action);
    }
    if (S.playall) {
      const i = D.order.indexOf(id);
      if (i + 1 < D.order.length) return playTitle(D.order[i + 1]);
      S.playall = false;
    }
    endCommand(D.titles[id].end_action);
  }

  // -- the remote ----------------------------------------------------------------
  const DIRS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
  let digits = "", digitTimer = null;
  function press(key) {
    const here = S.domain === "title" ? D.titles[S.title] : S.domain === "menu" ? D.menus[S.menu] : null;
    if (["menu", "title", "next", "prev"].includes(key) && here && here.prohibit.includes(key)) {
      note(`${key} not allowed here`); return;
    }
    if (S.domain === "title" && (key === "menu" || key === "title") && D.root) {
      S.resume = { title: S.title, chapter: S.chapter, time: tvideo.currentTime };
    }
    if (key === "title") {
      if (!D.root) return;
      const [kind, target, num] = parse(D.title_key);
      if (kind === "playlist") return playlistStart(target);
      if (kind === "playall") { single(); S.playall = true; return playTitle(D.order[0]); }
      if (kind === "title") { single(); return playTitle(target); }
      return enterMenu(target, num);
    }
    if (S.domain === "menu") {
      const m = D.menus[S.menu], b = m.buttons[S.button];
      if (["up", "down", "left", "right"].includes(key) && b) { const to = m.buttons.findIndex((x) => x.id === b.nav[key]); if (to >= 0) select(to); }
      else if (key === "enter") activate();
      else if (key === "menu") enterMenu(D.root);
      else if (key.startsWith("number:")) {
        const n = +key.slice(7) - (m.buttons[0] ? m.buttons[0].number - 1 : 0);
        if (n >= 1 && n <= m.buttons.length) { S.button = n - 1; showHighlight(); activate(); }
        else note(`no button ${key.slice(7)} here`);
      }
      return;
    }
    if (S.domain !== "title") return;
    const t = D.titles[S.title];
    if (key === "menu" && D.root) enterMenu(S.menuKey || D.root);
    else if (key === "next") {
      if (S.chapter < t.chapters.length) { S.chapter += 1; tvideo.currentTime = t.chapters[S.chapter - 1]; note(`chapter ${S.chapter}`); }
      else post();
    } else if (key === "prev") {
      S.chapter = Math.max(1, S.chapter - 1); tvideo.currentTime = t.chapters[S.chapter - 1]; note(`chapter ${S.chapter}`);
    } else if (key === "pause") { if (tvideo.paused) play(tvideo); else tvideo.pause(); }
  }
  document.addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    let key = DIRS[e.key] || null;
    if (e.key === "Enter") key = "enter";
    else if (e.key === "m" || e.key === "M") key = "menu";
    else if (e.key === "t" || e.key === "T") key = "title";
    else if (e.key === "PageDown") key = "next";
    else if (e.key === "PageUp") key = "prev";
    else if (e.key === " " && S.domain === "title") key = "pause";
    else if (/^[0-9]$/.test(e.key) && S.domain === "menu") {
      // number keys: two typed together are one number, as on a remote
      e.preventDefault();
      digits = (digits + e.key).slice(-2);
      clearTimeout(digitTimer);
      digitTimer = setTimeout(() => { const n = digits; digits = ""; press(`number:${+n}`); }, 700);
      return;
    }
    if (!key) return;
    e.preventDefault();
    press(key);
  });
  for (const b of document.querySelectorAll("#remote [data-key]")) b.onclick = () => press(b.dataset.key);
  $("restart").onclick = start;

  function start() {
    S.log = [];
    document.title = D.label || document.title;
    const [kind, target, num] = parse(D.first_play);
    note(`first play: ${D.first_play}`);
    if (kind === "menu") enterMenu(target, num);
    else if (kind === "playlist") playlistStart(target);
    else if (kind === "playall") { S.playall = true; playTitle(D.order[0]); }
    else if (kind === "title") playTitle(target);
    else if (D.root) enterMenu(D.root);
    else stop();
  }
  start();
})();
