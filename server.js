const http = require("node:http");
const crypto = require("node:crypto");

const PORT = Number(process.env.PORT || 3000);
const API_KEY = process.env.API_KEY || "";

let currentUrl = "";
let updatedAt = null;

function safeEqual(a, b) {
  const aa = Buffer.from(String(a || ""));
  const bb = Buffer.from(String(b || ""));
  return aa.length === bb.length && crypto.timingSafeEqual(aa, bb);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "GET" && url.pathname === "/healthz") {
    res.writeHead(200, { "content-type": "text/plain" });
    return res.end("ok");
  }

  if (req.method === "GET" && url.pathname === "/api/url") {
    res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" });
    return res.end(JSON.stringify({ url: currentUrl || null, updatedAt }));
  }

  if (req.method === "POST" && url.pathname === "/api/url") {
    let body = "";
    req.on("data", (c) => {
      body += c;
      if (body.length > 8192) req.destroy();
    });
    req.on("end", () => {
      let data = {};
      try { data = JSON.parse(body || "{}"); } catch {}
      const key = req.headers["x-api-key"] || data.key || "";
      if (!API_KEY || !safeEqual(key, API_KEY)) {
        res.writeHead(401, { "content-type": "application/json" });
        return res.end(JSON.stringify({ error: "Unauthorized" }));
      }
      if (typeof data.url !== "string" || !/^https:\/\/[a-zA-Z0-9.-]+/.test(data.url)) {
        res.writeHead(400, { "content-type": "application/json" });
        return res.end(JSON.stringify({ error: "Invalid url" }));
      }
      currentUrl = data.url.trim();
      updatedAt = new Date().toISOString();
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true, url: currentUrl, updatedAt }));
    });
    return;
  }

  if (req.method === "GET" && url.pathname === "/") {
    if (url.searchParams.get("go") === "1" && currentUrl) {
      res.writeHead(302, { Location: currentUrl, "cache-control": "no-store" });
      return res.end();
    }
    const safeUrl = escapeHtml(currentUrl);
    const safeTime = escapeHtml(updatedAt || "Waiting for Termux...");
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
    return res.end(`<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Link API</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#140b10;color:#f3e8ee;font-family:system-ui,sans-serif;padding:20px}
.card{max-width:440px;width:100%;background:#22111a;border:1px solid #4a2438;border-radius:16px;padding:24px;text-align:center}
h2{margin:0 0 12px;font-size:20px}
a{display:block;word-break:break-all;color:#e2588d;margin:14px 0;font-size:15px}
.meta{font-size:12px;color:#b89aa8}
.btn{display:inline-block;margin-top:14px;padding:10px 18px;background:#e2588d;color:#fff;border-radius:10px;text-decoration:none;font-weight:600}
</style></head><body><div class="card">
<h2>Current Link</h2>
${currentUrl ? `<a href="${safeUrl}">${safeUrl}</a><a class="btn" href="${safeUrl}">Open Site</a>` : `<p>No link posted yet.</p>`}
<div class="meta">Updated: ${safeTime}</div>
</div></body></html>`);
  }

  res.writeHead(404);
  res.end("Not found");
});

server.listen(PORT, () => console.log(`Link API listening on :${PORT}`));