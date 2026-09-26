"""Research envelope around existing runtime contracts; null means unobserved."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict

class TrajectoryTurn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    schema_version: Literal['1.0.0']
    scenario_id: str | None
    scenario_version: str | None
    session_id: str
    arc_id: str | None
    turn_id: str
    record_kind: Literal['player_turn','opening','speculative_branch']
    provenance: Literal['real_provider_observed','mixed','mock_or_fixture','unknown']
    player: dict[str,Any]
    context: dict[str,Any]
    intent: dict[str,Any] | None
    jev: dict[str,Any]
    director: dict[str,Any]
    narrative: dict[str,Any]
    skills: dict[str,Any]
    state: dict[str,Any]
    production: dict[str,Any]
    branch: dict[str,Any]
    player_output: dict[str,Any]
    metrics: dict[str,Any]
    timeline: list[dict[str,Any]]
    missing_observability: list[str]
