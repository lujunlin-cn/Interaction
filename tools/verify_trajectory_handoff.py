"""Read-only service checks plus one tiny local inference. Never media."""
import json,time,urllib.request,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];base='http://127.0.0.1:9000'
def get(path):
 with urllib.request.urlopen(base+path,timeout=15) as r:return json.load(r)
def sanitize(x):
 if isinstance(x,dict):
  return {k:('[CONFIGURED]' if v else '[UNSET]') if any(s in k.lower() for s in ['key','secret','credential','token']) else sanitize(v) for k,v in x.items()}
 if isinstance(x,list):return [sanitize(v) for v in x]
 return x
out={'health':get('/api/health'),'service':subprocess.check_output(['systemctl','--user','is-active','interaction.service'],text=True).strip(),
 'enabled':subprocess.check_output(['systemctl','--user','is-enabled','interaction.service'],text=True).strip(),
 'linger':subprocess.check_output(['loginctl','show-user','hajimi2025','-p','Linger'],text=True).strip(),
 'url':base,'port':9000,'paid_media_requests_this_check':0}
for route in ['/api/dev/generation-settings','/api/dev/profile','/api/dev/providers','/api/skills/observatory']:
 try:
  data=get(route)
  if route.endswith('observatory'):out['observatory']={'http':'PASS','top_level_keys':list(data),'metrics_entries':len(data.get('metrics',[]))}
  else:out[route]=sanitize(data)
 except Exception as e:out[route]={'error_type':type(e).__name__}
with urllib.request.urlopen(base+'/',timeout=15) as r:out['frontend']={'status':r.status,'html':b'<html' in r.read().lower()}
llm='http://127.0.0.1:8001/v1'
with urllib.request.urlopen(llm+'/models',timeout=10) as r:models=json.load(r)
model=next(m['id'] for m in models['data'] if 'Lightning' in m['id']);started=time.perf_counter()
req=urllib.request.Request(llm+'/chat/completions',data=json.dumps({'model':model,'messages':[{'role':'user','content':'请只回复 OK。'}],'max_tokens':96,'temperature':0,'chat_template_kwargs':{'enable_thinking':False}}).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=60) as r:
 answer=json.load(r);out['nemotron']={'endpoint':llm,'model':model,'status':r.status,'latency_ms':round((time.perf_counter()-started)*1000),'reply':answer['choices'][0]['message'].get('content'),'usage':answer.get('usage'),'loaded':True}
out['checked_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
(ROOT/'docs/trajectory-analysis/human_test_handoff.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+chr(10))
print(json.dumps({k:v for k,v in out.items() if not k.startswith('/api/dev/')},ensure_ascii=False,indent=2))
