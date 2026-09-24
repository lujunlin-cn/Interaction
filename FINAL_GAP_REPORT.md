# Final Gap Report — PRD v0.6

审计基线：本轮最新 `main`（起始 SHA `8e7eb048397555ab7fb993025c48a42bc6f905a5`）。
PRD v0.6 是业务 SoT；线上 :9000 和 Nemotron Lightning 部署已确认，不再列为 Gap。

## CLOSED

- VIDEO_LOCAL Sol-H3 live validation：在正式 Profile API 下启动完整 ComfyUI worker
  与 adapter，真实生成 5.042 秒 MP4；A→V→A 和 Nemotron 中文 JSON smoke 见
  `FINAL_E2E_ACCEPTANCE.md`。
- Profile lifecycle resource release：VIDEO_LOCAL 切换现在同时停止/启动 adapter
  和 ComfyUI，避免 H3 权重残留导致 Nemotron EngineCore 启动失败。

- Play Loop：Opening → 自动播放 → Decision Lead 服务端 Gate → 选择/自由输入 → 下一幕，失败可重试/文字继续/退出。
- Real Multi-Shot Runtime：N Shot → N 个 Provider Job → N clips → FFmpeg concat；每 Shot 和 SceneArtifact 都记录 provenance。
- H3 Max 真实双 Shot：两个独立 request ID、两个真实 mp4、ffprobe 与 concat 证据见 `REAL_MULTISHOT_ACCEPTANCE.md`。
- Profile lifecycle：DGX Spark 实际 A→V→A，真实 stop/release/start/health/cold-start/Director smoke 见 `PROFILE_SWITCH_ACCEPTANCE.md`。
- Decision Lead 服务端暴露条件、后端 SemVer、Publish Gate、typed patch（含 characters/mechanics）。
- UI Size 不再使用整体 `zoom`/`transform: scale`；三档 token 和 4K 工作区已落地，并在 Chromium 100% Browser Zoom 下重新生成五档截图。
- Character Studio 正式 React/API：AI、图片 Baseline、手动三入口以及 Candidate/Canonical/多视图/Edit/Outfit/Version/Snapshot/Override/Promote/Resolver。

## PARTIAL

- Character Studio 外部 nano-banana-2 AI 生图、多视图和编辑的完整浏览器 Flow A～E 本轮没有重新消耗外部配额；本轮只实测了图片 Baseline → Candidate → Canonical API。
- 默认 hybrid 运行时云视频仍允许 `h3_max → mock_video` 显式降级；Real Multi-Shot PASS 只引用真实 H3 证据，不引用该 fallback。
- 全量测试在显式离线验收环境 `PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false` 下为 `45 passed, 6 warnings`；直接使用线上 hybrid `.env` 会因外部真实视频任务时序导致 1 个 timed 用例不稳定，因此不宣称 hybrid pytest 全绿。

## BLOCKED

- AT-44 需要真实用户试玩反馈，本机无法替代真实体验者。

## REMAINING

- 在有浏览器自动化和可控 nano-banana 配额的验收窗口重拍五档分辨率，并完整执行 Character Studio Flow A～E。
- 若生产环境要求所有视频都是真实 H3/Sol-H3，将 `PROVIDER_MODE=live` 并确保参考素材和 Provider 配额可用；hybrid 的降级语义需保留。

最终候选 SHA：见本次 Final E2E 提交。
