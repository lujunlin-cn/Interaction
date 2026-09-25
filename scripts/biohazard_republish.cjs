// Review existing authoring through Standard UI and publish updated visual pins.
const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert').strict;
const base='http://127.0.0.1:9000',sid='scn_00003_364d7e';
const root=path.resolve(__dirname,'../docs/acceptance/biohazard_full_e2e/continuation/republish');
fs.mkdirSync(root,{recursive:true});
const save=(name,value)=>fs.writeFileSync(path.join(root,name),JSON.stringify(value,null,2));
(async()=>{
 assert(!fs.existsSync(path.join(root,'published.json')),'Already published; reuse checkpoint');
 const b=await chromium.launch({headless:true}),p=await b.newPage({viewport:{width:1920,height:1080}});
 const get=async endpoint=>{const r=await p.request.get(base+endpoint);assert(r.ok());return r.json()};
 const writes=[];
 await p.route('**/api/**',async route=>{const r=route.request(),u=new URL(r.url()).pathname;
  if(r.method()!=='GET'){
   if(![ '/api/scenarios/'+sid, '/api/scenarios/'+sid+'/publish' ].includes(u))return route.abort();
   writes.push({at:new Date().toISOString(),method:r.method(),path:u,body:r.postDataJSON()});
  }return route.continue();
 });
 try{
  const before=await get('/api/scenarios/'+sid),globals=(await get('/api/characters')).items;save('draft_before.json',before);
  const oldSnapshots=await get('/api/scenarios/ver_00001_b26e3c/character-snapshots');
  save('v020_snapshots_before.json',oldSnapshots);
  await p.goto(base);await p.evaluate(id=>{localStorage.setItem('drama.editId',id);localStorage.setItem('drama.mode','standard')},sid);
  await p.goto(base+'/#/creator/characters');await p.reload();
  const pins=[];
  for(const old of before.characters.filter(c=>c.global_character_id)){
   const g=globals.find(c=>c.id===old.global_character_id);assert(g&&!g.archived);
   await p.getByRole('button',{name:old.identity,exact:true}).first().click();await p.getByRole('button',{name:'版本',exact:true}).click();
   if(g.version>old.global_character_version){
    await p.getByRole('button',{name:'查看变化',exact:true}).click();await p.screenshot({path:path.join(root,old.id+'_version_diff.png'),fullPage:true});
    await p.getByRole('button',{name:'更新到 v'+g.version,exact:true}).click();
    for(let i=0;i<60;i++){if((await get('/api/scenarios/'+sid)).characters.find(c=>c.id===old.id).global_character_version===g.version)break;assert(i<59,'Pin save timeout');await p.waitForTimeout(100);}
   }
   const next=(await get('/api/scenarios/'+sid)).characters.find(c=>c.id===old.id);
   assert.equal(next.global_character_version,g.version);assert.equal(next.global_character_id,old.global_character_id);assert.equal(next.outfit_id,old.outfit_id);
   for(const [key,source]of Object.entries(old.overlay_sources||{})){const field=key==='appearance'?'visual_state':key;if(source==='OVERRIDE'&&Object.hasOwn(old,field))assert.deepEqual(next[field],old[field]);}
   pins.push({character:old.id,global_id:g.id,old_pin:old.global_character_version,new_pin:g.version,overlays_preserved:true});
  }
  save('pin_review.json',pins);
  for(const [tab,label]of [['overview','故事概览'],['world','世界'],['drama','戏剧结构'],['mechanics','玩法机制'],['characters','角色'],['publish','发布']]){
   await p.goto(base+'/#/creator/'+tab);await p.waitForTimeout(400);
   await p.screenshot({path:path.join(root,tab+'.png'),fullPage:true});
   fs.writeFileSync(path.join(root,tab+'_visible.txt'),await p.locator('body').innerText());
  }
  const draft=await get('/api/scenarios/'+sid);
  for(const field of ['world','drama','mechanics','player_character'])assert.deepEqual(draft[field],before[field]);
  assert.equal(draft.player_character,'leon');
  const expected=['chr_00013_113084','chr_00018_204d12','chr_00032_149758'];
  assert.deepEqual(draft.characters.filter(c=>c.global_character_id).map(c=>c.global_character_id).sort(),expected.sort());
  const gate=await get('/api/scenarios/'+sid+'/publish-check');assert(gate.checklist.every(c=>c.ok));
  save('draft_reviewed.json',draft);save('publish_gate.json',gate);
  await p.getByRole('checkbox',{name:'我已审阅这个故事（世界规则、真相模型与结局族符合预期）',exact:true}).check();
  await p.screenshot({path:path.join(root,'publish_reviewed.png'),fullPage:true});
  const pending=p.waitForResponse(r=>r.url().endsWith('/publish')&&r.request().method()==='POST');
  await p.getByRole('button',{name:'发布新版本',exact:true}).click();
  const response=await pending,result=await response.json();assert(response.ok(),JSON.stringify(result));save('published.json',result);
  await p.waitForTimeout(500);await p.screenshot({path:path.join(root,'published.png'),fullPage:true});
  save('snapshots.json',await get('/api/scenarios/'+result.version_id+'/character-snapshots'));
  assert.deepEqual(await get('/api/scenarios/ver_00001_b26e3c/character-snapshots'),oldSnapshots);
  save('verification.json',{at:new Date().toISOString(),pins,immutable_v020_unchanged:true,authoring_and_overlays_preserved:true,publish:result,writes});
  console.log(JSON.stringify({published:result,pins}));
 }finally{save('ui_writes.json',writes);await b.close()}
})();
