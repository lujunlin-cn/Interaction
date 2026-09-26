# 安全与已知限制（G28）

封版基线（2026-09-23）。本文件如实记录当前安全边界——不夸大、不隐瞒。

## 密钥与凭据

- **只走 `backend/.env` / 环境变量**，`.env` 已在 `.gitignore`，不入 Git。
- 覆盖：StepFun（`STEP_API_KEY`）、fal（`FAL_KEY`）、Jev（`JEV_API_KEY`）、
  Sol-H3 adapter token、DB 连接串。
- Provider 内部构造 `Authorization` 头；**不写入** Trace span、日志、界面、
  返回体。`G29_MODEL_DEPLOY_AUDIT.md` 等文档中所有凭据均已脱敏
  （`<set-in-DGX-env>` 占位）。
- 验证：`git grep -iE "api_key|secret|token|fal_key|jev" backend/app` 无硬编码；
  `git ls-files | grep '\.env$'` 为空（`.env` 未被 track）。

## CORS（G28 收敛）

- `CORSMiddleware` 收敛为 `settings.cors_origins`（逗号分隔），**不再 `*`**。
- 默认白名单：同源 `47.108.220.174:9000` / `127.0.0.1:9000` + 本地 dev 端口
  （5173/4173）。生产同源部署下跨域头实际不触发，但收敛避免被任意站点跨域调 API。
- 实测：evil origin 预检 → 无 `Access-Control-Allow-Origin`；allowed origin →
  200 + 正确 `ACAO`。

## 无鉴权面（已知接受风险）

| 面 | 现状 | 风险 | 适用边界 |
| --- | --- | --- | --- |
| `/media` 生成产物 | `StaticFiles` 直挂，URL 即可访问 | 拿到路径即可读生成视频/装配产物 | 内网/演示 |
| `/files` 上传素材 | 同上 | 上传素材可被直读 | 内网/演示 |
| `/dev/*` 调试接口 | providers/inject、profile/switch、fixtures、jobs 无鉴权 | 知道路径即可注故障/切 profile | 验收脚本需要；公网应限制来源 |
| 会话 | `session_id` 即访问令牌 | 知道 sid 即可读状态/发 action | 单租户演示 |

**公网部署须知**：当前经 FRP 中转暴露公网属**已知接受风险**。正式公网需在前置
反代加鉴权或签名 URL（`/media`、`/files`），`/dev/*` 限制来源 IP/内网。

## 依赖与数据

- PG `interaction-drama-db` @`127.0.0.1:5433`（docker），仅本机回环。
- 外部 Provider 调用均出站到各自 API 域（StepFun/TypeSafe/fal/本地 adapter），
  凭据走 HTTPS `Authorization` 头。
- Trace span 记 provider/model/状态，**不记**请求体密钥、`.env` 值。

## 已修复的本轮安全/质量问题

- CORS `*` → 白名单（G28）。
- `G29_MODEL_DEPLOY_AUDIT.md` 中 `SOL_H3_API_KEY` 明文 → `<set-in-DGX-env>`。
- mock `_director_plan` `scenario_context` 提取吞入非 JSON 尾行 → `raw_decode`
  只取首个 JSON 对象（防 prompt 字段污染导致 ctx 解析失败静默丢 ops）。
