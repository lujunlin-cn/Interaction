// Explicit Standard UI confirmation; one character per invocation.
const {chromium} = require('../frontend/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [cid, name, label] = process.argv.slice(2);
const base = 'http://127.0.0.1:9000';
const folder = path.resolve(__dirname, '../docs/acceptance/biohazard_full_e2e/continuation');
(async () => {
  if (!cid || !name || !label) throw Error('character id, display name and label required');
  const marker = path.join(folder, `${label}_standard_views_ui.json`);
  if (fs.existsSync(marker)) throw Error('Operation already recorded; inspect checkpoint before retrying');
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  const posts = [];
  await page.route('**/api/**', async route => {
    const r=route.request();
    if(r.method()!=='GET') {
      if(new URL(r.url()).pathname!==`/api/characters/${cid}/standard-views` || posts.length) return route.abort();
      posts.push({at:new Date().toISOString(),path:new URL(r.url()).pathname,body:r.postDataJSON()});
      fs.writeFileSync(marker, JSON.stringify({status:'SUBMITTED',posts},null,2));
    }
    return route.continue();
  });
  try {
    await page.goto(base+'/#/characterLibrary');
    await page.getByRole('button').filter({has:page.getByRole('heading',{name,exact:true})}).click();
    await page.getByRole('button',{name:'造型',exact:true}).click();
    await page.getByRole('button',{name:'选择主图并生成标准视图',exact:true}).click();
    await page.getByText('生成标准参考图？将基于主图生成其他视角，请确认后继续。',{exact:true}).waitFor();
    await page.screenshot({path:path.join(folder,`${label}_standard_views_confirm.png`),fullPage:true});
    const pending=page.waitForResponse(r=>r.url().endsWith('/standard-views')&&r.request().method()==='POST',{timeout:900000});
    await page.getByRole('button',{name:'确认生成',exact:true}).click();
    const r=await pending;
    const result={status:r.status(),at:new Date().toISOString(),posts,body:await r.json()};
    fs.writeFileSync(marker,JSON.stringify(result,null,2));
    await page.waitForTimeout(500);
    await page.screenshot({path:path.join(folder,`${label}_standard_views_result.png`),fullPage:true});
    console.log(JSON.stringify(result));
    if(!r.ok()) process.exitCode=1;
  } finally {await browser.close();}
})();
