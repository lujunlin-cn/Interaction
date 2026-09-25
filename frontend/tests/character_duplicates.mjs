/** Real Standard UI + isolated real backend. No external providers or live DB. */
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dir = await mkdtemp(path.join(tmpdir(), 'character-duplicates-'));
const evidence = path.join(root, 'docs/acceptance/biohazard_full_e2e/continuation');
await mkdir(evidence, {recursive: true});
const base = 'http://127.0.0.1:9003';
const server = spawn(path.join(root, 'backend/.venv/bin/python'), ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '9003'], {
  cwd: path.join(root, 'backend'), stdio: 'ignore',
  env: {...process.env, PYTHONPATH: '.', DATABASE_URL: `sqlite+aiosqlite:///${dir}/test.db`, DATA_DIR: `${dir}/data`, MEDIA_DIR: `${dir}/media`, PROVIDER_MODE: 'mock', PROFILE_LIFECYCLE_ENABLED: 'false', FAL_PAID_GENERATION_ENABLED: 'false'},
});
let browser;
const cases = [], posts = [];
try {
  for (let i = 0; i < 100; i++) {
    if (server.exitCode !== null) throw Error('Isolated test backend stopped');
    try { if ((await fetch(base + '/api/health')).ok) break; } catch {}
    await new Promise(r => setTimeout(r, 100));
    if (i === 99) throw Error('Isolated backend unavailable');
  }
  browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
  let loseResponse = true;
  await page.route('**/api/**', async route => {
    const request = route.request(), pathname = new URL(request.url()).pathname;
    if (/ai-generate|edit-image|standard-views|understanding|sessions/.test(pathname)) throw Error('Paid or unrelated operation forbidden');
    if (request.method() === 'POST' && pathname === '/api/characters') {
      posts.push(request.postDataJSON());
      if (loseResponse) { loseResponse = false; const response = await route.fetch(); assert.equal(response.status(), 200); return route.abort('connectionreset'); }
    }
    return route.continue();
  });
  await page.goto(base + '/#/characterLibrary');
  await page.getByRole('button', {name: '新建角色', exact: true}).click();
  await page.getByRole('button', {name: '手动创建', exact: true}).click();
  await page.getByLabel('姓名', {exact: true}).fill('Morgan · Vale');
  await page.getByLabel('角色描述', {exact: true}).fill('A careful archivist');
  await page.getByRole('button', {name: '创建并进入 Studio', exact: true}).dblclick();
  await page.getByRole('button', {name: '创建并进入 Studio', exact: true}).waitFor({state: 'visible'});
  await page.waitForFunction(() => document.body.textContent.includes('创建失败'));
  const getCharacters = async () => (await (await fetch(base + '/api/characters')).json()).items;
  assert.equal((await getCharacters()).filter(c => c.name === 'Morgan · Vale').length, 1);
  cases.push({name: 'Double click commits one Character', result: 'PASS'});
  const token = posts[0].creation_idempotency_key;
  await page.reload();
  await page.getByRole('button', {name: '新建角色', exact: true}).click();
  assert.equal(await page.getByLabel('姓名', {exact: true}).inputValue(), 'Morgan · Vale');
  await page.getByRole('button', {name: '创建并进入 Studio', exact: true}).click();
  await page.getByRole('heading', {name: 'Morgan · Vale', exact: true}).waitFor();
  assert.equal(posts[1].creation_idempotency_key, token);
  assert.equal((await getCharacters()).filter(c => c.name === 'Morgan · Vale').length, 1);
  cases.push({name: 'Lost response + page reload retry reuses creation token', result: 'PASS'});
  await page.getByRole('button', {name: '← 返回角色库', exact: true}).click();
  await page.getByRole('button', {name: '新建角色', exact: true}).click();
  await page.getByRole('button', {name: '手动创建', exact: true}).click();
  await page.getByLabel('姓名', {exact: true}).fill('ＭＯＲＧＡＮ-ＶＡＬＥ');
  await page.getByLabel('角色描述', {exact: true}).fill('A genuinely different person');
  await page.getByText('角色库中可能已经存在这个角色', {exact: true}).waitFor();
  await page.screenshot({path: path.join(evidence, 'duplicate_protection_isolated.png')});
  await page.getByRole('button', {name: '仍然创建新角色', exact: true}).click();
  await page.getByRole('heading', {name: 'ＭＯＲＧＡＮ-ＶＡＬＥ', exact: true}).waitFor();
  assert.equal((await getCharacters()).filter(c => /Morgan|ＭＯＲＧＡＮ/.test(c.name)).length, 2);
  cases.push({name: 'Normalized duplicate warning and explicit second identity', result: 'PASS'});
  await writeFile(path.join(evidence, 'duplicate_browser_regression.json'), JSON.stringify({scope: 'isolated real backend + Standard UI', viewport: '1920x1080', paid_media_requests: 0, cases, creation_requests: posts}, null, 2));
  console.log(JSON.stringify(cases));
} finally {
  await browser?.close();
  server.kill('SIGTERM'); // Only our isolated :9003 process; preserve official :9000 and Nemotron.
  await new Promise(r => server.once('exit', r));
  await rm(dir, {recursive: true, force: true});
}
