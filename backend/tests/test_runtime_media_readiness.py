"""Production readiness regressions using text/video HTTP-free doubles."""
import asyncio
import json
from types import SimpleNamespace

import pytest


def fixture_engine(monkeypatch, source="recommendation", ending=None):
    from app.config import settings
    from app.domain.schemas import Branch, BranchSource, OutcomeSpec, ProviderRouteRecord
    from app.runtime.engine import RuntimeEngine
    monkeypatch.setattr(settings, "provider_mode", "live")
    monkeypatch.setattr(settings, "shots_per_branch", 1)
    monkeypatch.setattr(settings, "developer_test_override_enabled", False)
    monkeypatch.setattr(settings, "mock_shot_duration", 5)
    monkeypatch.setattr(settings, "opening_shot_duration", 8)
    monkeypatch.setattr(settings, "ending_shot_duration", 9)
    monkeypatch.setattr(settings, "max_video_shot_duration", 10)
    engine = RuntimeEngine(None)
    state = engine._bootstrap("audit-v", "audit-s", {"title": "Audit story", "characters": [
        {"id": name, "identity": name} for name in ("alpha", "beta", "gamma")]})
    branch = Branch(id="audit-b", session_id=state.id, arc_id=state.current_arc().id,
                    base_versions=engine._branch_base_versions(state),
                    source=BranchSource(source), label="Inspect", narrative="Three distinct people inspect a locked room.",
                    outcome=OutcomeSpec(title="Inspect", text="Inspect room", ending=ending))
    state.branches.append(branch)
    engine.sessions[state.id] = state
    for name in ("alpha", "beta", "gamma"):
        for role in ("front", "three_quarter", "side", "full_front"):
            state.asset_manifest.append({"id": f"{name}-{role}", "entity": name, "role": role,
                                         "path": f"https://example.invalid/{name}/{role}.png", "type": "image"})
    route = ProviderRouteRecord(role="production", primary="nemotron_local", selected="nemotron_local", status="success")
    return engine, state, branch, route


def test_opening_calls_director_and_retains_authoritative_no_state_change(monkeypatch):
    engine, state, branch, route = fixture_engine(monkeypatch, "opening")
    calls = []

    async def director(messages, mechanics, session_id, branch_id):
        calls.append(messages)
        return {"outcome": {"title": "A real model opening", "text": "The partner enters through a flickering door.",
                             "ops": [], "evidence": [], "skill_triggers": [], "ending": None},
                "directive": {"primary_function": "ESTABLISH_OPENING"}}, route

    monkeypatch.setattr(engine, "_director_output", director)
    before = state.world.model_dump()
    asyncio.run(engine._plan_branch(state, branch))
    assert len(calls) == 1
    assert branch.outcome.title == "A real model opening"
    assert state.world.model_dump() == before
    assert branch.routes == [route]
    assert branch.outcome.ops == []


def test_opening_cannot_commit_director_invented_state(monkeypatch):
    from app.runtime.engine import EngineError
    engine, state, branch, route = fixture_engine(monkeypatch, "opening")

    async def director(*args):
        return {"outcome": {"title": "Invalid", "text": "Invalid", "ops": [{"op": "addItem", "value": "key"}]}, "directive": {}}, route

    monkeypatch.setattr(engine, "_director_output", director)
    with pytest.raises(EngineError, match="unauthorized state"):
        asyncio.run(engine._plan_branch(state, branch))
    assert state.world.inventory == []


@pytest.mark.parametrize("source,ending,proposed,expected", [
    ("opening", None, 5, 8), ("opening", None, 12, 10),
    ("recommendation", "escape", 4, 8), ("free", None, 15, 10),
    ("recommendation", None, 5, 5),
    ("opening", None, 8.5, 8), ("free", None, 5.75, 5),
])
def test_duration_policy_and_cast_references(monkeypatch, source, ending, proposed, expected):
    from app.providers.base import TextResponse
    engine, state, branch, route = fixture_engine(monkeypatch, source, ending)

    async def text(*args, **kwargs):
        return None, route, TextResponse(content=json.dumps({"shots": [{
            "title": "Inspect", "prompt": "A scene with two people", "duration": proposed,
            "cast": ["alpha", "beta"]}]}))

    engine.router = SimpleNamespace(call_text=text)
    asyncio.run(engine._shoot_branch(state, branch))
    assert len(branch.shots) == 1
    shot = branch.shots[0]
    assert shot.duration == expected
    assert shot.params["cast"] == ["alpha", "beta"]
    assert {ref["entity"] for ref in shot.references} == {"alpha", "beta"}
    assert "Image 1: alpha" in shot.prompt
    assert "Image 2: beta" in shot.prompt


def test_extra_shots_rejected_before_video_submit(monkeypatch):
    from app.providers.base import TextResponse
    from app.runtime.engine import EngineError
    engine, state, branch, route = fixture_engine(monkeypatch)

    async def text(*args, **kwargs):
        return None, route, TextResponse(content=json.dumps({"shots": [{"prompt": "scene", "duration": 5, "cast": []}] * 3}))

    engine.router = SimpleNamespace(call_text=text)
    with pytest.raises(EngineError, match="shot count"):
        asyncio.run(engine._shoot_branch(state, branch))
    assert branch.jobs == [] and branch.shots == []


def test_three_actor_references_balanced_and_audio_not_starved(monkeypatch):
    engine, state, branch, route = fixture_engine(monkeypatch)
    for name in ("alpha", "beta", "gamma"):
        state.asset_manifest.append({"id": f"{name}-voice", "entity": name, "role": "voice", "path": f"https://example.invalid/{name}.wav"})
    refs = engine._bound_references(state, ["alpha", "beta", "gamma"])
    images = [ref for ref in refs if ref["type"] == "image"]
    assert len(images) == 9
    assert [ref["entity"] for ref in images[:3]] == ["alpha", "beta", "gamma"]
    assert all(sum(ref["entity"] == name for ref in images) == 3 for name in ("alpha", "beta", "gamma"))
    assert len([ref for ref in refs if ref["type"] == "audio"]) == 3


def test_reference_mixed_cap_and_url_deduplication_match_adapter(monkeypatch):
    from app.providers.real import FalH3MaxProvider
    engine, state, branch, route = fixture_engine(monkeypatch)
    # A duplicated role pointing at the same image must not shift Image N.
    state.asset_manifest.insert(1, {**state.asset_manifest[0], "id": "duplicate-role", "role": "wardrobe"})
    for name in ("alpha", "beta", "gamma"):
        for kind, role, suffix in (("audio", "voice", "wav"), ("video", "motion", "mp4")):
            state.asset_manifest.append({"id": f"{name}-{role}", "entity": name, "role": role,
                "type": kind, "path": f"https://example.invalid/{name}.{suffix}"})
    refs = engine._bound_references(state, ["alpha", "beta", "gamma"])
    adapted = FalH3MaxProvider(api_key="offline")._adapt_references({"references": refs})
    assert len(refs) == 12
    assert len(adapted["reference_image_urls"]) == 9
    assert len(adapted["reference_audio_urls"]) + len(adapted["reference_video_urls"]) == 3
    assert adapted["reference_image_urls"] == [ref["path"] for ref in refs if ref["type"] == "image"]
    assert len(set(adapted["reference_image_urls"])) == 9


def test_cast_capacity_failure_stops_before_paid_submit(monkeypatch):
    from app.config import settings
    from app.providers.base import TextResponse
    from app.runtime.engine import EngineError
    engine, state, branch, route = fixture_engine(monkeypatch)
    monkeypatch.setattr(settings, "developer_test_override_enabled", True)
    monkeypatch.setattr(settings, "developer_test_max_shots", 1)
    monkeypatch.setattr(settings, "max_test_reference_images", 2)

    async def text(*args, **kwargs):
        return None, route, TextResponse(content=json.dumps({"shots": [{"prompt": "Three people", "duration": 5,
            "cast": ["alpha", "beta", "gamma"]}]}))

    engine.router = SimpleNamespace(call_text=text)
    with pytest.raises(EngineError, match="no image reference"):
        asyncio.run(engine._shoot_branch(state, branch))
    assert branch.jobs == []


def test_media_submit_uses_each_shot_refs_and_duplicate_submit_is_rejected(monkeypatch):
    from app.domain.schemas import RuntimeProfile, ShotPlan
    from app.providers.base import VideoJobHandle, VideoJobResult
    from app.providers.router import ProviderError
    engine, state, branch, route = fixture_engine(monkeypatch)
    selected = engine._bound_references(state, ["gamma"])
    branch.shots = [ShotPlan(id="shot-1", index=1, duration=5, references=selected, prompt="One person", params={"cast": ["gamma"]})]
    branch.references = engine._bound_references(state, ["alpha", "beta", "gamma"])
    calls = []

    class Provider:
        name = "offline-video-spy"

        async def submit(self, request):
            calls.append(request)
            return VideoJobHandle(provider_job_id="offline-job", provider=self.name)

        async def status(self, handle):
            return VideoJobResult(status="READY", raw={"clips": []})

    async def noop(*args):
        pass

    monkeypatch.setattr(engine, "_persist", noop)
    engine.router = SimpleNamespace(profile=RuntimeProfile.AGENT_LOCAL,
        video_provider=lambda *args, **kwargs: (Provider(), route))
    asyncio.run(engine._generate_branch_media(state.id, branch.id))
    assert len(calls) == 1
    assert calls[0]["references"] == selected
    assert {ref["entity"] for ref in calls[0]["references"]} == {"gamma"}
    with pytest.raises(ProviderError, match="already has submitted"):
        asyncio.run(engine._generate_branch_media(state.id, branch.id))
    assert len(calls) == 1


def test_mock_provider_respects_count_contract_without_paid_network(monkeypatch):
    from app.providers.mock_text import MockTextProvider
    result = asyncio.run(MockTextProvider().generate([{"role": "user", "content": "raw_player_input: opening"}],
        output_contract={"purpose": "production_shots", "shot_policy": {"count": 1, "target": 8}}))
    shots = json.loads(result.content)["shots"]
    assert len(shots) == 1 and shots[0]["duration"] == 8


def test_resume_submitted_media_reuses_handle_without_another_submit(monkeypatch):
    from app.domain.schemas import ShotPlan, RuntimeProfile
    from app.providers.base import VideoJobHandle, VideoJobResult
    engine, state, branch, route = fixture_engine(monkeypatch)
    handle = VideoJobHandle(provider="h3_max", provider_job_id="already-paid", status_url="https://queue.test/status")
    branch.shots = [ShotPlan(id="shot-1", index=1, duration=5, prompt="Original shot")]
    branch.jobs = [handle.provider_job_id]
    branch.pipeline_events = [{"event": "video_submit", "shot_id": "shot-1", "provider": "h3_max",
        "provider_job_id": handle.provider_job_id, "submitted_at": 100, "handle": handle.model_dump()}]
    polled = []
    class Provider:
        name = "h3_max"
        async def submit(self, request):
            raise AssertionError("recovery must not purchase another video")
        async def status(self, recovered):
            polled.append(recovered)
            return VideoJobResult(status="READY", raw={"clips": []})
    async def noop(*args): pass
    monkeypatch.setattr(engine, "_persist", noop)
    engine.router = SimpleNamespace(profile=RuntimeProfile.AGENT_LOCAL,
        video_provider=lambda *args, **kwargs: (Provider(), route))
    asyncio.run(engine._generate_branch_media(state.id, branch.id, resume=True))
    assert polled == [handle]
    assert branch.jobs == ["already-paid"]


def test_resume_pipeline_keeps_original_narrative_and_shot_plan(monkeypatch):
    from app.domain.schemas import BranchStatus
    from app.config import settings
    engine, state, branch, route = fixture_engine(monkeypatch)
    branch.status = BranchStatus.RETRYING
    branch.jobs = ["already-paid"]
    original = branch.narrative
    calls = []
    async def forbidden(*args):
        raise AssertionError("do not replan or rewrite a shot already submitted")
    async def media(session_id, branch_id, *, resume=False):
        calls.append(resume)
    async def noop(*args): pass
    monkeypatch.setattr(settings, "branch_phase_delay_ms", 0)
    for name in ("_plan_branch", "_narrate_branch", "_shoot_branch"):
        monkeypatch.setattr(engine, name, forbidden)
    for name in ("_persist", "_push", "_assemble_branch", "_maybe_publish"):
        monkeypatch.setattr(engine, name, noop)
    monkeypatch.setattr(engine, "_generate_branch_media", media)
    asyncio.run(engine._pipeline_inner(state.id, branch.id, False))
    assert calls == [True]
    assert branch.narrative == original
    assert branch.status == BranchStatus.READY


def test_unbound_text_creature_keeps_cast_description_with_other_identity_refs(monkeypatch):
    from app.providers.base import TextResponse
    engine, state, branch, route = fixture_engine(monkeypatch)
    state.scenario_snapshot["characters"].append({"id": "creature", "identity": "Armored pursuit creature",
        "visual_state": "towering silhouette, damaged left shoulder", "appearance": "gray plated skin"})
    state.scenario_snapshot["characters"][0]["appearance"] = "short dark hair and a green coat"

    async def text(*args, **kwargs):
        assert "short dark hair and a green coat" in kwargs["messages"][0]["content"]
        return None, route, TextResponse(content=json.dumps({"shots": [{"prompt": "A person evades a creature",
            "duration": 5, "cast": ["alpha", "creature"]}]}))

    engine.router = SimpleNamespace(call_text=text)
    asyncio.run(engine._shoot_branch(state, branch))
    shot = branch.shots[0]
    assert shot.params["cast"] == ["alpha", "creature"]
    assert shot.params["text_only_cast"] == ["creature"]
    assert "gray plated skin" in shot.prompt and "damaged left shoulder" in shot.prompt
    assert "short dark hair and a green coat" in shot.prompt
    assert {ref["entity"] for ref in shot.references} == {"alpha"}


def test_bound_actor_missing_visual_identity_is_not_silently_text_cast(monkeypatch):
    from app.providers.base import TextResponse
    from app.runtime.engine import EngineError
    engine, state, branch, route = fixture_engine(monkeypatch)
    state.scenario_snapshot["characters"].append({"id": "bound", "identity": "Pinned actor", "global_character_id": "library-actor"})

    async def text(*args, **kwargs):
        return None, route, TextResponse(content=json.dumps({"shots": [{"prompt": "Two actors", "duration": 5,
            "cast": ["alpha", "bound"]}]}))

    engine.router = SimpleNamespace(call_text=text)
    with pytest.raises(EngineError, match="no image reference"):
        asyncio.run(engine._shoot_branch(state, branch))


def test_uncertain_submit_is_persisted_and_cannot_be_resubmitted(monkeypatch):
    from app.domain.schemas import RuntimeProfile, ShotPlan
    from app.providers.real import FalGenerationError
    from app.providers.router import ProviderError
    engine, state, branch, route = fixture_engine(monkeypatch)
    refs = engine._bound_references(state, ["alpha"])
    branch.shots = [ShotPlan(id="shot-1", index=1, duration=5, references=refs, prompt="A person")]
    branch.references = refs
    calls = []

    class Provider:
        name = "h3_max"

        async def submit(self, request):
            calls.append(request)
            raise FalGenerationError("TIMEOUT", "unknown outcome", submit_uncertain=True, usage_id="audit-usage")

    async def noop(*args):
        pass

    monkeypatch.setattr(engine, "_persist", noop)
    engine.router = SimpleNamespace(profile=RuntimeProfile.AGENT_LOCAL, video_provider=lambda *a, **k: (Provider(), route))
    with pytest.raises(FalGenerationError):
        asyncio.run(engine._generate_branch_media(state.id, branch.id))
    assert len(calls) == 1
    assert branch.pipeline_events[-1]["event"] == "video_submit_uncertain"
    assert branch.pipeline_events[-1]["usage_id"] == "audit-usage"
    with pytest.raises(ProviderError, match="previous submit"):
        asyncio.run(engine._generate_branch_media(state.id, branch.id))
    assert len(calls) == 1


def test_reference_free_h3_shot_rejected_before_http(monkeypatch):
    from app.domain.schemas import RuntimeProfile, ShotPlan
    from app.providers.router import ProviderError
    engine, state, branch, route = fixture_engine(monkeypatch)
    branch.shots = [ShotPlan(id="shot-1", index=1, duration=5, prompt="An unbound creature")]

    class Provider:
        name = "h3_max"

        async def submit(self, request):
            raise AssertionError("No reference must not reach H3 submit")

    engine.router = SimpleNamespace(profile=RuntimeProfile.AGENT_LOCAL, video_provider=lambda *a, **k: (Provider(), route))
    with pytest.raises(ProviderError, match="requires a reference"):
        asyncio.run(engine._generate_branch_media(state.id, branch.id))
