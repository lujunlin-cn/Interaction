import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('visual_qa_tool', Path(__file__).resolve().parents[2] / 'tools/visual_qa.py')
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def review():
    return {'scene_semantics_match': '0.45', 'character_identity_consistent': True,
            'multi_character_identity_swap': False, 'motion_coherence': '0.82',
            'shot_continuity': '0.80', 'story_action_visible': False,
            'major_visual_artifact': False, 'issues': ['Required actors are absent'],
            'recommendation': 'retry'}


def test_flat_numeric_contract_preserves_major_failure_judgment():
    raw = review()
    normalized = qa.normalize_review(raw, 'video')
    qa.validate_review(normalized, 'video', [])
    assert normalized['qa']['scene_semantics_match'] == .45
    assert normalized['qa']['recommendation'] == 'retry'
    assert normalized['qa']['story_action_visible'] is False
    assert raw['scene_semantics_match'] == '0.45'


def test_ambiguous_flags_and_invalid_scores_still_fail():
    for field, value in [('character_identity_consistent', 'probably'), ('motion_coherence', '1.8')]:
        raw = review()
        raw[field] = value
        with pytest.raises(ValueError):
            qa.validate_review(qa.normalize_review(raw, 'video'), 'video', [])
