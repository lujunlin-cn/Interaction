/** 设置：标准 / 开发者模式 + 全局显示（外观/字号/密度/字幕）+ 运行信息。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { setDisplay, setState, useUi } from "../store";

export default function Settings() {
  const ui = useUi();
  const [health, setHealth] = useState<any>(null);
  const [providers, setProviders] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [switching, setSwitching] = useState(false);
  const [generation, setGeneration] = useState<any>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api.devProviders().then(setProviders).catch(() => {});
    api.devProfile().then(setProfile).catch(() => {});
    api.devGenerationSettings().then(setGeneration).catch(() => {});
  }, []);
  const switchProfile = async (target: string) => {
    setSwitching(true);
    try {
      const result = await api.devProfileSwitch(target);
      setProfile(result);
      setProviders(await api.devProviders());
    } catch (e: any) {
      setProfile({ state: "FAILED", error: e.message });
    } finally {
      setSwitching(false);
    }
  };
  const updateGeneration = async (patch: Record<string, any>) => {
    try { setGeneration(await reqGeneration(patch)); } catch { /* settings are best effort */ }
  };
  const d = ui.display;
  return (
    <>
      <div className="card">
        <h3>模式</h3>
        <p className="muted">
          标准模式只显示自然语言状态；开发者模式会显示分支状态机、指纹、路由与 Trace 等技术细节。
        </p>
        <div className="toolbar">
          <button className={ui.mode === "standard" ? "active" : ""}
            onClick={() => setState({ mode: "standard" })}>标准模式</button>
          <button className={ui.mode === "developer" ? "active" : ""}
            onClick={() => setState({ mode: "developer" })}>开发者模式</button>
        </div>
      </div>

      <div className="card">
        <h3>本地运行模式</h3>
        <p className="muted">
          选择在本机生成视频或优先生成故事。切换期间会保存进度，准备好后可以继续游玩。
        </p>
        <div className="toolbar">
          {([["AGENT_LOCAL_PROFILE", "故事优先"], ["VIDEO_LOCAL_PROFILE", "本机视频"]] as const).map(([target, label]) => (
            <button key={target} className={providers?.profile === target ? "active" : ""}
              disabled={switching || providers?.profile === target || profile?.state !== "ACTIVE"}
              onClick={() => switchProfile(target)}>
              {providers?.profile === target ? `✓ ${label}` : label}
            </button>
          ))}
        </div>
        {ui.mode === "developer" && <div className="kv" style={{ marginTop: 12 }}>
          <b>当前 Profile</b><span className="mono">{providers?.profile ?? "正在载入…"}</span>
          <b>Sol-H3</b><span className="mono">{providers?.health?.sol_h3_local?.status ?? "未检查"}</span>
          <b>切换状态</b><span>{profile?.state ?? "ACTIVE"}{profile?.error ? `：${profile.error}` : ""}</span>
        </div>}
        {ui.mode === "standard" && <p className="muted">{switching ? "正在准备，请稍候…" : profile?.error ? "切换暂时未完成，请重试。" : "运行环境已就绪"}</p>}
      </div>

      <div className="card">
        <h3>外观</h3>
        <div className="two">
          <label><span>主题</span>
            <div className="toolbar" style={{ marginTop: 0 }}>
              <button className={d.appearance === "system" ? "active" : ""}
                onClick={() => setDisplay({ appearance: "system" })}>跟随系统</button>
              <button className={d.appearance === "light" ? "active" : ""}
                onClick={() => setDisplay({ appearance: "light" })}>浅色</button>
              <button className={d.appearance === "dark" ? "active" : ""}
                onClick={() => setDisplay({ appearance: "dark" })}>深色</button>
            </div>
          </label>
          <label><span>界面大小</span>
            <div className="toolbar" style={{ marginTop: 0 }}>
              {([["standard", "标准"], ["large", "大"], ["xlarge", "特大"]] as const).map(([v, l]) => (
                <button key={v} className={d.uiSize === v ? "active" : ""}
                  onClick={() => setDisplay({ uiSize: v })}>{l}</button>
              ))}
            </div>
          </label>
          <label><span>界面字号</span>
            <div className="toolbar" style={{ marginTop: 0 }}>
              {([["small", "小"], ["medium", "标准"], ["large", "大"], ["xlarge", "特大"]] as const).map(([v, l]) => (
                <button key={v} className={d.fontSize === v ? "active" : ""}
                  onClick={() => setDisplay({ fontSize: v })}>{l}</button>
              ))}
            </div>
          </label>
          <label><span>字幕（字号 / 位置）</span>
            <div className="toolbar" style={{ marginTop: 0 }}>
              {([["standard", "标准"], ["large", "大"], ["xlarge", "特大"], ["auto", "自动适应屏幕"]] as const).map(([v, l]) => (
                <button key={v} className={d.subtitleSize === v ? "active" : ""}
                  onClick={() => setDisplay({ subtitleSize: v })}>{l}</button>
              ))}
              <span style={{ width: 8 }} />
              {([["bottomInside", "画面底部·内"], ["bottomOutside", "画面底部·外"]] as const).map(([v, l]) => (
                <button key={v} className={d.subtitlePos === v ? "active" : ""}
                  onClick={() => setDisplay({ subtitlePos: v })}>{l}</button>
              ))}
            </div>
          </label>
        </div>
        {/* 实时预览 */}
        <div className="display-preview">
          <div className="preview-scene">
            <div className="preview-caption" style={{
              fontSize: d.subtitleSize === "xlarge" ? 22 : d.subtitleSize === "large" ? 19 : 15,
              bottom: d.subtitlePos === "bottomOutside" ? -28 : 12,
            }}>
              雨夜的公寓里，你听到门外传来脚步声。
            </div>
          </div>
          <p className="muted" style={{ marginTop: 8 }}>
            预览随设置实时变化；界面按 100% 浏览器缩放设计。
          </p>
        </div>
      </div>

      {ui.mode === "developer" && <div className="card">
        <h3>运行信息</h3>
        {health ? (
          <div className="kv">
            <b>Provider 模式</b><span className="mono">{health.provider_mode}</span>
            <b>Runtime Profile</b><span className="mono">{health.profile}</span>
          </div>
        ) : <p className="muted">正在载入…</p>}
        <p className="muted">
          API Key、Endpoint、模型 ID 全部由部署环境的 .env 注入，不在界面显示、不入库。
        </p>
      </div>}

      <div className="card">
        <h3>媒体生成</h3>
        {ui.mode === "standard" ? (
          <p className="muted">云端媒体生成当前受部署策略控制；已有素材仍可正常播放。</p>
        ) : (
          <>
            <p className="muted">仅影响之后的新任务，旧素材不会改变。当前付费保险丝：{generation?.fal_paid_generation_enabled ? "已开启" : "已暂停"}。</p>
            <div className="two">
              <label><span>图片生成分辨率</span><select value={generation?.image_resolution ?? "0.5K"} onChange={e => updateGeneration({ image_resolution: e.target.value })}>{["0.5K", "1K", "2K", "4K"].map(v => <option key={v}>{v}</option>)}</select></label>
              <label><span>视频生成分辨率</span><select value={generation?.video_resolution ?? "480P"} onChange={e => updateGeneration({ video_resolution: e.target.value })}>{["480P", "768P", "1080P"].map(v => <option key={v}>{v}</option>)}</select></label>
              <label><span>视频比例</span><select value={generation?.aspect_ratio ?? "16:9"} onChange={e => updateGeneration({ aspect_ratio: e.target.value })}>{["16:9", "9:16", "1:1", "auto"].map(v => <option key={v}>{v}</option>)}</select></label>
              <label><span>测试 Top-K</span><select value={generation?.test_top_k ?? 1} onChange={e => updateGeneration({ test_top_k: Number(e.target.value) })}>{[1, 2, 3].map(v => <option key={v}>{v}</option>)}</select></label>
              <label><span>每分支最大 Shot</span><select value={generation?.test_max_shots ?? 1} onChange={e => updateGeneration({ test_max_shots: Number(e.target.value) })}>{[1, 2, 3].map(v => <option key={v}>{v}</option>)}</select></label>
              <label><span>单 Shot 最大时长</span><select value={generation?.test_shot_duration ?? 5} onChange={e => updateGeneration({ test_shot_duration: Number(e.target.value) })}>{[5, 10, 15].map(v => <option key={v}>{v}s</option>)}</select></label>
            </div>
            <p className="muted">测试参考上限：图片 {generation?.max_test_reference_images ?? 2} 张，视频 {generation?.max_test_reference_videos ?? 0} 个。</p>
          </>
        )}
      </div>
    </>
  );
}

async function reqGeneration(patch: Record<string, any>) {
  const resp = await fetch("/api/dev/generation-settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
  if (!resp.ok) throw new Error(String(resp.status));
  return resp.json();
}
