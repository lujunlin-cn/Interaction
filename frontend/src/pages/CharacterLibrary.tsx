/** 全局角色库：跨故事共享的稳定角色身份资产；故事使用快照，不被后续修改覆盖。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import type { Asset, CharacterAsset, CharacterVersion, GlobalCharacter } from "../types";

export default function CharacterLibrary() {
  const ui = useUi();
  const [items, setItems] = useState<GlobalCharacter[]>([]);
  const [q, setQ] = useState("");

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
          <p className="muted">跨故事共享稳定的角色身份资产。故事使用的是角色快照，不会被角色库的后续修改自动覆盖。</p>
        </div>
        <button className="primary" onClick={async () => {
          const created = await api.createCharacter({ name: "新角色" });
          toast("已创建全局角色。");
          setState({ globalCharacterId: created.id });
          reload();
        }}>新建全局角色</button>
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
    </>
  );
}

function CharacterDetail({ ch, onBack, onSaved }: {
  ch: GlobalCharacter; onBack: () => void; onSaved: () => void;
}) {
  const [draft, setDraft] = useState(ch);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [studioAssets, setStudioAssets] = useState<CharacterAsset[]>([]);
  const [versions, setVersions] = useState<CharacterVersion[]>([]);
  const [prompt, setPrompt] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [busy, setBusy] = useState("");
  const [confirmViews, setConfirmViews] = useState<string | null>(null);
  const [outfitName, setOutfitName] = useState("");
  const [outfits, setOutfits] = useState<any[]>([]);
  useEffect(() => setDraft(ch), [ch.id, ch.version]);
  const loadAssets = () =>
    api.listCharacterAssets(ch.id).then((r) => setAssets(r.items)).catch(() => {});
  const loadStudio = () => {
    void api.listCharacterStudioAssets(ch.id).then((r) => setStudioAssets(r.items)).catch(() => {});
    void api.characterVersions(ch.id).then((r) => setVersions(r.items)).catch(() => {});
    void api.listCharacterOutfits(ch.id).then((r) => setOutfits(r.items)).catch(() => {});
  };
  useEffect(() => { void loadAssets(); loadStudio(); }, [ch.id, ch.version]);

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
          <p className="muted">全局角色 · v{ch.version}</p>
        </div>
        <span className="avatar large">{ch.name.slice(0, 1)}</span>
      </div>
      <section className="focus-section">
        <h3>Outfit 管理</h3>
        <div className="row">
          <input value={outfitName} onChange={(e) => setOutfitName(e.target.value)} placeholder="造型名称，例如：黄色雨衣" />
          <button disabled={!outfitName || !!busy} onClick={() => run("Outfit 已创建", async () => {
            await api.createCharacterOutfit(ch.id, outfitName); setOutfitName("");
            const next = await api.listCharacterOutfits(ch.id); setOutfits(next.items);
          })}>添加 Outfit</button>
        </div>
        <div className="pillrow">{outfits.map((o) => <span className="soft-tag" key={o.id}>{o.name}</span>)}</div>
      </section>
      <section className="focus-section">
        <h3>Character Studio</h3>
        <p className="muted">AI 生图和编辑都生成新的 Candidate，不会覆盖原始资产。选定主图后再确认生成标准视图。</p>
        <div className="two">
          <label><span>AI 创建 / 外观补充</span>
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)}
              placeholder="例如：深色雨衣、短发、疲惫但警觉" /></label>
          <div className="row" style={{ alignItems: "end" }}>
            <button className="primary" disabled={!!busy}
              onClick={() => run("已生成 2 张 Candidate", () => api.aiGenerateCharacter(ch.id, prompt, 2))}>
              {busy === "已生成 2 张 Candidate" ? "生成中…" : "AI 生成 2 张 Candidate"}
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
            <div className="row"><b className="grow">{a.role}</b><span className="status-pill">{a.status}</span></div>
            <div className="row">
              {a.status === "CANDIDATE" && <button className="small" onClick={() => run("Candidate 已批准", () => api.setCharacterAssetStatus(a.id, "APPROVED"))}>批准</button>}
              {(a.status === "APPROVED" || a.status === "CANDIDATE") && <button className="small" onClick={() => run("已设为 Canonical", () => api.approveCharacterAsset(ch.id, a.id))}>设为主资产</button>}
            </div>
          </article>)}
        </div>
        {confirmViews && <div className="notice">
          <b>二次确认：生成 four-view 标准参考组？</b>
          <div className="row">
            <button className="primary" onClick={() => run("标准视图已生成", async () => {
              await api.standardCharacterViews(ch.id, confirmViews); setConfirmViews(null);
            })}>确认生成</button>
            <button onClick={() => setConfirmViews(null)}>取消</button>
          </div>
        </div>}
        <div className="two">
          <label><span>非破坏式编辑（换装 / 背景 / 姿势 / 视角 / 自由文本）</span>
            <textarea value={editInstruction} onChange={(e) => setEditInstruction(e.target.value)}
              placeholder="例如：保持身份不变，换成黄色雨衣，背景改为楼梯间" /></label>
          <div className="row" style={{ alignItems: "end" }}>
            <button disabled={!!busy || !editInstruction || !studioAssets.length}
              onClick={() => run("编辑 Candidate 已生成", () => api.editCharacterImage(ch.id, studioAssets[0].id, editInstruction))}>生成编辑 Candidate</button>
          </div>
        </div>
      </section>
      <section className="focus-section">
        <h3>Character Version / Diff</h3>
        {versions.length === 0 ? <p className="muted">保存元数据或 Canonical 资产后会形成版本。</p> : <table className="dev"><thead><tr><th>版本</th><th>变更</th><th>时间</th></tr></thead><tbody>
          {versions.map((v) => <tr key={v.id}><td>v{v.version}</td><td>{v.change_type}</td><td>{new Date(v.created_at).toLocaleString()}</td></tr>)}
        </tbody></table>}
        <p className="muted">Scenario Snapshot、Local Override、Promote 与 Production Reference Resolver 已由 API 提供，发布/开发者页面可继续查看。</p>
      </section>
      <section className="focus-section">
        <h3>角色基础信息</h3>
        <div className="two">
          <label><span>名字</span>
            <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></label>
          <label><span>标签（用逗号分隔）</span>
            <input value={(draft.tags || []).join("，")}
              onChange={(e) => setDraft({
                ...draft,
                tags: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
              })} /></label>
        </div>
        <label><span>简介</span>
          <textarea value={draft.bio} onChange={(e) => setDraft({ ...draft, bio: e.target.value })} /></label>
        <label><span>基础人格</span>
          <textarea value={draft.personality}
            onChange={(e) => setDraft({ ...draft, personality: e.target.value })} /></label>
        <div className="row">
          <button className="primary" onClick={save}>保存为新版本</button>
          <span className="muted">保存会创建新版本；已有故事仍继续使用各自的角色快照。</span>
        </div>
      </section>
      <section className="focus-section">
        <h3>视觉身份</h3>
        <RefSlotGrid ch={ch} assets={assets} onPick={bindRef} onUpload={uploadRef}
          slots={[
            { key: "ref_front_asset", title: "正面图", accept: "image" },
            { key: "ref_side_asset", title: "侧面图", accept: "image" },
            { key: "ref_back_asset", title: "背面图", accept: "image" },
          ]} />
        <RefSlotGrid ch={ch} assets={assets} onPick={bindRef} onUpload={uploadRef} multi
          slots={[{ key: "ref_other_assets", title: "其他参考图片", accept: "image" }]} />
        <p className="muted">形象参考绑定后随角色快照固定；上传的素材保存在角色全局素材池。</p>
      </section>
      <section className="focus-section">
        <h3>声音 / 动作身份</h3>
        <RefSlotGrid ch={ch} assets={assets} onPick={bindRef} onUpload={uploadRef}
          slots={[
            { key: "ref_voice_asset", title: "主声音参考", accept: "voice" },
            { key: "ref_motion_asset", title: "动作参考（视频）", accept: "video" },
          ]} />
      </section>
    </>
  );
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
                    {a?.name || aid}</span>
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
