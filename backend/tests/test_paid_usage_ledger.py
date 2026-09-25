"""Offline HTTP-spy tests: no external media request is permitted here."""
import asyncio
import json
import os
import subprocess
import sys

import httpx
import pytest


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


def stub_http(monkeypatch, responder):
    from app.providers import real

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            return responder("POST", url, kwargs)

        async def get(self, url, **kwargs):
            return responder("GET", url, kwargs)

    monkeypatch.setattr(real.httpx, "AsyncClient", Client)


def response(status, data, url, request_id=""):
    return httpx.Response(status, json=data, headers={"x-request-id": request_id},
                          request=httpx.Request("POST", url))


def test_journal_survives_new_process_and_excludes_sensitive_fields(isolated_ledger):
    from app.providers.real import _record_usage, _update_usage, usage_ledger
    attempt = _record_usage("image_relay", "image-model", "image_edit", {
        "prompt": "PRIVATE STORY", "Authorization": "Bearer TOP_SECRET",
        "image": ["https://example.invalid/ref?token=SIGNED_SECRET"],
        "size": "4096x4096", "n": 1,
    }, "SUBMITTED")
    _update_usage(attempt, "SUCCEEDED", request_id="external-123", model="actual-image-model")
    items = usage_ledger()
    assert len(items) == 1 and items[0]["request_id"] == "external-123"
    assert items[0]["reference_summary"]["images"] == 1
    assert items[0]["external_http_attempts"] == 1
    path = isolated_ledger / ".private" / "usage-ledger.jsonl"
    raw = path.read_text()
    assert len(raw.splitlines()) == 2  # Append status, preserve original event.
    for secret in ("PRIVATE STORY", "TOP_SECRET", "SIGNED_SECRET", "Authorization"):
        assert secret not in raw
    env = {**os.environ, "DATA_DIR": str(isolated_ledger)}
    restarted = subprocess.run([sys.executable, "-c", "from app.providers.real import usage_ledger; import json; print(json.dumps(usage_ledger()))"],
                               env=env, text=True, capture_output=True, check=True)
    assert json.loads(restarted.stdout) == items


def test_interrupted_last_append_does_not_destroy_next_event(isolated_ledger):
    from app.providers.real import _record_usage, usage_ledger
    first = _record_usage("image_relay", "model", "image_generation", {}, "SUBMITTED")
    path = isolated_ledger / ".private" / "usage-ledger.jsonl"
    with path.open("a") as stream:
        stream.write('{"id":"incomplete')
    second = _record_usage("image_relay", "model", "image_generation", {}, "SUBMITTED")
    assert {entry["id"] for entry in usage_ledger()} == {first, second}


@pytest.mark.parametrize("edit", [False, True])
def test_relay_records_one_external_request_with_completion(monkeypatch, edit):
    from app.providers.real import OpenAIImageProvider, usage_ledger
    calls = []

    def responder(method, url, kwargs):
        calls.append((method, url))
        return response(200, {"model": "actual", "data": [{"url": "https://example.invalid/result"}]}, url, "relay-456")

    stub_http(monkeypatch, responder)
    provider = OpenAIImageProvider("https://example.invalid", "secret", "preferred")
    request = {"prompt": "private", "resolution": "4K", "image_urls": ["https://example.invalid/reference"]}
    result = asyncio.run(provider.edit(request) if edit else provider.generate(request))
    ledger = usage_ledger()
    assert len(calls) == 1 and len(ledger) == 1
    assert ledger[0]["status"] == "SUCCEEDED"
    assert ledger[0]["request_id"] == result["request_id"] == "relay-456"
    assert ledger[0]["model"] == "actual"
    assert ledger[0]["resolution"] == "4K"
    assert ledger[0]["reference_summary"]["images"] == (1 if edit else 0)
    assert sum(i["external_http_attempts"] for i in ledger) == 1


@pytest.mark.parametrize("status,message", [(401, "bad token"), (400, "invalid size"), (422, "size is not supported by model"), (404, "route not found")])
def test_relay_does_not_retry_auth_or_non_model_errors(monkeypatch, status, message):
    from app.providers.real import OpenAIImageProvider, usage_ledger
    calls = []

    def responder(method, url, kwargs):
        calls.append(url)
        return response(status, {"error": {"message": message}}, url, "rejected-request")

    stub_http(monkeypatch, responder)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(OpenAIImageProvider("https://example.invalid", "secret", "preferred").generate({"resolution": "4K"}))
    assert len(calls) == 1
    entry = usage_ledger()[0]
    assert entry["status"] == "FAILED"
    assert entry["request_id"] == "rejected-request"
    assert entry["http_status"] == status


def test_explicit_model_rejection_counts_two_attempts(monkeypatch):
    from app.config import settings
    from app.providers.real import OpenAIImageProvider, usage_ledger
    monkeypatch.setattr(settings, "image_provider_fallback_model", "alternate")
    calls = []

    def responder(method, url, kwargs):
        calls.append(kwargs["json"]["model"])
        if len(calls) == 1:
            return response(404, {"error": {"code": "model_not_found"}}, url, "rejected")
        return response(200, {"id": "accepted", "data": [{"url": "https://example.invalid/image"}]}, url)

    stub_http(monkeypatch, responder)
    result = asyncio.run(OpenAIImageProvider("https://example.invalid", "secret", "preferred").generate({"resolution": "4K"}))
    assert calls == ["preferred", "alternate"]
    assert result["model"] == "alternate"
    entries = usage_ledger()
    assert len(entries) == 2
    assert {e["status"] for e in entries} == {"FAILED", "SUCCEEDED"}
    assert sum(e["external_http_attempts"] for e in entries) == 2


@pytest.mark.parametrize("edit", [False, True])
def test_relay_uses_ordered_three_model_fallback(monkeypatch, edit):
    from app.config import settings
    from app.providers.real import OpenAIImageProvider, usage_ledger

    monkeypatch.setattr(settings, "image_provider_fallback_model", "gpt-image-2.5-flare")
    monkeypatch.setattr(settings, "image_provider_fallback_model_2", "gpt-image-2.5-sunburst")
    monkeypatch.setattr(settings, "image_provider_fallback_model_3", "gpt-image-2")
    calls = []

    def responder(method, url, kwargs):
        calls.append(kwargs["json"]["model"])
        if len(calls) < 4:
            return response(503, {"error": {"message": "temporarily unavailable"}}, url, f"failed-{len(calls)}")
        return response(200, {"model": "gpt-image-2", "data": [{"url": "https://example.invalid/image"}]}, url, "accepted")

    stub_http(monkeypatch, responder)
    request = {"resolution": "4K", "prompt": "portrait"}
    if edit:
        request["image_urls"] = ["https://example.invalid/reference"]
    result = asyncio.run((OpenAIImageProvider("https://example.invalid", "secret", "preferred").edit if edit else OpenAIImageProvider("https://example.invalid", "secret", "preferred").generate)(request))
    assert calls == ["preferred", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2"]
    assert result["model"] == "gpt-image-2"
    assert len(usage_ledger()) == 4


def test_fal_guard_and_request_id_are_durable(monkeypatch):
    from app.config import settings
    from app.providers.real import FalGenerationError, FalH3MaxProvider, reset_fal_circuit, usage_ledger
    reset_fal_circuit()

    monkeypatch.setattr(settings, "fal_paid_generation_enabled", False)
    calls = []

    def responder(method, url, kwargs):
        calls.append(method)
        if method == "POST":
            return response(200, {"request_id": "h3-job", "status_url": "https://example.invalid/status", "response_url": "https://example.invalid/result"}, url)
        return response(200, {"status": "IN_QUEUE"}, url)

    stub_http(monkeypatch, responder)
    provider = FalH3MaxProvider(api_key="test-secret")
    with pytest.raises(FalGenerationError):
        asyncio.run(provider.submit({"resolution": "480P"}))
    assert calls == []
    assert usage_ledger()[0]["external_http_attempts"] == 0
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    handle = asyncio.run(provider.submit({"resolution": "480P", "shots": [{"duration": 5}]}))
    asyncio.run(provider.status(handle))
    entries = usage_ledger()
    actual = next(e for e in entries if e["request_id"] == "h3-job")
    assert actual["status"] == "GENERATING"
    assert actual["duration"] == 5
    assert actual["resolution"] == "480P"
    assert sum(e["external_http_attempts"] for e in entries) == 1
    assert calls == ["POST", "GET"]
    reset_fal_circuit()


def test_fal_rejects_over_capacity_before_submit(monkeypatch):
    from app.config import settings
    from app.providers.real import FalGenerationError, FalH3MaxProvider, reset_fal_circuit, usage_ledger
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    reset_fal_circuit()

    def responder(*args):
        raise AssertionError("Invalid references must never reach HTTP")

    stub_http(monkeypatch, responder)
    with pytest.raises(FalGenerationError, match="reference count"):
        asyncio.run(FalH3MaxProvider(api_key="offline").submit({"resolution": "480P",
            "reference_image_urls": [f"https://example.invalid/image{i}" for i in range(9)],
            "reference_audio_urls": [f"https://example.invalid/audio{i}" for i in range(3)],
            "reference_video_urls": ["https://example.invalid/video"],
        }))
    assert usage_ledger() == []


@pytest.mark.parametrize("duration", [0, -1, 8.5, float("nan"), float("inf"), "invalid"])
def test_fal_rejects_invalid_duration_before_http(monkeypatch, duration):
    from app.config import settings
    from app.providers.real import FalGenerationError, FalH3MaxProvider, reset_fal_circuit, usage_ledger
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    reset_fal_circuit()

    def responder(*args):
        raise AssertionError("Invalid duration must never reach HTTP")

    stub_http(monkeypatch, responder)
    with pytest.raises(FalGenerationError, match="positive finite integer"):
        asyncio.run(FalH3MaxProvider(api_key="offline").submit({"resolution": "480P", "shots": [{"duration": duration}]}))
    assert usage_ledger() == []


@pytest.mark.parametrize("error_type,uncertain", [
    (httpx.ReadTimeout, True), (httpx.WriteTimeout, True), (httpx.ReadError, True),
    (httpx.ConnectTimeout, False), (httpx.PoolTimeout, False), (httpx.ConnectError, False),
])
def test_fal_records_uncertain_post_separately_from_presubmit_failure(monkeypatch, error_type, uncertain):
    from app.config import settings
    from app.providers.real import FalGenerationError, FalH3MaxProvider, reset_fal_circuit, usage_ledger
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    reset_fal_circuit()
    calls = []

    def responder(method, url, kwargs):
        calls.append(method)
        raise error_type("injected transport failure", request=httpx.Request("POST", url))

    stub_http(monkeypatch, responder)
    with pytest.raises(FalGenerationError) as caught:
        asyncio.run(FalH3MaxProvider(api_key="offline").submit({"resolution": "480P", "shots": [{"duration": 5}]}))
    assert caught.value.submit_uncertain is uncertain
    assert len(calls) == 1
    entry = usage_ledger()[0]
    assert entry["status"] == ("SUBMISSION_UNCERTAIN" if uncertain else "FAILED")
    assert entry["id"] == caught.value.usage_id
    assert entry["request_id"] is None
    assert entry["external_http_attempts"] == 1
