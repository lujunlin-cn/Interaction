/** 侧栏线性描边图标：统一 stroke 风格，继承 currentColor，尺寸由 CSS 控制。 */
import React from "react";

export type IconName =
  | "home" | "play" | "user" | "grid" | "target" | "book" | "layers"
  | "gear" | "image" | "chart" | "upload" | "spark" | "doc" | "search"
  | "bell" | "moon" | "dot" | "circle" | "drama" | "mechanic" | "branch"
  | "cache" | "route" | "runtime" | "video" | "assembly" | "trace"
  | "metric" | "qa" | "fixture" | "film" | "more" | "plus" | "back";

const PATHS: Record<IconName, React.ReactNode> = {
  // 场景
  home: <><path d="M4 11.5 12 4l8 7.5" /><path d="M6 9.8V20h12V9.8" /><path d="M10 20v-5h4v5" /></>,
  play: <path d="M7 5.5v13l11-6.5z" />,
  user: <><circle cx="12" cy="8.2" r="3.4" /><path d="M4.8 19.4c1.2-3.4 3.9-5.2 7.2-5.2s6 1.8 7.2 5.2" /></>,
  // 创作
  grid: <><rect x="4.5" y="4.5" width="6.4" height="6.4" rx="1.4" /><rect x="13.1" y="4.5" width="6.4" height="6.4" rx="1.4" /><rect x="4.5" y="13.1" width="6.4" height="6.4" rx="1.4" /><rect x="13.1" y="13.1" width="6.4" height="6.4" rx="1.4" /></>,
  target: <><circle cx="12" cy="12" r="7.4" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" /></>,
  book: <><path d="M5 5.6C6.6 4.9 8.5 4.9 12 6.3c3.5-1.4 5.4-1.4 7-0.7V18c-1.6-.7-3.5-.7-7 .7-3.5-1.4-5.4-1.4-7-.7z" /><path d="M12 6.3v12.4" /></>,
  layers: <><path d="M12 4 4.5 8.2 12 12.4l7.5-4.2z" /><path d="M4.5 12 12 16.2 19.5 12" /><path d="M4.5 15.8 12 20l7.5-4.2" /></>,
  gear: <><circle cx="12" cy="12" r="3" /><path d="M12 3.4v2.2M12 18.4v2.2M3.4 12h2.2M18.4 12h2.2M5.9 5.9l1.6 1.6M16.5 16.5l1.6 1.6M18.1 5.9l-1.6 1.6M7.5 16.5l-1.6 1.6" /></>,
  image: <><rect x="4" y="5" width="16" height="14" rx="1.6" /><circle cx="9" cy="10" r="1.5" /><path d="M4.5 16.5 9.5 12l3 3 3.5-3.5 4 4" /></>,
  chart: <><path d="M4.5 19.5v-9M9.5 19.5V7.5M14.5 19.5v-6M19.5 19.5V4.5" /></>,
  upload: <><path d="M12 15.5V5" /><path d="M7.5 9 12 4.5 16.5 9" /><path d="M5 15.5v3.6a1.4 1.4 0 0 0 1.4 1.4h11.2a1.4 1.4 0 0 0 1.4-1.4v-3.6" /></>,
  spark: <><path d="M12 4l1.7 4.6L18.5 10l-4.8 1.4L12 16l-1.7-4.6L5.5 10l4.8-1.4z" /><path d="M18 16l.8 2.2L21 19l-2.2.8L18 22l-.8-2.2L15 19l2.2-.8z" /></>,
  doc: <><path d="M6.5 4.5h7l4 4v11h-11z" /><path d="M13.5 4.5v4h4" /><path d="M9 12.5h6M9 15.5h6" /></>,
  // 顶部工具
  search: <><circle cx="11" cy="11" r="6" /><path d="M15.5 15.5 20 20" /></>,
  bell: <><path d="M6 16v-5.5a6 6 0 0 1 12 0V16l1.5 2.5H4.5z" /><path d="M10 18.5a2 2 0 0 0 4 0" /></>,
  moon: <path d="M19.5 13.5A7.5 7.5 0 1 1 10.5 4.5a6 6 0 0 0 9 9z" />,
  // 占位/圆点
  dot: <circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" />,
  circle: <circle cx="12" cy="12" r="5.5" />,
  // 创作子项 / 开发者
  drama: <><path d="M5 4.5h14v9a7 7 0 0 1-14 0z" /><path d="M8.5 9.5c.6 1.4 2 2.4 3.5 2.4s2.9-1 3.5-2.4" /><path d="M8.5 9.5h.01M15.5 9.5h.01" /></>,
  mechanic: <><circle cx="12" cy="12" r="3" /><path d="M12 4.5v-1M12 20.5v-1M4.5 12h-1M20.5 12h-1M6.7 6.7l-.7-.7M18 18l-.7-.7M17.3 6.7l.7-.7M6 18l.7-.7" /></>,
  branch: <><circle cx="6.5" cy="6.5" r="2" /><circle cx="6.5" cy="17.5" r="2" /><circle cx="17.5" cy="8.5" r="2" /><path d="M6.5 8.5v7M6.5 12.5c0-2.6 2-4 4.5-4h4.5" /></>,
  cache: <><ellipse cx="12" cy="6" rx="7" ry="2.4" /><path d="M5 6v12c0 1.3 3.1 2.4 7 2.4s7-1.1 7-2.4V6" /><path d="M5 12c0 1.3 3.1 2.4 7 2.4s7-1.1 7-2.4" /></>,
  route: <><path d="M4.5 7.5h11l-3-3" /><path d="M19.5 16.5h-11l3 3" /></>,
  runtime: <><rect x="4.5" y="4.5" width="15" height="15" rx="2" /><path d="M8.5 12h7M12 8.5v7" /></>,
  video: <><rect x="4" y="6.5" width="11.5" height="11" rx="1.6" /><path d="M15.5 10.8 20 8v8l-4.5-2.8" /></>,
  assembly: <><path d="M4.5 7h15M4.5 12h15M4.5 17h9" /></>,
  trace: <><path d="M4.5 18.5 9 10l3.5 5 3-7 4 10.5" /></>,
  metric: <><path d="M4.5 19.5h15" /><path d="M6 16l3.5-4 3 2.5 4-6 2 3" /></>,
  qa: <><path d="M12 4l7 2.5v4.7c0 4.4-3 7.6-7 8.8-4-1.2-7-4.4-7-8.8V6.5z" /><path d="M8.8 12l2.2 2.2 4.2-4.4" /></>,
  fixture: <><path d="M9 4.5h6M10.5 4.5V9l-4.5 8.4A1.6 1.6 0 0 0 7.4 20h9.2a1.6 1.6 0 0 0 1.4-2.6L13.5 9V4.5" /><path d="M8 14.5h8" /></>,
  film: <><rect x="4" y="5" width="16" height="14" rx="1.6" /><path d="M4 9.5h16M4 14.5h16M9 5v14M15 5v14" /></>,
  more: <><circle cx="6" cy="12" r="1.3" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none" /><circle cx="18" cy="12" r="1.3" fill="currentColor" stroke="none" /></>,
  plus: <><path d="M12 5.5v13M5.5 12h13" /></>,
  back: <><path d="M14.5 5.5 8 12l6.5 6.5" /></>,
};

export default function Icon({ name, size = 17 }: { name: IconName; size?: number }) {
  return (
    <svg className="ico" width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}
