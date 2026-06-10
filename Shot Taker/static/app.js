/* ============================================================
   ShotTaker — front-end application logic
   ============================================================ */
const api  = async (u, o) => (await fetch(u, o)).json();
const post = (u, b) => api(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) });
const $ = (id) => document.getElementById(id);
const esc = (s) => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* on-brand SVG icon helpers (reference the inline sprite in index.html) */
const ic = (name) => `<svg class="ic"><use href="#i-${name}"/></svg>`;
const rateStars = (n) => n ? `<span class="rate-stars">${ic("star-fill").repeat(n)}</span>` : "";

let SETTINGS = {};
let BRAND = {};
let lastCaptureTs = 0;

/* ---------- boot ---------- */
window.addEventListener("DOMContentLoaded", init);

async function init() {
  BRAND = await api("/api/brand");
  applyBrand(BRAND);
  SETTINGS = await api("/api/settings");
  applyTheme(SETTINGS.theme || "dark");

  document.querySelectorAll("#nav button").forEach(b =>
    b.onclick = () => switchTab(b.dataset.tab, b));

  buildSettingsTabs();
  loadDashboard();
  loadLog();
  refreshStatus();
  setInterval(refreshStatus, 4000);
  setInterval(pollCaptureToast, 4000);
  setInterval(() => { if (currentTab === "dashboard") loadLog(); }, 6000);

  const setup = await api("/api/setup/status");
  if (!setup.setup_complete) openSetup();
}

function applyBrand(b) {
  const c = b.colors || {};
  const r = document.documentElement.style;
  Object.entries(c).forEach(([k, v]) => r.setProperty("--" + k, v));
  $("brandName").textContent = b.name || "ShotTaker";
  $("brandTag").textContent = b.tagline || "";
  $("verFoot").textContent = "v" + (b.version || "");
  document.title = b.name || "ShotTaker";
}
function applyTheme(t) { document.documentElement.setAttribute("data-theme", t); }

/* ---------- tabs ---------- */
let currentTab = "dashboard";
const TITLES = { dashboard: "Dashboard", gallery: "Gallery", games: "Games", stats: "Stats", settings: "Settings" };
function switchTab(tab, btn) {
  currentTab = tab;
  document.querySelectorAll(".tabpage").forEach(p => p.classList.remove("active"));
  $("page-" + tab).classList.add("active");
  document.querySelectorAll("#nav button").forEach(b => b.classList.remove("active"));
  (btn || document.querySelector(`#nav button[data-tab="${tab}"]`)).classList.add("active");
  $("pageTitle").textContent = TITLES[tab];
  if (tab === "gallery") { loadGameFilter(); loadGallery(); }
  if (tab === "games") loadGames();
  if (tab === "stats") loadStats();
  if (tab === "settings") renderSettings();
}

/* ---------- status ---------- */
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("statusDot").classList.toggle("live", !!s.gameActive);
    if (s.gameActive && s.activeGame) {
      $("nowPlaying").innerHTML = `<b>${esc(nameOf(s.activeGame))}</b> · ${esc(s.activePlatform || "")} ·
        <span class="muted">${s.sessionShots || 0} shots this session</span>`;
    } else {
      $("nowPlaying").textContent = "No game detected.";
    }
    SETTINGS.capture_paused = SETTINGS.capture_paused; // keep
    const paused = (await api("/api/settings")).capture_paused;
    $("pauseBtn").innerHTML = paused ? ic("play") + " Resume" : ic("pause") + " Pause";
    $("pauseBtn").classList.toggle("primary", paused);
  } catch (e) {}
}
let NAMES = {};
function nameOf(exe) { return NAMES[exe] || exe; }

async function togglePause() {
  const cur = (await api("/api/settings")).capture_paused;
  await post("/api/capture/pause", { paused: !cur });
  refreshStatus();
  toast(!cur ? "Capture paused" : "Capture resumed");
}
async function captureNow() { await post("/api/capture/now"); toast("Grabbing a shot…", "ok"); }
async function fireBurst() { await post("/api/burst/fire"); toast("Burst away — spray and pray", "ok"); }

/* ---------- dashboard ---------- */
async function loadDashboard() {
  const st = await api("/api/status");
  const stats = await api("/api/stats");
  $("dashCards").innerHTML = [
    card("Games on deck", st.games || 0, true),
    card("Shots captured", stats.screenshots_taken || 0),
    card("Now playing", st.gameActive ? nameOf(st.activeGame) : "—"),
    card("Library scans", stats.scan_count || 0),
  ].join("");
}
function card(label, value, grad) {
  return `<div class="card"><div class="label">${label}</div>
    <div class="value ${grad ? "grad" : ""}">${esc(String(value))}</div></div>`;
}
async function loadLog() {
  const lines = await api("/api/log");
  $("log").innerHTML = lines.map(l => {
    let cls = "";
    if (l.toLowerCase().includes("error") || l.includes("failed")) cls = "err";
    else if (l.includes("[CAP]") || l.includes("[SHOT]")) cls = "cap";
    else if (l.includes("[ACT]")) cls = "act";
    else if (l.includes("[ACH]")) cls = "ach";
    return `<div class="line ${cls}">${esc(l)}</div>`;
  }).join("");
}

/* ---------- capture toast ---------- */
async function pollCaptureToast() {
  if (!SETTINGS.capture_toast) return;
  try {
    const c = await api("/api/capture/last");
    if (c && c.ts && c.ts > lastCaptureTs) {
      if (lastCaptureTs) toast(c.type + " captured", "ok", "capture");
      lastCaptureTs = c.ts;
    }
  } catch (e) {}
}

/* ============================================================
   GALLERY
   ============================================================ */
let galleryPage = 1, favOnly = false, selectMode = false, selected = new Set();
let galleryItems = [], sessionMode = false;
let debounceTimer;
function debouncedGallery() { clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { galleryPage = 1; loadGallery(); }, 250); }

async function loadGameFilter() {
  const games = await api("/api/gallery/games");
  const sel = $("gGame");
  sel.innerHTML = `<option value="">All games</option>` +
    games.map(g => `<option value="${esc(g.folder)}">${esc(g.name)}</option>`).join("");
}
function toggleFavFilter() { favOnly = !favOnly; $("favFilter").classList.toggle("primary", favOnly); galleryPage = 1; loadGallery(); }

async function loadGallery() {
  sessionMode = false;
  const q = new URLSearchParams({
    game: $("gGame").value, type: $("gType").value, sort: $("gSort").value,
    search: $("gSearch").value, favorites: favOnly ? "1" : "", page: galleryPage, per_page: 24,
  });
  const data = await api("/api/gallery/screenshots?" + q);
  renderGallery(data);
}
async function loadSessionView() {
  sessionMode = true;
  const data = await api("/api/gallery/session?page=1&per_page=48");
  renderGallery(data);
  toast(data.session ? "Showing last session: " + nameOf(data.session.game) : "No recent session");
}

function renderGallery(data) {
  galleryItems = data.items || [];
  const grid = $("galleryGrid");
  if (!galleryItems.length) {
    grid.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="big">${ic("gallery")}</div>
      No loot yet. Boot a game — your highlights land here.</div>`;
    $("galleryPager").innerHTML = "";
    return;
  }
  grid.innerHTML = galleryItems.map((it, i) => `
    <div class="shot ${selected.has(it.path) ? "selected" : ""}" data-i="${i}">
      ${selectMode ? `<input type="checkbox" class="pick" ${selected.has(it.path) ? "checked" : ""}
          onchange="toggleSelect('${b64(it.path)}', this)">` : ""}
      <button class="fav ${it.favorite ? "on" : ""}" onclick="favShot(${i})">${it.favorite ? ic("star-fill") : ic("star")}</button>
      <img class="thumb" loading="lazy" src="${it.thumb}" onclick="openLightbox(${i})" />
      <div class="meta"><div class="g">${esc(it.name || it.game)}</div>
        <div class="s"><span class="chip type">${it.type}</span>${rateStars(it.rating)}</div></div>
    </div>`).join("");
  if (!sessionMode) renderPager(data);
  else $("galleryPager").innerHTML = "";
}
function renderPager(d) {
  if (d.pages <= 1) { $("galleryPager").innerHTML = ""; return; }
  let h = `<button class="btn sm" ${d.page <= 1 ? "disabled" : ""} onclick="goPage(${d.page - 1})">‹</button>`;
  for (let p = Math.max(1, d.page - 2); p <= Math.min(d.pages, d.page + 2); p++)
    h += `<button class="btn sm ${p === d.page ? "primary" : ""}" onclick="goPage(${p})">${p}</button>`;
  h += `<button class="btn sm" ${d.page >= d.pages ? "disabled" : ""} onclick="goPage(${d.page + 1})">›</button>`;
  $("galleryPager").innerHTML = h;
}
function goPage(p) { galleryPage = p; loadGallery(); }

async function favShot(i) {
  const it = galleryItems[i];
  const r = await post("/api/gallery/favorite", { path: it.path });
  it.favorite = r.favorite; renderGallery({ items: galleryItems, pages: 1, page: 1 });
}

/* selection + bulk */
const b64 = (s) => btoa(unescape(encodeURIComponent(s)));
const unb64 = (s) => decodeURIComponent(escape(atob(s)));
function toggleSelectMode() {
  selectMode = !selectMode; selected.clear();
  $("selBtn").classList.toggle("primary", selectMode);
  $("bulkBar").style.display = selectMode ? "flex" : "none";
  renderGallery({ items: galleryItems, pages: 1, page: galleryPage });
}
function toggleSelect(p64, el) {
  const p = unb64(p64);
  el.checked ? selected.add(p) : selected.delete(p);
  $("selCount").textContent = selected.size + " selected";
  el.closest(".shot").classList.toggle("selected", el.checked);
}
async function bulkExport(kind) {
  if (!selected.size) return toast("Select some screenshots first", "err");
  toast("Building " + kind + "…");
  const r = await post("/api/export/" + kind, { paths: [...selected] });
  toast(r.success ? "Exported → " + r.path : "Export failed: " + r.error, r.success ? "ok" : "err");
}
async function bulkDelete() {
  if (!selected.size || !confirm(`Delete ${selected.size} screenshot(s)?`)) return;
  const r = await post("/api/gallery/delete", { paths: [...selected] });
  toast("Deleted " + r.deleted, "ok"); selected.clear(); loadGallery();
}
function openRename() {
  if (!selected.size) return toast("Select some screenshots first", "err");
  openModal("renameOverlay");
}
async function doRename() {
  const r = await post("/api/gallery/rename",
    { paths: [...selected], game_name: $("renameGame").value, shot_type: $("renameType").value });
  closeModal("renameOverlay");
  toast(r.success ? "Renamed " + r.renamed : "Rename failed", r.success ? "ok" : "err");
  selected.clear(); loadGallery();
}

/* ---------- lightbox ---------- */
let lbIndex = 0;
function openLightbox(i) { lbIndex = i; showLb(); $("lightbox").classList.add("open"); }
function closeLightbox() { $("lightbox").classList.remove("open"); }
function lbNav(d) { lbIndex = (lbIndex + d + galleryItems.length) % galleryItems.length; showLb(); }
function showLb() {
  const it = galleryItems[lbIndex];
  $("lbImg").src = it.url;
  $("lbFav").classList.toggle("primary", it.favorite);
  $("lbFav").innerHTML = (it.favorite ? ic("star-fill") : ic("star")) + (it.favorite ? " Favorited" : " Favorite");
  $("lbStars").innerHTML = [1, 2, 3, 4, 5].map(n =>
    `<span class="${n <= (it.rating || 0) ? "on" : ""}" onclick="lbRate(${n})">${ic(n <= (it.rating || 0) ? "star-fill" : "star")}</span>`).join("");
}
async function lbFavorite() {
  const it = galleryItems[lbIndex];
  const r = await post("/api/gallery/favorite", { path: it.path });
  it.favorite = r.favorite; showLb();
}
async function lbRate(n) {
  const it = galleryItems[lbIndex];
  const r = await post("/api/gallery/rate", { path: it.path, rating: n });
  it.rating = r.rating; showLb();
}
async function lbTag() {
  const it = galleryItems[lbIndex];
  const t = prompt("Tags (comma separated):", (it.tags || []).join(", "));
  if (t === null) return;
  const r = await post("/api/gallery/tag", { path: it.path, tags: t.split(",").map(x => x.trim()) });
  it.tags = r.tags; toast("Tags saved", "ok");
}
async function lbOpen() { await post("/api/gallery/open", { path: galleryItems[lbIndex].path }); }
async function lbDelete() {
  if (!confirm("Delete this screenshot?")) return;
  await post("/api/gallery/delete", { path: galleryItems[lbIndex].path });
  closeLightbox(); loadGallery();
}
document.addEventListener("keydown", e => {
  if (!$("lightbox").classList.contains("open")) return;
  if (e.key === "Escape") closeLightbox();
  if (e.key === "ArrowLeft") lbNav(-1);
  if (e.key === "ArrowRight") lbNav(1);
});

/* ============================================================
   GAMES
   ============================================================ */
let GAMES = {};
async function loadGames() {
  const d = await api("/api/games");
  GAMES = d.games || {}; NAMES = d.names || {};
  const platforms = [...new Set(Object.values(GAMES))];
  $("gamesPlatform").innerHTML = `<option value="">All platforms</option>` +
    platforms.map(p => `<option>${p}</option>`).join("");
  renderGames();
}
function renderGames() {
  const q = ($("gamesSearch").value || "").toLowerCase();
  const plat = $("gamesPlatform").value;
  const rows = Object.entries(GAMES).filter(([exe, p]) =>
    (!plat || p === plat) && (exe.includes(q) || nameOf(exe).toLowerCase().includes(q)));
  $("gamesCount").textContent = `${rows.length} of ${Object.keys(GAMES).length} games`;
  $("gamesList").innerHTML = rows.map(([exe, p]) => `
    <div class="list-row">
      <div class="grow"><div class="name">${esc(nameOf(exe))}</div>
        <div class="sub">${esc(exe)}</div></div>
      <span class="chip ${p}">${p}</span>
      <button class="btn sm" onclick="renameGameName('${esc(exe)}')">Rename</button>
      <button class="btn sm" onclick="disableGame('${esc(exe)}')">Hide</button>
      <button class="btn sm danger" onclick="blacklistGame('${esc(exe)}')">Blacklist</button>
    </div>`).join("") || `<div class="empty"><div class="big">${ic("games")}</div>No games found yet. Point ShotTaker at your libraries in Settings → Game folders.</div>`;
}
async function renameGameName(exe) {
  const n = prompt("Friendly name for " + exe + ":", nameOf(exe));
  if (n === null) return;
  await post("/api/names/set", { exe, name: n });
  loadGames(); toast("Name saved", "ok");
}
async function disableGame(exe) { await post("/api/games/disable", { exe }); toast("Hidden"); loadGames(); }
async function blacklistGame(exe) { await post("/api/blacklist/add", { exe }); toast("Blacklisted"); loadGames(); }
async function triggerScan() { toast("Scanning…"); await api("/api/scan/games"); loadGames(); toast("Scan complete", "ok"); }

/* ============================================================
   STATS
   ============================================================ */
async function loadStats() {
  const s = await api("/api/stats/summary");
  $("statCards").innerHTML = [
    card("Shots captured", s.total_screenshots || 0, true),
    card("Favorites", s.favorites || 0),
    card("Runs logged", s.total_sessions || 0),
    card("Hours sunk", fmtDur(s.total_playtime_seconds || 0)),
    card("Games played", s.games_played || 0),
    card("Most played", s.most_played_game || "—"),
  ].join("");
  // sparkline
  const days = s.captures_per_day || {};
  const vals = Object.values(days); const max = Math.max(1, ...vals);
  $("sparkline").innerHTML = Object.entries(days).map(([d, v]) =>
    `<div class="sb" style="height:${(v / max) * 100}%" title="${d}: ${v}"></div>`).join("")
    || `<div class="muted">No captures in the last 30 days.</div>`;
  $("shotsByGame").innerHTML = bars(s.shots_by_game);
  $("playtimeByGame").innerHTML = bars(s.playtime_by_game, fmtDur);
  $("recentSessions").innerHTML = (s.recent_sessions || []).slice().reverse().map(x =>
    `<div class="list-row"><div class="grow"><div class="name">${esc(nameOf(x.game))}</div>
      <div class="sub">${x.timestamp} · ${fmtDur(x.duration)} · ${x.shots} shots</div></div></div>`).join("")
    || `<div class="muted">No sessions yet.</div>`;
  const events = await api("/api/events");
  $("eventLog").innerHTML = events.slice(0, 30).map(e =>
    `<div class="list-row"><span class="chip gold">${e.kind}</span>
      <div class="grow"><div class="name">${esc(nameOf(e.game))}</div>
      <div class="sub">${e.timestamp}</div></div></div>`).join("") || `<div class="muted">No events yet.</div>`;
}
function bars(obj, fmt) {
  const entries = Object.entries(obj || {});
  if (!entries.length) return `<div class="muted">No data yet.</div>`;
  const max = Math.max(...entries.map(e => e[1]));
  return entries.map(([k, v]) => `<div class="bar-row"><div class="bl">${esc(k)}</div>
    <div class="bt"><div class="bf" style="width:${(v / max) * 100}%"></div></div>
    <div class="bv">${fmt ? fmt(v) : v}</div></div>`).join("");
}
function fmtDur(s) {
  s = Math.round(s); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h}h ${m}m` : `${m}m`;
}

/* ============================================================
   SETTINGS  (schema-driven)
   ============================================================ */
const SETTINGS_TABS = {
  Capture: [
    { type: "select", key: "capture_mode", title: "Capture mode",
      desc: "Time Lapse = on a timer · Action = on screen change · Hybrid = both",
      options: [["timelapse", "Time Lapse"], ["action", "Action Shots"], ["hybrid", "Hybrid"]] },
    { type: "number", key: "interval", title: "Time-lapse interval (seconds)", min: 5, max: 7200, scale: 1000 },
    { type: "number", key: "first_delay", title: "First-shot delay (seconds)", min: 0, max: 120 },
    { type: "select", key: "monitor", title: "Monitor", dynamic: "monitors" },
    { type: "select", key: "screenshot_format", title: "Format",
      options: [["png", "PNG (lossless)"], ["jpeg", "JPEG"], ["webp", "WebP (smallest)"]] },
    { type: "number", key: "jpeg_quality", title: "JPEG quality", min: 50, max: 100 },
    { type: "number", key: "webp_quality", title: "WebP quality", min: 50, max: 100 },
    { type: "number", key: "capture_scale", title: "Resolution scale (%)", min: 25, max: 100,
      desc: "Downscale to save space. 100 = native." },
    { type: "toggle", key: "per_game_folders", title: "Per-game folders" },
  ],
  Quality: [
    { type: "number", key: "sensitivity", title: "Action sensitivity", min: 5, max: 100,
      desc: "Lower = more shots. Only affects Action/Hybrid." },
    { type: "number", key: "action_cooldown", title: "Action cooldown (seconds)", min: 1, max: 60 },
    { type: "toggle", key: "suppress_loading_screens", title: "Skip loading / menu screens" },
    { type: "toggle", key: "suppress_dark_frames", title: "Skip black / very dark frames" },
    { type: "toggle", key: "letterbox_suppression", title: "Skip letterboxed (cutscene) frames" },
    { type: "toggle", key: "dedupe_enabled", title: "Skip near-duplicate frames" },
    { type: "number", key: "dedupe_threshold", title: "Duplicate threshold", min: 1, max: 30,
      desc: "Higher = more aggressive de-duplication." },
    { type: "toggle", key: "precapture_buffer", title: "Pre-capture (save the frame before the change)" },
    { type: "toggle", key: "burst_enabled", title: "Time-lapse burst" },
    { type: "number", key: "burst_shots", title: "Burst shots", min: 1, max: 10 },
  ],
  Achievements: [
    { type: "toggle", key: "achievement_screenshots_enabled", title: "Capture on Steam achievement unlock" },
    { type: "number", key: "achievement_burst.shots", title: "Achievement burst shots", min: 1, max: 15 },
    { type: "number", key: "achievement_burst.delay", title: "Burst delay (seconds)", min: 0.3, max: 5, step: 0.1 },
    { type: "text", key: "steam_stats_folder", title: "Steam stats folder", browse: true,
      desc: "Leave blank to auto-detect (…/Steam/appcache/stats)." },
    { type: "toggle", key: "steam_hotkey_backup", title: "Also press Steam F12 (backup)" },
    { type: "toggle", key: "manual_hotkey_enabled", title: "Manual capture hotkey" },
    { type: "text", key: "manual_hotkey", title: "Hotkey (e.g. f9, ctrl+f9)" },
  ],
  Storage: [
    { type: "text", key: "screenshot_folder", title: "Screenshot folder", browse: true },
    { type: "number", key: "max_shots_per_game", title: "Max shots per game (0 = unlimited)", min: 0, max: 100000 },
    { type: "number", key: "max_disk_mb", title: "Max total disk (MB, 0 = unlimited)", min: 0, max: 1000000 },
    { type: "toggle", key: "watermark_enabled", title: "Watermark screenshots" },
    { type: "text", key: "watermark_text", title: "Watermark text", desc: "Use {game} and {date}." },
  ],
  Notifications: [
    { type: "toggle", key: "notifications_enabled", title: "Enable notifications" },
    { type: "toggle", key: "capture_toast", title: "Show a toast on each capture" },
    { type: "sound" },
  ],
  Window: [
    { type: "select", key: "theme", title: "Theme", options: [["dark", "Dark"], ["light", "Light"]], theme: true },
    { type: "toggle", key: "popup_on_game", title: "Show window when a game starts" },
    { type: "toggle", key: "minimise_to_tray", title: "Minimise to tray on close" },
    { type: "startup" },
  ],
  Privacy: [
    { type: "toggle", key: "privacy_guard_enabled", title: "Privacy guard",
      desc: "Pause capture when a sensitive app is focused." },
    { type: "text", key: "privacy_apps_csv", title: "Sensitive app keywords (comma separated)", csv: "privacy_apps" },
  ],
  Folders: [{ type: "gamefolders" }],
  Advanced: [
    { type: "toggle", key: "resolve_game_names", title: "Resolve friendly game names" },
    { type: "toggle", key: "debug_mode", title: "Debug mode (devtools)" },
    { type: "configio" },
    { type: "setupbtn" },
  ],
};
let activeSettingsTab = "Capture";
let MONITORS = [];

function buildSettingsTabs() {
  $("settingsTabs").innerHTML = Object.keys(SETTINGS_TABS).map(t =>
    `<button class="btn sm ${t === activeSettingsTab ? "primary" : ""}" onclick="setSettingsTab('${t}')">${t}</button>`).join("");
}
function setSettingsTab(t) { activeSettingsTab = t; buildSettingsTabs(); renderSettings(); }

function getKey(k) { return k.split(".").reduce((o, p) => (o || {})[p], SETTINGS); }
function setKey(k, v) {
  const parts = k.split("."); let o = SETTINGS;
  for (let i = 0; i < parts.length - 1; i++) { o[parts[i]] = o[parts[i]] || {}; o = o[parts[i]]; }
  o[parts[parts.length - 1]] = v;
}
async function saveSettings() { await post("/api/settings", SETTINGS); }

async function renderSettings() {
  SETTINGS = await api("/api/settings");
  if (!MONITORS.length) MONITORS = await api("/api/monitors");
  const items = SETTINGS_TABS[activeSettingsTab];
  $("settingsBody").innerHTML = `<div class="panel">` + items.map(renderField).join("") + `</div>`;
}

function renderField(f) {
  const row = (ctl, title, desc) =>
    `<div class="setting"><div class="info"><div class="t">${title}</div>${desc ? `<div class="d">${desc}</div>` : ""}</div>
      <div class="ctl">${ctl}</div></div>`;
  if (f.type === "toggle") {
    const v = getKey(f.key);
    return row(`<label class="toggle"><input type="checkbox" ${v ? "checked" : ""}
      onchange="onToggle('${f.key}', this.checked${f.theme ? ", true" : ""})"><span class="track"></span></label>`, f.title, f.desc);
  }
  if (f.type === "number") {
    let v = getKey(f.key); if (f.scale) v = v / f.scale;
    return row(`<input type="number" style="width:120px" value="${v}" min="${f.min ?? 0}" max="${f.max ?? 9e9}"
      step="${f.step || 1}" onchange="onNumber('${f.key}', this.value, ${f.scale || 0})">`, f.title, f.desc);
  }
  if (f.type === "text") {
    const v = f.csv ? (getKey(f.csv) || []).join(", ") : (getKey(f.key) || "");
    const browse = f.browse ? `<button class="btn sm" onclick="browseSetting('${f.key}')">${ic("folder")}</button>` : "";
    return row(`<input type="text" style="width:260px" value="${esc(v)}"
      onchange="onText('${f.key}', this.value, '${f.csv || ""}')">${browse}`, f.title, f.desc);
  }
  if (f.type === "select") {
    let opts = f.options || [];
    if (f.dynamic === "monitors") {
      opts = [["auto", "Auto (game's display)"], ["all", "All displays"]]
        .concat(MONITORS.filter(m => m.index > 0).map(m => [String(m.index), `${m.label} (${m.width}×${m.height})`]));
    }
    const v = getKey(f.key);
    return row(`<select onchange="onSelect('${f.key}', this.value${f.theme ? ", true" : ""})">` +
      opts.map(([val, lab]) => `<option value="${val}" ${String(v) === String(val) ? "selected" : ""}>${lab}</option>`).join("") +
      `</select>`, f.title, f.desc);
  }
  if (f.type === "sound") {
    return row(`<input type="file" accept="audio/*" onchange="uploadSound(this)">
      <button class="btn sm" onclick="testNotif()">Test</button>`, "Notification sound", "Upload mp3/wav/ogg.");
  }
  if (f.type === "startup") {
    return row(`<label class="toggle"><input type="checkbox" id="startupToggle" onchange="toggleStartup(this.checked)">
      <span class="track"></span></label>`, "Launch with Windows", "Start ShotTaker on login.") + initStartup();
  }
  if (f.type === "gamefolders") return gameFoldersUI();
  if (f.type === "configio") {
    return row(`<button class="btn sm" onclick="exportConfig()">Export</button>
      <button class="btn sm" onclick="importConfig()">Import</button>`, "Backup config", "Settings, folders, profiles & names.");
  }
  if (f.type === "setupbtn") return row(`<button class="btn sm" onclick="openSetup()">Re-run setup</button>`, "Setup wizard", "");
  return "";
}
function initStartup() { api("/api/startup/status").then(s => { const t = $("startupToggle"); if (t) t.checked = s.in_startup; }); return ""; }

async function onToggle(k, v, theme) { setKey(k, v); await saveSettings(); if (theme) applyTheme(v); }
async function onNumber(k, v, scale) { v = parseFloat(v); setKey(k, scale ? Math.round(v * scale) : v); await saveSettings(); }
async function onText(k, v, csv) { if (csv) setKey(csv, v.split(",").map(x => x.trim()).filter(Boolean)); else setKey(k, v); await saveSettings(); }
async function onSelect(k, v, theme) { setKey(k, v); await saveSettings(); if (theme) applyTheme(v); }
async function browseSetting(k) { const r = await post("/api/browse/folder"); if (r.success) { setKey(k, r.path); await saveSettings(); renderSettings(); } }
async function toggleStartup(on) { await post("/api/startup/" + (on ? "enable" : "disable")); toast("Startup updated", "ok"); }

async function uploadSound(input) {
  if (!input.files.length) return;
  const fd = new FormData(); fd.append("file", input.files[0]);
  const r = await (await fetch("/api/sound/upload", { method: "POST", body: fd })).json();
  toast(r.success ? "Sound uploaded" : "Upload failed", r.success ? "ok" : "err");
}
function testNotif() { toast("This is a test notification", "ok", "bell"); }
async function exportConfig() {
  const data = await api("/api/config/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = "shottaker_config.json"; a.click();
}
function importConfig() {
  const inp = document.createElement("input"); inp.type = "file"; inp.accept = ".json";
  inp.onchange = async () => {
    const text = await inp.files[0].text();
    await post("/api/config/import", JSON.parse(text));
    toast("Config imported", "ok"); SETTINGS = await api("/api/settings"); renderSettings();
  };
  inp.click();
}

/* ---------- game folders UI ---------- */
async function gameFoldersUI() {
  const folders = await api("/api/folders");
  let h = `<div class="row" style="margin-bottom:14px"><button class="btn sm primary" onclick="autodetectFolders()">${ic("search")} Scan my drives</button>
    <span class="muted">Point ShotTaker at the folders where each launcher installs games.</span></div>`;
  const platforms = ["steam", "epic", "gog", "ubisoft", "ea", "xbox", "battlenet", "riot", "rockstar", "itch", "extra"];
  for (const p of platforms) {
    const list = folders[p] || [];
    h += `<div style="margin-bottom:14px"><div class="row between"><b style="text-transform:capitalize">${p}</b>
      <button class="btn sm" onclick="addFolder('${p}')">+ Add folder</button></div>`;
    h += list.map(path => `<div class="list-row" style="margin-top:6px"><div class="grow sub">${esc(path)}</div>
      <button class="btn sm" onclick="openPath('${esc(path)}')">Open</button>
      <button class="btn sm danger" onclick="removeFolder('${p}','${esc(path)}')">${ic("close")}</button></div>`).join("");
  }
  $("settingsBody").innerHTML = `<div class="panel">${h}</div>`;
  return "";
}
async function addFolder(p) { const r = await post("/api/browse/folder"); if (r.success) { await post("/api/folders/add", { platform: p, path: r.path }); gameFoldersUI(); } }
async function removeFolder(p, path) { await post("/api/folders/remove", { platform: p, path }); gameFoldersUI(); }
async function openPath(p) { await post("/api/folders/open", { path: p }); }
async function autodetectFolders() {
  toast("Detecting…");
  const sel = {}; ["steam", "epic", "gog", "ubisoft", "ea", "xbox", "battlenet", "riot", "rockstar", "itch"].forEach(p => sel[p] = true);
  await post("/api/folders/autodetect", sel); gameFoldersUI(); toast("Auto-detect done", "ok");
}

/* ============================================================
   SETUP WIZARD
   ============================================================ */
const PLATFORMS = ["steam", "epic", "gog", "ubisoft", "ea", "xbox", "battlenet", "riot", "rockstar", "itch"];
let setupSel = new Set(["steam"]), setupMode = "hybrid";
function openSetup() {
  $("setupPlatforms").innerHTML = PLATFORMS.map(p =>
    `<label><input type="checkbox" ${setupSel.has(p) ? "checked" : ""} onchange="setupToggle('${p}',this.checked)">
     <span style="text-transform:capitalize">${p}</span></label>`).join("");
  const modes = [["timelapse", "clock", "Time Lapse", "A steady drip, every few minutes"],
    ["action", "burst", "Action Shots", "Fires when the action spikes"],
    ["hybrid", "hybrid", "Hybrid", "Why not both?"]];
  $("setupModes").innerHTML = modes.map(([v, i, t, d]) =>
    `<div class="mode-card ${v === setupMode ? "sel" : ""}" onclick="setupPickMode('${v}')">
      <div class="mi">${ic(i)}</div><div class="mt">${t}</div><div class="md">${d}</div></div>`).join("");
  openModal("setupOverlay");
}
function setupToggle(p, on) { on ? setupSel.add(p) : setupSel.delete(p); }
function setupPickMode(m) { setupMode = m; openSetup(); }
async function setupAutodetect() {
  $("setupDetectResult").textContent = "Scanning drives…";
  const sel = {}; setupSel.forEach(p => sel[p] = true);
  const r = await post("/api/folders/autodetect", sel);
  const total = Object.values(r.folders || {}).reduce((a, b) => a + b.length, 0);
  $("setupDetectResult").textContent = `Found ${total} game folder(s).`;
}
async function finishSetup() {
  const data = {
    capture_mode: setupMode,
    selected_platforms: [...setupSel],
    screenshot_folder: $("setupFolder").value,
  };
  await post("/api/setup/complete", data);
  closeModal("setupOverlay");
  SETTINGS = await api("/api/settings");
  toast("You're in. Game on.", "ok", "games");
  loadDashboard();
}
async function browseInto(id) { const r = await post("/api/browse/folder"); if (r.success) $(id).value = r.path; }

/* ============================================================
   UTIL
   ============================================================ */
function openModal(id) { $(id).classList.add("open"); }
function closeModal(id) { $(id).classList.remove("open"); }
function toast(msg, kind, iconName) {
  const el = document.createElement("div");
  el.className = "toast " + (kind || "");
  el.innerHTML = (iconName ? ic(iconName) + " " : "") + esc(msg);
  $("toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = 0; setTimeout(() => el.remove(), 300); }, 3200);
}
