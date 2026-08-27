import { test, expect, type Page } from "@playwright/test";
import {
  ANSWERED_INVESTIGATION,
  ANSWERED_SSE,
  EMPTY_SSE,
  INSUFFICIENT_INVESTIGATION,
  INSUFFICIENT_SSE,
} from "./fixtures";

// Every state a run can render, plus the honesty-guardrail exit behaviour: a
// visitor can trigger the adversarial scenario and see the report flagged as
// insufficient evidence rather than a confident (and wrong) "attack" claim.
// The backend is fully mocked at the network layer.

async function mockInvestigation(
  page: Page,
  opts: { id: string; sse: string; investigation: unknown }
) {
  await page.route(`**/investigations/${opts.id}/events`, async (route) => {
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: opts.sse });
  });
  await page.route(`**/investigations/${opts.id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(opts.investigation),
    });
  });
}

/** Routes POST /investigations to a run id chosen from the question, so the
 * two scenario buttons resolve to the two mocked runs. */
async function mockCreate(page: Page) {
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

test("loading: shows a starting message before the run begins", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id: "run-loading", status: "running" }),
    });
  });

  await page.goto("/");
  await expect(page.getByText("Starting the investigation")).toBeVisible();
});

test("success: renders the trace and the incident report", async ({ page }) => {
  await mockCreate(page);
  await mockInvestigation(page, {
    id: "run-success",
    sse: ANSWERED_SSE,
    investigation: ANSWERED_INVESTIGATION,
  });

  await page.goto("/");
  await expect(page.getByLabel("Trace")).toBeVisible();
  await expect(page.getByLabel("Incident report")).toBeVisible();
  await expect(page.getByText("payment-service timeout cascade")).toBeVisible();
});

test("insufficient evidence: the adversarial scenario is flagged, not confidently answered", async ({
  page,
}) => {
  await mockCreate(page);
  await mockInvestigation(page, {
    id: "run-success",
    sse: ANSWERED_SSE,
    investigation: ANSWERED_INVESTIGATION,
  });
  await mockInvestigation(page, {
    id: "run-insufficient",
    sse: INSUFFICIENT_SSE,
    investigation: INSUFFICIENT_INVESTIGATION,
  });

  await page.goto("/");
  await expect(page.getByLabel("Incident report")).toBeVisible();

  await page.getByRole("button", { name: "Traffic spike (is it an attack?)" }).click();

  await expect(page.getByText("Insufficient evidence")).toBeVisible();
});

test("empty: renders a defensive message when a completed run has no report", async ({
  page,
}) => {
  await mockCreate(page);
  await mockInvestigation(page, {
    id: "run-success",
    sse: EMPTY_SSE,
    investigation: { ...ANSWERED_INVESTIGATION, report: null },
  });

  await page.goto("/");
  await expect(page.getByText("produced no report")).toBeVisible();
});

test("error: renders an alert when the investigation cannot be started", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
  });

  await page.goto("/");
  await expect(page.getByText("Could not start the investigation")).toBeVisible();
});
