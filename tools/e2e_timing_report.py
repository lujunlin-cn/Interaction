import json,statistics
from pathlib import Path
from urllib.request import urlopen
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'docs/acceptance/biohazard_full_e2e'
def get(p):return json.load(urlopen('http://127.0.0.1:9000'+p))
def stats(xs):
 xs=[x for x in xs if x is not None]
 return dict(n=len(xs),total=round(sum(xs),3),mean=round(statistics.mean(xs),3) if xs else None,median=round(statistics.median(xs),3) if xs else None,max=round(max(xs),3) if xs else None)
def main():
 states=[get('/api/dev/sessions/'+s+'/state') for s in ['sess_00006_6051ee','sess_00006_97bc74']]
 u=get('/api/dev/usage-ledger?limit=2000')['items'];jobs=set();branches=[]
 for s in states:
  for b in s['branches']:
   ts={}
   for e in b['pipeline_events']:
    if e.get('event')=='video_submit':jobs.add(e['provider_job_id'])
    if e.get('at') and e.get('status'):ts.setdefault(e['status'],e['at'])
   t=sorted(ts.items(),key=lambda x:x[1]);ready=b.get('ready_at')
   branches.append(dict(session=s['id'],branch=b['id'],label=b['label'],status=b['status'],epoch=b.get('epoch_id'),source=b['source'],created_at=b['created_at'],ready_at=ready,ready_seconds=(ready-b['created_at'])/1000 if ready else None,phase_seconds={k:round((t[i+1][1]-v)/1000,3) for i,(k,v) in enumerate(t[:-1])}))
 media=[dict(x,wall_seconds=round((x['updated_at']-x['at'])/1000,3)) for x in u if x.get('request_id') in jobs and x['status']=='SUCCEEDED']
 imgs=[dict(x,wall_seconds=round((x['updated_at']-x['at'])/1000,3)) for x in u if x.get('task') in ('image_edit','image_generation') and x['at']>=1790336164992]
 qa={}
 for p in (E/'visual_qa').glob('*step5*.json'):
  d=json.loads(p.read_text());key=d.get('completion_id') or d.get('request_id')
  if key and d.get('elapsed_seconds'):qa[key]=dict(file=str(p.relative_to(R)),seconds=d['elapsed_seconds'])
 traces={}
 for p in E.rglob('*traces.json'):
  x=json.loads(p.read_text())
  for t in x.get('items',[]) if isinstance(x,dict) else x:
   if isinstance(t,dict) and t.get('id'):traces[t['id']]=t
 for t in get('/api/dev/traces?limit=2000')['items']:traces[t['id']]=t
 lower=min(s['created_at'] for s in states);calls=[];roles={}
 for t in traces.values():
  if t.get('name')!='provider.text' or not t.get('duration_ms') or t.get('at',0)<lower:continue
  key=t.get('input',{}).get('role','unknown')+' / '+t.get('provider','')+' / '+t.get('model','')
  roles.setdefault(key,[]).append(t['duration_ms']/1000)
  calls.append({k:t.get(k) for k in ['id','at','duration_ms','branch_id','provider','model','input','output']})
 batches=[]
 for eid in sorted({b['epoch'] for b in branches if b['epoch'] and b['source'] in ['RECOMMENDATION','TIMED']}):
  group=[b for b in branches if b['epoch']==eid];ready=[b['ready_at'] for b in group if b['ready_at']]
  batches.append(dict(epoch=eid,count=len(group),ever_ready=len(ready),wall_seconds=(max(ready)-min(b['created_at'] for b in group))/1000 if len(ready)==len(group) else None))
 for b in branches:
  commits=[t['at'] for t in traces.values() if t.get('branch_id')==b['branch'] and t.get('name')=='commit.canonical' and t.get('status')=='success']
  b['ready_to_commit_wait_seconds']=(min(commits)-b['ready_at'])/1000 if commits and b['ready_at'] else None
 summary={'4K Image HTTP':stats([x['wall_seconds'] for x in imgs]),'H3 queue/generation/poll':stats([x['wall_seconds'] for x in media]),'Step5 QA (timed calls only)':stats([x['seconds'] for x in qa.values()]),**{k:stats(v) for k,v in roles.items()}}
 d=dict(generated_at=datetime.now(timezone.utc).isoformat(),units='seconds',methodology=['Phase dwell includes scheduler/session-lock waiting.','Parallel durations must not be summed as user wait.','Historical unmeasured timestamps are unavailable,not zero.'],summary=summary,branches=branches,images=imgs,h3=media,qa=list(qa.values()))
 d.update(model_calls=calls,recommendation_batches=batches)
 (E/'phase_timings.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 rows=['# Biohazard E2E 阶段耗时','',d['generated_at'],'','真实时间戳统计；流水线阶段含调度等待，H3含排队和轮询；人工/QA/调试时间不计生成。缺失历史数据不估算。','','| 阶段 | 次数 | 总s | 平均s | 中位s | 最长s |','|---|---:|---:|---:|---:|---:|']
 for k,v in summary.items():rows.append('| '+k+' | '+' | '.join(str(v[i]) for i in ['n','total','mean','median','max'])+' |')
 rows+=['','## Scene各阶段墙钟','','| Branch | 状态 | 创建至READY | Planning | Narrative | Production | Generating | Assembling | READY后审核/调试等待 |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for b in branches:
  vals=[b['ready_seconds']]+[b['phase_seconds'].get(k) for k in ['PLANNING','NARRATIVE','PRODUCTION','GENERATING','ASSEMBLING']]+[b['ready_to_commit_wait_seconds']]
  rows.append('| '+b['branch']+' | '+b['source']+'/'+b['status']+' | '+' | '.join('未测量' if v is None else str(round(v,3)) for v in vals)+' |')
 rows+=['','FREE初次Director可能早于Branch创建；创建至READY不是完整点击到播放。Provider耗时来自独立trace，不能与阶段驻留重复相加。','','## 推荐整批READY','','| Epoch | 分支数 | 曾READY | 整批墙钟s |','|---|---:|---:|---:|']
 for e in batches:rows.append('| '+e['epoch']+' | '+str(e['count'])+' | '+str(e['ever_ready'])+' | '+str(e['wall_seconds'])+' |')
 rows+=['','逐请求明细与来源ID：docs/acceptance/biohazard_full_e2e/phase_timings.json。','']
 (R/'BIOHAZARD_FULL_E2E_TIMING.md').write_text(chr(10).join(rows)+chr(10));print(summary)
if __name__=='__main__':main()
