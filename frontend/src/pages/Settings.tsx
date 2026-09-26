/** 设置：标准 / 开发者模式 + 全局显示（外观/字号/密度/字幕）+ 运行信息。 */
import React, { useEffect, useState } from "react";
import { api, type MediaLanguage } from "../api";
import { setDisplay, setState, toast, useUi } from "../store";

export default function Settings() {
  const ui = useUi();
  const [health, setHealth] = useState<any>(null);
  const [providers, setProviders] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [switching, setSwitching] = useState(false);
  const [generation, setGeneration] = useState<any>(null);
  const [preflight, setPreflight] = useState<any>(null);
  const [ledger, setLedger] = useState<any[]>([]);
  const [language, setLanguage] = useState<MediaLanguage | null>(null);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [languageError, setLanguageError] = useState("");
  const loadLanguage = async () => {
    try { setLanguage(await api.languageSettings()); setLanguageError(""); }
    catch { setLanguageError("语言设置暂时无法载入，请重试。"); }
  };
  useEffect(() => { void loadLanguage(); }, []);
  const updateLanguage = async (patch: Partial<MediaLanguage>) => {
    if (!language || savingLanguage) return;
    setSavingLanguage(true);
    try {
      setLanguage(await api.saveLanguageSettings({ ...language, ...patch }));
      setLanguageError("");
      toast("语言设置已保存，将用于之后新制作的场景。");
    } catch { setLanguageError("语言设置未保存，请重试。"); }
    finally { setSavingLanguage(false); }
  };
  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api.devProviders().then(setProviders).catch(() => {});
    api.devProfile().then(setProfile).catch(() => {});
    api.devGenerationSettings().then(setGeneration).catch(() => {});
    if (ui.mode === "developer") api.devUsageLedger().then((r) => setLedger(r.items)).catch(() => {});
  }, [ui.mode]);
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
          玩家模式只保留故事与继续入口；创作模式开放故事编排；开发者模式额外显示分支状态机、指纹、路由与 Trace 等技术细节。
        </p>
        <div className="toolbar">
          <button className={ui.mode === "player" ? "active" : ""}
            onClick={() => setState({ mode: "player" })}>玩家模式</button>
          <button className={ui.mode === "creator" ? "active" : ""}
            onClick={() => setState({ mode: "creator" })}>创作模式</button>
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
        {ui.mode !== "developer" && <p className="muted">{switching ? "正在准备，请稍候…" : profile?.error ? "切换暂时未完成，请重试。" : "运行环境已就绪"}</p>}
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
        <p className="muted">只影响之后的新任务，旧素材不会改变。当前云端保险丝：{generation?.fal_paid_generation_enabled ? "已开启" : "已暂停"}。</p>
        <div className="two">
          <label><span>视频语言（角色对白 / 旁白）</span><select aria-label="视频语言" value={language?.video_language ?? "zh-CN"}
            disabled={!language || savingLanguage} onChange={e => updateLanguage({ video_language: e.target.value as MediaLanguage["video_language"] })}>
            <option value="zh-CN">中文（普通话）</option><option value="en">English</option>
          </select></label>
          <label><span>字幕语言</span><select aria-label="字幕语言" value={language?.subtitle_language ?? "zh-CN"}
            disabled={!language || savingLanguage} onChange={e => updateLanguage({ subtitle_language: e.target.value as MediaLanguage["subtitle_language"] })}>
            <option value="zh-CN">中文（简体）</option><option value="en">English</option>
          </select></label>
          <label><span>图片生成分辨率</span><select value={generation?.image_resolution ?? "0.5K"} onChange={e => updateGeneration({ image_resolution: e.target.value })}>{["0.5K", "1K", "2K", "4K"].map(v => <option key={v}>{v}</option>)}</select></label>
          <label><span>视频生成分辨率</span><select value={generation?.video_resolution ?? "480P"} onChange={e => updateGeneration({ video_resolution: e.target.value })}>{["480P", "768P", "1080P"].map(v => <option key={v}>{v}</option>)}</select></label>
          <label><span>视频比例</span><select value={generation?.aspect_ratio ?? "16:9"} onChange={e => updateGeneration({ aspect_ratio: e.target.value })}>{["auto", "16:9", "9:16", "1:1"].map(v => <option key={v}>{v}</option>)}</select></label>
        </div>
        <p className="muted">语言设置保存在此部署，供之后新制作的场景使用。视频语言也用于新叙事与推荐文案；字幕可独立选择。已生成或正在制作的场景保留原语言。字幕是场景摘要，并非逐字听写；本设置不会翻译旧视频或改变界面语言。</p>
        {languageError && <p role="alert">{languageError}{!language && <button onClick={loadLanguage}>重新载入语言设置</button>}</p>}
        {ui.mode !== "developer" && <p className="muted">当前云端媒体生成暂时不可用时，可以继续播放已有素材、上传素材或选择文字模式。</p>}
        {ui.mode === "developer" && <>
          <h4>开发测试覆盖</h4>
          <p className="muted">仅用于测试/验收，不会修改已发布故事的正式配置。</p>
          <div className="two">
            <label className="toggle-line"><span>Jev 推荐预生成视频</span><input type="checkbox"
              checked={generation?.pre_generate_recommendation_media !== false}
              onChange={e => updateGeneration({ pre_generate_recommendation_media: e.target.checked })} />
              <small>{generation?.pre_generate_recommendation_media === false ? "关闭：只在选中后生成视频，节省 H3 费用" : "开启：推荐出现前并行准备视频"}</small></label>
            <label className="toggle-line"><span>启用测试生成覆盖</span><input type="checkbox" checked={Boolean(generation?.test_override_enabled)} onChange={e => updateGeneration({ test_override_enabled: e.target.checked })} /> <small>仅开发测试上下文</small></label>
            <label><span>测试 Top-K</span><select value={generation?.test_top_k ?? 1} onChange={e => updateGeneration({ test_top_k: Number(e.target.value) })}>{[1, 2, 3].map(v => <option key={v}>{v}</option>)}</select></label>
            <label><span>每分支最大 Shot</span><select value={generation?.test_max_shots ?? 1} onChange={e => updateGeneration({ test_max_shots: Number(e.target.value) })}>{[1, 2, 3].map(v => <option key={v}>{v}</option>)}</select></label>
            <label><span>单 Shot 最大时长</span><select value={generation?.test_shot_duration ?? 5} onChange={e => updateGeneration({ test_shot_duration: Number(e.target.value) })}>{[5, 10, 15].map(v => <option key={v}>{v}s</option>)}</select></label>
          </div>
          <p className="muted">测试参考上限：图片 {generation?.max_test_reference_images ?? 2} 张，视频 {generation?.max_test_reference_videos ?? 0} 个。</p>
          <div className="toolbar"><button onClick={async () => {
            try { setPreflight(await api.devGenerationPreflight({ role: "h3_max" })); }
            catch { toast("暂时无法读取生成预检，请稍后重试。"); }
          }}>查看付费 Preflight</button><button onClick={() => api.devUsageLedger().then(r => setLedger(r.items))}>刷新 Usage Ledger</button></div>
          {preflight && <><p className="muted">当前配置预估，尚未锁定生成计划；参考素材数量在完成角色与镜头解析前未知。</p><pre>{JSON.stringify(preflight, null, 2)}</pre></>}
          {ledger.length > 0 && <details><summary>最近 Usage Ledger（{ledger.length}）</summary><pre>{JSON.stringify(ledger, null, 2)}</pre></details>}
        </>}
      </div>
    </>
  );
}

async function reqGeneration(patch: Record<string, any>) {
  const resp = await fetch("/api/dev/generation-settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
  if (!resp.ok) throw new Error(String(resp.status));
  return resp.json();
}
