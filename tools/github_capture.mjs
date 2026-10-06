// GitHub-репозиторий → данные + скриншот страницы для сцены "github".
//
//   node tools/github_capture.mjs owner/name videos/<slug> [--light]
//
// Пишет: <проект>/captures/github/<owner>__<name>.json  { repo, stars, desc, lang, topics,
//          install_cmds[], title_bbox, stars_bbox, vw, vh }
//        <проект>/captures/github/<owner>__<name>.png   (1280×1600 @2x, тёмная тема)
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import puppeteer from "puppeteer-core";
import { findChrome } from "./chrome.mjs";

const [repo, proj, ...flags] = process.argv.slice(2);
if (!repo || !proj || !repo.includes("/")) {
  console.error("usage: node github_capture.mjs owner/name <project_dir> [--light]");
  process.exit(1);
}
const [owner, name] = repo.split("/");
const out = path.join(proj, "captures", "github");
fs.mkdirSync(out, { recursive: true });
const base = path.join(out, `${owner}__${name}`);
const CHROME = findChrome();
const VW = 1280, VH = 1600;

let token = "";
try { token = execSync("gh auth token", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch {}
const H = { "User-Agent": "hf-tools", Accept: "application/vnd.github+json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };

async function api(p) {
  const r = await fetch(`https://api.github.com${p}`, { headers: H });
  if (!r.ok) throw new Error(`${p}: HTTP ${r.status}`);
  return r.json();
}

// команды установки из README: первые блоки кода с install/npx/pip/brew/clone/claude mcp add/skills
function installCmds(md) {
  const blocks = [...md.matchAll(/```[a-zA-Z]*\n([\s\S]*?)```/g)].map((m) => m[1].trim());
  const re = /(npx |npm i|npm install|pip install|pipx |uv |brew install|git clone|claude mcp add|\/plugin|curl .*\| *(ba)?sh|cargo install|go install|skills add)/;
  const cmds = [];
  for (const b of blocks) for (const line of b.split("\n")) {
    const l = line.replace(/^\$\s*/, "").trim();
    if (re.test(l) && l.length < 140 && !cmds.includes(l)) cmds.push(l);
  }
  return cmds.slice(0, 6);
}

const meta = { repo: `${owner}/${name}`, vw: VW, vh: VH };
try {
  const r = await api(`/repos/${owner}/${name}`);
  Object.assign(meta, { stars: r.stargazers_count, desc: r.description || "", lang: r.language || "",
    topics: r.topics || [], license: r.license?.spdx_id || "", homepage: r.homepage || "", forks: r.forks_count });
  try {
    const rd = await api(`/repos/${owner}/${name}/readme`);
    meta.install_cmds = installCmds(Buffer.from(rd.content, "base64").toString("utf8"));
  } catch { meta.install_cmds = []; }
} catch (e) { console.error("API:", e.message); }

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true,
  args: ["--hide-scrollbars", "--lang=en-US"] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: VW, height: VH, deviceScaleFactor: 2 });
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: flags.includes("--light") ? "light" : "dark" }]);
  await page.goto(`https://github.com/${owner}/${name}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("strong[itemprop=name], #repo-title-component", { timeout: 20000 }).catch(() => {});
  await page.waitForNetworkIdle({ idleTime: 800, timeout: 8000 }).catch(() => {});
  // убрать баннеры cookies/входа
  await page.evaluate(() => {
    for (const sel of ["#cookie-consent-banner", ".js-cookie-consent-banner", "cookie-consent-banner",
      ".signup-prompt", ".flash-full", "[data-testid=cookie-banner]"]) document.querySelectorAll(sel).forEach((n) => n.remove());
  });
  await new Promise((r) => setTimeout(r, 600));
  const bb = await page.evaluate(() => {
    const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return r.width ? [r.x, r.y, r.width, r.height] : null; };
    const q = (...ss) => { for (const s of ss) { const e = document.querySelector(s); if (e && e.getBoundingClientRect().width) return e; } return null; };
    const nameEl = q("strong[itemprop=name] a", "strong[itemprop=name]", "#repo-title-component a", "[data-testid=repo-title] a");
    const ownerEl = q("span.author a", "a[rel=author]", "#repo-title-component [data-hovercard-type]");
    let title = box(nameEl);
    const ob = box(ownerEl);
    if (title && ob && Math.abs(ob[1] - title[1]) < 20) {           // owner / name одной рамкой
      const x = Math.min(ob[0], title[0]), r = Math.max(ob[0] + ob[2], title[0] + title[2]);
      title = [x, Math.min(ob[1], title[1]), r - x, Math.max(ob[3], title[3])];
    }
    const stars = box(q("#repo-stars-counter-star", "a[href$='/stargazers']"));
    return { title, stars };
  });
  meta.title_bbox = bb.title;
  meta.stars_bbox = bb.stars;
  await page.screenshot({ path: base + ".png", clip: { x: 0, y: 0, width: VW, height: VH } });
} finally {
  await browser.close();
}
fs.writeFileSync(base + ".json", JSON.stringify(meta, null, 2));
console.log(JSON.stringify({ ...meta, png: base + ".png" }, null, 2));
