// =========================
// WIZARD STATE
// =========================
const WIZARD_TOTAL_STEPS = 13;
let wizardStepList = [];
let wizardCurrentIndex = 0;

const PLATFORMS = {
    steam:   { label: "Steam",   cls: "steam-label" },
    gog:     { label: "GOG",     cls: "gog-label" },
    epic:    { label: "Epic",    cls: "epic-label" },
    ubisoft: { label: "Ubisoft", cls: "ubisoft-label" },
    ea:      { label: "EA",      cls: "ea-label" }
};

const PLATFORM_STEPS = ["steam", "gog", "epic", "ubisoft", "ea"];

const FIXED_STEPS = [
    "welcome", "platforms", "capturemode", "shotfolder",
    "notifications", "window", "gamefolders", "steamstats", "done"
];

// =========================
// STARTUP
// =========================
fetch("/api/setup/status")
    .then(r => r.json())
    .then(d => { if (!d.setup_complete) showWizard(); else showApp(); })
    .catch(() => showApp());

function showWizard() {
    document.getElementById("wizardOverlay").style.display = "flex";
    document.getElementById("mainApp").style.display = "none";
    buildStepList();
    wizardCurrentIndex = 0;
    renderWizardStep();
    fetch("/api/settings").then(r => r.json()).then(prefillWizard).catch(() => {});
}

function showApp() {
    document.getElementById("wizardOverlay").style.display = "none";
    document.getElementById("mainApp").style.display = "block";
    const header = document.getElementById("mainHeader");
    if (header) header.style.display = "";
    refreshAll();
}

// =========================
// WIZARD STEP LIST
// =========================
function buildStepList() {
    const mode = document.querySelector('input[name="capture_mode"]:checked')?.value || "timelapse";
    const steps = ["welcome", "platforms", "capturemode", "shotfolder"];

    if (mode === "timelapse" || mode === "hybrid") steps.push("interval");
    if (mode === "action" || mode === "hybrid")    steps.push("actionshots");

    steps.push("achievements", "notifications", "window", "gamefolders", "steamstats", "done");
    wizardStepList = steps;
}

function getSelectedPlatforms() {
    return PLATFORM_STEPS.filter(p => document.getElementById("use_" + p)?.checked);
}

// =========================
// WIZARD NAVIGATION
// =========================
function renderWizardStep() {
    buildStepList();
    const stepId = wizardStepList[wizardCurrentIndex];
    const total  = wizardStepList.length;

    document.querySelectorAll(".wizard-step").forEach(el => el.classList.remove("active"));
    const cur = document.getElementById("wstep-" + stepId);
    if (cur) cur.classList.add("active");

    const pct = total > 1 ? (wizardCurrentIndex / (total - 1)) * 100 : 0;
    document.getElementById("wizardProgressBar").style.width = pct + "%";
    document.getElementById("wizardStepLabel").innerText = `Step ${wizardCurrentIndex + 1} of ${total}`;

    document.getElementById("wizBtnBack").style.display = wizardCurrentIndex > 0 ? "inline-block" : "none";
    const isLast = wizardCurrentIndex === total - 1;
    document.getElementById("wizBtnNext").style.display   = isLast ? "none" : "inline-block";
    document.getElementById("wizBtnFinish").style.display = isLast ? "inline-block" : "none";

    if (stepId === "gamefolders") wizAutoScanFolders();
    if (isLast) buildWizardSummary();
}

function wizardNext() {
    if (wizardCurrentIndex < wizardStepList.length - 1) {
        wizardCurrentIndex++;
        renderWizardStep();
    }
}

function wizardBack() {
    if (wizardCurrentIndex > 0) {
        wizardCurrentIndex--;
        renderWizardStep();
    }
}

document.addEventListener("change", function(e) {
    if (e.target.name === "capture_mode") buildStepList();
});

// =========================
// WIZARD SUMMARY
// =========================
function buildWizardSummary() {
    const mode = document.querySelector('input[name="capture_mode"]:checked')?.value || "timelapse";
    const modeLabels = { timelapse: "⏱ Time Lapse", action: "⚡ Action Shots", hybrid: "🔀 Hybrid" };
    const folder = document.getElementById("wiz_screenshot_folder")?.value || "Not set";
    const perGame = document.getElementById("wiz_per_game")?.checked;
    const achEnabled = document.getElementById("wiz_achievement_enabled")?.checked;
    const notifEnabled = document.querySelector('input[name="notif_enabled"]:checked')?.value === "yes";

    const html = `
        <table class="summary-table">
            <tr><td><strong>Capture mode</strong></td><td>${modeLabels[mode]}</td></tr>
            <tr><td><strong>Screenshot folder</strong></td><td class="path-cell">${folder}</td></tr>
            <tr><td><strong>Organise by game</strong></td><td>${perGame ? "Yes" : "No"}</td></tr>
            <tr><td><strong>Achievement screenshots</strong></td><td>${achEnabled ? "Enabled" : "Disabled"}</td></tr>
            <tr><td><strong>Notifications</strong></td><td>${notifEnabled ? "Enabled" : "Silent"}</td></tr>
        </table>`;
    document.getElementById("wizardSummary").innerHTML = html;
}

// =========================
// WIZARD FINISH
// =========================
function wizardFinish() {
    const mode         = document.querySelector('input[name="capture_mode"]:checked')?.value || "timelapse";
    const notifEnabled = document.querySelector('input[name="notif_enabled"]:checked')?.value === "yes";
    const burstEnabled = document.getElementById("wiz_burst_enabled")?.checked || false;
    const achEnabled   = document.getElementById("wiz_achievement_enabled")?.checked || false;

    const payload = {
        capture_mode:      mode,
        screenshot_folder: document.getElementById("wiz_screenshot_folder")?.value || "screenshots",
        per_game_folders:  document.getElementById("wiz_per_game")?.checked !== false,
        interval:          parseInt(document.getElementById("wiz_interval")?.value || 7) * 60000,
        first_delay:       parseInt(document.getElementById("wiz_first_delay")?.value || 10),
        sensitivity:       parseFloat(document.getElementById("wiz_sensitivity")?.value || 30),
        action_cooldown:   parseFloat(document.getElementById("wiz_action_cooldown")?.value || 5),
        burst_enabled:     burstEnabled,
        burst_shots:       Math.min(10, Math.max(1, parseInt(document.getElementById("wiz_burst_shots")?.value || 3))),
        burst_delay:       Math.max(0.5, parseFloat(document.getElementById("wiz_burst_delay")?.value || 0.5)),
        achievement_screenshots_enabled: achEnabled,
        achievement_burst: {
            shots: Math.min(10, Math.max(1, parseInt(document.getElementById("wiz_ach_shots")?.value || 7))),
            delay: Math.max(0.5, parseFloat(document.getElementById("wiz_ach_delay")?.value || 0.5))
        },
        notifications_enabled: notifEnabled,
        minimise_to_tray:  document.getElementById("wiz_minimise_tray")?.checked || false,
        popup_on_game:     document.getElementById("wiz_popup_game")?.checked !== false,
        steam_stats_folder: document.getElementById("wiz_steam_stats")?.value || "",
        selected_platforms: getSelectedPlatforms(),
        hotkeys: { steam: "f12" }
    };

    fetch("/api/setup/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(() => showApp());
}

// =========================
// PREFILL WIZARD
// =========================
function prefillWizard(s) {
    if (!s) return;

    const modeEl = document.querySelector(`input[name="capture_mode"][value="${s.capture_mode || 'timelapse'}"]`);
    if (modeEl) modeEl.checked = true;

    const sf = document.getElementById("wiz_screenshot_folder");
    if (sf) sf.value = s.screenshot_folder || "";

    const pg = document.getElementById("wiz_per_game");
    if (pg) pg.checked = s.per_game_folders !== false;

    const intEl = document.getElementById("wiz_interval");
    if (intEl) intEl.value = Math.round((s.interval || 420000) / 60000);

    const delEl = document.getElementById("wiz_first_delay");
    if (delEl) delEl.value = s.first_delay || 10;

    const sensEl = document.getElementById("wiz_sensitivity");
    if (sensEl) { sensEl.value = s.sensitivity || 30; document.getElementById("wiz_sens_val").textContent = sensEl.value; }

    const coolEl = document.getElementById("wiz_action_cooldown");
    if (coolEl) coolEl.value = s.action_cooldown || 5;

    const wb = document.getElementById("wiz_burst_enabled");
    if (wb) { wb.checked = s.burst_enabled || false; toggleWizBurst(); }

    const wa = document.getElementById("wiz_achievement_enabled");
    if (wa) wa.checked = s.achievement_screenshots_enabled || false;

    const wss = document.getElementById("wiz_steam_stats");
    if (wss) wss.value = s.steam_stats_folder || "";

    if (s.selected_platforms) {
        PLATFORM_STEPS.forEach(p => {
            const el = document.getElementById("use_" + p);
            if (el) el.checked = s.selected_platforms.includes(p);
        });
    }

    const notifMode = s.notifications_enabled !== false ? "yes" : "no";
    const notifEl = document.querySelector(`input[name="notif_enabled"][value="${notifMode}"]`);
    if (notifEl) notifEl.checked = true;

    if (s.notification_sound) updateSoundLabels(s.notification_sound.split("/").pop());
}

// =========================
// BURST TOGGLE (WIZARD)
// =========================
function toggleWizBurst() {
    const enabled = document.getElementById("wiz_burst_enabled")?.checked;
    const opts = document.getElementById("wiz_burst_options");
    if (opts) opts.style.display = enabled ? "block" : "none";
}

function toggleWizStartup(checkbox) {
    const route = checkbox.checked ? "/api/startup/enable" : "/api/startup/disable";
    fetch(route, { method: "POST" })
        .then(r => r.json())
        .then(d => { if (!d.success) { alert("Startup toggle failed: " + (d.error || "")); checkbox.checked = !checkbox.checked; } });
}

// =========================
// WIZARD GAME FOLDERS
// =========================
function wizAutoScanFolders() {
    const selected = getSelectedPlatforms();
    const payload = {};
    selected.forEach(p => payload[p] = true);

    const statusEl = document.getElementById("wiz_scan_status");
    if (statusEl) statusEl.innerHTML = "🔍 Scanning for game folders...";

    fetch("/api/folders/autodetect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(d => {
        if (statusEl) statusEl.innerHTML = "✅ Scan complete.";
        renderWizFolderResults(d.folders, selected);
    })
    .catch(() => { if (statusEl) statusEl.innerHTML = "⚠️ Scan failed. Add folders manually below."; });
}

function renderWizFolderResults(folders, selected) {
    const el = document.getElementById("wiz_folder_results");
    if (!el) return;
    let html = "";
    selected.forEach(p => {
        const info = PLATFORMS[p] || { label: p, cls: "extra_games-label" };
        const paths = folders[p] || [];
        html += `<div class="wiz-folder-platform">
            <div class="wiz-folder-platform-header">
                <span class="platform-label ${info.cls}">${info.label}</span>
                <span class="wiz-folder-count">${paths.length} folder${paths.length !== 1 ? "s" : ""} found</span>
            </div>`;
        if (paths.length > 0) {
            paths.forEach(path => {
                html += `<div class="wiz-folder-item">
                    <span class="folder-path">${path}</span>
                    <button class="remove-btn" onclick="wizRemoveFolder('${p}', '${path.replace(/\\/g, "\\\\")}', this)">✕</button>
                </div>`;
            });
        } else {
            html += `<div class="wiz-folder-item">No folders found automatically.</div>`;
        }
        html += `</div>`;
    });
    el.innerHTML = html;
}

function wizRemoveFolder(platform, path, btn) {
    fetch("/api/folders/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform, path })
    }).then(r => r.json()).then(d => {
        if (d.success) btn.closest(".wiz-folder-item")?.remove();
    });
}

function wizAddFolder() {
    const platform = document.getElementById("wiz_add_platform")?.value;
    const path = document.getElementById("wiz_add_path")?.value?.trim();
    if (!path) return;
    fetch("/api/folders/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform, path })
    }).then(r => r.json()).then(d => {
        if (d.success) {
            document.getElementById("wiz_add_path").value = "";
            renderWizFolderResults(d.folders, getSelectedPlatforms());
        }
    });
}

function wizBrowseFolder(inputId) { browseFolder(path => { const el = document.getElementById(inputId); if (el) el.value = path; }); }

// =========================
// KEY CAPTURE
// =========================
document.addEventListener("keydown", function(e) {
    const active = document.activeElement;
    if (!active || !active.classList.contains("key-input")) return;
    e.preventDefault();
    const parts = [];
    if (e.ctrlKey)  parts.push("ctrl");
    if (e.altKey)   parts.push("alt");
    if (e.shiftKey) parts.push("shift");
    const key = e.key.toLowerCase();
    if (["control", "alt", "shift", "meta"].includes(key)) return;
    const keyMap = { " ": "space", "arrowup": "up", "arrowdown": "down", "arrowleft": "left", "arrowright": "right", "printscreen": "printscreen" };
    parts.push(keyMap[key] || key);
    active.value = parts.join("+");
});

function clearKey(id) { const el = document.getElementById(id); if (el) el.value = ""; }

// =========================
// COPY TO CLIPBOARD
// =========================
function copyToClipboard(id) {
    const el = document.getElementById(id);
    if (!el || !el.value) return;
    navigator.clipboard.writeText(el.value).then(() => {
        const btn = el.nextElementSibling;
        if (btn) { const o = btn.textContent; btn.textContent = "✓ Copied!"; setTimeout(() => btn.textContent = o, 1500); }
    });
}

// =========================
// TAB SYSTEM
// =========================
function switchTab(tab, btn) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(tab).classList.add("active");
    if (btn) btn.classList.add("active");
    if (tab === "gallery") loadGallery();
    if (tab === "games")   loadGames();
    // Clear gallery selection when leaving gallery
    if (tab !== "gallery") deselectAllGallery();
}

function switchSettingsTab(tabId, btn) {
    document.querySelectorAll(".stab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".stab").forEach(el => el.classList.remove("active"));
    const tab = document.getElementById(tabId);
    if (tab) tab.classList.add("active");
    if (btn) btn.classList.add("active");
    if (tabId === "stab-feedback") { loadSystemInfo(); loadLog(); }
}

// =========================
// DASHBOARD
// =========================
function loadDashboard() {
    fetch("/api/settings").then(r => r.json()).then(s => {
        loadDashCaptureMode(s);
    });
    loadLastSession();
    fetch("/api/status").then(r => r.json()).then(d => {
        const game = d.activeGame || "None";
        document.getElementById("activeGame").innerText = game;
        document.getElementById("activePlatform").innerText = d.activePlatform || "—";
        document.getElementById("gameCount").innerText = d.games || 0;

        const dot = document.getElementById("statusDot");
        const txt = document.getElementById("statusText");
        const badge = document.getElementById("activePlatformBadge");

        if (d.gameActive) {
            dot.className = "status-dot running";
            txt.innerText = "Capturing";
            badge.innerText = game !== "None" ? game : "";
        } else {
            dot.className = "status-dot";
            txt.innerText = "Monitoring";
            badge.innerText = "";
        }
    });

    fetch("/api/stats").then(r => r.json()).then(d => {
        document.getElementById("shotCount").innerText = d.screenshots_taken || 0;
    });

    loadScreenshotFolderLinks();
}

function loadScreenshotFolderLinks() {
    fetch("/api/settings").then(r => r.json()).then(settings => {
        const folders = settings.screenshot_folders || {};
        let html = "";
        Object.entries(PLATFORMS).forEach(([key, info]) => {
            const path = folders[key];
            if (path) {
                const safe = path.replace(/\\/g, "\\\\");
                html += `<div class="folder-link-row">
                    <span class="platform-label ${info.cls}">${info.label}</span>
                    <span class="folder-path">${path}</span>
                    <button class="btn btn-secondary" onclick="openFolder('${safe}')">Open</button>
                </div>`;
            }
        });

        // Also show ShotTaker's own screenshot folder
        const sf = settings.screenshot_folder;
        if (sf) {
            const safe = sf.replace(/\\/g, "\\\\");
            html = `<div class="folder-link-row">
                <span class="platform-label" style="background:var(--accent-dim);color:var(--accent);border:1px solid var(--accent);">ShotTaker</span>
                <span class="folder-path">${sf}</span>
                <button class="btn btn-secondary" onclick="openFolder('${safe}')">Open</button>
            </div>` + html;
        }

        if (!html) html = "<p class='hint' style='color:var(--text-dim); font-size:12px;'>No screenshot folders configured. Set them in Settings → Gallery.</p>";
        document.getElementById("screenshotFolderLinks").innerHTML = html;
    });
}

// =========================
// GALLERY
// =========================
let galleryItems = [];
let galleryPage = 1;
let galleryCurrentIndex = 0;

function loadGallery() {
    const game = document.getElementById("gallery_game_filter")?.value || "";
    const type = document.getElementById("gallery_type_filter")?.value || "";

    fetch(`/api/gallery/screenshots?game=${encodeURIComponent(game)}&type=${encodeURIComponent(type)}&page=${galleryPage}&per_page=24`)
        .then(r => r.json())
        .then(data => {
            galleryItems = data.items || [];
            renderGallery(data);
            updateGalleryFilters();
        })
        .catch(() => {
            document.getElementById("galleryEmpty").classList.remove("hidden");
            document.getElementById("galleryGrid").innerHTML = "";
        });
}

function renderGallery(data) {
    const grid  = document.getElementById("galleryGrid");
    const empty = document.getElementById("galleryEmpty");
    const stats = document.getElementById("galleryStats");
    const pag   = document.getElementById("galleryPagination");

    if (!data.items || data.items.length === 0) {
        grid.innerHTML = "";
        empty.classList.remove("hidden");
        pag.innerHTML = "";
        if (stats) stats.innerText = "";
        return;
    }

    empty.classList.add("hidden");
    if (stats) stats.innerText = `${data.total} screenshot${data.total !== 1 ? "s" : ""}`;

    const typeClasses = { TimeLapse: "badge-timelapse", DynamicShot: "badge-dynamic", Achievement: "badge-achievement" };
    const typeLabels  = { TimeLapse: "Time Lapse", DynamicShot: "Action Shot", Achievement: "Achievement" };

    grid.innerHTML = data.items.map((item, i) => `
        <div class="card" tabindex="0" id="card_${i}"
             onclick="handleCardClick(event, ${i})"
             onkeydown="if(event.key==='Enter') openLightbox(${i})">
            <input type="checkbox" class="card-select-check" id="check_${i}"
                   onclick="event.stopPropagation(); toggleCardSelect(${i})"
                   onchange="updateSelectionToolbar()">
            <button class="card-delete-btn" onclick="event.stopPropagation(); deleteCardShot(${i})" title="Delete">✕</button>
            <div class="card-thumb">
                <img src="${item.thumb}" alt="${item.filename}" loading="lazy"
                     onload="this.classList.add('loaded')" onerror="this.style.display='none'">
                <div class="card-placeholder">📷</div>
            </div>
            <div class="card-body">
                <div class="card-game">${item.game || "Unknown"}</div>
                <div class="card-meta">
                    <span class="card-type-badge ${typeClasses[item.type] || ''}">${typeLabels[item.type] || item.type}</span>
                    #${item.num}
                </div>
            </div>
        </div>`).join("");

    // Pagination
    renderPagination(data.page, data.pages, pag);
}

function renderPagination(current, total, container) {
    if (total <= 1) { container.innerHTML = ""; return; }
    let html = "";
    const prev = current > 1;
    const next = current < total;
    html += `<button class="page-btn" ${!prev ? "disabled" : ""} onclick="galleryGoPage(${current - 1})">←</button>`;
    for (let i = 1; i <= total; i++) {
        if (i === 1 || i === total || Math.abs(i - current) <= 2) {
            html += `<button class="page-btn ${i === current ? 'active' : ''}" onclick="galleryGoPage(${i})">${i}</button>`;
        } else if (Math.abs(i - current) === 3) {
            html += `<span class="page-ellipsis">…</span>`;
        }
    }
    html += `<button class="page-btn" ${!next ? "disabled" : ""} onclick="galleryGoPage(${current + 1})">→</button>`;
    container.innerHTML = html;
}

function galleryGoPage(page) { galleryPage = page; loadGallery(); }

function updateGalleryFilters() {
    fetch("/api/gallery/games").then(r => r.json()).then(games => {
        const sel = document.getElementById("gallery_game_filter");
        if (!sel) return;
        const current = sel.value;
        sel.innerHTML = '<option value="">All Games</option>' +
            games.map(g => `<option value="${g}" ${g === current ? "selected" : ""}>${g}</option>`).join("");
    });
}

// =========================
// LIGHTBOX
// =========================
function openLightbox(index) {
    galleryCurrentIndex = index;
    const item = galleryItems[index];
    if (!item) return;

    document.getElementById("lbImg").src = item.url;
    document.getElementById("lbGame").innerText = item.game || "";
    document.getElementById("lbType").innerText = item.type || "";
    document.getElementById("lbNum").innerText = `#${item.num}`;
    const copyBtn = document.getElementById("lbCopy");
    if (copyBtn) copyBtn.dataset.url = item.url;

    // Size lightbox to 85% of window
    const frame = document.querySelector(".lb-frame");
    const img   = document.getElementById("lbImg");
    if (frame && img) {
        const w = Math.round(window.innerWidth  * 0.85);
        const h = Math.round(window.innerHeight * 0.85);
        frame.style.width    = w + "px";
        frame.style.height   = h + "px";
        frame.style.maxWidth = w + "px";
        img.style.maxWidth   = w + "px";
        img.style.maxHeight  = (h - 80) + "px";
    }

    // Update open-with label
    fetch("/api/settings").then(r => r.json()).then(s => {
        const prog = s.open_with || "mspaint";
        const name = prog.split("\\").pop().split("/").pop().replace(".exe", "");
        document.getElementById("lbOpenWith").innerText = `🖼 Open in ${name}`;
    });

    document.getElementById("lbPrev").classList.toggle("hidden", index === 0);
    document.getElementById("lbNext").classList.toggle("hidden", index === galleryItems.length - 1);
    document.getElementById("lightbox").classList.remove("hidden");
}

function closeLightbox() { document.getElementById("lightbox").classList.add("hidden"); }

function lightboxNav(dir) {
    const next = galleryCurrentIndex + dir;
    if (next >= 0 && next < galleryItems.length) openLightbox(next);
}

document.addEventListener("keydown", function(e) {
    if (!document.getElementById("lightbox").classList.contains("hidden")) {
        if (e.key === "ArrowLeft")  lightboxNav(-1);
        if (e.key === "ArrowRight") lightboxNav(1);
        if (e.key === "Escape")     closeLightbox();
    }
});

function copyScreenshotPath() {
    const item = galleryItems[galleryCurrentIndex];
    if (!item) return;
    navigator.clipboard.writeText(item.path || item.url).then(() => {
        const btn = document.getElementById("lbCopy");
        if (btn) { const o = btn.textContent; btn.textContent = "✓ Copied!"; setTimeout(() => btn.textContent = o, 1500); }
    });
}

function openInApp() {
    const item = galleryItems[galleryCurrentIndex];
    if (!item) return;
    fetch("/api/gallery/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: item.path })
    }).then(r => r.json()).then(d => { if (!d.success) showToast("Could not open: " + (d.error || ""), "error"); });
}

function deleteCurrentShot() {
    const item = galleryItems[galleryCurrentIndex];
    if (!item) return;
    if (!confirm(`Delete ${item.filename}?`)) return;
    fetch("/api/gallery/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: item.path })
    }).then(r => r.json()).then(d => {
        if (d.success) { closeLightbox(); loadGallery(); showToast("Deleted.", "success"); }
        else showToast("Delete failed: " + (d.error || ""), "error");
    });
}

// =========================
// GAMES LIST
// =========================
let allGames = {};
let activePlatformFilter = "all";

function loadGames() {
    fetch("/api/games").then(r => r.json()).then(data => { allGames = data; filterGames(); });
}

function setPlatformFilter(platform, btn) {
    activePlatformFilter = platform;
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    filterGames();
}

function filterGames() {
    const search = document.getElementById("gamesSearch")?.value.toLowerCase().trim() || "";
    const entries = Object.entries(allGames);
    const filtered = entries.filter(([exe, platform]) =>
        (activePlatformFilter === "all" || platform === activePlatformFilter) &&
        (!search || exe.includes(search))
    ).sort((a, b) => a[0].localeCompare(b[0]));

    const countEl = document.getElementById("gamesCount");
    if (countEl) countEl.innerText = `${filtered.length} of ${entries.length}`;

    let html = "";
    if (entries.length === 0) {
        html = "<p class='hint' style='color:var(--text-dim); padding:20px 0;'>No games found. Add game folders in Settings → Platforms and run a scan.</p>";
    } else if (filtered.length === 0) {
        html = "<p class='hint' style='color:var(--text-dim); padding:20px 0;'>No games match your search or filter.</p>";
    } else {
        filtered.forEach(([exe, platform]) => {
            const info = PLATFORMS[platform] || { label: platform, cls: "extra_games-label" };
            html += `<div class="game-item">
                <span class="game-exe">${exe}</span>
                <span class="platform-label ${info.cls}">${info.label}</span>
                <button class="btn btn-secondary" onclick="blacklistGame('${exe}')">Blacklist</button>
                <button class="btn btn-secondary" onclick="disableGame('${exe}')">Disable</button>
            </div>`;
        });
    }
    document.getElementById("gamesList").innerHTML = html;
}

function disableGame(exe) {
    fetch("/api/games/disable", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ exe }) })
        .then(() => loadGames());
}

function blacklistGame(exe) {
    fetch("/api/blacklist/add", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ exe }) })
        .then(() => { loadGames(); loadBlacklist(); });
}

// =========================
// BLACKLIST
// =========================
function loadBlacklist() {
    fetch("/api/blacklist").then(r => r.json()).then(data => {
        let html = data.length
            ? data.map(x => `<div class="blacklist-item"><span>${x}</span><button class="btn btn-secondary" onclick="restoreGame('${x}')">Restore</button></div>`).join("")
            : "<p class='hint' style='color:var(--text-dim); padding:20px 0;'>Blacklist is empty.</p>";
        document.getElementById("blacklistList").innerHTML = html;
    });
}

function restoreGame(exe) {
    fetch("/api/blacklist/move_to_games", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ exe }) })
        .then(() => { loadBlacklist(); loadGames(); });
}

// =========================
// SETTINGS — LOAD
// =========================
function loadSettings() {
    fetch("/api/settings").then(r => r.json()).then(d => {
        // Capture mode
        const modeEl = document.querySelector(`input[name="s_capture_mode"][value="${d.capture_mode || 'timelapse'}"]`);
        if (modeEl) modeEl.checked = true;
        updateSettingsVisibility();

        // Interval
        const iv = document.getElementById("interval");
        if (iv) iv.value = Math.round((d.interval || 420000) / 60000);
        const fd = document.getElementById("first_delay");
        if (fd) fd.value = d.first_delay || 10;

        // Action shots
        const sv = document.getElementById("sensitivity");
        if (sv) { sv.value = d.sensitivity || 30; document.getElementById("sens_val").textContent = sv.value; }
        setCooldownFromSeconds(d.action_cooldown || 5);

        // Burst
        const be = document.getElementById("burst_enabled");
        if (be) { be.checked = d.burst_enabled || false; toggleBurst(); }
        const bs = document.getElementById("burst_shots");
        if (bs) bs.value = d.burst_shots || 3;
        const bd = document.getElementById("burst_delay");
        if (bd) bd.value = d.burst_delay || 0.5;

        // Achievement
        const ae = document.getElementById("achievement_enabled");
        if (ae) ae.checked = d.achievement_screenshots_enabled || false;
        const as = document.getElementById("ach_shots");
        if (as) as.value = d.achievement_burst?.shots || 7;
        const ad = document.getElementById("ach_delay");
        if (ad) ad.value = d.achievement_burst?.delay || 0.5;

        // Hotkeys
        const hks = document.getElementById("hk_steam");
        if (hks) hks.value = d.hotkeys?.steam || "f12";
        const shb = document.getElementById("steam_hotkey_backup");
        if (shb) shb.checked = d.steam_hotkey_backup || false;

        // Gallery
        const sff = document.getElementById("screenshot_folder");
        if (sff) sff.value = d.screenshot_folder || "";
        const pgf = document.getElementById("per_game_folders");
        if (pgf) pgf.checked = d.per_game_folders !== false;
        const ow = document.getElementById("open_with");
        if (ow) ow.value = d.open_with || "mspaint";

        // Screenshot folders
        const sf = d.screenshot_folders || {};
        ["steam","gog","epic","ubisoft","ea"].forEach(p => {
            const el = document.getElementById("sf_" + p);
            if (el) el.value = sf[p] || "";
        });

        // Notifications
        loadNotifSettings(d);

        // Window
        loadWindowSettings();

        // Steam stats
        const ssf = document.getElementById("steam_stats_folder");
        if (ssf) ssf.value = d.steam_stats_folder || "";

        // Debug
        loadDebugMode();
    });
}

// Listen for capture mode changes in settings
document.addEventListener("change", function(e) {
    if (e.target.name === "s_capture_mode") updateSettingsVisibility();
});

// =========================
// SETTINGS — SAVE
// =========================
function saveSettings() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.interval    = parseInt(document.getElementById("interval").value) * 60000;
        current.first_delay = parseInt(document.getElementById("first_delay").value) || 10;
        current.burst_enabled = document.getElementById("burst_enabled")?.checked || false;
        current.burst_shots = Math.min(10, Math.max(1, parseInt(document.getElementById("burst_shots")?.value || 3)));
        current.burst_delay = Math.max(0.5, parseFloat(document.getElementById("burst_delay")?.value || 0.5));
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => showToast("Saved.", "success"));
}

function updateSettingsVisibility() {
    const mode = document.querySelector('input[name="s_capture_mode"]:checked')?.value || "timelapse";
    const tl = document.getElementById("card_timelapse");
    const as = document.getElementById("card_actionshots");
    if (tl) tl.style.display = (mode === "timelapse" || mode === "hybrid") ? "block" : "none";
    if (as) as.style.display = (mode === "action" || mode === "hybrid") ? "block" : "none";
}

function saveCaptureMode() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.capture_mode = document.querySelector('input[name="s_capture_mode"]:checked')?.value || "timelapse";
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => { showToast("Capture mode saved.", "success"); updateSettingsVisibility(); });
}

function saveActionSettings() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.sensitivity    = parseFloat(document.getElementById("sensitivity")?.value || 30);
        current.action_cooldown = getCooldownSeconds();
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => showToast("Saved.", "success"));
}

function saveAchievementSettings() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.achievement_screenshots_enabled = document.getElementById("achievement_enabled")?.checked || false;
        current.achievement_burst = {
            shots: Math.min(10, Math.max(1, parseInt(document.getElementById("ach_shots")?.value || 7))),
            delay: Math.max(0.5, parseFloat(document.getElementById("ach_delay")?.value || 0.5))
        };
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    });
}

function saveHotkeys() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.hotkeys = current.hotkeys || {};
        current.hotkeys.steam = document.getElementById("hk_steam")?.value || "f12";
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => showToast("Hotkey saved.", "success"));
}

function saveHotkeyBackup() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.steam_hotkey_backup = document.getElementById("steam_hotkey_backup")?.checked || false;
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    });
}

function saveGallerySettings() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.screenshot_folder = document.getElementById("screenshot_folder")?.value || "screenshots";
        current.per_game_folders  = document.getElementById("per_game_folders")?.checked !== false;
        current.open_with         = document.getElementById("open_with")?.value || "mspaint";
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => { showToast("Gallery settings saved.", "success"); loadDashboard(); });
}

function saveScreenshotFolders() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.screenshot_folders = current.screenshot_folders || {};
        ["steam","gog","epic","ubisoft","ea"].forEach(p => {
            current.screenshot_folders[p] = document.getElementById("sf_" + p)?.value || "";
        });
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => { showToast("Folders saved.", "success"); loadDashboard(); });
}

function saveSteamStatsFolder() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.steam_stats_folder = document.getElementById("steam_stats_folder")?.value || "";
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    }).then(() => showToast("Steam stats folder saved.", "success"));
}

function toggleBurst() {
    const enabled = document.getElementById("burst_enabled")?.checked;
    const opts = document.getElementById("burst_options");
    if (opts) opts.style.display = enabled ? "block" : "none";
}

// =========================
// GAME FOLDERS
// =========================
function loadFolders() {
    fetch("/api/folders").then(r => r.json()).then(data => {
        const allPlatforms = ["steam","gog","epic","ubisoft","ea","extra_games"];
        const labels = { steam:"Steam", gog:"GOG", epic:"Epic", ubisoft:"Ubisoft", ea:"EA", extra_games:"Other" };
        const clss   = { steam:"steam-label", gog:"gog-label", epic:"epic-label", ubisoft:"ubisoft-label", ea:"ea-label", extra_games:"extra_games-label" };

        allPlatforms.forEach(key => {
            const id = key === "extra_games" ? "extraFolderList" : key + "FolderList";
            const el = document.getElementById(id);
            if (!el) return;
            const paths = data[key] || [];
            let html = `<h4 style="font-size:12px; color:var(--text-dim); margin:10px 0 6px;"><span class="platform-label ${clss[key]}">${labels[key]}</span></h4>`;
            if (paths.length > 0) {
                paths.forEach(path => {
                    const safe = path.replace(/\\/g, "\\\\");
                    html += `<div class="folder-item-row">
                        <span class="folder-path" style="flex:1;">${path}</span>
                        <button class="remove-btn" onclick="removeGameFolder('${key}', '${safe}')">✕ Remove</button>
                    </div>`;
                });
            } else {
                html += `<span class="hint" style="font-size:12px; color:var(--text-dim);">None added.</span>`;
            }
            el.innerHTML = html;
        });
    });
}

function addGameFolder() {
    const platform = document.getElementById("add_platform")?.value;
    const path = document.getElementById("add_folder_path")?.value?.trim();
    if (!path) return;
    fetch("/api/folders/add", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ platform, path }) })
        .then(r => r.json()).then(d => {
            if (d.success) { document.getElementById("add_folder_path").value = ""; loadFolders(); fetch("/api/scan/games").then(() => loadGames()); }
        });
}

function removeGameFolder(platform, path) {
    fetch("/api/folders/remove", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ platform, path }) })
        .then(r => r.json()).then(() => { loadFolders(); fetch("/api/scan/games").then(() => loadGames()); });
}

function runAutoScan() {
    const payload = {};
    ["steam","gog","epic","ubisoft","ea"].forEach(p => payload[p] = true);
    fetch("/api/folders/autodetect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        .then(r => r.json()).then(() => { loadFolders(); showToast("Auto-scan complete.", "success"); });
}

function triggerGameScan() {
    fetch("/api/scan/games").then(r => r.json()).then(() => { loadGames(); showToast("Games rescanned.", "success"); });
}

// =========================
// OPEN FOLDER IN EXPLORER
// =========================
function openFolder(path) {
    if (!path) { alert("No folder path set."); return; }
    fetch("/api/folders/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) })
        .then(r => r.json()).then(d => { if (!d.success) alert("Could not open: " + (d.error || "")); });
}

// =========================
// BROWSE FOLDER
// =========================
function browseFolder(callback) {
    fetch("/api/browse/folder", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
        .then(r => r.json()).then(d => { if (d.success && d.path) callback(d.path); else if (!d.cancelled) alert("Could not open folder picker: " + (d.error || "")); });
}

function browseAndFill(inputId) { browseFolder(path => { const el = document.getElementById(inputId); if (el) el.value = path; }); }

// =========================
// NOTIFICATIONS
// =========================
function playBuiltinSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.3);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.4);
    } catch(e) {}
}

function playNotifSound(settings) {
    const path = settings?.notification_sound;
    if (path) { try { new Audio(path).play().catch(() => playBuiltinSound()); } catch(e) { playBuiltinSound(); } }
    else playBuiltinSound();
}

function showGameNotification(exe, platform, settings) {
    if (!settings?.notifications_enabled) return;
    playNotifSound(settings);
    const body = `${exe} (${platform}) — capturing started.\n\nNot in a game? Blacklist this exe from the Games tab.`;
    if (Notification.permission === "granted") new Notification("🎮 ShotTaker", { body });
    else if (Notification.permission !== "denied") Notification.requestPermission().then(p => { if (p === "granted") new Notification("🎮 ShotTaker", { body }); });
}

function testNotification() {
    Notification.requestPermission().then(p => {
        const warn = document.getElementById("wiz_notif_permission");
        if (p === "granted") {
            if (warn) warn.style.display = "none";
            fetch("/api/settings").then(r => r.json()).then(s => {
                playNotifSound(s);
                new Notification("🎮 ShotTaker — Test", { body: "example-game.exe (steam) — this is what a detection notification looks like." });
            });
        } else { if (warn) warn.style.display = "block"; }
    });
}

function uploadSound(input) {
    const file = input.files[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    fetch("/api/sound/upload", { method: "POST", body: fd }).then(r => r.json()).then(d => {
        if (d.success) updateSoundLabels(file.name); else alert("Upload failed: " + (d.error || ""));
    });
}

function deleteSound() {
    fetch("/api/sound/delete", { method: "POST" }).then(r => r.json()).then(() => updateSoundLabels(null));
}

function updateSoundLabels(filename) {
    ["wiz_sound_label","sound_label"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = filename ? `Custom: ${filename}` : "Using built-in sound";
    });
    ["wiz_sound_delete","sound_delete"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = filename ? "inline-block" : "none";
    });
}

function saveNotifSetting() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.notifications_enabled = document.getElementById("notif_enabled_setting")?.checked || false;
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    });
}

function loadNotifSettings(s) {
    const toggle = document.getElementById("notif_enabled_setting");
    if (toggle) toggle.checked = s?.notifications_enabled || false;
    if (s?.notification_sound) updateSoundLabels(s.notification_sound.split("/").pop());
}

let lastDetectedGame = null;
function checkForNewGame() {
    fetch("/api/status").then(r => r.json()).then(d => {
        const game = d.activeGame; const platform = d.activePlatform || "unknown";
        if (game && game !== lastDetectedGame) {
            lastDetectedGame = game;
            fetch("/api/settings").then(r => r.json()).then(s => showGameNotification(game, platform, s));
        } else if (!game && lastDetectedGame) {
                lastDetectedGame = null;
                // Auto-show recent session in gallery when game ends
                if (document.getElementById("gallery")?.classList.contains("active")) {
                    if (!sessionFilterActive) toggleSessionFilter();
                }
                loadLastSession();
            } else if (!game) {
                lastDetectedGame = null;
            }
    });
}
setInterval(checkForNewGame, 5000);

// =========================
// WINDOW & STARTUP
// =========================
function loadWindowSettings() {
    fetch("/api/startup/status").then(r => r.json()).then(d => {
        const el = document.getElementById("setting_startup"); if (el) el.checked = d.in_startup || false;
    });
    fetch("/api/settings").then(r => r.json()).then(d => {
        const mt = document.getElementById("setting_minimise_tray"); if (mt) mt.checked = d.minimise_to_tray || false;
        const pg = document.getElementById("setting_popup_game"); if (pg) pg.checked = d.popup_on_game !== false;
        const pd = document.getElementById("setting_popup_duration"); if (pd) pd.value = d.popup_duration || 5;
        const row = document.getElementById("popup_duration_row");
        if (row) row.style.display = (d.minimise_to_tray && d.popup_on_game !== false) ? "flex" : "none";
    });
}

function toggleStartup(checkbox) {
    const route = checkbox.checked ? "/api/startup/enable" : "/api/startup/disable";
    fetch(route, { method: "POST" }).then(r => r.json()).then(d => {
        if (!d.success) { alert("Startup toggle failed: " + (d.error || "")); checkbox.checked = !checkbox.checked; }
    });
}

function saveWindowSettings() {
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.minimise_to_tray = document.getElementById("setting_minimise_tray")?.checked || false;
        current.popup_on_game    = document.getElementById("setting_popup_game")?.checked !== false;
        current.popup_duration   = parseInt(document.getElementById("setting_popup_duration")?.value || 5);
        const row = document.getElementById("popup_duration_row");
        if (row) row.style.display = (current.minimise_to_tray && current.popup_on_game) ? "flex" : "none";
        return fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(current) });
    });
}

// =========================
// BURST & ACHIEVEMENT
// =========================
function fireManualBurst() {
    fetch("/api/burst/fire", { method: "POST" }).then(r => r.json()).then(d => {
        if (d.success) showToast("Burst fired!", "success"); else alert("Burst failed: " + (d.error || ""));
    });
}

// =========================
// DEBUG MODE
// =========================
function loadDebugMode() {
    fetch("/api/debug/status").then(r => r.json()).then(d => {
        const el = document.getElementById("debug_mode_toggle"); if (el) el.checked = d.debug_mode || false;
    });
}

function saveDebugMode(checkbox) {
    fetch("/api/debug/set", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: checkbox.checked }) })
        .then(r => r.json()).then(() => {
            const note = document.getElementById("debug_restart_note"); if (note) note.style.display = "block";
        });
}

// =========================
// LOG
// =========================
let _fullLog = [];

function loadLog() {
    fetch("/api/log").then(r => r.json()).then(lines => {
        _fullLog = [...lines].reverse();
        const el = document.getElementById("detectionLog"); if (!el) return;
        el.innerHTML = lines.length
            ? lines.map(l => {
                let cls = "log-line";
                if (l.includes("[GAME]"))  cls += " log-game";
                else if (l.includes("[SCAN]")) cls += " log-scan";
                else if (l.includes("[CMD]"))  cls += " log-cmd";
                else if (l.includes("[ACH]") || l.includes("[CAP]") || l.includes("[ACT]")) cls += " log-ach";
                else if (l.toLowerCase().includes("error")) cls += " log-error";
                return `<div class="${cls}">${l}</div>`;
            }).join("")
            : "<span style='color:var(--text-dim);font-size:12px;'>No log entries yet.</span>";
    });
}

function copyFullLog() {
    if (!_fullLog.length) { alert("Log is empty."); return; }
    navigator.clipboard.writeText(_fullLog.join("\n")).then(() => {
        const btn = document.querySelector(".log-copy-btn");
        if (btn) { const o = btn.textContent; btn.textContent = "✓ Copied!"; setTimeout(() => btn.textContent = o, 1500); }
    });
}

function clearLogDisplay() {
    const el = document.getElementById("detectionLog"); if (el) el.innerHTML = "<span style='color:var(--text-dim);font-size:12px;'>Cleared.</span>";
    _fullLog = [];
}

// =========================
// SYSTEM INFO
// =========================
function loadSystemInfo() {
    fetch("/api/sysinfo").then(r => r.json()).then(d => {
        const el = document.getElementById("systemInfo"); if (!el) return;
        el.innerHTML = Object.entries(d).map(([k, v]) => `<div class="log-line"><span style="color:var(--accent)">${k}:</span> ${v}</div>`).join("");
    });
}

// =========================
// FEEDBACK
// =========================
function sendFeedback() {
    const type    = document.getElementById("feedback_type")?.value || "bug";
    const body    = document.getElementById("feedback_body")?.value || "";
    const inclLog = document.getElementById("feedback_include_log")?.checked;
    const typeLabels = { bug: "Bug Report", suggestion: "Suggestion", other: "Feedback" };
    const subject = encodeURIComponent(`ShotTaker ${typeLabels[type] || "Feedback"}`);
    let emailBody = body;
    if (inclLog && _fullLog.length) emailBody += "\n\n--- Detection Log ---\n" + _fullLog.join("\n");
    fetch("/api/sysinfo").then(r => r.json()).then(sysinfo => {
        emailBody += "\n\n--- System Info ---\n" + Object.entries(sysinfo).map(([k,v]) => `${k}: ${v}`).join("\n");
        window.location.href = `mailto:FEEDBACK_EMAIL_HERE?subject=${subject}&body=${encodeURIComponent(emailBody)}`;
    });
}

// =========================
// GALLERY SELECTION
// =========================
let selectedItems = new Set();
let sessionFilterActive = false;

function handleCardClick(event, index) {
    if (event.target.classList.contains('card-select-check') ||
        event.target.classList.contains('card-delete-btn')) return;
    if (selectedItems.size > 0) {
        toggleCardSelect(index);
    } else {
        openLightbox(index);
    }
}

function toggleCardSelect(index) {
    const card = document.getElementById(`card_${index}`);
    const check = document.getElementById(`check_${index}`);
    if (selectedItems.has(index)) {
        selectedItems.delete(index);
        card?.classList.remove("selected");
        if (check) check.checked = false;
    } else {
        selectedItems.add(index);
        card?.classList.add("selected");
        if (check) check.checked = true;
    }
    updateSelectionToolbar();
}

function updateSelectionToolbar() {
    const toolbar = document.getElementById("selectionToolbar");
    const count = document.getElementById("selectionCount");
    if (toolbar) toolbar.classList.toggle("visible", selectedItems.size > 0);
    if (count) count.textContent = `${selectedItems.size} selected`;
}

function selectAllGallery() {
    galleryItems.forEach((_, i) => {
        selectedItems.add(i);
        document.getElementById(`card_${i}`)?.classList.add("selected");
        const check = document.getElementById(`check_${i}`);
        if (check) check.checked = true;
    });
    updateSelectionToolbar();
}

function deselectAllGallery() {
    selectedItems.forEach(i => {
        document.getElementById(`card_${i}`)?.classList.remove("selected");
        const check = document.getElementById(`check_${i}`);
        if (check) check.checked = false;
    });
    selectedItems.clear();
    updateSelectionToolbar();
}

function deleteCardShot(index) {
    const item = galleryItems[index];
    if (!item) return;
    if (!confirm(`Delete ${item.filename}?`)) return;
    fetch("/api/gallery/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: item.path })
    }).then(r => r.json()).then(d => {
        if (d.success) { loadGallery(); showToast("Deleted.", "success"); }
        else showToast("Delete failed: " + (d.error || ""), "error");
    });
}

function bulkDeleteSelected() {
    if (selectedItems.size === 0) return;
    if (!confirm(`Delete ${selectedItems.size} screenshot(s)? This cannot be undone.`)) return;
    const paths = Array.from(selectedItems).map(i => galleryItems[i]?.path).filter(Boolean);
    Promise.all(paths.map(path =>
        fetch("/api/gallery/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path })
        }).then(r => r.json())
    )).then(results => {
        const ok = results.filter(r => r.success).length;
        deselectAllGallery();
        loadGallery();
        showToast(`Deleted ${ok} screenshot(s).`, "success");
    });
}


// =========================
// BULK RENAME
// =========================
function showBulkRename() {
    if (selectedItems.size === 0) return;
    document.getElementById("renameCount").textContent = selectedItems.size;
    document.getElementById("bulkRenameModal").style.display = "flex";

    // Populate game name suggestions
    fetch("/api/gallery/games").then(r => r.json()).then(games => {
        const dl = document.getElementById("gameNameSuggestions");
        if (dl) dl.innerHTML = games.map(g => `<option value="${g}">`).join("");
    });

    updateRenamePreview();
}

function updateRenamePreview() {
    const game = document.getElementById("rename_game")?.value || "GameName";
    const type = document.getElementById("rename_type")?.value || "TimeLapse";
    const preview = document.getElementById("renamePreview");
    if (preview) preview.textContent = `${game}_${type}_001.png`;
}

document.addEventListener("input", function(e) {
    if (e.target.id === "rename_game" || e.target.id === "rename_type") updateRenamePreview();
});

function closeBulkRename() {
    document.getElementById("bulkRenameModal").style.display = "none";
}

function confirmBulkRename() {
    const game = document.getElementById("rename_game")?.value?.trim();
    const type = document.getElementById("rename_type")?.value;
    if (!game) { alert("Please enter a game name."); return; }

    const paths = Array.from(selectedItems).map(i => galleryItems[i]?.path).filter(Boolean);

    fetch("/api/gallery/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paths, game_name: game, shot_type: type })
    })
    .then(r => r.json())
    .then(d => {
        closeBulkRename();
        deselectAllGallery();
        loadGallery();
        const ok = (d.results || []).filter(r => r.success).length;
        const fail = (d.results || []).filter(r => !r.success).length;
        if (fail > 0) showToast(`Renamed ${ok}, failed ${fail}.`, "error");
        else showToast(`Renamed ${ok} screenshot(s).`, "success");
    });
}


// =========================
// SESSION FILTER
// =========================
function toggleSessionFilter() {
    sessionFilterActive = !sessionFilterActive;
    const btn = document.getElementById("sessionFilterBtn");
    if (btn) {
        btn.style.borderColor = sessionFilterActive ? "var(--accent)" : "";
        btn.style.color = sessionFilterActive ? "var(--accent)" : "";
    }
    if (sessionFilterActive) loadSessionGallery();
    else loadGallery();
}

function loadSessionGallery() {
    fetch(`/api/gallery/session?page=${galleryPage}&per_page=24`)
        .then(r => r.json())
        .then(data => {
            galleryItems = data.items || [];
            renderGallery(data);
            // Update stats to show session info
            const stats = document.getElementById("galleryStats");
            const session = data.session;
            if (stats && session) {
                stats.textContent = `${data.total} shots — ${session.game || "Unknown"} — ${session.timestamp || ""}`;
            }
        });
}


// =========================
// DASHBOARD CAPTURE MODE
// =========================
function loadDashCaptureMode(settings) {
    const mode = settings?.capture_mode || "timelapse";
    const modeEl = document.querySelector(`input[name="dash_capture_mode"][value="${mode}"]`);
    if (modeEl) modeEl.checked = true;

    const hint = document.getElementById("dashModeHint");
    if (hint) {
        const interval = Math.round((settings?.interval || 420000) / 60000);
        const sensitivity = settings?.sensitivity || 30;
        if (mode === "timelapse") hint.textContent = `Taking screenshots every ${interval} minutes · Change timing in Settings`;
        else if (mode === "action") hint.textContent = `Capturing on screen changes · Sensitivity: ${sensitivity} · Change in Settings`;
        else hint.textContent = `Time Lapse every ${interval} min + Action Shots at sensitivity ${sensitivity} · Change in Settings`;
    }
}

function saveDashCaptureMode() {
    const mode = document.querySelector('input[name="dash_capture_mode"]:checked')?.value || "timelapse";
    fetch("/api/settings").then(r => r.json()).then(current => {
        current.capture_mode = mode;
        return fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(current)
        });
    }).then(() => {
        fetch("/api/settings").then(r => r.json()).then(s => loadDashCaptureMode(s));
        showToast("Capture mode updated.", "success");
    });
}

function loadLastSession() {
    fetch("/api/session/last").then(r => r.json()).then(session => {
        const card = document.getElementById("lastSessionCard");
        const info = document.getElementById("lastSessionInfo");
        if (!session || !card || !info) return;

        card.style.display = "block";
        const duration = session.end && session.start
            ? Math.round((session.end - session.start) / 60)
            : 0;

        info.innerHTML = `
            <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
                <div><div class="dash-label">Game</div><div style="font-weight:600;">${session.game || "Unknown"}</div></div>
                <div><div class="dash-label">Duration</div><div style="font-weight:600;">${duration} min</div></div>
                <div><div class="dash-label">Screenshots</div><div style="font-weight:600;">${session.shots || 0}</div></div>
                <div><div class="dash-label">Date</div><div style="font-weight:600;">${session.timestamp || ""}</div></div>
                <button class="btn btn-secondary" onclick="viewSessionGallery()" style="margin-left:auto;">View in Gallery →</button>
            </div>`;
    }).catch(() => {});
}

function viewSessionGallery() {
    switchTab("gallery", document.querySelector('.nav-btn[onclick*="gallery"]'));
    sessionFilterActive = false;
    toggleSessionFilter();
}


// =========================
// STEAM APPID LOOKUP
// =========================
function lookupSteamIds() {
    // Find all game names that look like Steam AppIDs (pure numbers)
    const appids = Object.keys(allGames)
        .concat(Array.from(document.querySelectorAll("#gallery_game_filter option"))
            .map(o => o.value).filter(v => v))
        .filter(name => /^[0-9]+$/.test(name));

    if (appids.length === 0) {
        showToast("No numeric AppIDs found in gallery.", "");
        return;
    }

    showToast(`Looking up ${appids.length} Steam AppID(s)...`, "");

    fetch("/api/steam/lookup/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ appids })
    })
    .then(r => r.json())
    .then(results => {
        const found = Object.entries(results).filter(([id, name]) => name);
        if (found.length === 0) {
            showToast("No games found for those AppIDs.", "");
            return;
        }
        // Show results in a simple dialog
        let msg = `Found ${found.length} game(s):\n\n`;
        found.forEach(([id, name]) => { msg += `${id} = ${name}\n`; });
        msg += `\nUse the bulk rename feature to rename these folders.`;
        alert(msg);
        showToast(`Found ${found.length} game name(s).`, "success");
    })
    .catch(e => showToast("Lookup failed: " + e, "error"));
}

// Single AppID lookup
function lookupSingleAppId(appid) {
    return fetch(`/api/steam/lookup?appid=${appid}`)
        .then(r => r.json());
}

// =========================
// COOLDOWN UNIT HELPERS
// =========================
function updateCooldownMax() {
    const unit = document.getElementById("action_cooldown_unit")?.value;
    const input = document.getElementById("action_cooldown");
    if (!input) return;
    if (unit === "minutes") {
        input.max = 60;
        if (parseInt(input.value) > 60) input.value = 60;
    } else {
        input.max = 999;
    }
}

function getCooldownSeconds() {
    const val = parseFloat(document.getElementById("action_cooldown")?.value || 5);
    const unit = document.getElementById("action_cooldown_unit")?.value || "seconds";
    return unit === "minutes" ? val * 60 : val;
}

function setCooldownFromSeconds(seconds) {
    const input = document.getElementById("action_cooldown");
    const unitSel = document.getElementById("action_cooldown_unit");
    if (!input || !unitSel) return;
    if (seconds >= 60 && seconds % 60 === 0) {
        unitSel.value = "minutes";
        input.value = seconds / 60;
    } else {
        unitSel.value = "seconds";
        input.value = seconds;
    }
}

// =========================
// TOAST NOTIFICATIONS
// =========================
function showToast(msg, type = "") {
    const container = document.getElementById("toasts");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    requestAnimationFrame(() => { toast.classList.add("show"); });
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// =========================
// MASTER REFRESH
// =========================
function refreshAll() {
    loadDashboard();
    loadGames();
    loadBlacklist();
    loadSettings();
    loadFolders();
    loadLog();
    loadWindowSettings();
    loadDebugMode();
}

setInterval(loadDashboard, 5000);
setInterval(loadLog, 4000);
setInterval(loadGames, 15000);
