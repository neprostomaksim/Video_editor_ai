// Кроссплатформенные мелочи для node-инструментов (macOS / Windows / Linux):
//   findChrome() — Chrome для puppeteer-core: $CHROME_PATH → установленный Chrome/Edge/Chromium → кэш puppeteer →
//                  браузер HyperFrames (python3 hf.py browser ensure — скачает при первом запуске);
//   fileUrl(p)   — правильный file:// URL (на Windows "file://" + "C:\..." не работает).
// При импорте добавляет bin/ проекта в PATH — там ffmpeg, если setup положил его туда.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.env.PATH = path.join(ROOT, "bin") + path.delimiter + (process.env.PATH || "");

export const fileUrl = (p) => pathToFileURL(path.resolve(p)).href;

export function findChrome() {
  for (const k of ["CHROME_PATH", "PUPPETEER_EXECUTABLE_PATH"]) {
    if (process.env[k] && fs.existsSync(process.env[k])) return process.env[k];
  }
  const home = os.homedir();
  let c = [];
  if (process.platform === "darwin") {
    c = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      path.join(home, "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
      "/Applications/Chromium.app/Contents/MacOS/Chromium"];
  } else if (process.platform === "win32") {
    for (const base of [process.env.PROGRAMFILES, process.env["PROGRAMFILES(X86)"], process.env.LOCALAPPDATA]) {
      if (base) c.push(path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
        path.join(base, "Chromium", "Application", "chrome.exe"),
        path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"));
    }
  } else {
    c = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
      "/snap/bin/chromium"];
  }
  for (const p of c) if (p && fs.existsSync(p)) return p;
  // кэш puppeteer (в том числе браузер, который скачивает HyperFrames)
  const rels = ["chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-linux64/chrome", "chrome-win64/chrome.exe",
    "chrome-headless-shell-mac-arm64/chrome-headless-shell", "chrome-headless-shell-mac-x64/chrome-headless-shell",
    "chrome-headless-shell-linux64/chrome-headless-shell", "chrome-headless-shell-win64/chrome-headless-shell.exe"];
  for (const cache of [path.join(home, ".cache", "puppeteer"), path.join(home, ".cache", "hyperframes", "chrome")]) {
    for (const kind of ["chrome", "chrome-headless-shell", ""]) {
      const dir = path.join(cache, kind);
      let vs = [];
      try { vs = fs.readdirSync(dir).sort().reverse(); } catch { continue; }
      for (const v of vs) for (const rel of rels) {
        const p = path.join(dir, v, rel);
        if (fs.existsSync(p)) return p;
      }
    }
  }
  // браузер HyperFrames: скачать (если ещё нет) и спросить путь
  const py = process.platform === "win32" ? "python" : "python3";
  try {
    const hf = path.join(ROOT, "hf.py");
    execFileSync(py, [hf, "browser", "ensure"], { stdio: "ignore" });
    const out = execFileSync(py, [hf, "browser", "path"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    const line = out.trim().split(/\r?\n/).reverse().find((l) => fs.existsSync(l.trim()));
    if (line) return line.trim();
  } catch {}
  console.error("Не найден Chrome. Установи Google Chrome или запусти setup (python3 setup.py), " +
    "или задай путь в переменной CHROME_PATH");
  process.exit(1);
}
