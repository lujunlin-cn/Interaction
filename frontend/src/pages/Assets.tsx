/** 素材管理：上传 / 绑定 / 版本与授权状态（G20：role/authorized/canonical/trim/用途标记）。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";
import type { Asset } from "../types";

const TYPE_LABELS: Record<string, string> = { image: "图片", voice: "声音", video: "视频" };
const ROLE_OPTIONS: Array<[string, string]> = [
  ["identity", "身份参考"], ["wardrobe", "服装造型"], ["location", "地点场景"],
  ["style", "风格基调"], ["voice", "声音参考"], ["motion", "动作参考"], ["camera", "镜头参考"],
];

export default function Assets() {
  const ui = useUi();
  const [bindings, setBindings] = useState<Array<{id: string; label: string}>>([]);
  const [items, setItems] = useState<Asset[]>([]);
  const [filter, setFilter] = useState("all");
  const [binding, setBinding] = useState("");
  const [role, setRole] = useState("identity");
  const fileRef = useRef<HTMLInputElement>(null);

  const sid = ui.editId;
  const reload = () => {
    if (sid) api.listAssets(sid).then((r) => setItems(r.items)).catch(() => {});
  };
  useEffect(reload, [sid]);
  useEffect(() => { if (sid) api.getScenario(sid).then(d => setBindings([
    ...d.characters.map(c => ({ id: c.id, label: c.identity })),
    ...d.world.locations.split("\n").filter(Boolean).map(l => { const [id, label] = l.split("｜"); return { id, label: label || "故事地点" }; }),
  ])).catch(() => {}); }, [sid]);

  if (!sid) return <div className="empty">请先在「创作 → 概览」选择一个故事。</div>;

  const shown = items.filter((a) => filter === "all" || a.type === filter);
  return (
    <>
      <div className="card">
        <div className="row">
          <h3 className="grow">素材（{items.length}）</h3>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">全部类型</option>
            <option value="image">图片</option>
            <option value="voice">声音</option>
            <option value="video">视频</option>
          </select>
          {ui.mode === "developer" ? <input placeholder="绑定对象 ID" value={binding} onChange={e => setBinding(e.target.value)} />
            : <select aria-label="素材用于" value={binding} onChange={e => setBinding(e.target.value)}><option value="">选择人物或地点…</option>{bindings.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}</select>}
          <select value={role} onChange={(e) => setRole(e.target.value)} title="参考用途">
            {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <button className="primary" onClick={() => fileRef.current?.click()}>上传素材</button>
          <input ref={fileRef} type="file" hidden accept="image/*,audio/*,video/*"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                await api.uploadAsset(sid, file, { entity: binding, binding, role });
                toast("已上传。");
                reload();
              } catch (err: any) {
                toast(`上传失败：${err.message}`);
              }
              e.target.value = "";
            }} />
        </div>
        <p className="muted">
          为素材选择用途，并绑定到人物或地点。确认授权后，可以将它用于故事画面、声音或动作。
        </p>
      </div>
      {shown.length === 0 ? <div className="empty">还没有素材。</div> : (
        <table className="dev">
          <thead><tr>
            <th>名称</th><th>类型</th><th>用途</th><th>绑定</th><th>标记</th>
            <th>时长/裁剪</th><th>版本</th><th>预览</th><th>操作</th>
          </tr></thead>
          <tbody>
            {shown.map((a) => (
              <AssetRow key={a.id} a={a} sid={sid} onChanged={reload} bindings={bindings} />
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

/** 单个素材行：预览 / 元数据行内编辑 / 替换（版本+1）/ 删除 */
function AssetRow({ a, sid, onChanged, bindings }: { a: Asset; sid: string; onChanged: () => void; bindings: Array<{id:string;label:string}> }) {
  const developer = useUi().mode === "developer";
  const replaceRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Asset>>({});

  const saveMeta = async () => {
    try {
      await api.patchAsset(sid, a.id, form);
      toast("素材元数据已更新。");
      setEditing(false);
      onChanged();
    } catch (err: any) {
      toast(`保存失败：${err.message}`);
    }
  };

  return (
    <>
      <tr>
        <td>{a.name}</td>
        <td>{TYPE_LABELS[a.type] ?? a.type}<div className="muted">{(a.size / 1024).toFixed(0)} KB</div></td>
        <td>{ROLE_OPTIONS.find(([v]) => v === a.role)?.[1] ?? (a.role || "—")}</td>
        <td>{developer ? a.entity || a.binding || "—" : bindings.find(b => b.id === (a.entity || a.binding))?.label || "通用素材"}</td>
        <td>
          {a.canonical && <span className="badge ok">{developer ? "canonical" : "标准参考"}</span>}{" "}
          {a.authorized ? <span className="badge ok">已授权</span> : <span className="badge warn">未授权</span>}
          {a.source && <div className="muted">{a.source}</div>}
        </td>
        <td>
          {a.duration != null && <div>{a.duration.toFixed(1)}s</div>}
          {a.type === "video" && (a.trim_start > 0 || a.trim_end > 0) &&
            <div className="muted">裁 {a.trim_start.toFixed(1)}–{a.trim_end.toFixed(1)}s</div>}
        </td>
        <td>v{a.version}</td>
        <td>
          {a.type === "image" && (
            <img src={`/files/${a.storage_path}`} alt={a.name}
              style={{ maxWidth: 120, maxHeight: 68, borderRadius: 4 }} />
          )}
          {a.type === "voice" && <audio controls src={`/files/${a.storage_path}`} style={{ height: 28 }} />}
          {a.type === "video" && <video controls src={`/files/${a.storage_path}`} style={{ maxWidth: 140 }} />}
        </td>
        <td>
          <div className="toolbar" style={{ marginTop: 0 }}>
            <button className="small" onClick={() => { setForm({}); setEditing(!editing); }}>编辑</button>
            <button className="small" onClick={() => replaceRef.current?.click()}>替换</button>
            <input ref={replaceRef} type="file" hidden accept="image/*,audio/*,video/*"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                try {
                  await api.replaceAsset(sid, a.id, file);
                  toast(`已替换，版本升级到 v${a.version + 1}。`);
                  onChanged();
                } catch (err: any) {
                  toast(`替换失败：${err.message}`);
                }
                e.target.value = "";
              }} />
            <button className="small danger" onClick={async () => {
              if (!window.confirm(`确定删除素材「${a.name}」？`)) return;
              try {
                await api.removeAsset(sid, a.id);
                toast("已删除素材。");
                onChanged();
              } catch (err: any) {
                toast(`删除失败：${err.message}`);
              }
            }}>删除</button>
          </div>
        </td>
      </tr>
      {editing && (
        <tr>
          <td colSpan={9} style={{ background: "var(--bg-soft, rgba(128,128,128,.06))" }}>
            <div className="row" style={{ flexWrap: "wrap", gap: 10 }}>
              <label><span>{developer ? "用途 role" : "参考用途"}</span>
                <select value={form.role ?? a.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  {ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select></label>
              {developer ? <><label><span>entity</span><input value={form.entity ?? a.entity} onChange={e => setForm({ ...form, entity: e.target.value })} /></label>
                <label><span>binding</span><input value={form.binding ?? a.binding} onChange={e => setForm({ ...form, binding: e.target.value })} /></label></>
                : <label><span>人物或地点</span><select value={form.entity ?? a.entity ?? ""} onChange={e => setForm({ ...form, entity: e.target.value, binding: e.target.value })}>
                  <option value="">通用素材</option>{bindings.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
                </select></label>}
              <label><span>来源说明</span>
                <input style={{ width: 140 }} value={form.source ?? a.source ?? ""}
                  onChange={(e) => setForm({ ...form, source: e.target.value })} /></label>
              {a.type === "video" && (<>
                <label><span>裁剪起 (s)</span>
                  <input type="number" step="0.1" style={{ width: 80 }}
                    value={form.trim_start ?? a.trim_start}
                    onChange={(e) => setForm({ ...form, trim_start: Number(e.target.value) })} /></label>
                <label><span>裁剪止 (s)</span>
                  <input type="number" step="0.1" style={{ width: 80 }}
                    value={form.trim_end ?? a.trim_end}
                    onChange={(e) => setForm({ ...form, trim_end: Number(e.target.value) })} /></label>
              </>)}
              <label style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <input type="checkbox" style={{ width: "auto" }}
                  checked={form.canonical ?? a.canonical}
                  onChange={(e) => setForm({ ...form, canonical: e.target.checked })} />
                {developer ? "canonical" : "作为标准参考"}</label>
              <label style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <input type="checkbox" style={{ width: "auto" }}
                  checked={form.authorized ?? a.authorized}
                  onChange={(e) => setForm({ ...form, authorized: e.target.checked })} />
                已授权</label>
              <button className="primary small" onClick={saveMeta}>保存</button>
              <button className="small" onClick={() => setEditing(false)}>取消</button>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
