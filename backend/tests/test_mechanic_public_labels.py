from types import SimpleNamespace as N
from app.domain.schemas import BranchStatus, OutcomeSpec, PatchOperation
from app.runtime.engine import _mechanic_labels

def branch(status, label='', evidence=None):
    return N(status=status, outcome=OutcomeSpec(title='Collected',text='Collected supplies',
        ops=[PatchOperation(op='addItem',value='supply_82')],evidence=evidence or []),
        director_result={'outcome':{'skill_triggers':[{'skill':'inventory','target':'supply_82','label':label}]}})

def test_labels_come_only_from_canonical_proposals():
    s=N(branches=[branch(BranchStatus.CANONICAL,'急救包'),branch(BranchStatus.READY,'不能显示的候选物品')])
    assert _mechanic_labels(s,'inventory') == {'supply_82':'急救包'}

def test_legacy_labels_use_recorded_evidence_without_guessing_translation():
    s=N(branches=[branch(BranchStatus.CANONICAL,evidence=['在值班室获得急救包和门禁卡'])])
    assert _mechanic_labels(s,'inventory') == {'supply_82':'在值班室获得急救包和门禁卡'}

def test_failed_proposal_cannot_expose_labels():
    assert _mechanic_labels(N(branches=[branch(BranchStatus.FAILED,'不可获得的物品')]),'inventory') == {}
