"""内置 Scenario：雨夜公寓（移植自高保真原型的 sampleScenario）。"""
from __future__ import annotations

from ..domain.schemas import (
    DramaSpec, MechanicConfig, ScenarioCharacter, ScenarioDraft, ThemeConfig, WorldSpec,
)


def rainy_apartment() -> ScenarioDraft:
    return ScenarioDraft(
        id="rainy_apartment",
        title="雨夜公寓",
        description="午夜前，Alice 准备离开公寓。走廊的脚步声、磨损的钥匙和一段尚未找到的录音，"
                    "指向同一件旧事。你扮演邻居，自行决定信任、调查或离开。",
        genre="悬疑",
        tone="克制、细节驱动、允许安静的关系发展",
        play_style="自由调查 / 角色对话 / 可主动退出",
        player_character="player",
        status="PUBLISHED",
        version="1.0.0",
        owner="official",
        world=WorldSpec(
            rules="现代现实世界；无超自然复活；人物只能使用持有的物品；玩家决定行动，不代替玩家承诺。",
            lore="午夜的公寓仍在停电检修。Alice 已提前买好离城车票。",
            locations="foyer｜公寓门厅\nroom｜302 房间\nbackyard｜后院\nstreet｜街道",
            constraints="核心真相不可改写；UNTIMED 现实思考不推进故事时钟。",
        ),
        characters=[
            ScenarioCharacter(
                id="player", identity="玩家 / Alice 的邻居", personality="由玩家行动塑造",
                desire="由玩家表达，不替其决定", fear="未知", secrets="无预设秘密",
                knowledge="Alice 将在午夜离开", relationship="Alice 信任 42 / 100",
                visual_state="灰色外套，未受伤"),
            ScenarioCharacter(
                id="alice", identity="Alice / 即将离城的档案修复师",
                personality="谨慎、温柔、不轻易交付信任",
                desire="安全离开，并保护证据", fear="证据被销毁、他人因她卷入危险",
                secrets="她保存录音，是为了举报而非灭证",
                knowledge="知道录音的真实来源；不知道玩家下一步计划",
                relationship="对玩家信任 42 / 100",
                visual_state="深色风衣、手持旧钥匙、衣袖有雨水",
                global_character_id="chr_alice", global_character_version=1),
        ],
        drama=DramaSpec(
            core_question="Alice 是否值得信任，而你愿意为真相承担什么？",
            central_conflict="调查真相与尊重 Alice 的边界之间的冲突。",
            truth_model="fact_recording：Alice 保存的是举报证据，并非犯罪指令。\n"
                        "fact_key：钥匙上的划痕来自反复打开旧档案柜。\n"
                        "fact_departure：Alice 已购买午夜离城车票。",
            secrets="录音的用途尚未向玩家揭示；房东知道旧档案柜的位置。",
            misbeliefs="玩家可能怀疑 Alice 在销毁证据；这仅是假设，不是玩家真实信念。",
            pressures="警方调查｜警方已约定查访｜行动触发\nAlice 离开计划｜午夜车票｜故事时间推进",
            anchors="见到行李；发现钥匙划痕；得到或放弃录音；作出是否参与的决定。",
            ending_families="truth_and_trust｜公开证据且保全关系\n"
                            "voluntary_departure｜玩家主动退出\n"
                            "quiet_farewell｜未揭开全部秘密但达成告别",
            foreshadows="key_scratches｜作者预埋，需呈现\ntrain_ticket｜作者预埋，需呈现",
            forbidden_outcomes="不得让已经确认死亡的人无因果复活；不得凭空制造绑架把退出的玩家拉回主线。",
            # 限时互动声明（I02/I03）：id｜kind｜超时秒｜超时确定性结果（Scenario 预先声明）
            timed_interactions="doorbell_urgent｜urgent_dialogue｜30｜保持沉默，Alice 自己应对了门外的查访",
        ),
        mechanics={
            "relationship": MechanicConfig(enabled=True, config={"care_delta": 9, "min": 0, "max": 100}),
            "clue-system": MechanicConfig(enabled=True, config={"states": ["DISCOVERED", "VERIFIED", "USED"]}),
            "inventory": MechanicConfig(enabled=True, config={"capacity": 8}),
            "qte": MechanicConfig(enabled=True, config={
                "timeout_seconds": 3, "qte_fallback": "qte_failure", "dialogue_fallback": "silence"}),
        },
        theme=ThemeConfig(),
        reviewed=True,
    )
