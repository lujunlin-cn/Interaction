/** Creator：概览（AI 创作）/ 世界 / 角色 / 戏剧结构 / 玩法机制 / 主题 / 发布 / 变更记录。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import type { GlobalCharacter, ScenarioCharacter, ScenarioDraft } from "../types";

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
];

export default function Creator() {
  const ui = useUi();
  const [draft, setDraft] = useState<ScenarioDraft | null>(null);
  const [idea, setIdea] = useState("创建一个发生在雨夜公寓里的悬疑故事，玩家可以调查、关心 Alice，也可以选择离开。");
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
    try {
      await api.saveScenario(next);
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
            <h3>AI Scenario Creation</h3>
            <label>
              <span>用一句话描述你的故事</span>
              <textarea value={idea} onChange={(e) => setIdea(e.target.value)} />
            </label>
            <div className="row">
              <button className="primary" disabled={authoring} onClick={async () => {
                setAuthoring(true);
                try {
                  const created = await api.createScenario(idea);
                  toast("草案已生成。已上传素材、手工编辑及锁定字段均保留。");
                  setState({ editId: created.id, creatorTab: "drama" });
                } catch (e: any) {
                  toast(`生成失败：${e.message}`);
                } finally {
                  setAuthoring(false);
                }
              }}>Generate Scenario</button>
              {authoring && <span className="muted">正在生成草案…</span>}
              <span className="muted">生成可编辑草案，不预生成整个分支树。</span>
            </div>
          </div>
          <div className="card">
            <h3>Overview</h3>
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
        </>
      )}

      {ui.creatorTab === "world" && (
        <div className="card">
          <h3>世界</h3>
          {(["rules", "lore", "locations", "constraints"] as const).map((k) => (
            <label key={k}><span>{({ rules: "World Rules / 世界规则", lore: "Lore / 背景设定",
              locations: "Locations / 地点（每行：id｜名称）", constraints: "Constraints / 约束" } as const)[k]}</span>
              <textarea value={draft.world[k]}
                onChange={(e) => patch({ world: { ...draft.world, [k]: e.target.value } })} /></label>
          ))}
        </div>
      )}

      {ui.creatorTab === "characters" && (
        <CharactersTab draft={draft} globals={globals} onSave={save}
          selectedId={ui.characterId} onSelect={(id) => setState({ characterId: id })} />
      )}

      {ui.creatorTab === "drama" && (
        <div className="card">
          <h3>戏剧结构</h3>
          {DRAMA_FIELDS.map(([k, label, hint]) => (
            <label key={k}><span>{label}</span>
              <textarea value={draft.drama[k]} placeholder={hint}
                onChange={(e) => patch({ drama: { ...draft.drama, [k]: e.target.value } })} /></label>
          ))}
        </div>
      )}

      {ui.creatorTab === "mechanics" && (
        <div className="card">
          <h3>玩法机制</h3>
          <p className="muted">只有已审核的四种机制可选；它们在游玩中以「{Object.values(MECHANIC_LABELS).join(" / ")}」的自然名称出现。</p>
          {(["relationship", "clue-system", "inventory", "qte"] as const).map((k) => {
            const m = draft.mechanics[k] ?? { enabled: false, config: {} };
            return (
              <div key={k} className="notice">
                <label style={{ display: "flex", gap: 8, alignItems: "center", margin: 0 }}>
                  <input type="checkbox" style={{ width: "auto" }} checked={m.enabled}
                    onChange={(e) => patch({
                      mechanics: { ...draft.mechanics, [k]: { ...m, enabled: e.target.checked } },
                    })} />
                  <b>{MECHANIC_LABELS[k]}</b>
                </label>
                {m.enabled && (
                  <textarea style={{ marginTop: 8 }} rows={2}
                    value={JSON.stringify(m.config)}
                    onChange={(e) => {
                      try {
                        const config = JSON.parse(e.target.value || "{}");
                        patch({ mechanics: { ...draft.mechanics, [k]: { ...m, config } } });
                      } catch { /* 等用户输完合法 JSON */ }
                    }} />
                )}
              </div>
            );
          })}
        </div>
      )}

      {ui.creatorTab === "theme" && (
        <div className="card">
          <h3>故事视觉设定</h3>
          <div className="two">
            <label><span>强调色</span>
              <input type="color" value={draft.theme.accent}
                onChange={(e) => patch({ theme: { ...draft.theme, accent: e.target.value } })} /></label>
            <label><span>字幕</span>
              <select value={draft.theme.subtitles}
                onChange={(e) => patch({ theme: { ...draft.theme, subtitles: e.target.value } })}>
                <option value="normal">正常</option><option value="large">大字号</option>
                <option value="off">关闭</option>
              </select></label>
          </div>
        </div>
      )}

      {ui.creatorTab === "publish" && (
        <div className="card">
          <h3>发布</h3>
          <PublishChecklist draft={draft} />
          <div className="toolbar">
            <button className="primary" onClick={async () => {
              try {
                const r = await api.publishScenario(draft.id);
                toast(`已发布 v${r.version}。已有游玩会话继续绑定原版本。`);
                const v = await api.scenarioVersions(draft.id);
                setVersions(v.items);
              } catch (e: any) {
                toast(`发布失败：${e.message}`);
              }
            }}>发布 v{nextVersion(versions)}</button>
            <span className="muted">发布后形成不可变版本；已有会话不受影响。</span>
          </div>
          <div className="divider" />
          <h4>版本历史</h4>
          {versions.length === 0 ? <div className="empty">尚未发布。</div> : (
            <table className="dev">
              <thead><tr><th>版本</th><th>发布时间</th><th>版本 ID</th></tr></thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.version_id}>
                    <td>v{v.version}</td>
                    <td>{new Date(v.created_at).toLocaleString()}</td>
                    <td className="mono">{v.version_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {ui.creatorTab === "changes" && (
        <div className="card">
          <h3>变更记录</h3>
          <p className="muted">人工编辑字段：{draft.manual_edits.length ? draft.manual_edits.join("、") : "无"}</p>
          <p className="muted">锁定字段：{draft.locks.length ? draft.locks.join("、") : "无"}</p>
          <p className="muted">AI 修改草案时，人工编辑与锁定字段会被保留。</p>
        </div>
      )}
    </>
  );
}

function nextVersion(versions: { version: string }[]): string {
  const last = versions[0]?.version ?? "0.0.0";
  const [a, b] = last.split(".").map(Number);
  return last === "0.0.0" ? "1.0.0" : `${a || 1}.${(b || 0) + 1}.0`;
}

function PublishChecklist({ draft }: { draft: ScenarioDraft }) {
  const checks: Array<[string, boolean]> = [
    ["标题与简介已填写", Boolean(draft.title && draft.description)],
    ["世界规则已填写", Boolean(draft.world.rules)],
    ["至少一名角色", draft.characters.length > 0],
    ["核心问题已填写", Boolean(draft.drama.core_question)],
    ["真相模型已填写", Boolean(draft.drama.truth_model)],
    ["结局族已定义", Boolean(draft.drama.ending_families)],
  ];
  return (
    <div>
      {checks.map(([label, ok]) => (
        <div key={label} className="row" style={{ gap: 6 }}>
          <span className={`badge ${ok ? "ok" : "err"}`}>{ok ? "PASS" : "FIX"}</span>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

function CharactersTab({ draft, globals, onSave, selectedId, onSelect }: {
  draft: ScenarioDraft; globals: GlobalCharacter[];
  onSave: (d: ScenarioDraft, note?: string) => void;
  selectedId: string | null; onSelect: (id: string) => void;
}) {
  const [pickGlobal, setPickGlobal] = useState("");
  const selected = draft.characters.find((c) => c.id === selectedId) ?? draft.characters[0];

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
            <option value="">从角色库创建故事角色…</option>
            {globals.map((g) => <option key={g.id} value={g.id}>{g.name}（v{g.version}）</option>)}
          </select>
          <button className="small" disabled={!pickGlobal} onClick={() => {
            const g = globals.find((x) => x.id === pickGlobal);
            if (!g) return;
            const instance: ScenarioCharacter = {
              id: `char_${g.id.slice(-6)}`, identity: g.name, personality: g.personality,
              desire: "", fear: "", secrets: "", knowledge: "", relationship: "",
              visual_state: "", global_character_id: g.id, global_character_version: g.version,
            };
            onSave({ ...draft, characters: [...draft.characters, instance] }, "已按角色库快照创建故事角色。");
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
          <GlobalBindingPanel character={selected} globals={globals} onUpdate={updateChar} />
          <div className="two">
            {([["identity", "本故事身份"], ["personality", "人格表现"], ["desire", "Desire / 欲望"],
              ["fear", "Fear / 恐惧"], ["secrets", "Secrets / 秘密"], ["knowledge", "Knowledge / 已知"],
              ["relationship", "Relationships / 关系"], ["visual_state", "当前 Visual State"],
            ] as Array<[keyof ScenarioCharacter, string]>).map(([k, label]) => (
              <label key={k}><span>{label}</span>
                <textarea rows={2} value={String(selected[k] ?? "")}
                  onChange={(e) => updateChar({ [k]: e.target.value } as any)} /></label>
            ))}
          </div>
          <button className="danger small" onClick={() => {
            onSave({ ...draft, characters: draft.characters.filter((c) => c.id !== selected.id) });
          }}>删除这个角色</button>
        </div>
      )}
    </>
  );
}

function GlobalBindingPanel({ character, globals, onUpdate }: {
  character: ScenarioCharacter; globals: GlobalCharacter[];
  onUpdate: (patch: Partial<ScenarioCharacter>) => void;
}) {
  const g = globals.find((x) => x.id === character.global_character_id);
  if (!g) {
    return (
      <div className="character-origin-panel">
        <div className="row"><b className="grow">故事角色</b><span className="badge">未绑定角色库</span></div>
        <p className="muted">这个角色只存在于当前故事。你可以保留它，也可以从全局角色库选择一个角色创建新的故事实例。</p>
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
          <div className="muted">角色库快照 v{character.global_character_version} · {g.bio?.slice(0, 40) || "未填写简介"}</div>
        </div>
        <span className={`badge ${hasUpdate ? "warn" : ""}`}>
          {hasUpdate ? "角色库存在新版本" : "角色快照已固定"}
        </span>
      </div>
      {hasUpdate && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="small" onClick={() =>
            alert(`角色库当前版本：v${g.version}\n简介：${g.bio}\n人格：${g.personality}`)}>
            查看变化
          </button>
          <button className="primary small" onClick={() =>
            onUpdate({ global_character_version: g.version, personality: g.personality || character.personality })}>
            更新到新版本
          </button>
          <button className="small" onClick={() => onUpdate({ global_character_version: g.version })}>
            继续使用当前版本
          </button>
        </div>
      )}
    </div>
  );
}
