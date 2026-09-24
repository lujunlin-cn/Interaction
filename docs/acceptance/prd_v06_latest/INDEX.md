# Evidence index · latest PRD v0.6 UX

最终应用代码候选：`2e548769d0960d901075eca46ac2f7ec63409512`。完整判据、范围与结论见根目录 `LATEST_PRD_UX_ACCEPTANCE.md`。记录了修复前失败，不能把本目录所有文件一概算作PASS。

## 最终成功记录

| 文件 | 证明什么 |
| --- | --- |
| verification_summary.json / backend_pytest.log / frontend_build.log | 最新候选完整回归、构建、源码树与bundle指纹 |
| GAP_AUDIT.md | 编码前Q105–122逐项检查（不是实现完成报告） |
| at77_79_browser.json | 真实Step建议→React确认→Changes→相同Developer字段 |
| at78_81_browser.json | 详细输入不重复追问、Overlay不改Global、显式Promote |
| global_ai_understanding.json / global_ai_browser.json | 真实角色AI建议与React接受 |
| live_mechanics_proposal.json / mechanics_compiler_success_traces.json | 真实Step自然语言玩法编译、验证后的Typed Config |
| live_mechanic_execution.json | 最后修复后的真实行动重试：Skill1.0.0→Proposal→World v1→v2、关系55、定性HUD；明确文字模式 |
| real_h3_opening_provenance.json / real_h3_opening.mp4 | 本轮真实两Shot/独立fal请求/完整references/FFmpeg/10.4s产物 |
| live_play_state.json / live_play_traces.json | 本轮较早的真实FREE H3成功；最终Director修复后没有新增fal视频，不冒充最新FREE全链复测 |
| live_timed_timeout.json / timed_countdown.png | 实际TIMED超时fallback |
| live_text_ending_continue.json | fal拒绝后用户明确文字继续→Ending→真实Step续Arc2，保留旧Arc和事实 |
| responsive_checks.json | 当前React构建的35项尺寸/页面/UI Size检查，浏览器zoom=1 |
| deployment_validation.json | 推送后的应用部署和本地/公网健康、bundle/API/data校验 |

## 受控回放 / 故障注入

| 文件 | 范围 |
| --- | --- |
| *_origin.json | 隔离Session克隆来源；恢复原始World/Drama、延长TTL用于暂停检查；不计新Provider调用 |
| lead_ready_replay_validation.json | 真实H3缓存，Lead前API不暴露推荐，达到后React选择CANONICAL |
| final_ready_commit.json | 最后应用候选再次执行服务端Lead/Ready选择→CANONICAL |
| final_player_checks.json | 当前Firefox容器全屏包含真实视频/字幕/HUD/三Ready/输入；标题淡出、字幕位置、关系定性/精确值和Inspector |
| schema_fault_browser.json | 真实Nemotron调用后明确替换为格式错误的JSON；两次尝试后恢复状态、Standard/Developer错误隔离 |
| media_state_validation.json | 对真实MP4传输注入延迟/503；Loading/Failed、重载播放、文字继续与状态不变 |

## 外部阻塞与修复前记录

- `fal_ending_failure.json`：真实HTTP403 `User is locked. Reason: TOP_UP.`。视频Ending BLOCKED，不等于文字Ending失败。
- `*_before_fix*`、`authoring_structural_failure_traces.json`：作者输出、开场空异常、关系缺少Skill提案/初始值等失败。后续成功记录与测试单独列出。
- `live_browser_e2e.json`、`player_browser_validation.json`：早期浏览器尝试，包含失败，不是最终整轮成功证据。
- `firefox_player_validation.json`：真实视频播放和AT-84/87/85/86步骤成功；最后找Inspector按钮失败。最终Inspector已由`final_player_checks.json`和`schema_fault_browser.json`独立通过。
- `live_ready_ending_continue.json`：保留结局链中途失败的状态，不是Ending全成功报告。
- `live_character_proposal.json` / `live_proposal_traces.json` / `pre_final_provider_traces.json`：包含重试前角色理解失败；最终全局角色结果看`global_ai_*`。
- `final_live_traces.json`：采样时包含重放夹具的提交失败和旧Provider拒绝，不是全部通过的Trace汇总。
- `chromium_codec_limit.json`：本机Chromium无H.264/AAC；播放验收使用`firefox_codec_support.json`对应Firefox。
- `step_format_probe_True.json` / `step_format_probe_False.json`：同端点/模型的JSON格式兼容对照，说明为何Step 5不发送response_format=json_object。
- `AT01_76_HISTORICAL.md`：旧矩阵原样存档，不将旧55 PASS用作最新HEAD证据。

## 关键截图

AI引导Drama：`ai_guided_drama.png`、`complete_story_understanding.png`、`changes_before_after.png`。
角色：`character_library.png`、`creator_character_overlay.png`。
玩法：`natural_language_mechanics.png`、`developer_mechanics.png`。
Player：`normal_player.png`、`fullscreen_ready_layers.png`、`hud_expanded.png`、`hud_relationship_qualitative.png`、`ready_recommendations.png`、`free_input.png`。
字幕：`unicode_subtitle_bottomInside.png`、`unicode_subtitle_bottomOutside.png`。
恢复：`player_generating.png`、`player_loading.png`、`player_media_failed.png`、`schema_error_standard.png`、`mechanic_commit_recoverable.png`、`ending_text_recovery.png`。
Developer：`developer_inspector.png`、`developer_schema_inspector.png`。

本目录的PNG/MP4/JSON散列见`evidence_manifest.json`；清单自身不递归计算。
