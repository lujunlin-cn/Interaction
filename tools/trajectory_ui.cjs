// Isolated browser contracts. All API responses are fixtures; no live writes/media.
const {chromium,firefox}=require('../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert').strict;
const out=path.resolve(__dirname,'../docs/trajectory-analysis/browser');fs.mkdirSync(out,{recursive:true});
(async()=>{
 let browser;try{browser=await chromium.launch({headless:true});}catch{browser=await firefox.launch({headless:true});}
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{if(!localStorage.getItem('drama.mode'))localStorage.setItem('drama.mode','player');localStorage.setItem('drama.sessionId','research-fixture');});
 let view={session_id:'research-fixture',scenario:{title:'离线交互合约演示',player_identity:'调查员'},arc:{seq:1,total:1},
  player:{status:'WAITING_DECISION',scene_title:'已经抵达档案室',scene_text:'门锁解除，你抵达档案室。',caption:'门锁解除。',video_url:'',duration:0,lead:0,position:0},
  causal_presentation:{action:'使用门禁卡打开档案室',result:'门锁解除，你抵达档案室。',transition:'走廊 → 档案室',visual_focus:'把门禁卡贴近读卡器，推开门'},
  recommendations:[{branch_id:'a',label:'检查值班日志',summary:'核对停电前的最后记录',media_ready:false},{branch_id:'b',label:'询问同伴看到什么',summary:'一起判断是否继续进入',media_ready:false},{branch_id:'c',label:'退回安全通道',summary:'先为撤离保留一条路线',media_ready:false}],
  generating:[],known:{inventory:['门禁卡'],inventory_labels:{},relationships:[],clues:[],knowledge:[]},messages:[],wishes:[],hint_chips:[],ended:false,pending_intent:null,selected:null,timed:null};
 const initial=JSON.parse(JSON.stringify(view));
 const chain={window:'fixture window',metrics:[{skill_id:'intent-reconciliation',invocations:1,success:1,failure:0,average_latency_ms:12,latency_samples:1,proposal_count:0,proposals_in_committed_branches:0}],persistence:{pending:0,failures:0,dropped:0},chains:[{branch_id:'fixture-turn',calls:[{id:'span1',skill_id:'intent-reconciliation',skill_version:'2.0.0',status:'success',duration_ms:12,input:{why:'确认后的方式进入规划',raw:'先观察，不追击'},output:{strategy:'不追击'}}]}]};
 await page.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),p=url.pathname;
  let result={};
  if(req.method()!=='GET'){
   writes.push({path:p,body:req.postDataJSON()});
   if(p.endsWith('/intent/confirm')){view.pending_intent=null;result={status:'CANCELLED'};}
   else if(p.endsWith('/action')){view.pending_intent={kind:'clarification',raw_text:'先看看门外，不追击',action:'躲在门后观察',desire:'避免暴露',strategy:'先关灯，不主动攻击',confidence:.4};result={status:'CLARIFICATION_REQUIRED'};}
   else throw new Error('Unexpected write '+p);
  }else if(p.endsWith('/view'))result=view;
  else if(p==='/api/skills/observatory')result=chain;
  else if(p==='/api/skills')result={platform:[],mechanics:[]};
  else if(p.endsWith('/state'))result={branches:[],world:{version:1,inventory:[],relationships:{},clues:{},knowledge:[],truth:{}},drama:{revision:1,foreshadows:[]},pressures:[],wishes:[],committed_keys:[],events:[],budget:{},player:{}};
  else if(p.includes('/traces'))result={items:[]};
  else if(p.includes('/providers'))result={providers:[],routes:{}};
  else if(p.includes('/language'))result={video_language:'zh-CN',subtitle_language:'zh-CN'};
  else result={items:[]};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)});
 });
 try{
  await page.goto('http://127.0.0.1:9017/#/player');
  await page.getByTestId('action-result').locator('summary').click();
  await page.getByText('门锁解除，你抵达档案室。',{exact:false}).first().waitFor();
  assert.equal(await page.locator('.rec-card').count(),3);
  await page.getByLabel('描述你想做的事').fill('先看看门外，不追击');
  await page.screenshot({path:path.join(out,'causal_result_and_choices.png'),fullPage:true});
  await page.getByRole('button',{name:'行动',exact:true}).click();
  await page.locator('.intent-summary').waitFor();
  assert.equal(await page.locator('.intent-form input').count(),0);
  assert((await page.locator('.intent-summary').innerText()).includes('避免暴露'));
  await page.getByRole('button',{name:'修改理解',exact:true}).click();
  const strategy=page.getByLabel('可能的方式（可选修改）');await strategy.fill('不追击，只看清人数');
  await page.screenshot({path:path.join(out,'ai_prefilled_confirmation.png'),fullPage:true});
  await page.getByRole('button',{name:'确认并继续',exact:true}).click();
  assert(writes.some(x=>x.body.approved===true&&x.body.strategy==='不追击，只看清人数'));
  await page.waitForFunction(()=>!document.querySelector('.intent-card'));
  await page.getByLabel('描述你想做的事').fill('先看看门外，不追击');await page.getByRole('button',{name:'行动',exact:true}).click();
  await page.locator('.intent-summary').waitFor();
  await page.getByRole('button',{name:'算了，不这么做',exact:true}).click();
  assert(writes.some(x=>x.body.approved===false));
  assert(!await page.getByText('Skill Observatory',{exact:false}).count());
  await page.evaluate(()=>localStorage.setItem('drama.mode','developer'));
  await page.goto('http://127.0.0.1:9017/#/developer/skills');await page.reload();
  await page.getByTestId('skill-observatory').waitFor();
  await page.getByText('Skill Chain · fixture-turn · 1 步',{exact:true}).click();
  await page.getByText('intent-reconciliation v2.0.0',{exact:false}).click();
  await page.getByText('确认后的方式进入规划',{exact:false}).waitFor();
  await page.screenshot({path:path.join(out,'skill_observatory.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({status:'PASS',mode:'isolated browser fixtures',tests:['causal receipt','three purposes plus free input','AI-prefilled optional fields','edited confirmation payload','cancellation','Developer skill chain detail','Standard no internals'],writes,errors,live_writes:0,paid_media_requests:0},null,2));
  console.log('PASS: isolated UI contracts; no live writes or media.');
 }catch(e){fs.writeFileSync(path.join(out,'failure_debug.json'),JSON.stringify({error:String(e),errors,url:page.url(),body:await page.locator('body').innerText()},null,2));throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
