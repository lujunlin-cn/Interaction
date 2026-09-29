/** 故事库：图二风格 —— Hero（主标题+输入框+创建）+ 最近的故事卡片网格 + 官方示例。
 * 玩家态（mode=player）：Hero 聚焦「开始游玩」，隐藏创作/编辑/删除入口。 */
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { setState, toast, useUi } from "../store";
import Icon from "../components/Icon";
import type { ScenarioDraft } from "../types";

const MECHANIC_LABELS: Record<string, string> = {
  relationship: "关系变化", "clue-system": "线索调查", inventory: "道具系统", qte: "限时互动",
};

/** 故事卡片封面映射：真实故事按 id 取封面，取不到用占位渐变。 */
const COVER_BY_ID: Record<string, string> = {
  rainy_apartment: "/img/images/cover-rainy.png",
  scn_00003_364d7e: "/img/images/cover-biohazard.png",
};
const SAMPLE_COVERS = [
  "/img/images/cover-sample1.png", "/img/images/cover-sample2.png",
  "/img/images/cover-sample3.png", "/img/images/cover-sample4.png",
];
/** 官方示例（图二底部一排，静态展示）。 */
const OFFICIAL_SAMPLES = [
  { title: "城市边缘", cover: SAMPLE_COVERS[0], genre: "都市" },
  { title: "东京夜行", cover: SAMPLE_COVERS[1], genre: "冒险" },
  { title: "深夜书房", cover: SAMPLE_COVERS[2], genre: "治愈" },
  { title: "海平线", cover: SAMPLE_COVERS[3], genre: "青春" },
];

/** 最近的故事：固定展示数量（含「新建故事」占位卡）。 */
const RECENT_TOTAL = 4;
/** 真实故事不足时用于补齐一排的静态示例卡。 */
const FILLER_CARDS = [
  {
    title: "夏日回声", cover: "/img/images/cover-summer.png", tags: ["青春", "成长"],
    desc: "三位性格迥异的少女在毕业前的最后一个夏天…", chars: 4, scenes: 8,
  },
  {
    title: "海平线", cover: SAMPLE_COVERS[3], tags: ["青春", "治愈"],
    desc: "沿着海岸线骑行七天，把说不出口的话留给风…", chars: 2, scenes: 5,
  },
];

export default function Home() {
  const ui = useUi();
  const isPlayer = ui.mode === "player";
  const [items, setItems] = useState<ScenarioDraft[]>([]);
  const [versions, setVersions] = useState<Record<string, string>>({});
  const [importing, setImporting] = useState(false);
  const [importText, setImportText] = useState("");
  const [idea, setIdea] = useState("");
  const starting = useRef(false);
  const [startingId, setStartingId] = useState<string | null>(null);

  const reload = () => {
    api.listScenarios().then(async (r) => {
      setItems(r.items);
      const map: Record<string, string> = {};
      for (const sc of r.items) {
        try {
          const v = await api.scenarioVersions(sc.id);
          if (v.items.length) map[sc.id] = v.items[0].version_id;
        } catch { /* ignore */ }
      }
      setVersions(map);
    }).catch((e) => toast(`加载故事库失败：${e.message}`));
  };
  useEffect(reload, []);

  const createStory = async (withIdea?: string) => {
    try {
      const draft = await api.createScenario(withIdea ?? "");
      setState({ editId: draft.id, page: "creator", creatorTab: "overview" });
    } catch (e: any) {
      toast(`创建失败：${e.message}`);
    }
  };

  const startPlay = async (sc: ScenarioDraft) => {
    if (starting.current) return;
    starting.current = true;
    setStartingId(sc.id);
    // 在“开始游玩”的真实点击手势内请求浏览器全屏。播放器随后挂载到同一个
    // appframe，避免等异步创建 Session 后再请求而被浏览器拦截。
    const appframe = document.querySelector<HTMLElement>(".appframe");
    if (appframe && !document.fullscreenElement && appframe.requestFullscreen) {
      void appframe.requestFullscreen().catch(() => {
        // 浏览器策略或测试环境不允许全屏时，应用剧场模式仍会正常工作。
      });
    }
    try {
      // 库页面挂起期间发布可能已变化：在用户动作边界重新解析最新版本。
      const latest = await api.scenarioVersions(sc.id);
      const versionId = latest.items[0]?.version_id;
      if (!versionId) {
        toast("请先完成发布，试玩会使用最近一次发布的故事版本。");
        setState({ editId: sc.id, page: "creator", creatorTab: "publish" });
        return;
      }
      const { session_id } = await api.createSession(versionId);
      setState({ sessionId: session_id, scenarioVersionId: versionId, page: "player" });
    } catch (e: any) {
      toast(`开始游玩失败：${e.message}`);
    } finally {
      starting.current = false;
      setStartingId(null);
    }
  };

  const coverOf = (sc: ScenarioDraft, i: number) =>
    COVER_BY_ID[sc.id] ?? SAMPLE_COVERS[i % SAMPLE_COVERS.length];

  return (
    <div className="home-v2">
      {/* ===== Hero ===== */}
      <section className="hero">
        <div className="hero-bg" style={{ backgroundImage: "url(/img/images/hero.png)" }} />
        <div className="hero-overlay" />
        <div className="hero-content">
          <div className="hero-kicker">INTERACTIVE DRAMA</div>
          <h1 className="hero-title">{isPlayer ? <>选择一个世界<br />开始你的故事</> : <>用 AI 讲好<br />每一个值得被体验的故事</>}</h1>
          <p className="hero-sub">{isPlayer ? "每个故事都会回应你的选择；没有标准答案。" : "从灵感到世界，让角色在你构建的故事中真实存在。"}</p>

          {isPlayer ? (
            <div className="hero-create">
              <button className="hero-cta" onClick={() => setState({ mode: "creator", page: "creator", creatorTab: "overview" })}>
                亲手创作 <span className="hero-cta-arrow">→</span>
              </button>
              {ui.sessionId && (
                <button className="hero-tag" onClick={() => setState({ page: "player" })}>
                  <Icon name="play" size={15} /> 继续当前游玩
                </button>
              )}
            </div>
          ) : (
            <div className="hero-create">
              <div className="hero-inputwrap">
                <span className="hero-input-ico"><Icon name="spark" size={16} /></span>
                <input
                  className="hero-input"
                  placeholder="描述一个世界，或者手动创建…"
                  value={idea}
                  onChange={(e) => setIdea(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") createStory(idea); }}
                />
              </div>
              <button className="hero-cta" onClick={() => createStory(idea)}>
                创建故事 <span className="hero-cta-arrow">→</span>
              </button>
            </div>
          )}

          <div className="hero-tags">
            <button className="hero-tag" onClick={() => toast("参考图上传即将上线")}><Icon name="image" size={15} /> 参考图</button>
            <button className="hero-tag" onClick={() => setState({ page: "characterLibrary", globalCharacterId: null })}><Icon name="user" size={15} /> 角色</button>
            <button className="hero-tag" onClick={() => toast("风格选择即将上线")}><Icon name="spark" size={15} /> 风格</button>
            <button className="hero-tag" onClick={() => toast("世界观模板即将上线")}><Icon name="target" size={15} /> 世界观</button>
          </div>
        </div>
      </section>

      {/* ===== 最近的故事 ===== */}
      <section className="home-section">
        <div className="section-head">
          <h2 className="section-title">最近的故事 <span className="section-chevron">›</span></h2>
          <div className="section-tools">
            {ui.mode === "developer" && (
              <button className="view-toggle" title="导入故事" onClick={() => setImporting(true)}><Icon name="upload" size={15} /></button>
            )}
            <span className="section-link">全部故事 ›</span>
            <button className="view-toggle active" title="网格"><Icon name="grid" size={15} /></button>
            <button className="view-toggle" title="列表"><Icon name="assembly" size={15} /></button>
          </div>
        </div>

        <div className="story-grid">
          {/* 新建故事占位卡：固定排最左（玩家态隐藏，只展示可游玩故事） */}
          {!isPlayer && (
          <article className="story-card story-new" onClick={() => createStory()}>
            <div className="story-cover story-new-cover" style={{ backgroundImage: "url(/img/images/cover-mountain.png)" }}>
              <div className="story-new-inner">
                <div className="story-new-plus"><Icon name="plus" size={30} /></div>
                <div className="story-new-title">新建故事</div>
                <div className="story-new-sub">从一个想法开始，创造属于你的世界。</div>
              </div>
            </div>
          </article>
          )}

          {[...items]
            .sort((a, b) => Number(b.status === "PUBLISHED") - Number(a.status === "PUBLISHED"))
            .slice(0, isPlayer ? RECENT_TOTAL : RECENT_TOTAL - 1)
            .map((sc, i) => (
            <article key={sc.id} className="story-card">
              <div className="story-cover" style={{ backgroundImage: `url(${coverOf(sc, i)})` }}>
                {sc.status === "PUBLISHED" && <span className="story-badge"><Icon name="plus" size={11} /> 已发布</span>}
              </div>
              <div className="story-body">
                <div className="story-titlerow">
                  <h3 className="story-name">{sc.title}</h3>
                  <div className="story-tags">
                    {sc.genre && <span className="story-tag">{sc.genre}</span>}
                    <span className="story-tag dim">{sc.owner === "official" ? "官方故事" : "我的故事"}</span>
                  </div>
                </div>
                <p className="story-desc">{sc.description || "尚未填写故事简介"}</p>
                <div className="story-meta">
                  <span><Icon name="user" size={13} /> {sc.characters?.length ?? 0} 个角色</span>
                  <span><Icon name="film" size={13} /> {Object.keys(sc.world?.locations?.split("\n") ?? {}).length || "—"} 个场景</span>
                </div>
                <div className="story-actions">
                  <button className="primary" disabled={startingId !== null || (!versions[sc.id] && sc.status !== "PUBLISHED")}
                    onClick={() => startPlay(sc)}>{startingId === sc.id ? "正在进入…" : "开始游玩"}</button>
                  {!isPlayer && (
                    <>
                      <button onClick={() => setState({ editId: sc.id, page: "creator", creatorTab: "overview" })}>编辑</button>
                      <button onClick={async () => {
                        try {
                          await api.duplicateScenario(sc.id);
                          toast("已创建副本。");
                          reload();
                        } catch (e: any) {
                          toast(`复制失败：${e.message}`);
                        }
                      }}>复制</button>
                      {sc.owner !== "official" && (
                        <button className="danger" onClick={async () => {
                          if (!window.confirm(`确定删除「${sc.title}」？此操作不可撤销。`)) return;
                          try {
                            await api.deleteScenario(sc.id);
                            toast("已删除。");
                            window.dispatchEvent(new Event("plotshift:library-changed"));
                            if (ui.editId === sc.id) setState({ editId: null });
                            reload();
                          } catch (e: any) {
                            toast(`删除失败：${e.message}`);
                          }
                        }}>删除</button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </article>
          ))}

          {/* 真实故事不足一排时用静态示例卡补齐 */}
          {FILLER_CARDS.slice(0, Math.max(0, (isPlayer ? RECENT_TOTAL : RECENT_TOTAL - 1) - items.length)).map((f) => (
            <article key={f.title} className="story-card">
              <div className="story-cover" style={{ backgroundImage: `url(${f.cover})` }}></div>
              <div className="story-body">
                <div className="story-titlerow">
                  <h3 className="story-name">{f.title}</h3>
                  <div className="story-tags">
                    <span className="story-tag">{f.tags[0]}</span>
                    <span className="story-tag dim">{f.tags[1]}</span>
                  </div>
                </div>
                <p className="story-desc">{f.desc}</p>
                <div className="story-meta"><span><Icon name="user" size={13} /> {f.chars} 个角色</span><span><Icon name="film" size={13} /> {f.scenes} 个场景</span></div>
                <div className="story-actions">
                  <button className="primary" onClick={() => toast("示例故事即将上线")}>开始游玩</button>
                  {!isPlayer && <button onClick={() => toast("示例故事即将上线")}>编辑</button>}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ===== 官方示例 ===== */}
      <section className="home-section">
        <div className="section-head">
          <h2 className="section-title">官方示例 <span className="section-chevron">›</span></h2>
          <span className="section-link">更多灵感，创造更多可能</span>
        </div>
        <div className="sample-row">
          {OFFICIAL_SAMPLES.map((s) => (
            <div key={s.title} className="sample-card" onClick={() => toast("示例故事即将上线")}>
              <div className="sample-cover" style={{ backgroundImage: `url(${s.cover})` }} />
              <div className="sample-name">{s.title}</div>
            </div>
          ))}
        </div>
      </section>

      {importing && (
        <div className="modal-mask" onClick={() => setImporting(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>导入故事</h3>
            <p className="muted">粘贴 Scenario JSON。导入不会执行任何包内代码；发布前仍需校验和审阅。</p>
            <textarea value={importText} onChange={(e) => setImportText(e.target.value)}
              placeholder='{"title": "...", "world": {...}, "drama": {...}, "characters": [...], "mechanics": {...}}' />
            <div className="toolbar">
              <button onClick={() => setImporting(false)}>取消</button>
              <button className="primary" onClick={async () => {
                try {
                  const data = JSON.parse(importText);
                  validateImport(data);
                  const draft = await api.createScenario();
                  await api.saveScenario({ ...draft, ...data, id: draft.id, status: "DRAFT" });
                  setImporting(false);
                  toast("已导入草案。");
                  setState({ editId: draft.id, page: "creator", creatorTab: "publish" });
                  reload();
                } catch (e: any) {
                  toast(`导入失败：${e.message}`);
                }
              }}>导入</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function validateImport(data: any) {
  const scan = (v: any, path = "root") => {
    if (v && typeof v === "object") {
      for (const [k, x] of Object.entries(v)) {
        if (["__proto__", "constructor", "prototype", "scripts", "executable", "shell"].includes(k)) {
          throw new Error(`不允许可执行字段或危险键：${k}`);
        }
        if ((k.endsWith("path") || k.endsWith("_ref")) && typeof x === "string"
          && /(\.\.\/|^\/|^[A-Za-z]:)/.test(x)) {
          throw new Error("不允许路径穿越或绝对路径");
        }
        scan(x, `${path}.${k}`);
      }
    }
  };
  scan(data);
  const sc = data.scenario || data;
  if (!sc.title || !sc.world || !sc.drama || !Array.isArray(sc.characters)) {
    throw new Error("缺少 Scenario 必需的 typed fields");
  }
}
