import asyncio
import hashlib

import httpx
import pytest

from app.config import settings
from app.providers import real, reference_images
from app.providers.base import VideoJobHandle

PNG = b"\x89PNG\r\n\x1a\noriginal-image-bytes"


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "public_base_url", "https://app.test")


def test_archived_original_survives_expired_source_and_rejects_replacement(monkeypatch):
    source = "https://expired.test/portrait.png"
    digest = hashlib.sha256(PNG).hexdigest()
    record = reference_images.store_image(source, PNG, expected_sha256=digest)
    def forbidden(*args, **kwargs):
        raise AssertionError("archived references must not contact expired hosts")
    monkeypatch.setattr(reference_images.httpx, "AsyncClient", forbidden)
    assert asyncio.run(reference_images.archive_image(source)) == record
    assert (settings.data_path / record["url"].removeprefix("/files/")).read_bytes() == PNG
    with pytest.raises(reference_images.ReferenceImageError, match="changed"):
        reference_images.store_image(source, PNG + b"new")
    with pytest.raises(reference_images.ReferenceImageError, match="original hash"):
        reference_images.store_image("https://other.test/a.png", PNG, expected_sha256="incorrect")


def test_fal_submits_archived_reference_in_original_order(monkeypatch):
    source = "https://expired.test/portrait.png"
    archived = reference_images.store_image(source, PNG)
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    real.reset_fal_circuit()
    calls = []
    def handler(req):
        import json
        calls.append(req)
        assert req.method == "POST"
        data = json.loads(req.content)
        assert data["reference_image_urls"] == ["https://app.test" + archived["url"], "https://app.test/files/outfit.png"]
        return httpx.Response(200, json={"request_id": "job", "status_url": "https://queue.test/status", "response_url": "https://queue.test/result"})
    client_type = httpx.AsyncClient
    monkeypatch.setattr(real.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(real.FalH3MaxProvider(api_key="offline").submit({"duration": 5,
        "references": [{"path": source, "type": "image"}, {"path": "/files/outfit.png", "type": "image"}]}))
    assert len(calls) == 1
    assert result.metadata["reference_transport"][0]["sha256"] == archived["sha256"]


def test_reference_failure_happens_before_paid_submit(monkeypatch):
    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    real.reset_fal_circuit()
    calls = []
    def handler(req):
        calls.append(req.method)
        assert req.method == "GET"
        return httpx.Response(404, json={"detail": "image not found"})
    client_type = httpx.AsyncClient
    monkeypatch.setattr(real.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs))
    with pytest.raises(real.FalGenerationError, match="reference") as error:
        asyncio.run(real.FalH3MaxProvider(api_key="offline").submit({"duration": 5,
            "reference_image_urls": ["https://expired.test/lost.png"]}))
    assert error.value.kind == "REFERENCE_UNAVAILABLE"
    assert calls == ["GET"]
    assert real.fal_circuit_status()["http_attempts"] == 0


def test_fal_result_422_preserves_failure_without_guessing_response_suffix(monkeypatch):
    calls = []
    usage_id = real._record_usage("h3_max", "model", "video_generation", {}, "ACCEPTED")
    def handler(req):
        calls.append(req.url.path)
        if req.url.path == "/status":
            return httpx.Response(200, json={"status": "COMPLETED"})
        assert req.url.path == "/result"
        return httpx.Response(422, json={"detail": [{"loc": ["body", "reference_image_urls", 1],
            "type": "file_download_error", "input": "https://private.test/image?token=DO_NOT_LOG", "msg": "Failed to download the file."}]})
    client_type = httpx.AsyncClient
    monkeypatch.setattr(real.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs))
    handle = VideoJobHandle(provider="h3_max", provider_job_id="failed-job", status_url="https://queue.test/status",
        response_url="https://queue.test/result", metadata={"usage_id": usage_id})
    result = asyncio.run(real.FalH3MaxProvider(api_key="offline").status(handle))
    assert result.status == "FAILED"
    assert "REFERENCE_UNAVAILABLE" in result.error
    assert result.raw["http_status"] == 422
    assert result.raw["reference_indices"] == [1]
    assert "DO_NOT_LOG" not in str(result)
    assert calls == ["/status", "/result"]
    entry = next(x for x in real.usage_ledger() if x["id"] == usage_id)
    assert entry["status"] == "FAILED" and entry["http_status"] == 422


def test_generated_candidate_archives_without_changing_identity(client, monkeypatch):
    from app.main import provider_router
    from app.runtime.character_service import CharacterAssetService
    response = client.post("/api/characters", json={"name": "Archive test", "bio": "An archive test character"})
    assert response.status_code == 200
    character = response.json()
    source = "https://expired.test/generated.png"
    reference_images.store_image(source, PNG)
    monkeypatch.setattr(provider_router, "mode", "live")
    service = CharacterAssetService(provider_router)
    asset = client.portal.call(lambda: service.add_asset(character["id"], "front", source,
        provenance={"provider": "image_relay", "capability": "IMAGE_GENERATION"}))
    assert asset.url.startswith("/files/reference-images/")
    assert asset.status.value == "CANDIDATE"
    assert asset.character_id == character["id"]
    assert asset.provenance["archive"]["sha256"] == hashlib.sha256(PNG).hexdigest()
    persisted = client.portal.call(service.list_assets, character["id"])
    assert persisted[0].url == asset.url


def test_archive_failure_preserves_paid_candidate_for_recovery(client, monkeypatch):
    from app.main import provider_router
    from app.runtime.character_service import CharacterAssetService
    response = client.post("/api/characters", json={"name": "Recover candidate", "bio": "A recovery test character"})
    assert response.status_code == 200
    character = response.json()
    monkeypatch.setattr(provider_router, "mode", "live")
    async def unavailable(source):
        raise reference_images.ReferenceImageError("reference download failed")
    monkeypatch.setattr(reference_images, "archive_image", unavailable)
    service = CharacterAssetService(provider_router)
    asset = client.portal.call(lambda: service.add_asset(character["id"], "front", "https://expired.test/new.png",
        provenance={"provider": "image_relay", "capability": "IMAGE_EDIT"}))
    persisted = client.portal.call(service.list_assets, character["id"])
    assert len(persisted) == 1 and persisted[0].id == asset.id
    assert persisted[0].provenance["archive_error"] == "ReferenceImageError"


def test_temporary_poll_disconnect_keeps_same_paid_job(monkeypatch):
    calls = []
    def handler(req):
        calls.append((req.method, req.url.path))
        assert req.method == "GET"
        if len(calls) == 1:
            raise httpx.ConnectError("temporary connection failure", request=req)
        return httpx.Response(200, json={"status": "IN_PROGRESS"})
    client_type = httpx.AsyncClient
    monkeypatch.setattr(real.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs))
    handle = VideoJobHandle(provider="h3_max", provider_job_id="existing-job", status_url="https://queue.test/status")
    provider = real.FalH3MaxProvider(api_key="offline")
    first = asyncio.run(provider.status(handle))
    second = asyncio.run(provider.status(handle))
    assert first.status == second.status == "GENERATING"
    assert first.raw["poll_error"] == "NETWORK_ERROR"
    assert calls == [("GET", "/status"), ("GET", "/status")]
