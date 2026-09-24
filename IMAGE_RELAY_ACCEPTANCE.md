# Image Relay Acceptance

日期：2026-09-25

已将 Character Studio 的 `nano_banana_2` 逻辑槽位接入 OpenAI Images-compatible 中转站。配置项为 `IMAGE_PROVIDER_BASE_URL`、`IMAGE_PROVIDER_API_KEY`、`IMAGE_PROVIDER_MODEL`，默认模型 `gpt-image-2.5-sunburst`，备用模型 `gpt-image-2`。密钥只从环境读取。

适配契约：

- `POST /v1/images/generations`
- `Authorization: Bearer <TOKEN>`
- `prompt / size / quality / style / n / response_format=url`
- OpenAI 标准 `data[].url` 响应转换为 CharacterAsset Candidate
- 0.5K/1K/2K/4K 映射为 512/1024/2048/4096 方图
- 非破坏 Edit 走 `/v1/images/edits`，保留原图和 source refs

真实最小 smoke 已完成：`gpt-image-2.5-sunburst`、`n=1`、`1024x1024`、`standard`、`vivid`，HTTP 200，返回 1 个 URL，结果 1254×1254。请求详情（不含密钥）见 `docs/acceptance/image_relay_live_smoke.json`。

这次 smoke 没有调用 Fal；H3 Max、Sol-H3 和 Fal circuit 语义不变。
