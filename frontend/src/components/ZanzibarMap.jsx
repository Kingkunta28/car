import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Clock, MapPin, Plane } from "lucide-react";
import { cx, usd } from "../lib/format";

// Stylised outline of Unguja (Zanzibar island). Not to scale — for orientation only.
const ISLAND = "M160 22 C172 30 182 52 188 78 C196 112 206 140 214 176 C222 214 226 246 222 276 C216 296 204 306 206 322 C210 336 232 334 248 346 C258 356 252 372 238 374 C226 376 222 388 220 404 C216 432 210 462 200 492 C190 520 176 548 160 572 C150 584 138 582 134 566 C128 540 124 512 116 488 C108 462 96 444 92 420 C88 396 98 372 92 352 C86 334 72 326 74 306 C76 288 88 280 92 262 C98 236 106 206 112 176 C118 140 126 104 136 72 C142 48 150 30 160 22 Z";

export const PLACES = [
  { id: "stone-town", name: "Stone Town", x: 82, y: 298, free: true, time: "≈ 15 min", note: "Hotels, the old town and the port — handover is free." },
  { id: "airport", name: "Zanzibar Airport", x: 102, y: 334, free: true, time: "Meet at arrivals", note: "Abeid Amani Karume International. We meet you in the arrivals hall with a name sign." },
  { id: "nungwi", name: "Nungwi", x: 161, y: 42, time: "≈ 1 h 15", note: "Northern tip — beaches, sunsets and dhow builders." },
  { id: "kendwa", name: "Kendwa", x: 145, y: 70, time: "≈ 1 h 10", note: "Calm water and long, swimmable beaches." },
  { id: "matemwe", name: "Matemwe", x: 204, y: 150, time: "≈ 1 h", note: "Quiet north-east coast facing Mnemba Atoll." },
  { id: "pongwe", name: "Pongwe", x: 216, y: 236, time: "≈ 1 h", note: "Small palm-fringed coves on the east coast." },
  { id: "jozani", name: "Jozani Forest", x: 176, y: 380, time: "≈ 45 min", note: "Red colobus monkeys and mangrove boardwalks." },
  { id: "michamvi", name: "Michamvi", x: 240, y: 352, time: "≈ 1 h 15", note: "Peninsula with lagoon views on both sides." },
  { id: "bwejuu", name: "Bwejuu", x: 226, y: 382, time: "≈ 1 h 05", note: "Long white beach between Paje and Michamvi." },
  { id: "paje", name: "Paje", x: 222, y: 404, time: "≈ 1 h", note: "Kite-surfing lagoon on the south-east coast." },
  { id: "jambiani", name: "Jambiani", x: 208, y: 462, time: "≈ 1 h 10", note: "Laid-back fishing village with seaweed farms." },
  { id: "kizimkazi", name: "Kizimkazi", x: 158, y: 556, time: "≈ 1 h", note: "Southern tip — dolphin trips and quiet bays." },
];
const AIRPORT = PLACES[1];

function route(to) {
  const mx = (AIRPORT.x + to.x) / 2 + (to.y < AIRPORT.y ? 40 : 30);
  const my = (AIRPORT.y + to.y) / 2;
  return `M${AIRPORT.x} ${AIRPORT.y} Q ${mx} ${my} ${to.x} ${to.y}`;
}

/**
 * Interactive delivery-zone map. `fee` is the outside-zone fee from the API.
 * `variant="hero"` is a compact dark version; `"full"` adds the place list.
 */
export default function ZanzibarMap({ fee, variant = "full", className }) {
  const { t } = useTranslation();
  const [active, setActive] = useState("nungwi");
  const place = PLACES.find((p) => p.id === active);
  const dark = variant === "hero";

  return (
    <div className={className}>
     <div className={cx("relative", variant === "full" ? "mx-auto aspect-[320/620] max-h-[560px]" : "h-full")}>
      <svg viewBox="0 0 320 620" className={cx("h-full w-full", dark && "pb-40 pt-4")} role="img"
        aria-label={t("ui.mapLabel", { place: place.name })}>
        <defs>
          <radialGradient id="zm-sea" cx="50%" cy="45%" r="60%">
            <stop offset="0%" stopColor={dark ? "#12294B" : "#E6F4F6"} />
            <stop offset="100%" stopColor={dark ? "#050E1C" : "#F7FBFB"} stopOpacity={dark ? 0 : 1} />
          </radialGradient>
          <linearGradient id="zm-land" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={dark ? "#1B3A66" : "#F3EFE8"} />
            <stop offset="100%" stopColor={dark ? "#12294B" : "#E8E1D6"} />
          </linearGradient>
        </defs>
        <rect width="320" height="620" fill="url(#zm-sea)" />
        {/* Coastline glow + land */}
        <path d={ISLAND} fill="none" stroke={dark ? "#3FB6C4" : "#9FD8DE"} strokeOpacity={dark ? 0.25 : 0.6} strokeWidth="10" />
        <path d={ISLAND} fill="url(#zm-land)" stroke={dark ? "#2A4F85" : "#D9CFBF"} strokeWidth="1.5" />
        {/* Free zone */}
        <ellipse cx="92" cy="316" rx="34" ry="44" fill="#F28C28" fillOpacity={dark ? 0.16 : 0.14} stroke="#F28C28" strokeDasharray="4 4" strokeWidth="1.5" />
        {/* Route */}
        {!place.free && (
          <path key={place.id} d={route(place)} fill="none" stroke="#F28C28" strokeWidth="2.5" strokeLinecap="round"
            pathLength="1" strokeDasharray="1" style={{ "--len": 1 }} className="animate-dash" />
        )}
        {/* Pins */}
        {PLACES.map((p) => {
          const on = p.id === active;
          return (
            <g key={p.id} transform={`translate(${p.x} ${p.y})`} className="cursor-pointer" onClick={() => setActive(p.id)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setActive(p.id)} tabIndex={0} role="button"
              aria-label={`${p.name}: ${p.free ? t("ui.freePlace") : t("ui.outsidePlace")}`} aria-pressed={on}>
              {on && <circle r="9" fill="#F28C28" className="origin-center animate-pulse-ring" style={{ transformBox: "fill-box" }} />}
              <circle r={on ? 6.5 : 4.5} fill={p.free ? "#F28C28" : dark ? "#fff" : "#0B1F3A"} stroke={dark ? "#050E1C" : "#fff"} strokeWidth="2" />
              {(on || variant === "full") && (
                <text x={p.x > 200 || p.id === "stone-town" ? -10 : 10} y="4" textAnchor={p.x > 200 || p.id === "stone-town" ? "end" : "start"} fontSize="12" fontWeight={on ? 700 : 500}
                  fill={dark ? "#fff" : "#0B1F3A"} fontFamily="Inter, sans-serif" style={{ paintOrder: "stroke" }}
                  stroke={dark ? "#050E1C" : "#fff"} strokeWidth="3">{p.name}</text>
              )}
            </g>
          );
        })}
        <text x="300" y="604" textAnchor="end" fontSize="9" fill={dark ? "#8DA2C0" : "#8A94A6"} fontFamily="Inter, sans-serif">{t("ui.mapScale")}</text>
      </svg>

      {/* Info card */}
      <div className={cx("absolute inset-x-3 bottom-3 rounded-2xl p-4 sm:inset-x-auto sm:left-3 sm:w-64",
        dark ? "glass text-white" : "border border-line bg-white/95 shadow-[var(--shadow-card)] backdrop-blur")} aria-live="polite">
        <div className="flex items-center justify-between gap-2">
          <p className={cx("font-display text-lg font-semibold", dark ? "text-white" : "text-navy-900")}>{place.name}</p>
          <span className={cx("rounded-full px-2.5 py-0.5 text-xs font-bold",
            place.free ? "bg-orange-500 text-navy-950" : dark ? "bg-white/15 text-white" : "bg-navy-50 text-navy-800")}>
            {place.free ? t("booking.free").toUpperCase() : fee != null ? `${usd(fee)} ${t("ui.eachWay")}` : t("ui.outside")}
          </span>
        </div>
        <p className={cx("mt-1.5 text-sm leading-relaxed", dark ? "text-white/70" : "text-muted")}>{t(`map.notes.${PLACES.findIndex((p) => p.id === place.id)}`)}</p>
        <p className={cx("mt-2 flex items-center gap-1.5 text-xs font-medium", dark ? "text-white/60" : "text-muted")}>
          {place.id === "airport" ? <Plane className="size-3.5" /> : <Clock className="size-3.5" />}
          {place.id === "airport" ? t("ui.meetArrivals") : place.free ? place.time : `${place.time} ${t("ui.driveFrom")}`}
        </p>
      </div>
     </div>

      {variant === "full" && (
        <ul className="mt-4 flex flex-wrap gap-2" aria-label={t("ui.chooseDestination")}>
          {PLACES.map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => setActive(p.id)} aria-pressed={p.id === active}
                className={cx("inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition",
                  p.id === active ? "border-navy-900 bg-navy-900 text-white" : "border-line bg-white text-navy-900 hover:border-navy-600")}>
                <MapPin className={cx("size-3.5", p.free ? "text-orange-500" : "")} aria-hidden />{p.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
