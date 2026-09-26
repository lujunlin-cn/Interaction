// Isolated static build and API fixtures: no live state/provider requests.
const {chromium,firefox}=require('../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert').strict;
const dist=path.resolve(__dirname,'../frontend/dist'),out=path.resolve(__dirname,'../docs/acceptance/branch_merge_20260926');
const server=http.createServer((req,res)=>{
 const pathname=new URL(req.url,'http://localhost').pathname;
 const file=path.join(dist,pathname==='/'?'index.html':pathname);
 if(!file.startsWith(dist+path.sep)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');fs.createReadStream(file).pipe(res);
});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 let browser;try{browser=await chromium.launch({headless:true});}catch{browser=await firefox.launch({headless:true});}
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{localStorage.setItem('drama.mode','player');localStorage.setItem('drama.sessionId','merge-fixture');});
 let view={session_id:'merge-fixture',scenario:{title:'合并回归',player_identity:'调查员'},arc:{seq:1,total:1},
 player:{status:'OPENING_PREPARING',scene_title:'第一幕',scene_text:'',caption:'',video_url:'',duration:8,lead:5,position:0},
 opening:{location_line:'港口 · 雨夜',premise_lines:['暴雨封住了通往灯塔的道路。'],identity_line:'你是一名调查员。',hook_line:'失踪的人在哪里？',accent:'#e2d5a7'},
 recommendations:[],generating:[],known:{inventory:[],relationships:[],clues:[],knowledge:[]},
 messages:[],wishes:[],hint_chips:[],ended:false,pending_intent:null,selected:null,timed:null};
 await page.route('**/api/**',async route=>{
 const req=route.request(),p=new URL(req.url()).pathname;
 let result={items:[]};
 if(p.endsWith('/view'))result=view;
 else if(req.method()!=='GET')result={status:'OK'};
 await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)});
 });
 // Hold a synthetic video request: dispatch media lifecycle events, do not decode or generate media.
 await page.route('**/fixture.mp4',()=>{});
 try{
  await page.goto('http://127.0.0.1:'+server.address().port+'/#/player');
  await page.getByTestId('opening-crawl').waitFor();
  await page.screenshot({path:path.join(out,'opening.png'),fullPage:true});
  await page.getByRole('button',{name:'跳过前情提要'}).click();
  assert.equal(await page.getByTestId('opening-crawl').count(),0);
  view={...view,player:{...view.player,status:'GENERATING_NEXT',scene_text:'上一幕'},selected:{status:'CANONICAL',label:'上一幕'},
   pending_effects:['你靠近门边，检查锁孔。','走廊里传来轻微响声。'],pending_phase:'GENERATING',pending_label:'检查门锁',action_pending:true};
  await page.getByTestId('action-sequence').waitFor();
  assert((await page.getByTestId('action-sequence').innerText()).includes('你靠近门边'));
  assert.equal(await page.getByRole('progressbar').getAttribute('aria-valuenow'),'3');
  await page.screenshot({path:path.join(out,'waiting.png'),fullPage:true});
  view={...view,pending_effects:[],pending_phase:'',pending_label:'',action_pending:false,
   selected:null,player:{...view.player,status:'PLAYING',video_url:'/fixture.mp4'}};
  await page.locator('video').waitFor();
  await page.locator('video').dispatchEvent('playing');
  await page.locator('video').dispatchEvent('waiting');
  await page.locator('.buffering-badge').waitFor();
  assert.equal(await page.locator('.media-status').count(),0);
  assert.equal(await page.getByTestId('action-sequence').count(),0);
  await page.screenshot({path:path.join(out,'buffering.png'),fullPage:true});
  await page.locator('video').dispatchEvent('playing');
  await page.waitForFunction(()=>!document.querySelector('.buffering-badge'));
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({status:'PASS',scope:'isolated browser fixtures and synthetic media events',checks:['opening crawl and skip','pending text and actual phase','terminal text disappears','buffering after first frame keeps stage visible','playback recovery'],errors,live_writes:0,paid_media_requests:0},null,2));
  console.log('PASS: merged opening / waiting / buffering UI contracts');
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);server.close();process.exit(1);});
