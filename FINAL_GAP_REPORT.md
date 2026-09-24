# FINAL GAP REPORT — 互动短剧封版审计

审计基线：PRD v0.6（唯一业务 SoT）+ `interactive_drama_prototype.html`（UI 参考）+ 当前后端/前端全量代码 + DGX Spark 历史实测（2026-09-24 更新）。

> 前一版 v0.5 / Nemotron 未部署结论已过期。Nemotron Lightning 已在本机 vLLM 容器真实启动并完成中文 JSON 与 1/2/4 路并发验证；Sol-H3 本轮未重新取得 DGX 产物，因此保持 PARTIAL。
判定标准：「类/接口/字段存在」≠ 完成。完成 = 用户可操作 + Runtime 真执行 + Provider/状态真变化 + Trace 可查 + 正常/失败路径可复现。

## DGX 实测快照（2026-09-24）

- 服务：uvicorn :9000 运行中，commit `6e8b826`，`PROVIDER_MODE=hybrid`，`AGENT_LOCAL_PROFILE`，/api/health OK。
- 硬件：NVIDIA GB10（CUDA 13.0，driver 580.159.03），内存 121G 已用 102G。
- Nemotron Lightning：vLLM 0.27.1-aarch64 监听 `127.0.0.1:8001`，`/v1/models` 返回 `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`；中文 JSON 冒烟成功，GPU 进程约 80,329 MiB。
- Director 并发：直连 vLLM 的 1/2/4 路三轮成功率为 3/3、6/6、12/12；4 路未见 OOM/timeout。业务 admission 默认 2，队列超时回退 Step 5。
- Ollama：可作为显式降级 Provider，但不再冒充 Nemotron。
- PG：`interaction-drama-db` @127.0.0.1:5433 正常。
- Sol-H3 本地视频：adapter 已实现真实 submit/status/cancel/health；本轮未重新取得目标机出片产物，结论为 PARTIAL。
- ComfyUI @8188 在跑（与本案无关）。

## Gap Checklist

| # | 区域 | PRD/总纲要求 | 现状 | Gap | 修复 | 验证 |
|---|------|--------------|------|-----|------|------|
| G01 | Runtime 泛化（P0）| 候选来自 Scenario+World+Drama+Arc+Preference+Wishes+Pressure+Director+Jev | `candidate_actions()` L290-337 硬编码 foyer/Alice/钥匙/储物柜/录音/车票/离开公寓 | 灯塔失踪案等新 Scenario 推荐仍是雨夜公寓候选 | Director 生成候选（World/Drama 上下文注入）→ Jev rank → 确定性兜底（观察/对话/离开三类通用模板按 locations/characters 参数化） | 「废弃灯塔失踪案」端到端：创建→发布→游玩→候选含灯塔语义、无 Alice/foyer |
| G02 | patch 白名单 | 约束操作类型/namespace/schema | `ALLOWED_PATCH_PATHS` 写死 `objects.back_door/recording/alice_*` | 新 Scenario 的 objects.* 无法落盘；location 单值白名单 | 改为 namespace 白名单：`location`（值须 ∈ Scenario locations）、`objects.*`、`clues.*`、`relationships.*`、`truth.*`、`inventory`、`fiction_minutes` 各配 op schema；禁止任意路径 | 灯塔案 patch `objects.lighthouse_log` 可提交；`evil.root` 被拒 |
| G03 | 双域原子提交 | world+drama 全成功才落版本 | `_commit_branch` L1077 先替换 `state.world` 再验 drama，drama 失败留半提交 | AT-09/40 必现缺陷 | 两域先在副本 validate，全部通过后一次性赋值；`committed_keys` 同事务追加 | 注入 drama proposal 失败 → world.version 不变 |
| G04 | 两阶段 Canonical | PROVISIONAL 可观察、媒体确认、失败回滚 | PROVISIONAL 瞬时（同函数内），媒体只查文件存在；catch 不回滚 world/drama | 形式合规实质缺失 | PROVISIONAL 阶段显式 persist+push；媒体校验失败 → branch FAILED + state 回滚 + 事件 | AT-50 失败注入测试：媒体缺失注入 → 回滚可断言 |
| G05 | 标签/结局文案 | 从 Scenario snapshot 读 | `CLUE_LABELS`/`ENDING_TITLES`/`ENDING_FAMILIES` 全局常量 | 新 Scenario 的 clue/ending family 无中文名（回退裸 id） | 解析 snapshot `ending_families`/`foreshadows`/`truth_model` 的 `id｜描述` 行建映射；未声明的 family 回退通用文案 | 灯塔案 ending family 显示其声明文案 |
| G06 | WorldState 默认值 | — | `location` 默认 `"foyer"` | 无 locations 的 Scenario 起始位置错 | `_bootstrap` 已用 locations[0]；schemas 默认值改中性 `"start"` | 新建空 Scenario 游玩不报错 |
| G07 | Mock Director | Mock 也应 Scenario 泛化 | `rule_based_outcome` 全雨夜公寓语义（alice/recording/backyard） | 灯塔案 Mock 模式下行为仍错（但文本通用） | 抽取规则保留但按 snapshot 参数化：角色名/location/物品从 snapshot 读；无法命中时通用 outcome | Mock 模式灯塔案不产出 alice 相关内容 |
| G08 | Mock Narrative | — | `_narrative` 返回 `speaker: "alice"` 写死 | 角色库第一人名应为在场 NPC | speaker 用 snapshot 首个非玩家角色 id | 断言无 "alice" |
| G09 | 三模态 references | references→provider adapter 不静默丢 | `_bound_references` 产 refs 进 `submit({"references":...})`；FalH3 adapter 只转发 `image_url/reference_*_urls` 而 engine 给的是 `references` | **真实 H3 调用 references 静默丢失** | Provider 侧加 request adapter：`references[]`（按 type image/voice/video + path）→ fal 的 `reference_image_urls`/`reference_audio_urls`/`reference_video_urls`；Sol-H3 同契约；request.json 落盘可审计 | 上传绑定 alice 图片 → 生成 request.json 含 reference_image_urls |
| G10 | Sol-H3 Adapter | 真实 submit/status/cancel/health | 全部占位 raise | VIDEO_LOCAL_PROFILE 不可用 | 实现基于本地推理服务的 adapter（Spark 无 Sol-H3 运行实例 → 实现代码 + 标 BLOCKED 实测） | 代码实现 + capabilities 实测记录 |
| G11 | 角色库 | 搜索覆盖 name/bio/tags/personality；资产上传/绑定/预览；snapshot 三选一 | `CharacterService.list` 搜索不含 personality；前端 CharacterDetail 的 ref_* 只读 chip，无上传/选择/删除/预览/绑定 UI | 资产链断 | PATCH 已支持字段；前端加资产选择器（列出 assets + 预览 + 绑定到 ref_*） | 绑定 asset→角色 ref_front → snapshot 隔离验证 |
| G12 | 角色 snapshot→Production | snapshot references 真进生产 | `_bound_references` 只扫 asset_manifest（Scenario assets），不读角色 ref_* | 角色绑定图不进视频请求 | `_bound_references` 合并：在场角色的 global ref assets（经 snapshot 版本固定） | 灯塔案角色绑图 → request.json references 含该 asset |
| G13 | 全局显示设置 | Appearance/UI Size/Subtitle 四档+位置+预览 | Settings 页只有模式切换+运行信息 | 整块缺失 | store 加 display 配置（localStorage）+ CSS 变量档位；设置页三组控件+实时预览 | 切深色/大字号全组件生效 |
| G14 | 响应式 | 100% zoom 为基准；禁 11/12px 核心字号 | 全文 12/13px；需 150% zoom 才正常 | 设计基准错误 | 设计 token（--font-xs 12px 仅徽章/--font-sm 13/--font-md 15/--font-lg 17/--font-xl 22）+ sidebar/content 宽度 token + media query | Playwright 五档 viewport 截图 |
| G15 | Creator Theme | accent/font/density/subtitles/background+预览 | 只有 accent color+subtitles 两项 | font/density/background/预览缺 | ThemeConfig 字段已有；补控件+预览面板 | 预览随选项变化 |
| G16 | 局部编辑 typed patch | instruction→{path,before,after,reason,source} | `apply_instruction` 只改写 description | patch 不 typed、不碰其他字段、无 lock 检查 | authoring contract 返回 patches[]；服务端按路径应用（drama.*/world.*/characters[].*），locks 内字段拒绝 | 「把核心问题改成X」→ drama.core_question 变化，changes 有记录 |
| G17 | Changes 日志 | 字段/Before/After/来源/时间 | `manual_edits` 只是字段名列表 | 无结构化日志 | ScenarioDraft 加 `changes: [{path,before,after,source,at}]`；save/instruct 两路写入；changes tab 渲染表格 | 编辑+AI 修改均有行 |
| G18 | Publish Gate | 服务端校验 11 项+「我已审阅」 | `publish()` 直接 `reviewed=True` | 后端自置 reviewed；无校验 | publish 服务端跑 checklist（title/world rules/角色引用/core question/truth/pressure/ending family/timed/mechanic/asset refs/char snapshot），失败 422 列表；req 体需 `reviewed: true` | 空 truth_model 发布被拒；勾审阅后成功 |
| G19 | 发布并试玩 | 按钮一键 | 无 | 发布后手动回故事库 | publish 成功后直接 createSession→跳 Player | 点击即进游玩 |
| G20 | 素材页 | binding/entity/role/authorization/canonical/trim/时长/用途标记 | 只传 binding/entity；无 role/authorized/canonical/trim UI | schema 字段闲置 | 上传表单+行内编辑补全字段（role 下拉、authorized/canonical 勾选、video trim_start/end、参考用途标记） | 保存后 dev/state 可见字段 |
| G21 | Developer 隐藏 | 标准模式隐藏 | Sidebar 未读 | 需确认 Sidebar 是否按 mode 过滤 | Sidebar 加 mode gate | 标准模式无 Developer 入口 |
| G22 | Profile 状态机 | 七态可见 | `switch_profile` 有 DRAINING..ACTIVE 但 history 无时间线/时长；前端只显示当前态 | 过程不可观察 | history 记录每态 at+耗时；前端 RuntimeTab 渲染 timeline | 切换时逐态可见 |
| G23 | Sol-H3 任务 UI | Job ID/模型/GPU/Profile/起止/status/output/error | ProductionTab 只回显一次提交结果 | 无任务列表/轮询 | JobRow 已有；加 GET /dev/jobs 列表+status 轮询 | 提交后可见状态迁移 |
| G24 | Skill 审计 | 版本/used_by/最近调用/输入输出 artifact | registry 静态；toggle 有；无调用记录 | 审计链断 | tracer emit 时带 skill_id/skill_version（已支持字段）；SkillsTab 加「最近调用」列（查 TraceSpan） | 禁用后 trace 可查阻塞记录 |
| G25 | Wish 七态 | ACTIVE/DEFERRED/CONFLICTED/PARTIALLY/FULFILLED/FAILED/WITHDRAWN+reason/evidence | Wish 模型有 8 态但只迁移 ACTIVE→WITHDRAWN；玩家端只显示 ACTIVE | 生命周期只有两态被用 | 提交分支时按 outcome 与 wish scope 评估：fulfilled/partial/conflict；Ledger 记录 reason/evidence/at/branch；玩家端友好文案 | 许愿「希望平安离开」+完成离开结局 → FULFILLED 可断言 |
| G26 | Mechanic Skill 闭环 | trigger→Skill→versioned input→Proposal→validate→commit→Trace→UI→下一拍 | Mock outcome 里 `mech_enabled()` 直接产 ops——Skill 没有独立 Proposal 步骤与 Trace | 「Registry+if」模式 | relationship/clue 做成显式 invocation：director 返回 trigger → runtime 调 skill fn → Proposal（带 skill_version+input）→ state_manager → trace | trace 有 `skill.relationship` span，v1.0.0，输入输出可查 |
| G27 | 自由输入失败恢复 | 重试/修改输入/取消 | 分支 FAILED 后前端只 toast | 无重试入口 | view 加 `last_failed_action`；前端给重试按钮（重发 action） | 注入失败后点重试成功 |
| G28 | Security | key 不入 Git/trace/UI | FalH3 header Key 在 provider 内；trace 不记 key ✓；CORS `*` | CORS 过宽；media/files 目录无鉴权（内网可接受，文档注明） | CORS 收敛为同源；KNOWN_LIMITATIONS 注明 | grep 无 key 泄露 |
| G29 | Nemotron 部署 | 真实 NVFP4 在 Spark | vLLM 8001 已监听，模型 ID 与中文 chat 已核实 | 并发长稳态仍需持续压测 | vLLM 容器启动脚本、固定模型配置、admission control、并发探针 | `/v1/models` + 中文 JSON + 1/2/4 路报告 |
| G30 | AT-01~60 | 逐条矩阵 | 无 | 交付物缺 | ACCEPTANCE_MATRIX.md 按实测填写；BLOCKED 不伪造 | 文件交付 |
| G31 | 前端补充 | Decision Lead/选择反馈/Ending 已有；Hint chips 已有 | Player 基本完整；缺：失败重试(G27)、subtitle 设置生效、wish 状态文案(G25) | — | 随 G13/G25/G27 | — |
| G32 | Prototype 对照 | Intent Echo/Timed/Lead/状态面板/反馈/Ending | 均存在；玩家状态面板无 secret/confidence/fingerprint ✓ | 待逐项浏览器复验 | Playwright 回归 | 截图留证 |

## 修复顺序（本报告执行计划）

1. **G01/G02/G05/G06/G07/G08** Runtime 泛化（engine + state_manager + mock_text）→ 灯塔案验证
2. **G03/G04** 原子提交 + 两阶段 → 失败注入测试
3. **G09/G12** references adapter + 角色 snapshot 进生产
4. **G18/G16/G17/G15/G20/G11/G19** Creator/素材/角色库闭环
5. **G13/G14** 设置 + 响应式
6. **G22/G23/G24/G21** Developer 控制台
7. **G25/G26/G27** Wish/Mechanic/恢复
8. **G29** DGX 模型部署核查 → 报告
9. **G30/G32** 验收矩阵 + 浏览器回归 + 五份交付报告
