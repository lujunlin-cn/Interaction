/** Player presentation; runtime contracts remain on the server. */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { api, sessionSocket } from "../api";
import { setState, toast, useUi } from "../store";
import type { PendingIntent, PlayerView, Wish } from "../types";

const WISH_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "生效中", DEFERRED: "已延期", CONFLICTED: "与规则冲突", FULFILLED: "已实现",
  PARTIALLY_FULFILLED: "部分实现", FAILED: "未能实现", SUPERSEDED: "被替换", WITHDRAWN: "已撤回",
};
function publicLabel(value: string, fallback: string) { return /^[a-z][a-z0-9]*_[a-z0-9_]+$/i.test(value) ? fallback : value; }
function relationshipLabel(value: number) { return value >= 70 ? "信任你" : value >= 50 ? "愿意与你交流" : value >= 30 ? "有所戒备" : "暂时保持距离"; }

export default function Player() {
  const ui = useUi(), sid = ui.sessionId, developer = ui.mode === "developer";
  const [view, setView] = useState<PlayerView | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [ack, setAck] = useState<string | null>(null);
  const [wishOpen, setWishOpen] = useState(false);
  const [hudHover, setHudHover] = useState(false);
  const [hudPinned, setHudPinned] = useState(false);
  const [replay, setReplay] = useState<string | null>(null);
  const [media, setMedia] = useState<"loading" | "playing" | "failed">("loading");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [titleVisible, setTitleVisible] = useState(true);
  const [controlActivity, setControlActivity] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [connectionFailed, setConnectionFailed] = useState(false);
  const [devState, setDevState] = useState<any>(null);
  const [now, setNow] = useState(Date.now());
  const [timedBase, setTimedBase] = useState<{remaining: number; at: number} | null>(null);
  const shellRef = useRef<HTMLDivElement>(null), videoRef = useRef<HTMLVideoElement>(null);
  const requestInFlight = useRef(false);
  const receiptSent = useRef("");
  const error = (e: any) => toast(developer ? e.message : "这个操作暂时没有完成，请重试。");
  const command = (c: string) => sid ? api.playerCommand(sid, c).catch(error) : Promise.resolve();

  useEffect(() => {
    if (!sid) return;
    let closed = false;
    const refresh = () => api.sessionView(sid).then(v => { if (!closed) { setView(v); setConnectionFailed(false); } }).catch(() => !closed && setConnectionFailed(true));
    void refresh();
    const ws = sessionSocket(sid, msg => { if (!closed && msg.type === "state") setView(msg.view); });
    // Playback position / Lead visibility must also refresh when a healthy WS has no new state event.
    const t = window.setInterval(refresh, 1000);
    return () => { closed = true; clearInterval(t); ws.close(); };
  }, [sid]);
  useEffect(() => {
    const t = view?.timed;
    setTimedBase(t?.active && t.remaining_ms != null ? {remaining: t.remaining_ms, at: Date.now()} : null);
  }, [view?.timed?.remaining_ms, view?.timed?.active]);
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 200); return () => clearInterval(t); }, []);
  useEffect(() => {
    setMedia("loading"); setTitleVisible(true);
  }, [view?.player.video_url, replay, loadAttempt]);
  useEffect(() => {
    if (media !== "playing") return;
    const t = setTimeout(() => setTitleVisible(false), 3500); return () => clearTimeout(t);
  }, [media, view?.player.video_url]);
  useEffect(() => {
    if (media !== "loading" || !view?.player.video_url) return;
    const t = setTimeout(() => setMedia("failed"), 20000); return () => clearTimeout(t);
  }, [media, view?.player.video_url, loadAttempt]);
  useEffect(() => {
    setShowControls(true);
    if (media !== "playing" || view?.player.status !== "PLAYING") return;
    const t = setTimeout(() => setShowControls(false), 3000);
    return () => clearTimeout(t);
  }, [controlActivity, media, view?.player.status]);
  useEffect(() => {
    const fn = () => setFullscreen(document.fullscreenElement === shellRef.current);
    document.addEventListener("fullscreenchange", fn); return () => document.removeEventListener("fullscreenchange", fn);
  }, []);
  useEffect(() => {
    // Theater Mode is an application layout state. It must never depend on
    // document.fullscreenElement and must not leak after leaving the Player.
    if (sid) setState({ theaterMode: true });
    return () => setState({ theaterMode: false });
  }, [sid]);
  useEffect(() => {
    if (sid && developer && ui.inspectorOpen) void api.devState(sid).then(setDevState).catch(error);
  }, [sid, developer, ui.inspectorOpen, view?.player.status]);

  const submitAction = async () => {
    if (!sid || !input.trim() || requestInFlight.current) return;
    requestInFlight.current = true; setBusy(true); setAck(null);
    try {
      const r = await api.freeAction(sid, input.trim());
      if (r.status === "QUICK_ACK") setAck(r.ack || "好的。");
      setInput(""); setView(await api.sessionView(sid));
    } catch (e) { error(e); } finally { requestInFlight.current = false; setBusy(false); }
  };
  const choose = async (branchId: string) => {
    if (!sid || requestInFlight.current) return;
    requestInFlight.current = true; setBusy(true);
    try { await api.selectBranch(sid, branchId); setView(await api.sessionView(sid)); }
    catch (e) { error(e); } finally { requestInFlight.current = false; setBusy(false); }
  };
  if (!sid) return <div className="player-shell"><div className="empty">请从故事库选择一个世界开始。</div></div>;
  if (!view) return <div className="player-shell"><div className="card">{connectionFailed ? "暂时无法连接故事，请稍后重试。" : "正在连接故事…"}<button onClick={() => setState({page: "home"})}>返回故事库</button></div></div>;
  const p = view.player;
  const failed = p.status === "FAILED_RECOVERABLE" || p.status === "FAILED";
  const generating = p.status === "OPENING_PREPARING" || p.status === "GENERATING_NEXT";
  const accepted = busy || Boolean((view as any).action_pending) || Boolean(view.pending_intent);
  const decisionOpen = Boolean(
    view.ended || view.pending_intent || view.last_failed_action ||
    view.recommendations.length > 0 || view.timed?.selection_open ||
    failed || media === "failed" || p.status === "WAITING_DECISION" ||
    p.status === "READY" || (p.status === "PLAYING" && p.duration > 0 && p.position >= (p.decision_open_at ?? p.lead))
  );
  const remaining = timedBase ? Math.max(0, timedBase.remaining - (now - timedBase.at)) : null;
  const hudOpen = hudPinned || hudHover;
  const source = replay || p.video_url;
  const finished = async () => {
    if (replay) { setReplay(null); return; }
    await command("skip");
    if (receiptSent.current !== p.video_url) { await api.commitReceipt(sid); receiptSent.current = p.video_url; }
  };
  const recover = <div className="toolbar recovery-actions">
    {media === "failed" && <button onClick={() => { setMedia("loading"); setLoadAttempt(x => x + 1); }}>重新载入</button>}
    <button onClick={() => command(failed ? "retry" : "regenerate")}>重新生成</button>
    <button onClick={() => { setInput(view.last_failed_action?.raw_text || ""); document.querySelector<HTMLInputElement>('.free-input-row input')?.focus(); }}>修改行动</button>
    <button onClick={async () => { const r = await command("text_continue"); if (r?.needs_action) setInput(r.raw_text || ""); else setInput(""); }}>文字模式继续</button>
    <button onClick={() => setState({page: "home", sessionId: null})}>退出故事</button>
  </div>;
  return <div className="player-shell immersive-player" ref={shellRef} data-testid="player-shell" data-decision-open={decisionOpen ? "true" : "false"} onPointerMove={() => setControlActivity(Date.now())} onPointerDown={() => setControlActivity(Date.now())} onKeyDown={() => setControlActivity(Date.now())}>
    <header className="player-head"><b className="grow">{view.scenario.title}</b><span className="muted">第 {view.arc.seq} 篇章</span><button className="small" onClick={() => setState({page: "home", sessionId: null, theaterMode: false})}>退出</button></header>
    <div className="immersion-layer" data-layer="immersion">
      <div className="player-stage">
        {source && <video key={`${source}:${loadAttempt}`} ref={videoRef} src={source} autoPlay playsInline
          onLoadStart={() => { setMedia("loading"); if (!replay) void command("pause"); }}
          onCanPlay={() => { setMedia("playing"); videoRef.current?.play().catch(() => setAck("点击播放，开始观看这一幕。")); }}
          onPlaying={() => { setMedia("playing"); setAck(a => a === "点击播放，开始观看这一幕。" ? null : a); if (!replay) void command("play"); }}
          onWaiting={() => { setMedia("loading"); if (!replay) void command("pause"); }}
          onPause={() => !replay && void command("pause")}
          onError={() => { setMedia("failed"); if (!replay) void command("pause"); }}
          onEnded={finished} />}
        {(generating || failed || (source && media !== "playing") || (!source && !p.scene_text)) && <div className={`media-status ${failed || media === "failed" ? "failed" : ""}`} role="status"
          data-media-state={failed || (source && media === "failed") ? "FAILED" : generating ? "GENERATING" : "LOADING"}>
          <div className="media-status-symbol">{failed || media === "failed" ? "↻" : "◌"}</div>
          <h3>{failed ? "这个行动暂时没有生成成功。" : source && media === "failed" ? "这一幕暂时无法播放。" : generating ? "正在生成这一幕……" : "正在载入场景……"}</h3>
          <p>{failed || media === "failed" ? "你的行动已保留，可以重新尝试或继续阅读故事。" : "故事准备好后将在这里播放。"}</p>
          {(failed || (source && media === "failed")) && recover}
        </div>}
        {!source && p.scene_text && !generating && !failed && <div className="text-scene"><p>{p.scene_text}</p></div>}
        {!replay && source && <div className={`scene-intro ${titleVisible ? "visible" : ""}`}><b>{p.scene_title}</b><span>{(p as any).location_name || ""}</span></div>}
        <aside className={`player-hud ${hudOpen ? "open" : ""}`} data-layer="hud" onMouseEnter={() => setHudHover(true)} onMouseLeave={() => setHudHover(false)}>
          <button className="hud-toggle" aria-label="故事随身册" aria-expanded={hudOpen} aria-pressed={hudPinned} onClick={() => { setHudPinned(v => !v); setHudHover(false); }}>☰ {hudPinned ? "收回" : "随身册"}</button>
          {hudOpen && <div className="hud-drawer">
            <h4>背包</h4>{[...new Set(view.known.inventory.map(it => developer ? it : publicLabel(view.known.inventory_labels?.[it] || it, "随身物品")))].map(label => <p key={label}>{label}</p>)}{!view.known.inventory.length && <p className="muted">暂时没有物品</p>}
            <h4>人物关系</h4>{view.known.relationships.map(r => <p key={r.id}>{r.name}：{developer ? `${r.value} / 100` : relationshipLabel(r.value)}</p>)}
            <h4>线索</h4>{[...view.known.clues, ...view.known.knowledge].filter((c,i,a) => a.findIndex(x => x.id === c.id) === i).map(c => <p key={c.id}>{developer ? c.label : publicLabel(c.label, "新发现的线索")}</p>)}
            <h4>愿望</h4>{view.wishes.filter(w => w.status === "ACTIVE").map(w => <p key={w.id}>{w.raw}</p>)}
            <button onClick={() => setWishOpen(true)}>许下或查看愿望</button>
          </div>}
        </aside>
        <div className="player-controls" data-visible={showControls}>
          <button className="small" onClick={() => { const v = videoRef.current; if (v) v.paused ? v.play().catch(error) : v.pause(); }}>播放 / 暂停</button>
          <div className="player-progress grow"><div style={{width: `${p.duration ? Math.min(100, p.position / p.duration * 100) : 0}%`}} /></div>
          <span className="player-time" aria-label="播放进度">{Math.floor(p.position)}s / {Math.floor(p.duration)}s</span>
          <details className="player-more"><summary>··· 更多</summary><div>
            <button onClick={() => setState({ theaterMode: !ui.theaterMode })}>{ui.theaterMode ? "退出剧场模式" : "进入剧场模式"}</button>
            <button onClick={async () => { try { document.fullscreenElement ? await document.exitFullscreen() : await shellRef.current?.requestFullscreen(); } catch (e) { error(e); } }}>{fullscreen ? "退出浏览器全屏" : "浏览器全屏"}</button>
            <button onClick={() => { setReplay(null); setLoadAttempt(x => x + 1); }}>重新播放</button>
            <button onClick={finished}>跳过当前场景</button>{view.generating.length > 0 && <button onClick={() => api.cancelGeneration(sid).catch(error)}>取消生成</button>}{replay && <button onClick={() => setReplay(null)}>返回当前场景</button>}
            <button onClick={() => setState({page: "home", sessionId: null, theaterMode: false})}>退出故事</button>
          </div></details>
          {developer && <button className="small" onClick={() => setState({inspectorOpen: !ui.inspectorOpen})}>Inspector</button>}
        </div>
      </div>
      {!replay && source && media === "playing" && p.caption && <div className="scene-caption"><div className="scene-text">{(p as any).caption_speaker && <b>{(p as any).caption_speaker}： </b>}{p.caption}</div></div>}
    </div>
    {connectionFailed && <p role="status">连接暂时中断，正在重新连接。你的行动草稿仍在这里。</p>}
    {ack && <div className="ack-toast">{ack}</div>}
    {view.last_failed_action && !failed && <div className="notice"><p>这个行动暂时没有生成成功。</p>{recover}</div>}
    {view.messages.length > 0 && <div className="msg-list">{view.messages.slice(-2).map((m,i) => <p key={i}>{m.text}</p>)}</div>}
    {view.pending_intent && <IntentCard key={view.pending_intent.raw_text} sid={sid} intent={view.pending_intent} />}
      {view.ended && view.ending && <EndingPanel sid={sid} view={view} onReplay={setReplay} />}
    {!view.ended && <div className="interaction-dock">
      {view.timed?.active && <div className="qte-composer"><b>{remaining == null ? "准备快速决定" : `${Math.ceil(remaining / 1000)} 秒`}</b><p>{view.timed.fallback_hint}</p></div>}
      {view.selected && view.selected.status !== "CANONICAL" ? <div className="decision-layer" data-layer="decision">✓ {view.selected.label} · 正在继续故事……</div>
        : !accepted && view.recommendations.length > 0 && (!view.timed?.active || view.timed.selection_open) && <section className="decision-layer" data-layer="decision"><div className="rec-row">{view.recommendations.map(r => <button className="rec-card" key={r.branch_id} disabled={busy} onClick={() => choose(r.branch_id)}><b>{r.label}</b>{r.media_ready === false && <small className="muted">视频准备中，选中后继续</small>}<p>{r.summary}</p></button>)}</div></section>}
      <section className="agency-layer" data-layer="agency"><p className="muted">推荐只是快捷行动，你仍然可以做自己的选择。</p><div className="free-input-row"><input aria-label="描述你想做的事" placeholder="描述你想做的事……" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !accepted) void submitAction(); }} /><button className="primary" disabled={accepted || !input.trim()} onClick={submitAction}>{accepted ? "正在继续故事…" : "行动"}</button></div></section>
    </div>}
    {developer && ui.inspectorOpen && <section className="card developer-inspector"><h3>Developer Inspector</h3><pre>{JSON.stringify(devState, null, 2)}</pre><button onClick={() => setState({page: "developer", devTab: "trace"})}>查看完整 Trace</button></section>}
    {wishOpen && <WishDrawer sid={sid} wishes={view.wishes} onClose={() => setWishOpen(false)} />}
  </div>;
}

/** 意图回显 / 澄清卡（FR-046 / AT-30）：玩家原文保留，可修改理解后确认 */
function IntentCard({ sid, intent }: { sid: string; intent: PendingIntent }) {
  const [action, setAction] = useState(intent.action);
  const [desire, setDesire] = useState(intent.desire);
  const [strategy, setStrategy] = useState(intent.strategy);
  const [editing, setEditing] = useState(intent.kind === "clarification");
  const [busy, setBusy] = useState(false);

  const send = async (approved: boolean) => {
    setBusy(true);
    try {
      await api.confirmIntent(sid, { approved, action, desire, strategy });
    } catch (e: any) {
      toast(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`intent-card ${intent.kind}`}>
      <div className="intent-head">
        {intent.kind === "clarification" ? "⚠ 这件事可能需要想清楚" : "我这样理解你的意思"}
      </div>
      <div className="intent-raw">你的原话：{intent.raw_text}</div>
      {editing ? (
        <div className="intent-form">
          <label><span>你打算怎么做</span>
            <input value={action} onChange={(e) => setAction(e.target.value)} /></label>
          <label><span>你想达到的目的</span>
            <input value={desire} onChange={(e) => setDesire(e.target.value)} /></label>
          <label><span>你希望的方式</span>
            <input value={strategy} onChange={(e) => setStrategy(e.target.value)} /></label>
        </div>
      ) : (
        <div className="intent-summary">
          {action && <div>行动：{action}</div>}
          {desire && <div>目的：{desire}</div>}
          {strategy && <div>方式：{strategy}</div>}
        </div>
      )}
      <div className="toolbar">
        <button className="primary" disabled={busy} onClick={() => send(true)}>
          {editing ? "确认并继续" : "按这个意思继续"}
        </button>
        {!editing && intent.kind === "echo" && (
          <button disabled={busy} onClick={() => setEditing(true)}>修改理解</button>
        )}
        <button disabled={busy} onClick={() => send(false)}>算了，不这么做</button>
      </div>
    </div>
  );
}

/** 篇章结束页：保留清单 / 下一篇章预告 / 关键行动 / 篇章历史 / 反馈入口 */
function EndingPanel({ sid, view, onReplay }: {
  sid: string; view: PlayerView; onReplay: (url: string) => void;
}) {
  const developer = useUi().mode === "developer";
  const e = view.ending!;
  return (
    <div className="ending-panel">
      <h2 className="ending-title">第 {view.arc.seq} 篇章完 · {e.title}</h2>

      <div className="ending-grid">
        <div className="ending-card">
          <h3>会继续保留</h3>
          {e.carried.relationships.map((r) => (
            <div key={r.id} className="tool-line">{r.name}　<span className="muted">{developer ? `信任 ${r.value}` : relationshipLabel(r.value)}</span></div>
          ))}
          {e.carried.inventory.map((it) => (
            <div key={it} className="tool-line">🎒 {it}</div>
          ))}
          {e.carried.knowledge.map((k) => (
            <div key={k.id} className="tool-line">🔎 {k.label}</div>
          ))}
          <div className="muted" style={{ marginTop: 6 }}>{e.carried.continue_note}</div>
        </div>
        <div className="ending-card">
          <h3>下一篇章</h3>
          <p>{e.next_arc_hint}</p>
          {!e.continue_available && (
            <div className="notice warn">
              本局的生成预算已接近用完（{e.budget.used}/{e.budget.total}），
              继续可能需要先结束本局或提高预算。
            </div>
          )}
        </div>
      </div>

      {e.turns.length > 0 && (
        <div className="ending-card">
          <h3>本篇章关键行动</h3>
          <table className="ending-table">
            <tbody>
              {e.turns.map((t, i) => (
                <tr key={i}>
                  <td className="muted">{i + 1}</td>
                  <td>{t.label}</td>
                  <td className="muted">{t.title}</td>
                  <td>
                    {t.video_url && (
                      <button className="small" onClick={() => onReplay(t.video_url!)}>
                        回顾片段
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {e.arcs.length > 1 && (
        <div className="ending-card">
          <h3>篇章历史</h3>
          {e.arcs.map((a) => (
            <div key={a.seq} className="tool-line">
              第 {a.seq} 篇章 <span className="muted">{developer ? a.ending_family : "已完成"}</span>
            </div>
          ))}
        </div>
      )}

      <div className="toolbar" style={{ justifyContent: "center", marginTop: 18 }}>
        <button className="primary" disabled={view.pending_continuation || !e.continue_available}
          onClick={async () => {
            try {
              await api.continueWorld(sid);
            } catch (err: any) {
              toast(err.message);
            }
          }}>
          {view.pending_continuation ? "正在构思新篇章…" : "让故事继续"}
        </button>
        <button onClick={() => setState({ page: "feedback" })}>记录体验反馈</button>
        <button onClick={() => setState({ page: "home", sessionId: null })}>回到故事库</button>
      </div>
    </div>
  );
}

function WishDrawer({ sid, wishes, onClose }: {
  sid: string; wishes: Wish[]; onClose: () => void;
}) {
  const [text, setText] = useState("");
  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Wish / 许愿</h3>
        <p className="muted">希望会影响未来，不直接改变既有事实，也不保证实现。任何普通节点都可以表达。</p>
        <label><span>我的愿望</span>
          <textarea value={text} onChange={(e) => setText(e.target.value)} /></label>
        <div className="toolbar">
          <button className="primary" disabled={!text.trim()} onClick={async () => {
            try {
              await api.addWish(sid, text.trim());
              setText("");
              toast("愿望已记录。");
            } catch (e: any) {
              toast(e.message);
            }
          }}>记录愿望</button>
          <button onClick={onClose}>关闭</button>
        </div>
        <div className="divider" />
        {wishes.length === 0 ? <div className="empty">还没有愿望。</div> : wishes.map((w) => {
          const label = WISH_STATUS_LABEL[w.status] || w.status;
          const lastHistory = (w.history || []).slice(-1)[0];
          return (
            <div key={w.id} className="card">
              <div className="row">
                <b className="grow">{w.raw}</b>
                <span className={`badge ${w.status === "ACTIVE" ? "ok" :
                  w.status === "FULFILLED" ? "ok" : ""}`}>{label}</span>
              </div>
              <div className="muted">{w.effective_boundary} · {w.scope}</div>
              {lastHistory?.reason && (
                <div className="muted">最新：{lastHistory.reason}</div>
              )}
              {w.status === "ACTIVE" && (
                <div className="toolbar">
                  <button className="small" onClick={async () => {
                    await api.withdrawWish(sid, w.id);
                    toast("已撤回。");
                  }}>撤回</button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
