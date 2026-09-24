"""AT-90: current React, recorded real H3 bytes, explicit transport faults (no mock provider)."""
import sys,json,time,httpx
import latest_prd_firefox as driver
from latest_prd_firefox import Browser,OUT
BASE='http://127.0.0.1:9004';driver.BASE=BASE
sid='acceptance_media_replay';c=httpx.Client(base_url=BASE,timeout=30);b=Browser();report={}
try:
 b.viewport(1920,1080);c.post('/acceptance/mode',json={'mode':'delay'});b.goto('/')
 b.js('localStorage.setItem("drama.mode","standard");localStorage.setItem("drama.sessionId",arguments[0])',sid);b.call('/refresh',{});b.goto('/#/player')
 b.wait('return document.querySelector("[data-media-state=LOADING]")?.textContent',30);b.screenshot('player_loading');report['loading']=b.js('return document.querySelector("[data-media-state=LOADING]").textContent')
 b.wait('return document.querySelector("video")?.readyState>=2',45)
 c.post('/acceptance/mode',json={'mode':'fail'});b.call('/refresh',{});b.wait('return document.querySelector("[data-media-state=FAILED]")?.textContent',30);b.screenshot('player_media_failed');report['failed']=b.js('return document.querySelector("[data-media-state=FAILED]").textContent')
 assert 'Pydantic' not in report['failed'] and 'provider' not in report['failed'].lower()
 c.post('/acceptance/mode',json={'mode':'pass'});b.click('重新载入');b.wait('return document.querySelector("video")?.readyState>=2',30);report['reload']=b.js('let v=document.querySelector("video");return {width:v.videoWidth,height:v.videoHeight,readyState:v.readyState,url:v.currentSrc};');assert report['reload']['width']>0
 c.post('/acceptance/mode',json={'mode':'fail'});b.call('/refresh',{});b.wait('return !!document.querySelector("[data-media-state=FAILED]")',30)
 before=c.get(f'/api/dev/sessions/{sid}/state').json()['world'];b.click('文字模式继续');b.wait('return !!document.querySelector(".text-scene")',30);after=c.get(f'/api/dev/sessions/{sid}/state').json();assert before==after['world'];report['text_continuation_world_unchanged']=True;b.screenshot('media_text_continue')
 report['status']='PASS';report['source']='isolated replay of real H3 SceneArtifact, media transport delayed/503 via tools/acceptance_media_proxy.py; no new Provider generation';(OUT/'media_state_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('AT-90 media states PASS',flush=True)
finally:c.post('/acceptance/mode',json={'mode':'pass'});b.close()
