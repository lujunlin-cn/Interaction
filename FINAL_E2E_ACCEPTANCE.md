# VIDEO_LOCAL / Sol-H3 Final E2E Acceptance

日期：2026-09-24  
起始 SHA：`e000fcac71bc399b124b2f6ce740a6d04df33318`  
候选 SHA：`13c75b26ac46efc09fd30d2f7ad5733229886436`

## 1. Profile A→V — PASS

通过正式 `POST /api/dev/profile/switch`。生命周期记录为
`DRAINING → PERSISTING → STOPPING → STARTING_TARGET → HEALTH_CHECK → ACTIVE`。
Nemotron 容器停止，ComfyUI worker 与 adapter 启动，adapter `/health` 返回
`status=ok, comfyui=true, comfy_ws=true`。

## 2. VIDEO_LOCAL Sol-H3 real generation — PASS

正式 `POST /api/dev/local-task` 在 `VIDEO_LOCAL_PROFILE` 下路由到
`sol_h3_local`，没有 fallback。Provider job：
`h3_a90abb24a91c4c07b17230db7cd0d3e4`；后端 job：`job_00002_6bbc98`；模型
`minimax-h3-flash` / tier `sol`；状态 `done → READY`。

产物：`backend/data/media/clips/h3_a90abb24a91c4c07b17230db7cd0d3e4/clip_1.mp4`
（845,186 bytes）。`ffprobe`：H.264 + AAC，1344×768，24 fps，5.042 s。
Adapter 完整记录了 prompt、request id、created/started/finished 时间和
`resolution=720p`。

## 3. Profile V→A — PASS

正式 API 返回 ACTIVE。修复后停止 adapter 与 ComfyUI 容器，确认 H3 worker
释放，再启动 Nemotron；冷启动 141.254 s。`/v1/models` 返回
`nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`。

真实中文 Director smoke：`chat_template_kwargs.enable_thinking=false`、JSON
response format，延迟 727 ms，返回 `{"intent":"探索","action":"移动到灯塔背面"}`。

## 4. Creator — PARTIAL

离线 contract/vertical-slice 覆盖创建故事、typed patch、lock 和变化记录；本轮
未重新进行完整浏览器录制，因此不把 UI 操作证据写成 PASS。

## 5. Character Studio — PARTIAL

正式 React/API 已覆盖三入口、Candidate/Canonical、多视图、Edit、Outfit、版本、
Snapshot、Override、Promote 和 Resolver。外部 nano-banana-2 图片配额的完整
浏览器流程本轮未重跑，按验收纪律保留 PARTIAL。

## 6–14. Publish / Opening / Decision Lead / Ready Branch / Free Input /
Intent Echo / TIMED / Failure Recovery / Ending — PARTIAL

现有离线测试覆盖这些状态和失败恢复契约（45 个测试全绿）；本轮没有把新的
`废弃灯塔失踪案` 从正式 React 逐步操作到 Ending，因此不使用 mock 或历史截图
冒充真实用户 E2E PASS。

## 15. Trace / Provenance — PASS（本轮链路）

Sol-H3 job、后端 JobRow、clip 路径和 profile timeline 可反查；Nemotron
`/v1/models` 与 Director request/response 可反查。完整故事 Trace 的 UI 录制仍
按上项列为 PARTIAL。

## 回归

- Backend：`45 passed, 6 warnings, 0 failed`，命令使用独立 SQLite 临时库、
  `PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false`，耗时 115.57 s。
- Frontend：`npm ci && npm run build` PASS；TypeScript、Vite、bundle 均成功。
- Live smoke：Nemotron、Sol-H3 均真实成功；本仓已有 H3 Max、Step、Jev 证据继续
  保存在对应 acceptance 文档中。

## 必要修复

`VIDEO_LOCAL` 生命周期现在会同时停止/启动 adapter 和 ComfyUI worker。此前只杀
adapter 会让 H3 权重继续占用 Spark 统一内存，导致 Nemotron EngineCore 启动失败。
