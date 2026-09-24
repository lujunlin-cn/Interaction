import asyncio


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
