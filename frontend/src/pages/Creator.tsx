/** Creator：概览（AI 创作）/ 世界 / 角色 / 戏剧结构 / 玩法机制 / 主题 / 发布 / 变更记录。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import StoryUnderstanding, { DRAMA_GROUPS, FIELD_LABELS, readable, typedText } from "../components/StoryUnderstanding";
import CharacterProfile from "../components/CharacterProfile";
import type { GlobalCharacter, PublishCheck, ScenarioCharacter, ScenarioDraft } from "../types";

const MECHANIC_LABELS: Record<string, string> = {
  relationship: "关系变化", "clue-system": "线索调查", inventory: "道具系统", qte: "限时互动",
};
const DRAMA_FIELDS: Array<[keyof ScenarioDraft["drama"], string, string]> = [
  ["core_question", "Core Question / 核心问题", "这个故事最终让玩家面对什么问题？"],
  ["central_conflict", "Central Conflict / 中心冲突", "主要张力来自哪里？"],
  ["truth_model", "Truth Model / 真相模型", "每行一条：fact_id：稳定真相描述"],
  ["secrets", "Secrets / 秘密", "尚未向玩家揭示的信息"],
  ["misbeliefs", "Misbeliefs / 误解", "角色可能存在的误解（不是玩家的真实信念）"],
  ["pressures", "Pressures / 压力", "每行一条：名称｜来源｜驱动（行动触发 / 故事时间推进）"],
  ["anchors", "Key Beats / 关键节点", "预期会发生的关键节点"],
  ["ending_families", "Ending Families / 结局族", "每行一条：id｜描述"],
  ["foreshadows", "Foreshadows / 伏笔", "每行一条：id｜说明"],
  ["forbidden_outcomes", "Forbidden Outcomes / 禁止结果", "世界规则之外、不允许发生的结果"],
  ["timed_interactions", "Timed Interactions / 限时互动", "每行一条：id｜kind(qte|urgent_dialogue)｜超时秒｜超时确定性结果（需启用「限时互动」玩法）"],
];

export default function Creator() {
  const ui = useUi();
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());
  const saveSequence = useRef(0);
  const [draft, setDraft] = useState<ScenarioDraft | null>(null);
  const [idea, setIdea] = useState("");
  const [authoring, setAuthoring] = useState(false);
  const [globals, setGlobals] = useState<GlobalCharacter[]>([]);
  const [versions, setVersions] = useState<{ version_id: string; version: string; created_at: number }[]>([]);

  useEffect(() => {
    if (!ui.editId) return;
    api.getScenario(ui.editId).then(setDraft).catch(() => setDraft(null));
    api.scenarioVersions(ui.editId).then((r) => setVersions(r.items)).catch(() => {});
    api.listCharacters().then((r) => setGlobals(r.items)).catch(() => {});
  }, [ui.editId, ui.creatorTab]);

  if (!ui.editId || !draft) {
    return <div className="empty">没有可编辑的故事。请从「＋ 创建故事」开始。</div>;
  }

  const save = async (next: ScenarioDraft, note?: string) => {
    setDraft(next);
    const sequence = ++saveSequence.current;
    const request = saveQueue.current.catch(() => {}).then(() => api.saveScenario(next));
    saveQueue.current = request;
    try {
      const saved = await request;
      if (sequence === saveSequence.current) setDraft(saved);
      if (note) toast(note);
    } catch (e: any) {
      toast(`保存失败：${e.message}`);
    }
  };
  const patch = (p: Partial<ScenarioDraft>) => save({ ...draft, ...p, updated_at: Date.now() });

  return (
    <>
      {ui.creatorTab === "overview" && (
        <>
          <div className="card">
            <h3>让 AI 帮你完善故事</h3>
            <label>
              <span>用一句话描述你的故事</span>
              <textarea value={idea} onChange={(e) => setIdea(e.target.value)} />
            </label>
            <div className="row">
              <button className="primary" disabled={authoring} onClick={async () => {
                setAuthoring(true);
                try {
                  const created = await api.createScenario(idea);
                  setDraft(created);
                  toast("已生成新的故事草案，请确认 AI 的理解。");
                  setState({ editId: created.id, creatorTab: "drama" });
                } catch (e: any) {
                  toast(`生成失败：${e.message}`);
                } finally {
                  setAuthoring(false);
                }
              }}>理解我的故事</button>
              {authoring && <span className="muted">正在生成草案…</span>}
              <span className="muted">生成可编辑草案，不预生成整个分支树。</span>
            </div>
          </div>
          {draft.description && <StoryUnderstanding key={draft.id} draft={draft} onDraft={setDraft} />}
          <details><summary>故事基本信息</summary><div className="card">
            <h3>故事概览</h3>
            <label><span>Title / 标题</span>
              <input value={draft.title} onChange={(e) => patch({ title: e.target.value })} /></label>
            <label><span>Description / 简介</span>
              <textarea value={draft.description} onChange={(e) => patch({ description: e.target.value })} /></label>
            <div className="two">
              <label><span>Genre / 类型</span>
                <input value={draft.genre} onChange={(e) => patch({ genre: e.target.value })} /></label>
              <label><span>Tone / 语气</span>
                <input value={draft.tone} onChange={(e) => patch({ tone: e.target.value })} /></label>
            </div>
            <label><span>Expected Play Style / 预期玩法</span>
              <input value={draft.play_style} onChange={(e) => patch({ play_style: e.target.value })} /></label>
            <label><span>玩家扮演角色</span>
              <select value={draft.player_character}
                onChange={(e) => patch({ player_character: e.target.value })}>
                {draft.characters.map((c) => <option key={c.id} value={c.id}>{c.identity}</option>)}
              </select></label>
          </div>
          </details>
          <InstructCard draft={draft} onDraft={setDraft} />
        </>
      )}

      {ui.creatorTab === "world" && (
        <div className="card">
          <h3>世界</h3>
          {(["rules", "lore", "locations", "constraints"] as const).map((k) => (
            <label key={k}><span>{({ rules: "World Rules / 世界规则", lore: "Lore / 背景设定",
              locations: ui.mode === "developer" ? "Locations / 地点（每行：id｜名称）" : "故事发生的地点", constraints: "Constraints / 约束" } as const)[k]}</span>
              <textarea value={ui.mode === "standard" && k === "locations" ? readable(draft.world[k]) : draft.world[k]}
                onChange={(e) => patch({ world: { ...draft.world, [k]: ui.mode === "standard" && k === "locations" ? e.target.value.split("\n").map((v, i) => `${draft.world.locations.split("\n")[i]?.split("｜")[0] || `location_${i}`}｜${v}`).join("\n") : e.target.value } })} /></label>
          ))}
        </div>
      )}

      {ui.creatorTab === "characters" && (
        <CharactersTab draft={draft} globals={globals} onSave={save}
          selectedId={ui.characterId} onSelect={(id) => setState({ characterId: id })} />
      )}

      {ui.creatorTab === "drama" && (ui.mode === "developer" ? <div className="card"><h3>DramaSpec</h3>
        {DRAMA_FIELDS.map(([k, label, hint]) => <label key={k}><span>{label}</span><textarea value={draft.drama[k]} placeholder={hint} onChange={e => patch({ drama: { ...draft.drama, [k]: e.target.value } })} /></label>)}
      </div> : <>
        <StoryUnderstanding key={draft.id} draft={draft} onDraft={setDraft} />
        {DRAMA_GROUPS.map(([title, fields]) => <section className="card" key={title}><h3>{title}</h3>
          {fields.map(k => draft.drama[k] ? <NaturalField key={k} label={FIELD_LABELS[k]} value={draft.drama[k]} path={`drama.${k}`} onSave={v => patch({ drama: { ...draft.drama, [k]: v } })} /> : null)}
        </section>)}
        <details><summary>高级戏剧控制</summary><div>{(["foreshadows", "timed_interactions"] as const).map(k => <p key={k}><b>{FIELD_LABELS[k]}：</b>{readable(draft.drama[k]) || "尚未设置，可通过补充想法让 AI 建议。"}</p>)}</div></details>
      </>)}

      {ui.creatorTab === "mechanics" && <>
        <StoryUnderstanding key={`${draft.id}:mechanics`} draft={draft} scope="mechanics" onDraft={setDraft} />
        <div className="understanding-grid">
          {Object.entries(draft.mechanics).filter(([, m]) => m.enabled).map(([k, m]) => <section key={k} className="card">
            <h3>{m.title || MECHANIC_LABELS[k]}</h3><p>{m.tutorial || "这项玩法已启用，可通过上方描述调整规则。"}</p>
            <div className="toolbar"><button onClick={() => document.querySelector<HTMLTextAreaElement>('[aria-label="补充创作想法"]')?.focus()}>调整</button>
              <button onClick={() => patch({ mechanics: { ...draft.mechanics, [k]: { ...m, enabled: false } } })}>移除</button></div>
            {ui.mode === "developer" && <details><summary>Skill / version / config / trigger / StatePatch</summary><pre>{JSON.stringify(m, null, 2)}</pre><textarea defaultValue={JSON.stringify(m.config)} onBlur={e => {
              try { const config = JSON.parse(e.target.value); void patch({ mechanics: { ...draft.mechanics, [k]: { ...m, config } } }); } catch { toast("JSON 格式无效"); }
            }} /></details>}
          </section>)}
        </div>
        <button onClick={() => document.querySelector<HTMLTextAreaElement>('[aria-label="补充创作想法"]')?.focus()}>＋ 添加一种玩法</button>
      </>}

      {ui.creatorTab === "theme" && (
        <div className="card">
          <h3>故事视觉设定</h3>
          <div className="two">
            <label><span>强调色</span>
              <input type="color" value={draft.theme.accent}
                onChange={(e) => patch({ theme: { ...draft.theme, accent: e.target.value } })} /></label>
            <label><span>字体</span>
              <select value={draft.theme.font}
                onChange={(e) => patch({ theme: { ...draft.theme, font: e.target.value } })}>
                <option value="system">系统默认</option>
                <option value="serif">衬线（宋体系）</option>
                <option value="rounded">圆体（幼圆系）</option>
              </select></label>
            <label><span>界面密度</span>
              <select value={draft.theme.density}
                onChange={(e) => patch({ theme: { ...draft.theme, density: e.target.value } })}>
                <option value="compact">紧凑</option>
                <option value="comfortable">舒适</option>
                <option value="roomy">宽松</option>
              </select></label>
            <label><span>字幕</span>
              <select value={draft.theme.subtitles}
                onChange={(e) => patch({ theme: { ...draft.theme, subtitles: e.target.value } })}>
                <option value="normal">正常</option><option value="large">大字号</option>
                <option value="off">关闭</option>
              </select></label>
            <label><span>背景</span>
              <select value={draft.theme.background}
                onChange={(e) => patch({ theme: { ...draft.theme, background: e.target.value } })}>
                <option value="plain">纯色</option>
                <option value="gradient">渐变</option>
                <option value="texture">纹理</option>
              </select></label>
          </div>
          {/* 预览 */}
          <h4>预览</h4>
          <div className="display-preview">
            <div className="preview-scene" style={{
              background: draft.theme.background === "gradient"
                ? `linear-gradient(160deg, ${draft.theme.accent}55, #0f151b)`
                : draft.theme.background === "texture"
                  ? `repeating-linear-gradient(45deg, #1d2833, #1d2833 8px, #18222b 8px, #18222b 16px)`
                  : "#151c24",
            }}>
              <div className="preview-caption" style={{
                bottom: 12, color: draft.theme.subtitles === "off" ? "transparent" : "#f0f2f4",
                fontSize: draft.theme.subtitles === "large" ? 19 : 15,
                fontFamily: draft.theme.font === "serif" ? "Songti SC, SimSun, serif"
                  : draft.theme.font === "rounded" ? "Yuanti SC, YouYuan, sans-serif" : "inherit",
              }}>
                {draft.title} —— 场景字幕预览
              </div>
            </div>
          </div>
        </div>
      )}

      {ui.creatorTab === "publish" && (
        <PublishTab draft={draft} versions={versions} onPublished={async () => {
          const v = await api.scenarioVersions(draft.id);
          setVersions(v.items);
        }} />
      )}

      {ui.creatorTab === "changes" && (
        <div className="card">
          <h3>变更记录</h3>
          {(!draft.changes || draft.changes.length === 0) ? (
            <div className="empty">还没有变更记录。人工保存或 AI 指令修改都会产生条目。</div>
          ) : (
            <table className="dev">
              <thead><tr><th>字段</th><th>Before</th><th>After</th><th>来源</th><th>时间</th></tr></thead>
              <tbody>
                {[...draft.changes].reverse().map((c, i) => (
                  <tr key={i}>
                    <td>{ui.mode === "developer" ? c.path : FIELD_LABELS[c.path.split(".").slice(-1)[0]] || "故事设定"}</td>
                    <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {readable(c.before ?? "—").slice(0, 80)}</td>
                    <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {readable(c.after ?? "—").slice(0, 80)}</td>
                    <td>{c.source === "confirmed_ai" ? "AI 建议·已确认" : c.source === "instruct" ? "AI 指令" : "人工编辑"}{c.reason ? `：${c.reason}` : ""}</td>
                    <td>{new Date(c.at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="muted" style={{ marginTop: 10 }}>
            锁定内容：{draft.locks.length ? ui.mode === "developer" ? draft.locks.join("、") : `${draft.locks.length} 项` : "无"}；锁定字段 AI 指令不会改写。
          </p>
        </div>
      )}
    </>
  );
}

/** G16：自然语言修改指令 → 服务端 typed patch，结果写入 changes 日志 */
function InstructCard({ draft, onDraft }: { draft: ScenarioDraft; onDraft: (d: ScenarioDraft) => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="card">
      <h3>AI 修改指令</h3>
      <p className="muted">用自然语言要求 AI 修改草案（如「把核心问题改为：真相值不值得被揭开」）。命中白名单字段的修改会以 Before/After 记入「变更记录」；锁定字段不会被改写。</p>
      <div className="row">
        <input className="grow" value={text} placeholder="输入修改指令…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && text.trim() && !busy) (document.getElementById("instruct-btn") as HTMLButtonElement)?.click(); }} />
        <button id="instruct-btn" className="primary" disabled={!text.trim() || busy} onClick={async () => {
          setBusy(true);
          try {
            const next = await api.instructScenario(draft.id, text.trim());
            onDraft(next);
            const last = next.changes[next.changes.length - 1];
            toast(last && last.source === "instruct" ? `已应用：${last.path} → ${String(last.after).slice(0, 40)}` : "指令已处理。");
            setText("");
          } catch (e: any) {
            toast(`指令失败：${e.message}`);
          } finally {
            setBusy(false);
          }
        }}>发送</button>
      </div>
    </div>
  );
}

/** G18/G19：发布 Gate（服务端 checklist）+「我已审阅」+ 发布并试玩 */
function PublishTab({ draft, versions, onPublished }: {
  draft: ScenarioDraft;
  versions: { version_id: string; version: string; created_at: number }[];
  onPublished: () => Promise<void>;
}) {
  const developer = useUi().mode === "developer";
  const [checklist, setChecklist] = useState<PublishCheck[] | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.publishCheck(draft.id).then((r) => setChecklist(r.checklist)).catch(() => {});
  }, [draft.id, draft.updated_at]);

  const publish = async (play: boolean) => {
    setErr("");
    try {
      const r = await api.publishScenario(draft.id, { reviewed, play });
      toast(`已发布 v${r.version}。`);
      await onPublished();
      if (play && r.session_id) {
        setState({ sessionId: r.session_id, page: "player" });
      }
    } catch (e: any) {
      // 422 detail 含 checklist
      const detail = e?.detail || e?.message || String(e);
      if (e?.detail?.checklist) setChecklist(e.detail.checklist);
      setErr(typeof detail === "string" ? detail : (detail.message || "发布检查未通过"));
    }
  };

  const allOk = (checklist ?? []).every((c) => c.ok);
  return (
    <div className="card">
      <h3>发布</h3>
      {checklist === null ? <p className="muted">正在检查…</p> : (
        <div>
          {checklist.map((c) => (
            <div key={c.id} className="row" style={{ gap: 6 }}>
              <span className={`badge ${c.ok ? "ok" : "err"}`}>{c.ok ? "PASS" : "FIX"}</span>
              <span className="grow">{c.label}</span>
              {c.detail && !c.ok && <span className="muted">{developer ? c.detail : "请补充或检查这项内容"}</span>}
            </div>
          ))}
        </div>
      )}
      <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
        <input type="checkbox" style={{ width: "auto" }} checked={reviewed}
          onChange={(e) => setReviewed(e.target.checked)} />
        <b>我已审阅这个故事（世界规则、真相模型与结局族符合预期）</b>
      </label>
      {err && <div className="notice warn">{err}</div>}
      <div className="toolbar">
        <button className="primary" disabled={!reviewed || !allOk}
          onClick={() => publish(false)}>发布新版本</button>
        <button disabled={!reviewed || !allOk}
          onClick={() => publish(true)}>发布并试玩</button>
        <span className="muted">发布后形成不可变版本；已有会话不受影响。</span>
      </div>
      <div className="divider" />
      <h4>版本历史</h4>
      {versions.length === 0 ? <div className="empty">尚未发布。</div> : (
        <table className="dev">
          <thead><tr><th>版本</th><th>发布时间</th>{developer && <th>版本 ID</th>}</tr></thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.version_id}>
                <td>v{v.version}</td>
                <td>{new Date(v.created_at).toLocaleString()}</td>
                {developer && <td className="mono">{v.version_id}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function nextVersion(versions: { version: string }[]): string {
  const last = versions[0]?.version ?? "0.0.0";
  const [a, b] = last.split(".").map(Number);
  return last === "0.0.0" ? "1.0.0" : `${a || 1}.${(b || 0) + 1}.0`;
}

function CharactersTab({ draft, globals, onSave, selectedId, onSelect }: {
  draft: ScenarioDraft; globals: GlobalCharacter[];
  onSave: (d: ScenarioDraft, note?: string) => void;
  selectedId: string | null; onSelect: (id: string) => void;
}) {
  const [pickGlobal, setPickGlobal] = useState("");
  const [inherited, setInherited] = useState<Record<string, any>>({});
  const [studioTab, setStudioTab] = useState("overview");
  const selected = draft.characters.find((c) => c.id === selectedId) ?? draft.characters[0];

  useEffect(() => {
    setInherited({});
    if (selected?.global_character_id) api.characterVersions(selected.global_character_id).then(({ items }) => {
      const core = items.find(v => v.version === selected.global_character_version)?.identity_spec;
      if (core) setInherited({ identity: core.name, personality: core.personality, visual_state: core.appearance,
        ...Object.fromEntries(["desire", "fear", "secrets", "knowledge", "relationship"].map(k => [k, core[`default_${k}`]])) });
    });
  }, [selected?.id, selected?.global_character_version]);
  const updateChar = (patch: Partial<ScenarioCharacter>) => {
    const chars = draft.characters.map((c) => (c.id === selected?.id ? { ...c, ...patch } : c));
    onSave({ ...draft, characters: chars });
  };

  return (
    <>
      <div className="card">
        <div className="row">
          <h3 className="grow">角色（{draft.characters.length}）</h3>
          <select value={pickGlobal} onChange={(e) => setPickGlobal(e.target.value)}>
            <option value="">从角色库添加角色…</option>
            {globals.map((g) => <option key={g.id} value={g.id}>{g.name}（v{g.version}）</option>)}
          </select>
          <button className="small" disabled={!pickGlobal} onClick={() => {
            const g = globals.find((x) => x.id === pickGlobal);
            if (!g) return;
            const bound = draft.characters.find(c => c.global_character_id === g.id);
            if (bound) { onSelect(bound.id); return; }
            const instance: ScenarioCharacter = {
              id: `char_${g.id.slice(-6)}`, identity: g.name, personality: g.personality,
              desire: g.default_desire || "", fear: g.default_fear || "", secrets: g.default_secrets || "", knowledge: g.default_knowledge || "", relationship: g.default_relationship || "",
              visual_state: g.appearance || "", global_character_id: g.id, global_character_version: g.version,
            };
            onSave({ ...draft, characters: [...draft.characters, instance] }, "已添加角色库中的角色；当前故事使用固定版本。");
          }}>添加</button>
          <button className="small" onClick={() => {
            const id = `char_${Math.random().toString(36).slice(2, 8)}`;
            onSave({
              ...draft,
              characters: [...draft.characters, {
                id, identity: "新角色", personality: "", desire: "", fear: "", secrets: "",
                knowledge: "", relationship: "", visual_state: "",
              }],
            });
          }}>新建空白角色</button>
        </div>
        <div className="pillrow">
          {draft.characters.map((c) => (
            <button key={c.id} className={`small ${selected?.id === c.id ? "active" : ""}`}
              onClick={() => onSelect(c.id)}>{c.identity}</button>
          ))}
        </div>
      </div>
      {selected && (
        <div className="card">
          <h3>{selected.identity}</h3>
          <nav className="studio-tabs" aria-label="角色">
            {[["overview", "概览"], ["identity", "身份"], ["appearance", "造型"], ["motion", "姿势与动作"], ["voice", "声音"], ["usage", "使用记录"], ["versions", "版本"]].map(([id, label]) => <button key={id} className={studioTab === id ? "active" : ""} onClick={() => setStudioTab(id)}>{label}</button>)}
          </nav>
          <GlobalBindingPanel character={selected} globals={globals} onUpdate={updateChar} />
          {studioTab === "overview" && <StoryUnderstanding key={`${draft.id}:${selected.id}`} draft={draft} scope="character" characterId={selected.id} onDraft={onSave} />}
          <CharacterProfile scope="scenario" onlySections={studioTab === "overview" ? ["身份", "人格与动机", "认知与秘密", "关系"] : studioTab === "identity" ? ["身份", "人格与动机", "认知与秘密", "关系"] : studioTab === "appearance" ? ["外观与造型"] : studioTab === "motion" || studioTab === "voice" ? ["声音与动作"] : ["使用与版本"]} values={selected} inherited={inherited} onChange={updateChar}
            onPromote={selected.global_character_id ? async () => {
              try { const v = await api.promoteStoryCharacter(draft.id, selected.id); toast(`已保存为角色库 v${v.version}；本故事仍保留原版本。`); } catch (e: any) { toast(e.message); }
            } : undefined} extras={{ "外观与造型": selected.global_character_id ? <StoryCharacterOverlay character={selected} globalCharacter={globals.find(g => g.id === selected.global_character_id)} onUpdate={updateChar} /> : null, "声音与动作": selected.global_character_id ? <StoryCharacterOverlay character={selected} globalCharacter={globals.find(g => g.id === selected.global_character_id)} onUpdate={updateChar} /> : <p className="muted">先选择角色库中的角色，当前故事再决定自己的造型、姿势和声音。</p> }} />
          <button className="danger small" onClick={() => {
            onSave({ ...draft, characters: draft.characters.filter((c) => c.id !== selected.id) });
          }}>删除这个角色</button>
        </div>
      )}
    </>
  );
}

function StoryCharacterOverlay({ character, globalCharacter, onUpdate }: {
  character: ScenarioCharacter; globalCharacter?: GlobalCharacter; onUpdate: (patch: Partial<ScenarioCharacter>) => void;
}) {
  const outfits = globalCharacter?.outfits ?? [];
  const poses = globalCharacter?.ref_pose_assets ?? [];
  const motions = globalCharacter?.ref_motion_assets?.length
    ? globalCharacter.ref_motion_assets
    : (globalCharacter?.ref_motion_asset ? [globalCharacter.ref_motion_asset] : []);
  const voices = [
    ...(globalCharacter?.ref_voice_asset ? [{ id: globalCharacter.ref_voice_asset, label: "主声音" }] : []),
    ...(globalCharacter?.alternate_voice_assets ?? []).map((id, i) => ({ id, label: `备用声音 ${String.fromCharCode(66 + i)}` })),
  ];
  const toggle = (key: "pose_refs" | "motion_refs", id: string) => {
    const current = character[key] ?? [];
    const next = current.includes(id) ? current.filter(x => x !== id) : [...current, id];
    onUpdate({ [key]: next, overlay_sources: { ...(character.overlay_sources ?? {}), [key === "pose_refs" ? "pose" : "motion"]: next.length ? "OVERRIDE" : "INHERIT" } });
  };
  return <div className="character-overlay-card">
    <h4>本故事覆盖</h4>
    <p className="muted">角色库定义继续保留；这里的选择只写入当前故事。</p>
    <label><span>本故事造型</span><select aria-label="本故事造型" value={character.outfit_id ?? ""} onChange={e => onUpdate({ outfit_id: e.target.value || null, overlay_sources: { ...(character.overlay_sources ?? {}), outfit: e.target.value ? "OVERRIDE" : "INHERIT" } })}>
      <option value="">继承默认造型</option>{outfits.map(o => <option value={o.id} key={o.id}>{o.name}</option>)}
    </select></label>
    {outfits.filter(o => o.id === character.outfit_id).map(o => <div className="notice" key={o.id}><b>{o.name}</b>{o.description && <p>{o.description}</p>}<span className="muted">已有参考素材 {o.reference_assets?.length ?? 0} 项 · 仅本故事选择</span></div>)}
    <label><span>本故事视觉状态</span><textarea value={character.visual_state} onChange={e => onUpdate({ visual_state: e.target.value, overlay_sources: { ...(character.overlay_sources ?? {}), visual_state: e.target.value ? "OVERRIDE" : "INHERIT" } })} placeholder="例如：本故事中穿黄色雨衣，但保持身份不变" /></label>
    <fieldset><legend>本故事姿势参考</legend>{poses.length ? poses.map((id, i) => <label className="check-row" key={id}><input type="checkbox" checked={(character.pose_refs ?? []).includes(id)} onChange={() => toggle("pose_refs", id)} /><span>姿势参考 {i + 1}</span><small className="muted">{(character.pose_refs ?? []).includes(id) ? "仅本故事" : "继承角色库"}</small></label>) : <p className="muted">角色库暂未绑定姿势参考。</p>}</fieldset>
    <fieldset><legend>本故事动作参考</legend>{motions.length ? motions.map((id, i) => <label className="check-row" key={id}><input type="checkbox" checked={(character.motion_refs ?? []).includes(id)} onChange={() => toggle("motion_refs", id)} /><span>动作参考 {i + 1}</span><small className="muted">{(character.motion_refs ?? []).includes(id) ? "仅本故事" : "继承角色库"}</small></label>) : <p className="muted">角色库暂未绑定动作视频。</p>}</fieldset>
    <fieldset><legend>本故事声音</legend>{voices.length ? voices.map(v => <label className="check-row" key={v.id}><input type="radio" name={`voice-${character.id}`} checked={(character.voice_id ?? globalCharacter?.ref_voice_asset) === v.id} onChange={() => onUpdate({ voice_id: v.id, overlay_sources: { ...(character.overlay_sources ?? {}), voice: v.id === globalCharacter?.ref_voice_asset ? "INHERIT" : "OVERRIDE" } })} /><span>{v.label}</span><small className="muted">{v.id === globalCharacter?.ref_voice_asset ? "继承角色库" : "仅本故事选择"}</small></label>) : <p className="muted">角色库暂未绑定声音。</p>}</fieldset>
    <p className="muted">保存后显示“仅本故事”；使用外层“保存为角色库新版本”才会显式更新角色库。</p>
  </div>;
}

function GlobalBindingPanel({ character, globals, onUpdate }: {
  character: ScenarioCharacter; globals: GlobalCharacter[];
  onUpdate: (patch: Partial<ScenarioCharacter>) => void;
}) {
  const [diff, setDiff] = useState<any>(null);
  const g = globals.find((x) => x.id === character.global_character_id);
  if (!g) {
    return (
      <div className="character-origin-panel">
        <div className="row"><b className="grow">角色</b><span className="badge">未绑定角色库</span></div>
        <p className="muted">这个角色只存在于当前故事。绑定角色库后，动机、秘密、关系和造型仍可仅在本故事覆盖。</p>
        <select aria-label="绑定角色库角色" value="" onChange={e => { const picked = globals.find(x => x.id === e.target.value); if (picked) onUpdate({ global_character_id: picked.id, global_character_version: picked.version }); }}>
          <option value="">选择要继承的角色库角色…</option>{globals.map(item => <option value={item.id} key={item.id}>{item.name} · v{item.version}</option>)}
        </select>
      </div>
    );
  }
  const hasUpdate = g.version > (character.global_character_version ?? 0);
  return (
    <div className="character-origin-panel">
      <div className="row">
        <span className="avatar small">{g.name.slice(0, 1)}</span>
        <div className="grow">
          <b>{g.name}</b>
          <div className="muted">继承角色库 v{character.global_character_version} · {g.bio?.slice(0, 40) || "未填写简介"}</div>
        </div>
        <span className={`badge ${hasUpdate ? "warn" : ""}`}>
          {hasUpdate ? "角色库存在新版本" : "角色快照已固定"}
        </span>
      </div>
      {diff && <div className="notice">{Object.entries(diff.field_diffs || {}).map(([k, v]: [string, any]) => <p key={k}>{FIELD_LABELS[k.replace("default_", "")] || (k === "appearance" ? "外观" : "角色资料")}：{readable(v.before) || "未设置"} → {readable(v.after) || "未设置"}</p>)}<p>参考图变化：{Object.keys(diff.asset_diffs || {}).length} 项</p></div>}
      {hasUpdate && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="small" onClick={() => api.characterVersionDiff(g.id, character.global_character_version || 1, g.version).then(setDiff).catch(e => toast(e.message))}>
            查看变化
          </button>
          <button className="primary small" onClick={() =>
            onUpdate({ global_character_version: g.version })}>
            更新到新版本
          </button>
          <button className="small" onClick={() => toast("继续使用当前版本，本故事没有更新。")}>
            继续使用当前版本
          </button>
        </div>
      )}
    </div>
  );
}

function NaturalField({ label, value, path, onSave }: {label: string; value: string; path: string; onSave: (s: string) => void}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  return <div className="character-understanding"><b>{label}</b>{editing ? <><textarea value={text} onChange={e => setText(e.target.value)} /><button onClick={() => { onSave(typedText(path, text, value)); setEditing(false); }}>保存</button></> : <><p>{readable(value)}</p><button className="small" onClick={() => { setText(readable(value)); setEditing(true); }}>修改</button></>}</div>;
}
