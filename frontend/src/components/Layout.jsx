import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Mail, MapPin, Menu, MessageCircle, Phone, X } from "lucide-react";
import { useSite } from "../lib/hooks";
import { cx, whatsappLink } from "../lib/format";
import { Button } from "./ui";

const NAV = [
  { to: "/fleet", label: "Our Fleet" },
  { to: "/before-you-rent", label: "Before You Rent" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

export function Logo({ light = false, site }) {
  if (site?.logo_url) {
    return <img src={site.logo_url} alt={site.business_name || "Rafiki Car Hire"} className="h-9 w-auto" />;
  }
  return (
    <span className={cx("font-display text-[1.35rem] font-extrabold leading-none tracking-[0.08em]", light ? "text-white" : "text-navy-900")}>
      RAFIKI<span className="text-orange-500">.</span>
      <span className={cx("ml-1.5 align-middle text-[0.62rem] font-semibold tracking-[0.28em]", light ? "text-white/70" : "text-muted")}>CAR HIRE</span>
    </span>
  );
}

function Header() {
  const { data: site } = useSite();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const overHero = pathname === "/" && !scrolled;

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={cx("fixed inset-x-0 top-0 z-50 transition-colors duration-300",
      overHero ? "bg-transparent" : "border-b border-line/70 bg-white/90 backdrop-blur-lg")}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <div className="container-x flex h-[72px] items-center justify-between gap-6">
        <Link to="/" aria-label="Rafiki Car Hire home"><Logo light={overHero} site={site} /></Link>
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => cx(
              "rounded-lg px-3.5 py-2 text-[15px] font-medium transition",
              overHero ? "text-white/85 hover:text-white hover:bg-white/10" : "text-navy-900/80 hover:text-navy-900 hover:bg-navy-50",
              isActive && (overHero ? "text-white" : "text-navy-900 bg-navy-50"))}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Button to="/book" size="sm" className="hidden sm:inline-flex">Book a car</Button>
          <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            className={cx("grid size-11 place-items-center rounded-xl lg:hidden", overHero ? "text-white hover:bg-white/10" : "text-navy-900 hover:bg-navy-50")}>
            {open ? <X className="size-6" /> : <Menu className="size-6" />}
          </button>
        </div>
      </div>
      {open && (
        <nav id="mobile-nav" className="border-t border-line bg-white lg:hidden" aria-label="Mobile">
          <div className="container-x flex flex-col py-3">
            {[{ to: "/", label: "Home" }, ...NAV].map((n) => (
              <NavLink key={n.to} to={n.to} end className={({ isActive }) => cx("rounded-lg px-3 py-3 text-base font-medium", isActive ? "bg-navy-50 text-navy-900" : "text-navy-900/80")}>
                {n.label}
              </NavLink>
            ))}
            <Button to="/book" className="mt-2">Book a car</Button>
          </div>
        </nav>
      )}
    </header>
  );
}

function Footer() {
  const { data: site } = useSite();
  const wa = whatsappLink(site?.whatsapp_number, "Hello Rafiki Car Hire, I'd like to ask about renting a car.");
  return (
    <footer className="bg-navy-950 text-white/75">
      <div className="container-x grid gap-10 py-14 md:grid-cols-2 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <Logo light site={site} />
          <p className="mt-4 max-w-xs text-sm leading-relaxed">
            {site?.tagline || "Drive Zanzibar with Confidence."} Self-drive car hire across Unguja with free airport and Stone Town handover.
          </p>
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-white">Explore</h2>
          <ul className="mt-4 space-y-2.5 text-sm">
            {[["/fleet", "Our fleet"], ["/book", "Book a car"], ["/before-you-rent", "Before you rent"], ["/about", "About us"], ["/booking/manage", "Manage my booking"]].map(([to, l]) => (
              <li key={to}><Link to={to} className="hover:text-white">{l}</Link></li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-white">Contact</h2>
          <ul className="mt-4 space-y-3 text-sm">
            <li className="flex gap-2.5"><MapPin className="size-4 shrink-0 translate-y-0.5 text-orange-400" />{site?.business_address || "Zanzibar, Tanzania"}</li>
            {site?.business_phone && <li><a className="flex gap-2.5 hover:text-white" href={`tel:${site.business_phone}`}><Phone className="size-4 translate-y-0.5 text-orange-400" />{site.business_phone}</a></li>}
            {site?.business_email && <li><a className="flex gap-2.5 hover:text-white" href={`mailto:${site.business_email}`}><Mail className="size-4 translate-y-0.5 text-orange-400" />{site.business_email}</a></li>}
            {wa && <li><a className="flex gap-2.5 hover:text-white" href={wa} target="_blank" rel="noopener noreferrer"><MessageCircle className="size-4 translate-y-0.5 text-orange-400" />WhatsApp us</a></li>}
          </ul>
        </div>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-white">Legal</h2>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li><Link to="/terms" className="hover:text-white">Terms &amp; conditions</Link></li>
            <li><Link to="/privacy" className="hover:text-white">Privacy policy</Link></li>
          </ul>
          <p className="mt-6 text-xs text-white/50">All prices in US dollars (USD).</p>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="container-x flex flex-col justify-between gap-2 py-5 text-xs text-white/50 sm:flex-row">
          <p>© {new Date().getFullYear()} {site?.business_name || "Rafiki Car Hire"}. All rights reserved.</p>
          <p>Car hire Zanzibar · Zanzibar airport car rental · Self-drive Zanzibar</p>
        </div>
      </div>
    </footer>
  );
}

function WhatsAppFab() {
  const { data: site } = useSite();
  const { pathname } = useLocation();
  const href = whatsappLink(site?.whatsapp_number, "Hello Rafiki Car Hire, I have a question about car hire.");
  if (!href || pathname.startsWith("/book")) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" aria-label="Chat with us on WhatsApp"
      className="no-print fixed bottom-5 right-5 z-40 grid size-14 place-items-center rounded-full bg-[#1FAF38] text-white shadow-lg shadow-black/20 transition hover:scale-105">
      <MessageCircle className="size-7" />
    </a>
  );
}

export default function PublicLayout() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main id="main" className={cx("flex-1", pathname === "/" ? "" : "pt-[72px]")}><Outlet /></main>
      <Footer />
      <WhatsAppFab />
    </div>
  );
}
