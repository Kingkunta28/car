import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../../lib/api";
import { fmtDate, usd } from "../../lib/format";
import { Badge, ErrorState } from "../../components/ui";
import { PageHeader, Pager, Table, TableSkeleton } from "./AdminShell";

const STATUSES = [["", "All statuses"], ["PENDING_CONFIRMATION", "Pending"], ["CONFIRMED", "Confirmed"], ["COMPLETED", "Completed"],
  ["CANCELLED", "Cancelled"], ["REJECTED", "Rejected"], ["EXPIRED", "Expired"]];
const PAY = [["", "Any payment"], ["UNPAID", "Unpaid"], ["PENDING_VERIFICATION", "To verify"], ["PARTIALLY_PAID", "Partially paid"], ["PAID", "Paid"], ["REFUNDED", "Refunded"]];

export default function Bookings() {
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const [q, setQ] = useState(sp.get("q") || "");
  const page = Number(sp.get("page") || 1);
  const params = Object.fromEntries([...sp.entries()]);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-bookings", params], placeholderData: keepPreviousData,
    queryFn: () => api.get("/admin/bookings/", { params }),
  });
  const set = (patch) => {
    const n = new URLSearchParams(sp);
    Object.entries(patch).forEach(([k, v]) => (v ? n.set(k, v) : n.delete(k)));
    if (!("page" in patch)) n.delete("page");
    setSp(n);
  };

  return (
    <>
      <PageHeader title="Bookings" subtitle="Search, filter and manage every reservation." />
      <div className="card mb-4 grid gap-3 p-4 md:grid-cols-[1.5fr_1fr_1fr_1fr_1fr]">
        <form onSubmit={(e) => { e.preventDefault(); set({ q }); }} className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <input className="input pl-9" placeholder="Reference, name, email, phone, invoice…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search bookings" />
        </form>
        <select className="input" aria-label="Booking status" value={sp.get("booking_status") || ""} onChange={(e) => set({ booking_status: e.target.value })}>
          {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className="input" aria-label="Payment status" value={sp.get("payment_status") || ""} onChange={(e) => set({ payment_status: e.target.value })}>
          {PAY.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input type="date" className="input" aria-label="Pickup from" value={sp.get("pickup_from") || ""} onChange={(e) => set({ pickup_from: e.target.value })} />
        <input type="date" className="input" aria-label="Pickup to" value={sp.get("pickup_to") || ""} onChange={(e) => set({ pickup_to: e.target.value })} />
      </div>
      <div className="card overflow-hidden">
        {error ? <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div> : isLoading ? <TableSkeleton /> : (
          <>
            <Table onRow={(r) => nav(`/admin/bookings/${r.id}`)} rows={data.results} empty="No bookings match these filters."
              columns={[
                { key: "ref", label: "Reference", render: (r) => <span className="font-semibold text-navy-900">{r.booking_reference}</span> },
                { key: "guest", label: "Guest", render: (r) => <><span className="block font-medium">{r.customer_name}</span><span className="text-xs text-muted">{r.customer_phone}</span></> },
                { key: "vehicle", label: "Vehicle", render: (r) => r.vehicle.name },
                { key: "dates", label: "Dates", render: (r) => <span className="whitespace-nowrap">{fmtDate(r.pickup_date, { day: "numeric", month: "short" })} → {fmtDate(r.return_date, { day: "numeric", month: "short", year: "2-digit" })}</span> },
                { key: "total", label: "Total", className: "text-right", render: (r) => <><span className="block font-semibold tabular-nums">{usd(r.grand_total)}</span>{Number(r.balance_due) > 0 && Number(r.amount_paid) > 0 && <span className="text-xs text-muted">due {usd(r.balance_due)}</span>}</> },
                { key: "status", label: "Status", render: (r) => <Badge status={r.booking_status}>{r.booking_status_display}</Badge> },
                { key: "pay", label: "Payment", render: (r) => <Badge status={r.payment_status}>{r.payment_status_display}</Badge> },
              ]} />
            <Pager data={data} page={page} setPage={(p) => set({ page: String(p) })} />
          </>
        )}
      </div>
    </>
  );
}
