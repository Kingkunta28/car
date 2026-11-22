const locale = () => ({ en: "en-US", it: "it-IT", es: "es-ES", fr: "fr-FR", de: "de-DE", pt: "pt-PT" }[document.documentElement.lang] || "en-US");

const USD_PRICE_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  currencyDisplay: "symbol",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Display USD in the site's fixed business format, regardless of selected language. */
export function formatPrice(amount) {
  if (amount == null || (typeof amount === "string" && !amount.trim())) return "—";
  if (typeof amount !== "number" && typeof amount !== "string") return "—";
  const value = Number(amount);
  return Number.isFinite(value) ? USD_PRICE_FORMATTER.format(value) : "—";
}

// Keep existing imports consistent while migrating callers to the named API.
export const usd = formatPrice;

export function fmtDate(d, opts = { weekday: "short", day: "numeric", month: "short", year: "numeric" }) {
  if (!d) return "—";
  const date = typeof d === "string" && d.length === 10 ? new Date(`${d}T12:00:00`) : new Date(d);
  return new Intl.DateTimeFormat(locale(), opts).format(date);
}

export const fmtDateTime = (d) =>
  d ? new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(d)) : "—";

export const fmtTime = (t) => (t ? t.slice(0, 5) : "");

export function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

export function rentalDays(pd, pt, rd, rt) {
  if (!pd || !rd || !pt || !rt) return 0;
  const ms = new Date(`${rd}T${rt}`) - new Date(`${pd}T${pt}`);
  return ms > 0 ? Math.max(1, Math.ceil(ms / 86_400_000)) : 0;
}

export const cx = (...c) => c.filter(Boolean).join(" ");

export function whatsappLink(number, text = "") {
  const digits = (number || "").replace(/\D/g, "");
  if (!digits) return null;
  return `https://wa.me/${digits}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
}

export const STATUS_TONES = {
  PENDING_CONFIRMATION: "amber", CONFIRMED: "green", COMPLETED: "navy", REJECTED: "red", CANCELLED: "red",
  EXPIRED: "slate", UNPAID: "slate", PENDING_VERIFICATION: "amber", PARTIALLY_PAID: "blue", PAID: "green",
  PARTIALLY_REFUNDED: "blue", REFUNDED: "slate", VERIFIED: "green", INITIATED: "amber", FAILED: "red",
  REVERSED: "red", ISSUED: "green", SUPERSEDED: "slate", VOID: "red", SENT: "green", QUEUED: "amber",
  ABANDONED: "red", PENDING: "amber", PURGED: "slate", AVAILABLE: "green", MAINTENANCE: "amber", UNAVAILABLE: "red",
};
