// HTML-макет → PNG (для хука/вставок, когда нужного экрана нет в библиотеке сцен:
// окно запроса разрешения, карточка пакета, уведомление, интерфейс сервиса).
//
//   node tools/html_snap.mjs <file.html> <out.png> [W] [H] [--scale 1]
//
// W×H по умолчанию 1080×1010 (зона графики в split); 1080×1920 — полный экран.
// Шрифты движка: url('<относит.путь>/assets/fonts/…') или системные.
import path from "node:path";
import puppeteer from "puppeteer-core";
import { findChrome, fileUrl } from "./chrome.mjs";

const a = process.argv.slice(2);
const [inp, out] = a;
const W = +(a[2] || 1080), H = +(a[3] || 1010);
const si = a.indexOf("--scale");
const scale = si >= 0 ? +a[si + 1] : 1;
if (!inp || !out) { console.error("usage: node html_snap.mjs <file.html> <out.png> [W] [H] [--scale 1]"); process.exit(1); }
const b = await puppeteer.launch({ executablePath: findChrome(),
  headless: true, args: ["--allow-file-access-from-files"] });
try {
  const p = await b.newPage();
  await p.setViewport({ width: W, height: H, deviceScaleFactor: scale });
  await p.goto(fileUrl(inp), { waitUntil: "load" });
  await p.evaluate(() => document.fonts && document.fonts.ready);
  await new Promise((r) => setTimeout(r, 300));
  await p.screenshot({ path: out });
  console.log("→", out, `${W}x${H}`);
} finally {
  await b.close();
}
