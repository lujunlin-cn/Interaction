# PRD v0.6 Final Closure

日期：2026-09-24

## Final Candidate

- 起始 SHA：`8e7eb048397555ab7fb993025c48a42bc6f905a5`
- 最终候选 SHA：`9be1d814784d3653e3bdaf62d6afb1a37d90b9b5`
- 结论：**PARTIAL**。真实 H3 Multi-Shot、真实 Profile 往返、UI 五档响应式截图和离线回归已完成；外部 Character Studio 浏览器 Flow A～E 尚缺本轮完整留证。

本轮新增 `FINAL_E2E_ACCEPTANCE.md`：VIDEO_LOCAL 下真实 Sol-H3 出片、ComfyUI
worker 健康、V→A 资源释放和 Nemotron 重新启动已完成；完整普通用户故事 E2E
未重新录制的项目继续保持 PARTIAL。

## 验收结果

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Backend | PASS（离线验收） | `PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false`：45 passed, 6 warnings |
| Frontend Build | PASS | `npm ci && npm run build`，tsc + Vite 成功 |
| Real H3 Multi-Shot | PASS | `REAL_MULTISHOT_ACCEPTANCE.md`，2 jobs/2 clips/FFmpeg/ffprobe |
| Profile Switch | PASS | `PROFILE_SWITCH_ACCEPTANCE.md`，DGX Spark A→V→A、stop/start/health/cold-start |
| Character Studio | PARTIAL | 正式 React/API 与图片 Baseline→Canonical 实测；AI 外部 Flow A～E 未重跑 |
| UI/Responsive | PASS | zoom 已删除、三档 token 已实现；Chromium 100% 下五档截图和 1920 三档截图已留存 |
| AT-01～76 | 55 PASS / 20 PARTIAL / 1 BLOCKED / 0 NOT_RUN | `ACCEPTANCE_MATRIX.md` |

## 真实证据

- H3 双 Shot 原始 Provider 回执：`real_h3_multishot_evidence.json`
- H3 concat 产物：`backend/data/media/scenes/real_acceptance_h3_multishot.mp4`
- Profile 原始 API、models 和 Director response：`backend/profile_switch_acceptance_runtime.json`
- Character Baseline API：角色 `chr_00001_4bddcd`，Candidate/Canonical `ca_00003_5cf0fb`
- Nemotron ID：`nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`
- StepFun endpoint：`https://api.stepfun.com/step_plan/v1`
