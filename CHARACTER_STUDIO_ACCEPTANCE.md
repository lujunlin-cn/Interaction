# Character Studio Acceptance

日期：2026-09-24  
判定：**PARTIAL（代码与 API 已闭环，外部生图流程需人工浏览器复验）**

## 已接入

- `新建角色` 三入口：AI 创建、从图片创建、手动创建。
- AI 创建调用 `ai-generate` 请求 2 张 Candidate；图片创建调用
  `baseline-image` 形成身份 Candidate；手动创建形成无图片角色。
- Candidate → APPROVED → CANONICAL；选主图后二次确认生成标准多视图。
- `nano-banana-2/edit` 非破坏编辑，保留源图并生成新 Candidate。
- Outfit、版本/Diff、Scenario Snapshot、Local Override、Promote Global、Resolver
  均有正式 React 操作和 `frontend/src/api.ts` wrapper。
- Standard Mode 隐藏 Snapshot/Asset/Version ID、Provider、Model、Prompt、request ID、
  原始 JSON；Developer Mode 保留完整审计信息。

## 实测 API

本机对新角色 `chr_00001_4bddcd` 执行了手动创建 → 图片 Baseline → Candidate →
Canonical：`ca_00003_5cf0fb`，版本 `cv_00004_8b502f`，Resolver/快照接口仍可继续
使用。原始资产保持存在，Canonical 状态由后端真实变更。

AI 生图和标准多视图依赖 fal/nano-banana-2 配额，本轮没有用 Mock 把外部生图写成
PASS；需在有配额的浏览器会话按 Flow A～E 重新截图确认。
