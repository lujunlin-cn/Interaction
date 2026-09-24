/** Real browser acceptance. Requires the live candidate API and an authored draft.
 * npm ci --prefix frontend
 * BASE_URL=http://127.0.0.1:9002 CHROMIUM_PATH=/path/to/chrome node tools/latest_prd_browser.cjs
 * No response mocking: screenshots and records come from the React app + REST API.
 */
const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('node:fs'); const path=require('node:path');
const base=process.env.BASE_URL||'http://127.0.0.1:9002';
const out=path.resolve('docs/acceptance/prd_v06_latest');
const scenarioId=process.env.SCENARIO_ID||fs.readFileSync(path.join(out,'live_scenario_id.txt'),'utf8').trim();
const evidence={scenario_id:scenarioId,base_url:base,started_at:new Date().toISOString(),checks:[],errors:[]};
const save=()=>fs.writeFileSync(path.join(out,'live_browser_e2e.json'),JSON.stringify(evidence,null,2));
const check=(name,data)=>{evidence.checks.push({name,at:new Date().toISOString(),...data});save();console.log(name,data.status||'');};
const screenshot=async(p,name)=>p.screenshot({path:path.join(out,name+'.png'),fullPage:true});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1920,height:1080}});
 page.on('pageerror',e=>evidence.errors.push(String(e)));
 await page.addInitScript(id=>{localStorage.setItem('drama.mode','standard');localStorage.setItem('drama.editId',id)},scenarioId);
 const get=async(url)=>(await page.request.get(base+url)).json();
 await page.goto(base+'/#/creator/mechanics'); await page.getByText('你希望这个故事怎么玩？',{exact:true}).waitFor();
 let draft=await get('/api/scenarios/'+scenarioId);const proposal=draft.creator_projection['mechanics:'];
 if(!proposal?.items?.length)throw Error('No real mechanics proposal');
 const response=page.waitForResponse(r=>r.url().endsWith('/understanding/confirm'));
 await page.getByRole('button',{name:'接受已明确的理解',exact:true}).click();const accepted=await response;
 if(!accepted.ok())throw Error('Mechanic confirmation rejected: '+await accepted.text());
 draft=await accepted.json(); check('AT-82 compile',{status:'PASS',intent:draft.mechanic_authoring_intent,mechanics:draft.mechanics,timed:draft.drama.timed_interactions});
 await screenshot(page,'natural_language_mechanics');
 if((await page.locator('main').innerText()).includes('Typed Config'))throw Error('Standard config leak');
 await page.goto(base+'/#/settings');await page.getByRole('button',{name:'开发者模式',exact:true}).click();
 await page.goto(base+'/#/creator/mechanics');await page.getByText('你希望这个故事怎么玩？',{exact:true}).waitFor();await page.getByText('Skill / version / config / trigger / StatePatch',{exact:true}).first().click();await screenshot(page,'developer_mechanics');
 await page.goto(base+'/#/settings');await page.getByRole('button',{name:'标准模式',exact:true}).click();
 await page.goto(base+'/#/creator/publish');await page.getByRole('checkbox').check();
 const publishedResponse=page.waitForResponse(r=>r.url().endsWith('/publish'),{timeout:30000});
 await page.getByRole('button',{name:'发布并试玩',exact:true}).click();const pub=await publishedResponse;
 if(!pub.ok())throw Error('Publish rejected: '+await pub.text());const published=await pub.json();
 const sid=published.session_id;evidence.session_id=sid;fs.writeFileSync(path.join(out,'live_session_id.txt'),sid);check('Publish',{status:'PASS',...published});
 await page.locator('[data-media-state="GENERATING"]').waitFor({timeout:10000});await screenshot(page,'player_generating');
 const before=await get(`/api/sessions/${sid}/view`);check('Opening preparing',{status:before.player.status==='OPENING_PREPARING'?'PASS':'FAIL',view:before});
 await page.waitForFunction(()=>!!document.querySelector('video')?.getAttribute('src'),{},{timeout:300000});
 await page.locator('video').evaluate(v=>v.play().catch(()=>{}));
 await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,{},{timeout:30000});
 await screenshot(page,'normal_player');
 await page.getByRole('button',{name:'沉浸全屏',exact:true}).click();
 const full=await page.evaluate(()=>({target:document.fullscreenElement?.getAttribute('data-testid'),agency:!!document.fullscreenElement?.querySelector('[data-layer="agency"]'),hud:!!document.fullscreenElement?.querySelector('[data-layer="hud"]'),video:!!document.fullscreenElement?.querySelector('video')}));
 if(full.target!=='player-shell'||!full.agency||!full.hud)throw Error('Fullscreen lost interaction layer');
 check('AT-84 fullscreen',{status:'PASS',...full});await screenshot(page,'player_fullscreen');
 await page.getByRole('button',{name:'故事随身册'}).hover();await page.locator('.hud-drawer').waitFor();await screenshot(page,'hud_expanded');
 await page.getByRole('button',{name:'故事随身册'}).click();await page.mouse.move(1700,50);if(await page.locator('.hud-drawer').count()!==1)throw Error('HUD pin lost');
 await page.getByRole('button',{name:'故事随身册'}).click();await page.mouse.move(1700,50);if(await page.locator('.hud-drawer').count())throw Error('HUD unpin failed');
 check('AT-87 HUD',{status:'PASS',hover:true,pin:true,unpin:true});await page.getByRole('button',{name:'退出全屏'}).click();
 await page.locator('.rec-card').first().waitFor({timeout:300000});
 const ready=await get(`/api/sessions/${sid}/view`);check('AT-85 decision',{status:ready.player.position>=ready.player.decision_open_at?'PASS':'FAIL',position:ready.player.position,lead:ready.player.decision_open_at,recommendations:ready.recommendations});await screenshot(page,'ready_recommendations');
 const order=await page.evaluate(()=>document.querySelector('[data-layer="decision"]').compareDocumentPosition(document.querySelector('[data-layer="agency"]')));if(!(order&4))throw Error('Agency before decisions');
 await page.getByLabel('描述你想做的事').fill('我绕到灯塔背面查看备用入口');await screenshot(page,'free_input');
 const actionResponse=page.waitForResponse(r=>r.url().endsWith('/action'),{timeout:180000});await page.getByRole('button',{name:'行动',exact:true}).click();const action=await(await actionResponse).json();check('AT-86 Free Input',{status:'TRIGGERED',response:action});
 if(['INTENT_ECHO','CLARIFICATION_REQUIRED'].includes(action.status)){
   await page.getByRole('button',{name:/按这个意思继续|确认并继续/}).click();
 }
 const pollUntil=async(fn,timeout=300000)=>{const start=Date.now();while(Date.now()-start<timeout){const state=await get(`/api/dev/sessions/${sid}/state`);if(fn(state))return state;await page.waitForTimeout(1000)}throw Error('Runtime completion timeout')};
 const state=await pollUntil(s=>s.branches.some(b=>b.source==='free'&&['CANONICAL','FAILED'].includes(b.status)));
 const free=state.branches.filter(b=>b.source==='free').at(-1);check('FREE canonical',{status:free.status==='CANONICAL'?'PASS':'FAIL',branch:free,world:state.world});
 const traces=await get('/api/dev/traces?limit=2000');fs.writeFileSync(path.join(out,'live_play_traces.json'),JSON.stringify(traces,null,2));fs.writeFileSync(path.join(out,'live_play_state.json'),JSON.stringify(state,null,2));
 await page.goto(base+'/#/settings');await page.getByRole('button',{name:'开发者模式',exact:true}).click();await page.goto(base+'/#/player');await page.getByRole('button',{name:'Inspector',exact:true}).click();await page.locator('.developer-inspector pre').waitFor();await screenshot(page,'developer_inspector');
 check('Browser',{status:evidence.errors.length?'FAIL':'PASS',errors:evidence.errors});await browser.close();
})().catch(e=>{evidence.failure=String(e);save();console.error(e);process.exit(1)});
