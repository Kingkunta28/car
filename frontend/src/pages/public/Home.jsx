import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight, BadgeCheck, CalendarDays, ChevronDown, Clock, FileText, MapPin, MessageCircle, Plane, ShieldCheck,
  Star, Wallet,
} from "lucide-react";
import { api } from "../../lib/api";
import { useBookingOptions, useReveal, useSite, useVehicles } from "../../lib/hooks";
import { DESTINATIONS, HOW_IT_WORKS, faqs, zoneFee } from "../../lib/content";
import { cx, todayISO, usd, whatsappLink } from "../../lib/format";
import { Seo, businessJsonLd } from "../../lib/seo";
import { Button, Skeleton } from "../../components/ui";
import VehicleCard from "../../components/VehicleCard";

function HeroBackdrop({ image }) {
  if (image) {
    return <img src={image} alt="" className="hero-media absolute inset-0 h-full w-full object-cover" fetchPriority="high" />;
  }
  // Photo-free atmospheric fallback until the owner uploads a hero photograph.
  return (
    <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_80%_10%,#F6A452_0%,#C2410C_18%,#1B3A66_48%,#061224_100%)]" aria-hidden>
      <svg className="absolute bottom-0 left-0 h-1/2 w-full opacity-60" viewBox="0 0 1440 400" preserveAspectRatio="none">
        <path d="M0 260 C 240 200 420 300 720 250 S 1200 180 1440 230 V400 H0Z" fill="#0B1F3A" />
        <path d="M0 310 C 300 270 520 350 820 310 S 1240 270 1440 300 V400 H0Z" fill="#061224" />
      </svg>
    </div>
  );
}

function QuickSearch() {
  const nav = useNavigate();
  const [pickup, setPickup] = useState(todayISO(3));
  const [ret, setRet] = useState(todayISO(7));
  const [location, setLocation] = useState("AIRPORT");
  const submit = (e) => {
    e.preventDefault();
    nav(`/book?pickup_date=${pickup}&return_date=${ret}&pickup_type=${location}`);
  };
  return (
    <form onSubmit={submit} className="glass grid gap-3 rounded-2xl p-3 text-white sm:grid-cols-[1.2fr_1fr_1fr_auto] sm:items-end sm:p-4">
      <label className="block">
        <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-white/75">Pickup location</span>
        <select value={location} onChange={(e) => setLocation(e.target.value)} className="input border-white/20 bg-white text-ink">
          <option value="AIRPORT">Zanzibar Airport — free</option>
          <option value="TOWN">Zanzibar Town — free</option>
          <option value="OUTSIDE_ZONE">Hotel outside free zone</option>
        </select>
      </label>
      <label className="block">
        <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-white/75">Pickup date</span>
        <input type="date" min={todayISO(0)} value={pickup} onChange={(e) => { setPickup(e.target.value); if (e.target.value >= ret) setRet(e.target.value); }} className="input bg-white" required />
      </label>
      <label className="block">
        <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-white/75">Return date</span>
        <input type="date" min={pickup} value={ret} onChange={(e) => setRet(e.target.value)} className="input bg-white" required />
      </label>
      <Button type="submit" size="lg" className="h-[46px]" icon={CalendarDays}>Find a car</Button>
    </form>
  );
}

function FaqItem({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-line">
      <h3>
        <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
          className="flex w-full items-center justify-between gap-4 py-5 text-left font-display text-lg font-semibold text-navy-900">
          {q}
          <ChevronDown className={cx("size-5 shrink-0 text-orange-600 transition-transform duration-300", open && "rotate-180")} aria-hidden />
        </button>
      </h3>
      <div className={cx("grid transition-all duration-300", open ? "grid-rows-[1fr] pb-5" : "grid-rows-[0fr]")}>
        <p className="overflow-hidden text-muted leading-relaxed">{a}</p>
      </div>
    </div>
  );
}

export default function Home() {
  const { data: site } = useSite();
  const { data: options } = useBookingOptions();
  const featured = useVehicles({ featured: "true" });
  const all = useVehicles({});
  const testimonials = useQuery({ queryKey: ["testimonials"], queryFn: () => api.get("/testimonials/"), staleTime: 600_000 });
  const ref = useReveal([featured.data, testimonials.data]);
  const vehicles = (featured.data?.length ? featured.data : all.data || []).slice(0, 3);
  const fromPrice = all.data?.length ? Math.min(...all.data.map((v) => Number(v.price_per_day))) : null;
  const heroImage = site?.hero_image_url || null;
  const wa = whatsappLink(site?.whatsapp_number, "Hello Rafiki Car Hire, I'd like help choosing a car for my Zanzibar trip.");
  const faqList = faqs(options);

  return (
    <div ref={ref}>
      <Seo
        title="Car Hire Zanzibar — Self-Drive Car Rental"
        description="Self-drive car hire in Zanzibar with free airport and Stone Town delivery. Clear USD prices, well-kept SUVs and 4x4s, and friendly local support."
        path="/"
        jsonLd={[businessJsonLd(site), {
          "@context": "https://schema.org", "@type": "FAQPage",
          mainEntity: faqList.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
        }]}
      />

      {/* HERO */}
      <section className="relative isolate flex min-h-[100svh] items-end overflow-hidden bg-navy-950 pb-14 pt-32 text-white sm:items-center sm:pb-20">
        <HeroBackdrop image={heroImage} />
        <div className="absolute inset-0 bg-gradient-to-t from-navy-950 via-navy-950/55 to-navy-950/20" aria-hidden />
        <div className="container-x relative">
          <div className="max-w-3xl">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-1.5 text-sm font-medium text-white/90 backdrop-blur">
              <MapPin className="size-4 text-orange-400" aria-hidden /> Zanzibar, Tanzania
            </p>
            <h1 className="text-[2.6rem] font-bold leading-[1.04] text-white sm:text-6xl lg:text-7xl">
              Drive Zanzibar <span className="text-orange-400">with confidence.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-white/80 sm:text-xl">
              Well-kept cars delivered to the airport, Stone Town or your hotel. Clear US-dollar pricing, an instant invoice, and a local team on WhatsApp whenever you need us.
            </p>
          </div>
          <div className="mt-10 max-w-4xl"><QuickSearch /></div>
          <ul className="mt-8 flex flex-wrap gap-x-8 gap-y-3 text-sm text-white/80">
            <li className="flex items-center gap-2"><Plane className="size-4 text-orange-400" /> Free airport handover</li>
            <li className="flex items-center gap-2"><Wallet className="size-4 text-orange-400" /> No hidden charges</li>
            {fromPrice && <li className="flex items-center gap-2"><BadgeCheck className="size-4 text-orange-400" /> Cars from {usd(fromPrice)}/day</li>}
          </ul>
        </div>
      </section>

      {/* FEATURED FLEET */}
      <section className="py-20 sm:py-28">
        <div className="container-x">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end" data-reveal>
            <div>
              <p className="eyebrow">The fleet</p>
              <h2 className="mt-3 text-3xl font-bold sm:text-4xl">Cars made for island roads</h2>
              <p className="mt-3 max-w-xl text-muted">From compact runabouts for Stone Town to 4x4s for the east-coast tracks — every car is serviced between rentals.</p>
            </div>
            <Button to="/fleet" variant="outline" icon={ArrowRight}>View all vehicles</Button>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {featured.isLoading || all.isLoading
              ? [0, 1, 2].map((i) => <Skeleton key={i} className="h-[420px]" />)
              : vehicles.map((v, i) => <div key={v.id} data-reveal={i * 90}><VehicleCard vehicle={v} /></div>)}
          </div>
          {!featured.isLoading && !all.isLoading && !vehicles.length && (
            <p className="mt-8 rounded-xl bg-sand-50 p-6 text-center text-muted">Our fleet is being updated. Please contact us for availability.</p>
          )}
        </div>
      </section>

      {/* WHY RAFIKI */}
      <section className="bg-navy-950 py-20 text-white sm:py-28">
        <div className="container-x grid gap-14 lg:grid-cols-[1fr_1.3fr] lg:items-center">
          <div data-reveal>
            <p className="eyebrow text-orange-400">Why Rafiki</p>
            <h2 className="mt-3 text-3xl font-bold text-white sm:text-4xl">"Rafiki" means friend. That's how we look after you.</h2>
            <p className="mt-5 max-w-lg leading-relaxed text-white/70">
              We're a Zanzibar team, so you get local knowledge with the standards of an international rental company: written invoices, verified receipts, and a booking you can manage online.
            </p>
            <Button to="/about" variant="light" className="mt-8" icon={ArrowRight}>About us</Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              { icon: Plane, t: "Airport & town delivery", d: "Free handover at the airport and in Zanzibar Town. Hotels elsewhere on the island for a flat fee." },
              { icon: FileText, t: "Instant invoice", d: "Your itemised invoice is emailed the moment you book. Every payment gets its own receipt." },
              { icon: ShieldCheck, t: "Secure documents", d: "Passport and licence copies for permits are stored privately and deleted after your trip." },
              { icon: MessageCircle, t: "Real people on WhatsApp", d: "Questions about routes, fuel or the ferry? Message us — we answer like a friend would." },
            ].map((f, i) => (
              <div key={f.t} data-reveal={i * 80} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 transition hover:bg-white/[0.07]">
                <span className="grid size-11 place-items-center rounded-xl bg-orange-500 text-navy-950"><f.icon className="size-5" aria-hidden /></span>
                <h3 className="mt-5 text-lg font-semibold text-white">{f.t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/65">{f.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-20 sm:py-28">
        <div className="container-x">
          <div className="max-w-2xl" data-reveal>
            <p className="eyebrow">How it works</p>
            <h2 className="mt-3 text-3xl font-bold sm:text-4xl">From booking to beach in four steps</h2>
          </div>
          <ol className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {HOW_IT_WORKS.map((s, i) => (
              <li key={s.title} className="relative" data-reveal={i * 90}>
                <span className="font-display text-5xl font-bold text-orange-500/90">0{i + 1}</span>
                <h3 className="mt-3 text-xl font-semibold">{s.title}</h3>
                <p className="mt-2 leading-relaxed text-muted">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ZANZIBAR INFO */}
      <section className="bg-sand-50 py-20 sm:py-28">
        <div className="container-x grid gap-12 lg:grid-cols-[1fr_1.4fr]">
          <div data-reveal>
            <p className="eyebrow">Driving in Zanzibar</p>
            <h2 className="mt-3 text-3xl font-bold sm:text-4xl">The island is yours to explore</h2>
            <p className="mt-4 leading-relaxed text-muted">
              Unguja is about 85 km from north to south, so with your own car Nungwi's beaches, the Jozani forest and the south-coast lagoons are all an easy day out. Driving is on the left, and roads between the main towns are paved.
            </p>
            <ul className="mt-6 space-y-3 text-[15px]">
              <li className="flex gap-3"><Clock className="mt-0.5 size-5 shrink-0 text-orange-600" /> Allow extra time near villages and police checkpoints — keep your permit and licence handy.</li>
              <li className="flex gap-3"><MapPin className="mt-0.5 size-5 shrink-0 text-orange-600" /> Outside-zone delivery is {zoneFee(options) ? usd(zoneFee(options)) : "a flat fee"} per leg, wherever you're staying.</li>
            </ul>
            <Button to="/before-you-rent" variant="outline" className="mt-8">Read before you rent</Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {DESTINATIONS.map((d, i) => (
              <div key={d.name} className="card p-6" data-reveal={i * 80}>
                <p className="text-xs font-semibold uppercase tracking-wider text-orange-600">{d.time}</p>
                <h3 className="mt-2 text-xl font-semibold">{d.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{d.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS — only genuine, published reviews */}
      {testimonials.data?.length > 0 && (
        <section className="py-20 sm:py-28">
          <div className="container-x">
            <div className="max-w-2xl" data-reveal>
              <p className="eyebrow">Guest stories</p>
              <h2 className="mt-3 text-3xl font-bold sm:text-4xl">What our guests say</h2>
            </div>
            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {testimonials.data.slice(0, 6).map((t, i) => (
                <figure key={t.id} className="card flex flex-col p-6" data-reveal={i * 80}>
                  <div className="flex gap-0.5" aria-label={`${t.rating} out of 5 stars`}>
                    {Array.from({ length: 5 }).map((_, s) => (
                      <Star key={s} className={cx("size-4", s < t.rating ? "fill-orange-500 text-orange-500" : "text-slate-300")} aria-hidden />
                    ))}
                  </div>
                  <blockquote className="mt-4 flex-1 leading-relaxed text-navy-900">"{t.quote}"</blockquote>
                  <figcaption className="mt-5 text-sm font-semibold">{t.customer_name}{t.country && <span className="font-normal text-muted"> · {t.country}</span>}</figcaption>
                </figure>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* FAQ */}
      <section className={cx("py-20 sm:py-28", testimonials.data?.length ? "bg-sand-50" : "")}>
        <div className="container-x grid gap-12 lg:grid-cols-[1fr_1.6fr]">
          <div data-reveal>
            <p className="eyebrow">Questions</p>
            <h2 className="mt-3 text-3xl font-bold sm:text-4xl">Frequently asked</h2>
            <p className="mt-4 text-muted">Can't find your answer? <Link to="/contact" className="font-semibold text-navy-700 underline underline-offset-4">Get in touch</Link>.</p>
          </div>
          <div data-reveal>{faqList.map((f) => <FaqItem key={f.q} {...f} />)}</div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-20 sm:pb-28">
        <div className="container-x">
          <div className="relative overflow-hidden rounded-3xl bg-navy-900 px-6 py-14 text-center text-white sm:px-12" data-reveal>
            <div className="absolute -right-20 -top-24 size-72 rounded-full bg-orange-500/25 blur-3xl" aria-hidden />
            <h2 className="relative text-3xl font-bold text-white sm:text-4xl">Ready when you land.</h2>
            <p className="relative mx-auto mt-3 max-w-xl text-white/75">Reserve your car now and we'll be waiting at arrivals — or ask us anything on WhatsApp first.</p>
            <div className="relative mt-8 flex flex-wrap justify-center gap-3">
              <Button to="/book" size="lg">Book your car</Button>
              {wa && <Button href={wa} target="_blank" rel="noopener noreferrer" variant="whatsapp" size="lg" icon={MessageCircle}>WhatsApp us</Button>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
