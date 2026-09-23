# 现场演示脚本 · 互动短剧（PRD §18.2 落地版）

部署：`http://139.199.69.46:9000`，`provider_mode=hybrid`，
`profile=AGENT_LOCAL_PROFILE`。演示前 `curl /api/health` 确认在线；
`GET /api/dev/providers` 确认各角色 `selected` 符合预期。

> 真实性纪律：预制/缓存内容明确标注；不拼其他会话补成功；不改真相；
> 玩家界面只讲自然中文，技术状态只在开发者模式展示。

## 演示动线

| # | 动作 | 操作 | 证明什么 | 备注 |
| --- | --- | --- | --- | --- |
| D0 | 模型路由预览 | 开发者模式 → 模型路由 tab | 六类 Provider 健康矩阵 + 各角色 fallback 链真实在跑 | `dev_router.png` 已留证 |
| D1 | 创作 | 侧边栏「＋ 创建故事」→ 输入一句 idea → 概览页看 AI 草案 → 局部改一个字段 | 不手写分支树即得结构化草案（core_question/truth_model/pressure/ending_family） | AT-01/43 |
| D1b | 角色制作 | 角色库 → 一句描述 → 2 张 Candidate → 选 Canonical → 换装 Edit | Character Studio 闭环（v0.6 P0） | nano-banana-2 真实调用，耗 fal 配额——配额紧时展示已有 Candidate + 说明来源 |
| D2 | 素材 | 素材页上传图/声/视频 → 绑定角色 ref_* | 三模态 references 进生成请求不静默丢 | 开发者模式展示 request references |
| D3 | 开场 | 故事库 → 雨夜公寓 → 进入游玩 | 明确入口与角色；开场视频播放 | 预制开场标「预先准备」 |
| D4 | 命中 | 等推荐面板出现 → 点任一 READY 候选 | Ready Gate：显示即可播放，点击不重复生成 | Trace 可看候选 Ready 时间 |
| D5 | 自由行动 | 输入「我找到那段录音」→（Jev 低置信先回显确认）→ 确认 → 等新 Beat | 开放路径真实生成新视频；Jev INTENT_ECHO/CLARIFICATION 真实回显 | 已实测：`skill.inventory`+`skill.clue-system` 落 world |
| D5b | 小动作 | 输入「检查桌子」 | QUICK_ACK 不伪造视频任务 | 与关键行动分流 |
| D6 | 许愿/机制 | 玩家面板提交「希望平安离开这里」→ 后续行动推进 | Wish 入 Ledger，机制事件产 StatePatch | G25：离开类结局后 Wish → FULFILLED + 中文 badge + reason |
| D7 | 装配/结局 | 开发者模式看 production.shots→video→assembly | 多 Shot 真实装配成 scene mp4；Director 自然收束不硬切 | `assembly.concat` span 可查 |
| D8 | 本地执行 | 开发者模式 → 运行环境 → 切 VIDEO_LOCAL → `/dev/local-task` 提交 Sol-H3 | Spark 本地视频后端真实存在 | 已实测出 370KB mp4；切换展示 drain→active |
| D9 | 技术审阅 | 开发者模式 Trace / 世界状态 / 分支预测 tab | Skills 版本化执行、World/Drama 双域提交、Jev observation、Directive | 标准/开发者模式切换证明术语隔离（普通用户不见 Prompt/Provider） |
| D9b | 模型路由 | 模型路由 tab 指 director/narrative/production 各自链 + 一次可控 fallback | Q49-70 模型职责真实运行 | DGX 实测 nemotron_local/step_5 circuit_open→降级链即活证据 |
| D9c | 并行/事务 | 分支预测 tab：Top-K 并行 + SELECTED→CANONICAL | 推荐零重推理、并行预生成、两阶段提交安全 | `scheduler.lock_topk`/`publish` span |
| D10 | 本地输出 | 视频生成 tab：Job 列表 + status 迁移 + 输出文件 | 本地任务有来源/耗时/产物 | `job_*` GENERATING→READY |
| D11 | 续杯 | Arc 关闭后 → 「继续这个世界」 | 旧结局保留，关系/事实继承，新 Arc 开始 | `test_full_flow` 断言 arcs==2 |
| D12 | 玩家反馈 | 展示已收集反馈 | 真实体验评价 | ⛔ 当前无真实玩家样本——如实说「未评估」，不用自动分数冒充 |

## 现场时长弹性

- 本地 Sol-H3 任务可在 D8 提前启动，生成期间继续讲解（Q26 B 允许），
  不要求同一 Spark 同时跑所有模型。
- D11/D12 可按时长展示已有存档/先前反馈并明确来源，不冒充当场产生。
- 不规定现场热插拔 Skill，不做强制盲测/对照。

## 演示前检查清单

```bash
curl -s http://139.199.69.46:9000/api/health
curl -s http://139.199.69.46:9000/api/dev/providers   # 看 selected/skipped
# 若某 provider 意外 circuit_open：POST /api/dev/providers/recover
```

- [ ] 前端 `index-*.js` 为最新构建（页面源码比对 `dist/assets/`）
- [ ] 浏览器清 localStorage 或新开隐私窗口，避免旧 sessionId 残留
- [ ] 准备一个干净 session（`POST /api/sessions {version_id}`）
