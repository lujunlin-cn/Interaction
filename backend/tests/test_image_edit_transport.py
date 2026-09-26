"""Actual encoded multipart HTTP body, without any external request."""
import asyncio
from email import policy
from email.parser import BytesParser

import httpx
import pytest


def test_edit_uploads_binary_and_records_transport(monkeypatch, tmp_path):
    from app.config import settings
    from app.providers.real import OpenAIImageProvider, usage_ledger
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    original_client = httpx.AsyncClient
    source = b"\x89PNG\r\n\x1a\nexisting-asset"
    source_gets, submissions = [], []

    async def respond(request):
        if request.method == "GET":
            source_gets.append(str(request.url))
            assert "authorization" not in request.headers
            return httpx.Response(200, content=source, headers={"content-type": "image/png"})
        body = await request.aread()
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + body)
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        assert parts["image"].get_payload(decode=True) == source
        assert parts["image"].get_filename() == "reference-0.png"
        assert parts["size"].get_content() == "4096x4096"
        assert parts["n"].get_content() == "1"
        assert parts["prompt"].get_content() == "Keep identity, change outfit"
        submissions.append(parts["model"].get_content())
        if len(submissions) == 1:
            return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})
        return httpx.Response(200, json={"data": [{"url": "https://assets.test/out.png"}]}, headers={"x-request-id": "edit-live-contract"})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    provider = OpenAIImageProvider("https://relay.test", "offline-token", "primary")
    result = asyncio.run(provider.edit({"prompt": "Keep identity, change outfit", "resolution": "4K", "image_urls": ["https://assets.test/source.png"]}))
    assert len(source_gets) == 1 and len(submissions) == 2
    assert result["request_id"] == "edit-live-contract"
    assert result["transport"] == "multipart/form-data"
    assert len(result["source_image_sha256"]) == 1
    assert all(entry["transport"] == "multipart/form-data" and entry["reference_summary"]["images"] == 1 for entry in usage_ledger())
    assert "offline-token" not in str(result) and "existing-asset" not in str(result)


def test_edit_repeats_openai_image_field_for_multiple_sources(monkeypatch, tmp_path):
    """Relays accept repeated ``image`` parts; ``image[]`` is ignored by api-top."""
    from app.config import settings
    from app.providers.real import OpenAIImageProvider
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    original_client = httpx.AsyncClient
    seen = []

    async def respond(request):
        if request.method == "GET":
            return httpx.Response(200, content=b"\x89PNG\r\n\x1a\nsource")
        body = await request.aread()
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + body)
        seen.extend(part.get_param("name", header="content-disposition")
                    for part in message.iter_parts())
        return httpx.Response(200, json={"data": [{"url": "https://assets.test/out.png"}]})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs:
                        original_client(transport=httpx.MockTransport(respond), **kwargs))
    provider = OpenAIImageProvider("https://relay.test", "offline-token", "primary")
    asyncio.run(provider.edit({"prompt": "preserve identity", "resolution": "4K",
                               "image_urls": ["https://assets.test/a.png",
                                               "https://assets.test/b.png"]}))
    assert seen.count("image") == 2
    assert "image[]" not in seen


def test_local_source_cannot_escape_public_asset_root(monkeypatch, tmp_path):
    from app.config import settings
    from app.providers.real import OpenAIImageProvider, usage_ledger
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    provider = OpenAIImageProvider("https://relay.test", "offline-token")
    for source in ["/files/../.env", "/files/%2e%2e/.env", "/files/.private/usage-ledger.jsonl"]:
        with pytest.raises(ValueError, match="public image"):
            asyncio.run(provider.edit({"image_urls": [source]}))
    assert usage_ledger() == []


def test_standard_views_stop_after_first_failure_and_resume_saved_views(client, monkeypatch):
    from app.main import provider_router
    from app.runtime.character_service import CharacterAssetService
    character = client.post("/api/characters", json={"name": "View Recovery", "bio": "offline outage"}).json()
    service = CharacterAssetService(provider_router)
    front = client.portal.call(service.add_asset, character["id"], "front", "https://assets.test/front.png")
    calls = []

    class Provider:
        async def edit(self, request):
            calls.append(request)
            if len(calls) == 2:
                raise RuntimeError("provider-wide outage")
            return {"images": [{"url": f"https://assets.test/{len(calls)}.png"}]}

    monkeypatch.setitem(provider_router.registry, "nano_banana_2", Provider())
    with pytest.raises(RuntimeError, match="provider-wide"):
        client.portal.call(service.generate_standard_views, character["id"], front.id)
    assert len(calls) == 2
    views = client.portal.call(service.generate_standard_views, character["id"], front.id)
    assert len(views) == 4 and len(calls) == 5  # The completed first view was reused.
