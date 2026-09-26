/** 左侧 Sidebar：按 mode 三态裁剪。
 * player   → 只保留故事库 / 继续游玩 / 设置 / 反馈（玩家不看见创作流程）
 * creator  → 完整创作导航 + 角色库
 * developer→ creator 基础上加开发者页签 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { CreatorTab, DevTab, setState, useUi } from "../store";
import type { ScenarioDraft } from "../types";

function NavButton(props: {
  label: string; icon: string; active?: boolean; disabled?: boolean; sub?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`sidebar-item${props.active ? " active" : ""}`}
      style={props.sub ? { paddingLeft: 30 } : undefined}
      disabled={props.disabled}
      onClick={props.onClick}
    >
      <span className="nav-ico">{props.icon}</span>
      <span className="nav-label">{props.label}</span>
    </button>
  );
}

export default function Sidebar() {
  const ui = useUi();
  const dev = ui.mode === "developer";
  const creator = ui.mode === "creator" || dev;
  const [library, setLibrary] = useState<ScenarioDraft[]>([]);
  const [editing, setEditing] = useState<ScenarioDraft | null>(null);

  useEffect(() => {
    api.listScenarios().then((r) => setLibrary(r.items)).catch(() => {});
  }, [ui.page, ui.editId]);
  useEffect(() => {
    if (ui.editId) api.getScenario(ui.editId).then(setEditing).catch(() => setEditing(null));
    else setEditing(null);
  }, [ui.editId]);

  const creatorBtn = (tab: CreatorTab) => (
    <NavButton key={tab} icon={creatorIcons[tab]} label={creatorLabels[tab]}
      active={ui.page === "creator" && ui.creatorTab === tab}
      onClick={() => setState({ page: "creator", creatorTab: tab })} />
  );

  return (
    <aside id="sidebar">
      <div className="sidebar-brand"><span className="sidebar-mark">剧</span><span>互动短剧</span></div>
      {creator ? (
        <button className="sidebar-create" onClick={async () => {
          const draft = await api.createScenario();
          setState({ editId: draft.id, page: "creator", creatorTab: "overview" });
        }}>＋ 创建故事</button>
      ) : (
        <button className="sidebar-create" onClick={() => setState({ page: "home" })}>
          ▶ 开始游玩</button>
      )}

      <div className="sidebar-nav">

      <div className="sidebar-section">
        <div className="sidebar-section-title">场景</div>
        <NavButton icon="⌂" label="故事库" active={ui.page === "home"} onClick={() => setState({ page: "home" })} />
        <NavButton icon="▶" label="继续游玩" active={ui.page === "player"} disabled={!ui.sessionId}
          onClick={() => setState({ page: "player" })} />
        {creator && (
          <NavButton icon="人" label="角色库" active={ui.page === "characterLibrary"}
            onClick={() => setState({ page: "characterLibrary", globalCharacterId: null })} />
        )}
      </div>

      {creator && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">创作</div>
          {creatorBtn("overview")}
          {creatorBtn("world")}
          {creatorBtn("characters")}
          {ui.page === "creator" && ui.creatorTab === "characters" && editing && (
            <div className="sidebar-subitems">
              {editing.characters.map((c) => (
                <NavButton key={c.id} sub icon="·" label={c.identity}
                  active={ui.characterId === c.id}
                  onClick={() => setState({ characterId: c.id })} />
              ))}
            </div>
          )}
          {creatorBtn("drama")}
          {creatorBtn("mechanics")}
          <NavButton icon="▧" label="素材" active={ui.page === "assets"}
            onClick={() => setState({ page: "assets" })} />
          {creatorBtn("publish")}
        </div>
      )}

      {dev && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">开发者</div>
          {devTabs.map(([k, label, icon]) => (
            <NavButton key={k} icon={icon} label={label}
              active={ui.page === "developer" && ui.devTab === k}
              onClick={() => setState({ page: "developer", devTab: k as DevTab })} />
          ))}
        </div>
      )}

      <div className="sidebar-section recent-section">
        <div className="sidebar-section-title">最近项目</div>
        {library.slice(0, 4).map((sc) => (
          <button key={sc.id} className="recent-project"
            onClick={() => setState({ editId: sc.id, page: "creator", creatorTab: "overview" })}>
            <span className="nav-ico">{sc.owner === "official" ? "●" : "○"}</span>
            <span className="nav-label">{sc.title}</span>
          </button>
        ))}
      </div>
      </div>

      <div className="sidebar-spacer" />
      <div className="sidebar-bottom">
        {!creator && (
          <NavButton icon="✎" label="进入创作模式" active={false}
            onClick={() => setState({ mode: "creator", page: "creator", creatorTab: "overview" })} />
        )}
        {ui.mode === "creator" && (
          <NavButton icon="←" label="返回玩家模式" active={false}
            onClick={() => setState({ mode: "player", page: "home" })} />
        )}
        <NavButton icon="⚙" label="设置" active={ui.page === "settings"}
          onClick={() => setState({ page: "settings" })} />
        <div className="mode-label">
          {dev ? "开发者模式" : ui.mode === "creator" ? "创作模式" : "玩家模式"}
        </div>
      </div>
    </aside>
  );
}

const creatorLabels: Record<CreatorTab, string> = {
  overview: "概览", world: "世界", characters: "角色", drama: "戏剧结构",
  mechanics: "玩法机制", theme: "故事视觉设定", publish: "发布", changes: "变更记录",
};
const creatorIcons: Record<CreatorTab, string> = {
  overview: "◫", world: "◎", characters: "人", drama: "◇",
  mechanics: "⚙", theme: "❖", publish: "↑", changes: "≣",
};
const devTabs: Array<[DevTab, string, string]> = [
  ["skills", "系统 Skills", "⌁"],
  ["branches", "分支预测", "⑂"],
  ["world", "世界状态", "▦"],
  ["drama", "戏剧控制", "◇"],
  ["cache", "分支缓存", "▤"],
  ["router", "模型路由", "⇄"],
  ["runtime", "运行环境", "▣"],
  ["production", "视频生成", "◈"],
  ["assembly", "视频装配", "≡"],
  ["trace", "Trace", "⌇"],
  ["metrics", "Metrics", "∿"],
  ["qa", "QA", "✓"],
  ["prototype", "原型夹具", "⚗"],
];
