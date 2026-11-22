import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, ArrowRight, Baby, Building2, Check, ChevronDown, CreditCard, FileCheck2, Landmark, Lock, MapPin, Minus, Plane,
  Plus, ShieldCheck, Upload,
} from "lucide-react";
import { api, ApiError } from "../../lib/api";
import { useBookingOptions, useVehicles } from "../../lib/hooks";
import { cx, fmtDate, rentalDays, todayISO, usd } from "../../lib/format";
import { babySeatText, unitPrice } from "../../lib/content";
import { DEFAULT_BOOKING_OPTIONS, vehicleSnapshot } from "../../data/vehicles";
import { saveGuest } from "../../lib/guest";
import { Seo } from "../../lib/seo";
import { Alert, Button, ErrorState, Field, PageLoader, Spinner } from "../../components/ui";
import { VehicleImage } from "../../components/VehicleCard";

const STEPS = ["Your details", "Car & dates", "Pickup", "Return", "Flight", "Extras", "Payment", "Review & submit"];
const DRAFT_KEY = "rafiki.booking-draft";

const emptyLeg = { type: "", area: "", address: "", instructions: "" };
const initialState = (sp) => ({
  customer: { full_name: "", email: "", phone: "", nationality: "", additional_info: "" },
  vehicle: sp.get("vehicle") || "",
  pickup_date: sp.get("pickup_date") || "", pickup_time: "10:00",
  return_date: sp.get("return_date") || "", return_time: "10:00",
  pickup: { ...emptyLeg, type: sp.get("pickup_type") || "" },
  ret: { ...emptyLeg },
  flight: { airline_name: "", flight_number: "", arrival_date: "", arrival_time: "", arrival_airport: "", notes: "" },
  extras: {},
  payment_method: "",
  accept_terms: false,
});

function loadDraft(sp) {
  const base = initialState(sp);
  try {
    const d = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || "null");
    if (!d) return base;
    const merged = { ...base, ...d, accept_terms: false };
    merged.customer = { ...base.customer, ...(d.customer || {}) };
    merged.pickup = { ...base.pickup, ...(d.pickup || {}) };
    merged.ret = { ...base.ret, ...(d.ret || {}) };
    merged.flight = { ...base.flight, ...(d.flight || {}) };
    merged.extras = d.extras && typeof d.extras === "object" && !Array.isArray(d.extras) ? d.extras : {};
    for (const k of ["vehicle", "pickup_date", "return_date"]) if (sp.get(k)) merged[k] = sp.get(k);
    if (sp.get("pickup_type")) merged.pickup = { ...merged.pickup, type: sp.get("pickup_type") };
    return merged;
  } catch { return base; }
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE_RE = /^\+?[0-9 ()-]{7,25}$/;

function validateStep(step, s, files, options) {
  const e = {};
  if (step === 0) {
    if ((s.customer.full_name || "").trim().length < 2) e["customer.full_name"] = "Please enter your full name.";
    if (!EMAIL_RE.test(s.customer.email || "")) e["customer.email"] = "Please enter a valid email address.";
    if (!PHONE_RE.test(s.customer.phone || "")) e["customer.phone"] = "Include your country code, e.g. +44 7700 900123.";
  }
  if (step === 1) {
    if (!s.vehicle) e.vehicle = "Please choose a vehicle.";
    if (!s.pickup_date) e.pickup_date = "Choose a pickup date.";
    if (!s.return_date) e.return_date = "Choose a return date.";
    if (s.pickup_date && s.return_date && rentalDays(s.pickup_date, s.pickup_time, s.return_date, s.return_time) < 1)
      e.return_date = "Return must be after pickup.";
    if (s.pickup_date && s.pickup_date < todayISO()) e.pickup_date = "Pickup can't be in the past.";
  }
  const leg = (key, prefix) => {
    const l = s[key];
    if (!l.type) e[`${prefix}_type`] = "Choose a location.";
    if ((l.type === "TOWN" || l.type === "OUTSIDE_ZONE") && !l.address.trim()) e[`${prefix}_address`] = "Please enter the exact address, hotel or property.";
    if (l.type === "OUTSIDE_ZONE" && !l.area.trim()) e[`${prefix}_area`] = "Please enter the area or destination.";
  };
  if (step === 2) leg("pickup", "pickup");
  if (step === 3) leg("ret", "return");
  if (step === 5 && s.extras.driving_permit && !options?.isFallback) {
    const max = (options?.max_upload_mb || 8) * 1024 * 1024;
    for (const [k, label] of [["passport", "passport"], ["driving_licence", "driving licence"]]) {
      if (!files[k]) e[k] = `Please upload a copy of your ${label}.`;
      else if (files[k].size > max) e[k] = `File is larger than ${options?.max_upload_mb || 8} MB.`;
    }
  }
  if (step === 6 && !s.payment_method) e.payment_method = "Choose how you'd like to pay.";
  if (step === 7 && !s.accept_terms) e.accept_terms = "Please accept the terms to continue.";
  return e;
}

// Map server field names to the step where they're edited.
const FIELD_STEP = (k) => k.startsWith("customer") ? 0
  : /^(vehicle|pickup_date|pickup_time|return_date|return_time)/.test(k) ? 1
  : k.startsWith("pickup_") ? 2 : k.startsWith("return_") ? 3 : k.startsWith("flight") ? 4
  : /^(extras|documents|passport|driving_licence)/.test(k) ? 5 : k.startsWith("payment") ? 6 : 7;

function toPayload(s, vehicle, totalAmount, options) {
  const flight = Object.fromEntries(Object.entries(s.flight).map(([k, v]) => [k, v || (k.includes("date") || k.includes("time") ? null : "")]));
  return {
    customer: s.customer, vehicle: s.vehicle, vehicle_id: vehicle.id,
    vehicle_snapshot: vehicleSnapshot(vehicle), daily_rate: vehicle.price_per_day,
    ...(totalAmount ? { total_amount: totalAmount } : {}),
    pickup_date: s.pickup_date, pickup_time: s.pickup_time, return_date: s.return_date, return_time: s.return_time,
    pickup_type: s.pickup.type, pickup_area: s.pickup.area, pickup_address: s.pickup.address, pickup_instructions: s.pickup.instructions,
    return_type: s.ret.type, return_area: s.ret.area, return_address: s.ret.address, return_instructions: s.ret.instructions,
    flight, extras: Object.fromEntries(Object.entries(options.isFallback ? {} : s.extras).filter(([, q]) => q > 0)),
    payment_method: s.payment_method, accept_terms: s.accept_terms,
  };
}

function useQuote(s, vehicle) {
  const ready = s.vehicle && s.pickup_date && s.return_date && s.pickup_time && s.return_time
    && vehicle && rentalDays(s.pickup_date, s.pickup_time, s.return_date, s.return_time) > 0;
  const body = {
    vehicle: s.vehicle, vehicle_id: vehicle?.id, vehicle_snapshot: vehicleSnapshot(vehicle), daily_rate: vehicle?.price_per_day,
    pickup_date: s.pickup_date, pickup_time: s.pickup_time, return_date: s.return_date,
    return_time: s.return_time, pickup_type: s.pickup.type || "AIRPORT", return_type: s.ret.type || "AIRPORT",
    extras: Object.fromEntries(Object.entries(s.extras).filter(([, q]) => q > 0)),
  };
  const [debounced, setDebounced] = useState(body);
  const key = JSON.stringify(body);
  useEffect(() => { const t = setTimeout(() => setDebounced(JSON.parse(key)), 300); return () => clearTimeout(t); }, [key]);
  return useQuery({
    queryKey: ["quote", debounced], enabled: !!ready, retry: false, placeholderData: (prev) => prev,
    queryFn: () => api.post("/bookings/quote/", debounced),
  });
}

function LocationPicker({ prefix, leg, onChange, options, errors, isReturn }) {
  const icons = { AIRPORT: Plane, TOWN: Building2, OUTSIDE_ZONE: MapPin };
  return (
    <div className="space-y-6">
      <fieldset>
        <legend className="sr-only">{isReturn ? "Return" : "Pickup"} location</legend>
        <div className="grid gap-3 sm:grid-cols-3" role="radiogroup">
          {options.locations.map((l) => {
            const Icon = icons[l.code];
            const active = leg.type === l.code;
            return (
              <button key={l.code} type="button" role="radio" aria-checked={active} onClick={() => onChange({ ...leg, type: l.code })}
                className={cx("flex flex-col items-start rounded-2xl border-2 p-4 text-left transition",
                  active ? "border-navy-900 bg-navy-50" : "border-line hover:border-navy-600")}>
                <Icon className={cx("size-6", active ? "text-orange-600" : "text-navy-600")} aria-hidden />
                <span className="mt-3 font-semibold text-navy-900">{l.label}</span>
                <span className={cx("mt-1 text-sm font-semibold", options.isFallback && l.code === "OUTSIDE_ZONE" ? "text-muted" : Number(l.fee) ? "text-orange-600" : "text-emerald-700")}>
                  {options.isFallback && l.code === "OUTSIDE_ZONE" ? "Confirm fee" : Number(l.fee) ? usd(l.fee) : "FREE"}
                </span>
              </button>
            );
          })}
        </div>
        {errors[`${prefix}_type`] && <p className="mt-2 text-sm text-red-600" role="alert">{errors[`${prefix}_type`]}</p>}
      </fieldset>

      {leg.type === "AIRPORT" && (
        <Alert tone="info">
          We'll meet you at {options.default_arrival_airport}.{!isReturn && " Add your flight on the next steps so we can track delays."}
        </Alert>
      )}
      {leg.type === "OUTSIDE_ZONE" && (
        <Field label="Area or destination" required error={errors[`${prefix}_area`]} hint="e.g. Nungwi, Paje, Matemwe, Michamvi">
          {(a) => <input {...a} className="input" value={leg.area} maxLength={160} onChange={(e) => onChange({ ...leg, area: e.target.value })} />}
        </Field>
      )}
      {(leg.type === "TOWN" || leg.type === "OUTSIDE_ZONE") && (
        <Field label="Exact address" required error={errors[`${prefix}_address`]} hint="Hotel, resort, street, building or property name">
          {(a) => <input {...a} className="input" value={leg.address} maxLength={255} onChange={(e) => onChange({ ...leg, address: e.target.value })} />}
        </Field>
      )}
      {leg.type && (
        <Field label="Instructions (optional)" hint={leg.type === "AIRPORT" ? "Anything we should know — e.g. travelling with infants" : "Gate codes, landmarks, reception details…"}>
          {(a) => <textarea {...a} rows={3} className="input" value={leg.instructions} maxLength={1000} onChange={(e) => onChange({ ...leg, instructions: e.target.value })} />}
        </Field>
      )}
    </div>
  );
}

function Qty({ value, max, onChange, label }) {
  return (
    <div className="flex items-center gap-1 rounded-xl border border-line bg-white p-1" role="group" aria-label={label}>
      <button type="button" className="grid size-10 place-items-center rounded-lg text-navy-900 hover:bg-navy-50 disabled:opacity-40"
        onClick={() => onChange(Math.max(0, value - 1))} disabled={value <= 0} aria-label={`Fewer ${label}`}><Minus className="size-4" /></button>
      <output className="w-8 text-center font-semibold tabular-nums" aria-live="polite">{value}</output>
      <button type="button" className="grid size-10 place-items-center rounded-lg text-navy-900 hover:bg-navy-50 disabled:opacity-40"
        onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max} aria-label={`More ${label}`}><Plus className="size-4" /></button>
    </div>
  );
}

function FileDrop({ id, label, file, onFile, error, maxMb }) {
  const ref = useRef(null);
  return (
    <div>
      <span className="label">{label} <span className="text-orange-600">*</span></span>
      <button type="button" onClick={() => ref.current?.click()} aria-describedby={`${id}-h`}
        className={cx("flex w-full items-center gap-3 rounded-xl border-2 border-dashed p-4 text-left transition",
          error ? "border-red-400 bg-red-50" : file ? "border-emerald-500 bg-emerald-50" : "border-line hover:border-navy-600")}>
        {file ? <FileCheck2 className="size-6 text-emerald-700" /> : <Upload className="size-6 text-navy-600" />}
        <span className="min-w-0">
          <span className="block truncate font-medium text-navy-900">{file ? file.name : "Choose a file"}</span>
          <span id={`${id}-h`} className="text-sm text-muted">PDF, JPG, PNG or WebP · max {maxMb} MB</span>
        </span>
      </button>
      <input ref={ref} id={id} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp" className="sr-only"
        onChange={(e) => onFile(e.target.files?.[0] || null)} />
      {error && <p className="mt-1.5 text-sm text-red-600" role="alert">{error}</p>}
    </div>
  );
}

function Summary({ s, quote, vehicle, compact }) {
  const q = quote.data;
  return (
    <div className="card overflow-hidden">
      {vehicle && !compact && (
        <div className="aspect-[16/9] bg-slate-100"><VehicleImage vehicle={vehicle} /></div>
      )}
      <div className="p-5">
        <h2 className="text-lg font-semibold">{vehicle ? vehicle.name : "Your booking"}</h2>
        {s.pickup_date && s.return_date && (
          <p className="mt-1 text-sm text-muted">{fmtDate(s.pickup_date)} {s.pickup_time} → {fmtDate(s.return_date)} {s.return_time}</p>
        )}
        {!q && !quote.isFetching && <p className="mt-4 text-sm text-muted">Choose a car and dates to see your price.</p>}
        {quote.isFetching && !q && <div className="mt-4"><Spinner /></div>}
        {quote.error && <p className="mt-4 text-sm text-red-600" role="alert">{quote.error.message}</p>}
        {q && (
          <>
            {!q.available && <Alert tone="error" className="mt-4">This car is already reserved for some of these dates. Please change dates or choose another car.</Alert>}
            <dl className={cx("mt-4 space-y-2 text-sm", quote.isFetching && "opacity-60")}>
              <div className="flex justify-between"><dt className="text-muted">Rental · {q.rental_days} day{q.rental_days > 1 ? "s" : ""} × {usd(q.daily_rate)}</dt><dd className="font-medium tabular-nums">{usd(q.rental_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Pickup fee</dt><dd className="tabular-nums">{Number(q.pickup_fee) ? usd(q.pickup_fee) : "Free"}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Return fee</dt><dd className="tabular-nums">{Number(q.return_fee) ? usd(q.return_fee) : "Free"}</dd></div>
              {q.lines.filter((l) => l.kind === "extra").map((l) => (
                <div key={l.code} className="flex justify-between"><dt className="text-muted">{l.description}{l.quantity > 1 ? ` × ${l.quantity}` : ""}</dt><dd className="tabular-nums">{usd(l.total)}</dd></div>
              ))}
              {Number(q.tax_amount) > 0 && <div className="flex justify-between"><dt className="text-muted">{q.tax_label} ({q.tax_rate}%)</dt><dd className="tabular-nums">{usd(q.tax_amount)}</dd></div>}
              <div className="flex items-baseline justify-between border-t border-line pt-3">
                <dt className="font-semibold text-navy-900">Total (USD)</dt>
                <dd className="font-display text-2xl font-bold text-navy-900 tabular-nums">{usd(q.grand_total)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-muted">Final price is confirmed by our system when you submit.</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function Booking() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const bookingOptions = useBookingOptions();
  const liveOptions = bookingOptions.data;
  const hasLiveOptions = Array.isArray(liveOptions?.extras) && Array.isArray(liveOptions?.locations)
    && !!liveOptions.payment_methods?.online && !!liveOptions.payment_methods?.manual;
  const options = hasLiveOptions ? liveOptions : DEFAULT_BOOKING_OPTIONS;
  const vehicles = useVehicles({});
  const [s, setS] = useState(() => loadDraft(sp));
  const [step, setStep] = useState(0);
  const [files, setFiles] = useState({ passport: null, driving_licence: null });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const topRef = useRef(null);
  const vehicle = useMemo(() => vehicles.data?.find((v) => v.slug === s.vehicle), [vehicles.data, s.vehicle]);
  const quote = useQuote(s, vehicle);

  useEffect(() => {
    const { accept_terms, ...draft } = s; // eslint-disable-line no-unused-vars
    try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch { /* ignore */ }
  }, [s]);

  const up = (patch) => setS((p) => ({ ...p, ...patch }));
  const upCustomer = (k, v) => setS((p) => ({ ...p, customer: { ...p.customer, [k]: v } }));
  const upFlight = (k, v) => setS((p) => ({ ...p, flight: { ...p.flight, [k]: v } }));
  const setExtra = (code, qty) => setS((p) => ({ ...p, extras: { ...p.extras, [code]: qty } }));

  const go = (n) => { setStep(n); setErrors({}); topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); };
  const next = () => {
    const e = validateStep(step, s, files, options);
    if (step === 1 && quote.data && !quote.data.available) e.vehicle = "This car is reserved for these dates — choose other dates or another car.";
    setErrors(e);
    if (Object.keys(e).length) {
      requestAnimationFrame(() => document.querySelector('[aria-invalid="true"], [role="alert"]')?.focus?.());
      return;
    }
    go(step + 1);
  };

  const submit = async () => {
    for (let i = 0; i < STEPS.length; i++) {
      const e = validateStep(i, s, files, options);
      if (Object.keys(e).length) { setErrors(e); setStep(i); return; }
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      const form = new FormData();
      const totalAmount = quote.data && !quote.isFetching && !quote.isPlaceholderData ? quote.data.grand_total : null;
      form.append("payload", JSON.stringify(toPayload(s, vehicle, totalAmount, options)));
      if (s.extras.driving_permit) {
        form.append("passport", files.passport);
        form.append("driving_licence", files.driving_licence);
      }
      const res = await api.upload("/bookings/", form);
      saveGuest(res.booking_reference, res.access_token);
      try { sessionStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ }
      nav("/booking/confirmation", { state: res, replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        const fe = err.fieldErrors();
        const keys = Object.keys(fe);
        if (keys.length) {
          const mapped = Object.fromEntries(keys.map((k) => [k.replace(/^(\w+)\.0$/, "$1"), fe[k]]));
          setErrors(mapped);
          setStep(Math.min(...keys.map(FIELD_STEP)));
        }
        setSubmitError(err.message);
      } else {
        setSubmitError("We couldn't reach our server. Please check your connection and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (vehicles.isLoading) return <PageLoader />;
  if (vehicles.error) return <div className="container-x py-16"><ErrorState error={vehicles.error} onRetry={vehicles.refetch} /></div>;

  const babySeat = options.extras.find((x) => x.code === "baby_seat");
  const permit = options.extras.find((x) => x.code === "driving_permit");
  const others = options.extras.filter((x) => !["baby_seat", "driving_permit"].includes(x.code));
  const bookable = (vehicles.data || []).filter((v) => v.availability_status === "AVAILABLE");

  return (
    <>
      <Seo title="Book a Car" path="/book" description="Book your Zanzibar rental car online in minutes. Free airport handover, instant invoice, and secure payment." />
      <div ref={topRef} className="scroll-mt-24 border-b border-line bg-sand-50">
        <div className="container-x py-8">
          <p className="eyebrow">Book your car</p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">{STEPS[step]}</h1>
          <ol className="mt-6 flex gap-1.5" aria-label="Booking progress">
            {STEPS.map((label, i) => (
              <li key={label} className="flex-1">
                <button type="button" onClick={() => i < step && go(i)} disabled={i > step}
                  aria-current={i === step ? "step" : undefined} aria-label={`Step ${i + 1}: ${label}`}
                  className={cx("h-1.5 w-full rounded-full transition", i < step ? "bg-navy-900" : i === step ? "bg-orange-500" : "bg-slate-200")} />
                <span className="mt-2 hidden text-xs font-medium text-muted lg:block">{label}</span>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-sm text-muted lg:hidden">Step {step + 1} of {STEPS.length}</p>
        </div>
      </div>

      <div className="container-x grid gap-10 py-10 lg:grid-cols-[1fr_380px]">
        <form noValidate onSubmit={(e) => { e.preventDefault(); step === STEPS.length - 1 ? submit() : next(); }} className="min-w-0">
          {options.isFallback && <Alert tone="info" className="mb-6">Some booking extras or location fees are temporarily unavailable. The booking service will validate the total before confirming your request.</Alert>}
          {step < STEPS.length - 1 && (
            <details className="group mb-8 rounded-2xl border border-line bg-sand-50 lg:hidden">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3.5 font-semibold text-navy-900 [&::-webkit-details-marker]:hidden">
                <span>Price summary</span>
                <span className="flex items-center gap-2 font-display text-lg">{quote.data ? usd(quote.data.grand_total) : "—"}
                  <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden /></span>
              </summary>
              <div className="px-2 pb-2"><Summary s={s} quote={quote} vehicle={vehicle} compact /></div>
            </details>
          )}
          {step === 0 && (
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Full name" required error={errors["customer.full_name"]} className="sm:col-span-2">
                {(a) => <input {...a} className="input" autoComplete="name" value={s.customer.full_name} onChange={(e) => upCustomer("full_name", e.target.value)} />}
              </Field>
              <Field label="Email address" required error={errors["customer.email"]} hint="Your invoice and booking link are sent here.">
                {(a) => <input {...a} type="email" className="input" autoComplete="email" value={s.customer.email} onChange={(e) => upCustomer("email", e.target.value)} />}
              </Field>
              <Field label="Phone / WhatsApp" required error={errors["customer.phone"]}>
                {(a) => <input {...a} type="tel" className="input" autoComplete="tel" placeholder="+44 7700 900123" value={s.customer.phone} onChange={(e) => upCustomer("phone", e.target.value)} />}
              </Field>
              <Field label="Nationality" error={errors["customer.nationality"]}>
                {(a) => <input {...a} className="input" autoComplete="country-name" value={s.customer.nationality} onChange={(e) => upCustomer("nationality", e.target.value)} />}
              </Field>
              <Field label="Anything else we should know? (optional)" className="sm:col-span-2">
                {(a) => <textarea {...a} rows={3} maxLength={2000} className="input" value={s.customer.additional_info} onChange={(e) => upCustomer("additional_info", e.target.value)} />}
              </Field>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-6">
              <Field label="Vehicle" required error={errors.vehicle}>
                {(a) => (
                  <select {...a} className="input" value={s.vehicle} onChange={(e) => up({ vehicle: e.target.value })}>
                    <option value="">Choose a vehicle…</option>
                    {bookable.map((v) => <option key={v.slug} value={v.slug}>{v.name} — {v.transmission_display}, {v.passenger_capacity} seats — {usd(v.price_per_day)}/day</option>)}
                  </select>
                )}
              </Field>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Pickup date" required error={errors.pickup_date}>
                  {(a) => <input {...a} type="date" min={todayISO()} className="input" value={s.pickup_date} onChange={(e) => up({ pickup_date: e.target.value, ...(s.return_date && e.target.value > s.return_date ? { return_date: e.target.value } : {}) })} />}
                </Field>
                <Field label="Pickup time" required>
                  {(a) => <input {...a} type="time" step="900" className="input" value={s.pickup_time} onChange={(e) => up({ pickup_time: e.target.value })} />}
                </Field>
                <Field label="Return date" required error={errors.return_date}>
                  {(a) => <input {...a} type="date" min={s.pickup_date || todayISO()} className="input" value={s.return_date} onChange={(e) => up({ return_date: e.target.value })} />}
                </Field>
                <Field label="Return time" required error={errors.return_time}>
                  {(a) => <input {...a} type="time" step="900" className="input" value={s.return_time} onChange={(e) => up({ return_time: e.target.value })} />}
                </Field>
              </div>
              {rentalDays(s.pickup_date, s.pickup_time, s.return_date, s.return_time) > 0 && (
                <p className="rounded-xl bg-navy-50 px-4 py-3 text-sm text-navy-900">
                  Rental duration: <strong>{rentalDays(s.pickup_date, s.pickup_time, s.return_date, s.return_time)} day(s)</strong> — each started 24 hours counts as a day.
                </p>
              )}
            </div>
          )}

          {step === 2 && <LocationPicker prefix="pickup" leg={s.pickup} options={options} errors={errors} onChange={(pickup) => up({ pickup })} />}
          {step === 3 && (
            <div className="space-y-4">
              {s.pickup.type && !s.ret.type && (
                <button type="button" className="text-sm font-semibold text-navy-700 underline underline-offset-4" onClick={() => up({ ret: { ...s.pickup } })}>
                  Return to the same place as pickup
                </button>
              )}
              <LocationPicker prefix="return" isReturn leg={s.ret} options={options} errors={errors} onChange={(ret) => up({ ret })} />
            </div>
          )}

          {step === 4 && (
            <div className="space-y-5">
              <Alert tone="info">Optional — but if you're arriving by air, your flight details help us meet you even if you're delayed.</Alert>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Airline">{(a) => <input {...a} className="input" value={s.flight.airline_name} maxLength={80} onChange={(e) => upFlight("airline_name", e.target.value)} />}</Field>
                <Field label="Flight number" error={errors["flight.flight_number"]}>{(a) => <input {...a} className="input uppercase" placeholder="e.g. KQ 484" value={s.flight.flight_number} maxLength={20} onChange={(e) => upFlight("flight_number", e.target.value)} />}</Field>
                <Field label="Arrival date">{(a) => <input {...a} type="date" className="input" value={s.flight.arrival_date} onChange={(e) => upFlight("arrival_date", e.target.value)} />}</Field>
                <Field label="Arrival time">{(a) => <input {...a} type="time" className="input" value={s.flight.arrival_time} onChange={(e) => upFlight("arrival_time", e.target.value)} />}</Field>
                <Field label="Arrival airport" className="sm:col-span-2">{(a) => <input {...a} className="input" placeholder={options.default_arrival_airport} value={s.flight.arrival_airport} maxLength={160} onChange={(e) => upFlight("arrival_airport", e.target.value)} />}</Field>
                <Field label="Flight notes" className="sm:col-span-2">{(a) => <textarea {...a} rows={2} className="input" value={s.flight.notes} maxLength={1000} onChange={(e) => upFlight("notes", e.target.value)} />}</Field>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-5">
              {options.isFallback && <Alert tone="info">Tell us about any extras you need in the final notes; our team will confirm availability and pricing.</Alert>}
              {babySeat && (
                <div className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex gap-4">
                    <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-orange-100 text-orange-600"><Baby className="size-6" /></span>
                    <div>
                      <h3 className="font-semibold">{babySeat.name}</h3>
                      <p className="text-sm text-muted">{babySeatText(options)} — for the whole booking, not per day.</p>
                      {(s.extras.baby_seat || 0) > 0 && <p className="mt-1 text-sm font-semibold text-navy-900">{s.extras.baby_seat} × {usd(unitPrice(babySeat, s.extras.baby_seat))} = {usd(s.extras.baby_seat * unitPrice(babySeat, s.extras.baby_seat))}</p>}
                    </div>
                  </div>
                  <Qty label="baby seats" value={s.extras.baby_seat || 0} max={babySeat.max_quantity} onChange={(q) => setExtra("baby_seat", q)} />
                </div>
              )}
              {permit && (
                <div className={cx("card p-5", s.extras.driving_permit && "ring-2 ring-navy-900")}>
                  <label className="flex cursor-pointer gap-4">
                    <input type="checkbox" className="mt-1 size-5 accent-navy-900" checked={!!s.extras.driving_permit}
                      onChange={(e) => setExtra("driving_permit", e.target.checked ? 1 : 0)} />
                    <span>
                      <span className="block font-semibold text-navy-900">{permit.name} — {usd(permit.price)}</span>
                      <span className="mt-1 block text-sm leading-relaxed text-muted">
                        We'll help you apply for the Zanzibar driving permit you need as a visitor. We arrange the application on your behalf; <strong>approval is decided by the issuing authority and payment does not guarantee it.</strong>
                      </span>
                    </span>
                  </label>
                  {!!s.extras.driving_permit && (
                    <div className="mt-5 space-y-4 border-t border-line pt-5">
                      <p className="flex items-start gap-2 text-sm text-navy-900"><Lock className="mt-0.5 size-4 shrink-0 text-emerald-700" />
                        Your documents are uploaded over an encrypted connection, stored privately, seen only by authorised staff and deleted after your rental. Please don't send them by email or WhatsApp.</p>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <FileDrop id="passport" label="Valid passport" file={files.passport} error={errors.passport} maxMb={options.max_upload_mb}
                          onFile={(f) => setFiles((x) => ({ ...x, passport: f }))} />
                        <FileDrop id="licence" label="Valid driving licence" file={files.driving_licence} error={errors.driving_licence} maxMb={options.max_upload_mb}
                          onFile={(f) => setFiles((x) => ({ ...x, driving_licence: f }))} />
                      </div>
                      {errors.documents && <p className="text-sm text-red-600" role="alert">{errors.documents}</p>}
                    </div>
                  )}
                </div>
              )}
              {others.map((x) => (
                <div key={x.code} className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="font-semibold">{x.name} — {usd(x.price)} <span className="text-sm font-normal text-muted">{x.pricing_type_display.toLowerCase()}</span></h3>
                    {x.description && <p className="text-sm text-muted">{x.description}</p>}
                  </div>
                  {x.max_quantity > 1
                    ? <Qty label={x.name} value={s.extras[x.code] || 0} max={x.max_quantity} onChange={(q) => setExtra(x.code, q)} />
                    : <input type="checkbox" aria-label={`Add ${x.name}`} className="size-5 accent-navy-900" checked={!!s.extras[x.code]} onChange={(e) => setExtra(x.code, e.target.checked ? 1 : 0)} />}
                </div>
              ))}
              {errors.extras && <p className="text-sm text-red-600" role="alert">{errors.extras}</p>}
            </div>
          )}

          {step === 6 && (
            <div className="space-y-6">
              <fieldset>
                <legend className="sr-only">Payment method</legend>
                <div className={`grid gap-4 ${options.payment_methods.online.available ? "sm:grid-cols-2" : "sm:grid-cols-1"}`} role="radiogroup">
                  {[
                    ...(options.payment_methods.online.available ? [
                      { code: "ONLINE", icon: CreditCard, title: "Pay online", text: "Secure card or mobile-money checkout through our payment partner." },
                    ] : []),
                    { code: "MANUAL", icon: Landmark, title: "Manual payment", text: "Bank transfer, mobile money or other methods we accept. We verify your payment before marking it paid." },
                  ].map((m) => (
                    <button key={m.code} type="button" role="radio" aria-checked={s.payment_method === m.code}
                      onClick={() => up({ payment_method: m.code })}
                      className={cx("flex flex-col items-start rounded-2xl border-2 p-5 text-left transition disabled:cursor-not-allowed disabled:opacity-50",
                        s.payment_method === m.code ? "border-navy-900 bg-navy-50" : "border-line hover:border-navy-600")}>
                      <m.icon className="size-6 text-navy-700" />
                      <span className="mt-3 font-semibold text-navy-900">{m.title}</span>
                      <span className="mt-1 text-sm text-muted">{m.text}</span>
                    </button>
                  ))}
                </div>
                {errors.payment_method && <p className="mt-2 text-sm text-red-600" role="alert">{errors.payment_method}</p>}
              </fieldset>
              {s.payment_method === "MANUAL" && options.payment_methods.manual.instructions && (
                <div className="rounded-2xl bg-sand-50 p-5">
                  <h3 className="font-semibold">How to pay</h3>
                  <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-muted">{options.payment_methods.manual.instructions}</p>
                  <p className="mt-3 text-sm text-muted">Payment instructions will be provided with your booking invoice.</p>
                </div>
              )}
              {s.payment_method === "ONLINE" && (
                <Alert tone="info">After you submit, you'll get your invoice and can pay securely from the confirmation page. Your booking is only marked paid once the payment provider confirms it to us.</Alert>
              )}
            </div>
          )}

          {step === 7 && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                {[
                  ["Guest", <>{s.customer.full_name}<br />{s.customer.email}<br />{s.customer.phone}</>, 0],
                  ["Car & dates", <>{vehicle?.name}<br />{fmtDate(s.pickup_date)} {s.pickup_time}<br />→ {fmtDate(s.return_date)} {s.return_time}</>, 1],
                  ["Pickup", <>{options.locations.find((l) => l.code === s.pickup.type)?.label}{s.pickup.area && ` — ${s.pickup.area}`}<br />{s.pickup.address}</>, 2],
                  ["Return", <>{options.locations.find((l) => l.code === s.ret.type)?.label}{s.ret.area && ` — ${s.ret.area}`}<br />{s.ret.address}</>, 3],
                  ["Flight", s.flight.flight_number || s.flight.airline_name ? `${s.flight.airline_name} ${s.flight.flight_number}` : "Not provided", 4],
                  ["Extras", Object.entries(s.extras).filter(([, q]) => q > 0).map(([c, q]) => `${options.extras.find((e) => e.code === c)?.name} × ${q}`).join(", ") || "None", 5],
                  ["Payment", s.payment_method === "ONLINE" ? "Pay online (secure checkout)" : s.payment_method === "MANUAL" ? "Manual payment" : "Not chosen", 6],
                ].map(([title, body, st]) => (
                  <div key={title} className="rounded-2xl border border-line p-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold uppercase tracking-wider text-muted">{title}</h3>
                      <button type="button" onClick={() => go(st)} className="text-sm font-semibold text-navy-700 underline underline-offset-4">Edit</button>
                    </div>
                    <p className="mt-2 text-[15px] leading-relaxed text-navy-900">{body}</p>
                  </div>
                ))}
              </div>
              <div className="lg:hidden"><Summary s={s} quote={quote} vehicle={vehicle} compact /></div>
              <label className="flex gap-3 text-sm leading-relaxed">
                <input type="checkbox" className="mt-0.5 size-5 accent-navy-900" checked={s.accept_terms} onChange={(e) => up({ accept_terms: e.target.checked })}
                  aria-invalid={!!errors.accept_terms} />
                <span>I agree to the <a href="/terms" target="_blank" className="font-semibold text-navy-700 underline">rental terms</a> and <a href="/privacy" target="_blank" className="font-semibold text-navy-700 underline">privacy policy</a>, and confirm that my details are correct.</span>
              </label>
              {errors.accept_terms && <p className="text-sm text-red-600" role="alert">{errors.accept_terms}</p>}
              <p className="flex items-center gap-2 text-sm text-muted"><ShieldCheck className="size-4 text-emerald-700" />
                Submitting reserves the car for {options.hold_hours} hours while we confirm. You'll receive your invoice by email straight away.</p>
            </div>
          )}

          {submitError && <Alert tone="error" className="mt-6">{submitError}</Alert>}

          <div className="mt-10 flex items-center justify-between gap-3 border-t border-line pt-6">
            {step > 0 ? <Button type="button" variant="ghost" icon={ArrowLeft} onClick={() => go(step - 1)}>Back</Button> : <span />}
            {step < STEPS.length - 1
              ? <Button type="submit" size="lg">{step === 4 && !s.flight.flight_number && !s.flight.airline_name ? "Skip" : "Continue"} <ArrowRight className="size-4" /></Button>
              : <Button type="submit" size="lg" loading={submitting} icon={Check}>Submit booking</Button>}
          </div>
        </form>

        <aside className="hidden lg:block"><div className="sticky top-24"><Summary s={s} quote={quote} vehicle={vehicle} /></div></aside>
      </div>
    </>
  );
}
