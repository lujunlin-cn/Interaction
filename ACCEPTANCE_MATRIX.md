# 验收矩阵 · AT-01~AT-76

PRD v0.6 §17「验收用例与完成定义」。按实测证据填写——只标真实跑过的用例，
外部依赖（真实 Provider 配额 / 用户试玩 / 人工判断）标 BLOCKED，未跑完的标
NOT_RUN，**不伪造**。

## 测试基线（Final Closure）

- 单元/集成：`cd backend && PROVIDER_MODE=mock pytest tests/` — **45/45 绿**
  （含 vertical_slice 端到端、generalization、skills、two-phase commit）。
- 部署：DGX Spark `:9000`，`provider_mode=hybrid`，`profile=AGENT_LOCAL_PROFILE`。

本地复核命令：`DATABASE_URL=sqlite+aiosqlite:///./itest.db PROVIDER_MODE=mock SOL_H3_BASE_URL= .venv/bin/python -m pytest tests/ -q`。
DGX Spark 已配置 `SOL_H3_BASE_URL=http://127.0.0.1:8790`；单元测试使用显式夹具隔离外部服务。

### Final Closure 增量结论

- Play Loop 已闭环：创建 Session 后进入 `OPENING_PREPARING`，首幕复用
  Narrative → Production → Video → Assembly，自动播放并在 `_present()` 后后台预生成推荐；
  播放结束进入 `WAITING_DECISION`，失败进入 `FAILED_RECOVERABLE`，可重试、切换文字模式或退出。
- 首幕带 `opening` 标记，不计入限时互动的有效行动计数；限时节点不会在刚进入故事时提前消费。

- Character Studio 正式 React 操作已接入 AI 双 Candidate、Canonical、标准视图二次确认、非破坏编辑、Outfit、版本/Diff、Snapshot Override/Promote 与 Resolver。
- Runtime 已按 `ShotPlan N → N 个 Provider Job → N 个 clip → FFmpeg concat` 执行；Trace 的 `video.generate` 记录 `jobs`、`clips`、`shot_ids`。
- `hybrid` 云视频路由为 `h3_max → mock_video`；Mock 仅显式降级。Real Multi-Shot 必须由真实 Provider N Job + N clip + FFmpeg concat 证明。
- Nemotron 3.5 Lightning NVFP4 已在 DGX Spark 通过 vLLM 0.27.1-aarch64 启动；`:8001/v1/models` 与中文 Director JSON 冒烟均通过。`gemma3:27b` 不计入 Nemotron PASS。
- 真实链路冒烟：`sess_00003_fef0ad` → 自由输入「我找到那段录音」→ Jev
  `CLARIFICATION_REQUIRED`(0.44) → confirm → `br_00051_ff2a3d` CANONICAL →
  真实 mp4 `/media/scenes/scene_00083_00ca24.mp4` + 真实 LLM 叙事 +
  `skill.inventory`/`skill.clue-system` spans(ver 1.0.0) + world
  `inventory=[Evidence Recording]`、`clues=[recording_found]`。
- 本次发现并修复回归：`schema_hint` 注入使 mock `_director_plan` 的
  `scenario_context` 提取吞入尾部非 JSON 行 → `ctx={}` → location/npc ops 丢失
  （`test_full_flow` 挂 `world.location=='foyer'`）。已改 `raw_decode` 只取首个
  JSON 对象，45/45 恢复绿，DGX 已同步。

## 状态图例

| 标记 | 含义 |
| --- | --- |
| ✅ PASS | 有真实运行证据（测试断言 / DGX trace / 世界态变化） |
| 🔶 PARTIAL | 路径存在且有部分证据，但未覆盖用例全部判据 |
| ⛔ BLOCKED | 依赖外部条件（真实 Provider 配额、人工试玩、GPU 资源）当前无法执行 |
| ⬜ NOT_RUN | 代码路径实现但本会话未实测；不标 PASS |

---

## A. 会话/分支/两域提交（AT-01~AT-20）

| AT | 用例 | 状态 | 证据 / 备注 |
| --- | --- | --- | --- |
| AT-01 | 输入新设定，审阅 AI 草案并局部修改角色 | ✅ | `test_scenario_authoring_and_publish`：一句 idea → draft 含 core_question/truth_model/editable → publish 出版本；前端 Creator 页可局部改。 |
| AT-02 | 上传图片/声音/动作参考视频并绑定 | 🔶 | 素材上传 API + 三模态 references 链（#19）已通；三者同传混用的端到端留证见 AT-03。 |
| AT-03 | 同一次生成混用图、声、视频 | 🔶 | Provider adapter 不静默丢模态（references 打包进 contract）；真实三路同传的 provider 侧回执未全量留证。 |
| AT-04 | 播放中等待推荐，再点 READY 候选 | ✅ | Ready Gate：只有 READY 分支进 recommendations（I05）；点击走 ready-hit 复用同一 BranchContract，不重复生成。vertical_slice 选择→CANONICAL→video_url 播放验证。 |
| AT-05 | 无对应候选的自由输入形成新意图 | ✅ | 「我绕到后院去看看」无候选 → 新 FREE branch GENERATING → 真实新视频 + `location→backyard` op（test_full_flow 断言）。 |
| AT-06 | 现实世界不可能的道具/行为 | ✅ | 「我用激光炮打开后门」→ QUICK_ACK，world.version 不变、location 不变（test_full_flow 断言无污染）。 |
| AT-07 | 提交「希望她最终不要死」类 Wish | ✅ | Wish 独立保存原话 + `normalized_preference`；进 Wish Ledger，不即时改生死（G25；test_wish_lifecycle + mock smoke FULFILLED）。 |
| AT-08 | 更新 Wish/Drama/素材后旧分支撤回 | ✅ | Dependency Fingerprint：相关依赖变化使未就绪分支 INVALIDATED；有效依赖复用（fingerprint sha256 trace）。 |
| AT-09 | 非法字段/过期版本/重复提案 | ✅ | StateManager.validate 幂等键重复→duplicate、base_version 过期→stale reject、precondition 不符→reject；测试覆盖两域拒绝。 |
| AT-10 | 多分支生成但只选一条 | ✅ | Two-Phase：仅 SELECTED 进 PROVISIONAL→CANONICAL；未选分支的 ops/drama/foreshadow 不进 Canonical（测试断言 version 单调、无单边提交）。 |
| AT-11 | 多 Shot Beat 生成装配 | ✅ | production.shots→video.generate(多 clip)→assembly.concat；scene mp4 为多镜头真实拼接（#26 multi-shot 链路验证，ffprobe 时长=镜头和）。 |
| AT-12 | 命中机制事件后状态与 UI 更新 | ✅ | G26 Mechanic Skill 闭环：真实链路 `skill.inventory`/`skill.clue-system` span→ops→world `inventory`/`clues` 更新→Player 面板已知列表变化。 |
| AT-13 | Director 在不同历史下形成不同结局 | 🔶 | ending family 由 outcome.ending 解析 Scenario 声明；不同轨迹的分支结局矩阵未做大规模对比实验。 |
| AT-14 | Jev 超时/错误/低置信降级 | ✅ | 真实 Jev 返回 `CLARIFICATION_REQUIRED`(0.44)/`INTENT_ECHO`(0.49) → pending_intent → confirm 推进；无越权、无无限重试（DGX 实测）。 |
| AT-15 | Full Beat 生成/装配失败恢复 | ✅ | G27：inject provider_unhealthy → `last_failed_action{branch_id,raw_text,fail_stage}` → recover → 重发原文 → READY；已提交小动作不重复执行。 |
| AT-16 | 刷新/双击/重复回调幂等 | ✅ | idempotency_key `commit:{branch}`；重复 select 已消费分支→409；load_session 从 DB 恢复到正确 Scene。 |
| AT-17 | 达到预算不再新增超额任务 | 🔶 | budget_total/per_turn/speculation_cap 配置与记账存在；超额边界实测未单独留证。 |
| AT-18 | Spark 真实提交 Sol-H3 任务 | ✅ | #26：VIDEO_LOCAL 下 `POST /dev/local-task` → sol_h3_local 提交 → `_watch` 推进 READY → `clip_*.mp4`(370KB, ffprobe 5.042s)。 |
| AT-19 | 一轮 Skill trace 可追到版本/工具/状态 | ✅ | `skill.{sid}` span 带 `skill_id`+`skill_version`(1.0.0)+input(trigger)+output(ops 数)；/dev/traces 全链可查。 |
| AT-20 | 检索不泄露隐藏剧情/密钥/投机未来 | ✅ | ScenePacket allowed/forbidden_revelations 校验；G28 密钥只走 .env，Trace/界面无密钥；投机分支不进玩家已知。 |

## B. 决策/意图/时机（AT-21~AT-44）

| AT | 用例 | 状态 | 证据 / 备注 |
| --- | --- | --- | --- |
| AT-21 | Decision Lead Window 提前出现 | 🔶 | decision_lead_seconds 配置 + lead window 逻辑在；窗口内「所有候选都成立」的强保证未端到端留证。 |
| AT-22 | UNTIMED 未选择不自动推进 | ✅ | UNTIMED 停中性等待、不判失败、继续接受输入（状态机测试）。 |
| AT-23 | TIMED 超时执行预声明 fallback | ✅ | timed watchdog + Scenario 声明 fallback→正常事件链；`timed_timeout_override` 测试夹具。 |
| AT-24 | 连续行为更新偏好供 Jev | 🔶 | PlayerPreferenceState 从已提交事件更新并注入 Jev 请求；偏好不改 Hard State（结构保证），真实 Jev 偏好权重效果未量化。 |
| AT-25 | 部分 Ready 部分渲染不显示未就绪 | ✅ | Ready Gate：未 READY 不进 recommendations；调度等待/降 K/effective_k 可查（scheduler.publish span 记 effective_k）。 |
| AT-26 | 行动→观察→Drama 更新有类型化记录 | ✅ | Jev observation + evidence + 版本化 Manager 提交；模型不直写状态（双域 Proposal/Commit）。 |
| AT-27 | 探索期合法提前揭关键问题 | 🔶 | outcome.ending/跳阶段路径存在；「可跳阶段不强迫补齐」的多路径实测有限。 |
| AT-28 | 小动作/关键行动/完整 Beat 分层 | ✅ | QUICK_ACK 不重规划；关键行动即时评估；Beat 后幂等评估（测试分层断言）。 |
| AT-29 | UNTIMED 久留不惩罚；「等一小时」按规则 | ✅ | 「等一小时」→`fiction_minutes+60` op，非生成等待惩罚（mock 规则 + kind=withdrawal）。 |
| AT-30 | 明示动机不被偏好覆盖；歧义先澄清 | ✅ | 「跟踪是为了保护」明示动机入 intent；低置信→CLARIFICATION_REQUIRED 不强行执行（Jev 实测）。 |
| AT-31 | Directive 含功能/目标/硬约束/机会 | ✅ | DramaticDirective 结构：primary/secondary/target_changes/hard_constraints/avoid（director.plan span output）。 |
| AT-32 | 空抽屉/小动作组合/关键发现三态 | ✅ | 空抽屉→快速反馈；组合→合并；关键发现→完整 Beat+新视频（mock 规则分类 + mode 字段）。 |
| AT-33 | 有/无前文证据的反转候选区分 | 🔶 | evidence/Dependency 机制区分铺垫；语义复核的对抗性实测未做。 |
| AT-34 | 伏笔登记/呈现/回收可追溯 | ✅ | ForeshadowEntry 生命周期 + `AUTHOR_SEEDED/EMERGENT` origin；未呈现不构成已知；回收有正式事件。 |
| AT-35 | 压力源不支持则不凭空加灾难 | ✅ | Directive avoid 列「未建立的灾难」；_advance_pressures 按已声明压力源推进。 |
| AT-36 | Director 按历史判断继续/收束 | 🔶 | 无固定轮数/ readiness 分数门槛（配置无此项）；多长度轨迹判断未系统采样。 |
| AT-37 | Wish 不可行/部分/冲突三态 | ✅ | 七态 Wish：ACTIVE/PARTIALLY_FULFILLED/FULFILLED/FAILED… + history{action,reason,evidence} + 中文 label（G25，Player badge 实测）。 |
| AT-38 | 明确离城→退出/后果结局 | ✅ | 「转身离开」→`ending=voluntary_departure`+`location` op+ended；不强行拉回、不凭空灾难（G25 mock smoke）。 |
| AT-39 | Arc 关闭后不自动续，点继续新建 | ✅ | ended 后 `/continue`→`CONTINUED`→arcs==2、继承事实关系、旧结局不变（test_full_flow 断言）。 |
| AT-40 | 两域联合提交失败/重复/过期 | ✅ | World+Drama 原子提交：单边失败整体 reject；重复幂等；过期分支拒（不出现死角色复活类冲突）。 |
| AT-41 | 高置信普通 vs 重大反转路径 | 🔶 | confidence 阈值路由（普通快行/重大仍审查）逻辑在；两档对照实测样本不足。 |
| AT-42 | 压力/伏笔/关系/Wish 争用可解释 | 🔶 | Directive 硬约束优先 + opportunity 来源；「不一次硬塞全部」策略在，多源并发裁决实测有限。 |
| AT-43 | 一句想法+否决 AI 设定可局部改 | ✅ | idea→完整草案；Creator 可局部改非专业字段（test + 前端）。 |
| AT-44 | 真实体验者试玩并反馈 | ⛔ | 需真实用户试玩；不虚构结论。 |

## C. 模型部署 / Provider 路由（AT-45~AT-60）

| AT | 用例 | 状态 | 证据 / 备注 |
| --- | --- | --- | --- |
| AT-45 | DGX 启动本地 Director + 中文规划 | ✅ | vLLM `:8001/v1/models` 返回固定 Nemotron ID；真实中文请求返回合法 `outcome`/`directive` JSON。 |
| AT-46 | Ready 点击 vs 自由输入路径 | ✅ | Ready 复用 BranchContract 不重复生成；自由输入新 FREE branch 保留原文+Jev observation。 |
| AT-47 | Director prompt 分层 Context | 🔶 | `_scenario_brief` 摘要注入而非全量 Event Log；token 占比/检索来源量化未采集。 |
| AT-48 | Narrative 试图泄露未授权秘密被拒 | ✅ | `leak_secret` fixture 注入 → forbidden_revelations 校验拦截（FR-068 测试夹具）。 |
| AT-49 | K=3 三路并行非串行 | ✅ | lock_topk(k=3) 后并行启动；generating 同时多条（view.generating 实测多分支同阶段）。 |
| AT-50 | READY 点击后媒体校验失败回滚 | ✅ | SELECTED→PROVISIONAL→校验失败回滚，正式 State/Drama/伏笔不污染（two-phase 测试）。 |
| AT-51 | 全链耗时分阶段 timing | 🔶 | 各阶段 span 有 ts/时长；cold-hot 标记与 P95 判定未建报表（PRD 明确不以旧 P95 判 PASS）。 |
| AT-52 | Top-K 中一条失败两次→K-1 发布 | ✅ | 单分支快速 retry 1 次→仍失败→其余 Ready 以 K-1 原子发布，`effective_k`+原因记 scheduler span。 |
| AT-53 | Step3.7 Narrative timeout→本地 Lightning | ✅ | narrative 路由 `step_37→nemotron_local→mock_text`；inject timeout→Router 记错误回退、契约不变、来源标 fallback（#26/路由矩阵实测）。 |
| AT-54 | 本地 Lightning OOM→Step5（非3.7） | ✅ | admission/Provider error 均按 `nemotron_local→step_5→mock_text` 回退；本次实测服务无 OOM，故障路径由路由测试覆盖。 |
| AT-55 | 未选分支相似请求的指纹复用/失效 | ✅ | Dependency Fingerprint sha256：兼容才复用，人物/Wish/Asset 变→确定性 INVALIDATED。 |
| AT-56 | AGENT↔VIDEO 往返切换 drain/persist | 🔶 | `/dev/profile/switch` 切换 + profile_unavailable→fallback 验证（#26）；drain/persist/unload 全程时序留证未全量。 |
| AT-57 | VIDEO_LOCAL 下 Production 走 3.7 | ✅ | VIDEO_LOCAL 时本地 Lightning unavailable→production 按 Q69 自动 step_37，来源正确（profile 切换实测）。 |
| AT-58 | VIDEO_LOCAL+3.7 故障不误试 Lightning | ✅ | Router 不尝试已 unload 的 Lightning；进入可恢复错误路径/无冻结 fallback 如实返回。 |
| AT-59 | 分角色注入故障走各自 fallback 链 | ✅ | director/narrative/production 各自固定链 + circuit breaker + trace（路由矩阵 skipped[] 实测记录）。 |
| AT-60 | Provider 版本升级后旧分支 provenance | 🔶 | provenance 记 model/adapter/profile 版本；版本变更触发 fingerprint 失效的实测未做。 |

## D. 角色库 / 素材 / 前端（AT-61~AT-76）

| AT | 用例 | 状态 | 证据 / 备注 |
| --- | --- | --- | --- |
| AT-61 | 全局角色库按 personality 搜索 | ✅ | 角色库 search 后端真实返回（#20 闭环）；UI 与能力一致。 |
| AT-62 | 一句描述 AI 建角色→2 张 Candidate | ✅ | DGX 实测：`ai-generate`→2×CANDIDATE（真实 fal `v3b.fal.media` URL）；`ai-describe`→真实 LLM 外观草案（FR-096 确认制不落库）。 |
| AT-63 | 选主图→二次确认→标准参考组 | ✅ | DGX 实测：approve front→CANONICAL+IDENTITY 版本→`standard-views` 真实 4 视图并行（three_quarter/side/full_front/full_side）→ 各 approve 成 Canonical。 |
| AT-64 | 「换雨衣保持身份」编辑 | 🔶 | `edit-image` 非破坏式→derived CANDIDATE、identity guard prompt 注入（mock 实测）；真实 nano-banana-2/edit 单次留证待跑（路径与 standard-views 同一 adapter）。 |
| AT-65 | 快捷只改背景/姿势 + 自由语言编辑 | 🔶 | 前端 Edit 入口落 IMAGE_EDIT、指令自由文本、新候选引用 source_asset_refs 可追踪；无需 Mask 编辑器。 |
| AT-66 | Outfit 属同一 GlobalCharacter | ✅ | Outfit 挂同一 CharacterVersion、可缺视图、不复制角色（数据结构）。 |
| AT-67 | 上传 Pose/动作视频 Reference | ✅ | 两类 Reference 绑定 CharacterVersion 并可被 Production Resolver 读（references 链）。 |
| AT-68 | 换主图/Canonical Voice/新增 Outfit | 🔶 | DGX 实测：版本链 v1..v7（IDENTITY×3→ASSET_ADDITION×4）、diff v1→v6 资产差异正确；Voice/Outfit 三类各一次留证未全跑。 |
| AT-69 | Scenario 用 v3 后 Global 升 v4 | ✅ | publish 自动 `snapshot_for_scenario`（routes.py publish 钩）→ frozen_asset_refs；Global 新版本不渗透（DGX 实测 promote 升全局 v7）。 |
| AT-70 | Scenario 内改外观→仅本故事/全局 | ✅ | `character-snapshots/{id}/override` 写 local_overrides 不污染 Global；`/promote` 人工升为新全局版本（DGX 实测 200→全局 appearance 生效）。 |
| AT-71 | 单角色 Scene→自动选 2-4 张图 | ✅ | DGX 实测：5 Canonical→resolve 选 4 张+selection_reason 可审计；create_session 把 frozen refs 直进 asset_manifest（engine.py v0.6 快照消费）；developer_override 优先（mock 实测）。 |
| AT-72 | 双角色素材近上限→确定性裁剪 | 🔶 | `_bound_references` 按角色分桶+每角色≤4+主身份优先（engine.py）；双角色边界实测未跑。 |
| AT-73 | 改文字描述不点重新生成→不动资产 | ✅ | 保存仅 PATCH 文本字段；Studio 提示「不会自动生图」；`ai-describe` 仅返回草案不落库（FR-096 确认制）。 |
| AT-74 | 多分辨率 100% Zoom 走四页 | ✅ | `docs/acceptance/shots/`：1366×768 / 1440×900 / 1920×1080 / 2560×1440 / 3840×2160 五档走 home/creator/developer——文字可读、侧边栏与工作区无关键遮挡；4K 合理扩展。新增 `#/<page>[/<tab>]` 深链（store.ts）支撑可分享直达与验收脚本。 |
| AT-75 | 标准隐藏 Prompt/Provider，开发者可见 | ✅ | 术语隔离：玩家界面自然中文、Provider/model 仅开发者模式；FAL_KEY 不进浏览器/Trace（G28）。 |
| AT-76 | 封版部署核查 + AGENT↔VIDEO 往返 | 🔶 | Nemotron Lightning 已真实部署并完成并发验证；Profile API 已接入 drain/persist/stop-release/start/health 生命周期，真实双向切换需在单 GPU 空闲窗口执行，保留 PARTIAL，不以 enum 变化冒充 PASS。 |

---

## 汇总

以下汇总是上一轮 DGX 证据快照，保留用于追溯；Final Closure 增量结论不把未重跑的真实 Provider 证据升级为 PASS。

| 状态 | 数量 | 占比 |
| --- | --- | --- |
| ✅ PASS | 51 | 67% |
| 🔶 PARTIAL | 24 | 32% |
| ⛔ BLOCKED | 1 | 1% |
| ⬜ NOT_RUN | 0 | 0% |
| 合计 | 76 | 100% |

**BLOCKED / 待外部条件**：

- **AT-44**：需真实用户试玩反馈，不虚构。
- **AT-76 残项**：真实双向切换会停止 Nemotron 并启动 Sol-H3 容器，需单 GPU 空闲窗口保留 stop/start/health 证据；Nemotron 部署本身已通过。Real Multi-Shot 不能用 Mock 证明。
- **AT-45/47/51/60/62~65/68/71/72**：路径实现且有结构证据，缺大规模或真实配额下的
  端到端留证，标 PARTIAL 而非 PASS。

**已知接受风险**（README G28）：`/media`、`/files` 静态目录无鉴权、`/dev/*` 无鉴权、
session_id 即访问令牌——单租户内网/演示适用，公网需反代签名 URL。
