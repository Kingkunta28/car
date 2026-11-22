import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { CarFront, Search, SlidersHorizontal, X } from "lucide-react";
import { useVehicles } from "../../lib/hooks";
import { cx, todayISO } from "../../lib/format";
import { Seo } from "../../lib/seo";
import { Button, EmptyState, ErrorState, Skeleton } from "../../components/ui";
import VehicleCard from "../../components/VehicleCard";
import PageHero from "../../components/PageHero";

const CATEGORIES = [
  "ECONOMY", "COMPACT", "COMPACT_SUV", "SUV", "4X4", "MINIVAN", "LUXURY",
];

function Filters({ params, set, clear, count }) {
  const { t } = useTranslation();
  const cats = params.getAll("category");
  const toggleCat = (c) => {
    const next = cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c];
    set({ category: next });
  };
  return (
    <div className="space-y-7">
      <fieldset>
        <legend className="label">{t("fleet.vehicleType")}</legend>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((v) => (
            <button key={v} type="button" onClick={() => toggleCat(v)} aria-pressed={cats.includes(v)}
              className={cx("rounded-full border px-3.5 py-1.5 text-sm font-medium transition",
                cats.includes(v) ? "border-navy-900 bg-navy-900 text-white" : "border-line bg-white text-navy-900 hover:border-navy-600")}>
              {t(`vehicle.categories.${v}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="label">{t("fleet.transmission")}</legend>
        <div className="grid grid-cols-3 gap-2">
          {[["", "Any"], ["AUTOMATIC", "Auto"], ["MANUAL", "Manual"]].map(([v, l]) => (
            <button key={l} type="button" onClick={() => set({ transmission: v })} aria-pressed={(params.get("transmission") || "") === v}
              className={cx("rounded-xl border py-2 text-sm font-medium", (params.get("transmission") || "") === v ? "border-navy-900 bg-navy-50" : "border-line hover:border-navy-600")}>
              {l}
            </button>
          ))}
        </div>
      </fieldset>
      <div>
        <span className="label">{t("fleet.price")}</span>
        <div className="grid grid-cols-2 gap-2">
          <input aria-label="Minimum price per day" type="number" min="0" inputMode="numeric" placeholder="Min" className="input"
            value={params.get("min_price") || ""} onChange={(e) => set({ min_price: e.target.value })} />
          <input aria-label="Maximum price per day" type="number" min="0" inputMode="numeric" placeholder="Max" className="input"
            value={params.get("max_price") || ""} onChange={(e) => set({ max_price: e.target.value })} />
        </div>
      </div>
      <label className="block">
        <span className="label">{t("fleet.passengers")}</span>
        <select className="input" value={params.get("min_passengers") || ""} onChange={(e) => set({ min_passengers: e.target.value })}>
          <option value="">{t("fleet.any")}</option>
          {[2, 4, 5, 7, 8].map((n) => <option key={n} value={n}>{n}+ seats</option>)}
        </select>
      </label>
      <fieldset>
        <legend className="label">{t("fleet.availability")}</legend>
        <label className="flex items-center gap-2.5 text-sm">
          <input type="checkbox" className="size-4 accent-navy-900" checked={params.get("available") === "true"}
            onChange={(e) => set({ available: e.target.checked ? "true" : "" })} />
          {t("fleet.availableNow")}
        </label>
        <p className="mt-3 text-sm text-muted">{t("fleet.checkDates")}</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <input aria-label="From date" type="date" min={todayISO()} className="input" value={params.get("from") || ""} onChange={(e) => set({ from: e.target.value })} />
          <input aria-label="To date" type="date" min={params.get("from") || todayISO()} className="input" value={params.get("to") || ""} onChange={(e) => set({ to: e.target.value })} />
        </div>
      </fieldset>
      <div className="flex items-center justify-between border-t border-line pt-5">
        <span className="text-sm text-muted">{count ?? "…"} vehicle{count === 1 ? "" : "s"}</span>
        <button type="button" onClick={clear} className="text-sm font-semibold text-navy-700 underline underline-offset-4">{t("actions.clear")}</button>
      </div>
    </div>
  );
}

export default function Fleet() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);
  const query = useMemo(() => {
    const q = {};
    for (const k of ["search", "transmission", "min_price", "max_price", "min_passengers", "available", "ordering"]) if (params.get(k)) q[k] = params.get(k);
    const cats = params.getAll("category");
    if (cats.length === 1) q.category = cats[0]; // several types are filtered client-side below
    const from = params.get("from"), to = params.get("to");
    if (from && to && to > from) { q.pickup_at = `${from}T10:00:00`; q.return_at = `${to}T10:00:00`; }
    return q;
  }, [params]);
  const { data, isLoading, error, refetch } = useVehicles(query);
  const list = useMemo(() => {
    if (!data) return [];
    const cats = params.getAll("category");
    return cats.length > 1 ? data.filter((v) => cats.includes(v.category)) : data;
  }, [data, params]);

  const set = (patch) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      next.delete(k);
      (Array.isArray(v) ? v : [v]).filter(Boolean).forEach((x) => next.append(k, x));
    }
    setParams(next, { replace: true });
  };
  const datesQuery = params.get("from") && params.get("to") ? `&pickup_date=${params.get("from")}&return_date=${params.get("to")}` : "";

  return (
    <>
      <Seo title={`${t("fleet.eyebrow")} — ${t("seo.fleet")}`} path="/fleet" description={t("fleet.lead")} />
      <PageHero eyebrow={t("fleet.eyebrow")} title={t("fleet.title")} accent={t("fleet.accent")}
        lead={t("fleet.lead")} />
      <section className="container-x grid gap-10 py-12 lg:grid-cols-[280px_1fr]">
        <aside className="hidden lg:block">
          <div className="card sticky top-28 p-6"><Filters params={params} set={set} clear={() => setParams({})} count={list.length} /></div>
        </aside>
        <div>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted" aria-live="polite"><span className="font-semibold text-navy-900">{list.length}</span> vehicle{list.length === 1 ? "" : "s"}</p>
            <div className="flex flex-wrap items-center gap-2">
              <label className="relative">
                <span className="sr-only">{t("fleet.search")}</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
                <input type="search" className="input h-10 w-full py-0 pl-9 pr-3 text-sm sm:w-52" placeholder={t("fleet.search")}
                  value={params.get("search") || ""} onChange={(e) => set({ search: e.target.value })} />
              </label>
              <label className="flex items-center gap-2 text-sm text-muted">
                <span className="hidden sm:inline">{t("fleet.sortBy")}</span>
                <select className="input h-10 w-auto py-0 pr-9 text-sm" aria-label={t("fleet.sort")} value={params.get("ordering") || ""} onChange={(e) => set({ ordering: e.target.value })}>
                  <option value="">{t("fleet.recommended")}</option>
                  <option value="price_per_day">{t("fleet.priceLow")}</option>
                  <option value="-price_per_day">{t("fleet.priceHigh")}</option>
                  <option value="-passenger_capacity">{t("fleet.seats")}</option>
                  <option value="name">{t("fleet.nameAZ")}</option>
                </select>
              </label>
              <Button variant="outline" size="sm" icon={SlidersHorizontal} onClick={() => setShowFilters(true)} className="lg:hidden">{t("actions.filters")}</Button>
            </div>
          </div>
          {error ? <ErrorState error={error} onRetry={refetch} /> : isLoading ? (
            <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-[420px]" />)}</div>
          ) : list.length ? (
            <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">{list.map((v) => <VehicleCard key={v.id} vehicle={v} query={datesQuery} />)}</div>
          ) : (
            <EmptyState icon={CarFront} title={t("fleet.noMatch")}
              action={<Button variant="outline" onClick={() => setParams({})}>{t("actions.clear")}</Button>}>
              {t("fleet.noMatchHelp", { defaultValue: "Try changing or clearing your filters." })}
            </EmptyState>
          )}
        </div>
      </section>
      {showFilters && (
        <div className="fixed inset-0 z-[60] lg:hidden" role="dialog" aria-modal="true" aria-label={t("actions.filters")}>
          <button className="absolute inset-0 bg-navy-950/50" onClick={() => setShowFilters(false)} aria-label={t("actions.close")} />
          <div className="absolute inset-y-0 right-0 w-[min(360px,90vw)] overflow-y-auto bg-white p-5 shadow-2xl">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t("actions.filters")}</h2>
              <button onClick={() => setShowFilters(false)} className="grid size-10 place-items-center rounded-lg hover:bg-slate-100" aria-label={t("fleet.closeFilters")}><X className="size-5" /></button>
            </div>
            <Filters params={params} set={set} clear={() => setParams({})} count={list.length} />
            <Button className="mt-6 w-full" onClick={() => setShowFilters(false)}>{list.length} {t("fleet.vehicles", { defaultValue: "vehicles" })}</Button>
          </div>
        </div>
      )}
    </>
  );
}
