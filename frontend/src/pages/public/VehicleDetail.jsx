import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Briefcase, Check, DoorOpen, Fuel, Info, Plane, Settings2, Users } from "lucide-react";
import { api } from "../../lib/api";
import { useBookingOptions } from "../../lib/hooks";
import { priceOf, zoneFee } from "../../lib/content";
import { cx, fmtDate, usd } from "../../lib/format";
import { Seo, SITE_URL } from "../../lib/seo";
import { Badge, Button, ErrorState, PageLoader } from "../../components/ui";
import { VehicleImage } from "../../components/VehicleCard";

function Gallery({ vehicle }) {
  const [i, setI] = useState(0);
  const images = vehicle.images || [];
  return (
    <div>
      <div className="aspect-[16/10] overflow-hidden rounded-3xl bg-slate-100">
        <VehicleImage vehicle={vehicle} image={images[i]} eager sizes="(min-width:1024px) 60vw, 100vw" />
      </div>
      {images.length > 1 && (
        <div className="mt-3 flex gap-3 overflow-x-auto pb-1" role="tablist" aria-label="Vehicle photos">
          {images.map((img, idx) => (
            <button key={img.id} role="tab" aria-selected={i === idx} onClick={() => setI(idx)}
              className={cx("h-20 w-28 shrink-0 overflow-hidden rounded-xl ring-2 transition", i === idx ? "ring-orange-500" : "ring-transparent opacity-75 hover:opacity-100")}>
              <img src={img.url} alt={img.alt_text || `Photo ${idx + 1}`} loading="lazy" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function VehicleDetail() {
  const { slug } = useParams();
  const { data: v, isLoading, error, refetch } = useQuery({ queryKey: ["vehicle", slug], queryFn: () => api.get(`/vehicles/${slug}/`) });
  const avail = useQuery({ queryKey: ["vehicle-avail", slug], queryFn: () => api.get(`/vehicles/${slug}/availability/`), enabled: !!v });
  const { data: options } = useBookingOptions();

  if (isLoading) return <PageLoader />;
  if (error) return <div className="container-x py-16"><ErrorState error={error} onRetry={refetch} title={error.status === 404 ? "Vehicle not found" : undefined} /></div>;

  const specs = [
    [Settings2, "Transmission", v.transmission_display], [Users, "Passengers", `${v.passenger_capacity} seats`],
    [Fuel, "Fuel", v.fuel_type_display], [Briefcase, "Luggage", `${v.luggage_capacity} bags`], [DoorOpen, "Doors", v.doors],
  ];
  const busy = (avail.data?.busy || []).filter((b) => new Date(b.end) > new Date()).slice(0, 6);
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
              <h2 className="text-2xl font-bold">About this car</h2>
              <p className="mt-3 whitespace-pre-line leading-relaxed text-muted">{v.description || `${v.brand} ${v.model} — a reliable choice for exploring Zanzibar.`}</p>
            </div>
            <div className="mt-10">
              <h2 className="text-2xl font-bold">Specifications</h2>
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
                <h2 className="text-2xl font-bold">Features</h2>
                <ul className="mt-4 grid gap-2.5 sm:grid-cols-2">
                  {v.features.map((f) => <li key={f} className="flex items-center gap-2.5"><Check className="size-5 text-emerald-600" aria-hidden />{f}</li>)}
                </ul>
              </div>
            )}
            <div className="mt-10 rounded-2xl border border-line p-6">
              <h2 className="flex items-center gap-2 text-xl font-bold"><Info className="size-5 text-orange-600" /> Important rental information</h2>
              <ul className="mt-4 space-y-2.5 text-[15px] leading-relaxed text-muted">
                <li>• Bring your passport and a valid driving licence. Visitors also need a Zanzibar driving permit — we can arrange it for {priceOf(options, "driving_permit") ? usd(priceOf(options, "driving_permit")) : "a small fee"}.</li>
                <li>• Delivery to Zanzibar Airport and Zanzibar Town is free; other locations cost {zoneFee(options) ? usd(zoneFee(options)) : "a flat fee"} each way.</li>
                <li>• Child seats are {priceOf(options, "baby_seat") ? usd(priceOf(options, "baby_seat")) : "available"} per seat for the whole rental.</li>
                <li>• Each started 24-hour period counts as one rental day.</li>
              </ul>
              <Link to="/before-you-rent" className="mt-4 inline-block text-sm font-semibold text-navy-700 underline underline-offset-4">Read everything before you rent</Link>
            </div>
          </div>

          <aside className="lg:sticky lg:top-24 lg:self-start">
            <div className="card p-6">
              <Badge status={v.availability_status}>{v.availability_display}</Badge>
              <h1 className="mt-3 text-3xl font-bold">{v.name}</h1>
              <p className="text-muted">{v.brand} {v.model}{v.year ? ` · ${v.year}` : ""} · {v.category_display}</p>
              <p className="mt-6">
                <span className="font-display text-4xl font-bold text-navy-900">{usd(v.price_per_day)}</span>
                <span className="text-muted"> per day</span>
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted">
                <li className="flex items-center gap-2"><Plane className="size-4 text-orange-600" /> Free airport &amp; town handover</li>
                <li className="flex items-center gap-2"><Check className="size-4 text-orange-600" /> Full price shown before you book</li>
              </ul>
              <Button to={`/book?vehicle=${v.slug}`} size="lg" className="mt-6 w-full" disabled={!bookable}
                aria-disabled={!bookable}>{bookable ? "Book this car" : "Not available to book"}</Button>
              {busy.length > 0 && (
                <div className="mt-6 border-t border-line pt-5">
                  <p className="text-sm font-semibold text-navy-900">Already reserved</p>
                  <ul className="mt-2 space-y-1 text-sm text-muted">
                    {busy.map((b) => <li key={b.start}>{fmtDate(b.start, { day: "numeric", month: "short" })} – {fmtDate(b.end, { day: "numeric", month: "short", year: "numeric" })}</li>)}
                  </ul>
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>
    </>
  );
}
