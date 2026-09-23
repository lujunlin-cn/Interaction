/** 原型说明页：架构与术语对照。 */
import React from "react";

export default function Notes() {
  return (
    <>
      <div className="card">
        <h3>这是什么</h3>
        <p>互动短剧平台：创作世界 → 自由行动 → 看见后果 → 继续这个世界。</p>
        <p className="muted">
          业务行为以 PRD v0.5 为准；本实现把原型中的 Mock Runtime 替换为真实的
          FastAPI + PostgreSQL 后端（双域 Proposal→Validate→Commit、分支状态机、指纹失效、
          Provider Router 熔断降级、FFmpeg 确定性装配）。
        </p>
      </div>
      <div className="card">
        <h3>术语隔离</h3>
        <p className="muted">
          玩家界面只出现自然中文（如「正在生成画面」）；PROVISIONAL / CANONICAL /
          JEV_ANALYZING 等技术词只在开发者模式中出现。
        </p>
      </div>
      <div className="card">
        <h3>Provider 模式</h3>
        <p className="muted">
          mock：全部 Mock Provider（离线零费用，Mock 只替换 Provider 不替换业务 Runtime）；
          live：PRD 冻结矩阵（Nemotron Lightning 本地 / StepFun / fal H3 / Jev）；
          hybrid：按冻结矩阵路由，真实 Provider 不可用时显式降级并记录路由事件。
        </p>
      </div>
    </>
  );
}
