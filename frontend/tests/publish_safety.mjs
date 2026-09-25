/** Browser regression for Creator publish. All API traffic is mocked in browser;
 * no backend, model, generation request, or published story is created.
 * Run: node tests/publish_safety.mjs (from frontend).
 */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { chromium } from "playwright";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const evidence = path.resolve(root, "../docs/acceptance/publish_safety");
const origin = "http://127.0.0.1:9002";
const draft = () => ({
  id: "publish_regression", title: "发布安全回归", description: "", genre: "调查", tone: "克制",
  play_style: "自由行动", player_character: "tester", status: "DRAFT", version: "0.0.0", owner: "user",
  world: { rules: "已发生的事实不能撤销。", lore: "隔离测试", locations: "entry｜入口", constraints: "无外部调用" },
  characters: [{ id: "tester", identity: "测试角色", personality: "", desire: "", fear: "", secrets: "", knowledge: "", relationship: "", visual_state: "" }],
  drama: { core_question: "如何安全发布？", central_conflict: "保存与发布", truth_model: "事实已确认", secrets: "", misbeliefs: "", pressures: "时间", anchors: "", ending_families: "完成", foreshadows: "", forbidden_outcomes: "", timed_interactions: "" },
  mechanics: {}, theme: { accent: "#728adb", font: "system", density: "comfortable", subtitles: "normal", background: "plain" },
  reviewed: false, manual_edits: [], locks: [], changes: [], updated_at: 1,
});
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const cases = [];
await mkdir(evidence, { recursive: true });
const server = await createServer({ root, configFile: false, server: { host: "127.0.0.1", port: 9002, strictPort: true, hmr: false } });
await server.listen();
const browser = await chromium.launch({ headless: true });
let paidRequests = 0;

async function setup(tab = "publish", { assetWarning = false } = {}) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const state = { draft: draft(), events: [], posts: [], saveGate: null, saveFailed: false, checkGate: null, publishGate: null, failNextCheck: false, updateOnNextRead: false, assetWarning, unexpected: [] };
  await page.addInitScript(() => { localStorage.setItem("drama.editId", "publish_regression"); localStorage.setItem("drama.mode", "standard"); });
  await context.route("**/*", async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin !== origin) { state.unexpected.push(request.url()); paidRequests++; return route.abort(); }
    if (!url.pathname.startsWith("/api/")) return route.continue();
    const method = request.method(), pathname = url.pathname;
    state.events.push({ method, path: pathname, event: "start" });
    const fulfill = async (data, status = 200) => { state.events.push({ method, path: pathname, event: "complete", status }); await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) }); };
    if (pathname === "/api/scenarios") return fulfill({ items: [state.draft] });
    if (pathname === "/api/characters") return fulfill({ items: [] });
    if (pathname === "/api/scenarios/publish_regression" && method === "GET") {
      if (state.updateOnNextRead) { state.updateOnNextRead = false; state.draft = { ...state.draft, title: "已更新的故事", updated_at: state.draft.updated_at + 1 }; }
      return fulfill(state.draft);
    }
    if (pathname === "/api/scenarios/publish_regression" && method === "PUT") {
      if (state.saveGate) await state.saveGate.promise;
      if (state.saveFailed) return fulfill({ detail: "保存失败，请重试。" }, 422);
      state.draft = { ...request.postDataJSON(), updated_at: state.draft.updated_at + 1 };
      return fulfill(state.draft);
    }
    if (pathname.endsWith("/versions")) return fulfill({ items: [] });
    if (pathname.endsWith("/publish-check")) {
      if (state.checkGate) await state.checkGate.promise;
      const failed = state.failNextCheck; state.failNextCheck = false;
      const checklist = [{ id: "world_rules", label: "世界规则", ok: !failed, detail: failed ? "缺少规则" : "" }];
      if (state.assetWarning) checklist.push({ id: "char_assets", label: "角色视觉资产", ok: true, detail: "警告：角色缺少 CANONICAL 资产（视频制作时需补充或使用文字模式）：chr_private_missing_image" });
      return fulfill({ checklist });
    }
    if (pathname.endsWith("/publish") && method === "POST") {
      state.posts.push(request.postDataJSON());
      if (state.publishGate) await state.publishGate.promise;
      return fulfill({ version_id: "version_mock", version: "1.0.0" });
    }
    state.unexpected.push(`${method} ${pathname}`);
    return fulfill({ detail: "Unexpected test request" }, 500);
  });
  await page.goto(`${origin}/#/creator/${tab}`);
  const review = page.getByRole("checkbox", { name: /我已审阅/ });
  const publish = page.getByRole("button", { name: "发布新版本", exact: true });
  const play = page.getByRole("button", { name: "发布并试玩", exact: true });
  return { page, context, state, review, publish, play };
}

async function until(fn, message) {
  const deadline = Date.now() + 5000;
  while (!await fn()) { if (Date.now() > deadline) throw new Error(message); await new Promise(r => setTimeout(r, 20)); }
}
async function ready(t) { await t.review.waitFor(); await until(() => t.review.isEnabled(), "review never became available"); }
async function record(name, test) {
  const started = Date.now();
  try { await test(); cases.push({ name, status: "PASS", elapsed_ms: Date.now() - started }); }
  catch (error) { cases.push({ name, status: "FAIL", error: String(error) }); }
}

try {
  await record("missing character image warning stays visible while text publication is allowed", async () => {
    const t = await setup("publish", { assetWarning: true });
    try {
      await ready(t);
      const warning = t.page.getByText("部分角色尚未设置视觉身份。可以先发布文字故事；制作视频前请补充角色图片，或选择文字模式。", { exact: true });
      assert.equal(await warning.isVisible(), true, "green char_assets check hid the missing-image warning");
      assert.doesNotMatch(await t.page.locator("body").innerText(), /CANONICAL|chr_private_missing_image/);
      assert.equal(await t.publish.isDisabled(), true, "warning must not automatically review the story");
      await t.review.check();
      assert.equal(await t.publish.isEnabled(), true, "missing image must not block reviewed text publication");
      await t.page.screenshot({ path: path.join(evidence, "text_publish_visual_warning.png"), fullPage: true });
      await t.publish.click();
      await until(() => t.state.posts.length === 1, "reviewed text story did not publish");
      assert.deepEqual(t.state.posts, [{ reviewed: true, play: false }]);
      assert.deepEqual(t.state.unexpected, []);
    } finally { await t.context.close(); }
  });
  await record("pending save completes before fresh publish checks", async () => {
    const t = await setup("world");
    try {
      t.state.saveGate = deferred();
      await t.page.getByLabel("World Rules / 世界规则").fill("修改后的规则必须先保存。");
      await until(() => t.state.events.some(e => e.method === "PUT" && e.event === "start"), "save did not start");
      await t.page.locator("#sidebar button").filter({ hasText: /^↑发布$/ }).click();
      await t.review.waitFor(); await t.page.waitForTimeout(100);
      assert.equal(await t.review.isDisabled(), true, "review was allowed while save pending");
      assert.equal(await t.publish.isDisabled(), true);
      assert.equal(t.state.events.filter(e => e.path.endsWith("/publish-check")).length, 0, "publish checks ran before saved draft");
      t.state.saveGate.resolve(); await ready(t);
      assert.equal(await t.review.isChecked(), false, "save completion must not auto-review");
      const saveDone = t.state.events.findIndex(e => e.method === "PUT" && e.event === "complete");
      const firstCheck = t.state.events.findIndex(e => e.path.endsWith("/publish-check"));
      assert.ok(saveDone >= 0 && firstCheck > saveDone);
      assert.equal(t.state.posts.length, 0);
      await t.page.screenshot({ path: path.join(evidence, "saved_before_review.png"), fullPage: true });
    } finally { t.state.saveGate?.resolve(); await t.context.close(); }
  });
  await record("failed save blocks publishing", async () => {
    const t = await setup("world");
    try {
      t.state.saveGate = deferred(); t.state.saveFailed = true;
      await t.page.getByLabel("World Rules / 世界规则").fill("无法保存的修改");
      await until(() => t.state.events.some(e => e.method === "PUT"), "save did not start");
      await t.page.locator("#sidebar button").filter({ hasText: /^↑发布$/ }).click();
      t.state.saveGate.resolve(); await t.review.waitFor(); await t.page.waitForTimeout(150);
      assert.equal(await t.review.isDisabled(), true);
      assert.equal(await t.publish.isDisabled(), true);
      assert.equal(await t.play.isDisabled(), true);
      assert.equal(t.state.posts.length, 0);
      await t.page.screenshot({ path: path.join(evidence, "save_failure_blocks_publish.png"), fullPage: true });
    } finally { await t.context.close(); }
  });
  await record("latest draft change invalidates earlier review", async () => {
    const t = await setup();
    try {
      await ready(t); await t.review.check(); t.state.updateOnNextRead = true;
      await t.publish.click(); await t.page.waitForTimeout(200);
      assert.equal(t.state.posts.length, 0, "published an unreviewed newer draft");
      assert.equal(await t.review.isChecked(), false);
      assert.equal(await t.publish.isDisabled(), true);
      await t.page.getByText("故事内容已更新，请重新检查并勾选审阅后再发布。", { exact: true }).waitFor();
      await t.page.screenshot({ path: path.join(evidence, "changed_draft_requires_review.png"), fullPage: true });
    } finally { await t.context.close(); }
  });
  await record("normalized draft converges and a new human review can publish", async () => {
    const t = await setup();
    try {
      await ready(t); await t.review.check();
      t.state.draft = { ...t.state.draft, drama: { ...t.state.draft.drama, pressures: "封锁｜供电减少｜故事时间推进" } };
      await t.publish.click();
      await until(() => t.review.isEnabled(), "normalized draft did not converge");
      await t.page.waitForTimeout(100);
      assert.equal(await t.review.isChecked(), false);
      assert.equal(t.state.posts.length, 0);
      const settledRequests = t.state.events.length;
      await t.page.waitForTimeout(100);
      assert.equal(t.state.events.length, settledRequests, "normalization caused an endless reload");
      await t.review.check(); await t.publish.click();
      await until(() => t.state.posts.length === 1, "fresh review could not publish normalized draft");
    } finally { await t.context.close(); }
  });
  await record("publish rechecks validity and rejects stale success", async () => {
    const t = await setup();
    try {
      await ready(t); await t.review.check(); t.state.failNextCheck = true;
      await t.publish.click(); await t.page.waitForTimeout(150);
      assert.equal(t.state.posts.length, 0, "published using stale checklist");
      assert.equal(await t.review.isChecked(), false);
      assert.equal(await t.publish.isDisabled(), true);
    } finally { await t.context.close(); }
  });
  await record("draft changed during fresh check requires a new review", async () => {
    const t = await setup();
    try {
      await ready(t); await t.review.check(); t.state.checkGate = deferred();
      const checkCount = t.state.events.filter(e => e.path.endsWith("/publish-check") && e.event === "start").length;
      await t.publish.click();
      await until(() => t.state.events.filter(e => e.path.endsWith("/publish-check") && e.event === "start").length > checkCount, "fresh check did not start");
      t.state.draft = { ...t.state.draft, title: "校验期间修改的故事", updated_at: t.state.draft.updated_at + 1 };
      t.state.checkGate.resolve(); await t.page.waitForTimeout(150);
      assert.equal(t.state.posts.length, 0);
      assert.equal(await t.review.isChecked(), false);
      assert.equal(await t.publish.isDisabled(), true);
    } finally { t.state.checkGate?.resolve(); await t.context.close(); }
  });
  await record("same-tick double click submits one play request", async () => {
    const t = await setup();
    try {
      await ready(t); await t.review.check(); t.state.publishGate = deferred();
      await t.play.evaluate(button => { button.click(); button.click(); button.parentElement.querySelector("button").click(); });
      await until(() => t.state.posts.length > 0, "publish did not submit");
      await t.page.waitForTimeout(100);
      assert.equal(t.state.posts.length, 1, "duplicate publish/session request");
      assert.equal(t.state.posts[0].play, true);
      assert.equal(await t.publish.isDisabled(), true);
      assert.equal(await t.play.isDisabled(), true);
      assert.equal(await t.review.isDisabled(), true);
      t.state.publishGate.resolve();
      await until(() => t.review.isEnabled(), "publish did not release UI");
      assert.equal(await t.review.isChecked(), false, "successful publish must require fresh review for another publication");
      assert.equal(await t.publish.isDisabled(), true);
      assert.deepEqual(t.state.unexpected, []);
      await t.page.screenshot({ path: path.join(evidence, "one_publish_request.png"), fullPage: true });
    } finally { t.state.publishGate?.resolve(); await t.context.close(); }
  });
  await record("changing Creator tabs does not release in-flight publish lock", async () => {
    const t = await setup();
    try {
      await ready(t); await t.review.check(); t.state.publishGate = deferred();
      await t.play.click(); await until(() => t.state.posts.length === 1, "publish did not submit");
      await t.page.locator("#sidebar button").filter({ hasText: /^◎世界$/ }).click();
      await t.page.getByLabel("World Rules / 世界规则").waitFor();
      await t.page.locator("#sidebar button").filter({ hasText: /^↑发布$/ }).click();
      await t.review.waitFor(); await t.page.waitForTimeout(100);
      assert.equal(await t.review.isDisabled(), true);
      assert.equal(await t.play.isDisabled(), true);
      assert.equal(t.state.posts.length, 1);
      t.state.publishGate.resolve(); await ready(t);
      assert.equal(await t.review.isChecked(), false);
    } finally { t.state.publishGate?.resolve(); await t.context.close(); }
  });
} finally {
  await browser.close(); await server.close();
  const report = { date: new Date().toISOString(), mode: "browser API mocks; no live backend", viewport: "1920x1080", external_paid_media_requests: paidRequests, cases };
  await mkdir(evidence, { recursive: true });
  await writeFile(path.join(evidence, "publish_safety.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (cases.some(c => c.status === "FAIL") || paidRequests) process.exitCode = 1;
}
