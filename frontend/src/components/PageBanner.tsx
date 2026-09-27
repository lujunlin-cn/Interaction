/** 功能页顶部横幅：复用首页 hero 的深色电影感视觉，更矮更紧凑。 */
import React from "react";

export default function PageBanner({ image, kicker, title, sub, action }: {
  image: string; kicker: string; title: string; sub?: string; action?: React.ReactNode;
}) {
  return (
    <section className="page-banner">
      <div className="page-banner-bg" style={{ backgroundImage: `url(${image})` }} />
      <div className="page-banner-overlay" />
      <div className="page-banner-content">
        <div className="page-banner-kicker">{kicker}</div>
        <h2 className="page-banner-title">{title}</h2>
        {sub && <p className="page-banner-sub">{sub}</p>}
        {action && <div className="page-banner-action">{action}</div>}
      </div>
    </section>
  );
}
