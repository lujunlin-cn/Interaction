/** Player：视频场景 + Ready 推荐 + 限时互动 + 自由输入 + 意图回显 + Wish。
 *
 * 术语隔离：普通玩家只看到自然中文状态（“正在生成画面”），
 * PROVISIONAL / CANONICAL 等技术词只在开发者视图出现。
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { api, sessionSocket } from "../api";
import { setState, toast, useUi } from "../store";
import type { PendingIntent, PlayerView, Wish } from "../types";

const WISH_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "生效中", DEFERRED: "已延期", CONFLICTED: "与规则冲突",
  FULFILLED: "已实现", PARTIALLY_FULFILLED: "部分实现", FAILED: "未能实现",
  SUPERSEDED: "被替换", WITHDRAWN: "已撤回",
};

export default function Player() {
  const ui = useUi();
  const sid = ui.sessionId;
  const [view, setView] = useState<PlayerView | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [ack, setAck] = useState<string | null>(null);
  const [wishOpen, setWishOpen] = useState(false);
  const [popover, setPopover] = useState<string | null>(null);
  const [replay, setReplay] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const receiptSent = useRef<string>("");
  // 倒计时本地基线：以服务端 remaining_ms 为准，本地只做渲染插值
  const [timedBase, setTimedBase] = useState<{ remaining: number; at: number } | null>(null);
  const [now, setNow] = useState(Date.now());

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

  // 倒计时插值时钟
  useEffect(() => {
    if (!view?.timed?.active) return;
    const t = window.setInterval(() => setNow(Date.now()), 200);
    return () => window.clearInterval(t);
  }, [view?.timed?.active]);

  useEffect(() => {
    const t = view?.timed;
    if (t?.active && t.remaining_ms != null) {
      setTimedBase({ remaining: t.remaining_ms, at: Date.now() });
    } else {
      setTimedBase(null);
    }
    // 只在服务端值刷新时重置基线
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view?.timed?.remaining_ms, view?.timed?.active]);

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

  const timedRemaining = useMemo(() => {
    if (!view?.timed?.active || !timedBase) return null;
    return Math.max(0, timedBase.remaining - (now - timedBase.at));
  }, [view?.timed?.active, timedBase, now]);

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
  const leadReached = p.lead <= 0 || p.position >= p.lead;
  const wishesActive = view.wishes.filter((w) => w.status === "ACTIVE");

  const submitAction = async (preset?: string) => {
    const text = (preset ?? input).trim();
    if (!text || busy) return;
    setBusy(true);
    setAck(null);
    try {
      const r = await api.freeAction(sid, text);
      if (r.status === "QUICK_ACK") setAck(r.ack ?? "好的。");
      // INTENT_ECHO / CLARIFICATION_REQUIRED 由 view.pending_intent 渲染（WS 推送）
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

  const cancelGeneration = async () => {
    try {
      const r = await api.cancelGeneration(sid);
      toast(r.status === "CANCELLED" ? "已取消当前生成。" : "当前没有正在生成的内容。");
    } catch (e: any) {
      toast(e.message);
    }
  };

  return (
    <div className="player-shell">
      {/* 头部：标题 + 扮演角色 + 篇章 + 退出 */}
      <div className="player-head">
        <div className="grow">
          <b>{view.scenario.title}</b>
          <span className="player-head-sub">
            你扮演：{view.scenario.player_identity.split(" / ")[0]} · 第 {view.arc.seq} 篇章
          </span>
        </div>
        <button className="small" onClick={() => setState({ page: "home", sessionId: null })}>
          退出
        </button>
      </div>

      {/* 工具栏：背包 / 信任值 / 线索 / 愿望 */}
      <div className="player-tools">
        <ToolButton icon="🎒" label="背包" count={view.known.inventory.length}
          open={popover === "bag"} onToggle={() => setPopover(popover === "bag" ? null : "bag")}>
          {view.known.inventory.length === 0
            ? <div className="muted">还没有拿到任何物品。</div>
            : view.known.inventory.map((it) => <div key={it} className="tool-line">{it}</div>)}
        </ToolButton>
        <ToolButton icon="♡" label="信任值" count={view.known.relationships.length}
          open={popover === "rel"} onToggle={() => setPopover(popover === "rel" ? null : "rel")}>
          {view.known.relationships.length === 0
            ? <div className="muted">还没有建立关系变化。</div>
            : view.known.relationships.map((r) => (
              <div key={r.id} className="tool-line">
                {r.name}<span className="muted">　信任 {r.value} / 100</span>
                <span className="rel-bar"><span style={{ width: `${Math.min(100, r.value)}%` }} /></span>
              </div>
            ))}
        </ToolButton>
        <ToolButton icon="🔎" label="线索" count={view.known.clues.length}
          open={popover === "clue"} onToggle={() => setPopover(popover === "clue" ? null : "clue")}>
          {view.known.clues.length === 0 && view.known.knowledge.length === 0
            ? <div className="muted">还没有发现线索。</div>
            : [...view.known.clues, ...view.known.knowledge]
              .filter((c, i, arr) => arr.findIndex((x) => x.id === c.id) === i)
              .map((c) => <div key={c.id} className="tool-line">{c.label}</div>)}
        </ToolButton>
        <ToolButton icon="✨" label="愿望" count={wishesActive.length}
          open={popover === "wish"} onToggle={() => setPopover(popover === "wish" ? null : "wish")}>
          {wishesActive.length === 0
            ? <div className="muted">还没有愿望。愿望会影响未来，但不保证实现。</div>
            : wishesActive.map((w) => <div key={w.id} className="tool-line">{w.raw}</div>)}
          <button className="small" style={{ marginTop: 8 }}
            onClick={() => { setPopover(null); setWishOpen(true); }}>许下新愿望</button>
        </ToolButton>
      </div>

      <div className="player-stage">
        {replay ? (
          <video key={replay} src={replay} autoPlay controls
            onEnded={() => setReplay(null)} />
        ) : p.video_url ? (
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
                : p.status === "LOADING" ? "正在载入场景…"
                : p.scene_text ? "" : "场景将在准备好后播放"}
            </div>
            {p.scene_text && <div className="player-textonly">{p.scene_text}</div>}
          </div>
        )}
        {!replay && (p.scene_title || p.scene_text) && p.video_url && (
          <div className="scene-caption">
            <div className="scene-title">{p.scene_title}</div>
            <div className="scene-text">{p.scene_text}</div>
          </div>
        )}
        {replay && (
          <button className="small replay-close" onClick={() => setReplay(null)}>返回当前场景</button>
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
        {view.generating.length > 0 && (
          <button className="small" onClick={cancelGeneration}>取消生成</button>
        )}
        <button className="small" onClick={() => setState({ inspectorOpen: !ui.inspectorOpen })}>
          {ui.inspectorOpen ? "收起检查器" : "检查器"}
        </button>
      </div>

      {ack && <div className="ack-toast">{ack}</div>}

      {/* G27：自由输入失败恢复——重试 / 修改后重发 / 放弃 */}
      {view.last_failed_action && (
        <div className="notice" style={{ borderColor: "#7a4a4a", marginTop: 8 }}>
          <div className="row">
            <span className="grow">
              上一次行动「{view.last_failed_action.label}」没有成功
              {view.last_failed_action.error ? `（${view.last_failed_action.error}）` : "。"}
            </span>
            <button className="small" onClick={() => {
              setInput(view.last_failed_action!.raw_text || "");
            }}>修改后重发</button>
            <button className="small" disabled={busy} onClick={async () => {
              const text = view.last_failed_action!.raw_text;
              if (!text) return;
              setBusy(true);
              try {
                const r = await api.freeAction(sid, text);
                if (r.status === "QUICK_ACK") setAck(r.ack ?? "好的。");
              } catch (e: any) { toast(e.message); }
              finally { setBusy(false); }
            }}>重试</button>
          </div>
        </div>
      )}

      {/* 小动作反馈流 */}
      {view.messages.length > 0 && (
        <div className="msg-list">
          {view.messages.slice(-4).map((m, i) => (
            <div key={`${m.at}-${i}`} className={`msg-line ${m.kind}`}>{m.text}</div>
          ))}
        </div>
      )}

      {/* 意图回显 / 澄清卡（FR-046：玩家确认或修改理解后才会生成） */}
      {view.pending_intent && <IntentCard sid={sid} intent={view.pending_intent} />}

      {view.ended && view.ending ? (
        <EndingPanel sid={sid} view={view} onReplay={(url) => setReplay(url)} />
      ) : (
        <>
          {/* 限时互动（TIMED）：倒计时 + 选项 + 确定性结果提示 */}
          {view.timed?.active && (
            <div className="qte-composer">
              <div className="qte-count">
                {timedRemaining != null ? Math.ceil(timedRemaining / 1000) : "…"}
              </div>
              <div className="qte-body">
                <b>需要立刻作出反应</b>
                <div className="muted" style={{ color: "#c9b06a" }}>
                  {view.timed.fallback_hint}
                </div>
              </div>
            </div>
          )}

          {/* 已选收起 */}
          {view.selected && view.selected.status !== "CANONICAL" ? (
            <div className="notice" style={{ marginTop: 14 }}>
              ✓ 你已选择「{view.selected.label}」，其他选项已收起。故事正在为你生成…
            </div>
          ) : (
            <>
              <div className="player-section-title">
                {view.timed?.active ? "在倒计时结束前选择——" : "接下来，你可以——"}
              </div>
              {view.recommendations.length > 0 ? (
                view.timed?.active && !view.timed.selection_open ? (
                  <div className="muted" style={{ color: "#9fb0c0" }}>选项正在准备中…</div>
                ) : (
                  <div className="rec-row">
                    {view.recommendations.map((r) => (
                      <button key={r.branch_id} className="rec-card" onClick={() => choose(r.branch_id)}>
                        <div className="rec-label">{r.label}</div>
                        <div className="rec-summary">{r.summary}</div>
                      </button>
                    ))}
                  </div>
                )
              ) : (
                <div className="muted" style={{ color: "#9fb0c0" }}>
                  {view.generating.length > 0
                    ? "推荐正在准备中…"
                    : leadReached
                      ? "暂无推荐，试试自由输入。"
                      : "继续观看，临近分岔点时会出现可选行动。"}
                </div>
              )}
              {!leadReached && view.recommendations.length === 0 && view.generating.length === 0 && (
                <button className="small" style={{ marginTop: 6 }}
                  onClick={() => api.playerCommand(sid, "skip").catch(() => {})}>
                  重新准备建议
                </button>
              )}
            </>
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

          {!view.timed?.active && (
            <>
              <div className="player-section-title">或者，按你自己的想法行动</div>
              {view.hint_chips.length > 0 && (
                <div className="chips-row">
                  <span className="muted" style={{ color: "#9fb0c0" }}>试试这些输入：</span>
                  {view.hint_chips.map((c) => (
                    <button key={c} className="chip" onClick={() => submitAction(c)}>{c}</button>
                  ))}
                </div>
              )}
              <div className="free-input-row">
                <input
                  value={input}
                  placeholder="描述你想做的事，例如：我绕到后院去看看"
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") submitAction(); }}
                  disabled={busy}
                />
                <button className="primary" onClick={() => submitAction()} disabled={busy || !input.trim()}>
                  {busy ? "正在理解…" : "行动"}
                </button>
              </div>
            </>
          )}
        </>
      )}

      <button className="wish-fab" onClick={() => setWishOpen(true)}>许愿</button>
      {wishOpen && (
        <WishDrawer sid={sid} wishes={view.wishes} onClose={() => setWishOpen(false)} />
      )}
    </div>
  );
}

/** 工具栏按钮 + 弹出面板 */
function ToolButton({ icon, label, count, open, onToggle, children }: {
  icon: string; label: string; count: number; open: boolean;
  onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <span className="tool-wrap">
      <button className={`tool-btn ${open ? "active" : ""}`} onClick={onToggle}>
        {icon} {label} <b>{count}</b>
      </button>
      {open && <div className="tool-popover" onClick={(e) => e.stopPropagation()}>{children}</div>}
    </span>
  );
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
  const e = view.ending!;
  return (
    <div className="ending-panel">
      <h2 style={{ color: "#e8edf2" }}>第 {view.arc.seq} 篇章完 · {e.title}</h2>

      <div className="ending-grid">
        <div className="ending-card">
          <h3>会继续保留</h3>
          {e.carried.relationships.map((r) => (
            <div key={r.id} className="tool-line">{r.name}　<span className="muted">信任 {r.value}</span></div>
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
              第 {a.seq} 篇章 <span className="muted">{a.ending_family ?? ""}</span>
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
