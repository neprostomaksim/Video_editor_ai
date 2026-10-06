// Скриншот любой страницы для сцен image/hook (сайт продукта, новость, документация).
//
//   node tools/web_capture.mjs <url> <out.png> [--mobile] [--dark] [--h 1600] [--wait 1500] [--scroll 0]
//
// --mobile  вьюпорт 430×932 @3x (как телефон) вместо 1280×1600 @2x
// --dark    prefers-color-scheme: dark
// --h       высота кадра (px CSS), --scroll — прокрутить страницу на N px перед снимком
import puppeteer from "puppeteer-core";
import { findChrome } from "./chrome.mjs";

const args = process.argv.slice(2);
const [url, out] = args.filter((a) => !a.startsWith("--") && !/^\d+$/.test(a));
const flag = (n) => args.includes(n);
const num = (n, d) => { const i = args.indexOf(n); return i >= 0 ? Number(args[i + 1]) : d; };
if (!url || !out) { console.error("usage: node web_capture.mjs <url> <out.png> [--mobile] [--dark] [--h N] [--wait ms] [--scroll px]"); process.exit(1); }
const mobile = flag("--mobile");
const VW = mobile ? 430 : 1280, VH = num("--h", mobile ? 932 : 1600);
const browser = await puppeteer.launch({ executablePath: findChrome(),
  headless: true, args: ["--hide-scrollbars", "--lang=en-US"] });
try {
  const page = await browser.newPage();
  if (mobile) await page.setUserAgent("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1");
  await page.setViewport({ width: VW, height: VH, deviceScaleFactor: mobile ? 3 : 2, isMobile: mobile, hasTouch: mobile });
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: flag("--dark") ? "dark" : "light" }]);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForNetworkIdle({ idleTime: 800, timeout: 12000 }).catch(() => {});
  // убрать баннеры cookies/чаты поддержки
  await page.evaluate(() => {
    const kill = ["#onetrust-banner-sdk", "#CybotCookiebotDialog", "[id*=cookie i]", "[class*=cookie i]",
      "[aria-label*=cookie i]", "#intercom-container", ".intercom-lightweight-app", "#hubspot-messages-iframe-container"];
    for (const s of kill) document.querySelectorAll(s).forEach((n) => { if (n.getBoundingClientRect().height < 500) n.remove(); });
  });
  const sc = num("--scroll", 0);
  if (sc) await page.evaluate((y) => window.scrollTo(0, y), sc);
  await new Promise((r) => setTimeout(r, num("--wait", 1200)));
  await page.screenshot({ path: out, clip: { x: 0, y: sc, width: VW, height: VH } });   // clip — в координатах документа
  console.log("→", out, `${VW}x${VH}`, await page.title());
} finally {
  await browser.close();
}
