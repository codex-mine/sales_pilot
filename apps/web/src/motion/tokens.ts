/**
 * Motion tokens (durations + easings) mirrored from the CSS custom
 * properties in `globals.css`. Framer Motion needs numeric/string values at
 * the JS layer, so these are the canonical source for animated components
 * — keep them in sync with `--duration-*` / `--ease-*` if either changes.
 */
export const duration = {
  fast: 0.12,
  normal: 0.2,
  slow: 0.32,
} as const;

/** Cubic-bezier easing curves. `standard` is the default for most UI motion. */
export const easing = {
  standard: [0.4, 0, 0.2, 1] as const,
  emphasized: [0.2, 0, 0, 1] as const,
  decelerate: [0, 0, 0.2, 1] as const,
  accelerate: [0.4, 0, 1, 1] as const,
};
