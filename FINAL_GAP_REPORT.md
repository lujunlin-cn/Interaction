# Final Gap Report · PRD v0.6

最终应用代码候选：`15855a658a63626a0f17d64239ee3b3aecd25f57`。需求冻结/起点：`b055674aa0702fc1c1ed50f7c3ee62e4ea43dc88`。
本报告取代此前旧SHA和“旧现状→新修复”混合结论。详细验收见 [LATEST_PRD_UX_ACCEPTANCE.md](LATEST_PRD_UX_ACCEPTANCE.md)。

## CLOSED

- Q105–Q122：AI引导式Drama、统一角色Core/Overlay、自然语言玩法编译与教程、Player四层/容器全屏、HUD、Standard错误隔离、字幕与三种媒体状态。
- 本轮AT-77–90为13 PASS / 1 PARTIAL；AT-91–98为8 PASS，包含真实Step/Jev/Nemotron/H3，以及明确标注的真实媒体回放/故障注入。没有用Mock视频证明真实Provider。
- 本轮真实H3两Shot Opening、3个Ready候选及自由输入FREE视频；正式角色固定版本参考进入Production。
- 真实玩法行动发现并修正缺失Skill提案与初始关系缺失问题；重试经relationship Skill/StateManager写入关系55，World版本仅增1，失败恢复可用。
- 原始Schema错误仅Developer可见；失败重试、媒体重新载入、明确文字恢复、文字Ending和真实Step Continue World完成。
- 最新应用候选全量离线回归63 passed / 0 failed / 6 warnings，124.62秒；npm ci与tsc/Vite build exit 0。
- Firefox 100% Browser Zoom下五档分辨率×五页，1920三档UI Size，共35/35响应式检查；中文真实视频字幕与全屏截图均已更新。
- 已确认的公网服务、Nemotron部署和历史Sol-H3/Profile双向切换保持既有成果，不列为部署Gap。历史证据与本轮UX实测范围分开记录。

## PARTIAL

- AT-86最终候选新FREE视频：本轮较早的真实FREE视频成功，最后Director/关系修复后文字FREE成功；fal锁阻止再次验证新视频。
- 全视频用户E2E：Opening/推荐/FREE真实H3成功，视频Ending未完成；文字Ending成功不替代视频Ending。
- Character Studio新Nano Banana双Candidate、多视图、非破坏Edit完整外部生图流程本轮未重跑；本轮验证的是文字AI理解、复用真实图片上传基线、Overlay/Promote及Production引用。
- AT-01–76只重跑相关路径和完整离线契约测试；未覆盖的真实语义、边界、多模态或Profile用例没有沿用旧PASS作最新HEAD证明。

## BLOCKED

- fal账单锁：真实视频Ending请求 `01a0d481-3949-7f32-8d42-0ffed6de7010` 返回403 `User is locked. Reason: TOP_UP.`。保留 `fal_ending_failure.json`，不再重复提交付费视频请求。
- 独立真实体验者反馈（AT-44）尚无。自动化和开发者验收不能伪装真实用户反馈。

## REMAINING

- P0：fal恢复后补视频Ending及连续视频完整回归；补Character Studio外部生图完整浏览器Flow。
- P1：补本轮范围外的AT-01–76语义/多模态/边界样本与独立试玩。矩阵中PARTIAL包含“本轮未全面复测”，不等于已实现能力丢失。
- 本轮不扩展账号、多租户或新的模型部署范围。hybrid仍允许显式Mock降级；真实验收使用live，并逐分支核对provenance。

- 运维P1：生产库有2条旧standalone生成记录和2个旧Session的中断分支（约28小时以上未更新），对应旧验收任务；本轮只保留原记录，不用改enum伪造完成。新Session验收与它们隔离。

## 本轮无费用收口（2026-09-25）

- Fal 付费开关默认 `false`，`403 TOP_UP/User is locked` 分类为 `BILLING_LOCKED` 并打开进程熔断；本轮 Fal paid HTTP POST 为 0。
- 图片/视频 resolution、aspect ratio、Developer 测试限制和 preflight 已贯通；后端 63 passed，前端 build PASS。
- 充值后的 Paid-01 Character、Paid-02 FREE H3、Paid-03 Video Ending 仍保持 PARTIAL/BLOCKED，见 [NO_COST_E2E_ACCEPTANCE.md](NO_COST_E2E_ACCEPTANCE.md)。

## 本轮 Product Closure（No-Fal）

- CLOSED：应用内 Theater Mode、媒体设置参数链、Developer Test Override、Paid Guard、Billing Circuit、Usage Ledger/Preflight、纯文字角色 Publish warning。
- PARTIAL：角色库与 Creator 的完整 Outfit/Voice/Pose/Motion 同颗粒度仍需一次完整非付费浏览器回归；角色外部生图流程不在本轮执行。
- BLOCKED：Fal 额度未恢复，Paid-01/02/03 继续等待充值；AT-44 独立体验者反馈仍无外部条件。
- REMAINING：充值后只执行三个付费路径，不扩展产品范围。详细证据见 `PRD_V06_PRODUCT_CLOSURE_NO_FAL.md`。
