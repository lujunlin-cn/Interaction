/** Explicit Standard Player text action. Developer endpoints are read-only evidence. */
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
const [sid, label, action] = process.argv.slice(2);
assert(sid && /^[a-z0-9_]+$/.test(label), 'session and safe evidence label required');
const base = 'http://127.0.0.1:9000';
const folder = new URL('../docs/acceptance/biohazard_full_e2e/continuation/text_tail/', import.meta.url);
await mkdir(folder, { recursive: true });
const get = async path => { const r = await fetch(base + '/api/' + path); assert(r.ok, path); return r.json(); };
const save = async (name, data) => writeFile(new URL(label + '_' + name + '.json', folder), JSON.stringify(data, null, 2));
const capture = async phase => {
  const result = {};
  for (const [name, path] of Object.entries({ state: 'dev/sessions/' + sid + '/state', view: 'sessions/' + sid + '/view', usage: 'dev/usage-ledger', traces: 'dev/traces?limit=2000' })) {
    result[name] = await get(path); await save(phase + '_' + name, result[name]);
  }
  return result;
};
const before = await capture('before');
assert.equal(before.state.text_mode, true, 'Refuse action that could buy media');
assert.equal(before.view.generating.length, 0, 'Wait for current work before another action');
const settings = await get('dev/generation-settings');
assert.equal(settings.pre_generate_recommendation_media, false);
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await context.newPage();
const mutations = [], errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('request', r => { if (r.method() !== 'GET') mutations.push({ method: r.method(), url: r.url(), body: r.postData() }); });
await page.addInitScript(s => { localStorage.setItem('drama.mode', 'standard'); localStorage.setItem('drama.sessionId', s); }, sid);
const start = Date.now();
try {
  await page.goto(base + '/#/player');
  await page.locator('.player-shell[data-decision-open]').waitFor();
  if (action === '--continue') {
    assert.equal(before.view.ended, true);
    await page.getByRole('button', { name: '让故事继续', exact: true }).click();
  } else if (action) {
    await page.getByRole('textbox', { name: '描述你想做的事', exact: true }).fill(action);
    await page.getByRole('button', { name: '行动', exact: true }).click();
  }
  if (action) {
    for (let i = 0; i < 120; i++) {
      await page.waitForTimeout(1000);
      const v = await get('sessions/' + sid + '/view');
      if (v.pending_intent) {
        const confirm = page.getByRole('button', { name: '确认并继续', exact: true });
        if (await confirm.isVisible()) await confirm.click();
      }
      if (v.last_failed_action || v.player.status.includes('FAILED')) break;
      if (action === '--continue' ? v.arc.seq > before.view.arc.seq : v.selected?.status === 'CANONICAL' && v.selected?.branch_id !== before.view.selected?.branch_id) break;
    }
  }
  await page.screenshot({ path: new URL(label + '.png', folder).pathname });
  await writeFile(new URL(label + '_visible.txt', folder), await page.locator('body').innerText());
  const after = await capture('after');
  const summary = { label, session_id: sid, duration_seconds: (Date.now() - start) / 1000, text_mode: after.state.text_mode, status: after.view.player.status, selected: after.view.selected, ended: after.view.ended, arc: after.view.arc, scene: after.view.player.scene_text, known: after.view.known, timed: after.view.timed, mutations, errors };
  await save('summary', summary);
  console.log(JSON.stringify(summary, null, 2));
} finally { await browser.close(); }
