import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight, BadgeCheck, Baby, CalendarDays, CarFront, Check, ChevronDown, FileText, Lock, MapPin, MessageCircle,
  Plane, Quote, ShieldCheck, Star, Wallet,
} from "lucide-react";
import { api } from "../../lib/api";
import { useBookingOptions, useReveal, useSite, useVehicles } from "../../lib/hooks";
import { DESTINATIONS, HOW_IT_WORKS, babySeatText, faqs, priceOf, zoneFee } from "../../lib/content";
import { cx, todayISO, usd, whatsappLink } from "../../lib/format";
import { getBusinessInfo } from "../../data/businessInfo";
import { Seo, businessJsonLd } from "../../lib/seo";
import { Button, Skeleton } from "../../components/ui";
import VehicleCard from "../../components/VehicleCard";
import ZanzibarMap from "../../components/ZanzibarMap";
import { Counter, Parallax } from "../../components/Motion";
import heroBeach from "../../assets/hero-beach.webp";
import heroCar from "../../assets/hero-prado.webp";

/* ------------------------------------------------------------------ Hero */
const TRUST = [
  { icon: CalendarDays, title: "home.flexible", text: "home.flexibleText" },
  { icon: MessageCircle, title: "home.support", text: "home.supportText" },
  { icon: Plane, title: "home.convenientPickup", text: "home.convenientPickupText" },
];

function HeroVisual({ photo, fromPrice }) {
  const { t } = useTranslation();
  return (
    <div className="relative mx-auto w-full max-w-[560px] lg:max-w-none">
      {/* Orange offset frame accent */}
      <div className="absolute -right-3 -top-3 hidden h-[calc(100%-2rem)] w-[calc(100%-2rem)] rounded-[2rem] border-2 border-orange-500/70 sm:block" aria-hidden />
      <Parallax speed={0.04}>
        <figure className="relative aspect-[4/3] overflow-hidden rounded-[2rem] bg-navy-800 shadow-[var(--shadow-lift)] animate-[reveal_1.2s_var(--ease-out-soft)_0.15s_both] lg:aspect-[5/6]">
          <img src={photo} alt="Turquoise water and white sand on the coast of Zanzibar" width="1600" height="1001"
            className="h-full w-full scale-105 object-cover object-[60%_78%] lg:object-[60%_center]" fetchPriority="high" />
          <div className="absolute inset-0 bg-gradient-to-t from-navy-950/55 via-transparent to-transparent" aria-hidden />
          <figcaption className="absolute right-5 top-5 rounded-full bg-navy-950/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur">
            Zanzibar, Tanzania
          </figcaption>
        </figure>
      </Parallax>
      {/* Vehicle breaks out of the frame */}
      <div className="absolute -bottom-6 left-[4%] w-[92%] sm:-left-10 lg:-bottom-10 lg:-left-24 lg:w-[105%]">
        <div className="relative animate-[car-in_1.3s_var(--ease-out-soft)_0.45s_both]">
          <div className="absolute inset-x-[10%] bottom-[3%] h-[10%] rounded-[50%] bg-black/60 blur-2xl" aria-hidden />
          <img src={heroCar} width="1100" height="647" alt="Black Toyota Land Cruiser Prado available for hire in Zanzibar from Rafiki Car Hire"
            className="relative w-full drop-shadow-[0_25px_35px_rgb(0_0_0/0.45)]" fetchPriority="high" />
        </div>
      </div>
      {/* Floating benefit card */}
      <div className="absolute -left-2 top-6 animate-[fade-up_0.9s_var(--ease-out-soft)_0.9s_both] sm:-left-8 lg:-left-14 lg:top-10">
        <div className="animate-float flex items-center gap-3 rounded-2xl bg-white p-3.5 pr-5 text-navy-900 shadow-[var(--shadow-lift)]">
          <span className="grid size-10 place-items-center rounded-xl bg-orange-500 text-navy-950"><Plane className="size-5" aria-hidden /></span>
          <span>
            <span className="block text-sm font-semibold">{t("home.freeAirport")}</span>
            <span className="block text-xs text-muted">{t("home.arrivals")}</span>
          </span>
        </div>
      </div>
      {fromPrice != null && (
        <div className="absolute -right-2 top-[42%] hidden animate-[fade-up_0.9s_var(--ease-out-soft)_1.05s_both] sm:block lg:-right-6">
          <div className="animate-float rounded-2xl bg-navy-950 px-4 py-3 text-white shadow-[var(--shadow-lift)] [animation-delay:-3s]">
            <span className="block text-xs text-white/60">{t("home.carsFrom")}</span>
            <span className="font-display text-xl font-bold">{usd(fromPrice)}<span className="text-sm font-normal text-white/60"> / day</span></span>
          </div>
        </div>
      )}
    </div>
  );
}

function Hero({ site, fromPrice }) {
  const { t } = useTranslation();
  const photo = site?.hero_image_url || heroBeach;
  return (
    <section className="relative isolate overflow-hidden bg-navy-950 pb-16 pt-28 text-white sm:pt-32 lg:pb-20 lg:pt-36" aria-labelledby="hero-title">
      <div className="pointer-events-none absolute -right-40 top-10 -z-10 size-[42rem] rounded-full bg-orange-500/10 blur-3xl" aria-hidden />
      <div className="container-x">
        <div className="grid items-center gap-16 lg:grid-cols-12 lg:gap-10">
          <div className="stagger lg:col-span-6">
            <p className="eyebrow eyebrow-light">{t("home.eyebrow")}</p>
            <h1 id="hero-title" className="display-xl mt-6 text-white">
              {t("home.title")} <span className="serif-accent block text-orange-400">{t("home.accent")}</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-white/75">
              {t("home.lead")}
            </p>
            <div className="mt-9 grid gap-3 sm:flex sm:flex-wrap">
              <Button to="/fleet" size="lg" arrow className="w-full sm:w-auto">{t("home.explore")}</Button>
              <Button to="/book" size="lg" variant="outlineLight" className="w-full sm:w-auto">{t("home.book")}</Button>
            </div>
            <ul className="mt-10 grid gap-5 border-t border-white/10 pt-8 sm:grid-cols-3">
              {TRUST.map((item) => (
                <li key={item.title} className="flex gap-3">
                  <item.icon className="mt-0.5 size-5 shrink-0 text-orange-400" aria-hidden />
                  <span><span className="block text-sm font-semibold text-white">{t(item.title)}</span><span className="block text-xs text-white/55">{t(item.text)}</span></span>
                </li>
              ))}
            </ul>
          </div>
          <div className="lg:col-span-6 lg:pl-8">
            <HeroVisual photo={photo} fromPrice={fromPrice} />
          </div>
        </div>
        <div className="mt-20 animate-[fade-up_0.9s_var(--ease-out-soft)_0.6s_both] lg:mt-24">
          <QuickSearch />
        </div>
      </div>
    </section>
  );
}

function QuickSearch() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [f, setF] = useState({ pickup_type: "AIRPORT", pickup_date: todayISO(3), return_date: todayISO(7) });
  const days = Math.max(0, Math.round((new Date(f.return_date) - new Date(f.pickup_date)) / 86_400_000));
  const submit = (e) => { e.preventDefault(); nav(`/book?${new URLSearchParams(f)}`); };
  return (
    <form onSubmit={submit} aria-label={t("home.quickSearch")}
      className="grid gap-4 rounded-[var(--radius-panel)] bg-white p-4 text-ink shadow-[var(--shadow-lift)] sm:p-5 md:grid-cols-[1.3fr_1fr_1fr_auto] md:items-end">
      <label className="block">
        <span className="label flex items-center gap-1.5"><MapPin className="size-4 text-orange-600" aria-hidden /> {t("home.pickup")}</span>
        <select className="input" value={f.pickup_type} onChange={(e) => setF({ ...f, pickup_type: e.target.value })}>
          <option value="AIRPORT">{t("home.airportFree")}</option>
          <option value="TOWN">{t("home.townFree")}</option>
          <option value="OUTSIDE_ZONE">{t("home.outsideZone")}</option>
        </select>
      </label>
      <label className="block">
        <span className="label flex items-center gap-1.5"><CalendarDays className="size-4 text-orange-600" aria-hidden /> {t("home.pickupDate")}</span>
        <input type="date" className="input" min={todayISO()} value={f.pickup_date} required
          onChange={(e) => setF({ ...f, pickup_date: e.target.value, return_date: e.target.value >= f.return_date ? e.target.value : f.return_date })} />
      </label>
      <label className="block">
        <span className="label flex items-center justify-between"><span className="flex items-center gap-1.5"><CalendarDays className="size-4 text-orange-600" aria-hidden /> {t("home.returnDate")}</span>
          {days > 0 && <span className="text-xs font-normal text-muted">{days} day{days > 1 ? "s" : ""}</span>}</span>
        <input type="date" className="input" min={f.pickup_date} value={f.return_date} required onChange={(e) => setF({ ...f, return_date: e.target.value })} />
      </label>
      <Button type="submit" size="lg" className="h-[46px] w-full md:w-auto" arrow>{t("home.checkAvailability")}</Button>
    </form>
  );
}

/* --------------------- Sections */
function Stats({ vehicles, options, fromPrice }) {
  const { t } = useTranslation();
  const stats = [
    vehicles?.length ? { v: vehicles.length, label: t("home.stats.fleet"), sub: t("home.stats.fleetNote") } : null,
    { v: 0, prefix: "$", label: t("home.stats.handover"), sub: t("home.stats.handoverNote") },
    { v: options?.hold_hours ?? 24, suffix: "h", label: t("home.stats.hold"), sub: t("home.stats.holdNote") },
    fromPrice != null ? { v: Number(fromPrice), prefix: "$", label: t("home.stats.price"), sub: t("home.stats.priceNote") } : null,
  ].filter(Boolean);
  return (
    <section className="pt-20 sm:pt-24" aria-label="Rafiki at a glance">
      <div className="container-x">
        <dl className={cx("grid gap-px overflow-hidden rounded-[var(--radius-card)] border border-line bg-line", stats.length === 4 ? "sm:grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-3")}>
          {stats.map((s, i) => (
            <div key={s.label} className="bg-white p-6 sm:p-7" data-reveal={i * 70}>
              <dt className="sr-only">{s.label}</dt>
              <dd className="font-display text-4xl font-bold tracking-tight text-navy-900 sm:text-5xl"><Counter value={s.v} prefix={s.prefix} suffix={s.suffix} /></dd>
              <dd className="mt-2 font-medium text-navy-900">{s.label}</dd>
              <dd className="text-sm text-muted">{s.sub}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

const TABS = [["", "All"], ["SUV", "SUV"], ["4X4", "4x4"], ["COMPACT_SUV", "Compact SUV"], ["ECONOMY", "Economy"], ["MINIVAN", "Minivan"]];

function FleetShowcase({ vehicles, loading }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState("");
  const available = useMemo(() => TABS.filter(([k]) => !k || vehicles?.some((v) => v.category === k)), [vehicles]);
  const list = (vehicles || []).filter((v) => !tab || v.category === tab)
    .sort((a, b) => Number(b.is_featured) - Number(a.is_featured)).slice(0, 6);
  return (
    <section className="py-24 sm:py-32">
      <div className="container-x">
        <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end" data-reveal>
          <div>
            <p className="eyebrow">{t("home.fleetEyebrow")}</p>
            <h2 className="display-lg mt-4 max-w-2xl">{t("home.fleetTitle")}</h2>
            <p className="lead mt-4 max-w-xl">{t("home.fleetLead")}</p>
          </div>
          <Button to="/fleet" variant="outline" arrow>{t("home.viewFleet")}</Button>
        </div>
        {available.length > 2 && (
          <div className="mt-10 flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Vehicle type">
            {available.map(([k, l]) => (
              <button key={l} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                className={cx("shrink-0 rounded-full border px-4 py-2 text-sm font-semibold transition",
                  tab === k ? "border-navy-900 bg-navy-900 text-white" : "border-line bg-white text-navy-900 hover:border-navy-600")}>{k ? t(`vehicle.categories.${k}`) : t("home.all")}</button>
            ))}
          </div>
        )}
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {loading ? [0, 1, 2].map((i) => <Skeleton key={i} className="h-[440px]" />)
            : list.map((v, i) => <div key={v.id} data-reveal={(i % 3) * 90}><VehicleCard vehicle={v} /></div>)}
        </div>
        {!loading && !list.length && (
          <div className="mt-8 grid items-center gap-6 rounded-[var(--radius-panel)] border border-dashed border-sand-200 bg-sand-50 p-8 sm:grid-cols-[auto_1fr_auto] sm:p-10">
            <span className="grid size-14 place-items-center rounded-2xl bg-white text-navy-700 shadow-sm"><CarFront className="size-7" /></span>
            <div>
              <h3 className="text-xl font-semibold">{t("home.fleetUpdating")}</h3>
              <p className="mt-1 text-muted">{t("home.fleetUpdatingText")}</p>
            </div>
            <Button to="/contact" variant="navy" arrow>{t("home.askAvailability")}</Button>
          </div>
        )}
      </div>
    </section>
  );
}

function Zones({ options }) {
  const { t } = useTranslation();
  const fee = zoneFee(options);
  const tiers = [
    { icon: Plane, title: t("booking.airport"), price: t("booking.free"), text: t("home.airportText") },
    { icon: MapPin, title: t("booking.town"), price: t("booking.free"), text: t("home.townText") },
    { icon: CarFront, title: t("booking.locations.OUTSIDE_ZONE"), price: fee ? usd(fee) : t("home.flatFee"), text: t("home.outsideText") },
  ];
  return (
    <section id="zones" className="scroll-mt-24 bg-sand-50 py-24 sm:py-32">
      <div className="container-x grid gap-14 lg:grid-cols-[1fr_1fr] lg:items-center">
        <div data-reveal>
          <p className="eyebrow">{t("home.deliveryEyebrow")}</p>
          <h2 className="display-lg mt-4">{t("home.deliveryTitle")}</h2>
          <p className="lead mt-4 max-w-lg">{t("home.deliveryLead")}</p>
          <ul className="mt-10 space-y-3">
            {tiers.map((t) => (
              <li key={t.title} className="card flex items-start gap-4 p-5">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-navy-900 text-orange-400"><t.icon className="size-5" /></span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-3">
                    <h3 className="font-semibold">{t.title}</h3>
                    <span className={cx("font-display text-lg font-bold", t.price === "Free" ? "text-emerald-700" : "text-navy-900")}>{t.price}</span>
                  </div>
                  <p className="mt-0.5 text-sm text-muted">{t.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="card p-4 sm:p-6" data-reveal="100">
          <ZanzibarMap fee={fee} />
        </div>
      </div>
    </section>
  );
}

function Bento({ options }) {
  const { t } = useTranslation();
  return (
    <section className="py-24 sm:py-32">
      <div className="container-x">
        <div className="max-w-2xl" data-reveal>
          <p className="eyebrow">{t("home.why")}</p>
          <h2 className="display-lg mt-4">{t("home.whyTitle")}</h2>
        </div>
        <div className="mt-12 grid auto-rows-[minmax(200px,auto)] gap-4 md:grid-cols-6">
          <div className="relative overflow-hidden rounded-[var(--radius-panel)] bg-navy-950 p-7 text-white md:col-span-4 md:row-span-2 sm:p-9" data-reveal>
            <div className="hairline-grid absolute inset-0 opacity-70" aria-hidden />
            <div className="relative grid h-full gap-8 sm:grid-cols-[1fr_auto] sm:items-end">
              <div>
                <FileText className="size-8 text-orange-400" />
              <h3 className="mt-6 text-3xl font-bold text-white">{t("home.paperwork")}</h3>
                <p className="mt-3 max-w-md leading-relaxed text-white/70">{t("home.paperworkText")}</p>
              </div>
              {/* Invoice motif */}
              <div className="animate-float w-full max-w-[230px] rotate-2 rounded-2xl bg-white p-4 text-ink shadow-2xl sm:w-[230px]" aria-hidden>
                <div className="flex items-center justify-between"><span className="font-display text-sm font-extrabold tracking-wider text-navy-900">RAFIKI<span className="text-orange-500">.</span></span><span className="text-[10px] font-semibold text-muted">INVOICE</span></div>
                <div className="mt-3 h-px bg-orange-500" />
                {[["Rental · 4 days", "220.00"], ["Pickup · Nungwi", "25.00"], ["Baby seat × 2", "120.00"]].map(([a, b]) => (
                  <div key={a} className="mt-2 flex justify-between text-[11px]"><span className="text-muted">{a}</span><span className="tabular-nums">${b}</span></div>
                ))}
                <div className="mt-3 flex justify-between border-t border-line pt-2 text-xs font-bold"><span>Total USD</span><span className="tabular-nums">$365.00</span></div>
                <p className="mt-1 text-[9px] text-muted">Example only</p>
              </div>
            </div>
          </div>
          <div className="card p-7 md:col-span-2" data-reveal="80">
            <Lock className="size-7 text-orange-600" />
            <h3 className="mt-5 text-xl font-semibold">{t("home.privateDocs")}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{t("home.privateDocsText")}</p>
          </div>
          <div className="card p-7 md:col-span-2" data-reveal="160">
            <MessageCircle className="size-7 text-orange-600" />
            <h3 className="mt-5 text-xl font-semibold">{t("home.realPeople")}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{t("home.realPeopleText")}</p>
          </div>
          <div className="card p-7 md:col-span-3" data-reveal>
            <ShieldCheck className="size-7 text-orange-600" />
            <h3 className="mt-5 text-xl font-semibold">{t("home.permit")}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{t("home.permitText", { price: priceOf(options, "driving_permit") ? usd(priceOf(options, "driving_permit")) : "" })}</p>
          </div>
          <div className="card p-7 md:col-span-3" data-reveal="80">
            <Baby className="size-7 text-orange-600" />
            <h3 className="mt-5 text-xl font-semibold">{t("home.children")}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{t("home.childrenText", { price: babySeatText(options) })}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const { t } = useTranslation();
  return (
    <section id="how-it-works" className="relative scroll-mt-20 overflow-hidden bg-navy-950 py-24 text-white sm:py-32">
      <div className="pointer-events-none absolute -right-40 top-0 size-[36rem] rounded-full bg-orange-500/15 blur-3xl" aria-hidden />
      <div className="container-x relative">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end" data-reveal>
          <div>
            <p className="eyebrow eyebrow-light">{t("home.how")}</p>
            <h2 className="display-lg mt-4 text-white">{t("home.howTitle")}</h2>
          </div>
          <Button to="/book" arrow>{t("home.start")}</Button>
        </div>
        <ol className="relative mt-16 grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
          <div className="absolute left-0 right-0 top-6 hidden h-px bg-gradient-to-r from-orange-500/0 via-orange-500/50 to-orange-500/0 lg:block" aria-hidden />
          {HOW_IT_WORKS.map((s, i) => (
            <li key={s.title} className="relative" data-reveal={i * 100}>
              <span className="relative grid size-12 place-items-center rounded-full border border-orange-500/40 bg-navy-900 font-display text-lg font-bold text-orange-400">{i + 1}</span>
              <h3 className="mt-6 text-xl font-semibold text-white">{t(`home.steps.${i}.title`)}</h3>
              <p className="mt-2 leading-relaxed text-white/65">{t(`home.steps.${i}.text`)}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Destinations() {
  const { t } = useTranslation();
  return (
    <section className="py-24 sm:py-32">
      <div className="container-x">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr] lg:items-end" data-reveal>
          <div>
            <p className="eyebrow">{t("home.driving")}</p>
            <h2 className="display-lg mt-4">{t("home.drivingTitle")}</h2>
          </div>
          <p className="lead">{t("home.drivingLead")}</p>
        </div>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {DESTINATIONS.map((d, i) => (
            <article key={d.name} className="card card-hover group relative overflow-hidden p-6" data-reveal={i * 80}>
              <span className="absolute -right-6 -top-6 size-24 rounded-full bg-orange-100 transition-transform duration-700 group-hover:scale-[2.2]" aria-hidden />
              <p className="relative text-xs font-semibold uppercase tracking-wider text-orange-600">{t(`home.destinations.${i}.time`)}</p>
              <h3 className="relative mt-3 text-2xl font-semibold">{d.name}</h3>
              <p className="relative mt-2 text-sm leading-relaxed text-muted">{t(`home.destinations.${i}.text`)}</p>
            </article>
          ))}
        </div>
        <Link to="/before-you-rent" className="link-u mt-8 inline-flex items-center gap-1.5">{t("home.tips")} <ArrowRight className="arrow size-4" /></Link>
      </div>
    </section>
  );
}

function Testimonials({ items }) {
  const { t } = useTranslation();
  if (!items?.length) return null;
  return (
    <section className="bg-sand-50 py-24 sm:py-32">
      <div className="container-x">
        <div className="max-w-2xl" data-reveal>
          <p className="eyebrow">{t("home.stories")}</p>
          <h2 className="display-lg mt-4">{t("home.storiesTitle")}</h2>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {items.slice(0, 6).map((t, i) => (
            <figure key={t.id} className="card flex flex-col p-7" data-reveal={(i % 3) * 80}>
              <Quote className="size-8 text-orange-500" aria-hidden />
              <blockquote className="mt-4 flex-1 font-serif text-xl leading-snug text-navy-900">“{t.quote}”</blockquote>
              <figcaption className="mt-6 flex items-center justify-between border-t border-line pt-4 text-sm">
                <span className="font-semibold text-navy-900">{t.customer_name}{t.country && <span className="font-normal text-muted"> · {t.country}</span>}</span>
                <span className="flex gap-0.5" aria-label={`${t.rating} out of 5 stars`}>
                  {Array.from({ length: 5 }).map((_, s) => <Star key={s} className={cx("size-3.5", s < t.rating ? "fill-orange-500 text-orange-500" : "text-slate-300")} aria-hidden />)}
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function Faq({ list }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(0);
  return (
    <section id="faq" className="scroll-mt-24 py-24 sm:py-32">
      <div className="container-x grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
        <div data-reveal>
          <p className="eyebrow">{t("home.questions")}</p>
          <h2 className="display-lg mt-4">{t("home.goodToKnow")}</h2>
          <p className="lead mt-4">{t("home.faqLead")} <Link to="/contact" className="link-u">{t("home.askDirect")}</Link>.</p>
        </div>
        <div className="divide-y divide-line border-y border-line" data-reveal>
          {list.map((f, i) => (
            <div key={f.q}>
              <h3>
                <button onClick={() => setOpen(open === i ? -1 : i)} aria-expanded={open === i}
                  className="flex w-full items-center justify-between gap-6 py-6 text-left font-display text-lg font-semibold text-navy-900 transition hover:text-orange-600 sm:text-xl">
                  {f.q}
                  <span className={cx("grid size-9 shrink-0 place-items-center rounded-full border transition duration-300",
                    open === i ? "rotate-180 border-orange-500 bg-orange-500 text-navy-950" : "border-line")}>
                    <ChevronDown className="size-4" aria-hidden />
                  </span>
                </button>
              </h3>
              <div className={cx("grid transition-all duration-500 ease-[var(--ease-out-soft)]", open === i ? "grid-rows-[1fr] pb-6" : "grid-rows-[0fr]")}>
                <p className="overflow-hidden pr-12 leading-relaxed text-muted">{f.a}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}


function FinalCta({ wa }) {
  const { t } = useTranslation();
  return (
    <section className="pb-24 sm:pb-32" aria-labelledby="final-cta">
      <div className="container-x">
        <div className="relative overflow-hidden rounded-[var(--radius-panel)] bg-navy-950 px-6 py-14 text-white sm:px-14" data-reveal>
          <div className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-orange-500/20 blur-3xl" aria-hidden />
          <div className="relative grid gap-8 lg:grid-cols-[1.4fr_auto] lg:items-center">
            <div>
              <p className="eyebrow eyebrow-light">{t("home.ready")}</p>
              <h2 id="final-cta" className="display-lg mt-4 text-white">{t("home.readyTitle")}</h2>
              <p className="mt-4 max-w-xl text-white/70">{t("home.readyText")}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button to="/book" size="lg" arrow>{t("home.book")}</Button>
              {wa && <Button href={wa} target="_blank" rel="noopener noreferrer" size="lg" variant="outlineLight" icon={MessageCircle}>{t("home.whatsapp")}</Button>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const { t } = useTranslation();
  const { data: site } = useSite();
  const business = getBusinessInfo(site);
  const { data: options } = useBookingOptions();
  const vehicles = useVehicles({});
  const testimonials = useQuery({ queryKey: ["testimonials"], queryFn: () => api.get("/testimonials/"), staleTime: 600_000 });
  const ref = useReveal([vehicles.data, testimonials.data]);
  const fromPrice = vehicles.data?.length ? Math.min(...vehicles.data.map((v) => Number(v.price_per_day))) : null;
  const faqList = faqs(options);
  const wa = whatsappLink(business.whatsappNumber);

  return (
    <div ref={ref}>
      <Seo title={t("seo.home")} path="/"
        description={t("home.lead")}
        jsonLd={[businessJsonLd(site), { "@context": "https://schema.org", "@type": "FAQPage",
          mainEntity: faqList.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })) }]} />
      <Hero site={site} fromPrice={fromPrice} />
      <Stats vehicles={vehicles.data} options={options} fromPrice={fromPrice} />
      <FleetShowcase vehicles={vehicles.data} loading={vehicles.isLoading} />
      <Zones options={options} />
      <Bento options={options} />
      <HowItWorks />
      <Destinations />
      <Testimonials items={testimonials.data} />
      <Faq list={faqList} />
      <FinalCta wa={wa ? whatsappLink(business.whatsappNumber, "Hello Rafiki Car Hire! I would like to book a car.") : null} />
    </div>
  );
}
