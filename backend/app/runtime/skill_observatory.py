"""Bounded, honest observed metrics. Proposals are not canonical commits."""
from collections import defaultdict

def summarize(spans: list[dict]) -> dict:
    unique={s['id']:s for s in spans}
    grouped=defaultdict(list)
    commits={s.get('branch_id') for s in unique.values() if s.get('name')=='commit.canonical' and s.get('status')=='success'}
    chains=defaultdict(list)
    for span in sorted(unique.values(),key=lambda s:s.get('at',0)):
        skill=span.get('skill_id')
        if not skill and span.get('name','').startswith('skill.'):
            skill=span['name'][6:]
        if not skill or skill=='toggle': continue
        grouped[skill].append(span)
        if span.get('branch_id'): chains[span['branch_id']].append(span)
    rows=[]
    for skill, calls in grouped.items():
        timed=[s['duration_ms'] for s in calls if s.get('duration_ms',0)>0]
        proposals=[s for s in calls if s.get('output',{}).get('proposal')]
        committed=sum(s.get('branch_id') in commits for s in proposals)
        rows.append({'skill_id':skill,'invocations':len(calls),'success':sum(s.get('status')=='success' for s in calls),
            'failure':sum(s.get('status') in ('failed','rejected') for s in calls),'fallback':sum(s.get('status')=='fallback' for s in calls),
            'latency_samples':len(timed),'average_latency_ms':sum(timed)/len(timed) if timed else None,
            'proposal_count':len(proposals),'proposals_in_committed_branches':committed,
            'proposal_acceptance_rate':committed/len(proposals) if proposals else None,
            'last_triggered':max(s.get('at',0) for s in calls),'latest':calls[-5:],
            'trigger_precision':None,'trigger_recall':None,'input_tokens':None,'output_tokens':None})
    return {'window':'latest 5000 persisted spans plus process recent; not lifetime statistics',
        'metrics':rows, 'chains':[{'branch_id':k,'calls':v} for k,v in list(chains.items())[-20:]],
        'missing_metrics':['trigger_precision/recall need independent labels','skill token attribution unavailable for shared model calls'],
        'note':'Success = capability returned. Proposal acceptance = linked canonical branch in this window; uncommitted is not necessarily rejected.'}
