/** 素材管理：上传 / 绑定 / 版本与授权状态。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";
import type { Asset } from "../types";

const TYPE_LABELS: Record<string, string> = { image: "图片", voice: "声音", video: "视频" };

export default function Assets() {
  const ui = useUi();
  const [items, setItems] = useState<Asset[]>([]);
  const [filter, setFilter] = useState("all");
  const [binding, setBinding] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const sid = ui.editId;
  const reload = () => {
    if (sid) api.listAssets(sid).then((r) => setItems(r.items)).catch(() => {});
  };
  useEffect(reload, [sid]);

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
          <input placeholder="绑定对象（如 alice / foyer / style）" value={binding}
            onChange={(e) => setBinding(e.target.value)} style={{ width: 220 }} />
          <button className="primary" onClick={() => fileRef.current?.click()}>上传素材</button>
          <input ref={fileRef} type="file" hidden accept="image/*,audio/*,video/*"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                await api.uploadAsset(sid, file, { entity: binding, binding });
                toast("已上传。");
                reload();
              } catch (err: any) {
                toast(`上传失败：${err.message}`);
              }
              e.target.value = "";
            }} />
        </div>
        <p className="muted">
          素材变更会让依赖它的候选分支失效（fingerprint miss）；正在播放或已推荐的内容不会中途被替换。
        </p>
      </div>
      {shown.length === 0 ? <div className="empty">还没有素材。</div> : (
        <table className="dev">
          <thead><tr><th>名称</th><th>类型</th><th>大小</th><th>绑定</th><th>版本</th><th>预览</th></tr></thead>
          <tbody>
            {shown.map((a) => (
              <tr key={a.id}>
                <td>{a.name}</td>
                <td>{TYPE_LABELS[a.type] ?? a.type}</td>
                <td>{(a.size / 1024).toFixed(0)} KB</td>
                <td>{a.entity || a.binding || "—"}</td>
                <td>v{a.version}</td>
                <td>
                  {a.type === "image" && (
                    <img src={`/files/${a.storage_path}`} alt={a.name}
                      style={{ maxWidth: 120, maxHeight: 68, borderRadius: 4 }} />
                  )}
                  {a.type === "voice" && <audio controls src={`/files/${a.storage_path}`} style={{ height: 28 }} />}
                  {a.type === "video" && <video controls src={`/files/${a.storage_path}`} style={{ maxWidth: 140 }} />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
