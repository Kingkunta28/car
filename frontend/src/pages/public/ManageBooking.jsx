import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Download, FileText, KeyRound, Landmark, MessageCircle, Receipt, Upload } from "lucide-react";
import { api, download } from "../../lib/api";
import { fmtDate, fmtDateTime, fmtTime, usd } from "../../lib/format";
import { clearGuest, loadGuest, saveGuest } from "../../lib/guest";
import { Seo } from "../../lib/seo";
import { Alert, Badge, Button, ErrorState, Field, Modal, PageLoader, useToast } from "../../components/ui";
import { VehicleImage } from "../../components/VehicleCard";

function AccessForm({ onAccess }) {
  const [ref, setRef] = useState("");
  const [token, setToken] = useState("");
  return (
    <div className="container-x max-w-lg py-16">
      <span className="grid size-12 place-items-center rounded-2xl bg-navy-50 text-navy-700"><KeyRound className="size-6" /></span>
      <h1 className="mt-5 text-3xl font-bold">Manage your booking</h1>
      <p className="mt-2 text-muted">Open the private link in your booking email — it signs you in automatically. Or paste your reference and access code below.</p>
      <form className="mt-8 space-y-4" onSubmit={(e) => { e.preventDefault(); saveGuest(ref.trim().toUpperCase(), token.trim()); onAccess(); }}>
        <Field label="Booking reference" required>{(a) => <input {...a} className="input uppercase" placeholder="RCH-XXXXXXX" value={ref} onChange={(e) => setRef(e.target.value)} required />}</Field>
        <Field label="Access code" required hint="The long code after “token=” in your email link.">{(a) => <input {...a} className="input" value={token} onChange={(e) => setToken(e.target.value)} required autoComplete="off" />}</Field>
        <Button type="submit" className="w-full" size="lg">Open booking</Button>
      </form>
      <p className="mt-6 text-sm text-muted">Lost the email? Contact us with your booking reference and we'll resend it.</p>
    </div>
  );
}

function ManualPaymentForm({ guest, booking, onDone }) {
  const toast = useToast();
  const [f, setF] = useState({ amount: booking.balance_due, channel: "BANK_TRANSFER", transaction_reference: "", note: "" });
  const [proof, setProof] = useState(null);
  const [err, setErr] = useState({});
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr({});
    try {
      const form = new FormData();
      Object.entries(f).forEach(([k, v]) => form.append(k, v));
      if (proof) form.append("proof", proof);
      await api.upload("/payments/manual/", form, { guest });
      toast("Thank you — we'll verify your payment and send a receipt.");
      onDone();
    } catch (ex) {
      setErr({ ...ex.fieldErrors?.(), _: ex.message });
    } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-4">
      {booking.payment_options?.manual?.instructions && (
        <div className="rounded-xl bg-sand-50 p-4 text-sm"><p className="font-semibold">Payment instructions</p><p className="mt-1 whitespace-pre-line text-muted">{booking.payment_options.manual.instructions}</p></div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Amount paid (USD)" required error={err.amount}>{(a) => <input {...a} type="number" step="0.01" min="0.01" max={booking.balance_due} className="input" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} />}</Field>
        <Field label="Method" required error={err.channel}>{(a) => (
          <select {...a} className="input" value={f.channel} onChange={(e) => setF({ ...f, channel: e.target.value })}>
            <option value="BANK_TRANSFER">Bank transfer</option><option value="MOBILE_MONEY">Mobile money</option><option value="OTHER">Other</option>
          </select>)}</Field>
      </div>
      <Field label="Transaction reference" error={err.transaction_reference} hint="From your bank or mobile-money receipt">{(a) => <input {...a} className="input" value={f.transaction_reference} onChange={(e) => setF({ ...f, transaction_reference: e.target.value })} />}</Field>
      <Field label="Proof of payment (optional)" error={err.proof} hint="PDF, JPG or PNG">{(a) => <input {...a} type="file" accept=".pdf,.jpg,.jpeg,.png" className="input" onChange={(e) => setProof(e.target.files?.[0] || null)} />}</Field>
      <Field label="Note (optional)">{(a) => <textarea {...a} rows={2} className="input" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />}</Field>
      {err._ && <Alert tone="error">{err._}</Alert>}
      <Button type="submit" loading={busy} icon={Upload} className="w-full">Submit payment details</Button>
    </form>
  );
}

export default function ManageBooking() {
  const [guest, setGuest] = useState(() => loadGuest());
  const qc = useQueryClient();
  const toast = useToast();
  const [modal, setModal] = useState(null);
  const [paying, setPaying] = useState(false);
  const q = useQuery({
    queryKey: ["guest-booking", guest?.reference], enabled: !!guest, retry: false,
    queryFn: () => api.get("/bookings/track/", { guest }),
  });

  if (!guest) return (<><Seo title="Manage booking" noindex /><AccessForm onAccess={() => setGuest(loadGuest())} /></>);
  if (q.isLoading) return <PageLoader />;
  if (q.error) return (
    <div className="container-x max-w-xl py-16">
      <Seo title="Manage booking" noindex />
      <ErrorState error={q.error} title="We couldn't open this booking" />
      <Button variant="outline" className="mt-6" onClick={() => { clearGuest(); setGuest(null); }}>Enter details manually</Button>
    </div>
  );

  const b = q.data;
  const refresh = () => qc.invalidateQueries({ queryKey: ["guest-booking"] });
  const canPay = Number(b.balance_due) > 0 && ["PENDING_CONFIRMATION", "CONFIRMED"].includes(b.booking_status);
  const dl = async (path, params, name) => {
    try { await download(path, { guest, params }, name); } catch (e) { toast(e.message, "error"); }
  };
  const payOnline = async () => {
    setPaying(true);
    try {
      const res = await api.post("/payments/online/initiate/", { gateway: b.payment_options.online.gateways[0]?.code }, { guest });
      window.location.assign(res.redirect_url);
    } catch (e) {
      toast(e.message, "error");
      setPaying(false);
    }
  };

  return (
    <>
      <Seo title={`Booking ${b.booking_reference}`} noindex />
      <div className="border-b border-line bg-sand-50">
        <div className="container-x flex flex-col gap-4 py-10 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">Your booking</p>
            <h1 className="mt-2 font-display text-3xl font-bold tracking-wide sm:text-4xl">{b.booking_reference}</h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge status={b.booking_status}>{b.booking_status_display}</Badge>
              <Badge status={b.payment_status}>{b.payment_status_display}</Badge>
            </div>
          </div>
          {b.whatsapp_url && <Button href={b.whatsapp_url} target="_blank" rel="noopener noreferrer" variant="whatsapp" icon={MessageCircle}>Contact us on WhatsApp</Button>}
        </div>
      </div>

      <div className="container-x grid gap-8 py-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          {b.booking_status === "PENDING_CONFIRMATION" && (
            <Alert tone="warning" title="Awaiting confirmation">We're holding the car until {fmtDateTime(b.hold_expires_at)}. You'll get an email as soon as we confirm.</Alert>
          )}
          <div className="card overflow-hidden sm:flex">
            <div className="aspect-[16/10] sm:aspect-auto sm:w-64 shrink-0 bg-slate-100"><VehicleImage vehicle={b.vehicle} image={b.vehicle.image ? { url: b.vehicle.image } : null} /></div>
            <dl className="grid flex-1 gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2"><dt className="text-sm text-muted">Vehicle</dt><dd className="font-semibold">{b.vehicle.name}</dd></div>
              <div><dt className="text-sm text-muted">Pickup</dt><dd className="font-medium">{fmtDate(b.pickup_date)}, {fmtTime(b.pickup_time)}</dd><dd className="text-sm text-muted">{b.pickup_type_display}{b.pickup_area && ` — ${b.pickup_area}`}{b.pickup_address && <><br />{b.pickup_address}</>}</dd></div>
              <div><dt className="text-sm text-muted">Return</dt><dd className="font-medium">{fmtDate(b.return_date)}, {fmtTime(b.return_time)}</dd><dd className="text-sm text-muted">{b.return_type_display}{b.return_area && ` — ${b.return_area}`}{b.return_address && <><br />{b.return_address}</>}</dd></div>
            </dl>
          </div>

          <div className="card p-5">
            <h2 className="flex items-center gap-2 text-lg font-semibold"><FileText className="size-5 text-navy-600" /> Invoices</h2>
            <ul className="mt-3 divide-y divide-line">
              {b.invoices.map((i) => (
                <li key={i.invoice_number} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-medium">{i.invoice_number} {i.invoice_status === "SUPERSEDED" && <Badge status="SUPERSEDED">Replaced</Badge>}</p>
                    <p className="text-sm text-muted">{fmtDate(i.issue_date)} · {usd(i.total_amount)}</p>
                  </div>
                  <Button size="sm" variant="outline" icon={Download} onClick={() => dl("/invoices/download/", { invoice: i.invoice_number }, `${i.invoice_number}.pdf`)}>PDF</Button>
                </li>
              ))}
            </ul>
          </div>

          {(b.receipts.length > 0 || b.payments.length > 0) && (
            <div className="card p-5">
              <h2 className="flex items-center gap-2 text-lg font-semibold"><Receipt className="size-5 text-navy-600" /> Payments &amp; receipts</h2>
              <ul className="mt-3 divide-y divide-line">
                {b.payments.map((p) => (
                  <li key={p.payment_reference} className="flex items-center justify-between gap-3 py-3 text-sm">
                    <span><span className="font-medium text-navy-900">{usd(p.amount)}</span> · {p.payment_method} · {fmtDate(p.created_at)}</span>
                    <Badge status={p.status}>{p.status_display}</Badge>
                  </li>
                ))}
                {b.receipts.map((r) => (
                  <li key={r.receipt_number} className="flex items-center justify-between gap-3 py-3">
                    <span className="text-sm">Receipt <strong>{r.receipt_number}</strong> · {usd(r.amount)}</span>
                    <Button size="sm" variant="outline" icon={Download} onClick={() => dl("/receipts/download/", { receipt: r.receipt_number }, `${r.receipt_number}.pdf`)}>PDF</Button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className="card p-5">
            <h2 className="text-lg font-semibold">Price summary</h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-muted">Rental ({b.rental_days} days)</dt><dd>{usd(b.rental_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Pickup fee</dt><dd>{Number(b.pickup_fee) ? usd(b.pickup_fee) : "Free"}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Return fee</dt><dd>{Number(b.return_fee) ? usd(b.return_fee) : "Free"}</dd></div>
              {b.extras.map((e) => <div key={e.code} className="flex justify-between"><dt className="text-muted">{e.service_name} × {e.quantity}</dt><dd>{usd(e.total_price)}</dd></div>)}
              {Number(b.tax_amount) > 0 && <div className="flex justify-between"><dt className="text-muted">Tax</dt><dd>{usd(b.tax_amount)}</dd></div>}
              <div className="flex justify-between border-t border-line pt-3 font-semibold"><dt>Total</dt><dd>{usd(b.grand_total)}</dd></div>
              <div className="flex justify-between text-emerald-700"><dt>Paid</dt><dd>{usd(b.amount_paid)}</dd></div>
              <div className="flex justify-between font-display text-lg font-bold text-navy-900"><dt>Balance due</dt><dd>{usd(b.balance_due)}</dd></div>
            </dl>
            {canPay && (
              <div className="mt-5 space-y-2.5">
                {b.payment_options?.online?.available && <Button className="w-full" size="lg" icon={CreditCard} loading={paying} onClick={payOnline}>Pay {usd(b.balance_due)} online</Button>}
                <Button className="w-full" variant="outline" icon={Landmark} onClick={() => setModal("manual")}>I've paid manually</Button>
              </div>
            )}
          </div>
          {b.documents.length > 0 && (
            <div className="card p-5 text-sm">
              <h2 className="font-semibold">Permit documents</h2>
              <ul className="mt-2 space-y-1 text-muted">{b.documents.map((d) => <li key={d.document_type}>{d.document_type}: {d.status}</li>)}</ul>
              <p className="mt-3 text-xs text-muted">Stored privately and deleted after your rental.</p>
            </div>
          )}
          <button className="text-sm text-muted underline underline-offset-4" onClick={() => { clearGuest(); setGuest(null); }}>Sign out of this booking</button>
        </aside>
      </div>

      <Modal open={modal === "manual"} onClose={() => setModal(null)} title="Submit a manual payment">
        <ManualPaymentForm guest={guest} booking={b} onDone={() => { setModal(null); refresh(); }} />
      </Modal>
    </>
  );
}
