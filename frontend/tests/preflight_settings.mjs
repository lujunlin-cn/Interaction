/** Developer Settings uses effective server preflight, never hidden test knobs. */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { chromium } from "playwright";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const evidence = path.resolve(root, "../docs/acceptance/preflight_safety");
await mkdir(evidence, { recursive: true });
const origin = "http://127.0.0.1:9002";
const server = await createServer({ root, configFile: false, server: { host: "127.0.0.1", port: 9002, strictPort: true, hmr: false } });
await server.listen();
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await context.newPage();
const requests = [], unexpected = [];
let status = "PASS", error;
await page.addInitScript(() => localStorage.setItem("drama.mode", "developer"));
await context.route("**/*", async route => {
  const request = route.request(), url = new URL(request.url());
  if (url.origin !== origin) { unexpected.push(request.url()); return route.abort(); }
  if (!url.pathname.startsWith("/api/")) return route.continue();
  const responses = {
    "/api/health": { ok: true, provider_mode: "live", profile: "AGENT_LOCAL_PROFILE" },
    "/api/dev/providers": { profile: "AGENT_LOCAL_PROFILE", health: {} },
    "/api/dev/profile": { state: "ACTIVE" },
    "/api/dev/generation-settings": { fal_paid_generation_enabled: true, image_resolution: "4K", video_resolution: "480P", aspect_ratio: "16:9", test_override_enabled: false, test_top_k: 1, test_max_shots: 1, test_shot_duration: 5, max_test_reference_images: 2, max_test_reference_videos: 0 },
    "/api/dev/usage-ledger": { items: [] },
    "/api/scenarios": { items: [] },
  };
  let response = responses[url.pathname];
  if (url.pathname === "/api/dev/generation-preflight") {
    requests.push(request.postDataJSON());
    response = { estimate: true, actual_plan: false, estimate_basis: "EFFECTIVE_CONFIGURATION", jobs: 3, total_requested_duration: 15, reference_images: null, reference_status: "UNKNOWN_NOT_RESOLVED", circuit: "OPEN", fal_request_allowed: false, blocked_reasons: ["BILLING_LOCKED"] };
  }
  if (!response) { unexpected.push(`${request.method()} ${url.pathname}`); response = {}; }
  await route.fulfill({ contentType: "application/json", body: JSON.stringify(response) });
});
try {
  await page.goto(`${origin}/#/settings`);
  await page.getByRole("button", { name: "查看付费 Preflight", exact: true }).click();
  await page.getByText("当前配置预估，尚未锁定生成计划；参考素材数量在完成角色与镜头解析前未知。", { exact: true }).waitFor();
  assert.deepEqual(requests, [{ role: "h3_max" }]);
  assert.deepEqual(unexpected, []);
  const result = await page.locator("pre").first().innerText();
  assert.match(result, /"jobs": 3/);
  assert.match(result, /"reference_images": null/);
  assert.match(result, /"fal_request_allowed": false/);
  await page.screenshot({ path: path.join(evidence, "settings_preflight.png"), fullPage: true });
} catch (e) { status = "FAIL"; error = String(e); process.exitCode = 1; }
finally {
  await browser.close(); await server.close();
  const report = { date: new Date().toISOString(), mode: "isolated browser API mocks", viewport: "1920x1080", status, error, requests, unexpected, external_paid_media_requests: 0 };
  await writeFile(path.join(evidence, "browser.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
