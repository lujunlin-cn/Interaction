/** Read-only UI layout check on the historical failed session; never successful H3 evidence. */
const { chromium } = require('../../../frontend/node_modules/playwright');
const fs = require('node:fs');
const base = process.env.BASE_URL || 'http://127.0.0.1:9000';
const sid = 'sess_00028_dc6cb4';
const out = __dirname;
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const results = [];
  for (const viewport of [{ width: 1920, height: 1080 }, { width: 2560, height: 1440 }]) {
    const context = await browser.newContext({ viewport });
    const writes = [], errors = [];
    await context.route('**/api/**', async route => {
      const request = route.request();
      if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
        writes.push({ method: request.method(), path: new URL(request.url()).pathname });
        return route.abort('blockedbyclient');
      }
      await route.continue();
    });
    const page = await context.newPage();
    page.on('pageerror', err => errors.push(String(err)));
    await page.addInitScript(id => {
      localStorage.setItem('drama.mode', 'standard');
      localStorage.setItem('drama.sessionId', id);
    }, sid);
    await page.goto(base + '/#/player');
    const input = page.getByRole('textbox', { name: '描述你想做的事' });
    await input.fill('检查剧场布局：保留这段未提交的行动');
    await page.locator('.appframe[data-theater-mode=\"true\"]').waitFor();
    const inspect = () => page.evaluate(() => {
      const box = selector => { const e = document.querySelector(selector); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height, bottom: r.bottom }; };
      return {
        fullscreen: !!document.fullscreenElement,
        theater: document.querySelector('.appframe')?.dataset.theaterMode,
        sidebar: !!document.querySelector('#sidebar'),
        headerVisible: !!document.querySelector('.player-head')?.checkVisibility(),
        stage: box('.player-stage'), agency: box('[data-layer=agency]'), hud: box('[data-layer=hud]'),
        controls: box('.player-controls'), error: box('.media-status.failed'),
        decisionCount: document.querySelectorAll('[data-layer=decision]').length,
        inspectorCount: document.querySelectorAll('.developer-inspector').length,
        bodyText: document.body.innerText,
      };
    });
    const state = await inspect();
    await page.screenshot({ path: `${out}/theater_readonly_${viewport.width}.png`, fullPage: true });
    const toggle = page.getByRole('button', { name: '故事随身册' });
    await toggle.hover(); await page.locator('.hud-drawer').waitFor();
    await toggle.click(); await page.mouse.move(viewport.width - 200, 120);
    const pinned = await toggle.getAttribute('aria-pressed') === 'true' && await page.locator('.hud-drawer').isVisible();
    await page.screenshot({ path: `${out}/hud_readonly_${viewport.width}.png`, fullPage: true });
    await toggle.click(); await page.mouse.move(viewport.width - 200, 120);
    const unpinned = await page.locator('.hud-drawer').count() === 0;
    await page.locator('.player-more summary').click();
    await page.getByRole('button', { name: '退出剧场模式', exact: true }).click();
    const preserved = await input.inputValue() === '检查剧场布局：保留这段未提交的行动' && await page.evaluate(id => localStorage.getItem('drama.sessionId') === id, sid);
    results.push({ viewport, state, pinned, unpinned, sessionAndInputPreserved: preserved, blockedMutations: writes, errors });
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(`${out}/theater_readonly.json`, JSON.stringify({ captured_at: new Date().toISOString(), session_id: sid, evidence_scope: 'Read-only layout check on historical FAILED_RECOVERABLE opening; no real playable H3 or new session evidence', results }, null, 2));
  console.log(JSON.stringify(results.map(({ state: { bodyText, ...state }, ...r }) => ({ ...r, state })), null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
