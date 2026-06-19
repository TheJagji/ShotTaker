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
function getKey(k) { return k.split(".").reduce((o, p) => (o || {})[p], SETTINGS); }
function setKey(k, v) {
  const parts = k.split("."); let o = SETTINGS;
  for (let i = 0; i < parts.length - 1; i++) { o[parts[i]] = o[parts[i]] || {}; o = o[parts[i]]; }
  o[parts[parts.length - 1]] = v;
}
async function saveSettings() { await post("/api/settings", SETTINGS); }
let BRAND = {};
let lastCaptureTs = 0;

/* ---------- boot ---------- */
window.addEventListener("DOMContentLoaded", init);

async function init() {
  window.onerror = (msg, src, line, col, err) => {
    document.body.innerHTML = `<div style="padding:40px;color:#f87171;font-family:monospace;background:#0d0e13;min-height:100vh">
      <h2 style="margin-bottom:16px">ShotTaker — startup error</h2>
      <pre>${msg}\n${src}:${line}:${col}\n${err?.stack || ""}</pre>
    </div>`;
  };
  window.onunhandledrejection = (e) => {
    document.body.innerHTML = `<div style="padding:40px;color:#f87171;font-family:monospace;background:#0d0e13;min-height:100vh">
      <h2 style="margin-bottom:16px">ShotTaker — unhandled promise rejection</h2>
      <pre>${e.reason}</pre>
    </div>`;
  };
  BRAND = await api("/api/brand");
  applyBrand(BRAND);
  SETTINGS = await api("/api/settings");
  applyTheme(SETTINGS.theme || "dark");

  document.querySelectorAll("#nav button").forEach(b =>
    b.onclick = () => switchTab(b.dataset.tab, b));

  buildSettingsTabs();
  loadDashboard();
  refreshStatus();
  setInterval(refreshStatus, 4000);
  setTimeout(() => setInterval(pollCaptureToast, 4000), 2000);
  setInterval(() => { if (currentTab === "dashboard") loadDashboard(); }, 30000);

  const setup = await api("/api/setup/status");
  if (!setup.setup_complete) openSetup();

  // Only prevent right-click on gallery shots (handled per-element)
  // Don't block globally as it prevents F12/devtools access
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
const TITLES = { dashboard: "Dashboard", gallery: "Gallery", scanned: "Scanned Lists", games: "Scanned Lists", stats: "Stats", settings: "Settings" };
function switchTab(tab, btn) {
  currentTab = tab;
  document.querySelectorAll(".tabpage").forEach(p => p.classList.remove("active"));
  const page = $("page-" + tab);
  if (page) page.classList.add("active");
  document.querySelectorAll("#nav button").forEach(b => b.classList.remove("active"));
  (btn || document.querySelector(`#nav button[data-tab="${tab}"]`))?.classList.add("active");
  $("pageTitle").textContent = TITLES[tab] || tab;
  if (tab === "gallery") { loadGameFilter(); loadGallery(); }
  if (tab === "scanned" || tab === "games") loadScanned();
  if (tab === "stats") loadStats();
  if (tab === "settings") renderSettings();
}

/* ---------- status ---------- */
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("statusDot").classList.toggle("live", !!s.gameActive);
    // update page title status dot only
    // cloud popup: if game just closed and cloud folder is set and popup enabled
    if (!s.gameActive && window._lastGameActive && SETTINGS.cloud_folder && SETTINGS.cloud_popup_enabled) {
      triggerCloudPopup();
    }
    window._lastGameActive = !!s.gameActive;
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
  const sum = await api("/api/stats/summary");
  $("dashCards").innerHTML = [
    card("Games on deck", st.games || 0, true),
    card("Shots captured", stats.screenshots_taken || 0),
    card("Favorites", sum.favorites || 0),
    card("Hours sunk", fmtDur(sum.total_playtime_seconds || 0)),
    card("Sessions", sum.total_sessions || 0),
    card("Most played", sum.most_played_game || "—"),
  ].join("");

  // Mini stats — sparkline + top games
  const days = sum.captures_per_day || {};
  const vals = Object.values(days); const max = Math.max(1, ...vals);
  const gameColors = {};
  const gameList = Object.keys(sum.shots_by_game || {}).slice(0, 8);
  const palette = ["#7c5cff","#4ea8ff","#22d3ee","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c"];
  gameList.forEach((g, i) => { gameColors[g] = palette[i % palette.length]; });

  $("dashMiniStats").innerHTML = `
    <div class="row" style="align-items:flex-start;gap:18px">
      <div class="panel grow">
        <h3>Captures — last 30 days</h3>
        <div class="sub" style="margin-bottom:10px">Day by day</div>
        <div class="spark" id="dashSparkline"></div>
      </div>
      <div class="panel" style="min-width:220px">
        <h3>Top games</h3>
        <div id="dashTopGames" style="margin-top:10px"></div>
      </div>
    </div>`;

  $("dashSparkline").innerHTML = Object.entries(days).map(([d, v]) =>
    `<div class="sb" style="height:${(v/max)*100}%;background:var(--grad)" title="${d}: ${v}"></div>`
  ).join("") || `<div class="muted">No captures in the last 30 days.</div>`;

  $("dashTopGames").innerHTML = Object.entries(sum.shots_by_game || {}).slice(0,6).map(([g,v], i) =>
    `<div class="bar-row">
      <div class="bl" style="display:flex;align-items:center;gap:6px">
        <span style="width:10px;height:10px;border-radius:50%;background:${palette[i%palette.length]};flex-shrink:0;display:inline-block"></span>
        ${esc(g)}
      </div>
      <div class="bt"><div class="bf" style="width:${(v/Math.max(1,...Object.values(sum.shots_by_game||{})))*100}%;background:${palette[i%palette.length]}"></div></div>
      <div class="bv">${v}</div>
    </div>`).join("") || `<div class="muted">No data yet.</div>`;
}
function card(label, value, grad) {
  return `<div class="card"><div class="label">${label}</div>
    <div class="value ${grad ? "grad" : ""}">${esc(String(value))}</div></div>`;
}
async function loadLog() {
  // loadLog is deprecated on dashboard - log now lives in Feedback section
  // Keep for backward compat with old index.html that still has #log on dashboard
  const el = $("log");
  if (!el) return;
  const lines = await api("/api/log");
  el.innerHTML = lines.map(l => {
    let cls = "";
    if (l.toLowerCase().includes("error") || l.includes("failed")) cls = "err";
    else if (l.includes("[CAP]") || l.includes("[SHOT]")) cls = "cap";
    else if (l.includes("[ACT]")) cls = "act";
    else if (l.includes("[ACH]")) cls = "ach";
    return `<div class="line ${cls}">${esc(l)}</div>`;
  }).join("");
  el.style.display = "none"; // hide it even if old HTML has it
  el.closest(".panel")?.style.setProperty("display", "none");
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
    <div class="shot ${selected.has(it.path) ? "selected" : ""}" data-i="${i}"
      onclick="shotClick(event, ${i})"
      oncontextmenu="shotContextMenu(event, ${i})">
      ${selectMode ? "<input type=\"checkbox\" class=\"pick\" " + (selected.has(it.path) ? "checked" : "") + " onchange=\"toggleSelect('" + b64(it.path) + "', this)\" onclick=\"event.stopPropagation()\">": ""}
      <button class="fav ${it.favorite ? "on" : ""}" onclick="event.stopPropagation();favShot(${i})">${it.favorite ? ic("star-fill") : ic("star")}</button>
      <img class="thumb" loading="lazy" src="${it.thumb}" />
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
/* ---------- click to select + context menu ---------- */
function shotClick(e, i) {
  if (selectMode) {
    e.preventDefault();
    const it = galleryItems[i];
    const wasSelected = selected.has(it.path);
    wasSelected ? selected.delete(it.path) : selected.add(it.path);
    $("selCount").textContent = selected.size + " selected";
    const el = e.currentTarget;
    el.classList.toggle("selected", !wasSelected);
    const cb = el.querySelector(".pick");
    if (cb) cb.checked = !wasSelected;
  } else {
    openLightbox(i);
  }
}

function shotContextMenu(e, i) {
  e.preventDefault();
  const it = galleryItems[i];
  const cloudFolder = SETTINGS.cloud_folder || "";
  const menu = $("ctxMenu");
  menu.innerHTML = [
    `<div class="ctx-item" onclick="openLightbox(${i});hideCtx()">🔍 View</div>`,
    `<div class="ctx-item" onclick="ctxFav(${i})">⭐ ${it.favorite ? "Unfavorite" : "Favorite"}</div>`,
    `<div class="ctx-divider"></div>`,
    `<div class="ctx-item" onclick="ctxRate(${i},1)">★☆☆☆☆ Rate 1</div>`,
    `<div class="ctx-item" onclick="ctxRate(${i},2)">★★☆☆☆ Rate 2</div>`,
    `<div class="ctx-item" onclick="ctxRate(${i},3)">★★★☆☆ Rate 3</div>`,
    `<div class="ctx-item" onclick="ctxRate(${i},4)">★★★★☆ Rate 4</div>`,
    `<div class="ctx-item" onclick="ctxRate(${i},5)">★★★★★ Rate 5</div>`,
    `<div class="ctx-divider"></div>`,
    `<div class="ctx-item" onclick="ctxTag(${i})">🏷 Tag…</div>`,
    `<div class="ctx-item" onclick="ctxOpen(${i})">📂 Open file</div>`,
    cloudFolder
      ? `<div class="ctx-item" onclick="ctxSendToCloud(${i})">☁ Send to cloud folder</div>`
      : `<div class="ctx-item ctx-disabled">☁ Send to cloud folder (not set)</div>`,
    `<div class="ctx-divider"></div>`,
    `<div class="ctx-item ctx-danger" onclick="ctxDelete(${i})">🗑 Delete</div>`,
  ].join("");
  // Show first so we can measure height, then reposition
  menu.style.left = e.clientX + "px";
  menu.style.top = e.clientY + "px";
  menu.style.display = "block";
  const mw = menu.offsetWidth || 200;
  const mh = menu.offsetHeight || 300;
  const x = Math.min(e.clientX, window.innerWidth - mw - 8);
  const y = Math.min(e.clientY, window.innerHeight - mh - 8);
  menu.style.left = x + "px";
  menu.style.top = y + "px";
  setTimeout(() => document.addEventListener("click", hideCtx, { once: true }), 0);
}
function hideCtx() {
  const m = $("ctxMenu");
  if (m) m.style.display = "none";
}
async function ctxFav(i) { hideCtx(); await favShot(i); }
async function ctxRate(i, n) {
  hideCtx();
  const it = galleryItems[i];
  const r = await post("/api/gallery/rate", { path: it.path, rating: n });
  it.rating = r.rating;
  renderGallery({ items: galleryItems, pages: 1, page: galleryPage });
}
async function ctxTag(i) { hideCtx(); lbIndex = i; await lbTag(); }
async function ctxOpen(i) { hideCtx(); await post("/api/gallery/open", { path: galleryItems[i].path }); }
async function ctxDelete(i) {
  hideCtx();
  if (!confirm("Delete this screenshot?")) return;
  await post("/api/gallery/delete", { path: galleryItems[i].path });
  toast("Deleted", "ok"); loadGallery();
}
async function ctxSendToCloud(i) {
  hideCtx();
  const it = galleryItems[i];
  const r = await post("/api/cloud/copy", { paths: [it.path] });
  toast(r.success ? "Copied to cloud folder" : "Failed: " + r.error, r.success ? "ok" : "err");
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
  const lb = $("lightbox");
  if (!lb || !lb.classList.contains("open")) return;
  if (e.key === "Escape") closeLightbox();
  if (e.key === "ArrowLeft") lbNav(-1);
  if (e.key === "ArrowRight") lbNav(1);
});

/* ============================================================
   SCANNED LISTS  (Games + Blacklist)
   ============================================================ */
let GAMES = {};
let activeScannedTab = "games";

function switchScannedTab(tab) {
  activeScannedTab = tab;
  $("scannedTabGames").classList.toggle("primary", tab === "games");
  $("scannedTabBlacklist").classList.toggle("primary", tab === "blacklist");
  $("scannedTabGames").classList.toggle("btn", true);
  $("scannedTabBlacklist").classList.toggle("btn", true);
  if (tab === "games") renderScannedGames();
  else renderScannedBlacklist();
}

async function loadScanned() {
  const d = await api("/api/games");
  GAMES = d.games || {}; NAMES = d.names || {};
  if (activeScannedTab === "games") renderScannedGames();
  else renderScannedBlacklist();
}

function renderScannedGames() {
  const useScannedBody = !!$("scannedBody");
  if (useScannedBody) {
    // New index.html — render toolbar + list into scannedBody
    const platforms = [...new Set(Object.values(GAMES))];
    const toolbar = `<div class="gallery-toolbar" style="margin-bottom:14px">
      <input type="search" id="gamesSearch" placeholder="Search games…" oninput="filterScannedGames()" style="min-width:200px" />
      <select id="gamesPlatform" onchange="filterScannedGames()"><option value="">All platforms</option>${
        platforms.map(p => "<option>" + p + "</option>").join("")
      }</select>
      <span class="grow"></span>
      <span class="muted" id="gamesCount"></span>
      <button class="btn sm" onclick="triggerScan()"><svg class="ic"><use href="#i-target"/></svg> Rescan</button>
    </div>`;
    $("scannedBody").innerHTML = toolbar + `<div id="gamesList"></div>`;
  } else {
    // Old index.html — platform dropdown already in HTML, just populate it
    const platforms = [...new Set(Object.values(GAMES))];
    const platEl = $("gamesPlatform");
    if (platEl) platEl.innerHTML = `<option value="">All platforms</option>` +
      platforms.map(p => `<option>${p}</option>`).join("");
  }
  filterScannedGames();
}

function filterScannedGames() {
  const q = ($("gamesSearch")?.value || "").toLowerCase();
  const plat = $("gamesPlatform")?.value || "";
  const rows = Object.entries(GAMES).filter(([exe, p]) =>
    (!plat || p === plat) && (exe.includes(q) || nameOf(exe).toLowerCase().includes(q)));
  $("gamesCount").textContent = `${rows.length} of ${Object.keys(GAMES).length} games`;
  $("gamesList").innerHTML = rows.map(([exe, p]) => {
    const steamIcon = p === "steam"
      ? `<img data-src="/api/game/icon/${encodeURIComponent(exe)}" src="" style="width:24px;height:24px;border-radius:4px;object-fit:cover;flex-shrink:0;background:var(--raised)" class="game-icon-lazy" onerror="this.style.display='none'" />`
      : `<span style="width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;color:var(--muted)">${ic("games")}</span>`;
    return `<div class="list-row">
      ${steamIcon}
      <div class="grow"><div class="name">${esc(nameOf(exe))}</div>
        <div class="sub">${esc(exe)}</div></div>
      <span class="chip ${p}">${p}</span>
      <button class="btn sm" onclick="renameGameName('${esc(exe)}')">Rename</button>
      <button class="btn sm" onclick="disableGame('${esc(exe)}')">Hide</button>
      <button class="btn sm danger" onclick="blacklistGame('${esc(exe)}')">Blacklist</button>
    </div>`;
  }).join("") || `<div class="empty"><div class="big">${ic("games")}</div>No games found yet. Point ShotTaker at your libraries in Settings → Folders.</div>`;
  // Load icons lazily to avoid hammering Flask with 100+ simultaneous requests
  setTimeout(loadLazyIcons, 50);
}

function loadLazyIcons() {
  const imgs = document.querySelectorAll("img.game-icon-lazy[data-src]");
  let delay = 0;
  imgs.forEach(img => {
    setTimeout(() => {
      if (img.dataset.src) {
        img.src = img.dataset.src;
        delete img.dataset.src;
      }
    }, delay);
    delay += 30; // 30ms between each request = ~3 seconds for 100 icons
  });
}

async function renderScannedBlacklist() {
  const list = await api("/api/blacklist");
  let h = `<div class="row between" style="margin-bottom:14px">
    <span class="muted">Processes ShotTaker will never treat as a game.</span>
    <button class="btn sm primary" onclick="blacklistAddFromScanned()">+ Add entry</button>
  </div>`;
  if (!list.length) {
    h += `<div class="empty"><div class="big">${ic("close")}</div>Your blacklist is empty.</div>`;
  } else {
    h += list.map(exe => `
      <div class="list-row">
        <div class="grow"><div class="name">${esc(exe)}</div></div>
        <button class="btn sm" onclick="blacklistRestoreFromScanned('${esc(exe)}')">Restore</button>
        <button class="btn sm danger" onclick="blacklistRemoveFromScanned('${esc(exe)}')">Remove</button>
      </div>`).join("");
  }
  $("scannedBody").innerHTML = `<div class="panel">${h}</div>`;
}
async function blacklistAddFromScanned() {
  const exe = prompt("Executable to blacklist (e.g. mygame.exe):");
  if (!exe?.trim()) return;
  await post("/api/blacklist/add", { exe: exe.trim() });
  toast("Blacklisted", "ok"); renderScannedBlacklist();
}
async function blacklistRestoreFromScanned(exe) {
  await post("/api/blacklist/move_to_games", { exe });
  toast(esc(exe) + " restored", "ok");
  const d = await api("/api/games");
  GAMES = d.games || {}; NAMES = d.names || {};
  renderScannedBlacklist();
}
async function blacklistRemoveFromScanned(exe) {
  if (!confirm("Remove " + exe + " from blacklist?")) return;
  await post("/api/blacklist/remove", { exe });
  toast("Removed", "ok"); renderScannedBlacklist();
}
async function renameGameName(exe) {
  const n = prompt("Friendly name for " + exe + ":", nameOf(exe));
  if (n === null) return;
  await post("/api/names/set", { exe, name: n });
  loadScanned(); toast("Name saved", "ok");
}
async function disableGame(exe) { await post("/api/games/disable", { exe }); toast("Hidden"); loadScanned(); }
async function blacklistGame(exe) { await post("/api/blacklist/add", { exe }); toast("Blacklisted"); loadScanned(); }
async function triggerScan() { toast("Scanning…"); await api("/api/scan/games"); loadScanned(); toast("Scan complete", "ok"); }

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
  const sparkPalette = ["#7c5cff","#4ea8ff","#22d3ee","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c"];
  const sparkGames = Object.keys(s.shots_by_game || {}).slice(0, 8);
  $("sparkline").innerHTML = Object.entries(days).map(([d, v], i) => {
    const col = sparkGames.length ? sparkPalette[i % sparkPalette.length] : "var(--primary)";
    return `<div class="sb" style="height:${(v/max)*100}%;background:${col}" title="${d}: ${v}"></div>`;
  }).join("") || `<div class="muted">No captures in the last 30 days.</div>`;
  $("shotsByGame").innerHTML = bars(s.shots_by_game);
  $("playtimeByGame").innerHTML = bars(s.playtime_by_game, fmtDur);
  if ($("shotsByType")) $("shotsByType").innerHTML = bars(s.shots_by_type);
  if ($("sessionsByGame")) $("sessionsByGame").innerHTML = bars(s.sessions_by_game);
  $("recentSessions").innerHTML = (s.recent_sessions || []).slice().reverse().map(x =>
    `<div class="list-row"><div class="grow"><div class="name">${esc(nameOf(x.game))}</div>
      <div class="sub">${x.timestamp} · ${fmtDur(x.duration)} · ${x.shots} shots</div></div>
      <span class="chip ${x.platform || ""}">${x.platform || ""}</span></div>`).join("")
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
// Settings grouped into Shot Settings / App Settings / Dev Info
const SETTINGS_GROUPS = {
  "Shot Settings": ["Capture", "Quality", "Achievements", "Storage", "Folders"],
  "App Settings":  ["Notifications", "Window", "Privacy", "Advanced"],
  "Dev Info":      ["Feedback", "About"],
};
const SETTINGS_TABS = {
  // Shot Settings
  Capture: [
    { type: "select", key: "capture_mode", title: "Capture mode",
      desc: "Time Lapse = on a timer · Action = on screen change · Hybrid = both",
      options: [["timelapse", "Time Lapse"], ["action", "Action Shots"], ["hybrid", "Hybrid"]] },
    { type: "slider", key: "sensitivity", title: "Action sensitivity", min: 5, max: 100, step: 1,
      desc: "How much the screen needs to change before an Action Shot fires. Lower = triggers more often, higher = only big scene changes. Only affects Action / Hybrid." },
    { type: "number", key: "action_cooldown", title: "Action cooldown (seconds)", min: 1, max: 60,
      desc: "Minimum gap between Action Shots." },
    { type: "number", key: "interval", title: "Time-lapse interval (seconds)", min: 5, max: 7200, scale: 1000 },
    { type: "number", key: "first_delay", title: "First-shot delay (seconds)", min: 0, max: 120 },
    { type: "select", key: "monitor", title: "Monitor", dynamic: "monitors" },
    { type: "select", key: "screenshot_format", title: "Format",
      options: [["png", "PNG (lossless)"], ["jpeg", "JPEG"], ["webp", "WebP (smallest)"]] },
    { type: "number", key: "jpeg_quality", title: "JPEG quality", min: 50, max: 100 },
    { type: "number", key: "webp_quality", title: "WebP quality", min: 50, max: 100 },
    { type: "toggle", key: "per_game_folders", title: "Per-game folders" },
  ],
  Quality: [
    { type: "toggle", key: "suppress_loading_screens", title: "Skip loading / menu screens" },
    { type: "toggle", key: "suppress_dark_frames", title: "Skip black / very dark frames" },
    { type: "toggle", key: "letterbox_suppression", title: "Skip letterboxed (cutscene) frames" },
    { type: "toggle", key: "dedupe_enabled", title: "Skip near-duplicate frames" },
    { type: "number", key: "dedupe_threshold", title: "Duplicate threshold", min: 1, max: 30,
      desc: "Higher = more aggressive de-duplication." },
    { type: "number", key: "capture_scale", title: "Resolution scale (%)", min: 25, max: 100,
      desc: "Downscale to save space. 100 = native." },
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
    { type: "text", key: "cloud_folder", title: "Cloud folder (optional)", browse: true,
      desc: "Point to your Dropbox / OneDrive / Google Drive sync folder. Leave blank to disable." },
    { type: "toggle", key: "cloud_popup_enabled", title: "Show upload picker after each session",
      desc: "After a game closes, lets you pick which screenshots to copy to your cloud folder." },
    { type: "number", key: "max_shots_per_game", title: "Max shots per game (0 = unlimited)", min: 0, max: 100000 },
    { type: "number", key: "max_disk_mb", title: "Max total disk (MB, 0 = unlimited)", min: 0, max: 1000000 },
    { type: "toggle", key: "watermark_enabled", title: "Watermark screenshots" },
    { type: "text", key: "watermark_text", title: "Watermark text", desc: "Use {game} and {date}." },
  ],
  Folders: [{ type: "gamefolders" }],
  // App Settings
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
  Advanced: [
    { type: "toggle", key: "resolve_game_names", title: "Resolve friendly game names" },
    { type: "toggle", key: "debug_mode", title: "Debug mode (devtools)" },
    { type: "toggle", key: "force_mss", title: "Use standard capture engine (mss)",
      desc: "Switch from the Rust/DXGI engine back to the standard mss capture. Requires restart." },
    { type: "configio" },
    { type: "setupbtn" },
  ],
  // Dev Info
  Feedback: [{ type: "feedback" }],
  About: [{ type: "about" }],
};
let activeSettingsTab = "Capture";
let activeSettingsGroup = "Shot Settings";
let MONITORS = [];

function buildSettingsTabs() {
  // Group selector (only if element exists — new index.html)
  const groupEl = $("settingsGroups");
  if (groupEl) {
    groupEl.innerHTML = Object.keys(SETTINGS_GROUPS).map(g =>
      `<button class="btn sm ${g === activeSettingsGroup ? "primary" : ""}"
        onclick="switchSettingsGroup('${g}')">${g}</button>`).join("");
  }
  // Tab selector for current group
  const tabs = SETTINGS_GROUPS[activeSettingsGroup] || Object.values(SETTINGS_GROUPS)[0];
  const tabEl = $("settingsTabs");
  if (tabEl) {
    tabEl.innerHTML = tabs.map(t =>
      `<button class="btn sm ${t === activeSettingsTab ? "primary" : ""}"
        onclick="setSettingsTab('${t}')">${t}</button>`).join("");
  }
}
function switchSettingsGroup(g) {
  activeSettingsGroup = g;
  activeSettingsTab = SETTINGS_GROUPS[g][0];
  buildSettingsTabs();
  // Clear body immediately so old content doesn't flash
  const body = $("settingsBody");
  if (body) body.innerHTML = "";
  renderSettings();
}
function setSettingsTab(t) {
  activeSettingsTab = t;
  buildSettingsTabs();
  const body = $("settingsBody");
  if (body) body.innerHTML = "";
  renderSettings();
}

async function renderSettings() {
  SETTINGS = await api("/api/settings");
  if (!MONITORS.length) MONITORS = await api("/api/monitors");
  const items = SETTINGS_TABS[activeSettingsTab];
  if (!items) return;
  // Always clear first so stale content never persists
  const body = $("settingsBody");
  if (body) body.innerHTML = "";
  const fullPage = items.length === 1 && ["blacklistmgr", "about", "feedback"].includes(items[0].type);
  if (fullPage) {
    renderField(items[0]);
  } else {
    if (body) body.innerHTML = `<div class="panel">` + items.map(renderField).join("") + `</div>`;
  }
}

function renderField(f) {
  try {
  const row = (ctl, title, desc) =>
    `<div class="setting"><div class="info"><div class="t">${title}</div>${desc ? "<div class=\"d\">" + desc + "</div>" : ""}</div>
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
        .concat((MONITORS || []).map((m, i) => {
          const label = m.label || (m.primary ? "Primary" : `Display ${m.index + 1}`);
          return [String(m.index + 1), `${label} (${m.width}×${m.height})`];
        }));
    }
    const v = getKey(f.key);
    return row(`<select onchange="onSelect('${f.key}', this.value${f.theme ? ", true" : ""})">` +
      opts.map(([val, lab]) => `<option value="${val}" ${String(v) === String(val) ? "selected" : ""}>${lab}</option>`).join("") +
      `</select>`, f.title, f.desc);
  }
  if (f.type === "slider") {
    const v = getKey(f.key);
    const id = "slider_" + f.key.replace(".", "_");
    return row(`<div style="display:flex;align-items:center;gap:10px">
      <input type="range" id="${id}" min="${f.min ?? 0}" max="${f.max ?? 100}" step="${f.step || 1}" value="${v}"
        style="width:180px" oninput="onSlider('${f.key}', this.value, '${id}_val')"
        onchange="onSliderCommit('${f.key}', this.value, '${id}_val')">
      <span id="${id}_val" style="min-width:32px;text-align:right;font-variant-numeric:tabular-nums">${v}</span>
    </div>`, f.title, f.desc);
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
  if (f.type === "blacklistmgr") return blacklistMgrUI();
  if (f.type === "about") return aboutUI();
  if (f.type === "feedback") return feedbackUI();
  return "";
  } catch(e) {
    console.error("renderField error for type", f.type, "key", f.key, e);
    return `<div class="setting"><div class="info"><div class="t" style="color:var(--danger)">Error rendering: ${f.type} / ${f.key || ""}</div></div></div>`;
  }
}
function initStartup() { api("/api/startup/status").then(s => { const t = $("startupToggle"); if (t) t.checked = s.in_startup; }); return ""; }

async function onToggle(k, v, theme) { setKey(k, v); await saveSettings(); if (theme) applyTheme(v); }
async function onNumber(k, v, scale) { v = parseFloat(v); setKey(k, scale ? Math.round(v * scale) : v); await saveSettings(); }
async function onText(k, v, csv) { if (csv) setKey(csv, v.split(",").map(x => x.trim()).filter(Boolean)); else setKey(k, v); await saveSettings(); }
async function onSelect(k, v, theme) { setKey(k, v); await saveSettings(); if (theme) applyTheme(v); }
function onSlider(k, v, labelId) { const el = $(labelId); if (el) el.textContent = v; }
async function onSliderCommit(k, v, labelId) { setKey(k, parseFloat(v)); await saveSettings(); }
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

/* ---------- blacklist manager ---------- */
async function blacklistMgrUI() {
  const list = await api("/api/blacklist");
  let h = `<div class="row between" style="margin-bottom:14px">
    <span class="muted">Your custom blacklist — processes ShotTaker will never treat as a game.</span>
    <button class="btn sm primary" onclick="blacklistAdd()">+ Add entry</button>
  </div>`;
  if (!list.length) {
    h += `<div class="empty"><div class="big">${ic("close")}</div>Your blacklist is empty. Use the Blacklist button on the Games page to add entries.</div>`;
  } else {
    h += list.map(exe => `
      <div class="list-row">
        <div class="grow"><div class="name">${esc(exe)}</div></div>
        <button class="btn sm" onclick="blacklistRestore('${esc(exe)}')">Restore</button>
        <button class="btn sm danger" onclick="blacklistDelete('${esc(exe)}')">Remove</button>
      </div>`).join("");
  }
  $("settingsBody").innerHTML = `<div class="panel">${h}</div>`;
  return "";
}
async function blacklistAdd() {
  const exe = prompt("Executable name to blacklist (e.g. mygame.exe):");
  if (!exe || !exe.trim()) return;
  await post("/api/blacklist/add", { exe: exe.trim() });
  toast("Blacklisted", "ok");
  blacklistMgrUI();
}
async function blacklistRestore(exe) {
  await post("/api/blacklist/move_to_games", { exe });
  toast(esc(exe) + " restored — rescanning…", "ok");
  blacklistMgrUI();
}
async function blacklistDelete(exe) {
  if (!confirm("Remove " + exe + " from your blacklist?\n\nIt will not be restored to the game list — use Restore for that.")) return;
  await post("/api/blacklist/remove", { exe });
  toast("Removed from blacklist", "ok");
  blacklistMgrUI();
}

/* ---------- about ---------- */
function aboutUI() {
  const b = BRAND;
  $("settingsBody").innerHTML = `<div class="panel" style="text-align:center;padding:40px 20px">
    <img src="/static/icon.png" style="width:72px;height:72px;border-radius:18px;box-shadow:var(--shadow);margin-bottom:18px" alt="${esc(b.name)}" />
    <div style="font-size:26px;font-weight:700;background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px">${esc(b.name)}</div>
    <div id="aboutSysInfo" style="margin-bottom:20px"></div>
    <div id="aboutText" style="white-space:pre-wrap;text-align:left;color:var(--text);line-height:1.7;margin-bottom:16px"></div>
    `;
  api("/api/sysinfo").then(info => {
    const el = $("aboutSysInfo");
    if (!el) return;
    el.innerHTML = Object.entries(info).map(([k, v]) =>
      `<div class="setting" style="justify-content:center;gap:24px;border-bottom:none;padding:5px 0">
        <span style="color:var(--muted);font-size:12.5px">${esc(k)}</span>
        <span style="font-weight:550">${esc(String(v))}</span>
      </div>`).join("");
  });
  api("/api/about").then(r => {
    const el = $("aboutText");
    if (el) el.textContent = r.text || "";
  });
  return "";
}
async function aboutEdit() {
  const r = await api("/api/about");
  const area = $("aboutEditArea");
  if (area) area.value = r.text || "";
  const panel = $("aboutEditPanel");
  if (panel) panel.style.display = "";
}
function aboutCancelEdit() {
  const panel = $("aboutEditPanel");
  if (panel) panel.style.display = "none";
}
async function aboutSave() {
  const area = $("aboutEditArea");
  if (!area) return;
  await post("/api/about", { text: area.value });
  const el = $("aboutText");
  if (el) el.textContent = area.value;
  aboutCancelEdit();
  toast("About saved", "ok");
}

/* ---------- feedback ---------- */
// FEEDBACK_EMAIL — replace with your support email address when ready
const FEEDBACK_EMAIL = "YOUR_EMAIL_HERE";

function feedbackUI() {
  const el = $("settingsBody");
  el.innerHTML = `
    <div class="panel">
      <h3 style="margin-bottom:4px">Send Feedback</h3>
      <p class="sub">Bug report, feature request, or anything else — we read it all.</p>
      <div class="field">
        <label>Type</label>
        <select id="fbType">
          <option value="bug">Bug report</option>
          <option value="feature">Feature request</option>
          <option value="other">Other</option>
        </select>
      </div>
      <div class="field">
        <label>Message</label>
        <textarea id="fbMessage" style="width:100%;height:160px;resize:vertical" placeholder="Describe the issue or idea…"></textarea>
      </div>
      <div class="field">
        <label style="display:flex;align-items:center;gap:8px">
          <input type="checkbox" id="fbAttachLog" checked />
          Attach detection log
        </label>
      </div>
      <div class="row between" style="margin-top:8px">
        <button class="btn sm ghost" onclick="fbCopyLog()">📋 Copy log to clipboard</button>
        <button class="btn primary" onclick="fbSend()">Send feedback</button>
      </div>
    </div>
    <div class="panel" style="margin-top:0">
      <h3 style="margin-bottom:4px">Detection Log</h3>
      <div class="row between" style="margin-bottom:10px">
        <span class="muted" style="font-size:12.5px">Recent console output</span>
        <div style="display:flex;gap:6px">
          <button class="btn sm" onclick="fbRefreshLog()">Refresh</button>
          <button class="btn sm" onclick="fbCopyLog()">Copy</button>
        </div>
      </div>
      <div class="log" id="fbLog"></div>
    </div>
    <div class="panel" style="margin-top:0">
      <h3 style="margin-bottom:4px">Debug Mode</h3>
      <div class="setting">
        <div class="info"><div class="t">Enable debug mode</div>
          <div class="d">Opens browser devtools in the app window. Requires restart.</div></div>
        <div class="ctl"><label class="toggle"><input type="checkbox" id="fbDebugToggle"
          ${SETTINGS.debug_mode ? "checked" : ""} onchange="onToggle('debug_mode', this.checked)">
          <span class="track"></span></label></div>
      </div>
    </div>`;
  fbRefreshLog();
  return "";
}
async function fbRefreshLog() {
  const lines = await api("/api/log");
  const el = $("fbLog");
  if (!el) return;
  el.innerHTML = lines.map(l => {
    let cls = "";
    if (l.toLowerCase().includes("error") || l.includes("failed")) cls = "err";
    else if (l.includes("[CAP]") || l.includes("[SHOT]")) cls = "cap";
    else if (l.includes("[ACT]")) cls = "act";
    else if (l.includes("[ACH]")) cls = "ach";
    return `<div class="line ${cls}">${esc(l)}</div>`;
  }).join("");
  el.scrollTop = el.scrollHeight;
}
async function fbCopyLog() {
  const lines = await api("/api/log");
  navigator.clipboard.writeText(lines.join("\n")).then(() => toast("Log copied to clipboard", "ok"));
}
async function fbSend() {
  const type = $("fbType")?.value || "other";
  const msg = $("fbMessage")?.value?.trim();
  if (!msg) return toast("Please write a message first", "err");
  const attachLog = $("fbAttachLog")?.checked;
  let body = `Type: ${type}\n\nMessage:\n${msg}`;
  if (attachLog) {
    const lines = await api("/api/log");
    body += "\n\n--- Detection Log ---\n" + lines.join("\n");
  }
  const subject = encodeURIComponent(`ShotTaker Feedback: ${type}`);
  const bodyEnc = encodeURIComponent(body);
  const email = FEEDBACK_EMAIL;
  if (email === "YOUR_EMAIL_HERE") {
    toast("Feedback email not configured yet", "err");
    return;
  }
  window.location.href = "mailto:" + email + "?subject=" + subject + "&body=" + bodyEnc;
}

/* ---------- cloud copy ---------- */
async function openCloudPopup(paths) {
  const cloudFolder = SETTINGS.cloud_folder || "";
  if (!cloudFolder) return;
  openModal("cloudOverlay");
  $("cloudModalSub").textContent = `Select screenshots to copy to ${cloudFolder}`;
  const grid = $("cloudPickerGrid");
  const items = paths.map((p, i) => ({ path: p, selected: true, idx: i }));
  grid.innerHTML = items.map((it, i) => `
    <div style="position:relative;cursor:pointer" onclick="toggleCloudItem(this,${i})" data-selected="1">
      <img src="/api/gallery/thumb/${btoa(it.path)}" style="width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;border:2px solid var(--primary)" />
      <div style="position:absolute;top:4px;right:4px;background:var(--primary);color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:12px" class="cloud-check">✓</div>
    </div>`).join("");
  grid._paths = paths;
}
function toggleCloudItem(el, i) {
  const sel = el.dataset.selected === "1";
  el.dataset.selected = sel ? "0" : "1";
  el.querySelector("img").style.borderColor = sel ? "var(--border)" : "var(--primary)";
  el.querySelector(".cloud-check").style.display = sel ? "none" : "flex";
}
async function doCloudCopy() {
  const grid = $("cloudPickerGrid");
  const paths = [...grid.querySelectorAll("[data-selected='1']")].map((el, i) => grid._paths[i]);
  if (!paths.length) return toast("Nothing selected", "err");
  const r = await post("/api/cloud/copy", { paths });
  closeModal("cloudOverlay");
  toast(r.success ? `Copied ${paths.length} screenshot(s) to cloud folder` : "Failed: " + r.error, r.success ? "ok" : "err");
}

async function triggerCloudPopup() {
  // get last session screenshots
  try {
    const data = await api("/api/gallery/session?page=1&per_page=100");
    const paths = (data.items || []).map(it => it.path);
    if (paths.length) openCloudPopup(paths);
  } catch(e) {}
}

/* ============================================================
   SETUP WIZARD
   ============================================================ */
const PLATFORMS = ["steam", "epic", "gog", "ubisoft", "ea", "xbox", "battlenet", "riot", "rockstar", "itch"];
let setupSel = new Set(["steam"]), setupMode = "hybrid", setupEngine = "rust";
function openSetup() {
  // Engine picker
  const engineEl = $("setupEngine");
  if (engineEl) {
    engineEl.innerHTML = [
      ["rust", "⚡ Rust / DXGI", "GPU-accelerated capture. Lower CPU usage, faster grabs. Requires the Rust extension to be built. Recommended.", true],
      ["mss", "🐍 Standard (mss)", "Pure Python capture. Works everywhere Python does. No extra build step needed.", false],
    ].map(([v, title, desc, rec]) => `
      <div class="mode-card ${setupEngine === v ? "sel" : ""}" onclick="setupPickEngine('${v}')" style="text-align:left;padding:16px">
        <div class="mt" style="font-size:15px">${title}${rec ? " <span style='color:var(--success);font-size:11px;font-weight:600'>RECOMMENDED</span>" : ""}</div>
        <div class="md" style="margin-top:6px;line-height:1.5">${desc}</div>
      </div>`).join("");
  }
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
function setupPickEngine(e) { setupEngine = e; openSetup(); }
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
    force_mss: setupEngine === "mss",
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
