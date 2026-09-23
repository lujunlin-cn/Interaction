/** 故事库：选择世界 / 创建 / 导入。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import type { ScenarioDraft } from "../types";

const MECHANIC_LABELS: Record<string, string> = {
  relationship: "关系变化", "clue-system": "线索调查", inventory: "道具系统", qte: "限时互动",
};

export default function Home() {
  const ui = useUi();
  const [items, setItems] = useState<ScenarioDraft[]>([]);
  const [versions, setVersions] = useState<Record<string, string>>({});
  const [importing, setImporting] = useState(false);
  const [importText, setImportText] = useState("");

  const reload = () => {
    api.listScenarios().then(async (r) => {
      setItems(r.items);
      const map: Record<string, string> = {};
      for (const sc of r.items) {
        try {
          const v = await api.scenarioVersions(sc.id);
          if (v.items.length) map[sc.id] = v.items[0].version_id;
        } catch { /* ignore */ }
      }
      setVersions(map);
    }).catch((e) => toast(`加载故事库失败：${e.message}`));
  };
  useEffect(reload, []);

  const startPlay = async (sc: ScenarioDraft) => {
    const versionId = versions[sc.id];
    if (!versionId) {
      toast("请先完成发布，试玩会使用最近一次发布的故事版本。");
      setState({ editId: sc.id, page: "creator", creatorTab: "publish" });
      return;
    }
    try {
      const { session_id } = await api.createSession(versionId);
      setState({ sessionId: session_id, scenarioVersionId: versionId, page: "player" });
    } catch (e: any) {
      toast(`开始游玩失败：${e.message}`);
    }
  };

  return (
    <>
      <div className="home-intro">
        <h1>选择一个世界，或亲手创建</h1>
        <p className="muted">预设故事只是起点，你仍然可以在游玩中做出计划外的行动。</p>
        <div className="toolbar">
          <button className="primary" onClick={async () => {
            const draft = await api.createScenario();
            setState({ editId: draft.id, page: "creator", creatorTab: "overview" });
          }}>创建故事</button>
          <button onClick={() => setImporting(true)}>导入故事</button>
          {ui.sessionId && (
            <button onClick={() => setState({ page: "player" })}>继续当前游玩</button>
          )}
        </div>
      </div>
      <h2>故事库</h2>
      <div className="grid">
        {items.map((sc) => (
          <article key={sc.id} className="card story-library-card">
            <div className="row">
              <h3 className="grow">{sc.title}</h3>
              <span className={`badge ${sc.status === "PUBLISHED" ? "ok" : ""}`}>
                {sc.status === "PUBLISHED" ? "已发布" : sc.status === "DRAFT" ? "草稿" : sc.status}
              </span>
            </div>
            <p>{sc.description || "尚未填写故事简介"}</p>
            <div className="pillrow">
              <span className="badge">{sc.owner === "official" ? "官方故事" : "我的故事"}</span>
              {sc.genre && <span className="badge">{sc.genre}</span>}
            </div>
            <p className="muted">
              玩法：{Object.entries(sc.mechanics).filter(([, v]) => v.enabled)
                .map(([k]) => MECHANIC_LABELS[k] ?? k).join(" · ") || "剧情互动"}
              <br />版本：v{sc.version}
            </p>
            <div className="toolbar">
              <button className="primary" disabled={!versions[sc.id] && sc.status !== "PUBLISHED"}
                onClick={() => startPlay(sc)}>开始游玩</button>
              <button onClick={() => setState({ editId: sc.id, page: "creator", creatorTab: "overview" })}>
                编辑
              </button>
            </div>
          </article>
        ))}
      </div>
      {importing && (
        <div className="modal-mask" onClick={() => setImporting(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>导入故事</h3>
            <p className="muted">粘贴 Scenario JSON。导入不会执行任何包内代码；发布前仍需校验和审阅。</p>
            <textarea value={importText} onChange={(e) => setImportText(e.target.value)}
              placeholder='{"title": "...", "world": {...}, "drama": {...}, "characters": [...], "mechanics": {...}}' />
            <div className="toolbar">
              <button onClick={() => setImporting(false)}>取消</button>
              <button className="primary" onClick={async () => {
                try {
                  const data = JSON.parse(importText);
                  validateImport(data);
                  const draft = await api.createScenario();
                  await api.saveScenario({ ...draft, ...data, id: draft.id, status: "DRAFT" });
                  setImporting(false);
                  toast("已导入草案。");
                  setState({ editId: draft.id, page: "creator", creatorTab: "publish" });
                  reload();
                } catch (e: any) {
                  toast(`导入失败：${e.message}`);
                }
              }}>导入</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function validateImport(data: any) {
  const scan = (v: any, path = "root") => {
    if (v && typeof v === "object") {
      for (const [k, x] of Object.entries(v)) {
        if (["__proto__", "constructor", "prototype", "scripts", "executable", "shell"].includes(k)) {
          throw new Error(`不允许可执行字段或危险键：${k}`);
        }
        if ((k.endsWith("path") || k.endsWith("_ref")) && typeof x === "string"
          && /(\.\.\/|^\/|^[A-Za-z]:)/.test(x)) {
          throw new Error("不允许路径穿越或绝对路径");
        }
        scan(x, `${path}.${k}`);
      }
    }
  };
  scan(data);
  const sc = data.scenario || data;
  if (!sc.title || !sc.world || !sc.drama || !Array.isArray(sc.characters)) {
    throw new Error("缺少 Scenario 必需的 typed fields");
  }
}
