"""ProviderRouter 单元测试：路由矩阵、fallback、熔断、Profile 约束。"""
import pytest

from app.domain.schemas import RuntimeProfile
from app.providers.real import build_provider_registry
from app.providers.router import ProviderBlocked, ProviderRouter


def make_router(mode="mock", profile=RuntimeProfile.AGENT_LOCAL):
    return ProviderRouter(build_provider_registry("mock"), mode=mode, profile=profile)


class TestRouter:
    def test_mock_routes_all_roles(self):
        r = make_router()
        for role in ("director", "narrative", "production", "authoring", "decision", "cloud_video"):
            provider, rec = r.route(role)
            assert provider is not None
            assert rec.status == "healthy"

    def test_live_matrix_shape(self):
        r = ProviderRouter(build_provider_registry("mock"), mode="live")
        m = {x["role"]: x for x in r.route_matrix()}
        assert m["director"]["primary"] == "nemotron_local"
        assert m["director"]["fallbacks"] == ["step_5"]
        assert m["narrative"]["primary"] == "step_37"
        assert m["production"]["fallbacks"] == ["step_37"]
        assert m["authoring"]["primary"] == "step_5"

    def test_profile_constraint_video_local(self):
        r = ProviderRouter(build_provider_registry("mock"), mode="live",
                           profile=RuntimeProfile.VIDEO_LOCAL)
        m = {x["role"]: x for x in r.route_matrix()}
        # VIDEO_LOCAL 下 nemotron_local 不可用 → director 落到 step_5
        assert m["director"]["selected"] == "step_5"
        assert any(s["reason"] == "profile_unavailable" for s in m["director"]["skipped"])

    def test_fallback_on_failure(self):
        r = ProviderRouter(build_provider_registry("mock"), mode="live")
        r.inject_failure("nemotron_local", "circuit_open")
        _, rec = r.route("director")
        assert rec.selected == "step_5"
        assert rec.status == "fallback"

    def test_blocked_when_all_down(self):
        r = ProviderRouter(build_provider_registry("mock"), mode="live")
        r.inject_failure("step_5", "circuit_open")
        with pytest.raises(ProviderBlocked):
            r.route("authoring")

    def test_permanent_block_fast_fails(self):
        r = ProviderRouter(build_provider_registry("mock"), mode="live")
        r.inject_failure("step_5", "policy_rejection")
        with pytest.raises(ProviderBlocked) as ei:
            r.route("authoring")
        assert ei.value.permanent

    def test_recover_all(self):
        r = make_router(mode="live")
        r.inject_failure("step_5", "circuit_open")
        r.recover_all()
        provider, rec = r.route("authoring")
        assert rec.selected == "step_5"
