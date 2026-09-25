/** 角色库：跨故事共享的稳定角色身份资产；故事使用快照，不被后续修改覆盖。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import CharacterProfile from "../components/CharacterProfile";
import CharacterStudio, { CharacterStudioTabs, STUDIO_TABS } from "../components/CharacterStudio";
import type { CharacterAsset, GlobalCharacter } from "../types";

const ROLE_LABELS: Record<string,string> = {front:"主身份图",three_quarter:"四分之三视图",side:"侧面视图",back:"额外背面参考",full_front:"全身正面",full_side:"全身侧面",outfit:"造型参考",pose:"姿势参考",motion:"动作参考",voice:"声音参考",derived:"编辑后的形象"};
const UNDERSTANDING_LABELS: Record<string, string> = { personality: "基础人格", default_desire: "最想得到什么", default_fear: "最害怕什么", default_secrets: "默认秘密", default_knowledge: "默认认知", default_relationship: "默认关系", appearance: "稳定外观描述" };
function savedUnderstanding(id: string): Record<string, string> | null {
  try { return JSON.parse(sessionStorage.getItem(`character-understanding:${id}`) || "null"); }
  catch { return null; }
}
export default function CharacterLibrary() {
  const ui = useUi();
  const [items, setItems] = useState<GlobalCharacter[]>([]);
  const [q, setQ] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [pendingUnderstanding, setPendingUnderstanding] = useState<{ id: string; values: Record<string, string> } | null>(null);

  const reload = () => api.listCharacters(q).then((r) => setItems(r.items)).catch(() => {});
  useEffect(() => { reload(); }, [q]);

  const selected = items.find((g) => g.id === ui.globalCharacterId) ?? null;
  if (selected) {
    return <CharacterDetail key={selected.id} ch={selected} onBack={() => setState({ globalCharacterId: null })}
      onSaved={reload} initialUnderstanding={pendingUnderstanding?.id === selected.id ? pendingUnderstanding.values : null} />;
  }
  return (
    <>
      <div className="task-head">
        <div className="grow">
          <p className="muted">角色库保存角色长期稳定的身份；故事可以继承它，也可以只在当前故事里覆盖。</p>
        </div>
        <button className="primary" onClick={() => setCreateOpen(true)}>新建角色</button>
      </div>
      <div className="character-searchbar">
        <input placeholder="按名字、描述、标签、职业或性格搜索" value={q}
          onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="global-character-grid">
        {items.map((g) => (
          <article key={g.id} className="global-character-card">
            <button className="global-character-open" onClick={() => setState({ globalCharacterId: g.id })}>
              <span className="avatar">{g.name.slice(0, 1)}</span>
              <div className="global-character-copy">
                <div className="row"><h3 className="grow">{g.name}</h3>
                  <span className="version-pill">v{g.version}</span></div>
                <p>{g.bio || "尚未填写简介"}</p>
                <div className="pillrow">
                  {(g.tags || []).slice(0, 4).map((t) => <span key={t} className="soft-tag">{t}</span>)}
                </div>
                <div className="character-stats">
                  <span>形象参考 {[g.ref_front_asset, g.ref_side_asset, g.ref_back_asset,
                    ...(g.ref_other_assets || [])].filter(Boolean).length}</span>
                  <span>声音参考 {g.ref_voice_asset ? "已设置" : "未设置"}</span>
                </div>
              </div>
            </button>
          </article>
        ))}
        {items.length === 0 && <div className="empty">没有找到匹配的角色。</div>}
      </div>
      {createOpen && <CharacterCreate onClose={() => setCreateOpen(false)} onCreated={(id, understanding) => {
        if (understanding) sessionStorage.setItem(`character-understanding:${id}`, JSON.stringify(understanding));
        setPendingUnderstanding(understanding ? { id, values: understanding } : null);
        setCreateOpen(false); setState({ globalCharacterId: id }); reload();
      }} />}
    </>
  );
}

function CharacterCreate({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string, understanding?: Record<string, string>) => void }) {
  const [kind, setKind] = useState<"ai" | "image" | "manual">("ai");
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [personality, setPersonality] = useState("");
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const submit = async () => {
    if (!name.trim() || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    try {
      const created = createdId ? { id: createdId } : await api.createCharacter({ name: name.trim(), bio, personality, appearance: prompt });
      setCreatedId(created.id);
      if (kind === "ai") {
        const understanding = await api.characterUnderstanding(created.id);
        toast("AI 已整理角色建议，请逐项确认。确认后可在造型中主动生成候选图。");
        onCreated(created.id, understanding);
        return;
      } else if (kind === "image" && file) {
        const asset = await api.importCharacterBaseline(created.id, file);
        toast("图片已作为身份参考保存，请在 Studio 中确认主形象。");
      } else {
        toast("无图片角色已创建，可在 Studio 中继续补充形象。");
      }
      onCreated(created.id);
    } catch (e: any) { toast(`创建失败：${e.message}`); }
    finally { submitting.current = false; setBusy(false); }
  };
  return <div className="modal-mask" role="dialog" aria-modal="true">
    <div className="modal">
      <div className="row"><h3 className="grow">新建角色</h3><button onClick={onClose}>关闭</button></div>
      <p className="muted">AI 创建先整理文字建议，由你确认；图片只会在造型页明确点击生成后制作。</p>
      <div className="toolbar">
        {([["ai", "AI 创建"], ["image", "从图片创建"], ["manual", "手动创建"]] as const).map(([v, label]) =>
          <button key={v} className={kind === v ? "active" : ""} onClick={() => setKind(v)}>{label}</button>)}
      </div>
      <div className="divider" />
      <label><span>姓名</span><input value={name} onChange={e => setName(e.target.value)} placeholder="例如：林岚" /></label>
      <label><span>角色描述</span><textarea value={bio} onChange={e => setBio(e.target.value)} placeholder="身份、经历和故事中的作用" /></label>
      {(kind === "ai" || kind === "manual") && <label><span>人格</span><textarea value={personality} onChange={e => setPersonality(e.target.value)} placeholder="谨慎、敏锐、渴望真相……" /></label>}
      {kind === "ai" && <label><span>形象描述</span><textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="短发、深色雨衣、疲惫但警觉" /></label>}
      {kind === "image" && <label><span>人物图片</span><input type="file" accept="image/*" onChange={e => setFile(e.target.files?.[0] ?? null)} /></label>}
      {createdId && <button onClick={() => onCreated(createdId)}>进入已创建角色，稍后补充图片</button>}
      <div className="row" style={{ justifyContent: "flex-end" }}><button onClick={onClose}>取消</button><button className="primary" disabled={!name.trim() || !bio.trim() || busy || (kind === "image" && !file)} onClick={submit}>{busy ? "创建中…" : "创建并进入 Studio"}</button></div>
    </div>
  </div>;
}

function CharacterDetail({ ch, onBack, onSaved, initialUnderstanding }: {
  ch: GlobalCharacter; onBack: () => void; onSaved: () => void; initialUnderstanding?: Record<string, string> | null;
}) {
  const [understanding, setUnderstanding] = useState<Record<string, string> | null>(() => savedUnderstanding(ch.id) || initialUnderstanding || null);
  const [editingSuggestion, setEditingSuggestion] = useState<string | null>(null);
  const [suggestionText, setSuggestionText] = useState("");
  const [studioAssets, setStudioAssets] = useState<CharacterAsset[]>([]);
  const [prompt, setPrompt] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [busy, setBusy] = useState("");
  const submitting = useRef(false);
  const [confirmViews, setConfirmViews] = useState<string | null>(null);
  const [scenarioVersionId, setScenarioVersionId] = useState("");
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [resolver, setResolver] = useState<any>(null);
  const [tab, setTab] = useState<(typeof STUDIO_TABS)[number][0]>("overview");
  const [paidEnabled, setPaidEnabled] = useState(false);
  const [editSourceId, setEditSourceId] = useState("");
  const developer = useUi().mode === "developer";
  useEffect(() => {
    if (understanding) sessionStorage.setItem(`character-understanding:${ch.id}`, JSON.stringify(understanding));
    else sessionStorage.removeItem(`character-understanding:${ch.id}`);
  }, [ch.id, understanding]);
  const loadStudio = () => api.listCharacterStudioAssets(ch.id).then(r => setStudioAssets(r.items)).catch(() => {});
  useEffect(() => { void loadStudio(); }, [ch.id, ch.version]);
  const loadSnapshots = () => scenarioVersionId
    ? api.listCharacterSnapshots(scenarioVersionId).then((r) => setSnapshots(r.items)).catch(() => {})
    : undefined;
  useEffect(() => { if (scenarioVersionId) void loadSnapshots(); }, [scenarioVersionId]);
  useEffect(() => { api.devGenerationSettings().then((v) => setPaidEnabled(Boolean(v.fal_paid_generation_enabled))).catch(() => {}); }, []);

  const run = async (label: string, action: () => Promise<unknown>) => {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(label);
    try { await action(); toast(label); loadStudio(); onSaved(); }
    catch (e: any) { toast(`${label}失败：${e.message}`); }
    finally { submitting.current = false; setBusy(""); }
  };

  return (
    <>
      <div className="task-head">
        <div className="grow">
          <button className="text-button" onClick={onBack}>← 返回角色库</button>
          <h2>{ch.name}</h2>
          <p className="muted">角色库定义 · v{ch.version}</p>
        </div>
        <span className="avatar large">{ch.name.slice(0, 1)}</span>
      </div>
      <CharacterStudioTabs tab={tab} onChange={setTab} />
      {tab === "overview" && <section className="card"><h3>AI 对这个角色的理解</h3><p>{ch.bio}</p>
        <button disabled={!!busy} onClick={() => run("已整理角色建议", async () => setUnderstanding(await api.characterUnderstanding(ch.id)))}>让 AI 补充可选信息</button>
        {understanding && <div className="understanding-grid">{Object.entries(understanding).map(([key, value]) => <div className="understanding-item" key={key}>
          <h4>{UNDERSTANDING_LABELS[key] || "角色建议"}</h4><p>{value}</p>
          {editingSuggestion === key && <textarea aria-label={`修改${UNDERSTANDING_LABELS[key] || "角色建议"}`} value={suggestionText} onChange={e => setSuggestionText(e.target.value)} />}
          <button disabled={!!busy} onClick={() => run("已确认角色建议", async () => { await api.updateCharacter(ch.id, { [key]: editingSuggestion === key ? suggestionText : value }); setUnderstanding(old => { const n = { ...old }; delete n[key]; return n; }); setEditingSuggestion(null); })}>{editingSuggestion === key ? "确认修改" : "接受"}</button>
          <button disabled={!!busy} onClick={() => { setEditingSuggestion(key); setSuggestionText(value); }}>修改</button>
          <button disabled={!!busy} onClick={() => setUnderstanding(old => { const n = { ...old }; delete n[key]; return n; })}>忽略</button>
        </div>)}</div>}
      </section>}
      {tab === "identity" && <CharacterProfile scope="global" onlySections={["身份", "人格与动机", "认知与秘密", "关系"]} values={{ identity: ch.name, bio: ch.bio, personality: ch.personality,
        visual_state: ch.appearance, ...Object.fromEntries(["desire", "fear", "secrets", "knowledge", "relationship"].map(k => [k, (ch as any)[`default_${k}`]])) }}
        onChange={patch => run("已保存为角色库新版本", () => api.updateCharacter(ch.id, Object.fromEntries(Object.entries(patch).map(([k, v]) => [k === "identity" ? "name" : k === "visual_state" ? "appearance" : ["desire", "fear", "secrets", "knowledge", "relationship"].includes(k) ? `default_${k}` : k, v]))))}
        extras={{}} />}
      {tab === "appearance" && <>
      <CharacterProfile scope="global" onlySections={["外观与造型"]} values={{ visual_state: ch.appearance || "" }} onChange={patch => run("已保存角色外观描述", () => api.updateCharacter(ch.id, { appearance: patch.visual_state }))} />
      <section className="focus-section">
        <h3 id="studio-images">形象生成与编辑</h3>
        <p className="muted">AI 生图和编辑都会生成新的候选图，不会覆盖原始形象。选定主图后再确认生成标准视图。</p>
        <div className="two">
          <label><span>AI 创建 / 外观补充</span>
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)}
              placeholder="例如：深色雨衣、短发、疲惫但警觉" /></label>
          <div className="row" style={{ alignItems: "end" }}>
            <button className="primary" disabled={!!busy}
              onClick={() => paidEnabled
                ? run("已生成 2 张候选图", () => api.aiGenerateCharacter(ch.id, prompt, 2))
                : toast("当前云端形象生成暂时不可用。你仍可以上传已有素材或编辑角色文字信息。")}>
              {busy === "已生成 2 张候选图" ? "生成中…" : "AI 生成 2 张候选图"}
            </button>
            <button disabled={!!busy || !studioAssets.find((a) => a.status === "CANONICAL" && a.role === "front")}
              onClick={() => setConfirmViews(studioAssets.find((a) => a.status === "CANONICAL" && a.role === "front")?.id ?? null)}>
              选择主图并生成标准视图
            </button>
          </div>
        </div>
        <div className="studio-asset-grid">
          {studioAssets.map((a) => <article className="studio-asset" key={a.id}>
            <img src={a.url.startsWith("/") ? a.url : a.url} alt={a.role} />
            <div className="row"><b className="grow">{ROLE_LABELS[a.role] || (developer ? a.role : "参考图")}</b>{developer && <span className="status-pill">{a.status}</span>}</div>
            {developer && <details><summary>Provider / Model / Prompt / request ID</summary><pre>{JSON.stringify(a, null, 2)}</pre></details>}
            <div className="row">
              {a.status === "CANDIDATE" && <button className="small" onClick={() => run(developer ? "Candidate 已批准" : "候选图已确认", () => api.setCharacterAssetStatus(a.id, "APPROVED"))}>{developer ? "批准" : "确认候选图"}</button>}
              {(a.status === "APPROVED" || a.status === "CANDIDATE") && <button className="small" onClick={() => run(developer ? "已设为 Canonical" : "已设为主形象", () => api.approveCharacterAsset(ch.id, a.id))}>{developer ? "设为 Canonical" : "设为主形象"}</button>}
            </div>
          </article>)}
        </div>
        <label><span>编辑源图</span><select value={editSourceId} onChange={(e) => setEditSourceId(e.target.value)}>
          <option value="">选择候选图或主形象</option>
          {studioAssets.map((a) => <option value={a.id} key={a.id}>{ROLE_LABELS[a.role] || (developer ? a.role : "参考图")} · {developer ? `${a.status} · ${a.id}` : (a.status === "CANONICAL" ? "主形象" : "候选图")}</option>)}
        </select></label>
        <div className="toolbar quick-edit-actions" aria-label="快捷编辑">
          {([['换装','换成黄色雨衣，保持身份不变'], ['换背景','更换为故事场景背景'], ['换表情','调整为克制、警觉的表情'], ['换姿势','调整为站立观察姿势'], ['换视角','改为三分之四视角']] as const).map(([label, instruction]) => <button key={label} className="small" onClick={() => { setEditInstruction(instruction); if (!paidEnabled) toast("当前云端形象生成暂时不可用。快捷编辑已保留为待执行意图。"); }}>{label}</button>)}
        </div>
        {confirmViews && <div className="notice">
              <b>{paidEnabled ? "生成标准参考图？将基于主图生成其他视角，请确认后继续。" : "当前云端形象生成暂时不可用。"}</b>
          <div className="row">
            <button className="primary" disabled={!!busy} onClick={() => paidEnabled
              ? run("标准视图已生成", async () => { await api.standardCharacterViews(ch.id, confirmViews); setConfirmViews(null); })
              : toast("当前云端形象生成暂时不可用，请稍后重试或上传已有标准参考图。")}>确认生成</button>
            <button disabled={!!busy} onClick={() => setConfirmViews(null)}>取消</button>
          </div>
        </div>}
        <div className="two">
          <label><span>非破坏式编辑（换装 / 背景 / 姿势 / 视角 / 自由文本）</span>
            <textarea value={editInstruction} onChange={(e) => setEditInstruction(e.target.value)}
              placeholder="例如：保持身份不变，换成黄色雨衣，背景改为楼梯间" /></label>
          <div className="row" style={{ alignItems: "end" }}>
            <button disabled={!!busy || !editInstruction || !editSourceId}
              onClick={() => paidEnabled
                ? run(developer ? "编辑 Candidate 已生成" : "新的编辑形象已生成", () => api.editCharacterImage(ch.id, editSourceId, editInstruction))
                : toast("当前云端形象生成暂时不可用。原始形象保持不变。")}>{developer ? "生成编辑 Candidate" : "生成编辑形象"}</button>
          </div>
        </div>
        {!paidEnabled && <div className="notice warn">当前云端形象生成暂时不可用。可上传已有图片、编辑文字资料，或稍后重试。</div>}
      </section></>}
      <CharacterStudio scope="library" tab={tab} libraryCharacter={ch} onLibraryChange={onSaved} />
      {developer && (tab === "usage" || tab === "versions") && <details className="card"><summary>Developer · Reference Override</summary>
        <label><span>已发布故事版本 ID</span><input value={scenarioVersionId} onChange={e => setScenarioVersionId(e.target.value)} /></label>
        <button disabled={!scenarioVersionId || !!busy} onClick={loadSnapshots}>读取版本快照</button>
        {snapshots.filter(snapshot => snapshot.global_character_id === ch.id).map(snapshot => <ReferenceOverrideEditor key={snapshot.id} snapshot={snapshot} onResolved={setResolver} />)}
        {resolver && <pre>{JSON.stringify(resolver, null, 2)}</pre>}
      </details>}
    </>
  );
}

function ReferenceOverrideEditor({ snapshot, onResolved }: { snapshot: any; onResolved: (v: any) => void }) {
  const initial = snapshot.frozen_asset_refs || {};
  const [images, setImages] = useState<string[]>(() => ["front", "three_quarter", "side", "full_front"].map(k => initial[k]).filter(Boolean));
  const [voice, setVoice] = useState(String(initial.voice || ""));
  const [motion, setMotion] = useState(String(initial.motion || ""));
  const [newRef, setNewRef] = useState("");
  const save = async () => {
    const override = { image_refs: images, voice_ref: voice || null, motion_ref: motion || null };
    await api.overrideCharacterSnapshot(snapshot.id, { reference_override: override });
    const resolved = await api.resolveCharacterReferences(snapshot.id, "studio-preview", undefined, override);
    onResolved(resolved); toast("Reference Override 已应用到本次制作预览。");
  };
  return <div className="reference-override-editor">
    <h4>Developer Reference Override</h4>
    <p className="muted">可移除、添加、调整顺序，并指定 Voice / Motion；只影响本次制作参考。</p>
    <div className="override-list">{images.map((ref, i) => <div className="row" key={`${ref}-${i}`}><span className="mono grow">{i + 1}. {ref}</span><button className="small" disabled={i === 0} onClick={() => setImages(v => { const n = [...v]; [n[i - 1], n[i]] = [n[i], n[i - 1]]; return n; })}>上移</button><button className="small" disabled={i === images.length - 1} onClick={() => setImages(v => { const n = [...v]; [n[i + 1], n[i]] = [n[i], n[i + 1]]; return n; })}>下移</button><button className="small danger" onClick={() => setImages(v => v.filter((_, j) => j !== i))}>移除</button></div>)}</div>
    <div className="row"><input value={newRef} onChange={e => setNewRef(e.target.value)} placeholder="输入图片 asset/ref" /><button className="small" disabled={!newRef.trim()} onClick={() => { setImages(v => [...v, newRef.trim()].slice(0, 4)); setNewRef(""); }}>添加</button></div>
    <div className="two"><label><span>Voice</span><input value={voice} onChange={e => setVoice(e.target.value)} placeholder="Voice A asset/ref" /></label><label><span>Motion</span><input value={motion} onChange={e => setMotion(e.target.value)} placeholder="run_01 asset/ref" /></label></div>
    <button className="small" onClick={() => void save()}>使用此 Override</button>
  </div>;
}
