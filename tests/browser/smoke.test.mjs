import assert from "node:assert/strict";
import test from "node:test";
import { chromium } from "playwright";

const baseURL = process.env.OES_BASE_URL || "http://127.0.0.1:8000";

function makeCSV() {
  const rows = ["x1,x2,y"];
  for (let i = 1; i <= 40; i += 1) {
    const x1 = i;
    const x2 = (i % 7) - 3;
    const disturbance = ((i % 5) - 2) * 0.3;
    const y = 4 + 1.7 * x1 - 0.8 * x2 + disturbance;
    rows.push(`${x1},${x2},${y.toFixed(4)}`);
  }
  return rows.join("\n");
}

test(
  "Chromium initializes Pyodide, profiles CSV, estimates OLS-HC3 and exports reports",
  { timeout: 240_000 },
  async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const pageErrors = [];
    page.on("pageerror", error => pageErrors.push(error.message));

    try {
      await page.goto(baseURL, { waitUntil: "domcontentloaded" });
      await page.waitForFunction(
        () => document.querySelector("#runtime-label")?.textContent === "Browser Python runtime ready",
        null,
        { timeout: 180_000 }
      ).catch(async error => {
        const detail = await page.locator("#runtime-detail").textContent().catch(() => "No runtime detail");
        throw new Error(`Pyodide did not become ready: ${detail}. ${error.message}`);
      });

      assert.match(await page.locator("#runtime-detail").textContent(), /Pyodide ready/);

      await page.locator("#file-input").setInputFiles({
        name: "oes-browser-smoke.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(makeCSV(), "utf8")
      });

      await page.waitForFunction(
        () => document.querySelector("#global-status")?.textContent.includes("Loaded 40 rows and 3 columns"),
        null,
        { timeout: 30_000 }
      );

      await page.locator("#outcome-select").selectOption("y");
      await page.locator("#profile-button").click();
      await page.waitForFunction(
        () => document.querySelector("#profile-status")?.textContent === "Profile complete",
        null,
        { timeout: 30_000 }
      );

      assert.match(await page.locator("#profile-results").textContent(), /OBSERVATIONS/);
      assert.match(await page.locator("#recommendations").textContent(), /OLS with HC3 robust covariance/);

      await page.locator("#model-select").selectOption("ols_hc3");
      await page.locator("#predictors-select").selectOption(["x1", "x2"]);
      await page.locator("#estimate-button").click();
      await page.waitForFunction(
        () => document.querySelector("#result-status")?.textContent === "Estimation complete",
        null,
        { timeout: 45_000 }
      );

      const resultText = await page.locator("#results").textContent();
      assert.match(resultText, /OLS with HC3 robust covariance/);
      assert.match(resultText, /x1/);
      assert.match(resultText, /x2/);
      assert.match(resultText, /40/);

      const [jsonDownload] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#download-json").click()
      ]);
      assert.equal(jsonDownload.suggestedFilename(), "oes-intelligence-analysis.json");

      const [htmlDownload] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#download-html").click()
      ]);
      assert.equal(htmlDownload.suggestedFilename(), "oes-intelligence-report.html");

      assert.deepEqual(pageErrors, [], "Browser page should not emit uncaught JavaScript errors");
    } finally {
      await browser.close();
    }
  }
);
