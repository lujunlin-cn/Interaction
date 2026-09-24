import React, { useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";
import type { ScenarioDraft } from "../types";

export const DRAMA_GROUPS = [
  ["故事真正想问什么？", ["core_question", "central_conflict"]],
  ["背后的真相是什么？", ["truth_model", "secrets", "misbeliefs"]],
  ["什么会推动故事向前？", ["pressures", "anchors"]],
  ["故事可能走向哪里？", ["ending_families"]],
  ["什么绝对不能发生？", ["forbidden_outcomes"]],
] as const;
export const FIELD_LABELS: Record<string, string> = {
  core_question: "故事核心", central_conflict: "主要冲突", truth_model: "背后真相", secrets: "故事秘密",
  misbeliefs: "人物的误解", pressures: "推动故事的压力", anchors: "关键时刻", ending_families: "结局方向",
  forbidden_outcomes: "绝对不能发生", foreshadows: "伏笔", timed_interactions: "紧张时刻",
  identity: "本故事身份", personality: "她的性格", desire: "最想得到", fear: "最害怕",
  knowledge: "已经知道", relationship: "与他人的关系", visual_state: "当前外观",
};
export function readable(value: unknown): string {
  if (value && typeof value === "object") return String((value as any).tutorial || (value as any).title || "已准备玩法建议");
  return String(value ?? "").split("\n").map(l => {
    const cols = l.split("｜");
    if (cols.length >= 4 && /qte|urgent_dialogue/.test(cols[1])) return `${cols[2]} 秒内决定；超时：${cols.slice(3).join("，")}`;
    if (cols.length > 1) return cols.slice(1).filter(c => !/^(行动触发|故事时间推进)$/.test(c)).join("，");
    return l.replace(/^[a-zA-Z_][\w-]*[：:]\s*/, "");
  }).join("\n");
}
export function typedText(path: string, text: string, old: string): string {
  const key = path.split(".").slice(-1)[0];
  const lines = text.split("\n").filter(Boolean);
  const previous = old.split("\n");
  if (key === "truth_model") return lines.map((s, i) => `${previous[i]?.split(/[：:]/)[0] || `fact_${i + 1}`}：${s}`).join("\n");
  if (["ending_families", "foreshadows"].includes(key || "")) return lines.map((s, i) => `${previous[i]?.split("｜")[0] || `entry_${i + 1}`}｜${s}`).join("\n");
  if (key === "pressures") return lines.map((s, i) => `${previous[i]?.split("｜")[0] || `pressure_${i + 1}`}｜${s}｜${previous[i]?.split("｜")[2] || "行动触发"}`).join("\n");
  return text;
}

export default function StoryUnderstanding({ draft, scope = "drama", characterId = "", onDraft }: {
  draft: ScenarioDraft; scope?: "drama" | "character" | "mechanics"; characterId?: string;
  onDraft: (d: ScenarioDraft) => void;
}) {
  const key = `${scope}:${characterId}`;
  const [projection, setProjection] = useState<any>(draft.creator_projection?.[key]);
  const [instruction, setInstruction] = useState(scope === "mechanics" ? draft.mechanic_authoring_intent || "" : "");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [free, setFree] = useState("");
  const developer = useUi().mode === "developer";
  const propose = async () => {
    setBusy(true);
    try { setProjection(await api.creatorUnderstanding(draft.id, scope, instruction, characterId)); }
    catch (e: any) { toast(e.message); } finally { setBusy(false); }
  };
  const accept = async (answers: Record<string, unknown>) => {
    if ((answers["mechanics.qte"] as any)?.enabled) {
      const timed = projection.items.find((i: any) => i.path === "drama.timed_interactions");
      if (timed) answers = { ...answers, "drama.timed_interactions": timed.value };
    }
    setBusy(true);
    try {
      const next = await api.confirmUnderstanding(draft.id, projection.id, answers);
      onDraft(next); setProjection(next.creator_projection?.[key]); toast("已保存你确认的理解。");
    } catch (e: any) { toast(e.message); } finally { setBusy(false); }
  };
  const renderItem = (item: any) => <article key={item.path} className="understanding-item">
          <h4>{FIELD_LABELS[item.path.split(".").slice(-1)[0]] || (scope === "mechanics" ? "玩法建议" : "角色理解")}</h4>
          <p>{readable(item.summary)}</p>
          {projection.accepted.includes(item.path) ? <span className="badge ok">已确认</span> : <>
            {item.question && <p><b>{item.question}</b></p>}
            {item.question && <div className="suggestion-list">{item.suggestions.map((s: any, i: number) =>
              <button key={i} disabled={busy} onClick={() => accept({ [item.path]: s.value })}>{s.label}</button>)}</div>}
            <div className="toolbar"><button disabled={busy} onClick={() => accept({ [item.path]: item.value })}>接受</button>
              <button onClick={() => { setEditing(item.path); setFree(readable(item.value)); }}>{item.question ? "其他 / 自己描述" : "修改"}</button>
              <button disabled={busy} onClick={() => scope === "mechanics" && typeof item.value === "object" ? accept({ [item.path]: { ...item.value, enabled: false } }) : accept({ [item.path]: "" })}>删除这项</button></div>
            {editing === item.path && <div className="inline-editor"><textarea aria-label="自己描述" value={free} onChange={e => setFree(e.target.value)} />
              <button disabled={busy} onClick={() => {
                if (typeof item.value === "object" || item.path.endsWith("timed_interactions")) { setInstruction(free); setEditing(null); toast("已放入补充想法，点击更新理解后确认新建议。"); }
                else void accept({ [item.path]: typedText(item.path, free, item.value) });
              }}>确认修改</button></div>}
          </>}
          {developer && <pre>{JSON.stringify(item, null, 2)}</pre>}
        </article>;
  return <section className="card understanding">
    <h3>{scope === "mechanics" ? "你希望这个故事怎么玩？" : scope === "character" ? "AI 对这个角色在当前故事中的理解" : "AI 当前理解"}</h3>
    <p>{projection?.summary || (scope === "drama" ? draft.description : "结合这个故事提出建议，由你确认后保存。")}</p>
    <label><span>{scope === "mechanics" ? "描述玩法，也可以要求调整已有玩法" : "补充想法（选填）"}</span>
      <textarea aria-label="补充创作想法" value={instruction} onChange={e => setInstruction(e.target.value)}
        placeholder={scope === "mechanics" ? "主要调查和询问角色，人物记得我是否撒谎，追逐时要快速决定，不显示数值。" : "告诉 AI 你想保留或进一步完善的内容…"} /></label>
    <button className="primary" disabled={busy} onClick={propose}>{busy ? "正在整理故事…" : projection ? "更新理解与建议" : "帮我完善"}</button>
    {projection && <>
      <p className="muted">{projection.items.filter((i: any) => i.question && !projection.accepted.includes(i.path)).length ? "有几件重要的事需要你来决定" : "已明确的内容不重复询问，你可以直接接受或继续修改。"}</p>
      <div className="understanding-grid">
        {projection.items.filter((i: any) => developer || (i.question && !projection.accepted.includes(i.path))).map(renderItem)}
      </div>
      {!developer && <details><summary>查看已明确的理解与已确认内容</summary><div className="understanding-grid">{projection.items.filter((i: any) => !i.question || projection.accepted.includes(i.path)).map(renderItem)}</div></details>}
      <button disabled={busy} onClick={() => accept(Object.fromEntries(projection.items.filter((i: any) => !i.question && !projection.accepted.includes(i.path)).map((i: any) => [i.path, i.value])))}>接受已明确的理解</button>
      {developer && <details><summary>Authoring provenance</summary><pre>{JSON.stringify(projection, null, 2)}</pre></details>}
    </>}
  </section>;
}
