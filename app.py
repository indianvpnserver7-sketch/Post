import json
import os
import re
from datetime import datetime, timezone
from threading import Lock
from flask import Flask, jsonify, redirect, request, Response

app = Flask(__name__)

DATA_FILE = os.environ.get("DATA_FILE", "links.json")
MAX_LINKS = int(os.environ.get("MAX_LINKS", "500"))
URL_RE = re.compile(r"^https://[a-zA-Z0-9.-]+(?::\d+)?(?:/[^\s]*)?$")
LOCK = Lock()


def _load_links():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_links(links):
    tmp = f"{DATA_FILE}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(links[:MAX_LINKS], f, indent=2)
    os.replace(tmp, DATA_FILE)


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>PixelArt · Links</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath d='M24 4L42 14V34L24 44L6 34V14L24 4Z' stroke='%23e2588d' stroke-width='3' fill='none'/%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400;1,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #220f17;
      --bg-2: #3f1e2b;
      --bg-3: #57293c;
      --bg-5: #1a0b11;
      --border-2: #ebd5dd70;
      --border-3: #ebd5dd30;
      --border-4: #ebd5dd1a;
      --text: #c0c0c0;
      --bright-text: #ffffff;
      --accent: #e2588d;
      --accent-2: #c44ac4;
      --radius: 15px;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow-x: hidden;
      font-feature-settings: "tnum" 1, "zero" 1;
      -webkit-font-smoothing: antialiased;
    }
    ::selection { background: var(--accent); color: var(--bright-text); }
    button { font-family: inherit; cursor: pointer; }
    a { color: var(--accent); text-decoration: none; }

    .grid-bg {
      position: fixed; inset: 0; z-index: 0; pointer-events: none;
      background-image:
        linear-gradient(to right, #8080800c 1px, transparent 1px),
        linear-gradient(to bottom, #8080800a 1px, transparent 1px);
      background-size: 14px 14px;
      -webkit-mask-image: radial-gradient(at center, black 10%, transparent 90%);
      mask-image: radial-gradient(at center, black 10%, transparent 90%);
      animation: gridDrift 60s linear infinite;
    }
    @keyframes gridDrift { from { background-position: 0 0; } to { background-position: 14px 14px; } }

    .aurora { position: fixed; inset: 0; z-index: 1; pointer-events: none; overflow: hidden; }
    .aurora-blob { position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.28; }
    .aurora-1 {
      width: 60vw; height: 60vw; top: -22vw; left: -16vw;
      background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
      animation: float1 24s ease-in-out infinite;
    }
    .aurora-2 {
      width: 55vw; height: 55vw; bottom: -22vw; right: -16vw;
      background: radial-gradient(circle, var(--accent-2) 0%, transparent 70%);
      animation: float2 30s ease-in-out infinite;
    }
    @keyframes float1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(5vw,4vw) scale(1.12); } }
    @keyframes float2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-5vw,-3vw) scale(1.1); } }

    .shell {
      position: relative; z-index: 2;
      max-width: 780px;
      margin: 0 auto;
      padding: 36px 18px 80px;
    }

    .hero { text-align: center; margin-bottom: 26px; }
    .hero-logo {
      font-family: 'Playfair Display', Georgia, serif;
      font-style: italic; font-weight: 400;
      font-size: clamp(48px, 10vw, 68px);
      letter-spacing: -2.5px; line-height: 1;
      background: linear-gradient(180deg, var(--bright-text) 30%, var(--accent) 100%);
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 0 24px color-mix(in srgb, var(--accent) 42%, transparent));
    }
    .hero-sub {
      font-family: 'Playfair Display', Georgia, serif;
      font-style: italic; font-size: 13px; color: var(--text);
      margin-top: 8px; letter-spacing: 0.4px;
      display: inline-flex; align-items: center; gap: 10px;
    }
    .status-pill {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 3px 10px; border-radius: 999px;
      background: rgba(74, 222, 128, 0.12);
      border: 1px solid rgba(74, 222, 128, 0.35);
      color: #4ade80; font-family: 'Inter', sans-serif;
      font-style: normal; font-size: 11px; font-weight: 600;
    }
    .status-pill.empty {
      background: rgba(255,255,255,0.05);
      border-color: var(--border-3); color: var(--text);
    }
    .status-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: currentColor; box-shadow: 0 0 8px currentColor;
      animation: pulse 1.8s ease-in-out infinite;
    }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

    .latest-card {
      position: relative; overflow: hidden;
      border-radius: 20px;
      padding: 22px;
      margin-bottom: 24px;
      background: linear-gradient(135deg,
        color-mix(in srgb, var(--bg-2) 82%, transparent),
        color-mix(in srgb, var(--bg-5) 88%, transparent));
      backdrop-filter: blur(22px) saturate(160%);
      -webkit-backdrop-filter: blur(22px) saturate(160%);
      border: 1.5px solid color-mix(in srgb, var(--accent) 45%, transparent);
      box-shadow:
        0 20px 50px rgba(0,0,0,0.45),
        0 0 40px color-mix(in srgb, var(--accent) 18%, transparent),
        inset 0 1px 0 rgba(255,255,255,0.12);
      animation: cardIn 0.35s cubic-bezier(.34,1.56,.64,1);
    }
    @keyframes cardIn { from { opacity: 0; transform: translateY(14px) scale(0.98); } to { opacity: 1; transform: none; } }

    .latest-top {
      display: flex; align-items: center; justify-content: space-between;
      gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
    }
    .latest-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 11px; border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #fff; font-size: 10.5px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 1px;
      box-shadow: 0 4px 14px color-mix(in srgb, var(--accent) 40%, transparent);
    }
    .latest-rel { font-size: 12px; color: var(--text); opacity: 0.85; }

    .latest-url {
      display: block;
      font-size: clamp(15px, 3vw, 18px);
      font-weight: 600;
      color: var(--bright-text);
      word-break: break-all;
      line-height: 1.4;
      margin-bottom: 10px;
      transition: color 0.15s;
    }
    .latest-url:hover { color: var(--accent); }

    .latest-meta {
      display: flex; flex-wrap: wrap; gap: 14px;
      font-size: 12px; color: var(--text); opacity: 0.85;
      margin-bottom: 16px;
    }
    .latest-meta span { display: inline-flex; align-items: center; gap: 5px; }

    .latest-actions { display: flex; gap: 10px; flex-wrap: wrap; }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 8px;
      padding: 11px 18px; border-radius: 12px;
      font-size: 13px; font-weight: 600; border: none; transition: 0.18s;
    }
    .btn:active { transform: scale(0.97); }
    .btn-primary {
      flex: 1; min-width: 140px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #fff;
      box-shadow: 0 8px 24px color-mix(in srgb, var(--accent) 35%, transparent);
    }
    .btn-primary:hover { opacity: 0.94; box-shadow: 0 10px 28px color-mix(in srgb, var(--accent) 48%, transparent); }
    .btn-ghost {
      background: rgba(0,0,0,0.28);
      color: var(--bright-text);
      border: 1.5px solid var(--border-3);
    }
    .btn-ghost:hover { border-color: var(--accent); background: rgba(0,0,0,0.42); }

    .toolbar {
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 12px;
    }
    .search-box {
      flex: 1; min-width: 0;
      display: flex; align-items: center; gap: 10px;
      background: color-mix(in srgb, var(--bg) 72%, transparent 28%);
      backdrop-filter: blur(22px) saturate(160%);
      -webkit-backdrop-filter: blur(22px) saturate(160%);
      border: 2px solid var(--border-3);
      border-radius: var(--radius);
      padding: 0 8px 0 14px;
      height: 46px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      transition: 0.2s;
    }
    .search-box:focus-within {
      border-color: var(--accent);
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 16%, transparent), 0 8px 24px rgba(0,0,0,0.38);
    }
    .search-icon { color: var(--bright-text); opacity: 0.65; flex-shrink: 0; }
    .search-box input {
      flex: 1; min-width: 0;
      background: transparent; border: none; outline: none;
      color: var(--bright-text); font-size: 14px; font-family: inherit;
    }
    .search-box input::placeholder { color: var(--text); opacity: 0.55; }
    .clear-btn {
      width: 28px; height: 28px; border-radius: 50%;
      border: none; background: rgba(255,255,255,0.08);
      color: var(--text); font-size: 13px;
      display: none; align-items: center; justify-content: center;
    }
    .clear-btn.visible { display: flex; }
    .clear-btn:hover { background: rgba(255,255,255,0.16); color: var(--bright-text); }

    .refresh-btn {
      height: 46px; padding: 0 14px;
      border-radius: var(--radius);
      background: color-mix(in srgb, var(--bg) 72%, transparent 28%);
      backdrop-filter: blur(18px);
      border: 2px solid var(--border-3);
      color: var(--bright-text); font-size: 13px; font-weight: 500;
      display: inline-flex; align-items: center; gap: 6px;
      transition: 0.2s; flex-shrink: 0;
    }
    .refresh-btn:hover { border-color: var(--accent); }
    .refresh-btn.spinning svg { animation: spin 0.7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .stats-row {
      display: flex; align-items: center; justify-content: space-between;
      font-size: 11.5px; color: var(--text); opacity: 0.75;
      padding: 0 4px; margin-bottom: 18px;
    }

    .day-section {
      margin-bottom: 22px;
      animation: cardIn 0.3s ease backwards;
    }
    .day-header {
      display: flex; align-items: center; justify-content: space-between;
      gap: 10px;
      padding: 8px 4px 10px;
      margin-bottom: 8px;
      border-bottom: 1px solid var(--border-3);
    }
    .day-title {
      font-family: 'Playfair Display', Georgia, serif;
      font-style: italic; font-weight: 400;
      font-size: 20px; color: var(--bright-text);
      display: flex; align-items: center; gap: 8px;
    }
    .day-sub {
      font-family: 'Inter', sans-serif;
      font-style: normal; font-size: 12px; color: var(--text); opacity: 0.7;
    }
    .day-count {
      padding: 3px 10px; border-radius: 999px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--border-3);
      font-size: 11px; font-weight: 600; color: var(--accent);
      flex-shrink: 0;
    }

    .day-list { display: flex; flex-direction: column; gap: 8px; }
    .link-item {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      padding: 13px 15px;
      background: color-mix(in srgb, var(--bg) 68%, transparent 32%);
      backdrop-filter: blur(18px) saturate(140%);
      -webkit-backdrop-filter: blur(18px) saturate(140%);
      border: 1.5px solid var(--border-3);
      border-radius: 14px;
      transition: transform 0.18s, border-color 0.2s, box-shadow 0.2s;
    }
    .link-item:hover {
      transform: translateY(-2px);
      border-color: color-mix(in srgb, var(--accent) 65%, transparent);
      box-shadow: 0 10px 26px rgba(0,0,0,0.35);
    }
    .link-item.is-latest {
      border-color: color-mix(in srgb, var(--accent) 45%, transparent);
      background: linear-gradient(135deg,
        color-mix(in srgb, var(--accent) 10%, var(--bg)),
        color-mix(in srgb, var(--bg-2) 70%, transparent));
    }

    .link-main { flex: 1; min-width: 0; }
    .link-url-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 5px; }
    .link-url {
      font-size: 13.5px; font-weight: 600; color: var(--bright-text);
      word-break: break-all;
    }
    .link-url:hover { color: var(--accent); }
    .mini-badge {
      padding: 2px 7px; border-radius: 999px;
      background: color-mix(in srgb, var(--accent) 22%, transparent);
      border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
      color: var(--accent); font-size: 10px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.7px;
    }
    .link-time {
      font-size: 12px; color: var(--text); opacity: 0.8;
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    }

    .link-actions { display: flex; gap: 6px; flex-shrink: 0; }
    .icon-btn {
      padding: 7px 12px; border-radius: 10px;
      background: rgba(0,0,0,0.28);
      border: 1px solid var(--border-3);
      color: var(--bright-text); font-size: 12px; font-weight: 500;
      transition: 0.15s;
      display: inline-flex; align-items: center; gap: 5px;
    }
    .icon-btn:hover { border-color: var(--accent); background: rgba(0,0,0,0.45); }
    .icon-btn.ok { border-color: #4ade80; color: #4ade80; }

    .empty-state {
      text-align: center;
      padding: 48px 20px;
      background: color-mix(in srgb, var(--bg) 68%, transparent 32%);
      border: 1.5px dashed var(--border-3);
      border-radius: 18px;
      color: var(--text);
    }
    .empty-state h3 {
      font-family: 'Playfair Display', Georgia, serif;
      font-style: italic; font-weight: 400;
      font-size: 22px; color: var(--bright-text); margin-bottom: 6px;
    }
    .empty-state p { font-size: 13px; opacity: 0.8; }

    @media (max-width: 560px) {
      .shell { padding: 24px 14px 60px; }
      .link-item { flex-direction: column; align-items: stretch; }
      .link-actions { justify-content: flex-end; }
      .refresh-btn span { display: none; }
    }
  </style>
</head>
<body>
  <div class="grid-bg" aria-hidden="true"></div>
  <div class="aurora" aria-hidden="true">
    <div class="aurora-blob aurora-1"></div>
    <div class="aurora-blob aurora-2"></div>
  </div>

  <main class="shell">
    <header class="hero">
      <h1 class="hero-logo">pixelart</h1>
      <div class="hero-sub">
        <span>PixelArt://links</span>
        <span id="status-pill" class="status-pill empty">
          <span class="status-dot"></span>
          <span id="status-text">Checking…</span>
        </span>
      </div>
    </header>

    <section id="latest-wrap"></section>

    <div class="toolbar">
      <div class="search-box">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input id="search" type="text" placeholder="Search links, dates, or times…" autocomplete="off" spellcheck="false" />
        <button id="clear-search" class="clear-btn" type="button" title="Clear search">✕</button>
      </div>
      <button id="refresh-btn" class="refresh-btn" type="button" title="Refresh links">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>
        <span>Refresh</span>
      </button>
    </div>

    <div class="stats-row">
      <span id="stats-count">Loading history…</span>
      <span id="stats-sync">Auto-refresh: 15s</span>
    </div>

    <section id="history"></section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);
    let allLinks = [];

    function esc(s) {
      return String(s ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[c]));
    }

    function dayKey(iso) {
      const d = new Date(iso);
      if (isNaN(d)) return "unknown";
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${y}-${m}-${day}`;
    }

    function dayLabel(key, iso) {
      if (key === "unknown") return { title: "Unknown Date", sub: "" };
      const d = new Date(iso);
      const now = new Date();
      const todayKey = dayKey(now.toISOString());
      const yest = new Date(now);
      yest.setDate(now.getDate() - 1);
      const yestKey = dayKey(yest.toISOString());

      const formatted = d.toLocaleDateString(undefined, {
        weekday: "short", month: "short", day: "numeric", year: "numeric"
      });
      if (key === todayKey) return { title: "Today", sub: formatted };
      if (key === yestKey) return { title: "Yesterday", sub: formatted };
      return { title: formatted, sub: "" };
    }

    function fmtDateTime(iso) {
      const d = new Date(iso);
      if (isNaN(d)) return iso || "";
      return d.toLocaleString(undefined, {
        month: "short", day: "numeric", year: "numeric",
        hour: "numeric", minute: "2-digit", second: "2-digit"
      });
    }

    function relTime(iso) {
      const t = new Date(iso).getTime();
      if (isNaN(t)) return "";
      const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
      if (sec < 60) return `${sec}s ago`;
      const min = Math.floor(sec / 60);
      if (min < 60) return `${min}m ago`;
      const hr = Math.floor(min / 60);
      if (hr < 24) return `${hr}h ago`;
      const days = Math.floor(hr / 24);
      return `${days}d ago`;
    }

    async function copyText(text, btn) {
      try {
        await navigator.clipboard.writeText(text);
        const orig = btn.innerHTML;
        btn.classList.add("ok");
        btn.textContent = "Copied ✓";
        setTimeout(() => {
          btn.classList.remove("ok");
          btn.innerHTML = orig;
        }, 1400);
      } catch {
        prompt("Copy link:", text);
      }
    }

    function renderLatest(latest) {
      const wrap = $("latest-wrap");
      const pill = $("status-pill");
      const statusText = $("status-text");

      if (!latest) {
        pill.className = "status-pill empty";
        statusText.textContent = "Waiting for link";
        wrap.innerHTML = "";
        return;
      }

      pill.className = "status-pill";
      statusText.textContent = "Live";

      const posted = fmtDateTime(latest.posted_at);
      const lastSeen = latest.last_seen ? fmtDateTime(latest.last_seen) : posted;
      const ago = relTime(latest.last_seen || latest.posted_at);

      wrap.innerHTML = `
        <div class="latest-card">
          <div class="latest-top">
            <span class="latest-badge"><span class="status-dot"></span> Active Link</span>
            <span class="latest-rel">Last heartbeat ${esc(ago)}</span>
          </div>
          <a class="latest-url" href="${esc(latest.url)}" target="_blank" rel="noopener">${esc(latest.url)}</a>
          <div class="latest-meta">
            <span>📅 Posted: ${esc(posted)}</span>
            <span>🔄 Synced: ${esc(lastSeen)}</span>
          </div>
          <div class="latest-actions">
            <a class="btn btn-primary" href="${esc(latest.url)}" target="_blank" rel="noopener">Open PixelArt ↗</a>
            <button class="btn btn-ghost" type="button" id="copy-latest">Copy URL</button>
          </div>
        </div>
      `;
      $("copy-latest").addEventListener("click", function () {
        copyText(latest.url, this);
      });
    }

    function renderHistory() {
      const q = $("search").value.trim().toLowerCase();
      $("clear-search").classList.toggle("visible", q.length > 0);

      const latestUrl = allLinks[0] ? allLinks[0].url : null;
      const latestPosted = allLinks[0] ? allLinks[0].posted_at : null;

      const filtered = allLinks.filter((item) => {
        if (!q) return true;
        const k = dayKey(item.posted_at);
        const lbl = dayLabel(k, item.posted_at);
        const hay = [
          item.url,
          fmtDateTime(item.posted_at),
          lbl.title,
          lbl.sub,
          k
        ].join(" ").toLowerCase();
        return hay.includes(q);
      });

      $("stats-count").textContent = q
        ? `Showing ${filtered.length} of ${allLinks.length} link${allLinks.length === 1 ? "" : "s"}`
        : `${allLinks.length} link${allLinks.length === 1 ? "" : "s"} recorded`;

      const container = $("history");
      if (!allLinks.length) {
        container.innerHTML = `
          <div class="empty-state">
            <h3>No links posted yet</h3>
            <p>Start your Termux script and your tunnel URLs will appear here grouped by day.</p>
          </div>`;
        return;
      }

      if (!filtered.length) {
        container.innerHTML = `
          <div class="empty-state">
            <h3>No matching links</h3>
            <p>Try searching a different URL keyword, month, or date.</p>
          </div>`;
        return;
      }

      const groups = new Map();
      for (const item of filtered) {
        const k = dayKey(item.posted_at);
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(item);
      }

      const frag = document.createDocumentFragment();
      for (const [key, items] of groups.entries()) {
        const lbl = dayLabel(key, items[0].posted_at);
        const section = document.createElement("div");
        section.className = "day-section";

        const header = document.createElement("div");
        header.className = "day-header";
        header.innerHTML = `
          <div class="day-title">
            <span>${esc(lbl.title)}</span>
            ${lbl.sub ? `<span class="day-sub">${esc(lbl.sub)}</span>` : ""}
          </div>
          <span class="day-count">${items.length} link${items.length === 1 ? "" : "s"}</span>
        `;
        section.appendChild(header);

        const list = document.createElement("div");
        list.className = "day-list";

        for (const item of items) {
          const isLatest = item.url === latestUrl && item.posted_at === latestPosted;
          const row = document.createElement("div");
          row.className = "link-item" + (isLatest ? " is-latest" : "");
          row.innerHTML = `
            <div class="link-main">
              <div class="link-url-row">
                <a class="link-url" href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.url)}</a>
                ${isLatest ? `<span class="mini-badge">Latest</span>` : ""}
              </div>
              <div class="link-time">
                <span>🕒 Posted ${esc(fmtDateTime(item.posted_at))}</span>
                <span>(${esc(relTime(item.posted_at))})</span>
              </div>
            </div>
            <div class="link-actions">
              <button class="icon-btn copy-one" type="button">Copy</button>
              <a class="icon-btn" href="${esc(item.url)}" target="_blank" rel="noopener">Open ↗</a>
            </div>
          `;
          row.querySelector(".copy-one").addEventListener("click", function () {
            copyText(item.url, this);
          });
          list.appendChild(row);
        }

        section.appendChild(list);
        frag.appendChild(section);
      }

      container.innerHTML = "";
      container.appendChild(frag);
    }

    async function fetchLinks(spin = false) {
      const btn = $("refresh-btn");
      if (spin) btn.classList.add("spinning");
      try {
        const res = await fetch("/api/url", { cache: "no-store" });
        const data = await res.json();
        allLinks = Array.isArray(data.links) ? data.links : [];
        renderLatest(data.latest || null);
        renderHistory();
      } catch {
        $("status-text").textContent = "Offline";
      } finally {
        if (spin) setTimeout(() => btn.classList.remove("spinning"), 300);
      }
    }

    $("search").addEventListener("input", renderHistory);
    $("clear-search").addEventListener("click", () => {
      $("search").value = "";
      renderHistory();
      $("search").focus();
    });
    $("refresh-btn").addEventListener("click", () => fetchLinks(true));

    fetchLinks(false);
    setInterval(() => fetchLinks(false), 15000);
  </script>
</body>
</html>
"""


@app.route("/healthz")
def healthz():
    return Response("ok", status=200, mimetype="text/plain")


@app.route("/")
def index():
    if request.args.get("go") == "1":
        with LOCK:
            links = _load_links()
        if links:
            return redirect(links[0]["url"], code=302)
    return Response(
        INDEX_HTML,
        status=200,
        mimetype="text/html",
        headers={"Cache-Control": "no-store"},
    )


@app.route("/api/url", methods=["GET", "POST"])
def api_url():
    if request.method == "GET":
        with LOCK:
            links = _load_links()
        return jsonify({
            "ok": True,
            "latest": links[0] if links else None,
            "links": links,
            "count": len(links),
        }), 200, {"Cache-Control": "no-store"}

    data = request.get_json(silent=True) or {}
    raw_url = (data.get("url") or "").strip()
    if not URL_RE.match(raw_url):
        return jsonify({"error": "Invalid url"}), 400

    now = _now_iso()
    with LOCK:
        links = _load_links()
        if links and links[0].get("url") == raw_url:
            links[0]["last_seen"] = now
            _save_links(links)
            return jsonify({"ok": True, "deduped": True, "latest": links[0]})

        entry = {
            "url": raw_url,
            "posted_at": now,
            "last_seen": now,
        }
        links.insert(0, entry)
        links = links[:MAX_LINKS]
        _save_links(links)
        return jsonify({"ok": True, "deduped": False, "latest": entry})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)