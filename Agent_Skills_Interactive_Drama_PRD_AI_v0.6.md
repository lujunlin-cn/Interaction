---
document_id: interactive-drama-prd
version: "0.6"
language: zh-CN
prepared_on: "2026-09-24"
status: requirements-baseline-with-character-asset-studio-runtime-and-ai-native-creator-player-ux
product_name: "AI 原生互动视频／短剧平台（工作名称）"
source_of_truth: "v0.5 完整基线（Q01–Q70、I01–I05、Dynamic Drama Control、Model/Agent Runtime）+ Q71–Q104 Character Studio 决策 + Q105–Q122 AI 引导式创作/统一角色颗粒度/自然语言玩法/沉浸式 Player 决策 + fal.ai Nano Banana 2 图像 Provider 锁定 + 全局显示/响应式与真实模型部署验收补充"
supersedes: "PRD v0.5；完整继承既有产品、戏剧控制、模型与 Runtime 基线，增量冻结全局角色资产系统、AI 引导式 Creator、统一角色管理颗粒度、自然语言玩法作者界面、沉浸式 Player、全局显示与响应式验收"
artifacts:
  ai: Agent_Skills_Interactive_Drama_PRD_AI_v0.6.md
  latest_alias: Agent_Skills_Interactive_Drama_PRD_AI.md
  human: Agent_Skills_Interactive_Drama_PRD_Reader.html
human_artifact_status: "高保真原型独立维护；v0.6 Markdown 为需求权威基线，正式 React 实现不得低于已冻结的关键交互"
baseline_file: Agent_Skills_Interactive_Drama_PRD_AI_v0.5.md
baseline_git_blob_sha: "68aa819dc85803b894b68ff7abc34c4518b675ff"
decision_count: 122
character_decision_range: [Q71, Q104]
creator_player_ux_decision_range: [Q105, Q122]
character_image_provider_lock: "fal.ai: fal-ai/nano-banana-2 + fal-ai/nano-banana-2/edit"
interaction_amendments: [I01, I02, I03, I04, I05]
external_evidence_refresh: "2026-09-23：在继承 v0.5 资料基础上，核验 fal.ai Nano Banana 2 文生图与 Edit API；其余模型/运行时来源继承 v0.5，真实部署状态必须以服务器实测为准"
implementation_status: "需求基线；代码、付费 API、本地模型与线上部署是否完成必须以真实运行、Trace、AT 验收和服务器证据为准"
priority_semantics:
  P0: "黑客松交付必需；其中新增工程建议仍须按建议身份理解"
  P1: "核心闭环通过后实施"
  P2: "后续产品扩展"
provenance_semantics:
  USER: "用户原始需求或明确选择"
  DERIVED: "落实已选需求所必需的设计约束，不代表已经实现"
  PROPOSED: "本次新增建议，可替换，不得冒充用户决定"
  VERIFIED_DOC: "早前版本记录的一手文档核验；本轮继承，未重新联网核验，也不等于本项目实测通过"
  OPEN: "待凭据、设备、规则或实验确认"
---

# AI 原生互动视频／短剧平台 PRD v0.6 · Character Asset Studio & Model/Agent Runtime Architecture

> **创作者定义世界与矛盾，玩家决定行动，系统组织有因果、有递进、可收束也可续玩的故事，Agent Skills 将值得呈现的剧情制作成下一幕。**
>
> 本文同时是产品需求基线与 AI 开发代理的工程输入。它不是产品已经实现的声明，也不是对所有模型性能的保证。**v0.6 为合并后的完整 Markdown 基线，不是仅有新增条目的补丁。v0.6 完整继承 Q01–Q70 与 I01–I05，并新增 Q71–Q104 的 Character Studio / Global Character Asset System 决策，以及 Q105–Q122 的 AI 引导式 Creator、统一角色颗粒度、自然语言玩法和沉浸式 Player 决策。角色生图与编图统一锁定 fal.ai Nano Banana 2；应用、模型部署、API 容错、角色一致性与性能仍须真实验收。**

## 00. 文档契约与执行规则

### 00.1 阅读优先级

开发者或 AI 编程代理应先读第 01–03 节确定产品意图与决策，再读第 04–06 节确定体验和功能，最后进入状态、Skills、调度、技术与验收章节。发生冲突时采用： **用户后续明确选择 > 用户原始意图 > 本文派生设计 > 本文新增建议** 。技术文档可以推翻能力假设，但不能被用来悄悄删除用户已确认的功能；发现阻塞必须标记未通过，并提出替代实现。

本文用 `USER / DERIVED / PROPOSED / VERIFIED_DOC / OPEN` 区分来源，用 `P0 / P1 / P2` 区分交付顺序。 **来源与优先级是两条独立维度** ：例如一个被建议列为 P0 的状态事务机制，仍是工程建议，不是用户逐字指定的技术。

### 00.2 不得误读的核心约束

1. 本产品不是把自由文本分类回固定视频树；未见过的合法行动必须能形成新剧情与新视频。
2.  **Q09 选 B** ：不合世界设定的行为优先在故事内部解释、受阻或转化，不以标准化报错打断沉浸；不强行采用被用户未选的三级产品交互。
3.  **Q11 的导演能力叫“许愿”** ：角色扮演仍是主入口，愿望影响未来，不直接改写既有事实。
4.  **Q18 选 C** ：预生成未命中时显示主题化加载动画；不将聊天、调查、QTE 等等待期小游戏列为 MVP 必做。
5.  **Q22 选 C 且 Q25 选 A** ：图片、声音、视频三类参考素材都必须有实际生成链路，不能只有 Schema、假按钮或上传存储。
6.  **Q28 选 B** ：以真实 Skill 调用日志为比赛展示验收；现场安装／卸载、开关对照不是必做。
7.  **Q12 的“高概率两三个选项”指候选行动／分支，不是镜头数量** ；一个分支还可能包含多个镜头，预算必须计入相乘后的任务量。
8.  **Q19 的低成本预测不是用视频模型试演未来** ：文本模型提供候选及假设后果，Jev 判断、排序、筛选；只把少量临近分支送去视频生成。
9.  **Q21 是混合部署偏好** ：Jev 调 API，视频可调 API，State／Director 考虑本地，Narrative 可调 StepFun。不得宣传成已实现全离线，也不得假设每个 Agent 独占一个模型。
10. 双视频后端是产品要求；同机并发、模式完全对等和固定秒级延迟仍需技术验证。不能用 API 输出冒充 Spark 输出，也不能用录制素材冒充实时生成。
11. **后续显式修订：所有对玩家显示的系统推荐选项必须已经 Ready。** 未完成渲染／装配的候选可以留在内部调度队列，但不能作为正常可选项展示；动态 Top-K 仍保留，只是 K 同时约束要发布给玩家的 Ready 推荐集。
12. **决策时序分为 Decision Lead Window、UNTIMED 与 TIMED。** 普通剧情选择默认无倒计时；QTE／紧急对话等可以限时并配置确定性超时结果。不得为了等生成而无限慢放当前视频。

13. **Q30–Q35：戏剧控制是显式状态、规则与语义评估组成的逻辑能力，不是第五个常驻编剧 Agent。** Jev 可做快速分类、评分与升级判断；Director 仍负责计划，Narrative 负责具体演绎。
14. **Q31、Q36：阶段是柔性提示，完整 Beat 需要明确戏剧价值，但不能把每个动作都拍成视频。** 小动作可以快速确认或合并处理，不能为了数值推进而强造冲突。
15. **Q33、Q39 与 I02 同时有效。** 世界有独立因果与压力来源；玩家明确选择等待／不行动可以有后果，但普通 `UNTIMED` 节点的现实思考时间、API 延迟不能暗中变成世界惩罚。
16. **Q40 选 B，而不是 C。** 何时收束由 Director 判断；Ending Readiness 只能作参考，不设强制达标分数、固定 Beat 数或软最大长度来替代判断。结局内容仍须遵守世界事实。
17. **Q43 选 C：续杯采用 Arc Closure + New Arc。** 当前篇章可以真正结束；玩家主动继续时继承世界与关系，开启新矛盾。不得撕毁旧结局，也不因可续杯而绕过预算与权限。
18. **Q44：World / Drama 是两个受控状态域。** 所有模型与 Skill 只能提出观察或补丁；确定性的 State Service／Drama State Manager 校验、提交。预测分支不能成为真实伏笔、愿望达成或戏剧债务。
19. **Q48 选 A，而不是 C。** 戏剧效果以真实玩家体验反馈为主要依据；不强制盲测、有／无控制层对照或自动 LLM Judge。Q29 的产品／系统指标及状态正确性测试仍保留。
20. **未被 Q30–Q48 明确选择的队友建议不自动升级为要求。** 不强制每个推荐项显示欲望文案，不强制每次自由输入二次确认，也不把许愿限定为只能在重大节点使用。
21. **Q49–Q54：本地 Agent Backbone 与模型职责已冻结。** Director 使用 `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` 在 DGX Spark 本地运行；Production 默认复用同一本地 Backbone；State 以确定性 `State Manager` 为主体，复杂语义解析复用本地模型。Narrative 固定使用 Step 3.7 Flash API，Scenario Authoring 固定使用 Step 5 Preview API；Jev 继续使用 API。不得把“多个 Agent”误解为每个 Agent 必须各驻留一份模型权重。
22. **Q55–Q61：推荐路径与自由输入路径分离，但共享同一 Branch Contract。** 已 Ready 推荐点击不得重新走慢链；自由输入先经 Jev First Pass，同时把玩家原文与 Jev observation 交给 Director。Director 使用分层工作上下文，Narrative 只接收受限 `ScenePacket`。Top-K 一旦确定，K 条分支完全并行；阶段边界串行、边界内部并行；状态采用 `SELECTED → CANONICAL` 两阶段提交。
23. **Q59 选 B，而不是限并发排队方案。** 成本与并发控制发生在 K 被确定之前；一旦接受 K，K 条候选并行进入 Narrative／Production／H3。分支内部因镜头连续性产生的依赖仍可串行。若供应商硬并发不足，应在锁定 K 前降低 K，而不是把已选择的 K 人为排成长队。
24. **Q62 选 A：v0.5 不把任何固定 latency class 或 P95 数字写成正式 SLA。** 所有阶段必须埋点并记录真实分布，性能门槛在 DGX Spark 与真实 API 跑通后制定；旧版建议阈值不再作为验收承诺。
25. **Q63–Q70：容错、缓存与 Provider Router 已冻结。** Top-K 单分支失败快速重试一次，仍失败则以 K-1 发布；Narrative 主 Step 3.7 Flash、回退本地 Lightning；Director 主本地 Lightning、回退 Step 5 Preview；Production 主本地 Lightning、回退 Step 3.7 Flash；未选分支使用短生命周期缓存及确定性 Dependency Fingerprint；单 Spark 显式切换 `AGENT_LOCAL_PROFILE / VIDEO_LOCAL_PROFILE`；重试、健康、circuit breaker、fallback 与 trace 统一由 Provider Router 管理。
26. **VIDEO_LOCAL_PROFILE 的 fallback 不得被想当然。** 该 Profile 中本地 Lightning 需要卸载以给 Sol-H3 腾出资源，因此 Narrative 的“本地 Lightning fallback”此时不可用。v0.5 仅标记此为运行时约束；若要增加 Step 5 等第二级紧急回退，须另行确认，不能把助手建议自动当成用户决定。


27. **Q71–Q104：角色不是普通资料表，而是跨 Scenario 复用的 Global Character Asset System。** 全局角色拥有稳定身份、多视图 Canonical References、Outfit、Pose/Motion、Voice、版本与使用记录；Scenario 永远消费版本化 Snapshot，不直接绑定可变的 Global Character。
28. **角色生图与编图统一使用 fal.ai Nano Banana 2。** 产品层只暴露 IMAGE_GENERATION / IMAGE_EDIT 逻辑角色；当前 Provider 固定为 fal.ai，文生图 endpoint 为 fal-ai/nano-banana-2，编辑 endpoint 为 fal-ai/nano-banana-2/edit。具体供应商字段只存在 Adapter，不散落在 Character UI 或 Runtime 业务逻辑中。
29. **角色创建固定为三种入口：AI 创建、从图片创建、手动创建。** AI 创建默认生成 2 张候选；纯文字角色允许存在，不因创建角色立即强制产生 API 成本。
30. **Canonical Reference 与生成候选必须分层。** 生成结果先进入 GENERATED/CANDIDATE，用户确认后才能 APPROVED/CANONICAL；Edit 永不覆盖原图；删除 Canonical 前必须指定替代项。
31. **标准角色参考组采用主图 + 多视图。** 用户选定主图后先询问是否生成标准组；标准组为正面头像、3/4 头像、侧面头像、全身正面、全身侧面。批量多视图属于会产生成本的显式操作，必须二次确认。
32. **Outfit 属于同一角色而不是新角色。** Outfit 可拥有自己的正面/侧面/背面/全身参考，但不强制一次生成齐全。角色编辑默认保护脸、年龄、发型与基本体型；产品提供换装、换背景、换表情、换姿势、换视角与自然语言编辑，不在 v0.6 强制复杂 Mask 编辑器。
33. **不建立预生成表情资产库。** 表情默认属于镜头级 Production / Image Edit 条件；姿势与动作则同时支持静态 Pose Reference 和动作视频 Reference。
34. **Character Version 记录重要身份与资产变化，并区分 Change Type。** 主身份、Canonical Reference、标准造型、核心描述/人格、Canonical Voice 等重要变化产生新版本；系统区分 Identity / Appearance / Metadata / Asset Addition 等变化类型。
35. **Global Character 更新不得自动污染已有 Scenario。** ScenarioCharacterSnapshot 固定到选定版本；发现新版本时显示差异，用户选择继续旧版本或升级。Scenario 内修改角色时必须明确选择“仅本故事”或“更新全局”；本地 Override 可人工保存为新的全局角色版本。
36. **Voice 是版本化角色资产。** 一个角色有一个 Canonical Voice 和多个备用 Voice；Canonical Voice 绑定 Character Version，不把任意声音文件自动提升为角色身份。
37. **Production Reference Resolver 自动选择角色参考。** 默认由 Production Planner 根据当前 Scene 从 Character Snapshot 中选择最相关的 2–4 张图片及必要 Voice/Motion；Developer 可覆盖。多角色场景先为每个角色建立独立 Reference Pack，再受全局 Provider 能力与总素材上限约束。
38. **Character Studio 是正式产品页面。** 角色详情至少包含概览、身份、造型、姿势/动作、声音、使用记录、版本；生图/编图既可从 Character Studio 发起，也可从通用 Assets 发起，但角色专用工作流以 Character Studio 为主。
39. **普通用户不显示 API 单次费用或“节省/标准”预算档位。** 成本仍由 Budget Manager / Usage Ledger 记录；批量多视图需要显式确认。标准模式隐藏底层 Prompt，Developer 模式可查看实际 Prompt、Provider、Model、Request/Artifact。
40. **AI 可补全角色描述，但必须经用户确认。** 修改文字描述不会自动重新生成现有图片；系统提示视觉资产与描述可能不同步，并提供“保持现有视觉 / 重新生成 / 编辑现有形象”。
41. **全局 UI 与故事 Theme 是两个不同层级。** 全局 Appearance 支持跟随系统/浅色/深色，UI Size 支持标准/大/特大，字幕支持字号与画内/画外位置；Scenario Theme 不得覆盖用户的全局可读性设置。
42. **浏览器 100% Zoom 是桌面设计基准。** 1366×768、1440×900、1920×1080、2560×1440、3840×2160 均须真实浏览器回归；不得依赖用户把 Chrome 缩放到 150%，也不得用整体 transform/zoom 掩盖字号和布局问题。
43. **模型“写在配置里”不等于已部署。** v0.6 封版必须对 Lightning、Step 3.7、Step 5、Jev、H3 Max、Sol-H3 分别保存真实 health/request/output/model-id/profile 证据；DGX Profile 切换须证明真实服务启停与资源释放，而不是只切枚举。

44. **Q105–Q108：Standard Creator 不再把内部 Schema 直接等价成用户表单。** 一句话／多句话故事描述之后，AI 先给出当前理解，只对高影响且缺失或低置信的内容追问；追问优先给出与当前故事相关的建议选项，并始终保留“其他／自己修改”。完整 DramaSpec 字段属于 Developer／高级编辑面。
45. **Q109–Q112：角色库与 Creator 中的角色必须使用同一管理颗粒度。** Global Character 表达跨故事稳定身份，Scenario Character 表达该故事中的身份、动机、认知、关系与视觉状态 Overlay；两处信息架构一致，只是编辑作用域不同。普通创作不得要求用户手填所有 Desire/Fear/Secrets/Knowledge/Relationships。
46. **Q113–Q115：玩法机制的 Standard UI 是自然语言“怎么玩”说明，不是勾选 Skill 后暴露 JSON。** 创作者用一句话描述玩法，Authoring 将其编译成受验证的 MechanicSpec；Runtime 仍消费确定性 Typed Config。Developer 才显示 Skill ID、版本、触发器和原始配置。
47. **Q116–Q120：Player 是视频优先的沉浸式播放器。** 主沉浸形态是应用内 Theater Mode：Player 独占应用主内容区、隐藏 Sidebar/应用级导航，浏览器本身保持普通窗口；视频舞台占据绝大多数可用空间，Jev/Top-K 推荐固定在视频下方第二层，自由输入固定在最底层且持续可用，HUD 覆盖在视频左上角。Browser Fullscreen 仅作为可选二级播放功能，不能把它等价成产品的“沉浸模式”。
48. **Q120：背包、关系、线索、愿望退出主布局，进入左上角可滑出的 HUD。** 桌面支持 hover 临时展开、点击固定；触屏用点击抽屉。Standard 默认用叙事性关系描述而非裸数值，Developer 可查看精确状态值。
49. **Q121–Q122：Standard Player 不暴露 Runtime／Schema／Pydantic／Provider 错误。** 技术详情进入 Developer Inspector；玩家只看到可恢复的自然语言反馈及“重试／修改／文字继续／退出”等动作。生成中、媒体载入中、播放失败必须是不同状态，不能统一成永久黑屏。
50. **创作端隐藏机器需要的结构，游玩端隐藏机器正在运行的过程。** Standard Mode 以故事意图、角色意图、玩法规则和可玩的选择为中心；Developer Mode 保留完整 Schema、Trace、Provider、版本与原始工件。

### 00.3 本次交付范围

交付 v0.4 完整基线与全部 70 项决策追溯、I01–I05 互动修订、动态戏剧控制、模型／Agent Runtime、用户流程、功能与验收、数据和 Skill 契约、Provider 路由、生成调度、缓存与容错、成本与延迟口径、风险、演示和实施顺序。本轮只依据已提供的文件与对话合并，不增加未经核验的外部模型能力结论。 **不包含已运行的应用、已打包的技能、已验证的模型环境或付费 API 实验结果。** 未掌握团队人数与分工、实际节点权限、API 配额、预算、赛方完整评分细则；这些列入技术／执行依赖，不再通过无限访谈延迟本版交付。

### 00.4 v0.6 阅读与实施入口

| 需要回答的问题 | 优先阅读 |
|---|---|
| 用户究竟选了什么，尤其哪些不是助手推荐项 | 02.3 Q30–Q48、02.4 覆盖关系 |
| 戏剧控制是不是另一个 Agent | 07.8、08.1、08.4 |
| 世界事实、戏剧状态、压力和伏笔由谁写 | 07.9、07.12–07.15、10.5–10.8 |
| 小动作怎样响应，为什么不一定生成视频 | 04.2、04.8、07.10 |
| 结局如何决定，续杯怎样保留历史 | 04.6、07.16、10.9 |
| 新机制怎样与 Ready Gate、UNTIMED、预算兼容 | 02.4、07.12、12.8 |
| 怎样知道戏剧体验改善了 | 16.5、17.3；主要依据是玩家反馈，不是自动总分 |
| Director／Narrative／Production 各用什么模型 | 02.5、08.5、14.2；以 Q49–Q54 和后续 Lightning 锁定为准 |
| 推荐命中与自由输入为什么走不同链路 | 08.2、10.11、12.9 |
| Top-K 怎样并行、失败后怎样降 K | 02.5、08.8、12.2～12.3、12.9 |
| 上下文如何裁剪，Narrative 为什么看不到全部世界 | 08.8、10.12～10.13 |
| Lightning 与 Sol-H3 单 Spark 如何切换 | 14.3、14.7、15.1 |
| Provider fallback、缓存与两阶段提交 | 08.9、12.10～12.12、14.6、15.1 |

| Global Character / Character Studio 怎样工作 | 02.7、06.5、10.15、13.8 |
| 角色生图、编图与 Nano Banana 2 路由 | 13.8、14.2.1、FR-085～086／097 |
| Character Version、Snapshot、Local Override | 10.15、FR-090～091、AT-68～70 |
| H3 怎样自动选角色参考 | 13.8、FR-093、AT-71～72 |
| 100% Zoom、全局显示设置与响应式 | 06.6、FR-098～100、AT-74 |
| 怎样证明模型真的部署而不是只配了环境变量 | 14.9、17.1、AT-75～76 |

AI 开发代理不得只读新增章节而忽略三模态素材、双后端、Ready Gate、状态隔离等已有 P0 要求；也不得只看旧 v0.4 模型候选表而忽略 v0.5 已锁定的 Lightning／StepFun 路由。新字段和伪代码是项目设计契约，不是任何模型已原生支持的接口。

## 01. 原始构想还原

### 01.1 产品问题

用户以 B 站互动视频为参照：玩家能通过选项观看不同片段，也可能遇到好感度、收集、QTE 等机制；但这些体验依赖预制视频与固定选项。用户希望突破的不是按钮的外观，而是 **玩家想到系统没有列出的行动，或想影响后续剧情时，产品仍能响应** 。

普通人直接使用视频模型还有三道门槛：不会把想法写成有效生成提示词，不会调用 API 或部署模型，以及不知道下一步该怎样发展。平台必须同时提供自由输入、可选建议、预设世界和自动生产链路，而不能只提供高级 Prompt 编辑器。

### 01.2 原始意图追溯表

| 意图 ID | 用户第一次输入的实质内容 | 本文如何落实 | 不能被替换成什么 |
|---|---|---|---|
| O01 | 玩家可自定义剧情的互动视频／短剧 | 角色行动、对话、许愿、状态化生成 | 纯视频生成表单或固定分支匹配 |
| O02 | 基于高速 MiniMax H3 Max／Sol-H3 | 云端体验主路 + Spark 本地视频后端 | 自研基础视频模型作为前置条件 |
| O03 | 有选项，也要比传统互动视频更自由 | 2–3 个可选建议 + 始终可用的自由输入 | 只推荐、不接受计划外行为 |
| O04 | 有好感度、收集、QTE 等互动机制 | Scenario 可组合 Mechanic Skills；MVP 至少贯通一种 | 要求一次实现所有游戏类型 |
| O05 | 用户不会写提示词和调用参数 | 意图编译、分镜、参考映射、Provider 参数适配 | 把模型参数再次全部暴露给用户 |
| O06 | 用户有时没有剧情想法 | 预设 Scenario、AI 创作入口、建议行动 | 空白输入框让用户从零设计世界 |
| O07 | 自定义界面风格，和美工协作 | 可配置主题与素材；美术负责视觉资产 | 运行任意用户生成的 JavaScript |
| O08 | 自动剪辑、拼接 2–3 个 5–10 秒片段 | Story Beat／Shot 分层、视频装配与音频处理 | 仅返回若干下载链接让用户手动剪 |
| O09 | 本地 NVIDIA／StepFun、多 Agent、Skill 设计 | 四个运行时 Agent、真实 Skills、混合模型与可观测性 | 为了数量堆 Agent 或把 CRUD 都叫 Skill |
| O10 | 期待 Jev 高速判断发挥作用 | 意图路由、玩法触发、候选排序、升级决策 | 把 Jev 当作开放式编剧或视频模型 |
| O11 | 通过问答把重大假设逐步明确 | 原始 29 项及后续 Q30–Q48 逐一保留，记录 I01–I05 与新选择的覆盖关系 | 把助手推荐自动当成用户选择 |


### 01.2.1 v0.6 角色资产系统新增原始意图

用户进一步明确：全局“角色”应接近 LibTV / Google Flow 一类可持续复用的角色管理体验，而不是只有姓名、人格和几个 Asset ID。角色应能够在平台内创建视觉形象、编辑既有形象、形成稳定多视图与造型资产，再被不同 Scenario 以版本化 Snapshot 使用。由此新增意图 O12：

| 意图 ID | 用户确认的实质内容 | v0.6 如何落实 | 不能被替换成什么 |
|---|---|---|---|
| O12 | 跨项目全局角色库应同时承担角色生图、编图、稳定身份资产与后续视频参考管理 | Character Studio + Nano Banana 2 Image Router + CharacterVersion + ScenarioCharacterSnapshot + Production Reference Resolver | 只有文本 CRUD、只上传图片不生产、或让每个 Scenario 各自复制一份不可追踪素材 |

这一增量不改变 O01–O11；角色系统的目标是降低视频生产中的身份素材准备成本，并保持跨故事复用与版本稳定性，而不是把产品扩展成通用 Photoshop。

### 01.3 初始速度判断的地位

用户提出的体验依据是：H3 Max 约 2–3 秒生成 5 秒 768p 视频，Sol-H3 在 Spark 上约 60 秒完成同类输出。外部资料确实存在相近展示：fal 公布 H3 Max 的 5 秒 768p 样例用时 2.78 秒；Sol-H3 Spark 页面公布约 56 秒热态端到端数据。[S01][S04]

 **这些是厂商／项目方特定条件下的数据，不是本产品每轮交互的 SLA。** 参考素材上传、Prompt 扩展、排队、多个 Shot、重试、下载、拼接、播放器缓冲和冷启动均可能增加等待。本产品的目标是利用这些能力改善体验，而不是先宣布任何输入都能 3 秒生成完整短剧。

## 02. 全部 104 项选择与最终解释

本节保留 Q01–Q29 原始选择、I01–I05 互动修订、Q30–Q48 动态戏剧控制、Q49–Q70 模型／Agent Runtime，以及 Q71–Q104 Character Studio，共 104 项问答决策。字母保留用户原选项；括号补充优先于助手当时的示例。旧决定与后续选择有冲突时，按 02.4 明确覆盖，不静默保留两套互斥实现。

| 决策 ID | 最终选择 | 确认的内容与用户补充 | 对实现和验收的影响 |
|---|---|---|---|
| Q01 | C | 受世界规则约束的开放剧情 | 固定世界，开放路径；自由输入不得被强制映射到已有视频 |
| Q02 | B | 创作者发布 Scenario Package，玩家进入游玩 | 产品具有 Creator／Player 两种工作流；MVP 用一部高质量预设验证 |
| Q03 | C | H3 Max API + Spark Sol-H3 双视频后端 | 统一任务接口，分别记录能力与延迟；不要求两者同速 |
| Q04 | D | 初始认可预测预生成 + 互动机制减轻等待 | 预测保留；等待期互动机制后来被 Q18 C 收敛为非 MVP 必做 |
| Q05 | C | 玩法以 Mechanic Skills 组合 | Runtime 提供状态与 UI 基础，不把所有故事写死成同一套玩法 |
| Q06 | B | Director、State、Narrative、Production 四个核心 Agent | 按职责隔离上下文和工具；不等于四份独立权重或四个服务 |
| Q07 | C | 结构化状态 + Event Log + Narrative Memory | 明确事实、事件和叙事记忆的权威关系 |
| Q08 | C | Canonical Assets + Continuity Skill | 长期身份、临时视觉状态、上一镜头共同约束生产 |
| Q09 | B | 优先在世界内把不合理行动圆回来 | 保留表达的真实意图，避免生硬报错；既定世界硬规则仍不得被暗改 |
| Q10 | C | AI Authoring Copilot + Structured Editor | 一句话起稿，表单／自然语言局部修改，发布为可加载包 |
| Q11 | C | 玩家既是角色也像导演；主视角是角色扮演，通过“许愿”影响故事 | 主入口行动／对话，次入口许愿；Wish 是未来偏好，不是即时世界补丁 |
| Q12 | C | Narrative Beat；用户强调一般生成 Jev 高概率的两三个选项，多了成本爆炸 | 区分候选分支数和每分支 Shot 数；生产预算覆盖两者及重试 |
| Q13 | B | Skill 只提出修改建议，State 统一提交 | 所有世界修改走有版本、有来源、可校验的 Proposal |
| Q14 | C | 强类型外壳 + 自然语言内容 | 机器字段可校验，剧情文本保持表达能力 |
| Q15 | C | Manifest + Typed Data + Narrative Files + Assets + Skills | Scenario 可导入、版本化、解析和校验；故事设定不能散落在业务代码 |
| Q16 | B | Jev 承担快速离散判断 | 路由、触发、排序、轻量一致性和升级；不承担开放式生成 |
| Q17 | B | 依据分布、预算、队列动态 Top-K，正常 K∈{1,2,3}；后续明确“所有显示选项必须 Ready” | 动态 K 仍决定投机规模，但系统推荐只有在对应分支完整 Ready 后才能发布；此前“显示数不等于预生成数”的解释被后续决策覆盖 |
| Q18 | C | 未命中时显示 AI／主题化加载动画 | 不强制即时对话、调查或小游戏作为等待填充；不得假进度 |
| Q19 | C | Story Spine + Rolling Horizon；未来剧情多用 Jev 预测，降低视频生成成本 | 大部分前瞻停留在文本状态层，只有近端少量候选被媒体化 |
| Q20 | C | Ending Families + 根据本局历史动态生成结局 | 结局内容不照搬固定视频；何时收束及结束后如何继续由后续 Q40 B、Q43 C 补充 |
| Q21 | C | 模型 Provider 可替换；Jev API、视频可 API，State／Director 考虑本地，Narrative 可 StepFun API | 默认混合部署；本地模型选型、共驻和中文质量必须实测 |
| Q22 | C | 图片 + 声音 + 视频素材全部支持 | 三类素材有角色／用途绑定、预览、引用和生成消费 |
| Q23 | C | 真正可复用的能力做成 Skill，基础设施不 Skill 化 | 区分 Skill、工具、Agent、Runtime；复用官方 Prompt 经验并明确原创边界 |
| Q24 | C | 一个完整 Vertical Slice + Creator Flow | 既展示创作到游玩的闭环，也展示自由行动、Wish、玩法和双后端 |
| Q25 | A | 三类素材在 MVP 全部完整实现 | 明确否决“仅图片可用、音视频留接口”的减范围方案 |
| Q26 | B | 主互动走 H3 Max；现场提交并展示真实 Sol-H3 本地任务 | 本地任务可在讲解期间运行；需要资源切换及来源证明，不必本地跑完整局 |
| Q27 | C | 延迟—成本权衡，不孤立追求命中率 | 同时测等待和浪费，设置总预算与投机预算上限 |
| Q28 | B | 用 Skill 调用日志证明真实执行 | 输入输出摘要、工件、耗时和下游可追踪；不强制现场卸载／安装对照 |
| Q29 | C | 产品指标 + 系统指标两套保留 | 用户体验、自由行动、完成率与决策／生成／状态指标同时验收 |

### 02.1 v0.3 增量决策：互动时序、Ready Gate 与玩家偏好

以下内容来自 Q01–Q29 冻结后与队友继续讨论，并由用户再次显式确认。它们不是对 29 项原决定的重做，而是对 **互动视频时序与投机发布策略** 的增量约束。若与 v0.2 中的派生解释冲突，以本节为准。

| 增量 ID | 用户确认的修订 | PRD 含义 |
|---|---|---|
| I01 | Decision Lead Window | 下一组选项可以在当前视频真正分叉点之前出现；此后继续播放的内容必须对所有候选分支都成立，以便把观看时间与思考／预生成时间重叠 |
| I02 | Interaction Timing Mode | 每个互动事件声明 `UNTIMED` 或 `TIMED`；普通 Narrative Decision 默认 `UNTIMED`，QTE／紧急对话等可为 `TIMED` |
| I03 | Timed Interaction Timeout | `TIMED` 事件必须由 Scenario 声明确定性 timeout fallback，例如对话沉默、QTE 失败、战斗受击；超时不能由模型临场随意决定 |
| I04 | Session Player Preference State | Jev 排序除当前世界／剧情状态外，还可读取本局近期真实选择形成的偏好信号；MVP 仅 session-scoped，跨 Scenario 持久画像不是 P0 |
| I05 | 所有显示的系统推荐选项必须 Ready | 系统推荐分支在视频完整生成、装配、版本校验通过之前不能作为正常可选项显示；自由输入仍始终允许，因此自由输入仍可能真实 miss |

**覆盖关系。** I05 只覆盖 v0.2 中“显示选项数可以大于预生成数”的派生解释，不推翻 Q17 的动态 Top-K，也不取消 Q18 的 miss 加载动画。新的语义是：调度器先决定 K，再在内部完成 K 条候选；若在发布截止前无法全部 Ready，可以在发布前下调 K，或进入短暂等待，但不能把未 Ready 的分支展示给玩家。

### 02.2 冲突合并与解释边界

 **Q04 与 Q18：** 采用“投机预生成 + 未命中加载动画”。恋爱值、收集、QTE 仍可以是剧情玩法，但不因此变成必须用来拖延玩家的等待工具。

 **I05 与 Q18：** 正常点击系统推荐项时，按契约不应再出现“为该选项现生成视频”的等待，因为推荐项只有 Ready 后才能显示。Q18 的加载动画主要服务于自由输入、缓存失效、后端失败恢复或其他真实未命中。

 **Q22、Q25 与 Q24：** 三类素材全部进入 MVP，不因一个纵向样板而减少素材类型。范围控制应发生在题材数量、编辑器复杂度、玩法数量和用户规模上，而不是删除明确坚持的音视频能力。

 **Q12 与 Q17：** 通常目标是两三个候选，动态 K 仍可在 1–3 内根据预算、队列和截止时间调整；但 **系统推荐集只有在其中每个待显示分支都 Ready 后才发布**。因此 v0.2 的“显示选项数不等于预渲染数”解释失效。每条分支的镜头数量仍是独立预算维度；此前“每 Beat 默认 1–2 Shot、最多 3 Shot”属于工程默认建议，不是用户单独确认的固定业务常数。

 **Q13 与实现安全：** “State Agent 提交”是权责定义。其最终数据库写入应由确定性 State Service 执行版本校验与事务，不靠另一次 LLM 判断代替数据库约束。Q44 将同样原则扩展到 Drama State；二者可以共享数据库事务，不要求另建一个 Agent。

 **Q28 与能力验证：** 无需把现场技能热插拔作为演示任务，但仍须做离线契约测试，不能用可编辑字符串伪造成功日志。

### 02.3 Q30–Q48：动态戏剧控制的最终决策

动机来自队友的《AI 原生互动短剧 PRD 产品修改建议》：自由输入被接受，不等于故事有递进；玩家决定行动，系统组织世界回应、冲突、揭示与收束。该文件是讨论稿，**最终范围以本表用户选择为准**，不能将讨论稿自称的共识或助手示例直接覆盖用户决策。

| 决策 ID | 最终选择 | 用户确认的方案与补充 | 落实与限制 |
|---|---|---|---|
| Q30 | C | Typed Dramatic State + Rules + LLM Evaluator；“这又是一个 jev 可以使用的地方” | 结构化状态和确定性规则兜底，Jev 做快速评估，复杂语义交给 LLM；不增加第五个常驻 Agent |
| Q31 | C | Soft Phase／柔性戏剧阶段 | 可跳跃、重叠、回落；阶段提示不得阻止玩家已合法达成的进展 |
| Q32 | C | 双时间尺度评估 | 普通 Action 先做重要性判断；高影响 Action 即时重规划；完整 Beat 后必须评估 |
| Q33 | C | 世界独立前进，玩家承担不行动的后果 | 使用已建立的时间、NPC 目标与机会窗口；不强迫玩家回主线，不惩罚 UNTIMED 的现实思考时间 |
| Q34 | C | Confidence-Gated Desire；“置信度也可以依赖 jev” | 区分 action／desire／strategy；高置信直行，中置信可纠正回显，低置信且高影响先澄清；推断不等于玩家真实动机 |
| Q35 | C | Dramatic Directive | 输出需要的戏剧功能、目标变化、约束与可用机会，不直接规定固定事件 |
| Q36 | C | Progress Vector + Minimum Dramatic Value | 完整 Beat 需说明改变了什么、承担什么功能；低价值行动可快速确认或合并，不强行生成视频 |
| Q37 | C | Truth Model + Twist Candidate + Readiness Gate | 事实稳定，理解可改变；反转有前文证据、预期依据与后续影响，不随机改真相 |
| Q38 | C | Foreshadow Ledger | 支持作者预埋与运行中新生伏笔，注册、铺设、加强、回收或放弃均可追溯 |
| Q39 | C | Pressure Sources | 压力来自既有设定、NPC 行动及真实后果；Drama Control 组织呈现，不能为了刺激凭空制造灾难 |
| Q40 | **B** | **Director 自行判断何时结束；“用户还想玩可以继续续杯”** | 不采用 Q40 C 的 Readiness Vector + Soft Length Budget 强制收束；事实摘要可辅助，决定权归 Director |
| Q41 | C | Wish Ledger + Dramatic Opportunity | 愿望显式记录、寻找合乎因果的实现机会，允许部分达成、失败或被替换；不能改写过去 |
| Q42 | C | 允许退出矛盾并形成 Consequence Ending | 拒绝主线可以真正结束当前篇章；后果基于已有世界，不以额外灾难惩罚“不配合剧情” |
| Q43 | C | Arc Closure + New Arc | 当前 Arc 真正关闭；主动续杯继承世界与关系，建立新问题、矛盾和压力，不撕毁旧结局 |
| Q44 | C | Drama Store + Proposal／Commit | Drama State Manager 作为 Runtime 模块校验、提交；Director／Narrative／Jev／Skills 只能提案 |
| Q45 | C | Jev = Observable Decision；LLM = Semantic Judgment | Jev 分类、评分、排序、置信与路由；长程语义及高影响判断升级；高置信不豁免事实／权限检查 |
| Q46 | C | Constraint + Priority + Opportunity | 硬约束优先，维护 Pending Obligations／Drama Debt，再按当前情境寻找自然机会；不以债务强迫玩家行动 |
| Q47 | C | AI Draft + Structured Review | Authoring 自动生成戏剧结构；Creator 用简明问答／表单接受、修改或局部重生成，不必手填专业术语 |
| Q48 | **A** | **看最终用户是否喜欢，通过真实用户体验判断** | 玩家反馈是戏剧效果主要依据；不将盲测、控制层开关对照或自动 Judge 纳入本次必做 |

**原始选择记录：**

```text
Q30 C（这又是一个jev可以使用的地方）
Q31 C
Q32 C
Q33 C
Q34 C（置信度也可以依赖jev）
Q35 C
Q36 C
Q37 C
Q38 C
Q39 C
Q40 B（用户还想玩可以继续续杯）
Q41 C
Q42 C
Q43 C
Q44 C
Q45 C
Q46 C
Q47 C
Q48 A
```

### 02.4 v0.4 覆盖关系与未自动采纳项

| 涉及的旧解释／讨论建议 | v0.4 的有效规则 | 来源 |
|---|---|---|
| 每次自由行动都必须产出完整 Beat 和新视频 | 每次已接受行动都有恰当反馈；分为快速确认、合并、完整 Beat。重要计划外行动仍必须能产生新剧情与新视频 | Q32、Q36；更新 FR-010、PM-02 |
| 阶段须依次进行，或以数值门槛允许进入结局 | 阶段柔性；反转成立条件保留，但结局时机由 Director 判断，不能用 Ending Readiness 分数或轮数门槛代替 | Q31、Q37、**Q40 B** |
| 达到结局就终止整个 Session／世界 | 关闭当前 Arc；用户可主动开启下一 Arc，事实和关系持续存在 | Q43 |
| “世界不断推进”可以解释为输入慢／API 慢就损失机会 | 保留 I02。默认按已提交的故事行动及授权事件推进世界；真实思考、加载不冒充角色等待。仅明确 TIMED 节点有现实倒计时 | Q33、Q39 + I02、I03；实现细节为 DERIVED／PROPOSED |
| 所有模型都可以直接调整戏剧分数 | 单一 Drama State Manager 提交；模型提出观察与补丁，确定性代码校验 | Q44 |
| 候选渲染出来就算伏笔已铺设／愿望已达成 | 投机世界与投机戏剧状态同时隔离；只有真实提交、按可见性确认的事件才能支撑相应结论 | Q38、Q41、Q44 + 原状态隔离 |
| 因为有文本快速反馈，可以把未生成视频的系统推荐也显示出来 | **不得。** I05 保持：正常剧情推荐面板的已显示项仍有完整 Ready 视频。文本快速反馈用于玩家自主输入的小动作或独立机制操作，不借机放宽 Ready Gate | I05 + Q36 |
| 所有欲望推断都要求二次确认 | 按 Q34 的置信与影响程度分流；不能替玩家锁定动机 | Q34 |
| 队友建议每个推荐项都加欲望副标题 | 可作为 UI 建议，尚不是独立确认的必做；显示时不得剧透或将推断当事实 | PROPOSED，非新增 USER 约束 |
| 队友建议仅重大节点可许愿 | 本轮没有选择这项限制，保留既有许愿入口；重大节点主动提示可选，不能禁止平时主动表达 | Q11、Q41；入口提示为 PROPOSED |
| 使用盲测、有／无 Drama Control 对照和自动结构分数证明戏剧提升 | 用户最终选 Q48 A，以真实玩家是否喜欢、为何喜欢／不喜欢为主；工程校验和 Q29 指标仍保留，但不是“有趣”的替代证明 | **Q48 A**、Q29 |
| 因为用户可续杯，模型应永远不结束／预算可以自动重置 | Director 可以形成自然结局；继续由玩家选择，预算、授权和安全边界不自动解除 | Q40、Q43 + FR-034 |

对旧版示例中的 `ending_readiness < 0.5`、`target_beats=12 / soft_max=16`、“当前 Arc 必须因轮数而收束”等，本版不予固化。它们是曾被讨论的示例，不是用户最终选定的强制规则。


### 02.5 Q49–Q70：模型、Agent Runtime、Provider 与容错的最终决策

本节来自 v0.4 之后对“每个 Agent 用什么模型、调用 API 还是本地部署、如何并行与降级”的连续问答。Q50、Q51 存在用户后续直接改写，因此以“最终锁定”而非最初选项字母为准。

| 决策 ID | 最终选择 | 用户确认的方案与补充 | 落实与限制 |
|---|---|---|---|
| Q49 | C | 一个共享本地 Backbone + 不同 Agent Prompt／Skill | Director、Production、State semantic fallback 共用本地服务；不按 Agent 复制权重 |
| Q50 | **最终锁定** | **Director 本地使用 NVIDIA Nemotron 3.5 Lightning 30B-A3B NVFP4** | 不再把 Nemotron 3 Super 或 Qwen 当主 Director 候选；中文剧情规划仍需本项目实测 |
| Q51 | **用户改写** | Narrative 固定 Step 3.7 Flash API；Scenario Authoring 固定 Step 5 Preview API | 不做“普通 Beat／高潮动态切模型”的自动路由；Authoring 是低频高质量任务 |
| Q52 | C | State Manager + Semantic Model | Canonical State 由确定性服务拥有；复杂语义解析按需复用 Lightning，不把数据库事务交给 LLM |
| Q53 | B | 单 Spark 双 Runtime Profile；架构兼容未来双 Spark | `AGENT_LOCAL_PROFILE` 跑 Lightning，`VIDEO_LOCAL_PROFILE` 跑 Sol-H3；切换是明确服务级操作 |
| Q54 | B | Production 默认本地 Lightning + `h3-production` Skill | Narrative 不越权直接生成最终 H3 请求；Production 仍有独立契约 |
| Q55 | C | 双 Pipeline + 同一 Branch Contract | Ready 推荐点击直接复用 Branch；自由输入才创建新 Branch；底层状态与媒体契约一致 |
| Q56 | C | Jev First Pass + 玩家原文一起交 Director | Jev observation 是辅助观察，不替代原文，不作为事实真相 |
| Q57 | C | Hierarchical Working Context | Director 默认看 Scenario Core、相关 Canonical Slice、Drama State、Arc Summary、最近重要事件与按需检索，不塞全量 Event Log |
| Q58 | C | Narrative 使用受限 `ScenePacket` | Director 知道全局故事；Narrative 只获得本场景必要真相、角色知识、允许／禁止揭示与风格，不自行重新导演 |
| Q59 | **B** | Top-K 分支全部完全并行 | 一旦 K 已锁定，K 条分支并行 Narrative／Production／H3；成本与并发约束在锁 K 前解决 |
| Q60 | C | 阶段边界串行，边界内部并行 | Jev→Director Skeleton 必须先冻结；之后 Narrative、素材检索、连续性准备等按 DAG 并行 |
| Q61 | C | Two-Phase Canonicalization | 点击后 Branch 进入 `SELECTED` provisional view，可立即规划 N+2；媒体确认可播放后才 `CANONICAL` 提交，失败则回滚 provisional |
| Q62 | **A** | 暂不规定固定延迟等级／SLO | 先实现并完整 tracing；用实机分布决定后续 P50／P95 目标，不把示例阈值写成合同 |
| Q63 | C | 单分支快速重试一次，仍失败则 K-1 发布 | 失败分支不能拖死整个 Ready 推荐集；重试次数 1 属于本次 USER 决策 |
| Q64 | C | Narrative：Step 3.7 Flash 主、Lightning 本地回退 | timeout／5xx／rate limit／连续 schema failure 等由 Provider Router 触发回退；VIDEO_LOCAL_PROFILE 下该本地回退不可用 |
| Q65 | **B** | Director：Lightning 本地主、Step 5 Preview API 回退 | Director 属于高影响规划节点，fallback 优先保质量；不采用 Step 3.7 作为首个 Director fallback |
| Q66 | C | 未选分支短生命周期 Branch Cache | 未选媒体与 Branch Proposal 可暂存，但永不自动进入 Canonical World／Drama |
| Q67 | C | Dependency Fingerprint 判定缓存复用 | 使用确定性依赖版本／事实指纹，不让 LLM 以“看起来差不多”决定复用 |
| Q68 | B | 显式 `AGENT_LOCAL_PROFILE / VIDEO_LOCAL_PROFILE` | 切换需 drain、持久化、卸载、清理、启动、health check、router switch；不是假设同驻 |
| Q69 | B | Production：Lightning 本地主、Step 3.7 Flash API 回退 | 在 VIDEO_LOCAL_PROFILE 等本地 Backbone 不可用时仍保留 Production 职责与同一 Skill／Schema |
| Q70 | B | 统一 Provider Router | 集中管理 timeout、retry、health、circuit breaker、fallback、route、cost／trace；Agent 不自行散落降级逻辑 |

**最终模型矩阵：**

```text
Jev Fast Plane        → Jev API
Director              → Nemotron 3.5 Lightning local
                         fallback: Step 5 Preview API
State Manager         → deterministic runtime
State semantic        → reuse Lightning when needed
Drama Control         → rules + Jev + Director; no extra foundation model
Narrative             → Step 3.7 Flash API
                         fallback: Lightning local when available
Scenario Authoring    → Step 5 Preview API
Production            → Lightning local + h3-production Skill
                         fallback: Step 3.7 Flash API
Cloud Video           → H3 Max API
Local Video           → Sol-H3 on DGX Spark
Assembly              → FFmpeg / deterministic runtime
```

### 02.6 v0.5 覆盖关系与旧解释失效项

| 旧解释／早期建议 | v0.5 最终规则 | 来源 |
|---|---|---|
| Director 本地模型仍在 Qwen／Nemotron Super／Lightning 间待选 | **锁定 Nemotron 3.5 Lightning 30B-A3B NVFP4** | Q50 后续用户明确锁定 |
| Narrative 可按戏剧重要性动态在 Step 3.7／Step 5 间切换 | Narrative 固定 Step 3.7 Flash；Step 5 Preview 用于 Scenario Authoring 与 Director fallback | Q51、Q65 |
| State 是完整 LLM Agent | Canonical State 由 State Manager 负责；LLM 只做必要语义解析／提案 | Q52 + 既有 Q13／Q44 |
| Top-K 选定后可再用并发预算把部分分支排队 | **Q59 B：锁定 K 后全并行。** 供应商并发不够时应先降低 K | Q59 |
| 投机时优先完成 Top-1，再扩展其他候选 | 不再作为默认策略；所有被纳入 K 的分支同步开始，分支内部依赖例外 | Q59 |
| 点击 Ready 推荐后再重新走 Director／Narrative 链 | 不允许；复用已冻结 Branch Contract，只做版本与前置条件校验、两阶段提交 | Q55、Q61 |
| Narrative 可以读取完整 World／Drama 上下文 | Narrative 读取最小 `ScenePacket`，全局重规划归 Director | Q58 |
| Director 每轮读取完整 Event Log | 使用 Hierarchical Working Context + 检索；全量日志只作为权威存储 | Q57 |
| 旧版 P95 数值可当交付目标 | v0.5 暂无正式性能 SLA；只要求真实 tracing 与后续基准制定 | Q62 |
| 未选缓存由整体版本粗失效即可视为最终方案 | v0.5 选定短 TTL + Dependency Fingerprint；首版可保守失效，但目标契约已确定 | Q66、Q67 |
| 单 Spark 里 Lightning 与 Sol-H3 可尝试热共驻 | 显式 Profile 切换，不承诺共驻；切换期间按 Provider fallback 继续核心文本链 | Q53、Q68 |
| 各 Agent 各自处理 timeout／fallback | 统一 Provider Router 处理 | Q70 |



### 02.7 Q71–Q104：Global Character / Character Studio 最终决策

以下编号将本轮角色问答顺延为全局 Q71–Q104。另有一项不占问答编号的 USER 锁定：角色生图与编图统一使用 fal.ai Nano Banana 2，以减少额外 API 供应商数量。

| 决策 ID | 最终选择 | 确认内容 | 对实现与验收的影响 |
|---|---|---|---|
| Q71 | B | 新建角色：AI 创建 / 从图片创建 / 手动创建 | 不强迫所有角色立即生成图片；三入口都落到同一 GlobalCharacter |
| Q72 | B | 主身份图 + 多视图 Canonical References | 角色身份不是单张图字段 |
| Q73 | B | AI 创建默认 2 张初始候选 | 两张都先是 Candidate，用户选定后再提升 |
| Q74 | B | 选主图后弹窗询问是否生成标准角色图组 | 不未经确认批量烧 API |
| Q75 | B | 标准图组：正面头像、3/4 头像、侧面头像、全身正面、全身侧面 | 用统一 reference_role 标记并可单独重做 |
| Q76 | B | 换衣服属于同一角色下的 Outfit | 不为每套衣服复制一个新角色 |
| Q77 | B | Outfit 可拥有自己的正/侧/背/全身参考 | 不强制一次补齐 |
| Q78 | B | Edit 默认锁定脸、年龄、发型、基本体型 | 身份保护是默认行为；仍需输出质量验收 |
| Q79 | B | 快捷编辑 + 自然语言编辑 | 快捷项包括换装/背景/表情/姿势/视角，自由文本始终可用 |
| Q80 | B | Edit 永不覆盖原图，产生新 Candidate | 原资产保留，用户确认后才能替换 Canonical |
| Q81 | B | 提供语义“局部修改”，首版不做复杂 Mask 编辑器 | 底层仍可由 Nano Banana 2 完成整图编辑 |
| Q82 | A | 不建设固定表情资产库 | 表情进入镜头级 Prompt / Edit，而不是预生成六宫格 |
| Q83 | C | 静态 Pose + 动作视频 Reference 都支持 | Pose 与 Motion 都可参与 Production |
| Q84 | C | 身份图、声音、标准造型、核心描述/人格等重要变化产生 Character Version | 版本粒度足以保护已有 Scenario |
| Q85 | B | 自动区分 Change Type | 至少支持 Identity / Appearance / Metadata / Asset Addition |
| Q86 | B | Global Character 更新后已有 Scenario 保持 Snapshot，不自动同步 | 通过差异页选择继续旧版或升级 |
| Q87 | B | 一个 Canonical Voice + 多个备用 Voice | 不把角色限制成单一不可替换音频 |
| Q88 | B | Canonical Voice 与 Character Version 绑定 | 声音变化能被 Snapshot 与 Production 追踪 |
| Q89 | C | Production Planner 自动选 Reference，Developer 可覆盖 | 普通玩家/创作者不逐幕手工拼 Provider 参数 |
| Q90 | B | 每幕动态选最相关 2–4 张角色图片 | 不把全部角色图库塞给视频模型 |
| Q91 | B | 多角色先各自构建 Reference Pack，再控制总素材数量 | 保持角色隔离并遵守 Provider 总上限 |
| Q92 | B | 角色详情采用 Character Studio | Tabs：概览/身份/造型/姿势动作/声音/使用记录/版本 |
| Q93 | C | 生图入口同时存在于 Character Studio 与 Assets | 角色专用流程在 Studio，通用生成在 Assets |
| Q94 | B | 允许无图片的纯文字角色 | Production 真正需要视觉身份时再提示补资产 |
| Q95 | A | 普通生成前不显示预计费用 | 成本留在 Budget/Developer，不污染创作主流程 |
| Q96 | A | 不提供节省/标准等预算模式 | 不把候选数包装成用户必须理解的推理档位 |
| Q97 | B | 批量生成多视图前必须二次确认 | 这是成本确认，不显示具体金额 |
| Q98 | B | AI 自动补全结构化角色描述，但用户确认后写入 | 不把模型推断直接变角色事实 |
| Q99 | B | 生图 Prompt 标准模式隐藏、Developer 模式可见 | 普通用户编辑人物意图而非供应商 Prompt |
| Q100 | B | 修改角色文字描述不自动重新生图 | 显示视觉可能过期，并提供保持/重生/编辑三个动作 |
| Q101 | B | 图片资产状态：GENERATED/CANDIDATE/APPROVED/CANONICAL/ARCHIVED | 生命周期可审计 |
| Q102 | B | Canonical Image 不能直接删除，必须先选择替代 Canonical | 防止 Scenario / Production 引用悬空 |
| Q103 | C | Scenario 修改角色时选择“仅本故事”或“更新全局” | 前者创建 Local Override，后者产生受控 Global Version |
| Q104 | C | Scenario Local Override 可人工保存为新的全局角色版本 | 不自动反向污染 Global Character |

**IMAGE-01（USER）：** 角色 Image Generation 与 Image Edit 统一通过 fal.ai。当前锁定 endpoint 为 fal-ai/nano-banana-2 与 fal-ai/nano-banana-2/edit。Provider 能力升级可以替换 Adapter，但不得在没有用户确认的情况下改变产品层角色工作流或把另一个收费供应商设为默认。

### 02.8 Q105–Q122：AI 引导式 Creator、统一角色颗粒度、自然语言玩法与沉浸式 Player

以下决策来自 2026-09-24 的连续产品讨论，均为 USER 明确认可的产品方向。它们不改变既有 Runtime 的 World/Drama 双域、Ready-only Recommendation、Character Snapshot、Mechanic Skill 与 Provider 架构，而是重新定义 Standard Mode 如何把这些能力呈现给创作者和玩家。

| 决策 ID | 最终选择 | 确认内容 | 对实现与验收的影响 |
|---|---|---|---|
| Q105 | USER | Standard Creator 默认不展示一组空白内部 Schema 表单 | 用户先看到 AI 当前理解、缺失项与少量待确认问题；完整原始字段进入高级/Developer 编辑 |
| Q106 | USER | “戏剧结构”定位为对一句／多句话故事描述的深化追问层 | DramaSpec 是 Runtime 数据结构，不是 Standard UI；页面负责帮助用户形成 DramaSpec |
| Q107 | USER | 缺失内容优先提供与当前故事相关的建议选项，并保留自由修改 | AI 高置信内容可自动补全；中低置信／高影响内容再追问。具体 confidence 阈值为可配置实现细节，不作为不可变产品常数 |
| Q108 | USER | Standard Drama 按自然语言主题组织，而非逐字段暴露 Core Question/Truth Model 等内部结构 | 至少覆盖“故事真正想问什么／背后真相／推动故事的压力／可能结局／绝对不能发生什么”；伏笔、限时互动等高级项可折叠或 Developer 查看 |
| Q109 | USER | Global Character 与 Creator Character 使用同一信息架构和管理颗粒度 | 两个入口不能把同一个角色定义成两种互不兼容的对象 |
| Q110 | USER | 角色强制必填保持最小化 | Global 最低为名字 + 一句话角色定义；Scenario 至少明确本故事身份/作用，其余人格、动机、秘密、认知、关系、视觉状态允许 AI 建议或选填 |
| Q111 | USER | Scenario Character 是 Global Character Snapshot 上的故事级 Overlay | Desire/Fear/Secrets/Knowledge/Relationships/Visual State 默认属于当前故事状态，不静默回写 Global |
| Q112 | USER | 角色编辑也遵循“AI 先理解、用户确认缺失项”的创作方式 | 不要求创作者面对一排空白 Desire/Fear/Secrets 等 textarea；AI 可生成建议，用户确认、修改或忽略 |
| Q113 | USER | Standard Mode 的玩法机制显示为自然语言“游戏教程／玩法规则” | 不以“勾选关系变化／线索调查／道具系统／限时互动 + JSON 参数”作为默认创作界面 |
| Q114 | USER | 创作者可以一句话描述希望故事“怎么玩” | Authoring AI 将自然语言编译成 MechanicSpec Proposal，经 Schema/权限校验后形成 Runtime Typed Config；自然语言不是 Runtime 配置格式 |
| Q115 | USER | 玩法以可读规则卡管理 | Standard 可查看、调整、移除、添加玩法；Developer 才显示 Skill ID/version、Typed Config、Trigger、StatePatch Contract |
| Q116 | USER | Player 的视觉中心是视频；主沉浸形态为应用内 Theater Mode，而不是浏览器 Fullscreen | Theater Mode 隐藏 Sidebar/应用级导航并让 Player 独占主内容区；浏览器仍保持普通窗口。视频占绝对主体，推荐与自由输入固定在下方，HUD 位于视频左上角；Browser Fullscreen 仅作为二级可选功能 |
| Q117 | USER | Player 信息架构固定为 Immersion / Decision / Agency / HUD 四层 | Immersion=视频与字幕；Decision=Ready 推荐；Agency=自由输入；HUD=背包/关系/线索/愿望 |
| Q118 | USER | Jev/Top-K 推荐是视频下方的第二层快捷行动 | 只在 Decision Lead 到达且分支 Ready 后出现；未 Ready 时不显示“暂无推荐”等系统噪声；选中后其余推荐收起 |
| Q119 | USER | 自由输入是最底层、持续可用的主行动入口 | 即使有推荐也必须保留自由输入，避免产品退化成固定三选一；行动已被接受执行时可以临时锁提交但不隐藏入口 |
| Q120 | USER | 背包、关系、线索、愿望进入左上角隐藏式 HUD | 桌面 hover 可临时滑出、点击可固定；移动/触屏点击抽屉；Standard 使用定性关系表达，Developer 可见原始数值 |
| Q121 | USER | Standard Player 隐藏检查器、Branch/Provider/Schema/Pydantic 等技术错误 | 玩家只接收自然语言的可恢复反馈；Developer Inspector 保留原始错误、Trace 与结构化详情 |
| Q122 | USER | 字幕、媒体状态与失败恢复都属于播放器产品体验 | 场景标题短暂显示后淡出；对话/旁白使用安全区字幕；Generating/Loading/Failed 分离；结构化输出错误优先在服务端规范化/有限重试，再进入 FAILED_RECOVERABLE，而不是把底层验证报错吐给玩家 |

**统一产品原则（USER）：** Standard Creator 不把“机器需要的结构”交给用户手工维护；Standard Player 不把“机器正在运行的过程”暴露给玩家。结构化 Schema、JSON、ID、Provider、Trace 和精确数值仍完整存在，但属于 Developer Mode 与可审计后台。

## 03. 产品定位、边界与成功闭环

### 03.1 一句话定义

一个由 Agent Skills 驱动的有状态互动短剧平台：创作者以自然语言及多模态素材建立世界、人物与矛盾，玩家以角色身份自由行动并许愿；系统既维护事实与连续性，也动态组织冲突、信息、关系、反转和收束，把具有戏剧价值的内容制作成新视频，并允许在篇章结束后继续这个世界。

### 03.2 用户与价值

| 用户 | 要完成的任务 | 核心价值 | 关键入口 |
|---|---|---|---|
| Creator | 把想法、人物和素材做成能玩的故事 | 不必设计全部分支，不必懂生成 API | 创建故事、编辑设定、素材管理、发布试玩 |
| Player | 进入故事，做自己想到的决定 | 推荐可选但不强制；行动产生可见后果 | 建议选项、自由行动／对话、许愿、玩法面板 |
| 开发／演示者 | 观察系统为什么调用能力、实际做了什么 | 状态、工件、成本和调用可追溯 | 开发者面板、任务列表、来源标识 |

### 03.3 最小完整体验

`选择预设或创建 Scenario → 审阅世界与戏剧结构 → 配置图／声／视频参考 → 发布试玩 → 观看开场 → 推荐或自由行动 → 理解行动及欲望 → 世界后果与戏剧评估 → 快速反馈／合并／完整视频 Beat → 许愿与玩法 → Director 形成当前 Arc 结局 → 玩家选择结束或继续这个世界`。

一次关键的“真实自由行动”必须能形成计划外有效意图、合法后果、新 Story Beat 与对应视频；这项核心证明不取消。**但 Q36 覆盖“一切小动作都必须生成视频”的解释**：低价值操作可快速确认或合并，其原文、反馈和必要状态变化仍须可追踪。只有输入框、所有自由输入永远只返回文字，或把输入全部导向固定视频，都不能通过核心验收。

### 03.4 明确非目标

P0 不做多人共享世界、创作者交易市场、支付推荐系统、原生手机 App、完整时间线视频编辑器、自研视频基座、自研 Jev、为每个职业拆一个 Agent、强制所有推理全离线，也不承诺无限长故事始终无漂移。单用户／少量评委试用是建议部署目标，不是用户已经给定的并发 SLA。

平台定位不等于已经形成商业护城河；投机渲染、状态化叙事、Skills 组合是本次可展示的设计贡献，是否优于替代方案需在后续测试中证明。

### 03.5 动态戏剧结构与控制权

平台要回答的不只是“下一段能否生成”，还包括“这段为什么值得发生，如何承接之前的行动”。玩家拥有行动与策略选择权；世界规则决定可行性和代价；系统组织 NPC 回应、压力、揭示和叙事节奏；结局由真实行为与系统判断共同形成。

**戏剧性不是强制刺激。** 可以有安静、情绪沉淀、关系修复或玩家主动放弃的段落；不能为了不断提高风险而伪造背叛、抹掉成功、改写真相。完整视频 Beat 需要明确的叙事作用，而不是每个回合都必须冲突升级。

## 04. 核心用户流程

### 04.1 Creator：从想法到可玩故事

 **起点。** 用户可以从平台准备的 Scenario 开始，也可以输入一句故事想法。平台先生成可编辑草案，而不是立即为所有分支烧钱制作视频。草案涵盖世界、角色、初始状态、核心戏剧问题、相互冲突的目标、角色欲望与恐惧、秘密与真相／知情范围、压力来源、初始线索与伏笔、剧情锚点、可能结局、机制建议与素材清单。按 Q47 C，由 AI 起稿，Creator 只需用可理解的问题审阅，例如“故事最终要回答什么”“为什么不能一直拖”“哪些事实不能被反转推翻”。

 **编辑。** 用户在表单中调整角色、关系、地点、规则、视觉风格和机制，也能继续说“把她改得更谨慎，但保留温柔外表”。系统展示修改差异，只改有关字段；已经上传的素材和手工确认的规则不得被整包重写覆盖。发布前运行结构校验、资产引用检查和初始状态检查。

 **素材。** 图、声、视频都必须能上传、预览、绑定角色或场景、选择用途并被生成链路消费。声音可以绑定角色音色参考；视频可以绑定动作、镜头或风格参考；图片可以绑定角色身份、服装或场景。三者不要求用户每次全部上传，但产品必须支持分别使用与受后端限制约束的混合使用。

 **发布。** 系统生成不可变的 Scenario 发布版本和默认开场。后续编辑形成新版本；已开始的游戏绑定原版本，不能因作者改角色而让中途玩家突然换脸。用“发布并试玩”连接创作与体验，不建设大型作品发布社区。

### 04.2 Player：推荐有用，但不是边界

玩家选择故事后，看到简短设定、扮演角色、可用机制和素材／内容提示，进入开场。决策 UI 不必等当前视频完全结束才出现：当 StoryBeat 声明 `DecisionLeadWindow` 时，系统可在真正剧情分叉点之前打开互动窗口，让玩家一边观看仍然对所有候选都成立的公共片段，一边阅读选项或输入自己的行动。

系统推荐项由 Jev 排序与调度器选择后先在内部生成；**只有完整视频已生成、装配完成且版本校验有效的候选才允许出现在推荐面板中**。推荐面板发布后，点击任一系统选项都应走 Ready hit，不再为该选项临时启动生成。自由输入始终保留：系统记录原话并识别行动、对话、问题或愿望；可复用真正语义等价的缓存，但不得为了命中率把“绕到后门观察”偷换成“跟随她进入正门”。无法等价复用就接受一次真正的 cache miss，并按 Q18 C 进入主题化加载流程。

玩家提交后先得到意图回执，再按 Q36 分流：低价值小动作快速反馈，连续小动作可合并成探索／过渡，重要变化形成完整 Narrative Beat 并自动剪成可播放片段。完整 Beat 应呈现与玩家行动有关的目标、信息、关系、风险或情绪变化，不能只返回通用过场。合并不能跳过需要玩家再作决定的关键点。

### 04.3 “许愿”的产品语义

许愿是玩家表达“希望故事如何发展”的通道，例如“多一些恋爱戏”“希望她最终活下来”。它不需要跳出角色扮演主界面，也不应伪装成角色已经说出口的台词。

按 Q41，Wish 进入显式 Ledger，保留可查看、修改、撤回的产品能力。生命周期区分 `ACTIVE / DEFERRED / CONFLICTED / FULFILLED / PARTIALLY_FULFILLED / FAILED / SUPERSEDED / WITHDRAWN`；这些枚举是可版本化的实现建议。显示不剧透的反馈：“会寻找合乎当前故事的机会，但不保证实现。”不能把“被模型读到”记为“已实现”，也不引入用户没有要求的愿望币、付费许愿或次数限制。

愿望与世界硬规则冲突时不改历史。已在 Canonical Truth 确认死亡的角色不能因为愿望直接复活；若此前仅是角色／玩家误以为死亡、真实状态本来另有设定，则可用已有证据澄清。这是改变理解而不是把已确认的死亡事实改成未死亡，符合 Q37。为了不让用户的每次修改都触发重付费生成， **建议愿望默认在下一未锁定 Beat 生效** ；界面应显示生效边界。

**入口不变。** 本轮确认的是愿望的记录与合理实现机会，不是“普通节点禁止许愿”。保留既有次级入口；可在重大转折前更明显地提示一次，但提示频率与欲望副标题均为 UI 建议，不是新增硬门槛。

### 04.4 不合理行动：在故事里回应

对于“我从口袋掏出激光炮”这样的输入，系统优先保留情绪或目标，在世界内部给出失败尝试、玩笑、想象或可行替代。例如：“你摸向口袋，只有钥匙。门锁并没有松动，但旁边的消防柜也许值得看看。”不能把玩家的动作未经提示变成另一种有重大后果的行动。

 **避免新的假自由。** “圆回来”不等于每次都强迫故事回到主线。合理的新行动仍要改变计划；Story Anchors 是约束或机会，而非不可绕过的隐形轨道。安全政策、个人素材权限和实际技术错误则需要清楚说明，不能全部写成戏剧情节来掩盖。

### 04.5 等待与错误

未命中时保留最近画面或播放已准备好的主题动画，显示真实阶段：理解行动、准备镜头、排队、生成、装配、准备播放。**已显示的系统推荐选项按 I05 不应进入这一生成等待；如果它在用户点击前因 Wish、素材或状态版本变化失效，应撤回／刷新推荐集，而不是让一个已展示的“Ready 选项”暗中退化成未就绪。** 加载动画本身不再按每次请求额外调用视频模型生成，也不计入剧情缓存命中。

只展示后端确实报告的进度；无法得到百分比时使用阶段状态，不伪造“99%”。失败后保留玩家输入，显示可重试、修改输入或返回上个决策点的操作。 **不强制玩家聊天、调查或做 QTE 来等待。** 取消和重试可能仍产生已执行的供应商费用，界面不得承诺取消即退款。

### 04.6 结局、回顾与“续杯”

作者定义 Ending Families 的条件和语义方向，**Director 根据当前事实、玩家经历与叙事语义判断何时形成自然结局**。事实与结局类型必须相容，但不要求 Ending Readiness 达到某个分数，也不因到达固定轮数而结束。玩家明确不再参与核心矛盾时，可以形成忠于世界因果的退出／后果结局。

结局关闭当前 `StoryArc`，不清空世界。结束页展示本篇章回顾与“继续这个世界”入口；只有玩家主动继续，系统才建立新的戏剧问题、矛盾和压力，继承人物关系、已知事实、原有素材，以及经范围检查后仍有效的愿望和未回收线索。旧结局仍成立，不使用“刚才全是假的”强行恢复旧矛盾。

建议回顾页列出本篇章关键行动及已观看视频。单个 MP4 只能导出已经走过的线性路径，不包含仍可交互的未来分支；线性导出仍为 P1。续杯必须通过预算与资源检查，不能通过新建 Arc 自动重置总费用上限。若资源不足，保存世界并明确暂停，不用突然悲剧充当收费或技术失败提示。

### 04.7 Decision Lead Window 与互动计时语义

`DecisionLeadWindow` 是“选项出现”与“剧情真正分叉”之间的时间窗，而不是无限等待生成的慢放手段。Production／Narrative 在设计一个可提前交互的 Beat 时，应明确以下时序字段：

```yaml
next_decision:
  mode: UNTIMED | TIMED
  decision_open_at_ms: 6000
  branch_point_at_ms: 10000
  timeout_ms: null | 3000
  timeout_fallback: null | silence | qte_failure | combat_hit
  suggestion_ready_policy: ALL_READY_BEFORE_PUBLISH
```

从 `decision_open_at_ms` 到 `branch_point_at_ms` 的画面必须是 **branch-invariant footage**：无论玩家最终选哪个系统分支，这段内容都仍然成立。系统不得为了“多挤几秒生成时间”而让角色重复动作、异常减速或长期慢放；慢动作只应作为有叙事理由的镜头语言，或 `TIMED` QTE 的明确机制效果。

**UNTIMED。** 普通剧情决策默认无倒计时。玩家可以思考、输入或暂时不选；到公共片段结束仍未提交时，不自动替玩家选项，也不把沉默等同于选择。播放器可以停在中性边界画面／短循环环境镜头，等待真实输入。

**TIMED。** QTE、紧急对话或其他明确要求即时反应的事件允许倒计时。Scenario 必须在事件发布前声明 timeout fallback，且 fallback 是确定性的业务结果，例如 `dialogue → silence`、`qte → failure`、`combat → hit`；模型只能负责把结果写成剧情，不能临时改变超时判定。

**Ready Gate。** 调度器可以在后台有 `PLANNING / RENDERING / ASSEMBLING / READY` 等候选状态，但正常推荐面板只接收 `READY`。为了避免先到选项获得不公平注意，建议一个互动节点的系统推荐集原子发布：先选 K，再等 K 个候选全部 Ready；如果赶不上 Decision Lead Window，可以在发布前重新计算并下调 K，而不是一个个把未完整的选项冒出来。自由输入不受 Ready Gate 限制，因此它是开放性与真实 cache miss 的主要入口。

### 04.8 欲望回显与小动作反馈

自由输入保留原文，同时区分 `action`（做什么）、`desire`（可能想得到什么）与 `strategy`（采取什么方式）。玩家主动写出的动机优先于系统推断；未说明时允许记录未知，不能为了完整字段臆测。

按 Q34 C：高置信且低歧义时直接继续；中置信给可修改的小字回显；低置信且影响重大时，先用一个针对性问题澄清，再执行不可逆后果。Jev 的 confidence 可作为输入，但未经本项目验证不能当作准确概率。高置信也不免除对秘密揭示、角色生死等重大变化的事实检查。

“看看空抽屉”可快速反馈；多个已提交的检查动作可汇总成一个探索片段；发现决定性录音、作出公开指控或改变关键关系才需要完整 Beat。每个动作仍有记录及必要的状态后果，不能因为没生成视频就丢掉获得道具、时间消耗或 NPC 反应。

普通 `UNTIMED` 节点停留在输入框不是角色选择“等待”。只有玩家提交“等一小时”之类行动，或进入明确告知的 `TIMED` 场景，才按对应规则推进机会窗口。


### 04.9 Character Studio：从角色想法到可生产身份资产

角色创建遵循同一条可审计链：

AI 创建 / 从图片创建 / 手动创建 → GlobalCharacter Draft → 生成或上传 Candidate → 用户确认 Canonical → 可选标准多视图 → Outfit / Pose / Motion / Voice → CharacterVersion → ScenarioCharacterSnapshot → Production Reference Resolver。

AI 创建默认请求 2 张候选。选择主图后只提示是否生成标准多视图，不自动继续产生额外请求。纯文字角色可以直接保存；当故事进入需要视频生产但角色仍缺必要视觉参考时，再给出明确补资产提示。

角色 Edit 是非破坏式操作：任何换装、换背景、换姿势、换视角或自然语言编辑都会创建新 Candidate。用户可以将其批准为 Derived Asset、Outfit Reference 或新的 Canonical；旧图进入历史/归档，不被静默覆盖。

Scenario 内对角色的改动必须先让用户选作用域：仅本故事，或更新全局。仅本故事产生 Scenario Local Override；如用户认为该造型值得复用，可再显式“保存为全局角色新版本”。

角色在 Global Character Library 与 Scenario Creator 中必须使用相同的信息架构：身份、人格与动机、认知与秘密、关系、外观与造型、声音与动作、使用与版本。Global 页面编辑“这个人长期是谁”；Scenario 页面编辑“这个人在当前故事中是谁、想要什么、知道什么、与谁是什么关系、当前看起来怎样”。Scenario 层通过 Snapshot/Overlay 表达，不复制一套互不兼容的角色 Schema，也不把故事级 Desire/Fear/Secrets/Knowledge/Relationships/Visual State 静默写回全局。

角色强制必填保持克制：Global 至少名字 + 一句话角色定义；Scenario 至少明确本故事身份/作用。其余字段允许 AI 根据故事自动提出建议，用户确认、修改或留空。Standard Mode 不应以一排空白 textarea 迫使用户手工补齐内部字段。

### 04.10 AI 引导式故事深化：从“一句话”到可发布结构

Creator 的默认流程不应是“一句话生成一个待填的大表单”，而应是：

一句／多句话故事描述 → AI 形成当前理解 → 检测高影响缺失项 → 只追问必要问题 → 用户通过建议卡/自然语言确认 → 写入受验证的 Drama/Character/Mechanic 结构 → 发布前统一预览。

对已经描述清楚的内容不重复询问。若用户只写了模糊概念，AI 应优先给出 3～4 个与该故事相关的建议方案，再保留“其他／自己描述”。Standard Mode 中的戏剧结构至少以自然语言呈现为：

- 这个故事真正想问什么；
- 这个世界／事件背后的真相是什么；
- 什么会逼着故事向前走；
- 故事可能走向哪些结局；
- 有什么绝对不能发生。

Foreshadow、Timed Interaction、内部 ID、Truth Fact Key、Pressure ID 等属于高级控制，Standard 可折叠为自然语言摘要，Developer 才展示原始结构。

Overview 在生成初稿后应显示“AI 已理解什么／还需要确认几件事”，而不是立即把用户送进几十个空字段。用户完成必要确认后可以“直接试玩”或“继续精修”。

## 05. 功能需求与验收矩阵

本表采用稳定功能 ID。测试和任务分解应引用这些 ID，而不是只引用章节名。`P0-MIN` 表示保留能力但采用最小可用 UI；不得把 Q25 的完整素材链路解释为 MIN 占位。

| 功能 ID | 功能与来源 | 优先级 | 可验收行为 | 明确边界 |
|---|---|---|---|---|
| FR-001 | Scenario 预设入口；O06、Q02 | P0 | 至少一个可从入口游玩的高质量完整 Scenario | 数量先收敛，不牺牲完整闭环 |
| FR-002 | 自然语言创建；Q10、Q24、Q47 | P0 | 输入新设定产生含世界与戏剧结构的草案，可分项审阅、修改并启动 | 不能只挑模板名字，也不能要求普通 Creator 手填完整专业编剧表 |
| FR-003 | 结构化／自然语言局部编辑；Q10 | P0-MIN | 编辑角色或规则只修改对应内容，能显示差异 | 无需完整节点式剧情编辑器 |
| FR-004 | Scenario 校验、导入和版本绑定；Q15、DERIVED | P0 | 缺角色引用或规则冲突时发布失败；已有局绑定版本 | 不执行来历不明包中的任意代码 |
| FR-005 | 图片参考；Q22、Q25 | P0 | 上传、预览、绑定、出现在真实生成请求，成片可检查参考目标 | 仅存入素材库不算完成 |
| FR-006 | 声音参考；Q22、Q25 | P0 | 声音被绑定和引用，生成请求携带有效音频，输出可听取验证 | 不把配一段背景音乐冒充角色声音参考 |
| FR-007 | 视频参考；Q22、Q25 | P0 | 视频裁选／校验后用于动作、镜头或风格生成条件 | 不把视频仅作为播放器背景冒充参考输入 |
| FR-008 | 多模态混合参考；Q25、DERIVED | P0 | 至少一个图＋声＋视频混合测试有请求工件与成片 | 超出供应商上限须提示，不静默丢弃 |
| FR-009 | 推荐行动；O03、Q12、Q17、I05 | P0 | 通常目标 2–3 个；实际发布 K∈{1,2,3}，且每个已显示候选都有完整 Ready SceneArtifact | 未 Ready 候选不能作为正常选项显示；避免剧情剧透 |
| FR-010 | 自由行动／对话；Q01、Q11、Q34、Q36 | P0 | 原话与欲望理解可追踪；小动作可快速／合并反馈；至少一个计划外关键行动形成新 Beat 和新视频 | 不强行回固定分支，也不把全部自由输入降为文字以规避视频闭环 |
| FR-011 | 许愿；Q11、Q41 | P0 | Wish Ledger 记录偏好、范围、状态与被规划采用的机会；按真实事件确认达成情况 | 不直接写世界事实，不保证实现；未新增“仅重大节点可用”限制 |
| FR-012 | 世界内解释；Q09 | P0 | 不合设定的输入有沉浸式回应，并保持规则 | 安全／权限／错误信息不做欺骗式包装 |
| FR-013 | 三层世界状态＋Drama Domain；Q07、Q30、Q44 | P0 | 硬事实、事件、记忆与戏剧组织状态可区分查询；引用和冲突可定位 | 记忆与戏剧判断不能覆盖硬事实；双域不等于必须两套数据库 |
| FR-014 | 受控提交；Q13、Q44 | P0 | 世界与戏剧变化分别由确定性管理器校验；跨域相关变化一致提交，非法／过期／重复提案不生效 | 模型与 Skill 只有提案权，Drama State 不绕过既有 State Service |
| FR-015 | 四 Agent 协作；Q06 | P0 | 四种职责有独立任务与 trace，可串联产出一幕 | 不要求四个独立模型进程 |
| FR-016 | Jev 快速判断；Q16、Q21、Q30、Q34、Q45 | P0 | 原路由、候选排序、机制触发保留，增加重要性、欲望置信和相关压力源判断；高影响／不确定升级 | 不能把置信度当真相或已校准玩家行为概率，不能直接决定结局 |
| FR-017 | 双时间尺度文本滚动规划；Q19、Q32、Q35 | P0 | 高影响 Action 即时重规划；每个完整 Beat 后评估，输出 Dramatic Directive 与短期候选计划 | 小动作不必完整重规划；不为整个前瞻树生成视频 |
| FR-018 | 动态 Top-K；Q17、Q27、I05 | P0 | 正常从 1–3 中按预算／队列／评分选取；在发布前可因截止时间／预算下调 K，并追踪原因 | K 对应内部投机规模与待发布推荐集；未 Ready 不得展示，预算不足不允许超额兜底 |
| FR-019 | 分支缓存与失效；Q04、Q38、Q44、DERIVED | P0 | 命中匹配世界、剧情计划、Arc、相关 Drama、Wish、资产等版本；未选分支不成为伏笔或愿望实现 | 无关置信／排序更新不应被误当事实改变；保守失效可先实施 |
| FR-020 | 加载动画；Q18、I05 | P0 | 自由输入 miss、缓存失效或真实后端等待时显示主题化动画及真实阶段；失败保留输入 | 正常点击已显示系统推荐项不应触发现生成等待；等待期小游戏不是必做 |
| FR-021 | Story Beat → Shot Plan；Q12、Q36 | P0 | Full Beat 包含戏剧功能、预期变化与证据，再拆镜头；实际交付后记录已发生变化 | Quick／Merge 不伪装成完整新视频；镜头数是独立预算 |
| FR-022 | Prompt 优化与参数隐藏；O05、Q23 | P0 | 用户意图被编译成可执行请求，参数有来源和合法值 | 正常用户无需编辑 API JSON |
| FR-023 | 视觉／声音连续性规划；Q08、Q25 | P0 | 相同角色身份、当前服饰／持物、场景、音色参考进入下一镜头计划 | 输入约束不等于输出一定正确 |
| FR-024 | 自动装配；O08、Q23 | P0 | 至少两段生成片段能完成裁切、拼接、音轨处理并播放 | 生成台词与字幕不一致须暴露，不能假装精确 |
| FR-025 | H3 Max 云端后端；Q03、Q26 | P0 | 文本／关键帧／参考所需路径按能力矩阵调用，保存 job 与输出 | 具体账户权限和限流待实测 |
| FR-026 | Sol-H3 Spark 后端；Q03、Q26 | P0 | 真实本地任务完成；保存节点、配置、日志与输出 | 不要求本地完整局或与云端完全同速 |
| FR-027 | 按 Agent 配置模型；Q21 | P0 | State／Director 可接本地，Narrative 可接 StepFun；配置可替换 | 更换模型需复测契约和中文质量 |
| FR-028 | 至少一种 Mechanic Skill；Q05、Q24 | P0 | 完成触发→Proposal→状态→UI→后续剧情反馈 | 好感度、收集、QTE 全部齐备不是当前必做 |
| FR-029 | 动态结局与篇章；Q20、Q40、Q42、Q43 | P0 | Director 决定收束，结局引用本局事实；允许退出矛盾结局；关闭 Arc 后可主动续杯 | 不用固定轮数、Ending Readiness 门槛代替判断；旧“两类结局”演示数量仍为建议 |
| FR-030 | Skill 运行日志；Q28 | P0 | 日志来自真实执行，能点到输入／输出摘要与工件 | 不要求现场热插拔 A/B |
| FR-031 | 体验与系统指标；Q29、Q48 | P0 | 原系统与产品指标保留；真实玩家反馈是戏剧效果主要依据，区分技术正确与是否喜欢 | 不强制戏剧开关对照、盲测或 LLM Judge，不用自动分数宣称好玩 |
| FR-032 | 主题化 UI；O07、PROPOSED | P0-MIN | 一套完成度高的主题 + 可配置色彩／字体栈／背景／组件样式 | 更多主题、自然语言生成主题列 P1 |
| FR-033 | 刷新恢复与任务幂等；DERIVED | P0 | 刷新不重复扣道具或发起相同付费任务，可恢复当前局 | “可恢复”不等于无限回溯编辑历史 |
| FR-034 | 预算、权限与取消；DERIVED | P0 | 队列投递前预留预算；取消不再投递后续镜头；权限检查先于上传外部服务 | 不许无上限自动重试 |
| FR-035 | 本局线性成片导出；PROPOSED | P1 | 导出实际看过的片段与必要字幕 | 不导出未发生分支冒充经历 |
| FR-036 | 更多玩法、主题与 Scenario；PROPOSED | P1/P2 | 扩展遵循已有契约，不修改核心状态写入口 | 不挤占三类素材及核心自由行动闭环 |
| FR-037 | Decision Lead Window；I01 | P0 | 至少一个互动节点在当前视频结束前打开决策窗口，随后公共画面继续播放到真正分叉点 | 公共画面必须对所有候选成立；不得靠无限慢放掩盖等待 |
| FR-038 | Interaction Timing Mode；I02 | P0 | 每个互动节点可声明 `UNTIMED` 或 `TIMED`；普通 Narrative Decision 默认无倒计时 | 不把所有对话强制做成 QTE |
| FR-039 | Timed Interaction Timeout；I03 | P0 | 至少一个限时互动在超时后执行 Scenario 预先声明的确定性 fallback，并写入正常事件链 | timeout 结果不能由模型临场随意改判 |
| FR-040 | Session Player Preference State；I04 | P0 | 从本局真实选择累计偏好信号并作为 Jev 候选排序输入；可追溯到证据事件 | P0 不建立跨 Scenario 持久心理画像；偏好信号不是世界事实 |
| FR-041 | Ready-only Recommendation Gate；I05 | P0 | 推荐面板出现时，其所有可点击系统选项均已完成生成／装配／版本校验；点击后直接进入 Ready hit | 未完成候选只能留在内部队列；自由输入仍允许真实 miss |
| FR-042 | Typed Drama Control；Q30 | P0 | 读取有来源的 Dramatic State，规则与 Jev／LLM 评估生成可审计观察；规则不伪造剧情 | 不新增第五个常驻 Agent；示例数值阈值不是业务常数 |
| FR-043 | 柔性戏剧阶段；Q31 | P0 | 阶段可跳跃、重叠、回落，记录理由；玩家提前达成目标不被阶段顺序拦截 | 不强制固定八阶段，更不要求每局都有反转 |
| FR-044 | Action／Beat 双尺度；Q32 | P0 | 普通动作轻评估，关键动作即时评估，每个完整 Beat 后评估；重复通知不重复评估提交 | 普通机制检查不等于每次重建整个滚动计划 |
| FR-045 | 世界自主后果；Q33 | P0 | 玩家明确不行动时，已建立的 NPC 计划／窗口可推进并产生因果后果 | 不惩罚普通现实思考或生成等待；不强拉回主线 |
| FR-046 | 欲望理解与置信分流；Q34 | P0 | 区分原话、Action、Desire、Strategy；中置信可纠正、低置信高影响先澄清 | 推断可未知，用户明示优先；不每轮强制确认 |
| FR-047 | Dramatic Directive；Q35 | P0 | 输出主要戏剧功能、目标变化、硬约束、可用机会、避免事项与依据 | 不直接指定固定剧情事件，不替代 Narrative 的演绎 |
| FR-048 | 戏剧价值与响应分级；Q36 | P0 | Full Beat 有有据可查的 Progress Vector／功能；低价值行动快速确认或合并 | 不为凑指标虚增数值，不强制每动作视频化 |
| FR-049 | Truth／Twist Gate；Q37 | P0 | 反转候选引用稳定真相、已呈现线索和预期依据，并说明后续影响；不成立时延期或否决 | 不能改写已确认真相，也不将推测当作玩家真实信念 |
| FR-050 | Foreshadow Ledger；Q38 | P0 | 作者／新生伏笔注册，铺设、加强、回收、放弃有引用和可见性记录 | 只在计划或未选视频出现不算正式铺设 |
| FR-051 | Pressure Sources；Q39 | P0 | 压力有定义、触发依据、世界状态引用及机会窗口；展示能追到已有因果 | 不由 Director 为“刺激”直接改计时或加灾难 |
| FR-052 | Director 结局判断；**Q40 B** | P0 | 记录是否收束、当前 Arc、依据与结局方向；可以参考事实摘要但无强制 readiness／轮数阈值 | 技术预算不足是暂停／资源提示，不是假结局 |
| FR-053 | Wish Ledger 与实现机会；Q41 | P0 | 愿望被规范化、记录范围和状态，以实际后果支持达成／部分达成／失败 | 不能自动成为必须兑现的剧情债务 |
| FR-054 | Consequence Ending；Q42 | P0 | 玩家主动退出核心矛盾可进入真实后果结局，允许未解秘密和短篇章 | 不以追杀、强制偶遇等手段把玩家拉回原线 |
| FR-055 | Arc Closure + New Arc；Q43 | P0 | 主动续杯创建新 Arc，继承合法事实、关系与相关未结项，建立新戏剧问题 | 不覆盖旧结局，不默认复活／重置角色，不自动续费 |
| FR-056 | Drama Proposal／Commit；Q44 | P0 | Drama State Manager 检查版本、来源、引用与权限；关联世界变化一致提交；投机分支隔离 | 不要求单独服务；不允许模型直接写库 |
| FR-057 | Jev／LLM 戏剧分工；Q45 | P0 | Jev 闭集判断与不确定升级；LLM 解释上下文；高影响反转等经语义评审 | 不能仅凭高置信度绕过真相或授权校验 |
| FR-058 | 戏剧债务与机会仲裁；Q46 | P0 | 硬约束优先，记录真实待处理事项，再按场景机会选择本幕重点；可正当地延期／放弃 | 无依据的“必须高潮”不是义务；不把 Wish 自动变保证 |
| FR-059 | 戏剧结构 AI 起草与审阅；Q47 | P0-MIN | 自动起草问题、矛盾、真相、角色欲望、压力、伏笔和结局方向；可局部审阅 | 与现有 Creator Flow 合并，不增庞大专家编辑器 |
| FR-060 | 真实玩家体验评价；**Q48 A** | P0 | 记录真实游玩样本、玩家喜欢／不喜欢及具体片段、问题和改进判断 | 不预填满意结论，不要求盲测或自动戏剧总分 |
| FR-061 | 本地 Director Backbone；Q49、Q50 | P0 | DGX Spark 上真实启动 `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`，Director 调用有 trace、模型版本与结构化产物 | 不以远端 NIM 冒充本地；中文规划质量需单独实测 |
| FR-062 | 固定模型职责路由；Q51、Q54 | P0 | Narrative 请求走 Step 3.7 Flash；Scenario Authoring 走 Step 5 Preview；Production 默认走本地 Lightning + `h3-production` | 不自动按高潮把 Narrative 切 Step 5；Production 不由 Narrative 越权替代 |
| FR-063 | State Manager + semantic fallback；Q52 | P0 | CRUD／版本／事务由确定性 State Manager 完成；只有复杂语义解析才调用 Lightning／受控模型 | LLM 不能直接提交 Canonical State |
| FR-064 | 双 Runtime Profile；Q53、Q68 | P0 | 能完成 `AGENT_LOCAL_PROFILE ↔ VIDEO_LOCAL_PROFILE` 的 drain、持久化、卸载、启动、health check 与 route switch | 不承诺 Lightning 与 Sol-H3 同驻；切换耗时真实记录 |
| FR-065 | 双 Pipeline 与 Branch Contract；Q55 | P0 | Ready 推荐与自由输入走不同入口但产出同一 Branch 对象；Ready 点击不重复创建同一剧情／视频 | Branch 必须绑定输入快照、状态版本、媒体和提案 |
| FR-066 | Jev First Pass 保留原文；Q56 | P0 | Director 同时收到 `raw_player_input` 与 Jev observation／confidence，可接受或修正 | Jev 摘要不能覆盖玩家原话或成为事实 |
| FR-067 | Director 分层工作上下文；Q57 | P0 | 每轮只装载 Scenario Core、相关状态切片、Drama、Arc Summary、最近事件、检索历史与当前输入；全量日志不默认塞 Prompt | 检索／摘要不能替代 Canonical Event Log |
| FR-068 | Narrative ScenePacket；Q58 | P0 | Narrative 只获得本幕 Beat、角色可知信息、允许／禁止揭示、关系、风格与必要真相 | 不向 Narrative 暴露无关秘密，不允许它重写 Director 计划 |
| FR-069 | Top-K 全并行；Q59 | P0 | K 锁定后 K 条分支并行进入 Narrative／Production／视频；每条均可独立 trace | 供应商并发不足时在锁 K 前降 K；分支内部镜头依赖可串行 |
| FR-070 | DAG 内部并行；Q60 | P0 | Director Branch Skeleton 冻结后，Narrative、素材检索、连续性／预校验等按依赖并行；下游只消费已冻结边界 | 不做 token 级无约束级联导致上游改稿污染下游 |
| FR-071 | Two-Phase Canonicalization；Q61 | P0 | 玩家点击后 Branch 标为 `SELECTED` 并建立 provisional view；视频确认可播放后才 `CANONICAL`，失败可回滚 | provisional 可用于 N+2 规划，但不得提前写正式历史／伏笔／Wish 达成 |
| FR-072 | 性能仅测量、不先写 SLA；Q62 | P0 | 所有关键节点记录真实起止、TTFT／输出／媒体等待；报告分布与环境 | v0.5 不设固定 P95 门槛，不把厂商 benchmark 当项目 SLA |
| FR-073 | Top-K 失败降级；Q63 | P0 | 单分支失败立即快速重试一次；仍失败则从发布集合移除并以 K-1 原子发布其余 Ready 分支 | 不因单分支无限重试阻塞全部推荐；effective_k 必须记录 |
| FR-074 | Narrative Provider fallback；Q64 | P0 | Step 3.7 Flash 暂时错误／schema 连续失败时 Router 可回退本地 Lightning，并记录 provider change | VIDEO_LOCAL_PROFILE 下 Lightning 不可用时不得伪称已 fallback；此边角另列 OPEN |
| FR-075 | Director Provider fallback；Q65 B | P0 | 本地 Lightning OOM／不健康／被 Profile 卸载时回退 Step 5 Preview API，保留同一输出契约 | 不自动改用 Step 3.7 作为第一 fallback；fallback 结果需标来源 |
| FR-076 | 短生命周期 Branch Cache；Q66 | P0 | 未选 Branch／媒体进入有 TTL 与 Arc／Session 边界的缓存，可被兼容未来请求复用 | 缓存内容不构成发生事实；过期／不兼容自动失效 |
| FR-077 | Dependency Fingerprint；Q67 | P0 | Branch 记录相关 World／Character／Location／Asset／Drama／Wish／Arc 依赖并生成可校验 fingerprint | 不让 LLM 仅凭相似度决定复用；依赖不全时保守 miss |
| FR-078 | Runtime Profile 切换协议；Q68 | P0 | 切换时停止新本地任务、drain、保存状态、关闭服务、清理、启动目标服务、health check、Router 原子切换 | 失败保持可恢复旧 Profile／明确不可用状态，不静默半切换 |
| FR-079 | Production Provider fallback；Q69 | P0 | Lightning 不可用时 Step 3.7 Flash 仍按相同 `h3-production` Skill／Schema 生成 Production 计划 | Narrative 不因共用 Step 3.7 而获得 Production 状态写权限 |
| FR-080 | 统一 Provider Router；Q70 | P0 | Router 集中执行 health、timeout、retry、circuit breaker、fallback、model route、trace 与成本标签 | Agent 业务代码不散落供应商 if/else；视频／文本路由类型仍分开 |
| FR-081 | Provider／Profile 可用性约束；Q64、Q68、DERIVED | P0 | Router 根据当前 Profile 计算真实可用 fallback 集；不可用 fallback 在调用前即被剔除并产生可解释诊断 | 不把 `VIDEO_LOCAL_PROFILE` 中已卸载的 Lightning 当可用 Narrative fallback |
| FR-082 | 模型与路由版本锁定；DERIVED | P0 | Session／Branch／trace 记录 Director、Narrative、Authoring、Production、Jev、Video 的具体模型／adapter／profile 版本 | “provider 名称相同”不等于模型版本相同；升级后须复测关键契约 |


| FR-083 | 全局角色库；O12、Q71、Q92 | P0 | 可跨 Scenario 搜索、创建、查看、版本化和复用角色；搜索至少覆盖 name、bio、tags、personality | 不是仅当前项目角色列表；不得用 UI placeholder 声称搜索后端未支持字段 |
| FR-084 | 角色三种创建入口；Q71、Q94 | P0 | AI 创建、从图片创建、手动创建都能形成 GlobalCharacter；无图角色可合法保存 | 不强制创建即调用付费生图 |
| FR-085 | 角色 AI 生图；Q73～075、IMAGE-01 | P0 | fal-ai/nano-banana-2 真实调用产生默认 2 张 Candidate；用户可选 Canonical，并可二次确认生成标准多视图 | 只有假按钮、Mock URL 或上传占位不算完成 |
| FR-086 | 角色图片编辑；Q78～081、IMAGE-01 | P0 | fal-ai/nano-banana-2/edit 支持参考图 + 编辑指令，默认保护身份属性，结果新建 Candidate | 不覆盖原图；首版不要求复杂 Mask 编辑器 |
| FR-087 | Canonical Reference Pack；Q72、Q75 | P0 | 主图及正面头像/3⁄4/侧面/全身正面/全身侧面有独立 role、版本与 provenance | 多视图未确认前不得自动批量生成 |
| FR-088 | Outfit 与身份保护；Q76～078 | P0 | Outfit 属于同一角色，可挂多视图；Edit 默认锁脸/年龄/发型/基本体型 | Outfit 不是复制新角色；模型实际一致性需样本验证 |
| FR-089 | Pose / Motion 资产；Q82～083 | P0-MIN | 不建固定表情库；支持静态 Pose 与动作视频 Reference 上传/生成后绑定角色 | 表情由镜头级 Production 控制 |
| FR-090 | Character Version 与 Change Type；Q84～085 | P0 | 重要身份/声音/标准造型/核心描述变化产生新版本，并记录 change_type 与 before/after | 版本不能只改字符串而不冻结资产引用 |
| FR-091 | Scenario Snapshot / Local Override；Q86、Q103～104 | P0 | Scenario 固定 CharacterVersion Snapshot；可查看新版差异、选择升级；本地 override 可人工升为全局新版本 | Global 更新不得静默改变已有 Scenario |
| FR-092 | 角色声音资产；Q87～088 | P0 | 一个 Canonical Voice + 多备用 Voice，可试听、替换、版本追踪，Canonical Voice 进入 Snapshot | 不把任意音频文件自动视为角色声音 |
| FR-093 | Production Reference Resolver；Q89～091 | P0 | 根据 Scene 自动从 Snapshot 选择最相关 2–4 张角色图及必要 Voice/Motion；Developer 可覆盖并保留实际发送清单 | 不全量塞素材；选择结果不得只存在 Prompt 文本里 |
| FR-094 | Character Studio UI；Q92～093 | P0 | 概览/身份/造型/姿势动作/声音/使用记录/版本均可操作；Character Studio 与 Assets 都可发起图像生成 | 资产 ID 只读展示不算角色工作台 |
| FR-095 | 非破坏资产生命周期；Q80、Q101～102 | P0 | GENERATED→CANDIDATE→APPROVED→CANONICAL→ARCHIVED 可追踪；替换 Canonical 前验证引用 | 禁止直接删除仍被 Snapshot/Production 使用的 Canonical |
| FR-096 | AI 描述辅助与 Prompt 可见性；Q98～100 | P0-MIN | AI 补全描述先预览确认；标准模式隐藏底层 Prompt，Developer 可查；描述变化不自动重生图 | 模型补全不自动写角色事实，不静默产生 API 成本 |
| FR-097 | Image Router；IMAGE-01 | P0 | 产品只调用 IMAGE_GENERATION / IMAGE_EDIT；Adapter 当前路由到 fal.ai Nano Banana 2，并记录 model/request/artifact/latency/error | 业务层不得散落具体 fal endpoint；FAL_KEY 不进前端 |
| FR-098 | 标准/开发者模式；USER | P0 | 标准模式隐藏 Developer 导航与底层 Prompt/Provider；开发者模式可查看真实技术工件 | 左下角只显示当前模式，不显示“在线 API/离线原型”等伪技术状态 |
| FR-099 | 全局显示设置；USER | P0 | 跟随系统/浅色/深色，UI Size 标准/大/特大，字幕字号与画内/画外位置有实时预览 | 与 Scenario Theme 分离；故事不能强制降低可读性 |
| FR-100 | 桌面响应式基线；USER | P0 | 1366×768、1440×900、1080p、2K、4K 在浏览器 100% Zoom 下可读可操作；Player 视频区、Creator 表单、Developer 表格合理扩展 | 不用大量 11–12px 核心文字，不靠 transform/zoom 整页放大 |
| FR-101 | 真实模型部署核查；USER、DERIVED | P0 | Lightning、Step 3.7、Step 5、Jev、H3 Max、Sol-H3 均有实际 health/request/model/output 证据，路由与 Profile 切换可审计 | .env 写了模型名、Mock PASS 或枚举切换均不能替代真实部署证据 |
| FR-102 | 角色生成成本语义；Q95～097 | P0 | 普通用户不看单次价格和预算档位；多视图批量生成前明确二次确认；后台 Usage Ledger 记录真实消耗 | “不显示费用”不等于不计费、不限额或无预算保护 |
| FR-103 | AI 引导式 Creator；Q105～108 | P0 | 一句话/多句话输入后先生成“当前理解 + 待确认项”；只有缺失/低置信且高影响内容进入追问，追问有上下文相关建议和自由输入 | Standard 不以空白 DramaSpec 表单作为默认创作起点 |
| FR-104 | 戏剧结构自然语言投影；Q106～108 | P0 | Standard 把 DramaSpec 投影为核心问题/真相/压力/结局/限制等可读模块；高级字段可折叠，Developer 可见完整结构 | 不删除底层 DramaSpec，也不因隐藏字段跳过 Publish 校验 |
| FR-105 | 统一角色管理颗粒度；Q109～111 | P0 | Character Library 与 Creator 使用同一信息架构；Global Core 与 Scenario Overlay 的作用域清晰可见 | 同一角色不得在两个入口出现互不兼容的字段模型 |
| FR-106 | 角色最小必填与 AI 补全；Q110～112 | P0 | 名字+一句话定义即可形成 Global Draft；Scenario 角色至少有本故事身份/作用；AI 可建议动机、恐惧、秘密、认知、关系与 Visual State，用户确认后写入 | 不强制人工填写所有内部角色字段 |
| FR-107 | Scenario Character Overlay；Q111 | P0 | Desire/Fear/Secrets/Knowledge/Relationships/Visual State 默认写入 Scenario Snapshot/Override，可查看继承/覆盖来源 | 不静默污染 Global Character；提升全局必须显式操作 |
| FR-108 | 自然语言玩法作者界面；Q113～114 | P0 | 用户用自然语言描述“怎么玩”，Authoring AI 生成 MechanicSpec Proposal，经 Schema/权限校验后保存 Typed Config | 自然语言不直接在 Runtime 中作为任意代码/JSON 执行 |
| FR-109 | 玩法教程卡；Q113～115 | P0 | Standard 以“调查与线索/人物关系/道具/紧张时刻”等自然语言规则卡显示，可调整/移除/添加；Developer 显示 Skill/Version/Trigger/Config | Standard 不暴露空 JSON textarea |
| FR-110 | Player Theater Mode；Q116～117 | P0 | Standard Player 可进入/退出应用内 Theater Mode：隐藏 Sidebar/应用级 Header/Creator 导航，Player 占满应用可用视口；Stage 使用剩余最大空间，Decision Layer 固定在 Stage 下方，Agency Layer 固定为最底层，HUD 覆盖左上；Browser Fullscreen 作为“更多”中的可选二级功能 | 不得把 `requestFullscreen()` 本身当作 Theater Mode 完成；不得因 Runtime 状态改变把 Decision/Agency Dock 挤离固定层级 |
| FR-111 | Decision / Agency Interaction Dock；Q117～119 | P0 | Ready 推荐位于自由输入上方，仅在 Decision Lead 后出现；自由输入始终存在；选中推荐后其余卡片收起并显示正在继续故事 | 未 Ready 不展示；不能用推荐取代自由行动 |
| FR-112 | Player HUD 抽屉；Q120 | P0 | 左上角 HUD 汇总背包/关系/线索/Wish；桌面 hover 临时展开、点击固定，触屏点击展开；Standard 关系默认定性表达 | 精确数值和 State ID 进入 Developer |
| FR-113 | Standard 错误隔离与 Developer Inspector；Q121 | P0 | Standard 把模型/Schema/Provider 异常转成可恢复的人话与操作；Developer Inspector 保留原始 Trace、错误、Branch/Provider 信息 | Pydantic URL、Python exception、原始 validation dump 不得直出玩家界面 |
| FR-114 | 字幕、媒体状态与输出修复；Q122 | P0 | Scene Title 短暂淡入淡出；字幕按对话/旁白显示；Generating/Loading/Failed 三态明确；可安全规范化的结构化模型输出先做 deterministic repair 或一次 schema retry | 不把黑屏作为通用加载态；修复不得绕过业务校验或偷偷改世界事实 |

### 05.1 P0 的交付策略

用户已选择较宽的媒体输入范围，因此应以“ **功能真通，界面精简** ”控制范围：素材支持图／声／视频的最小合法上传、预览、用途绑定和生成；编辑器先用表单；只做一个精致故事和一种能闭环的玩法；不建素材市场和大型创作社区。

FR-042–060 是动态戏剧控制的最小可用实现；FR-061–082 是 v0.5 模型／运行时增量；FR-083–102 是 v0.6 Character Studio、显示与真实部署验收增量；FR-103–114 是 2026-09-24 冻结的 AI-native Creator / Character / Mechanics / Player UX 增量，不要求为每项建一个服务或 Skill。Director 持有一个戏剧评估工作流、同库增加结构化记录、在现有 UI 中增加回显与续杯即可起步。具体字段、测试数量和技术实现仍区分 DERIVED／PROPOSED；例如 FR-029 的“两类结局”演示数量依然只是建议。

## 06. 界面与交互规格

### 06.1 页面结构

| 页面 | 主要区域 | 用户可见信息 | 不应出现的信息 |
|---|---|---|---|
| 故事入口 | 预设卡片、创建按钮、继续游玩 | 类型、简介、扮演角色、机制标签 | 所有隐藏结局条件与未揭露秘密 |
| 创作工作台 | AI 当前理解、待确认问题、建议卡、自然语言编辑、素材面板、预览 | 草案状态、缺失内容、用户确认、变更、发布校验 | Standard 默认空白内部 Schema、原始 JSON、无意义的全部推理参数 |
| 素材面板 | 图／声／视频预览、角色绑定、用途选择 | 文件规格、授权来源、引用编号 | 供应商密钥或永久公开的私密链接 |
| 游玩页 | 沉浸视频舞台、字幕、Decision Layer、Agency Layer、左上 HUD | Ready 推荐、自由行动、自然语言已知状态、可恢复反馈 | Standard 中的 Inspector、Pydantic/Provider/Branch 错误、未发生投机剧情与秘密 |
| 许愿抽屉 | 输入、当前愿望、撤回／修改 | 下一幕／后续生效提示，不剧透的反馈 | 把愿望当作保证达成的承诺 |
| 开发者面板 | Agent／Skill trace、World／Drama 版本、Arc、队列 | Directive、提案、证据引用、工件来源、失败与成本 | 默认暴露私人素材、隐藏推理或向玩家泄露秘密 |
| 篇章结束页 | 回顾、结局、继续这个世界 | 当前 Arc 已关闭、续杯预览与资源限制 | 旧结局被悄悄撤销或新篇章费用被隐藏 |

### 06.2 主题定制的责任边界

原始构想中的“自定义使用界面风格”不能遗漏。建议将主题定义为受控 `theme.json` 与静态资产，包含背景、色板、字体栈、布局密度、字幕样式、按钮和机制组件皮肤。美术负责视觉质量，Runtime 负责安全组件，Skill 可在后续把自然语言偏好转换成主题配置。

P0 用一套完成度高的主题证明接口，允许 Creator 调整少量 token；任意布局生成、自由 CSS／脚本执行和全主题市场留到后续。 **这是本次建议的范围安排，原用户并未选择砍掉界面定制。**

### 06.3 输入与播放时序

回合边界区分 `ActionTurn` 与 `StoryBeat`：多个小动作可只有轻反馈并在适当时合成一幕，一个重要动作也可形成一个完整 Beat。主要剧情分叉仍对应一次明确决定，但 **互动窗口不必等当前 Beat 完全播完才打开**。当存在 `DecisionLeadWindow` 时，播放器继续播放公共、分支无关的尾段，同时前端允许玩家阅读系统建议或开始自由输入；真正的分支媒体在 `branch_point` 之后接管。这样把观看、思考和预生成重叠起来，而不是靠把当前视频任意拉长来掩盖延迟。

系统建议遵循 `ALL_READY_BEFORE_PUBLISH`：调度器先在后台生成候选，推荐面板只发布已经完整 Ready 的集合。普通剧情决策默认 `UNTIMED`，视频公共尾段结束后玩家仍可继续思考，不自动选；QTE／紧急对话等 `TIMED` 互动才显示倒计时，并在超时后执行 Scenario 已声明的 fallback。前端输入可以草拟，但一次会话同时只有一个已接受的行动处于执行中；双击提交由幂等键去重。

角色扮演主视角是身份与决策权限的概念，不等于每个镜头必须是第一人称摄影。镜头可以切特写或第三人称，但不能无意替玩家决定下一次重大行动。

### 06.4 开发视图不替代玩家体验

默认隐藏模型概率、GPU 队列和完整 Trace，把它们放在演示／调试面板中。推荐选项不默认展示未经校准的“你有 82% 概率选择它”。玩家只需要知道能做什么，以及自己的选择是否被接受。


### 06.5 Global Character Library 与 Character Studio

Global Character Library 是跨 Scenario 的一级导航，不属于单一 Creator 项目。列表支持搜索 name、bio、tags、personality，并展示角色主图、当前版本与使用范围。点击角色进入 Character Studio。

Character Studio 至少提供：概览、身份、造型、姿势/动作、声音、使用记录、版本。身份页管理 Canonical 主图与标准多视图；造型页管理默认造型和 Outfit；姿势/动作页管理静态 Pose 与动作视频；声音页管理 Canonical Voice 与备用 Voice；版本页显示 change_type、before/after、由哪些 Scenario Snapshot 使用。

生成/编辑操作以用户意图为主：普通模式显示“生成角色图片”“编辑形象”“生成参考图”“新建造型”等产品动作，不展示 fal endpoint、temperature 或原始请求 JSON。Developer 模式才显示 Prompt、Provider、模型、request_id、输入引用、输出资产与错误。

角色库与 Creator 的角色页使用同一层级：身份、人格与动机、认知与秘密、关系、外观与造型、声音与动作、使用与版本。角色库呈现 Global Core；Creator 呈现 Scenario Snapshot/Overlay，并在每个可覆盖部分明确“继承全局 / 仅本故事 / 保存为全局新版本”。Standard Mode 以自然语言展示 AI 当前理解，不让用户手工维护版本 ID、Snapshot JSON 或 Resolver 原始输出。

### 06.6 全局显示设置与响应式桌面基线

全局 Settings 提供 Appearance：跟随系统 / 浅色 / 深色；UI Size：标准 / 大 / 特大；字幕字号：标准 / 大 / 特大 / 自动适应屏幕；字幕位置：画面底部·内 / 画面底部·外，并有即时预览。它们作用于整个产品 Shell，与 Scenario Theme 分离。

桌面设计以浏览器 100% Zoom 为基准。必须真实测试 1366×768、1440×900、1920×1080、2560×1440、3840×2160；1080p 不应需要 150% Zoom 才舒适阅读。核心正文、Sidebar、按钮、表单、Developer 表格不得长期依赖 11–12px 字号。布局应使用合理 rem/clamp/grid/container/media query；禁止用整页 transform:scale 或 CSS zoom 模拟响应式。

Player 的视频区域是视觉中心并随屏幕扩展；Creator 在 2K/4K 不应仍被锁死在狭窄单列；Developer 表格可横向滚动并保持可读列宽；Sidebar 在小桌面不挤压主操作，在 4K 也不能形成过度空白。

### 06.7 Standard Creator：AI 当前理解、追问与自然语言玩法

Standard Creator 的第一屏是“AI 当前理解”，而不是内部字段列表。每个模块允许三类动作：接受当前理解、从建议中选择、自由修改。只有真正影响故事逻辑且 AI 无法稳定确定的内容才进入待确认队列；用户原始描述越完整，系统询问越少。

戏剧结构使用面向创作者的语言；Developer 才展示 Core Question、Truth Model、Pressure ID、Ending Family ID、Foreshadow ID 等内部结构。角色编辑同样先展示“这个角色在当前故事中是谁／想要什么／知道什么”，并标记哪些来自 Global、哪些属于当前 Scenario。

玩法机制顶部提供“你希望这个故事怎么玩？”自然语言入口。AI 编译后，以类似游戏教程的卡片呈现，例如“调查环境可以发现线索”“人物会记住你如何对待他们”“重要物品可以保存并再次使用”“紧张场景可能需要快速决定”。Standard 可调整、移除、新增规则；不得直接暴露 {} JSON 参数框。Developer 才允许检查对应 Mechanic Skill、版本、Typed Config、Trigger 与 StatePatch Contract。

### 06.8 Player：Theater Mode、Interaction Dock 与 HUD

Player 采用四层信息架构：

1. Immersion Layer：视频、场景标题、字幕。视频是页面绝对视觉中心；场景标题在新场景开始时短暂显示后淡出，对话与旁白使用视频安全区字幕。
2. Decision Layer：Jev/Top-K 已 Ready 推荐。它位于视频下方、自由输入上方，在 Decision Lead 到达后轻量出现；未 Ready 时不显示“暂无推荐”占位。用户选中后其余卡收起，保留“已选择／正在继续故事”的轻反馈。
3. Agency Layer：自由输入位于最底层，是持续存在的主行动入口。有无推荐都可输入，不把体验退化成固定三选一。
4. HUD Layer：背包、关系、线索、Wish 收入视频左上角隐藏式抽屉。桌面 hover 临时展开、点击固定；移动端点击展开。Standard 默认用“信任／戒备／关系改善”等叙事性描述，不要求显示 0–100 数值。

**Theater Mode 是 Standard Player 的主沉浸模式。** 进入 Theater Mode 后，应用级 Sidebar、Creator/Library 导航与普通页面 Header 隐藏，Player 自身占满应用可用视口（建议以 100dvh/可用容器高度布局），但浏览器保持普通窗口状态，不要求触发 Fullscreen API，也不出现必须按 Esc 才能退出的浏览器全屏提示。视频 Stage 使用除交互区之外的最大剩余空间；Decision Layer 固定在 Stage 下方；Agency Layer 固定在最底层，因此无论视频播放、生成、失败或 Intent 状态如何，玩家都能形成稳定的“视频 → 推荐 → 自由输入”空间认知。

Browser Fullscreen 仍可保留为播放器“更多”菜单中的二级可选功能；它可以让整个 PlayerShell 请求 fullscreen，但不得成为 Theater Mode 的前置条件，也不得作为 FR-110 / AT-84 的通过依据。

播放控制应覆盖在视频下缘并在鼠标/触摸唤起时显示，闲置时淡出；低频“跳过当前场景／浏览器全屏／字幕设置／退出故事”等动作进入次级菜单。普通模式下不应在视频与 Decision Layer 之间长期占据一整行网页式工具栏。

Generating、Loading、Failed、Intent Echo/Clarification 与可恢复错误不得把 Interaction Dock 推离固定层级。优先把媒体状态和恢复动作显示为 Stage 内 Overlay／轻量浮层；用户选择“修改行动”时再把焦点交给 Agency Layer。Standard Mode 不出现 Inspector 按钮、Branch Status、Provider、request ID、Python/Pydantic validation 详情；完整技术错误只进入 Developer Inspector。

播放器必须区分 Generating（尚在生成媒体）、Loading（已有媒体但浏览器正在载入）、Failed（加载或生成失败）。不可把三者统一显示为无解释的黑屏。字幕编码、场景名、人物名必须使用完整 Unicode 路径验证，不接受 tofu 方块或乱码作为已知可忽略问题。

## 07. 叙事引擎与状态正确性

### 07.1 规划、事实、媒体三者分离

系统必须区分三个对象： **可能发生的计划、已经确认的世界事实、用于呈现事实的媒体文件** 。写出一个候选不等于事情发生；生成了一个视频也不等于玩家已经选了它；视频里意外出现一个新道具，更不意味着数据库应该自动增加该道具。

建议采用以下权威链：`World Rules + Canonical State → 合法意图与后果提案 → Story Beat → Shot Plan → Media Artifact`。生成模型处于呈现层，不是世界真相的最终裁判。

### 07.2 三层状态及访问控制

| 层级 | 内容 | 写入方式 | 读取范围 |
|---|---|---|---|
| Hard State | 角色位置、物品归属、任务、已知事实、机制数值、视觉临时状态 | State Service 校验 Proposal 后事务提交 | 按 Agent、玩家和角色权限裁剪 |
| Event Log | 已确认行动、结果、状态差异、触发机制、版本和来源 | 随状态事务写入，追加而不覆盖 | 用于恢复、回顾、审计与记忆生成 |
| Narrative Memory | 关系印象、气氛、叙事摘要及伏笔索引 | 根据已提交事件生成，保留 event／ledger 引用 | 按观众／角色知识范围读取；正式伏笔生命周期以 Drama Ledger 为准 |

 **知识范围是必要约束。** “作者知道凶手是谁”“Alice 知道凶手是谁”“玩家已经知道凶手是谁”必须分开。建议候选行动只使用玩家可知信息；否则预生成选项本身就可能泄露真相。情绪与关系摘要不能凭空变成已发生的事件。

### 07.3 State Agent 与 State Service

State Agent 负责解释后果、提出冲突解决与叙事记忆建议；State Service 是其唯一可信写入接口，负责类型、范围、权限、前置条件、版本、幂等和事务。数据库账号不给 Narrative、Production 或普通 Skills。

每次提交至少验证：目标字段在允许路径内，来源 Skill 有提案权限，引用角色／物品存在，数值满足机制规则，`base_state_version` 未过期，事件未重复执行。关系值增减并非每次都需要调用 LLM；明确规则可由脚本计算，但仍形成带来源的 Proposal。

### 07.4 世界／戏剧事务与呈现边界（派生建议）

完整视频路径采用 `prepare → render → validate → commit → present`：接受行动后创建合法后果与戏剧提案，生成媒体并检查，通过确定性服务原子提交世界补丁、相关戏剧记录、事件与媒体引用，再可靠通知播放器。Q44 不要求另一套数据库；建议在同一个事务内协调两个状态域。

Q36 的快速反馈路径采用 `prepare → validate → commit → acknowledge`，没有视频任务就不等待不存在的媒体。合并路径逐个记录已接受动作及真实后果，随后把未呈现的小动作汇总为一个片段；不能在合并成片时再次执行道具消耗或时间变化。发现需要玩家新选择的关键后果必须立即暂停合并。

**提交与玩家看见是不同事件。** Canonical 事件可先与媒体引用一起提交；但 `PresentationReceipt`／玩家已知信息应在相应片段或文本真正呈现后更新。仅生成一个视频、甚至提交待播场景，都不足以证明玩家已看见其中线索。跳过片段的已知范围需由摘要呈现或明确回执建立。

失败与恢复必须满足：未提交动作失败不产生幽灵事件；已提交小动作不会因后续蒙太奇失败而重复执行或无故消失；重复回调不重复扣数值；断线后能区分“已发生未呈现”与“尚未执行”。真实资源不足显示暂停，不由 Narrative 编造剧情解释技术故障。

### 07.5 投机分支必须隔离

每个投机分支绑定不可变的世界／Drama／Arc 输入快照，只持有候选 Beat、WorldPatch／DramaPatch、镜头任务和媒体工件。其推演结果存入 `SpeculativeBranch`，不得进入正式 Event Log、玩家记忆、角色知情、Foreshadow／Wish Ledger 或 Drama Debt。生成了未选中的“伏笔回收镜头”不等于伏笔已回收。

选择命中后仍需检查前提与版本，再把该分支转为当前已选择回合。未选中的分支到期或失效即释放预算占用和临时引用；已经产生的供应商费用仍计入浪费。

### 07.6 变更、取消和重试

| 事件 | 世界状态处理 | 媒体／缓存处理 |
|---|---|---|
| 玩家在决策前修改 Wish | 增加 wish version，不改既有事实 | 重新评估受影响缓存；不再提交已过时投机任务 |
| 已选回合生成中再许愿 | 保存待生效偏好 | 默认下一未锁定 Beat 生效；不无条件撤销付费任务 |
| 作者修改角色或素材 | 新建 Scenario／Asset 版本 | 已有局保持旧版本；显式迁移才改变引用 |
| 视频生成失败 | 尚未提交的世界补丁保持未生效 | 有限重试；失败保留输入与错误原因 |
| 同一回合重复回调 | 幂等提交，只产生一个正式事件 | 复用已有结果，记录重复通知 |
| 用户取消 | 取消未提交计划，不虚构已发生事件 | 停止后续投递；后端无法中止时丢弃迟到结果并记账 |
| 缓存命中但版本过期 | 不提交旧补丁 | 视为失效未命中，不为追求命中率强行复用 |

### 07.7 长程剧情、篇章与结局判断

Story Spine 保存核心问题、冲突、人物动机、真相、锚点与结局方向；Director 继续使用 Q19 的 Rolling Horizon，通常只执行最近一步。未来 2–4 个候选 Beat 只是原讨论中的可调规划跨度，不是故事总长度或媒体预生成深度。

Q32 将重规划触发精确化为“关键 Action 即时 + 每个完整 Beat 后评估”。锚点可作为机会或必要主题，不能覆盖玩家已经改变的事实；合法的提前破局应被承认，不强迫再走探索阶段。

**Q40 B 覆盖旧版“不能只由 Director 判断何时结束”的限制。** 结局时机属于 Director 的叙事判断；它仍必须读取事实、未结关系和玩家意愿，而不能越权修改结局内容所依赖的真相。可提供 Ending Context 摘要，但不建立 Ending Readiness 硬门控、自动分数阈值、固定轮数或强制软上限。Arc 的具体结局方向继续使用 Q20 的 Ending Families，是否续杯由玩家决定。

### 07.8 Drama Control 的实现边界

**USER：** Q30、Q35、Q44、Q45 确定这是一套“显式戏剧状态 + 规则 + 快慢评估 + Directive”，不是另一个全能编剧 Agent。

| 模块／职责 | 回答的问题 | 不负责什么 |
|---|---|---|
| World State／State Service | 事实是什么、什么变化合法且已经发生 | 不因为叙事需要而改写真相 |
| Dramatic State／Drama State Manager | 戏剧组织记录是什么，哪些观察与待处理事项可信 | 不自己开放式编剧，不让模型直接写库 |
| Jev 快评 | 当前输入属于什么、影响多大、哪种已知机会相关、是否不确定 | 不生成开放剧情、不保证读懂玩家心理 |
| LLM／Director 语义评估 | 为什么此行动重要、当前缺什么、哪些证据支持判断 | 不用解释性文本豁免硬约束 |
| Dramatic Directive | 下一步优先完成什么戏剧功能，受什么约束 | 不强制 Alice 必须被绑架等固定事件 |
| Director 计划 | 在当前路径上用什么合法事件完成该功能 | 不取代玩家作下一次重大决定 |
| Narrative 演绎 | 事件、对白、情绪和镜头前的叙事具体如何呈现 | 不把未提交设想写成事实 |
| Production 呈现 | 将合格的完整 Beat 转成视频 | 不为纯粹凑镜头制造情节 |

**PROPOSED：** 首版把 Drama Evaluator 与 Directive 生成实现为 Director 工作流中的明确步骤；同一文本模型可在一次结构化调用中产出语义观察、Directive 与计划草案，避免为了架构图增加多次串行请求。逻辑产物、权限与 Trace 分开即可，不要求单独部署“控制平面服务”。

### 07.9 Dramatic State 的权威性与来源

World Domain 保存真相、物品、关系事实、知情范围、世界时间、压力源的实际进展。Drama Domain 保存 phase hints、Progress 观察、伏笔生命周期、Twist 候选、Wish 的叙事处理、未结线与 Pending Obligations。关系数值和计时器不能同时在两个域各自成为权威副本。

Dramatic State 应显式区分：

- `OBSERVED`：有正式事件、已呈现内容或玩家明确表达支持；
- `INFERRED`：模型依据证据作出的解释，保留置信、来源和可修正性；
- `PLANNED`：未来计划，仅用于候选和排程，不是已发生；
- `RETRACTED / SUPERSEDED`：观察被修正或替换，历史仍可审计。

Jev／LLM 可提出观察和补丁，Drama State Manager 校验输入版本、证据引用、合法路径和域间一致性后提交。多个 Manager 是逻辑分工而非多个可互相覆盖的数据库账号。**Director 不能先把“反转已准备好”写成真，再以这个自填字段作为唯一依据通过反转。**

### 07.10 Progress Vector 与三档响应

Q36 采用明确戏剧作用及最低价值，不采用“每幕必须加一分”。建议 Progress Vector 的维度为 `goal / information / relationship / risk / commitment / foreshadowing / emotional_shift`；每项保存变化描述、支持事件、影响对象及预期／实际标记。数值刻度和阈值需在原型中调整，不从示例直接固化。

| 响应类型 | 适用情况 | 产品输出与状态处理 |
|---|---|---|
| QUICK_ACK | 已明确且低影响的小动作、无关键发现的检查 | 短文本／UI 反馈；有必要事实变化则照常提交；不强发 H3 |
| MERGED_TRANSITION | 玩家连续完成的若干小动作可以共同表达一次探索或过渡 | 保留每次动作与后果；在安全边界汇总，必要时生成一个蒙太奇 |
| FULL_BEAT | 新关键问题、信息揭示、关系改变、风险变化、承诺、伏笔或有价值的情绪转变 | 说明戏剧功能与变化，再进入视频规划和生成 |

重要性 `significance` 与戏剧价值 `dramatic_value` 不同：前者决定是否立即重评，后者决定是否值得完整呈现。一个简短但不可逆的承诺可以同时 HIGH／FULL；一个开局氛围镜头可以有建立预期的价值，不必修改背包或风险数值。

完整 Beat 的 `expected_progress` 是提案，执行后的 `observed_progress` 才能进入已发生记录。不能靠模型写一句“丰富了气氛”无限生成空转视频，也不能为达阈值凭空增加关系值。证据不足或意义很低时应缩短、合并、修改或不生成；安静场景和玩家选择的低刺激路径仍被允许。

### 07.11 双时间尺度与柔性阶段

每个已接受 Action 先做轻量重要性判断；确定性规则可以直接识别消耗关键物品、公开秘密、离开地点等明确高影响变化，Jev 可补充分类与置信。HIGH、低置信高风险或实质改变已有计划时立即触发完整语义评估；LOW 一般不重建全局计划。

每个正式完整 Beat 在完成／明确跳过后的边界至少评估一次。以 `arc_id + beat_id + evaluated_revision` 去重；投机候选评估只能写在分支命名空间。玩家可在 Lead Window 输入下一步，但尚未发生的候选后果不能计入当前篇章进展。

Phase Hint 可以为 `SETUP / EXPLORATION / ESCALATION / REVELATION / CRISIS / CLIMAX / RESOLUTION` 等主／次标签。标签可跳跃、重叠、回落；只是解释当前叙事需求，不是严格推进图。用户开局就查明真相时，允许转入后果或收束，而不是要求补足“探索三幕”。

### 07.12 Pressure Sources 与世界时间

每个压力源应有来源、驱动条件、影响目标、可用机会窗口及世界状态引用。可能由世界时间、玩家行动、NPC 目标或已发生事件推动；Director 只能在合法进展范围内选择呈现方式，不能为了“剧情太慢”直接篡改其到期时间。

**DERIVED：Q33／Q39 不能取消 I02。** 系统必须分开 `wall_time`（现实时间）、`fiction_time`（故事时间）与 `interaction_deadline`（明确限时节点）。建议默认以已接受动作的故事时长和合法世界事件推进 fiction time，UNTIMED 的输入停留、Jev/API 排队、视频重试不计入。玩家选择“睡两小时”与玩家想了两分钟不是同一行为。

NPC 可以在角色不参与时按既定计划行动；不等于后台用玩家不知道的现实倒计时惩罚离线。TIMED 的超时继续按 I03 提交确定性 fallback，随后再由叙事系统描述后果。若未来需要持续现实时间世界，应作为独立模式重新明示，本版不引入。

压力源的事实进度归 World State，Drama State 只引用它并记录显著性、叙事相关性和可用机会。排队成本上升不是角色危险增加；玩家拒绝调查也不自动授权系统凭空产生火灾或绑架。

### 07.13 Truth Model、角色知识与反转

Scenario 的 Truth Model 区分世界真实事实、表面解释、角色知情／误解及证据关系。运行时可以在尚未确定且不与历史矛盾的范围补充新细节，但已确认的关键真相不能为了反转被重写。

一个 Twist Candidate 至少说明：重新解释什么、依赖哪些事实与已呈现线索、玩家可能形成的预期依据、新信息如何重解旧事件、随后哪些目标／关系／可选策略改变。Jev 可判断明确子问题，重大反转的语义合理性由 LLM／Director 审查，硬一致性由规则检查。

反转可通过的条件包括：前文确实存在可追溯线索，候选不违反真相与知情权限，新信息有解释力且会产生后果。只有计划中才出现的证据、未选分支中的对白或尚未播到的内容都不能作为“玩家已经知道”的依据。

`player_belief` 应记录为有来源的假设；玩家明确说过的话和系统推测分开。无法确认预期时，宁可称为信息揭示，而不硬称“成功颠覆玩家认知”。反转不是每局必有，更不是按轮数触发的任务。

### 07.14 Foreshadow Ledger

支持 `AUTHOR_SEEDED` 与 `EMERGENT`。建议生命周期为 `PROPOSED → PLANTED → REINFORCED → PAYOFF_READY → PAID_OFF`，允许根据需要跳过加强或进入 `ABANDONED`；枚举是工程契约，不要求每条伏笔完整走一遍。

每项至少记录关联真相／问题、设定来源、铺设事件、呈现回执、谁可见、支持的解释、可回收条件、所属 Arc 与处理结果。Narrative 提出的新生伏笔必须先登记并通过一致性检查；实际铺设与观众可知性分别由真实事件和呈现记录支持。

不同于伏笔登记，`PAYOFF_READY` 是可修正的组织判断，不是事实。回收必须有真实后果及对应事件引用。允许合理放弃或作为新 Arc 的开放线；没有必要为了“回收率”把所有背景道具强行做成重大秘密。

### 07.15 Wish Ledger、待处理事项与机会仲裁

Wish 保留玩家原文、规范化偏好、作用范围、生效边界、版本和状态。Director 应寻找不破坏因果的实现机会，记录采用、延期、冲突、达成或失败的依据。Wish 达成必须依据实际事件，不根据候选视频或模型一句“已经考虑”认定。

Pending Obligations／Drama Debt 保存已建立但尚待处理的威胁、伏笔、关系问题及应被回应的偏好。每项有来源、相关 Arc、时效条件、优先级理由、可用机会及解决／延期／放弃记录。**愿望得到回应的义务，不等于保证愿望结果实现。**

Q46 的仲裁顺序是：
1. 先满足世界真相、权限、玩家已确定行动和既有事实等硬约束；
2. 识别确有依据的紧迫事项，例如已声明即将关闭的窗口、已建立的承诺；
3. 在剩余空间里选择此刻最自然的戏剧机会，形成一个主要功能和少量次要功能。

具体评分公式不是用户已选常数。债务变久只提高关注，不自动许可灾难、强迫玩家或触发结局。`closing_arc` 义务只能在 Director 已作出有效收束判断后生成，不能因固定轮数反向逼它结束。债务亦可通过合理解释、失败后果、退出结局或新 Arc 的显式承接处理。

### 07.16 结局、退出与新 Arc

Director 输出 `CONTINUE / PREPARE_CLOSURE / CLOSE_ARC` 等结局判断及依据。可读取核心问题、玩家所得信息、不可逆状态、未结关系等摘要，但**这些是参考，不能构成自动 Ending Readiness Gate**。State Service 仍检查选定结局内容的事实合法性；“有权决定收束”不等于有权改写真相。Ending Family 的条件限定该结局方向能否成立，不自动触发收束，也不应使合法退出只能等待所有秘密揭开。

玩家合法退出矛盾时，Director 可形成短的 Consequence Ending，不需要先揭开所有秘密或完成所有伏笔。后果只能来自已建立的因果或有明确不确定性的描述；不得为了让结局显得刺激而恶意惩罚玩家退出。

Arc 关闭时保存结局、闭合的问题、相关事实快照、仍开放／已放弃事项及原因。玩家选择继续后，Authoring／Director 工作流生成新 Arc 草案，复用世界、角色与素材，继承适用的关系、Wish 和线索，同时建立新的核心问题、冲突与压力。新 Arc 可以紧接、跨时间或换焦点，但时间跳跃造成的事实变化仍须合法提交。

已关闭 Arc 不再回写为“其实从未结束”。新篇章不是新付费授权，也不是新的无上限预算；没有资源时存档待续。系统支持持续续玩，不承诺无限上下文、无限内存或自动生成无穷篇章。

### 07.17 双域提交与观察版本

World 事件与关联的 Drama 变更应使用相同 `turn_id / event_id`，接受世界与戏剧基础版本检查。建议由同库 Commit Coordinator 协调 State Service 与 Drama State Manager，在同一事务中提交；如果分服务实现，则须提供等价的一致性与恢复机制，不能先宣传分布式架构再依赖手工补数据。

仅有语义评价更新时，可以只增加 Drama revision，不篡改 World version；但若它改变某个候选所依赖的 Directive／Arc 计划，则相关候选必须失效。偏好、置信或排序元数据变化是否影响媒体，应按依赖判断；首版允许保守失效并记录成本。

Proposal 必须包含 base versions、source、operation、evidence refs、confidence（若为推断）和影响域。正式推断被修正时追加替代记录，不删除历史事实。预生成分支的 DramaPatch 和 WorldPatch 只能在玩家选中、前置条件仍成立后提交。

### 07.18 示例：同一世界，三条真实路径

**下例仅演示契约，不是固定样板剧情。** 作者已设定 Alice 午夜会离开；玩家已看见她整理行李，这个线索有正式呈现记录。

| 玩家行为 | 合法世界回应 | 戏剧处理 | 不允许的捷径 |
|---|---|---|---|
| 检查一个空抽屉 | 告知未发现内容，记录已检查 | QUICK_ACK；通常无需重规划和视频 | 为每个抽屉凭空制造新证据 |
| 明确表示想保护她，询问她离开的原因 | 她按已知秘密与性格回应 | 关系／信息变化可形成 FULL_BEAT；相关伏笔登记 | 把“保护”错误推断成“攻击”后直接执行 |
| 选择睡到第二天或直接离城 | 按已有计划推进 departure；保留后果 | 可发生窗口关闭，或 Director 形成退出结局 | 等玩家回到页面才凭空插入绑架，强拉回主线 |

若玩家选择“继续这个世界”，新 Arc 可围绕离城后的新生活或合法未结线展开；不得把已经离城的事实悄悄抹掉。是否有趣最终仍由玩家反馈判断，而不是表格满足即算成功。

## 08. 四 Agent 协作与模型边界

### 08.1 职责与产物

| Agent | 输入 | 必需产物 | 允许调用 | 禁止越权 |
|---|---|---|---|---|
| Director | Story Spine、World／Drama 视图、Arc、Wish、事件 | DramaticDirective、RollingPlan、结局／续篇判断与升级决策 | Narrative、State、Jev、戏剧评估工作流与 Skills | 不直接写状态，不为戏剧方便改真相或替玩家决策 |
| State | 规则、当前状态、Action／Proposal | 校验建议、冲突诊断、通过服务提交的事件、记忆更新 | State Service、机制 Skills | 不用纯语言判断绕过确定性事务校验 |
| Narrative | Action／Desire、合法后果、Directive、计划与可见信息 | 快速／合并反馈、StoryBeat、Progress 提案、伏笔候选、对白与行动文本 | 意图／叙事／机制相关 Skills | 不能把提案写成正式伏笔，不发明玩家未选择的重大决定 |
| Production | StoryBeat、资产与视觉状态、能力矩阵、预算 | ShotPlan、GenerationJob、SceneArtifact | 连续性、H3 生产、剪辑 Skills 与媒体工具 | 不把不支持的参考输入静默删除后宣称成功 |

创作阶段还需要 `scenario-authoring` 工作流，但无需因此增加第五个常驻运行时 Agent；它可由 Director 的创作模式或独立非运行时任务执行。四个角色可以共享同一个本地推理端点，区别在于上下文、任务、工具权限和输出契约。

### 08.2 v0.5 双执行主链

Q55 将“已 Ready 的系统推荐”与“计划外自由输入”正式分开；二者最终都归一到 `BranchContract`，因此不会维护两套世界语义。

**路径 A：Ready Recommendation**

```text
当前 Scene 播放
  → Director / Drama 在后台产生 Candidate Skeletons
  → Jev 排序并确定 K
  → K 条 Branch 并行：Narrative → Production → H3 → Assembly
  → 所有待发布 Branch 达到 READY（失败分支按 Q63 重试／降 K）
  → 原子发布推荐面板
  → 玩家点击某个 READY Branch
  → 轻量版本／前置条件校验
  → status = SELECTED，建立 provisional view
  → 立即允许用 provisional state 规划 N+2
  → Scene 可播放确认
  → World／Drama / Event Log 正式 CANONICAL commit
```

点击 Ready 推荐时不得重新调用 Director／Narrative 来“再解释一次”该分支，也不得重新发起同一视频任务。若版本失效，撤回旧推荐并按真实 miss／重建处理。

**路径 B：Free-form Action**

```text
玩家原文
  → Jev First Pass（intent / significance / desire / confidence / trigger）
  → raw input + Jev observation 一起交 Director
  → World / Drama 评估 + Dramatic Directive
  → Director Final Branch Skeleton
  → ScenePacket → Narrative（Step 3.7 Flash）
  → Production Plan（本地 Lightning，失败可 Step 3.7 fallback）
  → H3 Max / 当前 Video Provider
  → READY
  → SELECTED / CANONICAL 提交流程
```

Jev 只提供 observation，不能因高置信就删除玩家原文；Director 有权基于更完整上下文修正 observation。自由输入若语义等价命中一个有效内部 Branch，可直接复用对应工件，但必须通过 Dependency Fingerprint 与意图等价校验。

### 08.3 三类 Provider，不强行套一种接口

| Provider | 统一的内部接口建议 | 为什么单独定义 |
|---|---|---|
| TextModelProvider | `generate(messages, output_contract, tools, budget)` | 适配本地模型和 StepFun 的文本／工具输出 |
| DecisionProvider | `evaluate(state, questions, model_version)` | Jev 是类型化问题评估接口，不是普通聊天补全 [S05] |
| VideoProvider | `capabilities(), submit(), status(), result(), cancel_if_supported()` | 视频生成是有工件与长任务状态的过程 [S02][S03] |

“可切换模型”仅表示 Runtime 解耦；它不自动保证输出质量、工具行为、所有输入模式或参数名等价。配置必须同时绑定模型 ID、适配器版本、输出契约与已通过的测试集。

### 08.4 不增加第五个 Agent 的实现方案

建议将新增部分实现为 `evaluate_drama / build_directive / plan_arc / review_ending` 等 Director 内部工作流节点，外加确定性的 `DramaStateManager`。Jev 的 DecisionProvider 复用现有接口；State／Drama 可以共用一个持久化层；Narrative 和 Production 的职责保持清晰。

逻辑上的“独立评估”意在固定来源、输入和权限，并不要求另一份大模型常驻 Spark。双域状态、额外上下文与记录会增加资源消耗，仍遵循 14.3 的分时 profile，不以新增戏剧功能为由假定内存突然足够。


### 08.5 最终模型与 Agent Runtime 分工

| 角色／能力 | Primary | Fallback | 运行位置 | 备注 |
|---|---|---|---|---|
| Director | Nemotron 3.5 Lightning 30B-A3B NVFP4 | Step 5 Preview API | DGX Spark → 云端 | 本地高频规划；fallback 以质量优先 |
| State Manager | 确定性代码 | — | 本地 | 事务、版本、幂等、授权；不是 LLM Agent |
| State semantic parsing | 复用 Lightning | Director fallback 链可处理高影响解析 | 本地／云端 | 只输出 Proposal，不直写状态 |
| Drama Control | Rules + Jev + Director | 随 Director route | 混合 | 不新增第五个基础模型 |
| Narrative | Step 3.7 Flash API | Lightning local（仅 Profile 可用时） | 云端 → 本地 | 只演绎 ScenePacket，不重做全局计划 |
| Scenario Authoring | Step 5 Preview API | 未冻结第二 fallback | 云端 | 低频、高质量优先 |
| Production | Lightning local + `h3-production` | Step 3.7 Flash API | 本地 → 云端 | 保持独立 Production 契约 |
| Fast Decision | Jev API | 未冻结替代模型 | 云端 | 路由／分类／排序／confidence |
| Video | H3 Max API | Sol-H3 作为可选本地 Provider，而非透明错误 fallback | 云端／本地 | 两后端能力和速度不同 |
| Assembly | FFmpeg／程序 | — | 本地 | 确定性媒体处理 |

“fallback”指同一 Agent 职责下的 Provider 降级，不意味着不同模型输出等价。每次 fallback 都记录源模型、触发原因、输入契约版本和下游工件。

### 08.6 Director 的 Hierarchical Working Context

Director 不默认读取整个 Event Log。每轮工作上下文按以下层级构造：

1. `Scenario Core`：核心世界规则、当前 Arc 的 dramatic question 与不可变 Truth 引用；
2. `Canonical State Slice`：当前地点、相关人物／道具／任务的最小事实视图；
3. `Drama State`：柔性阶段、Pressure、Wish、Foreshadow、Pending Obligations 等相关条目；
4. `Arc Summary`：当前篇章压缩摘要，带来源事件范围；
5. `Recent Events`：最近 3–8 个高重要度事件作为初始建议值，实际数量按 token budget 决定；
6. `Retrieved History`：按实体、事件类型、标签、重要性或后续向量检索选取旧事件；
7. `Current Input`：玩家原文与 Jev observation。

全量 Event Log 始终留在权威存储，摘要与检索只是上下文构造层，不能覆盖硬事实。模型支持 1M context 不构成每轮塞满上下文的理由。

### 08.7 Narrative ScenePacket

Narrative 不接收完整 Scenario／Drama 数据库，而接收 Director／State 构造的最小 `ScenePacket`。至少包含：

- 已冻结的 `StoryBeat / Branch Skeleton`；
- `dramatic_function` 与本幕目标；
- 出场角色人格、当前情绪、**该角色真正知道的内容**；
- 当前场景可见真相与 `allowed_revelations / forbidden_revelations`；
- 关系与必要的历史片段；
- 风格、语气、时长和生产约束；
- 不得改写的 world facts 与 player commitment。

原则是：**Director knows the story; Narrative knows the scene.** Narrative 可以丰富对白、动作、节奏和微观表演，但不能改变核心事件、提前泄密或把提案写入 Canonical State。

### 08.8 Agent DAG 与并行边界

Q60 选择“阶段边界串行、边界内部并行”。必须先冻结：

```text
raw input + Jev observation
        ↓
Director Final Branch Skeleton
```

Skeleton 冻结后可以并行：`Narrative / asset retrieval / continuity preparation / StatePatch pre-validation`。Narrative 完成后可以并行：`Production prompt / voice preparation / subtitle preparation`。依赖前一镜头输出的镜头仍在分支内部串行。

Q59 进一步要求：**Top-K 一旦确定，K 条 Branch 彼此完全并行启动。** 不再采用“先 Top-1、再排队 B/C”的默认策略；资源不足应在确定 K 前体现为更小的 K。

### 08.9 Branch 两阶段 Canonicalization

Branch 状态至少区分：

```text
PLANNED → RENDERING → READY → SELECTED → CANONICAL
                              ↘ FAILED / INVALIDATED / EXPIRED
```

玩家点击 READY Branch 后立刻进入 `SELECTED` 并建立 provisional state view；N+2 的低成本计划可以读取该视图，以利用正在播放的 N+1 视频时间。只有当 Scene 已确认可播放并且最终前置条件仍成立，World／Drama／Event Log 才原子转为 `CANONICAL`。播放／工件验证失败时回滚 provisional view，不得留下正式伏笔、Wish 达成或状态修改。

## 09. Agent Skills 设计

### 09.1 Skill、工具、Agent、Runtime 的区别

Agent 是持有职责、上下文和可调用能力的执行者；Skill 是可被发现和按需加载的任务说明、规则、参考资料及可选脚本；工具执行具体动作；Runtime 负责会话、权限、调度、存储、状态事务和日志。

Agent Skills 开放规范以 `SKILL.md` 为入口，并支持脚本、参考资料和资产目录；它并不自带本产品的世界状态、强类型 I/O、UI 组件或数据库权限模型。[S09] 因此本文的 `contract.json`、触发事件与状态提案规则是 **本项目扩展契约** ，不能宣传成所有 Agent Skills 平台天然支持的标准。

### 09.2 P0 技能清单

| Skill ID | 能力与触发 | 输入 → 输出 | 核心质量门 | 复用与原创边界 |
|---|---|---|---|---|
| SK-01 scenario-authoring | 创建／修改故事及新 Arc 草案 | 想法＋资产＋继承摘要 → 世界／戏剧草案及局部补丁 | 真相、压力、欲望、伏笔等引用可验证，不覆盖已有事实 | 复用原创作流程，不增加强制专业表单 |
| SK-02 intent-reconciliation | 自由／含糊／不合设定输入 | 原话＋可见状态＋规则 → Action／Desire／Strategy＋回显／澄清 | 原文保留、显式动机优先、置信不确定可升级，不擅自替换重大行动 | 复用意图 Skill，Jev 提供辅助判断而非直接写事实 |
| SK-03 visual-continuity | 每次镜头规划 | 身份资产＋临时状态＋前镜头 → 连续性约束 | 角色、衣着、持物、时间、地点引用可追踪 | 自有状态化约束；可扩展音色条件 |
| SK-04 h3-production | Beat 进入媒体阶段 | Beat＋参考映射＋能力矩阵 → ShotPlan／请求计划 | 模式支持、标签对应、时长合法、预算内 | 可复用官方 h3-prompt-writing 的模式规则，新增状态与 Provider 适配 [S10] |
| SK-05 video-assembly | 镜头生成完成 | 镜头工件＋剪辑计划 → SceneArtifact | 音视频可解码、规格统一、无误拼分支 | 自有叙事装配策略；底层调用 FFmpeg [S17] |
| SK-06 mechanic-* | 满足所选玩法事件 | Action／Event＋机制配置 → StatePatchProposal＋UIEvent | 数值合法、无直接写库、结果影响后续剧情 | 至少实现 clue 或 relationship 一种；具体题材选择是建议 |

五个平台级 Skills 加至少一个机制 Skill 是本次建议的最小实现集合，与 Q23／Q24 的方向一致。基础设施如数据库、队列、Jev API client、缓存和 GPU 资源管理不是为了凑数量而增加的 Skill。

### 09.3 真正执行 Skill 的 Harness

建议 Harness 在启动时扫描已审核技能的名称和描述；执行任务时选择相关 Skill，加载其指令与必要参考；将版本、允许工具、输入契约和预算加入本次执行上下文；执行期间记录产生的工具调用和工件；结果通过 Schema 与领域规则后才进入下游。

没有参与本次执行的 `SKILL.md` 不能只凭目录存在就记一次成功调用。日志至少保留 `skill_id / skill_version / instruction_hash / trace_id / input_artifact / output_artifact / tool_spans / status / duration`。 **不要求保存或展示模型隐藏推理；保存可审计的输入输出摘要、工具参数、公开决策理由和工件即可。**

### 09.4 技能目录建议

```text
skills/visual-continuity/
  SKILL.md
  references/
    continuity-rules.md
    h3-reference-mapping.md
  scripts/
    build_constraints.py
  contracts/
    input.schema.json
    output.schema.json
  runtime/
    contract.json
  tests/
    fixtures.json
```

`SKILL.md` 的最小前置元数据采用 `name` 和 `description`；本项目的权限、超时、版本和事件配置放在扩展文件中。特定平台的 UI 元数据按需添加，不把某个平台的专用目录当成跨平台强制要求。[S09][S10]

### 09.5 机制不是随意加分

机制 Skill 必须在自己的规则文件中声明状态字段、合法取值、触发条件、数值变化依据、冲突处理及 UI 输出。例如线索收集至少包含“未发现 → 已发现 → 已验证／已用于推理”等有意义的状态；关系机制至少说明一次行动如何影响信任，以及该变化怎样改变后续人物反应。

完整 QTE 玩法系统仍可后移；I02／I03 要求的最小 TIMED 互动与确定性超时必须保留，可用一次紧急对话实现。计时由 Runtime 管理，不能用生成模型响应速度决定成败。线索 Skill 的道具／发现状态属于 World Domain，伏笔的戏剧用途与生命周期属于 Drama Domain，通过事件引用关联，不能各自创造一份“真相”。

### 09.6 技能扩展与安全

P0 建议只加载自有或人工审核的技能包。Creator 可以选择技能和编辑配置，但 AI 生成 Scenario 不等于获得在服务器执行任意脚本的权限。新增机制应声明所需字段与依赖；卸载有状态机制需要迁移策略，不能直接删除其他剧情依赖的事实。

现场验收以 Q28 B 的 **真实调用链日志** 为准。技能安装／卸载动画、热插拔和对照视频可作为后续增强，不挤占已确定的三类素材支持。

### 09.7 戏剧能力与 Skill 的关系

Q23 的原则不变：Skill 封装可复用工作流，Runtime 承担确定性基础设施。现有 `scenario-authoring`、`intent-reconciliation`、`h3-production` 及玩法 Skill 的输入输出扩充后即可支撑第一版 Drama Control；**不要求为每个 Ledger、阈值或状态表新建 Skill。**

可在后续将成熟的戏剧规划／反转复核工作流提炼成 Skill，但此项是 PROPOSED，不能自动增加 SK-07 等 P0 数量。Drama State Manager、版本事务、计时器、预算与缓存依然属于 Runtime。Q28 B 的真实 Skill 日志保留；Director 的戏剧评估也应有执行记录，但普通函数步骤不能谎称调用了一个从未加载的 Skill。

## 10. 数据契约与 Scenario Package

### 10.1 核心实体

以下是本项目的建议数据模型，非任何供应商已提供的 API。全部 ID 应稳定且可追踪，模型输出必须经 Schema 验证。

| 实体 | 最小字段 | 关键约束 |
|---|---|---|
| ScenarioVersion | id、version、manifest、rules、characters、dramatic_spec、truth_model、pressure_definitions、anchors、ending_families、skill_refs、asset_refs | 发布后不可原地修改；戏剧草案经审阅；会话绑定版本 |
| Session | id、scenario_version、state_version、drama_revision、active_arc_id、arc_revision、wish_version、preference_version、current_turn、provider_profile、budget | 双域版本区分；继续新 Arc 不自动重置会话总预算 |
| PlayerPreferenceState | session_id、version、signals、evidence_event_refs、updated_at | 只从本局真实行为更新；用于排序启发，不是世界事实或人格诊断 |
| PlayerInput | id、session_id、turn_id、raw_text、channel、candidate_id、idempotency_key | 原始文本不覆盖；候选选择也记录来源 |
| ResolvedIntent | actor、action、target、desire、strategy、evidence、confidence、impact、clarification_status、reconciliation_text | 保留原文引用与显式／推断来源；未知动机允许为空，不为命中缓存改意图 |
| Wish | id、raw_text、normalized_preference、scope、status、effective_from_turn、version、evidence_refs | 玩家偏好和叙事处理单一来源；跨 Arc 需检查范围，达成依真实事件 |
| StoryBeat | id、arc_id、base_versions、intent_refs、directive_ref、dramatic_function、expected_progress、observed_progress、events、dialogue、world_patch_ref、drama_patch_ref、next_decision | 预期／已发生分开；完整 Beat 可多 Shot；不替玩家作下一关键决定 |
| ShotPlan | id、beat_id、duration_s、aspect_ratio、resolution、visual_constraints、references、dialogue、transition | 参考素材有 ID、版本、模态与用途 |
| GenerationJob | id、provider、provider_job_id、profile、state、request_hash、cost_reservation、artifact_ref | 任务状态与本局世界状态分开 |
| BranchContract | branch_id、recommendation_epoch、raw_or_candidate_intent、jev_observation_ref、director_plan_ref、scene_packet_ref、base_versions、world_patch、drama_patch、beat_ref、jobs、artifact_ref、dependency_fingerprint、status、expiry | 推荐与自由输入统一的一级对象；未 `CANONICAL` 前不得成为正式历史 |
| SpeculativeBranch | candidate_id、base_versions、arc_id、world_patch、drama_patch、beat_ref、jobs、expiry、read_set | 未选择前双域隔离；未看见的内容不能建立玩家信念／伏笔回收 |
| SceneArtifact | id、beat_id、arc_id、clip_refs、assembled_video、audio、subtitle、provenance、quality_status、presentation_receipts | Ready 与已呈现区分；保留来源、Arc 与分支归属 |
| StatePatchProposal | proposal_id、base_version、actor、source_skill、operations、preconditions、event_refs | 白名单字段、前置条件、幂等检查 |
| SkillInvocation | trace_id、skill_id、version、instruction_hash、inputs、outputs、tools、status、latency | 由真实执行产生，不是演示用伪日志 |
| ScenePacket | branch_id、beat、dramatic_function、character_views、scene_truth、allowed_revelations、forbidden_revelations、relationship_context、style、production_constraints | Narrative 的最小授权上下文；不得包含无关秘密 |
| ProviderRouteEvent | trace_id、role、primary_provider、selected_provider、model_version、profile、reason、attempt、health_snapshot、latency | 每次 primary／retry／fallback 可追溯；不把云端 fallback 标成 local |
| RuntimeProfile | profile_id、local_services、unavailable_fallbacks、memory_guard、transition_state、health | 单 Spark profile 的显式事实来源；Router 以此计算可用 Provider |

### 10.2 统一 Skill 外壳示例

示例展示字段约定，不代表已经写好完整的 JSON Schema。传入 Skill 的状态应是最小授权视图，而不是整份数据库。

```json
{
  "schema_version": "1.0",
  "trace_id": "trace_demo_001",
  "session_id": "session_demo_001",
  "turn_id": "turn_003",
  "scenario_ref": {"id": "rainy_apartment", "version": "1.0.0"},
  "base_state_version": 12,
  "base_drama_revision": 7,
  "arc_id": "arc_001",
  "arc_revision": 2,
  "wish_version": 2,
  "event": {
    "type": "PLAYER_ACTION",
    "actor_id": "player",
    "target_id": "alice"
  },
  "state_view": {
    "location_id": "hallway",
    "player_items": ["coat"],
    "alice_trust": 40
  },
  "payload": {
    "raw_text": "我把外套递给她，但不跟她上楼。",
    "resolved_goal": "表达关心，同时留在当前地点"
  },
  "constraints": {
    "allowed_proposal_paths": ["/characters/alice/trust"],
    "max_model_calls": 1,
    "deadline_ms": 3000
  }
}
```

`deadline_ms` 与调用次数是示例预算，不是已验证 SLA。一个可能的输出如下；加 3 分也只是示例，实际值必须由该 Scenario 的机制规则决定。

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "state_patch_proposals": [
    {
      "proposal_id": "proposal_demo_003",
      "base_state_version": 12,
      "source_skill": "relationship@1.0.0",
      "preconditions": [
        {"path": "/characters/alice/trust", "equals": 40}
      ],
      "operations": [
        {"op": "increment", "path": "/characters/alice/trust", "value": 3}
      ],
      "reason": "符合本场景关心行为规则；没有改变玩家位置"
    }
  ],
  "narrative": "Alice 接过外套，发现你并没有跟上来。",
  "ui_events": [{"type": "relationship_changed", "target": "alice"}],
  "artifacts": [],
  "warnings": []
}
```

`increment` 是项目自定义操作，不应误称为标准 JSON Patch 操作。实现时可以转换成标准补丁加事务校验，或明确采用自有 DSL。

### 10.3 Scenario 包建议结构

```text
scenario/
  scenario.yaml
  world/
    rules.yaml
    locations.yaml
    lore.md
  characters/
    alice.yaml
    alice.md
  story/
    premise.md
    anchors.yaml
    ending-families.yaml
    drama-spec.yaml
    truth-model.yaml
    pressure-sources.yaml
    initial-foreshadows.yaml
  mechanics/
    config.yaml
  assets/
    manifest.json
    images/
    voices/
    videos/
  skills/
    skills.lock.json
  ui/
    theme.json
  tests/
    initial-state.json
    scenario-smoke-cases.json
```

技能既可以是通过哈希锁定的可复用依赖，也可以随包附带经审核的技能目录；必须能判断来源和版本。大媒体与模型权重不应塞进 Skill 指令文件。包内路径需校验，不允许路径穿越或导入时执行任意脚本。

```yaml
schema_version: "1.0"
id: rainy_apartment
version: "1.0.0"
title: 雨夜公寓
language: zh-CN
entrypoint: story/premise.md
player_character_id: player
world_rules: world/rules.yaml
character_refs:
  - characters/alice.yaml
initial_state_ref: tests/initial-state.json
story:
  anchors_ref: story/anchors.yaml
  endings_ref: story/ending-families.yaml
  drama_spec_ref: story/drama-spec.yaml
  truth_model_ref: story/truth-model.yaml
  pressure_sources_ref: story/pressure-sources.yaml
  initial_foreshadows_ref: story/initial-foreshadows.yaml
assets_manifest: assets/manifest.json
skills_lock: skills/skills.lock.json
mechanics_config: mechanics/config.yaml
ui_theme: ui/theme.json
required_media_capabilities:
  - reference_image
  - reference_audio
  - reference_video
```

### 10.4 Provider 能力矩阵

每个实际部署 profile 都应声明：文生视频、首尾帧、图／声／视频参考、支持时长、尺寸、最大输入数、原生音频、种子、取消、状态查询、可报告的计时字段。每项区分 `documented / tested / unsupported / unknown`。

 **不能因为同属 H3 系列就默认模式完全对等。** H3 Max 云端全能参考接口有文档支持；Spark 当前实现支持哪些模式、素材组合与上限，仍需在选定提交和配置上逐项验证。[S02][S03][S04] 本产品的三类素材 P0 可由已通过测试的云端 profile 完整承担；本地 profile 必须真实生成，但未验证的功能不得显示成已支持。

### 10.5 Drama 扩展实体及权威归属

以下字段是本项目的建议最小契约，不代表已实现完整 Schema。已确认的是能力与边界，字段命名可在保持语义和迁移记录的前提下调整。

| 实体 | 最小字段／作用 | 权威性与限制 |
|---|---|---|
| DramaticSpec | core_question、central_conflicts、character_desires、truth_refs、pressure_refs、initial_foreshadows、ending_directions | Scenario 中的创作定义，由 AI 起稿、Creator 审阅 |
| DramaticState | session_id、arc_id、revision、phase_hints、progress_refs、ledger_refs、pending_obligations、last_evaluated_event | Manager 管理的组织状态，不是一份可覆盖世界的第二真相 |
| DramaObservation | type、value、source、evidence_refs、confidence、observed_or_inferred、base_versions | 分类／解释可修正；不得把未知 belief 变成确定事实 |
| DramaticDirective | primary_function、secondary_functions、target_changes、hard_constraints、preferred_opportunities、avoid、evidence_refs | 功能目标，不是完整剧本；绑定 Arc／World／Drama 版本 |
| ActionResponsePlan | input_refs、significance、response_mode、feedback、expected_world_patch、expected_drama_patch、merge_group_id | QUICK／MERGED／FULL 都必须保留用户行动和必要后果 |
| ProgressEvidence | dimension、change、affected_entities、event_refs、presentation_refs、planned_or_observed | 不是单纯给七个维度打分；不得重复累计同一个事件 |
| TruthFact／KnowledgeRecord | fact_id、value、status、introduced_at、known_by、evidence_refs | 关键事实在 World Domain；推测与真相分开、访问受限 |
| TwistCandidate | reinterpretation、truth_refs、required_evidence、belief_hypotheses、consequences、review_status | 通过事实／呈现／语义检查才能执行；不保证玩家实际感到意外 |
| ForeshadowEntry | origin、arc_scope、supporting_truth、status、planted_event、presentation_refs、payoff_refs、abandon_reason | 新生成需注册；未选分支不得入正式 Ledger |
| PressureSourceDefinition | origin、driver、trigger_conditions、targets、window、consequence_rules | 作者／已批准世界规则定义；动态新增须有合法因果来源 |
| PressureInstance | source_id、world_state_ref、progress、deadline_basis、evidence_refs | 实际进展归 World，Drama 只保存呈现相关性与优先观察 |
| PendingObligation | source_ref、kind、scope、urgency_reason、opportunities、status、resolution_refs | 可延期、失败、放弃或转入新 Arc；Wish 不是必兑现保证 |
| EndingDecision | arc_id、decision、ending_family、reason、evidence_refs、unresolved_disposition、author | author 为 Director；没有强制 readiness_score 门槛 |
| StoryArc | id、parent_arc_id、status、premise、question、conflicts、opened_at、closed_at、closure_ref、carryover_refs | 关闭的是篇章；新 Arc 不抹去旧事实／旧结局 |
| DramaPatchProposal | proposal_id、base_versions、source、operations、evidence_refs、scope、idempotency_key | Manager 校验；scope 区分 canonical 与 speculative |
| PresentationReceipt | artifact_or_message_id、scene_id、visible_segments、knowledge_refs、timestamp、skip_status | 防止把“生成过”误当“玩家已看见” |
| PlayerExperienceFeedback | session_id、arc_id、liked_or_not、reasons、relevant_turns、wants_continue、assistance_notes | 来自真实体验者；未收集不填假值，不等于所有玩家结论 |

`StoryArc` 与运行中的 Ledger 存在会话存档内，不回写不可变 Scenario 发布包。跨 Arc 沿用同一世界状态版本链；旧 Arc 的关闭快照只读，事件继续追加。

### 10.6 意图观察与置信分流示例

```json
{
  "input_id": "input_017",
  "raw_text": "我跟着她，但别让她发现。我是想保护她。",
  "resolved": {
    "action": "follow_alice",
    "desire": "protect_alice",
    "strategy": "avoid_detection",
    "desire_source": "PLAYER_EXPLICIT"
  },
  "confidence": {
    "value": 0.91,
    "source": "decision_provider",
    "calibrated_for_this_task": false
  },
  "impact": "MEDIUM",
  "clarification": {
    "required": false,
    "reason": "玩家已直接说明动机，且没有冲突的显式限制"
  },
  "evidence_refs": ["input_017"]
}
```

0.91 只是字段示例，不是已测结果。玩家明确说“保护”，模型不能因历史偏好更爱调查就将 desire 改成“寻找罪证”。同一行动存在实质不同动机、且会改变不可逆后果时，先澄清再提交；不确定也可保留 desire 为未知。

### 10.7 Dramatic Directive 与 Progress 示例

```json
{
  "directive_id": "directive_017",
  "arc_id": "arc_001",
  "base_versions": {
    "world": 12,
    "drama": 7,
    "arc": 2,
    "wish": 2
  },
  "primary_function": "REVEAL_EXISTING_PRESSURE",
  "secondary_functions": ["DEVELOP_RELATIONSHIP"],
  "target_changes": [
    {
      "dimension": "information",
      "description": "让玩家理解已经建立的离开计划对当前选择的影响",
      "source_refs": ["fact_departure", "event_luggage_seen"]
    }
  ],
  "hard_constraints": [
    "保留玩家不暴露自己的明确要求",
    "不得改变已确认的离开时间",
    "不得泄露玩家尚未知晓的核心真相"
  ],
  "preferred_opportunities": ["pressure_alice_departure"],
  "avoid": ["unestablished_disaster", "forced_player_confrontation"],
  "pending_obligation_refs": ["obligation_004"],
  "evidence_refs": ["input_017", "event_luggage_seen"]
}
```

Directive 说明需要的作用与边界，而非规定下一秒必须发生哪个事件。Narrative 生成事件草案后，输出例如：

```json
{
  "beat_id": "beat_009",
  "arc_id": "arc_001",
  "response_mode": "FULL_BEAT",
  "directive_ref": "directive_017",
  "dramatic_function": "REVEAL_EXISTING_PRESSURE",
  "expected_progress": [
    {
      "dimension": "information",
      "change": "玩家获得关于离开计划的新确认",
      "evidence_basis": ["fact_departure"],
      "planned_or_observed": "PLANNED"
    },
    {
      "dimension": "relationship",
      "change": "NPC 对玩家的保护行为作出符合当前关系的反应",
      "evidence_basis": ["input_017"],
      "planned_or_observed": "PLANNED"
    }
  ],
  "observed_progress": [],
  "world_patch_proposal_ref": "world_proposal_017",
  "drama_patch_proposal_ref": "drama_proposal_017"
}
```

具体是否被玩家看到、NPC 关系是否真的改变，要在执行／呈现之后依正式事件补入 observed progress。纯计划不能支撑下次反转或“愿望已达成”。

### 10.8 DramaPatch 与联合提交示例

```json
{
  "proposal_id": "drama_proposal_017",
  "scope": "CANONICAL_CANDIDATE",
  "session_id": "session_demo_001",
  "arc_id": "arc_001",
  "turn_id": "turn_017",
  "base_versions": {
    "world": 12,
    "drama": 7,
    "arc": 2,
    "wish": 2
  },
  "source": {
    "role": "narrative",
    "invocation_id": "invocation_017"
  },
  "operations": [
    {
      "op": "propose_foreshadow",
      "entry_id": "foreshadow_003",
      "origin": "EMERGENT",
      "supporting_truth_refs": ["truth_002"],
      "status": "PROPOSED"
    }
  ],
  "required_world_proposal": "world_proposal_017",
  "evidence_refs": ["input_017"],
  "idempotency_key": "session_demo_001:turn_017:drama"
}
```

这里的操作是项目 DSL，不是标准 JSON Patch。`CANONICAL_CANDIDATE` 表示待正式提交，不等于已生效；投机提案使用 `SPECULATIVE` 并带 branch_id。Manager 不允许 Narrative 借一个 propose 操作直接把状态跳成 `PAID_OFF`。

建议联合提交过程为：校验 World／Drama 基础版本 → 校验双方前置条件与引用 → 验证反馈／媒体已可呈现 → 单事务写两域变化、事件及 outbox → 后续呈现回执更新可见性。仅更新推断时不要求媒体，但仍须有证据与版本，不可凭空创造剧情事件。

### 10.9 StoryArc 与 EndingDecision 示例

```json
{
  "ending_decision": {
    "arc_id": "arc_001",
    "decision": "CLOSE_ARC",
    "author": "DIRECTOR",
    "ending_family": "voluntary_departure",
    "reason": "玩家明确离开当前矛盾，其行动及合法后果已经足以形成阶段性结局",
    "evidence_refs": ["input_leave_city", "event_departure_confirmed"],
    "unresolved_disposition": [
      {
        "ref": "secret_002",
        "disposition": "LEFT_UNKNOWN"
      }
    ]
  },
  "continuation": {
    "requires_player_request": true,
    "next_arc_status": "NOT_CREATED",
    "inherit_world": true,
    "inherit_relationships": true,
    "recheck_wish_and_obligation_scope": true,
    "recheck_budget_and_permissions": true
  }
}
```

本对象故意不含 `minimum_readiness_score / mandatory_beat_count / soft_max_beats`。Director 可以在较早或较晚位置关闭 Arc，但必须说明与真实经历的关系。玩家未点击继续时，不自动生成下一篇章；新 Arc 有新 ID、新问题／冲突／压力，旧 Arc 的 closure_ref 永久保留。

### 10.10 Scenario 戏剧定义与运行策略

AI 起草的 `drama-spec.yaml` 应表达内容定义，不把运行中的得分写进发布配置。建议结构：

```yaml
schema_version: "1.0"
core_question: "在真相与关系发生冲突时，玩家愿意承担什么代价？"
central_conflict_refs:
  - conflict_truth_vs_trust
character_desire_refs:
  - desire_alice
truth_model_ref: truth-model.yaml
pressure_sources_ref: pressure-sources.yaml
initial_foreshadows_ref: initial-foreshadows.yaml
ending_families_ref: ending-families.yaml
phase_policy: SOFT_HINTS
ending_authority: DIRECTOR
continuation_mode: CLOSE_ARC_THEN_NEW_ARC
```

运行策略另存，以下是建议配置，不是新的用户投票：

```yaml
drama_runtime:
  evaluation:
    on_high_impact_action: true
    after_full_beat: true
    allow_rule_fast_path: true
    uncertain_or_high_impact_escalation: true
  response_modes:
    - QUICK_ACK
    - MERGED_TRANSITION
    - FULL_BEAT
  time:
    default_basis: COMMITTED_FICTION_ACTIONS
    charge_untimed_thinking: false
    charge_model_latency: false
    timed_fallback_from_scenario: true
  recommendation:
    ready_policy: ALL_READY_BEFORE_PUBLISH
    ready_artifact_type: VIDEO_SCENE
  ending:
    authority: DIRECTOR
    readiness_is_advisory_only: true
    auto_close_on_beat_count: false
    continuation_requires_player_request: true
  evaluation_of_experience:
    primary: REAL_PLAYER_FEEDBACK
    blind_comparison_required: false
    automated_drama_judge_required: false
```

上面的 runtime 配置不得被 Creator 的自然语言故事文本覆盖；它属于产品权限和执行策略。故事时钟的每种行动成本、压力源触发规则与用户测试样本规模仍需在实现／试用中确定，不伪装成已有实验结果。

### 10.11 BranchContract 示例

```json
{
  "branch_id": "branch_017",
  "recommendation_epoch": "rec_008",
  "status": "READY",
  "base_versions": {
    "world": 128,
    "drama": 31,
    "arc": 7,
    "wish": 4,
    "assets": 12
  },
  "intent": {
    "raw_text": "我先假装离开，再绕到后门观察。",
    "action": "fake_leave_then_observe",
    "desire": "discover_truth",
    "strategy": "avoid_detection"
  },
  "jev_observation_ref": "jev_obs_017",
  "director_plan_ref": "plan_017",
  "scene_packet_ref": "scene_packet_017",
  "beat_ref": "beat_017",
  "world_patch_ref": "wp_017",
  "drama_patch_ref": "dp_017",
  "jobs": ["video_job_51", "assembly_job_18"],
  "artifact_ref": "scene_017.mp4",
  "dependency_fingerprint": "sha256:...",
  "expiry": "arc_or_ttl_policy"
}
```

推荐路径的 `candidate_id` 与自由输入原文最终都归一成 BranchContract。READY 不代表事实已经发生；只有 `CANONICAL` 才进入正式历史。

### 10.12 ScenePacket 示例

```json
{
  "branch_id": "branch_017",
  "story_beat": {
    "event": "玩家在不暴露怀疑的情况下绕到后门观察 Alice",
    "dramatic_function": "REVEAL_INFORMATION"
  },
  "characters": {
    "alice": {
      "personality_ref": "char_alice_v4",
      "current_emotion": "uneasy",
      "knowledge": ["knows_player_saw_blood"],
      "does_not_know": ["player_is_behind_building"]
    }
  },
  "scene_truth": ["alice_is_packing", "back_door_is_unlocked"],
  "allowed_revelations": ["alice_has_a_train_ticket"],
  "forbidden_revelations": ["core_secret_01"],
  "relationship_context": {"alice_trust": 42},
  "style": {"tone": "suspense", "dialogue_density": "low"}
}
```

Narrative 输出若需要一个未在 Packet 中允许的新核心事实，只能提出 clarification／proposal，不得自行加入正史。

### 10.13 Director WorkingContext 示例

```yaml
scenario_core:
  world_rules_ref: rules_v8
  dramatic_question: "Alice 是否值得信任？"
canonical_slice:
  location: apartment_backyard
  entities: [player, alice, back_door]
drama_state:
  phase_hint: escalation
  active_pressure_sources: [alice_departure]
  relevant_wishes: [wish_004]
arc_summary_ref: arc_001_summary_v6
recent_event_refs: [event_118, event_121, event_125, event_127]
retrieved_history_refs: [event_044, clue_009]
player_input_ref: input_128
jev_observation_ref: jev_obs_128
```

上下文构造器要记录每个片段的来源和 token 预算；“没有传给模型”不等于“系统遗忘”。

### 10.14 Dependency Fingerprint

缓存复用所需 fingerprint 以 Branch 的真实 read set 为基础，而不是仅哈希全局版本：

```yaml
dependencies:
  world:
    player.location: v22
    door.back.locked: v8
  characters:
    alice.visual_state: v17
    alice.knowledge: v11
  drama:
    active_arc: arc_001@7
    pressure.alice_departure: v3
  wish:
    wish_004: v2
  assets:
    alice_identity: sha256:...
    location_backyard: sha256:...
  provider_contract:
    h3_prompt_skill: v1.3
    video_profile: h3-max-reference-v2
```

任一实质依赖变化即 miss／invalidate；未声明依赖或 fingerprint 构造失败时采用保守 miss。


### 10.15 Character Asset System 数据契约

v0.6 新增以下一级实体。GlobalCharacter 是身份容器；CharacterVersion 是可复现版本；ScenarioCharacterSnapshot 才是 Scenario/Runtime 的稳定输入。

| 实体 | 最小字段 | 关键约束 |
|---|---|---|
| GlobalCharacter | id、name、bio、personality、tags、current_version_id、created_at、updated_at | 跨 Scenario；搜索字段与 UI 声明一致 |
| CharacterVersion | id、character_id、version、change_type、identity_spec、canonical_asset_refs、outfits、pose_refs、motion_refs、canonical_voice_ref、alternate_voice_refs、source_version_id、created_at | 发布后不可原地改写；重要资产变化产生新版本 |
| CharacterAsset | id、asset_id、character_version_id、role、status、outfit_id、source_asset_refs、generation_job_id、provenance | role 与状态分离；Edit 结果不覆盖 source |
| CharacterOutfit | id、name、description、reference_assets、is_default | 属于同一角色版本，可缺部分视图 |
| ScenarioCharacterSnapshot | id、scenario_version_id、global_character_id、character_version_id、frozen_identity、frozen_asset_refs、local_overrides、created_at | Runtime 只读 Snapshot；Global 新版不自动渗透 |
| CharacterVersionDiff | from_version、to_version、change_types、field_diffs、asset_diffs、breaking_identity_change | Creator 升级前必须可见 |
| CharacterReferenceSelection | scene_or_shot_id、character_snapshot_id、selected_image_refs、voice_ref、motion_ref、selection_reason、developer_override、provider_limits_snapshot | Production 实际发送什么必须可审计 |

CharacterAsset.status 使用 GENERATED / CANDIDATE / APPROVED / CANONICAL / ARCHIVED。CANONICAL 资产若被 Snapshot 或版本引用，不允许直接硬删除；先切换替代 Canonical，再归档旧资产。

CharacterVersion.change_type 至少包含 IDENTITY、APPEARANCE、METADATA、ASSET_ADDITION、VOICE。Identity-breaking change 必须在 UI 明示，例如更换主脸；新增 Outfit 通常属于非破坏性 Appearance/Asset 变化，但仍记录版本来源。

Image Generation / Edit 的所有任务复用 GenerationJob 与 Asset Registry，保存 provider、model、request_id、input refs、prompt hash、output refs、status、latency、错误与实际费用。前端不保存 FAL_KEY。

### 10.16 Creator Projection / Character Overlay / MechanicSpec / Player Presentation

为避免 Standard UI 与 Runtime Schema 耦合，增加“产品投影层”概念；它不是新的事实状态域，不能绕过 World/Drama/Character/Mechanic 的正式提交。

CreatorProjection 至少包含：AI 对用户原始故事的自然语言 summary、已确定项、待确认问题、每个问题的 contextual suggestions、用户自由修改，以及其对应的目标 typed path。建议项可以由 LLM 生成，但写入正式状态前仍走既有 Authoring patch/lock/validation。

Character 保持两层语义：
- GlobalCharacterCore：名字、一句话定义、基础人格、稳定身份资产及版本化默认值；
- ScenarioCharacterOverlay：本故事身份/作用、Desire、Fear、Secrets、Knowledge、Relationships、Visual State 与其他本地覆盖；最终由 ScenarioCharacterSnapshot 冻结。

MechanicAuthoringIntent 保存创作者对“怎么玩”的自然语言；MechanicSpec 是经过 Schema 校验的机器配置，引用 mechanic skill_id/version、enabled、typed config、trigger/visibility 及必要 StatePatch Contract。Runtime 只消费 MechanicSpec，不直接执行任意自然语言或用户 JSON。

PlayerPresentationState 区分至少 GENERATING_MEDIA / LOADING_MEDIA / PLAYING / WAITING_DECISION / FAILED_RECOVERABLE / ENDED，并输出 Standard-safe error_message 与 recovery_actions。raw exception、validation detail、provider diagnostics 只进入 Developer Trace。

## 11. Jev 与低成本剧情前瞻

### 11.1 正确分工

Jev 官方接口接受状态和类型化问题，返回 choice、score 或 yes/no 概率等判断；其 Choice 选项由调用方提供。[S05] 因此正确流程是：

```text
Director / Narrative 提供简短候选及假设后果
  → State 规则过滤不可行候选
  → Jev 对候选进行选择倾向、叙事价值或风险评估
  → Runtime 根据预算和队列选少量近端候选
  → Production 只为这些候选生成视频
```

这落实了 Q19“多用 Jev 预测，不用视频生成来试探未来”的想法。 **候选内容的生成、规则判断、玩家行为预测和媒体生成是不同问题** ；不能用一个“高概率”分数混在一起。

### 11.2 Jev 的任务清单

| 决策任务 | 问题定义 | 输入限制 | 失败／低置信路径 |
|---|---|---|---|
| 输入路由 | 行动、对话、Wish、问题、系统操作 | 使用明确 UI 通道作为强先验，减少不必要调用 | Director 或保守规则处理，不丢用户输入 |
| 机制触发 | 是否涉及关系、道具、线索等 | 结合已安装技能及其触发定义 | 交给相关技能进一步判断 |
| 候选排序 | 在当前玩家可见情境下哪些行动更可能被选择 | 候选集＋近期行为＋可见状态，保留 OTHER | 使用保守优先级，不伪造概率置信 |
| 轻量一致性 | 某个提案是否明显与给定事实矛盾 | 只能作为辅助审查，硬规则仍由代码校验 | State／Director 审查 |
| 升级决策 | 当前任务是否需要更强模型或补充上下文 | 结合模型信号和规则，不仅看一个阈值 | 升级、限次修复或明确失败 |

当前 Jev 文档说明输入是文本或结构化文本，不接收原始图片、音频、视频；中文等非英语任务的效果需要自行测试。[S06] 因此它不能独立充当视觉连续性检测器，也不能直接判断上传声音是否相同。媒体需要先经过可解释的文本化／感知模型，或由专用检测和人工验收完成。

### 11.3 “概率”不自动等于玩家真实选择频率

需要严格区分：`decision confidence`、`narrative quality score` 与 `player-choice propensity`。官方 confidence 是从答案分布得到的模型确定性信号，适合控制升级策略；它不是在本产品玩家群体上已经标定的行为模型。[S07]

MVP 可以使用 Jev 的分布作为启发式排名。只有收集实际选择、保留候选集及展示位置，并做留出验证后，才能把结果称作校准后的玩家选择概率。冷启动阶段界面与报告应标记“排序分数／未校准预测”，不展示虚构准确率。

`OTHER` 必须保留：它代表玩家可能自由输入未列出的行为。不得只把 Top-3 重新归一化成 100%，然后据此声称能覆盖所有选择。对中文双关、长句、多目标行动与否定表达要单独测试。

### 11.4 Session Player Preference State

MVP 不建立跨作品的长期“用户画像”，而是在每个 Session 内维护轻量偏好信号。它只使用 **玩家已经真实做出的选择** 作为证据，例如更常调查、冒险、社交或直接行动；具体特征维度应由 Scenario／产品定义，可版本化，不把模型对性格、身份或敏感属性的猜测写入其中。

`PlayerPreferenceState` 在正式行动提交后更新，保存 `evidence_event_refs` 和版本号。Jev 做候选排序时可以读取 `current visible state + recent events + preference signals + candidate set`，用于调整预取优先级；它不能因为偏好信号而判定一个本来非法的世界行为合法，也不能直接修改剧情事实。

偏好版本变化通常只影响 **下一轮候选排序与预算分配**，不自动使已经生成且语义仍有效的媒体失效。P1 才考虑跨 Session／跨 Scenario 的持久偏好，并在那之前单独评估账号绑定、隐私、删除和冷启动问题。

### 11.5 远期计划与近期视频的不同预算

建议维护两个窗口：`planning_horizon` 用于文本层滚动前瞻，`media_prefetch_depth=1` 用于最近一次决策的少量视频。前瞻候选采用有限束宽或总节点数预算，避免 3 个方向再各生 3 个方向形成无上限树展开。

多轮未来状态由简短规则和文本提案描述，Jev 批量评估， **并不调用 H3 试演这些未来** 。远期候选不预先写入正式事件；发生新的行动或愿望后可整体重规划。

### 11.6 版本与退化模式

测试通过后锁定 Jev 的版本 ID，日志记录实际返回模型版本；不要只依赖会移动的 `jev-latest` 别名。[S06] Jev 服务不可用时，可由 Director 做小候选集排序或采用保守预取，但必须标记 degraded mode。退化路径使产品可继续运行，不能替代比赛中 Jev 的真实接入验收。

### 11.7 Jev 在 Drama Control 中的新增职责

以下是 Q30、Q34、Q45 选择的**项目分工**，不是已经验证的 Jev 戏剧能力基准。继续使用现有 DecisionProvider，以版本化问题和有限候选表达任务。

| 新增判断 | Jev 快路径 | 必要的规则／LLM边界 |
|---|---|---|
| Action Significance | 在给定上下文中选择 LOW／MEDIUM／HIGH／UNCERTAIN | 已知关键物品、生死、公开秘密等硬触发可以直接升级，不能被低评分压下 |
| Desire／Strategy | 在候选解释中排序并给置信，允许 UNKNOWN／OTHER | 明确动机不被推断覆盖；低置信且高影响先澄清 |
| Pressure Relevance | 对已存在压力源的相关性排序 | 不创造未登记威胁，不直接修改世界时钟 |
| Commitment Observation | 对“是否形成承诺”等明确问题输出判断 | 不可逆承诺必须有行动／事件依据；复杂语义由 Director 解释 |
| Progress／Function Suggestion | 对已有候选功能、证据关联和价值等级做辅助评估 | 不用单分数替代完整 Beat 的证据，不直接写 Drama State |
| Escalation | 判断是否需补上下文或交给强模型 | 高影响反转、重大真相变更提案、结局判断不能仅因 confidence 高而跳过语义审查 |

Jev 的每次请求应带 task_id、问题版本、可用证据与允许输出，响应保留模型版本及是否为推断。候选生成仍由文本模型负责；长程原因解释、自然事件设计和 Director 结局判断不转嫁给 Jev。

### 11.8 置信、影响与语义评估不是一个分数

继续区分 `decision_confidence / choice_propensity / dramatic_value / factual_validity`。Q34 允许依赖 Jev 置信做 UX 分流，不意味着 0.9 就有 90% 概率读懂玩家真实动机；Q30 允许 Jev 做戏剧评价，也不意味着高分能通过反转或改变世界。

规则建议采用“影响优先于快路径收益”：明确且低风险可直接走；不确定且高影响先澄清／升级；置信高但涉及结局、生死、核心真相等重大决策仍遵循相应权限与审查。具体阈值由任务试用确定，不能照抄问答示例。

### 11.9 上下文与调用预算

快评使用当前 Action、少量最近事件、当前 Arc 摘要、必要 Ledger 条目及相关压力源，不默认给 Jev 塞完整历史。Director 的语义升级可以扩展证据范围；各字段保留引用以便检索，不把摘要本身当作唯一事实。

同一次 Action 的多个闭集问题可合并请求；已有规则或可靠结果可复用，避免为了“更多使用 Jev”重复调用。Drama Control 新增的延迟与费用纳入原预算、Trace 和 SM 指标，不得把节省的视频费用当作已经实现的收益。


### 11.10 Jev First Pass 的权威边界

自由输入首先可由 Jev 产出 `type / significance / desire / strategy / trigger / confidence` 等 observation，但 Director 的输入必须同时包含玩家原文。Jev 结果用于快速路由、上下文选择和升级，不得在进入 Director 前把原文压缩丢失。

对于推荐候选，Jev 排序发生在 Candidate Skeleton 形成之后；它负责选择／排序可生成的近端候选，不负责写 Narrative。Q59 的 Top-K 全并行只在 K 被最终锁定后生效。

## 12. 投机渲染、预算与缓存

### 12.1 调度目标

Q27 选择的是延迟—成本权衡。建议以最小化成本函数表达，而不是把二者相加后又称为“最大化效用”：

```text
minimize J = E[T_next_scene] + lambda * C_total
subject to:
  per-turn, per-session and provider budgets
  demand jobs have priority over speculative jobs
  normal speculative branch count K in {1, 2, 3}
  valid world / relevant drama / arc / wish / asset / scenario versions
```

`T_next_scene` 是玩家提交到下一幕首帧的时间，单位秒；`C_total` 统一用一种货币或已标定的资源成本，`lambda` 单位为秒／货币单位。仅做概念优化不意味着要引入复杂求解器；P0 可用明确可解释的贪心规则。分布未经行为校准时，`E[T]` 只能称为估计，不是实证期望。

### 12.2 正常调度与硬预算闸

正常开启投机时 K 为 1、2 或 3；选择依据包括候选排序、预计完成时间、`DecisionLeadWindow` 剩余时间、队列和预算。调度器选择 K 条后先在内部完成 StoryBeat、镜头生成、装配与版本校验，**推荐面板只有在待发布集合中的每条分支都达到 `READY` 后才允许原子发布**。如果在发布截止前预计无法完成，可以在发布前把 K 下调到 2 或 1；已经发布后不得用“还在生成”占位项冒充正常选项。

若预算耗尽、服务故障、没有合法候选或所有工作都影响更高优先级的当前请求， **禁止新投机任务** 。若此时没有可发布的 Ready 推荐集，可以暂不显示系统建议并保留自由输入，或进入短暂中性等待；不能为了满足“至少一个”而无限消费，也不能展示未 Ready 分支。

建议分别设置整局总预算、单轮预算、投机预算、单分支镜头预算、重试预算和供应商并发上限。用户未提供人民币金额，PRD 不凭空指定；部署配置必须填写，缺省使用保守限额而非无限制。

### 12.3 分支数 × 镜头数才是实际任务量

```text
new_video_jobs = sum(shots_for_each_speculative_branch)
                + uncached_demand_shots
                + permitted_retry_shots
```

例如 3 条候选分支、每条 2 个 Shot，已经是 6 个生成任务；这是计算示例，不是本项目已发起的任务。再加上参考素材编码、Prompt 扩展、重试和剪辑，不能把“Top-3”写成“每轮只付 3 个视频的钱”。

Q59 已选择 **Top-K 完全并行**：成本、配额和硬并发限制必须在锁定 K 前进入调度决策；一旦 K 被接受，K 条 Branch 同时启动 Narrative／Production／视频工作，不再故意先做 Top-1 再排队其他分支。关键镜头若依赖前一镜头输出，仍可在该 Branch 内部串行；“分支并行”不等于破坏镜头连续性。若 Provider 无法同时承载 K 条，应在锁 K 前降低 K，并记录 `target_k / effective_k / reason`。

### 12.4 命中定义

| 类型 | 定义 | 玩家体验 | 指标处理 |
|---|---|---|---|
| Ready hit | 语义等价且所有必要媒体已装配可播放，版本有效 | 无新增生成等待，但仍有校验、网络和解码耗时 | 计入完整就绪命中 |
| In-flight hit | 自由输入与某个内部候选语义匹配，但该候选仍在生成／装配 | 仍显示加载动画，等待剩余工作 | 不计入“立即播放”命中；正常系统推荐不允许以此状态展示 |
| Miss | 没有等价有效分支 | 提交当前行动生成任务 | 按 Q18 C 显示加载动画 |
| Invalidated hit | 内容曾命中，但状态／Wish／资产变化使其失效 | 不能复用错误剧情 | 计入失效，不包装成成功缓存 |

缓存复用必须保持意图等价。例如“我离开”与“我假装离开并观察”不是同一行动，不能为了节省成本而合并。对语义等价性不确定时优先 miss。

按 I05，**系统推荐按钮被玩家看到时应天然满足 Ready hit 条件**。因此“点击一个已经显示的系统推荐却得到 In-flight hit”应视为 Ready Gate 或版本同步缺陷，而不是正常产品状态。自由输入仍可命中内部在途候选，因此 In-flight hit 类型保留。

### 12.5 缓存键与生命周期

建议缓存键至少含：`session / scenario_version / arc_id / arc_revision / base_state_version / relevant_drama_revision / wish_version / normalized_intent_and_material_desire / story_plan_revision / skill_versions / asset_hashes / provider_profile / generation_parameters`。只有会实质改变后果的 Desire／Strategy 差异才参与语义等价性；不确定时优先不复用。媒体记录保留 seed 与请求哈希；相同 seed 不承诺跨后端得到相同视频。

Q66–Q67 已将目标契约锁定为 **短生命周期 Branch Cache + Dependency Fingerprint**。首版实现可以在 fingerprint 生成不完整时保守整版本失效，但不能把“粗粒度版本失效”当最终语义。未选 Branch 的媒体与 Proposal 只在 TTL／当前 Arc 等限定范围暂存；复用前确定性检查 read set、World／Character／Drama／Wish／Asset／Provider Contract 等依赖。跨玩家共享私有角色／音色素材缓存默认禁用；通用预设素材另行授权。

### 12.6 优先级、取消与持久化

当前玩家明确选择的任务高于任何预测任务。若供应商只支持提交后等待，调度器能做的是在提交前保留名额、取消尚未发出的工作、在任务结束后换优先级， **不能假设已经运行的视频任务可以零代价抢占** 。

所有外部付费请求先登记并预留预算，保存供应商任务 ID。网络超时且不确定任务是否已创建时先查状态或对账，不直接盲目重发；一次请求的幂等性不能靠本地函数名保证。

### 12.7 本地吞吐的现实边界

预生成可以利用观看和思考时间，但不能凭空提高设备吞吐。以官方约 56 秒热态生成一条 5 秒视频作为说明，假设单任务串行，预生成三条至少需要约 168 秒，尚不包括每分支多个镜头。[S04]  **此处是基于串行假设的算术推导，不是三任务实测。**

因此单 Spark 本地模式不能仅凭 Top-K 就保证连续“看 5 秒、立即看下一段”的体验。这也是 Q26 选择云端主互动、本地真实任务独立展示的合理边界。缓存命中率与可持续吞吐应分别报告。

### 12.8 Drama Control 与 Ready Gate 的组合规则

**I05 不变。** 正常剧情推荐面板发布的每个选项都必须有完整 Ready SceneArtifact；发布前已经完成必要的意图解释、候选戏剧评估、事实预校验与装配。点击后只做轻量版本／前置条件校验及提交，不能因为加了 Drama Control 又重新进行长链编剧。

Q36 的 QUICK_ACK／MERGED_TRANSITION 不放宽这个约束。它们服务于玩家自主输入的小动作和独立机制操作；不能把只有文本反馈的候选混入 Ready 视频推荐，伪称“文本 Ready 也满足原承诺”。低戏剧价值候选宜不进入付费预生成队列，重新选择有实质不同策略与足够价值的近端候选，数量仍由 Top-K／预算决定。

每个候选同时保存 projected World／Drama 快照，只有正式选择并通过检查后才能提交。真实行动、有效 Wish、Arc 切换、真相或相关 Directive 改变时，撤回受影响的推荐集合并重建；不借缓存成本把玩家拉回旧剧情。

`DecisionLeadWindow` 的公共尾段仍必须分支无关，推荐文本只能引用玩家当时已知信息。建议使用 `recommendation_epoch` 绑定该决策点的输入快照与冻结的候选计划：常规 Beat 后评估若只更新置信／排序、不改变合法后果，可保留有效候选；若改变实质前提，应刷新集合。保守整版本失效可作为首版实现，但必须记录额外等待与浪费，不能声称始终零等待。

Arc 已关闭时立即停止为旧 Arc 投递新候选；未选未来不转移为下一 Arc 的事实或戏剧债务。续杯只继承正式历史与明确承接的未结项，重新建立新 Arc 的候选与预算检查。

### 12.9 Ready Branch 的发布与失败降 K

Top-K 生成过程中，每条 Branch 有独立失败域。若某条在 Narrative、Production、Video 或 Assembly 阶段出现可重试暂时错误，按 Q63 **快速重试一次**；仍失败则该 Branch 标记 `FAILED` 并从当前推荐集合移除。其余 READY Branch 可作为 K-1 集合原子发布，不继续等待失败项无限重试。

`effective_k`、失败阶段、retry 次数和是否因错误降 K 必须写 trace。若 K-1=0，则保留自由输入并进入真实错误／等待恢复路径；不能显示一个未 Ready 的“占位推荐”。

### 12.10 Two-Phase Canonicalization 与下一轮预取

`SELECTED` 代表玩家已选中 Branch，但正式媒体呈现和 Canonical commit 尚未确认。Runtime 建立 provisional view，使 Director 可以在 N+1 视频开始播放前规划 N+2；该 view 不能写入正式 Event Log、Foreshadow、Wish 状态或玩家知识。

SceneArtifact 校验通过并确认可播放后，World／Drama／Event Log 原子提交并把 Branch 置为 `CANONICAL`。失败则回滚 provisional view，取消依赖它且尚未发出的 N+2 投机任务；已经发出的付费任务按预算／Provider 能力处理并标记 orphaned，不得当成正式剧情。

### 12.11 Branch Cache 生命周期

未选择的 READY Branch 进入 `STALE_CANDIDATE`／缓存态，保留到 TTL、Arc 关闭、依赖失效、素材撤回或存储策略触发。它们可以复用媒体工件，但不能继承为新 Arc 的事实。

缓存命中需要同时满足意图等价和 Dependency Fingerprint 兼容。LLM 可以帮助生成候选映射，但最终复用判定必须由确定性依赖校验完成；不确定时 miss。

### 12.12 Provider Router 与投机任务的关系

Router 对每个 Branch 记录实际 Provider 路径。例如 Narrative 从 Step 3.7 fallback 到 Lightning、Production 从 Lightning fallback 到 Step 3.7，都不会改变 Branch ID，但会改变 provenance 与性能数据。Provider fallback 后仍须满足同一 Schema、ScenePacket 与状态权限。

视频后端 H3 Max／Sol-H3 是显式 Provider 选择，不自动视为彼此透明的错误 fallback；Q26 的现场本地视频展示和 Q68 的 Profile 切换仍是明确操作。

## 13. 多模态素材与视频生产链路

### 13.1 三类素材的“完整支持”定义

Q25 A 不等于做一个大型资产管理产品，但必须做到下面的真实链路：`上传 → 验证 → 预览／裁选 → 角色或场景绑定 → 用途定义 → Provider 参考输入 → 生成 → 成片检查 → 来源记录`。

| 素材 | 应表达的用途 | P0 必需处理 | 验收证据 |
|---|---|---|---|
| 图片 | 人物身份、服装、场景、风格或关键帧 | 格式／尺寸验证、预览、角色与用途绑定 | 请求引用的确切资产哈希＋生成结果 |
| 声音 | 指定角色的声音参考，或明确的声音风格 | 格式／时长验证、试听、说话人和用途绑定 | 音频输入实际送达后端；听取输出是否符合参考目标 |
| 视频 | 动作、镜头、人物、场景或风格参考 | 探测编码／时长、简单裁选或要求合法片段、预览与用途绑定 | 选定参考区间与真实请求字段、成片对应目标 |

参考音频不等于已训练专属音色模型，也不保证每次产生完全相同的声音。视频参考不等于精确动作捕捉。本产品必须真实利用参考输入，同时如实说明模型对内容遵循的误差。

### 13.2 已核对的云端接口能力

MiniMax 当前视频文档列出 H3 Max 的文生、图生与全能参考入口，支持图片、音频和视频参考；fal 的 H3 Max reference-to-video 接口也提供对应参考数组。[S02][S03] 这为 Q25 A 提供了可行接入路径，不需要把音视频降级成以后再做。

素材上限与格式必须由 adapter 从固定版本配置中校验。当前 MiniMax 文档给出的全能参考限制包括图片最多 9 张、视频和音频分别最多 3 段、混合最多 12 个文件，视频／音频参考有时长限制。[S02]  **这些供应商规则不是本平台永久常数** ；实现时保存能力快照，升级后回归测试。不同入口和不同供应商的限制不能混用。

### 13.3 Asset Registry

建议记录：`asset_id / version / content_hash / owner / media_type / mime / duration / dimensions / source / consent_scope / bound_entity / reference_role / storage_uri / provider_upload_ref / expiry`。

原始素材保留本地受控副本；需要云端消费时，生成短期可访问链接或通过供应商上传通道传送。仅存在于 Spark 内网的文件路径不能直接填进云端 API 的 URL 字段。默认不把私人图片和声音放进公共永久链接。

AI 应解释素材用途，而不是替用户擅自改变人物身份。P0 可以让用户手工绑定角色并由 AI 补充建议；不必先实现高精度自动人脸识别或声纹识别。

### 13.4 Prompt 与参考编译

Production Agent 先生成镜头计划，再由连续性 Skill 读取稳定身份、当下服装／持物／伤痕／天气与上一镜头，形成参考映射和不能变化的条件。每份外部请求保存内部资产 ID 到供应商标签的映射，避免图片顺序变化后人物指代错位。

官方 H3 Prompt Skill 已有基础模式和全参考模式的编写规则，应复用并锁定来源版本，而不是把“会写 H3 提示词”独占地当成自有创新。[S10] 本项目新增的是意图、状态、剧情、镜头、素材和预算之间的编译契约。

fal 接口提供不同 Prompt 扩展模式，其中更高质量扩展可能引入额外耗时。[S03] 建议避免应用内重写与供应商深度重写重复执行；在结构化提示词已通过测试时优先评估关闭扩展，在需要模型补全时再选择相应模式。不得只根据宣传中的 3 秒估算带深度扩展的请求。

### 13.5 视频模式与镜头连续性

建议按条件选择模式，而不是所有镜头都用同一种接口：有上一镜头结尾时可评估首帧／首尾帧续接；需要维持多个角色和声音时可使用全能参考；无需身份条件的环境镜头可用文生视频。具体组合由该 profile 的能力矩阵决定。

同一 Beat 的 Shot 可并行与否，取决于是否需要前镜头输出作条件。默认建议每 Beat 1–2 Shot、关键节点最多 3 Shot，镜头常用 5 秒，复杂动作可用 10 秒或后端允许的时长；这些是可调的工程默认，不是用户要求所有视频固定 5 秒。

### 13.6 自动装配

`video-assembly` 负责按剧情顺序组织片段、必要的裁切、规格统一、转场、音量与音轨、字幕和最终输出。FFmpeg 提供相关媒体过滤和拼接基础能力，本项目需封装参数、验证与错误处理。[S17]

跨镜头的音频与对白必须有计划：不要把带完整音乐和对白的片段硬拼后让声音突然重叠。建议先使用保守切换、对白间隙与短音频淡化；不得剪掉关键台词。原生音频与计划台词不一致时，不能继续烧录看似精确的计划字幕；应标记检查失败、限次重生成，或使用经过确认的转写。

输出必须包含媒体工件清单、规格、素材来源、生成 profile 和对应 Story Beat。若只有一个 Shot，装配仍执行验证和封装，但不能为展示剪辑能力而伪造“合并了三段”。演示中另选一个真正的多 Shot Beat 证明拼接。

### 13.7 质量门与失败策略

P0 必需技术检查：能解码、非空、时长与规格合法、音轨符合请求、镜头顺序正确、分支一致、资产与请求可追溯。连续性 Skill 的输入规划是 P0；自动视觉检查器是建议增强，不能拿 Jev 直接替代视觉模型。

建议将输出问题分成：关键身份／事件错乱、显著连续性错误、轻微视觉瑕疵。前两者若被检测到应阻止自动提交或限次重试；轻微瑕疵可带警告展示。没有启用自动语义检查时必须标 `semantic_check=not_run`，由测试样本的人审证明质量，不得宣称每段视频都通过自动一致性验证。


### 13.8 Character Asset Studio → Production Reference Resolver

v0.6 将角色资产加入三模态生产链：

角色描述/上传图 → Nano Banana 2 生图或 Edit → Candidate → 用户批准 → CharacterVersion Canonical Pack → ScenarioCharacterSnapshot → Reference Resolver → h3-production → H3 Adapter。

AI 创建默认用 fal-ai/nano-banana-2 生成 2 张候选；用户选择一张主身份图后，可二次确认生成标准多视图。编辑使用 fal-ai/nano-banana-2/edit，并可输入一个或多个 reference image URL；Adapter 负责把受控本地资产上传或转换成供应商可读取 URL。fal 官方当前文档支持多 image_urls，具体上限、格式和能力按调用时固定的 Provider capability snapshot 校验，而不是写死在 UI。[S26][S27]

Reference Resolver 不把角色全部资产塞进 H3。它根据当前 Scene/Shot、角色 Outfit、Pose/Motion、镜头景别与 Provider 上限，为每个角色选择最相关参考；普通目标为 2–4 张角色图片，再附必要 Voice/Motion。多角色场景先独立构造每个角色的 pack，再按总上限裁剪；裁剪必须可解释并记录，不能静默丢掉主身份参考。

角色表情不是长期预生成资产库。诸如“紧张地笑”“哭着压低声音”属于 ScenePacket / Production Prompt 条件；若某镜头确实需要先得到静态表情参考，可临时通过 IMAGE_EDIT 生成 Derived Candidate，但除非用户批准，不自动晋升为 Canonical。

## 14. 技术选型与部署建议

### 14.1 选型结论

 **建议采用轻量、显式的工作流工程栈，而不是叠加多个全能 Agent 框架。** 工作流的可恢复执行状态不是故事的固定阶段状态机；Q31 仍要求柔性戏剧阶段。 建议主栈：React／TypeScript 前端，Python／FastAPI 后端，Pydantic 数据契约，LangGraph 或小型显式状态机编排，PostgreSQL 作为权威状态与任务记录，独立视频 worker，FFmpeg 装配，结构化 trace。各项都是本次建议，不是用户已选定的库版本。

| 层 | 建议选型 | 选择理由与代价 | 备选／边界 |
|---|---|---|---|
| Web UI | React + TypeScript，轻量构建工具 | 方便组合播放器、表单和状态面板；需要维护前后端契约 [S19] | 不要求 Next.js 全栈或原生 App |
| API | Python + FastAPI | 与模型服务和异步任务集成直接，接口可统一描述 [S15] | 长视频任务不挂在 HTTP 请求生命周期 |
| Schema | Pydantic + 导出的 JSON Schema | 对模型输出和外部请求做显式验证 [S16] | 强类型不等于语义正确，还要领域规则 |
| 编排 | LangGraph，或少量明确节点的自有状态机 | 支持有状态、可恢复的工作流组织；便于混合确定步骤与模型步骤 [S13] | 只选一个主编排器，避免框架套框架 |
| NVIDIA 工具 | NeMo Agent Toolkit 作为可选可观测／集成层 | 其官方文档覆盖工作流、观测、评估和 LangGraph 集成 [S14] | 非用户已确认必做；规则未强制时不为品牌堆依赖 |
| 权威存储 | PostgreSQL，事务＋唯一约束＋版本校验 | 状态、事件和 outbox 可以原子提交 [S22] | 初期不需要专门图数据库或向量数据库 |
| 媒体／任务 | 独立 worker + 持久化 job 表 | 能恢复任务、限并发、记录账单和输出 | Redis／专门消息队列到压力证据出现后再引入 |
| 资产 | 本地受控文件存储 + 供应商上传／短期 URL | 便于单机落地和校验真实引用 | 不把内网路径当公网可读 URL；S3 兼容存储可后加 |
| 日志 | JSONL／数据库 trace，OpenTelemetry 字段约定 | 能把一个输入关联到 Agent、Skill、API 与媒体工件 [S18] | 无需先建设大型监控平台 |
| 视频后处理 | FFmpeg／ffprobe | 单一媒体处理链，便于记录命令和检查 [S17] | 不默认镜头规格可直接无损拼接 |
| 部署 | Docker Compose 等简单服务编排 | 单 Spark／单节点易复现，职责分离 | 镜像需匹配 ARM64／GB10；不默认桌面 CUDA 镜像可直接运行 [S11] |

选择 LangGraph 不意味着其 checkpoint 就是整个游戏的唯一事实库；Canonical State、媒体任务账本和技能执行工件仍由本项目明确持久化。重放图节点也不应该重复触发付费视频任务。

**v0.4 的最小增量实现建议：** 在现有 Python Runtime 内新增 Drama State Manager、评估／Directive 节点和结构化表；与 World State 共用事务与 outbox；现有 Director／State 模型服务复用，不再增加一份常驻权重。Ledger 可以先存为带 Schema 和事件引用的结构化记录，不需要为“戏剧图谱”引入新图数据库。

这些是 PROPOSED 的落地方式；验收重点是权限、因果、版本和可恢复性，不是部署了多少个服务。

### 14.2 v0.6 已冻结的模型与 Provider 选择

Q49–Q70 已把主要文本/视频模型从“候选建议”升级为 USER 决策；v0.6 进一步把角色 Image Generation / Image Edit 锁定到 fal.ai Nano Banana 2。除非后续用户再次修改，实施不得自行换掉主模型后仍称满足同一基线。

| 任务 | Primary | Fallback | 部署 | 状态与验证要求 |
|---|---|---|---|---|
| Director | `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` | Step 5 Preview API | DGX Spark 本地 → API | **用户已锁定**；需测中文玩家输入、Drama 规划、JSON／tool schema、长局上下文 |
| State Manager | 确定性代码 | — | 本地 | 版本、事务、幂等、权限不交给模型 |
| State semantic parsing | 复用 Lightning | 高影响时可走 Director fallback 链 | 本地／API | 输出 Proposal／Observation，不直写 State |
| Drama Control | Rules + Jev + Director | 随 Director 路由 | 混合 | 无第五个常驻模型 |
| Narrative | Step 3.7 Flash API | Lightning local（Profile 可用时） | API → 本地 | **用户已固定**；验证中文对白、ScenePacket 遵循、禁泄密 |
| Scenario Authoring | Step 5 Preview API | 未冻结 | API | **用户已固定**；低频、高质量优先 |
| Production | Lightning local + `h3-production` Skill | Step 3.7 Flash API | 本地 → API | 验证 H3 参数、参考映射与输出 Schema |
| Fast Decision | Jev API | 未冻结 | API | 中文 closed-set、confidence、Top-K 排序 |
| Cloud Video | H3 Max API | 不把 Sol-H3 当透明自动 fallback | API | 主互动路径 |
| Local Video | Sol-H3 | — | DGX Spark | 显式 VIDEO_LOCAL_PROFILE、真实任务证据 |
| Image Generation | fal.ai fal-ai/nano-banana-2 | 未冻结 | API | 角色 AI 创建与标准参考图；默认 2 候选；真实 request/artifact 可追踪 |
| Image Edit | fal.ai fal-ai/nano-banana-2/edit | 未冻结 | API | 换装/背景/姿势/视角/自由编辑；结果非破坏式 Candidate |
| Assembly | FFmpeg／程序 | — | 本地 | 确定性媒体链 |

NVIDIA 当前 Model Card 将 Nemotron 3.5 Lightning 标为 30B 总参数／3B active、最长 1M context，并定位于 long-running agents／agentic workflows。[S23] NVIDIA 当前单 DGX Spark 的实验 vLLM profile 明确支持该 NVFP4 checkpoint；其验证 profile 使用 65,536-token context、单并发序列，并在特定 32K–42K 输入测试中报告后续请求平均约 102 output tok/s。[S24] **这些是 NVIDIA 特定 profile 的公开验证，不是本项目 Director 的 SLA，也不证明中文剧情规划质量。**

Nemotron 3.5 Lightning 的官方主支持语言列表没有把中文列为正式主支持语言，因此本项目仍必须用中文剧情／规划 case 实测，不得因模型已锁定而跳过 G03。[S23] Step 3.7 Flash 与 Step 5 Preview 的 API 可用性、账号权限、配额和实际模型 ID 也要在提交前锁定。[S08][S21][S25]


### 14.2.1 v0.6 Image Router

Image Router 与 Text Provider Router / Video Provider 在类型上分离，但共享统一的 health、timeout、retry、trace、usage、artifact provenance 语义。业务层只允许调用 IMAGE_GENERATION 和 IMAGE_EDIT 两个逻辑能力。

当前固定路由：

- IMAGE_GENERATION → fal.ai → fal-ai/nano-banana-2
- IMAGE_EDIT → fal.ai → fal-ai/nano-banana-2/edit

fal 官方当前 API 文档确认 text-to-image endpoint 支持批量 num_images，Edit endpoint 支持 image_urls 多图输入；文件可以通过可访问 URL、data URI 或 fal storage 传递。[S26][S27] 实现时 FAL_KEY 只能留在服务端，不得下发浏览器。模型价格、最大输入数、分辨率等易变化信息不得硬编码成永久产品文案。

Image Router 输出统一 GenerationJob / CharacterAsset 工件；失败不能自动覆盖原资产。若未来切换模型，只替换 Adapter 与 capability snapshot，并重新运行 Character Consistency / Edit Preservation 验收。

### 14.3 DGX Spark 资源与双 Runtime Profile

DGX Spark 为统一内存架构；Sol-H3 的官方 Spark 配方曾给出接近整机可用内存的占用口径，因此 v0.5 **不允许把 Lightning + Sol-H3 同时常驻当作默认架构**。[S04][S11] Q53、Q68 已选择显式服务级 Profile：

| Profile | Spark 本地服务 | 云端文本路由 | 用途 | 关键限制 |
|---|---|---|---|---|
| `AGENT_LOCAL_PROFILE` | Lightning、State／Drama Runtime、Production、FFmpeg | Jev、Step 3.7 Narrative、Step 5 Authoring／Director fallback、H3 Max | 主交互与 Agent Skills 演示 | Sol-H3 不常驻 |
| `VIDEO_LOCAL_PROFILE` | Sol-H3、轻量 State／Runtime、FFmpeg | Jev、Step 3.7 Narrative／Production、Step 5 Director fallback | 本地视频生成展示 | Lightning 已卸载；Narrative 的本地 fallback 不可用 |

切换必须执行：`stop accepting new local jobs → drain → persist → shutdown serving process → release resources → launch target service → health check → Provider Router atomic switch`。模型加载／卸载、冷启动、失败恢复都单独计时，不藏进视频热态生成数字。

若未来获得第二台 Spark，可把 Agent 与 Video profile 拆到不同节点，但这属于部署扩展，不改变 Provider／Branch 契约。单机共驻只有在真实峰值内存、KV、应用服务和稳定性测试通过后才允许宣传。

### 14.4 v0.6 Provider Router 配置示例（内部配置，不是供应商请求体）

```yaml
profile: AGENT_LOCAL_PROFILE

providers:
  jev:
    type: decision
    adapter: typesafe
    model: PIN_JEV_VERSION

  nemotron_local:
    type: text
    adapter: openai_compatible_local
    model: nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
    base_url_env: LOCAL_LLM_BASE_URL

  step_37:
    type: text
    adapter: stepfun_chat
    model: step-3.7-flash
    api_key_env: STEP_API_KEY

  step_5:
    type: text
    adapter: stepfun_chat
    model: PIN_STEP_5_PREVIEW_MODEL_ID
    api_key_env: STEP_API_KEY

  h3_max:
    type: video
    adapter: h3_max
    credentials_env: H3_API_KEY

  sol_h3_local:
    type: video
    adapter: sol_h3_spark
    profile_ref: profiles/sol_h3_spark.lock.yaml

routes:
  director:
    primary: nemotron_local
    fallbacks: [step_5]
  narrative:
    primary: step_37
    fallbacks: [nemotron_local]
  production:
    primary: nemotron_local
    fallbacks: [step_37]
  authoring:
    primary: step_5
    fallbacks: []
  decision:
    primary: jev
  cloud_video:
    primary: h3_max
  local_video:
    primary: sol_h3_local

profile_constraints:
  AGENT_LOCAL_PROFILE:
    available: [nemotron_local, jev, step_37, step_5, h3_max]
    unavailable: [sol_h3_local]
  VIDEO_LOCAL_PROFILE:
    available: [sol_h3_local, jev, step_37, step_5, h3_max]
    unavailable: [nemotron_local]

speculation:
  normal_max_branches: 3
  launch_selected_k_in_parallel: true
  media_prefetch_depth: 1

retry_policy:
  speculative_branch_fast_retry: 1
  publish_k_minus_one_after_retry_failure: true

cache:
  branch_ttl_required: true
  dependency_fingerprint_required: true
```

启动时必须解析当前 Profile 的真实可用 Provider；例如 `VIDEO_LOCAL_PROFILE` 中 Narrative 配置虽写有 `nemotron_local` fallback，Router 也必须识别其不可用，不能等到请求时才假装本地服务存在。`PIN_*` 占位必须在启动校验时失败。

### 14.5 先验证再扩展的技术门

| Gate | 验证对象 | 通过条件 | 未通过时行动 |
|---|---|---|---|
| G01 | H3 Max API 权限与三类参考 | 图、声、视频独立及混合请求有真实任务与成片 | 换已支持的供应商／修适配器；不得删掉 Q25 |
| G02 | Jev 中文决策 | 小型固定测试集有可解释路由和升级，失败不阻塞主链 | 调整问题／上下文或使用保守 fallback，记录限制 |
| G03 | Nemotron 3.5 Lightning 本地 Director | 中文自由输入理解、Drama／Rolling Plan、结构化输出、内存与长局上下文达到可用水平；保存真实 DGX Spark 配置 | 先修 Prompt／Context／serving；若仍失败标主模型阻塞并按已选 Step 5 fallback 运行，不私自换主模型 |
| G04 | Sol-H3 单独运行 | 固定配置至少完成真实视频任务，保存环境与输出 | 修复环境；未完成就标本地后端未验收 |
| G05 | Runtime Profile 切换 | AGENT↔VIDEO 完整 drain／持久化／服务重启／health／Router 切换，无 OOM、无丢任务、fallback 集正确更新 | 保持可恢复旧 Profile；不宣称模型同驻 |
| G06 | 状态与缓存一致性 | 过期 Proposal、重复回调、Wish 更新不产生错误世界 | 修 Runtime，不让 LLM 自己解释掉故障 |
| G07 | 全链路体验 | Creator 到当前 Arc 结局及主动续杯闭环，至少一个关键 free-form miss 与一个 ready hit | 找瓶颈；不得只用按钮缓存 Demo 替代 |
| G08 | 戏剧与双域正确性 | 小动作分流、因果压力、伏笔／反转、结局权限和新 Arc 继承符合契约 | 修状态与规划，不以自动戏剧分数掩盖错误 |
| G09 | 玩家体验反馈 | 真实玩家完成可用范围试玩，反馈有来源、具体片段及问题记录 | 无反馈标未评估，负反馈形成修改项，不宣称戏剧性已提升 |
| G10 | Provider Router 容错 | 注入 Step 3.7 timeout、Lightning 不健康、Step 5 failure，route／retry／circuit breaker 与 provenance 符合 Q64–Q70 | 修 Router；不得把 fallback 后结果继续标 primary／local |
| G11 | BranchContract／两阶段提交 | Ready 点击不重推理；SELECTED provisional 可预取 N+2；播放失败能回滚且不污染 Canonical | 修事务／取消；不以“最终看起来对”掩盖中间污染 |
| G12 | Top-K 全并行与失败降 K | 锁 K 后 K 条真实并发启动；单分支失败一次重试后能 K-1 发布，其他 Ready 不被拖死 | 调整锁 K 前的并发／配额判断，不改回选后串行 |
| G13 | Branch Cache Fingerprint | 有效依赖不变可复用，相关依赖变化必须失效，未声明依赖保守 miss | 补 read set／fingerprint，不让 LLM 猜缓存兼容 |

所有 Gate 在本次文档交付时均为 **未实测** 。公开文档的存在只使相应路线具备尝试依据。

### 14.6 Provider Router 语义

Provider Router 是基础设施层，不是新的 Agent。它按 role、当前 Runtime Profile、health、错误分类和已冻结 fallback 顺序选择 Provider，并产生 `ProviderRouteEvent`。至少支持：

- health／readiness cache；
- per-provider timeout；
- Q63 指定的投机分支快速重试一次；
- circuit breaker；
- role-specific fallback；
- Profile 约束；
- trace／cost／model-version tagging。

永久业务错误、内容策略拒绝、Schema 本身非法不能靠切模型无限重试。fallback 必须重用同一输入／输出契约，并把模型差异暴露给质量日志。

### 14.7 Profile 切换状态机

建议的 RuntimeProfile 状态：

```text
ACTIVE
  → DRAINING
  → STOPPING
  → STARTING_TARGET
  → HEALTH_CHECK
  → ACTIVE(target)
      ↘ FAILED_RECOVERABLE → RESTORE_PREVIOUS
      ↘ FAILED_BLOCKED
```

切换过程中前端应显示“本地后端切换中”，但云端文本路径是否继续取决于 Router 可用性。State／Drama／Session 存储不随模型进程销毁。

### 14.8 当前未解决的 fallback 缺口

`VIDEO_LOCAL_PROFILE` 中 `nemotron_local` 被显式标记不可用，因此 Q64 的 Narrative fallback 链只有 primary Step 3.7 可用。如果此时 Step 3.7 同时失败，v0.5 **没有用户确认的第二 Narrative emergency fallback**。实现可选择阻止切换、暂停 Narrative 或后续再确认新的回退，但不能擅自把 Step 5 加入 Narrative fallback 并称为已冻结需求。


### 14.9 v0.6 模型部署真实性门

封版时不得通过读取 .env、README 或 Provider registry 判断“模型已部署”。至少保存以下真实证据：

- DGX Spark / 本地节点：nvidia-smi 或等价硬件/内存状态、实际服务进程、监听端口、health。
- Nemotron Director：实际 /v1/models 或服务模型标识、一次中文 Director 请求、结构化输出、冷/热延迟、内存占用。
- Step 3.7 / Step 5：真实 API 返回的模型标识、schema 兼容、成功与失败请求。
- Jev：真实闭集任务、confidence/clarification 结果和版本。
- H3 Max：至少 text、image reference、audio reference、video reference、mixed reference 的真实请求证据。
- Sol-H3：真实 submit/status/output，本地节点、模型/config、分辨率、推理与 decode 时间。
- Profile switch：AGENT_LOCAL→VIDEO_LOCAL→AGENT_LOCAL 的真实 drain/persist/stop/release/start/health/router switch，失败可恢复旧 Profile。

Developer 面板显示的 provider/model/profile 只能来自实际 RouteEvent / Job，不允许由前端常量伪造。

## 15. 非功能需求、权限与可靠性

### 15.1 可靠性

会话、Arc、输入、任务、World／Drama 状态补丁和媒体工件均有稳定 ID。前端刷新、worker 重启、供应商重复回调不能重复推进剧情。外部任务状态须持久化，不能只存在进程内变量。生成失败保持上个有效决策点，已提交 Scene 可恢复播放。

建议区分错误类别：用户素材不合法、后端能力不支持、内容限制、网络／限流、生成失败、装配失败、World／Drama 版本冲突、证据引用缺失、结局／续杯状态冲突。永久错误不自动重试；暂时错误采用有上限退避；涉及新费用时遵守预算。降级模式必须可见，不能将本地失败后自动转云端的结果仍标为“本地”。


Provider Router 进一步把错误分为 `retryable_transient / provider_unhealthy / schema_failure / permanent_request_error / policy_rejection / profile_unavailable`。Narrative 的 Step 3.7 暂时错误可回退 Lightning（仅其 Profile 可用时）；Director 的 Lightning 失败回退 Step 5；Production 的 Lightning 失败回退 Step 3.7。每次 fallback 都必须保存 `primary_error` 与最终 provider。

Top-K 某一分支的快速重试次数按 Q63 固定为 1；第二次失败进入 K-1 发布，不将整个推荐集合置为失败。该规则只适用于投机分支暂时错误，不代表任何外部 API 都可以无条件重试一次。

### 15.2 安全与素材权限

Creator 和 Player 权限分开。剧情文本、用户行动和上传文件中的文字都是业务数据，不能覆盖系统权限、泄露密钥或让模型调用任意 shell。Scenario 硬规则不可由 Player 直接修改；Wish 只能使用独立偏好通道。

人物图像、声音和视频应记录来源及使用授权范围；涉及真实人物声音或形象时要求明确授权，提供删除与撤回使用的入口。生成内容应有合适的 AI 生成说明。这里是产品风险控制建议，不代表完成特定法域的法律审查。

外部 API 仅传送执行所需的数据。混合部署仍可能把剧情、参考素材或状态摘要发送到外部服务，不能只因使用 DGX Spark 就宣传“所有数据不出设备”。开发者日志默认脱敏，密钥仅从服务器环境／秘密存储读取。

### 15.3 媒体和技能安全

上传验证真实格式、大小、时长与解码结果；不只信任文件扩展名。限制转码资源、清理临时文件，防止超大视频耗尽统一内存。P0 建议不开放任意远程 URL 导入；确需导入时要防止访问内网地址与敏感服务。

技能脚本限工具、目录和运行时长；未审核包不得获得网络、数据库或任意命令权限。UI 主题只允许受控配置，不能让创作者注入任意脚本。

### 15.4 可观测性

一个 `trace_id` 串起玩家输入、Jev 问题与版本、Action／Desire 理解、DramaObservation、Directive、Arc、Agent 产物、Skill 指令版本、工具调用、双域状态提案、Provider job、装配文件与最终呈现。使用父子 span 或类似结构，能回答“这段视频为什么生成、使用了谁的素材、耗了多少、改变了什么”。OpenTelemetry 的 trace／span 概念可以作为组织方式。[S18]

v0.5 还要求记录 `BranchContract / provider route / runtime profile / model version / context token counts / cache fingerprint / SELECTED→CANONICAL` 状态转换。Q62 不设性能 SLA，但没有这些时序数据也不能声称“后续再优化”。

开发者面板不把未执行的预测伪装成真实调用，也不预填成功率与节省金额。需要样例日志演示 UI 时必须明显标为 SAMPLE，不能混入真实指标。

## 16. 指标定义与测量口径

### 16.1 产品指标

| 指标 ID | 名称 | 定义与分母 | 需要分组 |
|---|---|---|---|
| PM-01 | 下一幕等待时间 | 从玩家确认提交到下一幕第一帧实际播放 | 已显示系统推荐／自由输入；Ready hit／In-flight hit／Miss；云端／本地；冷／热 |
| PM-02 | 自由行动响应完成率 | 已接受自由行动中，按确认后的 QUICK／MERGED／FULL 路径完成合法反馈的比例；另列“需完整视频”的关键行动子集及成功率 | 技术完成、意图保留、响应分级分开；不能通过把所有动作降级为文本虚增完成率 |
| PM-03 | Ready 推荐按时发布率 | 需要系统推荐的互动节点中，在目标 Decision Lead Window／branch point 前成功发布 Ready 推荐集的节点比例 | 按目标 K、实际 K、云端／本地分组；已显示推荐本身 Ready hit 应为 100% 合同要求 |
| PM-04 | 篇章完成与续玩 | 已到达有效 Arc 结局／符合统计条件的已开始 Arc；Session 结束、暂离、主动续杯另记 | Q43 下完成旧 Arc 后继续不算未完成；退出矛盾结局不同于技术中断 |
| PM-05 | 剧情响应与体验反馈 | 真实体验者描述行动影响、递进、反转、收束和连续性，关联具体片段 | Q48 A 下以玩家是否喜欢及其原因评判戏剧效果，不用自动总分替代 |
| PM-06 | 愿望可追踪性 | 有状态、有效范围及规划／结果证据的 Wish／有效 Wish | 规划引用不等于实现；部分达成、失败与跨 Arc 延续分开 |
| PM-07 | 自由输入预取命中率 | 有效自由输入中，可语义等价复用 Ready／In-flight 内部候选的比例 | Ready 与 In-flight 分开；不能通过偷换用户意图提高指标 |
| PM-08 | 玩家喜好与继续意愿；Q48 A | 收集真实玩家是否喜欢、喜欢／不喜欢什么、是否想继续及原因 | 记录样本和辅助情况；无统一及格分，无反馈不能宣称已改善 |
| PM-09 | 续杯行为（辅助） | 结局后实际选择继续、成功建立新 Arc、主动停止或资源阻塞分别计数 | 仅为行为记录，不把点击续杯自动等同于叙事质量 |

### 16.2 系统指标

| 指标 ID | 名称 | 定义与注意事项 |
|---|---|---|
| SM-01 | Jev 延迟／升级率 | 真实请求起止、模型版本、请求规模；错误／低置信升级单列 |
| SM-02 | Skill 契约成功率 | 实际调用中类型合法且通过领域检查的比例；目录加载不算执行成功 |
| SM-03 | 状态一致性错误 | 非法补丁被错误接受、重复执行、投机污染、知识泄漏等错误分类 |
| SM-04 | Provider 任务延迟 | 提交、排队、推理、回传／下载分别记录；供应商未提供的阶段标未知 |
| SM-05 | 本地冷／热延迟 | 模型加载、热态生成、后处理、传输分别计时 |
| SM-06 | 生成／消费比 | 生成的媒体时长或成本／实际消费的媒体时长或成本；不可只看文件个数 |
| SM-07 | 投机浪费成本 | 已确定过期或未使用分支的实际计费成本／全部媒体成本；在途任务不提前判废 |
| SM-08 | 连续性返工率 | 因身份／状态／参考遵循问题重做的生成任务／已完成任务 |
| SM-09 | 预算守约 | 超预算提交次数、取消后新增任务数、重试额外费用 |
| SM-10 | 全链路成本 | 文本、Jev、Prompt 扩展、参考输入、视频、存储与传输等可获得费用；未知项单列 |
| SM-11 | Ready Gate 违规 | 已显示系统推荐在点击时不是 READY、缺有效版本或仍需启动同分支生成的次数；目标为 0 |
| SM-12 | 推荐集降 K 率 | 因 deadline／预算／队列从初始目标 K 下调后才发布的节点比例；用于评估速度—选择丰富度权衡 |
| SM-13 | 双域提交正确性 | World／Drama 版本冲突、部分提交、重复回收／愿望达成、投机污染等工程错误；不是戏剧质量分数 |
| SM-14 | 戏剧评估开销 | Jev／LLM 评估耗时、调用数、升级原因、重规划次数与费用；区分普通 Action／重要 Action／Beat 边界 |
| SM-15 | 响应分级与媒体支出 | QUICK／MERGED／FULL 实际数量、镜头任务及成本；只描述消耗，不自动宣称分级改善体验 |
| SM-16 | Provider fallback 率 | 按 role／primary→fallback／错误原因／Runtime Profile 统计；fallback 后质量与延迟分开 |
| SM-17 | Director 上下文负载 | 输入 token、各层占比、retrieved history 数量、TTFT、输出 token；用于控制长局退化 |
| SM-18 | Top-K 并行完成时间 | 从 K 锁定到最后一个待发布 Branch READY 的 wall time，另记各分支完成时间与 effective_k |
| SM-19 | Branch retry／K-1 率 | 单分支快速重试次数、重试成功率、因失败降 K 的节点比例 |
| SM-20 | Cache fingerprint 命中／失效率 | fingerprint valid hit、dependency invalidation、保守 miss、错误复用；错误复用目标为 0 |
| SM-21 | Provisional rollback 率 | SELECTED 后因媒体／前置条件失败回滚次数、被取消的 N+2 投机任务及 orphan 成本 |
| SM-22 | Profile 切换耗时与失败率 | drain、shutdown、load、health、route switch 分段计时；AGENT↔VIDEO 分开 |

供应商返回的 `inference` 字段可能只表示部分 GPU 推理阶段；例如 fal 文档将对应字段描述为 DiT 去噪时间。[S03] 不得拿它与从按钮点击到播放的端到端时间混合对比。

### 16.3 v0.5 性能策略：先测量，再冻结 SLA

Q62 明确选择 **A：现阶段不规定固定延迟等级或硬 P95**。因此旧版“交互回执 P95 ≤ 1 秒、Ready 首帧 P95 ≤ 1.5 秒”等仅作为曾讨论的工程建议，**不再属于 v0.5 的目标或验收门槛**。

实现阶段必须先记录：Jev、Director TTFT／输出、Narrative API、Production、H3、Assembly、Ready Gate、Profile 切换以及 fallback 的真实分布，并标注 context 长度、模型版本、冷／热状态和并发。团队在获得足够实测后再另行冻结 P50／P95 SLO。

厂商或 NVIDIA profile 的 tok/s／TTFT 仅作容量规划参考，不能直接写成产品承诺。[S24]

### 16.4 投机策略的比较实验

建议在相同 Scenario、相同候选展示和可回放行动序列下，对比“不预生成”“固定 Top-1”“动态 Top-K”。同时记录等待、生成成本、浪费、当前任务被投机挤占的时间和自由行动是否被错误合并。重复实验应固定可固定的条件，并记录供应商随机性与排队差异。

不能为了提高命中率把推荐选项改得更诱导，或者隐藏自由输入，再把收益全部归因于 Jev。候选质量、玩家行为模型、调度策略与视频吞吐需分别分析。

### 16.5 Q48 A：戏剧效果主要由真实体验判断

本次用户选择的是“看最终用户喜不喜欢”，不是 Q48 C 的结构指标＋盲测实验。**P0 不要求控制层 OFF／ON 对照、盲测、LLM Judge 或自动戏剧总分。** 16.1–16.2 仍用于观察体验和排查工程问题，不能将“字段非空、伏笔全部回收、压力一直升高”当作“故事好玩”的证明。

建议在可玩原型上让真实体验者自主选择、自由输入，经历当前 Arc 的推进和收束；结束后记录是否喜欢、最想继续／最想退出的片段、是否觉得被强拉主线，以及结局／续杯是否自然。具体问法可调整，不固定评分量表或样本数，也不要求一定试玩到系统指定轮数。

结论应分开记录：`实现可运行`、`规则符合契约`、`玩家主观评价`。工程用例全部通过但玩家认为无聊时，不能宣布戏剧目标完成；反馈积极但样本少时，应说明样本范围，不能直接推断所有用户。负反馈应关联具体事件与 Directive，形成可修订问题，而不是再让一个模型给出更高分覆盖它。

第 16.4 节保留的投机调度比较仅是原有可选工程实验，不是 Q48 的戏剧效果验收，也不修改正常产品的 Ready-only 契约。

## 17. 验收用例与完成定义

### 17.1 P0 必过用例

| 用例 ID | 场景与步骤 | 预期结果 | 对应需求 |
|---|---|---|---|
| AT-01 | 输入新设定，审阅 AI 生成的世界／戏剧草案并局部修改角色 | 有核心问题、冲突、真相、压力与可编辑内容；发布时不覆盖手工锁定字段 | FR-002～004、059 |
| AT-02 | 上传角色图片、声音片段、动作参考视频 | 三者可预览与绑定；有实际引用请求及可检查的输出 | FR-005～007 |
| AT-03 | 同一次生成混用图、声、视频 | Provider 收到全部有效输入；不静默丢弃其中任何一种 | FR-008 |
| AT-04 | 当前视频仍在播放时等待推荐面板出现，再选择任一已显示候选 | 面板出现时所有可点击候选均已 READY；点击走 Ready hit，不额外生成同一 Scene；播放有真实时间戳 | FR-009、018、019、037、041 |
| AT-05 | 输入“假装离开，再绕到后门观察”且无对应候选 | 形成新意图和 Beat，不映射成“离开”；显示加载动画并真实生成 | FR-010、020 |
| AT-06 | 现实世界输入不可能的道具／行为 | 故事内回应，不修改硬规则、不意外执行另一重大行动 | FR-012 |
| AT-07 | 提交“希望她最终不要死” | 独立保存原话与偏好；进入 Wish Ledger 和后续机会规划，不即时修改生死事实 | FR-011、017、053 |
| AT-08 | 已有投机缓存后更新有效 Wish、相关 Drama／Arc 或素材版本 | 受影响旧分支撤回；未受影响有效依赖可复用；失效分支不进入正式两域 | FR-019、041、056 |
| AT-09 | Skill／模型提交非法字段、过期 World／Drama 版本或重复提案 | 确定性拒绝／幂等，不改 Canonical 状态，不出现单边提交 | FR-014、056 |
| AT-10 | 多条投机分支生成但只选一条 | 只有选中合法分支提交；其他剧情、伏笔、愿望达成、债务不进入正式记录 | FR-013、019、050、053、056 |
| AT-11 | 多 Shot Beat 生成并装配 | 正确顺序、音轨与规格；成片是同一分支的真实多个镜头 | FR-021～024 |
| AT-12 | 命中一种机制事件，再推进剧情 | Skill 产出补丁，状态和 UI 更新，下一幕引用该变化 | FR-028 |
| AT-13 | Director 在不同真实历史下选择形成不同结局 | 方向与事实相容，引用实际行为；不要求固定轮数或强制 readiness 得分 | FR-029、052、054 |
| AT-14 | Jev 超时、返回错误或低置信 | 有可见降级／升级；无越权修改、无无限重试 | FR-016 |
| AT-15 | Full Beat 生成／装配失败，或合并片段在小动作已提交后失败 | 未提交 Full Beat 不推进；已提交小动作不重复执行、不被抹掉；有可恢复呈现 | FR-014、020、033、048、056 |
| AT-16 | 刷新、双击提交、重复供应商回调 | 没有重复付费投递或重复状态执行；恢复到正确 Scene | FR-033、034 |
| AT-17 | 达到整局或投机预算 | 不新增超额任务，当前用户输入得到明确反馈 | FR-018、034 |
| AT-18 | Spark 真实提交 Sol-H3 任务 | 本地节点完成视频；有配置、日志、时间与输出来源 | FR-026 |
| AT-19 | 查看一轮 Skill trace | 能从用户输入追到技能指令版本、工具、工件和状态结果 | FR-030 |
| AT-20 | 全局检索敏感信息和未发生事件 | 不向玩家泄露隐藏剧情、其他局素材、密钥或投机未来 | FR-013、030、权限要求 |
| AT-21 | 在可提前交互的 Beat 中打开 Decision Lead Window | 选项／输入区在当前视频结束前出现；窗口内后续画面对所有候选都成立；没有为等生成无限慢放 | FR-037 |
| AT-22 | `UNTIMED` 普通剧情节点在公共片段结束后仍未选择 | 不自动替玩家选择、不判失败；停在中性等待状态并继续接受输入 | FR-038 |
| AT-23 | `TIMED` 紧急对话或简化 QTE 超时 | 执行 Scenario 预先声明的 fallback，并形成正常事件／状态链；模型不能改判 | FR-038、039 |
| AT-24 | 玩家连续做出数次可分类行为后进入下一决策 | `PlayerPreferenceState` 只从已提交事件更新，Jev 请求包含该偏好信号；世界 Hard State 不因偏好本身改变 | FR-016、040 |
| AT-25 | Top-K 中一部分候选仍在渲染，另一部分已经 Ready | 未 Ready 候选不显示；调度器在发布前等待、降 K 或暂缓推荐，不能展示“可点但还要现生成”的系统选项 | FR-018、041 |
| AT-26 | 观察一个新行动从 Jev／LLM 评估到 Drama 更新 | 有类型化观察、证据、版本与 Manager 提交；模型不能直写状态 | FR-042、056、057 |
| AT-27 | 玩家在探索阶段合法提前揭开关键问题 | 可跳阶段或转后果／收束，不强迫补齐中间阶段 | FR-043、052 |
| AT-28 | 依次执行普通小动作、关键行动、完整 Beat 完成 | 普通动作不无故全量重规划，关键行动即时评估，Beat 后恰当评估且幂等 | FR-044、017 |
| AT-29 | 在 UNTIMED 界面久留／生成变慢，然后提交“等一小时” | 前两者不偷偷推进世界惩罚；明确等待按既有时间与 NPC 规则产生后果 | FR-038、045、051 |
| AT-30 | 明确写“跟踪是为了保护”，再测试低置信高影响歧义 | 明示动机不被偏好覆盖；需要时先澄清；不每次强制确认 | FR-046、057 |
| AT-31 | 查看一个准备生成完整 Beat 的 Directive | 输出戏剧功能、目标、硬约束与机会；不以固定事件替代玩家路径 | FR-047 |
| AT-32 | 空抽屉、小动作组合、关键发现三种输入 | 分别可快速反馈、合并、完整 Beat；状态不丢、不重复，关键发现仍有新视频 | FR-010、048、021 |
| AT-33 | 构造有前文证据和只在未选分支有证据的两个反转候选 | 前者可经语义复核执行，后者不得当作已铺垫；真相不被临时重写 | FR-049、019 |
| AT-34 | 新生伏笔登记、呈现、回收，并测试跳过／未选视频 | 生命周期可追溯；未呈现内容不自动构成玩家已知，回收有正式事件 | FR-050、056 |
| AT-35 | Director 请求升级冲突，但既有压力源不支持某灾难 | 不凭空增加灾难或改时钟；改用合法机会或承认当前不应加压 | FR-051、058 |
| AT-36 | 在不同长度的轨迹中让 Director 判断继续或收束 | 根据具体历史作判断，配置中没有必须达到的结局分数／固定轮数门槛 | FR-052 |
| AT-37 | Wish 暂无可行机会、部分实现、与已发生事实冲突 | 状态与解释可追踪；失败／部分达成允许，不改过去、不伪称已实现 | FR-053 |
| AT-38 | 玩家明确离城并拒绝继续参与当前矛盾 | 可真实进入退出／后果结局，不被强行带回主线，也不凭空施加灾难惩罚 | FR-054、052 |
| AT-39 | Arc 关闭后先不继续，再点击继续这个世界 | 未请求不自动开启；请求后新建 Arc，继承事实关系、检查未结项范围与预算，旧结局不变 | FR-055、034 |
| AT-40 | World／Drama 联合提交失败、重复通知或过期分支试图提交 | 两域一致、幂等或明确拒绝，恢复不会出现已死角色被戏剧状态复活等冲突 | FR-056、014 |
| AT-41 | Jev 高置信普通判断与高置信重大反转／结局判断对照执行路径 | 普通闭集可快行，重大语义仍由正确角色审查；结局决定归 Director | FR-057、052 |
| AT-42 | 压力、伏笔、关系与 Wish 同时争用下一幕 | 硬约束优先；待处理事项有来源，可解释选择当前机会、延期或放弃，不一次硬塞全部 | FR-058 |
| AT-43 | Creator 仅提供一句故事想法，并否决一项 AI 戏剧设定 | AI 起完整草案，简明审阅可局部修改；不要求 Creator 重写专业字段或整个故事 | FR-059、002、003 |
| AT-44 | 真实体验者试玩并提供反馈 | 记录是否喜欢、原因与具体片段、是否想继续；无反馈不虚构结论，不强制盲测／自动打分 | FR-060、031 |
| AT-45 | 在 DGX Spark 启动锁定的 Lightning Director，并执行中文自由行动＋Drama 规划 | trace 显示本地模型 ID／版本；能生成合法结构化 Director 产物；失败如实记录 | FR-061、067、072 |
| AT-46 | Ready 推荐与自由输入各执行一次 | Ready 点击复用同一 BranchContract、不重复 Narrative／视频；自由输入新建 Branch 且保留原文＋Jev observation | FR-065、066 |
| AT-47 | 给 Director 一个长局 Session | Prompt 由分层 Context 构造，不默认塞全量 Event Log；可追踪摘要／检索来源和 token 占比 | FR-067 |
| AT-48 | Narrative 收到 ScenePacket，尝试泄露未允许核心秘密 | 输出被约束／校验拒绝，不因 Narrative 看到全局数据而提前揭密 | FR-068 |
| AT-49 | K=3 且 Provider 允许三路并发 | 三条 Branch 在 K 锁定后并行启动；不存在人为 Top-1→B→C 串行队列 | FR-069、070 |
| AT-50 | 玩家点击 READY Branch，随后媒体校验失败 | 先有 SELECTED provisional，可启动 N+2；失败后 provisional 回滚且正式 State／Drama／伏笔未污染 | FR-071 |
| AT-51 | 采集一轮全链耗时 | 有各阶段真实 timing／context／cold-hot 标记，但系统不以旧 P95 示例判 PASS／FAIL | FR-072 |
| AT-52 | Top-K 中一条 H3 任务暂时失败两次 | 第一次快速 retry，第二次失败后其余 Ready 以 K-1 发布；effective_k／原因可查 | FR-073 |
| AT-53 | 注入 Step 3.7 Narrative timeout 于 AGENT_LOCAL_PROFILE | Router 记录错误并回退本地 Lightning；最终 ScenePacket 契约不变，来源标 fallback | FR-074、080 |
| AT-54 | 注入本地 Lightning Director OOM／service down | Director 回退 Step 5 Preview；不误路由到 Step 3.7 作为第一 fallback | FR-075、080 |
| AT-55 | 未选 Branch 在若干轮后出现相似请求 | 只有 Dependency Fingerprint 仍兼容才复用；相关人物／Wish／Asset 改变后确定性失效 | FR-076、077 |
| AT-56 | AGENT_LOCAL→VIDEO_LOCAL→AGENT_LOCAL 切换 | 每次完成 drain／persist／unload／load／health／router switch，State 不丢、无假同驻；切换时间可查 | FR-064、078 |
| AT-57 | VIDEO_LOCAL_PROFILE 下执行 Production | 本地 Lightning 被视为 unavailable，Production 自动按 Q69 走 Step 3.7；来源正确 | FR-079、081 |
| AT-58 | VIDEO_LOCAL_PROFILE 下同时注入 Step 3.7 Narrative 故障 | Router 不错误尝试已卸载 Lightning；明确返回当前无已冻结 fallback／进入可恢复错误路径 | FR-074、081 |
| AT-59 | 对不同角色注入不同 Provider 故障 | Provider Router 按 Director／Narrative／Production 各自固定 fallback 链工作，circuit breaker／trace 正确 | FR-075、079、080 |
| AT-60 | 升级一个 Provider 模型版本后复用旧 Branch | 模型／adapter／profile 版本进入 provenance；若 Provider Contract 影响结果则 fingerprint／测试触发失效或重新验证 | FR-077、082 |


| AT-61 | 从 Global Character Library 搜索一个仅 personality 命中的角色 | 后端真实返回该角色；搜索能力与 UI placeholder 一致 | FR-083 |
| AT-62 | 用一句描述 AI 创建角色 | fal-ai/nano-banana-2 真实产生 2 张 Candidate；未选择前都不是 Canonical | FR-084、085 |
| AT-63 | 选择主图后点击生成标准参考组 | 先出现二次确认；确认后生成正面/3⁄4/侧面/全身正面/全身侧面并记录 provenance | FR-087、102 |
| AT-64 | 对 Canonical 角色执行“换成雨衣，保持身份” | fal-ai/nano-banana-2/edit 真实调用；原图不覆盖，新图为 Candidate；身份保护要求进入请求 | FR-086、088、095 |
| AT-65 | 使用快捷“只改背景/姿势”与自由自然语言各编辑一次 | 两种入口都落到 IMAGE_EDIT；无需 Mask 编辑器；结果和输入引用可追踪 | FR-086 |
| AT-66 | 创建 Outfit 并补两张视图 | Outfit 仍属于同一 GlobalCharacter，可缺未生成视图，不复制角色 | FR-088 |
| AT-67 | 上传静态 Pose 与动作视频 Reference | 二者均绑定 CharacterVersion，并能被 Production Resolver 读取；不存在固定表情资产库要求 | FR-089 |
| AT-68 | 更换主身份图、Canonical Voice、仅新增 Outfit 各一次 | 产生正确 CharacterVersion 与 change_type，identity-breaking change 明确警告 | FR-090、092 |
| AT-69 | Scenario 使用 Alice v3 后 Global 更新到 v4 | 已发布/已有 Scenario 保持 v3 Snapshot；Creator 可查看差异并选择继续或升级 | FR-091 |
| AT-70 | 在 Scenario 内改角色外观 | 用户可选择仅本故事或更新全局；local override 可再人工保存为全局新版本 | FR-091 |
| AT-71 | 单角色 Scene 请求 Production | Resolver 自动选择最相关 2–4 张图 + 必要 Voice/Motion；实际 H3 请求与选择清单一致 | FR-093 |
| AT-72 | 双角色 Scene 且素材接近 Provider 上限 | 两个角色先独立打包，再按总上限确定性裁剪；主身份引用不被静默丢弃 | FR-093 |
| AT-73 | 修改角色文字描述但不点重新生成 | 旧视觉资产保持不变，UI 提示可能不一致并提供保持/重生/编辑；无自动 API 请求 | FR-096 |
| AT-74 | 1366×768、1440×900、1920×1080、2560×1440、3840×2160 在 100% Zoom 走 Creator/Character/Player/Developer | 核心文字可读、布局无关键遮挡；1080p 不依赖 150% Zoom；2K/4K 合理扩展 | FR-099、100 |
| AT-75 | 标准模式与开发者模式查看同一角色生成任务 | 标准模式隐藏 Prompt/Provider；开发者可见真实 model/request/artifact；FAL_KEY 永不出现在浏览器/Trace | FR-097、098 |
| AT-76 | 封版模型部署核查与一次 AGENT↔VIDEO 往返切换 | 六类模型/Provider 均有真实请求或本地输出证据；Profile 切换证明真实服务启停与资源状态 | FR-101 |
| AT-77 | 用一句很模糊的故事描述创建 Scenario | Standard 不出现一排空字段；AI 显示当前理解并只针对关键缺失项给出上下文相关建议 + 自由输入 | FR-103、104 |
| AT-78 | 用一段已经明确真相、冲突、压力的详细描述创建 Scenario | 已明确内容不重复追问；只显示真正缺失/低置信高影响项，用户可直接接受并继续 | FR-103 |
| AT-79 | 同一 Scenario 在 Standard / Developer 查看戏剧结构 | Standard 为自然语言主题与建议；Developer 能看到对应 DramaSpec 原始结构，二者保存后指向同一正式数据 | FR-104 |
| AT-80 | 从角色库与 Creator 打开同一 Global Character | 两边信息架构颗粒度一致；Creator 清楚显示 Global 继承项与 Scenario Overlay，不出现两套互不兼容角色定义 | FR-105～107 |
| AT-81 | Scenario 给角色修改 Desire/Secret/Visual State | 只改变当前 Snapshot/Override；Global Character 不变；用户显式“保存为全局新版本”后才产生全局版本 | FR-107 |
| AT-82 | 输入“主要靠调查和询问角色，角色记得我是否撒谎，追逐时要快速决定” | Standard 生成可读玩法教程卡；后台产生受验证 MechanicSpec 并绑定对应 Skills | FR-108、109 |
| AT-83 | Standard / Developer 查看同一玩法机制 | Standard 无空 JSON textarea；Developer 可查 skill_id/version/typed config/trigger，二者修改走同一验证链 | FR-108、109 |
| AT-84 | Player 进入/退出 Theater Mode | 浏览器保持普通窗口（进入 Theater Mode 本身不要求 `document.fullscreenElement`）；Sidebar/应用级 Header 隐藏，Player 占满应用可用视口；视频 Stage 为视觉主体，HUD 位于左上，Ready 推荐在 Stage 下方，自由输入固定最底层；退出后 Session/播放/输入状态不丢失。另测 Browser Fullscreen 时不得影响这些层，但 Browser Fullscreen 不是本 AT 的主通过条件 | FR-110 |
| AT-85 | 视频尚未进入 Decision Lead，再到达 Lead | 到达前不出现系统推荐；到达后只显示完整 Ready 推荐，位置位于自由输入上方 | FR-111 |
| AT-86 | 有 3 个 Ready 推荐时玩家坚持自由输入 | 自由输入始终可操作并形成 FREE branch；系统不强迫三选一；一旦行动接受，重复提交被锁/幂等 | FR-111 |
| AT-87 | Player 查看背包/关系/线索/Wish | 左上 HUD 可 hover 临时展开、点击固定；Standard 关系为定性文案，Developer 可查原始数值 | FR-112 |
| AT-88 | Director 返回与 DramaticDirective Schema 不一致的结构 | Standard 不显示 Pydantic/Python 原始错误；安全可修复时规范化或一次 schema retry，仍失败进入 FAILED_RECOVERABLE；Developer 可查原始错误 | FR-113、114 |
| AT-89 | 播放一个包含中文场景名、人物名和字幕的视频 | 无 tofu 方块/乱码；场景标题短暂显示后淡出；字幕在安全区可读，画内/画外设置正常 | FR-114 |
| AT-90 | 分别触发视频生成中、媒体载入中和加载失败 | 三种状态视觉/文案可区分；Failed 提供重新载入/重新生成/文字继续等合理恢复，不出现无解释永久黑屏 | FR-113、114 |

所有 AT 用例在本文交付时状态为 `NOT RUN`。v0.6 新增 AT-61～90；其中涉及 fal.ai、H3、Jev、StepFun、Lightning、Sol-H3 的项目必须用真实调用/节点证据，不得由 Mock 测试替代。实现阶段应保存 `PASS / FAIL / BLOCKED`、执行环境、请求配置、输出工件和复核记录。一次成功片段不能代替三类素材及多轮稳定性的验收。

### 17.2 单项功能完成定义

一个功能只有在实现、正常与主要失败路径测试、日志可查、输入输出契约固定、演示可复现之后，才算完成。涉及外部 API 必须有真实调用；涉及本地推理必须有真实节点证据；涉及效果判断必须有样本与检查标准。测试桩可以加速开发，但不得通过改名变成真实实现。

### 17.3 人工体验验收的执行与记录

AT-44 验收的是“真实体验与反馈被完成、问题被诚实记录”，不意味着反馈天然正面。最低记录包括原型版本、Scenario／Arc、体验者与团队的关系（匿名即可）、是否被引导、实际经历范围、是否喜欢及原因、关键正负片段、继续意愿和待改问题。

建议自由试玩后再询问感受，避免先告诉体验者“这里有先进戏剧控制，所以应该很有趣”。这是普通用户研究的执行建议，不等于要求盲测或对照实验。负反馈保留原意；把技术 bug 与叙事节奏问题分开整理。

若只有开发者自己走完预定演示路径，应标“团队自测”，不能写成已验证普通玩家喜好。样本数量和满意标准尚未由用户指定，实施时记录实际范围即可，不补造统计显著性或达标率。

## 18. MVP 交付、演示与实施顺序

### 18.1 MVP 必做与可后移范围

| 范围 | P0 必做 | P1／P2 可后移 |
|---|---|---|
| 内容与创作 | 一个高质量完整 Scenario、AI 创作、简单结构化编辑 | 多题材库、复杂节点编辑、多人创作 |
| 素材 | 图、声、视频完整消费链路及混合验证 | 大型素材市场、高级资产自动标注 |
| 互动 | Ready 推荐＋自由行动＋置信回显＋Wish＋主题加载＋小动作反馈 | 等待期聊天／调查小游戏、完整 QTE 玩法、连续语音输入 |
| 玩法 | 至少一种闭环 Mechanic Skill | 全量恋爱／背包／战斗／QTE 系统 |
| 生成 | 多 Shot 装配、H3 Max 主路、Sol-H3 真实任务 | 持续流式世界、任意长片、自研视频模型 |
| Skills | 真正加载执行与日志、契约测试 | 现场热插拔、公开技能市场 |
| UI | 一套完整主题＋受控配置 | 任意自然语言生成布局、多主题市场 |
| 可靠性 | 双域受控事务、预算、错误恢复、任务来源、Arc 继承 | 大规模多租户与跨区域部署 |
| 模型／Runtime | Lightning 本地 Director、Step 3.7 Narrative、Step 5 Authoring／Director fallback、统一 Router、双 Profile、BranchContract、两阶段提交 | 多节点自动弹性调度、更多模型自动择优 |
| 戏剧控制 | 柔性阶段、双尺度评估、Progress、真相／伏笔／压力／Wish／待处理事项、Directive | 复杂自动调参、额外戏剧专用 Agent、大型规划搜索 |
| 结局／体验 | Director 收束、合法退出结局、主动新 Arc 续杯、真实玩家反馈 | 自动戏剧 Judge、强制盲测或开关对照均非本轮必做 |


v0.6 对 P0 再增加三个不可后移的封版面：

1. **Character Studio 闭环：** Global Character → Nano Banana 2 生图/Edit → Canonical/Version → Scenario Snapshot → Reference Resolver → H3 实际消费。
2. **100% Zoom 响应式：** 1080p/2K/4K 及常见较小桌面真实浏览器回归；全局 Appearance/UI Size/字幕设置与 Scenario Theme 分离。
3. **真实模型部署证据：** 所有固定 Provider 与双 Runtime Profile 必须有可复核工件；配置文件、Mock 和前端状态不能算部署完成。

### 18.2 现场演示脚本

| 阶段 | 演示动作 | 证明什么 | 真实性要求 |
|---|---|---|---|
| D1 创作 | 输入想法，审阅世界／戏剧草案并局部修改 | 不手写分支树或专业戏剧配置 | 展示实际核心问题、冲突、压力等结构 |
| D2 素材 | 绑定图、声、视频并展示合法参考配置 | Q25 A 的完整输入能力 | 素材确实出现在一次生成请求中 |
| D3 开场 | 进入已发布 Scenario，播放开场 | 普通用户有明确入口与角色 | 预制开场明确标为预先准备，不冒充实时 |
| D4 命中 | 当前视频进入 Decision Lead Window；推荐面板在候选全部 Ready 后出现，随后选择任一项 | 观看／思考／预生成并行，且“显示即可播放” | Trace 展示每条候选 Ready 与面板发布时间；不用已录制伪装 |
| D5 自由行动 | 输入计划外关键行动，并可穿插一个小动作 | 开放路径与戏剧价值分流 | 关键行动有新 Beat／视频和真实 miss；小动作不能伪造视频任务 |
| D6 许愿／机制 | 提交 Wish，触发一条线索或关系变化 | 偏好与状态持续影响剧情 | 展示 StatePatch 与后续引用，不即时魔法改写 |
| D7 装配／结局 | 展示多 Shot 片段、Director 的自然收束与事实回扣 | 自动生产链完整，结局不按固定轮数硬切 | 不拼接其他会话补成功，不为演示篡改真相 |
| D8 本地执行 | 切换资源 profile，提交 Sol-H3 任务 | NVIDIA 本地视频后端真实存在 | 输出关联 Spark 节点、配置与任务 |
| D9 技术审阅 | 任务运行期间讲解 Skills、World／Drama、Jev 和 Directive | Q28 B：真实执行；控制层不是另一个随意编剧 Agent | 日志有版本和证据；不展示隐藏推理或假成功 |
| D9b 模型路由 | 展示 Director=本地 Lightning、Narrative=Step 3.7、Authoring=Step 5、Production route 与一次可控 fallback | Q49–Q70 的模型职责是真实运行，不是架构图 | trace 显示 provider／model／profile 与 fallback 原因；不暴露密钥 |
| D9c Branch／并行 | 展示 Top-K 并行 trace、Ready BranchContract 与 SELECTED→CANONICAL | 推荐零重推理、并行预生成和事务安全 | 真实 span／job 时间，不用假并行日志 |
| D10 结果展示 | 展示本地输出及冷热／切换耗时 | 双后端与性能口径诚实 | 本地输出晚于主路并非造假理由 |
| D11 续杯 | 当前 Arc 关闭后选择“继续这个世界” | 旧结局保留，人物关系／事实延续，新问题开始 | 新 Arc 有 ID、继承清单与资源检查；不自动重置历史 |
| D12 玩家反馈 | 展示已经实际收集的体验意见和仍待改进项 | Q48 A：以玩家感受评价戏剧效果 | 没有样本就明确未评估，不用自动分数替代 |

可根据现场时长把本地任务启动前移，但须先通过资源切换测试。Q26 B 允许“本地生成期间继续讲解”，不代表同一 Spark 必须同时运行所有模型。演示时不规定必须现场热插拔 Skill，也不规定必须做 Drama Control 开关或盲测。D11／D12 可按现场时长展示真实存档／先前反馈并明确来源，不能冒充刚刚生成或刚刚完成的玩家测试。


v0.6 现场演示建议在 D2 前增加“D1b 角色制作”：从一句角色描述生成 2 张候选，选择 Canonical，执行一次换装 Edit，展示 CharacterVersion；随后在 D2/H3 请求中证明该角色 Snapshot 的参考图被 Resolver 自动选中并实际发送。另在 D9 技术审阅中切换标准/开发者模式，展示普通用户不见底层 Prompt，而开发者可以查看同一次 fal/H3 调用的真实 Provider、Model、Request 和 Artifact。

演示机浏览器必须使用 100% Zoom；如需要调到 150% 才能看清，应判定 UI 响应式尚未封版，而不是现场临时放大。

### 18.3 实施顺序与依赖

| 阶段 | 工作包 | 进入条件 | 可交付成果 |
|---|---|---|---|
| M0 可行性探针 | Jev、Step 3.7、Step 5、H3 Max、Lightning 本地、Sol-H3 各自最小真实调用 | 凭据、算力与预算可用 | 固定模型 ID／adapter、能力矩阵、真实产物、延迟和资源记录 |
| M1 契约与状态 | Scenario／Arc、World／Drama、Proposal、Job、Trace、预算 | 本 PRD 基线 | 同库双域最小 Runtime、版本与幂等测试 |
| M2 文本可玩链 | Action／Desire、轻评估／Directive、Progress、伏笔／真相／压力／Wish、退出与续杯 | M1 | 先用文本验证戏剧与因果，再做初轮真人试玩；不是最终视频能力的替代 |
| M3 媒体闭环 | 三类素材、生产 Skill、视频 worker、剪辑 | M0 云端能力、M1 | 一次行动到可播放 Scene 的真实链 |
| M4 投机调度 | BranchContract、Jev、Top-K 全并行、Ready Gate、两阶段提交、Fingerprint Cache、Lead Window | M2＋M3 | Ready 点击不重推理；失败 K-1；投机状态不污染事实 |
| M5 Provider 与双后端 | Provider Router、Director／Narrative／Production fallback、AGENT↔VIDEO Profile、恢复、主题与玩家页面 | M0 本地／API 能力、M3 | Creator→Player→fallback→本地视频任务完整演示 |
| M6 验收与封版 | AT-01～60、Provider／Profile 失败注入、来源核查、真实玩家反馈、内容打磨 | 前述闭环可运行 | 演示包、真实反馈与改进项、日志、已知限制、固定版本配置 |

这不是工期承诺；团队人数、技能分布和节点获得情况尚未知。不要为了赶进度先造漂亮视频再补状态系统，因为那会掩盖最核心的假自由问题。

公开活动说明给出的预赛作品开发与提交窗口为  **2026 年 9 月 20–29 日** ，决赛路演为  **2026 年 10 月 15 日** ；说明强调完整可运行的 Agent 应用和 Agent Skills。[S20] 具体提交时刻、格式、评分权重、本地模型要求与团队是否已获节点，仍应以参赛者收到的最新官方规则为准。本文不从宣传材料推断“API 不允许”或“必须全本地”。

### 18.4 v0.3 → v0.4 的最小工程增量

先扩充 Schema／状态域与 Authoring 输出；再在 Director 中加入重要性判定、语义评估与 Directive；接入 Quick／Merged／Full 分流、伏笔／反转与因果压力；最后打通 Arc 关闭／继续及缓存依赖。现有视频 Adapter、三模态上传、装配和四 Agent 配置优先复用。

不以“戏剧控制”名义重写全部 Runtime，不要求单独部署第五个 Agent、额外常驻 LLM 或新的微服务集群。原型初期可只实现一种题材、一小组明确压力源和一个短 Arc 的续接；能力必须真实闭环，不能把多个 Ledger 做成不参与运行的展示页。


### 18.5 v0.4 → v0.5 的最小工程增量

1. 先把本地 Director 服务锁定为 Nemotron 3.5 Lightning，并用固定中文 Director case 跑通结构化输出；
2. 加 `ProviderRouter` 与 role-specific route，不改四 Agent 业务职责；
3. 引入 `BranchContract / ScenePacket / WorkingContext / RuntimeProfile / ProviderRouteEvent`；
4. 把推荐与自由输入拆成双 Pipeline，Ready 点击改为 Branch 复用；
5. 将 Top-K 调度改为“锁 K 前做容量判断，锁 K 后全并行”，接入一次快速 retry 与 K-1；
6. 实现 SELECTED provisional view 与 CANONICAL commit；
7. 把旧粗缓存升级为短 TTL + Dependency Fingerprint；
8. 完成 AGENT_LOCAL／VIDEO_LOCAL Profile 切换和 Q64／Q65／Q69 fallback 注入测试。

不需要为了 v0.5 新增 Agent 数量，也不要求把所有服务迁移到微服务。优先把 Provider、Branch 和事务边界做正确，再优化性能；Q62 已明确不在本版先写硬延迟 SLA。


### 18.6 v0.5 → v0.6 的最小工程增量

1. 先把 GlobalCharacter 从普通资料 CRUD 升级为 CharacterVersion / CharacterAsset / ScenarioCharacterSnapshot 数据模型，并迁移现有角色引用；
2. 实现 Image Router，服务端接 fal-ai/nano-banana-2 与 fal-ai/nano-banana-2/edit，统一 GenerationJob、错误、Trace 与资产落库；
3. 实现 Character Studio：三种创建入口、2 候选、Canonical、多视图、Outfit、Pose/Motion、Voice、版本与使用记录；
4. 实现非破坏 Edit、Canonical 替换保护、Global↔Scenario 作用域选择和版本 Diff；
5. 实现 Production Reference Resolver，把 Snapshot 中选出的实际 image/voice/motion refs 编译进 H3 Provider 请求，不允许 references 静默丢失；
6. 补全 Standard/Developer、全局 Appearance/UI Size/Subtitle 与 100% Zoom 响应式；
7. 真实核查 Lightning、Step 3.7、Step 5、Jev、H3 Max、Sol-H3 和双 Profile；形成可复核 deployment report；
8. 执行 AT-61～76，并与原 AT-01～60 一起形成 PASS/FAIL/BLOCKED 矩阵；
9. 将 Standard Creator 从空白 Schema 表单改为“AI 当前理解 → 缺失追问 → 建议卡/自由修改 → typed patch”，保留 Developer 原始结构；
10. 统一 Character Library 与 Creator 的角色信息架构，引入明确 Global Core / Scenario Overlay 展示，不改变已有 Snapshot 数据边界；
11. 将玩法机制 Standard UI 改为自然语言教程卡，补 Authoring Intent → MechanicSpec Proposal → Schema Validate → Runtime Skill 的编译链；
12. 将 Player 改为视频优先四层架构，支持 PlayerShell 全屏、Decision/Agency Dock、左上 HUD、Standard-safe Error 与媒体状态区分；
13. 执行新增 AT-77～90，重点验证“创作端不暴露机器结构、游玩端不暴露机器运行过程”。

v0.6 不要求建设 Photoshop 级 Mask 编辑器、固定表情资产库、角色素材市场、复杂预算套餐，也不新增第二个默认图像 API 供应商。

## 19. 未决依赖、风险与新增建议

### 19.1 尚待验证，但不需要再重开产品访谈的事项

| 风险／依赖 ID | 未决事项 | 对交付的影响 | 应产出的确认或实测 |
|---|---|---|---|
| R01 | 实际参赛规则与提交要求 | 可能影响部署证据和 Demo 包装 | 官方完整规则／参赛通知，不自行猜评分比例 |
| R02 | DGX Spark 节点、权限、磁盘与网络 | 决定本地模型和容器能否运行 | 设备清单、权限、预装栈、可用内存与磁盘 |
| R03 | API 凭据、配额、并发与预算 | 决定云端三模态和投机可用规模 | G01／G02 实测与实际价格快照 |
| R04 | Jev 的中文和行为预测效果 | 可能有高速但错误的路由／排序 | 中文边界测试、真实选择记录、保守阈值 |
| R05 | Sol-H3 与本地文本模型争用统一内存 | OOM、重载耗时、无法同时演示 | G03–G05；默认分时，不假定共驻 |
| R06 | 多角色、多 Shot、声音的连续性 | 体验核心可能失败 | 参考组合测试、人审样本、错误分类 |
| R07 | 自由行动语义过度归并 | 产品退化成固定选项工具 | AT-05 及多目标／否定表达测试 |
| R08 | 多分支多镜头造成预算增长 | 低等待以不可控成本换取 | 分层预算、实际账单、SM-06／07／10 |
| R09 | 生成结果与正式世界矛盾 | 后续剧情出现不可能事件 | 提交边界、关键检查、失败回退 |
| R10 | 三模态完整支持使范围偏大 | UI／转码工作挤压 Agent 核心 | 简化编辑器和题材数量，不删 Q25 功能 |
| R11 | 示例 Scenario 尚未最终选题 | 素材准备和机制难度不确定 | 建议少角色、少场景、明确冲突；题材由创作阶段定 |
| R12 | 团队分工与实际演示时长未知 | 实施顺序与演示片段需调整 | 明确负责人、提交检查表、实测演示时长 |
| R13 | Jev 的欲望／重要性判断错误或置信失真 | 系统误解玩家并生成错误后果 | 明示动机优先、UNKNOWN、低置信高影响澄清、任务级测试 |
| R14 | Drama State 自我证明、投机伏笔入正史 | 随机反转、真相漂移、虚假推进 | 证据引用、双域 Manager、呈现回执、AT-26／33／34／40 |
| R15 | 世界时钟与 UNTIMED／媒体等待混淆 | 玩家被暗中惩罚，破坏既有自由交互 | 明确 fiction／wall／deadline 三种时间，AT-29 |
| R16 | 玩家体验样本和反馈尚未取得 | 无法声称故事有趣或控制层已改善体验 | 真实试玩、样本与片段记录；不代填分数、不强制新增盲测方案 |
| R17 | 续杯历史增长、预算和未结事项累积 | 上下文膨胀、旧结局被破坏、超额消费 | Arc 摘要及事件检索、关闭快照、范围审查、全会话预算 |
| R18 | Full Beat 门槛导致只剩文字或强行高戏剧 | 偏离互动视频定位或产生廉价刺激 | 保留重要自由行动视频验收，允许安静有效段落，依据玩家反馈调整 |
| R19 | 新评估增加延迟并频繁使 Ready 候选失效 | 就绪推荐迟迟不出现，预算浪费 | 复用快评、批处理、依赖版本和 recommendation epoch，记录真实开销 |
| R20 | Lightning 的中文剧情规划／结构化输出未由本项目验证 | Director 可能高速但误解中文欲望、Drama Debt 或泄密约束 | 固定中文 Director benchmark、长局 case、schema／tool 成功率；不因已锁模型跳过测试 |
| R21 | Top-K 全并行冲击 API 并发／成本 | Ready 更快但可能触发 rate limit 或瞬时预算峰值 | 锁 K 前检查并发与预算；不足直接降 K，不在锁定后排队 |
| R22 | VIDEO_LOCAL_PROFILE 中 Narrative 本地 fallback 缺失 | Step 3.7 同时故障时 Narrative 无已冻结 fallback | Profile 切换前 health check；失败明确阻塞／恢复，后续再决定是否增加 emergency provider |
| R23 | Dependency Fingerprint 漏依赖 | 错误复用旧视频导致剧情／视觉冲突 | read set 审计、保守 miss、AT-55；错误复用视为一致性缺陷 |
| R24 | Provisional N+2 预取后 N+1 回滚 | 产生 orphan 任务和额外成本 | 依赖链取消、budget tag、orphan provenance、SM-21 |
| R25 | Provider fallback 导致风格／行为差异 | 同一角色文风突变或 Structured Output 失败 | role-specific contract tests、fallback 质量样本、记录实际 provider |
| R26 | Runtime Profile 切换失败或耗时过长 | 本地演示中断、Spark OOM／端口冲突 | 状态机式切换、恢复旧 Profile、真实 cold-start 计时、AT-56 |

### 19.2 本次新增建议清单

| 建议 ID | 建议 | 为什么值得采纳 | 未采纳的影响 |
|---|---|---|---|
| REC-01 | 用确定性 State Service 承接 State Agent 写入 | 让事务、版本、幂等不依赖概率输出 | 需要另一个可证明等价的安全提交机制 |
| REC-02 | 同一 Spark 采用两个资源 profile | 避免把近满内存的视频配方和 LLM 强行同驻 | 必须提供实际共驻证据或更多设备 |
| REC-03 | 前瞻深度与媒体预生成深度分开 | 符合 Q19 的低成本预测，不做整树视频 | 预算和吞吐很容易被前瞻树耗尽 |
| REC-04 | 就绪命中与在途命中分开 | 不把仍在等待的请求包装成实时命中 | 缓存指标无法反映真实体验 |
| REC-05 | 所有外部素材使用可追踪引用与授权记录 | 可复现、能删除、能解释生成来源 | 后续难以核查人物和声音素材使用 |
| REC-06 | 复用官方 H3 Prompt Skill，但保留自有编译链 | 少重复造轮子，并准确界定贡献 | 更多工作花在底层格式而非互动体验 |
| REC-07 | 单一编排器、小型持久化任务层 | 降低框架整合复杂度 | 多框架调试会消耗黑客松时间 |
| REC-08 | Demo 用少量角色、场景和可见状态变化 | 更易证明自由行动与连续性，而不是用大场面掩盖问题 | 生产质量和一致性风险增大 |
| REC-09 | 默认 Wish 下一未锁定 Beat 生效 | 兼顾用户意图与缓存／付费任务稳定性 | 必须另行定义生成中的愿望如何改写任务 |
| REC-10 | 不把“实时”“全本地”“自由无限”作为无条件宣传 | 与真实能力和本次混合部署保持一致 | 容易出现无法兑现的评审演示承诺 |
| REC-11 | Drama State Manager 与 World State 先共用数据库事务 | 落实 Q44，而不增分布式事务负担 | 其他实现须证明一致性、幂等和恢复 |
| REC-12 | Director 的语义评估、Directive、计划可合并结构化调用 | 保持逻辑边界但减少串行延迟 | 多次调用须有可测收益和预算依据 |
| REC-13 | 用事件／呈现引用表达 Progress，而非只堆分数 | 防止模型自证有趣或凭空铺垫 | 需提供等价证据链，不能只有自然语言自评 |
| REC-14 | 新 Arc 继承清单及不可变关闭快照 | 避免续杯反向破坏旧结局 | 需另有可验证的事实与结局保护机制 |
| REC-15 | Director Context 优先结构化检索，再考虑向量库 | 长局先避免全量 prefill，减少新基础设施 | 若标签／实体检索不足，再以真实 miss case 引入向量检索 |
| REC-16 | Profile 切换前做 Step 3.7／Step 5 health preflight | VIDEO_LOCAL 依赖云端文本链 | 该检查是工程建议，不等于新增 Narrative emergency fallback |
| REC-17 | Provider Router 与 Agent 业务逻辑分层 | 容错和供应商切换可集中测试 | 分散 if/else 会让 fallback 无法审计 |

这些建议没有替换用户的选项。尤其不重新要求用户选择音视频占位、等待期小游戏、技能开关演示或全云／全本地单一路线。

### 19.3 v0.2 对早期 PRD 的实质修正（继承记录）

本版新增了原始意图和全部决策追溯；恢复了被弱化的界面风格定制；明确 Q18、Q25、Q28 对早期推荐的覆盖；纠正“Jev 生成选项文本／写未来剧情”的职责混淆；分开分支与 Shot 成本；加入投机状态隔离、Wish／素材导致的缓存失效、真实媒体消费验收和幂等提交。

技术上不再默认所有 Agent 与 Sol-H3 能同时装进 Spark，也不把厂商单条生成用时当作整轮等待保证。性能目标、模型候选、题材建议和待验证项均明确标注来源，避免把助手建议写成已获用户确认的事实。

### 19.4 v0.3 增量修订

v0.3 不重写 v0.2 的 Agent、Skill、状态和双后端主架构，主要补足 **互动视频时序**：引入 Decision Lead Window，使选择界面可在真正分叉前出现；把普通决策与限时互动分成 `UNTIMED / TIMED`；为限时互动增加 deterministic timeout fallback；正式定义 session-scoped `PlayerPreferenceState` 作为 Jev 候选排序信号。

同时，用户明确选择“**所有显示的系统选项必须 Ready**”。因此本版覆盖 v0.2 中“显示选项数可以大于实际预生成数”的派生解释：动态 Top-K 仍保留，但未 Ready 候选只能存在于内部投机队列，不能出现在正常推荐面板。系统推荐点击应天然是 Ready hit；自由输入继续承担开放剧情和真实 miss。


### 19.5 v0.4 修订记录与追溯

本版保留 v0.3 的全部 41 个功能 ID、25 个验收 ID、原始意图 O01–O11、Q01–Q29 和 I01–I05；只修改受新决定影响的语义，新增 Q30–Q48、FR-042～060、AT-26～44。原始 v0.3 文件独立保留，本文为合并后的完整基线。

| 修订主题 | 对应决定 | 主要落点 |
|---|---|---|
| 戏剧控制形态、柔性阶段与双尺度 | Q30–Q32 | 07.8～07.11、08.2／08.4、FR-042～044 |
| 因果自主世界与欲望理解 | Q33–Q34 | 04.8、07.12、10.6、FR-045～046 |
| 功能 Directive 与有意义推进 | Q35–Q36 | 07.10、10.7、FR-047～048；更新 FR-010、PM-02 |
| 真相、反转、伏笔与压力源 | Q37–Q39 | 07.12～07.14、10.5、FR-049～051 |
| Director 结局判断，而非门槛控制 | **Q40 B** | 04.6、07.7／07.16、10.9、FR-052；替换旧结局判断限制 |
| 愿望与合法退出结局 | Q41–Q42 | 04.3、07.15／07.16、FR-053～054 |
| 旧 Arc 关闭、新 Arc 续杯 | Q43 | 04.6、07.16、10.9、FR-055；更新完成率和 Demo |
| 双域提交与 Jev／LLM 分工 | Q44–Q45 | 07.9／07.17、10.8、11.7～11.9、FR-056～057 |
| 戏剧债务、机会仲裁与 AI 创作 | Q46–Q47 | 07.15、04.1、09.2、FR-058～059 |
| 玩家主观体验为主，不强制盲测／自动分数 | **Q48 A** | 16.5、17.3、FR-060、AT-44 |
| 与既有 Ready／计时／预算兼容 | I01–I05 + 新决定 | 02.4、07.12、12.8、FR-019／041 |

**明确未改变：** 图／声／视频三类素材完整支持；四个核心 Agent；本地／云端双后端及主路演示配置；动态 Top-K；所有显示的系统推荐必须 Ready；自由输入可 miss 并加载；普通交互不限时；Skill 以真实日志展示。

### 19.6 v0.5 修订记录与追溯

v0.5 完整继承 v0.4 的 O01–O11、Q01–Q48、I01–I05、FR-001～060 与 AT-01～44；新增 Q49–Q70、FR-061～082、AT-45～60，并修改模型候选、Top-K 并行、缓存、性能目标、Runtime Profile 与 Provider 容错的旧解释。

| 修订主题 | 对应决定 | 主要落点 |
|---|---|---|
| Lightning 本地 Director 与共享 Backbone | Q49、Q50、Q52、Q54 | 08.5、14.2、FR-061～063 |
| StepFun 固定职责 | Q51、Q65、Q69 | 08.5、14.2、14.4、FR-062／075／079 |
| 双 Pipeline／BranchContract／Jev First Pass | Q55、Q56 | 08.2、10.11、11.10、FR-065～066 |
| Hierarchical Context／ScenePacket | Q57、Q58 | 08.6～08.7、10.12～10.13、FR-067～068 |
| Top-K 全并行与 DAG | **Q59 B**、Q60 | 08.8、12.3、FR-069～070 |
| 两阶段 Canonicalization | Q61 | 08.9、12.10、FR-071 |
| 不先写 SLA | **Q62 A** | 16.3、FR-072 |
| 重试一次后 K-1 | Q63 | 12.9、15.1、FR-073 |
| Narrative／Director／Production fallback | Q64、**Q65 B**、Q69 | 14.2／14.4／14.6、FR-074／075／079 |
| 短 TTL Cache + Fingerprint | Q66、Q67 | 10.14、12.5／12.11、FR-076～077 |
| AGENT／VIDEO Profile | Q53、Q68 | 14.3／14.7、FR-064／078／081 |
| 统一 Provider Router | Q70 | 14.4／14.6、FR-080 |

**明确未改变：** 四 Agent 职责、Dynamic Drama Control、图／声／视频完整素材链、Ready-only Recommendation、Jev 不写剧情、H3 Max 主互动／Sol-H3 本地展示、Q48 的真人体验评价原则。


### 19.7 v0.6 修订记录与追溯

v0.6 完整继承 v0.5 的 O01–O11、Q01–Q70、I01–I05、FR-001～082 与 AT-01～60；先新增 O12、Q71–Q104、IMAGE-01、FR-083～102 与 AT-61～76，并在 2026-09-24 继续冻结 Q105–Q122、FR-103～114 与 AT-77～90。核心变化除跨 Scenario 角色资产系统外，还包括 AI 引导式创作、角色颗粒度统一、自然语言玩法作者界面和视频优先的沉浸式 Player。

| 修订主题 | 对应决定 | 主要落点 |
|---|---|---|
| Global Character 与三种创建入口 | Q71、Q92、Q94 | 04.9、06.5、FR-083～084 |
| Nano Banana 2 生图/编图 | Q73、Q79～081、IMAGE-01 | 13.8、14.2.1、FR-085～086／097 |
| Canonical 多视图 | Q72、Q74～075、Q97 | 10.15、13.8、FR-087／102 |
| Outfit 与身份保护 | Q76～078 | 06.5、10.15、FR-088 |
| Pose/Motion，不做固定表情库 | Q82～083 | FR-089、AT-67 |
| Character Version / Change Type | Q84～085 | 10.15、FR-090 |
| Snapshot、Local Override、反向保存全局 | Q86、Q103～104 | 10.15、FR-091、AT-69～70 |
| Voice 版本化 | Q87～088 | FR-092 |
| Reference Resolver 与多角色素材选择 | Q89～091 | 13.8、FR-093、AT-71～72 |
| Character Studio + Assets 双入口 | Q92～093 | 06.5、FR-094 |
| 非破坏资产状态 | Q80、Q101～102 | 10.15、FR-095 |
| AI 补全/Prompt 可见性/不自动重生 | Q98～100 | 06.5、FR-096 |
| 不显示单次费用/预算档 | Q95～097 | FR-102 |
| 标准/开发者、全局显示与响应式 | 用户后续明确要求 | 06.6、FR-098～100、AT-74～75 |
| 真实模型部署验收 | 用户后续明确要求 | 14.9、FR-101、AT-76 |
| AI 引导式戏剧结构与缺失追问 | Q105～108 | 04.10、06.7、FR-103～104、AT-77～79 |
| 角色库/Creator 统一颗粒度与 Scenario Overlay | Q109～112 | 04.9、06.5、10.16、FR-105～107、AT-80～81 |
| 自然语言玩法教程与 MechanicSpec 编译 | Q113～115 | 06.7、10.16、FR-108～109、AT-82～83 |
| 沉浸式 Player、全屏、Decision/Agency Dock、HUD | Q116～120 | 06.8、FR-110～112、AT-84～87 |
| Standard 错误隔离、字幕和媒体状态 | Q121～122 | 06.8、10.16、FR-113～114、AT-88～90 |

**明确未改变：** Ready-only Recommendation、自由输入可真实 miss、World/Drama 双域受控提交、两阶段 Canonicalization、H3 Max 主互动、Sol-H3 本地任务、Lightning/StepFun/Jev 路由与双 Runtime Profile。

### 19.8 2026-09-24 Creator / Player UX 冻结补充

本轮没有改变 World/Drama 双域提交、四 Agent 职责、Ready-only Recommendation、Top-K、Character Snapshot 或 Mechanic Skill 的底层架构；修改的是“用户如何与这些结构交互”。

统一原则是：**创作端隐藏机器需要的结构，游玩端隐藏机器正在运行的过程。** Standard Creator 从“空白结构化表单”转成 AI 当前理解、缺失追问、建议卡和自然语言修改；Standard Player 从“Runtime Debug UI + 视频”转成视频优先的 Immersion/Decision/Agency/HUD 四层播放器。Developer Mode 继续保留完整 Schema、JSON、ID、Provider、Trace、精确关系值和原始错误，因此本轮不是删除可审计能力，而是建立正确的信息层级。

角色库与 Creator 的差异只允许来自作用域：前者编辑 Global Character Core，后者编辑 Scenario Snapshot/Overlay；不得再因页面入口不同而拥有不一致的角色定义颗粒度。玩法机制同理：Standard 显示可理解的游戏教程规则，Runtime 仍使用受验证的 MechanicSpec。

**Q116 修订说明（USER，2026-09-24）：** “沉浸模式”不是浏览器 Fullscreen API。用户明确要求视频画面在应用内尽可能占满主视图，选项位于视频下方第二层，自由输入位于最底层，背包/关系/线索/Wish 通过视频左上角弹出 HUD 查看。浏览器全屏仅保留为附加能力；此前“PlayerShell requestFullscreen 即代表沉浸模式完成”的解释被本修订覆盖。

### 19.9 本轮没有自动加入的产品要求

没有强制“每个节点都展示欲望副标题”，没有把所有自由输入变成二次确认，没有禁止在普通节点许愿，没有规定篇章必须 12 或 16 个 Beat，没有以 Drama Debt 代替 Director 自动结局，没有要求第五个 Agent，也没有以另一种名称偷偷加入 Q48 C 的盲测／开关对照／自动戏剧总分。

字段、枚举、时钟推进细节、样本范围和具体阈值仍是可验证的实现设计。若后续证据表明需要修改，保留来源、影响范围与用户确认记录；不能把尚未验证的选择包装成已实现效果。

## 20. 外部依据与核验范围

以下 S01–S22 继承 v0.4 的既有核验记录；S23–S25 于 2026 年 9 月 21 日为 v0.5 模型／运行时决策补充核验；S26–S27 于 2026 年 9 月 23 日核验 fal.ai Nano Banana 2 文生图与 Edit API。引用不代表本项目已完成部署、中文质量或 SLA 验证。引用不证明本项目已接入或达到性能；实施前仍应保存访问快照、提交哈希或版本。

| 来源 | 一手资料 | 支撑范围与限制 |
|---|---|---|
| S01 | fal：Introducing H3 Max | H3 Max 定位及官方展示的 2.78 秒样例；不是本应用 SLA |
| S02 | MiniMax：视频生成指南 | H3／H3 Max 模式、参考素材限制与异步任务流程 |
| S03 | fal：H3 Max reference-to-video API | 三类参考字段、任务、扩展选项及部分计时字段 |
| S04 | NVIDIA Research：Sol-H3 Spark | 特定 Spark 配方、热态约 56 秒和内存口径；非同驻 LLM 测试 |
| S05 | TypeSafe：API Reference | Jev 类型化问题与答案接口，候选由调用方定义 |
| S06 | TypeSafe：Models | 模型版本、文本输入、语言注意事项与别名风险 |
| S07 | TypeSafe：Confidence | 概率分布与 confidence 的区别、阈值需按任务验证 |
| S08 | StepFun：Chat Completions API | StepFun 文本／工具调用接口与参数参考 |
| S09 | Agent Skills：Specification | SKILL.md、目录结构、元数据及渐进加载 |
| S10 | MiniMax-AI：h3-prompt-writing | 官方 H3 Prompt Skill 的模式、参考映射和可复用工作流 |
| S11 | NVIDIA：DGX Spark 产品规格 | 统一内存、Arm CPU 等硬件规格；不作为本应用基准 |
| S12 | NVIDIA：Nemotron on DGX Spark | 官方本地模型服务部署路线；不证明与 Sol-H3 共驻 |
| S13 | LangChain：LangGraph Overview | 有状态编排、持久化和确定性／Agent 步骤混合 |
| S14 | NVIDIA：NeMo Agent Toolkit Overview | 工作流、观测与集成；是否采用仍是建议 |
| S15 | FastAPI 官方文档 | Web API 框架能力与用法，不证明本应用性能 |
| S16 | Pydantic 官方文档 | 数据类型与验证工具，不替代业务语义检查 |
| S17 | FFmpeg Filters 官方文档 | 媒体过滤、音视频处理和拼接基础能力 |
| S18 | OpenTelemetry：Traces | 可观测性中的 trace／span 组织概念 |
| S19 | React 官方 Quick Start | 组件化前端实现基础；不表示 UI 已实现 |
| S20 | NVIDIA英伟达中国发布的第三届活动说明 | 公开日程、完整 Agent 应用与 Skills 方向；未取得完整评分细则 |
| S21 | StepFun：Step 3.7 Flash | 多模态理解、工具调用和推理选项；编剧效果待测 |
| S22 | PostgreSQL：Transactions | 事务的原子提交基础；幂等仍需应用实现 |
| S23 | NVIDIA：Nemotron 3.5 Lightning 30B-A3B Model Card | 30B／3B active、1M context、agentic 定位及主支持语言；不证明中文剧情规划已达标 |
| S24 | NVIDIA NemoClaw：单 DGX Spark Nemotron 3.5 Lightning vLLM Profile | 单 Spark 实验 profile、资源边界和特定验证吞吐；不是本项目 SLA |
| S25 | StepFun 开放平台：Step 5 Preview／模型入口 | 当前 Step 5 Preview 作为前沿模型入口及统一 API 平台；实际模型 ID／配额以账号为准 |

v0.3 记录：当时官方活动报名页未能打开，赛事信息引用 NVIDIA 官方账号活动说明，而非其他届规则。本轮没有重新检查该页面，也没有对真实 API 发请求、连接 Spark、测试模型效果或价格。新增戏剧控制部分是需求与实现设计，不是实验报告。

| S26 | fal.ai：Nano Banana 2 Text-to-Image API | fal-ai/nano-banana-2 endpoint、num_images、文件/队列与输出结构；价格与限制会变化，不作为永久常数 |
| S27 | fal.ai：Nano Banana 2 Edit API | fal-ai/nano-banana-2/edit、image_urls 多参考输入与文件传递；实际角色一致性仍需项目样本验证 |

### 20.1 给 AI 开发代理的结束检查

提交代码或宣称完成前检查：

1. 是否逐项保留 Q01–Q122、I01–I05，尤其 Q40 B、Q48 A、Q59 B、Q62 A、Q65 B，以及 Q71–Q104 的 Character Studio 决策；USER、DERIVED、PROPOSED 是否明确分开。
2. 图／声／视频三类参考是否真实消费，四 Agent 与双后端是否有真实执行证据。
3. 自由输入是否保留原意；小动作可轻反馈，关键计划外行动是否仍能产出新视频；欲望不确定时是否适度澄清。
4. World／Drama／Arc 是否有合法版本、来源和幂等提交；未选分支是否污染事实、伏笔、Wish、债务或玩家知识。
5. 反转是否引用已存在且已经呈现的证据，是否偷改真相；阶段／Progress 是否被用来强拉玩家回固定主线。
6. 世界压力是否有已建立的因果；UNTIMED 思考或模型等待是否被错误计为角色不行动；TIMED 是否使用确定性 fallback。
7. 所有已显示系统推荐是否真的 Ready；Drama 或 Wish 更新后旧候选是否正确撤回；是否以文本 Ready 偷换原视频 Ready 承诺。
8. Director 是否真正拥有结局时机判断；是否存在强制 Ending Readiness 阈值／固定轮数；退出矛盾是否允许真实后果结局。
9. 续杯是否经玩家请求与预算检查；新 Arc 是否继承真实历史并保护旧结局，未发生投机未来是否被错误带入。
10. 戏剧效果是否有真实玩家反馈；是否把自动分数、字段完整或工程测试通过假称为“用户觉得好玩”；是否偷偷引入必做盲测或开关对照。
11. Skill 日志、模型来源、费用、资源冲突和错误是否真实；是否把未运行 AT 写成通过。
12. 是否保留已知限制及负反馈，避免宣传无条件实时、全离线、无限续玩不耗资源。
13. Director 是否真实使用本地 Lightning；Narrative／Authoring／Production 是否按固定 Provider 路由；fallback 后来源是否正确标注。
14. Ready 推荐点击是否复用 BranchContract；Top-K 是否在锁 K 后真实并行；失败是否只重试一次后 K-1。
15. Director 是否用 Hierarchical Working Context；Narrative 是否只看 ScenePacket，未泄漏禁止信息。
16. SELECTED provisional 与 CANONICAL 是否区分；回滚是否取消／标记依赖 N+2 任务且不污染正式状态。
17. Branch Cache 是否使用短 TTL 与 Dependency Fingerprint；是否存在 LLM 凭相似感觉错误复用。
18. AGENT_LOCAL／VIDEO_LOCAL Profile 是否真实切换；VIDEO_LOCAL 下是否错误把已卸载 Lightning 当作 fallback。
19. 是否完整记录实际性能而没有把 NVIDIA／厂商 benchmark 或旧 P95 建议冒充项目 SLA。

20. Character Studio 是否真正执行 Nano Banana 2 生图/Edit；2 候选、Canonical、多视图、Outfit、Pose/Motion、Voice、Version/Snapshot 是否有真实工件而非静态字段。
21. Scenario 是否只消费 Character Snapshot；Global Character 新版是否会错误污染旧 Scenario；Local Override 与“保存为全局新版本”是否可追踪。
22. Production Reference Resolver 是否把真实选中的角色 image/voice/motion refs 发送到 H3；是否存在 generic references 在 Provider Adapter 中被静默忽略。
23. Standard/Developer、Appearance/UI Size/Subtitle 是否真实生效；1080p/2K/4K 是否在 100% Zoom 可用，而不是靠浏览器 150%。
24. Lightning、Step 3.7、Step 5、Jev、H3 Max、Sol-H3 是否有真实部署/调用证据；Profile 切换是否真的启停服务与释放资源。
25. Standard Creator 是否仍以空白 DramaSpec/Character/Mechanic Schema 要求用户手填；若是，则未满足 Q105～115。
26. AI 是否只追问真正缺失或高影响不确定项，并提供上下文相关建议与自由修改，而不是机械逐字段问卷。
27. Character Library 与 Creator 的角色信息架构是否一致；Scenario Desire/Fear/Secrets/Knowledge/Relationships/Visual State 是否错误回写 Global。
28. Standard 玩法是否是自然语言教程卡；任意用户自然语言是否先编译/验证成 MechanicSpec，而不是直接执行 JSON/代码。
29. Player Theater Mode 是否在不依赖浏览器 Fullscreen 的情况下隐藏 Sidebar/应用级 Header、让 Stage 占据主要视口，并保持 HUD 左上、Ready 推荐位于 Agency 输入之上、自由输入固定最底层；Browser Fullscreen 是否只作为二级可选功能且不破坏这些层。
30. 背包/关系/线索/Wish 是否进入可隐藏 HUD；Standard 是否避免把精确关系数值、Branch/Provider/Inspector 暴露为主要玩法。
31. Player 是否区分 Generating/Loading/Failed；中文字幕是否无乱码；Pydantic/Python 原始错误是否只存在于 Developer Trace。

**产品价值由可玩的体验证明：玩家作出系统未预制的行动，世界记住它，故事在因果约束下回应并推进；该收束时能自然结束，玩家愿意时可以继续这个世界。**

### 20.2 本轮直接依据与文档身份

| 本地来源 | 使用方式 | 权限边界 |
|---|---|---|
| `Agent_Skills_Interactive_Drama_PRD_AI_v0.5.md` | 完整继承 O01–O11、Q01–Q70、I01–I05、FR-001～082 与 AT-01～60 | v0.6 在其上增量冻结角色资产系统、显示/响应式与真实部署验收；Git blob `68aa819dc85803b894b68ff7abc34c4518b675ff` |
| `199e7ecc-c52b-4d09-852b-378d8637b4b8.md`：《AI 原生互动短剧 PRD 产品修改建议》 | 动态戏剧结构、有意义推进、欲望、反转和收束的动机来源 | 是讨论稿；其中入口限制、确认频率等未被选择的内容不自动成为要求 |
| 当前对话 Q30–Q48 的问题、选项、最终选择及括号补充 | 本轮 USER 决策来源，02.3 保留完整选择记录 | 用户最终选择优先于助手推荐与示例；Q40 为 B，Q48 为 A |
| 当前对话 Q49–Q70 及后续“Lightning 本地作为 Director”明确锁定 | v0.5 USER 模型／Runtime 决策来源，02.5 保留最终选择 | 用户后续直接锁定优先于此前候选／benchmark 建议；Q59 为 B、Q62 为 A、Q65 为 B |

| 当前对话 Q71–Q104 与“fal.ai Nano Banana 2 统一生图/编图”明确锁定 | v0.6 USER Character Studio 决策来源 | 用户最终选项优先于助手推荐；Q82=A 不做固定表情资产库，Q95/Q96=A 不显示费用/预算档 |
| 当前项目对全局角色库、Standard/Developer、Appearance/UI Size/Subtitle、100% Zoom 与模型部署检查的明确要求 | v0.6 产品/验收补充 | 不得把原型已有交互在正式 React 中缩水；模型部署以真实服务器证据为准 |
| 2026-09-24 连续三轮产品讨论：戏剧结构追问、角色/玩法颗粒度、沉浸式 Player | v0.6 Q105–Q122 USER 决策来源 | Standard Creator 隐藏机器结构、Standard Player 隐藏机器运行过程；Developer 保留全部可审计工件 |
| 2026-09-24 对 Q116 的后续澄清：应用内 Theater Mode ≠ Browser Fullscreen | v0.6 Q116 / FR-110 / AT-84 覆盖性修订 | Theater Mode 隐藏应用导航并占满主视图；视频→推荐→自由输入层级稳定；浏览器 Fullscreen 降为二级可选功能 |

本次文档加工读取了以上两份本地 Markdown 全文。源文件指纹用于核对基线，不代表模型能力或工程实现通过测试。

```text
baseline_v0.4_sha256:
  44463bc9d8d543f6e99792bcfbc07201b2ab3b5709961590b7b11db5c6d850b1
teammate_draft_sha256:
  ac02be7624b1daf8ee1f05af76ecb8fde1558ac2ddf72363d419b1bed530ac46
```

文档状态：**Q01–Q122 与 v0.6 Character Studio / AI-guided Creator / Natural-language Mechanics / Immersive Player / Image Router / Responsive / Deployment Verification 需求合并完成；实现状态不得从本文推断，须以代码、线上部署、真实 Provider/本地模型证据与 AT-01～90 为准。** 后续实现和审阅以本 v0.6 Markdown 为需求权威基线。

[S01]: https://fal.ai/learn/devs/introducing-h3-max-by-fal
[S02]: https://platform.minimax.cn/docs/guides/video-generation
[S03]: https://fal.ai/models/minimax/h3-max/reference-to-video/api
[S04]: https://nvlabs.github.io/Sana/Sol-Engine/Sol-H3-Spark/
[S05]: https://docs.typesafe.ai/api
[S06]: https://docs.typesafe.ai/models
[S07]: https://docs.typesafe.ai/confidence
[S08]: https://platform.stepfun.com/docs/zh/api-reference/chat/chat-completion-create
[S09]: https://agentskills.io/specification
[S10]: https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/SKILL.md
[S11]: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
[S12]: https://build.nvidia.com/spark/nemotron
[S13]: https://docs.langchain.com/oss/python/langgraph/overview
[S14]: https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html
[S15]: https://fastapi.tiangolo.com/
[S16]: https://pydantic.dev/docs/validation/latest/get-started/
[S17]: https://ffmpeg.org/ffmpeg-filters.html
[S18]: https://opentelemetry.io/docs/concepts/signals/traces/
[S19]: https://react.dev/learn
[S20]: https://www.toutiao.com/article/7681559874408464939/
[S21]: https://platform.stepfun.com/docs/zh/guides/models/step-3.7-flash
[S22]: https://www.postgresql.org/docs/current/tutorial-transactions.html
[S23]: https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard
[S24]: https://docs.nvidia.com/nemoclaw/user-guide/deepagents/inference/local-inference/set-up-vllm
[S25]: https://platform.stepfun.com/


[S26]: https://fal.ai/models/fal-ai/nano-banana-2/api
[S27]: https://fal.ai/models/fal-ai/nano-banana-2/edit/api
