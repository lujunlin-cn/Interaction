/** API 客户端：前端只与后端 REST/WS 通信，绝不直连模型 Provider。 */
import type {
  Asset, CharacterAsset, CharacterReferenceSelection, CharacterSnapshot, CharacterVersion,
  DevState, Fixtures, GlobalCharacter, PlayerView, ProfileStatus,
  ProviderHealth, PublishCheck, ScenarioDraft, ScenarioVersion, SkillsRegistry,
} from "./types";

const BASE = "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + path, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail: any = `${resp.status}`;
    try {
      detail = (await resp.json()).detail ?? detail;
    } catch { /* ignore */ }
    const err = new Error(typeof detail === "string" ? detail : (detail?.message || JSON.stringify(detail)));
    (err as any).detail = detail;
    throw err;
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
  publishScenario: (id: string, opts: { reviewed: boolean; play?: boolean }) =>
    req<{ version_id: string; version: string; session_id?: string; checklist?: PublishCheck[] }>(
      `/api/scenarios/${id}/publish`,
      { method: "POST", body: JSON.stringify(opts) }),
  publishCheck: (id: string) =>
    req<{ checklist: PublishCheck[] }>(`/api/scenarios/${id}/publish-check`),
  scenarioVersions: (id: string) => req<{ items: ScenarioVersion[] }>(`/api/scenarios/${id}/versions`),
  duplicateScenario: (id: string) =>
    req<ScenarioDraft>(`/api/scenarios/${id}/duplicate`, { method: "POST" }),
  deleteScenario: (id: string) =>
    req<{ ok: boolean }>(`/api/scenarios/${id}`, { method: "DELETE" }),

  listCharacters: (q = "") => req<{ items: GlobalCharacter[] }>(`/api/characters?q=${encodeURIComponent(q)}`),
  createCharacter: (data: Partial<GlobalCharacter>) =>
    req<GlobalCharacter>("/api/characters", { method: "POST", body: JSON.stringify(data) }),
  updateCharacter: (id: string, patch: Partial<GlobalCharacter>) =>
    req<GlobalCharacter>(`/api/characters/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  listCharacterAssets: (cid: string) =>
    req<{ items: Asset[] }>(`/api/characters/${cid}/assets`),
  uploadCharacterAsset: (cid: string, file: File, role: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("role", role);
    return req<Asset>(`/api/characters/${cid}/assets`, { method: "POST", body: fd });
  },
  aiGenerateCharacter: (cid: string, prompt = "", numImages = 2) =>
    req<{ items: CharacterAsset[] }>(`/api/characters/${cid}/ai-generate`, {
      method: "POST", body: JSON.stringify({ prompt, num_images: numImages }),
    }),
  standardCharacterViews: (cid: string, frontAssetId: string) =>
    req<{ items: CharacterAsset[] }>(`/api/characters/${cid}/standard-views`, {
      method: "POST", body: JSON.stringify({ front_asset_id: frontAssetId }),
    }),
  editCharacterImage: (cid: string, sourceAssetId: string, instruction: string,
                       role = "derived", outfitId?: string) =>
    req<{ items: CharacterAsset[] }>(`/api/characters/${cid}/edit-image`, {
      method: "POST", body: JSON.stringify({ source_asset_id: sourceAssetId,
        instruction, role, outfit_id: outfitId }),
    }),
  listCharacterStudioAssets: (cid: string, status?: string) =>
    req<{ items: CharacterAsset[] }>(`/api/characters/${cid}/character-assets${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  approveCharacterAsset: (cid: string, aid: string) =>
    req<CharacterAsset>(`/api/characters/${cid}/assets/${aid}/approve`, { method: "POST" }),
  setCharacterAssetStatus: (aid: string, status: CharacterAsset["status"]) =>
    req<CharacterAsset>(`/api/character-assets/${aid}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  characterVersions: (cid: string) => req<{ items: CharacterVersion[] }>(`/api/characters/${cid}/versions`),
  listCharacterOutfits: (cid: string) => req<{ items: any[] }>(`/api/characters/${cid}/outfits`),
  createCharacterOutfit: (cid: string, name: string, description = "") =>
    req<any>(`/api/characters/${cid}/outfits`, { method: "POST", body: JSON.stringify({ name, description }) }),
  characterVersionDiff: (cid: string, from: number, to: number) =>
    req<any>(`/api/characters/${cid}/versions/diff?from_v=${from}&to_v=${to}`),
  characterSnapshot: (scenarioVersionId: string, cid: string) =>
    req<CharacterSnapshot>(`/api/scenarios/${scenarioVersionId}/character-snapshots/${cid}`, { method: "POST" }),
  listCharacterSnapshots: (scenarioVersionId: string) =>
    req<{ items: CharacterSnapshot[] }>(`/api/scenarios/${scenarioVersionId}/character-snapshots`),
  overrideCharacterSnapshot: (snapshotId: string, overrides: Record<string, any>) =>
    req<CharacterSnapshot>(`/api/character-snapshots/${snapshotId}/override`, { method: "POST", body: JSON.stringify(overrides) }),
  promoteCharacterSnapshot: (snapshotId: string) =>
    req<CharacterVersion>(`/api/character-snapshots/${snapshotId}/promote`, { method: "POST" }),
  resolveCharacterReferences: (snapshotId: string, sceneId: string, providerLimits?: Record<string, number>) =>
    req<CharacterReferenceSelection>(`/api/character-snapshots/${snapshotId}/resolve-references`, {
      method: "POST", body: JSON.stringify({ scene_or_shot_id: sceneId, provider_limits: providerLimits }),
    }),

  listAssets: (sid: string) => req<{ items: Asset[] }>(`/api/scenarios/${sid}/assets`),
  uploadAsset: (sid: string, file: File, meta: { binding?: string; role?: string; entity?: string }) => {
    const fd = new FormData();
    fd.append("file", file);
    if (meta.binding) fd.append("binding", meta.binding);
    if (meta.role) fd.append("role", meta.role);
    if (meta.entity) fd.append("entity", meta.entity);
    return req<Asset>(`/api/scenarios/${sid}/assets`, { method: "POST", body: fd });
  },
  replaceAsset: (sid: string, aid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<Asset>(`/api/scenarios/${sid}/assets/${aid}`, { method: "PUT", body: fd });
  },
  removeAsset: (sid: string, aid: string) =>
    req<{ ok: boolean }>(`/api/scenarios/${sid}/assets/${aid}`, { method: "DELETE" }),
  patchAsset: (sid: string, aid: string, patch: Partial<Asset>) =>
    req<Asset>(`/api/scenarios/${sid}/assets/${aid}`,
      { method: "PATCH", body: JSON.stringify(patch) }),

  createSession: (versionId: string) =>
    req<{ session_id: string }>("/api/sessions", { method: "POST", body: JSON.stringify({ version_id: versionId }) }),
  sessionView: (sid: string) => req<PlayerView>(`/api/sessions/${sid}/view`),
  selectBranch: (sid: string, branchId: string) =>
    req<{ status: string }>(`/api/sessions/${sid}/select`, { method: "POST", body: JSON.stringify({ branch_id: branchId }) }),
  freeAction: (sid: string, text: string) =>
    req<{ status: string; ack?: string; question?: string; branch_id?: string; echo?: any; merged?: boolean }>(
      `/api/sessions/${sid}/action`, { method: "POST", body: JSON.stringify({ text }) }),
  confirmIntent: (sid: string, data: { approved: boolean; action?: string; desire?: string; strategy?: string }) =>
    req<{ status: string }>(`/api/sessions/${sid}/intent/confirm`, { method: "POST", body: JSON.stringify(data) }),
  cancelGeneration: (sid: string) =>
    req<{ status: string; count?: number }>(`/api/sessions/${sid}/cancel`, { method: "POST" }),
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
  devProfile: () => req<ProfileStatus>("/api/dev/profile"),
  devProfileSwitch: (target: string) =>
    req<any>("/api/dev/profile/switch", { method: "POST", body: JSON.stringify({ target }) }),
  devFixtures: () => req<Fixtures>("/api/dev/fixtures"),
  devSetFixture: (key: string, value: any) =>
    req<Fixtures>("/api/dev/fixtures", { method: "POST", body: JSON.stringify({ key, value }) }),
  devLocalTask: (prompt: string) =>
    req<any>("/api/dev/local-task", { method: "POST", body: JSON.stringify({ prompt }) }),
  devJobs: (limit = 50) => req<{ items: any[] }>(`/api/dev/jobs?limit=${limit}`),

  skills: () => req<SkillsRegistry>("/api/skills"),
  skillCalls: (skillId: string, limit = 5) =>
    req<{ items: any[] }>(`/api/skills/${skillId}/calls?limit=${limit}`),
  toggleSkill: (skillId: string, enabled: boolean) =>
    req<SkillsRegistry>(`/api/skills/${skillId}/toggle`, { method: "POST", body: JSON.stringify({ enabled }) }),
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
