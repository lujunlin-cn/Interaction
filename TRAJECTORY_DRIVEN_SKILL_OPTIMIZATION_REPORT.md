# Trajectory-Driven Skill Optimization Report

研究日期：2026-09-26。Start SHA：c22d14bceea3930e2dd2c25eaaf449bc85fbbd0a。

本轮完成“历史数据 → 分析 → 能力边界 → 实现 → 隔离回放 → 反例复验”的研究闭环。**确定性契约、安全与恢复回归通过；剧情质量全面改善及无质量退化门槛仍为 PARTIAL。** 不把模型偏好票数、有效 JSON 或旧视频当成完整 Gameplay PASS。

用户指定产品范围：PLAYER_UX_FEEDBACK_REPORT.pdf 的 **4、5、7、8**。其他 Agent 的玩家/创作者/开发者分离及开场呈现改动已保留，不在本报告中冒领。最终 SHA 以包含本报告的 Git 提交与交付回复为准。

## 1. 数据集与重建范围

- 数据库 41 个 Session；合并验收证据去重后 42 个。
- Session provenance：25 real_provider_observed、14 mixed、2 mock_or_fixture、1 unknown。真实 Provider 不等于真人操作，旧自动验收与用户操作无法全部区分。
- 全体 214 条分支记录：40 acted turns、146 speculative、28 opening。**不把 214 叫作 214 次玩家行动。**
- 真实 Provider 分支子集 119 条：26 acted turns、69 speculative、24 opening。包括 16 FREE，其中 13 最终 canonical。
- 474 个来源文件、467 条恢复 Span、69 条去重 Usage Ledger operation。初始数据库 Trace 表为 0，不能据此假装完整调用史。
- 统一 TrajectoryTurn schema 1.0.0，214/214 结构验证通过。复用原 Branch/World/Proposal 领域结构；缺失信息保留 null 与 missing_observability。
- 重建依据：domain ID、branch/session 关联、事件时间、read_set、canonical receipt。缺失历史 memory/pressure 清空为未知，不回填最终状态冒充回合前状态。

入口：docs/trajectory-analysis/TRAJECTORY_SOURCE_INDEX.md、dataset.json、source_index.json、TURN_TIMELINES.md、TRAJECTORY_TURN.schema.json。

## 2. 最严重的十类 Gameplay 问题

| 问题 | 证据 | 根因 / 处理 |
|---|---|---|
| 意图进入 Director 前丢失 | 16 个 FREE 使用同一路径；确认 strategy 不在真实 prompt | Routing 契约缺失；已传递 ActionSemanticPacket |
| 用物品变成获得物品 | 2 个 USED + add；含急救物资与未持有武器 | Mechanic 提案歧义；组级仲裁阻止此模式 |
| 文本已发现线索，状态未体现 | 4 个需复核样本 | Evidence 与 Clue 生命周期未对齐；尚未证明全是漏触发 |
| 正文说完成/移动，状态未推进 | 6 个需复核样本 | Director prose 与 typed patch 不一致；仍需语义评估 |
| Jev 缺乏当前情境 | 11 次 ranking 中 4 次 OTHER > .5 | 缺少可读地点、近期行动、关系、压力；已扩充并保存 OTHER |
| 重复提交/再生可重复进入流程 | 用户问题 7；31 个历史 canonical checkpoint 注入 retry | Runtime 缺少终态幂等；已修复 |
| Director 上下文混入资产信息 | 119 条同输入投影对比 | 非规划信息与历史双重叙述；移除明确媒体字段 |
| Narrative 缺物品/地点/允许变更 | 文字回放凭空出现便携设备和笔记本 | Context starvation；补充 ScenePacket，但反例仍存在 |
| Skill 不可追踪、重启丢 Trace | 初始 DB Span=0，文件有 467 条；查询前缀不匹配 | 持久化和观测问题；持久 Trace 与 Observatory |
| Provider/角色引用/秘密误杀掩盖玩法问题 | 5 billing、2 ref、3历史 truth false-positive 分支 | 分离 transport、引用和语义问题；保留先前修复，本轮不烧媒体 |

分组、重叠计数、严重程度和示例见 FAILURE_TAXONOMY.md。数量不能相加形成总体失败率。

## 3. 哪些不是单纯模型问题

确认后的意图未被发送、Jev 缺少当前情境、Narrative 没有资源/地点、同一提案重复进入提交、Skill 查询不到记录，都是 Runtime/Context/Contract 问题。

“未持有火箭也直接秒杀威胁”“在错误地点开锁”“关系变化指向错误人物”则属于尚未解决的语义 grounding。新增 schema 不足以证明已修复。没有证据证明系统进行了四次独立重复理解；历史典型链路是 Jev → Director → Narrative。

## 4. Jev Top-K

最大可证问题是 context starvation 与 OTHER 被排序流程忽略，**不是已证明普遍存在三个同义选项**。历史候选大体有调查/社交/救援/撤离方向。精确 Unicode 去重、当前情境、目的描述与 OTHER 记录已实现；不为刷多样性强塞无关行为。

3 个真实 Director + Jev 回放，同为 Top-3 盲评：2 组偏好新版，1 组偏好旧版；多样性分数 4→3、3→4、3→4。失败组仍重复“恢复供电”这一已叙述目标。历史 canonical location 与正文进度不一致也影响判断。小样本、单一 Critic，不能声称多样性普遍提高。

初评误把旧 5 候选与新 3 选项比较，已保留并排除，最终用旧 Jev 分数取 Top-3 再盲评。

## 5. Free Input Fidelity

16 个 FREE 记录均保留原始输入；13/16 canonical 是分支完成率，不是意图忠实度。8 个固定历史 FREE、跨两个故事的真实文字 counterfactual，Step5 匿名评审：新版偏好 6，旧版偏好 2。

Fidelity：EXACT 0→1、ACCEPTABLE 4→4、DISTORTED 3→2、OVERRIDDEN 1→1；EXACT+ACCEPTABLE 4/8→5/8。未持有武器案例两版均 OVERRIDDEN，即使新版因较少额外污染获偏好，也不是成功。历史状态重建受限、模型随机性使其只能是研究信号，不能当作因果提升百分比。

两个旧版获偏好反例：br_00010_040fd6 远程开锁、br_00010_262ca1 新增随身设备。补充 Narrative state projection 后，固定 Director outcome 再测 2 例，笔记本幻想仍在，故不标记修复成功。

## 6. Existing Skill Audit：过少、过多、拆分、合并

已记录 triggers：Inventory 13、Clue 13、Relationship 8。没有独立真实标签，无法仅凭次数判断过少/过多，也不能给出伪精确率/召回率。4 条 Evidence/no-Clue 是人工评审队列；Relationship 默认 target/delta、错误对象解释需重点审视。

拆分 Runtime 内能力契约、策略、schema 与调度职责，不增加几十个模型代理。合并 Inventory/Clue/Relationship 的共同提案仲裁；保留独立 typed effect adapter，不让三个 Agent 各重解同一行动。Wish 保持偏好状态，QTE 保持受控定时机制，ffmpeg/格式化/查状态继续是 Tool，不包装成“智能 Skill”。

逐项矩阵：docs/skills/CURRENT_SKILL_AUDIT.md。

## 7. 新发现并实现的能力

| 能力 / 优化 | 版本与职责 | 证据 / 评价 |
|---|---|---|
| Understand Free Action | v2.0.0；复用 Jev 理解，原话/确认修改/顺序/否定/目标/方式进入同一 packet；模糊输入由 AI 预填供确认 | 原话 16/16；确认/edit/cancel 测试；8 个真实文字盲评 |
| Evaluate Choices | v1.0.0；已知情境 → 具体行为/目的 → 去重 → Jev 排序及 OTHER | 11 个历史 ranking、3 个真实反事实；不宣称解决语义重复 |
| Reconcile Mechanics | v1.0.0；显式目标、冲突/重复/生命周期检查；一次有界 Director 修正 | 56 个提案：3 改善、53 不变、0 规则回归 |
| Skill Observatory | 持久、版本、why/input/output、延迟与提案处置、Skill Chain | 重启持久化测试、真实 API 可读、隔离浏览器 PASS |
| 因果呈现与专属 Context | Narrative 单一 visual_focus；Player 行动→结果→位置变化；Director 去媒体元数据；Narrative 已知状态 | PDF 4/5；119 context 投影、浏览器、2 反例复验；未新生成视频 |
| 恢复与幂等 | 当前 canonical 选择重试返回原结果；历史过期选择拒绝；重复生成任务复用；已花费选项移除 | PDF 7；31 checkpoint replay；并发/恢复 regression |

“既有模型推理 + 独立契约/策略/schema + 可观察结果”组成能力，不宣称 deterministic helper 是新的自主 Agent。StateManager 始终是正式状态提交边界。

PDF 8 的目的/方式由 AI 尽量预填，可编辑、取消、留空；确认前不执行。字段是可修改假设，不被当成新的世界事实。

## 8. Replay Before / After

| 层 | 样本 | Improved / Neutral / Regressed | 说明 |
|---|---:|---|---|
| 提案确定性规则 | 56 | 3 / 53 / 0 | 两个使用即获取被挡，一个 clue envelope 修正 |
| 终态重复提交注入 | 31 | 31 / 0 / 0 | 历史状态内存副本；旧流程停于写入边界前 |
| 真实 FREE 文字 + 盲评 | 8 | 6 / 0 / 2 | 单 Critic、时间分离，不是受控在线 A/B |
| 真实 Top-3 + 盲评 | 3 | 2 / 0 / 1 | 相同 K；不比较 5 对 3 |
| Narrative context 单变量跟进 | 2 | 不给伪成功分 | 输出合法，但设备幻想未全部解决 |

Replay 不连接媒体 adapter，不调用正式 Player API，不写 canonical DB。冻结源哈希前后一致，隔离世界状态未变。Production 研究已存 plan / visual_focus，不提交 H3。

## 9. Calls / Context / Latency / Cost

- 119 条 Director context：678,125 → 635,864 Unicode 字符，下降 6.232%；检查的 state/rule 核心字段丢失 0。semantic packet、Narrative 投影增加其他部分，所以不是完整请求 token 降幅。
- 不能证明 LLM calls/turn 下降。普通成功链路没有因 helper 新增 LLM；模糊意图预填和提案纠错可增加调用。幂等减少错误重复任务，不是正常回合固定调用。
- 历史 created→Ready n=74，中位 97.063s；created→canonical n=31，中位 84.948s。样本不同，包含队列/媒体/用户等待，不可直接比较。无新增媒体验证，**没有 Ready latency 改善结论**。
- 历史 provider latency：Nemotron n55、中位 5.616s；Step3.7 n22、中位 12.160s；Step5 n1、34.100s。全量端到端、各 Skill token、准确浪费秒数仍缺数据。
- 有结构记录的成功文字/Decision 调用 25（Director 11、Narrative 11、Jev 3）；Step5 7 attempts、5 parsed successes；另有 tiny local health inference。早期 transport/context-budget 失败独立保存，记录不等于完整账单。
- **Image Generate 0 / Image Edit 0 / H3 0**。图片仍 Relay，Fal 仅 H3；Provider 路由未改。

## 10. State Consistency / Trigger Quality

确定性 state consistency 改善有证据；语义世界一致性仍有缺口。阻止 USED + add 不意味着发现所有虚构物品，没有 patch 的不合理叙事仍能出现。Relationship 的显式合法 target/delta 不等于因果正确。

Trigger precision/recall、Truth Leakage Rate、Branch Pollution Rate 无独立标注分母，不填虚构数字。隔离、原子提交与 snapshot 回归通过；不能把单元测试通过改名为真实世界零污染率。

## 11. PRD Deviations / v0.7 建议

ADR-001/002/003 记录原设计、轨迹、选项、决定、迁移、回滚：

1. 能力 contract/policy/version/metrics 成为正式对象。
2. 玩家确认的 semantic packet、AI 预填与可取消确认。
3. Player 行动/结果回执及单镜头 visible focus。
4. 当前 canonical 选择重试返回幂等成功，过期历史选择仍拒绝。
5. 持久 Trace 与 Skill Observatory。
6. ScenePacket 显式已知状态/允许变更；不把完整隐藏 truth 交给 Narrative。

此前用户批准的“Jev 文字选项先出现、视频可延后”保持现状；本轮未新放宽 READY/提交规则。建议 v0.7 明确 decision availability 与 media readiness。Speculative isolation、StateManager、Snapshot immutable、Standard 无技术信息、自由输入保留均未改变。

## 12. Competition 演示

Developer → System Skills → Skill Observatory：名字、版本、触发原因、输入摘要、输出、提案、commit 关联、延迟与有限窗口统计；未知 token/precision/recall 为空。普通用户只看故事与可理解反馈。

五项重点：**Understand Free Action、Evaluate Choices、Reconcile Mechanics、Manage Inventory / Discover Clue（typed effect family）、Plan Video Production**。Visual Continuity 当前主要是 reference policy/tool，不能冒充自动运行的视觉 Critic。

链路：玩家偏离推荐 → Jev observation → Understand Free Action → Director → Reconcile Mechanics → Inventory/Clue/Relationship proposal → StateManager → Narrative focus → Production。Skill 不直接写 World。测试截图为 fixture UI，不冒充新真实游玩；真实历史、文字回放与新运行 Trace 分开标识。

## 13. 回归、运行环境与交接

Backend **257 passed / 0 failed**；Frontend build **PASS**；7 项隔离浏览器契约 **PASS**。mock、Publish atomicity、AT-80、Theater、paid safety 纳入完整回归。

测试隔离改为单进程独立临时 DB/media/data、禁用测试 profile lifecycle，避免继承部署配置切换模型。早期影响已恢复，最终模型健康。

手工 uvicorn 占据 9000 已平滑交接给 systemd。最终 interaction.service active/enabled、Linger=yes、9000 可用、live、AGENT_LOCAL_PROFILE；Nemotron Lightning 已加载，/models 与 tiny inference PASS；Fal paid=true；Jev 预测媒体预生成=false。服务和模型保持运行。证据 human_test_handoff.json。

## 14. Remaining Research Directions

1. Evidence-bound feasibility：未持有装备、未识别对象、无证据秘密不能进入裁定；需独立标签与反例集。
2. 区分 planned / attempted / achieved，将正文与 location/inventory/clue/ending 对齐。
3. 角色/关系主体三元组，解决对第三者失信却扣伙伴关系的误解释。
4. Semantic goal repetition / meaningful diversity：多故事 held-out 后再评 MMR/critic，不用荒谬选项刷分。
5. Complete trace 与 phase timing，计算真正 per-turn tokens、first-option/first-Ready/K-Ready、media waste、trigger precision/recall。
6. 双 Critic / 人工抽样 / 同模型同步 baseline-vs-candidate replay，控制历史缺失和随机性。不反复调参直到这 8 例表面全胜。

本轮不宣称“所有问题修复”或“Gameplay 无退化”。确定性功能已落地并可人工使用；更强语义优化由明确反例和门槛约束下一轮研究。
