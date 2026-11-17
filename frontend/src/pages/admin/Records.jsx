import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Download, Eye, RefreshCw, RotateCcw, Search, Send, X } from "lucide-react";
import { api, download } from "../../lib/api";
import { fmtDate, fmtDateTime, usd } from "../../lib/format";
import { Alert, Badge, Button, ErrorState, Field, Modal, PageLoader, useToast } from "../../components/ui";
import { can, FINANCE, PageHeader, Pager, Table, TableSkeleton, useAdmin } from "./AdminShell";

function useList(key, path, extra = {}) {
  const [sp, setSp] = useSearchParams();
  const params = { ...Object.fromEntries([...sp.entries()]), ...extra };
  const page = Number(sp.get("page") || 1);
  const query = useQuery({ queryKey: [key, params], queryFn: () => api.get(path, { params }), placeholderData: keepPreviousData });
  const set = (patch) => {
    const n = new URLSearchParams(sp);
    Object.entries(patch).forEach(([k, v]) => (v ? n.set(k, v) : n.delete(k)));
    if (!("page" in patch)) n.delete("page");
    setSp(n);
  };
  return { ...query, sp, set, page };
}

function SearchBar({ sp, set, placeholder, children }) {
  const [q, setQ] = useState(sp.get("q") || "");
  return (
    <div className="card mb-4 flex flex-col gap-3 p-4 md:flex-row">
      <form className="relative flex-1" onSubmit={(e) => { e.preventDefault(); set({ q }); }}>
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
        <input className="input pl-9" placeholder={placeholder} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
      </form>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------- Customers */
export function Customers() {
  const nav = useNavigate();
  const { data, isLoading, error, refetch, sp, set, page } = useList("admin-customers", "/admin/customers/");
  return (
    <>
      <PageHeader title="Customers" subtitle="Everyone who has booked with you." />
      <SearchBar sp={sp} set={set} placeholder="Name, email, phone or booking reference…" />
      <div className="card overflow-hidden">
        {error ? <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div> : isLoading ? <TableSkeleton /> : (
          <>
            <Table rows={data.results} onRow={(r) => nav(`/admin/customers/${r.id}`)} empty="No customers found."
              columns={[
                { key: "n", label: "Name", render: (r) => <span className="font-semibold text-navy-900">{r.full_name}</span> },
                { key: "e", label: "Contact", render: (r) => <><span className="block">{r.email}</span><span className="text-xs text-muted">{r.phone}</span></> },
                { key: "nat", label: "Nationality", render: (r) => r.nationality || "—" },
                { key: "b", label: "Bookings", className: "text-right", render: (r) => r.booking_count },
                { key: "s", label: "Paid", className: "text-right", render: (r) => usd(r.total_spent) },
                { key: "l", label: "Last booking", render: (r) => fmtDate(r.last_booking_at) },
              ]} />
            <Pager data={data} page={page} setPage={(p) => set({ page: String(p) })} />
          </>
        )}
      </div>
    </>
  );
}

export function CustomerDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { data: c, isLoading, error, refetch } = useQuery({ queryKey: ["admin-customer", id], queryFn: () => api.get(`/admin/customers/${id}/`) });
  if (isLoading) return <PageLoader />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <>
      <Link to="/admin/customers" className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700"><ArrowLeft className="size-4" /> All customers</Link>
      <PageHeader title={c.full_name} subtitle={`${c.email} · ${c.phone}${c.nationality ? ` · ${c.nationality}` : ""}`} />
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-5"><p className="text-sm text-muted">Bookings</p><p className="font-display text-2xl font-semibold">{c.booking_count}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Total paid</p><p className="font-display text-2xl font-semibold">{usd(c.total_spent)}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Customer since</p><p className="font-display text-2xl font-semibold">{fmtDate(c.created_at)}</p></div>
      </div>
      <h2 className="mb-3 mt-8 text-lg font-semibold">Booking history</h2>
      <div className="card overflow-hidden">
        <Table rows={c.bookings} onRow={(r) => nav(`/admin/bookings/${r.id}`)} columns={[
          { key: "r", label: "Reference", render: (r) => <span className="font-semibold">{r.booking_reference}</span> },
          { key: "v", label: "Vehicle", render: (r) => r.vehicle.name },
          { key: "d", label: "Dates", render: (r) => `${fmtDate(r.pickup_date)} → ${fmtDate(r.return_date)}` },
          { key: "t", label: "Total", render: (r) => usd(r.grand_total) },
          { key: "s", label: "Status", render: (r) => <Badge status={r.booking_status}>{r.booking_status_display}</Badge> },
        ]} />
      </div>
      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <div><h2 className="mb-3 text-lg font-semibold">Invoices</h2><div className="card overflow-hidden">
          <Table rows={c.invoices} columns={[
            { key: "n", label: "Invoice", render: (r) => r.invoice_number },
            { key: "d", label: "Issued", render: (r) => fmtDate(r.issue_date) },
            { key: "t", label: "Total", render: (r) => usd(r.total_amount) },
            { key: "s", label: "Status", render: (r) => <Badge status={r.invoice_status}>{r.invoice_status_display}</Badge> },
          ]} /></div></div>
        <div><h2 className="mb-3 text-lg font-semibold">Payments</h2><div className="card overflow-hidden">
          <Table rows={c.payments} columns={[
            { key: "r", label: "Payment", render: (r) => r.payment_reference },
            { key: "a", label: "Amount", render: (r) => usd(r.amount) },
            { key: "m", label: "Method", render: (r) => r.channel_display || r.payment_method_display },
            { key: "s", label: "Status", render: (r) => <Badge status={r.payment_status}>{r.payment_status_display}</Badge> },
          ]} /></div></div>
      </div>
    </>
  );
}

/* -------------------------------------------------------------- Invoices */
export function Invoices() {
  const toast = useToast();
  const user = useAdmin();
  const [tab, setTab] = useState("invoices");
  const inv = useList("admin-invoices", "/admin/invoices/");
  const receipts = useQuery({ queryKey: ["admin-receipts", inv.sp.get("q")], enabled: tab === "receipts",
    queryFn: () => api.get("/admin/receipts/", { params: { q: inv.sp.get("q") || "" } }) });
  const [revise, setRevise] = useState(null);
  const [reason, setReason] = useState("");
  const qc = useQueryClient();
  const reviseM = useMutation({
    mutationFn: () => api.post(`/admin/invoices/${revise.id}/revise/`, { reason }),
    onSuccess: (d) => { toast(`Revised invoice ${d.invoice_number} issued and emailed`); setRevise(null); setReason(""); qc.invalidateQueries({ queryKey: ["admin-invoices"] }); },
    onError: (e) => toast(e.message, "error"),
  });
  const act = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, "error"); } };

  return (
    <>
      <PageHeader title="Invoices & receipts" subtitle="Issued invoices are never edited — corrections create a revision." />
      <div className="mb-4 flex gap-1 rounded-xl bg-slate-100 p-1 sm:w-fit" role="tablist">
        {[["invoices", "Invoices"], ["receipts", "Payment receipts"]].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold ${tab === k ? "bg-white shadow-sm" : "text-muted"}`}>{l}</button>
        ))}
      </div>
      <SearchBar sp={inv.sp} set={inv.set} placeholder="Invoice number, booking reference or customer…">
        {tab === "invoices" && <select className="input md:w-48" aria-label="Invoice status" value={inv.sp.get("invoice_status") || ""} onChange={(e) => inv.set({ invoice_status: e.target.value })}>
          <option value="">All statuses</option><option value="ISSUED">Current</option><option value="SUPERSEDED">Superseded</option><option value="VOID">Void</option>
        </select>}
      </SearchBar>
      <div className="card overflow-hidden">
        {tab === "invoices" ? (inv.error ? <div className="p-4"><ErrorState error={inv.error} /></div> : inv.isLoading ? <TableSkeleton /> : (
          <>
            <Table rows={inv.data.results} columns={[
              { key: "n", label: "Invoice", render: (r) => <><span className="font-semibold">{r.invoice_number}</span>{r.revision_reason && <span className="block text-xs text-muted">{r.revision_reason}</span>}</> },
              { key: "b", label: "Booking", render: (r) => <Link to={`/admin/bookings/${r.booking_id}`} className="font-medium text-navy-700 underline">{r.booking_reference}</Link> },
              { key: "c", label: "Customer", render: (r) => r.customer_name },
              { key: "d", label: "Issued", render: (r) => fmtDate(r.issue_date) },
              { key: "t", label: "Total", className: "text-right", render: (r) => <span className="font-semibold tabular-nums">{usd(r.total_amount)}</span> },
              { key: "s", label: "Status", render: (r) => <div className="flex flex-wrap gap-1"><Badge status={r.invoice_status}>{r.invoice_status_display}</Badge><Badge status={r.payment_status}>{r.payment_status_display}</Badge></div> },
              { key: "e", label: "Email", render: (r) => r.delivery?.[0] ? <Badge status={r.delivery[0].delivery_status}>{r.delivery[0].delivery_status.toLowerCase()}</Badge> : "—" },
              { key: "a", label: "", className: "text-right whitespace-nowrap", render: (r) => <span className="inline-flex gap-1">
                <Button size="sm" variant="ghost" icon={Eye} aria-label="Preview" onClick={() => act(() => download(`/admin/invoices/${r.id}/download/`, { params: { inline: 1 }, preview: true }))} />
                <Button size="sm" variant="ghost" icon={Download} aria-label="Download" onClick={() => act(() => download(`/admin/invoices/${r.id}/download/`))} />
                {r.invoice_status === "ISSUED" && <Button size="sm" variant="ghost" icon={Send} aria-label="Resend" onClick={() => act(() => api.post(`/admin/invoices/${r.id}/resend/`, {}), "Invoice emailed to guest")} />}
                {r.invoice_status === "ISSUED" && can(user, ...FINANCE) && <Button size="sm" variant="ghost" icon={RefreshCw} aria-label="Issue revised invoice" onClick={() => setRevise(r)} />}
              </span> },
            ]} />
            <Pager data={inv.data} page={inv.page} setPage={(p) => inv.set({ page: String(p) })} />
          </>
        )) : (receipts.isLoading ? <TableSkeleton /> : (
          <Table rows={receipts.data?.results || []} empty="No receipts yet — they're issued when payments are verified." columns={[
            { key: "n", label: "Receipt", render: (r) => <span className="font-semibold">{r.receipt_number}</span> },
            { key: "b", label: "Booking", render: (r) => r.booking_reference },
            { key: "p", label: "Payment", render: (r) => r.payment_reference },
            { key: "c", label: "Customer", render: (r) => r.customer_name },
            { key: "d", label: "Date", render: (r) => fmtDate(r.issue_date) },
            { key: "a", label: "Amount", className: "text-right", render: (r) => usd(r.amount) },
            { key: "x", label: "", className: "text-right", render: (r) => <Button size="sm" variant="ghost" icon={Download} aria-label="Download receipt" onClick={() => act(() => download(`/admin/receipts/${r.id}/download/`))} /> },
          ]} />
        ))}
      </div>
      <Modal open={!!revise} onClose={() => setRevise(null)} title={`Revise ${revise?.invoice_number}`}
        footer={<><Button variant="ghost" onClick={() => setRevise(null)}>Cancel</Button><Button loading={reviseM.isPending} disabled={!reason.trim()} onClick={() => reviseM.mutate()}>Issue revised invoice</Button></>}>
        <p className="text-sm text-muted">This re-issues the invoice from the booking's current details (e.g. after correcting the guest's name). The original is kept and marked superseded. To change prices, dates or extras use <strong>Modify</strong> on the booking instead.</p>
        <Field label="Reason (printed on the revised invoice)" className="mt-4">{(a) => <input {...a} className="input" value={reason} onChange={(e) => setReason(e.target.value)} />}</Field>
      </Modal>
    </>
  );
}

/* -------------------------------------------------------------- Payments */
export function Payments() {
  const toast = useToast();
  const user = useAdmin();
  const finance = can(user, ...FINANCE);
  const qc = useQueryClient();
  const list = useList("admin-payments", "/admin/payments/");
  const [dlg, setDlg] = useState(null); // { type, payment }
  const [form, setForm] = useState({});
  const close = () => { setDlg(null); setForm({}); };
  const m = useMutation({
    mutationFn: ({ type, payment }) => {
      if (type === "verify") return api.post(`/admin/payments/${payment.id}/verify/`, { confirm: !!form.confirm, notes: form.notes || "", ...(form.amount && form.amount !== payment.amount ? { amount: form.amount } : {}) });
      if (type === "reject") return api.post(`/admin/payments/${payment.id}/reject/`, { reason: form.reason || "" });
      if (type === "refund") return api.post(`/admin/payments/${payment.id}/refund/`, { amount: form.amount, reason: form.reason || "", via_gateway: !!form.via_gateway });
      return api.post(`/admin/payments/${payment.id}/sync/`, {});
    },
    onSuccess: (_, v) => { toast({ verify: "Payment verified — receipt sent", reject: "Payment rejected — guest notified", refund: "Refund recorded", sync: "Status refreshed from gateway" }[v.type]); close(); qc.invalidateQueries({ queryKey: ["admin-payments"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); },
    onError: (e) => toast(e.message, "error"),
  });
  const p = dlg?.payment;

  return (
    <>
      <PageHeader title="Payments" subtitle="Nothing counts as paid until it is verified by the gateway or by you." />
      <SearchBar sp={list.sp} set={list.set} placeholder="Payment, booking or transaction reference…">
        <select className="input md:w-56" aria-label="Payment status" value={list.sp.get("payment_status") || ""} onChange={(e) => list.set({ payment_status: e.target.value })}>
          <option value="">All statuses</option><option value="PENDING_VERIFICATION">Awaiting verification</option><option value="VERIFIED">Verified</option>
          <option value="INITIATED">Online — in progress</option><option value="FAILED">Failed</option><option value="REJECTED">Rejected</option><option value="REVERSED">Reversed</option>
        </select>
        <select className="input md:w-44" aria-label="Payment method" value={list.sp.get("payment_method") || ""} onChange={(e) => list.set({ payment_method: e.target.value })}>
          <option value="">Any method</option><option value="MANUAL">Manual</option><option value="ONLINE">Online</option>
        </select>
      </SearchBar>
      <div className="card overflow-hidden">
        {list.error ? <div className="p-4"><ErrorState error={list.error} /></div> : list.isLoading ? <TableSkeleton /> : (
          <>
            <Table rows={list.data.results} empty="No payments match." columns={[
              { key: "r", label: "Payment", render: (r) => <><span className="font-semibold">{r.payment_reference}</span><span className="block text-xs text-muted">{fmtDateTime(r.created_at)}</span></> },
              { key: "b", label: "Booking", render: (r) => <><Link to={`/admin/bookings/${r.booking_id}`} className="font-medium text-navy-700 underline">{r.booking_reference}</Link><span className="block text-xs text-muted">{r.customer_name}</span></> },
              { key: "m", label: "Method", render: (r) => <>{r.payment_method_display}<span className="block text-xs text-muted">{r.channel_display}{r.gateway && ` · ${r.gateway}`}</span></> },
              { key: "t", label: "Reference", render: (r) => <span className="text-xs">{r.transaction_reference || "—"}</span> },
              { key: "a", label: "Amount", className: "text-right", render: (r) => <><span className="font-semibold tabular-nums">{usd(r.amount)}</span>{Number(r.refunded_amount) > 0 && <span className="block text-xs text-red-600">−{usd(r.refunded_amount)} refunded</span>}</> },
              { key: "s", label: "Status", render: (r) => <><Badge status={r.payment_status}>{r.payment_status_display}</Badge>{r.verified_by && <span className="mt-1 block text-xs text-muted">by {r.verified_by}</span>}{!r.verified_by && r.verification_source === "GATEWAY_API" && <span className="mt-1 block text-xs text-muted">by gateway</span>}</> },
              { key: "x", label: "", className: "text-right whitespace-nowrap", render: (r) => finance && <span className="inline-flex gap-1">
                {r.has_proof && <Button size="sm" variant="ghost" icon={Eye} aria-label="View proof" onClick={() => download(`/admin/payments/${r.id}/proof/`, { params: { inline: 1 }, preview: true }).catch((e) => toast(e.message, "error"))} />}
                {r.payment_status === "PENDING_VERIFICATION" && <>
                  <Button size="sm" icon={Check} onClick={() => { setForm({ amount: r.amount }); setDlg({ type: "verify", payment: r }); }}>Verify</Button>
                  <Button size="sm" variant="ghost" icon={X} aria-label="Reject" onClick={() => setDlg({ type: "reject", payment: r })} />
                </>}
                {r.payment_status === "INITIATED" && <Button size="sm" variant="ghost" icon={RefreshCw} aria-label="Check with gateway" onClick={() => m.mutate({ type: "sync", payment: r })} />}
                {r.payment_status === "VERIFIED" && Number(r.amount) > Number(r.refunded_amount) && <Button size="sm" variant="ghost" icon={RotateCcw} aria-label="Refund" onClick={() => { setForm({ amount: (r.amount - r.refunded_amount).toFixed(2) }); setDlg({ type: "refund", payment: r }); }} />}
              </span> },
            ]} />
            <Pager data={list.data} page={list.page} setPage={(pg) => list.set({ page: String(pg) })} />
          </>
        )}
      </div>

      <Modal open={dlg?.type === "verify"} onClose={close} title={`Verify ${p?.payment_reference}`}
        footer={<><Button variant="ghost" onClick={close}>Cancel</Button><Button loading={m.isPending} disabled={!form.confirm} onClick={() => m.mutate(dlg)}>Verify payment</Button></>}>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div><dt className="text-muted">Guest reported</dt><dd className="font-semibold">{usd(p?.amount)} via {p?.channel_display}</dd></div>
          <div><dt className="text-muted">Reference</dt><dd className="font-semibold">{p?.transaction_reference || "—"}</dd></div>
          {p?.payer_note && <div className="col-span-2"><dt className="text-muted">Guest note</dt><dd>{p.payer_note}</dd></div>}
        </dl>
        <Field label="Amount actually received (USD)" className="mt-4">{(a) => <input {...a} type="number" step="0.01" className="input" value={form.amount || ""} onChange={(e) => setForm({ ...form, amount: e.target.value })} />}</Field>
        <Field label="Notes (optional)" className="mt-3">{(a) => <input {...a} className="input" placeholder="e.g. Seen on CRDB statement 18 Nov" value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} />}</Field>
        <label className="mt-4 flex gap-2.5 text-sm"><input type="checkbox" className="mt-0.5 size-4 accent-navy-900" checked={!!form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.checked })} />
          I have checked that these funds were received in our account. This verification is recorded under my name.</label>
      </Modal>
      <Modal open={dlg?.type === "reject"} onClose={close} title={`Reject ${p?.payment_reference}`}
        footer={<><Button variant="ghost" onClick={close}>Cancel</Button><Button variant="danger" loading={m.isPending} disabled={!form.reason?.trim()} onClick={() => m.mutate(dlg)}>Reject payment</Button></>}>
        <Field label="Reason (emailed to the guest)">{(a) => <textarea {...a} rows={3} className="input" value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} />}</Field>
      </Modal>
      <Modal open={dlg?.type === "refund"} onClose={close} title={`Refund ${p?.payment_reference}`}
        footer={<><Button variant="ghost" onClick={close}>Cancel</Button><Button variant="danger" loading={m.isPending} disabled={!form.reason?.trim()} onClick={() => m.mutate(dlg)}>Record refund</Button></>}>
        <Alert tone="warning">Record a refund after the money has been returned — or tick the box to request it through the payment gateway.</Alert>
        <Field label="Refund amount (USD)" className="mt-4">{(a) => <input {...a} type="number" step="0.01" className="input" value={form.amount || ""} onChange={(e) => setForm({ ...form, amount: e.target.value })} />}</Field>
        <Field label="Reason" className="mt-3">{(a) => <input {...a} className="input" value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} />}</Field>
        {p?.payment_method === "ONLINE" && <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-navy-900" checked={!!form.via_gateway} onChange={(e) => setForm({ ...form, via_gateway: e.target.checked })} /> Request the refund through {p.gateway}</label>}
      </Modal>
    </>
  );
}
