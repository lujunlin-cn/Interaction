# 报告与验收证据总索引

2026-09-25；以下报告与证据均保存在本仓库。

## 最新状态

- Backend：当前审计重跑 274 passed / 0 failed / 7 warnings；Frontend build：PASS。
- 生化危机 FULL E2E：PARTIAL。真实 H3 游玩、Ending、Continue World、完整角色参考图组与视觉 QA 尚未完成。
- 已归档 10 张 4096×4096 Relay Candidate：Leon 4、Claire 2、Victor 4。
- 当前图片走用户批准的 Image Relay，Fal 仅用于 H3；付费开关按用户要求保持开启。
- 本次报告整理、离线回归与提交未发起新的外部付费媒体请求；历史使用见 Usage Ledger。

## 报告目录

- [验收矩阵 · AT-01–AT-98](ACCEPTANCE_MATRIX.md)
- [Biohazard FULL E2E Acceptance](BIOHAZARD_FULL_E2E_ACCEPTANCE.md)
- [Character Library ↔ Creator Granularity Closure](CHARACTER_GRANULARITY_CLOSURE.md)
- [Character Studio Acceptance](CHARACTER_STUDIO_ACCEPTANCE.md)
- [现场演示脚本 · 互动短剧（PRD §18.2 落地版）](DEMO_SCRIPT.md)
- [部署与运维手册 · 互动短剧](DEPLOYMENT.md)
- [Nemotron Lightning Director 并发实测](DIRECTOR_CONCURRENCY_REPORT.md)
- [Fal 双 Key 轮换验收](FAL_KEY_ROTATION_ACCEPTANCE.md)
- [Final Closure Report · PRD v0.6](FINAL_CLOSURE_REPORT.md)
- [VIDEO_LOCAL / Sol-H3 Final E2E Acceptance](FINAL_E2E_ACCEPTANCE.md)
- [Final Gap Report · PRD v0.6](FINAL_GAP_REPORT.md)
- [G29 真实模型部署核查（DGX Spark，2026-09-24，v0.6 Final Closure）](G29_MODEL_DEPLOY_AUDIT.md)
- [Image Relay Acceptance](IMAGE_RELAY_ACCEPTANCE.md)
- [Latest PRD UX Acceptance · PRD v0.6](LATEST_PRD_UX_ACCEPTANCE.md)
- [No-cost E2E Acceptance · Fal Safety and Offline Regression](NO_COST_E2E_ACCEPTANCE.md)
- [PRD v0.6 Product Closure（历史 No-Fal + 角色 Scope 复验）](PRD_V06_PRODUCT_CLOSURE_NO_FAL.md)
- [Profile Switch Acceptance](PROFILE_SWITCH_ACCEPTANCE.md)
- [Interactive Drama · 互动短剧平台](README.md)
- [Real H3 Max Multi-Shot Acceptance](REAL_MULTISHOT_ACCEPTANCE.md)
- [安全与已知限制（G28）](SECURITY_KNOWN_LIMITATIONS.md)
- [UI Size Acceptance](UI_SIZE_ACCEPTANCE.md)
- [Biohazard E2E Evidence Index](docs/acceptance/biohazard_full_e2e/EVIDENCE_INDEX.md)
- [Biohazard full E2E evidence index](docs/acceptance/biohazard_full_e2e/INDEX.md)
- [Relay Visual Continuation](docs/acceptance/biohazard_full_e2e/RELAY_VISUAL_CONTINUATION.md)
- [Live Creator parameter review and UI publication](docs/acceptance/biohazard_full_e2e/creator_review/README.md)
- [Relay Candidate Assets](docs/acceptance/biohazard_full_e2e/relay_assets/README.md)
- [Character scope browser regression](docs/acceptance/character_scope_regression/README.md)
- [Player stage control regression](docs/acceptance/player_stage_controls/README.md)
- [验收矩阵 · AT-01~AT-76](docs/acceptance/prd_v06_latest/AT01_76_HISTORICAL.md)
- [Latest PRD UX — implementation audit before changes](docs/acceptance/prd_v06_latest/GAP_AUDIT.md)
- [Evidence index · latest PRD v0.6 UX](docs/acceptance/prd_v06_latest/INDEX.md)
- [Effective generation preflight regression](docs/acceptance/preflight_safety/README.md)
- [Creator pressure contract regression](docs/acceptance/pressure_contract/README.md)
- [Creator publish safety regression](docs/acceptance/publish_safety/README.md)
- [Trajectory-driven skill optimization report](TRAJECTORY_DRIVEN_SKILL_OPTIMIZATION_REPORT.md)
- [Trajectory analysis evidence index](docs/trajectory-analysis/EVIDENCE_INDEX.md)
- [Current trajectory capture and replay benchmark](docs/trajectory-analysis/current_capture_20260926/README.md)
- [Trajectory-driven architecture decisions](docs/architecture/trajectory-driven/)

## 原始证据

- [生化危机证据目录](docs/acceptance/biohazard_full_e2e/)
- [10 张 Relay 视觉资产](docs/acceptance/biohazard_full_e2e/relay_assets/)
- [最新后端回归日志](docs/acceptance/biohazard_full_e2e/backend_regression_final.txt)
- [最新前端构建日志](docs/acceptance/biohazard_full_e2e/frontend_build_latest.txt)

历史报告按各自日期与范围解读；Mock、配置状态和旧测试不能替代真实 Provider 成功证据。密钥、环境文件、运行数据库与空临时文件不入库。
