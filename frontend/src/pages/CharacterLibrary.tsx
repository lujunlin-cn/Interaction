/** 全局角色库：跨故事共享的稳定角色身份资产；故事使用快照，不被后续修改覆盖。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import type { GlobalCharacter } from "../types";

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
  useEffect(() => setDraft(ch), [ch.id, ch.version]);

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
        <div className="identity-grid">
          <RefList title="正面图" value={draft.ref_front_asset} />
          <RefList title="侧面图" value={draft.ref_side_asset} />
          <RefList title="背面图" value={draft.ref_back_asset} />
          <RefList title="其他参考图片" value={(draft.ref_other_assets || []).join("、")} />
        </div>
        <p className="muted">在「素材」页上传图片后，可在故事角色中引用；形象参考的版本随角色快照固定。</p>
      </section>
      <section className="focus-section">
        <h3>声音身份</h3>
        <div className="identity-grid">
          <RefList title="主声音参考" value={draft.ref_voice_asset} />
          <RefList title="动作参考（视频）" value={draft.ref_motion_asset} />
        </div>
      </section>
    </>
  );
}

function RefList({ title, value }: { title: string; value?: string | null }) {
  return (
    <div className="identity-panel">
      <div className="row"><h4 className="grow">{title}</h4></div>
      {value ? <div className="ref-chip">{value}</div> : <div className="muted">尚未添加</div>}
    </div>
  );
}
