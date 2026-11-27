import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Clock, Download, FileText, KeyRound, MessageCircle, Receipt } from "lucide-react";
import { api, download } from "../../lib/api";
import { fmtDate, fmtTime, usd, whatsappLink } from "../../lib/format";
import { useSite } from "../../lib/hooks";
import { getBusinessInfo } from "../../data/businessInfo";
import { clearGuest, loadGuest, saveGuest } from "../../lib/guest";
import { Seo } from "../../lib/seo";
import { Alert, Badge, Button, ErrorState, Field, PageLoader, useToast } from "../../components/ui";
import { VehicleImage } from "../../components/VehicleCard";

function AccessForm({ onAccess }) {
  const { t } = useTranslation();
  const [ref, setRef] = useState("");
  const [token, setToken] = useState("");
  return (
    <div className="container-x max-w-lg py-16">
      <span className="grid size-12 place-items-center rounded-2xl bg-navy-50 text-navy-700"><KeyRound className="size-6" /></span>
      <h1 className="mt-5 text-3xl font-bold">{t("manage.title")}</h1>
      <p className="mt-2 text-muted">{t("manage.intro")}</p>
      <form className="mt-8 space-y-4" onSubmit={(e) => { e.preventDefault(); saveGuest(ref.trim().toUpperCase(), token.trim()); onAccess(); }}>
        <Field label={t("manage.reference")} required>{(a) => <input {...a} className="input uppercase" placeholder={t("manage.referencePlaceholder")} value={ref} onChange={(e) => setRef(e.target.value)} required />}</Field>
        <Field label={t("manage.accessCode")} required hint={t("manage.accessHint")}>{(a) => <input {...a} className="input" value={token} onChange={(e) => setToken(e.target.value)} required autoComplete="off" />}</Field>
        <Button type="submit" className="w-full" size="lg">{t("manage.open")}</Button>
      </form>
      <p className="mt-6 text-sm text-muted">{t("manage.lostEmail")}</p>
    </div>
  );
}

export default function ManageBooking() {
  const { t } = useTranslation();
  const [guest, setGuest] = useState(() => loadGuest());
  const toast = useToast();
  const [confirmationBusy, setConfirmationBusy] = useState(false);
  const { data: site } = useSite();
  const business = getBusinessInfo(site);
  const wa = whatsappLink(business.whatsappNumber, `Hello Rafiki Car Hire, I need a new link for my booking ${guest?.reference || ""}.`);
  const q = useQuery({
    queryKey: ["guest-booking", guest?.reference], enabled: !!guest, retry: false,
    queryFn: () => api.get("/bookings/track/", { guest }),
  });

  if (!guest) return (<><Seo title={t("manage.title")} noindex /><AccessForm onAccess={() => setGuest(loadGuest())} /></>);
  if (q.isLoading) return <PageLoader />;
  if (q.error) {
    const expired = q.error.status === 404;
    return (
      <div className="container-x max-w-xl py-20 text-center">
        <Seo title={t("manage.title")} noindex />
        {expired ? (
          <>
            <span className="mx-auto grid size-16 place-items-center rounded-full bg-orange-100 text-orange-600"><Clock className="size-8" /></span>
            <h1 className="display-md mt-6">{t("manage.expired")}</h1>
            <p className="lead mt-3">{t("manage.expiredText")}</p>
          </>
        ) : <ErrorState error={q.error} onRetry={q.refetch} title={t("manage.openError")} />}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {wa && <Button href={wa} target="_blank" rel="noopener noreferrer" variant="whatsapp" icon={MessageCircle}>{t("manage.newLink")}</Button>}
          <Button variant="outline" onClick={() => { clearGuest(); setGuest(null); }}>{t("manage.manual")}</Button>
        </div>
      </div>
    );
  }

  const b = q.data;
  const bookingWhatsApp = whatsappLink(business.whatsappNumber, `Hello Rafiki Car Hire, I have a question about booking ${b.booking_reference}.`);
  const dl = async (path, params, name) => {
    try { await download(path, { guest, params }, name); } catch (e) { toast(e.message, "error"); }
  };
  const downloadConfirmation = async () => {
    setConfirmationBusy(true);
    try { await download("/bookings/confirmation/download/", { guest }, `${b.booking_reference}-confirmation.pdf`); }
    catch (e) { toast(e.message || "Download failed — please try again.", "error"); }
    finally { setConfirmationBusy(false); }
  };
  return (
    <>
      <Seo title={`Booking ${b.booking_reference}`} noindex />
      <div className="border-b border-line bg-sand-50">
        <div className="container-x flex flex-col gap-4 py-10 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">{t("manage.yourBooking")}</p>
            <h1 className="mt-2 font-display text-3xl font-bold tracking-wide sm:text-4xl">{b.booking_reference}</h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge status={b.booking_status}>{b.booking_status === "PENDING_CONFIRMATION" ? t("manage.awaiting") : b.booking_status_display}</Badge>
              <Badge status={b.payment_status}>{b.payment_status_display}</Badge>
            </div>
          </div>
          {bookingWhatsApp && <Button href={bookingWhatsApp} target="_blank" rel="noopener noreferrer" variant="whatsapp" icon={MessageCircle}>{t("manage.contactWhatsApp")}</Button>}
        </div>
      </div>

      <div className="container-x grid gap-8 py-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          {b.booking_status === "PENDING_CONFIRMATION" && (
            <Alert tone="info" title={t("manage.awaiting")}>{t("manage.awaitingText")}</Alert>
          )}
          <div className="card overflow-hidden sm:flex">
            <div className="aspect-[16/10] sm:aspect-auto sm:w-64 shrink-0 bg-slate-100"><VehicleImage vehicle={b.vehicle} image={b.vehicle.image ? { url: b.vehicle.image } : null} /></div>
            <dl className="grid flex-1 gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2"><dt className="text-sm text-muted">{t("manage.vehicle")}</dt><dd className="font-semibold">{b.vehicle.name}</dd></div>
              <div><dt className="text-sm text-muted">{t("manage.pickup")}</dt><dd className="font-medium">{fmtDate(b.pickup_date)}, {fmtTime(b.pickup_time)}</dd><dd className="text-sm text-muted">{b.pickup_type_display}{b.pickup_area && ` — ${b.pickup_area}`}{b.pickup_address && <><br />{b.pickup_address}</>}</dd></div>
              <div><dt className="text-sm text-muted">{t("manage.return")}</dt><dd className="font-medium">{fmtDate(b.return_date)}, {fmtTime(b.return_time)}</dd><dd className="text-sm text-muted">{b.return_type_display}{b.return_area && ` — ${b.return_area}`}{b.return_address && <><br />{b.return_address}</>}</dd></div>
            </dl>
          </div>

          <div className="card flex flex-wrap items-center justify-between gap-3 p-5">
            <div><h2 className="font-semibold">{t("manage.confirmation")}</h2><p className="mt-1 text-sm text-muted">{t("manage.confirmationText")}</p></div>
            <Button size="sm" variant="outline" icon={Download} loading={confirmationBusy} onClick={downloadConfirmation}>{t("manage.download")}</Button>
          </div>

          <div className="card p-5">
            <h2 className="flex items-center gap-2 text-lg font-semibold"><FileText className="size-5 text-navy-600" /> {t("manage.invoices")}</h2>
            <ul className="mt-3 divide-y divide-line">
              {b.invoices.map((i) => (
                <li key={i.invoice_number} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-medium">{i.invoice_number} {i.invoice_status === "SUPERSEDED" && <Badge status="SUPERSEDED">{t("manage.replaced")}</Badge>}</p>
                    <p className="text-sm text-muted">{fmtDate(i.issue_date)} · {usd(i.total_amount)}</p>
                  </div>
                  <Button size="sm" variant="outline" icon={Download} onClick={() => dl("/invoices/download/", { invoice: i.invoice_number }, `${i.invoice_number}.pdf`)}>PDF</Button>
                </li>
              ))}
            </ul>
          </div>

          {(b.receipts.length > 0 || b.payments.length > 0) && (
            <div className="card p-5">
              <h2 className="flex items-center gap-2 text-lg font-semibold"><Receipt className="size-5 text-navy-600" /> {t("manage.payments")}</h2>
              <ul className="mt-3 divide-y divide-line">
                {b.payments.map((p) => (
                  <li key={p.payment_reference} className="flex items-center justify-between gap-3 py-3 text-sm">
                    <span><span className="font-medium text-navy-900">{usd(p.amount)}</span> · {p.payment_method} · {fmtDate(p.created_at)}</span>
                    <Badge status={p.status}>{p.status_display}</Badge>
                  </li>
                ))}
                {b.receipts.map((r) => (
                  <li key={r.receipt_number} className="flex items-center justify-between gap-3 py-3">
                    <span className="text-sm">{t("manage.receipt")} <strong>{r.receipt_number}</strong> · {usd(r.amount)}</span>
                    <Button size="sm" variant="outline" icon={Download} onClick={() => dl("/receipts/download/", { receipt: r.receipt_number }, `${r.receipt_number}.pdf`)}>PDF</Button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className="card p-5">
            <h2 className="text-lg font-semibold">{t("manage.summary")}</h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-muted">{t("manage.rental", { days: b.rental_days })}</dt><dd>{usd(b.rental_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">{t("manage.pickupFee")}</dt><dd>{Number(b.pickup_fee) ? usd(b.pickup_fee) : t("manage.free")}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">{t("manage.returnFee")}</dt><dd>{Number(b.return_fee) ? usd(b.return_fee) : t("manage.free")}</dd></div>
              {b.extras.map((e) => <div key={e.code} className="flex justify-between"><dt className="text-muted">{e.code === "baby_seat" ? t("booking.babySeats") : e.code === "driving_permit" ? t("booking.permit") : e.service_name} × {e.quantity}</dt><dd>{usd(e.total_price)}</dd></div>)}
              {Number(b.tax_amount) > 0 && <div className="flex justify-between"><dt className="text-muted">{t("manage.tax")}</dt><dd>{usd(b.tax_amount)}</dd></div>}
              <div className="flex justify-between border-t border-line pt-3 font-semibold"><dt>{t("manage.total")}</dt><dd>{usd(b.grand_total)}</dd></div>
              <div className="flex justify-between text-emerald-700"><dt>{t("manage.paid")}</dt><dd>{usd(b.amount_paid)}</dd></div>
              <div className="flex justify-between font-display text-lg font-bold text-navy-900"><dt>{t("manage.balance")}</dt><dd>{usd(b.balance_due)}</dd></div>
            </dl>
            {b.payment_method === "MANUAL" && Number(b.balance_due) > 0 && (
              <Alert tone="info" className="mt-5">{t("manage.localPaymentNote")}</Alert>
            )}
          </div>
          {b.documents.length > 0 && (
            <div className="card p-5 text-sm">
              <h2 className="font-semibold">{t("manage.permitDocs")}</h2>
              <ul className="mt-2 space-y-1 text-muted">{b.documents.map((d) => <li key={d.document_type}>{d.document_type}: {d.status}</li>)}</ul>
              <p className="mt-3 text-xs text-muted">{t("manage.storedDocs")}</p>
            </div>
          )}
          <button className="text-sm text-muted underline underline-offset-4" onClick={() => { clearGuest(); setGuest(null); }}>{t("manage.signOut")}</button>
        </aside>
      </div>

    </>
  );
}
