import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileDown, FileSpreadsheet } from "lucide-react";
import { api, download } from "../../lib/api";
import { cx, todayISO, usd } from "../../lib/format";
import { Button, ErrorState, useToast } from "../../components/ui";
import { PageHeader, TableSkeleton } from "./AdminShell";

const REPORTS = [
  { key: "revenue", label: "Monthly revenue", period: "year" },
  { key: "bookings", label: "Monthly bookings", period: "year" },
  { key: "vehicles", label: "Vehicle performance", period: "range" },
  { key: "payments", label: "Payments", period: "range" },
  { key: "outstanding", label: "Outstanding balances", period: "none" },
];
const MONEY_COLS = new Set(["received", "refunded", "net", "booked_value", "collected", "daily_rate", "amount", "total", "paid", "balance"]);

function MiniBars({ rows, field }) {
  const max = Math.max(1, ...rows.map((r) => Number(r[field]) || 0));
  return (
    <div className="flex h-40 items-end gap-1.5" role="img" aria-label="Monthly chart">
      {rows.map((r) => {
        const v = Number(r[field]) || 0;
        return (
          <div key={r.label} className="group flex flex-1 flex-col items-center gap-1">
            <div className="relative w-full flex-1">
              <div className="absolute bottom-0 w-full rounded-t-md bg-navy-700 transition group-hover:bg-orange-500" style={{ height: `${(v / max) * 100}%` }} title={`${r.label}: ${MONEY_COLS.has(field) ? usd(v) : v}`} />
            </div>
            <span className="text-[10px] font-medium text-muted">{r.label.slice(0, 3)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function Reports() {
  const toast = useToast();
  const [kind, setKind] = useState("revenue");
  const [year, setYear] = useState(new Date().getFullYear());
  const [from, setFrom] = useState(todayISO(-30));
  const [to, setTo] = useState(todayISO());
  const def = REPORTS.find((r) => r.key === kind);
  const params = def.period === "year" ? { year } : def.period === "range" ? { date_from: from, date_to: to } : {};
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ["report", kind, params], queryFn: () => api.get(`/admin/reports/${kind}/`, { params }) });
  const exp = (format) => download(`/admin/reports/${kind}/`, { params: { ...params, export: format } }).catch((e) => toast(e.message, "error"));

  return (
    <>
      <PageHeader title="Reports" subtitle="Revenue is based on verified payments only."
        actions={<><Button variant="outline" icon={FileSpreadsheet} onClick={() => exp("csv")}>Export CSV</Button><Button variant="outline" icon={FileDown} onClick={() => exp("pdf")}>Export PDF</Button></>} />
      <div className="mb-4 flex flex-wrap gap-2" role="tablist">
        {REPORTS.map((r) => (
          <button key={r.key} role="tab" aria-selected={kind === r.key} onClick={() => setKind(r.key)}
            className={cx("rounded-full px-4 py-2 text-sm font-semibold transition", kind === r.key ? "bg-navy-900 text-white" : "bg-white text-navy-900 ring-1 ring-line hover:bg-navy-50")}>{r.label}</button>
        ))}
      </div>
      <div className="card mb-4 flex flex-wrap items-end gap-3 p-4">
        {def.period === "year" && <label className="text-sm"><span className="label">Year</span>
          <select className="input w-32" value={year} onChange={(e) => setYear(e.target.value)}>
            {Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i).map((y) => <option key={y}>{y}</option>)}
          </select></label>}
        {def.period === "range" && <>
          <label className="text-sm"><span className="label">From</span><input type="date" className="input" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
          <label className="text-sm"><span className="label">To</span><input type="date" className="input" value={to} onChange={(e) => setTo(e.target.value)} /></label>
        </>}
        {def.period === "none" && <p className="text-sm text-muted">Open bookings with an unpaid balance, as of today.</p>}
      </div>
      {error ? <ErrorState error={error} onRetry={refetch} /> : isLoading ? <TableSkeleton /> : (
        <div className="space-y-6">
          {data.summary && (
            <div className="flex flex-wrap gap-4">
              {Object.entries(data.summary).map(([k, v]) => (
                <div key={k} className="card px-5 py-4"><p className="text-sm text-muted">{k.replace(/_/g, " ")}</p><p className="font-display text-2xl font-semibold">{usd(v)}</p></div>
              ))}
            </div>
          )}
          {(kind === "revenue" || kind === "bookings") && (
            <div className="card p-5"><h2 className="mb-4 font-semibold">{kind === "revenue" ? "Net revenue by month" : "Booking requests by month"}</h2>
              <MiniBars rows={data.rows} field={kind === "revenue" ? "net" : "total"} /></div>
          )}
          <div className="card overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <caption className="sr-only">{data.title}</caption>
              <thead className="border-b border-line bg-slate-50 text-xs font-semibold uppercase tracking-wider text-muted">
                <tr>{data.headers.map((h) => <th key={h} scope="col" className="px-4 py-3">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.rows.length === 0 && <tr><td colSpan={data.headers.length} className="px-4 py-12 text-center text-muted">No data for this period.</td></tr>}
                {data.rows.map((r, i) => (
                  <tr key={i}>{data.columns.map((c) => <td key={c} className={cx("px-4 py-2.5", MONEY_COLS.has(c) && "tabular-nums")}>{MONEY_COLS.has(c) ? usd(r[c]) : r[c]}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
