import { test } from "@playwright/test";
import path from "node:path";
import { ANSWERED_INVESTIGATION, ANSWERED_SSE, INSUFFICIENT_INVESTIGATION, INSUFFICIENT_SSE } from "./fixtures";

// Captures the screenshots the docs walkthrough embeds. Reuses the exact same
// network mocks as incident.spec.ts, so a screenshot can never silently drift
// from what the smoke test proves the UI does (`make docs-screenshots`).
const SCREENSHOTS_DIR = path.join(__dirname, "..", "..", "docs", "assets");

async function mockCreate(page: import("@playwright/test").Page) {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    const body = route.request().postDataJSON() as { question: string };
    const id = body.question.toLowerCase().includes("attacked")
      ? "run-insufficient"
      : "run-success";
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id, status: "running" }),
    });
  });
}

async function mockInvestigation(
  page: import("@playwright/test").Page,
  id: string,
  sse: string,
  investigation: unknown
) {
  await page.route(`**/investigations/${id}/events`, async (route) => {
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: sse });
  });
  await page.route(`**/investigations/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(investigation),
    });
  });
}

test("capture: a full evidence-grounded incident report", async ({ page }) => {
  await mockCreate(page);
  await mockInvestigation(page, "run-success", ANSWERED_SSE, ANSWERED_INVESTIGATION);

  await page.goto("/");
  await page.getByLabel("Incident report").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, "screenshot-report.png"),
    fullPage: true,
  });
});

test("capture: the honesty guardrail flags an unsupported attack claim", async ({ page }) => {
  await mockCreate(page);
  await mockInvestigation(page, "run-success", ANSWERED_SSE, ANSWERED_INVESTIGATION);
  await mockInvestigation(page, "run-insufficient", INSUFFICIENT_SSE, INSUFFICIENT_INVESTIGATION);

  await page.goto("/");
  await page.getByLabel("Incident report").waitFor();
  await page.getByRole("button", { name: "Traffic spike (is it an attack?)" }).click();
  await page.getByText("Insufficient evidence").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, "screenshot-insufficient-evidence.png"),
    fullPage: true,
  });
});
