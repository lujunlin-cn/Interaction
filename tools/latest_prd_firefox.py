"""Real Firefox/WebDriver acceptance on Spark (Chromium test build lacks H264).
Start: /snap/bin/firefox.geckodriver --port 4444 --host 127.0.0.1
Run from repo root with backend/.venv/bin/python tools/latest_prd_firefox.py.
No stubs: all app requests use the configured live candidate server.
"""
import base64, json, os, pathlib, time
import httpx
OUT = pathlib.Path('docs/acceptance/prd_v06_latest')
BASE = os.getenv('BASE_URL', 'http://127.0.0.1:9002')
class Browser:
    def __init__(self):
        self.http = httpx.Client(timeout=60)
        r = self.http.post('http://127.0.0.1:4444/session', json={'capabilities': {'alwaysMatch': {'browserName': 'firefox', 'moz:firefoxOptions': {'args': ['-headless']}}}})
        r.raise_for_status(); self.id = r.json()['value']['sessionId']; pathlib.Path('/tmp/interaction-active-webdriver.txt').write_text(self.id); self.base = 'http://127.0.0.1:4444/session/' + self.id
    def call(self, route, data):
        r = self.http.post(self.base + route, json=data); r.raise_for_status(); value = r.json().get('value')
        if isinstance(value, dict) and value.get('error'): raise RuntimeError(value)
        return value
    def js(self, script, *args): return self.call('/execute/sync', {'script':script, 'args': list(args)})
    def goto(self, path): self.call('/url', {'url':BASE+path})
    def wait(self, script, timeout=60):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            result=self.js(script)
            if result: return result
            time.sleep(.5)
        raise TimeoutError(script)
    def click(self, text):
        deadline=time.monotonic()+15
        element=None
        while time.monotonic()<deadline:
            element=self.js("return [...document.querySelectorAll('button')].find(x=>x.textContent.trim()===arguments[0]);",text)
            if element:break
            time.sleep(.2)
        if not element: raise ValueError('Button not found: '+text)
        self.call('/element/'+element['element-6066-11e4-a52e-4f735466cecf']+'/click',{})
    def input(self, selector, text):
        el=self.js('return document.querySelector(arguments[0])',selector)['element-6066-11e4-a52e-4f735466cecf']
        self.call('/element/'+el+'/clear',{});self.call('/element/'+el+'/value',{'text':text})
    def screenshot(self,name):
        r=self.http.get(self.base+'/screenshot').json()['value'];(OUT/(name+'.png')).write_bytes(base64.b64decode(r))
    def viewport(self,width,height):
        self.call('/window/rect',{'width':width,'height':height})
        dx,dy=self.js('return [outerWidth-innerWidth,outerHeight-innerHeight]')
        self.call('/window/rect',{'width':width+dx,'height':height+dy})
    def close(self): self.http.delete(self.base)

def run():
    sid=os.getenv('SESSION_ID') or (OUT/'live_session_id.txt').read_text().strip()
    scenario=(OUT/'live_scenario_id.txt').read_text().strip()
    report={'session_id':sid,'started_at':time.time(),'checks':[]}
    def record(name, **data):
        report['checks'].append({'name':name,'at':time.time(),**data});(OUT/'firefox_player_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(name,data.get('status',''),flush=True)
    c=httpx.Client(base_url=BASE,timeout=180);b=Browser()
    try:
        b.viewport(1920,1080);b.goto('/')
        b.js('localStorage.setItem("drama.mode","standard");localStorage.setItem("drama.sessionId",arguments[0]);localStorage.setItem("drama.editId",arguments[1]);',sid,scenario)
        b.call('/refresh',{});b.goto('/#/player')
        b.wait('return document.querySelector("video")?.readyState >= 2',600)
        b.click('播放 / 暂停');time.sleep(1)
        video=b.js('const v=document.querySelector("video");return {readyState:v.readyState,width:v.videoWidth,height:v.videoHeight,time:v.currentTime,error:v.error?.message,paused:v.paused,codec:v.canPlayType(\'video/mp4; codecs="avc1.42E01E"\')};')
        assert video['width']>0 and not video.get('error'),video
        state=c.get(f'/api/dev/sessions/{sid}/state').json();opening=next(x for x in state['branches'] if x['source']=='opening')
        assert opening['artifact'] and any(r['selected']=='h3_max' for r in opening['routes'])
        assert not any(r['selected']=='mock_video' for r in opening['routes'])
        record('Real video playback',status='PASS',video=video,opening=opening)
        b.screenshot('normal_player');b.click('沉浸全屏')
        full=b.wait('const e=document.fullscreenElement;return e && {target:e.dataset.testid,video:!!e.querySelector("video"),subtitle:!!e.querySelector(".scene-caption"),hud:!!e.querySelector(".player-hud"),agency:!!e.querySelector(".agency-layer")};')
        assert full['target']=='player-shell' and all(full[k] for k in ['video','subtitle','hud','agency'])
        b.screenshot('player_fullscreen');record('AT-84',status='PASS',fullscreen=full)
        el=b.js('return document.querySelector(".hud-toggle")')['element-6066-11e4-a52e-4f735466cecf']
        b.call('/actions',{'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','duration':100,'origin':{'element-6066-11e4-a52e-4f735466cecf':el},'x':0,'y':0}]}]})
        b.wait('return !!document.querySelector(".hud-drawer")');b.screenshot('hud_expanded')
        b.call('/element/'+el+'/click',{});b.call('/actions',{'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','duration':100,'origin':'viewport','x':700,'y':50}]}]})
        assert b.js('return !!document.querySelector(".hud-drawer")')
        b.call('/element/'+el+'/click',{});b.call('/actions',{'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','duration':100,'origin':'viewport','x':700,'y':50}]}]})
        assert not b.js('return !!document.querySelector(".hud-drawer")')
        record('AT-87',status='PASS',hover=True,pin=True,unpin=True);b.click('退出全屏')
        b.wait('return document.querySelectorAll(".rec-card").length === 3',600);v=c.get(f'/api/sessions/{sid}/view').json()
        assert v['player']['position']>=v['player']['decision_open_at'];b.screenshot('ready_recommendations')
        assert b.js('return !!(document.querySelector(".decision-layer").compareDocumentPosition(document.querySelector(".agency-layer")) & Node.DOCUMENT_POSITION_FOLLOWING)')
        record('AT-85',status='PASS',view=v)
        b.input('.free-input-row input','我敲响后门，大声表明保险调查员的身份，请林岚开门，带我进入灯塔门厅一起搜查。');b.screenshot('free_input');b.click('行动')
        deadline=time.monotonic()+600;free=None
        while time.monotonic()<deadline:
            v=c.get(f'/api/sessions/{sid}/view').json()
            if v.get('pending_intent'):
                b.screenshot('intent_echo');b.click('按这个意思继续' if v['pending_intent']['kind']=='echo' else '确认并继续')
            state=c.get(f'/api/dev/sessions/{sid}/state').json();items=[x for x in state['branches'] if x['source']=='free'];free=items[-1] if items else None
            if free and free['status'] in ('CANONICAL','FAILED'):break
            time.sleep(1)
        record('AT-86',status='PASS' if free and free['status']=='CANONICAL' else 'FAIL',free_branch=free,world=state['world'])
        (OUT/'live_play_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2));(OUT/'live_play_traces.json').write_text(json.dumps(c.get('/api/dev/traces?limit=2000').json(),ensure_ascii=False,indent=2))
        b.goto('/#/settings');b.click('开发者模式');b.goto('/#/player');b.click('Inspector');b.wait('return document.querySelector(".developer-inspector pre")?.textContent.length>100');b.screenshot('developer_inspector')
        record('Inspector',status='PASS')
    except Exception as e:
        record('failure',status='FAIL',error=repr(e));b.screenshot('firefox_failure');raise
    finally:b.close()
if __name__=='__main__':run()
