// Isolated UI regression. Mocked HTTP only; never creates a live Session.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const server=await createServer({root,configFile:false,server:{host:'127.0.0.1',port:9004,strictPort:true,hmr:false}});
await server.listen();
const browser=await chromium.launch({headless:true});
try{
 for(const unavailable of [false,true]){
  const page=await browser.newPage();
  let latest='version_old',fail=false,versionReads=0;const sessions=[];
  await page.route('**/api/**',async route=>{
   const r=route.request(),p=new URL(r.url()).pathname;
   const reply=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
   if(p==='/api/scenarios')return reply({items:[{id:'story',title:'Published Story',description:'A generic story',version:'0.2.0',status:'PUBLISHED',mechanics:{}}]});
   if(p.endsWith('/versions')){versionReads++;return reply(fail?{detail:'Unavailable'}:{items:[{version_id:latest,version:latest==='version_old'?'0.2.0':'0.3.0'}]},fail?503:200);}
   if(p==='/api/sessions'){sessions.push(r.postDataJSON());await new Promise(r=>setTimeout(r,100));return reply({session_id:'offline_session'});}
   return reply({ok:true,items:[]});
  });
  await page.goto('http://127.0.0.1:9004/#/home');
  const start=page.getByRole('button',{name:'开始游玩',exact:true});await start.waitFor();
  while(versionReads<1)await page.waitForTimeout(20);
  await page.waitForTimeout(100);latest='version_new';fail=unavailable;
  await start.dblclick();await page.waitForTimeout(500);
  assert.deepEqual(sessions,unavailable?[]:[{version_id:'version_new'}]);
  assert(versionReads>=2,'Starting must refresh the published version');
  await page.close();
 }
 console.log('PASS: refreshed publication, double click deduplication, failed refresh submits no session.');
}finally{await browser.close();await server.close()}
