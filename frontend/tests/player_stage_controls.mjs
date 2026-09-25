/** Offline Player layout regression. Mock APIs/WS only; no media providers. */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { chromium } from "playwright";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const evidence = path.resolve(root, "../docs/acceptance/player_stage_controls");
await mkdir(evidence, { recursive: true });
const origin = "http://127.0.0.1:9012";
const server = await createServer({ root, configFile: false, server: {
  host: "127.0.0.1", port: 9012, strictPort: true, hmr: false,
} });
await server.listen();
const browser = await chromium.launch({ headless: true });
const cases = [], unexpected = [], requests = [];
const inside = (child, parent) => child.x >= parent.x - 1 && child.y >= parent.y - 1
  && child.right <= parent.right + 1 && child.bottom <= parent.bottom + 1;

async function run(width, height, failed) {
  const name = `${width}_${failed ? "error" : "ready"}`;
  const context = await browser.newContext({ viewport: { width, height }, serviceWorkers: "block" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  const view = {
    session_id: "offline-layout-session", scenario: { title: "播放器布局回归", player_identity: "调查员" },
    arc: { seq: 1, total: 1 },
    player: { status: failed ? "FAILED_RECOVERABLE" : "WAITING_DECISION", scene_title: "检查入口",
      scene_text: "你与同伴停在入口，商量下一步行动。", caption: "继续观察。", video_url: "",
      duration: 8, lead: 6, decision_open_at: 6, position: 8 },
    // The combined error + Ready case proves overlays cannot displace either dock.
    recommendations: Array.from({ length: 3 }, (_, i) => ({ branch_id: `offline-${i}`,
      label: ["检查门厅", "继续观察", "询问同伴"][i], summary: "一条可用行动", confidence: .9 })),
    known: { inventory: ["手电筒"], relationships: [{ id: "partner", name: "同伴", value: 73 }],
      clues: [{ id: "door", label: "入口有新鲜足迹" }], knowledge: [] },
    wishes: [], messages: [], generating: [], selected: null, timed: null, pending_intent: null,
    action_pending: false, ended: false, pending_continuation: false,
    last_failed_action: failed ? { raw_text: "检查入口", label: "检查入口" } : null,
  };
  await page.addInitScript(() => {
    localStorage.setItem("drama.mode", "standard");
    localStorage.setItem("drama.sessionId", "offline-layout-session");
  });
  await context.routeWebSocket("**/*", ws => ws.onMessage(() => {}));
  await context.route("**/*", async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin !== origin) { unexpected.push(request.url()); return route.abort(); }
    if (!url.pathname.startsWith("/api/")) return route.continue();
    requests.push(`${request.method()} ${url.pathname}`);
    if (request.method() !== "GET") {
      unexpected.push(`${request.method()} ${url.pathname}`);
      return route.fulfill({ status: 403, body: "Offline layout test: mutations prohibited" });
    }
    let data;
    if (url.pathname === "/api/scenarios") data = { items: [] };
    else if (url.pathname === "/api/sessions/offline-layout-session/view") data = view;
    else { unexpected.push(`${request.method()} ${url.pathname}`); data = {}; }
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(data) });
  });
  const measure = () => page.evaluate(() => {
    const rect = selector => { const r = document.querySelector(selector).getBoundingClientRect();
      return { x: r.x, y: r.y, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; };
    return { stage: rect(".player-stage"), controls: rect(".player-controls"),
      decision: rect('[data-layer="decision"]'), agency: rect('[data-layer="agency"]'),
      hud: rect(".hud-toggle"), error: document.querySelector(".media-status") ? rect(".media-status") : null,
      fullscreen: Boolean(document.fullscreenElement), theater: document.querySelector(".appframe").dataset.theaterMode,
      sidebar: Boolean(document.querySelector("#sidebar")),
      headerVisible: document.querySelector(".player-head").getBoundingClientRect().height > 0,
      session: localStorage.getItem("drama.sessionId"), progress: document.querySelector(".player-time").textContent };
  });
  const openMenu = async () => {
    if (!(await page.locator(".player-more").evaluate(el => el.open))) await page.locator(".player-more > summary").click();
  };
  const result = { name, viewport: { width, height }, fixture: failed ? "failed + 3 Ready recommendations" : "3 Ready recommendations" };
  try {
    await page.goto(`${origin}/#/player`);
    await page.locator(".rec-card").first().waitFor();
    const initial = await measure();
    assert.equal(initial.theater, "true", "Player must default to application Theater Mode");
    result.theater = await measure();
    await page.screenshot({ path: path.join(evidence, `${name}.png`) });
    assert.equal(result.theater.fullscreen, false);
    assert.equal(result.theater.sidebar, false);
    assert.equal(result.theater.headerVisible, false);
    assert.ok(inside(result.theater.controls, result.theater.stage),
      `controls must stay inside Stage, not Agency: ${JSON.stringify(result.theater)}`);
    assert.ok(result.theater.stage.height > height * .65);
    assert.ok(result.theater.decision.y >= result.theater.stage.bottom - 1);
    assert.ok(result.theater.agency.y >= result.theater.decision.bottom - 1);
    assert.ok(Math.abs(result.theater.agency.bottom - height) < 2);
    if (failed) assert.ok(inside(result.theater.error, result.theater.stage));
    assert.ok(inside(result.theater.hud, result.theater.stage));
    assert.equal(await page.locator(".rec-card").count(), 3);
    assert.equal(await page.getByRole("button", { name: "Inspector", exact: true }).count(), 0);

    await openMenu();
    result.menu = await page.locator(".player-more > div").evaluate(el => {
      const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, right: r.right, bottom: r.bottom };
    });
    assert.ok(inside(result.menu, result.theater.stage), "More menu must open inside Stage");
    for (const button of await page.locator(".player-more > div button").all()) {
      await button.click({ trial: true }); // Verify hit target, never trigger a player command.
    }
    await page.locator(".player-more > summary").click();

    const input = page.getByRole("textbox", { name: "描述你想做的事", exact: true });
    await input.click();
    await input.pressSequentially("和同伴检查入口，暂不选择推荐。");
    assert.equal(await input.inputValue(), "和同伴检查入口，暂不选择推荐。");
    await page.getByRole("button", { name: "行动", exact: true }).click({ trial: true });
    const hud = page.getByRole("button", { name: "故事随身册", exact: true });
    await hud.hover(); await page.locator(".hud-drawer").waitFor();
    await page.mouse.move(width / 2, 100);
    assert.equal(await page.locator(".hud-drawer").count(), 0);
    await hud.click(); await page.mouse.move(width / 2, 100);
    assert.equal(await hud.getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator(".hud-drawer").count(), 1);

    await openMenu();
    await page.getByRole("button", { name: "退出剧场模式", exact: true }).click();
    await page.waitForFunction(() => document.querySelector(".appframe").dataset.theaterMode === "false");
    await page.waitForTimeout(1100); // View polling must not undo a manual layout choice.
    result.normal = await measure();
    assert.ok(inside(result.normal.controls, result.normal.stage), "Normal-mode controls must also overlay Stage");
    assert.equal(result.normal.sidebar, true);
    assert.equal(result.normal.headerVisible, true);
    assert.equal(result.normal.fullscreen, false);
    assert.equal(result.normal.session, initial.session);
    assert.equal(result.normal.progress, initial.progress);
    assert.equal(await input.inputValue(), "和同伴检查入口，暂不选择推荐。");
    assert.equal(await hud.getAttribute("aria-pressed"), "true");
    await openMenu();
    await page.getByRole("button", { name: "进入剧场模式", exact: true }).click();
    await hud.click(); await page.mouse.move(width / 2, 100);
    assert.equal(await hud.getAttribute("aria-pressed"), "false");
    assert.equal(await page.locator(".hud-drawer").count(), 0);
    assert.equal(await input.inputValue(), "和同伴检查入口，暂不选择推荐。");
    assert.equal(await page.locator(".rec-card").count(), 3);
    await page.screenshot({ path: path.join(evidence, `${name}.png`) });

    // A real page departure clears Theater; returning to the retained session
    // mounts Player in its default layout again, without browser fullscreen.
    await openMenu();
    await page.getByRole("button", { name: "退出剧场模式", exact: true }).click();
    await page.locator("#sidebar .sidebar-item").filter({ has: page.locator(".nav-label", { hasText: /^故事库$/ }) }).click();
    assert.equal(await page.locator(".appframe").getAttribute("data-theater-mode"), "false");
    await page.locator("#sidebar .sidebar-item").filter({ has: page.locator(".nav-label", { hasText: /^当前游玩$/ }) }).click();
    await page.locator(".rec-card").first().waitFor();
    result.reentered = await measure();
    assert.equal(result.reentered.theater, "true");
    assert.equal(result.reentered.fullscreen, false);
    assert.equal(result.reentered.session, initial.session);
    assert.deepEqual(errors, []);
    result.status = "PASS";
    result.checks = ["default application Theater", "Stage controls", "visible menu hit targets", "Agency typing", "Ready decisions",
      "HUD hover/pin/unpin", "normal/theater toggle preserves session, input, progress, HUD",
      "manual normal mode survives polling", "leave/reentry restores default Theater without browser fullscreen"];
  } catch (error) { result.status = "FAIL"; result.error = String(error); }
  finally { cases.push(result); await context.close(); }
}

try {
  for (const [width, height] of [[1920, 1080], [2560, 1440]]) {
    for (const failed of [true, false]) await run(width, height, failed);
  }
} finally {
  await browser.close(); await server.close();
  const report = { captured_at: new Date().toISOString(), evidence_scope: "Offline browser fixtures, not Real Provider E2E",
    external_paid_media_requests: 0, mutation_requests: requests.filter(r => !r.startsWith("GET ")),
    unexpected, cases };
  await writeFile(path.join(evidence, "browser.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (unexpected.length || cases.some(c => c.status === "FAIL")) process.exitCode = 1;
}
