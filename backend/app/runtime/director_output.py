"""Bounded shape repair, without inventing facts or modifying proposed state ops."""
import json
from typing import Literal
from pydantic import BaseModel, Field
from ..domain.schemas import DramaticDirective, OutcomeSpec

class MechanicTrigger(BaseModel):
    skill: Literal["relationship", "clue-system", "inventory"]
    target: str = ""
    action: Literal["add", "remove"] = "add"
    stage: Literal["DISCOVERED", "VERIFIED", "USED"] = "DISCOVERED"
    value: int | None = None

class DirectorOutcome(OutcomeSpec):
    skill_triggers: list[MechanicTrigger] = Field(default_factory=list)

class DirectorOutput(BaseModel):
    outcome: DirectorOutcome
    directive: DramaticDirective

def normalize_director_output(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Director output must be an object")
    directive = data.get("directive")
    if not isinstance(directive, dict):
        raise ValueError("Director directive must be an object")
    directive = dict(directive)
    # The old prompt requested strings while the domain schema requires records.
    # Wrapping a description preserves exactly the model text and adds no facts.
    if isinstance(directive.get("target_changes"), list):
        directive["target_changes"] = [{"description": x} if isinstance(x, str) else x for x in directive["target_changes"]]
    directive["id"] = "validation-only"
    DirectorOutput.model_validate({"outcome": data.get("outcome"), "directive": directive})
    directive.pop("id")
    return {**data, "directive": directive}
