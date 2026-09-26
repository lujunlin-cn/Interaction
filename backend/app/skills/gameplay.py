"""Versioned gameplay policies. Agents interpret; policies never commit state.

These contracts compose existing Jev/Director inference, without adding a model
per small function. Uncertain semantic repairs return to Director once.
"""
from __future__ import annotations
from copy import deepcopy
import json
import re
import unicodedata
from typing import Any
from pydantic import BaseModel, Field
from . import mechanic
from .registry import is_enabled

class ActionSemanticPacket(BaseModel):
    version: str = '2.0.0'
    raw_input: str
    action: str
    action_source: str = 'PLAYER_RAW'
    desire: str | None = None
    strategy: str | None = None
    route: str = 'unknown'
    confidence: float = 0.0
    impact: str = 'UNKNOWN'
    quoted_constraints: list[str] = Field(default_factory=list)
    observation: dict[str, Any] = Field(default_factory=dict)
    policy: str = ('Original and player-confirmed intent are authoritative preferences, not world facts. '
                   'Preserve targets, sequence, strategy and negative constraints. Explain any world-grounded obstruction. '
                   'Never grant an item or evidence simply because the player claims it exists.')

def understand_action(raw: str, observation: dict, confirmed_action: str = '') -> ActionSemanticPacket:
    confirmed = observation.get('desire_source') == 'PLAYER_CONFIRMED'
    action = (confirmed_action or observation.get('action') or raw) if confirmed else raw
    clauses = re.split(r'(?<=[。！？.!?；;])', action)
    constraints = [c.strip() for c in clauses if re.search(r'不|别|只|先|再|without|never|only|first|then|do not|don.t',c,re.I)]
    return ActionSemanticPacket(raw_input=raw, action=action, action_source='PLAYER_CONFIRMED' if confirmed else 'PLAYER_RAW',
        desire=observation.get('desire'), strategy=observation.get('strategy'), route=str(observation.get('route') or 'unknown'),
        confidence=max(0.0,min(1.0,float(observation.get('confidence') or 0))), impact=str(observation.get('impact') or 'UNKNOWN'),
        quoted_constraints=constraints, observation={k:v for k,v in observation.items() if k!='usage'})

# Context projection is a deterministic tool, not an extra reasoning Skill.
# Drop only known storage/presentation metadata. Unknown semantic fields survive.
CHARACTER_MEDIA_FIELDS = {'canonical_asset_id','canonical_image','canonical_front_asset_id','reference_pack',
    'standard_views','assets','outfits','poses','motions','voices','canonical_voice','alternate_voices','voice',
    'character_snapshot_id','snapshot_id','global_character_id','character_version_id','character_version',
    'version','created_at','updated_at','thumbnail','thumbnail_url','image_url','avatar','reference_assets',
    'visual_reference_assets','canonical_reference','media','asset_ids','visual_pack'}

def project_character(character: dict) -> dict:
    return {k:deepcopy(v) for k,v in character.items() if k not in CHARACTER_MEDIA_FIELDS}

def director_context(brief: dict) -> dict:
    result=deepcopy(brief)
    result['player']=project_character(result.get('player') or {})
    result['npcs']=[project_character(c) for c in result.get('npcs',[])]
    # Keep complete most recent narrative for continuity, old outcomes/evidence
    # remain verbatim; avoid sending the same beat in two renderings four times.
    beats=result.get('recent_canonical_beats',[])
    for beat in beats[:-1]: beat.pop('presented_narrative',None)
    return result

def mechanic_context(brief: dict, world: dict) -> dict:
    return {'npcs':[{'id':n.get('id'),'identity':n.get('identity')} for n in brief.get('npcs',[])],
        'relationships':deepcopy(world.get('relationships',{})), 'inventory':list(world.get('inventory',[])),
        'clues':deepcopy(world.get('clues',{})), 'location':world.get('location'),
        'locations':brief.get('locations',{})}

def choice_context(brief: dict, preferences: dict, pressures: list[dict]) -> dict:
    keys=('title','core_question','central_conflict','location','locations','inventory','clues','knowledge','relationships','phase','wishes')
    result={k:deepcopy(brief[k]) for k in keys if k in brief}
    result['location_name']=(brief.get('locations') or {}).get(brief.get('location'),brief.get('location'))
    result['recent_canonical_beats']=deepcopy(brief.get('recent_canonical_beats',[])[-2:])
    result['npcs']=[{'id':n.get('id'),'identity':n.get('identity')} for n in brief.get('npcs',[])]
    result['preferences']=deepcopy(preferences)
    result['active_pressures']=[{k:v for k,v in p.items() if k in ('id','label','kind','status','level','description','current','threshold')} for p in pressures]
    return result

def distinct_candidates(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    """Exact normalized duplicates only. Never invent actions to meet a metric."""
    seen=set();kept=[];removed=[]
    for c in candidates:
        key=''.join(x for x in unicodedata.normalize('NFKC',c.get('label','')).casefold() if x.isalnum())
        if key and key not in seen: kept.append(c);seen.add(key)
        else: removed.append({'label':c.get('label'),'reason':'empty_or_exact_duplicate'})
    return kept,removed

class ArbitrationResult(BaseModel):
    version: str = '1.0.0'
    operations: list[dict] = Field(default_factory=list)
    invocations: list[dict] = Field(default_factory=list)
    decisions: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

def arbitrate(outcome: dict, context: dict, mechanics: dict, branch_id: str, base_version: int, drama_revision: int) -> ArbitrationResult:
    """Reconcile proposals, not facts. Contradictions require Director correction.

    No semantic substitution of item IDs, no default NPC/delta, no auto-grant.
    De-duplication is safe only for identical proposals.
    """
    result=ArbitrationResult();ops=deepcopy(outcome.get('ops') or []);seen=set();targets={}
    for trigger in outcome.get('skill_triggers') or []:
        sid=trigger.get('skill','');target=trigger.get('target') or trigger.get('item') or trigger.get('clue')
        decision={'skill':sid,'target':target,'trigger':deepcopy(trigger),'status':'considered'}
        result.decisions.append(decision)
        if sid not in ('inventory','clue-system','relationship'):
            decision.update(status='rejected',reason='unknown_skill');result.errors.append('unknown mechanic skill: '+sid);continue
        if not is_enabled(sid) or not (mechanics.get(sid,{}).get('enabled',True)):
            decision.update(status='disabled',reason='skill_disabled');continue
        reason=None
        if not isinstance(target,str) or not target: reason='explicit_target_required'
        elif sid=='inventory':
            action=trigger.get('action','add')
            if action not in ('add','remove'): reason='unknown_inventory_action'
            elif str(trigger.get('stage','')).upper()=='USED' and action=='add': reason='inventory_use_cannot_acquire'
            elif action=='remove' and target not in context.get('inventory',[]): reason='cannot_remove_unowned_item'
        elif sid=='relationship':
            if target not in {n.get('id') for n in context.get('npcs',[])}: reason='unknown_relationship_target'
            elif type(trigger.get('value')) not in (int,float): reason='explicit_numeric_delta_required'
        elif sid=='clue-system':
            stages={'DISCOVERED':0,'VERIFIED':1,'USED':2}
            stage=str(trigger.get('stage') or 'DISCOVERED').upper()
            old=context.get('clues',{}).get(target)
            if stage not in stages: reason='unknown_clue_stage'
            elif old in stages and stages[stage]<stages[old]: reason='clue_lifecycle_cannot_regress'
        if reason:
            decision.update(status='rejected',reason=reason);result.errors.append(f'{sid}:{target}:{reason}');continue
        signature=json.dumps(trigger,sort_keys=True,ensure_ascii=False)
        if signature in seen:
            decision.update(status='deduplicated',reason='identical_trigger');continue
        seen.add(signature)
        target_key=(sid,target)
        # Two different proposals for the same target are ambiguous.
        if target_key in targets:
            decision.update(status='rejected',reason='conflicting_target_proposals');result.errors.append(f'{sid}:{target}:conflicting_target_proposals');continue
        targets[target_key]=signature
        invocation=mechanic.invoke(sid,trigger,context,mechanics,branch_id,base_version,drama_revision)
        if invocation:
            result.invocations.append(invocation);ops.extend(invocation['proposal']['operations'])
            decision.update(status='proposed',reason='explicit_director_proposal_validated')
        else: decision.update(status='not_applicable',reason='no_operations')
    # Multiple clue envelopes from models are transport redundancy only when
    # every entry has a typed clue operation. Never guess missing information.
    explicit={op.get('path','')[6:] for op in ops if str(op.get('path','')).startswith('clues.') and op.get('op')=='set'}
    ops=[op for op in ops if not (op.get('path') in ('clues','/clues') and op.get('op') in ('add','set')
        and isinstance(op.get('value'),list) and op['value'] and all(x in explicit for x in op['value']))]
    op_seen=set()
    for op in ops:
        signature=json.dumps(op,sort_keys=True,ensure_ascii=False)
        if signature in op_seen:
            result.decisions.append({'status':'deduplicated','reason':'identical_operation','operation':op});continue
        op_seen.add(signature);result.operations.append(op)
    return result
