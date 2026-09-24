/** 设置：标准 / 开发者模式 + 全局显示（外观/字号/密度/字幕）+ 运行信息。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { setDisplay, setState, useUi } from "../store";

export default function Settings() {
  const ui = useUi();
  const [health, setHealth] = useState<any>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);
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
          <label><span>UI Size</span>
            <div className="toolbar" style={{ marginTop: 0 }}>
              {([["standard", "标准"], ["large", "大"], ["xlarge", "特大"]] as const).map(([v, l]) => (
                <button key={v} className={d.uiSize === v ? "active" : ""}
                  onClick={() => setDisplay({ uiSize: v, fontSize: v === "standard" ? "medium" : v })}>{l}</button>
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

      <div className="card">
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
      </div>
    </>
  );
}
