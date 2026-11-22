import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { filterVehicles, findDefaultVehicle } from "../data/vehicles";

export const useSite = () =>
  useQuery({ queryKey: ["site"], queryFn: () => api.get("/site/"), staleTime: 10 * 60_000 });

export const useBookingOptions = () =>
  useQuery({ queryKey: ["booking-options"], queryFn: () => api.get("/booking-options/"), staleTime: 5 * 60_000 });

function localizedVehicle(vehicle, t) {
  if (!vehicle) return vehicle;
  const featureKeys = {
    "Air conditioning": "airConditioning", "Four-wheel drive": "fourWheelDrive", "High ground clearance": "highClearance",
    "7 seats": "sevenSeats", "Premium SUV comfort": "premiumComfort", "Easy automatic": "easyAutomatic",
    "Large boot": "largeBoot", "Compact and nimble": "compactNimble", "Double cab": "doubleCab",
    "Load bed": "loadBed", "Fuel efficient": "fuelEfficient", "8 seats": "eightSeats", "Sliding doors": "slidingDoors",
  };
  return {
    ...vehicle,
    category_display: t(`vehicle.categories.${vehicle.category}`, { defaultValue: vehicle.category_display }),
    transmission_display: t(`vehicle.values.${vehicle.transmission.toLowerCase()}`, { defaultValue: vehicle.transmission_display }),
    fuel_type_display: t(`vehicle.values.${vehicle.fuel_type.toLowerCase()}`, { defaultValue: vehicle.fuel_type_display }),
    availability_display: t(`vehicle.availability.${vehicle.availability_status}`, { defaultValue: vehicle.availability_display }),
    description: t(`catalogue.${vehicle.slug}`, { defaultValue: vehicle.description }),
    features: vehicle.features.map((feature) => t(`vehicle.features.${featureKeys[feature]}`, { defaultValue: feature })),
  };
}

export const useVehicles = (params = {}) => {
  const { t, i18n } = useTranslation();
  return useQuery({
    queryKey: ["vehicles", params, i18n.resolvedLanguage],
    queryFn: () => filterVehicles(params).map((vehicle) => localizedVehicle(vehicle, t)),
    initialData: () => filterVehicles(params).map((vehicle) => localizedVehicle(vehicle, t)),
    staleTime: Infinity,
  });
};

export const useVehicle = (slug) => {
  const { t, i18n } = useTranslation();
  return useQuery({
    queryKey: ["vehicle", slug, i18n.resolvedLanguage],
    queryFn: () => localizedVehicle(findDefaultVehicle(slug), t) || Promise.reject(new Error("This vehicle could not be found.")),
    initialData: () => localizedVehicle(findDefaultVehicle(slug), t),
    staleTime: Infinity,
  });
};

/** Adds a restrained fade-up to children with [data-reveal] as they scroll into view. */
export function useReveal(deps = []) {
  const ref = useRef(null);
  useEffect(() => {
    const root = ref.current;
    if (!root || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const els = [...root.querySelectorAll("[data-reveal]:not(.reveal-in)")];
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) {
          const delay = Number(e.target.dataset.reveal || 0);
          setTimeout(() => e.target.classList.add("reveal-in"), delay);
          io.unobserve(e.target);
        }
      }),
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    els.forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.top > window.innerHeight) { el.classList.add("reveal-ready"); io.observe(el); }
    });
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}
