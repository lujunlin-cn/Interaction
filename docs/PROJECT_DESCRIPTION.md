# Interaction：面向 Agent Skills 的互动短剧平台

> 一句话介绍：让玩家用自己的行动改变一部由 Agent Skills 协同创作、生成和维护状态的互动短剧。

## 项目概述

Interaction 是一个由多个 Agent Skills 协同驱动的互动短剧创作与游玩平台。它把“写故事、做角色、排练分支、生成镜头、让玩家行动”放进同一条可追踪的工作流：创作者可以用自然语言描述主题，系统先给出可编辑的理解结果，再由创作者确认世界、戏剧冲突、角色和机制；玩家进入故事后，每一回合都可以选择推荐行动，也可以直接输入自己的行动。系统会记录玩家意图、当前世界状态、角色关系、物品和线索，并在分支达到 READY 后才把它呈现给玩家。

项目的核心不是把一个超长 Prompt 接到网页上，而是把互动剧情拆成职责清晰、可组合、可观察的 Agent Skills。Understand Free Action 负责把自由输入整理为带来源的行动语义包；Evaluate Choices 负责结合当前剧情生成并排序推荐；Reconcile Mechanics 负责协调物品、线索、关系和限时机制；Narrative 负责把已批准的导演结果写成场景文本；Production 负责规划镜头和媒体任务；StateManager 是唯一的正式状态提交入口。每个 Skill 都有版本、输入输出契约、失败回退和调用轨迹，开发者模式可以查看“为什么触发、提出了什么、是否被接受、耗时多久”。

## 我们解决什么问题

传统互动短剧通常在两个极端之间选择：固定分支足够稳定，但玩家的自由输入没有真正影响；全交给一个大模型足够灵活，却容易出现角色身份漂移、状态前后矛盾、选项同质化和媒体失败后无法恢复。Interaction 把“理解行动”和“提交世界状态”分开，把 Agent 的创造性限制在可检查的 Proposal 内，再由确定性的 Runtime 和 StateManager 完成校验与提交。这样既保留生成式剧情的开放性，也能让每一步有来源、有状态、有回退。

## 设计原则

1. **玩家行动优先**：推荐只是入口，自由输入始终可用；原文、确认后的意图和最终后果都可追溯。
2. **状态先于文案**：Narrative 只能渲染已批准事实，不能凭空增加角色知识、物品或世界规则。
3. **准备完成才呈现**：只有 READY 分支才能成为玩家可选内容；媒体失败必须显式呈现为可恢复错误。
4. **外部服务可替换**：Provider Router 隔离模型和供应商，mock、live、hybrid 都使用同一套业务契约。
5. **真实成本可控**：Jev 预生成视频默认关闭，付费媒体由显式开关保护，离线回归不访问外部 Provider。

## 用户流程

1. **创建故事**：在 Standard UI 输入一句自然语言描述，查看 AI 理解和澄清问题，确认后写入结构化 World、Drama、Character 和 Mechanics。
2. **管理角色**：为角色建立身份参考组、造型、姿势、声音和版本；Scenario 发布时固定 Character Snapshot，避免全局角色后续编辑悄悄改变历史故事。
3. **发布前检查**：系统校验世界设定、戏剧参数、机制配置、角色快照和媒体引用。未通过检查的草稿不能伪装成已发布故事。
4. **开始游玩**：Opening 场景完成后，玩家在 Decision Lead 看到已锁定的推荐。推荐媒体是否 READY 与文字选项呈现分离，失败时可以重试、改写行动或切换为文字继续。
5. **行动产生后果**：玩家可以选择推荐，也可以输入“我去配电室寻找备用电源”这样的自由行动。系统保留原文和确认后的意图，再由导演、机制 Skills、叙事和制作管线共同推进下一幕。
6. **分支与世界延续**：选中的分支按 SELECTED → PROVISIONAL → CANONICAL 状态提交；失败分支会回滚，不污染正式世界。玩家可以在 Arc 结束后继续世界，新的 Session 仍从已发布版本开始。

## 一条行动如何穿过 Agent Skills

```mermaid
flowchart LR
    A[玩家自由输入] --> B[Understand Free Action]
    B --> C[Director Planning]
    C --> D[Reconcile Mechanics]
    D --> E[StateManager Proposal 校验]
    E --> F[Narrative]
    F --> G[Production / Visual QA]
    G --> H[READY 后呈现]
    H --> I[Canonical Commit]
```

每个节点都写入可检索的 trace span。媒体生成失败只会让分支进入可恢复状态，不会跳过 READY 门槛或伪造 Canonical 结果。

## 系统组成

```text
frontend/                 React 页面、Theater Player、Creator、Developer Inspector
backend/app/api/          REST 与 WebSocket 接口
backend/app/runtime/      RuntimeEngine、分支生命周期、会话与语言设置
backend/app/domain/       StateManager、Scenario、Character Snapshot、契约模型
backend/app/providers/    本地/外部/Mock Provider 与路由器
backend/app/skills/       Agent Skills、Proposal 和触发策略
deploy/                   PostgreSQL Compose、后端和 Nemotron 启动脚本
```

## 核心演示脚本

评审现场可以用以下顺序在不暴露密钥的情况下演示产品：

1. 在 Story Creator 输入一句故事设定，展示 AI 理解、澄清和可编辑结果。
2. 打开 Character Studio，展示角色身份参考组、版本和 Scenario Snapshot。
3. 发布故事后进入 Theater Player，先选择一条推荐，再输入一条不在推荐中的自由行动。
4. 在 Developer Inspector 打开 Skill Chain，展示行动语义包、机制 Proposal、Narrative 和分支状态。
5. 打开一次失败或 mock 媒体任务，展示重试、文字继续和状态回滚，不把错误伪装成成功。

完整现场部署只需要先启动 mock 模式；接入真实 Provider 后，可以逐项打开文本、图片、决策和视频能力。

## 如何评价系统

项目的评价对象不是单次模型回答，而是完整的行动链：

- **Free Action Fidelity**：最终剧情是否保持玩家原始策略和约束。
- **Choice Diversity**：推荐是否在行动、风险、信息价值和目标上有真实差异。
- **Mechanic Precision/Recall**：物品、线索、关系和限时机制是否在该触发时触发。
- **State Consistency**：叙事、角色知识、库存和世界状态是否一致。
- **Ready Latency / Recovery Success**：玩家多久看到可用结果，以及失败后能否继续。
- **Cost Safety**：付费图片、视频和重试是否有明确计数和开关。

这些指标可以通过 mock 测试、只读 Replay 和真实 Provider 的服务端 trace 逐步采集，避免把一次偶然生成结果当作系统能力。

## Agent Skills 的工程特点

- **有边界**：Skill 只读取契约允许的上下文，只提出 Proposal，不绕过 StateManager 直接修改世界。
- **可组合**：一次行动可以依次经过自由行动理解、机制协调、导演规划、叙事和视频制作，而不是由单一代理包办所有判断。
- **可版本化**：Skill manifest 记录版本、触发条件、依赖、失败语义和评估指标，轨迹中保存每次调用的输入摘要与结果。
- **可恢复**：Provider 超时、格式错误、媒体失败和重复提交都有显式状态与幂等保护；系统不会把错误页或假媒体当成成功。
- **可评估**：项目提供冻结轨迹、只读 Replay 和 Before/After 指标，可分析自由行动保真度、推荐差异性、机制触发质量、上下文规模和 Ready 延迟。

## 技术与创新亮点

平台采用 React + TypeScript 前端、FastAPI 异步后端和 PostgreSQL 持久化，统一由 Provider Router 管理本地模型与外部 API。DGX Spark 上运行 NVIDIA Nemotron 3.5 Lightning，为导演和制作规划提供低延迟本地推理；StepFun Step 3.7 Flash / Step 5 Preview 用于叙事、创作理解和回退；Jev 负责决策评估；图片使用 OpenAI-compatible Image Relay，视频使用 fal.ai 的 `minimax/h3-max/reference-to-video`。所有 Provider 都可以切换到 mock 模式进行无费用回归。

项目特别重视状态安全和证据链：分支有 READY 门槛，Canonical 状态采用两阶段提交，角色引用解析到不可变 Snapshot，所有媒体任务记录 Provider、模型、时长和重试；外部凭据只存在于服务端 Secret，不进入前端、Git 或轨迹。这样既能展示 Agent Skills 的协作过程，也能让评审复现一条从玩家输入到剧情结果的完整因果链。

## 运行方式与边界

开发者可以使用 mock 模式快速演示创建、发布、游玩和恢复流程；需要真实文本、图片或视频时，再按部署说明逐个配置 Provider。仓库公开文档不包含历史验收材料、运行数据库或凭据。真实 Provider 的费用、模型许可证、服务可用性和公网安全责任由部署者承担。
