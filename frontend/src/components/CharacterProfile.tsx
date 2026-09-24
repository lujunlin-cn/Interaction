import React, { useState } from "react";
import { useUi } from "../store";

export const CHARACTER_SECTIONS: Array<[string, Array<[string, string]>]> = [
  ["身份", [["identity", "名字与身份"], ["bio", "一句话角色定义"]]],
  ["人格与动机", [["personality", "基础人格"], ["desire", "最想得到什么"], ["fear", "最害怕什么"]]],
  ["认知与秘密", [["knowledge", "已经知道什么"], ["secrets", "藏着什么秘密"]]],
  ["关系", [["relationship", "与他人的关系"]]],
  ["外观与造型", [["visual_state", "外观与当前造型"]]],
  ["声音与动作", []], ["使用与版本", []],
];
export default function CharacterProfile({ scope, values, inherited = {}, onChange, onPromote, extras = {} }: {
  scope: "global" | "scenario"; values: Record<string, any>; inherited?: Record<string, any>;
  onChange: (patch: Record<string, string>) => void; onPromote?: () => void;
  extras?: Record<string, React.ReactNode>;
}) {
  const dev = useUi().mode === "developer";
  const [editing, setEditing] = useState<string | null>(null);
  const [text, setText] = useState("");
  return <div className="character-profile">
    <p className="scope-note">{scope === "global" ? "全局角色 · 这个人长期是谁" : "仅本故事 · 这个人在当前故事中的状态"}</p>
    {CHARACTER_SECTIONS.map(([title, fields]) => <section key={title} className="card">
      <h3>{title}</h3>
      {fields.filter(([key]) => scope === "global" || key !== "bio").map(([key, label]) => {
        const value = values[key] ?? inherited[key] ?? "";
        const fromGlobal = scope === "scenario" && inherited[key] && value === inherited[key];
        return <div className="character-understanding" key={key}>
          <div className="row"><b className="grow">{label}</b><span className="soft-tag">{scope === "global" ? "全局默认" : fromGlobal ? "继承全局" : "仅本故事"}</span></div>
          {value ? <p>{value}</p> : <p className="muted">{key === "identity" || (key === "bio" && scope === "global") ? "请补充这项基本信息" : "选填 · 可让 AI 提出建议，或留待故事中发展"}</p>}
          {editing === key ? <div><textarea aria-label={label} value={text} onChange={e => setText(e.target.value)} />
            <button onClick={() => { onChange({ [key]: text }); setEditing(null); }}>保存</button><button onClick={() => setEditing(null)}>取消</button></div>
            : <div className="toolbar"><button className="small" onClick={() => { setEditing(key); setText(value); }}>{value ? "修改" : "补充"}</button>
              {value && !["identity", "bio"].includes(key) && <button className="small" onClick={() => onChange({ [key]: "" })}>删除</button>}
              {scope === "scenario" && inherited[key] && !fromGlobal && <button className="small" onClick={() => onChange({ [key]: inherited[key] })}>继承全局</button>}</div>}
          {dev && <small className="mono">{key}</small>}
        </div>;
      })}
      {extras[title] || (fields.length === 0 && <p className="muted">{scope === "scenario" ? "沿用所绑定角色的声音、动作和版本；可在角色库查看。" : "可在下方角色工作台管理参考素材与历史版本。"}</p>)}
    </section>)}
    {onPromote && <button onClick={onPromote}>保存为全局新版本</button>}
  </div>;
}
