# Latest PRD UX Acceptance · PRD v0.6

日期：2026-09-25。总体结论：**PARTIAL**，不宣称全量 PRD 完成。

- 需求/起始 SHA：`881dd66cb8585b51c0a3c8ff5c47160a000c737c`。
- **Final SHA（最终应用代码候选）：`461a3d3ba946720a864cd9278e9acdd74eb3b6e1`**。
- 最后的交付提交只归档报告、截图、原始证据；交付 SHA 以 main 最新提交和交付回复为准。应用代码树保持与上述候选一致。
- 修改前审计：[GAP_AUDIT.md](docs/acceptance/prd_v06_latest/GAP_AUDIT.md)。下表是修改后结果，不能用审计中的“已实现”替代运行验收。
- Backend：**60 passed / 0 failed / 0 skipped / 6 warnings，124.62秒**；命令 `PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false pytest tests/ -q`，见[原始日志](docs/acceptance/prd_v06_latest/backend_pytest.log)。
- Frontend：`npm ci && npm run build`，TypeScript + Vite 6.4.3，41 modules，exit 0；CSS 25.82 kB，JS 266.89 kB。见 [构建日志](docs/acceptance/prd_v06_latest/frontend_build.log)。

## 验收环境与证据边界

正式 React 构建 + FastAPI，独立 SQLite 验收库 `/tmp/interaction-latest-live.db`，`PROVIDER_MODE=live`、`PROFILE_LIFECYCLE_ENABLED=false`、`PROVIDER_TIMEOUT_SECONDS=120`。本轮不重做已确认的模型部署/Profile往返。Nemotron 使用现有 DGX 服务；Step 使用 `https://api.stepfun.com/step_plan/v1`，密钥未更改。

Firefox 156.0.1 实际支持 H.264/AAC。本机 Playwright Chromium 缺这两个解码器，其黑屏不计入产品播放PASS。35项响应式检查覆盖五档分辨率×五页，另在1920×1080检查大/特大，浏览器缩放均为1。截图见 [证据目录](docs/acceptance/prd_v06_latest/)。

原始live故事使用900秒分支TTL以便长时间人工/浏览器检查。Lead/Ready、媒体传输错误与最终全屏细查使用**隔离Session回放已生成的真实H3缓存**，延长该夹具过期时间并恢复原始正式状态；没有声称发生新的Provider生成。AT-88在真实Nemotron响应后明确注入错误，不是自然模型故障。所有这些范围均记录在对应JSON中。

## Q105–Q122 实现状态

| Q | 状态 | 实现与运行证据（均在证据目录） |
| --- | --- | --- |
| Q105 | IMPLEMENTED | 先展示 AI 当前理解，Proposal 独立保存，确认后才写 DramaSpec；`at77_79_browser.json` |
| Q106 | IMPLEMENTED | 戏剧结构改为故事深化工作流，保留同一正式 DramaSpec；`at77_79_browser.json` |
| Q107 | IMPLEMENTED | 真实 Step 5 生成上下文建议和自由回答；详细描述不重复追问；`live_vague_authoring.json / at78_81_browser.json` |
| Q108 | IMPLEMENTED | 五类自然语言主题；高级戏剧字段在 Developer 中编辑；`ai_guided_drama.png / developer_drama.png` |
| Q109 | IMPLEMENTED | Library 与 Creator 共用七组 CharacterProfile；`character_library.png / creator_character_overlay.png` |
| Q110 | IMPLEMENTED | Global 最低名字与一句话定义；其余可选/AI 建议；`global_ai_browser.json` |
| Q111 | IMPLEMENTED | 固定 Global 版本和故事 Overlay，显式 Promote 才升级全局；`at78_81_browser.json` |
| Q112 | IMPLEMENTED | 真实 AI 角色理解→用户确认→版本写入；`global_ai_understanding.json / global_ai_browser.json` |
| Q113 | IMPLEMENTED | Standard 玩法是教程卡，不出现 JSON 参数框；`natural_language_mechanics.png` |
| Q114 | IMPLEMENTED | 真实自然语言编译→Schema/权限校验→Typed Config→Runtime Skill；`live_mechanics_proposal.json / live_mechanic_execution.json` |
| Q115 | IMPLEMENTED | 规则卡可调整/移除/添加；Developer 可查 Skill/version/config/trigger/permissions；`developer_mechanics.png` |
| Q116 | IMPLEMENTED | 整个 PlayerShell fullscreen，保留所有互动层；`final_player_checks.json` |
| Q117 | IMPLEMENTED | 视频、Ready 推荐、持续自由输入、HUD 四层；`normal_player.png / fullscreen_ready_layers.png` |
| Q118 | IMPLEMENTED | 服务端 Lead + Ready Gate；推荐在输入上方，选中收起；`lead_ready_replay_validation.json` |
| Q119 | IMPLEMENTED | 推荐存在和 TIMED 期间均保留输入，接受后锁重复提交；`firefox_player_validation.json / timed_countdown.png` |
| Q120 | IMPLEMENTED | HUD hover/pin/unpin；Standard 定性、Developer 精确值；`final_player_checks.json / hud_relationship_qualitative.png` |
| Q121 | IMPLEMENTED | Standard 安全错误；Developer 保留完整原始异常；`schema_fault_browser.json` |
| Q122 | IMPLEMENTED | 标题淡出、Unicode 字幕、三种媒体状态、有限 Schema 修复/重试；`final_player_checks.json / media_state_validation.json` |

## FR-103–FR-114

| FR | 结果 | 覆盖 | 证据 |
| --- | --- | --- | --- |
| FR-103 | PASS | Q105–108 | AT-77/78 |
| FR-104 | PASS | Q106–108 | AT-79 |
| FR-105 | PASS | Q109–111 | AT-80 |
| FR-106 | PASS | Q110–112 | AT-80/81 + global_ai_browser.json |
| FR-107 | PASS | Q111 | AT-81 |
| FR-108 | PASS | Q113–114 | AT-82 |
| FR-109 | PASS | Q113–115 | AT-83 |
| FR-110 | PASS | Q116–117 | AT-84 |
| FR-111 | PARTIAL | Q117–119 | AT-85/86 |
| FR-112 | PASS | Q120 | AT-87 |
| FR-113 | PASS | Q121 | AT-88/90 |
| FR-114 | PASS | Q122 | AT-88/89/90 |

## AT-77–AT-90

13 PASS / 1 PARTIAL / 0 FAIL / 0 BLOCKED。PASS 限于各条判据，不外推为外部生图或全视频结局已完成。

| AT | 结果 | 实测 | 证据（目录内） |
| --- | --- | --- | --- |
| AT-77 | PASS | 真实 Step 5 生成当前理解与三组上下文问题，React 选择建议并正式写入；锁/过期/非法路径由回归验证。 | `at77_79_browser.json` |
| AT-78 | PASS | 明确真相/冲突/压力的描述没有重复问题（explicit_questions=0）。 | `at78_81_browser.json` |
| AT-79 | PASS | React 确认 truth_model 后 Changes 留 Before/After/source/time，Developer 显示同一值。 | `at77_79_browser.json` |
| AT-80 | PASS | 同一角色使用七组信息架构；Creator 绑定固定全局版本，故事作用域可见。 | `character_library.png / creator_character_overlay.png` |
| AT-81 | PASS | Desire/Secret/Visual State 修改后 Global 不变；点击 Promote 后才产生全局版本，已发布快照继续固定。 | `at78_81_browser.json` |
| AT-82 | PASS | 真实 Step 5 编译并发布三类玩法；真实 Jev/Nemotron 行动重试调用 relationship Skill 1.0.0，正式关系写入55，World version仅增加1。该次呈现为用户选定的文字模式。 | `live_mechanics_proposal.json / live_mechanic_execution.json` |
| AT-83 | PASS | Standard 教程卡无 JSON；Developer 查同一 Typed Config/Skill/trigger；确认与手动编辑共用校验。 | `natural_language_mechanics.png / developer_mechanics.png` |
| AT-84 | PASS | Firefox 实际 fullscreenElement=player-shell，真实视频、字幕、HUD、三个Ready和输入均在容器内。 | `final_player_checks.json` |
| AT-85 | PASS | 真实 H3 缓存回放：Lead 前 API recommendations=[]，到达后3条Ready可见，React 位于输入上方；点击后CANONICAL。不是新生成证明。 | `lead_ready_replay_validation.json` |
| AT-86 | PARTIAL | 本轮早期React存在三条真实Ready时自由输入，真实FREE H3分支br_00136_383b8e已CANONICAL。最后的Director/关系修复后只重跑真实文字FREE与离线回归；fal锁阻止再次完成新FREE视频，故不以较早视频证明最终候选全部通过。 | `firefox_player_validation.json / live_play_state.json` |
| AT-87 | PASS | Firefox hover/pin/unpin；背包/关系/线索/愿望；已写入的关系在Standard显示定性文字、Developer显示数值。 | `final_player_checks.json / live_mechanic_execution.json` |
| AT-88 | PASS | 真实Nemotron调用后，隔离测试装置明确注入target_changes=42；一次schema retry后FAILED_RECOVERABLE。Standard无原始错误，Developer可查，World不变。 | `schema_fault_browser.json` |
| AT-89 | PASS | Firefox真实H.264/AAC播放；中文场景/人物/字幕截图检查；标题淡出；画内与画外字幕可读。 | `final_player_checks.json / unicode_subtitle_bottomInside.png / unicode_subtitle_bottomOutside.png` |
| AT-90 | PASS | 实际生成画面、真实MP4的HTTP延迟/503分别形成Generating/Loading/Failed；重新载入播放成功，文字恢复不重复提交。 | `media_state_validation.json / player_generating.png` |

`firefox_player_validation.json` 中前五项分别为真实播放、AT-84/87/85/86的成功记录；最后一次查找 Inspector 按钮的早期脚本失败被保留。Inspector 的最终结果以 `schema_fault_browser.json`、`final_player_checks.json` 为准，不把整个早期脚本说成成功。

## 完整用户路径

| 阶段 | 结果 | 本轮证据与限制 |
| --- | --- | --- |
| 新故事与AI当前理解 | PASS | 新“灯塔失踪案”；真实Step 5、React建议选择、正式Drama写入、Changes与锁校验 |
| 创建/绑定角色 | PASS（文字与上传基线） | 林岚全局角色、真实AI理解；现有真实fal图片作为明确上传基线；固定v2并发布Snapshot/Production refs。未声称本轮新生成Nano Banana图片 |
| 自然语言玩法与Runtime | PASS | 已发布Typed Config被Director读取，真实relationship Skill→Proposal→World版本变化，见live_mechanic_execution.json |
| Publish / Snapshot | PASS（成功路径） | scn_00009_1cba84，ver_00003_222069 / 0.1.0；严格Gate失败组合由离线回归覆盖，非全部真实Provider负例复测 |
| Opening / autoplay | PASS | scene_00020_a1a8f6，真实两Shot H3、FFmpeg、Firefox播放；首幕失败后由React重试成功 |
| Lead / Ready选择 | PASS | 服务端Gate与真实缓存重放选择→PROVISIONAL→CANONICAL，未选择分支不写正式状态 |
| Free / Jev / Director / Narrative / H3 | PARTIAL | br_00136_383b8e→scene_00161_f1d16f是本轮真实FREE视频；最终Director/关系修复后文字FREE通过，新视频未重跑 |
| Intent Echo / Clarification | PASS | 真实Jev低置信行动先确认，React确认后继续；live_mechanic_execution及前一请求保留原文/观察/确认事件 |
| TIMED | PASS（超时路径） | 真实倒计时和预声明fallback；手动选择完整路径的回归在离线测试中，未新增全视频实测 |
| Provider / Schema / 传输失败 | PASS | 真实首幕失败后重试成功；fal拒绝后文字恢复；Nemotron响应故障注入；真实MP4的HTTP503恢复；提交拒绝亦进入FAILED_RECOVERABLE |
| 视频Ending | BLOCKED | fal请求01a0d481-3949-7f32-8d42-0ffed6de7010：403，User is locked. Reason: TOP_UP. |
| 文字Ending / Continue World | PASS | 用户显式文字继续→text SceneArtifact→原有双阶段提交→Arc关闭；真实Step继续生成Arc2，继承事实，保留旧Arc |
| 全程视频E2E | PARTIAL | 结局视频受外部账单锁阻塞；文字恢复不计作视频成功 |

## 本轮无费用安全回归（2026-09-25）

见 [NO_COST_E2E_ACCEPTANCE.md](NO_COST_E2E_ACCEPTANCE.md)。`FAL_PAID_GENERATION_ENABLED=false`，本轮新增 Fal paid 请求为 0；Billing Locked 熔断与图片/视频 resolution 参数链已验证。充值后的三组真实媒体验收继续保持 PARTIAL/BLOCKED。

真实H3证据生成于本轮实现提交f4c5f29；最终候选的媒体提交/拼接代码相同，后续Director提示与关系初始化修复以真实文字路径和完整回归验证。没有声称在最后一次提交后新增fal视频。

真实Opening视频：[real_h3_opening.mp4](docs/acceptance/prd_v06_latest/real_h3_opening.mp4)。1344×768、H.264/AAC、10.400秒、2,829,853字节。独立H3 request IDs：`01a0d467-f124-7a53-ac75-3148b59314e1`、`01a0d467-f0ff-7933-8c30-bfeae6b9ae63`。各Shot的prompt/references/submit/completion/clip/时长及concat输入顺序见 `real_h3_opening_provenance.json`；本次不将fallback计作真实H3。

## 本轮必要修复

- Authoring Proposal独立于正式数据，确认时核对锁、允许路径与旧值；长请求完成后合并最新草稿，不覆盖并发编辑。
- Step Plan上的Step 5在强制JSON response_format下实测输出损坏；该模型采用明确JSON提示、服务端严格校验和一次修复重试。保留实际对照与失败输出。
- 发布时使用绑定的Global版本及本故事Overlay；修正“继续旧版本”误升级。Character文本修改不触发生图。
- FREE沿用已接受的Director计划；Ending强制完整呈现；Narrative无效输出不能用泄露真相的premise冒充结果。
- 修正Opening泄露为推荐、TIMED在Lead前开始计时、空异常字符串被当成功、参考图双重 `/files/` 前缀。
- 自然语言关系不再依赖“信任42/100”内部写法：已声明NPC的未指定数值采用中性50（实现默认，不从文字推断信任）；显式数值保留。旧Session首次关系变化经Skill提案初始化，未选分支不提前改状态。真实失败/修复/重试留证。
- World提交拒绝进入FAILED_RECOVERABLE并保留原始原因；文字恢复使用明确text artifact，不伪造MP4、不重复提交、不绕过StateManager。

## Remaining P0 / P1

- P0 / BLOCKED：恢复fal账户额度后补视频Ending及后续全视频连续游玩；已有403证据，未继续重复计费请求。
- P0 / PARTIAL：Nano Banana新建双Candidate、多视图与非破坏编辑完整真实浏览器流程本轮未重跑。不要把复用真实上传基线当成新生图。
- P1 / PARTIAL：本轮没有全面重跑AT-01–76全部语义/边界/多模态验收；见当前矩阵及历史存档。真实用户反馈仍待独立体验者。
- 非Gap：公网服务与Nemotron部署已经确认；本轮不以重复部署替代UX验收。

- 运维P1：生产库有2条旧standalone生成记录和2个旧Session的中断分支（约28小时以上未更新），对应旧验收任务；本轮只保留原记录，不用改enum伪造完成。新Session验收与它们隔离。
