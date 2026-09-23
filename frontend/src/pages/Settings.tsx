/** 设置：标准 / 开发者模式切换 + 运行信息。 */
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { setState, useUi } from "../store";

export default function Settings() {
  const ui = useUi();
  const [health, setHealth] = useState<any>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);
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
