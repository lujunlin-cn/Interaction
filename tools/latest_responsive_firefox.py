"""Capture current React pages with a real video in Firefox, browser zoom 100%."""
import json,time,os
from latest_prd_firefox import Browser, OUT
sid=os.getenv('SESSION_ID') or (OUT/'live_session_id.txt').read_text();scenario=(OUT/'live_scenario_id.txt').read_text();b=Browser();results=[]
try:
 b.goto('/');b.js('localStorage.setItem("drama.mode","standard");localStorage.setItem("drama.sessionId",arguments[0]);localStorage.setItem("drama.editId",arguments[1])',sid,scenario)
 for width,height in [(1366,768),(1440,900),(1920,1080),(2560,1440),(3840,2160)]:
  for size in (['standard','large','xlarge'] if width==1920 else ['standard']):
   b.js('localStorage.setItem("drama.display",JSON.stringify({appearance:"light",uiSize:arguments[0],fontSize:"medium",density:"comfortable",subtitleSize:"standard",subtitlePos:"bottomInside"}))',size)
   b.call('/refresh',{});b.viewport(width,height)
   for name,route in [('home','home'),('creator','creator/drama'),('characters','characterLibrary'),('player','player'),('settings','settings')]:
    b.goto('/#/'+route);time.sleep(.7)
    if name=='player':
     b.wait('return !!document.querySelector(".free-input-row") || !!document.querySelector(".ending-panel")',30)
    m=b.js('const s=[...document.querySelectorAll("#sidebar button")].find(x=>x.textContent.includes("设置"))?.getBoundingClientRect();return {width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,zoom:visualViewport.scale,sidebar:document.querySelector("#sidebar").offsetWidth,font:getComputedStyle(document.body).fontSize,settingsVisible:!!s&&s.top>=0&&s.bottom<=innerHeight,rootZoom:getComputedStyle(document.querySelector("#root")).zoom};')
    b.screenshot(f'{name}_{width}x{height}_{size}')
    results.append({'page':name,'ui_size':size,**m,'pass':m['scrollWidth']<=m['width'] and m['settingsVisible'] and m['zoom']==1})
 (OUT/'responsive_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print('Responsive checks',sum(x['pass'] for x in results),'/',len(results),flush=True)
finally:b.close()
