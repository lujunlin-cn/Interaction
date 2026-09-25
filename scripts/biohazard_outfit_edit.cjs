// One authorized business operation through Standard Character Studio.
// Does not retry the operation or start reference packs / Player sessions.
const { chromium } = require('../frontend/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const base = 'http://127.0.0.1:9000';
const evidence = path.resolve(__dirname, '../docs/acceptance/biohazard_full_e2e/continuation');
(async () => {
  if (fs.existsSync(path.join(evidence, 'leon_outfit_edit_ui_result.json'))) throw Error('Operation already recorded; inspect it before any new paid operation');
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
  const mutations = [];
  await page.route('**/api/**', async route => {
    const req = route.request();
    if (req.method() !== 'GET') {
      if (new URL(req.url()).pathname !== '/api/characters/chr_00013_113084/edit-image' || mutations.length) return route.abort();
      mutations.push({at: new Date().toISOString(), path: new URL(req.url()).pathname, body: req.postDataJSON()});
    }
    return route.continue();
  });
  try {
    await page.goto(base + '/#/characterLibrary');
    await page.getByRole('button').filter({has: page.getByRole('heading', {name: '李昂·S·肯尼迪', exact: true})}).click();
    await page.getByRole('button', {name: '造型', exact: true}).click();
    await page.getByRole('combobox', {name: /编辑源图/}).selectOption('ca_00016_628682');
    await page.getByLabel('非破坏式编辑（换装 / 背景 / 姿势 / 视角 / 自由文本）', {exact: true}).fill('制作同一个李昂的 RPD 执勤装备造型参考。严格保持源图的脸、年轻成年年龄、棕色短发与基本体型；只将服装调整为 RPD 警员制服、防护背心、实用战术装备，衣服有雨水与轻度污迹；没有伤势或感染特征。保持单人、清楚的正面身份与中性背景。');
    await page.screenshot({path: path.join(evidence, 'leon_outfit_edit_before.png'), fullPage: true});
    const pending = page.waitForResponse(r => r.url().endsWith('/edit-image') && r.request().method() === 'POST', {timeout: 600000});
    await page.getByRole('button', {name: '生成编辑形象', exact: true}).click();
    const response = await pending;
    const result = {at: new Date().toISOString(), status: response.status(), body: await response.json(), mutations};
    fs.writeFileSync(path.join(evidence, 'leon_outfit_edit_ui_result.json'), JSON.stringify(result, null, 2));
    await page.waitForTimeout(500);
    await page.screenshot({path: path.join(evidence, 'leon_outfit_edit_after.png'), fullPage: true});
    console.log(JSON.stringify(result));
  } finally { await browser.close(); } // Official services deliberately remain running.
})();
