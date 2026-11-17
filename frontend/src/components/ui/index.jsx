import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight, CheckCircle2, Info, Loader2, X, XCircle } from "lucide-react";
import { cx, STATUS_TONES } from "../../lib/format";

const BTN = {
  primary: "bg-orange-500 text-navy-950 hover:bg-orange-400 shadow-[0_8px_20px_-8px_rgb(242_140_40/0.6)] hover:shadow-[var(--shadow-glow)]",
  navy: "bg-navy-900 text-white hover:bg-navy-800 shadow-[0_8px_20px_-10px_rgb(11_31_58/0.6)]",
  glass: "border border-white/20 bg-white/10 text-white backdrop-blur-md hover:bg-white/20",
  outlineLight: "border border-white/45 text-white hover:border-white hover:bg-white hover:text-navy-900",
  outline: "border border-line bg-white text-navy-900 hover:border-navy-600 hover:bg-navy-50",
  ghost: "text-navy-900 hover:bg-navy-50",
  light: "bg-white text-navy-900 hover:bg-orange-50",
  danger: "bg-red-600 text-white hover:bg-red-700",
  whatsapp: "bg-[#1FAF38] text-white hover:bg-[#189a30]",
};
const SIZE = { sm: "h-10 px-4 text-sm", md: "h-11 px-5 text-[15px]", lg: "h-[52px] px-7 text-base" };

export function Button({ variant = "primary", size = "md", to, href, loading, className, children, icon: Icon, arrow, ...rest }) {
  const cls = cx(
    "group inline-flex items-center justify-center gap-2 rounded-full font-semibold transition duration-300 ease-[var(--ease-out-soft)]",
    "disabled:cursor-not-allowed disabled:opacity-55 active:scale-[0.98] select-none whitespace-nowrap",
    BTN[variant], SIZE[size], className,
  );
  const content = (
    <>
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : Icon && <Icon className="size-4" aria-hidden />}
      {children}
      {arrow && !loading && <ArrowRight className="arrow size-4" aria-hidden />}
    </>
  );
  if (to) return <Link to={to} className={cls} {...rest}>{content}</Link>;
  if (href) return <a href={href} className={cls} {...rest}>{content}</a>;
  return <button className={cls} disabled={loading || rest.disabled} {...rest}>{content}</button>;
}

const TONE = {
  green: "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/25",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  blue: "bg-sky-50 text-sky-800 ring-sky-600/20",
  navy: "bg-navy-50 text-navy-800 ring-navy-600/20",
  slate: "bg-slate-100 text-slate-700 ring-slate-500/20",
  orange: "bg-orange-50 text-orange-600 ring-orange-500/30",
};

export function Badge({ tone = "slate", status, children, className }) {
  const t = status ? STATUS_TONES[status] || "slate" : tone;
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset whitespace-nowrap", TONE[t], className)}>
      {children}
    </span>
  );
}

export function Field({ label, error, hint, required, children, className }) {
  const id = useId();
  const child = typeof children === "function" ? children({ id, "aria-invalid": !!error, "aria-describedby": error || hint ? `${id}-d` : undefined }) : children;
  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="label">
          {label} {required && <span className="text-orange-600" aria-hidden>*</span>}
        </label>
      )}
      {child}
      {(error || hint) && (
        <p id={`${id}-d`} className={cx("mt-1.5 text-sm", error ? "text-red-600" : "text-muted")} role={error ? "alert" : undefined}>
          {error || hint}
        </p>
      )}
    </div>
  );
}

export const Spinner = ({ className, label = "Loading" }) => (
  <span role="status" className={cx("inline-flex items-center gap-2 text-muted", className)}>
    <Loader2 className="size-5 animate-spin" aria-hidden />
    <span className="sr-only">{label}</span>
  </span>
);

export function PageLoader() {
  return <div className="flex min-h-[40vh] items-center justify-center"><Spinner /></div>;
}

export function EmptyState({ icon: Icon = Info, title, children, action }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-line bg-sand-50 px-6 py-14 text-center">
      <span className="mb-4 grid size-12 place-items-center rounded-2xl bg-white text-navy-700 shadow-sm"><Icon className="size-6" aria-hidden /></span>
      <h3 className="text-lg font-semibold">{title}</h3>
      {children && <div className="mt-1.5 max-w-md text-muted">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "Something went wrong" }) {
  return (
    <div role="alert" className="flex flex-col items-center rounded-2xl border border-red-200 bg-red-50 px-6 py-10 text-center">
      <AlertTriangle className="mb-3 size-8 text-red-600" aria-hidden />
      <h3 className="text-lg font-semibold text-red-900">{title}</h3>
      <p className="mt-1 max-w-md text-red-800">{error?.message || "Please check your connection and try again."}</p>
      {onRetry && <Button variant="outline" className="mt-4" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function Alert({ tone = "info", title, children, className }) {
  const map = {
    info: ["bg-navy-50 border-navy-100 text-navy-900", Info],
    success: ["bg-emerald-50 border-emerald-200 text-emerald-900", CheckCircle2],
    warning: ["bg-orange-50 border-orange-100 text-navy-900", AlertTriangle],
    error: ["bg-red-50 border-red-200 text-red-900", XCircle],
  };
  const [cls, Icon] = map[tone];
  return (
    <div className={cx("flex gap-3 rounded-xl border p-4 text-sm", cls, className)} role={tone === "error" ? "alert" : "status"}>
      <Icon className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div>{title && <p className="font-semibold">{title}</p>}<div className={title ? "mt-0.5" : ""}>{children}</div></div>
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer, size = "md" }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  const widths = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl" };
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={(e) => { e.preventDefault(); onClose?.(); }}
      className={cx("w-[calc(100%-2rem)] rounded-2xl p-0 shadow-2xl backdrop:bg-navy-950/50 backdrop:backdrop-blur-sm m-auto", widths[size])}
    >
      {open && (
        <div className="flex max-h-[85vh] flex-col">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button onClick={onClose} className="grid size-9 place-items-center rounded-lg text-muted hover:bg-slate-100" aria-label="Close dialog">
              <X className="size-5" />
            </button>
          </div>
          <div className="overflow-y-auto px-5 py-4">{children}</div>
          {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line bg-slate-50 px-5 py-3">{footer}</div>}
        </div>
      )}
    </dialog>
  );
}

const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((message, tone = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[100] flex flex-col items-center gap-2 px-4 sm:items-end sm:pr-6" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={cx("pointer-events-auto flex max-w-sm items-start gap-2.5 rounded-xl px-4 py-3 text-sm font-medium shadow-lg",
            t.tone === "error" ? "bg-red-600 text-white" : "bg-navy-900 text-white")}>
            {t.tone === "error" ? <XCircle className="size-5 shrink-0" /> : <CheckCircle2 className="size-5 shrink-0 text-orange-400" />}
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function Stat({ label, value, icon: Icon, tone = "navy", hint, to }) {
  const body = (
    <div className="card flex h-full items-start gap-4 p-5 transition hover:shadow-[var(--shadow-lift)]">
      {Icon && (
        <span className={cx("grid size-11 shrink-0 place-items-center rounded-xl", tone === "orange" ? "bg-orange-100 text-orange-600" : "bg-navy-50 text-navy-700")}>
          <Icon className="size-5" aria-hidden />
        </span>
      )}
      <div className="min-w-0">
        <p className="text-sm text-muted">{label}</p>
        <p className="mt-0.5 font-display text-2xl font-semibold text-navy-900 tabular-nums">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
      </div>
    </div>
  );
  return to ? <Link to={to} className="block">{body}</Link> : body;
}

export function Skeleton({ className }) {
  return <div className={cx("skeleton", className)} aria-hidden />;
}
