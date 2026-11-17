import { useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { CheckCircle2, Clock, Download, MessageCircle, Settings } from "lucide-react";
import { download } from "../../lib/api";
import { fmtDateTime, usd } from "../../lib/format";
import { loadGuest } from "../../lib/guest";
import { Seo } from "../../lib/seo";
import { Alert, Badge, Button, useToast } from "../../components/ui";

export default function Confirmation() {
  const { state } = useLocation();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const guest = loadGuest();
  if (!state || !guest) return <Navigate to="/booking/manage" replace />;

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
      <section className="bg-gradient-to-b from-sand-50 to-white">
        <div className="container-x max-w-3xl py-14 sm:py-20">
          <div className="text-center">
            <span className="mx-auto grid size-16 place-items-center rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 className="size-9" /></span>
            <h1 className="mt-6 text-3xl font-bold sm:text-4xl">Booking submitted — asante!</h1>
            <p className="mx-auto mt-3 max-w-xl text-lg text-muted">
              We've reserved the car and emailed your invoice. Our team will review your booking and confirm it shortly.
            </p>
          </div>

          <div className="card mt-10 divide-y divide-line">
            <dl className="grid gap-6 p-6 sm:grid-cols-2">
              <div><dt className="text-sm text-muted">Booking reference</dt><dd className="mt-1 font-display text-2xl font-bold tracking-wide text-navy-900">{state.booking_reference}</dd></div>
              <div><dt className="text-sm text-muted">Invoice number</dt><dd className="mt-1 font-display text-2xl font-bold text-navy-900">{state.invoice_number}</dd></div>
              <div><dt className="text-sm text-muted">Booking status</dt><dd className="mt-1.5"><Badge status={state.booking_status}>{state.booking_status_display}</Badge></dd></div>
              <div><dt className="text-sm text-muted">Payment status</dt><dd className="mt-1.5"><Badge status={state.payment_status}>{state.payment_status_display}</Badge></dd></div>
              <div><dt className="text-sm text-muted">Total amount</dt><dd className="mt-1 font-display text-2xl font-bold text-navy-900">{usd(state.grand_total)} <span className="text-base font-medium text-muted">USD</span></dd></div>
              <div><dt className="text-sm text-muted">Payment method</dt><dd className="mt-1 font-semibold text-navy-900">{state.payment_method_display}</dd></div>
            </dl>
            <div className="flex items-start gap-3 p-6 text-sm text-muted">
              <Clock className="mt-0.5 size-5 shrink-0 text-orange-600" />
              <p>Your car is held until <strong className="text-navy-900">{fmtDateTime(state.hold_expires_at)}</strong> while we confirm. The invoice is not a receipt — you'll get a receipt for each payment once it's verified.</p>
            </div>
            <div className="flex flex-wrap gap-3 p-6">
              <Button onClick={getInvoice} loading={busy} icon={Download} size="lg">Download invoice (PDF)</Button>
              <Button to="/booking/manage" variant="navy" size="lg" icon={Settings}>{state.payment_method === "ONLINE" ? "Pay now & manage booking" : "Manage booking & payment"}</Button>
              {state.whatsapp_url && (
                <Button href={state.whatsapp_url} target="_blank" rel="noopener noreferrer" variant="whatsapp" size="lg" icon={MessageCircle}>Send details on WhatsApp</Button>
              )}
            </div>
          </div>
          <Alert tone="info" className="mt-6">
            Keep the email we sent you — its private link lets you return to your booking, download invoices and pay at any time.
            {" "}<Link to="/fleet" className="font-semibold underline">Back to the fleet</Link>
          </Alert>
        </div>
      </section>
    </>
  );
}
