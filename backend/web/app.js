/* ===== RankUp web — talks to /api/v1 (same origin) ===== */
const API = "/api/v1";
let RANKS = [["Wood", 0], ["Stone", 60], ["Flint", 140], ["Coal", 240], ["Iron", 360], ["Bronze", 500], ["Silver", 680], ["Gold", 900], ["Platinum", 1160], ["Emerald", 1480], ["Sapphire", 1860], ["Ruby", 2320], ["Diamond", 2880], ["Radiant", 3560], ["Ascended", 4400]];
let USER = null;
let SUBJECT = localStorage.getItem("mt_subject") || "";  // loadSubjects falls back to the first subject
let SUBJECTS = [];
let CURRENT_VIEW = "tutor";
// discipline icon keys (map to ICONS above) — actual SVG line art, not emoji
const SUBJECT_ICONS = ["book", "brain", "sigma", "atom", "flask", "leaf", "globe", "scroll", "palette", "music", "code", "language", "scales", "calculator", "planet", "compass", "pencil"];
const SUBJECT_ICON_SET = new Set(SUBJECT_ICONS);
function subjectIcon(key, size = 18) { return icon(SUBJECT_ICON_SET.has(key) ? key : "book", size); }
function subjectIconKey(key) { return SUBJECT_ICON_SET.has(key) ? key : "book"; }

/* ---- token storage (localStorage = remember me, sessionStorage = this tab only) ---- */
const store = {
  get(k) { return localStorage.getItem(k) ?? sessionStorage.getItem(k); },
  set(k, v, persist) { (persist ? localStorage : sessionStorage).setItem(k, v); },
  clear() { ["mt_token", "mt_refresh"].forEach((k) => { localStorage.removeItem(k); sessionStorage.removeItem(k); }); },
};
let TOKEN = store.get("mt_token") || "";
let REFRESH = store.get("mt_refresh") || "";
let REMEMBER = !!localStorage.getItem("mt_token");

function saveTokens(access, refresh) {
  TOKEN = access; REFRESH = refresh;
  store.set("mt_token", access, REMEMBER);
  store.set("mt_refresh", refresh, REMEMBER);
}

async function tryRefresh() {
  if (!REFRESH) return false;
  const r = await fetch(API + "/auth/refresh", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ refresh: REFRESH }) });
  if (!r.ok) return false;
  const t = await r.json(); saveTokens(t.access, t.refresh); return true;
}

/* ---- api helper (auto-refreshes on 401 once) ---- */
async function api(path, opts = {}) {
  let res = await _fetch(path, opts);
  if (res.status === 401 && (await tryRefresh())) res = await _fetch(path, opts);
  if (res.status === 401 && TOKEN && !path.startsWith("/auth/")) {
    // refresh failed -> session is dead; land the user on the login screen
    store.clear();
    location.reload();
    throw new Error("invalid token");
  }
  if (opts.stream) return res;
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).error?.message || msg; } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}
function _fetch(path, { method = "GET", body } = {}) {
  const headers = { "content-type": "application/json", "x-lang": (window.I18N || {}).lang || "pt" };
  if (TOKEN) headers.authorization = `Bearer ${TOKEN}`;
  return fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
}

const $ = (s) => document.querySelector(s);
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };
function toast(msg) {
  // t() maps known backend PT messages to the active language; unknown text passes through
  const box = $("#toast"); box.textContent = window.I18N ? t(msg) : msg; box.classList.add("show");
  setTimeout(() => box.classList.remove("show"), 2200);
}
const esc = (s) => (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

/* ---- clean line icons (stroke = currentColor) ---- */
const ICONS = {
  compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5 13.5 13.5 8.5 15.5 10.5 10.5Z"/>',
  trophy: '<path d="M7 4h10v4a5 5 0 0 1-10 0Z"/><path d="M7 6H4v1.5a3 3 0 0 0 3 3"/><path d="M17 6h3v1.5a3 3 0 0 1-3 3"/><path d="M9 19h6"/><path d="M12 13v6"/>',
  book: '<path d="M5 4h10a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2Z"/><path d="M5 17.5h12"/>',
  shield: '<path d="M12 3 19 6v5c0 4-3 7-7 9-4-2-7-5-7-9V6Z"/>',
  swords: '<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" y1="19" x2="19" y2="13"/><line x1="16" y1="16" x2="20" y2="20"/><line x1="19" y1="21" x2="21" y2="19"/><polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/><line x1="5" y1="14" x2="9" y2="18"/><line x1="7" y1="17" x2="4" y2="20"/><line x1="3" y1="19" x2="5" y2="21"/>',
  chat: '<path d="M21 12a8 8 0 0 1-8 8H4l2.5-2.5A8 8 0 1 1 21 12Z"/><line x1="9" y1="10" x2="15" y2="10"/><line x1="9" y1="13.5" x2="13" y2="13.5"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><line x1="16" y1="16" x2="21" y2="21"/>',
  crown: '<path d="M4 17 3 7l5 4 4-6 4 6 5-4-1 10Z"/><path d="M5 20h14"/>',
  ghost: '<path d="M12 3a7 7 0 0 0-7 7v10l2.5-2 2.5 2 2.5-2 2.5 2 2.5-2 2.5 2V10a7 7 0 0 0-7-7Z"/><circle cx="9.5" cy="11" r=".8" fill="currentColor"/><circle cx="14.5" cy="11" r=".8" fill="currentColor"/>',
  gamepad: '<path d="M6 8h12a4 4 0 0 1 4 4v3a3 3 0 0 1-5.5 1.7L15 15H9l-1.5 1.7A3 3 0 0 1 2 15v-3a4 4 0 0 1 4-4Z"/><line x1="7.5" y1="11" x2="7.5" y2="14"/><line x1="6" y1="12.5" x2="9" y2="12.5"/><circle cx="16" cy="11.5" r=".8" fill="currentColor"/><circle cx="18" cy="13.5" r=".8" fill="currentColor"/>',
  cat: '<path d="M5 9 4 3l4 3h8l4-3-1 6a8 8 0 0 1 1 4c0 4.5-3.5 7-8 7s-8-2.5-8-7a8 8 0 0 1 1-4Z"/><circle cx="9" cy="12" r=".8" fill="currentColor"/><circle cx="15" cy="12" r=".8" fill="currentColor"/><path d="M12 15v1"/><path d="M10.5 17c.5.7 2.5.7 3 0"/>',
  owl: '<circle cx="12" cy="13" r="8"/><circle cx="9" cy="11" r="2.6"/><circle cx="15" cy="11" r="2.6"/><circle cx="9" cy="11" r=".7" fill="currentColor"/><circle cx="15" cy="11" r=".7" fill="currentColor"/><path d="M12 14.5 10.8 16h2.4Z"/><path d="M5.5 6.5 8 8.5M18.5 6.5 16 8.5"/>',
  wand: '<path d="M4 20 14 10"/><path d="m15 3 .9 2.1L18 6l-2.1.9L15 9l-.9-2.1L12 6l2.1-.9Z"/><path d="m20 11 .5 1.2L21.7 12.7l-1.2.5L20 14.4l-.5-1.2-1.2-.5 1.2-.5Z"/>',
  sparkle: '<path d="M12 3.5 13.7 9 19 10.7 13.7 12.4 12 18 10.3 12.4 5 10.7 10.3 9Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.7 2.7 2.7 15.3 0 18M12 3c-2.7 2.7-2.7 15.3 0 18"/>',
  lock: '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  check: '<path d="M5 12.5 10 17.5 19 7"/>',
  pencil: '<path d="M4 20h4L19.5 8.5l-4-4L4 16Z"/><path d="M14 6 18 10"/>',
  flame: '<path d="M12 3c.5 3 4 4.5 4 8a4 4 0 0 1-8 0c0-1.6.8-2.6 1.6-3.4.2 1.4.9 2 1.6 2 .9-1.4-.8-3.4-.8-6.6Z"/>',
  user: '<circle cx="12" cy="8" r="3.6"/><path d="M5 20a7 7 0 0 1 14 0"/>',
  doc: '<path d="M7 3h7l4 4v14H7Z"/><path d="M14 3v4h4"/><path d="M9.5 13h5M9.5 16.5h5"/>',
  play: '<path d="M8 5.5 18 12 8 18.5Z"/>',
  star: '<path d="M12 4 14.3 9.2 20 9.8 15.8 13.6 17 19.2 12 16.3 7 19.2 8.2 13.6 4 9.8 9.7 9.2Z"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M6 7l1 12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-12"/><path d="M10 11v6M14 11v6"/>',
  restore: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 4v4h4"/>',
  chevron: '<path d="M6 9l6 6 6-6"/>',
  // ---- discipline icons (line art, not emoji) ----
  brain: '<path d="M12 5a3 3 0 0 0-5.6-1.5A2.5 2.5 0 0 0 4 6c0 .6.2 1.1.5 1.5A2.5 2.5 0 0 0 4 10c0 1 .6 1.9 1.5 2.3A2.5 2.5 0 0 0 7 16a3 3 0 0 0 5 1Z"/><path d="M12 5a3 3 0 0 1 5.6-1.5A2.5 2.5 0 0 1 20 6c0 .6-.2 1.1-.5 1.5A2.5 2.5 0 0 1 20 10c0 1-.6 1.9-1.5 2.3A2.5 2.5 0 0 1 17 16a3 3 0 0 1-5 1Z"/><path d="M12 5v12"/>',
  sigma: '<path d="M17 5H7l5 7-5 7h10"/>',
  atom: '<circle cx="12" cy="12" r="1.5"/><ellipse cx="12" cy="12" rx="9" ry="3.6"/><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(120 12 12)"/>',
  flask: '<path d="M9 3h6M10 3v5L5.5 17A1.5 1.5 0 0 0 7 19.2h10A1.5 1.5 0 0 0 18.5 17L14 8V3"/><path d="M8 14h8"/>',
  leaf: '<path d="M5 19c0-8 6-14 14-14 0 8-6 14-14 14Z"/><path d="M5 19 14 10"/>',
  scroll: '<path d="M7 4h9a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H7"/><path d="M7 4a2 2 0 0 0-2 2 2 2 0 0 0 2 2h2"/><path d="M10 9h5M10 13h5"/>',
  palette: '<path d="M12 3a9 9 0 1 0 1 18c1 0 1.4-.8 1-1.6-.5-1 .2-2.4 1.4-2.4H17a4 4 0 0 0 4-4c0-5.5-4-10-9-10Z"/><circle cx="8.5" cy="11" r="1"/><circle cx="12" cy="8" r="1"/><circle cx="15.5" cy="11" r="1"/>',
  music: '<circle cx="7" cy="18" r="2.3"/><circle cx="17" cy="16" r="2.3"/><path d="M9.3 18V7l9.7-2v11"/>',
  code: '<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>',
  language: '<path d="M4 5h16v10H9l-4 4Z"/><path d="M8 9h8M8 12h6"/>',
  scales: '<path d="M12 4v16M8 20h8"/><path d="M4 8h16"/><path d="M4 8 1.8 13a2.6 2.6 0 0 0 4.4 0Z"/><path d="M20 8l-2.2 5a2.6 2.6 0 0 0 4.4 0Z"/><path d="M12 4 4 8M12 4l8 4"/>',
  calculator: '<rect x="6" y="3" width="12" height="18" rx="2"/><path d="M8.5 7h7"/><path d="M9 12h.01M12 12h.01M15 12h.01M9 16h.01M12 16h.01M15 16h.01"/>',
  planet: '<circle cx="12" cy="11" r="6"/><ellipse cx="12" cy="12" rx="11" ry="3.6" transform="rotate(-25 12 12)"/>',
};
function icon(name, size = 18) {
  return `<svg class="ic" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
}

/* ---- rank logos (SVG) ---- */
// backgrounds grouped in tiers of 3 (each group shares one shield colour):
//  Wood/Stone/Flint   -> Flint grey   (#5d6b73)
//  Coal/Iron/Bronze   -> Stone grey   (#9a9a9a)
//  Silver/Gold/Platinum -> Iron        (#aab4bf)
//  Emerald/Sapphire/Ruby -> Silver     (#c9cdd6)
//  Diamond/Radiant/Ascended -> Platinum teal (#9fd6d2)  (Ascended fill overridden to white below)
const RANK_COLORS = {
  Wood: "#5d6b73", Stone: "#5d6b73", Flint: "#5d6b73",
  Coal: "#9a9a9a", Iron: "#9a9a9a", Bronze: "#9a9a9a",
  Silver: "#aab4bf", Gold: "#aab4bf", Platinum: "#aab4bf",
  Emerald: "#c9cdd6", Sapphire: "#c9cdd6", Ruby: "#c9cdd6",
  Diamond: "#9fd6d2", Radiant: "#9fd6d2", Ascended: "#9fd6d2",
};
let _logoSeq = 0;
function shade(hex, pct) {
  const num = parseInt(hex.replace("#", ""), 16);
  let r = (num >> 16) & 255, g = (num >> 8) & 255, b = num & 255;
  const t = pct < 0 ? 0 : 255, p = Math.abs(pct) / 100;
  r = Math.round((t - r) * p + r); g = Math.round((t - g) * p + g); b = Math.round((t - b) * p + b);
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}
function textOn(hex) { // black/white text that contrasts with a colour
  const n = parseInt(hex.replace("#", ""), 16);
  const L = 0.2126 * ((n >> 16 & 255) / 255) + 0.7152 * ((n >> 8 & 255) / 255) + 0.0722 * ((n & 255) / 255);
  return L > 0.6 ? "#1a1a1a" : "#fff";
}
// true per-rank accent colour — drives borders/medallion
const RANK_ACCENT = {
  Wood: "#8a5a2b", Stone: "#9a9a9a", Flint: "#5d6b73", Coal: "#454b50", Iron: "#aab4bf",
  Bronze: "#c0844a", Silver: "#c9cdd6", Gold: "#d8b774", Platinum: "#9fd6d2", Emerald: "#2fae66",
  Sapphire: "#3b74de", Ruby: "#d6395f", Diamond: "#7fb6e6", Radiant: "#ffcf5a", Ascended: "#9fd6d2",
};
// rank logo = generated hex shield (per-rank colour) with the rank's own SVG art
// (from /ranks/<name>.svg) embedded in the centre, + a Roman-numeral tier medallion.
const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV"];
function roman(n) { return ROMAN[n - 1] || String(n); }
function rankLogo(name, size = 28, bg = null) {
  const tier = Math.max(0, RANKS.findIndex((r) => r[0] === name)) + 1;
  const id = "rl" + _logoSeq++;
  // swap the inner art for Radiant <-> Ascended
  const artName = name === "Radiant" ? "ascended" : name === "Ascended" ? "radiant" : name;
  const file = encodeURIComponent(artName.toLowerCase());

  // shield background per rank
  const BG = {
    Wood: "#5d6b73", Stone: "#5d6b73", Flint: "#5d6b73",
    Coal: "#9a9a9a", Iron: "#9a9a9a", Bronze: "#9a9a9a",
    Silver: "#c9cdd6", Gold: "#c9cdd6", Platinum: "#c9cdd6",          // silver
    Emerald: "#d8b774", Sapphire: "#d8b774", Ruby: "#d8b774",         // gold
    Diamond: "#ffffff", Radiant: "#ffffff", Ascended: "#ffffff",     // white
  };
  let c, light, dark;
  if (bg === "white") {                  // forced white shield (admin panel)
    light = "#ffffff"; c = "#fbfbfb"; dark = "#e6e6e6";
  } else if (bg) {                       // personalized: shield = chosen rank's colour
    c = RANK_ACCENT[bg] || RANK_ACCENT[name] || "#d8b774";
    light = shade(c, 58); dark = shade(c, -46);
  } else {                               // default (not linked to a rank): white shield
    light = "#ffffff"; c = "#fbfbfb"; dark = "#e6e6e6";
  }
  // border + medallion correlate with the rank's own accent colour
  const acc = RANK_ACCENT[name] || "#d8b774";
  const outer = acc, frame = shade(acc, -28), med = acc, numColor = textOn(acc);
  // gem drop-shadow: neutral, or tinted the rank colour for Radiant/Ascended
  const sCol = name === "Radiant" ? "#ffd24a" : name === "Ascended" ? "#9fd6d2" : "#000";
  const colored = sCol !== "#000";
  return `<svg class="rlogo" viewBox="0 0 100 100" width="${size}" height="${size}" aria-label="${esc(name)}">
    <defs>
      <linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${light}"/><stop offset=".5" stop-color="${c}"/><stop offset="1" stop-color="${dark}"/>
      </linearGradient>
      <filter id="${id}s" x="-100%" y="-100%" width="300%" height="300%">
        ${colored
          ? `<feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="${sCol}" flood-opacity="1" result="s1"/>
             <feDropShadow in="s1" dx="0" dy="0" stdDeviation="6" flood-color="${sCol}" flood-opacity="1"/>`
          : `<feDropShadow dx="0" dy="1.5" stdDeviation="2.2" flood-color="#000" flood-opacity="0.5"/>`}
      </filter>
    </defs>
    <path d="M50 3 L90 25 V72 L50 97 L10 72 V25 Z" fill="url(#${id})" stroke="${outer}" stroke-opacity=".7" stroke-width="3"/>
    <path d="M50 11 L83 30 V69 L50 89 L17 69 V30 Z" fill="none" stroke="${frame}" stroke-opacity=".55" stroke-width="1.5"/>
    <image href="/ranks/${file}.svg" xlink:href="/ranks/${file}.svg" x="27" y="15" width="46" height="46" preserveAspectRatio="xMidYMid meet" filter="url(#${id}s)"/>
    <circle cx="50" cy="76" r="12.5" fill="${med}" stroke="#fff" stroke-opacity=".6" stroke-width="1.5"/>
    <text x="50" y="80.5" text-anchor="middle" font-family="'Century Gothic','Jost',sans-serif" font-weight="700" font-size="13" fill="${numColor}">${roman(tier)}</text>
  </svg>`;
}

async function loadRanks() {
  try {
    const r = await api("/ranks");
    if (r && r.length) RANKS = r.map((t) => [t.name, t.ep]);
  } catch {}
}

/* ---- rank-up animation ---- */
function styleBadge(node, rank, color) {
  node.innerHTML = rank ? rankLogo(rank, 140) : "";
  node.style.color = color; // drives the glow (currentColor)
}
function countEp(from, to, dur) {
  const ep = $("#ruEp"), t0 = performance.now();
  (function step(t) {
    const k = Math.min(1, (t - t0) / dur);
    ep.textContent = Math.round(from + (to - from) * k) + " EP";
    if (k < 1) requestAnimationFrame(step);
  })(t0);
}
const RU_CHARGE = 2800;   // ms — prolonged, decelerating bar + balloon inflate
function playRankUp(toRank, fromRank) {
  const TH = Object.fromEntries(RANKS);
  const idx = RANKS.findIndex((r) => r[0] === toRank);
  if (fromRank === undefined) fromRank = idx > 0 ? RANKS[idx - 1][0] : null;
  const toEp = TH[toRank] ?? 0, fromEp = fromRank ? TH[fromRank] : 0;
  const cTo = RANK_COLORS[toRank] || "#d8b774", cFrom = fromRank ? RANK_COLORS[fromRank] : cTo;

  const o = $("#rankup"), from = $("#ruFrom"), to = $("#ruTo"), bar = $("#ruBar"), ring = $("#ruRing");
  [o._t1, o._t2, o._t3, o._t4].forEach(clearTimeout);
  from.className = "rankup__badge ru-from"; to.className = "rankup__badge ru-to";
  ring.classList.remove("go"); o.classList.remove("flash"); $("#ruSpark").innerHTML = "";
  styleBadge(from, fromRank, cFrom); styleBadge(to, toRank, cTo);
  $("#ruName").textContent = ""; $("#ruName").style.color = cTo;
  $("#ruSub").textContent = fromRank ? "A subir de rank…" : "Novo rank!";
  bar.style.transition = "none"; bar.style.width = "0%";

  o.classList.remove("show"); void o.offsetWidth; o.classList.add("show");

  // phase A: the bar fills while the CURRENT (old) rank logo inflates with it;
  // EP counts up; an ethereal swell rises underneath.
  const grow = fromRank ? from : to;
  requestAnimationFrame(() => {
    bar.style.transition = `width ${RU_CHARGE}ms cubic-bezier(.1,.7,.2,1)`;
    bar.style.width = "100%";
    grow.classList.add("inflate");
  });
  countEp(fromEp, toEp, RU_CHARGE);
  playCharge(RU_CHARGE);

  // phase B: at the end the charged logo POPS / explodes
  o._t1 = setTimeout(() => {
    grow.classList.remove("inflate"); void grow.offsetWidth;
    o.classList.add("flash"); ring.classList.add("go");
    spawnSparks(cTo); playPop();
    if (fromRank) {
      from.classList.add("boom");
      // phase C: the NEW rank emerges only after the old one bursts
      o._t2 = setTimeout(() => {
        to.classList.add("show");
        $("#ruName").textContent = toRank;
        $("#ruSub").textContent = "Novo rank! — toca para continuar";
        playVictory(toRank);
      }, 380);
    } else {
      grow.classList.add("pop");
      $("#ruName").textContent = toRank;
      $("#ruSub").textContent = "Novo rank! — toca para continuar";
      playVictory(toRank);
    }
  }, RU_CHARGE);
  o._t3 = setTimeout(() => o.classList.remove("flash"), RU_CHARGE + 300);
  // stays on screen until the user clicks (no auto-dismiss)
  o.onclick = () => o.classList.remove("show");
}
function spawnSparks(color) {
  const box = $("#ruSpark"); box.innerHTML = "";
  for (let i = 0; i < 28; i++) {
    const a = (Math.PI * 2 * i) / 28 + Math.random() * 0.3;
    const dist = 100 + Math.random() * 110;
    const s = document.createElement("span");
    s.className = "spark";
    s.style.background = Math.random() < 0.5 ? color : "#fff";
    s.style.setProperty("--dx", `${Math.cos(a) * dist}px`);
    s.style.setProperty("--dy", `${Math.sin(a) * dist}px`);
    s.style.setProperty("--r", `${Math.random() * 540}deg`);
    s.style.animationDelay = `${Math.random() * 0.12}s`;
    box.appendChild(s);
  }
}

/* ---- synthesized audio (no asset files) ---- */
let _ruAc = null;
function ruAudio() {
  try {
    if (!_ruAc) { const C = window.AudioContext || window.webkitAudioContext; _ruAc = new C(); }
    if (_ruAc.state === "suspended") _ruAc.resume();
    return _ruAc;
  } catch { return null; }
}
// master bus with a hard limiter — nothing can ever spike past this
function ruBus(a) {
  if (a._bus) return a._bus;
  const master = a.createGain(); master.gain.value = 0.4;
  const comp = a.createDynamicsCompressor();
  comp.threshold.value = -16; comp.knee.value = 24; comp.ratio.value = 16;
  comp.attack.value = 0.002; comp.release.value = 0.25;
  master.connect(comp).connect(a.destination);
  a._bus = master; return master;
}
// bounded multi-tap "space" (NO feedback loop -> cannot run away)
function ruSpace(a) {
  if (a._space) return a._space;
  const inp = a.createGain(), bus = ruBus(a);
  inp.connect(bus); // dry
  [0.07, 0.13, 0.19, 0.27].forEach((dt, i) => {
    const d = a.createDelay(1), g = a.createGain();
    d.delayTime.value = dt; g.gain.value = 0.22 * Math.pow(0.68, i);
    inp.connect(d).connect(g).connect(bus);
  });
  a._space = inp; return inp;
}
// soft bell / glockenspiel note with long shimmering tail (sine partials)
function ruBell(a, f, t, dur, vol) {
  const space = ruSpace(a), g = a.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(vol, t + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  [[1, 1], [2, 0.4], [3, 0.18], [4.2, 0.08]].forEach(([mult, amp]) => {
    const o = a.createOscillator(), pg = a.createGain();
    o.type = "sine"; o.frequency.value = f * mult; pg.gain.value = amp;
    o.connect(pg).connect(g); o.start(t); o.stop(t + dur + 0.1);
  });
  g.connect(space);
}
// ethereal swell: a soft, slowly brightening pad chord that rises as the bar fills
function playCharge(durMs) {
  const a = ruAudio(); if (!a) return;
  const t = a.currentTime, T = durMs / 1000, space = ruSpace(a);
  const bed = a.createGain(); bed.connect(space);
  bed.gain.setValueAtTime(0.0001, t);
  bed.gain.exponentialRampToValueAtTime(0.10, t + T * 0.45);
  bed.gain.exponentialRampToValueAtTime(0.16, t + T * 0.95);
  bed.gain.exponentialRampToValueAtTime(0.0001, t + T + 0.4);
  [196, 261.63, 329.63, 392].forEach((f, i) => {        // G3 C4 E4 G4 — warm major pad
    const o = a.createOscillator(), lp = a.createBiquadFilter(), og = a.createGain();
    o.type = "triangle"; o.frequency.value = f; o.detune.value = i % 2 ? 5 : -5;
    lp.type = "lowpass"; lp.frequency.setValueAtTime(600, t); lp.frequency.exponentialRampToValueAtTime(2600, t + T);
    og.gain.value = 0.25 - i * 0.03;
    o.connect(lp).connect(og).connect(bed); o.start(t); o.stop(t + T + 0.5);
  });
  // slow shimmer that ascends with the charge
  const sh = a.createOscillator(), sg = a.createGain();
  sh.type = "sine"; sh.frequency.setValueAtTime(880, t); sh.frequency.exponentialRampToValueAtTime(1760, t + T);
  sg.gain.setValueAtTime(0.0001, t); sg.gain.exponentialRampToValueAtTime(0.05, t + T * 0.9); sg.gain.exponentialRampToValueAtTime(0.0001, t + T + 0.1);
  sh.connect(sg).connect(space); sh.start(t); sh.stop(t + T + 0.12);
}
// the "pop": a soft airy chime burst (no harshness) — a bright bell + gentle whoosh
function playPop() {
  const a = ruAudio(); if (!a) return;
  const t = a.currentTime;
  ruBell(a, 1567.98, t, 1.4, 0.22);   // G6 sparkle
  const len = Math.floor(a.sampleRate * 0.35), buf = a.createBuffer(1, len, a.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.sin((Math.PI * i) / len);  // soft swell
  const n = a.createBufferSource(); n.buffer = buf;
  const bp = a.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 5000; bp.Q.value = 0.7;
  const g = a.createGain(); g.gain.value = 0.18;
  n.connect(bp).connect(g).connect(ruSpace(a)); n.start(t); n.stop(t + 0.36);
}
// each rank gets its own key: root climbs ~a whole tone per rank (brighter as you ascend)
function ruRoot(rank) {
  const tier = Math.max(0, RANKS.findIndex((r) => r[0] === rank));
  return 130.81 * Math.pow(2, (tier * 2) / 12); // C3 up by whole tones
}
// reveal: one warm, accomplished MAJOR chord in the rank's key — swell, hold, fade over 3s
function playVictory(rank) {
  const a = ruAudio(); if (!a) return;
  const t = a.currentTime, DUR = 3.0, space = ruSpace(a);
  const root = ruRoot(rank);
  // major triad + octave, just intonation: sub-root, root, M3, P5, octave, M3-above
  const voices = [root * 0.5, root, root * 1.25, root * 1.5, root * 2, root * 2.5];
  const chord = a.createGain(); chord.connect(space);
  chord.gain.setValueAtTime(0.0001, t);
  chord.gain.linearRampToValueAtTime(0.3, t + 0.18);    // gentle swell in
  chord.gain.setValueAtTime(0.3, t + 0.7);              // hold
  chord.gain.exponentialRampToValueAtTime(0.0001, t + DUR); // fade out
  voices.forEach((f, i) => {
    const o = a.createOscillator(), o2 = a.createOscillator(), lp = a.createBiquadFilter(), vg = a.createGain();
    o.type = "triangle"; o2.type = "sine"; o.frequency.value = f; o2.frequency.value = f; o2.detune.value = i % 2 ? 6 : -6;
    lp.type = "lowpass"; lp.frequency.value = 2800;
    vg.gain.value = 0.72 - i * 0.07;                     // upper voices softer
    o.connect(lp); o2.connect(lp); lp.connect(vg).connect(chord);
    o.start(t); o2.start(t); o.stop(t + DUR + 0.1); o2.stop(t + DUR + 0.1);
  });
}
const playDing = playVictory;  // back-compat alias

/* ---- minimal, safe markdown -> html (escape first, then format) ---- */
function inlineMd(t) {
  return t
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
    .replace(/(^|[^\w])_([^_\n]+)_(?!\w)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function mdToHtml(src) {
  const lines = esc(src).split("\n");
  const out = [];
  let para = [], list = null, inCode = false, code = [];
  const flushP = () => { if (para.length) { out.push("<p>" + inlineMd(para.join(" ")) + "</p>"); para = []; } };
  const flushL = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) { out.push("<pre><code>" + code.join("\n") + "</code></pre>"); code = []; inCode = false; }
      else { flushP(); flushL(); inCode = true; }
      continue;
    }
    if (inCode) { code.push(line); continue; }
    if (!line.trim()) { flushP(); flushL(); continue; }
    let m;
    if ((m = line.match(/^\s*#{1,3}\s+(.*)$/))) { flushP(); flushL(); out.push("<h4>" + inlineMd(m[1]) + "</h4>"); continue; }
    if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { flushP(); if (list !== "ul") { flushL(); out.push("<ul>"); list = "ul"; } out.push("<li>" + inlineMd(m[1]) + "</li>"); continue; }
    if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) { flushP(); if (list !== "ol") { flushL(); out.push("<ol>"); list = "ol"; } out.push("<li>" + inlineMd(m[1]) + "</li>"); continue; }
    flushL(); para.push(line);
  }
  if (inCode) out.push("<pre><code>" + code.join("\n") + "</code></pre>");
  flushP(); flushL();
  return out.join("");
}

/* ===================================================================== */
/* AUTH                                                                  */
/* ===================================================================== */
let authMode = "login";
$("#segLogin").onclick = () => setAuthMode("login");
$("#segReg").onclick = () => setAuthMode("reg");
function setAuthMode(m) {
  authMode = m;
  $("#segLogin").classList.toggle("is-active", m === "login");
  $("#segReg").classList.toggle("is-active", m === "reg");
  const reg = m === "reg";
  $("#afName").style.display = reg ? "block" : "none";
  $("#afEmail").style.display = reg ? "block" : "none";
  $("#afId").style.display = reg ? "none" : "block";
  $("#afEmail").required = reg; $("#afId").required = !reg;
  $("#afSubmit").textContent = reg ? t("Criar conta") : t("Entrar");
}

$("#authForm").onsubmit = async (e) => {
  e.preventDefault();
  $("#afErr").textContent = "";
  REMEMBER = $("#afRemember").checked;
  const password = $("#afPass").value;
  try {
    let identifier;
    if (authMode === "reg") {
      const email = $("#afEmail").value;
      await api("/auth/register", { method: "POST", body: { email, password, display_name: $("#afName").value || t("Estudante") } });
      identifier = email;
    } else {
      identifier = $("#afId").value;
    }
    store.clear();
    const tok = await api("/auth/login", { method: "POST", body: { identifier, password } });
    saveTokens(tok.access, tok.refresh);
    await boot();
  } catch (err) { $("#afErr").textContent = t(err.message); }
};

$("#logout").onclick = () => { store.clear(); location.reload(); };

$("#afEye").onclick = () => {
  const p = $("#afPass"), show = p.type === "password";
  p.type = show ? "text" : "password";
  $("#afEye").classList.toggle("on", show);
};

/* right-side account rail: collapsed (avatar + friend avatars + expand arrow)
   <-> expanded (profile + friends + red exit). Bottom arrow toggles; no close X. */
let _railOpen = localStorage.getItem("mt_rail") === "1";
function setRail(open) {
  _railOpen = open;
  localStorage.setItem("mt_rail", open ? "1" : "0");
  renderRail();
}
function _initial(name) { return (name || "?").trim().charAt(0).toUpperCase() || "?"; }

async function renderRail() {
  const rail = $("#rail"); if (!rail || !USER) return;
  rail.classList.toggle("open", _railOpen);
  const p = window._prog || { rank: (RANKS[0] || ["Wood"])[0], xp: 0, streak: 0 };
  const top = $("#railTop"), fr = $("#railFriends");
  if (_railOpen) {
    top.innerHTML = `<button class="umprofile" id="umProfileBtn">
      ${rankLogo(p.rank, 52, USER.background)}
      <span class="umprofile__info">
        <b>${esc(USER.display_name)}</b>
        <span class="muted" style="display:inline-flex;align-items:center;gap:5px;font-size:13px">${p.rank} · ${p.xp} EP · ${p.streak}${icon("flame", 13)}</span>
        <span class="muted" style="font-size:12.5px" title="${t("Objetivo diário: 5 respostas")}">🎯 ${t("Hoje")}: ${Math.min(p.answers_today || 0, 5)}/5${(p.answers_today || 0) >= 5 ? " ✓" : ""}</span>
        <span class="umprofile__link">${t("Ver perfil →")}</span>
      </span></button>`;
    $("#umProfileBtn").onclick = () => go("profile");
    fr.innerHTML = friendsCard();
    mountFriends(fr.querySelector(".frcard"));
    $("#logout").style.display = "";
  } else {
    top.innerHTML = `<div class="rail__avatar" title="${esc(USER.display_name)}" style="position:relative">${rankLogo(p.rank, 44, USER.background)}<span class="nav__dot" id="railDm" ${!(window._unread || {}).total ? "hidden" : ""} style="top:-2px;right:-4px">✉</span></div>
      ${p.streak ? `<div class="rail__streak" title="${t("Sequência: {n} certas seguidas", { n: p.streak })}">${p.streak}${icon("flame", 12)}</div>` : ""}`;
    let d = { friends: [] };
    try { d = await api("/friends"); } catch {}
    fr.innerHTML = d.friends.length
      ? d.friends.map((f) => `<span class="rail__friend" title="${esc(f.display_name)}">${f.avatar && AVATAR_KEYS.includes(f.avatar) ? icon(f.avatar, 22) : esc(_initial(f.display_name))}</span>`).join("")
      : `<div class="rail__noav" title="${t("Sem amigos")}">${icon("user", 18)}</div>`;
    $("#logout").style.display = "none";
  }
}
// click anywhere on the collapsed rail to open; click outside to close
$("#rail").onclick = (e) => { if (!_railOpen) { e.stopPropagation(); setRail(true); } };
document.addEventListener("click", (e) => { if (_railOpen && !$("#rail").contains(e.target)) setRail(false); });

async function boot() {
  try {
    USER = await api("/me");
  } catch { TOKEN = ""; localStorage.removeItem("mt_token"); $("#auth").style.display = "grid"; $("#app").style.display = "none"; return; }
  $("#auth").style.display = "none";
  $("#app").style.display = "block";
  $("#navAdmin").style.display = USER.role === "admin" ? "block" : "none";
  await loadSubjects();
  await loadRanks();
  await refreshChip();
  go("tutor");
}

async function loadSubjects() {
  try { SUBJECTS = await api("/subjects"); } catch { SUBJECTS = []; }
  if (SUBJECTS.length && !SUBJECTS.some((s) => s.key === SUBJECT)) SUBJECT = SUBJECTS[0].key;
  const sw = $("#subjSel");
  const cur = SUBJECTS.find((s) => s.key === SUBJECT) || SUBJECTS[0] || { name: "—", icon: "" };
  sw.innerHTML = `
    <button class="subjsw__btn" id="subjBtn">${subjectIcon(cur.icon, 16)}<span>${esc(cur.name)}</span>${icon("chevron", 14)}</button>
    <div class="subjsw__menu" id="subjMenu" hidden>${SUBJECTS.map((s) => `<button class="subjsw__item ${s.key === SUBJECT ? "is-active" : ""}" data-key="${s.key}">${subjectIcon(s.icon, 16)}<span>${esc(s.name)}</span></button>`).join("")}</div>`;
  $("#subjBtn").onclick = (e) => { e.stopPropagation(); const m = $("#subjMenu"); m.hidden = !m.hidden; };
  $("#subjMenu").querySelectorAll(".subjsw__item").forEach((b) => (b.onclick = () => {
    $("#subjMenu").hidden = true;
    if (b.dataset.key !== SUBJECT) { SUBJECT = b.dataset.key; localStorage.setItem("mt_subject", SUBJECT); tutorConcepts = []; CONCEPT_NAMES = {}; preloadConcepts(); }
    loadSubjects(); refreshChip(); go(CURRENT_VIEW);
  }));
  if (!window._subjOutsideWired) {
    document.addEventListener("click", () => { const m = $("#subjMenu"); if (m && !m.hidden) m.hidden = true; });
    window._subjOutsideWired = true;
  }
}

async function refreshChip() {
  let p = { rank: (RANKS[0] || ["Wood"])[0], xp: 0, streak: 0 };
  try { p = await api(`/me/progress/${SUBJECT}`); } catch {}
  window._prog = p;
  await renderRail();
  updateDuelBadge();
  checkAchievements();
}

// toast newly unlocked achievements (first run just seeds the snapshot)
async function checkAchievements() {
  try {
    const list = await api("/me/achievements");
    const prev = new Set(JSON.parse(localStorage.getItem("mt_ach") || "[]"));
    const unlocked = list.filter((a) => a.unlocked).map((a) => a.key);
    if (prev.size) {
      unlocked.filter((k) => !prev.has(k)).forEach((k) => {
        const meta = ACH_META[k];
        if (meta) { toast(`🏆 ${t("Conquista desbloqueada")}: ${t(meta[1])}`); try { playPop(); } catch {} }
      });
    }
    localStorage.setItem("mt_ach", JSON.stringify(unlocked));
  } catch {}
}

// red counter on the Duelos nav item: invites + duels waiting on me
setInterval(() => { if (USER) updateDuelBadge(); }, 30000);  // keep it fresh while browsing
async function updateDuelBadge() {
  let n = 0;
  try {
    const ds = await api("/duels");
    n = ds.filter((d) => d.needs_my_action && ["pending", "setup", "active"].includes(d.status)).length;
  } catch {}
  const dot = $("#duelDot");
  if (dot) { dot.hidden = !n; dot.textContent = n > 9 ? "9+" : n; }
  try {
    const prev = (window._unread || {}).total || 0;
    window._unread = await api("/messages/unread");
    const dmDot = $("#railDm");
    if (dmDot) dmDot.hidden = !window._unread.total;
    if (window._unread.total > prev) renderFriends();  // live-update visible friend lists
  } catch {}
}

/* ===================================================================== */
/* NAV                                                                   */
/* ===================================================================== */
$("#nav").addEventListener("click", (e) => {
  const b = e.target.closest(".nav__i"); if (!b) return;
  go(b.dataset.v);
});
function go(view) {
  if (view !== "duels") { stopDuelPolling(); stopMatchmaking(); }  // leaving duels kills the pollers
  CURRENT_VIEW = view;
  document.querySelectorAll(".nav__i").forEach((b) => b.classList.toggle("is-active", b.dataset.v === view));
  ({ tutor: vTutor, practice: vPractice, materials: vMaterials, duels: vDuels, profile: vProfile, admin: vAdmin }[view])();
}

/* ===================================================================== */
/* TUTOR                                                                 */
/* ===================================================================== */
let tutorSid = null, tutorConcepts = [], PENDING_MATERIAL = null, PENDING_PRACTICE = null, PENDING_REVIEW = false;
async function vTutor() {
  const v = $("#view");
  v.innerHTML = `
    <div class="view__head"><h1>${t("Tutor Socrático")}</h1><p>${t("Orienta-te a pensar — nunca dá a resposta. As conversas ficam guardadas.")}</p></div>
    <div id="annBox"></div>
    <div id="revBanner"></div>
    <div class="tutor">
      <aside class="chats">
        <button class="btn btn--sm" id="tNew" style="width:100%">${t("+ Nova conversa")}</button>
        <div class="chats__list" id="chatList"></div>
      </aside>
      <div class="card">
        <div class="row" style="margin-bottom:10px">
          <button class="btn btn--ghost btn--sm" id="tPick">${icon("book", 14)} ${t("Escolher material")}</button>
          <span id="tMat" class="muted" style="font-size:13px"></span>
        </div>
        <div class="chat" id="chat"></div>
        <form class="chat__in" id="chatForm">
          <input id="chatText" placeholder="${t("Escreve ao tutor…")}" autocomplete="off" />
          <button class="btn" id="chatSend">${t("Enviar")}</button>
        </form>
      </div>
    </div>`;
  $("#tNew").onclick = () => openMaterialPicker((id) => newTutor(id));
  $("#tPick").onclick = () => openMaterialPicker((id) => newTutor(id));
  $("#chatForm").onsubmit = sendTutor;
  renderAnnouncements();
  renderReviewBanner();
  await loadChatList();
  if (PENDING_MATERIAL) {  // arrived from Materiais → ground on that material
    const id = PENDING_MATERIAL; PENDING_MATERIAL = null;
    await newTutor(id);
    return;
  }
  const sessions = window._chats || [];
  if (sessions.length) await openChat(sessions[0].id);
  else await newTutor(null);
}
function setTutorMat(title) { $("#tMat").textContent = title ? `· ${title}` : `· ${t("Tópico livre")}`; }

async function loadChatList() {
  let sessions = [];
  try { sessions = await api("/tutor/sessions"); } catch {}
  window._chats = sessions;
  $("#chatList").innerHTML = sessions.length
    ? sessions.map((s) => `<div class="chatrow">
        <button class="chatitem ${s.id === tutorSid ? "is-active" : ""}" data-id="${s.id}">${esc(s.title || t("Conversa"))}</button>
        <button class="chatdel" data-ren="${s.id}" title="${t("Mudar nome")}">${icon("pencil", 13)}</button>
        <button class="chatdel" data-del="${s.id}" title="${t("Apagar conversa")}">${icon("trash", 14)}</button>
      </div>`).join("")
    : `<p class="muted" style="font-size:13px;padding:8px">${t("Sem conversas ainda.")}</p>`;
  $("#chatList").querySelectorAll(".chatitem").forEach((b) => (b.onclick = () => openChat(b.dataset.id)));
  $("#chatList").querySelectorAll("[data-ren]").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); startRenameChat(b.dataset.ren); }));
  $("#chatList").querySelectorAll("[data-del]").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); deleteChat(b.dataset.del); }));
}

// swap a chat row for an inline input; Enter/blur saves, Esc cancels
function startRenameChat(id) {
  const row = $(`#chatList .chatitem[data-id="${id}"]`); if (!row) return;
  const cur = row.textContent;
  const inp = el(`<input class="chatitem chatitem--edit" maxlength="120">`);
  inp.value = cur;
  row.replaceWith(inp); inp.focus(); inp.select();
  const save = async () => {
    const val = inp.value.trim();
    if (val && val !== cur) {
      try { await api(`/tutor/sessions/${id}`, { method: "PATCH", body: { title: val } }); toast(t("Nome alterado")); }
      catch (e) { toast(e.message); }
    }
    loadChatList();
  };
  inp.onblur = save;
  inp.onkeydown = (ev) => {
    if (ev.key === "Enter") inp.blur();
    else if (ev.key === "Escape") { inp.onblur = null; loadChatList(); }
  };
}

async function deleteChat(id) {
  if (!confirm(t("Apagar esta conversa? Fica oculta e é recuperável durante 6 meses (no painel de admin); depois é apagada permanentemente."))) return;
  try {
    await api(`/tutor/sessions/${id}`, { method: "DELETE" });
    toast(t("Conversa apagada"));
    if (id === tutorSid) { tutorSid = null; $("#chat").innerHTML = ""; }
    await loadChatList();
    const sessions = window._chats || [];
    if (id === tutorSid || !tutorSid) {
      if (sessions.length) await openChat(sessions[0].id);
      else await newTutor(null);
    }
  } catch (e) { toast(e.message); }
}

async function newTutor(materialId = null) {
  try {
    const s = await api("/tutor/sessions", { method: "POST", body: { subject: SUBJECT, material: materialId } });
    tutorSid = s.id;
    $("#chat").innerHTML = "";
    setTutorMat(materialId ? s.title : null);
    addMsg("bot", materialId
      ? t("Olá — vamos explorar **{title}**. Não dou respostas; ajudo-te a chegar lá. Por onde começamos?", { title: esc(s.title) })
      : t("Olá — sou o teu tutor na **RankUp**. Não dou respostas; ajudo-te a encontrá-las. O que queres explorar?"));
    showStarters(!!materialId);
    await loadChatList();
  } catch (e) { toast(e.message); }
}

async function openChat(id) {
  tutorSid = id;
  $("#chat").innerHTML = "";
  const meta = (window._chats || []).find((s) => s.id === id);
  setTutorMat(meta && meta.material_id ? meta.title : null);
  try {
    const msgs = await api(`/tutor/sessions/${id}`);
    if (!msgs.length) { addMsg("bot", t("Olá — sou o teu tutor na **RankUp**. O que queres explorar?")); showStarters(!!(meta && meta.material_id)); }
    else msgs.forEach((m) => addMsg(m.role === "assistant" ? "bot" : "user", m.content));
  } catch (e) { toast(e.message); }
  document.querySelectorAll(".chatitem").forEach((b) => b.classList.toggle("is-active", b.dataset.id === id));
}

// live text filter over a card grid: hides non-matching cards, keeps a count label
function wireGridSearch(inputSel, gridSel, countSel, noun) {
  const input = $(inputSel), grid = $(gridSel), count = $(countSel);
  if (!input || !grid) return;
  const apply = () => {
    const q = input.value.trim().toLowerCase();
    let shown = 0;
    grid.querySelectorAll(".mkt-card").forEach((c) => {
      const hit = !q || (c.dataset.search || "").includes(q);
      c.style.display = hit ? "" : "none";
      if (hit) shown++;
    });
    if (count) count.textContent = q ? `${shown} ${noun}` : "";
  };
  input.oninput = apply;
  apply();
}

// quick-start suggestion chips shown on an empty chat
function showStarters(hasMat) {
  const opts = (hasMat
    ? ["Quais são as ideias principais?", "Faz-me uma pergunta sobre isto", "Dá-me um exemplo do dia a dia", "Porque é que isto é importante?"]
    : ["Ajuda-me a preparar um teste", "Explora um conceito comigo", "Testa o que eu já sei", "Por onde devo começar?"]).map((s) => t(s));
  const chat = $("#chat"); if (!chat) return;
  const box = el(`<div class="starters">${opts.map((o) => `<button type="button" class="starter">${o}</button>`).join("")}</div>`);
  chat.appendChild(box);
  box.querySelectorAll(".starter").forEach((b) => (b.onclick = () => {
    $("#chatText").value = b.textContent;
    box.remove();
    $("#chatForm").requestSubmit();
  }));
}

function addMsg(who, text) {
  const inner = who === "bot" ? mdToHtml(text) : esc(text);
  const m = el(`<div class="msg msg--${who}"><div class="msg__av">${who === "bot" ? icon("sparkle", 16) : icon("user", 16)}</div><div class="msg__b">${inner}</div></div>`);
  const chat = $("#chat");
  if (chat) { chat.appendChild(m); chat.scrollTop = chat.scrollHeight; }  // user may have left the view mid-flight
  return m.querySelector(".msg__b");
}

async function sendTutor(e) {
  e.preventDefault();
  const txt = $("#chatText").value.trim(); if (!txt || !tutorSid) return;
  $("#chat").querySelectorAll(".starters").forEach((s) => s.remove());
  $("#chatText").value = ""; $("#chatSend").disabled = true;
  addMsg("user", txt);
  const bubble = addMsg("bot", "");
  bubble.innerHTML = '<span class="dots"></span>';
  let first = true, acc = "";
  try {
    const res = await api(`/tutor/sessions/${tutorSid}/messages`, { method: "POST", body: { text: txt }, stream: true });
    if (!res.ok) throw new Error("erro " + res.status);
    await readSSE(res, {
      token: (d) => { first = false; acc += d.text; bubble.innerHTML = mdToHtml(acc); $("#chat").scrollTop = $("#chat").scrollHeight; },
      done: () => {},
    });
    if (first) bubble.textContent = t("(sem resposta)");
  } catch (err) {
    bubble.textContent = "⚠ " + err.message;
  } finally { $("#chatSend").disabled = false; refreshChip(); loadChatList(); }
}

async function readSSE(res, handlers) {
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      let ev = "message", data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) ev = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data && handlers[ev]) handlers[ev](JSON.parse(data));
    }
  }
}

/* ===================================================================== */
/* PRACTICE                                                              */
/* ===================================================================== */
async function vPractice() {
  const v = $("#view");
  const teacher = USER.role === "teacher" || USER.role === "admin";
  v.innerHTML = `
    <div class="view__head"><h1>${t("Ranked")}</h1><p>${t("Escolhe um teste do marketplace. EP ganha-se pelo raciocínio, não só pela resposta certa.")}</p></div>
    <div id="revBanner"></div>
    <div class="card lbcard" id="epLb" style="display:none"></div>
    ${teacher ? `<div class="card" id="classCard" style="display:none"></div>` : ""}
    <div class="card">
      <div class="row" style="justify-content:space-between"><h3 style="font-size:16px">${t("Marketplace de testes")}</h3>
        ${teacher ? `<div class="row"><button class="btn btn--ghost btn--sm" id="genTest">${icon("sparkle", 15)} ${t("Gerar com IA")}</button><button class="btn btn--sm" id="newTest">${icon("plus", 15)} ${t("Criar teste")}</button></div>` : ""}</div>
      <div id="newTestForm"></div>
      <div class="toolrow"><input id="testSearch" class="searchbar" placeholder="${t("Procurar teste…")}" autocomplete="off"><span class="muted" id="testCount"></span></div>
      <div id="tests" class="mkt-grid" style="margin-top:12px">…</div>
    </div>
    <div id="run"></div>`;
  if (teacher) {
    $("#newTest").onclick = () => {
      const f = $("#newTestForm");
      if (f.innerHTML) { f.innerHTML = ""; return; }
      f.innerHTML = `<div class="mgbox" style="margin-top:10px">
        <label class="fld"><span class="label">${t("Título do teste")}</span><input id="ntTitle" placeholder="${t("ex: Ética — fundamentos")}"></label>
        <label class="fld"><span class="label">${t("Descrição")}</span><input id="ntDesc" placeholder="${t("breve descrição")}"></label>
        <label class="remember" style="margin:4px 0"><input type="checkbox" id="ntPub"> ${t("Tornar pública já")}</label>
        <div class="row"><button class="btn btn--sm" id="ntCreate">${t("Criar")}</button><button class="btn btn--ghost btn--sm" id="ntCancel">${t("Cancelar")}</button></div></div>`;
      $("#ntCancel").onclick = () => { f.innerHTML = ""; };
      $("#ntCreate").onclick = async () => {
        try {
          await api(`/subjects/${SUBJECT}/tests`, { method: "POST", body: { title: $("#ntTitle").value.trim(), description: $("#ntDesc").value.trim(), is_public: $("#ntPub").checked } });
          f.innerHTML = ""; toast(t("Teste criado")); renderTests(teacher);
        } catch (e) { toast(e.message); }
      };
    };
    $("#genTest").onclick = () => {
      const f = $("#newTestForm");
      if (f.dataset.mode === "gen") { f.innerHTML = ""; f.dataset.mode = ""; return; }
      f.dataset.mode = "gen";
      f.innerHTML = `<div class="mgbox" style="margin-top:10px">
        <b>${icon("sparkle", 16)} ${t("Gerar teste com IA")}</b>
        <label class="fld"><span class="label">${t("Tópico")}</span><input id="gTopic" placeholder="${t("ex: ética de Kant")}"></label>
        <div class="row">
          <label class="fld"><span class="label">${t("Nº de perguntas")}</span><select id="gCount" style="max-width:130px">${[3,5,8,10].map(n=>`<option ${n===3?"selected":""}>${n}</option>`).join("")}</select></label>
          <label class="fld"><span class="label">${t("Dificuldade")}</span><select id="gDiff" style="max-width:130px">${[[1,t("Fácil")],[2,t("Médio")],[3,t("Difícil")]].map(([v,n])=>`<option value="${v}" ${v===2?"selected":""}>${n}</option>`).join("")}</select></label>
          <label class="fld"><span class="label">${t("Tema")}</span><select id="gConcept" style="max-width:200px"></select></label>
        </div>
        <div class="row"><button class="btn btn--sm" id="gGo">${t("Gerar")}</button><button class="btn btn--ghost btn--sm" id="gCancel">${t("Cancelar")}</button></div></div>`;
      $("#gCancel").onclick = () => { f.innerHTML = ""; f.dataset.mode = ""; };
      (async () => {
        let cs = [];
        try { cs = (await api(`/subjects/${SUBJECT}/graph`)).concepts; } catch {}
        $("#gConcept").innerHTML = `<option value="">${t("tema automático")}</option>` + cs.map((c) => `<option value="${c.key}">${esc(c.name)}</option>`).join("");
      })();
      $("#gGo").onclick = async () => {
        const topic = $("#gTopic").value.trim();
        if (!topic) return toast(t("Escreve um tópico"));
        f.innerHTML = ""; f.dataset.mode = "";
        const ph = el(`<div class="mkt-card mkt-card--gen"><div class="gen-shimmer"></div><div class="gen-shimmer" style="width:70%"></div><div class="gen-shimmer" style="width:40%"></div><p class="muted" style="font-size:13px;display:flex;align-items:center;gap:6px">${icon("sparkle", 15)} ${t("A IA está a criar o teste…")}</p></div>`);
        $("#tests").prepend(ph);
        try {
          const gen = await api(`/subjects/${SUBJECT}/tests/generate`, { method: "POST", body: { topic, count: +$("#gCount")?.value || 3, difficulty: +$("#gDiff")?.value || 2, concept: $("#gConcept")?.value || null } });
          toast(t("Teste gerado: {n} pergunta(s)", { n: gen.question_count }));
          await renderTests(teacher);
          const card = $(`#tests .mkt-card`); if (card) card.classList.add("gen-in");
        } catch (e) { toast(e.message); ph.remove(); }
      };
    };
  }
  renderTests(teacher);
  renderEpLeaderboard();
  renderReviewBanner();
  if (teacher) renderClassView();
  if (PENDING_PRACTICE) { const c = PENDING_PRACTICE; PENDING_PRACTICE = null; startFocusedPractice(c); }
  if (PENDING_REVIEW) { PENDING_REVIEW = false; startReviewSession(); }
}

// teacher-only radar: class-wide weakest topics for the active discipline
async function renderClassView() {
  const box = $("#classCard"); if (!box) return;
  let topics = [];
  try { topics = await api(`/teacher/class-topics/${SUBJECT}`); } catch {}
  if (!topics.length) return;
  box.style.display = "";
  box.innerHTML = `
    <h3 style="font-size:16px;margin-bottom:4px">${icon("compass", 16)} ${t("Visão da turma")}</h3>
    <p class="muted" style="font-size:13px;margin-bottom:10px">${t("Temas com pior mestria média — onde a turma precisa de reforço.")}</p>
    <table><tr><th>${t("Tema")}</th><th>${t("Alunos")}</th><th>${t("Mestria média")}</th></tr>
    ${topics.map((tp) => {
      const pct = Math.round(tp.avg_mastery * 100);
      return `<tr><td>${esc(tp.topic)}</td><td>${tp.students}</td><td><b style="color:${pct < 40 ? "var(--red)" : pct < 70 ? "#8a6d1d" : "var(--green)"}">${pct}%</b></td></tr>`;
    }).join("")}</table>`;
}

// per-subject EP ladder shown on the Ranked view
async function renderEpLeaderboard() {
  let lb = [];
  try { lb = await api(`/leaderboards/${SUBJECT}?limit=10`); } catch {}
  const box = $("#epLb");
  if (!box || !lb.length) return;
  const subjName = (SUBJECTS.find((s) => s.key === SUBJECT) || {}).name || SUBJECT;
  box.style.display = "";
  const row = (r, pos, me) => `
      <div class="lbrow ${me ? "is-me" : ""}">
        <span class="lbrow__pos">${pos}</span>
        ${userAvatar(r, 24)}
        ${rankLogo(r.rank, 26)}
        <span class="lbrow__name">${esc(r.display_name)}</span>
        <span class="lbrow__streak">${r.streak}${icon("flame", 12)}</span>
        <span class="lbrow__ep">${r.xp} EP</span>
      </div>`;
  let html = lb.map((r, i) => row(r, i + 1, r.display_name === USER.display_name)).join("");
  if (!lb.some((r) => r.display_name === USER.display_name)) {
    try {
      const me = await api(`/leaderboards/${SUBJECT}/me`);
      if (me.position) html += `<div class="lbrow lbrow--gap">…</div>` + row({ ...me, display_name: USER.display_name }, me.position, true);
    } catch {}
  }
  box.innerHTML = `
    <h3 style="font-size:16px;margin-bottom:10px">${icon("trophy", 16)} ${t("Classificação")} · ${esc(subjName)}</h3>
    <div class="lbrows">${html}</div>`;
}

async function renderTests(teacher) {
  let tests = [], stats = {};
  try { tests = await api(`/subjects/${SUBJECT}/tests`); } catch {}
  if (teacher) {
    try { (await api(`/teacher/test-stats/${SUBJECT}`)).forEach((s) => (stats[s.test_id] = s)); } catch {}
  }
  if (!tests.length) { $("#tests").innerHTML = `<p class="muted">${teacher ? t("Ainda não há testes — cria um.") : t("Ainda não há testes.")}</p>`; return; }
  $("#tests").innerHTML = tests.map((ts) => `
    <div class="mkt-card" data-search="${esc(`${ts.title} ${ts.description || ""} ${ts.author || ""}`.toLowerCase())}">
      <div class="mkt-card__top">
        <span class="mkt-card__title">${esc(ts.title)}</span>
        ${ts.is_public ? `<span class="badge-ok">${icon("globe", 12)} ${t("pública")}</span>` : `<span class="badge-pend">${icon("lock", 12)} ${t("privada")}</span>`}
      </div>
      <p class="mkt-card__desc">${esc(ts.description || "—")}</p>
      <div class="mkt-card__meta">${t("{n} pergunta(s)", { n: ts.question_count })}${stats[ts.id] ? ` · ${t("{n} aluno(s)", { n: stats[ts.id].students })} · ${t("{p}% certas", { p: stats[ts.id].pct_correct })}` : ""}</div>
      <div class="mkt-card__tags">
        ${ts.ai_generated ? `<span class="tag tag--ai">${icon("sparkle", 12)} ${t("Gerado por IA")}</span>` : ""}
        <span class="tag tag--author" title="${t("Submetido por")}">${icon("pencil", 12)} ${esc(ts.author || "—")}</span>
        ${ts.teacher_approved ? `<span class="tag" title="${t("Aprovado por")}">${icon("check", 12)} ${esc(ts.approver || t("aprovado"))}</span>` : `<span class="badge-pend">${t("pendente")}</span>`}
        ${(ts.materials || []).map((m) => `<span class="tag tag--mat" data-mat="${m.id}" title="${t("Ctrl+clique para abrir o material")}">${icon("book", 12)} ${esc(m.title)}</span>`).join("")}
      </div>
      <div class="mkt-card__foot">
        ${ts.question_count ? `<button class="btn btn--sm" data-do="${ts.id}">${t("Fazer")}</button>` : `<span class="muted" style="font-size:13px">${t("sem perguntas")}</span>`}
        ${ts.question_count ? `<button class="btn btn--ghost btn--sm" data-cards="${ts.id}" data-title="${esc(ts.title)}">${icon("book", 14)} ${t("Flashcards")}</button>` : ""}
        ${(teacher && ts.is_mine) || USER.role === "admin" ? `<button class="btn btn--ghost btn--sm" data-edit="${ts.id}">${icon("pencil", 14)} ${t("Editar")}</button>` : ""}
        ${(teacher && ts.is_mine) || USER.role === "admin" ? `<button class="btn btn--ghost btn--sm" data-pub="${ts.id}" data-cur="${ts.is_public}">${ts.is_public ? t("Tornar privada") : t("Publicar")}</button>` : ""}
      </div>
    </div>`).join("");
  wireGridSearch("#testSearch", "#tests", "#testCount", t("teste(s)"));
  $("#tests").querySelectorAll("[data-do]").forEach((b) => (b.onclick = () => startTest(b.dataset.do)));
  $("#tests").querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => openTestEditor(b.dataset.edit)));
  $("#tests").querySelectorAll("[data-cards]").forEach((b) => (b.onclick = () => startFlashcards(b.dataset.cards, b.dataset.title)));
  $("#tests").querySelectorAll("[data-mat]").forEach((b) => (b.onclick = (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;  // Ctrl/Cmd+click to open the material
    e.preventDefault(); openMaterialById(b.dataset.mat);
  }));
  $("#tests").querySelectorAll("[data-pub]").forEach((b) => (b.onclick = async () => {
    try {
      await api(`/tests/${b.dataset.pub}`, { method: "PATCH", body: { is_public: b.dataset.cur !== "true" } });
      toast(b.dataset.cur !== "true" ? t("Pública") : t("Privada")); renderTests(teacher);
    } catch (e) { toast(e.message); }
  }));
}

/* ===================================================================== */
/* MATERIALS (own page; links to Ranked tests + Practice tutor)          */
/* ===================================================================== */
async function vMaterials() {
  const v = $("#view");
  v.innerHTML = `
    <div class="view__head"><h1>${t("Materiais")}</h1><p>${t("Referências que alimentam o tutor (Learn) e fundamentam os testes (Ranked). Material de professor fica aprovado.")}</p></div>
    <div class="card">
      <div class="mgbox">
        <b>${icon("plus", 15)} ${t("Adicionar material")}</b>
        <label class="fld"><span class="label">${t("Título")}</span><input id="nmTitle" placeholder="${t("ex: Imperativo categórico")}"></label>
        <label class="fld"><span class="label">${t("Conteúdo de referência")}</span><textarea id="nmBody" rows="3"></textarea></label>
        <div class="row" style="margin-top:8px"><button class="btn btn--sm" id="nmAdd">${t("Adicionar")}</button><button class="btn btn--ghost btn--sm" id="nmCancel">${t("Limpar")}</button></div>
      </div>
    </div>
    <div class="toolrow"><input id="matSearch" class="searchbar" placeholder="${t("Procurar material…")}" autocomplete="off">
      <select id="matSort" class="searchbar" style="flex:0 0 auto;width:auto">
        <option value="fav">${t("Favoritos primeiro")}</option>
        <option value="new">${t("Mais recentes")}</option>
        <option value="pend">${t("Pendentes primeiro")}</option>
      </select><span class="muted" id="matCount"></span></div>
    <div id="matGrid" class="mkt-grid">…</div>`;
  await renderMaterialsPage();
}

async function renderMaterialsPage() {
  $("#nmCancel").onclick = () => { $("#nmTitle").value = ""; $("#nmBody").value = ""; };
  $("#nmAdd").onclick = async () => {
    try {
      await api(`/subjects/${SUBJECT}/material`, { method: "POST", body: {
        title: $("#nmTitle").value.trim(), body: $("#nmBody").value } });
      $("#nmTitle").value = ""; $("#nmBody").value = ""; toast(t("Material adicionado")); renderMaterialsPage();
    } catch (e) { toast(e.message); }
  };
  const isTeacher = USER.role === "teacher" || USER.role === "admin";
  let mats = [];
  try { mats = await api(`/subjects/${SUBJECT}/material`); } catch {}
  const sortMode = ($("#matSort") || {}).value || "fav";
  if (sortMode === "new") mats.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  else if (sortMode === "pend") mats.sort((a, b) => (a.teacher_approved ? 1 : 0) - (b.teacher_approved ? 1 : 0));
  else mats.sort((a, b) => (b.favorited ? 1 : 0) - (a.favorited ? 1 : 0));
  _matCache = {}; mats.forEach((m) => (_matCache[m.id] = m));
  $("#matGrid").innerHTML = mats.length ? mats.map((m) => `
    <div class="mkt-card pick" data-open="${m.id}" data-search="${esc(`${m.title} ${m.body || ""}`.slice(0, 400).toLowerCase())}">
      <div class="mkt-card__top">
        <span class="mkt-card__title">${esc(m.title)}</span>
        <button class="iconbtn star ${m.favorited ? "on" : ""}" data-fav="${m.id}" title="${t("Favorito")}">${icon("star", 16)}</button>
      </div>
      <div class="mkt-card__meta">${matStatus(m)}</div>
      <p class="mkt-card__desc">${esc((m.body || "").slice(0, 160))}${(m.body || "").length > 160 ? "…" : ""}</p>
      <div class="mkt-card__foot">
        <button class="btn btn--ghost btn--sm" data-study="${m.id}">${icon("compass", 14)} ${t("Estudar no Learn")}</button>
        ${(isTeacher && !m.teacher_approved) ? `<button class="btn btn--sm" data-approve="${m.id}">${icon("check", 14)} ${t("Aprovar")}</button>` : ""}
      </div>
    </div>`).join("") : `<p class="muted">${t("Sem materiais ainda — adiciona o primeiro.")}</p>`;
  const sortSel = $("#matSort");
  if (sortSel && !sortSel._wired) { sortSel._wired = true; sortSel.onchange = () => renderMaterialsPage(); }
  wireGridSearch("#matSearch", "#matGrid", "#matCount", t("material(is)"));
  $("#matGrid").querySelectorAll("[data-open]").forEach((c) => (c.onclick = () => openMaterialInspector(_matCache[c.dataset.open])));
  $("#matGrid").querySelectorAll("[data-study]").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); PENDING_MATERIAL = b.dataset.study; go("tutor"); }));
  $("#matGrid").querySelectorAll("[data-approve]").forEach((b) => (b.onclick = async (e) => {
    e.stopPropagation();
    try { await api(`/materials/${b.dataset.approve}/approve`, { method: "POST" }); toast(t("Material aprovado")); renderMaterialsPage(); }
    catch (err) { toast(err.message); }
  }));
  $("#matGrid").querySelectorAll("[data-fav]").forEach((b) => (b.onclick = async (e) => {
    e.stopPropagation();
    try { const r = await api(`/materials/${b.dataset.fav}/favorite`, { method: "POST" }); b.classList.toggle("on", r.favorited); }
    catch (err) { toast(err.message); }
  }));
}

// material status line: submitter + approval state + approver
function matStatus(m) {
  const who = m.author ? ` · ${icon("pencil", 11)} ${esc(m.author)}` : "";
  const state = m.teacher_approved
    ? `<span class="badge-ok">${icon("check", 12)} ${t("aprovado")}${m.approver ? " · " + esc(m.approver) : ""}</span>`
    : `<span class="badge-pend">${t("pendente")}</span>`;
  return state + who;
}

let _matCache = {};
async function openMaterialById(id) {
  let m = _matCache[id];
  if (!m) {
    try { m = (await api(`/subjects/${SUBJECT}/material`)).find((x) => x.id === id); } catch {}
  }
  if (m) openMaterialInspector(m);
  else toast(t("Material não encontrado"));
}
function _fmtSize(n) { return n > 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB"; }
function _assetIcon(kind) { return kind === "pdf" ? "doc" : kind === "markdown" ? "book" : "doc"; }

async function openMaterialInspector(m) {
  if (!m) return;
  let full = m;
  try { full = await api(`/materials/${m.id}`); } catch {}  // fetch assets
  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel">
      <div class="modal__hd"><h3>${t("Material")}</h3><button class="iconbtn" id="mClose">${icon("plus", 18)}</button></div>
      <div class="modal__body">
        <div class="mgbox">
          <label class="fld"><span class="label">${t("Título")}</span><input id="miTitle" value="${esc(full.title)}"></label>
          <label class="fld"><span class="label">${t("Conteúdo (markdown suportado)")}</span><textarea id="miBody" rows="8">${esc(full.body || "")}</textarea></label>
          <div class="mkt-card__meta">${matStatus(full)}</div>
          <div class="row" style="margin-top:6px">
            <button class="btn btn--sm" id="miSave">${t("Guardar")}</button>
            <button class="btn btn--ghost btn--sm" id="miStudy">${icon("compass", 14)} ${t("Estudar no Learn")}</button>
            ${((USER.role === "teacher" || USER.role === "admin") && !full.teacher_approved) ? `<button class="btn btn--sm" id="miApprove">${icon("check", 14)} ${t("Aprovar")}</button>` : ""}
          </div>
        </div>
        <h4 class="modal__sub">${t("Anexos (PDF / Markdown)")}</h4>
        <div id="miAssets"></div>
        <label class="btn btn--ghost btn--sm" style="margin-top:10px;cursor:pointer">
          ${icon("plus", 14)} ${t("Adicionar ficheiro")}
          <input id="miUpload" type="file" accept=".pdf,.md,.markdown,.txt" style="display:none">
        </label>
      </div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  const close = () => closeModal();
  $("#mClose").onclick = close; $("#modal .modal__backdrop").onclick = close;
  $("#miStudy").onclick = () => { PENDING_MATERIAL = m.id; closeModal(); go("tutor"); };
  if ($("#miApprove")) $("#miApprove").onclick = async () => {
    try { await api(`/materials/${m.id}/approve`, { method: "POST" }); toast(t("Material aprovado")); closeModal(); if (CURRENT_VIEW === "materials") renderMaterialsPage(); }
    catch (e) { toast(e.message); }
  };
  $("#miSave").onclick = async () => {
    try {
      await api(`/materials/${m.id}`, { method: "PATCH", body: { title: $("#miTitle").value.trim(), body: $("#miBody").value } });
      toast(t("Material atualizado"));
      if (CURRENT_VIEW === "materials") renderMaterialsPage();
    } catch (e) { toast(e.message); }
  };
  renderAssets(m.id, full.assets || []);
  $("#miUpload").onchange = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      const res = await fetch(`${API}/materials/${m.id}/assets`, { method: "POST", headers: TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}, body: fd });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error?.message || t("erro"));
      toast(t("Ficheiro anexado"));
      const fresh = await api(`/materials/${m.id}`);
      renderAssets(m.id, fresh.assets || []);
    } catch (err) { toast(err.message); }
  };
}

function renderAssets(matId, assets) {
  const box = $("#miAssets");
  box.innerHTML = assets.length ? assets.map((a) => `
    <div class="asset-row">
      <span class="asset-row__name">${icon(_assetIcon(a.kind), 15)} ${esc(a.filename)} <span class="muted" style="font-size:12px">· ${a.kind} · ${_fmtSize(a.size)}</span></span>
      <span class="row" style="gap:6px">
        <a class="btn btn--ghost btn--sm" href="${API}/materials/${matId}/assets/${a.id}/download" target="_blank">${t("Abrir")}</a>
        <button class="btn btn--ghost btn--sm" data-del="${a.id}">${t("Apagar")}</button>
      </span>
    </div>`).join("") : `<p class="muted" style="font-size:13px">${t("Sem anexos. PDFs e markdown são lidos e usados para informar o tutor e a avaliação.")}</p>`;
  box.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm(t("Apagar este anexo?"))) return;
    try { await api(`/materials/${matId}/assets/${b.dataset.del}`, { method: "DELETE" });
      const fresh = await api(`/materials/${matId}`); renderAssets(matId, fresh.assets || []); }
    catch (e) { toast(e.message); }
  }));
}

let _run = null;
// shared runner for marketplace tests, review sessions and focused practice
function renderRunSession(s, title, retryId = null) {
  // shuffle question order per attempt (options keep server order — grading is by index)
  for (let i = s.items.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [s.items[i], s.items[j]] = [s.items[j], s.items[i]]; }
  _run = { id: retryId, total: s.items.length, answered: 0, correct: 0, ep: 0 };
  const card = el(`<div class="card">
    <div class="row" style="justify-content:space-between;align-items:center"><h3 style="font-size:16px">${esc(title)}</h3><span class="muted" id="runProg">0 / ${s.items.length}</span></div>
    <div class="bar" style="margin:10px 0 16px"><div class="bar__f" id="runBar" style="width:0%"></div></div>
    <div id="runItems"></div><div id="runSummary"></div></div>`);
  $("#run").innerHTML = ""; $("#run").appendChild(card);
  s.items.forEach((it, idx) => $("#runItems").appendChild(renderItem(it, idx)));
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function startTest(id) {
  $("#run").innerHTML = `<div class="card"><p class="muted">${t("A carregar…")}</p></div>`;
  try {
    const s = await api(`/tests/${id}/start`, { method: "POST" });
    renderRunSession(s, t("Teste em curso"), id);
  } catch (e) { $("#run").innerHTML = `<div class="card"><p class="err">${e.message}</p></div>`; }
}

async function startReviewSession() {
  try {
    const s = await api("/practice/review", { method: "POST", body: { subject: SUBJECT, count: 5 } });
    renderRunSession(s, t("Revisão — erros anteriores"));
  } catch (e) { toast(e.message); }
}

async function startFocusedPractice(concept) {
  try {
    const s = await api("/practice/sessions", { method: "POST", body: { subject: SUBJECT, concept, difficulty: 2, count: 5 } });
    renderRunSession(s, t("Prática focada"));
  } catch (e) { toast(e.message); }
}

// teacher announcements for the active discipline (Learn view)
async function renderAnnouncements() {
  const box = $("#annBox"); if (!box) return;
  let list = [];
  try { list = await api(`/subjects/${SUBJECT}/announcements`); } catch {}
  const teacher = USER.role === "teacher" || USER.role === "admin";
  if (!list.length && !teacher) { box.innerHTML = ""; return; }
  const dfmt = (iso) => new Date(iso).toLocaleDateString(I18N.lang === "pt" ? "pt-PT" : I18N.lang);
  box.innerHTML = `<div class="card anncard">
    <h3 style="font-size:15px;margin-bottom:8px">📣 ${t("Avisos")}</h3>
    ${list.slice(0, 5).map((a) => `<div class="ann">
      ${userAvatar({ avatar: a.avatar, display_name: a.author }, 26)}
      <div class="ann__b"><p>${esc(a.text)}</p><small>${esc(a.author)} · ${dfmt(a.when)}</small></div>
      ${(USER.role === "admin" || a.author_id === USER.id) ? `<button class="iconbtn" data-anndel="${a.id}" title="${t("Apagar")}">${icon("trash", 14)}</button>` : ""}
    </div>`).join("") || `<p class="muted" style="font-size:13px">${t("Sem avisos.")}</p>`}
    ${teacher ? `<form class="row" id="annForm" style="margin-top:8px">
      <input id="annText" maxlength="500" placeholder="${t("Escreve um aviso para a turma…")}" style="flex:1">
      <button class="btn btn--sm">${t("Publicar aviso")}</button></form>` : ""}
  </div>`;
  box.querySelectorAll("[data-anndel]").forEach((b) => (b.onclick = async () => {
    if (!confirm(t("Apagar este aviso?"))) return;
    try { await api(`/announcements/${b.dataset.anndel}`, { method: "DELETE" }); renderAnnouncements(); }
    catch (e) { toast(e.message); }
  }));
  if ($("#annForm")) $("#annForm").onsubmit = async (e) => {
    e.preventDefault();
    const txt = $("#annText").value.trim(); if (!txt) return;
    try { await api(`/subjects/${SUBJECT}/announcements`, { method: "POST", body: { text: txt } }); renderAnnouncements(); }
    catch (err) { toast(err.message); }
  };
}

// banner on Ranked: questions whose last attempt was wrong
async function renderReviewBanner() {
  const b = $("#revBanner"); if (!b) return;
  let c = 0;
  try { c = (await api(`/practice/review/count?subject=${SUBJECT}`)).count; } catch {}
  b.innerHTML = c ? `<div class="card revcard">
      <span>${icon("flame", 18)} <b>${t("Tens {n} pergunta(s) para rever", { n: c })}</b> — ${t("erraste-as da última vez.")}</span>
      <button class="btn btn--sm" id="revGo">${t("Rever agora")}</button></div>` : "";
  if (c) $("#revGo").onclick = () => {
    if ($("#run")) startReviewSession();          // already on Ranked
    else { PENDING_REVIEW = true; go("practice"); }  // e.g. from Learn
  };
}

/* ===================================================================== */
/* FLASHCARD PRACTICE                                                    */
/* ===================================================================== */
let _fc = null;
async function startFlashcards(testId, title) {
  $("#view").innerHTML = `
    <div class="view__head"><h1>${t("Flashcards")}</h1><p>${esc(title || t("Teste"))}</p></div>
    <div class="loader"><div class="loader__ring"></div><span>${t("A baralhar as cartas…")}</span></div>`;
  let cards = [];
  try { cards = await api(`/tests/${testId}/cards`); } catch (e) { go("practice"); return toast(e.message); }
  if (!cards.length) { go("practice"); return toast(t("Sem perguntas")); }
  for (let i = cards.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [cards[i], cards[j]] = [cards[j], cards[i]]; }
  _fc = { cards, i: 0, scoreSum: 0, answered: 0, title: title || t("Teste") };
  const v = $("#view");
  v.innerHTML = `
    <div class="view__head" style="display:flex;align-items:center;justify-content:space-between">
      <div><h1>${t("Flashcards")}</h1><p>${esc(_fc.title)}</p></div>
      <button class="btn btn--ghost btn--sm" id="fcExit">${t("← Voltar")}</button>
    </div>
    <div class="fc-wrap">
      <div class="fc-bar"><span id="fcProg"></span><span class="muted" style="font-size:12.5px">${t("← → navegar · espaço virar")}</span><span id="fcScore"></span></div>
      <div id="fcStage"></div>
      <div class="fc-nav"><button class="btn btn--ghost btn--sm" id="fcPrev">${t("Anterior")}</button><button class="btn btn--sm" id="fcNext">${t("Próxima →")}</button></div>
    </div>`;
  $("#fcExit").onclick = () => go("practice");
  $("#fcPrev").onclick = () => { if (_fc.i > 0) { _fc.i--; renderCard(); } };
  $("#fcNext").onclick = () => { if (_fc.i < _fc.cards.length - 1) { _fc.i++; renderCard(); } else toast(t("Última carta")); };
  // keyboard: arrows navigate, space/enter flips (single listener, rebound per deck)
  if (window._fcKeys) document.removeEventListener("keydown", window._fcKeys);
  window._fcKeys = (e) => {
    if (!_fc || !$("#fcStage")) return;
    if (e.target.matches("input,textarea,select")) return;
    if (e.key === "ArrowLeft") $("#fcPrev")?.click();
    else if (e.key === "ArrowRight") $("#fcNext")?.click();
    else if (e.key === " " || e.key === "Enter") { e.preventDefault(); $("#fcCard")?.classList.toggle("is-flipped"); }
  };
  document.addEventListener("keydown", window._fcKeys);
  renderCard();
}

function renderCard() {
  const c = _fc.cards[_fc.i];
  $("#fcProg").textContent = t("Carta {i} / {n}", { i: _fc.i + 1, n: _fc.cards.length });
  $("#fcScore").textContent = _fc.answered ? t("Média {p}%", { p: Math.round(_fc.scoreSum / _fc.answered) }) : "—";
  const mcq = c.kind === "mcq";
  const answerInput = mcq
    ? `<div class="fc-opts">${(c.options || []).map((o, i) => `<label class="opt"><input type="radio" name="fcopt" value="${i}"> ${esc(o)}</label>`).join("")}</div>`
    : `<textarea id="fcText" rows="4" placeholder="${t("Escreve a tua resposta…")}"></textarea>`;
  $("#fcStage").innerHTML = `
    <div class="flashcard" id="fcCard">
      <div class="flashcard__inner">
        <div class="flashcard__face flashcard__front">
          <span class="fc-kind">${mcq ? t("Escolha múltipla") : (c.kind === "short" ? t("Resposta curta") : t("Resposta longa"))}</span>
          <div class="fc-q">${esc(c.text)}</div>
        </div>
        <div class="flashcard__face flashcard__back">
          <div id="fcResult"></div>
        </div>
      </div>
      <div class="fc-loading" id="fcLoading"><div class="loader__ring"></div><span>${t("A avaliar…")}</span></div>
    </div>
    <div class="fc-answer" id="fcAnswer">
      <span class="label">${t("A tua resposta")}</span>
      ${answerInput}
      <button class="btn btn--sm" id="fcCheck" style="align-self:flex-start">${t("Verificar")}</button>
    </div>`;
  $("#fcCheck").onclick = () => checkCard(c);
  // click the card itself to flip between question and result, indefinitely
  $("#fcCard").onclick = () => $("#fcCard").classList.toggle("is-flipped");
}

async function checkCard(c) {
  const mcq = c.kind === "mcq";
  let raw;
  if (mcq) {
    const sel = document.querySelector('input[name="fcopt"]:checked');
    if (!sel) return toast(t("Escolhe uma opção"));
    raw = { selected_index: +sel.value };
  } else {
    const txt = ($("#fcText").value || "").trim();
    if (!txt) return toast(t("Escreve uma resposta"));
    raw = { text: txt };
  }
  $("#fcLoading").classList.add("show");
  $("#fcCheck").disabled = true;
  try {
    const r = await api(`/questions/${c.id}/grade`, { method: "POST", body: { raw } });
    const score = mcq ? (r.correct ? 100 : 0) : Math.round((r.reasoning_score || 0) * 100);
    _fc.scoreSum += score; _fc.answered += 1;
    let detail;
    if (mcq) {
      const opts = r.answer.options || c.options || [];
      detail = `<p><b>${t("Resposta certa:")}</b> ${esc(opts[r.answer.answer_index] ?? "—")}</p>` + (r.answer.why ? `<p class="muted">${esc(r.answer.why)}</p>` : "");
    } else {
      detail = (r.feedback ? `<p>${esc(t(r.feedback))}</p>` : "") + (r.answer.reference ? `<p class="muted" style="font-size:13px"><b>${t("Referência:")}</b> ${esc(r.answer.reference.slice(0, 400))}…</p>` : "");
    }
    $("#fcResult").innerHTML = `
      <div class="fc-grade ${score >= 60 ? "ok" : "no"}">${score}%</div>
      <div class="fc-verdict">${mcq ? (r.correct ? t("Certo!") : t("Rever")) : t("Avaliação do raciocínio")}</div>
      ${detail}`;
    $("#fcLoading").classList.remove("show");
    $("#fcCard").classList.add("is-flipped");
    $("#fcScore").textContent = t("Média {p}%", { p: Math.round(_fc.scoreSum / _fc.answered) });
    // lock the answer area, hint to flip back
    $("#fcAnswer").querySelectorAll("input,textarea,button").forEach((el) => (el.disabled = true));
    $("#fcCheck").textContent = t("Respondido ✓");
  } catch (e) {
    toast(e.message); $("#fcLoading").classList.remove("show"); $("#fcCheck").disabled = false;
  }
}

/* ---- full test editor modal ---- */
const QTYPES = [["mcq", "Escolha múltipla"], ["short", "Resposta curta"], ["reasoning", "Resposta longa"]];
let _editCtx = { testId: null, concepts: [], materials: [] };

function closeModal() { $("#modal").classList.remove("show"); $("#modal").innerHTML = ""; }
// Esc closes whatever modal is open
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && $("#modal").innerHTML) closeModal();
});

async function openTestEditor(testId) {
  _editCtx.testId = testId;
  try {
    _editCtx.concepts = (await api(`/subjects/${SUBJECT}/graph`)).concepts || [];
    _editCtx.materials = await api(`/subjects/${SUBJECT}/material`);
  } catch {}
  await reloadEditor();
}

async function reloadEditor() {
  let tf;
  try { tf = await api(`/tests/${_editCtx.testId}/full`); } catch (e) { return toast(e.message); }
  const cOpts = (sel) => _editCtx.concepts.map((c) => `<option value="${c.key}" ${c.key === sel ? "selected" : ""}>${esc(c.name)}</option>`).join("");
  const mOpts = (sel) => `<option value="">${t("— sem material —")}</option>` + _editCtx.materials.map((m) => `<option value="${m.id}" ${m.id === sel ? "selected" : ""}>${esc(m.title)}</option>`).join("");
  const diffOpts = (d) => [[1, t("Fácil")], [2, t("Médio")], [3, t("Difícil")]].map(([v, n]) => `<option value="${v}" ${v === d ? "selected" : ""}>${n}</option>`).join("");

  const qForm = (q, i) => {
    const isNew = !q.id;
    const kind = q.kind || "reasoning";
    return `<div class="qedit" data-qid="${q.id || ""}">
      <div class="qedit__hd">${isNew ? t("Nova pergunta") : t("Pergunta {n}", { n: i + 1 })}</div>
      <div class="row">
        <label class="fld"><span class="label">${t("Tipo")}</span><select class="qe-kind">${QTYPES.map(([v, n]) => `<option value="${v}" ${v === kind ? "selected" : ""}>${t(n)}</option>`).join("")}</select></label>
        <label class="fld"><span class="label">${t("Tema")}</span><select class="qe-concept">${cOpts(q.concept) || `<option value="">${t("(sem temas nesta disciplina)")}</option>`}</select></label>
        <label class="fld"><span class="label">${t("Dificuldade")}</span><select class="qe-diff">${diffOpts(q.difficulty || 2)}</select></label>
      </div>
      <div class="row">
        <label class="fld"><span class="label">${t("EP por acerto")}</span><input class="qe-ep" type="number" placeholder="50" value="${q.ep_award ?? ""}"></label>
        <label class="fld"><span class="label">${t("EP por erro")}</span><input class="qe-epw" type="number" placeholder="0" value="${q.ep_wrong ?? 0}"></label>
      </div>
      <div class="qe-mcq" style="display:${kind === "mcq" ? "block" : "none"}">
        <label class="fld"><span class="label">${t("Enunciado")}</span><input class="qe-stem" value="${esc(q.stem || "")}"></label>
        <label class="fld"><span class="label">${t("Opções (uma por linha)")}</span><textarea class="qe-opts" rows="3">${esc((q.options || []).join("\n"))}</textarea></label>
        <label class="fld"><span class="label">${t("Índice da opção correta (0, 1, 2…)")}</span><input class="qe-ans" type="number" min="0" value="${q.answer_index ?? ""}" style="max-width:200px"></label>
      </div>
      <div class="qe-open" style="display:${kind === "mcq" ? "none" : "block"}">
        <label class="fld"><span class="label">${t("Pergunta")}</span><textarea class="qe-prompt" rows="2">${esc(q.prompt || "")}</textarea></label>
        <label class="fld"><span class="label">${t("Material para avaliação")}</span><select class="qe-mat">${mOpts(q.material_id)}</select></label>
      </div>
      <div class="row" style="margin-top:8px">
        <button class="btn btn--sm qe-save">${isNew ? t("Adicionar") : t("Guardar")}</button>
        ${isNew ? `<button class="btn btn--ghost btn--sm qe-discard">${t("Descartar")}</button>` : `<button class="btn btn--ghost btn--sm qe-del">${t("Apagar")}</button>`}
      </div>
    </div>`;
  };

  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel">
      <div class="modal__hd">
        <h3>${t("Editar teste")}</h3>
        <span class="row" style="gap:8px">
          <button class="btn btn--ghost btn--sm" id="etPrint">${icon("doc", 14)} ${t("Imprimir")}</button>
          <button class="iconbtn" id="mClose">${icon("plus", 18)}</button>
        </span>
      </div>
      <div class="modal__body">
        <div class="mgbox">
          <label class="fld"><span class="label">${t("Título")}</span><input id="etTitle" value="${esc(tf.title)}"></label>
          <label class="fld"><span class="label">${t("Descrição")}</span><input id="etDesc" value="${esc(tf.description || "")}"></label>
          <label class="remember"><input type="checkbox" id="etPub" ${tf.is_public ? "checked" : ""}> ${t("Pública (visível a todos)")}</label>
          <button class="btn btn--sm" id="etSave" style="align-self:flex-start;margin-top:6px">${t("Guardar detalhes")}</button>
        </div>
        <h4 class="modal__sub">${t("Perguntas")} (${tf.questions.length})</h4>
        <div id="qList">${tf.questions.map((q, i) => qForm(q, i)).join("") || `<p class="muted">${t("Sem perguntas — adiciona uma.")}</p>`}</div>
        <button class="btn btn--ghost btn--sm" id="qAddNew" style="margin-top:10px">${icon("plus", 14)} ${t("Adicionar pergunta")}</button>
      </div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  $("#mClose").onclick = () => { closeModal(); renderTests(true); };
  $("#modal .modal__backdrop").onclick = () => { closeModal(); renderTests(true); };
  $("#etPrint").onclick = () => printTest(tf);
  $("#etSave").onclick = async () => {
    try {
      await api(`/tests/${_editCtx.testId}`, { method: "PATCH", body: { title: $("#etTitle").value.trim(), description: $("#etDesc").value.trim(), is_public: $("#etPub").checked } });
      toast(t("Detalhes guardados"));
    } catch (e) { toast(e.message); }
  };
  $("#qAddNew").onclick = () => {
    const wrap = el(`<div></div>`); wrap.innerHTML = qForm({}, 0);
    $("#qList").appendChild(wrap.firstChild);
    wireQRow($("#qList").lastElementChild);
  };
  $("#qList").querySelectorAll(".qedit").forEach(wireQRow);
}

// paper version of a test: questions + optional answer key, straight to print
function printTest(tf) {
  const withKey = confirm(t("Incluir chave de correção na última página?"));
  const letters = "abcdefghij";
  const qHtml = (q, i) => `
    <div class="q"><b>${i + 1}.</b> ${esc(q.stem || q.prompt || "")}
      ${q.kind === "mcq"
        ? `<ol type="a">${(q.options || []).map((o) => `<li>${esc(o)}</li>`).join("")}</ol>`
        : `<div class="lines"></div><div class="lines"></div><div class="lines"></div>`}
    </div>`;
  const key = withKey
    ? `<div class="key"><h2>${t("Chave de correção")} — ${esc(tf.title)}</h2><ol>${tf.questions.map((q) =>
        `<li>${q.kind === "mcq" ? (letters[q.answer_index] ?? "?") : t("resposta aberta")}</li>`).join("")}</ol></div>`
    : "";
  const w = window.open("", "_blank");
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(tf.title)}</title><style>
    body{font-family:Georgia,serif;color:#111;margin:2.2cm;font-size:13pt;line-height:1.5}
    h1{font-size:17pt;margin:0 0 2px} .sub{color:#555;font-size:11pt;margin:0 0 6px}
    .meta{border-bottom:1.5px solid #111;padding-bottom:8px;margin-bottom:18px;font-size:11pt}
    .q{margin:0 0 16px;page-break-inside:avoid} ol{margin:6px 0 0 8px}
    .lines{border-bottom:1px solid #999;height:26px}
    .key{page-break-before:always}
  </style></head><body>
    <h1>${esc(tf.title)}</h1>
    <p class="sub">${esc(tf.description || "")}</p>
    <div class="meta">${t("Nome")}: ______________________________ &nbsp;&nbsp; ${t("Data")}: ____ / ____ / ______</div>
    ${tf.questions.map(qHtml).join("")}
    ${key}
  </body></html>`);
  w.document.close(); w.focus(); w.print();
}

/* ---- material picker modal (used by Practice) ---- */
function matPickCard(m) {
  return `<div class="mkt-card pick" data-pick="${m.id}">
    <div class="mkt-card__top"><span class="mkt-card__title">${esc(m.title)}</span>
      <button class="iconbtn star ${m.favorited ? "on" : ""}" data-fav="${m.id}" title="${t("Favorito")}">${icon("star", 16)}</button></div>
    <p class="mkt-card__desc">${esc((m.body || "").slice(0, 120))}${(m.body || "").length > 120 ? "…" : ""}</p>
    ${m.teacher_approved ? `<div class="mkt-card__tags"><span class="badge-ok">${icon("check", 12)} ${t("aprovado")}</span></div>` : ""}
  </div>`;
}
async function openMaterialPicker(onPick) {
  let mats = [];
  try { mats = await api(`/subjects/${SUBJECT}/material`); } catch {}
  mats.sort((a, b) => (b.favorited ? 1 : 0) - (a.favorited ? 1 : 0));
  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel">
      <div class="modal__hd"><h3>${t("Escolher material")}</h3><button class="iconbtn" id="mClose">${icon("plus", 18)}</button></div>
      <div class="modal__body">
        <div class="mkt-grid" id="pickGrid">
          <div class="mkt-card pick" data-free="1"><div class="mkt-card__top"><span class="mkt-card__title">${icon("sparkle", 14)} ${t("Tópico livre")}</span></div><p class="mkt-card__desc">${t("Conversa aberta, sem material.")}</p></div>
          ${mats.map(matPickCard).join("")}
        </div>
      </div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  const close = () => closeModal();
  $("#mClose").onclick = close; $("#modal .modal__backdrop").onclick = close;
  $("#pickGrid").querySelectorAll("[data-fav]").forEach((b) => (b.onclick = async (e) => {
    e.stopPropagation();
    try { const r = await api(`/materials/${b.dataset.fav}/favorite`, { method: "POST" }); b.classList.toggle("on", r.favorited); }
    catch (err) { toast(err.message); }
  }));
  $("#pickGrid").querySelectorAll(".pick").forEach((c) => (c.onclick = () => {
    const id = c.dataset.free ? null : c.dataset.pick;
    closeModal(); onPick(id);
  }));
}

function wireQRow(row) {
  const q = (s) => row.querySelector(s);
  const sync = () => {
    const mcq = q(".qe-kind").value === "mcq";
    q(".qe-mcq").style.display = mcq ? "block" : "none";
    q(".qe-open").style.display = mcq ? "none" : "block";
  };
  q(".qe-kind").onchange = sync; sync();
  if (q(".qe-discard")) q(".qe-discard").onclick = () => row.remove();
  if (q(".qe-del")) q(".qe-del").onclick = async () => {
    if (!confirm(t("Apagar esta pergunta?"))) return;
    try { await api(`/tests/${_editCtx.testId}/questions/${row.dataset.qid}`, { method: "DELETE" }); toast(t("Apagada")); reloadEditor(); }
    catch (e) { toast(e.message); }
  };
  q(".qe-save").onclick = async () => {
    const kind = q(".qe-kind").value;
    const body = { concept: q(".qe-concept").value, kind, difficulty: +q(".qe-diff").value,
      ep_award: q(".qe-ep").value === "" ? null : +q(".qe-ep").value, ep_wrong: +(q(".qe-epw").value || 0) };
    if (kind === "mcq") {
      body.stem = q(".qe-stem").value; body.options = q(".qe-opts").value.split("\n").map((s) => s.trim()).filter(Boolean);
      body.answer_index = q(".qe-ans").value === "" ? null : +q(".qe-ans").value;
    } else { body.prompt = q(".qe-prompt").value; body.material = q(".qe-mat").value || null; }
    const qid = row.dataset.qid;
    try {
      if (qid) await api(`/tests/${_editCtx.testId}/questions/${qid}`, { method: "PATCH", body });
      else await api(`/tests/${_editCtx.testId}/questions`, { method: "POST", body });
      toast(t("Guardada")); reloadEditor();
    } catch (e) { toast(e.message); }
  };
}

function renderItem(it, idx) {
  const p = it.payload;
  const node = el(`<div class="q"></div>`);
  if (it.kind === "mcq") {
    node.innerHTML = `<div class="q__stem">${idx + 1}. ${esc(p.stem)}</div>` +
      (p.options || []).map((o, i) => `<label class="opt"><input type="radio" name="q${it.id}" value="${i}"> ${esc(o)}</label>`).join("") +
      `<button class="btn btn--sm" data-go>${t("Responder")}</button><div class="grade" style="display:none"></div>`;
  } else {
    node.innerHTML = `<div class="q__stem">${idx + 1}. ${esc(p.prompt || p.stem)}</div>` +
      `<textarea rows="4" placeholder="${t("Explica o teu raciocínio…")}"></textarea>` +
      `<div style="margin-top:10px"><button class="btn btn--sm" data-go>${t("Responder")}</button></div><div class="grade" style="display:none"></div>`;
  }
  node.querySelector("[data-go]").onclick = () => submitItem(it, node);
  return node;
}

async function submitItem(it, node) {
  const btn = node.querySelector("[data-go]");
  let raw;
  if (it.kind === "mcq") {
    const sel = node.querySelector(`input[name="q${it.id}"]:checked`);
    if (!sel) return toast(t("Escolhe uma opção"));
    raw = { selected_index: +sel.value };
  } else {
    const txt = node.querySelector("textarea").value.trim();
    if (!txt) return toast(t("Escreve a resposta"));
    raw = { text: txt };
  }
  btn.disabled = true; btn.textContent = t("A avaliar…");
  try {
    const r = await api(`/practice/items/${it.id}/answer`, { method: "POST", body: { raw } });
    const g = node.querySelector(".grade");
    g.style.display = "block";
    g.className = "grade " + (r.correct ? "ok" : "no");
    g.innerHTML = `<b>${r.correct ? t("✓ Certo") : t("✗ Rever")}</b> · ${t("raciocínio")} ${(r.reasoning_score * 100).toFixed(0)}% · <b>${r.xp_delta >= 0 ? "+" : ""}${r.xp_delta} EP</b>` +
      (r.feedback ? `<br>${esc(t(r.feedback))}` : "") +
      (r.why ? `<br><b>${t("Porquê:")}</b> ${esc(r.why)}` : "");
    // reveal the right option (and the wrong pick) — corrective feedback on the spot
    if (r.answer_index != null) {
      node.querySelectorAll(".opt").forEach((o, i) => {
        const inp = o.querySelector("input");
        if (i === r.answer_index) o.classList.add("opt--right");
        else if (inp.checked) o.classList.add("opt--wrong");
        inp.disabled = true;
      });
    }
    btn.textContent = t("Respondido");
    if (_run) {
      _run.answered++; if (r.correct) _run.correct++; _run.ep += r.xp_delta;
      const pr = $("#runProg"), bar = $("#runBar");
      if (pr) pr.textContent = `${_run.answered} / ${_run.total}`;
      if (bar) bar.style.width = `${Math.round((100 * _run.answered) / _run.total)}%`;
      if (_run.answered === _run.total && $("#runSummary")) {
        const pct = Math.round((100 * _run.correct) / _run.total);
        $("#runSummary").innerHTML = `<div class="grade ${pct >= 50 ? "ok" : "no"}" style="margin-top:14px">
          <b>${t("Teste concluído!")}</b> ${t("{c}/{n} certas ({p}%)", { c: _run.correct, n: _run.total, p: pct })} · <b>${_run.ep >= 0 ? "+" : ""}${_run.ep} EP</b>
          <div style="margin-top:10px">${_run.id ? `<button class="btn btn--sm" id="runAgain">${t("Repetir teste")}</button>` : ""}</div></div>`;
        if (_run.id && $("#runAgain")) $("#runAgain").onclick = () => startTest(_run.id);
        renderReviewBanner();  // count may have changed after this run
        $("#runSummary").scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
    if (r.ranked_up) playRankUp(r.rank);
    refreshChip();
  } catch (e) { toast(e.message); btn.disabled = false; btn.textContent = t("Responder"); }
}

/* ===================================================================== */
/* PROGRESS                                                              */
/* ===================================================================== */
function rankFill(xp) {
  let lo = 0, hi = RANKS[RANKS.length - 1][1];
  for (let i = 0; i < RANKS.length; i++) {
    if (xp >= RANKS[i][1]) { lo = RANKS[i][1]; hi = RANKS[i + 1] ? RANKS[i + 1][1] : RANKS[i][1] + 1; }
  }
  return Math.min(100, Math.round(((xp - lo) / (hi - lo)) * 100));
}
async function vProfile() {
  const v = $("#view");
  const subjName = (SUBJECTS.find((s) => s.key === SUBJECT) || {}).name || SUBJECT;
  v.innerHTML = `<div class="view__head"><h1>${t("Meu perfil")}</h1><p>${esc(USER.display_name)} · ${esc(subjName)}</p></div>
    <div class="card" id="pg">…</div>
    <div class="card"><h3 style="font-size:16px;margin-bottom:10px">${t("Conquistas")}</h3><div class="ach-grid" id="pach">…</div></div>
    <div class="card"><h3 style="font-size:16px;margin-bottom:10px">${t("Últimos resultados")}</h3><div id="pres">…</div></div>
    <div class="card"><h3 style="font-size:16px;margin-bottom:10px">${t("Histórico de duelos")}</h3><div id="dhist">…</div></div>
    <div class="card"><h3 style="font-size:16px;margin-bottom:10px">${t("Uso da IA")}</h3><div id="us">…</div></div>
    <div class="card">
      <h3 style="font-size:16px;margin-bottom:4px">${t("Conta")}</h3>
      <p class="muted" style="font-size:13px;margin-bottom:12px">${t("O teu nome, utilizador e avatar — como os outros te veem.")}</p>
      <div class="mgbox" style="max-width:460px">
        <label class="fld"><span class="label">${t("Nome")}</span><input id="accName" maxlength="60" value="${esc(USER.display_name)}"></label>
        <label class="fld"><span class="label">${t("Utilizador (para login e amigos)")}</span><input id="accUser" maxlength="20" placeholder="ex: joao_b" value="${esc(USER.username || "")}"></label>
        <span class="label" style="margin-top:6px">${t("Foto de perfil (verificada por IA)")}</span>
        <div class="row" style="align-items:center;gap:12px">
          ${userAvatar(USER, 56)}
          <label class="btn btn--ghost btn--sm" style="cursor:pointer">${icon("plus", 14)} ${t("Carregar foto")}
            <input id="accPhoto" type="file" accept="image/jpeg,image/png,image/webp" style="display:none"></label>
          ${USER.photo ? `<button class="btn btn--ghost btn--sm" id="accPhotoDel">${icon("trash", 14)} ${t("Remover foto")}</button>` : ""}
          <span class="muted" id="accPhotoStatus" style="font-size:12.5px"></span>
        </div>
        <span class="label" style="margin-top:6px">${t("Avatar")}</span>
        <div class="av-pick" id="avPick">
          <button type="button" class="av-sw ${!USER.avatar ? "on" : ""}" data-av="">${esc((USER.display_name || "?").charAt(0).toUpperCase())}</button>
          ${AVATAR_KEYS.map((k) => `<button type="button" class="av-sw ${USER.avatar === k ? "on" : ""}" data-av="${k}">${icon(k, 20)}</button>`).join("")}
        </div>
        <button class="btn btn--sm" id="accSave" style="align-self:flex-start;margin-top:8px">${t("Guardar")}</button>
      </div>
    </div>
    <div class="card">
      <h3 style="font-size:16px;margin-bottom:4px">${t("Idioma")}</h3>
      <p class="muted" style="font-size:13px;margin-bottom:10px">${t("A língua da interface. Novas línguas são fáceis de adicionar.")}</p>
      <div class="row" id="langPick">${Object.entries(I18N.LANGS).map(([k, n]) => `<button class="btn ${k === I18N.lang ? "" : "btn--ghost"} btn--sm" data-lang="${k}">${n}</button>`).join("")}</div>
    </div>
    <div class="card">
      <h3 style="font-size:16px;margin-bottom:4px">${t("Segurança")}</h3>
      <p class="muted" style="font-size:13px;margin-bottom:12px">${icon("lock", 13)} ${t("Palavra-passe protegida com Argon2. Alterá-la termina as outras sessões.")}</p>
      <div class="mgbox" style="max-width:420px">
        <b>${icon("lock", 14)} ${t("Alterar palavra-passe")}</b>
        <label class="fld"><span class="label">${t("Palavra-passe atual")}</span><input id="pwCur" type="password" autocomplete="current-password"></label>
        <label class="fld"><span class="label">${t("Nova palavra-passe (mín. 8)")}</span><input id="pwNew" type="password" autocomplete="new-password"></label>
        <label class="fld"><span class="label">${t("Confirmar nova")}</span><input id="pwNew2" type="password" autocomplete="new-password"></label>
        <button class="btn btn--sm" id="pwSave" style="align-self:flex-start;margin-top:6px">${t("Alterar")}</button>
      </div>
    </div>
    ${friendsCard()}`;
  mountFriends(document.querySelector("#view .frcard"));
  $("#accPhoto").onchange = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    $("#accPhotoStatus").textContent = t("A verificar com IA…");
    const fd = new FormData(); fd.append("file", f);
    try {
      const res = await fetch(`${API}/me/photo`, { method: "POST", headers: TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}, body: fd });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error?.message || t("erro"));
      USER = body;
      toast(t("Foto aprovada e publicada") + " ✓");
      renderRail(); vProfile();
    } catch (err) { $("#accPhotoStatus").textContent = ""; toast(t(err.message)); }
  };
  if ($("#accPhotoDel")) $("#accPhotoDel").onclick = async () => {
    try { USER = await api("/me/photo", { method: "DELETE" }); toast(t("Foto removida")); renderRail(); vProfile(); }
    catch (e) { toast(e.message); }
  };
  let _pickedAv = USER.avatar || "";
  $("#avPick").querySelectorAll(".av-sw").forEach((b) => (b.onclick = () => {
    _pickedAv = b.dataset.av;
    $("#avPick").querySelectorAll(".av-sw").forEach((x) => x.classList.toggle("on", x === b));
  }));
  $("#accSave").onclick = async () => {
    try {
      const body = { display_name: $("#accName").value.trim(), avatar: _pickedAv };
      const uname = $("#accUser").value.trim().toLowerCase();
      if (uname) body.username = uname;
      USER = await api("/me", { method: "PATCH", body });
      toast(t("Conta atualizada"));
      renderRail(); vProfile();
    } catch (e) { toast(e.message); }
  };
  $("#langPick").querySelectorAll("[data-lang]").forEach((b) => (b.onclick = () => I18N.set(b.dataset.lang)));
  $("#pwSave").onclick = async () => {
    const cur = $("#pwCur").value, n = $("#pwNew").value, n2 = $("#pwNew2").value;
    if (n.length < 8) return toast(t("Nova palavra-passe: mínimo 8 caracteres"));
    if (n !== n2) return toast(t("As palavras-passe não coincidem"));
    try {
      await api("/me/password", { method: "POST", body: { current_password: cur, new_password: n } });
      $("#pwCur").value = ""; $("#pwNew").value = ""; $("#pwNew2").value = "";
      toast(t("Palavra-passe alterada"));
    } catch (e) { toast(e.message); }
  };
  try {
    const p = await api(`/me/progress/${SUBJECT}`);
    const unlocked = RANKS.filter(([, ep]) => p.xp >= ep).map(([n]) => n);
    const sw = (n, on) => `<button class="bg-sw ${on ? "on" : ""}" data-bg="${n}" title="${n}" style="background:${n === "" ? "var(--panel2)" : RANK_ACCENT[n]}">${n === "" ? "A" : ""}</button>`;
    $("#pg").innerHTML = `
      <div class="rankrow">${rankLogo(p.rank, 72, USER.background)}<span class="rankbadge" style="color:${RANK_COLORS[p.rank] || "var(--ink)"}">${p.rank}</span></div>
      <div class="bar"><div class="bar__f" style="width:${rankFill(p.xp)}%"></div></div>
      ${(() => {
        const next = RANKS.find(([, ep]) => p.xp < ep);
        const ladder = RANKS.map(([n, ep]) => `
          <div class="rkstep ${n === p.rank ? "is-cur" : ""} ${p.xp < ep ? "is-locked" : ""}" title="${n} · ${ep} EP">
            ${rankLogo(n, 34)}<span>${n}</span><b>${ep} EP</b></div>`).join("");
        const hint = next
          ? t("Faltam <b>{n} EP</b> para <b>{rank}</b>.", { n: next[1] - p.xp, rank: next[0] })
          : t("Rank máximo alcançado!");
        return `<div class="rankladder">${ladder}</div><p class="muted" style="font-size:13px;margin-top:2px">${hint}</p>`;
      })()}
      <div class="stat"><div><span class="label">EP</span><b>${p.xp}</b></div><div><span class="label">${t("Streak")}</span><b style="display:inline-flex;align-items:center;gap:4px">${p.streak}${icon("flame", 15)}</b></div><div><span class="label">${t("Rating duelos")}</span><b id="pgElo">—</b></div><div><span class="label">${t("V / D / E")}</span><b id="pgWdl">—</b></div><div><span class="label">👏 Kudos</span><b id="pgKud">—</b></div></div>
      <h3 style="margin:18px 0 6px;font-size:16px">${t("EP — últimos 14 dias")}</h3>
      <div class="spark" id="pgSpark"></div>
      <h3 style="margin:18px 0 6px;font-size:16px">${t("Fundo do emblema")}</h3>
      <p class="muted" style="font-size:13px;margin-bottom:8px">${t("Desbloqueias mais cores ao subir de rank.")}</p>
      <div class="bg-pick" id="bgPick">${sw("", !USER.background)}${unlocked.map((n) => sw(n, USER.background === n)).join("")}</div>
      <h3 style="margin:18px 0 8px;font-size:16px">${t("Temas a melhorar")}</h3>
      ${(p.weak_concepts || []).length
        ? `<table><tr><th>${t("Tema")}</th><th>${t("Mestria")}</th><th></th></tr>` +
          p.weak_concepts.map((w) => `<tr><td>${esc(w.name || "") || conceptName(w.concept_id)}</td><td>${(w.mastery * 100).toFixed(0)}%</td><td>${w.key ? `<button class="btn btn--ghost btn--sm" data-prac="${esc(w.key)}">${t("Praticar")}</button>` : ""}</td></tr>`).join("") + `</table>`
        : `<p class="muted">${t("Ainda sem dados — faz uns exercícios na Prática.")}</p>`}`;
    $("#pg").querySelectorAll("[data-prac]").forEach((b) => (b.onclick = () => { PENDING_PRACTICE = b.dataset.prac; go("practice"); }));
    $("#bgPick").querySelectorAll(".bg-sw").forEach((b) => (b.onclick = () => setMyBackground(b.dataset.bg)));
    try {
      const r = await api(`/duels/rating?subject=${SUBJECT}`);
      if ($("#pgElo")) $("#pgElo").textContent = r.rating;
      if ($("#pgWdl")) $("#pgWdl").textContent = `${r.wins} / ${r.losses} / ${r.draws}`;
      const k = await api("/me/kudos");
      if ($("#pgKud")) $("#pgKud").textContent = k.received;
    } catch {}
    try {
      const hist = await api(`/me/progress/${SUBJECT}/history`);
      const max = Math.max(1, ...hist.map((h) => h.ep));
      $("#pgSpark").innerHTML = hist.some((h) => h.ep)
        ? hist.map((h) =>
            `<div class="spark__bar ${h.ep ? "" : "spark__bar--zero"}" style="height:${Math.max(4, Math.round((100 * h.ep) / max))}%" title="${h.day}: ${h.ep} EP"></div>`
          ).join("")
        : `<p class="muted" style="font-size:13px">${t("Ainda sem EP nestas 2 semanas — faz um teste no Ranked.")}</p>`;
    } catch { if ($("#pgSpark")) $("#pgSpark").innerHTML = ""; }
  } catch (e) { $("#pg").innerHTML = `<p class="err">${e.message}</p>`; }
  try {
    const list = await api("/me/achievements");
    $("#pach").innerHTML = list.map((ac) => {
      const [ic, title, desc] = ACH_META[ac.key] || ["star", ac.key, ""];
      return `<div class="ach ${ac.unlocked ? "" : "ach--locked"}" title="${esc(t(desc))}">
        <span class="ach__ic">${icon(ic, 22)}</span>
        <b>${esc(t(title))}</b>
        <small>${ac.unlocked ? t("Desbloqueada") : `${ac.value}/${ac.target}`}</small>
      </div>`;
    }).join("");
  } catch { $("#pach").innerHTML = `<p class="muted">—</p>`; }
  try {
    const rs = await api("/me/results");
    const dfmt = (iso) => new Date(iso).toLocaleDateString(I18N.lang === "pt" ? "pt-PT" : I18N.lang);
    $("#pres").innerHTML = rs.length
      ? `<table><tr><th>${t("Quando")}</th><th>${t("Teste")}</th><th>${t("Certas")}</th><th>${t("Raciocínio")}</th></tr>` + rs.map((r) => {
          const pct = r.answered ? Math.round((100 * r.correct) / r.answered) : 0;
          return `<tr><td>${dfmt(r.when)}</td><td>${esc(r.test_title || t("Prática"))}</td><td>${r.correct}/${r.answered} (${pct}%)</td><td>${Math.round(r.avg_reasoning * 100)}%</td></tr>`;
        }).join("") + `</table>`
      : `<p class="muted">${t("Ainda sem testes feitos.")}</p>`;
  } catch { $("#pres").innerHTML = `<p class="muted">—</p>`; }
  try {
    const ds = (await api("/duels")).filter((d) => d.status === "complete" || d.status === "forfeited").slice(0, 10);
    $("#dhist").innerHTML = ds.length
      ? `<table><tr><th>${t("Oponente")}</th><th>${t("Resultado")}</th><th>${t("Pontos")}</th><th>${t("Modo")}</th></tr>` + ds.map((d) => {
          const res = d.is_draw ? `<span class="badge-pend">${t("Empate")}</span>` : d.won ? `<span class="badge-ok">${t("Vitória")}</span>` : `<span class="badge-no">${t("Derrota")}</span>`;
          return `<tr><td>${esc(d.opponent_name)}</td><td>${res}</td><td>${d.my_points}–${d.opp_points}</td><td class="muted">${d.ranked ? t("Ranked") : t("Amigável")}</td></tr>`;
        }).join("") + `</table>`
      : `<p class="muted">${t("Ainda sem duelos concluídos — desafia um amigo nos Duelos.")}</p>`;
  } catch (e) { $("#dhist").innerHTML = `<p class="muted">—</p>`; }
  try {
    const u = await api("/me/usage");
    $("#us").innerHTML = `<div class="stat">
      <div><span class="label">${t("Tokens in")}</span><b>${u.tokens_in}</b></div>
      <div><span class="label">${t("Tokens out")}</span><b>${u.tokens_out}</b></div>
      <div><span class="label">${t("Custo")}</span><b>${u.cost_eur} €</b></div>
      <div><span class="label">${t("Tutor restante hoje")}</span><b>${u.tutor_messages_remaining_today ?? "∞"}</b></div>
    </div>`;
  } catch (e) { $("#us").innerHTML = `<p class="err">${e.message}</p>`; }
}
// preset avatars (line-art, school-safe — no uploads)
const AVATAR_KEYS = ["cat", "owl", "ghost", "gamepad", "wand", "crown", "swords", "flame", "star", "atom", "planet", "brain", "music", "palette", "code", "compass"];
function userAvatar(u, size = 32) {
  const uid = (u && (u.user_id || u.id)) || "";
  const photo = (u && u.photo) || "";
  const av = (u && u.avatar) || "";
  const initial = ((u && u.display_name) || "?").trim().charAt(0).toUpperCase() || "?";
  const inner = photo && uid
    ? `<img src="${API}/users/${uid}/photo?v=${encodeURIComponent(photo)}" alt="" loading="lazy">`
    : av && AVATAR_KEYS.includes(av) ? icon(av, Math.round(size * 0.62)) : esc(initial);
  return `<span class="uav" style="width:${size}px;height:${size}px;font-size:${Math.round(size * 0.44)}px">${inner}</span>`;
}

// achievement metadata: key -> [icon, title, description] (titles translate via t())
const ACH_META = {
  "first-answer": ["check", "Primeira resposta", "Responde à tua primeira pergunta."],
  "ten-answers": ["pencil", "Estudante ativo", "Responde a 10 perguntas."],
  "hundred-answers": ["book", "Maratonista", "Responde a 100 perguntas."],
  "fifty-correct": ["sparkle", "Meio século", "Acerta 50 respostas."],
  "perfect-test": ["star", "Perfecionista", "Termina um teste (5+ perguntas) com tudo certo."],
  "streak-5": ["flame", "Em chamas", "Acerta 5 respostas seguidas."],
  "first-duel": ["swords", "Duelista", "Completa o teu primeiro duelo."],
  "duel-winner": ["trophy", "Vencedor", "Ganha um duelo."],
  "duel-champion": ["shield", "Campeão", "Ganha 5 duelos."],
  "ep-100": ["compass", "A subir", "Chega a 100 EP numa disciplina."],
  "ep-500": ["globe", "Veterano", "Chega a 500 EP numa disciplina."],
  "two-subjects": ["scales", "Explorador", "Ganha EP em 2 disciplinas."],
};

let CONCEPT_NAMES = {};
function conceptName(id) { return esc(CONCEPT_NAMES[id] || id.slice(0, 8)); }

async function setMyBackground(bg) {
  try {
    const u = await api("/me/background", { method: "PATCH", body: { background: bg || null } });
    USER.background = u.background;
    vProfile(); refreshChip();
  } catch (e) { toast(e.message); }
}

/* ===================================================================== */
/* ADMIN                                                                 */
/* ===================================================================== */
const ADMIN_TABS = [["geral", "Visão geral"], ["disciplinas", "Disciplinas"], ["contas", "Contas"], ["ranks", "Ranks"], ["conversas", "Conversas"]];
let _adminTab = "geral";

async function vAdmin() {
  const v = $("#view");
  v.innerHTML = `
    <div class="view__head"><h1>${t("Administração")}</h1><p>${t("Gestão de contas, conteúdo e progressão.")}</p></div>
    <div class="tabs" id="adminTabs">${ADMIN_TABS.map(([k, l]) => `<button class="tab ${k === _adminTab ? "is-active" : ""}" data-tab="${k}">${esc(t(l))}</button>`).join("")}</div>
    <div id="adminPanel"></div>`;
  $("#adminTabs").querySelectorAll(".tab").forEach((b) => (b.onclick = () => { _adminTab = b.dataset.tab; vAdmin(); }));
  await showAdminTab(_adminTab);
}

/* generic client-side row filter for a table inside `container` */
function wireTableSearch(input, container) {
  input.oninput = () => {
    const q = input.value.toLowerCase();
    container.querySelectorAll("table tr").forEach((tr) => {
      if (tr.querySelector("th")) return;  // keep header
      tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
    });
  };
}
function searchBar(id, placeholder) {
  return `<div class="row" style="margin-bottom:10px"><input id="${id}" placeholder="${placeholder}" autocomplete="off" style="max-width:320px"></div>`;
}

/* SVG-icon picker modal — onPick(key) */
function iconPicker(cur, onPick) {
  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel" style="max-width:380px">
      <div class="modal__hd"><h3>${t("Escolher ícone")}</h3><button class="iconbtn" id="mClose">${icon("plus", 18)}</button></div>
      <div class="modal__body"><div class="icon-grid">${SUBJECT_ICONS.map((k) => `<button class="icon-sw ${k === cur ? "on" : ""}" data-k="${k}" title="${k}">${icon(k, 24)}</button>`).join("")}</div></div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  const close = () => closeModal();
  $("#mClose").onclick = close; $("#modal .modal__backdrop").onclick = close;
  $("#modal").querySelectorAll(".icon-sw").forEach((b) => (b.onclick = () => { closeModal(); onPick(b.dataset.k); }));
}
function bindIconPick(btn) {
  btn.onclick = () => iconPicker(btn.dataset.icon, (k) => { btn.dataset.icon = k; btn.innerHTML = icon(k, 20); });
}

async function showAdminTab(tab) {
  const p = $("#adminPanel");
  if (tab === "geral") {
    p.innerHTML = `<div class="card"><h3 style="font-size:16px;margin-bottom:12px">${t("Plataforma")}</h3><div class="statgrid" id="agStats">…</div></div>`;
    try {
      const s = await api("/admin/stats");
      const tile = (label, val, warn, goTab) => `<div class="stattile ${warn && val > 0 ? "stattile--warn" : ""} ${goTab ? "stattile--link" : ""}" ${goTab ? `data-tab="${goTab}"` : ""}><b>${val}</b><span>${t(label)}</span></div>`;
      $("#agStats").innerHTML =
        tile("Contas", s.users, false, "contas") + tile("Professores", s.teachers, false, "contas") + tile("Disciplinas", s.subjects, false, "disciplinas") +
        tile("Materiais", s.materials) + tile("Materiais pendentes", s.materials_pending, true) +
        tile("Testes", s.tests) + tile("Conversas", s.conversations, false, "conversas") +
        tile("Conversas apagadas", s.deleted_conversations, false, "conversas") + tile("Duelos", s.duels);
      $("#agStats").querySelectorAll("[data-tab]").forEach((el2) => (el2.onclick = () => { _adminTab = el2.dataset.tab; vAdmin(); }));
    } catch (e) { $("#agStats").innerHTML = `<p class="err">${e.message}</p>`; }
    return;
  }
  if (tab === "disciplinas") {
    p.innerHTML = `
      <div class="card">
        <h3 style="font-size:16px;margin-bottom:10px">${t("Disciplinas")}</h3>
        <div class="row" style="margin-bottom:12px;align-items:flex-end">
          <label class="fld"><span class="label">${t("Chave")}</span><input id="ndKey" placeholder="${t("ex: matematica")}" style="max-width:150px"></label>
          <label class="fld"><span class="label">${t("Nome")}</span><input id="ndName" placeholder="${t("ex: Matemática")}" style="max-width:190px"></label>
          <label class="fld"><span class="label">${t("Ícone")}</span><button type="button" class="iconpick" id="ndIconBtn" data-icon="book">${icon("book", 20)}</button></label>
          <button class="btn btn--sm" id="ndAdd">${icon("plus", 15)} ${t("Adicionar")}</button>
        </div>
        ${searchBar("subjSearch", t("Procurar disciplina…"))}
        <div id="subjTable"></div>
      </div>`;
    bindIconPick($("#ndIconBtn"));
    renderSubjectsAdmin();
    wireAddDiscipline();
    wireTableSearch($("#subjSearch"), $("#subjTable"));
  } else if (tab === "contas") {
    p.innerHTML = `<div class="card"><div class="row" style="justify-content:space-between;margin-bottom:10px"><h3 style="font-size:16px">${t("Contas")}</h3><button class="btn btn--ghost btn--sm" id="csvUsers">${icon("doc", 14)} ${t("Exportar CSV")}</button></div>${searchBar("userSearch", t("Procurar por nome ou email…"))}<div id="adm">…</div></div>`;
    await renderUsers();
    wireTableSearch($("#userSearch"), $("#adm"));
    $("#csvUsers").onclick = async () => {
      try {
        const users = await api("/admin/users");
        const cols = ["display_name", "username", "email", "role", "plan"];
        const csvCell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
        const csv = [cols.join(";")].concat(users.map((u) => cols.map((c) => csvCell(u[c])).join(";"))).join("\r\n");
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
        a.download = "rankup-contas.csv";
        a.click();
        URL.revokeObjectURL(a.href);
      } catch (e) { toast(e.message); }
    };
  } else if (tab === "ranks") {
    p.innerHTML = `<div class="card"><h3 style="font-size:16px;margin-bottom:10px">${t("EP por rank")}</h3>
      <div class="tier-layout"><div><div class="tier-edit" id="tierEdit"></div>
        <button class="btn btn--sm" id="tierSave" style="margin-top:12px">${t("Guardar limiares")}</button></div>
        <div class="tier-preview" id="tierPreview"></div></div></div>`;
    renderTierEditor();
  } else if (tab === "conversas") {
    p.innerHTML = `<div class="card">
      <h3 style="font-size:16px;margin-bottom:4px">${icon("trash", 16)} ${t("Conversas apagadas")}</h3>
      <p class="muted" style="font-size:13px;margin-bottom:10px">${t("Ocultadas pelos alunos. Recuperáveis 6 meses; depois apagadas permanentemente.")}</p>
      ${searchBar("delSearch", t("Procurar por conversa ou aluno…"))}<div id="delChats">…</div></div>`;
    await renderDeletedChats();
    wireTableSearch($("#delSearch"), $("#delChats"));
  }
}

function renderSubjectsAdmin() {
  $("#subjTable").innerHTML = `<table><tr><th>${t("Ícone")}</th><th>${t("Nome")}</th><th>${t("Chave")}</th><th></th></tr>` +
    SUBJECTS.map((s) => `<tr data-key="${s.key}">
      <td><button type="button" class="iconpick s-icon" data-icon="${subjectIconKey(s.icon)}">${subjectIcon(s.icon, 20)}</button></td>
      <td><input class="s-name" value="${esc(s.name)}"></td>
      <td><span class="muted">${esc(s.key)}</span></td>
      <td><button class="btn btn--sm s-save">${t("Guardar")}</button></td>
    </tr>`).join("") + `</table>`;
  $("#subjTable").querySelectorAll("tr[data-key]").forEach((tr) => {
    bindIconPick(tr.querySelector(".s-icon"));
    tr.querySelector(".s-save").onclick = async () => {
      try {
        await api(`/admin/subjects/${tr.dataset.key}`, { method: "PATCH", body: {
          name: tr.querySelector(".s-name").value.trim(), icon: tr.querySelector(".s-icon").dataset.icon } });
        toast(t("Disciplina guardada"));
        await loadSubjects(); renderSubjectsAdmin();
      } catch (e) { toast(e.message); }
    };
  });
}

async function renderDeletedChats() {
  let rows;
  try { rows = await api("/admin/tutor/deleted"); } catch (e) { $("#delChats").innerHTML = `<p class="err">${e.message}</p>`; return; }
  if (!rows.length) { $("#delChats").innerHTML = `<p class="muted" style="font-size:13px">${t("Sem conversas apagadas.")}</p>`; return; }
  const fmt = (iso) => iso ? new Date(iso).toLocaleDateString(I18N.lang === "pt" ? "pt-PT" : I18N.lang) : "—";
  $("#delChats").innerHTML = `<table><tr><th>${t("Conversa")}</th><th>${t("Aluno")}</th><th>${t("Msgs")}</th><th>${t("Apagada")}</th><th>${t("Purga")}</th><th></th></tr>` +
    rows.map((r) => `<tr data-id="${r.id}">
      <td><b>${esc(r.title || t("Conversa"))}</b></td>
      <td>${esc(r.owner)}</td>
      <td>${r.messages}</td>
      <td>${fmt(r.deleted_at)}</td>
      <td>${r.expired ? `<span class="badge-pend">${t("a purgar")}</span>` : fmt(r.purges_at)}</td>
      <td><button class="btn btn--ghost btn--sm" data-restore="${r.id}">${icon("restore", 14)} ${t("Recuperar")}</button></td>
    </tr>`).join("") + `</table>`;
  $("#delChats").querySelectorAll("[data-restore]").forEach((b) => (b.onclick = async () => {
    try { await api(`/admin/tutor/deleted/${b.dataset.restore}/restore`, { method: "POST" }); toast(t("Conversa recuperada")); renderDeletedChats(); }
    catch (e) { toast(e.message); }
  }));
}

function wireAddDiscipline() {
  $("#ndAdd").onclick = async () => {
    const key = $("#ndKey").value.trim(), name = $("#ndName").value.trim();
    if (!key || !name) return toast(t("Chave + nome"));
    try {
      await api("/admin/subjects", { method: "POST", body: { key, name, icon: $("#ndIconBtn").dataset.icon } });
      $("#ndKey").value = ""; $("#ndName").value = "";
      $("#ndIconBtn").dataset.icon = "book"; $("#ndIconBtn").innerHTML = icon("book", 20);
      await loadSubjects(); renderSubjectsAdmin();
      toast(t("Disciplina criada"));
    } catch (e) { toast(e.message); }
  };
}

function setTierPreview(name) {
  const ep = (RANKS.find((r) => r[0] === name) || [])[1] ?? 0;
  const tier = Math.max(0, RANKS.findIndex((r) => r[0] === name)) + 1;
  $("#tierPreview").innerHTML =
    `${rankLogo(name, 168, "white")}
     <div style="font-family:'Century Gothic','Jost',sans-serif;font-weight:700;font-size:24px;margin-top:8px;color:${RANK_COLORS[name] || "var(--ink)"}">${name}</div>
     <div class="muted" style="font-size:13px">Tier ${roman(tier)} · ${ep} EP</div>`;
}
function renderTierEditor() {
  $("#tierEdit").innerHTML = RANKS.map(([n, ep]) =>
    `<div class="tier" data-name="${n}">
       <span style="display:inline-flex;align-items:center;gap:8px">${rankLogo(n, 28, "white")} <b>${n}</b></span>
       <span class="row" style="gap:6px">
         <input class="tier-ep" data-name="${n}" type="number" min="0" value="${ep}" style="width:96px">
         <button class="btn btn--ghost btn--sm tier-play" data-rank="${n}" title="${t("Pré-visualizar")}">▶</button>
       </span>
     </div>`
  ).join("");
  $("#tierEdit").querySelectorAll(".tier-play").forEach((b) => (b.onclick = () => playRankUp(b.dataset.rank)));
  $("#tierEdit").querySelectorAll(".tier").forEach((row) => (row.onmouseenter = () => setTierPreview(row.dataset.name)));
  setTierPreview(RANKS[0][0]);
  $("#tierSave").onclick = async () => {
    const tiers = [...document.querySelectorAll(".tier-ep")].map((i) => ({ name: i.dataset.name, ep: +i.value }));
    try {
      const r = await api("/admin/ranks", { method: "PATCH", body: { tiers } });
      RANKS = r.map((t) => [t.name, t.ep]);
      toast(t("Limiares atualizados"));
      renderTierEditor(); renderUsers(); refreshChip();
    } catch (e) { toast(e.message); }
  };
}
async function renderUsers() {
  try {
    const users = await api("/admin/users");
    const subjName = (SUBJECTS.find((s) => s.key === SUBJECT) || {}).name || SUBJECT;
    $("#adm").innerHTML = `<h3 style="font-size:16px;margin-bottom:10px">${t("Contas")}</h3><table><tr><th>${t("Conta")}</th><th>${t("Role")}</th><th>${t("Plano")}</th><th>${t("Fundo")}</th><th>EP (${esc(subjName)})</th><th></th></tr>` +
      users.map((u) => `<tr data-id="${u.id}">
        <td><b>${esc(u.display_name)}</b><br><span class="muted">${esc(u.username || u.email)}</span></td>
        <td><select class="u-role">${["student", "teacher", "admin"].map((r) => `<option ${r === u.role ? "selected" : ""}>${r}</option>`).join("")}</select></td>
        <td><select class="u-plan">${["free", "pro"].map((p) => `<option ${p === u.plan ? "selected" : ""}>${p}</option>`).join("")}</select></td>
        <td><select class="u-bg"><option value="" ${!u.background ? "selected" : ""}>auto</option>${RANKS.map(([n]) => `<option ${u.background === n ? "selected" : ""}>${n}</option>`).join("")}</select></td>
        <td class="row" style="gap:6px">
          <input class="u-xp" type="number" min="0" placeholder="EP" style="width:90px">
          <button class="btn btn--sm u-prog">${t("Definir EP")}</button>
        </td>
        <td class="row"><button class="btn btn--sm u-save">${t("Guardar")}</button><button class="btn btn--ghost btn--sm u-del">${t("Apagar")}</button></td>
      </tr>`).join("") + `</table>`;
    $("#adm").querySelectorAll("tr[data-id]").forEach((tr) => {
      const id = tr.dataset.id;
      tr.querySelector(".u-save").onclick = async () => {
        try {
          await api(`/admin/users/${id}`, { method: "PATCH", body: {
            role: tr.querySelector(".u-role").value,
            plan: tr.querySelector(".u-plan").value,
            set_background: true, background: tr.querySelector(".u-bg").value || null,
          } });
          toast(t("Guardado"));
        } catch (e) { toast(e.message); }
      };
      tr.querySelector(".u-prog").onclick = async () => {
        const xpStr = tr.querySelector(".u-xp").value;
        if (xpStr === "") return toast(t("Define os EP"));
        try {
          const res = await api(`/admin/users/${id}/progress`, { method: "PATCH", body: { subject: SUBJECT, xp: +xpStr } });
          toast(`OK → ${res.xp} EP · ${res.rank}`);
          if (id === USER.id) refreshChip();  // update own visible chip immediately
        } catch (e) { toast(e.message); }
      };
      tr.querySelector(".u-del").onclick = async () => {
        if (!confirm(t("Apagar esta conta?"))) return;
        try { await api(`/admin/users/${id}`, { method: "DELETE" }); renderUsers(); } catch (e) { toast(e.message); }
      };
    });
  } catch (e) { $("#adm").innerHTML = `<p class="err">${e.message}</p>`; }
}

/* ---- preload concept names for progress table ---- */
async function preloadConcepts() {
  try {
    const g = await api(`/subjects/${SUBJECT}/graph`);
    g.concepts.forEach((c) => (CONCEPT_NAMES[c.id] = c.name));
  } catch {}
}

/* ===================================================================== */
/* DUELS + FRIENDS                                                       */
/* ===================================================================== */
let _duelPoll = null, _duelTick = null, _duelId = null, _duelSig = "", _duelSecs = null;
let _duelDraft = { key: "", text: "" };

function stopDuelPolling() {
  if (_duelPoll) { clearInterval(_duelPoll); _duelPoll = null; }
  if (_duelTick) { clearInterval(_duelTick); _duelTick = null; }
  _duelId = null; _duelSig = "";
}
function fmtClock(s) {
  if (s == null) return "";
  s = Math.max(0, s | 0);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/* ---- lobby: friends + my duels ---- */
async function vDuels() {
  stopDuelPolling();
  const v = $("#view");
  const subjName = (SUBJECTS.find((s) => s.key === SUBJECT) || {}).name || SUBJECT;
  v.innerHTML = `
    <div class="view__head"><h1>${t("Duelos")}</h1><p>${t("Desafia amigos: cada um escolhe um material da mesma disciplina e duelam-se em perguntas. A IA julga cada ronda. Vitória 2 pts · empate 1 pt.")}</p></div>
    <div class="card" id="rankedCard">…</div>
    <div class="duel-lobby">
      ${friendsCard()}
      <div class="card">
        <h3 style="font-size:16px;margin-bottom:4px">${icon("trophy", 16)} ${t("Os meus duelos")}</h3>
        <p class="muted" style="font-size:13px;margin-bottom:10px">${t("Desafios criados na disciplina")} <b>${esc(subjName)}</b>.</p>
        <div id="duBox">…</div>
      </div>
    </div>`;
  mountFriends(document.querySelector("#view .frcard"));
  renderRanked();
  renderDuelList();
}

/* ---- ranked: rating + matchmaking ---- */
let _mmPoll = null, _mmSearching = false;
function stopMatchmaking() {
  if (_mmPoll) { clearInterval(_mmPoll); _mmPoll = null; }
  if (_mmSearching) { api("/duels/ranked/queue", { method: "DELETE" }).catch(() => {}); _mmSearching = false; }
}

async function renderRanked() {
  const box = $("#rankedCard"); if (!box) return;
  const subj = SUBJECTS.find((s) => s.key === SUBJECT) || { name: SUBJECT, icon: "" };
  let r = { rating: 1000, games: 0, wins: 0, losses: 0, draws: 0 }, lb = [];
  try { r = await api(`/duels/rating?subject=${SUBJECT}`); } catch {}
  try { lb = await api(`/duels/leaderboard?subject=${SUBJECT}`); } catch {}
  box.className = "rk";
  box.innerHTML = `
    <span class="rk__bk rk__bk--tl"></span><span class="rk__bk rk__bk--br"></span>
    <div class="rk__head">
      <div class="rk__title">${t("DUELOS")}&nbsp;<span>${t("RANKED")}</span></div>
      <div class="rk__disc">${subjectIcon(subj.icon, 16)} ${esc(subj.name)}</div>
    </div>
    <div class="rk__body">
      <div class="rk__rating">
        <div class="rk__diamond"><b>${r.rating}</b></div>
        <div class="rk__rec">
          <span class="rk__reclabel">${t("RATING")}</span>
          <span class="rk__recnums"><b style="color:var(--green)">${r.wins}${t("V")}</b> · <b style="color:var(--red)">${r.losses}${t("D")}</b> · ${r.draws}${t("E")}</span>
        </div>
      </div>
      <div id="mmBox" class="rk__action"></div>
    </div>
    ${lb.length ? `<div class="rk__lb">
      <div class="rk__lbtitle">${icon("trophy", 14)} ${t("CLASSIFICAÇÃO")}</div>
      ${lb.slice(0, 6).map((x, i) => `<div class="rk__lbrow ${x.name === USER.display_name ? "is-me" : ""}">
        <span class="rk__rank">${i + 1}</span>${userAvatar({ avatar: x.avatar, display_name: x.name }, 22)}<span class="rk__pname">${esc(x.name)}</span>
        <span class="rk__pwl muted">${x.wins}/${x.losses}/${x.draws}</span><span class="rk__prating">${x.rating}</span></div>`).join("")}
    </div>` : ""}`;
  renderMMBox();
}

function renderMMBox() {
  const mm = $("#mmBox"); if (!mm) return;
  if (_mmSearching) {
    mm.innerHTML = `
      <div class="rk-search">
        <div class="rk-search__ring"><div class="loader__ring"></div></div>
        <div class="rk-search__txt"><div class="rk-search__t">${t("À PROCURA DE OPONENTE")}</div><div class="rk-search__w" id="mmWait"></div></div>
      </div>
      <button class="rk-cancel" id="mmCancel">${t("Cancelar procura")}</button>`;
    $("#mmCancel").onclick = () => { stopMatchmaking(); renderRanked(); };
  } else {
    mm.innerHTML = `
      <button class="rk-cta" id="mmFind"><span class="rk-cta__ic">${icon("trophy", 30)}</span><span>${t("Procurar Oponente")}</span></button>
      <p class="rk-cta__note">${t("Encontra um adversário do teu nível e sobe na classificação.")}</p>`;
    $("#mmFind").onclick = startMatchmaking;
  }
}

async function startMatchmaking() {
  try {
    const res = await api("/duels/ranked/queue", { method: "POST", body: { subject: SUBJECT } });
    if (res.state === "matched") return openDuel(res.duel_id);
    _mmSearching = true; renderMMBox();
    _mmPoll = setInterval(pollMatchmaking, 2500);
  } catch (e) { toast(e.message); }
}

async function pollMatchmaking() {
  let res;
  try { res = await api("/duels/ranked/status"); } catch { return; }
  if (res.state === "matched") { if (_mmPoll) clearInterval(_mmPoll); _mmPoll = null; _mmSearching = false; return openDuel(res.duel_id); }
  if (res.state === "queued") { const w = $("#mmWait"); if (w) w.textContent = `(${res.waited || 0}s)`; }
  else { stopMatchmaking(); renderRanked(); }  // idle = queue lost
}

/* ---- reusable friends panel (used by Duels lobby + Profile) ---- */
function friendsCard() {
  return `<div class="card frcard">
    <h3 style="font-size:16px;margin-bottom:10px">${icon("user", 16)} ${t("Amigos")}</h3>
    <div class="row" style="margin-bottom:12px">
      <input class="fr-id" placeholder="${t("nome, utilizador ou email")}" autocomplete="off">
      <button class="btn btn--ghost btn--sm fr-search" title="${t("Procurar pessoas")}">${icon("search", 14)} ${t("Procurar")}</button>
      <button class="btn btn--ghost btn--sm fr-add" title="${t("Adicionar por email/utilizador")}">${icon("plus", 14)} ${t("Adicionar")}</button>
    </div>
    <div class="fr-box">…</div>
  </div>`;
}
function mountFriends(card) {
  card = card || document.querySelector(".frcard");
  if (!card) return;
  const input = card.querySelector(".fr-id");
  card.querySelector(".fr-add").onclick = async () => {
    const id = input.value.trim();
    if (!id) return toast(t("Escreve um email ou utilizador"));
    try { await api("/friends/requests", { method: "POST", body: { identifier: id } }); input.value = ""; toast(t("Pedido enviado")); renderFriends(card); }
    catch (e) { toast(e.message); }
  };
  card.querySelector(".fr-search").onclick = () => openUserSearch(input.value.trim());
  input.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); openUserSearch(input.value.trim()); } };
  renderFriends(card);
}

async function renderFriends(card) {
  card = card || document.querySelector(".frcard");
  if (!card) return;
  const box = card.querySelector(".fr-box");
  let d;
  try { d = await api("/friends"); } catch (e) { box.innerHTML = `<p class="err">${e.message}</p>`; return; }
  const reqRow = (r) => `<div class="fr-row">
    <span>${icon("user", 14)} <b>${esc(r.display_name)}</b> <span class="muted" style="font-size:12px">${esc(r.username || "")}</span></span>
    <span class="row" style="gap:6px">
      <button class="btn btn--sm" data-acc="${r.id}">${t("Aceitar")}</button>
      <button class="btn btn--ghost btn--sm" data-dec="${r.id}">${t("Recusar")}</button>
    </span></div>`;
  const unreadBy = (window._unread || {}).by_user || {};
  const frRow = (f) => `<div class="fr-row">
    <span class="fr-who">${userAvatar(f, 30)} <b>${esc(f.display_name)}</b> <span class="muted fr-user" style="font-size:12px">${esc(f.username || "")}</span></span>
    <span class="fr-acts">
      <button class="fr-act" data-prof="${f.user_id}" title="${t("Ver perfil")}">${icon("user", 15)}</button>
      <button class="fr-act frmsg" data-msg="${f.user_id}" data-name="${esc(f.display_name)}" title="${t("Mensagens")}">${icon("chat", 15)}${unreadBy[f.user_id] ? `<span class="frmsg__n">${unreadBy[f.user_id]}</span>` : ""}</button>
      <button class="fr-act" data-duel="${f.user_id}" title="${t("Desafiar")}">${icon("swords", 15)}</button>
      <button class="fr-act fr-act--danger" data-unfr="${f.user_id}" title="${t("Remover")}">✕</button>
    </span></div>`;
  box.innerHTML =
    (d.incoming.length ? `<div class="fr-sec"><span class="label">${t("Pedidos recebidos")}</span>${d.incoming.map(reqRow).join("")}</div>` : "") +
    (d.outgoing.length ? `<div class="fr-sec"><span class="label">${t("Pedidos enviados")}</span>${d.outgoing.map((r) => `<div class="fr-row"><span>${icon("user", 14)} <b>${esc(r.display_name)}</b></span><span class="muted" style="font-size:12px">${t("pendente…")}</span></div>`).join("")}</div>` : "") +
    `<div class="fr-sec"><span class="label">${t("Amigos")}</span>${d.friends.length ? d.friends.map(frRow).join("") : `<p class="muted" style="font-size:13px">${t("Sem amigos ainda — adiciona pelo email/utilizador.")}</p>`}</div>`;
  box.querySelectorAll("[data-acc]").forEach((b) => (b.onclick = async () => { try { await api(`/friends/requests/${b.dataset.acc}/accept`, { method: "POST" }); renderFriends(card); } catch (e) { toast(e.message); } }));
  box.querySelectorAll("[data-dec]").forEach((b) => (b.onclick = async () => { try { await api(`/friends/requests/${b.dataset.dec}/decline`, { method: "POST" }); renderFriends(card); } catch (e) { toast(e.message); } }));
  box.querySelectorAll("[data-unfr]").forEach((b) => (b.onclick = async () => { if (!confirm(t("Remover este amigo?"))) return; try { await api(`/friends/${b.dataset.unfr}`, { method: "DELETE" }); renderFriends(card); } catch (e) { toast(e.message); } }));
  box.querySelectorAll("[data-duel]").forEach((b) => (b.onclick = () => challengeFriend(b.dataset.duel)));
  box.querySelectorAll("[data-msg]").forEach((b) => (b.onclick = () => openThread(b.dataset.msg, b.dataset.name)));
  box.querySelectorAll("[data-prof]").forEach((b) => (b.onclick = () => openUserProfile(b.dataset.prof)));
}

/* ---- people search (full page) ---- */
async function openUserSearch(q = "") {
  stopDuelPolling(); stopMatchmaking(); stopDmPolling();
  document.querySelectorAll(".nav__i").forEach((b) => b.classList.remove("is-active"));
  $("#view").innerHTML = `
    <div class="view__head"><h1>${t("Pessoas")}</h1><p>${t("Procura colegas pelo nome ou utilizador.")}</p></div>
    <div class="card">
      <form class="row" id="usForm" style="margin-bottom:12px">
        <input id="usQ" class="searchbar" style="flex:1;max-width:420px" placeholder="${t("nome ou utilizador…")}" value="${esc(q)}" autocomplete="off">
        <button class="btn btn--sm">${icon("search", 14)} ${t("Procurar")}</button>
      </form>
      <div id="usResults"><p class="muted">${t("Escreve pelo menos 2 letras.")}</p></div>
    </div>`;
  $("#usForm").onsubmit = (e) => { e.preventDefault(); runUserSearch(); };
  $("#usQ").focus();
  if (q.trim().length >= 2) runUserSearch();
}

async function runUserSearch() {
  const q = $("#usQ").value.trim();
  if (q.length < 2) { $("#usResults").innerHTML = `<p class="muted">${t("Escreve pelo menos 2 letras.")}</p>`; return; }
  let rows = [];
  try { rows = await api(`/users/search?q=${encodeURIComponent(q)}`); } catch (e) { return toast(e.message); }
  const relBadge = (r) =>
    r.status === "friends" ? `<span class="badge-ok">${t("Amigos")}</span>`
    : r.status === "outgoing" ? `<span class="badge-pend">${t("pendente…")}</span>`
    : r.status === "incoming" ? `<button class="btn btn--ghost btn--sm" data-acc2="${r.request_id}">${icon("check", 14)} ${t("Aceitar")}</button>`
    : `<button class="btn btn--ghost btn--sm" data-add="${r.user_id}">${icon("plus", 14)} ${t("Adicionar")}</button>`;
  $("#usResults").innerHTML = rows.length ? rows.map((r) => `<div class="fr-row">
      <span style="display:inline-flex;align-items:center;gap:8px">${userAvatar(r, 30)} <b>${esc(r.display_name)}</b> <span class="muted" style="font-size:12px">${esc(r.username || "")}</span>${r.role !== "student" ? ` <span class="tag">${esc(r.role)}</span>` : ""}</span>
      <span class="row" style="gap:6px">
        <button class="btn btn--ghost btn--sm" data-prof="${r.user_id}" title="${t("Ver perfil")}">${icon("user", 14)} ${t("Perfil")}</button>
        ${relBadge(r)}
      </span></div>`).join("")
    : `<p class="muted">${t("Ninguém encontrado.")}</p>`;
  $("#usResults").querySelectorAll("[data-prof]").forEach((b) => (b.onclick = () => openUserProfile(b.dataset.prof)));
  $("#usResults").querySelectorAll("[data-add]").forEach((b) => (b.onclick = async () => {
    try { await api("/friends/requests", { method: "POST", body: { user_id: b.dataset.add } }); toast(t("Pedido enviado")); runUserSearch(); }
    catch (e) { toast(e.message); }
  }));
  $("#usResults").querySelectorAll("[data-acc2]").forEach((b) => (b.onclick = async () => {
    try { await api(`/friends/requests/${b.dataset.acc2}/accept`, { method: "POST" }); toast(t("Pedido aceite")); runUserSearch(); }
    catch (e) { toast(e.message); }
  }));
}

/* ---- public profile page ---- */
async function openUserProfile(uid) {
  stopDuelPolling(); stopMatchmaking(); stopDmPolling();
  document.querySelectorAll(".nav__i").forEach((b) => b.classList.remove("is-active"));
  let p;
  try { p = await api(`/users/${uid}/profile?subject=${SUBJECT}`); } catch (e) { return toast(e.message); }
  const dfmt = (iso) => new Date(iso).toLocaleDateString(I18N.lang === "pt" ? "pt-PT" : I18N.lang);
  const actions = p.status === "friends"
    ? `<button class="btn btn--ghost btn--sm" id="upMsg">${icon("chat", 14)} ${t("Mensagem")}</button>
       <button class="btn btn--ghost btn--sm" id="upDuel">${icon("trophy", 14)} ${t("Desafiar")}</button>`
    : p.status === "outgoing" ? `<span class="badge-pend">${t("pendente…")}</span>`
    : p.status === "incoming" ? `<button class="btn btn--ghost btn--sm" id="upAcc">${icon("check", 14)} ${t("Aceitar pedido")}</button>`
    : `<button class="btn btn--ghost btn--sm" id="upAdd">${icon("plus", 14)} ${t("Adicionar amigo")}</button>`;
  $("#view").innerHTML = `
    <div class="view__head" style="display:flex;align-items:center;justify-content:space-between">
      <h1>${t("Perfil")}</h1>
      <button class="btn btn--ghost btn--sm" id="upBack">${t("← Voltar")}</button>
    </div>
    <div class="card">
      <div class="uphead">
        ${userAvatar(p, 72)}
        <div>
          <h2 style="font-family:'Century Gothic','Jost',sans-serif">${esc(p.display_name)}</h2>
          <p class="muted">${p.username ? "@" + esc(p.username) + " · " : ""}${p.role !== "student" ? esc(p.role) + " · " : ""}${t("membro desde")} ${dfmt(p.member_since)}</p>
        </div>
        <span class="row" style="margin-left:auto;gap:8px">${actions}</span>
      </div>
      <div class="stat" style="margin-top:16px">
        ${p.rank != null ? `<div><span class="label">${esc((SUBJECTS.find((s) => s.key === SUBJECT) || {}).name || SUBJECT)}</span><b style="display:inline-flex;align-items:center;gap:6px">${rankLogo(p.rank, 26)} ${p.rank} · ${p.xp} EP</b></div>` : ""}
        <div><span class="label">${t("Duelos")} ${t("V / D / E")}</span><b>${p.duel_wins} / ${p.duel_losses} / ${p.duel_draws}</b></div>
        <div><span class="label">👏 Kudos</span><b>${p.kudos}</b></div>
        <div><span class="label">${t("Conquistas")}</span><b>${p.achievements_unlocked}/${p.achievements_total}</b></div>
      </div>
    </div>`;
  $("#upBack").onclick = () => go("duels");
  if ($("#upAdd")) $("#upAdd").onclick = async () => {
    try { await api("/friends/requests", { method: "POST", body: { user_id: uid } }); toast(t("Pedido enviado")); openUserProfile(uid); }
    catch (e) { toast(e.message); }
  };
  if ($("#upAcc")) $("#upAcc").onclick = async () => {
    try { await api(`/friends/requests/${p.request_id}/accept`, { method: "POST" }); toast(t("Pedido aceite")); openUserProfile(uid); }
    catch (e) { toast(e.message); }
  };
  if ($("#upMsg")) $("#upMsg").onclick = () => openThread(uid, p.display_name);
  if ($("#upDuel")) $("#upDuel").onclick = () => challengeFriend(uid);
}

/* ---- direct messages: modal thread, polls while open ---- */
let _dmPoll = null, _dmOther = null;
function stopDmPolling() { if (_dmPoll) clearInterval(_dmPoll); _dmPoll = null; _dmOther = null; }

async function openThread(otherId, name) {
  stopDmPolling();
  _dmOther = otherId;
  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel" style="max-width:460px">
      <div class="modal__hd"><h3>${icon("chat", 16)} ${esc(name)}</h3><button class="iconbtn" id="mClose">${icon("plus", 18)}</button></div>
      <div class="modal__body">
        <div class="dm" id="dmBox"><p class="muted">${t("A carregar…")}</p></div>
        <form class="chat__in" id="dmForm" style="margin-top:10px">
          <input id="dmText" maxlength="500" placeholder="${t("Escreve uma mensagem…")}" autocomplete="off">
          <button class="btn btn--sm">${t("Enviar")}</button>
        </form>
      </div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  const close = () => { stopDmPolling(); closeModal(); renderFriends(); updateDuelBadge(); };
  $("#mClose").onclick = close; $("#modal .modal__backdrop").onclick = close;
  $("#dmForm").onsubmit = async (e) => {
    e.preventDefault();
    const txt = $("#dmText").value.trim(); if (!txt) return;
    $("#dmText").value = "";
    try { await api(`/messages/${otherId}`, { method: "POST", body: { text: txt } }); await refreshThread(); }
    catch (err) { toast(err.message); }
  };
  await refreshThread();
  _dmPoll = setInterval(refreshThread, 4000);
}

async function refreshThread() {
  if (!_dmOther || !$("#dmBox")) { stopDmPolling(); return; }
  let msgs = [];
  try { msgs = await api(`/messages/${_dmOther}`); } catch { return; }
  const fmtT = (iso) => new Date(iso).toLocaleTimeString(I18N.lang === "pt" ? "pt-PT" : I18N.lang, { hour: "2-digit", minute: "2-digit" });
  const atBottom = $("#dmBox").scrollHeight - $("#dmBox").scrollTop - $("#dmBox").clientHeight < 40;
  $("#dmBox").innerHTML = msgs.length
    ? msgs.map((m) => `<div class="dm__m ${m.from_id === USER.id ? "dm__m--me" : ""}"><span>${esc(m.text)}</span><small>${fmtT(m.created_at)}</small></div>`).join("")
    : `<p class="muted" style="font-size:13px">${t("Ainda sem mensagens — diz olá!")}</p>`;
  if (atBottom) $("#dmBox").scrollTop = $("#dmBox").scrollHeight;
}

// challenging always asks which discipline first (duels are per-subject)
function challengeFriend(opponentId) {
  if (SUBJECTS.length <= 1) return createDuel(opponentId, SUBJECT || (SUBJECTS[0] || {}).key);
  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel" style="max-width:380px">
      <div class="modal__hd"><h3>${t("Duelo — escolher disciplina")}</h3><button class="iconbtn" id="mClose">${icon("plus", 18)}</button></div>
      <div class="modal__body"><div class="subjpick">
        ${SUBJECTS.map((s) => `<button class="subjpick__it ${s.key === SUBJECT ? "is-active" : ""}" data-subj="${s.key}">${subjectIcon(s.icon, 18)}<span>${esc(s.name)}</span></button>`).join("")}
      </div></div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  $("#mClose").onclick = closeModal; $("#modal .modal__backdrop").onclick = closeModal;
  $("#modal").querySelectorAll("[data-subj]").forEach((b) => (b.onclick = () => {
    closeModal();
    createDuel(opponentId, b.dataset.subj);
  }));
}

async function createDuel(opponentId, subject) {
  try {
    const r = await api("/duels", { method: "POST", body: { opponent_id: opponentId, subject } });
    toast(t("Desafio enviado!"));
    openDuel(r.id);
  } catch (e) { toast(e.message); }
}

async function renderDuelList() {
  let duels;
  try { duels = await api("/duels"); } catch (e) { $("#duBox").innerHTML = `<p class="err">${e.message}</p>`; return; }
  if (!duels.length) { $("#duBox").innerHTML = `<p class="muted" style="font-size:13px">${t("Sem duelos. Desafia um amigo.")}</p>`; return; }
  const STATUS = {
    pending: t("Convite pendente"), setup: t("A preparar"), active: t("A decorrer"),
    complete: t("Terminado"), declined: t("Recusado"), forfeited: t("Desistência"), cancelled: t("Cancelado"),
  };
  $("#duBox").innerHTML = duels.map((d) => {
    let badge = STATUS[d.status] || d.status;
    if (d.status === "complete" || d.status === "forfeited")
      badge = d.is_draw ? t("Empate") : (d.won ? t("Vitória") : t("Derrota"));
    const cls = (d.status === "complete" || d.status === "forfeited") ? (d.is_draw ? "" : (d.won ? "win" : "loss")) : "";
    const incoming = d.status === "pending" && !d.is_challenger;
    const myTurn = d.needs_my_action && ["setup", "active"].includes(d.status);
    return `<div class="du-row ${myTurn || incoming ? "du-row--act" : ""}">
      <span><b>vs ${esc(d.opponent_name)}</b> <span class="du-badge ${cls}">${badge}</span>${d.ranked ? ` <span class="du-badge du-badge--ranked">${t("Ranked")}</span>` : ""}${myTurn ? ` <span class="du-badge du-badge--act">${t("A tua vez")}</span>` : ""}
        ${["active", "complete", "forfeited"].includes(d.status) ? `<span class="muted" style="font-size:12px"> · ${d.my_points}–${d.opp_points}</span>` : ""}</span>
      <span class="row" style="gap:6px">
        ${incoming ? `<button class="btn btn--sm" data-acc="${d.id}">${t("Aceitar")}</button><button class="btn btn--ghost btn--sm" data-dec="${d.id}">${t("Recusar")}</button>`
          : d.status === "pending" && d.is_challenger ? `<button class="btn btn--ghost btn--sm" data-open="${d.id}">${t("Ver")}</button><button class="btn btn--ghost btn--sm" data-cancel="${d.id}">${t("Cancelar")}</button>`
          : (["setup", "active"].includes(d.status) ? `<button class="btn btn--sm" data-open="${d.id}">${t("Entrar|duelo")}</button>`
          : `<button class="btn btn--ghost btn--sm" data-open="${d.id}">${t("Ver")}</button>`)}
      </span></div>`;
  }).join("");
  $("#duBox").querySelectorAll("[data-open]").forEach((b) => (b.onclick = () => openDuel(b.dataset.open)));
  $("#duBox").querySelectorAll("[data-acc]").forEach((b) => (b.onclick = async () => { try { await api(`/duels/${b.dataset.acc}/accept`, { method: "POST" }); openDuel(b.dataset.acc); } catch (e) { toast(e.message); } }));
  $("#duBox").querySelectorAll("[data-dec]").forEach((b) => (b.onclick = async () => { try { await api(`/duels/${b.dataset.dec}/decline`, { method: "POST" }); renderDuelList(); } catch (e) { toast(e.message); } }));
  $("#duBox").querySelectorAll("[data-cancel]").forEach((b) => (b.onclick = async () => { try { await api(`/duels/${b.dataset.cancel}/cancel`, { method: "POST" }); toast(t("Desafio cancelado")); renderDuelList(); } catch (e) { toast(e.message); } }));
}

/* ---- arena (polls server) ---- */
function openDuel(id) {
  stopDuelPolling(); stopMatchmaking();
  _duelId = id; _duelSig = ""; _duelSecs = null;
  $("#view").innerHTML = `<div class="view__head" style="display:flex;align-items:center;justify-content:space-between">
      <div><h1>${t("Duelo")}</h1><p class="muted" id="duelSub">${t("A carregar…")}</p></div>
      <button class="btn btn--ghost btn--sm" id="duBack">${t("← Voltar")}</button>
    </div>
    <div id="duelArena"><div class="loader"><div class="loader__ring"></div><span>${t("A carregar…")}</span></div></div>`;
  $("#duBack").onclick = () => go("duels");
  pollDuel();
  _duelPoll = setInterval(pollDuel, 2000);
  _duelTick = setInterval(() => {
    if (_duelSecs != null) { _duelSecs = Math.max(0, _duelSecs - 1); const t = $("#duelTimer"); if (t) t.textContent = fmtClock(_duelSecs); }
  }, 1000);
}

async function pollDuel() {
  if (!_duelId) return;
  let d;
  try { d = await api(`/duels/${_duelId}`); } catch (e) { return; }
  if (_duelId !== d.id) return;  // changed mid-flight
  _duelSecs = d.seconds_left;
  const sig = [d.status, d.phase, d.current_round, d.current?.i_am_asker, d.current?.question,
    d.current?.my_answered, d.current?.opp_answered, d.result, d.my_points, d.opp_points,
    d.history.length, d.opp_material_picked, d.my_material_id, d.kudos_given].join("|");
  if (sig === _duelSig) return;  // only timer changed -> no re-render (keeps focus while typing)
  _duelSig = sig;
  renderDuelArena(d);
}

function renderDuelArena(d) {
  $("#duelSub").textContent = `${esc(d.my_name)} vs ${esc(d.opponent_name)} · ${esc(d.subject_name)}`;
  const arena = $("#duelArena");
  const score = `<div class="du-score"><div class="du-score__me"><span class="label">${t("Tu")}</span><b>${d.my_points}</b></div><div class="du-score__x">–</div><div class="du-score__opp"><span class="label" style="display:inline-flex;align-items:center;gap:6px">${userAvatar({ avatar: d.opponent_avatar, photo: d.opponent_photo, user_id: d.opponent_id, display_name: d.opponent_name }, 22)} ${esc(d.opponent_name)}</span><b>${d.opp_points}</b></div></div>`;
  const timer = (lbl) => `<div class="du-timer"><span class="label">${lbl}</span><span id="duelTimer" class="du-timer__v">${fmtClock(_duelSecs)}</span></div>`;
  const forfeitBtn = `<button class="btn btn--ghost btn--sm" id="duForfeit" style="color:var(--red)">${t("Desistir")}</button>`;
  const hist = historyHtml(d);

  const cancelBtn = `<button class="btn btn--ghost btn--sm" id="duCancel">${t("Cancelar desafio")}</button>`;
  let body = "";
  if (d.status === "pending") {
    body = `<div class="du-wait">${icon("trophy", 28)}<p>${t("À espera que <b>{name}</b> aceite o desafio…", { name: esc(d.opponent_name) })}</p><p class="muted" style="font-size:12.5px">${t("Podes cancelar sem consequências enquanto ele não aceitar.")}</p>${cancelBtn}</div>`;
  } else if (d.status === "declined") {
    body = `<div class="du-wait"><p>${t("Desafio recusado.")}</p></div>`;
    stopDuelPolling();
  } else if (d.status === "cancelled") {
    body = `<div class="du-wait"><p>${t("Desafio cancelado — sem consequências.")}</p></div>`;
    stopDuelPolling();
  } else if (d.status === "setup") {
    const mine = d.my_material_id ? `<span class="badge-ok">${icon("check", 12)} ${esc(d.my_material_title || t("escolhido"))}</span>` : `<button class="btn btn--sm" id="duPick">${icon("book", 14)} ${t("Escolher material")}</button>`;
    const opp = d.opp_material_picked ? `<span class="badge-ok">${icon("check", 12)} ${t("escolhido")}</span>` : `<span class="badge-pend">${t("à espera")}</span>`;
    body = `<div class="card"><h3 style="font-size:16px;margin-bottom:6px">${t("Preparação")}</h3>
      <p class="muted" style="font-size:13px;margin-bottom:12px">${t("Cada jogador escolhe um material de <b>{subj}</b>. O duelo começa quando ambos escolherem (sorteio de quem começa).", { subj: esc(d.subject_name) })}</p>
      <div class="du-prep"><div class="du-prep__row"><span>${t("O teu material")}</span>${mine}</div><div class="du-prep__row"><span>${esc(d.opponent_name)}</span>${opp}</div></div>
      <div style="margin-top:14px">${forfeitBtn}</div></div>`;
  } else if (d.status === "active") {
    const c = d.current || {};
    let phase = "";
    if (d.phase === "question") {
      if (c.i_am_asker) {
        phase = `<div class="card du-phase"><span class="du-phase__tag">${icon("pencil", 14)} ${t("Cria a tua pergunta")}</span>${timer(t("Tempo"))}
          <textarea id="duQText" rows="3" placeholder="${t("Escreve uma pergunta sobre o teu material…")}"></textarea>
          <button class="btn btn--sm" id="duQSend" style="align-self:flex-start;margin-top:8px">${t("Enviar pergunta")}</button></div>`;
      } else {
        phase = `<div class="card du-phase"><span class="du-phase__tag">${icon("user", 14)} ${t("{name} está a criar a pergunta…", { name: esc(c.asker_name) })}</span>${timer(t("Tempo"))}<div class="loader"><div class="loader__ring"></div><span>${t("Aguarda")}</span></div></div>`;
      }
    } else if (d.phase === "answer") {
      const q = `<div class="du-q"><span class="label">${t("Pergunta de {name}", { name: esc(c.asker_name) })}</span><div class="du-q__t">${esc(c.question)}</div></div>`;
      if (!c.my_answered) {
        phase = `<div class="card du-phase"><span class="du-phase__tag">${icon("flame", 14)} ${t("Responde! (em simultâneo)")}</span>${timer(t("Tempo"))}${q}
          <textarea id="duAnsText" rows="4" placeholder="${t("A tua resposta…")}"></textarea>
          <button class="btn btn--sm" id="duAnsSend" style="align-self:flex-start;margin-top:8px">${t("Enviar resposta")}</button></div>`;
      } else {
        phase = `<div class="card du-phase"><span class="du-phase__tag">${icon("check", 14)} ${t("Resposta enviada")}</span>${timer(t("Tempo"))}${q}
          <p class="muted">${c.opp_answered ? t("Ambos responderam — a avaliar…") : t("À espera de <b>{name}</b>…", { name: esc(d.opponent_name) })}</p></div>`;
      }
    } else if (d.phase === "judging") {
      phase = `<div class="card du-phase"><span class="du-phase__tag">${icon("sparkle", 14)} ${t("A IA está a avaliar a ronda…")}</span><div class="loader"><div class="loader__ring"></div><span>${t("A julgar")}</span></div></div>`;
    }
    body = `${score}<div class="du-round-lbl">${t("Ronda {i} de {n}", { i: d.current_round + 1, n: d.total_rounds })}</div>${phase}${hist}<div style="margin-top:12px">${forfeitBtn}</div>`;
  } else if (d.status === "complete" || d.status === "forfeited") {
    const r = d.result;
    const txt = d.forfeited ? (d.i_forfeited ? t("Desististe") : t("{name} desistiu", { name: esc(d.opponent_name) })) :
      (r === "win" ? t("Venceste!") : r === "loss" ? t("Derrota") : t("Empate"));
    const ratingLine = (d.ranked && d.rating_delta != null)
      ? `<p class="du-rating ${d.rating_delta >= 0 ? "up" : "down"}">${icon("sparkle", 14)} Rating ${d.rating_delta >= 0 ? "+" : ""}${d.rating_delta}</p>` : "";
    const again = d.ranked
      ? `<button class="btn btn--sm" id="duAgain" data-mode="ranked">${icon("trophy", 14)} ${t("Nova partida ranked")}</button>`
      : `<button class="btn btn--sm" id="duAgain" data-mode="rematch">${icon("swords", 14)} ${t("Desforra")}</button>`;
    const kudosBtn = d.kudos_given ? `<span class="badge-ok">👏 ${t("Kudos enviados")}</span>`
      : `<button class="btn btn--ghost btn--sm" id="duKudos">👏 ${t("Dar kudos a {name}", { name: esc(d.opponent_name) })}</button>`;
    const msgBtn = `<button class="btn btn--ghost btn--sm" id="duMsg">${icon("chat", 14)} ${t("Mensagem")}</button>`;
    body = `${d.ranked ? `<div class="du-ranked-tag">${icon("sparkle", 12)} ${t("Ranked")}</div>` : ""}${score}<div class="du-result du-result--${r}">${icon(r === "win" ? "trophy" : "shield", 30)}<h2>${txt}</h2><p class="muted">${d.my_points}–${d.opp_points}</p>${ratingLine}<div class="row" style="margin-top:12px;justify-content:center;gap:8px">${again}${kudosBtn}${d.ranked ? "" : msgBtn}</div></div>${hist}`;
    if (r === "win" && !d.forfeited) { try { playPop(); } catch {} }
    stopDuelPolling();
  }
  arena.innerHTML = body;

  // wire actions
  if ($("#duCancel")) $("#duCancel").onclick = async () => {
    try { await api(`/duels/${d.id}/cancel`, { method: "POST" }); toast(t("Desafio cancelado")); go("duels"); }
    catch (e) { toast(e.message); }
  };
  if ($("#duMsg")) $("#duMsg").onclick = () => openThread(d.opponent_id, d.opponent_name);
  if ($("#duKudos")) $("#duKudos").onclick = async () => {
    try { await api(`/duels/${d.id}/kudos`, { method: "POST" }); toast(t("Kudos enviados") + " 👏"); _duelSig = ""; pollDuel(); }
    catch (e) { toast(e.message); }
  };
  if ($("#duAgain")) $("#duAgain").onclick = async () => {
    if ($("#duAgain").dataset.mode === "ranked") { go("duels"); setTimeout(() => startMatchmaking(), 400); return; }
    try {
      const nd = await api("/duels", { method: "POST", body: { opponent_id: d.opponent_id, subject: d.subject } });
      toast(t("Desforra enviada — à espera do adversário"));
      openDuel(nd.id);
    } catch (e) { toast(e.message); }
  };
  if ($("#duForfeit")) $("#duForfeit").onclick = async () => {
    // inside the grace window leaving is free — try that first
    if (!d.ranked && d.status === "setup") {
      try {
        await api(`/duels/${d.id}/cancel`, { method: "POST" });
        toast(t("Saíste sem consequências")); go("duels"); return;
      } catch {}
    }
    if (!confirm(t("Desistir do duelo? O adversário ganha."))) return;
    try { await api(`/duels/${d.id}/forfeit`, { method: "POST" }); _duelSig = ""; pollDuel(); } catch (e) { toast(e.message); }
  };
  if ($("#duPick")) $("#duPick").onclick = () => openDuelMaterialPicker(d.subject, async (mid) => {
    try { await api(`/duels/${d.id}/material`, { method: "POST", body: { material_id: mid } }); _duelSig = ""; pollDuel(); } catch (e) { toast(e.message); }
  });
  const qT = $("#duQText");
  if (qT) {
    const dk = "q" + d.current_round;
    if (_duelDraft.key === dk) qT.value = _duelDraft.text;
    qT.oninput = () => (_duelDraft = { key: dk, text: qT.value });
    qT.onkeydown = (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("#duQSend").click(); };
    $("#duQSend").onclick = async () => {
      const text = qT.value.trim(); if (!text) return toast(t("Escreve a pergunta"));
      $("#duQSend").disabled = true;
      try { await api(`/duels/${d.id}/question`, { method: "POST", body: { text } }); _duelDraft = { key: "", text: "" }; _duelSig = ""; pollDuel(); }
      catch (e) { toast(e.message); $("#duQSend").disabled = false; }
    };
  }
  const aT = $("#duAnsText");
  if (aT) {
    const dk = "a" + d.current_round;
    if (_duelDraft.key === dk) aT.value = _duelDraft.text;
    aT.oninput = () => (_duelDraft = { key: dk, text: aT.value });
    aT.onkeydown = (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("#duAnsSend").click(); };
    $("#duAnsSend").onclick = async () => {
      const text = aT.value.trim(); if (!text) return toast(t("Escreve a resposta"));
      $("#duAnsSend").disabled = true;
      try { await api(`/duels/${d.id}/answer`, { method: "POST", body: { text } }); _duelDraft = { key: "", text: "" }; _duelSig = ""; pollDuel(); }
      catch (e) { toast(e.message); $("#duAnsSend").disabled = false; }
    };
  }
}

function historyHtml(d) {
  if (!d.history.length) return "";
  return `<div class="du-hist"><span class="label">${t("Rondas anteriores")}</span>${d.history.map((r) => `
    <details class="du-hist__r du-hist__r--${r.outcome}">
      <summary>${t("Ronda {n}", { n: r.ordinal + 1 })} · ${r.outcome === "win" ? t("ganhaste") : r.outcome === "loss" ? t("perdeste") : t("empate")} <span class="muted">(+${r.my_delta}/+${r.opp_delta})</span></summary>
      <div class="du-hist__body">
        <p><b>${t("Pergunta")} (${esc(r.asker_name)}):</b> ${esc(r.question)}</p>
        <p><b>${t("Tu")}:</b> ${esc(r.my_answer) || `<span class='muted'>${t("(sem resposta)")}</span>`}</p>
        <p><b>${esc(d.opponent_name)}:</b> ${esc(r.opp_answer) || `<span class='muted'>${t("(sem resposta)")}</span>`}</p>
        ${r.reason ? `<p class="muted">${icon("sparkle", 12)} ${esc(r.reason)}</p>` : ""}
      </div>
    </details>`).join("")}</div>`;
}

async function openDuelMaterialPicker(subjectKey, onPick) {
  let mats = [];
  try { mats = await api(`/subjects/${subjectKey}/material`); } catch {}
  $("#modal").innerHTML = `
    <div class="modal__backdrop"></div>
    <div class="modal__panel">
      <div class="modal__hd"><h3>${t("Escolher material para o duelo")}</h3><button class="iconbtn" id="mClose">${icon("plus", 18)}</button></div>
      <div class="modal__body">
        ${mats.length ? `<div class="mkt-grid" id="pickGrid">${mats.map(matPickCard).join("")}</div>`
          : `<p class="muted">${t("Sem materiais nesta disciplina. Cria materiais primeiro em Materiais.")}</p>`}
      </div>
    </div>`;
  $("#modal").classList.add("show");
  $("#mClose").querySelector("svg").style.transform = "rotate(45deg)";
  const close = () => closeModal();
  $("#mClose").onclick = close; $("#modal .modal__backdrop").onclick = close;
  $("#pickGrid") && $("#pickGrid").querySelectorAll("[data-pick]").forEach((c) => (c.onclick = () => { closeModal(); onPick(c.dataset.pick); }));
}

/* ---- start ---- */
if (TOKEN) boot().then(preloadConcepts);
else $("#auth").style.display = "grid";

// offline shell (network-first, so it never serves stale assets while online)
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
