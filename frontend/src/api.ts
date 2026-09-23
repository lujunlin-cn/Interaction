/** API 客户端：前端只与后端 REST/WS 通信，绝不直连模型 Provider。 */
import type {
  Asset, DevState, GlobalCharacter, PlayerView, ProviderHealth, ScenarioDraft,
  ScenarioVersion, SkillsRegistry,
} from "./types";

const BASE = "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + path, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = `${resp.status}`;
    try {
      detail = (await resp.json()).detail ?? detail;
    } catch { /* ignore */ }
    throw new Error(String(detail));
  }
  return resp.json();
}

export const api = {
  health: () => req<{ ok: boolean; provider_mode: string; profile: string }>("/api/health"),

  listScenarios: () => req<{ items: ScenarioDraft[] }>("/api/scenarios"),
  getScenario: (id: string) => req<ScenarioDraft>(`/api/scenarios/${id}`),
  createScenario: (idea?: string) =>
    req<ScenarioDraft>("/api/scenarios", { method: "POST", body: JSON.stringify({ idea: idea ?? "" }) }),
  saveScenario: (draft: ScenarioDraft) =>
    req<ScenarioDraft>(`/api/scenarios/${draft.id}`, { method: "PUT", body: JSON.stringify(draft) }),
  instructScenario: (id: string, instruction: string) =>
    req<ScenarioDraft>(`/api/scenarios/${id}/instruct`, { method: "POST", body: JSON.stringify({ instruction }) }),
  publishScenario: (id: string) =>
    req<{ version_id: string; version: string }>(`/api/scenarios/${id}/publish`, { method: "POST" }),
  scenarioVersions: (id: string) => req<{ items: ScenarioVersion[] }>(`/api/scenarios/${id}/versions`),

  listCharacters: (q = "") => req<{ items: GlobalCharacter[] }>(`/api/characters?q=${encodeURIComponent(q)}`),
  createCharacter: (data: Partial<GlobalCharacter>) =>
    req<GlobalCharacter>("/api/characters", { method: "POST", body: JSON.stringify(data) }),
  updateCharacter: (id: string, patch: Partial<GlobalCharacter>) =>
    req<GlobalCharacter>(`/api/characters/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  listAssets: (sid: string) => req<{ items: Asset[] }>(`/api/scenarios/${sid}/assets`),
  uploadAsset: (sid: string, file: File, meta: { binding?: string; role?: string; entity?: string }) => {
    const fd = new FormData();
    fd.append("file", file);
    const qs = new URLSearchParams();
    if (meta.binding) qs.set("binding", meta.binding);
    if (meta.role) qs.set("role", meta.role);
    if (meta.entity) qs.set("entity", meta.entity);
    return req<Asset>(`/api/scenarios/${sid}/assets?${qs}`, { method: "POST", body: fd });
  },

  createSession: (versionId: string) =>
    req<{ session_id: string }>("/api/sessions", { method: "POST", body: JSON.stringify({ version_id: versionId }) }),
  sessionView: (sid: string) => req<PlayerView>(`/api/sessions/${sid}/view`),
  selectBranch: (sid: string, branchId: string) =>
    req<{ status: string }>(`/api/sessions/${sid}/select`, { method: "POST", body: JSON.stringify({ branch_id: branchId }) }),
  freeAction: (sid: string, text: string) =>
    req<{ status: string; ack?: string; question?: string; branch_id?: string }>(
      `/api/sessions/${sid}/action`, { method: "POST", body: JSON.stringify({ text }) }),
  playerCommand: (sid: string, command: string) =>
    req<{ position: number; status: string }>(`/api/sessions/${sid}/player`, { method: "POST", body: JSON.stringify({ command }) }),
  commitReceipt: (sid: string) => req(`/api/sessions/${sid}/receipt`, { method: "POST" }),
  addWish: (sid: string, text: string) =>
    req(`/api/sessions/${sid}/wishes`, { method: "POST", body: JSON.stringify({ text }) }),
  withdrawWish: (sid: string, wishId: string) =>
    req(`/api/sessions/${sid}/wishes/${wishId}`, { method: "DELETE" }),
  continueWorld: (sid: string) =>
    req<{ status: string; arc: number }>(`/api/sessions/${sid}/continue`, { method: "POST" }),

  devState: (sid: string) => req<DevState>(`/api/dev/sessions/${sid}/state`),
  devTraces: (limit = 200) => req<{ items: any[] }>(`/api/dev/traces?limit=${limit}`),
  devProviders: () => req<{
    mode: string; profile: string;
    health: Record<string, ProviderHealth>; matrix: any[]; events: any[];
  }>("/api/dev/providers"),
  devRecoverProviders: () => req("/api/dev/providers/recover", { method: "POST" }),
  devInject: (provider: string, kind: string) =>
    req("/api/dev/providers/inject", { method: "POST", body: JSON.stringify({ provider, kind }) }),

  skills: () => req<SkillsRegistry>("/api/skills"),
  submitFeedback: (data: Record<string, string>) =>
    req("/api/feedback", { method: "POST", body: JSON.stringify(data) }),
};

export function sessionSocket(sid: string, onMessage: (msg: any) => void): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/sessions/${sid}`);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch { /* ignore */ }
  };
  return ws;
}
