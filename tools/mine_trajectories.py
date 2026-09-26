"""Read-only trajectory mining; no runtime, providers or media submission.

Run from backend: .venv/bin/python ../tools/mine_trajectories.py
Sources are content-hashed. Multiple acceptance captures are deduplicated by
domain ID, never counted as independent plays. Unknown provenance stays unknown.
"""
from __future__ import annotations
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
OUT = ROOT / 'docs/trajectory-analysis'

def clean(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if re.search(r'api.?key|authorization|credential|secret_key|access_token', k, re.I) else clean(v)) for k,v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'https?://[^\s\"<>]+', lambda m: m[0].split('?')[0], value)
        return re.sub(r'\bsk-[A-Za-z0-9_-]{16,}', '[REDACTED]', value)
    return value

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def classify(providers):
    providers = {str(x).lower() for x in providers if x and x != 'runtime'}
    mock = any('mock' in p or 'fixture' in p or 'replay' in p for p in providers)
    real = any(p in {'nemotron_local','step_37','step_5','jev','h3_max','fal_h3_max','sol_h3','stepfun','openai_compatible'} or 'step-3' in p or 'step-5' in p for p in providers)
    return 'mixed' if real and mock else 'real_provider_observed' if real else 'mock_or_fixture' if mock else 'unknown'

async def main():
    from sqlalchemy import select, text
    from app.db import SessionLocal
    from app.db_models import SessionRow, TraceSpanRow, JobRow
    OUT.mkdir(parents=True, exist_ok=True)
    sessions, spans, jobs, source_index, snapshots = {}, {}, {}, [], defaultdict(list)
    async with SessionLocal() as db:
        if db.bind.dialect.name == 'postgresql':
            await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        for row in (await db.execute(select(SessionRow))).scalars():
            sessions[row.id] = row.state
            snapshots[row.id].append({'source':'database:sessions/'+row.id, 'state':row.state})
        for row in (await db.execute(select(TraceSpanRow))).scalars():
            spans[row.id] = row.data
        for row in (await db.execute(select(JobRow))).scalars():
            jobs[row.id] = row.data
        await db.rollback()
    db_counts = {'sessions':len(sessions),'spans':len(spans),'jobs':len(jobs)}
    paths = sorted((ROOT/'docs/acceptance').rglob('*.json')) + sorted((ROOT/'docs/acceptance').rglob('*.jsonl'))
    ledger = ROOT/'backend/data/.private/usage-ledger.jsonl'
    if ledger.exists():
        paths.append(ledger)
    ledger_records = {}
    for path in paths:
        raw = path.read_bytes()
        try:
            data = [json.loads(line) for line in raw.splitlines() if line.strip()] if path.suffix == '.jsonl' else json.loads(raw)
        except (ValueError, UnicodeError):
            continue
        sid, scid, event_types, providers, times, bids = set(),set(),set(),set(),[],set()
        has_state = False
        failure_records = 0
        for obj in walk(data):
            if obj.get('last_error') or obj.get('error') or obj.get('status') in ('failed', 'FAILED', 'FAILED_RECOVERABLE'):
                failure_records += 1
            if isinstance(obj.get('session_id'),str): sid.add(obj['session_id'])
            if isinstance(obj.get('scenario_id'),str): scid.add(obj['scenario_id'])
            if isinstance(obj.get('branch_id'),str): bids.add(obj['branch_id'])
            if isinstance(obj.get('at'),(int,float)): times.append(obj['at'])
            if isinstance(obj.get('provider'),str): providers.add(obj['provider'])
            if isinstance(obj.get('selected'),str): providers.add(obj['selected'])
            if str(obj.get('id','')).startswith('sess_') and 'branches' in obj and 'world' in obj:
                sid.add(obj['id']); has_state=True
                snapshots[obj['id']].append({'source':str(path.relative_to(ROOT)), 'state':obj})
                if obj['id'] not in sessions or obj.get('updated_at',0)>sessions[obj['id']].get('updated_at',0): sessions[obj['id']]=obj
            if str(obj.get('id','')).startswith('span_') and 'input' in obj and 'output' in obj:
                spans[obj['id']]={**spans.get(obj['id'],{}),**obj};event_types.add(obj.get('name',''))
            if str(obj.get('id','')).startswith('evt_'): event_types.add(obj.get('type',''))
            if 'external_http_attempts' in obj and ('capability' in obj or 'operation' in obj or 'task' in obj):
                key=obj.get('operation_id') or obj.get('id') or hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()

                if obj.get('updated_at',obj.get('at',0)) >= ledger_records.get(key,{}).get('updated_at',0): ledger_records[key]=obj
        source_index.append({'source':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw), 'sessions':sorted(sid), 'scenarios':sorted(scid), 'branches':sorted(bids), 'timestamp_range_ms':[min(times),max(times)] if times else None,'event_types':sorted(event_types),'provenance':classify(providers),'providers':sorted(providers),'has_canonical_snapshot':has_state,'complete':False})
        source_index[-1].update(historical_failure_observed=bool(failure_records), failure_records_observed=failure_records)
    branch_sessions={b['id']:sid for sid,s in sessions.items() for b in s['branches']}
    for span in spans.values():
        if not span.get('session_id') and span.get('branch_id') in branch_sessions: span['session_id']=branch_sessions[span['branch_id']]
        if not span.get('name') and span.get('input',{}).get('role'): span['name']='provider.text';span['name_inferred_from_role']=True
    turns=[];session_index=[]
    for sid,s in sorted(sessions.items()):
        ss=[sp for sp in spans.values() if sp.get('session_id')==sid]
        providers={r.get('selected') for b in s['branches'] for r in b.get('routes',[])} | {sp.get('provider') for sp in ss}
        provenance=classify(providers)
        session_index.append({'session_id':sid,'scenario_id':s.get('scenario_id'),'scenario_version_id':s.get('scenario_version_id'),'provenance':provenance,'providers':sorted(p for p in providers if p),'branches':len(s['branches']),'player_inputs':sum(e['type']=='player_input' for e in s.get('events',[])),'created_at':s.get('created_at'),'updated_at':s.get('updated_at'),'source_count':len(snapshots[sid])})
        for b in s['branches']:
            evs=[e for e in s.get('events',[]) if e.get('branch_id')==b['id']]
            bs=[sp for sp in ss if sp.get('branch_id')==b['id']]
            inputs=[e for e in s.get('events',[]) if e['type']=='player_input' and e.get('raw_input')==(b.get('intent') or {}).get('raw_text')]
            before=[p for p in snapshots[sid] if p['state'].get('updated_at',0)<=b.get('created_at',0)]
            checkpoint=max(before,key=lambda p:p['state'].get('updated_at',0)) if before else None
            canonical=next((e for e in evs if e['type']=='branch_canonical'),None)
            selected=any(e['type'] in ('branch_selected','branch_selected_early') for e in evs)
            kind='opening' if b['source']=='opening' else 'player_turn' if b['source']=='free' or selected or b['status']=='CANONICAL' else 'speculative_branch'
            phases={e.get('extra',{}).get('status'):e['at'] for e in evs if e['type']=='branch_phase'}
            turns.append({'schema_version':'1.0.0','scenario_id':s.get('scenario_id'),'scenario_version':s.get('scenario_version_id'),'session_id':sid,'arc_id':b.get('arc_id'),'turn_id':b['id'],'record_kind':kind,'provenance':classify([r.get('selected') for r in b.get('routes',[])]) if b.get('routes') else provenance,
                'player':{'raw_input':(b.get('intent') or {}).get('raw_text') or b.get('label'),'free_input':b['source']=='free','selected_recommendation':selected,'timed_action':b['source']=='timed','input_events':[e['id'] for e in inputs]},
                'context':{'read_set':b.get('read_set',{}),'checkpoint_source':checkpoint['source'] if checkpoint else None,'checkpoint_is_exact_before':False,'current_scene':(b.get('context') or {}).get('scene'),'world_before':(b.get('read_set') or {}).get('world'),'knowledge_before':None,'drama_before':(b.get('read_set') or {}).get('drama'),'active_pressures':None},
                'intent':b.get('intent'),'jev':{'calls':[sp for sp in ss if sp.get('name')=='decision.intent' and sp.get('input',{}).get('raw_player_input')==(b.get('intent') or {}).get('raw_text')]},
                'director':{'output':b.get('director_result'),'directive':b.get('directive'),'routes':[r for r in b.get('routes',[]) if r.get('role')=='director']},
                'narrative':{'output':b.get('narrative'),'packet':b.get('packet')},
                'skills':{'triggered':(b.get('director_result') or {}).get('outcome',{}).get('skill_triggers',[]),'spans':[sp for sp in bs if sp.get('skill_id')],'considered':None},
                'state':{'proposed_patch':b.get('state_patch_proposal'),'committed_patch':canonical.get('operations') if canonical else None,'canonical_event':canonical,'canonical_after':None},
                'production':{'shots':b.get('shots',[]),'jobs':b.get('jobs',[]),'artifact':b.get('artifact'),'retry':b.get('retry',0)},
                'branch':{k:b.get(k) for k in ('id','status','source','epoch_id','created_at','ready_at','fail_stage','last_error','invalidated_reason','base_versions')},
                'player_output':{'narrative':b.get('narrative'),'subtitles':b.get('caption'),'recoverable_error':b.get('last_error')},
                'metrics':{'route_count_lower_bound':len(b.get('routes',[])),'provider_latency_ms':None,'tokens':None,'created_to_ready_ms':b['ready_at']-b['created_at'] if b.get('ready_at') else None,'created_to_canonical_ms':canonical['at']-b['created_at'] if canonical else None,'phase_timestamps':phases},
                'timeline':sorted(evs+bs,key=lambda e:e.get('at',0)),
                'missing_observability':['exact_context_before','provider_input_tokens','provider_output_tokens','considered_skills','canonical_after_per_turn','complete_provider_attempts']})
    dataset={'captured_at':datetime.now(timezone.utc).isoformat(),'start_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'db_counts':db_counts,'session_index':session_index,'turns':turns,'spans':list(spans.values()),'ledger':list(ledger_records.values())}
    # Replay source keeps published authoring and recorded state only; never DB connection details.
    replay=[{'session_id':sid,'state':s} for sid,s in sorted(sessions.items())]
    for name,data in [('dataset.json',dataset),('source_index.json',source_index),('replay_sessions.json',replay)]:
        (OUT/name).write_text(json.dumps(clean(data),ensure_ascii=False,indent=2)+'\n')
    stats={'db':db_counts,'deduplicated_sessions':len(sessions),'session_provenance':dict(Counter(x['provenance'] for x in session_index)),'branches':len(turns),'record_kinds':dict(Counter(t['record_kind'] for t in turns)),'recovered_spans':len(spans),'span_names':dict(Counter(x.get('name') for x in spans.values())),'sources':len(source_index),'ledger_records':len(ledger_records)}
    (OUT/'mining_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=='__main__': asyncio.run(main())
