import { createContext, useContext, useEffect, useState } from "react";
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3, CalendarCheck, Car, ChevronLeft, ChevronRight, CreditCard, FileText, LayoutDashboard, LogOut, Menu,
  Settings, Users, X,
} from "lucide-react";
import { api, ApiError } from "../../lib/api";
import { cx } from "../../lib/format";
import { Seo } from "../../lib/seo";
import { Alert, Button, Field, PageLoader } from "../../components/ui";
import { Logo } from "../../components/Layout";

const AuthCtx = createContext(null);
export const useAdmin = () => useContext(AuthCtx);
export const can = (user, ...roles) => user && (user.is_superuser || roles.includes(user.role));
export const FINANCE = ["ADMIN", "MANAGER"];

const NAV = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/admin/bookings", label: "Bookings", icon: CalendarCheck },
  { to: "/admin/vehicles", label: "Vehicles", icon: Car },
  { to: "/admin/customers", label: "Customers", icon: Users },
  { to: "/admin/invoices", label: "Invoices", icon: FileText },
  { to: "/admin/payments", label: "Payments", icon: CreditCard },
  { to: "/admin/reports", label: "Reports", icon: BarChart3, roles: FINANCE },
  { to: "/admin/settings", label: "Settings", icon: Settings },
];

export function AdminLogin() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [f, setF] = useState({ email: "", password: "" });
  const [state, setState] = useState({ busy: false, error: "" });
  const submit = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: "" });
    try {
      const res = await api.post("/admin/auth/login/", f);
      qc.setQueryData(["me"], { user: res.user });
      nav("/admin", { replace: true });
    } catch (err) {
      setState({ busy: false, error: err.status === 429 ? "Too many attempts. Please wait and try again." : err.message });
    }
  };
  return (
    <div className="grid min-h-dvh place-items-center bg-navy-950 px-4">
      <Seo title="Staff sign in" noindex />
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center"><Logo light /></div>
        <form onSubmit={submit} className="rounded-2xl bg-white p-7 shadow-2xl">
          <h1 className="text-xl font-bold">Staff sign in</h1>
          <p className="mt-1 text-sm text-muted">Management dashboard — authorised staff only.</p>
          <div className="mt-6 space-y-4">
            <Field label="Email">{(a) => <input {...a} type="email" autoComplete="username" required className="input" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />}</Field>
            <Field label="Password">{(a) => <input {...a} type="password" autoComplete="current-password" required className="input" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />}</Field>
            {state.error && <Alert tone="error">{state.error}</Alert>}
            <Button type="submit" loading={state.busy} className="w-full" size="lg">Sign in</Button>
          </div>
        </form>
        <p className="mt-6 text-center text-sm text-white/50"><Link to="/" className="hover:text-white">← Back to website</Link></p>
      </div>
    </div>
  );
}

export function AdminShell() {
  const { pathname } = useLocation();
  const qc = useQueryClient();
  const nav = useNavigate();
  const [mobile, setMobile] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.get("/admin/auth/me/"), retry: false, staleTime: 5 * 60_000 });
  useEffect(() => { setMobile(false); }, [pathname]);

  if (me.isLoading) return <PageLoader />;
  if (me.error) {
    if (me.error instanceof ApiError && [401, 403].includes(me.error.status)) return <Navigate to="/admin/login" replace />;
    return <div className="p-10"><Alert tone="error">Could not reach the server: {me.error.message}</Alert></div>;
  }
  const user = me.data.user;
  const logout = async () => {
    try { await api.post("/admin/auth/logout/"); } finally { qc.clear(); nav("/admin/login", { replace: true }); }
  };
  const items = NAV.filter((n) => !n.roles || can(user, ...n.roles));

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className={cx("flex h-16 items-center border-b border-white/10 px-5", collapsed && "lg:justify-center lg:px-0")}>
        <Link to="/admin" className={collapsed ? "lg:hidden" : ""}><Logo light /></Link>
        {collapsed && <span className="hidden font-display text-xl font-extrabold text-white lg:block">R<span className="text-orange-500">.</span></span>}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Dashboard">
        {items.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} title={collapsed ? n.label : undefined}
            className={({ isActive }) => cx("flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition",
              isActive ? "bg-orange-500 text-navy-950" : "text-white/70 hover:bg-white/10 hover:text-white", collapsed && "lg:justify-center")}>
            <n.icon className="size-5 shrink-0" aria-hidden /><span className={collapsed ? "lg:sr-only" : ""}>{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        <div className={cx("px-3 py-2", collapsed && "lg:hidden")}>
          <p className="truncate text-sm font-semibold text-white">{user.full_name}</p>
          <p className="truncate text-xs text-white/50">{user.role_display}</p>
        </div>
        <button onClick={logout} className={cx("flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/70 hover:bg-white/10 hover:text-white", collapsed && "lg:justify-center")}>
          <LogOut className="size-5" /><span className={collapsed ? "lg:sr-only" : ""}>Sign out</span>
        </button>
        <button onClick={() => setCollapsed((c) => !c)} className="mt-1 hidden w-full items-center justify-center rounded-xl py-2 text-white/40 hover:text-white lg:flex" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
        </button>
      </div>
    </div>
  );

  return (
    <AuthCtx.Provider value={user}>
      <Seo title="Dashboard" noindex />
      <div className="flex min-h-dvh bg-slate-50">
        <aside className={cx("sticky top-0 hidden h-dvh shrink-0 bg-navy-950 transition-[width] duration-300 lg:block", collapsed ? "w-20" : "w-64")}>{sidebar}</aside>
        {mobile && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button className="absolute inset-0 bg-navy-950/60" onClick={() => setMobile(false)} aria-label="Close menu" />
            <aside className="absolute inset-y-0 left-0 w-72 bg-navy-950">{sidebar}</aside>
          </div>
        )}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-line bg-white/90 px-4 backdrop-blur lg:hidden">
            <button onClick={() => setMobile(true)} className="grid size-10 place-items-center rounded-lg hover:bg-slate-100" aria-label="Open menu">
              {mobile ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
            <Logo />
          </header>
          <main className="flex-1 p-4 sm:p-6 lg:p-8"><Outlet /></main>
        </div>
      </div>
    </AuthCtx.Provider>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div><h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>{subtitle && <p className="mt-1 text-muted">{subtitle}</p>}</div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Pager({ data, page, setPage }) {
  if (!data || (!data.next && !data.previous)) return null;
  const pages = Math.ceil(data.count / 20);
  return (
    <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
      <span className="text-muted">{data.count} results · page {page} of {pages}</span>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={!data.previous} onClick={() => setPage(page - 1)}>Previous</Button>
        <Button size="sm" variant="outline" disabled={!data.next} onClick={() => setPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}

export function Table({ columns, rows, onRow, empty = "Nothing to show yet." }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs font-semibold uppercase tracking-wider text-muted">
          <tr>{columns.map((c) => <th key={c.key} scope="col" className={cx("px-4 py-3", c.className)}>{c.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.length === 0 && <tr><td colSpan={columns.length} className="px-4 py-14 text-center text-muted">{empty}</td></tr>}
          {rows.map((r) => (
            <tr key={r.id} onClick={onRow ? () => onRow(r) : undefined}
              className={cx("transition", onRow && "cursor-pointer hover:bg-navy-50/60")}
              tabIndex={onRow ? 0 : undefined} onKeyDown={onRow ? (e) => e.key === "Enter" && onRow(r) : undefined}>
              {columns.map((c) => <td key={c.key} className={cx("px-4 py-3 align-middle", c.className)}>{c.render ? c.render(r) : r[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TableSkeleton() {
  return <div className="space-y-2 p-4">{[0, 1, 2, 3, 4].map((i) => <div key={i} className="skeleton h-11" />)}</div>;
}
