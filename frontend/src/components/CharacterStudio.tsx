import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";
import type { Asset, CharacterAsset, CharacterOutfit, CharacterVersion, GlobalCharacter, ScenarioCharacter } from "../types";

export const STUDIO_TABS = [["overview", "概览"], ["identity", "身份"], ["appearance", "造型"], ["motion", "姿势与动作"], ["voice", "声音"], ["usage", "使用记录"], ["versions", "版本"]] as const;
export type StudioTab = typeof STUDIO_TABS[number][0];
type Scope = "library" | "scenario";
type ReferenceMap = Record<string, string | string[] | null>;
type Media = { id: string; name: string; type: Asset["type"]; url: string; scope: Scope };
const IDENTITY_SLOTS = [["front", "主身份图"], ["three_quarter", "四分之三"], ["side", "侧面"], ["full_front", "全身正面"], ["full_side", "全身侧面"], ["back", "额外背面参考"], ["other", "其他参考图"]] as const;
const REF_KEYS: Record<string, keyof GlobalCharacter> = { front: "ref_front_asset", three_quarter: "ref_three_quarter_asset", side: "ref_side_asset", full_front: "ref_full_front_asset", full_side: "ref_full_side_asset", back: "ref_back_asset", other: "ref_other_assets" };
const CHANGE_LABELS: Record<string, string> = { IDENTITY: "身份变化", APPEARANCE: "造型变化", METADATA: "资料变化", ASSET_ADDITION: "新增参考素材" };
const ids = (value: string | string[] | null | undefined) => Array.isArray(value) ? value : value ? [value] : [];
const unique = (values: string[]) => [...new Set(values)];
const uploadedMedia = (a: Asset, scope: Scope): Media => ({ id: a.id, name: a.name, type: a.type, url: `/files/${a.storage_path}`, scope });

export function CharacterStudioTabs({ tab, onChange }: { tab: StudioTab; onChange: (tab: StudioTab) => void }) {
  return <nav className="studio-tabs" aria-label="角色工作台">{STUDIO_TABS.map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => onChange(id)}>{label}</button>)}</nav>;
}

/** Shared media/version management. Only this scope boundary chooses write APIs. */
export default function CharacterStudio({ scope, tab, libraryCharacter, character, scenarioId, onScenarioChange, onLibraryChange, onPromote }: {
  scope: Scope; tab: StudioTab; libraryCharacter?: GlobalCharacter; character?: ScenarioCharacter;
  scenarioId?: string; onScenarioChange?: (patch: Partial<ScenarioCharacter>) => Promise<boolean>;
  onLibraryChange?: () => void; onPromote?: () => Promise<unknown>;
}) {
  const [pool, setPool] = useState<Media[]>([]);
  const [versions, setVersions] = useState<CharacterVersion[]>([]);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const operationLock = useRef(false);
  const [diff, setDiff] = useState<any>(null);
  const [usages, setUsages] = useState<Array<{ id: string; title: string; version: number | null; published: boolean }>>([]);
  const [selectedOutfit, setSelectedOutfit] = useState("");
  const [paidEnabled, setPaidEnabled] = useState(false);
  const developer = useUi().mode === "developer";
  const cid = libraryCharacter?.id;
  const isScenario = scope === "scenario";

  useEffect(() => {
    let current = true;
    const load = async () => {
      const [uploads, generated, history, storyAssets] = await Promise.all([
        cid ? api.listCharacterAssets(cid) : Promise.resolve({ items: [] as Asset[] }),
        cid ? api.listCharacterStudioAssets(cid) : Promise.resolve({ items: [] as CharacterAsset[] }),
        cid ? api.characterVersions(cid) : Promise.resolve({ items: [] as CharacterVersion[] }),
        isScenario && scenarioId ? api.listAssets(scenarioId) : Promise.resolve({ items: [] as Asset[] }),
      ]);
      if (!current) return;
      const media = [
        ...uploads.items.map(a => uploadedMedia(a, "library")),
        ...generated.items.map((a, index) => ({ id: a.id, name: `${IDENTITY_SLOTS.find(([key]) => key === a.role)?.[1] || "角色形象"} · ${a.status === "CANONICAL" ? "主形象" : `候选图 ${index + 1}`}`, type: "image" as const, url: a.url, scope: "library" as const })),
        ...storyAssets.items.map(a => uploadedMedia(a, "scenario")),
      ];
      setPool([...new Map(media.map(a => [a.id, a])).values()]);
      setVersions(history.items);
    };
    void load().catch(() => toast("参考素材暂时无法加载，请稍后重试。"));
    return () => { current = false; };
  }, [cid, libraryCharacter?.version, scenarioId, isScenario, revision]);

  useEffect(() => {
    api.devGenerationSettings().then(v => setPaidEnabled(Boolean(v.fal_paid_generation_enabled))).catch(() => {});
  }, []);
  useEffect(() => { setDiff(null); setSelectedOutfit(""); }, [cid, character?.id, character?.global_character_version]);
  useEffect(() => {
    if (tab !== "usage" || !cid) return;
    let current = true;
    api.listScenarios().then(async result => {
      const rows = await Promise.all(result.items.map(async item => {
        const story = await api.getScenario(item.id);
        return story.characters.filter(c => c.global_character_id === cid).map(c => ({ id: story.id, title: story.title, version: c.global_character_version ?? null, published: story.status === "PUBLISHED" }));
      }));
      if (current) setUsages(rows.flat());
    }).catch(() => {});
    return () => { current = false; };
  }, [cid, tab, revision]);

  const pinned = isScenario ? versions.find(v => v.version === character?.global_character_version) : undefined;
  const pinnedUnavailable = isScenario && Boolean(cid && character?.global_character_version) && !pinned;
  const inheritedRefs: ReferenceMap = isScenario ? (pinned?.canonical_asset_refs || {}) : Object.fromEntries(Object.entries(REF_KEYS).map(([slot, key]) => [slot, (libraryCharacter?.[key] ?? null) as ReferenceMap[string]]));
  if (!isScenario && versions[0]) {
    for (const [slot, value] of Object.entries(versions[0].canonical_asset_refs)) {
      if (!inheritedRefs[slot]) inheritedRefs[slot] = value;
    }
  }
  const baseOutfits = isScenario ? pinned?.outfits || [] : libraryCharacter?.outfits || [];
  const basePoses = isScenario ? pinned?.pose_refs || [] : libraryCharacter?.ref_pose_assets || [];
  const baseMotions = isScenario ? pinned?.motion_refs || [] : libraryCharacter?.ref_motion_assets?.length ? libraryCharacter.ref_motion_assets : libraryCharacter?.ref_motion_asset ? [libraryCharacter.ref_motion_asset] : [];
  const canonicalVoice = isScenario ? pinned?.canonical_voice_ref : libraryCharacter?.ref_voice_asset;
  const alternateVoices = isScenario ? pinned?.alternate_voice_refs || [] : libraryCharacter?.alternate_voice_assets || [];
  const isOverride = (key: string) => character?.overlay_sources?.[key] === "OVERRIDE";
  const sources = (key: string, value: "INHERIT" | "OVERRIDE") => ({ ...character?.overlay_sources, [key]: value });
  const saveScenario = (patch: Partial<ScenarioCharacter>) => onScenarioChange?.(patch);
  const run = async (operation: () => Promise<unknown>, note = "已保存") => {
    if (operationLock.current) return;
    operationLock.current = true;
    setBusy(true);
    try { await operation(); setRevision(v => v + 1); onLibraryChange?.(); toast(note); }
    catch { toast("操作未完成，请重试。原有角色资料仍保留。"); }
    finally { operationLock.current = false; setBusy(false); }
  };
  const upload = async (file: File, role: string): Promise<string> => {
    const a = isScenario && scenarioId
      ? await api.uploadAsset(scenarioId, file, { role, entity: character?.id, binding: character?.id })
      : await api.uploadCharacterAsset(cid!, file, role);
    setPool(current => [...current, uploadedMedia(a, scope)]);
    return a.id;
  };
  const saveRef = (slot: string, value: ReferenceMap[string]) => {
    if (isScenario) saveScenario({ reference_overrides: { ...character?.reference_overrides, [slot]: value }, overlay_sources: sources("reference", "OVERRIDE") });
    else void run(() => api.updateCharacter(cid!, { [REF_KEYS[slot]]: value }), "参考组已保存为角色库新版本");
  };
  const allOutfits = [...baseOutfits, ...(character?.local_outfits || [])];
  const displayedOutfitId = isScenario ? character?.outfit_id || baseOutfits.find(o => o.is_default)?.id : selectedOutfit || baseOutfits.find(o => o.is_default)?.id || baseOutfits[0]?.id;
  const outfit = allOutfits.find(o => o.id === displayedOutfitId);
  const selectedPoses = isScenario && isOverride("pose") ? character?.pose_refs || [] : basePoses;
  const selectedMotions = isScenario && isOverride("motion") ? character?.motion_refs || [] : baseMotions;
  const selectedVoice = isScenario && isOverride("voice") ? character?.voice_id : canonicalVoice;
  const updateOutfit = (patch: Partial<CharacterOutfit>) => {
    if (!outfit) return;
    if (!isScenario) { void run(() => api.updateCharacterOutfit(cid!, outfit.id, patch)); return; }
    const existing = character?.local_outfits?.find(o => o.id === outfit.id);
    const changed = { ...outfit, ...patch, id: existing?.id || `local_outfit_${crypto.randomUUID()}`, is_default: false };
    const local = existing ? character!.local_outfits!.map(o => o.id === existing.id ? changed : o) : [...(character?.local_outfits || []), changed];
    saveScenario({ local_outfits: local, outfit_id: changed.id, overlay_sources: sources("outfit", "OVERRIDE") });
  };
  const changeList = (kind: "pose" | "motion", selected: string[]) => {
    if (isScenario) saveScenario({ [kind === "pose" ? "pose_refs" : "motion_refs"]: selected, overlay_sources: sources(kind, "OVERRIDE") });
    else void run(() => api.updateCharacter(cid!, { [kind === "pose" ? "ref_pose_assets" : "ref_motion_assets"]: selected }));
  };
  const chooseVoice = (id: string | null) => {
    if (isScenario) saveScenario({ voice_id: id, overlay_sources: sources("voice", id === canonicalVoice ? "INHERIT" : "OVERRIDE") });
    else void run(() => api.updateCharacter(cid!, { ref_voice_asset: id, alternate_voice_assets: unique([...alternateVoices.filter(v => v !== id), ...(canonicalVoice && canonicalVoice !== id ? [canonicalVoice] : [])]) }));
  };
  const latestVersion = Math.max(libraryCharacter?.version || 0, ...versions.map(v => v.version));
  const summary = <div className="studio-scope-summary">
    {isScenario && cid && <p>来自角色库 v{character?.global_character_version} · 当前角色库最新 v{latestVersion}</p>}
    <dl><dt>造型</dt><dd>{isScenario && !isOverride("outfit") ? "继承角色库默认造型" : outfit?.name || "未选择"}</dd>
      <dt>姿势</dt><dd>{selectedPoses.length} 项 · {isScenario && isOverride("pose") ? "仅本故事" : "继承角色库"}</dd>
      <dt>动作</dt><dd>{selectedMotions.length} 项 · {isScenario && isOverride("motion") ? "仅本故事" : "继承角色库"}</dd>
      <dt>声音</dt><dd>{pool.find(a => a.id === selectedVoice)?.name || (selectedVoice ? "已选声音" : "未设置")} · {isScenario && isOverride("voice") ? "仅本故事" : "主声音"}</dd>
      {isScenario && <><dt>本故事覆盖</dt><dd>{Object.values(character?.overlay_sources || {}).filter(v => v === "OVERRIDE").length} 项</dd></>}</dl>
  </div>;
  return <div className="shared-character-studio" data-scope={scope}>
    {pinnedUnavailable && <p role="status" className="notice">正在加载当前故事固定的角色版本。参考管理会在版本加载完成后开放。</p>}
    {(tab === "identity" || tab === "appearance") && <>
      {tab === "identity" && <section className="focus-section"><h3>标准身份参考组</h3><p className="muted">{isScenario ? "继承当前固定版本的参考组；上传、绑定与解绑只影响本故事。" : "主身份图和标准视图随角色版本保存；额外参考单独管理。"}</p>
        <div className="identity-grid">{IDENTITY_SLOTS.map(([slot, label]) => {
          const overridden = isScenario && Object.prototype.hasOwnProperty.call(character?.reference_overrides || {}, slot);
          const value = overridden ? character?.reference_overrides?.[slot] : inheritedRefs[slot];
          return <MediaSlot key={slot} title={label} type="image" value={value} pool={pool} multiple={slot === "other"} disabled={busy || pinnedUnavailable}
            source={isScenario ? overridden ? "仅本故事" : "继承角色库" : "角色库定义"}
            onChange={v => saveRef(slot, v)} onUpload={f => upload(f, "identity")}
            onInherit={isScenario && overridden ? () => { const next = { ...character?.reference_overrides }; delete next[slot]; saveScenario({ reference_overrides: next, overlay_sources: sources("reference", Object.keys(next).length ? "OVERRIDE" : "INHERIT") }); } : undefined} />;
        })}</div></section>}
      {tab === "appearance" && <section className="focus-section"><h3>{isScenario ? "本故事造型" : "造型管理"}</h3>
        <fieldset disabled={busy || pinnedUnavailable} className="studio-outfit-choices"><legend>选择造型</legend>
          {isScenario && <label className="check-row"><input type="radio" name={`outfit-${character?.id}`} checked={!isOverride("outfit") && !character?.outfit_id} onChange={() => saveScenario({ outfit_id: null, overlay_sources: sources("outfit", "INHERIT") })} />继承角色库默认造型</label>}
          {allOutfits.map(o => <label className="check-row" key={o.id}><input type="radio" name={`outfit-${character?.id || cid}`} checked={isScenario ? character?.outfit_id === o.id : displayedOutfitId === o.id} onChange={() => isScenario ? saveScenario({ outfit_id: o.id, overlay_sources: sources("outfit", "OVERRIDE") }) : setSelectedOutfit(o.id)} /><span>{o.name}</span><small>{character?.local_outfits?.some(local => local.id === o.id) ? "仅本故事" : o.is_default ? "角色库默认" : "继承角色库"}</small></label>)}
        </fieldset>
        <NewOutfit disabled={busy} scope={scope} onCreate={async (name, description) => {
          if (!isScenario) await run(async () => { const added = await api.createCharacterOutfit(cid!, name, description); setSelectedOutfit(added.id); });
          else { const added = { id: `local_outfit_${crypto.randomUUID()}`, name, description, is_default: false, reference_slots: {}, reference_assets: [] }; saveScenario({ local_outfits: [...character?.local_outfits || [], added], outfit_id: added.id, overlay_sources: sources("outfit", "OVERRIDE") }); }
        }} />
        {outfit && <OutfitEditor key={outfit.id} outfit={outfit} scope={scope} pool={pool} disabled={busy || pinnedUnavailable} paidEnabled={paidEnabled} onSave={updateOutfit} onUpload={f => upload(f, "outfit")} />}
      </section>}
    </>}
    {tab === "motion" && <section className="focus-section"><h3>姿势与动作</h3>
      <ReferenceChecklist title={isScenario ? "本故事姿势参考" : "静态姿势参考"} type="image" selected={selectedPoses} inherited={basePoses} pool={pool} scope={scope} disabled={busy || pinnedUnavailable} override={isOverride("pose")} onChange={values => changeList("pose", values)} onUpload={f => upload(f, "pose")} onInherit={() => saveScenario({ pose_refs: [], overlay_sources: sources("pose", "INHERIT") })} />
      <ReferenceChecklist title={isScenario ? "本故事动作参考" : "动作视频参考"} type="video" selected={selectedMotions} inherited={baseMotions} pool={pool} scope={scope} disabled={busy || pinnedUnavailable} override={isOverride("motion")} onChange={values => changeList("motion", values)} onUpload={f => upload(f, "motion")} onInherit={() => saveScenario({ motion_refs: [], overlay_sources: sources("motion", "INHERIT") })} />
    </section>}
    {tab === "voice" && <section className="focus-section"><h3>{isScenario ? "本故事声音" : "声音"}</h3>
      <p className="muted">{isScenario ? "选择主声音会继承角色库；备用或上传的声音仅用于本故事。" : "一个主声音与多个备用声音，随角色版本保存。"}</p>
      <fieldset disabled={busy || pinnedUnavailable}><legend>{isScenario ? "选择本故事声音" : "选择主声音"}</legend>
        {unique([...(canonicalVoice ? [canonicalVoice] : []), ...alternateVoices, ...(selectedVoice ? [selectedVoice] : [])]).map((id, i) => <div className="studio-media-row" key={id}><label className="check-row"><input type="radio" name={`voice-${character?.id || cid}`} checked={selectedVoice === id} onChange={() => chooseVoice(id)} /><span>{id === canonicalVoice ? "主声音" : `备用声音 ${String.fromCharCode(65 + i)}`} · {pool.find(a => a.id === id)?.name || "声音参考"}</span><small>{isScenario ? baseVoiceOrigin(id, canonicalVoice, alternateVoices) : id === canonicalVoice ? "主声音" : "备用声音"}</small></label><MediaPreview media={pool.find(a => a.id === id)} />{!isScenario && id !== canonicalVoice && <button className="small" onClick={() => void run(() => api.updateCharacter(cid!, { alternate_voice_assets: alternateVoices.filter(v => v !== id) }))}>解绑</button>}</div>)}
        <label className="check-row"><input type="radio" name={`voice-${character?.id || cid}`} checked={!selectedVoice} onChange={() => chooseVoice(null)} />{isScenario ? "本故事不使用声音参考" : "暂不设置主声音"}</label>
      </fieldset>
      <MediaSlot title={isScenario ? "上传或绑定本故事专用声音" : "添加备用声音"} type="voice" value={[]} pool={pool} multiple disabled={busy || pinnedUnavailable} onUpload={f => upload(f, "voice")} onChange={value => {
        const values = ids(value); const id = values[values.length - 1]; if (!id) return;
        if (isScenario) chooseVoice(id);
        else void run(() => api.updateCharacter(cid!, canonicalVoice ? { alternate_voice_assets: unique([...alternateVoices, id]).filter(v => v !== canonicalVoice) } : { ref_voice_asset: id }));
      }} />
      {isScenario && isOverride("voice") && <button className="small" onClick={() => saveScenario({ voice_id: canonicalVoice || null, overlay_sources: sources("voice", "INHERIT") })}>恢复继承主声音</button>}
    </section>}
    {(tab === "overview" || tab === "usage" || tab === "versions") && summary}
    {tab === "usage" && <section className="focus-section"><h3>使用记录</h3>{usages.length ? <table><thead><tr><th>故事</th><th>固定角色版本</th><th>状态</th></tr></thead><tbody>{usages.map(row => <tr key={row.id}><td>{row.title}</td><td>v{row.version}</td><td>{row.published ? "已发布" : "草案"}</td></tr>)}</tbody></table> : <p className="muted">这个角色尚未出现在已保存的故事中。</p>}</section>}
    {tab === "versions" && <section className="focus-section"><h3>版本</h3>
      {isScenario && cid && <div className="notice"><p>来自角色库：v{character?.global_character_version} · 当前角色库最新：v{latestVersion}</p>
        {latestVersion > (character?.global_character_version || 0) && <div className="toolbar"><button onClick={() => api.characterVersionDiff(cid, character?.global_character_version || 1, latestVersion).then(setDiff).catch(() => toast("暂时无法读取版本变化"))}>查看变化</button><button onClick={() => toast(`继续使用 v${character?.global_character_version}，本故事没有更新。`)}>继续使用 v{character?.global_character_version}</button><button className="primary" onClick={() => {
          const latest = versions.find(v => v.version === latestVersion); if (!latest) return;
          const patch: Partial<ScenarioCharacter> = { global_character_version: latestVersion };
          for (const [field, core] of [["identity", "name"], ["personality", "personality"], ["visual_state", "appearance"], ...["desire", "fear", "secrets", "knowledge", "relationship"].map(key => [key, `default_${key}`])]) {
            const source = character?.overlay_sources?.[field === "visual_state" ? "appearance" : field];
            if (source === "INHERIT" || (source !== "OVERRIDE" && ((character as any)?.[field] === pinned?.identity_spec[core] || !(character as any)?.[field]))) (patch as any)[field] = latest.identity_spec[core] || "";
          }
          void saveScenario(patch)?.then(saved => { if (saved) { setDiff(null); toast("已更新继承版本；本故事覆盖继续保留。"); } });
        }}>更新到 v{latestVersion}</button></div>}
        {onPromote && <button disabled={busy} onClick={() => void run(onPromote, "已保存为角色库新版本；当前故事仍固定原版本")}>保存为角色库新版本</button>}
      </div>}
      {diff && <div className="notice">{Object.entries(diff.field_diffs || {}).map(([key, value]: [string, any]) => <p key={key}>{({ name: "姓名", bio: "角色定义", personality: "人格", appearance: "外观" } as Record<string, string>)[key] || "角色资料"}：{String(value.before || "未设置")} → {String(value.after || "未设置")}</p>)}<p>参考素材变化：{Object.keys(diff.asset_diffs || {}).length} 项</p>{developer && <pre>{JSON.stringify(diff, null, 2)}</pre>}</div>}
      {versions.length ? <table><thead><tr><th>版本</th><th>变更</th><th>时间</th><th>参考信息</th></tr></thead><tbody>{versions.map(v => <tr key={v.id}><td>v{v.version}{isScenario && v.version === character?.global_character_version ? " · 本故事使用" : ""}</td><td>{CHANGE_LABELS[v.change_type] || "角色更新"}</td><td>{new Date(v.created_at).toLocaleString()}</td><td>造型 {v.outfits.length} · 姿势 {v.pose_refs?.length || 0} · 动作 {v.motion_refs?.length || 0} · 声音 {(v.canonical_voice_ref ? 1 : 0) + (v.alternate_voice_refs?.length || 0)}</td></tr>)}</tbody></table> : <p className="muted">保存角色资料后会产生版本记录。</p>}
    </section>}
  </div>;
}

function baseVoiceOrigin(id: string, canonical?: string | null, alternates: string[] = []) {
  return id === canonical ? "继承角色库" : alternates.includes(id) ? "仅本故事选择" : "仅本故事";
}

function MediaPreview({ media }: { media?: Media }) {
  if (!media) return <span className="muted">已绑定参考素材</span>;
  if (media.type === "image") return <img className="studio-media-thumb" src={media.url} alt={media.name} />;
  if (media.type === "voice") return <audio controls preload="none" src={media.url} aria-label={`试听 ${media.name}`} />;
  return <video controls preload="metadata" className="studio-media-thumb" src={media.url} aria-label={media.name} />;
}

function MediaSlot({ title, type, value, pool, multiple, disabled, source, onChange, onUpload, onInherit }: {
  title: string; type: Asset["type"]; value: ReferenceMap[string] | undefined; pool: Media[]; multiple?: boolean; disabled?: boolean; source?: string;
  onChange: (value: ReferenceMap[string]) => void; onUpload: (file: File) => Promise<string>; onInherit?: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const selected = ids(value);
  return <div className="identity-panel"><div className="row"><h4 className="grow">{title}</h4>{source && <small className="soft-tag">{source}</small>}</div>
    {selected.length ? selected.map(id => <div className="studio-media-row" key={id}><MediaPreview media={pool.find(a => a.id === id)} /><span className="grow">{pool.find(a => a.id === id)?.name || title}</span><button className="small" aria-label={`解绑 ${title} ${pool.find(a => a.id === id)?.name || "参考"}`} disabled={disabled || uploading} onClick={() => onChange(multiple ? selected.filter(v => v !== id) : null)}>解绑</button></div>) : <p className="muted">尚未绑定参考素材</p>}
    <select aria-label={`${title} 从已有素材绑定`} value="" disabled={disabled || uploading} onChange={e => { if (e.target.value) onChange(multiple ? unique([...selected, e.target.value]) : e.target.value); }}><option value="">从已有素材绑定…</option>{pool.filter(a => a.type === type && !selected.includes(a.id)).map(a => <option key={a.id} value={a.id}>{a.name}{a.scope === "scenario" ? " · 仅本故事" : ""}</option>)}</select>
    <label className="studio-upload"><span>{uploading ? "上传中…" : `上传${title}`}</span><input aria-label={`上传${title}`} type="file" accept={type === "image" ? "image/*" : type === "voice" ? "audio/*" : "video/*"} disabled={disabled || uploading} onChange={async e => {
      const file = e.target.files?.[0]; e.target.value = ""; if (!file) return;
      setUploading(true); try { const id = await onUpload(file); onChange(multiple ? unique([...selected, id]) : id); } catch { toast("上传未完成，请重试。"); } finally { setUploading(false); }
    }} /></label>
    {onInherit && <button className="small" disabled={disabled} onClick={onInherit}>恢复继承角色库</button>}
  </div>;
}

function NewOutfit({ scope, disabled, onCreate }: { scope: Scope; disabled: boolean; onCreate: (name: string, description: string) => Promise<void> }) {
  const [name, setName] = useState(""); const [description, setDescription] = useState("");
  return <details className="studio-new-outfit"><summary>{scope === "scenario" ? "+ 本故事新造型" : "+ 添加造型"}</summary><label><span>造型名称</span><input aria-label="新造型名称" value={name} onChange={e => setName(e.target.value)} /></label><label><span>造型描述</span><textarea aria-label="新造型描述" value={description} onChange={e => setDescription(e.target.value)} /></label><button disabled={disabled || !name.trim()} onClick={async () => { await onCreate(name.trim(), description); setName(""); setDescription(""); }}>{scope === "scenario" ? "仅本故事保存造型" : "创建造型"}</button></details>;
}

function OutfitEditor({ outfit, scope, pool, disabled, paidEnabled, onSave, onUpload }: { outfit: CharacterOutfit; scope: Scope; pool: Media[]; disabled: boolean; paidEnabled: boolean; onSave: (patch: Partial<CharacterOutfit>) => void; onUpload: (file: File) => Promise<string> }) {
  const [name, setName] = useState(outfit.name); const [description, setDescription] = useState(outfit.description || "");
  useEffect(() => { setName(outfit.name); setDescription(outfit.description || ""); }, [outfit.name, outfit.description]);
  const slots = outfit.reference_slots || {};
  const inSlots = Object.values(slots).flatMap(v => ids(v));
  const legacyAdditional = (outfit.reference_assets || []).filter(id => !inSlots.includes(id));
  const saveSlot = (slot: string, value: ReferenceMap[string]) => {
    const next = { ...slots, additional: unique([...ids(slots.additional), ...legacyAdditional]), [slot]: value };
    onSave({ reference_slots: next, reference_assets: unique(Object.values(next).flatMap(v => ids(v))) });
  };
  return <article className="studio-outfit-editor"><h4>{outfit.name}{outfit.is_default ? " · 默认造型" : ""}</h4>
    <div className="two"><label><span>名称</span><input aria-label="造型名称" value={name} onChange={e => setName(e.target.value)} /></label><label><span>描述</span><textarea aria-label="造型描述" value={description} onChange={e => setDescription(e.target.value)} /></label></div>
    <div className="toolbar"><button disabled={disabled || !name.trim()} onClick={() => onSave({ name: name.trim(), description })}>{scope === "scenario" ? "仅本故事保存" : "保存造型资料"}</button>{scope === "library" && !outfit.is_default && <button disabled={disabled} onClick={() => onSave({ is_default: true })}>设为默认造型</button>}</div>
    {scope === "scenario" && <p className="muted">修改继承造型会创建本故事专用造型，角色库原造型保持不变。</p>}
    <div className="identity-grid">{[["front", "造型正面"], ["side", "造型侧面"], ["back", "造型背面"], ["full_body", "造型全身"], ["additional", "造型额外参考"]].map(([key, label]) => <MediaSlot key={key} title={label} type="image" value={key === "additional" ? unique([...ids(slots.additional), ...legacyAdditional]) : slots[key]} multiple={key === "additional"} pool={pool} disabled={disabled} onChange={v => saveSlot(key, v)} onUpload={onUpload} />)}</div>
    <div className="toolbar"><button disabled={!paidEnabled} onClick={() => toast("请在形象生成区填写造型描述并确认生成。")}>AI 生成{!paidEnabled ? " · 当前不可用" : ""}</button><button disabled={!paidEnabled} onClick={() => { document.getElementById("studio-images")?.scrollIntoView({ behavior: "smooth" }); toast("请在形象编辑区选择源图并填写换装要求。"); }}>编辑现有形象{!paidEnabled ? " · 当前不可用" : ""}</button></div>
  </article>;
}

function ReferenceChecklist({ title, type, selected, inherited, pool, scope, disabled, override, onChange, onUpload, onInherit }: {
  title: string; type: "image" | "video"; selected: string[]; inherited: string[]; pool: Media[]; scope: Scope; disabled: boolean; override: boolean;
  onChange: (values: string[]) => void; onUpload: (file: File) => Promise<string>; onInherit: () => void;
}) {
  const options = unique([...inherited, ...selected]);
  return <div className="studio-reference-checklist"><fieldset disabled={disabled}><legend>{title}</legend>
    {scope === "scenario" && <p className="muted">{override ? "仅本故事 · 可取消全部参考" : "继承角色库"}</p>}
    {options.map((id, index) => <div className="studio-media-row" key={id}><label className="check-row"><input type="checkbox" checked={selected.includes(id)} onChange={() => onChange(selected.includes(id) ? selected.filter(v => v !== id) : [...selected, id])} /><span>{pool.find(a => a.id === id)?.name || `${title} ${index + 1}`}</span><small>{inherited.includes(id) ? "继承角色库" : "仅本故事"}</small></label><MediaPreview media={pool.find(a => a.id === id)} /></div>)}
    {!options.length && <p className="muted">尚未添加参考素材。</p>}
    {scope === "scenario" && override && <button className="small" onClick={onInherit}>恢复继承角色库</button>}
    </fieldset><MediaSlot title={scope === "scenario" ? `${title}专用素材` : `添加${title}`} type={type} value={[]} pool={pool.filter(a => !selected.includes(a.id))} multiple disabled={disabled} onUpload={onUpload} onChange={v => onChange(unique([...selected, ...ids(v)]))} />
  </div>;
}
