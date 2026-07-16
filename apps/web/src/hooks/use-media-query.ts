"use client";

import { useSyncExternalStore } from "react";

/**
 * Subscribes to a CSS media query and returns whether it currently matches.
 * SSR-safe: resolves to `false` on the server and during the first client
 * render, then syncs on mount (avoids hydration mismatches).
 */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Named breakpoints matching the design system's container/grid breakpoints. */
export const breakpoints = {
  sm: "(min-width: 640px)",
  md: "(min-width: 768px)",
  lg: "(min-width: 1024px)",
  xl: "(min-width: 1280px)",
  "2xl": "(min-width: 1440px)",
} as const;

export function useBreakpoint(breakpoint: keyof typeof breakpoints): boolean {
  return useMediaQuery(breakpoints[breakpoint]);
}
