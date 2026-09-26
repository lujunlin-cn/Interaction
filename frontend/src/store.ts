/** 全局应用状态：页面导航、当前编辑的 Scenario、当前 Session、模式。 */
import { useSyncExternalStore } from "react";
import type { PlayerView } from "./types";

export type Page =
  | "home" | "player" | "characterLibrary" | "creator" | "assets"
  | "developer" | "settings" | "feedback" | "notes";

export type CreatorTab =
  | "overview" | "world" | "characters" | "drama" | "mechanics" | "theme" | "publish" | "changes";

export type DevTab =
  | "skills" | "branches" | "world" | "drama" | "cache" | "router" | "runtime"
  | "production" | "assembly" | "trace" | "metrics" | "qa" | "prototype";

/** G13：全局显示设置（持久化 localStorage，CSS 变量档位生效） */
export interface DisplayPrefs {
  appearance: "system" | "light" | "dark";
  density: "comfortable" | "compact" | "roomy";
  fontSize: "small" | "medium" | "large" | "xlarge";
  uiSize: "standard" | "large" | "xlarge";
  subtitleSize: "standard" | "large" | "xlarge" | "auto" | "small" | "medium";
  subtitlePos: "bottomInside" | "bottomOutside" | "bottom" | "top";
}

export type Mode = "player" | "creator" | "developer";

export interface UiState {
  page: Page;
  creatorTab: CreatorTab;
  devTab: DevTab;
  /** 三态：player=普通玩家（默认）；creator=创作模式；developer=开发者。
   * 兼容迁移：旧值 "standard" 读入时按上下文归并为 player。 */
  mode: Mode;
  editId: string | null;            // 正在编辑的 Scenario
  sessionId: string | null;         // 当前游玩 Session
  scenarioVersionId: string | null;
  characterId: string | null;       // 创作者 tab 里选中的角色
  globalCharacterId: string | null; // 角色库里打开的角色
  inspectorOpen: boolean;
  theaterMode: boolean;
  toast: string | null;
  playerView: PlayerView | null;    // WS 推送的最新玩家视图
  display: DisplayPrefs;
}

function loadDisplay(): DisplayPrefs {
  try {
    const raw = localStorage.getItem("drama.display");
    if (raw) {
      const saved = JSON.parse(raw);
      const uiSize = saved.uiSize === "125" || saved.uiSize === "large" ? "large"
        : saved.uiSize === "150" || saved.uiSize === "xlarge" ? "xlarge" : "standard";
      return { appearance: "system", density: "comfortable", fontSize: "medium",
        subtitleSize: "standard", subtitlePos: "bottomInside", ...saved, uiSize };
    }
  } catch { /* ignore */ }
  return { appearance: "system", density: "comfortable", uiSize: "standard", fontSize: "medium",
    subtitleSize: "standard", subtitlePos: "bottomInside" };
}

/** 深链：#/<page>[/<tab>] 直达页面（验收脚本与可分享链接用）。 */
function pageFromHash(): { page: Page; creatorTab: CreatorTab; devTab: DevTab } {
  const seg = location.hash.replace(/^#\/?/, "").split("/");
  const p = seg[0] as Page;
  const pages: Page[] = ["home", "player", "creator", "characterLibrary",
    "assets", "developer", "settings", "feedback", "notes"];
  const ctabs: CreatorTab[] = ["overview", "world", "characters", "drama",
    "mechanics", "theme", "publish", "changes"];
  const dtabs: DevTab[] = ["skills", "branches", "world", "drama", "cache",
    "router", "runtime", "production", "assembly", "trace", "metrics", "qa",
    "prototype"];
  return {
    page: pages.includes(p) ? p : "home",
    creatorTab: ctabs.includes(seg[1] as CreatorTab) ? seg[1] as CreatorTab : "overview",
    devTab: dtabs.includes(seg[1] as DevTab) ? seg[1] as DevTab : "branches",
  };
}

function loadMode(): Mode {
  const raw = localStorage.getItem("drama.mode");
  if (raw === "developer" || raw === "creator") return raw;
  // 旧值 "standard" / 空 / 其他 → 默认玩家态；创作者由显式切换进入。
  return "player";
}

const _init = pageFromHash();
const initial: UiState = {
  page: _init.page,
  creatorTab: _init.creatorTab,
  devTab: _init.devTab,
  mode: loadMode(),
  editId: localStorage.getItem("drama.editId"),
  sessionId: localStorage.getItem("drama.sessionId"),
  scenarioVersionId: null,
  characterId: null,
  globalCharacterId: null,
  inspectorOpen: false,
  theaterMode: false,
  toast: null,
  playerView: null,
  display: loadDisplay(),
};

let state: UiState = { ...initial };
const listeners = new Set<() => void>();

export function getState(): UiState {
  return state;
}

export function setState(patch: Partial<UiState>) {
  state = { ...state, ...patch };
  if (patch.mode) localStorage.setItem("drama.mode", patch.mode);
  if (patch.editId !== undefined) {
    patch.editId ? localStorage.setItem("drama.editId", patch.editId)
      : localStorage.removeItem("drama.editId");
  }
  if (patch.sessionId !== undefined) {
    patch.sessionId ? localStorage.setItem("drama.sessionId", patch.sessionId)
      : localStorage.removeItem("drama.sessionId");
  }
  if (patch.display) localStorage.setItem("drama.display", JSON.stringify(patch.display));
  listeners.forEach((l) => l());
}

/** 合并式更新 display（避免调用方手动展开） */
export function setDisplay(patch: Partial<DisplayPrefs>) {
  setState({ display: { ...state.display, ...patch } });
}

export function toast(msg: string) {
  if (state.mode !== "developer" && /pydantic|traceback|validationerror|exception|provider|request[_ ]?id|branch[_ ]?id|schema|https?:|\bJSON\b|\b502\b|\b500\b/i.test(msg)) msg = "这个操作暂时没有完成，请保留输入后重试。";
  setState({ toast: msg });
  window.setTimeout(() => {
    if (getState().toast === msg) setState({ toast: null });
  }, 3600);
}

export function useUi(): UiState {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}

window.addEventListener("hashchange", () => setState(pageFromHash()));
