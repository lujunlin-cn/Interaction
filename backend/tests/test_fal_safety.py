import asyncio

import httpx


def test_paid_generation_guard_fails_before_network(monkeypatch):
    from app.config import settings
    from app.providers.real import FalH3MaxProvider, FalImageProvider

    monkeypatch.setattr(settings, "fal_paid_generation_enabled", False)

    async def run():
        for call in (
            FalH3MaxProvider(api_key="test").submit({"prompt": "x", "shots": [{"duration": 5}]}),
            FalImageProvider(api_key="test").generate({"prompt": "x", "num_images": 2}),
        ):
            try:
                await call
            except Exception as exc:  # guard is the assertion
                assert getattr(exc, "kind", "") == "PAID_GENERATION_DISABLED"
            else:
                raise AssertionError("paid provider call unexpectedly succeeded")

    asyncio.run(run())


def test_top_up_opens_fal_circuit():
    from app.providers.real import _fal_http_error, fal_circuit_status, reset_fal_circuit

    reset_fal_circuit()
    response = httpx.Response(
        403,
        request=httpx.Request("POST", "https://queue.fal.run/test"),
        content=b'{"detail":"User is locked. Reason: TOP_UP"}',
    )
    error = _fal_http_error(httpx.HTTPStatusError("403", request=response.request, response=response))
    assert error.kind == "BILLING_LOCKED"
    assert fal_circuit_status()["state"] == "OPEN"
    reset_fal_circuit()
