/** Developer Inspector：分支预测 / 世界状态 / 戏剧控制 / 缓存 / 路由 / 运行环境 / 生成 / 装配 / Trace / Metrics / QA / Skills。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";
import type { DevState, Fixtures, SkillsRegistry } from "../types";

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
      {ui.devTab === "skills" && skills && <SkillsTab skills={skills} onChanged={reload} />}
      {ui.devTab === "qa" && <QaTab state={state} />}
      {ui.devTab === "prototype" && <PrototypeTab />}
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
  const [profile, setProfile] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const reloadProfile = () => api.devProfile().then(setProfile).catch(() => {});

  useEffect(() => { reloadProfile(); }, [providers?.profile]);

  const switchTo = async (target: string) => {
    setBusy(true);
    try {
      const r = await api.devProfileSwitch(target);
      if (r.ok) toast(`已切换到 ${target}。`);
      else toast(`切换失败，已回滚：${(r.failed_health || []).join(", ") || r.error || "健康检查未通过"}`);
      reloadProfile();
    } catch (e: any) {
      toast(`切换被拒：${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const PROFILES: Array<[string, string]> = [
    ["AGENT_LOCAL_PROFILE", "Agent 本地（文本优先）"],
    ["VIDEO_LOCAL_PROFILE", "视频本地（生成优先）"],
  ];
  return (
    <>
      <div className="card">
        <h3>运行环境</h3>
        <div className="kv">
          <b>Runtime Profile</b><span className="mono">{providers.profile}</span>
          <b>切换状态</b><span><Pill s={profile?.state ?? "ACTIVE"} /></span>
          <b>Provider 模式</b><span className="mono">{providers.mode}</span>
        </div>
        <p className="muted">
          AGENT_LOCAL_PROFILE ↔ VIDEO_LOCAL_PROFILE 为显式切换（drain → persist → unload → start → 健康检查）。
          健康检查失败会自动回滚到原 Profile。VIDEO_LOCAL_PROFILE 下本地 Agent 模型不可用，角色自动走冻结的 fallback 链。
        </p>
        <div className="toolbar">
          {PROFILES.map(([key, label]) => (
            <button key={key} className="small"
              disabled={busy || providers.profile === key || (profile && profile.state !== "ACTIVE")}
              onClick={() => switchTo(key)}>
              {providers.profile === key ? `✓ ${label}` : `切换到 ${label}`}
            </button>
          ))}
        </div>
      </div>
      {profile?.history?.length > 0 && (
        <div className="card">
          <h3>切换历史（七态 timeline）</h3>
          {profile.history.slice().reverse().map((h: any, i: number) => (
            <div key={i} style={{ marginBottom: 14 }}>
              <div className="row">
                <b className="mono">{h.from} → {h.to}</b>
                <Pill s={h.result === "switched" ? "healthy" : "unhealthy"} />
                <span className="muted">{h.result === "switched" ? "切换成功" : `回滚：${(h.failed_health || []).join(", ")}`}</span>
              </div>
              <div className="row" style={{ flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                {(h.timeline || []).map((t: any, j: number) => (
                  <span key={j} className="badge" title={new Date(t.at).toLocaleTimeString()}>
                    {t.state}{t.duration_ms != null ? ` ${t.duration_ms}ms` : ""}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function ProductionTab({ state }: { state: DevState }) {
  const rows = state.branches.filter((b) => b.routes?.length);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);

  const reloadJobs = () => api.devJobs().then((r) => setJobs(r.items)).catch(() => {});
  useEffect(() => {
    reloadJobs();
    const t = setInterval(reloadJobs, 4000);   // G23：轮询状态迁移
    return () => clearInterval(t);
  }, []);

  return (
    <>
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
      <div className="card">
        <h3>本地直出任务（Sol-H3，不走剧情管线）</h3>
        <p className="muted">
          用本地视频模型直接生成一段短片段，用于验证本地模型可用性；与剧情分支管线相互独立。
        </p>
        <div className="row">
          <input className="grow" placeholder="描述要生成的画面，例如：雨夜窗边的人影"
            value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          <button className="primary" disabled={busy || !prompt.trim()} onClick={async () => {
            setBusy(true);
            try {
              const r = await api.devLocalTask(prompt.trim());
              setJob(r);
              toast("本地任务已提交。");
            } catch (e: any) {
              toast(`提交失败：${e.message}`);
            } finally {
              setBusy(false);
            }
          }}>{busy ? "提交中…" : "提交本地任务"}</button>
        </div>
        {job && (
          <pre style={{ marginTop: 10 }}>{JSON.stringify(job, null, 2)}</pre>
        )}
      </div>
      {/* G23：任务列表（Job ID/Provider/Profile/状态/起止/output/error） */}
      <div className="card">
        <h3>生成任务（{jobs.length}）</h3>
        {jobs.length === 0 ? <div className="empty">还没有任务记录。</div> : (
          <table className="dev">
            <thead><tr><th>Job ID</th><th>Provider</th><th>Profile</th><th>状态</th><th>开始</th><th>输出 / 错误</th></tr></thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td className="mono">{j.id}</td>
                  <td className="mono">{j.provider}</td>
                  <td className="mono">{j.profile ?? "—"}</td>
                  <td><Pill s={j.status} /></td>
                  <td className="mono">{j.started_at ? new Date(j.started_at).toLocaleTimeString() : "—"}</td>
                  <td className="mono" style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {j.error ?? JSON.stringify(j.output ?? {}).slice(0, 90)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
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

function SkillsTab({ skills, onChanged }: { skills: SkillsRegistry; onChanged: () => void }) {
  const toggle = async (s: { id: string; title: string; enabled?: boolean }) => {
    try {
      await api.toggleSkill(s.id, s.enabled === false);
      toast(`「${s.title}」已${s.enabled === false ? "启用" : "禁用"}。`);
      onChanged();
    } catch (e: any) {
      toast(`切换失败：${e.message}`);
    }
  };
  return (
    <>
      <SkillObservatory />
      <div className="card">
        <h3>平台 Skills</h3>
        <p className="muted">
          禁用某个 Skill 后，依赖它的生成步骤会被阻塞（分支标记失败并说明原因），可随时恢复。
        </p>
        <table className="dev">
          <thead><tr><th>Skill</th><th>版本</th><th>产出</th><th>使用方</th><th>最近调用</th><th>状态</th></tr></thead>
          <tbody>
            {skills.platform.map((s) => (
              <tr key={s.id} style={s.enabled === false ? { opacity: 0.5 } : undefined}>
                <td><b>{s.title}</b><br /><span className="mono muted">{s.id}</span><br />
                  <span className="muted">{s.description}</span></td>
                <td className="mono">{s.version}</td>
                <td className="mono">{s.produces.join(", ")}</td>
                <td>{(s.used_by || []).join(", ")}</td>
                <td><SkillCalls skillId={s.id} /></td>
                <td>
                  <button className="small" onClick={() => toggle(s)}>
                    {s.enabled === false ? "已禁用 · 点击启用" : "已启用 · 点击禁用"}
                  </button>
                </td>
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

function SkillObservatory() {
  const [data, setData] = useState<any>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    const refresh = () => fetch("/api/skills/observatory").then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(x => { if (alive) { setData(x); setFailed(false); } }).catch(() => { if (alive) setFailed(true); });
    void refresh(); const timer = setInterval(refresh, 5000);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  return <section className="card" data-testid="skill-observatory">
    <h3>Skill Observatory · 能力调用与提案链</h3>
    <p className="muted">最近观测窗口；调用成功不等于状态已提交。精确率、召回率没有标注时不显示虚构分数。</p>
    {failed && <p role="status">暂时无法载入能力轨迹，请稍后重试。</p>}
    {data && <>
      <p>持久化待写入 {data.persistence.pending} · 写入失败 {data.persistence.failures} · 丢失 {data.persistence.dropped}</p>
      <table className="dev"><thead><tr><th>能力</th><th>调用 / 成功 / 失败</th><th>有记录平均耗时</th><th>提案 / 已提交分支</th></tr></thead>
        <tbody>{data.metrics.map((m: any) => <tr key={m.skill_id}>
          <td>{m.skill_id}</td><td>{m.invocations} / {m.success} / {m.failure}</td>
          <td>{m.average_latency_ms == null ? "未记录" : Math.round(m.average_latency_ms) + " ms (" + m.latency_samples + " 样本)"}</td>
          <td>{m.proposal_count} / {m.proposals_in_committed_branches}</td>
        </tr>)}</tbody></table>
      {!data.chains.length && <p>尚无本次部署后的能力链；研究 Replay 记录见仓库报告，不冒充线上调用。</p>}
      {data.chains.slice().reverse().map((chain: any) => <details key={chain.branch_id}>
        <summary>Skill Chain · {chain.branch_id} · {chain.calls.length} 步</summary>
        {chain.calls.map((c: any) => <details key={c.id}>
          <summary>{c.skill_id || c.name} v{c.skill_version || "未记录"} · {c.status} · {c.duration_ms ? c.duration_ms + " ms" : "耗时未记录"}</summary>
          <pre>{JSON.stringify({why: c.input?.why, input: c.input, output: c.output}, null, 2)}</pre>
        </details>)}
      </details>)}
    </>}
  </section>;
}

/** G24：某 Skill 最近调用记录（含禁用阻塞记录） */
function SkillCalls({ skillId }: { skillId: string }) {
  const [calls, setCalls] = useState<any[] | null>(null);
  useEffect(() => {
    api.skillCalls(skillId).then((r) => setCalls(r.items)).catch(() => setCalls([]));
  }, [skillId]);
  if (calls === null) return <span className="muted">…</span>;
  if (calls.length === 0) return <span className="muted">无记录</span>;
  return (
    <div className="mono" style={{ fontSize: "var(--font-xs)" }}>
      {calls.slice(0, 3).map((c) => (
        <div key={c.id} title={JSON.stringify(c.output).slice(0, 200)}>
          {new Date(c.at).toLocaleTimeString()} {c.name}
          <Pill s={c.status === "success" ? "healthy" : "unhealthy"} />
        </div>
      ))}
    </div>
  );
}

/** 原型夹具：只影响 Mock Provider 的行为档位，用于演示/验收不同响应路径。 */
function PrototypeTab() {
  const [fixtures, setFixtures] = useState<Fixtures | null>(null);
  const reload = () => api.devFixtures().then(setFixtures).catch(() => {});
  useEffect(() => { reload(); }, []);

  if (!fixtures) return <div className="empty">正在载入…</div>;

  const set = async (key: string, value: any) => {
    try {
      const r = await api.devSetFixture(key, value);
      setFixtures(r);
    } catch (e: any) {
      toast(`设置失败：${e.message}`);
    }
  };

  const CONFIDENCE: Array<[string, string]> = [
    ["auto", "自动（按输入内容判断）"],
    ["high", "总是高置信（直接生成）"],
    ["medium", "总是中置信（触发理解确认）"],
    ["low", "总是低置信（触发理解确认）"],
  ];
  const RESPONSE: Array<[string, string]> = [
    ["auto", "自动（按影响面判断）"],
    ["quick", "总是小动作（即时回应）"],
    ["merged", "小动作（演示合并转场）"],
    ["full", "总是完整分支（生成新场景）"],
  ];

  return (
    <>
      <div className="card">
        <h3>意图理解置信度</h3>
        <p className="muted">控制「自由输入」被理解时的置信度档位，用于演示「我这样理解你的意思」确认卡。</p>
        <div className="toolbar">
          {CONFIDENCE.map(([v, label]) => (
            <button key={v} className={`small ${fixtures.confidence === v ? "primary" : ""}`}
              onClick={() => set("confidence", v)}>{label}</button>
          ))}
        </div>
      </div>
      <div className="card">
        <h3>行动响应档位</h3>
        <p className="muted">控制自由输入产生的响应类型：小动作即时回应 / 完整分支生成 / 合并转场。</p>
        <div className="toolbar">
          {RESPONSE.map(([v, label]) => (
            <button key={v} className={`small ${fixtures.response === v ? "primary" : ""}`}
              onClick={() => set("response", v)}>{label}</button>
          ))}
        </div>
      </div>
      <div className="card">
        <h3>叙事泄密注入</h3>
        <p className="muted">
          开启后，Mock 叙事会故意泄露未授权的真相片段，用于验证「泄密拦截 → 重写 → 分支失败」的安全链。
        </p>
        <div className="toolbar">
          <button className={`small ${fixtures.leak_secret ? "primary" : ""}`}
            onClick={() => set("leak_secret", !fixtures.leak_secret)}>
            {fixtures.leak_secret ? "已开启 · 点击关闭" : "已关闭 · 点击开启"}
          </button>
        </div>
      </div>
      <div className="card">
        <div className="row">
          <h3 className="grow">重置</h3>
          <button className="small danger" onClick={() => set("reset", true)}>全部恢复自动</button>
        </div>
        <p className="muted">夹具只影响 Mock Provider，不改变任何业务 Runtime 行为；重启服务后自动复位。</p>
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
