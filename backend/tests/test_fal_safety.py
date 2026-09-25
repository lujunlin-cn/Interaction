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


def test_fal_key_rotation_on_quota(monkeypatch):
    from app.config import settings
    from app.providers import real
    from app.providers.real import FalH3MaxProvider, fal_circuit_status, reset_fal_circuit

    monkeypatch.setattr(settings, "fal_paid_generation_enabled", True)
    monkeypatch.setattr(settings, "fal_key", "key-one")
    monkeypatch.setattr(settings, "fal_key_secondary", "key-two")
    reset_fal_circuit()
    calls = []

    class FakeResponse:
        def __init__(self, status, body):
            self.status_code = status
            self._body = body
            self.request = httpx.Request("POST", "https://queue.fal.run/test")
            self.text = body.decode() if isinstance(body, bytes) else str(body)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("quota", request=self.request,
                                            response=httpx.Response(self.status_code, request=self.request, content=self._body))

        def json(self):
            return self._body

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, url, json, headers):
            calls.append(headers["Authorization"])
            if len(calls) == 1:
                return FakeResponse(403, b'{"detail":"User is locked. Reason: TOP_UP"}')
            return FakeResponse(200, {"request_id": "job-two", "status_url": "https://status", "response_url": "https://result"})

    monkeypatch.setattr(real.httpx, "AsyncClient", FakeClient)

    async def run():
        handle = await FalH3MaxProvider().submit({"prompt": "one small test", "shots": [{"duration": 5}], "resolution": "480P"})
        assert handle.metadata["fal_key_index"] == 1
        assert calls == ["Key key-one", "Key key-two"]

    asyncio.run(run())
    status = fal_circuit_status()
    assert status["active_key_index"] == 1
    assert status["keys"][0]["state"] == "OPEN"
    reset_fal_circuit()
