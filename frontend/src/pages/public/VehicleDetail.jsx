import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Briefcase, Check, ChevronLeft, ChevronRight, DoorOpen, Expand, Fuel, Info, Plane, Settings2, Users, X } from "lucide-react";
import { useVehicle, useVehicles } from "../../lib/hooks";
import { cx, usd } from "../../lib/format";
import { Seo, SITE_URL } from "../../lib/seo";
import { Alert, Badge, Button, ErrorState, PageLoader } from "../../components/ui";
import VehicleCard, { VehicleImage } from "../../components/VehicleCard";

function Lightbox({ images, index, setIndex, onClose }) {
  const { t } = useTranslation();
  const n = images.length;
  const go = useCallback((d) => setIndex((i) => (i + d + n) % n), [n, setIndex]);
  const startX = useRef(null);
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); if (e.key === "ArrowRight") go(1); if (e.key === "ArrowLeft") go(-1); };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [go, onClose]);
  const img = images[index];
  return (
    <div className="fixed inset-0 z-[90] flex flex-col bg-navy-950/95 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={t("vehicle.photos")}
      onTouchStart={(e) => { startX.current = e.touches[0].clientX; }}
      onTouchEnd={(e) => { const d = e.changedTouches[0].clientX - (startX.current ?? 0); if (Math.abs(d) > 50) go(d < 0 ? 1 : -1); }}>
      <div className="flex items-center justify-between p-4 text-white">
        <span className="text-sm text-white/70">{index + 1} / {n}</span>
        <button onClick={onClose} className="grid size-11 place-items-center rounded-full hover:bg-white/10" aria-label={t("vehicle.closeGallery")} autoFocus><X className="size-6" /></button>
      </div>
      <div className="relative flex flex-1 items-center justify-center px-4 pb-6">
        <img key={img.id} src={img.url} alt={img.alt_text || `Photo ${index + 1}`} className="animate-fade-up max-h-full max-w-full rounded-2xl object-contain" />
        {n > 1 && <>
          <button onClick={() => go(-1)} className="glass absolute left-4 grid size-12 place-items-center rounded-full text-white" aria-label={t("vehicle.previous")}><ChevronLeft className="size-6" /></button>
          <button onClick={() => go(1)} className="glass absolute right-4 grid size-12 place-items-center rounded-full text-white" aria-label={t("vehicle.next")}><ChevronRight className="size-6" /></button>
        </>}
      </div>
    </div>
  );
}

function Gallery({ vehicle }) {
  const { t } = useTranslation();
  const [i, setI] = useState(0);
  const [open, setOpen] = useState(false);
  const images = vehicle.images || [];
  return (
    <div>
      <button type="button" disabled={!images.length} onClick={() => setOpen(true)}
        className="group relative block aspect-[16/10] w-full overflow-hidden rounded-[var(--radius-panel)] bg-slate-100 disabled:cursor-default"
        aria-label={images.length ? t("vehicle.openGallery") : undefined}>
        <VehicleImage vehicle={vehicle} image={images[i]} eager sizes="(min-width:1024px) 60vw, 100vw"
          className="transition duration-700 group-hover:scale-[1.03]" />
        {images.length > 0 && (
          <span className="absolute bottom-4 right-4 inline-flex items-center gap-2 rounded-full bg-navy-950/75 px-3.5 py-2 text-sm font-medium text-white backdrop-blur">
            <Expand className="size-4" /> {images.length} photo{images.length > 1 ? "s" : ""}
          </span>
        )}
      </button>
      {images.length > 1 && (
        <div className="mt-3 flex gap-3 overflow-x-auto pb-1" role="tablist" aria-label={t("vehicle.photos")}>
          {images.map((img, idx) => (
            <button key={img.id} role="tab" aria-selected={i === idx} onClick={() => setI(idx)}
              className={cx("h-20 w-28 shrink-0 overflow-hidden rounded-xl ring-2 ring-offset-2 transition", i === idx ? "ring-orange-500" : "ring-transparent opacity-70 hover:opacity-100")}>
              <img src={img.url} alt={img.alt_text || `Photo ${idx + 1}`} loading="lazy" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
      {open && <Lightbox images={images} index={i} setIndex={setI} onClose={() => setOpen(false)} />}
    </div>
  );
}

export default function VehicleDetail() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data: v, isLoading, error, refetch } = useVehicle(slug);
  const fleet = useVehicles({});

  if (isLoading) return <PageLoader />;
  if (error) return <div className="container-x py-16"><ErrorState error={error} onRetry={refetch} title={error.status === 404 ? "Vehicle not found" : undefined} /></div>;

  const specs = [
    [Settings2, t("vehicle.transmission"), v.transmission_display], [Users, t("vehicle.passengers"), `${v.passenger_capacity} ${t("vehicle.seats", { defaultValue: "seats" })}`],
    [Fuel, t("vehicle.fuel"), v.fuel_type_display], [Briefcase, t("vehicle.luggage"), `${v.luggage_capacity} ${t("vehicle.bags", { defaultValue: "bags" })}`], [DoorOpen, t("vehicle.doors"), v.doors],
  ];
  const bookable = v.availability_status === "AVAILABLE";

  return (
    <>
      <Seo title={`${v.name} Rental in Zanzibar`} path={`/fleet/${v.slug}`} image={v.images?.[0]?.url}
        description={`Hire a ${v.brand} ${v.model} in Zanzibar from ${usd(v.price_per_day)} per day. ${v.transmission_display}, ${v.passenger_capacity} seats, free airport delivery.`}
        jsonLd={{
          "@context": "https://schema.org", "@type": "Product", name: `${v.brand} ${v.model} rental — ${v.name}`,
          image: v.images?.map((i) => i.url), description: v.description, brand: { "@type": "Brand", name: v.brand },
          offers: { "@type": "Offer", priceCurrency: "USD", price: v.price_per_day, url: `${SITE_URL}/fleet/${v.slug}`,
            availability: bookable ? "https://schema.org/InStock" : "https://schema.org/OutOfStock" },
        }} />
      <div className="container-x py-8 sm:py-12">
        <Link to="/fleet" className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700 hover:text-navy-900">
          <ArrowLeft className="size-4" /> Back to fleet
        </Link>
        <div className="mt-6 grid gap-10 lg:grid-cols-[1.5fr_1fr]">
          <div>
            <Gallery vehicle={v} />
            <div className="mt-10">
              <h2 className="display-md">{t("vehicle.about")}</h2>
              <p className="mt-3 whitespace-pre-line leading-relaxed text-muted">{v.description || `${v.brand} ${v.model} — a reliable choice for exploring Zanzibar.`}</p>
            </div>
            <div className="mt-10">
              <h2 className="display-md">{t("vehicle.specifications")}</h2>
              <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                {specs.map(([Icon, k, val]) => (
                  <div key={k} className="flex items-center gap-3 rounded-xl bg-sand-50 p-4">
                    <Icon className="size-5 text-navy-600" aria-hidden />
                    <div><dt className="text-xs text-muted">{k}</dt><dd className="font-semibold text-navy-900">{val}</dd></div>
                  </div>
                ))}
              </dl>
            </div>
            {v.features?.length > 0 && (
              <div className="mt-10">
                <h2 className="display-md">{t("vehicle.features")}</h2>
                <ul className="mt-4 grid gap-2.5 sm:grid-cols-2">
                  {v.features.map((f) => <li key={f} className="flex items-center gap-2.5"><Check className="size-5 text-emerald-600" aria-hidden />{f}</li>)}
                </ul>
              </div>
            )}
            <div className="mt-10 rounded-2xl border border-line p-6">
              <h2 className="flex items-center gap-2 text-xl font-bold"><Info className="size-5 text-orange-600" /> {t("vehicle.conditions")}</h2>
              <ul className="mt-4 space-y-2.5 text-[15px] leading-relaxed text-muted">
                <li>• Bring your passport and a valid driving licence. Visitors also need a Zanzibar driving permit; ask us for the current fee.</li>
                <li>• Delivery to Zanzibar Airport and Zanzibar Town is free; other locations may incur a fee confirmed in your booking quote.</li>
                <li>• Ask us about child-seat availability and pricing when booking.</li>
                <li>• Prices are per day. Fuel is not included.</li>
                <li>• Each started 24-hour period counts as one rental day.</li>
              </ul>
              <Link to="/before-you-rent" className="mt-4 inline-block text-sm font-semibold text-navy-700 underline underline-offset-4">{t("vehicle.readGuide")}</Link>
            </div>
          </div>

          <aside className="lg:sticky lg:top-24 lg:self-start">
            <div className="card p-6">
              <Badge status={v.availability_status}>{v.availability_display}</Badge>
              <h1 className="display-md mt-3">{v.name}</h1>
              <p className="text-muted">{v.brand} {v.model}{v.year ? ` · ${v.year}` : ""} · {v.category_display}</p>
              <p className="mt-6">
                <span className="font-display text-4xl font-bold text-navy-900">{usd(v.price_per_day)}</span>
                <span className="text-muted"> per day</span>
              </p>
              <Alert tone="info" className="mt-4">{t("vehicle.chooseDates")}</Alert>
              <ul className="mt-4 space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2"><Plane className="size-4 text-orange-600" /> Free airport &amp; town handover</li>
                <li className="flex items-center gap-2"><Check className="size-4 text-orange-600" /> Full price shown before you book</li>
              </ul>
              <Button to={`/book?vehicle=${v.slug}`} size="lg" className="mt-6 w-full" disabled={!bookable}
                aria-disabled={!bookable}>{bookable ? "Book this car" : "Not available to book"}</Button>
            </div>
          </aside>
        </div>
      </div>
      {/* Related vehicles: same category first, then closest price */}
      {(() => {
        const others = (fleet.data || []).filter((x) => x.slug !== v.slug && x.availability_status === "AVAILABLE");
        const related = [...others].sort((a, b) =>
          (a.category === v.category ? 0 : 1) - (b.category === v.category ? 0 : 1)
          || Math.abs(a.price_per_day - v.price_per_day) - Math.abs(b.price_per_day - v.price_per_day)).slice(0, 3);
        if (!related.length) return null;
        return (
          <section className="border-t border-line bg-sand-50 py-16 sm:py-20" aria-labelledby="related-heading">
            <div className="container-x">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="eyebrow">{t("vehicle.related")}</p>
                  <h2 id="related-heading" className="display-md mt-3">{t("vehicle.similar")}</h2>
                </div>
                <Button to="/fleet" variant="outline" arrow>{t("actions.viewAll")}</Button>
              </div>
              <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{related.map((x) => <VehicleCard key={x.id} vehicle={x} />)}</div>
            </div>
          </section>
        );
      })()}
      {/* Mobile sticky booking bar */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white/95 px-4 py-3 backdrop-blur-lg lg:hidden" style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}>
        <div className="flex items-center justify-between gap-4">
          <p><span className="font-display text-2xl font-bold text-navy-900">{usd(v.price_per_day)}</span><span className="text-sm text-muted"> / day</span></p>
          <Button to={`/book?vehicle=${v.slug}`} disabled={!bookable} arrow={bookable}>{bookable ? "Book this car" : "Unavailable"}</Button>
        </div>
      </div>
      <div className="h-20 lg:hidden" aria-hidden />
    </>
  );
}
