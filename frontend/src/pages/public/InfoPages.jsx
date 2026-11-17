import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Baby, BadgeCheck, Car, CheckCircle2, Clock, Compass, FileText, Fuel, HeartHandshake, Mail, MapPin,
  MessageCircle, Phone, Plane, ShieldCheck, Sun,
} from "lucide-react";
import { api } from "../../lib/api";
import { useBookingOptions, useReveal, useSite } from "../../lib/hooks";
import { priceOf, zoneFee } from "../../lib/content";
import { usd, whatsappLink } from "../../lib/format";
import { Seo, businessJsonLd } from "../../lib/seo";
import { Alert, Button, Field } from "../../components/ui";

/* ------------------------------------------------------------------ About */
export function About() {
  const ref = useReveal();
  const { data: site } = useSite();
  return (
    <div ref={ref}>
      <Seo title="About Us — Local Car Hire in Zanzibar" path="/about"
        description="Rafiki Car Hire is a Zanzibar-based car rental company offering reliable self-drive vehicles, honest pricing and friendly local support." />
      <section className="relative overflow-hidden bg-navy-900 text-white">
        <div className="absolute -left-32 top-0 size-[28rem] rounded-full bg-orange-500/20 blur-3xl" aria-hidden />
        <div className="container-x relative grid gap-10 py-20 sm:py-28 lg:grid-cols-2 lg:items-end">
          <div>
            <p className="eyebrow text-orange-400">About Rafiki</p>
            <h1 className="mt-4 text-4xl font-bold text-white sm:text-6xl">Your friend on the road in Zanzibar.</h1>
          </div>
          <p className="text-lg leading-relaxed text-white/75">
            <em>Rafiki</em> is Swahili for “friend”. We started Rafiki Car Hire to give visitors the freedom of a self-drive holiday with the reassurance of a local team who knows every road, ferry time and beach turn-off on the island.
          </p>
        </div>
      </section>
      <section className="container-x grid gap-12 py-20 lg:grid-cols-3">
        {[
          { icon: HeartHandshake, t: "Honest & transparent", d: "One clear price in US dollars, an itemised invoice the moment you book, and a receipt for every payment. No surprises at the counter." },
          { icon: Car, t: "Cars we trust", d: "Our vehicles are inspected and cleaned between every rental, and chosen for Zanzibar's mix of town streets and coastal roads." },
          { icon: Compass, t: "Local knowledge", d: "Ask us anything — the quickest route to Nungwi, where to fill up, or how checkpoints work. We're here on WhatsApp throughout your trip." },
        ].map((v, i) => (
          <div key={v.t} data-reveal={i * 80}>
            <span className="grid size-12 place-items-center rounded-2xl bg-orange-100 text-orange-600"><v.icon className="size-6" /></span>
            <h2 className="mt-5 text-2xl font-bold">{v.t}</h2>
            <p className="mt-3 leading-relaxed text-muted">{v.d}</p>
          </div>
        ))}
      </section>
      <section className="bg-sand-50">
        <div className="container-x grid gap-10 py-20 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <div data-reveal>
            <h2 className="text-3xl font-bold sm:text-4xl">Who we serve</h2>
            <p className="mt-4 leading-relaxed text-muted">
              Holidaymakers and families exploring beyond the resort, business travellers who need dependable transport, and residents who need a car for a week or a month. Whoever you are, you get the same care — from your first message to the moment you hand back the keys.
            </p>
          </div>
          <div className="card p-7" data-reveal>
            <p className="font-display text-xl font-semibold text-navy-900">“{site?.tagline || "Drive Zanzibar with Confidence."}”</p>
            <p className="mt-3 text-muted">That's our promise — and the standard we hold every booking to.</p>
            <Button to="/fleet" className="mt-6">Meet the fleet</Button>
          </div>
        </div>
      </section>
    </div>
  );
}

/* ---------------------------------------------------------------- Contact */
export function Contact() {
  const { data: site } = useSite();
  const [f, setF] = useState({ name: "", email: "", phone: "", subject: "", message: "", website: "" });
  const [state, setState] = useState({ busy: false, done: false, error: null, fields: {} });
  const wa = whatsappLink(site?.whatsapp_number, "Hello Rafiki Car Hire!");
  const submit = async (e) => {
    e.preventDefault();
    setState({ busy: true, done: false, error: null, fields: {} });
    try {
      await api.post("/contact/", f);
      setState({ busy: false, done: true, error: null, fields: {} });
    } catch (err) {
      setState({ busy: false, done: false, error: err.message, fields: err.fieldErrors?.() || {} });
    }
  };
  return (
    <>
      <Seo title="Contact Us" path="/contact" description="Contact Rafiki Car Hire in Zanzibar by WhatsApp, phone or email for car hire questions, airport delivery and custom quotes."
        jsonLd={businessJsonLd(site)} />
      <section className="container-x grid gap-12 py-14 sm:py-20 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <p className="eyebrow">Contact</p>
          <h1 className="mt-3 text-4xl font-bold sm:text-5xl">Let's plan your drive.</h1>
          <p className="mt-4 max-w-md text-lg text-muted">The quickest way to reach us is WhatsApp. We usually reply within the hour during the day (EAT, UTC+3).</p>
          <ul className="mt-8 space-y-4">
            {wa && <li><a href={wa} target="_blank" rel="noopener noreferrer" className="card flex items-center gap-4 p-4 transition hover:shadow-[var(--shadow-lift)]"><span className="grid size-11 place-items-center rounded-xl bg-[#1FAF38] text-white"><MessageCircle className="size-5" /></span><span><span className="block font-semibold">WhatsApp</span><span className="text-sm text-muted">+{site.whatsapp_number}</span></span></a></li>}
            {site?.business_phone && <li><a href={`tel:${site.business_phone}`} className="card flex items-center gap-4 p-4"><span className="grid size-11 place-items-center rounded-xl bg-navy-50 text-navy-700"><Phone className="size-5" /></span><span><span className="block font-semibold">Phone</span><span className="text-sm text-muted">{site.business_phone}</span></span></a></li>}
            {site?.business_email && <li><a href={`mailto:${site.business_email}`} className="card flex items-center gap-4 p-4"><span className="grid size-11 place-items-center rounded-xl bg-navy-50 text-navy-700"><Mail className="size-5" /></span><span><span className="block font-semibold">Email</span><span className="text-sm text-muted">{site.business_email}</span></span></a></li>}
            <li className="card flex items-center gap-4 p-4"><span className="grid size-11 place-items-center rounded-xl bg-navy-50 text-navy-700"><MapPin className="size-5" /></span><span><span className="block font-semibold">Based in</span><span className="text-sm text-muted">{site?.business_address || "Zanzibar, Tanzania"}</span></span></li>
          </ul>
        </div>
        <div className="card p-6 sm:p-8">
          {state.done ? (
            <div className="py-10 text-center">
              <CheckCircle2 className="mx-auto size-12 text-emerald-600" />
              <h2 className="mt-4 text-2xl font-bold">Message sent</h2>
              <p className="mt-2 text-muted">Thank you, {f.name.split(" ")[0]}. We'll reply to {f.email} soon.</p>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-5">
              <h2 className="text-2xl font-bold">Send us a message</h2>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Name" required error={state.fields.name}>{(a) => <input {...a} className="input" required autoComplete="name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />}</Field>
                <Field label="Email" required error={state.fields.email}>{(a) => <input {...a} type="email" required className="input" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />}</Field>
                <Field label="Phone (optional)">{(a) => <input {...a} type="tel" className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />}</Field>
                <Field label="Subject">{(a) => <input {...a} className="input" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} />}</Field>
              </div>
              <Field label="Message" required error={state.fields.message}>{(a) => <textarea {...a} required rows={5} maxLength={4000} className="input" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} />}</Field>
              <input type="text" name="website" tabIndex={-1} autoComplete="off" className="hidden" value={f.website} onChange={(e) => setF({ ...f, website: e.target.value })} aria-hidden />
              {state.error && <Alert tone="error">{state.error}</Alert>}
              <Button type="submit" size="lg" loading={state.busy} className="w-full sm:w-auto">Send message</Button>
            </form>
          )}
        </div>
      </section>
    </>
  );
}

/* --------------------------------------------------------- Before You Rent */
export function BeforeYouRent() {
  const { data: o } = useBookingOptions();
  const ref = useReveal([o]);
  const p = (v) => (v ? usd(v) : "—");
  const sections = [
    { icon: FileText, t: "Documents you'll need", items: [
      "A valid passport (or national ID for residents).",
      "A valid driving licence from your home country, held for long enough to meet our rental terms.",
      `A Zanzibar driving permit. Visitors need one to drive legally; we can arrange it for ${p(priceOf(o, "driving_permit"))} when you upload copies of your passport and licence while booking. Approval is decided by the issuing authority.`,
    ] },
    { icon: Plane, t: "Pickup & return", items: [
      "Zanzibar Airport (Abeid Amani Karume International) — free.",
      "Zanzibar Town, including Stone Town hotels — free.",
      `Anywhere outside the free zone — ${p(zoneFee(o))} per leg. Pickup and return are charged separately.`,
      "Add your flight number and we'll adjust if your flight is delayed.",
    ] },
    { icon: Clock, t: "Rental days & timing", items: [
      "Each started 24-hour period counts as one rental day.",
      `Bookings are held for ${o?.hold_hours ?? 24} hours while we confirm them — you'll get an email either way.`,
      "Need to change your dates? Contact us — we'll update your booking and send a revised invoice.",
    ] },
    { icon: Baby, t: "Travelling with children", items: [
      `Child and baby seats are ${p(priceOf(o, "baby_seat"))} per seat for your whole booking (not per day).`,
      "Choose how many you need in step 6 of the booking form.",
    ] },
    { icon: Fuel, t: "On the road", items: [
      "Zanzibar drives on the LEFT. Speed limits are low, especially through villages — watch for pedestrians, cyclists and speed bumps.",
      "Police checkpoints are common; stop when asked and have your licence and permit ready.",
      "Fuel stations are plentiful around Stone Town but sparser on the coasts — fill up before long drives.",
    ] },
    { icon: ShieldCheck, t: "Payments & paperwork", items: [
      "Prices are in US dollars. You receive an itemised invoice immediately after booking.",
      "Pay online or manually (bank transfer, mobile money). Manual payments are verified by our team before they count.",
      "A receipt is issued for every verified payment. An invoice on its own is not proof of payment.",
    ] },
  ];
  return (
    <div ref={ref}>
      <Seo title="Before You Rent — Driving in Zanzibar Guide" path="/before-you-rent"
        description="Everything to know before hiring a car in Zanzibar: driving permits, documents, airport delivery, child seats, payments and local driving tips." />
      <section className="bg-orange-50">
        <div className="container-x py-14 sm:py-20">
          <p className="eyebrow">Before you rent</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-bold sm:text-5xl">Everything you need for a smooth start.</h1>
          <p className="mt-4 max-w-2xl text-lg text-muted">A two-minute read that answers the questions most of our guests ask before they land.</p>
        </div>
      </section>
      <section className="container-x grid gap-6 py-14 md:grid-cols-2">
        {sections.map((s, i) => (
          <div key={s.t} className="card p-6 sm:p-7" data-reveal={(i % 2) * 80}>
            <h2 className="flex items-center gap-3 text-xl font-bold"><span className="grid size-10 place-items-center rounded-xl bg-navy-900 text-orange-400"><s.icon className="size-5" /></span>{s.t}</h2>
            <ul className="mt-5 space-y-3">
              {s.items.map((it) => <li key={it} className="flex gap-3 leading-relaxed text-muted"><BadgeCheck className="mt-0.5 size-5 shrink-0 text-orange-600" />{it}</li>)}
            </ul>
          </div>
        ))}
      </section>
      <section className="container-x pb-20">
        <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-navy-900 p-8 text-white sm:flex-row sm:items-center">
          <div className="flex items-center gap-4"><Sun className="size-10 text-orange-400" /><p className="text-xl font-semibold">Ready? It takes about three minutes to book.</p></div>
          <Button to="/book" size="lg">Book your car</Button>
        </div>
      </section>
    </div>
  );
}

/* -------------------------------------------------------------- Legal */
function Legal({ title, path, description, updated, children }) {
  return (
    <>
      <Seo title={title} path={path} description={description} />
      <article className="container-x max-w-3xl py-14 sm:py-20">
        <p className="eyebrow">Legal</p>
        <h1 className="mt-3 text-4xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-muted">Last updated {updated}</p>
        <div className="mt-10 space-y-8 leading-relaxed text-[15.5px] text-ink [&_h2]:mb-3 [&_h2]:text-xl [&_h2]:font-bold [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-1.5 [&_p]:text-muted [&_li]:text-muted">
          {children}
        </div>
      </article>
    </>
  );
}

export function Privacy() {
  const { data: site } = useSite();
  return (
    <Legal title="Privacy Policy" path="/privacy" updated="November 2026" description="How Rafiki Car Hire collects, uses, protects and deletes your personal information.">
      <section><h2>Who we are</h2><p>{site?.business_name || "Rafiki Car Hire"} ("we", "us") provides car rental services in Zanzibar, Tanzania. We are responsible for the personal information you give us when you make an enquiry or booking.</p></section>
      <section><h2>What we collect</h2><ul>
        <li>Contact details: name, email address, phone number and nationality.</li>
        <li>Booking details: dates, pickup and return locations, flight information and selected services.</li>
        <li>Identity documents: copies of your passport and driving licence, only if you ask us to arrange a driving permit.</li>
        <li>Payment records: amounts, references and proof of payment. Card details are entered on our payment provider's secure page — we never see or store your card number.</li>
      </ul></section>
      <section><h2>How we use it</h2><p>We use your information to process and manage your booking, issue invoices and receipts, arrange permits you request, contact you about your rental, meet legal and accounting obligations, and keep our services secure. We do not sell your data or use it for third-party advertising.</p></section>
      <section><h2>How we protect it</h2><ul>
        <li>All data is transmitted over encrypted connections (HTTPS).</li>
        <li>Identity documents are kept in private storage that is never publicly accessible, and only authorised staff can view them. Each access is logged.</li>
        <li>We never send passport or licence copies by email or WhatsApp.</li>
        <li>Your booking page is protected by a private, expiring access link.</li>
      </ul></section>
      <section><h2>How long we keep it</h2><p>Passport and licence copies are securely deleted after your rental ends (or after a booking is cancelled), once they are no longer needed. Booking, invoice and payment records are kept for as long as required for accounting and legal purposes.</p></section>
      <section><h2>Your rights</h2><p>You can ask us for a copy of your information, to correct it, or to delete it where we are not legally required to keep it. Contact us{site?.business_email ? ` at ${site.business_email}` : ""} and we will respond promptly.</p></section>
    </Legal>
  );
}

export function Terms() {
  const { data: o } = useBookingOptions();
  return (
    <Legal title="Terms & Conditions" path="/terms" updated="November 2026" description="Rental terms and conditions for Rafiki Car Hire, Zanzibar.">
      <section><h2>1. Bookings</h2><p>A booking request reserves the selected vehicle for {o?.hold_hours ?? 24} hours while we review it. A booking is confirmed only when we confirm it in writing. We may decline a request, in which case any payment you have made is refunded.</p></section>
      <section><h2>2. Prices &amp; invoices</h2><p>All prices are in US dollars and are calculated by our booking system at the time of booking. Your invoice is issued immediately. If your booking is changed, we issue a revised invoice; the original remains on record. An invoice is not a receipt — a receipt is issued for each verified payment.</p></section>
      <section><h2>3. Payments</h2><p>You may pay online through our payment provider or manually by the methods we accept. Manual payments count towards your booking only after we have verified them. Online payments count only after the provider confirms them to us.</p></section>
      <section><h2>4. Rental period</h2><p>Each started 24-hour period is charged as one rental day. Please return the vehicle at the agreed time and place; late returns may be charged as additional days.</p></section>
      <section><h2>5. Pickup &amp; return locations</h2><p>Handover at Zanzibar Airport and in Zanzibar Town is free. Locations outside the free zone carry a delivery fee{o ? ` of ${usd(o.locations.find((l) => l.code === "OUTSIDE_ZONE")?.fee)}` : ""} for each leg.</p></section>
      <section><h2>6. Drivers &amp; documents</h2><p>Every driver must hold a valid driving licence and carry it, together with any required Zanzibar driving permit, while driving. Our permit arrangement service helps you apply; approval is decided by the issuing authority and is not guaranteed by payment of the arrangement fee.</p></section>
      <section><h2>7. Use of the vehicle</h2><ul>
        <li>Drive lawfully, carefully and within the island's speed limits.</li>
        <li>Do not drive under the influence of alcohol or drugs, carry more passengers than the vehicle's seats, or sub-let the vehicle.</li>
        <li>Report any accident, damage or breakdown to us immediately.</li>
      </ul></section>
      <section><h2>8. Cancellations</h2><p>Please tell us as early as possible if you need to cancel. Refunds for cancellations are handled according to the cancellation terms set out in your booking confirmation.</p></section>
      <section><h2>9. Contact</h2><p>Questions about these terms? <Link to="/contact" className="font-semibold text-navy-700 underline">Contact us</Link>.</p></section>
    </Legal>
  );
}

export function NotFound() {
  return (
    <div className="container-x py-24 text-center">
      <Seo title="Page not found" noindex />
      <p className="font-display text-7xl font-bold text-orange-500">404</p>
      <h1 className="mt-4 text-3xl font-bold">This road doesn't go anywhere.</h1>
      <p className="mt-2 text-muted">The page you're looking for has moved or never existed.</p>
      <div className="mt-8 flex justify-center gap-3"><Button to="/">Go home</Button><Button to="/fleet" variant="outline">See the fleet</Button></div>
    </div>
  );
}
