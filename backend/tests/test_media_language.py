"""Language contracts must reach real runtime boundaries without paid media."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.providers.base import TextResponse
from test_runtime_media_readiness import fixture_engine


def test_language_settings_persist_and_reject_invalid_input(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    before = client.get("/api/settings/language")
    assert before.status_code == 200
    assert before.json() == {"video_language": "zh-CN", "subtitle_language": "zh-CN"}
    updated = {"video_language": "en", "subtitle_language": "zh-CN"}
    assert client.put("/api/settings/language", json=updated).json() == updated
    from app.runtime.language_settings import read_language_settings
    assert read_language_settings().model_dump() == updated
    assert client.get("/api/settings/language").json() == updated
    for patch in ({"video_language": "fr"}, {"subtitle_language": None}, {"fal_paid_generation_enabled": False}):
        assert client.put("/api/settings/language", json={**updated, **patch}).status_code == 422
        assert read_language_settings().model_dump() == updated


@pytest.mark.parametrize("video,subtitle", [("zh-CN", "zh-CN"), ("en", "en"), ("zh-CN", "en"), ("en", "zh-CN")])
def test_language_and_authorized_dialogue_survive_narrative_production(monkeypatch, tmp_path, video, subtitle):
    from app.domain.media_language import MediaLanguage
    from app.runtime.language_settings import save_language_settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    save_language_settings(MediaLanguage(video_language=video, subtitle_language=subtitle))
    engine, state, branch, route = fixture_engine(monkeypatch)

    caption = "We should check the door." if subtitle == "en" else "我们应该检查这扇门。"
    line = "Check the door." if video == "en" else "检查这扇门。"
    calls = []

    async def text(role, **kw):
        calls.append((role, kw))
        if role == "narrative":
            value = {"text": line, "caption": caption, "dialogue": [{"speaker": "alpha", "line": line}]}
        else:
            value = {"shots": [{"title": "Door", "prompt": "Two people by a door.", "subtitle": caption,
                                "duration": 5, "cast": ["alpha", "beta"], "dialogue_indices": [0]}]}
        return None, route, TextResponse(content=json.dumps(value))

    engine.router = SimpleNamespace(call_text=text)
    asyncio.run(engine._narrate_branch(state, branch))
    # A later settings change must not change the language of an in-flight beat.
    save_language_settings(MediaLanguage(video_language="en" if video == "zh-CN" else "zh-CN"))
    asyncio.run(engine._shoot_branch(state, branch))
    language = {"video_language": video, "subtitle_language": subtitle}
    assert branch.media_language.model_dump() == language
    assert branch.dialogue == [{"speaker": "alpha", "line": line}]
    assert branch.caption == branch.shots[0].subtitle == caption
    for role, kw in calls:
        assert kw["output_contract"]["media_language"] == language
        assert "Mandarin Chinese" in kw["messages"][0]["content"] or "English" in kw["messages"][0]["content"]
    shot = branch.shots[0]
    assert shot.params["media_language"] == language
    assert line in shot.prompt
    assert "Do not render subtitles" in shot.prompt
    assert ("Mandarin Chinese" if video == "zh-CN" else "English") in shot.prompt
    assert branch.jobs == []
    from app.domain.schemas import Branch
    assert Branch.model_validate_json(branch.model_dump_json()).media_language.model_dump() == language


def test_silent_shot_forbids_invented_speech(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    engine, state, branch, route = fixture_engine(monkeypatch)
    state.scenario_snapshot["characters"][0]["identity"] = "Alpha · Player character, young officer"

    async def text(role, **kw):
        return None, route, TextResponse(content=json.dumps({"shots": [{"title": "Hallway",
            "prompt": "Silent corridor.", "duration": 5, "cast": ["alpha"], "dialogue_indices": []}]}))

    engine.router = SimpleNamespace(call_text=text)
    asyncio.run(engine._shoot_branch(state, branch))
    assert "No speech or voiceover" in branch.shots[0].prompt
    assert "Stage the shot in the described story location from its first frame" in branch.shots[0].prompt
    assert "Use the reference images only for character identity and clothing" in branch.shots[0].prompt
    assert "Do not render subtitles" in branch.shots[0].prompt
    assert "Player character, young officer" not in branch.shots[0].prompt


def test_invented_dialogue_reference_blocks_before_video(monkeypatch, tmp_path):
    from app.runtime.engine import EngineError
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    engine, state, branch, route = fixture_engine(monkeypatch)

    async def text(role, **kw):
        return None, route, TextResponse(content=json.dumps({"shots": [{"title": "Hallway",
            "prompt": "A corridor.", "duration": 5, "cast": ["alpha"], "dialogue_indices": [42]}]}))

    engine.router = SimpleNamespace(call_text=text)
    with pytest.raises(EngineError, match="dialogue"):
        asyncio.run(engine._shoot_branch(state, branch))
    assert branch.jobs == []


@pytest.mark.parametrize("provider_name", ["fal", "local"])
def test_language_prompt_reaches_video_http_payload(monkeypatch, tmp_path, provider_name):
    import httpx
    from app.domain.media_language import MediaLanguage
    from app.providers.real import FalH3MaxProvider, SolH3LocalProvider, reset_fal_circuit
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    reset_fal_circuit()

    captured = []
    original = httpx.AsyncClient

    def respond(request):
        captured.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, json={"request_id": "offline-language-job"})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    provider = FalH3MaxProvider(api_key="offline-test", model="minimax/h3-max/reference-to-video") if provider_name == "fal" else SolH3LocalProvider(base_url="http://local.invalid")
    prompt = "An underground room." + MediaLanguage(video_language="zh-CN", subtitle_language="en").video_instruction([{"speaker": "Officer", "line": "留在这里。"}])
    asyncio.run(provider.submit({"prompt": prompt, "shots": [{"duration": 5}], "resolution": "480P", "aspect_ratio": "16:9"}))
    assert len(captured) == 1
    url, payload = captured[0]
    assert payload["prompt"] == prompt
    assert payload["resolution"] == "480P" and payload["duration"] == 5
    if provider_name == "fal":
        assert url.endswith("/minimax/h3-max/reference-to-video")
        assert payload["prompt_expansion_mode"] == "disabled"
    reset_fal_circuit()


@pytest.mark.parametrize("field", ["caption", "dialogue"])
def test_wrong_language_stops_after_one_text_retry(monkeypatch, tmp_path, field):
    from app.runtime.engine import EngineError
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    engine, state, branch, route = fixture_engine(monkeypatch)
    calls = []

    async def text(role, **kw):
        calls.append(role)
        result = {"text": "两人停在门口。", "caption": "检查这扇门。", "dialogue": []}
        if field == "caption":
            result["caption"] = "We should check the locked door before entering."
        else:
            result["dialogue"] = [{"speaker": "alpha", "line": "We should check the locked door before entering."}]
        return None, route, TextResponse(content=json.dumps(result))

    engine.router = SimpleNamespace(call_text=text)
    with pytest.raises(EngineError, match="schema validation"):
        asyncio.run(engine._narrate_branch(state, branch))
    assert calls == ["narrative", "narrative"]
    assert branch.jobs == [] and branch.shots == []


def test_language_check_keeps_proper_names():
    from app.domain.media_language import obvious_language_mismatch
    assert not obvious_language_mismatch("Dr. Alexandra Morgan!", "zh-CN", ("Dr. Alexandra Morgan",))
    assert not obvious_language_mismatch("RPD", "zh-CN")
    assert obvious_language_mismatch("We should check the door.", "zh-CN")
    assert obvious_language_mismatch("我们应该检查这扇门。", "en")
