"""No-network regressions for paid failures and private asset serving."""
import asyncio

import httpx
import pytest
from fastapi import FastAPI


@pytest.mark.parametrize('kind', [
    'BILLING_LOCKED', 'QUOTA_EXHAUSTED', 'AUTH_FAILED',
    'PAID_GENERATION_DISABLED', 'INVALID_REQUEST', 'CIRCUIT_OPEN',
])
@pytest.mark.parametrize('source', ['opening', 'free', 'recommendation'])
def test_nonrecoverable_provider_failure_never_restarts_pipeline(monkeypatch, kind, source):
    calls, state, branch, tasks = run_failed_pipeline(monkeypatch, kind, source)
    assert calls == {'plan': 1, 'narrative': 1, 'production': 1, 'submit': 1}
    assert branch.retry == 0
    assert tasks == {}
    assert branch.status.value == 'FAILED'
    assert branch.fail_stage == 'GENERATING'
    assert kind in branch.last_error
    assert branch.artifact is None
    assert not any(e.type == 'branch_retry' for e in state.events)
    assert sum(e.type == 'branch_failed' for e in state.events) == 1
    assert state.world.version == 1
    assert state.budget.reserved == 0
    if source in ('opening', 'free'):
        assert state.player.status == 'FAILED_RECOVERABLE'


def test_transient_provider_failure_retains_one_bounded_pipeline_retry(monkeypatch):
    calls, state, branch, tasks = run_failed_pipeline(monkeypatch, 'TRANSIENT_PROVIDER_ERROR', 'free')
    assert calls == {'plan': 2, 'narrative': 2, 'production': 2, 'submit': 2}
    assert branch.retry == 1
    assert len(tasks) == 1
    assert all(task.done() for task in tasks.values())
    assert branch.status.value == 'FAILED'
    assert state.player.status == 'FAILED_RECOVERABLE'
    assert sum(e.type == 'branch_retry' for e in state.events) == 1
    assert branch.artifact is None
    assert state.world.version == 1


def test_uncertain_paid_submit_never_restarts_pipeline(monkeypatch):
    calls, state, branch, tasks = run_failed_pipeline(monkeypatch, 'TIMEOUT', 'free', submit_uncertain=True)
    assert calls == {'plan': 1, 'narrative': 1, 'production': 1, 'submit': 1}
    assert branch.retry == 0 and tasks == {}
    assert branch.status.value == 'FAILED'
    assert state.player.status == 'FAILED_RECOVERABLE'
    assert not any(event.type == 'branch_retry' for event in state.events)


def run_failed_pipeline(monkeypatch, kind, source, submit_uncertain=False):
    """Exercise real pipeline state/retry logic with model/network seams disabled."""
    from app.config import settings
    from app.domain.schemas import Branch, BranchSource
    from app.providers.real import FalGenerationError
    from app.runtime.engine import RuntimeEngine

    engine = RuntimeEngine(None)
    state = engine._bootstrap('safety-version', 'safety-scenario', {'title': 'Safety contract'})
    branch = Branch(id='safety-branch', session_id=state.id,
                    arc_id=state.current_arc().id, source=BranchSource(source),
                    label='Inspect the sealed door', base_versions=engine._branch_base_versions(state))
    state.branches.append(branch)
    state.budget.reserved = settings.effective_shots_per_branch * settings.shot_unit_cost
    engine.sessions[state.id] = state
    calls = {'plan': 0, 'narrative': 0, 'production': 0, 'submit': 0}

    async def noop(*args, **kwargs):
        pass

    async def plan(*args):
        calls['plan'] += 1

    async def narrative(*args):
        calls['narrative'] += 1

    async def production(*args):
        calls['production'] += 1

    async def submit(*args):
        calls['submit'] += 1
        raise FalGenerationError(kind, f'classified media failure: {kind}', submit_uncertain=submit_uncertain)

    for method in ('_persist', '_push', '_phase_sleep', '_maybe_publish'):
        monkeypatch.setattr(engine, method, noop)
    monkeypatch.setattr(engine, '_plan_branch', plan)
    monkeypatch.setattr(engine, '_narrate_branch', narrative)
    monkeypatch.setattr(engine, '_shoot_branch', production)
    monkeypatch.setattr(engine, '_generate_branch_media', submit)

    async def run():
        await engine._run_pipeline(state.id, branch.id)
        if engine._pipeline_tasks:
            await asyncio.wait_for(asyncio.gather(*engine._pipeline_tasks.values()), timeout=2)

    asyncio.run(run())
    return calls, state, branch, engine._pipeline_tasks


def test_private_audit_files_never_served_but_public_assets_remain_available(tmp_path):
    from app.main import PublicAssetFiles

    private = tmp_path / '.private'
    private.mkdir()
    private.joinpath('usage-ledger.jsonl').write_text('SECRET_AUDIT_SENTINEL')
    nested = tmp_path / 'assets' / '.private'
    nested.mkdir(parents=True)
    nested.joinpath('trace.json').write_text('SECRET_AUDIT_SENTINEL')
    tmp_path.joinpath('.env').write_text('SECRET_AUDIT_SENTINEL')
    public = tmp_path / 'assets' / 'portrait.png'
    public.write_bytes(b'PUBLIC_IMAGE_SENTINEL')
    app = FastAPI()
    app.mount('/files', PublicAssetFiles(directory=str(tmp_path)), name='test-files')

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            for path in (
                '/files/.private/usage-ledger.jsonl',
                '/files/%2Eprivate/usage-ledger.jsonl',
                '/files/.private%2Fusage-ledger.jsonl',
                '/files/assets/%2E%2E/%2Eprivate/usage-ledger.jsonl',
                '/files/assets/.private/trace.json',
                '/files/.env',
            ):
                for method in ('GET', 'HEAD'):
                    response = await client.request(method, path)
                    assert response.status_code == 404, (method, path, response.status_code)
                    assert 'SECRET_AUDIT_SENTINEL' not in response.text
            response = await client.get('/files/assets/portrait.png')
            assert response.status_code == 200
            assert response.content == b'PUBLIC_IMAGE_SENTINEL'
            assert (await client.head('/files/assets/portrait.png')).status_code == 200

    asyncio.run(run())
