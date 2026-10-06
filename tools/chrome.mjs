// Путь к Chrome/Chromium для puppeteer-core: $CHROME_PATH → системный Chrome → Chromium из кэша puppeteer.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function findChrome() {
  const cands = [
    process.env.CHROME_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ];
  for (const c of cands) if (c && fs.existsSync(c)) return c;
  const cache = path.join(os.homedir(), ".cache", "puppeteer");
  try {
    for (const kind of ["chrome", "chrome-headless-shell"]) {
      const dir = path.join(cache, kind);
      for (const v of fs.readdirSync(dir).sort().reverse()) {
        for (const rel of ["chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
          "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
          "chrome-linux64/chrome", "chrome-headless-shell-mac-arm64/chrome-headless-shell",
          "chrome-headless-shell-linux64/chrome-headless-shell"]) {
          const p = path.join(dir, v, rel);
          if (fs.existsSync(p)) return p;
        }
      }
    }
  } catch {}
  console.error("Не найден Chrome. Установи Google Chrome или задай CHROME_PATH=/путь/к/chrome");
  process.exit(1);
}
