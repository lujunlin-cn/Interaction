from app.domain.schemas import Branch, ScenePacket
from app.runtime.engine import RuntimeEngine


def test_public_character_name_is_not_itself_a_secret_but_fact_remains_blocked():
    engine = RuntimeEngine(None)
    state = engine._bootstrap('names-version', 'names-story', {
        'characters': [{'id': 'doctor', 'identity': 'Dr. Morgan Vale · physician'}],
        'drama': {'truth_model': 'fact_01：Morgan Vale ordered the delayed evacuation.'},
    })
    branch = Branch(id='names-branch', session_id=state.id, label='Look at the monitor',
                    arc_id=state.current_arc().id, base_versions=engine._branch_base_versions(state))
    branch.packet = ScenePacket(branch_id=branch.id, beat='Arrival', dramatic_function='SETUP',
                                forbidden_revelations=['fact_01'])
    assert engine._forbidden_hits(state, branch, 'Morgan answers over the radio.') == []
    assert engine._forbidden_hits(state, branch, 'Morgan Vale ordered the delayed evacuation.')
