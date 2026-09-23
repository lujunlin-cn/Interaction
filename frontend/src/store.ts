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
  | "production" | "assembly" | "trace" | "metrics" | "qa";

export interface UiState {
  page: Page;
  creatorTab: CreatorTab;
  devTab: DevTab;
  mode: "standard" | "developer";
  editId: string | null;            // 正在编辑的 Scenario
  sessionId: string | null;         // 当前游玩 Session
  scenarioVersionId: string | null;
  characterId: string | null;       // 创作者 tab 里选中的故事角色
  globalCharacterId: string | null; // 角色库里打开的全局角色
  inspectorOpen: boolean;
  toast: string | null;
  playerView: PlayerView | null;    // WS 推送的最新玩家视图
}

const initial: UiState = {
  page: "home",
  creatorTab: "overview",
  devTab: "branches",
  mode: (localStorage.getItem("drama.mode") as "developer") || "standard",
  editId: localStorage.getItem("drama.editId"),
  sessionId: localStorage.getItem("drama.sessionId"),
  scenarioVersionId: null,
  characterId: null,
  globalCharacterId: null,
  inspectorOpen: false,
  toast: null,
  playerView: null,
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
  listeners.forEach((l) => l());
}

export function toast(msg: string) {
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
