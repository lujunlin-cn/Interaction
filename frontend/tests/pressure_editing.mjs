/** Standard Creator pressure editing. All API calls mocked; no live service. */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { chromium } from "playwright";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const evidence = path.resolve(root, "../docs/acceptance/pressure_contract");
await mkdir(evidence, { recursive: true });
const origin = "http://127.0.0.1:9002";
const server = await createServer({ root, configFile: false, server: { host: "127.0.0.1", port: 9002, strictPort: true, hmr: false } });
await server.listen();
const browser = await chromium.launch({ headless: true });
const cases = [], unexpected = [];

async function run(name, pressure, change, expected) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const patches = [];
  let draft = { id: "pressure-test", title: "压力编辑回归", description: "", genre: "调查", tone: "克制", play_style: "调查",
    player_character: "p", characters: [], world: { rules: "", lore: "", locations: "", constraints: "" },
    drama: { core_question: "如何通过调查解决危险？", central_conflict: "", truth_model: "", secrets: "", misbeliefs: "", pressures: pressure, anchors: "", ending_families: "", foreshadows: "", forbidden_outcomes: "", timed_interactions: "" },
    mechanics: {}, theme: {}, changes: [], locks: [], manual_edits: [], updated_at: 1, status: "DRAFT", version: "1.0.0", owner: "user" };
  await page.addInitScript(() => { localStorage.setItem("drama.editId", "pressure-test"); localStorage.setItem("drama.mode", "standard"); });
  await context.route("**/*", async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin !== origin) { unexpected.push(request.url()); return route.abort(); }
    if (!url.pathname.startsWith("/api/")) return route.continue();
    let body;
    if (url.pathname === "/api/scenarios") body = { items: [draft] };
    else if (url.pathname === "/api/characters" || url.pathname.endsWith("/versions")) body = { items: [] };
    else if (url.pathname === "/api/scenarios/pressure-test") {
      if (request.method() === "PUT") { draft = { ...request.postDataJSON(), updated_at: 2 }; patches.push(draft); }
      body = draft;
    } else { unexpected.push(`${request.method()} ${url.pathname}`); body = { detail: "unexpected" }; }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
  try {
    await page.goto(`${origin}/#/creator/drama`);
    const field = page.locator(".character-understanding").filter({ hasText: "推动故事的压力" });
    await field.waitFor();
    assert.equal((await field.innerText()).includes('"trigger_type"'), false, "Standard leaked raw JSON");
    await field.getByRole("button", { name: "修改", exact: true }).click();
    if (change) await field.locator("textarea").fill(change);
    await field.getByRole("button", { name: "保存", exact: true }).click();
    if (expected === null) {
      await page.getByText(/请说明这项压力是随行动触发/).waitFor();
      assert.equal(patches.length, 0);
      assert.equal(await field.locator("textarea").count(), 1, "input was lost on validation error");
    } else {
      await page.waitForFunction(() => !document.querySelector(".character-understanding textarea"));
      await page.waitForTimeout(50);
      assert.equal(patches.length, 1);
      assert.equal(patches[0].drama.pressures, expected);
    }
    await page.screenshot({ path: path.join(evidence, `${name}.png`), fullPage: true });
    cases.push({ name, status: "PASS", save_requests: patches.length });
  } catch (error) { cases.push({ name, status: "FAIL", error: String(error) }); }
  finally { await context.close(); }
}

try {
  await run("old_wrong_tail", "供电恶化｜设施损毁与故事时间推进｜安全门与系统权限随电力减少而失效", "设施损毁导致门禁逐步失效", "供电恶化｜设施损毁导致门禁逐步失效｜故事时间推进");
  await run("structured_json_is_readable", JSON.stringify([{ name: "封锁逼近", source: "电力减少", trigger_type: "故事时间推进" }]), "电力减少后门禁逐步关闭", "封锁逼近｜电力减少后门禁逐步关闭｜故事时间推进");
  await run("ambiguous_driver_preserves_input", "危机｜天气恶化｜路线关闭", "风暴令道路关闭", null);
  await run("explicit_driver_is_honored", "危机｜天气恶化｜路线关闭", "道路会随故事时间推进关闭", "危机｜道路会随故事时间推进关闭｜故事时间推进");
  await run("existing_valid_driver_retained", "警报｜安全系统｜行动触发", "强行开门会启动警报", "警报｜强行开门会启动警报｜行动触发");
} finally {
  await browser.close(); await server.close();
  const report = { date: new Date().toISOString(), mode: "isolated browser API mocks", viewport: "1920x1080", external_paid_media_requests: 0, unexpected, cases };
  await writeFile(path.join(evidence, "browser.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (unexpected.length || cases.some(c => c.status === "FAIL")) process.exitCode = 1;
}
