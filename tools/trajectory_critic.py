"""Opt-in bounded text research. No media adapter, Player API or DB writes.

Frozen historical outputs vs current pipeline are a temporal counterfactual,
not an A/B user experiment. Critic is blinded; its labels are not world truth.
"""
from __future__ import annotations
import asyncio, hashlib, json, sys, argparse, time
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tools'))
OUT=ROOT/'docs/trajectory-analysis'
from replay_trajectories import TextOnlyRouter, frozen_state

class ChoiceRouter(TextOnlyRouter):
    async def call_decision(self,state,questions,**kwargs):
        from app.providers.real import JevDecisionProvider
        from app.domain.schemas import ProviderRouteRecord
        provider=JevDecisionProvider();response=await provider.evaluate(state,questions)
        self.calls.append({'role':'decision','model':response.model,'latency_ms':response.latency_ms,
                           'scores':response.scores,'input_chars':len(json.dumps(state,ensure_ascii=False))})
        return provider,ProviderRouteRecord(role='decision',primary='jev',selected='jev',status='AVAILABLE',model=response.model),response

async def choices():
    from app.runtime.engine import RuntimeEngine
    d=json.loads((OUT/'dataset.json').read_text());states={r['session_id']:r['state'] for r in json.loads((OUT/'replay_sessions.json').read_text())}
    ranks=[s for s in d['spans'] if s.get('name')=='decision.rank' and s.get('provider')=='jev']
    folder=OUT/'choice_replay';folder.mkdir(exist_ok=True);seen=set()
    for span in ranks:
        sid=span.get('session_id')
        if not sid or sid in seen:continue
        candidates=[t for t in d['turns'] if t['session_id']==sid and t['provenance']=='real_provider_observed']
        if not candidates:continue
        seen.add(sid)
        target=folder/(span['id']+'.json')
        if target.exists():
            if len(seen)==3:break
            continue
        t=min(candidates,key=lambda t:abs(t['branch']['created_at']-span.get('at',0)))
        router=ChoiceRouter();engine=RuntimeEngine(router);state,b=frozen_state(t,states,engine)
        before=state.model_dump(mode='json')
        old=[]
        for label in span['input']['candidates']:
            matched=next((br for br in states[sid]['branches'] if br.get('label')==label),{})
            old.append({'label':label,'summary':matched.get('summary',''),'kind':(matched.get('outcome') or {}).get('kind')})
        result={'id':span['id'],'session_id':sid,'context_reconstructed_from':t['turn_id'],
                'context_is_exact_rank_time':False,'visible_before':engine._scenario_brief(state),
                'old':old,'old_scores':span['output'].get('ranked',{}),'paid_media_requests':0}
        try:result['new']=await engine.candidate_actions(state)
        except Exception as e:result['error']=type(e).__name__+': '+str(e)[:500]
        result['calls']=router.calls;result['state_unchanged']=state.model_dump(mode='json')==before
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print('choice',sid,'recorded',len(router.calls),'text/decision calls',flush=True)
        if len(seen)==3:break

async def critique(choices_only=False):
    from app.config import settings
    from app.providers.real import OpenAICompatTextProvider
    from app.runtime.structured_output import decode_object
    from app.skills.gameplay import choice_context
    provider=OpenAICompatTextProvider('step_5',settings.step_base_url,settings.step_api_key,settings.step5_model)
    folder=OUT/('pairwise_choices' if choices_only else 'pairwise');folder.mkdir(exist_ok=True)
    rows=[];mapping=[]
    for file in sorted((OUT/'text_replay').glob('*.json'))+sorted((OUT/'choice_replay').glob('*.json')):
        if choices_only and file.parent.name!='choice_replay':continue
        obj=json.loads(file.read_text())
        if 'new' not in obj:continue
        if file.parent.name=='choice_replay':
            scores=obj['old_scores']
            # Compare equally sized Jev-selected sets, not five old candidates
            # against three new recommendations. Preserve original raw evidence.
            obj['old']=sorted(obj['old'],key=lambda c:scores.get(c['label'],0),reverse=True)[:len(obj['new'])]
        case_id='case_'+hashlib.sha256(file.stem.encode()).hexdigest()[:10]
        swap=int(hashlib.sha256((case_id+'fixed-blind-seed').encode()).hexdigest(),16)%2==1
        visible=choice_context(obj['visible_before'],{},[])
        # Include supplied world rules, not secret truth; unknown checkpoints stay unknown.
        visible['world_rules']=obj['visible_before'].get('world_rules','')
        visible['world_constraints']=obj['visible_before'].get('world_constraints','')
        def presentation(item):
            if isinstance(item,list):return item
            outcome=item.get('outcome') or {}
            return {'adjudication':{k:v for k,v in outcome.items() if k in ('title','text','ops','evidence','skill_triggers','ending')},
                    'narrative':item.get('narrative')}
        old,new=presentation(obj['old']),presentation(obj['new'])
        rows.append({'case_id':case_id,'task':'choice_set' if file.parent.name=='choice_replay' else 'free_action',
                     'player_input':obj.get('raw_input'), 'visible_context':visible,
                     'A':new if swap else old,'B':old if swap else new})
        mapping.append({'case_id':case_id,'source':str(file.relative_to(ROOT)),'new_version':'A' if swap else 'B'})
    (folder/'blind_mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    for n in range(0,len(rows),3):
        target=folder/f'batch_{n//3+1}.json'
        if target.exists():
            previous=json.loads(target.read_text())
            if 'result' in previous:continue
            archive=folder/'transport_failures';archive.mkdir(exist_ok=True)
            target.rename(archive/(target.stem+'_prior_'+str(int(time.time()))+'.json'))
        cases=rows[n:n+3]
        instruction=('你是独立的互动故事轨迹评审。A/B 匿名顺序已打乱，不知道哪版新。'
            '只比较已提供的上下文，不补全缺失事实，不偏爱长文。可读性与多样性不应掩盖玩家目标被改写或物品凭空出现。'
            'world/rules及已持有物是约束，玩家声称持有不等于已持有；有依据的受阻属于ACCEPTABLE。'
            '对每个case返回JSON {cases:[{case_id,winner:"A|B|tie|insufficient",'
            'fidelity_A:"EXACT|ACCEPTABLE|DISTORTED|OVERRIDDEN|UNKNOWN",fidelity_B:同枚举,'
            'world_consistency_A:1到5或null,world_consistency_B:同,'
            'causal_clarity_A:1到5或null,causal_clarity_B:同,'
            'mechanic_appropriateness_A:1到5或null,mechanic_appropriateness_B:同,'
            'choice_diversity_A:1到5或null,choice_diversity_B:同,'
            'knowledge_boundary_issues:[],evidence:引用确切原文并解释判定,limitations:[]}]}。'
            '任务choice_set时fidelity为UNKNOWN，评价选项策略差异、现实可执行性和目的是否基于已知信息。'
            '遇到上下文缺失写insufficient而不是杜撰。你是研究Critic，不修改运行时状态。')
        prompt=json.dumps(cases,ensure_ascii=False)
        record={'provider':'step_5','configured_model':settings.step5_model,'request_sha256':hashlib.sha256((instruction+prompt).encode()).hexdigest(),
                'anonymized_cases':cases,'judge_policy':instruction,'paid_media_requests':0}
        try:
            response=await provider.generate([{'role':'system','content':instruction},{'role':'user','content':prompt}],
                {'purpose':'trajectory_pairwise'},budget={'max_tokens':32768,'reasoning_effort':'high','timeout_seconds':300})
            record.update(model=response.model,request_id=response.request_id,latency_ms=response.latency_ms,usage=response.usage,
                          raw_response=response.content)
            record["result"]=decode_object(response.content)
        except Exception as e:record['error']=type(e).__name__+': '+str(e)[:600]
        target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print('critic',target.name,'PASS' if 'result' in record else record['error'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--choices',action='store_true');p.add_argument('--critique',action='store_true');p.add_argument('--critique-choices',action='store_true');args=p.parse_args()
    if args.choices:asyncio.run(choices())
    if args.critique:asyncio.run(critique())
    if args.critique_choices:asyncio.run(critique(True))
