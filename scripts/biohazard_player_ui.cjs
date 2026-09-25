// Standard UI browser controller; never stops live services.
const {chromium,firefox}=require('../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert').strict;
const base='http://127.0.0.1:9000',scenario='scn_00003_364d7e';
const run=process.argv[2]||'play';
assert(/^[a-z0-9_]+$/.test(run));
const root=path.resolve(__dirname,'../docs/acceptance/biohazard_full_e2e/continuation',run);
fs.mkdirSync(root,{recursive:true});
const file=n=>path.join(root,n),save=(n,v)=>fs.writeFileSync(file(n),JSON.stringify(v,null,2));
const log=(n,v)=>fs.appendFileSync(file(n),JSON.stringify({at:new Date().toISOString(),...v})+String.fromCharCode(10));
(async()=>{
 const browserType=process.env.E2E_BROWSER==='firefox'?firefox:chromium;
 const browser=await browserType.launch({headless:true}),page=await browser.newPage({viewport:{width:1920,height:1080}});
 save('browser_environment.json',{browser:browserType.name(),version:browser.version(),viewport:{width:1920,height:1080},preserve_live_services:true});
 page.setDefaultTimeout(20000);
 await page.addInitScript(() => { window.__videoEvents=[]; for(const kind of ['loadstart','loadedmetadata','canplay','playing','waiting','pause','ended','error']) document.addEventListener(kind,e=>{const v=e.target;if(v instanceof HTMLVideoElement)window.__videoEvents.push({at:Date.now(),kind,currentTime:v.currentTime,duration:v.duration,ended:v.ended,readyState:v.readyState,error:v.error?.message});},true); });
 let sid=fs.existsSync(file('session.json'))?JSON.parse(fs.readFileSync(file('session.json'))).session_id:null;
 const get=async endpoint=>{const r=await page.request.get(base+endpoint);if(!r.ok())throw Error(endpoint+' '+r.status());return r.json()};
 const allowed=new RegExp('^/api/sessions(?:$|/[^/]+/(?:action|intent/confirm|select|player|receipt|wishes|continue|cancel)$)');
 await page.route('**/api/**',async route=>{
  const r=route.request(),url=new URL(r.url()).pathname;
  if(r.method()!=='GET'&&!allowed.test(url)){log('blocked_requests.jsonl',{method:r.method(),path:url});return route.abort();}
  if(r.method()!=='GET')log('ui_requests.jsonl',{method:r.method(),path:url,body:r.postData()});return route.continue();
 });
 page.on('response',async r=>{
  const url=new URL(r.url()).pathname;if(!url.startsWith('/api/'))return;
  try{const body=await r.json();
   if(r.request().method()!=='GET')log('ui_responses.jsonl',{path:url,status:r.status(),body});
   if(url.endsWith('/view')){
    log('player_views.jsonl',{body});
    if(body.player?.video_url&&body.player.position<body.player.lead&&!fs.existsSync(file('before_decision_lead.json'))){save('before_decision_lead.json',body);await page.screenshot({path:file('before_decision_lead.png')});}
   }
  }catch{}
 });
 await page.goto(base+'/#/home');
 await page.evaluate(id=>{localStorage.setItem('drama.mode','standard');if(id)localStorage.setItem('drama.sessionId',id)},sid);
 if(sid){await page.goto(base+'/#/player');await page.reload();}
 async function snapshot(label){
  if(!/^[a-z0-9_]+$/.test(label))throw Error('Unsafe evidence label');
  const text=await page.locator('body').innerText();await page.screenshot({path:file(label+'.png'),fullPage:true});
  const view=sid?await get('/api/sessions/'+sid+'/view'):null,state=sid?await get('/api/dev/sessions/'+sid+'/state'):null;
  save(label+'_view.json',view);save(label+'_state.json',state);save(label+'_traces.json',await get('/api/dev/traces?limit=1000'));save(label+'_usage.json',await get('/api/dev/usage-ledger?limit=2000'));fs.writeFileSync(file(label+'_visible.txt'),text);
  const media=await page.evaluate(()=>({events:window.__videoEvents||[],videos:[...document.querySelectorAll('video')].map(v=>({src:v.currentSrc,currentTime:v.currentTime,duration:v.duration,ended:v.ended,paused:v.paused,readyState:v.readyState,networkState:v.networkState,error:v.error?.message}))}));save(label+'_media.json',media);
  return {sid,text,media,player:view?.player,arc:view?.arc,known:view?.known,timed:view?.timed,pending_intent:view?.pending_intent,recommendations:view?.recommendations,ended:view?.ended,ending:view?.ending,epoch:state?.epoch,branches:state?.branches.map(b=>({id:b.id,source:b.source,status:b.status,label:b.label,outcome:b.outcome})),world:state?.world,drama:state?.drama};
 }
 let busy=false;
 const server=http.createServer(async(req,res)=>{
  if(req.method!=='POST'||req.url!=='/command'){res.writeHead(404);return res.end()}
  let raw='';for await(const chunk of req)raw+=chunk;if(busy){res.writeHead(409);return res.end('Browser command in progress')}busy=true;
  try{const q=JSON.parse(raw);log('commands.jsonl',q);
   if(q.op==='start'){
    assert(!sid,'Session exists: reuse checkpoint');const versions=(await get('/api/scenarios/'+scenario+'/versions')).items;assert.equal(versions[0].version,q.expectedVersion);
    assert(!fs.existsSync(file('start_submitted.json')),'Inspect earlier start before retry');await page.goto(base+'/#/home');
    const card=page.locator('article.story-library-card').filter({has:page.getByRole('heading',{name:'生化危机：黑雨隔离区',exact:true})});await card.getByRole('button',{name:'开始游玩',exact:true}).waitFor();save('start_submitted.json',{at:new Date().toISOString(),version:versions[0]});
    const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/sessions'&&r.request().method()==='POST');await card.getByRole('button',{name:'开始游玩',exact:true}).click();const r=await pending,body=await r.json();assert(r.ok(),JSON.stringify(body));sid=body.session_id;
    const actualState=await get('/api/dev/sessions/'+sid+'/state');
    save('session.json',{...body,scenario,expected_version:versions[0],actual_version_id:actualState.scenario_version_id});
    assert.equal(actualState.scenario_version_id,versions[0].version_id,'UI started a stale publication');
    await page.getByTestId('player-shell').waitFor();
   }else if(q.op==='action'){
    if(q.requireThree){assert.equal(await page.locator('.rec-card').count(),3);assert(await page.getByRole('textbox',{name:'描述你想做的事'}).isVisible());await snapshot('three_ready_plus_free_input');}
    await snapshot(q.label+'_before');await page.getByRole('textbox',{name:'描述你想做的事'}).fill(q.text);await page.getByRole('button',{name:'行动',exact:true}).click();
   }else if(q.op==='confirm'){await page.getByRole('button',{name:/^(按这个意思继续|确认并继续)$/}).click();
   }else if(q.op==='select'){await snapshot(q.label+'_before');const cards=page.locator('.rec-card');assert(await cards.count()>q.index);await cards.nth(q.index).click();
   }else if(q.op==='wish'){
    const toggle=page.getByRole('button',{name:'故事随身册',exact:true});if(await toggle.getAttribute('aria-expanded')!=='true')await toggle.click();await page.getByRole('button',{name:'许下或查看愿望',exact:true}).click();await page.getByLabel('我的愿望',{exact:true}).fill(q.text);
    const pending=page.waitForResponse(r=>r.url().endsWith('/wishes')&&r.request().method()==='POST');await page.getByRole('button',{name:'记录愿望',exact:true}).click();await pending;await page.screenshot({path:file('wish_hud.png'),fullPage:true});await page.getByRole('button',{name:'关闭',exact:true}).click();
   }else if(q.op==='hud'){const toggle=page.getByRole('button',{name:'故事随身册',exact:true});if(await toggle.getAttribute('aria-expanded')!=='true')await toggle.click();
   }else if(q.op==='continue'){await snapshot('ending_before_continue');await page.getByRole('button',{name:'让故事继续',exact:true}).click();
   }else if(q.op==='retry'){await page.getByRole('button',{name:'重新生成',exact:true}).first().click();
   }else if(q.op==='play'){
    if(await page.locator('video').evaluate(v=>v.paused))await page.getByRole('button',{name:'播放 / 暂停',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('video')?.ended,{},{timeout:20000});
   }else if(q.op==='home'){await page.goto(base+'/#/home');
   }else if(q.op!=='inspect')throw Error('Unknown operation');
   await page.waitForTimeout(500);const result=await snapshot(q.label||q.op);res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(result));
  }catch(e){res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:e.message}));}finally{busy=false}
 });
 server.listen(9011,'127.0.0.1',()=>console.log('Browser ready :9011; explicit start required.'));
 const close=async()=>{server.close();await browser.close();process.exit(0)};process.on('SIGTERM',close);process.on('SIGINT',close);
})();
