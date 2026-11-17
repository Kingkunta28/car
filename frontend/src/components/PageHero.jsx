import { cx } from "../lib/format";

/**
 * Inner-page header. Each page picks a tone so pages feel related but distinct:
 *  - "sand": light editorial (Fleet, Before You Rent)
 *  - "navy": dark statement (About)
 *  - "plain": minimal (forms, legal)
 */
export default function PageHero({ eyebrow, title, accent, lead, tone = "sand", aside, children }) {
  const dark = tone === "navy";
  return (
    <section className={cx("relative overflow-hidden",
      tone === "sand" && "border-b border-line bg-sand-50", dark && "grain bg-navy-950 text-white", tone === "plain" && "bg-white")}>
      {dark && <div className="hairline-grid pointer-events-none absolute inset-0" aria-hidden />}
      {tone === "sand" && <div className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full bg-orange-100/70 blur-3xl" aria-hidden />}
      <div className={cx("container-x relative grid gap-10 lg:items-end", aside ? "lg:grid-cols-[1.4fr_1fr]" : "", dark ? "py-20 sm:py-28" : "py-14 sm:py-20")}>
        <div className="stagger max-w-3xl">
          {eyebrow && <p className={cx("eyebrow", dark && "eyebrow-light")}>{eyebrow}</p>}
          <h1 className={cx("display-lg mt-4", dark && "text-white")}>
            {title}{accent && <> <span className={cx("serif-accent", dark ? "text-orange-400" : "text-orange-600")}>{accent}</span></>}
          </h1>
          {lead && <p className={cx("mt-5 max-w-2xl text-lg leading-relaxed sm:text-xl", dark ? "text-white/70" : "text-muted")}>{lead}</p>}
          {children}
        </div>
        {aside && <div className="animate-fade-up [animation-delay:0.2s]">{aside}</div>}
      </div>
    </section>
  );
}
