/** Player：视频场景 + Ready 推荐 + 自由输入 + Wish。
 *
 * 术语隔离：普通玩家只看到自然中文状态（“正在生成画面”），
 * PROVISIONAL / CANONICAL 等技术词只在开发者视图出现。
 */
import React, { useEffect, useRef, useState } from "react";
import { api, sessionSocket } from "../api";
import { setState, toast, useUi } from "../store";
import type { PlayerView, Wish } from "../types";

export default function Player() {
  const ui = useUi();
  const sid = ui.sessionId;
  const [view, setView] = useState<PlayerView | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [ack, setAck] = useState<string | null>(null);
  const [clarify, setClarify] = useState<string | null>(null);
  const [wishOpen, setWishOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const receiptSent = useRef<string>("");

  useEffect(() => {
    if (!sid) return;
    let closed = false;
    api.sessionView(sid).then((v) => !closed && setView(v)).catch(() => {});
    const ws = sessionSocket(sid, (msg) => {
      if (msg.type === "state") setView(msg.view);
    });
    // WS 断线兜底轮询
    const timer = window.setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        api.sessionView(sid).then(setView).catch(() => {});
      }
    }, 2500);
    return () => {
      closed = true;
      window.clearInterval(timer);
      ws.close();
    };
  }, [sid]);

  // 场景播完：上报 receipt（只上报一次）
  useEffect(() => {
    if (!sid || !view) return;
    const p = view.player;
    const key = `${sid}:${p.scene_title}:${p.duration}`;
    if (p.status === "READY" && p.video_url && receiptSent.current !== key) {
      receiptSent.current = key;
      api.commitReceipt(sid).catch(() => {});
    }
  }, [sid, view]);

  if (!sid) {
    return (
      <div className="player-shell">
        <div className="empty" style={{ marginTop: 60 }}>
          还没有进行中的游玩。请从「故事库」选择一个世界开始。
        </div>
      </div>
    );
  }
  if (!view) {
    return <div className="player-shell"><div className="player-placeholder">正在载入…</div></div>;
  }

  const p = view.player;
  const progress = p.duration > 0 ? Math.min(100, (p.position / p.duration) * 100) : 0;

  const submitAction = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setAck(null);
    setClarify(null);
    try {
      const r = await api.freeAction(sid, text);
      if (r.status === "QUICK_ACK") setAck(r.ack ?? "好的。");
      else if (r.status === "CLARIFICATION_REQUIRED") setClarify(r.question ?? "你具体想怎么做？");
      setInput("");
    } catch (e: any) {
      toast(e.message);
    } finally {
      setBusy(false);
    }
  };

  const choose = async (branchId: string) => {
    try {
      await api.selectBranch(sid, branchId);
    } catch (e: any) {
      toast(e.message);
    }
  };

  return (
    <div className="player-shell">
      <div className="player-stage">
        {p.video_url ? (
          <video
            key={p.video_url}
            ref={videoRef}
            src={p.video_url}
            autoPlay
            onPlay={() => api.playerCommand(sid, "play").catch(() => {})}
            onPause={() => api.playerCommand(sid, "pause").catch(() => {})}
            onEnded={() => api.playerCommand(sid, "skip").catch(() => {})}
          />
        ) : (
          <div className="player-placeholder">
            <div style={{ fontSize: 40 }}>▶</div>
            <div>
              {view.generating.length > 0
                ? "正在为你准备接下来的故事…"
                : p.status === "LOADING" ? "正在载入场景…" : "场景将在准备好后播放"}
            </div>
          </div>
        )}
        {(p.scene_title || p.scene_text) && (
          <div className="scene-caption">
            <div className="scene-title">{p.scene_title}</div>
            <div className="scene-text">{p.scene_text}</div>
          </div>
        )}
      </div>
      <div className="player-progress"><div style={{ width: `${progress}%` }} /></div>
      <div className="player-controls">
        <button className="small" onClick={() => {
          const v = videoRef.current;
          if (v) v.paused ? v.play() : v.pause();
        }}>播放 / 暂停</button>
        <button className="small" onClick={() => api.playerCommand(sid, "skip").catch(() => {})}>
          跳过当前场景
        </button>
        <span className="muted" style={{ color: "#9fb0c0" }}>
          {p.status === "PLAYING" ? "正在播放" :
            p.status === "READY" ? "场景已播完，选择下一步" :
            p.status === "ENDED" ? "本篇已结束" :
            p.status === "FAILED" ? "生成遇到问题" : "正在准备"}
        </span>
        <span style={{ flex: 1 }} />
        <button className="small" onClick={() => setState({ inspectorOpen: !ui.inspectorOpen })}>
          {ui.inspectorOpen ? "收起检查器" : "检查器"}
        </button>
      </div>

      {ack && <div className="ack-toast">{ack}</div>}
      {clarify && (
        <div className="ack-toast">我想确认一下：{clarify}</div>
      )}

      {view.ended ? (
        <div className="player-ended">
          <h2 style={{ color: "#e8edf2" }}>本篇完</h2>
          <p style={{ color: "#9fb0c0" }}>这段矛盾已经收束。你可以让这个世界继续下去。</p>
          <div className="toolbar" style={{ justifyContent: "center" }}>
            <button className="primary" disabled={view.pending_continuation}
              onClick={async () => {
                try {
                  await api.continueWorld(sid);
                } catch (e: any) {
                  toast(e.message);
                }
              }}>
              {view.pending_continuation ? "正在构思新篇章…" : "让故事继续"}
            </button>
            <button onClick={() => setState({ page: "home", sessionId: null })}>回到故事库</button>
          </div>
        </div>
      ) : (
        <>
          <div className="player-section-title">接下来，你可以——</div>
          {view.recommendations.length > 0 ? (
            <div className="rec-row">
              {view.recommendations.map((r) => (
                <button key={r.branch_id} className="rec-card" onClick={() => choose(r.branch_id)}>
                  <div className="rec-label">{r.label}</div>
                  <div className="rec-summary">{r.summary}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="muted" style={{ color: "#9fb0c0" }}>
              {view.generating.length > 0 ? "推荐正在准备中…" : "暂无推荐，试试自由输入。"}
            </div>
          )}
          {view.generating.length > 0 && (
            <div className="generating-row">
              {view.generating.map((g) => (
                <span key={g.branch_id} className="generating-chip">
                  {g.phase_label || "正在准备"} · {g.label}
                </span>
              ))}
            </div>
          )}

          <div className="player-section-title">或者，按你自己的想法行动</div>
          <div className="free-input-row">
            <input
              value={input}
              placeholder="描述你想做的事，例如：我绕到后院去看看"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") submitAction(); }}
              disabled={busy}
            />
            <button className="primary" onClick={submitAction} disabled={busy || !input.trim()}>
              {busy ? "正在理解…" : "行动"}
            </button>
          </div>
        </>
      )}

      <button className="wish-fab" onClick={() => setWishOpen(true)}>许愿</button>
      {wishOpen && (
        <WishDrawer sid={sid} wishes={view.wishes} onClose={() => setWishOpen(false)} />
      )}
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
        {wishes.length === 0 ? <div className="empty">还没有愿望。</div> : wishes.map((w) => (
          <div key={w.id} className="card">
            <div className="row">
              <b className="grow">{w.raw}</b>
              <span className={`badge ${w.status === "ACTIVE" ? "ok" : ""}`}>{w.status}</span>
            </div>
            <div className="muted">{w.effective_boundary} · {w.scope}</div>
            {w.status === "ACTIVE" && (
              <div className="toolbar">
                <button className="small" onClick={async () => {
                  await api.withdrawWish(sid, w.id);
                  toast("已撤回。");
                }}>撤回</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
