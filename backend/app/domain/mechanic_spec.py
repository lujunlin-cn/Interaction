"""Authoring boundary for the four installed mechanic skills. No executable input."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

class RelationshipConfig(StrictConfig):
    care_delta: int = Field(default=9, ge=-100, le=100)
    min: Literal[0] = 0
    max: Literal[100] = 100
    show_values: bool = False
    show_panel: bool = True

class ClueConfig(StrictConfig):
    states: list[Literal["DISCOVERED", "VERIFIED", "USED"]] = Field(default_factory=lambda: ["DISCOVERED", "VERIFIED", "USED"])
    show_panel: bool = True
    allow_review: bool = True

class InventoryConfig(StrictConfig):
    capacity: int = Field(default=8, ge=1, le=100)
    show_panel: bool = True

class QteConfig(StrictConfig):
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    trigger_after_actions: int = Field(default=1, ge=1, le=100)
    trigger_location_ids: list[str] = Field(default_factory=list)
    qte_fallback: Literal["qte_failure"] = "qte_failure"
    dialogue_fallback: Literal["silence"] = "silence"

CONFIGS = {"relationship": RelationshipConfig, "clue-system": ClueConfig,
           "inventory": InventoryConfig, "qte": QteConfig}
CONTRACTS = {
    "relationship": ("人物关系", "角色会记住你如何对待他们，影响以后的帮助与交流。", "角色互动", ["relationships.*"]),
    "clue-system": ("调查与线索", "检查环境、物品和询问人物，可以发现并核实线索。", "调查或询问", ["clues.*"]),
    "inventory": ("道具", "重要物品可以保存，在之后的场景再次使用。", "获得或使用物品", ["addItem", "removeItem"]),
    "qte": ("紧张时刻", "危险场景需要在有限时间内决定，超时按已设定的结果继续。", "故事声明的限时事件", ["TimedInteractionRequest"]),
}

def location_names(locations: str) -> dict[str, str]:
    """Use the same stable location IDs as canonical WorldState."""
    names = {}
    for line in locations.splitlines():
        parts = [part.strip() for part in line.split("｜", 1)]
        if parts[0]:
            names[parts[0]] = parts[1] if len(parts) == 2 else parts[0]
    return names


def validate_mechanics(mechanics: dict, locations: str | None = None) -> dict:
    from .schemas import MechanicConfig
    out = {}
    for key, raw in mechanics.items():
        if key not in CONFIGS:
            raise ValueError(f"不支持的玩法：{key}")
        item = raw.model_dump() if isinstance(raw, MechanicConfig) else raw
        spec = MechanicConfig.model_validate(item)
        spec.config = CONFIGS[key].model_validate(spec.config).model_dump()
        if key == "qte" and locations is not None:
            unknown = set(spec.config["trigger_location_ids"]) - location_names(locations).keys()
            if unknown:
                raise ValueError("限时玩法触发地点不存在，请从当前故事地点中选择：" + "、".join(sorted(unknown)))
        title, tutorial, trigger, permissions = CONTRACTS[key]
        spec.skill_id, spec.version = key, "1.0.0"
        spec.title, spec.tutorial = title, spec.tutorial or tutorial
        spec.trigger, spec.state_patch_contract = trigger, permissions
        out[key] = spec
    return out
