# G29 真实模型部署核查（DGX Spark，2026-09-24，v0.6 Final Closure）

本文件的结论以实际探针为准。适配器代码存在不等于 Provider PASS。

| 槽位 | 期望 | DGX 实况 | 结论 | 处理 |
|---|---|---|---|---|
| nemotron_local（director/production）| vLLM `http://127.0.0.1:8001/v1` `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` | `/v1/models` 返回固定模型 ID；中文 JSON 冒烟成功；vLLM 0.27.1-aarch64，GPU 进程约 80,329 MiB | **PASS（实部署）** | `local_llm_base_url` 与 `local_llm_model` 固定为 Nemotron；Gemma 不占用此槽位 |
| Ollama gemma3:27b | 显式降级 Provider | 可保留在 11434，但不作为 Nemotron 证据 | 非 Nemotron PASS | 仅在显式配置为外部 fallback 时使用 |
| step_37 / step_5 | StepFun `api.stepfun.com` | env 已配 `STEP_API_KEY`/`STEP37_MODEL`/`STEP5_MODEL` | 就绪（真实调用待验收 #29） | HYBRID narrative→step_37 首位 |
| jev（decision）| TypeSafe `api.typesafe.ai` | env 已配 `JEV_API_KEY`/`JEV_MODEL=jev-latest` | 就绪 | decision 路由首位 |
| h3_max（cloud_video）| fal.ai `minimax/h3-max/reference-to-video` | env 已配 `FAL_KEY` | **已实测出片** | job `01a0ceef-d403-78c2-b737-7aa3cccb8f05` → COMPLETED → 下载 `clip_1.mp4`（6.9MB, ffprobe 5.184s）。endpoint id 已修正（原 `fal-ai/` 前缀 404）；reference-to-video 必须带≥1 参考图。 |
| sol_h3_local（local_video，VIDEO_LOCAL_PROFILE）| Sol-H3 本地 | 适配器已实现；本次会话未重新取得 DGX 任务产物 | PARTIAL（历史任务证据仍保留） | `SOL_H3_BASE_URL` 由目标机注入 |
| 其他本地服务 | — | ComfyUI `8188` 在线；h3-object3d-worker `8792`（TRELLIS.2-4B）在线 | 非本系统槽位 | 不接 |

## h3-adapter 8790 实测协议（SolH3LocalProvider 实现依据）

- `POST /v1/videos/generations` Bearer token → `{request_id:"h3_…", status:"pending"}`
- `GET /v1/videos/{id}` → `{status: pending|running|done|failed|expired|cancelled|draft, video:{url}, error}`
- `GET /v1/videos/{id}/content` → mp4（带 token）
- `POST /v1/videos/{id}/cancel` → 排队直接取消 / 执行中中断 ComfyUI
- 参考：`reference_images`≤9、`reference_videos`≤3（{data,duration,with_audio}）、`reference_audios`≤3
- 鉴权：`Authorization: Bearer <H3_ADAPTER_TOKEN>`（SERVICE_USER，不做数据隔离）

## 代码改动

- `config.py`：`local_llm_model` 固定为 Nemotron Lightning；新增 Director admission 配置与 `sol_h3_base_url`/`sol_h3_api_key`
- `providers/real.py`：`SolH3LocalProvider` 由占位重写为 h3-adapter 真实协议（submit/status/cancel/health + references 适配）；注册表注入 env 配置

## 当前 BLOCKED / 待办

- **Nemotron 并发边界**：直连 vLLM 的 1/2/4 路三轮分别 3/3、6/6、12/12；4 路短请求无 OOM/timeout。业务 admission 仍保守设为 2，详见 `DIRECTOR_CONCURRENCY_REPORT.md`。
- **sol_h3_local 真实出片**：本次 Final Closure 未重新取得任务产物，保持 PARTIAL，不升级为 PASS。
