"""MockTextProvider —— 确定性的结构化输出，忠实扮演 Director / Narrative / Production / Authoring。

Mock 只替换 Provider 层（模型推理），不替换业务 Runtime。
输出是规则驱动的中文文本，用于离线开发与状态机验证。
"""
from __future__ import annotations

import asyncio
import json
import re

from .base import TextResponse


def _extract(messages: list[dict], key: str, default: str = "") -> str:
    """从 system prompt 的 ```json 块或最后一条 user 消息中取字段。"""
    for m in messages:
        content = m.get("content", "")
        for block in re.findall(r"```json\n?(.*?)```", content, re.S):
            try:
                data = json.loads(block)
                if key in data:
                    return str(data[key])
            except Exception:
                continue
    return default


class MockTextProvider:
    name = "mock_text"
    healthy = True

    async def generate(self, messages, output_contract=None, tools=None, budget=None) -> TextResponse:
        await asyncio.sleep(0.05)  # 模拟一点延迟，保持异步语义
        purpose = (output_contract or {}).get("purpose") or (budget or {}).get("purpose", "")
        content = self._dispatch(purpose, messages, output_contract)
        return TextResponse(content=content, model="mock-text-v1", provider=self.name, latency_ms=50)

    def _dispatch(self, purpose: str, messages, contract) -> str:
        user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if purpose == "director_plan":
            return self._director_plan(user)
        if purpose == "narrative_beat":
            return self._narrative(user)
        if purpose == "production_shots":
            return self._shots(user)
        if purpose == "authoring_draft":
            return self._authoring(user)
        if purpose == "authoring_patch":
            return self._authoring_patch(user)
        if purpose == "new_arc":
            return self._new_arc(user)
        return json.dumps({"text": f"收到：{user[:80]}"}, ensure_ascii=False)

    # ------------------------------------------------------------------
    def _director_plan(self, user: str) -> str:
        """Director 的结构化规划：评估 + Directive + 结果说明。"""
        raw = _extract_from_user(user, "raw_player_input") or user
        outcome = rule_based_outcome(raw)
        directive = {
            "primary_function": "CLOSE_CURRENT_ARC" if outcome["ending"] else
                "REVEAL_INFORMATION" if outcome["evidence"] else
                "DEVELOP_RELATIONSHIP" if outcome["kind"] == "social" else "RESPOND_TO_PLAYER_ACTION",
            "secondary_functions": ["PRESERVE_CONTINUITY"],
            "target_changes": [{
                "dimension": "relationship" if outcome["kind"] == "social" else "information",
                "description": outcome["text"][:120],
                "planned_or_observed": "PLANNED",
            }],
            "hard_constraints": [
                "保留玩家原文中的否定、顺序和策略",
                "核心真相不改写",
                "UNTIMED 思考和模型等待不推进故事时钟",
            ],
            "avoid": ["强拉回固定主线", "未建立的灾难", "把 Wish 当作保证"],
        }
        return json.dumps({"outcome": outcome, "directive": directive}, ensure_ascii=False)

    def _narrative(self, user: str) -> str:
        packet_hint = _extract_from_user(user, "scene_title") or "下一幕"
        text = _extract_from_user(user, "scene_text") or "场景继续推进。"
        caption = _extract_from_user(user, "caption") or text[:60]
        from .fixtures import get as _fixtures
        if _fixtures().get("leak_secret"):
            # 泄密注入（FR-068 验收夹具）：模拟 Narrative 越权揭示未授权真相
            # 文本刻意命中 truth_model 的事实片段，用于驱动 forbidden_revelations 校验
            text += "（原来 Alice 保存的是举报证据。）"
        return json.dumps({
            "title": packet_hint, "text": text, "caption": caption,
            "dialogue": [{"speaker": "alice", "line": caption}],
        }, ensure_ascii=False)

    def _shots(self, user: str) -> str:
        raw = _extract_from_user(user, "raw_player_input") or "行动"
        text = _extract_from_user(user, "scene_text") or raw
        title = _extract_from_user(user, "scene_title") or "行动结果"
        return json.dumps({"shots": [
            {"title": "行动与空间关系", "prompt": f"{title}。{raw}。保持身份、服装、持物与场景连续性。",
             "subtitle": raw, "duration": 5},
            {"title": "人物回应与关键细节", "prompt": f"{title}。{text[:60]}。保持连续性与克制语气。",
             "subtitle": text[:60], "duration": 5},
        ]}, ensure_ascii=False)

    def _authoring(self, user: str) -> str:
        idea = _extract_from_user(user, "idea") or user.strip()
        title = re.sub(r"^(创建|生成|写)(一个|一部)?", "", idea).strip()[:22] or "未命名故事"
        suspense = bool(re.search(r"悬疑|秘密|真相|失踪|谋杀|档案", idea))
        draft = {
            "title": title,
            "description": idea[:300],
            "genre": "悬疑" if suspense else "剧情",
            "tone": "克制、细节驱动",
            "play_style": "自由调查 / 角色对话 / 可主动退出",
            "world": {
                "rules": "现代现实世界；人物只能使用持有的物品；玩家决定行动，不代替玩家承诺。",
                "lore": f"创作想法：{idea}",
                "locations": "main｜主要场景\nback｜次要场景",
                "constraints": "核心真相不可改写；UNTIMED 现实思考不推进故事时钟。",
            },
            "drama": {
                "core_question": "在这个故事中，谁的解释可信，玩家愿意为真相付出什么？" if suspense
                    else "面对彼此冲突的目标，玩家会作出怎样的选择？",
                "central_conflict": "由创作想法衍生的角色目标冲突：个人愿望、关系边界与世界规则。",
                "truth_model": "fact_main：草案生成时确立的稳定真相，需在审阅中确认。",
                "secrets": "关键信息尚未向玩家揭示。",
                "misbeliefs": "角色可能存在误解；这仅是假设，不是玩家真实信念。",
                "pressures": "external_clock｜外部时间表｜故事时间推进",
                "anchors": "关键会面；证据出现；作出是否参与的决定。",
                "ending_families": "truth_revealed｜揭示真相\nquiet_exit｜玩家主动退出",
                "foreshadows": "",
                "forbidden_outcomes": "不得让已确认死亡的角色无因果复活。",
            },
        }
        return json.dumps(draft, ensure_ascii=False)

    def _authoring_patch(self, user: str) -> str:
        instruction = _extract_from_user(user, "instruction") or ""
        current = _extract_from_user(user, "current") or ""
        after = re.sub(r"^(改为|改成|设置为)[：:]?", "", instruction).strip()
        if not after or after == instruction:
            after = f"{current}\n{instruction}".strip()
        return json.dumps({"after": after}, ensure_ascii=False)

    def _new_arc(self, user: str) -> str:
        return json.dumps({
            "question": "上一篇章结束后，你们将如何面对这些事实？",
            "conflict": "新的生活边界与仍然相关的未结事项之间的冲突。",
        }, ensure_ascii=False)

    async def health(self) -> bool:
        return self.healthy


def _extract_from_user(user: str, key: str) -> str:
    m = re.search(rf"{key}[：:]\s*(.+)", user)
    return m.group(1).strip() if m else ""


def rule_based_outcome(raw: str, mechanics: dict | None = None) -> dict:
    """确定性意图→结果规则（移植自高保真原型的演示规则）。

    这是 Mock Provider 的领域规则部分：在真实模型接入前，让状态机与验收路径可运行。
    """
    ops: list[dict] = []
    evidence: list[str] = []
    text: list[str] = []
    title = "你的行动"
    ending = None
    kind = "investigation"
    mode = "FULL_BEAT"

    def mech_enabled(name: str) -> bool:
        if mechanics is None:
            return True
        return bool(mechanics.get(name, {}).get("enabled", False))

    if re.search(r"激光炮|瞬间移动|复活|飞天", raw):
        return {
            "title": "一次不可能的尝试",
            "text": "你摸向口袋，里面并没有那样的道具。你可以继续表达自己的目的，但这个世界的规则没有改变。",
            "ops": [], "evidence": [], "ending": None, "kind": "investigation", "mode": "QUICK_ACK",
        }
    if re.search(r"(?:退出|离城|转身离开|彻底离开)", raw) and "假装" not in raw:
        ops.append({"op": "set", "path": "location", "value": "street"})
        ending = "voluntary_departure"
        title = "雨中离去"
        text.append("你离开了公寓，不再参与眼前的矛盾。Alice 的离开计划仍然成立；你没有被额外的灾难强行拉回。")
        kind = "withdrawal"
    elif re.search(r"(?:等一小时|等待一小时|睡到明天)", raw):
        ops += [{"op": "increment", "path": "fiction_minutes", "value": 60},
                {"op": "set", "path": "objects.alice_departure", "value": "departed"}]
        title = "你选择等待"
        text.append("你明确决定等一小时。Alice 按原先的车票离开；这不是现实思考或生成等待造成的惩罚。")
        kind = "withdrawal"
    elif re.search(r"公开证据|结束这段|告别她|告别|给出结局", raw):
        ending = "truth_or_farewell"      # 具体 family 由 Director 在上下文里解析
        title = "收束这段矛盾"
        text.append("你作出了收束当前矛盾的选择。系统将根据你实际掌握的证据形成相应的结局。")
    elif re.search(r"真相|重新理解|揭示反转", raw):
        title = "线索的另一种含义"
        evidence.append("truth_revealed")
        text.append("已有线索相互印证，你开始重新理解眼前的一切。真相未改变，改变的是你现在掌握的解释。")
    elif "录音" in raw:
        title = "关键录音"
        if mech_enabled("inventory"):
            ops.append({"op": "addItem", "value": "Evidence Recording"})
        if mech_enabled("clue-system"):
            ops.append({"op": "set", "path": "clues.recording_found", "value": "DISCOVERED"})
        ops.append({"op": "set", "path": "objects.recording", "value": "found"})
        evidence.append("recording_found")
        text.append("你找到一段标有举报预约的录音。它与 Alice 的离城安排有关，但你仍需结合已有线索判断。")
    elif "钥匙" in raw and re.search(r"给我|获得|拿起|交给|索要|请求", raw):
        title = "钥匙的交付"
        if mech_enabled("inventory"):
            ops.append({"op": "addItem", "value": "Apartment Key"})
        evidence.append("key_scratches")
        text.append("Alice 允许你暂时保管公寓钥匙。你留意到钥匙齿边反复摩擦留下的划痕。")
    elif "钥匙" in raw:
        title = "钥匙上的划痕"
        evidence.append("key_scratches")
        if mech_enabled("clue-system"):
            ops.append({"op": "set", "path": "clues.key_scratches", "value": "DISCOVERED"})
        text.append("你观察她手中的旧钥匙。齿边有规律的磨损，更像经常打开某个旧柜子，而不是撬锁。")
    elif re.search(r"外套|安慰|保护她|递给", raw):
        title = "一次温和的靠近"
        kind = "social"
        care = 9
        if mechanics and mechanics.get("relationship", {}).get("config"):
            care = int(mechanics["relationship"]["config"].get("care_delta", 9))
        if mech_enabled("relationship"):
            ops.append({"op": "increment", "path": "relationships.alice", "value": care})
        if "外套" in raw and mech_enabled("inventory"):
            ops += [{"op": "removeItem", "value": "Coat"},
                    {"op": "set", "path": "objects.alice_visual", "value": "深色风衣，披上玩家递来的灰色外套"}]
        text.append("Alice 接受了你的关心。她是否进一步解释，仍取决于自己的目标和已经建立的信任。")
    elif re.search(r"后门|假装离开|后院", raw):
        title = "后门的视角"
        ops.append({"op": "set", "path": "location", "value": "backyard"})
        evidence.append("train_ticket")
        text.append("你没有跟她走正门，而是按自己的计划绕到后院。隔着窗户，你看到她收起一张午夜车票。她尚未察觉你的怀疑。")
    elif re.search(r"空抽屉|看一下抽屉", raw):
        title = "空抽屉"
        text.append("抽屉里只有旧纸屑，没有关键发现。这个动作已记录，不需要生成新视频。")
        mode = "QUICK_ACK"
        ops.append({"op": "inspect", "value": "drawer"})
    elif re.search(r"检查桌子|检查柜子|检查窗户|检查书架|检查", raw):
        title = "探索中的小动作"
        text.append("你完成了检查，没有越过需要另作决定的关键点。这个动作可以与其他检查汇总。")
        mode = "QUICK_ACK"
        ops.append({"op": "inspect", "value": raw})
    elif re.search(r"闪避|抓住手腕|后退", raw):
        title = "躲开突发动作"
        kind = "risk"
        text.append("你及时作出反应，躲开了突发动作。结果来自已准备好的限时分支，而非模型响应速度。")
    else:
        text.append(f"你选择：“{raw}”。场景按照这个新的行动展开；Alice 结合当前信任作出谨慎回应。")
    # 开发夹具：响应模式覆盖（Prototype Controls）
    from .fixtures import get as _fixtures
    override = _fixtures().get("response", "auto")
    if override == "quick":
        mode = "QUICK_ACK"
    elif override == "full":
        mode = "FULL_BEAT"
    elif override == "merged" and kind == "investigation" and not ending:
        mode = "QUICK_ACK"   # 合并过渡由 Runtime 的 merge_buffer 汇总产生
    return {"title": title, "text": " ".join(text), "ops": ops, "evidence": evidence,
            "ending": ending, "kind": kind, "mode": mode}
