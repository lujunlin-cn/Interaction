# 验收矩阵 · AT-01–AT-98

需求基线：PRD v0.6 / `b055674aa0702fc1c1ed50f7c3ee62e4ea43dc88`。
最新应用代码候选：最新交付提交（见 `git rev-parse HEAD`）。详细证据：[LATEST_PRD_UX_ACCEPTANCE.md](LATEST_PRD_UX_ACCEPTANCE.md)。

当前矩阵统计（历史证据与下述新增角色 Scope 证据分开）：**PASS 42 / PARTIAL 55 / BLOCKED 1 / FAIL 0**。
其中本轮重点 AT-77–90：13 PASS / 1 PARTIAL；本轮新增 AT-91–98：8 PASS。PARTIAL包含本轮未完整复测项，不表示已确认的部署能力丢失。

历史“55 PASS / 20 PARTIAL / 1 BLOCKED”已移入[历史存档](docs/acceptance/prd_v06_latest/AT01_76_HISTORICAL.md)，不再充作最新HEAD结果。历史Sol-H3/Profile真实证据保留在FINAL_E2E_ACCEPTANCE.md和PROFILE_SWITCH_ACCEPTANCE.md；本轮没有重复模型部署或Profile切换。

判定：PASS需要实际触发、正式状态/Artifact、Trace、正常与关键失败路径证据；PARTIAL表示有实现/部分验证但不足以完整关闭；BLOCKED有明确外部原因；FAIL表示实测实现不符合。离线pytest验证确定性契约，不能证明真实Provider。缓存回放与故障注入均显式标识。

历史无费用复验见 [NO_COST_E2E_ACCEPTANCE.md](NO_COST_E2E_ACCEPTANCE.md)。2026-09-25 新增的角色 Scope A–F 浏览器回归独立使用 mock / Fal Guard OFF，付费媒体请求 0；不代表正在进行的真实 FULL E2E 总请求为 0。完整付费验收与计费记录以 BIOHAZARD_FULL_E2E_ACCEPTANCE.md 为准。当前图片 Relay 是 USER-approved cost optimization；该轮图片必须走 Relay，Fal 仅用于 H3。

2026-09-25 最终整合回归：**Backend 197 passed / 0 failed / 6 warnings**（mock providers、Fal Guard OFF、lifecycle disabled）；`compileall` / `pip check` / `npm ci` / frontend build PASS。9000服务已重启，JS/CSS实际响应与最终dist逐字节/SHA-256一致；`docs/acceptance/biohazard_full_e2e/deployment_final.json`。当前生化危机故事已通过真实 Standard UI 参数复查、显式审阅与发布 **v0.2.0**（`ver_00001_b26e3c`）；角色 pin 为 Leon v8 / Claire v7 / Victor v7。其 FULL E2E 仍为 **PARTIAL**：Relay 已生成三角色共 10 张 4K Candidate 证据，但标准视图、Outfit 编辑未完成，无成功 H3 视频；不得借历史缓存或上述离线测试提升真实 Player 验收状态。详见 [BIOHAZARD_FULL_E2E_ACCEPTANCE.md](BIOHAZARD_FULL_E2E_ACCEPTANCE.md)。

| AT | 用例 | 最新判定 | 本轮证据/限制 |
| --- | --- | --- | --- |
| AT-01 | 输入新设定，审阅 AI 草案并局部修改角色 | PASS | 真实Step故事→确认→正式字段；at77_79_browser.json |
| AT-02 | 上传图片/声音/动作参考视频并绑定 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-03 | 同一次生成混用图、声、视频 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-04 | 播放中等待推荐，再点 READY 候选 | PASS | 真实H3缓存、服务端Lead、React选择→CANONICAL；lead_ready_replay_validation.json |
| AT-05 | 无对应候选的自由输入形成新意图 | PARTIAL | 真实FREE H3分支；live_play_state.json，br_00136_383b8e  最后Director/关系修复后真实文字FREE通过，但fal锁阻止最终候选新FREE视频重测。 |
| AT-06 | 现实世界不可能的道具/行为 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-07 | 提交「希望她最终不要死」类 Wish | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-08 | 更新 Wish/Drama/素材后旧分支撤回 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-09 | 非法字段/过期版本/重复提案 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-10 | 多分支生成但只选一条 | PASS | 真实缓存选择正式提交；未选分支隔离的双域回归通过 |
| AT-11 | 多 Shot Beat 生成装配 | PASS | 本轮Opening两个独立H3 Job + FFmpeg；real_h3_opening_provenance.json |
| AT-12 | 命中机制事件后状态与 UI 更新 | PASS | 真实relationship Skill 1.0.0→状态55→定性HUD；live_mechanic_execution.json |
| AT-13 | Director 在不同历史下形成不同结局 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-14 | Jev 超时/错误/低置信降级 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-15 | Full Beat 生成/装配失败恢复 | PASS | 首幕真实失败重试、文字恢复、HTTP媒体故障及回滚恢复留证 |
| AT-16 | 刷新/双击/重复回调幂等 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-17 | 达到预算不再新增超额任务 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-18 | Spark 真实提交 Sol-H3 任务 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-19 | 一轮 Skill trace 可追到版本/工具/状态 | PASS | 真实Skill Trace含版本/触发/Proposal，Canonical状态可查；live_mechanic_execution.json |
| AT-20 | 检索不泄露隐藏剧情/密钥/投机未来 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-21 | Decision Lead Window 提前出现 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-22 | UNTIMED 未选择不自动推进 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-23 | TIMED 超时执行预声明 fallback | PASS | 真实TIMED超时fallback；live_timed_timeout.json |
| AT-24 | 连续行为更新偏好供 Jev | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-25 | 部分 Ready 部分渲染不显示未就绪 | PASS | READY缓存仍在Lead前被服务端隐藏；lead_ready_replay_validation.json |
| AT-26 | 行动→观察→Drama 更新有类型化记录 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-27 | 探索期合法提前揭关键问题 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-28 | 小动作/关键行动/完整 Beat 分层 | PASS | 轻量查看QUICK_ACK与后续FREE H3、Ending完整呈现对照 |
| AT-29 | UNTIMED 久留不惩罚；「等一小时」按规则 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-30 | 明示动机不被偏好覆盖；歧义先澄清 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-31 | Directive 含功能/目标/硬约束/机会 | PASS | 真实Director结构及受控Schema错误；schema_fault_browser.json |
| AT-32 | 空抽屉/小动作组合/关键发现三态 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-33 | 有/无前文证据的反转候选区分 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-34 | 伏笔登记/呈现/回收可追溯 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-35 | 压力源不支持则不凭空加灾难 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-36 | Director 按历史判断继续/收束 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-37 | Wish 不可行/部分/冲突三态 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-38 | 明确离城→退出/后果结局 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-39 | Arc 关闭后不自动续，点继续新建 | PASS | 文字Ending后React显式继续，真实Step创建Arc2；live_text_ending_continue.json |
| AT-40 | 两域联合提交失败/重复/过期 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-41 | 高置信普通 vs 重大反转路径 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-42 | 压力/伏笔/关系/Wish 争用可解释 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-43 | 一句想法+否决 AI 设定可局部改 | PASS | 真实当前理解与React局部确认；at77_79_browser.json |
| AT-44 | 真实体验者试玩并反馈 | BLOCKED | 尚无独立真实体验者反馈，自动化不能替代 |
| AT-45 | DGX 启动本地 Director + 中文规划 | PASS | 复用现有Nemotron；本轮真实Director调用与中文输出，不重复部署 |
| AT-46 | Ready 点击 vs 自由输入路径 | PASS | 真实Ready缓存选择与新FREE视频分别实测；不混淆复用/生成 |
| AT-47 | Director prompt 分层 Context | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-48 | Narrative 试图泄露未授权秘密被拒 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-49 | K=3 三路并行非串行 | PASS | 真实三个推荐及各自H3 jobs/阶段时间；live_play_traces.json |
| AT-50 | READY 点击后媒体校验失败回滚 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-51 | 全链耗时分阶段 timing | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-52 | Top-K 中一条失败两次→K-1 发布 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-53 | Step3.7 Narrative timeout→本地 Lightning | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-54 | 本地 Lightning OOM→Step5（非3.7） | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-55 | 未选分支相似请求的指纹复用/失效 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-56 | AGENT↔VIDEO 往返切换 drain/persist | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-57 | VIDEO_LOCAL 下 Production 走 3.7 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-58 | VIDEO_LOCAL+3.7 故障不误试 Lightning | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-59 | 分角色注入故障走各自 fallback 链 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-60 | Provider 版本升级后旧分支 provenance | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-61 | 全局角色库按 personality 搜索 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-62 | 一句描述 AI 建角色→2 张 Candidate | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-63 | 选主图→二次确认→标准参考组 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-64 | 「换雨衣保持身份」编辑 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-65 | 快捷只改背景/姿势 + 自由语言编辑 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-66 | Outfit 属同一 GlobalCharacter | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-67 | 上传 Pose/动作视频 Reference | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-68 | 换主图/Canonical Voice/新增 Outfit | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-69 | Scenario 用 v3 后 Global 升 v4 | PASS | 固定v2后全局版本升级不改变Snapshot；at78_81_browser.json +回归 |
| AT-70 | Scenario 内改外观→仅本故事/全局 | PASS | React本故事修改→Global不变→显式Promote；at78_81_browser.json |
| AT-71 | 单角色 Scene→自动选 2-4 张图 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-72 | 双角色素材近上限→确定性裁剪 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-73 | 改文字描述不点重新生成→不动资产 | PASS | AI角色文本确认写版本，已有Canonical图片保持；global_ai_browser.json |
| AT-74 | 多分辨率 100% Zoom 走四页 | PASS | 当前构建Firefox 35/35，100% Browser Zoom；responsive_checks.json |
| AT-75 | 标准隐藏 Prompt/Provider，开发者可见 | PASS | Standard信息分层与Developer原始异常；schema_fault_browser.json / final_player_checks.json |
| AT-76 | 封版部署核查 + AGENT↔VIDEO 往返 | PARTIAL | 本轮未完整重跑此条的所有真实/失败判据；历史证据见AT01_76_HISTORICAL.md，不据此宣称最新HEAD PASS。 |
| AT-77 | 模糊故事 | PASS | 真实 Step 5 生成当前理解与三组上下文问题，React 选择建议并正式写入；锁/过期/非法路径由回归验证。 `at77_79_browser.json` |
| AT-78 | 完整故事 | PASS | 明确真相/冲突/压力的描述没有重复问题（explicit_questions=0）。 `at78_81_browser.json` |
| AT-79 | Drama 两种模式 | PASS | React 确认 truth_model 后 Changes 留 Before/After/source/time，Developer 显示同一值。 `at77_79_browser.json` |
| AT-80 | 角色两个入口同管理颗粒度 | PASS | 旧七标题/入口检查不足，已由 1920×1080 实际 UI A–F 覆盖：造型选择/五槽上传、3选2姿势及空覆盖、2选1动作、备用声音、刷新保留且Global逐字段不变；库v24→v25仍pin v24，显式更新与Promote新v26后旧版本不变。共享CharacterStudio，`docs/acceptance/character_scope_regression/scope_regression.json`。 |
| AT-81 | 角色 Overlay | PASS | Desire/Secret/Visual State 修改后 Global 不变；点击 Promote 后才产生全局版本，已发布快照继续固定。 `at78_81_browser.json` |
| AT-82 | 自然语言玩法 | PASS | 真实 Step 5 编译并发布三类玩法；真实 Jev/Nemotron 行动重试调用 relationship Skill 1.0.0，正式关系写入55，World version仅增加1。该次呈现为用户选定的文字模式。 `live_mechanics_proposal.json / live_mechanic_execution.json` |
| AT-83 | 玩法两种模式 | PASS | Standard 教程卡无 JSON；Developer 查同一 Typed Config/Skill/trigger；确认与手动编辑共用校验。 `natural_language_mechanics.png / developer_mechanics.png` |
| AT-84 | Player Theater Mode | PASS | 2026-09-25修复controls遮Agency与默认Theater入口。9000历史失败Session只读1920×1080/2560×1440：默认应用内Theater、fullscreen=false、Sidebar/Header隐藏、controls在Stage内、Agency底部、HUD/Session/input保留；`docs/acceptance/biohazard_full_e2e/theater_readonly.json`。隔离error/Ready四案验证切换/重新进入与progress保留；`docs/acceptance/player_stage_controls/browser.json`。非新H3成功证明。 |
| AT-85 | Decision Lead | PASS | 真实 H3 缓存回放：Lead 前 API recommendations=[]，到达后3条Ready可见，React 位于输入上方；点击后CANONICAL。不是新生成证明。 `lead_ready_replay_validation.json` |
| AT-86 | 三推荐之外自由行动 | PARTIAL | React 存在三条真实Ready时自由输入，经真实链生成新FREE H3分支br_00136_383b8e并CANONICAL；重复提交保护回归通过。 `firefox_player_validation.json / live_play_state.json`  最后Director/关系修复后真实文字FREE通过，但fal锁阻止最终候选新FREE视频重测。 |
| AT-87 | HUD | PASS | Firefox hover/pin/unpin；背包/关系/线索/愿望；已写入的关系在Standard显示定性文字、Developer显示数值。 `final_player_checks.json / live_mechanic_execution.json` |
| AT-88 | Director Schema 故障 | PASS | 真实Nemotron调用后，隔离测试装置明确注入target_changes=42；一次schema retry后FAILED_RECOVERABLE。Standard无原始错误，Developer可查，World不变。 `schema_fault_browser.json` |
| AT-89 | Unicode 字幕 | PASS | Firefox真实H.264/AAC播放；中文场景/人物/字幕截图检查；标题淡出；画内与画外字幕可读。 `final_player_checks.json / unicode_subtitle_bottomInside.png / unicode_subtitle_bottomOutside.png` |
| AT-90 | 媒体三态 | PASS | 实际生成画面、真实MP4的HTTP延迟/503分别形成Generating/Loading/Failed；重新载入播放成功，文字恢复不重复提交。 `media_state_validation.json / player_generating.png` |

## AT-91–AT-98（本轮无 Fal 新请求）

| AT | 用例 | 最新判定 | 本轮证据/限制 |
| --- | --- | --- | --- |
| AT-91 | 媒体设置写入新任务 provenance | PASS | Settings/Runtime/Provider 参数链已统一，图片 resolution、视频 resolution、aspect_ratio 进入请求与 provenance；未知值不静默忽略。 |
| AT-92 | Provider 不支持能力显式处理 | PASS | H3 Max、Sol-H3、图片中转站对未知 resolution/aspect_ratio 显式 reject；无 Fal 请求。 |
| AT-93 | Developer 测试覆盖不污染正式配置 | PASS | `developer_test_override_enabled` 关闭时使用正式 K/Shot/Duration，开启时使用 `effective_*`；Settings 明确标识开发测试覆盖。 |
| AT-94 | Guard OFF 遍历 H3/Nano Banana | PASS | `no_fal_guard_probe.json`：两条付费 Provider 在 HTTP 前返回 `PAID_GENERATION_DISABLED`，http_attempts=0。 |
| AT-95 | TOP_UP 熔断 | PASS | `tests/test_fal_safety.py::test_top_up_opens_fal_circuit`：403 TOP_UP→BILLING_LOCKED→OPEN，后续本地快速失败。 |
| AT-96 | Billing Locked 时角色非付费能力 | PASS | 角色文字编辑、上传/绑定、版本/Snapshot/Overlay 路径仍可用；AI 生图/Edit 显示自然语言不可用提示。 |
| AT-97 | 媒体失败不以 Mock 冒充 | PASS | Player 保留 FAILED_RECOVERABLE、重试/修改/文字继续/退出；本轮未将 Mock 作为正式 Fal 媒体成功。 |
| AT-98 | Paid Preflight + Usage Ledger | PASS | `/api/dev/generation-preflight` 与 `/api/dev/usage-ledger` 可审计 job、duration、resolution、reference、guard/circuit、blocked reason。 |
