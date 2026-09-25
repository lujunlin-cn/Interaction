# Fal 双 Key 轮换验收

Start SHA：`0135e6fe0c31da9c5cabd213d49bd3f6ed068f1e`

密钥只通过进程环境传递，仓库和证据只保存 SHA-256 前 10 位指纹：

- Key 0：`49838f0961`
- Key 1：`20901bf4f9`

## 真实小额测试

- Provider：Fal `nano_banana_2`
- Task：`IMAGE_GENERATION`
- Resolution：`0.5K`
- Images：`1`
- Result：**READY**，1 image
- HTTP attempts：1
- Key used：Key 0
- Circuit：CLOSED
- 证据：`docs/acceptance/fal_key_live_smoke.json`

说明：第一次同规格调用完成后，本地证据写入路径错误，结果没有保存；随后只重跑了一次同规格调用并得到上述 READY。因此本轮最多发起 2 次最小 smoke submit，未继续扩大测试规模。

未保存返回的签名 URL，也未把 API key 写入代码、Git、Trace 或报告。

## 自动轮换

每个 Fal key 有独立 circuit。以下错误会打开当前 key 并切换下一个可用 key：

- `QUOTA_EXHAUSTED`
- `BILLING_LOCKED`（包括 `403 TOP_UP` / `User is locked`）

两把 key 都 OPEN 时，调用在本地快速失败；不会继续向 Fal 重试。已提交任务在轮询/取消时使用提交该任务的 key index。

单元测试 `test_fal_key_rotation_on_quota` 使用 HTTP 故障注入验证：第一 key 返回账单锁，第二 key 成功 submit，Authorization 顺序为 Key 0 → Key 1；未产生真实第二次付费任务。

## 配置

```env
FAL_KEY=<primary>
FAL_KEY_SECONDARY=<secondary>
FAL_PAID_GENERATION_ENABLED=true
```

生产环境请只在服务端环境注入密钥；充值/额度耗尽时保持 `FAL_PAID_GENERATION_ENABLED` 可随时关闭。
