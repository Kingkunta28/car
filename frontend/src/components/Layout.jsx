import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ArrowUpRight, CalendarCheck, Mail, MapPin, Menu, MessageCircle, Phone, X } from "lucide-react";
import { useSite } from "../lib/hooks";
import { cx, whatsappLink } from "../lib/format";
import { Button } from "./ui";
import ErrorBoundary from "./ErrorBoundary";
import logoMark from "../assets/logo-mark.webp";
import i18n, { LANGUAGES } from "../i18n";

const NAV = [
  { to: "/", key: "nav.home", end: true },
  { to: "/fleet", key: "nav.fleet" },
  { to: "/about", key: "nav.about" },
  { to: "/before-you-rent", key: "nav.guide" },
  { to: "/contact", key: "nav.contact" },
];

function LanguageSelect({ overHero = false }) {
  const { t } = useTranslation();
  return (
    <label className="inline-flex items-center gap-1.5">
      <span className="sr-only">{t("language.label")}</span>
      <select aria-label={t("language.label")} value={i18n.resolvedLanguage || "en"}
        onChange={(event) => i18n.changeLanguage(event.target.value)}
        className={cx("h-10 max-w-[9.5rem] cursor-pointer rounded-full border px-2.5 text-sm font-medium outline-none transition focus:ring-2 focus:ring-orange-500",
          overHero ? "border-white/20 bg-navy-950/40 text-white" : "border-line bg-white text-navy-900")}>
        {LANGUAGES.map((language) => <option key={language.code} value={language.code} className="bg-white text-navy-900">{language.flag} {language.label}</option>)}
      </select>
    </label>
  );
}

// Brand lock-up: the Rafiki emblem (on its own white tile, so it reads on dark and
// light backgrounds) + the wordmark. The full badge logo is used in the footer and on PDFs.
export function Logo({ light = false, compact = false, mark = true }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      {mark && (
        <span className="grid h-11 w-[78px] shrink-0 place-items-center overflow-hidden rounded-xl bg-white shadow-[0_4px_14px_-6px_rgb(0_0_0/0.35)] ring-1 ring-black/5">
          <img src={logoMark} alt="" width="594" height="320" className="h-full w-full object-cover" />
        </span>
      )}
      <span className={cx("font-display text-[1.35rem] font-extrabold leading-none tracking-[0.06em]", light ? "text-white" : "text-navy-900")}>
        RAFIKI<span className="text-orange-500">.</span>
        {!compact && <span className={cx("mt-1 block text-[0.58rem] font-semibold tracking-[0.32em]", light ? "text-white/60" : "text-muted")}>CAR HIRE</span>}
      </span>
    </span>
  );
}

function Header() {
  const { t } = useTranslation();
  const { data: site } = useSite();
  const { pathname } = useLocation();
  const [mobile, setMobile] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const overHero = pathname === "/" && !scrolled && !mobile;

  useEffect(() => { setMobile(false); }, [pathname]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => {
    document.body.style.overflow = mobile ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobile]);

  return (
    <header className={cx("fixed inset-x-0 top-0 z-50 transition-[background,box-shadow,border-color] duration-500",
      overHero ? "border-b border-transparent bg-transparent" : "border-b border-line/70 bg-white/85 shadow-[0_1px_0_rgb(11_31_58/0.02)] backdrop-blur-xl")}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">{t("nav.skip")}</a>
      <div className="container-x flex h-[76px] items-center justify-between gap-6">
        <Link to="/" aria-label="Rafiki Car Hire home" className="relative z-10"><Logo light={overHero} site={site} /></Link>
        <nav className="hidden items-center gap-1 lg:flex" aria-label={t("nav.main")}>
          {NAV.map((m) => (
            <NavLink key={m.to} to={m.to} end={m.end} className={({ isActive }) => cx(
              "relative rounded-full px-3.5 py-2 text-[15px] font-medium transition",
              overHero ? "text-white/80 hover:text-white" : "text-navy-900/75 hover:text-navy-900",
              isActive && (overHero ? "text-white" : "text-navy-900"),
              "after:absolute after:inset-x-3.5 after:-bottom-0.5 after:h-0.5 after:origin-left after:rounded-full after:bg-orange-500 after:transition-transform after:duration-300",
              isActive ? "after:scale-x-100" : "after:scale-x-0 hover:after:scale-x-100")}>{t(m.key)}</NavLink>
          ))}
        </nav>
        <div className="relative z-10 flex items-center gap-2">
          <LanguageSelect overHero={overHero} />
          <Link to="/booking/manage" className={cx("hidden rounded-full px-3.5 py-2 text-sm font-medium transition xl:inline-flex",
            overHero ? "text-white/75 hover:text-white" : "text-muted hover:text-navy-900")}>{t("nav.myBooking")}</Link>
          <Button to="/book" size="sm" arrow className="hidden sm:inline-flex">{t("nav.book")}</Button>
          <button onClick={() => setMobile((o) => !o)} aria-expanded={mobile} aria-controls="mobile-nav" aria-label={mobile ? t("nav.close") : t("nav.open")}
            className={cx("grid size-11 place-items-center rounded-full transition lg:hidden", overHero ? "text-white hover:bg-white/10" : "text-navy-900 hover:bg-navy-50")}>
            {mobile ? <X className="size-6" /> : <Menu className="size-6" />}
          </button>
        </div>
      </div>

      {/* Full-screen mobile menu */}
      <div id="mobile-nav" className={cx("fixed inset-x-0 bottom-0 top-[76px] overflow-y-auto bg-white transition duration-500 ease-[var(--ease-out-soft)] lg:hidden",
        mobile ? "visible translate-y-0 opacity-100" : "invisible -translate-y-3 opacity-0")} aria-hidden={!mobile}>
        <nav className="container-x flex min-h-full flex-col py-6" aria-label={t("nav.mobile")}>
          {[...NAV, { to: "/booking/manage", key: "nav.manageBooking" }].map((n, i) => (
            <NavLink key={n.to} to={n.to} end tabIndex={mobile ? 0 : -1}
              style={{ transitionDelay: mobile ? `${60 + i * 40}ms` : "0ms" }}
              className={({ isActive }) => cx("flex items-center justify-between border-b border-line py-4 font-display text-2xl font-semibold transition duration-500",
                mobile ? "translate-x-0 opacity-100" : "-translate-x-4 opacity-0", isActive ? "text-orange-600" : "text-navy-900")}>
              {t(n.key)}<ArrowUpRight className="size-5 text-muted" aria-hidden />
            </NavLink>
          ))}
          <div className="mt-auto space-y-3 pt-8">
            <LanguageSelect />
            <Button to="/book" size="lg" className="w-full" icon={CalendarCheck} tabIndex={mobile ? 0 : -1}>{t("nav.book")}</Button>
            {whatsappLink(site?.whatsapp_number) && (
              <Button href={whatsappLink(site.whatsapp_number, "Hello Rafiki Car Hire!")} target="_blank" rel="noopener noreferrer"
                variant="whatsapp" size="lg" className="w-full" icon={MessageCircle} tabIndex={mobile ? 0 : -1}>{t("actions.whatsapp")}</Button>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}

const FOOTER_LINKS = {
  quick: [
    { to: "/", key: "nav.home" },
    { to: "/about", key: "nav.about" },
    { to: "/fleet", key: "nav.fleet" },
    { to: "/contact", key: "nav.contact" },
    { to: "/before-you-rent", key: "nav.guide" },
  ],
  rental: [
    { to: "/#how-it-works", key: "footer.how" },
    { to: "/before-you-rent#booking", key: "footer.bookingInfo" },
    { to: "/before-you-rent#permit", key: "footer.permit" },
    { to: "/terms", key: "footer.terms" },
    { to: "/#faq", key: "footer.faq" },
  ],
};

function FooterLinks({ title, links }) {
  const { t } = useTranslation();
  return (
    <nav aria-label={title}>
      <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-white">{title}</h2>
      <ul className="mt-5 space-y-3 text-[15px]">
        {links.map((l) => (
          <li key={l.to}>
            <Link to={l.to} className="group inline-flex items-center gap-0 text-white/65 transition-all duration-300 hover:gap-2 hover:text-orange-400">
              <span className="h-px w-0 bg-orange-400 transition-all duration-300 group-hover:w-3" aria-hidden />
              {t(l.key)}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function ContactItem({ icon: Icon, label, children, href, external }) {
  const body = (
    <>
      <span className="grid size-9 shrink-0 place-items-center rounded-full border border-white/15 text-orange-400 transition-colors duration-300 group-hover:border-orange-400 group-hover:bg-orange-500 group-hover:text-navy-950">
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block text-xs text-white/45">{label}</span>
        <span className="block break-words text-[15px] text-white/85 transition-colors group-hover:text-white">{children}</span>
      </span>
    </>
  );
  return (
    <li>
      {href ? (
        <a href={href} className="group flex items-center gap-3" {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>{body}</a>
      ) : <div className="group flex items-center gap-3">{body}</div>}
    </li>
  );
}

function Footer() {
  const { t } = useTranslation();
  const { data: site } = useSite();
  const wa = whatsappLink(site?.whatsapp_number, "Hello Rafiki Car Hire, I'd like to ask about renting a car.");
  const year = new Date().getFullYear();
  const name = site?.business_name || "Rafiki Car Hire";
  return (
    <footer className="relative overflow-hidden bg-navy-950 text-white/70" aria-labelledby="footer-heading">
      <h2 id="footer-heading" className="sr-only">{name} — site information</h2>
      <div className="h-1 bg-gradient-to-r from-orange-500 via-orange-400 to-orange-500" aria-hidden />
      <div className="container-x">
        <div className="grid grid-cols-2 gap-x-6 gap-y-12 py-16 lg:grid-cols-[1.35fr_1fr_1.15fr_1.25fr] lg:gap-10">
          {/* Brand */}
          <div className="col-span-2 lg:col-span-1">
            <Link to="/" aria-label={`${name} home`} className="inline-block">
              {site?.logo_url ? (
                <span className="block rounded-2xl bg-white p-2.5 shadow-[0_10px_30px_-12px_rgb(0_0_0/0.6)]">
                  <img src={site.logo_url} alt={`${name} logo`} width="760" height="582" loading="lazy" className="h-20 w-auto" />
                </span>
              ) : <Logo light />}
            </Link>
            <p className="mt-6 max-w-xs text-[15px] leading-relaxed">
              {t("footer.discover")}
            </p>
            <p className="mt-4 font-serif text-lg italic text-orange-400">{site?.tagline || "Drive Zanzibar with Confidence."}</p>
          </div>

          <FooterLinks title={t("footer.quick")} links={FOOTER_LINKS.quick} />
          <FooterLinks title={t("footer.rental")} links={FOOTER_LINKS.rental} />

          {/* Contact — only details stored in Site Settings are shown */}
          <div className="col-span-2 lg:col-span-1">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-white">{t("footer.contact")}</h2>
            <ul className="mt-5 space-y-4">
              {site?.business_phone && <ContactItem icon={Phone} label={t("footer.phone")} href={`tel:${site.business_phone.replace(/\s/g, "")}`}>{site.business_phone}</ContactItem>}
              {wa && <ContactItem icon={MessageCircle} label={t("footer.whatsappSupport")} href={wa} external>{site.business_phone || `+${site.whatsapp_number}`}</ContactItem>}
              {site?.business_email && <ContactItem icon={Mail} label={t("footer.email")} href={`mailto:${site.business_email}`}>{site.business_email}</ContactItem>}
              <ContactItem icon={MapPin} label={t("footer.place")} external
                href={`https://maps.google.com/?q=${encodeURIComponent(site?.business_address || "Zanzibar, Tanzania")}`}>
                {site?.business_address || "Zanzibar, Tanzania"}
              </ContactItem>
            </ul>
          </div>
        </div>

        <div className="flex flex-col gap-4 border-t border-white/10 py-6 text-sm text-white/45 sm:flex-row sm:items-center sm:justify-between">
          <p>© {year} {name}. {t("footer.rights")}</p>
          <nav aria-label="Legal" className="flex gap-6">
            <Link to="/privacy" className="transition-colors hover:text-orange-400">{t("footer.privacy")}</Link>
            <Link to="/terms" className="transition-colors hover:text-orange-400">{t("footer.terms")}</Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}

function MobileBookCta() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const [show, setShow] = useState(false);
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 560);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const hidden = pathname.startsWith("/book") || pathname.startsWith("/fleet/") || pathname.startsWith("/payment") || pathname.startsWith("/admin");
  if (hidden || !show) return null;
  return (
    <Link to="/book" className="no-print fixed bottom-5 left-5 z-40 inline-flex h-12 animate-fade-up items-center gap-2 rounded-full bg-orange-500 px-5 font-semibold text-navy-950 shadow-lg shadow-black/20 sm:hidden">
      <CalendarCheck className="size-5" /> {t("nav.book")}
    </Link>
  );
}

function WhatsAppFab() {
  const { t } = useTranslation();
  const { data: site } = useSite();
  const { pathname } = useLocation();
  const href = whatsappLink(site?.whatsapp_number, "Hello Rafiki Car Hire, I have a question about car hire.");
  if (!href || pathname.startsWith("/book") || pathname.startsWith("/fleet/")) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" aria-label={t("footer.chat")}
      className="no-print group fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-[#1FAF38] p-3.5 text-white shadow-lg shadow-black/20 transition hover:pr-5">
      <MessageCircle className="size-6" />
      <span className="max-w-0 overflow-hidden whitespace-nowrap text-sm font-semibold transition-all duration-500 group-hover:max-w-40">{t("footer.chat")}</span>
    </a>
  );
}

export default function PublicLayout() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) { setTimeout(() => el.scrollIntoView({ behavior: "smooth" }), 80); return; }
    }
    window.scrollTo(0, 0); // block body: scrollTo() may return a Promise
  }, [pathname, hash]);
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main id="main" className={cx("flex-1", pathname === "/" ? "" : "pt-[76px]")}>
        <ErrorBoundary resetKey={pathname}>
          <div key={pathname} className="page-enter"><Outlet /></div>
        </ErrorBoundary>
      </main>
      <Footer />
      <MobileBookCta />
      <WhatsAppFab />
    </div>
  );
}
