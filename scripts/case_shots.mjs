// Скриншоты мини-аппа для кейса: живой каталог, телефонный экран 390×844 @3x.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.argv[2] || "http://localhost:4173/";
const OUT = process.argv[3] || "shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, locale: "ru-RU" });
const page = await ctx.newPage();
const log = (...a) => console.log(...a);
page.on("pageerror", (e) => log("pageerror:", String(e)));
const top = ".screen:not(.is-under)";
const shot = async (name, wait = 900) => {
  await page.waitForTimeout(wait);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  log("ok", name);
};
const scroll = (y) => page.locator(`${top} .screen-scroll`).first().evaluate((el, y) => el.scrollTo({ top: y }), y);
const open = async () => {
  await page.goto(BASE);
  await page.waitForSelector(".tabbar", { timeout: 30000 });
  await page.waitForTimeout(4500);
};
const step = async (name, fn) => {
  try {
    await fn();
  } catch (e) {
    log("FAIL", name, String(e).split("\n")[0]);
  }
};

await step("preloader", async () => {
  await page.goto(BASE);
  await shot("01-preloader", 700);
});
await step("home", async () => {
  await page.waitForSelector(".tabbar", { timeout: 30000 });
  await shot("02-home", 4500);
  await scroll(560);
  await shot("03-home-devices", 1200);
});
await step("device", async () => {
  await page.locator('[aria-label^="Смартфоны,"]').first().click();
  await page.waitForTimeout(1200);
  await page.locator(`${top} .chip`, { hasText: "iOS" }).first().click();
  await shot("04-smartphones", 1600);
});
await step("product", async () => {
  await open();
  await page.locator(".tab").nth(1).click();
  await page.fill(".search-pill input", "iPhone 17 Pro");
  await page.waitForTimeout(900);
  await shot("05-search", 600);
  await page.locator(".row").first().click();
  await shot("06-product", 1800);
  const specs = page.locator(`${top} .specs`).first();
  await specs.evaluate((el) => el.scrollIntoView({ block: "start" }));
  await shot("07-product-specs", 900);
  await page.locator(`${top} button`, { hasText: "Сравнить" }).first().click();
  await page.locator(`${top} [aria-label="В избранное"]`).first().click().catch(() => {});
  await page.locator(`${top} .buybar .btn-primary`).first().click().catch(() => {});
  await page.waitForTimeout(600);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(900);
  await page.locator(".row").nth(1).click();
  await page.waitForTimeout(1500);
  await page.locator(`${top} button`, { hasText: "Сравнить" }).first().click();
  await page.locator(`${top} .buybar .btn-primary`).first().click().catch(() => {});
  await page.waitForTimeout(500);
  await page.locator(`${top} button`, { hasText: "Открыть сравнение" }).first().click();
  await shot("08-compare", 1500);
});
await step("cart", async () => {
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
  await page.locator(".tab").nth(3).click();
  await shot("09-cart", 1300);
});
await step("tradein", async () => {
  await open();
  await page.locator(".promo-dark").first().click();
  await page.waitForTimeout(1200);
  await page.locator(`${top} .ti-models button, ${top} .ti-models [role=radio]`).first().click().catch(() => {});
  await page.waitForTimeout(500);
  await page.locator(`${top} .ti-conds button, ${top} .ti-conds [role=radio]`).first().click().catch(() => {});
  await shot("10-tradein", 1200);
});
await step("service", async () => {
  await open();
  await page.locator(".promo:not(.promo-dark)").first().click();
  await shot("11-service", 1400);
});
await browser.close();
