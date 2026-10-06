// Анимированный HTML-макет → MP4 (для хука и вставок: курсор едет, кнопка жмётся, текст печатается,
// элементы появляются). Анимации пишутся обычным CSS (@keyframes / animation-delay); запись детерминированная:
// все анимации ставятся на паузу и для каждого кадра выставляется currentTime — без дёрганий и пропусков.
//
//   node tools/html_record.mjs <file.html> <out.mp4> [W] [H] [--dur 4] [--fps 25]
//
// W×H по умолчанию 1080×1010 (зона графики в split); 1080×1920 — полный экран.
// Правило монтажа: первые секунды ролика — ВСЕГДА движение (видео или такой макет), не статичная картинка.
import path from "node:path";
import { spawn } from "node:child_process";
import puppeteer from "puppeteer-core";
import { findChrome } from "./chrome.mjs";

const a = process.argv.slice(2);
const [inp, out] = a;
const W = +(a[2] && !a[2].startsWith("--") ? a[2] : 1080);
const H = +(a[3] && !a[3].startsWith("--") ? a[3] : 1010);
const opt = (n, d) => { const i = a.indexOf(n); return i >= 0 ? +a[i + 1] : d; };
const DUR = opt("--dur", 4), FPS = opt("--fps", 25);
if (!inp || !out) { console.error("usage: node html_record.mjs <file.html> <out.mp4> [W] [H] [--dur 4] [--fps 25]"); process.exit(1); }

const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
  "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "25", "-keyint_min", "25",
  "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });

const b = await puppeteer.launch({ executablePath: findChrome(),
  headless: true, args: ["--allow-file-access-from-files"] });
try {
  const p = await b.newPage();
  await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await p.goto("file://" + path.resolve(inp), { waitUntil: "load" });
  await p.evaluate(() => document.fonts && document.fonts.ready);
  await new Promise((r) => setTimeout(r, 250));
  const n = Math.round(DUR * FPS);
  for (let f = 0; f < n; f++) {
    const ms = (f / FPS) * 1000;
    await p.evaluate((t) => { document.getAnimations().forEach((an) => { an.pause(); an.currentTime = t; }); }, ms);
    const buf = await p.screenshot({ type: "png" });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  }
} finally {
  await b.close();
  ff.stdin.end();
}
await new Promise((r) => ff.on("close", r));
console.log("→", out, `${W}x${H}`, `${DUR}s @${FPS}fps`);
