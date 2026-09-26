"""Build a read-only benchmark from the frozen trajectory corpus.

This command deliberately does not import the runtime, open the application
database, call a provider, or submit media.  It consumes the immutable files
created by :mod:`mine_trajectories` and the already completed offline replay
receipts.  This makes it safe to run while the live service is serving manual
tests.

Usage (from the repository root)::

    python tools/trajectory_replay_benchmark.py
    python tools/trajectory_replay_benchmark.py --output /tmp/benchmark.json

The output is a compact benchmark receipt.  Raw player text and model output
are intentionally omitted; those remain in the frozen dataset and existing
replay receipts, subject to their provenance and redaction rules.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable

try:  # Running as ``python tools/...`` from the repository root.
    from trajectory_schema import TrajectoryTurn
except ModuleNotFoundError:  # Running through an import from another cwd.
    from tools.trajectory_schema import TrajectoryTurn


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "trajectory-analysis" / "dataset.json"
DEFAULT_REPLAY = ROOT / "docs" / "trajectory-analysis" / "replay_results.json"
DEFAULT_SESSIONS = ROOT / "docs" / "trajectory-analysis" / "replay_sessions.json"
DEFAULT_CURRENT_CAPTURE = ROOT / "docs" / "trajectory-analysis" / "current_capture_20260926" / "capture_metadata.json"
# Keep the current verification receipt separate from the frozen benchmark
# corpus.  The date is deliberate: a new capture must never silently rewrite
# the historical result used by the reports.
DEFAULT_OUTPUT = ROOT / "docs" / "trajectory-analysis" / "current_capture_20260926" / "replay_benchmark.json"


@dataclass(frozen=True)
class FrozenPaths:
    """Hashes of read-only inputs used by a benchmark run."""

    dataset_sha256: str
    replay_sessions_sha256: str | None
    replay_results_sha256: str | None


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _median(values: Iterable[int | float]) -> float | None:
    values = sorted(float(value) for value in values if isinstance(value, (int, float)) and value > 0)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def load_frozen_dataset(path: Path = DEFAULT_INPUT) -> tuple[dict[str, Any], list[TrajectoryTurn]]:
    """Load and strictly validate the normalized trajectory corpus.

    Validation happens before any aggregate is computed.  Duplicate turn IDs
    are rejected because they make replay comparisons ambiguous.  The source
    JSON object is returned as well so callers can inspect capture metadata
    without losing fields that are outside the typed envelope.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    turns_raw = payload.get("turns")
    if not isinstance(turns_raw, list):
        raise ValueError(f"{path} does not contain a turns list")
    turns = [TrajectoryTurn.model_validate(row) for row in turns_raw]
    ids = [turn.turn_id for turn in turns]
    duplicates = sorted(turn_id for turn_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate turn_id values: {', '.join(duplicates[:5])}")
    return payload, turns


def _count_media_jobs(turn: TrajectoryTurn) -> int:
    jobs = turn.production.get("jobs")
    return len(jobs) if isinstance(jobs, list) else 0


def _duration_seconds(job: Any) -> float | None:
    if not isinstance(job, dict):
        return None
    for key in ("requested_duration_seconds", "duration_seconds", "duration"):
        value = job.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _load_current_capture(path: Path) -> dict[str, Any] | None:
    """Read an optional point-in-time live inventory, never the live DB."""
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    db = value.get("db")
    if not isinstance(db, dict):
        return {"capture_id": value.get("capture_id"), "captured_at": value.get("captured_at")}
    # Keep only numeric, aggregate fields.  Per-session state and credentials
    # are intentionally never copied into the benchmark receipt.
    return {
        "capture_id": value.get("capture_id"),
        "captured_at": value.get("captured_at"),
        "repository_head": value.get("repository_head"),
        "db_counts": {
            key: db.get(key)
            for key in ("sessions", "spans", "jobs", "branches", "player_input_events")
            if isinstance(db.get(key), int)
        },
        "branch_status_counts": db.get("branch_status_counts", {}),
        "session_provenance": db.get("session_provenance", {}),
        "read_only_inventory": True,
    }


def summarize(
    payload: dict[str, Any],
    turns: list[TrajectoryTurn],
    *,
    input_path: Path = DEFAULT_INPUT,
    replay_path: Path = DEFAULT_REPLAY,
    sessions_path: Path = DEFAULT_SESSIONS,
    current_capture_path: Path = DEFAULT_CURRENT_CAPTURE,
) -> dict[str, Any]:
    """Return compact, provenance-aware metrics from frozen records."""

    provenance = Counter(turn.provenance for turn in turns)
    kinds = Counter(turn.record_kind for turn in turns)
    statuses = Counter((turn.branch.get("status") or "UNKNOWN") for turn in turns)
    real = [turn for turn in turns if turn.provenance == "real_provider_observed"]
    acted = [turn for turn in real if turn.record_kind == "player_turn"]
    free = [turn for turn in acted if turn.player.get("free_input")]
    canonical_free = [turn for turn in free if turn.branch.get("status") == "CANONICAL"]
    span_names = Counter()
    providers = Counter()
    for span in payload.get("spans", []):
        if isinstance(span, dict):
            if span.get("name"):
                span_names[span["name"]] += 1
            if span.get("provider"):
                providers[span["provider"]] += 1

    media_jobs = sum(_count_media_jobs(turn) for turn in turns)
    media_seconds = [
        duration
        for turn in turns
        for job in (turn.production.get("jobs") or [])
        for duration in [_duration_seconds(job)]
        if duration is not None
    ]
    ready_ms = [turn.metrics.get("created_to_ready_ms") for turn in real]
    canonical_ms = [turn.metrics.get("created_to_canonical_ms") for turn in real]
    missing = Counter(field for turn in turns for field in turn.missing_observability)

    saved_replay: dict[str, Any] | None = None
    if replay_path.exists():
        try:
            candidate = json.loads(replay_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                summary = candidate.get("summary")
                if isinstance(summary, dict):
                    saved_replay = {
                        "baseline_sha": summary.get("baseline_sha"),
                        "historical_records": summary.get("historical_records"),
                        "outcomes": summary.get("outcomes", {}),
                        "policy_outcomes_available": summary.get("policy_outcomes_available"),
                        "old_context_chars": summary.get("old_context_chars"),
                        "new_context_chars": summary.get("new_context_chars"),
                        "new_paid_media_requests": summary.get("new_paid_media_requests"),
                    }
        except (OSError, ValueError, TypeError):
            saved_replay = None

    source_paths = FrozenPaths(
        dataset_sha256=_sha256(input_path) or "",
        replay_sessions_sha256=_sha256(sessions_path),
        replay_results_sha256=_sha256(replay_path),
    )
    return {
        "schema": "trajectory-replay-benchmark/1.0",
        "repository_sha": _repo_sha(),
        "capture": {
            "captured_at": payload.get("captured_at"),
            "dataset_start_sha": payload.get("start_sha"),
            "input": str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path),
            "turns": len(turns),
            "sessions": len({turn.session_id for turn in turns}),
        },
        "provenance": {
            "turns_by_provenance": dict(sorted(provenance.items())),
            "turns_by_kind": dict(sorted(kinds.items())),
            "branches_by_status": dict(sorted(statuses.items())),
            "real_provider_turns": len(real),
            "real_provider_acted_turns": len(acted),
            "real_free_turns": len(free),
            "real_free_canonical_turns": len(canonical_free),
        },
        "observed_chain": {
            "span_count": len(payload.get("spans", [])),
            "span_names": dict(sorted(span_names.items())),
            "providers": dict(sorted(providers.items())),
            "skill_trigger_count": sum(len(turn.skills.get("triggered") or []) for turn in turns),
            "state_proposal_count": sum(bool(turn.state.get("proposed_patch")) for turn in turns),
            "media_job_records": media_jobs,
            "requested_media_seconds_observed": sum(media_seconds) if media_seconds else 0,
            "ready_latency_median_ms": _median(ready_ms),
            "canonical_latency_median_ms": _median(canonical_ms),
        },
        "observability": {
            "missing_fields": dict(sorted(missing.items())),
            "records_with_missing_observability": sum(bool(turn.missing_observability) for turn in turns),
        },
        "saved_offline_replay": saved_replay,
        "current_capture_inventory": _load_current_capture(current_capture_path),
        "safety_contract": {
            "read_only_sources": True,
            "network_calls": 0,
            "image_requests": 0,
            "video_requests": 0,
            "canonical_db_writes": 0,
            "uses_saved_replay_receipts_only": True,
            "frozen_source_hashes": asdict(source_paths),
        },
    }


def run(
    *, input_path: Path = DEFAULT_INPUT, replay_path: Path = DEFAULT_REPLAY,
    sessions_path: Path = DEFAULT_SESSIONS, output_path: Path = DEFAULT_OUTPUT,
    current_capture_path: Path = DEFAULT_CURRENT_CAPTURE,
) -> dict[str, Any]:
    before = FrozenPaths(_sha256(input_path) or "", _sha256(sessions_path), _sha256(replay_path))
    payload, turns = load_frozen_dataset(input_path)
    result = summarize(payload, turns, input_path=input_path, replay_path=replay_path,
                       sessions_path=sessions_path, current_capture_path=current_capture_path)
    after = FrozenPaths(_sha256(input_path) or "", _sha256(sessions_path), _sha256(replay_path))
    result["safety_contract"]["sources_unchanged"] = before == after
    if before != after:
        raise RuntimeError("frozen replay sources changed during benchmark")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--replay-results", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--replay-sessions", type=Path, default=DEFAULT_SESSIONS)
    parser.add_argument("--current-capture", type=Path, default=DEFAULT_CURRENT_CAPTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(input_path=args.input, replay_path=args.replay_results,
                 sessions_path=args.replay_sessions, output_path=args.output,
                 current_capture_path=args.current_capture)
    print(json.dumps({
        "schema": result["schema"],
        "turns": result["capture"]["turns"],
        "sessions": result["capture"]["sessions"],
        "real_provider_turns": result["provenance"]["real_provider_turns"],
        "media_requests": result["safety_contract"]["video_requests"] + result["safety_contract"]["image_requests"],
        "sources_unchanged": result["safety_contract"]["sources_unchanged"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
