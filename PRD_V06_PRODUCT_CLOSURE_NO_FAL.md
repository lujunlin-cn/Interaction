# PRD v0.6 Product Closure（No-Fal 本轮）

Start SHA：`deb92fdbb9c7b6f9b56e517b35add290f8d3063f`
Final SHA：以最终 git rev-parse HEAD 为准

Fal Paid Generation Enabled：`false`
Fal paid HTTP attempts：**0**

## 本轮结论

| 项目 | 判定 | 真实证据 |
| --- | --- | --- |
| Player Theater Mode | PASS | `docs/acceptance/prd_v06_latest/no_fal_ui_browser.json`：普通浏览器窗口、`document.fullscreenElement=false`、Sidebar 隐藏、Stage 1920×997.75、Agency/HUD 保留；退出后状态和输入仍在 |
| 角色命名 | PASS | Standard 使用“角色库 / 角色 / 本故事覆盖”，不把 Global Character 作为主要产品名 |
| 角色同颗粒度 | PASS | 角色库与 Creator 均提供七个工作台标签；Creator 逐项提供 Outfit、Pose、Motion、Canonical/Alternate Voice 的 Scenario Overlay，证据见 `CHARACTER_GRANULARITY_CLOSURE.md` |
| Character Studio tabs | PASS | `no_fal_ui_browser.json`：概览、身份、造型、姿势与动作、声音、使用记录、版本 |
| Outfit | PARTIAL | 同角色 Outfit 创建、默认标识和素材池入口可操作；本轮未执行任何付费生成 |
| Pose/Motion | PARTIAL | 多个静态 Pose / Motion Reference 槽位和上传入口已接入，完整 Resolver/Production 组合仍待更完整实测 |
| Canonical + Alternate Voice | PARTIAL | Canonical/备用声音 UI 与 typed 字段已接入，未做真实音频全流程 |
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

- Backend：`PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false FAL_PAID_GENERATION_ENABLED=false .venv/bin/python -m pytest tests -q` → **63 passed / 0 failed / 6 warnings**。
- Frontend：`npm run build` → **PASS**（TypeScript + Vite）。
- Browser UI：1920×1080 mock runtime，无页面异常；Theater、退出、角色 tabs、媒体 Settings、Developer Preflight/Usage Ledger 通过，见 `no_fal_ui_browser.json` 与对应截图。
- Guard probe：`no_fal_guard_probe.json`；Fal paid HTTP attempts **0**。

## 仍需充值后完成

- Paid-01 Character：`0.5K → AI Create → 2 Candidates → Canonical → Standard Views → 1 Edit`（中转站/图片 Provider 另行按真实账号验证，不能用 Mock 代替）。
- Paid-02 FREE Branch：`480P / K=1 / 1 Shot / 5s → 自由输入 → 新 H3 → CANONICAL`。
- Paid-03 Ending：`480P → H3 MP4 → CANONICAL → Arc Closed → Continue World`。

这些项目继续标记 `PARTIAL/BLOCKED`，本轮没有为提高 PASS 数量产生任何 Fal generation/edit 请求。

## 仍存在的非 Fal P0

- Character Library 与 Creator 的 Outfit/Voice/Pose/Motion 细粒度操作已完成 1920×1080 非付费浏览器回归，证据见 `docs/acceptance/prd_v06_latest/character_granularity_browser.json`。
- AT-01～76 中未在本轮重跑的真实语义/边界/多模态用例仍保持原有 PARTIAL；AT-44 独立体验者反馈仍 BLOCKED。
