const state = {
  kind: "live",
  category: "",
  query: "",
  limit: 100,
  categories: {},
  selected: null,
  selectedUrl: ""
};

const $ = (id) => document.getElementById(id);
const api = async (path) => {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return await res.json();
};
const fmt = (n) => Number(n || 0).toLocaleString();
const cleanTitle = (name = "") => name.replace(/\s+\[[0-9]+\]\s*$/, "").trim();

function parseEventTime(name = "") {
  const m = name.match(/\((20\d{2})[-_](\d{2})[-_](\d{2})[ T](\d{2}):?(\d{2})(?::?(\d{2}))?\)/);
  if (!m) return null;
  const [, y, mo, d, h, mi] = m;
  const date = new Date(`${y}-${mo}-${d}T${h}:${mi}:00`);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function timeLabel(item) {
  const d = parseEventTime(item.name || "");
  if (!d) return item.kind === "live" ? "LIVE" : item.kind?.toUpperCase() || "ITEM";
  const day = d.toLocaleDateString([], { month: "short", day: "numeric" });
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return `${day} · ${time}`;
}

function setStatus(msg) { $("statusText").textContent = msg; }

async function loadStatus() {
  const data = await api("/api/iptv/status");
  if (!data.ok) {
    setStatus("No IPTV index found");
    $("stats").innerHTML = `<div class="stat"><b>Setup</b><span>${data.message || "Import playlist first"}</span></div>`;
    return;
  }
  setStatus(`${fmt(data.total_items)} indexed items`);
  const counts = data.counts_by_kind || {};
  $("stats").innerHTML = `
    <div class="stat"><b>${fmt(data.total_items)}</b><span>Total</span></div>
    <div class="stat"><b>${fmt(counts.live)}</b><span>Live</span></div>
    <div class="stat"><b>${fmt(counts.movie)}</b><span>Movies</span></div>
    <div class="stat"><b>${fmt(counts.series)}</b><span>Series</span></div>
  `;
}

async function loadCategories() {
  const data = await api("/api/iptv/categories");
  state.categories = data.categories || {};
  renderCategories();
}

function renderCategories() {
  const box = $("categoryList");
  const cats = state.categories[state.kind] || {};
  const entries = Object.entries(cats).sort((a,b) => b[1] - a[1]);
  const allCount = entries.reduce((sum, [,n]) => sum + Number(n || 0), 0);
  box.innerHTML = "";
  const allBtn = categoryButton("", `All ${state.kind}`, allCount);
  box.appendChild(allBtn);
  for (const [name, count] of entries.slice(0, 140)) {
    box.appendChild(categoryButton(name, name, count));
  }
}

function categoryButton(value, label, count) {
  const btn = document.createElement("button");
  btn.className = `category ${state.category === value ? "active" : ""}`;
  btn.innerHTML = `<span>${escapeHtml(label)}</span><span class="count">${fmt(count)}</span>`;
  btn.onclick = () => {
    state.category = value;
    state.query = "";
    $("searchInput").value = "";
    renderCategories();
    loadItems();
  };
  return btn;
}

function pageKindTitle() {
  if (state.kind === "live") return "Live Guide";
  if (state.kind === "movie") return "Movies";
  if (state.kind === "series") return "Series";
  return "IPTV";
}

async function loadItems() {
  state.limit = Number($("limitSelect").value || 100);
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.kind) params.set("kind", state.kind);
  if (state.category) params.set("category", state.category);
  params.set("limit", String(state.limit));
  const data = await api(`/api/iptv/search?${params}`);
  const items = data.items || [];
  $("pageTitle").textContent = pageKindTitle();
  $("pageSubtitle").textContent = state.kind === "live"
    ? "EPG-style live cards. Real XMLTV guide data can be layered in later."
    : "Poster-card browser built from your local playlist index.";
  $("activeFilter").textContent = `${state.category || "All"} ${state.kind}${state.query ? ` · search: ${state.query}` : ""} · ${fmt(items.length)} shown`;
  renderItems(items);
}

function renderItems(items) {
  const grid = $("guideGrid");
  const empty = $("emptyState");
  grid.innerHTML = "";
  empty.classList.toggle("hidden", items.length > 0);
  for (const item of items) grid.appendChild(card(item));
}

function card(item) {
  const el = document.createElement("article");
  el.className = "card";
  const logo = item.logo
    ? `<img class="logo" src="${escapeAttr(item.logo)}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'logo logo-fallback',textContent:'TV'}))">`
    : `<div class="logo logo-fallback">${(item.kind || "TV").slice(0,2).toUpperCase()}</div>`;
  const label = timeLabel(item);
  el.innerHTML = `
    <div class="logo-row">
      ${logo}
      <div>
        <div class="badges">
          <span class="badge">${escapeHtml(label)}</span>
          <span class="badge">${escapeHtml(item.category || item.group || "Uncategorized")}</span>
        </div>
      </div>
    </div>
    <div>
      <h3 class="title">${escapeHtml(cleanTitle(item.name || "Untitled"))}</h3>
      <p class="meta">${escapeHtml(item.tvg_id || item.tvg_name || item.group || "No tvg-id")}</p>
      ${item.kind === "live" ? `<div class="progress"><div></div></div>` : ""}
    </div>
    <div class="card-actions">
      <button data-action="select">Details</button>
      <button data-action="play">Play</button>
    </div>
  `;
  el.querySelector('[data-action="select"]').onclick = () => selectItem(item, false);
  el.querySelector('[data-action="play"]').onclick = () => selectItem(item, true);
  return el;
}

async function selectItem(item, playNow) {
  state.selected = item;
  state.selectedUrl = "";
  $("playerPanel").classList.remove("hidden");
  $("selectedTitle").textContent = cleanTitle(item.name || "Untitled");
  $("selectedMeta").textContent = `${item.kind || "unknown"} · ${item.category || item.group || "Uncategorized"} · ${item.tvg_id || "no tvg-id"}`;
  $("videoPlayer").removeAttribute("src");
  $("openExternal").removeAttribute("href");
  $("openExternal").textContent = "Open direct";
  $("copyUrlButton").disabled = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (playNow) await loadStreamUrl(true);
}

async function loadStreamUrl(play) {
  if (!state.selected) return;
  const data = await api(`/api/iptv/item/${state.selected.id}?include_url=true`);
  const url = data.item?.url || "";
  state.selectedUrl = url;
  $("copyUrlButton").disabled = !url;
  if (url) {
    $("openExternal").href = url;
    $("videoPlayer").src = url;
    if (play) $("videoPlayer").play().catch(() => {});
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}
function escapeAttr(s) { return escapeHtml(s).replace(/`/g, "&#96;"); }

function bind() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.kind = btn.dataset.kind;
      state.category = "";
      state.query = "";
      $("searchInput").value = "";
      renderCategories();
      loadItems();
    };
  });
  $("searchButton").onclick = () => {
    state.query = $("searchInput").value.trim();
    state.category = "";
    renderCategories();
    loadItems();
  };
  $("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") $("searchButton").click(); });
  $("refreshButton").onclick = async () => { await loadStatus(); await loadCategories(); await loadItems(); };
  $("limitSelect").onchange = loadItems;
  $("closePlayer").onclick = () => { $("videoPlayer").pause(); $("playerPanel").classList.add("hidden"); };
  $("loadStreamButton").onclick = () => loadStreamUrl(false);
  $("copyUrlButton").onclick = async () => {
    if (state.selectedUrl) await navigator.clipboard.writeText(state.selectedUrl);
  };
}

(async function main() {
  bind();
  try {
    await loadStatus();
    await loadCategories();
    await loadItems();
  } catch (err) {
    setStatus("IPTV API unavailable");
    $("emptyState").classList.remove("hidden");
    $("emptyState").innerHTML = `<h3>IPTV API unavailable</h3><p>${escapeHtml(err.message)}</p>`;
  }
})();
