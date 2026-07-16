import type { Variants } from "framer-motion";
import { duration, easing } from "./tokens";

/**
 * Reusable Framer Motion variants. Import these instead of writing ad-hoc
 * transition objects in component code — it's how "every animation feels
 * subtle and consistent" stays true as the library grows past one author.
 *
 * Naming mirrors the motion tokens brief: hover, page transition, sidebar,
 * modal, dropdown, drawer, toast, loading.
 */

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: duration.normal, ease: easing.standard } },
  exit: { opacity: 0, transition: { duration: duration.fast, ease: easing.accelerate } },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: duration.normal, ease: easing.decelerate },
  },
  exit: { opacity: 0, y: 4, transition: { duration: duration.fast, ease: easing.accelerate } },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: duration.normal, ease: easing.emphasized },
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
};

/** Dialog / modal surface entrance. */
export const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96, y: 8 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: duration.normal, ease: easing.emphasized },
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    y: 4,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
};

/** Popover / dropdown menu entrance — smaller travel distance than modals. */
export const dropdownVariants: Variants = {
  hidden: { opacity: 0, scale: 0.98, y: -4 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: duration.fast, ease: easing.decelerate },
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    y: -4,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
};

export const drawerRightVariants: Variants = {
  hidden: { x: "100%" },
  visible: { x: 0, transition: { duration: duration.slow, ease: easing.emphasized } },
  exit: { x: "100%", transition: { duration: duration.normal, ease: easing.accelerate } },
};

export const drawerLeftVariants: Variants = {
  hidden: { x: "-100%" },
  visible: { x: 0, transition: { duration: duration.slow, ease: easing.emphasized } },
  exit: { x: "-100%", transition: { duration: duration.normal, ease: easing.accelerate } },
};

/** Sidebar collapse/expand (width or x-translation depending on layout). */
export const sidebarVariants: Variants = {
  expanded: { width: 272, transition: { duration: duration.normal, ease: easing.standard } },
  collapsed: { width: 72, transition: { duration: duration.normal, ease: easing.standard } },
};

export const toastVariants: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: duration.normal, ease: easing.decelerate },
  },
  exit: { opacity: 0, scale: 0.96, transition: { duration: duration.fast, ease: easing.accelerate } },
};

/** Page-level route transitions — a restrained fade + rise, not a slide. */
export const pageTransitionVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: { duration: duration.normal, ease: easing.standard } },
  exit: { opacity: 0, transition: { duration: duration.fast, ease: easing.accelerate } },
};

/** Stagger a list's children (notification feed, activity timeline, menu items). */
export const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04, delayChildren: 0.02 } },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0, transition: { duration: duration.normal, ease: easing.standard } },
};

/** Subtle scale used for hover/tap affordance on clickable cards/rows. */
export const hoverScale = {
  whileHover: { scale: 1.01, transition: { duration: duration.fast, ease: easing.standard } },
  whileTap: { scale: 0.99 },
};
