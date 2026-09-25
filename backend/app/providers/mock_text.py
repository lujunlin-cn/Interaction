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
        if purpose == "candidate_actions":
            return self._candidates(user)
        if purpose == "director_plan":
            return self._director_plan(user)
        if purpose == "narrative_beat":
            return self._narrative(user, contract)
        if purpose == "production_shots":
            return self._shots(user, (contract or {}).get("shot_policy"))
        if purpose == "mechanic_projection":
            from ..domain.mechanic_spec import CONTRACTS
            data = json.loads(user)
            words = {"relationship": ["人物", "角色", "撒谎", "关系"], "clue-system": ["调查", "线索", "询问"], "inventory": ["物品", "道具", "背包"], "qte": ["追逐", "快速", "紧张"]}
            return json.dumps({"summary": data["intent"], "mechanics": {k: {"enabled": any(w in data["intent"] for w in words[k]), "config": {}, "tutorial": v[1]} for k, v in CONTRACTS.items()}, "timed_event": {"id": "urgent_choice", "kind": "qte", "timeout_seconds": 10, "fallback": "没有及时选择，错过眼前的机会"}}, ensure_ascii=False)
        if purpose == "creator_projection":
            return self._projection(json.loads(user))
        if purpose == "character_understanding":
            return json.dumps({"personality": "谨慎而细心", "default_desire": "找到值得信赖的伙伴", "appearance": "实用的日常外套"}, ensure_ascii=False)
        if purpose == "authoring_draft":
            return self._authoring(user)
        if purpose == "authoring_patch":
            return self._authoring_patch(user)
        if purpose == "new_arc":
            return self._new_arc(user)
        return json.dumps({"text": f"收到：{user[:80]}"}, ensure_ascii=False)

    # ------------------------------------------------------------------
    def _candidates(self, user: str) -> str:
        """Mock 候选生成：按 scenario_context 参数化，不绑定具体故事语义。

        Runtime 端会再做一次确定性兜底；这里给出带场景名词的候选，
        让 Mock 模式下推荐也体现 Scenario 内容（可测试、可演示）。
        """
        ctx: dict = {}
        raw = _extract_from_user(user, "scenario_context")
        if raw:
            try:
                ctx = json.loads(raw)
            except Exception:
                ctx = {}
        loc_name = ctx.get("location_name") or ctx.get("location") or "当前位置"
        npcs = ctx.get("npcs") or []
        npc_name = (npcs[0].get("identity") or npcs[0].get("id")) if npcs else None
        npc_name = str(npc_name).split(" /")[0] if npc_name else None
        locs = ctx.get("locations") or {}
        cur = ctx.get("location")
        others = [v for k, v in locs.items() if k != cur]
        cands = [
            {"label": f"仔细观察{loc_name}的细节", "summary": "先收集眼前可观察的信息",
             "kind": "investigation", "confidence": 0.68},
        ]
        if npc_name:
            cands.append({"label": f"和{npc_name}谈谈", "summary": "让关系自然流动",
                          "kind": "social", "confidence": 0.64})
        if ctx.get("clues"):
            cands.append({"label": "梳理目前掌握的线索", "summary": "已有线索也许指向同一个方向",
                          "kind": "investigation", "confidence": 0.6})
        if others:
            cands.append({"label": f"离开这里，去{others[-1]}",
                          "summary": "主动改变自己所处的位置",
                          "kind": "withdrawal", "confidence": 0.55})
        else:
            cands.append({"label": "主动退出眼前的故事", "summary": "不再参与眼前的矛盾",
                          "kind": "withdrawal", "confidence": 0.55})
        return json.dumps({"candidates": cands}, ensure_ascii=False)

    def _director_plan(self, user: str) -> str:
        """Director 的结构化规划：评估 + Directive + 结果说明。"""
        raw = _extract_from_user(user, "raw_player_input") or user
        ctx: dict = {}
        ctx_raw = _extract_from_user(user, "scenario_context")
        if ctx_raw:
            try:
                # scenario_context 是单行 json.dumps，但其后可能跟中文 schema_hint 等
                # 非「key:」行——正则边界只认 [a-zA-Z_]:，会把尾巴吞进来。
                # raw_decode 只取首个完整 JSON 对象，丢弃被污染的尾部。
                ctx, _ = json.JSONDecoder().raw_decode(ctx_raw.strip())
                if not isinstance(ctx, dict):
                    ctx = {}
            except Exception:
                ctx = {}
        outcome = rule_based_outcome(raw, context=ctx)
        if raw.strip() == "opening":
            outcome.update(ops=[], evidence=[], skill_triggers=[], ending=None, kind="opening")
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

    def _narrative(self, user: str, contract: dict | None = None) -> str:
        packet_hint = _extract_from_user(user, "scene_title") or "下一幕"
        text = _extract_from_user(user, "scene_text") or "场景继续推进。"
        caption = _extract_from_user(user, "caption") or text[:60]
        brief = (contract or {}).get("scenario_brief") or {}
        npcs = brief.get("npcs") or []
        speaker = str(npcs[0].get("id")) if npcs else "npc"
        from .fixtures import get as _fixtures
        if _fixtures().get("leak_secret"):
            # 泄密注入（FR-068 验收夹具）：模拟 Narrative 越权揭示未授权真相。
            # 从 scenario_brief.truth_model 取首个事实片段注入（Runtime 会做
            # forbidden_revelations 校验 → 任何 Scenario 都会命中泄密拦截）。
            leak_seg = "某个未授权的真相"
            truth_model = brief.get("truth_model") or ""
            for line in truth_model.splitlines():
                if "：" in line:
                    value = line.split("：", 1)[1].strip()
                    for seg in re.split(r"[，。；、,.;！？\s]+", value):
                        seg = seg.strip()
                        # 与 engine._forbidden_hits 的 ≥6 阈值保持一致，
                        # 确保注入片段一定能被泄密校验命中。
                        if len(seg) >= 6:
                            leak_seg = seg
                            break
                    if leak_seg != "某个未授权的真相":
                        break
            text += f"（原来{leak_seg}。）"
        return json.dumps({
            "title": packet_hint, "text": text, "caption": caption,
            "dialogue": [{"speaker": speaker, "line": caption}],
        }, ensure_ascii=False)

    def _shots(self, user: str, policy: dict | None = None) -> str:
        raw = _extract_from_user(user, "raw_player_input") or "行动"
        text = _extract_from_user(user, "scene_text") or raw
        title = _extract_from_user(user, "scene_title") or "行动结果"
        shots = [
            {"title": "行动与空间关系", "prompt": f"{title}。{raw}。保持身份、服装、持物与场景连续性。",
             "subtitle": raw, "duration": 5},
            {"title": "人物回应与关键细节", "prompt": f"{title}。{text[:60]}。保持连续性与克制语气。",
             "subtitle": text[:60], "duration": 5},
        ]
        if policy:
            count = int(policy.get("count", 2))
            shots = [{**shots[i % len(shots)], "duration": policy.get("target", 5)} for i in range(count)]
        return json.dumps({"shots": shots}, ensure_ascii=False)

    def _projection(self, request):
        draft = request["draft"]
        scope = request["scope"]
        items = []
        if scope == "mechanics":
            from ..domain.mechanic_spec import CONTRACTS
            instruction = request["instruction"]
            words = {"relationship": ["人物", "角色", "撒谎", "关系"], "clue-system": ["调查", "线索", "询问"], "inventory": ["物品", "道具", "背包"], "qte": ["追逐", "快速", "紧张"]}
            for key, (title, tutorial, _, _) in CONTRACTS.items():
                enabled = any(w in instruction for w in words[key])
                items.append({"path": "mechanics." + key, "summary": tutorial, "value": {"enabled": enabled, "config": {}, "tutorial": tutorial}})
            if any(w in instruction for w in words["qte"]):
                items.append({"path": "drama.timed_interactions", "summary": "紧张时刻限时决定，超时错过机会", "value": "urgent_choice｜qte｜10｜没有及时决定，错过眼前的机会"})
        else:
            for path in request["allowed_paths"]:
                if scope == "drama":
                    value = draft["drama"].get(path.split(".")[-1], "")
                else:
                    m = re.match(r"characters\[(\d+)\]\.(.*)", path)
                    value = draft["characters"][int(m[1])].get(m[2], "") or f"围绕{draft['title']}，谨慎寻找事情的答案"
                item = {"path": path, "value": value, "summary": re.sub(r"\b[a-z_]+[：｜]", "", value) or "可选内容，暂时留白"}
                if scope == "drama" and path in ("drama.truth_model", "drama.central_conflict") and len(request["original_story"]) < 40:
                    item["question"] = f"{draft['title']}中，你更希望故事朝哪个方向发展？"
                    item["suggestions"] = [{"label": f"{draft['title']}：{choice}", "value": ("fact_main：" if path.endswith("truth_model") else "") + choice} for choice in ("失踪者在保护某个人", "关键证人隐瞒了一段过去", "大家对同一件事有不同理解")]
                items.append(item)
        return json.dumps({"summary": f"故事围绕{draft['title']}展开。{request['original_story']}", "items": items}, ensure_ascii=False)

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
            "characters": [
                {"id": "player", "identity": "玩家扮演的调查者",
                 "personality": "冷静、观察细致",
                 "desire": "弄清眼前这件事的真相", "fear": "被卷入无法脱身的局面"},
                {"id": "npc_main", "identity": "与谜团相关的关键人物",
                 "personality": "防备、话里有话",
                 "desire": "保护自己真正在意的东西", "secrets": "知道核心真相的一部分"},
            ],
        }
        return json.dumps(draft, ensure_ascii=False)

    def _authoring_patch(self, user: str) -> str:
        """G16：instruction → typed patches[{path,before,after,reason}]。

        常见句式映射：
        - 「把核心问题改成X」→ drama.core_question
        - 「把标题改成X」→ title
        - 「把背景改成X」→ world.lore
        其他 → description 追加。
        """
        instruction = _extract_from_user(user, "instruction") or ""
        patches: list[dict] = []
        m = re.search(r"把(.+?)(?:改成|改为|设置为|设为)[：:](.+)$", instruction)
        if m:
            field_map = {
                "核心问题": "drama.core_question", "中心冲突": "drama.central_conflict",
                "真相": "drama.truth_model", "真相模型": "drama.truth_model",
                "标题": "title", "简介": "description", "描述": "description",
                "背景": "world.lore", "世界观": "world.rules", "规则": "world.rules",
                "基调": "tone", "类型": "genre",
            }
            target = field_map.get(m.group(1).strip())
            if target:
                patches.append({"path": target, "after": m.group(2).strip(),
                                "reason": instruction[:80]})
        if not patches:
            after = re.sub(r"^(改为|改成|设置为)[：:]?", "", instruction).strip()
            patches.append({"path": "description",
                            "after": after if after != instruction else instruction,
                            "reason": instruction[:80]})
        return json.dumps({"patches": patches}, ensure_ascii=False)

    def _new_arc(self, user: str) -> str:
        return json.dumps({
            "question": "上一篇章结束后，你们将如何面对这些事实？",
            "conflict": "新的生活边界与仍然相关的未结事项之间的冲突。",
        }, ensure_ascii=False)

    async def health(self) -> bool:
        return self.healthy


def _extract_from_user(user: str, key: str) -> str:
    """从 user 消息取「key: value」字段；value 直到下一个行首「key:」或文本结束。

    行首锚定 + 引号排除：JSON 值里的 "location": 不会被误认为字段名。
    """
    m = re.search(rf"(?:^|\n){key}[：:]\s*(.+?)(?=\n[a-zA-Z_]+[：:]|\Z)", user, re.S)
    return m.group(1).strip() if m else ""


def rule_based_outcome(raw: str, mechanics: dict | None = None,
                       context: dict | None = None) -> dict:
    """确定性意图→结果规则（移植自高保真原型的演示规则）。

    这是 Mock Provider 的领域规则部分：在真实模型接入前，让状态机与验收路径可运行。
    context 为 Runtime 传入的 Scenario 摘要（locations/characters/ending_families 等），
    规则命中失败时按 context 产出通用结果，保证 Scenario 泛化。
    """
    context = context or {}
    npcs = context.get("npcs") or []
    first_npc = str((npcs[0].get("identity") or npcs[0].get("id")) or "在场的人"
                    ).split(" /")[0] if npcs else "在场的人"
    first_npc_id = str(npcs[0].get("id")) if npcs else "npc"
    loc_names = context.get("locations") or {}
    ending_families = context.get("ending_families") or {}
    cur_loc = context.get("location", "")
    other_locs = [k for k in loc_names if k != cur_loc]
    leave_loc = other_locs[-1] if other_locs else "elsewhere"
    leave_name = loc_names.get(leave_loc, "别处")
    ending_ids = list(ending_families.keys())
    ending_departure = next((e for e in ending_ids
                             if "departure" in e or "exit" in e or "leave" in e),
                            ending_ids[-1] if ending_ids else None)
    ending_resolve = next((e for e in ending_ids
                           if "truth" in e or "reveal" in e or "farewell" in e),
                          ending_ids[0] if ending_ids else None)

    ops: list[dict] = []
    skill_triggers: list[dict] = []
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

    # --- 通用规则（Scenario 无关）：不可能尝试 / 主动退出 / 收束 / 检查 / 闪避 ---
    if re.search(r"激光炮|瞬间移动|复活|飞天", raw):
        return {
            "title": "一次不可能的尝试",
            "text": "你摸向口袋，里面并没有那样的道具。你可以继续表达自己的目的，但这个世界的规则没有改变。",
            "ops": [], "evidence": [], "ending": None, "kind": "investigation", "mode": "QUICK_ACK",
        }
    if re.search(r"(?:退出|离城|转身离开|彻底离开|离开这里)", raw) and "假装" not in raw:
        ops.append({"op": "set", "path": "location", "value": leave_loc})
        ending = ending_departure
        title = "你选择离开"
        text.append(f"你离开了当前位置，前往{leave_name}，不再参与眼前的矛盾。"
                    "故事的其他部分仍然按自己的逻辑运转；你没有被额外的灾难强行拉回。")
        kind = "withdrawal"
    elif re.search(r"(?:等一小时|等待一小时|睡到明天)", raw):
        ops.append({"op": "increment", "path": "fiction_minutes", "value": 60})
        title = "你选择等待"
        text.append("你明确决定等一小时。故事按自己的时间表继续推进；"
                    "这不是现实思考或生成等待造成的惩罚。")
        kind = "withdrawal"
    elif re.search(r"公开证据|结束这段|告别|给出结局|做出最终选择", raw):
        ending = ending_resolve      # 具体 family 由 Scenario 声明解析
        title = "收束这段矛盾"
        text.append("你作出了收束当前矛盾的选择。系统将根据你实际掌握的证据形成相应的结局。")
    elif re.search(r"真相|重新理解|揭示反转", raw):
        title = "线索的另一种含义"
        evidence.append("truth_revealed")
        text.append("已有线索相互印证，你开始重新理解眼前的一切。真相未改变，改变的是你现在掌握的解释。")
    # --- 以下为「雨夜公寓」内置 Scenario 的特化演示规则（仅在该 Scenario 的语义下命中） ---
    elif "录音" in raw:
        title = "关键录音"
        if mech_enabled("inventory"):
            skill_triggers.append({"skill": "inventory", "action": "add",
                                   "target": "Evidence Recording"})
        if mech_enabled("clue-system"):
            skill_triggers.append({"skill": "clue-system",
                                   "target": "recording_found", "stage": "DISCOVERED"})
        ops.append({"op": "set", "path": "objects.recording", "value": "found"})
        evidence.append("recording_found")
        text.append(f"你找到一段标有举报预约的录音。它与{first_npc}的计划有关，但你仍需结合已有线索判断。")
    elif "钥匙" in raw and re.search(r"给我|获得|拿起|交给|索要|请求", raw):
        title = "钥匙的交付"
        if mech_enabled("inventory"):
            skill_triggers.append({"skill": "inventory", "action": "add",
                                   "target": "Apartment Key"})
        evidence.append("key_scratches")
        text.append(f"{first_npc}允许你暂时保管那把钥匙。你留意到钥匙齿边反复摩擦留下的划痕。")
    elif "钥匙" in raw:
        title = "钥匙上的划痕"
        evidence.append("key_scratches")
        if mech_enabled("clue-system"):
            skill_triggers.append({"skill": "clue-system",
                                   "target": "key_scratches", "stage": "DISCOVERED"})
        text.append("你观察那把旧钥匙。齿边有规律的磨损，更像经常打开某个旧柜子，而不是撬锁。")
    elif re.search(r"外套|安慰|保护|递给", raw):
        title = "一次温和的靠近"
        kind = "social"
        care = 9
        if mechanics and mechanics.get("relationship", {}).get("config"):
            care = int(mechanics["relationship"]["config"].get("care_delta", 9))
        if mech_enabled("relationship"):
            skill_triggers.append({"skill": "relationship",
                                   "target": first_npc_id, "value": care})
        if "外套" in raw:
            if mech_enabled("inventory"):
                skill_triggers.append({"skill": "inventory", "action": "remove",
                                       "target": "Coat"})
            ops.append({"op": "set", "path": f"objects.{first_npc_id}_visual",
                        "value": "深色风衣，披上玩家递来的灰色外套"})
        text.append(f"{first_npc}接受了你的关心。TA 是否进一步解释，仍取决于自己的目标和已经建立的信任。")
    elif re.search(r"后门|假装离开|后院", raw):
        title = "后门的视角"
        if "backyard" in loc_names:
            ops.append({"op": "set", "path": "location", "value": "backyard"})
        evidence.append("train_ticket")
        text.append(f"你没有跟{first_npc}走正门，而是按自己的计划绕到后院。"
                    "隔着窗户，你看到 TA 收起一张午夜车票。TA 尚未察觉你的怀疑。")
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
        # 通用兜底：Scenario 无关，不产出硬编码实体（G07）
        text.append(f"你选择：“{raw}”。场景按照这个新的行动展开；"
                    f"{first_npc}结合当前的状态作出谨慎回应。")
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
            "ending": ending, "kind": kind, "mode": mode,
            "skill_triggers": skill_triggers}
