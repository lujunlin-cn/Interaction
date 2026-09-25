from types import SimpleNamespace

from app.domain.schemas import Branch, BranchSource, BranchStatus, RecommendationEpoch, SceneArtifact
from app.runtime.engine import RuntimeEngine


def decision():
    engine = RuntimeEngine(SimpleNamespace())
    state = engine._bootstrap('v', 's', {'world': {'locations': 'hall｜大厅'}})
    branch = Branch(id='b', session_id=state.id, arc_id=state.current_arc().id,
                    source=BranchSource.RECOMMENDATION, status=BranchStatus.READY,
                    base_versions=engine._branch_base_versions(state),
                    fingerprint=engine.compute_fingerprint(state), expires_at=1,
                    artifact=SceneArtifact(id='a', branch_id='b', quality_status='READY'))
    state.branches.append(branch)
    state.epoch = RecommendationEpoch(id='e', k=1, target_k=1, branch_ids=['b'],
                                      ready_ids=['b'], published=True, status='READY')
    return engine, state, branch


def test_current_untimed_decision_does_not_expire_while_player_thinks():
    engine, state, branch = decision()
    assert engine.valid_branch(state, branch)


def test_detached_cached_branch_still_expires():
    engine, state, branch = decision()
    state.epoch = None
    assert not engine.valid_branch(state, branch)


def test_active_decision_never_bypasses_fingerprint_or_media_validation():
    engine, state, branch = decision()
    branch.fingerprint = 'stale'
    assert not engine.valid_branch(state, branch)
    branch.fingerprint = engine.compute_fingerprint(state)
    branch.artifact.quality_status = 'FAILED'
    assert not engine.valid_branch(state, branch)
