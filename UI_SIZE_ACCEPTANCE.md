# UI Size Acceptance

日期：2026-09-24  
判定：**PASS**

本轮移除了 `#root { zoom: ... }`，也没有使用 `transform: scale()`。UI Size 现在是
`standard / large / xlarge` 三档设计 token，分别调整字号、Sidebar 宽度、控件高度、
卡片内边距和工作区宽度；浏览器缩放保持 100%。旧 localStorage 的 `100/125/150` 会
自动迁移到三档语义值。

Settings 显示为：

- 界面大小：标准 / 大 / 特大
- 外观：跟随系统 / 浅色 / 深色
- 字幕：标准 / 大 / 特大 / 自动适应屏幕
- 位置：画面底部·内 / 画面底部·外

`npm ci && npm run build` 在本机真实执行成功。工作区使用 `90vw/94vw` 上限策略，
4K 不再固定为 1100px 中央小窗口；Sidebar 的中段保持 `overflow-y:auto`，底部设置
入口固定可达。

本轮用 Chromium headless 在 100% Browser Zoom 重新生成了五档截图，覆盖 Home、Creator、
Character Studio、Player、Settings：`docs/acceptance/final_ui/`。另在 1920×1080
分别以 standard/large/xlarge 生成 Settings 截图，确认三档同时改变阅读尺度和布局 token。
