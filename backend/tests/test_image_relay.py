import asyncio
import httpx
import pytest


def test_image_relay_uses_openai_image_contract(monkeypatch):
    from app.providers.real import OpenAIImageProvider

    provider = OpenAIImageProvider("https://api-top.com", "token", "gpt-image-2.5-sunburst")
    captured = {}

    async def fake_request(path, payload):
        captured.update(path=path, payload=payload)
        return {"data": [{"url": "https://example.test/image.png"}]}

    monkeypatch.setattr(provider, "_request", fake_request)
    result = asyncio.run(provider.generate({
        "prompt": "cat", "num_images": 2, "resolution": "0.5K",
    }))
    assert captured["path"] == "generations"
    assert captured["payload"] == {
        "model": "gpt-image-2.5-sunburst", "prompt": "cat", "size": "512x512",
        "quality": "standard", "style": "vivid", "n": 2, "response_format": "url",
    }
    assert result["images"][0]["url"].endswith("image.png")


@pytest.mark.parametrize("operation", ["generate", "edit"])
def test_image_relay_returns_actual_request_and_dimensions(monkeypatch, operation):
    from app.providers.real import OpenAIImageProvider
    provider = OpenAIImageProvider("https://example.invalid", "token", "requested-model")

    async def fake_request(path, payload):
        return {"request_id": "relay-request-42", "model": "served-model",
                "data": [{"url": "https://example.invalid/asset.png", "width": 4096, "height": 4096}]}

    monkeypatch.setattr(provider, "_request", fake_request)
    result = asyncio.run(getattr(provider, operation)({
        "prompt": "portrait", "resolution": "4K", "aspect_ratio": "16:9",
        "image_urls": ["https://example.invalid/source.png"],
    }))
    assert result["request_id"] == "relay-request-42"
    assert result["provider"] == "image_relay"
    assert result["model"] == "served-model"
    assert result["requested_model"] == "requested-model"
    assert result["resolution"] == "4K"
    assert result["requested_size"] == "4096x4096"
    assert result["actual_aspect_ratio"] == result["aspect_ratio"] == "1:1"
    assert result["requested_aspect_ratio"] == "16:9"
    assert result["normalization"]["aspect_ratio"]["submitted"] == "1:1"
    assert result["output_dimensions"] == [{"width": 4096, "height": 4096}]


def test_image_relay_preserves_header_request_id(monkeypatch):
    from app.providers.real import OpenAIImageProvider

    class StubClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            return httpx.Response(200, headers={"x-request-id": "header-123"},
                                  json={"data": [{"url": "https://example.invalid/asset.png"}]},
                                  request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", StubClient)
    provider = OpenAIImageProvider("https://example.invalid", "token", "image-model")
    result = asyncio.run(provider.generate({"prompt": "portrait", "resolution": "4K"}))
    assert result["request_id"] == "header-123"
    assert result["actual_aspect_ratio"] is None


@pytest.mark.parametrize("mode", ["live", "hybrid"])
@pytest.mark.parametrize("base_url,api_key", [("https://example.invalid", ""), ("", "token")])
def test_partial_relay_configuration_never_falls_back_to_fal(monkeypatch, mode, base_url, api_key):
    from app.config import settings
    from app.providers.real import OpenAIImageProvider, build_provider_registry
    monkeypatch.setattr(settings, "image_provider_base_url", base_url)
    monkeypatch.setattr(settings, "image_provider_api_key", api_key)
    monkeypatch.setattr(settings, "fal_key", "")
    monkeypatch.setattr(settings, "fal_key_secondary", "")
    provider = build_provider_registry(mode)["nano_banana_2"]
    assert isinstance(provider, OpenAIImageProvider)
    with pytest.raises(RuntimeError, match="image relay is not configured"):
        asyncio.run(provider.generate({"prompt": "portrait"}))


def test_character_generation_paths_persist_relay_provenance(client, monkeypatch):
    from app.main import provider_router
    from app.runtime.character_service import CharacterAssetService

    character = client.post("/api/characters", json={"name": "Audit Character", "bio": "Reference audit"}).json()
    calls = []

    class StubImageProvider:
        name = "image_relay"

        async def generate(self, request):
            calls.append(request)
            return {"provider": self.name, "model": "actual-image-model", "request_id": f"relay-{len(calls)}",
                    "images": [{"url": f"https://example.invalid/{len(calls)}.png", "width": 4096, "height": 4096}],
                    "resolution": "4K", "aspect_ratio": "1:1", "requested_aspect_ratio": "16:9",
                    "actual_aspect_ratio": "1:1", "requested_size": "4096x4096"}

        async def edit(self, request):
            return await self.generate(request)

    monkeypatch.setitem(provider_router.registry, "nano_banana_2", StubImageProvider())
    service = CharacterAssetService(provider_router)
    candidates = client.portal.call(service.ai_generate_candidates, character["id"])
    views = client.portal.call(service.generate_standard_views, character["id"], candidates[0].id)
    edits = client.portal.call(service.edit_image, character["id"], candidates[0].id, "Change outfit")
    persisted = client.portal.call(service.list_assets, character["id"])
    assert len(candidates) == 1 and len(views) == 4 and len(edits) == 1
    assert len(persisted) == 6
    for asset in persisted:
        assert asset.provenance["request_id"].startswith("relay-")
        assert asset.provenance["request_id"] != asset.generation_job_id
        assert asset.provenance["provider"] == "image_relay"
        assert asset.provenance["model"] == "actual-image-model"
        assert asset.provenance["output_dimensions"] == {"width": 4096, "height": 4096}
        assert asset.provenance["requested_aspect_ratio"] == "16:9"
        assert asset.provenance["actual_aspect_ratio"] == "1:1"
