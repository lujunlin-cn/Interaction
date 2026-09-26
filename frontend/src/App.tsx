/** App 外壳：左侧 Sidebar + 主工作区 +（Player 页）Inspector 抽屉。 */
import React, { useEffect } from "react";
import { setState, useUi } from "./store";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import Creator from "./pages/Creator";
import CharacterLibrary from "./pages/CharacterLibrary";
import Assets from "./pages/Assets";
import Player from "./pages/Player";
import Developer from "./pages/Developer";
import Settings from "./pages/Settings";
import Feedback from "./pages/Feedback";
import Notes from "./pages/Notes";

const TITLES: Record<string, string> = {
  home: "故事库",
  player: "当前游玩",
  characterLibrary: "角色库",
  assets: "素材",
  settings: "设置",
  feedback: "体验反馈",
  notes: "原型说明",
};

export default function App() {
  const ui = useUi();
  const isPlayer = ui.page === "player";

  // G13：全局显示设置 → body data-* 属性（CSS 变量档位生效）
  useEffect(() => {
    const b = document.body;
    b.dataset.appearance = ui.display.appearance;
    b.dataset.density = ui.display.density;
    b.dataset.fontsize = ui.display.fontSize;
    b.dataset.uisize = ui.display.uiSize;
    b.dataset.subtitleSize = ui.display.subtitleSize;
    b.dataset.subtitlePos = ui.display.subtitlePos;
  }, [ui.display]);
  const inspector = false;

  let content: React.ReactNode;
  switch (ui.page) {
    case "home": content = <Home />; break;
    case "creator": content = <Creator />; break;
    case "characterLibrary": content = <CharacterLibrary />; break;
    case "assets": content = <Assets />; break;
    case "player": content = <Player />; break;
    case "developer": content = ui.mode === "developer" ? <Developer /> : <Settings />; break;
    case "settings": content = <Settings />; break;
    case "feedback": content = <Feedback />; break;
    case "notes": content = ui.mode === "developer" ? <Notes /> : <Home />; break;
    default: content = <Home />;
  }

  return (
    <div className={`appframe${ui.theaterMode ? " theater-mode" : ""}`} data-theater-mode={ui.theaterMode ? "true" : "false"}>
      {!ui.theaterMode && <Sidebar />}
      <main className={`workspace-main${isPlayer ? " player-mode" : ""}`}>
        {isPlayer ? content : (
          <>
            <div className="topbar">
              <h1>{ui.page === "creator" ? creatorTitle(ui.creatorTab) :
                ui.page === "developer" ? devTitle(ui.devTab) : TITLES[ui.page] ?? "互动短剧"}</h1>
              <span className="muted">{ui.mode === "developer" ? "开发者模式" : ui.mode === "creator" ? "创作模式" : "玩家模式"}</span>
            </div>
            <div className={`workspace-inner ${ui.page === "developer" ? "wide" : ui.page === "home" ? "library" : ""}`}>
              {content}
            </div>
          </>
        )}
      </main>
      {inspector && <aside className="inspector-drawer"><InspectorDrawer /></aside>}
      {ui.toast && <div className="toast">{ui.toast}</div>}
    </div>
  );
}

function creatorTitle(tab: string): string {
  return ({
    overview: "概览", world: "世界", characters: "角色", drama: "戏剧结构",
    mechanics: "玩法机制", theme: "故事视觉设定", publish: "发布", changes: "变更记录",
  } as Record<string, string>)[tab] ?? "创作";
}

function devTitle(tab: string): string {
  return ({
    skills: "系统 Skills", branches: "分支预测", world: "世界状态", drama: "戏剧控制",
    cache: "分支缓存", router: "模型路由", runtime: "运行环境", production: "视频生成",
    assembly: "视频装配", trace: "Trace", metrics: "Metrics", qa: "QA",
  } as Record<string, string>)[tab] ?? "开发者";
}

/** Player 页内嵌的精简 Inspector（完整版在 Developer 页）。 */
function InspectorDrawer() {
  const ui = useUi();
  return (
    <>
      <div className="row">
        <h3 className="grow">Inspector</h3>
        <button className="small" onClick={() => setState({ inspectorOpen: false })}>收起</button>
        <button className="small" onClick={() => setState({ page: "developer", devTab: "branches" })}>
          打开完整开发者视图
        </button>
      </div>
      <p className="muted">
        当前会话：<span className="mono">{ui.sessionId ?? "无"}</span>
      </p>
      <p className="muted">技术状态（PROVISIONAL / CANONICAL / 指纹等）只在开发者视图展示。</p>
    </>
  );
}
