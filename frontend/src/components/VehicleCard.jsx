import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowUpRight, Briefcase, Car, Fuel, Settings2, Users } from "lucide-react";
import { cx, usd } from "../lib/format";
import vehiclePhotos from "../lib/vehicle-photos";
import { Badge } from "./ui";

/** Real photo if uploaded; otherwise a composed, branded panel (never a cartoon car). */
export function VehicleImage({ vehicle, image, className, eager = false, sizes = "(min-width:1024px) 33vw, (min-width:640px) 50vw, 100vw" }) {
  const { t } = useTranslation();
  const [useRemoteFallback, setUseRemoteFallback] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const img = image || vehicle?.images?.[0];
  const bundledUrl = vehiclePhotos[vehicle?.slug];
  const publicVehicleImage = img?.url?.startsWith("/images/cars/") ? img.url : null;
  const preferredUrl = publicVehicleImage || bundledUrl || img?.url;
  const remoteUrl = img?.url && img.url !== preferredUrl ? img.url : bundledUrl && bundledUrl !== preferredUrl ? bundledUrl : null;
  const imageUrl = useRemoteFallback ? remoteUrl : preferredUrl;
  if (imageUrl && !imageFailed) {
    return (
      <img src={imageUrl} alt={img?.alt_text || `${vehicle.brand} ${vehicle.model} for hire in Zanzibar`}
        loading={eager ? "eager" : "lazy"} decoding="async" sizes={sizes}
        onError={() => {
          if (!useRemoteFallback && remoteUrl) setUseRemoteFallback(true);
          else setImageFailed(true);
        }}
        className={cx("h-full w-full object-cover", className)} />
    );
  }
  return (
    <div role="img" aria-label={`${vehicle?.name || "Vehicle"} — photo coming soon`}
      className={cx("relative flex h-full w-full flex-col items-center justify-center overflow-hidden bg-navy-900 text-white/70", className)}>
      <div className="absolute inset-0 bg-[radial-gradient(70%_60%_at_70%_20%,rgb(242_140_40/0.28),transparent_60%)]" aria-hidden />
      <div className="hairline-grid absolute inset-0" aria-hidden />
      <Car className="relative size-10 text-orange-400" strokeWidth={1.3} aria-hidden />
      <span className="relative mt-3 font-display text-lg font-semibold text-white">{vehicle?.brand} {vehicle?.model}</span>
      <span className="relative mt-0.5 text-[11px] uppercase tracking-[0.25em] text-white/50">{t("vehicle.photoSoon")}</span>
    </div>
  );
}

export function Spec({ icon: Icon, children }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-muted">
      <Icon className="size-4 text-navy-600" aria-hidden /> {children}
    </span>
  );
}

export default function VehicleCard({ vehicle, query = "" }) {
  const { t } = useTranslation();
  const available = vehicle.availability_status === "AVAILABLE";
  return (
    <article className="group card card-hover relative flex h-full flex-col overflow-hidden">
      <Link to={`/fleet/${vehicle.slug}`} className="relative block aspect-[16/11] overflow-hidden bg-slate-100" tabIndex={-1} aria-hidden>
        <VehicleImage vehicle={vehicle} className="transition duration-[1.2s] ease-[var(--ease-out-soft)] group-hover:scale-[1.06]" />
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-navy-950/70 to-transparent" />
        <span className="absolute left-4 top-4"><Badge tone="navy" className="bg-white/95 backdrop-blur">{vehicle.category_display}</Badge></span>
        {!available && <span className="absolute right-4 top-4"><Badge status={vehicle.availability_status} className="bg-white/95">{vehicle.availability_display}</Badge></span>}
        <p className="absolute bottom-3 left-4 text-white">
          <span className="font-display text-2xl font-bold">{usd(vehicle.price_per_day)}</span>
          <span className="text-sm text-white/75"> / {t("vehicle.perDay")}</span>
        </p>
        <span className="absolute bottom-3 right-4 grid size-10 translate-y-2 place-items-center rounded-full bg-white text-navy-900 opacity-0 transition duration-500 group-hover:translate-y-0 group-hover:opacity-100">
          <ArrowUpRight className="size-5" />
        </span>
      </Link>
      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <h3 className="text-xl font-semibold">
          <Link to={`/fleet/${vehicle.slug}`} className="after:absolute after:inset-0 focus:outline-none">{vehicle.name}</Link>
        </h3>
        <p className="mt-0.5 text-sm text-muted">{vehicle.brand} {vehicle.model}{vehicle.year ? ` · ${vehicle.year}` : ""}</p>
        <div className="mt-5 grid grid-cols-2 gap-x-3 gap-y-2.5 border-t border-line pt-5">
          <Spec icon={Settings2}>{vehicle.transmission_display}</Spec>
          <Spec icon={Users}>{vehicle.passenger_capacity} {t("vehicle.passengers")}</Spec>
          <Spec icon={Fuel}>{vehicle.fuel_type_display}</Spec>
          <Spec icon={Briefcase}>{vehicle.luggage_capacity} {t("vehicle.luggage")}</Spec>
        </div>
        <div className="relative z-10 mt-6 flex gap-2 pt-1">
          <Link to={`/fleet/${vehicle.slug}`} className="inline-flex h-10 flex-1 items-center justify-center rounded-full border border-line text-sm font-semibold text-navy-900 transition hover:border-navy-600 hover:bg-navy-50">{t("actions.details")}</Link>
          {available ? (
            <Link to={`/book?vehicle=${vehicle.slug}${query}`} className="inline-flex h-10 flex-1 items-center justify-center rounded-full bg-orange-500 text-sm font-semibold text-navy-950 transition hover:bg-orange-400">{t("actions.book")}</Link>
          ) : (
            <span className="inline-flex h-10 flex-1 cursor-not-allowed items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-400" aria-disabled="true">{t("actions.unavailable")}</span>
          )}
        </div>
      </div>
    </article>
  );
}
