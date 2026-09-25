/** 全局角色库：跨故事共享的稳定角色身份资产；故事使用快照，不被后续修改覆盖。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import CharacterProfile from "../components/CharacterProfile";
import type { Asset, CharacterAsset, CharacterVersion, GlobalCharacter } from "../types";

const ROLE_LABELS: Record<string,string> = {front:"主身份图",three_quarter:"四分之三视图",side:"侧面视图",back:"背面视图",full_front:"全身正面",full_side:"全身侧面",outfit:"造型参考",pose:"姿势参考",motion:"动作参考",voice:"声音参考",derived:"编辑后的形象"};
const STUDIO_TABS = [["overview", "概览"], ["identity", "身份"], ["appearance", "造型"], ["motion", "姿势与动作"], ["voice", "声音"], ["usage", "使用记录"], ["versions", "版本"]] as const;
export default function CharacterLibrary() {
  const ui = useUi();
  const [items, setItems] = useState<GlobalCharacter[]>([]);
  const [q, setQ] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const reload = () => api.listCharacters(q).then((r) => setItems(r.items)).catch(() => {});
  useEffect(() => { reload(); }, [q]);

  const selected = items.find((g) => g.id === ui.globalCharacterId) ?? null;
  if (selected) {
    return <CharacterDetail ch={selected} onBack={() => setState({ globalCharacterId: null })}
      onSaved={reload} />;
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
      {createOpen && <CharacterCreate onClose={() => setCreateOpen(false)} onCreated={(id) => {
        setCreateOpen(false); setState({ globalCharacterId: id }); reload();
      }} />}
    </>
  );
}

function CharacterCreate({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [kind, setKind] = useState<"ai" | "image" | "manual">("ai");
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [personality, setPersonality] = useState("");
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [paidEnabled, setPaidEnabled] = useState(false);
  useEffect(() => { api.devGenerationSettings().then((v) => setPaidEnabled(Boolean(v.fal_paid_generation_enabled))).catch(() => {}); }, []);
  const submit = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    try {
      const created = createdId ? { id: createdId } : await api.createCharacter({ name: name.trim(), bio, personality });
      setCreatedId(created.id);
      if (kind === "ai") {
        if (!paidEnabled) {
          toast("角色已创建。当前云端形象生成暂时不可用，可先使用文字角色或上传已有图片。");
        } else {
          await api.aiGenerateCharacter(created.id, prompt || bio, 2);
          toast("角色已创建，2 张候选图正在角色 Studio 中展示。请选图并确认主形象。");
        }
      } else if (kind === "image" && file) {
        const asset = await api.importCharacterBaseline(created.id, file);
        toast("图片已作为身份参考保存，请在 Studio 中确认主形象。");
      } else {
        toast("无图片角色已创建，可在 Studio 中继续补充形象。");
      }
      onCreated(created.id);
    } catch (e: any) { toast(`创建失败：${e.message}`); }
    finally { setBusy(false); }
  };
  return <div className="modal-mask" role="dialog" aria-modal="true">
    <div className="modal">
      <div className="row"><h3 className="grow">新建角色</h3><button onClick={onClose}>关闭</button></div>
      <p className="muted">三条入口最终都会进入同一个 Character Studio。</p>
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

function CharacterDetail({ ch, onBack, onSaved }: {
  ch: GlobalCharacter; onBack: () => void; onSaved: () => void;
}) {
  const [draft, setDraft] = useState(ch);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [understanding, setUnderstanding] = useState<Record<string, string> | null>(null);
  const [studioAssets, setStudioAssets] = useState<CharacterAsset[]>([]);
  const [versions, setVersions] = useState<CharacterVersion[]>([]);
  const [prompt, setPrompt] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [busy, setBusy] = useState("");
  const [confirmViews, setConfirmViews] = useState<string | null>(null);
  const [outfitName, setOutfitName] = useState("");
  const [outfits, setOutfits] = useState<any[]>([]);
  const [scenarioVersionId, setScenarioVersionId] = useState("");
  const [scenarioChoices, setScenarioChoices] = useState<{ id: string; title: string; version: string }[]>([]);
  const [scenarioId, setScenarioId] = useState("");
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [resolver, setResolver] = useState<any>(null);
  const [tab, setTab] = useState<(typeof STUDIO_TABS)[number][0]>("overview");
  const [paidEnabled, setPaidEnabled] = useState(false);
  const [diff, setDiff] = useState<any>(null);
  const [overrideJson, setOverrideJson] = useState('{"appearance":""}');
  const [overrideText, setOverrideText] = useState("");
  const [editSourceId, setEditSourceId] = useState("");
  const developer = useUi().mode === "developer";
  useEffect(() => setDraft(ch), [ch.id, ch.version]);
  const loadAssets = () =>
    api.listCharacterAssets(ch.id).then((r) => setAssets(r.items)).catch(() => {});
  const loadStudio = () => {
    void api.listCharacterStudioAssets(ch.id).then((r) => setStudioAssets(r.items)).catch(() => {});
    void api.characterVersions(ch.id).then((r) => setVersions(r.items)).catch(() => {});
    void api.listCharacterOutfits(ch.id).then((r) => setOutfits(r.items)).catch(() => {});
  };
  useEffect(() => { void loadAssets(); loadStudio(); }, [ch.id, ch.version]);
  useEffect(() => {
    if (developer) return;
    api.listScenarios().then(async ({ items }) => {
      const rows: { id: string; title: string; version: string }[] = [];
      for (const s of items) {
        try {
          const vs = await api.scenarioVersions(s.id);
          for (const v of vs.items) rows.push({ id: s.id, title: s.title, version: v.version_id });
        } catch { /* a draft has no versions */ }
      }
      setScenarioChoices(rows);
    }).catch(() => {});
  }, [developer]);
  const loadSnapshots = () => scenarioVersionId
    ? api.listCharacterSnapshots(scenarioVersionId).then((r) => setSnapshots(r.items)).catch(() => {})
    : undefined;
  useEffect(() => { if (scenarioVersionId) void loadSnapshots(); }, [scenarioVersionId]);
  useEffect(() => { api.devGenerationSettings().then((v) => setPaidEnabled(Boolean(v.fal_paid_generation_enabled))).catch(() => {}); }, []);

  const run = async (label: string, action: () => Promise<unknown>) => {
    setBusy(label);
    try { await action(); toast(label); loadStudio(); onSaved(); }
    catch (e: any) { toast(`${label}失败：${e.message}`); }
    finally { setBusy(""); }
  };

  const save = async () => {
    try {
      await api.updateCharacter(ch.id, {
        name: draft.name, bio: draft.bio, personality: draft.personality, tags: draft.tags,
      });
      toast("已保存为新版本；已有故事仍继续使用各自的角色快照。");
      onSaved();
    } catch (e: any) {
      toast(`保存失败：${e.message}`);
    }
  };

  /** 绑定/解绑 ref_* 槽位（立即 PATCH 生成新版本，快照语义保持不变） */
  const bindRef = async (key: string, assetId: string | null, multi?: boolean) => {
    try {
      const cur = (ch as any)[key];
      const patch: Record<string, any> = multi
        ? { [key]: Array.isArray(cur)
            ? (cur.includes(assetId)
                ? cur.filter((x: string) => x !== assetId)
                : [...cur, assetId])
            : assetId ? [assetId] : [] }
        : { [key]: (cur === assetId ? null : assetId) };
      const updated = await api.updateCharacter(ch.id, patch as Partial<GlobalCharacter>);
      setDraft(updated);
      toast("引用已更新为新版本。");
      onSaved();
    } catch (e: any) {
      toast(`绑定失败：${e.message}`);
    }
  };

  /** 上传到角色全局素材池，成功后自动绑定到该槽位 */
  const uploadRef = async (key: string, file: File) => {
    try {
      const role = key === "ref_voice_asset" ? "voice"
        : key === "ref_motion_asset" ? "motion" : "identity";
      const a = await api.uploadCharacterAsset(ch.id, file, role);
      toast(`已上传「${a.name}」。`);
      loadAssets();
      await bindRef(key, a.id, key === "ref_other_assets");
    } catch (e: any) {
      toast(`上传失败：${e.message}`);
    }
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
      <nav className="studio-tabs" aria-label="角色工作台">
        {STUDIO_TABS.map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}
      </nav>
      {tab === "overview" && <section className="card"><h3>AI 对这个角色的理解</h3><p>{ch.bio}</p>
        <button disabled={!!busy} onClick={() => run("已整理角色建议", async () => setUnderstanding(await api.characterUnderstanding(ch.id)))}>让 AI 补充可选信息</button>
        {understanding && <div className="understanding-grid">{Object.entries(understanding).map(([key, value]) => <div className="understanding-item" key={key}><p>{value}</p><button onClick={() => run("已确认角色建议", async () => { await api.updateCharacter(ch.id, { [key]: value }); setUnderstanding(old => { const n = { ...old }; delete n[key]; return n; }); })}>接受</button><button onClick={() => setUnderstanding(old => { const n = { ...old }; delete n[key]; return n; })}>忽略</button></div>)}</div>}
      </section>}
      {tab === "identity" && <CharacterProfile scope="global" onlySections={["身份", "人格与动机", "认知与秘密", "关系"]} values={{ identity: ch.name, bio: ch.bio, personality: ch.personality,
        visual_state: ch.appearance, ...Object.fromEntries(["desire", "fear", "secrets", "knowledge", "relationship"].map(k => [k, (ch as any)[`default_${k}`]])) }}
        onChange={patch => run("已保存为角色库新版本", () => api.updateCharacter(ch.id, Object.fromEntries(Object.entries(patch).map(([k, v]) => [k === "identity" ? "name" : k === "visual_state" ? "appearance" : ["desire", "fear", "secrets", "knowledge", "relationship"].includes(k) ? `default_${k}` : k, v]))))}
        extras={{}} />}
      {tab === "appearance" && <>
      <section id="studio-images" className="focus-section">
        <h3>{developer ? "Outfit 管理" : "造型管理"}</h3>
        <div className="row">
          <input value={outfitName} onChange={(e) => setOutfitName(e.target.value)} placeholder="造型名称，例如：黄色雨衣" />
          <button disabled={!outfitName || !!busy} onClick={() => run("造型已创建", async () => {
            await api.createCharacterOutfit(ch.id, outfitName); setOutfitName("");
            const next = await api.listCharacterOutfits(ch.id); setOutfits(next.items);
          })}>添加造型</button>
        </div>
        <div className="pillrow">{outfits.map((o) => <span className="soft-tag" key={o.id}>{o.name}{o.is_default ? " · 默认造型" : ""}</span>)}</div>
        <p className="muted">每套造型可继续上传 front / side / back / full body 参考图。生成按钮遵守当前云端保险丝。</p>
      </section>
      <section className="focus-section">
        <h3>Character Studio</h3>
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
            <button className="primary" onClick={() => paidEnabled
              ? run("标准视图已生成", async () => { await api.standardCharacterViews(ch.id, confirmViews); setConfirmViews(null); })
              : toast("当前云端形象生成暂时不可用，请稍后重试或上传已有标准参考图。")}>确认生成</button>
            <button onClick={() => setConfirmViews(null)}>取消</button>
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
      {(tab === "usage" || tab === "versions") && <section id="studio-versions" className="focus-section">
        <h3>{developer ? "Character Version / Diff" : "版本与变化"}</h3>
        {versions.length === 0 ? <p className="muted">保存资料或主形象后会形成版本。</p> : <table className="dev"><thead><tr><th>版本</th><th>变更</th><th>时间</th></tr></thead><tbody>
          {versions.map((v) => <tr key={v.id}><td>v{v.version}</td><td>{developer ? v.change_type : ({ IDENTITY: "身份变化", APPEARANCE: "造型变化", METADATA: "资料变化", ASSET_ADDITION: "新增参考图" } as Record<string, string>)[v.change_type] || "角色更新"}</td><td>{new Date(v.created_at).toLocaleString()}</td></tr>)}
        </tbody></table>}
        {versions.length >= 2 && <button onClick={() => api.characterVersionDiff(ch.id, versions[versions.length - 1].version, versions[0].version).then(setDiff)}>{developer ? "查看首末版本 Diff" : "查看版本变化"}</button>}
        {diff && <>{developer ? <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(diff, null, 2)}</pre> : <div className="notice">{Object.entries(diff.field_diffs || {}).map(([k, d]: [string, any]) => <p key={k}><b>{{name: "姓名", bio: "角色定义", personality: "人格", appearance: "外观", default_desire: "默认动机", default_fear: "默认恐惧", default_secrets: "默认秘密", default_knowledge: "默认认知", default_relationship: "默认关系", tags: "标签"}[k] || "角色信息"}</b>：{String(d.before || "未设置")} → {String(d.after || "未设置")}</p>)}<p>参考素材变化：{Object.keys(diff.asset_diffs || {}).length} 项</p></div>}</>}
        <div className="two">
          {developer ? <label><span>Scenario Version ID</span>
            <input value={scenarioVersionId} onChange={(e) => setScenarioVersionId(e.target.value)} placeholder="粘贴已发布版本 ID" /></label>
            : <label><span>选择正在使用这个角色的故事</span><select value={scenarioVersionId} onChange={(e) => { setScenarioVersionId(e.target.value); setScenarioId(e.target.selectedOptions[0]?.dataset.scenario || ""); }}>
              <option value="">选择已发布故事</option>
              {scenarioChoices.map((s) => <option key={s.version} value={s.version} data-scenario={s.id}>{s.title} · 已发布版本</option>)}
            </select></label>}
          <div className="row" style={{ alignItems: "end" }}>
            <button disabled={!scenarioVersionId || !!busy} onClick={() => run(developer ? "Scenario Snapshot 已创建" : "故事角色版本已记录", async () => {
              await api.characterSnapshot(scenarioVersionId, ch.id); loadSnapshots();
            })}>{developer ? "创建快照" : "记录故事使用版本"}</button>
            <button disabled={!scenarioVersionId} onClick={loadSnapshots}>{developer ? "查看快照" : "查看使用记录"}</button>
          </div>
        </div>
        {snapshots.filter((s) => s.global_character_id === ch.id).map((s) => <div className="notice" key={s.id}>
          <div className="row"><b className="grow">当前故事正在使用角色 v{s.character_version}</b>{developer && <span className="status-pill">Snapshot {s.id}</span>}</div>
          {!developer && <p className="muted">角色库已有 v{ch.version}。故事快照会保持当前版本，直到你选择更新。</p>}
          {developer ? <><label><span>Local Override JSON</span><textarea value={overrideJson} onChange={(e) => setOverrideJson(e.target.value)} /></label><ReferenceOverrideEditor snapshot={s} onResolved={setResolver} /></>
            : <label><span>本故事专属修改</span><textarea value={overrideText} onChange={(e) => setOverrideText(e.target.value)} placeholder="例如：本故事中换成黄色雨衣，但保持身份不变" /></label>}
          <div className="row">
            <button className="small" onClick={() => run(developer ? "Local Override 已保存" : "本故事修改已保存", async () => {
              await api.overrideCharacterSnapshot(s.id, developer ? JSON.parse(overrideJson) : { appearance: overrideText }); loadSnapshots();
            })}>{developer ? "Local Override" : "保存本故事修改"}</button>
            <button className="small" onClick={() => run(developer ? "已提升到全局角色" : "已保存为角色库新版本", () => api.promoteCharacterSnapshot(s.id))}>{developer ? "Promote Global" : "保存为角色库新版本"}</button>
            {developer && <button className="small" onClick={() => api.resolveCharacterReferences(s.id, "studio-preview").then(setResolver).then(() => toast("已更新本故事的参考图"))}>{developer ? "Resolve References" : "更新制作参考"}</button>}
          </div>
        </div>)}
        {resolver && (developer ? <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(resolver, null, 2)}</pre> : <div className="notice">制作参考已解析，可用于本故事后续场景。</div>)}
      </section>}
      {tab === "appearance" && <section className="focus-section">
        <h3>视觉身份</h3>
        <RefSlotGrid ch={ch} assets={assets} onPick={bindRef} onUpload={uploadRef}
          slots={[
            { key: "ref_front_asset", title: "正面图", accept: "image" },
            { key: "ref_side_asset", title: "侧面图", accept: "image" },
            { key: "ref_back_asset", title: "背面图", accept: "image" },
          ]} />
        <RefSlotGrid ch={ch} assets={assets} onPick={bindRef} onUpload={uploadRef} multi
          slots={[{ key: "ref_other_assets", title: "其他参考图片", accept: "image" }]} />
        <p className="muted">形象参考绑定后随角色快照固定；上传的素材保存在角色库素材池。</p>
      </section>}
      {(tab === "motion" || tab === "voice") && <section id="studio-voice" className="focus-section">
        <h3>{tab === "voice" ? "声音" : "姿势与动作"}</h3>
        <RefSlotGrid ch={ch} assets={assets} onPick={bindRef} onUpload={uploadRef}
          slots={tab === "voice" ? [
            { key: "ref_voice_asset", title: "主声音（Canonical）", accept: "voice" },
            { key: "alternate_voice_assets", title: "备用声音", accept: "voice" },
          ] : [
            { key: "ref_pose_assets", title: "静态姿势参考", accept: "image" },
            { key: "ref_motion_assets", title: "动作视频参考", accept: "video" },
          ]} multi />
      </section>}
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

/** ref_* 槽位组：已绑定素材缩略预览 + 从角色素材池选择 / 直接上传 / 解绑 */
function RefSlotGrid({ ch, assets, slots, onPick, onUpload, multi }: {
  ch: GlobalCharacter; assets: Asset[]; onUpload: (key: string, file: File) => void;
  slots: { key: string; title: string; accept: "image" | "voice" | "video" }[];
  onPick: (key: string, assetId: string | null, multi?: boolean) => void;
  multi?: boolean;
}) {
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const boundIds = (key: string): string[] => {
    const v = (ch as any)[key];
    return Array.isArray(v) ? v : v ? [v] : [];
  };
  return (
    <div className="identity-grid">
      {slots.map((slot) => {
        const pool = assets.filter((a) => a.type === slot.accept);
        const bound = boundIds(slot.key);
        return (
          <div className="identity-panel" key={slot.key}>
            <div className="row"><h4 className="grow">{slot.title}</h4>
              <button className="small" onClick={() => fileRefs.current[slot.key]?.click()}>
                上传</button>
              <input type="file" hidden
                accept={slot.accept === "image" ? "image/*" : slot.accept === "voice" ? "audio/*" : "video/*"}
                ref={(el) => { fileRefs.current[slot.key] = el; }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onUpload(slot.key, f);
                  e.target.value = "";
                }} />
            </div>
            {bound.length === 0 && <div className="muted">尚未添加</div>}
            {bound.map((aid) => {
              const a = assets.find((x) => x.id === aid);
              return (
                <div className="ref-chip" key={aid} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {a?.type === "image" &&
                    <img src={`/files/${a.storage_path}`} alt={a.name}
                      style={{ width: 40, height: 40, objectFit: "cover", borderRadius: 4 }} />}
                  {a?.type === "voice" && <audio controls src={`/files/${a.storage_path}`} style={{ height: 26 }} />}
                  {a?.type === "video" && <video src={`/files/${a.storage_path}`} style={{ width: 56 }} />}
                  <span className="grow" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                    {a?.name || "已绑定参考"}</span>
                  <button className="small danger" onClick={() => onPick(slot.key, aid, multi)}>解绑</button>
                </div>
              );
            })}
            {pool.filter((a) => !bound.includes(a.id)).length > 0 && (
              <select defaultValue="" onChange={(e) => {
                if (e.target.value) { onPick(slot.key, e.target.value, multi); e.target.value = ""; }
              }}>
                <option value="" disabled>从素材池选择…</option>
                {pool.filter((a) => !bound.includes(a.id)).map((a) => (
                  <option key={a.id} value={a.id}>{a.name}（{a.type}）</option>
                ))}
              </select>
            )}
          </div>
        );
      })}
    </div>
  );
}
