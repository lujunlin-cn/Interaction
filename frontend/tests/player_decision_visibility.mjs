/** Offline UI regression: decision availability is independent of media/recommendations. */
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('..', import.meta.url));
const output = fileURLToPath(new URL('../../docs/acceptance/player_decision_visibility/', import.meta.url));
await mkdir(output, { recursive: true });
const server = await createServer({ root, configFile: false, server: { host: '127.0.0.1', port: 9014, strictPort: true, hmr: false } });
await server.listen();
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await context.newPage();
const cases = [], unexpected = [];
const view = {
  session_id: 'visibility', scenario: { title: '文字与视频抉择回归', player_identity: '调查员' }, arc: { seq: 1, total: 1 },
  player: { status: 'WAITING_DECISION', scene_title: '阅读完成', scene_text: '你和同伴读完记录，准备决定下一步。', caption: '', video_url: '', duration: 0, lead: 0, decision_open_at: 0, position: 0 },
  recommendations: [], generating: [], known: { inventory: [], relationships: [], clues: [], knowledge: [] }, wishes: [], messages: [],
  selected: null, timed: null, pending_intent: null, last_failed_action: null, action_pending: false, ended: false, pending_continuation: false,
};
await page.addInitScript(() => { localStorage.setItem('drama.mode', 'standard'); localStorage.setItem('drama.sessionId', 'visibility'); });
await context.routeWebSocket('**/*', ws => ws.onMessage(() => {}));
await context.route('**/*', route => {
  const req = route.request(), url = new URL(req.url());
  if (url.origin !== 'http://127.0.0.1:9014' || req.method() !== 'GET') { unexpected.push(req.url()); return route.abort(); }
  if (!url.pathname.startsWith('/api/')) return route.continue();
  return route.fulfill({ contentType: 'application/json', body: JSON.stringify(url.pathname.endsWith('/view') ? view : { items: [] }) });
});
try {
  await page.goto('http://127.0.0.1:9014/#/player');
  await page.locator('.player-shell[data-decision-open]').waitFor();
  const input = page.getByRole('textbox', { name: '描述你想做的事', exact: true });
  const scenarios = [
    { name: 'text_wait_without_recommendations', status: 'WAITING_DECISION', position: 0, duration: 0, lead: 0, open: true },
    { name: 'playing_before_lead', status: 'PLAYING', position: 1, duration: 8, lead: 5, open: false },
    { name: 'lead_without_recommendations', status: 'PLAYING', position: 5, duration: 8, lead: 5, open: true },
    { name: 'waiting_for_jev_after_video', status: 'WAITING_DECISION', position: 8, duration: 8, lead: 5, open: true },
    { name: 'arc_two_wait_without_recommendations', status: 'WAITING_DECISION', position: 0, duration: 0, lead: 0, open: true },
  ];
  for (const s of scenarios) {
    Object.assign(view.player, { status: s.status, position: s.position, duration: s.duration, decision_open_at: s.lead, lead: s.lead });
    await page.waitForTimeout(1250);
    const actual = await page.locator('.player-shell').getAttribute('data-decision-open');
    assert.equal(actual, String(s.open), s.name);
    assert.equal(await input.isVisible(), s.open, s.name + ': input');
    assert.equal(await page.locator('.player-controls').isVisible(), s.open, s.name + ': controls');
    assert.equal(await page.locator('.hud-toggle').isVisible(), s.open, s.name + ': HUD');
    if (s.open) { await input.fill('我与同伴核对记录。'); await page.getByRole('button', { name: '行动', exact: true }).click({ trial: true }); }
    await page.screenshot({ path: output + s.name + '.png' });
    cases.push({ ...s, result: 'PASS' });
  }
  assert.deepEqual(unexpected, []);
} finally {
  await browser.close(); await server.close();
  await writeFile(output + 'regression.json', JSON.stringify({ scope: 'offline UI; no provider calls', cases, unexpected }, null, 2));
}
console.log(JSON.stringify({ passed: cases.length, paid_media_requests: 0 }));
