/** 体验反馈：结构化反馈（对应 PRD PlayerExperienceFeedback）。 */
import React, { useState } from "react";
import { api } from "../api";
import { toast, useUi } from "../store";

export default function Feedback() {
  const ui = useUi();
  const [form, setForm] = useState({
    name: "", relation: "", guided: "", liked: "", reasons: "",
    relevant_turn: "", wants_continue: "",
  });
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });
  return (
    <div className="card">
      <h3>体验反馈</h3>
      <div className="two">
        <label><span>你的称呼</span><input value={form.name} onChange={set("name")} /></label>
        <label><span>你与这个故事的关系</span>
          <input value={form.relation} onChange={set("relation")} placeholder="玩家 / 作者 / 观察者…" /></label>
      </div>
      <label><span>你感觉被引导了吗？</span>
        <textarea value={form.guided} onChange={set("guided")} /></label>
      <label><span>你最喜欢的部分 *</span>
        <textarea value={form.liked} onChange={set("liked")} /></label>
      <label><span>为什么？ *</span>
        <textarea value={form.reasons} onChange={set("reasons")} /></label>
      <label><span>印象最深的回合</span>
        <input value={form.relevant_turn} onChange={set("relevant_turn")} /></label>
      <label><span>想继续这个世界吗？</span>
        <input value={form.wants_continue} onChange={set("wants_continue")} /></label>
      <button className="primary" disabled={!form.liked || !form.reasons} onClick={async () => {
        try {
          await api.submitFeedback({ ...form, session_id: ui.sessionId ?? "" });
          toast("感谢反馈！");
          setForm({ name: "", relation: "", guided: "", liked: "", reasons: "", relevant_turn: "", wants_continue: "" });
        } catch (e: any) {
          toast(e.message);
        }
      }}>提交反馈</button>
    </div>
  );
}
