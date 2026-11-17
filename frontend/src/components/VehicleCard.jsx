import { Link } from "react-router-dom";
import { Briefcase, Car, Fuel, Settings2, Users } from "lucide-react";
import { cx, usd } from "../lib/format";
import { Badge, Button } from "./ui";

/** Real photo if uploaded; otherwise a neutral branded panel (never a cartoon car). */
export function VehicleImage({ vehicle, image, className, eager = false, sizes = "(min-width:1024px) 33vw, 100vw" }) {
  const img = image || vehicle?.images?.[0];
  if (img?.url) {
    return (
      <img src={img.url} alt={img.alt_text || `${vehicle.brand} ${vehicle.model} for hire in Zanzibar`}
        loading={eager ? "eager" : "lazy"} decoding="async" sizes={sizes}
        className={cx("h-full w-full object-cover", className)} />
    );
  }
  return (
    <div className={cx("flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-navy-800 to-navy-950 text-white/70", className)}
      role="img" aria-label={`${vehicle?.name || "Vehicle"} — photo coming soon`}>
      <Car className="size-10 text-orange-400/80" strokeWidth={1.4} aria-hidden />
      <span className="mt-2 text-xs font-medium uppercase tracking-[0.2em]">{vehicle?.brand} {vehicle?.model}</span>
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
  const available = vehicle.availability_status === "AVAILABLE";
  return (
    <article className="group card flex flex-col overflow-hidden transition duration-300 hover:-translate-y-1 hover:shadow-[var(--shadow-lift)]">
      <Link to={`/fleet/${vehicle.slug}`} className="relative block aspect-[16/10] overflow-hidden bg-slate-100" tabIndex={-1} aria-hidden>
        <VehicleImage vehicle={vehicle} className="transition duration-700 group-hover:scale-[1.04]" />
        <span className="absolute left-3 top-3"><Badge tone="navy" className="bg-white/95">{vehicle.category_display}</Badge></span>
      </Link>
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-lg font-semibold">
              <Link to={`/fleet/${vehicle.slug}`} className="hover:text-navy-700">{vehicle.name}</Link>
            </h3>
            <p className="text-sm text-muted">{vehicle.brand} {vehicle.model}{vehicle.year ? ` · ${vehicle.year}` : ""}</p>
          </div>
          <Badge status={vehicle.availability_status}>{available ? "Available" : vehicle.availability_display}</Badge>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2">
          <Spec icon={Settings2}>{vehicle.transmission_display}</Spec>
          <Spec icon={Users}>{vehicle.passenger_capacity} seats</Spec>
          <Spec icon={Fuel}>{vehicle.fuel_type_display}</Spec>
          <Spec icon={Briefcase}>{vehicle.luggage_capacity} bags</Spec>
        </div>
        <div className="mt-auto flex items-end justify-between gap-3 border-t border-line pt-4 mt-5">
          <p>
            <span className="font-display text-2xl font-semibold text-navy-900">{usd(vehicle.price_per_day)}</span>
            <span className="text-sm text-muted"> / day</span>
          </p>
          <div className="flex gap-2">
            <Button to={`/fleet/${vehicle.slug}`} variant="outline" size="sm">Details</Button>
            <Button to={`/book?vehicle=${vehicle.slug}${query}`} size="sm" disabled={!available}
              aria-disabled={!available} className={!available ? "pointer-events-none opacity-50" : ""}>Book now</Button>
          </div>
        </div>
      </div>
    </article>
  );
}
