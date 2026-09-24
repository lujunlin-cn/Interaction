# Profile Switch Acceptance

日期：2026-09-24  
判定：**PASS（DGX Spark 实际往返）**

后端以 `PROFILE_LIFECYCLE_ENABLED=true` 重启后，在空闲窗口执行了完整的
`AGENT_LOCAL_PROFILE → VIDEO_LOCAL_PROFILE → AGENT_LOCAL_PROFILE`。实现支持 Docker
容器和宿主机 Sol-H3 adapter 两种生命周期；本机 Sol-H3 使用
`/home/hajimi2025/h3-adapter/h3_adapter.py` hook。

## A → V

- `DRAINING → PERSISTING → STOPPING → STARTING_TARGET → HEALTH_CHECK → ACTIVE`
- `interaction-nemotron` stop 后 `docker inspect` 为 `false`，vLLM `:8001` 暂不可连接。
- Sol-H3 adapter 进程重新启动：`h3_adapter.py --host 127.0.0.1 --port 8790`。
- `GET /health` 使用 Sol token 返回 HTTP 200，`status=degraded`（ComfyUI worker 当前
  未运行，但 adapter/tier/队列服务可用）。
- A→V API 返回 `ok=true`，STOPPING 3.142s，HEALTH_CHECK 66ms。

## V → A

- Sol-H3 adapter stop 后，`interaction-nemotron` 重新 start；旧 Sol 进程消失。
- Nemotron NVFP4 冷启动耗时 149.021s，期间 vLLM `/v1/models` 暂不可连接，健康检查
  未提前切换为 ACTIVE。
- 启动完成后 `/v1/models` 返回固定 ID：
  `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`。
- 中文 Director 请求成功，端到端请求耗时 2383ms，返回 JSON `outcome/directive`。
- V→A API 返回 `ok=true`，并记录完整 lifecycle timeline。

原始 API 返回保存在 [`backend/profile_switch_acceptance_runtime.json`](backend/profile_switch_acceptance_runtime.json)。
失败路径仍保留 `FAILED_RECOVERABLE` 和旧服务恢复逻辑：目标 health 失败时不会把
Profile 标成假 ACTIVE。
