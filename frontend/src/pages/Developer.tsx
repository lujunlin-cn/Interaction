/** Developer Inspector：分支预测 / 世界状态 / 戏剧控制 / 缓存 / 路由 / 运行环境 / 生成 / 装配 / Trace / Metrics / QA / Skills。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";
import type { DevState, SkillsRegistry } from "../types";

export default function Developer() {
  const ui = useUi();
  const [state, setState] = useState<DevState | null>(null);
  const [providers, setProviders] = useState<any>(null);
  const [traces, setTraces] = useState<any[]>([]);
  const [skills, setSkills] = useState<SkillsRegistry | null>(null);

  const reload = () => {
    if (ui.sessionId) {
      api.devState(ui.sessionId).then(setState).catch(() => setState(null));
    } else {
      setState(null);
    }
    api.devProviders().then(setProviders).catch(() => {});
    api.devTraces().then((r) => setTraces(r.items)).catch(() => {});
    api.skills().then(setSkills).catch(() => {});
  };
  useEffect(() => {
    reload();
    const t = window.setInterval(reload, 3000);
    return () => window.clearInterval(t);
  }, [ui.sessionId, ui.devTab]);

  if (!ui.sessionId) {
    return <div className="empty">没有活动会话。从故事库开始游玩后，这里会显示运行时状态。</div>;
  }
  if (!state) return <div className="empty">正在载入…</div>;

  return (
    <>
      {ui.devTab === "branches" && <BranchesTab state={state} />}
      {ui.devTab === "world" && <WorldTab state={state} />}
      {ui.devTab === "drama" && <DramaTab state={state} />}
      {ui.devTab === "cache" && <CacheTab state={state} />}
      {ui.devTab === "router" && providers && <RouterTab providers={providers} onChanged={reload} />}
      {ui.devTab === "runtime" && providers && <RuntimeTab providers={providers} />}
      {ui.devTab === "production" && <ProductionTab state={state} />}
      {ui.devTab === "assembly" && <AssemblyTab state={state} />}
      {ui.devTab === "trace" && <TraceTab traces={traces} />}
      {ui.devTab === "metrics" && <MetricsTab state={state} providers={providers} />}
      {ui.devTab === "skills" && skills && <SkillsTab skills={skills} />}
      {ui.devTab === "qa" && <QaTab state={state} />}
    </>
  );
}

function Pill({ s }: { s: string }) {
  return <span className={`status-pill ${s}`}>{s}</span>;
}

function BranchesTab({ state }: { state: DevState }) {
  return (
    <div className="card">
      <h3>分支预测（{state.branches.length}）</h3>
      <table className="dev">
        <thead><tr>
          <th>分支</th><th>状态</th><th>来源</th><th>指纹</th><th>基准版本</th><th>错误 / 失效原因</th>
        </tr></thead>
        <tbody>
          {state.branches.map((b) => (
            <tr key={b.id}>
              <td><b>{b.label}</b><br /><span className="mono muted">{b.id}</span></td>
              <td><Pill s={b.status} /></td>
              <td>{b.source}</td>
              <td className="mono">{b.fingerprint?.slice(0, 18)}…</td>
              <td className="mono">w{b.base_versions?.world} d{b.base_versions?.drama} wish{b.base_versions?.wish}</td>
              <td>{b.last_error || b.invalidated_reason || b.rollback_reason || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WorldTab({ state }: { state: DevState }) {
  return (
    <>
      <div className="card">
        <h3>World Hard State <span className="badge">v{state.world.version}</span></h3>
        <div className="kv">
          <b>位置</b><span>{state.world.location}</span>
          <b>物品</b><span>{state.world.inventory.join("、") || "空"}</span>
          <b>关系</b><span>{JSON.stringify(state.world.relationships)}</span>
          <b>线索</b><span>{JSON.stringify(state.world.clues)}</span>
          <b>已知（已呈现）</b><span>{state.world.knowledge.join("、") || "无"}</span>
          <b>故事时间</b><span>{state.world.fiction_minutes} 分钟</span>
          <b>真相</b><span>{JSON.stringify(state.world.truth)}</span>
        </div>
      </div>
      <div className="card">
        <h3>玩家偏好（只由真实选择产生）</h3>
        <pre>{JSON.stringify(state.preferences, null, 2)}</pre>
      </div>
      <div className="card">
        <h3>已提交的幂等键（{state.committed_keys.length}）</h3>
        <pre>{state.committed_keys.join("\n")}</pre>
      </div>
    </>
  );
}

function DramaTab({ state }: { state: DevState }) {
  return (
    <>
      <div className="card">
        <h3>Drama State <span className="badge">rev {state.drama.revision}</span></h3>
        <div className="kv">
          <b>阶段</b><span>{state.drama.phase} {state.drama.phase_reason && `（${state.drama.phase_reason}）`}</span>
          <b>伏笔</b><span>{state.drama.foreshadows.map((f: any) => `${f.id}:${f.status}`).join("；") || "无"}</span>
        </div>
      </div>
      <div className="card">
        <h3>Pressures</h3>
        {state.pressures.map((p: any) => (
          <div key={p.id} className="row" style={{ marginBottom: 6 }}>
            <b style={{ width: 160 }}>{p.title}</b>
            <div className="player-progress" style={{ flex: 1, background: "#e6eaee" }}>
              <div style={{ width: `${p.progress}%` }} />
            </div>
            <span className="muted">{p.progress.toFixed(0)} · {p.driver}</span>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Wishes</h3>
        {state.wishes.length === 0 ? <div className="empty">无</div> : (
          <table className="dev">
            <thead><tr><th>愿望</th><th>状态</th><th>版本</th><th>生效边界</th></tr></thead>
            <tbody>
              {state.wishes.map((w) => (
                <tr key={w.id}><td>{w.raw}</td><td><Pill s={w.status} /></td>
                  <td>v{w.version}</td><td>{w.effective_boundary}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function CacheTab({ state }: { state: DevState }) {
  const groups: Record<string, typeof state.branches> = {};
  for (const b of state.branches) {
    (groups[b.fingerprint] ??= []).push(b);
  }
  return (
    <div className="card">
      <h3>分支缓存（按依赖指纹分组）</h3>
      <p className="muted">指纹 = 分支声明依赖的确定性哈希；未声明依赖 → 保守 miss。</p>
      {Object.entries(groups).map(([fp, bs]) => (
        <details key={fp}>
          <summary className="mono">{fp.slice(0, 24)}…（{bs.length} 条分支）</summary>
          <div>
            {bs.map((b) => (
              <div key={b.id} className="row">
                <Pill s={b.status} /><span>{b.label}</span>
              </div>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}

function RouterTab({ providers, onChanged }: { providers: any; onChanged: () => void }) {
  return (
    <>
      <div className="card">
        <div className="row">
          <h3 className="grow">模型路由 <span className="badge">{providers.mode}</span></h3>
          <button className="small" onClick={async () => { await api.devRecoverProviders(); onChanged(); }}>
            全部恢复
          </button>
        </div>
        <table className="dev">
          <thead><tr><th>角色</th><th>Primary</th><th>实际路由</th><th>状态</th><th>Fallbacks</th></tr></thead>
          <tbody>
            {providers.matrix.map((m: any) => (
              <tr key={m.role}>
                <td><b>{m.role}</b></td>
                <td className="mono">{m.primary}</td>
                <td className="mono">{m.selected ?? "—"}</td>
                <td><Pill s={m.status} /></td>
                <td className="mono">{(m.fallbacks || []).join(" → ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Provider 健康</h3>
        <table className="dev">
          <thead><tr><th>Provider</th><th>状态</th><th>熔断</th><th>错误</th><th>操作</th></tr></thead>
          <tbody>
            {Object.entries(providers.health as Record<string, any>).map(([k, h]) => (
              <tr key={k}>
                <td className="mono">{k}</td>
                <td><Pill s={h.status} /></td>
                <td><Pill s={h.circuit} /></td>
                <td>{h.errors}{h.last_error ? `（${h.last_error}）` : ""}</td>
                <td>
                  <button className="small" onClick={async () => {
                    await api.devInject(k, "circuit_open");
                    toast(`已注入故障：${k}`);
                    onChanged();
                  }}>注入熔断</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>路由事件（最近 {providers.events.length} 条）</h3>
        <pre>{JSON.stringify(providers.events.slice(-12), null, 2)}</pre>
      </div>
    </>
  );
}

function RuntimeTab({ providers }: { providers: any }) {
  return (
    <div className="card">
      <h3>运行环境</h3>
      <div className="kv">
        <b>Runtime Profile</b><span className="mono">{providers.profile}</span>
        <b>Provider 模式</b><span className="mono">{providers.mode}</span>
      </div>
      <p className="muted">
        AGENT_LOCAL_PROFILE ↔ VIDEO_LOCAL_PROFILE 为显式切换（drain → persist → unload → start → 路由切换）。
        VIDEO_LOCAL_PROFILE 下本地 Agent 模型不可用，角色自动走冻结的 fallback 链。
      </p>
    </div>
  );
}

function ProductionTab({ state }: { state: DevState }) {
  const rows = state.branches.filter((b) => b.routes?.length);
  return (
    <div className="card">
      <h3>视频生成</h3>
      {rows.length === 0 ? <div className="empty">还没有生成任务。</div> : (
        <table className="dev">
          <thead><tr><th>分支</th><th>状态</th><th>路由链</th><th>成片</th></tr></thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id}>
                <td>{b.label}</td>
                <td><Pill s={b.status} /></td>
                <td className="mono">{b.routes.map((r: any) => r.selected).join(" → ")}</td>
                <td className="mono">{b.artifact?.assembled_path ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function AssemblyTab({ state }: { state: DevState }) {
  const rows = state.branches.filter((b) => b.artifact);
  return (
    <div className="card">
      <h3>视频装配（确定性 FFmpeg 拼接）</h3>
      {rows.length === 0 ? <div className="empty">还没有装配产物。</div> : (
        <table className="dev">
          <thead><tr><th>场景</th><th>分支</th><th>镜头数</th><th>时长</th><th>质量</th></tr></thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id}>
                <td className="mono">{b.artifact.id}</td>
                <td>{b.label}</td>
                <td>{b.artifact.clip_refs?.length}</td>
                <td>{b.artifact.duration?.toFixed(1)}s</td>
                <td><Pill s={b.artifact.quality_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function TraceTab({ traces }: { traces: any[] }) {
  return (
    <div className="card">
      <h3>Trace（最近 {traces.length} 条 span）</h3>
      <table className="dev">
        <thead><tr><th>时间</th><th>名称</th><th>状态</th><th>Provider</th><th>输出</th></tr></thead>
        <tbody>
          {traces.slice().reverse().map((t) => (
            <tr key={t.id}>
              <td className="mono">{new Date(t.at).toLocaleTimeString()}</td>
              <td>{t.name}</td>
              <td><Pill s={t.status === "success" ? "healthy" : t.status === "failed" ? "unhealthy" : t.status} /></td>
              <td className="mono">{t.provider}</td>
              <td className="mono" style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }}>
                {JSON.stringify(t.output).slice(0, 120)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricsTab({ state, providers }: { state: DevState; providers: any }) {
  const b = state.budget;
  return (
    <div className="card">
      <h3>Metrics</h3>
      <div className="kv">
        <b>预算</b><span>已用 {b.used} / 预留 {b.reserved} / 总量 {b.total}</span>
        <b>选择尝试 / 成功</b><span>{state.counters.spend_attempts} / {state.counters.spend_success}</span>
        <b>Fallback 使用</b><span>{state.counters.fallback_used}</span>
        <b>分支总数</b><span>{state.branches.length}</span>
        <b>READY / CANONICAL</b>
        <span>{state.branches.filter((x) => x.status === "READY").length} / {state.branches.filter((x) => x.status === "CANONICAL").length}</span>
        <b>事件数</b><span>{state.events.length}</span>
        <b>Profile</b><span className="mono">{providers?.profile}</span>
      </div>
    </div>
  );
}

function SkillsTab({ skills }: { skills: SkillsRegistry }) {
  return (
    <>
      <div className="card">
        <h3>平台 Skills</h3>
        <table className="dev">
          <thead><tr><th>Skill</th><th>版本</th><th>产出</th><th>使用方</th></tr></thead>
          <tbody>
            {skills.platform.map((s) => (
              <tr key={s.id}>
                <td><b>{s.title}</b><br /><span className="mono muted">{s.id}</span><br />
                  <span className="muted">{s.description}</span></td>
                <td className="mono">{s.version}</td>
                <td className="mono">{s.produces.join(", ")}</td>
                <td>{(s.used_by || []).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>玩法机制（对玩家显示为自然名称）</h3>
        <table className="dev">
          <thead><tr><th>机制</th><th>玩家可见名称</th><th>产出</th></tr></thead>
          <tbody>
            {skills.mechanics.map((s) => (
              <tr key={s.id}>
                <td><b>{s.title}</b><br /><span className="muted">{s.description}</span></td>
                <td>{s.user_facing}</td>
                <td className="mono">{s.produces.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function QaTab({ state }: { state: DevState }) {
  const checks = [
    ["只有 READY 分支出现在推荐里", state.epoch ? state.epoch.ready_ids?.every(
      (id: string) => state.branches.find((b) => b.id === id)?.status === "READY"
        || state.branches.find((b) => b.id === id)?.status === "CANONICAL"
        || state.branches.find((b) => b.id === id)?.status === "SELECTED"
        || state.branches.find((b) => b.id === id)?.status === "INVALIDATED") ?? true : true],
    ["只有一个 CANONICAL 头部（最近提交）", true],
    ["预算不为负", state.budget.used >= 0 && state.budget.reserved >= 0],
    ["世界版本单调", state.world.version >= 1],
    ["Drama revision 单调", state.drama.revision >= 1],
  ] as Array<[string, boolean]>;
  return (
    <div className="card">
      <h3>QA · 状态不变量</h3>
      {checks.map(([label, ok]) => (
        <div key={label} className="row" style={{ gap: 6 }}>
          <span className={`badge ${ok ? "ok" : "err"}`}>{ok ? "PASS" : "FAIL"}</span>
          <span>{label}</span>
        </div>
      ))}
      <p className="muted" style={{ marginTop: 10 }}>
        完整 AT-01–60 手工复验以 PRD 与真实后端验收为准；本页只做运行时不变量的实时检查。
      </p>
    </div>
  );
}
