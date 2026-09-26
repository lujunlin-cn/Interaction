"""Read-only trajectory benchmark contract tests.

The benchmark is intentionally kept outside the live runtime.  These tests
exercise its typed-envelope validation and aggregation with a tiny synthetic
corpus so the full historical JSON is not parsed during every backend test.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "trajectory_replay_benchmark.py"
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("trajectory_replay_benchmark", MODULE_PATH)
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


def _turn(turn_id: str, *, provenance: str = "real_provider_observed", free: bool = True) -> dict:
    return {
        "schema_version": "1.0.0",
        "scenario_id": "scenario",
        "scenario_version": "version",
        "session_id": "session",
        "arc_id": "arc",
        "turn_id": turn_id,
        "record_kind": "player_turn",
        "provenance": provenance,
        "player": {"raw_input": "look", "free_input": free},
        "context": {},
        "intent": None,
        "jev": {},
        "director": {},
        "narrative": {},
        "skills": {"triggered": [{"skill": "clue-system"}]},
        "state": {"proposed_patch": {"operations": []}},
        "production": {"jobs": []},
        "branch": {"status": "CANONICAL"},
        "player_output": {},
        "metrics": {"created_to_ready_ms": 20, "created_to_canonical_ms": 30},
        "timeline": [],
        "missing_observability": [],
    }


def test_load_frozen_dataset_rejects_duplicate_turn_ids(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"turns": [_turn("duplicate"), _turn("duplicate")]}, ensure_ascii=False))
    with pytest.raises(ValueError, match="duplicate turn_id"):
        benchmark.load_frozen_dataset(path)


def test_summary_marks_read_only_and_counts_free_canonical_turns(tmp_path):
    dataset = {"captured_at": "now", "start_sha": "base", "spans": []}
    first = benchmark.TrajectoryTurn.model_validate(_turn("one"))
    second = benchmark.TrajectoryTurn.model_validate(_turn("two", provenance="mock_or_fixture", free=False))
    input_path = tmp_path / "dataset.json"
    input_path.write_text(json.dumps({"turns": [_turn("one"), _turn("two", provenance="mock_or_fixture", free=False)]}))
    result = benchmark.summarize(dataset, [first, second], input_path=input_path,
                                 replay_path=tmp_path / "missing-replay.json",
                                 sessions_path=tmp_path / "missing-sessions.json")
    assert result["capture"]["turns"] == 2
    assert result["provenance"]["real_free_canonical_turns"] == 1
    assert result["observed_chain"]["skill_trigger_count"] == 2
    assert result["safety_contract"]["network_calls"] == 0
    assert result["safety_contract"]["canonical_db_writes"] == 0
