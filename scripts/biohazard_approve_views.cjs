// Approve only existing standard views explicitly accepted by Step 5.
const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert').strict;
const [cid,name,label]=process.argv.slice(2), base='http://127.0.0.1:9000';
const root=path.resolve(__dirname,'../docs/acceptance/biohazard_full_e2e');
(async()=>{
  const qa=JSON.parse(fs.readFileSync(path.join(root,`visual_qa/${label}_reference_step5.json`)));
  assert.equal(qa.status,'SUCCEEDED');assert.equal(qa.result.recommendation,'accept');
  const accepted=new Set(qa.result.assets.filter(a=>!a.major_failure&&a.qa.recommendation==='accept').map(a=>a.asset_id));
  const b=await chromium.launch({headless:true}),p=await b.newPage({viewport:{width:1920,height:1080}});
  const writes=[];
  await p.route('**/api/**',async route=>{const r=route.request();if(r.method()!=='GET'){
    if(!/^\/api\/(character-assets\/[^/]+|characters\/[^/]+\/assets\/[^/]+\/approve)$/.test(new URL(r.url()).pathname))return route.abort();
    writes.push({path:new URL(r.url()).pathname,body:r.postDataJSON()});
  }return route.continue()});
  try{
    const get=async url=>(await p.request.get(base+url)).json();
    const before=(await get(`/api/characters/${cid}/character-assets`)).items;
    const views=before.filter(a=>['three_quarter','side','full_front','full_side'].includes(a.role)&&a.status!=='ARCHIVED');
    assert.equal(views.length,4);for(const a of views)assert(accepted.has(a.id));
    await p.goto(base+'/#/characterLibrary');
    await p.getByRole('button').filter({has:p.getByRole('heading',{name,exact:true})}).click();
    await p.getByRole('button',{name:'造型',exact:true}).click();
    for(const asset of views){
      if(asset.status==='CANONICAL')continue;
      const card=p.locator('.studio-asset').filter({has:p.locator(`img[src="${asset.url}"]`)});
      if(asset.status==='CANDIDATE'){
        await card.getByRole('button',{name:'确认候选图',exact:true}).click();
        await card.getByRole('button',{name:'确认候选图',exact:true}).waitFor({state:'hidden'});
      }
      await card.getByRole('button',{name:'设为主形象',exact:true}).click();
      await card.getByRole('button',{name:'设为主形象',exact:true}).waitFor({state:'hidden'});
    }
    await p.getByRole('button',{name:'身份',exact:true}).click();
    await p.waitForFunction(()=>Array.from(document.querySelectorAll('.identity-grid img')).length>=5&&Array.from(document.querySelectorAll('.identity-grid img')).every(x=>x.complete&&x.naturalWidth>0),{},{timeout:60000});
    await p.screenshot({path:path.join(root,`continuation/${label}_reference_pack_approved.png`),fullPage:true});
    const after=(await get(`/api/characters/${cid}/character-assets`)).items;
    assert.equal(after.filter(a=>a.status==='CANONICAL'&&['front','three_quarter','side','full_front','full_side'].includes(a.role)).length,5);
    const character=(await get('/api/characters')).items.find(c=>c.id===cid);
    const result={at:new Date().toISOString(),character,writes,assets:after};
    fs.writeFileSync(path.join(root,`continuation/${label}_reference_approved_ui.json`),JSON.stringify(result,null,2));
    console.log(JSON.stringify({character:cid,version:character.version,canonical_views:5}));
  }finally{await b.close()}
})();
