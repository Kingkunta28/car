import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Baby, BadgeCheck, Car, CheckCircle2, Clock, Compass, FileText, Fuel, HeartHandshake, Mail, MapPin,
  MessageCircle, Phone, Plane, ShieldCheck, Sun,
} from "lucide-react";
import { api } from "../../lib/api";
import { useBookingOptions, useReveal, useSite } from "../../lib/hooks";
import { zoneFee } from "../../lib/content";
import { fmtDate, usd, whatsappLink } from "../../lib/format";
import { Seo, businessJsonLd } from "../../lib/seo";
import { Alert, Button, Field } from "../../components/ui";
import PageHero from "../../components/PageHero";
import ZanzibarMap from "../../components/ZanzibarMap";

/* ------------------------------------------------------------------ About */
export function About() {
  const { t } = useTranslation();
  const ref = useReveal();
  const { data: site } = useSite();
  return (
    <div ref={ref}>
      <Seo title={t("home.why")} path="/about" description={t("home.lead")} />
      <PageHero tone="navy" eyebrow={t("home.why")} title={t("home.title")} accent={t("home.accent")}
        lead={t("home.lead")} />
      <section className="container-x grid gap-12 py-20 lg:grid-cols-3">
        {[
          { icon: HeartHandshake, title: t("home.paperwork"), body: t("home.paperworkText") },
          { icon: Car, title: t("home.fleetTitle"), body: t("home.fleetLead") },
          { icon: Compass, title: t("home.realPeople"), body: t("home.realPeopleText") },
        ].map((v, i) => (
          <div key={v.title} data-reveal={i * 80}>
            <span className="grid size-12 place-items-center rounded-2xl bg-orange-100 text-orange-600"><v.icon className="size-6" /></span>
            <h2 className="mt-5 text-2xl font-bold">{v.title}</h2>
            <p className="mt-3 leading-relaxed text-muted">{v.body}</p>
          </div>
        ))}
      </section>
      <section className="bg-sand-50">
        <div className="container-x grid gap-10 py-20 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <div data-reveal>
            <h2 className="text-3xl font-bold sm:text-4xl">{t("home.storiesTitle")}</h2>
            <p className="mt-4 leading-relaxed text-muted">{t("home.drivingLead")}</p>
          </div>
          <div className="card p-7" data-reveal>
            <p className="font-display text-xl font-semibold text-navy-900">“{site?.tagline || "Drive Zanzibar with Confidence."}”</p>
            <p className="mt-3 text-muted">{t("home.readyText")}</p>
            <Button to="/fleet" className="mt-6">{t("home.viewFleet")}</Button>
          </div>
        </div>
      </section>
    </div>
  );
}

/* ---------------------------------------------------------------- Contact */
export function Contact() {
  const { t } = useTranslation();
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
      <Seo title={t("footer.contact")} path="/contact" description={t("contact.lead")}
        jsonLd={businessJsonLd(site)} />
      <section className="container-x grid gap-12 py-14 sm:py-20 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <p className="eyebrow">{t("footer.contact")}</p>
          <h1 className="display-lg mt-4">{t("contact.title")}</h1>
          <p className="mt-4 max-w-md text-lg text-muted">{t("contact.lead")}</p>
          <ul className="mt-8 space-y-4">
            {wa && <li><a href={wa} target="_blank" rel="noopener noreferrer" className="card flex items-center gap-4 p-4 transition hover:shadow-[var(--shadow-lift)]"><span className="grid size-11 place-items-center rounded-xl bg-[#1FAF38] text-white"><MessageCircle className="size-5" /></span><span><span className="block font-semibold">{t("contact.whatsapp")}</span><span className="text-sm text-muted">{site.business_phone || `+${site.whatsapp_number}`}</span></span></a></li>}
            {site?.business_phone && <li><a href={`tel:${site.business_phone}`} className="card flex items-center gap-4 p-4"><span className="grid size-11 place-items-center rounded-xl bg-navy-50 text-navy-700"><Phone className="size-5" /></span><span><span className="block font-semibold">{t("footer.phone")}</span><span className="text-sm text-muted">{site.business_phone}</span></span></a></li>}
            {site?.business_email && <li><a href={`mailto:${site.business_email}`} className="card flex items-center gap-4 p-4"><span className="grid size-11 place-items-center rounded-xl bg-navy-50 text-navy-700"><Mail className="size-5" /></span><span><span className="block font-semibold">{t("footer.email")}</span><span className="text-sm text-muted">{site.business_email}</span></span></a></li>}
            <li><a href={`https://maps.google.com/?q=${encodeURIComponent(site?.business_address || "Zanzibar, Tanzania")}`} target="_blank" rel="noopener noreferrer" className="card card-hover flex items-center gap-4 p-4"><span className="grid size-11 place-items-center rounded-xl bg-navy-50 text-navy-700"><MapPin className="size-5" /></span><span><span className="block font-semibold">{t("contact.find")}</span><span className="text-sm text-muted">{site?.business_address || "Zanzibar, Tanzania"}</span><span className="block text-xs font-semibold text-orange-600">{t("contact.openMap")}</span></span></a></li>
          </ul>
        </div>
        <div className="card p-6 sm:p-8">
          {state.done ? (
            <div className="py-10 text-center">
              <CheckCircle2 className="mx-auto size-12 text-emerald-600" />
              <h2 className="mt-4 text-2xl font-bold">{t("contact.sent")}</h2>
              <p className="mt-2 text-muted">{t("contact.thanks", { name: f.name.split(" ")[0], email: f.email })}</p>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-5">
              <h2 className="text-2xl font-bold">{t("contact.heading")}</h2>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label={t("contact.name")} required error={state.fields.name}>{(a) => <input {...a} className="input" required autoComplete="name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />}</Field>
                <Field label={t("footer.email")} required error={state.fields.email}>{(a) => <input {...a} type="email" required className="input" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />}</Field>
                <Field label={t("contact.phoneOptional")}>{(a) => <input {...a} type="tel" className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />}</Field>
                <Field label={t("contact.subject")}>{(a) => <input {...a} className="input" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} />}</Field>
              </div>
              <Field label={t("contact.message")} required error={state.fields.message}>{(a) => <textarea {...a} required rows={5} maxLength={4000} className="input" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} />}</Field>
              <input type="text" name="website" tabIndex={-1} autoComplete="off" className="hidden" value={f.website} onChange={(e) => setF({ ...f, website: e.target.value })} aria-hidden />
              {state.error && <Alert tone="error">{state.error}</Alert>}
              <Button type="submit" size="lg" loading={state.busy} className="w-full sm:w-auto">{t("contact.send")}</Button>
            </form>
          )}
        </div>
      </section>
      <section className="container-x pb-20" aria-label={t("contact.map")}>
        <div className="overflow-hidden rounded-[var(--radius-panel)] border border-line shadow-[var(--shadow-card)]">
          <iframe title={`Map: ${site?.business_address || "Zanzibar, Tanzania"}`} loading="lazy" referrerPolicy="no-referrer-when-downgrade"
            src={`https://maps.google.com/maps?q=${encodeURIComponent(site?.business_address || "Zanzibar, Tanzania")}&z=13&output=embed`}
            className="block h-[360px] w-full border-0 sm:h-[440px]" />
        </div>
      </section>
    </>
  );
}

/* --------------------------------------------------------- Before You Rent */
export function BeforeYouRent() {
  const { t } = useTranslation();
  const { data: o } = useBookingOptions();
  const ref = useReveal([o]);
  const sections = [
    { id: "permit", icon: FileText, title: t("booking.passport"), keys: ["booking.passport", "booking.licence", "vehicle.permit"] },
    { icon: Plane, title: t("home.delivery"), keys: ["vehicle.delivery", "booking.flightOptional"] },
    { icon: Clock, title: t("booking.duration"), keys: ["booking.durationRule", "booking.holdNotice", "booking.instructions"] },
    { icon: Baby, title: t("home.children"), keys: ["vehicle.childSeat", "booking.babySeats"] },
    { icon: Fuel, title: t("home.driving"), keys: ["home.drivingLead", "vehicle.permit", "vehicle.fuelNotIncluded"] },
    { id: "booking", icon: ShieldCheck, title: t("booking.payment"), keys: ["booking.manualDescription", "booking.documentPrivacy", "booking.paymentInstructions"] },
  ];
  return (
    <div ref={ref}>
      <Seo title={t("footer.bookingInfo")} path="/before-you-rent" description={t("booking.permitDescription")} />
      <PageHero eyebrow={t("footer.bookingInfo")} title={t("vehicle.conditions")} accent={t("home.ready")}
        lead={t("booking.documentPrivacy")} />
      <section className="container-x py-14">
        <div className="card grid gap-8 p-5 sm:p-8 lg:grid-cols-[1fr_1fr] lg:items-center">
          <div>
            <p className="eyebrow">{t("home.deliveryEyebrow")}</p>
            <h2 className="display-md mt-3">{t("home.deliveryTitle")}</h2>
            <p className="mt-3 leading-relaxed text-muted">{t("vehicle.delivery")}</p>
          </div>
          <ZanzibarMap fee={zoneFee(o)} />
        </div>
      </section>
      <section className="container-x grid gap-6 pb-14 md:grid-cols-2">
        {sections.map((s, i) => (
          <div key={s.t} id={s.id} className="card scroll-mt-28 p-6 sm:p-7" data-reveal={(i % 2) * 80}>
            <h2 className="flex items-center gap-3 text-xl font-bold"><span className="grid size-10 place-items-center rounded-xl bg-navy-900 text-orange-400"><s.icon className="size-5" /></span>{s.title}</h2>
            <ul className="mt-5 space-y-3">
              {s.keys.map((key) => <li key={key} className="flex gap-3 leading-relaxed text-muted"><BadgeCheck className="mt-0.5 size-5 shrink-0 text-orange-600" />{t(key, { hours: o?.hold_hours ?? 24 })}</li>)}
            </ul>
          </div>
        ))}
      </section>
      <section className="container-x pb-20">
        <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-navy-900 p-8 text-white sm:flex-row sm:items-center">
          <div className="flex items-center gap-4"><Sun className="size-10 text-orange-400" /><p className="text-xl font-semibold">{t("home.readyText")}</p></div>
          <Button to="/book" size="lg">{t("home.book")}</Button>
        </div>
      </section>
    </div>
  );
}

/* -------------------------------------------------------------- Legal */
function Legal({ title, path, description, updated, children }) {
  const { t } = useTranslation();
  return (
    <>
      <Seo title={title} path={path} description={description} />
      <article className="container-x max-w-3xl py-14 sm:py-20">
        <p className="eyebrow">{t("info.legal.eyebrow")}</p>
        <h1 className="mt-3 text-4xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-muted">{t("info.legal.updated", { date: updated })}</p>
        <div className="mt-10 space-y-8 leading-relaxed text-[15.5px] text-ink [&_h2]:mb-3 [&_h2]:text-xl [&_h2]:font-bold [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-1.5 [&_p]:text-muted [&_li]:text-muted">
          {children}
        </div>
      </article>
    </>
  );
}

export function Privacy() {
  const { t } = useTranslation();
  const { data: site } = useSite();
  return (
    <Legal title={t("footer.privacy")} path="/privacy" updated={fmtDate("2026-11-01", { month: "long", year: "numeric" })} description={t("footer.privacy")}>
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
  const { t } = useTranslation();
  const { data: o } = useBookingOptions();
  return (
    <Legal title={t("footer.terms")} path="/terms" updated={fmtDate("2026-11-01", { month: "long", year: "numeric" })} description={t("footer.terms")}>
      <section><h2>1. Bookings</h2><p>A booking request reserves the selected vehicle for {o?.hold_hours ?? 24} hours while we review it. A booking is confirmed only when we confirm it in writing. We may decline a request, in which case any payment you have made is refunded.</p></section>
      <section><h2>2. Prices &amp; invoices</h2><p>All prices are in US dollars and are calculated by our booking system at the time of booking. Your invoice is issued immediately. If your booking is changed, we issue a revised invoice; the original remains on record. An invoice is not a receipt — a receipt is issued for each verified payment.</p></section>
      <section><h2>3. Payments</h2><p>Payment is currently made manually using the methods we accept. A manual payment counts towards your booking only after we have verified it.</p></section>
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
  const { t } = useTranslation();
  return (
    <div className="container-x py-24 text-center">
      <Seo title={t("info.notFound.title")} noindex />
      <p className="font-display text-7xl font-bold text-orange-500">404</p>
      <h1 className="mt-4 text-3xl font-bold">{t("info.notFound.heading")}</h1>
      <p className="mt-2 text-muted">{t("info.notFound.text")}</p>
      <div className="mt-8 flex justify-center gap-3"><Button to="/">{t("info.notFound.home")}</Button><Button to="/fleet" variant="outline">{t("info.notFound.fleet")}</Button></div>
    </div>
  );
}
