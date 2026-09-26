// Settings-only browser regression; never creates a session or a media job.
const {chromium, firefox} = require('../frontend/node_modules/playwright');
const fs = require('fs'), path = require('path'), assert = require('assert').strict;
const base = 'http://127.0.0.1:9000';
const out = path.resolve(__dirname, '../docs/acceptance/media_language');
(async () => {
  let browser;
  try { browser = await chromium.launch({headless: true}); }
  catch { browser = await firefox.launch({headless: true}); }
  const page = await browser.newPage({viewport: {width: 1440, height: 1100}});
  const requests = [], errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('drama.mode', 'standard'));
  await page.route('**/api/**', async route => {
    const r = route.request(), p = new URL(r.url()).pathname;
    if (r.method() !== 'GET' && !(p === '/api/settings/language' && r.method() === 'PUT')) {
      errors.push('Unexpected write blocked: ' + p);
      return route.abort();
    }
    if (r.method() !== 'GET') requests.push({path: p, method: r.method(), body: r.postDataJSON()});
    return route.continue();
  });
  try {
    await page.goto(base + '/#/settings');
    const video = page.getByLabel('视频语言', {exact: true});
    const subtitle = page.getByLabel('字幕语言', {exact: true});
    await video.waitFor();
    await page.waitForFunction(() => !document.querySelector('select[aria-label="视频语言"]')?.disabled);
    const select = async (control, value) => {
      if (await control.inputValue() === value) return;
      const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/settings/language' && r.request().method() === 'PUT');
      await control.selectOption(value);
      assert((await response).ok());
      await page.waitForFunction(() => !document.querySelector('select[aria-label="视频语言"]')?.disabled);
      assert.equal(await control.inputValue(), value);
    };
    const states = [];
    for (const [v, s] of [['zh-CN','zh-CN'], ['en','zh-CN'], ['en','en'], ['zh-CN','en']]) {
      await select(video, v); await select(subtitle, s);
      const actual = await (await page.request.get(base + '/api/settings/language')).json();
      assert.deepEqual(actual, {video_language:v, subtitle_language:s});
      states.push(actual);
    }
    await page.screenshot({path: path.join(out, 'settings_chinese_video_english_subtitles.png'), fullPage:true});
    await page.reload();
    await page.waitForFunction(() => !document.querySelector('select[aria-label="视频语言"]')?.disabled);
    assert.equal(await subtitle.inputValue(), 'en');
    await select(subtitle, 'zh-CN');
    // Saving errors must remain visible; the controls retain the saved value.
    await page.route('**/api/settings/language', async route => {
      if (route.request().method() === 'PUT') return route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({detail:'temporary test error'})});
      return route.fallback();
    });
    await video.selectOption('en');
    await page.getByRole('alert').filter({hasText:'语言设置未保存'}).waitFor();
    assert.equal(await video.inputValue(), 'zh-CN');
    await page.unroute('**/api/settings/language');
    await page.reload();
    await page.waitForFunction(() => !document.querySelector('select[aria-label="视频语言"]')?.disabled);
    assert.equal(await video.inputValue(), 'zh-CN');
    assert.equal(await subtitle.inputValue(), 'zh-CN');
    await page.screenshot({path:path.join(out,'settings_default_chinese.png'), fullPage:true});
    assert.equal(await page.getByText('Jev 推荐预生成视频',{exact:true}).count(),0);
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(out, 'browser_regression.json'), JSON.stringify({at_utc:new Date().toISOString(),status:'PASS',states,refresh_persistence:'PASS',failed_save_feedback:'PASS',standard_mode:'PASS',requests,errors,paid_generation_requests:0,final:{video_language:'zh-CN',subtitle_language:'zh-CN'}},null,2));
    console.log('PASS: four language pairs, persistence, save failure, Standard UI; no paid requests.');
    await page.goto(base + '/#/home');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
