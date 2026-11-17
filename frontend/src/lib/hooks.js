import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export const useSite = () =>
  useQuery({ queryKey: ["site"], queryFn: () => api.get("/site/"), staleTime: 10 * 60_000 });

export const useBookingOptions = () =>
  useQuery({ queryKey: ["booking-options"], queryFn: () => api.get("/booking-options/"), staleTime: 5 * 60_000 });

export const useVehicles = (params = {}) =>
  useQuery({ queryKey: ["vehicles", params], queryFn: () => api.get("/vehicles/", { params }), staleTime: 60_000 });

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
