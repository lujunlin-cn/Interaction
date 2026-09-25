# PRD v0.6 Product Closure（历史 No-Fal + 角色 Scope 复验）

Start SHA：`deb92fdbb9c7b6f9b56e517b35add290f8d3063f`
Final SHA：本报告所在最终提交；交付回复提供完整 SHA，使用 `git rev-parse HEAD` 核对。

历史 No-Fal / 本次独立角色 Scope 服务：Fal Paid Generation Enabled `false`，Fal paid HTTP attempts **0**。

**范围限制：**以上 0 只适用于隔离的无费用测试，不是当前 live FULL E2E 总数。live 9000 已有历史四张 Relay 图和一次 Fal attempt，最终由 BIOHAZARD_FULL_E2E_ACCEPTANCE.md 计账；用户最新要求 live 付费开关保留供人工测试。

## 本轮结论

| 项目 | 判定 | 真实证据 |
| --- | --- | --- |
| Player Theater Mode | PASS | `docs/acceptance/prd_v06_latest/no_fal_ui_browser.json`：普通浏览器窗口、`document.fullscreenElement=false`、Sidebar 隐藏、Stage 1920×997.75、Agency/HUD 保留；退出后状态和输入仍在 |
| 角色命名 | PASS | Standard 使用“角色库 / 角色 / 本故事覆盖”，不把 Global Character 作为主要产品名 |
| 角色同颗粒度 | PASS | 旧七标题证据作废；共享 Studio 的 A–F 实际点击、上传、持久化/刷新、Global 不变、版本固定/更新与 Promote 均通过，见 `docs/acceptance/character_scope_regression/scope_regression.json` |
| Character Studio tabs | PASS | `no_fal_ui_browser.json`：概览、身份、造型、姿势与动作、声音、使用记录、版本 |
| Outfit 管理 | PASS | 名称/描述/default、front/side/back/full_body/additional上传绑定；Creator新造型仅写local_outfits；付费生成质量另验 |
| Pose/Motion 管理 | PASS | 3选2姿势、2选1动作、空OVERRIDE、故事专用上传/刷新实测；真实Production质量另验 |
| Canonical + Alternate Voice 管理 | PASS | Voice A主声音、Voice B备用试听/选择；Creator切B不改Global A，Promote才创建新版本 |
| Scenario Overlay | PASS | ScenarioCharacter 增加 outfit/pose/motion/voice overlay；显式继承/覆盖/Promote 路径保留 Global 不变 |
| Pure-text Character Publish | PASS | Publish Gate 将缺视觉资产写成 warning；真正视频 Production 时再要求补资产或文字模式 |
| Assets Image Generation Entry | PARTIAL | Assets 入口仍存在；Fal Guard OFF 时禁止付费提交，未执行新生图 |
| Visual Stale UX | PASS | 文字变化不自动生图，保留现有视觉并提示可保持/重生/编辑 |
| Generation Settings | PASS | Standard/Developer Settings 的 image 0.5K/1K/2K/4K、video 480P/768P/1080P、aspect ratio；Provider 对未知能力显式 reject |
| Test Override | PASS | Developer 明确“开发测试覆盖”，K/Shot/Duration 通过 `effective_*` 只影响启用的测试上下文 |
| Paid Guard | PASS | H3 Max / Nano Banana Generate/Edit 在 HTTP 之前返回 `PAID_GENERATION_DISABLED`，`http_attempts=0` |
| Billing Circuit | PASS | `403 + TOP_UP/User is locked` 分类 `BILLING_LOCKED`、OPEN circuit；已有 pytest 故障注入验证后续本地快速失败 |
| Usage Ledger | PASS | `/api/dev/usage-ledger` 与 Preflight 记录 provider/model/task/request/status、参数、引用摘要和 blocked reason |

## 验证

- Backend：当前整合全套 **195 passed / 0 failed / 6 warnings**，Fal Guard OFF、mock providers、lifecycle disabled；历史 No-Fal 的 63 passed 仅保留为历史记录。
- Frontend：`npm run build` → **PASS**（TypeScript + Vite）。
- 最终部署：`npm ci` / build、Backend compileall/pip check PASS；9000服务重启active，JS/CSS响应与最终dist逐字节/SHA-256一致。用户对象保持不变，既有seed启动逻辑仅刷新官方rainy-apartment两行。见 `docs/acceptance/biohazard_full_e2e/deployment_final.json`。
- Browser UI：1920×1080 mock runtime，无页面异常；Theater、退出、角色 tabs、媒体 Settings、Developer Preflight/Usage Ledger 通过，见 `no_fal_ui_browser.json` 与对应截图。
- Guard probe：`no_fal_guard_probe.json`；Fal paid HTTP attempts **0**。

## 独立真实付费验收尚待完成

- Paid-01 Character（当前授权 FULL E2E 参数）：`4K → AI Create → 2 Candidates → Canonical → Standard Views → 1 Edit`；必须使用已批准的 Image Relay，不能用 Mock 代替。
- Paid-02 FREE Branch：当前 FULL E2E 使用 `480P / K=3 / 1 Shot per branch / 优先 5s`，必须先有真实三条 READY，再在三选项可见时走独立 FREE → CANONICAL；K=1 仅是旧小额 smoke 方案，不能满足本次验收。
- Paid-03 Ending：`480P → H3 MP4 → CANONICAL → Arc Closed → Continue World`。

这些项目的真实闭环继续独立判定；隔离角色 Scope 回归没有产生任何媒体 generation/edit 请求。当前真实 FULL E2E 已获授权，不能把历史充值阻塞当作最新账号状态。

当前真实故事已通过 Standard UI 逐页检查参数、显式勾选审阅并发布 **v0.2.0**（`ver_00001_b26e3c`），三名角色 pin 为 Leon v8 / Claire v7 / Victor v7。完整 E2E 仍为 PARTIAL：缺少 `IMAGE_PROVIDER_API_KEY`，Claire/Victor 视觉资产及真实 H3 游玩尚未完成。本次修复/复查 continuation 新媒体付费请求为 0；不抹去此前四张 Relay 图片与一次 Fal HTTP attempt。详见 `BIOHAZARD_FULL_E2E_ACCEPTANCE.md`。

## 仍存在的非 Fal P0

- Character management 范围没有已知剩余 P0。实际 A–F 持久化证据位于 `docs/acceptance/character_scope_regression/`；旧仅入口/标题证据已被替代。
- 后续发现的后端原子发布缺口已修复：ScenarioVersion 与全部 CharacterSnapshots 使用同一事务和冻结的审阅草案来源；7项故障注入/版本来源漂移/兼容测试通过。此修复不代表真实视频 E2E 已完成。
- AT-01～76 中未在本轮重跑的真实语义/边界/多模态用例仍保持原有 PARTIAL；AT-44 独立体验者反馈仍 BLOCKED。

Image Relay 是 **USER-approved cost optimization**：IMAGE_GENERATION / IMAGE_EDIT → configured image provider → 当前部署优先 OpenAI-compatible Relay。FalImageProvider 仍保留，本次真实 E2E 的 Fal 仅用于 H3。
