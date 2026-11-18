import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Ban, Check, CheckCheck, Download, Eye, FileText, Flag, MessageCircle, Pencil, Plane, Plus, Send, X,
} from "lucide-react";
import { api, download } from "../../lib/api";
import { fmtDate, fmtDateTime, fmtTime, usd } from "../../lib/format";
import { Alert, Badge, Button, ErrorState, Field, Modal, PageLoader, useToast } from "../../components/ui";
import { can, FINANCE, useAdmin } from "./AdminShell";

const ACTIONS = {
  CONFIRMED: { path: "confirm", label: "Confirm booking", icon: Check, variant: "primary", needsReason: false },
  REJECTED: { path: "reject", label: "Reject", icon: X, variant: "danger", needsReason: true },
  CANCELLED: { path: "cancel", label: "Cancel booking", icon: Ban, variant: "outline", needsReason: true },
  COMPLETED: { path: "complete", label: "Mark completed", icon: Flag, variant: "navy", needsReason: false },
};

function Section({ title, children, actions }) {
  return (
    <section className="card overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
        <h2 className="font-semibold">{title}</h2>{actions}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function DL({ rows }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {rows.filter(Boolean).map(([k, v]) => (
        <div key={k}><dt className="text-xs font-semibold uppercase tracking-wider text-muted">{k}</dt><dd className="mt-0.5 text-[15px] text-navy-900">{v || "—"}</dd></div>
      ))}
    </dl>
  );
}

function StatusDialog({ action, booking, onClose, onDone }) {
  const toast = useToast();
  const [notes, setNotes] = useState("");
  const [notify, setNotify] = useState(true);
  const a = ACTIONS[action];
  const m = useMutation({
    mutationFn: () => api.post(`/admin/bookings/${booking.id}/${a.path}/`, { notes, notify_guest: notify }),
    onSuccess: (data) => { toast(`Booking ${data.booking_status_display.toLowerCase()}`); onDone(data); },
    onError: (e) => toast(e.message, "error"),
  });
  return (
    <Modal open onClose={onClose} title={a.label}
      footer={<><Button variant="ghost" onClick={onClose}>Back</Button>
        <Button variant={a.variant === "outline" ? "danger" : a.variant} loading={m.isPending}
          disabled={a.needsReason && !notes.trim()} onClick={() => m.mutate()}>{a.label}</Button></>}>
      <p className="text-sm text-muted">Booking <strong>{booking.booking_reference}</strong> for {booking.customer.full_name}.</p>
      {action === "CONFIRMED" && Number(booking.balance_due) > 0 && <Alert tone="warning" className="mt-3">Balance of {usd(booking.balance_due)} is still outstanding.</Alert>}
      {(action === "REJECTED" || action === "CANCELLED") && Number(booking.amount_paid) > 0 && (
        <Alert tone="warning" className="mt-3">The guest has paid {usd(booking.amount_paid)}. Record any refund from the payment record.</Alert>
      )}
      <Field label={a.needsReason ? "Reason (shared with the guest)" : "Message to guest (optional)"} className="mt-4">
        {(p) => <textarea {...p} rows={3} className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />}
      </Field>
      {action !== "COMPLETED" && (
        <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-navy-900" checked={notify} onChange={(e) => setNotify(e.target.checked)} /> Email the guest</label>
      )}
    </Modal>
  );
}

function ModifyDialog({ booking, onClose, onDone }) {
  const toast = useToast();
  const vehicles = useQuery({ queryKey: ["admin-vehicles-all"], queryFn: () => api.get("/admin/vehicles/", { params: { page_size: 100 } }) });
  const opts = useQuery({ queryKey: ["booking-options"], queryFn: () => api.get("/booking-options/") });
  const [f, setF] = useState({
    vehicle: booking.vehicle.id, pickup_date: booking.pickup_date, pickup_time: booking.pickup_time.slice(0, 5),
    return_date: booking.return_date, return_time: booking.return_time.slice(0, 5),
    pickup_type: booking.pickup_type, pickup_area: booking.pickup_area, pickup_address: booking.pickup_address,
    return_type: booking.return_type, return_area: booking.return_area, return_address: booking.return_address,
    extras: Object.fromEntries(booking.extras.map((e) => [e.code, e.quantity])), reason: "",
  });
  const [err, setErr] = useState({});
  const m = useMutation({
    mutationFn: () => api.post(`/admin/bookings/${booking.id}/modify/`, f),
    onSuccess: (d) => { toast(d.revised_invoice ? `Saved — revised invoice ${d.revised_invoice} issued and emailed` : "Booking updated"); onDone(d); },
    onError: (e) => { setErr({ ...e.fieldErrors(), _: e.message }); },
  });
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  return (
    <Modal open onClose={onClose} title="Modify booking" size="lg"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={m.isPending} disabled={!f.reason.trim()} onClick={() => m.mutate()}>Save changes</Button></>}>
      <Alert tone="info">Changes to the car, dates, locations or extras recalculate the price and issue a <strong>revised invoice</strong>. The original invoice is kept. The agreed daily rate is kept unless you change the car.</Alert>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Field label="Vehicle" className="sm:col-span-2" error={err.vehicle}>{(p) => (
          <select {...p} className="input" value={f.vehicle} onChange={(e) => set("vehicle", e.target.value)}>
            {(vehicles.data?.results || []).map((v) => <option key={v.id} value={v.id}>{v.name} — {usd(v.price_per_day)}/day</option>)}
          </select>)}</Field>
        <Field label="Pickup date" error={err.pickup_date}>{(p) => <input {...p} type="date" className="input" value={f.pickup_date} onChange={(e) => set("pickup_date", e.target.value)} />}</Field>
        <Field label="Pickup time">{(p) => <input {...p} type="time" className="input" value={f.pickup_time} onChange={(e) => set("pickup_time", e.target.value)} />}</Field>
        <Field label="Return date" error={err.return_date}>{(p) => <input {...p} type="date" className="input" value={f.return_date} onChange={(e) => set("return_date", e.target.value)} />}</Field>
        <Field label="Return time">{(p) => <input {...p} type="time" className="input" value={f.return_time} onChange={(e) => set("return_time", e.target.value)} />}</Field>
        {["pickup", "return"].map((leg) => (
          <div key={leg} className="space-y-3 rounded-xl border border-line p-3">
            <Field label={`${leg === "pickup" ? "Pickup" : "Return"} location`}>{(p) => (
              <select {...p} className="input" value={f[`${leg}_type`]} onChange={(e) => set(`${leg}_type`, e.target.value)}>
                {(opts.data?.locations || []).map((l) => <option key={l.code} value={l.code}>{l.label} ({Number(l.fee) ? usd(l.fee) : "free"})</option>)}
              </select>)}</Field>
            {f[`${leg}_type`] === "OUTSIDE_ZONE" && <Field label="Area" error={err[`${leg}_area`]}>{(p) => <input {...p} className="input" value={f[`${leg}_area`]} onChange={(e) => set(`${leg}_area`, e.target.value)} />}</Field>}
            {f[`${leg}_type`] !== "AIRPORT" && <Field label="Address" error={err[`${leg}_address`]}>{(p) => <input {...p} className="input" value={f[`${leg}_address`]} onChange={(e) => set(`${leg}_address`, e.target.value)} />}</Field>}
          </div>
        ))}
        <div className="sm:col-span-2">
          <p className="label">Extras</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {(opts.data?.extras || []).map((x) => (
              <label key={x.code} className="flex items-center justify-between gap-3 rounded-xl border border-line px-3 py-2 text-sm">
                <span>{x.name} ({usd(x.price)})</span>
                <input type="number" min="0" max={x.max_quantity} className="input w-20" value={f.extras[x.code] || 0}
                  onChange={(e) => set("extras", { ...f.extras, [x.code]: Math.max(0, Math.min(x.max_quantity, Number(e.target.value))) })} />
              </label>
            ))}
          </div>
        </div>
        <Field label="Reason for change (shown on revised invoice)" className="sm:col-span-2" error={err.reason}>{(p) => <input {...p} className="input" required value={f.reason} onChange={(e) => set("reason", e.target.value)} />}</Field>
      </div>
      {err._ && <Alert tone="error" className="mt-4">{err._}</Alert>}
    </Modal>
  );
}

function RecordPaymentDialog({ booking, onClose, onDone }) {
  const toast = useToast();
  const [f, setF] = useState({ booking: booking.id, amount: booking.balance_due, channel: "CASH", transaction_reference: "", notes: "" });
  const m = useMutation({
    mutationFn: () => api.post("/admin/payments/record/", f),
    onSuccess: () => { toast("Payment recorded and receipt issued"); onDone(); },
    onError: (e) => toast(e.message, "error"),
  });
  return (
    <Modal open onClose={onClose} title="Record a payment received"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={m.isPending} disabled={!f.notes.trim()} onClick={() => m.mutate()}>Record payment</Button></>}>
      <Alert tone="warning">Only record money you have actually received. This action is logged under your name and issues a receipt to the guest.</Alert>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Field label="Amount (USD)">{(p) => <input {...p} type="number" step="0.01" className="input" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} />}</Field>
        <Field label="Method">{(p) => (
          <select {...p} className="input" value={f.channel} onChange={(e) => setF({ ...f, channel: e.target.value })}>
            <option value="CASH">Cash</option><option value="BANK_TRANSFER">Bank transfer</option><option value="MOBILE_MONEY">Mobile money</option><option value="CARD">Card (terminal)</option><option value="OTHER">Other</option>
          </select>)}</Field>
        <Field label="Reference (optional)" className="sm:col-span-2">{(p) => <input {...p} className="input" value={f.transaction_reference} onChange={(e) => setF({ ...f, transaction_reference: e.target.value })} />}</Field>
        <Field label="How and when was it received?" className="sm:col-span-2">{(p) => <textarea {...p} rows={2} className="input" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />}</Field>
      </div>
    </Modal>
  );
}

export default function BookingDetail() {
  const { id } = useParams();
  const user = useAdmin();
  const qc = useQueryClient();
  const toast = useToast();
  const [dialog, setDialog] = useState(null);
  const [dossierBusy, setDossierBusy] = useState(false);
  const [note, setNote] = useState("");
  const key = ["admin-booking", id];
  const { data: b, isLoading, error, refetch } = useQuery({ queryKey: key, queryFn: () => api.get(`/admin/bookings/${id}/`) });
  const refresh = (data) => { if (data?.id) qc.setQueryData(key, data); else qc.invalidateQueries({ queryKey: key }); qc.invalidateQueries({ queryKey: ["admin-bookings"] }); setDialog(null); };
  const addNote = useMutation({
    mutationFn: () => api.post(`/admin/bookings/${id}/notes/`, { body: note }),
    onSuccess: () => { setNote(""); refresh(); toast("Note added"); },
  });
  const finance = can(user, ...FINANCE);

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;

  const docAction = async (doc, status) => {
    try { await api.post(`/admin/bookings/${id}/documents/${doc.id}/verify/`, { status }); refresh(); toast(`Document marked ${status.toLowerCase()}`); }
    catch (e) { toast(e.message, "error"); }
  };
  const dl = (path, opts = {}) => download(path, opts).catch((e) => toast(e.message, "error"));
  const downloadDossier = async () => {
    setDossierBusy(true);
    try { await download(`/admin/bookings/${id}/dossier/`); }
    catch (e) { toast(e.message || "The private dossier could not be downloaded.", "error"); }
    finally { setDossierBusy(false); }
  };
  const resendInvoice = async (inv) => {
    try { await api.post(`/admin/invoices/${inv.id}/resend/`, {}); toast(`Invoice emailed to ${b.customer.email}`); refresh(); }
    catch (e) { toast(e.message, "error"); }
  };
  const resendNotification = async (n) => {
    try { await api.post(`/admin/notifications/${n.id}/resend/`, {}); toast("Email queued"); refresh(); }
    catch (e) { toast(e.message, "error"); }
  };

  return (
    <>
      <Link to="/admin/bookings" className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700"><ArrowLeft className="size-4" /> All bookings</Link>
      <div className="mt-3 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-wide">{b.booking_reference}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge status={b.booking_status}>{b.booking_status_display}</Badge>
            <Badge status={b.payment_status}>{b.payment_status_display}</Badge>
            <Badge tone="slate">{b.payment_method_display}</Badge>
            {b.booking_status === "PENDING_CONFIRMATION" && <Badge tone="orange">Hold until {fmtDateTime(b.hold_expires_at)}</Badge>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {b.allowed_transitions.map((s) => ACTIONS[s] && (
            <Button key={s} variant={ACTIONS[s].variant} icon={ACTIONS[s].icon} onClick={() => setDialog(s)}>{ACTIONS[s].label}</Button>
          ))}
          {finance && ["PENDING_CONFIRMATION", "CONFIRMED"].includes(b.booking_status) && <Button variant="outline" icon={Pencil} onClick={() => setDialog("modify")}>Modify</Button>}
          {b.whatsapp?.to_guest && <Button href={b.whatsapp.to_guest} target="_blank" rel="noopener noreferrer" variant="whatsapp" icon={MessageCircle}>WhatsApp guest</Button>}
        </div>
      </div>
      {b.status_reason && <Alert tone="info" className="mt-4">{b.status_reason}</Alert>}

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <div className="space-y-6">
          <Section title="Guest">
            <DL rows={[["Name", <Link key="c" to={`/admin/customers/${b.customer.id}`} className="font-semibold text-navy-700 underline">{b.customer.full_name}</Link>],
              ["Email", <a key="e" href={`mailto:${b.customer.email}`} className="underline">{b.customer.email}</a>],
              ["Phone", <a key="p" href={`tel:${b.customer.phone}`} className="underline">{b.customer.phone}</a>], ["Nationality", b.customer.nationality],
              b.customer_notes && ["Guest notes", b.customer_notes]]} />
          </Section>
          <Section title="Rental">
            <DL rows={[["Vehicle", b.vehicle.name], ["Duration", `${b.rental_days} day(s) at ${usd(b.daily_rate)}`],
              ["Pickup", `${fmtDate(b.pickup_date)} ${fmtTime(b.pickup_time)}`], ["Return", `${fmtDate(b.return_date)} ${fmtTime(b.return_time)}`],
              ["Pickup location", <>{b.pickup_type_display}{b.pickup_area && ` — ${b.pickup_area}`}<br /><span className="text-muted">{b.pickup_address}</span>{b.pickup_instructions && <><br /><em className="text-muted">{b.pickup_instructions}</em></>}</>],
              ["Return location", <>{b.return_type_display}{b.return_area && ` — ${b.return_area}`}<br /><span className="text-muted">{b.return_address}</span>{b.return_instructions && <><br /><em className="text-muted">{b.return_instructions}</em></>}</>]]} />
          </Section>
          <Section title={<span className="flex items-center gap-2"><Plane className="size-4" /> Flight</span>}>
            {b.flight ? <DL rows={[["Airline", b.flight.airline_name], ["Flight no.", b.flight.flight_number],
              ["Arrival", `${b.flight.arrival_date ? fmtDate(b.flight.arrival_date) : ""} ${fmtTime(b.flight.arrival_time)}`], ["Airport", b.flight.arrival_airport], b.flight.notes && ["Notes", b.flight.notes]]} />
              : <p className="text-sm text-muted">No flight information provided.</p>}
          </Section>
          {b.documents.length > 0 && (
            <Section title="Permit documents (private)">
              {!finance && <p className="mb-3 text-sm text-muted">Only managers and administrators can open identity documents.</p>}
              <ul className="divide-y divide-line">
                {b.documents.map((d) => (
                  <li key={d.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div><p className="font-medium">{d.document_type_display}</p>
                      <p className="text-xs text-muted">{d.file_kind?.toUpperCase()} · {(d.file_size / 1024).toFixed(0)} KB · uploaded {fmtDateTime(d.uploaded_at)}{d.verified_by && ` · reviewed by ${d.verified_by}`}</p></div>
                    <div className="flex items-center gap-2">
                      <Badge status={d.verification_status}>{d.verification_status_display}</Badge>
                      {finance && d.has_file && <>
                        <Button size="sm" variant="outline" icon={Eye} onClick={() => dl(`/admin/bookings/${id}/documents/${d.id}/download/`, { params: { inline: 1 }, preview: true })}>View</Button>
                        {d.verification_status === "PENDING" && <>
                          <Button size="sm" variant="ghost" icon={CheckCheck} onClick={() => docAction(d, "VERIFIED")}>Verify</Button>
                          <Button size="sm" variant="ghost" icon={X} onClick={() => docAction(d, "REJECTED")}>Reject</Button>
                        </>}
                      </>}
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {finance && <Section title="Internal booking dossier · restricted"
            actions={<Button size="sm" variant="outline" icon={Download} loading={dossierBusy} onClick={downloadDossier}>Generate &amp; download</Button>}>
            <p className="text-sm text-muted">Private staff PDF with booking details and uploaded passport and driving licence pages. Identity files are never included in customer invoices or email attachments.</p>
          </Section>}
          <Section title="Internal notes">
            <form onSubmit={(e) => { e.preventDefault(); note.trim() && addNote.mutate(); }} className="flex gap-2">
              <input className="input" placeholder="Add a note for the team (never shown to the guest)" value={note} onChange={(e) => setNote(e.target.value)} aria-label="New note" />
              <Button type="submit" icon={Plus} loading={addNote.isPending}>Add</Button>
            </form>
            <ul className="mt-4 space-y-3">
              {b.notes.map((n) => <li key={n.id} className="rounded-xl bg-slate-50 p-3 text-sm"><p className="whitespace-pre-line">{n.body}</p><p className="mt-1 text-xs text-muted">{n.author} · {fmtDateTime(n.created_at)}</p></li>)}
            </ul>
          </Section>
          <Section title="History">
            <ol className="space-y-3 border-l-2 border-line pl-5">
              {b.status_history.map((h) => (
                <li key={h.id} className="relative text-sm">
                  <span className="absolute -left-[27px] top-1 size-3 rounded-full border-2 border-white bg-orange-500" />
                  <p><span className="font-medium">{h.status_field === "payment_status" ? "Payment" : "Booking"}:</span> {h.previous_status ? `${h.previous_status} → ` : ""}<strong>{h.new_status}</strong></p>
                  <p className="text-xs text-muted">{fmtDateTime(h.created_at)}{h.changed_by && ` · ${h.changed_by}`}{h.notes && ` · ${h.notes}`}</p>
                </li>
              ))}
            </ol>
          </Section>
        </div>

        <div className="space-y-6">
          <Section title="Charges">
            <dl className="space-y-2 text-sm">
              {b.pricing_breakdown.lines.map((l) => (
                <div key={l.code} className="flex justify-between gap-3"><dt className="text-muted">{l.description}{l.quantity > 1 && l.kind === "extra" ? ` × ${l.quantity}` : ""}</dt><dd className="tabular-nums">{Number(l.total) ? usd(l.total) : "Free"}</dd></div>
              ))}
              {Number(b.tax_amount) > 0 && <div className="flex justify-between"><dt className="text-muted">Tax</dt><dd>{usd(b.tax_amount)}</dd></div>}
              <div className="flex justify-between border-t border-line pt-2 font-semibold"><dt>Grand total</dt><dd>{usd(b.grand_total)}</dd></div>
              <div className="flex justify-between text-emerald-700"><dt>Paid (verified)</dt><dd>{usd(b.amount_paid)}</dd></div>
              <div className="flex justify-between font-display text-lg font-bold"><dt>Balance</dt><dd>{usd(b.balance_due)}</dd></div>
            </dl>
          </Section>
          <Section title="Payments" actions={finance && Number(b.balance_due) > 0 && <Button size="sm" variant="outline" icon={Plus} onClick={() => setDialog("record")}>Record</Button>}>
            {b.payments.length === 0 ? <p className="text-sm text-muted">No payments yet.</p> : (
              <ul className="divide-y divide-line">
                {b.payments.map((p) => (
                  <li key={p.id} className="py-3 text-sm">
                    <div className="flex items-center justify-between gap-2"><span className="font-semibold">{usd(p.amount)} · {p.channel_display || p.payment_method_display}</span><Badge status={p.payment_status}>{p.payment_status_display}</Badge></div>
                    <p className="mt-0.5 text-xs text-muted">{p.payment_reference} · {fmtDateTime(p.created_at)}{p.transaction_reference && ` · ref ${p.transaction_reference}`}{p.verified_by && ` · verified by ${p.verified_by}`}</p>
                    {p.payment_status === "PENDING_VERIFICATION" && <Link to={`/admin/payments?q=${p.payment_reference}`} className="mt-1 inline-block text-xs font-semibold text-orange-600 underline">Review payment →</Link>}
                  </li>
                ))}
              </ul>
            )}
          </Section>
          <Section title="Invoices & receipts">
            <ul className="divide-y divide-line">
              {b.invoices.map((inv) => (
                <li key={inv.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                  <span><span className="font-semibold">{inv.invoice_number}</span> · {usd(inv.total_amount)} <Badge status={inv.invoice_status} className="ml-1">{inv.invoice_status_display}</Badge></span>
                  <span className="flex gap-1">
                    <Button size="sm" variant="ghost" icon={Download} onClick={() => dl(`/admin/invoices/${inv.id}/download/`)} aria-label={`Download ${inv.invoice_number}`} />
                    {inv.invoice_status === "ISSUED" && <Button size="sm" variant="ghost" icon={Send} onClick={() => resendInvoice(inv)}>Resend</Button>}
                  </span>
                </li>
              ))}
              {b.receipts.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-2 py-3 text-sm">
                  <span><FileText className="mr-1 inline size-4 text-muted" />Receipt {r.receipt_number} · {usd(r.amount)}</span>
                  <Button size="sm" variant="ghost" icon={Download} onClick={() => dl(`/admin/receipts/${r.id}/download/`)} aria-label={`Download ${r.receipt_number}`} />
                </li>
              ))}
            </ul>
          </Section>
          <Section title="Email delivery">
            <ul className="space-y-2.5 text-sm">
              {b.notifications.map((n) => (
                <li key={n.id} className="flex items-start justify-between gap-2">
                  <span className="min-w-0"><span className="block truncate">{n.notification_type_display}</span>
                    <span className="text-xs text-muted">{n.recipient} · {n.attempts} attempt(s){n.error_message && ` · ${n.error_message.slice(0, 60)}`}</span></span>
                  <span className="flex shrink-0 items-center gap-1">
                    <Badge status={n.delivery_status}>{n.delivery_status_display.split(" ")[0]}</Badge>
                    {["FAILED", "ABANDONED", "SENT"].includes(n.delivery_status) && <button onClick={() => resendNotification(n)} className="grid size-8 place-items-center rounded-lg hover:bg-slate-100" aria-label="Resend email"><Send className="size-4" /></button>}
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        </div>
      </div>

      {ACTIONS[dialog] && <StatusDialog action={dialog} booking={b} onClose={() => setDialog(null)} onDone={refresh} />}
      {dialog === "modify" && <ModifyDialog booking={b} onClose={() => setDialog(null)} onDone={refresh} />}
      {dialog === "record" && <RecordPaymentDialog booking={b} onClose={() => setDialog(null)} onDone={refresh} />}
    </>
  );
}
