# No-cost E2E Acceptance · Fal Safety and Offline Regression

日期：2026-09-25  
Start SHA：`266520898a296c0b26e25b7cbc79cfbded14b484`  
Final SHA：`afbbe48a086e6d769b6ebc17bd66b0a42ab82b9c`

## 费用边界

- `FAL_PAID_GENERATION_ENABLED=false`（默认值，本轮未开启）。
- 本轮没有调用新的 H3 Max、Nano Banana、Nano Banana Edit 或视频 Ending 请求。
- Fal paid HTTP POST attempts：**0**。禁用开关在创建 `httpx` 客户端前快速失败；H3 与图片 Provider 均验证为 `PAID_GENERATION_DISABLED`。
- 已有 H3/Nano Banana 媒体缓存可以播放，但没有被当作本轮新 Provider 生成证据。

## 本轮实现

### Billing / quota circuit breaker

`403` 且响应包含 `TOP_UP`、`User is locked` 或 `BILLING` 会分类为 `BILLING_LOCKED`，立即打开进程内 Fal circuit。后续付费请求在本地失败，不 retry、不再次提交。分类还覆盖 `QUOTA_EXHAUSTED`、`AUTH_FAILED`、`RATE_LIMITED`、`TRANSIENT_PROVIDER_ERROR`、`INVALID_REQUEST` 和超时语义；原始技术细节只保留 Developer 路由/Trace。

### 媒体参数

新任务设置已贯通 Settings → Runtime → Provider：图片 `resolution`（0.5K/1K/2K/4K），视频 `resolution`（480P/768P/1080P），`aspect_ratio`（16:9/9:16/1:1/auto），以及 Developer 测试 Top-K、Shot 数、单 Shot 时长、参考数量上限。旧 Artifact 不变。Nano Banana 不再发送旧 `image_size`。

## 验证

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| Paid guard：H3 submit | PASS | `FalGenerationError(PAID_GENERATION_DISABLED)`，HTTP POST 计数 0 |
| Paid guard：Nano Banana generate | PASS | 同上，HTTP POST 计数 0 |
| TOP_UP 分类与熔断 | PASS | `BILLING_LOCKED`，circuit=`OPEN`，后续请求本地拒绝 |
| Backend | PASS | `PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false .venv/bin/python -m pytest tests -q`：62 passed / 0 failed / 0 skipped / 6 warnings / 125.44s |
| Frontend | PASS | `npm ci && npm run build`：TypeScript + Vite，exit 0 |

## 最新 HEAD 可无费用复验的范围

State/Transaction、Decision/Jev、Nemotron Director、Step Narrative、Mechanic Skill、Wish/Pressure/Foreshadow、Character 非付费版本/快照/Overlay/Resolver、Creator/Publish、Player UI/错误态、Continue World 均使用 mock、fixture、本地模型或已有媒体缓存复验。离线回归全绿；缓存回放不计作新真实媒体生成。

## 仍需 Fal 充值

- Paid-01 Character：`0.5K → AI Create → 2 Candidates → Canonical → Standard Views → 1 Edit`。
- Paid-02 FREE：`480P / K=1 / 1 Shot / 5s → 自由输入 → 新 H3 → CANONICAL`。
- Paid-03 Ending：`480P → H3 MP4 → CANONICAL → Arc Closed → Continue World`。

这三组在充值前保持 `PARTIAL/BLOCKED`，不使用 Mock 或历史缓存冒充新真实 Provider PASS。
