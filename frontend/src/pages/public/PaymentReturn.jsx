import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, Clock, RotateCcw, XCircle } from "lucide-react";
import { api } from "../../lib/api";
import { usd } from "../../lib/format";
import { Seo } from "../../lib/seo";
import { Button, Spinner } from "../../components/ui";

/** Pesapal redirects here. We never trust the redirect itself — the backend
 *  checks the transaction with the gateway before anything is marked paid. */
export default function PaymentReturn() {
  const { t } = useTranslation();
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
  let icon = <Clock className="size-9 text-amber-600" />, title = "processing", text = "processingText";
  if (cancelled || !trackingId) { icon = <XCircle className="size-9 text-slate-500" />; title = "notCompleted"; text = "notCompletedText"; }
  else if (d?.status === "VERIFIED") { icon = <CheckCircle2 className="size-9 text-emerald-600" />; title = "confirmed"; text = "confirmedText"; }
  else if (d?.status === "FAILED") { icon = <XCircle className="size-9 text-red-600" />; title = "failed"; text = "failedText"; }
  else if (state.error) { title = "checkError"; text = "checkErrorText"; }

  return (
    <div className="container-x max-w-xl py-20 text-center">
      <Seo title={t("paymentStatus.title")} noindex />
      <span className="mx-auto grid size-16 place-items-center rounded-full bg-slate-100">{state.loading ? <Spinner /> : icon}</span>
      <h1 className="mt-6 text-3xl font-bold">{state.loading ? t("paymentStatus.checking") : t(`paymentStatus.${title}`)}</h1>
      {!state.loading && <p className="mt-3 text-lg text-muted">{t(`paymentStatus.${text}`, { amount: usd(d?.amount), reference: d?.booking_reference })}</p>}
      {d && !state.loading && <p className="mt-4 text-sm text-muted">{t("paymentStatus.status")} <strong>{d.booking_payment_status}</strong> · {t("paymentStatus.balance")} {usd(d.balance_due)}</p>}
      {!state.loading && (
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {(cancelled || !trackingId || d?.status === "FAILED")
            ? <><Button to="/booking/manage" size="lg" icon={RotateCcw}>{t("paymentStatus.tryAgain")}</Button><Button to="/booking/manage" size="lg" variant="outline">{t("paymentStatus.manual")}</Button></>
            : <Button to="/booking/manage" size="lg" arrow>{t("paymentStatus.booking")}</Button>}
        </div>
      )}
    </div>
  );
}
