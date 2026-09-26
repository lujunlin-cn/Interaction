"""Versioned agent policies, shared by runtime and offline counterfactuals.

Interpretation remains model work; schemas and policies bound its authority.
These are not extra per-turn agents or extra provider calls.
"""
INTENT_PREVIEW_POLICY = (
    '返回 JSON {action,desire,strategy}，三个字段都是短字符串。先理解玩家原话，供玩家确认。'
    '保留否定和顺序；目的和方式只能提出温和、可修改的推测，不得增加杀人、使用未持有物品等新决定。'
    '无法确定的目标保留原指代，不假装确定；不裁定结果，不生成剧情，不泄密。'
)
CHOICE_POLICY = (
    '每个 label 是一个可执行的具体动作，summary 是玩家看得懂的当前目的，'
    '不要使用机制分类或系统摘要；目的只能基于已知信息，不泄露秘密或尚未识别的实体名称。'
    '承接最近已完成的行动，不把已经解决的事情重新当选项；候选应有不同策略或风险。'
)
CAUSAL_NARRATIVE_POLICY = (
    '另外返回 visual_focus：从已裁定结果中选一个5至10秒能看清的核心可见动作，'
    '不要把移动、调查、保护、判断和下一步计划塞到同一镜头。'
    'text承接玩家行动，说明实际结果或阻碍；不得只重复铺垫，也不得擅自增加下一步决定。'
)
MECHANIC_REPAIR_POLICY = (
    '此前提案与当前状态冲突，请重新裁定同一行动，不能凭空补充物品或改变玩家目标。'
    '使用物品不等于获得物品；未持有时说明受阻，不得伪造持有。只返回完整合法结果。'
)
