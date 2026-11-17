import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, CheckCircle2, Clock, Download, Home, MapPin, MessageCircle, Settings } from "lucide-react";
import { api, download } from "../../lib/api";
import { fmtDate, fmtDateTime, fmtTime, usd } from "../../lib/format";
import { loadGuest } from "../../lib/guest";
import { Seo } from "../../lib/seo";
import { Alert, Badge, Button, Skeleton, useToast } from "../../components/ui";
import { VehicleImage } from "../../components/VehicleCard";

function Row({ label, value, strong }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <dt className={strong ? "font-semibold text-navy-900" : "text-muted"}>{label}</dt>
      <dd className={strong ? "font-display text-xl font-bold text-navy-900 tabular-nums" : "tabular-nums text-navy-900"}>{value}</dd>
    </div>
  );
}

export default function Confirmation() {
  const { state } = useLocation();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const guest = loadGuest();
  // Full booking details come from the backend (authorised by the guest token), never from the form.
  const booking = useQuery({ queryKey: ["guest-booking", guest?.reference], enabled: !!guest && !!state,
    queryFn: () => api.get("/bookings/track/", { guest }), retry: 1 });
  if (!state || !guest) return <Navigate to="/booking/manage" replace />;
  const b = booking.data;

  const getInvoice = async () => {
    setBusy(true);
    try {
      await download("/invoices/download/", { guest, params: { invoice: state.invoice_number } }, `${state.invoice_number}.pdf`);
    } catch (e) {
      toast(e.message || "Download failed — please try again.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Seo title="Booking received" noindex />
      <section className="bg-sand-50">
        <div className="container-x max-w-5xl py-14 sm:py-20">
          <div className="stagger text-center">
            <span className="mx-auto grid size-16 place-items-center rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 className="size-9" /></span>
            <p className="eyebrow mt-6 justify-center">Booking submitted</p>
            <h1 className="display-lg mt-3">Asante, {b?.customer?.full_name?.split(" ")[0] || "we've got it"}.</h1>
            <p className="lead mx-auto mt-4 max-w-xl">Your car is reserved and your invoice is on its way by email. Our team will confirm your booking shortly.</p>
          </div>

          <div className="mt-12 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            {/* Booking card */}
            <div className="card overflow-hidden">
              <div className="grid gap-px bg-line sm:grid-cols-2">
                <div className="bg-white p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted">Booking reference</p><p className="mt-1 font-display text-2xl font-bold tracking-wide text-navy-900">{state.booking_reference}</p></div>
                <div className="bg-white p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted">Invoice number</p><p className="mt-1 font-display text-2xl font-bold text-navy-900">{state.invoice_number}</p></div>
              </div>
              {booking.isLoading ? <div className="space-y-3 p-5"><Skeleton className="h-32" /><Skeleton className="h-16" /></div> : b ? (
                <div className="p-5">
                  <div className="flex gap-4">
                    <div className="h-20 w-28 shrink-0 overflow-hidden rounded-xl bg-slate-100"><VehicleImage vehicle={b.vehicle} image={b.vehicle.image ? { url: b.vehicle.image } : null} /></div>
                    <div>
                      <p className="font-display text-lg font-semibold text-navy-900">{b.vehicle.name}</p>
                      <p className="text-sm text-muted">{b.vehicle.transmission} · {b.vehicle.passenger_capacity} seats</p>
                      <p className="mt-1 text-sm text-muted">{b.rental_days} day{b.rental_days > 1 ? "s" : ""}</p>
                    </div>
                  </div>
                  <dl className="mt-5 grid gap-4 border-t border-line pt-5 sm:grid-cols-2">
                    <div className="flex gap-3"><CalendarDays className="mt-0.5 size-5 shrink-0 text-orange-600" /><div><dt className="text-xs font-semibold uppercase tracking-wider text-muted">Pickup</dt>
                      <dd className="text-sm text-navy-900">{fmtDate(b.pickup_date)}, {fmtTime(b.pickup_time)}</dd>
                      <dd className="text-sm text-muted">{b.pickup_type_display}{b.pickup_area && ` — ${b.pickup_area}`}</dd></div></div>
                    <div className="flex gap-3"><MapPin className="mt-0.5 size-5 shrink-0 text-orange-600" /><div><dt className="text-xs font-semibold uppercase tracking-wider text-muted">Return</dt>
                      <dd className="text-sm text-navy-900">{fmtDate(b.return_date)}, {fmtTime(b.return_time)}</dd>
                      <dd className="text-sm text-muted">{b.return_type_display}{b.return_area && ` — ${b.return_area}`}</dd></div></div>
                  </dl>
                </div>
              ) : <Alert tone="info" className="m-5">Your full booking details are in the email we just sent.</Alert>}
              <div className="flex items-start gap-3 border-t border-line bg-sand-50 p-5 text-sm text-muted">
                <Clock className="mt-0.5 size-5 shrink-0 text-orange-600" />
                <p>Your car is held until <strong className="text-navy-900">{fmtDateTime(state.hold_expires_at)}</strong> while we confirm. An invoice is not a receipt — you'll receive a receipt for each payment once it's verified.</p>
              </div>
            </div>

            {/* Summary & actions */}
            <div className="space-y-6">
              <div className="card p-5">
                <div className="flex flex-wrap gap-2">
                  <Badge status={state.booking_status}>{state.booking_status_display}</Badge>
                  <Badge status={b?.payment_status || state.payment_status}>{b?.payment_status_display || state.payment_status_display}</Badge>
                  <Badge tone="slate">{state.payment_method_display}</Badge>
                </div>
                <dl className="mt-4 divide-y divide-line">
                  {b && <>
                    <Row label={`Rental · ${b.rental_days} × ${usd(b.daily_rate)}`} value={usd(b.rental_total)} />
                    <Row label="Pickup fee" value={Number(b.pickup_fee) ? usd(b.pickup_fee) : "Free"} />
                    <Row label="Return fee" value={Number(b.return_fee) ? usd(b.return_fee) : "Free"} />
                    {b.extras.map((e) => <Row key={e.code} label={`${e.service_name} × ${e.quantity}`} value={usd(e.total_price)} />)}
                    {Number(b.tax_amount) > 0 && <Row label="Tax" value={usd(b.tax_amount)} />}
                  </>}
                  <Row label="Total (USD)" value={usd(state.grand_total)} strong />
                </dl>
              </div>
              <div className="space-y-2.5">
                <Button onClick={getInvoice} loading={busy} icon={Download} size="lg" className="w-full">Download invoice PDF</Button>
                <Button to="/booking/manage" variant="navy" size="lg" icon={Settings} className="w-full">
                  {state.payment_method === "ONLINE" ? "Pay now & view booking" : "View booking & payment"}
                </Button>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {state.whatsapp_url && <Button href={state.whatsapp_url} target="_blank" rel="noopener noreferrer" variant="whatsapp" icon={MessageCircle}>WhatsApp us</Button>}
                  <Button to="/" variant="outline" icon={Home} className={state.whatsapp_url ? "" : "sm:col-span-2"}>Back to home</Button>
                </div>
              </div>
              <p className="text-center text-xs text-muted">Keep the email we sent you — its private link lets you return to this booking at any time.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
