import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Ban, CalendarCheck, CalendarClock, Car, CheckCircle2, CircleDollarSign, Flag, Wallet } from "lucide-react";
import { api } from "../../lib/api";
import { fmtDate, fmtDateTime, fmtTime, usd } from "../../lib/format";
import { Badge, ErrorState, Stat } from "../../components/ui";
import { PageHeader, TableSkeleton, useAdmin } from "./AdminShell";

export default function Overview() {
  const user = useAdmin();
  const { data: d, isLoading, error, refetch } = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get("/admin/dashboard/"), refetchInterval: 60_000 });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <>
      <PageHeader title={`Karibu, ${user.full_name.split(" ")[0]}`} subtitle="Here's what's happening at Rafiki Car Hire today." />
      {isLoading ? <TableSkeleton /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
            <Stat label="Total bookings" value={d.bookings.total} icon={CalendarCheck} to="/admin/bookings" />
            <Stat label="Pending confirmation" value={d.bookings.pending} icon={CalendarClock} tone="orange" to="/admin/bookings?booking_status=PENDING_CONFIRMATION" />
            <Stat label="Confirmed" value={d.bookings.confirmed} icon={CheckCircle2} to="/admin/bookings?booking_status=CONFIRMED" />
            <Stat label="Completed" value={d.bookings.completed} icon={Flag} to="/admin/bookings?booking_status=COMPLETED" />
            <Stat label="Cancelled / rejected" value={d.bookings.cancelled} icon={Ban} to="/admin/bookings?booking_status=CANCELLED" />
            {d.revenue && <Stat label="Total revenue (verified)" value={usd(d.revenue.total)} hint={`${usd(d.revenue.this_month)} this month`} icon={CircleDollarSign} tone="orange" to="/admin/reports" />}
            <Stat label="Outstanding payments" value={usd(d.outstanding.amount)} hint={`${d.outstanding.bookings} booking(s)`} icon={Wallet} to="/admin/bookings?outstanding=true" />
            <Stat label="Payments to verify" value={d.pending_payments} icon={AlertCircle} tone={d.pending_payments ? "orange" : "navy"} to="/admin/payments?payment_status=PENDING_VERIFICATION" />
            <Stat label="Total vehicles" value={d.vehicles.total} icon={Car} to="/admin/vehicles" />
            <Stat label="Available now" value={d.vehicles.available} hint={`${d.vehicles.on_rent} on rent · ${d.vehicles.maintenance} in maintenance`} icon={Car} to="/admin/vehicles" />
          </div>

          <div className="mt-8 grid gap-6 xl:grid-cols-2">
            <section className="card overflow-hidden">
              <h2 className="border-b border-line px-5 py-4 text-lg font-semibold">Awaiting confirmation</h2>
              {d.awaiting_confirmation.length === 0 ? <p className="px-5 py-10 text-center text-muted">Nothing waiting — nice work.</p> : (
                <ul className="divide-y divide-line">
                  {d.awaiting_confirmation.map((b) => (
                    <li key={b.id}><Link to={`/admin/bookings/${b.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-navy-50/60">
                      <span className="min-w-0"><span className="block font-semibold text-navy-900">{b.booking_reference} · {b.customer__full_name}</span>
                        <span className="text-sm text-muted">{b.vehicle__name} · pickup {fmtDate(b.pickup_date)}</span></span>
                      <span className="text-right"><span className="block font-semibold">{usd(b.grand_total)}</span>
                        <span className="text-xs text-orange-600">hold until {fmtDateTime(b.hold_expires_at)}</span></span>
                    </Link></li>
                  ))}
                </ul>
              )}
            </section>
            <section className="card overflow-hidden">
              <h2 className="border-b border-line px-5 py-4 text-lg font-semibold">Pickups in the next 7 days</h2>
              {d.upcoming_pickups.length === 0 ? <p className="px-5 py-10 text-center text-muted">No confirmed pickups this week.</p> : (
                <ul className="divide-y divide-line">
                  {d.upcoming_pickups.map((b) => (
                    <li key={b.id}><Link to={`/admin/bookings/${b.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-navy-50/60">
                      <span><span className="block font-semibold text-navy-900">{fmtDate(b.pickup_date)} · {fmtTime(b.pickup_time)}</span>
                        <span className="text-sm text-muted">{b.customer__full_name} · {b.vehicle__name}</span></span>
                      <Badge tone="navy">{b.pickup_type.replace("_", " ").toLowerCase()}</Badge>
                    </Link></li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </>
  );
}
