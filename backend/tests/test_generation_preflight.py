"""Developer preflight is a truthful local estimate, never a provider submission."""
from types import SimpleNamespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes import build_api
from app.config import settings
from app.providers import real


@pytest.fixture
def preview(monkeypatch):
    for key, value in {
        "target_k": 3, "shots_per_branch": 1, "mock_shot_duration": 5,
        "opening_shot_duration": 8, "ending_shot_duration": 8, "max_video_shot_duration": 10,
        "developer_test_override_enabled": False, "developer_test_top_k": 1,
        "developer_test_max_shots": 1, "developer_test_shot_duration": 5,
        "max_test_reference_images": 2, "max_test_reference_videos": 0,
        "fal_paid_generation_enabled": True, "video_generation_resolution": "480P",
        "generation_aspect_ratio": "16:9",
    }.items():
        monkeypatch.setattr(settings, key, value)
    circuit = {"state": "CLOSED", "reason": "", "keys": [{"state": "CLOSED", "index": 0}]}
    monkeypatch.setattr(real, "fal_circuit_status", lambda: circuit.copy())
    def no_ledger(*args, **kwargs):
        pytest.fail("preview must not create a generation attempt in Usage Ledger")
    monkeypatch.setattr(real, "_record_usage", no_ledger)
    router = SimpleNamespace(mode="live", health={}, registry={})
    app = FastAPI()
    app.include_router(build_api(SimpleNamespace(), router))
    async def call(data=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://local") as client:
            return await client.post("/api/dev/generation-preflight", json=data or {"role": "h3_max"})
    return call, circuit, router


@pytest.mark.asyncio
async def test_formal_preflight_uses_effective_configuration_and_unknown_refs(preview):
    call, _, _ = preview
    response = await call()
    assert response.status_code == 200
    result = response.json()
    assert (result["branches"], result["shots_per_branch"], result["jobs"], result["total_requested_duration"]) == (3, 1, 3, 15)
    assert result["estimate"] is True and result["actual_plan"] is False
    assert result["reference_images"] is None and result["reference_videos"] is None
    assert result["reference_status"] == "UNKNOWN_NOT_RESOLVED"
    assert result["reference_limits"] == {"image": 9, "audio": 3, "video": 3, "mixed": 12}
    assert result["fal_request_allowed"] is True


@pytest.mark.asyncio
async def test_test_override_controls_k_shots_duration_and_caps(preview, monkeypatch):
    call, _, _ = preview
    monkeypatch.setattr(settings, "developer_test_override_enabled", True)
    result = (await call()).json()
    assert result["jobs"] == 1 and result["total_requested_duration"] == 5
    assert result["reference_limits"]["image"] == 2
    assert result["reference_limits"]["video"] == 0
    assert result["reference_images"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["opening", "ending"])
async def test_opening_and_ending_estimate_single_eight_second_shot(preview, phase):
    call, _, _ = preview
    result = (await call({"role": "h3_max", "phase": phase})).json()
    assert result["jobs"] == 1 and result["total_requested_duration"] == 8


@pytest.mark.asyncio
async def test_opening_respects_test_duration_and_global_cap(preview, monkeypatch):
    call, _, _ = preview
    monkeypatch.setattr(settings, "developer_test_override_enabled", True)
    result = (await call({"role": "h3_max", "phase": "opening"})).json()
    assert result["duration"] == 5


@pytest.mark.asyncio
async def test_open_circuit_is_not_allowed_when_guard_enabled(preview):
    call, circuit, _ = preview
    circuit.update(state="OPEN", reason="BILLING_LOCKED")
    result = (await call()).json()
    assert result["guard"] == "CLOSED" and result["circuit"] == "OPEN"
    assert result["fal_request_allowed"] is False
    assert "BILLING_LOCKED" in result["blocked_reasons"]


@pytest.mark.asyncio
async def test_missing_credential_and_router_circuit_also_block(preview):
    call, circuit, router = preview
    circuit["keys"] = []
    assert (await call()).json()["fal_request_allowed"] is False
    circuit["keys"] = [{"state": "CLOSED"}]
    router.health["h3_max"] = SimpleNamespace(circuit="OPEN")
    assert (await call()).json()["fal_request_allowed"] is False


@pytest.mark.asyncio
async def test_guard_off_preview_does_not_record_a_fake_generation_attempt(preview, monkeypatch):
    call, _, _ = preview
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", False)
    result = (await call()).json()
    assert result["fal_request_allowed"] is False
    assert "PAID_GENERATION_DISABLED" in result["blocked_reasons"]


@pytest.mark.asyncio
async def test_manual_preview_is_explicit_and_does_not_apply_test_caps(preview):
    call, _, _ = preview
    result = (await call({"role": "h3_max", "branches": 2, "shots": 2, "duration": 9,
                          "reference_images": 6, "reference_videos": 2})).json()
    assert result["estimate_basis"] == "MANUAL_PREVIEW"
    assert result["jobs"] == 4 and result["total_requested_duration"] == 36
    assert result["reference_images"] == 6 and result["reference_videos"] == 2
    assert result["reference_status"] == "MANUAL_COUNTS_NOT_RESOLVED"
    assert settings.target_k == 3 and not settings.developer_test_override_enabled


@pytest.mark.asyncio
async def test_preview_above_cap_is_explicitly_blocked_not_silently_clipped(preview):
    call, _, _ = preview
    result = (await call({"role": "h3_max", "duration": 15, "reference_images": 10})).json()
    assert result["duration"] == 15 and result["reference_images"] == 10
    assert result["fal_request_allowed"] is False
    assert result["validation_errors"]


@pytest.mark.asyncio
async def test_invalid_numeric_preview_gets_readable_422(preview):
    call, _, _ = preview
    response = await call({"role": "h3_max", "branches": "bad"})
    assert response.status_code == 422
    assert "detail" in response.json()
