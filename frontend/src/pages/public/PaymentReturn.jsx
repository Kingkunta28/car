import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, Clock, RotateCcw, XCircle } from "lucide-react";
import { api } from "../../lib/api";
import { usd } from "../../lib/format";
import { Seo } from "../../lib/seo";
import { Button, Spinner } from "../../components/ui";

/** Pesapal redirects here. We never trust the redirect itself — the backend
 *  checks the transaction with the gateway before anything is marked paid. */
export default function PaymentReturn() {
  const [sp] = useSearchParams();
  const trackingId = sp.get("OrderTrackingId");
  const cancelled = sp.get("cancelled") === "1";
  const [state, setState] = useState({ loading: !!trackingId && !cancelled, data: null, error: null });

  useEffect(() => {
    if (!trackingId || cancelled) return;
    let tries = 0, stop = false;
    const check = async () => {
      try {
        const data = await api.post("/payments/online/verify/", { order_tracking_id: trackingId });
        if (stop) return;
        if (data.status === "INITIATED" && tries++ < 5) { setTimeout(check, 3000); setState({ loading: true, data, error: null }); return; }
        setState({ loading: false, data, error: null });
      } catch (e) {
        if (!stop) setState({ loading: false, data: null, error: e });
      }
    };
    check();
    return () => { stop = true; };
  }, [trackingId, cancelled]);

  const d = state.data;
  let icon = <Clock className="size-9 text-amber-600" />, title = "Payment processing", text = "We're waiting for confirmation from the payment provider. This can take a minute — we'll email your receipt as soon as it's confirmed.";
  if (cancelled || !trackingId) { icon = <XCircle className="size-9 text-slate-500" />; title = "Payment not completed"; text = "No payment was taken. You can try again from your booking page whenever you're ready."; }
  else if (d?.status === "VERIFIED") { icon = <CheckCircle2 className="size-9 text-emerald-600" />; title = "Payment confirmed"; text = `Thank you — ${usd(d.amount)} has been received for booking ${d.booking_reference}. Your receipt is on its way by email.`; }
  else if (d?.status === "FAILED") { icon = <XCircle className="size-9 text-red-600" />; title = "Payment failed"; text = "The payment didn't go through and no money was taken. Please try again or choose manual payment."; }
  else if (state.error) { title = "We couldn't check your payment"; text = "Don't worry — if the payment succeeded it will still be confirmed automatically. Check your booking page shortly."; }

  return (
    <div className="container-x max-w-xl py-20 text-center">
      <Seo title="Payment status" noindex />
      <span className="mx-auto grid size-16 place-items-center rounded-full bg-slate-100">{state.loading ? <Spinner /> : icon}</span>
      <h1 className="mt-6 text-3xl font-bold">{state.loading ? "Checking your payment…" : title}</h1>
      {!state.loading && <p className="mt-3 text-lg text-muted">{text}</p>}
      {d && !state.loading && <p className="mt-4 text-sm text-muted">Payment status: <strong>{d.booking_payment_status}</strong> · Balance due {usd(d.balance_due)}</p>}
      {!state.loading && (
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {(cancelled || !trackingId || d?.status === "FAILED")
            ? <><Button to="/booking/manage" size="lg" icon={RotateCcw}>Try again</Button><Button to="/booking/manage" size="lg" variant="outline">Pay manually instead</Button></>
            : <Button to="/booking/manage" size="lg" arrow>Go to my booking</Button>}
        </div>
      )}
    </div>
  );
}
